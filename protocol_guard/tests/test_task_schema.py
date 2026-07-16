"""Test task card schema validation v2 + v1.2 integrity checks."""

import pytest
from protocol_guard.task_schema import validate_task_card


def _valid_task():
    return {
        "task_id": "TEST_001",
        "task_card_version": 2,
        "protocol_version": "v1.0",
        "execution_mode": "confirm_then_execute",
        "task_type": "AUDIT",
        "project_state_file": "PROJECT_STATE.yaml",
        "input_files": ["scene/test.blend"],
        "output_files": ["scene/test_out.blend", "reports/report.md"],
        "primary_goal": "Verify framing feasibility",
        "primary_variable": "camera_distance_m",

        "dependent_variables": [
            {
                "name": "camera_shift_y",
                "solver": "analytical_bbox_centering",
                "minimum": -1.0,
                "maximum": 1.0,
                "unit": "normalized_camera_shift",
            }
        ],

        "fixed_params": {
            "lens_mm": 24,
            "sensor_fit": "HORIZONTAL",
            "elevation_deg": 25,
        },

        "locked_items": [
            {
                "lock_id": "character_roots",
                "resource_type": "blender_collection",
                "selector": "CHR_*",
                "protected_fields": ["location", "rotation_euler", "scale", "hierarchy"],
            }
        ],

        "allowed_modifications": [
            {"target": "Camera", "fields": ["location"]}
        ],

        "forbidden_modifications": [
            {"target": "CHR_*", "fields": ["location", "rotation_euler", "scale"]}
        ],

        "preflight_checks": [
            {"check_id": "input_scene_exists", "checker": "file_exists", "required": True}
        ],

        "technical_pass_conditions": [
            {"condition_id": "no_clipping", "metric": "clipped_count", "operator": "eq", "expected": 0, "required": True},
            {"condition_id": "content_h", "metric": "proj_h_pct", "operator": "between", "expected": [56, 61], "required": True},
        ],

        "visual_intent": "Camera shows checkout counters clearly",
        "visual_forbidden": "No character clipping",

        "evidence_required": [
            {"evidence_id": "clean", "role": "clean_preview", "path": "clean.png", "required": True},
        ],

        "upload_dir": "reviews/UPLOAD_NEXT",
        "upload_files": ["clean.png", "debug.png", "report.md"],

        "stop_conditions": [
            {"condition": "sha256_mismatch", "action": "stop_before_execution"},
        ],

        "state_patch_requested": {
            "fields": {"scene_phase": "done"},
            "reason": "Complete",
        },
    }


