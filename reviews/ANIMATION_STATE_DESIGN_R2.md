# Animation State Design R2

```text
TASK_ID: ANIMATION_STATE_DESIGN_R2_CORRECTION
TASK_TYPE: DESIGN_CORRECTION
DATE: 2026-07-22
DESIGN_VERSION: R2
DESIGN_STATUS: READY_FOR_INDEPENDENT_REVIEW
IMPLEMENTATION_AUTHORIZED: FALSE
SUPERSEDES: ANIMATION_STATE_DESIGN_R1.md
```

## R2 Correction Summary

```text
F-001: Sub-check result model with independent per-check result dicts.
       Top-level aggregates. Multiple FAIL/ERROR combinations defined.

F-002: Animation State takes scene + target. Looks up animation_object_name
       from scene.objects independently. Does NOT execute inside
       _check_root_objects. Root branch behavior explicitly defined.

F-003: Uses only passed target scene (scene.objects, scene.frame_current).
       ACCESS_SCENE_REFERENCE operation removed. bpy.context.scene not used.

F-004: FAIL/ERROR boundary: AttributeError → ERROR; property=None when
       non-None required → FAIL. Consistent across all 5 sub-checks.
       All attribute read exceptions mapped.

F-005: _collect_target_errors format, message, and order defined.
       Scope guard contract with entry function, AST counts,
       runtime counts, helper boundaries, and alias rules.
```

## 1. Design Basis

| Source | Role |
|---|---|
| `ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md` §9 | AUTHORITATIVE_REQUIREMENT |
| `asset_scene_preflight_core.py` lines 370-387 | LOCKED_SCHEMA |
| `ROTATION_DESIGN_R3.md` | EXISTING_PROJECT_CONVENTION |
| `14B_4A_VISIBILITY_DESIGN_R2.md` | EXISTING_PROJECT_CONVENTION |
| `14B_3B_FACING_DESIGN_R2C1.md` | EXISTING_PROJECT_CONVENTION |
| `ANIMATION_STATE_ORIGINAL_REQUIREMENT_AUDIT_REPORT.md` (R3) | AUDIT |

## 2. Fields (unchanged from R1)

| # | Field | Type (LOCKED_SCHEMA) | Required |
|---|---|---|---|
| 1 | `animation_state.animation_object_name` | non-empty string | Yes, if block present |
| 2 | `animation_state.require_animation_data` | boolean or null | No |
| 3 | `animation_state.expected_action_name` | non-empty string or null | No |
| 4 | `animation_state.expected_pose_position` | "POSE", "REST", or null | No |
| 5 | `animation_state.record_current_frame` | boolean or null | No |

## 3. Configuration Semantics (unchanged from R1)

```text
animation_state missing → NOT_CHECKED
animation_state: null  → NOT_CHECKED
animation_state: {}    → pre-open ERROR (LOCKED_SCHEMA)

Each nullable field: null or missing → check skipped, key omitted from sub-result.
record_current_frame: false → frame not read, key omitted.
```

## 4. Integration: Root Independence

### 4.1 Call Location

```text
Animation State check takes two parameters:
  scene   — the target Scene (from bpy.data.scenes.get, already resolved)
  target  — the target dict from spec["targets"]

It looks up animation_object_name via scene.objects iteration.
It does NOT receive a pre-resolved root_obj.

Call site: in reader.py result assembly, AFTER scene_basic and root object
checks, BEFORE per-target result finalization. Same level as other
field-group checks (standing, facing, etc.).

Animation State check is called for EVERY target that has a non-null
animation_state block, REGARDLESS of root object check outcome.
```

### 4.2 Root Branch Behavior

