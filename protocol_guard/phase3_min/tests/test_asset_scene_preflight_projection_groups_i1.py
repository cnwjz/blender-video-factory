"""Projection Groups I1 focused tests — pre-open, framework, entry integration.

All tests use monkeypatch, no Blender.
"""
import ast, os, sys, pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

_MISSING = object()


# ── helpers ──

def _spec(**kw):
    s = {
        "blend_path": "dummy.blend",
        "scene_name": "Scene",
        "repository_root": PROJECT_ROOT,
        "targets": [
            {"target_id": "CHR_TEST", "root_object_name": "root",
             "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH"}
        ],
    }
    s.update(kw)
    return s


def _pg(group_id="g", target_ids=None, additional_object_names=None,
        camera_object_name="C", mvc=4,
        min_left=0.0, max_right=1.0, min_bottom=0.0, max_top=1.0,
        require_camera_outside_world_bbox=False):
    if target_ids is None:
        target_ids = ["CHR_TEST"]
    if additional_object_names is None:
        additional_object_names = []
    return {
        "group_id": group_id,
        "target_ids": target_ids,
        "additional_object_names": additional_object_names,
        "camera_object_name": camera_object_name,
        "minimum_visible_projected_corner_count": mvc,
        "required_screen_bbox": {
            "min_left": min_left, "max_right": max_right,
            "min_bottom": min_bottom, "max_top": max_top,
        },
        "require_camera_outside_world_bbox": require_camera_outside_world_bbox,
    }


def _pg_pass(group_id="g"):
    return {
        "result": "PASS", "group_id": group_id,
        "target_ids": ["CHR_TEST"],
        "camera_object_name": "C",
        "evaluated_mesh_names": [], "surviving_corners": 8,
        "screen_bbox": {"min_x": 0.1, "max_x": 0.9, "min_y": 0.1, "max_y": 0.9},
        "required_screen_bbox": {"min_left": 0.0, "max_right": 1.0,
                                 "min_bottom": 0.0, "max_top": 1.0},
        "minimum_visible_projected_corner_count": 4,
        "camera_world_location": [0.0, 0.0, 10.0],
        "require_camera_outside_world_bbox": False,
        "union_bbox": None,
        "per_source_summary": {},
        "failed_checks": None, "actual_type": None, "failure_code": None,
    }


def _pg_fail(group_id="g", failure_code="CAMERA_OBJECT_NOT_FOUND"):
    r = _pg_pass(group_id)
    r["result"] = "FAIL"
    r["failure_code"] = failure_code
    return r


def _pg_error(group_id="g", operation="GET_EVALUATED_DEPSGRAPH"):
    return {
        "result": "ERROR", "group_id": group_id, "target_ids": ["CHR_TEST"],
        "error_type": "PROJECTION_GROUP_COMPUTATION_ERROR",
        "operation": operation,
        "note": operation + "_FAILED",
    }


# ════════════════ Pre-open validation ════════════════

