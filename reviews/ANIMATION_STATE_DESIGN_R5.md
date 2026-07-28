# Animation State Design R5

```text
TASK_ID: ANIMATION_STATE_DESIGN_R5_CORRECTION
TASK_TYPE: DESIGN_CORRECTION
DATE: 2026-07-22
DESIGN_VERSION: R5
DESIGN_STATUS: READY_FOR_INDEPENDENT_REVIEW
IMPLEMENTATION_AUTHORIZED: FALSE
SUPERSEDES: ANIMATION_STATE_DESIGN_R4.md
```

## R5 Correction Summary

```text
F-002: Overall matrix replaced with pre-animation_overall × animation_state_result.
       _recompute_overall(checks) scans ALL check keys including animation_state.
       ERROR > FAIL > PASS enforced regardless of root outcome.
       ROOT_FAIL + ANIM_ERROR = ERROR (not FAIL). Contradiction removed.

F-003: Scene=None guard placed BEFORE the merge loop in pseudocode (§4.2).
       if scene is None: skip entire Animation State block.
       No call-and-discard. Pseudocode and prose now consistent.

F-004: action_name dependency contract unified. When require_animation_data is
       false/null but expected_action_name is set, action_name reads
       obj.animation_data independently. obj.animation_data=None → FAIL.
       obj.animation_data Exception → ERROR (operation: READ_ANIMATION_DATA,
       attributed to action_name sub-key). action.name=None → FAIL.

F-005B: Counts verified and corrected.
       9 unique ERROR operations. 21 FORBIDDEN_ATTRIBUTES. 8 ALLOWED_ATTRIBUTES.
       AST counts: 1 access point per attribute. Runtime counts: conditional
       (0 if not triggered, max 1 if triggered except obj.name: N).
       "Any bpy.ops.*" is one wildcard rule covering all operators.
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

| # | Field | Type (LOCKED_SCHEMA) |
|---|---|---|
| 1 | `animation_state.animation_object_name` | non-empty string |
| 2 | `animation_state.require_animation_data` | boolean or null |
| 3 | `animation_state.expected_action_name` | non-empty string or null |
| 4 | `animation_state.expected_pose_position` | "POSE", "REST", or null |
| 5 | `animation_state.record_current_frame` | boolean or null |

## 3. Sub-Key Existence — MODEL_A (unchanged)

```text
Sub-key present IFF its trigger field is configured with an activating value.

| Sub-key | Present when |
|---|---|
| animation_object | always (if animation_state block present and non-null) |
| animation_data | require_animation_data is true |
| action_name | expected_action_name is a non-null string |
| pose_position | expected_pose_position is a non-null string |
| current_frame | record_current_frame is true |

Block missing or null:
  checks.animation_state = {"result": "NOT_CHECKED",
                            "note": "ANIMATION_STATE_NOT_CONFIGURED"}
  No sub-keys. Participates in overall as NOT_CHECKED.

_has_animation_state(target):
  True when target.get("animation_state") is a non-null dict.
  False otherwise → block-level NOT_CHECKED result used.
```

## 4. Integration

### 4.1 Location

```text
In open_blend_and_get_scene(), after _check_root_objects() returns:

  per_target_results = _check_root_objects(scene, targets)

  # Animation State: independent per-target check (R5: scene guard first)
  if scene is not None:
      for i, target in enumerate(targets):
          if _has_animation_state(target):
              as_result = _check_animation_state(scene, target)
          else:
              as_result = {"result": "NOT_CHECKED",
                           "note": "ANIMATION_STATE_NOT_CONFIGURED"}
          if i < len(per_target_results):
              per_target_results[i]["checks"]["animation_state"] = as_result
              per_target_results[i]["overall"] = _recompute_overall(
                  per_target_results[i]["checks"])

  return {"scene_basic": checks, "per_target_results": per_target_results}
