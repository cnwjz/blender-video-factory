# Projection Groups Formal Lock Record

```text
DOCUMENT_ID: PROJECTION_GROUPS_FORMAL_LOCK_RECORD
FIELD_GROUP: PROJECTION_GROUPS
TASK_ID: PROJECTION_GROUPS_FORMAL_LOCK_SYNC
DATE: 2026-07-27
FINAL_LOCK_STATUS: COMPLETED_AND_FORMALLY_LOCKED
FINAL_LOCKED: TRUE
FINAL_LOCK_APPROVAL: USER_EXPLICITLY_APPROVED
FINAL_LOCK_APPROVAL_DATE: 2026-07-27
MASTER_MAP_VERSION: R81
DESIGN_VERSION: R3
```

## Lock Authority

```text
USER_FORMAL_APPROVAL: 批准正式锁定 Projection Groups 字段组
LOCK_BASIS: USER_EXPLICIT_APPROVAL
LOCK_DATE: 2026-07-27
```

## Locked Scope

```text
Projection Groups Design R3 (FORMALLY_LOCKED)
  — 10-leaf-field schema (7 direct fields)
  — 6 pre-open validation rules
  — camera lookup contract (reuse Camera Check §6)
  — independent scene cache — no dependency on _target_caches
  — target_ids root precondition check → FAIL ROOT_OBJECT_NOT_FOUND /
    ROOT_OBJECT_TYPE_MISMATCH / ERROR RESOLVE_TARGET_GEOMETRY
  — additional_object_names no-silent-skip → FAIL ADDITIONAL_OBJECT_NOT_FOUND /
    ADDITIONAL_OBJECT_TYPE_MISMATCH
  — id() dedup
  — single depsgraph for all groups
  — evaluated geometry contract (reuse Camera Check §8)
  — to_mesh_clear() in finally block with ERROR priority
  — mesh.vertices iteration exceptions → READ_MESH_VERTICES
  — union world bbox + 8-corner projection
  — world_to_camera_view(scene, camera_obj, Vector(corner_ws))
  — check order: screen bbox → mvc → camera outside bbox
  — require_camera_outside_world_bbox per-axis strict-outside
  — required_screen_bbox mixed axial model (X containment, Y coverage)
  — 12 failure codes, 1 error type, 14 error operations
  — 16-key PASS/FAIL + 6-key ERROR result dicts
  — per_source_summary for both target_ids and additional_object_names
  — scene.objects materialized once
  — projection_group_overall → EXIT_PASS/FAIL/ERROR
  — build_error_result extended with projection_groups parameter
  — early-return ERROR results sorted by (group_id.casefold(), group_id)

Projection Groups I1 (COMPLETED_AND_INDEPENDENTLY_PASSED)
  — _validate_projection_groups_rules_preopen (6 rules)
  — build_error_result extension (projection_groups parameter)
  — _compute_projection_group_overall
  — _validate_and_open_spec integration (pre-open + overall + result builders)
  — open_blend_and_get_scene integration (projection_groups_block parameter)
  — _check_projection_groups entry wiring
  — 43 focused CPython tests (0 failed)

Projection Groups I2 (COMPLETED_AND_INDEPENDENTLY_PASSED)
  — _check_projection_groups full runtime implementation
  — camera_object_name resolution
  — target_ids geometry_scope collection
  — additional_object_names resolution with FAIL paths
  — evaluated geometry iteration (reuse Camera Check pattern)
  — union bbox computation
  — 8-corner projection via world_to_camera_view
  — screen bbox + mvc + camera outside bbox checks
  — per_source_summary
  — 33 focused CPython tests (0 failed)
  — 11 Blender wrapper tests (0 failed)
  — 15/15 Blender 5.1.2 temporary scene scenarios (0 failed)

Projection Groups E (COMPLETED_AND_INDEPENDENTLY_PASSED)
  — Full protocol_guard regression: 1729 collected, 1729 passed, 0 failed,
    0 errors, 0 skipped, exit 0
  — Scope Guard authorization updated (blender_scene_basic.py:
    _check_projection_groups added to matrix_world, eval_apis,
    and world_to_camera_view authorized sets)
  — Cross-test fake module pollution fixed (test_asset_scene_preflight_projection_groups_i2.py)
  — Production defect confirmed: FALSE
```

## Final Results

