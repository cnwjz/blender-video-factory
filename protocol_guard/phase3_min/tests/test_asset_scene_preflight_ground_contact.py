"""Ground Contact focused tests — config, algorithm, ERROR, result dicts,
overall aggregation, error collection, entry integration, cleanup, dedup,
read counts.

All tests run in CPython with fake/mock objects. No Blender dependency.
Covers Design R2 §17 matrix.
"""
import math
import types
import pytest
from protocol_guard.phase3_min.asset_scene_preflight_check import (
    _validate_ground_contact_rules_preopen,
    _collect_target_errors,
)
from protocol_guard.phase3_min.blender_scene_reader import (
    _check_ground_contact,
    _recompute_target_overall,
)
from protocol_guard.phase3_min.tests.assertions import (
    assert_dict_equal,
)


# ═══════════════════════ bpy context mock ═══════════════════════

class _FakeBpyContext:
    """Mock bpy.context with configurable depsgraph and call counter."""
    def __init__(self):
        self._depsgraph = object()
        self._depsgraph_raises = None
        self.call_count = 0

    def set_depsgraph_raises(self, exc):
        self._depsgraph_raises = exc

    def evaluated_depsgraph_get(self):
        self.call_count += 1
        if self._depsgraph_raises:
            raise self._depsgraph_raises
        return self._depsgraph


@pytest.fixture(autouse=True)
def _ensure_bpy_context():
    """Ensure bpy.context mock exists for all tests."""
    import sys
    bpy = sys.modules.get("bpy")
    if bpy is None:
        bpy = types.ModuleType("bpy")
        sys.modules["bpy"] = bpy
    had_context = hasattr(bpy, "context")
    saved_context = bpy.__dict__.get("context") if had_context else None
    ctx = _FakeBpyContext()
    bpy.context = ctx
    yield
    if had_context:
        bpy.context = saved_context
    else:
        try:
            del bpy.context
        except (AttributeError, KeyError):
            pass


# ═══════════════════════ helpers ═══════════════════════

def _gc_block(gz, tol):
    return {"ground_z": gz, "ground_contact_tolerance": tol}


def _target(tid="T1", gc=None, geometry_scope="DESCENDANT_MESHES",
            root_object_name="root"):
    t = {
        "target_id": tid,
        "root_object_name": root_object_name,
        "geometry_scope": geometry_scope,
    }
    if gc is not None:
        t["ground_contact"] = gc
    return t


def _root_pass(root_type="EMPTY"):
    return {"checks": {"object_exists": {"result": "PASS"},
                       "object_type": {"result": "PASS", "actual": root_type}}}


def _root_not_found():
    return {"checks": {"object_exists": {"result": "FAIL"},
                       "object_type": {"result": "NOT_CHECKED"}}}


def _root_ambiguous():
    return {"checks": {"object_exists": {"result": "ERROR",
                "error_type": "AMBIGUOUS_ROOT_OBJECT_NAME", "match_count": 3},
                       "object_type": {"result": "NOT_CHECKED"}}}


def _root_lookup_error():
    return {"checks": {"object_exists": {"result": "ERROR",
                "error_type": "DIRECT_CHILD_LOOKUP_ERROR"},
                       "object_type": {"result": "NOT_CHECKED"}}}


def _root_type_mismatch():
    return {"checks": {"object_exists": {"result": "PASS"},
                       "object_type": {"result": "FAIL",
                                       "expected": "EMPTY", "actual": "MESH"}}}


# ── fake Blender objects ──────────────────────────────────────────────────

class FakeMesh:
    def __init__(self, vertices):
        self.vertices = [FakeVertex(v) for v in vertices]


class FakeVertex:
    def __init__(self, co):
        self._co = co
        self._co_raises = None

    @property
    def co(self):
        if self._co_raises:
            raise self._co_raises
        return FakeVector(self._co)

    def set_co_raises(self, exc):
        self._co_raises = exc


class FakeVector:
    def __init__(self, co):
        self._co = tuple(co)
    @property
    def x(self): return self._co[0]
    @property
    def y(self): return self._co[1]
    @property
    def z(self): return self._co[2]


class FakeMatrixWorld:
    def __init__(self, offset=(0, 0, 0), scale=(1, 1, 1)):
        self._offset = offset; self._scale = scale
        self.read_count = 0

    def __matmul__(self, vertex_co):
        return FakeVector((
            vertex_co.x * self._scale[0] + self._offset[0],
            vertex_co.y * self._scale[1] + self._offset[1],
            vertex_co.z * self._scale[2] + self._offset[2],
        ))


class FakeEvaluated:
    def __init__(self, mesh=None, mw=None, to_mesh_raises=None,
                 to_mesh_clear_raises=None, mw_raises=None):
        self._mesh = mesh
        self._mw = mw if mw is not None else FakeMatrixWorld()
        self._to_mesh_raises = to_mesh_raises
        self._to_mesh_clear_raises = to_mesh_clear_raises
        self._mw_raises = mw_raises
        self._cleared = False
        self.matrix_world_read_count = 0

    def to_mesh(self):
        if self._to_mesh_raises:
            raise self._to_mesh_raises
        return self._mesh if self._mesh is not None else FakeMesh([])

    def to_mesh_clear(self):
        self._cleared = True
        if self._to_mesh_clear_raises:
            raise self._to_mesh_clear_raises

    @property
    def matrix_world(self):
        self.matrix_world_read_count += 1
        if self._mw_raises:
            raise self._mw_raises
        return self._mw

    @property
    def cleared(self):
        return self._cleared


