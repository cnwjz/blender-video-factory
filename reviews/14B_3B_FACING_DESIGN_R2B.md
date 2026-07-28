# 14B-3B Facing Forward Axis -- Design R2B

```text
TASK_ID: 14B_3B_DESIGN_R2B
BASELINE: d44679fc11c5069a17277395bb6c52b5a6dfc799
DESIGN_STATUS: READY_FOR_INDEPENDENT_REVIEW
IMPLEMENTATION_AUTHORIZED: FALSE
BLENDER_EXECUTION_AUTHORIZED: FALSE
REAL_PROJECT_BLEND_VALIDATION_AUTHORIZED: FALSE
PRIOR_REVISIONS: R1, R2A
```

R2A 修正了配置语义（14A schema 行为）。R2B 补全原始需求证据、数学边界和矩阵策略确认。

---

## 一、字段合同（R2A 已确定，此处为最终版）

| 字段 | 类型 | 14A 校验 |
|------|------|---------|
| `facing.local_forward_axis` | `str` or `None` | `not in AXIS_VALUES` → ERROR（含 None） |
| `facing.expected_world_forward_axis` | `str` or `None` | `not in AXIS_VALUES` → ERROR（含 None） |
| `facing.facing_tolerance_degrees` | `number or None` | `_check_tolerance` — None 静默跳过 |

### 1.1 INVALID_FACING_RULE_RELATION

```
INVALID_FACING_RULE_RELATION: target '<target_id>' facing forward_axis missing required fields: ['facing_tolerance_degrees']
```

精确单行字符串。缺失字段列表在只有一个元素时仍使用 `[...]` 格式。写入 `input_errors`，退出码 2，`.blend` 不打开。最终输出受 14A `canonicalize()` → `sorted(ie)` 字典序控制。

### 1.2 Pre-Open 函数

```python
def _validate_facing_forward_axis_rules_preopen(targets):
    errors = []
    for target in targets:
        tid = target.get("target_id", "")
        facing = target.get("facing")
        if not isinstance(facing, dict):
            continue
        la = facing.get("local_forward_axis")
        ew = facing.get("expected_world_forward_axis")
        tol = facing.get("facing_tolerance_degrees")
        if (la in AXIS_VALUES) and (ew in AXIS_VALUES) and (tol is None):
            errors.append(
                f"INVALID_FACING_RULE_RELATION: target '{tid}' "
                f"facing forward_axis missing required fields: ['facing_tolerance_degrees']"
            )
    return errors
```

---

## 二、完整算法

### 2.1 算法步骤

与 Standing 共享相同的变换流水线。输入为 `target`（spec 片段）和 `root_obj`（已验证的根对象）。

```
Step 1: 读取 matrix_world（最多一次）
  try: mw = root_obj.matrix_world
  except → ERROR, operation=READ_ROOT_MATRIX_WORLD

Step 2: 提取 3x3 线性变换（最多一次）
  try: m3 = mw.to_3x3()
  except → ERROR, operation=CONVERT_ROOT_MATRIX_WORLD_TO_3X3

  to_3x3() 保留旋转、缩放、负缩放、非均匀缩放和剪切。不分解、不去缩放、不正交化。

Step 3: 变换 local forward axis
  import mathutils  # lazy inside function
  try: world_fwd = m3 @ mathutils.Vector(axis_to_vector(local_forward_axis))
       world_fwd_tuple = (world_fwd.x, world_fwd.y, world_fwd.z)
  except → ERROR, operation=TRANSFORM_LOCAL_FORWARD_AXIS

Step 4: 校验并归一化
  4a. 分量有限性: 检查 world_fwd_tuple 三个分量均为有限值
      任一为 NaN/Inf → ERROR, operation=NORMALIZE_WORLD_FORWARD_AXIS
                       note=NONFINITE_WORLD_FORWARD_VECTOR

  4b. 长度计算:
      try: length = sqrt(x² + y² + z²)
      except (OverflowError, ValueError) → ERROR, NORMALIZE_WORLD_FORWARD_AXIS
                                            note=NONFINITE_WORLD_FORWARD_VECTOR

  4c. 长度有限性: if not isfinite(length) → ERROR, NORMALIZE_WORLD_FORWARD_AXIS
                                             note=NONFINITE_WORLD_FORWARD_VECTOR

  4d. 长度为零: if length == 0.0 → ERROR, NORMALIZE_WORLD_FORWARD_AXIS
                                    note=ZERO_LENGTH_FORWARD_VECTOR

  4e. 归一化: actual = [x/length, y/length, z/length]

Step 5: 计算角度
  try: angle = vector_angle_degrees(actual, axis_to_vector(expected_world_forward_axis))
  except → ERROR, operation=COMPUTE_FORWARD_AXIS_ANGLE

Step 6: 容差比较
  passes = (angle <= tolerance)
  angle == tolerance → PASS
  angle >  tolerance → FAIL, failure_code=FACING_FORWARD_AXIS_DEVIATION
```

