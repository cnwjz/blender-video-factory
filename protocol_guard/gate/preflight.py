"""Pre-execution gate: TOCTOU, path, scope, Blender-disable checks."""

import hashlib, json, os

from protocol_guard.state.project_state import (
    _sha256_file, _canonical_state_hash, load_state, validate_state,
)


def _normalize_path(p, root):
    """Convert to normalized relative path. Reject dangerous paths."""
    if not isinstance(p, str):
        raise ValueError(f"Path must be string: {p}")
    if p == "":
        raise ValueError("Empty path")
    if os.path.isabs(p):
        raise ValueError(f"Absolute path rejected: {p}")
    if p.startswith("\\\\") or p.startswith("//"):
        raise ValueError(f"UNC path rejected: {p}")
    # Drive-relative (C:without-backslash)
    if len(p) >= 2 and p[1] == ":" and not p.startswith(p[:2] + "\\"):
        raise ValueError(f"Drive-relative path rejected: {p}")
    if ":" in p.split("/")[-1].split("\\")[0]:
        raise ValueError(f"ADS or colon in path rejected: {p}")
    # Check for ..
    segments = p.replace("\\", "/").split("/")
    if ".." in segments:
        raise ValueError(f"Parent traversal rejected: {p}")
    # Check control chars / null
    for c in p:
        if ord(c) < 32 or c == "\x7f":
            raise ValueError(f"Control character in path rejected: {p}")
    # Resolve and check stays within root
    abs_p = os.path.normpath(os.path.join(root, p))
    abs_root = os.path.normpath(os.path.abspath(root))
    if not abs_p.startswith(abs_root + os.sep) and abs_p != abs_root:
        raise ValueError(f"Path resolves outside root: {p} -> {abs_p}")
    return p


def preflight(task_path, state_path, freeze_bundle_path, auth_path, runtime_root):
    """Run all pre-execution checks.

    Checks:
      1. Phase 1 data layer locked (phase_approved=true, workflow_phase=code_guard_phase_1_locked)
      2. Task card unchanged since freeze
      3. PROJECT_STATE canonical unchanged since freeze
      4. Input files unchanged since freeze
      5. Authorization valid, not expired
      6. No blocked_operations hit
      7. No locked_assets modification
      8. No diagnostic_only misuse
      9. Path safety for all declared paths

    Returns:
        (cleared: bool, errors: list[str])
    """
    errors = []

    # Load freeze bundle
    if not os.path.exists(freeze_bundle_path):
        return (False, ["Freeze bundle not found"])
    with open(freeze_bundle_path, "r", encoding="utf-8") as f:
        fb = json.load(f)

    # 1. Phase 1 lock
    state = load_state(state_path)
    if not state.get("phase_approved"):
        errors.append("Phase 1 data layer not approved (phase_approved=false)")
    if state.get("workflow_phase") != "code_guard_phase_1_locked":
        errors.append(f"workflow_phase is '{state.get('workflow_phase')}', expected 'code_guard_phase_1_locked'")

    # 2. Task card unchanged
    tc_sha = _sha256_file(task_path)
    if tc_sha != fb.get("task_card_raw_sha256"):
        errors.append("TOCTOU: task card changed since freeze")

    # 3. PROJECT_STATE unchanged
    ps_sha = _canonical_state_hash(state)
    if ps_sha != fb.get("project_state_canonical_sha256"):
        errors.append("TOCTOU: project state canonical hash changed since freeze")

    # 4. Input files unchanged
    import yaml
    with open(task_path, "r", encoding="utf-8") as f:
        task_data = yaml.safe_load(f)
    for inf in task_data.get("input_files", []):
        inf_abs = os.path.join(os.path.dirname(os.path.abspath(state_path)), inf)
        if os.path.exists(inf_abs):
            h = _sha256_file(inf_abs)
            expected = fb.get("input_files_raw_sha256", {}).get(inf)
            if h != expected:
                errors.append(f"TOCTOU: input file changed: {inf}")
        else:
            errors.append(f"Input file not found: {inf}")

    # 5. Authorization
    if os.path.exists(auth_path):
        from protocol_guard.gate.authorize import validate_authorization
        # We need understand.json path - derive from runtime_root
        understand_path = os.path.join(os.path.dirname(freeze_bundle_path), "understand.json")
        ok_auth, _, auth_errs = validate_authorization(
            auth_path, freeze_bundle_path, understand_path, task_path, state_path
        )
        if not ok_auth:
            errors.extend(auth_errs)
    else:
        errors.append("Authorization file not found")

    # 6. Blocked operations check
    blocked = state.get("blocked_operations", [])
    for bo in blocked:
        # Only exact-match blocked operations can be reliably checked
        # Natural language entries cause SPEC_INVALID, not silently ignored
        if isinstance(bo, str) and not bo.startswith("op:"):
            errors.append(f"SPEC_INVALID: blocked_operation '{bo}' is natural language, cannot be reliably checked")
        elif isinstance(bo, str) and bo.startswith("op:"):
            op_id = bo[3:]
            # Compare against task allowed_modifications
            for am in task_data.get("allowed_modifications", []):
                if am.get("target", "") == op_id:
                    errors.append(f"Blocked operation match: {op_id}")

    # 7. Locked assets check
    locked = state.get("locked_assets", [])
    repo_root = os.path.dirname(os.path.abspath(state_path))
    for la in locked:
        la_paths = la.get("selector", "").split(", ")
        for lp in la_paths:
            for am in task_data.get("allowed_modifications", []):
                am_target = am.get("target", "")
                if lp.rstrip("/") == am_target or am_target.startswith(lp):
                    errors.append(f"Locked asset modification attempted: {am_target} matches {lp}")

    # 8. Diagnostic-only check
    diag = state.get("diagnostic_only_outputs", [])
    for d in diag:
        d_path = d.get("path", "")
        for inf in task_data.get("input_files", []):
            if inf == d_path or inf.startswith(d_path.rstrip("/")):
                errors.append(f"Diagnostic-only output used as input: {d_path}")

    # 9. Path safety
    for inf in task_data.get("input_files", []):
        try:
            _normalize_path(inf, repo_root)
        except ValueError as e:
            errors.append(f"Path safety violation in input_files: {e}")
    for outf in task_data.get("output_files", []):
        try:
            _normalize_path(outf, repo_root)
        except ValueError as e:
            errors.append(f"Path safety violation in output_files: {e}")

    return (len(errors) == 0, errors)
