"""Full 7-stage integration test with mock pipeline."""
import json, os, tempfile, yaml
from protocol_guard.gate.freeze_bundle import freeze_bundle
from protocol_guard.gate.understand import record_understanding
from protocol_guard.gate.authorize import validate_authorization
from protocol_guard.gate.claim import create_claim
from protocol_guard.gate.attempt_state import init_attempt_state, transition_attempt_state
from protocol_guard.gate.preflight import preflight
from protocol_guard.gate.executor import mock_execute
from protocol_guard.gate.finalize import finalize
from protocol_guard.task_schema import validate_task_card

def _write_task(td, data):
    p = os.path.join(td, "task.yaml")
    with open(p, "w") as f: yaml.dump(data, f)
    return p

def _write_state(td, data):
    p = os.path.join(td, "state.yaml")
    with open(p, "w") as f: yaml.dump(data, f)
    return p

def _write_json(td, name, data):
    p = os.path.join(td, name)
    with open(p, "w") as f: json.dump(data, f)
    return p

class TestIntegration:
    def test_full_pipeline(self):
        with tempfile.TemporaryDirectory() as td:
            # Fixtures
            task = {"task_id":"INT_TEST","task_card_version":2,"protocol_version":"v1.0","execution_mode":"confirm_then_execute","task_type":"PROTOCOL_MAINTENANCE","project_state_file":"state.yaml","input_files":["in.txt"],"output_files":["out.txt"],"primary_goal":"Integration test","primary_variable":"x","dependent_variables":[],"fixed_params":{},"locked_items":[],"allowed_modifications":[],"forbidden_modifications":[],"preflight_checks":[],"technical_pass_conditions":[],"visual_intent":"","visual_forbidden":"","evidence_required":[],"upload_dir":"d","upload_files":["result.txt"],"stop_conditions":[],"state_patch_requested":None}
            state = {"protocol_version":"v1.0","project_id":"int","workflow_phase":"code_guard_phase_1_locked","scene_phase":"paused","phase_approved":True,"project_work_paused":True,"last_task_id":"T","last_task_card_sha256":None,"last_technical_result":"TECHNICAL_PASS","evidence_status":"VALID","evidence_sha256":None,"output_files":[],"last_execution_time":"2026-07-15T15:00:00+08:00","locked_assets":[],"unlocked_assets":[],"diagnostic_only_outputs":[],"pending_review":None,"blocked_operations":[],"failed_paths":[],"change_log":[]}

            # Create input file
            with open(os.path.join(td, "in.txt"), "w") as f: f.write("test")

            # 1. validate
            is_valid, errs = validate_task_card(task)
            assert is_valid, f"validate failed: {errs}"

            tp = _write_task(td, task)
            sp = _write_state(td, state)

            # 2. freeze
            fd = os.path.join(td, "frozen")
            ok_fb, bundle, fb_sha, errs_fb = freeze_bundle(tp, sp, fd)
            assert ok_fb, f"freeze failed: {errs_fb}"
            fb_path = os.path.join(fd, "freeze_bundle.json")
            assert os.path.exists(fb_path)

            # 3. understand
            ok_ur, rec, ur_sha, errs_ur = record_understanding(tp, fb_path, fd)
            assert ok_ur, f"understand failed: {errs_ur}"
            ur_path = os.path.join(fd, "understand.json")

            # 4. authorize (create validation fixture)
            import hashlib
            inp_sha = hashlib.sha256(open(os.path.join(td, "in.txt"), "rb").read()).hexdigest()
            auth = {"authorization_id":"INT_A1","task_id":"INT_TEST","task_card_sha256":bundle["task_card_raw_sha256"],"freeze_bundle_sha256":fb_sha,"understand_record_sha256":ur_sha,"project_state_sha256":bundle["project_state_canonical_sha256"],"input_files_sha256":{"in.txt": inp_sha},"requested_operation_ids":[],"allowed_modification_paths":[],"declared_output_paths":["out.txt"],"scope":["preflight","mock_execute","finalize"],"issued_at":"2026-01-01T00:00:00Z","authorized_by":"USER","gpt_review_reference":"r"}
            ap = _write_json(td, "auth.json", auth)
            ok_auth, auth_data, errs_auth = validate_authorization(ap, fb_path, ur_path, tp, sp)
            assert ok_auth, f"auth failed: {errs_auth}"

            # 5. preflight
            cleared, errs_pf = preflight(tp, sp, fb_path, ap, td)
            assert cleared, f"preflight failed: {errs_pf}"

            # 6. claim
            ok_cl, claim, cpath, errs_cl = create_claim(ap, auth_data, td)
            assert ok_cl, f"claim failed: {errs_cl}"

            # 7. attempt state init
            ok_as, astate, aspath, errs_as = init_attempt_state(claim, cpath, td)
            assert ok_as, f"attempt init failed: {errs_as}"
            assert astate["status"] == "CLAIMED"

            # Transition to EXECUTING -> EXECUTED
            ok_t1, _, _ = transition_attempt_state(aspath, "CLAIMED", "EXECUTING",
                "INT_TEST", "INT_A1", claim["attempt_id"], astate["claim_sha256"])
            assert ok_t1
            ok_t2, _, _ = transition_attempt_state(aspath, "EXECUTING", "EXECUTED",
                "INT_TEST", "INT_A1", claim["attempt_id"], astate["claim_sha256"])
            assert ok_t2

            # 8. execute
            ok_ex, result_ex, errs_ex = mock_execute(tp, os.path.join(td, "ws"))
            assert ok_ex, f"execute failed: {errs_ex}"

            # 9. finalize
            ok_fn, result_fn, errs_fn = finalize(tp, claim, cpath, td, result_ex if ok_ex else {"output_files":{},"workspace_dir":td})
            assert ok_fn, f"finalize failed: {errs_fn}"
            assert result_fn["technical_result"] == "TECHNICAL_PASS"

            # Verify hash chain
            assert result_fn["claim_sha256"] is not None
            assert "attempt_id" in result_fn
            print(f"Integration pipeline: 7 stages completed, TECHNICAL_PASS")