class TestPreOpenValidation:
    def test_mvc_gt_8_rejected(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _validate_projection_groups_rules_preopen)
        s = _spec(projection_groups=[_pg(mvc=12)])
        errs = _validate_projection_groups_rules_preopen(s)
        assert any("must be <= 8" in e for e in errs)

    def test_mvc_8_allowed(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _validate_projection_groups_rules_preopen)
        s = _spec(projection_groups=[_pg(mvc=8)])
        errs = _validate_projection_groups_rules_preopen(s)
        assert all("must be <= 8" not in e for e in errs)

    def test_mvc_0_allowed(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _validate_projection_groups_rules_preopen)
        s = _spec(projection_groups=[_pg(mvc=0)])
        errs = _validate_projection_groups_rules_preopen(s)
        assert _validate_projection_groups_rules_preopen(s) == []

    def test_bbox_min_left_out_of_range(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _validate_projection_groups_rules_preopen)
        s = _spec(projection_groups=[_pg(min_left=-0.5)])
        errs = _validate_projection_groups_rules_preopen(s)
        assert any("min_left" in e and "out of [0,1]" in e for e in errs)

    def test_bbox_max_right_out_of_range(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _validate_projection_groups_rules_preopen)
        s = _spec(projection_groups=[_pg(max_right=1.5)])
        errs = _validate_projection_groups_rules_preopen(s)
        assert any("max_right" in e and "out of [0,1]" in e for e in errs)

    def test_bbox_min_bottom_out_of_range(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _validate_projection_groups_rules_preopen)
        s = _spec(projection_groups=[_pg(min_bottom=-0.1)])
        errs = _validate_projection_groups_rules_preopen(s)
        assert any("min_bottom" in e and "out of [0,1]" in e for e in errs)

    def test_bbox_max_top_out_of_range(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _validate_projection_groups_rules_preopen)
        s = _spec(projection_groups=[_pg(max_top=1.2)])
        errs = _validate_projection_groups_rules_preopen(s)
        assert any("max_top" in e and "out of [0,1]" in e for e in errs)

    def test_additional_object_empty_string(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _validate_projection_groups_rules_preopen)
        s = _spec(projection_groups=[_pg(additional_object_names=["", "valid"])])
        errs = _validate_projection_groups_rules_preopen(s)
        assert any("must be a non-empty string" in e for e in errs)

    def test_duplicate_target_id(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _validate_projection_groups_rules_preopen)
        s = _spec(projection_groups=[_pg(target_ids=["CHR_TEST", "CHR_TEST"])])
        errs = _validate_projection_groups_rules_preopen(s)
        assert any("duplicate target_id" in e for e in errs)

    def test_duplicate_additional_object_name(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _validate_projection_groups_rules_preopen)
        s = _spec(projection_groups=[_pg(
            additional_object_names=["A", "A"])])
        errs = _validate_projection_groups_rules_preopen(s)
        assert any("duplicate object name" in e for e in errs)

    def test_both_empty(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _validate_projection_groups_rules_preopen)
        s = _spec(projection_groups=[_pg(target_ids=[],
                   additional_object_names=[])])
        errs = _validate_projection_groups_rules_preopen(s)
        assert any("both target_ids and additional_object_names are empty" in e for e in errs)

    def test_all_valid(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _validate_projection_groups_rules_preopen)
        s = _spec(projection_groups=[_pg()])
        errs = _validate_projection_groups_rules_preopen(s)
        assert errs == []

    def test_null_projection_groups(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _validate_projection_groups_rules_preopen)
        s = _spec(projection_groups=None)
        errs = _validate_projection_groups_rules_preopen(s)
        assert errs == []

    def test_missing_projection_groups_key(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _validate_projection_groups_rules_preopen)
        s = _spec()
        s.pop("projection_groups", None)
        errs = _validate_projection_groups_rules_preopen(s)
        assert errs == []

    def test_errors_sorted(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _validate_projection_groups_rules_preopen)
        s = _spec(projection_groups=[
            _pg(group_id="g", mvc=12, min_left=-1.0, max_right=2.0)])
        errs = _validate_projection_groups_rules_preopen(s)
        assert errs == sorted(errs, key=lambda e: (e.casefold(), e))


# ════════════════ Projection Group Overall ════════════════

class TestProjectionGroupOverall:
    def test_empty_returns_pass(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _compute_projection_group_overall)
        assert _compute_projection_group_overall([]) == "PASS"

    def test_all_pass(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _compute_projection_group_overall)
        pg = [_pg_pass("g1"), _pg_pass("g2")]
        assert _compute_projection_group_overall(pg) == "PASS"

    def test_any_fail_no_error(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _compute_projection_group_overall)
        pg = [_pg_pass("g1"), _pg_fail("g2")]
        assert _compute_projection_group_overall(pg) == "FAIL"

    def test_any_error(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _compute_projection_group_overall)
        pg = [_pg_pass("g1"), _pg_error("g2")]
        assert _compute_projection_group_overall(pg) == "ERROR"

    def test_error_over_fail(self):
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _compute_projection_group_overall)
        pg = [_pg_fail("g1"), _pg_error("g2")]
        assert _compute_projection_group_overall(pg) == "ERROR"


# ════════════════ Result builders ════════════════

