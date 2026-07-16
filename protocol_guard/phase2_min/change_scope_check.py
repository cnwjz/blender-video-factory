"""Change Scope Check — verify worktree changes against frozen policy."""

import json, os, re, sys

from protocol_guard.frozen.snapshot import verify_frozen_task
from protocol_guard.phase2_min.io_utils import (
    sha256_file, load_task_card, load_frozen_task, load_policy,
    normalize_path, resolve_repo_root, validate_path_in_repo, run_git,
    validate_policy_structure, validate_safe_path, sort_result,
)

EXCLUDED_BUILTIN = {".git", "reviews/UPLOAD_NEXT"}
SHA256_RE = re.compile(r'^[a-f0-9]{64}$')


def _match_policy(path, entry):
    np = normalize_path(path).lower()
    ep = normalize_path(entry["path"]).lower()
    pt = entry.get("path_type", "")
    if pt == "file":
        return np == ep
    elif pt == "directory":
        return np == ep or np.startswith(ep.rstrip("/") + "/") or np.startswith(ep + "/")
    return False


def _is_excluded(path):
    np = normalize_path(path).lower()
    for ex in EXCLUDED_BUILTIN:
        en = normalize_path(ex).lower()
        if np == en or np.startswith(en.rstrip("/") + "/"):
            return True
    return False


def change_scope_check(task_path, frozen_dir):
    """Check worktree changes since baseline comply with frozen policy.

    Returns: (exit_code: int, result: dict)
        0 = PASS, 1 = FAIL, 2 = ERROR
    """
    result = {
        "schema_version": "1",
        "checker": "change_scope_check",
        "task_id": None,
        "baseline_commit_sha": None,
        "policy_sha256": None,
        "actual_changes": [],
        "out_of_scope_changes": [],
        "protected_file_changes": [],
        "input_errors": [],
        "result": None,
    }
    errors = result["input_errors"]

    try:
        return _change_scope_check_impl(task_path, frozen_dir, result, errors)
    except Exception as e:
        errors.append(f"UNEXPECTED_CHECKER_ERROR: {type(e).__name__}")
        result["result"] = "ERROR"
        return (2, sort_result(result))


