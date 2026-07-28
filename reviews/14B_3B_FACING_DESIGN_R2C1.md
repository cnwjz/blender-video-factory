# 14B-3B Facing Forward Axis -- Final Design R2C1

```text
TASK_ID: 14B_3B_DESIGN_R2C1
BASELINE: d44679fc11c5069a17277395bb6c52b5a6dfc799
DESIGN_STATUS: READY_FOR_INDEPENDENT_REVIEW
IMPLEMENTATION_AUTHORIZED: FALSE
BLENDER_EXECUTION_AUTHORIZED: FALSE
REAL_PROJECT_BLEND_VALIDATION_AUTHORIZED: FALSE
SUPERSEDES: 14B_3B_FACING_DESIGN_R2.md (R2C)
```

Final design incorporating R2A (configuration semantics), R2B (evidence + matrix strategy), R2B1 (direct evidence + overflow), R2C (scope guard contract + task split), R2C1 (overflow correction, scope guard clarity, error order, I3 split).

---

## 1. Fields

| Field | Type | 14A validation |
|-------|------|---------------|
| `facing.local_forward_axis` | `str` or `None` | `not in AXIS_VALUES` -> ERROR (None included) |
| `facing.expected_world_forward_axis` | `str` or `None` | `not in AXIS_VALUES` -> ERROR (None included) |
| `facing.facing_tolerance_degrees` | `number or None` | `_check_tolerance` (None silently skipped) |

Origin: "face +Y" from v4 doc -> axis names; tolerance threshold from locked 14A schema for repeatable numeric judgment.

### 1.1 Pre-open validation

```python
def _validate_facing_forward_axis_rules_preopen(targets):
    errors = []
    for target in targets:
        tid = target.get("target_id", "")
        facing = target.get("facing")
        if not isinstance(facing, dict):
            continue
        la = facing.get("local_forward_axis")
        ew = facing.get("expected_world_forward_axis")
        tol = facing.get("facing_tolerance_degrees")
        if (la in AXIS_VALUES) and (ew in AXIS_VALUES) and (tol is None):
            errors.append(
                f"INVALID_FACING_RULE_RELATION: target '{tid}' "
                f"facing forward_axis missing required fields: ['facing_tolerance_degrees']"
            )
    return errors
```

Only triggers when both axes are valid but tolerance is missing/null. Error added to `input_errors`, exit code 2, `.blend` not opened. Final output sorted lexicographically by 14A `canonicalize()`.

### 1.2 Call order in `_validate_and_open`

```python
pre_open_errs  = _validate_direct_child_rules_preopen(targets)
pre_open_errs += _validate_standing_up_axis_rules_preopen(targets)
pre_open_errs += _validate_facing_forward_axis_rules_preopen(targets)  # new
```

Internal ordering: direct_child -> standing -> facing. Final ordering: `sorted(ie)` (14A canonicalize).

---

## 2. Algorithm

Same transform pipeline as Standing. Inputs: `target` dict, `root_obj` (verified).

```
Step 1: Read matrix_world (at most once)
  try: mw = root_obj.matrix_world
  except -> ERROR, operation=READ_ROOT_MATRIX_WORLD

Step 2: to_3x3 (at most once)
  try: m3 = mw.to_3x3()
  except -> ERROR, operation=CONVERT_ROOT_MATRIX_WORLD_TO_3X3

  to_3x3() preserves all linear components. No decomposition/descaling/orthogonalization.

Step 3: Transform
  try: world_fwd = m3 @ mathutils.Vector(axis_to_vector(local_forward_axis))
       world_fwd_tuple = (world_fwd.x, world_fwd.y, world_fwd.z)
  except -> ERROR, operation=TRANSFORM_LOCAL_FORWARD_AXIS

Step 4: Validate and normalize
  4a. Component finiteness:
      if any(world_fwd[i] is NaN/Inf) ->
        ERROR, operation=NORMALIZE_WORLD_FORWARD_AXIS, note=NONFINITE_WORLD_FORWARD_VECTOR

  4b. Length computation:
      try: length = math.sqrt(value[0]**2 + value[1]**2 + value[2]**2)
      except (OverflowError, ValueError) ->
        ERROR, NORMALIZE_WORLD_FORWARD_AXIS, note=NONFINITE_WORLD_FORWARD_VECTOR

  4c. Length finiteness:
      if not math.isfinite(length) -> ERROR, NORMALIZE_WORLD_FORWARD_AXIS, note=NONFINITE_WORLD_FORWARD_VECTOR

  4d. Zero length:
      if length == 0.0 -> ERROR, NORMALIZE_WORLD_FORWARD_AXIS, note=ZERO_LENGTH_FORWARD_VECTOR

  4e. Normalize: actual = [x/length, y/length, z/length]

Step 5: Angle
  try: angle = vector_angle_degrees(actual, axis_to_vector(expected_world_forward_axis))
  except -> ERROR, operation=COMPUTE_FORWARD_AXIS_ANGLE

Step 6: Tolerance
  passes = (angle <= tolerance)
  angle == tolerance -> PASS
  angle >  tolerance -> FAIL, failure_code=FACING_FORWARD_AXIS_DEVIATION
```

