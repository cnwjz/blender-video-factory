# Rotation Original Requirement Audit R2

```text
TASK_ID: ROTATION_ORIGINAL_REQUIREMENT_AUDIT_R2_CORRECTION
DATE: 2026-07-20
AUDIT_RESULT: CONTRACT_CONFLICT_REQUIRES_USER_DECISION
```

## 1. SOURCE_FILES_READ

| File | Role |
|------|------|
| `GLOBAL_CODEIFICATION_AUDIT_INPUTS/02_phase3_design/PHASE_3_MINIMUM_DESIGN_SPEC_R1.md` | Primary rotation field definition (§5.2 lines 154-155) |
| `GLOBAL_CODEIFICATION_AUDIT_INPUTS/01_authoritative_requirements/Blender_固定资产模板路线_新对话交接文档_v4.md` | Operational rotation correction value, world-space rotation rule, troubleshooting order |
| `GLOBAL_CODEIFICATION_AUDIT_INPUTS/02_phase3_design/ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md` | Phase 3 contract (line 484: "Facing and rotation (Quaternion distance)") |
| `GLOBAL_CODEIFICATION_AUDIT_INPUTS/02_phase3_design/14B_3A_FINAL_DESIGN_R2.md` | Standing final design |
| `protocol_guard/phase3_min/asset_scene_preflight_core.py` | 14A Core: `_validate_rotation` (lines 328-340), `quaternion_min_angle_degrees` (lines 501-521) |
| `protocol_guard/phase3_min/blender_scene_reader.py` | Blender reader (no rotation runtime) |
| `protocol_guard/phase3_min/asset_scene_preflight_check.py` | Preflight entry point |
| `protocol_guard/phase3_min/tests/test_asset_scene_preflight_core.py` | 14A Core rotation schema tests |
| `reviews/PROJECT_CODEIFICATION_MASTER_MAP.md` | R22 master map |
| `reviews/GLOBAL_CODEIFICATION_AUDIT_REPORT.md` | Global codeification audit |
| `reviews/POST_14B_3B_GLOBAL_REMAINING_REQUIREMENTS_AUDIT_R1_REPORT.md` | Post-facing gap audit |
| Lock records: 14B_2D, 14B_3A, 14B_3B, 14B_4A | Hierarchy, Standing, Facing, Visibility locks |
| Design documents: 14B_3B_FACING_DESIGN_R2.md, 14B_4A_VISIBILITY_DESIGN_R2.md | Facing and Visibility design contracts |

## 2. FIELD_PROVENANCE_MATRIX

| Requirement | Classification | Source | Evidence |
|------------|---------------|--------|----------|
| Field name: `expected_rotation_euler_deg` | **CONFLICTING** | Design Spec R1 §5.2 line 154 | `"expected_rotation_euler_deg": [0, 0, 0]` — at target top level |
| Field name: `expected_world_rotation_euler_degrees` | **DERIVED_ONLY** | 14A Core line 332 | `r.get("expected_world_rotation_euler_degrees")` — under `rotation` sub-object |
| Field hierarchy: target top-level | **CONFLICTING** | Design Spec R1 §5.2 line 154 | Inline within target object |
| Field hierarchy: `rotation` sub-object | **DERIVED_ONLY** | 14A Core line 329 | `r = t.get("rotation")` |
| "world" qualifier in field name | **SUPPORTED_BY_LOCKED_CONTRACT** | V4 lines 239-241 + Standing/Facing designs | V4: "世界旋转只写 Top Empty"; Standing: `expected_world_up_axis`; Facing: `expected_world_forward_axis` |
| Data type: array of 3 numbers | **EXACT_SOURCE** | Design Spec R1 line 154 + 14A Core lines 334-339 | Example `[0, 0, 0]`; Core validates `len==3`, numeric, finite |
| Array length: 3 | **EXACT_SOURCE** | Design Spec R1 line 154 + 14A Core line 334 | `len(erw) != 3` validation |
| Units: degrees | **EXACT_SOURCE** | Design Spec R1 line 154 + 14A Core line 332 | "deg"/"degrees" in field names |
| Euler order (expected conversion) | **NOT_SPECIFIED** | — | No source defines Euler rotation order for converting expected Euler to quaternion |
| World quaternion read/convert method | **NOT_SPECIFIED** | — | No source defines how `matrix_world` yields a rotation quaternion at runtime |
| Blender rotation_mode | **NOT_SPECIFIED** | — | No source specifies `rotation_euler` vs `rotation_quaternion` preference |
| `rotation_tolerance_deg` (design) | **CONFLICTING** | Design Spec R1 line 155 | `"rotation_tolerance_deg": 2.0` |
| `rotation_tolerance_degrees` (core) | **DERIVED_ONLY** | 14A Core line 340 | `r.get("rotation_tolerance_degrees")` |
| Tolerance type: finite non-negative numeric | **EXACT_SOURCE** | 14A Core `_check_tolerance` | Shared `_check_tolerance` enforces finite, non-negative numeric |
| Tolerance units: degrees | **EXACT_SOURCE** | Design Spec R1 line 155 + 14A Core | Used in `quaternion_min_angle_degrees` which returns degrees |
| Comparison algorithm: quaternion minimum angle | **SUPPORTED_BY_LOCKED_CONTRACT** | Implementation Contract R2 line 484 + 14A Core lines 501-521 | R2: "Quaternion distance"; Core: `quaternion_min_angle_degrees(normalize → abs(dot) → clamp → 2*degrees(acos(dot)))` |
| Rotation missing/null in schema | **EXACT_SOURCE** | 14A Core line 330 | `if r is None: return` — schema does not error |
| Rotation missing/null: runtime behavior | **NOT_SPECIFIED** | — | No source defines whether runtime outputs NOT_CHECKED for missing rotation |
| Partial configuration semantics | **NOT_SPECIFIED** | — | No source defines behavior when only one of expected/tolerance is set |
| PASS/FAIL/ERROR/NOT_CHECKED aggregation | **SUPPORTED_BY_LOCKED_CONTRACT** | 14A Core general contract | Standing/Facing/Visibility establish ERROR>FAIL>PASS>NOT_CHECKED pattern |
| Failure code | **NOT_SPECIFIED** | — | No source defines rotation-specific failure codes |
| Runtime error type and operation | **NOT_SPECIFIED** | — | No source defines rotation-specific error types or operations |
| Non-finite handling | **SUPPORTED_BY_LOCKED_CONTRACT** | 14A Core lines 338-339 | NaN/Inf rejected |
| Read-only boundary | **SUPPORTED_BY_LOCKED_CONTRACT** | Visibility I2 / Facing I3A | AST-based scope guard pattern established |

