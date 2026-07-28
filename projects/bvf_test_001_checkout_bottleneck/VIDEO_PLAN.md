# 一个收银窗口关闭后，队伍为什么突然变长？— VIDEO_PLAN

```text
DOCUMENT_ID: CHECKOUT_BOTTLENECK_VIDEO_PLAN
VERSION: R1
DATE: 2026-07-28
STATUS: INITIALIZED_FOR_VIDEO_PRODUCTION_STANDARD_R2
PROJECT_ROOT: D:\blender-video-factory
PROJECT_PATH: D:\blender-video-factory\projects\bvf_test_001_checkout_bottleneck

VIDEO_ID: bvf_test_001_checkout_bottleneck
VIDEO_TITLE: 一个收银窗口关闭后，队伍为什么突然变长？
PLATFORM: 抖音
ASPECT_RATIO: 9:16
TARGET_RESOLUTION: 1080x1920
TARGET_FPS: 30
TARGET_DURATION: 约 11.5 秒 / 约 345 帧

CURRENT_STAGE: P3_ASSET_CANDIDATE_RULING
ACTIVE_TASK_ID: NONE
ACTIVE_TASK_STATUS: AWAITING_USER_AUTHORIZATION
UNIQUE_NEXT_TASK: CHECKOUT_CANDIDATE_01_CAPABILITY_AND_LICENSE_AUDIT

LAST_TECHNICAL_GATE: LEGACY_GRAYBOX_GATE_PASS_ONLY_NOT_VALID_FOR_CURRENT_ASSET_ROUTE
LAST_VISUAL_REVIEW: LEGACY_GRAYBOX_MECHANISM_UNDERSTANDABLE_BUT_PUBLICATION_STYLE_REJECTED; CURRENT_ASSET_FUNCTION_SAMPLE_NOT_FORMALLY_APPROVED
USER_VISUAL_APPROVAL: NOT_GRANTED_FOR_CURRENT_ASSET_ROUTE
CURRENT_APPROVED_BLEND: NONE_FOR_CURRENT_ASSET_ROUTE
CURRENT_APPROVED_PREVIEW: NONE_FOR_CURRENT_ASSET_ROUTE
STOP_LOSS_TRIGGERED: FALSE_FOR_CURRENT_ASSET_ROUTE; TRUE_FOR_LEGACY_NATIVE_GEOMETRY_STYLE_ROUTE

MCP_EXECUTION_STATUS: MUST_REVERIFY_IN_CURRENT_SESSION_AT_P0
MCP_REQUIRED_SUCCESS_SIGNAL: BLENDER_SCRIPT_SUCCESS + BVF_MCP_SMOKE_OK

FORMAL_BUILD_ENTRY: NOT_ASSIGNED
FORMAL_GATE_ENTRY: NOT_ASSIGNED
FORMAL_PREVIEW_ENTRY: NOT_ASSIGNED
FORMAL_FINAL_RENDER_ENTRY: NOT_ASSIGNED
FORMAL_OUTPUT_VALIDATION_ENTRY: NOT_ASSIGNED
```

## 1. 视频目标

使用 Blender 三维动画清楚表现：当三个收银窗口中的中间窗口停止服务后，中间队伍的顾客被迫转向左右窗口，剩余两条队伍因此变长。

最终成片必须让观众即使暂时关闭声音和字幕，也能看懂“服务能力减少，而顾客没有减少，所以拥堵集中到剩余窗口”的因果关系。

## 2. 观众最终应理解的结论

```text
顾客数量没有突然增加
＋
可用收银窗口从三个减少为两个
→
中间队伍被分流到左右队伍
→
剩余队伍明显变长
```

## 3. 已锁定的故事和规格

### 3.1 权威设计文件

```text
projects\bvf_test_001_checkout_bottleneck\design\SCENE_REACTION_TABLE.md
projects\bvf_test_001_checkout_bottleneck\design\ASSET_CAPABILITY_REQUIREMENTS.md
```

### 3.2 故事段落

1. 第一秒钩子：三个窗口和三条队伍同时可读。
2. 正常运转：三条传送带、收银员和队伍正常工作。
3. 中间窗口关闭：绿灯变红、中间传送带停止、关闭标识出现、收银员离开。
4. 顾客分流：M1、M2、M3 依次观察、转身、移动并加入左右队伍。
5. 结果展示：左右队伍明显比开头更长，中间窗口持续关闭。