### 2.1 Overflow semantics (corrected)

Components with large finite values may cause `value**2` to raise `OverflowError` directly (Python `OverflowError: (34, 'Result too large')`). This is caught by the `except (OverflowError, ValueError)` block at 4b. Separately, finite components that produce `inf` via `**` (IEEE 754 overflow without exception) are not caught by 4a (components were finite when checked), but produce `sqrt(inf) = inf` which is caught by 4c. Both paths route to `NORMALIZE_WORLD_FORWARD_AXIS, note=NONFINITE_WORLD_FORWARD_VECTOR`.

### 2.2 Edge cases

| Case | World result | After normalize | Angle | Verdict |
|-------|-------------|----------------|-------|---------|
| Identity +Y | (0,1,0) L=1 | (0,1,0) | 0deg | PASS |
| Rot X 90deg +Y->+Z | (0,0,1) | (0,0,1) | 90deg | tol-dependent |
| Uniform scale 2x | (0,2,0) | (0,1,0) | 0deg | PASS |
| Non-uniform (2,3,4) | (0,3,0) | (0,1,0) | 0deg | PASS |
| Neg scale Y +Y->-Y | (0,-1,0) | (0,-1,0) | 180deg | FAIL (correct) |
| Neg scale Z | (0,1,0) | (0,1,0) | 0deg | PASS |
| Shear (no effect) | (0,1,0) | (0,1,0) | 0deg | PASS |
| Shear (deviates) | e.g. (0.5,1,0) | normalized | ~26.6deg | tol-dependent |
| Zero vector | (0,0,0) L=0 | -- | -- | ERROR ZERO_LENGTH |
| NaN component | (NaN,*,*) | -- | -- | ERROR NONFINITE |
| Inf component | (Inf,*,*) | -- | -- | ERROR NONFINITE |
| value**2 OverflowError | 1e155**2 raises | -- | -- | ERROR NONFINITE (caught at 4b) |
| Rot+non-uniform scale | (0,0,3) | (0,0,1) | 90deg | tol-dependent |

---

## 3. Matrix read strategy

**Strategy A** (confirmed): Independent reads.

```
_check_standing_up_axis(target, root_obj)     -> reads matrix_world once
_check_facing_forward_axis(target, root_obj)   -> reads matrix_world once
```

No shared cache. No externally pre-read matrix. Standing's locked signature and contract unchanged.

```
Standing FAIL  -> Facing still executes
Standing ERROR -> Facing still executes
Facing FAIL    -> Standing unchanged
Facing ERROR   -> Standing unchanged
```

---

## 4. Operations (5)

