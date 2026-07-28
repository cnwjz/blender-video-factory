# Projection Groups Formal Lock Record

```text
DOCUMENT_ID: PROJECTION_GROUPS_FORMAL_LOCK_RECORD
FIELD_GROUP: PROJECTION_GROUPS
TASK_ID: PROJECTION_GROUPS_FORMAL_LOCK_SYNC
DATE: 2026-07-26
FINAL_LOCK_STATUS: FORMALLY_LOCKED
FINAL_LOCKED: TRUE
FINAL_LOCK_APPROVAL: USER_EXPLICITLY_APPROVED
FINAL_LOCK_APPROVAL_DATE: 2026-07-26
MASTER_MAP_VERSION: R80
DESIGN_VERSION: R3
```

## Lock Authority

```text
USER_FORMAL_APPROVAL: 批准正式锁定 Projection Groups Design R3
LOCK_BASIS: USER_EXPLICIT_APPROVAL
LOCK_DATE: 2026-07-26
```

## Locked Scope

```text
Projection Groups Design R3 (FORMALLY_LOCKED)
  — 10-leaf-field schema (7 direct fields)
  — 6 pre-open validation rules
  — camera lookup contract (reuse Camera Check §6)
  — target_ids root failure → FAIL ROOT_OBJECT_NOT_FOUND / ROOT_OBJECT_TYPE_MISMATCH
  — additional_object_names → FAIL ADDITIONAL_OBJECT_NOT_FOUND / ADDITIONAL_OBJECT_TYPE_MISMATCH
  — independent scene cache — no dependency on _target_caches
  — single depsgraph for all groups
  — evaluated geometry (reuse Camera Check §8)
  — union world bbox + 8-corner projection
  — world_to_camera_view(scene, camera_obj, Vector(corner_ws))
  — check order: screen bbox → mvc (matches Camera Check R1 §19 step 6)
  — required_screen_bbox mixed axial model (X containment, Y coverage)
  — require_camera_outside_world_bbox per-axis strict-outside
  — 12 failure codes, 1 error type, 14 error operations
  — 16-key PASS/FAIL + 6-key ERROR result dicts
  — per_source_summary for both target_ids and additional_object_names
  — projection_group_overall → EXIT_PASS/FAIL/ERROR
  — build_error_result extended with projection_groups parameter
  — 3 implementation stages: I1 (pre-open/framework), I2 (Blender runtime), E (regression)
  — ~38 CPython + ~26 Blender test scenarios + 14 ERROR operation coverage

Design R3 closes:
  — DESIGN_FREEDOM_CLOSED_COUNT: 32
  — DOCUMENTATION_GAP_CLOSED_COUNT: 8
  — UNRESOLVED_DESIGN_DECISIONS: 0
  — INTERNAL_CONTRADICTION_COUNT: 0
```

## Explicit Exclusions

```text
IMPLEMENTATION_AUTHORIZED: FALSE
  本次锁定仅授权 Projection Groups Design R3。
  实施 (I1, I2, E) 需要用户新的明确授权。

  不得修改 Camera Check 已锁定内容。
  不得修改 per_target_results 结构。
  不得修改 _check_root_objects 返回值或 _target_caches 逻辑。
```

## Lock Effect

```text
Projection Groups 设计已正式锁定。
实施必须遵守 Design R3。
后续设计修改需要用户新的明确授权。

本锁定不授权任何实施活动。
```

---

*Projection Groups Design R3 formally locked. Awaiting user authorization for I1 implementation.*
