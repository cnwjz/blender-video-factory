"""Test PROJECT_STATE v2 + v1.2 + v1.3 + v1.4 integrity checks."""

import os
import copy
import tempfile
import glob as globmod
import pytest
import yaml

from protocol_guard.state.project_state import (
    validate_state,
    validate_patch,
    validate_patch_document,
    apply_patch_document,
    apply_patch,
    load_state,
    save_state,
    _write_yaml_unchecked,
    build_evidence_manifest,
    verify_evidence_manifest,
    _sha256_file,
    CLAUDE_WRITABLE,
)
from protocol_guard.result import VALID_TECHNICAL_RESULTS, VALID_EVIDENCE_STATUSES


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_PATH = os.path.join(PROJECT_ROOT, "PROJECT_STATE.yaml")


def _base_state():
    return {
        "protocol_version": "v1.0",
        "project_id": "test_project",
        "workflow_phase": "testing",
        "scene_phase": "test_phase",
        "phase_approved": False,
        "project_work_paused": True,
        "last_task_id": "TEST_001",
        "last_task_card_sha256": None,
        "last_technical_result": "TECHNICAL_PASS",
        "evidence_status": "VALID",
        "evidence_sha256": None,
        "output_files": ["test.md"],
        "last_execution_time": "2026-07-15T13:25:23+08:00",
        "locked_assets": [],
        "unlocked_assets": [],
        "diagnostic_only_outputs": [],
        "pending_review": None,
        "blocked_operations": ["禁止测试操作"],
        "failed_paths": [],
        "change_log": [
            {
                "timestamp": "2026-01-01T00:00:00+00:00",
                "actor": "SYSTEM_MIGRATION",
                "task_id": "INIT",
                "fields_changed": ["initial_state"],
                "reason": "Initial creation",
            }
        ],
    }


def _patch_doc(actor="CLAUDE", fields=None, task_id="TASK_PATCH", reason="test"):
    return {
        "actor": actor,
        "task_id": task_id,
        "fields": fields or {"last_task_id": "NEW_TASK"},
        "reason": reason,
    }


# ═══════════════════════════════════════════════════════════════════
# Schema validation (existing)
# ═══════════════════════════════════════════════════════════════════

class TestProjectStateSchemaV2:
    def test_initial_project_state_passes(self):
        state = load_state(STATE_PATH)
        ok, errs = validate_state(state)
        assert ok, f"PROJECT_STATE.yaml failed validation: {errs}"

    def test_invalid_technical_result_fails(self):
        state = _base_state()
        state["last_technical_result"] = "BOGUS_RESULT"
        ok, errs = validate_state(state)
        assert not ok

    def test_invalid_evidence_status_fails(self):
        state = _base_state()
        state["evidence_status"] = "BOGUS"
        ok, errs = validate_state(state)
        assert not ok

    def test_missing_required_field_fails(self):
        state = _base_state()
        del state["workflow_phase"]
        ok, errs = validate_state(state)
        assert not ok

    def test_missing_locked_assets_fails(self):
        state = _base_state()
        del state["locked_assets"]
        ok, errs = validate_state(state)
        assert not ok

    def test_missing_blocked_operations_fails(self):
        state = _base_state()
        del state["blocked_operations"]
        ok, errs = validate_state(state)
        assert not ok

    def test_sha256_empty_string_fails(self):
        state = _base_state()
        state["last_task_card_sha256"] = ""
        ok, errs = validate_state(state)
        assert not ok

    def test_sha256_null_passes(self):
        state = _base_state()
        ok, errs = validate_state(state)
        assert ok

    def test_sha256_64_hex_passes(self):
        state = _base_state()
        state["last_task_card_sha256"] = "a" * 64
        ok, errs = validate_state(state)
        assert ok

    def test_evidence_sha256_empty_string_fails(self):
        state = _base_state()
        state["evidence_sha256"] = ""
        ok, errs = validate_state(state)
        assert not ok

    def test_evidence_sha256_null_passes(self):
        state = _base_state()
        ok, errs = validate_state(state)
        assert ok

    # ── v1.2: strict datetime validation ──
    def test_last_execution_time_without_timezone_fails(self):
        state = _base_state()
        state["last_execution_time"] = "2026-01-01T00:00:00"
        ok, errs = validate_state(state)
        assert not ok

    def test_invalid_datetime_month_99_fails(self):
        state = _base_state()
        state["last_execution_time"] = "2026-99-99T25:99:99+99:99"
        ok, errs = validate_state(state)
        assert not ok

    def test_invalid_datetime_hour_25_fails(self):
        state = _base_state()
        state["last_execution_time"] = "2026-01-01T25:99:99+00:00"
        ok, errs = validate_state(state)
        assert not ok

    def test_valid_z_time_passes(self):
        state = _base_state()
        state["last_execution_time"] = "2026-07-15T05:25:23Z"
        ok, errs = validate_state(state)
        assert ok

    def test_valid_offset_time_passes(self):
        state = _base_state()
        state["last_execution_time"] = "2026-07-15T13:25:23+08:00"
        ok, errs = validate_state(state)
        assert ok

    def test_disk_project_state_by_schema(self):
        """Disk PROJECT_STATE.yaml must pass schema after updates."""
        state = load_state(STATE_PATH)
        ok, errs = validate_state(state)
        assert ok, f"Disk state failed: {errs}"

    def test_change_log_entry_3_actor_is_system_migration(self):
        """Third change_log entry must have actor=SYSTEM_MIGRATION."""
        state = load_state(STATE_PATH)
        entries = state.get("change_log", [])
        assert len(entries) >= 3, f"Expected at least 3 change_log entries, got {len(entries)}"
        assert entries[2]["actor"] == "SYSTEM_MIGRATION", f"Entry 2 actor: {entries[2]['actor']}"


