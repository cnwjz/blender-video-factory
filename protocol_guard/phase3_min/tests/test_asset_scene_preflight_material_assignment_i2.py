"""Material Assignment I2 focused tests — 7 ERROR operations + error collection.

No Blender, no open_blend_and_get_scene, no scope guard.
All tests run in CPython with fake objects.
"""
import pytest
from protocol_guard.phase3_min.blender_scene_reader import (
    _check_material_assignment,
    _check_material_slots_for_mesh,
)
from protocol_guard.phase3_min.asset_scene_preflight_check import (
    _collect_target_errors,
)


# ── fake objects ──────────────────────────────────────────────────────
class _FakeObj:
    def __init__(self, name, obj_type="MESH", material_slots=None, children=None,
                 raise_on_children=False, raise_on_type=False,
                 raise_on_material_slots=False, raise_on_name=False):
        object.__setattr__(self, '_name', name)
        object.__setattr__(self, '_obj_type', obj_type)
        object.__setattr__(self, '_material_slots',
                           material_slots if material_slots is not None else [])
        object.__setattr__(self, '_children',
                           children if children is not None else [])
        object.__setattr__(self, '_raise_on_children', raise_on_children)
        object.__setattr__(self, '_raise_on_type', raise_on_type)
        object.__setattr__(self, '_raise_on_material_slots', raise_on_material_slots)
        object.__setattr__(self, '_raise_on_name', raise_on_name)

    @property
    def name(self):
        if object.__getattribute__(self, '_raise_on_name'):
            raise RuntimeError("name fail")
        return object.__getattribute__(self, '_name')

    @property
    def type(self):
        if object.__getattribute__(self, '_raise_on_type'):
            raise RuntimeError("type fail")
        return object.__getattribute__(self, '_obj_type')

    @property
    def children(self):
        if object.__getattribute__(self, '_raise_on_children'):
            raise RuntimeError("children fail")
        return object.__getattribute__(self, '_children')

    @property
    def material_slots(self):
        if object.__getattribute__(self, '_raise_on_material_slots'):
            raise RuntimeError("material_slots fail")
        return object.__getattribute__(self, '_material_slots')


class _FakeSlot:
    def __init__(self, material=None, raise_on_material=False):
        self._material = material
        self._raise_on_material = raise_on_material

    @property
    def material(self):
        if self._raise_on_material:
            raise RuntimeError("slot.material fail")
        return self._material


class _FakeScene:
    def __init__(self, objects, raise_on_objects=False):
        self._objects = objects
        self._raise_on_objects = raise_on_objects

    @property
    def objects(self):
        if self._raise_on_objects:
            raise RuntimeError("scene.objects fail")
        return self._objects


def _root_pass(actual="MESH"):
    return {"checks": {"object_exists": {"result": "PASS"},
                        "object_type": {"result": "PASS", "actual": actual}}}


def _target(require=True, geo_scope="SELF_MESH", root_name="root"):
    return {
        "material_assignment": {"require_material_assignment_presence": require},
        "geometry_scope": geo_scope,
        "root_object_name": root_name,
    }


ERROR_TYPE = "MATERIAL_ASSIGNMENT_COMPUTATION_ERROR"


# ── READ_SCENE_OBJECTS ─────────────────────────────────────────────────
class TestREAD_SCENE_OBJECTS:
    def test_scene_objects_attr_fails(self):
        s = _FakeScene([], raise_on_objects=True)
        r = _check_material_assignment(s, _target(), _root_pass())
        assert r == {"result": "ERROR", "error_type": ERROR_TYPE,
                      "operation": "READ_SCENE_OBJECTS",
                      "note": "READ_SCENE_OBJECTS_FAILED"}
        assert "per_mesh" not in r


# ── RESOLVE_ROOT_OBJECT ────────────────────────────────────────────────
class TestRESOLVE_ROOT_OBJECT:
    def test_obj_name_read_fails(self):
        obj = _FakeObj("root", raise_on_name=True)
        s = _FakeScene([obj])
        r = _check_material_assignment(s, _target(), _root_pass())
        assert r == {"result": "ERROR", "error_type": ERROR_TYPE,
                      "operation": "RESOLVE_ROOT_OBJECT",
                      "note": "RESOLVE_ROOT_OBJECT_FAILED"}
        assert "per_mesh" not in r

    def test_zero_matches(self):
        obj = _FakeObj("other")
        s = _FakeScene([obj])
        r = _check_material_assignment(s, _target(), _root_pass())
        assert r["operation"] == "RESOLVE_ROOT_OBJECT"

    def test_two_matches(self):
        a1 = _FakeObj("dup")
        a2 = _FakeObj("dup")
        s = _FakeScene([a1, a2])
        r = _check_material_assignment(s, _target(root_name="dup"), _root_pass())
        assert r["operation"] == "RESOLVE_ROOT_OBJECT"


