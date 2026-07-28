# 14B-3B Facing 需求审计

```text
TASK_ID: 14B_3B_FACING_REQUIREMENT_AUDIT
DATE: 2026-07-18
BASELINE: d44679fc11c5069a17277395bb6c52b5a6dfc799
AUDIT_TYPE: REQUIREMENT_EXTRACTION_AND_CLASSIFICATION
```

## 1. 审计范围

审计了原始有效需求文档 `Blender_固定资产模板路线_新对话交接文档_v4(6).md` 中所有与 Facing（朝向）相关的要求，并对照 14A Core 当前 schema 实现。

## 2. 14A Core Schema 现状

文件: `protocol_guard/phase3_min/asset_scene_preflight_core.py` lines 317-325

### 2.1 字段定义

| 字段路径 | 类型 | 有效值 | 验证逻辑 |
|----------|------|--------|---------|
| `facing.local_forward_axis` | string | AXIS_VALUES: +X,-X,+Y,-Y,+Z,-Z | 非 None 时必须为合法轴名 |
| `facing.expected_world_forward_axis` | string | AXIS_VALUES: +X,-X,+Y,-Y,+Z,-Z | 非 None 时必须为合法轴名 |
| `facing.facing_tolerance_degrees` | number | 有限、非负、非布尔 | `_check_tolerance` 验证 |

### 2.2 Schema 级别行为

- `facing` 为 `None` → 跳过验证，不报错
- `facing` 不是 dict → ERROR: `targets[i].facing must be an object`
- 单个字段为 `None` → 14A schema **不报错**，该字段被跳过（与 standing 不同，standing 是 pre-open 阶段处理部分配置）
- 非法轴名 → ERROR: `targets[i].facing.<field> must be one of [+X, -X, +Y, -Y, +Z, -Z]`
- 0.0 容差 → **合法**（`_check_tolerance` 允许 0.0，检查 `x >= 0`）

### 2.3 与 Standing 的关键差异

| 方面 | Standing | Facing |
|------|----------|--------|
| 字段组 | `local_up_axis`, `expected_world_up_axis`, `up_axis_tolerance_degrees` | `local_forward_axis`, `expected_world_forward_axis`, `facing_tolerance_degrees` |
| 部分配置 | pre-open 校验拦截 (INVALID_UP_AXIS_RULE_RELATION) | 14A schema 不拦截 |
| 零容差 | 合法 | 合法 |
| `_check_tolerance` | 使用 | 使用 |

## 3. 原始文档 Facing 要求提取

### 3.1 可代码化的要求

| # | 原始描述 | 代码化方案 |
|---|---------|-----------|
| R1 | "五个角色朝向统一（face +Y）" (line 666) | `local_forward_axis = "+Y"`, `expected_world_forward_axis = "+Y"`，PASS/FAIL 基于角度 |
| R2 | "单角色朝向验证" (line 350) | 同 R1，作为 Asset Scene Preflight 检查的一部分 |
| R3 | "角色资产在进入场景前没有完成孤立结构验证、朝向验证" (line 423) | Facing 检查作为 preflight 的一部分，必须在进入场景前执行 |
| R4 | "全部人物的位置、姿势和朝向" (line 1252, 1290, 1486, 1529) — 锁定后禁止修改 | Facing 检查验证当前朝向是否符合 spec，任何变化会被检测 |

### 3.2 不可可靠代码化的要求

| # | 原始描述 | 分类 | 理由 |
|---|---------|------|------|
| D1 | "顾客朝向收银员" (line 997-998) | DEFER_REQUIRES_STATE | 需要知道顾客和收银员的场景位置来计算相对方向，超出单角色预检范围 |
| D2 | "收银员朝向顾客" (line 998) | DEFER_REQUIRES_STATE | 同上 |
| D3 | "不允许顾客朝向镜头" (line 1003) | DEFER_REQUIRES_STATE | 需要相机位置信息 |
| D4 | "顾客朝向对应收银通道" (line 1237, 1459) | DEFER_REQUIRES_STATE | 需要场景布局上下文 |
| D5 | "人物站立、朝向、层级、比例没有通过时，禁止调整正式相机" (line 341) | DOCUMENT_ONLY | 工作流规则，由人执行 |
| D6 | "位置与朝向不变" (line 1550) | HUMAN_JUDGMENT_ONLY | 需要视觉比较（两帧之间），非自动可判定 |
| D7 | "五个固定角色 Collection 能否在新场景中稳定 Append 并保持朝向状态" (line 1361) | DOCUMENT_ONLY | Append 行为验证，非 preflight 职责 |

## 4. 需求-实现差距

### 4.1 Schema 已完成

- 三个字段的类型和值范围验证（14A Core）
- 容差的数值合法性验证

### 4.2 待实现（运行时）

- 读取 `matrix_world` 并提取 3x3 旋转矩阵
- 将 `local_forward_axis` 通过矩阵转换到世界空间
- 与 `expected_world_forward_axis` 比较角度
- PASS/FAIL/NOT_CHECKED 判定
- 五个运行时 ERROR operation 边界
- `_collect_target_errors` 扩展
- Real Blender mathutils 边界测试

## 5. 冲突与裁决

无文档冲突。原始文档中 "face +Y" 是唯一的明确单角色朝向要求，与 schema 的 `local_forward_axis` / `expected_world_forward_axis` 设计一致。

## 6. 审计结论

Facing 的代码化范围明确且有限：
- **可代码化**: 单个角色的 `local_forward_axis` 到 `expected_world_forward_axis` 的矩阵转换和角度比较
- **不可代码化**: 场景级角色之间的相对朝向、镜头朝向、工作流规则
- **数学算法**: 与 Standing 相同（matrix_world.to_3x3() 旋转、归一化、acos 角度），差异仅为轴名语义不同
