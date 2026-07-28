"""Animation State I5 R6 — Scope Guard using Rotation I4A framework."""

import ast
import os
import sys
from collections import defaultdict

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

READER_PATH = os.path.join(ROOT, "protocol_guard", "phase3_min", "blender_scene_reader.py")

from protocol_guard.phase3_min.tests.test_asset_scene_preflight_blender_rotation_i4a import (
    ReachableScopeAnalyzer, _attr_chain, _shallow_nodes,
)

ENTRY_NAME = "_check_animation_state"

ALLOWED_CANONICAL = [
    "scene.objects", "animation_object.name",
    "animation_object.animation_data", "animation_data.action", "action.name",
    "animation_object.data", "data.pose_position", "scene.frame_current",
]

FORBIDDEN_ATTRS = {
    "matrix_world", "matrix_local", "matrix_basis", "matrix_parent_inverse",
    "rotation_euler", "rotation_quaternion", "rotation_mode",
    "location", "scale", "dimensions",
    "hide_viewport", "hide_render", "hide_get",
    "material_slots", "bound_box",
    "evaluated_get", "evaluated_depsgraph_get", "to_mesh", "to_mesh_clear",
    "users_collection", "nla_tracks",
}

VAR_MAP = {"obj": "animation_object", "matched_obj": "animation_object",
           "ad_cached": "animation_data", "obj_data": "data"}

with open(READER_PATH, encoding="utf-8") as f:
    _REAL = f.read()
_REAL_TREE = ast.parse(_REAL)


def _get_rot_module():
    import protocol_guard.phase3_min.tests.test_asset_scene_preflight_blender_rotation_i4a as m
    return m


