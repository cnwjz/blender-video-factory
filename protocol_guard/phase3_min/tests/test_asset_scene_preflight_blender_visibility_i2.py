"""Tests for 14B-4A Visibility I2 R2: static scope guard for _check_visibility.

Enforces root-only, read-only visibility boundaries.
"""
import ast
import os
import sys
import tempfile
import textwrap

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

READER_PATH = os.path.join(ROOT, "protocol_guard", "phase3_min", "blender_scene_reader.py")

VISIBILITY_ATTRS = {"hide_viewport", "hide_render"}
VISIBILITY_SUB_KEYS = {"require_not_hidden_viewport", "require_not_hidden_render"}
FORBIDDEN_SCOPE = {
    "children", "parent", "descendants", "data",
    "material_slots", "animation_data", "users_collection", "collections",
    "matrix_world", "bound_box", "evaluated_get", "evaluated_depsgraph_get",
    "to_mesh", "location", "rotation_euler",
    "rotation_quaternion",
}
FORBIDDEN_CALL_NAMES = {
    "render", "save", "save_mainfile", "save_as_mainfile", "open_mainfile",
}


def _attr_chain(node):
    parts = []
    cur = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return list(reversed(parts))
    return None


# ── Scope Analyzer ────────────────────────────────────────────────────

