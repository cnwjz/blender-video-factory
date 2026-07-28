# Animation State Design Input Collection Report (R5 Corrected)

```text
TASK_ID: ANIMATION_STATE_DESIGN_INPUT_COLLECTION_R5_2B_EVIDENCE_CORRECTION
TASK_TYPE: DESIGN_INPUT_COLLECTION (PACKAGE_DEFECT)
DATE: 2026-07-22
TASK_STATUS: COMPLETED
PREVIOUS_TASK_ID: ANIMATION_STATE_DESIGN_INPUT_COLLECTION_R4_PACKAGE_CORRECTION
```

## R5 Correction Summary

```text
14B_2B DIRECT BOUNDARY EVIDENCE: INSUFFICIENT

After exhaustive search of the project directory, no standalone document was found
that directly lists 14B_2B's locked contract in prose form. The existing
14B_2B_FINAL_REVIEW_REPORT.md records formal file hashes (5 of 5 MATCH),
test results (139 core + 497 full regression passed), and boundary declarations.
File hashes authenticate the frozen implementation but do not themselves
constitute the locked contract.

The 14B_2B contract (required/allowed/forbidden direct child name rules)
is implemented in the frozen production code (check.py lines 13-61
_validate_direct_child_rules_preopen; reader.py direct child traversal logic).
This code IS the contract, expressed as frozen, hash-verified implementation.
However, per the task requirement, production source code cannot substitute
for a formal lock document that explicitly lists field names, semantics,
result codes, and read-only boundaries.

What was searched:
  - GLOBAL_CODEIFICATION_AUDIT_INPUTS/03_locked_stage_evidence/ (2B has only
    FINAL_REVIEW_REPORT.md + SOURCE_SNAPSHOT.txt — neither restates the contract)
  - GLOBAL_CODEIFICATION_AUDIT_INPUTS/90_unverified_reference/
  - GLOBAL_CODEIFICATION_AUDIT_INPUTS/99_missing_and_claude_request/
    (MISSING_OR_UNCERTAIN_FILES.md line 52: "14B-2B 独立 GPT 最终验收文本"
    listed as "可补充但不阻止启动盘点" — explicitly missing but non-blocking)
  - reviews/ (all reports — none define 14B_2B contract explicitly)
  - ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md
    (written after 14B_2 was locked; does not break down 2A/2B/2C/2D)

Comparison with 14B_2A and 14B_2C:
  - 14B_2A: SCOPE_GIT_AND_LOCK_EVIDENCE.txt documents root lookup scope,
    name matching, result codes, and 31 prohibited APIs in detail.
  - 14B_2C: FINAL_REVIEW_REPORT.md documents full locked contract with
    field names, descendant behavior, scene identity, branch pruning,
    error codes, aggregation rules, and read-only boundaries.
  - 14B_2B: FINAL_REVIEW_REPORT.md documents file hashes and test results
    only. No prose contract document.

Consequence:
  INPUT_COLLECTION_RESULT downgraded to INPUT_INSUFFICIENT.
  LOCKED_GROUPS_FULLY_REVIEWED downgraded to FALSE.
  MISSING_LOCKED_BOUNDARY_EVIDENCE: 14B_2B.
```

## R4 Correction Summary (historical)

