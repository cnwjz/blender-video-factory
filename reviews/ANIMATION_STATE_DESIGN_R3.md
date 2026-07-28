# Animation State Design R3

```text
TASK_ID: ANIMATION_STATE_DESIGN_R3_CORRECTION
TASK_TYPE: DESIGN_CORRECTION
DATE: 2026-07-22
DESIGN_VERSION: R3
DESIGN_STATUS: READY_FOR_INDEPENDENT_REVIEW
IMPLEMENTATION_AUTHORIZED: FALSE
SUPERSEDES: ANIMATION_STATE_DESIGN_R2.md
```

## R3 Correction Summary

```text
F-001: Dependency model fixed. Impossible combinations removed.
       Three distinct NOT_CHECKED reasons: ANIMATION_OBJECT_NOT_FOUND,
       ANIMATION_OBJECT_UNAVAILABLE, ANIMATION_DATA_NOT_AVAILABLE.

F-002: Exact integration location: open_blend_and_get_scene() after
       _check_root_objects(). Per-target merge. Root × Animation State
       overall matrix defined. Code structure mapped to production.

F-003: Scene=None behavior: per_target_results empty (existing behavior).
       Animation State not reached when scene is None.

F-004: None/Exception matrix: all 7 attribute accesses with normal/None/
       Exception columns. "Armature always has .data" removed.
       Consistent: except Exception → ERROR; None when required → FAIL.

F-005: _collect_target_errors: complete 6-group order. Animation State
       ERROR messages distinguishable (object not found vs ambiguous vs lookup).

F-006 (new): Scope guard: 7 categories listed separately. Counts match.
       bpy.data.objects.get added to FORBIDDEN_CALLS.
       bpy.data.objects[...] added to FORBIDDEN_SUBSCRIPTS.
       ALLOWED_BLENDER_CALLS: NONE declared.
       Python builtins: allowed for string comparison, dict access, iteration.

D-001: Implementation file boundaries, test split, and Blender requirements restored.
```

## 1. Design Basis (unchanged)

| Source | Role |
|---|---|
| `ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md` §9 | AUTHORITATIVE_REQUIREMENT |
| `asset_scene_preflight_core.py` lines 370-387 | LOCKED_SCHEMA |
| `ROTATION_DESIGN_R3.md` | EXISTING_PROJECT_CONVENTION |
| `14B_4A_VISIBILITY_DESIGN_R2.md` | EXISTING_PROJECT_CONVENTION |
| `ANIMATION_STATE_ORIGINAL_REQUIREMENT_AUDIT_REPORT.md` (R3) | AUDIT |

## 2. Fields (unchanged)

| # | Field | Type (LOCKED_SCHEMA) | Required |
|---|---|---|---|
| 1 | `animation_state.animation_object_name` | non-empty string | Yes, if block present |
| 2 | `animation_state.require_animation_data` | boolean or null | No |
| 3 | `animation_state.expected_action_name` | non-empty string or null | No |
| 4 | `animation_state.expected_pose_position` | "POSE", "REST", or null | No |
| 5 | `animation_state.record_current_frame` | boolean or null | No |

## 3. Configuration Semantics (unchanged)

```text
animation_state missing → NOT_CHECKED
animation_state: null  → NOT_CHECKED
animation_state: {}    → pre-open ERROR (LOCKED_SCHEMA)

Each nullable field: null or missing → check skipped, sub-key omitted.
record_current_frame: false → not read, sub-key omitted.
```

## 4. Integration: Exact Production Location

### 4.1 Current Production Structure

```text
reader.py :: open_blend_and_get_scene(absolute_blend_path, scene_name, ...)
  → Opens .blend, resolves scene
  → Builds scene_basic result
  → Calls _check_root_objects(scene, targets) → per_target_results
     (line 1407)
  → Returns {"scene_basic": ..., "per_target_results": ...}
  → check.py :: _collect_target_errors(per_target_results)
     (called after reader returns, for ERROR collection)

_check_root_objects(scene, targets) — line 1093:
  scene is None → returns [] immediately (line 1107)
  For each target, iterates scene.objects, matches root_name
  On root PASS (unique+type): calls standing, facing, visibility, rotation
    (lines 1239-1246)
```