### 3.3 当前正式范围

最终目标仍是约 11.5 秒、30 FPS、9:16、1080×1920 的完整视频。

当前阶段只处理资产候选裁决。没有完成资产、首帧和功能样片门槛前，不授权完整动画或正式渲染。

## 4. 资产状态

### 4.1 当前正式批准资产

```text
NONE
```

“曾经成功导入或用于实验”不等于已经按新规范获得正式生产批准。

### 4.2 checkout_candidate_01

```text
ROLE: 当前环境与收银设备候选包
KNOWN_LOCAL_INPUT: D:\blender-video-factory\assets\incoming\checkout_candidate_01\
LEGACY_PACKAGE_REFERENCE: Supermercado.zip
CURRENT_DECISION: NEEDS_REVIEW
LICENSE_STATUS: UNKNOWN / NOT FORMALLY RESOLVED
CAPABILITY_STATUS: PARTIALLY_DEMONSTRATED_BY_LEGACY_FUNCTION_SAMPLE
FORMAL_APPROVAL: FALSE
```

已知旧实验曾成功导入 `cashier.fbx`、购物车和部分商品，并在功能样片脚本中使用。但仓库资产审计记录该 Supermarket 来源和许可证未得到可靠确认，因此不能直接进入正式商业成片。

下一任务必须确认：

1. 真实来源与许可证。
2. 收银台、传送带和可动部件结构。
3. 是否可独立控制三条传送带。
4. 收银设备、关闭标识和商品的脚本可控性。
5. 与人物候选的视觉风格匹配度。
6. `READY / EASY_TO_RIG / REQUIRES_MODIFICATION / UNSUITABLE` 裁决。

### 4.3 character_candidate_01

```text
ROLE: 当前收银员与顾客候选包
LEGACY_CHARACTERS: Worker_Male, Casual_Bald
CURRENT_DECISION: NEEDS_SEPARATE_FORMAL_REVIEW
LICENSE_STATUS: NOT CONFIRMED_IN_THIS_PLAN
FORMAL_APPROVAL: FALSE
```

旧功能样片脚本曾加载人物并实现 idle、walk、收银员离开和顾客开始转身，但没有形成当前规范要求的正式孤立资产批准、首帧批准和完整联合场景视觉批准。

在 checkout_candidate_01 完成裁决后，再为 character_candidate_01 创建独立任务；不得在当前任务中同时审核两套候选包。

## 5. 当前阶段状态

| 阶段 | 状态 | 说明 |
|---|---|---|
| P0 环境与入口确认 | NEEDS_RECHECK | 当前会话必须重新验证 blender-mcp `script_execute` 成功标记，不沿用旧会话结果 |
| P1 视频定义与剧情冻结 | COMPLETED | `SCENE_REACTION_TABLE.md` 已存在并覆盖五个段落 |
| P2 资产能力要求冻结 | COMPLETED | `ASSET_CAPABILITY_REQUIREMENTS.md` 已存在，核心互动能力已列出 |
| P3 资产搜索、许可证与候选裁决 | IN_PROGRESS | 当前 checkout 候选来源、许可证和完整能力尚未正式裁决 |
| P4 新资产孤立验证与固定资产库 | NOT_FORMALLY_PASSED | 旧实验不代替正式批准 |
| P5 静态首帧锁定 | NOT_STARTED_UNDER_STANDARD | 当前资产路线没有用户批准的正式首帧 |
| P6 3–5 秒功能样片 | LEGACY_EXPERIMENT_EXISTS_NOT_APPROVED | 脚本实现过六项互动，但联合场景结果没有正式批准 |
| P7 完整动画配置冻结 | NOT_STARTED_FOR_ASSET_ROUTE | 旧 graybox 配置不能直接作为正式资产路线配置 |
| P8 确定性构建 | LEGACY_REFERENCES_ONLY | 现有脚本可参考，不是当前正式入口 |
| P9 项目技术门禁 | LEGACY_GRAYBOX_ONLY | `production_gate.py` 与 graybox 对象和事件帧硬耦合 |
| P10 低清完整预览 | NOT_APPROVED_FOR_ASSET_ROUTE | 没有当前资产路线批准预览 |
| P11 正式渲染与输出验证 | NOT_AUTHORIZED | 不得启动 |
| P12 后期与交付 | NOT_STARTED | 不得启动 |

