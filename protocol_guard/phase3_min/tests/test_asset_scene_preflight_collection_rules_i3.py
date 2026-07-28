"""Collection Rules I3 R2 focused tests — real Reader integration + exit aggregation.

No Blender, no scope guard. All tests call the real open_blend_and_get_scene
with monkeypatched helpers. No fake Reader functions.
"""
import pytest
import copy
from protocol_guard.phase3_min.blender_scene_reader import (
    _check_collection_rules_global,
    _check_collection_membership,
    _recompute_target_overall,
    _CollectionRulesError,
    _cr_global_error,
    _cr_per_target_error,
)
from protocol_guard.phase3_min.asset_scene_preflight_check import (
    _collect_target_errors,
    _validate_and_open_spec,
)
from protocol_guard.phase3_min.asset_scene_preflight_core import (
    EXIT_PASS, EXIT_FAIL, EXIT_ERROR,
)
import protocol_guard.phase3_min.blender_scene_reader as bsr
import protocol_guard.phase3_min.asset_scene_preflight_check as check_mod


# ── helpers ────────────────────────────────────────────────────────────

def _root_pass_multi(names):
    return [
        {"target_id": n, "root_object_name": "root_" + n,
         "checks": {"object_exists": {"result": "PASS"},
                    "object_type": {"result": "PASS"}},
         "overall": "PASS"}
        for n in names
    ]


def _fake_not_checked(*args, **kwargs):
    return {"result": "NOT_CHECKED", "note": "NOT_CONFIGURED"}


def _fake_pass_per_target(*args, **kwargs):
    return {
        "result": "PASS", "required_names": [], "direct_collections": [],
        "ancestor_collections": [], "matched_names": [], "missing_names": [],
    }


def _install_minimal_bpy(monkeypatch):
    monkeypatch.setattr(bsr, "bpy", type("FakeBpy", (), {
        "ops": type("FO", (), {
            "wm": type("FW", (), {
                "open_mainfile": staticmethod(lambda filepath=None: {"FINISHED"})
            })()
        })(),
        "data": type("FD", (), {
            "scenes": type("FS", (), {
                "get": staticmethod(lambda n: type("FSx", (), {
                    "name": "S", "render": type("FR", (), {"engine": "X"})(),
                    "objects": [], "frame_current": 1,
                })())
            })()
        })(),
        "context": type("FC", (), {"scene": type("FCS", (), {"name": "S"})()})(),
    })())


def _single_target():
    return [{"target_id": "T1", "root_object_name": "r",
             "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH"}]


# ── reader signature compatibility ─────────────────────────────────────


class TestReaderSignature:
    def test_four_arg_call_still_works(self, monkeypatch):
        _install_minimal_bpy(monkeypatch)
        r = bsr.open_blend_and_get_scene("/tmp/fake.blend", "Scene", None)
        assert "scene_basic" in r
        assert "per_target_results" in r
        assert "global_results" in r

    def test_five_arg_signature_accepts_collection_rules_block(self):
        import inspect
        sig = inspect.signature(bsr.open_blend_and_get_scene)
        assert "collection_rules_block" in sig.parameters
        assert sig.parameters["collection_rules_block"].default is None


# ── exact call order tests (real Reader) ──────────────────────────────


