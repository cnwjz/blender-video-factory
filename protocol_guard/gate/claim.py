"""Immutable claim — requires validated auth data."""
import hashlib, json, os, uuid

def _load_schema():
    p = os.path.join(os.path.dirname(os.path.dirname(__file__)), "schemas", "claim.schema.json")
    with open(p, "r") as f: return json.load(f)

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

def create_claim(authorization_path, validated_auth_data, runtime_root):
    import jsonschema
    schema = _load_schema()
    if validated_auth_data is None:
        return (False, None, None, ["create_claim requires validated authorization data from validate_authorization"])

    task_id = validated_auth_data["task_id"]
    auth_id = validated_auth_data["authorization_id"]
    attempt_id = str(uuid.uuid4())

    if not os.path.exists(authorization_path):
        return (False, None, None, ["Authorization file not found"])
    auth_sha = _sha256_file(authorization_path)

    claim_data = {
        "authorization_id": auth_id, "authorization_sha256": auth_sha,
        "attempt_id": attempt_id, "task_id": task_id,
        "claimed_at": _now_iso(), "process_id": os.getpid(),
    }

    try: jsonschema.validate(instance=claim_data, schema=schema)
    except jsonschema.ValidationError as e: return (False, None, None, [f"Schema: {e.message}"])

    claim_dir = os.path.join(runtime_root, task_id, "authorizations", auth_id)
    os.makedirs(claim_dir, exist_ok=True)
    claim_path = os.path.join(claim_dir, "claim.json")

    try:
        with open(claim_path, "x", encoding="utf-8") as f:
            json.dump(claim_data, f, ensure_ascii=False, sort_keys=True, indent=2)
            f.flush(); os.fsync(f.fileno())
    except FileExistsError:
        try:
            with open(claim_path, "r") as f: existing = json.load(f)
            jsonschema.validate(instance=existing, schema=schema)
            if os.path.getsize(claim_path) == 0:
                return (False, None, claim_path, ["HUMAN_AUDIT_REQUIRED: Zero-byte claim file exists"])
            return (False, None, claim_path, [f"Claim already exists for {auth_id}"])
        except (json.JSONDecodeError, jsonschema.ValidationError):
            return (False, None, claim_path, ["HUMAN_AUDIT_REQUIRED: Corrupted claim file. Manual inspection required."])

    return (True, claim_data, claim_path, [])
