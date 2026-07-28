# Animation State Design R1

```text
TASK_ID: ANIMATION_STATE_DESIGN
TASK_TYPE: DESIGN
DATE: 2026-07-22
DESIGN_VERSION: R1
DESIGN_STATUS: READY_FOR_INDEPENDENT_REVIEW
IMPLEMENTATION_AUTHORIZED: FALSE
```

## 1. Design Basis

### 1.1 Authoritative Inputs

| Source | Role |
|---|---|
| `ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md` §9 | AUTHORITATIVE_REQUIREMENT: field names, check semantics, C10, disclaimer |
| `asset_scene_preflight_core.py` lines 370-387 | LOCKED_SCHEMA: type/null validation for all 5 fields |
| `ROTATION_DESIGN_R3.md` | EXISTING_PROJECT_CONVENTION: result structure, ERROR mapping, failure codes |
| `14B_4A_VISIBILITY_DESIGN_R2.md` | EXISTING_PROJECT_CONVENTION: read-once, write-forbidden, field independence |
| `14B_3B_FACING_DESIGN_R2C1.md` | EXISTING_PROJECT_CONVENTION: scope guard, pre-open validation pattern |
| `ANIMATION_STATE_ORIGINAL_REQUIREMENT_AUDIT_REPORT.md` (R3) | AUDIT: 18 NO_AUTHORITATIVE_BASIS items, 0 CONTRACT_CONFLICTS |

### 1.2 Design Decisions Classification

Every decision in this document is classified:

```text
AUTHORITATIVE_REQUIREMENT  — from Contract R2 §9
LOCKED_SCHEMA             — from core.py LOCKED 14A Core
EXISTING_PROJECT_CONVENTION — from locked field group designs
NEW_DESIGN_DECISION       — this design chooses among valid options
```

## 2. Fields

| # | Field | Type (LOCKED_SCHEMA) | Required |
|---|---|---|---|
| 1 | `animation_state.animation_object_name` | non-empty string | Yes, if block present |
| 2 | `animation_state.require_animation_data` | boolean or null | No |
| 3 | `animation_state.expected_action_name` | non-empty string or null | No |
| 4 | `animation_state.expected_pose_position` | "POSE", "REST", or null | No |
| 5 | `animation_state.record_current_frame` | boolean or null | No |

LOCKED_SCHEMA: core.py `_validate_animation_state()` enforces these types at pre-open.
All 5 fields appear in Contract R2 §9.1 (AUTHORITATIVE_REQUIREMENT).

## 3. Configuration Semantics

```text
animation_state missing → NOT_CHECKED (NEW_DESIGN_DECISION)
animation_state: null  → NOT_CHECKED (NEW_DESIGN_DECISION)
animation_state: {}    → schema requires animation_object_name; pre-open ERROR (LOCKED_SCHEMA)

Each nullable field:
  null → check skipped, field omitted from result (NEW_DESIGN_DECISION)
  missing → same as null (NEW_DESIGN_DECISION)

record_current_frame: false → frame not recorded, key omitted from result (NEW_DESIGN_DECISION)
```

Basis: same pattern as Rotation Design R3 §2 (EXISTING_PROJECT_CONVENTION).

## 4. Result Structures

Nested path: `checks.animation_state`.

### 4.1 NOT_CHECKED

```python
{
    "result": "NOT_CHECKED",
    "note": "ANIMATION_STATE_NOT_CONFIGURED"
}
```

Trigger: `animation_state` missing or null. (NEW_DESIGN_DECISION)
Pattern: same as Rotation `"REQUIREMENT_NOT_CONFIGURED"` (EXISTING_PROJECT_CONVENTION).

### 4.2 PASS

```python
{
    "result": "PASS",
    "animation_object": {
        "result": "PASS",
        "object_name": "<animation_object_name from spec>"
    },
    "animation_data_present": True,
    "action_name": "<action.name>" or None,
    "pose_position": "<pose_position>" or None,
    "current_frame": <int> or None
}
```

