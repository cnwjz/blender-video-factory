# Rotation Runtime Design R2

```text
TASK_ID: ROTATION_DESIGN_R2_CORRECTION
DATE: 2026-07-20
DESIGN_VERSION: R2
DESIGN_STATUS: READY_FOR_INDEPENDENT_REVIEW
IMPLEMENTATION_AUTHORIZED: FALSE
```

## 1. AUTHORITATIVE_INPUTS

| Input | Role |
|-------|------|
| `reviews/ROTATION_CONTRACT_DECISION_RECORD.md` | USER_APPROVED_CONTRACT |
| `reviews/ROTATION_ORIGINAL_REQUIREMENT_AUDIT_R2.md` | Independent audit |
| `protocol_guard/phase3_min/asset_scene_preflight_core.py` | LOCKED_SOURCE — `_validate_rotation`, `quaternion_min_angle_degrees` |
| `reviews/14B_3A_FORMAL_LOCK_RECORD.md` | LOCKED_SOURCE — Standing |
| `reviews/14B_3B_FACING_DESIGN_R2.md` | LOCKED_SOURCE — Facing |
| `reviews/14B_4A_VISIBILITY_FORMAL_LOCK_RECORD.md` | LOCKED_SOURCE — Visibility |

## 2. FIXED_CONTRACT

### 2.1 Schema (LOCKED_SOURCE)

```text
target.rotation.expected_world_rotation_euler_degrees — array[3], finite numbers
target.rotation.rotation_tolerance_degrees             — finite non-negative number
```

14A Core `_validate_rotation` (lines 328-340) validates structure. `rotation: None` → schema silently skips.

### 2.2 Comparison Algorithm (LOCKED_SOURCE)

```text
quaternion_min_angle_degrees(actual, expected):
  validate 4-tuples, finite, non-zero-length
  normalize both → |dot| → clamp[-1,1] → 2*degrees(acos(dot))
```

## 3. RUNTIME_CONFIGURATION_SEMANTICS

| Configuration | Runtime Result |
|-------------|----------------|
| `rotation` missing | NOT_CHECKED |
| `rotation: null` | NOT_CHECKED |
| `rotation: {}` | NOT_CHECKED |
| erw present, tolerance missing | Pre-open ERROR (exit 2) |
| erw missing, tolerance present | NOT_CHECKED |
| Both present | Execute comparison |

## 4. EULER_ORDER_AND_EXPECTED_QUATERNION

Euler order: **XYZ** (R1_DESIGN_DECISION).

### 4.1 Helper Strategy (F-004)

**Option B**: Dedicated helper `_expected_euler_to_quaternion` as the sole authorized Euler-to-quaternion conversion point.

```python
def _expected_euler_to_quaternion(erw):
    """Convert [rx, ry, rz] in degrees to (w, x, y, z) tuple.
    Only function authorized to call Euler(...).to_quaternion().
    """
    rx, ry, rz = erw
    euler = Euler((
        math.radians(rx), math.radians(ry), math.radians(rz)
    ), 'XYZ')
    quat = euler.to_quaternion()
    quat.normalize()
    return (quat.w, quat.x, quat.y, quat.z)
```

Classification: **R1_DESIGN_DECISION**. Rejected alternative: inline in `_check_rotation` (harder to scope-guard, duplicates conversion logic if helper is needed elsewhere).

### 4.2 Scope Guard Contract (F-004)

```text
_check_rotation:
  root_obj.matrix_world  Load: exactly 1
  Matrix.to_quaternion() call: exactly 1

_expected_euler_to_quaternion:
  Euler() constructor: exactly 1
  Euler.to_quaternion() call: exactly 1

All other functions in blender_scene_reader.py:
  Matrix.to_quaternion() calls: 0
  Euler.to_quaternion() calls: 0
  Euler() constructor (rotation-related): 0

Scope guard must detect:
  mw.to_quaternion() alias calls
  Helper propagation (calls into _expected_euler_to_quaternion)
  Unauthorized direct Euler.to_quaternion() in other functions
  setattr/delattr writes to matrix_world or rotation properties
```

Scope guard follows Facing I3A and Visibility I2 patterns: AST-based enforcement, adversarial probes for alias/bypass scenarios, and helper-propagation through call-graph analysis.

## 5. ACTUAL_WORLD_QUATERNION_EXTRACTION (F-003)

### 5.1 Exact Contract

```text
Actual world quaternion source: root_obj.matrix_world.to_quaternion()
Do NOT read object.rotation_euler or object.rotation_quaternion.
Do NOT manually modify Blender's matrix conversion result.
Do NOT perform custom de-scaling, orthogonalization, or reflection repair.
```

### 5.2 Scale/Shear/Reflection Contract