class FakeMeshObj:
    """Fake bpy.types.Object with type MESH. Tracks evaluated_get calls."""
    def __init__(self, name, evaluated=None, eval_raises=None, children=None):
        self._name = name
        self.type = "MESH"
        self._evaluated = evaluated
        self._eval_raises = eval_raises
        self.children = children if children is not None else []
        self.eval_get_count = 0
        self.to_mesh_count = 0
        self.to_mesh_clear_count = 0

    @property
    def name(self): return self._name

    def evaluated_get(self, depsgraph):
        self.eval_get_count += 1
        if self._eval_raises:
            raise self._eval_raises
        ev = self._evaluated if self._evaluated is not None else FakeEvaluated(
            mesh=FakeMesh([(0, 0, 0)]))
        # Wrap to_mesh and to_mesh_clear with counters
        orig_to_mesh = ev.to_mesh
        orig_to_mesh_clear = ev.to_mesh_clear
        _self = self
        def _counted_to_mesh():
            _self.to_mesh_count += 1
            return orig_to_mesh()
        def _counted_to_mesh_clear():
            _self.to_mesh_clear_count += 1
            orig_to_mesh_clear()
        ev.to_mesh = _counted_to_mesh
        ev.to_mesh_clear = _counted_to_mesh_clear
        return ev


class FakeScene:
    def __init__(self, objects):
        self.objects = objects


def _make_full_mock(mesh_objects, geometry_scope="DESCENDANT_MESHES",
                    root_name="root", ground_z=0.0, tolerance=0.02,
                    root_type="EMPTY"):
    root = FakeMeshObj(name=root_name, children=list(mesh_objects))
    root.type = root_type
    all_objs = [root] + list(mesh_objects)
    scene = FakeScene(all_objs)
    target = _target(tid="T1", gc=_gc_block(ground_z, tolerance),
                     geometry_scope=geometry_scope,
                     root_object_name=root_name)
    ptr = {"checks": {"object_exists": {"result": "PASS"},
                      "object_type": {"result": "PASS", "actual": root_type}}}
    return scene, target, ptr


# ═══════════════════════ config / NOT_CHECKED ═══════════════════════

class TestConfigNotChecked:
    def test_gc_missing(self):
        r = _check_ground_contact(None, _target(gc=None), _root_pass())
        assert r == {"result": "NOT_CHECKED", "note": "GROUND_CONTACT_NOT_CONFIGURED"}

    def test_gc_none_block(self):
        t = _target(); t["ground_contact"] = None
        r = _check_ground_contact(None, t, _root_pass())
        assert r == {"result": "NOT_CHECKED", "note": "GROUND_CONTACT_NOT_CONFIGURED"}

    def test_gc_empty_dict(self):
        r = _check_ground_contact(None, _target(gc={}), _root_pass())
        assert r == {"result": "NOT_CHECKED", "note": "GROUND_CONTACT_NOT_CONFIGURED"}

    def test_both_null(self):
        t = _target(gc={"ground_z": None, "ground_contact_tolerance": None})
        r = _check_ground_contact(None, t, _root_pass())
        assert r == {"result": "NOT_CHECKED", "note": "GROUND_CONTACT_NOT_CONFIGURED"}


# ═══════════════════════ pre-open validation ═══════════════════════

class TestPreOpenValidation:
    def test_gz_present_tol_absent(self):
        t = _target(tid="A", gc={"ground_z": 0.0})
        errs = _validate_ground_contact_rules_preopen([t])
        assert len(errs) == 1
        assert "INVALID_GROUND_CONTACT_RULE_RELATION" in errs[0]
        assert "target 'A'" in errs[0]
        assert "ground_contact_tolerance" in errs[0]

    def test_gz_present_tol_none(self):
        t = _target(tid="A", gc={"ground_z": 0.0, "ground_contact_tolerance": None})
        errs = _validate_ground_contact_rules_preopen([t])
        assert len(errs) == 1
        assert "ground_contact_tolerance" in errs[0]

    def test_tol_present_gz_absent(self):
        t = _target(tid="B", gc={"ground_contact_tolerance": 0.02})
        errs = _validate_ground_contact_rules_preopen([t])
        assert len(errs) == 1
        assert "target 'B'" in errs[0]
        assert "ground_z" in errs[0]

    def test_tol_present_gz_none(self):
        t = _target(tid="B", gc={"ground_z": None, "ground_contact_tolerance": 0.02})
        errs = _validate_ground_contact_rules_preopen([t])
        assert len(errs) == 1
        assert "ground_z" in errs[0]

    def test_both_present_no_error(self):
        assert _validate_ground_contact_rules_preopen(
            [_target(gc=_gc_block(0.0, 0.02))]) == []

    def test_both_absent_no_error(self):
        assert _validate_ground_contact_rules_preopen([_target(gc={})]) == []

    def test_gc_missing_no_error(self):
        assert _validate_ground_contact_rules_preopen([_target(gc=None)]) == []

    def test_multi_target_sorted_errors(self):
        t1 = _target(tid="ZB", gc={"ground_z": 0.0})
        t2 = _target(tid="AA", gc={"ground_contact_tolerance": 0.02})
        errs = _validate_ground_contact_rules_preopen([t1, t2])
        assert len(errs) == 2
        assert "target 'AA'" in errs[0]
        assert "target 'ZB'" in errs[1]

    def test_tolerance_zero_legal(self):
        assert _validate_ground_contact_rules_preopen(
            [_target(gc=_gc_block(0.0, 0.0))]) == []