Field inclusion rules:
- `animation_data_present`: present when `require_animation_data` is true (NEW_DESIGN_DECISION)
- `action_name`: present when `expected_action_name` is a non-null string (NEW_DESIGN_DECISION)
- `pose_position`: present when `expected_pose_position` is a non-null string (NEW_DESIGN_DECISION)
- `current_frame`: present when `record_current_frame` is true (NEW_DESIGN_DECISION)

### 4.3 FAIL

```python
{
    "result": "FAIL",
    "failure_code": "<code from §5.2>",
    "animation_object": {
        "result": "PASS",
        "object_name": "<name>"
    },
    # plus the same conditional fields as PASS, for the check that failed
}
```

FAIL occurs at the top-level `animation_state` result. The failing sub-check is identified by `failure_code`. The `animation_object` sub-result is always present when the object was found.

### 4.4 ERROR

```python
{
    "result": "ERROR",
    "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
    "operation": "<from §5.3>",
    "note": "<from §5.3>",
    # animation_object sub-result present if object was found before error
}
```

ERROR omits: `failure_code`, `animation_data_present`, `action_name`, `pose_position`, `current_frame`.
Pattern: same as Rotation Design R3 §4 (EXISTING_PROJECT_CONVENTION).

### 4.5 Aggregation

```text
Overall checks.animation_state.result:
  ERROR > FAIL > PASS > NOT_CHECKED (EXISTING_PROJECT_CONVENTION)

animation_object sub-result:
  independent of other checks — object lookup ERROR does not block
  require_animation_data or record_current_frame if they can execute
  without the object (e.g., record_current_frame reads scene, not object)

NEW_DESIGN_DECISION: require_animation_data, expected_action_name,
expected_pose_position each depend on animation_object being found.
If animation_object is FAIL or ERROR, those dependent checks produce
NOT_CHECKED with note "ANIMATION_OBJECT_NOT_FOUND".
```

## 5. Failure Codes and ERROR Contracts

### 5.1 Result Summary

| Status | Meaning |
|---|---|
| PASS | All configured checks satisfied |
| FAIL | A configured check did not pass |
| ERROR | A required read or computation failed |
| NOT_CHECKED | animation_state not configured or dependency not met |

### 5.2 FAIL Codes

| Trigger | failure_code | Basis |
|---|---|---|
| animation_object_name not found in scene | `ANIMATION_OBJECT_NOT_FOUND` | AUTHORITATIVE_REQUIREMENT (§9.2 line 276) |
| require_animation_data=true, animation_data is None | `ANIMATION_DATA_NOT_PRESENT` | AUTHORITATIVE_REQUIREMENT (§9.2 line 277) |
| expected_action_name set, action.name does not match | `ACTION_NAME_MISMATCH` | AUTHORITATIVE_REQUIREMENT (§9.2 line 278) |
| expected_pose_position set, pose_position does not match | `POSE_POSITION_MISMATCH` | AUTHORITATIVE_REQUIREMENT (§9.2 line 279) |

All failure_code values are NEW_DESIGN_DECISION.

### 5.3 ERROR Operations

| Trigger | error_type | operation | note | Basis |
|---|---|---|---|---|
| `bpy.context.scene` access raises | `ANIMATION_STATE_COMPUTATION_ERROR` | `ACCESS_SCENE_REFERENCE` | `ACCESS_SCENE_REFERENCE_FAILED` | NEW_DESIGN_DECISION |
| `scene.objects` iteration raises | `ANIMATION_STATE_COMPUTATION_ERROR` | `LOOKUP_ANIMATION_OBJECT` | `LOOKUP_ANIMATION_OBJECT_FAILED` | NEW_DESIGN_DECISION |
| `object.animation_data` raises AttributeError | `ANIMATION_STATE_COMPUTATION_ERROR` | `READ_ANIMATION_DATA` | `READ_ANIMATION_DATA_FAILED` | NEW_DESIGN_DECISION |
| `animation_data.action` raises AttributeError | `ANIMATION_STATE_COMPUTATION_ERROR` | `READ_ACTION_REFERENCE` | `READ_ACTION_REFERENCE_FAILED` | NEW_DESIGN_DECISION |
| `action.name` raises AttributeError | `ANIMATION_STATE_COMPUTATION_ERROR` | `READ_ACTION_NAME` | `READ_ACTION_NAME_FAILED` | NEW_DESIGN_DECISION |
| `object.data` raises AttributeError | `ANIMATION_STATE_COMPUTATION_ERROR` | `READ_OBJECT_DATA` | `READ_OBJECT_DATA_FAILED` | NEW_DESIGN_DECISION |
| `data.pose_position` raises AttributeError | `ANIMATION_STATE_COMPUTATION_ERROR` | `READ_POSE_POSITION` | `READ_POSE_POSITION_FAILED` | NEW_DESIGN_DECISION |
| `scene.frame_current` raises AttributeError | `ANIMATION_STATE_COMPUTATION_ERROR` | `READ_CURRENT_FRAME` | `READ_CURRENT_FRAME_FAILED` | NEW_DESIGN_DECISION |