| Root Check Outcome | Animation State Behavior | Basis |
|---|---|---|
| Root PASS (unique, type match) | Execute normally | EXISTING_PROJECT_CONVENTION |
| ROOT_OBJECT_NOT_FOUND | Execute normally (different object check) | NEW_DESIGN_DECISION |
| ROOT_OBJECT_TYPE_MISMATCH | Execute normally | NEW_DESIGN_DECISION |
| AMBIGUOUS_ROOT_OBJECT_NAME | Execute normally | NEW_DESIGN_DECISION |
| Root scene.objects lookup ERROR | Execute normally (scene is valid) | NEW_DESIGN_DECISION |

Rationale: `animation_object_name` may refer to the root object or any other
object in the scene. The root check and animation check are independent.
(EXISTING_PROJECT_CONVENTION: same pattern as Standing — Standing executes
even if direct_children fail.)

## 5. Scene Source

```text
ALL reads use the target scene passed as parameter:
  scene.objects       — object lookup
  scene.frame_current — frame recording

bpy.context.scene is NEVER used.

ACCESS_SCENE_REFERENCE operation → REMOVED (R2).
The scene is already resolved before the check is called.
```

## 6. Result Structure: Sub-Check Model

Nested path: `checks.animation_state`.

Each configured sub-check produces its own result dict. The top-level
`checks.animation_state.result` aggregates.

### 6.1 Top-Level Structure

```python
{
    "result": "<PASS|FAIL|ERROR|NOT_CHECKED>",
    # plus sub-check keys when their checks execute
}
```

### 6.2 Sub-Check Keys

| Sub-key | Present when |
|---|---|
| `animation_object` | always (if animation_state configured) |
| `animation_data` | `require_animation_data` is true |
| `action_name` | `expected_action_name` is a non-null string |
| `pose_position` | `expected_pose_position` is a non-null string |
| `current_frame` | `record_current_frame` is true |

### 6.3 NOT_CHECKED

```python
# animation_state missing or null:
{
    "result": "NOT_CHECKED",
    "note": "ANIMATION_STATE_NOT_CONFIGURED"
}
# No sub-check keys present.
```

### 6.4 Sub-Check Result Dictionaries

#### animation_object

```python
# PASS — object found:
{"result": "PASS", "object_name": "<name>"}

# FAIL — object not found:
{"result": "FAIL", "failure_code": "ANIMATION_OBJECT_NOT_FOUND",
 "object_name": "<name from spec>"}

# ERROR — lookup failure:
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "LOOKUP_ANIMATION_OBJECT",
 "note": "LOOKUP_ANIMATION_OBJECT_FAILED"}
# omits: object_name

# ERROR — ambiguous name:
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "LOOKUP_ANIMATION_OBJECT",
 "note": "AMBIGUOUS_ANIMATION_OBJECT_NAME"}
```

#### animation_data

```python
# PASS:
{"result": "PASS", "animation_data_present": True}

# FAIL — animation_data is None:
{"result": "FAIL", "failure_code": "ANIMATION_DATA_NOT_PRESENT"}

# ERROR — AttributeError reading animation_data:
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "READ_ANIMATION_DATA", "note": "READ_ANIMATION_DATA_FAILED"}
# omits: animation_data_present
```

#### action_name

```python
# PASS:
{"result": "PASS", "action_name": "<name>"}

# FAIL — action is None or name mismatch:
{"result": "FAIL", "failure_code": "ACTION_NAME_MISMATCH"}

# ERROR — AttributeError reading animation_data.action:
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "READ_ACTION_REFERENCE", "note": "READ_ACTION_REFERENCE_FAILED"}
# omits: action_name

# ERROR — AttributeError reading action.name:
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "READ_ACTION_NAME", "note": "READ_ACTION_NAME_FAILED"}
```

#### pose_position

```python
# PASS:
{"result": "PASS", "pose_position": "<POSE or REST>"}

# FAIL — pose_position mismatch:
{"result": "FAIL", "failure_code": "POSE_POSITION_MISMATCH"}

# ERROR — AttributeError reading object.data:
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "READ_OBJECT_DATA", "note": "READ_OBJECT_DATA_FAILED"}

# ERROR — AttributeError reading data.pose_position:
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "READ_POSE_POSITION", "note": "READ_POSE_POSITION_FAILED"}
# omits: pose_position
```

