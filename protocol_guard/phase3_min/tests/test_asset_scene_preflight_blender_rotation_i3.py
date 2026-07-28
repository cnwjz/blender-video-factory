"""Tests for Rotation I3 R3: exact contracts + real helper integration."""
import ast
import math
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

import pytest

_mu = sys.modules["mathutils"]
class _FakeEuler:
    def __init__(self, angles, order):
        self.angles = tuple(angles); self.order = order
    def to_quaternion(self):
        import math as _m
        hx, hy, hz = self.angles[0]/2, self.angles[1]/2, self.angles[2]/2
        cx = _m.cos(hx); sx = _m.sin(hx)
        cy = _m.cos(hy); sy = _m.sin(hy)
        cz = _m.cos(hz); sz = _m.sin(hz)
        class Q: pass
        q = Q()
        q.w = cx*cy*cz - sx*sy*sz
        q.x = sx*cy*cz + cx*sy*sz
        q.y = cx*sy*cz - sx*cy*sz
        q.z = cx*cy*sz + sx*sy*cz
        q.normalize = lambda: None
        return q

@pytest.fixture(autouse=True)
def _setup_i3_euler():
    """Save Euler, set FakeEuler, restore via try/yield/finally."""
    import sys as _sys
    _mu2 = _sys.modules["mathutils"]
    # ── Save ──
    _had_euler = "Euler" in _mu2.__dict__
    _saved_euler = _mu2.__dict__.get("Euler")
    # ── Setup ──
    _mu2.__dict__["Euler"] = _FakeEuler
    try:
        yield
    finally:
        if _had_euler:
            _mu2.__dict__["Euler"] = _saved_euler
        else:
            _mu2.__dict__.pop("Euler", None)

import protocol_guard.phase3_min.asset_scene_preflight_core as core
from protocol_guard.phase3_min.blender_scene_reader import _check_rotation
from protocol_guard.phase3_min.asset_scene_preflight_check import _collect_target_errors

_PASS_KEYS = {"result", "expected_world_rotation_euler_degrees",
              "expected_quaternion", "actual_quaternion",
              "angle_degrees", "tolerance_degrees"}
_FAIL_KEYS = _PASS_KEYS | {"failure_code"}
_ERROR_KEYS = {"result", "error_type", "operation", "note"}

def _valid_spec(erw=(0,0,0), tol=2.0):
    return {"rotation": {"expected_world_rotation_euler_degrees": list(erw),
                          "rotation_tolerance_degrees": tol}}

def _obj(to_quat_tuple=(1.0, 0.0, 0.0, 0.0)):
    class _FakeMW:
        def to_quaternion(self):
            class Q: pass
            q = Q()
            q.w, q.x, q.y, q.z = to_quat_tuple
            return q
    class Obj:
        type = "EMPTY"
        @property
        def matrix_world(self): return _FakeMW()
    return Obj()

def _mock_helper(return_value):
    capture = {"calls": 0, "actuals": [], "expecteds": []}
    orig = core.quaternion_min_angle_degrees
    def _w(actual, expected):
        capture["calls"] += 1; capture["actuals"].append(actual); capture["expecteds"].append(expected)
        return return_value
    core.quaternion_min_angle_degrees = _w
    return capture, orig


# ── F-001: Exact error collection list assertions ─────────────────────