ERROR pattern matches Rotation Design R3 §3 (EXISTING_PROJECT_CONVENTION):
- Unified `error_type`: "ANIMATION_STATE_COMPUTATION_ERROR"
- Distinct `operation` per read step
- Distinct `note` describing the failure

### 5.4 Ambiguous Object Name

```text
If multiple objects in the scene have the same name as animation_object_name:
  result: ERROR
  error_type: ANIMATION_STATE_COMPUTATION_ERROR
  operation: LOOKUP_ANIMATION_OBJECT
  note: AMBIGUOUS_ANIMATION_OBJECT_NAME

NEW_DESIGN_DECISION: follows Hierarchy AMBIGUOUS_ROOT_OBJECT_NAME pattern
(EXISTING_PROJECT_CONVENTION).
```

## 6. Per-Field Behavior

### 6.1 animation_object_name

```text
LOOKUP (NEW_DESIGN_DECISION):
  Method: iterate scene.objects, case-sensitive exact name match.
  Rationale: same pattern as root object lookup in 14B_2A
  (EXISTING_PROJECT_CONVENTION). bpy.data.objects.get() is NOT used
  because it does not check scene membership.

  Scene membership: python object identity (is) against target scene.
  Same pattern as 14B_2C (EXISTING_PROJECT_CONVENTION).

  Type constraint: NONE. Contract does not specify object type
  (AUTHORITATIVE_REQUIREMENT audit §6.1). The design does not add one.

RESULT WHEN FOUND (animation_object sub-result):
  {"result": "PASS", "object_name": "<name>"}

RESULT WHEN NOT FOUND:
  {"result": "FAIL", "failure_code": "ANIMATION_OBJECT_NOT_FOUND",
   "animation_object": {"result": "FAIL", "object_name": "<name from spec>"}}

RESULT WHEN AMBIGUOUS:
  Top-level ERROR per §5.4. animation_object sub-result not produced.

RELATION TO ROOT OBJECT:
  animation_object_name may equal root_object_name. No restriction.
  Animation State check is independent of root object check.
  (NEW_DESIGN_DECISION: no dependency beyond scene being open.)
```

### 6.2 require_animation_data

```text
WHEN TRUE (AUTHORITATIVE_REQUIREMENT §9.2 line 277):
  Read object.animation_data.
  If animation_data is not None → PASS, record animation_data_present: True.
  If animation_data is None → FAIL, failure_code: ANIMATION_DATA_NOT_PRESENT.

WHEN FALSE, NULL, OR MISSING:
  Check skipped. animation_data_present key omitted from result.
  (NEW_DESIGN_DECISION: follow existing project convention for null=false=skip)

WHEN animation_data EXISTS BUT .action IS NONE:
  require_animation_data itself → PASS (animation_data is not None).
  This check does not inspect .action.
  (NEW_DESIGN_DECISION: contract only requires animation_data not be None)

NLA: NOT CHECKED. Contract mentions only .action (§9.2 line 278),
  not NLA tracks. No expansion beyond contract scope.
  (AUTHORITATIVE_REQUIREMENT audit disclaimer)
```

### 6.3 expected_action_name

