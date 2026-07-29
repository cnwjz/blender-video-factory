# 一个收银窗口关闭后，队伍为什么突然变长？— VIDEO_PLAN

```text
DOCUMENT_ID: CHECKOUT_BOTTLENECK_VIDEO_PLAN
VERSION: R3
DATE: 2026-07-29
STATUS: PENDING_USER_APPROVAL
ALIGNED_STANDARD: VIDEO_PRODUCTION_EXECUTION_STANDARD R4
ALIGNED_CLAUDE_RULES: BVF_PROJECT_CLAUDE_RULES R4
PROJECT_ROOT: D:\blender-video-factory
PROJECT_PATH: D:\blender-video-factory\projects\bvf_test_001_checkout_bottleneck

VIDEO_ID: bvf_test_001_checkout_bottleneck
VIDEO_TITLE: 一个收银窗口关闭后，队伍为什么突然变长？
PLATFORM: 抖音
ASPECT_RATIO: 9:16
ENGINEERING_VALIDATION_ASPECT_RATIO: 9:16
TARGET_RESOLUTION: 1080x1920
TARGET_FPS: 30
TARGET_DURATION: 约 11.5 秒 / 约 345 帧

CURRENT_STAGE: P4_ASSET_TEMPLATE_BASELINE
CURRENT_PROBLEM_ID: P4_CHECKOUT_ASSET_BASELINE
PROBLEM_IMPLEMENTATION_COUNT: 0
PROBLEM_CORRECTION_COUNT: 0
ACTIVE_TASK_ID: NONE
ACTIVE_TASK_STATUS: AWAITING_USER_AUTHORIZATION
UNIQUE_NEXT_TASK: FREEZE_AND_MEASURE_MANUAL_REFERENCE_V1

LAST_TECHNICAL_GATE: LEGACY_MINIMUM_ASSET_VALIDATION_ONLY
LAST_VISUAL_REVIEW: USER_CONFIRMED_CASHIER_SIZE_AND_POSITION_FOR_CALIBRATION
USER_VISUAL_APPROVAL: MANUAL_REFERENCE_APPROVED_FOR_EXTRACTION_ONLY

CURRENT_MANUAL_REFERENCE: scene\formal_first_frame_manual_layout_v1.blend
CURRENT_MANUAL_REFERENCE_STATUS: USER_CONFIRMED_PATH_PENDING_FRESH_PROCESS_VERIFICATION
CURRENT_APPROVED_ASSET_TEMPLATE: NONE
CURRENT_APPROVED_WORLD_LAYOUT: NONE
CURRENT_APPROVED_SHOT: NONE
CURRENT_APPROVED_BLEND: NONE
CURRENT_APPROVED_PREVIEW: NONE

STOP_LOSS_TRIGGERED: FALSE
HISTORICAL_STOP_LOSS_RECORDS: P5_FIRST_FRAME_COMPOSITION

MCP_EXECUTION_STATUS: MUST_REVERIFY_WHEN_NEXT_BLENDER_TASK_STARTS
MCP_REQUIRED_SUCCESS_SIGNAL: BLENDER_SCRIPT_SUCCESS + BVF_MCP_SMOKE_OK

FORMAL_BUILD_ENTRY: NOT_ASSIGNED
FORMAL_GATE_ENTRY: NOT_ASSIGNED
FORMAL_PREVIEW_ENTRY: NOT_ASSIGNED
FORMAL_FINAL_RENDER_ENTRY: NOT_ASSIGNED
FORMAL_OUTPUT_VALIDATION_ENTRY: NOT_ASSIGNED
```

`STOP_LOSS_TRIGGERED` 只表示当前 `P4_CHECKOUT_ASSET_BASELINE` 问题的状态。旧 P5 首帧构图问题已经触发止损，记录在第 9 节，不因开启新的基础问题而清零。

## 1. 视频目标

使用 Blender 三维动画清楚表现：

> 当三个收银窗口中的中间窗口停止服务后，中间队伍的顾客被迫转向左右窗口，剩余两条队伍因此变长。

最终成片必须让观众即使关闭声音和字幕，也能看懂：