```text
PACKAGE DEFECT FIXED: 14B_2A, 14B_2B, 14B_2C final evidence files located and included.
  Source: GLOBAL_CODEIFICATION_AUDIT_INPUTS/03_locked_stage_evidence/

  14B_2A: 14B_2A_SCOPE_GIT_AND_LOCK_EVIDENCE.txt
    — EVIDENCE_TYPE: SCOPE_GIT_AND_LOCK_EVIDENCE
    — Documents root object lookup (scene.objects traversal, case-sensitive exact),
      ROOT_OBJECT_NOT_FOUND, ROOT_OBJECT_TYPE_MISMATCH, AMBIGUOUS_ROOT_OBJECT_NAME,
      full traversal, type read only after unique match, prohibited API scan,
      locked file hash verification.

  14B_2B: 14B_2B_FINAL_REVIEW_REPORT.md
    — EVIDENCE_TYPE: FINAL_REVIEW_REPORT
    — Documents formal file hashes (all verified), 14A core 139 passed,
      full regression 497 passed/2 skipped, boundaries verified.

  14B_2C: 14B_2C_FINAL_REVIEW_REPORT.md
    — EVIDENCE_TYPE: FINAL_REVIEW_REPORT
    — Documents full locked contract: required_descendant_names,
      forbidden_descendant_name_patterns, AMBIGUOUS_DESCENDANT_NAME,
      DESCENDANT_LOOKUP_ERROR, 4 operations, scene identity (is),
      branch pruning, stable sorting, read-only boundaries,
      ERROR/FAIL/PASS/NOT_CHECKED aggregation, lock recommendation.

  Each boundary previously unsupported now has a direct evidence file in the ZIP.
  INPUT_COLLECTION_RESULT restored to INPUT_SUFFICIENT_FOR_REQUIREMENT_AUDIT.
  LOCKED_GROUPS_FULLY_REVIEWED restored to 5.
  MISSING_LOCKED_BOUNDARY_EVIDENCE: NONE.
```

## R3 Correction Summary (historical)

```text
F-001 FIXED: "Type per Contract" column removed from AUTHORITATIVE_REQUIREMENT table (§3.1).
  Exact types (non-empty string, boolean or null, string or null, "POSE"/"REST"/null)
  and null-acceptance behavior moved exclusively to CURRENT_SCHEMA_BEHAVIOR (§3.2).
  Statement "The contract states types and semantics" replaced with:
  "The contract provides field names, example values, and basic check semantics.
  Exact validation types and null behavior come from the current schema implementation."

F-002 FIXED: Premature design language removed from §5 (Existing Project Mechanisms).
  "Animation State will need explicit authorization to access animation_data" → removed.
  "animation_state will explicitly authorize animation_data" → removed.
  Replaced with factual description: Visibility scope guard prohibits animation_data.
  Whether Animation State establishes its own scope guard is deferred to design.

F-003 FIXED: Hierarchy now reviewed as 4 separate subgroups (14B_2A, 14B_2B, 14B_2C, 14B_2D).
  14B_2A, 14B_2B, 14B_2C: NO_SEPARATE_FORMAL_LOCK_RECORD_FOUND.
  Each subgroup's boundary traced to specific ZIP-included file.
  14B_2D_FORMAL_LOCK_RECORD.md no longer cited for 2A/2B/2C boundaries.
```

## 1. R39 State Confirmation

```text
MASTER_MAP_VERSION: R39
ACTIVE_TASK_ID: ANIMATION_STATE_DESIGN_INPUT_COLLECTION
ACTIVE_TASK_STATUS: NOT_STARTED
UNIQUE_NEXT_ATOMIC_TASK: ANIMATION_STATE_DESIGN_INPUT_COLLECTION
CURRENT_NEXT_TASK: ANIMATION_STATE_DESIGN_INPUT_COLLECTION
```

## 2. Authoritative Requirement Sources

| # | File | Animation Content |
|---|---|---|
| 1 | `GLOBAL_CODEIFICATION_AUDIT_INPUTS/01_authoritative_requirements/Blender_固定资产模板路线_新对话交接文档_v4.md` | High-level workflow constraints; action_name/pose_source/frame as historical inspection fields (V4 lines 620-624) |
| 2 | `GLOBAL_CODEIFICATION_AUDIT_INPUTS/02_phase3_design/PHASE_3_MINIMUM_DESIGN_SPEC_R1.md` | Animation mentioned only as HUMAN_JUDGMENT quality item |
| 3 | `GLOBAL_CODEIFICATION_AUDIT_INPUTS/02_phase3_design/ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md` | Section 9: Explicit Animation State — authoritative field definition; C10 constraint |

## 3. Exact Animation State Field Analysis

All five field names originate from **Contract R2 Section 9** (lines 256-285). The contract provides field names, JSON example values, and basic check semantics. Exact validation types, null behavior, and missing-field handling come from the current schema implementation (core.py `_validate_animation_state()`).

### 3.1 AUTHORITATIVE_REQUIREMENT — From Contract R2 §9