## 3. FIELD_NAME_AND_HIERARCHY_FINDINGS

### 3.1 Differences

```
Design Spec R1               14A Core
─────────────────────────────────────────────────────
expected_rotation_euler_deg  →  expected_world_rotation_euler_degrees
rotation_tolerance_deg       →  rotation_tolerance_degrees
(at target top level)        →  (under rotation sub-object)
```

### 3.2 What Has Source Support

- **"world" qualifier**: V4 states "世界旋转只写 Top Empty" (world rotation only written to Top Empty) at line 240. Diagnostic reads `root_matrix_world` (line 609). The character library correction applies `Top Empty rotation_euler = (pi/2, 0, pi)` (line 681). Standing (`expected_world_up_axis`) and Facing (`expected_world_forward_axis`) both use `world_` prefix. The "world" concept for rotation has source basis — specifically that rotation is diagnosed and enforced at the Top Empty in world space.

- **Sub-object pattern**: Standing, Facing, and Visibility all use `target.<field_group>.*` nesting. The 14A Core's `rotation.*` pattern is consistent with all other locked field groups.

- **Quaternion minimum angle**: Implementation Contract R2 line 484 explicitly states "Quaternion distance." 14A Core `quaternion_min_angle_degrees` (lines 501-521) implements the locked formula: normalize both quaternions, abs(dot), clamp to [-1,1], 2*degrees(acos(dot)). This algorithm is locked and not subject to re-litigation.

### 3.3 What Lacks Formal Record

- **Field renaming**: `deg` → `degrees`, no formal changelog
- **Hierarchy migration**: target top-level → `rotation` sub-object, no formal changelog
- The changes are consistent with Standing/Facing/Visibility patterns but were never documented as Rotation-specific decisions

### 3.4 Finding

These differences constitute **CONTRACT_CONFLICT**. The 14A Core schema implements field names and hierarchy that diverge from Design Spec R1. The changes are consistent with established design patterns (sub-object nesting, `world_` prefix, Quaternion distance) but were never formally authorized for Rotation.

## 4. COORDINATE_SPACE_AND_EULER_ORDER_FINDINGS

| Aspect | Status |
|--------|--------|
| World coordinate space principle | **SUPPORTED** — V4 line 240, Standing/Facing world_ patterns |
| Expected Euler → quaternion order | **NOT_SPECIFIED** — no source defines whether conversion uses XYZ, ZYX, or other order |
| Runtime world quaternion extraction | **NOT_SPECIFIED** — no source defines the `matrix_world → quaternion` conversion method |

## 5. SCHEMA_VS_RUNTIME_BOUNDARY

