"""Shared read-only utilities for Phase 2 Min checkers."""

import hashlib, json, os, re, subprocess, yaml

SHA256_RE = re.compile(r'^[a-f0-9]{64}$')
_isjunction = getattr(os.path, "isjunction", lambda p: False)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk: break
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def load_task_card(task_path):
    with open(task_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_frozen_task(frozen_dir):
    fp = os.path.join(frozen_dir, "frozen_task.yaml")
    if not os.path.exists(fp):
        return (None, "frozen_task.yaml not found")
    with open(fp, "r", encoding="utf-8") as f:
        return (yaml.safe_load(f), None)


def normalize_path(p):
    """Normalize to forward-slash relative path. Reject dangerous paths."""
    if not isinstance(p, str) or p == "":
        raise ValueError(f"Invalid path: {p!r}")
    if os.path.isabs(p):
        raise ValueError(f"Absolute path rejected: {p}")
    if p.startswith("\\\\") or p.startswith("//"):
        raise ValueError(f"UNC path rejected: {p}")
    if len(p) >= 2 and p[1] == ":" and not p.startswith(p[:2] + "\\"):
        raise ValueError(f"Drive-relative path rejected: {p}")
    segments = p.replace("\\", "/").split("/")
    if ".." in segments:
        raise ValueError(f"Parent traversal rejected: {p}")
    for c in p:
        if ord(c) < 32:
            raise ValueError(f"Control character in path: {p!r}")
    return "/".join(segments)


def paths_equal_ci(a, b):
    return normalize_path(a).lower() == normalize_path(b).lower()


def run_git(args, cwd):
    try:
        r = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=10)
        return (r.stdout, r.stderr, r.returncode)
    except FileNotFoundError:
        return ("", "git not found", 1)
    except subprocess.TimeoutExpired:
        return ("", "git timeout", 1)


def resolve_repo_root(task_path):
    task_dir = os.path.dirname(os.path.abspath(task_path))
    out, err, rc = run_git(["rev-parse", "--show-toplevel"], task_dir)
    if rc != 0:
        return (None, f"git rev-parse failed: {err.strip()}")
    return (os.path.realpath(out.strip()), None)


# ════════════════════ Unified safe path validation ════════════════════

def validate_safe_path(root, rel_path, require_type=None):
    """Unified safe path validation with component-level link checking.

    Args:
        root: Absolute canonical root directory (os.path.realpath result)
        rel_path: Relative path within root
        require_type: None, 'file', or 'dir'

    Returns (abs_path: str|None, error: str|None)
    """
    if not isinstance(rel_path, str) or rel_path == "":
        return (None, "PATH_EMPTY_OR_NOT_STRING")
    try:
        np = normalize_path(rel_path)
    except ValueError as e:
        return (None, f"PATH_REJECTED: {e}")

    # Build and check every component
    root = os.path.realpath(root)
    segments = np.split("/")
    current = root

    for i, seg in enumerate(segments):
        if seg in ("", ".", ".."):
            return (None, "PATH_ESCAPES_REPOSITORY")
        current = os.path.join(current, seg)
        if os.path.islink(current):
            return (None, "LINK_COMPONENT_REJECTED")
        if _isjunction(current):
            return (None, "JUNCTION_COMPONENT_REJECTED")

    # Final boundary check using realpath
    real = os.path.realpath(current)
    try:
        common = os.path.commonpath([real, root])
    except ValueError:
        return (None, "PATH_ESCAPES_REPOSITORY")
    if os.path.normcase(common) != os.path.normcase(root):
        return (None, "PATH_ESCAPES_REPOSITORY")

    # Type check
    if require_type == "file":
        if not os.path.isfile(real):
            return (None, "PATH_NOT_A_FILE")
    elif require_type == "dir":
        if not os.path.isdir(real):
            return (None, "PATH_NOT_A_DIR")

    return (real, None)


def validate_path_in_repo(path_str, repo_root, label):
    """Validate relative path within repo using unified check."""
    _, err = validate_safe_path(repo_root, path_str)
    if err:
        return (None, f"{label}: {err}")
    return (normalize_path(path_str), None)


def validate_dir_in_repo(dir_path, repo_root, label):
    """Validate directory within repo."""
    _, err = validate_safe_path(repo_root, dir_path, require_type="dir")
    if err:
        return (None, f"{label}: {err}")
    return (normalize_path(dir_path), None)


# ════════════════════ Structure validation helpers ════════════════════

def _require_type(value, expected_type, label):
    if not isinstance(value, expected_type):
        return f"INVALID_STRUCTURE: {label} must be {expected_type.__name__}, got {type(value).__name__}"
    return None


