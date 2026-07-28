# Post-14B-3B Global Remaining Requirements Audit R1

```text
TASK_ID: POST_14B_3B_GLOBAL_REMAINING_REQUIREMENTS_AUDIT_R1
DATE: 2026-07-18
BASELINE: PROJECT_CODEIFICATION_MASTER_MAP.md R15
```

## 1. Locked — No Action Required

```text
14A Core
14B-1 Scene basic read
14B-2A Root object existence + type
14B-2B Direct children
14B-2C Descendants
14B-2D Descendant types
14B-3A Standing Up Axis
14B-3B Facing Forward Axis
```

## 2. Master Map Stale References (R15 needs cleanup)

These sections are out of date with R15 Facing LOCKED status:

| Section | Issue | Fix |
|---------|-------|-----|
| §6 table row 1 | facing marked `DESIGN_LOCKED` | Should be `LOCKED` |
| §9 "完全锁定" count | 2 | Should be 3 (hierarchy, standing, facing) |
| §9 "运行时尚未开始" count | 8 | Should be 7 (facing removed) |
| §10 progress text | References outdated facing design-only status | Should note facing fully locked |

Not blocking — cosmetic discrepancies. Safe to fix during next master map update.

## 3. Remaining Asset Scene Preflight Field Groups

All have 14A schema validation already. Need Blender Reader runtime:

| Priority | Field | Schema | Complexity | Core bpy reads |
|----------|-------|--------|------------|----------------|
| 1 | visibility | SCHEMA_ONLY | Low | `hide_viewport`, `hide_render` |
| 2 | rotation | SCHEMA_ONLY | Medium | `rotation_quaternion` / `rotation_euler` |
| 3 | animation_state | SCHEMA_ONLY | Medium | `animation_data`, `action` |
| 4 | material_assignment | SCHEMA_ONLY | Medium | `material_slots` |
| 5 | collection_rules | SCHEMA_ONLY | Medium | `bpy.data.collections`, `users_collection` |
| 6 | ground_contact | SCHEMA_ONLY | High | evaluated depsgraph, `to_mesh` |
| 7 | camera_check | SCHEMA_ONLY | High | `world_to_camera_view` |
| 8 | projection_groups | SCHEMA_ONLY | High | evaluated bbox, projection groups |

## 4. Independent Checker

| Checker | Status |
|---------|--------|
| blender_output_artifact_check | NOT_STARTED |

## 5. Deferred Items (correctly categorized)

```text
HISTORICAL TEST HARNESS: ACTIVE_NONBLOCKING_LEGACY_TEST, PRIORITY LOW
REAL PROJECT .BLEND VALIDATION: DEFERRED
RENDER / SAVE: FORBIDDEN unless explicitly authorized
```

## 6. Missing from Master Map

None found. All 11 field groups + 1 output checker are listed.

## 7. Unsupported Master Map Items

None. All listed items have original requirement backing.

## 8. Conflicts

| Location | Conflict | Resolution |
|----------|----------|------------|
| §6 row 1 | facing `DESIGN_LOCKED` vs R15 `LOCKED` | Update to LOCKED (cosmetic) |
| §9 counts | 2 locked / 8 remaining vs reality 3 locked / 7 remaining | Update counts (cosmetic) |

No structural conflicts.

## 9. Recommendation

Start with **visibility** — the lowest-complexity remaining field group. It reads only `hide_viewport` and `hide_render` (two boolean attributes on Blender objects). This provides a quick win and establishes a clean pattern for the medium and high complexity groups.

```text
REMAINING_REQUIREMENT_COUNT: 9 (8 field groups + 1 output checker)
MISSING_FROM_MASTER_MAP_COUNT: 0
UNSUPPORTED_MASTER_MAP_ITEM_COUNT: 0
CONFLICT_COUNT: 0 (2 cosmetic staleness items, not structural)
```
