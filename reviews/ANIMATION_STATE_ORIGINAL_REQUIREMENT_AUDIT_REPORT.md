# Animation State Original Requirement Audit Report (R2 Corrected)

```text
TASK_ID: ANIMATION_STATE_ORIGINAL_REQUIREMENT_AUDIT_R2_CORRECTION
TASK_TYPE: ORIGINAL_REQUIREMENT_AUDIT (EVIDENCE_CORRECTION)
DATE: 2026-07-22
TASK_STATUS: COMPLETED
PREVIOUS_TASK_ID: ANIMATION_STATE_ORIGINAL_REQUIREMENT_AUDIT
```

## R2 Correction Summary

```text
F-001 FIXED: AUTHORITATIVE_REQUIREMENT and CURRENT_SCHEMA_BEHAVIOR fully separated.
  Contract: field names, JSON example values, basic check semantics, C10, disclaimer.
  Schema: all type enforcement, null acceptance, empty string rejection,
  POSE/REST exclusive list, block-level optionality.
  Removed phrases: "Contract defines non-empty string", "Contract defines boolean or null",
  "require_animation_data optional according to Contract", etc.

F-002 FIXED: Armature type requirement removed.
  Contract specifies property path object.data.pose_position.
  It does NOT specify an animation object type constraint.
  Behavior for objects lacking .data or .pose_position is a design question.

F-003 FIXED: Locked schema preserved; premature design decisions removed.
  expected_pose_position POSE/REST exclusive list is CURRENT_SCHEMA_BEHAVIOR.
  14A Core is LOCKED. Unless a CONTRACT_CONFLICT is found and adjudicated,
  the schema constraint stands. No CONTRACT_CONFLICT was found.
  Removed: "design may relax", "record_current_frame has no PASS/FAIL",
  "scope guard absence is a production defect".
  Implementation gaps now list only contract-mandated runtime capabilities.
```

## 1. R40 State Confirmation

```text
MASTER_MAP_VERSION: R40
ACTIVE_TASK_ID: ANIMATION_STATE_ORIGINAL_REQUIREMENT_AUDIT
ANIMATION_STATE_DESIGN_STATUS: NOT_STARTED
ANIMATION_STATE_IMPLEMENTATION_STATUS: NOT_STARTED
14A_CORE: LOCKED
LOCKED_TASKS_MUST_NOT_BE_REDESIGNED: TRUE
```

## 2. Authoritative Sources

| # | File | Relevant Section |
|---|---|---|
| S1 | `ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md` | §9 lines 256-285 |
| S2 | `Blender_固定资产模板路线_新对话交接文档_v4.md` | Lines 620-624 (historical inspection fields) |
| S3 | `PHASE_3_MINIMUM_DESIGN_SPEC_R1.md` | Animation = HUMAN_JUDGMENT |
| S4 | `asset_scene_preflight_core.py` | `_validate_animation_state()` lines 370-387 |
| S5 | `asset_scene_preflight_check.py` | Runtime infrastructure |
| S6 | `blender_scene_reader.py` | `scene.frame_current` line 1343 |

## 3. Authoritative Requirement (Contract R2 §9 Only)

All five field names originate from Contract R2 §9.1 (lines 264-271). The JSON block shows example values: `"Armature"`, `true`, `null`, `null`, `true`.

### 3.1 Field Names and Example Values

```text
animation_state.animation_object_name     example: "Armature"
animation_state.require_animation_data    example: true
animation_state.expected_action_name      example: null
animation_state.expected_pose_position    example: null
animation_state.record_current_frame      example: true
```

### 3.2 Check Semantics (§9.2)

```text
1. animation_object_name must exist in the scene. FAIL if missing.
   (line 276)

2. If require_animation_data: object.animation_data must not be None.
   (line 277)

3. If expected_action_name is set:
   object.animation_data.action.name must match.
   (line 278)

4. expected_pose_position: if set,
   object.data.pose_position must match (e.g., 'POSE', 'REST').
   (line 279)

5. record_current_frame: the current scene.frame_current
   is recorded in the result.
   (line 280)
```

