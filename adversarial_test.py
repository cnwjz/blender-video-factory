"""Phase 1.4 Adversarial Integrity Test — pre-manifest verification only.

Verifies 7 properties that must hold before evidence_manifest.json is built:
  1. reread validation failure leaves no temp file
  2. read exception leaves no temp file
  3. replace exception leaves original intact
  4. valid save leaves no temp file
  5. manifest builder has no self reference
  6. tampered report is detected
  7. tampered state is detected

Post-freeze final package verification runs separately and its result is
not written into any file that belongs to the evidence manifest.
"""

import copy
import os
import sys
import tempfile
import glob as globmod

sys.path.insert(0, os.path.dirname(__file__))

from protocol_guard.state.project_state import (
    save_state,
    load_state,
    validate_state,
    _write_yaml_unchecked,
    build_evidence_manifest,
    verify_evidence_manifest,
    _sha256_file,
)

import yaml

PASS = 0
FAIL = 0


def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS: {label}")
    else:
        FAIL += 1
        print(f"  FAIL: {label} — {detail}")


def _base_state():
    return {
        "protocol_version": "v1.0",
        "project_id": "adv_p14",
        "workflow_phase": "testing",
        "scene_phase": "adv_phase",
        "phase_approved": False,
        "project_work_paused": True,
        "last_task_id": "ADV_14_TEST",
        "last_task_card_sha256": None,
        "last_technical_result": "TECHNICAL_PASS",
        "evidence_status": "VALID",
        "evidence_sha256": None,
        "output_files": ["test.md"],
        "last_execution_time": "2026-07-15T14:45:00+08:00",
        "locked_assets": [],
        "unlocked_assets": [],
        "diagnostic_only_outputs": [],
        "pending_review": None,
        "blocked_operations": [],
        "failed_paths": [],
        "change_log": [
            {
                "timestamp": "2026-01-01T00:00:00+00:00",
                "actor": "SYSTEM_MIGRATION",
                "task_id": "INIT",
                "fields_changed": ["initial_state"],
                "reason": "Initial",
            }
        ],
    }


