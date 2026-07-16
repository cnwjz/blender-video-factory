"""Test task card freeze and verification — v2 task format compatible."""

import os
import tempfile
import yaml

from protocol_guard.frozen.snapshot import freeze_task, verify_frozen_task


def _write_task(task_dir, task_data):
    task_path = os.path.join(task_dir, "task.yaml")
    with open(task_path, "w", encoding="utf-8") as f:
        yaml.dump(task_data, f, default_flow_style=False, allow_unicode=True)
    return task_path


def _base_task():
    return {
        "task_id": "FREEZE_TEST",
        "task_card_version": 2,
        "protocol_version": "v1.0",
        "execution_mode": "confirm_then_execute",
        "task_type": "AUDIT",
        "project_state_file": "PROJECT_STATE.yaml",
        "input_files": ["test.blend"],
        "output_files": ["test_out.blend", "report.md"],
        "primary_goal": "Test freeze",
        "primary_variable": "camera_distance_m",
        "dependent_variables": [
            {"name": "shift_y", "solver": "centering"},
        ],
        "fixed_params": {"lens_mm": 24},
        "locked_items": [
            {"lock_id": "chars", "resource_type": "blender_collection", "selector": "CHR_*", "protected_fields": ["location"]},
        ],
        "allowed_modifications": [{"target": "Camera", "fields": ["location"]}],
        "forbidden_modifications": [{"target": "CHR_*", "fields": ["location"]}],
        "preflight_checks": [{"check_id": "c1", "checker": "file_exists", "required": True}],
        "technical_pass_conditions": [
            {"condition_id": "c1", "metric": "h", "operator": "gte", "expected": 48, "required": True},
        ],
        "visual_intent": "Clear view",
        "visual_forbidden": "No clipping",
        "evidence_required": [{"evidence_id": "clean", "role": "clean_preview", "path": "clean.png", "required": True}],
        "upload_dir": "reviews",
        "upload_files": ["clean.png", "report.md"],
        "stop_conditions": [{"condition": "fail", "action": "stop_current_task"}],
        "state_patch_requested": None,
    }


class TestFreezeTask:
    def test_first_freeze_succeeds(self):
        with tempfile.TemporaryDirectory() as td:
            task_path = _write_task(td, _base_task())
            frozen_dir = os.path.join(td, "frozen")
            ok, sha, err = freeze_task(task_path, frozen_dir)
            assert ok, f"Freeze failed: {err}"
            assert sha is not None
            assert len(sha) == 64
            assert os.path.exists(os.path.join(frozen_dir, "frozen_task.yaml"))
            assert os.path.exists(os.path.join(frozen_dir, "frozen_task.sha256"))

    def test_verify_succeeds_on_unchanged_task(self):
        with tempfile.TemporaryDirectory() as td:
            task_path = _write_task(td, _base_task())
            frozen_dir = os.path.join(td, "frozen")
            ok, sha, err = freeze_task(task_path, frozen_dir)
            assert ok

            match, current, stored, verify_err = verify_frozen_task(task_path, frozen_dir)
            assert match, f"Verification failed: {verify_err}"
            assert current == stored

    def test_modified_task_fails_verification(self):
        with tempfile.TemporaryDirectory() as td:
            task_path = _write_task(td, _base_task())
            frozen_dir = os.path.join(td, "frozen")
            ok, sha, err = freeze_task(task_path, frozen_dir)
            assert ok

            task_data = _base_task()
            task_data["primary_variable"] = "different_lens"
            _write_task(td, task_data)

            match, current, stored, verify_err = verify_frozen_task(task_path, frozen_dir)
            assert not match, "Modified task should fail verification"
            assert current != stored

    def test_existing_frozen_rejects_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            task_path = _write_task(td, _base_task())
            frozen_dir = os.path.join(td, "frozen")
            ok, sha, err = freeze_task(task_path, frozen_dir)
            assert ok

            ok2, sha2, err2 = freeze_task(task_path, frozen_dir)
            assert not ok2, "Second freeze should be rejected"
            assert "already exists" in err2.lower()

    def test_freezing_nonexistent_dir_creates_it(self):
        with tempfile.TemporaryDirectory() as td:
            task_path = _write_task(td, _base_task())
            frozen_dir = os.path.join(td, "nested", "frozen")
            ok, sha, err = freeze_task(task_path, frozen_dir)
            assert ok
            assert os.path.isdir(frozen_dir)