def _analyze(source):
    tree = ast.parse(source)
    rot_mod = _get_rot_module()

    # Check entry exists
    all_funcs = {}
    for n in ast.iter_child_nodes(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            all_funcs[n.name] = n
    if ENTRY_NAME not in all_funcs:
        return {"entry_found": False}

    # Patch ENTRY_NAMES and get reachable funcs
    saved = rot_mod.ENTRY_NAMES
    rot_mod.ENTRY_NAMES = {ENTRY_NAME}
    try:
        analyzer = ReachableScopeAnalyzer(tree)
        funcs = analyzer._get_reachable_funcs()
    finally:
        rot_mod.ENTRY_NAMES = saved

    # Walk each reachable function using shallow nodes (extended to skip Lambda)
    def _shallow_skip_lambda(body):
        """Walk statements, skip FunctionDef/ClassDef entirely, skip Lambda bodies."""
        nodes = []
        def _walk_no_nested(n):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                return
            nodes.append(n)
            for child in ast.iter_child_nodes(n):
                _walk_no_nested(child)
        for stmt in body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            _walk_no_nested(stmt)
        return nodes

    nodes_per_func = {}
    for fname, fn in funcs.items():
        nodes_per_func[fname] = _shallow_skip_lambda(fn.body)

    # Canonical attr counts
    canon_counts = defaultdict(int)
    for fname, fn in funcs.items():
        for node in nodes_per_func[fname]:
            if isinstance(node, ast.Attribute):
                chain = _attr_chain(node)
                if chain:
                    resolved = [VAR_MAP.get(chain[0], chain[0])] + list(chain[1:])
                    canon_counts[".".join(resolved)] += 1

    allowed_counts = {a: canon_counts.get(a, 0) for a in ALLOWED_CANONICAL}

    # Forbidden reads
    forbidden_reads = set()
    for fname, fn in funcs.items():
        for node in nodes_per_func[fname]:
            if isinstance(node, ast.Attribute):
                chain = _attr_chain(node)
                if chain:
                    chain_s = ".".join(chain)
                    for fb in FORBIDDEN_ATTRS:
                        if fb in chain:
                            forbidden_reads.add(chain_s)

    # Multi-layer alias tracking
    raw_aliases = {}
    for fname, fn in funcs.items():
        for node in nodes_per_func[fname]:
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        if isinstance(node.value, ast.Name):
                            raw_aliases[(fname, t.id)] = node.value.id
                        elif isinstance(node.value, ast.Attribute):
                            chain = _attr_chain(node.value)
                            if chain:
                                raw_aliases[(fname, t.id)] = ".".join(chain)

    def _resolve_alias(fname, name):
        """Follow alias chains, resolving attribute prefixes."""
        seen = {name}; cur = name
        while True:
            if (fname, cur) in raw_aliases:
                nxt = raw_aliases[(fname, cur)]
                if nxt in seen: break
                seen.add(nxt); cur = nxt
                continue
            # Try to resolve cur as "prefix.rest" where prefix is an alias
            if "." in cur:
                parts = cur.split(".", 1)
                if (fname, parts[0]) in raw_aliases:
                    resolved_prefix = _resolve_alias_one(fname, parts[0])
                    new_cur = f"{resolved_prefix}.{parts[1]}"
                    if new_cur not in seen:
                        seen.add(new_cur); cur = new_cur
                        continue
            break
        return cur

    def _resolve_alias_one(fname, name):
        """Single-step alias resolution."""
        if (fname, name) in raw_aliases:
            return _resolve_alias_one(fname, raw_aliases[(fname, name)])
        return name

    # Forbidden calls with alias resolution
    forbidden_calls = set()
    for fname, fn in funcs.items():
        for node in nodes_per_func[fname]:
            if isinstance(node, ast.Call):
                chain = _attr_chain(node.func)
                if chain:
                    cs = ".".join(chain)
                    if cs.startswith("bpy.ops."):
                        forbidden_calls.add(cs)
                    # Alias resolution for calls
                    resolved = _resolve_alias(fname, chain[0])
                    if resolved.startswith("bpy.ops."):
                        forbidden_calls.add(f"alias:{cs}→{resolved}")
                # Method call on alias: _o.get('X') where _o → bpy.data.objects
                if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                    resolved = _resolve_alias(fname, node.func.value.id)
                    if resolved == "bpy.data.objects":
                        forbidden_calls.add(f"alias:{node.func.value.id}.{node.func.attr}()→bpy.data.objects.{node.func.attr}()")
                    if resolved.startswith("bpy.data.objects"):
                        forbidden_calls.add(f"alias_method:{resolved}.{node.func.attr}()")
            # Subscript on alias
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
                resolved = _resolve_alias(fname, node.value.id)
                if resolved == "bpy.data.objects" or resolved.startswith("bpy.data.objects"):
                    forbidden_calls.add(f"alias_sub:{node.value.id}[...]→{resolved}[...]")

    # Writes with alias resolution + deep target traversal
    writes = set()
    def _collect_write_targets(target):
        if isinstance(target, ast.Attribute):
            chain = _attr_chain(target)
            if chain:
                writes.add(".".join(chain))
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                _collect_write_targets(elt)

    for fname, fn in funcs.items():
        for node in nodes_per_func[fname]:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = [node.target] if isinstance(node, ast.AnnAssign) else list(node.targets)
                for t in targets:
                    _collect_write_targets(t)
            if isinstance(node, ast.AugAssign):
                _collect_write_targets(node.target)
            if isinstance(node, ast.Delete):
                for t in node.targets:
                    _collect_write_targets(t)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in ("setattr", "delattr"):
                    writes.add(f"{node.func.id}()")

    return {
        "entry_found": True,
        "reachable": sorted(funcs.keys()),
        "allowed_counts": allowed_counts,
        "forbidden_reads": sorted(forbidden_reads),
        "forbidden_calls": sorted(forbidden_calls),
        "writes": sorted(writes),
    }


_BASELINE = _analyze(_REAL)


# ---- Baseline ----
def test_entry_exists():
    assert _BASELINE["entry_found"] is True


def test_allowed_counts():
    for a in ALLOWED_CANONICAL:
        assert _BASELINE["allowed_counts"][a] == 1, f"'{a}' count={_BASELINE['allowed_counts'][a]}"


def test_forbidden_reads_zero():
    assert _BASELINE["forbidden_reads"] == [], f"Forbidden: {_BASELINE['forbidden_reads']}"


def test_forbidden_calls_zero():
    assert _BASELINE["forbidden_calls"] == [], f"Calls: {_BASELINE['forbidden_calls']}"


def test_writes_zero():
    assert _BASELINE["writes"] == [], f"Writes: {_BASELINE['writes']}"


# ---- Injection helper ----
def _inject(line):
    lines = _REAL.split("\n")
    fn_start = None
    for i, l in enumerate(lines):
        if f"def {ENTRY_NAME}(" in l: fn_start = i; break
    assert fn_start is not None
    insert = fn_start + 1
    if '"""' in lines[insert]:
        while insert < len(lines):
            s = lines[insert].strip()
            if s.endswith('"""') and s.count('"""') >= 1: insert += 1; break
            insert += 1
    while insert < len(lines) and (not lines[insert].strip() or lines[insert].strip().startswith("#")):
        insert += 1
    return "\n".join(lines[:insert] + [line] + lines[insert:])


# ---- Forbidden injection ----
@pytest.mark.parametrize("prop", sorted(FORBIDDEN_ATTRS))
def test_forbidden_injection(prop):
    r = _analyze(_inject(f"    _{prop} = matched_obj.{prop}"))
    assert len(r["forbidden_reads"]) >= 1, f"{prop} not detected"


# ---- Allowed mutations ----
ACCESS_EXPRESSIONS = {
    "scene.objects": "scene.objects",
    "animation_object.name": "obj.name",
    "animation_object.animation_data": "matched_obj.animation_data",
    "animation_data.action": "ad_cached.action",
    "action.name": "action.name",
    "animation_object.data": "matched_obj.data",
    "data.pose_position": "obj_data.pose_position",
    "scene.frame_current": "scene.frame_current",
}

WRONG_PREFIX_EXPRESSIONS = {
    "scene.objects": "wrong_scene.objects",
    "animation_object.name": "wrong_obj.name",
    "animation_object.animation_data": "wrong_obj.animation_data",
    "animation_data.action": "wrong_ad.action",
    "action.name": "wrong_action.name",
    "animation_object.data": "wrong_obj.data",
    "data.pose_position": "wrong_data.pose_position",
    "scene.frame_current": "wrong_scene.frame_current",
}


def _replace_entry_once(source, old, new):
    tree = ast.parse(source)

    entry = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == ENTRY_NAME
    )

    lines = source.splitlines(keepends=True)
    start = sum(len(line) for line in lines[: entry.lineno - 1])
    end = sum(len(line) for line in lines[: entry.end_lineno])

    entry_source = source[start:end]

    assert entry_source.count(old) == 1, (
        old,
        entry_source.count(old),
    )

    replaced_entry = entry_source.replace(old, new, 1)

    return source[:start] + replaced_entry + source[end:]


