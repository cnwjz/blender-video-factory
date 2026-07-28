# 14B-3B Facing Forward Axis 正式锁定记录

```text
TASK_ID: 14B_3B_FACING_DESIGN
TASK_NAME: Facing Forward Axis
LOCK_STATUS: LOCKED
LOCK_APPROVAL_DATE: 2026-07-18
LOCK_BASIS: USER_FORMAL_APPROVAL
BASELINE_COMMIT: d44679fc11c5069a17277395bb6c52b5a6dfc799
LOCK_SCOPE: DESIGN_AND_IMPLEMENTATION
```

## Implementation Completion

```text
14B_3B_I1: COMPLETED_AND_INDEPENDENTLY_PASSED
14B_3B_I2A: COMPLETED_AND_INDEPENDENTLY_PASSED
14B_3B_I2B: COMPLETED_AND_INDEPENDENTLY_PASSED
14B_3B_I3A: COMPLETED_AND_INDEPENDENTLY_PASSED
14B_3B_I3B: COMPLETED_AND_INDEPENDENTLY_PASSED
14B_3B_FACING_IMPLEMENTATION: COMPLETED
14B_3B: FORMALLY_LOCKED
FACING_LOCKED: TRUE
FROZEN_ACCEPTANCE_MATRIX_VERSION: R5
```

## Test Results

```text
I3B_TEST_RESULT: 9 passed, 0 failed
FACING_REGRESSION_RESULT: 137 passed, 0 failed
CORE_REGRESSION_RESULT: 139 passed, 0 failed
FULL_REGRESSION_RESULT: 856 passed, 0 failed, 2 skipped
SCOPE_GUARD_RESULT: 1 passed
COLLECTION_ERROR_COUNT: 0
ALL_COMMANDS_EXIT_ZERO: TRUE
```

## Contract Conflict Resolution

F-008 contract conflict adjudicated 2026-07-18. `build_error_result` in locked 14A Core does not accept `per_target`. R5 matrix amendment resolved: entry-level verifies `per_target_results==[]`; internal `_check_root_objects` call verifies `target overall=="ERROR"`. Production code NOT modified.

## Boundary

```text
PRODUCTION_CODE_MODIFIED_DURING_FINAL_CORRECTION: FALSE
REAL_PROJECT_BLEND_OPENED: FALSE
RENDER_EXECUTED: FALSE
```

## Locked Design Documents

| Document | Location |
|----------|----------|
| Requirement Audit R2 | reviews/14B_3B_FACING_REQUIREMENT_AUDIT_R2.md |
| Design R2C1 | reviews/14B_3B_FACING_DESIGN_R2C1.md |
| Design Changelog | reviews/14B_3B_DESIGN_R2C1_CHANGELOG.md |
| Acceptance Matrix R5 | reviews/UPLOAD_NEXT/14B_3B_I3B_ACCEPTANCE_FREEZE_R5_UPLOAD.zip |
| F-008 Adjudication | reviews/14B_3B_I3B_F008_CONTRACT_CONFLICT_ADJUDICATION_REPORT.md |
| Final Regression R2 | reviews/UPLOAD_NEXT/14B_3B_FINAL_REGRESSION_R2_EVIDENCE_REPACK_UPLOAD.zip |

## Fields

- `facing.local_forward_axis` (str, AXIS_VALUES)
- `facing.expected_world_forward_axis` (str, AXIS_VALUES)
- `facing.facing_tolerance_degrees` (number)

## Locked Design Decisions

- Configuration semantics per 14A schema actual behavior
- Pre-open: INVALID_FACING_RULE_RELATION only when both axes valid + tolerance missing/null
- Algorithm: same transform pipeline as Standing
- Matrix strategy A: independent reads
- 5 operations
- Nested result path: checks.facing.forward_axis
- ERROR > FAIL > PASS overall aggregation
- Scope guard: exactly 1 matrix_world load + 1 to_3x3 call each for standing and facing
