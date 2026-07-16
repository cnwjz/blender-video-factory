"""Test atomic attempt state transitions."""
import json, os, tempfile
from protocol_guard.gate.claim import create_claim
from protocol_guard.gate.attempt_state import init_attempt_state, transition_attempt_state, atomic_write_state

def _write_json(td, name, data):
    p = os.path.join(td, name)
    with open(p, "w") as f: json.dump(data, f)
    return p

def _make_auth(td, aid="A1"):
    auth = {"authorization_id":aid,"task_id":"T","task_card_sha256":"a"*64,"freeze_bundle_sha256":"b"*64,"understand_record_sha256":"c"*64,"project_state_sha256":"d"*64,"input_files_sha256":{},"requested_operation_ids":[],"allowed_modification_paths":[],"declared_output_paths":[],"scope":["preflight","mock_execute","finalize"],"issued_at":"2026-01-01T00:00:00Z","authorized_by":"USER","gpt_review_reference":"r"}
    return _write_json(td, "auth.json", auth)

class TestAttemptState:
    def test_init(self):
        with tempfile.TemporaryDirectory() as td:
            ap = _make_auth(td)
            ok_c, claim, cpath, _ = create_claim(ap, json.load(open(ap,"r")), td)
            assert ok_c
            ok, state, spath, errs = init_attempt_state(claim, cpath, td)
            assert ok
            assert state["status"] == "CLAIMED"

    def test_valid_transitions(self):
        with tempfile.TemporaryDirectory() as td:
            ap = _make_auth(td)
            ok_c, claim, cpath, _ = create_claim(ap, json.load(open(ap,"r")), td)
            ok_s, state, spath, _ = init_attempt_state(claim, cpath, td)
            ok1, s1, _ = transition_attempt_state(spath, "CLAIMED", "EXECUTING", "T", "A1", claim["attempt_id"], state["claim_sha256"])
            assert ok1 and s1["status"] == "EXECUTING"
            ok2, s2, _ = transition_attempt_state(spath, "EXECUTING", "EXECUTED", "T", "A1", claim["attempt_id"], state["claim_sha256"])
            assert ok2 and s2["status"] == "EXECUTED"

    def test_invalid_transition_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            ap = _make_auth(td)
            ok_c, claim, cpath, _ = create_claim(ap, json.load(open(ap,"r")), td)
            ok_s, state, spath, _ = init_attempt_state(claim, cpath, td)
            ok, _, _ = transition_attempt_state(spath, "CLAIMED", "FINALIZED", "T", "A1", claim["attempt_id"], state["claim_sha256"])
            assert not ok

    def test_wrong_status_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            ap = _make_auth(td)
            ok_c, claim, cpath, _ = create_claim(ap, json.load(open(ap,"r")), td)
            ok_s, state, spath, _ = init_attempt_state(claim, cpath, td)
            ok, _, _ = transition_attempt_state(spath, "EXECUTING", "EXECUTED", "T", "A1", claim["attempt_id"], state["claim_sha256"])
            assert not ok

    def test_indeterminate_blocks_all(self):
        with tempfile.TemporaryDirectory() as td:
            ap = _make_auth(td, "BLK")
            ok_c, claim, cpath, _ = create_claim(ap, json.load(open(ap,"r")), td)
            ok_s, state, spath, _ = init_attempt_state(claim, cpath, td)
            transition_attempt_state(spath, "CLAIMED", "EXECUTING", "T", "BLK", claim["attempt_id"], state["claim_sha256"])
            transition_attempt_state(spath, "EXECUTING", "INDETERMINATE", "T", "BLK", claim["attempt_id"], state["claim_sha256"])
            ok, _, _ = transition_attempt_state(spath, "INDETERMINATE", "FINALIZED", "T", "BLK", claim["attempt_id"], state["claim_sha256"])
            assert not ok

    def test_executed_to_finalized(self):
        with tempfile.TemporaryDirectory() as td:
            ap = _make_auth(td, "FIN")
            ok_c, claim, cpath, _ = create_claim(ap, json.load(open(ap,"r")), td)
            ok_s, state, spath, _ = init_attempt_state(claim, cpath, td)
            transition_attempt_state(spath, "CLAIMED", "EXECUTING", "T", "FIN", claim["attempt_id"], state["claim_sha256"])
            transition_attempt_state(spath, "EXECUTING", "EXECUTED", "T", "FIN", claim["attempt_id"], state["claim_sha256"])
            ok, s, _ = transition_attempt_state(spath, "EXECUTED", "FINALIZED", "T", "FIN", claim["attempt_id"], state["claim_sha256"])
            assert ok and s["status"] == "FINALIZED"