# ═══════════════════════════════════════════════════════════════════
# Field permissions (v1.2: CLAUDE strict whitelist)
# ═══════════════════════════════════════════════════════════════════

class TestFieldPermissions:
    def test_claude_can_write_runtime_fields(self):
        allowed, blocked, reason = validate_patch("CLAUDE", {
            "last_task_id": "TASK_002",
            "last_technical_result": "TECHNICAL_FAIL",
            "evidence_status": "VALID",
        })
        assert allowed, f"CLAUDE should be allowed: {reason}"

    def test_claude_cannot_write_locked_assets(self):
        allowed, blocked, reason = validate_patch("CLAUDE", {
            "locked_assets": []
        })
        assert not allowed

    def test_claude_cannot_write_project_id(self):
        """CLAUDE strict whitelist: project_id is not in CLAUDE_WRITABLE."""
        allowed, blocked, reason = validate_patch("CLAUDE", {
            "project_id": "hijacked"
        })
        assert not allowed, f"CLAUDE should not write project_id: {reason}"
        assert "project_id" in blocked

    def test_claude_cannot_write_unknown_field(self):
        """CLAUDE strict whitelist: any unknown field must be rejected."""
        allowed, blocked, reason = validate_patch("CLAUDE", {
            "made_up_field": 42
        })
        assert not allowed, f"Unknown field should be rejected: {reason}"

    def test_claude_writes_valid_runtime_field_passes(self):
        allowed, blocked, reason = validate_patch("CLAUDE", {
            "last_execution_time": "2026-07-15T13:25:23+08:00"
        })
        assert allowed, f"Valid runtime field should pass: {reason}"

    def test_gpt_proposal_cannot_write_directly(self):
        allowed, blocked, reason = validate_patch("GPT_PROPOSAL", {
            "scene_phase": "camera_locked"
        })
        assert not allowed

    def test_user_approved_can_write_restricted_fields(self):
        allowed, blocked, reason = validate_patch("USER_APPROVED", {
            "scene_phase": "camera_locked",
            "phase_approved": True,
        })
        assert allowed


# ═══════════════════════════════════════════════════════════════════
# apply_patch_document (v1.2)
# ═══════════════════════════════════════════════════════════════════