```text
WHEN SET TO NON-NULL STRING (AUTHORITATIVE_REQUIREMENT §9.2 line 278):
  Read object.animation_data.action.
  If animation_data is None → ERROR (READ_ACTION_REFERENCE_FAILED).
  If action is None → FAIL, failure_code: ACTION_NAME_MISMATCH
    (action is None, cannot match any expected name).
    NEW_DESIGN_DECISION: None != any string, so mismatch.
  If action.name == expected_action_name → PASS, record action_name.
  If action.name != expected_action_name → FAIL, failure_code: ACTION_NAME_MISMATCH.

WHEN NULL OR MISSING:
  Check skipped. action_name key omitted from result.

CASE SENSITIVITY (NEW_DESIGN_DECISION):
  Exact case-sensitive match. Same pattern as root object name matching
  in 14B_2A (EXISTING_PROJECT_CONVENTION).

RELATION TO require_animation_data:
  expected_action_name is independent. It reads animation_data.action
  regardless of require_animation_data value.
  If animation_data is None → ERROR (not FAIL), because the read path
  failed, not the match condition.
  (NEW_DESIGN_DECISION: independence avoids hidden coupling)

ACTION QUALITY:
  Per §9.3 disclaimer, name match is structural only.
  Does not verify motion correctness.
```

### 6.4 expected_pose_position

```text
WHEN SET TO NON-NULL STRING (AUTHORITATIVE_REQUIREMENT §9.2 line 279):
  Read object.data.
  If object has no .data attribute → ERROR (READ_OBJECT_DATA_FAILED).
  Read data.pose_position.
  If data has no .pose_position → ERROR (READ_POSE_POSITION_FAILED).
  If data.pose_position == expected_pose_position → PASS, record pose_position.
  If data.pose_position != expected_pose_position → FAIL,
    failure_code: POSE_POSITION_MISMATCH.

WHEN NULL OR MISSING:
  Check skipped. pose_position key omitted from result.

ALLOWED VALUES (LOCKED_SCHEMA):
  "POSE", "REST", or null. Schema enforces this at pre-open.
  This design does not add or relax values.
  No CONTRACT_CONFLICT found (R3 audit).

OBJECT TYPE:
  .data.pose_position is Armature-specific in Blender.
  The design does NOT add an explicit type check.
  Non-Armature objects will fail at the .data or .pose_position
  attribute access → ERROR. This is sufficient and avoids
  introducing an unauthoritative type constraint.
  (NEW_DESIGN_DECISION: rely on attribute errors, not type checks)
```

### 6.5 record_current_frame

```text
WHEN TRUE (AUTHORITATIVE_REQUIREMENT §9.2 line 280):
  Read scene.frame_current from the target scene.
  Store value under key "current_frame" in the animation_state result.
  (NEW_DESIGN_DECISION: output key name)

  This is a data-recording field. It does NOT produce PASS or FAIL.
  If true → record and include key. Recording failure → ERROR.
  (NEW_DESIGN_DECISION: no verdict, consistent with §9.2 wording
   "is recorded in the result" — not "must equal" or "must pass")

WHEN FALSE, NULL, OR MISSING:
  Do NOT read scene.frame_current. Key omitted from result.
  (NEW_DESIGN_DECISION: false means don't record)

INTERACTION WITH scene_basic.current_frame:
  reader.py line 1343 already reads frame_current for scene_basic result.
  Animation State reads independently when record_current_frame is true.
  No deduplication — each check reads what it needs.
  (NEW_DESIGN_DECISION: independent reads, same pattern as Facing
   independent matrix_world reads — EXISTING_PROJECT_CONVENTION)

ERROR:
  If scene is None or frame_current read raises → ERROR,
  operation: READ_CURRENT_FRAME.
  If ERROR occurs alongside other FAIL results → ERROR takes priority
  (ERROR > FAIL aggregation).
```

## 7. Read Counts and Read-Only Boundary

### 7.1 Maximum Read Counts

| Blender Property / Operation | Max Reads | Condition |
|---|---|---|
| `scene.objects` iteration (object lookup) | 1 | Always, if animation_state configured |
| `object.animation_data` | 1 | `require_animation_data=true` OR `expected_action_name` set |
| `animation_data.action` | 1 | `expected_action_name` set |
| `action.name` | 1 | `expected_action_name` set |
| `object.data` | 1 | `expected_pose_position` set |
| `data.pose_position` | 1 | `expected_pose_position` set |
| `scene.frame_current` | 1 | `record_current_frame=true` |

