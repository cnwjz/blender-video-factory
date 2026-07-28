# 14B-2D-I2C1 Regression Report

**TASK_ID**: 14B_2D_I2C1
**BASELINE**: d44679fc11c5069a17277395bb6c52b5a6dfc799
**HEAD_UNCHANGED**: TRUE

## Test Results
| Suite | Passed | Failed |
|-------|--------|--------|
| I2A focused | 9 | 0 |
| I2B1 focused | 8 | 0 |
| I2B2 focused | 7 | 0 |
| I1A focused | 17 | 0 |
| I1B focused | 19 | 0 |
| Descendant regression | 73 | 0 |
| 14A core | 139 | 0 |
| protocol_guard | 631 | 0 (2 skipped) |

## Static Read-Only Check
- Only reads: scene.objects, root.children, descendant.name, descendant.children, descendant.type
- No: bpy.data.objects, object.parent, geometry, transform, material, animation, camera, render, save
- **PASS**

## Boundaries
| PRODUCTION_FILES_MODIFIED_THIS_TASK | 0 |
| TEST_FILES_MODIFIED_THIS_TASK | 0 |
| BLENDER_RUN | TRUE |
| BLENDER_EXECUTION_SCOPE | FACTORY_STARTUP_AUTOMATED_TESTS_ONLY |
| REAL_BLEND_OPENED | FALSE |
| RENDER_RUN | FALSE |
| SAVE_RUN | FALSE |
| BLENDER_DATA_MODIFIED | FALSE |
| UNAUTHORIZED_API_FOUND | FALSE |
| GIT_COMMIT_RUN | FALSE |
| GIT_PUSH_RUN | FALSE |
| NEXT_TASK_STARTED | FALSE |