def _write_file(td, name, content):
    p = os.path.join(td, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    return p


print("=== Phase 1.4 Adversarial Integrity Test ===\n")

# 1. reread validation failure leaves no temp file
print("1. Reread validation failure leaves no temp file")
with tempfile.TemporaryDirectory() as td:
    sp = os.path.join(td, "state.yaml")

    def fake_write_bad(data, path):
        bad = copy.deepcopy(data)
        bad["last_technical_result"] = "BOGUS"
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(bad, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    import protocol_guard.state.project_state as ps_mod
    orig_write = ps_mod._write_yaml_unchecked
    ps_mod._write_yaml_unchecked = fake_write_bad
    try:
        ok, _ = save_state(_base_state(), sp)
        check("reread fail returns False", not ok)
        check("no file created", not os.path.exists(sp))
        temps = globmod.glob(os.path.join(td, ".project_state_tmp_*"))
        check("no temp files left", len(temps) == 0, str(temps))
    finally:
        ps_mod._write_yaml_unchecked = orig_write

# 2. read exception leaves no temp file
print("\n2. Read exception leaves no temp file")
with tempfile.TemporaryDirectory() as td:
    sp = os.path.join(td, "state.yaml")

    def fake_write_garbage(data, path):
        with open(path, "wb") as f:
            f.write(b"\x00\x01\x02NOT_YAML")

    ps_mod._write_yaml_unchecked = fake_write_garbage
    try:
        ok, _ = save_state(_base_state(), sp)
        check("read exception returns False", not ok)
        temps = globmod.glob(os.path.join(td, ".project_state_tmp_*"))
        check("no temp files left", len(temps) == 0, str(temps))
    finally:
        ps_mod._write_yaml_unchecked = orig_write

# 3. replace exception leaves original intact
print("\n3. Replace exception leaves original intact")
with tempfile.TemporaryDirectory() as td:
    sp = os.path.join(td, "state.yaml")
    state = _base_state()
    ok1, _ = save_state(state, sp)
    check("initial save succeeds", ok1)
    with open(sp, "rb") as f:
        original = f.read()

    orig_replace = os.replace
    def fake_replace(src, dst):
        raise OSError("Simulated failure")
    os.replace = fake_replace
    try:
        ok2, _ = save_state(state, sp)
        check("replace exception returns False", not ok2)
        with open(sp, "rb") as f:
            current = f.read()
        check("original file bytes unchanged", current == original)
        temps = globmod.glob(os.path.join(td, ".project_state_tmp_*"))
        check("no temp files left", len(temps) == 0, str(temps))
    finally:
        os.replace = orig_replace

# 4. valid save leaves no temp file
print("\n4. Valid save leaves no temp file")
with tempfile.TemporaryDirectory() as td:
    sp = os.path.join(td, "state.yaml")
    ok, _ = save_state(_base_state(), sp)
    check("valid save succeeds", ok)
    check("file exists", os.path.exists(sp))
    temps = globmod.glob(os.path.join(td, ".project_state_tmp_*"))
    check("no temp files left", len(temps) == 0, str(temps))

# 5. manifest has no self reference
print("\n5. Manifest has no self reference")
with tempfile.TemporaryDirectory() as td:
    state = _base_state()
    state["last_task_id"] = "SELF_REF_TEST"
    files = {}
    for i, name in enumerate(["report.md", "snap.txt", "pytest.txt", "adv.txt"]):
        files[name] = _write_file(td, name, f"content_{i}")
    mp = os.path.join(td, "evidence_manifest.json")
    ok, manifest, msha, errs = build_evidence_manifest(state, files, "SELF_REF_TEST", mp)
    check("build succeeds", ok, str(errs))
    mfiles = manifest.get("files", {})
    check("no evidence_manifest.json in files", "evidence_manifest.json" not in mfiles)
    check("no PROJECT_STATE.yaml in files", "PROJECT_STATE.yaml" not in mfiles)

# 6. tampered report is detected
print("\n6. Tampered report is detected")
with tempfile.TemporaryDirectory() as td:
    state = _base_state()
    state["last_task_id"] = "TAMPER_RPT"
    files = {}
    for i, name in enumerate(["report.md", "snap.txt", "pytest.txt", "adv.txt"]):
        files[name] = _write_file(td, name, f"v{i}")
    mp = os.path.join(td, "evidence_manifest.json")
    build_evidence_manifest(state, files, "TAMPER_RPT", mp)
    state["evidence_sha256"] = _sha256_file(mp)
    ok1, _ = verify_evidence_manifest(state, mp, files)
    check("initial verify passes", ok1)
    with open(files["report.md"], "w") as f:
        f.write("TAMPERED CONTENT")
    ok2, _ = verify_evidence_manifest(state, mp, files)
    check("tampered report detected", not ok2)

# 7. tampered state is detected
print("\n7. Tampered state is detected")
with tempfile.TemporaryDirectory() as td:
    state = _base_state()
    state["last_task_id"] = "TAMPER_STATE"
    files = {}
    for i, name in enumerate(["rpt.md", "snap.txt", "pytest.txt", "adv.txt"]):
        files[name] = _write_file(td, name, f"v{i}")
    mp = os.path.join(td, "evidence_manifest.json")
    build_evidence_manifest(state, files, "TAMPER_STATE", mp)
    state["evidence_sha256"] = _sha256_file(mp)
    ok1, _ = verify_evidence_manifest(state, mp, files)
    check("initial verify passes", ok1)
    state["last_task_id"] = "CHANGED_STATE"
    ok2, _ = verify_evidence_manifest(state, mp, files)
    check("tampered state detected", not ok2)

print(f"\n{'='*50}")
print(f"RESULTS: {PASS} passed, {FAIL} failed")
print(f"{'='*50}")
sys.exit(0 if FAIL == 0 else 1)
