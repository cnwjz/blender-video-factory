"""Material Assignment I1 focused tests — config ⇛ PASS/FAIL/NOT_CHECKED only.

No ERROR, no open_blend_and_get_scene, no scope guard, no Blender.
All tests run in CPython with fake objects.
"""
import pytest
from protocol_guard.phase3_min.blender_scene_reader import (
    _check_material_assignment,
    _collect_geometry_scope_objects,
    _check_material_slots_for_mesh,
)


# ── helpers ────────────────────────────────────────────────────────────
class FakeObj:
    """Minimal fake Blender object for I1 geometry scope tests."""
    def __init__(self, name, obj_type="MESH", children=None, material_slots=None):
        self._name = name
        self.type = obj_type
        self.children = children if children is not None else []
        self.material_slots = material_slots if material_slots is not None else []

    @property
    def name(self):
        return self._name


class FakeSlot:
    """Fake material slot."""
    def __init__(self, material):
        self.material = material


class FakeScene:
    """Fake scene wrapping objects."""
    def __init__(self, objects):
        self.objects = objects


def _make_root_pass():
    """Return a per_target_result with root checks both PASS."""
    return {
        "checks": {
            "object_exists": {"result": "PASS"},
            "object_type": {"result": "PASS", "actual": "MESH"},
        }
    }


def _target(ma_block, geometry_scope="SELF_MESH", root_object_name="root"):
    return {
        "material_assignment": ma_block,
        "geometry_scope": geometry_scope,
        "root_object_name": root_object_name,
    }


