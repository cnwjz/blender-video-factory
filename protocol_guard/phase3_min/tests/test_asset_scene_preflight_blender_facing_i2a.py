"""Tests for 14B-3B I2A: facing 4 runtime ERROR operations."""
import os, sys, math, types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import pytest

_bpy = types.ModuleType("bpy"); _bpy.ops = types.ModuleType("bpy.ops")
_bpy.data = types.ModuleType("bpy.data"); _bpy.context = types.ModuleType("bpy.context")
sys.modules["bpy"] = _bpy; sys.modules["bpy.ops"] = _bpy.ops
sys.modules["bpy.data"] = _bpy.data; sys.modules["bpy.context"] = _bpy.context


class FakeVector:
    def __init__(self, seq):
        self.x, self.y, self.z = seq[0], seq[1], seq[2]


class FakeMat3:
    def __init__(self, rows):
        self._rows = rows
    def to_3x3(self):
        return FakeMat3(self._rows)
    def __matmul__(self, vec):
        r = self._rows
        return FakeVector((
            r[0][0]*vec.x + r[0][1]*vec.y + r[0][2]*vec.z,
            r[1][0]*vec.x + r[1][1]*vec.y + r[1][2]*vec.z,
            r[2][0]*vec.x + r[2][1]*vec.y + r[2][2]*vec.z,
        ))


_mu = types.ModuleType("mathutils"); _mu.Vector = FakeVector
sys.modules["mathutils"] = _mu

from protocol_guard.phase3_min.blender_scene_reader import _check_facing_forward_axis, _check_root_objects


def _mat3_id():
    return FakeMat3([[1.0,0,0],[0,1.0,0],[0,0,1.0]])

def _root(mat=None):
    class R: pass
    r = R(); r.matrix_world = mat if mat is not None else _mat3_id(); r.type = "EMPTY"
    return r

def _facing_spec(local="+Y", expected="+Y", tol=5.0):
    return {"facing": {"local_forward_axis": local,
            "expected_world_forward_axis": expected,
            "facing_tolerance_degrees": tol}}

NORMAL_FIELDS = ["local_forward_axis", "expected_world_forward_axis",
    "actual_world_forward_direction", "angle_degrees", "tolerance_degrees"]


# ── READ_ROOT_MATRIX_WORLD ──────────────────────────────────────────────

class TestReadRootMatrixWorldError:
    def test_matrix_world_access_raises(self):
        class Root:
            @property
            def matrix_world(self):
                raise RuntimeError("boom")
            type = "EMPTY"
        r = _check_facing_forward_axis(_facing_spec(), Root())
        assert r["result"] == "ERROR"
        fa = r["forward_axis"]
        assert fa["result"] == "ERROR"
        assert fa["error_type"] == "FACING_FORWARD_AXIS_ERROR"
        assert fa["operation"] == "READ_ROOT_MATRIX_WORLD"
        assert fa["note"] == "READ_ROOT_MATRIX_WORLD_FAILED"

    def test_normal_fields_omitted(self):
        class Root:
            @property
            def matrix_world(self):
                raise RuntimeError("boom")
            type = "EMPTY"
        r = _check_facing_forward_axis(_facing_spec(), Root())
        for f in NORMAL_FIELDS:
            assert f not in r["forward_axis"], f"field {f} should be omitted on ERROR"
        assert "failure_code" not in r["forward_axis"]


# ── CONVERT_ROOT_MATRIX_WORLD_TO_3X3 ────────────────────────────────────

class TestConvertRootMatrixWorldTo3x3Error:
    def test_to_3x3_raises(self):
        class BadMW:
            def to_3x3(self):
                raise RuntimeError("boom")
        class Root:
            matrix_world = BadMW()
            type = "EMPTY"
        r = _check_facing_forward_axis(_facing_spec(), Root())
        assert r["result"] == "ERROR"
        fa = r["forward_axis"]
        assert fa["result"] == "ERROR"
        assert fa["error_type"] == "FACING_FORWARD_AXIS_ERROR"
        assert fa["operation"] == "CONVERT_ROOT_MATRIX_WORLD_TO_3X3"
        assert fa["note"] == "CONVERT_ROOT_MATRIX_WORLD_TO_3X3_FAILED"

    def test_normal_fields_omitted(self):
        class BadMW:
            def to_3x3(self):
                raise RuntimeError("boom")
        class Root:
            matrix_world = BadMW()
            type = "EMPTY"
        r = _check_facing_forward_axis(_facing_spec(), Root())
        for f in NORMAL_FIELDS:
            assert f not in r["forward_axis"], f"field {f} should be omitted on ERROR"


# ── TRANSFORM_LOCAL_FORWARD_AXIS ────────────────────────────────────────

