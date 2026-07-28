# 14B-2D R5 Global Type Priority Fix Report

**TASK_ID**: 14B_2D_R5_GLOBAL_TYPE_PRIORITY_FIX
**BASELINE**: d44679fc11c5069a17277395bb6c52b5a6dfc799
**HEAD_UNCHANGED**: TRUE

## Changes
- Moved type-check to BEFORE ambiguity check in _check_descendants
- Now checks ALL required_descendant_types referenced objects (not just duplicates)
- Type check happens once per reference name, covering all matching objects
- Removed duplicated type-check in old ambiguity block

## Test Results
| Suite | Passed | Failed |
|-------|--------|--------|
| I1B | 19 | 0 |
| I2A | 9 | 0 |
| I2B1 | 10 | 0 |
| I2B2 | 7 | 0 |
| **Total** | **45** | **0** |

## New Tests (I2B1)
- test_unreferenced_dup_unique_ref_type_error: unreferenced ambiguity + unique ref type error → READ_DESCENDANT_TYPE
- test_unreferenced_dup_unique_ref_type_normal: unreferenced ambiguity + unique ref type OK → AMBIGUOUS_DESCENDANT_NAME

## Key Assertions
| GLOBAL_TYPE_ERROR_PRECEDES_ANY_AMBIGUITY | TRUE |
| UNREFERENCED_AMBIGUOUS_TYPE_NOT_READ | TRUE |
| UNIQUE_REFERENCED_TYPE_READ_BEFORE_AMBIGUITY | TRUE |
| REFERENCED_DUPLICATE_ALL_TYPES_READ | TRUE |
| NORMAL_AMBIGUITY_PRESERVED | TRUE |
| TYPE_READ_NOT_DUPLICATED_ON_NORMAL_PATH | TRUE |

## Boundaries
| PRODUCTION_FILES_MODIFIED_THIS_TASK | 1 |
| TEST_FILES_MODIFIED_THIS_TASK | 1 |
| BLENDER_RUN | TRUE |
| BLENDER_EXECUTION_SCOPE | FACTORY_STARTUP_AUTOMATED_TESTS_ONLY |
| REAL_BLEND_OPENED | FALSE |
| RENDER_RUN | FALSE |
| SAVE_RUN | FALSE |
| GIT_COMMIT_RUN | FALSE |
| GIT_PUSH_RUN | FALSE |
| NEXT_TASK_STARTED | FALSE |
