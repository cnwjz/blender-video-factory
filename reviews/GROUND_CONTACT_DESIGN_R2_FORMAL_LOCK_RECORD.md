# Ground Contact Design R2 正式锁定记录

```text
DOCUMENT_ID: GROUND_CONTACT_DESIGN_R2_FORMAL_LOCK_RECORD
TASK_ID: GROUND_CONTACT_DESIGN_R2_FORMAL_LOCK_SYNC
MASTER_MAP_VERSION: R76
LOCKED_DESIGN_FILE: reviews/GROUND_CONTACT_DESIGN_R1.md
LOCKED_DESIGN_VERSION: R2
USER_FORMAL_LOCK_APPROVAL: TRUE
LOCK_APPROVAL_DATE: 2026-07-26
INDEPENDENT_REVIEW_STATUS: ALL_CHECKS_PASS_WITH_NONBLOCKING_NOTES
TRUE_BLOCKING_ISSUES: 0
FORMALLY_LOCKED: TRUE
IMPLEMENTATION_AUTHORIZED: FALSE
```

## 用户批准

```text
用户于 2026-07-26 明确批准正式锁定 Ground Contact Design R2。
```

## GPT 独立审核结论

```text
DESIGN_REVIEW_STATUS: ACCEPTED_WITH_NONBLOCKING_NOTES
TRUE_BLOCKING_ISSUES: 0
```

## 锁定范围

```text
1. 配置启用语义:
   all-or-nothing 模型，恰好一个字段为非 None → pre-open INPUT ERROR

2. root 前置语义:
   Ground Contact 只读取已有 checks.object_exists 和 checks.object_type，
   不修改 _check_root_objects

3. target.geometry_scope 复用:
   SELF_MESH / DESCENDANT_MESHES / SELF_AND_DESCENDANT_MESHES

4. evaluated depsgraph 数据链:
   depsgraph → evaluated_get → to_mesh → matrix_world → vertices → to_mesh_clear

5. world-space lowest_z 聚合:
   所有 geometry scope MESH 对象的全局最小 world-space Z

6. to_mesh_clear 清理合同:
   每个成功 to_mesh 的 MESH 在 finally 中恰好一次 to_mesh_clear；
   to_mesh 未成功则 0 次

7. PASS / FAIL / ERROR / NOT_CHECKED 完整矩阵

8. failure_code 封闭集合 (3 个):
   GROUND_CONTACT_OUT_OF_TOLERANCE
   NO_EVALUATED_GEOMETRY
   NON_FINITE_EVALUATED_VERTEX_Z

9. ERROR operation 封闭集合 (12 个):
   READ_SCENE_OBJECTS, RESOLVE_ROOT_OBJECT,
   READ_ROOT_CHILDREN, READ_DESCENDANT_CHILDREN, READ_DESCENDANT_TYPE,
   GET_EVALUATED_DEPSGRAPH, EVALUATED_GET, TO_MESH, TO_MESH_CLEAR,
   READ_EVALUATED_MATRIX_WORLD, READ_MESH_VERTICES,
   TRANSFORM_VERTEX_TO_WORLD_SPACE

10. 结果字典:
    6 种唯一键集合 (NOT_CHECKED / PASS / FAIL(TOLERANCE) /
    FAIL(NO_GEOM) / FAIL(NON_FINITE) / ERROR)

11. 集成位置:
    _check_ground_contact(scene, target, per_target_result)
    open_blend_and_get_scene per-target 循环: animation_state →
    material_assignment → ground_contact → collection_membership

12. 副作用边界:
    无保存、无渲染、无 transform 修改、无场景副作用

13. 精简实施路径:
    GROUND_CONTACT_IMPLEMENTATION → GROUND_CONTACT_BLENDER_VALIDATION →
    GROUND_CONTACT_FINAL_REGRESSION
    Scope Guard: DEFERRED_NON_BLOCKING_ITEM
```

## DEFERRED_NON_BLOCKING_ITEMS

```text
DEFERRED_NON_BLOCKING_ITEM_1:
COMPUTE_LOWEST_Z 不设置独立 ERROR operation；
普通 NaN/Infinity 继续按照 NON_FINITE_EVALUATED_VERTEX_Z 处理。

DEFERRED_NON_BLOCKING_ITEM_2:
defensive root 重新解析分支属于正常同步执行路径之外的防御逻辑，
不为此继续创建设计修正任务。
```

## 锁定边界

```text
本次只锁定 Ground Contact Design R2。

本次不代表:
  — Ground Contact 生产实现已经开始
  — GROUND_CONTACT_IMPLEMENTATION 已获得实施授权
  — Ground Contact 字段组已经完成
  — Ground Contact 字段组已经最终正式锁定

LOCKED_TASKS_MUST_NOT_BE_REDESIGNED: TRUE
FUTURE_CHANGES_REQUIRE_NEW_EXPLICIT_TASK_AND_REVIEW: TRUE
IMPLEMENTATION_AUTHORIZED: FALSE

不得修改:
  — 14A Core schema
  — _check_root_objects
  — 任何既有锁定字段组
  — PROJECT_CODEIFICATION_MASTER_MAP.md (除授权状态同步外)
  — CLAUDE.md
```

## 锁定不包含

```text
— 生产实现代码
— 运行时测试
— Blender 验证
— Scope Guard 实现
— 真实项目 .blend 验证
— 渲染
— Ground Contact 字段组最终锁定
```
