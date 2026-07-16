# Phase 2A Minimum Rebuild Spec — R1 Corrected

Date: 2026-07-16
Task: CODE_GUARD_PHASE_2A_ROOT_CAUSE_AUDIT_R1_CORRECTION
Classification: **PARTIAL_REBUILD_PHASE_2A**

---

## 1. Architecture: Two-Stage Model

```
Stage A: prepare_task(task_path, state_path, runtime_root)

  task.yaml ──► validate ──► freeze ──► understand
                                         │
  Outputs (in runtime_root/preparations/<task_id>/<prepare_id>/):
    frozen_task.yaml
    freeze_bundle.json
    understand.json
    prepare_package.json

  prepare_package.json binds:
    prepare_id, task_id, task_card_raw_sha256, frozen_task_sha256,
    freeze_bundle_sha256, understand_record_sha256,
    project_state_canonical_sha256, input_files_raw_sha256,
    allowed_modification_paths, declared_output_paths, created_at

  STOPS HERE. Does NOT proceed to execution.

    ═══════════ EXTERNAL BOUNDARY ═══════════
    GPT reviews understand.json
    User creates authorization.json (immutable)
    authorization binds prepare_package_sha256
    ═══════════════════════════════════════════

Stage B: execute_authorized_task(auth_path, prepare_package_path, runtime_root)

  1. Read prepare_package.json, verify Schema
  2. Verify all prepare artifacts exist and SHA256 match
  3. Read authorization.json, verify Schema
  4. Verify authorization.prepare_package_sha256 matches
  5. Verify ALL authorization bindings match prepare artifacts
  6. preflight (TOCTOU, paths, blocked_ops)
  7. If preflight fails → return (False, None, errors). NO claim created.
  8. claim (internal, O_CREAT|O_EXCL, path: executions/<task_id>/authorizations/<auth_id>/)
  9. Create workspace inside runtime_root (verify: in root, empty, not symlink)
  10. mock_execute in workspace (import whitelist, AST, no subprocess)
  11. workspace_diff (before execute vs after execute)
  12. finalize (result + attempt_state FINALIZED)

  Outputs ALL in: runtime_root/executions/<task_id>/authorizations/<auth_id>/
    claim.json, attempt_state.json, execution_result.json, workspace/
```

---

## 2. Public API (Only Two Functions)

```python
# protocol_guard/gate/prepare.py
def prepare_task(task_path: str, state_path: str, runtime_root: str) -> tuple[bool, dict, list[str]]

# protocol_guard/gate/execute.py
def execute_authorized_task(auth_path: str, prepare_package_path: str, runtime_root: str) -> tuple[bool, dict, list[str]]
```

**No other public functions in the gate package.** `claim` creation is an internal (underscore-prefixed) function, not exported from `protocol_guard.gate`.

---

## 3. Precise Directory Layout

```
runtime_root/
  preparations/
    <task_id>/
      <prepare_id>/
        frozen_task.yaml
        freeze_bundle.json
        understand.json
        prepare_package.json

  executions/
    <task_id>/
      authorizations/
        <authorization_id>/
          claim.json          (O_CREAT|O_EXCL, immutable)
          attempt_state.json  (atomic transitions)
          execution_result.json
          workspace/          (created by Stage B internally)
```

**claim uniqueness**: `task_id + authorization_id` path + `O_CREAT|O_EXCL`. `attempt_id` stored inside claim, not used as path component.

**workspace**: Created internally by Stage B. Verified: realpath inside runtime_root, empty before execution, not symlink/junction.

---

## 4. Authorization Structure (Immutable)

```json
{
  "authorization_id": "string",
  "task_id": "string",
  "prepare_id": "string",
  "prepare_package_sha256": "64-char hex",
  "task_card_sha256": "64-char hex",
  "frozen_task_sha256": "64-char hex",
  "freeze_bundle_sha256": "64-char hex",
  "understand_record_sha256": "64-char hex",
  "project_state_canonical_sha256": "64-char hex",
  "input_files_sha256": {"relative_path": "64-char hex"},
  "allowed_modification_paths": ["relative_path"],
  "declared_output_paths": ["relative_path"],
  "scope": ["execute_authorized_task"],
  "issued_at": "ISO 8601",
  "expires_at": "ISO 8601 or null",
  "authorized_by": "USER",
  "gpt_review_reference": "string"
}
```

All set comparisons are **exact equality** — no subset/superset.
`scope` is exactly `["execute_authorized_task"]`.

