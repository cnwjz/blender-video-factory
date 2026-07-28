# Animation State I5 R9 Correction Report

```text
TASK_ID: ANIMATION_STATE_I5_R9_CORRECTION
TASK_TYPE: CORRECTION
DATE: 2026-07-24
TASK_STATUS: CORRECTED_PENDING_INDEPENDENT_CHECK
```

## Correction

```text
F_001_STATUS: PARTIAL — 6 of 8 test_allowed_missing_fails + test_allowed_wrong_prefix fail
F_002_STATUS: FIXED
PYTHON_VERSION: 3.14.5
PRODUCTION_CODE_MODIFIED: FALSE
OTHER_EXISTING_TESTS_MODIFIED: FALSE
```

## F_001 Detail

`ACCESS_EXPRESSIONS` values provided in task spec are not all unique in `blender_scene_reader.py`:

```text
scene.objects: 6 occurrences → _replace_once assert fails
obj.name: 2 occurrences → _replace_once assert fails
scene.frame_current: 2 occurrences → _replace_once assert fails
matched_obj.animation_data: 1 occurrence → PASS
ad_cached.action: 1 occurrence → PASS
action.name: 1 occurrence → PASS
matched_obj.data: 1 occurrence → PASS
obj_data.pose_position: 1 occurrence → PASS
```

The `_replace_once` implementation requires `source.count(old) == 1` (assertion on line 294).

Tests modified exactly per task spec: old `test_allowed_missing_fails` (checking baseline `_BASELINE` count==1) and old `test_allowed_wrong_prefix` (using `_inject` to inject duplicates) replaced with new implementations using `ACCESS_EXPRESSIONS`, `WRONG_PREFIX_EXPRESSIONS`, and `_replace_once`. `test_allowed_duplicate` and all 7 fixed probes preserved unchanged.

## Matrices

```text
ALLOWED_MISSING_MATRIX_PASS: FALSE (6 failed: scene.objects, obj.name, scene.frame_current)
ALLOWED_DUPLICATE_MATRIX_PASS: TRUE (8× injection verified)
ALLOWED_WRONG_PREFIX_MATRIX_PASS: FALSE (6 failed: same 3 attributes)
SEVEN_FIXED_PROBES_PASS: TRUE
```

## Test Result

```text
I5_FOCUSED_RESULT: 58 passed, 6 failed, exit 1
```

## Lint

```text
FOCUSED_TEST_LINT_RESULT: PASS
FOCUSED_TEST_LINT_EXIT_CODE: 0
MASTER_MAP_LINT_RESULT: FAIL
MASTER_MAP_LINT_EXIT_CODE: 1
MASTER_MAP_LINT_ISSUE: Section9_visibility_progress row format mismatch (pre-existing)
```