class TestErrorCollection:
    def test_viewport_rotation_exact_list(self):
        r = _err_result(viewport_error="READ_ROOT_HIDE_VIEWPORT", render_error=None,
                        rotation_error="COMPUTE_ROTATION_ANGLE")
        errs = _collect_target_errors([r])
        assert errs == [
            "VISIBILITY_READ_ERROR: target 't1' root_object_name 'Root' operation 'READ_ROOT_HIDE_VIEWPORT'",
            "ROTATION_COMPUTATION_ERROR: target 't1' root_object_name 'Root' operation 'COMPUTE_ROTATION_ANGLE'",
        ]

    def test_render_rotation_exact_list(self):
        r = _err_result(viewport_error=None, render_error="READ_ROOT_HIDE_RENDER",
                        rotation_error="COMPUTE_ROTATION_ANGLE")
        errs = _collect_target_errors([r])
        assert errs == [
            "VISIBILITY_READ_ERROR: target 't1' root_object_name 'Root' operation 'READ_ROOT_HIDE_RENDER'",
            "ROTATION_COMPUTATION_ERROR: target 't1' root_object_name 'Root' operation 'COMPUTE_ROTATION_ANGLE'",
        ]

    def test_both_visibility_rotation_exact_list(self):
        r = _err_result(viewport_error="READ_ROOT_HIDE_VIEWPORT",
                        render_error="READ_ROOT_HIDE_RENDER",
                        rotation_error="COMPUTE_ROTATION_ANGLE")
        errs = _collect_target_errors([r])
        assert errs == [
            "VISIBILITY_READ_ERROR: target 't1' root_object_name 'Root' operation 'READ_ROOT_HIDE_VIEWPORT'",
            "VISIBILITY_READ_ERROR: target 't1' root_object_name 'Root' operation 'READ_ROOT_HIDE_RENDER'",
            "ROTATION_COMPUTATION_ERROR: target 't1' root_object_name 'Root' operation 'COMPUTE_ROTATION_ANGLE'",
        ]

    def test_all_preexisting_errors_preserved_exact(self):
        r = {
            "target_id": "t1", "root_object_name": "Root",
            "checks": {
                "object_exists": {"result": "ERROR", "error_type": "AMBIGUOUS_ROOT_OBJECT_NAME", "match_count": 3},
                "direct_children": {"result": "ERROR", "error_type": "DIRECT_CHILD_LOOKUP_ERROR", "operation": "READ_CHILDREN_BBOX"},
                "descendants": {"result": "ERROR", "error_type": "DESCENDANT_LOOKUP_ERROR", "operation": "DESCENDANT_TRAVERSAL"},
                "standing": {"up_axis": {"result": "ERROR", "operation": "READ_ROOT_MATRIX_WORLD"}},
                "facing": {"forward_axis": {"result": "ERROR", "operation": "READ_ROOT_MATRIX_WORLD"}},
                "visibility": {"viewport": {"result": "PASS"}, "render": {"result": "PASS"}},
                "rotation": {"result": "NOT_CHECKED"},
            },
            "overall": "ERROR",
        }
        errs = _collect_target_errors([r])
        assert errs == [
            "AMBIGUOUS_ROOT_OBJECT_NAME: target 't1' root_object_name 'Root' has 3 matches",
            "DIRECT_CHILD_LOOKUP_ERROR: target 't1' root_object_name 'Root' operation 'READ_CHILDREN_BBOX'",
            "DESCENDANT_LOOKUP_ERROR: target 't1' root_object_name 'Root' operation 'DESCENDANT_TRAVERSAL'",
            "STANDING_UP_AXIS_ERROR: target 't1' root_object_name 'Root' operation 'READ_ROOT_MATRIX_WORLD'",
            "FACING_FORWARD_AXIS_ERROR: target 't1' root_object_name 'Root' operation 'READ_ROOT_MATRIX_WORLD'",
        ]


def _err_result(viewport_error=None, render_error=None, rotation_error=None):
    vis = {}
    if viewport_error:
        vis["viewport"] = {"result": "ERROR", "operation": viewport_error}
    else:
        vis["viewport"] = {"result": "PASS"}
    if render_error:
        vis["render"] = {"result": "ERROR", "operation": render_error}
    else:
        vis["render"] = {"result": "PASS"}
    rot = {"result": "ERROR", "operation": rotation_error} if rotation_error else {"result": "NOT_CHECKED"}
    return {
        "target_id": "t1", "root_object_name": "Root",
        "checks": {
            "object_exists": {"result": "PASS"},
            "direct_children": {"result": "PASS"},
            "descendants": {"result": "PASS"},
            "standing": {"up_axis": {"result": "PASS"}},
            "facing": {"forward_axis": {"result": "PASS"}},
            "visibility": vis,
            "rotation": rot,
        },
        "overall": "ERROR" if rotation_error else "PASS",
    }


# ── F-002: Helper params + real integration ──────────────────────────

