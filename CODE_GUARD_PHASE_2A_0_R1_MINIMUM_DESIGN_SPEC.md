# Phase 2A R1 Minimum Design Spec

Date: 2026-07-15
Task: CODE_GUARD_PHASE_2A_0_R1_DESIGN_CORRECTION
Previous: CODE_GUARD_PHASE_2A_0_MINIMUM_DESIGN_SPEC (GPT_REVIEW_FAILED)

---

## 1. R1 Correction Summary

| # | v1 Error | R1 Fix |
|---|----------|--------|
| 1 | Real PROJECT_STATE written during finalize | Real PS read-only. All writes to temp fixtures. |
| 2 | Auth consumed in finalize | Atomic claim before execution. Separate claim artifact. |
| 3 | Auth scope included validate/freeze/understand | Scope: preflight + claim + execute + finalize only |
| 4 | Crash recovery: auth consumed before finalize | Claim before execute. INDETERMINATE state. |
| 5 | Freeze: understand bound to task_card SHA | understand binds freeze_bundle SHA256 |
| 6 | Undeclared: scan output dir only | Repo-level before/after diff |
| 7 | Evidence: shared dir with Phase 1 | Dedicated Phase 2A evidence dir |
| 8 | Bootstrapping: gate runs itself | Gate tested on fixtures only. Phase 2A-1 uses GPT+User approval. |
| 9 | Blender: "no import bpy" only | AST + subprocess + string + whitelist |
| 10 | CLI included | No CLI. Python API. |
| 11 | Tests incomplete | Full matrix: unit + integration + adversarial + concurrent + crash + path traversal |
| 12 | No source evidence appendix | Appendix in capability audit |
| 13 | Task draft not schema-validated | Validated against task_card.schema.json |

---

## 2. Architecture: New Module Tree

```
protocol_guard/
  gate/
    __init__.py
    freeze_bundle.py       # Multi-artifact freeze + post-freeze re-check
    understand.py          # Understanding record (binds freeze_bundle SHA)
    authorize.py           # Immutable authorization (validates, does not create)
    claim.py               # Atomic one-time claim (NEW — was part of finalize)
    preflight.py           # Pre-execution gate (includes Blender-disable checks)
    executor.py            # Mock executor (AST/subprocess/string/whitelist enforced)
    finalize.py            # Post-execution audit + repo diff (does NOT write real PS)
    conditions.py          # Stop condition evaluator
  schemas/
    freeze_bundle.schema.json
    understand_record.schema.json
    authorization.schema.json
    claim.schema.json              # NEW
    execution_result.schema.json
  gate/tests/
    __init__.py
    test_freeze_bundle.py
    test_understand.py
    test_authorize.py
    test_claim.py
    test_preflight.py
    test_executor.py
    test_finalize.py
    test_conditions.py
    test_integration.py
```

No CLI. No modifications to Phase 1 files.

---

## 3. Data Structures

### 3.1 Freeze Bundle

```json
{
  "task_id": "string",
  "frozen_at": "ISO 8601",
  "task_card_raw_sha256": "64-char hex",
  "project_state_canonical_sha256": "64-char hex",
  "input_files_raw_sha256": {"relative_path": "64-char hex"},
  "frozen_task_copy_path": "tasks/<task_id>/frozen_task.yaml",
  "post_freeze_recheck_passed": true
}
```

Post-freeze re-check: immediately after writing freeze_bundle.json, re-read all source files and re-compute SHA256. Any mismatch → delete freeze_bundle.json, return failure.

### 3.2 Understanding Record

```json
{
  "task_id": "string",
  "freeze_bundle_sha256": "64-char hex",
  "understood_by": "CLAUDE",
  "recorded_at": "ISO 8601",
  "task_goal": "string",
  "allowed_files": ["relative_path"],
  "forbidden_files": ["relative_path"],
  "input_files": ["relative_path"],
  "output_files": ["relative_path"],
  "preconditions": ["string"],
  "stop_conditions": ["string"],
  "blender_required": false,
  "spec_conflicts_found": false,
  "spec_conflicts_detail": []
}
```

