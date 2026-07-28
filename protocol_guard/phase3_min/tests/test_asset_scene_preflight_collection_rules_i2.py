"""Collection Rules I2 focused tests — ERROR branches + error collection.

No open_blend_and_get_scene integration, no scope guard, no Blender.
All tests run in CPython with fake objects and monkeypatched bpy.
"""
import pytest
from protocol_guard.phase3_min.blender_scene_reader import (
    _check_collection_rules_global,
    _check_collection_membership,
    _materialize_bpy_data_collections,
    _materialize_collection_ancestor_index,
    _compute_ancestor_closure,
    _resolve_root_for_collection_rules,
    _CollectionRulesError,
    _cr_global_error,
    _cr_per_target_error,
)
from protocol_guard.phase3_min.asset_scene_preflight_check import (
    _collect_target_errors,
)
import protocol_guard.phase3_min.blender_scene_reader as bsr
import protocol_guard.phase3_min.asset_scene_preflight_check as check_mod


# ── fakes ────────────────────────────────────────────────────────────────


class FakeCollection:
    def __init__(self, name, children=None, explode_name=False, explode_children=False):
        self._name = name
        self._children = children if children is not None else []
        self._explode_name = explode_name
        self._explode_children = explode_children

    @property
    def name(self):
        if self._explode_name:
            raise RuntimeError("BOOM: collection.name read failed")
        return self._name

    @property
    def children(self):
        if self._explode_children:
            raise RuntimeError("BOOM: collection.children read failed")
        return self._children


class FakeObj:
    def __init__(self, name, obj_type="MESH", explode_name=False,
                 explode_users_collection=False, users_collection=None):
        self._name = name
        self.type = obj_type
        self.children = []
        self._users_collection = users_collection if users_collection is not None else []
        self._explode_name = explode_name
        self._explode_users_collection = explode_users_collection

    @property
    def name(self):
        if self._explode_name:
            raise RuntimeError("BOOM: obj.name read failed")
        return self._name

    @property
    def users_collection(self):
        if self._explode_users_collection:
            raise RuntimeError("BOOM: users_collection read failed")
        return self._users_collection


class FakeScene:
    def __init__(self, objects, explode_objects=False):
        self._objects = objects
        self._explode_objects = explode_objects

    @property
    def objects(self):
        if self._explode_objects:
            raise RuntimeError("BOOM: scene.objects read failed")
        return self._objects


class FakeBpyData:
    def __init__(self, collections, explode_collections=False):
        self._collections = collections
        self._explode_collections = explode_collections

    @property
    def collections(self):
        if self._explode_collections:
            raise RuntimeError("BOOM: bpy.data.collections read failed")
        return self._collections


class FakeBpy:
    def __init__(self, collections=None, explode_collections=False):
        self.data = FakeBpyData(
            collections if collections is not None else [],
            explode_collections=explode_collections,
        )


def _make_root_pass(root_type="MESH"):
    return {
        "checks": {
            "object_exists": {"result": "PASS"},
            "object_type": {"result": "PASS", "actual": root_type},
        }
    }


def _target(collection_names=None, root_object_name="root"):
    t = {"geometry_scope": "SELF_MESH", "root_object_name": root_object_name}
    if collection_names is not None:
        t["required_collection_names"] = collection_names
    return t


def _install_fake_bpy(monkeypatch, collections=None, explode_collections=False):
    fb = FakeBpy(collections, explode_collections=explode_collections)
    monkeypatch.setattr(bsr, "bpy", fb)
    return fb


# ── global ERROR tests ───────────────────────────────────────────────────