class TestResultBuilders:
    def test_build_pass_includes_projection_groups(self):
        from protocol_guard.phase3_min.asset_scene_preflight_core import (
            build_pass_result)
        pg = [_pg_pass()]
        r = build_pass_result({}, "", projection_groups=pg)
        assert r["projection_group_results"] == pg
        assert r["result"] == "PASS"

    def test_build_pass_projection_groups_none_default(self):
        from protocol_guard.phase3_min.asset_scene_preflight_core import (
            build_pass_result)
        r = build_pass_result({}, "")
        assert r["projection_group_results"] == []

    def test_build_fail_includes_projection_groups(self):
        from protocol_guard.phase3_min.asset_scene_preflight_core import (
            build_fail_result)
        pg = [_pg_fail()]
        r = build_fail_result({}, "", projection_groups=pg)
        assert r["projection_group_results"] == pg
        assert r["result"] == "FAIL"

    def test_build_error_with_projection_groups(self):
        from protocol_guard.phase3_min.asset_scene_preflight_core import (
            build_error_result)
        pg = [_pg_error()]
        r = build_error_result({}, "", ["some error"], projection_groups=pg)
        assert r["projection_group_results"] == pg
        assert r["result"] == "ERROR"
        assert "some error" in r["input_errors"]

    def test_build_error_without_projection_groups(self):
        from protocol_guard.phase3_min.asset_scene_preflight_core import (
            build_error_result)
        r = build_error_result({}, "", ["pre-open error"])
        assert r["projection_group_results"] == []
        assert r["result"] == "ERROR"

    def test_build_error_no_input_errors(self):
        from protocol_guard.phase3_min.asset_scene_preflight_core import (
            build_error_result)
        r = build_error_result({}, "", [])
        assert r["input_errors"] == []
        assert r["result"] == "ERROR"


# ════════════════ Entry integration ════════════════