### 4.2 Animation State Integration

```text
NEW_DESIGN_DECISION: Option A — Post-root merge.

In open_blend_and_get_scene(), AFTER _check_root_objects() returns:

  per_target_results = _check_root_objects(scene, targets)

  # Animation State: independent of root object
  for i, target in enumerate(targets):
      if _has_animation_state(target):
          as_result = _check_animation_state(scene, target)
          # Merge into existing per_target_results[i]["checks"]
          if i < len(per_target_results):
              per_target_results[i]["checks"]["animation_state"] = as_result
              # Recompute overall
              per_target_results[i]["overall"] = _recompute_overall(
                  per_target_results[i]["checks"])

Call order within open_blend_and_get_scene():
  1. scene_basic
  2. _check_root_objects (hierarchy + standing + facing + visibility + rotation)
  3. _check_animation_state per target (merge + recompute overall)
  4. Return {"scene_basic": ..., "per_target_results": ...}

FILES MODIFIED:
  - blender_scene_reader.py: add _check_animation_state(), add merge loop
  - asset_scene_preflight_check.py: add _collect_target_errors animation_state case

FILES NOT MODIFIED:
  - asset_scene_preflight_core.py (LOCKED 14A Core)
  - Existing test files (LOCKED)
```

### 4.3 Scene is None

```text
When scene is None:
  _check_root_objects returns [] (existing behavior, reader.py line 1107).
  Animation State loop iterates over targets but scene is None →
  _check_animation_state(None, target) returns:
    {"result": "NOT_CHECKED", "note": "SCENE_NOT_AVAILABLE"}
  This result is NOT merged into per_target_results (list is empty).
  check.py receives empty per_target_results → no ERROR collection.

Consistent with existing scene_basic result which reports
scene_exists: false when scene is None.
```

### 4.4 Root × Animation State Overall Matrix

For each target where animation_state is configured:

| Root Outcome | Animation State | Overall | Rule |
|---|---|---|---|
| PASS | PASS | PASS | — |
| PASS | FAIL | FAIL | FAIL > PASS |
| PASS | ERROR | ERROR | ERROR > all |
| ROOT_OBJECT_NOT_FOUND | PASS | FAIL | Root FAIL dominates |
| ROOT_OBJECT_NOT_FOUND | FAIL | FAIL | Both FAIL |
| ROOT_OBJECT_NOT_FOUND | ERROR | ERROR | ERROR > FAIL |
| ROOT_OBJECT_TYPE_MISMATCH | PASS | FAIL | Root FAIL dominates |
| ROOT_OBJECT_TYPE_MISMATCH | FAIL | FAIL | Both FAIL |
| ROOT_OBJECT_TYPE_MISMATCH | ERROR | ERROR | ERROR > FAIL |
| AMBIGUOUS_ROOT_OBJECT_NAME | any | ERROR | Root ERROR dominates |
| Root lookup ERROR | any | ERROR | Root ERROR dominates |

Rule: `_recompute_overall(checks)` scans all `checks.*.result` values.
ERROR if any ERROR; else FAIL if any FAIL; else PASS.
Same algorithm as existing reader.py lines 1248-1260.

Root NOT_CHECKED results (e.g., standing when root not found) do NOT
affect overall — they are NOT_CHECKED, not FAIL.

## 5. Sub-Check Result Model (Corrected)

### 5.1 Dependency Rules

```text
animation_object lookup produces the object reference.

If animation_object result is PASS → obj reference is valid.
  → animation_data, action_name, pose_position sub-checks execute.

If animation_object result is FAIL (not found) →
  → dependency reason: "ANIMATION_OBJECT_NOT_FOUND"
  → animation_data, action_name, pose_position → NOT_CHECKED
  → current_frame → executes independently (reads scene)

If animation_object result is ERROR (ambiguous or lookup error) →
  → dependency reason: "ANIMATION_OBJECT_UNAVAILABLE"
  → animation_data, action_name, pose_position → NOT_CHECKED
  → current_frame → executes independently

If animation_object is PASS but animation_data sub-result is FAIL or ERROR →
  → dependency reason: "ANIMATION_DATA_NOT_AVAILABLE"
  → action_name → NOT_CHECKED
  → pose_position → executes independently (reads obj.data, not animation_data)
  → current_frame → executes independently

pose_position and current_frame have NO dependencies beyond animation_object.
record_current_frame reads scene, not object — fully independent.
```

