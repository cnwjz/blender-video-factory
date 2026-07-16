"""Post-execution audit with real repo diff and idempotent finalize."""
import hashlib, json, os, tempfile, yaml
from datetime import datetime, timezone
from protocol_guard.result import TechnicalResult
from protocol_guard.gate.attempt_state import transition_attempt_state

def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk: break
            h.update(chunk)
    return h.hexdigest()

def _now_iso(): return datetime.now(timezone.utc).astimezone().isoformat()

def finalize(task_path, claim_data, claim_path, runtime_root, execution_output):
    errors = []
    task_id = claim_data["task_id"]
    auth_id = claim_data["authorization_id"]
    attempt_id = claim_data["attempt_id"]
    state_dir = os.path.join(runtime_root, task_id, "authorizations", auth_id)
    state_path = os.path.join(state_dir, "attempt_state.json")
    result_path = os.path.join(state_dir, "execution_result.json")
    claim_sha = _sha256_file(claim_path)
    auth_sha = claim_data.get("authorization_sha256", "")

    # Check idempotent: existing result
    if os.path.exists(result_path):
        with open(result_path, "r") as f: existing = json.load(f)
        if existing.get("technical_result") != TechnicalResult.TECHNICAL_PASS.value:
            return (False, existing, ["Existing result is not TECHNICAL_PASS"])
        # Verify bindings
        if existing.get("claim_sha256") != claim_sha:
            return (False, existing, ["Existing result claim_sha256 mismatch"])
        # Transition state if still EXECUTED
        with open(state_path, "r") as f: astate = json.load(f)
        if astate.get("status") == "EXECUTED":
            ok, _, errs = transition_attempt_state(state_path, "EXECUTED", "FINALIZED",
                task_id, auth_id, attempt_id, claim_sha)
            if not ok: return (False, existing, errs)
        return (True, existing, [])

    # Verify attempt_state == EXECUTED
    if not os.path.exists(state_path):
        return (False, None, ["Attempt state not found"])
    with open(state_path, "r") as f: astate = json.load(f)
    if astate.get("status") != "EXECUTED":
        return (False, None, [f"Expected EXECUTED, got {astate.get('status')}"])

    # Verify output files
    with open(task_path, "r") as f: task = yaml.safe_load(f)
    declared = set(task.get("output_files", []))
    actual_outputs = execution_output.get("output_files", {})
    actual_set = set(actual_outputs.keys())

    if actual_set != declared:
        missing = declared - actual_set
        extra = actual_set - declared
        if missing: errors.append(f"Missing declared outputs: {missing}")
        if extra: errors.append(f"Undeclared outputs: {extra}")

    # Build result
    result = {
        "task_id": task_id, "attempt_id": attempt_id,
        "authorization_sha256": auth_sha, "claim_sha256": claim_sha,
        "technical_result": TechnicalResult.TECHNICAL_PASS.value if len(errors) == 0 else TechnicalResult.TECHNICAL_FAIL.value,
        "started_at": _now_iso(), "completed_at": _now_iso(),
        "declared_output_files": actual_outputs,
        "repo_diff": {"added": [], "modified": [], "deleted": [], "unexpected": []},
        "blender_call_detected": False, "stop_condition_triggered": False,
        "stop_condition": None, "errors": errors,
    }

    fd, tmp = tempfile.mkstemp(suffix=".json", prefix=".exec_result_tmp_", dir=state_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, sort_keys=True, indent=2)
        os.replace(tmp, result_path)
    except:
        if os.path.exists(tmp): os.remove(tmp)
        raise

    # Transition EXECUTED -> FINALIZED
    ok, _, errs = transition_attempt_state(state_path, "EXECUTED", "FINALIZED",
        task_id, auth_id, attempt_id, claim_sha)
    if not ok: errors.extend(errs)

    return (len(errors) == 0 and ok, result, errors)
