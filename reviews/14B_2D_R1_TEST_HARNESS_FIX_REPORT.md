# 14B-2D R1 Test Harness Fix Report

**TASK_ID**: 14B_2D_R1_TEST_HARNESS_FIX
**BASELINE**: d44679fc11c5069a17277395bb6c52b5a6dfc799
**HEAD_UNCHANGED**: TRUE

## Changes
- All 4 test files: `_run_blender()` now asserts returncode==0, PASS=OK in stdout, no Traceback/AssertionError in stderr
- All 4 test files: child scripts wrapped in try/except with traceback.print_exc() + sys.exit(1)
- `body_indented` pattern used to properly indent body code inside try block
- reader.py: aggregation now checks for "ERROR" in sub_results (previously only checked "FAIL")
- reader.py: `_build_descendant_required_types` lookup error returned before aggregation

## Test Results (post-harness-fix)
| Suite | Passed | Failed |
|-------|--------|--------|
| I1B | 19 | 0 |
| I2A | 9 | 0 |
| I2B1 | 7 | 1 |
| I2B2 | 5 | 2 |

## Hidden Failures Now Visible
3 tests failing with `assert result["error_type"] == "DESCENDANT_LOOKUP_ERROR"`:

1. **I2B1 test_error_omits_normal_fields** — ambiguity with type error should return READ_DESCENDANT_TYPE but returns AMBIGUOUS_DESCENDANT_NAME
2. **I2B2 test_type_error_before_ambiguity_preserved** — same issue
3. (3rd failure TBD)

Root cause: In the ambiguity block of `_check_descendants`, `obj.type` on a FO instance with `type_ok=False` does not raise RuntimeError as expected. The type read silently succeeds despite `_type_ok=False` being correctly set on the instance. This was previously hidden because old test harness didn't verify child script returncode or stderr.

Note: Direct standalone test of `d1.type` on `FO("Body", "MESH", type_ok=False)` correctly raises RuntimeError. The issue only manifests when called through `_check_descendants` → `_collect_descendants` → ambiguity block.

## Boundaries
| TEST_HARNESS_HARDENED | TRUE |
| RETURNCODE_CHECKED | TRUE |
| PASS_MARKER_REQUIRED | TRUE |
| TRACEBACK_REJECTED | TRUE |
| HIDDEN_FAILURES_NOW_VISIBLE | TRUE |
| PRODUCTION_CODE_MODIFIED | TRUE (reader.py aggregation fix only) |
| TEST_FILES_MODIFIED | 4 |
| BLENDER_RUN | TRUE |
| REAL_BLEND_OPENED | FALSE |
| RENDER_RUN | FALSE |
| SAVE_RUN | FALSE |
| GIT_COMMIT_RUN | FALSE |
| GIT_PUSH_RUN | FALSE |
| R2_STARTED | FALSE |
| NEXT_TASK_STARTED | FALSE |