Binding: `freeze_bundle_sha256` = SHA256 of freeze_bundle.json raw bytes. NOT the task card SHA256.

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
  "scope": ["preflight", "claim", "mock_execute", "finalize"],
  "allowed_modification_paths": ["relative_path"],
  "declared_output_paths": ["relative_path"],
  "issued_at": "ISO 8601",
  "expires_at": "ISO 8601 or null",
  "authorized_by": "USER",
  "gpt_review_reference": "string"
}
```

Immutable after creation. Scope explicitly excludes validate, freeze, understand, authorize.
Authorization is created externally (by user/GPT). Phase 2A code only validates it.

### 3.4 Claim (Atomic, One-Time)

```json
{
  "attempt_id": "string (UUID)",
  "authorization_id": "string",
  "authorization_sha256": "64-char hex",
  "task_id": "string",
  "status": "CLAIMED | EXECUTING | EXECUTED | FINALIZED | INDETERMINATE",
  "claimed_at": "ISO 8601",
  "process_id": "integer",
  "status_changed_at": "ISO 8601"
}
```

Atomic claim: file created with `status: CLAIMED` using O_CREAT|O_EXCL (or equivalent).
If file already exists → claim rejected (concurrent process already claimed).
Status transitions: CLAIMED → EXECUTING → EXECUTED → FINALIZED. INDETERMINATE if crash detected.

### 3.5 Execution Result

```json
{
  "task_id": "string",
  "attempt_id": "string",
  "authorization_sha256": "64-char hex",
  "claim_sha256": "64-char hex",
  "technical_result": "TECHNICAL_PASS | TECHNICAL_FAIL | ...",
  "started_at": "ISO 8601",
  "completed_at": "ISO 8601",
  "declared_output_files": {"relative_path": "64-char hex"},
  "repo_diff": {
    "added": ["relative_path"],
    "modified": ["relative_path"],
    "deleted": ["relative_path"],
    "unexpected": ["relative_path"]
  },
  "blender_call_detected": false,
  "stop_condition_triggered": false,
  "stop_condition": null,
  "errors": []
}
```

---

## 4. State Flow (Corrected)

```
[EXTERNAL: GPT + USER approve]
         │
TASK_CARD ──► validate ──► freeze ──► understand
         │
    [EXTERNAL: GPT reviews understand, USER creates authorization]
         │
authorization ──► preflight ──► claim ──► mock_execute ──► finalize
                   (reads       (atomic   (isolated      (repo diff
                    real PS      O_CREAT   temp dir)       + evidence
                    read-only)   |O_EXCL)                  dir only)