| # | Operation | Trigger | Note |
|---|-----------|---------|------|
| 1 | `READ_ROOT_MATRIX_WORLD` | matrix_world access raises | READ_ROOT_MATRIX_WORLD_FAILED |
| 2 | `CONVERT_ROOT_MATRIX_WORLD_TO_3X3` | to_3x3() raises | CONVERT_ROOT_MATRIX_WORLD_TO_3X3_FAILED |
| 3 | `TRANSFORM_LOCAL_FORWARD_AXIS` | m3 @ Vector raises | TRANSFORM_LOCAL_FORWARD_AXIS_FAILED |
| 4 | `NORMALIZE_WORLD_FORWARD_AXIS` | NaN/Inf/overflow/non-finite | NONFINITE_WORLD_FORWARD_VECTOR |
|   | (same op, different branch) | length == 0.0 | ZERO_LENGTH_FORWARD_VECTOR |
| 5 | `COMPUTE_FORWARD_AXIS_ANGLE` | vector_angle_degrees raises | COMPUTE_FORWARD_AXIS_ANGLE_FAILED |

5 distinct operations. NORMALIZE_WORLD_FORWARD_AXIS has 2 error branches (note values), not independent operations.

### 4.1 ERROR structure

```json
{"facing": {"result": "ERROR", "forward_axis": {"result": "ERROR", "error_type": "FACING_FORWARD_AXIS_ERROR", "operation": "<OP>", "note": "<NOTE>"}}}
```

On ERROR, `forward_axis` omits: `local_forward_axis`, `expected_world_forward_axis`, `actual_world_forward_direction`, `angle_degrees`, `tolerance_degrees`, `failure_code`.

---

## 5. Results quick reference

**NOT_CHECKED**: `{"facing":{"result":"NOT_CHECKED","forward_axis":{"result":"NOT_CHECKED","note":"FORWARD_AXIS_RULES_NOT_CONFIGURED"}}}`

**PASS**: `{"facing":{"result":"PASS","forward_axis":{"result":"PASS","local_forward_axis":"+Y","expected_world_forward_axis":"+Y","actual_world_forward_direction":[0,1,0],"angle_degrees":0,"tolerance_degrees":15}}}`

**FAIL**: `{"facing":{"result":"FAIL","forward_axis":{"result":"FAIL","local_forward_axis":"+Y","expected_world_forward_axis":"+Y","actual_world_forward_direction":[0,-1,0],"angle_degrees":180,"tolerance_degrees":5,"failure_code":"FACING_FORWARD_AXIS_DEVIATION"}}}`

**ERROR**: `{"facing":{"result":"ERROR","forward_axis":{"result":"ERROR","error_type":"FACING_FORWARD_AXIS_ERROR","operation":"READ_ROOT_MATRIX_WORLD","note":"READ_ROOT_MATRIX_WORLD_FAILED"}}}`

---

## 6. _collect_target_errors

```python
ff = checks.get("facing", {}).get("forward_axis", {})
if ff.get("result") == "ERROR":
    op = ff.get("operation", "UNKNOWN")
    err_msgs.append(
        f"FACING_FORWARD_AXIS_ERROR: target '{tid}' "
        f"root_object_name '{rn}' operation '{op}'"
    )
```

Internal per-target collection order:

```
1. object_exists (AMBIGUOUS_ROOT_OBJECT_NAME, DIRECT_CHILD_LOOKUP_ERROR)
2. direct_children (AMBIGUOUS_DIRECT_CHILD_NAME, DIRECT_CHILD_LOOKUP_ERROR)
3. descendants (AMBIGUOUS_DESCENDANT_NAME, DESCENDANT_LOOKUP_ERROR)
4. standing (STANDING_UP_AXIS_ERROR)
5. facing (FACING_FORWARD_AXIS_ERROR)
```

This is the order produced by `_collect_target_errors` before the final `sorted(ie)` canonicalization step. The final `input_errors` array in the output JSON is lexicographically sorted by 14A `canonicalize()`.

---

## 7. Scene failure paths

| Condition | Facing |
|-----------|--------|
| `scene is None` | Omitted |
| `scene.objects` read fails | Omitted (no facing key) |
| ROOT_OBJECT_NOT_FOUND | NOT_CHECKED, note=ROOT_OBJECT_NOT_FOUND |
| ROOT_OBJECT_TYPE_MISMATCH | NOT_CHECKED, note=ROOT_OBJECT_TYPE_MISMATCH |
| AMBIGUOUS_ROOT_OBJECT_NAME | NOT_CHECKED, note=AMBIGUOUS_ROOT_OBJECT_NAME |

---

## 8. Target overall aggregation

