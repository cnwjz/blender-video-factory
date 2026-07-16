# Phase 2A R2 Minimum Design Spec

Date: 2026-07-15
Task: CODE_GUARD_PHASE_2A_0_R2_FINAL_DESIGN_CORRECTION

---

## 1. R2 Correction Register

| # | Issue | Fix |
|---|-------|-----|
| 1 | Task card validation not actually run | Real validate_task_card() executed. is_valid=True, errors=[]. Recorded with YAML SHA256. |
| 2 | locked_items had notes field (schema violation) | Removed from all locked_items entries. |
| 3 | state_patch_requested requested PS mutation | Set to null. Real PS read-only throughout. |
| 4 | Claim mutable + immutable conflated | Split: claim.json (immutable, O_CREAT\|O_EXCL) + attempt_state.json (atomic transitions). |
| 5 | Crash recovery underspecified | Full INDETERMINATE rules. EXECUTED→idempotent finalize. CLAIMED→can retry. |
| 6 | Global string scan for bpy in whole gate/ dir | Replaced: executor import whitelist, AST check, subprocess intercept. Detection terms allowed in strategy code/tests/errors. |
| 7 | File count off by one | Exact: 36 new source files, 33 output_files declared. |
| 8 | Evidence incomplete | 7-file package: REPORT, SOURCE_SNAPSHOT, PROTECTED_FILES_INTEGRITY.json, pytest_output, adversarial_output, execution_result, evidence_manifest. |
| 9 | Repo diff timing and exclusions unclear | Specified: pre-exec baseline → post-exec after-manifest → compare before evidence write. Exclusions listed. |
| 10 | PATH_MAX 260 limit | Removed. Structural rules: no .., no absolute, no UNC, no ADS, no out-of-root symlink/junction. |
| 11 | Source appendix lacked real test names | Each function now references real test class/method names. |
| 12 | blocked_operations mapping unspecified | Exact string match only. Natural language → SPEC_INVALID. Path-based checks use normalized relative paths. |
| 13 | Evidence manifest self-reference rules incomplete | 7-file package: first 6 files frozen then manifest built from them. Manifest excludes itself and real PS. |

---

## 2. Architecture: Module Tree (Final)

```
protocol_guard/gate/
  __init__.py
  freeze_bundle.py       # Atomic multi-artifact freeze + post-freeze re-check
  understand.py          # Understanding record → binds freeze_bundle SHA256
  authorize.py           # Immutable authorization validation (does not create)
  claim.py               # Immutable claim: O_CREAT|O_EXCL, never modified after creation
  attempt_state.py       # Mutable: CLAIMED→EXECUTING→EXECUTED→FINALIZED (or INDETERMINATE)
                         #   Each transition: tempfile write → re-read → validate → os.replace
  preflight.py           # Pre-execution gate checks
  executor.py            # Mock executor: import whitelist, AST-checked, subprocess-intercepted
  finalize.py            # Post-execution: repo diff, evidence, does NOT write real PS
  conditions.py          # Stop condition evaluator
  recovery.py            # Crash recovery: detect INDETERMINATE, check idempotent finalize
```

---

## 3. Data Structures (Key Changes Only)

### 3.1 Claim (Immutable)

```json
{
  "authorization_id": "string",
  "authorization_sha256": "64-char hex",
  "attempt_id": "string (UUID)",
  "task_id": "string",
  "claimed_at": "ISO 8601",
  "process_id": "integer"
}
```

Created via open() with O_CREAT|O_EXCL. Never modified after creation.
Stored at: `tasks/<task_id>/claim.json`

### 3.2 Attempt State (Mutable, Atomic Transitions)

```json
{
  "attempt_id": "string",
  "status": "CLAIMED | EXECUTING | EXECUTED | FINALIZED | INDETERMINATE",
  "status_changed_at": "ISO 8601",
  "process_id": "integer"
}
```

Each transition: write to tempfile → re-read → validate → os.replace.
Stored at: `tasks/<task_id>/attempt_state.json`

### 3.3 Authorization (Immutable)

```json
{
  "authorization_id": "string",
  "task_id": "string",
  "task_card_sha256": "64-char hex",
  "freeze_bundle_sha256": "64-char hex",
  "understand_record_sha256": "64-char hex",
  "project_state_sha256": "64-char hex",
  "input_files_sha256": {"relative_path": "64-char hex"},
  "scope": ["preflight", "mock_execute", "finalize"],
  "allowed_modification_paths": ["relative_path"],
  "declared_output_paths": ["relative_path"],
  "issued_at": "ISO 8601",
  "expires_at": "ISO 8601 or null",
  "authorized_by": "USER",
  "gpt_review_reference": "string"
}
```