```

### 4.2 Scene is None

```text
scene is None:
  _check_root_objects returns [] (existing behavior, line 1107).
  if scene is not None: guard is FALSE.
  Animation State merge loop ENTIRELY SKIPPED.
  No _check_animation_state call. No result. No merge.
  check.py receives empty per_target_results → no ERROR collection.
```

### 4.3 Overall Computation

```text
_recompute_overall(checks):
  Scan checks.<key>.result for ALL keys present in checks:
    hierarchy keys (object_exists, direct_children, descendants)
    standing, facing, visibility, rotation
    animation_state  ← included in scan

  If any result == "ERROR" → return "ERROR"
  elif any result == "FAIL" → return "FAIL"
  else → return "PASS"

This correctly implements ERROR > FAIL > PASS regardless of which
check produced the ERROR or FAIL.
```

### 4.4 Pre-Animation × Animation State Overall Matrix

| Pre-Animation Overall | Animation State Result | Final Overall | Rule |
|---|---|---|---|
| ERROR | ERROR | ERROR | ERROR > all |
| ERROR | FAIL | ERROR | pre ERROR dominates |
| ERROR | PASS | ERROR | pre ERROR dominates |
| ERROR | NOT_CHECKED | ERROR | pre ERROR dominates |
| FAIL | ERROR | ERROR | anim ERROR > pre FAIL |
| FAIL | FAIL | FAIL | both FAIL |
| FAIL | PASS | FAIL | pre FAIL |
| FAIL | NOT_CHECKED | FAIL | pre FAIL |
| PASS | ERROR | ERROR | anim ERROR |
| PASS | FAIL | FAIL | anim FAIL |
| PASS | PASS | PASS | both PASS |
| PASS | NOT_CHECKED | PASS | NOT_CHECKED ignored |

This follows ERROR > FAIL > PASS strictly. Animation State ERROR
always produces overall ERROR, regardless of pre-animation state.

## 5. Result Structures (MODEL_A)

### 5.1 animation_object Sub-Key

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

# ERROR (ambiguous name):
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "RESOLVE_ANIMATION_OBJECT_NAME",
 "note": "AMBIGUOUS_ANIMATION_OBJECT_NAME"}

# ERROR (obj.name raises during iteration):
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "READ_ANIMATION_OBJECT_NAME",
 "note": "READ_ANIMATION_OBJECT_NAME_FAILED"}
```

### 5.2 animation_data Sub-Key

```text
Present only when require_animation_data is true.
```

```python
# PASS:
{"result": "PASS", "animation_data_present": True}

# FAIL:
{"result": "FAIL", "failure_code": "ANIMATION_DATA_NOT_PRESENT"}

# ERROR:
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "READ_ANIMATION_DATA", "note": "READ_ANIMATION_DATA_FAILED"}

# NOT_CHECKED (dependency — animation_object failed/errored):
{"result": "NOT_CHECKED", "note": "ANIMATION_OBJECT_NOT_FOUND"}
# or
{"result": "NOT_CHECKED", "note": "ANIMATION_OBJECT_UNAVAILABLE"}
```

### 5.3 action_name Sub-Key

```text
Present only when expected_action_name is a non-null string.
Independent of require_animation_data — reads obj.animation_data directly.

Two scenarios:
  A. require_animation_data is true:
       animation_data sub-key is present.
       obj.animation_data read is cached and shared.
       If animation_data sub-result is FAIL/ERROR → action_name = NOT_CHECKED.

  B. require_animation_data is false, null, or missing:
       animation_data sub-key is NOT present.
       action_name reads obj.animation_data independently.
       No caching from animation_data sub-key (it doesn't exist).
```