# ── config semantics ───────────────────────────────────────────────────
class TestConfigSemantics:
    def test_missing_block(self):
        t = {"geometry_scope": "SELF_MESH"}
        r = _check_material_assignment(FakeScene([]), t, _make_root_pass())
        assert r == {"result": "NOT_CHECKED", "note": "MATERIAL_ASSIGNMENT_NOT_CONFIGURED"}

    def test_none_block(self):
        t = _target(None)
        r = _check_material_assignment(FakeScene([]), t, _make_root_pass())
        assert r == {"result": "NOT_CHECKED", "note": "MATERIAL_ASSIGNMENT_NOT_CONFIGURED"}

    def test_empty_dict(self):
        t = _target({})
        r = _check_material_assignment(FakeScene([]), t, _make_root_pass())
        assert r == {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"}

    def test_require_false(self):
        t = _target({"require_material_assignment_presence": False})
        r = _check_material_assignment(FakeScene([]), t, _make_root_pass())
        assert r == {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"}

    def test_require_none(self):
        t = _target({"require_material_assignment_presence": None})
        r = _check_material_assignment(FakeScene([]), t, _make_root_pass())
        assert r == {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"}

    def test_require_absent(self):
        t = _target({"other": 1})
        r = _check_material_assignment(FakeScene([]), t, _make_root_pass())
        assert r == {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"}


# ── root preconditions ─────────────────────────────────────────────────
class TestRootPreconditions:
    def test_root_not_found(self):
        pr = {"checks": {"object_exists": {"result": "FAIL"}}}
        t = _target({"require_material_assignment_presence": True})
        r = _check_material_assignment(FakeScene([]), t, pr)
        assert r == {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_NOT_FOUND"}

    def test_root_ambiguous(self):
        pr = {"checks": {"object_exists": {"result": "PASS", "error_type": "AMBIGUOUS_ROOT_OBJECT_NAME"}}}
        t = _target({"require_material_assignment_presence": True})
        r = _check_material_assignment(FakeScene([]), t, pr)
        assert r == {"result": "NOT_CHECKED", "note": "AMBIGUOUS_ROOT_OBJECT_NAME"}

    def test_root_type_mismatch(self):
        pr = {"checks": {"object_exists": {"result": "PASS"}, "object_type": {"result": "FAIL"}}}
        t = _target({"require_material_assignment_presence": True})
        r = _check_material_assignment(FakeScene([]), t, pr)
        assert r == {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_TYPE_MISMATCH"}

    def test_root_lookup_error(self):
        pr = {"checks": {"object_exists": {"result": "ERROR"}}}
        t = _target({"require_material_assignment_presence": True})
        r = _check_material_assignment(FakeScene([]), t, pr)
        assert r == {"result": "NOT_CHECKED", "note": "ROOT_LOOKUP_ERROR"}

    def test_object_type_not_pass(self):
        pr = {"checks": {"object_exists": {"result": "PASS"}, "object_type": {"result": "NOT_CHECKED"}}}
        t = _target({"require_material_assignment_presence": True})
        r = _check_material_assignment(FakeScene([]), t, pr)
        assert r == {"result": "NOT_CHECKED", "note": "ROOT_LOOKUP_ERROR"}


# ── geometry scope ─────────────────────────────────────────────────────
class TestGeometryScope:
    def test_self_mesh_with_mesh_root(self):
        root = FakeObj("root", "MESH", material_slots=[FakeSlot("mat1")])
        scene = FakeScene([root])
        t = _target({"require_material_assignment_presence": True}, "SELF_MESH")
        r = _check_material_assignment(scene, t, _make_root_pass())
        assert r["result"] == "PASS"
        assert len(r["per_mesh"]) == 1
        assert r["per_mesh"][0]["mesh_name"] == "root"

    def test_self_mesh_with_empty_root(self):
        root = FakeObj("root", "EMPTY")
        scene = FakeScene([root])
        pr = {"checks": {"object_exists": {"result": "PASS"}, "object_type": {"result": "PASS", "actual": "EMPTY"}}}
        t = _target({"require_material_assignment_presence": True}, "SELF_MESH")
        r = _check_material_assignment(scene, t, pr)
        assert r == {"result": "NOT_CHECKED", "note": "NO_MESH_IN_GEOMETRY_SCOPE"}

    def test_descendant_meshes_collects_children(self):
        child = FakeObj("child", "MESH", material_slots=[FakeSlot("mat1")])
        root = FakeObj("root", "EMPTY", children=[child])
        scene = FakeScene([root, child])
        pr = {"checks": {"object_exists": {"result": "PASS"}, "object_type": {"result": "PASS", "actual": "EMPTY"}}}
        t = _target({"require_material_assignment_presence": True}, "DESCENDANT_MESHES")
        r = _check_material_assignment(scene, t, pr)
        assert r["result"] == "PASS"
        assert r["per_mesh"][0]["mesh_name"] == "child"

    def test_self_and_descendant_meshes(self):
        child = FakeObj("child", "MESH", material_slots=[FakeSlot("mat1")])
        root = FakeObj("root", "MESH", children=[child], material_slots=[FakeSlot("mat1")])
        scene = FakeScene([root, child])
        t = _target({"require_material_assignment_presence": True}, "SELF_AND_DESCENDANT_MESHES")
        r = _check_material_assignment(scene, t, _make_root_pass())
        assert r["result"] == "PASS"
        assert len(r["per_mesh"]) == 2

    def test_identity_dedup(self):
        child = FakeObj("child", "MESH", material_slots=[FakeSlot("mat1")])
        # Intentionally put child in root.children twice (different wrapper)
        root = FakeObj("root", "MESH", children=[child, child],
                       material_slots=[FakeSlot("mat1")])
        scene = FakeScene([root])
        t = _target({"require_material_assignment_presence": True}, "SELF_AND_DESCENDANT_MESHES")
        r = _check_material_assignment(scene, t, _make_root_pass())
        assert r["result"] == "PASS"
        assert len(r["per_mesh"]) == 1  # dedup

    def test_scene_outside_intermediate_continues_traversal(self):
        deep = FakeObj("deep", "MESH", material_slots=[FakeSlot("mat1")])
        middle = FakeObj("middle", "EMPTY", children=[deep])
        # middle is NOT in scene.objects —— scene 外中间节点
        child_b = FakeObj("child_b", "MESH")
        root = FakeObj("root", "MESH", children=[middle, child_b],
                       material_slots=[FakeSlot("mat1")])
        scene = FakeScene([root, child_b, deep])  # middle absent
        t = _target({"require_material_assignment_presence": True}, "SELF_AND_DESCENDANT_MESHES")
        r = _check_material_assignment(scene, t, _make_root_pass())
        names = {pm["mesh_name"] for pm in r["per_mesh"]}
        assert "root" in names
        assert "child_b" in names
        assert "deep" in names  # reached via Scene-外中间节点

    def test_stable_sorting(self):
        root = FakeObj("root", "MESH", material_slots=[FakeSlot("mat1")])
        zebra = FakeObj("Zebra", "MESH", material_slots=[FakeSlot("mat1")])
        apple = FakeObj("apple", "MESH", material_slots=[FakeSlot("mat1")])
        root.children = [zebra, apple]
        scene = FakeScene([root, zebra, apple])
        t = _target({"require_material_assignment_presence": True}, "SELF_AND_DESCENDANT_MESHES")
        r = _check_material_assignment(scene, t, _make_root_pass())
        names = [pm["mesh_name"] for pm in r["per_mesh"]]
        # casefold: apple < root < Zebra  →  apple, root, Zebra
        assert names == ["apple", "root", "Zebra"]

    def test_homonymous_stable_sorting_by_materialization_index(self):
        a1 = FakeObj("a", "MESH", material_slots=[FakeSlot("mat1")])
        a2 = FakeObj("a", "MESH", material_slots=[FakeSlot("mat1")])
        root = FakeObj("root", "EMPTY", children=[a1, a2])
        scene = FakeScene([root, a1, a2])
        pr = {"checks": {"object_exists": {"result": "PASS"}, "object_type": {"result": "PASS", "actual": "EMPTY"}}}
        t = _target({"require_material_assignment_presence": True}, "DESCENDANT_MESHES")
        r = _check_material_assignment(scene, t, pr)
        assert r["result"] == "PASS"
        assert len(r["per_mesh"]) == 2
        # a1 materialization_index=1, a2=2 —— ordering deterministic, not by id()

    def test_non_mesh_descendant_filtered(self):
        empty_child = FakeObj("empty_child", "EMPTY")
        mesh_child = FakeObj("mesh_child", "MESH", material_slots=[FakeSlot("mat1")])
        root = FakeObj("root", "EMPTY", children=[empty_child, mesh_child])
        scene = FakeScene([root, empty_child, mesh_child])
        pr = {"checks": {"object_exists": {"result": "PASS"}, "object_type": {"result": "PASS", "actual": "EMPTY"}}}
        t = _target({"require_material_assignment_presence": True}, "DESCENDANT_MESHES")
        r = _check_material_assignment(scene, t, pr)
        assert r["result"] == "PASS"
        assert len(r["per_mesh"]) == 1
        assert r["per_mesh"][0]["mesh_name"] == "mesh_child"


# ── material slot checks ───────────────────────────────────────────────
class TestSlotChecks:
    def test_zero_slots(self):
        r = _check_material_slots_for_mesh(FakeObj("m"), "m")
        assert r == {"mesh_name": "m", "result": "FAIL",
                      "failure_code": "MESH_HAS_NO_MATERIAL_SLOTS"}

    def test_all_valid(self):
        r = _check_material_slots_for_mesh(
            FakeObj("m", material_slots=[FakeSlot("mat1"), FakeSlot("mat2")]), "m")
        assert r == {"mesh_name": "m", "result": "PASS", "slot_count": 2}

    def test_single_null(self):
        r = _check_material_slots_for_mesh(
            FakeObj("m", material_slots=[FakeSlot(None)]), "m")
        assert r == {"mesh_name": "m", "result": "FAIL",
                      "failure_code": "NULL_MATERIAL_SLOT", "null_slot_indices": [0]}

    def test_mixed_valid_and_null(self):
        r = _check_material_slots_for_mesh(
            FakeObj("m", material_slots=[FakeSlot("ok"), FakeSlot(None)]), "m")
        assert r == {"mesh_name": "m", "result": "FAIL",
                      "failure_code": "NULL_MATERIAL_SLOT", "null_slot_indices": [1]}


# ── aggregation ────────────────────────────────────────────────────────
class TestAggregation:
    def test_all_pass(self):
        m1 = FakeObj("m1", "MESH", material_slots=[FakeSlot("ok")])
        m2 = FakeObj("m2", "MESH", material_slots=[FakeSlot("ok")])
        root = FakeObj("root", "EMPTY", children=[m1, m2])
        scene = FakeScene([root, m1, m2])
        pr = {"checks": {"object_exists": {"result": "PASS"}, "object_type": {"result": "PASS", "actual": "EMPTY"}}}
        t = _target({"require_material_assignment_presence": True}, "DESCENDANT_MESHES")
        r = _check_material_assignment(scene, t, pr)
        assert r["result"] == "PASS"
        assert len(r["per_mesh"]) == 2

    def test_mixed_pass_fail(self):
        m1 = FakeObj("m1", "MESH", material_slots=[FakeSlot("ok")])
        m2 = FakeObj("m2", "MESH", material_slots=[])  # FAIL
        root = FakeObj("root", "EMPTY", children=[m1, m2])
        scene = FakeScene([root, m1, m2])
        pr = {"checks": {"object_exists": {"result": "PASS"}, "object_type": {"result": "PASS", "actual": "EMPTY"}}}
        t = _target({"require_material_assignment_presence": True}, "DESCENDANT_MESHES")
        r = _check_material_assignment(scene, t, pr)
        assert r["result"] == "FAIL"
        assert r["failure_code"] == "MATERIAL_ASSIGNMENT_FAILURE"
        assert len(r["per_mesh"]) == 2

    def test_empty_scope(self):
        root = FakeObj("root", "EMPTY")
        scene = FakeScene([root])
        pr = {"checks": {"object_exists": {"result": "PASS"}, "object_type": {"result": "PASS", "actual": "EMPTY"}}}
        t = _target({"require_material_assignment_presence": True}, "DESCENDANT_MESHES")
        r = _check_material_assignment(scene, t, pr)
        assert r == {"result": "NOT_CHECKED", "note": "NO_MESH_IN_GEOMETRY_SCOPE"}


# ── result key verification ────────────────────────────────────────────
class TestResultKeys:
    def test_pass_keys(self):
        r = _check_material_slots_for_mesh(
            FakeObj("m", material_slots=[FakeSlot("ok")]), "m")
        assert sorted(r.keys()) == sorted(["mesh_name", "result", "slot_count"])

    def test_fail_no_slots_keys(self):
        r = _check_material_slots_for_mesh(FakeObj("m"), "m")
        assert sorted(r.keys()) == sorted(["mesh_name", "result", "failure_code"])

    def test_fail_null_keys(self):
        r = _check_material_slots_for_mesh(
            FakeObj("m", material_slots=[FakeSlot(None)]), "m")
        assert sorted(r.keys()) == sorted(
            ["mesh_name", "result", "failure_code", "null_slot_indices"])

    def test_not_checked_keys(self):
        t = {"material_assignment": None, "geometry_scope": "SELF_MESH"}
        r = _check_material_assignment(FakeScene([]), t, _make_root_pass())
        assert sorted(r.keys()) == sorted(["result", "note"])

    def test_top_level_fail_keys(self):
        root = FakeObj("root", "MESH", material_slots=[])
        scene = FakeScene([root])
        t = _target({"require_material_assignment_presence": True}, "SELF_MESH")
        r = _check_material_assignment(scene, t, _make_root_pass())
        assert sorted(r.keys()) == sorted(["result", "failure_code", "per_mesh"])


# ── F-002: root resolution exceptions ──────────────────────────────────
class TestRootResolution:
    def test_no_matching_root_returns_error(self):
        root = FakeObj("other", "MESH", material_slots=[FakeSlot("mat1")])
        scene = FakeScene([root])
        t = _target({"require_material_assignment_presence": True}, "SELF_MESH")
        t["root_object_name"] = "root_target"
        r = _check_material_assignment(scene, t, _make_root_pass())
        assert r == {"result": "ERROR",
                      "error_type": "MATERIAL_ASSIGNMENT_COMPUTATION_ERROR",
                      "operation": "RESOLVE_ROOT_OBJECT",
                      "note": "RESOLVE_ROOT_OBJECT_FAILED"}

    def test_two_homonymous_roots_returns_error(self):
        a1 = FakeObj("dup", "MESH", material_slots=[FakeSlot("mat1")])
        a2 = FakeObj("dup", "MESH", material_slots=[FakeSlot("mat2")])
        scene = FakeScene([a1, a2])
        t = _target({"require_material_assignment_presence": True}, "SELF_MESH")
        t["root_object_name"] = "dup"
        r = _check_material_assignment(scene, t, _make_root_pass())
        assert r == {"result": "ERROR",
                      "error_type": "MATERIAL_ASSIGNMENT_COMPUTATION_ERROR",
                      "operation": "RESOLVE_ROOT_OBJECT",
                      "note": "RESOLVE_ROOT_OBJECT_FAILED"}

    def test_two_homonymous_different_slots_returns_error(self):
        a1 = FakeObj("dup", "MESH", material_slots=[FakeSlot("mat1")])
        a2 = FakeObj("dup", "MESH", material_slots=[])
        scene = FakeScene([a1, a2])
        t = _target({"require_material_assignment_presence": True}, "SELF_MESH")
        t["root_object_name"] = "dup"
        r = _check_material_assignment(scene, t, _make_root_pass())
        assert r == {"result": "ERROR",
                      "error_type": "MATERIAL_ASSIGNMENT_COMPUTATION_ERROR",
                      "operation": "RESOLVE_ROOT_OBJECT",
                      "note": "RESOLVE_ROOT_OBJECT_FAILED"}


# ── F-002: zero bpy reads on disabled/unconfigured path ────────────────
class _ExplodingScene:
    """Fake scene that explodes if .objects is accessed."""
    @property
    def objects(self):
        raise AssertionError("scene.objects must not be read")


def test_no_read_when_block_missing():
    t = {"geometry_scope": "SELF_MESH"}
    r = _check_material_assignment(_ExplodingScene(), t, _make_root_pass())
    assert r == {"result": "NOT_CHECKED", "note": "MATERIAL_ASSIGNMENT_NOT_CONFIGURED"}


def test_no_read_when_block_none():
    t = _target(None)
    r = _check_material_assignment(_ExplodingScene(), t, _make_root_pass())
    assert r == {"result": "NOT_CHECKED", "note": "MATERIAL_ASSIGNMENT_NOT_CONFIGURED"}


def test_no_read_when_empty_dict():
    t = _target({})
    r = _check_material_assignment(_ExplodingScene(), t, _make_root_pass())
    assert r == {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"}


def test_no_read_when_require_false():
    t = _target({"require_material_assignment_presence": False})
    r = _check_material_assignment(_ExplodingScene(), t, _make_root_pass())
    assert r == {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"}


def test_no_read_when_root_not_found():
    t = _target({"require_material_assignment_presence": True})
    pr = {"checks": {"object_exists": {"result": "FAIL"}}}
    r = _check_material_assignment(_ExplodingScene(), t, pr)
    assert r == {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_NOT_FOUND"}


def test_no_read_when_root_type_mismatch():
    t = _target({"require_material_assignment_presence": True})
    pr = {"checks": {"object_exists": {"result": "PASS"},
                     "object_type": {"result": "FAIL"}}}
    r = _check_material_assignment(_ExplodingScene(), t, pr)
    assert r == {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_TYPE_MISMATCH"}


# ── F-002: read count probe ────────────────────────────────────────────
class CountingObj:
    """Fake that counts property accesses for read count verification."""
    def __init__(self, name, obj_type="MESH", children=None, material_slots=None,
                 raise_on=None):
        self._name = name
        self._type = obj_type
        self._children = children if children is not None else []
        self._material_slots = material_slots if material_slots is not None else []
        self._raise_on = raise_on if raise_on is not None else set()
        self.attr_reads = {}

    def _record(self, attr):
        self.attr_reads[attr] = self.attr_reads.get(attr, 0) + 1
        if attr in self._raise_on:
            raise RuntimeError(f"FAKE_ERROR_{attr}")

    @property
    def name(self):
        self._record("name")
        return self._name

    @property
    def type(self):
        self._record("type")
        return self._type

    @property
    def children(self):
        self._record("children")
        return self._children

    @property
    def material_slots(self):
        self._record("material_slots")
        return self._material_slots


class CountingSlot:
    def __init__(self, material):
        self._material = material
        self.material_reads = 0

    @property
    def material(self):
        self.material_reads += 1
        return self._material


class CountingScene:
    def __init__(self, objects):
        self._objects = objects
        self.objects_reads = 0

    @property
    def objects(self):
        self.objects_reads += 1
        return self._objects


class TestReadCounts:
    def test_self_and_descendant_path_counts(self):
        slot_m1 = CountingSlot("mat1")
        slot_m2 = CountingSlot("mat2")
        m1 = CountingObj("m1", "MESH", material_slots=[slot_m1])
        m2 = CountingObj("m2", "MESH", material_slots=[slot_m2])
        # EMPTY intermediate with 2 children, one of which is MESH descendant
        mid = CountingObj("mid", "EMPTY", children=[m1, m2])
        root = CountingObj("root", "MESH", children=[mid],
                           material_slots=[CountingSlot("root_mat")])
        scene = CountingScene([root, mid, m1, m2])

        t = _target({"require_material_assignment_presence": True},
                    "SELF_AND_DESCENDANT_MESHES")
        pr = {"checks": {"object_exists": {"result": "PASS"},
                         "object_type": {"result": "PASS", "actual": "MESH"}}}
        r = _check_material_assignment(scene, t, pr)

        assert r["result"] == "PASS"
        assert len(r["per_mesh"]) == 3  # root + m1 + m2

        # Verify read counts
        assert scene.objects_reads == 1
        # name: root, mid, m1, m2
        for obj in [root, mid, m1, m2]:
            assert obj.attr_reads.get("name", 0) == 1
        # root_obj.type: 0 (reuse from per_target_result)
        assert root.attr_reads.get("type", 0) == 0
        # root.children: 1
        assert root.attr_reads.get("children", 0) == 1
        # mid.children: 1, mid.type: 1 (descendant)
        assert mid.attr_reads.get("children", 0) == 1
        assert mid.attr_reads.get("type", 0) == 1
        # m1,m2.type: 1 each (descendant)
        assert m1.attr_reads.get("type", 0) == 1
        assert m2.attr_reads.get("type", 0) == 1
        # m1,m2 children: 1 each (DFS pushes their children onto stack)
        assert m1.attr_reads.get("children", 0) == 1
        assert m2.attr_reads.get("children", 0) == 1
        # material_slots: 1 per MESH
        for obj in [root, m1, m2]:
            assert obj.attr_reads.get("material_slots", 0) == 1
        # slot.material: 1 per slot
        assert slot_m1.material_reads == 1
        assert slot_m2.material_reads == 1