```

Phases 1-3 (validate/freeze/understand) run under existing GPT+User+Claude flow.
Phases 4-7 (preflight/claim/execute/finalize) are gated by authorization.
Real PROJECT_STATE is read-only throughout.

---

## 5. Stage Specifications (Key Changes Only)

### 5.2 freeze

Post-freeze re-check added:
1. Compute all hashes
2. Write freeze_bundle.json
3. Re-read all source files, re-compute all hashes
4. Any mismatch → delete freeze_bundle.json, return failure
5. Set `post_freeze_recheck_passed: true` in bundle

### 5.4 authorize

Phase 2A code only VALIDATES authorization. Does not create it.
Validation checks:
1. authorization_id is unique
2. All bound SHA256s match current artifacts
3. Scope does not exceed ["preflight","claim","mock_execute","finalize"]
4. Not expired
5. Claim file does not exist for this authorization_id (not yet claimed)

### 5.5 claim (NEW — was embedded in finalize)

Before any execution side effect:
1. Open claim file with O_CREAT|O_EXCL → atomic creation
2. If EEXIST → claim rejected, return failure
3. Write claim record with status=CLAIMED
4. Return claim record

After claim succeeds, status transitions:
- EXECUTING: set before executor starts
- EXECUTED: set after executor completes successfully
- FINALIZED: set after finalize completes
- INDETERMINATE: set if crash detected during EXECUTING (recovery only)

### 5.6 mock execute

Blender-disable enforcement (R1 expanded):
1. AST scan of all gate/*.py: no `import bpy` or `from bpy`
2. Subprocess interception: mock `subprocess.run`, `subprocess.Popen`, `os.system` to reject any call
3. String scan: reject any string containing "bpy", "blender", "blender.exe" in gate source
4. Operation whitelist: only `open()`, file read/write, `shutil.copy2`, `os.makedirs`, `os.path.exists`, `os.listdir` allowed
5. Isolation: mock executor runs in `tempfile.TemporaryDirectory()`, never touches real repo

All 5 checks verified by dedicated tests. Test independence: checks pass even if bpy is installed.

### 5.7 finalize

Repository-level diff (R1 expanded):
1. Before execution: capture full manifest of all files in scope (relative paths, SHA256)
2. After execution: re-scan same scope
3. Compare: new files, modified files, deleted files
4. Cross-reference against task_card.allowed_modifications and task_card.output_files
5. Any file NOT in allowed_modifications → undeclared modification → block TECHNICAL_PASS
6. Path traversal check: reject any path containing "..", absolute paths, junction/symlink targets outside repo

Evidence written to dedicated Phase 2A directory only.
Real PROJECT_STATE.yaml NOT written.

---

## 6. Crash Recovery (Corrected)

| Crash point | Claim status | Action |
|------------|-------------|--------|
| Before claim | N/A | Nothing claimed. Restart from preflight. |
| Claimed, before execute | CLAIMED | Executor not started. Can re-run execute with same claim. |
| During execute | EXECUTING → INDETERMINATE | Claim marked indeterminate. Outputs may be partial. New authorization required. |
| After execute, before finalize | EXECUTED | Outputs complete. Can re-run finalize with same claim (idempotent). |
| During finalize | EXECUTED | Finalize is idempotent: re-verify all output hashes, re-attempt. |
| INDETERMINATE state | INDETERMINATE | HUMAN AUDIT REQUIRED. No automatic retry. |

**Key rule**: Any INDETERMINATE state blocks automatic recovery. Human must inspect.

---

## 7. Path Traversal and Junction Rules

Reject any path that:
1. Contains ".." (parent directory traversal)
2. Is absolute (must be relative to repo root)
3. Resolves to a location outside repo root (via symlink or junction)
4. Contains control characters or null bytes
5. Exceeds MAX_PATH (260 chars on Windows)

All path checks applied to: input_files, output_files, allowed_modifications paths, evidence paths.

---

## 8. Hash Chain (R1 Corrected)

```
task_card_raw ──SHA256──► freeze_bundle.task_card_raw_sha256
                                         │
PROJECT_STATE canonical ──SHA256─────────┤
                                         │
input_files (each) ──SHA256──────────────┤
                                         │
                              freeze_bundle.json
                                    │
                              SHA256(freeze_bundle)
                                    │
                    understand_record.freeze_bundle_sha256
                                    │
                              SHA256(understand_record)
                                    │
                    authorization.understand_record_sha256
                                    │
                              SHA256(authorization)
                                    │
                         claim.authorization_sha256
                                    │
                              SHA256(claim)
                                    │
                    execution_result.claim_sha256