| Matrix Property | Runtime Behavior |
|----------------|------------------|
| Uniform scale | `to_quaternion()` returns rotation component; angle unaffected |
| Non-uniform scale | `to_quaternion()` returns rotation component; may affect quaternion if scale is non-uniform |
| Negative scale | `to_quaternion()` returns rotation; q/-q equivalence handles quaternion sign, NOT scale sign |
| Shear | `to_quaternion()` returns best-fit rotation; may produce unexpected angle |
| Reflection | `to_quaternion()` may return unexpected quaternion; treated as input to comparison |

**Contract**: If `to_quaternion()` returns a finite, non-zero quaternion tuple `(w,x,y,z)`, it is used directly in `quaternion_min_angle_degrees`. No additional validation, de-scaling, or correction is applied. If `to_quaternion()` raises an exception, or the result is non-finite or zero-length: **ERROR** — `CONVERT_ROOT_MATRIX_WORLD_TO_QUATERNION`.

**q/-q equivalence**: `abs(dot)` in `quaternion_min_angle_degrees` handles the fact that quaternions `q` and `-q` represent the same rotation. This is a quaternion representation property, NOT a claim that negative scale or reflection is equivalent to the original rotation.

### 5.3 Real Blender Validation (I4B)

A dedicated real Blender mathutils validation task (I4B) verifies the behavior with temporary scenes/`.blend` files (NOT real project `.blend`). Minimum validation:

```text
Normal rotation (identity, 90deg X, 90deg Y, 90deg Z)
Uniform scale (2x, 0.5x)
Non-uniform scale (2x X, 1x Y, 1x Z)
Negative scale (-1x, -1y, -1z)
Shear (shear X→Y, shear Y→Z)
Reflection (mirror across X)
```

Each case: apply known rotation + matrix modification, run `to_quaternion()`, compute angle against expected, verify PASS/FAIL per tolerance.

## 6. COMPARISON_AND_TOLERANCE

### 6.1 PASS/FAIL Boundary

```text
angle <= tolerance: PASS
angle > tolerance: FAIL
```

### 6.2 Edge Cases (F-001)

| Case | `abs(dot)` | Angle | Meaning |
|------|-----------|-------|---------|
| q and -q (same rotation) | 1.0 | 0° | PASS |
| 90° apart | ≈0.707 | ≈90° | PASS if tolerance ≥ 90 |
| True 180° apart | 0.0 | 180° | FAIL if tolerance < 180°; PASS if tolerance = 180° |
| tolerance=0, angle=0 | 1.0 | 0° | PASS |
| tolerance=0, angle>0 | <1.0 | >0° | FAIL |

**q/-q is NOT a 180° difference**. q and -q are the same rotation (`|dot| = 1`, angle = 0°). True 180° difference means `|dot| = 0`, angle = 180°. The `abs()` in the helper is the q/-q handler; the angle is what determines PASS/FAIL.

Classification: **LOCKED_SOURCE** — follows from `quaternion_min_angle_degrees` implementation.

## 7. PASS_FAIL_ERROR_NOT_CHECKED

| Result | Condition |
|--------|-----------|
| PASS | rotation configured, `angle ≤ tolerance` |
| FAIL | rotation configured, `angle > tolerance` |
| ERROR | Any read/convert/compute exception (see §8) |
| NOT_CHECKED | rotation missing/null/empty/tolerance-only |

Overall: ERROR > FAIL > PASS > NOT_CHECKED.

## 8. FAILURE_AND_ERROR_CONTRACT (F-002)

### 8.1 Failure Code

```text
failure_code: "OBJECT_ROTATION_OUT_OF_TOLERANCE"
```

### 8.2 ERROR Operations

| Operation | Trigger |
|-----------|---------|
| `READ_ROOT_MATRIX_WORLD` | `root_obj.matrix_world` access fails |
| `CONVERT_ROOT_MATRIX_WORLD_TO_QUATERNION` | `mw.to_quaternion()` fails or returns non-finite/zero-length |
| `CONVERT_EXPECTED_EULER_TO_QUATERNION` | `Euler(...).to_quaternion()` fails or returns non-finite/zero-length |
| `COMPUTE_ROTATION_ANGLE` | `quaternion_min_angle_degrees` raises exception |

### 8.3 ERROR Sub-notes

```text
READ_ROOT_MATRIX_WORLD_FAILED
NONFINITE_ROTATION_QUATERNION (to_quaternion returned NaN/Inf)
ZERO_LENGTH_ROTATION_QUATERNION (to_quaternion returned zero-length)
CONVERT_EXPECTED_EULER_TO_QUATERNION_FAILED
COMPUTE_ROTATION_ANGLE_FAILED
```

### 8.4 Complete Result Structures

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
    "operation": "<OPERATION>",
    "note": "<NOTE>",
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

### 8.5 Nested Path

```text
checks.rotation — full inner dict as defined above
```

### 8.6 _collect_target_errors

