# 14B-3A-E1 -- Runner Consistency & Standing Full Focus Report (R2)

```text
TASK_STATUS: COMPLETED
TASK_ID: 14B_3A_E1
DATE: 2026-07-18
REVISION: R2 (helper AST comparison replaced with output equivalence)
```

## Modified Files

| File | Change |
|------|--------|
| `protocol_guard/phase3_min/tests/test_asset_scene_preflight_blender_standing_runner_consistency.py` | Rewritten: main algorithm AST + extracted helper output comparison |

Production code, runner, master map NOT modified. No .blend opened.

## Test Results (R2)

```text
73 passed, 0 failed, 0 xfailed
```

```text
SUITE                                      PASSED  FAILED
────────────────────────────────────────  ───────  ──────
CPython I1A (pre-open validation)             11       0
CPython I1B (PASS/FAIL/NOT_CHECKED)           13       0
CPython I1C1 (4 runtime ERRORs)               14       0
CPython I1C2 (NORMALIZE_WORLD_UP_AXIS)        11       0
CPython I1C3 (_collect_target_errors)          9       0
Runner main algorithm AST consistency          1       0
Runner axis_to_vector output (6 axes)          1       0
Runner vector_angle_degrees output:
  -- 36 axis combinations                      1       0
  -- 36 shear direction pairs                  1       0
  -- 18 non-axis × axis pairs                  1       0
Blender I2 (real mathutils)                   10       0
────────────────────────────────────────  ───────  ──────
TOTAL                                         73       0
```

## Consistency Test Design (R2)

### Main Algorithm (AST comparison)

`check_standing_up_axis` from runner is compared against
`_check_standing_up_axis` from blender_scene_reader.py after normalizing
function name, stripping docstring, and removing body-level import statements.
AST dump is byte-identical. **PASSED**.

### Helpers (output equivalence via AST extraction)

Runner's `axis_to_vector` and `vector_angle_degrees` are extracted from the
runner source AST, compiled with `compile()`, and executed. Their outputs are
compared against 14A Core for a comprehensive input set:

| Helper | Inputs | Tolerance |
|--------|--------|-----------|
| `axis_to_vector` | 6 axes (+X/-X/+Y/-Y/+Z/-Z) | per-component exact match |
| `vector_angle_degrees` | 36 axis pairs | 1e-8 deg |
| `vector_angle_degrees` | 36 shear/non-axis pairs | 1e-5 deg |
| `vector_angle_degrees` | 18 non-axis × axis pairs | 1e-5 deg |

The 1e-5 tolerance for non-axis vectors accommodates the known semantic
difference: the runner does not re-normalize inputs (inputs are pre-normalized
by the caller), while 14A Core normalizes internally via `dot / (la * lb)`.
For axis vectors this has zero effect. For float64-computed unit vectors the
effect is at most ~1.2e-6 degrees (below 1e-5 safety margin).

## Boundary Compliance

```text
BLENDER_EXECUTED: TRUE (--background --factory-startup for I2 only)
REAL_PROJECT_BLEND_OPENED: FALSE
PRODUCTION_CODE_MODIFIED: FALSE
14A_CORE_MODIFIED: FALSE
LOCKED_LOGIC_MODIFIED: FALSE
MASTER_MAP_MODIFIED: FALSE
RUNNER_MODIFIED: FALSE
STANDING_LOCKED: FALSE
E2_STARTED: FALSE
```
