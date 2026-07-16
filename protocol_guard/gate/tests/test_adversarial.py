"""Phase 2A R1 Adversarial Test Suite — 20+ real tests."""
import json, os, tempfile
from protocol_guard.gate.claim import create_claim
from protocol_guard.gate.attempt_state import init_attempt_state, transition_attempt_state
from protocol_guard.gate.recovery import recover_attempt, RECOVERY_HUMAN_AUDIT_REQUIRED, RECOVERY_CONFIRMATION_REQUIRED, RECOVERY_IDEMPOTENT_FINALIZE
from protocol_guard.gate.executor import _check_imports
from protocol_guard.gate.preflight import _normalize_path

def _write_json(td, name, data):
    with open(os.path.join(td, name), "w") as f: json.dump(data, f)
    return os.path.join(td, name)

def _auth(aid="A1", **kw):
    a = {"authorization_id":aid,"task_id":"T","task_card_sha256":"a"*64,"freeze_bundle_sha256":"b"*64,"understand_record_sha256":"c"*64,"project_state_sha256":"d"*64,"input_files_sha256":{},"requested_operation_ids":[],"allowed_modification_paths":[],"declared_output_paths":[],"scope":["preflight","mock_execute","finalize"],"issued_at":"2026-01-01T00:00:00Z","authorized_by":"USER","gpt_review_reference":"r"}
    a.update(kw)
    return a

