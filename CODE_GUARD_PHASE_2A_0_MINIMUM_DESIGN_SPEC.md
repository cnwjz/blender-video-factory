# Phase 2A Minimum Design Spec

Date: 2026-07-15
Task: CODE_GUARD_PHASE_2A_0_SINGLE_TASK_GATE_DESIGN_AUDIT

---

## 1. Architecture: New Module Tree

```
protocol_guard/
  gate/                              # ALL new Phase 2A code
    __init__.py
    conditions.py                    # Stop condition evaluator
    freeze_bundle.py                 # Multi-artifact atomic freeze
    understand.py                    # Structured understanding record
    authorize.py                     # One-time authorization lifecycle
    preflight.py                     # Pre-execution gate checker
    executor.py                      # Mock executor (no Blender)
    finalize.py                      # Post-execution audit + state update
    cli.py                           # Single entry point
  schemas/
    understand_record.schema.json    # NEW — understanding record
    authorization.schema.json        # NEW — auth token
    freeze_bundle.schema.json        # NEW — multi-artifact freeze
    execution_result.schema.json     # NEW — structured result
  gate/
    tests/
      test_conditions.py
      test_freeze_bundle.py
      test_understand.py
      test_authorize.py
      test_preflight.py
      test_executor.py
      test_finalize.py
```

---

## 2. Data Structures

### 2.1 Freeze Bundle (`freeze_bundle.schema.json`)

```json
{
  "task_id": "string",
  "task_card_sha256": "64-char hex",
  "project_state_sha256": "64-char hex (canonical with evidence_sha256=null)",
  "input_files": {"path": "sha256"},
  "frozen_at": "ISO 8601 with timezone"
}
```

Stored at: `tasks/<task_id>/freeze_bundle.json`

### 2.2 Understanding Record (`understand_record.schema.json`)

```json
{
  "task_id": "string",
  "freeze_bundle_sha256": "64-char hex",
  "understood_by": "CLAUDE",
  "recorded_at": "ISO 8601",
  "task_goal": "string",
  "allowed_modifications": ["string"],
  "forbidden_files": ["string"],
  "input_files": ["string"],
  "output_files": ["string"],
  "preconditions": ["string"],
  "stop_conditions": ["string"],
  "blender_required": "bool",
  "spec_conflicts_found": "bool",
  "spec_conflicts_detail": ["string"]
}
```

Stored at: `tasks/<task_id>/understand.json`

### 2.3 Authorization (`authorization.schema.json`)

```json
{
  "task_id": "string",
  "task_card_sha256": "64-char hex",
  "project_state_sha256": "64-char hex",
  "input_files_sha256": {"path": "sha256"},
  "scope": ["validate", "freeze", "understand", "authorize", "preflight", "execute", "finalize"],
  "issued_at": "ISO 8601",
  "expires_after": "ISO 8601 or null",
  "consumed": false,
  "consumed_at": null,
  "approved_by": "USER"
}
```

Stored at: `approvals/<task_id>.json`

### 2.4 Execution Result (`execution_result.schema.json`)

```json
{
  "task_id": "string",
  "authorization_sha256": "64-char hex",
  "technical_result": "TECHNICAL_PASS | TECHNICAL_FAIL | ...",
  "started_at": "ISO 8601",
  "completed_at": "ISO 8601",
  "output_files": {"path": "sha256"},
  "declared_modifications": ["string"],
  "undeclared_modifications": ["string"],
  "stop_condition_triggered": "bool",
  "stop_condition": "string or null",
  "errors": ["string"]
}
```

Stored at: `evidence/<task_id>/execution_result.json`

---

## 3. State Flow: The 7 Stages

```
TASK_CARD.yaml ──► [1. validate] ──► [2. freeze] ──► [3. understand]
                                                          │
                                                    [4. authorize]
                                                    (GPT + USER)
                                                          │
                                                    [5. preflight]
                                                          │
                                                    [6. mock execute]
                                                          │
                                                    [7. finalize]
```

**Every stage returns (success, result_data, errors).**
**Any failure at any stage blocks all subsequent stages.**

---

## 4. Stage Specifications

### 4.1 validate

```
Input:  PROJECT_STATE.yaml path, task_card.yaml path
Output: (is_valid, errors)
Exit:   0 = valid, 1 = invalid, 2 = constraint conflict

Checks:
  1. PROJECT_STATE is valid (reuse validate_state)
  2. Task card is valid (reuse validate_task_card)
  3. Stop conditions in task card do not preclude execution
  4. Allowed modifications do not conflict with locked_assets
  5. Allowed modifications do not hit blocked_operations
```

### 4.2 freeze

```
Input:  PROJECT_STATE.yaml path, task_card.yaml path
Output: freeze_bundle.json
Exit:   0 = frozen, 1 = freeze failed

Actions:
  1. SHA256(task_card) — reuse _sha256_file
  2. Canonical PROJECT_STATE SHA256 — reuse _canonical_state_hash
  3. SHA256(each input_file in task card) — reuse _sha256_file
  4. Build freeze_bundle dict → validate against schema
  5. Write freeze_bundle.json
  6. Reject if freeze_bundle already exists (no silent overwrite)
```

