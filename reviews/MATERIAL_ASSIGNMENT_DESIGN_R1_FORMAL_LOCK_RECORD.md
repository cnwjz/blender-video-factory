# Material Assignment Design R1 Formal Lock Record

```text
DOCUMENT_ID: MATERIAL_ASSIGNMENT_DESIGN_R1_FORMAL_LOCK_RECORD
TASK_ID: MATERIAL_ASSIGNMENT_DESIGN_FORMAL_LOCK_SYNC
DESIGN_VERSION: R1
DESIGN_FILE: reviews/MATERIAL_ASSIGNMENT_DESIGN_R1.md
DESIGN_SHA256: D1C6BCCF56A726A8BA8C6CB04A99D967A44ED41A1958527B4B9B743F51049E6C
SOURCE_MASTER_MAP_VERSION: R63
TARGET_MASTER_MAP_VERSION: R64
LOCK_BASIS: USER_FORMAL_APPROVAL
LOCK_APPROVAL_DATE: 2026-07-25
INDEPENDENT_REVIEW_STATUS: ALL_CHECKS_PASS
TRUE_BLOCKING_ISSUES: 0
FORMALLY_LOCKED: TRUE
```

## Locked Scope

```text
1. 配置字段和启用语义 (require_material_assignment_presence, §3)
2. target.geometry_scope 来源及三个枚举值 (SELF_MESH / DESCENDANT_MESHES / SELF_AND_DESCENDANT_MESHES, §5)
3. Scene 对象物化、root 独立解析和 geometry scope 算法 (§6)
4. material_slots 和 slot.material 的 PASS / FAIL / ERROR / NOT_CHECKED 语义 (§7, §8)
5. failure_code、结果字典精确键集合和稳定排序 (§8, §9)
6. 恰好 7 个 ERROR operation (§10)
7. 属性读取次数与缓存合同 (§11, §12)
8. _check_material_assignment(scene, target, per_target_result) 函数边界 (§14)
9. open_blend_and_get_scene 中的集成顺序 (§14)
10. AST Scope Guard 边界 (§15)
11. I1、I2、I3、I4A、I4B、E 实施拆分 (§20)
12. 保存重开持久化仍为 DEFER_REQUIRES_STATE (§19)
```

## Boundaries

```text
本次锁定只锁定 Material Assignment Design R1。
不代表 Material Assignment 生产实现已经完成。
不代表 Material Assignment 字段组最终锁定。
不授权修改其他已锁定字段组。
LOCKED_TASKS_MUST_NOT_BE_REDESIGNED: TRUE
FUTURE_CHANGES_REQUIRE_NEW_EXPLICIT_TASK_AND_REVIEW: TRUE
IMPLEMENTATION_AUTHORIZED: FALSE
```