# ── READ_ROOT_CHILDREN ─────────────────────────────────────────────────
class TestREAD_ROOT_CHILDREN:
    def test_root_children_fails(self):
        root = _FakeObj("root", "MESH", raise_on_children=True)
        s = _FakeScene([root])
        r = _check_material_assignment(s, _target(geo_scope="DESCENDANT_MESHES"),
                                       _root_pass())
        assert r == {"result": "ERROR", "error_type": ERROR_TYPE,
                      "operation": "READ_ROOT_CHILDREN",
                      "note": "READ_ROOT_CHILDREN_FAILED"}
        assert "per_mesh" not in r


# ── READ_DESCENDANT_CHILDREN ───────────────────────────────────────────
class TestREAD_DESCENDANT_CHILDREN:
    def test_descendant_children_fails(self):
        bad = _FakeObj("bad", "EMPTY", raise_on_children=True)
        root = _FakeObj("root", "EMPTY", children=[bad])
        s = _FakeScene([root, bad])
        r = _check_material_assignment(s, _target(geo_scope="DESCENDANT_MESHES"),
                                       _root_pass(actual="EMPTY"))
        assert r["operation"] == "READ_DESCENDANT_CHILDREN"
        assert "per_mesh" not in r


# ── READ_DESCENDANT_TYPE ───────────────────────────────────────────────
class TestREAD_DESCENDANT_TYPE:
    def test_descendant_type_fails(self):
        bad = _FakeObj("bad", "MESH", raise_on_type=True)
        root = _FakeObj("root", "EMPTY", children=[bad])
        s = _FakeScene([root, bad])
        r = _check_material_assignment(s, _target(geo_scope="DESCENDANT_MESHES"),
                                       _root_pass(actual="EMPTY"))
        assert r["operation"] == "READ_DESCENDANT_TYPE"
        assert "per_mesh" not in r


# ── READ_MATERIAL_SLOTS ────────────────────────────────────────────────
class TestREAD_MATERIAL_SLOTS:
    def test_material_slots_attr_fails(self):
        obj = _FakeObj("m", "MESH", raise_on_material_slots=True)
        r = _check_material_slots_for_mesh(obj, "m")
        assert r == {"mesh_name": "m", "result": "ERROR",
                      "error_type": ERROR_TYPE,
                      "operation": "READ_MATERIAL_SLOTS",
                      "note": "READ_MATERIAL_SLOTS_FAILED"}

    def test_per_mesh_error_others_continue(self):
        ok = _FakeObj("ok", "MESH", material_slots=[_FakeSlot("mat1")])
        bad = _FakeObj("bad", "MESH", raise_on_material_slots=True)
        root = _FakeObj("root", "EMPTY", children=[ok, bad])
        s = _FakeScene([root, ok, bad])
        r = _check_material_assignment(s, _target(geo_scope="DESCENDANT_MESHES"),
                                       _root_pass(actual="EMPTY"))
        assert r["result"] == "ERROR"
        assert len(r["per_mesh"]) == 2
        results = {pm["mesh_name"]: pm["result"] for pm in r["per_mesh"]}
        assert results["ok"] == "PASS"
        assert results["bad"] == "ERROR"


# ── READ_SLOT_MATERIAL ─────────────────────────────────────────────────
class TestREAD_SLOT_MATERIAL:
    def test_slot_material_fails(self):
        bad_slot = _FakeSlot(raise_on_material=True)
        ok_slot = _FakeSlot("mat")
        obj = _FakeObj("m", "MESH", material_slots=[ok_slot, bad_slot])
        r = _check_material_slots_for_mesh(obj, "m")
        assert r["result"] == "ERROR"
        assert r["operation"] == "READ_SLOT_MATERIAL"
        assert r["slot_index"] == 1
        assert r["note"] == "READ_SLOT_MATERIAL_FAILED"