### 2.2 数学边缘情况

| 情况 | 变换结果 | 归一化后 | 角度 | 判定 |
|------|---------|---------|------|------|
| 恒等 +Y→+Y | (0,1,0) length=1 | (0,1,0) | 0° | PASS |
| X 轴旋转 90° +Y→+Z | (0,0,1) | (0,0,1) | 90° | 取决于容差 |
| 均匀缩放 2× | (0,2,0) | (0,1,0) | 0° | PASS |
| 非均匀缩放 (2,3,4) | (0,3,0) | (0,1,0) | 0° | PASS |
| 负缩放 Y (1,-1,1) +Y→-Y | (0,-1,0) | (0,-1,0) | 180° | FAIL（正确行为） |
| 负缩放 Z (1,1,-1) | (0,1,0) | (0,1,0) | 0° | PASS |
| 剪切（不改变 forward） | (0,1,0) | (0,1,0) | 0° | PASS |
| 剪切（偏离 forward） | e.g. (0.5,1,0) | 归一化 | ~26.6° | 取决于容差 |
| 零向量 | (0,0,0) length=0 | — | — | ERROR ZERO_LENGTH |
| NaN 分量 | (NaN,*,*) | — | — | ERROR NONFINITE |
| Inf 分量 | (Inf,*,*) | — | — | ERROR NONFINITE |
| 平方溢出 | 1e155² → OverflowError | — | — | ERROR NONFINITE |
| 旋转+非均匀缩放 | (0,0,3) | (0,0,1) | 90° | PASS/FAIL 取决于容差 |

---

## 三、矩阵读取策略 A（最终确认）

### 3.1 策略

```
_check_standing_up_axis(target, root_obj) → 读取 root_obj.matrix_world 一次
_check_facing_forward_axis(target, root_obj) → 读取 root_obj.matrix_world 一次
```

两个函数之间**没有**共享的矩阵缓存。不从外部传入预读取的矩阵。不在 `_check_root_objects` 中预提取矩阵。

### 3.2 论证

1. Standing 已锁定，其函数签名和内部合同不得修改（锁定记录: `14B_3A_FORMAL_LOCK_RECORD.md`）。
2. 任何共享缓存要求修改 `_check_root_objects` 来传入矩阵，这会改变 Standing 的调用路径。
3. `matrix_world` 是 Blender property 访问（非计算密集型），两次读取的性能开销可忽略。
4. 独立读取使每个检查的 ERROR 路径完全隔离——矩阵读取失败不会在检查之间传播。
5. Scope guard 测试独立验证每个函数的读取次数约束。

### 3.3 独立性

```
Standing FAIL  → Facing 仍执行
Standing ERROR → Facing 仍执行
Facing FAIL    → Standing 结果不变
Facing ERROR   → Standing 结果不变
```

两个检查的唯一共享点：都在 `_check_root_objects` 的 `type_ok` 分支中调用，都向同一 `checks` dict 写入各自的结果。

---

## 四、Operation 定义

### 4.1 Operation 数量

Facing 有 **5 个 operation**（同 Standing）：

| # | Operation | 触发条件 | Note 值 |
|---|-----------|---------|---------|
| 1 | `READ_ROOT_MATRIX_WORLD` | `root_obj.matrix_world` 访问抛异常 | `READ_ROOT_MATRIX_WORLD_FAILED` |
| 2 | `CONVERT_ROOT_MATRIX_WORLD_TO_3X3` | `mw.to_3x3()` 调用抛异常 | `CONVERT_ROOT_MATRIX_WORLD_TO_3X3_FAILED` |
| 3 | `TRANSFORM_LOCAL_FORWARD_AXIS` | `m3 @ Vector(...)` 抛异常 | `TRANSFORM_LOCAL_FORWARD_AXIS_FAILED` |
| 4 | `NORMALIZE_WORLD_FORWARD_AXIS` | 分量 NaN/Inf、长度溢出、长度非有限 | `NONFINITE_WORLD_FORWARD_VECTOR` |
|   | （同上，不同分支） | `length == 0.0` | `ZERO_LENGTH_FORWARD_VECTOR` |
| 5 | `COMPUTE_FORWARD_AXIS_ANGLE` | `vector_angle_degrees(...)` 抛异常 | `COMPUTE_FORWARD_AXIS_ANGLE_FAILED` |