### 5.2 Valid Sub-Check Combinations

```text
VALID (animation_object=PASS):
  anim_obj=PASS, anim_data=PASS, action_name=PASS, pose=PASS, frame=PASS
  anim_obj=PASS, anim_data=FAIL, action_name=N/C, pose=PASS, frame=PASS
  anim_obj=PASS, anim_data=PASS, action_name=FAIL, pose=PASS, frame=ERROR
  anim_obj=PASS, anim_data=ERROR, action_name=N/C, pose=FAIL, frame=PASS

VALID (animation_object=FAIL):
  anim_obj=FAIL, anim_data=N/C(NOT_FOUND), action_name=N/C(NOT_FOUND),
  pose=N/C(NOT_FOUND), frame=PASS

VALID (animation_object=ERROR):
  anim_obj=ERROR, anim_data=N/C(UNAVAILABLE), action_name=N/C(UNAVAILABLE),
  pose=N/C(UNAVAILABLE), frame=ERROR

INVALID (removed from R2):
  anim_obj=FAIL + anim_data=ERROR — impossible: anim_data
  does not execute when anim_obj fails
```

### 5.3 NOT_CHECKED Reasons

```text
"ANIMATION_STATE_NOT_CONFIGURED" — animation_state missing or null (top-level)
"ANIMATION_OBJECT_NOT_FOUND"     — object not in scene (anim_data/action_name/pose_position)
"ANIMATION_OBJECT_UNAVAILABLE"   — ambiguous or lookup error (anim_data/action_name/pose_position)
"ANIMATION_DATA_NOT_AVAILABLE"   — animation_data check failed/errored (action_name only)
"SCENE_NOT_AVAILABLE"            — scene is None (top-level, not merged)
```

## 6. Result Structures

Nested path: `checks.animation_state`.

### 6.1 Top-Level (animation_state missing or null)

```python
{"result": "NOT_CHECKED", "note": "ANIMATION_STATE_NOT_CONFIGURED"}
```

### 6.2 Sub-Check Result Dicts

#### animation_object

```python
# PASS:
{"result": "PASS", "object_name": "<name>"}

# FAIL:
{"result": "FAIL", "failure_code": "ANIMATION_OBJECT_NOT_FOUND",
 "object_name": "<name from spec>"}

# ERROR (lookup exception):
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "LOOKUP_ANIMATION_OBJECT",
 "note": "LOOKUP_ANIMATION_OBJECT_FAILED"}

# ERROR (ambiguous):
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "LOOKUP_ANIMATION_OBJECT",
 "note": "AMBIGUOUS_ANIMATION_OBJECT_NAME"}
```

#### animation_data

```python
# PASS:
{"result": "PASS", "animation_data_present": True}

# FAIL:
{"result": "FAIL", "failure_code": "ANIMATION_DATA_NOT_PRESENT"}

# ERROR:
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "READ_ANIMATION_DATA", "note": "READ_ANIMATION_DATA_FAILED"}

# NOT_CHECKED:
{"result": "NOT_CHECKED", "note": "ANIMATION_OBJECT_NOT_FOUND"}
# or
{"result": "NOT_CHECKED", "note": "ANIMATION_OBJECT_UNAVAILABLE"}
```

#### action_name

```python
# PASS:
{"result": "PASS", "action_name": "<name>"}

# FAIL (action is None):
{"result": "FAIL", "failure_code": "ACTION_NAME_MISMATCH"}

# FAIL (name mismatch):
{"result": "FAIL", "failure_code": "ACTION_NAME_MISMATCH"}

# ERROR (animation_data.action AttributeError):
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "READ_ACTION_REFERENCE", "note": "READ_ACTION_REFERENCE_FAILED"}

# ERROR (action.name AttributeError):
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "READ_ACTION_NAME", "note": "READ_ACTION_NAME_FAILED"}

# NOT_CHECKED:
{"result": "NOT_CHECKED", "note": "ANIMATION_OBJECT_NOT_FOUND"}
# or
{"result": "NOT_CHECKED", "note": "ANIMATION_OBJECT_UNAVAILABLE"}
# or
{"result": "NOT_CHECKED", "note": "ANIMATION_DATA_NOT_AVAILABLE"}
```

