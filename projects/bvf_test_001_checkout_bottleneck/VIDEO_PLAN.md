# 一个收银窗口关闭后，队伍为什么突然变长？— VIDEO_PLAN

```text
DOCUMENT_ID: CHECKOUT_BOTTLENECK_VIDEO_PLAN
VERSION: R2
DATE: 2026-07-29
STATUS: UPDATED_FOR_VIDEO_PRODUCTION_STANDARD_R3
PROJECT_ROOT: D:\blender-video-factory
PROJECT_PATH: D:\blender-video-factory\projects\bvf_test_001_checkout_bottleneck

VIDEO_ID: bvf_test_001_checkout_bottleneck
VIDEO_TITLE: 一个收银窗口关闭后，队伍为什么突然变长？
PLATFORM: 抖音
ASPECT_RATIO: 9:16
TARGET_RESOLUTION: 1080x1920
TARGET_FPS: 30
TARGET_DURATION: 约 11.5 秒 / 约 345 帧

CURRENT_STAGE: P5_FORMAL_FIRST_FRAME
ACTIVE_TASK_ID: NONE
ACTIVE_TASK_STATUS: AWAITING_USER_AUTHORIZATION
UNIQUE_NEXT_TASK: FORMAL_FIRST_FRAME_V1

LAST_TECHNICAL_GATE: ASSET_ROUTE_MINIMUM_TECHNICAL_VALIDATION_COMPLETED
LAST_VISUAL_REVIEW: ASSET_DIAGNOSTIC_OUTPUT_NOT_ACCEPTED_AS_FORMAL_VISUAL_APPROVAL
USER_VISUAL_APPROVAL: NOT_GRANTED_FOR_FORMAL_FIRST_FRAME
CURRENT_APPROVED_BLEND: NONE
CURRENT_APPROVED_PREVIEW: NONE
STOP_LOSS_TRIGGERED: FALSE

MCP_EXECUTION_STATUS: MUST_REVERIFY_WHEN_NEXT_BLENDER_TASK_STARTS
MCP_REQUIRED_SUCCESS_SIGNAL: BLENDER_SCRIPT_SUCCESS + BVF_MCP_SMOKE_OK

FORMAL_BUILD_ENTRY: NOT_ASSIGNED
FORMAL_GATE_ENTRY: NOT_ASSIGNED
FORMAL_PREVIEW_ENTRY: NOT_ASSIGNED
FORMAL_FINAL_RENDER_ENTRY: NOT_ASSIGNED
FORMAL_OUTPUT_VALIDATION_ENTRY: NOT_ASSIGNED
```

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

### 2.3 当前成片范围

```text
画幅：9:16
目标分辨率：1080x1920
帧率：30 FPS
时长：约 11.5 秒
```

当前只进入正式首帧阶段，不授权完整动画、完整预览或正式渲染。

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

## 4. 当前正式生产资产路线

### 4.1 环境与收银设备

```text
ASSET_ROUTE: PensamientoAzul Supermarket 3D Assets
LOCAL_PACKAGE_REFERENCE: Supermercado.zip
PRIMARY_CHECKOUT_ASSET: cashier.fbx
SOURCE_STATUS: CONFIRMED_FOR_CURRENT_ROUTE
LICENSE_STATUS: CONFIRMED_IN_COMPLETED_ASSET_REVIEW
TECHNICAL_DECISION: SELECTED_FOR_FORMAL_FIRST_FRAME
VISUAL_APPROVAL: PENDING_FORMAL_FIRST_FRAME
```

已确认的技术事实：

1. `cashier.fbx` 可以成功导入 Blender。
2. 收银台由 4 个独立 Mesh 组成。
3. 传送带表面可以独立控制。
4. 三个收银台实例可以分别控制。
5. 资产可以进入正式首帧进行比例、构图和风格审核。

边界：

1. 诊断阶段使用过的放大比例只用于确认结构，不是正式首帧比例。
2. 正式比例必须根据人物、相机和画面构图重新决定。
3. 技术可用不等于视觉路线已经获得用户批准。

### 4.2 人物

```text
ASSET_ROUTE: Quaternius Ultimate Animated Character Pack
PRIMARY_CHARACTER_REFERENCE: Casual_Male.blend
LICENSE_STATUS: CC0
IMPORT_METHOD: BLEND_APPEND
TECHNICAL_DECISION: SELECTED_FOR_FORMAL_FIRST_FRAME
VISUAL_APPROVAL: PENDING_FORMAL_FIRST_FRAME
```

已确认的技术事实：

1. 人物应通过原生 `.blend` Append 进入项目。
2. Armature Modifier 能够保留。
3. Idle 和 Walk 动作真实存在。
4. Walk 是原地循环动作，不依靠静态姿势平移冒充行走。
5. 世界空间位移应由人物顶层控制对象承担。
6. `CharacterRootControl` 路线能够在不破坏骨骼动画的情况下控制人物移动。
7. 足部高度在步态周期中真实变化，证明 Walk 动作不是固定姿势。
8. 资产可以在 EEVEE 中正常显示并进入正式首帧。

