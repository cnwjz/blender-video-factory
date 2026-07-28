# 14B-3B Facing Forward Axis -- Design R2B1

```text
TASK_ID: 14B_3B_DESIGN_R2B1
BASELINE: d44679fc11c5069a17277395bb6c52b5a6dfc799
DESIGN_STATUS: READY_FOR_INDEPENDENT_REVIEW
IMPLEMENTATION_AUTHORIZED: FALSE
BLENDER_EXECUTION_AUTHORIZED: FALSE
REAL_PROJECT_BLEND_VALIDATION_AUTHORIZED: FALSE
PRIOR_REVISIONS: R1, R2A, R2B
```

R2A 修正了配置语义（14A schema 行为）。R2B 补全了需求证据和矩阵策略。R2B1 补全直接检查证据、溢出语义和来源文件名。

---

## 一、字段合同

| 字段 | 类型 | 14A 校验 | 来源 |
|------|------|---------|------|
| `facing.local_forward_axis` | `str` or `None` | `not in AXIS_VALUES` -> ERROR (including None) | 原始 v4 文档 "face +Y" -> 14A schema 轴名枚举 |
| `facing.expected_world_forward_axis` | `str` or `None` | `not in AXIS_VALUES` -> ERROR (including None) | 原始 v4 文档 "face +Y" -> 14A schema 轴名枚举 |
| `facing.facing_tolerance_degrees` | `number or None` | `_check_tolerance` -- None silently skipped | 14A schema（原始文档无容差概念，由实现层引入用于可重复的数值判定） |

### 1.1 INVALID_FACING_RULE_RELATION

```
INVALID_FACING_RULE_RELATION: target '<target_id>' facing forward_axis missing required fields: ['facing_tolerance_degrees']
```

精确单行字符串。写入 `input_errors`，退出码 2，`.blend` 不打开。最终输出受 14A `canonicalize()` -> `sorted(ie)` 字典序控制。

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

与 Standing 共享相同的变换流水线。

```
Step 1: Read matrix_world (at most once)
  try: mw = root_obj.matrix_world
  except -> ERROR, operation=READ_ROOT_MATRIX_WORLD

Step 2: Extract 3x3 linear transform (at most once)
  try: m3 = mw.to_3x3()
  except -> ERROR, operation=CONVERT_ROOT_MATRIX_WORLD_TO_3X3

  to_3x3() preserves rotation, scale, negative scale, non-uniform scale,
  and shear. No decomposition, descaling, or orthogonalization.

Step 3: Transform local forward axis
  import mathutils  # lazy inside function
  try: world_fwd = m3 @ mathutils.Vector(axis_to_vector(local_forward_axis))
       world_fwd_tuple = (world_fwd.x, world_fwd.y, world_fwd.z)
  except -> ERROR, operation=TRANSFORM_LOCAL_FORWARD_AXIS

Step 4: Validate and normalize
  4a. Component finiteness: check all three components of world_fwd_tuple
      are finite. Any NaN/Inf -> ERROR, operation=NORMALIZE_WORLD_FORWARD_AXIS
      note=NONFINITE_WORLD_FORWARD_VECTOR

  4b. Length computation:
      The multiplication x*x for large finite components may overflow to inf.
      math.sqrt() with extreme arguments may raise OverflowError or ValueError.
      try: length = sqrt(x*x + y*y + z*z)
      except (OverflowError, ValueError) -> ERROR,
        operation=NORMALIZE_WORLD_FORWARD_AXIS
        note=NONFINITE_WORLD_FORWARD_VECTOR

  4c. Length finiteness: if not isfinite(length) -> ERROR,
      operation=NORMALIZE_WORLD_FORWARD_AXIS
      note=NONFINITE_WORLD_FORWARD_VECTOR

  4d. Zero length: if length == 0.0 -> ERROR,
      operation=NORMALIZE_WORLD_FORWARD_AXIS
      note=ZERO_LENGTH_FORWARD_VECTOR

  4e. Normalize: actual = [x/length, y/length, z/length]

Step 5: Compute angle
  try: angle = vector_angle_degrees(actual, axis_to_vector(expected_world_forward_axis))
  except -> ERROR, operation=COMPUTE_FORWARD_AXIS_ANGLE

Step 6: Tolerance comparison
  passes = (angle <= tolerance)
  angle == tolerance -> PASS
  angle >  tolerance -> FAIL, failure_code=FACING_FORWARD_AXIS_DEVIATION
```

### 2.2 溢出语义（修正）

在 Step 4b 中，非有限长度的产生有两条路径：

| 路径 | 触发条件 | 处理 |
|------|---------|------|
| 浮点乘法 `x*x` 溢出 | 分量约 > 1e154 时 `x*x` 产生 inf 而非 OverflowError（IEEE 754 默认） | inf 通过 4a 或 4c 捕获 |
| `x*x` 结果为 inf，`sqrt(inf)` = inf | 正常返回，inf 通过 4c 捕获 | 4c: `not isfinite(inf)` -> NONFINITE |
| `math.sqrt()` 内部抛出 `OverflowError` | 极端参数值，平台相关 | except 捕获 -> NONFINITE |
| `math.sqrt()` 内部抛出 `ValueError` | 负参数（浮点误差），平台相关 | except 捕获 -> NONFINITE |

所有四条路径都路由到同一个结果：`operation=NORMALIZE_WORLD_FORWARD_AXIS, note=NONFINITE_WORLD_FORWARD_VECTOR`。

### 2.3 数学边缘情况