class VisibilityScopeAnalyzer:
    def __init__(self, reader_path):
        with open(reader_path, encoding="utf-8") as f:
            self.reader_tree = ast.parse(f.read(), filename=reader_path)

    @staticmethod
    def _is_func(node):
        return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))

    def _top_funcs(self):
        return {n.name: n for n in ast.iter_child_nodes(self.reader_tree) if self._is_func(n)}

    def _walk_scope_aware(self, node):
        yield node
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                continue
            yield from self._walk_scope_aware(child)

    def _param_names(self, fn):
        names = {a.arg for a in fn.args.args}
        if fn.args.vararg:
            names.add(fn.args.vararg.arg)
        return names

    def _collect_vis_aliases(self, fn_node, params):
        """Track variables assigned from target.get('visibility') and their plain aliases.

        Returns set of variable names that hold the visibility dict.
        """
        aliases = set()
        for node in self._walk_scope_aware(fn_node):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        # vis = target.get("visibility")
                        if (isinstance(node.value, ast.Call)
                                and isinstance(node.value.func, ast.Attribute)
                                and node.value.func.attr == "get"
                                and isinstance(node.value.func.value, ast.Name)
                                and node.value.func.value.id == "target"
                                and node.value.args
                                and isinstance(node.value.args[0], ast.Constant)
                                and node.value.args[0].value == "visibility"):
                            aliases.add(t.id)
                        # plain alias: x = vis  (where vis is already an alias)
                        elif (isinstance(node.value, ast.Name)
                              and node.value.id in aliases):
                            aliases.add(t.id)
        return aliases

    # ── F-001: root_obj only reads ─────────────────────────────────────

    def check_root_obj_reads(self):
        """Verify hide_viewport/hide_render are only read on root_obj param.

        Returns list of violation strings.
        """
        funcs = self._top_funcs()
        fn = funcs.get("_check_visibility")
        if fn is None:
            return ["_check_visibility not found"]
        params = self._param_names(fn)
        violations = []
        root_loads_vp = 0
        root_loads_hr = 0

        for node in self._walk_scope_aware(fn):
            if isinstance(node, ast.Attribute) and node.attr in VISIBILITY_ATTRS:
                if isinstance(node.ctx, ast.Load):
                    # Is the receiver root_obj?
                    if isinstance(node.value, ast.Name) and node.value.id == "root_obj":
                        if node.attr == "hide_viewport":
                            root_loads_vp += 1
                        elif node.attr == "hide_render":
                            root_loads_hr += 1
                    else:
                        violations.append(
                            f"NON_ROOT_VISIBILITY_READ: {node.attr} on non-root_obj "
                            f"(line {node.lineno})"
                        )

        if root_loads_vp != 1:
            violations.append(f"ROOT_VP_LOAD_COUNT: {root_loads_vp} (expected 1)")
        if root_loads_hr != 1:
            violations.append(f"ROOT_HR_LOAD_COUNT: {root_loads_hr} (expected 1)")

        return violations

    def check_other_functions_no_visibility_reads(self):
        """Verify no other top-level function reads hide_viewport/hide_render."""
        funcs = self._top_funcs()
        violations = []
        for name, fn in funcs.items():
            if name == "_check_visibility":
                continue
            for node in self._walk_scope_aware(fn):
                if isinstance(node, ast.Attribute) and node.attr in VISIBILITY_ATTRS:
                    if isinstance(node.ctx, ast.Load):
                        violations.append(
                            f"OTHER_FUNC_READ: {name} reads {node.attr} (line {node.lineno})"
                        )
        return violations

    # ── F-002: setattr/delattr detection ───────────────────────────────

    def check_visibility_writes(self):
        """Detect Store, Del, AugAssign, setattr, delattr on visibility attrs.

        Scans entire reader tree.
        """
        violations = []
        funcs = self._top_funcs()
        fn = funcs.get("_check_visibility")
        check_fn = fn

        for node in ast.walk(self.reader_tree):
            # Attribute Store/Del
            if isinstance(node, ast.Attribute) and node.attr in VISIBILITY_ATTRS:
                if isinstance(node.ctx, (ast.Store, ast.Del)):
                    violations.append(
                        f"VISIBILITY_WRITE: {node.attr} {type(node.ctx).__name__} "
                        f"(line {node.lineno})"
                    )
            # AugAssign
            if isinstance(node, ast.AugAssign):
                if isinstance(node.target, ast.Attribute) and node.target.attr in VISIBILITY_ATTRS:
                    violations.append(
                        f"VISIBILITY_WRITE: {node.target.attr} AugAssign (line {node.lineno})"
                    )
            # setattr(x, "hide_viewport", ...) or setattr(x, "hide_render", ...)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "setattr" and len(node.args) >= 2:
                    a1 = node.args[1]
                    if isinstance(a1, ast.Constant) and a1.value in VISIBILITY_ATTRS:
                        violations.append(
                            f"VISIBILITY_WRITE: setattr({a1.value!r}) (line {node.lineno})"
                        )
            # delattr(x, "hide_viewport") or delattr(x, "hide_render")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "delattr" and node.args:
                    a1 = node.args[0] if len(node.args) >= 2 else None
                    if a1 is None:
                        # delattr(x, "hide_viewport") has the attr as second arg
                        # Actually: delattr(obj, name) — second arg
                        pass
                    # Correct: delattr(obj, name) — check second arg
                if node.func.id == "delattr" and len(node.args) >= 2:
                    a1 = node.args[1]
                    if isinstance(a1, ast.Constant) and a1.value in VISIBILITY_ATTRS:
                        violations.append(
                            f"VISIBILITY_WRITE: delattr({a1.value!r}) (line {node.lineno})"
                        )
        return violations

    # ── F-003: target key + vis alias tracking ─────────────────────────

    def check_target_keys(self):
        """Verify target.get/key access uses literal 'visibility', no dynamic keys."""
        funcs = self._top_funcs()
        fn = funcs.get("_check_visibility")
        if fn is None:
            return ["_check_visibility not found"]
        violations = []

        for node in self._walk_scope_aware(fn):
            # target.get(key)
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "get"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "target"
                    and node.args):
                a0 = node.args[0]
                if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
                    if a0.value != "visibility":
                        violations.append(
                            f"TARGET_WRONG_KEY: target.get({a0.value!r}) (line {node.lineno})"
                        )
                else:
                    violations.append(
                        f"TARGET_DYNAMIC_KEY: target.get(...) non-literal (line {node.lineno})"
                    )
            # target[key]
            if (isinstance(node, ast.Subscript)
                    and isinstance(node.value, ast.Name)
                    and node.value.id == "target"
                    and isinstance(node.ctx, ast.Load)):
                if isinstance(node.slice, ast.Constant):
                    if node.slice.value != "visibility":
                        violations.append(
                            f"TARGET_WRONG_KEY: target[{node.slice.value!r}] (line {node.lineno})"
                        )
                else:
                    violations.append(
                        f"TARGET_DYNAMIC_KEY: target[...] non-literal (line {node.lineno})"
                    )

        return violations

    def check_vis_keys(self):
        """Verify visibility-dict variables only read allowed sub-keys with literals."""
        funcs = self._top_funcs()
        fn = funcs.get("_check_visibility")
        if fn is None:
            return ["_check_visibility not found"]
        params = self._param_names(fn)
        vis_aliases = self._collect_vis_aliases(fn, params)
        violations = []

        for node in self._walk_scope_aware(fn):
            # x.get(key) where x is a vis alias
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "get"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id in vis_aliases
                    and node.args):
                a0 = node.args[0]
                if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
                    if a0.value not in VISIBILITY_SUB_KEYS:
                        violations.append(
                            f"VIS_INVALID_KEY: get({a0.value!r}) (line {node.lineno})"
                        )
                else:
                    violations.append(
                        f"VIS_DYNAMIC_KEY: get(...) non-literal (line {node.lineno})"
                    )
            # x[key] where x is a vis alias
            if (isinstance(node, ast.Subscript)
                    and isinstance(node.value, ast.Name)
                    and node.value.id in vis_aliases
                    and isinstance(node.ctx, ast.Load)):
                if isinstance(node.slice, ast.Constant):
                    if node.slice.value not in VISIBILITY_SUB_KEYS:
                        violations.append(
                            f"VIS_INVALID_KEY: [{node.slice.value!r}] (line {node.lineno})"
                        )
                else:
                    violations.append(
                        f"VIS_DYNAMIC_KEY: [...] non-literal (line {node.lineno})"
                    )

        return violations

    # ── F-004: forbidden calls ─────────────────────────────────────────

    def check_forbidden_calls(self):
        """Detect bare calls to render, save, etc. + bpy.ops + forbidden scope."""
        funcs = self._top_funcs()
        fn = funcs.get("_check_visibility")
        if fn is None:
            return ["_check_visibility not found"]
        violations = []

        for node in self._walk_scope_aware(fn):
            # Bare Name calls: render(), save(), etc.
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in FORBIDDEN_CALL_NAMES:
                    violations.append(
                        f"FORBIDDEN_CALL: {node.func.id}() (line {node.lineno})"
                    )
            # Attribute calls: obj.render(), etc.
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in FORBIDDEN_CALL_NAMES:
                    violations.append(
                        f"FORBIDDEN_CALL: .{node.func.attr}() (line {node.lineno})"
                    )
                # bpy.ops.*
                chain = _attr_chain(node.func)
                if chain and chain[0] == "bpy" and len(chain) >= 2 and chain[1] == "ops":
                    violations.append(
                        f"BPY_OPS: bpy.ops.{'.'.join(chain[2:])} (line {node.lineno})"
                    )
            # Forbidden scope access
            if isinstance(node, ast.Attribute):
                if node.attr in FORBIDDEN_SCOPE and isinstance(node.ctx, ast.Load):
                    violations.append(
                        f"FORBIDDEN_ACCESS: {node.attr} (line {node.lineno})"
                    )
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in FORBIDDEN_SCOPE:
                    violations.append(
                        f"FORBIDDEN_CALL: {node.func.attr}() (line {node.lineno})"
                    )

        return violations

    # ── Aggregate ──────────────────────────────────────────────────────

    def analyze_production(self):
        violations = []
        violations.extend(self.check_root_obj_reads())
        violations.extend(self.check_other_functions_no_visibility_reads())
        violations.extend(self.check_visibility_writes())
        violations.extend(self.check_target_keys())
        violations.extend(self.check_vis_keys())
        violations.extend(self.check_forbidden_calls())
        return violations

    def function_exists(self):
        return "_check_visibility" in self._top_funcs()