class TestHelperParams:
    def test_helper_receives_exact_args(self):
        """actual=(0,1,0,0), expected Euler (0,0,0) -> expected (1,0,0,0)."""
        cap, orig = _mock_helper(0.0)
        try:
            _check_rotation(_valid_spec(erw=(0,0,0)), _obj(to_quat_tuple=(0.0, 1.0, 0.0, 0.0)))
            assert cap["calls"] == 1
            assert cap["actuals"] == [(0.0, 1.0, 0.0, 0.0)]
            assert cap["expecteds"] == [(1.0, 0.0, 0.0, 0.0)]
        finally:
            core.quaternion_min_angle_degrees = orig

    def test_under_tolerance_pass(self):
        cap, orig = _mock_helper(1.5)
        try:
            assert _check_rotation(_valid_spec(tol=2.0), _obj())["result"] == "PASS"
        finally: core.quaternion_min_angle_degrees = orig

    def test_equal_tolerance_pass(self):
        cap, orig = _mock_helper(2.0)
        try:
            assert _check_rotation(_valid_spec(tol=2.0), _obj())["result"] == "PASS"
        finally: core.quaternion_min_angle_degrees = orig

    def test_over_tolerance_fail(self):
        cap, orig = _mock_helper(3.0)
        try:
            r = _check_rotation(_valid_spec(tol=2.0), _obj())
            assert r["result"] == "FAIL"
            assert r["failure_code"] == "OBJECT_ROTATION_OUT_OF_TOLERANCE"
        finally: core.quaternion_min_angle_degrees = orig


class TestRealHelperIntegration:
    def test_q_neg_q_is_zero(self):
        r = _check_rotation(_valid_spec(erw=(0,0,0), tol=0.0),
                            _obj(to_quat_tuple=(-1.0, 0.0, 0.0, 0.0)))
        assert r["result"] == "PASS"
        assert r["angle_degrees"] == 0.0

    def test_180_degree_below_tolerance_fail(self):
        r = _check_rotation(_valid_spec(erw=(0,0,0), tol=179.0),
                            _obj(to_quat_tuple=(0.0, 1.0, 0.0, 0.0)))
        assert r["result"] == "FAIL"
        assert r["angle_degrees"] == 180.0

    def test_180_degree_equal_tolerance_pass(self):
        r = _check_rotation(_valid_spec(erw=(0,0,0), tol=180.0),
                            _obj(to_quat_tuple=(0.0, 1.0, 0.0, 0.0)))
        assert r["result"] == "PASS"
        assert r["angle_degrees"] == 180.0


# ── F-003: NaN/Inf exact ERROR contract ──────────────────────────────

class TestNonfiniteExactContract:
    @pytest.mark.parametrize("bad_val,label", [
        (float('nan'), "NaN"),
        (float('inf'), "Inf"),
    ])
    def test_nonfinite_full_contract(self, bad_val, label):
        orig = core.quaternion_min_angle_degrees
        core.quaternion_min_angle_degrees = lambda *a: bad_val
        try:
            r = _check_rotation(_valid_spec(), _obj())
            assert set(r.keys()) == _ERROR_KEYS
            assert r["result"] == "ERROR"
            assert r["error_type"] == "ROTATION_COMPUTATION_ERROR"
            assert r["operation"] == "COMPUTE_ROTATION_ANGLE"
            assert r["note"] == "NONFINITE_ROTATION_ANGLE"
            assert "expected_world_rotation_euler_degrees" not in r
            assert "expected_quaternion" not in r
            assert "actual_quaternion" not in r
            assert "angle_degrees" not in r
            assert "tolerance_degrees" not in r
            assert "failure_code" not in r
        finally:
            core.quaternion_min_angle_degrees = orig


def test_test_file_self_parse():
    with open(__file__, "r", encoding="utf-8") as f:
        ast.parse(f.read())

def test_test_file_no_skip_xfail():
    with open(__file__, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = None
            if isinstance(node.func, ast.Attribute): name = node.func.attr
            elif isinstance(node.func, ast.Name): name = node.func.id
            if name in ("skip", "skipif", "xfail", "importorskip"):
                raise AssertionError(f"line {node.lineno}: {name}()")