```text
Projection Groups I1 CPython:            43 passed, 0 failed, exit 0
Projection Groups I2 CPython:            33 passed, 0 failed, exit 0
Projection Groups Blender wrapper:       11 passed, 0 failed, exit 0
Projection Groups Blender scenarios:     15/15 passed
  Blender version:                       5.1.2
14A Core regression:                     139 passed, 0 failed, exit 0
Camera Check regression:                 74 passed, 0 failed, exit 0
Full protocol_guard:                     1729 collected, 1729 passed,
                                         0 failed, 0 errors, 0 skipped, exit 0
REAL_PROJECT_BLEND_OPENED:               FALSE
BLEND_FILES_SAVED:                       FALSE
RENDER_EXECUTED:                         FALSE
TRUE_BLOCKING_ISSUES:                    0
```

## E Correction Note

```text
E 阶段完整回归发现两项测试兼容性问题：

1. 跨测试假模块污染：
   test_asset_scene_preflight_projection_groups_i2.py 的模块级
   bpy_extras/mathutils 假模块被其他测试文件覆盖，导致 SCREEN_BBOX 检验失败。
   通过 autouse fixture 中每次重建假模块解决。

2. Scope Guard 授权遗漏：
   test_asset_scene_preflight_blender_scene_basic.py 的矩阵读写和
   evaluated API 授权集合未包含 _check_projection_groups。
   已将其纳入 matrix_world、eval_apis 和 world_to_camera_view 授权集合。

两项均为测试文件缺陷修复，不涉及生产代码修改。
```

## Frozen Hashes

```text
protocol_guard/phase3_min/asset_scene_preflight_core.py
  SHA256: 93D983D22246F751AEC372B848CD0D30DA3D0659F8A17235F7BBCD4CFCE41FE1

protocol_guard/phase3_min/asset_scene_preflight_check.py
  SHA256: 0AD8A900B87BB617B9AA4A59917E09377BECDE2EF07634A0823DFDF050E8E37B

protocol_guard/phase3_min/blender_scene_reader.py
  SHA256: 2FF7AA1F869349FC81C046EB2AFAD9DC38103C77ECAE11C3ADC7A0B1E7142718

protocol_guard/phase3_min/tests/test_asset_scene_preflight_projection_groups_i1.py
  SHA256: 4CFACD3D94FD600BCB584A7B7A64532D45F67A9BD4AD53ADABD21370B1B96410

protocol_guard/phase3_min/tests/test_asset_scene_preflight_projection_groups_i2.py
  SHA256: 028E58D47D82E5E32FC3BADFB6441239F9143C3AA3D972B7950CD8ACD2C5E738

protocol_guard/phase3_min/tests/blender_projection_groups_validation_runner.py
  SHA256: 836F356ECA1CFD5C71235577EBF3315749CBD5ED05D51D5BFE7C7424B8864CA6

protocol_guard/phase3_min/tests/test_asset_scene_preflight_projection_groups_blender.py
  SHA256: E369FBF3F21BE010082A0186C1113ED51E091D9B9553390C44D615051718C335

protocol_guard/phase3_min/tests/test_asset_scene_preflight_collection_rules_i3.py
  SHA256: 742B3C51C941EE43DE99249788C0C0F6A0D1AA3BC5F23F2EC99C65349DCA7C58

protocol_guard/phase3_min/tests/test_asset_scene_preflight_blender_facing_i3a.py
  SHA256: 8A4518F1B0228557554652A8E2D9B7253EB73BE9AFA5E6441042B0599044F44A

protocol_guard/phase3_min/tests/test_asset_scene_preflight_blender_scene_basic.py
  SHA256: A0B2BF1463F32F615DF893932DC1BABA8DB50EE42EA2CB1B1EDB7F52D76DADA5
```

## Explicit Exclusions

```text
Projection Groups 后续修改必须重新获得用户明确授权。
不得擅自重新设计 R3。
本锁定不授权 blender_output_artifact_check 或其他未开始字段组。

IMPLEMENTATION_AUTHORIZED: FALSE
  — 已被 E 完成替代。后续如需要 I1/I2/E 级别的修改，需新授权。
```

## Lock Effect

```text
Projection Groups 设计、生产实现、测试、Blender 验证和完整回归均已完成
并通过独立审核。用户于 2026-07-27 明确批准正式锁定。

后续修改 Projection Groups 的生产实现、测试或设计合同必须经过新的用户明确授权。
```

---

*Projection Groups formally locked. All stages completed and independently passed.*
