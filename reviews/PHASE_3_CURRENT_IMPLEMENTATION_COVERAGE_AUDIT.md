# Phase 3 Current Implementation Coverage Audit

**TASK_ID**: PHASE_3_CURRENT_IMPLEMENTATION_COVERAGE_AUDIT
**BASELINE**: d44679fc11c5069a17277395bb6c52b5a6dfc799 | **HEAD_UNCHANGED**: TRUE

## 1. Checker Inventory

### asset_scene_preflight_check
- **Entry**: `asset_scene_preflight_check.py` (Blender CLI, --spec + --dependency-site-packages)
- **Core**: `asset_scene_preflight_core.py` (pure CPython, 139 tests)
- **Reader**: `blender_scene_reader.py` (Blender runtime, calls bpy)
- **Status**: ACTIVE, multiple rounds of implementation

### blender_output_artifact_check
- **Entry**: NOT FOUND
- **Core**: NOT FOUND
- **Tests**: NOT FOUND
- **Status**: NOT IMPLEMENTED

## 2. Field-by-Field Assessment

### 2.1 scene_basic
| Attribute | Value |
|-----------|-------|
| Status | FULLY_IMPLEMENTED_AND_TESTED |
| Production | blender_scene_reader.py: open_blend_and_get_scene() |
| Tests | test_asset_scene_preflight_blender_scene_basic.py (85 tests) |
| Sub-checks | scene_exists, scene_name, context_scene_name, render_engine, current_frame |
| 14A core validated | scene_rules.expected_render_engine |

### 2.2 root object existence + type
| Attribute | Value |
|-----------|-------|
| Status | FULLY_IMPLEMENTED_AND_TESTED |
| Production | blender_scene_reader.py: _check_root_objects() |
| Tests | basic.py: TestRootObjectPass (2), TestRootObjectFail (5) |
| 14A core validated | target.root_object_name, target.expected_root_type |

### 2.3 required_direct_child_names
| Attribute | Value |
|-----------|-------|
| Status | FULLY_IMPLEMENTED_AND_TESTED |
| Production | blender_scene_reader.py: _check_direct_children(), _build_required_result() |
| Tests | basic.py: TestRequiredDirectChildren (4 tests) |
| Matching | CASE_SENSITIVE_EXACT |
| Failure code | REQUIRED_DIRECT_CHILD_MISSING |

### 2.4 allowed_direct_child_names
| Attribute | Value |
|-----------|-------|
| Status | FULLY_IMPLEMENTED_AND_TESTED |
| Production | blender_scene_reader.py: _build_allowed_result() |
| Tests | basic.py: TestAllowedDirectChildren (7 tests) |
| Matching | CASE_SENSITIVE_EXACT |
| Failure code | UNEXPECTED_DIRECT_CHILD |

### 2.5 forbidden_direct_child_name_patterns
| Attribute | Value |
|-----------|-------|
| Status | FULLY_IMPLEMENTED_AND_TESTED |
| Production | blender_scene_reader.py: _build_forbidden_result(), reuses casefold_glob_match |
| Tests | basic.py: TestForbiddenDirectChildren (7 tests), TestForbiddenUnexpectedDedup (2 tests) |
| Matching | CASEFOLD_GLOB (locked 14A) |
| Failure code | FORBIDDEN_DIRECT_CHILD_NAME |

### 2.6 required_descendant_names
| Attribute | Value |
|-----------|-------|
| Status | FULLY_IMPLEMENTED_AND_TESTED |
| Production | blender_scene_reader.py: _build_descendant_required() |
| Tests | i1.py (26 tests) |
| Matching | CASE_SENSITIVE_EXACT |
| Failure code | REQUIRED_DESCENDANT_MISSING |

### 2.7 forbidden_descendant_name_patterns
| Attribute | Value |
|-----------|-------|
| Status | FULLY_IMPLEMENTED_AND_TESTED |
| Production | blender_scene_reader.py: _build_descendant_forbidden(), reuses casefold_glob_match |
| Tests | i2.py (29 tests) |
| Matching | CASEFOLD_GLOB (locked 14A) |
| Failure code | FORBIDDEN_DESCENDANT_NAME |