# ═══════════════════════ root preconditions ═══════════════════════

class TestRootPreconditions:
    def test_root_not_found(self):
        r = _check_ground_contact(None, _target(gc=_gc_block(0.0, 0.02)),
                                  _root_not_found())
        assert r == {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_NOT_FOUND"}

    def test_root_ambiguous(self):
        r = _check_ground_contact(None, _target(gc=_gc_block(0.0, 0.02)),
                                  _root_ambiguous())
        assert r == {"result": "NOT_CHECKED", "note": "AMBIGUOUS_ROOT_OBJECT_NAME"}

    def test_root_lookup_error(self):
        r = _check_ground_contact(None, _target(gc=_gc_block(0.0, 0.02)),
                                  _root_lookup_error())
        assert r == {"result": "NOT_CHECKED", "note": "ROOT_LOOKUP_ERROR"}

    def test_root_type_mismatch(self):
        r = _check_ground_contact(None, _target(gc=_gc_block(0.0, 0.02)),
                                  _root_type_mismatch())
        assert r == {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_TYPE_MISMATCH"}

    def test_root_not_found_no_bpy_read(self):
        r = _check_ground_contact(None, _target(gc=_gc_block(0.0, 0.02)),
                                  _root_not_found())
        assert r["result"] == "NOT_CHECKED"


# ═══════════════════════ scene / root ERROR ═══════════════════════

class TestSceneRootErrors:
    def test_read_scene_objects_raises(self):
        class BadScene:
            @property
            def objects(self):
                raise RuntimeError("boom")
        r = _check_ground_contact(BadScene(), _target(gc=_gc_block(0.0, 0.02)),
                                  _root_pass())
        assert r["result"] == "ERROR"
        assert r["operation"] == "READ_SCENE_OBJECTS"

    def test_resolve_root_object_raises(self):
        class BadObj:
            @property
            def name(self):
                raise RuntimeError("boom")
        r = _check_ground_contact(FakeScene([BadObj()]),
                                  _target(gc=_gc_block(0.0, 0.02)), _root_pass())
        assert r["result"] == "ERROR"
        assert r["operation"] == "RESOLVE_ROOT_OBJECT"


# ═══════════════════════ geometry scope ERROR ═══════════════════════

class TestGeometryScopeErrors:
    def test_read_root_children_raises(self):
        class BadRoot:
            type = "EMPTY"; _name = "root"
            @property
            def name(self): return self._name
            @property
            def children(self): raise RuntimeError("boom")
        root = BadRoot()
        r = _check_ground_contact(FakeScene([root]),
                                  _target(gc=_gc_block(0.0, 0.02)),
                                  {"checks": {"object_exists": {"result": "PASS"},
                                              "object_type": {"result": "PASS",
                                                              "actual": "EMPTY"}}})
        assert r["result"] == "ERROR"
        assert r["operation"] == "READ_ROOT_CHILDREN"

    def test_read_descendant_children_raises(self):
        class BadChild:
            type = "MESH"; _name = "child"
            @property
            def name(self): return self._name
            @property
            def children(self): raise RuntimeError("boom")
        root = FakeMeshObj(name="root"); root.type = "EMPTY"
        child = BadChild(); root.children = [child]
        r = _check_ground_contact(FakeScene([root, child]),
                                  _target(gc=_gc_block(0.0, 0.02)),
                                  {"checks": {"object_exists": {"result": "PASS"},
                                              "object_type": {"result": "PASS",
                                                              "actual": "EMPTY"}}})
        assert r["result"] == "ERROR"
        assert r["operation"] == "READ_DESCENDANT_CHILDREN"

    def test_read_descendant_type_raises(self):
        class BadTypeChild:
            _name = "child"; children = []
            @property
            def name(self): return self._name
            @property
            def type(self): raise RuntimeError("boom")
        root = FakeMeshObj(name="root"); root.type = "EMPTY"
        child = BadTypeChild(); root.children = [child]
        r = _check_ground_contact(FakeScene([root, child]),
                                  _target(gc=_gc_block(0.0, 0.02)),
                                  {"checks": {"object_exists": {"result": "PASS"},
                                              "object_type": {"result": "PASS",
                                                              "actual": "EMPTY"}}})
        assert r["result"] == "ERROR"
        assert r["operation"] == "READ_DESCENDANT_TYPE"


# ═══════════════════════ evaluated geometry algorithm ═══════════════════════

class TestEvaluatedGeometryAlgorithm:
    def test_pass_exact_ground_z(self):
        m = FakeMeshObj("m", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, 0)]), mw=FakeMatrixWorld()))
        scene, target, ptr = _make_full_mock([m])
        r = _check_ground_contact(scene, target, ptr)
        assert r["result"] == "PASS"
        assert r["actual_lowest_z"] == 0.0

    def test_pass_within_tolerance(self):
        m = FakeMeshObj("m", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, 0.01)]), mw=FakeMatrixWorld()))
        scene, target, ptr = _make_full_mock([m])
        assert _check_ground_contact(scene, target, ptr)["result"] == "PASS"

    def test_pass_tolerance_boundary(self):
        m = FakeMeshObj("m", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, 0.02)]), mw=FakeMatrixWorld()))
        scene, target, ptr = _make_full_mock([m])
        assert _check_ground_contact(scene, target, ptr)["result"] == "PASS"

    def test_fail_above_tolerance(self):
        m = FakeMeshObj("m", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, 0.03)]), mw=FakeMatrixWorld()))
        scene, target, ptr = _make_full_mock([m])
        r = _check_ground_contact(scene, target, ptr)
        assert r["result"] == "FAIL"
        assert r["failure_code"] == "GROUND_CONTACT_OUT_OF_TOLERANCE"

    def test_fail_below_ground(self):
        m = FakeMeshObj("m", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, -0.03)]), mw=FakeMatrixWorld()))
        scene, target, ptr = _make_full_mock([m])
        r = _check_ground_contact(scene, target, ptr)
        assert r["result"] == "FAIL"
        assert r["failure_code"] == "GROUND_CONTACT_OUT_OF_TOLERANCE"

    def test_zero_tolerance_pass(self):
        m = FakeMeshObj("m", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, 0.0)]), mw=FakeMatrixWorld()))
        scene, target, ptr = _make_full_mock([m], ground_z=0.0, tolerance=0.0)
        assert _check_ground_contact(scene, target, ptr)["result"] == "PASS"

    def test_zero_tolerance_fail(self):
        m = FakeMeshObj("m", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, 0.001)]), mw=FakeMatrixWorld()))
        scene, target, ptr = _make_full_mock([m], ground_z=0.0, tolerance=0.0)
        assert _check_ground_contact(scene, target, ptr)["result"] == "FAIL"

    def test_two_mesh_global_lowest(self):
        m1 = FakeMeshObj("m1", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, 0.05)]), mw=FakeMatrixWorld()))
        m2 = FakeMeshObj("m2", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, -0.01)]), mw=FakeMatrixWorld()))
        scene, target, ptr = _make_full_mock([m1, m2])
        r = _check_ground_contact(scene, target, ptr)
        assert r["result"] == "PASS"
        assert r["actual_lowest_z"] == -0.01

    def test_mw_transform_applied(self):
        m = FakeMeshObj("m", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, 0.0)]),
            mw=FakeMatrixWorld(offset=(0, 0, 0.5))))
        scene, target, ptr = _make_full_mock([m], ground_z=0.5, tolerance=0.0)
        r = _check_ground_contact(scene, target, ptr)
        assert r["result"] == "PASS"
        assert r["actual_lowest_z"] == 0.5

    def test_preserves_within_scope(self):
        m = FakeMeshObj("m", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, 1.0), (0, 0, -0.5), (0, 0, 2.0)]),
            mw=FakeMatrixWorld()))
        scene, target, ptr = _make_full_mock([m], ground_z=-0.5, tolerance=0.0)
        r = _check_ground_contact(scene, target, ptr)
        assert r["result"] == "PASS"
        assert r["actual_lowest_z"] == -0.5