```text
顾客数量没有增加
＋
可用收银窗口从三个减少为两个
→
中间队伍分流到左右队伍
→
剩余两条队伍明显变长
```

## 2. 已锁定的故事和规格

### 2.1 权威设计文件

```text
projects\bvf_test_001_checkout_bottleneck\design\SCENE_REACTION_TABLE.md
projects\bvf_test_001_checkout_bottleneck\design\ASSET_CAPABILITY_REQUIREMENTS.md
```

### 2.2 故事段落

1. 第一秒钩子：三个窗口和三条队伍同时可读。
2. 正常运转：三个窗口和三条队伍处于正常服务状态。
3. 中间窗口关闭：状态标识改变、中间服务停止、收银员离开。
4. 顾客分流：中间队伍顾客依次观察、转身并加入左右队伍。
5. 结果展示：顾客总数不变，左右队伍比开头明显变长，中间窗口持续关闭。

### 2.3 最终发布规格

```text
最终发布画幅：9:16
目标分辨率：1080x1920
帧率：30 FPS
时长：约 11.5 秒
```

最终发布规格不因当前基础修正而改变。

当前有效工程验证画幅与最终发布画幅相同，均为 9:16。未来可以由用户明确批准改用 16:9 制作最小端到端工程样片；在该批准真实发生并写入本计划前，16:9 只属于候选方案，不得替代当前有效的 9:16 工程验证画幅。

当前只授权整理项目状态。尚未授权打开或保存 `.blend`、运行 Blender、制作动画、完整预览或正式渲染。

## 3. 当前可发布级标准

本视频达到以下条件即可视为具备发布价值，不在生产中临时提高为电影级或广告级标准：

1. 三个收银窗口和三条队伍在开头清楚可读。
2. 中间窗口关闭后，顾客向左右分流的因果一眼可懂。
3. 顾客总量没有通过新增角色制造“队伍变长”的假象。
4. 人物没有明显滑步、横躺、漂浮、穿模或被关键性裁切。
5. 收银设备、人物、环境的比例和空间关系基本可信。
6. 材质和灯光能够清楚表达主体，不呈现明显诊断图或默认练习效果。
7. 完整成片具备字幕、必要音效和清楚节奏。
8. 视频干净、完整、可解码，用户愿意发布。

这些发布级标准不等于当前 P4 资产模板任务的全部验收标准。当前任务只处理会阻断可靠布局和镜头生产的收银台基准问题。

## 4. 当前正式生产资产路线

### 4.1 环境与收银设备

```text
ASSET_ROUTE: PensamientoAzul Supermarket 3D Assets
RAW_GEOMETRY_SOURCE: cashier.fbx
LOCAL_PACKAGE_REFERENCE: Supermercado.zip
SOURCE_STATUS: CONFIRMED_FOR_CURRENT_ROUTE
LICENSE_STATUS: CONFIRMED_IN_COMPLETED_ASSET_REVIEW
TECHNICAL_CAPABILITY: CONFIRMED
MANUAL_CALIBRATION_REFERENCE: scene\formal_first_frame_manual_layout_v1.blend
APPROVED_TEMPLATE_STATUS: NOT_CREATED
FORMAL_LAYOUT_ELIGIBILITY: BLOCKED_UNTIL_TEMPLATE_APPROVED
```

已确认的技术事实：

1. `cashier.fbx` 可以成功导入 Blender。
2. 收银台由 4 个独立 Mesh 组成。
3. 传送带表面可以独立控制。
4. 三个收银台实例可以分别控制。
5. 这些事实只证明原始资产具备技术能力，不证明正式世界尺寸、贴地、方向或布局已经批准。

三种来源的职责：

```text
cashier.fbx
→ 原始几何来源

scene\formal_first_frame_manual_layout_v1.blend
→ 用户确认的视觉尺寸、位置和空间关系参考
→ 身份为 MANUAL_REFERENCE

未来批准的收银台模板
→ 通过必要机器门禁和用户视觉确认后形成
→ 正式视频生产唯一默认收银台来源
```