# ── Snippet analyzer for adversarial tests ────────────────────────────

def _analyze_snippet(code, entry_name, params=None):
    """Create a fake reader with only the given code, then analyze.

    params: comma-separated string like "target,root_obj" so the analyzer
    can find them as function arguments.
    """
    tree = ast.parse(textwrap.dedent(code))
    # Build a temp file so the analyzer can read it
    a = VisibilityScopeAnalyzer.__new__(VisibilityScopeAnalyzer)
    a.reader_tree = tree
    return a.analyze_production()


# ═══════════════════════════════════════════════════════════════════════
# Production tests
# ═══════════════════════════════════════════════════════════════════════

class TestProduction:
    def test_function_exists(self):
        a = VisibilityScopeAnalyzer(READER_PATH)
        assert a.function_exists()

    def test_scope_guard_clean(self):
        a = VisibilityScopeAnalyzer(READER_PATH)
        violations = a.analyze_production()
        assert violations == [], f"Violations: {violations}"

    def test_root_vp_load_is_1(self):
        a = VisibilityScopeAnalyzer(READER_PATH)
        v = a.check_root_obj_reads()
        assert "ROOT_VP_LOAD_COUNT" not in " ".join(v), f"vp load count wrong: {v}"

    def test_root_hr_load_is_1(self):
        a = VisibilityScopeAnalyzer(READER_PATH)
        v = a.check_root_obj_reads()
        assert "ROOT_HR_LOAD_COUNT" not in " ".join(v), f"hr load count wrong: {v}"

    def test_no_other_func_reads(self):
        a = VisibilityScopeAnalyzer(READER_PATH)
        v = a.check_other_functions_no_visibility_reads()
        assert v == [], f"Other func reads: {v}"

    def test_no_writes(self):
        a = VisibilityScopeAnalyzer(READER_PATH)
        v = a.check_visibility_writes()
        assert v == [], f"Writes: {v}"

    def test_target_keys_clean(self):
        a = VisibilityScopeAnalyzer(READER_PATH)
        v = a.check_target_keys()
        assert v == [], f"Target key violations: {v}"

    def test_vis_keys_clean(self):
        a = VisibilityScopeAnalyzer(READER_PATH)
        v = a.check_vis_keys()
        assert v == [], f"Vis key violations: {v}"

    def test_no_forbidden_calls(self):
        a = VisibilityScopeAnalyzer(READER_PATH)
        v = a.check_forbidden_calls()
        assert v == [], f"Forbidden calls: {v}"


