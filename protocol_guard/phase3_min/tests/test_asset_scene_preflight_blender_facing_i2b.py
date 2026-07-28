"""Tests for 14B-3B I2B: NORMALIZE_WORLD_FORWARD_AXIS + edge boundaries."""
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


# ── ZERO_LENGTH ─────────────────────────────────────────────────────────

class TestZeroLength:
    def test_zero_vector(self):
        zero = FakeMat3([[0,0,0],[0,0,0],[0,0,0]])
        r = _check_facing_forward_axis(_facing_spec(), _root(mat=zero))
        assert r["result"] == "ERROR"
        fa = r["forward_axis"]
        assert fa["operation"] == "NORMALIZE_WORLD_FORWARD_AXIS"
        assert fa["note"] == "ZERO_LENGTH_FORWARD_VECTOR"

    def test_normal_fields_omitted(self):
        zero = FakeMat3([[0,0,0],[0,0,0],[0,0,0]])
        r = _check_facing_forward_axis(_facing_spec(), _root(mat=zero))
        for f in NORMAL_FIELDS:
            assert f not in r["forward_axis"], f"field {f} omitted on ERROR"
        assert "failure_code" not in r["forward_axis"]


# ── NONFINITE: NaN ──────────────────────────────────────────────────────

class TestNaN:
    def test_nan_component(self):
        nan = float("nan")
        mat = FakeMat3([[nan,0,0],[0,nan,0],[0,0,nan]])
        r = _check_facing_forward_axis(_facing_spec(), _root(mat=mat))
        assert r["result"] == "ERROR"
        fa = r["forward_axis"]
        assert fa["operation"] == "NORMALIZE_WORLD_FORWARD_AXIS"
        assert fa["note"] == "NONFINITE_WORLD_FORWARD_VECTOR"

    def test_normal_fields_omitted(self):
        nan = float("nan")
        mat = FakeMat3([[nan,0,0],[0,nan,0],[0,0,nan]])
        r = _check_facing_forward_axis(_facing_spec(), _root(mat=mat))
        for f in NORMAL_FIELDS:
            assert f not in r["forward_axis"], f"field {f} omitted on ERROR"


# ── NONFINITE: +Inf ─────────────────────────────────────────────────────

class TestPositiveInf:
    def test_pos_inf_component(self):
        inf = float("inf")
        mat = FakeMat3([[inf,0,0],[0,inf,0],[0,0,inf]])
        r = _check_facing_forward_axis(_facing_spec(), _root(mat=mat))
        assert r["result"] == "ERROR"
        fa = r["forward_axis"]
        assert fa["operation"] == "NORMALIZE_WORLD_FORWARD_AXIS"
        assert fa["note"] == "NONFINITE_WORLD_FORWARD_VECTOR"

    def test_normal_fields_omitted(self):
        inf = float("inf")
        mat = FakeMat3([[inf,0,0],[0,inf,0],[0,0,inf]])
        r = _check_facing_forward_axis(_facing_spec(), _root(mat=mat))
        for f in NORMAL_FIELDS:
            assert f not in r["forward_axis"], f"field {f} omitted on ERROR"


# ── NONFINITE: -Inf ─────────────────────────────────────────────────────

class TestNegativeInf:
    def test_neg_inf_component(self):
        ninf = float("-inf")
        mat = FakeMat3([[ninf,0,0],[0,ninf,0],[0,0,ninf]])
        r = _check_facing_forward_axis(_facing_spec(), _root(mat=mat))
        assert r["result"] == "ERROR"
        fa = r["forward_axis"]
        assert fa["operation"] == "NORMALIZE_WORLD_FORWARD_AXIS"
        assert fa["note"] == "NONFINITE_WORLD_FORWARD_VECTOR"

    def test_normal_fields_omitted(self):
        ninf = float("-inf")
        mat = FakeMat3([[ninf,0,0],[0,ninf,0],[0,0,ninf]])
        r = _check_facing_forward_axis(_facing_spec(), _root(mat=mat))
        for f in NORMAL_FIELDS:
            assert f not in r["forward_axis"], f"field {f} omitted on ERROR"


# ── NONFINITE: OverflowError ────────────────────────────────────────────

class TestOverflow:
    def test_large_components_overflow(self):
        big = 1e200
        mat = FakeMat3([[big,0,0],[0,big,0],[0,0,big]])
        r = _check_facing_forward_axis(_facing_spec(), _root(mat=mat))
        assert r["result"] == "ERROR"
        fa = r["forward_axis"]
        assert fa["operation"] == "NORMALIZE_WORLD_FORWARD_AXIS"
        assert fa["note"] == "NONFINITE_WORLD_FORWARD_VECTOR"


# ── Non-finite length ───────────────────────────────────────────────────

class TestNonFiniteLength:
    def test_finite_components_inf_length(self):
        """All components finite, no OverflowError in **2, but sum overflows
        to inf. Proves length non-finite guard (4c), not component guard (4a)
        nor OverflowError guard (4b)."""
        big = 1e154  # **2 = 1e308 (finite, within float64 max ~1.79e308)
        mat = FakeMat3([[0, big, 0], [0, big, 0], [0, big, 0]])
        r = _check_facing_forward_axis(_facing_spec(), _root(mat=mat))
        assert r["result"] == "ERROR"
        assert r["forward_axis"]["operation"] == "NORMALIZE_WORLD_FORWARD_AXIS"
        assert r["forward_axis"]["note"] == "NONFINITE_WORLD_FORWARD_VECTOR"


# ── Integration ─────────────────────────────────────────────────────────

