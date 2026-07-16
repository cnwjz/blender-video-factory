"""PROJECT_STATE.yaml management with field-level actor permissions.

v1.4:
  - save_state() tmp_path cleanup via try/finally (unconditional)
  - build_evidence_manifest() and verify_evidence_manifest() — no self-referencing
  - evidence_manifest.json excludes itself and final PROJECT_STATE raw file hash

v1.3:
  - save_state() atomic: deepcopy → validate → tempfile → re-read → re-validate → os.replace
  - GPT_PROPOSAL via USER_APPROVED: change_log.reason records [GPT_PROPOSAL via USER_APPROVED]
"""

import copy
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone

import yaml

from protocol_guard.result import VALID_TECHNICAL_RESULTS, VALID_EVIDENCE_STATUSES

_SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "schemas", "project_state.schema.json"
)

PATCH_SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "schemas", "state_patch.schema.json"
)

CLAUDE_WRITABLE = frozenset({
    "last_task_id",
    "last_task_card_sha256",
    "last_technical_result",
    "evidence_status",
    "evidence_sha256",
    "output_files",
    "last_execution_time",
})

RESTRICTED_FIELDS = frozenset({
    "workflow_phase",
    "scene_phase",
    "phase_approved",
    "locked_assets",
    "unlocked_assets",
    "blocked_operations",
    "failed_paths",
    "project_work_paused",
    "protocol_version",
    "diagnostic_only_outputs",
    "pending_review",
    "change_log",
})

SHA256_PATTERN = re.compile(r'^[a-f0-9]{64}$')


def _load_schema():
    with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_patch_schema():
    with open(PATCH_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _sha256_bytes(data):
    """SHA256 of raw bytes → lowercase hex."""
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path):
    """SHA256 of file raw bytes → lowercase hex."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _validate_iso_datetime(value, field_name):
    if not isinstance(value, str) or len(value) == 0:
        return f"{field_name} must be a non-empty ISO 8601 string with timezone"
    try:
        dt = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return f"{field_name}: invalid ISO 8601 datetime: '{value}'"
    if dt.utcoffset() is None:
        return f"{field_name}: missing timezone (must include Z, +HH:MM, or -HH:MM): '{value}'"
    return None


def _now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat()


# ═══════════════════════════════════════════════════════════════════
# State validation
# ═══════════════════════════════════════════════════════════════════

def validate_state(state_data, schema=None):
    import jsonschema
    if schema is None:
        schema = _load_schema()
    errors = []
    try:
        jsonschema.validate(instance=state_data, schema=schema)
    except jsonschema.ValidationError as e:
        errors.append(f"Schema violation: {e.message}")
        return False, errors

    tr = state_data.get("last_technical_result")
    if tr is not None and tr not in VALID_TECHNICAL_RESULTS:
        errors.append(f"Invalid technical_result: {tr}")
    es = state_data.get("evidence_status")
    if es is not None and es not in VALID_EVIDENCE_STATUSES:
        errors.append(f"Invalid evidence_status: {es}")

    for sha_field in ["last_task_card_sha256", "evidence_sha256"]:
        val = state_data.get(sha_field)
        if val is not None:
            if not isinstance(val, str):
                errors.append(f"{sha_field} must be null or a 64-char hex string")
            elif len(val) == 0:
                errors.append(f"{sha_field} must be null, not empty string")
            elif not SHA256_PATTERN.match(val):
                errors.append(f"{sha_field} must be a 64-char lowercase hex string, got: '{val}'")

    let = state_data.get("last_execution_time")
    if let is not None:
        err = _validate_iso_datetime(let, "last_execution_time")
        if err:
            errors.append(err)

    for i, entry in enumerate(state_data.get("change_log", [])):
        ts = entry.get("timestamp", "")
        if ts:
            err = _validate_iso_datetime(ts, f"change_log[{i}].timestamp")
            if err:
                errors.append(err)

    for i, asset in enumerate(state_data.get("locked_assets", [])):
        aa = asset.get("approved_at")
        if aa is not None:
            err = _validate_iso_datetime(aa, f"locked_assets[{i}].approved_at")
            if err:
                errors.append(err)

    pr = state_data.get("pending_review")
    if isinstance(pr, dict):
        pr_status = pr.get("status")
        if pr_status is not None and pr_status not in ("awaiting_gpt_review", "awaiting_user_review", "approved", "rejected"):
            errors.append(f"Invalid pending_review.status: {pr_status}")

    return (len(errors) == 0, errors)


# ═══════════════════════════════════════════════════════════════════
# Evidence manifest (v1.4 — no self-reference)
# ═══════════════════════════════════════════════════════════════════

def _canonical_json(obj):
    """Deterministic JSON: sort_keys, compact separators, ensure_ascii=False, UTF-8."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _canonical_state_hash(state_data):
    """SHA256 of canonical JSON of state with evidence_sha256 temporarily null."""
    c = copy.deepcopy(state_data)
    c["evidence_sha256"] = None
    return _sha256_bytes(_canonical_json(c))