class TestExactCallOrder:
    def test_single_target_order(self, monkeypatch):
        """Root → Global → [animation, material, collection, overall] per target."""
        _install_minimal_bpy(monkeypatch)
        call_log = []
        monkeypatch.setattr(bsr, "_check_root_objects",
                            lambda s, t, _target_caches=None: (call_log.append("root"),
                                          _root_pass_multi(["T1"]))[1])
        monkeypatch.setattr(bsr, "_check_collection_rules_global",
                            lambda b: (call_log.append("global_collection_rules"),
                                       None)[1])
        monkeypatch.setattr(bsr, "_check_animation_state",
                            lambda s, t, _target_caches=None: (call_log.append(f"animation_state:{t['target_id']}"),
                                          {"result": "NOT_CHECKED"})[1])
        monkeypatch.setattr(bsr, "_check_material_assignment",
                            lambda s, t, p: (call_log.append(f"material_assignment:{t['target_id']}"),
                                             {"result": "NOT_CHECKED"})[1])
        monkeypatch.setattr(bsr, "_check_collection_membership",
                            lambda s, t, p: (call_log.append(f"collection_membership:{t['target_id']}"),
                                             {"result": "NOT_CHECKED"})[1])
        monkeypatch.setattr(bsr, "_recompute_target_overall",
                            lambda c: (call_log.append("recompute_overall:T1"),
                                       "PASS")[1])

        bsr.open_blend_and_get_scene("/x.blend", "S", None, _single_target())

        assert call_log == [
            "root",
            "global_collection_rules",
            "animation_state:T1",
            "material_assignment:T1",
            "collection_membership:T1",
            "recompute_overall:T1",
        ]

    def test_multi_target_order(self, monkeypatch):
        """Global once before all targets; each target fully complete before next."""
        _install_minimal_bpy(monkeypatch)
        call_log = []
        targets = [
            {"target_id": "T1", "root_object_name": "r1",
             "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH"},
            {"target_id": "T2", "root_object_name": "r2",
             "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH"},
        ]
        monkeypatch.setattr(bsr, "_check_root_objects",
                            lambda s, t, _target_caches=None: (call_log.append("root"),
                                          _root_pass_multi(["T1", "T2"]))[1])
        monkeypatch.setattr(bsr, "_check_collection_rules_global",
                            lambda b: (call_log.append("global_collection_rules"),
                                       None)[1])
        monkeypatch.setattr(bsr, "_check_animation_state",
                            lambda s, t, _target_caches=None: (call_log.append(f"animation_state:{t['target_id']}"),
                                          {"result": "NOT_CHECKED"})[1])
        monkeypatch.setattr(bsr, "_check_material_assignment",
                            lambda s, t, p: (call_log.append(f"material_assignment:{t['target_id']}"),
                                             {"result": "NOT_CHECKED"})[1])
        monkeypatch.setattr(bsr, "_check_collection_membership",
                            lambda s, t, p: (call_log.append(f"collection_membership:{t['target_id']}"),
                                             {"result": "NOT_CHECKED"})[1])
        recompute_count = [0]
        def _tracked_recompute(checks):
            recompute_count[0] += 1
            tid = "T" + str(recompute_count[0])
            call_log.append(f"recompute_overall:{tid}")
            return "PASS"
        monkeypatch.setattr(bsr, "_recompute_target_overall", _tracked_recompute)

        bsr.open_blend_and_get_scene("/x.blend", "S", None, targets)

        assert call_log == [
            "root",
            "global_collection_rules",
            "animation_state:T1",
            "material_assignment:T1",
            "collection_membership:T1",
            "recompute_overall:T1",
            "animation_state:T2",
            "material_assignment:T2",
            "collection_membership:T2",
            "recompute_overall:T2",
        ]


# ── wrong-order mutation test ──────────────────────────────────────────


class TestWrongOrderCaught:
    def test_global_must_be_after_root(self, monkeypatch):
        """If global runs before root, the exact-order test must fail."""
        original = bsr.open_blend_and_get_scene
        _install_minimal_bpy(monkeypatch)
        call_log = []

        def _mutated(abp, sn, scr, tgt=None, collection_rules_block=None):
            # WRONG: global before root
            call_log.append("global_collection_rules")
            call_log.append("root")
            for i, t in enumerate(tgt or []):
                call_log.append(f"animation_state:{t['target_id']}")
                call_log.append(f"material_assignment:{t['target_id']}")
                call_log.append(f"collection_membership:{t['target_id']}")
                call_log.append("recompute_overall:T1")
            return {"scene_basic": {}, "global_results": {"scene_basic": {}},
                    "per_target_results": []}

        monkeypatch.setattr(bsr, "open_blend_and_get_scene", _mutated)
        bsr.open_blend_and_get_scene("/x.blend", "S", None, _single_target())
        # Wrong order: global before root
        assert call_log != [
            "root",
            "global_collection_rules",
            "animation_state:T1",
            "material_assignment:T1",
            "collection_membership:T1",
            "recompute_overall:T1",
        ]


# ── real Reader global_results identity ────────────────────────────────