```python
# PASS:
{"result": "PASS", "action_name": "<name>"}

# FAIL (animation_data is None — can't have an action):
{"result": "FAIL", "failure_code": "ACTION_NAME_MISMATCH"}

# FAIL (action is None):
{"result": "FAIL", "failure_code": "ACTION_NAME_MISMATCH"}

# FAIL (action.name is None — None != expected string):
{"result": "FAIL", "failure_code": "ACTION_NAME_MISMATCH"}

# FAIL (name mismatch):
{"result": "FAIL", "failure_code": "ACTION_NAME_MISMATCH"}

# ERROR (Scenario A: animation_data sub-key read failed;
#         attributed to animation_data sub-key, action_name = N/C):
#  → see NOT_CHECKED below

# ERROR (Scenario B: obj.animation_data raises Exception;
#         attributed to action_name sub-key):
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "READ_ANIMATION_DATA", "note": "READ_ANIMATION_DATA_FAILED"}

# ERROR (animation_data.action raises Exception):
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "READ_ACTION_REFERENCE", "note": "READ_ACTION_REFERENCE_FAILED"}

# ERROR (action.name raises Exception):
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "READ_ACTION_NAME", "note": "READ_ACTION_NAME_FAILED"}

# NOT_CHECKED (dependency — animation_object failed/errored):
{"result": "NOT_CHECKED", "note": "ANIMATION_OBJECT_NOT_FOUND"}
# or
{"result": "NOT_CHECKED", "note": "ANIMATION_OBJECT_UNAVAILABLE"}

# NOT_CHECKED (Scenario A dependency — animation_data sub-check failed/errored):
{"result": "NOT_CHECKED", "note": "ANIMATION_DATA_NOT_AVAILABLE"}
```

### 5.4 pose_position Sub-Key (unchanged)

```python
# Present only when expected_pose_position is a non-null string.

# PASS:
{"result": "PASS", "pose_position": "<POSE or REST>"}

# FAIL:
{"result": "FAIL", "failure_code": "POSE_POSITION_MISMATCH"}

# ERROR:
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "READ_OBJECT_DATA", "note": "READ_OBJECT_DATA_FAILED"}

# ERROR:
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "READ_POSE_POSITION", "note": "READ_POSE_POSITION_FAILED"}

# NOT_CHECKED:
{"result": "NOT_CHECKED", "note": "ANIMATION_OBJECT_NOT_FOUND"}
# or
{"result": "NOT_CHECKED", "note": "ANIMATION_OBJECT_UNAVAILABLE"}
```

### 5.5 current_frame Sub-Key (unchanged)

```python
# Present only when record_current_frame is true.

# PASS:
{"result": "PASS", "current_frame": <int or None>}

# ERROR:
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "READ_CURRENT_FRAME", "note": "READ_CURRENT_FRAME_FAILED"}
```

### 5.6 Top-Level Aggregation (unchanged)

```text
Scan all PRESENT sub-key results.
ERROR if any present sub-key is ERROR.
FAIL if any present sub-key is FAIL.
PASS otherwise (all PASS or NOT_CHECKED, or no sub-keys present).
NOT_CHECKED at top-level only when animation_state block missing/null.
```

## 6. Dependency Rules (R5)

```text
animation_object → PASS → obj reference valid → dependent checks execute.

animation_object → FAIL (not found) →
  animation_data: NOT_CHECKED "ANIMATION_OBJECT_NOT_FOUND"
  action_name:    NOT_CHECKED "ANIMATION_OBJECT_NOT_FOUND"
  pose_position:  NOT_CHECKED "ANIMATION_OBJECT_NOT_FOUND"
  current_frame:  EXECUTES INDEPENDENTLY

animation_object → ERROR (ambiguous or lookup exception) →
  animation_data: NOT_CHECKED "ANIMATION_OBJECT_UNAVAILABLE"
  action_name:    NOT_CHECKED "ANIMATION_OBJECT_UNAVAILABLE"
  pose_position:  NOT_CHECKED "ANIMATION_OBJECT_UNAVAILABLE"
  current_frame:  EXECUTES INDEPENDENTLY

animation_object PASS + animation_data sub-key PRESENT (require_animation_data=true):
  animation_data FAIL or ERROR →
    action_name: NOT_CHECKED "ANIMATION_DATA_NOT_AVAILABLE"

animation_object PASS + animation_data sub-key NOT PRESENT
  (require_animation_data is false/null/missing):
  action_name reads obj.animation_data independently (§5.3 Scenario B).
  No animation_data sub-key to depend on.
  obj.animation_data read failure → ERROR attributed to action_name.
```