### 3.3 C10 Constraint

```text
Animation object = explicit spec field (not inferred from hierarchy).
(Contract line 522)
```

### 3.4 Action Quality Disclaimer (§9.3)

```text
The checker records the action name and pose position as structural facts.
It does NOT verify that the action produces correct motion, that idle/walk
animations are correctly loaded, or that cross-frame playback is valid.
These remain human-review or deferred-state items.
(lines 282-284)
```

### 3.5 What the Contract Does NOT Specify

```text
The contract does NOT specify:
  - Exact field types (e.g., "non-empty string", "boolean or null")
  - Null acceptance semantics
  - Missing-field behavior
  - Empty string behavior
  - Whether POSE/REST is an exclusive or example list
  - Block-level optionality (animation_state absent vs null vs {})
  - FAIL code names
  - ERROR conditions
  - Object type constraint for animation_object_name
  - Object lookup mechanism
  - Result output key names or structure
  - Case sensitivity of action name matching
  - NLA track consideration
  - Scope guard boundaries
  - Runtime behavior when the animation_state block is absent or null
    (schema skips validation; whether the result is NOT_CHECKED, omitted,
    or represented in another form is not specified)
```

## 4. Current Schema Behavior (core.py `_validate_animation_state()`)

The following behaviors are defined by the current schema implementation, NOT by Contract R2:

```text
BLOCK-LEVEL:
  - animation_state block absent or None → validation skipped (line 371-372)
  - animation_state present but not a dict → error (line 373)

TYPE AND VALUE ENFORCEMENT:
  - animation_object_name: must be non-empty string (line 374-375)
    Null → error. Empty string → error.
  - require_animation_data: if present and not None, must be boolean (line 376-378)
    Null → silently skip validation.
  - expected_action_name: if present and not None, must be non-empty string (line 379-381)
    Null → silently skip. Empty string → error.
  - expected_pose_position: if present and not None, must be "POSE" or "REST" (line 382-384)
    Null → silently skip. Any other value → error.
  - record_current_frame: if present and not None, must be boolean (line 385-387)
    Null → silently skip.

LOCKED STATUS OF POSE/REST:
  14A Core is LOCKED (R40 master map). The POSE/REST exclusive list in core.py
  is part of the locked schema. No CONTRACT_CONFLICT was found between the
  contract ("e.g., 'POSE', 'REST'") and the schema (exclusive list), because
  an exclusive list is a stricter subset, not a contradiction. The schema
  behavior is preserved and is not open for relaxation during ordinary design.
```

## 5. Current Runtime Implementation

```text
IMPLEMENTED:
  - Pre-open schema validation via _validate_animation_state()
    (core.py lines 370-387)
  - scene.frame_current read for scene_basic result
    (reader.py line 1343 — separate from animation_state)
  - Pre-open validation tests (test_core.py lines 306-327, 2 tests)

NOT IMPLEMENTED — CONTRACT-MANDATED RUNTIME CAPABILITIES:
  1. Animation object lookup in scene (Contract §9.2 line 276)
  2. animation_data existence check (Contract §9.2 line 277)
  3. action.name comparison (Contract §9.2 line 278)
  4. data.pose_position comparison (Contract §9.2 line 279)
  5. scene.frame_current recording in animation_state result
     (Contract §9.2 line 280)

NO RUNTIME EXISTS FOR:
  - ERROR handling (all five checks)
  - Scope guard
  - Target overall aggregation
  - Blender tests
```

## 6. Per-Field Audit

### 6.1 `animation_object_name`

