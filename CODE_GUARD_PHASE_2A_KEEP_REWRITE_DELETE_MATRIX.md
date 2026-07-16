# Phase 2A KEEP / REWRITE / DELETE / DEFER Matrix — R1 Corrected

Date: 2026-07-16
Task: CODE_GUARD_PHASE_2A_ROOT_CAUSE_AUDIT_R1_CORRECTION
Classification: PARTIAL_REBUILD_PHASE_2A

---

## Gate Modules (11 files)

### protocol_guard/gate/__init__.py
- **Current role**: Package marker, empty
- **Defects**: None
- **Dependencies**: None
- **Conclusion**: **KEEP**

### freeze_bundle.py
- **Current role**: Multi-artifact freeze with post-freeze re-check
- **Defects**: Freeze doesn't validate state before freezing. Post-freeze failure doesn't clean up incomplete files. Missing flush+fsync+re-read+Schema re-verify+hash re-compute chain. No prepare_id.
- **Dependencies**: Used by understand, authorize, preflight
- **Retention risk**: Medium. Hashing primitives are correct but the orchestration needs hardening.
- **Conclusion**: **REWRITE_WITH_PRIMITIVE_REUSE** — Keep `_sha256_file`, `_canonical_state_hash`, `_canonical_json`. Rewrite orchestration to add: validate_task_card, validate_state, frozen copy SHA verification, cleanup on post-freeze failure, flush+fsync+os.replace+re-read+Schema re-verify+hash re-compute, reject overwrite of existing prepare dir.

### understand.py
- **Current role**: Reads task card + freeze bundle, produces immutable understand record
- **Defects**: Hardcodes `blender_required=False` and `spec_conflicts_found=False`. Does not extract allowed/forbidden file lists from actual task card analysis.
- **Dependencies**: Used by prepare_task
- **Retention risk**: Low. Data structure is sound, content derivation needs fix.
- **Conclusion**: **REWRITE** — Derive all values from task card analysis. Remove hardcoded defaults.

### authorize.py
- **Current role**: Validates authorization against bound artifacts
- **Defects**: Does not validate prepare_package_sha256. Does not cross-check allowed_modification_paths against task card. Missing declared_output_paths validation.
- **Dependencies**: Used by Stage B
- **Retention risk**: High. Core gate function.
- **Conclusion**: **REWRITE** — Add prepare_package_sha256 binding. Validate all path sets are exact-equal (not subset/superset). Add explicit error for each missing binding.

### claim.py
- **Current role**: O_CREAT|O_EXCL immutable claim, requires validated auth data
- **Defects**: None critical. Atomic creation correct.
- **Dependencies**: Used by Stage B
- **Retention risk**: Low.
- **Conclusion**: **KEEP** — Make non-public (underscore-prefixed internal function, not exported from gate package). Uniqueness by task_id+authorization_id path.

### attempt_state.py
- **Current role**: Atomic state transitions
- **Defects**: None critical. Transition validation correct.
- **Dependencies**: Used by Stage B, finalize
- **Retention risk**: Low.
- **Conclusion**: **KEEP**

### preflight.py
- **Current role**: Pre-execution TOCTOU + path + authorization checks
- **Defects**: Auth validation failure doesn't block (errors collected but function returns). Uses task card paths instead of authorization paths. Natural language blocked_operations cause SPEC_INVALID but don't block.
- **Dependencies**: Used by Stage B
- **Retention risk**: High.
- **Conclusion**: **REWRITE** — All failures must block (return False immediately). Use authorization.allowed_modification_paths and authorization.declared_output_paths. Any SPEC_INVALID must block.

### executor.py
- **Current role**: AST-checked import whitelist + mock text transformation
- **Defects**: ALLOWED_IMPORTS too permissive. Mock transform trivial. Doesn't verify workspace isolation before execution.
- **Dependencies**: Used by Stage B
- **Retention risk**: Medium.
- **Conclusion**: **REWRITE** — Minimal whitelist (no uuid, no unused modules). Verify workspace is empty before execution. Verify all outputs within workspace. Verify input file exists in declared location.

### finalize.py
- **Current role**: Output comparison + result generation + state transition
- **Defects**: repo_diff/workspace_diff hardcoded as empty dict — never computed. Idempotent path doesn't re-verify output SHA256s. Result timestamp regenerated on every call. Existing FAIL result not properly blocked.
- **Dependencies**: Used by Stage B
- **Retention risk**: CRITICAL.
- **Conclusion**: **REWRITE** — Execute real workspace_diff before/after. Re-verify all output SHA256s in idempotent path. Do not regenerate timestamp. Block overwrite of non-PASS result.

### conditions.py
- **Current role**: Stop condition evaluator
- **Defects**: None critical.
- **Dependencies**: Used by task validation
- **Retention risk**: Low.
- **Conclusion**: **KEEP**

