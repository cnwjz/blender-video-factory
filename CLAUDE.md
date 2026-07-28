# BVF Claude Code 项目规则

```text
DOCUMENT_ID: BVF_PROJECT_CLAUDE_RULES
VERSION: R3
PROJECT_ROOT: D:\blender-video-factory
```

本文件只规定本仓库长期稳定的执行纪律。它不记录某条视频的进度，不复制完整生产流程，也不记录质检系统当前状态。通用规则遵守用户级全局 `CLAUDE.md`，用户本轮明确要求优先。

## 1. 权威文件

- 根目录 `CLAUDE.md`：Claude Code 的长期执行纪律。
- `VIDEO_PRODUCTION_EXECUTION_STANDARD.md`：视频生产阶段、门槛和角色分工。
- 当前视频的 `VIDEO_PLAN.md`：当前阶段、批准状态、正式入口和唯一下一任务。
- `reviews/PROJECT_CODEIFICATION_MASTER_MAP.md`：仅用于通用质检系统维护。

旧报告、旧 ZIP、历史对话、文件名和 Claude Code 自己的完成声明，不能覆盖当前权威文件。

## 2. 任务模式

每轮只允许一个主要模式。

### VIDEO_PRODUCTION

适用于资产、场景、动画、Blender、blender-mcp、预览、渲染、编码、后期，以及当前视频自己的构建、门禁和输出验证。

必须读取生产规范、当前 `VIDEO_PLAN.md` 和本轮阶段直接依赖的文件。当前状态只以 `VIDEO_PLAN.md` 为准。

普通视频任务不得默认要求总地图版本、字段组锁定、完整 pytest 回归、质检状态同步或总地图更新。

### QA_SYSTEM_MAINTENANCE

仅适用于 `protocol_guard` 通用实现、schema、通用 gate、checker、字段组测试、回归、状态同步和锁定。

必须读取 `reviews/PROJECT_CODEIFICATION_MASTER_MAP.md` 以及本轮指定的设计、合同、锁定记录、代码和测试。只有本模式启用总地图、pytest、完整回归、状态同步和正式锁定规则。

### REPOSITORY_MAINTENANCE

适用于 Git、目录、文档、忽略规则和普通工具维护。只读取任务直接相关的文件。

不得自动修改视频状态、质检状态、已批准的 `.blend`、预览、成片或已锁定实现。含独立 `.git` 的子目录默认视为独立仓库，除非任务明确指定。

## 3. 共同执行规则

执行前确认：`TASK_ID`、`TASK_MODE`、唯一目标、权威输入、允许与禁止修改、允许操作、验收标准、停止条件和交付物。

必须遵守：

1. 一轮只推进一个目标。
2. 只修改明确授权的文件。
3. 不顺手修复范围外问题。
4. 不做无关重构、格式化或依赖升级。
5. 结论必须来自真实读取、检查或执行。
6. 命令启动不等于执行成功；测试通过不等于用户验收；`Render Saved` 不等于画面正确。
7. 完成当前任务后立即停止，不得自动开始下一阶段。

目标存在关键歧义、权威材料冲突、修改范围不明、必须授权的操作未授权、验收标准不足、任务与状态文件冲突，或两次定点尝试后仍失败时，立即停止并如实报告。

新问题分为：

- `BLOCKER`：不解决就无法可靠完成当前目标。
- `QUALITY`：影响质量，但不阻止完成。
- `TECH_DEBT`：未来复用或架构问题。

只有 `BLOCKER` 自动进入当前任务。

## 4. 视频生产硬规则

视频生产以最终成片为目标，不得把测试、报告、证据、架构或通用化变成主要工作。

`VIDEO_PLAN.md` 已分配正式构建、门禁、预览、正式渲染或输出验证入口时，必须使用正式入口。旧脚本和实验入口只能作为参考。

复杂场景默认采用明确配置或常量、版本化 bpy 脚本、blender-mcp 或 Blender 后台执行，并保存版本化 `.blend`。不得使用大量零散 MCP 调用盲目搭建复杂场景。

固定环境：

```text
OS: Windows 10
PROJECT_ROOT: D:\blender-video-factory
BLENDER: D:\Windows software\blender\blender.exe
BLENDER_VERSION: 5.1.2
PYTHON_VERSION: 3.14.5
FFMPEG_VERSION: 8.1.1
```

Blender、blender-mcp、打开或保存 `.blend`、渲染和编码，必须在本轮授权范围内执行。

新人物、骨骼、核心互动设备和关键相机变化必须进行必要的结构或视觉验证。视觉正确必须检查实际图片或视频；文件大小、像素统计、分辨率和编码信息只能作为辅助信号。

技术门禁失败时，不得正式渲染、绕过门禁或以部分通过冒充整体通过。

用户负责最终审美、发布和止损；Claude Code 不得代替用户裁定。

同一问题默认最多一轮实现和一轮定点修正，之后停止并报告。

## 5. 质检系统维护硬规则

本节只在 `QA_SYSTEM_MAINTENANCE` 模式启用。

普通实现只运行与改动直接相关的最小必要测试。修改 Python 文件后，在 pytest 前执行语法检查。

不得用 skip、xfail、提前 return、`assert True`、`or True`、无有效断言或等价机制掩盖失败。

完整回归、状态同步、总地图修改和正式锁定，只有本轮明确授权时才能执行。

Claude Code 无权代替 GPT 宣布独立审核通过，也无权代替用户批准正式锁定。

辅助测试、Scope Guard、报告和证据默认最多一轮实现和一轮集中修正。非核心增强缺口不得长期阻断视频生产。

## 6. 验证与交付

只执行与本轮改动直接相关的最小必要验证。根据任务选择语法、配置、路径、Blender 实际运行、场景结构、项目门禁、视觉预览、输出文件验证、聚焦 pytest 或明确授权的回归。

验证失败、命令非零退出、门禁失败或无法证明满足验收时，不得输出 `TASK_STATUS: COMPLETED`。

普通任务默认不生成完整报告、完整日志、ZIP、Manifest、SHA256、证据包或重复副本。

1–3 个文件直接上传；4 个及以上文件只有在保留目录结构或依赖确有价值时才打 ZIP。

临时脚本、缓存、帧序列、临时 `.blend` 和诊断文件不得混入 `delivery`。已批准或已提交审核的文件不得覆盖。

## 7. 默认输出

任务提示词规定格式时，严格使用指定格式。未规定时至少输出：

```text
TASK_ID:
TASK_MODE:
TASK_STATUS:
FILES_MODIFIED:
VALIDATIONS_RUN:
VALIDATION_RESULT:
OUTPUT_FILES:
DELIVERY_FOLDER:
BLOCKERS:
QUALITY_ITEMS:
TECH_DEBT:
NEXT_STAGE_STARTED: FALSE
```

视频生产任务还应补充本轮任务提示词或生产规范明确要求的字段。

所有状态、数字、路径和结果必须来自本轮真实检查或执行。