class TestTransformLocalForwardAxisError:
    def test_matmul_raises(self):
        class RaisingMatmul:
            def __matmul__(self, vec):
                raise RuntimeError("boom")
        class MW:
            def to_3x3(self):
                return RaisingMatmul()
        class Root:
            matrix_world = MW()
            type = "EMPTY"
        r = _check_facing_forward_axis(_facing_spec(), Root())
        assert r["result"] == "ERROR"
        fa = r["forward_axis"]
        assert fa["result"] == "ERROR"
        assert fa["error_type"] == "FACING_FORWARD_AXIS_ERROR"
        assert fa["operation"] == "TRANSFORM_LOCAL_FORWARD_AXIS"
        assert fa["note"] == "TRANSFORM_LOCAL_FORWARD_AXIS_FAILED"

    def test_normal_fields_omitted(self):
        class RaisingMatmul:
            def __matmul__(self, vec):
                raise RuntimeError("boom")
        class MW:
            def to_3x3(self):
                return RaisingMatmul()
        class Root:
            matrix_world = MW()
            type = "EMPTY"
        r = _check_facing_forward_axis(_facing_spec(), Root())
        for f in NORMAL_FIELDS:
            assert f not in r["forward_axis"], f"field {f} should be omitted on ERROR"


# ── COMPUTE_FORWARD_AXIS_ANGLE ──────────────────────────────────────────

class TestComputeForwardAxisAngleError:
    def test_vector_angle_degrees_raises(self):
        import protocol_guard.phase3_min.asset_scene_preflight_core as core
        original = core.vector_angle_degrees
        try:
            def _raising(*args):
                raise RuntimeError("angle boom")
            core.vector_angle_degrees = _raising
            r = _check_facing_forward_axis(_facing_spec(), _root())
            assert r["result"] == "ERROR"
            fa = r["forward_axis"]
            assert fa["result"] == "ERROR"
            assert fa["error_type"] == "FACING_FORWARD_AXIS_ERROR"
            assert fa["operation"] == "COMPUTE_FORWARD_AXIS_ANGLE"
            assert fa["note"] == "COMPUTE_FORWARD_AXIS_ANGLE_FAILED"
        finally:
            core.vector_angle_degrees = original

    def test_normal_fields_omitted(self):
        import protocol_guard.phase3_min.asset_scene_preflight_core as core
        original = core.vector_angle_degrees
        try:
            core.vector_angle_degrees = lambda *a: (_ for _ in ()).throw(RuntimeError("boom"))
            r = _check_facing_forward_axis(_facing_spec(), _root())
            for f in NORMAL_FIELDS:
                assert f not in r["forward_axis"], f"field {f} should be omitted on ERROR"
        finally:
            core.vector_angle_degrees = original


# ── I1 regression: PASS/FAIL/NOT_CHECKED still work ────────────────────

class TestI1Regression:
    def test_not_checked_still_works(self):
        r = _check_facing_forward_axis({}, _root())
        assert r["result"] == "NOT_CHECKED"

    def test_pass_still_works(self):
        r = _check_facing_forward_axis(_facing_spec(), _root())
        assert r["result"] == "PASS"
        assert r["forward_axis"]["angle_degrees"] == 0.0

    def test_fail_still_works(self):
        a = math.radians(180); c = math.cos(a); s = math.sin(a)
        mat = FakeMat3([[1,0,0],[0,c,-s],[0,s,c]])  # X-rot 180: +Y -> -Y
        r = _check_facing_forward_axis(_facing_spec(tol=5.0), _root(mat=mat))
        assert r["result"] == "FAIL"
        assert r["forward_axis"]["failure_code"] == "FACING_FORWARD_AXIS_DEVIATION"


# ── Integration: error makes overall ERROR, standing still independent ──

