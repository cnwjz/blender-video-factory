# Rotation Original Requirement Audit R1

```text
TASK_ID: ROTATION_ORIGINAL_REQUIREMENT_AUDIT
DATE: 2026-07-20
AUDIT_RESULT: CONTRACT_CONFLICT_REQUIRES_USER_DECISION
```

## 1. SOURCE_FILES_READ

| File | Role |
|------|------|
| `GLOBAL_CODEIFICATION_AUDIT_INPUTS/02_phase3_design/PHASE_3_MINIMUM_DESIGN_SPEC_R1.md` | Primary rotation field definition (lines 154-155) |
| `GLOBAL_CODEIFICATION_AUDIT_INPUTS/01_authoritative_requirements/Blender_固定资产模板路线_新对话交接文档_v4.md` | Operational rotation correction value, troubleshooting order |
| `GLOBAL_CODEIFICATION_AUDIT_INPUTS/02_phase3_design/ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md` | Phase 3 contract (rotation listed within facing, line 484) |
| `GLOBAL_CODEIFICATION_AUDIT_INPUTS/02_phase3_design/14B_3A_FINAL_DESIGN_R2.md` | Standing final design (rotation interaction boundary) |
| `protocol_guard/phase3_min/asset_scene_preflight_core.py` | 14A Core rotation schema validation (lines 328-340) |
| `protocol_guard/phase3_min/blender_scene_reader.py` | Blender reader (no rotation runtime implementation) |
| `protocol_guard/phase3_min/asset_scene_preflight_check.py` | Preflight entry point |
| `protocol_guard/phase3_min/tests/test_asset_scene_preflight_core.py` | 14A Core rotation schema tests |
| `reviews/PROJECT_CODEIFICATION_MASTER_MAP.md` | R22 master map |
| `reviews/GLOBAL_CODEIFICATION_AUDIT_REPORT.md` | Global codeification audit |
| `reviews/POST_14B_3B_GLOBAL_REMAINING_REQUIREMENTS_AUDIT_R1_REPORT.md` | Post-facing gap audit |
| `reviews/14B_2D_FORMAL_LOCK_RECORD.md` | Hierarchy lock |
| `reviews/14B_3A_FORMAL_LOCK_RECORD.md` | Standing lock |
| `reviews/14B_3B_FORMAL_LOCK_RECORD.md` | Facing lock |
| `reviews/14B_4A_VISIBILITY_FORMAL_LOCK_RECORD.md` | Visibility lock |
| `reviews/14B_3B_FACING_DESIGN_R2.md` | Facing design R2 |
| `reviews/14B_4A_VISIBILITY_DESIGN_R2.md` | Visibility design R2 |

## 2. FIELD_PROVENANCE_MATRIX

