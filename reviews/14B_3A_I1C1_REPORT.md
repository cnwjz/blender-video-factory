# 14B-3A-I1C1 — Standing Up Axis Runtime Error Operations Report

```text
TASK_STATUS: COMPLETED
TASK_ID: 14B_3A_I1C1
DATE: 2026-07-18
```

## Modified Files

| File | Change |
|------|--------|
| `protocol_guard/phase3_min/blender_scene_reader.py` | Added four try/except blocks in `_check_standing_up_axis()` |
| `protocol_guard/phase3_min/tests/test_asset_scene_preflight_blender_standing_i1c1.py` | New file: 14 tests |

## Four Operations Implemented

Each operation wraps exactly one step in `_check_standing_up_axis()` with try/except:

| # | Operation | What It Wraps | Line |
|---|-----------|---------------|------|
| 1 | `READ_ROOT_MATRIX_WORLD` | `mw = root_obj.matrix_world` | after local_vec/expected_vec |
| 2 | `CONVERT_ROOT_MATRIX_WORLD_TO_3X3` | `m3 = mw.to_3x3()` | after Step 1 |
| 3 | `TRANSFORM_LOCAL_UP_AXIS` | `world_up_v = m3 @ mathutils.Vector(local_vec)` + tuple extraction | after Step 2 |
| 4 | `COMPUTE_UP_AXIS_ANGLE` | `angle = vector_angle_degrees(actual_world, expected_vec)` | after normalize |

Each on exception returns:
```json
{
  "result": "ERROR",
  "up_axis": {
    "result": "ERROR",
    "error_type": "STANDING_UP_AXIS_ERROR",
    "operation": "<OP>",
    "note": "<OP>_FAILED"
  }
}
```

## Normal Result Fields Omitted on ERROR

Confirmed for all four operations:

```text
FIELDS_OMITTED:
  - local_up_axis
  - expected_world_up_axis
  - actual_world_up_direction
  - angle_degrees
  - tolerance_degrees
  - failure_code
FIELDS_PRESENT:
  - result
  - up_axis.result
  - up_axis.error_type
  - up_axis.operation
  - up_axis.note
```

## Matrix Read / to_3x3 Call Constraints

```text
MATRIX_WORLD_READ_ONCE_PRESERVED: TRUE
TO_3X3_CALL_ONCE_PRESERVED: TRUE
```

Verified by:
- `test_matrix_world_read_at_most_once` (PASS path)
- `test_to_3x3_called_once` (PASS path)
- `test_matrix_world_not_read_after_to_3x3_fails` (CONVERT error path)
- `test_to_3x3_called_once_before_matmul_fails` (TRANSFORM error path)
- `test_matrix_world_read_once_before_angle_fails` (COMPUTE error path)

## Integration

`_check_root_objects` already aggregates `su_r == "ERROR"` into `overall = "ERROR"`.
Verified by `test_standing_error_makes_overall_error` — subprocess test confirms:
- `overall` = `"ERROR"`
- `standing.result` = `"ERROR"`
- `standing.up_axis.error_type` = `"STANDING_UP_AXIS_ERROR"`
- `standing.up_axis.operation` = `"READ_ROOT_MATRIX_WORLD"`

## Focused Test Result

```text
COMMAND: python -m pytest standing_i1.py standing_i1b.py standing_i1c1.py -v --tb=long
COLLECTED: 38
PASSED: 38
FAILED: 0
TIME: 0.32s

I1A (pre-open):   11 passed
I1B (PASS/FAIL):  13 passed
I1C1 (ERRORs):    14 passed
```

## Boundary Compliance

```text
BLENDER_EXECUTED: FALSE
REAL_PROJECT_BLEND_OPENED: FALSE
14A_CORE_MODIFIED: FALSE
LOCKED_LOGIC_MODIFIED: FALSE
MASTER_MAP_MODIFIED: FALSE
NEXT_TASK_STARTED: FALSE

NOT_IMPLEMENTED (per scope):
  - Zero-length vector ERROR (NORMALIZE_WORLD_UP_AXIS)
  - NaN / Inf classification
  - _collect_target_errors extension for standing
  - Real Blender boundary tests
  - Standing regression
  - 14A Core regression
  - Full regression
  - Final evidence package
```

## Remaining Standing Work

Per design R2:
- `NORMALIZE_WORLD_UP_AXIS` (zero-length, NaN, Inf)
- `_collect_target_errors` standing extension
- Real Blender boundary tests
- Standing regression
- 14B_3A_E final lock
