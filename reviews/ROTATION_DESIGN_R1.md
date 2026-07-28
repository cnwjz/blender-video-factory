# Rotation Runtime Design R1

```text
TASK_ID: ROTATION_DESIGN_R1
DATE: 2026-07-20
DESIGN_VERSION: R1
DESIGN_STATUS: READY_FOR_INDEPENDENT_REVIEW
IMPLEMENTATION_AUTHORIZED: FALSE
```

## 1. AUTHORITATIVE_INPUTS

| Input | Role |
|-------|------|
| `reviews/ROTATION_CONTRACT_DECISION_RECORD.md` | USER_APPROVED_CONTRACT — field names + hierarchy |
| `reviews/ROTATION_ORIGINAL_REQUIREMENT_AUDIT_R2.md` | Independent audit — all NOT_SPECIFIED items identified |
| `protocol_guard/phase3_min/asset_scene_preflight_core.py` | LOCKED_SOURCE — `_validate_rotation`, `quaternion_min_angle_degrees`, `_check_tolerance` |
| `reviews/14B_3A_FORMAL_LOCK_RECORD.md` | LOCKED_SOURCE — Standing matrix_world read pattern |
| `reviews/14B_3B_FACING_DESIGN_R2.md` | LOCKED_SOURCE — Facing matrix_world + to_3x3 pattern |
| `reviews/14B_4A_VISIBILITY_FORMAL_LOCK_RECORD.md` | LOCKED_SOURCE — Visibility read-once, root-only, scope guard |
| `reviews/PROJECT_CODEIFICATION_MASTER_MAP.md` | R23 master map |

## 2. FIXED_CONTRACT

### 2.1 Schema (14A Core — LOCKED)

```text
Field: target.rotation.expected_world_rotation_euler_degrees  — array[3] of finite numbers
Field: target.rotation.rotation_tolerance_degrees              — finite non-negative number

Schema validates:
  - rotation is a dict (None → silently skip)
  - erw must be list of len==3, all finite numbers
  - tolerance passed through shared _check_tolerance (finite, non-negative, None→skip)
```

Classification: **LOCKED_SOURCE** — 14A Core lines 328-340.

### 2.2 Comparison Algorithm (14A Core — LOCKED)

```text
quaternion_min_angle_degrees(actual, expected):
  validate 4-tuples, finite, non-zero-length
  normalize both
  abs(dot)
  clamp to [-1, 1]
  2 * degrees(acos(dot))
```

Classification: **LOCKED_SOURCE** — 14A Core lines 501-521.

### 2.3 Pre-open Validation (following Facing §1.1 pattern)

```python
def _validate_rotation_rules_preopen(targets):
    errors = []
    for target in targets:
        tid = target.get("target_id", "")
        rot = target.get("rotation")
        if not isinstance(rot, dict):
            continue
        erw = rot.get("expected_world_rotation_euler_degrees")
        tol = rot.get("rotation_tolerance_degrees")
        if erw is not None and tol is None:
            errors.append(
                f"INVALID_ROTATION_RULE_RELATION: target '{tid}' "
                f"rotation missing required fields: ['rotation_tolerance_degrees']"
            )
    return errors
```

Classification: **REUSED_LOCKED_PATTERN** — Facing §1.1 partial-config detection. Only fires when expected is present but tolerance is missing. Same ordering/error collection as Facing/Standing.

### 2.4 Call Order

```python
pre_open_errs += _validate_rotation_rules_preopen(targets)  # after visibility
```

Classification: **R1_DESIGN_DECISION**. Rotation pre-open is added after visibility (last field group before rotation in execution order). Standing→Facing→Visibility→Rotation.

## 3. RUNTIME_CONFIGURATION_SEMANTICS

| Configuration | Runtime Result | Classification |
|-------------|----------------|----------------|
| `rotation` missing from target | `NOT_CHECKED` | REUSED_LOCKED_PATTERN — Standing/Facing/Visibility all use NOT_CHECKED for missing field groups |
| `rotation: null` | `NOT_CHECKED` | REUSED_LOCKED_PATTERN — schema treats null as absent |
| `rotation: {}` (empty) | `NOT_CHECKED` | REUSED_LOCKED_PATTERN |
| `erw` present, `tolerance` missing | Pre-open ERROR (exit 2) | REUSED_LOCKED_PATTERN — Facing §1.1 |
| `erw` missing, `tolerance` present | `NOT_CHECKED` | R1_DESIGN_DECISION — tolerance meaningless without expected value |
| Both `erw` and `tolerance` present | Execute comparison | — |