# ═══════════════════════ empty / zero vertex ═══════════════════════

class TestEmptyGeometry:
    def test_no_mesh_in_scope(self):
        root = FakeMeshObj(name="root"); root.type = "EMPTY"
        scene = FakeScene([root])
        ptr = {"checks": {"object_exists": {"result": "PASS"},
                          "object_type": {"result": "PASS", "actual": "EMPTY"}}}
        r = _check_ground_contact(scene, _target(gc=_gc_block(0.0, 0.02)), ptr)
        assert r["result"] == "FAIL"
        assert r["failure_code"] == "NO_EVALUATED_GEOMETRY"

    def test_zero_vertices(self):
        m = FakeMeshObj("m", evaluated=FakeEvaluated(
            mesh=FakeMesh([]), mw=FakeMatrixWorld()))
        scene, target, ptr = _make_full_mock([m])
        r = _check_ground_contact(scene, target, ptr)
        assert r["result"] == "FAIL"
        assert r["failure_code"] == "NO_EVALUATED_GEOMETRY"


# ═══════════════════════ non-finite vertices ═══════════════════════

class TestNonFiniteVertices:
    def test_nan_vertex(self):
        m = FakeMeshObj("m", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, float('nan'))]), mw=FakeMatrixWorld()))
        scene, target, ptr = _make_full_mock([m])
        r = _check_ground_contact(scene, target, ptr)
        assert r["result"] == "FAIL"
        assert r["failure_code"] == "NON_FINITE_EVALUATED_VERTEX_Z"

    def test_inf_vertex(self):
        m = FakeMeshObj("m", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, float('inf'))]), mw=FakeMatrixWorld()))
        scene, target, ptr = _make_full_mock([m])
        r = _check_ground_contact(scene, target, ptr)
        assert r["result"] == "FAIL"
        assert r["failure_code"] == "NON_FINITE_EVALUATED_VERTEX_Z"

    def test_mixed_nan_and_normal(self):
        m = FakeMeshObj("m", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, float('nan')), (0, 0, 0.01)]),
            mw=FakeMatrixWorld()))
        scene, target, ptr = _make_full_mock([m])
        r = _check_ground_contact(scene, target, ptr)
        assert r["result"] == "FAIL"
        assert r["failure_code"] == "NON_FINITE_EVALUATED_VERTEX_Z"

    def test_all_nan(self):
        m = FakeMeshObj("m", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, float('nan')), (0, 0, float('nan'))]),
            mw=FakeMatrixWorld()))
        scene, target, ptr = _make_full_mock([m])
        r = _check_ground_contact(scene, target, ptr)
        assert r["result"] == "FAIL"
        assert r["failure_code"] == "NON_FINITE_EVALUATED_VERTEX_Z"