#### pose_position

```python
# PASS:
{"result": "PASS", "pose_position": "<POSE or REST>"}

# FAIL:
{"result": "FAIL", "failure_code": "POSE_POSITION_MISMATCH"}

# ERROR (obj.data AttributeError):
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "READ_OBJECT_DATA", "note": "READ_OBJECT_DATA_FAILED"}

# ERROR (data.pose_position AttributeError):
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "READ_POSE_POSITION", "note": "READ_POSE_POSITION_FAILED"}

# NOT_CHECKED:
{"result": "NOT_CHECKED", "note": "ANIMATION_OBJECT_NOT_FOUND"}
# or
{"result": "NOT_CHECKED", "note": "ANIMATION_OBJECT_UNAVAILABLE"}
```

#### current_frame

```python
# PASS (data recorded):
{"result": "PASS", "current_frame": <int>}

# ERROR:
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "READ_CURRENT_FRAME", "note": "READ_CURRENT_FRAME_FAILED"}

# No NOT_CHECKED for dependency — current_frame is fully independent
```

### 6.3 Top-Level Aggregation

```text
Top-level checks.animation_state.result:
  ERROR > FAIL > PASS > NOT_CHECKED
  (All sub-check results present; worst determines top-level)

When animation_state missing/null → top-level NOT_CHECKED (no sub-keys).
```

## 7. Object Lookup

```text
Method: iterate scene.objects, case-sensitive exact name match (obj.name == name).
Scene membership: implicit (scene.objects only contains scene members).
Type constraint: NONE. No Armature requirement.
bpy.data.objects.get: NOT used (does not check scene membership).
bpy.data.objects[...]: NOT used.
```

## 8. FAIL/ERROR Boundary — Complete Matrix

### 8.1 Unified Rule

```text
except Exception caught during attribute access → ERROR
Attribute accessed successfully, value is None when non-None required → FAIL
Attribute accessed successfully, value does not match expected → FAIL
AttributeError (property missing) → caught by except Exception → ERROR
```

All Blender property accesses wrapped in `try: ... except Exception: ...`.
Same pattern as reader.py line 1121-1122 (EXISTING_PROJECT_CONVENTION).

### 8.2 Complete Normal/None/Exception Table

| # | Read Target | Normal | None | Exception | ERROR operation |
|---|---|---|---|---|---|
| 1 | `scene.objects` iteration | success | N/A | Exception | `LOOKUP_ANIMATION_OBJECT` |
| 2 | `obj.name` (during iteration) | string | N/A | N/A (built-in) | — |
| 3 | `obj.animation_data` | non-None → PASS; None → FAIL | FAIL | Exception | `READ_ANIMATION_DATA` |
| 4 | `animation_data.action` | non-None → compare; None → FAIL | FAIL | Exception | `READ_ACTION_REFERENCE` |
| 5 | `action.name` | string → compare | N/A | Exception | `READ_ACTION_NAME` |
| 6 | `obj.data` | non-None → continue; None → N/A | N/A | Exception | `READ_OBJECT_DATA` |
| 7 | `data.pose_position` | "POSE"/"REST" → compare; other → FAIL | N/A | Exception | `READ_POSE_POSITION` |
| 8 | `scene.frame_current` | int → record | int (None is valid int? no — scene always has frame_current) | Exception | `READ_CURRENT_FRAME` |

### 8.3 Edge Cases

