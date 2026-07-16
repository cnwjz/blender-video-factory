# Phase 2A R2 Current Capability Audit

Date: 2026-07-15
Task: CODE_GUARD_PHASE_2A_0_R2_FINAL_DESIGN_CORRECTION
Previous: CODE_GUARD_PHASE_2A_0_R1_DESIGN_CORRECTION (GPT_REVIEW_FAILED)

---

## 1. Phase 1 Inventory

15 files in protocol_guard/. 121 passing tests. Locked.

---

## 2. R1 → R2 Correction Summary

| R1 Error | R2 Fix |
|----------|--------|
| task_card validation only claimed PASS | Real validate_task_card() executed. Result saved in task draft. |
| locked_items had notes field (schema violation) | Removed. |
| state_patch_requested requested PS write | Set to null. |
| claim mutable after creation | Split: claim.json (immutable, O_CREAT\|O_EXCL) + attempt_state.json (atomic transitions) |
| INDETERMINATE recovery underspecified | Full rules: detect→transition→block. EXECUTED+hashes→idempotent finalize. |
| Global string scan for bpy in gate/ | Replaced: executor import whitelist + AST check + subprocess intercept. Strategy code allowed to mention detection terms. |
| 24 files declared but actually 25 | Exact count: 33 output files (added attempt_state.py, recovery.py, test_adversarial.py, fixtures). |
| Evidence incomplete | Added: REPORT, SOURCE_SNAPSHOT, PROTECTED_FILES_INTEGRITY.json to evidence package. |
| Repo diff timing unclear | Specified: baseline before exec, after manifest before evidence write, compare. Clear exclusions. |
| Path rules had MAX_PATH | Removed. Replaced with structural rules (no .., no absolute, no UNC, no ADS, no out-of-root symlink). |
| Source evidence appendix lacked real test names | Each function now lists real test class/function names. |
| blocked_operations mapping not specified | Deterministic exact-match only. Natural language returns SPEC_INVALID. |

---

## 3. Source Evidence Appendix — Phase 1 Reuse with Real Test References

### 3.1 result.py

- **File**: `protocol_guard/result.py`
- **Public API**: `TechnicalResult(Enum)` — TECHNICAL_PASS, TECHNICAL_FAIL, CONSTRAINT_CONFLICT, EVIDENCE_INVALID, SPEC_INVALID
- **Public API**: `EvidenceStatus(Enum)` — VALID, RECOVERED, INVALID
- **Public API**: `VALID_TECHNICAL_RESULTS` (frozenset), `VALID_EVIDENCE_STATUSES` (frozenset)
- **Tests**: `TestTechnicalResult::test_valid_main_results`, `TestTechnicalResult::test_evidence_recovered_not_main_result`, `TestTechnicalResult::test_technical_pass_is_valid`, `TestTechnicalResult::test_illegal_result_rejected`, `TestTechnicalResult::test_evidence_recovered_is_not_a_technical_result`, `TestEvidenceStatus::test_valid_evidence_statuses`, `TestEvidenceStatus::test_illegal_evidence_status_rejected`
- **Reuse**: Direct import. All values immutable.
- **Private API risk**: None. All exports are public enums/constants.

### 3.2 task_schema.py

- **File**: `protocol_guard/task_schema.py`
- **Public API**: `validate_task_card(task_data, schema=None) → (bool, list[str])`
- **Public API**: `load_task_card(task_path) → dict`
- **Public API**: `validate_task_file(task_path) → (bool, list[str])`
- **Behavior**: JSON Schema structural check + 10 cross-field validations (parameter overlap, unique IDs, between/in operators, allowed/forbidden conflict, state_patch field whitelist from PS schema)
- **Tests**: `TestTaskCardValidationV2` (33 tests), `TestVisualIntentNaturalLanguage` (1 test). Key tests: `test_valid_task_passes`, `test_fixed_params_as_array_fails`, `test_dependent_variable_duplicate_name_fails`, `test_allowed_forbidden_same_target_same_field_fails`, `test_state_patch_unknown_ps_field_fails`
- **Reuse**: `validate_task_card()` for validate stage. `load_task_card()` for freeze stage.
- **Private API risk**: `_load_schema()`, `_load_ps_schema()`, `_get_ps_field_names()`, `_unique_ids()` are private. Phase 2A calls only public API.

### 3.3 project_state.py

- **File**: `protocol_guard/state/project_state.py`
- **Public API**: `validate_state(state_data, schema=None) → (bool, list[str])`
- **Public API**: `validate_patch(actor, patch_fields) → (bool, list, str)`
- **Public API**: `validate_patch_document(patch_doc) → (bool, list[str])`
- **Public API**: `apply_patch_document(state_data, patch_doc, approval=None) → (bool, dict, list[str])`
- **Public API**: `apply_patch(state_data, actor, patch_fields, approval=None) → (bool, dict, list[str])`
- **Public API**: `load_state(state_path) → dict`
- **Public API**: `save_state(state_data, state_path) → (bool, list[str])`
- **Public API**: `build_evidence_manifest(state_data, file_paths, task_id, manifest_path) → (bool, dict, str, list[str])`
- **Public API**: `verify_evidence_manifest(state_data, manifest_path, file_paths) → (bool, list[str])`
- **Public API**: `CLAUDE_WRITABLE` (frozenset)
- **Private (stable)**: `_canonical_state_hash(state_data) → str`, `_sha256_file(path) → str`, `_sha256_bytes(data) → str`, `_canonical_json(obj) → bytes`, `_validate_iso_datetime(value, field_name) → str|None`
- **Tests**: 75 tests across `TestProjectStateSchemaV2`, `TestFieldPermissions`, `TestApplyPatchDocument`, `TestStatePatchSchemaV2`, `TestSaveState`, `TestGptProposalLogging`, `TestProjectStateCoherence`, `TestEvidenceManifest`, `TestEnumsRegression`
- **Reuse**: `validate_state()` for preflight. `_canonical_state_hash()` for freeze+preflight. `_sha256_file()` for freeze+preflight+finalize. `_canonical_json()` for deterministic serialization. `_sha256_bytes()` for hash computation.
- **Private API risk**: `_sha256_file()` duplicated in snapshot.py. Phase 2A must import from one canonical source. `save_state()` and `apply_patch_document()` write to real files — Phase 2A-1 calls these only with temp dir paths, never real PROJECT_STATE path.