用户报告人工参考场景中收银台父级 Scale 为：

```text
X = 13.154
Y = 35.448
Z = 18.330
```

这组数值只说明当前导入层级如何达到用户认可的可见效果，不是批准模板合同。正式基准必须记录可见几何的组合世界尺寸、最低点、方向、结构和锚点，不得把非均匀父级 Scale 直接复制成长期规则。

不得继续沿用“根据人物、相机和画面构图反复重新决定正式比例”的旧假设。

正确规则：

```text
先从 MANUAL_REFERENCE 提取并批准收银台世界空间基准
→ 再派生批准模板
→ 后续布局和相机只能使用批准尺寸
→ 不得为了构图重新缩放收银台
```

### 4.2 人物

```text
ASSET_ROUTE: Quaternius Ultimate Animated Character Pack
PRIMARY_CHARACTER_REFERENCE: Casual_Male.blend
LICENSE_STATUS: CC0
IMPORT_METHOD: BLEND_APPEND
TECHNICAL_CAPABILITY: CONFIRMED
VISUAL_APPROVAL: PENDING_FORMAL_SCENE
```

已确认的技术事实：

1. 人物应通过原生 `.blend` Append 进入项目。
2. Armature Modifier 能够保留。
3. Idle 和 Walk 动作真实存在。
4. Walk 是原地循环动作，不依靠静态姿势平移冒充行走。
5. 世界空间位移应由人物顶层控制对象承担。
6. `CharacterRootControl` 路线能够在不破坏骨骼动画的情况下控制人物移动。
7. 足部高度在步态周期中真实变化。
8. 资产可以在 EEVEE 中正常显示。

当前 P4 问题只处理收银台基准。不得顺便修改人物资产路线、人物比例、骨骼、动作、材质或正式动画。人物尺寸和贴地只在后续布局门禁中按真实需要检查。

## 5. 当前阶段状态

| 阶段 | 状态 | 说明 |
|---|---|---|
| P0 环境与入口确认 | RECHECK_WHEN_NEEDED | 下一次授权 Blender 任务时重新运行最小 MCP smoke test |
| P1 视频定义与剧情冻结 | COMPLETED | 核心结论和五段故事已经冻结 |
| P2 资产能力要求冻结 | COMPLETED | 核心互动能力已经明确 |
| P3 资产搜索、许可证与候选裁决 | COMPLETED | PensamientoAzul 与 Quaternius 路线已选定 |
| P4 新资产孤立验证与固定资产库 | CURRENT_STAGE | 原始资产最低技术能力已证明；批准收银台模板尚未创建；当前先冻结并测量人工参考场景 |
| P5A 世界布局批准 | NOT_STARTED | 等收银台批准模板和布局合同完成后开始 |
| P5B 镜头构图批准 | NOT_STARTED | 等世界布局获得批准后开始；不得继续直接生成相机方案 |
| P6 3–5 秒核心功能样片 | NOT_STARTED | 正式镜头批准后再开始 |
| P7 完整动画配置冻结 | NOT_STARTED | 功能样片通过后再开始 |
| P8 确定性构建 | NOT_ASSIGNED | 正式入口将在真实脚本存在并验证后填写 |
| P9 项目技术门禁与统一编排 | NOT_ASSIGNED_FOR_CURRENT_ROUTE | 旧 graybox 门禁不能授权当前路线；当前项目 G0/G1 尚未接入 |
| P10 完整低清预览 | NOT_STARTED | 完整动画和必要门禁通过后开始 |
| P11 正式渲染与输出验证 | NOT_AUTHORIZED | 当前不得启动 |
| P12 后期包装与交付 | NOT_STARTED | 当前不得启动 |

当前阶段从 P5 调整为 P4，不是推翻视频路线，而是补回此前被错误跳过的资产基准层。旧 P5 结果保留为历史证据，不作为当前继续修补的候选。

## 6. 当前已确认的技术事实

以下事实可以直接用于后续生产，不需要再次启动同类资产接触表验证：

