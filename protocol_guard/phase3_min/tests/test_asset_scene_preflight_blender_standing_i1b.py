"""Tests for 14B-3A-I1B: standing up_axis PASS/FAIL/NOT_CHECKED."""
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

def _mat3_rot(axis, angle):
    c = math.cos(angle); s = math.sin(angle); x,y,z = axis
    if abs(x-1)<1e-9: rows = [[1,0,0],[0,c,-s],[0,s,c]]
    elif abs(y-1)<1e-9: rows = [[c,0,s],[0,1,0],[-s,0,c]]
    elif abs(z-1)<1e-9: rows = [[c,-s,0],[s,c,0],[0,0,1]]
    else: rows = [[1,0,0],[0,1,0],[0,0,1]]
    return FakeMat3(rows)

def _mat3_scale(sx, sy, sz):
    return FakeMat3([[sx,0,0],[0,sy,0],[0,0,sz]])

def _root(mat=None, otype="EMPTY"):
    class R: pass
    r = R(); r.matrix_world = mat if mat is not None else _mat3_id(); r.type = otype
    return r

def _standing(**kw):
    return {"standing": {"local_up_axis": kw.get("local"),
            "expected_world_up_axis": kw.get("expected"),
            "up_axis_tolerance_degrees": kw.get("tol")}}


class TestStandingNotChecked:
    def test_all_three_none(self):
        r = _check_standing_up_axis(_standing(local=None, expected=None, tol=None), _root())
        assert r["result"] == "NOT_CHECKED"
        assert r["up_axis"]["result"] == "NOT_CHECKED"
        assert r["up_axis"]["note"] == "UP_AXIS_RULES_NOT_CONFIGURED"

    def test_no_standing_key(self):
        r = _check_standing_up_axis({}, _root())
        assert r["result"] == "NOT_CHECKED"


class TestStandingPass:
    def test_plus_z_to_plus_z_zero_tolerance(self):
        r = _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=0.0), _root())
        assert r["result"] == "PASS"
        u = r["up_axis"]
        assert u["result"] == "PASS"
        assert u["local_up_axis"] == "+Z"
        assert u["angle_degrees"] == 0.0
        assert u["tolerance_degrees"] == 0.0

    def test_angle_equal_tolerance_passes(self):
        r = _check_standing_up_axis(_standing(local="+Z", expected="+Y", tol=90.0), _root())
        assert r["result"] == "PASS"

    def test_angle_within_tolerance_passes(self):
        m = _mat3_rot((1,0,0), math.radians(5))
        r = _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=10.0), _root(mat=m))
        assert r["result"] == "PASS"


class TestStandingFail:
    def test_angle_exceeds_tolerance_fails(self):
        m = _mat3_rot((1,0,0), math.radians(10))
        r = _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=5.0), _root(mat=m))
        assert r["result"] == "FAIL"
        u = r["up_axis"]
        assert u["failure_code"] == "STANDING_UP_AXIS_DEVIATION"


class TestNormalization:
    def test_non_unit_vector_normalized(self):
        m = _mat3_scale(2.0, 2.0, 2.0)
        r = _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=0.0), _root(mat=m))
        assert r["result"] == "PASS"
        d = r["up_axis"]["actual_world_up_direction"]
        norm = math.sqrt(d[0]**2 + d[1]**2 + d[2]**2)
        assert abs(norm - 1.0) < 1e-9


class TestMatrixWorldReadOnce:
    def test_matrix_read_at_most_once(self):
        class RT:
            def __init__(self): self._reads = 0
            @property
            def matrix_world(self): self._reads += 1; return _mat3_id()
            type = "EMPTY"
        root = RT()
        _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=0.0), root)
        assert root._reads == 1


