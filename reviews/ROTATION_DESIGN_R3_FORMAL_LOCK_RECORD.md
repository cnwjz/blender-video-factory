# Rotation Design R3 Formal Lock Record

```text
LOCK_ID: ROTATION_DESIGN_R3
LOCK_STATUS: FORMALLY_LOCKED
LOCK_DATE: 2026-07-20
USER_APPROVAL_RECORDED: TRUE
FINAL_DESIGN_PATH: reviews/ROTATION_DESIGN_R3.md
DESIGN_VERSION: R3
INDEPENDENT_REVIEW_STATUS: ALL_CHECKS_PASS
TRUE_BLOCKING_ISSUES: 0
ROTATION_IMPLEMENTATION_AUTHORIZED: TRUE
ROTATION_IMPLEMENTATION_STARTED: FALSE
```

## Locked Contract

### Fields
```text
target.rotation.expected_world_rotation_euler_degrees
target.rotation.rotation_tolerance_degrees
```

### Euler Order
```text
XYZ
```

### Actual World Quaternion
```text
root_obj.matrix_world.to_quaternion()
Do NOT read object.rotation_euler or object.rotation_quaternion.
Do NOT perform custom de-scaling, orthogonalization, or reflection repair.
```

### Comparison Algorithm
```text
quaternion_min_angle_degrees (14A Core lines 501-521)
normalize → abs(dot) → clamp[-1,1] → 2*degrees(acos(dot))
```

### Key Behaviors
```text
q and -q represent the same rotation (|dot|=1, angle=0°)
True 180° difference → |dot|=0, angle=180°
Tolerance uses inclusive boundary (angle ≤ tolerance → PASS)
Scale/shear/reflection: use matrix_world.to_quaternion() real return value
Non-finite or zero-length quaternion → ERROR
```

### Failure Code
```text
OBJECT_ROTATION_OUT_OF_TOLERANCE
```

### ERROR Operations
```text
READ_ROOT_MATRIX_WORLD
CONVERT_ROOT_MATRIX_WORLD_TO_QUATERNION
CONVERT_EXPECTED_EULER_TO_QUATERNION
COMPUTE_ROTATION_ANGLE
```

### Result Structures
```text
PASS: result, expected_world_rotation_euler_degrees, expected_quaternion[w,x,y,z],
      actual_quaternion[w,x,y,z], angle_degrees, tolerance_degrees

FAIL: result, failure_code, expected_world_rotation_euler_degrees,
      expected_quaternion[w,x,y,z], actual_quaternion[w,x,y,z],
      angle_degrees, tolerance_degrees

ERROR: result, error_type, operation, note
       (omits expected/actual/angle/tolerance/failure_code)

NOT_CHECKED: result, note

Nested path: checks.rotation
```

### Error Collection
```text
_collect_target_errors format:
  ROTATION_COMPUTATION_ERROR: target '<tid>' root_object_name '<rn>' operation '<op>'

Collection order: object_exists, direct_children, descendants,
  standing, facing, visibility, rotation
```

### Read Contract
```text
root_obj.matrix_world: at most 1 read
Matrix.to_quaternion(): at most 1 call
Euler.to_quaternion(): at most 1 call (within _expected_euler_to_quaternion)
quaternion_min_angle_degrees: at most 1 call
Read-only, root-only, no writes
```

### Check Independence
```text
Rotation executes independently of Standing, Facing, Visibility.
Each reads matrix_world independently (Strategy A).
```

### Implementation Tasks
```text
ROTATION_I1_IMPLEMENTATION
ROTATION_I2_IMPLEMENTATION
ROTATION_I3_IMPLEMENTATION
ROTATION_I4A_SCOPE_GUARD
ROTATION_I4B_BLENDER_VALIDATION
ROTATION_E_FINAL_REGRESSION
```