# ── short-circuit and aggregation ──────────────────────────────────────
class TestShortCircuit:
    def test_geometry_error_no_per_mesh_and_no_material_reads(self):
        s = _FakeScene([], raise_on_objects=True)
        r = _check_material_assignment(s, _target(), _root_pass())
        assert "per_mesh" not in r

    def test_fail_plus_error_gives_error(self):
        ok = _FakeObj("ok", "MESH", material_slots=[_FakeSlot("mat1")])
        fail = _FakeObj("fail", "MESH", material_slots=[])
        err = _FakeObj("err", "MESH", raise_on_material_slots=True)
        root = _FakeObj("root", "EMPTY", children=[ok, fail, err])
        s = _FakeScene([root, ok, fail, err])
        r = _check_material_assignment(s, _target(geo_scope="DESCENDANT_MESHES"),
                                       _root_pass(actual="EMPTY"))
        assert r["result"] == "ERROR"

    def test_pass_plus_error_gives_error(self):
        ok = _FakeObj("ok", "MESH", material_slots=[_FakeSlot("mat1")])
        err = _FakeObj("err", "MESH", raise_on_material_slots=True)
        root = _FakeObj("root", "EMPTY", children=[ok, err])
        s = _FakeScene([root, ok, err])
        r = _check_material_assignment(s, _target(geo_scope="DESCENDANT_MESHES"),
                                       _root_pass(actual="EMPTY"))
        assert r["result"] == "ERROR"

    def test_multiple_local_errors_all_preserved(self):
        e1 = _FakeObj("e1", "MESH", raise_on_material_slots=True)
        e2 = _FakeObj("e2", "MESH", material_slots=[_FakeSlot(raise_on_material=True)])
        root = _FakeObj("root", "EMPTY", children=[e1, e2])
        s = _FakeScene([root, e1, e2])
        r = _check_material_assignment(s, _target(geo_scope="DESCENDANT_MESHES"),
                                       _root_pass(actual="EMPTY"))
        assert r["result"] == "ERROR"
        assert len(r["per_mesh"]) == 2
        assert all(pm["result"] == "ERROR" for pm in r["per_mesh"])


# ── key sets ───────────────────────────────────────────────────────────
class TestKeySets:
    def test_read_material_slots_keys(self):
        r = _check_material_slots_for_mesh(
            _FakeObj("m", raise_on_material_slots=True), "m")
        assert sorted(r.keys()) == sorted(
            ["mesh_name", "result", "error_type", "operation", "note"])

    def test_read_slot_material_keys(self):
        r = _check_material_slots_for_mesh(
            _FakeObj("m", material_slots=[_FakeSlot(raise_on_material=True)]), "m")
        assert sorted(r.keys()) == sorted(
            ["mesh_name", "result", "error_type", "operation", "note", "slot_index"])

    def test_geometry_error_keys(self):
        s = _FakeScene([], raise_on_objects=True)
        r = _check_material_assignment(s, _target(), _root_pass())
        assert sorted(r.keys()) == sorted(
            ["result", "error_type", "operation", "note"])


# ── _collect_target_errors ─────────────────────────────────────────────
def _make_target_result(tid, checks):
    """Build minimum per_target_result with overall derived from checks."""
    overall = "PASS"
    for c in checks.values():
        if isinstance(c, dict) and c.get("result") == "ERROR":
            overall = "ERROR"
            break
        elif isinstance(c, dict) and c.get("result") == "FAIL":
            overall = "FAIL"
    return {"target_id": tid, "root_object_name": "root", "overall": overall,
            "checks": checks}