class TestTaskCardValidationV2:
    # ── Basic structural validation ──
    def test_valid_task_passes(self):
        ok, errs = validate_task_card(_valid_task())
        assert ok, f"Expected valid but got errors: {errs}"

    def test_missing_required_field_fails(self):
        task = _valid_task()
        del task["task_id"]
        ok, errs = validate_task_card(task)
        assert not ok

    def test_invalid_execution_mode_fails(self):
        task = _valid_task()
        task["execution_mode"] = "bypass_everything"
        ok, errs = validate_task_card(task)
        assert not ok

    # ── primary_variable constraints ──
    def test_primary_variable_not_single_string_fails(self):
        task = _valid_task()
        task["primary_variable"] = ["lens", "distance"]
        ok, errs = validate_task_card(task)
        assert not ok

    def test_empty_primary_variable_fails(self):
        task = _valid_task()
        task["primary_variable"] = ""
        ok, errs = validate_task_card(task)
        assert not ok

    # ── fixed_params ──
    def test_fixed_params_as_object_passes(self):
        task = _valid_task()
        ok, errs = validate_task_card(task)
        assert ok

    def test_fixed_params_as_array_fails(self):
        task = _valid_task()
        task["fixed_params"] = ["lens_mm", "sensor_fit"]
        ok, errs = validate_task_card(task)
        assert not ok

    # ── dependent_variables ──
    def test_dependent_variable_missing_name_fails(self):
        task = _valid_task()
        task["dependent_variables"] = [{"solver": "test"}]
        ok, errs = validate_task_card(task)
        assert not ok

    def test_dependent_variable_duplicate_name_fails(self):
        task = _valid_task()
        task["dependent_variables"] = [
            {"name": "shift_y", "solver": "centering"},
            {"name": "shift_y", "solver": "other"},
        ]
        ok, errs = validate_task_card(task)
        assert not ok

    # ── Cross-field overlap ──
    def test_primary_overlaps_fixed_param_key_fails(self):
        task = _valid_task()
        task["primary_variable"] = "lens_mm"
        task["fixed_params"] = {"lens_mm": 24}
        ok, errs = validate_task_card(task)
        assert not ok

    def test_primary_overlaps_dependent_variable_name_fails(self):
        task = _valid_task()
        task["primary_variable"] = "camera_shift_y"
        ok, errs = validate_task_card(task)
        assert not ok

    def test_dependent_and_fixed_overlap_fails(self):
        task = _valid_task()
        task["dependent_variables"] = [{"name": "lens_mm", "solver": "test"}]
        task["fixed_params"] = {"lens_mm": 24}
        ok, errs = validate_task_card(task)
        assert not ok

    # ── technical_pass_conditions ──
    def test_condition_missing_operator_fails(self):
        task = _valid_task()
        task["technical_pass_conditions"] = [
            {"condition_id": "test", "metric": "x", "expected": 0, "required": True}
        ]
        ok, errs = validate_task_card(task)
        assert not ok

    def test_between_expected_not_two_numbers_fails(self):
        task = _valid_task()
        task["technical_pass_conditions"] = [
            {"condition_id": "test", "metric": "x", "operator": "between", "expected": [1], "required": True}
        ]
        ok, errs = validate_task_card(task)
        assert not ok

    def test_between_expected_non_numeric_fails(self):
        task = _valid_task()
        task["technical_pass_conditions"] = [
            {"condition_id": "test", "metric": "x", "operator": "between", "expected": ["a", "b"], "required": True}
        ]
        ok, errs = validate_task_card(task)
        assert not ok

    def test_condition_id_duplicate_fails(self):
        task = _valid_task()
        task["technical_pass_conditions"] = [
            {"condition_id": "dup", "metric": "x", "operator": "eq", "expected": 0, "required": True},
            {"condition_id": "dup", "metric": "y", "operator": "eq", "expected": 1, "required": True},
        ]
        ok, errs = validate_task_card(task)
        assert not ok

    def test_in_operator_non_empty_array_passes(self):
        task = _valid_task()
        task["technical_pass_conditions"] = [
            {"condition_id": "check", "metric": "status", "operator": "in", "expected": [0, 1, 2], "required": True}
        ]
        ok, errs = validate_task_card(task)
        assert ok

    # ── locked_items ──
    def test_locked_items_as_strings_fails(self):
        task = _valid_task()
        task["locked_items"] = ["character_library", "counter_geometry"]
        ok, errs = validate_task_card(task)
        assert not ok

    def test_locked_items_structured_passes(self):
        task = _valid_task()
        ok, errs = validate_task_card(task)
        assert ok

    # ── state_patch_requested ──
    def test_state_patch_requested_null_passes(self):
        task = _valid_task()
        task["state_patch_requested"] = None
        ok, errs = validate_task_card(task)
        assert ok

    def test_state_patch_requested_empty_object_fails(self):
        task = _valid_task()
        task["state_patch_requested"] = {}
        ok, errs = validate_task_card(task)
        assert not ok

    def test_state_patch_requested_unknown_field_fails(self):
        task = _valid_task()
        task["state_patch_requested"] = {
            "fields": {"scene_phase": "done"},
            "reason": "test",
            "extra_field": "should_not_be_here",
        }
        ok, errs = validate_task_card(task)
        assert not ok

    def test_state_patch_requested_missing_reason_fails(self):
        task = _valid_task()
        task["state_patch_requested"] = {"fields": {"scene_phase": "done"}}
        ok, errs = validate_task_card(task)
        assert not ok

    # ── v1.2: state_patch_requested.fields whitelist ──
    def test_state_patch_unknown_ps_field_fails(self):
        """Task state_patch_requested.fields with unknown PROJECT_STATE field must fail."""
        task = _valid_task()
        task["state_patch_requested"] = {
            "fields": {"made_up_field": 42},
            "reason": "test",
        }
        ok, errs = validate_task_card(task)
        assert not ok, f"Unknown PS field should be rejected, got: {errs}"

    def test_state_patch_known_ps_field_passes(self):
        """Task state_patch_requested.fields with valid PROJECT_STATE field must pass."""
        task = _valid_task()
        task["state_patch_requested"] = {
            "fields": {"scene_phase": "testing"},
            "reason": "Update scene phase",
        }
        ok, errs = validate_task_card(task)
        assert ok, f"Known PS field should pass, got: {errs}"

    # ── output_files / upload_files ──
    def test_output_files_empty_fails(self):
        task = _valid_task()
        task["output_files"] = []
        ok, errs = validate_task_card(task)
        assert not ok

    def test_upload_files_duplicate_fails(self):
        task = _valid_task()
        task["upload_files"] = ["a.png", "b.png", "a.png"]
        ok, errs = validate_task_card(task)
        assert not ok

    def test_input_files_duplicate_fails(self):
        task = _valid_task()
        task["input_files"] = ["a.blend", "a.blend"]
        ok, errs = validate_task_card(task)
        assert not ok

    # ── v1.2: allowed vs forbidden conflict detection ──
    def test_allowed_forbidden_same_target_same_field_fails(self):
        task = _valid_task()
        task["allowed_modifications"] = [
            {"target": "Camera", "fields": ["location", "rotation_euler"]}
        ]
        task["forbidden_modifications"] = [
            {"target": "Camera", "fields": ["location"]}
        ]
        ok, errs = validate_task_card(task)
        assert not ok, f"Conflict Camera.location should be rejected"

    def test_allowed_forbidden_same_target_no_overlap_passes(self):
        task = _valid_task()
        task["allowed_modifications"] = [
            {"target": "Camera", "fields": ["location"]}
        ]
        task["forbidden_modifications"] = [
            {"target": "Camera", "fields": ["rotation_euler"]}
        ]
        ok, errs = validate_task_card(task)
        assert ok, f"Non-overlapping fields should pass, got: {errs}"

    def test_allowed_forbidden_different_target_passes(self):
        task = _valid_task()
        task["allowed_modifications"] = [
            {"target": "Camera", "fields": ["location"]}
        ]
        task["forbidden_modifications"] = [
            {"target": "Light", "fields": ["location"]}
        ]
        ok, errs = validate_task_card(task)
        assert ok, f"Different targets should pass, got: {errs}"

    # ── Legacy ──
    def test_invalid_task_type_fails(self):
        task = _valid_task()
        task["task_type"] = "FANCY_NEW_TYPE"
        ok, errs = validate_task_card(task)
        assert not ok


class TestVisualIntentNaturalLanguage:
    def test_visual_intent_allows_natural_language(self):
        task = _valid_task()
        task["visual_intent"] = "画面应该像一个温馨的日本便利店，暖色调灯光"
        ok, errs = validate_task_card(task)
        assert ok
