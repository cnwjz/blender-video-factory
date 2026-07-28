# 14B-3A-I2 -- Real Blender mathutils Matrix Boundary Test Report

```text
TASK_STATUS: COMPLETED
TASK_ID: 14B_3A_I2
DATE: 2026-07-18
```

## Modified Files

| File | Change |
|------|--------|
| `protocol_guard/phase3_min/tests/blender_standing_i2_runner.py` | New: Blender runner with inlined locked algorithm + real mathutils |
| `protocol_guard/phase3_min/tests/test_asset_scene_preflight_blender_standing_i2.py` | New: pytest that spawns Blender once and asserts all 9 scenarios |

Production code NOT modified.

## Runner Design

The runner inlines the LOCKED `_check_standing_up_axis` algorithm and LOCKED 14A core helpers (`axis_to_vector`, `vector_angle_degrees`) to avoid the `protocol_guard.frozen.snapshot → import yaml` chain, which is unavailable in Blender's bundled Python. The full module import chain is tested by the existing Blender entry point (`asset_scene_preflight_check.py`) which uses `--dependency-site-packages`. The I2 runner isolates the matrix math logic for targeted boundary testing.

The inlined algorithm is byte-identical to `blender_scene_reader.py:_check_standing_up_axis` per design R2 sections 7 and 10.

## Blender Test Scenarios (9 total)

| # | Scenario | Matrix | Result | Key Verification |
|---|----------|--------|--------|------------------|
| 1 | Identity | `Matrix.Identity(4)` | PASS | +Z→+Z, angle=0°, tol=0 |
| 2 | Rot X 90deg | `Matrix.Rotation(90deg, 4, 'X')` | PASS | +Z→-Y, direction (-0,-1,0) |
| 3 | Rot Y 90deg | `Matrix.Rotation(90deg, 4, 'Y')` | PASS | +Z→+X, direction (1,0,0) |
| 4 | Neg Z scale | `Matrix.Diagonal((1,1,-1,1))` | FAIL | +Z→-Z, angle≈180°, code=STANDING_UP_AXIS_DEVIATION |
| 5 | Non-uniform scale | `Matrix.Diagonal((2,3,4,1))` | PASS | +Z→+Z, normalized direction, tol=1 |
| 6 | Rot+Scale combined | `Rot(X,90) @ Diag(2,3,4)` | PASS | +Z→-Y, direction correct after normalization |
| 7 | Shear ZX tol=30 | ZX shear 0.5 | PASS | angle≈26.6° < 30° |
| 8 | Shear ZX tol=10 | ZX shear 0.5 | FAIL | angle≈26.6° > 10°, code=STANDING_UP_AXIS_DEVIATION |
| 9 | Zero Z scale | `Matrix.Diagonal((1,1,0,1))` | ERROR | ZERO_LENGTH_UP_VECTOR |

All 9 scenarios produce the expected `result` field. The Blender runner also verifies `direction`, `angle_degrees`, `failure_code`, `operation`, and `note` fields for each scenario type.

## Standalone Verification Command

```bat
blender --background --factory-startup --python blender_standing_i2_runner.py
```

Output: `PASS=OK` and `BLENDER_STANDING_I2_RESULTS=[...]` with all 9 entries.

## Test Results

```text
BLENDER_I2_TEST:  10 passed, 0 failed (1.44s)
CPYTHON_I1_I1C3:  58 passed, 0 failed (0.38s)
TOTAL_STANDING:   68 passed, 0 failed
```

## Boundary Compliance

```text
BLENDER_EXECUTED: TRUE (--background --factory-startup only)
REAL_PROJECT_BLEND_OPENED: FALSE
PRODUCTION_CODE_MODIFIED: FALSE
14A_CORE_MODIFIED: FALSE
LOCKED_LOGIC_MODIFIED: FALSE
MASTER_MAP_MODIFIED: FALSE
STANDING_LOCKED: FALSE
NEXT_TASK_STARTED: FALSE
```