class TestEntryIntegration:
    """Integration tests through _validate_and_open_spec entry path."""

    @pytest.fixture(autouse=True)
    def _patch_env(self, monkeypatch):
        import protocol_guard.phase3_min.asset_scene_preflight_check as check
        import protocol_guard.phase3_min.asset_scene_preflight_core as core
        import json

        # Patch validate_spec_paths to avoid real filesystem dependency
        def fake_validate_spec_paths(repo_root, blend_path):
            return ("/fake/abs/path.blend", None)

        monkeypatch.setattr(core, "validate_spec_paths", fake_validate_spec_paths)

        # Patch file loading to read the actual spec from tmp_path
        real_load = core.load_spec_bytes

        def fake_load(path):
            # Actually read the spec file so _validate_and_open_spec gets real content
            with open(path, 'rb') as f:
                raw = f.read()
            return (raw, None)

        monkeypatch.setattr(core, "load_spec_bytes", fake_load)

        # Keep parse_spec_json real — it parses the actual spec content
        monkeypatch.setattr(core, "validate_spec", lambda spec: [])
        monkeypatch.setattr("protocol_guard.phase2_min.io_utils.sha256_file",
                            lambda path: "abc123")

    def _setup_reader(self, monkeypatch, pg_results=None, scene_error=None,
                      per_target_results=None):
        import protocol_guard.phase3_min.blender_scene_reader as reader

        if per_target_results is None:
            per_target_results = [{
                "target_id": "CHR_TEST",
                "root_object_name": "root",
                "overall": "PASS",
                "checks": {
                    "object_exists": {"result": "PASS"},
                    "object_type": {"result": "PASS", "actual": "EMPTY"},
                },
            }]

        scene_basic = {"scene_exists": {"result": "PASS", "expected": True, "actual": True}}

        def fake_open(absolute_blend_path, scene_name, spec_scene_rules,
                      targets=None, collection_rules_block=None,
                      projection_groups_block=None):
            r = {"scene_basic": scene_basic, "global_results": {"scene_basic": scene_basic},
                 "per_target_results": per_target_results,
                 "projection_group_results": pg_results or []}
            if scene_error:
                r["error"] = scene_error["error"]
                r["error_type"] = scene_error.get("error_type", "OPEN_ERROR")
            return r

        monkeypatch.setattr(reader, "open_blend_and_get_scene", fake_open)

        # Patch pre-open validators to return empty
        monkeypatch.setattr(
            "protocol_guard.phase3_min.asset_scene_preflight_check"
            "._validate_direct_child_rules_preopen",
            lambda targets: [])
        monkeypatch.setattr(
            "protocol_guard.phase3_min.asset_scene_preflight_check"
            "._validate_standing_up_axis_rules_preopen",
            lambda targets: [])
        monkeypatch.setattr(
            "protocol_guard.phase3_min.asset_scene_preflight_check"
            "._validate_facing_forward_axis_rules_preopen",
            lambda targets: [])
        monkeypatch.setattr(
            "protocol_guard.phase3_min.asset_scene_preflight_check"
            "._validate_rotation_rules_preopen",
            lambda targets: [])
        monkeypatch.setattr(
            "protocol_guard.phase3_min.asset_scene_preflight_check"
            "._validate_ground_contact_rules_preopen",
            lambda targets: [])
        monkeypatch.setattr(
            "protocol_guard.phase3_min.asset_scene_preflight_check"
            "._validate_camera_check_rules_preopen",
            lambda targets: [])
        monkeypatch.setattr(
            "protocol_guard.phase3_min.asset_scene_preflight_check"
            "._validate_projection_groups_rules_preopen",
            lambda spec: [])

    def _write_spec(self, tmp_path, spec_dict):
        import json
        p = tmp_path / "spec.json"
        p.write_text(json.dumps(spec_dict), encoding="utf-8")
        return str(p)

    # ── enable/disable ──

    def test_null_projection_groups_empty_list(self, monkeypatch, tmp_path):
        self._setup_reader(monkeypatch)
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _validate_and_open_spec)
        sp = self._write_spec(tmp_path, _spec(projection_groups=None))
        exit_code, result = _validate_and_open_spec(sp)
        assert result["projection_group_results"] == []
        assert exit_code == 0

    def test_empty_array_projection_groups_empty_list(self, monkeypatch, tmp_path):
        self._setup_reader(monkeypatch)
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _validate_and_open_spec)
        sp = self._write_spec(tmp_path, _spec(projection_groups=[]))
        exit_code, result = _validate_and_open_spec(sp)
        assert result["projection_group_results"] == []
        assert exit_code == 0

    # ── projection_group_overall PASS ──

    def test_all_pass_overall_pass(self, monkeypatch, tmp_path):
        self._setup_reader(monkeypatch, pg_results=[_pg_pass()])
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _validate_and_open_spec)
        sp = self._write_spec(tmp_path, _spec(projection_groups=[_pg()]))
        exit_code, result = _validate_and_open_spec(sp)
        assert result["projection_group_results"][0]["result"] == "PASS"
        assert result["result"] == "PASS"
        assert exit_code == 0

    # ── projection_group_overall FAIL ──

    def test_fail_overall_fail(self, monkeypatch, tmp_path):
        self._setup_reader(monkeypatch, pg_results=[_pg_fail()])
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _validate_and_open_spec)
        sp = self._write_spec(tmp_path, _spec(projection_groups=[_pg()]))
        exit_code, result = _validate_and_open_spec(sp)
        assert result["projection_group_results"][0]["result"] == "FAIL"
        assert result["result"] == "FAIL"
        assert exit_code == 1

    # ── projection_group_overall ERROR ──

    def test_error_overall_error(self, monkeypatch, tmp_path):
        self._setup_reader(monkeypatch, pg_results=[_pg_error()])
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _validate_and_open_spec)
        sp = self._write_spec(tmp_path, _spec(projection_groups=[_pg()]))
        exit_code, result = _validate_and_open_spec(sp)
        assert result["projection_group_results"][0]["result"] == "ERROR"
        assert result["result"] == "ERROR"
        assert exit_code == 2

    def test_error_preserves_group_details(self, monkeypatch, tmp_path):
        self._setup_reader(monkeypatch, pg_results=[_pg_error(group_id="g1",
                           operation="TO_MESH_CLEAR")])
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _validate_and_open_spec)
        sp = self._write_spec(tmp_path, _spec(projection_groups=[_pg(group_id="g1")]))
        exit_code, result = _validate_and_open_spec(sp)
        pg0 = result["projection_group_results"][0]
        assert pg0["result"] == "ERROR"
        assert pg0["group_id"] == "g1"
        assert pg0["operation"] == "TO_MESH_CLEAR"
        assert pg0["error_type"] == "PROJECTION_GROUP_COMPUTATION_ERROR"
        assert any("TO_MESH_CLEAR" in e for e in result["input_errors"])

    def test_error_with_multiple_groups(self, monkeypatch, tmp_path):
        self._setup_reader(monkeypatch, pg_results=[
            _pg_pass("g1"), _pg_error("g2"), _pg_fail("g3")])
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _validate_and_open_spec)
        sp = self._write_spec(tmp_path, _spec(projection_groups=[
            _pg(group_id="g1"), _pg(group_id="g2"), _pg(group_id="g3")]))
        exit_code, result = _validate_and_open_spec(sp)
        assert result["result"] == "ERROR"
        assert len(result["projection_group_results"]) == 3

    # ── pre-open ERROR blocks ──

    def test_pre_open_error_blocks_reader(self, monkeypatch, tmp_path):
        # self._setup_reader patches all pre-open validators to return []
        # We must override ONLY this one AFTER _setup_reader
        self._setup_reader(monkeypatch)
        import protocol_guard.phase3_min.asset_scene_preflight_check as check
        monkeypatch.setattr(check, "_validate_projection_groups_rules_preopen",
                            lambda spec: ["PG_RULE_ERROR"])
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _validate_and_open_spec)
        sp = self._write_spec(tmp_path, _spec(projection_groups=[_pg(mvc=12)]))
        exit_code, result = _validate_and_open_spec(sp)
        assert exit_code == 2
        assert result["result"] == "ERROR"
        assert "PG_RULE_ERROR" in result["input_errors"]
        # pre-open error: projection_group_results stays as []
        assert result["projection_group_results"] == []

    # ── projection_groups_block passed ──

    def test_projection_groups_block_passed_to_reader(self, monkeypatch, tmp_path):
        self._setup_reader(monkeypatch)
        passed = []
        import protocol_guard.phase3_min.blender_scene_reader as reader
        orig = reader.open_blend_and_get_scene

        def capture(absolute_blend_path, scene_name, spec_scene_rules,
                    targets=None, collection_rules_block=None,
                    projection_groups_block=None):
            passed.append(projection_groups_block)
            return orig(absolute_blend_path, scene_name, spec_scene_rules,
                       targets=targets, collection_rules_block=collection_rules_block,
                       projection_groups_block=projection_groups_block)

        monkeypatch.setattr(reader, "open_blend_and_get_scene", capture)
        from protocol_guard.phase3_min.asset_scene_preflight_check import (
            _validate_and_open_spec)
        pg_spec = [_pg(group_id="g1")]
        sp = self._write_spec(tmp_path, _spec(projection_groups=pg_spec))
        _validate_and_open_spec(sp)
        assert len(passed) > 0
        assert passed[0] == pg_spec