class TestGlobalErrorG1:
    """G1: MATERIALIZE_BPY_DATA_COLLECTIONS"""

    def test_bpy_data_collections_explodes(self, monkeypatch):
        _install_fake_bpy(monkeypatch, explode_collections=True)
        r = _check_collection_rules_global({"required_collection_names": ["A"]})
        assert r == {
            "result": "ERROR",
            "error_type": "COLLECTION_RULES_COMPUTATION_ERROR",
            "operation": "MATERIALIZE_BPY_DATA_COLLECTIONS",
            "note": "MATERIALIZE_BPY_DATA_COLLECTIONS_FAILED",
            "required": {"result": "NOT_CHECKED",
                         "note": "GLOBAL_ERROR_SHORT_CIRCUIT"},
            "forbidden": {"result": "NOT_CHECKED",
                          "note": "GLOBAL_ERROR_SHORT_CIRCUIT"},
        }

    def test_g1_key_set_exact(self, monkeypatch):
        _install_fake_bpy(monkeypatch, explode_collections=True)
        r = _check_collection_rules_global({"required_collection_names": ["A"]})
        assert set(r.keys()) == {
            "result", "error_type", "operation", "note", "required", "forbidden"}


class TestGlobalErrorG2:
    """G2: READ_COLLECTION_NAME"""

    def test_collection_name_explodes(self, monkeypatch):
        c = FakeCollection("A", explode_name=True)
        _install_fake_bpy(monkeypatch, [c])
        r = _check_collection_rules_global({"required_collection_names": ["A"]})
        assert r["result"] == "ERROR"
        assert r["operation"] == "READ_COLLECTION_NAME"
        assert r["note"] == "READ_COLLECTION_NAME_FAILED"

    def test_g2_short_circuits_sub_checks(self, monkeypatch):
        c = FakeCollection("A", explode_name=True)
        _install_fake_bpy(monkeypatch, [c])
        r = _check_collection_rules_global({
            "required_collection_names": ["A"],
            "forbidden_collection_name_patterns": ["*test*"],
        })
        assert r["required"]["result"] == "NOT_CHECKED"
        assert r["required"]["note"] == "GLOBAL_ERROR_SHORT_CIRCUIT"
        assert r["forbidden"]["result"] == "NOT_CHECKED"
        assert r["forbidden"]["note"] == "GLOBAL_ERROR_SHORT_CIRCUIT"


class TestGlobalErrorG3:
    """G3: RESOLVE_REQUIRED_COLLECTION"""

    def test_g3_resolve_error_built(self, monkeypatch):
        """G3 reached by making required_names dedup/sort explode."""
        c1 = FakeCollection("CHR_A")
        _install_fake_bpy(monkeypatch, [c1])
        import builtins
        original_sorted = builtins.sorted
        def _exploding_sorted(iterable, key=None):
            # Explode only when processing the required names (a set of strings)
            if isinstance(iterable, set) and all(isinstance(x, str) for x in iterable):
                raise RuntimeError("BOOM: G3")
            return original_sorted(iterable, key=key)
        monkeypatch.setattr(builtins, "sorted", _exploding_sorted)
        r = _check_collection_rules_global({"required_collection_names": ["CHR_A"]})
        assert r["result"] == "ERROR"
        assert r["operation"] == "RESOLVE_REQUIRED_COLLECTION"

    def test_g3_short_circuits_forbidden(self, monkeypatch):
        import builtins
        c1 = FakeCollection("CHR_A")
        _install_fake_bpy(monkeypatch, [c1])
        original_sorted = builtins.sorted
        def _exploding_sorted(iterable, key=None):
            if isinstance(iterable, set) and all(isinstance(x, str) for x in iterable):
                raise RuntimeError("BOOM: G3")
            return original_sorted(iterable, key=key)
        monkeypatch.setattr(builtins, "sorted", _exploding_sorted)
        r = _check_collection_rules_global({
            "required_collection_names": ["CHR_A"],
            "forbidden_collection_name_patterns": ["*test*"],
        })
        assert r["required"]["result"] == "NOT_CHECKED"
        assert r["required"]["note"] == "GLOBAL_ERROR_SHORT_CIRCUIT"
        assert r["forbidden"]["result"] == "NOT_CHECKED"
        assert r["forbidden"]["note"] == "GLOBAL_ERROR_SHORT_CIRCUIT"