#### current_frame

```python
# PASS — frame recorded (data-recording, no verdict):
{"result": "PASS", "current_frame": <int>}

# ERROR — AttributeError reading scene.frame_current:
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "READ_CURRENT_FRAME", "note": "READ_CURRENT_FRAME_FAILED"}
# omits: current_frame
```

### 6.5 Dependency and NOT_CHECKED Cascading

```text
If animation_object result is FAIL or ERROR:
  animation_data sub-result  → NOT_CHECKED: "ANIMATION_OBJECT_NOT_FOUND"
  action_name sub-result     → NOT_CHECKED: "ANIMATION_OBJECT_NOT_FOUND"
  pose_position sub-result   → NOT_CHECKED: "ANIMATION_OBJECT_NOT_FOUND"
  current_frame is INDEPENDENT — reads scene, not object; executes normally

If animation_object is PASS but animation_data sub-result is FAIL or ERROR:
  action_name sub-result → NOT_CHECKED: "ANIMATION_DATA_NOT_AVAILABLE"
  (action_name depends on animation_data being readable)

pose_position does NOT depend on animation_data — it reads object.data.
current_frame does NOT depend on any other sub-check.
```

NOT_CHECKED sub-result format:
```python
{"result": "NOT_CHECKED", "note": "<reason>"}
```

### 6.6 Top-Level Aggregation

```text
checks.animation_state.result is the WORST of all present sub-results:
  ERROR > FAIL > PASS > NOT_CHECKED

Examples:
  animation_object=PASS, animation_data=FAIL, action_name=NOT_CHECKED,
  pose_position=PASS, current_frame=PASS
  → top-level result = FAIL

  animation_object=ERROR, current_frame=PASS
  → top-level result = ERROR

  All sub-results PASS or NOT_CHECKED
  → top-level result = PASS

NOT_CHECKED top-level occurs only when animation_state is missing or null.
```

### 6.7 Simultaneous FAIL + ERROR

```text
animation_object=FAIL, animation_data=ERROR:
  Top-level = ERROR (ERROR > FAIL).
  Both sub-results present with their individual result dicts.
  animation_data ERROR omits animation_data_present per its ERROR contract.
```

## 7. FAIL/ERROR Boundary

### 7.1 Unified Rule

```text
AttributeError (property does not exist on object, or access raises) → ERROR
Property exists, value is None when non-None is required → FAIL
Property exists, value does not match expected → FAIL
```

This rule applies consistently to all sub-checks.

### 7.2 Normal/None/Exception Table

| Read Target | Normal (PASS) | None (FAIL) | AttributeError (ERROR) |
|---|---|---|---|
| `scene.objects` iteration | objects iterated, match found/not found | N/A — iterable | `LOOKUP_ANIMATION_OBJECT_FAILED` |
| `obj.animation_data` | non-None | `ANIMATION_DATA_NOT_PRESENT` | `READ_ANIMATION_DATA_FAILED` |
| `animation_data.action` | non-None | `ACTION_NAME_MISMATCH` | `READ_ACTION_REFERENCE_FAILED` |
| `action.name` | string, compared | N/A — action has .name if action exists | `READ_ACTION_NAME_FAILED` |
| `obj.data` | non-None | N/A — Armature always has .data if Armature | `READ_OBJECT_DATA_FAILED` |
| `data.pose_position` | "POSE" or "REST" | N/A — pose_position exists if data exists | `READ_POSE_POSITION_FAILED` |
| `scene.frame_current` | int | N/A — frame_current exists if scene exists | `READ_CURRENT_FRAME_FAILED` |

### 7.3 Exception Handling