## 7. Object Lookup (unchanged)

```text
Method: iterate scene.objects, case-sensitive exact match by obj.name.
Scene membership: implicit (scene.objects).
Type constraint: NONE.
bpy.data.objects.get / bpy.data.objects[...]: NOT used.
```

## 8. FAIL/ERROR Boundary — Complete Matrix

### 8.1 Unified Rule

```text
None checked BEFORE dereference. No artificial exceptions from None.anything.
Attribute access raises Exception → ERROR.
Value is None when required → FAIL.
Value mismatch → FAIL.
Dependency not met → NOT_CHECKED.
```

### 8.2 Complete Matrix

| # | Read Target | Normal | None Behavior | Exception Behavior |
|---|---|---|---|---|
| 1 | scene.objects iteration | success | N/A | ERROR: LOOKUP_ANIMATION_OBJECT |
| 2 | obj.name (per object) | string | N/A | ERROR: READ_ANIMATION_OBJECT_NAME |
| 3 | obj.animation_data | non-None or None | None → Scenario A: FAIL (ANIMATION_DATA_NOT_PRESENT, if anim_data sub-key present); Scenario B: FAIL (ACTION_NAME_MISMATCH, if standalone action_name check). Never dereferenced. | ERROR: READ_ANIMATION_DATA |
| 4 | animation_data.action | non-None or None | None → FAIL (ACTION_NAME_MISMATCH). Only accessed after confirming animation_data is not None. | ERROR: READ_ACTION_REFERENCE |
| 5 | action.name | string or None | None → FAIL (ACTION_NAME_MISMATCH). Only accessed after confirming action is not None. | ERROR: READ_ACTION_NAME |
| 6 | obj.data | non-None or None | None → ERROR (READ_OBJECT_DATA_FAILED). No deref — pose_position unreadable. | ERROR: READ_OBJECT_DATA |
| 7 | data.pose_position | any or None | None → FAIL (POSE_POSITION_MISMATCH). Only accessed after confirming data is not None. | ERROR: READ_POSE_POSITION |
| 8 | scene.frame_current | int or None | None → PASS, current_frame: None | ERROR: READ_CURRENT_FRAME |

## 9. FAIL Codes and ERROR Operations

### 9.1 FAIL Codes (4 unique, unchanged)

| # | failure_code | Sub-key |
|---|---|---|
| 1 | `ANIMATION_OBJECT_NOT_FOUND` | animation_object |
| 2 | `ANIMATION_DATA_NOT_PRESENT` | animation_data |
| 3 | `ACTION_NAME_MISMATCH` | action_name |
| 4 | `POSE_POSITION_MISMATCH` | pose_position |

### 9.2 ERROR Operations (9 unique)

| # | operation | Sub-key | Trigger |
|---|---|---|---|
| 1 | `LOOKUP_ANIMATION_OBJECT` | animation_object | scene.objects iteration raises |
| 2 | `RESOLVE_ANIMATION_OBJECT_NAME` | animation_object | multiple objects with same name |
| 3 | `READ_ANIMATION_OBJECT_NAME` | animation_object | obj.name raises during iteration |
| 4 | `READ_ANIMATION_DATA` | animation_data or action_name | obj.animation_data raises (Scenario A→anim_data sub-key; Scenario B→action_name sub-key) |
| 5 | `READ_ACTION_REFERENCE` | action_name | animation_data.action raises |
| 6 | `READ_ACTION_NAME` | action_name | action.name raises |
| 7 | `READ_OBJECT_DATA` | pose_position | obj.data raises or obj.data is None |
| 8 | `READ_POSE_POSITION` | pose_position | data.pose_position raises |
| 9 | `READ_CURRENT_FRAME` | current_frame | scene.frame_current raises |