| # | Field | Contract Example Value | Contract Semantic | Contract Line |
|---|---|---|---|---|
| 1 | `animation_state.animation_object_name` | `"Armature"` | Explicitly named object must exist in scene; FAIL if missing | §9.1 line 266, §9.2 line 276 |
| 2 | `animation_state.require_animation_data` | `true` | If true, `object.animation_data` must not be None | §9.1 line 267, §9.2 line 277 |
| 3 | `animation_state.expected_action_name` | `null` | If set, `object.animation_data.action.name` must match | §9.1 line 268, §9.2 line 278 |
| 4 | `animation_state.expected_pose_position` | `null` | If set, `object.data.pose_position` must match | §9.1 line 269, §9.2 line 279 |
| 5 | `animation_state.record_current_frame` | `true` | Record current `scene.frame_current` in result | §9.1 line 270, §9.2 line 280 |

**C10 Constraint** (Contract line 522): "Animation object = explicit spec field (not inferred from hierarchy)." `animation_object_name` must be explicitly configured in the spec. The checker must NOT search the hierarchy to find an Armature automatically. The contract states the object must exist in the scene. Whether the object must be the root object, a descendant, or any scene object is not further constrained by the contract.

**Action Quality Disclaimer** (Contract §9.3 lines 282-284): The checker records structural facts (action name, pose position). It does NOT verify motion correctness, idle/walk loading, or cross-frame playback validity.

### 3.2 CURRENT_SCHEMA_BEHAVIOR — From core.py `_validate_animation_state()`

The following type constraints and null/missing behaviors are defined by the current schema implementation, not by Contract R2:

| Field | Schema Validation Rule | Source (core.py) |
|---|---|---|
| `animation_object_name` | Must be non-empty string; missing or empty → error | line 374-375 |
| `require_animation_data` | If not None, must be boolean; None accepted silently | line 376-378 |
| `expected_action_name` | If not None, must be non-empty string; None accepted silently | line 379-381 |
| `expected_pose_position` | If not None, must be "POSE" or "REST"; None accepted silently | line 382-384 |
| `record_current_frame` | If not None, must be boolean; None accepted silently | line 385-387 |
| `animation_state` block | Entirely optional at target level; None → function returns early | line 371-372 |
| Non-dict `animation_state` | Produces error: "must be an object" | line 373 |

The contract does not explicitly state that `require_animation_data`, `expected_action_name`, `expected_pose_position`, and `record_current_frame` accept null. The contract's JSON example shows `null` for `expected_action_name` and `expected_pose_position`, but does not define null-acceptance as a general rule. The schema implementation is what enforces these validation rules.

**Test coverage** (test_asset_scene_preflight_core.py lines 306-327):
- `test_animation_state_valid`: Full valid config with all 5 fields → no validation errors
- `test_animation_state_missing_object_name`: Empty animation_state object → error containing "animation_object_name"

### 3.3 CURRENT_RUNTIME_IMPLEMENTATION

```text
File: protocol_guard/phase3_min/asset_scene_preflight_check.py
Animation State runtime code: NONE
  No _check_animation_state function exists.
  No animation_state/animation_data/action references anywhere in check.py.

File: protocol_guard/phase3_min/blender_scene_reader.py
  Only animation-related read: scene.frame_current (line 1343)
  Returned as "current_frame" in scene_basic result.
  No animation_data, .action, nla_tracks, or pose_position reads.
```

### 3.4 NO_AUTHORITATIVE_BASIS_FOUND

```text
NO_AUTHORITATIVE_BASIS_FOUND:
  1. FAIL code naming convention for animation_state checks
  2. ERROR classification — Contract §9 lists checks but does not define
     which conditions produce ERROR vs FAIL
  3. record_current_frame output key name in the result structure
  4. record_current_frame=false output behavior (omit key, record null, etc.)
  5. Behavior when animation_data exists but .action is None while
     expected_action_name is set — FAIL vs ERROR not specified
  6. Whether animation_object_name must be an Armature-type object —
     contract is silent on type restriction
  7. NLA track consideration — Contract mentions only .action, not NLA
  8. NOT_CHECKED conditions beyond "animation_state block absent from target"
  9. Whether animation_state check executes independently when root/hierarchy
     checks fail (standing/facing/rotation pattern: execute if root valid)
  10. Interaction with scene_basic.current_frame already read by reader.py
      line 1343 — deduplication or separate read not specified
  11. Scope guard read/write boundaries for animation_state checks
  12. Target overall aggregation behavior for animation_state vs other checks
```

