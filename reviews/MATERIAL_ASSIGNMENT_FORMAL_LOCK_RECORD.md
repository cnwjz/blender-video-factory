# Material Assignment 字段组正式锁定记录

```text
TASK_ID: MATERIAL_ASSIGNMENT_FORMAL_LOCK_SYNC
FIELD_GROUP: material_assignment
DESIGN_VERSION: R1
LOCK_STATUS: FORMALLY_LOCKED
LOCK_BASIS: USER_FORMAL_APPROVAL
LOCK_APPROVAL_DATE: 2026-07-25
MASTER_MAP_VERSION_AFTER_SYNC: R70
```

## 用户批准

```text
用户于 2026-07-25 明确批准正式锁定 Material Assignment 字段组。
```

## 锁定前置条件

```text
Material Assignment Design R1 已正式锁定。

I1: COMPLETED_AND_INDEPENDENTLY_PASSED
  42 passed, 0 failed

I2: COMPLETED_AND_INDEPENDENTLY_PASSED
  23 passed, 0 failed
  I1 + I2: 65 passed, 0 failed

I3: COMPLETED_AND_INDEPENDENTLY_PASSED
  19 passed, 0 failed
  I1 + I2 + I3: 84 passed, 0 failed

I4A: COMPLETED_AND_INDEPENDENTLY_PASSED
  41 passed, 0 failed
  I1 + I2 + I3 + I4A: 125 passed, 0 failed

I4B: COMPLETED_AND_INDEPENDENTLY_PASSED
  Blender 5.1.2
  6 pytest tests passed
  12/12 temporary Blender scenarios passed
  Blender exit code 0

E: COMPLETED_AND_INDEPENDENTLY_PASSED
  Material Assignment focused: 131 passed, 0 failed
  14A Core: 139 passed, 0 failed
  Full protocol_guard:
    1482 collected
    1480 passed
    0 failed
    2 skipped
    exit code 0

TRUE_BLOCKING_ISSUES_AT_LOCK: 0
PRODUCTION_DEFECTS_AT_LOCK: 0
MATERIAL_ASSIGNMENT_REGRESSION_DEFECTS_AT_LOCK: 0
```

## 锁定能力

```text
target.material_assignment.require_material_assignment_presence

geometry_scope:
  SELF_MESH
  DESCENDANT_MESHES
  SELF_AND_DESCENDANT_MESHES

检查 geometry scope 内的每个 MESH。
每个被检查 MESH 必须：
  - 至少存在一个 material slot
  - 每个 slot.material 均不是 None

支持: PASS / FAIL / ERROR / NOT_CHECKED

支持:
  per_mesh 结果
  缺失 slot index 记录
  多 MESH 聚合
  target overall 重算
  Scene 外分支排除
  与 Standing、Facing 等其他检查独立共存
```

## 锁定边界

```text
本次锁定不包含:
  - 材质视觉质量
  - Shader Node 正确性
  - 贴图文件是否存在
  - Image datablock 内容
  - 渲染外观
  - 材质命名规范
  - 保存并重新打开 .blend 后的持久化验证
  - 真实项目 .blend 验证
  - 渲染验证
  - 通用 Python 静态分析器能力
  - 任意深度 helper 或完整函数数据流分析
```

## 运行安全事实

```text
REAL_PROJECT_BLEND_OPENED: FALSE
REAL_PROJECT_BLEND_MODIFIED: FALSE
TEMPORARY_TEST_BLEND_SAVED: FALSE
RENDER_RUN: FALSE
```

## 锁定后规则

```text
Material Assignment 已正式锁定。

后续不得:
  - 重新设计锁定字段
  - 扩大锁定语义
  - 因理论静态分析绕法重新打开 I4A
  - 因非阻断测试增强重新打开字段组

只有以下情况允许提出解锁或修正:
  - 生产代码存在真实错误
  - 锁定能力与实际行为相反
  - 新需求经过用户明确批准
  - 与其他正式锁定合同发生真实冲突
```