# ═══════════════════════ evaluated geometry ERROR ═══════════════════════

class TestEvaluatedGeometryErrors:
    def test_depsgraph_raises(self):
        import bpy
        m = FakeMeshObj("m", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, 0)])))
        scene, target, ptr = _make_full_mock([m])
        bpy.context.set_depsgraph_raises(RuntimeError("boom"))
        r = _check_ground_contact(scene, target, ptr)
        assert r["result"] == "ERROR"
        assert r["operation"] == "GET_EVALUATED_DEPSGRAPH"

    def test_evaluated_get_raises(self):
        m = FakeMeshObj("m", eval_raises=RuntimeError("eval boom"))
        scene, target, ptr = _make_full_mock([m])
        r = _check_ground_contact(scene, target, ptr)
        assert r["result"] == "ERROR"
        assert r["operation"] == "EVALUATED_GET"

    def test_to_mesh_raises(self):
        m = FakeMeshObj("m", evaluated=FakeEvaluated(
            to_mesh_raises=RuntimeError("to_mesh boom")))
        scene, target, ptr = _make_full_mock([m])
        r = _check_ground_contact(scene, target, ptr)
        assert r["result"] == "ERROR"
        assert r["operation"] == "TO_MESH"

    def test_to_mesh_clear_raises(self):
        ev = FakeEvaluated(mesh=FakeMesh([(0, 0, 0)]),
                           to_mesh_clear_raises=RuntimeError("clear boom"))
        m = FakeMeshObj("m", evaluated=ev)
        scene, target, ptr = _make_full_mock([m])
        r = _check_ground_contact(scene, target, ptr)
        assert r["result"] == "ERROR"
        assert r["operation"] == "TO_MESH_CLEAR"

    def test_matrix_world_raises(self):
        m = FakeMeshObj("m", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, 0)]), mw_raises=RuntimeError("mw boom")))
        scene, target, ptr = _make_full_mock([m])
        r = _check_ground_contact(scene, target, ptr)
        assert r["result"] == "ERROR"
        assert r["operation"] == "READ_EVALUATED_MATRIX_WORLD"

    def test_vertices_len_raises(self):
        class BadVerticesMesh:
            @property
            def vertices(self): raise RuntimeError("len boom")
        m = FakeMeshObj("m", evaluated=FakeEvaluated(mesh=BadVerticesMesh()))
        scene, target, ptr = _make_full_mock([m])
        r = _check_ground_contact(scene, target, ptr)
        assert r["result"] == "ERROR"
        assert r["operation"] == "READ_MESH_VERTICES"

    def test_vertex_iteration_raises(self):
        class BadIterMesh:
            @property
            def vertices(self):
                class BadIter:
                    def __len__(self): return 2
                    def __iter__(self): raise RuntimeError("iter boom"); yield
                return BadIter()
        m = FakeMeshObj("m", evaluated=FakeEvaluated(mesh=BadIterMesh()))
        scene, target, ptr = _make_full_mock([m])
        r = _check_ground_contact(scene, target, ptr)
        assert r["result"] == "ERROR"
        assert r["operation"] == "READ_MESH_VERTICES"

    def test_vertex_co_raises(self):
        """v.co read raises → READ_MESH_VERTICES, and to_mesh_clear runs."""
        mesh = FakeMesh([(0, 0, 0)])
        mesh.vertices[0].set_co_raises(RuntimeError("co boom"))
        ev = FakeEvaluated(mesh=mesh, mw=FakeMatrixWorld())
        m = FakeMeshObj("m", evaluated=ev)
        scene, target, ptr = _make_full_mock([m])
        r = _check_ground_contact(scene, target, ptr)
        assert_dict_equal(r, {
            "result": "ERROR",
            "error_type": "GROUND_CONTACT_COMPUTATION_ERROR",
            "operation": "READ_MESH_VERTICES",
            "note": "READ_MESH_VERTICES_FAILED",
        })
        assert ev.cleared  # to_mesh_clear 1 time
        assert m.to_mesh_clear_count == 1

    def test_transform_vertex_raises(self):
        class BadMatrix:
            def __matmul__(self, co): raise RuntimeError("transform boom")
        m = FakeMeshObj("m", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, 0)]), mw=BadMatrix()))
        scene, target, ptr = _make_full_mock([m])
        r = _check_ground_contact(scene, target, ptr)
        assert r["result"] == "ERROR"
        assert r["operation"] == "TRANSFORM_VERTEX_TO_WORLD_SPACE"

    def test_eval_fail_cleanup_multi_mesh(self):
        """Mesh1 eval+to_mesh succeed, Mesh2 eval fails — Mesh1 cleaned."""
        m1 = FakeMeshObj("m1", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, 0)]), mw=FakeMatrixWorld()))
        m2 = FakeMeshObj("m2", eval_raises=RuntimeError("eval2 boom"))
        scene, target, ptr = _make_full_mock([m1, m2])
        r = _check_ground_contact(scene, target, ptr)
        assert r["result"] == "ERROR"
        assert r["operation"] == "EVALUATED_GET"
        # m1: eval succeeded, to_mesh succeeded, to_mesh_clear ran once
        assert m1.to_mesh_clear_count == 1
        # m2: eval failed, nothing else
        assert m2.eval_get_count == 1
        assert m2.to_mesh_count == 0
        assert m2.to_mesh_clear_count == 0

    def test_to_mesh_clear_not_called_on_to_mesh_fail(self):
        ev = FakeEvaluated(to_mesh_raises=RuntimeError("to_mesh boom"))
        m = FakeMeshObj("m", evaluated=ev)
        scene, target, ptr = _make_full_mock([m])
        r = _check_ground_contact(scene, target, ptr)
        assert r["operation"] == "TO_MESH"
        assert m.to_mesh_clear_count == 0

    def test_mw_fail_and_clear_fail_clear_overrides(self):
        """matrix_world read fails → READ_EVALUATED_MATRIX_WORLD pending,
        but to_mesh_clear also fails → TO_MESH_CLEAR overrides."""
        ev = FakeEvaluated(
            mesh=FakeMesh([(0, 0, 0)]),
            mw_raises=RuntimeError("mw boom"),
            to_mesh_clear_raises=RuntimeError("clear boom"),
        )
        m = FakeMeshObj("m", evaluated=ev)
        scene, target, ptr = _make_full_mock([m])
        r = _check_ground_contact(scene, target, ptr)
        assert r["result"] == "ERROR"
        assert r["operation"] == "TO_MESH_CLEAR"

    def test_zero_vertex_and_clear_fail_clear_overrides(self):
        """zero vertices → would continue, but to_mesh_clear fails →
        TO_MESH_CLEAR, not continuing to next object."""
        ev = FakeEvaluated(
            mesh=FakeMesh([]),
            to_mesh_clear_raises=RuntimeError("clear boom"),
        )
        m = FakeMeshObj("m", evaluated=ev)
        scene, target, ptr = _make_full_mock([m])
        r = _check_ground_contact(scene, target, ptr)
        assert r["result"] == "ERROR"
        assert r["operation"] == "TO_MESH_CLEAR"