NEW_DESIGN_DECISION for all counts. Pattern: Visibility Design R2 §3 (EXISTING_PROJECT_CONVENTION).

### 7.2 Cache Strategy

```text
Read-once cache: each Blender property read result is stored in a local
variable. Result construction uses cached values, never re-reads Blender.

Same pattern as Visibility Design R2 §3 (EXISTING_PROJECT_CONVENTION).
```

### 7.3 Write Forbidden

```text
Animation State MUST NOT write to:
  - Any Blender object attribute
  - animation_data
  - action
  - pose_position
  - frame_current
  - Any scene property

Pattern: Visibility Design R2 §4 (EXISTING_PROJECT_CONVENTION).
```

### 7.4 Prohibited API Calls

```text
FORBIDDEN:
  - bpy.ops.wm.open_mainfile
  - bpy.ops.wm.save_as_mainfile
  - bpy.ops.wm.save_mainfile
  - bpy.ops.render.render
  - Any operator that modifies .blend state

Pattern: all locked field groups (EXISTING_PROJECT_CONVENTION).
```

## 8. Scope Guard Decision

### 8.1 Decision

```text
SCOPE_GUARD_REQUIRED: TRUE

RATIONALE (NEW_DESIGN_DECISION):
  Animation State reads properties (animation_data, action, pose_position,
  frame_current) that are currently in FORBIDDEN_SCOPE for other field groups
  (Visibility test line 20). A scope guard is necessary to:
  1. Confirm Animation State does not exceed its authorized reads
  2. Confirm other field groups do not begin reading animation properties
  3. Enforce the read count limits in §7.1

Pattern: Standing, Facing, Visibility, Rotation all have scope guards
(EXISTING_PROJECT_CONVENTION).
```

### 8.2 Allowed Reads

```text
ANIMATION_STATE_SCOPE — ALLOWED:
  scene.objects (animation object lookup)
  obj.name (case-sensitive match)
  obj.animation_data (when require_animation_data or expected_action_name)
  animation_data.action (when expected_action_name)
  action.name (when expected_action_name)
  obj.data (when expected_pose_position)
  data.pose_position (when expected_pose_position)
  scene.frame_current (when record_current_frame)
```

### 8.3 Forbidden Reads

```text
ANIMATION_STATE_SCOPE — FORBIDDEN:
  matrix_world, matrix_local, matrix_basis, matrix_parent_inverse
  rotation_euler, rotation_quaternion, rotation_mode
  location, scale, dimensions
  parent, children
  hide_viewport, hide_render, hide_get
  material_slots, materials
  bound_box, evaluated_get, evaluated_depsgraph_get, to_mesh
  users_collection, bpy.data.collections
  world_to_camera_view
  nla_tracks (contract does not address NLA)
  Any write operation
```

### 8.4 Scope Guard Implementation

```text
Entry function: _check_animation_state (or equivalent in reader.py)
The scope guard AST analyzer verifies:
  1. Only allowed attributes are read within the function and its reachable helpers
  2. Read counts do not exceed §7.1 limits
  3. No forbidden APIs are called

Pattern: Rotation I4A scope guard (EXISTING_PROJECT_CONVENTION).
```

## 9. Integration With Existing Systems

### 9.1 Pre-open vs Runtime Split

```text
Pre-open (core.py, NO CHANGE):
  _validate_animation_state() validates types, null, empty string.
  Already implemented. LOCKED_SCHEMA.

Runtime (reader.py, NEW CODE):
  New function: _check_animation_state(scene, target, animation_object_name)
  Called after root object is resolved, before per-target result assembly.
  (NEW_DESIGN_DECISION: animation_state check does NOT depend on root check
  passing — it only depends on animation_object_name being found in scene.)

Call order in _check_root_objects or similar:
  Existing hierarchy checks → animation_state check → aggregation.
```

### 9.2 Target Overall Aggregation

