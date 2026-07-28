# 14B-3B Facing Forward Axis -- Design R1

```text
TASK_ID: 14B_3B_FACING_DESIGN_R1
BASELINE: d44679fc11c5069a17277395bb6c52b5a6dfc799
DESIGN_STATUS: READY_FOR_INDEPENDENT_REVIEW
IMPLEMENTATION_AUTHORIZED: FALSE
BLENDER_EXECUTION_AUTHORIZED: FALSE
REAL_PROJECT_BLEND_VALIDATION_AUTHORIZED: FALSE
```

---

## 一、字段合同

### 1.1 字段定义（来自 14A Core 已锁定 schema）

| 字段 | 类型 | 有效值 |
|------|------|--------|
| `facing.local_forward_axis` | `str` or `None` | `"+X"`, `"-X"`, `"+Y"`, `"-Y"`, `"+Z"`, `"-Z"` |
| `facing.expected_world_forward_axis` | `str` or `None` | `"+X"`, `"-X"`, `"+Y"`, `"-Y"`, `"+Z"`, `"-Z"` |
| `facing.facing_tolerance_degrees` | `float` or `None` | `>= 0.0`, 有限, 非 NaN/Inf, 非 bool |

### 1.2 处理矩阵

| 场景 | 14A Schema | Pre-Open | Runtime |
|------|-----------|----------|---------|
| `facing` 字段缺失 | no-op | no-op | NOT_CHECKED |
| `facing` 为 `null` | no-op | no-op | NOT_CHECKED |
| `facing` 为空对象 `{}` | no-op | no-op | NOT_CHECKED |
| 三个字段全部 `None` | no-op | no-op | NOT_CHECKED |
| 三个字段全部配置 | 轴值+容差各自校验 | 通过 | 执行检查 |
| 仅 1-2 个字段配置 | 轴值+容差各自校验 | **ERROR** (INVALID_FACING_RULE_RELATION) | 不执行 |
| `local_forward_axis` 非法 | **ERROR** | 不执行 | 不执行 |
| `expected_world_forward_axis` 非法 | **ERROR** | 不执行 | 不执行 |
| `facing_tolerance_degrees` 非法 | **ERROR** | 不执行 | 不执行 |
| `facing_tolerance_degrees` 为 0.0 | 合法 | 通过 | 角度 == 0.0 时 PASS |

### 1.3 Pre-Open 校验

新增 `_validate_facing_forward_axis_rules_preopen(targets)` 函数，采用与 Standing 相同的 all-or-nothing 模式：

- `facing` 不存在或为 `None` → 跳过
- 三个字段全部为 `None`（`.get()` 返回 `None`）→ 合法，NOT_CHECKED
- 三个字段全部非 `None` → 合法，执行
- 仅 1-2 个非 `None` → **ERROR**: `INVALID_FACING_RULE_RELATION`

与 Standing 完全相同的行为，独立的函数，在 `_validate_and_open` 中与 standing 并列调用。

### 1.4 容差语义

- `angle == tolerance` → PASS（与 Standing 一致）
- `angle < tolerance` → PASS
- `angle > tolerance` → FAIL（failure_code: `FACING_FORWARD_AXIS_DEVIATION`）

---

## 二、Facing 的数学语义

### 2.1 算法大纲

与 Standing 共享相同的矩阵变换流水线，轴线名和语义方向不同。逐项说明：

| 步骤 | Standing (up) | Facing (forward) | 算法 |
|------|--------------|------------------|------|
| 局部向量 | `axis_to_vector(local_up_axis)` | `axis_to_vector(local_forward_axis)` | **相同** |
| 期望向量 | `axis_to_vector(expected_world_up_axis)` | `axis_to_vector(expected_world_forward_axis)` | **相同** |
| 读取矩阵 | `root_obj.matrix_world` | `root_obj.matrix_world` | **相同** |
| 提取旋转 | `mw.to_3x3()` | `mw.to_3x3()` | **相同** |
| 世界变换 | `m3 @ Vector(local_vec)` | `m3 @ Vector(local_vec)` | **相同** |
| 归一化 | `sqrt(x^2+y^2+z^2)`, 各分量除以长度 | 同 | **相同** |
| 角度计算 | `vector_angle_degrees(normalized, expected)` | 同 | **相同** |
| 容差比较 | `angle <= tolerance` | 同 | **相同** |
| 零长度 | ZERO_LENGTH_UP_VECTOR | ZERO_LENGTH_FORWARD_VECTOR | **相同，名称变化** |
| NaN/Inf | NONFINITE_WORLD_UP_VECTOR | NONFINITE_WORLD_FORWARD_VECTOR | **相同，名称变化** |
| 溢出保护 | try/except (OverflowError, ValueError) | 同 | **相同** |

### 2.2 负缩放

同 Standing：`local_forward_axis = +Y`，世界矩阵有 `(1, -1, 1)` 缩放 → `actual_world_direction = (0, -1, 0)` → 与 `expected_world_forward_axis = +Y` 的角度 = 180deg → FAIL。