# ═══════════════════════ result dicts ═══════════════════════

class TestResultDicts:
    def test_not_checked_keys(self):
        r = _check_ground_contact(None, _target(gc=None), _root_pass())
        assert_dict_equal(r, {"result": "NOT_CHECKED",
                              "note": "GROUND_CONTACT_NOT_CONFIGURED"})

    def test_pass_keys(self):
        m = FakeMeshObj("m", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, 0)])))
        scene, target, ptr = _make_full_mock([m])
        r = _check_ground_contact(scene, target, ptr)
        expected = {"result", "ground_z", "ground_contact_tolerance",
                    "actual_lowest_z", "absolute_error", "evaluated_mesh_names"}
        assert set(r.keys()) == expected
        assert r["result"] == "PASS"

    def test_fail_tolerance_keys(self):
        m = FakeMeshObj("m", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, 0.1)])))
        scene, target, ptr = _make_full_mock([m])
        r = _check_ground_contact(scene, target, ptr)
        expected = {"result", "failure_code", "ground_z",
                    "ground_contact_tolerance", "actual_lowest_z",
                    "absolute_error", "evaluated_mesh_names"}
        assert set(r.keys()) == expected

    def test_fail_no_geom_keys(self):
        root = FakeMeshObj(name="root"); root.type = "EMPTY"
        scene = FakeScene([root])
        ptr = {"checks": {"object_exists": {"result": "PASS"},
                          "object_type": {"result": "PASS", "actual": "EMPTY"}}}
        r = _check_ground_contact(scene, _target(gc=_gc_block(0.0, 0.02)), ptr)
        expected = {"result", "failure_code", "ground_z",
                    "ground_contact_tolerance"}
        assert set(r.keys()) == expected
        assert "actual_lowest_z" not in r

    def test_fail_nonfinite_keys(self):
        m = FakeMeshObj("m", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, float('nan'))])))
        scene, target, ptr = _make_full_mock([m])
        r = _check_ground_contact(scene, target, ptr)
        expected = {"result", "failure_code", "ground_z",
                    "ground_contact_tolerance", "evaluated_mesh_names"}
        assert set(r.keys()) == expected
        assert "actual_lowest_z" not in r

    def test_error_keys(self):
        m = FakeMeshObj("m", eval_raises=RuntimeError("boom"))
        scene, target, ptr = _make_full_mock([m])
        r = _check_ground_contact(scene, target, ptr)
        expected = {"result", "error_type", "operation", "note"}
        assert set(r.keys()) == expected
        assert "ground_z" not in r


# ═══════════════════════ overall aggregation (real _recompute_target_overall) ═

class TestOverallAggregationReal:
    """Directly call _recompute_target_overall(checks) to prove aggregation."""

    def test_gc_pass_other_pass_overall_pass(self):
        checks = {
            "object_exists": {"result": "PASS"},
            "object_type": {"result": "PASS"},
            "ground_contact": {"result": "PASS"},
        }
        assert _recompute_target_overall(checks) == "PASS"

    def test_gc_fail_other_pass_overall_fail(self):
        checks = {
            "object_exists": {"result": "PASS"},
            "object_type": {"result": "PASS"},
            "ground_contact": {"result": "FAIL",
                               "failure_code": "GROUND_CONTACT_OUT_OF_TOLERANCE"},
        }
        assert _recompute_target_overall(checks) == "FAIL"

    def test_gc_error_other_pass_overall_error(self):
        checks = {
            "object_exists": {"result": "PASS"},
            "object_type": {"result": "PASS"},
            "ground_contact": {
                "result": "ERROR",
                "error_type": "GROUND_CONTACT_COMPUTATION_ERROR",
                "operation": "EVALUATED_GET",
                "note": "EVALUATED_GET_FAILED",
            },
        }
        assert _recompute_target_overall(checks) == "ERROR"

    def test_gc_not_checked_other_pass_overall_pass(self):
        checks = {
            "object_exists": {"result": "PASS"},
            "object_type": {"result": "PASS"},
            "ground_contact": {"result": "NOT_CHECKED",
                               "note": "GROUND_CONTACT_NOT_CONFIGURED"},
        }
        assert _recompute_target_overall(checks) == "PASS"