class TestGlobalErrorG4:
    """G4: MATCH_FORBIDDEN_PATTERN"""

    def test_casefold_glob_match_explodes(self, monkeypatch):
        c1 = FakeCollection("CHR_A")
        _install_fake_bpy(monkeypatch, [c1])
        monkeypatch.setattr(
            "protocol_guard.phase3_min.asset_scene_preflight_core.casefold_glob_match",
            lambda name, pat: (_ for _ in ()).throw(RuntimeError("BOOM: G4")),
        )
        r = _check_collection_rules_global({
            "required_collection_names": [],
            "forbidden_collection_name_patterns": ["*test*"],
        })
        assert r["result"] == "ERROR"
        assert r["operation"] == "MATCH_FORBIDDEN_PATTERN"
        assert r["note"] == "MATCH_FORBIDDEN_PATTERN_FAILED"

    def test_g4_short_circuits_required(self, monkeypatch):
        c1 = FakeCollection("CHR_A")
        _install_fake_bpy(monkeypatch, [c1])
        monkeypatch.setattr(
            "protocol_guard.phase3_min.asset_scene_preflight_core.casefold_glob_match",
            lambda name, pat: (_ for _ in ()).throw(RuntimeError("BOOM: G4")),
        )
        r = _check_collection_rules_global({
            "required_collection_names": ["CHR_A"],
            "forbidden_collection_name_patterns": ["*test*"],
        })
        assert r["required"]["result"] == "NOT_CHECKED"
        assert r["required"]["note"] == "GLOBAL_ERROR_SHORT_CIRCUIT"
        assert r["forbidden"]["result"] == "NOT_CHECKED"
        assert r["forbidden"]["note"] == "GLOBAL_ERROR_SHORT_CIRCUIT"


class TestGlobalErrorG5:
    """G5: READ_COLLECTION_CHILDREN_GLOBAL — builder supported, not runtime reachable."""

    def test_g5_builder_produces_correct_dict(self):
        r = _cr_global_error("READ_COLLECTION_CHILDREN_GLOBAL")
        assert r == {
            "result": "ERROR",
            "error_type": "COLLECTION_RULES_COMPUTATION_ERROR",
            "operation": "READ_COLLECTION_CHILDREN_GLOBAL",
            "note": "READ_COLLECTION_CHILDREN_GLOBAL_FAILED",
            "required": {"result": "NOT_CHECKED",
                         "note": "GLOBAL_ERROR_SHORT_CIRCUIT"},
            "forbidden": {"result": "NOT_CHECKED",
                          "note": "GLOBAL_ERROR_SHORT_CIRCUIT"},
        }

    def test_g5_not_runtime_reachable(self, monkeypatch):
        """Global required+forbidden path does not read collection.children."""
        c1 = FakeCollection("CHR_A", explode_children=True)
        _install_fake_bpy(monkeypatch, [c1])
        r = _check_collection_rules_global({
            "required_collection_names": ["CHR_A"],
            "forbidden_collection_name_patterns": ["*nope*"],
        })
        assert r["result"] == "PASS"

    def test_global_no_children_access_in_forbidden(self, monkeypatch):
        """Forbidden check only uses name set, never children."""
        c1 = FakeCollection("CHR_A", explode_children=True)
        _install_fake_bpy(monkeypatch, [c1])
        r = _check_collection_rules_global(
            {"required_collection_names": [], "forbidden_collection_name_patterns": ["*A*"]})
        assert r["forbidden"]["result"] == "FAIL"


# ── per-target ERROR tests ───────────────────────────────────────────────