1. PensamientoAzul 收银台可以作为三个独立窗口使用。
2. 收银台传送带表面可以独立控制。
3. Quaternius 人物采用 `.blend` Append。
4. 人物的 Armature、Mesh 和动作路线可保留。
5. Idle 可以用于静态排队和等待。
6. Walk 可以循环播放。
7. 人物世界位移由顶层 Root 控制，不能用固定姿势滑行代替。
8. Blender 5.1.2 和 EEVEE 可以执行当前资产路线的最小渲染。
9. 当前资产路线足以进入资产基准提取和批准模板派生。
10. 当前没有批准的收银台资产模板、世界布局、镜头或正式首帧。
11. 当前没有真实结果证明旧正式首帧已经通过视觉审核。
12. 通用检查器存在不等于收银台已经被项目门禁配置和检查。

## 7. 当前人工参考及批准边界

```text
REFERENCE_PATH: scene\formal_first_frame_manual_layout_v1.blend
IDENTITY: MANUAL_REFERENCE
SOURCE_OF_TRUTH_FOR: 用户认可的收银台可见尺寸、贴地结果和收银台之间的位置参考
NOT_APPROVED_AS: 资产模板、世界布局、正式镜头或正式首帧
```

用户已确认该人工场景中的收银台大小和位置在视觉上正确。因此它可以作为只读标定来源。人工场景中的人物站位、完整世界布局、相机、灯光和材质不因本次确认自动获得批准。开始模板派生前必须先完成：

1. 文件真实存在性和身份验证。
2. 只读打开。
3. 组合世界包围盒尺寸提取。
4. 世界空间最低点和地面关系提取。
5. 对象层级、世界矩阵和实例一致性提取。
6. 正面、顾客侧和队伍延伸方向确认。
7. 统一诊断视图比较。
8. 用户确认提取结果代表人工场景中的正确答案。

在这些步骤完成前：

```text
CURRENT_APPROVED_ASSET_TEMPLATE: NONE
CURRENT_APPROVED_WORLD_LAYOUT: NONE
CURRENT_APPROVED_SHOT: NONE
```

不得把人工参考原件直接复制到 `APPROVED`，也不得覆盖、Apply Transform、清理层级、重新导入资产或保存修改。

## 8. 当前阻断问题

### 当前 P4 问题的 BLOCKER

#### B1：没有批准的收银台资产模板

当前只有原始 `cashier.fbx` 和人工参考场景。正式布局仍缺少稳定、可重复 Append 的批准模板。

#### B2：人工参考场景尚未冻结并提取世界空间事实

当前知道用户认可画面，但没有机器可读的世界尺寸、最低点、方向、层级和实例一致性结果。

#### B3：批准基准尚未形成

父级 Scale 不能代替可见几何的世界空间合同。没有批准基准时，Claude Code 仍可能在下一场景中重新猜测大小、位置和贴地。

### P4 完成前必须解决的阻断

#### B4：G0 资产门禁尚未接入当前收银台模板路线

现有通用检查器尚未被当前项目正式配置并调用来检查收银台模板身份、世界尺寸、最低点、方向、结构和保存重开一致性。批准收银台模板前必须建立并通过 G0；G1 不属于 P4 的完成条件。

### 开始 P5A 布局施工前必须准备的条件

#### B5：批准布局合同、布局构建入口和 G1 配置尚未建立

当前人工场景可以提供关系参考，但不能直接代替可重复构建的批准布局合同、确定性布局入口和 G1 检查配置。P5A 阶段内才生成世界布局候选、运行 G1，并由用户批准世界布局；这些结果不要求在进入 P5A 前预先完成。

B4 和 B5 不阻止当前只读测量任务。B4 必须在批准收银台模板前解决；B5 必须在开始 P5A 布局施工前准备完成。

## 9. 历史问题与止损记录

```text
HISTORICAL_PROBLEM_ID: P5_FIRST_FRAME_COMPOSITION
STATUS: STOP_LOSS_TRIGGERED
RESULT: CLOSED_PENDING_FOUNDATION_REBUILD
IMPLEMENTATION_AND_ATTEMPTS: V1 / V2 / V3 / ALT_V1
```

历史事实：