边界：

1. 当前只证明技术路线可行。
2. 诊断接触表没有形成正式视觉批准。
3. 人物与超市场景是否风格协调，必须通过正式首帧判断。

## 5. 当前阶段状态

| 阶段 | 状态 | 说明 |
|---|---|---|
| P0 环境与入口确认 | RECHECK_WHEN_NEEDED | 下一次需要 Blender 时重新运行最小 MCP smoke test |
| P1 视频定义与剧情冻结 | COMPLETED | 核心结论和五段故事已经冻结 |
| P2 资产能力要求冻结 | COMPLETED | 核心互动能力已经明确 |
| P3 资产搜索、许可证与候选裁决 | COMPLETED | PensamientoAzul 与 Quaternius 路线已选定 |
| P4 新资产孤立验证 | MINIMUM_TECHNICAL_PASS | 已证明正式首帧所需的最低技术能力；诊断图不构成视觉批准 |
| P5 静态首帧锁定 | CURRENT_STAGE | 尚无正式首帧，下一任务直接制作首帧 V1 |
| P6 3–5 秒核心功能样片 | NOT_STARTED | 首帧批准后再开始 |
| P7 完整动画配置冻结 | NOT_STARTED | 功能样片通过后再开始 |
| P8 确定性构建 | NOT_ASSIGNED | 正式入口将在实际脚本存在并验证后填写 |
| P9 项目技术门禁 | LEGACY_REFERENCE_ONLY | 旧 graybox 门禁不能直接授权当前资产路线 |
| P10 完整低清预览 | NOT_STARTED | 完整动画和必要门禁通过后再开始 |
| P11 正式渲染与输出验证 | NOT_AUTHORIZED | 当前不得启动 |
| P12 后期包装与交付 | NOT_STARTED | 当前不得启动 |

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
9. 当前资产路线在技术上足以进入正式首帧。
10. 当前没有任何真实结果证明正式画面已经通过视觉审核。

## 7. 已完成但不作为正式视觉批准的验证

资产技术验证已经完成其最低目的：

1. 证明收银台结构和多实例控制可行。
2. 证明人物原生 Append、Idle、Walk 和 Root 位移可行。
3. 证明当前资产组合能够在 Blender 中渲染。

现有诊断输出存在裁切、重叠或无法直接展示正式构图的问题，因此：

```text
不得把诊断接触表写为正式首帧
不得把技术数据写为视觉通过
不得继续为了美化诊断接触表而推迟正式生产
```

资产验证任务的自动修正额度已经用完。除非用户明确重新授权，不再启动第三轮接触表修正任务。

## 8. 用户已批准的视觉版本

```text
APPROVED_ASSET_STYLE_ROUTE: NOT_YET
APPROVED_FORMAL_FIRST_FRAME: NONE
APPROVED_CORE_FUNCTION_SAMPLE: NONE
APPROVED_LOW_RES_PREVIEW: NONE
APPROVED_FINAL_VIDEO: NONE
```

用户已同意继续使用当前技术路线进行下一步生产，但尚未批准任何正式画面。

## 9. 当前阻断问题

### B1：没有接近成片的正式首帧

当前没有一张真实画面能够证明三个窗口、三条队伍和整体空间关系清楚可读。

### B2：核心因果所需的空间构图尚未得到视觉证明

必须先证明开头的三个窗口和三条队伍可以在 9:16 画面中同时清楚呈现，之后才值得扩展动画。

### B3：正式比例、材质和灯光尚未冻结

诊断阶段参数不能直接作为成片参数。收银台比例、人物大小、材质表现、环境亮度和相机位置必须通过正式首帧共同确定。

### B4：当前资产组合尚未获得用户视觉批准

技术可行不能代替风格和发布价值判断。正式首帧是当前唯一需要解决的视觉门槛。

### P0 前置条件

下一次执行 Blender 任务时，需要重新确认当前会话的 MCP 和后台执行能力。该检查属于正式首帧任务的最小前置步骤，不单独形成新的项目阶段或报告任务。

## 10. 当前唯一下一任务

```text
TASK_ID: FORMAL_FIRST_FRAME_V1
CURRENT_STAGE: P5_FORMAL_FIRST_FRAME
UNIQUE_MAIN_GOAL: 使用已选定的 PensamientoAzul 收银台与 Quaternius 人物，制作一张接近最终成片效果的 9:16 正式首帧，让三个收银窗口、三条队伍和整体空间关系清楚可读。
```

### 10.1 允许范围