class TestRootPreconditions:
    @pytest.mark.parametrize("scenario,expected_note", [
        ("not_found", "ROOT_OBJECT_NOT_FOUND"),
        ("type_mismatch", "ROOT_OBJECT_TYPE_MISMATCH"),
        ("ambiguous", "AMBIGUOUS_ROOT_OBJECT_NAME"),
    ])
    def test_root_precondition_standing_not_checked(self, scenario, expected_note):
        td = __import__("tempfile").TemporaryDirectory()
        try:
            script = f'''
import json, sys, os
sys.path.insert(0, r"{os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))}")
import types
_bpy = types.ModuleType("bpy"); _bpy.ops = types.ModuleType("bpy.ops")
_bpy.data = types.ModuleType("bpy.data"); _bpy.context = types.ModuleType("bpy.context")
sys.modules["bpy"] = _bpy; sys.modules["bpy.ops"] = _bpy.ops
sys.modules["bpy.data"] = _bpy.data; sys.modules["bpy.context"] = _bpy.context
_mu = types.ModuleType("mathutils")
class FV:
    def __init__(self, s): self.x,self.y,self.z = s[0],s[1],s[2]
_mu.Vector = FV; sys.modules["mathutils"] = _mu
from protocol_guard.phase3_min.blender_scene_reader import _check_root_objects

class FakeScene:
    def __init__(self, objs): self.objects = list(objs)

targets = [{{"target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
    "standing": {{"local_up_axis": "+Z", "expected_world_up_axis": "+Z", "up_axis_tolerance_degrees": 5.0}}}}]
t = targets[0]

if "{scenario}" == "not_found":
    scene = FakeScene([])
elif "{scenario}" == "type_mismatch":
    class RO:
        name = "R"; type = "MESH"
    scene = FakeScene([RO()])
elif "{scenario}" == "ambiguous":
    class RO1:
        name = "R"; type = "EMPTY"
    class RO2:
        name = "R"; type = "EMPTY"
    scene = FakeScene([RO1(), RO2()])

results = _check_root_objects(scene, targets)
st = results[0]["checks"]["standing"]
assert st["result"] == "NOT_CHECKED", f"Expected NOT_CHECKED, got {{st}}"
assert st["up_axis"]["result"] == "NOT_CHECKED"
assert st["up_axis"]["note"] == "{expected_note}"
print("PASS=OK")
'''
            sf = os.path.join(td.name, "run.py")
            with open(sf, "w") as f: f.write(script)
            import subprocess as _sp
            r = _sp.run(["python", sf], capture_output=True, text=True)
            assert r.returncode == 0 and "PASS=OK" in r.stdout, f"FAILED: {r.stdout}\n{r.stderr}"
        finally:
            td.cleanup()


class TestCheckRootObjectsIntegration:
    def test_valid_root_standing_executes(self):
        td = __import__("tempfile").TemporaryDirectory()
        try:
            script = f'''
import json, sys, os
sys.path.insert(0, r"{os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))}")
import types
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
    class _mw:
        @staticmethod
        def to_3x3():
            class M3:
                def __getitem__(s2, r): return (1.0 if r==0 else 0, 1.0 if r==1 else 0, 1.0 if r==2 else 0)
                def __matmul__(s2, v): return FV((v.x, v.y, v.z))
            return M3()
    matrix_world = _mw()

class FS:
    def __init__(self, objs): self.objects = list(objs)

results = _check_root_objects(FS([RO()]), [{{"target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
    "standing": {{"local_up_axis": "+Z", "expected_world_up_axis": "+Z", "up_axis_tolerance_degrees": 5.0}}}}])
st = results[0]["checks"]["standing"]
assert st["result"] == "PASS", f"Expected PASS, got {{st}}"
assert st["up_axis"]["result"] == "PASS"
print("PASS=OK")
'''
            sf = os.path.join(td.name, "run.py")
            with open(sf, "w") as f: f.write(script)
            import subprocess as _sp
            r = _sp.run(["python", sf], capture_output=True, text=True)
            assert r.returncode == 0 and "PASS=OK" in r.stdout, f"FAILED: {r.stdout}\n{r.stderr}"
        finally:
            td.cleanup()


class TestTo3x3SingleCall:
    def test_to_3x3_called_once(self):
        class MW:
            def __init__(self): self._calls = 0
            def to_3x3(self): self._calls += 1; return _mat3_id()
        class R: pass
        root = R(); root.matrix_world = MW(); root.type = "EMPTY"
        _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=5.0), root)
        assert root.matrix_world._calls == 1
