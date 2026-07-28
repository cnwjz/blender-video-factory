# Animation State Design R4

```text
TASK_ID: ANIMATION_STATE_DESIGN_R4_CORRECTION
TASK_TYPE: DESIGN_CORRECTION
DATE: 2026-07-22
DESIGN_VERSION: R4
DESIGN_STATUS: READY_FOR_INDEPENDENT_REVIEW
IMPLEMENTATION_AUTHORIZED: FALSE
SUPERSEDES: ANIMATION_STATE_DESIGN_R3.md
```

## R4 Correction Summary

```text
F-001: MODEL_A adopted throughout. Sub-key present only when field configured
       (require_animation_data=true, expected_action_name set, etc.).
       Missing/null/false fields → sub-key omitted. Top-level scans present keys.
       Block missing/null → {"result":"NOT_CHECKED","note":"..."} — no sub-keys.

F-003: Scene=None → _check_animation_state NOT called. per_target_results stays [].
       No result produced, no merge attempted. Contradiction removed.

F-004: None check BEFORE dereference. animation_data=None → directly FAIL
       (ACTION_NAME_MISMATCH), not dereference→Exception→ERROR.
       obj.data=None → directly ERROR (READ_OBJECT_DATA_FAILED, not by dereference).
       obj.name Exception mapped. frame_current=None → PASS with None recorded.

F-005A: AMBIGUOUS uses distinct operation "RESOLVE_ANIMATION_OBJECT_NAME".
       LOOKUP_ERROR uses "LOOKUP_ANIMATION_OBJECT". Messages include operation,
       making them distinguishable. Max simultaneous ERROR = 3 (corrected from 5).

F-005B: Runtime read count table restored. Scope guard identifiers counted individually
       (no merged entries). "Any bpy.ops.*" restored to FORBIDDEN_CALLS.
       bpy.data.objects.get and bpy.data.objects[...] rules restored.
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

## 3. Sub-Key Existence Model — MODEL_A

### 3.1 Rule

```text
MODEL_A: A sub-key exists in checks.animation_state IFF its trigger
field is configured with a value that activates the check.

| Sub-key | Present when |
|---|---|
| animation_object | always (if animation_state block present and non-null) |
| animation_data | require_animation_data is true |
| action_name | expected_action_name is a non-null string |
| pose_position | expected_pose_position is a non-null string |
| current_frame | record_current_frame is true |

Top-level aggregation: scans only the sub-keys that are present.
If no sub-keys are present → top-level = PASS (all configured checks passed;
nothing was configured, nothing failed).
```

### 3.2 Configuration → Sub-Key Mapping

```text
animation_state missing → {"result": "NOT_CHECKED", "note": "ANIMATION_STATE_NOT_CONFIGURED"}
  No sub-keys. This IS the complete checks.animation_state value.

animation_state: null → same as missing.

animation_state: {"animation_object_name": "Armature"} (all other fields null/missing):
  Sub-keys: animation_object only.
  Top-level = animation_object.result.

animation_state: {"animation_object_name": "A", "require_animation_data": true,
                   "expected_action_name": "idle", "expected_pose_position": "POSE",
                   "record_current_frame": true}:
  Sub-keys: all 5 present.
```

### 3.3 Block Missing/Null in Overall

```text
When animation_state block is missing or null:
  checks.animation_state = {"result": "NOT_CHECKED", "note": "ANIMATION_STATE_NOT_CONFIGURED"}
  This value IS merged into per_target_results[i]["checks"]["animation_state"].
  It participates in overall: NOT_CHECKED does not affect overall
  (overall scans for ERROR > FAIL; NOT_CHECKED contributes neither).

_has_animation_state(target):
  Returns True when target.get("animation_state") is a non-null dict.
  False when missing or None → block NOT_CHECKED result used.
```

## 4. Integration (unchanged from R3)

### 4.1 Location

```text
open_blend_and_get_scene(), after _check_root_objects() returns (line 1407):

  per_target_results = _check_root_objects(scene, targets)

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

_recompute_overall(checks):
  Scans checks.*.result for all keys present in checks.
  If any result == "ERROR" → return "ERROR"
  elif any result == "FAIL" → return "FAIL"
  else → return "PASS"