# ════════════════ Result dict key sets ════════════════

class TestResultDictKeys:
    def test_pass_16_keys(self):
        r = _pg_pass()
        assert len(r) == 16
        assert r["result"] == "PASS"
        assert r["failure_code"] is None
        assert r["failed_checks"] is None
        assert r["actual_type"] is None
        assert "target_ids" in r

    def test_fail_16_keys(self):
        r = _pg_fail()
        assert len(r) == 16
        assert r["result"] == "FAIL"
        assert r["failure_code"] is not None
        assert "target_ids" in r
        assert "require_camera_outside_world_bbox" in r

    def test_error_6_keys(self):
        r = _pg_error()
        assert len(r) == 6
        assert r["result"] == "ERROR"
        assert r["error_type"] == "PROJECTION_GROUP_COMPUTATION_ERROR"
        assert "operation" in r
        assert "note" in r
        assert "group_id" in r
        assert "target_ids" in r

    def test_fail_all_required_keys_present(self):
        required_keys = {
            "result", "group_id", "target_ids", "camera_object_name",
            "evaluated_mesh_names", "surviving_corners", "screen_bbox",
            "required_screen_bbox", "minimum_visible_projected_corner_count",
            "camera_world_location", "require_camera_outside_world_bbox",
            "union_bbox", "per_source_summary", "failed_checks",
            "actual_type", "failure_code",
        }
        r = _pg_fail()
        assert set(r.keys()) == required_keys

    def test_fail_require_camera_outside_always_present(self):
        r = _pg_fail(failure_code="NO_EVALUATED_GEOMETRY")
        assert "require_camera_outside_world_bbox" in r


# ════════════════ Stub behavior ════════════════

class TestRuntimeEntryGuard:
    def test_null_block_returns_empty(self):
        from protocol_guard.phase3_min.blender_scene_reader import (
            _check_projection_groups)
        r = _check_projection_groups(None, None, [])
        assert r == []

    def test_empty_array_returns_empty(self):
        from protocol_guard.phase3_min.blender_scene_reader import (
            _check_projection_groups)
        r = _check_projection_groups(None, [], [])
        assert r == []

    def test_non_list_returns_empty(self):
        from protocol_guard.phase3_min.blender_scene_reader import (
            _check_projection_groups)
        r = _check_projection_groups(None, "not_a_list", [])
        assert r == []
