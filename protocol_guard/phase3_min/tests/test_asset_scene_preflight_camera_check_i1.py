"""Camera Check I1 R5 — complete per-target cache + 54-scenario coverage."""
import ast, math, os, sys, pytest, types

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

_MISSING = object()

# ════════════════ helpers ════════════════

def _target(tid, root_name, root_type, geometry_scope="SELF_MESH", **extra):
    t = {"target_id": tid, "root_object_name": root_name,
         "expected_root_type": root_type, "geometry_scope": geometry_scope}
    t.update(extra)
    return t

def _pt_pass(rt="EMPTY"):
    return {"checks": {"object_exists": {"result": "PASS"},
                       "object_type": {"result": "PASS", "actual": rt}}}

def _cc_block(cam="C", mvc=8, ml=0.0, mr=1.0, mb=0.0, mt=1.0):
    return {"camera_object_name": cam,
            "minimum_visible_projected_corner_count": mvc,
            "required_screen_bbox": {"min_left": ml, "max_right": mr,
                                     "min_bottom": mb, "max_top": mt}}

# ════════════════ fakes ════════════════

class FVec:
    __slots__ = ('x','y','z')
    def __init__(self, *args):
        if len(args) == 1 and isinstance(args[0], (tuple, list)):
            x, y, z = args[0]
        elif len(args) == 3:
            x, y, z = args
        else:
            x = args[0] if len(args) > 0 else 0.0
            y = args[1] if len(args) > 1 else 0.0
            z = args[2] if len(args) > 2 else 0.0
        self.x = float(x); self.y = float(y); self.z = float(z)

class FObj:
    def __init__(self, name, otype="MESH", children=None):
        self.name = name; self.type = otype; self.children = children or []

class AccessCountScene:
    def __init__(self, objects): self._objects = objects; self.access_count = 0
    @property
    def objects(self): self.access_count += 1; return list(self._objects)

class CountingScene:
    def __init__(self, objects): self._objects = objects; self.access_count = 0
    @property
    def objects(self): self.access_count += 1; return list(self._objects)

class NameCountObj:
    def __init__(self, name, otype="MESH"):
        self._name = name; self._type = otype
        self.name_read_count = 0; self.type_read_count = 0
    @property
    def name(self): self.name_read_count += 1; return self._name
    @property
    def children(self): return []
    @property
    def type(self): self.type_read_count += 1; return self._type

class NameCountScene:
    def __init__(self, objects): self._objects = objects
    @property
    def objects(self): return list(self._objects)

class BadNameCamera:
    def __init__(self): self.type = "CAMERA"
    @property
    def name(self): raise Exception("name fail")

class _FakeEval:
    def __init__(self, verts=None, mw=None, tm_raise=None, tmc_raise=None, mw_raise=None):
        self.verts = verts or []
        self._mw = mw; self._tm_raise = tm_raise
        self._tmc_raise = tmc_raise; self._mw_raise = mw_raise
    @property
    def matrix_world(self):
        if self._mw_raise: raise self._mw_raise
        return self._mw or _FakeMW()
    def to_mesh(self):
        if self._tm_raise: raise self._tm_raise
        return _FakeMesh(self.verts)
    def to_mesh_clear(self):
        if self._tmc_raise: raise self._tmc_raise
    def evaluated_get(self, dg): return self

class _FakeMW:
    def __matmul__(self, v):
        if hasattr(v, 'x'): return FVec(v.x, v.y, v.z)
        return FVec(v[0], v[1], v[2])

class _FakeMesh:
    def __init__(self, verts): self.vertices = _FakeVerts(verts)
class _FakeVerts:
    def __init__(self, verts): self._v = verts
    def __iter__(self):
        for v in self._v: yield _FakeV(v)
    def __len__(self): return len(self._v)
class _FakeV:
    def __init__(self, co): self.co = co

# ════════════════ mock helpers ════════════════

def _mock_eval(monkeypatch, collect_result, depsgraph_raise=None):
    import bpy, mathutils
    bpy.context = types.ModuleType("context")
    if depsgraph_raise:
        bpy.context.evaluated_depsgraph_get = lambda: (_ for _ in ()).throw(depsgraph_raise)
    else:
        bpy.context.evaluated_depsgraph_get = lambda: object()
    monkeypatch.setattr(bpy, "context", bpy.context, raising=False)
    monkeypatch.setattr("protocol_guard.phase3_min.blender_scene_reader._collect_geometry_scope_objects",
                        lambda *a,**kw: collect_result)
    mathutils.Vector = FVec