**requested_operation_ids**: REMOVED from this MVP. Phase 1 task card Schema does not include it and must not be modified. Future: use independent `operation_request` artifact.

---

## 5. freeze_bundle REWRITE_WITH_PRIMITIVE_REUSE

Keep from current `freeze_bundle.py`:
- `_sha256_file(path)` → raw byte SHA256
- `_canonical_state_hash(state_data)` → canonical JSON SHA
- `_canonical_json(obj)` → deterministic JSON

Rewrite the orchestration to:
1. `validate_task_card(task_data)` via Phase 1
2. `validate_state(state_data)` via Phase 1
3. Compute task card raw SHA256
4. Compute state canonical SHA256
5. Compute all input file raw SHA256s
6. Copy frozen task → compute frozen_task_sha256 → verify == task_card_sha256
7. Post-freeze re-check of ALL source hashes
8. On ANY mismatch: delete frozen_task.yaml, delete temp bundle, return failure
9. Write freeze_bundle.json via: tempfile → flush → fsync → os.replace → re-read → Schema verify → hash re-compute
10. Reject if prepare directory already exists

`freeze_bundle.schema.json`: add optional `prepare_id` field.

---

## 6. Python Contract Boundary

Code Guard is a **protocol and audit layer**, not an OS security sandbox.

**Cannot claim**:
- Python module calls cannot be bypassed by importing internal functions directly
- OS-level process isolation
- Cryptographic actor identity verification

**Can claim**:
- Public API surface is exactly `prepare_task` and `execute_authorized_task`
- No single public function crosses the external authorization boundary
- Tests verify that there is no single-function path from prepare to execute
- `__all__` export list enforces public API surface

Internal functions (claim, attempt_state transition) are underscore-prefixed and not exported from `protocol_guard.gate`.

---

## 7. Invariant-Based Test Strategy

No test count target. Each invariant must have at least 4 test categories: **Success, Failure, Bypass, Tamper**.

| # | Invariant | Success | Failure | Bypass | Tamper |
|---|-----------|---------|---------|--------|--------|
| 1 | Stage A and Stage B are separate, no single function crosses boundary | Stage A produces package, Stage B called separately | N/A (structural) | No public function does both | prepare artifacts cannot serve as auth |
| 2 | prepare_package cannot be forged | Valid package verifies | Missing field rejected | Wrong SHA rejected | Tampered field rejected |
| 3 | Authorization binds ALL prepare artifacts | All bindings match → valid | Any single binding mismatch → invalid | Missing binding → invalid | Swapped binding → invalid |
| 4 | No claim without valid authorization | Valid auth → claim created | Missing auth → no claim | Invalid auth → no claim | Replayed auth → no claim |
| 5 | Preflight failure → zero side effects | Preflight passes → claim exists | Preflight fails → claim file absent | Preflight skipped → claim absent | TOCTOU change → preflight fails |
| 6 | One claim per authorization | First claim succeeds | Second claim rejected | Different auth_id → different path | Same auth_id → EEXIST |
| 7 | Executor only writes declared outputs in workspace | Declared output in workspace → ok | Output outside workspace → fail | Extra output → fail | Missing output → fail |
| 8 | Undeclared workspace change → no TECHNICAL_PASS | Clean workspace → PASS | New file → FAIL | Modified file → FAIL | Deleted file → FAIL |
| 9 | Failed result cannot become success | Original PASS → idempotent returns PASS | Original FAIL → idempotent returns FAIL | Overwrite attempt → blocked | Timestamp change → blocked |
| 10 | Existing evidence not overwritten | New result written to unique path | Existing result → verify only | Overwrite → blocked | Timestamp regeneration → blocked |
| 11 | Phase 1 and root files not written | Phase 1 SHA unchanged | Any Phase 1 file change → blocked | Direct write → blocked | Accidental overwrite → detected |
| 12 | No public single-function auth bypass | Both stages called separately | N/A (structural) | Internal function not exported | __all__ verified |
| 13 | Evidence target not a locked Phase 1.4 path | Unique build_id → ok | Existing build_id → stopped | Locked path → blocked | Root redirect → blocked |

Test names must describe the invariant, not the implementation detail. Examples:
- `test_claim_refused_when_authorization_missing` (not `test_create_claim_returns_false`)
- `test_workspace_new_file_detected_as_undeclared` (not `test_finalize_detects_added`)

