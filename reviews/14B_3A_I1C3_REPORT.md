# 14B-3A-I1C3 -- _collect_target_errors Standing Extension Report

```text
TASK_STATUS: COMPLETED
TASK_ID: 14B_3A_I1C3
DATE: 2026-07-18
```

## Modified Files

| File | Change |
|------|--------|
| `protocol_guard/phase3_min/asset_scene_preflight_check.py` | Added standing ERROR collection in `_collect_target_errors()` |
| `protocol_guard/phase3_min/tests/test_asset_scene_preflight_blender_standing_i1c3.py` | New file: 9 tests |

## Implementation

Added 5 lines to `_collect_target_errors()` after descendants ERROR block, before `return err_msgs`:

```python
su = checks.get("standing", {}).get("up_axis", {})
if su.get("result") == "ERROR":
    op = su.get("operation", "UNKNOWN")
    err_msgs.append(
        f"STANDING_UP_AXIS_ERROR: target '{tid}' "
        f"root_object_name '{rn}' operation '{op}'"
    )
```

Follows design R2 Section 5 exactly:
- Reads `checks.standing.up_axis`, not `checks.standing` directly
- Appended after descendants errors for same target (natural loop order)
- Existing error order preserved, no global re-sort
- Missing operation defaults to `UNKNOWN`

## Test Coverage (9 tests)

| Test | Verifies |
|------|----------|
| standing_error_alone | Single standing ERROR → 1 message collected |
| standing_error_with_descendants_error_order | Both ERRORs → descendants first, standing second |
| descendants_error_standing_pass | Only descendants error collected |
| descendants_fail_standing_fail | overall=FAIL → no top-level errors |
| operation_missing_uses_unknown | Missing operation → "UNKNOWN" |
| standing_not_checked | NOT_CHECKED standing → no standing error |
| no_standing_key | Missing standing key → graceful skip |
| multiple_targets_preserve_order | Multi-target order preserved |
| error_message_format_exact | Exact format string match |

## Focused Test Result

```text
COMMAND: python -m pytest standing_i1.py standing_i1b.py standing_i1c1.py standing_i1c2.py standing_i1c3.py -v --tb=short
COLLECTED: 58
PASSED: 58
FAILED: 0
TIME: 0.43s

I1A (pre-open):    11 passed
I1B (PASS/FAIL):   13 passed
I1C1 (4 runtime):  14 passed
I1C2 (normalize):  11 passed
I1C3 (collect):     9 passed
```

## Boundary Compliance

```text
BLENDER_EXECUTED: FALSE
REAL_PROJECT_BLEND_OPENED: FALSE
14A_CORE_MODIFIED: FALSE
LOCKED_LOGIC_MODIFIED: FALSE
BLENDER_SCENE_READER_MODIFIED: FALSE
MASTER_MAP_MODIFIED: FALSE
STANDING_LOCKED: FALSE
NEXT_TASK_STARTED: FALSE
```