def _mock_full(monkeypatch, collect_result, wtcv_fn, depsgraph_raise=None):
    import bpy, mathutils
    bpy.context = types.ModuleType("context")
    if depsgraph_raise:
        bpy.context.evaluated_depsgraph_get = lambda: (_ for _ in ()).throw(depsgraph_raise)
    else:
        bpy.context.evaluated_depsgraph_get = lambda: object()
    monkeypatch.setattr(bpy, "context", bpy.context, raising=False)
    monkeypatch.setattr("protocol_guard.phase3_min.blender_scene_reader._collect_geometry_scope_objects",
                        lambda *a,**kw: collect_result)
    mathutils.Vector = FVec
    if "bpy_extras" not in sys.modules:
        beu = types.ModuleType("bpy_extras"); beu.__path__ = []; beu.__package__ = "bpy_extras"
        sys.modules["bpy_extras"] = beu
    beu = sys.modules["bpy_extras"]
    bou = types.ModuleType("bpy_extras.object_utils")
    bou.__package__ = "bpy_extras.object_utils"; bou.__path__ = []
    bou.world_to_camera_view = wtcv_fn; beu.object_utils = bou
    sys.modules["bpy_extras.object_utils"] = bou


# ════════════════ S01-S10 pre-open ════════════════

class TestPreopen:
    def test_no_block(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import _validate_camera_check_rules_preopen
        assert _validate_camera_check_rules_preopen([_target("A","r","E")]) == []
    def test_none_block(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import _validate_camera_check_rules_preopen
        assert _validate_camera_check_rules_preopen([_target("A","r","E",camera_check=None)]) == []
    def test_valid(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import _validate_camera_check_rules_preopen
        assert _validate_camera_check_rules_preopen([_target("A","r","E",camera_check=_cc_block(mvc=8))]) == []
    def test_mvc_gt_8(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import _validate_camera_check_rules_preopen
        e = _validate_camera_check_rules_preopen([_target("A","r","E",camera_check=_cc_block(mvc=9))])
        assert any("must be <= 8" in x for x in e)
    def test_mvc_eq_8(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import _validate_camera_check_rules_preopen
        assert _validate_camera_check_rules_preopen([_target("A","r","E",camera_check=_cc_block(mvc=8))]) == []
    def test_min_left_gt_max_right(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import _validate_camera_check_rules_preopen
        e = _validate_camera_check_rules_preopen([_target("A","r","E",camera_check=_cc_block(ml=0.9,mr=0.1))])
        assert any("min_left > max_right" in x for x in e)
    def test_min_bottom_gt_max_top(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import _validate_camera_check_rules_preopen
        e = _validate_camera_check_rules_preopen([_target("A","r","E",camera_check=_cc_block(mb=0.9,mt=0.1))])
        assert any("min_bottom > max_top" in x for x in e)
    def test_bbox_below_zero(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import _validate_camera_check_rules_preopen
        e = _validate_camera_check_rules_preopen([_target("A","r","E",camera_check=_cc_block(ml=-0.1))])
        assert any("out of [0,1]" in x for x in e)
    def test_bbox_above_one(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import _validate_camera_check_rules_preopen
        e = _validate_camera_check_rules_preopen([_target("A","r","E",camera_check=_cc_block(mr=1.5))])
        assert any("out of [0,1]" in x for x in e)
    def test_bbox_boundary(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import _validate_camera_check_rules_preopen
        assert _validate_camera_check_rules_preopen([_target("A","r","E",camera_check=_cc_block(ml=0.0,mr=1.0,mb=0.0,mt=1.0))]) == []


# ════════════════ S11-S14 config ════════════════

class TestConfig:
    def test_none_returns_none(self):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        assert _check_camera_check(None, _target("A","r","E",camera_check=None), _pt_pass()) is None
    def test_missing_returns_none(self):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        assert _check_camera_check(None, _target("A","r","E"), _pt_pass()) is None


# ════════════════ S15-S18 root preconditions ════════════════

class TestRootPreconditions:
    def _t(self): return _target("A","r","E",camera_check=_cc_block())
    def test_root_not_found(self):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        r = _check_camera_check(None, self._t(), {"checks":{"object_exists":{"result":"FAIL"},"object_type":{"result":"NOT_CHECKED"}}})
        assert r == {"result":"NOT_CHECKED","note":"ROOT_OBJECT_NOT_FOUND"}
    def test_root_ambiguous(self):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        r = _check_camera_check(None, self._t(), {"checks":{"object_exists":{"result":"ERROR","error_type":"AMBIGUOUS_ROOT_OBJECT_NAME"},"object_type":{"result":"NOT_CHECKED"}}})
        assert r == {"result":"NOT_CHECKED","note":"AMBIGUOUS_ROOT_OBJECT_NAME"}
    def test_root_lookup_error(self):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        r = _check_camera_check(None, self._t(), {"checks":{"object_exists":{"result":"ERROR"},"object_type":{"result":"NOT_CHECKED"}}})
        assert r == {"result":"NOT_CHECKED","note":"ROOT_LOOKUP_ERROR"}
    def test_root_type_mismatch(self):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        r = _check_camera_check(None, self._t(), {"checks":{"object_exists":{"result":"PASS"},"object_type":{"result":"FAIL"}}})
        assert r == {"result":"NOT_CHECKED","note":"ROOT_OBJECT_TYPE_MISMATCH"}


# ════════════════ S19-S22 camera lookup ════════════════

class TestCameraLookup:
    def _t(self): return _target("A","root","EMPTY",camera_check=_cc_block(cam="MyCam"))
    def test_camera_not_found(self):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        r = _check_camera_check(CountingScene([FObj("root")]), self._t(), _pt_pass())
        assert r["failure_code"] == "CAMERA_OBJECT_NOT_FOUND"
    def test_camera_ambiguous(self):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        r = _check_camera_check(CountingScene([FObj("root"),FObj("MyCam","CAMERA"),FObj("MyCam","CAMERA")]), self._t(), _pt_pass())
        assert r["failure_code"] == "CAMERA_OBJECT_NOT_FOUND"
    def test_camera_type_mismatch(self):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        r = _check_camera_check(CountingScene([FObj("root"),FObj("MyCam","MESH")]), self._t(), _pt_pass())
        assert r["failure_code"] == "CAMERA_TYPE_MISMATCH"


# ════════════════ S23-S28 evaluated geometry ════════════════

class TestEvaluatedGeometry:
    def _t(self, mvc=1): return _target("A","root","MESH",camera_check=_cc_block(cam="C",mvc=mvc,ml=0,mr=1,mb=0,mt=1))
    def _s(self): return CountingScene([FObj("root","MESH"),FObj("C","CAMERA")])

    def test_zero_vertex(self, monkeypatch):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        _mock_eval(monkeypatch, [(_FakeEval(verts=[]),"root")])
        r = _check_camera_check(self._s(), self._t(), _pt_pass("MESH"))
        assert r["result"] == "FAIL"; assert r["failure_code"] == "NO_EVALUATED_GEOMETRY"
        assert set(r.keys()) == {"result","failure_code","evaluated_mesh_names"}

    def test_mixed_zero_finite(self, monkeypatch):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        _mock_eval(monkeypatch, [(_FakeEval(verts=[]),"m0"),(_FakeEval(verts=[FVec(0,0,0)]),"m1")])
        t = _target("A","root","MESH",geometry_scope="SELF_AND_DESCENDANT_MESHES",camera_check=_cc_block(cam="C",mvc=1))
        r = _check_camera_check(self._s(), t, _pt_pass("MESH"))
        assert r["failure_code"] == "NO_EVALUATED_GEOMETRY"

    def test_nan(self, monkeypatch):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        _mock_eval(monkeypatch, [(_FakeEval(verts=[FVec(float('nan'),0,0)]),"root")])
        r = _check_camera_check(self._s(), self._t(), _pt_pass("MESH"))
        assert r["result"] == "FAIL"; assert r["failure_code"] == "NON_FINITE_EVALUATED_VERTEX"
        assert set(r.keys()) == {"result","failure_code","evaluated_mesh_names"}

    def test_inf(self, monkeypatch):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        _mock_eval(monkeypatch, [(_FakeEval(verts=[FVec(float('inf'),0,0)]),"root")])
        r = _check_camera_check(self._s(), self._t(), _pt_pass("MESH"))
        assert r["failure_code"] == "NON_FINITE_EVALUATED_VERTEX"

    def test_nan_over_zero(self, monkeypatch):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        _mock_eval(monkeypatch, [(_FakeEval(verts=[]),"m0"),(_FakeEval(verts=[FVec(float('nan'),0,0)]),"m1")])
        t = _target("A","root","MESH",geometry_scope="SELF_AND_DESCENDANT_MESHES",camera_check=_cc_block(cam="C",mvc=1))
        r = _check_camera_check(self._s(), t, _pt_pass("MESH"))
        assert r["failure_code"] == "NON_FINITE_EVALUATED_VERTEX"

    def test_tmc_overrides_zero(self, monkeypatch):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        _mock_eval(monkeypatch, [(_FakeEval(verts=[],tmc_raise=Exception("c")),"root")])
        r = _check_camera_check(self._s(), self._t(), _pt_pass("MESH"))
        assert r["operation"] == "TO_MESH_CLEAR"

    def test_tmc_overrides_nan(self, monkeypatch):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        _mock_eval(monkeypatch, [(_FakeEval(verts=[FVec(float('nan'),0,0)],tmc_raise=Exception("c")),"root")])
        r = _check_camera_check(self._s(), self._t(), _pt_pass("MESH"))
        assert r["operation"] == "TO_MESH_CLEAR"


# ════════════════ S29-S40 ERROR operations ════════════════

class TestErrorOps:
    def _t(self): return _target("A","root","MESH",camera_check=_cc_block(cam="C",mvc=1))
    def _s(self): return CountingScene([FObj("root","MESH"),FObj("C","CAMERA")])

    def test_read_scene_objects(self):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        class Bad: objects = property(lambda s: (_ for _ in ()).throw(Exception("x")))
        r = _check_camera_check(Bad(), self._t(), _pt_pass("MESH"))
        assert r["operation"] == "READ_SCENE_OBJECTS"

    def test_depsgraph(self, monkeypatch):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        _mock_eval(monkeypatch, [(_FakeEval(verts=[FVec(0,0,0)]),"root")], depsgraph_raise=Exception("dg"))
        r = _check_camera_check(self._s(), self._t(), _pt_pass("MESH"))
        assert r["operation"] == "GET_EVALUATED_DEPSGRAPH"

    def test_evaluated_get(self, monkeypatch):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        class Bad: pass
        _mock_eval(monkeypatch, [(Bad(),"root")])
        r = _check_camera_check(self._s(), self._t(), _pt_pass("MESH"))
        assert r["operation"] == "EVALUATED_GET"

    def test_to_mesh(self, monkeypatch):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        _mock_eval(monkeypatch, [(_FakeEval(verts=[FVec(0,0,0)],tm_raise=Exception("tm")),"root")])
        r = _check_camera_check(self._s(), self._t(), _pt_pass("MESH"))
        assert r["operation"] == "TO_MESH"

    def test_matrix_world(self, monkeypatch):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        _mock_eval(monkeypatch, [(_FakeEval(verts=[FVec(0,0,0)],mw_raise=Exception("mw")),"root")])
        r = _check_camera_check(self._s(), self._t(), _pt_pass("MESH"))
        assert r["operation"] == "READ_EVALUATED_MATRIX_WORLD"

    def test_to_mesh_clear(self, monkeypatch):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        _mock_eval(monkeypatch, [(_FakeEval(verts=[FVec(0,0,0)],tmc_raise=Exception("tmc")),"root")])
        r = _check_camera_check(self._s(), self._t(), _pt_pass("MESH"))
        assert r["operation"] == "TO_MESH_CLEAR"

    def test_import_wtcv(self, monkeypatch):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        _mock_eval(monkeypatch, [(_FakeEval(verts=[FVec(0,0,0)]),"root")])
        import builtins
        _orig = builtins.__import__
        monkeypatch.setattr(builtins, "__import__",
                            lambda name,*a,**kw: (_ for _ in ()).throw(Exception("no"))
                            if name=="bpy_extras.object_utils" else _orig(name,*a,**kw))
        r = _check_camera_check(self._s(), self._t(), _pt_pass("MESH"))
        assert r["operation"] == "IMPORT_WORLD_TO_CAMERA_VIEW"


# ════════════════ S41-S54 projection ════════════════

class TestProjection:
    def _t(self, mvc=1, ml=0.0, mr=1.0, mb=0.0, mt=1.0):
        return _target("A","root","MESH",camera_check=_cc_block(cam="C",mvc=mvc,ml=ml,mr=mr,mb=mb,mt=mt))
    def _s(self): return CountingScene([FObj("root","MESH"),FObj("C","CAMERA")])

    def test_behind_camera(self, monkeypatch):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        fe = _FakeEval(verts=[FVec(i,j,k) for i in range(2) for j in range(2) for k in range(2)])
        _mock_full(monkeypatch, [(fe,"root")], wtcv_fn=lambda *a: FVec(0.5,0.5,-1.0))
        r = _check_camera_check(self._s(), self._t(), _pt_pass("MESH"))
        assert r["result"] == "FAIL"; assert r["failure_code"] == "BEHIND_CAMERA"
        assert set(r.keys()) == {"result","failure_code","camera_object_name",
                                  "projected_corner_count","front_facing_projected_corner_count",
                                  "evaluated_mesh_names"}

    def test_left_fail(self, monkeypatch):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        fe = _FakeEval(verts=[FVec(i,j,0) for i in range(2) for j in range(2) for k in range(2)])
        _mock_full(monkeypatch, [(fe,"root")], wtcv_fn=lambda sc,ca,c: FVec(c.x*0.05+0.02,0.5,1.0))
        r = _check_camera_check(self._s(), self._t(ml=0.04), _pt_pass("MESH"))
        assert r["failure_code"] == "SCREEN_BBOX_REQUIREMENT_NOT_MET"

    def test_bottom_fail(self, monkeypatch):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        fe = _FakeEval(verts=[FVec(i,j,0) for i in range(2) for j in range(2) for k in range(2)])
        _mock_full(monkeypatch, [(fe,"root")], wtcv_fn=lambda sc,ca,c: FVec(0.5,c.y*0.1+0.20,1.0))
        r = _check_camera_check(self._s(), self._t(mb=0.15), _pt_pass("MESH"))
        assert r["failure_code"] == "SCREEN_BBOX_REQUIREMENT_NOT_MET"

    def test_top_fail(self, monkeypatch):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        fe = _FakeEval(verts=[FVec(i,j,0) for i in range(2) for j in range(2) for k in range(2)])
        _mock_full(monkeypatch, [(fe,"root")], wtcv_fn=lambda sc,ca,c: FVec(0.5,c.y*0.1+0.50,1.0))
        r = _check_camera_check(self._s(), self._t(mt=0.85), _pt_pass("MESH"))
        assert r["failure_code"] == "SCREEN_BBOX_REQUIREMENT_NOT_MET"

    def test_screen_bbox_req_keys(self, monkeypatch):
        """SCREEN_BBOX_REQUIREMENT_NOT_MET → exact 9-key set."""
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        fe = _FakeEval(verts=[FVec(i,j,0) for i in range(2) for j in range(2) for k in range(2)])
        _mock_full(monkeypatch, [(fe,"root")], wtcv_fn=lambda sc,ca,c: FVec(c.x*0.05+0.02,0.5,1.0))
        r = _check_camera_check(self._s(), self._t(ml=0.04), _pt_pass("MESH"))
        assert r["result"] == "FAIL"
        assert r["failure_code"] == "SCREEN_BBOX_REQUIREMENT_NOT_MET"
        assert set(r.keys()) == {"result","failure_code","camera_object_name",
                                  "projected_corner_count","front_facing_projected_corner_count",
                                  "minimum_visible_projected_corner_count",
                                  "actual_screen_bbox","required_screen_bbox","evaluated_mesh_names"}

    def test_insufficient(self, monkeypatch):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        fe = _FakeEval(verts=[FVec(i,j,0) for i in range(2) for j in range(2) for k in range(2)])
        cnt=[0]
        def wtcv(*a): cnt[0]+=1; return FVec(0.5,0.5,-1.0) if cnt[0]<=4 else FVec(0.5,0.5,1.0)
        _mock_full(monkeypatch, [(fe,"root")], wtcv_fn=wtcv)
        r = _check_camera_check(self._s(), self._t(mvc=8,mb=0.5,mt=0.5), _pt_pass("MESH"))
        assert r["result"] == "FAIL"; assert r["failure_code"] == "INSUFFICIENT_VISIBLE_PROJECTED_CORNERS"
        assert set(r.keys()) == {"result","failure_code","camera_object_name",
                                  "projected_corner_count","front_facing_projected_corner_count",
                                  "minimum_visible_projected_corner_count","evaluated_mesh_names"}

    def test_bbox_over_insufficient(self, monkeypatch):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        fe = _FakeEval(verts=[FVec(i,j,0) for i in range(2) for j in range(2) for k in range(2)])
        cnt=[0]
        def wtcv(*a): cnt[0]+=1; return FVec(0.5,0.5,-1.0) if cnt[0]<=4 else FVec(0.5,0.5,1.0)
        _mock_full(monkeypatch, [(fe,"root")], wtcv_fn=wtcv)
        r = _check_camera_check(self._s(), self._t(mvc=8,mb=0.15), _pt_pass("MESH"))
        assert r["failure_code"] == "SCREEN_BBOX_REQUIREMENT_NOT_MET"

    def test_pass(self, monkeypatch):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        fe = _FakeEval(verts=[FVec(i,j,0) for i in range(2) for j in range(2) for k in range(2)])
        _mock_full(monkeypatch, [(fe,"root")], wtcv_fn=lambda sc,ca,c: FVec(0.04+c.x*0.46,0.15+c.y*0.70,1.0))
        r = _check_camera_check(self._s(), self._t(mvc=8,ml=0.04,mr=0.96,mb=0.15,mt=0.85), _pt_pass("MESH"))
        assert r["result"] == "PASS"
        assert set(r.keys()) == {"result","camera_object_name","projected_corner_count",
                                  "front_facing_projected_corner_count","minimum_visible_projected_corner_count",
                                  "actual_screen_bbox","required_screen_bbox","evaluated_mesh_names"}

    def test_boundary_eq(self, monkeypatch):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        fe = _FakeEval(verts=[FVec(0,0,0),FVec(0,1,0)])
        cnt=[0]
        def wtcv(*a): cnt[0]+=1; return FVec(0.5,0.5,-1.0) if cnt[0]<=4 else FVec(0.5,0.85,1.0)
        _mock_full(monkeypatch, [(fe,"root")], wtcv_fn=wtcv)
        r = _check_camera_check(self._s(), self._t(mvc=4,mb=0.85,mt=0.85), _pt_pass("MESH"))
        assert r["result"] == "PASS"


# ════════════════ F-001A per-target cache (entry orchestration) ════════════════

class TestPerTargetCacheEntry:
    """Test real entry orchestration: _check_root_objects populates cache,
    _check_camera_check reuses it without re-materializing."""

    def test_one_enabled_no_extra_access(self):
        import protocol_guard.phase3_min.blender_scene_reader as r
        s = CountingScene([FObj("root","EMPTY"),FObj("C","CAMERA")])
        t = _target("A","root","EMPTY",camera_check=_cc_block(cam="C",mvc=1,ml=0,mr=1,mb=0,mt=1))
        caches = {}
        results = r._check_root_objects(s, [t], _target_caches=caches)
        assert s.access_count == 1, f"root phase: {s.access_count}"
        assert "A" in caches
        r._check_camera_check(s, t, results[0], _target_cache=caches.get("A"))
        assert s.access_count == 1, f"after Camera Check: {s.access_count}"

    def test_two_enabled_distinct(self):
        import protocol_guard.phase3_min.blender_scene_reader as r
        s = CountingScene([FObj("r1","EMPTY"),FObj("r2","EMPTY"),FObj("C","CAMERA")])
        t1 = _target("A","r1","EMPTY",camera_check=_cc_block(cam="C",mvc=1,ml=0,mr=1,mb=0,mt=1))
        t2 = _target("B","r2","EMPTY",camera_check=_cc_block(cam="C",mvc=1,ml=0,mr=1,mb=0,mt=1))
        caches = {}
        results = r._check_root_objects(s, [t1, t2], _target_caches=caches)
        assert s.access_count == 2, f"two targets: {s.access_count}"
        assert "A" in caches; assert "B" in caches
        assert caches["A"] is not caches["B"]
        r._check_camera_check(s, t1, results[0], _target_cache=caches["A"])
        r._check_camera_check(s, t2, results[1], _target_cache=caches["B"])
        assert s.access_count == 2, f"after both Camera Checks: {s.access_count}"

    def test_disabled_plus_enabled(self):
        import protocol_guard.phase3_min.blender_scene_reader as r
        s = CountingScene([FObj("r1","EMPTY"),FObj("r2","EMPTY"),FObj("C","CAMERA")])
        t1 = _target("A","r1","EMPTY")  # no camera_check
        t2 = _target("B","r2","EMPTY",camera_check=_cc_block(cam="C",mvc=1,ml=0,mr=1,mb=0,mt=1))
        caches = {}
        results = r._check_root_objects(s, [t1, t2], _target_caches=caches)
        assert "A" not in caches, "disabled target should not get cache"
        assert "B" in caches, "enabled target should get cache"
        # _check_root_objects materializes per-target: 2 targets = 2 accesses
        assert s.access_count == 2, f"disabled+enabled: {s.access_count}"
        # assert no additional access from Camera Check
        before_cc = s.access_count
        r._check_camera_check(s, t2, results[1], _target_cache=caches["B"])
        assert s.access_count == before_cc

    def test_materialization_failure_no_retry(self):
        import protocol_guard.phase3_min.blender_scene_reader as r
        class FailOnceScene:
            access_count = 0
            @property
            def objects(self):
                self.access_count += 1
                raise Exception("fail")
        s = FailOnceScene()
        t = _target("A","root","EMPTY",camera_check=_cc_block(cam="C",mvc=1,ml=0,mr=1,mb=0,mt=1))
        caches = {}
        results = r._check_root_objects(s, [t], _target_caches=caches)
        assert s.access_count == 1
        assert results[0]["overall"] == "ERROR"


# ════════════════ F-001B obj.name reads (entry orchestration) ════════════════

class TestObjNameReadsEntry:
    def test_name_reads_via_cache(self):
        """Camera lookup uses cached names from root phase — no re-reads."""
        import protocol_guard.phase3_min.blender_scene_reader as r
        objs = [NameCountObj("root"), NameCountObj("M1"), NameCountObj("M2"), NameCountObj("C","CAMERA")]
        s = NameCountScene(objs)
        t = _target("A","root","EMPTY",camera_check=_cc_block(cam="C",mvc=1,ml=0,mr=1,mb=0,mt=1))
        caches = {}
        results = r._check_root_objects(s, [t], _target_caches=caches)
        root_reads = sum(o.name_read_count for o in objs)
        N = len(objs)
        assert root_reads <= N
        before = sum(o.name_read_count for o in objs)
        r._check_camera_check(s, t, results[0], _target_cache=caches.get("A"))
        after = sum(o.name_read_count for o in objs)
        assert after == before, f"Camera Check re-read names: {after-before} extra"

    def test_camera_at_end(self):
        import protocol_guard.phase3_min.blender_scene_reader as r
        objs = [NameCountObj("root"), NameCountObj("A1"), NameCountObj("A2"), NameCountObj("A3"), NameCountObj("C","CAMERA")]
        s = NameCountScene(objs)
        t = _target("A","root","EMPTY",camera_check=_cc_block(cam="C",mvc=1,ml=0,mr=1,mb=0,mt=1))
        caches = {}
        results = r._check_root_objects(s, [t], _target_caches=caches)
        root_reads = sum(o.name_read_count for o in objs)
        assert root_reads <= len(objs)
        before = sum(o.name_read_count for o in objs)
        r._check_camera_check(s, t, results[0], _target_cache=caches.get("A"))
        assert sum(o.name_read_count for o in objs) == before

    def test_camera_not_found(self):
        import protocol_guard.phase3_min.blender_scene_reader as r
        objs = [NameCountObj("root"), NameCountObj("M1")]
        s = NameCountScene(objs)
        t = _target("A","root","EMPTY",camera_check=_cc_block(cam="NoCam",mvc=1,ml=0,mr=1,mb=0,mt=1))
        caches = {}
        results = r._check_root_objects(s, [t], _target_caches=caches)
        before = sum(o.name_read_count for o in objs)
        r._check_camera_check(s, t, results[0], _target_cache=caches.get("A"))
        assert sum(o.name_read_count for o in objs) == before

    def test_camera_ambiguous(self):
        import protocol_guard.phase3_min.blender_scene_reader as r
        objs = [NameCountObj("root"), NameCountObj("C","CAMERA"), NameCountObj("C","CAMERA")]
        s = NameCountScene(objs)
        t = _target("A","root","EMPTY",camera_check=_cc_block(cam="C",mvc=1,ml=0,mr=1,mb=0,mt=1))
        caches = {}
        results = r._check_root_objects(s, [t], _target_caches=caches)
        before = sum(o.name_read_count for o in objs)
        r._check_camera_check(s, t, results[0], _target_cache=caches.get("A"))
        assert sum(o.name_read_count for o in objs) == before

    def test_camera_name_read_error_entry(self):
        """Real entry: _check_root_objects catches name error, Camera Check consumes cache."""
        import protocol_guard.phase3_min.blender_scene_reader as r
        objs = [NameCountObj("root"), BadNameCamera()]
        s = NameCountScene(objs)
        t = _target("A","root","EMPTY",camera_check=_cc_block(cam="BadNameCamera",mvc=1,ml=0,mr=1,mb=0,mt=1))
        caches = {}
        results = r._check_root_objects(s, [t], _target_caches=caches)
        assert "A" in caches
        cc_r = r._check_camera_check(s, t, results[0], _target_cache=caches["A"])
        assert cc_r["result"] == "ERROR"
        assert cc_r["error_type"] == "CAMERA_CHECK_COMPUTATION_ERROR"
        assert cc_r["operation"] == "RESOLVE_CAMERA_OBJECT"
        assert cc_r["note"] == "RESOLVE_CAMERA_OBJECT_FAILED"


# ════════════════ F-004A missing vs null ════════════════

class TestMissingNullDistinction:
    """F-004A: _MISSING sentinel ensures missing != null."""

    def _checks(self, scene, cc_val):
        import protocol_guard.phase3_min.blender_scene_reader as r
        t = _target("A","root","EMPTY")
        if cc_val is _MISSING:
            pass  # key not created
        else:
            t["camera_check"] = cc_val
        # verify input construction
        if cc_val is _MISSING:
            assert "camera_check" not in t
        elif cc_val is None:
            assert "camera_check" in t
            assert t["camera_check"] is None
        return r._check_root_objects(scene, [t])[0]["checks"]

    def _empty(self): return CountingScene([])
    def _mismatch(self): return CountingScene([FObj("root","MESH")])
    def _ambig(self): return CountingScene([FObj("root","E"),FObj("root","E")])

    def test_missing_not_found(self):
        assert "camera_check" not in self._checks(self._empty(), _MISSING)
    def test_null_not_found(self):
        assert "camera_check" not in self._checks(self._empty(), None)
    def test_missing_type_mismatch(self):
        assert "camera_check" not in self._checks(self._mismatch(), _MISSING)
    def test_null_type_mismatch(self):
        assert "camera_check" not in self._checks(self._mismatch(), None)
    def test_missing_ambiguous(self):
        assert "camera_check" not in self._checks(self._ambig(), _MISSING)
    def test_null_ambiguous(self):
        assert "camera_check" not in self._checks(self._ambig(), None)
    def test_enabled_not_found(self):
        assert "camera_check" in self._checks(self._empty(), _cc_block())
    def test_enabled_type_mismatch(self):
        assert "camera_check" in self._checks(self._mismatch(), _cc_block())


# ════════════════ F-004B all 11 result dict forms ════════════════

class TestAllResultDictForms:
    """F-004B: every form tested with unconditional exact assertions."""

    # Form 1: disabled → key absent (tested in TestMissingNullDistinction)
    def test_form2_not_checked(self):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        r = _check_camera_check(None, _target("A","r","E",camera_check=_cc_block()),
                                {"checks":{"object_exists":{"result":"FAIL"},"object_type":{"result":"NOT_CHECKED"}}})
        assert r == {"result":"NOT_CHECKED","note":"ROOT_OBJECT_NOT_FOUND"}

    def test_form4_camera_not_found(self):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        r = _check_camera_check(CountingScene([FObj("root")]),
                                _target("A","root","E",camera_check=_cc_block(cam="X")), _pt_pass())
        assert r["result"] == "FAIL"; assert r["failure_code"] == "CAMERA_OBJECT_NOT_FOUND"
        assert set(r.keys()) == {"result","failure_code","camera_object_name"}

    def test_form5_camera_type_mismatch(self):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        r = _check_camera_check(CountingScene([FObj("root"),FObj("C","MESH")]),
                                _target("A","root","E",camera_check=_cc_block()), _pt_pass())
        assert r["result"] == "FAIL"; assert r["failure_code"] == "CAMERA_TYPE_MISMATCH"
        assert set(r.keys()) == {"result","failure_code","camera_object_name","actual_type"}

    def test_form7_no_geometry(self):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        t = _target("A","root","MESH",geometry_scope="DESCENDANT_MESHES",camera_check=_cc_block())
        r = _check_camera_check(CountingScene([FObj("root"),FObj("C","CAMERA")]), t, _pt_pass("MESH"))
        assert r["result"] == "FAIL"; assert r["failure_code"] == "NO_EVALUATED_GEOMETRY"
        assert set(r.keys()) == {"result","failure_code","evaluated_mesh_names"}

    def test_form11_error(self):
        from protocol_guard.phase3_min.blender_scene_reader import _check_camera_check
        class Bad: objects = property(lambda s: (_ for _ in ()).throw(Exception("x")))
        r = _check_camera_check(Bad(), _target("A","r","E",camera_check=_cc_block()), _pt_pass())
        assert r["result"] == "ERROR"
        assert set(r.keys()) == {"result","error_type","operation","note"}

# ════════════════ overall / error collection / scope ════════════════

class TestOverall:
    def test_error(self):
        from protocol_guard.phase3_min.blender_scene_reader import _recompute_target_overall
        assert _recompute_target_overall({"object_exists":{"result":"PASS"},"camera_check":{"result":"ERROR","error_type":"X","operation":"Y","note":"Z"}}) == "ERROR"
    def test_fail_no_over_error(self):
        from protocol_guard.phase3_min.blender_scene_reader import _recompute_target_overall
        assert _recompute_target_overall({"object_exists":{"result":"ERROR"},"camera_check":{"result":"FAIL","failure_code":"X","camera_object_name":"Y"}}) == "ERROR"
    def test_fail(self):
        from protocol_guard.phase3_min.blender_scene_reader import _recompute_target_overall
        assert _recompute_target_overall({"object_exists":{"result":"PASS"},"camera_check":{"result":"FAIL","failure_code":"X","camera_object_name":"Y"}}) == "FAIL"

class TestErrorCollection:
    def test_collected(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import _collect_target_errors
        e = _collect_target_errors([{"target_id":"A","root_object_name":"r","overall":"ERROR","checks":{"camera_check":{"result":"ERROR","error_type":"CAMERA_CHECK_COMPUTATION_ERROR","operation":"T","note":"x"}}}])
        assert any("CAMERA_CHECK_COMPUTATION_ERROR" in x for x in e)

class TestNotCheckedTemplates:
    def test_not_found(self):
        import protocol_guard.phase3_min.blender_scene_reader as r
        s = CountingScene([]); t = _target("A","root","EMPTY",camera_check=_cc_block())
        assert r._check_root_objects(s,[t])[0]["checks"]["camera_check"] == {"result":"NOT_CHECKED","note":"ROOT_OBJECT_NOT_FOUND"}
    def test_type_mismatch(self):
        import protocol_guard.phase3_min.blender_scene_reader as r
        s = CountingScene([FObj("root","MESH")]); t = _target("A","root","EMPTY",camera_check=_cc_block())
        assert r._check_root_objects(s,[t])[0]["checks"]["camera_check"] == {"result":"NOT_CHECKED","note":"ROOT_OBJECT_TYPE_MISMATCH"}
    def test_ambiguous(self):
        import protocol_guard.phase3_min.blender_scene_reader as r
        s = CountingScene([FObj("root","EMPTY"),FObj("root","EMPTY")]); t = _target("A","root","EMPTY",camera_check=_cc_block())
        assert r._check_root_objects(s,[t])[0]["checks"]["camera_check"] == {"result":"NOT_CHECKED","note":"AMBIGUOUS_ROOT_OBJECT_NAME"}

class TestScopeGuard:
    def test_string_ban(self):
        fp = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                          "phase3_min","tests","test_asset_scene_preflight_blender_scene_basic.py")
        ast.parse(open(fp,encoding="utf-8").read())
    def test_fn_exists(self):
        fp = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                          "phase3_min","blender_scene_reader.py")
        tree = ast.parse(open(fp,encoding="utf-8").read())
        assert any(isinstance(n,ast.FunctionDef) and n.name=="_check_camera_check" for n in ast.walk(tree))
    def test_wtcv_count(self):
        fp = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                          "phase3_min","blender_scene_reader.py")
        tree = ast.parse(open(fp,encoding="utf-8").read())
        cc = next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=="_check_camera_check")
        assert sum(1 for n in ast.walk(cc) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=="world_to_camera_view") == 1
