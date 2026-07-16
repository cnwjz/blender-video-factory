
"""Mandatory 7-stage single-task gate pipeline. No stage can be skipped."""

import json, os, shutil
from protocol_guard.task_schema import validate_task_file
from protocol_guard.state.project_state import load_state, validate_state

from protocol_guard.gate.freeze_bundle import freeze_bundle
from protocol_guard.gate.understand import record_understanding
from protocol_guard.gate.authorize import validate_authorization
from protocol_guard.gate.claim import create_claim
from protocol_guard.gate.attempt_state import init_attempt_state, transition_attempt_state
from protocol_guard.gate.preflight import preflight
from protocol_guard.gate.executor import mock_execute
from protocol_guard.gate.finalize import finalize
from protocol_guard.gate.recovery import recover_attempt, RECOVERY_RETRY_PREFLIGHT, RECOVERY_IDEMPOTENT_FINALIZE, RECOVERY_DONE


def run_single_task_gate(task_path, state_path, auth_path, runtime_root, workspace_dir):
    """Execute the full 7-stage gate pipeline.

    Returns: (success: bool, stage_results: dict, errors: list[str])
    """
    errors = []
    stages = {}

    os.makedirs(runtime_root, exist_ok=True)
    os.makedirs(workspace_dir, exist_ok=True)
    task_id = None

    # ── 1. validate ──
    is_valid, verrs = validate_task_file(task_path)
    stages["validate"] = {"ok": is_valid, "errors": verrs}
    if not is_valid:
        errors.extend(verrs)
        return (False, stages, errors)

    state_data = load_state(state_path)
    ok_state, serrs = validate_state(state_data)
    stages["validate_state"] = {"ok": ok_state, "errors": serrs}
    if not ok_state:
        errors.extend(serrs)
        return (False, stages, errors)

    import yaml
    with open(task_path, "r") as f:
        task_data = yaml.safe_load(f)
    task_id = task_data.get("task_id", "unknown")

    # ── 2. freeze ──
    fb_dir = os.path.join(runtime_root, task_id, "frozen")
    ok_fb, bundle, fb_sha, ferrs = freeze_bundle(task_path, state_path, fb_dir)
    stages["freeze"] = {"ok": ok_fb, "bundle_sha256": fb_sha, "errors": ferrs}
    if not ok_fb:
        errors.extend(ferrs)
        return (False, stages, errors)
    fb_path = os.path.join(fb_dir, "freeze_bundle.json")

    # ── 3. understand ──
    ok_ur, rec, ur_sha, uerrs = record_understanding(task_path, fb_path, fb_dir)
    stages["understand"] = {"ok": ok_ur, "record_sha256": ur_sha, "errors": uerrs}
    if not ok_ur:
        errors.extend(uerrs)
        return (False, stages, errors)
    ur_path = os.path.join(fb_dir, "understand.json")

    # ── 4. authorize ──
    ok_auth, auth_data, aerrs = validate_authorization(auth_path, fb_path, ur_path, task_path, state_path)
    stages["authorize"] = {"ok": ok_auth, "errors": aerrs}
    if not ok_auth:
        errors.extend(aerrs)
        return (False, stages, errors)

    # ── 5. preflight ──
    cleared, perrs = preflight(task_path, state_path, fb_path, auth_path, runtime_root)
    stages["preflight"] = {"cleared": cleared, "errors": perrs}
    if not cleared:
        errors.extend(perrs)
        return (False, stages, errors)

    # ── 6. claim + mock_execute ──
    ok_cl, claim_data, claim_path, clerrs = create_claim(auth_path, auth_data, runtime_root)
    stages["claim"] = {"ok": ok_cl, "errors": clerrs}
    if not ok_cl:
        errors.extend(clerrs)
        return (False, stages, errors)

    ok_as, astate, aspath, aserrs = init_attempt_state(claim_data, claim_path, runtime_root)
    stages["attempt_init"] = {"ok": ok_as, "errors": aserrs}
    if not ok_as:
        errors.extend(aserrs)
        return (False, stages, errors)

    # Transition CLAIMED -> EXECUTING
    ok_e1, _, e1errs = transition_attempt_state(aspath, "CLAIMED", "EXECUTING",
        task_id, auth_data["authorization_id"], claim_data["attempt_id"], astate["claim_sha256"])
    stages["attempt_executing"] = {"ok": ok_e1, "errors": e1errs}
    if not ok_e1:
        errors.extend(e1errs)
        return (False, stages, errors)

    # Execute
    ok_ex, exec_result, exerrs = mock_execute(task_path, workspace_dir)
    stages["execute"] = {"ok": ok_ex, "errors": exerrs}
    if not ok_ex:
        errors.extend(exerrs)
        return (False, stages, errors)

    # Transition EXECUTING -> EXECUTED
    ok_e2, _, e2errs = transition_attempt_state(aspath, "EXECUTING", "EXECUTED",
        task_id, auth_data["authorization_id"], claim_data["attempt_id"], astate["claim_sha256"])
    stages["attempt_executed"] = {"ok": ok_e2, "errors": e2errs}
    if not ok_e2:
        errors.extend(e2errs)
        return (False, stages, errors)

    # ── 7. finalize ──
    ok_fn, result_fn, fnerrs = finalize(task_path, claim_data, claim_path, runtime_root, exec_result)
    stages["finalize"] = {"ok": ok_fn, "errors": fnerrs}
    if not ok_fn:
        errors.extend(fnerrs)

    return (ok_fn and ok_ex and cleared, stages, errors)
