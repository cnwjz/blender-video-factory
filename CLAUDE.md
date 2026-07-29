# BVF Claude Code 项目规则

```text
DOCUMENT_ID: BVF_PROJECT_CLAUDE_RULES
VERSION: R4
PROJECT_ROOT: D:\blender-video-factory
```

本文件只规定本仓库长期稳定的执行纪律。它不记录某条视频的进度，不复制完整生产流程，也不记录质检系统当前状态。视频生产的完整阶段、门槛、批准和门禁规则以 `VIDEO_PRODUCTION_EXECUTION_STANDARD.md` 为准；当前视频状态以该项目的 `VIDEO_PLAN.md` 为准。通用规则遵守用户级全局 `CLAUDE.md`，用户本轮明确要求优先。

## 1. 权威文件

- 根目录 `CLAUDE.md`：Claude Code 的长期执行纪律。
- `VIDEO_PRODUCTION_EXECUTION_STANDARD.md`：视频生产阶段、门槛、批准、门禁和角色分工。
- 当前视频的 `VIDEO_PLAN.md`：当前阶段、`PROBLEM_ID`、批准状态、正式入口和唯一下一任务。
- 当前项目明确标记为 `APPROVED` 的资产模板、合同、配置和 `.blend`：只在对应项目及对应阶段内具有权威性。
- `reviews/PROJECT_CODEIFICATION_MASTER_MAP.md`：仅用于通用质检系统维护。

旧报告、旧 ZIP、历史对话、文件名、未批准候选和 Claude Code 自己的完成声明，不能覆盖当前权威文件。

权威文件之间发生会改变目标、范围、验收标准、允许修改内容、批准状态或下一步的冲突时，不得自行拼接解释，必须停止并报告。

## 2. 任务模式

每轮只允许一个主要模式。

### VIDEO_PRODUCTION

适用于资产、场景、动画、Blender、blender-mcp、预览、渲染、编码、后期，以及当前视频自己的构建、阶段门禁和输出验证。

必须读取生产规范、当前 `VIDEO_PLAN.md`、本轮权威输入，以及当前阶段直接依赖的批准模板、批准合同或批准场景。当前状态只以 `VIDEO_PLAN.md` 为准。

普通视频任务不得默认要求总地图版本、字段组锁定、完整 pytest 回归、质检状态同步或总地图更新。

### QA_SYSTEM_MAINTENANCE

仅适用于 `protocol_guard` 通用实现、schema、通用 gate、checker、字段组测试、回归、状态同步和锁定。

必须读取 `reviews/PROJECT_CODEIFICATION_MASTER_MAP.md` 以及本轮指定的设计、合同、锁定记录、代码和测试。只有本模式启用总地图、pytest、完整回归、状态同步和正式锁定规则。

### REPOSITORY_MAINTENANCE

适用于 Git、目录、文档、忽略规则和普通工具维护。只读取任务直接相关的文件。

不得自动修改视频批准状态、质检锁定状态、`MANUAL_REFERENCE`、`APPROVED`、已提交审核的 `.blend`、预览、成片或已锁定实现。含独立 `.git` 的子目录默认视为独立仓库，除非任务明确指定。

## 3. 共同执行规则

执行前必须确认本轮核心边界：

```text
TASK_ID
UNIQUE_MAIN_GOAL
AUTHORITATIVE_INPUTS
ALLOW_MODIFY
DO_NOT_MODIFY
ACCEPTANCE_CRITERIA
STOP_CONDITIONS
DELIVERABLES
```

以下信息只在当前任务确实需要时增加，不得为了形式完整机械重复：

```text
PROBLEM_ID
TASK_MODE
CURRENT_STAGE
INPUT_APPROVAL_STATUS
AUTHORIZED_OPERATIONS
MANDATORY_GATE
```

任务模式必须能够从本轮指令、对话或状态文件中唯一确定。只要继续处理同一真实问题，就必须沿用同一 `PROBLEM_ID`；不属于返工或持续问题的简单任务可以省略该字段或写 `NOT_APPLICABLE`。

必须遵守：

1. 一轮只推进一个主要目标，最多附带一个不可分割的子目标。
2. 只修改明确授权的文件、对象和属性。
3. 不顺手修复范围外问题。
4. 不做无关重构、格式化或依赖升级。
5. 结论必须来自真实读取、检查或执行。
6. 命令启动不等于执行成功；测试通过不等于用户验收；`Render Saved` 不等于画面正确。
7. 完成当前任务后立即停止，不得自动开始下一阶段。
8. 不得从门禁失败或尚未批准的候选进入下一阶段。
9. 不得以文字总结代替任务要求的原始机器结果。
10. 不适用的字段或门禁写 `NOT_APPLICABLE` 或 `NOT_REQUIRED`，不得为了形式完整启动无关工作。

目标存在关键歧义、权威材料冲突、修改范围不明、必须授权的操作未授权、验收标准不足、任务与状态文件冲突，或同一 `PROBLEM_ID` 的一轮实现加一轮定点修正后仍失败时，立即停止并如实报告。