```text
expected_action_name set, require_animation_data NOT set, obj.animation_data is None:
  animation_data sub-check: not executed (require_animation_data not set)
  action_name sub-check: reads obj.animation_data → None → reads animation_data.action
    → animation_data is None, has no .action → except Exception
    → ERROR, operation: READ_ACTION_REFERENCE, note: READ_ACTION_REFERENCE_FAILED
  RULE: action_name check accesses animation_data.action directly.
  If animation_data is None, the .action access raises AttributeError → ERROR.

obj.data is None:
  obj.data → None → reads data.pose_position
    → None has no .pose_position → except Exception
    → ERROR, operation: READ_POSE_POSITION, note: READ_POSE_POSITION_FAILED

action.name is None:
  action.name → None → compared to expected_action_name
    → None != string → FAIL, failure_code: ACTION_NAME_MISMATCH

data.pose_position is None:
  data.pose_position → None → compared to expected_pose_position
    → None not in ("POSE", "REST") → FAIL, failure_code: POSE_POSITION_MISMATCH

scene.frame_current is None:
  scene always has frame_current (int). Not expected to be None.
  If somehow None → PASS, current_frame: None recorded.
```

Note: "Armature always has .data" removed (R3). Non-Armature objects will
trigger except Exception at the obj.data access → ERROR per unified rule.

## 9. FAIL Codes and ERROR Operations

### 9.1 FAIL Codes (4 unique)

| # | failure_code | Sub-key | Trigger |
|---|---|---|---|
| 1 | `ANIMATION_OBJECT_NOT_FOUND` | `animation_object` | object name not in scene |
| 2 | `ANIMATION_DATA_NOT_PRESENT` | `animation_data` | animation_data is None |
| 3 | `ACTION_NAME_MISMATCH` | `action_name` | action is None or name != expected |
| 4 | `POSE_POSITION_MISMATCH` | `pose_position` | pose_position != expected |

### 9.2 ERROR Cases (8)

| # | operation | note | Sub-key | Trigger |
|---|---|---|---|---|
| 1 | `LOOKUP_ANIMATION_OBJECT` | `LOOKUP_ANIMATION_OBJECT_FAILED` | `animation_object` | scene.objects iteration raises |
| 2 | `LOOKUP_ANIMATION_OBJECT` | `AMBIGUOUS_ANIMATION_OBJECT_NAME` | `animation_object` | multiple objects with same name |
| 3 | `READ_ANIMATION_DATA` | `READ_ANIMATION_DATA_FAILED` | `animation_data` | obj.animation_data raises |
| 4 | `READ_ACTION_REFERENCE` | `READ_ACTION_REFERENCE_FAILED` | `action_name` | animation_data.action raises |
| 5 | `READ_ACTION_NAME` | `READ_ACTION_NAME_FAILED` | `action_name` | action.name raises |
| 6 | `READ_OBJECT_DATA` | `READ_OBJECT_DATA_FAILED` | `pose_position` | obj.data raises |
| 7 | `READ_POSE_POSITION` | `READ_POSE_POSITION_FAILED` | `pose_position` | data.pose_position raises |
| 8 | `READ_CURRENT_FRAME` | `READ_CURRENT_FRAME_FAILED` | `current_frame` | scene.frame_current raises |

Unique error_type: `ANIMATION_STATE_COMPUTATION_ERROR` (all 8 cases).
Unique operation values: 7 (`LOOKUP_ANIMATION_OBJECT` used twice with different notes).

## 10. _collect_target_errors

### 10.1 Complete Order

```text
Error collection order in check.py _collect_target_errors():
  1. hierarchy (object_exists: AMBIGUOUS_ROOT_OBJECT_NAME, DIRECT_CHILD_LOOKUP_ERROR)
  2. hierarchy (direct_children: AMBIGUOUS_DIRECT_CHILD_NAME, DIRECT_CHILD_LOOKUP_ERROR)
  3. hierarchy (descendants: AMBIGUOUS_DESCENDANT_NAME, DESCENDANT_LOOKUP_ERROR)
  4. standing (STANDING_UP_AXIS_ERROR)
  5. facing (FACING_FORWARD_AXIS_ERROR)
  6. visibility (VISIBILITY_READ_ERROR)
  7. rotation (ROTATION_COMPUTATION_ERROR)
  8. animation_state (ANIMATION_STATE_COMPUTATION_ERROR)  ← NEW
```

### 10.2 Animation State ERROR Messages

