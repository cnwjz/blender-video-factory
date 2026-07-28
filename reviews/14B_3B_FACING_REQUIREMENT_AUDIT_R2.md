# 14B-3B Facing 需求审计 R2（最终版）

```text
TASK_ID: 14B_3B_DESIGN_R2C
DATE: 2026-07-18
BASELINE: d44679fc11c5069a17277395bb6c52b5a6dfc799
AUDIT_TYPE: REQUIREMENT_EXTRACTION_AND_CLASSIFICATION
STATUS: FINAL (merges R2A + R2B1 + R2C)
```

## 1. 原始需求证据

来源: `Blender_固定资产模板路线_新对话交接文档_v4.md`（位于 `GLOBAL_CODEIFICATION_AUDIT_INPUTS/01_authoritative_requirements/`）

### 1.1 直接 face +Y 检查要求

| # | 位置 | 原文 | 类型 |
|---|------|------|------|
| E1 | line 721 | `人物正面方向符合库内记录（face +Y）` | 直接检查要求 |
| E2 | line 1189 | `检查层级、站立状态、face +Y、1.75 高度、脚底接触和游离 Mesh` | 直接检查要求 |
| E3 | line 1388 | `正面方向 face +Y` | 直接检查要求 |

这三处直接规定：验证角色正面方向为 +Y。对应 `local_forward_axis` / `expected_world_forward_axis` 字段。

### 1.2 流程上下文

| # | 位置 | 原文 | 类型 |
|---|------|------|------|
| E4 | line 350 | `单角色朝向验证` | 流水线步骤名 |
| E5 | line 423 | `没有完成孤立结构验证、朝向验证` | 失败分析 |
| E6 | line 341 | `人物站立、朝向、层级、比例没有通过时，禁止调整正式相机` | 门禁规则 |
| E7 | line 666 | `五个角色朝向统一（face +Y）` | 定量要求 |

### 1.3 容差字段来源

原始 v4 文档规定朝向目标（`face +Y`），未定义数值容差。`facing_tolerance_degrees` 来自已锁定 14A Core schema 的 `_check_tolerance`，用于可重复的数值判定。

### 1.4 超出范围

| # | 位置 | 原文 | 分类 |
|---|------|------|------|
| E8-E12 | lines 1252/1290/1486/1529/1550 | 锁定后位置/姿势/朝向不变 | DEFER_REQUIRES_STATE（需历史基准） |

## 2. 14A Schema 行为

文件: `asset_scene_preflight_core.py` `_validate_facing` (lines 317-325)

```python
def _validate_facing(t, i, errs):
    f = t.get("facing")
    if f is None: return                           # facing null -> skip
    if not isinstance(f, dict): errs.append(...); return
    if f.get("local_forward_axis") not in AXIS_VALUES:    # None not in set -> ERROR
        errs.append(...)
    if f.get("expected_world_forward_axis") not in AXIS_VALUES:  # None not in set -> ERROR
        errs.append(...)
    _check_tolerance(f, "facing_tolerance_degrees", ...)  # None -> silently skip
```

关键差异 vs Standing: 轴字段无 `is not None` 守卫，因此 `None` 直接产生 14A ERROR。

## 3. 配置语义矩阵

| facing 状态 | 14A Schema | Pre-Open | Runtime |
|-------------|-----------|----------|---------|
| 缺失 / null | no error | skip | NOT_CHECKED |
| {} | axis ERROR x2 | not reached | not reached |
| 仅一个轴字段 | missing axis ERROR | not reached | not reached |
| 双轴合法，tolerance 缺失/null | no error | INVALID_FACING_RULE_RELATION | not reached |
| 全配置合法 | no error | pass | execute |

## 4. `to_3x3()` 语义

`to_3x3()` 提取 4x4 的左上 3x3，保留**全部**线性分量：旋转、均匀/非均匀缩放、负缩放、剪切。禁止分解、去缩放、正交化、负缩放修正。与 Standing 语义一致。

## 5. 能力边界

Facing **仅**验证: `root_obj.matrix_world.to_3x3()` 将 `local_forward_axis` 变换后的世界方向与 `expected_world_forward_axis` 的角度差是否在容差内。

不验证: 位置、完整姿势、Roll、历史一致性、多角色相对朝向、镜头朝向。
