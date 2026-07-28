# Rotation E Final Regression R9 Report

```text
TASK_ID: ROTATION_E_FINAL_REGRESSION_R9_CORRECTION
DATE: 2026-07-21
TASK_STATUS: FOCUSED_TESTED
E_REGRESSION_EXECUTED: TRUE
```

## Fix (R9)

```text
F1: Use pytest.raises(StopIteration) for the teardown next(_gen).
    Teardown assertions (module_original, global_original) now execute
    inside the try block, after pytest.raises, before finally.
    StopIteration no longer skips the assertions.
```

## Results

```text
Rotation I1-I4B:  158 passed, 0 failed, exit 0
Full protocol_guard: 1164 passed, 0 failed, 2 skipped, exit 0
```

## SHA256

```text
FROZEN: check.py (b23159f6), core.py (9b5daa1c), reader.py (ef6ed7eb)
FROZEN: conftest.py (c4b937fc), rotation_i3.py (38da809d)
MODIFIED: rotation_i2.py (R9): from manifest
```

## Deliverable

```text
UPLOAD_NEXT_FILE: reviews/UPLOAD_NEXT/ROTATION_E_FINAL_REGRESSION/ROTATION_E_FINAL_REGRESSION_R9_CORRECTION_UPLOAD.zip
```