### 4.3 understand

```
Input:  freeze_bundle.json, task_card.yaml
Output: understand.json
Exit:   0 = recorded, 1 = failed

Actions:
  1. Verify freeze_bundle.json SHA256 matches task card
  2. Extract structured understanding from task card fields
  3. Build understand_record dict → validate against schema
  4. Write understand.json
  5. Reject if understand.json already exists
```

### 4.4 authorize

```
Input:  understand.json, freeze_bundle.json
Output: approval token file (empty — validation only in Phase 2A)
Exit:   0 = authorized, 1 = rejected

Phase 2A scope:
  - Design the authorization data structure
  - Implement authorization lifecycle (create, check, consume)
  - GPT reviews understand.json externally
  - User provides authorization token via separate mechanism
  - Code validates token but does not create it (creation is external)

Authorization check:
  1. authorization.json exists at approvals/<task_id>.json
  2. task_id matches
  3. task_card_sha256 matches current freeze bundle
  4. project_state_sha256 matches current freeze bundle
  5. consumed == false
  6. Not expired (if expires_after is set)
```

### 4.5 preflight

```
Input:  freeze_bundle.json, authorization.json, task_card.yaml, PROJECT_STATE.yaml
Output: (ok, errors)
Exit:   0 = cleared, 1 = blocked, 2 = needs re-freeze

Checks (all must pass):
  1. phase_approved == true
  2. workflow_phase == "code_guard_phase_1_locked"
  3. project_work_paused == true
  4. Task card SHA256 == freeze_bundle.task_card_sha256
  5. PROJECT_STATE canonical SHA == freeze_bundle.project_state_sha256
  6. All input files SHA256 == freeze_bundle.input_files
  7. Authorization exists, not consumed, not expired
  8. No task operation hits blocked_operations
  9. No task operation modifies locked_assets
  10. No task operation uses diagnostic_only outputs as formal assets
```

### 4.6 mock execute

```
Input:  task_card.yaml (must declare task_type: PROTOCOL_MAINTENANCE)
Output: execution_output/ directory with result files
Exit:   0 = success, 1 = execution failed

Mock task (no Blender):
  - Read input_file (text)
  - Transform content (uppercase, line count, etc.)
  - Write output_file (text)
  - Return structured result

Blender-free proof:
  - executor.py imports list must not include bpy
  - Test asserts "import bpy" raises ImportError in executor context
```

### 4.7 finalize

```
Input:  freeze_bundle.json, authorization.json, execution result data, output directory
Output: Updated PROJECT_STATE.yaml, execution_result.json, evidence manifest
Exit:   0 = finalized, 1 = finalization failed

Actions:
  1. Build execution_result dict → validate against schema
  2. Compute SHA256 of all actual output files
  3. Compare actual outputs to declared output_files in task card
  4. Detect undeclared file modifications (files in output dir not in task card)
  5. Mark authorization consumed: consumed=true, consumed_at=now
  6. Update PROJECT_STATE via apply_patch_document (CLAUDE actor):
     - last_task_id, last_technical_result, evidence_status, last_execution_time
     - output_files, evidence_sha256
  7. Build evidence manifest for output files
  8. Write execution_result.json
```

---

## 5. Failure Flows

| Stage | Failure | State impact | Recovery |
|-------|---------|-------------|----------|
| validate | Any check fails | None | Fix task card or PROJECT_STATE, re-run |
| freeze | SHA mismatch on existing freeze | None | Bump task_card_version or new task_id |
| understand | Freeze bundle missing | None | Re-run freeze |
| authorize | Auth file missing or invalid | None | Get GPT review + user approval |
| preflight | TOCTOU detected | None | Re-freeze required |
| preflight | Auth consumed | None (already consumed) | New task_id required |
| execute | Execution fails mid-way | Partial output files | Re-run with new authorization (old one consumed) |
| finalize | Evidence verification fails | Authorization consumed, state NOT updated | Manual audit |

**Any failure keeps PROJECT_STATE unchanged. Authorization is consumed ONLY in finalize (not before).**

---

## 6. Crash Recovery

| Crash point | State on restart | Action |
|------------|-----------------|--------|
| After freeze | freeze_bundle exists | validate → preflight (skip freeze, understand) |
| After understand | understand + freeze exist | authorize (skip to auth) |
| After authorize | Auth exists, not consumed | preflight |
| After preflight clears | freeze + auth valid | re-run execute |
| During execute | freeze + auth valid | re-run execute with new authorization |
| After execute, before finalize | outputs exist, auth consumed | MANUAL: audit outputs, decide |
| During finalize | Auth consumed but state not updated | MANUAL: re-run finalize or revert |

---

## 7. TOCTOU Detection

All freeze-time hashes (task card, state, inputs) are stored in freeze_bundle.json.
Preflight re-computes all three and compares against freeze bundle.
Any mismatch → block execution, requires re-freeze.

Input files are hashed as raw bytes — modification, truncation, and replacement all detected.

---

## 8. Undeclared Modification Detection