Scope does NOT include validate, freeze, understand, authorize, or claim — those are pre-authorization stages.

---

## 4. 7-Stage Pipeline (Claim is Internal to Execute)

```
[PRE-AUTHORIZATION — runs under existing GPT+User+Claude flow]
  1. validate   → Schema + cross-field + stop conditions
  2. freeze     → Multi-artifact bundle + post-freeze re-check
  3. understand → Structured record bound to freeze_bundle_sha256

[EXTERNAL: GPT reviews understand, USER creates authorization]

[POST-AUTHORIZATION — gated by authorization + claim]
  4. preflight  → All TOCTOU + path + scope checks (reads real PS, does not write)
  5. execute    → [internal: claim (immutable)] → [internal: attempt_state CLAIMED→EXECUTING]
                  → mock execute in temp workspace
                  → [internal: attempt_state EXECUTED]
  6. finalize   → Repo diff → build evidence in Phase 2A dir → [internal: attempt_state FINALIZED]
                  (does NOT write real PROJECT_STATE)

[EVIDENCE]
  7. (evidence generation — part of finalize)
     → CODE_GUARD_PHASE_2A_1_REPORT.md
     → CODE_GUARD_PHASE_2A_1_SOURCE_SNAPSHOT.txt
     → CODE_GUARD_PHASE_2A_1_PROTECTED_FILES_INTEGRITY.json
     → pytest_output.txt, adversarial_test_output.txt
     → execution_result.json
     → evidence_manifest.json
```

---

## 5. Crash Recovery Rules (R2 Detailed)

### 5.1 Recovery Function

```python
def recover(task_id) -> (recoverable: bool, action: str, detail: str):
    claim = read_claim(task_id)
    if claim is None:
        return (True, "RETRY_PREFLIGHT", "No claim exists, safe to retry from preflight")

    attempt = read_attempt_state(task_id)

    if attempt.status == "CLAIMED":
        return (True, "RETRY_EXECUTE", "Claimed but not started. Can execute with same claim.")
    elif attempt.status == "EXECUTING":
        # Check if execution_result.json exists and is complete
        if not has_complete_execution_result(task_id):
            transition_to_indeterminate(task_id, attempt)
            return (False, "HUMAN_AUDIT_REQUIRED",
                    "Attempt was EXECUTING but no complete result. Transitioned to INDETERMINATE.")
        # Has complete result — unusual but handle
        return (False, "HUMAN_AUDIT_REQUIRED",
                "Attempt EXECUTING but complete result found. Inconsistent state.")
    elif attempt.status == "EXECUTED":
        if not has_complete_execution_result(task_id):
            transition_to_indeterminate(task_id, attempt)
            return (False, "HUMAN_AUDIT_REQUIRED",
                    "Attempt marked EXECUTED but no complete result.")
        # Safe to idempotently finalize
        return (True, "IDEMPOTENT_FINALIZE",
                "Execution complete. Can run finalize (idempotent).")
    elif attempt.status == "FINALIZED":
        return (True, "DONE", "Already finalized. No action needed.")
    elif attempt.status == "INDETERMINATE":
        return (False, "HUMAN_AUDIT_REQUIRED",
                "Attempt is INDETERMINATE. Human inspection required.")
```

### 5.2 Idempotent Finalize

When `recover()` returns `IDEMPOTENT_FINALIZE`:
1. Verify all declared output file SHA256s match execution_result
2. If execution_result.json already exists: verify it, do NOT regenerate timestamp
3. Build/verify evidence manifest (if evidence_manifest.json already exists: verify only)
4. Do NOT re-consume authorization (already claimed)
5. Do NOT re-write claim.json (immutable)
6. Transition attempt_state: EXECUTED → FINALIZED

### 5.3 INDETERMINATE Transition

```python
def transition_to_indeterminate(task_id, attempt):
    new_state = {
        "attempt_id": attempt["attempt_id"],
        "status": "INDETERMINATE",
        "status_changed_at": now_iso(),
        "process_id": os.getpid(),
    }
    atomic_write_attempt_state(task_id, new_state)
```

After INDETERMINATE: no automatic retry, no automatic finalize, no automatic re-claim.