class TestIntegration:
    def test_normalize_error_makes_overall_error(self):
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

class MZero:
    def to_3x3(self):
        class M3:
            def __matmul__(s, v): return FV((0.0, 0.0, 0.0))
        return M3()

class RO:
    name = "R"; type = "EMPTY"
    matrix_world = MZero()

class FS:
    def __init__(self, objs): self.objects = list(objs)

results = _check_root_objects(FS([RO()]), [{{"target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
    "facing": {{"local_forward_axis": "+Y", "expected_world_forward_axis": "+Y", "facing_tolerance_degrees": 5.0}}}}])
assert results[0]["overall"] == "ERROR"
st = results[0]["checks"]["facing"]
assert st["result"] == "ERROR"
assert st["forward_axis"]["operation"] == "NORMALIZE_WORLD_FORWARD_AXIS"
print("PASS=OK")
'''
            sf = os.path.join(td.name, "run.py")
            with open(sf, "w") as f: f.write(script)
            import subprocess as _sp
            r = _sp.run(["python", sf], capture_output=True, text=True)
            assert r.returncode == 0 and "PASS=OK" in r.stdout, f"FAILED: {r.stdout}\n{r.stderr}"
        finally:
            td.cleanup()


# ── Error collection ────────────────────────────────────────────────────

class TestErrorCollection:
    def test_normalize_error_collected(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import _collect_target_errors
        per_target = [{
            "target_id": "A", "root_object_name": "R", "overall": "ERROR",
            "checks": {
                "facing": {
                    "result": "ERROR",
                    "forward_axis": {
                        "result": "ERROR",
                        "error_type": "FACING_FORWARD_AXIS_ERROR",
                        "operation": "NORMALIZE_WORLD_FORWARD_AXIS",
                        "note": "ZERO_LENGTH_FORWARD_VECTOR",
                    },
                },
            },
        }]
        errs = _collect_target_errors(per_target)
        assert len(errs) == 1
        assert "NORMALIZE_WORLD_FORWARD_AXIS" in errs[0]


# ── Edge: normalization still works for non-unit vectors ────────────────

class TestNormalizationStillWorks:
    def test_non_unit_vector_normalizes(self):
        scale2 = FakeMat3([[2,0,0],[0,2,0],[0,0,2]])
        r = _check_facing_forward_axis(_facing_spec(), _root(mat=scale2))
        assert r["result"] == "PASS"
        d = r["forward_axis"]["actual_world_forward_direction"]
        norm = math.sqrt(d[0]**2 + d[1]**2 + d[2]**2)
        assert abs(norm - 1.0) < 1e-9


# ── Edge: negative scale ────────────────────────────────────────────────

class TestNegativeScale:
    def test_neg_y_scale_flips_forward(self):
        """Y-axis negative scale flips +Y to -Y -> 180deg -> FAIL."""
        mat = FakeMat3([[1,0,0],[0,-1,0],[0,0,1]])
        r = _check_facing_forward_axis(_facing_spec(tol=5.0), _root(mat=mat))
        assert r["result"] == "FAIL"
        assert r["forward_axis"]["angle_degrees"] == pytest.approx(180.0, abs=0.01)

    def test_neg_z_scale_no_effect_on_y_forward(self):
        """Z-axis negative scale leaves +Y unchanged."""
        mat = FakeMat3([[1,0,0],[0,1,0],[0,0,-1]])
        r = _check_facing_forward_axis(_facing_spec(), _root(mat=mat))
        assert r["result"] == "PASS"
        assert r["forward_axis"]["angle_degrees"] == 0.0


# ── Edge: non-uniform scale ─────────────────────────────────────────────

class TestNonUniformScale:
    def test_non_uniform_normalizes_correctly(self):
        """Non-uniform (2,3,4) on +Y -> scaled Y, normalized back to +Y."""
        mat = FakeMat3([[2,0,0],[0,3,0],[0,0,4]])
        r = _check_facing_forward_axis(_facing_spec(), _root(mat=mat))
        assert r["result"] == "PASS"
        d = r["forward_axis"]["actual_world_forward_direction"]
        assert abs(d[0]) < 1e-9
        assert abs(d[1] - 1.0) < 1e-9
        assert abs(d[2]) < 1e-9


# ── Edge: shear ─────────────────────────────────────────────────────────

class TestShear:
    def test_shear_no_effect_on_forward(self):
        """XZ shear: column 2 shifted in X. +Y -> (0,1,0) unchanged."""
        mat = FakeMat3([[1.0, 0.0, 0.5], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        r = _check_facing_forward_axis(_facing_spec(tol=0.1), _root(mat=mat))
        assert r["result"] == "PASS"
        assert r["forward_axis"]["angle_degrees"] == 0.0

    def test_shear_deviates_forward(self):
        """XY shear: column 1 shifted in X. +Y -> (0.5, 1, 0), angle ~26.6."""
        mat = FakeMat3([[1.0, 0.5, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        r = _check_facing_forward_axis(_facing_spec(tol=30.0), _root(mat=mat))
        assert r["result"] == "PASS"
        assert r["forward_axis"]["angle_degrees"] > 0

    def test_shear_deviates_fails_tight_tolerance(self):
        """Same XY shear, tight tolerance -> FAIL."""
        mat = FakeMat3([[1.0, 0.5, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        r = _check_facing_forward_axis(_facing_spec(tol=10.0), _root(mat=mat))
        assert r["result"] == "FAIL"
        assert r["forward_axis"]["failure_code"] == "FACING_FORWARD_AXIS_DEVIATION"
