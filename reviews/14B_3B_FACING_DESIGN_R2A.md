# 14B-3B Facing Forward Axis -- Design R2A

```text
TASK_ID: 14B_3B_DESIGN_R2A
BASELINE: d44679fc11c5069a17277395bb6c52b5a6dfc799
DESIGN_STATUS: READY_FOR_INDEPENDENT_REVIEW
IMPLEMENTATION_AUTHORIZED: FALSE
BLENDER_EXECUTION_AUTHORIZED: FALSE
REAL_PROJECT_BLEND_VALIDATION_AUTHORIZED: FALSE
SUPERSEDES: 14B_3B_FACING_DESIGN_R1.md
```

---

## 一、配置语义（依据 14A schema 实际行为）

### 1.1 字段

| 字段 | 类型 | 14A 校验 |
|------|------|---------|
| `facing.local_forward_axis` | `str` or `None` | `f.get("local_forward_axis") not in AXIS_VALUES` → ERROR（含 None） |
| `facing.expected_world_forward_axis` | `str` or `None` | `f.get("expected_world_forward_axis") not in AXIS_VALUES` → ERROR（含 None） |
| `facing.facing_tolerance_degrees` | `float` or `None` | `_check_tolerance` — None 静默跳过，合法值需 >=0 且有限 |

### 1.2 Pre-Open 校验：`_validate_facing_forward_axis_rules_preopen`

**触发条件（唯一）**：两个轴字段都在 AXIS_VALUES 中，但 `facing_tolerance_degrees` 缺失或为 None。

**因为**：
- 轴字段缺失/None → 14A schema 已产生 ERROR（不同于 Standing 的 `is not None` 守卫）
- 轴字段非法 → 14A schema 已产生 ERROR
- tolerance 非法数值 → 14A schema 已产生 ERROR
- tolerance None → 14A `_check_tolerance` 静默跳过 → **唯一需要 pre-open 填补的空隙**

### 1.3 INVALID_FACING_RULE_RELATION 合同

```text
格式:
  INVALID_FACING_RULE_RELATION: target '<target_id>'
  facing forward_axis missing required fields: ['facing_tolerance_degrees']

缺失字段列表稳定排序: [field.casefold(), field]

写入: input_errors（通过 pre_open_errs.extend()）
退出码: 2
.blend: 不打开
最终输出: sorted(input_errors) 按字典序排列（14A canonicalize）
```

### 1.4 `_validate_and_open` 调用顺序

```python
pre_open_errs  = _validate_direct_child_rules_preopen(targets)      # 1st
pre_open_errs += _validate_standing_up_axis_rules_preopen(targets)   # 2nd
pre_open_errs += _validate_facing_forward_axis_rules_preopen(targets)  # 3rd (new)
if pre_open_errs:
    return (EXIT_ERROR, build_error_result(...))
```

内部收集顺序：direct_child → standing → facing（per `.extend()` 调用顺序）。

最终输出顺序：`canonicalize()` 对 `input_errors` 调用 `sorted(ie)`，即字典序。内部收集顺序不决定最终输出顺序。此行为是 14A 已锁定的标准化规范，所有 pre-open 校验器的错误都受此影响。

---

## 二、能力边界

Facing 检查**仅**验证：

> `root_obj.matrix_world.to_3x3()` 将 `local_forward_axis` 变换后，世界方向与 `expected_world_forward_axis` 的角度差 ≤ `facing_tolerance_degrees`。

**明确排除**：
- 位置验证（XYZ 坐标）
- 完整姿势验证（滚转、其余两轴）
- 历史状态变化检测
- 多角色相对朝向
- 镜头朝向

这些分别属于 ground_contact、rotation、场景级规则或人类判断。

---

## 三、场景失败路径下的 Facing 行为

以下情况 `_check_root_objects` 中 Facing 字段对应的 checks 条目：

### 3.1 Scene 不存在（`scene is None`）

`_check_root_objects` 返回 `[]`。无 target 处理。Facing 不出现。

### 3.2 `scene.objects` 读取失败

`_check_root_objects` line 720-730：checks 仅包含 `object_exists`、`object_type`、`direct_children`。**不含** `descendants`、`standing`、`facing`。

Facing 键缺失 → `checks.get("facing", {}).get("forward_axis", {})` → `result` 为 `None` → `_collect_target_errors` 不收集 facing 错误。

这是**省略**（键不存在），不是 NOT_CHECKED。

当 scope 扩展（添加 standing / facing 到该错误路径的 checks）不应在本设计内处理——这是 `_check_root_objects` 错误路径统一补全的问题，属于独立审计任务。

### 3.3 ROOT_OBJECT_NOT_FOUND

`_check_root_objects` line 741-770：checks 包含 `standing: NOT_CHECKED`。Facing 须以相同模式添加：

```json
{
  "facing": {
    "result": "NOT_CHECKED",
    "forward_axis": {
      "result": "NOT_CHECKED",
      "note": "ROOT_OBJECT_NOT_FOUND"
    }
  }
}
```

### 3.4 ROOT_OBJECT_TYPE_MISMATCH

```json
{
  "facing": {
    "result": "NOT_CHECKED",
    "forward_axis": {
      "result": "NOT_CHECKED",
      "note": "ROOT_OBJECT_TYPE_MISMATCH"
    }
  }
}
```

### 3.5 AMBIGUOUS_ROOT_OBJECT_NAME

```json
{
  "facing": {
    "result": "NOT_CHECKED",
    "forward_axis": {
      "result": "NOT_CHECKED",
      "note": "AMBIGUOUS_ROOT_OBJECT_NAME"
    }
  }
}
```

### 3.6 根对象存在且类型匹配，但 Facing 未配置

```json
{
  "facing": {
    "result": "NOT_CHECKED",
    "forward_axis": {
      "result": "NOT_CHECKED",
      "note": "FORWARD_AXIS_RULES_NOT_CONFIGURED"
    }
  }
}
```

---

## 四、R1 设计中保留的内容

以下 R1 设计不受本次修正影响，原样保留：

| 内容 | 状态 |
|------|------|
| 矩阵读取策略 A（独立读取） | 保留 |
| `matrix_world` 每个检查函数内最多读取一次 | 保留 |
| `to_3x3()` 每个检查函数内最多调用一次 | 保留 |
| 独立执行（不受其他检查结果影响） | 保留 |
| Target overall：ERROR > FAIL > PASS | 保留 |
| 结果嵌套路径：`checks.facing.forward_axis` | 保留 |
| PASS/FAIL 完整字段 | 保留 |
| ERROR 时省略正常结果字段 | 保留 |
| 五个 ERROR operation（名称调整为 forward 系） | 保留 |
| `_collect_target_errors` 扩展格式 | 保留 |
| 后续阶段拆分（I1/I2/I3/E） | 保留（实现时重新确认） |