**R1 decision**: Partial config where `erw=None, tol=nonzero` → NOT_CHECKED. Rationale: tolerance without expected value is semantically empty. Rejected alternative: ERROR (adds pre-open complexity for zero-value scenario).

## 4. EULER_ORDER_AND_EXPECTED_QUATERNION

### 4.1 Euler Order

```text
Euler order: XYZ (intrinsic Tait-Bryan)
```

Classification: **R1_DESIGN_DECISION**. Blender's default Euler order is XYZ. All locked Standing/Facing designs use XYZ for axis transforms. No alternative order has source support. Rejected alternatives: ZYX (common in aerospace), quaternion-only input (conflicts with user contract of Euler degrees input).

### 4.2 Expected Euler → Quaternion Conversion

```python
from mathutils import Euler, Quaternion
import math

def _expected_euler_to_quaternion(erw):
    """Convert [rx, ry, rz] in degrees to a normalized mathutils.Quaternion."""
    rx, ry, rz = erw
    euler = Euler((
        math.radians(rx),
        math.radians(ry),
        math.radians(rz),
    ), 'XYZ')
    quat = euler.to_quaternion()
    quat.normalize()
    return quat
```

Classification: **R1_DESIGN_DECISION**. Uses Blender's `mathutils.Euler → to_quaternion()` path. Normalization after conversion ensures unit quaternion for `quaternion_min_angle_degrees`. Rejected alternative: manual conversion formula (error-prone, duplicates mathutils).

## 5. ACTUAL_WORLD_QUATERNION_EXTRACTION

### 5.1 Extraction Method

```python
# Step 1: Read matrix_world (at most once)
mw = root_obj.matrix_world  # mathutils.Matrix 4x4

# Step 2: Convert to quaternion
actual_quat = mw.to_quaternion()  # mathutils.Quaternion
actual_quat.normalize()
```

Classification: **R1_DESIGN_DECISION**. `Matrix.to_quaternion()` is Blender's standard method. It decomposes the 4x4 matrix, extracting rotation while accounting for scale.

### 5.2 Scale, Negative Scale, Shear, Reflection

```text
matrix_world.to_quaternion() decomposes the 3x3 linear component.
Blender's implementation normalizes internally and handles:
  - Uniform scale: no effect on quaternion
  - Non-uniform scale: quaternion represents the rotation component
  - Negative scale: handled (q and -q equivalence)
  - Shear: quaternion represents best-fit rotation
  - Reflection: may produce unexpected results (documented as edge case)
```

Classification: **R1_DESIGN_DECISION**. Standing and Facing use `matrix_world.to_3x3()` for linear component extraction, which includes scale/shear. Rotation follows the same `matrix_world` read pattern but uses `to_quaternion()` instead of `to_3x3()`. Rejected alternative: `to_3x3().to_quaternion()` (identical output from Blender, adds unnecessary step).

### 5.3 Read Count and Caching

```text
matrix_world: at most 1 read per _check_rotation invocation
to_quaternion(): at most 1 call per _check_rotation invocation
expected Euler→quaternion conversion: at most 1 call per _check_rotation invocation

No caching across check invocations — same as Standing and Facing.
```

Classification: **REUSED_LOCKED_PATTERN** — Standing/Facing both enforce at-most-once matrix_world reads.

## 6. COMPARISON_AND_TOLERANCE

### 6.1 Angle Computation

```python
angle = quaternion_min_angle_degrees(actual_tuple, expected_tuple)
```

Converts `mathutils.Quaternion` to `(w, x, y, z)` tuple before calling the locked 14A helper.

### 6.2 PASS/FAIL Boundary

```text
if angle <= tolerance: PASS
else: FAIL
```

Classification: **R1_DESIGN_DECISION**. Inclusive boundary (`<=`) matches Standing and Facing tolerance conventions. Angle-equal-to-tolerance → PASS.

### 6.3 Edge Cases

| Case | Behavior | Classification |
|------|----------|---------------|
| 0deg difference (identical rotation) | PASS (angle=0 ≤ tolerance) | Implicit from algorithm |
| 180deg difference | 2*degrees(acos(|-1|)) = 2*degrees(acos(1)) = 0deg → PASS | q/-q handled by `abs(dot)` in helper |
| q vs -q | `abs(dot)` → maximum dot becomes 1, angle=0 → PASS | LOCKED_SOURCE — `quaternion_min_angle_degrees` |
| Non-unit quaternion | Normalized before comparison | Implicit — helper normalizes |
| Zero-length quaternion | ERROR — NumericalValidationError | LOCKED_SOURCE — helper raises |