---

## 6. Blender Disable (R2 Replaced)

### 6.1 Executor Import Whitelist

Only these modules may be imported in executor.py:
- `os`, `os.path`, `sys`, `json`, `hashlib`, `shutil`, `copy`, `tempfile`, `yaml`, `pathlib`
- `protocol_guard.gate.*` (own package)

Forbidden imports (enforced by AST scan):
- `bpy`, `subprocess`, `ctypes`, `multiprocessing`, `win32api`, `win32com`, `_winapi`, `msvcrt`, `signal`, `socket`, `http`, `urllib`, `requests`, `threading` (for process spawning), `concurrent.futures`

### 6.2 Subprocess Intercept (Test-Time)

In test environment, monkeypatch to raise on any call:
- `subprocess.run`
- `subprocess.Popen`
- `subprocess.call`
- `subprocess.check_call`
- `subprocess.check_output`
- `os.system`
- `os.popen`
- `os.spawn*`

### 6.3 AST Import Scan

Parse executor.py AST. Walk all Import and ImportFrom nodes. Reject any module not in whitelist.

### 6.4 String Check Scope

Strategy code, tests, and error messages MAY contain "bpy", "blender", "blender.exe" — these are detection terms and acceptable in security enforcement code.

---

## 7. Repo Diff Specification

### 7.1 Timing

1. **T1**: Before mock execute — generate baseline manifest (all tracked files, relative paths, raw SHA256)
2. **T2**: After mock execute completes, before finalize evidence writes — generate after-manifest
3. Compare: added = in T2 not in T1, modified = in both with different SHA, deleted = in T1 not in T2
4. Cross-reference against task_card.allowed_modifications and task_card.output_files
5. Only after comparison passes → write evidence to Phase 2A evidence dir

### 7.2 Excluded Paths

```
.git/
reviews/UPLOAD_NEXT/
reviews/PROTOCOL_IMPLEMENTATION_HISTORY/CODE_GUARD_PHASE_2A_1_IMPLEMENTATION/
__pycache__/
*.pyc
.pytest_cache/
*.pyo
```

Test execution: `PYTHONDONTWRITEBYTECODE=1` + `pytest -p no:cacheprovider`

### 7.3 Path Rejection Rules

```
Reject if path:
  - Contains ".." as a path segment
  - Is absolute (starts with / or C:\\)
  - Is a Windows UNC path (starts with \\\)
  - Is a drive-relative path (starts with C: without \\)
  - Contains NTFS alternate data stream (contains :)
  - Contains control characters or null bytes
  - Resolves (via realpath) to a location outside repo root
  - Is a symlink or junction pointing outside repo root
```

---

## 8. Evidence Package (7 Files)

1. `CODE_GUARD_PHASE_2A_1_REPORT.md` — Implementation report
2. `CODE_GUARD_PHASE_2A_1_SOURCE_SNAPSHOT.txt` — Full source of all new gate modules + tests
3. `CODE_GUARD_PHASE_2A_1_PROTECTED_FILES_INTEGRITY.json` — Before/after SHA256 of all protected files
4. `pytest_output.txt` — Full pytest output (Phase 1 + Phase 2A)
5. `adversarial_test_output.txt` — Standalone adversarial test output
6. `execution_result.json` — Structured execution result
7. `evidence_manifest.json` — SHA256 manifest of files 1-6 (excludes itself and real PS)

### 8.1 PROTECTED_FILES_INTEGRITY.json Structure

```json
{
  "recorded_at": "ISO 8601",
  "task_id": "CODE_GUARD_PHASE_2A_1_IMPLEMENTATION",
  "protected_files": {
    "PROJECT_STATE.yaml": {
      "before_sha256": "hex",
      "after_sha256": "hex",
      "unchanged": true
    },
    "protocol_guard/result.py": {
      "before_sha256": "hex",
      "after_sha256": "hex",
      "unchanged": true
    }
  },
  "summary": {
    "total_protected": 0,
    "unchanged": 0,
    "added": [],
    "modified": [],
    "deleted": []
  }
}
```

---

## 9. blocked_operations, locked_assets, diagnostic_only_outputs

### 9.1 blocked_operations

Stored as `array[string]` in PROJECT_STATE. Phase 2A preflight compares task_card allowed_modifications and operation descriptions against these strings using **exact match only**.

