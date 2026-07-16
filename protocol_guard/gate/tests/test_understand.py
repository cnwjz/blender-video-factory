"""Test understanding record creation."""
import json, os, tempfile, yaml
from protocol_guard.gate.freeze_bundle import freeze_bundle
from protocol_guard.gate.understand import record_understanding

def _write_task(td, data):
    p = os.path.join(td, "task.yaml")
    with open(p, "w") as f: yaml.dump(data, f)
    return p

def _write_state(td, data):
    p = os.path.join(td, "state.yaml")
    with open(p, "w") as f: yaml.dump(data, f)
    return p

def _base_task():
    return {"task_id":"UR_TEST","task_card_version":2,"protocol_version":"v1.0","execution_mode":"confirm_then_execute","task_type":"PROTOCOL_MAINTENANCE","project_state_file":"state.yaml","input_files":[],"output_files":["out.txt"],"primary_goal":"Test understanding","primary_variable":"x","dependent_variables":[],"fixed_params":{},"locked_items":[],"allowed_modifications":[{"target":"gate/","fields":["all"]}],"forbidden_modifications":[{"target":"state/","fields":["any"]}],"preflight_checks":[{"check_id":"c1","checker":"f","required":True}],"technical_pass_conditions":[],"visual_intent":"","visual_forbidden":"","evidence_required":[],"upload_dir":"d","upload_files":["out.txt"],"stop_conditions":[{"condition":"fail","action":"stop_current_task"}],"state_patch_requested":None}

def _base_state():
    return {"protocol_version":"v1.0","project_id":"ur","workflow_phase":"code_guard_phase_1_locked","scene_phase":"paused","phase_approved":True,"project_work_paused":True,"last_task_id":"T","last_task_card_sha256":None,"last_technical_result":"TECHNICAL_PASS","evidence_status":"VALID","evidence_sha256":None,"output_files":[],"last_execution_time":"2026-07-15T15:00:00+08:00","locked_assets":[],"unlocked_assets":[],"diagnostic_only_outputs":[],"pending_review":None,"blocked_operations":[],"failed_paths":[],"change_log":[]}

class TestUnderstand:
    def test_record_fields(self):
        with tempfile.TemporaryDirectory() as td:
            tp = _write_task(td, _base_task())
            sp = _write_state(td, _base_state())
            fd = os.path.join(td, "frozen")
            freeze_bundle(tp, sp, fd)
            fb_path = os.path.join(fd, "freeze_bundle.json")
            ok, rec, sha, errs = record_understanding(tp, fb_path, fd)
            assert ok, f"Failed: {errs}"
            assert rec["task_id"] == "UR_TEST"
            assert rec["freeze_bundle_sha256"] is not None
            assert rec["blender_required"] == False
            assert os.path.exists(os.path.join(fd, "understand.json"))

    def test_missing_freeze(self):
        with tempfile.TemporaryDirectory() as td:
            tp = _write_task(td, _base_task())
            sp = _write_state(td, _base_state())
            ok, _, _, errs = record_understanding(tp, os.path.join(td, "nope.json"), td)
            assert not ok


class TestUnderstandExtra:
    def test_blender_required_false(self):
        with tempfile.TemporaryDirectory() as td:
            tp = _write_task(td, _base_task())
            sp = _write_state(td, _base_state())
            fd = os.path.join(td, 'frozen')
            freeze_bundle(tp, sp, fd)
            fb_path = os.path.join(fd, 'freeze_bundle.json')
            _, rec, _, _ = record_understanding(tp, fb_path, fd)
            assert rec['blender_required'] == False

    def test_spec_conflicts_default_false(self):
        with tempfile.TemporaryDirectory() as td:
            tp = _write_task(td, _base_task())
            sp = _write_state(td, _base_state())
            fd = os.path.join(td, 'frozen')
            freeze_bundle(tp, sp, fd)
            fb_path = os.path.join(fd, 'freeze_bundle.json')
            _, rec, _, _ = record_understanding(tp, fb_path, fd)
            assert rec['spec_conflicts_found'] == False

    def test_understood_by_is_claude(self):
        with tempfile.TemporaryDirectory() as td:
            tp = _write_task(td, _base_task())
            sp = _write_state(td, _base_state())
            fd = os.path.join(td, 'frozen')
            freeze_bundle(tp, sp, fd)
            fb_path = os.path.join(fd, 'freeze_bundle.json')
            _, rec, _, _ = record_understanding(tp, fb_path, fd)
            assert rec['understood_by'] == 'CLAUDE'