```python
def _collect_target_errors(result):
    errors = []
    ...
    rot = result["checks"].get("rotation")
    if isinstance(rot, dict) and rot.get("result") == "ERROR":
        op = rot.get("operation", "UNKNOWN")
        errors.append(f"ROTATION_ERROR: {op}")
    return errors
```

Rotation errors are appended after visibility errors, before any future field group. Same `ROTATION_ERROR: <operation>` format as Standing/Facing/Visibility.

## 9. READ_COUNT_CACHE_AND_READ_ONLY_BOUNDARY

```text
root_obj.matrix_world: at most 1 read
Matrix.to_quaternion(): at most 1 call
Euler.to_quaternion(): at most 1 call (within helper)
quaternion_min_angle_degrees: at most 1 call

No reads on children, descendants, or non-root objects.
No writes to any Blender object or property.
```

## 10. AGGREGATION_AND_CHECK_INDEPENDENCE

Rotation executes independently of Standing, Facing, and Visibility. Each reads `root_obj.matrix_world` independently (Strategy A). Per-target overall: ERROR > FAIL > PASS > NOT_CHECKED.

## 11. LOCKED_BOUNDARY_COMPATIBILITY

| Boundary | Compatible |
|----------|-----------|
| Hierarchy | ✓ rotation reads root_obj (resolved by Hierarchy) |
| Standing | ✓ both read matrix_world independently |
| Facing | ✓ Rotation uses to_quaternion(), Facing uses to_3x3() |
| Visibility | ✓ no overlap with hide_viewport/hide_render |
| 14A Core | ✓ uses locked helpers |

CONTRACT_CONFLICT_COUNT: 0.

## 12. EDGE_CASE MATRIX

| Case | Result |
|------|--------|
| rotation missing | NOT_CHECKED |
| rotation: null | NOT_CHECKED |
| rotation: {} | NOT_CHECKED |
| full config, angle=0 | PASS |
| full config, angle<tolerance | PASS |
| full config, angle==tolerance | PASS |
| full config, q==-q (same rotation) | PASS (angle=0) |
| full config, 180deg apart, tolerance=179 | FAIL (angle=180 > 179) |
| full config, 180deg apart, tolerance=180 | PASS (angle=180 ≤ 180) |
| tolerance=0, angle=0 | PASS |
| tolerance=0, angle>0 | FAIL |
| erw present, tolerance=None | Pre-open ERROR |
| erw=None, tolerance present | NOT_CHECKED |
| matrix_world read exception | ERROR — READ_ROOT_MATRIX_WORLD |
| to_quaternion() exception | ERROR — CONVERT_ROOT_MATRIX_WORLD_TO_QUATERNION |
| to_quaternion() returns NaN/Inf | ERROR — NONFINITE_ROTATION_QUATERNION |
| to_quaternion() returns zero-length | ERROR — ZERO_LENGTH_ROTATION_QUATERNION |
| Euler conversion exception | ERROR — CONVERT_EXPECTED_EULER_TO_QUATERNION |
| compare exception | ERROR — COMPUTE_ROTATION_ANGLE |
| uniform scale | PASS or FAIL per angle |
| non-uniform scale | PASS or FAIL per angle (verified in I4B) |
| negative scale | PASS or FAIL per angle (verified in I4B) |
| shear | PASS or FAIL per angle (verified in I4B) |
| reflection | PASS or FAIL per angle (verified in I4B) |
| root_obj not found | NOT_CHECKED |
| mixed PASS/FAIL/ERROR/NOT_CHECKED across targets | Per-target aggregation |

## 13. IMPLEMENTATION_TASK_BREAKDOWN

| Task | Description |
|------|-------------|
| **I1** | Pre-open validation (`_validate_rotation_rules_preopen`), `_check_rotation` skeleton, NOT_CHECKED semantics, `_check_root_objects` integration, CPython-only tests |
| **I2** | World quaternion extraction (`to_quaternion()`), expected Euler→quaternion conversion (`_expected_euler_to_quaternion`), all 4 ERROR operations, read-once, CPython tests |
| **I3** | `quaternion_min_angle_degrees` integration, PASS/FAIL, complete result structures, failure_code, per-target aggregation, full contract tests |
| **I4A** | Scope guard — AST enforcement of read/write boundaries, helper propagation, alias detection, adversarial probes |
| **I4B** | Real Blender mathutils validation — temporary scenes, scale/shear/reflection verification, PASS/FAIL per tolerance |
| **E** | Focused regression (I1+I2+I3+I4A+I4B + existing), 14A Core, full protocol_guard regression, evidence package |

## 14. UNIQUE_NEXT_ATOMIC_TASK

```text
UNIQUE_NEXT_ATOMIC_TASK: ROTATION_I1_IMPLEMENTATION
```

Implementation authorization: **FALSE**.