```text
All Blender property reads wrapped in try/except Exception.
Any exception → ERROR with the corresponding operation.
Pattern: same as Rotation Design R3 (EXISTING_PROJECT_CONVENTION).

Implementation uses except Exception (not bare except) to avoid
catching KeyboardInterrupt/SystemExit.
```

## 8. Read Counts

### 8.1 Runtime Read Counts (max per invocation)

| Read | Max | Condition |
|---|---|---|
| `scene.objects` iteration | 1 | animation_state configured |
| `obj.name` (per object during iteration) | N per scene | object lookup |
| `obj.animation_data` | 1 | require_animation_data=true OR expected_action_name set |
| `animation_data.action` | 1 | expected_action_name set |
| `action.name` | 1 | expected_action_name set |
| `obj.data` | 1 | expected_pose_position set |
| `data.pose_position` | 1 | expected_pose_position set |
| `scene.frame_current` | 1 | record_current_frame=true |

### 8.2 AST vs Runtime Counts

```text
AST Load count (scope guard): counts source-code attribute access nodes
  within the check function and its reachable helpers. Used to verify
  that the source does not contain forbidden reads.

Runtime read count: counts actual Blender property accesses at execution
  time. Must not exceed the max in §8.1. Cache strategy ensures each
  property is read at most once.

obj.name during scene.objects iteration: N runtime reads (one per object
  iterated). Scope guard cannot limit this count — it verifies that
  obj.name access occurs only within the iteration construct and is
  used only for case-sensitive string comparison, not stored or
  propagated for other purposes.

NEW_DESIGN_DECISION: scope guard AST analysis permits obj.name reads
within the animation object lookup loop. All other scope guard
attribute counts map 1:1 to runtime counts.
```

## 9. Scope Guard Contract

### 9.1 Entry Function

```text
Entry: _check_animation_state(scene, target)
  Defined in: blender_scene_reader.py
  Scope guard analyzes this function and all reachable helpers.
```

### 9.2 Allowed Reads (AST-verified)

```text
ALLOWED_ATTRIBUTES:
  scene.objects          — (iterable, for object lookup)
  obj.name               — (str, for case-sensitive comparison; loop-local only)
  obj.animation_data     — (conditional on field config)
  animation_data.action  — (conditional on expected_action_name set)
  action.name            — (conditional on expected_action_name set)
  obj.data               — (conditional on expected_pose_position set)
  data.pose_position     — (conditional on expected_pose_position set)
  scene.frame_current    — (conditional on record_current_frame=true)
```

### 9.3 Forbidden Reads (AST-verified)

```text
FORBIDDEN_ATTRIBUTES:
  matrix_world, matrix_local, matrix_basis, matrix_parent_inverse
  rotation_euler, rotation_quaternion, rotation_mode
  location, scale, dimensions
  parent, children
  hide_viewport, hide_render, hide_get
  material_slots
  bound_box
  evaluated_get, evaluated_depsgraph_get, to_mesh, to_mesh_clear
  users_collection
  world_to_camera_view
  nla_tracks
  bpy.data.collections
  bpy.context.scene  (use passed scene parameter)
  bpy.data.objects.get, bpy.data.objects[   (use scene.objects iteration)
```

### 9.4 Forbidden Calls

```text
FORBIDDEN_CALLS:
  bpy.ops.wm.open_mainfile
  bpy.ops.wm.save_as_mainfile, bpy.ops.wm.save_mainfile
  bpy.ops.render.render
  Any bpy.ops.* operator
```

### 9.5 Write Detection

```text
MUST_NOT_WRITE:
  Any attribute assignment on Blender objects (obj, scene, data, action)
  Any scene property modification
  Any .blend file modification

AST-verified: zero attribute Store/Delete nodes on Blender objects.
```

### 9.6 Helper and Alias Rules

