"""Tests for 14B-3A-E1: runner-to-production AST consistency.

Verifies:
1. check_standing_up_axis AST matches _check_standing_up_axis (normalized)
2. axis_to_vector from runner produces same output as 14A Core
3. vector_angle_degrees from runner produces same output as 14A Core
"""
import ast, os, sys, math, difflib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

READER_PATH = os.path.join(ROOT, "protocol_guard", "phase3_min", "blender_scene_reader.py")
CORE_PATH = os.path.join(ROOT, "protocol_guard", "phase3_min", "asset_scene_preflight_core.py")
RUNNER_PATH = os.path.join(ROOT, "protocol_guard", "phase3_min", "tests", "blender_standing_i2_runner.py")


def _parse_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return ast.parse(f.read(), filename=path)


def _extract_func(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def _strip_docstring(body):
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        return body[1:]
    return body


def _is_import(node):
    return isinstance(node, (ast.Import, ast.ImportFrom))


def _strip_imports(body):
    return [n for n in body if not _is_import(n)]


def _normalize_func(node, new_name, strip_imports_flag):
    body = list(node.body)
    body = _strip_docstring(body)
    if strip_imports_flag:
        body = _strip_imports(body)
    new_node = ast.FunctionDef(
        name=new_name,
        args=node.args,
        body=body,
        decorator_list=[],
        returns=None,
        type_comment=None,
        type_params=[],
    )
    ast.copy_location(new_node, node)
    return new_node


def _ast_dump(node):
    return ast.dump(node, indent=2)


def _diff(label_a, label_b, dump_a, dump_b):
    lines_a = dump_a.splitlines(True)
    lines_b = dump_b.splitlines(True)
    diff = list(difflib.unified_diff(lines_a, lines_b,
        fromfile=label_a, tofile=label_b))
    return "".join(diff)


# ── Compile runner helpers from AST ──────────────────────────────────────

def _compile_runner_helpers():
    """Extract _AXIS_MAP, axis_to_vector, vector_angle_degrees from runner
    AST and compile them into executable functions. Returns (atv, vad)."""
    tree = _parse_file(RUNNER_PATH)
    nodes = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) and node.name in (
            "axis_to_vector", "vector_angle_degrees",
        ):
            nodes.append(node)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_AXIS_MAP":
                    nodes.append(node)

    module_ast = ast.Module(body=nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    code = compile(module_ast, "<runner_helpers>", "exec")
    namespace = {"math": math}
    exec(code, namespace)
    return namespace["axis_to_vector"], namespace["vector_angle_degrees"]


# ── Test: main algorithm AST consistency ─────────────────────────────────

class TestMainAlgorithmConsistency:
    def test_check_standing_up_axis_matches_production(self):
        reader_tree = _parse_file(READER_PATH)
        runner_tree = _parse_file(RUNNER_PATH)

        prod = _extract_func(reader_tree, "_check_standing_up_axis")
        runner = _extract_func(runner_tree, "check_standing_up_axis")

        assert prod is not None, "_check_standing_up_axis not found"
        assert runner is not None, "check_standing_up_axis not found"

        prod_norm = _normalize_func(prod, "_check", strip_imports_flag=True)
        runner_norm = _normalize_func(runner, "_check", strip_imports_flag=False)

        prod_dump = _ast_dump(prod_norm)
        runner_dump = _ast_dump(runner_norm)

        assert prod_dump == runner_dump, (
            "check_standing_up_axis AST does not match _check_standing_up_axis.\n"
            + _diff("production", "runner", prod_dump, runner_dump)
        )


# ── Test: axis_to_vector output equivalence ──────────────────────────────

class TestAxisToVectorOutput:
    def test_all_six_axes_match_core(self):
        runner_atv, _ = _compile_runner_helpers()
        from protocol_guard.phase3_min.asset_scene_preflight_core import (
            axis_to_vector as core_atv,
        )

        for axis in ["+X", "-X", "+Y", "-Y", "+Z", "-Z"]:
            r = runner_atv(axis)
            c = core_atv(axis)
            assert len(r) == 3, f"axis_to_vector({axis!r}) length={len(r)}"
            assert abs(r[0] - c[0]) < 1e-12, (
                f"axis_to_vector({axis!r}) x: runner={r[0]} core={c[0]}")
            assert abs(r[1] - c[1]) < 1e-12, (
                f"axis_to_vector({axis!r}) y: runner={r[1]} core={c[1]}")
            assert abs(r[2] - c[2]) < 1e-12, (
                f"axis_to_vector({axis!r}) z: runner={r[2]} core={c[2]}")


# ── Test: vector_angle_degrees output equivalence ────────────────────────

class TestVectorAngleDegreesOutput:
    def test_all_36_axis_combinations_match_core(self):
        _, runner_vad = _compile_runner_helpers()
        from protocol_guard.phase3_min.asset_scene_preflight_core import (
            axis_to_vector as core_atv,
            vector_angle_degrees as core_vad,
        )

        axes = ["+X", "-X", "+Y", "-Y", "+Z", "-Z"]
        for a_name in axes:
            for b_name in axes:
                a = list(core_atv(a_name))
                b = list(core_atv(b_name))
                r = runner_vad(a, b)
                c = core_vad(a, b)
                assert abs(r - c) < 1e-8, (
                    f"vector_angle_degrees({a_name},{b_name}): "
                    f"runner={r} core={c}"
                )

    def test_shear_directions_match_core(self):
        _, runner_vad = _compile_runner_helpers()
        from protocol_guard.phase3_min.asset_scene_preflight_core import (
            vector_angle_degrees as core_vad,
        )

        def _norm(x, y, z):
            L = math.sqrt(x*x + y*y + z*z)
            return [x/L, y/L, z/L]

        vectors = [
            _norm(0.5, 0.0, 1.0),   # shear direction
            _norm(1.0, 2.0, 3.0),   # general direction
            _norm(1.0, 1.0, 1.0),   # diagonal
            _norm(1.0, 1.0, 0.0),   # XY diagonal
            _norm(0.0, 3.0, 4.0),   # YZ 3-4-5
            _norm(1.0, 0.0, -1.0),  # XZ diagonal
        ]
        for i, va in enumerate(vectors):
            for j, vb in enumerate(vectors):
                r = runner_vad(va, vb)
                c = core_vad(va, vb)
                assert abs(r - c) < 1e-5, (
                    f"vector_angle_degrees(vec[{i}],vec[{j}]): "
                    f"runner={r} core={c}"
                )

    def test_non_axis_unit_vectors_against_axes_match_core(self):
        _, runner_vad = _compile_runner_helpers()
        from protocol_guard.phase3_min.asset_scene_preflight_core import (
            axis_to_vector as core_atv,
            vector_angle_degrees as core_vad,
        )

        def _norm(x, y, z):
            L = math.sqrt(x*x + y*y + z*z)
            return [x/L, y/L, z/L]

        non_axis = [
            _norm(0.5, 0.0, 1.0),   # shear direction
            _norm(1.0, 1.0, 1.0),   # diagonal
            _norm(1.0, 0.0, -1.0),  # XZ diagonal
        ]
        axes = ["+X", "-X", "+Y", "-Y", "+Z", "-Z"]
        for vec in non_axis:
            for a_name in axes:
                ax = list(core_atv(a_name))
                r = runner_vad(vec, ax)
                c = core_vad(vec, ax)
                assert abs(r - c) < 1e-5, (
                    f"vector_angle_degrees(vec,{a_name}): "
                    f"runner={r} core={c}"
                )
