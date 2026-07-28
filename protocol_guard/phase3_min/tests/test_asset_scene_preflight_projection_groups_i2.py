"""Projection Groups I2 R2 CPython tests — F-001 to F-004 + operation/failure coverage."""
import os, sys, pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

_EXC = "simulated failure"


class FVec:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = float(x); self.y = float(y); self.z = float(z)


class FakeObj:
    evaluated_get = None  # placeholder for monkeypatch
    def __init__(self, name, otype="MESH"):
        self.name = name; self.type = otype; self.children = []


class FakeScene:
    def __init__(self, objs):
        self._objs = objs; self.count = 0
    @property
    def objects(self):
        self.count += 1; return list(self._objs)


class FakeSceneExplode:
    @property
    def objects(self):
        raise Exception(_EXC)


class BadNameObj:
    def __init__(self, otype="MESH"):
        self.type = otype
    @property
    def name(self):
        raise Exception(_EXC)


class FakeCamLoc:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = float(x); self.y = float(y); self.z = float(z)


class FakeCamMW:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.translation = FakeCamLoc(x, y, z)


class FakeEval:
    def __init__(self, mesh, mw=None, mw_raise=False, tm_raise=False, tmc_raise=False):
        self._m = mesh; self._mw = mw; self._mr = mw_raise
        self._tr = tm_raise; self._cr = tmc_raise
    @property
    def matrix_world(self):
        if self._mr: raise Exception(_EXC)
        return self._mw
    def to_mesh(self):
        if self._tr: raise Exception(_EXC)
        return self._m
    def to_mesh_clear(self):
        if self._cr: raise Exception(_EXC)


class FakeMW:
    def __init__(self, dx=0, dy=0, dz=0):
        self.dx = dx; self.dy = dy; self.dz = dz
    def __matmul__(self, v):
        return FVec(v.x + self.dx, v.y + self.dy, v.z + self.dz)


class FakeMesh:
    def __init__(self, verts=None, count_raise=False, iter_raise=False):
        self._v = verts or []; self._cr = count_raise; self._ir = iter_raise
    @property
    def vertices(self):
        p = self
        class _VL:
            def __len__(s):
                if p._cr: raise Exception(_EXC)
                return len(p._v)
            def __iter__(s):
                if p._ir: raise Exception(_EXC)
                return iter(p._v)
        return _VL()


def _mkv(x, y, z):
    v = FVec(x, y, z); v.co = FVec(x, y, z); return v


def _t(tid, rn, gs="SELF_MESH"):
    return {"target_id": tid, "root_object_name": rn, "expected_root_type": "MESH", "geometry_scope": gs}


def _pg(gid, tids, anames=None, cam="Cam", mvc=4, ml=0.0, mr=1.0, mb=0.0, mt=1.0, rcob=False):
    return {"group_id": gid, "target_ids": list(tids), "additional_object_names": anames or [],
            "camera_object_name": cam, "minimum_visible_projected_corner_count": mvc,
            "required_screen_bbox": {"min_left": ml, "max_right": mr, "min_bottom": mb, "max_top": mt},
            "require_camera_outside_world_bbox": rcob}