class TestCollectTargetErrors:
    def test_geometry_error_message(self):
        s = _FakeScene([], raise_on_objects=True)
        ma = _check_material_assignment(s, _target(), _root_pass())
        pr = _make_target_result("t1", {"material_assignment_presence_check": ma})
        msgs = _collect_target_errors([pr])
        assert len(msgs) == 1
        assert "READ_SCENE_OBJECTS" in msgs[0]
        assert "t1" in msgs[0]

    def test_per_mesh_error_messages(self):
        e1 = _FakeObj("e1", "MESH", raise_on_material_slots=True)
        e2 = _FakeObj("e2", "MESH", material_slots=[_FakeSlot(raise_on_material=True)])
        root = _FakeObj("root", "EMPTY", children=[e1, e2])
        s = _FakeScene([root, e1, e2])
        ma = _check_material_assignment(s, _target(geo_scope="DESCENDANT_MESHES"),
                                        _root_pass(actual="EMPTY"))
        pr = _make_target_result("t1", {"material_assignment_presence_check": ma})
        msgs = _collect_target_errors([pr])
        assert len(msgs) == 2
        assert "e1" in msgs[0]
        assert "e2" in msgs[1]

    def test_messages_stable_order_with_hand_constructed_input(self):
        """Prove sorted by (operation, mesh_name) using unsorted per_mesh."""
        ma = {
            "result": "ERROR",
            "per_mesh": [
                {
                    "mesh_name": "z", "result": "ERROR",
                    "error_type": "MATERIAL_ASSIGNMENT_COMPUTATION_ERROR",
                    "operation": "READ_SLOT_MATERIAL",
                    "note": "READ_SLOT_MATERIAL_FAILED", "slot_index": 0,
                },
                {
                    "mesh_name": "b", "result": "ERROR",
                    "error_type": "MATERIAL_ASSIGNMENT_COMPUTATION_ERROR",
                    "operation": "READ_MATERIAL_SLOTS",
                    "note": "READ_MATERIAL_SLOTS_FAILED",
                },
                {
                    "mesh_name": "a", "result": "ERROR",
                    "error_type": "MATERIAL_ASSIGNMENT_COMPUTATION_ERROR",
                    "operation": "READ_MATERIAL_SLOTS",
                    "note": "READ_MATERIAL_SLOTS_FAILED",
                },
            ],
        }
        pr = _make_target_result("t1", {"material_assignment_presence_check": ma})
        msgs = _collect_target_errors([pr])

        expected = [
            "MATERIAL_ASSIGNMENT_COMPUTATION_ERROR: target 't1' "
            "material_assignment operation 'READ_MATERIAL_SLOTS' mesh 'a'",
            "MATERIAL_ASSIGNMENT_COMPUTATION_ERROR: target 't1' "
            "material_assignment operation 'READ_MATERIAL_SLOTS' mesh 'b'",
            "MATERIAL_ASSIGNMENT_COMPUTATION_ERROR: target 't1' "
            "material_assignment operation 'READ_SLOT_MATERIAL' mesh 'z'",
        ]
        assert msgs == expected

    def test_does_not_affect_other_field_groups(self):
        s = _FakeScene([], raise_on_objects=True)
        ma = _check_material_assignment(s, _target(), _root_pass())
        pr = _make_target_result("t1", {
            "material_assignment_presence_check": ma,
            "object_exists": {"result": "ERROR", "error_type": "AMBIGUOUS_ROOT_OBJECT_NAME",
                              "match_count": 2},
        })
        msgs = _collect_target_errors([pr])
        has_ma = any("MATERIAL_ASSIGNMENT" in m for m in msgs)
        has_ambiguity = any("AMBIGUOUS_ROOT_OBJECT_NAME" in m for m in msgs)
        assert has_ma
        assert has_ambiguity


# ── F-002: mid-explosion tests ─────────────────────────────────────────
class _ExplodingIterable:
    """Fake iterable that raises mid-iteration."""
    def __init__(self, items, fail_after=0):
        self._items = items
        self._fail_after = fail_after
        self._count = 0

    def __iter__(self):
        self._count = 0
        return self

    def __next__(self):
        self._count += 1
        if self._count > self._fail_after:
            raise RuntimeError("mid-iter fail")
        if self._count > len(self._items):
            raise StopIteration
        return self._items[self._count - 1]


class _ExplodingObj:
    """Fake obj whose material_slots iterable explodes mid-iteration."""
    def __init__(self, name, explode_after=0):
        self._name = name
        self.type = "MESH"
        self._explode_after = explode_after

    @property
    def name(self):
        return self._name

    @property
    def children(self):
        return []

    @property
    def material_slots(self):
        slots = [_FakeSlot(f"mat{i}") for i in range(3)]
        return _ExplodingIterable(slots, fail_after=self._explode_after)


class TestMidExplosion:
    def test_scene_objects_iterable_explodes_mid(self):
        """list(scene.objects) explodes mid-iteration → READ_SCENE_OBJECTS."""
        objs = [_FakeObj("root"), _FakeObj("other")]
        s = _FakeScene([])
        object.__setattr__(s, '_objects', _ExplodingIterable(objs, fail_after=1))
        r = _check_material_assignment(s, _target(), _root_pass())
        assert r == {"result": "ERROR", "error_type": "MATERIAL_ASSIGNMENT_COMPUTATION_ERROR",
                      "operation": "READ_SCENE_OBJECTS", "note": "READ_SCENE_OBJECTS_FAILED"}

    def test_material_slots_iterable_explodes_mid(self):
        """list(material_slots) explodes mid-iteration → READ_MATERIAL_SLOTS."""
        obj = _ExplodingObj("m", explode_after=1)
        r = _check_material_slots_for_mesh(obj, "m")
        assert r == {"mesh_name": "m", "result": "ERROR",
                      "error_type": "MATERIAL_ASSIGNMENT_COMPUTATION_ERROR",
                      "operation": "READ_MATERIAL_SLOTS",
                      "note": "READ_MATERIAL_SLOTS_FAILED"}