## 6. 已通过但只能作为参考的历史成果

### 6.1 原生几何 graybox 路线

已证明：

1. Blender 5.1.2、后台执行、PNG 序列和 FFmpeg 技术链可以工作。
2. 345 帧机制动画能够表达窗口关闭、顾客分流和队伍增长。
3. 旧项目门禁可以对 49 个事件帧执行正式预检并阻止失败预览。
4. 角色 Root 层级、相机投影预检和输出验证逻辑可复用。

但该路线因发布级视觉质量未通过而触发止损。不得把 graybox 的技术通过写成当前资产路线已经获得视觉批准。

### 6.2 旧功能样片实验

参考文件：

```text
projects\bvf_test_001_checkout_bottleneck\function_sample_v1_config.json
projects\bvf_test_001_checkout_bottleneck\build_function_sample_v1.py
```

旧实验曾实现：

1. 传送带或商品运动。
2. 指示灯由绿变红。
3. 中间运动停止。
4. 关闭标识出现。
5. 收银员转身离开。
6. 顾客开始转身。

这些结果证明部分互动可以脚本化，但该脚本属于实验性参考，不是当前正式构建入口，也不能代替 P3、P4、P5 和 P6 的正式门槛。

## 7. 用户已批准的视觉版本

```text
CURRENT_ASSET_ROUTE_APPROVED_FIRST_FRAME: NONE
CURRENT_ASSET_ROUTE_APPROVED_FUNCTION_SAMPLE: NONE
CURRENT_ASSET_ROUTE_APPROVED_LOW_RES_PREVIEW: NONE
```

用户只确认继续使用 Blender 资产驱动路线，并把技术路线与执行顺序交给 GPT。用户尚未批准当前资产路线的具体画面。

## 8. 当前阻断问题

### B1：checkout_candidate_01 的来源和许可证未正式确认

许可证未知时不得进入正式商业生产或最终交付。

### B2：checkout_candidate_01 的核心互动能力未形成正式裁决

必须确认传送带、收银台部件、脚本控制和修改成本，不能只依据旧实验“能够导入”。

### B3：当前资产路线没有正式入口

`FORMAL_BUILD_ENTRY`、`FORMAL_GATE_ENTRY`、`FORMAL_PREVIEW_ENTRY`、`FORMAL_FINAL_RENDER_ENTRY` 和 `FORMAL_OUTPUT_VALIDATION_ENTRY` 均未分配。只有资产和首帧路线稳定后才建立，不提前复制旧 graybox 入口冒充正式入口。

### B4：当前会话的 blender-mcp 执行能力未重新验证

下一次需要 Blender 的任务开始前，必须按规范 P0 执行 `BVF_MCP_SMOKE_OK` smoke test，并同时确认 `BLENDER_SCRIPT_SUCCESS` 或当前版本的等价成功信号。

## 9. 当前唯一下一任务

```text
TASK_ID: CHECKOUT_CANDIDATE_01_CAPABILITY_AND_LICENSE_AUDIT
CURRENT_STAGE: P3_ASSET_CANDIDATE_RULING
UNIQUE_MAIN_GOAL: 对 checkout_candidate_01 完成来源、许可证、结构和核心互动能力裁决，决定它是否允许进入当前视频的正式资产路线。
```

任务范围：

1. 只审核 `checkout_candidate_01`。
2. 不同时审核 `character_candidate_01`。
3. 不搭建正式场景。
4. 不创建完整动画。
5. 不修改通用质检代码。
6. 允许为资产检查运行最小 Blender 导入、结构提取和低分辨率接触表，但必须先通过 P0 MCP smoke test。
7. 如果来源和许可证仍无法确认，技术能力可以继续记录，但最终裁决不得为正式 `APPROVED`。

预期输出：

