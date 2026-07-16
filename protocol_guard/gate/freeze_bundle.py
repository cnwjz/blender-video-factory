"""Multi-artifact atomic freeze with post-freeze re-check."""

import copy
import hashlib
import json
import os
import tempfile
import yaml

from protocol_guard.state.project_state import (
    _sha256_file,
    _sha256_bytes,
    _canonical_state_hash,
    _canonical_json,
    load_state,
)


def _load_schema():
    schema_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "schemas", "freeze_bundle.schema.json"
    )
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def freeze_bundle(task_path, state_path, output_dir):
    """Create an atomic freeze bundle with post-freeze re-check.

    Args:
        task_path: path to task_card.yaml
        state_path: path to PROJECT_STATE.yaml
        output_dir: directory to write freeze_bundle.json (runtime_root)

    Returns:
        (success: bool, bundle: dict|None, sha256: str|None, errors: list[str])
    """
    import jsonschema
    errors = []
    schema = _load_schema()

    task_path = os.path.abspath(task_path)
    state_path = os.path.abspath(state_path)
    os.makedirs(output_dir, exist_ok=True)

    # 1. Load and validate task card
    try:
        with open(task_path, "r", encoding="utf-8") as f:
            task_data = yaml.safe_load(f)
    except Exception as e:
        return (False, None, None, [f"Failed to load task card: {e}"])

    from protocol_guard.task_schema import validate_task_card
    ok_tc, tc_errs = validate_task_card(task_data)
    if not ok_tc:
        return (False, None, None, tc_errs)

    task_id = task_data.get("task_id", "unknown")

    task_id = task_data.get("task_id", "unknown")

    # 2. Compute all hashes (first pass)
    task_card_sha = _sha256_file(task_path)
    state_data = load_state(state_path)
    state_canonical_sha = _canonical_state_hash(state_data)

    input_hashes = {}
    for inf in task_data.get("input_files", []):
        # Input paths are relative to project root
        inf_abs = os.path.join(os.path.dirname(state_path), inf)
        if not os.path.exists(inf_abs):
            return (False, None, None, [f"Input file not found: {inf}"])
        input_hashes[inf] = _sha256_file(inf_abs)

    # 3. Build candidate bundle
    frozen_task_copy = os.path.join(output_dir, "frozen_task.yaml")
    import shutil
    shutil.copy2(task_path, frozen_task_copy)

    candidate = {
        "task_id": task_id,
        "frozen_at": _now_iso(),
        "task_card_raw_sha256": task_card_sha,
        "project_state_canonical_sha256": state_canonical_sha,
        "input_files_raw_sha256": input_hashes,
        "frozen_task_copy_path": frozen_task_copy,
    }

    # 4. Post-freeze re-check: re-read all sources and re-compute
    task_card_sha2 = _sha256_file(task_path)
    state_data2 = load_state(state_path)
    state_canonical_sha2 = _canonical_state_hash(state_data2)

    if task_card_sha2 != task_card_sha:
        return (False, None, None, ["Post-freeze re-check failed: task card changed during freeze"])
    if state_canonical_sha2 != state_canonical_sha:
        return (False, None, None, ["Post-freeze re-check failed: project state changed during freeze"])

    for inf in task_data.get("input_files", []):
        inf_abs = os.path.join(os.path.dirname(state_path), inf)
        h2 = _sha256_file(inf_abs)
        if h2 != input_hashes[inf]:
            return (False, None, None, [f"Post-freeze re-check failed: input file changed: {inf}"])

    # 5. Validate against schema
    try:
        jsonschema.validate(instance=candidate, schema=schema)
    except jsonschema.ValidationError as e:
        return (False, None, None, [f"Freeze bundle schema violation: {e.message}"])

    # 6. Check for existing bundle (reject overwrite)
    bundle_path = os.path.join(output_dir, "freeze_bundle.json")
    if os.path.exists(bundle_path):
        return (False, None, None, ["Freeze bundle already exists. Bump task_card_version or use new task_id."])
    fd, tmp = tempfile.mkstemp(suffix=".json", prefix=".freeze_bundle_tmp_", dir=output_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(candidate, f, ensure_ascii=False, sort_keys=True, indent=2)
        os.replace(tmp, bundle_path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise

    bundle_sha = _sha256_file(bundle_path)
    return (True, candidate, bundle_sha, [])


def _now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).astimezone().isoformat()