Unique error_type: `ANIMATION_STATE_COMPUTATION_ERROR` (all 9 cases).
Unique operation values: 9.
READ_ANIMATION_DATA can appear under animation_data or action_name sub-key
depending on whether require_animation_data is true (Scenario A vs B).

## 10. _collect_target_errors (unchanged from R4)

```text
Order: hierarchy×3 → standing → facing → visibility → rotation → animation_state

Animation State messages: one per ERROR sub-result.
Format: "ANIMATION_STATE_COMPUTATION_ERROR: target '<tid>' animation_state
         operation '<operation>'"

Max messages per target: 3.
(When animation_object PASS: animation_data ERROR + pose_position ERROR
 + current_frame ERROR possible simultaneously. animation_object ERROR
 precludes animation_data/action_name/pose_position execution.)
```

## 11. Runtime Read Counts

### 11.1 Read Count Table

| # | Read Target | AST Access Points | Runtime Max | Trigger | Cache |
|---|---|---|---|---|---|
| 1 | scene.objects | 1 | 1 | animation_state block present | N/A |
| 2 | obj.name | 1 | N (loop-local) | object lookup iteration | Not cached |
| 3 | obj.animation_data | 1 | 1 (max) | require_animation_data=true OR expected_action_name set | Cached in local var |
| 4 | animation_data.action | 1 | 1 (max) | expected_action_name set, animation_data not None | Cached |
| 5 | action.name | 1 | 1 (max) | expected_action_name set, action not None | Cached |
| 6 | obj.data | 1 | 1 (max) | expected_pose_position set | Cached |
| 7 | data.pose_position | 1 | 1 (max) | expected_pose_position set, data not None | Cached |
| 8 | scene.frame_current | 1 | 1 (max) | record_current_frame=true | Cached |

```text
AST Access Points: each attribute has exactly 1 authorized access point
  in _check_animation_state or its reachable helpers.

Runtime Max: the maximum number of times the Blender property is read
  at execution time. Conditional attributes: 0 if not triggered, max 1
  if triggered. obj.name: N times (once per scene object during iteration).

obj.animation_data cache:
  When require_animation_data=true AND expected_action_name is set:
    obj.animation_data read once → cached.
    animation_data sub-check uses cache.
    action_name sub-check uses cache (Scenario A: dependency model).
    If animation_data sub-check is FAIL/ERROR → action_name = NOT_CHECKED
    (Scenario A), cache was already read.

  When require_animation_data is false/null AND expected_action_name is set:
    obj.animation_data read once for action_name check (Scenario B).
    animation_data sub-key not present.
    Cache still single read — no second use.
```

## 12. Scope Guard — Precise Counts

### 12.1 ENTRY_FUNCTION

```text
_check_animation_state(scene, target)
Defined in: blender_scene_reader.py
```

### 12.2 ALLOWED_ATTRIBUTES (8)

```text
 1. scene.objects
 2. obj.name
 3. obj.animation_data
 4. animation_data.action
 5. action.name
 6. obj.data
 7. data.pose_position
 8. scene.frame_current
```

### 12.3 FORBIDDEN_ATTRIBUTES (21)

```text
 1. matrix_world             12. hide_render
 2. matrix_local             13. hide_get
 3. matrix_basis             14. material_slots
 4. matrix_parent_inverse    15. bound_box
 5. rotation_euler           16. evaluated_get
 6. rotation_quaternion      17. evaluated_depsgraph_get
 7. rotation_mode            18. to_mesh
 8. location                 19. to_mesh_clear
 9. scale                    20. users_collection
10. dimensions               21. nla_tracks
11. hide_viewport
```

### 12.4 ALLOWED_CALLS

```text
ALLOWED_BLENDER_CALLS: NONE
ALLOWED_PYTHON_BUILTINS: YES (str comparison, dict operations, iteration, exceptions)
```

### 12.5 FORBIDDEN_CALLS

```text
1. Any bpy.ops.* operator  — wildcard rule, covers all operators
2. bpy.data.objects.get(...)  — any argument

Note: bpy.ops.wm.open_mainfile, bpy.ops.wm.save_as_mainfile,
bpy.ops.wm.save_mainfile are covered by rule 1 (Any bpy.ops.*).
```