```text
When checks.animation_state.result == "ERROR":
  Collect one message per ERROR sub-result.
  Message format:
    "ANIMATION_STATE_COMPUTATION_ERROR: target '<tid>' animation_state
     sub_check '<sub_key>' operation '<operation>'"

  Sub-checks checked in order:
    animation_object, animation_data, action_name, pose_position, current_frame

  For each sub-check where result == "ERROR":
    err_msgs.append(
      f"ANIMATION_STATE_COMPUTATION_ERROR: target '{tid}' "
      f"animation_state sub_check '{sub_key}' operation '{operation}'"
    )

  AMBIGUOUS_ANIMATION_OBJECT_NAME is distinguishable from
  LOOKUP_ANIMATION_OBJECT_FAILED via the operation field in the message.

  Example messages:
    "ANIMATION_STATE_COMPUTATION_ERROR: target 'A' animation_state
     sub_check 'animation_object' operation 'LOOKUP_ANIMATION_OBJECT'"
    "ANIMATION_STATE_COMPUTATION_ERROR: target 'A' animation_state
     sub_check 'action_name' operation 'READ_ACTION_REFERENCE'"

  Number of messages: one per ERROR sub-check (max 5 if all sub-check ERROR).
  Ordered by sub-key as listed above.
```

## 11. Scope Guard — Complete Categories

### 11.1 ENTRY_FUNCTION

```text
_check_animation_state(scene, target)
  Defined in: blender_scene_reader.py
  Scope guard AST analyzes this function and all reachable helpers.
```

### 11.2 ALLOWED_ATTRIBUTES (8)

```text
1. scene.objects          — iteration for object lookup
2. obj.name               — case-sensitive comparison (loop-local only)
3. obj.animation_data     — conditional on config
4. animation_data.action  — conditional on expected_action_name set
5. action.name            — conditional on expected_action_name set
6. obj.data               — conditional on expected_pose_position set
7. data.pose_position     — conditional on expected_pose_position set
8. scene.frame_current    — conditional on record_current_frame=true
```

### 11.3 FORBIDDEN_ATTRIBUTES (18)

```text
1.  matrix_world          10. hide_viewport
2.  matrix_local          11. hide_render
3.  matrix_basis          12. hide_get
4.  matrix_parent_inverse 13. material_slots
5.  rotation_euler        14. bound_box
6.  rotation_quaternion   15. evaluated_get / evaluated_depsgraph_get
7.  rotation_mode         16. to_mesh / to_mesh_clear
8.  location              17. users_collection
9.  scale / dimensions    18. nla_tracks
```

### 11.4 ALLOWED_CALLS

```text
ALLOWED_BLENDER_CALLS: NONE
  No bpy.* module functions or Blender type methods are called directly.

ALLOWED_PYTHON_BUILTINS: YES (for control flow and data handling)
  - str comparison (==, !=)
  - dict.get(), list.append()
  - sorted(), len(), isinstance()
  - Exception handling (try/except)
  - Iteration (for x in y)
```

### 11.5 FORBIDDEN_CALLS (4)

```text
1. bpy.ops.wm.open_mainfile
2. bpy.ops.wm.save_as_mainfile
3. bpy.ops.wm.save_mainfile
4. bpy.data.objects.get("<name>")
```

### 11.6 FORBIDDEN_SUBSCRIPTS (1)

```text
1. bpy.data.objects["<name>"]
```

### 11.7 WRITE_DETECTION

```text
Zero AST Store/Delete nodes targeting Blender object attributes.
Zero assignment to: obj.*, scene.*, data.*, action.*, bpy.*.
```

### 11.8 REACHABLE_HELPER_RULES

```text
Reachable helpers: functions called from _check_animation_state
(directly or transitively). Includes local functions and lambdas.

Shallow walking: FunctionDef/ClassDef bodies not in the reachable
call graph are skipped (they represent other check functions).

Pattern: Rotation I4A scope guard (EXISTING_PROJECT_CONVENTION).
```

### 11.9 ALIAS_RULES

```text
Variable aliases tracked: anim_data = obj.animation_data → reads
through anim_data count toward animation_data limit.

Method aliases tracked: method = obj.animation_data; method() —
not applicable here (no method calls on Blender objects).

Pattern: Rotation I4A scope guard (EXISTING_PROJECT_CONVENTION).
```

### 11.10 AST vs Runtime Counts

