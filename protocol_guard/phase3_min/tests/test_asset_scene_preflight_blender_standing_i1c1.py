"""Tests for 14B-3A-I1C1: standing up_axis four runtime ERROR operations."""
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


def _root(mat=None, otype="EMPTY"):
    class R: pass
    r = R(); r.matrix_world = mat if mat is not None else _mat3_id(); r.type = otype
    return r


def _standing(**kw):
    return {"standing": {"local_up_axis": kw.get("local"),
            "expected_world_up_axis": kw.get("expected"),
            "up_axis_tolerance_degrees": kw.get("tol")}}


NORMAL_ERROR_FIELDS = [
    "local_up_axis", "expected_world_up_axis",
    "actual_world_up_direction", "angle_degrees", "tolerance_degrees",
]


# --- READ_ROOT_MATRIX_WORLD ---

class TestReadRootMatrixWorldError:
    def test_matrix_world_access_raises(self):
        class Root:
            @property
            def matrix_world(self):
                raise RuntimeError("matrix_world boom")
            type = "EMPTY"
        r = _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=5.0), Root())
        assert r["result"] == "ERROR"
        u = r["up_axis"]
        assert u["result"] == "ERROR"
        assert u["error_type"] == "STANDING_UP_AXIS_ERROR"
        assert u["operation"] == "READ_ROOT_MATRIX_WORLD"
        assert u["note"] == "READ_ROOT_MATRIX_WORLD_FAILED"

    def test_normal_fields_omitted(self):
        class Root:
            @property
            def matrix_world(self):
                raise RuntimeError("boom")
            type = "EMPTY"
        r = _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=5.0), Root())
        for f in NORMAL_ERROR_FIELDS:
            assert f not in r["up_axis"], f"field {f} should be omitted on ERROR"
        assert "failure_code" not in r["up_axis"]


# --- CONVERT_ROOT_MATRIX_WORLD_TO_3X3 ---

class TestConvertRootMatrixWorldTo3x3Error:
    def test_to_3x3_raises(self):
        class BadMW:
            def to_3x3(self):
                raise RuntimeError("to_3x3 boom")
        class Root:
            matrix_world = BadMW()
            type = "EMPTY"
        r = _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=5.0), Root())
        assert r["result"] == "ERROR"
        u = r["up_axis"]
        assert u["result"] == "ERROR"
        assert u["error_type"] == "STANDING_UP_AXIS_ERROR"
        assert u["operation"] == "CONVERT_ROOT_MATRIX_WORLD_TO_3X3"
        assert u["note"] == "CONVERT_ROOT_MATRIX_WORLD_TO_3X3_FAILED"

    def test_normal_fields_omitted(self):
        class BadMW:
            def to_3x3(self):
                raise RuntimeError("boom")
        class Root:
            matrix_world = BadMW()
            type = "EMPTY"
        r = _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=5.0), Root())
        for f in NORMAL_ERROR_FIELDS:
            assert f not in r["up_axis"], f"field {f} should be omitted on ERROR"
        assert "failure_code" not in r["up_axis"]

    def test_matrix_world_not_read_after_to_3x3_fails(self):
        class BadMW:
            def __init__(self): self._reads = 0
            def to_3x3(self):
                raise RuntimeError("boom")
        class Root:
            def __init__(self):
                self._mw = BadMW()
            @property
            def matrix_world(self):
                self._mw._reads += 1
                return self._mw
            type = "EMPTY"
        r = _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=5.0), Root())
        assert r["result"] == "ERROR"
        assert r["up_axis"]["operation"] == "CONVERT_ROOT_MATRIX_WORLD_TO_3X3"


# --- TRANSFORM_LOCAL_UP_AXIS ---

class TestTransformLocalUpAxisError:
    def test_matmul_raises(self):
        class RaisingMatmul:
            def __matmul__(self, vec):
                raise RuntimeError("matmul boom")
        class MW:
            def to_3x3(self):
                return RaisingMatmul()
        class Root:
            matrix_world = MW()
            type = "EMPTY"
        r = _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=5.0), Root())
        assert r["result"] == "ERROR"
        u = r["up_axis"]
        assert u["result"] == "ERROR"
        assert u["error_type"] == "STANDING_UP_AXIS_ERROR"
        assert u["operation"] == "TRANSFORM_LOCAL_UP_AXIS"
        assert u["note"] == "TRANSFORM_LOCAL_UP_AXIS_FAILED"

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
        r = _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=5.0), Root())
        for f in NORMAL_ERROR_FIELDS:
            assert f not in r["up_axis"], f"field {f} should be omitted on ERROR"
        assert "failure_code" not in r["up_axis"]

    def test_to_3x3_called_once_before_matmul_fails(self):
        class RaisingMatmul:
            def __matmul__(self, vec):
                raise RuntimeError("boom")
        class MW:
            def __init__(self): self._calls = 0
            def to_3x3(self):
                self._calls += 1
                return RaisingMatmul()
        class Root:
            def __init__(self, mw): self._mw = mw
            @property
            def matrix_world(self): return self._mw
            type = "EMPTY"
        mw = MW()
        r = _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=5.0), Root(mw))
        assert r["result"] == "ERROR"
        assert r["up_axis"]["operation"] == "TRANSFORM_LOCAL_UP_AXIS"
        assert mw._calls == 1