class TestApplyPatchDocument:
    def test_claude_runtime_patch_succeeds(self):
        state = _base_state()
        pd = _patch_doc("CLAUDE", {"last_task_id": "TASK_003"})
        ok, new_state, errs = apply_patch_document(state, pd)
        assert ok, f"Expected success: {errs}"
        assert new_state["last_task_id"] == "TASK_003"

    def test_claude_project_id_rejected(self):
        state = _base_state()
        pd = _patch_doc("CLAUDE", {"project_id": "hijacked"})
        ok, new_state, errs = apply_patch_document(state, pd)
        assert not ok

    def test_atomic_failure_no_partial_change(self):
        """Failed patch must not modify original state at all."""
        state = _base_state()
        original_id = state["last_task_id"]
        pd = _patch_doc("CLAUDE", {"project_id": "hijacked", "last_task_id": "SHOULD_NOT_APPLY"})
        ok, new_state, errs = apply_patch_document(state, pd)
        assert not ok
        assert new_state is state  # original unchanged
        assert state["last_task_id"] == original_id  # not partially modified

    def test_invalid_enum_atomic_failure(self):
        """Writing invalid technical_result must fail atomically."""
        state = _base_state()
        pd = _patch_doc("USER_APPROVED", {"last_technical_result": "BOGUS"})
        ok, new_state, errs = apply_patch_document(state, pd)
        assert not ok

    def test_invalid_evidence_status_atomic_failure(self):
        state = _base_state()
        pd = _patch_doc("USER_APPROVED", {"evidence_status": "BOGUS"})
        ok, new_state, errs = apply_patch_document(state, pd)
        assert not ok

    def test_invalid_sha256_atomic_failure(self):
        state = _base_state()
        pd = _patch_doc("USER_APPROVED", {"evidence_sha256": "not-a-sha256"})
        ok, new_state, errs = apply_patch_document(state, pd)
        assert not ok

    def test_does_not_modify_original_state(self):
        """apply_patch_document must not mutate the input state_data dict."""
        state = _base_state()
        original = copy.deepcopy(state)
        pd = _patch_doc("CLAUDE", {"last_task_id": "NEW"})
        ok, _, _ = apply_patch_document(state, pd)
        assert state == original, "Original state_data was mutated"

    def test_does_not_modify_original_patch(self):
        """apply_patch_document must not mutate the input patch_doc."""
        state = _base_state()
        pd = _patch_doc("CLAUDE", {"last_task_id": "NEW"})
        original_pd = copy.deepcopy(pd)
        apply_patch_document(state, pd)
        assert pd == original_pd, "Original patch_doc was mutated"

    def test_change_log_in_fields_rejected(self):
        """Patch fields containing change_log must be rejected."""
        state = _base_state()
        pd = _patch_doc("USER_APPROVED", {"scene_phase": "x", "change_log": []})
        ok, _, errs = apply_patch_document(state, pd)
        assert not ok, f"change_log in fields should be rejected"

    def test_auto_change_log_appended_on_success(self):
        state = _base_state()
        original_len = len(state["change_log"])
        pd = _patch_doc("CLAUDE", {"last_task_id": "NEW_LOG"})
        ok, new_state, errs = apply_patch_document(state, pd)
        assert ok
        assert len(new_state["change_log"]) == original_len + 1

    def test_no_change_log_appended_on_failure(self):
        state = _base_state()
        original_len = len(state["change_log"])
        pd = _patch_doc("CLAUDE", {"project_id": "bad"})
        ok, _, errs = apply_patch_document(state, pd)
        assert not ok
        assert len(state["change_log"]) == original_len

    def test_gpt_proposal_without_approval_rejected(self):
        state = _base_state()
        pd = _patch_doc("GPT_PROPOSAL", {"scene_phase": "locked"})
        ok, _, errs = apply_patch_document(state, pd)
        assert not ok

    def test_gpt_proposal_with_approval_succeeds(self):
        state = _base_state()
        pd = _patch_doc("GPT_PROPOSAL", {"scene_phase": "camera_locked"})
        ok, new_state, _ = apply_patch_document(state, pd, approval={
            "approved_by": "USER_APPROVED",
            "approved_fields": ["scene_phase"],
        })
        assert ok
        assert new_state["scene_phase"] == "camera_locked"

    def test_user_approved_writes_restricted_succeeds(self):
        state = _base_state()
        pd = _patch_doc("USER_APPROVED", {"scene_phase": "locked", "phase_approved": True})
        ok, new_state, _ = apply_patch_document(state, pd)
        assert ok
        assert new_state["phase_approved"] is True

    def test_candidate_state_passes_schema_after_apply(self):
        """The new state after a successful patch must pass full schema validation."""
        state = _base_state()
        pd = _patch_doc("CLAUDE", {"last_execution_time": "2026-07-15T13:25:23+08:00"})
        ok, new_state, errs = apply_patch_document(state, pd)
        assert ok, f"Apply failed: {errs}"
        ok_v, v_errs = validate_state(new_state)
        assert ok_v, f"Result state failed validation: {v_errs}"

    def test_legacy_apply_patch_compatibility(self):
        """Legacy apply_patch still works as wrapper."""
        state = _base_state()
        ok, new_state, errs = apply_patch(state, "CLAUDE", {"last_task_id": "LEGACY"})
        assert ok, f"Legacy apply_patch failed: {errs}"
        assert new_state["last_task_id"] == "LEGACY"