### 12.6 FORBIDDEN_SUBSCRIPTS (1)

```text
1. bpy.data.objects["..."]
```

### 12.7 WRITE_DETECTION

```text
Zero AST Store/Delete nodes on Blender object attributes.
Zero assignment to: obj.*, scene.*, data.*, action.*, bpy.*.
```

### 12.8 REACHABLE_HELPER_RULES and ALIAS_RULES (unchanged)

```text
Reachable helpers: functions called from _check_animation_state (direct/transitive).
Shallow walking: FunctionDef/ClassDef outside call graph skipped.
Alias tracking: variable and method aliases.
Pattern: Rotation I4A scope guard (EXISTING_PROJECT_CONVENTION).
```

## 13. Implementation Boundaries (unchanged)

```text
FILES TO MODIFY:
  - blender_scene_reader.py
  - asset_scene_preflight_check.py
  - protocol_guard/phase3_min/tests/ (new test files)

FILES NOT TO MODIFY:
  - asset_scene_preflight_core.py (LOCKED 14A Core)
  - All existing test files (LOCKED)
  - All .blend files
```

## 14. Test Split (unchanged)

```text
I1:  Pre-open schema validation — CPython (2 existing tests)
I2:  Configuration semantics — CPython only
I3:  Object lookup — Real Blender
I4A: Runtime PASS/FAIL — Real Blender
I4B: ERROR boundaries — Real Blender
I5:  Scope guard — CPython
E:   Final regression — CPython + Real Blender

REAL_BLENDER_REQUIRED: TRUE
```

## 15. Design Completeness Matrix

```text
[x] MODEL_A: sub-key present only when field configured
[x] Block missing/null: top-level NOT_CHECKED, merged, participates in overall
[x] Scene=None: guard BEFORE loop; merge entirely skipped
[x] Overall: pre-animation × animation_state, ERROR > FAIL > PASS
[x] ROOT_FAIL + ANIM_ERROR = ERROR (not FAIL)
[x] action_name Scenario A (anim_data sub-key present): dependency NOT_CHECKED
[x] action_name Scenario B (no anim_data sub-key): independent obj.animation_data read
[x] obj.animation_data=None → Scenario A: anim_data FAIL + action_name N/C;
    Scenario B: action_name FAIL
[x] action=None → FAIL (ACTION_NAME_MISMATCH)
[x] action.name=None → FAIL (ACTION_NAME_MISMATCH)
[x] obj.data=None → ERROR (READ_OBJECT_DATA_FAILED)
[x] frame_current=None → PASS, None recorded
[x] None-before-deref: all matrix rows consistent
[x] FAIL codes: 4
[x] ERROR operations: 9 unique
[x] ALLOWED_ATTRIBUTES: 8
[x] FORBIDDEN_ATTRIBUTES: 21 (individually counted)
[x] FORBIDDEN_CALLS: 2 rules (wildcard bpy.ops.* + bpy.data.objects.get)
[x] FORBIDDEN_SUBSCRIPTS: 1
[x] AST access points: 1 per attribute
[x] Runtime counts: conditional (0 or max 1, obj.name: N)
[x] obj.animation_data cache: single read for both scenarios
[x] Max simultaneous ERRORs: 3
[x] _collect_target_errors: 8-group order, operation in message
[x] AMBIGUOUS vs LOOKUP: distinct operations
[x] Integration: Option A post-root merge
[x] Root independence preserved
[x] Target scene only
[x] LOCKED_SCHEMA preserved
[x] CONTRACT_CONFLICTS: 0
```

## 16. Scope Compliance

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

## 17. Deliverable

```text
UPLOAD_NEXT_FILE: reviews/UPLOAD_NEXT/ANIMATION_STATE_DESIGN_R5_CORRECTION/ANIMATION_STATE_DESIGN_R5_CORRECTION_UPLOAD.zip
```
