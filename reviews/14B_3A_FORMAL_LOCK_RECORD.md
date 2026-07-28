# 14B-3A Standing Up Axis 正式锁定记录

```text
TASK_ID: 14B_3A
TASK_NAME: Standing Up Axis
LOCK_STATUS: LOCKED
LOCK_APPROVAL_DATE: 2026-07-18
LOCK_BASIS: USER_FORMAL_APPROVAL
BASELINE_COMMIT: d44679fc11c5069a17277395bb6c52b5a6dfc799
FINAL_REVIEW_STATUS: ALL_CHECKS_PASS
FINAL_EVIDENCE_PACKAGE_SHA256: 9dc9ea3959077438c237a5281da572e6dc49732eb8082232963055782638c420
```

## 一、用户正式批准

用户于 2026-07-18 明确批准：

```text
批准正式锁定 14B-3A Standing Up Axis
```

从本记录生效起，`14B-3A` 视为正式锁定。

## 二、锁定字段

```text
standing.local_up_axis
standing.expected_world_up_axis
standing.up_axis_tolerance_degrees
```

## 三、锁定语义

```text
三个字段全部缺失或全部为 null -> NOT_CHECKED
仅配置其中 1 个或 2 个 -> 打开 .blend 前输入 ERROR
三个字段完整配置 -> 执行运行时 Standing Up Axis 检查
local_up_axis 经 root_obj.matrix_world.to_3x3() 转换到世界方向
转换结果必须有限且长度大于 0
归一化后与 expected_world_up_axis 计算角度
angle <= tolerance -> PASS
angle > tolerance -> FAIL，STANDING_UP_AXIS_DEVIATION
```

## 四、锁定读取与错误边界

```text
matrix_world：恰好读取一次
to_3x3：最多调用一次
READ_ROOT_MATRIX_WORLD
CONVERT_ROOT_MATRIX_WORLD_TO_3X3
TRANSFORM_LOCAL_UP_AXIS
NORMALIZE_WORLD_UP_AXIS
COMPUTE_UP_AXIS_ANGLE
ZERO_LENGTH_UP_VECTOR
NONFINITE_WORLD_UP_VECTOR
```

运行时错误必须位于 `standing.up_axis`，并由 `_collect_target_errors()` 以稳定顺序收集。Standing 必须在根对象唯一存在且类型匹配时独立执行，不得因 direct_children 或 descendants 的 FAIL / ERROR 被跳过。

## 五、测试与证据

```text
Standing focused: 73 passed, 0 failed
14A Core: 139 passed, 0 failed
Full regression: 719 passed, 2 skipped, 0 failed
Evidence ZIP: 23 files
Manifest: 22 entries
All size and SHA256 checks: PASS
```

## 六、锁定后约束

未经新的正式设计、独立验收和用户明确批准，不得：

```text
重新解释或扩大 Standing 字段语义
修改上述 PASS / FAIL / ERROR / NOT_CHECKED 合同
修改 operation、failure_code 或错误结构
放宽 matrix_world 和 to_3x3 的读取次数约束
移除 runner 一致性保护
将 Facing、Rotation、Ground Contact 等内容并入本锁定范围
```

以下内容仍未授权：

```text
真实项目 .blend 验证
渲染
保存 .blend
Facing 实现
其他字段组实现
```

## 七、下一步

```text
CURRENT_NEXT_TASK: 14B_3B_DESIGN
CURRENT_NEXT_ACTION: 设计 Facing 字段组的锁定合同与原子拆分
IMPLEMENTATION_AUTHORIZED: FALSE
```