## 4. Existing Implementation State

### 4.1 Pre-open Schema Validation

```text
File: protocol_guard/phase3_min/asset_scene_preflight_core.py
Function: _validate_animation_state(t, i, errs) — lines 370-387
Status: IMPLEMENTED (pre-open schema validation only)
Call site: line 163, within validate_spec() target loop
```

### 4.2 Runtime Implementation

```text
File: protocol_guard/phase3_min/asset_scene_preflight_check.py
Animation State runtime: NONE
```

### 4.3 Blender Reader

```text
File: protocol_guard/phase3_min/blender_scene_reader.py
Relevant read: scene.frame_current (line 1343)
```

### 4.4 Prohibited Reads in Locked Tests

```text
test_asset_scene_preflight_blender_scene_basic.py line 410:
  "animation_data" in forbidden attribute set

test_asset_scene_preflight_blender_visibility_i2.py line 20:
  "animation_data" in FORBIDDEN_SCOPE
```

## 5. Existing Project Mechanisms

The following mechanisms exist in locked field groups. Whether any apply to Animation State is a decision for the subsequent design phase. This section records facts, not design decisions:

```text
1. Result structure: PASS / FAIL / ERROR / NOT_CHECKED
   — Used by Standing, Facing, Visibility, Rotation
   — Each group defines its own NOT_CHECKED semantics

2. Target overall aggregation: ERROR > FAIL > PASS > NOT_CHECKED
   — Implemented in check.py _collect_target_errors()

3. Root object resolution: scene.objects.get(root_object_name)
   — Used by all 5 locked groups

4. Read-once cache: each Blender property read at most once per invocation
   — Contracted in Visibility Design R2 §3 and Rotation Design R3

5. Scope Guard: AST-based enforcement of read/write boundaries
   — Implemented for Standing, Facing, Visibility, Rotation
   — Each group defines its own allowed/disallowed read set
   — Visibility scope guard currently prohibits reads of animation_data
     (test_asset_scene_preflight_blender_visibility_i2.py line 20)
   — Whether Animation State establishes its own scope guard, which
     attributes it may read, and how many times, is deferred to design

6. Pre-open validation: _validate_*_rules_preopen() pattern
   — Used by Standing, Facing, Rotation

7. Shared assertions: assert_dict_equal, assert_no_extra_keys
8. Evidence runner: run_and_capture()
9. ZIP builder: build_zip() + verify_zip()
10. 14A Core: spec loading, field validation, path safety, stable serialization,
    quaternion_min_angle_degrees, canonicalize()
```

## 6. Locked Boundary Full Review — All 5 Groups

### 6.1 Hierarchy — Subgroup Analysis

Per R39 master map, Hierarchy covers 4 subgroups. Each is analyzed separately.

#### 6.1.1 14B_2A — Root Object Existence + Type + Scene Membership