```text
checks.animation_state.result participates in per-target overall aggregation:
  ERROR > FAIL > PASS > NOT_CHECKED (EXISTING_PROJECT_CONVENTION)

Collected by existing _collect_target_errors() for ERROR targets.
No changes to 14A Core aggregation logic needed.
```

### 9.3 scene_basic.current_frame Interaction

```text
reader.py line 1343: scene.frame_current already read for scene_basic.
Animation State reads independently when record_current_frame=true.
No deduplication — independent reads per field group.
Same pattern as Facing independent matrix_world reads (EXISTING_PROJECT_CONVENTION).
```

### 9.4 Files to Modify During Implementation

```text
EXPECTED FILE CHANGES:
  - blender_scene_reader.py: new _check_animation_state() function
  - asset_scene_preflight_check.py: caller integration in result assembly
  - protocol_guard/phase3_min/tests/: new test files
    (test_asset_scene_preflight_blender_animation_state_i1.py etc.)

FILES THAT MUST NOT BE MODIFIED:
  - asset_scene_preflight_core.py (LOCKED: 14A Core)
  - Existing test files for other field groups (LOCKED)
  - All .blend files
```

### 9.5 Test Structure

```text
PROPOSED TEST SPLIT:
  I1: Pre-open validation (core.py — already tested, 2 tests)
  I2: Configuration semantics (NOT_CHECKED, null, missing, false)
  I3: Animation object lookup (found, not found, ambiguous)
  I4A: Runtime PASS/FAIL (all 4 checks, individual and combined)
  I4B: ERROR boundaries (all 8 ERROR operations)
  I5: Scope guard (AST enforcement of read boundaries)
  E:  Final regression (full protocol_guard + all prior field groups)

REAL_BLENDER_REQUIRED: YES
  animation_data, action, pose_position, and frame_current require
  real Blender objects and scenes to test. Same pattern as all other
  runtime field group tests (EXISTING_PROJECT_CONVENTION).
```

## 10. Design Completeness Matrix

```text
[x] animation_object_name: found, not found, ambiguous, type constraint
[ ] animation_object_name: type constraint → NOT ADDED (no contract basis)
[x] require_animation_data: true, false, null, missing
[x] require_animation_data: animation_data None, not None, AttributeError
[x] expected_action_name: set, null, missing
[x] expected_action_name: action exists/None, name match/mismatch, case sensitivity
[x] expected_pose_position: set, null, missing
[x] expected_pose_position: POSE/REST/null, data missing, pose_position missing, AttributeError
[x] expected_pose_position: LOCKED_SCHEMA preserved (POSE/REST exclusive)
[x] record_current_frame: true, false, null, missing
[x] record_current_frame: output key name, scene.frame_current read, ERROR
[x] record_current_frame: verdict behavior (data-recording, no PASS/FAIL)
[x] NOT_CHECKED: animation_state missing, null
[x] NOT_CHECKED: dependency not met (animation_object not found)
[x] FAIL codes: 4 defined (OBJECT_NOT_FOUND, DATA_NOT_PRESENT, ACTION_NAME_MISMATCH, POSE_POSITION_MISMATCH)
[x] ERROR operations: 8 defined (ACCESS_SCENE through READ_CURRENT_FRAME) + AMBIGUOUS_ANIMATION_OBJECT_NAME
[x] ERROR aggregation: ERROR > FAIL > PASS > NOT_CHECKED
[x] FAIL + ERROR simultaneous: aggregation resolves to ERROR
[x] record_current_frame + ERROR: ERROR takes priority, frame not recorded
[x] Read counts: 7 properties, each at most 1 read
[x] Cache strategy: read-once, local variables
[x] Write forbidden: explicit list
[x] Scope guard: required, allowed/forbidden lists defined
[x] Test split: I1-I5 + E proposed
[x] Real Blender required: YES
[x] Contract conflicts: 0
[x] LOCKED_SCHEMA preserved: POSE/REST exclusive, type/null validation unchanged
```

## 11. Scope Compliance

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

## 12. Deliverable

```text
UPLOAD_NEXT_FILE: reviews/UPLOAD_NEXT/ANIMATION_STATE_DESIGN_R1/ANIMATION_STATE_DESIGN_R1_UPLOAD.zip
```