```text
obj.name during scene.objects iteration: N runtime reads.
Scope guard AST limit: obj.name allowed only within the lookup loop,
for case-sensitive comparison only, not stored or propagated.

All other attributes: AST count = runtime count = 1.
```

## 12. Implementation Boundaries

### 12.1 Files to Modify

```text
ALLOWED:
  - blender_scene_reader.py: _check_animation_state() + merge loop
  - asset_scene_preflight_check.py: _collect_target_errors() animation_state case
  - protocol_guard/phase3_min/tests/: new test files
    (test_asset_scene_preflight_blender_animation_state_i*.py)

MUST NOT MODIFY:
  - asset_scene_preflight_core.py (LOCKED 14A Core)
  - All existing test files for other field groups (LOCKED)
  - All .blend files
```

### 12.2 Test Split

```text
I1:  Pre-open schema validation (core.py — already tested, 2 existing tests)
I2:  Configuration semantics (NOT_CHECKED, null, missing, false, empty string)
     CPython only — fake objects sufficient for configuration tests.
I3:  Animation object lookup (found, not found, ambiguous, lookup ERROR)
     Real Blender required for scene.objects iteration.
I4A: Runtime PASS/FAIL (all 4 verdict sub-checks)
     Real Blender required for animation_data, action, pose_position.
I4B: ERROR boundaries (all 8 ERROR operations)
     Real Blender required for AttributeError triggering.
I5:  Scope guard (AST enforcement, forbidden reads/calls/writes)
     CPython — analyzes source code, no Blender needed.
E:   Final regression (full protocol_guard + all prior field groups)
     Real Blender + CPython combined.

REAL_BLENDER_REQUIRED: TRUE
  Animation State must verify against real Blender objects because:
  - animation_data, action, action.name are Blender-specific attributes
  - data.pose_position is Armature-specific
  - scene.frame_current is a Blender scene property
  - scene.objects iteration behavior must match real Blender
  - except Exception behavior varies between fake mocks and real Blender

CPython fake-object tests sufficient for: configuration semantics (I2),
scope guard (I5), and pre-open validation (I1).
```

## 13. Design Completeness Matrix

```text
[x] 5 fields all covered
[x] Sub-check result model: 5 independent sub-keys
[x] Dependency cascade: 3 NOT_CHECKED reasons (NOT_FOUND, UNAVAILABLE, DATA_NOT_AVAILABLE)
[x] Invalid combinations removed (anim_obj=FAIL + anim_data=ERROR)
[x] Integration: open_blend_and_get_scene() after _check_root_objects()
[x] Root × Animation State overall matrix: all 5 root outcomes defined
[x] Scene=None: per_target_results empty; Animation State not merged
[x] Object lookup: scene.objects, case-sensitive, no type constraint
[x] Normal/None/Exception: complete 8-row table
[x] "Armature always has .data" removed
[x] except Exception consistent throughout
[x] FAIL codes: 4 unique
[x] ERROR cases: 8
[x] Unique error operations: 7
[x] _collect_target_errors: 8-group order, Animation State messages
[x] Scope guard: 6 categories listed, counts match entries
[x] ALLOWED_ATTRIBUTES: 8
[x] FORBIDDEN_ATTRIBUTES: 18
[x] FORBIDDEN_CALLS: 4
[x] FORBIDDEN_SUBSCRIPTS: 1
[x] ALLOWED_BLENDER_CALLS: NONE
[x] ALLOWED_PYTHON_BUILTINS: YES
[x] WRITE_DETECTION: defined
[x] Helper/alias/shallow walking rules: defined
[x] AST vs runtime counts: separated
[x] Implementation files: allowed (2) and forbidden listed
[x] Test split: I1-I5 + E with CPython/Blender requirements
[x] REAL_BLENDER_REQUIRED: TRUE with justification
[x] LOCKED_SCHEMA preserved
[x] CONTRACT_CONFLICTS: 0
```

## 14. Scope Compliance

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

## 15. Deliverable

```text
UPLOAD_NEXT_FILE: reviews/UPLOAD_NEXT/ANIMATION_STATE_DESIGN_R3_CORRECTION/ANIMATION_STATE_DESIGN_R3_CORRECTION_UPLOAD.zip
```
