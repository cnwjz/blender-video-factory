# 14B-3B I3B F-008 Contract Conflict Adjudication Report

```text
TASK_ID: 14B_3B_I3B_F008_CONTRACT_CONFLICT_ADJUDICATION
DATE: 2026-07-18
TASK_STATUS: COMPLETED
```

## Decision

```text
DECISION: MATRIX_REQUIREMENT_INCORRECT
```

## Basis

### 1. 14A Core ERROR contract

File: `protocol_guard/phase3_min/asset_scene_preflight_core.py`, lines 735-740

```python
def build_error_result(spec, spec_sha256, input_errors):
    r = _base_result(spec, spec_sha256)
    r["result"] = "ERROR"
    if input_errors:
        r["input_errors"] = list(input_errors)
    return r
```

Contrast with `build_pass_result` (line 717-723) and `build_fail_result` (line 726-732), which accept `per_target=None` parameter and include targets when provided.

`build_error_result` does NOT accept `per_target`. This is deliberate: ERROR results are generated for pre-open failures, path validation failures, open failures, and runtime CRITICAL errors. In all cases, the targets were either not yet processed or their error details have been consolidated into `input_errors`. `per_target_results` is always `[]` by design.

### 2. Entry-level aggregation flow

File: `protocol_guard/phase3_min/asset_scene_preflight_check.py`, lines 408-414

```python
any_error = any(t.get("overall") == "ERROR" for t in per_target_results)
if any_error:
    err_msgs = _collect_target_errors(per_target_results)
    return (EXIT_ERROR, build_error_result(spec, spec_sha, err_msgs))
```

`per_target_results` is used internally to detect ERROR and collect error strings. It is then discarded — `build_error_result` is called with only `input_errors`, not `per_target_results`. target overall=="ERROR" is TRUE at the internal check point (line 409) but is not serialized to the final JSON.

### 3. Facing locked design

File: `reviews/14B_3B_FACING_DESIGN_R2C1.md`, Section 6

The locked design describes `_collect_target_errors` producing stable error strings for `input_errors`. It does NOT require `per_target_results` to be included in ERROR output.

### 4. R4 matrix error

File: `14B_3B_I3B_FROZEN_ACCEPTANCE_MATRIX_R4.md`, I3B-F-008 line 146

```
REQUIRED_TARGET_ASSERTIONS | target overall=="ERROR" (Entry level)
```

This requirement is incorrect. Entry-level ERROR output deliberately excludes `per_target_results`. target overall=="ERROR" is an internal computation artifact, not available in the production JSON output for ERROR results.

### 5. Conclusion

- Entry ERROR contract requires `per_target_results == []`: TRUE (per 14A Core `build_error_result`)
- target overall=="ERROR" belongs to internal result: TRUE (per `_validate_and_open` line 409, `_check_root_objects`)
- Matrix wrongly placed internal requirement on entry level: CONFIRMED
- Production change would violate 14A locked contract: CONFIRMED (`build_error_result` signature change would break all ERROR paths)

## Required Actions

```text
MATRIX_AMENDMENT_REQUIRED: F-008 REQUIRED_TARGET_ASSERTIONS should be
  verified via internal call (_check_root_objects), not entry-level JSON.
  Entry level: verify input_errors format only.
  Internal call: verify target overall=="ERROR" + forward_axis key set.
PRODUCTION_CHANGE_REQUIRED: FALSE
```

```text
ENTRY_ERROR_REQUIRES_EMPTY_PER_TARGET_RESULTS: TRUE
TARGET_OVERALL_BELONGS_TO_INTERNAL_RESULT: TRUE
MATRIX_CONFLICT_CONFIRMED: TRUE
PRODUCTION_CONTRACT_CONFLICT_CONFIRMED: FALSE
PRODUCTION_CHANGE_REQUIRED: FALSE
MATRIX_AMENDMENT_REQUIRED: TRUE
FILES_MODIFIED: FALSE
TESTS_RUN: FALSE
CURRENT_NEXT_TASK: 14B_3B_I3B_ACCEPTANCE_FREEZE_R5 (matrix amendment)
```