```text
SUBGROUP: 14B_2A
EVIDENCE_FILE: GLOBAL_CODEIFICATION_AUDIT_INPUTS/03_locked_stage_evidence/14B_2A_SCOPE_GIT_AND_LOCK_EVIDENCE.txt
EVIDENCE_TYPE: SCOPE_GIT_AND_LOCK_EVIDENCE
WHY_THIS_FILE_IS_AUTHORITATIVE:
  This is the formal final evidence file for 14B_2A. It was generated at the
  conclusion of the 14B_2A implementation phase and verified by the audit report
  (PROJECT_CODEIFICATION_MASTER_MAP_AUDIT_REPORT.md line 28: "14B_1, 14B_2A,
  14B_2B, 14B_2C LOCKED | YES | Evidence reports confirm").

EXACT_LOCKED_BOUNDARIES_SUPPORTED:
  - Root object lookup via scene.objects iteration (not bpy.data.objects.get)
    Evidence: reader.py line 37 — "for obj in scene.objects:"
  - Object name match: CASE_SENSITIVE_EXACT
    Evidence: reader.py line 38 — "if obj.name == root_name:"
  - Full scene traversal (no early exit after first match)
  - Object type read only after unique match (match_count == 1)
  - Result codes: ROOT_OBJECT_NOT_FOUND (match_count == 0),
    ROOT_OBJECT_TYPE_MISMATCH (type mismatch),
    AMBIGUOUS_ROOT_OBJECT_NAME (match_count > 1)
  - All spec targets supported
  - Scene basic result preserved
  - Prohibited API scan: 31 APIs verified absent (matrix_world, animation_data,
    hide_viewport, hide_render, rotation_euler, etc.)
  - Save/render/project boundaries: no production save or render operations
  - Locked file hashes: core.py SHA256 9B5DAA1C..., test_core.py SHA256 9B8F28EC...
    Both verified MATCH: TRUE
```

#### 6.1.2 14B_2B — Direct Children Name Rules

```text
SUBGROUP: 14B_2B
EVIDENCE_FILE: GLOBAL_CODEIFICATION_AUDIT_INPUTS/03_locked_stage_evidence/14B_2B_FINAL_REVIEW_REPORT.md
EVIDENCE_TYPE: FINAL_REVIEW_REPORT
EVIDENCE_STATUS: INSUFFICIENT_FOR_DIRECT_CONTRACT

WHY_INSUFFICIENT:
  This file records formal file hashes (5 of 5 MATCH: TRUE), test results
  (14A core 139 passed, full regression 497 passed/2 skipped), and boundary
  declarations. It authenticates the frozen implementation but does not
  restate the locked contract in prose.

  File hashes alone cannot prove the specific locked contract. The task
  requirement is for a document that directly lists:
    - Direct child object scope
    - Actual locked field names
    - Required/allowed/forbidden exact semantics
    - Missing/null/empty array behavior
    - Name matching rules
    - Scene membership behavior
    - PASS/FAIL/ERROR/NOT_CHECKED
    - Failure codes
    - Error types and operations
    - Aggregation and priority
    - Read-only boundaries

  No such standalone document exists for 14B_2B in the project directory.

WHAT_EXISTS:
  - 14B_2B_FINAL_REVIEW_REPORT.md: file hashes + test counts + boundary declarations
  - 14B_2B_SOURCE_SNAPSHOT.txt: source code snapshot (not a contract document)
  - Frozen production code (check.py _validate_direct_child_rules_preopen,
    reader.py direct child logic): the contract expressed as hash-verified
    implementation — but per task rules, production code cannot substitute
    for formal lock evidence
  - Global audit report: confirms 14B_2B LOCKED with "证据报告确认"
    (line 28) but does not itself restate the contract
  - MISSING_OR_UNCERTAIN_FILES.md line 52: "14B-2B 独立 GPT 最终验收文本"
    listed as missing but non-blocking

  The global audit report (GLOBAL_CODEIFICATION_AUDIT_REPORT.md lines 29-31)
  summarizes the 14B_2B scope as:
    Row 3: 直接子对象必需名称检查 (required direct child name check, 4 tests)
    Row 4: 直接子对象允许列表检查 (allowed direct child list check, 7 tests)
    Row 5: 直接子对象禁止模式检查 glob (forbidden pattern check, 9 tests)
  This is a description, not a formal contract document.

CONCLUSION:
  14B_2B DIRECT BOUNDARY EVIDENCE: INSUFFICIENT.
  The subgroup is not independently supported by a direct contract document.
  The frozen implementation is authentic (hash-verified) but the contract
  lives in code, not in a separate lock/design/acceptance document.
```

#### 6.1.3 14B_2C — Descendant Names, Ambiguity, Scene Membership, Branch Pruning