| Aspect | Finding | Classification |
|---|---|---|
| Field name and path | `animation_state.animation_object_name`, Contract §9.1 line 266 | AUTHORITATIVE_REQUIREMENT |
| Existence check | Must exist in scene; FAIL if missing (§9.2 line 276) | AUTHORITATIVE_REQUIREMENT |
| Object naming | Explicit spec field, not inferred from hierarchy (C10) | AUTHORITATIVE_REQUIREMENT |
| Type constraint | Contract does not specify object type | NO_AUTHORITATIVE_BASIS_FOUND |
| Lookup mechanism | Contract does not specify lookup method | NO_AUTHORITATIVE_BASIS_FOUND |
| Ambiguous names | Contract does not address duplicates | NO_AUTHORITATIVE_BASIS_FOUND |
| FAIL code name | Contract does not name the failure code | NO_AUTHORITATIVE_BASIS_FOUND |
| ERROR conditions | Contract does not define ERROR triggers | NO_AUTHORITATIVE_BASIS_FOUND |
| Non-empty string requirement | Schema: core.py line 374 | CURRENT_SCHEMA_BEHAVIOR |
| Null rejection | Schema: core.py line 374 | CURRENT_SCHEMA_BEHAVIOR |
| Empty string rejection | Schema: core.py line 374 | CURRENT_SCHEMA_BEHAVIOR |
| Runtime status | Not implemented | CURRENT_RUNTIME_BEHAVIOR |

### 6.2 `require_animation_data`

| Aspect | Finding | Classification |
|---|---|---|
| Field name and path | `animation_state.require_animation_data`, Contract §9.1 line 267 | AUTHORITATIVE_REQUIREMENT |
| True behavior | `object.animation_data` must not be None (§9.2 line 277) | AUTHORITATIVE_REQUIREMENT |
| False behavior | Contract conditional "If" implies no check when false | AUTHORITATIVE_REQUIREMENT |
| Blender property | `object.animation_data` (§9.2 line 277) | AUTHORITATIVE_REQUIREMENT |
| FAIL code name | Not specified | NO_AUTHORITATIVE_BASIS_FOUND |
| ERROR conditions | Not specified (e.g., AttributeError reading animation_data) | NO_AUTHORITATIVE_BASIS_FOUND |
| NLA consideration | Contract mentions only .action, not NLA | NO_AUTHORITATIVE_BASIS_FOUND |
| Boolean type enforcement | Schema: core.py lines 376-378 | CURRENT_SCHEMA_BEHAVIOR |
| Null acceptance | Schema: null silently skips | CURRENT_SCHEMA_BEHAVIOR |
| Runtime status | Not implemented | CURRENT_RUNTIME_BEHAVIOR |

### 6.3 `expected_action_name`

| Aspect | Finding | Classification |
|---|---|---|
| Field name and path | `animation_state.expected_action_name`, Contract §9.1 line 268 | AUTHORITATIVE_REQUIREMENT |
| When set | `object.animation_data.action.name` must match (§9.2 line 278) | AUTHORITATIVE_REQUIREMENT |
| Quality disclaimer | Name match only; does not verify motion quality (§9.3) | AUTHORITATIVE_REQUIREMENT |
| Case sensitivity | Contract: "must match" — case sensitivity not specified | NO_AUTHORITATIVE_BASIS_FOUND |
| action=None behavior | Contract does not address `.action` being None | NO_AUTHORITATIVE_BASIS_FOUND |
| FAIL code name | Not specified | NO_AUTHORITATIVE_BASIS_FOUND |
| ERROR conditions | Not specified | NO_AUTHORITATIVE_BASIS_FOUND |
| Non-empty string | Schema: core.py lines 379-381 | CURRENT_SCHEMA_BEHAVIOR |
| Null acceptance | Schema: null silently skips | CURRENT_SCHEMA_BEHAVIOR |
| Runtime status | Not implemented | CURRENT_RUNTIME_BEHAVIOR |

### 6.4 `expected_pose_position`