def build_evidence_manifest(state_data, file_paths, task_id, manifest_path):
    """Build evidence_manifest.json.

    Args:
        state_data: final candidate PROJECT_STATE dict
        file_paths: dict of {logical_name: absolute_path} for 4 deliverable files
        task_id: task identifier
        manifest_path: where to write evidence_manifest.json

    Returns:
        (success, manifest_data, manifest_sha256, errors)
    """
    errors = []

    # 1. Canonical state hash (evidence_sha256 = null)
    state_norm_hash = _canonical_state_hash(state_data)

    # 2. Hash the 4 frozen files
    file_hashes = {}
    for name in sorted(file_paths.keys()):
        path = file_paths[name]
        if not os.path.exists(path):
            errors.append(f"File not found: {name} at {path}")
            return (False, None, None, errors)
        file_hashes[name] = _sha256_file(path)

    # 3. Build manifest
    manifest = {
        "schema_version": "1.0",
        "task_id": task_id,
        "project_state_normalization": {
            "method": "canonical_json_with_evidence_sha256_null",
            "sha256": state_norm_hash,
        },
        "files": file_hashes,
    }

    # 4. Write manifest (deterministic JSON + trailing newline)
    manifest_bytes = _canonical_json(manifest) + b"\n"
    with open(manifest_path, "wb") as f:
        f.write(manifest_bytes)

    # 5. SHA256 of manifest file
    manifest_sha = _sha256_bytes(manifest_bytes)

    return (True, manifest, manifest_sha, [])


def verify_evidence_manifest(state_data, manifest_path, file_paths):
    """Verify evidence_manifest.json against current state and files.

    Checks:
      1. PROJECT_STATE.evidence_sha256 == SHA256(evidence_manifest.json)
      2. Canonical state hash (evidence_sha256=null) matches manifest
      3. All 4 files exist and SHA256 match
      4. Manifest does not contain itself
      5. Manifest does not contain PROJECT_STATE raw file hash
      6. task_id matches PROJECT_STATE.last_task_id

    Returns (is_valid, errors).
    """
    errors = []

    if not os.path.exists(manifest_path):
        errors.append(f"Manifest not found: {manifest_path}")
        return (False, errors)

    # Read manifest raw bytes
    with open(manifest_path, "rb") as f:
        manifest_bytes = f.read()

    # Read manifest JSON
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        errors.append(f"Manifest JSON parse error: {e}")
        return (False, errors)

    # 1. evidence_sha256 == SHA256(manifest file)
    manifest_file_sha = _sha256_bytes(manifest_bytes)
    expected_sha = state_data.get("evidence_sha256")
    if expected_sha is None or manifest_file_sha != expected_sha:
        errors.append(
            f"evidence_sha256 mismatch: state={expected_sha}, manifest_file={manifest_file_sha}"
        )

    # 2. Canonical state hash matches
    state_norm_hash = _canonical_state_hash(state_data)
    expected_norm = manifest.get("project_state_normalization", {}).get("sha256")
    if state_norm_hash != expected_norm:
        errors.append(
            f"Canonical state hash mismatch: computed={state_norm_hash}, manifest={expected_norm}"
        )

    # 3. File hashes match
    manifest_files = manifest.get("files", {})
    for name in sorted(file_paths.keys()):
        path = file_paths[name]
        if not os.path.exists(path):
            errors.append(f"File not found: {name} at {path}")
            continue
        actual = _sha256_file(path)
        expected = manifest_files.get(name)
        if actual != expected:
            errors.append(f"File hash mismatch for {name}: actual={actual}, manifest={expected}")

    # Check no extra files in manifest
    for name in manifest_files:
        if name not in file_paths:
            errors.append(f"Unexpected file in manifest: {name}")

    # 4. Manifest must not contain itself
    if "evidence_manifest.json" in manifest_files:
        errors.append("Manifest contains self-reference (evidence_manifest.json)")

    # 5. Manifest must not contain PROJECT_STATE raw file hash
    if "PROJECT_STATE.yaml" in manifest_files:
        errors.append("Manifest contains PROJECT_STATE.yaml raw file hash (self-reference)")

    # 6. task_id matches
    manifest_task = manifest.get("task_id")
    state_task = state_data.get("last_task_id")
    if manifest_task != state_task:
        errors.append(f"task_id mismatch: manifest={manifest_task}, state={state_task}")

    return (len(errors) == 0, errors)


# ═══════════════════════════════════════════════════════════════════
# Patch validation & application
# ═══════════════════════════════════════════════════════════════════

