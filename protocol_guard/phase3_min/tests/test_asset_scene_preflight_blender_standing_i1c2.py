"""Tests for 14B-3A-I1C2: standing up_axis NORMALIZE_WORLD_UP_AXIS error."""
import os, sys, math, types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import pytest

# Monkey-patch bpy and mathutils for CPython import
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
    def __getitem__(self, row):
        return tuple(self._rows[row])
    def __matmul__(self, vec):
        r = self._rows
        return FakeVector((
            r[0][0]*vec.x + r[0][1]*vec.y + r[0][2]*vec.z,
            r[1][0]*vec.x + r[1][1]*vec.y + r[1][2]*vec.z,
            r[2][0]*vec.x + r[2][1]*vec.y + r[2][2]*vec.z,
        ))


_mu = types.ModuleType("mathutils"); _mu.Vector = FakeVector
sys.modules["mathutils"] = _mu

from protocol_guard.phase3_min.blender_scene_reader import _check_standing_up_axis, _check_root_objects


def _mat3_id():
    return FakeMat3([[1.0,0,0],[0,1.0,0],[0,0,1.0]])


def _root(mat=None):
    class R: pass
    r = R(); r.matrix_world = mat if mat is not None else _mat3_id(); r.type = "EMPTY"
    return r


def _standing(**kw):
    return {"standing": {"local_up_axis": kw.get("local"),
            "expected_world_up_axis": kw.get("expected"),
            "up_axis_tolerance_degrees": kw.get("tol")}}


NORMAL_ERROR_FIELDS = [
    "local_up_axis", "expected_world_up_axis",
    "actual_world_up_direction", "angle_degrees", "tolerance_degrees",
]


# --- ZERO_LENGTH_UP_VECTOR ---

class TestZeroLengthUpVector:
    def test_zero_vector_produces_error(self):
        zero_mat = FakeMat3([[0,0,0],[0,0,0],[0,0,0]])
        r = _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=5.0), _root(mat=zero_mat))
        assert r["result"] == "ERROR"
        u = r["up_axis"]
        assert u["result"] == "ERROR"
        assert u["error_type"] == "STANDING_UP_AXIS_ERROR"
        assert u["operation"] == "NORMALIZE_WORLD_UP_AXIS"
        assert u["note"] == "ZERO_LENGTH_UP_VECTOR"

    def test_normal_fields_omitted(self):
        zero_mat = FakeMat3([[0,0,0],[0,0,0],[0,0,0]])
        r = _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=5.0), _root(mat=zero_mat))
        for f in NORMAL_ERROR_FIELDS:
            assert f not in r["up_axis"], f"field {f} should be omitted on ERROR"
        assert "failure_code" not in r["up_axis"]


# --- NONFINITE_WORLD_UP_VECTOR — NaN ---

class TestNaNComponent:
    def test_nan_component_produces_error(self):
        nan = float("nan")
        nan_mat = FakeMat3([[nan,0,0],[0,nan,0],[0,0,nan]])
        r = _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=5.0), _root(mat=nan_mat))
        assert r["result"] == "ERROR"
        u = r["up_axis"]
        assert u["result"] == "ERROR"
        assert u["error_type"] == "STANDING_UP_AXIS_ERROR"
        assert u["operation"] == "NORMALIZE_WORLD_UP_AXIS"
        assert u["note"] == "NONFINITE_WORLD_UP_VECTOR"

    def test_normal_fields_omitted(self):
        nan = float("nan")
        nan_mat = FakeMat3([[nan,0,0],[0,nan,0],[0,0,nan]])
        r = _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=5.0), _root(mat=nan_mat))
        for f in NORMAL_ERROR_FIELDS:
            assert f not in r["up_axis"], f"field {f} should be omitted on ERROR"
        assert "failure_code" not in r["up_axis"]


# --- NONFINITE_WORLD_UP_VECTOR — +Inf ---

class TestPositiveInfComponent:
    def test_pos_inf_component_produces_error(self):
        inf = float("inf")
        inf_mat = FakeMat3([[inf,0,0],[0,inf,0],[0,0,inf]])
        r = _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=5.0), _root(mat=inf_mat))
        assert r["result"] == "ERROR"
        u = r["up_axis"]
        assert u["result"] == "ERROR"
        assert u["error_type"] == "STANDING_UP_AXIS_ERROR"
        assert u["operation"] == "NORMALIZE_WORLD_UP_AXIS"
        assert u["note"] == "NONFINITE_WORLD_UP_VECTOR"

    def test_normal_fields_omitted(self):
        inf = float("inf")
        inf_mat = FakeMat3([[inf,0,0],[0,inf,0],[0,0,inf]])
        r = _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=5.0), _root(mat=inf_mat))
        for f in NORMAL_ERROR_FIELDS:
            assert f not in r["up_axis"], f"field {f} should be omitted on ERROR"
        assert "failure_code" not in r["up_axis"]