class TestPerTargetErrorP4:
    """P4: RESOLVE_ROOT_OBJECT_FOR_COLLECTION"""

    def test_scene_objects_explodes(self, monkeypatch):
        scene = FakeScene([], explode_objects=True)
        t = _target(["CHR_A"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert r == {
            "result": "ERROR",
            "error_type": "COLLECTION_RULES_COMPUTATION_ERROR",
            "operation": "RESOLVE_ROOT_OBJECT_FOR_COLLECTION",
            "note": "RESOLVE_ROOT_OBJECT_FOR_COLLECTION_FAILED",
        }

    def test_obj_name_explodes(self, monkeypatch):
        root = FakeObj("root", explode_name=True)
        scene = FakeScene([root])
        t = _target(["CHR_A"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert r["result"] == "ERROR"
        assert r["operation"] == "RESOLVE_ROOT_OBJECT_FOR_COLLECTION"

    def test_p4_key_set_exact(self, monkeypatch):
        scene = FakeScene([], explode_objects=True)
        t = _target(["CHR_A"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert set(r.keys()) == {"result", "error_type", "operation", "note"}

    def test_p4_no_normal_path_field_leaks(self, monkeypatch):
        scene = FakeScene([], explode_objects=True)
        t = _target(["CHR_A"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        for k in ("required_names", "direct_collections", "ancestor_collections",
                   "matched_names", "missing_names", "failure_code"):
            assert k not in r

    def test_p4_config_not_checked_still_not_checked(self, monkeypatch):
        """Normal NOT_CHECKED paths are NOT converted to ERROR."""
        scene = FakeScene([], explode_objects=True)
        t = _target([])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert r["result"] == "NOT_CHECKED"


class TestPerTargetErrorP1:
    """P1: READ_ROOT_USERS_COLLECTION"""

    def test_users_collection_explodes(self, monkeypatch):
        col = FakeCollection("CHR_A")
        root = FakeObj("root", obj_type="MESH", explode_users_collection=True)
        scene = FakeScene([root])
        _install_fake_bpy(monkeypatch, [col])
        t = _target(["CHR_A"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert r == {
            "result": "ERROR",
            "error_type": "COLLECTION_RULES_COMPUTATION_ERROR",
            "operation": "READ_ROOT_USERS_COLLECTION",
            "note": "READ_ROOT_USERS_COLLECTION_FAILED",
        }

    def test_p1_no_normal_path_field_leaks(self, monkeypatch):
        root = FakeObj("root", obj_type="MESH", explode_users_collection=True)
        scene = FakeScene([root])
        _install_fake_bpy(monkeypatch, [FakeCollection("CHR_A")])
        t = _target(["CHR_A"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        for k in ("required_names", "direct_collections", "ancestor_collections",
                   "matched_names", "missing_names", "failure_code"):
            assert k not in r


class TestPerTargetErrorP3:
    """P3: READ_COLLECTION_NAME_PER_TARGET"""

    def test_collection_name_explodes_in_materialize(self, monkeypatch):
        col = FakeCollection("CHR_A", explode_name=True)
        root = FakeObj("root", obj_type="MESH", users_collection=[col])
        scene = FakeScene([root])
        _install_fake_bpy(monkeypatch, [col])
        t = _target(["CHR_A"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert r["result"] == "ERROR"
        assert r["operation"] == "READ_COLLECTION_NAME_PER_TARGET"
        assert r["collection_name"] == "<UNREADABLE_COLLECTION>"
        assert r["note"] == "READ_COLLECTION_NAME_PER_TARGET_FAILED"

    def test_p3_key_set_exact(self, monkeypatch):
        col = FakeCollection("CHR_A", explode_name=True)
        root = FakeObj("root", obj_type="MESH", users_collection=[col])
        scene = FakeScene([root])
        _install_fake_bpy(monkeypatch, [col])
        t = _target(["CHR_A"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert set(r.keys()) == {
            "result", "error_type", "operation", "note", "collection_name"}


class TestPerTargetErrorP2:
    """P2: READ_COLLECTION_CHILDREN_PER_TARGET"""

    def test_collection_children_explodes(self, monkeypatch):
        parent = FakeCollection("Parent", explode_children=True)
        child = FakeCollection("Child")
        root = FakeObj("root", obj_type="MESH", users_collection=[child])
        scene = FakeScene([root])
        _install_fake_bpy(monkeypatch, [parent, child])
        t = _target(["Parent"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert r["result"] == "ERROR"
        assert r["operation"] == "READ_COLLECTION_CHILDREN_PER_TARGET"
        assert r["collection_name"] == "Parent"
        assert r["note"] == "READ_COLLECTION_CHILDREN_PER_TARGET_FAILED"

    def test_p2_key_set_exact(self, monkeypatch):
        parent = FakeCollection("Parent", explode_children=True)
        child = FakeCollection("Child")
        root = FakeObj("root", obj_type="MESH", users_collection=[child])
        scene = FakeScene([root])
        _install_fake_bpy(monkeypatch, [parent, child])
        t = _target(["Parent"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert set(r.keys()) == {
            "result", "error_type", "operation", "note", "collection_name"}

    def test_p2_no_ancestor_closure_after_error(self, monkeypatch):
        """P2 error short-circuits ancestor closure."""
        parent = FakeCollection("Parent", explode_children=True)
        child = FakeCollection("Child")
        root = FakeObj("root", obj_type="MESH", users_collection=[child])
        scene = FakeScene([root])
        _install_fake_bpy(monkeypatch, [parent, child])
        t = _target(["Parent"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        for k in ("required_names", "direct_collections", "ancestor_collections",
                   "matched_names", "missing_names", "failure_code"):
            assert k not in r


# ── CollectionRulesError + per_target_error helper ───────────────────────


class TestCollectionRulesError:
    def test_exception_carries_operation(self):
        e = _CollectionRulesError("TEST_OP")
        assert e.operation == "TEST_OP"
        assert e.collection_name is None

    def test_exception_carries_collection_name(self):
        e = _CollectionRulesError("TEST_OP", collection_name="MyCol")
        assert e.operation == "TEST_OP"
        assert e.collection_name == "MyCol"

    def test_cr_per_target_error_without_collection(self):
        r = _cr_per_target_error("READ_ROOT_USERS_COLLECTION")
        assert r == {
            "result": "ERROR",
            "error_type": "COLLECTION_RULES_COMPUTATION_ERROR",
            "operation": "READ_ROOT_USERS_COLLECTION",
            "note": "READ_ROOT_USERS_COLLECTION_FAILED",
        }

    def test_cr_per_target_error_with_collection(self):
        r = _cr_per_target_error(
            "READ_COLLECTION_CHILDREN_PER_TARGET", collection_name="Parent")
        assert r == {
            "result": "ERROR",
            "error_type": "COLLECTION_RULES_COMPUTATION_ERROR",
            "operation": "READ_COLLECTION_CHILDREN_PER_TARGET",
            "note": "READ_COLLECTION_CHILDREN_PER_TARGET_FAILED",
            "collection_name": "Parent",
        }


# ── error collection tests ───────────────────────────────────────────────


class TestErrorCollection:
    def test_per_target_error_without_collection_name(self, monkeypatch):
        scene = FakeScene([], explode_objects=True)
        t = _target(["CHR_A"], root_object_name="root")
        pr = _make_root_pass()
        r = _check_collection_membership(scene, t, pr)
        assert r["result"] == "ERROR"
        per_target = [
            {"target_id": "T1", "root_object_name": "root",
             "checks": {"collection_membership": r}, "overall": "ERROR"}
        ]
        msgs = _collect_target_errors(per_target)
        assert any("COLLECTION_RULES_COMPUTATION_ERROR" in m for m in msgs)
        assert any("collection_rules operation 'RESOLVE_ROOT_OBJECT_FOR_COLLECTION'" in m for m in msgs)

    def test_per_target_error_with_collection_name(self, monkeypatch):
        col = FakeCollection("Child")
        parent = FakeCollection("Parent", explode_children=True)
        root = FakeObj("root", obj_type="MESH", users_collection=[col])
        scene = FakeScene([root])
        _install_fake_bpy(monkeypatch, [parent, col])
        t = _target(["Parent"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        per_target = [
            {"target_id": "T1", "root_object_name": "root",
             "checks": {"collection_membership": r}, "overall": "ERROR"}
        ]
        msgs = _collect_target_errors(per_target)
        assert any("collection 'Parent'" in m for m in msgs)

    def test_non_error_membership_not_collected(self, monkeypatch):
        col = FakeCollection("CHR_A")
        root = FakeObj("root", obj_type="MESH", users_collection=[col])
        scene = FakeScene([root])
        _install_fake_bpy(monkeypatch, [col])
        t = _target(["CHR_A"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        per_target = [
            {"target_id": "T1", "root_object_name": "root",
             "checks": {"collection_membership": r}, "overall": "PASS"}
        ]
        msgs = _collect_target_errors(per_target)
        assert msgs == []

    def test_non_error_overall_skipped(self, monkeypatch):
        """Target with overall=PASS but collection_membership ERROR is skipped."""
        r = _cr_per_target_error("READ_ROOT_USERS_COLLECTION")
        per_target = [
            {"target_id": "T1", "root_object_name": "root",
             "checks": {"collection_membership": r}, "overall": "PASS"}
        ]
        msgs = _collect_target_errors(per_target)
        assert msgs == []


# ── F-002: exact order and stability tests ──────────────────────────────


class TestErrorSortOrder:
    def test_operation_primary_sort(self, monkeypatch):
        """Input order reversed, output sorted by operation."""
        e_rru = _cr_per_target_error("READ_ROOT_USERS_COLLECTION")
        e_ccpt = _cr_per_target_error(
            "READ_COLLECTION_CHILDREN_PER_TARGET", collection_name="Z")
        per_target = [
            {"target_id": "T1", "root_object_name": "root",
             "checks": {"collection_membership": e_rru}, "overall": "ERROR"},
            {"target_id": "T2", "root_object_name": "root",
             "checks": {"collection_membership": e_ccpt}, "overall": "ERROR"},
        ]
        msgs = _collect_target_errors(per_target)
        cr_msgs = [m for m in msgs if "COLLECTION_RULES" in m]
        assert len(cr_msgs) == 2
        assert "READ_COLLECTION_CHILDREN_PER_TARGET" in cr_msgs[0]
        assert "READ_ROOT_USERS_COLLECTION" in cr_msgs[1]

    def test_collection_name_secondary_sort(self, monkeypatch):
        """Same operation, different collection names → sorted by name."""
        e_zulu = _cr_per_target_error(
            "READ_COLLECTION_CHILDREN_PER_TARGET", collection_name="Zulu")
        e_alpha = _cr_per_target_error(
            "READ_COLLECTION_CHILDREN_PER_TARGET", collection_name="Alpha")
        per_target = [
            {"target_id": "T1", "root_object_name": "root",
             "checks": {"collection_membership": e_zulu}, "overall": "ERROR"},
            {"target_id": "T2", "root_object_name": "root",
             "checks": {"collection_membership": e_alpha}, "overall": "ERROR"},
        ]
        msgs = _collect_target_errors(per_target)
        cr_msgs = [m for m in msgs if "COLLECTION_RULES" in m]
        assert len(cr_msgs) == 2
        assert "collection 'Alpha'" in cr_msgs[0]
        assert "collection 'Zulu'" in cr_msgs[1]

    def test_equal_key_stability(self, monkeypatch):
        """Same (operation, collection_name) → preserved input target order."""
        e1 = _cr_per_target_error(
            "READ_COLLECTION_CHILDREN_PER_TARGET", collection_name="Shared")
        e2 = _cr_per_target_error(
            "READ_COLLECTION_CHILDREN_PER_TARGET", collection_name="Shared")
        per_target = [
            {"target_id": "T2", "root_object_name": "root",
             "checks": {"collection_membership": e1}, "overall": "ERROR"},
            {"target_id": "T1", "root_object_name": "root",
             "checks": {"collection_membership": e2}, "overall": "ERROR"},
        ]
        msgs = _collect_target_errors(per_target)
        cr_msgs = [m for m in msgs if "COLLECTION_RULES" in m]
        assert len(cr_msgs) == 2
        assert "target 'T2'" in cr_msgs[0]
        assert "target 'T1'" in cr_msgs[1]

    def test_mixed_existing_error_order_preserved(self, monkeypatch):
        """Existing errors keep order; CR errors appended last, sorted."""
        e_cc = _cr_per_target_error(
            "READ_COLLECTION_CHILDREN_PER_TARGET", collection_name="Alpha")
        e_ru = _cr_per_target_error("READ_ROOT_USERS_COLLECTION")
        per_target = [
            {"target_id": "T0", "root_object_name": "root",
             "checks": {
                 "object_exists": {"result": "ERROR",
                                   "error_type": "AMBIGUOUS_ROOT_OBJECT_NAME",
                                   "match_count": 2},
                 "collection_membership": e_ru,
             },
             "overall": "ERROR"},
            {"target_id": "T1", "root_object_name": "root",
             "checks": {
                 "rotation": {"result": "ERROR",
                              "error_type": "ROTATION_COMPUTATION_ERROR",
                              "operation": "READ_ROOT_MATRIX_WORLD"},
                 "collection_membership": {"result": "NOT_CHECKED",
                                           "note": "NOT_CONFIGURED"},
             },
             "overall": "ERROR"},
            {"target_id": "T2", "root_object_name": "root",
             "checks": {"collection_membership": e_cc},
             "overall": "ERROR"},
        ]
        msgs = _collect_target_errors(per_target)
        # 1. AMBIGUOUS_ROOT_OBJECT_NAME first
        assert "AMBIGUOUS_ROOT_OBJECT_NAME" in msgs[0]
        # 2. ROTATION_COMPUTATION_ERROR second
        assert "ROTATION_COMPUTATION_ERROR" in msgs[1]
        # 3-4. CR errors appended last
        cr_msgs = msgs[2:]
        assert len(cr_msgs) == 2
        assert all("COLLECTION_RULES" in m for m in cr_msgs)
        # Sort order
        assert "READ_COLLECTION_CHILDREN_PER_TARGET" in cr_msgs[0]
        assert "READ_ROOT_USERS_COLLECTION" in cr_msgs[1]


# ── F-002: real short-circuit proof tests ───────────────────────────────


class TestRealShortCircuit:
    def test_p4_short_circuit_no_users_collection_read(self, monkeypatch):
        """P4 error → P1 / collection materialize never happens."""
        scene = FakeScene([], explode_objects=True)
        monkeypatch.setattr(bsr, "bpy", None)
        t = _target(["CHR_A"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert r["result"] == "ERROR"
        assert r["operation"] == "RESOLVE_ROOT_OBJECT_FOR_COLLECTION"

    def test_p1_short_circuit_no_bpy_read(self, monkeypatch):
        """P1 error → bpy.data.collections never read."""
        root = FakeObj("root", obj_type="MESH", explode_users_collection=True)
        scene = FakeScene([root])
        monkeypatch.setattr(bsr, "bpy", None)
        t = _target(["CHR_A"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert r["result"] == "ERROR"
        assert r["operation"] == "READ_ROOT_USERS_COLLECTION"

    def test_p3_short_circuit_no_children_read(self, monkeypatch):
        """P3 error → collection.children never read."""
        col = FakeCollection("CHR_A", explode_name=True, explode_children=True)
        root = FakeObj("root", obj_type="MESH", users_collection=[col])
        scene = FakeScene([root])
        _install_fake_bpy(monkeypatch, [col])
        t = _target(["CHR_A"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert r["result"] == "ERROR"
        assert r["operation"] == "READ_COLLECTION_NAME_PER_TARGET"
        assert r["collection_name"] == "<UNREADABLE_COLLECTION>"

    def test_p2_short_circuit_no_closure(self, monkeypatch):
        """P2 error → ancestor closure never executed."""
        def _explode_closure(*args, **kwargs):
            raise AssertionError("BUG: _compute_ancestor_closure called after P2 error")
        monkeypatch.setattr(
            bsr, "_compute_ancestor_closure", _explode_closure)
        parent = FakeCollection("Parent", explode_children=True)
        child = FakeCollection("Child")
        root = FakeObj("root", obj_type="MESH", users_collection=[child])
        scene = FakeScene([root])
        _install_fake_bpy(monkeypatch, [parent, child])
        t = _target(["Parent"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert r["result"] == "ERROR"
        assert r["operation"] == "READ_COLLECTION_CHILDREN_PER_TARGET"

    def test_g2_midstream_short_circuit(self, monkeypatch):
        """G2 fails on 2nd collection → 3rd name never read."""
        class CountingMidstreamCol:
            def __init__(self, name, explode_name=False):
                self._name = name
                self._explode_name = explode_name
                self.name_read_count = 0
            @property
            def name(self):
                self.name_read_count += 1
                if self._explode_name:
                    raise RuntimeError("BOOM: midstream name")
                return self._name

        c1 = CountingMidstreamCol("A")
        c2 = CountingMidstreamCol("B", explode_name=True)
        c3 = CountingMidstreamCol("C")
        _install_fake_bpy(monkeypatch, [c1, c2, c3])
        r = _check_collection_rules_global({
            "required_collection_names": ["A"],
            "forbidden_collection_name_patterns": ["*x*"],
        })
        assert r["result"] == "ERROR"
        assert r["operation"] == "READ_COLLECTION_NAME"
        assert r["required"]["note"] == "GLOBAL_ERROR_SHORT_CIRCUIT"
        assert r["forbidden"]["note"] == "GLOBAL_ERROR_SHORT_CIRCUIT"
        assert c3.name_read_count == 0


# ── _CollectionRulesError re-raised through helpers ────────────────────────


class TestInternalExceptionPassthrough:
    def test_cr_error_re_raised_from_global(self, monkeypatch):
        """_CollectionRulesError is not swallowed by generic except."""
        def _raise_cr():
            raise _CollectionRulesError("MATERIALIZE_BPY_DATA_COLLECTIONS")
        monkeypatch.setattr(bsr, "bpy", type("FakeBpy", (), {
            "data": type("FakeData", (), {"collections": property(lambda s: _raise_cr())})()}))
        r = _check_collection_rules_global({"required_collection_names": ["A"]})
        assert r["result"] == "ERROR"
        assert r["operation"] == "MATERIALIZE_BPY_DATA_COLLECTIONS"

    def test_cr_error_re_raised_from_per_target(self, monkeypatch):
        """_CollectionRulesError propagated through _check_collection_membership."""
        def _raise_cr():
            raise _CollectionRulesError("MATERIALIZE_BPY_DATA_COLLECTIONS")
        root = FakeObj("root", obj_type="MESH", users_collection=[FakeCollection("A")])
        scene = FakeScene([root])
        monkeypatch.setattr(bsr, "bpy", type("FakeBpy", (), {
            "data": type("FakeData", (), {"collections": property(lambda s: _raise_cr())})()}))
        t = _target(["CHR_A"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert r["result"] == "ERROR"
        assert r["operation"] == "MATERIALIZE_BPY_DATA_COLLECTIONS"