```

### 4.2 Scene is None

```text
scene is None → _check_root_objects returns [] (existing behavior, line 1107).
Animation State loop: _check_animation_state NOT called.
No per_target_results → no merge.
check.py receives empty per_target_results → no ERROR collection.
Consistent with scene_basic.scene_exists: false.
```

### 4.3 Root × Overall Matrix (unchanged)

| Root Outcome | Animation State | Overall |
|---|---|---|
| PASS | PASS | PASS |
| PASS | FAIL | FAIL |
| PASS | ERROR | ERROR |
| ROOT_OBJECT_NOT_FOUND | any | FAIL (root) |
| ROOT_OBJECT_TYPE_MISMATCH | any | FAIL (root) |
| AMBIGUOUS_ROOT_OBJECT_NAME | any | ERROR (root) |
| Root lookup ERROR | any | ERROR (root) |

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
```

### 5.2 animation_data Sub-Key

```python
# Present only when require_animation_data is true.

# PASS:
{"result": "PASS", "animation_data_present": True}

# FAIL:
{"result": "FAIL", "failure_code": "ANIMATION_DATA_NOT_PRESENT"}

# ERROR:
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "READ_ANIMATION_DATA", "note": "READ_ANIMATION_DATA_FAILED"}

# NOT_CHECKED (dependency):
{"result": "NOT_CHECKED", "note": "ANIMATION_OBJECT_NOT_FOUND"}
# or
{"result": "NOT_CHECKED", "note": "ANIMATION_OBJECT_UNAVAILABLE"}
```

### 5.3 action_name Sub-Key

```python
# Present only when expected_action_name is a non-null string.

# PASS:
{"result": "PASS", "action_name": "<name>"}

# FAIL (animation_data is None → action cannot exist):
{"result": "FAIL", "failure_code": "ACTION_NAME_MISMATCH"}

# FAIL (action is None):
{"result": "FAIL", "failure_code": "ACTION_NAME_MISMATCH"}

# FAIL (name mismatch):
{"result": "FAIL", "failure_code": "ACTION_NAME_MISMATCH"}

# ERROR:
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "READ_ACTION_REFERENCE", "note": "READ_ACTION_REFERENCE_FAILED"}

# ERROR:
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "READ_ACTION_NAME", "note": "READ_ACTION_NAME_FAILED"}

# NOT_CHECKED (dependency):
{"result": "NOT_CHECKED", "note": "ANIMATION_OBJECT_NOT_FOUND"}
# or
{"result": "NOT_CHECKED", "note": "ANIMATION_OBJECT_UNAVAILABLE"}
# or
{"result": "NOT_CHECKED", "note": "ANIMATION_DATA_NOT_AVAILABLE"}
```

### 5.4 pose_position Sub-Key

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

# NOT_CHECKED (dependency):
{"result": "NOT_CHECKED", "note": "ANIMATION_OBJECT_NOT_FOUND"}
# or
{"result": "NOT_CHECKED", "note": "ANIMATION_OBJECT_UNAVAILABLE"}
```

### 5.5 current_frame Sub-Key

```python
# Present only when record_current_frame is true.

# PASS (frame recorded):
{"result": "PASS", "current_frame": <int or None>}

# ERROR:
{"result": "ERROR", "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
 "operation": "READ_CURRENT_FRAME", "note": "READ_CURRENT_FRAME_FAILED"}

# No NOT_CHECKED — current_frame is independent of animation_object.
```

### 5.6 Top-Level Aggregation

```text
Top-level checks.animation_state.result:
  Scan all PRESENT sub-key results.
  ERROR if any present sub-key is ERROR.
  FAIL if any present sub-key is FAIL.
  PASS otherwise (all present sub-keys PASS or NOT_CHECKED,
  or no sub-keys present).

NOT_CHECKED at top-level only when animation_state block is missing or null.
```

### 5.7 Valid Sub-Key Combinations (MODEL_A)

```text
Config: anim_obj only (require_animation_data=false, others null)
  → Sub-keys: animation_object
  → Possible: PASS, FAIL, ERROR