def _ptr(tid, rn, ok=True):
    if ok:
        return {"target_id": tid, "root_object_name": rn, "overall": "PASS",
                "checks": {"object_exists": {"result": "PASS"}, "object_type": {"result": "PASS", "actual": "MESH"}}}
    return {"target_id": tid, "root_object_name": rn, "overall": "FAIL",
            "checks": {"object_exists": {"result": "FAIL", "failure_code": "ROOT_OBJECT_NOT_FOUND"},
                       "object_type": {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_NOT_FOUND"}}}


def _ptr_tm(tid, rn, at="EMPTY"):
    return {"target_id": tid, "root_object_name": rn, "overall": "FAIL",
            "checks": {"object_exists": {"result": "PASS"},
                       "object_type": {"result": "FAIL", "actual": at, "failure_code": "ROOT_OBJECT_TYPE_MISMATCH"}}}


def _ptr_amb(tid, rn):
    return {"target_id": tid, "root_object_name": rn, "overall": "ERROR",
            "checks": {"object_exists": {"result": "ERROR", "error_type": "AMBIGUOUS_ROOT_OBJECT_NAME"},
                       "object_type": {"result": "NOT_CHECKED"}}}

T1 = [_t("T1", "CT1")]

# Fake bpy_extras and mathutils
import sys as _sys, types as _types
_fbe = _types.ModuleType("bpy_extras"); _fbe.__path__ = []
_fou = _types.ModuleType("bpy_extras.object_utils")
def _fwcv(scene, cam, cv):
    if cv.z >= 0: return FVec(0, 0, 0)
    f = -5.0 / cv.z
    return FVec(0.5 + cv.x * f * 0.15, 0.5 + cv.y * f * 0.15, -cv.z)
_fou.world_to_camera_view = _fwcv; _fbe.object_utils = _fou
_sys.modules["bpy_extras"] = _fbe; _sys.modules["bpy_extras.object_utils"] = _fou
# Fake mathutils so `import mathutils; mathutils.Vector(...)` works
_fmu = _types.ModuleType("mathutils")
_fmu.Vector = lambda x: FVec(x[0], x[1], x[2]) if hasattr(x, '__getitem__') else FVec(x.x, x.y, x.z)
_sys.modules["mathutils"] = _fmu


@pytest.fixture(autouse=True)
def _patch(monkeypatch):
    import protocol_guard.phase3_min.blender_scene_reader as r
    class _FC:
        @staticmethod
        def evaluated_depsgraph_get(): return "dg"
    class _FB:
        context = _FC()
    monkeypatch.setattr(r, "bpy", _FB())
    # Recreate fake modules each test to prevent cross-test pollution
    _fbe2 = _types.ModuleType("bpy_extras"); _fbe2.__path__ = []
    _fou2 = _types.ModuleType("bpy_extras.object_utils")
    def _fwcv2(scene, cam, cv):
        if cv.z >= 0: return FVec(0, 0, 0)
        f = -5.0 / cv.z
        return FVec(0.5 + cv.x * f * 0.15, 0.5 + cv.y * f * 0.15, -cv.z)
    _fou2.world_to_camera_view = _fwcv2; _fbe2.object_utils = _fou2
    _sys.modules["bpy_extras"] = _fbe2
    _sys.modules["bpy_extras.object_utils"] = _fou2
    _fmu2 = _types.ModuleType("mathutils")
    _fmu2.Vector = lambda x: FVec(x[0], x[1], x[2]) if hasattr(x, '__getitem__') else FVec(x.x, x.y, x.z)
    _sys.modules["mathutils"] = _fmu2


def _patch_eval(monkeypatch, fe):
    monkeypatch.setattr(FakeObj, "evaluated_get", lambda s, dg: fe)


# ════════════════ F-001 ════════════════

class TestF001:
    def test_runtime_error_maps(self, monkeypatch):
        import protocol_guard.phase3_min.blender_scene_reader as r
        monkeypatch.setattr(r, "_collect_geometry_scope_objects",
                            lambda **kw: (_ for _ in ()).throw(RuntimeError("X")))
        sc = FakeScene([FakeObj("Cam", "CAMERA"), FakeObj("CT1", "MESH")])
        res = r._check_projection_groups(
            sc, [_pg("g1", ["T1"], cam="Cam", ml=0.3, mr=0.7, mb=0.3, mt=0.7)],
            [_ptr("T1", "CT1")], targets=T1)
        g = res[0]
        assert g["result"] == "ERROR"
        assert g["operation"] == "COLLECT_GEOMETRY_SCOPE"
        assert "INTERNAL" not in str(g)
        assert len(g) == 6


# ════════════════ F-002 ════════════════

class TestF002:
    def test_tmc_priority(self, monkeypatch):
        import protocol_guard.phase3_min.blender_scene_reader as r
        _patch_eval(monkeypatch, FakeEval(FakeMesh([]), mw=FakeMW(), tmc_raise=True))
        monkeypatch.setattr(r, "_collect_geometry_scope_objects",
                            lambda **kw: [(FakeObj("CT1", "MESH"), "CT1")])
        sc = FakeScene([FakeObj("Cam", "CAMERA"), FakeObj("CT1", "MESH")])
        res = r._check_projection_groups(
            sc, [_pg("g1", ["T1"], cam="Cam", ml=0.3, mr=0.7, mb=0.3, mt=0.7)],
            [_ptr("T1", "CT1")], targets=T1)
        g = res[0]
        assert g["result"] == "ERROR"
        assert g["operation"] == "TO_MESH_CLEAR"
        assert len(g) == 6


# ════════════════ F-003 ════════════════

class TestF003:
    def test_len_exc(self, monkeypatch):
        import protocol_guard.phase3_min.blender_scene_reader as r
        _patch_eval(monkeypatch, FakeEval(FakeMesh(count_raise=True), mw=FakeMW()))
        monkeypatch.setattr(r, "_collect_geometry_scope_objects",
                            lambda **kw: [(FakeObj("CT1", "MESH"), "CT1")])
        sc = FakeScene([FakeObj("Cam", "CAMERA"), FakeObj("CT1", "MESH")])
        res = r._check_projection_groups(
            sc, [_pg("g1", ["T1"], cam="Cam", ml=0.3, mr=0.7, mb=0.3, mt=0.7)],
            [_ptr("T1", "CT1")], targets=T1)
        assert res[0]["operation"] == "READ_MESH_VERTICES"

    def test_iter_exc(self, monkeypatch):
        import protocol_guard.phase3_min.blender_scene_reader as r
        _patch_eval(monkeypatch, FakeEval(FakeMesh([_mkv(0, 0, -5)], iter_raise=True), mw=FakeMW()))
        monkeypatch.setattr(r, "_collect_geometry_scope_objects",
                            lambda **kw: [(FakeObj("CT1", "MESH"), "CT1")])
        sc = FakeScene([FakeObj("Cam", "CAMERA"), FakeObj("CT1", "MESH")])
        res = r._check_projection_groups(
            sc, [_pg("g1", ["T1"], cam="Cam", ml=0.3, mr=0.7, mb=0.3, mt=0.7)],
            [_ptr("T1", "CT1")], targets=T1)
        assert res[0]["operation"] == "READ_MESH_VERTICES"


# ════════════════ F-004 ════════════════

class TestF004:
    def test_early_sort(self):
        import protocol_guard.phase3_min.blender_scene_reader as r
        res = r._check_projection_groups(
            FakeSceneExplode(),
            [_pg("gB", ["T1"]), _pg("gA", ["T1"]), _pg("gC", ["T1"])],
            [], targets=[])
        assert len(res) == 3
        assert [g["group_id"] for g in res] == ["gA", "gB", "gC"]
        for g in res:
            assert g["operation"] == "READ_SCENE_OBJECTS"
            assert len(g) == 6

    def test_normal_sort(self, monkeypatch):
        import protocol_guard.phase3_min.blender_scene_reader as r
        sc = FakeScene([FakeObj("Cam", "CAMERA"), FakeObj("CT1", "MESH")])
        res = r._check_projection_groups(
            sc,
            [_pg("gB", ["T1"], cam="Cam", ml=0.3, mr=0.7, mb=0.3, mt=0.7),
             _pg("gA", ["T1"], cam="Cam", ml=0.3, mr=0.7, mb=0.3, mt=0.7)],
            [_ptr("T1", "CT1")], targets=T1)
        assert [g["group_id"] for g in res] == ["gA", "gB"]


# ════════════════ Operations ════════════════

class TestOps:
    def _e6(self, g, op):
        assert g["result"] == "ERROR"
        assert g["error_type"] == "PROJECTION_GROUP_COMPUTATION_ERROR"
        assert g["operation"] == op
        assert len(g) == 6

    def test_read_scene_objects(self):
        import protocol_guard.phase3_min.blender_scene_reader as r
        res = r._check_projection_groups(FakeSceneExplode(), [_pg("g1", ["T1"])], [], targets=[])
        self._e6(res[0], "READ_SCENE_OBJECTS")

    def test_resolve_camera(self):
        import protocol_guard.phase3_min.blender_scene_reader as r
        # Camera object whose .type read throws → RESOLVE_CAMERA_OBJECT
        class BadTypeCam:
            name = "BadCam"; children = []
            @property
            def type(self): raise Exception(_EXC)
        sc = FakeScene([BadTypeCam(), FakeObj("CT1", "MESH")])
        res = r._check_projection_groups(
            sc, [_pg("g1", ["T1"], cam="BadCam")], [_ptr("T1", "CT1")], targets=T1)
        self._e6(res[0], "RESOLVE_CAMERA_OBJECT")

    def test_resolve_additional(self):
        import protocol_guard.phase3_min.blender_scene_reader as r
        # Additional object whose .type read throws → RESOLVE_ADDITIONAL_OBJECT
        class BadTypeObj:
            name = "BadObj"; children = []
            @property
            def type(self): raise Exception(_EXC)
        sc = FakeScene([FakeObj("Cam", "CAMERA"), FakeObj("CT1", "MESH"), BadTypeObj()])
        res = r._check_projection_groups(
            sc, [_pg("g1", ["T1"], cam="Cam", anames=["BadObj"])],
            [_ptr("T1", "CT1")], targets=T1)
        self._e6(res[0], "RESOLVE_ADDITIONAL_OBJECT")

    def test_collect_geometry_scope(self, monkeypatch):
        import protocol_guard.phase3_min.blender_scene_reader as r
        monkeypatch.setattr(r, "_collect_geometry_scope_objects",
                            lambda **kw: (_ for _ in ()).throw(RuntimeError("x")))
        sc = FakeScene([FakeObj("Cam", "CAMERA"), FakeObj("CT1", "MESH")])
        res = r._check_projection_groups(
            sc, [_pg("g1", ["T1"], cam="Cam", ml=0.3, mr=0.7, mb=0.3, mt=0.7)],
            [_ptr("T1", "CT1")], targets=T1)
        self._e6(res[0], "COLLECT_GEOMETRY_SCOPE")

    def test_resolve_target(self):
        import protocol_guard.phase3_min.blender_scene_reader as r
        sc = FakeScene([FakeObj("Cam", "CAMERA")])
        res = r._check_projection_groups(sc, [_pg("g1", ["T1"], cam="Cam")], [], targets=[])
        self._e6(res[0], "RESOLVE_TARGET_GEOMETRY")

    def test_evaluated_get(self, monkeypatch):
        import protocol_guard.phase3_min.blender_scene_reader as r
        monkeypatch.setattr(FakeObj, "evaluated_get",
                            lambda self, dg: (_ for _ in ()).throw(Exception(_EXC)))
        monkeypatch.setattr(r, "_collect_geometry_scope_objects",
                            lambda **kw: [(FakeObj("CT1", "MESH"), "CT1")])
        sc = FakeScene([FakeObj("Cam", "CAMERA"), FakeObj("CT1", "MESH")])
        res = r._check_projection_groups(
            sc, [_pg("g1", ["T1"], cam="Cam", ml=0.3, mr=0.7, mb=0.3, mt=0.7)],
            [_ptr("T1", "CT1")], targets=T1)
        self._e6(res[0], "EVALUATED_GET")

    def test_to_mesh(self, monkeypatch):
        import protocol_guard.phase3_min.blender_scene_reader as r
        _patch_eval(monkeypatch, FakeEval(None, tm_raise=True))
        monkeypatch.setattr(r, "_collect_geometry_scope_objects",
                            lambda **kw: [(FakeObj("CT1", "MESH"), "CT1")])
        sc = FakeScene([FakeObj("Cam", "CAMERA"), FakeObj("CT1", "MESH")])
        res = r._check_projection_groups(
            sc, [_pg("g1", ["T1"], cam="Cam", ml=0.3, mr=0.7, mb=0.3, mt=0.7)],
            [_ptr("T1", "CT1")], targets=T1)
        self._e6(res[0], "TO_MESH")

    def test_to_mesh_clear(self, monkeypatch):
        import protocol_guard.phase3_min.blender_scene_reader as r
        _patch_eval(monkeypatch, FakeEval(FakeMesh([_mkv(0, 0, -5)]), mw=FakeMW(), tmc_raise=True))
        monkeypatch.setattr(r, "_collect_geometry_scope_objects",
                            lambda **kw: [(FakeObj("CT1", "MESH"), "CT1")])
        sc = FakeScene([FakeObj("Cam", "CAMERA"), FakeObj("CT1", "MESH")])
        res = r._check_projection_groups(
            sc, [_pg("g1", ["T1"], cam="Cam", ml=0.3, mr=0.7, mb=0.3, mt=0.7)],
            [_ptr("T1", "CT1")], targets=T1)
        self._e6(res[0], "TO_MESH_CLEAR")

    def test_read_matrix_world(self, monkeypatch):
        import protocol_guard.phase3_min.blender_scene_reader as r
        _patch_eval(monkeypatch, FakeEval(FakeMesh([_mkv(0, 0, -5)]), mw_raise=True))
        monkeypatch.setattr(r, "_collect_geometry_scope_objects",
                            lambda **kw: [(FakeObj("CT1", "MESH"), "CT1")])
        sc = FakeScene([FakeObj("Cam", "CAMERA"), FakeObj("CT1", "MESH")])
        res = r._check_projection_groups(
            sc, [_pg("g1", ["T1"], cam="Cam", ml=0.3, mr=0.7, mb=0.3, mt=0.7)],
            [_ptr("T1", "CT1")], targets=T1)
        self._e6(res[0], "READ_EVALUATED_MATRIX_WORLD")

    def test_read_mesh_vertices(self, monkeypatch):
        import protocol_guard.phase3_min.blender_scene_reader as r
        _patch_eval(monkeypatch, FakeEval(FakeMesh(count_raise=True), mw=FakeMW()))
        monkeypatch.setattr(r, "_collect_geometry_scope_objects",
                            lambda **kw: [(FakeObj("CT1", "MESH"), "CT1")])
        sc = FakeScene([FakeObj("Cam", "CAMERA"), FakeObj("CT1", "MESH")])
        res = r._check_projection_groups(
            sc, [_pg("g1", ["T1"], cam="Cam", ml=0.3, mr=0.7, mb=0.3, mt=0.7)],
            [_ptr("T1", "CT1")], targets=T1)
        self._e6(res[0], "READ_MESH_VERTICES")

    def test_transform(self, monkeypatch):
        import protocol_guard.phase3_min.blender_scene_reader as r
        class _B:
            def __matmul__(s, v): raise Exception(_EXC)
        _patch_eval(monkeypatch, FakeEval(FakeMesh([_mkv(0, 0, -5)]), mw=_B()))
        monkeypatch.setattr(r, "_collect_geometry_scope_objects",
                            lambda **kw: [(FakeObj("CT1", "MESH"), "CT1")])
        sc = FakeScene([FakeObj("Cam", "CAMERA"), FakeObj("CT1", "MESH")])
        res = r._check_projection_groups(
            sc, [_pg("g1", ["T1"], cam="Cam", ml=0.3, mr=0.7, mb=0.3, mt=0.7)],
            [_ptr("T1", "CT1")], targets=T1)
        self._e6(res[0], "TRANSFORM_VERTEX_TO_WORLD_SPACE")

    def test_resolve_target_amb(self):
        import protocol_guard.phase3_min.blender_scene_reader as r
        sc = FakeScene([FakeObj("Cam", "CAMERA"), FakeObj("CT1", "MESH")])
        res = r._check_projection_groups(
            sc, [_pg("g1", ["T1"], cam="Cam")],
            [_ptr_amb("T1", "CT1")], targets=[_t("T1", "CT1")])
        self._e6(res[0], "RESOLVE_TARGET_GEOMETRY")


# ════════════════ Failure codes ════════════════

class TestFC:
    def _fc(self, g, fc):
        assert g["result"] == "FAIL"
        assert g["failure_code"] == fc
        assert len(g) == 16

    def test_camera_not_found(self):
        import protocol_guard.phase3_min.blender_scene_reader as r
        sc = FakeScene([FakeObj("Cam", "CAMERA"), FakeObj("CT1", "MESH")])
        res = r._check_projection_groups(
            sc, [_pg("g1", ["T1"], cam="Ghost")], [_ptr("T1", "CT1")], targets=T1)
        self._fc(res[0], "CAMERA_OBJECT_NOT_FOUND")

    def test_camera_type_mismatch(self):
        import protocol_guard.phase3_min.blender_scene_reader as r
        sc = FakeScene([FakeObj("NotCam", "MESH"), FakeObj("CT1", "MESH")])
        res = r._check_projection_groups(
            sc, [_pg("g1", ["T1"], cam="NotCam")], [_ptr("T1", "CT1")], targets=T1)
        self._fc(res[0], "CAMERA_TYPE_MISMATCH")

    def test_additional_not_found(self):
        import protocol_guard.phase3_min.blender_scene_reader as r
        sc = FakeScene([FakeObj("Cam", "CAMERA"), FakeObj("CT1", "MESH")])
        res = r._check_projection_groups(
            sc, [_pg("g1", ["T1"], cam="Cam", anames=["Nope"])],
            [_ptr("T1", "CT1")], targets=T1)
        self._fc(res[0], "ADDITIONAL_OBJECT_NOT_FOUND")

    def test_additional_type_mismatch(self):
        import protocol_guard.phase3_min.blender_scene_reader as r
        sc = FakeScene([FakeObj("Cam", "CAMERA"), FakeObj("CT1", "MESH"), FakeObj("Emp", "EMPTY")])
        res = r._check_projection_groups(
            sc, [_pg("g1", ["T1"], cam="Cam", anames=["Emp"])],
            [_ptr("T1", "CT1")], targets=T1)
        self._fc(res[0], "ADDITIONAL_OBJECT_TYPE_MISMATCH")

    def test_root_not_found(self):
        import protocol_guard.phase3_min.blender_scene_reader as r
        sc = FakeScene([FakeObj("Cam", "CAMERA")])
        res = r._check_projection_groups(
            sc, [_pg("g1", ["T1"], cam="Cam")],
            [_ptr("T1", "Missing", ok=False)], targets=[_t("T1", "Missing")])
        self._fc(res[0], "ROOT_OBJECT_NOT_FOUND")

    def test_root_type_mismatch(self):
        import protocol_guard.phase3_min.blender_scene_reader as r
        sc = FakeScene([FakeObj("Cam", "CAMERA"), FakeObj("CT1", "MESH")])
        res = r._check_projection_groups(
            sc, [_pg("g1", ["T1"], cam="Cam")],
            [_ptr_tm("T1", "CT1")], targets=T1)
        self._fc(res[0], "ROOT_OBJECT_TYPE_MISMATCH")

    def test_non_finite(self, monkeypatch):
        import protocol_guard.phase3_min.blender_scene_reader as r
        _patch_eval(monkeypatch, FakeEval(FakeMesh([_mkv(float('inf'), 0, -5)]), mw=FakeMW()))
        monkeypatch.setattr(r, "_collect_geometry_scope_objects",
                            lambda **kw: [(FakeObj("CT1", "MESH"), "CT1")])
        sc = FakeScene([FakeObj("Cam", "CAMERA"), FakeObj("CT1", "MESH")])
        res = r._check_projection_groups(
            sc, [_pg("g1", ["T1"], cam="Cam", ml=0.3, mr=0.7, mb=0.3, mt=0.7)],
            [_ptr("T1", "CT1")], targets=T1)
        self._fc(res[0], "NON_FINITE_EVALUATED_VERTEX")

    def test_no_geometry(self, monkeypatch):
        import protocol_guard.phase3_min.blender_scene_reader as r
        _patch_eval(monkeypatch, FakeEval(FakeMesh([]), mw=FakeMW()))
        monkeypatch.setattr(r, "_collect_geometry_scope_objects",
                            lambda **kw: [(FakeObj("CT1", "MESH"), "CT1")])
        sc = FakeScene([FakeObj("Cam", "CAMERA"), FakeObj("CT1", "MESH")])
        res = r._check_projection_groups(
            sc, [_pg("g1", ["T1"], cam="Cam", ml=0.3, mr=0.7, mb=0.3, mt=0.7)],
            [_ptr("T1", "CT1")], targets=T1)
        self._fc(res[0], "NO_EVALUATED_GEOMETRY")


# ════════════════ PASS ════════════════

class FakeCam:
    def __init__(self, name="Cam", x=0.0, y=0.0, z=10.0):
        self.name = name; self.type = "CAMERA"; self.children = []
        self.matrix_world = FakeCamMW(x, y, z)


class TestPass:
    def test_pass_16_keys(self, monkeypatch):
        import protocol_guard.phase3_min.blender_scene_reader as r
        verts = [_mkv(0.5, 0.5, -5), _mkv(-0.5, 0.5, -5),
                 _mkv(0.5, -0.5, -5), _mkv(-0.5, -0.5, -5)]
        _patch_eval(monkeypatch, FakeEval(FakeMesh(verts), mw=FakeMW()))
        monkeypatch.setattr(r, "_collect_geometry_scope_objects",
                            lambda **kw: [(FakeObj("CT1", "MESH"), "CT1")])
        # Override bpy so depsgraph works for this test specifically
        class _Ctx:
            @staticmethod
            def evaluated_depsgraph_get(): return "dg"
        monkeypatch.setattr(r.bpy, "context", _Ctx())
        sc = FakeScene([FakeCam("Cam", z=10.0), FakeObj("CT1", "MESH")])
        res = r._check_projection_groups(
            sc, [_pg("g1", ["T1"], cam="Cam", ml=0.4, mr=0.6, mb=0.45, mt=0.55)],
            [_ptr("T1", "CT1")], targets=T1)
        g = res[0]
        # If not PASS, show what we got
        if g["result"] != "PASS":
            pytest.fail(f"Expected PASS, got {g['result']} op={g.get('operation','?')} "
                        f"fc={g.get('failure_code','?')} keys={sorted(g.keys())}")
        assert len(g) == 16
        assert g["failure_code"] is None
        assert g["failed_checks"] is None
        assert g["actual_type"] is None


# ════════════════ Counts ════════════════

class TestCounts:
    def test_scene_once(self, monkeypatch):
        import protocol_guard.phase3_min.blender_scene_reader as r
        sc = FakeScene([FakeObj("Cam", "CAMERA"), FakeObj("CT1", "MESH")])
        res = r._check_projection_groups(
            sc,
            [_pg("g1", ["T1"], cam="Cam", ml=0.3, mr=0.7, mb=0.3, mt=0.7),
             _pg("g2", ["T1"], cam="Cam", ml=0.3, mr=0.7, mb=0.3, mt=0.7)],
            [_ptr("T1", "CT1")], targets=T1)
        assert len(res) == 2
        assert sc.count == 1

    def test_target_ids_order(self, monkeypatch):
        import protocol_guard.phase3_min.blender_scene_reader as r
        sc = FakeScene([FakeObj("Cam", "CAMERA"), FakeObj("CT1", "MESH"), FakeObj("CT2", "MESH")])
        res = r._check_projection_groups(
            sc,
            [_pg("g1", ["T2", "T1"], cam="Cam", ml=0.3, mr=0.7, mb=0.3, mt=0.7)],
            [_ptr("T1", "CT1"), _ptr("T2", "CT2")],
            targets=[_t("T1", "CT1"), _t("T2", "CT2")])
        assert res[0]["target_ids"] == ["T2", "T1"]


# ════════════════ Remaining operations ════════════════

class TestRemainingOps:
    def _e6(self, g, op):
        assert g["result"] == "ERROR"
        assert g["error_type"] == "PROJECTION_GROUP_COMPUTATION_ERROR"
        assert g["operation"] == op
        assert len(g) == 6

    def test_compute_union_bbox(self, monkeypatch):
        """COMPUTE_UNION_BBOX: .x throws on second access during min()."""
        import protocol_guard.phase3_min.blender_scene_reader as r

        class BadWorldVert:
            y = 0.0; z = 0.0
            _count = 0
            @property
            def x(self):
                BadWorldVert._count += 1
                if BadWorldVert._count > 1:
                    raise Exception(_EXC)
                return 0.0

        class BadWrappingMW:
            def __matmul__(self, v):
                BadWorldVert._count = 0
                return BadWorldVert()

        _patch_eval(monkeypatch, FakeEval(
            FakeMesh([_mkv(0.5, 0.5, -5)]), mw=BadWrappingMW()))
        monkeypatch.setattr(r, "_collect_geometry_scope_objects",
                            lambda **kw: [(FakeObj("CT1", "MESH"), "CT1")])
        sc = FakeScene([FakeCam("Cam", z=10.0), FakeObj("CT1", "MESH")])
        res = r._check_projection_groups(
            sc, [_pg("g1", ["T1"], cam="Cam", ml=0.4, mr=0.6, mb=0.45, mt=0.55)],
            [_ptr("T1", "CT1")], targets=T1)
        self._e6(res[0], "COMPUTE_UNION_BBOX")

    def test_get_evaluated_depsgraph(self, monkeypatch):
        """GET_EVALUATED_DEPSGRAPH: depsgraph_get() throws."""
        import protocol_guard.phase3_min.blender_scene_reader as r

        class ThrowingCtx:
            @staticmethod
            def evaluated_depsgraph_get():
                raise Exception(_EXC)

        monkeypatch.setattr(r.bpy, "context", ThrowingCtx())

        verts = [_mkv(0.5, 0.5, -5), _mkv(-0.5, 0.5, -5),
                 _mkv(0.5, -0.5, -5), _mkv(-0.5, -0.5, -5)]
        _patch_eval(monkeypatch, FakeEval(FakeMesh(verts), mw=FakeMW()))
        monkeypatch.setattr(r, "_collect_geometry_scope_objects",
                            lambda **kw: [(FakeObj("CT1", "MESH"), "CT1")])
        sc = FakeScene([FakeCam("Cam", z=10.0), FakeObj("CT1", "MESH")])
        res = r._check_projection_groups(
            sc, [_pg("g1", ["T1"], cam="Cam", ml=0.4, mr=0.6, mb=0.45, mt=0.55)],
            [_ptr("T1", "CT1")], targets=T1)
        self._e6(res[0], "GET_EVALUATED_DEPSGRAPH")

    def test_project_bbox_corner(self, monkeypatch):
        """PROJECT_BBOX_CORNER: world_to_camera_view raises."""
        import protocol_guard.phase3_min.blender_scene_reader as r

        # Replace the fake world_to_camera_view with one that throws
        import bpy_extras.object_utils as fou
        monkeypatch.setattr(fou, "world_to_camera_view",
                            lambda sc, cam, v: (_ for _ in ()).throw(Exception(_EXC)))

        verts = [_mkv(0.5, 0.5, -5), _mkv(-0.5, 0.5, -5),
                 _mkv(0.5, -0.5, -5), _mkv(-0.5, -0.5, -5)]
        _patch_eval(monkeypatch, FakeEval(FakeMesh(verts), mw=FakeMW()))
        monkeypatch.setattr(r, "_collect_geometry_scope_objects",
                            lambda **kw: [(FakeObj("CT1", "MESH"), "CT1")])
        sc = FakeScene([FakeCam("Cam", z=10.0), FakeObj("CT1", "MESH")])
        res = r._check_projection_groups(
            sc, [_pg("g1", ["T1"], cam="Cam", ml=0.4, mr=0.6, mb=0.45, mt=0.55)],
            [_ptr("T1", "CT1")], targets=T1)
        self._e6(res[0], "PROJECT_BBOX_CORNER")


# ════════════════ Depsgraph count ════════════════

class TestDepsgraphCount:
    def test_depsgraph_called_once_for_multiple_groups(self, monkeypatch):
        """bpy.context.evaluated_depsgraph_get called exactly once across groups."""
        import protocol_guard.phase3_min.blender_scene_reader as r

        call_count = [0]

        class CountContext:
            @staticmethod
            def evaluated_depsgraph_get():
                call_count[0] += 1
                return "dg"

        monkeypatch.setattr(r.bpy, "context", CountContext())

        verts = [_mkv(0.5, 0.5, -5), _mkv(-0.5, 0.5, -5),
                 _mkv(0.5, -0.5, -5), _mkv(-0.5, -0.5, -5)]
        _patch_eval(monkeypatch, FakeEval(FakeMesh(verts), mw=FakeMW()))
        monkeypatch.setattr(r, "_collect_geometry_scope_objects",
                            lambda **kw: [(FakeObj("CT1", "MESH"), "CT1")])

        sc = FakeScene([FakeCam("Cam", z=10.0), FakeObj("CT1", "MESH")])
        res = r._check_projection_groups(
            sc,
            [_pg("g1", ["T1"], cam="Cam", ml=0.4, mr=0.6, mb=0.45, mt=0.55),
             _pg("g2", ["T1"], cam="Cam", ml=0.4, mr=0.6, mb=0.45, mt=0.55)],
            [_ptr("T1", "CT1")], targets=T1)
        assert len(res) == 2
        for g in res:
            if g["result"] != "PASS":
                pytest.fail(f"Group {g['group_id']}: {g['result']} "
                            f"op={g.get('operation','?')} fc={g.get('failure_code','?')}")
        assert call_count[0] == 1, f"depsgraph called {call_count[0]} times, expected 1"