def _allowed_valid(result):
    return all(result["allowed_counts"][a] == 1 for a in ALLOWED_CANONICAL)


@pytest.mark.parametrize("attr", ALLOWED_CANONICAL)
def test_allowed_missing_fails(attr):
    source = _replace_entry_once(
        _REAL,
        ACCESS_EXPRESSIONS[attr],
        "None",
    )
    result = _analyze(source)

    assert result["allowed_counts"][attr] == 0
    assert _allowed_valid(result) is False


@pytest.mark.parametrize("attr", ALLOWED_CANONICAL)
def test_allowed_wrong_prefix(attr):
    source = _replace_entry_once(
        _REAL,
        ACCESS_EXPRESSIONS[attr],
        WRONG_PREFIX_EXPRESSIONS[attr],
    )
    result = _analyze(source)

    assert result["allowed_counts"][attr] == 0
    assert _allowed_valid(result) is False


@pytest.mark.parametrize("attr", ALLOWED_CANONICAL)
def test_allowed_duplicate(attr):
    parts = attr.split(".")
    fake_map = {"animation_object": "matched_obj", "animation_data": "ad_cached",
                "action": "action", "data": "obj_data", "scene": "scene"}
    fake = fake_map.get(parts[0], parts[0])
    r = _analyze(_inject(f"    _dup = {fake}.{parts[-1]}"))
    assert r["allowed_counts"][attr] >= 2, f"{attr} duplicate: count={r['allowed_counts'][attr]}"
    assert _allowed_valid(r) is False, f"{attr} duplicate should fail validation"