class TestStatePatchSchemaV2:
    def test_patch_reason_required(self):
        import json, jsonschema
        ps_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "schemas", "state_patch.schema.json")
        with open(ps_path, "r", encoding="utf-8") as f:
            patch_schema = json.load(f)
        patch = {"actor": "CLAUDE", "task_id": "T", "fields": {"last_task_id": "X"}}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=patch, schema=patch_schema)

    def test_patch_unknown_state_field_fails(self):
        import json, jsonschema
        ps_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "schemas", "state_patch.schema.json")
        with open(ps_path, "r", encoding="utf-8") as f:
            patch_schema = json.load(f)
        patch = {"actor": "CLAUDE", "task_id": "T", "fields": {"not_a_real_field": 42}, "reason": "test"}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=patch, schema=patch_schema)

    def test_patch_valid_field_passes(self):
        import json, jsonschema
        ps_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "schemas", "state_patch.schema.json")
        with open(ps_path, "r", encoding="utf-8") as f:
            patch_schema = json.load(f)
        patch = {"actor": "CLAUDE", "task_id": "T", "fields": {"last_task_id": "X"}, "reason": "test"}
        jsonschema.validate(instance=patch, schema=patch_schema)

    def test_patch_task_id_required(self):
        import json, jsonschema
        ps_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "schemas", "state_patch.schema.json")
        with open(ps_path, "r", encoding="utf-8") as f:
            patch_schema = json.load(f)
        patch = {"actor": "CLAUDE", "fields": {"last_task_id": "X"}, "reason": "test"}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=patch, schema=patch_schema)


# ═══════════════════════════════════════════════════════════════════
# v1.4: save_state with unconditional tmp_path cleanup
# ═══════════════════════════════════════════════════════════════════

