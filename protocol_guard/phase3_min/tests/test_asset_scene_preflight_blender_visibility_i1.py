"""Tests for 14B-4A Visibility I1 R3: PASS/FAIL/NOT_CHECKED/ERROR.

Corrections:
  F-001: ZIP report filename standardized
  F-004: full outer dict equality + underscore write trap
  F-005: verified change scope evidence
"""
import ast
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

_bpy = types.ModuleType("bpy")
sys.modules["bpy"] = _bpy

from protocol_guard.phase3_min.blender_scene_reader import _check_visibility, _check_root_objects
from protocol_guard.phase3_min.tests.assertions import assert_dict_equal

_UNSET = object()


def _root(vp=False, hr=False, vp_err=False, hr_err=False, write_trap=False):
    """Create a mock root object.

    vp / hr:        values returned by hide_viewport / hide_render
    vp_err / hr_err: if True, reading the property raises RuntimeError
    write_trap:      if True, ALL attribute writes (including _underscore)
                     are recorded in _writes.
    """
    class R:
        type = "EMPTY"

        def __init__(self):
            object.__setattr__(self, "_reads_vp", 0)
            object.__setattr__(self, "_reads_hr", 0)
            object.__setattr__(self, "_writes", [])
            object.__setattr__(self, "_write_trap", write_trap)

        def __setattr__(self, name, value):
            if self._write_trap:
                self._writes.append(name)
            object.__setattr__(self, name, value)

        @property
        def hide_viewport(self):
            object.__setattr__(self, "_reads_vp", self._reads_vp + 1)
            if vp_err:
                raise RuntimeError("viewport read error")
            return vp

        @property
        def hide_render(self):
            object.__setattr__(self, "_reads_hr", self._reads_hr + 1)
            if hr_err:
                raise RuntimeError("render read error")
            return hr

    return R()


def _vis_spec(*, vp=_UNSET, hr=_UNSET, visibility=_UNSET):
    """Build a target dict with visibility configuration.

    visibility=_UNSET  -> no "visibility" key at all  -> {}
    visibility=None    -> "visibility": null
    visibility={}      -> "visibility": {}

    vp=_UNSET  -> field not present in visibility dict
    vp=None    -> "require_not_hidden_viewport": null
    vp=False   -> "require_not_hidden_viewport": false
    vp=True    -> "require_not_hidden_viewport": true
    (same for hr)
    """
    if visibility is _UNSET and vp is _UNSET and hr is _UNSET:
        return {}
    if visibility is None:
        return {"visibility": None}
    d = {}
    if vp is not _UNSET:
        d["require_not_hidden_viewport"] = vp
    if hr is not _UNSET:
        d["require_not_hidden_render"] = hr
    return {"visibility": d}


# ── result shape constants ────────────────────────────────────────────

