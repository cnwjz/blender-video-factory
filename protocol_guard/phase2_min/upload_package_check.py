"""Upload Package Check — verify UPLOAD_NEXT against frozen spec."""

import json, os, sys

from protocol_guard.frozen.snapshot import verify_frozen_task
from protocol_guard.phase2_min.io_utils import (
    sha256_file, load_task_card, load_frozen_task, load_upload_spec, load_manifest,
    normalize_path, detect_duplicate_package_paths, resolve_repo_root,
    validate_safe_path, validate_spec_structure, validate_manifest_structure, sort_result,
)


def _validate_manifest_filename(mf, upload_dir):
    """Validate manifest_filename. Returns error or None."""
    _, err = validate_safe_path(upload_dir, mf, require_type="file")
    if err:
        return f"manifest_filename: {err}"
    if ".." in normalize_path(mf).split("/"):
        return "manifest_filename contains parent traversal"
    return None


def _recursive_scan(upload_dir):
    items = {}
    for dirpath, dirnames, filenames in os.walk(upload_dir):
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            rel = os.path.relpath(fp, upload_dir).replace("\\", "/")
            items[rel] = "symlink" if os.path.islink(fp) else "file"
        for dn in dirnames:
            dp = os.path.join(dirpath, dn)
            rel = os.path.relpath(dp, upload_dir).replace("\\", "/")
            items[rel] = "symlink" if os.path.islink(dp) else "dir"
    return items


def upload_package_check(task_path, frozen_dir):
    result = {
        "schema_version": "1",
        "checker": "upload_package_check",
        "task_id": None,
        "upload_spec_sha256": None,
        "actual_files": [],
        "missing_files": [],
        "extra_files": [],
        "hash_mismatches": [],
        "source_mismatches": [],
        "task_id_mismatches": [],
        "manifest_errors": [],
        "input_errors": [],
        "result": None,
    }
    errors = result["input_errors"]
    try:
        return _upload_package_check_impl(task_path, frozen_dir, result, errors)
    except Exception as e:
        errors.append(f"UNEXPECTED_CHECKER_ERROR: {type(e).__name__}")
        result["result"] = "ERROR"
        return (2, sort_result(result))