class TestIntegration:
    def test_facing_error_makes_overall_error(self):
        td = __import__("tempfile").TemporaryDirectory()
        try:
            script = f'''
import json, sys, os, types
sys.path.insert(0, r"{os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))}")
_bpy = types.ModuleType("bpy"); _bpy.ops = types.ModuleType("bpy.ops")
_bpy.data = types.ModuleType("bpy.data"); _bpy.context = types.ModuleType("bpy.context")
sys.modules["bpy"] = _bpy; sys.modules["bpy.ops"] = _bpy.ops
sys.modules["bpy.data"] = _bpy.data; sys.modules["bpy.context"] = _bpy.context
_mu = types.ModuleType("mathutils")
class FV:
    def __init__(self, s): self.x,self.y,self.z = s[0],s[1],s[2]
_mu.Vector = FV; sys.modules["mathutils"] = _mu
from protocol_guard.phase3_min.blender_scene_reader import _check_root_objects

class RO:
    name = "R"; type = "EMPTY"
    @property
    def matrix_world(self):
        raise RuntimeError("boom")

class FS:
    def __init__(self, objs): self.objects = list(objs)

results = _check_root_objects(FS([RO()]), [{{"target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
    "facing": {{"local_forward_axis": "+Y", "expected_world_forward_axis": "+Y", "facing_tolerance_degrees": 5.0}}}}])
assert results[0]["overall"] == "ERROR", f"Expected ERROR, got {{results[0]}}"
st = results[0]["checks"]["facing"]
assert st["result"] == "ERROR"
assert st["forward_axis"]["operation"] == "READ_ROOT_MATRIX_WORLD"
print("PASS=OK")
'''
            sf = os.path.join(td.name, "run.py")
            with open(sf, "w") as f: f.write(script)
            import subprocess as _sp
            r = _sp.run(["python", sf], capture_output=True, text=True)
            assert r.returncode == 0 and "PASS=OK" in r.stdout, f"FAILED: {r.stdout}\n{r.stderr}"
        finally:
            td.cleanup()

    def test_standing_error_facing_still_executes(self):
        """Facing ERROR does not prevent Standing from running."""
        td = __import__("tempfile").TemporaryDirectory()
        try:
            script = f'''
import json, sys, os, types
sys.path.insert(0, r"{os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))}")
_bpy = types.ModuleType("bpy"); _bpy.ops = types.ModuleType("bpy.ops")
_bpy.data = types.ModuleType("bpy.data"); _bpy.context = types.ModuleType("bpy.context")
sys.modules["bpy"] = _bpy; sys.modules["bpy.ops"] = _bpy.ops
sys.modules["bpy.data"] = _bpy.data; sys.modules["bpy.context"] = _bpy.context
_mu = types.ModuleType("mathutils")
class FV:
    def __init__(self, s): self.x,self.y,self.z = s[0],s[1],s[2]
_mu.Vector = FV; sys.modules["mathutils"] = _mu
from protocol_guard.phase3_min.blender_scene_reader import _check_root_objects

class BadMW:
    def to_3x3(self):
        raise RuntimeError("boom")

class RO:
    name = "R"; type = "EMPTY"
    matrix_world = BadMW()

class FS:
    def __init__(self, objs): self.objects = list(objs)

results = _check_root_objects(FS([RO()]), [{{"target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
    "standing": {{"local_up_axis": "+Z", "expected_world_up_axis": "+Z", "up_axis_tolerance_degrees": 5.0}},
    "facing": {{"local_forward_axis": "+Y", "expected_world_forward_axis": "+Y", "facing_tolerance_degrees": 5.0}}}}])
# Both standing and facing try to_3x3 on same BadMW -> both ERROR
assert results[0]["checks"]["standing"]["result"] == "ERROR"
assert results[0]["checks"]["facing"]["result"] == "ERROR"
assert results[0]["overall"] == "ERROR"
print("PASS=OK")
'''
            sf = os.path.join(td.name, "run.py")
            with open(sf, "w") as f: f.write(script)
            import subprocess as _sp
            r = _sp.run(["python", sf], capture_output=True, text=True)
            assert r.returncode == 0 and "PASS=OK" in r.stdout, f"FAILED: {r.stdout}\n{r.stderr}"
        finally:
            td.cleanup()


# ── _collect_target_errors: facing collected after standing ─────────────

class TestCollectTargetErrors:
    def test_facing_error_collected(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import _collect_target_errors
        per_target = [{
            "target_id": "A", "root_object_name": "R", "overall": "ERROR",
            "checks": {
                "facing": {
                    "result": "ERROR",
                    "forward_axis": {
                        "result": "ERROR",
                        "error_type": "FACING_FORWARD_AXIS_ERROR",
                        "operation": "TRANSFORM_LOCAL_FORWARD_AXIS",
                        "note": "TRANSFORM_LOCAL_FORWARD_AXIS_FAILED",
                    },
                },
            },
        }]
        errs = _collect_target_errors(per_target)
        assert len(errs) == 1
        assert "FACING_FORWARD_AXIS_ERROR" in errs[0]
        assert "'A'" in errs[0]
        assert "'R'" in errs[0]
        assert "TRANSFORM_LOCAL_FORWARD_AXIS" in errs[0]

    def test_standing_before_facing_in_error_order(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import _collect_target_errors
        per_target = [{
            "target_id": "A", "root_object_name": "R", "overall": "ERROR",
            "checks": {
                "standing": {
                    "result": "ERROR",
                    "up_axis": {
                        "result": "ERROR",
                        "error_type": "STANDING_UP_AXIS_ERROR",
                        "operation": "READ_ROOT_MATRIX_WORLD",
                        "note": "READ_ROOT_MATRIX_WORLD_FAILED",
                    },
                },
                "facing": {
                    "result": "ERROR",
                    "forward_axis": {
                        "result": "ERROR",
                        "error_type": "FACING_FORWARD_AXIS_ERROR",
                        "operation": "COMPUTE_FORWARD_AXIS_ANGLE",
                        "note": "COMPUTE_FORWARD_AXIS_ANGLE_FAILED",
                    },
                },
            },
        }]
        errs = _collect_target_errors(per_target)
        assert len(errs) == 2
        assert "STANDING_UP_AXIS_ERROR" in errs[0]
        assert "FACING_FORWARD_AXIS_ERROR" in errs[1]

    def test_operation_missing_uses_unknown(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import _collect_target_errors
        per_target = [{
            "target_id": "A", "root_object_name": "R", "overall": "ERROR",
            "checks": {
                "facing": {
                    "result": "ERROR",
                    "forward_axis": {
                        "result": "ERROR",
                        "error_type": "FACING_FORWARD_AXIS_ERROR",
                        "note": "SOME_ERROR",
                    },
                },
            },
        }]
        errs = _collect_target_errors(per_target)
        assert len(errs) == 1
        assert "UNKNOWN" in errs[0]