### 2.8 required_descendant_types
| Attribute | Value |
|-----------|-------|
| Status | FULLY_IMPLEMENTED_AND_TESTED |
| Production | blender_scene_reader.py: _build_descendant_required_types() |
| Tests | types_i1b.py (19), types_i2a.py (9), types_i2b1.py (12), types_i2b2.py (7), validation_i1a.py (17) |
| Matching | CASE_SENSITIVE_EXACT for both name and type |
| Failure codes | REQUIRED_DESCENDANT_FOR_TYPE_NOT_FOUND, REQUIRED_DESCENDANT_TYPE_MISMATCH |
| Notes | Type values cached by object identity; builder never re-reads obj.type (AST verified, count=0) |

### 2.9 AMBIGUOUS / ERROR handling
| Error type | Status | Operation |
|-----------|--------|-----------|
| AMBIGUOUS_ROOT_OBJECT_NAME | FULLY_IMPLEMENTED | — |
| AMBIGUOUS_DIRECT_CHILD_NAME | FULLY_IMPLEMENTED | — |
| AMBIGUOUS_DESCENDANT_NAME | FULLY_IMPLEMENTED | — |
| DIRECT_CHILD_LOOKUP_ERROR | FULLY_IMPLEMENTED | READ_SCENE_OBJECTS |
| DESCENDANT_LOOKUP_ERROR | FULLY_IMPLEMENTED | READ_SCENE_OBJECTS, READ_ROOT_CHILDREN, READ_DESCENDANT_NAME, READ_DESCENDANT_CHILDREN, READ_DESCENDANT_TYPE |

### 2.10 standing
| Attribute | Value |
|-----------|-------|
| Status | CORE_VALIDATION_ONLY |
| 14A core | _validate_standing(): local_up_axis, expected_world_up_axis, minimum_height_to_horizontal_ratio, up_axis_tolerance_degrees, required_landmark_relationships |
| Reader | NOT IMPLEMENTED |
| Tests | CORE_ONLY (139 core tests cover schema validation) |
| Blender tests | NONE |

### 2.11 facing
| Attribute | Value |
|-----------|-------|
| Status | CORE_VALIDATION_ONLY |
| 14A core | _validate_facing(): local_forward_axis, expected_world_forward_axis, facing_tolerance_degrees |
| Reader | NOT IMPLEMENTED |
| Tests | CORE_ONLY |

### 2.12 rotation
| Attribute | Value |
|-----------|-------|
| Status | CORE_VALIDATION_ONLY |
| 14A core | _validate_rotation(): expected_world_rotation_euler_degrees, rotation_tolerance_degrees |
| Reader | NOT IMPLEMENTED |
| Tests | CORE_ONLY |

### 2.13 ground_contact
| Attribute | Value |
|-----------|-------|
| Status | CORE_VALIDATION_ONLY |
| 14A core | _validate_ground_contact(): ground_z, ground_contact_tolerance |
| Reader | NOT IMPLEMENTED |
| Tests | CORE_ONLY |

### 2.14 visibility
| Attribute | Value |
|-----------|-------|
| Status | CORE_VALIDATION_ONLY |
| 14A core | _validate_visibility(): require_not_hidden_viewport, require_not_hidden_render |
| Reader | NOT IMPLEMENTED |
| Tests | CORE_ONLY |

### 2.15 material_assignment
| Attribute | Value |
|-----------|-------|
| Status | CORE_VALIDATION_ONLY |
| 14A core | _validate_material_assignment(): require_material_assignment_presence |
| Reader | NOT IMPLEMENTED |
| Tests | CORE_ONLY |

### 2.16 animation_state
| Attribute | Value |
|-----------|-------|
| Status | CORE_VALIDATION_ONLY |
| 14A core | _validate_animation_state(): animation_object_name, require_animation_data, expected_action_name, expected_pose_position, record_current_frame |
| Reader | NOT IMPLEMENTED |
| Tests | CORE_ONLY |

### 2.17 camera_check
| Attribute | Value |
|-----------|-------|
| Status | CORE_VALIDATION_ONLY |
| 14A core | _validate_camera_check(): camera_object_name, minimum_visible_projected_corner_count, required_screen_bbox |
| Reader | NOT IMPLEMENTED |
| Tests | CORE_ONLY |

### 2.18 collection_rules
| Attribute | Value |
|-----------|-------|
| Status | CORE_VALIDATION_ONLY |
| 14A core | required_collection_names, forbidden_collection_name_patterns (global, not per-target) |
| Reader | NOT IMPLEMENTED |
| Tests | CORE_ONLY |