# ═══════════════════════════════════════════════════════════════════════
# Adversarial probes
# ═══════════════════════════════════════════════════════════════════════

_BASELINE = """
def _check_visibility(target, root_obj):
    vis = target.get("visibility")
    if not isinstance(vis, dict):
        return {"result": "NOT_CHECKED"}
    req_vp = vis.get("require_not_hidden_viewport")
    req_hr = vis.get("require_not_hidden_render")
    vp_cache = None
    hr_cache = None
    if req_vp is True:
        vp_cache = root_obj.hide_viewport
    if req_hr is True:
        hr_cache = root_obj.hide_render
    return {"result": "PASS"}
"""


class TestAdversarial:
    def test_non_root_hide_viewport_detected(self):
        code = _BASELINE + """
def _check_visibility(target, root_obj):
    vis = target.get("visibility")
    other = type('obj', (), {'hide_viewport': False})()
    x = other.hide_viewport
    return {"result": "PASS"}
"""
        v = _analyze_snippet(code, "_check_visibility")
        assert any("NON_ROOT_VISIBILITY_READ" in m for m in v), f"not detected: {v}"

    def test_non_root_hide_render_detected(self):
        code = _BASELINE + """
def _check_visibility(target, root_obj):
    vis = target.get("visibility")
    other = type('obj', (), {'hide_render': False})()
    x = other.hide_render
    return {"result": "PASS"}
"""
        v = _analyze_snippet(code, "_check_visibility")
        assert any("NON_ROOT_VISIBILITY_READ" in m for m in v), f"not detected: {v}"

    def test_setattr_hide_render_detected(self):
        code = _BASELINE + """
def _check_visibility(target, root_obj):
    vis = target.get("visibility")
    req_vp = vis.get("require_not_hidden_viewport")
    req_hr = vis.get("require_not_hidden_render")
    vp_cache = root_obj.hide_viewport if req_vp is True else None
    hr_cache = root_obj.hide_render if req_hr is True else None
    setattr(root_obj, "hide_render", True)
    return {"result": "PASS"}
"""
        v = _analyze_snippet(code, "_check_visibility")
        assert any("VISIBILITY_WRITE" in m and "setattr('hide_render')" in m
                   for m in v), f"setattr not detected: {v}"

    def test_delattr_hide_viewport_detected(self):
        code = _BASELINE + """
def _check_visibility(target, root_obj):
    vis = target.get("visibility")
    req_vp = vis.get("require_not_hidden_viewport")
    req_hr = vis.get("require_not_hidden_render")
    vp_cache = root_obj.hide_viewport if req_vp is True else None
    hr_cache = root_obj.hide_render if req_hr is True else None
    delattr(root_obj, "hide_viewport")
    return {"result": "PASS"}
"""
        v = _analyze_snippet(code, "_check_visibility")
        assert any("VISIBILITY_WRITE" in m and "delattr('hide_viewport')" in m
                   for m in v), f"delattr not detected: {v}"

    def test_dynamic_target_key_detected(self):
        code = """
def _check_visibility(target, root_obj):
    key = "visibility"
    vis = target.get(key)
    return {"result": "PASS"}
"""
        v = _analyze_snippet(code, "_check_visibility")
        assert any("TARGET_DYNAMIC_KEY" in m for m in v), f"not detected: {v}"

    def test_vis_alias_invalid_key_detected(self):
        code = _BASELINE + """
def _check_visibility(target, root_obj):
    vis = target.get("visibility")
    vp_cache = root_obj.hide_viewport
    hr_cache = root_obj.hide_render
    alias = vis
    val = alias.get("forbidden_key")
    return {"result": "PASS"}
"""
        v = _analyze_snippet(code, "_check_visibility")
        assert any("VIS_INVALID_KEY" in m and "forbidden_key" in m
                   for m in v), f"alias invalid key not detected: {v}"

    def test_bare_render_detected(self):
        code = _BASELINE + """
def _check_visibility(target, root_obj):
    vis = target.get("visibility")
    vp_cache = root_obj.hide_viewport if vis.get("require_not_hidden_viewport") is True else None
    hr_cache = root_obj.hide_render if vis.get("require_not_hidden_render") is True else None
    render()
    return {"result": "PASS"}
"""
        v = _analyze_snippet(code, "_check_visibility")
        assert any("FORBIDDEN_CALL" in m and "render" in m for m in v), f"not detected: {v}"

    def test_bare_save_detected(self):
        code = _BASELINE + """
def _check_visibility(target, root_obj):
    vis = target.get("visibility")
    vp_cache = root_obj.hide_viewport if vis.get("require_not_hidden_viewport") is True else None
    hr_cache = root_obj.hide_render if vis.get("require_not_hidden_render") is True else None
    save()
    return {"result": "PASS"}
"""
        v = _analyze_snippet(code, "_check_visibility")
        assert any("FORBIDDEN_CALL" in m and "save" in m for m in v), f"not detected: {v}"

    def test_bare_open_mainfile_detected(self):
        code = _BASELINE + """
def _check_visibility(target, root_obj):
    vis = target.get("visibility")
    vp_cache = root_obj.hide_viewport if vis.get("require_not_hidden_viewport") is True else None
    hr_cache = root_obj.hide_render if vis.get("require_not_hidden_render") is True else None
    open_mainfile()
    return {"result": "PASS"}
"""
        v = _analyze_snippet(code, "_check_visibility")
        assert any("FORBIDDEN_CALL" in m and "open_mainfile" in m for m in v), f"not detected: {v}"

    def test_clean_baseline_has_no_violations(self):
        v = _analyze_snippet(_BASELINE, "_check_visibility")
        assert v == [], f"clean baseline flagged: {v}"


# ═══════════════════════════════════════════════════════════════════════
# Self-integrity
# ═══════════════════════════════════════════════════════════════════════

def test_test_file_self_parse():
    with open(__file__, "r", encoding="utf-8") as f:
        ast.parse(f.read())


def test_test_file_no_skip_xfail():
    with open(__file__, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in ("skip", "skipif", "xfail", "importorskip"):
                    raise AssertionError(f"line {node.lineno}: {node.func.attr}()")
            elif isinstance(node.func, ast.Name):
                if node.func.id in ("skip", "skipif", "xfail", "importorskip"):
                    raise AssertionError(f"line {node.lineno}: {node.func.id}()")
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            for dec in node.decorator_list:
                name = None
                if isinstance(dec, ast.Attribute):
                    name = dec.attr
                elif isinstance(dec, ast.Name):
                    name = dec.id
                if name in ("skip", "skipif", "xfail", "importorskip"):
                    raise AssertionError(f"line {dec.lineno}: @{name}")