```text
SUBGROUP: 14B_2C
EVIDENCE_FILE: GLOBAL_CODEIFICATION_AUDIT_INPUTS/03_locked_stage_evidence/14B_2C_FINAL_REVIEW_REPORT.md
EVIDENCE_TYPE: FINAL_REVIEW_REPORT
WHY_THIS_FILE_IS_AUTHORITATIVE:
  This is the most comprehensive hierarchy subgroup final report. It documents
  the full 14B_2C locked contract with explicit field names, behaviors, error
  codes, and operational boundaries. Verified by the master map audit report.
  Lock recommendation: ALL_14B_2C_CHECKS_PASS, LOCK_RECOMMENDED: TRUE.

EXACT_LOCKED_BOUNDARIES_SUPPORTED:
  - Locked Contract (Section 3):
    required_descendant_names, forbidden_descendant_name_patterns,
    AMBIGUOUS_DESCENDANT_NAME, DESCENDANT_LOOKUP_ERROR
    4 operations: READ_SCENE_OBJECTS, READ_ROOT_CHILDREN,
    READ_DESCENDANT_NAME, READ_DESCENDANT_CHILDREN
  - Required Descendant Behavior (Section 5):
    Case-sensitive exact name matching, set semantics (dedup),
    Field missing/null → NOT_CHECKED, Empty array → PASS,
    Missing → REQUIRED_DESCENDANT_MISSING
  - Forbidden Descendant Behavior (Section 6):
    casefold_glob_match, case-insensitive glob, dedup,
    Match → FORBIDDEN_DESCENDANT_NAME
  - Scene Identity and Branch Pruning (Section 7):
    Python object identity (is) for scene membership,
    Root excluded from descendants, Non-scene objects excluded,
    Non-scene intermediate objects cut branches
  - Ambiguous Name Handling (Section 8):
    Two or more distinct identities with identical name →
    AMBIGUOUS_DESCENDANT_NAME ERROR
  - Lookup Error (Section 9):
    4 operations each → DESCENDANT_LOOKUP_ERROR, highest priority
  - ERROR/FAIL/PASS/NOT_CHECKED Aggregation (Section 10):
    LOOKUP_ERROR > AMBIGUITY > FAIL > PASS, NOT_CHECKED never triggers FAIL
  - Stable Sorting (Section 11): (name.casefold(), name)
  - Read-Only Boundaries (Section 12):
    No object.parent, descendant.type, evaluated geometry, bound_box,
    matrix_world, location, rotation, material_slots, animation_data,
    users_collection, world_to_camera_view, render, save in production code
  - 9 formal file hashes verified: pre-diagnostic == post-diagnostic
  - Blender focused: 158 passed, 14A core: 139 passed,
    protocol_guard full: 571 passed/2 skipped
```

#### 6.1.4 14B_2D — Descendant Type Rules + Type Cache

```text
FORMAL_LOCK_RECORD: reviews/14B_2D_FORMAL_LOCK_RECORD.md
  (ZIP: reviews/14B_2D_FORMAL_LOCK_RECORD.md)
MASTER_MAP_REFERENCE: R39 §4.2, §3 — 14B_2D: LOCKED
LOCK_BASIS: USER_FORMAL_APPROVAL
LOCK_DATE: 2026-07-18

BOUNDARIES:
  - required_descendant_types: type check per referenced name
  - Type cache by object identity (builder never re-reads obj.type)
  - AST-verified: builder has 0 obj.type attribute access nodes
  - READ_DESCENDANT_TYPE lookup error (5th operation)
  - Type error priority over AMBIGUOUS_DESCENDANT_NAME
  - Input validation: INVALID_DESCENDANT_TYPE_RULE_VALUE
```

### 6.2 Standing Up Axis (14B-3A)

```text
LOCK_RECORD: reviews/14B_3A_FORMAL_LOCK_RECORD.md
FILE_TYPE: FORMAL_LOCK_RECORD
NO_SEPARATE_FINAL_DESIGN_FILE_FOUND: TRUE
  Design decisions embedded in lock record and final independent review.

BOUNDARIES EXTRACTED:
  - 3 fields: local_up_axis, expected_world_up_axis, up_axis_tolerance_degrees
  - All 3 present → execute; all 3 absent/null → NOT_CHECKED; partial → pre-open ERROR
  - Reads root_obj.matrix_world exactly once
  - Calls to_3x3() at most once
  - 7 ERROR operation codes
  - angle <= tolerance → PASS (inclusive boundary)
  - Standing executes independently when root valid
```