Config: anim_obj + anim_data + action_name (require_animation_data=true,
         expected_action_name="idle", others null)
  → Sub-keys: animation_object, animation_data, action_name
  → If anim_obj PASS: anim_data=PASS/FAIL/ERROR, action_name=PASS/FAIL/ERROR/N/C
  → If anim_obj FAIL: anim_data=N/C(NOT_FOUND), action_name=N/C(NOT_FOUND)
  → Max ERROR: anim_obj ERROR + anim_data ERROR (if anim_obj PASS)
    + action_name ERROR (if anim_data PASS) = 1 (mutually exclusive)
    Actually: anim_obj ERROR → anim_data N/C, action_name N/C → max 1 ERROR
    Or: anim_obj PASS + anim_data ERROR + action_name N/C → max 1 ERROR
    Or: anim_obj PASS + anim_data PASS + action_name ERROR → max 1 ERROR

Config: all 5 sub-keys
  → anim_obj PASS: anim_data/action_name/pose_position execute
  → current_frame always independent
  → Max simultaneous ERRORs:
    anim_obj=PASS, anim_data=ERROR, action_name=N/C(DATA_NOT_AVAILABLE),
    pose_position=ERROR, current_frame=ERROR
    → 3 ERRORs (anim_data + pose_position + current_frame)
  → Or: anim_obj=ERROR, current_frame=ERROR
    → 2 ERRORs (anim_obj + current_frame)

Maximum simultaneous ERROR sub-results in one target: 3.
```

## 6. Dependency Rules

```text
animation_object → PASS → obj reference valid, dependent checks execute.

animation_object → FAIL or ERROR →
  animation_data: NOT_CHECKED (NOT_FOUND or UNAVAILABLE)
  action_name: NOT_CHECKED (NOT_FOUND or UNAVAILABLE)
  pose_position: NOT_CHECKED (NOT_FOUND or UNAVAILABLE)
  current_frame: executes independently (reads scene, not object)

animation_object PASS + animation_data FAIL or ERROR →
  action_name: NOT_CHECKED (ANIMATION_DATA_NOT_AVAILABLE)
  pose_position: executes independently (reads obj.data)
  current_frame: executes independently

NOT_CHECKED reasons:
  "ANIMATION_OBJECT_NOT_FOUND"   — object name not in scene
  "ANIMATION_OBJECT_UNAVAILABLE" — ambiguous name or lookup exception
  "ANIMATION_DATA_NOT_AVAILABLE" — animation_data check failed/errored (action_name only)
```

## 7. Object Lookup (unchanged)

```text
Method: iterate scene.objects, case-sensitive exact match (obj.name == name).
bpy.data.objects.get: NOT used.
bpy.data.objects[...]: NOT used.
Type constraint: NONE.
```

## 8. FAIL/ERROR Boundary — Corrected

### 8.1 Unified Rule

```text
Value obtained successfully + is None when required → FAIL (or appropriate verdict)
Value obtained successfully + mismatches expected → FAIL
Attribute access raises Exception → ERROR
Dependency not met → NOT_CHECKED