```text
Reachable helpers: any function called (directly or transitively) from
  _check_animation_state. Local functions, lambdas, and helper functions
  defined in reader.py are included.

Alias tracking:
  Variable aliases (e.g., anim_data = obj.animation_data) are tracked.
  Reads through aliases count toward the same attribute's limit.
  Method aliases are tracked (same pattern as Rotation I4A).

Shallow walking:
  FunctionDef and ClassDef bodies NOT in the reachable call graph are
  skipped (they represent other check functions, not helpers of
  animation_state).
```

### 9.7 Scope Guard Summary

```text
ENTRY: _check_animation_state(scene, target)
ALLOWED_READS: 8 attributes
FORBIDDEN_READS: 19 attributes
FORBIDDEN_CALLS: all bpy.ops.*
WRITE_DETECTION: zero Blender object attribute writes
HELPER_BOUNDARY: reachable call graph from entry
ALIAS_TRACKING: variable and method aliases
AST_vs_RUNTIME: obj.name counted at loop level; others 1:1

Pattern: Rotation I4A scope guard (EXISTING_PROJECT_CONVENTION).
```

## 10. _collect_target_errors Integration

```text
When checks.animation_state.result == "ERROR":
  _collect_target_errors() collects the error message in the same order
  as other field groups.

Error message format (same as Rotation, Standing):
  "ANIMATION_STATE_ERROR: target '<target_id>' animation_state <operation>"

For multiple ERROR sub-results within animation_state:
  One error message per ERROR sub-result.
  Messages ordered by sub-check key: animation_object, animation_data,
  action_name, pose_position, current_frame.
  Within each sub-check, one message (the sub-check's ERROR is singular).

Position in _collect_target_errors output:
  After Rotation errors, before any subsequent field group errors.
  Internal order: hierarchy → standing → facing → rotation → animation_state.

Pattern: same as existing _collect_target_errors for Standing/Rotation
(EXISTING_PROJECT_CONVENTION).
```

## 11. Complete FAIL/ERROR Mapping

### 11.1 FAIL Codes

| Trigger | failure_code | Sub-key |
|---|---|---|
| animation_object_name not in scene | `ANIMATION_OBJECT_NOT_FOUND` | `animation_object` |
| animation_data is None (require_animation_data=true) | `ANIMATION_DATA_NOT_PRESENT` | `animation_data` |
| action is None (expected_action_name set) | `ACTION_NAME_MISMATCH` | `action_name` |
| action.name != expected_action_name | `ACTION_NAME_MISMATCH` | `action_name` |
| pose_position != expected_pose_position | `POSE_POSITION_MISMATCH` | `pose_position` |

### 11.2 ERROR Operations

| Trigger | error_type | operation | note | Sub-key |
|---|---|---|---|---|
| scene.objects iteration raises | `ANIMATION_STATE_COMPUTATION_ERROR` | `LOOKUP_ANIMATION_OBJECT` | `LOOKUP_ANIMATION_OBJECT_FAILED` | `animation_object` |
| Multiple objects with same name | `ANIMATION_STATE_COMPUTATION_ERROR` | `LOOKUP_ANIMATION_OBJECT` | `AMBIGUOUS_ANIMATION_OBJECT_NAME` | `animation_object` |
| obj.animation_data AttributeError | `ANIMATION_STATE_COMPUTATION_ERROR` | `READ_ANIMATION_DATA` | `READ_ANIMATION_DATA_FAILED` | `animation_data` |
| animation_data.action AttributeError | `ANIMATION_STATE_COMPUTATION_ERROR` | `READ_ACTION_REFERENCE` | `READ_ACTION_REFERENCE_FAILED` | `action_name` |
| action.name AttributeError | `ANIMATION_STATE_COMPUTATION_ERROR` | `READ_ACTION_NAME` | `READ_ACTION_NAME_FAILED` | `action_name` |
| obj.data AttributeError | `ANIMATION_STATE_COMPUTATION_ERROR` | `READ_OBJECT_DATA` | `READ_OBJECT_DATA_FAILED` | `pose_position` |
| data.pose_position AttributeError | `ANIMATION_STATE_COMPUTATION_ERROR` | `READ_POSE_POSITION` | `READ_POSE_POSITION_FAILED` | `pose_position` |
| scene.frame_current AttributeError | `ANIMATION_STATE_COMPUTATION_ERROR` | `READ_CURRENT_FRAME` | `READ_CURRENT_FRAME_FAILED` | `current_frame` |

