"""Crash recovery logic for Phase 2A gate."""

import json, os


RECOVERY_RETRY_PREFLIGHT = "RETRY_PREFLIGHT"
RECOVERY_RETRY_EXECUTE = "RETRY_EXECUTE"
RECOVERY_IDEMPOTENT_FINALIZE = "IDEMPOTENT_FINALIZE"
RECOVERY_DONE = "DONE"
RECOVERY_HUMAN_AUDIT_REQUIRED = "HUMAN_AUDIT_REQUIRED"
RECOVERY_CONFIRMATION_REQUIRED = "RECOVERY_CONFIRMATION_REQUIRED"


def recover_attempt(claim_data, runtime_root, original_process_confirmed_stopped=False):
    """Determine the recovery action for an existing claim.

    Args:
        claim_data: claim dict (or None if no claim exists)
        runtime_root: root directory for runtime artifacts
        original_process_confirmed_stopped: caller must explicitly confirm

    Returns:
        (recoverable: bool, action: str, detail: str)
    """
    if claim_data is None:
        return (True, RECOVERY_RETRY_PREFLIGHT, "No claim exists. Safe to retry from preflight.")

    task_id = claim_data["task_id"]
    auth_id = claim_data["authorization_id"]
    state_dir = os.path.join(runtime_root, task_id, "authorizations", auth_id)
    state_path = os.path.join(state_dir, "attempt_state.json")

    if not os.path.exists(state_path):
        return (True, RECOVERY_RETRY_EXECUTE,
                "Claim exists but no attempt state. Can begin execution with this claim.")

    with open(state_path, "r", encoding="utf-8") as f:
        attempt = json.load(f)

    status = attempt.get("status", "UNKNOWN")

    if status == "CLAIMED":
        return (True, RECOVERY_RETRY_EXECUTE, "Claimed but not started. Can execute with same claim.")
    elif status == "EXECUTING":
        if not original_process_confirmed_stopped:
            return (False, RECOVERY_CONFIRMATION_REQUIRED,
                    "Attempt is EXECUTING. Caller must confirm original process has stopped.")
        # Check if complete execution result exists
        result_path = os.path.join(state_dir, "execution_result.json")
        if not os.path.exists(result_path):
            from protocol_guard.gate.attempt_state import transition_attempt_state, read_attempt_state
            transition_attempt_state(
                state_path, "EXECUTING", "INDETERMINATE",
                task_id, auth_id, attempt["attempt_id"], attempt.get("claim_sha256", "")
            )
            return (False, RECOVERY_HUMAN_AUDIT_REQUIRED,
                    "EXECUTING with no complete result. Transitioned to INDETERMINATE. Human audit required.")
        return (False, RECOVERY_HUMAN_AUDIT_REQUIRED,
                "EXECUTING but complete result found. Inconsistent state. Human audit required.")
    elif status == "EXECUTED":
        result_path = os.path.join(state_dir, "execution_result.json")
        if not os.path.exists(result_path):
            # Transition to INDETERMINATE
            from protocol_guard.gate.attempt_state import transition_attempt_state
            transition_attempt_state(
                state_path, "EXECUTED", "INDETERMINATE",
                task_id, auth_id, attempt["attempt_id"], attempt.get("claim_sha256", "")
            )
            return (False, RECOVERY_HUMAN_AUDIT_REQUIRED,
                    "Marked EXECUTED but no result file. Transitioned to INDETERMINATE.")
        return (True, RECOVERY_IDEMPOTENT_FINALIZE,
                "Execution complete with result. Can run idempotent finalize.")
    elif status == "FINALIZED":
        return (True, RECOVERY_DONE, "Already finalized. No action needed.")
    elif status == "INDETERMINATE":
        return (False, RECOVERY_HUMAN_AUDIT_REQUIRED,
                "Attempt is INDETERMINATE. Human inspection required. No automatic action permitted.")
    else:
        return (False, RECOVERY_HUMAN_AUDIT_REQUIRED, f"Unknown status: {status}")