```text
projects\bvf_test_001_checkout_bottleneck\assets\CHECKOUT_CANDIDATE_01_CAPABILITY_AUDIT.md
projects\bvf_test_001_checkout_bottleneck\assets\checkout_candidate_01_structure.json
projects\bvf_test_001_checkout_bottleneck\reviews\checkout_candidate_01_contact_sheet.png
projects\bvf_test_001_checkout_bottleneck\assets\SOURCE_AND_LICENSE.txt
```

通过后才决定：批准该环境候选、换资产，或进入单独的最小改造任务。

## 10. 当前入口映射

### 10.1 当前资产路线正式入口

```text
FORMAL_BUILD_ENTRY: NOT_ASSIGNED
FORMAL_GATE_ENTRY: NOT_ASSIGNED
FORMAL_PREVIEW_ENTRY: NOT_ASSIGNED
FORMAL_FINAL_RENDER_ENTRY: NOT_ASSIGNED
FORMAL_OUTPUT_VALIDATION_ENTRY: NOT_ASSIGNED
```

### 10.2 旧项目参考入口

```text
LEGACY_GRAYBOX_BUILD_ENTRY:
projects\bvf_test_001_checkout_bottleneck\build_graybox.py

LEGACY_GRAYBOX_GATE_ENTRY:
projects\bvf_test_001_checkout_bottleneck\production_gate.py

LEGACY_GRAYBOX_KEYFRAME_RENDER_ENTRY:
projects\bvf_test_001_checkout_bottleneck\_gate_render.py

LEGACY_GRAYBOX_FULL_PREVIEW_ENTRY:
projects\bvf_test_001_checkout_bottleneck\render_variant_b_full_preview.py

LEGACY_ASSET_FUNCTION_SAMPLE_BUILD_REFERENCE:
projects\bvf_test_001_checkout_bottleneck\build_function_sample_v1.py
```

以上全部标记为 `LEGACY_REFERENCE_ONLY`。没有 GPT 明确重新指定并验证前，不得用它们授权当前资产路线的正式渲染。

## 11. 推迟的 QUALITY 与 TECH_DEBT

### QUALITY

1. 当前资产路线的美术方向和首帧吸引力尚未审核。
2. 人物候选和环境候选的风格匹配尚未正式比较。
3. 功能样片节奏和联合场景观感尚未正式批准。

### TECH_DEBT

1. 当前仓库没有独立命名为 `blender_output_artifact_check` 的通用输出入口。
2. 旧门禁 JSON 字段与新规范建议语义尚未统一。
3. 旧项目目录未迁移到新模板；当前不要求迁移。
4. 通用质检不验证动作自然度和完整时间轴连续性，必须由项目补充检查与人工审核覆盖。

这些内容不阻止当前 P3 资产裁决。

## 12. 状态更新权限

1. Claude Code 可以在本轮明确授权时更新真实资产审核结果，但不能自行把用户视觉批准写为 `APPROVED`。
2. GPT 审核 Claude 的交付后，决定是否更新 `CURRENT_STAGE` 和 `UNIQUE_NEXT_TASK`。
3. 用户负责最终审美批准、继续投入、止损和发布决定。
4. 任何正式入口必须在真实存在并通过最小验证后才能从 `NOT_ASSIGNED` 改为具体路径。

## 13. R1 初始化依据

本文件根据以下现有仓库材料和用户已确认状态初始化：

```text
CLAUDE.md
VIDEO_PRODUCTION_EXECUTION_STANDARD_R2.md
projects\bvf_test_001_checkout_bottleneck\design\SCENE_REACTION_TABLE.md
projects\bvf_test_001_checkout_bottleneck\design\ASSET_CAPABILITY_REQUIREMENTS.md
projects\bvf_test_001_checkout_bottleneck\function_sample_v1_config.json
projects\bvf_test_001_checkout_bottleneck\build_function_sample_v1.py
projects\bvf_test_001_checkout_bottleneck\production_gate.py
projects\bvf_test_001_checkout_bottleneck\FINAL_VALIDATION_REPORT.md
reports\ASSET_AUDIT.md
```

无法由当前仓库或用户已确认结果唯一确定的内容均保留为 `NONE`、`NOT_ASSIGNED`、`UNKNOWN` 或 `NEEDS_REVIEW`，不得擅自补全。
