# 14B-4A Visibility Formal Lock Record

```text
TASK_ID: 14B_4A_VISIBILITY
LOCK_STATUS: FORMALLY_LOCKED
LOCK_BASIS: USER_FORMAL_APPROVAL
LOCK_APPROVAL_DATE: 2026-07-20
```

## Design

```text
DESIGN_VERSION: R2
DESIGN_STATUS: LOCKED
DESIGN_DOCUMENT: reviews/14B_4A_VISIBILITY_DESIGN_R2.md
```

## Implementation Status

```text
I1_STATUS: COMPLETED_AND_INDEPENDENTLY_PASSED
I2_STATUS: COMPLETED_AND_INDEPENDENTLY_PASSED
E_STATUS: INDEPENDENTLY_PASSED
TRUE_BLOCKING_ISSUES: 0
```

## Locked Fields

```text
visibility.require_not_hidden_viewport
visibility.require_not_hidden_render
```

## Locked Capabilities

```text
Corresponding Blender read-only attributes:
  root_obj.hide_viewport
  root_obj.hide_render

Including:
  Missing/null/empty configuration semantics
  PASS, FAIL, ERROR, NOT_CHECKED
  Field independence (each field reads its property independently)
  Read-once cache (each Blender property read at most once per invocation)
  Target overall aggregation (ERROR > FAIL > PASS > NOT_CHECKED)
  Read exception handling
  Read-only boundary
  Scope Guard (AST-based enforcement)
```

## Regression Results

```text
FOCUSED_RESULT: 199 passed, 0 failed
14A_CORE_RESULT: 139 passed, 0 failed
FULL_REGRESSION_RESULT: 1006 passed, 0 failed, 2 skipped
FULL_REGRESSION_EXIT_CODE: 0
```

## Final Evidence

```text
FINAL_EVIDENCE_PACKAGE: reviews/UPLOAD_NEXT/14B_4A_VISIBILITY_E/14B_4A_VISIBILITY_E_UPLOAD_R3.zip
FINAL_EVIDENCE_PACKAGE_SHA256: 7b876cc7694ffc341bda3682976434685f77455a95d3f0f6260e5ad50e9e09cf
```

## Scope

```text
BLENDER_PRODUCTION_CODE_MODIFIED: FALSE
BLENDER_EXECUTED: FALSE
REAL_PROJECT_BLEND_OPENED: FALSE
RENDER_EXECUTED: FALSE
SAVE_BLEND_EXECUTED: FALSE
```

## Locked Scope

This lock covers the visibility field group (2 boolean fields) only.

Not included:
```text
rotation
animation_state
material_assignment
collection_rules
ground_contact
camera_check
projection_groups
real project .blend verification
rendering or saving
```