新问题分为：

- `BLOCKER`：不解决就无法可靠完成当前目标。
- `QUALITY`：影响质量，但不阻止完成。
- `TECH_DEBT`：未来复用或架构问题。

只有 `BLOCKER` 自动进入当前任务。

**冻结验收标准的地位：**

任务执行前已经写入目标或验收标准的画面质量、可读性、功能完整性、正确性和可用性要求，属于当前目标本身。任一冻结验收标准未满足时：

1. 不得将其降级为 `QUALITY` 或“已知限制”后报告 `TASK_STATUS: COMPLETED`。
2. 仍有修正额度不等于已经获得修正授权。只有用户或 GPT 已明确授权，并且存在一个边界清楚、单一主要变量的定点修正路径时，才能执行一次修正；否则必须停止并报告。修正后仍不满足且额度已用完，必须报告 `PARTIAL` 或 `BLOCKED`。
3. 只有在任务执行过程中新发现、且不影响已冻结目标和验收标准的问题，才能记录为 `QUALITY` 或 `TECH_DEBT`。

**TASK_STATUS 的明确语义：**

- `COMPLETED`：本轮要求的实际交付物已经生成，并且执行者检查后能够证明本轮全部冻结验收标准均满足。
- `PARTIAL`：已生成部分或全部交付物，但至少一项本轮冻结验收标准仍未满足。
- `BLOCKED`：无法在授权范围内满足本轮冻结验收标准，或者同一 `PROBLEM_ID` 的一轮实现和一轮定点修正额度已经用完。

`TASK_STATUS` 只表示本轮执行任务的状态，不等于阶段批准。候选生成任务在用户批准未被列为本轮验收标准时，可以在 `USER_APPROVAL: PENDING` 的同时报告 `COMPLETED`；这不允许候选晋升或进入下一阶段。若本轮目标本身要求获得批准，则批准仍为 `PENDING` 时不得报告 `COMPLETED`。

文件存在、分辨率正确、对象数量正确、渲染成功或视觉辅助工具给出部分正面描述，都不能单独支持 `COMPLETED`。

**问题级止损：**

同一 `PROBLEM_ID` 默认最多一轮实现和一轮定点修正。更换 `TASK_ID`、脚本名、文件版本、相机类型、焦距或方案名称不重置次数。修正额度只表示允许被授权的次数上限，不构成自动执行授权。额度用完后必须停止自动修正，设置或报告 `STOP_LOSS_TRIGGERED: TRUE`，由 GPT 和用户决定是否修改前提或重新授权。

## 4. 视频生产硬规则

视频生产以最终成片为目标，不得把测试、报告、证据、架构或通用化变成主要工作。

`VIDEO_PLAN.md` 已分配当前阶段所需的正式构建、门禁、预览、正式渲染或输出验证入口时，必须使用正式入口。尚未进入对应阶段的入口可以是 `NOT_ASSIGNED`；只有当前任务实际依赖的入口缺失时才阻断。

复杂场景默认采用批准模板、批准合同或明确配置、版本化 `bpy` 脚本、blender-mcp 或 Blender 后台执行，并保存版本化候选 `.blend`。不得使用大量零散 MCP 调用盲目搭建复杂场景。

关键生产文件必须遵守：

```text
MANUAL_REFERENCE：用户手动确认的参考答案，只读
CANDIDATE：当前阶段候选，只能在授权范围内修改
APPROVED：必要机器门禁通过，并获得该阶段规定的批准
```

1. 不得覆盖 `MANUAL_REFERENCE`、`APPROVED` 或已提交审核的原件。
2. 只能从 `APPROVED`，或任务明确指定的 `MANUAL_REFERENCE` 副本派生候选。
3. 候选门禁失败或尚未获得规定批准时，不得成为下一阶段输入。
4. 批准内容需要变化时，必须创建新候选并重新审批。
5. 关键 `.blend` 必须保存后由全新 Blender 进程重新打开并验证；只检查当前内存状态不构成批准证据。

已有批准资产模板时，正式场景必须优先使用批准模板，不得重新导入原始资产并再次猜测比例、方向或贴地。核心资产正确性以可见几何的世界尺寸、最低点、方向、结构和批准基准为准，不得只看父级 `location`、`rotation`、`scale` 或原点。

复杂布局应由批准合同、语义锚点和确定性脚本生成。不得通过自然语言自由猜测大量关键对象的世界坐标。

必须区分 `WORLD_LAYOUT_APPROVED` 与 `SHOT_COMPOSITION_APPROVED`。相机任务不得为适配画面偷偷移动已批准世界布局；相机失败时应回到画幅、分镜或镜头合同决策，不能用相机掩盖资产或布局错误。

当前项目声明的必要阶段门禁必须真实执行。必检项为 `FAIL`、`ERROR`、`NOT_CHECKED`、结果缺失、旧结果、run_id 不匹配或 blend_path 不匹配时，门禁失败。门禁失败不得进入相机、动画、完整预览或正式渲染等下一阶段。