### pipeline.py (run_single_task_gate)
- **Current role**: Single synchronous 7-stage pipeline
- **Defects**: Crosses external authorization boundary in one call. No separation.
- **Dependencies**: All gate modules
- **Retention risk**: CRITICAL.
- **Conclusion**: **DELETE** — replaced by separate prepare_task and execute_authorized_task entry points.

### recovery.py
- **Current role**: Crash recovery logic
- **Defects**: Not needed for two-stage MVP. Recovery is a Phase 2B concern.
- **Dependencies**: None critical
- **Conclusion**: **DEFER** — keep on disk, do not import or use in Phase 2A rebuild. Revisit in Phase 2B.

---

## Schemas (6 files)

### freeze_bundle.schema.json
- **Conclusion**: **REWRITE** — Add optional `prepare_id` field. Keep core structure.

### understand_record.schema.json
- **Conclusion**: **REWRITE** — Remove hardcoded defaults. Make all fields derived from task card.

### authorization.schema.json
- **Conclusion**: **REWRITE** — Add `prepare_id`, `prepare_package_sha256`, `frozen_task_sha256`. Make `allowed_modification_paths` and `declared_output_paths` required.

### claim.schema.json
- **Conclusion**: **KEEP**

### attempt_state.schema.json
- **Conclusion**: **KEEP**

### execution_result.schema.json
- **Conclusion**: **REWRITE** — Replace `repo_diff` with `workspace_diff` (added/modified/deleted/unexpected in workspace). Make all diff fields required.

---

## Tests (13 files)

### protocol_guard/gate/tests/__init__.py
- **Conclusion**: **KEEP** (empty marker)

### test_freeze_bundle.py
- **Conclusion**: **REWRITE** — Keep deterministic + re-freeze tests. Add post-freeze cleanup test, frozen copy SHA mismatch test.

### test_understand.py
- **Conclusion**: **REWRITE** — Test derived values from task card. Remove hardcoded-value tests.

### test_authorize.py
- **Conclusion**: **REWRITE** — Test every binding field individually (at least 8 failure tests). Test prepare_package_sha256 mismatch.

### test_claim.py
- **Conclusion**: **REWRITE** — Keep atomic + double-claim tests. Add: null auth rejected, tampered claim detected, corrupted claim returns HUMAN_AUDIT_REQUIRED.

### test_attempt_state.py
- **Conclusion**: **REWRITE** — Keep transition tests. Add: identity field tamper blocking, indeterminate blocks all.

### test_preflight.py
- **Conclusion**: **REWRITE** — Add: preflight failure → no claim file exists (integration-level invariant). Auth failure → preflight returns False.

### test_executor.py
- **Conclusion**: **REWRITE** — Add: workspace empty before execution, output outside workspace fails, missing input fails, AST non-whitelist import rejected.

### test_finalize.py
- **Conclusion**: **REWRITE** — Add: real workspace_diff detects added/modified/deleted, idempotent preserves result bytes, FAIL result cannot become PASS.

### test_conditions.py
- **Conclusion**: **KEEP** — Minor cleanup (remove dict-length test, keep action mapping + trigger logic).

### test_recovery.py
- **Conclusion**: **DEFER** — With recovery deferred, tests deferred.

### test_integration.py
- **Conclusion**: **DELETE** — Current test validates the validator. Replace with Stage A + Stage B integration tests in new files.

### test_adversarial.py
- **Conclusion**: **REWRITE** — Replace with invariant-based adversarial tests (auth bypass, claim bypass, workspace escape, output overwrite, Phase 1 file write attempt).

---

## Fixtures (2 files)

### protocol_guard/gate/tests/fixtures/__init__.py
- **Conclusion**: **KEEP** (empty marker)

### protocol_guard/gate/tests/fixtures/mock_input.txt
- **Conclusion**: **KEEP** (valid mock input)

---

## Mock Task (1 file)

### tasks/MOCK_EXECUTE_TEST/task.yaml
- **Conclusion**: **REWRITE** — Simplify to single .txt input, single .txt output. Remove unused fields.

---

## Summary

| Verdict | Count | Files |
|---------|-------|-------|
| KEEP | 8 | __init__.py (gate), __init__.py (tests), __init__.py (fixtures), claim.py, attempt_state.py, conditions.py, mock_input.txt, claim.schema.json, attempt_state.schema.json |
| REWRITE_WITH_PRIMITIVE_REUSE | 1 | freeze_bundle.py |
| REWRITE | 14 | understand.py, authorize.py, preflight.py, executor.py, finalize.py, freeze_bundle.schema.json, understand_record.schema.json, authorization.schema.json, execution_result.schema.json, test_freeze_bundle.py, test_understand.py, test_authorize.py, test_claim.py, test_attempt_state.py, test_preflight.py, test_executor.py, test_finalize.py, test_adversarial.py, MOCK_EXECUTE_TEST/task.yaml |
| DELETE | 2 | pipeline.py, test_integration.py |
| DEFER | 2 | recovery.py, test_recovery.py |

**Total**: 8 KEEP + 1 REUSE + 19 REWRITE + 2 DELETE + 2 DEFER = 32 files accounted.