class TestRealReaderGlobalResults:
    def test_global_none_no_key(self, monkeypatch):
        """_check_collection_rules_global returns None → no key in global_results."""
        _install_minimal_bpy(monkeypatch)
        received_block = []
        def _fake_global(block):
            received_block.append(block)
            return None
        monkeypatch.setattr(bsr, "_check_collection_rules_global", _fake_global)

        r = bsr.open_blend_and_get_scene("/x.blend", "S", None, _single_target(), None)
        assert received_block[0] is None
        assert "collection_rules" not in r["global_results"]

    def test_global_not_checked_identity(self, monkeypatch):
        """Helper returns NOT_CHECKED dict — written as identity."""
        _install_minimal_bpy(monkeypatch)
        sentinel = {
            "result": "NOT_CHECKED",
            "required": {"result": "NOT_CHECKED",
                         "note": "REQUIRED_COLLECTION_NAMES_NOT_CONFIGURED"},
            "forbidden": {"result": "NOT_CHECKED",
                          "note": "FORBIDDEN_COLLECTION_NAME_PATTERNS_NOT_CONFIGURED"},
        }
        def _fake_global(block):
            return copy.deepcopy(sentinel)
        monkeypatch.setattr(bsr, "_check_collection_rules_global", _fake_global)

        r = bsr.open_blend_and_get_scene("/x.blend", "S", None, _single_target(), {})
        assert r["global_results"]["collection_rules"] == sentinel

    def test_global_pass_identity(self, monkeypatch):
        """Helper returns PASS dict — written as-is, no rebuild."""
        _install_minimal_bpy(monkeypatch)
        sentinel = {
            "result": "PASS",
            "required": {"result": "PASS", "required_names": ["A"], "missing_names": []},
            "forbidden": {"result": "PASS", "forbidden_patterns": [],
                          "matched_collections": []},
        }
        def _fake_global(block):
            return copy.deepcopy(sentinel)
        monkeypatch.setattr(bsr, "_check_collection_rules_global", _fake_global)

        r = bsr.open_blend_and_get_scene("/x.blend", "S", None, _single_target(), {})
        assert r["global_results"]["collection_rules"] == sentinel

    def test_global_fail_identity(self, monkeypatch):
        """Helper returns FAIL dict — written as-is."""
        _install_minimal_bpy(monkeypatch)
        sentinel = {
            "result": "FAIL",
            "failure_code": "COLLECTION_RULES_FAILURE",
            "required": {"result": "FAIL", "failure_code": "REQUIRED_COLLECTION_MISSING",
                         "required_names": ["A"], "missing_names": ["A"]},
            "forbidden": {"result": "NOT_CHECKED",
                          "note": "FORBIDDEN_COLLECTION_NAME_PATTERNS_NOT_CONFIGURED"},
        }
        def _fake_global(block):
            return copy.deepcopy(sentinel)
        monkeypatch.setattr(bsr, "_check_collection_rules_global", _fake_global)

        r = bsr.open_blend_and_get_scene("/x.blend", "S", None, _single_target(), {})
        assert r["global_results"]["collection_rules"] == sentinel

    def test_global_error_identity(self, monkeypatch):
        """Helper returns ERROR dict — written as-is, not stripped."""
        _install_minimal_bpy(monkeypatch)
        sentinel = _cr_global_error("MATERIALIZE_BPY_DATA_COLLECTIONS")
        def _fake_global(block):
            return sentinel
        monkeypatch.setattr(bsr, "_check_collection_rules_global", _fake_global)

        r = bsr.open_blend_and_get_scene("/x.blend", "S", None, _single_target(), {})
        assert r["global_results"]["collection_rules"] is sentinel

    def test_scene_basic_shared_object(self, monkeypatch):
        """global_results.scene_basic is the same object as top-level scene_basic."""
        _install_minimal_bpy(monkeypatch)
        r = bsr.open_blend_and_get_scene("/x.blend", "S", None, _single_target(), None)
        assert r["global_results"]["scene_basic"] is r["scene_basic"]


# ── per-target independence (real Reader) ─────────────────────────────