```

Each artifact binds the SHA256 of its predecessor. No self-reference.

Evidence manifest: built only from declared_output_files + execution_result.json. Excludes authorization, claim, freeze_bundle, understand_record, and evidence_manifest itself.

---

## 9. Evidence Directory Isolation

Phase 2A evidence path: `reviews/PROTOCOL_IMPLEMENTATION_HISTORY/CODE_GUARD_PHASE_2A_1_IMPLEMENTATION/`

Phase 1 files NOT overwritten:
- `pytest_output.txt`
- `adversarial_test_output.txt`
- `evidence_manifest.json`
- `PROJECT_STATE.yaml`
- Any Phase 1 report or source snapshot

Evidence generation order (within Phase 2A dir):
1. pytest_output.txt (frozen first)
2. adversarial_test_output.txt (frozen second)
3. execution_result.json (frozen third)
4. evidence_manifest.json (built last, excludes itself and PS)

---

## 10. Test Matrices (R1 Expanded)

### Unit Tests (minimum 60)

| Module | Min tests | Key scenarios |
|--------|-----------|---------------|
| conditions | 6 | Each action type, unknown condition, required vs optional |
| freeze_bundle | 8 | Deterministic, re-freeze rejected, post-freeze re-check, mid-freeze change detected, input file missing |
| understand | 6 | All fields, missing freeze, duplicate reject, field extraction from task card |
| authorize | 10 | All bindings match, each binding mismatch, expired, scope violation, missing GPT ref |
| claim | 8 | Atomic create, double claim rejected, status transitions, concurrent claim (file lock) |
| preflight | 10 | All checks pass, each check fails individually, TOCTOU types, path traversal in input, Blender-block checks |
| executor | 8 | Runs in temp dir, produces declared output, AST no-bpy, subprocess blocked, string scan, whitelist enforced |
| finalize | 8 | Repo diff: no unexpected, new file detected, modified file detected, deleted file detected, path traversal in output, undeclared blocks TECHNICAL_PASS |

### Integration Test (1)

Full pipeline: mock task → validate → freeze → understand → (mock auth) → preflight → claim → execute → finalize → verify all artifacts in hash chain.

### Adversarial Tests (minimum 15)

| # | Test |
|---|------|
| 1 | TOCTOU: task card modified after freeze |
| 2 | TOCTOU: input file modified after freeze |
| 3 | TOCTOU: PROJECT_STATE canonical changed after freeze |
| 4 | Double claim rejected (concurrent via file lock) |
| 5 | Authorization with wrong freeze_bundle SHA rejected |
| 6 | Authorization with wrong understand_record SHA rejected |
| 7 | Expired authorization rejected at preflight |
| 8 | Missing authorization blocks preflight |
| 9 | Claim status INDETERMINATE blocks automatic retry |
| 10 | Crash during execute: claim INDETERMINATE, outputs not finalized |
| 11 | Crash after execute: finalize idempotent re-run succeeds |
| 12 | Path traversal in input_file rejected ("../../../etc/passwd") |
| 13 | Absolute path in output_file rejected |
| 14 | `import bpy` in gate source detected by AST check |
| 15 | `subprocess.run(["blender.exe"])` in gate source detected |
| 16 | Undeclared new file in repo blocks TECHNICAL_PASS |
| 17 | Undeclared modified file in repo blocks TECHNICAL_PASS |
| 18 | All Phase 1 files byte-identical before/after Phase 2A-1 |

---

## 11. File Inventory (Corrected)

### Created (no CLI)

```
protocol_guard/gate/__init__.py
protocol_guard/gate/conditions.py
protocol_guard/gate/freeze_bundle.py
protocol_guard/gate/understand.py
protocol_guard/gate/authorize.py
protocol_guard/gate/claim.py              # NEW (was part of finalize)
protocol_guard/gate/preflight.py
protocol_guard/gate/executor.py
protocol_guard/gate/finalize.py

protocol_guard/schemas/freeze_bundle.schema.json
protocol_guard/schemas/understand_record.schema.json
protocol_guard/schemas/authorization.schema.json
protocol_guard/schemas/claim.schema.json           # NEW
protocol_guard/schemas/execution_result.schema.json

protocol_guard/gate/tests/__init__.py
protocol_guard/gate/tests/test_conditions.py
protocol_guard/gate/tests/test_freeze_bundle.py
protocol_guard/gate/tests/test_understand.py
protocol_guard/gate/tests/test_authorize.py
protocol_guard/gate/tests/test_claim.py
protocol_guard/gate/tests/test_preflight.py
protocol_guard/gate/tests/test_executor.py
protocol_guard/gate/tests/test_finalize.py
protocol_guard/gate/tests/test_integration.py

tasks/MOCK_EXECUTE_TEST/task.yaml
```

Total: 24 new files. 0 files modified.

---

## 12. Acceptance Criteria (Corrected)

1. Phase 1: 121 tests pass, unchanged
2. Phase 2A: >= 60 unit + >= 15 adversarial + 1 integration, all pass
3. Real PROJECT_STATE.yaml: SHA256 unchanged from baseline
4. All Phase 1 source/schema/test files: SHA256 unchanged from baseline
5. Phase 1 evidence files: SHA256 unchanged from baseline
6. No CLI module created
7. No `import bpy` or `blender.exe` string in any gate/*.py
8. No `subprocess.run`/`Popen`/`os.system` in gate code outside test-mocked calls
9. Mock executor output only in temp directories
10. Authorization model: immutable record + atomic claim + INDETERMINATE recovery
11. Repo diff detects added/modified/deleted/undeclared files
12. Path traversal and absolute paths rejected at validate and preflight
13. All 5 new schemas pass jsonschema meta-validation
