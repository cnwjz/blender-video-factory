"""Test authorization validation with real bound fixtures."""
import json, os, tempfile, yaml
from protocol_guard.gate.freeze_bundle import freeze_bundle
from protocol_guard.gate.understand import record_understanding
from protocol_guard.gate.authorize import validate_authorization

def _base_task(tid="AUTH_TEST"):
    return {"task_id":tid,"task_card_version":2,"protocol_version":"v1.0","execution_mode":"confirm_then_execute","task_type":"PROTOCOL_MAINTENANCE","project_state_file":"state.yaml","input_files":[],"output_files":["out.txt"],"primary_goal":"Test","primary_variable":"x","dependent_variables":[],"fixed_params":{},"locked_items":[],"allowed_modifications":[],"forbidden_modifications":[],"preflight_checks":[],"technical_pass_conditions":[],"visual_intent":"","visual_forbidden":"","evidence_required":[],"upload_dir":"d","upload_files":["out.txt"],"stop_conditions":[],"state_patch_requested":None}

def _base_state():
    return {"protocol_version":"v1.0","project_id":"auth","workflow_phase":"code_guard_phase_1_locked","scene_phase":"paused","phase_approved":True,"project_work_paused":True,"last_task_id":"T","last_task_card_sha256":None,"last_technical_result":"TECHNICAL_PASS","evidence_status":"VALID","evidence_sha256":None,"output_files":[],"last_execution_time":"2026-07-15T15:00:00+08:00","locked_assets":[],"unlocked_assets":[],"diagnostic_only_outputs":[],"pending_review":None,"blocked_operations":[],"failed_paths":[],"change_log":[]}

def _mk_auth(task_sha, fb_sha, ur_sha, ps_sha, **kw):
    a = {"authorization_id":"A1","task_id":"AUTH_TEST","task_card_sha256":task_sha,"freeze_bundle_sha256":fb_sha,"understand_record_sha256":ur_sha,"project_state_sha256":ps_sha,"input_files_sha256":{},"requested_operation_ids":[],"allowed_modification_paths":[],"declared_output_paths":[],"scope":["preflight","mock_execute","finalize"],"issued_at":"2026-01-01T00:00:00Z","authorized_by":"USER","gpt_review_reference":"r"}
    a.update(kw)
    return a