```python
if any check == "ERROR": overall = "ERROR"
elif any check == "FAIL": overall = "FAIL"
else: overall = "PASS"
```

Facing participates equally with direct_children, descendants, and standing.

---

## 9. Scope guard contract

### 9.1 Current state

The scope guard test (`test_asset_scene_preflight_blender_scene_basic.py::TestScopeStatic`) verifies:

- `asset_scene_preflight_check.py`: 0 `.matrix_world` attribute loads
- `_check_standing_up_axis`: exactly 1 `.matrix_world` load
- All other functions in `blender_scene_reader.py`: 0 `.matrix_world` loads

### 9.2 Updated contract

After `_check_facing_forward_axis` is implemented, the scope guard must be updated to:

**File-level string checks** (unchanged):
- All existing forbidden APIs remain globally forbidden
- `.location`, `.rotation_euler`, `.rotation_quaternion` remain globally forbidden

**Per-function AST checks** (`blender_scene_reader.py`):

| Function | `.matrix_world` Load count | `.to_3x3` Call count |
|----------|--------------------------|---------------------|
| `_check_standing_up_axis` | exactly 1 | exactly 1 |
| `_check_facing_forward_axis` | exactly 1 | exactly 1 |
| All other functions | 0 | not enforced this round |

For non-standing/non-facing functions, only `.matrix_world` is enforced (must be 0). `.to_3x3` call counting is enforced only on the two authorized functions (exactly 1 each), not on all other functions.

**`asset_scene_preflight_check.py`**:
- `.matrix_world` Load: 0 (unchanged)

### 9.3 Implementation notes

- Add a `_count_attr_loads(tree, attr_name)` helper (same pattern as existing `_count_matrix_world_attr_loads`)
- Add a `_count_method_calls(tree, method_name)` for `.to_3x3()`: count `ast.Call` nodes whose `func` is `ast.Attribute` with `attr == "to_3x3"`
- Iterate all top-level functions; check the two authorized functions against their expected counts; assert all other functions have `.matrix_world` count 0
- Standing's function body and contract must not be modified to satisfy the test

---

## 10. Implementation task breakdown

### I1: Pre-open + PASS/FAIL/NOT_CHECKED

```
14B_3B_I1A: _validate_facing_forward_axis_rules_preopen
14B_3B_I1B: _check_facing_forward_axis (NOT_CHECKED/PASS/FAIL + overall aggregation + _check_root_objects integration)
```

CPython only, fake objects. No Blender execution.

### I2A: Runtime ERROR (read/convert/transform/compute)

```
READ_ROOT_MATRIX_WORLD
CONVERT_ROOT_MATRIX_WORLD_TO_3X3
TRANSFORM_LOCAL_FORWARD_AXIS
COMPUTE_FORWARD_AXIS_ANGLE
```

Four try/except boundaries. CPython tests with fake objects.

### I2B: NORMALIZE_WORLD_FORWARD_AXIS + edges

```
Zero-length vector
NaN component
+Inf / -Inf component
value**2 OverflowError from large finite components
Negative scale, non-uniform scale, shear boundaries
```

One operation (NORMALIZE) with its 2 branches (ZERO_LENGTH, NONFINITE) plus edge-case coverage.

### I3A: Scope guard static test update

AST-based per-function checks as defined in Section 9. No Blender execution. CPython only.

### I3B: Blender real mathutils

Runner script (no .blend opened) -> pytest. Real `mathutils.Matrix`/`Vector`.
Includes: identity, rotation, scale, negative scale, shear, zero-scale ERROR.
Standing+Facing joint execution verification. Runner-production algorithm consistency test.

### E: Final evidence

```
14B_3B_E1: Standing + Facing + 14A Core + full regression
14B_3B_E2: Evidence package, manifest, final ZIP
```

### I2A vs I2B boundary

- I2A: 4 operations (READ, CONVERT, TRANSFORM, COMPUTE) -- each a distinct `try/except`
- I2B: 1 operation (NORMALIZE) with its 2 branches (ZERO_LENGTH, NONFINITE) + edge-case test coverage
- No overlap: I2A does not handle NORMALIZE; I2B does not handle READ/CONVERT/TRANSFORM/COMPUTE
