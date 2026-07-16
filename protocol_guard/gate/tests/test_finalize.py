"""Test finalize stage."""
import json, os, tempfile, yaml
from protocol_guard.gate.claim import create_claim
from protocol_guard.gate.attempt_state import init_attempt_state, transition_attempt_state
from protocol_guard.gate.finalize import finalize

def _write_json(td, name, data):
    p = os.path.join(td, name)
    with open(p, "w") as f: json.dump(data, f)
    return p

class TestFinalize:
    def test_finalize_produces_result(self):
        with tempfile.TemporaryDirectory() as td:
            auth = {"authorization_id":"A1","task_id":"T","task_card_sha256":"a"*64,"freeze_bundle_sha256":"b"*64,"understand_record_sha256":"c"*64,"project_state_sha256":"d"*64,"input_files_sha256":{},"requested_operation_ids":[],"allowed_modification_paths":[],"declared_output_paths":[],"scope":["preflight","mock_execute","finalize"],"issued_at":"2026-01-01T00:00:00Z","authorized_by":"USER","gpt_review_reference":"r"}
            ap = _write_json(td, "auth.json", auth)
            ok_c, claim, cpath, _ = create_claim(ap, json.load(open(ap,"r")), td)
            assert ok_c
            ok_s, state, spath, _ = init_attempt_state(claim, cpath, td)
            assert ok_s
            # Transition to EXECUTED (simulating executor)
            ok_t, _, _ = transition_attempt_state(spath, "CLAIMED", "EXECUTING",
                "T", "A1", claim["attempt_id"], state["claim_sha256"])
            assert ok_t
            ok_t2, _, _ = transition_attempt_state(spath, "EXECUTING", "EXECUTED",
                "T", "A1", claim["attempt_id"], state["claim_sha256"])
            assert ok_t2
            # Now finalize
            task_path = os.path.join(td, "task.yaml")
            with open(task_path, "w") as f:
                yaml.dump({"task_id":"T","output_files":["out.txt"],"allowed_modifications":[],"input_files":[]}, f)
            exec_out = {"output_files": {"out.txt": "e"*64}, "workspace_dir": td}
            ok_f, result, errs = finalize(task_path, claim, cpath, td, exec_out)
            assert ok_f, f"Finalize failed: {errs}"
            assert result["technical_result"] == "TECHNICAL_PASS"
            assert os.path.exists(os.path.join(td, "T", "authorizations", "A1", "execution_result.json"))

    def test_result_contains_claim_sha(self):
        with tempfile.TemporaryDirectory() as td:
            auth = {'authorization_id':'A4','task_id':'T','task_card_sha256':'a'*64,'freeze_bundle_sha256':'b'*64,'understand_record_sha256':'c'*64,'project_state_sha256':'d'*64,'input_files_sha256':{},'requested_operation_ids':[],'allowed_modification_paths':[],'declared_output_paths':[],'scope':['preflight','mock_execute','finalize'],'issued_at':'2026-01-01T00:00:00Z','authorized_by':'USER','gpt_review_reference':'r'}
            ap = _write_json(td, 'auth.json', auth)
            ok_c, claim, cpath, _ = create_claim(ap, json.load(open(ap,"r")), td)
            ok_s, state, spath, _ = init_attempt_state(claim, cpath, td)
            transition_attempt_state(spath, 'CLAIMED', 'EXECUTING', 'T', 'A4', claim['attempt_id'], state['claim_sha256'])
            transition_attempt_state(spath, 'EXECUTING', 'EXECUTED', 'T', 'A4', claim['attempt_id'], state['claim_sha256'])
            task_path = os.path.join(td, 'task.yaml')
            with open(task_path, 'w') as f: yaml.dump({'task_id':'T','output_files':[],'allowed_modifications':[],'input_files':[]}, f)
            ok_f, result, _ = finalize(task_path, claim, cpath, td, {'output_files':{},'workspace_dir':td})
            assert ok_f and result['claim_sha256'] is not None
    def test_missing_declared_output_fails(self):
        with tempfile.TemporaryDirectory() as td:
            auth = {"authorization_id":"A5","task_id":"T","task_card_sha256":"a"*64,"freeze_bundle_sha256":"b"*64,"understand_record_sha256":"c"*64,"project_state_sha256":"d"*64,"input_files_sha256":{},"requested_operation_ids":[],"allowed_modification_paths":[],"declared_output_paths":[],"scope":["preflight","mock_execute","finalize"],"issued_at":"2026-01-01T00:00:00Z","authorized_by":"USER","gpt_review_reference":"r"}
            ap = _write_json(td, "auth.json", auth)
            ad = json.load(open(ap))
            ok_c, claim, cp, _ = create_claim(ap, ad, td)
            ok_s, state, sp, _ = init_attempt_state(claim, cp, td)
            transition_attempt_state(sp, "CLAIMED", "EXECUTING", "T", "A5", claim["attempt_id"], state["claim_sha256"])
            transition_attempt_state(sp, "EXECUTING", "EXECUTED", "T", "A5", claim["attempt_id"], state["claim_sha256"])
            tp = os.path.join(td, "task.yaml")
            with open(tp, "w") as f: yaml.dump({"task_id":"T","output_files":["missing.txt"],"allowed_modifications":[],"input_files":[]}, f)
            ok_f, result, _ = finalize(tp, claim, cp, td, {"output_files":{},"workspace_dir":td})
            assert not ok_f or result["technical_result"] == "TECHNICAL_FAIL"


