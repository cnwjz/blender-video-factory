"""Mutable attempt state with atomic transitions via tempfile+revalidate+os.replace."""

import hashlib, json, os, tempfile


VALID_TRANSITIONS = {
    "CLAIMED": {"EXECUTING"},
    "EXECUTING": {"EXECUTED", "INDETERMINATE"},
    "EXECUTED": {"FINALIZED", "INDETERMINATE"},
    "FINALIZED": set(),
    "INDETERMINATE": set(),
}


def _load_schema():
    schema_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "schemas", "attempt_state.schema.json"
    )
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk: break
            h.update(chunk)
    return h.hexdigest()


def _now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).astimezone().isoformat()


def init_attempt_state(claim_data, claim_path, runtime_root):
    """Create initial attempt_state.json after successful claim.

    Returns:
        (success: bool, state_data: dict|None, state_path: str|None, errors: list[str])
    """
    import jsonschema
    schema = _load_schema()
    task_id = claim_data["task_id"]
    auth_id = claim_data["authorization_id"]

    state_dir = os.path.join(runtime_root, task_id, "authorizations", auth_id)
    os.makedirs(state_dir, exist_ok=True)
    state_path = os.path.join(state_dir, "attempt_state.json")

    if os.path.exists(state_path):
        return (False, None, state_path, ["attempt_state.json already exists"])

    claim_sha = _sha256_file(claim_path)
    state_data = {
        "task_id": task_id,
        "authorization_id": auth_id,
        "authorization_sha256": claim_data["authorization_sha256"],
        "attempt_id": claim_data["attempt_id"],
        "claim_sha256": claim_sha,
        "status": "CLAIMED",
        "status_changed_at": _now_iso(),
        "process_id": os.getpid(),
    }

    try:
        jsonschema.validate(instance=state_data, schema=schema)
    except jsonschema.ValidationError as e:
        return (False, None, None, [f"Attempt state schema violation: {e.message}"])

    ok, _, errs = atomic_write_state(state_data, state_path)
    return (ok, state_data if ok else None, state_path, errs)


def transition_attempt_state(state_path, expected_status, new_status, task_id, auth_id, attempt_id, claim_sha):
    """Atomic state transition: read→validate→write temp→re-read→validate→os.replace.

    Returns:
        (success: bool, new_state: dict|None, errors: list[str])
    """
    import jsonschema
    schema = _load_schema()
    errors = []

    if not os.path.exists(state_path):
        return (False, None, [f"Attempt state not found: {state_path}"])

    # Read and validate current state
    with open(state_path, "r", encoding="utf-8") as f:
        current = json.load(f)

    if current.get("status") != expected_status:
        errors.append(
            f"Expected status '{expected_status}' but current is '{current.get('status')}'"
        )

    # Verify identity fields unchanged
    for field, expected in [("task_id", task_id), ("authorization_id", auth_id),
                             ("attempt_id", attempt_id), ("claim_sha256", claim_sha)]:
        if current.get(field) != expected:
            errors.append(f"Identity field '{field}' mismatch: expected={expected}, got={current.get(field)}")

    if errors:
        return (False, None, errors)

    # Validate transition
    allowed = VALID_TRANSITIONS.get(expected_status, set())
    if new_status not in allowed:
        errors.append(f"Invalid transition: {expected_status} -> {new_status}")
        return (False, None, errors)

    new_state = dict(current)
    new_state["status"] = new_status
    new_state["status_changed_at"] = _now_iso()
    new_state["process_id"] = os.getpid()

    try:
        jsonschema.validate(instance=new_state, schema=schema)
    except jsonschema.ValidationError as e:
        return (False, None, [f"New state schema violation: {e.message}"])

    return atomic_write_state(new_state, state_path)


def atomic_write_state(state_data, target_path):
    """Write state atomically: tempfile → re-read → validate → os.replace.

    Returns:
        (success: bool, final_state: dict|None, errors: list[str])
    """
    import jsonschema
    schema = _load_schema()
    errors = []
    target_dir = os.path.dirname(os.path.abspath(target_path))

    fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix=".attempt_state_tmp_", dir=target_dir)
    tmp_path_saved = tmp_path
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state_data, f, ensure_ascii=False, sort_keys=True, indent=2)
            f.flush()
            os.fsync(f.fileno())

        # Re-read and validate
        with open(tmp_path, "r", encoding="utf-8") as f:
            re_read = json.load(f)

        try:
            jsonschema.validate(instance=re_read, schema=schema)
        except jsonschema.ValidationError as e:
            return (False, None, [f"Re-read validation failed: {e.message}"])

        os.replace(tmp_path, target_path)
        tmp_path = None

        # Verify after replace
        with open(target_path, "r", encoding="utf-8") as f:
            final = json.load(f)
        return (True, final, [])

    except Exception as e:
        errors.append(f"Atomic write failed: {e}")
        return (False, None, errors)
    finally:
        if tmp_path is not None and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def read_attempt_state(claim_data, runtime_root):
    """Read current attempt state for a claim."""
    task_id = claim_data["task_id"]
    auth_id = claim_data["authorization_id"]
    state_path = os.path.join(runtime_root, task_id, "authorizations", auth_id, "attempt_state.json")
    if not os.path.exists(state_path):
        return None
    with open(state_path, "r", encoding="utf-8") as f:
        return json.load(f)