class TestAuthorizeReal:
    def test_all_bindings_valid(self):
        with tempfile.TemporaryDirectory() as td:
            tp = os.path.join(td, "task.yaml")
            sp = os.path.join(td, "state.yaml")
            with open(tp, "w") as f: yaml.dump(_base_task(), f)
            with open(sp, "w") as f: yaml.dump(_base_state(), f)
            fd = os.path.join(td, "frozen")
            ok_fb, bundle, fb_sha, _ = freeze_bundle(tp, sp, fd)
            assert ok_fb
            fb_path = os.path.join(fd, "freeze_bundle.json")
            ok_ur, rec, ur_sha, _ = record_understanding(tp, fb_path, fd)
            assert ok_ur
            ur_path = os.path.join(fd, "understand.json")
            auth = _mk_auth(bundle["task_card_raw_sha256"], fb_sha, ur_sha, bundle["project_state_canonical_sha256"])
            ap = os.path.join(td, "auth.json")
            with open(ap, "w") as f: json.dump(auth, f)
            ok, ad, errs = validate_authorization(ap, fb_path, ur_path, tp, sp)
            assert ok, f"Failed: {errs}"
            assert ad is not None

    def test_expired(self):
        with tempfile.TemporaryDirectory() as td:
            tp = os.path.join(td, "task.yaml")
            sp = os.path.join(td, "state.yaml")
            with open(tp, "w") as f: yaml.dump(_base_task(), f)
            with open(sp, "w") as f: yaml.dump(_base_state(), f)
            fd = os.path.join(td, "frozen")
            _, bundle, fb_sha, _ = freeze_bundle(tp, sp, fd)
            fb_path = os.path.join(fd, "freeze_bundle.json")
            _, rec, ur_sha, _ = record_understanding(tp, fb_path, fd)
            ur_path = os.path.join(fd, "understand.json")
            auth = _mk_auth(bundle["task_card_raw_sha256"], fb_sha, ur_sha, bundle["project_state_canonical_sha256"],
                           expires_at="2020-01-02T00:00:00Z")
            ap = os.path.join(td, "auth.json")
            with open(ap, "w") as f: json.dump(auth, f)
            ok, ad, errs = validate_authorization(ap, fb_path, ur_path, tp, sp)
            assert not ok

    def test_wrong_scope(self):
        with tempfile.TemporaryDirectory() as td:
            tp = os.path.join(td, "task.yaml")
            sp = os.path.join(td, "state.yaml")
            with open(tp, "w") as f: yaml.dump(_base_task(), f)
            with open(sp, "w") as f: yaml.dump(_base_state(), f)
            fd = os.path.join(td, "frozen")
            _, bundle, fb_sha, _ = freeze_bundle(tp, sp, fd)
            fb_path = os.path.join(fd, "freeze_bundle.json")
            _, rec, ur_sha, _ = record_understanding(tp, fb_path, fd)
            ur_path = os.path.join(fd, "understand.json")
            auth = _mk_auth(bundle["task_card_raw_sha256"], fb_sha, ur_sha, bundle["project_state_canonical_sha256"],
                           scope=["validate"])
            ap = os.path.join(td, "auth.json")
            with open(ap, "w") as f: json.dump(auth, f)
            ok, ad, errs = validate_authorization(ap, fb_path, ur_path, tp, sp)
            assert not ok

    def test_wrong_task_card_sha(self):
        with tempfile.TemporaryDirectory() as td:
            tp = os.path.join(td, "task.yaml")
            sp = os.path.join(td, "state.yaml")
            with open(tp, "w") as f: yaml.dump(_base_task(), f)
            with open(sp, "w") as f: yaml.dump(_base_state(), f)
            fd = os.path.join(td, "frozen")
            _, bundle, fb_sha, _ = freeze_bundle(tp, sp, fd)
            fb_path = os.path.join(fd, "freeze_bundle.json")
            _, rec, ur_sha, _ = record_understanding(tp, fb_path, fd)
            ur_path = os.path.join(fd, "understand.json")
            auth = _mk_auth("f"*64, fb_sha, ur_sha, bundle["project_state_canonical_sha256"])
            ap = os.path.join(td, "auth.json")
            with open(ap, "w") as f: json.dump(auth, f)
            ok, ad, errs = validate_authorization(ap, fb_path, ur_path, tp, sp)
            assert not ok

    def test_wrong_freeze_sha(self):
        with tempfile.TemporaryDirectory() as td:
            tp = os.path.join(td, "task.yaml")
            sp = os.path.join(td, "state.yaml")
            with open(tp, "w") as f: yaml.dump(_base_task(), f)
            with open(sp, "w") as f: yaml.dump(_base_state(), f)
            fd = os.path.join(td, "frozen")
            _, bundle, fb_sha, _ = freeze_bundle(tp, sp, fd)
            fb_path = os.path.join(fd, "freeze_bundle.json")
            _, rec, ur_sha, _ = record_understanding(tp, fb_path, fd)
            ur_path = os.path.join(fd, "understand.json")
            auth = _mk_auth(bundle["task_card_raw_sha256"], "f"*64, ur_sha, bundle["project_state_canonical_sha256"])
            ap = os.path.join(td, "auth.json")
            with open(ap, "w") as f: json.dump(auth, f)
            ok, ad, errs = validate_authorization(ap, fb_path, ur_path, tp, sp)
            assert not ok

    def test_wrong_understand_sha(self):
        with tempfile.TemporaryDirectory() as td:
            tp = os.path.join(td, "task.yaml")
            sp = os.path.join(td, "state.yaml")
            with open(tp, "w") as f: yaml.dump(_base_task(), f)
            with open(sp, "w") as f: yaml.dump(_base_state(), f)
            fd = os.path.join(td, "frozen")
            _, bundle, fb_sha, _ = freeze_bundle(tp, sp, fd)
            fb_path = os.path.join(fd, "freeze_bundle.json")
            _, rec, ur_sha, _ = record_understanding(tp, fb_path, fd)
            ur_path = os.path.join(fd, "understand.json")
            auth = _mk_auth(bundle["task_card_raw_sha256"], fb_sha, "f"*64, bundle["project_state_canonical_sha256"])
            ap = os.path.join(td, "auth.json")
            with open(ap, "w") as f: json.dump(auth, f)
            ok, ad, errs = validate_authorization(ap, fb_path, ur_path, tp, sp)
            assert not ok

    def test_missing_file(self):
        ok, _, errs = validate_authorization("/nonexistent", "/x", "/x", "/x", "/x")
        assert not ok