def _upload_package_check_impl(task_path, frozen_dir, result, errors):
    # 1. Verify frozen task
    match, _, _, ferr = verify_frozen_task(task_path, frozen_dir)
    if not match:
        errors.append(f"Frozen task verification failed: {ferr}")
        result["result"] = "ERROR"
        return (2, sort_result(result))

    task_data = load_task_card(task_path)
    if not isinstance(task_data, dict):
        errors.append("INVALID_STRUCTURE: task card is not a dict")
        result["result"] = "ERROR"
        return (2, sort_result(result))
    frozen_data, ferr2 = load_frozen_task(frozen_dir)
    if frozen_data is None or not isinstance(frozen_data, dict):
        errors.append(ferr2 or "INVALID_STRUCTURE: frozen task is not a dict")
        result["result"] = "ERROR"
        return (2, sort_result(result))

    task_id = task_data.get("task_id", "unknown")
    result["task_id"] = task_id

    fixed = frozen_data.get("fixed_params", {})
    if not isinstance(fixed, dict):
        errors.append("INVALID_STRUCTURE: fixed_params is not a dict")
        result["result"] = "ERROR"
        return (2, sort_result(result))

    upload_spec_path = fixed.get("upload_spec_path")
    upload_spec_sha = fixed.get("upload_spec_sha256")
    if not upload_spec_path or not upload_spec_sha:
        errors.append("Missing fixed_params: upload_spec_path, upload_spec_sha256")
        result["result"] = "ERROR"
        return (2, sort_result(result))

    # 2. Resolve repo root
    repo_root, repo_err = resolve_repo_root(task_path)
    if repo_root is None:
        errors.append(repo_err)
        result["result"] = "ERROR"
        return (2, sort_result(result))

    # 3. Validate task and frozen in repo
    for label, p in [("task_path", task_path), ("frozen_dir", frozen_dir)]:
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

    # 4. Validate upload_spec_path
    spec_abs, spec_err = validate_safe_path(repo_root, upload_spec_path, require_type="file")
    if spec_err:
        errors.append(f"upload_spec_path: {spec_err}")
        result["result"] = "ERROR"
        return (2, sort_result(result))

    # 5. Verify upload spec SHA256
    actual_spec_sha = sha256_file(spec_abs)
    result["upload_spec_sha256"] = upload_spec_sha
    if actual_spec_sha != upload_spec_sha:
        errors.append("Upload spec SHA256 mismatch")
        result["result"] = "ERROR"
        return (2, sort_result(result))

    # 6. Load and validate spec
    try:
        spec = load_upload_spec(spec_abs)
    except Exception as e:
        errors.append(f"Cannot parse upload spec: {e}")
        result["result"] = "ERROR"
        return (2, sort_result(result))

    struct_errs = validate_spec_structure(spec)
    if struct_errs:
        errors.extend(struct_errs)
        result["result"] = "ERROR"
        return (2, sort_result(result))

    if spec.get("schema_version") != "1":
        errors.append("Upload spec schema_version must be '1'")
        result["result"] = "ERROR"
        return (2, sort_result(result))
    if spec.get("task_id") != task_id:
        result["task_id_mismatches"].append(f"Spec task_id={spec.get('task_id')} != {task_id}")
        result["result"] = "ERROR"
        return (2, sort_result(result))

    spec_entries = spec.get("entries", [])
    manifest_filename = spec.get("manifest_filename", "UPLOAD_MANIFEST.json")

    # 7. Validate spec entries
    for entry in spec_entries:
        pp = entry.get("package_path", "")
        sp = entry.get("source_path", "")
        if not pp or not sp:
            errors.append("Spec entry missing package_path or source_path")
            result["result"] = "ERROR"
            return (2, sort_result(result))

    dups = detect_duplicate_package_paths(spec_entries)
    if dups:
        result["source_mismatches"].append({"error": "Duplicate package_paths in spec", "paths": dups})
        result["result"] = "ERROR"
        return (2, sort_result(result))

    # 8. Validate UPLOAD_NEXT
    upload_abs, ul_err = validate_safe_path(repo_root, "reviews/UPLOAD_NEXT", require_type="dir")
    if ul_err:
        errors.append(f"UPLOAD_NEXT: {ul_err}")
        result["result"] = "ERROR"
        return (2, sort_result(result))

    # 9. Validate manifest_filename
    mf_err = _validate_manifest_filename(manifest_filename, upload_abs)
    if mf_err:
        errors.append(mf_err)
        result["result"] = "ERROR"
        return (2, sort_result(result))

    # 10. Load manifest
    manifest_path = os.path.join(upload_abs, manifest_filename)
    if not os.path.exists(manifest_path):
        errors.append(f"Manifest not found: {manifest_filename}")
        result["result"] = "ERROR"
        return (2, sort_result(result))
    try:
        manifest = load_manifest(manifest_path)
    except Exception as e:
        result["manifest_errors"].append(f"Cannot parse manifest: {e}")
        result["result"] = "ERROR"
        return (2, sort_result(result))

    struct_errs = validate_manifest_structure(manifest)
    if struct_errs:
        errors.extend(struct_errs)
        result["result"] = "ERROR"
        return (2, sort_result(result))

    if manifest.get("schema_version") != "1":
        errors.append("Manifest schema_version must be '1'")
        result["result"] = "ERROR"
        return (2, sort_result(result))
    if manifest.get("task_id") != task_id:
        result["task_id_mismatches"].append(f"Manifest task_id={manifest.get('task_id')} != {task_id}")
        result["result"] = "ERROR"
        return (2, sort_result(result))

    manifest_entries = manifest.get("entries", [])

    mdups = detect_duplicate_package_paths(manifest_entries)
    if mdups:
        result["source_mismatches"].append({"error": "Duplicate package_paths in manifest", "paths": mdups})
        result["result"] = "ERROR"
        return (2, sort_result(result))

    # 11. Manifest self-reference
    for me in manifest_entries:
        if normalize_path(me.get("package_path", "")).lower() == normalize_path(manifest_filename).lower():
            result["manifest_errors"].append("Manifest references itself")
            result["result"] = "FAIL"
            return (1, sort_result(result))

    # 12. Recursive scan
    scan_items = _recursive_scan(upload_abs)
    result["actual_files"] = sorted(scan_items.keys())

    # 13. Build maps
    spec_map = {}
    for e in spec_entries:
        k = normalize_path(e["package_path"]).lower()
        spec_map[k] = normalize_path(e["source_path"])

    manifest_map = {}
    for e in manifest_entries:
        k = normalize_path(e.get("package_path", "")).lower()
        v = normalize_path(e.get("source_path", ""))
        manifest_map[k] = v

    spec_keys = set(spec_map.keys())
    manifest_keys = set(manifest_map.keys())
    extra_in_manifest = manifest_keys - spec_keys
    missing_from_manifest = spec_keys - manifest_keys

    for k in extra_in_manifest:
        result["extra_files"].append(k)
    for k in missing_from_manifest:
        result["missing_files"].append(k)
    for k in spec_keys & manifest_keys:
        if spec_map[k] != manifest_map[k]:
            result["source_mismatches"].append({
                "package_path": k, "spec_source": spec_map[k], "manifest_source": manifest_map[k],
            })

    # 14. Actual files vs expected
    expected_files = {normalize_path(manifest_filename).lower()}
    for e in spec_entries:
        expected_files.add(normalize_path(e["package_path"]).lower())

    actual_file_keys = set()
    dirs_in_scan = set()
    for fn_rel, ftype in scan_items.items():
        if ftype == "symlink":
            result["source_mismatches"].append({"path": fn_rel, "error": "Symlink/junction in UPLOAD_NEXT"})
        elif ftype == "file":
            actual_file_keys.add(normalize_path(fn_rel).lower())
        elif ftype == "dir":
            dirs_in_scan.add(fn_rel)

    for d in sorted(dirs_in_scan):
        is_parent = any(normalize_path(f).lower().startswith(normalize_path(d).lower() + "/")
                       for f in actual_file_keys)
        if not is_parent:
            result["extra_files"].append(f"{d}/ (empty directory)")

    extra = sorted(actual_file_keys - expected_files)
    missing = sorted(expected_files - actual_file_keys)
    if extra:
        result["extra_files"] = sorted(set(result["extra_files"]) | set(extra))
    if missing:
        result["missing_files"] = sorted(set(result["missing_files"]) | set(missing))

    # 15. Per-entry validation
    for spec_entry in spec_entries:
        pp = normalize_path(spec_entry["package_path"])
        sp = normalize_path(spec_entry["source_path"])

        m_entry = None
        for me in manifest_entries:
            if normalize_path(me.get("package_path", "")).lower() == pp.lower():
                m_entry = me
                break
        if m_entry is None:
            continue

        m_sha = m_entry.get("sha256", "")

        # Validate package file via unified safe path
        pkg_abs, pkg_err = validate_safe_path(upload_abs, pp, require_type="file")
        if pkg_err:
            result["missing_files"].append(f"{pp}: {pkg_err}")
            continue
        pkg_sha = sha256_file(pkg_abs)
        if pkg_sha != m_sha:
            result["hash_mismatches"].append({
                "package_path": pp, "expected_sha256": m_sha, "actual_sha256": pkg_sha,
            })

        # Validate source_path via unified safe path (must be file, not dir)
        src_abs, src_err = validate_safe_path(repo_root, sp, require_type="file")
        if src_err:
            result["source_mismatches"].append({"package_path": pp, "error": f"source_path: {src_err}"})
            continue
        src_sha = sha256_file(src_abs)
        if src_sha != pkg_sha:
            result["hash_mismatches"].append({
                "package_path": pp, "error": "Source and package SHA256 differ",
                "package_sha256": pkg_sha, "source_sha256": src_sha,
            })
        if os.path.realpath(src_abs).startswith(os.path.realpath(upload_abs) + os.sep):
            result["source_mismatches"].append({"package_path": pp, "error": "Source inside UPLOAD_NEXT"})

    if errors:
        result["result"] = "ERROR"
        return (2, sort_result(result))
    has_issues = (result["missing_files"] or result["extra_files"] or
                  result["hash_mismatches"] or result["source_mismatches"] or
                  result["task_id_mismatches"] or result["manifest_errors"])
    if has_issues:
        result["result"] = "FAIL"
        return (1, sort_result(result))
    result["result"] = "PASS"
    return (0, sort_result(result))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        result = {"result": "ERROR", "input_errors": ["Usage: python -m protocol_guard.phase2_min.upload_package_check <task_path> <frozen_dir>"]}
        json.dump(sort_result(result), sys.stdout, ensure_ascii=False, sort_keys=True)
        sys.exit(2)
    try:
        code, result = upload_package_check(sys.argv[1], sys.argv[2])
        json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True)
        sys.exit(code)
    except Exception as e:
        result = {"result": "ERROR", "input_errors": [f"UNEXPECTED_CHECKER_ERROR: {type(e).__name__}"]}
        json.dump(sort_result(result), sys.stdout, ensure_ascii=False, sort_keys=True)
        sys.exit(2)
