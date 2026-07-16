"""Immutable authorization — validates ALL bindings."""
import hashlib, json, os, yaml
from protocol_guard.state.project_state import _sha256_file, _canonical_state_hash, load_state

def _load_schema():
    p = os.path.join(os.path.dirname(os.path.dirname(__file__)), "schemas", "authorization.schema.json")
    with open(p, "r") as f: return json.load(f)

def validate_authorization(auth_path, freeze_bundle_path, understand_path, task_path, state_path):
    import jsonschema
    schema = _load_schema()
    errors = []
    if not os.path.exists(auth_path): return (False, None, ["Auth file not found"])
    with open(auth_path, "r") as f: auth = json.load(f)
    try: jsonschema.validate(instance=auth, schema=schema)
    except jsonschema.ValidationError as e: return (False, None, [f"Schema: {e.message}"])

    # Check all SHA bindings
    for label, path, field in [
        ("freeze_bundle", freeze_bundle_path, "freeze_bundle_sha256"),
        ("understand", understand_path, "understand_record_sha256"),
        ("task_card", task_path, "task_card_sha256"),
    ]:
        if not os.path.exists(path): errors.append(f"{label} not found")
        else:
            a, e = _sha256_file(path), auth.get(field)
            if a != e: errors.append(f"{field} mismatch: auth={e}, actual={a}")

    if not os.path.exists(state_path): errors.append("state not found")
    else:
        state = load_state(state_path)
        a_ps, e_ps = _canonical_state_hash(state), auth.get("project_state_sha256")
        if a_ps != e_ps: errors.append(f"project_state_sha256 mismatch")

    with open(task_path, "r") as f: task = yaml.safe_load(f)
    auth_inputs = auth.get("input_files_sha256", {})
    state_dir = os.path.dirname(os.path.abspath(state_path))
    for inf in task.get("input_files", []):
        inf_abs = os.path.join(state_dir, inf)
        if not os.path.exists(inf_abs): errors.append(f"input not found: {inf}")
        else:
            a, e = _sha256_file(inf_abs), auth_inputs.get(inf)
            if a != e: errors.append(f"input SHA mismatch: {inf}")
    if set(auth_inputs.keys()) != set(task.get("input_files", [])):
        errors.append("input_files key set mismatch")

    scope = set(auth.get("scope", []))
    if scope != {"preflight", "mock_execute", "finalize"}:
        errors.append(f"scope must be [preflight, mock_execute, finalize]")

    for f in ["authorization_id", "task_id", "issued_at", "authorized_by", "gpt_review_reference"]:
        if not auth.get(f): errors.append(f"missing {f}")

    expires = auth.get("expires_at")
    if expires:
        from datetime import datetime
        try:
            if datetime.now(datetime.fromisoformat(expires).tzinfo) > datetime.fromisoformat(expires):
                errors.append(f"expired at {expires}")
        except: errors.append(f"invalid expires_at")

    return (len(errors) == 0, auth if len(errors) == 0 else None, errors)
