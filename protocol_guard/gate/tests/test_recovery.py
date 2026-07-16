"""Test crash recovery logic."""
import json, os, tempfile
from protocol_guard.gate.claim import create_claim
from protocol_guard.gate.attempt_state import init_attempt_state, transition_attempt_state
from protocol_guard.gate.recovery import recover_attempt, RECOVERY_RETRY_PREFLIGHT, RECOVERY_RETRY_EXECUTE, RECOVERY_IDEMPOTENT_FINALIZE, RECOVERY_DONE, RECOVERY_HUMAN_AUDIT_REQUIRED, RECOVERY_CONFIRMATION_REQUIRED

def _write_json(td, name, data):
    p = os.path.join(td, name)
    with open(p, "w") as f: json.dump(data, f)
    return p

class TestRecovery:
    def test_no_claim_retry_preflight(self):
        with tempfile.TemporaryDirectory() as td:
            ok, action, _ = recover_attempt(None, td)
            assert ok
            assert action == RECOVERY_RETRY_PREFLIGHT

    def test_claimed_retry_execute(self):
        with tempfile.TemporaryDirectory() as td:
            auth = {"authorization_id":"A1","task_id":"T","task_card_sha256":"a"*64,"freeze_bundle_sha256":"b"*64,"understand_record_sha256":"c"*64,"project_state_sha256":"d"*64,"input_files_sha256":{},"requested_operation_ids":[],"allowed_modification_paths":[],"declared_output_paths":[],"scope":["preflight","mock_execute","finalize"],"issued_at":"2026-01-01T00:00:00Z","authorized_by":"USER","gpt_review_reference":"r"}
            ap = _write_json(td, "auth.json", auth)
            ok_c, claim, cpath, _ = create_claim(ap, json.load(open(ap,"r")), td)
            assert ok_c
            init_attempt_state(claim, cpath, td)
            ok, action, _ = recover_attempt(claim, td)
            assert ok
            assert action == RECOVERY_RETRY_EXECUTE

    def test_executing_requires_confirmation(self):
        with tempfile.TemporaryDirectory() as td:
            auth = {"authorization_id":"A2","task_id":"T","task_card_sha256":"a"*64,"freeze_bundle_sha256":"b"*64,"understand_record_sha256":"c"*64,"project_state_sha256":"d"*64,"input_files_sha256":{},"requested_operation_ids":[],"allowed_modification_paths":[],"declared_output_paths":[],"scope":["preflight","mock_execute","finalize"],"issued_at":"2026-01-01T00:00:00Z","authorized_by":"USER","gpt_review_reference":"r"}
            ap = _write_json(td, "auth.json", auth)
            ok_c, claim, cpath, _ = create_claim(ap, json.load(open(ap,"r")), td)
            ok_s, state, spath, _ = init_attempt_state(claim, cpath, td)
            transition_attempt_state(spath, "CLAIMED", "EXECUTING",
                "T", "A2", claim["attempt_id"], state["claim_sha256"])
            ok, action, detail = recover_attempt(claim, td, original_process_confirmed_stopped=False)
            assert not ok
            assert action == RECOVERY_CONFIRMATION_REQUIRED

    def test_finalized_returns_done(self):
        with tempfile.TemporaryDirectory() as td:
            auth = {"authorization_id":"A3","task_id":"T","task_card_sha256":"a"*64,"freeze_bundle_sha256":"b"*64,"understand_record_sha256":"c"*64,"project_state_sha256":"d"*64,"input_files_sha256":{},"requested_operation_ids":[],"allowed_modification_paths":[],"declared_output_paths":[],"scope":["preflight","mock_execute","finalize"],"issued_at":"2026-01-01T00:00:00Z","authorized_by":"USER","gpt_review_reference":"r"}
            ap = _write_json(td, "auth.json", auth)
            ok_c, claim, cpath, _ = create_claim(ap, json.load(open(ap,"r")), td)
            ok_s, state, spath, _ = init_attempt_state(claim, cpath, td)
            transition_attempt_state(spath, "CLAIMED", "EXECUTING", "T", "A3", claim["attempt_id"], state["claim_sha256"])
            transition_attempt_state(spath, "EXECUTING", "EXECUTED", "T", "A3", claim["attempt_id"], state["claim_sha256"])
            transition_attempt_state(spath, "EXECUTED", "FINALIZED", "T", "A3", claim["attempt_id"], state["claim_sha256"])
            ok, action, _ = recover_attempt(claim, td)
            assert ok
            assert action == RECOVERY_DONE

    def test_no_claim_retry(self):
        ok, action, _ = recover_attempt(None, '')
        assert ok and action == RECOVERY_RETRY_PREFLIGHT