| Requirement | Classification | Source | Evidence |
|------------|---------------|--------|----------|
| Field name: `expected_rotation_euler_deg` | **CONFLICTING** | Design Spec R1 §5.2 line 154 | `"expected_rotation_euler_deg": [0, 0, 0]` — at target top level |
| Field name: `expected_world_rotation_euler_degrees` | **DERIVED_ONLY** | 14A Core line 332 | `r.get("expected_world_rotation_euler_degrees")` — under `rotation` sub-object |
| Field hierarchy: target top-level | **CONFLICTING** | Design Spec R1 §5.2 line 154 | Inline within target object |
| Field hierarchy: `rotation` sub-object | **DERIVED_ONLY** | 14A Core line 329 | `r = t.get("rotation")` |
| Data type: array of 3 numbers | **EXACT_SOURCE** | Design Spec R1 line 154 + 14A Core lines 334-339 | `[0, 0, 0]` example; Core validates `len==3` + numeric + finite |
| Array length: 3 | **EXACT_SOURCE** | Design Spec R1 line 154 + 14A Core line 334 | `len(erw) != 3` validation |
| Units: degrees | **EXACT_SOURCE** | Design Spec R1 line 154 | `expected_rotation_euler_deg` — "deg" suffix |
| Coordinate space: `world` | **UNSUPPORTED** | 14A Core line 332 | `expected_world_rotation_euler_degrees` — "world" in field name, no original spec basis |
| Euler order | **NOT_SPECIFIED** | — | Neither design spec nor 14A Core defines Euler rotation order (XYZ/ZYX/etc.) |
| Blender rotation_mode | **NOT_SPECIFIED** | — | No file specifies whether to use `rotation_euler` or `rotation_quaternion` at the Blender property level |
| `rotation_tolerance_deg` (design) | **CONFLICTING** | Design Spec R1 line 155 | `"rotation_tolerance_deg": 2.0` |
| `rotation_tolerance_degrees` (core) | **DERIVED_ONLY** | 14A Core line 340 | `r.get("rotation_tolerance_degrees")` — renamed "deg"→"degrees" |
| Tolerance type: numeric | **EXACT_SOURCE** | Design Spec R1 line 155 | `2.0` float example |
| Missing/null: NOT_CHECKED | **SUPPORTED_BY_LOCKED_CONTRACT** | 14A Core lines 330-331; Standing/Facing/Visibility pattern | `if r is None: return` + established field group conventions |
| Partial config: all-or-nothing | **NOT_SPECIFIED** | — | No spec or contract defines partial rotation config behavior |
| PASS/FAIL/ERROR/NOT_CHECKED | **SUPPORTED_BY_LOCKED_CONTRACT** | 14A Core general contract | Standing/Facing/Visibility establish overall aggregation pattern |
| Comparison algorithm | **UNSUPPORTED** | ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2 line 484 | "Quaternion distance" mentioned but no algorithm specified |
| Angle wrapping (0-360 vs -180-180) | **NOT_SPECIFIED** | — | No source addresses Euler angle periodicity |
| Non-finite handling | **SUPPORTED_BY_LOCKED_CONTRACT** | 14A Core lines 338-339 | NaN/Inf rejected as ERROR |
| Read error handling | **SUPPORTED_BY_LOCKED_CONTRACT** | Standing/Facing/Visibility patterns | Established ERROR operation pattern |
| Read-only boundary | **SUPPORTED_BY_LOCKED_CONTRACT** | Visibility I2 + Facing I3A scope guard patterns | AST-based enforcement established |
| Per-target aggregation | **SUPPORTED_BY_LOCKED_CONTRACT** | 14A Core `_validate_and_check` + `_check_root_objects` | ERROR>FAIL>PASS pattern |

## 3. FIELD_NAME_AND_HIERARCHY_FINDINGS

### 3.1 Field Name Differences

```
Design Spec R1               14A Core
─────────────────────────────────────────────────────
expected_rotation_euler_deg  →  expected_world_rotation_euler_degrees
rotation_tolerance_deg       →  rotation_tolerance_degrees
(at target top level)        →  (under rotation sub-object)
```

**Issue 1: `world` insertion.** No original spec or locked design document defines "world" as a rotation coordinate space qualifier. The Standing design defines `expected_world_up_axis` and Facing defines `expected_world_forward_axis` — both with explicit `world_` prefix in the design contracts. Rotation's `world_` prefix appeared only in the 14A Core implementation, without any design-level contract authorizing it.

**Issue 2: `deg` → `degrees`.** No formal rename record exists for either field. The change appears mechanical (full word vs abbreviation) but was never documented in a design changelog or contract amendment.

**Issue 3: Hierarchy migration.** The design spec places rotation fields at the target top level (`target.expected_rotation_euler_deg`). 14A Core nests them under `target.rotation.*`. Standing, Facing, and Visibility all use sub-object patterns (`standing.*`, `facing.*`, `visibility.*`), suggesting the 14A Core's nesting is a consistent design decision — but it was never formally documented as a Rotation-specific design change.

### 3.2 Finding

These differences constitute **CONTRACT_CONFLICT**. The 14A Core schema was implemented with field names and hierarchy that differ from the only formal design spec (R1), and no intervening design document records the change formally. The differences may reflect an intentional design evolution (matching the sub-object pattern of Standing/Facing/Visibility) but this was never documented as a rotation-specific decision.

## 4. COORDINATE_SPACE_AND_EULER_ORDER_FINDINGS

| Aspect | Status |
|--------|--------|
| Coordinate space (world vs local) | **UNDERSPECIFIED** — "world" in 14A Core field name implies `matrix_world` decomposition, but design spec has no coordinate space qualifier |
| Euler rotation order (XYZ/ZYX/etc.) | **NOT_SPECIFIED** — neither source defines it. Blender default is XYZ. Comparison without order specification is ambiguous |
| Quaternion vs Euler at runtime | **UNDERSPECIFIED** — Implementation contract mentions "Quaternion distance" (line 484) but 14A Core validates Euler degrees. Blender objects store `rotation_quaternion` (mode=QUATERNION) or `rotation_euler` (mode=XYZ/etc.) |