Finalize compares:
- task_card.output_files (declared)
- Actual files found in output directory (actual)

Files in actual but not in declared → `undeclared_modifications` array in execution_result.
This does NOT block finalization — it is recorded for audit.

Files in declared but not in actual → error (missing declared output).

---

## 9. CLI Entry Points (Python API, not shell commands in Phase 2A)

```python
# All return (success, data, errors)
gate.validate(task_path, state_path) -> (bool, dict, list)
gate.freeze(task_path, state_path) -> (bool, dict, list)
gate.understand(task_path, freeze_dir) -> (bool, dict, list)
gate.authorize(task_id, approvals_dir) -> (bool, dict, list)   # checks, does not create
gate.preflight(task_path, state_path, task_id) -> (bool, dict, list)
gate.execute(task_path, task_id, auth_path) -> (bool, dict, list)
gate.finalize(task_path, state_path, task_id) -> (bool, dict, list)
```

Exit codes: 0=success, 1=general failure, 2=constraint conflict, 3=evidence invalid, 4=spec invalid.

---

## 10. Minimum Test Matrix

| # | Test | Category |
|---|------|----------|
| 1 | Valid task passes validate | validate |
| 2 | Task with blocked_operation conflict fails validate | validate |
| 3 | Freeze produces deterministic SHA bundle | freeze |
| 4 | Re-freeze on same task rejected | freeze |
| 5 | Understand records all required fields | understand |
| 6 | Understand without freeze fails | understand |
| 7 | Authorization check passes for valid token | authorize |
| 8 | Already-consumed auth rejected | authorize |
| 9 | Expired auth rejected | authorize |
| 10 | Wrong task_card_sha256 in auth rejected | authorize |
| 11 | Preflight passes with all checks | preflight |
| 12 | TOCTOU task card change blocks preflight | preflight |
| 13 | TOCTOU input file change blocks preflight | preflight |
| 14 | Blocked operation hit blocks preflight | preflight |
| 15 | Mock executor runs without Blender | execute |
| 16 | Mock executor produces declared outputs | execute |
| 17 | Finalize produces correct execution_result | finalize |
| 18 | Finalize detects undeclared file | finalize |
| 19 | Finalize consumes authorization | finalize |
| 20 | Full pipeline end-to-end with mock task | integration |

---

## 11. Adversarial Test Matrix

| # | Test |
|---|------|
| 1 | Modified task card after freeze detected at preflight |
| 2 | Modified input file after freeze detected at preflight |
| 3 | Modified PROJECT_STATE after freeze detected at preflight |
| 4 | Double-authorization consumption rejected |
| 5 | Crash after execute — outputs preserved, state unchanged |
| 6 | Crash during finalize — auth consumed, no partial state |
| 7 | Missing authorization blocks execution |
| 8 | Expired authorization blocks execution |
| 9 | Replay of old freeze_bundle with new task rejected |
| 10 | Mock executor cannot import bpy |

---

## 12. Files to Create (Exact)

### Python modules
1. `protocol_guard/gate/__init__.py`
2. `protocol_guard/gate/conditions.py`
3. `protocol_guard/gate/freeze_bundle.py`
4. `protocol_guard/gate/understand.py`
5. `protocol_guard/gate/authorize.py`
6. `protocol_guard/gate/preflight.py`
7. `protocol_guard/gate/executor.py`
8. `protocol_guard/gate/finalize.py`
9. `protocol_guard/gate/cli.py`

### Schemas
10. `protocol_guard/schemas/understand_record.schema.json`
11. `protocol_guard/schemas/authorization.schema.json`
12. `protocol_guard/schemas/freeze_bundle.schema.json`
13. `protocol_guard/schemas/execution_result.schema.json`

### Tests
14. `protocol_guard/gate/tests/__init__.py`
15. `protocol_guard/gate/tests/test_conditions.py`
16. `protocol_guard/gate/tests/test_freeze_bundle.py`
17. `protocol_guard/gate/tests/test_understand.py`
18. `protocol_guard/gate/tests/test_authorize.py`
19. `protocol_guard/gate/tests/test_preflight.py`
20. `protocol_guard/gate/tests/test_executor.py`
21. `protocol_guard/gate/tests/test_finalize.py`

### Task card (for mock execution)
22. `tasks/MOCK_EXECUTE_TEST/task.yaml`

### Files to modify
**None.** Phase 1 code and schemas are unchanged.

### PROJECT_STATE updates during Phase 2A
Only via `apply_patch_document()` in finalize stage. Fields: last_task_id, last_technical_result, evidence_status, last_execution_time, output_files, evidence_sha256, change_log (append). All using existing CLAUDE actor permissions.

---

## 13. Acceptance Criteria

1. `python -m pytest protocol_guard/tests/ protocol_guard/gate/tests/ -v` — all pass (Phase 1 121 + Phase 2A new)
2. Full mock pipeline completes without error
3. No `import bpy` or `blender.exe` in any new module
4. Zero Phase 1 file modifications
5. Zero Phase 1 schema modifications
6. PROJECT_STATE.phase_approved remains true throughout
7. All 4 new schemas pass jsonschema meta-validation
