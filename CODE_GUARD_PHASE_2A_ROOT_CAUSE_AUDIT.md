# Phase 2A Root Cause Audit — R1 Corrected

Date: 2026-07-16
Task: CODE_GUARD_PHASE_2A_ROOT_CAUSE_AUDIT_R1_CORRECTION
Final Classification: **PARTIAL_REBUILD_PHASE_2A**

---

## 0. Audit Conclusion

**PARTIAL_REBUILD_PHASE_2A**. Keep and re-validate the atomic primitives (claim, attempt_state, conditions, freeze_bundle hashing primitives, and the working subset of schemas). Rewrite the architecture: split into two stages (prepare_task, execute_authorized_task) with an external authorization boundary between them. Rewrite authorize, preflight, executor, and finalize. Delete the old pipeline.py and integration test. Defer recovery.

Do NOT delete all Phase 2A code. The atomic tools are sound.

---

## 1. Root Causes of "All Tests Pass, Gate Not Closed"

### RC1: Single function crosses external authorization boundary
**File**: `pipeline.py:run_single_task_gate()` — validate → freeze → understand → authorize → preflight → claim → execute → finalize in one synchronous call. GPT review and user authorization are external steps that belong between Stage A and Stage B. The pipeline assumes the authorization file already exists.

### RC2: repo_diff never called
**File**: `finalize.py` line 71 — `"repo_diff": {"added": [], "modified": [], "deleted": [], "unexpected": []}` is hardcoded. The `repo_diff()` function defined in the module is dead code.

### RC3: Tests validate function returns, not gate invariants
Tests assert `ok=True`, `isinstance(cleared, bool)`, `os.path.exists(path)` — not "preflight failure prevents claim creation" or "authorization with wrong freeze_bundle SHA is rejected before claim."

### RC4: Evidence generation conflated with gate execution
The `finalize()` function writes `execution_result.json` with `TECHNICAL_PASS` based on local output comparison only. The separate R1 evidence script independently declared `TECHNICAL_PASS` based on test counts, not gate integrity.

### RC5: Test count threshold drove low-value tests
"70+ non-adversarial tests" requirement produced tests like `test_all_actions_covered` (checks dict length), `test_blender_required_false` (checks hardcoded value), `test_ast_clean_source_passes` (checks string). These inflate count without verifying invariants.

---

## 2. Phase 1.4 Evidence Overwrite — Root Cause

**Who wrote**: `_generate_evidence.py` ran `pytest ... > pytest_output.txt` in project root, overwriting Phase 1.4 frozen files.

**Why tests didn't prevent**: Phase 2A tests use temp dirs. The evidence script ran OUTSIDE the test suite.

**Why PROTECTED_FILES_INTEGRITY showed damage but TECHNICAL_PASS was still written**: `technical_result` was computed from test pass/fail counts independently of the integrity check. `unchanged: false` did not gate the result.

**Permanent fix**:
1. All evidence to `reviews/PROTOCOL_IMPLEMENTATION_HISTORY/<task_id>/<build_id>/` — never project root
2. Root-level Phase 1.4 evidence dirs read-only after freeze
3. Evidence scripts must not use `>` redirection to project root
4. `protected_files_unchanged: false` must force `TECHNICAL_FAIL`

---

## 3. Root Cause Summary Table

| # | Root Cause | Location | Severity |
|---|-----------|----------|----------|
| 1 | Single function crosses external auth boundary | pipeline.py | CRITICAL |
| 2 | repo_diff never called | finalize.py:71 | CRITICAL |
| 3 | Tests verify function returns, not invariants | All test files | CRITICAL |
| 4 | Evidence conflated with gate execution | R1 evidence script | HIGH |
| 5 | Test count drove low-value tests | conditions/understand/executor tests | HIGH |
| 6 | Phase 1.4 evidence overwritten by Phase 2A | _generate_evidence.py | CRITICAL |
| 7 | PROTECTED_FILES_INTEGRITY damage didn't block TECHNICAL_PASS | R1 evidence script | CRITICAL |

---

## 4. Classification Decision: PARTIAL_REBUILD_PHASE_2A

**Why not SALVAGE**: The architectural error (single function crossing auth boundary) and implementation error (dead repo_diff code) are too deep to patch.

**Why not FULL_REBUILD**: The atomic primitives are sound. `claim.py` (O_CREAT|O_EXCL), `attempt_state.py` (atomic transitions), `conditions.py` (action mapping), and the hashing primitives in `freeze_bundle.py` work correctly. Deleting them would waste verified code.

**What PARTIAL_REBUILD means**:
- KEEP: claim.py, attempt_state.py, conditions.py, __init__.py, fixtures, mock_input.txt, MOCK_EXECUTE_TEST task
- REWRITE_WITH_PRIMITIVE_REUSE: freeze_bundle.py
- REWRITE: understand.py, authorize.py, preflight.py, executor.py, finalize.py, 6 schemas, most tests
- DELETE: pipeline.py, test_integration.py
- DEFER: recovery.py, test_recovery.py

---

## 5. Two-Stage Architecture

```
Stage A: prepare_task(task_path, state_path, runtime_root)
  → validate → freeze → understand
  → outputs: prepare_package.json + frozen_task.yaml + freeze_bundle.json + understand.json
  → STOPS. Does not proceed to execution.

         [EXTERNAL: GPT reviews → User creates authorization.json]

Stage B: execute_authorized_task(auth_path, prepare_package_path, runtime_root)
  → read prepare_package, verify all bindings
  → verify authorization against prepare_package_sha256
  → preflight → claim → mock_execute → workspace_diff → finalize
  → outputs ONLY in runtime_root/executions/<task_id>/authorizations/<auth_id>/
```

No single function can cross the authorization boundary. Stage A and Stage B are separate, independently callable functions. The only public API is `prepare_task` and `execute_authorized_task`.

---

## 6. Is Phase 2A Worth Continuing?

**Yes.** The core protocol concepts are valid and Phase 1 primitives are sufficient. The failure was architectural (single pipeline crossing boundary) and implementation (dead code), not conceptual. A two-stage rebuild with invariant-based testing will close the gate.