## 5. TOLERANCE_AND_COMPARISON_FINDINGS

| Aspect | Status |
|--------|--------|
| Tolerance type | **EXACT_SOURCE** — numeric value in degrees, per-axis |
| Comparison algorithm | **UNSUPPORTED** — "Quaternion distance" mentioned but no formula specified |
| Per-axis vs angle-magnitude | **NOT_SPECIFIED** — Design spec implies per-axis Euler comparison; implementation contract mentions quaternion angle. These are incompatible approaches |
| Angle wrapping | **NOT_SPECIFIED** — Euler angles wrap at ±180 or 0-360; no wrapping policy defined |

## 6. LOCKED_BOUNDARY_FINDINGS

Rotation must NOT redefine or expand:

| Boundary | Lock Document | Constraint |
|----------|--------------|------------|
| Root object identification | 14B_2D | Hierarchy determines root via exact name match + scene membership |
| World up axis direction | 14B_3A | Standing validates `local_up_axis → world_up_axis` |
| World forward axis direction | 14B_3B | Facing validates `local_forward_axis → world_forward_axis` |
| hide_viewport / hide_render | 14B_4A | Visibility reads root-only, read-only |
| Result structure (per_target_results) | 14A Core | Overall ERROR>FAIL>PASS, NOT_CHECKED for unconfigured |
| Scope guard pattern | Visibility I2 / Facing I3A | AST-based enforcement of read/write boundaries |

## 7. CONTRACT_CONFLICTS

```text
ISSUE_TYPE: CONTRACT_CONFLICT
CONFLICT_COUNT: 1 (multi-faceted)

CONFLICT_ID: ROT-001
DESCRIPTION: 14A Core rotation schema field names and hierarchy differ from Design Spec R1 without formal change record

SUB_ISSUES:
  ROT-001a: Field name — expected_rotation_euler_deg → expected_world_rotation_euler_degrees
  ROT-001b: Field name — rotation_tolerance_deg → rotation_tolerance_degrees
  ROT-001c: Field hierarchy — target top-level → rotation sub-object
  ROT-001d: "world" qualifier — no formal basis in design spec or locked contracts
```

## 8. UNSUPPORTED_ASSUMPTIONS

| # | Assumption | Where Used | Risk |
|---|-----------|-----------|------|
| 1 | "world" coordinate space is the correct comparison frame | 14A Core field name | Moderate — Standing/Facing use `matrix_world`, consistent but not rotation-specific |
| 2 | `rotation` sub-object pattern is correct | 14A Core hierarchy | Low — consistent with Standing/Facing/Visibility pattern |
| 3 | Euler degrees comparison (per-axis) is the intended algorithm | 14A Core validation | High — implementation contract says "Quaternion distance" |
| 4 | Euler order is XYZ (Blender default) | Implicit | High — comparison without order spec is ambiguous |
| 5 | `degrees` vs `deg` is cosmetic | 14A Core rename | Low — but undocumented |
| 6 | Per-axis tolerance applies independently | Design spec example [0,0,0] + 2.0° | Moderate — no explicit per-axis statement |

## 9. AUDIT_RESULT

```text
AUDIT_RESULT: CONTRACT_CONFLICT_REQUIRES_USER_DECISION
```

The 14A Core rotation schema was implemented with field names and hierarchy that deviate from the only formal design specification (R1). No design changelog or contract amendment records the differences. The changes are consistent with Standing/Facing/Visibility design patterns (sub-object nesting, `world_` prefix) but were never formally authorized for Rotation specifically.

Additionally, two fundamental design questions are unresolved:
1. Euler per-axis comparison vs quaternion angle distance
2. Euler rotation order specification

## 10. UNIQUE_NEXT_ATOMIC_TASK

```text
UNIQUE_NEXT_ATOMIC_TASK: ROTATION_CONTRACT_DECISION
```

User must decide:
1. Whether to ratify the 14A Core field names (`expected_world_rotation_euler_degrees`, `rotation_tolerance_degrees`, under `rotation` sub-object) as the authoritative contract, superseding Design Spec R1
2. Whether Euler per-axis degree comparison or quaternion angle distance is the intended algorithm
3. Whether to specify Euler rotation order explicitly
```

```text
UNSUPPORTED_REQUIREMENT_COUNT: 6
```