# ---- 7 fixed probes ----
def test_p1_bpy_ops_two_layer_alias():
    src = _inject("    _f = bpy.ops.wm.open_mainfile\n    _g = _f\n    _g(filepath='/x')")
    r = _analyze(src)
    assert len(r["forbidden_calls"]) >= 1, "2-layer bpy.ops alias not detected"


def test_p2_bpy_data_get_alias():
    src = _inject("    _o = bpy.data.objects\n    _o.get('X')")
    r = _analyze(src)
    assert len(r["forbidden_calls"]) >= 1, "bpy.data.objects.get via object alias not detected"


def test_p3_bpy_data_subscript_multi_alias():
    src = _inject("    _d = bpy.data\n    _o = _d.objects\n    _o['X']")
    r = _analyze(src)
    assert len(r["forbidden_calls"]) >= 1, "multi-layer subscript alias not detected"


def test_p4_obj_alias_write():
    src = _inject("    _o = matched_obj\n    _o.name = 'hacked'")
    r = _analyze(src)
    assert len(r["writes"]) >= 1, "object alias write not detected"


def test_p5_bpy_alias_write():
    src = _inject("    _b = bpy\n    _b.x = 1")
    r = _analyze(src)
    assert len(r["writes"]) >= 1, "bpy alias write not detected"


def test_p6_deep_tuple_write():
    src = _inject("    (matched_obj.x, (matched_obj.y, matched_obj.z)) = (1, (2, 3))")
    r = _analyze(src)
    assert len(r["writes"]) >= 2, f"deep tuple write not detected (found {len(r['writes'])})"


def test_p7_uncalled_lambda_is_clean():
    src = _inject("    _f = lambda o: o.matrix_world")
    r = _analyze(src)
    assert len(r["forbidden_reads"]) == 0, f"Uncalled lambda leaked: {r['forbidden_reads']}"


# ---- Reachability probes ----
def _add_helper(src, fn_name, body):
    return src + f"\n\ndef {fn_name}(o):\n    {body}\n"

def test_helper_forbidden():
    r = _analyze(_add_helper(_inject("    _x = _i5_h(None)"), "_i5_h", "return o.matrix_world"))
    assert len(r["forbidden_reads"]) >= 1

def test_helper_alias():
    src = _inject("    _f = _i5_h\n    _x = _f(None)")
    r = _analyze(_add_helper(src, "_i5_h", "return o.matrix_world"))
    assert len(r["forbidden_reads"]) >= 1

def test_multi_layer():
    src = _inject("    _x = _i5_a(None)")
    src = _add_helper(src, "_i5_a", "return _i5_b(o)")
    src = _add_helper(src, "_i5_b", "return o.matrix_world")
    r = _analyze(src)
    assert len(r["forbidden_reads"]) >= 1

def test_recursive():
    src = _inject("    _x = _i5_r(None)")
    src += "\ndef _i5_r(o):\n    _i5_r(o)\n    return o.matrix_world\n"
    r = _analyze(src)
    assert len(r["forbidden_reads"]) >= 1

def test_uncalled_helper():
    r = _analyze(_add_helper(_REAL, "_i5_u", "return o.matrix_world"))
    assert len(r["forbidden_reads"]) == 0

def test_uncalled_local_class():
    src = _inject("    class _C:\n        def m(self):\n            return self.matrix_world\n    pass")
    r = _analyze(src)
    assert len(r["forbidden_reads"]) == 0

def test_entry_missing():
    r = _analyze("x = 1")
    assert r.get("entry_found") is False
