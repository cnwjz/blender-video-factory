# 14B-3B Facing 需求审计 R2B1

```text
TASK_ID: 14B_3B_DESIGN_R2B1
DATE: 2026-07-18
BASELINE: d44679fc11c5069a17277395bb6c52b5a6dfc799
AUDIT_TYPE: REQUIREMENT_EVIDENCE_AND_MATH_CORRECTION
PRIOR_REVISIONS: R1, R2A, R2B
```

## 1. 原始需求证据

来源: `Blender_固定资产模板路线_新对话交接文档_v4.md`（项目根目录及 `GLOBAL_CODEIFICATION_AUDIT_INPUTS/01_authoritative_requirements/`）

### 1.1 直接朝向/face +Y 要求（可代码化）

以下三处原文直接、明确地要求检查 `face +Y`：

| # | 位置 | 原文 | 证据类型 |
|---|------|------|---------|
| E1 | line 721 | `人物正面方向符合库内记录（face +Y）` | **直接检查要求** — 验证当前 .blend 中人物的正面方向为 +Y |
| E2 | line 1189 | `检查层级、站立状态、face +Y、1.75 高度、脚底接触和游离 Mesh` | **直接检查要求** — face +Y 列为结构化检查步骤之一 |
| E3 | line 1388 | `正面方向 face +Y` | **直接检查要求** — 在技术报告的检查点列表中明确列出 |

这三处直接对应 `local_forward_axis` 和 `expected_world_forward_axis` 字段。代码化实现：将角色的本地正面轴转换为世界方向，与 `+Y`（或 spec 中配置的方向）比较角度。

### 1.2 流程背景证据（非直接检查字段）

| # | 位置 | 原文 | 证据类型 |
|---|------|------|---------|
| E4 | line 350 | `单角色朝向验证` | 流程步骤 — 朝向验证是流水线步骤名称 |
| E5 | line 423 | `角色资产在进入场景前，没有完成孤立结构验证、朝向验证` | 失败分析 — 缺少朝向验证列为根因 |
| E6 | line 341 | `人物站立、朝向、层级、比例没有通过时，禁止调整正式相机` | 门禁规则 — 朝向是前置条件 |
| E7 | line 666 | `五个角色朝向统一（face +Y）` | 定量要求 — 全部角色统一 face +Y |

E4-E7 为 E1-E3 提供流程上下文和设计动机，但不直接定义检查字段或判定逻辑。

### 1.3 容差字段的来源

原始 v4 文档直接规定了朝向目标（`face +Y`），但**未**定义数值容差概念。`facing_tolerance_degrees` 来自当前已锁定 14A Core schema (`asset_scene_preflight_core.py` `_check_tolerance`)，其作用是提供可重复、无歧义的角度判定阈值。容差的引入是实现层面的工程决策，不改变原始要求的语义。

### 1.4 "锁定后朝向不变"需求（超出范围）

| # | 位置 | 原文 | 分类 |
|---|------|------|------|
| E8 | line 1252 | `全部人物的位置、姿势和朝向` | DEFER_REQUIRES_STATE |
| E9 | line 1290 | `人物位置、姿势和朝向` | DEFER_REQUIRES_STATE |
| E10 | line 1486 | `全部人物位置、姿势和朝向` | DEFER_REQUIRES_STATE |
| E11 | line 1529 | `人物位置、姿势与朝向` | DEFER_REQUIRES_STATE |
| E12 | line 1550 | `位置与朝向不变` | DEFER_REQUIRES_STATE |

**分类理由**: 判定"不变"需要历史基准（之前的 spec 快照或帧间比较）。当前 Facing 检查只能判定当前朝向是否符合 spec 容差，不能判定是否与过去一致。历史一致性验证超出 asset_scene_preflight 单帧检查范围。

## 2. `to_3x3()` 的数学语义

### 2.1 什么是 `to_3x3()`

`mathutils.Matrix.to_3x3()` 提取 4x4 世界矩阵的左上 3x3 子矩阵。该子矩阵包含完整的**线性变换**部分：

```text
T_3x3 = R * S
```

其中 R 是旋转分量，S 是缩放/剪切分量的组合。`to_3x3()` **保留旋转、均匀缩放、非均匀缩放、负缩放和剪切**。不执行任何分解、去缩放或正交化。

### 2.2 `to_3x3()` 保留的内容

| 变换类型 | 示例矩阵 | 对 `+Y` forward 的影响 | 角度变化 |
|---------|---------|----------------------|---------|
| 恒等 | diag(1,1,1) | (0,1,0) → (0,1,0) | 0deg |
| 旋转 90deg X | rot_x(90deg) | (0,1,0) → (0,0,1) | 90deg |
| 均匀缩放 2x | diag(2,2,2) | (0,1,0) → (0,2,0) → 归一化 → (0,1,0) | 0deg |
| 非均匀缩放 | diag(2,3,4) | (0,1,0) → (0,3,0) → 归一化 → (0,1,0) | 0deg |
| 负缩放 Z | diag(1,1,-1) | (0,1,0) → (0,1,0) | 0deg |
| 负缩放 Y | diag(1,-1,1) | (0,1,0) → (0,-1,0) | 180deg |
| 剪切 ZX | [[1,0,0.5],[0,1,0],[0,0,1]] | (0,1,0) → (0,1,0) | 0deg |
| 剪切 XZ | [[1,0,0],[0,1,0],[0.5,0,1]] | (0,1,0) → (0,1,0) | 0deg |
| 旋转+缩放 | rot_x(90deg) @ diag(2,3,4) | (0,1,0) → (0,0,3) → 归一化 → (0,0,1) | 90deg |

### 2.3 禁止的操作

Facing 设计**明确禁止**对 `to_3x3()` 结果进行以下任何处理：

- 矩阵分解（polar decomposition / SVD）
- 去缩放（removing scale component）
- 正交化（orthogonalization）
- 负缩放修正（negating axes to "fix" negative scale）

**理由**: Standing 已锁定且不执行任何此类操作。Facing 与 Standing 使用相同的变换流水线。对 `to_3x3()` 进行额外处理会导致两个检查产生不一致的世界方向。负缩放产生的 180deg 偏差属于**正确的 FAIL**。

## 3. 配置语义总结

与 R2A/R2B 一致：

| facing 状态 | 14A Schema | Pre-Open | Runtime |
|-------------|-----------|----------|---------|
| 缺失 / null | 无错误 | 跳过 | NOT_CHECKED |
| {} | 轴字段 ERROR | 不执行 | 不执行 |
| 仅一个轴字段 | 缺失轴 ERROR | 不执行 | 不执行 |
| 双轴合法，tolerance 缺失/null | 无错误 | INVALID_FACING_RULE_RELATION | 不执行 |
| 全配置合法 | 无错误 | 通过 | 执行 |

此矩阵从 14A Core 源码逐行追踪得出。