## 7. PASS_FAIL_ERROR_NOT_CHECKED

| Result | Condition |
|--------|-----------|
| `PASS` | rotation configured, `quaternion_min_angle_degrees ≤ tolerance` |
| `FAIL` | rotation configured, `quaternion_min_angle_degrees > tolerance` |
| `ERROR` | `matrix_world` read fails, `to_quaternion()` fails, Euler conversion fails, or zero-length quaternion |
| `NOT_CHECKED` | rotation missing, null, empty, or tolerance-only-without-expected |

Overall aggregation: ERROR > FAIL > PASS > NOT_CHECKED — **REUSED_LOCKED_PATTERN**.

## 8. FAILURE_AND_ERROR_CONTRACT

### 8.1 Failure Code

```text
failure_code: "OBJECT_ROTATION_OUT_OF_TOLERANCE"
```

Classification: **R1_DESIGN_DECISION**. Follows Visibility's `OBJECT_HIDDEN_IN_VIEWPORT` naming pattern (OBJECT_ prefix, descriptive suffix).

### 8.2 ERROR Operations

| Operation | Trigger |
|-----------|---------|
| `READ_ROOT_MATRIX_WORLD` | `root_obj.matrix_world` access fails |
| `CONVERT_ROOT_MATRIX_WORLD_TO_QUATERNION` | `mw.to_quaternion()` fails |
| `CONVERT_EXPECTED_EULER_TO_QUATERNION` | `Euler(radians(...), 'XYZ').to_quaternion()` fails |

Classification: **R1_DESIGN_DECISION**. Follows Standing's `READ_ROOT_MATRIX_WORLD` and Facing's `CONVERT_ROOT_MATRIX_WORLD_TO_3X3` naming convention. `READ_ROOT_MATRIX_WORLD` is reused from Standing/Facing (same operation, may be shared or counted per-field-group).

### 8.3 ERROR Result Structure

```python
{
    "result": "ERROR",
    "error_type": "ROTATION_COMPUTATION_ERROR",
    "operation": "<operation>",
    "note": "<operation>_FAILED",
}
```

Classification: **REUSED_LOCKED_PATTERN** — same ERROR structure as Standing/Facing/Visibility.

## 9. READ_COUNT_CACHE_AND_READ_ONLY_BOUNDARY

### 9.1 Read Limits

```text
root_obj.matrix_world:  1 read per check
matrix_world.to_quaternion(): 1 call per check
mathutils.Euler → to_quaternion(): 1 call per check

No reads on children, descendants, or any object other than root_obj.
No writes to any Blender object or property.
```

### 9.2 Allowed Blender Attributes

```text
root_obj.matrix_world  — only Blender object property accessed
```

### 9.3 Scope Guard

Following Visibility I2 and Facing I3A patterns: only `_check_rotation` is permitted to call `root_obj.matrix_world.to_quaternion()` and `Euler(...).to_quaternion()`. All other functions must have zero such calls. AST-based enforcement in I4.

Classification: **REUSED_LOCKED_PATTERN**.

## 10. AGGREGATION_AND_CHECK_INDEPENDENCE

### 10.1 Per-target Aggregation

```python
overall = max(standing, facing, visibility, rotation, ...) by ERROR > FAIL > PASS > NOT_CHECKED
```

Classification: **REUSED_LOCKED_PATTERN** — 14A Core overall aggregation.

### 10.2 Check Independence

Rotation executes independently of Standing, Facing, and Visibility. Each reads `root_obj.matrix_world` independently (Strategy A from Facing design — no shared cache across field groups). A Rotation ERROR does not block other checks; each contributes to the per-target overall aggregation.

Classification: **REUSED_LOCKED_PATTERN** — Facing design R2 §2 established independent matrix reads.

## 11. LOCKED_BOUNDARY_COMPATIBILITY

| Boundary | Compatibility |
|----------|--------------|
| Hierarchy | Rotation reads root_obj (resolved by Hierarchy). No new object search. ✓ |
| Standing | No conflict — both read matrix_world independently. ✓ |
| Facing | No conflict — Rotation uses to_quaternion(), Facing uses to_3x3(). ✓ |
| Visibility | No conflict — Rotation does not access hide_viewport/hide_render. ✓ |
| 14A Core | Rotation uses `quaternion_min_angle_degrees`, `_check_tolerance`, stable JSON output. ✓ |

No CONTRACT_CONFLICT found with any locked boundary.

## 12. EDGE_CASE_MATRIX