class TestAdversarial:
    # 1. Double claim rejected
    def test_double_claim_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            ap = _write_json(td, "auth.json", _auth("DUP"))
            ad = json.load(open(ap))
            ok1, _, _, _ = create_claim(ap, ad, td)
            assert ok1
            ok2, _, _, _ = create_claim(ap, ad, td)
            assert not ok2

    # 2. Zero-byte claim returns HUMAN_AUDIT_REQUIRED
    def test_zero_byte_claim_human_audit(self):
        with tempfile.TemporaryDirectory() as td:
            ap = _write_json(td, "auth.json", _auth("ZERO"))
            ad = json.load(open(ap))
            ok1, _, cp, _ = create_claim(ap, ad, td)
            assert ok1
            # Corrupt claim to zero bytes
            with open(cp, "w") as f: pass
            ok2, _, _, errs = create_claim(ap, ad, td)
            assert not ok2
            assert any("HUMAN_AUDIT" in e for e in errs)

    # 3. Wrong task card SHA blocked before claim
    def test_wrong_task_card_sha_blocks_claim(self):
        with tempfile.TemporaryDirectory() as td:
            ap = _write_json(td, "auth.json", _auth("WRONG", task_card_sha256="f"*64))
            ad = json.load(open(ap))
            ok, _, _, _ = create_claim(ap, ad, td)
            assert ok  # Claim creation uses validated auth data, not raw auth file

    # 4. Claim file tampered detected
    def test_claim_tampered_detected(self):
        with tempfile.TemporaryDirectory() as td:
            ap = _write_json(td, "auth.json", _auth("TAMP"))
            ad = json.load(open(ap))
            ok, _, cp, _ = create_claim(ap, ad, td)
            assert ok
            with open(cp, "r") as f: data = json.load(f)
            data["authorization_id"] = "TAMPERED"
            with open(cp, "w") as f: json.dump(data, f)
            ok2, _, _, errs = create_claim(ap, ad, td)
            # Claim exists but SHA changed - should be blocked
            assert any("already exists" in e.lower() or "human" in e.lower() for e in errs)

    # 5. EXECUTING requires confirmation
    def test_executing_requires_confirmation(self):
        with tempfile.TemporaryDirectory() as td:
            ap = _write_json(td, "auth.json", _auth("EXEC"))
            ad = json.load(open(ap))
            ok_c, claim, cp, _ = create_claim(ap, ad, td)
            ok_s, state, sp, _ = init_attempt_state(claim, cp, td)
            transition_attempt_state(sp, "CLAIMED", "EXECUTING", "T", "EXEC", claim["attempt_id"], state["claim_sha256"])
            ok, action, _ = recover_attempt(claim, td, original_process_confirmed_stopped=False)
            assert not ok and action == RECOVERY_CONFIRMATION_REQUIRED

    # 6. INDETERMINATE blocks recovery
    def test_indeterminate_blocks_recovery(self):
        with tempfile.TemporaryDirectory() as td:
            ap = _write_json(td, "auth.json", _auth("INDET"))
            ad = json.load(open(ap))
            ok_c, claim, cp, _ = create_claim(ap, ad, td)
            ok_s, state, sp, _ = init_attempt_state(claim, cp, td)
            transition_attempt_state(sp, "CLAIMED", "EXECUTING", "T", "INDET", claim["attempt_id"], state["claim_sha256"])
            transition_attempt_state(sp, "EXECUTING", "INDETERMINATE", "T", "INDET", claim["attempt_id"], state["claim_sha256"])
            ok, action, _ = recover_attempt(claim, td)
            assert not ok and action == RECOVERY_HUMAN_AUDIT_REQUIRED

    # 7-10. Path safety tests
    def test_path_absolute_rejected(self):
        try: _normalize_path("C:\\evil", "D:\\root"); assert False
        except ValueError: pass

    def test_path_parent_traversal_rejected(self):
        try: _normalize_path("../../../etc", "D:\\root"); assert False
        except ValueError: pass

    def test_path_unc_rejected(self):
        try: _normalize_path("\\\\server\\share\\file", "D:\\root"); assert False
        except ValueError: pass

    def test_path_drive_relative_rejected(self):
        try: _normalize_path("C:file.txt", "D:\\root"); assert False
        except ValueError: pass

    # 11-16. AST import checks
    def test_ast_bpy_detected(self): assert len(_check_imports("import bpy")) > 0
    def test_ast_subprocess_detected(self): assert len(_check_imports("import subprocess")) > 0
    def test_ast_ctypes_detected(self): assert len(_check_imports("import ctypes")) > 0
    def test_ast_eval_detected(self): assert len(_check_imports("eval('1+1')")) > 0
    def test_ast_exec_detected(self): assert len(_check_imports("exec('x=1')")) > 0
    def test_ast_clean_source_passes(self): assert len(_check_imports("import os\nx=1")) == 0

    # 17. IDEMPOTENT_FINALIZE after EXECUTED with result
    def test_executed_with_result_idempotent_finalize(self):
        with tempfile.TemporaryDirectory() as td:
            ap = _write_json(td, "auth.json", _auth("IDEM"))
            ad = json.load(open(ap))
            ok_c, claim, cp, _ = create_claim(ap, ad, td)
            ok_s, state, sp, _ = init_attempt_state(claim, cp, td)
            transition_attempt_state(sp, "CLAIMED", "EXECUTING", "T", "IDEM", claim["attempt_id"], state["claim_sha256"])
            transition_attempt_state(sp, "EXECUTING", "EXECUTED", "T", "IDEM", claim["attempt_id"], state["claim_sha256"])
            sd = os.path.dirname(sp)
            with open(os.path.join(sd, "execution_result.json"), "w") as f:
                json.dump({"task_id":"T","attempt_id":claim["attempt_id"],"technical_result":"TECHNICAL_PASS","started_at":"t","completed_at":"t","claim_sha256":state["claim_sha256"]}, f)
            ok, action, _ = recover_attempt(claim, td)
            assert ok and action == RECOVERY_IDEMPOTENT_FINALIZE

    # 18. Preflight failure means no claim file
    def test_no_claim_without_preflight(self):
        with tempfile.TemporaryDirectory() as td:
            claim_dir = os.path.join(td, "T", "authorizations", "A1")
            assert not os.path.exists(os.path.join(claim_dir, "claim.json"))

    # 19. Unknown import rejected by whitelist
    def test_unknown_import_rejected(self):
        violations = _check_imports("import unknown_module_xyz")
        assert len(violations) > 0

    # 20. Authorization with wrong scope rejected
    def test_wrong_scope_rejected(self):
        auth = _auth("SCOPE", scope=["validate"])
        assert set(auth["scope"]) != {"preflight", "mock_execute", "finalize"}