NONE is NOT dereferenced to create artificial exceptions.
If a property is None, the code checks for None BEFORE accessing sub-properties.
```

### 8.2 Complete Matrix

| # | Read Target | Normal value | Value=None behavior | Exception behavior |
|---|---|---|---|---|
| 1 | `scene.objects` iteration | success | N/A | ERROR: `LOOKUP_ANIMATION_OBJECT` |
| 2 | `obj.name` (per object in loop) | string | N/A (Blender objects always have .name) | ERROR: `READ_ANIMATION_OBJECT_NAME` |
| 3 | `obj.animation_data` | non-None or None | None → FAIL (if require_animation_data=true); None → proceed to check before deref (if expected_action_name set, see #4) | ERROR: `READ_ANIMATION_DATA` |
| 4 | `animation_data.action` | non-None or None | Checks obj.animation_data first: if None → FAIL (ACTION_NAME_MISMATCH, no deref); if non-None → read .action. action=None → FAIL (ACTION_NAME_MISMATCH) | ERROR: `READ_ACTION_REFERENCE` |
| 5 | `action.name` | string | Only accessed after confirming action is not None → N/A | ERROR: `READ_ACTION_NAME` |
| 6 | `obj.data` | non-None or None | None → ERROR: `READ_OBJECT_DATA_FAILED` (no deref — .data is None, pose_position cannot be read) | ERROR: `READ_OBJECT_DATA` |
| 7 | `data.pose_position` | "POSE"/"REST"/other | Only accessed after confirming data is not None. None → FAIL (POSE_POSITION_MISMATCH) | ERROR: `READ_POSE_POSITION` |
| 8 | `scene.frame_current` | int or None | None → PASS, recorded as None | ERROR: `READ_CURRENT_FRAME` |

### 8.3 Key Correction: None Before Dereference

```text
expected_action_name set, obj.animation_data is None:
  Check obj.animation_data. Value is None.
  Do NOT dereference None.animation_data.action.
  Instead: directly FAIL (ACTION_NAME_MISMATCH).
  Rationale: None has no .action, so no action name can match.

expected_action_name set, obj.animation_data is non-None, .action is None:
  Read animation_data.action. Value is None.
  Do NOT dereference None.name.
  Instead: directly FAIL (ACTION_NAME_MISMATCH).
  Rationale: None has no .name, so no name can match.

expected_pose_position set, obj.data is None:
  Read obj.data. Value is None.
  Do NOT dereference None.pose_position.
  Instead: ERROR (READ_OBJECT_DATA_FAILED).
  Rationale: Cannot read pose_position from None. This is a structural
  issue with the object, not a mismatch.

expected_pose_position set, obj.data is non-None, .pose_position is None:
  Read data.pose_position. Value is None.
  None != expected → FAIL (POSE_POSITION_MISMATCH).

scene.frame_current is None:
  Read scene.frame_current. Value is None.
  Record as None → PASS, current_frame: None.
```

## 9. FAIL Codes and ERROR Operations

### 9.1 FAIL Codes (4 unique, unchanged)

| # | failure_code | Sub-key | Trigger |
|---|---|---|---|
| 1 | `ANIMATION_OBJECT_NOT_FOUND` | animation_object | object name not in scene |
| 2 | `ANIMATION_DATA_NOT_PRESENT` | animation_data | animation_data is None |
| 3 | `ACTION_NAME_MISMATCH` | action_name | animation_data=None, action=None, or name mismatch |
| 4 | `POSE_POSITION_MISMATCH` | pose_position | pose_position != expected |

### 9.2 ERROR Operations (8 unique)

| # | operation | note | Sub-key | Trigger |
|---|---|---|---|---|
| 1 | `LOOKUP_ANIMATION_OBJECT` | `LOOKUP_ANIMATION_OBJECT_FAILED` | animation_object | scene.objects iteration raises |
| 2 | `RESOLVE_ANIMATION_OBJECT_NAME` | `AMBIGUOUS_ANIMATION_OBJECT_NAME` | animation_object | multiple objects with same name |
| 3 | `READ_ANIMATION_OBJECT_NAME` | `READ_ANIMATION_OBJECT_NAME_FAILED` | animation_object | obj.name raises during iteration |
| 4 | `READ_ANIMATION_DATA` | `READ_ANIMATION_DATA_FAILED` | animation_data | obj.animation_data raises |
| 5 | `READ_ACTION_REFERENCE` | `READ_ACTION_REFERENCE_FAILED` | action_name | animation_data.action raises |
| 6 | `READ_ACTION_NAME` | `READ_ACTION_NAME_FAILED` | action_name | action.name raises |
| 7 | `READ_OBJECT_DATA` | `READ_OBJECT_DATA_FAILED` | pose_position | obj.data raises or obj.data is None |
| 8 | `READ_POSE_POSITION` | `READ_POSE_POSITION_FAILED` | pose_position | data.pose_position raises |
| 9 | `READ_CURRENT_FRAME` | `READ_CURRENT_FRAME_FAILED` | current_frame | scene.frame_current raises |

Unique error_type: `ANIMATION_STATE_COMPUTATION_ERROR` (all 9 cases).
Unique operation values: 9.
Unique note values: 9.

## 10. _collect_target_errors

### 10.1 Order (unchanged)

```text
1. hierarchy (object_exists)
2. hierarchy (direct_children)
3. hierarchy (descendants)
4. standing
5. facing
6. visibility
7. rotation
8. animation_state  ← NEW
```

### 10.2 Animation State Messages

```text
When checks.animation_state.result == "ERROR":
  Collect one message per ERROR sub-result.
  Message format includes operation to distinguish cases:
    "ANIMATION_STATE_COMPUTATION_ERROR: target '<tid>' animation_state
     operation '<operation>'"

  Sub-checks checked in order:
    animation_object, animation_data, action_name, pose_position, current_frame

  For each sub-key where result == "ERROR":
    op = sub_result["operation"]
    err_msgs.append(
      f"ANIMATION_STATE_COMPUTATION_ERROR: target '{tid}' "
      f"animation_state operation '{op}'"
    )

  Distinguishability:
    "LOOKUP_ANIMATION_OBJECT" vs "RESOLVE_ANIMATION_OBJECT_NAME" —
    different operation strings in the message.
    AMBIGUOUS is distinguishable from LOOKUP_FAILED without
    needing the note field in the message.

    "READ_ANIMATION_OBJECT_NAME" is distinguishable from
    "LOOKUP_ANIMATION_OBJECT" — different operations.

  Maximum messages per target: 3.
  (animation_object + animation_data independent ERRORs not possible;
   animation_object ERROR precludes animation_data execution.
   Max: anim_data ERROR + pose_position ERROR + current_frame ERROR = 3,
   when animation_object PASS.)
