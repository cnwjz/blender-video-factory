# 14B-3B Facing 需求审计 R2A -- 配置语义修正

```text
TASK_ID: 14B_3B_DESIGN_R2A
DATE: 2026-07-18
BASELINE: d44679fc11c5069a17277395bb6c52b5a6dfc799
AUDIT_TYPE: CONFIGURATION_SEMANTICS_CORRECTION
SUPERSEDES: 14B_3B_FACING_REQUIREMENT_AUDIT.md (R1)
```

## 1. 修正背景

R1 设计错误地假设 Facing 与 Standing 使用相同的 all-or-nothing 预打开校验模式。实际检查 14A Core 源码后发现，两个字段组的 14A schema 验证逻辑不同，因此预打开校验的需求也不同。

## 2. 14A Schema 精确行为（逐行追踪）

文件: `asset_scene_preflight_core.py` `_validate_facing` (lines 317-325)

```python
def _validate_facing(t, i, errs):
    f = t.get("facing")
    if f is None: return
    if not isinstance(f, dict): errs.append(...); return
    if f.get("local_forward_axis") not in AXIS_VALUES:
        errs.append(f"targets[{i}].facing.local_forward_axis must be one of ...")
    if f.get("expected_world_forward_axis") not in AXIS_VALUES:
        errs.append(f"targets[{i}].facing.expected_world_forward_axis must be one of ...")
    _check_tolerance(f, "facing_tolerance_degrees", f"targets[{i}].facing", errs)
```

关键点：

### 2.1 轴字段：无 `is not None` 守卫

```python
if f.get("local_forward_axis") not in AXIS_VALUES:   # None not in set → True → ERROR
```

与 Standing 的区别：

```python
# Standing (line 298):
if s.get("local_up_axis") is not None and s["local_up_axis"] not in AXIS_VALUES:
#                                        ^^^^^^^^^^^^^^^ guards against None
```

这意味着：Facing 的轴字段为 `None` 或缺失 → 14A schema 直接产生 ERROR。Standing 的轴字段为 `None` → 14A schema 跳过，留给 pre-open 处理。

### 2.2 容差字段：`_check_tolerance` 对 None 静默跳过

```python
def _check_tolerance(d, key, prefix, errs):
    v = d.get(key)
    if v is None: return          # ← tolerance None/missing → no 14A error
```

与 Standing 相同。

## 3. 修正后的配置语义矩阵

| facing 状态 | 14A Schema 结果 | Pre-Open 结果 | Runtime |
|-------------|----------------|---------------|---------|
| 缺失 | 无错误 | 跳过 | NOT_CHECKED |
| `null` | 无错误 (`f is None: return`) | 跳过 | NOT_CHECKED |
| `{}` | **2 个 ERROR**（两轴 None∉AXIS_VALUES） | 不执行（errs 非空） | 不执行 |
| `{"local_forward_axis": "+Y"}` | **1 个 ERROR**（expected=None∉AXIS） | 不执行 | 不执行 |
| `{"expected_world_forward_axis": "+Y"}` | **1 个 ERROR**（local=None∉AXIS） | 不执行 | 不执行 |
| `{"local_forward_axis": "+Y", "expected_world_forward_axis": "+Y"}` | **无错误** | **INVALID_FACING_RULE_RELATION** | 不执行 |
| `{"local_forward_axis": "+Y", "expected_world_forward_axis": "+Y", "facing_tolerance_degrees": null}` | **无错误** | **INVALID_FACING_RULE_RELATION** | 不执行 |
| `{"local_forward_axis": "+Y", "expected_world_forward_axis": "+Y", "facing_tolerance_degrees": 0.0}` | 无错误 | 通过 | 执行 |
| `{"local_forward_axis": "+Y", "expected_world_forward_axis": "+Y", "facing_tolerance_degrees": 5.0}` | 无错误 | 通过 | 执行 |
| 轴值非法 (`"W"`, `"up"` 等) | **14A ERROR** | 不执行 | 不执行 |
| tolerance 为 bool/NaN/Inf/<0 | **14A ERROR** | 不执行 | 不执行 |
| facing 为非 dict 非 None | **14A ERROR** | 不执行 | 不执行 |

**核心修正**：Pre-Open 只检查一种情况——两个轴字段都合法（通过 14A 校验）但 `facing_tolerance_degrees` 缺失或为 None。这是 14A schema 无法覆盖的唯一合法-但-不完整配置。

## 4. Pre-Open 函数的精确语义

函数签名：`_validate_facing_forward_axis_rules_preopen(targets)`

只在以下条件全部成立时产生 ERROR：
1. `facing` 是 dict
2. `facing.local_forward_axis in AXIS_VALUES`
3. `facing.expected_world_forward_axis in AXIS_VALUES`
4. `facing` 中无 `facing_tolerance_degrees` 键，或该键的值为 `None`

其他情况一律返回空列表（由 14A schema 覆盖或属于 NOT_CHECKED）。

## 5. 能力边界修正

R1 设计包含了场景级朝向要求（"顾客朝向收银员"、"位置与朝向不变"等）的归类。R2A 明确：

Facing 检查**只能**验证：`root_obj.matrix_world.to_3x3()` 将 `local_forward_axis` 变换后的世界方向与 `expected_world_forward_axis` 的角度差是否在容差内。

**不能**：
- 证明角色位置正确（由 ground_contact 检查 Z，完整位置验证超出范围）
- 证明完整姿势正确（rotation 是独立字段组）
- 证明 Roll（绕 forward axis 的旋转）正确（需要 facing + standing 联合，或额外的 up 参考，不在当前范围内）
- 证明历史状态没有变化（需要帧比较或 checksum）
- 验证角色之间的相对朝向（需要多角色场景上下文）