Claude Code 必须按任务要求提交原始门禁结果、退出码、实际值、预期值和容差，不能只报告 `MET`、`PASS` 或 `TRUE`。任何人工或视觉批准都不能把机器硬失败直接改写为通过；只能修复候选，或正式修改并版本化验收合同后重新检查。

视觉结果必须区分：

```text
MACHINE_GATE_RESULT
INDEPENDENT_VISUAL_REVIEW
USER_APPROVAL
```

机器门禁负责客观事实；GPT 可以批准纯技术配置、脚本和机器门禁结果，并负责独立视觉初审；用户负责生产规范明确列出的资产比例、世界布局、镜头、样片、完整预览、成片等视觉批准，以及最终审美和发布决定。Claude Code 不得填写或暗示 `USER_APPROVAL: APPROVED`。

正式首帧、样片、完整预览和最终成片必须提供真实 PNG 或 MP4。静态数据、接触表、统计、终端说明或文件存在性不能代替任务要求的画面或视频。

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

普通生产任务只运行当前修改会影响的最小必要门禁，不默认运行完整质检或完整回归。资产测量、批准模板派生、门禁接入、故障注入或最小诊断只有在直接解除当前 `BLOCKER` 时，才可以成为独立技术任务；完成后立即回到直接生产。

## 5. 质检系统维护硬规则

本节只在 `QA_SYSTEM_MAINTENANCE` 模式启用。

普通实现只运行与改动直接相关的最小必要测试。修改 Python 文件后，在 pytest 前执行语法检查。

不得用 skip、xfail、提前 return、`assert True`、`or True`、无有效断言或等价机制掩盖失败。

完整回归、状态同步、总地图修改和正式锁定，只有本轮明确授权时才能执行。

Claude Code 无权代替 GPT 宣布独立审核通过，也无权代替用户批准正式锁定。

辅助测试、Scope Guard、报告和证据默认最多一轮实现和一轮集中修正。非核心增强缺口不得长期阻断视频生产。

## 6. 验证与交付

只执行与本轮改动直接相关的最小必要验证。根据任务选择语法、配置、路径、Blender 实际运行、场景结构、项目门禁、视觉预览、输出文件验证、聚焦 pytest 或明确授权的回归。

验证失败、命令非零退出、必要门禁失败、必检项未执行或无法证明满足验收时，不得输出 `TASK_STATUS: COMPLETED`。

视觉任务必须生成并确认实际 PNG 或 MP4 真实存在且可以读取，并核对本轮要求的机器可验证项，例如对象可见性、投影、裁切、分辨率和文件规格。Claude Code 可以如实报告明显异常，但不得把自身观察写成 `INDEPENDENT_VISUAL_REVIEW: PASS`，也不得代替 GPT 或用户判断画面可读性、空间关系、主体占比、剧情表达或审美是否通过。需要独立视觉审核的项目必须保持 `PENDING_GPT_REVIEW` 或 `PENDING`。若本轮冻结目标本身要求获得视觉批准，在对应审核完成前不得报告 `COMPLETED`；若本轮只要求生成候选，则按 §3 的任务状态语义处理。视觉辅助工具只提供辅助证据，不构成最终视觉批准。

普通任务默认不生成完整报告、完整日志、ZIP、Manifest、SHA256、证据包或重复副本。

1–3 个文件直接上传；4 个及以上文件只有在保留目录结构或依赖确有价值时才打 ZIP。

临时脚本、缓存、帧序列、临时 `.blend` 和诊断文件不得混入 `delivery`。`MANUAL_REFERENCE`、`APPROVED` 或已提交审核的文件不得覆盖。

## 7. 默认输出

任务提示词规定格式时，严格使用指定格式。未规定时，只选择能够说明本轮真实结果的最小字段集合，通常包括：

```text
TASK_ID:
TASK_STATUS:
OUTPUT_FILES:
BLOCKERS:
NEXT_STAGE_STARTED: FALSE
```

按任务实际需要增加，而不是机械全部输出：

```text
PROBLEM_ID:
TASK_MODE:
CURRENT_STAGE:
INPUT_APPROVAL_STATUS:
FILES_MODIFIED:
VALIDATIONS_RUN:
MACHINE_GATE_RESULT:
GATE_RESULT_FILES:
GATE_EXIT_CODE:
INDEPENDENT_VISUAL_REVIEW: PENDING_GPT_REVIEW
USER_APPROVAL: PENDING
QUALITY_ITEMS:
TECH_DEBT:
DELIVERY_FOLDER:
```

没有 `QUALITY`、`TECH_DEBT`、门禁或 delivery 时，不要求输出对应字段。不适用的已要求字段写 `NOT_APPLICABLE`，未执行的操作写 `NOT_RUN`，未授权的操作写 `NOT_AUTHORIZED`。所有状态、数字、路径和结果必须来自本轮真实检查或执行。