| Case | Expected Result | Classification |
|------|----------------|----------------|
| rotation missing | NOT_CHECKED | REUSED_LOCKED_PATTERN |
| rotation: null | NOT_CHECKED | REUSED_LOCKED_PATTERN |
| rotation: {} | NOT_CHECKED | REUSED_LOCKED_PATTERN |
| full valid config, angle=0 | PASS | Implicit from algo |
| full valid config, angle<tolerance | PASS | Implicit |
| full valid config, angle==tolerance | PASS | R1_DESIGN_DECISION |
| full valid config, angle>tolerance | FAIL | Implicit |
| tolerance=0, angle=0 | PASS | Implicit |
| tolerance=0, angle>0 | FAIL | Implicit |
| erw present, tolerance=None | pre-open ERROR | REUSED_LOCKED_PATTERN |
| erw=None, tolerance present | NOT_CHECKED | R1_DESIGN_DECISION |
| matrix_world read exception | ERROR — READ_ROOT_MATRIX_WORLD | REUSED_LOCKED_PATTERN |
| to_quaternion() exception | ERROR — CONVERT_ROOT_MATRIX_WORLD_TO_QUATERNION | R1_DESIGN_DECISION |
| Euler conversion exception | ERROR — CONVERT_EXPECTED_EULER_TO_QUATERNION | R1_DESIGN_DECISION |
| zero-length quaternion | ERROR — NumericalValidationError | LOCKED_SOURCE |
| non-finite Euler input | ERROR — schema validation | LOCKED_SOURCE |
| negative scale matrix | PASS or FAIL per algorithm (to_quaternion handles) | R1_DESIGN_DECISION |
| root_obj not found | NOT_CHECKED (pre-condition failure) | REUSED_LOCKED_PATTERN |
| mixed PASS/FAIL/ERROR across targets | Per-target aggregation | REUSED_LOCKED_PATTERN |
| Rotation + Standing + Facing + Visibility all configured | All execute independently | REUSED_LOCKED_PATTERN |

## 13. IMPLEMENTATION_TASK_BREAKDOWN

### I1: Pre-open Configuration and Runtime Entry
- `_validate_rotation_rules_preopen()` function in `asset_scene_preflight_check.py`
- `_check_rotation(target, root_obj)` skeleton in `blender_scene_reader.py`
- NOT_CHECKED semantics for missing/null/empty/tolerance-only
- `_check_root_objects` integration: NOT_CHECKED in 3 short-circuit branches
- Target overall ERROR>FAIL>PASS>NOT_CHECKED aggregation
- CPython-only tests (no Blender dependency)

### I2: World Quaternion Read and Conversion
- `root_obj.matrix_world` read (at most once)
- `to_quaternion()` + normalization
- Euler→quaternion conversion (`Euler(radians, 'XYZ').to_quaternion()`)
- Read exceptions → ERROR operations
- Conversion exceptions → ERROR operations
- Read-count and isolation tests

### I3: Quaternion Comparison, Result and Aggregation
- `quaternion_min_angle_degrees(actual, expected)` integration
- PASS/FAIL per tolerance
- failure_code: OBJECT_ROTATION_OUT_OF_TOLERANCE
- ERROR nesting with error_type/operation/note
- Actual/expected quaternion tuple in result
- Full result contract tests

### I4: Scope Guard and Static Enforcement
- AST analysis confirming only `_check_rotation` reads `to_quaternion()` and `Euler`
- Zero reads in any other function
- No writes, no setattr/delattr
- No forbidden scope access
- Adversarial probes

### E: Full Regression and Evidence
- Focused regression: I1+I2+I3+I4 + existing tests
- 14A Core regression
- Full protocol_guard regression
- Evidence package
- 0 failed, 0 skipped (except known Phase 2 symlink skips)

**Task count rationale**: 5 tasks (I1-I4 + E) following Standing/Facing pattern. I2-I3 are split at `to_quaternion` boundary because the read/conversion path has distinct ERROR operations from the comparison path. Both are independently testable. I4 is separate per Facing/Visibility precedent.

## 14. UNRESOLVED_CONFLICTS

```text
CONTRACT_CONFLICT_COUNT: 0
```

No conflicts with locked contracts found during design.

## 15. UNIQUE_NEXT_ATOMIC_TASK

```text
UNIQUE_NEXT_ATOMIC_TASK: ROTATION_I1_IMPLEMENTATION
```

Awaiting user authorization to begin Rotation I1 (pre-open + runtime entry + NOT_CHECKED semantics). Implementation authorization remains FALSE.