1. Append 已验证的人物资产。
2. 导入或使用已选定的收银台与必要超市场景资产。
3. 创建三个收银窗口和三条队伍。
4. 调整人物和设备的正式比例、位置和朝向。
5. 设置正式首帧所需的相机、灯光、环境和材质表现。
6. 创建或修改完成首帧所需的最小确定性脚本。
7. 保存新的版本化 `.blend`。
8. 渲染一张低成本审核分辨率的 9:16 正式首帧。

### 10.2 禁止范围

1. 不创建完整动画。
2. 不制作 3–5 秒功能样片。
3. 不制作完整低清预览。
4. 不进行正式全分辨率帧序列渲染。
5. 不扩建通用质检系统。
6. 不运行完整测试回归。
7. 不生成 Contact Sheet。
8. 不生成复杂 JSON、审计报告、证据包、Manifest 或 ZIP。
9. 不自动进入 P6。

### 10.3 首帧验收标准

1. 画幅为 9:16，建议审核分辨率为 540x960。
2. 三个收银窗口全部清楚可见，并能区分左、中、右。
3. 三条队伍全部清楚可读，不因人物严重重叠而混成一团。
4. 中间窗口和中间队伍的位置关系清楚，为后续关闭与分流留下可见空间。
5. 人物没有明显横躺、漂浮、穿模、异常缩放或关键性裁切。
6. 收银台、人物和环境比例基本可信。
7. 画面具备接近成片的材质和灯光，不是诊断图。
8. 资产风格没有明显冲突到无法继续。
9. 不依靠字幕解释场景结构。
10. GPT 必须查看实际 PNG 后才能裁定是否通过。

### 10.4 直接交付物

```text
formal_first_frame_v1.png
formal_first_frame_v1.blend
```

支持构建的脚本和配置可以保存在项目中，但不是用户本轮必须上传审核的主要交付物。

### 10.5 停止条件

出现以下任一情况时停止并如实报告：

1. 已选资产无法在同一场景中正常加载。
2. 人物或收银台存在无法通过当前任务范围解决的结构错误。
3. 9:16 画面无法在不破坏核心因果的情况下容纳三个窗口和三条队伍。
4. 完成首帧需要更换核心资产或改变已锁定故事。
5. 一轮实现和一轮定点修正后仍无法满足首帧验收标准。

## 11. 当前正式入口映射

```text
FORMAL_BUILD_ENTRY: NOT_ASSIGNED
FORMAL_GATE_ENTRY: NOT_ASSIGNED
FORMAL_PREVIEW_ENTRY: NOT_ASSIGNED
FORMAL_FINAL_RENDER_ENTRY: NOT_ASSIGNED
FORMAL_OUTPUT_VALIDATION_ENTRY: NOT_ASSIGNED
```

正式入口只有在真实脚本存在并完成最小验证后才能填写。

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

1. Quaternius 人物与 PensamientoAzul 环境可能存在风格差异，先通过正式首帧判断。
2. 收银台原始比例和结构可能需要视觉调整。
3. 正式字幕、音效和节奏尚未设计。
4. 设备关闭状态的最终视觉表现尚未冻结。

这些问题除非直接导致首帧无法使用，否则不得在本轮扩展成额外任务。

### TECH_DEBT

1. 当前资产路线的正式构建、门禁、预览和输出验证入口尚未分配。
2. 旧 graybox 门禁与当前资产对象命名和剧情事件不兼容。
3. 当前仓库没有独立命名为 `blender_output_artifact_check` 的通用输出入口。
4. 通用质检不能判断动作自然度、完整时间轴连续性和画面审美。

这些问题当前不阻止正式首帧。

## 13. 状态更新权限

1. Claude Code 可以报告真实执行事实，但不能自行写入用户视觉批准。
2. Claude Code 的 `COMPLETED` 只表示任务要求的工作和交付已完成。
3. GPT 必须先查看实际 PNG 或 MP4，再决定是否更新阶段和唯一下一任务。
4. 用户负责最终审美批准、继续投入、止损和发布决定。
5. 正式入口必须在文件真实存在并通过最小验证后才能从 `NOT_ASSIGNED` 改为具体路径。
6. 当前首帧通过前，不得把 `CURRENT_STAGE` 改为 P6。

## 14. R2 更新依据

本次更新依据：

```text
CLAUDE.md
VIDEO_PRODUCTION_EXECUTION_STANDARD.md R3
projects\bvf_test_001_checkout_bottleneck\design\SCENE_REACTION_TABLE.md
projects\bvf_test_001_checkout_bottleneck\design\ASSET_CAPABILITY_REQUIREMENTS.md
当前资产来源与许可证裁决
当前资产路线的两轮技术验证结果
GPT 对实际诊断图片和预览的视觉审核
用户对继续当前资产路线和生产顺序的确认
```

本次更新只同步当前真实状态和唯一下一任务：

1. 不修改视频故事。
2. 不修改资产文件。
3. 不创建正式首帧。
4. 不运行 Blender、测试、质检或渲染。
5. 不自动开始下一阶段。
