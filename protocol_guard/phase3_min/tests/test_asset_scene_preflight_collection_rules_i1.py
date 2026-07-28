"""Collection Rules I1 focused tests — config -> PASS/FAIL/NOT_CHECKED only.

No ERROR, no open_blend_and_get_scene integration, no scope guard, no Blender.
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
)
import protocol_guard.phase3_min.blender_scene_reader as bsr


# ── helpers ────────────────────────────────────────────────────────────


class FakeCollection:
    """Fake Blender Collection."""
    def __init__(self, name, children=None):
        self._name = name
        self.children = children if children is not None else []

    @property
    def name(self):
        return self._name


class FakeObj:
    """Fake Blender object."""
    def __init__(self, name, obj_type="MESH", children=None, users_collection=None):
        self._name = name
        self.type = obj_type
        self.children = children if children is not None else []
        self.users_collection = users_collection if users_collection is not None else []

    @property
    def name(self):
        return self._name


class FakeScene:
    """Fake scene wrapping objects."""
    def __init__(self, objects):
        self.objects = objects


class FakeBpyData:
    """Fake bpy.data with collections attribute."""
    def __init__(self, collections):
        self.collections = collections


class FakeBpy:
    """Fake bpy module."""
    def __init__(self, collections=None):
        self.data = FakeBpyData(collections if collections is not None else [])


def _make_root_pass(root_type="MESH"):
    """Return a per_target_result with root checks both PASS."""
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


def _install_fake_bpy(monkeypatch, collections=None):
    """Install FakeBpy into bsr module."""
    fb = FakeBpy(collections)
    monkeypatch.setattr(bsr, "bpy", fb)
    return fb


# ── global config semantics ────────────────────────────────────────────


class TestGlobalConfigSemantics:
    def test_none_block_returns_none(self, monkeypatch):
        r = _check_collection_rules_global(None)
        assert r is None

    def test_empty_dict_not_checked(self, monkeypatch):
        r = _check_collection_rules_global({})
        assert r == {
            "result": "NOT_CHECKED",
            "required": {"result": "NOT_CHECKED",
                         "note": "REQUIRED_COLLECTION_NAMES_NOT_CONFIGURED"},
            "forbidden": {"result": "NOT_CHECKED",
                          "note": "FORBIDDEN_COLLECTION_NAME_PATTERNS_NOT_CONFIGURED"},
        }

    def test_required_missing_field_not_checked(self, monkeypatch):
        _install_fake_bpy(monkeypatch, [FakeCollection("X")])
        r = _check_collection_rules_global({"forbidden_collection_name_patterns": ["*x*"]})
        assert r["required"] == {
            "result": "NOT_CHECKED",
            "note": "REQUIRED_COLLECTION_NAMES_NOT_CONFIGURED",
        }

    def test_required_null_not_checked(self, monkeypatch):
        _install_fake_bpy(monkeypatch, [])
        r = _check_collection_rules_global(
            {"required_collection_names": None, "forbidden_collection_name_patterns": []})
        assert r["required"] == {
            "result": "NOT_CHECKED",
            "note": "REQUIRED_COLLECTION_NAMES_NOT_CONFIGURED",
        }

    def test_required_empty_array_not_checked(self, monkeypatch):
        _install_fake_bpy(monkeypatch, [FakeCollection("X")])
        r = _check_collection_rules_global(
            {"required_collection_names": [], "forbidden_collection_name_patterns": ["*x*"]})
        assert r["required"] == {
            "result": "NOT_CHECKED",
            "note": "REQUIRED_COLLECTION_NAMES_NOT_CONFIGURED",
        }

    def test_forbidden_missing_field_not_checked(self, monkeypatch):
        _install_fake_bpy(monkeypatch, [FakeCollection("A")])
        r = _check_collection_rules_global({"required_collection_names": ["A"]})
        assert r["forbidden"] == {
            "result": "NOT_CHECKED",
            "note": "FORBIDDEN_COLLECTION_NAME_PATTERNS_NOT_CONFIGURED",
        }

    def test_forbidden_null_not_checked(self, monkeypatch):
        _install_fake_bpy(monkeypatch, [FakeCollection("A")])
        r = _check_collection_rules_global(
            {"required_collection_names": ["A"], "forbidden_collection_name_patterns": None})
        assert r["forbidden"] == {
            "result": "NOT_CHECKED",
            "note": "FORBIDDEN_COLLECTION_NAME_PATTERNS_NOT_CONFIGURED",
        }

    def test_forbidden_empty_array_not_checked(self, monkeypatch):
        _install_fake_bpy(monkeypatch, [FakeCollection("A")])
        r = _check_collection_rules_global(
            {"required_collection_names": ["A"], "forbidden_collection_name_patterns": []})
        assert r["forbidden"] == {
            "result": "NOT_CHECKED",
            "note": "FORBIDDEN_COLLECTION_NAME_PATTERNS_NOT_CONFIGURED",
        }

    def test_both_not_checked_top_not_checked(self, monkeypatch):
        r = _check_collection_rules_global({})
        assert r["result"] == "NOT_CHECKED"


# ── global required ─────────────────────────────────────────────────────


class TestGlobalRequired:
    def test_all_exist_pass(self, monkeypatch):
        c1 = FakeCollection("CHR_A")
        c2 = FakeCollection("CHR_B")
        _install_fake_bpy(monkeypatch, [c1, c2])
        r = _check_collection_rules_global({"required_collection_names": ["CHR_A", "CHR_B"]})
        assert r["required"] == {
            "result": "PASS",
            "required_names": ["CHR_A", "CHR_B"],
            "missing_names": [],
        }

    def test_partial_missing_fail(self, monkeypatch):
        c1 = FakeCollection("CHR_A")
        _install_fake_bpy(monkeypatch, [c1])
        r = _check_collection_rules_global({"required_collection_names": ["CHR_A", "CHR_B"]})
        assert r["required"]["result"] == "FAIL"
        assert r["required"]["failure_code"] == "REQUIRED_COLLECTION_MISSING"
        assert r["required"]["missing_names"] == ["CHR_B"]

    def test_all_missing_fail(self, monkeypatch):
        _install_fake_bpy(monkeypatch, [])
        r = _check_collection_rules_global({"required_collection_names": ["CHR_A"]})
        assert r["required"]["result"] == "FAIL"
        assert r["required"]["missing_names"] == ["CHR_A"]

    def test_duplicate_required_names_dedup(self, monkeypatch):
        c1 = FakeCollection("CHR_A")
        _install_fake_bpy(monkeypatch, [c1])
        r = _check_collection_rules_global({"required_collection_names": ["CHR_A", "CHR_A"]})
        assert r["required"]["required_names"] == ["CHR_A"]

    def test_case_sensitive_matching(self, monkeypatch):
        c1 = FakeCollection("CHR_A")
        _install_fake_bpy(monkeypatch, [c1])
        r = _check_collection_rules_global({"required_collection_names": ["chr_a"]})
        assert r["required"]["result"] == "FAIL"
        assert r["required"]["missing_names"] == ["chr_a"]

    def test_missing_names_sorted_casefold(self, monkeypatch):
        _install_fake_bpy(monkeypatch, [])
        r = _check_collection_rules_global({"required_collection_names": ["Z_col", "a_col", "M_col"]})
        assert r["required"]["missing_names"] == ["a_col", "M_col", "Z_col"]

    def test_required_names_sorted_casefold(self, monkeypatch):
        c1 = FakeCollection("a"); c2 = FakeCollection("Z"); c3 = FakeCollection("M")
        _install_fake_bpy(monkeypatch, [c1, c2, c3])
        r = _check_collection_rules_global({"required_collection_names": ["Z", "a", "M"]})
        assert r["required"]["required_names"] == ["a", "M", "Z"]


# ── global forbidden ────────────────────────────────────────────────────


class TestGlobalForbidden:
    def test_no_match_pass(self, monkeypatch):
        c1 = FakeCollection("CHR_A")
        _install_fake_bpy(monkeypatch, [c1])
        r = _check_collection_rules_global(
            {"required_collection_names": [], "forbidden_collection_name_patterns": ["*test*"]})
        assert r["forbidden"] == {
            "result": "PASS",
            "forbidden_patterns": ["*test*"],
            "matched_collections": [],
        }

    def test_casefold_match_fail(self, monkeypatch):
        c1 = FakeCollection("Test_Temp")
        _install_fake_bpy(monkeypatch, [c1])
        r = _check_collection_rules_global(
            {"required_collection_names": [], "forbidden_collection_name_patterns": ["*test*"]})
        assert r["forbidden"]["result"] == "FAIL"
        assert r["forbidden"]["failure_code"] == "FORBIDDEN_COLLECTION_MATCHED"
        assert r["forbidden"]["matched_collections"] == ["Test_Temp"]

    def test_multi_pattern_hit_one_collection_record_once(self, monkeypatch):
        c1 = FakeCollection("Test_Temp")
        _install_fake_bpy(monkeypatch, [c1])
        r = _check_collection_rules_global(
            {"required_collection_names": [],
             "forbidden_collection_name_patterns": ["*test*", "*Temp*"]})
        assert r["forbidden"]["result"] == "FAIL"
        assert r["forbidden"]["matched_collections"] == ["Test_Temp"]

    def test_one_pattern_hit_multi_collection_all_recorded(self, monkeypatch):
        c1 = FakeCollection("test_a")
        c2 = FakeCollection("test_b")
        _install_fake_bpy(monkeypatch, [c1, c2])
        r = _check_collection_rules_global(
            {"required_collection_names": [],
             "forbidden_collection_name_patterns": ["test_*"]})
        assert r["forbidden"]["result"] == "FAIL"
        assert r["forbidden"]["matched_collections"] == ["test_a", "test_b"]

    def test_duplicate_patterns_dedup(self, monkeypatch):
        c1 = FakeCollection("test_a")
        _install_fake_bpy(monkeypatch, [c1])
        r = _check_collection_rules_global(
            {"required_collection_names": [],
             "forbidden_collection_name_patterns": ["test_*", "test_*"]})
        assert r["forbidden"]["forbidden_patterns"] == ["test_*"]

    def test_required_pass_forbidden_fail_top_fail(self, monkeypatch):
        c1 = FakeCollection("CHR_A")
        c2 = FakeCollection("test_temp")
        _install_fake_bpy(monkeypatch, [c1, c2])
        r = _check_collection_rules_global({
            "required_collection_names": ["CHR_A"],
            "forbidden_collection_name_patterns": ["*test*"],
        })
        assert r["required"]["result"] == "PASS"
        assert r["forbidden"]["result"] == "FAIL"
        assert r["result"] == "FAIL"
        assert r["failure_code"] == "COLLECTION_RULES_FAILURE"

    def test_both_pass_top_pass(self, monkeypatch):
        c1 = FakeCollection("CHR_A")
        _install_fake_bpy(monkeypatch, [c1])
        r = _check_collection_rules_global({
            "required_collection_names": ["CHR_A"],
            "forbidden_collection_name_patterns": ["*nope*"],
        })
        assert r["result"] == "PASS"


# ── global top-level key sets ───────────────────────────────────────────


class TestGlobalKeySets:
    def test_top_not_checked_keys(self, monkeypatch):
        r = _check_collection_rules_global({})
        assert set(r.keys()) == {"result", "required", "forbidden"}

    def test_top_pass_keys(self, monkeypatch):
        c1 = FakeCollection("CHR_A")
        _install_fake_bpy(monkeypatch, [c1])
        r = _check_collection_rules_global({
            "required_collection_names": ["CHR_A"],
            "forbidden_collection_name_patterns": ["*nope*"],
        })
        assert set(r.keys()) == {"result", "required", "forbidden"}

    def test_top_fail_keys(self, monkeypatch):
        _install_fake_bpy(monkeypatch, [])
        r = _check_collection_rules_global({"required_collection_names": ["CHR_A"]})
        assert set(r.keys()) == {"result", "failure_code", "required", "forbidden"}


# ── per-target config semantics ─────────────────────────────────────────


class TestPerTargetConfigSemantics:
    def test_missing_field_not_checked(self, monkeypatch):
        t = {"geometry_scope": "SELF_MESH"}
        r = _check_collection_membership(FakeScene([]), t, _make_root_pass())
        assert r == {"result": "NOT_CHECKED",
                     "note": "REQUIRED_COLLECTION_NAMES_NOT_CONFIGURED"}

    def test_null_not_checked(self, monkeypatch):
        t = _target(None)
        r = _check_collection_membership(FakeScene([]), t, _make_root_pass())
        assert r == {"result": "NOT_CHECKED",
                     "note": "REQUIRED_COLLECTION_NAMES_NOT_CONFIGURED"}

    def test_empty_array_not_checked(self, monkeypatch):
        t = _target([])
        r = _check_collection_membership(FakeScene([]), t, _make_root_pass())
        assert r == {"result": "NOT_CHECKED",
                     "note": "REQUIRED_COLLECTION_NAMES_NOT_CONFIGURED"}


# ── per-target root preconditions ───────────────────────────────────────


class TestPerTargetRootPreconditions:
    def test_root_not_found(self, monkeypatch):
        pr = {"checks": {"object_exists": {"result": "FAIL"}}}
        t = _target(["CHR_A"])
        r = _check_collection_membership(FakeScene([]), t, pr)
        assert r == {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_NOT_FOUND"}

    def test_root_ambiguous(self, monkeypatch):
        pr = {"checks": {"object_exists": {"result": "PASS",
                     "error_type": "AMBIGUOUS_ROOT_OBJECT_NAME"}}}
        t = _target(["CHR_A"])
        r = _check_collection_membership(FakeScene([]), t, pr)
        assert r == {"result": "NOT_CHECKED", "note": "AMBIGUOUS_ROOT_OBJECT_NAME"}

    def test_root_type_mismatch(self, monkeypatch):
        pr = {"checks": {"object_exists": {"result": "PASS"},
                         "object_type": {"result": "FAIL"}}}
        t = _target(["CHR_A"])
        r = _check_collection_membership(FakeScene([]), t, pr)
        assert r == {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_TYPE_MISMATCH"}

    def test_object_type_not_pass(self, monkeypatch):
        pr = {"checks": {"object_exists": {"result": "PASS"},
                         "object_type": {"result": "NOT_CHECKED"}}}
        t = _target(["CHR_A"])
        r = _check_collection_membership(FakeScene([]), t, pr)
        assert r == {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_TYPE_MISMATCH"}

    def test_config_not_checked_does_not_read_bpy(self, monkeypatch):
        # Verify no bpy access when config is NOT_CHECKED
        t = _target([])
        r = _check_collection_membership(FakeScene([]), t, _make_root_pass())
        assert r["result"] == "NOT_CHECKED"


# ── per-target collection membership ────────────────────────────────────


class TestPerTargetMembership:
    def test_direct_collection_hit_pass(self, monkeypatch):
        col = FakeCollection("CHR_A")
        root = FakeObj("root", obj_type="MESH", users_collection=[col])
        scene = FakeScene([root])
        _install_fake_bpy(monkeypatch, [col])
        t = _target(["CHR_A"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert r["result"] == "PASS"
        assert r["matched_names"] == ["CHR_A"]
        assert r["direct_collections"] == ["CHR_A"]
        assert r["ancestor_collections"] == []
        assert r["missing_names"] == []

    def test_one_layer_ancestor_hit_pass(self, monkeypatch):
        parent_col = FakeCollection("Characters", children=[])
        child_col = FakeCollection("CHR_A", children=[])
        # Rebuild: parent's children includes child
        parent_col.children = [child_col]
        root = FakeObj("root", obj_type="MESH", users_collection=[child_col])
        scene = FakeScene([root])
        _install_fake_bpy(monkeypatch, [parent_col, child_col])
        t = _target(["Characters"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert r["result"] == "PASS"
        assert r["direct_collections"] == ["CHR_A"]
        assert r["ancestor_collections"] == ["Characters"]
        assert r["matched_names"] == ["Characters"]

    def test_multi_layer_ancestor_hit_pass(self, monkeypatch):
        gp = FakeCollection("Grandparent", children=[])
        parent = FakeCollection("Parent", children=[])
        child = FakeCollection("CHR_A", children=[])
        gp.children = [parent]
        parent.children = [child]
        root = FakeObj("root", obj_type="MESH", users_collection=[child])
        scene = FakeScene([root])
        _install_fake_bpy(monkeypatch, [gp, parent, child])
        t = _target(["Grandparent"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert r["result"] == "PASS"
        assert sorted(r["ancestor_collections"], key=lambda n: n.casefold()) == [
            "Grandparent", "Parent"]

    def test_at_least_one_hit_pass_missing_preserved(self, monkeypatch):
        col = FakeCollection("CHR_A")
        root = FakeObj("root", obj_type="MESH", users_collection=[col])
        scene = FakeScene([root])
        _install_fake_bpy(monkeypatch, [col])
        t = _target(["CHR_A", "CHR_B"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert r["result"] == "PASS"
        assert r["matched_names"] == ["CHR_A"]
        assert r["missing_names"] == ["CHR_B"]

    def test_no_match_fail(self, monkeypatch):
        col = FakeCollection("Other")
        root = FakeObj("root", obj_type="MESH", users_collection=[col])
        scene = FakeScene([root])
        _install_fake_bpy(monkeypatch, [col])
        t = _target(["CHR_A"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert r["result"] == "FAIL"
        assert r["failure_code"] == "TARGET_NOT_IN_REQUIRED_COLLECTION"
        assert r["matched_names"] == []
        assert r["missing_names"] == ["CHR_A"]

    def test_root_in_multiple_direct_at_least_one_pass(self, monkeypatch):
        col_a = FakeCollection("CHR_A")
        col_b = FakeCollection("Other")
        root = FakeObj("root", obj_type="MESH", users_collection=[col_a, col_b])
        scene = FakeScene([root])
        _install_fake_bpy(monkeypatch, [col_a, col_b])
        t = _target(["CHR_A"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert r["result"] == "PASS"
        assert sorted(r["direct_collections"], key=lambda n: n.casefold()) == [
            "CHR_A", "Other"]

    def test_multi_parent_collection_hit(self, monkeypatch):
        parent_a = FakeCollection("ParentA", children=[])
        parent_b = FakeCollection("ParentB", children=[])
        shared = FakeCollection("Shared", children=[])
        parent_a.children = [shared]
        parent_b.children = [shared]
        root = FakeObj("root", obj_type="MESH", users_collection=[shared])
        scene = FakeScene([root])
        _install_fake_bpy(monkeypatch, [parent_a, parent_b, shared])
        t = _target(["ParentA"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert r["result"] == "PASS"
        assert "ParentA" in r["ancestor_collections"]

    def test_scene_external_collection_option_b(self, monkeypatch):
        # Collection not in scene but in bpy.data.collections — OPTION_B allows
        col = FakeCollection("CHR_A")
        root = FakeObj("root", obj_type="MESH", users_collection=[col])
        scene = FakeScene([root])
        _install_fake_bpy(monkeypatch, [col])
        t = _target(["CHR_A"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert r["result"] == "PASS"

    def test_empty_direct_collection_no_ancestor_fail(self, monkeypatch):
        root = FakeObj("root", obj_type="MESH", users_collection=[])
        scene = FakeScene([root])
        _install_fake_bpy(monkeypatch, [])
        t = _target(["CHR_A"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert r["result"] == "FAIL"

    def test_deduplicated_direct_names(self, monkeypatch):
        col = FakeCollection("CHR_A")
        root = FakeObj("root", obj_type="MESH", users_collection=[col, col])
        scene = FakeScene([root])
        _install_fake_bpy(monkeypatch, [col])
        t = _target(["CHR_A"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert r["direct_collections"] == ["CHR_A"]


# ── per-target key sets ─────────────────────────────────────────────────


class TestPerTargetKeySets:
    def test_not_checked_keys(self, monkeypatch):
        t = _target([])
        r = _check_collection_membership(FakeScene([]), t, _make_root_pass())
        assert set(r.keys()) == {"result", "note"}

    def test_pass_keys(self, monkeypatch):
        col = FakeCollection("CHR_A")
        root = FakeObj("root", obj_type="MESH", users_collection=[col])
        scene = FakeScene([root])
        _install_fake_bpy(monkeypatch, [col])
        t = _target(["CHR_A"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert set(r.keys()) == {
            "result", "required_names", "direct_collections",
            "ancestor_collections", "matched_names", "missing_names",
        }

    def test_fail_keys(self, monkeypatch):
        root = FakeObj("root", obj_type="MESH", users_collection=[])
        scene = FakeScene([root])
        _install_fake_bpy(monkeypatch, [])
        t = _target(["CHR_A"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert set(r.keys()) == {
            "result", "failure_code", "required_names", "direct_collections",
            "ancestor_collections", "matched_names", "missing_names",
        }


# ── read count fakes ────────────────────────────────────────────────────


class CountingFakeCollection:
    """Fake Blender Collection with read counters."""
    def __init__(self, name, children=None):
        self._name = name
        self._children = children if children is not None else []
        self.name_read_count = 0
        self.children_read_count = 0

    @property
    def name(self):
        self.name_read_count += 1
        return self._name

    def _get_children(self):
        self.children_read_count += 1
        return self._children

    def _set_children(self, value):
        self._children = value

    children = property(_get_children, _set_children)


class CountingFakeObj:
    """Fake Blender object with read counters."""
    def __init__(self, name, obj_type="MESH", children=None, users_collection=None):
        self._name = name
        self.type = obj_type
        self._children = children if children is not None else []
        self._users_collection = users_collection if users_collection is not None else []
        self.name_read_count = 0
        self.users_collection_read_count = 0

    @property
    def name(self):
        self.name_read_count += 1
        return self._name

    @property
    def users_collection(self):
        self.users_collection_read_count += 1
        return self._users_collection

    @property
    def children(self):
        return self._children


class CountingFakeScene:
    """Fake scene with objects materialization counter."""
    def __init__(self, objects):
        self._objects = objects
        self.objects_read_count = 0

    @property
    def objects(self):
        self.objects_read_count += 1
        return self._objects


class CountingFakeBpyData:
    """Fake bpy.data with collections materialization counter."""
    def __init__(self, collections):
        self._collections = collections
        self.collections_read_count = 0

    @property
    def collections(self):
        self.collections_read_count += 1
        return self._collections


class CountingFakeBpy:
    """Fake bpy module with counting data."""
    def __init__(self, collections=None):
        self.data = CountingFakeBpyData(collections if collections is not None else [])


class ExplodingFakeCollection:
    """Collection that explodes if name or children is read."""
    def __init__(self, name, children=None):
        self._name = name
        self._children = children if children is not None else []

    @property
    def name(self):
        raise AssertionError("BUG: collection.name read outside materialize")

    @property
    def children(self):
        raise AssertionError("BUG: collection.children read outside materialize")


def _install_counting_bpy(monkeypatch, collections=None):
    fb = CountingFakeBpy(collections)
    monkeypatch.setattr(bsr, "bpy", fb)
    return fb


# ── real read count tests ────────────────────────────────────────────────


class TestDisabledPathExplodingGuards:
    """Verify disabled/not-configured paths never access bpy at all."""

    def test_none_block_never_reads_bpy(self, monkeypatch):
        # bpy.data.collections explodes if accessed
        monkeypatch.setattr(bsr, "bpy", None)
        r = _check_collection_rules_global(None)
        assert r is None

    def test_empty_dict_never_reads_bpy(self, monkeypatch):
        monkeypatch.setattr(bsr, "bpy", None)
        r = _check_collection_rules_global({})
        assert r["result"] == "NOT_CHECKED"

    def test_per_target_disabled_never_reads_bpy(self, monkeypatch):
        monkeypatch.setattr(bsr, "bpy", None)
        t = _target([])
        r = _check_collection_membership(FakeScene([]), t, _make_root_pass())
        assert r["result"] == "NOT_CHECKED"


class TestGlobalReadCounts:
    """Verify global layer: single materialization, name read once."""

    def test_collections_materialized_once(self, monkeypatch):
        c1 = CountingFakeCollection("CHR_A")
        c2 = CountingFakeCollection("CHR_B")
        fb = _install_counting_bpy(monkeypatch, [c1, c2])
        _check_collection_rules_global({
            "required_collection_names": ["CHR_A"],
            "forbidden_collection_name_patterns": ["*test*"],
        })
        assert fb.data.collections_read_count == 1

    def test_each_name_read_once(self, monkeypatch):
        c1 = CountingFakeCollection("CHR_A")
        c2 = CountingFakeCollection("CHR_B")
        _install_counting_bpy(monkeypatch, [c1, c2])
        _check_collection_rules_global({
            "required_collection_names": ["CHR_A", "CHR_B"],
            "forbidden_collection_name_patterns": ["*test*"],
        })
        assert c1.name_read_count == 1
        assert c2.name_read_count == 1

    def test_required_only_no_forbidden_reread(self, monkeypatch):
        c1 = CountingFakeCollection("CHR_A")
        _install_counting_bpy(monkeypatch, [c1])
        _check_collection_rules_global({
            "required_collection_names": ["CHR_A"],
        })
        assert c1.name_read_count == 1


class TestPerTargetReadCounts:
    """Verify per-target layer read counts."""

    def test_scene_objects_materialized_once(self, monkeypatch):
        col = CountingFakeCollection("CHR_A")
        root = CountingFakeObj("root", obj_type="MESH", users_collection=[col])
        scene = CountingFakeScene([root])
        _install_counting_bpy(monkeypatch, [col])
        t = _target(["CHR_A"])
        _check_collection_membership(scene, t, _make_root_pass())
        assert scene.objects_read_count == 1

    def test_each_candidate_name_read_once(self, monkeypatch):
        col = CountingFakeCollection("CHR_A")
        root = CountingFakeObj("root", obj_type="MESH", users_collection=[col])
        other = CountingFakeObj("other", obj_type="MESH")
        scene = CountingFakeScene([other, root])
        _install_counting_bpy(monkeypatch, [col])
        t = _target(["CHR_A"])
        _check_collection_membership(scene, t, _make_root_pass())
        assert root.name_read_count == 1
        assert other.name_read_count == 1

    def test_users_collection_read_once(self, monkeypatch):
        col = CountingFakeCollection("CHR_A")
        root = CountingFakeObj("root", obj_type="MESH", users_collection=[col])
        scene = CountingFakeScene([root])
        _install_counting_bpy(monkeypatch, [col])
        t = _target(["CHR_A"])
        _check_collection_membership(scene, t, _make_root_pass())
        assert root.users_collection_read_count == 1

    def test_bpy_collections_materialized_once_per_target(self, monkeypatch):
        col = CountingFakeCollection("CHR_A")
        root = CountingFakeObj("root", obj_type="MESH", users_collection=[col])
        scene = CountingFakeScene([root])
        fb = _install_counting_bpy(monkeypatch, [col])
        t = _target(["CHR_A"])
        _check_collection_membership(scene, t, _make_root_pass())
        assert fb.data.collections_read_count == 1

    def test_collection_children_read_once(self, monkeypatch):
        parent = CountingFakeCollection("Parent", children=[])
        child = CountingFakeCollection("CHR_A", children=[])
        parent.children = [child]
        root = CountingFakeObj("root", obj_type="MESH", users_collection=[child])
        scene = CountingFakeScene([root])
        _install_counting_bpy(monkeypatch, [parent, child])
        t = _target(["Parent"])
        _check_collection_membership(scene, t, _make_root_pass())
        assert parent.children_read_count == 1
        assert child.children_read_count == 1

    def test_collection_name_read_once_in_ancestor_path(self, monkeypatch):
        parent = CountingFakeCollection("Parent", children=[])
        child = CountingFakeCollection("CHR_A", children=[])
        parent.children = [child]
        root = CountingFakeObj("root", obj_type="MESH", users_collection=[child])
        scene = CountingFakeScene([root])
        _install_counting_bpy(monkeypatch, [parent, child])
        t = _target(["Parent"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert r["result"] == "PASS"
        # Both collections should have name read exactly once (by _materialize)
        assert parent.name_read_count == 1
        assert child.name_read_count == 1

    def test_full_ancestor_closure_read_counts(self, monkeypatch):
        """Direct + parent ancestor: all reads at most once."""
        parent = CountingFakeCollection("Parent", children=[])
        child = CountingFakeCollection("Child", children=[])
        parent.children = [child]
        root = CountingFakeObj("root", obj_type="MESH", users_collection=[child])
        scene = CountingFakeScene([root])
        fb = _install_counting_bpy(monkeypatch, [parent, child])
        t = _target(["Parent"])
        r = _check_collection_membership(scene, t, _make_root_pass())
        assert r["result"] == "PASS"
        assert r["direct_collections"] == ["Child"]
        assert r["ancestor_collections"] == ["Parent"]
        assert r["matched_names"] == ["Parent"]
        # Verify read counts
        assert scene.objects_read_count == 1
        assert root.name_read_count == 1
        assert root.users_collection_read_count == 1
        assert fb.data.collections_read_count == 1
        assert parent.children_read_count == 1
        assert child.children_read_count == 1
        assert parent.name_read_count == 1
        assert child.name_read_count == 1


class TestClosureCacheOnly:
    """Verify _compute_ancestor_closure never re-reads name/children."""

    def test_direct_name_from_cache_only(self, monkeypatch):
        dc = ExplodingFakeCollection("Direct")
        direct, ancestors = _compute_ancestor_closure(
            [dc], {}, {}, {id(dc): "Direct"})
        assert direct == ["Direct"]

    def test_ancestor_name_from_cache_only(self, monkeypatch):
        child = ExplodingFakeCollection("Child")
        parent = ExplodingFakeCollection("Parent")
        parent_of = {id(child): [id(parent)]}
        by_id = {id(child): child, id(parent): parent}
        name_by_id = {id(child): "Child", id(parent): "Parent"}
        direct, ancestors = _compute_ancestor_closure(
            [child], parent_of, by_id, name_by_id)
        assert direct == ["Child"]
        assert ancestors == ["Parent"]

    def test_closure_never_reads_children(self, monkeypatch):
        child = ExplodingFakeCollection("Child")
        parent = ExplodingFakeCollection("Parent")
        parent_of = {id(child): [id(parent)]}
        by_id = {id(child): child, id(parent): parent}
        name_by_id = {id(child): "Child", id(parent): "Parent"}
        direct, ancestors = _compute_ancestor_closure(
            [child], parent_of, by_id, name_by_id)
        assert ancestors == ["Parent"]


class TestOriginalReadCountGuardsPreserved:
    """Original minimal guards retained."""

    def test_global_not_enabled_no_bpy_read(self, monkeypatch):
        _install_fake_bpy(monkeypatch, [FakeCollection("X")])
        r = _check_collection_rules_global(None)
        assert r is None

    def test_empty_dict_no_bpy_read(self, monkeypatch):
        _install_fake_bpy(monkeypatch, [FakeCollection("X")])
        r = _check_collection_rules_global({})
        assert r["result"] == "NOT_CHECKED"

    def test_per_target_not_configured_no_bpy_read(self, monkeypatch):
        t = _target([])
        r = _check_collection_membership(FakeScene([]), t, _make_root_pass())
        assert r["result"] == "NOT_CHECKED"


# ── ancestor closure helper unit tests ──────────────────────────────────


class TestAncestorHelpers:
    def test_basic_parent_of_build(self, monkeypatch):
        parent = FakeCollection("Parent", children=[])
        child = FakeCollection("Child", children=[])
        parent.children = [child]
        parent_of, coll_by_id = _materialize_collection_ancestor_index(
            [parent, child], {id(parent): "Parent", id(child): "Child"})
        assert id(child) in parent_of
        assert parent_of[id(child)] == [id(parent)]

    def test_multi_parent(self, monkeypatch):
        p1 = FakeCollection("P1", children=[])
        p2 = FakeCollection("P2", children=[])
        child = FakeCollection("Child", children=[])
        p1.children = [child]
        p2.children = [child]
        idx = _materialize_collection_ancestor_index(
            [p1, p2, child],
            {id(p1): "P1", id(p2): "P2", id(child): "Child"},
        )
        parent_of, _ = idx
        assert len(parent_of[id(child)]) == 2

    def test_direct_and_ancestor_names(self, monkeypatch):
        parent = FakeCollection("Parent", children=[])
        child = FakeCollection("Child", children=[])
        parent.children = [child]
        parent_of = {id(child): [id(parent)]}
        by_id = {id(parent): parent, id(child): child}
        name_by_id = {id(parent): "Parent", id(child): "Child"}
        direct, ancestors = _compute_ancestor_closure(
            [child], parent_of, by_id, name_by_id)
        assert direct == ["Child"]
        assert ancestors == ["Parent"]

    def test_cycle_terminates(self, monkeypatch):
        a = FakeCollection("A", children=[])
        b = FakeCollection("B", children=[])
        a.children = [b]
        b.children = [a]
        by_id = {id(a): a, id(b): b}
        name_by_id = {id(a): "A", id(b): "B"}
        # Build parent_of: a->b means b's parent is a
        parent_of, _ = _materialize_collection_ancestor_index(
            [a, b], name_by_id)
        direct, ancestors = _compute_ancestor_closure(
            [a], parent_of, by_id, name_by_id)
        assert direct == ["A"]
        # should terminate without infinite recursion


# ── root resolution ─────────────────────────────────────────────────────


class TestRootResolution:
    def test_unique_match(self, monkeypatch):
        root = FakeObj("my_root", obj_type="MESH")
        scene = FakeScene([root])
        t = _target(["CHR_A"], root_object_name="my_root")
        pr = _make_root_pass()
        obj, err = _resolve_root_for_collection_rules(scene, t, pr)
        assert err is None
        assert obj is root

    def test_no_match_returns_none(self, monkeypatch):
        scene = FakeScene([FakeObj("other")])
        t = _target(["CHR_A"], root_object_name="my_root")
        pr = _make_root_pass()
        obj, err = _resolve_root_for_collection_rules(scene, t, pr)
        assert obj is None

    def test_ambiguous_returns_none(self, monkeypatch):
        r1 = FakeObj("my_root")
        r2 = FakeObj("my_root")
        scene = FakeScene([r1, r2])
        t = _target(["CHR_A"], root_object_name="my_root")
        pr = _make_root_pass()
        obj, err = _resolve_root_for_collection_rules(scene, t, pr)
        assert obj is None