def validate_policy_structure(policy):
    errs = []
    err = _require_type(policy, dict, "policy")
    if err: return [err]
    err = _require_type(policy.get("allowed_paths"), list, "allowed_paths")
    if err: errs.append(err)
    else:
        for i, e in enumerate(policy["allowed_paths"]):
            if not isinstance(e, dict): errs.append(f"allowed_paths[{i}] must be object")
    err = _require_type(policy.get("denied_paths"), list, "denied_paths")
    if err: errs.append(err)
    else:
        for i, e in enumerate(policy["denied_paths"]):
            if not isinstance(e, dict): errs.append(f"denied_paths[{i}] must be object")
    err = _require_type(policy.get("protected_files"), list, "protected_files")
    if err: errs.append(err)
    else:
        for i, e in enumerate(policy["protected_files"]):
            if not isinstance(e, dict): errs.append(f"protected_files[{i}] must be object")
    return errs


def validate_spec_structure(spec):
    errs = []
    err = _require_type(spec, dict, "upload_spec")
    if err: return [err]
    err = _require_type(spec.get("entries"), list, "upload_spec.entries")
    if err: errs.append(err)
    else:
        for i, e in enumerate(spec["entries"]):
            if not isinstance(e, dict): errs.append(f"upload_spec.entries[{i}] must be object")
    return errs


def validate_manifest_structure(manifest):
    errs = []
    err = _require_type(manifest, dict, "manifest")
    if err: return [err]
    err = _require_type(manifest.get("entries"), list, "manifest.entries")
    if err: errs.append(err)
    else:
        for i, e in enumerate(manifest["entries"]):
            if not isinstance(e, dict): errs.append(f"manifest.entries[{i}] must be object")
    return errs


# ════════════════════ Remaining utilities ════════════════════

def get_worktree_changes(repo_root, baseline_commit):
    changes = {
        "added": [], "modified": [], "deleted": [], "type_changed": [],
        "staged_added": [], "staged_modified": [], "staged_deleted": [],
        "unstaged_modified": [], "unstaged_deleted": [], "untracked": [],
    }

    def _parse_status(out, prefix_map):
        for line in out.strip().split("\n"):
            if not line: continue
            parts = line.split("\t")
            status = parts[0]
            name = parts[-1] if len(parts) > 1 else ""
            if not name: continue
            if len(status) >= 2 and status[1] == "T": changes["type_changed"].append(name)
            for st_prefix, target in prefix_map.items():
                if status.startswith(st_prefix) and name not in changes[target]:
                    changes[target].append(name)

    out, err, rc = run_git(["diff", "--name-status", baseline_commit, "HEAD"], repo_root)
    if rc == 0:
        _parse_status(out, {"A": "added", "M": "modified", "D": "deleted", "R": "added", "T": "type_changed"})
        for line in out.strip().split("\n"):
            if not line: continue
            parts = line.split("\t")
            if parts[0].startswith("R") and len(parts) >= 3:
                changes["deleted"].append(parts[1])

    out, err, rc = run_git(["diff", "--name-status", "--cached"], repo_root)
    if rc == 0:
        _parse_status(out, {"A": "staged_added", "M": "staged_modified", "D": "staged_deleted", "T": "type_changed"})

    out, err, rc = run_git(["diff", "--name-status"], repo_root)
    if rc == 0:
        _parse_status(out, {"M": "unstaged_modified", "D": "unstaged_deleted", "T": "type_changed"})

    out, err, rc = run_git(["ls-files", "--others", "--exclude-standard"], repo_root)
    if rc == 0:
        for line in out.strip().split("\n"):
            if line: changes["untracked"].append(line)

    return changes


def find_entry_by_package_path(package_path, entries):
    np = normalize_path(package_path)
    for e in entries:
        if normalize_path(e.get("package_path", "")).lower() == np.lower():
            return e
    return None


def detect_duplicate_package_paths(entries):
    seen = {}
    dups = []
    for e in entries:
        pp = normalize_path(e.get("package_path", "")).lower()
        if pp in seen: dups.append(e.get("package_path"))
        seen[pp] = True
    return dups


def load_policy(policy_path):
    with open(policy_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_upload_spec(spec_path):
    with open(spec_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_manifest(manifest_path):
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ════════════════════ Deterministic sorting ════════════════════

def sort_result(result):
    """Sort all list fields for deterministic output."""
    for key in ["actual_changes", "out_of_scope_changes", "protected_file_changes",
                "actual_files", "missing_files", "extra_files",
                "hash_mismatches", "source_mismatches", "task_id_mismatches",
                "manifest_errors", "input_errors"]:
        if key in result and isinstance(result[key], list):
            result[key] = sorted(result[key], key=lambda x: json.dumps(x, sort_keys=True) if isinstance(x, dict) else str(x))
    return result
