# 14B-2D-I2B1 Report

**TASK_ID**: 14B_2D_I2B1
**BASELINE_COMMIT**: d44679fc11c5069a17277395bb6c52b5a6dfc799
**HEAD_UNCHANGED**: TRUE

## Implementation
- READ_DESCENDANT_TYPE now takes priority over AMBIGUOUS_DESCENDANT_NAME
- When ambiguity exists and req_types references an ambiguous name, type reads are attempted first
- If any referenced object's .type throws → DESCENDANT_LOOKUP_ERROR (READ_DESCENDANT_TYPE)
- If all succeed → AMBIGUOUS_DESCENDANT_NAME (as before)
- Unreferenced ambiguous names: .type NOT read, AMBIGUOUS_DESCENDANT_NAME returned

## Files Modified
- protocol_guard/phase3_min/blender_scene_reader.py

## File Added
- test_asset_scene_preflight_blender_descendant_types_i2b1.py (8 tests)

## Test Results
| Suite | Passed | Failed |
|-------|--------|--------|
| I2B1 focused | 8 | 0 |
| I2A regression | 9 | 0 |
| I3A regression | 9 | 0 |

## Key Assertions
| TYPE_LOOKUP_PRECEDES_AMBIGUITY | TRUE |
| REFERENCED_AMBIGUOUS_TYPE_ERROR_RESULT | READ_DESCENDANT_TYPE |
| UNREFERENCED_AMBIGUOUS_TYPE_READ | FALSE |
| NORMAL_AMBIGUITY_PRESERVED | TRUE |
| I2A_UNIQUE_TYPE_ERROR_PRESERVED | TRUE |
| I1_NORMAL_TYPE_RESULT_PRESERVED | TRUE |
| ERROR_RESULT_OMITS_NORMAL_FIELDS | TRUE |

## Boundaries
| BLENDER_RUN | TRUE |
| BLENDER_EXECUTION_SCOPE | FACTORY_STARTUP_AUTOMATED_TESTS_ONLY |
| REAL_BLEND_OPENED | FALSE |
| RENDER_RUN | FALSE |
| SAVE_RUN | FALSE |
| ASSET_SCENE_PREFLIGHT_CORE_MODIFIED | FALSE |
| ASSET_SCENE_PREFLIGHT_CHECK_MODIFIED | FALSE |
| I2B2_STARTED | FALSE |
| GIT_COMMIT_RUN | FALSE |
| GIT_PUSH_RUN | FALSE |