class TestSaveState:
    def test_save_valid_state_succeeds(self):
        state = _base_state()
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "state.yaml")
            ok, errs = save_state(state, sp)
            assert ok, f"save_state should succeed: {errs}"
            assert os.path.exists(sp)

    def test_save_invalid_state_fails(self):
        state = _base_state()
        state["last_technical_result"] = "BOGUS"
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "state.yaml")
            ok, errs = save_state(state, sp)
            assert not ok

    def test_invalid_state_does_not_create_file(self):
        state = _base_state()
        state["last_technical_result"] = "BOGUS"
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "state.yaml")
            ok, errs = save_state(state, sp)
            assert not ok
            assert not os.path.exists(sp), "No file should be created for invalid state"

    def test_invalid_write_does_not_corrupt_existing_file(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "state.yaml")
            state = _base_state()
            ok1, _ = save_state(state, sp)
            assert ok1
            with open(sp, "r", encoding="utf-8") as f:
                original_content = f.read()

            bad_state = _base_state()
            bad_state["last_technical_result"] = "BOGUS"
            ok2, _ = save_state(bad_state, sp)
            assert not ok2
            with open(sp, "r", encoding="utf-8") as f:
                current_content = f.read()
            assert current_content == original_content, "Original file was corrupted"

    def test_save_state_does_not_modify_input(self):
        state = _base_state()
        original = copy.deepcopy(state)
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "state.yaml")
            save_state(state, sp)
        assert state == original, "save_state must not mutate input state_data"

    def test_saved_state_revalidates_on_reload(self):
        state = _base_state()
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "state.yaml")
            ok, _ = save_state(state, sp)
            assert ok
            reloaded = load_state(sp)
            ok_v, errs = validate_state(reloaded)
            assert ok_v, f"Reloaded state failed validation: {errs}"

    def test_reread_validation_failure_cleans_temp_file(self, monkeypatch):
        """Real test: monkeypatch _write_yaml_unchecked to write corrupt YAML that loads but fails validate_state."""
        def fake_write(data, path):
            # Write valid YAML that will parse but fail validate_state
            bad = copy.deepcopy(data)
            bad["last_technical_result"] = "BOGUS"
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(bad, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        monkeypatch.setattr(
            "protocol_guard.state.project_state._write_yaml_unchecked", fake_write
        )

        state = _base_state()
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "state.yaml")
            ok, _ = save_state(state, sp)
            assert not ok, "Should fail on corrupt re-read validation"
            # No temp files should remain
            temps = globmod.glob(os.path.join(td, ".project_state_tmp_*"))
            assert len(temps) == 0, f"Temp files left behind: {temps}"
            # Original file should not have been created (first save never succeeded)
            assert not os.path.exists(sp), "File should not exist for first-time save failure"

    def test_reread_failure_preserves_existing_file(self, monkeypatch):
        """When an existing valid file exists, corrupt re-read validation must preserve it."""
        def fake_write(data, path):
            bad = copy.deepcopy(data)
            bad["last_technical_result"] = "BOGUS"
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(bad, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "state.yaml")
            # First, write a valid file
            state = _base_state()
            ok1, _ = save_state(state, sp)
            assert ok1
            with open(sp, "rb") as f:
                original_bytes = f.read()

            # Now try to overwrite with monkeypatched corruption
            monkeypatch.setattr(
                "protocol_guard.state.project_state._write_yaml_unchecked", fake_write
            )
            ok2, _ = save_state(state, sp)
            assert not ok2
            # Original file bytes unchanged
            with open(sp, "rb") as f:
                current_bytes = f.read()
            assert current_bytes == original_bytes, "Existing file bytes changed after failed save"
            # No temp files
            temps = globmod.glob(os.path.join(td, ".project_state_tmp_*"))
            assert len(temps) == 0, f"Temp files left behind: {temps}"

    def test_read_exception_cleans_temp_file(self, monkeypatch):
        """If reading the temp file fails, temp file must be cleaned up."""
        def fake_write(data, path):
            # Write non-YAML garbage that will cause yaml.safe_load to fail
            with open(path, "wb") as f:
                f.write(b"\x00\x01\x02INVALID")
        monkeypatch.setattr(
            "protocol_guard.state.project_state._write_yaml_unchecked", fake_write
        )
        state = _base_state()
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "state.yaml")
            ok, errs = save_state(state, sp)
            assert not ok
            temps = globmod.glob(os.path.join(td, ".project_state_tmp_*"))
            assert len(temps) == 0, f"Temp files left behind: {temps}"

    def test_successful_save_leaves_no_temp_file(self):
        state = _base_state()
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "state.yaml")
            ok, _ = save_state(state, sp)
            assert ok
            temps = globmod.glob(os.path.join(td, ".project_state_tmp_*"))
            assert len(temps) == 0, f"Temp files left behind after success: {temps}"

    def test_replace_exception_cleans_temp_file(self, monkeypatch):
        """os.replace() failure must leave original file intact and clean temp file."""
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "state.yaml")
            state = _base_state()
            # First save must succeed before we break os.replace
            ok1, _ = save_state(state, sp)
            assert ok1
            with open(sp, "rb") as f:
                original_bytes = f.read()

            # Now break os.replace for the second save
            def fake_replace(src, dst):
                raise OSError("Simulated replace failure")
            monkeypatch.setattr(os, "replace", fake_replace)

            ok2, errs = save_state(state, sp)
            assert not ok2, f"save_state should fail on replace exception, got: {errs}"
            with open(sp, "rb") as f:
                current_bytes = f.read()
            assert current_bytes == original_bytes, "Original file bytes changed after replace exception"
            temps = globmod.glob(os.path.join(td, ".project_state_tmp_*"))
            assert len(temps) == 0, f"Temp files left behind after replace exception: {temps}"