Natural language entries (e.g., "禁止恢复正式相机构图") cannot be reliably interpreted by code. When a task card references an operation that could plausibly match a natural-language blocked_operation but no exact string match exists → preflight returns `SPEC_INVALID` or `CONSTRAINT_CONFLICT` with the ambiguous entries listed. No fuzzy matching.

### 9.2 locked_assets

Structured list in PROJECT_STATE. Preflight checks:
1. Task card allowed_modifications targets do not match any locked_asset path/selector
2. Task card does not request modification of locked_asset protected_fields
3. Path matching uses normalized relative paths

### 9.3 diagnostic_only_outputs

Structured list in PROJECT_STATE. Preflight checks:
1. Task card does not reference any diagnostic_only output as a formal input or required dependency
2. Task card does not request promotion of diagnostic output to production asset

---

## 10. Test Matrices

### Unit Tests (10 modules × ~7 tests each = ~70)

### Adversarial Tests (test_adversarial.py, standalone, ~18)

| # | Test |
|---|------|
| 1 | TOCTOU: task card modified after freeze |
| 2 | TOCTOU: input file modified after freeze |
| 3 | TOCTOU: PROJECT_STATE canonical changed after freeze |
| 4 | Double claim rejected via O_CREAT\|O_EXCL |
| 5 | Authorization with wrong freeze_bundle SHA rejected |
| 6 | Authorization with wrong understand_record SHA rejected |
| 7 | Expired authorization rejected at preflight |
| 8 | Missing authorization blocks preflight |
| 9 | INDETERMINATE blocks automatic retry |
| 10 | Crash during EXECUTING → transition to INDETERMINATE |
| 11 | EXECUTED with complete outputs → idempotent finalize |
| 12 | Path traversal in input_file rejected |
| 13 | Absolute path in output_file rejected |
| 14 | UNC path rejected |
| 15 | executor.py does not import bpy (AST verified) |
| 16 | executor.py does not import subprocess (AST verified) |
| 17 | Undeclared new file blocks TECHNICAL_PASS |
| 18 | Undeclared modified file blocks TECHNICAL_PASS |
| 19 | All Phase 1 files byte-identical before/after |
| 20 | Real PROJECT_STATE byte-identical before/after |

### Integration Test (1)

Full pipeline: fixture task → validate → freeze → understand → (mock auth) → preflight → claim → execute → finalize.
Verify all 7 evidence files generated. Verify hash chain integrity.

---

## 11. Exact File Inventory

### Created (36 new files)

**gate/ modules (10)**:
1. protocol_guard/gate/__init__.py
2. protocol_guard/gate/freeze_bundle.py
3. protocol_guard/gate/understand.py
4. protocol_guard/gate/authorize.py
5. protocol_guard/gate/claim.py
6. protocol_guard/gate/attempt_state.py
7. protocol_guard/gate/preflight.py
8. protocol_guard/gate/executor.py
9. protocol_guard/gate/finalize.py
10. protocol_guard/gate/conditions.py
11. protocol_guard/gate/recovery.py

**schemas (6)**:
12. protocol_guard/schemas/freeze_bundle.schema.json
13. protocol_guard/schemas/understand_record.schema.json
14. protocol_guard/schemas/authorization.schema.json
15. protocol_guard/schemas/claim.schema.json
16. protocol_guard/schemas/attempt_state.schema.json
17. protocol_guard/schemas/execution_result.schema.json

**tests (13)**:
18. protocol_guard/gate/tests/__init__.py
19. protocol_guard/gate/tests/test_freeze_bundle.py
20. protocol_guard/gate/tests/test_understand.py
21. protocol_guard/gate/tests/test_authorize.py
22. protocol_guard/gate/tests/test_claim.py
23. protocol_guard/gate/tests/test_attempt_state.py
24. protocol_guard/gate/tests/test_preflight.py
25. protocol_guard/gate/tests/test_executor.py
26. protocol_guard/gate/tests/test_finalize.py
27. protocol_guard/gate/tests/test_conditions.py
28. protocol_guard/gate/tests/test_recovery.py
29. protocol_guard/gate/tests/test_integration.py
30. protocol_guard/gate/tests/test_adversarial.py

**fixtures (2)**:
31. protocol_guard/gate/tests/fixtures/__init__.py
32. protocol_guard/gate/tests/fixtures/mock_input.txt

**task (1)**:
33. tasks/MOCK_EXECUTE_TEST/task.yaml

**Evidence (7, generated not source)**:
34-40. (Generated during finalize)

**Modified: 0 files.**