```

## 11. Runtime Read Counts

### 11.1 Read Count Table

| # | Read Target | Max Runtime Reads | Trigger Condition | Cache |
|---|---|---|---|---|
| 1 | `scene.objects` iteration | 1 | animation_state block present and non-null | N/A (iteration) |
| 2 | `obj.name` (per object) | N (loop-local) | during animation object lookup | Not cached (loop-local comparison only) |
| 3 | `obj.animation_data` | 1 | require_animation_data=true OR expected_action_name set | Cached in local variable; reused for both checks |
| 4 | `animation_data.action` | 1 | expected_action_name set and animation_data is not None | Cached in local variable |
| 5 | `action.name` | 1 | expected_action_name set and action is not None | Cached in local variable |
| 6 | `obj.data` | 1 | expected_pose_position set | Cached in local variable |
| 7 | `data.pose_position` | 1 | expected_pose_position set and data is not None | Cached in local variable |
| 8 | `scene.frame_current` | 1 | record_current_frame=true | Cached in local variable |

### 11.2 Cache Contract — obj.animation_data Single Read

```text
When BOTH require_animation_data=true AND expected_action_name is set:
  obj.animation_data is read ONCE and stored in a local variable.

  require_animation_data check uses the cached value:
    if cached is None → FAIL (ANIMATION_DATA_NOT_PRESENT)
    else → PASS

  expected_action_name check uses the SAME cached value:
    if cached is None → FAIL (ACTION_NAME_MISMATCH) [no deref]
    else → read cached.action → compare .name

  This ensures obj.animation_data is read at most once per invocation,
  even when both checks are configured.

Pattern: same as Visibility read-once cache (EXISTING_PROJECT_CONVENTION).
```

### 11.3 AST vs Runtime

```text
AST Load count: counts source-code attribute access nodes in
  _check_animation_state and reachable helpers.

Runtime count: actual Blender property reads at execution time.

obj.name: N runtime reads during iteration. Scope guard AST limit:
  obj.name access allowed only within the animation object lookup loop,
  used only for case-sensitive string comparison (==). Not stored or
  propagated beyond the loop.

All other attributes: AST count == runtime count == 1.
```

## 12. Scope Guard — Precise Counts

### 12.1 ENTRY_FUNCTION

```text
_check_animation_state(scene, target)
  Defined in: blender_scene_reader.py