| Aspect | Finding | Classification |
|---|---|---|
| Field name and path | `animation_state.expected_pose_position`, Contract §9.1 line 269 | AUTHORITATIVE_REQUIREMENT |
| When set | `object.data.pose_position` must match (§9.2 line 279) | AUTHORITATIVE_REQUIREMENT |
| Example values | Contract: "e.g., 'POSE', 'REST'" — examples only | AUTHORITATIVE_REQUIREMENT |
| Property path | `object.data.pose_position` (§9.2 line 279) | AUTHORITATIVE_REQUIREMENT |
| Object type constraint | Contract does NOT specify that animation object must be Armature. `.data.pose_position` is a property path; whether objects lacking `.data` or `.pose_position` produce ERROR or FAIL is a design question. | NO_AUTHORITATIVE_BASIS_FOUND |
| FAIL code name | Not specified | NO_AUTHORITATIVE_BASIS_FOUND |
| ERROR conditions | Not specified | NO_AUTHORITATIVE_BASIS_FOUND |
| Exclusive POSE/REST list | Schema: core.py lines 382-384. 14A Core is LOCKED. The exclusive list stands unless a CONTRACT_CONFLICT is found and adjudicated. No CONTRACT_CONFLICT exists (exclusive list is a stricter subset of examples). | CURRENT_SCHEMA_BEHAVIOR (LOCKED) |
| Null acceptance | Schema: null silently skips | CURRENT_SCHEMA_BEHAVIOR |
| Runtime status | Not implemented | CURRENT_RUNTIME_BEHAVIOR |

### 6.5 `record_current_frame`

| Aspect | Finding | Classification |
|---|---|---|
| Field name and path | `animation_state.record_current_frame`, Contract §9.1 line 270 | AUTHORITATIVE_REQUIREMENT |
| True behavior | Record `scene.frame_current` in result (§9.2 line 280) | AUTHORITATIVE_REQUIREMENT |
| Blender property | `scene.frame_current` (§9.2 line 280) | AUTHORITATIVE_REQUIREMENT |
| Output key name | Contract: "recorded in the result" — no key name specified | NO_AUTHORITATIVE_BASIS_FOUND |
| False/null/missing output | Contract only specifies true behavior | NO_AUTHORITATIVE_BASIS_FOUND |
| Interaction with scene_basic | reader.py line 1343 already reads frame_current for scene_basic | NO_AUTHORITATIVE_BASIS_FOUND |
| ERROR conditions | Not specified | NO_AUTHORITATIVE_BASIS_FOUND |
| Boolean type enforcement | Schema: core.py lines 385-387 | CURRENT_SCHEMA_BEHAVIOR |
| Null acceptance | Schema: null silently skips | CURRENT_SCHEMA_BEHAVIOR |
| Runtime status | Not implemented | CURRENT_RUNTIME_BEHAVIOR |
| Verdict behavior | Whether this field produces PASS/FAIL or only records data is a design question. Contract does not assign a verdict. | NO_AUTHORITATIVE_BASIS_FOUND |

## 7. NO_AUTHORITATIVE_BASIS_FOUND — Complete List

```text
 1. animation_object_name object type constraint
 2. animation_object_name lookup mechanism (bpy.data.objects.get vs scene.objects)
 3. animation_object_name ambiguous name handling
 4. FAIL code names for all five checks
 5. ERROR conditions for all five checks (AttributeError, None propagation, etc.)
 6. expected_action_name case sensitivity
 7. expected_action_name: behavior when animation_data exists but .action is None
 8. expected_pose_position: behavior for objects lacking .data or .pose_position
 9. record_current_frame output key name
10. record_current_frame false/null/missing output behavior
11. record_current_frame interaction with existing scene_basic.current_frame
12. record_current_frame verdict behavior (PASS/FAIL vs data-only recording)
13. NLA track consideration (contract mentions only .action)
14. Scope guard boundaries for animation_state reads
15. Runtime behavior when animation_state block is absent or null:
    schema skips validation (CURRENT_SCHEMA_BEHAVIOR);
    whether the final runtime result is NOT_CHECKED, omitted,
    or represented in another form remains a design question
    (NO_AUTHORITATIVE_BASIS_FOUND)
16. Target overall aggregation behavior for animation_state results
17. Field independence: whether require_animation_data=false blocks expected_action_name
18. Output result structure for all animation_state checks
```