def _change_scope_check_impl(task_path, frozen_dir, result, errors):
    # 1. Verify frozen task
    match, _, _, ferr = verify_frozen_task(task_path, frozen_dir)
    if not match:
        errors.append(f"Frozen task verification failed: {ferr}")
        result["result"] = "ERROR"
        return (2, sort_result(result))

    # 2. Load task card and frozen task
    frozen_data, ferr2 = load_frozen_task(frozen_dir)
    if frozen_data is None or not isinstance(frozen_data, dict):
        errors.append(ferr2 or "INVALID_STRUCTURE: frozen task is not a dict")
        result["result"] = "ERROR"
        return (2, sort_result(result))

    task_data = load_task_card(task_path)
    if not isinstance(task_data, dict):
        errors.append("INVALID_STRUCTURE: task card is not a dict")
        result["result"] = "ERROR"
        return (2, sort_result(result))
    task_id = task_data.get("task_id", "unknown")
    result["task_id"] = task_id

    # 3. Read fixed_params
    fixed = frozen_data.get("fixed_params", {})
    if not isinstance(fixed, dict):
        errors.append("INVALID_STRUCTURE: fixed_params is not a dict")
        result["result"] = "ERROR"
        return (2, sort_result(result))

    baseline_commit = fixed.get("baseline_commit_sha")
    policy_path = fixed.get("policy_path")
    policy_sha = fixed.get("policy_sha256")
    worktree_clean = fixed.get("worktree_clean_at_approval")
    result["baseline_commit_sha"] = baseline_commit

    if worktree_clean is not True:
        errors.append(f"worktree_clean_at_approval must be true, got: {worktree_clean!r}")
        result["result"] = "ERROR"
        return (2, sort_result(result))
    if not baseline_commit or not policy_path or not policy_sha:
        errors.append("Missing required fixed_params")
        result["result"] = "ERROR"
        return (2, sort_result(result))

    # 4. Resolve repo root
    repo_root, repo_err = resolve_repo_root(task_path)
    if repo_root is None:
        errors.append(repo_err)
        result["result"] = "ERROR"
        return (2, sort_result(result))

    # 5. Validate task and frozen in repo
    for label, p in [("task_path", task_path), ("frozen_dir", frozen_dir)]:
        _, err = validate_safe_path(repo_root, os.path.relpath(os.path.realpath(p), repo_root))
        if err and "REPOSITORY" not in err:
            _, err2 = validate_safe_path(repo_root, os.path.relpath(os.path.realpath(p), repo_root))
        # Direct check: realpath must be within repo
        rp = os.path.realpath(p)
        try:
            if os.path.commonpath([rp, repo_root]) != repo_root:
                errors.append(f"{label} is outside repo")
                result["result"] = "ERROR"
                return (2, sort_result(result))
        except ValueError:
            errors.append(f"{label} is outside repo")
            result["result"] = "ERROR"
            return (2, sort_result(result))

    # 6. Validate policy_path
    policy_abs, pol_err = validate_safe_path(repo_root, policy_path, require_type="file")
    if pol_err:
        errors.append(f"policy_path: {pol_err}")
        result["result"] = "ERROR"
        return (2, sort_result(result))

    # 7. Verify policy SHA256
    actual_policy_sha = sha256_file(policy_abs)
    result["policy_sha256"] = policy_sha
    if actual_policy_sha != policy_sha:
        errors.append("Policy SHA256 mismatch")
        result["result"] = "ERROR"
        return (2, sort_result(result))

    # 8. Load and validate policy structure
    try:
        policy = load_policy(policy_abs)
    except Exception as e:
        errors.append(f"Cannot parse policy: {e}")
        result["result"] = "ERROR"
        return (2, sort_result(result))

    struct_errs = validate_policy_structure(policy)
    if struct_errs:
        errors.extend(struct_errs)
        result["result"] = "ERROR"
        return (2, sort_result(result))

    if policy.get("schema_version") != "1":
        errors.append("Policy schema_version must be '1'")
        result["result"] = "ERROR"
        return (2, sort_result(result))
    if policy.get("task_id") != task_id:
        errors.append("Policy task_id mismatch")
        result["result"] = "ERROR"
        return (2, sort_result(result))

    allowed_paths = policy.get("allowed_paths", [])
    denied_paths = policy.get("denied_paths", [])
    protected_files = policy.get("protected_files", [])

    # 9. Validate policy entries
    for label, entries in [("allowed_paths", allowed_paths), ("denied_paths", denied_paths)]:
        seen = set()
        for entry in entries:
            pt = entry.get("path_type", "")
            p = entry.get("path", "")
            if pt not in ("file", "directory"):
                errors.append(f"{label} entry has invalid path_type: {entry}")
                result["result"] = "ERROR"
                return (2, sort_result(result))
            if not p:
                errors.append(f"{label} entry missing path")
                result["result"] = "ERROR"
                return (2, sort_result(result))
            try:
                np = normalize_path(p)
            except ValueError as e:
                errors.append(f"{label} entry path rejected ({p}): {e}")
                result["result"] = "ERROR"
                return (2, sort_result(result))
            if np.lower() in seen:
                errors.append(f"{label} duplicate path: {p}")
                result["result"] = "ERROR"
                return (2, sort_result(result))
            seen.add(np.lower())

    seen_protected = set()
    for entry in protected_files:
        p = entry.get("path", "")
        s = entry.get("sha256", "")
        if not p:
            errors.append("protected_files entry missing path")
            result["result"] = "ERROR"
            return (2, sort_result(result))
        try:
            np = normalize_path(p)
        except ValueError as e:
            errors.append(f"protected_files path rejected ({p}): {e}")
            result["result"] = "ERROR"
            return (2, sort_result(result))
        if np.lower() in seen_protected:
            errors.append(f"protected_files duplicate path: {p}")
            result["result"] = "ERROR"
            return (2, sort_result(result))
        seen_protected.add(np.lower())
        if not SHA256_RE.match(s):
            errors.append(f"protected_files invalid sha256 for {p}: {s}")
            result["result"] = "ERROR"
            return (2, sort_result(result))

    # 10. Validate baseline commit SHA format
    if not isinstance(baseline_commit, str):
        errors.append("BASELINE_NOT_FULL_COMMIT_SHA: baseline_commit_sha is not a string")
        result["result"] = "ERROR"
        return (2, sort_result(result))
    if not re.fullmatch(r'^[0-9a-f]{40}$', baseline_commit):
        errors.append("BASELINE_NOT_FULL_COMMIT_SHA: must be exactly 40 hex characters")
        result["result"] = "ERROR"
        return (2, sort_result(result))

    out, err, rc = run_git(["cat-file", "-t", baseline_commit], repo_root)
    if rc != 0:
        errors.append("BASELINE_OBJECT_NOT_FOUND: git cat-file -t failed")
        result["result"] = "ERROR"
        return (2, sort_result(result))
    if out.strip() != "commit":
        errors.append(f"BASELINE_OBJECT_NOT_COMMIT: object type is '{out.strip()}', expected 'commit'")
        result["result"] = "ERROR"
        return (2, sort_result(result))

    # 11. Get worktree changes
    git_changes, git_err = _get_changes_or_error(repo_root, baseline_commit)
    if git_err:
        errors.append(git_err)
        result["result"] = "ERROR"
        return (2, sort_result(result))

    all_changed = set()
    for change_type, paths in git_changes.items():
        for p in paths:
            all_changed.add((p, change_type))

    out_of_scope = []
    protected_changes = []

    # 12. Check protected files
    for pf_entry in protected_files:
        pf_path = normalize_path(pf_entry["path"])
        pf_expected_sha = pf_entry.get("sha256", "")
        pf_abs, pf_err = validate_safe_path(repo_root, pf_path, require_type="file")
        if pf_err:
            protected_changes.append({
                "path": pf_path, "reason": pf_err,
                "expected_sha256": pf_expected_sha, "actual_sha256": None,
            })
            continue

        actual_sha = sha256_file(pf_abs)
        if actual_sha != pf_expected_sha:
            protected_changes.append({
                "path": pf_path, "reason": "SHA256 mismatch",
                "expected_sha256": pf_expected_sha, "actual_sha256": actual_sha,
            })

    result["protected_file_changes"] = protected_changes

    # 13. Check changed files against policy
    for path, change_type in sorted(all_changed):
        np = normalize_path(path)
        if _is_excluded(np):
            continue
        is_protected = any(normalize_path(pf["path"]).lower() == np.lower()
                          for pf in protected_files)
        if is_protected:
            continue

        result["actual_changes"].append({"path": np, "change_type": change_type})

        if any(_match_policy(path, d) for d in denied_paths):
            out_of_scope.append({"path": np, "change_type": change_type, "reason": "denied_paths match"})
            continue
        if not any(_match_policy(path, a) for a in allowed_paths):
            out_of_scope.append({"path": np, "change_type": change_type, "reason": "not in allowed_paths"})

    result["out_of_scope_changes"] = out_of_scope

    if errors:
        result["result"] = "ERROR"
        return (2, sort_result(result))
    if out_of_scope or protected_changes:
        result["result"] = "FAIL"
        return (1, sort_result(result))
    result["result"] = "PASS"
    return (0, sort_result(result))