---

## 8. Evidence Path Isolation

### Runtime evidence (Stage B output)
```
runtime_root/executions/<task_id>/authorizations/<auth_id>/
  claim.json, attempt_state.json, execution_result.json, workspace/
```
Never written to project root.

### Implementation evidence (separate workflow)
```
reviews/PROTOCOL_IMPLEMENTATION_HISTORY/CODE_GUARD_PHASE_2A_REBUILD/<build_id>/
```

**build_id**: unique (timestamp + uuid suffix). If directory exists → stop, error.

### Implementation evidence workflow:
1. Record Phase 1.4 + PROJECT_STATE SHA256 baseline
2. Run pytest → output ONLY to `<build_id>/pytest_output.txt`
3. Run adversarial → output ONLY to `<build_id>/adversarial_test_output.txt`
4. Generate report → `<build_id>/REPORT.md`
5. Verify Phase 1.4 + PROJECT_STATE SHA256 unchanged
6. Verify Phase 1 source files unchanged
7. If `protected_files_unchanged: false` → force `TECHNICAL_FAIL`
8. Do NOT generate `TECHNICAL_PASS` if integrity check fails
9. Build manifest from frozen evidence files
10. Verify: no self-reference, no PROJECT_STATE.yaml in manifest

---

## 9. Precise Migration Plan

### Keep on disk (no modification)
- `protocol_guard/gate/__init__.py`
- `protocol_guard/gate/claim.py`
- `protocol_guard/gate/attempt_state.py`
- `protocol_guard/gate/conditions.py`
- `protocol_guard/schemas/claim.schema.json`
- `protocol_guard/schemas/attempt_state.schema.json`
- `protocol_guard/gate/tests/__init__.py`
- `protocol_guard/gate/tests/fixtures/__init__.py`
- `protocol_guard/gate/tests/fixtures/mock_input.txt`

### Rewrite in place (new content)
- `protocol_guard/gate/freeze_bundle.py` → keep hashing primitives, rewrite orchestration
- `protocol_guard/gate/understand.py` → derive values from task card
- `protocol_guard/gate/authorize.py` → add prepare_package_sha256, full bindings
- `protocol_guard/gate/preflight.py` → all failures blocking, use auth paths
- `protocol_guard/gate/executor.py` → minimal whitelist, workspace verification
- `protocol_guard/gate/finalize.py` → real workspace_diff, idempotent preservation
- `protocol_guard/schemas/freeze_bundle.schema.json`
- `protocol_guard/schemas/understand_record.schema.json`
- `protocol_guard/schemas/authorization.schema.json`
- `protocol_guard/schemas/execution_result.schema.json`
- All test files except `test_conditions.py`, `test_recovery.py`, `test_integration.py`
- `tasks/MOCK_EXECUTE_TEST/task.yaml`

### Create new
- `protocol_guard/gate/prepare.py` — Stage A entry point
- `protocol_guard/gate/execute.py` — Stage B entry point

### Delete from disk
- `protocol_guard/gate/pipeline.py`
- `protocol_guard/gate/tests/test_integration.py`

### Defer (keep on disk, do not import)
- `protocol_guard/gate/recovery.py`
- `protocol_guard/gate/tests/test_recovery.py`

---

## 10. Acceptance Criteria

1. Stage A produces valid prepare_package with all 4 artifacts
2. Stage A does not produce claim, attempt_state, or execution_result
3. Stage B called with valid auth + prepare_package → completes with TECHNICAL_PASS
4. Stage B called with invalid/missing auth → returns failure, no claim created
5. Stage B called with auth binding mismatch → returns failure, no claim created
6. Preflight failure → no claim.json exists on disk
7. Workspace new file → finalize returns TECHNICAL_FAIL
8. Workspace modified file → finalize returns TECHNICAL_FAIL
9. Existing FAIL result → finalize returns False (does not overwrite)
10. Existing PASS result → idempotent finalize returns True (does not regenerate)
11. No project root file modified during Stage B
12. `__all__` in `protocol_guard/gate/__init__.py` exports only `prepare_task`, `execute_authorized_task`
13. No test verifies `isinstance`, `len()`, or `os.path.exists` as primary assertion
14. All invariant tests pass
15. Phase 1: 121 tests unchanged
16. Real PROJECT_STATE.yaml SHA256 unchanged
17. Phase 1.4 evidence SHA256s unchanged
18. No CLI, no Blender, no subprocess