# --- NONFINITE_WORLD_UP_VECTOR — -Inf ---

class TestNegativeInfComponent:
    def test_neg_inf_component_produces_error(self):
        ninf = float("-inf")
        inf_mat = FakeMat3([[ninf,0,0],[0,ninf,0],[0,0,ninf]])
        r = _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=5.0), _root(mat=inf_mat))
        assert r["result"] == "ERROR"
        u = r["up_axis"]
        assert u["result"] == "ERROR"
        assert u["error_type"] == "STANDING_UP_AXIS_ERROR"
        assert u["operation"] == "NORMALIZE_WORLD_UP_AXIS"
        assert u["note"] == "NONFINITE_WORLD_UP_VECTOR"

    def test_normal_fields_omitted(self):
        ninf = float("-inf")
        inf_mat = FakeMat3([[ninf,0,0],[0,ninf,0],[0,0,ninf]])
        r = _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=5.0), _root(mat=inf_mat))
        for f in NORMAL_ERROR_FIELDS:
            assert f not in r["up_axis"], f"field {f} should be omitted on ERROR"
        assert "failure_code" not in r["up_axis"]


# --- Non-finite length (components finite but length overflows to Inf) ---

class TestNonFiniteLength:
    def test_large_components_produce_inf_length(self):
        big = 1e200
        big_mat = FakeMat3([[big,0,0],[0,big,0],[0,0,big]])
        r = _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=5.0), _root(mat=big_mat))
        assert r["result"] == "ERROR"
        u = r["up_axis"]
        assert u["result"] == "ERROR"
        assert u["error_type"] == "STANDING_UP_AXIS_ERROR"
        assert u["operation"] == "NORMALIZE_WORLD_UP_AXIS"
        assert u["note"] == "NONFINITE_WORLD_UP_VECTOR"


# --- Normal non-unit vector still normalizes and PASS ---

class TestNormalizationStillWorks:
    def test_non_unit_vector_normalizes_and_passes(self):
        scale2 = FakeMat3([[2,0,0],[0,2,0],[0,0,2]])
        r = _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=0.0), _root(mat=scale2))
        assert r["result"] == "PASS"
        u = r["up_axis"]
        assert u["result"] == "PASS"
        d = u["actual_world_up_direction"]
        norm = math.sqrt(d[0]**2 + d[1]**2 + d[2]**2)
        assert abs(norm - 1.0) < 1e-9


# --- Integration via _check_root_objects ---

class TestCheckRootObjectsIntegration:
    def test_normalize_error_makes_overall_error(self):
        td = __import__("tempfile").TemporaryDirectory()
        try:
            script = f'''
import json, sys, os
sys.path.insert(0, r"{os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))}")
import types, math
_bpy = types.ModuleType("bpy"); _bpy.ops = types.ModuleType("bpy.ops")
_bpy.data = types.ModuleType("bpy.data"); _bpy.context = types.ModuleType("bpy.context")
sys.modules["bpy"] = _bpy; sys.modules["bpy.ops"] = _bpy.ops
sys.modules["bpy.data"] = _bpy.data; sys.modules["bpy.context"] = _bpy.context
_mu = types.ModuleType("mathutils")
class FV:
    def __init__(self, s): self.x,self.y,self.z = s[0],s[1],s[2]
_mu.Vector = FV; sys.modules["mathutils"] = _mu
from protocol_guard.phase3_min.blender_scene_reader import _check_root_objects

class ZeroMat:
    def to_3x3(self):
        class M3:
            def __matmul__(s, vec): return FV((0.0, 0.0, 0.0))
        return M3()

class RO:
    name = "R"; type = "EMPTY"
    matrix_world = ZeroMat()

class FS:
    def __init__(self, objs): self.objects = list(objs)

results = _check_root_objects(FS([RO()]), [{{"target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
    "standing": {{"local_up_axis": "+Z", "expected_world_up_axis": "+Z", "up_axis_tolerance_degrees": 5.0}}}}])
assert results[0]["overall"] == "ERROR", f"Expected overall=ERROR, got {{results[0]}}"
st = results[0]["checks"]["standing"]
assert st["result"] == "ERROR"
assert st["up_axis"]["result"] == "ERROR"
assert st["up_axis"]["error_type"] == "STANDING_UP_AXIS_ERROR"
assert st["up_axis"]["operation"] == "NORMALIZE_WORLD_UP_AXIS"
assert st["up_axis"]["note"] == "ZERO_LENGTH_UP_VECTOR"
print("PASS=OK")
'''
            sf = os.path.join(td.name, "run.py")
            with open(sf, "w") as f: f.write(script)
            import subprocess as _sp
            r = _sp.run(["python", sf], capture_output=True, text=True)
            assert r.returncode == 0 and "PASS=OK" in r.stdout, f"FAILED: {r.stdout}\n{r.stderr}"
        finally:
            td.cleanup()