| Aspect | Schema (14A Core) | Runtime (not implemented) |
|--------|-------------------|--------------------------|
| Field structure validation | **IMPLEMENTED** — `_validate_rotation` | — |
| Tolerance validation | **IMPLEMENTED** — `_check_tolerance` | — |
| Quaternion angle computation | **IMPLEMENTED** — `quaternion_min_angle_degrees` | — |
| Missing/null behavior | Schema returns silently | **NOT_SPECIFIED** |
| Partial configuration | **NOT_SPECIFIED** | **NOT_SPECIFIED** |
| Failure codes | — | **NOT_SPECIFIED** |
| Error types/operations | — | **NOT_SPECIFIED** |
| PASS/FAIL/NOT_CHECKED output | — | **NOT_SPECIFIED** (pattern from locked field groups, not rotation-specific) |

## 6. LOCKED_BOUNDARY_FINDINGS

Rotation must NOT redefine or expand:

| Boundary | Lock | Constraint |
|----------|------|------------|
| Root object identification | 14B_2D | Hierarchy determines root via exact name match + scene membership |
| World up axis direction | 14B_3A | Standing validates `local_up_axis → world_up_axis` |
| World forward axis direction | 14B_3B | Facing validates `local_forward_axis → world_forward_axis` |
| hide_viewport / hide_render | 14B_4A | Visibility reads root-only, read-only |
| Result aggregation | 14A Core | ERROR>FAIL>PASS>NOT_CHECKED |
| Scope guard | Visibility I2 / Facing I3A | AST-based read/write boundary enforcement |
| Quaternion distance formula | 14A Core lines 501-521 | normalize → abs(dot) → clamp → 2*degrees(acos(dot)) |

## 7. CONTRACT_CONFLICTS

```text
ISSUE_TYPE: CONTRACT_CONFLICT
CONTRACT_CONFLICT_COUNT: 1 (multi-faceted)

CONFLICT_ID: ROT-001
DESCRIPTION: 14A Core rotation schema field names and hierarchy differ from Design Spec R1 without formal change record, though the design direction is consistent with locked patterns.

SUB_ISSUES:
  ROT-001a: Field name — expected_rotation_euler_deg → expected_world_rotation_euler_degrees
  ROT-001b: Field name — rotation_tolerance_deg → rotation_tolerance_degrees
  ROT-001c: Field hierarchy — target top-level → rotation sub-object
  ROT-001d: "world" qualifier HAS source support (V4 line 240, Standing/Facing patterns)
           but the formal RENAME from spec to implementation lacks a design changelog
```

## 8. UNSUPPORTED_ASSUMPTIONS

| # | Assumption | Risk |
|---|-----------|------|
| 1 | Euler→quaternion conversion uses XYZ order (Blender default) | High — no specification |
| 2 | `matrix_world.to_quaternion()` or equivalent is the correct extraction method | Moderate — implicit from `quaternion_min_angle_degrees` acceptance of 4-tuples |
| 3 | Per-axis Euler degree comparison is NOT the algorithm — quaternion distance is | Low — Implementation Contract R2 confirms Quaternion distance |
| 4 | `degrees` vs `deg` is cosmetic | Low — but undocumented |
| 5 | Sub-object nesting follows Standing/Facing/Visibility pattern intentionally | Low — consistent pattern, no evidence of error |

```text
UNSUPPORTED_REQUIREMENT_COUNT: 5
```

## 9. AUDIT_RESULT

```text
AUDIT_RESULT: CONTRACT_CONFLICT_REQUIRES_USER_DECISION
```

The 14A Core rotation schema was implemented with field names and hierarchy that diverge from Design Spec R1. The direction of change (sub-object nesting, `world_` prefix, Quaternion distance algorithm) is consistent with locked Standing/Facing/Visibility patterns and has partial source support in V4. However, no formal design changelog or contract amendment documents these changes for Rotation specifically.

The Quaternion minimum angle algorithm and tolerance schema are locked in 14A Core and not subject to change. Euler order for expected-value conversion and the runtime world quaternion extraction method remain unspecified and belong to the design phase, not this audit.

## 10. UNIQUE_NEXT_ATOMIC_TASK

```text
UNIQUE_NEXT_ATOMIC_TASK: ROTATION_CONTRACT_DECISION
```

**User must decide:**

Whether to formally ratify the current 14A Core Rotation field names (`expected_world_rotation_euler_degrees`, `rotation_tolerance_degrees`, under `rotation` sub-object) as the authoritative contract, thereby superseding Design Spec R1's `expected_rotation_euler_deg` / `rotation_tolerance_deg` at target top level.

Euler order and world quaternion conversion details are deferred to the design phase and are NOT part of this decision.
```