### 3.4 snapshot.py

- **File**: `protocol_guard/frozen/snapshot.py`
- **Public API**: `freeze_task(task_path, frozen_dir) → (bool, str|None, str)`
- **Public API**: `verify_frozen_task(task_path, frozen_dir) → (bool, str|None, str|None, str)`
- **Behavior**: Copies task YAML + writes SHA256 file. Rejects overwrite. Verify compares current SHA against stored.
- **Tests**: `TestFreezeTask::test_first_freeze_succeeds`, `TestFreezeTask::test_verify_succeeds_on_unchanged_task`, `TestFreezeTask::test_modified_task_fails_verification`, `TestFreezeTask::test_existing_frozen_rejects_overwrite`, `TestFreezeTask::test_freezing_nonexistent_dir_creates_it`
- **Reuse**: Task card raw-byte SHA256 capture for freeze_bundle.
- **Private API risk**: `_sha256_file()` duplicate — Phase 2A imports from project_state.py instead.

### 3.5 JSON Schemas

- **Files**: `task_card.schema.json`, `project_state.schema.json`, `state_patch.schema.json`
- **Tests**: Validated by all 121 tests. No dedicated schema-only tests.
- **Reuse**: Direct. No modification permitted.
- **Risk**: None.

---

## 4. R2 Architecture: New Module Tree

```
protocol_guard/
  gate/
    __init__.py
    freeze_bundle.py       # Multi-artifact freeze + post-freeze re-check
    understand.py          # Understanding record (binds freeze_bundle SHA256)
    authorize.py           # Immutable authorization validation
    claim.py               # Immutable claim (O_CREAT|O_EXCL)
    attempt_state.py       # Mutable attempt state (atomic tempfile+revalidate+os.replace)
    preflight.py           # Pre-execution gate
    executor.py            # Mock executor (import whitelist + AST + subprocess intercept)
    finalize.py            # Post-execution audit + repo diff
    conditions.py          # Stop condition evaluator
    recovery.py            # Crash recovery logic
  schemas/
    freeze_bundle.schema.json
    understand_record.schema.json
    authorization.schema.json
    claim.schema.json
    attempt_state.schema.json     # NEW (separated from claim)
    execution_result.schema.json
  gate/tests/
    __init__.py
    test_freeze_bundle.py
    test_understand.py
    test_authorize.py
    test_claim.py
    test_attempt_state.py
    test_preflight.py
    test_executor.py
    test_finalize.py
    test_conditions.py
    test_recovery.py
    test_integration.py
    test_adversarial.py            # Standalone adversarial suite
    fixtures/
      __init__.py
      mock_input.txt
```

No CLI. No modification to Phase 1 files.

---

## 5. R2 New Modules vs R1

| R1 Module | R2 Change |
|-----------|-----------|
| `gate/cli.py` | **REMOVED** |
| `gate/authorize.py` → validate only | Unchanged |
| `gate/claim.py` → mutable + immutable mixed | **SPLIT**: claim.py (immutable) + attempt_state.py (mutable, atomic transitions) |
| (not present) | `gate/recovery.py` — **NEW**: INDETERMINATE transition, idempotent finalize check |
| (not present) | `gate/tests/test_adversarial.py` — **NEW**: standalone adversarial suite |
| (not present) | `gate/tests/fixtures/mock_input.txt` — **NEW**: mock executor input |

---

## 6. Exact File Count

Total new files: 36

- 10 gate/ Python modules (no cli.py)
- 6 schemas
- 13 test modules (including __init__.py, fixtures/__init__.py)
- 1 mock_input.txt fixture
- 1 MOCK_EXECUTE_TEST/task.yaml
- 7 evidence files (generated, not source)

---

## 7. R2 Completion Criteria

1. Phase 1: 121 tests unchanged, all pass
2. Phase 2A: All new tests pass (unit + integration + adversarial)
3. Real PROJECT_STATE.yaml: byte-identical before/after
4. All Phase 1 source/schema/test/evidence: byte-identical before/after
5. No CLI module created
6. claim.json: immutable after O_CREAT|O_EXCL creation
7. attempt_state.json: atomic transitions via tempfile+revalidate+os.replace
8. Executor: import whitelist enforced, subprocess intercepted, AST-checked
9. Repo diff: baseline→after comparison, path traversal rejected
10. Evidence: 7-file package with PROTECTED_FILES_INTEGRITY.json
11. Evidence manifest: excludes itself and real PROJECT_STATE
12. Crash recovery: INDETERMINATE blocks automation, EXECUTED allows idempotent finalize