# ═══════════════════════ target error collection (real _collect_target_errors) ═

class TestTargetErrorCollectionReal:
    """Directly call _collect_target_errors with per_target_results to prove
    format and ordering of GROUND_CONTACT_COMPUTATION_ERROR messages."""

    def test_gc_error_format(self):
        ptr = [{
            "target_id": "T1",
            "root_object_name": "root",
            "checks": {
                "object_exists": {"result": "PASS"},
                "ground_contact": {
                    "result": "ERROR",
                    "error_type": "GROUND_CONTACT_COMPUTATION_ERROR",
                    "operation": "GET_EVALUATED_DEPSGRAPH",
                    "note": "GET_EVALUATED_DEPSGRAPH_FAILED",
                },
            },
            "overall": "ERROR",
        }]
        errs = _collect_target_errors(ptr)
        gc_errs = [e for e in errs if "GROUND_CONTACT_COMPUTATION_ERROR" in e]
        assert len(gc_errs) == 1
        assert "GROUND_CONTACT_COMPUTATION_ERROR: target 'T1' " \
               "root_object_name 'root' operation 'GET_EVALUATED_DEPSGRAPH'" in gc_errs[0]

    def test_rotation_gc_material_assignment_error_order(self):
        """rotation → ground_contact → material_assignment in collected errors."""
        ptr = [{
            "target_id": "T1",
            "root_object_name": "root",
            "checks": {
                "object_exists": {"result": "PASS"},
                "rotation": {
                    "result": "ERROR",
                    "error_type": "ROTATION_COMPUTATION_ERROR",
                    "operation": "READ_ROOT_MATRIX_WORLD",
                    "note": "READ_ROOT_MATRIX_WORLD_FAILED",
                },
                "ground_contact": {
                    "result": "ERROR",
                    "error_type": "GROUND_CONTACT_COMPUTATION_ERROR",
                    "operation": "TO_MESH",
                    "note": "TO_MESH_FAILED",
                },
                "material_assignment_presence_check": {
                    "result": "ERROR",
                    "error_type": "MATERIAL_ASSIGNMENT_COMPUTATION_ERROR",
                    "operation": "READ_MATERIAL_SLOTS",
                    "note": "READ_MATERIAL_SLOTS_FAILED",
                },
            },
            "overall": "ERROR",
        }]
        errs = _collect_target_errors(ptr)
        # Find indices to verify order
        rot_idx = next(i for i, e in enumerate(errs) if "ROTATION_COMPUTATION" in e)
        gc_idx = next(i for i, e in enumerate(errs) if "GROUND_CONTACT_COMPUTATION" in e)
        ma_idx = next(i for i, e in enumerate(errs) if "MATERIAL_ASSIGNMENT_COMPUTATION" in e)
        assert rot_idx < gc_idx < ma_idx, (
            f"Expected rotation({rot_idx}) < gc({gc_idx}) < ma({ma_idx})"
        )

    def test_gc_error_not_present_when_gc_is_not_checked(self):
        """When ground_contact is NOT_CHECKED, no GC ERROR is collected."""
        ptr = [{
            "target_id": "T1",
            "root_object_name": "root",
            "checks": {
                "object_exists": {"result": "PASS"},
                "ground_contact": {"result": "NOT_CHECKED",
                                   "note": "GROUND_CONTACT_NOT_CONFIGURED"},
            },
            "overall": "PASS",
        }]
        errs = _collect_target_errors(ptr)
        gc_errs = [e for e in errs if "GROUND_CONTACT_COMPUTATION" in e]
        assert gc_errs == []


# ═══════════════════════ read count contract ═══════════════════════

class TestReadCountContract:
    """Verified call counts: depsgraph 1/target, eval_get 1/MESH,
    to_mesh 1/MESH, matrix_world 1/successful MESH, to_mesh_clear 1/success."""

    def test_read_counts_two_meshes(self):
        import bpy
        m1 = FakeMeshObj("m1", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, 0)]), mw=FakeMatrixWorld()))
        m2 = FakeMeshObj("m2", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, 0)]), mw=FakeMatrixWorld()))
        scene, target, ptr = _make_full_mock([m1, m2])
        ctx = bpy.context
        ctx.call_count = 0  # reset
        r = _check_ground_contact(scene, target, ptr)
        assert r["result"] == "PASS"
        # depsgraph: exactly 1 per target
        assert ctx.call_count == 1
        # evaluated_get: exactly 1 per MESH
        assert m1.eval_get_count == 1
        assert m2.eval_get_count == 1
        # to_mesh: exactly 1 per MESH
        assert m1.to_mesh_count == 1
        assert m2.to_mesh_count == 1
        # to_mesh_clear: exactly 1 per successful MESH
        assert m1.to_mesh_clear_count == 1
        assert m2.to_mesh_clear_count == 1


