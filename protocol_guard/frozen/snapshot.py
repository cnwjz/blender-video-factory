"""SHA256-based task card freezing and verification.

Freeze: copy task.yaml → frozen_task.yaml + frozen_task.sha256
Verify: re-hash task.yaml and compare against stored SHA256.
Re-freeze: rejected if frozen_task.yaml already exists (must bump version or change task_id).
"""

import hashlib
import os
import shutil
import yaml


def _sha256_file(path):
    """Compute SHA256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _sha256_text(text):
    """Compute SHA256 hex digest of a string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def freeze_task(task_path, frozen_dir):
    """Freeze a task card: copy task + write SHA256.

    Args:
        task_path: Path to task.yaml
        frozen_dir: Directory to write frozen_task.yaml and frozen_task.sha256

    Returns:
        (success, sha256_hex, error_message)
        If frozen_task.yaml already exists in frozen_dir, returns (False, None, error).
    """
    os.makedirs(frozen_dir, exist_ok=True)

    frozen_yaml = os.path.join(frozen_dir, "frozen_task.yaml")
    frozen_sha = os.path.join(frozen_dir, "frozen_task.sha256")

    if os.path.exists(frozen_yaml):
        return (False, None,
                f"Frozen task already exists at {frozen_yaml}. "
                f"Bump task_card_version or use a new task_id to re-freeze.")

    sha = _sha256_file(task_path)
    shutil.copy2(task_path, frozen_yaml)
    with open(frozen_sha, "w", encoding="utf-8") as f:
        f.write(sha + "\n")

    return (True, sha, "")


def verify_frozen_task(task_path, frozen_dir):
    """Verify that task.yaml matches the frozen snapshot.

    Args:
        task_path: Path to current task.yaml
        frozen_dir: Directory containing frozen_task.yaml and frozen_task.sha256

    Returns:
        (match, current_sha256, frozen_sha256, error_message)
        match is True if SHA256s are identical.
    """
    frozen_yaml = os.path.join(frozen_dir, "frozen_task.yaml")
    frozen_sha = os.path.join(frozen_dir, "frozen_task.sha256")

    if not os.path.exists(frozen_yaml):
        return (False, None, None, f"Frozen task not found at {frozen_yaml}")
    if not os.path.exists(frozen_sha):
        return (False, None, None, f"SHA256 file not found at {frozen_sha}")

    with open(frozen_sha, "r", encoding="utf-8") as f:
        stored_sha = f.read().strip()

    current_sha = _sha256_file(task_path)

    return (current_sha == stored_sha, current_sha, stored_sha, "")