FAIL codes: 3 unique (two sub-checks share `ACTION_NAME_MISMATCH`).
ERROR operations: 8 (7 unique operations + AMBIGUOUS_ANIMATION_OBJECT_NAME variant).

All ERROR use unified error_type `ANIMATION_STATE_COMPUTATION_ERROR`.
Pattern: Rotation Design R3 §3 (EXISTING_PROJECT_CONVENTION).

## 12. Design Completeness Matrix

```text
[x] animation_object: found PASS, not-found FAIL, ambiguous ERROR, lookup ERROR
[x] animation_data: true/false/null/missing, None→FAIL, AttributeError→ERROR
[x] action_name: set/null/missing, action=None→FAIL, name mismatch→FAIL,
    animation_data.action AttributeError→ERROR, action.name AttributeError→ERROR
[x] pose_position: set/null/missing, mismatch→FAIL, obj.data AttributeError→ERROR,
    data.pose_position AttributeError→ERROR
[x] current_frame: true/false/null/missing, frame recorded→PASS,
    scene.frame_current AttributeError→ERROR, data-recording no FAIL
[x] NOT_CHECKED: animation_state missing/null (top-level), dependency cascade
[x] Sub-check NOT_CHECKED: animation_object FAIL/ERROR cascades to
    animation_data/action_name/pose_position; current_frame independent
[x] Multiple FAIL simultaneous: each sub-check has own result dict
[x] FAIL + ERROR simultaneous: top-level=ERROR, both sub-results present
[x] Multiple ERROR simultaneous: each sub-check has own ERROR dict
[x] Top-level aggregation: ERROR>FAIL>PASS>NOT_CHECKED with explicit examples
[x] Root independence: all 5 root outcomes defined; Animation State executes
    independently; takes scene+target, not root_obj
[x] Scene source: scene.objects + scene.frame_current from parameter only
[x] ACCESS_SCENE_REFERENCE removed
[x] FAIL/ERROR boundary: AttributeError→ERROR; None→FAIL; consistent table
[x] All read exceptions mapped: 8 operations covering all attribute accesses
[x] Read counts: 7 runtime properties, obj.name loop-local
[x] AST vs runtime counts: separated with obj.name exception documented
[x] Scope guard: entry function, allowed 8, forbidden 19, forbidden calls,
    write detection, helper/alias rules, shallow walking
[x] _collect_target_errors: message format, order, position defined
[x] LOCKED_SCHEMA preserved: POSE/REST exclusive, type/null validation
[x] No Armature type constraint
[x] No NLA expansion
[x] Action Quality Disclaimer preserved
[x] CONTRACT_CONFLICTS: 0
```

## 13. Scope Compliance

```text
DESIGN_READY_FOR_INDEPENDENT_REVIEW: TRUE
DESIGN_APPROVED: FALSE
DESIGN_LOCKED: FALSE
IMPLEMENTATION_AUTHORIZED: FALSE
PRODUCTION_CODE_MODIFIED: FALSE
TESTS_MODIFIED: FALSE
TESTS_RUN: FALSE
BLENDER_EXECUTED: FALSE
BLEND_FILES_OPENED: FALSE
MASTER_MAP_MODIFIED: FALSE
```

## 14. Deliverable

```text
UPLOAD_NEXT_FILE: reviews/UPLOAD_NEXT/ANIMATION_STATE_DESIGN_R2_CORRECTION/ANIMATION_STATE_DESIGN_R2_CORRECTION_UPLOAD.zip
```