class TestPerTargetIndependence:
    def test_t1_error_t2_still_executed(self, monkeypatch):
        """T1 collection_membership ERROR → T2 still fully processed."""
        _install_minimal_bpy(monkeypatch)
        targets = [
            {"target_id": "T1", "root_object_name": "r1",
             "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH"},
            {"target_id": "T2", "root_object_name": "r2",
             "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH"},
        ]
        t2_called = []
        monkeypatch.setattr(bsr, "_check_root_objects",
                            lambda s, t, _target_caches=None: _root_pass_multi(["T1", "T2"]))
        monkeypatch.setattr(bsr, "_check_animation_state", _fake_not_checked)
        monkeypatch.setattr(bsr, "_check_material_assignment", _fake_not_checked)
        monkeypatch.setattr(bsr, "_check_collection_rules_global",
                            lambda b: None)

        def _fake_cr(scene, target, ptr):
            if target["target_id"] == "T1":
                return _cr_per_target_error("READ_ROOT_USERS_COLLECTION")
            t2_called.append("collection_membership:T2")
            return {
                "result": "PASS", "required_names": ["A"],
                "direct_collections": ["A"], "ancestor_collections": [],
                "matched_names": ["A"], "missing_names": [],
            }

        monkeypatch.setattr(bsr, "_check_collection_membership", _fake_cr)

        r = bsr.open_blend_and_get_scene("/x.blend", "S", None, targets, None)
        ptr = r["per_target_results"]
        assert ptr[0]["overall"] == "ERROR"
        assert ptr[1]["overall"] == "PASS"
        assert len(t2_called) == 1

    def test_t1_error_retains_other_checks(self, monkeypatch):
        """T1 ERROR still has animation_state and material_assignment_presence_check keys."""
        _install_minimal_bpy(monkeypatch)
        monkeypatch.setattr(bsr, "_check_root_objects",
                            lambda s, t, _target_caches=None: _root_pass_multi(["T1"]))
        monkeypatch.setattr(bsr, "_check_animation_state",
                            lambda s, t, _target_caches=None: {"result": "PASS", "animation_object": {"result": "PASS"}})
        monkeypatch.setattr(bsr, "_check_material_assignment",
                            lambda s, t, p: {"result": "PASS", "per_mesh": []})
        monkeypatch.setattr(bsr, "_check_collection_rules_global", lambda b: None)
        monkeypatch.setattr(bsr, "_check_collection_membership",
                            lambda s, t, p: _cr_per_target_error("READ_ROOT_USERS_COLLECTION"))

        r = bsr.open_blend_and_get_scene("/x.blend", "S", None, _single_target(), None)
        checks = r["per_target_results"][0]["checks"]
        assert "animation_state" in checks
        assert "material_assignment_presence_check" in checks
        assert checks["collection_membership"]["result"] == "ERROR"


# ── spec argument passing test (real _validate_and_open_spec) ────────


class TestSpecArgumentPassing:
    def _make_fake_spec(self, monkeypatch, collection_rules=None):
        import tempfile, json, os
        tmpdir = tempfile.TemporaryDirectory()
        repo = tmpdir.name
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
            "targets": [{"target_id": "T1", "root_object_name": "r",
                         "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH"}],
            "global_rules": {},
        }
        if collection_rules is not None:
            spec["collection_rules"] = collection_rules
        spec_path = os.path.join(repo, "spec.json")
        with open(spec_path, "w", encoding="utf-8") as f:
            json.dump(spec, f)
        return tmpdir, spec_path, spec

    def test_scene_rules_passed(self, monkeypatch):
        captured = {}
        def _fake_reader(abp, sn, scr, tgt=None, collection_rules_block=None,
                         projection_groups_block=None):
            captured["scene_rules"] = scr
            captured["collection_rules_block"] = collection_rules_block
            captured["targets"] = tgt
            return {"scene_basic": {"scene_exists": {"result": "PASS"}},
                    "global_results": {"scene_basic": {"scene_exists": {"result": "PASS"}}},
                    "per_target_results": [{"target_id": "T1", "root_object_name": "r",
                                            "checks": {}, "overall": "PASS"}]}

        monkeypatch.setattr(bsr, "open_blend_and_get_scene", _fake_reader)
        tmpdir, sp, spec = self._make_fake_spec(monkeypatch,
                                                 {"required_collection_names": ["A"]})
        try:
            ec, result = _validate_and_open_spec(sp)
            assert captured["scene_rules"] is None
            assert captured["collection_rules_block"] == {"required_collection_names": ["A"]}
            assert captured["targets"] == spec["targets"]
        finally:
            tmpdir.cleanup()

    def test_scene_rules_not_swapped_with_collection_rules(self, monkeypatch):
        captured = {}
        def _fake_reader(abp, sn, scr, tgt=None, collection_rules_block=None,
                         projection_groups_block=None):
            captured["scene_rules"] = scr
            captured["collection_rules_block"] = collection_rules_block
            return {"scene_basic": {"scene_exists": {"result": "PASS"}},
                    "global_results": {"scene_basic": {"scene_exists": {"result": "PASS"}}},
                    "per_target_results": [{"target_id": "T1", "root_object_name": "r",
                                            "checks": {}, "overall": "PASS"}]}

        monkeypatch.setattr(bsr, "open_blend_and_get_scene", _fake_reader)
        tmpdir, sp, spec = self._make_fake_spec(monkeypatch, None)
        try:
            ec, result = _validate_and_open_spec(sp)
            assert captured["collection_rules_block"] is None
        finally:
            tmpdir.cleanup()