## 8. CONTRACT_CONFLICT Summary

```text
CONTRACT_CONFLICTS_FOUND: 0

Note on expected_pose_position:
  Contract §9.2: "e.g., 'POSE', 'REST'" — non-exclusive examples.
  Schema core.py: exclusive list accepting only "POSE" or "REST".
  This is NOT a conflict. The schema imposes a stricter constraint
  (subset of allowed values) than the contract (examples that do not
  forbid other values). Stricter subset ≠ contradiction.
  14A Core is LOCKED. The exclusive list stands.

Note on交接文档 v4:
  V4 action_name/pose_source/frame (lines 620-624) are superseded
  by Contract R2 §9. Not a conflict.
```

## 9. Cross-Field Relationships

```text
AUTHORITATIVE (from Contract §9):
  1. All five fields share the animation_state parent.
  2. animation_object_name is the gateway: it names the object
     against which all other checks run.
  3. expected_action_name accesses animation_data.action.name
     (implicit dependency: object → animation_data → action).
  4. expected_pose_position accesses data.pose_position
     (property path through the named object).

NOT SPECIFIED BY CONTRACT:
  5. Whether require_animation_data=false blocks expected_action_name.
  6. Whether animation_object failure blocks other checks.
  7. Whether expected_pose_position failure is independent of
     expected_action_name.
```

## 10. Open Design Questions

The following are design-phase decisions. None are currently decided:

```text
DESIGN QUESTIONS (derived from NO_AUTHORITATIVE_BASIS items):
  - Animation object type constraint (if any)
  - Object lookup mechanism and ambiguous name handling
  - FAIL code naming convention for all animation_state checks
  - ERROR condition definitions (all five checks)
  - Case sensitivity of action name matching
  - Behavior when animation_data.action is None but expected_action_name is set
  - Behavior when animation object lacks .data or .pose_position
  - record_current_frame output key name, false/null behavior,
    and interaction with scene_basic.current_frame
  - record_current_frame verdict semantics (PASS/FAIL vs data-only)
  - NLA track consideration
  - Scope guard read/write boundaries
  - Runtime behavior when animation_state block is absent or null
  - Target overall aggregation behavior
  - Field independence rules
  - Output result structure
```

## 11. Audit Conclusion

```text
CONTRACT_CONFLICTS_FOUND: 0

All five fields have authoritative basis in Contract R2 §9:
  - Field names and example values
  - Basic check semantics
  - C10 constraint (explicit spec, not inferred)
  - Action quality disclaimer

Current schema provides working pre-open validation (LOCKED 14A Core).
Current runtime has no animation_state implementation (5 contract-mandated
capabilities not yet built).

The open design questions are standard design-phase items.
None block the design phase from starting.

AUDIT_RESULT: REQUIREMENTS_SUFFICIENT_FOR_DESIGN
```

## 12. Scope Compliance

```text
DESIGN_CREATED: FALSE
DESIGN_APPROVED: NOT_WRITTEN
DESIGN_LOCKED: NOT_WRITTEN
IMPLEMENTATION_STARTED: NOT_WRITTEN
PRODUCTION_CODE_MODIFIED: FALSE
TESTS_MODIFIED: FALSE
TESTS_RUN: FALSE
BLENDER_EXECUTED: FALSE
BLEND_FILES_OPENED: FALSE
MASTER_MAP_MODIFIED: FALSE
14A_CORE_MODIFIED: FALSE
14B_2B_REAUDITED: FALSE
```

## 13. Deliverable

```text
UPLOAD_NEXT_FILE: reviews/UPLOAD_NEXT/ANIMATION_STATE_ORIGINAL_REQUIREMENT_AUDIT_R2_CORRECTION/ANIMATION_STATE_ORIGINAL_REQUIREMENT_AUDIT_R2_CORRECTION_UPLOAD.zip
```
