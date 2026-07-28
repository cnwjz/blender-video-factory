# Rotation Runtime Design R3

```text
TASK_ID: ROTATION_DESIGN_R3_CORRECTION
DATE: 2026-07-20
DESIGN_VERSION: R3
DESIGN_STATUS: READY_FOR_INDEPENDENT_REVIEW
IMPLEMENTATION_AUTHORIZED: FALSE
```

## 1. FIXED_CONTRACT

```text
Schema:        target.rotation.expected_world_rotation_euler_degrees (array[3], finite)
               target.rotation.rotation_tolerance_degrees (finite, >= 0)
Algorithm:     quaternion_min_angle_degrees (LOCKED_SOURCE, 14A Core lines 501-521)
Euler order:   XYZ (R1_DESIGN_DECISION)
Helper:        _expected_euler_to_quaternion (sole Euler→quaternion conversion, R2 §4.1)
```

## 2. RUNTIME_CONFIGURATION_SEMANTICS

| Configuration | Result |
|-------------|----------------|
| rotation missing | NOT_CHECKED — note: "REQUIREMENT_NOT_CONFIGURED" |
| rotation: null | NOT_CHECKED |
| rotation: {} | NOT_CHECKED |
| erw present, tolerance missing | Pre-open ERROR (exit 2) |
| erw missing, tolerance present | NOT_CHECKED |
| Both present | Execute comparison |

## 3. ERROR BRANCH MAPPING (F-002)

| Trigger | error_type | operation | note |
|---------|-----------|-----------|------|
| `root_obj.matrix_world` raises | ROTATION_COMPUTATION_ERROR | READ_ROOT_MATRIX_WORLD | READ_ROOT_MATRIX_WORLD_FAILED |
| `mw.to_quaternion()` raises | ROTATION_COMPUTATION_ERROR | CONVERT_ROOT_MATRIX_WORLD_TO_QUATERNION | CONVERT_ROOT_MATRIX_WORLD_TO_QUATERNION_FAILED |
| Actual quaternion non-finite (NaN/Inf) | ROTATION_COMPUTATION_ERROR | CONVERT_ROOT_MATRIX_WORLD_TO_QUATERNION | NONFINITE_ROTATION_QUATERNION |
| Actual quaternion zero-length | ROTATION_COMPUTATION_ERROR | CONVERT_ROOT_MATRIX_WORLD_TO_QUATERNION | ZERO_LENGTH_ROTATION_QUATERNION |
| `Euler(...).to_quaternion()` raises | ROTATION_COMPUTATION_ERROR | CONVERT_EXPECTED_EULER_TO_QUATERNION | CONVERT_EXPECTED_EULER_TO_QUATERNION_FAILED |
| Expected quaternion non-finite (NaN/Inf) | ROTATION_COMPUTATION_ERROR | CONVERT_EXPECTED_EULER_TO_QUATERNION | NONFINITE_ROTATION_QUATERNION |
| Expected quaternion zero-length | ROTATION_COMPUTATION_ERROR | CONVERT_EXPECTED_EULER_TO_QUATERNION | ZERO_LENGTH_ROTATION_QUATERNION |
| `quaternion_min_angle_degrees` raises | ROTATION_COMPUTATION_ERROR | COMPUTE_ROTATION_ANGLE | COMPUTE_ROTATION_ANGLE_FAILED |
| `quaternion_min_angle_degrees` returns NaN/Inf | ROTATION_COMPUTATION_ERROR | COMPUTE_ROTATION_ANGLE | NONFINITE_ROTATION_ANGLE |

After `quaternion_min_angle_degrees` returns: verify `math.isfinite(angle_degrees)`. If not finite → ERROR per last row above.

## 4. RESULT STRUCTURES

**PASS**:
```python
{
    "result": "PASS",
    "expected_world_rotation_euler_degrees": [rx, ry, rz],
    "expected_quaternion": [w, x, y, z],
    "actual_quaternion": [w, x, y, z],
    "angle_degrees": <float>,
    "tolerance_degrees": <float>,
}
```

**FAIL**:
```python
{
    "result": "FAIL",
    "failure_code": "OBJECT_ROTATION_OUT_OF_TOLERANCE",
    "expected_world_rotation_euler_degrees": [rx, ry, rz],
    "expected_quaternion": [w, x, y, z],
    "actual_quaternion": [w, x, y, z],
    "angle_degrees": <float>,
    "tolerance_degrees": <float>,
}
```

**ERROR**:
```python
{
    "result": "ERROR",
    "error_type": "ROTATION_COMPUTATION_ERROR",
    "operation": "<from mapping table>",
    "note": "<from mapping table>",
}
# ERROR omits: expected_world_rotation_euler_degrees, expected_quaternion,
# actual_quaternion, angle_degrees, tolerance_degrees, failure_code
```

**NOT_CHECKED**:
```python
{
    "result": "NOT_CHECKED",
    "note": "REQUIREMENT_NOT_CONFIGURED",
}
```

