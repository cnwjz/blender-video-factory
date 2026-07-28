# 14B-3A-I2 独立验收记录

```text
TASK_ID: 14B_3A_I2
REVIEW_STATUS: ALL_CHECKS_PASS
TASK_STATUS: PASSED
DATE: 2026-07-18
BLENDER_TEST_RESULT: 10 passed, 0 failed
CPYTHON_REPORTED_RESULT: 58 passed, 0 failed
CPYTHON_INDEPENDENT_RERUN: 58 passed, 0 failed
TOTAL_REPORTED_RESULT: 68 passed, 0 failed
PRODUCTION_CODE_MODIFIED: FALSE
REAL_PROJECT_BLEND_OPENED: FALSE
STANDING_LOCKED: FALSE
NEXT_TASK_STARTED: FALSE
```

## 独立结论

I2 已满足真实 Blender `mathutils.Matrix` 边界测试目标。

确认覆盖：

```text
单位矩阵
X 轴旋转 90 度
Y 轴旋转 90 度
Z 轴负缩放
非均匀正缩放
旋转与非均匀缩放组合
剪切矩阵容差 PASS
剪切矩阵容差 FAIL
Z 轴零缩放 ERROR
```

外层 pytest 使用 module 级 fixture，只启动一次 Blender。启动参数为：

```text
--background --factory-startup --python <runner>
```

runner 未调用 `bpy.ops.wm.open_mainfile`，未打开任何 `.blend` 文件。

## 内联算法核对

由于 Blender 内置 Python 的 import 链缺少 `yaml`，runner 内联了 Standing 算法与两个 14A 数学辅助函数。

独立 AST 核对结果：

```text
EXECUTABLE_LOGIC_EQUIVALENT: TRUE
NORMALIZED_AST_SHA256:
602f6e5aa12fd1ac5ccc0f2daed3cc2375a5e4d4053fe8e4b02427bdbe57e16e
```

这里的“一致”指排除函数名、docstring、注释和生产函数内部的懒加载 import 后，可执行 AST 逻辑相同。

提交报告中的“逐字节一致”表述不准确。两个函数并非逐字节相同，但当前可执行逻辑相同。该表述错误不影响 I2 功能通过。

## 测试证据

提交的 Blender 输出：

```text
10 passed, 0 failed
```

提交的 CPython 输出：

```text
58 passed, 0 failed
```

独立重建最小测试环境并复跑 I1 至 I1C3：

```text
58 passed, 0 failed
```

当前审核环境没有 Blender 可执行文件，因此无法在本环境再次启动 Blender。Blender 部分结论基于原始 pytest 输出、外层测试源码、runner 源码和静态一致性核对。

## 最终锁定前必须完成

```text
1. 增加自动一致性保护，防止 runner 内联算法与生产函数以后发生偏移。
2. 运行 Standing 全部聚焦回归。
3. 运行 14A Core 回归。
4. 运行完整项目回归。
5. 整理最终证据包。
6. 执行最终独立验收。
7. 由用户批准正式锁定 Standing。
```