1. V1、V2、V3 和 ALT_V1 均生成过实际 PNG。
2. 四版均未满足“三个收银窗口第一眼清楚可读、三条队伍完整、主体占比合理”的冻结标准。
3. 旧任务连续修改相机、构图、布局或资产表现，但基础资产尺寸、贴地和布局合同没有先被冻结。
4. 旧首帧失败不能再只归因于相机，也不能继续生成第五个相机方案。
5. V1、V2、V3 和 ALT_V1 均不得重新激活为当前唯一任务或下一阶段输入。

旧问题的止损记录永久保留。当前开启的是新的 `P4_CHECKOUT_ASSET_BASELINE`，其次数从 0 开始；这不表示旧问题被删除或重置。

## 10. 当前唯一下一任务

```text
PROBLEM_ID: P4_CHECKOUT_ASSET_BASELINE
TASK_ID: FREEZE_AND_MEASURE_MANUAL_REFERENCE_V1
CURRENT_STAGE: P4_ASSET_TEMPLATE_BASELINE
INPUT_IDENTITY: MANUAL_REFERENCE
TASK_STATUS_BEFORE_START: AWAITING_USER_AUTHORIZATION
```

### 唯一目标

只读冻结并测量用户确认的人工参考场景，为下一轮派生收银台候选模板建立可信基准。

### 允许执行

1. 在下一次任务开始时重新确认 MCP 或后台 Blender 执行能力。
2. 验证人工参考路径真实存在。
3. 记录来源路径、文件大小、修改时间和一个用于识别原件的哈希值。
4. 在全新 Blender 进程中只读打开人工参考场景。
5. 提取收银台对象层级、对象身份和子 Mesh 结构。
6. 提取每台收银台的组合世界包围盒尺寸。
7. 提取世界空间最低点、地面高度和贴地差值。
8. 提取世界矩阵、正面方向、顾客侧和队伍延伸方向。
9. 比较三台收银台实例的可见几何尺寸和结构一致性。
10. 记录与收银台有关的候选锚点位置，但不得自行批准锚点。
11. 生成正面、侧面、俯视和透视等必要诊断视图。
12. 输出最小测量结果，等待 GPT 和用户确认。

### 禁止执行

1. 不得保存、覆盖或修改人工参考原件。
2. 不得 Apply Transform、整理层级、移动对象或改变 Scale。
3. 不得重新导入 `cashier.fbx`。
4. 不得创建候选或批准资产模板。
5. 不得创建或修改布局合同。
6. 不得调整人物、相机、灯光或材质。
7. 不得制作动画、样片、完整预览或正式渲染。
8. 不得自动进入模板派生任务。

### 预期最小产物

```text
一个结构化测量结果
必要的统一诊断视图
原件未被修改的确认
```

具体脚本名和输出路径只有在文件真实创建并验证后才写入正式入口，不在本计划中预先猜测。

### 通过条件

1. 人工参考文件真实存在并可由全新 Blender 进程打开。
2. 提取结果来自可见几何的世界空间状态，而不是只读取父级 Scale。
3. 三台收银台的尺寸、最低点、方向和结构得到明确记录。
4. 诊断视图能够让 GPT 和用户核对提取对象是否正确。
5. 人工参考原件未被修改。
6. 用户确认测量结果可以作为候选模板派生的基准。

如果第 6 项尚未发生，执行报告必须保持 `TASK_STATUS: PARTIAL`、`USER_APPROVAL: PENDING`。可以如实报告候选测量产物已生成，但不得将测量结果晋升为批准合同，也不得开始下一阶段。

## 11. 当前正式入口映射

```text
FORMAL_BUILD_ENTRY: NOT_ASSIGNED
FORMAL_GATE_ENTRY: NOT_ASSIGNED
FORMAL_PREVIEW_ENTRY: NOT_ASSIGNED
FORMAL_FINAL_RENDER_ENTRY: NOT_ASSIGNED
FORMAL_OUTPUT_VALIDATION_ENTRY: NOT_ASSIGNED
```

尚未进入相应阶段的入口保持 `NOT_ASSIGNED`，不阻断当前只读测量任务。入口只有在真实脚本存在并完成最小验证后才能填写。

