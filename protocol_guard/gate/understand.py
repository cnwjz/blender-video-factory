"""Structured understanding record bound to freeze bundle SHA256."""

import hashlib, json, os, yaml
from datetime import datetime, timezone


def _load_schema():
    schema_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "schemas", "understand_record.schema.json"
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


def record_understanding(task_path, freeze_bundle_path, output_dir):
    """Read task card and freeze bundle, produce immutable understanding record.

    Args:
        task_path: path to task_card.yaml
        freeze_bundle_path: path to freeze_bundle.json
        output_dir: directory to write understand.json (runtime_root)

    Returns:
        (success: bool, record: dict|None, sha256: str|None, errors: list[str])
    """
    import jsonschema, tempfile
    errors = []
    schema = _load_schema()
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(freeze_bundle_path):
        return (False, None, None, ["Freeze bundle not found"])

    freeze_bundle_sha = _sha256_file(freeze_bundle_path)

    with open(freeze_bundle_path, "r", encoding="utf-8") as f:
        freeze_data = json.load(f)

    with open(task_path, "r", encoding="utf-8") as f:
        task_data = yaml.safe_load(f)

    task_id = task_data.get("task_id", "unknown")

    record = {
        "task_id": task_id,
        "freeze_bundle_sha256": freeze_bundle_sha,
        "task_goal": task_data.get("primary_goal", ""),
        "allowed_files": [m.get("target", "") for m in task_data.get("allowed_modifications", [])],
        "forbidden_files": [m.get("target", "") for m in task_data.get("forbidden_modifications", [])],
        "input_files": task_data.get("input_files", []),
        "output_files": task_data.get("output_files", []),
        "preconditions": [pc.get("check_id", "") for pc in task_data.get("preflight_checks", [])],
        "stop_conditions": [sc.get("condition", "") for sc in task_data.get("stop_conditions", [])],
        "blender_required": False,
        "spec_conflicts_found": False,
        "spec_conflicts_detail": [],
        "recorded_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "understood_by": "CLAUDE",
    }

    try:
        jsonschema.validate(instance=record, schema=schema)
    except jsonschema.ValidationError as e:
        return (False, None, None, [f"Understand record schema violation: {e.message}"])

    rec_path = os.path.join(output_dir, "understand.json")
    if os.path.exists(rec_path):
        return (False, None, None, ["understand.json already exists — record is immutable"])

    fd, tmp = tempfile.mkstemp(suffix=".json", prefix=".understand_tmp_", dir=output_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, sort_keys=True, indent=2)
        os.replace(tmp, rec_path)
    except Exception:
        if os.path.exists(tmp): os.remove(tmp)
        raise

    rec_sha = _sha256_file(rec_path)
    return (True, record, rec_sha, [])