Nested path: `checks.rotation`.

## 5. _collect_target_errors (F-002)

```python
def _collect_target_errors(target_results):
    ...
    for r in target_results:
        tid = r.get("target_id", "?")
        rn = r.get("root_object_name", "?")
        chk = r.get("checks", {})

        # ... existing checks (object_exists, direct_children, descendants,
        #     standing, facing, visibility) ...

        rot = chk.get("rotation", {})
        if rot.get("result") == "ERROR":
            op = rot.get("operation", "UNKNOWN")
            err_msgs.append(
                f"ROTATION_COMPUTATION_ERROR: target '{tid}' "
                f"root_object_name '{rn}' operation '{op}'"
            )
```

Collection order:

```text
1. object_exists
2. direct_children
3. descendants
4. standing
5. facing
6. visibility
7. rotation
```

Each entry format: `ROTATION_COMPUTATION_ERROR: target '<tid>' root_object_name '<rn>' operation '<op>'`.

## 6. ACTUAL_WORLD_QUATERNION_EXTRACTION (F-003)

### 6.1 Exact Contract

```text
Source: root_obj.matrix_world.to_quaternion()
Do NOT read object.rotation_euler or object.rotation_quaternion.
Do NOT modify Blender's conversion result.
Do NOT perform custom de-scaling, orthogonalization, or reflection repair.
```

### 6.2 Scale/Shear/Reflection: Runtime Flow

For each matrix property (uniform scale, non-uniform scale, negative scale, shear, reflection):

```text
1. Call matrix_world.to_quaternion()
2. If raises: ERROR — CONVERT_ROOT_MATRIX_WORLD_TO_QUATERNION / CONVERT_ROOT_MATRIX_WORLD_TO_QUATERNION_FAILED
3. If returns non-finite: ERROR — NONFINITE_ROTATION_QUATERNION
4. If returns zero-length: ERROR — ZERO_LENGTH_ROTATION_QUATERNION
5. If returns finite, non-zero quaternion: use directly in quaternion_min_angle_degrees
```

**No advance claim** about whether a given matrix type will produce PASS or FAIL. The quaternion returned by `to_quaternion()` is authoritative. q/-q equivalence (§6.3) handles quaternion sign only — it does not imply that negative scale, shear, or reflection produce the expected rotation.

### 6.3 q/-q Equivalence

`abs(dot)` in `quaternion_min_angle_degrees` handles quaternion representation sign. q and -q = same rotation (|dot|=1, angle=0°). True 180° difference = |dot|=0, angle=180°.

This is a quaternion representation property. It does not assert that negative scale, shear, or reflection produce rotation-equivalent quaternions.

### 6.4 Real Blender Validation (I4B)

I4B observes Blender's actual `to_quaternion()` behavior with temporary `.blend` files:

```text
Normal rotation (identity, 90deg X, 90deg Y, 90deg Z)
Uniform scale (2x, 0.5x)
Non-uniform scale (2x X, 1x Y, 1x Z)
Negative scale (-1x, -1y, -1z)
Shear (X→Y, Y→Z)
Reflection (mirror across X)
```

Each case: apply known rotation + matrix modification, call `to_quaternion()`, compute angle, verify PASS/FAIL per tolerance. Results become the authoritative matrix behavior contract for Rotation.

## 7. COMPARISON_AND_TOLERANCE

```text
angle <= tolerance: PASS
angle > tolerance: FAIL
failure_code: "OBJECT_ROTATION_OUT_OF_TOLERANCE"
```

PASS/FAIL/NOT_CHECKED aggregation: ERROR > FAIL > PASS > NOT_CHECKED (REUSED_LOCKED_PATTERN).

## 8. SCOPE GUARD

```text
_check_rotation:
  root_obj.matrix_world Load: exactly 1
  Matrix.to_quaternion() call: exactly 1

_expected_euler_to_quaternion:
  Euler() constructor: exactly 1
  Euler.to_quaternion() call: exactly 1

All other functions: 0 calls to Matrix.to_quaternion(), Euler.to_quaternion(), Euler().
Scope guard detects alias calls, helper propagation, setattr/delattr writes.
```

## 9. IMPLEMENTATION_TASK_BREAKDOWN

```text
I1   — Pre-open + NOT_CHECKED + entry + CPython tests
I2   — World quaternion + Euler conversion + all ERROR operations + read-once + CPython tests
I3   — quaternion_min_angle_degrees + PASS/FAIL + full result structures + aggregation + CPython tests
I4A  — Scope guard + AST enforcement + adversarial probes
I4B  — Real Blender mathutils validation (temporary .blend, scale/shear/reflection)
E    — Focused regression + 14A Core + full protocol_guard + evidence
```

## 10. UNIQUE_NEXT_ATOMIC_TASK

```text
UNIQUE_NEXT_ATOMIC_TASK: ROTATION_I1_IMPLEMENTATION
```

Implementation authorization: **FALSE**.