### 旧项目参考入口

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

以上均为 `LEGACY_REFERENCE_ONLY`。没有 GPT 明确重新指定并验证前，不得用它们授权当前资产路线。

## 12. 推迟的 QUALITY 与 TECH_DEBT

### QUALITY

1. Quaternius 人物与 PensamientoAzul 环境可能存在风格差异，后续通过正式场景判断。
2. 设备关闭状态的最终视觉表现尚未冻结。
3. 正式字幕、音效和节奏尚未设计。
4. 最终 9:16 可能需要拆镜头，而不是强迫全部故事进入单个首帧。

以上内容不属于当前只读测量任务，不得顺便处理。

### TECH_DEBT

1. 当前资产路线的正式构建、门禁、预览和输出验证入口尚未分配。
2. 旧 graybox 门禁与当前资产对象命名和剧情事件不兼容。
3. 当前仓库没有独立命名为 `blender_output_artifact_check` 的通用输出入口。
4. 通用质检不能判断动作自然度、完整时间轴连续性和画面审美。

这些问题不阻止当前 P4 测量任务。只有直接阻断后续批准模板、布局或输出时才进入对应任务。

## 13. 状态更新权限

1. Claude Code 只能报告真实执行事实，不能自行写入用户视觉批准。
2. GPT 可以批准纯技术配置、脚本和机器门禁结果。
3. 用户负责核心资产视觉比例、世界布局、镜头、样片、完整预览和成片等视觉批准。
4. `TASK_STATUS: COMPLETED` 不等于阶段批准，也不允许候选自动晋升。
5. GPT 必须读取原始机器结果；视觉任务必须查看实际 PNG 或 MP4 后再提出批准建议。
6. 正式入口必须在文件真实存在并通过最小验证后才能从 `NOT_ASSIGNED` 改为具体路径。
7. 当前收银台模板未批准前，不得把 `CURRENT_STAGE` 改为 P5A。
8. 世界布局未批准前，不得进入 P5B 相机定稿。
9. 当前 `P4_CHECKOUT_ASSET_BASELINE` 的修正次数必须按同一 `PROBLEM_ID` 记录，不能通过改任务名重置。
10. 仍有修正额度不等于已经获得修正授权。

## 14. R3 更新依据与范围

本次更新依据：

```text
CLAUDE.md R4
VIDEO_PRODUCTION_EXECUTION_STANDARD.md R4
原 VIDEO_PLAN.md R2
当前资产技术验证结果
四版正式首帧未批准的历史事实
用户确认的人工参考场景和收银台视觉尺寸、位置
本轮对资产基准、布局、门禁和止损问题的讨论结论
```

本次更新只调整项目状态和生产顺序：

1. 不修改视频故事。
2. 不修改最终 9:16 发布规格。
3. 不更换现有资产路线。
4. 不删除旧首帧失败和止损记录。
5. 将当前阶段从 P5 纠正为 P4 资产模板基准。
6. 登记人工参考场景，但不把它冒充批准模板。
7. 建立新的 `P4_CHECKOUT_ASSET_BASELINE` 问题和次数记录。
8. 把唯一下一任务改为只读冻结与测量。
9. 禁止继续直接调相机、制作动画或自动推进。
10. 不运行 Blender、测试、质检或渲染。

## 15. R2 历史更新记录

R2 曾依据当时的 R3 生产规范同步资产技术路线、旧 P5 状态和唯一下一任务。R2 保留的有效历史事实包括：

1. 视频题目和核心因果已冻结。
2. PensamientoAzul 与 Quaternius 资产路线已选择。
3. 收银台结构、多实例控制、人物 Append、Idle、Walk 和 Root 位移技术路线已得到最低验证。
4. V1、V2、V3 和 ALT_V1 均未获得正式首帧视觉批准。
5. 旧 graybox 入口不能授权当前真实资产路线。

R3 根据后续真实生产问题纠正了 R2 中“原始资产最低技术通过即可直接进入首帧”和“正式比例由相机与构图重新决定”的错误前提。