### 4.2 Operations vs 错误分支

- 5 个 distinct operation（对应代码中 5 个 `try/except` 或 guard 块）
- NORMALIZE_WORLD_FORWARD_AXIS 内部有 **2 个错误分支**（两个不同的 `note` 值）
- 错误分支不是独立的 operation——它们共享同一个 operation 名称

### 4.3 ERROR 结构

```json
{
  "facing": {
    "result": "ERROR",
    "forward_axis": {
      "result": "ERROR",
      "error_type": "FACING_FORWARD_AXIS_ERROR",
      "operation": "<OPERATION>",
      "note": "<NOTE>"
    }
  }
}
```

ERROR 时 `forward_axis` 省略:
- `local_forward_axis`
- `expected_world_forward_axis`
- `actual_world_forward_direction`
- `angle_degrees`
- `tolerance_degrees`
- `failure_code`

---

## 五、_collect_target_errors 扩展

```python
# After the standing error collection block:
ff = checks.get("facing", {}).get("forward_axis", {})
if ff.get("result") == "ERROR":
    op = ff.get("operation", "UNKNOWN")
    err_msgs.append(
        f"FACING_FORWARD_AXIS_ERROR: target '{tid}' "
        f"root_object_name '{rn}' operation '{op}'"
    )
```

Per-target 收集顺序: descendants → standing → facing。

---

## 六、结果结构速查

### NOT_CHECKED（未配置）
```json
{"facing": {"result": "NOT_CHECKED", "forward_axis": {"result": "NOT_CHECKED", "note": "FORWARD_AXIS_RULES_NOT_CONFIGURED"}}}
```

### PASS
```json
{"facing": {"result": "PASS", "forward_axis": {"result": "PASS", "local_forward_axis": "+Y", "expected_world_forward_axis": "+Y", "actual_world_forward_direction": [0.0, 1.0, 0.0], "angle_degrees": 0.0, "tolerance_degrees": 15.0}}}
```

### FAIL
```json
{"facing": {"result": "FAIL", "forward_axis": {"result": "FAIL", "local_forward_axis": "+Y", "expected_world_forward_axis": "+Y", "actual_world_forward_direction": [0.0, -1.0, 0.0], "angle_degrees": 180.0, "tolerance_degrees": 5.0, "failure_code": "FACING_FORWARD_AXIS_DEVIATION"}}}
```

### ERROR
```json
{"facing": {"result": "ERROR", "forward_axis": {"result": "ERROR", "error_type": "FACING_FORWARD_AXIS_ERROR", "operation": "READ_ROOT_MATRIX_WORLD", "note": "READ_ROOT_MATRIX_WORLD_FAILED"}}}
```

---

## 七、Scene 失败路径（R2A 已确定，无修改）

| 条件 | Facing 行为 |
|------|------------|
| `scene is None` | 省略（无 per_target_results） |
| `scene.objects` 读取失败 | 省略（checks 中无 facing 键） |
| ROOT_OBJECT_NOT_FOUND | NOT_CHECKED, note=ROOT_OBJECT_NOT_FOUND |
| ROOT_OBJECT_TYPE_MISMATCH | NOT_CHECKED, note=ROOT_OBJECT_TYPE_MISMATCH |
| AMBIGUOUS_ROOT_OBJECT_NAME | NOT_CHECKED, note=AMBIGUOUS_ROOT_OBJECT_NAME |

---

## 八、范围确认

**在范围内**:
- `facing.local_forward_axis`
- `facing.expected_world_forward_axis`
- `facing.facing_tolerance_degrees`
- `matrix_world.to_3x3()` 线性变换（保留所有线性分量）
- 5 个 operation 的 ERROR 处理
- `_collect_target_errors` 扩展
- Scope guard 测试更新

**不在范围内**:
- 矩阵分解、去缩放、正交化
- rotation、ground_contact、其余字段组
- 多角色相对朝向
- 历史状态一致性
- `.blend` 验证