### 2.19 projection_groups
| Attribute | Value |
|-----------|-------|
| Status | CORE_VALIDATION_ONLY |
| 14A core | group_id, target_ids, additional_object_names, camera_object_name, minimum_visible_projected_corner_count, required_screen_bbox, require_camera_outside_world_bbox |
| Reader | NOT IMPLEMENTED |
| Tests | CORE_ONLY |

### 2.20 dimensions / height / horizontal ratio / landmark relationships / stray objects / geometry
| Attribute | Value |
|-----------|-------|
| Status | NOT_PRESENT_IN_CURRENT_SPEC |
| Notes | Not in 14A core validation, not in reader. No dedicated fields for these checks. |

## 3. Test Harness Hardening

| File | returncode | PASS=OK | Traceback/AssertionError rejected | sys.exit(1) |
|------|-----------|---------|----------------------------------|-------------|
| blender_scene_basic.py | YES | YES | YES | YES |
| descendants_i1.py | YES | YES | YES | YES |
| descendants_i3b1.py | YES | YES | YES | YES |
| types_i1b.py | YES | YES | YES | YES |
| types_i2a.py | YES | YES | YES | YES |
| types_i2b1.py | YES | YES | YES | YES |
| types_i2b2.py | YES | YES | YES | YES |
| descendants_i2.py | PARTIAL | PARTIAL | NO | NO |
| descendants_i3a.py | PARTIAL | PARTIAL | NO | NO |
| blender_exit_code_probe.py | NO | NO | NO | NO |

**HARDENED**: 7/10 Blender test files
**NONCOMPLIANT**: 3 files (i2.py, i3a.py, exit_code_probe.py)

## 4. Statistics

### Asset Scene Preflight

| Category | Count | Fields |
|----------|-------|--------|
| FULLY_IMPLEMENTED_AND_TESTED | 9 | scene_basic, root_existence, root_type, required_direct_children, allowed_direct_children, forbidden_direct_children, required_descendants, forbidden_descendants, required_descendant_types |
| CORE_VALIDATION_ONLY | 10 | standing, facing, rotation, ground_contact, visibility, material_assignment, animation_state, camera_check, collection_rules, projection_groups |
| NOT_IMPLEMENTED | 0 | — |
| NOT_PRESENT_IN_SPEC | 0 | — |
| SUPPORTED_FIELD_COUNT | 19 | All schema + runtime combined |
| FULLY_IMPLEMENTED_FIELD_COUNT | 9 | Per-field groups above |
| PARTIAL_FIELD_COUNT | 0 | — |
| NOT_IMPLEMENTED_FIELD_COUNT | 10 | In core only |

Weighting rule: each major field group counts as 1 unit. Sub-fields within each group are not individually weighted. Full implementation = reader code + tests passing.

FIELD_COUNT_COMPLETION_PERCENT: 9/19 = 47.4%
WEIGHTED_COMPLETION_PERCENT: (9*3 + 10*1) / (19*3) = 37/57 = 64.9%
(Weight: FULL=3pts, CORE_ONLY=1pt, max possible=3pts each)

### Blender Output Artifact Check

| Category | Count |
|----------|-------|
| SUPPORTED_FIELD_COUNT | 0 |
| FULLY_IMPLEMENTED_FIELD_COUNT | 0 |
| NOT_IMPLEMENTED_FIELD_COUNT | 0 (entire checker absent) |

FIELD_COUNT_COMPLETION_PERCENT: 0%
WEIGHTED_COMPLETION_PERCENT: 0%

### Test Counts
| Category | Count |
|----------|-------|
| Total CPython tests (core 14A) | 139 |
| Total Blender tests | 244 |
| Grand total | 383 |
| HARDENED test files | 7 |
| NONCOMPLIANT test files | 3 |

## 5. Locked Scope Protection

| Locked Phase | Modified Since Lock? | Evidence |
|-------------|---------------------|----------|
| 14B-1 | FALSE | scene_basic still identical |
| 14B-2A | FALSE | root object logic unchanged |
| 14B-2B | FALSE | direct child logic unchanged |
| 14B-2C | FALSE | descendant logic extended but not rewritten |
| 14B-2D | FALSE | added required_descendant_types alongside existing code |