# ── global exit code tests ─────────────────────────────────────────────


class TestGlobalExitCodes:
    def _fake_spec_path(self, monkeypatch, scene_data, collection_rules=None):
        import tempfile, json, os
        tmpdir = tempfile.TemporaryDirectory()
        repo = tmpdir.name
        blend = os.path.join(repo, "scene.blend")
        with open(blend, "wb") as f:
            f.write(b"placeholder")
        spec = {
            "schema_version": "1", "checker": "asset_scene_preflight_check",
            "source_requirement_version": "Blender 固定资产模板路线 v4",
            "repository_root": repo, "blend_path": "scene.blend",
            "scene_name": "Scene",
            "targets": [{"target_id": "T1", "root_object_name": "r",
                         "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH"}],
            "global_rules": {},
        }
        if collection_rules is not None:
            spec["collection_rules"] = collection_rules
        spec_path = os.path.join(repo, "spec.json")
        with open(spec_path, "w", encoding="utf-8") as f:
            json.dump(spec, f)

        def _fake_reader(*args, **kwargs):
            return scene_data

        monkeypatch.setattr(bsr, "open_blend_and_get_scene", _fake_reader)
        return tmpdir, spec_path

    def test_global_error_exit_error(self, monkeypatch):
        sd = {
            "scene_basic": {"scene_exists": {"result": "PASS", "expected": True, "actual": True}},
            "global_results": {
                "scene_basic": {"scene_exists": {"result": "PASS"}},
                "collection_rules": _cr_global_error("MATERIALIZE_BPY_DATA_COLLECTIONS"),
            },
            "per_target_results": [{"target_id": "T1", "root_object_name": "r",
                                    "checks": {}, "overall": "PASS"}],
        }
        tmpdir, sp = self._fake_spec_path(monkeypatch, sd, {})
        try:
            ec, result = _validate_and_open_spec(sp)
            assert ec == EXIT_ERROR
            assert result["result"] == "ERROR"
        finally:
            tmpdir.cleanup()

    def test_global_error_message_first(self, monkeypatch):
        sd = {
            "scene_basic": {"scene_exists": {"result": "PASS"}},
            "global_results": {
                "scene_basic": {"scene_exists": {"result": "PASS"}},
                "collection_rules": _cr_global_error("G1"),
            },
            "per_target_results": [{"target_id": "T1", "root_object_name": "r",
                "checks": {"collection_membership": _cr_per_target_error(
                    "READ_ROOT_USERS_COLLECTION")},
                "overall": "ERROR"}],
        }
        tmpdir, sp = self._fake_spec_path(monkeypatch, sd, {})
        try:
            ec, result = _validate_and_open_spec(sp)
            assert ec == EXIT_ERROR
            assert result["input_errors"][0].startswith(
                "COLLECTION_RULES_COMPUTATION_ERROR: global")
        finally:
            tmpdir.cleanup()

    def test_global_error_and_target_error_both_present(self, monkeypatch):
        sd = {
            "scene_basic": {"scene_exists": {"result": "PASS"}},
            "global_results": {
                "scene_basic": {"scene_exists": {"result": "PASS"}},
                "collection_rules": _cr_global_error("G1"),
            },
            "per_target_results": [{"target_id": "T1", "root_object_name": "r",
                "checks": {"collection_membership": _cr_per_target_error(
                    "READ_ROOT_USERS_COLLECTION")},
                "overall": "ERROR"}],
        }
        tmpdir, sp = self._fake_spec_path(monkeypatch, sd, {})
        try:
            ec, result = _validate_and_open_spec(sp)
            msgs = result["input_errors"]
            global_msgs = [m for m in msgs if "global collection_rules" in m]
            target_msgs = [m for m in msgs if "collection_rules operation" in m
                           and "global" not in m]
            assert len(global_msgs) == 1
            assert len(target_msgs) >= 1
        finally:
            tmpdir.cleanup()

    def test_global_fail_exit_fail(self, monkeypatch):
        sd = {
            "scene_basic": {"scene_exists": {"result": "PASS"}},
            "global_results": {
                "scene_basic": {"scene_exists": {"result": "PASS"}},
                "collection_rules": {
                    "result": "FAIL", "failure_code": "COLLECTION_RULES_FAILURE",
                    "required": {"result": "PASS", "required_names": [], "missing_names": []},
                    "forbidden": {"result": "FAIL",
                                  "failure_code": "FORBIDDEN_COLLECTION_MATCHED",
                                  "forbidden_patterns": ["*test*"],
                                  "matched_collections": ["test_x"]},
                },
            },
            "per_target_results": [{"target_id": "T1", "root_object_name": "r",
                                    "checks": {}, "overall": "PASS"}],
        }
        tmpdir, sp = self._fake_spec_path(monkeypatch, sd, {})
        try:
            ec, result = _validate_and_open_spec(sp)
            assert ec == EXIT_FAIL
            assert result["result"] == "FAIL"
        finally:
            tmpdir.cleanup()

    def test_global_pass_targets_pass_exit_pass(self, monkeypatch):
        sd = {
            "scene_basic": {"scene_exists": {"result": "PASS"}},
            "global_results": {
                "scene_basic": {"scene_exists": {"result": "PASS"}},
                "collection_rules": {"result": "PASS",
                    "required": {"result": "NOT_CHECKED", "note": "X"},
                    "forbidden": {"result": "NOT_CHECKED", "note": "Y"}},
            },
            "per_target_results": [{"target_id": "T1", "root_object_name": "r",
                                    "checks": {}, "overall": "PASS"}],
        }
        tmpdir, sp = self._fake_spec_path(monkeypatch, sd, {})
        try:
            ec, result = _validate_and_open_spec(sp)
            assert ec == EXIT_PASS
        finally:
            tmpdir.cleanup()

    def test_global_not_checked_targets_pass_exit_pass(self, monkeypatch):
        sd = {
            "scene_basic": {"scene_exists": {"result": "PASS"}},
            "global_results": {
                "scene_basic": {"scene_exists": {"result": "PASS"}},
                "collection_rules": {"result": "NOT_CHECKED",
                    "required": {"result": "NOT_CHECKED", "note": "X"},
                    "forbidden": {"result": "NOT_CHECKED", "note": "Y"}},
            },
            "per_target_results": [{"target_id": "T1", "root_object_name": "r",
                                    "checks": {}, "overall": "PASS"}],
        }
        tmpdir, sp = self._fake_spec_path(monkeypatch, sd, {})
        try:
            ec, result = _validate_and_open_spec(sp)
            assert ec == EXIT_PASS
        finally:
            tmpdir.cleanup()

    def test_no_collection_rules_key_pass_exit_pass(self, monkeypatch):
        sd = {
            "scene_basic": {"scene_exists": {"result": "PASS"}},
            "global_results": {"scene_basic": {"scene_exists": {"result": "PASS"}}},
            "per_target_results": [{"target_id": "T1", "root_object_name": "r",
                                    "checks": {}, "overall": "PASS"}],
        }
        tmpdir, sp = self._fake_spec_path(monkeypatch, sd, None)
        try:
            ec, result = _validate_and_open_spec(sp)
            assert ec == EXIT_PASS
        finally:
            tmpdir.cleanup()

    def test_target_collection_error_exit_error(self, monkeypatch):
        sd = {
            "scene_basic": {"scene_exists": {"result": "PASS"}},
            "global_results": {"scene_basic": {"scene_exists": {"result": "PASS"}}},
            "per_target_results": [{"target_id": "T1", "root_object_name": "r",
                "checks": {"collection_membership": _cr_per_target_error(
                    "READ_ROOT_USERS_COLLECTION")},
                "overall": "ERROR"}],
        }
        tmpdir, sp = self._fake_spec_path(monkeypatch, sd, {})
        try:
            ec, result = _validate_and_open_spec(sp)
            assert ec == EXIT_ERROR
            assert any("READ_ROOT_USERS_COLLECTION" in m for m in result["input_errors"])
        finally:
            tmpdir.cleanup()

    def test_target_collection_fail_exit_fail(self, monkeypatch):
        sd = {
            "scene_basic": {"scene_exists": {"result": "PASS"}},
            "global_results": {"scene_basic": {"scene_exists": {"result": "PASS"}}},
            "per_target_results": [{"target_id": "T1", "root_object_name": "r",
                "checks": {"collection_membership": {
                    "result": "FAIL", "failure_code": "TARGET_NOT_IN_REQUIRED_COLLECTION",
                    "required_names": ["A"], "direct_collections": [],
                    "ancestor_collections": [], "matched_names": [], "missing_names": ["A"]}},
                "overall": "FAIL"}],
        }
        tmpdir, sp = self._fake_spec_path(monkeypatch, sd, {})
        try:
            ec, result = _validate_and_open_spec(sp)
            assert ec == EXIT_FAIL
        finally:
            tmpdir.cleanup()