def validate_patch(actor, patch_fields):
    if not isinstance(patch_fields, dict):
        return (False, [], "patch_fields must be a dict")
    requested = set(patch_fields.keys())
    if actor == "CLAUDE":
        blocked = requested - CLAUDE_WRITABLE
        if blocked:
            return (False, sorted(blocked),
                    f"CLAUDE can only write {sorted(CLAUDE_WRITABLE)}, rejected: {sorted(blocked)}")
        return (True, [], "")
    elif actor == "GPT_PROPOSAL":
        return (False, sorted(requested),
                "GPT_PROPOSAL cannot directly write any field")
    elif actor == "USER_APPROVED":
        return (True, [], "")
    else:
        return (False, sorted(requested), f"Unknown actor: {actor}")


def validate_patch_document(patch_doc):
    import jsonschema
    schema = _load_patch_schema()
    errors = []
    try:
        jsonschema.validate(instance=patch_doc, schema=schema)
    except jsonschema.ValidationError as e:
        errors.append(f"Patch schema violation: {e.message}")
        return False, errors
    fields = patch_doc.get("fields", {})
    if "change_log" in fields:
        errors.append("change_log cannot be in patch fields")
    return (len(errors) == 0, errors)


def apply_patch_document(state_data, patch_doc, approval=None):
    errors = []
    ok, errs = validate_patch_document(patch_doc)
    errors.extend(errs)
    if not ok:
        return (False, state_data, errors)

    original_actor = patch_doc["actor"]
    fields = patch_doc["fields"]
    task_id = patch_doc["task_id"]
    reason = patch_doc.get("reason", "")

    effective_actor = original_actor
    if original_actor == "GPT_PROPOSAL":
        if approval is None or approval.get("approved_by") != "USER_APPROVED":
            errors.append("GPT_PROPOSAL patches require USER_APPROVED approval")
            return (False, state_data, errors)
        effective_actor = "USER_APPROVED"
        approved_fields = approval.get("approved_fields", list(fields.keys()))
        fields = {k: v for k, v in fields.items() if k in approved_fields}

    allowed, blocked, reason_blocked = validate_patch(effective_actor, fields)
    if not allowed:
        errors.append(reason_blocked)
        return (False, state_data, errors)

    candidate = copy.deepcopy(state_data)
    applied_fields = copy.deepcopy(fields)
    candidate.update(applied_fields)

    log_actor = "USER_APPROVED" if original_actor == "GPT_PROPOSAL" else effective_actor
    if original_actor == "GPT_PROPOSAL":
        log_reason = f"[GPT_PROPOSAL via USER_APPROVED] {reason}"
    else:
        log_reason = reason

    log_entry = {
        "timestamp": _now_iso(),
        "actor": log_actor,
        "task_id": task_id,
        "fields_changed": sorted(applied_fields.keys()),
        "reason": log_reason,
    }
    existing_log = list(candidate.get("change_log", []))
    candidate["change_log"] = existing_log + [log_entry]

    ok_state, state_errs = validate_state(candidate)
    errors.extend(state_errs)
    if not ok_state:
        return (False, state_data, errors)

    return (True, candidate, [])


def apply_patch(state_data, actor, patch_fields, approval=None):
    patch_doc = {
        "actor": actor,
        "task_id": patch_fields.get("last_task_id", "LEGACY_PATCH"),
        "fields": {k: v for k, v in patch_fields.items() if k != "change_log"},
        "reason": "Legacy apply_patch call",
    }
    if "change_log" in patch_fields:
        return (False, state_data, ["change_log must not be in external patch fields"])
    return apply_patch_document(state_data, patch_doc, approval)


# ═══════════════════════════════════════════════════════════════════
# File I/O
# ═══════════════════════════════════════════════════════════════════

def load_state(state_path):
    with open(state_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _write_yaml_unchecked(state_data, path):
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(state_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def save_state(state_data, state_path):
    """Atomically save PROJECT_STATE data with full validation.

    v1.4: unconditional tmp_path cleanup via try/finally.
    """
    errors = []

    candidate = copy.deepcopy(state_data)

    ok, errs = validate_state(candidate)
    if not ok:
        errors.extend(errs)
        return (False, errors)

    target_dir = os.path.dirname(os.path.abspath(state_path))
    tmp_path = None

    try:
        fd, tmp_path = tempfile.mkstemp(
            suffix=".yaml",
            prefix=".project_state_tmp_",
            dir=target_dir,
        )
        os.close(fd)

        _write_yaml_unchecked(candidate, tmp_path)

        with open(tmp_path, "r", encoding="utf-8") as f:
            re_read = yaml.safe_load(f)

        ok_rr, errs_rr = validate_state(re_read)
        if not ok_rr:
            errors.extend(errs_rr)
            return (False, errors)

        os.replace(tmp_path, state_path)
        tmp_path = None  # success — do not delete in finally
        return (True, [])

    except Exception as e:
        errors.append(f"save_state failed: {e}")
        return (False, errors)

    finally:
        if tmp_path is not None and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