def _get_changes_or_error(repo_root, baseline_commit):
    from protocol_guard.phase2_min.io_utils import get_worktree_changes as gwc
    changes = {
        "added": [], "modified": [], "deleted": [], "type_changed": [],
        "staged_added": [], "staged_modified": [], "staged_deleted": [],
        "unstaged_modified": [], "unstaged_deleted": [], "untracked": [],
    }
    for cmd_args, target_keys in [
        (["diff", "--name-status", baseline_commit, "HEAD"],
         {"A": "added", "M": "modified", "D": "deleted", "T": "type_changed"}),
        (["diff", "--name-status", "--cached"],
         {"A": "staged_added", "M": "staged_modified", "D": "staged_deleted", "T": "type_changed"}),
        (["diff", "--name-status"],
         {"M": "unstaged_modified", "D": "unstaged_deleted", "T": "type_changed"}),
    ]:
        out, err, rc = run_git(cmd_args, repo_root)
        if rc != 0:
            return (None, f"git {' '.join(cmd_args)} failed: {err.strip()}")
        for line in out.strip().split("\n"):
            if not line: continue
            parts = line.split("\t")
            status = parts[0]; name = parts[-1] if len(parts) > 1 else ""
            if not name: continue
            if status.startswith("R") and len(parts) >= 3:
                changes["deleted"].append(parts[1]); changes["added"].append(parts[2])
            for st_prefix, target in target_keys.items():
                if status.startswith(st_prefix) and name not in changes[target]:
                    changes[target].append(name)
    out, err, rc = run_git(["ls-files", "--others", "--exclude-standard"], repo_root)
    if rc != 0:
        return (None, f"git ls-files failed: {err.strip()}")
    for line in out.strip().split("\n"):
        if line: changes["untracked"].append(line)
    return (changes, None)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        result = {"result": "ERROR", "input_errors": ["Usage: python -m protocol_guard.phase2_min.change_scope_check <task_path> <frozen_dir>"]}
        json.dump(sort_result(result), sys.stdout, ensure_ascii=False, sort_keys=True)
        sys.exit(2)
    try:
        code, result = change_scope_check(sys.argv[1], sys.argv[2])
        json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True)
        sys.exit(code)
    except Exception as e:
        result = {"result": "ERROR", "input_errors": [f"UNEXPECTED_CHECKER_ERROR: {type(e).__name__}"]}
        json.dump(sort_result(result), sys.stdout, ensure_ascii=False, sort_keys=True)
        sys.exit(2)