_NOT_CHECKED_VP = {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"}
_NOT_CHECKED_HR = {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"}
_NOT_CHECKED_RESULT = {
    "result": "NOT_CHECKED",
    "viewport": _NOT_CHECKED_VP,
    "render": _NOT_CHECKED_HR,
}

PASS_VP = {"result": "PASS", "require_not_hidden": True, "actual_hidden": False}
PASS_HR = {"result": "PASS", "require_not_hidden": True, "actual_hidden": False}
DOUBLE_PASS_RESULT = {"result": "PASS", "viewport": PASS_VP, "render": PASS_HR}

FAIL_VP = {"result": "FAIL", "failure_code": "OBJECT_HIDDEN_IN_VIEWPORT",
           "require_not_hidden": True, "actual_hidden": True}
FAIL_HR = {"result": "FAIL", "failure_code": "OBJECT_HIDDEN_IN_RENDER",
           "require_not_hidden": True, "actual_hidden": True}

VP_ERROR = {"result": "ERROR", "error_type": "VISIBILITY_READ_ERROR",
            "operation": "READ_ROOT_HIDE_VIEWPORT", "note": "READ_ROOT_HIDE_VIEWPORT_FAILED"}
HR_ERROR = {"result": "ERROR", "error_type": "VISIBILITY_READ_ERROR",
            "operation": "READ_ROOT_HIDE_RENDER", "note": "READ_ROOT_HIDE_RENDER_FAILED"}


# ═══════════════════════════════════════════════════════════════════════
# NOT_CHECKED
# ═══════════════════════════════════════════════════════════════════════

class TestNotChecked:
    def test_visibility_key_missing(self):
        root = _root(vp=False, hr=False)
        r = _check_visibility({}, root)
        assert_dict_equal(r, _NOT_CHECKED_RESULT)
        assert root._reads_vp == 0
        assert root._reads_hr == 0

    def test_visibility_null(self):
        root = _root(vp=False, hr=False)
        r = _check_visibility({"visibility": None}, root)
        assert_dict_equal(r, _NOT_CHECKED_RESULT)
        assert root._reads_vp == 0
        assert root._reads_hr == 0

    def test_visibility_empty_dict(self):
        root = _root(vp=False, hr=False)
        r = _check_visibility({"visibility": {}}, root)
        assert_dict_equal(r, _NOT_CHECKED_RESULT)
        assert root._reads_vp == 0
        assert root._reads_hr == 0

    def test_vp_null_hr_configured(self):
        root = _root(vp=False, hr=False)
        r = _check_visibility(_vis_spec(vp=None, hr=True), root)
        assert r["result"] == "PASS"
        assert r["viewport"]["result"] == "NOT_CHECKED"
        assert r["viewport"]["note"] == "REQUIREMENT_NOT_CONFIGURED"
        assert r["render"]["result"] == "PASS"
        assert root._reads_vp == 0
        assert root._reads_hr == 1

    def test_hr_null_vp_configured(self):
        root = _root(vp=False, hr=False)
        r = _check_visibility(_vis_spec(vp=True, hr=None), root)
        assert r["result"] == "PASS"
        assert r["viewport"]["result"] == "PASS"
        assert r["render"]["result"] == "NOT_CHECKED"
        assert root._reads_vp == 1
        assert root._reads_hr == 0

    def test_both_null(self):
        root = _root(vp=False, hr=False)
        r = _check_visibility(_vis_spec(vp=None, hr=None), root)
        assert_dict_equal(r, _NOT_CHECKED_RESULT)
        assert root._reads_vp == 0
        assert root._reads_hr == 0

    def test_vp_false(self):
        root = _root(vp=False, hr=False)
        r = _check_visibility(_vis_spec(vp=False, hr=True), root)
        assert r["result"] == "PASS"
        assert r["viewport"]["result"] == "NOT_CHECKED"
        assert root._reads_vp == 0
        assert root._reads_hr == 1

    def test_hr_false(self):
        root = _root(vp=False, hr=False)
        r = _check_visibility(_vis_spec(vp=True, hr=False), root)
        assert r["result"] == "PASS"
        assert r["render"]["result"] == "NOT_CHECKED"
        assert root._reads_vp == 1
        assert root._reads_hr == 0

    def test_both_false(self):
        root = _root(vp=False, hr=False)
        r = _check_visibility(_vis_spec(vp=False, hr=False), root)
        assert_dict_equal(r, _NOT_CHECKED_RESULT)
        assert root._reads_vp == 0
        assert root._reads_hr == 0


# ═══════════════════════════════════════════════════════════════════════
# PASS
# ═══════════════════════════════════════════════════════════════════════

class TestPass:
    def test_both_true_both_visible_full_contract(self):
        root = _root(vp=False, hr=False)
        r = _check_visibility(_vis_spec(vp=True, hr=True), root)
        assert_dict_equal(r, DOUBLE_PASS_RESULT)
        assert root._reads_vp == 1
        assert root._reads_hr == 1

    def test_only_viewport_configured_pass(self):
        root = _root(vp=False)
        r = _check_visibility(_vis_spec(vp=True), root)
        assert r["result"] == "PASS"
        assert r["viewport"]["result"] == "PASS"
        assert r["viewport"]["require_not_hidden"] is True
        assert r["viewport"]["actual_hidden"] is False
        assert r["render"]["result"] == "NOT_CHECKED"
        assert root._reads_vp == 1
        assert root._reads_hr == 0

    def test_only_render_configured_pass(self):
        root = _root(hr=False)
        r = _check_visibility(_vis_spec(hr=True), root)
        assert r["result"] == "PASS"
        assert r["viewport"]["result"] == "NOT_CHECKED"
        assert r["render"]["result"] == "PASS"
        assert r["render"]["require_not_hidden"] is True
        assert r["render"]["actual_hidden"] is False
        assert root._reads_vp == 0
        assert root._reads_hr == 1


# ═══════════════════════════════════════════════════════════════════════
# FAIL
# ═══════════════════════════════════════════════════════════════════════

class TestFail:
    def test_viewport_hidden_full_contract(self):
        root = _root(vp=True, hr=False)
        r = _check_visibility(_vis_spec(vp=True, hr=True), root)
        assert_dict_equal(r["viewport"], FAIL_VP)
        assert_dict_equal(r["render"], PASS_HR)
        assert r["result"] == "FAIL"
        assert root._reads_vp == 1
        assert root._reads_hr == 1

    def test_render_hidden_full_contract(self):
        root = _root(vp=False, hr=True)
        r = _check_visibility(_vis_spec(vp=True, hr=True), root)
        assert_dict_equal(r["viewport"], PASS_VP)
        assert_dict_equal(r["render"], FAIL_HR)
        assert r["result"] == "FAIL"
        assert root._reads_vp == 1
        assert root._reads_hr == 1

    def test_both_hidden(self):
        root = _root(vp=True, hr=True)
        r = _check_visibility(_vis_spec(vp=True, hr=True), root)
        assert r["result"] == "FAIL"
        assert r["viewport"]["result"] == "FAIL"
        assert r["viewport"]["failure_code"] == "OBJECT_HIDDEN_IN_VIEWPORT"
        assert r["render"]["result"] == "FAIL"
        assert r["render"]["failure_code"] == "OBJECT_HIDDEN_IN_RENDER"
        assert root._reads_vp == 1
        assert root._reads_hr == 1


# ═══════════════════════════════════════════════════════════════════════
# ERROR
# ═══════════════════════════════════════════════════════════════════════

class TestError:
    def test_viewport_read_error_full_contract(self):
        root = _root(vp_err=True)
        r = _check_visibility(_vis_spec(vp=True, hr=True), root)
        assert r["result"] == "ERROR"
        assert_dict_equal(r["viewport"], VP_ERROR)
        assert_dict_equal(r["render"], PASS_HR)
        assert root._reads_vp == 1
        assert root._reads_hr == 1

    def test_render_read_error_full_contract(self):
        root = _root(hr_err=True)
        r = _check_visibility(_vis_spec(vp=True, hr=True), root)
        assert r["result"] == "ERROR"
        assert_dict_equal(r["viewport"], PASS_VP)
        assert_dict_equal(r["render"], HR_ERROR)
        assert root._reads_vp == 1
        assert root._reads_hr == 1

    def test_both_read_error(self):
        root = _root(vp_err=True, hr_err=True)
        r = _check_visibility(_vis_spec(vp=True, hr=True), root)
        assert r["result"] == "ERROR"
        assert_dict_equal(r["viewport"], VP_ERROR)
        assert_dict_equal(r["render"], HR_ERROR)
        assert root._reads_vp == 1
        assert root._reads_hr == 1

    def test_vp_error_does_not_block_render_pass(self):
        root = _root(vp_err=True, hr=False)
        r = _check_visibility(_vis_spec(vp=True, hr=True), root)
        assert r["result"] == "ERROR"
        assert r["viewport"]["result"] == "ERROR"
        assert r["render"]["result"] == "PASS"
        assert root._reads_vp == 1
        assert root._reads_hr == 1

    def test_render_error_does_not_block_viewport_pass(self):
        root = _root(vp=False, hr_err=True)
        r = _check_visibility(_vis_spec(vp=True, hr=True), root)
        assert r["result"] == "ERROR"
        assert r["viewport"]["result"] == "PASS"
        assert r["render"]["result"] == "ERROR"
        assert root._reads_vp == 1
        assert root._reads_hr == 1

    def test_only_vp_configured_render_would_error_but_not_read(self):
        root = _root(vp=False, hr_err=True)
        r = _check_visibility(_vis_spec(vp=True), root)
        assert r["result"] == "PASS"
        assert r["viewport"]["result"] == "PASS"
        assert r["render"]["result"] == "NOT_CHECKED"
        assert root._reads_vp == 1
        assert root._reads_hr == 0

    def test_only_hr_configured_viewport_would_error_but_not_read(self):
        root = _root(vp_err=True, hr=False)
        r = _check_visibility(_vis_spec(hr=True), root)
        assert r["result"] == "PASS"
        assert r["viewport"]["result"] == "NOT_CHECKED"
        assert r["render"]["result"] == "PASS"
        assert root._reads_vp == 0
        assert root._reads_hr == 1


# ═══════════════════════════════════════════════════════════════════════
# F-004 — result contract: full outer dict equality
# ═══════════════════════════════════════════════════════════════════════

VP_FAIL_OUTER = {"result": "FAIL", "viewport": FAIL_VP, "render": PASS_HR}
HR_FAIL_OUTER = {"result": "FAIL", "viewport": PASS_VP, "render": FAIL_HR}
VP_ERROR_OUTER = {"result": "ERROR", "viewport": VP_ERROR, "render": PASS_HR}
HR_ERROR_OUTER = {"result": "ERROR", "viewport": PASS_VP, "render": HR_ERROR}
BOTH_ERROR_OUTER = {"result": "ERROR", "viewport": VP_ERROR, "render": HR_ERROR}


class TestResultContract:
    def test_not_checked_full(self):
        r = _check_visibility({}, _root())
        assert_dict_equal(r, _NOT_CHECKED_RESULT)

    def test_double_pass_full(self):
        root = _root(vp=False, hr=False)
        r = _check_visibility(_vis_spec(vp=True, hr=True), root)
        assert_dict_equal(r, DOUBLE_PASS_RESULT)

    def test_viewport_fail_full_outer(self):
        root = _root(vp=True, hr=False)
        r = _check_visibility(_vis_spec(vp=True, hr=True), root)
        assert_dict_equal(r, VP_FAIL_OUTER)

    def test_render_fail_full_outer(self):
        root = _root(vp=False, hr=True)
        r = _check_visibility(_vis_spec(vp=True, hr=True), root)
        assert_dict_equal(r, HR_FAIL_OUTER)

    def test_viewport_error_full_outer(self):
        root = _root(vp_err=True)
        r = _check_visibility(_vis_spec(vp=True, hr=True), root)
        assert_dict_equal(r, VP_ERROR_OUTER)

    def test_render_error_full_outer(self):
        root = _root(hr_err=True)
        r = _check_visibility(_vis_spec(vp=True, hr=True), root)
        assert_dict_equal(r, HR_ERROR_OUTER)

    def test_both_error_full_outer(self):
        root = _root(vp_err=True, hr_err=True)
        r = _check_visibility(_vis_spec(vp=True, hr=True), root)
        assert_dict_equal(r, BOTH_ERROR_OUTER)

    def test_outer_dict_detects_unexpected_field(self):
        """If visibility result gets an unexpected key, assert_dict_equal catches it."""
        root = _root(vp_err=True)
        r = _check_visibility(_vis_spec(vp=True, hr=True), root)
        modified = dict(r)
        modified["unexpected"] = True
        try:
            assert_dict_equal(modified, VP_ERROR_OUTER)
            raise AssertionError("should have detected unexpected key")
        except AssertionError as e:
            assert "extra keys" in str(e) or "unexpected" in str(e)


# ═══════════════════════════════════════════════════════════════════════
# F-004 — read-only boundary (write trap captures all writes)
# ═══════════════════════════════════════════════════════════════════════

class TestReadOnlyBoundary:
    def test_no_writes_during_check(self):
        root = _root(vp=False, hr=False, write_trap=True)
        r = _check_visibility(_vis_spec(vp=True, hr=True), root)
        assert_dict_equal(r, DOUBLE_PASS_RESULT)
        assert root._writes == [], f"unexpected writes: {root._writes}"
        assert root._reads_vp == 1
        assert root._reads_hr == 1

    def test_no_writes_even_on_fail(self):
        root = _root(vp=True, hr=True, write_trap=True)
        r = _check_visibility(_vis_spec(vp=True, hr=True), root)
        assert r["result"] == "FAIL"
        assert root._writes == [], f"unexpected writes: {root._writes}"
        assert root._reads_vp == 1
        assert root._reads_hr == 1

    def test_no_writes_even_on_error(self):
        root = _root(vp_err=True, hr_err=True, write_trap=True)
        r = _check_visibility(_vis_spec(vp=True, hr=True), root)
        assert r["result"] == "ERROR"
        assert root._writes == [], f"unexpected writes: {root._writes}"
        assert root._reads_vp == 1
        assert root._reads_hr == 1

    def test_underscore_write_is_trapped(self):
        """Prove that underscore-prefixed writes ARE captured by the trap."""
        root = _root(vp=False, hr=False, write_trap=True)
        root._secret_field = "should be trapped"
        assert "_secret_field" in root._writes, (
            f"underscore write NOT trapped; writes: {root._writes}"
        )


# ═══════════════════════════════════════════════════════════════════════
# Read-once
# ═══════════════════════════════════════════════════════════════════════

class TestReadOnce:
    def test_each_read_at_most_once(self):
        root = _root(vp=False, hr=False)
        _check_visibility(_vis_spec(vp=True, hr=True), root)
        assert root._reads_vp == 1, f"vp read {root._reads_vp} times"
        assert root._reads_hr == 1, f"hr read {root._reads_hr} times"

    def test_unconfigured_not_read(self):
        root = _root(vp=False, hr=False)
        _check_visibility(_vis_spec(vp=True), root)
        assert root._reads_vp == 1
        assert root._reads_hr == 0

    def test_neither_configured_neither_read(self):
        root = _root(vp=False, hr=False)
        _check_visibility({}, root)
        assert root._reads_vp == 0
        assert root._reads_hr == 0

    def test_repeated_call_reads_again(self):
        root = _root(vp=False, hr=False)
        _check_visibility(_vis_spec(vp=True, hr=True), root)
        _check_visibility(_vis_spec(vp=True, hr=True), root)
        assert root._reads_vp == 2
        assert root._reads_hr == 2


# ═══════════════════════════════════════════════════════════════════════
# Integration — root-not-found path
# ═══════════════════════════════════════════════════════════════════════

class TestIntegration:
    def test_root_not_found_visibility_not_checked(self):
        td = __import__("tempfile").TemporaryDirectory()
        try:
            script = f'''
import sys, os, types
sys.path.insert(0, r"{os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))}")
_bpy=types.ModuleType("bpy"); sys.modules["bpy"]=_bpy
from protocol_guard.phase3_min.blender_scene_reader import _check_root_objects
class FS:
    def __init__(self, objs): self.objects=list(objs)
results=_check_root_objects(FS([]), [{{"target_id":"A","root_object_name":"R","expected_root_type":"EMPTY","visibility":{{"require_not_hidden_viewport":True}}}}])
v=results[0]["checks"]["visibility"]
assert v["result"]=="NOT_CHECKED", f"expected NOT_CHECKED got {{v['result']}}"
assert v["viewport"]["note"]=="ROOT_OBJECT_NOT_FOUND", f"got {{v['viewport']['note']}}"
assert v["render"]["note"]=="ROOT_OBJECT_NOT_FOUND", f"got {{v['render']['note']}}"
assert v["viewport"]["result"]=="NOT_CHECKED"
assert v["render"]["result"]=="NOT_CHECKED"
vk=set(v.keys())
assert vk=={{"result","viewport","render"}}, f"extra/missing keys in root-not-found visibility: {{vk}}"
print("PASS=OK")
'''
            sf = os.path.join(td.name, "run.py")
            with open(sf, "w") as f:
                f.write(script)
            r = __import__("subprocess").run(["python", sf], capture_output=True, text=True)
            assert r.returncode == 0 and "PASS=OK" in r.stdout, f"FAILED: {r.stdout} {r.stderr}"
        finally:
            td.cleanup()


# ═══════════════════════════════════════════════════════════════════════
# Self-integrity checks
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
                    raise AssertionError(f"line {node.lineno}: {node.func.attr}() not allowed")
            elif isinstance(node.func, ast.Name):
                if node.func.id in ("skip", "skipif", "xfail", "importorskip"):
                    raise AssertionError(f"line {node.lineno}: {node.func.id}() not allowed")
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Attribute) and dec.attr in ("skip", "skipif", "xfail", "importorskip"):
                    raise AssertionError(f"line {dec.lineno}: @{dec.attr} not allowed")
                if isinstance(dec, ast.Name) and dec.id in ("skip", "skipif", "xfail", "importorskip"):
                    raise AssertionError(f"line {dec.lineno}: @{dec.id} not allowed")