### 2.3 非均匀缩放

同 Standing：`(2, 3, 4)` 缩放不会改变 `+Y` 轴方向（仅缩放 Y 分量），归一化后方向不变 → PASS。

### 2.4 Shear

同 Standing：shear 会偏离期望轴方向，实际角度由 `vector_angle_degrees` 计算 → 取决于容差。

---

## 三、与已锁定 Standing 的读取关系

### 3.1 选择方案 A：各自独立读取

**选择**: 方案 A。`_check_standing_up_axis` 和 `_check_facing_forward_axis` 各自在其函数体内读取 `root_obj.matrix_world` 最多一次。

**论证**:
1. Standing 已锁定。任何缓存机制会改变 `_check_root_objects` 的调用合同，这违反锁定约束。
2. 独立的 try/except 使得矩阵读取失败时两个检查各自的 ERROR 完全独立，不会互相污染。
3. 两个函数的单次读取约束各自通过 AST scope guard 独立验证。
4. Blender 中 `matrix_world` 是 property 访问（非重型计算），两次读取的性能影响可忽略。

### 3.2 Scope Guard 更新

当前 scope guard 规则：
```
_check_standing_up_axis → 恰好 1 次 .matrix_world Load
其他函数 → 禁止 .matrix_world
```

Facing 实现后更新为：
```
_check_standing_up_axis → 恰好 1 次 .matrix_world Load
_check_facing_forward_axis → 恰好 1 次 .matrix_world Load
其他函数 → 禁止 .matrix_world
```

此为 scope guard 测试的白名单扩展，不修改生产逻辑。

### 3.3 两个检查都执行时的读取次数

- Root 存在且类型匹配 → Standing 读 1 次（在其函数内），Facing 读 1 次（在其函数内）
- 仅配置 Standing → Standing 读 1 次，Facing 返回 NOT_CHECKED（不读取）
- 仅配置 Facing → Facing 读 1 次，Standing 返回 NOT_CHECKED（不读取）
- 都未配置 → 都不读取

每个函数内部的读取次数通过各个函数自己的 try/except 边界确保。

---

## 四、执行条件和独立性

### 4.1 执行条件

Facing 在以下条件下运行（与 Standing 完全相同的条件）：
- 根对象存在且唯一
- 根对象类型匹配 `expected_root_type`
- `facing` 三个字段全部配置（pre-open 已确保）

### 4.2 独立性

| 其他检查的状态 | Facing 是否运行 |
|---------------|----------------|
| direct_children PASS | 运行 |
| direct_children FAIL | 运行 |
| direct_children ERROR | 运行 |
| descendants PASS | 运行 |
| descendants FAIL | 运行 |
| descendants ERROR | 运行 |
| Standing PASS / FAIL / ERROR | 运行 |
| 根对象不存在 | NOT_CHECKED (ROOT_OBJECT_NOT_FOUND) |
| 根对象类型不匹配 | NOT_CHECKED (ROOT_OBJECT_TYPE_MISMATCH) |
| 根对象名称歧义 | NOT_CHECKED (AMBIGUOUS_ROOT_OBJECT_NAME) |

### 4.3 Target Overall 聚合

继续使用三级优先级：

```text
ERROR > FAIL > PASS
```

聚合逻辑：
```python
dc_r = direct_children.result
dd_r = descendants.result
su_r = standing.result
ff_r = facing.result

if any == "ERROR": overall = "ERROR"
elif any == "FAIL": overall = "FAIL"
else: overall = "PASS"
```

---

## 五、结果结构和稳定错误

### 5.1 结果结构总览

嵌套路径：`checks.facing.forward_axis`

```
checks.facing.result        → "PASS" | "FAIL" | "ERROR" | "NOT_CHECKED"
checks.facing.forward_axis  → { up_axis 风格的嵌套 dict }
```

### 5.2 完整 JSON 示例

#### NOT_CHECKED（未配置）
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

#### NOT_CHECKED（根前置条件失败）
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

#### PASS
```json
{
  "facing": {
    "result": "PASS",
    "forward_axis": {
      "result": "PASS",
      "local_forward_axis": "+Y",
      "expected_world_forward_axis": "+Y",
      "actual_world_forward_direction": [0.0, 1.0, 0.0],
      "angle_degrees": 0.0,
      "tolerance_degrees": 15.0
    }
  }
}
```

#### FAIL
```json
{
  "facing": {
    "result": "FAIL",
    "forward_axis": {
      "result": "FAIL",
      "local_forward_axis": "+Y",
      "expected_world_forward_axis": "+Y",
      "actual_world_forward_direction": [0.0, -1.0, 0.0],
      "angle_degrees": 180.0,
      "tolerance_degrees": 5.0,
      "failure_code": "FACING_FORWARD_AXIS_DEVIATION"
    }
  }
}
```