| 情况 | 变换结果 | 归一化后 | 角度 | 判定 |
|------|---------|---------|------|------|
| 恒等 +Y->+Y | (0,1,0) length=1 | (0,1,0) | 0deg | PASS |
| X 轴旋转 90deg +Y->+Z | (0,0,1) | (0,0,1) | 90deg | depends on tolerance |
| 均匀缩放 2x | (0,2,0) | (0,1,0) | 0deg | PASS |
| 非均匀缩放 (2,3,4) | (0,3,0) | (0,1,0) | 0deg | PASS |
| 负缩放 Y (1,-1,1) +Y->-Y | (0,-1,0) | (0,-1,0) | 180deg | FAIL (correct) |
| 负缩放 Z (1,1,-1) | (0,1,0) | (0,1,0) | 0deg | PASS |
| 剪切 (不改变 forward) | (0,1,0) | (0,1,0) | 0deg | PASS |
| 剪切 (偏离 forward) | e.g. (0.5,1,0) | normalized | ~26.6deg | depends on tolerance |
| 零向量 | (0,0,0) length=0 | -- | -- | ERROR ZERO_LENGTH |
| NaN 分量 | (NaN,*,*) | -- | -- | ERROR NONFINITE |
| Inf 分量 | (Inf,*,*) | -- | -- | ERROR NONFINITE |
| x*x 溢出到 inf | sqrt(inf) = inf | -- | -- | ERROR NONFINITE |
| 旋转+非均匀缩放 | (0,0,3) | (0,0,1) | 90deg | PASS/FAIL depend on tolerance |

---

## 三、矩阵读取策略 A

```
_check_standing_up_axis(target, root_obj) -> reads root_obj.matrix_world once
_check_facing_forward_axis(target, root_obj) -> reads root_obj.matrix_world once
```

No shared matrix cache. No externally pre-read matrix passed in. No pre-extraction in `_check_root_objects`.

Independence:
```
Standing FAIL  -> Facing still executes
Standing ERROR -> Facing still executes
Facing FAIL    -> Standing result unchanged
Facing ERROR   -> Standing result unchanged
```

---

## 四、Operation 定义

Facing has **5 operations** (same count as Standing):

| # | Operation | Trigger | Note value |
|---|-----------|---------|------------|
| 1 | `READ_ROOT_MATRIX_WORLD` | `root_obj.matrix_world` access raises | `READ_ROOT_MATRIX_WORLD_FAILED` |
| 2 | `CONVERT_ROOT_MATRIX_WORLD_TO_3X3` | `mw.to_3x3()` raises | `CONVERT_ROOT_MATRIX_WORLD_TO_3X3_FAILED` |
| 3 | `TRANSFORM_LOCAL_FORWARD_AXIS` | `m3 @ Vector(...)` raises | `TRANSFORM_LOCAL_FORWARD_AXIS_FAILED` |
| 4 | `NORMALIZE_WORLD_FORWARD_AXIS` | NaN/Inf components, overflow, non-finite length | `NONFINITE_WORLD_FORWARD_VECTOR` |
|   | (same operation, different branch) | `length == 0.0` | `ZERO_LENGTH_FORWARD_VECTOR` |
| 5 | `COMPUTE_FORWARD_AXIS_ANGLE` | `vector_angle_degrees(...)` raises | `COMPUTE_FORWARD_AXIS_ANGLE_FAILED` |

5 distinct operations. NORMALIZE_WORLD_FORWARD_AXIS has 2 internal error branches (different `note` values). Error branches are not independent operations.

### 4.1 ERROR structure

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

On ERROR, `forward_axis` omits: `local_forward_axis`, `expected_world_forward_axis`, `actual_world_forward_direction`, `angle_degrees`, `tolerance_degrees`, `failure_code`.

---

## 五、_collect_target_errors extension

```python
ff = checks.get("facing", {}).get("forward_axis", {})
if ff.get("result") == "ERROR":
    op = ff.get("operation", "UNKNOWN")
    err_msgs.append(
        f"FACING_FORWARD_AXIS_ERROR: target '{tid}' "
        f"root_object_name '{rn}' operation '{op}'"
    )
```

Per-target collection order: descendants -> standing -> facing.

---

## 六、Result structure quick reference

### NOT_CHECKED
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

## 七、Scene failure paths

| Condition | Facing behavior |
|-----------|----------------|
| `scene is None` | Omitted (no per_target_results) |
| `scene.objects` read failure | Omitted (no facing key in checks) |
| ROOT_OBJECT_NOT_FOUND | NOT_CHECKED, note=ROOT_OBJECT_NOT_FOUND |
| ROOT_OBJECT_TYPE_MISMATCH | NOT_CHECKED, note=ROOT_OBJECT_TYPE_MISMATCH |
| AMBIGUOUS_ROOT_OBJECT_NAME | NOT_CHECKED, note=AMBIGUOUS_ROOT_OBJECT_NAME |

---

## 八、Scope

**In scope**:
- `facing.local_forward_axis`, `facing.expected_world_forward_axis`, `facing.facing_tolerance_degrees`
- `matrix_world.to_3x3()` linear transform (preserving all linear components)
- 5 operation ERROR handling
- `_collect_target_errors` extension

**Deferred to later design/implementation**:
- Scope guard test update (not yet designed; must allow `.matrix_world` exactly once in `_check_facing_forward_axis` while preserving Standing's existing constraint)
- Implementation task breakdown (I1/I2/I3/E)

**Out of scope**:
- Matrix decomposition, descaling, orthogonalization
- rotation, ground_contact, remaining field groups
- Multi-character relative facing
- Historical state consistency
- `.blend` validation