# ═══════════════════════════════════════════════════════════════════
# v1.3: GPT_PROPOSAL source logging
# ═══════════════════════════════════════════════════════════════════

class TestGptProposalLogging:
    def test_gpt_proposal_log_reason_has_source_prefix(self):
        state = _base_state()
        pd = _patch_doc("GPT_PROPOSAL", {"scene_phase": "locked"}, reason="Camera framing approved")
        ok, new_state, _ = apply_patch_document(state, pd, approval={
            "approved_by": "USER_APPROVED",
            "approved_fields": ["scene_phase"],
        })
        assert ok
        log = new_state["change_log"][-1]
        assert "[GPT_PROPOSAL via USER_APPROVED]" in log["reason"]

    def test_direct_user_approved_no_gpt_prefix(self):
        state = _base_state()
        pd = _patch_doc("USER_APPROVED", {"scene_phase": "locked"}, reason="Direct approval")
        ok, new_state, _ = apply_patch_document(state, pd)
        assert ok
        log = new_state["change_log"][-1]
        assert "[GPT_PROPOSAL via USER_APPROVED]" not in log["reason"]
        assert log["reason"] == "Direct approval"

    def test_gpt_proposal_log_actor_is_user_approved(self):
        state = _base_state()
        pd = _patch_doc("GPT_PROPOSAL", {"scene_phase": "locked"})
        ok, new_state, _ = apply_patch_document(state, pd, approval={
            "approved_by": "USER_APPROVED",
            "approved_fields": ["scene_phase"],
        })
        assert ok
        log = new_state["change_log"][-1]
        assert log["actor"] == "USER_APPROVED"


# ═══════════════════════════════════════════════════════════════════
# v1.3: PROJECT_STATE coherence on disk
# ═══════════════════════════════════════════════════════════════════

class TestProjectStateCoherence:
    def test_last_task_id_matches_pending_review(self):
        state = load_state(STATE_PATH)
        assert state["last_task_id"] == state["pending_review"]["task_id"], \
            f"last_task_id={state['last_task_id']} != pending_review.task_id={state['pending_review']['task_id']}"

    def test_output_files_belong_to_phase(self):
        state = load_state(STATE_PATH)
        ofiles = state.get("output_files", [])
        assert "evidence_manifest.json" in ofiles, f"Missing evidence_manifest.json in output_files: {ofiles}"

    def test_output_files_exact_phase_1_4_set(self):
        """output_files must be exactly the 6 Phase 1.4 deliverable files, no more, no less."""
        state = load_state(STATE_PATH)
        ofiles = state.get("output_files", [])
        expected = [
            "CODE_GUARD_MVP_PHASE_1_4_REPORT.md",
            "CODE_GUARD_PHASE_1_4_SOURCE_SNAPSHOT.txt",
            "PROJECT_STATE.yaml",
            "pytest_output.txt",
            "adversarial_test_output.txt",
            "evidence_manifest.json",
        ]
        assert sorted(ofiles) == sorted(expected), \
            f"output_files mismatch. Expected: {expected}, Got: {ofiles}"

    def test_change_log_has_phase_1_2_record(self):
        state = load_state(STATE_PATH)
        task_ids = [e["task_id"] for e in state.get("change_log", [])]
        assert "CODE_GUARD_MVP_PHASE_1_2_PATCH_INTEGRITY" in task_ids

    def test_change_log_has_phase_1_3_record(self):
        state = load_state(STATE_PATH)
        task_ids = [e["task_id"] for e in state.get("change_log", [])]
        assert "CODE_GUARD_MVP_PHASE_1_3_PERSISTENCE_COHERENCE" in task_ids

    def test_change_log_has_phase_1_4_record(self):
        state = load_state(STATE_PATH)
        task_ids = [e["task_id"] for e in state.get("change_log", [])]
        assert "CODE_GUARD_MVP_PHASE_1_4_FINAL_EVIDENCE_FIX" in task_ids

    def test_current_project_state_passes_schema(self):
        state = load_state(STATE_PATH)
        ok, errs = validate_state(state)
        assert ok, f"Disk PROJECT_STATE failed schema: {errs}"