#### ERROR（以 READ_ROOT_MATRIX_WORLD 为例）
```json
{
  "facing": {
    "result": "ERROR",
    "forward_axis": {
      "result": "ERROR",
      "error_type": "FACING_FORWARD_AXIS_ERROR",
      "operation": "READ_ROOT_MATRIX_WORLD",
      "note": "READ_ROOT_MATRIX_WORLD_FAILED"
    }
  }
}
```

### 5.3 ERROR Operation 全集

| # | Operation | 对应步骤 | Note |
|---|-----------|---------|------|
| 1 | `READ_ROOT_MATRIX_WORLD` | `mw = root_obj.matrix_world` | READ_ROOT_MATRIX_WORLD_FAILED |
| 2 | `CONVERT_ROOT_MATRIX_WORLD_TO_3X3` | `m3 = mw.to_3x3()` | CONVERT_ROOT_MATRIX_WORLD_TO_3X3_FAILED |
| 3 | `TRANSFORM_LOCAL_FORWARD_AXIS` | `m3 @ Vector(local_vec)` | TRANSFORM_LOCAL_FORWARD_AXIS_FAILED |
| 4 | `NORMALIZE_WORLD_FORWARD_AXIS` (零长度) | `length == 0.0` | ZERO_LENGTH_FORWARD_VECTOR |
| 5 | `NORMALIZE_WORLD_FORWARD_AXIS` (非有限) | NaN/Inf/溢出 | NONFINITE_WORLD_FORWARD_VECTOR |
| 6 | `COMPUTE_FORWARD_AXIS_ANGLE` | `vector_angle_degrees(...)` | COMPUTE_FORWARD_AXIS_ANGLE_FAILED |

### 5.4 ERROR 时省略的字段

`forward_axis` 在 ERROR 时不得出现：
- `local_forward_axis`
- `expected_world_forward_axis`
- `actual_world_forward_direction`
- `angle_degrees`
- `tolerance_degrees`
- `failure_code`

### 5.5 顶层错误收集

`_collect_target_errors` 新增：
```python
ff = checks.get("facing", {}).get("forward_axis", {})
if ff.get("result") == "ERROR":
    op = ff.get("operation", "UNKNOWN")
    err_msgs.append(
        f"FACING_FORWARD_AXIS_ERROR: target '{tid}' "
        f"root_object_name '{rn}' operation '{op}'"
    )
```

稳定顺序：Standing errors 之后追加 Facing errors（per-target 内：descendants → standing → facing）。

---

## 六、范围边界

### 6.1 明确在范围内

```text
facing.local_forward_axis
facing.expected_world_forward_axis
facing.facing_tolerance_degrees
matrix_world.to_3x3() 旋转提取
轴向量变换
归一化
角度计算与容差比较
五个运行时 ERROR operation
_collect_target_errors 扩展
Scope guard 测试更新（测试文件，非生产代码）
```

### 6.2 明确排除

```text
rotation（下一个字段组）
ground_contact
visibility
material_assignment
animation_state
collection_rules
camera_check
projection_groups
evaluated geometry (depsgraph, to_mesh)
真实项目 .blend 验证（最后阶段）
FBX 导入
渲染
```

### 6.3 不可代码化分类

| 原始要求 | 分类 | 理由 |
|---------|------|------|
| 顾客朝向收银员 | DEFER_REQUIRES_STATE | 需要多角色相对位置 |
| 收银员朝向顾客 | DEFER_REQUIRES_STATE | 同上 |
| 不允许顾客朝向镜头 | DEFER_REQUIRES_STATE | 需要相机位置 |
| 人物站立/朝向/层级未通过时禁止调整相机 | DOCUMENT_ONLY | 工作流规则 |
| 位置与朝向不变 | HUMAN_JUDGMENT_ONLY | 视觉比较 |

---

## 七、后续任务拆分

```text
Phase 14B_3B_I1  — Pre-Open + PASS/FAIL/NOT_CHECKED
  14B_3B_I1A: Pre-open validation (_validate_facing_forward_axis_rules_preopen)
  14B_3B_I1B: 基础运行时 (_check_facing_forward_axis) PASS/FAIL/NOT_CHECKED
  CPython only, fake objects, 不运行 Blender

Phase 14B_3B_I2  — Runtime ERROR + 错误收集 + Scope Guard 同步
  14B_3B_I2A: 5 个 ERROR operation 边界
  14B_3B_I2B: NORMALIZE_WORLD_FORWARD_AXIS (零长度/NaN/Inf/溢出)
  14B_3B_I2C: _collect_target_errors 扩展
  14B_3B_I2D: Scope guard 测试更新（independent review 后执行）

Phase 14B_3B_I3  — Real Blender mathutils 边界测试
  Runner + pytest, 不打开 .blend

Phase 14B_3B_E   — Final evidence
  14B_3B_E1: Standing + Facing + 14A Core + 完整回归
  14B_3B_E2: 证据包、manifest、最终 ZIP
```

每个 Phase 必须全部子任务通过后才能进入下一个 Phase。
Standing 已锁定代码在整个过程中不得修改。