# ═══════════════════════ identity dedup ═══════════════════════

class TestIdentityDedupReal:
    """Same MESH object referenced twice → appears once, called once."""

    def test_duplicate_in_children(self):
        mesh = FakeMeshObj("dup", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, 0)]), mw=FakeMatrixWorld()))
        root = FakeMeshObj(name="root", children=[mesh, mesh])  # same ref twice
        root.type = "EMPTY"
        scene = FakeScene([root, mesh])
        t = _target(gc=_gc_block(0.0, 0.02))
        ptr = {"checks": {"object_exists": {"result": "PASS"},
                          "object_type": {"result": "PASS", "actual": "EMPTY"}}}
        r = _check_ground_contact(scene, t, ptr)
        assert r["result"] == "PASS"
        # Appears only once in evaluated_mesh_names
        assert r["evaluated_mesh_names"] == ["dup"]
        # Called only once
        assert mesh.eval_get_count == 1
        assert mesh.to_mesh_count == 1
        assert mesh.to_mesh_clear_count == 1


# ═══════════════════════ SELF_MESH scope ═══════════════════════

class TestSelfMeshScope:
    def test_self_mesh_root_is_mesh(self):
        root = FakeMeshObj(name="root")
        root.type = "MESH"
        root._evaluated = FakeEvaluated(mesh=FakeMesh([(0, 0, 0.01)]))
        scene = FakeScene([root])
        t = _target(gc=_gc_block(0.0, 0.02), geometry_scope="SELF_MESH")
        ptr = {"checks": {"object_exists": {"result": "PASS"},
                          "object_type": {"result": "PASS", "actual": "MESH"}}}
        r = _check_ground_contact(scene, t, ptr)
        assert r["result"] == "PASS"

    def test_self_mesh_root_not_mesh(self):
        root = FakeMeshObj(name="root"); root.type = "EMPTY"
        scene = FakeScene([root])
        t = _target(gc=_gc_block(0.0, 0.02), geometry_scope="SELF_MESH")
        ptr = {"checks": {"object_exists": {"result": "PASS"},
                          "object_type": {"result": "PASS", "actual": "EMPTY"}}}
        r = _check_ground_contact(scene, t, ptr)
        assert r["result"] == "FAIL"
        assert r["failure_code"] == "NO_EVALUATED_GEOMETRY"


# ═══════════════════════ scene membership ═══════════════════════

class TestSceneMembership:
    def test_child_not_in_scene_excluded(self):
        child = FakeMeshObj(name="child")
        root = FakeMeshObj(name="root", children=[child]); root.type = "EMPTY"
        scene = FakeScene([root])  # child NOT in scene.objects
        t = _target(gc=_gc_block(0.0, 0.02))
        ptr = {"checks": {"object_exists": {"result": "PASS"},
                          "object_type": {"result": "PASS", "actual": "EMPTY"}}}
        r = _check_ground_contact(scene, t, ptr)
        assert r["result"] == "FAIL"
        assert r["failure_code"] == "NO_EVALUATED_GEOMETRY"


# ═══════════════════════ evaluated_mesh_names ═══════════════════════

class TestEvaluatedMeshNames:
    def test_names_in_pass(self):
        m1 = FakeMeshObj("m1", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, 0)])))
        m2 = FakeMeshObj("m2", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, 0)])))
        scene, target, ptr = _make_full_mock([m1, m2])
        r = _check_ground_contact(scene, target, ptr)
        assert r["result"] == "PASS"
        assert r["evaluated_mesh_names"] == ["m1", "m2"]

    def test_names_in_nonfinite(self):
        m = FakeMeshObj("m", evaluated=FakeEvaluated(
            mesh=FakeMesh([(0, 0, float('nan'))])))
        scene, target, ptr = _make_full_mock([m])
        r = _check_ground_contact(scene, target, ptr)
        assert r["evaluated_mesh_names"] == ["m"]


# ═══════════════════════ pre-open entry test ═══════════════════════

class TestPreOpenEntry:
    """Partial config reaches _validate_and_open_spec → INPUT ERROR before path."""

    def test_partial_config_blocks_blend_open(self):
        """Pre-open ERROR prevents validate_spec_paths from being called."""
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _validate_and_open_spec,
        )
        import tempfile, json, os
        td = tempfile.TemporaryDirectory()
        try:
            repo = td.name
            blend = os.path.join(repo, "scene.blend")
            with open(blend, "wb") as f:
                f.write(b"placeholder")
            spec = {
                "schema_version": "1",
                "checker": "asset_scene_preflight_check",
                "source_requirement_version": "Blender 固定资产模板路线 v4",
                "repository_root": repo,
                "blend_path": "scene.blend",
                "scene_name": "Scene",
                "targets": [{
                    "target_id": "A",
                    "root_object_name": "r",
                    "expected_root_type": "EMPTY",
                    "geometry_scope": "SELF_MESH",
                    "ground_contact": {"ground_z": 0.0},
                }],
                "global_rules": {},
            }
            sf = os.path.join(repo, "spec.json")
            with open(sf, "w", encoding="utf-8") as f:
                json.dump(spec, f)
            exit_code, result = _validate_and_open_spec(sf)
            assert exit_code == 2
            assert result["result"] == "ERROR"
            assert any("INVALID_GROUND_CONTACT_RULE_RELATION" in e
                       for e in result["input_errors"])
        finally:
            td.cleanup()
