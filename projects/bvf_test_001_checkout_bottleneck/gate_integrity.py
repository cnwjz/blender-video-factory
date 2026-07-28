"""
Gate integrity functions — importable by both production pipeline and tests.
All functions are pure: no side effects, no Blender dependency, no file writes.
"""
import json, time
from pathlib import Path


def build_supplemental_result(check_errors, run_id=None):
    """Build supplemental result from dict of {check_name: [error_strings]}."""
    checks = {}
    total = 0
    for name, errs in check_errors.items():
        checks[name] = {"errors": len(errs), "pass": len(errs) == 0}
        total += len(errs)
    result = {"pass": total == 0, "checks": checks, "total_errors": total}
    if run_id: result["run_id"] = run_id
    return result


def compute_gate_result(build, auto, formal, supplemental, run_id=None,
                        gc_runs=0, cc_runs=0, pg_passes=0):
    """Pure function: compute gate result from sub-step boolean outcomes."""
    all_ok = bool(build and auto and formal and supplemental)
    return {
        "run_id": run_id or "",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "build_pass": bool(build), "auto_framing_pass": bool(auto),
        "formal_preflight_pass": bool(formal), "supplemental_pass": bool(supplemental),
        "gc_runs": gc_runs, "cc_runs": cc_runs, "pg_passes": pg_passes,
        "all_pass": all_ok, "key_frame_preview_authorized": all_ok,
        "full_render_authorized": False,
    }


def validate_run_results(run_dir, expected_run_id):
    """Validate run directory: all JSONs present, matching run_id,
    AND sub-results consistent with gate result.
    Returns (is_valid, errors_list).
    """
    errors = []
    run_path = Path(run_dir)

    # ── Load all files ──
    files_data = {}
    required = ["event_frames.json", "formal_preflight_summary.json",
                "supplemental_check.json", "production_gate_result.json"]
    for fname in required:
        fp = run_path / fname
        if not fp.is_file():
            errors.append(f"missing:{fname}")
            continue
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            errors.append(f"invalid_json:{fname}:{e}")
            continue
        rid = data.get("run_id")
        if rid is None:
            errors.append(f"no_run_id:{fname}")
        elif rid != expected_run_id:
            errors.append(f"run_id_mismatch:{fname} got={rid} expected={expected_run_id}")
        files_data[fname] = data

    # Need at least gate result for cross-validation
    gate = files_data.get("production_gate_result.json")
    formal = files_data.get("formal_preflight_summary.json")
    suppl = files_data.get("supplemental_check.json")
    if gate is None:
        return len(errors) == 0, errors

    # ── Cross-validate formal vs gate ──
    if formal:
        # formal_preflight_summary: dynamic_failed > 0 means formal failed
        formal_failed = formal.get("dynamic_failed", 0) > 0
        formal_static_fail = not formal.get("static_pass", True)
        formal_had_fail = formal_failed or formal_static_fail

        gate_says_formal_pass = gate.get("formal_preflight_pass", False)
        if formal_had_fail and gate_says_formal_pass:
            errors.append("inconsistent:formal_had_failures_but_gate_says_formal_pass")

        gate_says_all_pass = gate.get("all_pass", False)
        if formal_had_fail and gate_says_all_pass:
            errors.append("inconsistent:formal_failed_but_all_pass_true")

    # ── Cross-validate supplemental vs gate ──
    if suppl:
        suppl_pass = suppl.get("pass", False)
        suppl_errors = suppl.get("total_errors", 0)

        gate_says_suppl_pass = gate.get("supplemental_pass", False)
        if not suppl_pass and gate_says_suppl_pass:
            errors.append("inconsistent:supplemental_failed_but_gate_says_pass")

        if suppl_errors > 0 and gate.get("all_pass", False):
            errors.append("inconsistent:supplemental_has_errors_but_all_pass_true")

    # ── Cross-validate preview authorization ──
    all_passed = (gate.get("build_pass") and gate.get("auto_framing_pass") and
                  gate.get("formal_preflight_pass") and gate.get("supplemental_pass"))
    if not all_passed and gate.get("key_frame_preview_authorized", False):
        errors.append("inconsistent:not_all_pass_but_preview_authorized")

    all_pass_val = gate.get("all_pass", False)
    if all_pass_val != all_passed:
        errors.append("inconsistent:all_pass_mismatches_sub_passes")

    return len(errors) == 0, errors


def validate_snapshot_set(snapshot_dir, event_frames):
    """Verify snapshot .blend set exactly matches event frames."""
    sp = Path(snapshot_dir)
    if not sp.is_dir(): return False, ["snap_dir_missing"]
    expected = {f"snapshot_{f:04d}.blend" for f in event_frames}
    actual = {p.name for p in sp.glob("snapshot_*.blend")}
    missing = expected - actual; extra = actual - expected
    errors = []
    if missing: errors.append(f"missing_snapshots:{len(missing)}")
    if extra: errors.append(f"extra_snapshots:{len(extra)}")
    return len(errors) == 0, errors


def validate_preview_set(run_dir, expected_files):
    """Verify preview PNG set exactly matches expected list."""
    rp = Path(run_dir)
    actual = {p.name for p in rp.glob("frame_*.png")} if rp.is_dir() else set()
    expected = set(expected_files)
    missing = expected - actual; extra = actual - expected
    errors = []
    if missing: errors.append(f"missing_previews:{len(missing)}")
    if extra: errors.append(f"extra_previews:{len(extra)}")
    return len(errors) == 0, errors


def authorize_preview_render(gate_result_path, run_id):
    """Read production_gate_result.json and verify authorization."""
    try:
        data = json.loads(Path(gate_result_path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as e:
        return False, f"cannot_read_gate_result:{e}"
    file_rid = data.get("run_id")
    if file_rid is None: return False, "no_run_id_in_gate_result"
    if file_rid != run_id: return False, f"run_id_mismatch: file={file_rid} expected={run_id}"
    if not data.get("all_pass", False): return False, "all_pass_is_false"
    if not data.get("key_frame_preview_authorized", False):
        return False, "key_frame_preview_not_authorized"
    if data.get("full_render_authorized", False):
        return False, "full_render_authorized_is_true"
    return True, "ok"