# --- COMPUTE_UP_AXIS_ANGLE ---

class TestComputeUpAxisAngleError:
    def test_vector_angle_degrees_raises(self):
        import protocol_guard.phase3_min.asset_scene_preflight_core as core
        original = core.vector_angle_degrees
        try:
            def _raising(*args):
                raise RuntimeError("angle boom")
            core.vector_angle_degrees = _raising
            r = _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=5.0), _root())
            assert r["result"] == "ERROR"
            u = r["up_axis"]
            assert u["result"] == "ERROR"
            assert u["error_type"] == "STANDING_UP_AXIS_ERROR"
            assert u["operation"] == "COMPUTE_UP_AXIS_ANGLE"
            assert u["note"] == "COMPUTE_UP_AXIS_ANGLE_FAILED"
        finally:
            core.vector_angle_degrees = original

    def test_normal_fields_omitted(self):
        import protocol_guard.phase3_min.asset_scene_preflight_core as core
        original = core.vector_angle_degrees
        try:
            def _raising(*args):
                raise RuntimeError("boom")
            core.vector_angle_degrees = _raising
            r = _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=5.0), _root())
            for f in NORMAL_ERROR_FIELDS:
                assert f not in r["up_axis"], f"field {f} should be omitted on ERROR"
            assert "failure_code" not in r["up_axis"]
        finally:
            core.vector_angle_degrees = original

    def test_matrix_world_read_once_before_angle_fails(self):
        import protocol_guard.phase3_min.asset_scene_preflight_core as core
        original = core.vector_angle_degrees
        try:
            def _raising(*args):
                raise RuntimeError("boom")
            core.vector_angle_degrees = _raising

            class MW:
                def __init__(self): self._reads = 0
                def to_3x3(self):
                    class M3:
                        def __matmul__(s, vec): return FakeVector((vec.x, vec.y, vec.z))
                    return M3()
            class Root:
                def __init__(self):
                    self._mw = MW()
                @property
                def matrix_world(self):
                    self._mw._reads += 1
                    return self._mw
                type = "EMPTY"
            root = Root()
            r = _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=5.0), root)
            assert r["result"] == "ERROR"
            assert r["up_axis"]["operation"] == "COMPUTE_UP_AXIS_ANGLE"
            assert root._mw._reads == 1
        finally:
            core.vector_angle_degrees = original


# --- Integration via _check_root_objects ---

class TestCheckRootObjectsIntegration:
    def test_standing_error_makes_overall_error(self):
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
    @property
    def matrix_world(self):
        raise RuntimeError("boom")

class FS:
    def __init__(self, objs): self.objects = list(objs)

results = _check_root_objects(FS([RO()]), [{{"target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
    "standing": {{"local_up_axis": "+Z", "expected_world_up_axis": "+Z", "up_axis_tolerance_degrees": 5.0}}}}])
assert results[0]["overall"] == "ERROR", f"Expected overall=ERROR, got {{results[0]}}"
st = results[0]["checks"]["standing"]
assert st["result"] == "ERROR"
assert st["up_axis"]["result"] == "ERROR"
assert st["up_axis"]["error_type"] == "STANDING_UP_AXIS_ERROR"
assert st["up_axis"]["operation"] == "READ_ROOT_MATRIX_WORLD"
print("PASS=OK")
'''
            sf = os.path.join(td.name, "run.py")
            with open(sf, "w") as f: f.write(script)
            import subprocess as _sp
            r = _sp.run(["python", sf], capture_output=True, text=True)
            assert r.returncode == 0 and "PASS=OK" in r.stdout, f"FAILED: {r.stdout}\n{r.stderr}"
        finally:
            td.cleanup()


# --- Existing constraints preserved ---

class TestExistingConstraintsPreserved:
    def test_matrix_world_read_at_most_once(self):
        class RT:
            def __init__(self): self._reads = 0
            @property
            def matrix_world(self): self._reads += 1; return _mat3_id()
            type = "EMPTY"
        root = RT()
        _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=0.0), root)
        assert root._reads == 1

    def test_to_3x3_called_once(self):
        class MW:
            def __init__(self): self._calls = 0
            def to_3x3(self): self._calls += 1; return _mat3_id()
        class R: pass
        root = R(); root.matrix_world = MW(); root.type = "EMPTY"
        _check_standing_up_axis(_standing(local="+Z", expected="+Z", tol=5.0), root)
        assert root.matrix_world._calls == 1