### 6.3 Facing Forward Axis (14B-3B)

```text
LOCK_RECORD: reviews/14B_3B_FORMAL_LOCK_RECORD.md
FINAL_DESIGN: reviews/14B_3B_FACING_DESIGN_R2C1.md
FILE_TYPE: FORMAL_LOCK_RECORD + FINAL_DESIGN

BOUNDARIES EXTRACTED:
  - 3 fields: local_forward_axis, expected_world_forward_axis, facing_tolerance_degrees
  - Same transform pipeline as Standing (matrix_world.to_3x3())
  - Matrix strategy A: independent reads (each check reads matrix_world independently)
  - 5 operations defined
  - Nested result path: checks.facing.forward_axis
  - Scope guard: exactly 1 matrix_world load + 1 to_3x3 call each for standing AND facing
  - Pre-open: INVALID_FACING_RULE_RELATION
```

### 6.4 Visibility (14B-4A)

```text
LOCK_RECORD: reviews/14B_4A_VISIBILITY_FORMAL_LOCK_RECORD.md
FINAL_DESIGN: reviews/14B_4A_VISIBILITY_DESIGN_R2.md
FILE_TYPE: FORMAL_LOCK_RECORD + FINAL_DESIGN

BOUNDARIES EXTRACTED:
  - 2 fields: require_not_hide_viewport, require_not_hide_render
  - Reads: root_obj.hide_viewport, root_obj.hide_render
  - Read-once cache: each Blender property read at most once per invocation
  - Write forbidden: must not write to Blender object attributes
  - Field independence: one field's ERROR does not block the other
  - "animation_data" in FORBIDDEN_SCOPE for visibility
```

### 6.5 Rotation

```text
LOCK_RECORD: reviews/ROTATION_FORMAL_LOCK_RECORD.md
FINAL_DESIGN: reviews/ROTATION_DESIGN_R3.md
DESIGN_LOCK_RECORD: reviews/ROTATION_DESIGN_R3_FORMAL_LOCK_RECORD.md
FILE_TYPE: FORMAL_LOCK_RECORD + FINAL_DESIGN + DESIGN_FORMAL_LOCK

BOUNDARIES EXTRACTED:
  - 2 fields: expected_world_rotation_euler_degrees, rotation_tolerance_degrees
  - Reads root_obj.matrix_world.to_quaternion()
  - Forbidden: rotation_euler, rotation_quaternion
  - Forbidden: de-scaling, orthogonalization, reflection repair
  - Euler order: XYZ (fixed)
  - Algorithm: quaternion_min_angle_degrees (14A Core lines 501-521)
  - q/-q equivalence via abs(dot)
  - 9 ERROR branches mapped
  - FAIL code: OBJECT_ROTATION_OUT_OF_TOLERANCE
```

## 7. Contract Conflicts

```text
CONTRACT_CONFLICTS_FOUND: 0

The交接文档 v4 lists action_name, pose_source, frame as historical inspection
fields (V4 lines 620-624). Contract R2 §9 EXPRESSLY REPLACES the R1 "infer
Armature from hierarchy" approach with explicit animation_object_name.
The v4 fields are superseded, not conflicting.

C10 is explicit: "Animation object = explicit spec field (not inferred from
hierarchy)."
```

## 8. Input Sufficiency Assessment

```text
WHAT IS SUFFICIENT:
  - 5 field names, example values, and basic semantics from Contract R2 §9
  - C10 constraint: explicit spec, not inferred from hierarchy
  - Each field's pre-open validation rules (from core.py — schema behavior)
  - FAIL condition for animation_object_name (object missing from scene)
  - require_animation_data basic check (animation_data not None)
  - expected_action_name matching rule
  - expected_pose_position matching rule
  - record_current_frame basic instruction
  - Action quality disclaimer
  - Current implementation baseline: schema-only, no runtime
  - Inventory of existing project mechanisms
  - Locked boundary map from all 5 field groups (9 lock/design files)

WHAT IS INSUFFICIENT:
  - 12 NO_AUTHORITATIVE_BASIS items (see §3.4)

CONCLUSION: INPUT_INSUFFICIENT
RATIONALE: Contract §9 provides explicit field definitions and 4 of 5 locked
field groups have direct boundary evidence. However, 14B_2B lacks a standalone
contract document that directly lists its locked fields, semantics, result
codes, and read-only boundaries. The frozen production code authenticates the
implementation but cannot substitute for formal lock evidence per task rules.
MISSING_LOCKED_BOUNDARY_EVIDENCE: 14B_2B.
LOCKED_GROUPS_FULLY_REVIEWED: FALSE (14B_2B evidence insufficient).
```