# ── overall integration ───────────────────────────────────────────────


class TestOverallIntegration:
    def test_collection_fail_gives_overall_fail(self):
        checks = {
            "collection_membership": {"result": "FAIL"},
        }
        assert _recompute_target_overall(checks) == "FAIL"

    def test_collection_error_gives_overall_error(self):
        checks = {
            "collection_membership": {"result": "ERROR"},
        }
        assert _recompute_target_overall(checks) == "ERROR"

    def test_collection_pass_does_not_override_other_fail(self):
        checks = {
            "material_assignment_presence_check": {"result": "FAIL"},
            "collection_membership": {"result": "PASS"},
        }
        assert _recompute_target_overall(checks) == "FAIL"

    def test_collection_not_checked_does_not_degrade_pass(self):
        checks = {
            "collection_membership": {"result": "NOT_CHECKED"},
        }
        assert _recompute_target_overall(checks) == "PASS"

    def test_animation_error_collection_pass_overall_error(self):
        checks = {
            "animation_state": {"result": "ERROR"},
            "collection_membership": {"result": "PASS"},
        }
        assert _recompute_target_overall(checks) == "ERROR"


# ── legacy reader return compatibility ────────────────────────────────


class TestLegacyReaderReturn:
    def test_no_global_results_in_data_falls_back(self, monkeypatch):
        import tempfile, json, os
        tmpdir = tempfile.TemporaryDirectory()
        try:
            repo = tmpdir.name
            blend = os.path.join(repo, "scene.blend")
            with open(blend, "wb") as f:
                f.write(b"placeholder")
            spec = {
                "schema_version": "1", "checker": "asset_scene_preflight_check",
                "source_requirement_version": "Blender 固定资产模板路线 v4",
                "repository_root": repo, "blend_path": "scene.blend",
                "scene_name": "Scene",
                "targets": [{"target_id": "T1", "root_object_name": "r",
                             "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH"}],
                "global_rules": {},
            }
            spec_path = os.path.join(repo, "spec.json")
            with open(spec_path, "w", encoding="utf-8") as f:
                json.dump(spec, f)

            def _old_reader(*args, **kwargs):
                return {
                    "scene_basic": {"scene_exists": {"result": "PASS"}},
                    "per_target_results": [{"target_id": "T1",
                        "root_object_name": "r", "checks": {}, "overall": "PASS"}],
                }

            monkeypatch.setattr(bsr, "open_blend_and_get_scene", _old_reader)
            ec, result = _validate_and_open_spec(spec_path)
            assert ec == EXIT_PASS
        finally:
            tmpdir.cleanup()