# ═══════════════════════════════════════════════════════════════════
# v1.4: evidence manifest
# ═══════════════════════════════════════════════════════════════════

class TestEvidenceManifest:
    def _make_deliverable(self, td, name, content):
        p = os.path.join(td, name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        return p

    def test_manifest_no_self_reference(self):
        """Manifest must not contain evidence_manifest.json or PROJECT_STATE.yaml."""
        with tempfile.TemporaryDirectory() as td:
            state = _base_state()
            state["last_task_id"] = "MANIFEST_TEST"
            files = {}
            for i, name in enumerate(["a.md", "b.txt", "c.txt", "d.txt"]):
                files[name] = self._make_deliverable(td, name, f"content_{i}")
            mp = os.path.join(td, "evidence_manifest.json")
            ok, manifest, msha, errs = build_evidence_manifest(state, files, "MANIFEST_TEST", mp)
            assert ok, f"build failed: {errs}"
            mfiles = manifest.get("files", {})
            assert "evidence_manifest.json" not in mfiles, "Manifest contains self"
            assert "PROJECT_STATE.yaml" not in mfiles, "Manifest contains PS raw hash"

    def test_report_modification_detected(self):
        """Changing a deliverable file must cause verification failure."""
        with tempfile.TemporaryDirectory() as td:
            state = _base_state()
            state["last_task_id"] = "TAMPER_TEST"
            files = {}
            for i, name in enumerate(["report.md", "snap.txt", "pytest.txt", "adv.txt"]):
                files[name] = self._make_deliverable(td, name, f"v{i}")
            mp = os.path.join(td, "evidence_manifest.json")
            build_evidence_manifest(state, files, "TAMPER_TEST", mp)
            state["evidence_sha256"] = _sha256_file(mp)
            ok1, errs1 = verify_evidence_manifest(state, mp, files)
            assert ok1, f"Initial verify should pass: {errs1}"
            # Tamper with a file
            with open(files["report.md"], "w") as f:
                f.write("tampered")
            ok2, errs2 = verify_evidence_manifest(state, mp, files)
            assert not ok2, "Tampered report should be detected"

    def test_pytest_modification_detected(self):
        with tempfile.TemporaryDirectory() as td:
            state = _base_state()
            state["last_task_id"] = "PTEST"
            files = {}
            for i, name in enumerate(["r.md", "s.txt", "pytest.txt", "a.txt"]):
                files[name] = self._make_deliverable(td, name, f"v{i}")
            mp = os.path.join(td, "evidence_manifest.json")
            build_evidence_manifest(state, files, "PTEST", mp)
            state["evidence_sha256"] = _sha256_file(mp)
            with open(files["pytest.txt"], "w") as f:
                f.write("tampered pytest")
            ok, _ = verify_evidence_manifest(state, mp, files)
            assert not ok

    def test_state_non_sha_field_change_detected(self):
        """Changing a non-evidence_sha256 PS field changes canonical state hash."""
        with tempfile.TemporaryDirectory() as td:
            state = _base_state()
            state["last_task_id"] = "FIELD_TEST"
            files = {}
            for i, name in enumerate(["r.md", "s.txt", "p.txt", "a.txt"]):
                files[name] = self._make_deliverable(td, name, f"v{i}")
            mp = os.path.join(td, "evidence_manifest.json")
            build_evidence_manifest(state, files, "FIELD_TEST", mp)
            state["evidence_sha256"] = _sha256_file(mp)
            ok1, _ = verify_evidence_manifest(state, mp, files)
            assert ok1
            state["last_task_id"] = "CHANGED"
            ok2, _ = verify_evidence_manifest(state, mp, files)
            assert not ok2, "State field change should be detected via canonical hash mismatch"

    def test_evidence_sha_writeback_passes(self):
        """Only writing evidence_sha256 back should still verify (canonical hash uses null)."""
        with tempfile.TemporaryDirectory() as td:
            state = _base_state()
            state["last_task_id"] = "WRITEBACK"
            files = {}
            for i, name in enumerate(["r.md", "s.txt", "p.txt", "a.txt"]):
                files[name] = self._make_deliverable(td, name, f"v{i}")
            mp = os.path.join(td, "evidence_manifest.json")
            build_evidence_manifest(state, files, "WRITEBACK", mp)
            msha = _sha256_file(mp)
            state["evidence_sha256"] = msha
            ok, errs = verify_evidence_manifest(state, mp, files)
            assert ok, f"Writeback should pass: {errs}"

    def test_sha_mismatch_detected(self):
        with tempfile.TemporaryDirectory() as td:
            state = _base_state()
            state["last_task_id"] = "WRONG_SHA"
            files = {}
            for i, name in enumerate(["r.md", "s.txt", "p.txt", "a.txt"]):
                files[name] = self._make_deliverable(td, name, f"v{i}")
            mp = os.path.join(td, "evidence_manifest.json")
            build_evidence_manifest(state, files, "WRONG_SHA", mp)
            state["evidence_sha256"] = "f" * 64  # wrong hash
            ok, _ = verify_evidence_manifest(state, mp, files)
            assert not ok, "Wrong evidence_sha256 should be detected"

    def test_task_id_mismatch_detected(self):
        with tempfile.TemporaryDirectory() as td:
            state = _base_state()
            state["last_task_id"] = "TASK_A"
            files = {}
            for i, name in enumerate(["r.md", "s.txt", "p.txt", "a.txt"]):
                files[name] = self._make_deliverable(td, name, f"v{i}")
            mp = os.path.join(td, "evidence_manifest.json")
            build_evidence_manifest(state, files, "TASK_A", mp)
            state["evidence_sha256"] = _sha256_file(mp)
            state["last_task_id"] = "TASK_B"
            ok, _ = verify_evidence_manifest(state, mp, files)
            assert not ok, "task_id mismatch should be detected"

    def test_full_package_verifies(self):
        """Complete delivery package passes all checks."""
        with tempfile.TemporaryDirectory() as td:
            state = _base_state()
            state["last_task_id"] = "FULL_PACKAGE"
            files = {}
            for i, name in enumerate(["report.md", "snapshot.txt", "pytest.txt", "adversarial.txt"]):
                files[name] = self._make_deliverable(td, name, f"content_{i}")
            mp = os.path.join(td, "evidence_manifest.json")
            ok, manifest, msha, errs = build_evidence_manifest(state, files, "FULL_PACKAGE", mp)
            assert ok
            state["evidence_sha256"] = msha
            ok_v, v_errs = verify_evidence_manifest(state, mp, files)
            assert ok_v, f"Full package should verify: {v_errs}"
            assert "evidence_manifest.json" not in manifest.get("files", {})
            assert "PROJECT_STATE.yaml" not in manifest.get("files", {})


# ═══════════════════════════════════════════════════════════════════
# v1.4: enum regression
# ═══════════════════════════════════════════════════════════════════

class TestEnumsRegression:
    def test_five_main_results_unchanged(self):
        expected = {"TECHNICAL_PASS", "TECHNICAL_FAIL", "CONSTRAINT_CONFLICT",
                    "EVIDENCE_INVALID", "SPEC_INVALID"}
        assert VALID_TECHNICAL_RESULTS == expected

    def test_three_evidence_statuses_unchanged(self):
        expected = {"VALID", "RECOVERED", "INVALID"}
        assert VALID_EVIDENCE_STATUSES == expected