```

### 12.2 ALLOWED_ATTRIBUTES (8 unique identifiers)

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

### 12.3 FORBIDDEN_ATTRIBUTES (18 unique identifiers)

```text
 1. matrix_world
 2. matrix_local
 3. matrix_basis
 4. matrix_parent_inverse
 5. rotation_euler
 6. rotation_quaternion
 7. rotation_mode
 8. location
 9. scale
10. dimensions
11. hide_viewport
12. hide_render
13. hide_get
14. material_slots
15. bound_box
16. evaluated_get
17. evaluated_depsgraph_get
18. to_mesh
19. to_mesh_clear
20. users_collection
21. nla_tracks
```

Count: 21 (each attribute name counted individually).

### 12.4 ALLOWED_CALLS

```text
ALLOWED_BLENDER_CALLS: NONE
  No bpy.* module function calls.
  No Blender type method calls.

ALLOWED_PYTHON_BUILTINS: YES
  str comparison (==, !=), dict.get(), list.append(),
  sorted(), len(), isinstance(), try/except, for/in.
```

### 12.5 FORBIDDEN_CALLS (5)

```text
1. bpy.ops.wm.open_mainfile
2. bpy.ops.wm.save_as_mainfile
3. bpy.ops.wm.save_mainfile
4. bpy.data.objects.get(...)      — any argument
5. Any bpy.ops.* operator          — all operators, not just listed ones
```

### 12.6 FORBIDDEN_SUBSCRIPTS (1)

```text
1. bpy.data.objects["..."]        — any key
```

### 12.7 WRITE_DETECTION

```text
Zero AST Store/Delete nodes targeting Blender object attributes.
No assignment to: obj.*, scene.*, data.*, action.*, bpy.*.
```

### 12.8 REACHABLE_HELPER_RULES

```text
All functions called from _check_animation_state (directly or transitively).
Includes local functions and lambdas.
Shallow walking: FunctionDef/ClassDef bodies outside call graph are skipped.
Alias tracking: variable and method aliases.
Pattern: Rotation I4A scope guard (EXISTING_PROJECT_CONVENTION).
```

## 13. Implementation Boundaries (unchanged from R3)

```text
FILES TO MODIFY:
  - blender_scene_reader.py: _check_animation_state() + merge loop
  - asset_scene_preflight_check.py: _collect_target_errors() animation_state case
  - protocol_guard/phase3_min/tests/: new test files

FILES NOT TO MODIFY:
  - asset_scene_preflight_core.py (LOCKED 14A Core)
  - All existing test files (LOCKED)
  - All .blend files
```

## 14. Test Split (unchanged from R3)

```text
I1:  Pre-open schema validation — CPython (already tested, 2 tests)
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
[x] Block missing/null: NOT_CHECKED, merged into overall, does not affect it
[x] Scene=None: _check_animation_state NOT called; no results produced
[x] None-before-deref: animation_data=None→FAIL; obj.data=None→ERROR; action=None→FAIL
[x] obj.name Exception mapped: READ_ANIMATION_OBJECT_NAME operation
[x] frame_current=None: PASS with None recorded
[x] AMBIGUOUS vs LOOKUP: distinct operations (RESOLVE_ANIMATION_OBJECT_NAME vs LOOKUP_ANIMATION_OBJECT)
[x] Max simultaneous ERRORs: 3
[x] Runtime read count table: 8 rows restored
[x] obj.animation_data cache: single read for both checks
[x] Scope guard: identifiers counted individually (8 allowed, 21 forbidden)
[x] "Any bpy.ops.*" restored to FORBIDDEN_CALLS
[x] bpy.data.objects.get and bpy.data.objects[...] in rules
[x] 4 FAIL codes
[x] 9 ERROR operations
[x] _collect_target_errors: 8-group order
[x] Integration: Option A post-root merge preserved
[x] Root independence preserved
[x] Target scene parameter only
[x] REAL_BLENDER_REQUIRED: TRUE
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
UPLOAD_NEXT_FILE: reviews/UPLOAD_NEXT/ANIMATION_STATE_DESIGN_R4_CORRECTION/ANIMATION_STATE_DESIGN_R4_CORRECTION_UPLOAD.zip
```
