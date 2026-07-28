# Rotation Contract Decision Record

```text
DECISION_ID: ROTATION_CONTRACT_DECISION
DECISION_STATUS: USER_APPROVED
DECISION_DATE: 2026-07-20
SOURCE_AUDIT: reviews/ROTATION_ORIGINAL_REQUIREMENT_AUDIT_R2.md
USER_APPROVAL_RECORDED: TRUE
```

## Approved Contract

```text
14A Core Rotation schema is the authoritative contract:

target.rotation.expected_world_rotation_euler_degrees
target.rotation.rotation_tolerance_degrees

These field names and the rotation sub-object hierarchy formally supersede
PHASE_3_MINIMUM_DESIGN_SPEC_R1.md's old forms:

target.expected_rotation_euler_deg
target.rotation_tolerance_deg
```

## Superseded Contract

```text
PHASE_3_MINIMUM_DESIGN_SPEC_R1.md §5.2 lines 154-155
  "expected_rotation_euler_deg": [0, 0, 0]
  "rotation_tolerance_deg": 2.0
```

## Decision Scope

```text
COVERED:
  Field names (expected_world_rotation_euler_degrees, rotation_tolerance_degrees)
  rotation sub-object hierarchy
  Old Design Spec R1 forms formally superseded

NOT COVERED:
  Euler order for expected-Euler-to-quaternion conversion
  matrix_world to world quaternion conversion method
  Runtime semantics for rotation missing/null
  Runtime semantics for partial configuration
  Failure codes
  ERROR type and operation
  Read count and caching
  Implementation task breakdown
```

## Explicitly Deferred Items

```text
Euler order (XYZ/ZYX/etc.)
Expected Euler → quaternion conversion
matrix_world → world quaternion extraction
Runtime NOT_CHECKED/MISSING semantics
Partial configuration semantics
Rotation-specific failure codes
Rotation-specific ERROR types/operations
```

## Authorization

```text
ROTATION_DESIGN_AUTHORIZED: TRUE
ROTATION_IMPLEMENTATION_AUTHORIZED: FALSE
```