## 9. Input Package File Inventory

```text
FILES_COLLECTED: 21

AUTHORITATIVE_REQUIREMENTS (3):
  GLOBAL_CODEIFICATION_AUDIT_INPUTS/01_authoritative_requirements/Blender_固定资产模板路线_新对话交接文档_v4.md
  GLOBAL_CODEIFICATION_AUDIT_INPUTS/02_phase3_design/PHASE_3_MINIMUM_DESIGN_SPEC_R1.md
  GLOBAL_CODEIFICATION_AUDIT_INPUTS/02_phase3_design/ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md

CURRENT_IMPLEMENTATION (4):
  protocol_guard/phase3_min/asset_scene_preflight_core.py
  protocol_guard/phase3_min/asset_scene_preflight_check.py
  protocol_guard/phase3_min/blender_scene_reader.py
  protocol_guard/phase3_min/tests/test_asset_scene_preflight_core.py

MASTER_MAP (1):
  reviews/PROJECT_CODEIFICATION_MASTER_MAP.md (R39)

HIERARCHY (4):
  GLOBAL_CODEIFICATION_AUDIT_INPUTS/03_locked_stage_evidence/14B_2A_SCOPE_GIT_AND_LOCK_EVIDENCE.txt
    — 14B_2A: root existence/type/scene membership boundaries
  GLOBAL_CODEIFICATION_AUDIT_INPUTS/03_locked_stage_evidence/14B_2B_FINAL_REVIEW_REPORT.md
    — 14B_2B: direct children name rules boundaries
  GLOBAL_CODEIFICATION_AUDIT_INPUTS/03_locked_stage_evidence/14B_2C_FINAL_REVIEW_REPORT.md
    — 14B_2C: descendants/ambiguity/scene membership/branch pruning boundaries
  reviews/14B_2D_FORMAL_LOCK_RECORD.md
    — 14B_2D: descendant type rules + type cache

STANDING (1):
  reviews/14B_3A_FORMAL_LOCK_RECORD.md

FACING (2):
  reviews/14B_3B_FORMAL_LOCK_RECORD.md
  reviews/14B_3B_FACING_DESIGN_R2C1.md

VISIBILITY (2):
  reviews/14B_4A_VISIBILITY_FORMAL_LOCK_RECORD.md
  reviews/14B_4A_VISIBILITY_DESIGN_R2.md

ROTATION (3):
  reviews/ROTATION_FORMAL_LOCK_RECORD.md
  reviews/ROTATION_DESIGN_R3.md
  reviews/ROTATION_DESIGN_R3_FORMAL_LOCK_RECORD.md

REPORT (1):
  reviews/ANIMATION_STATE_DESIGN_INPUT_COLLECTION_REPORT.md
```

## 10. Scope Compliance

```text
DESIGN_CREATED: FALSE
PRODUCTION_CODE_MODIFIED: FALSE
TESTS_MODIFIED: FALSE
TESTS_RUN: FALSE
BLENDER_EXECUTED: FALSE
BLEND_FILES_OPENED: FALSE
MASTER_MAP_MODIFIED: FALSE
```

## 11. Deliverable

```text
UPLOAD_NEXT_FILE: reviews/UPLOAD_NEXT/ANIMATION_STATE_DESIGN_INPUT_COLLECTION_R5_2B_EVIDENCE_CORRECTION/ANIMATION_STATE_DESIGN_INPUT_COLLECTION_R5_2B_EVIDENCE_CORRECTION_UPLOAD.zip
```
