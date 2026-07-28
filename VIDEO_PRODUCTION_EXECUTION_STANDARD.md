# Blender 视频工厂完整生产执行规范

```text
DOCUMENT_ID: VIDEO_PRODUCTION_EXECUTION_STANDARD
VERSION: R2
DATE: 2026-07-28
PROJECT_ROOT: D:\blender-video-factory
DOCUMENT_ROLE: Blender 视频生产流程最高级通用规范
APPLIES_TO: 本仓库内所有新建和继续推进的视频项目
STATUS: TECHNICALLY_AUDITED_FOR_USER_APPROVAL
```

## 一、文档目的

本规范用于回答一件事：

> 从一个视频选题开始，如何稳定地使用 Claude Code、blender-mcp、Blender、项目质检代码和人工视觉审核，最终生成可交付的视频。

本项目的最终目标是持续产出视频，不是持续扩建测试、证据、架构或通用化系统。质检、脚本、MCP 和文档都是生产工具，不得反过来成为项目目标。

本规范长期保持稳定，不记录某一条视频的临时状态、具体资产路径、当前版本号或下一轮修改参数。每条视频的实时状态必须记录在该项目自己的 `VIDEO_PLAN.md` 中。

## 二、权威边界与优先级

不同文件只在各自范围内具有权威性，不得互相替代。

1. 用户本轮明确指令：决定本轮授权、审美裁定、发布与止损。
2. `VIDEO_PRODUCTION_EXECUTION_STANDARD.md`：决定所有视频共同遵守的生产顺序、阶段门槛和角色边界。
3. 当前视频的 `VIDEO_PLAN.md`：决定该视频的选题、已锁定内容、当前阶段、当前版本和唯一下一任务。
4. 根目录 `CLAUDE.md`：决定 Claude Code 的任务范围、真实性、验证、交付、返工和停止规则。
5. `PROJECT_CODEIFICATION_MASTER_MAP.md`：只记录通用质检系统的实现与锁定状态，不决定一条视频当前该做什么。
6. 设计表、配置文件、资产清单和项目脚本：只在当前视频和当前阶段内生效。

发生跨范围冲突时不得自行拼接解释。冲突会改变目标、范围、验收、修改文件或下一步时，必须停止并报告。

## 三、系统组成与职责

### 3.1 用户

用户只保留以下最终权力：

1. 选题是否值得做。
2. 画面审美是否满意。
3. 是否继续投入、止损或发布。
4. 是否正式批准进入需要人工放行的下一阶段。

用户不负责选择 Blender API、脚本结构、测试写法、坐标计算、文件组织或技术排查方案。

### 3.2 GPT 主控

GPT 是视频项目的导演和技术主控，负责：

1. 把用户目标转化为分阶段生产计划。
2. 冻结每轮唯一主要目标、允许范围、验收标准和停止条件。
3. 决定技术路线、任务拆分、质检范围、修复顺序和技术止损。
4. 编写可直接发送给 Claude Code 的执行指令。
5. 审核 Claude Code 的真实输出、代码、报告和交付文件。
6. 对图片和视频进行第一道视觉审核，拦截明显技术或视觉错误。
7. 将只有审美才能决定的问题交给用户裁定。
8. 防止测试、证据、打包和架构工作挤占生产。

GPT 的技术判断属于待验证结论。Claude Code 必须通过源码、结构化数据、Blender 实际运行或诊断工具确认。

### 3.3 Claude Code

Claude Code 是确定性施工与技术验证执行者，负责：

1. 读取本轮权威文件和明确任务。
2. 修改授权范围内的配置、Python 脚本和项目文件。
3. 通过 blender-mcp 或 Blender 后台进程执行 `bpy` 脚本。
4. 构建场景、设置动画、保存 `.blend`、渲染预览和运行质检。
5. 提取层级、坐标、旋转、骨骼、包围盒、可见性、动画和输出文件状态。
6. 在技术条件失败时停止并报告真实失败原因。
7. 生成当前任务要求的最小交付物并停止。

Claude Code 不得：

1. 自行决定画面是否好看或是否适合发布。
2. 自行开始下一阶段。
3. 绕过质检门禁直接交付。
4. 通过反复盲调参数寻找“满意效果”。
5. 同时修改多个基础变量。
6. 把测试通过等同于用户已经验收。

### 3.4 blender-mcp

`blender-mcp` 是外部 Blender 控制工具，不属于 `blender-video-factory` 仓库本体。它负责：

1. 查询 Blender 状态和环境。
2. 调用当前环境已经验证可用的后台 Blender 执行通道。实时 GUI 会话不是生产前提；只有在当前环境单独验证通过且本轮明确授权时才允许使用。
3. 执行内联或文件形式的 `bpy` 脚本。
4. 查询场景状态、保存场景和触发渲染。

复杂视频不得依靠数百次零散 MCP 操作逐个创建、移动和设置对象。默认方法是：

```text
Claude Code 生成确定性配置与 bpy 脚本
→ blender-mcp 执行脚本
→ Blender 完成实际场景构建
```

MCP 是“执行的手”，不是导演、动画设计师或质检员。工具名称可能随安装版本变化，执行时以当前 MCP 服务实际暴露的工具为准。

### 3.5 Blender

Blender 是实际生产环境，负责：

1. 资产导入与 Append。
2. 场景、材质、灯光、摄像机和动画计算。
3. `.blend` 保存。
4. PNG 序列与预览图渲染。

默认优先使用 `--background` 无头执行。Live GUI 不是默认入口，也不是 P0 通过条件；只有当前环境已单独验证、不会干扰 headless 调用且本轮明确授权时，才用于用户观察或人工检查。Live GUI 不能赋予 Claude Code 可靠的视觉判断能力。

### 3.6 通用质检系统

`protocol_guard/phase3_min` 是通用场景与资产质检底座，负责客观、可重复判断的要求，例如：

1. 对象存在性和类型。
2. 层级。
3. 站立。
4. 朝向。
5. 可见性。
6. 旋转。
7. 采样帧中的 Action、可见性和已配置状态字段。
8. 材质分配。
9. Collection 规则。
10. 地面接触。
11. 已配置摄像机结构与条件检查。
12. 已配置投影组的包围盒、角点和屏幕范围检查。

这些检查只证明配置中声明且实际执行的客观条件。它们不证明帧间运动连续、动作自然、整个时间轴始终无遮挡，也不证明构图具有审美质量。通用质检不能理解每条视频独有的剧情含义，因此每个视频项目还必须建立自己的补充门禁规则。

### 3.7 人工视觉审核

以下内容不能仅靠代码可靠裁定：

1. 画面是否好看。
2. 第一秒是否吸引人。
3. 资产风格是否统一。
4. 构图层次和遮挡观感。
5. 动作节奏是否自然。
6. 是否具有平台发布价值。

这些内容由 GPT 先审核，再由用户最终裁定。

## 四、总生产架构

所有视频统一采用以下结构：

```text
用户给出目标或选题
→ GPT 冻结当前阶段和唯一任务
→ Claude Code 编写或修改确定性配置与 bpy 脚本
→ blender-mcp / Blender 执行
→ 项目保存版本化 .blend
→ 通用质检 + 项目专用门禁
→ 关键帧或低清预览
→ GPT 技术与视觉初审
→ 用户审美裁定
→ 定点修正或放行
→ PNG 序列正式渲染
→ 输出文件验证
→ FFmpeg 编码
→ 后期包装
→ 最终审核与交付
```

任何阶段都不得跳过其前置门槛。

## 五、通用生产原则

### 5.1 一轮一个主要目标

每轮任务开始前必须冻结：

```text
UNIQUE_MAIN_GOAL
ALLOW_MODIFY
DO_NOT_MODIFY
ACCEPTANCE_CRITERIA
STOP_CONDITION
DELIVERABLES
```

每轮只允许一个主要修改变量。多个问题同时存在时，按阻断程度排序处理。

### 5.2 问题分类

所有新发现问题分为：

```text
BLOCKER：不解决就无法继续当前阶段
QUALITY：影响质量，但不阻止当前阶段技术完成
TECH_DEBT：架构、复用性、完备性或长期维护问题
```

只有 `BLOCKER` 自动进入当前任务。`QUALITY` 和 `TECH_DEBT` 只记录，除非用户另行授权。

### 5.3 生产优先

优先级固定为：

```text
真实视频生产
→ 必要技术验证
→ 必要修复
→ 增强测试
→ 报告、证据、打包和通用化
```

不得为了让测试系统更完美而无限推迟视频生产。

### 5.4 确定性优先

所有关键生产参数必须进入 JSON、YAML 或明确的 Python 常量，不能只存在于 Claude 的临时上下文中。

同一配置、同一资产版本和同一 Blender 环境重复运行时，应生成结构一致的场景。

### 5.5 失败即停止

前置门槛失败时：

1. 不得自动进入下一阶段。
2. 不得改用其他脚本绕过。
3. 不得把部分成功包装为整体成功。
4. 不得交付失败产物作为正式结果。

### 5.6 返工上限

同一问题默认最多：

```text
一轮实现
＋
一轮定点修正
```

第二轮后仍未解决，必须停止并由 GPT 判断：更换资产、简化目标、延期、记录技术债或让用户决定是否继续。

首帧审美返工最多两轮主要修改。不得连续产生开放式 `v3 / v4 / v5` 补丁链。

### 5.7 版本不覆盖

已通过或已提交审核的 `.blend`、配置、预览和视频不得被覆盖。新版本使用清晰递增命名，并记录修改变量。

## 六、每条视频的标准目录

```text
projects/<VIDEO_ID>/
├── VIDEO_PLAN.md
├── design/
│   ├── VIDEO_BRIEF.md
│   ├── SCENE_REACTION_TABLE.md
│   └── ASSET_CAPABILITY_REQUIREMENTS.md
├── assets/
│   ├── ASSET_SELECTION.md
│   └── ASSET_REFERENCES.json
├── config/
│   ├── scene_config.json
│   ├── animation_config.json
│   └── render_config.json
├── scripts/
│   ├── build_scene.py
│   ├── project_gate.py
│   ├── render_preview.py
│   ├── render_final.py
│   └── validate_output.py
├── scene/
├── diagnostics/
├── reviews/
└── output/
    ├── work/
    └── delivery/
```

规则：

1. `VIDEO_PLAN.md` 是该视频当前状态的唯一权威文件。
2. `design/` 只保存已冻结的内容设计和能力要求。
3. `assets/` 主要保存选择、来源、许可证和本地引用，不默认复制大型第三方原始资产。
4. `config/` 保存可重复构建的参数。
5. `scripts/` 保存正式入口和生产脚本。
6. `scene/` 保存版本化 `.blend`。
7. `diagnostics/` 保存运行期技术产物，不用于最终交付。
8. `reviews/` 保存需要 GPT 或用户审核的图片、视频和结论。
9. `output/work/` 保存帧序列和临时编码。
10. `output/delivery/` 只保存本轮需要用户上传或最终交付的文件。

旧项目不要求立即重构目录。继续使用旧目录时，必须在 `VIDEO_PLAN.md` 中记录实际路径映射。旧项目的正式入口可以位于项目根目录或历史子目录，不强制迁移到本节模板中的 `scripts/`；是否有效只由 `VIDEO_PLAN.md` 的 `FORMAL_*_ENTRY` 映射和真实文件验证决定。

## 七、VIDEO_PLAN.md 状态字段

每条视频必须维护以下顶部字段：

```text
VIDEO_ID:
VIDEO_TITLE:
PLATFORM:
ASPECT_RATIO:
TARGET_RESOLUTION:
TARGET_FPS:
TARGET_DURATION:
CURRENT_STAGE:
ACTIVE_TASK_ID:
ACTIVE_TASK_STATUS:
UNIQUE_NEXT_TASK:
LAST_TECHNICAL_GATE:
LAST_VISUAL_REVIEW:
USER_VISUAL_APPROVAL:
CURRENT_APPROVED_BLEND:
CURRENT_APPROVED_PREVIEW:
STOP_LOSS_TRIGGERED:
```

正文至少包含：

1. 视频目标和观众应理解的核心结论。
2. 已锁定内容。
3. 已批准资产。
4. 当前阶段已完成内容。
5. 当前阻断问题。
6. 当前唯一下一任务。
7. 人工审核记录。
8. 被推迟的质量问题和技术债。
9. 当前正式入口脚本。
10. 最终交付规格。

状态只能在真实完成和获得相应批准后更新。

## 八、完整生产阶段

# P0：环境与入口确认

### 目标

确认当前机器和会话具备执行本视频的基本条件。

### 必须确认

1. 根目录 `CLAUDE.md` 已读取。
2. 本规范已读取。
3. 当前视频 `VIDEO_PLAN.md` 已读取。
4. Blender 可执行路径真实存在。
5. Blender 版本符合项目约束。
6. Python、FFmpeg 和必要依赖可用。
7. blender-mcp 已连接或能够启动后台 Blender。
8. 当前正式项目路径存在。
9. 当前 `ACTIVE_TASK_ID` 与用户指令一致。

### 最小验证

新环境、MCP 修复、MCP 会话重建或关键配置变更后，按顺序运行：

```text
查询 Blender 状态
→ 调用 script_execute（或当前安装版本的等价工具）执行 print("BVF_MCP_SMOKE_OK")
→ 同时确认工具返回执行成功信号与 stdout 标记
→ 导入或创建 1 个最小对象
→ 渲染 1 帧
→ 检查不是黑屏、空帧或纯色背景
```

当前已知的 `blender-mcp` 成功信号为 `BLENDER_SCRIPT_SUCCESS`。若安装版本使用不同信号，必须在 `VIDEO_PLAN.md` 或当前环境记录中写明等价成功条件。只看到工具调用完成、进程退出或 `Render Saved` 不算通过。`script_execute` 超时、缺少成功信号或缺少 `BVF_MCP_SMOKE_OK` 时，P0 立即阻断，不得继续构建。

### 停止条件

环境不满足时停止，不进入设计、资产或构建阶段。

# P1：视频定义与剧情冻结

### 输入

用户选题、目标平台和基本诉求。

### 输出

1. `VIDEO_BRIEF.md`
2. `SCENE_REACTION_TABLE.md`
3. 初始化后的 `VIDEO_PLAN.md`

### VIDEO_BRIEF 必须说明

1. 视频题目。
2. 目标观众。
3. 观众最终应理解什么。
4. 平台、画幅、分辨率、帧率和暂定时长。
5. 第一秒钩子。
6. 结尾结论。
7. 不在当前视频范围内的内容。

### SCENE_REACTION_TABLE 必须按段记录

```text
TIME_RANGE
STORY_PURPOSE
HUMAN_ACTIONS
DEVICE_REACTIONS
PROP_REACTIONS
CAMERA_FOCUS
POST_PRODUCTION
BLOCKER_IF_MISSING
```

### 通过条件

每个剧情因果都能对应到可见的人物、设备或道具变化。不能只依赖字幕解释核心事件。

### 人工审核

用户只确认选题和故事方向，不处理技术实现。

# P2：资产能力要求冻结

### 目标

在搜索资产前，先定义资产必须支持什么功能。

### 输出

`ASSET_CAPABILITY_REQUIREMENTS.md`

### 资产分级

```text
CORE_INTERACTIVE：缺失会破坏剧情，属于 BLOCKER
SECONDARY_INTERACTIVE：最好支持，但可简化
BACKGROUND：只负责环境可信度，不要求可动
```

### 每个核心资产必须记录

1. 所需动作和状态。
2. 必须独立控制的部件。
3. 骨骼、绑定或父子层级要求。
4. 原点和轴心要求。
5. 脚本控制要求。
6. 内部几何是否必须完整。
7. 可接受的替代实现。
8. 功能缺失时是换资产还是简化剧情。

### 通过条件

所有 `BLOCKER_IF_MISSING` 都能映射到明确资产能力。

# P3：资产搜索、许可证与候选裁决

### 目标

找到风格合适、许可明确、功能可实现的资产。

### 每个候选资产记录

```text
ASSET_NAME
ASSET_TYPE
SOURCE
LICENSE
COMMERCIAL_USE_ALLOWED
LOCAL_PATH
FORMAT
VISUAL_STYLE_MATCH
REQUIRED_ACTIONS
EXISTING_ANIMATIONS
MOVABLE_PARTS
RIG_AVAILABLE
ORIGIN_OR_PIVOT_VALID
TEXTURES_AVAILABLE
SCRIPT_CONTROLLABLE
EXPECTED_MODIFICATION
CAPABILITY_CLASS
BLOCKERS
DECISION
```

### 能力分类

```text
READY
EASY_TO_RIG
REQUIRES_MODIFICATION
UNSUITABLE
```

### 裁决原则

1. 核心资产为 `UNSUITABLE`：更换资产或简化剧情，不进入正式场景。
2. 修复成本明显高于替换成本：优先替换。
3. 许可证未知：不得进入正式商业生产或对外交付。
4. 风格明显不一致：不得因为技术可用就强行混搭。

### 输出

`ASSET_SELECTION.md` 和资产引用记录。

# P4：新资产孤立验证与固定资产库

### 目标

证明新资产在进入正式场景前结构、姿势、比例、动作和材质都正常。

### 新人物、动物和带骨骼资产的强制顺序

```text
单资产导入
→ 提取层级、骨骼、变换和 bbox
→ 检查站立、朝向、比例和地面接触
→ 检查游离 Mesh 和异常对象
→ 验证所需 Action
→ 渲染正面、侧面、3/4 三视图
→ GPT 初审
→ 用户视觉裁定
→ 保存到固定资产库
```

### 人物最低技术门槛

1. 顶层控制 Root 存在。
2. Armature 存在。
3. Mesh 层级明确且没有零件脱离。
4. 没有额外漂浮 Mesh。
5. 世界空间处于站立状态。
6. 头部中心明显高于身体中心。
7. 高度明显大于宽度。
8. 脚底接近地面。
9. 项目标准高度已记录。
10. 正面方向已记录。
11. 必要动作真实存在且可以赋给正确对象。
12. 保存并重新打开后状态不变。

### 设备资产最低技术门槛

1. 活动部件可独立控制或容易拆分。
2. 原点和轴心合理。
3. 开启与关闭状态视觉差异清楚。
4. 内部几何在打开后不会暴露明显空洞。
5. 通过脚本设置关键帧后行为稳定。
6. 保存后重新打开状态不变。

### 固定资产库规则

1. 正式场景优先 Append 已验证 Collection。
2. 禁止每条视频重复导入和重新标准化同一原始资产。
3. 世界位置、旋转和缩放写在已验证 Root。
4. Action 赋给正确的 Armature 或控制对象。
5. 不修改资产库原文件，除非启动独立资产库任务。

### 停止条件

必要核心资产未全部通过前，禁止进入正式首帧。

# P5：静态首帧锁定

首帧必须拆成四个独立关卡，不得一次性混做。

## P5-A：角色与核心资产实例化

只验证 Append、对象存在、层级、姿势、尺寸、朝向、材质和地面接触。

禁止正式布局、相机、灯光和动画。

## P5-B：空间布局

锁定资产内部结构，只验证人物、设备和环境的空间关系。

最低通过条件：

1. 核心对象全部存在。
2. 人物穿模数量为 0，或在明确容差内。
3. 人物与设备关系符合剧情。
4. 人物脚底接地。
5. 朝向正确。
6. 队伍、通道或动作空间可区分。

只使用技术相机和中性灯光。

## P5-C：摄像机构图

锁定人物和资产布局，只修改摄像机。

程序化检查至少包括：

1. 必要对象裁切数量为 0。
2. 所有人物进入安全区。
3. 核心设备进入安全区。
4. 相机不进入必要对象的世界包围盒。
5. 上下无意义空白受控。
6. 左右安全边距满足当前平台要求。

完成后渲染低分辨率预览并停止。

## P5-D：灯光与正式首帧

锁定角色、布局和摄像机，只调整正式灯光、环境和允许修改的材质表现。

输出：

1. 版本化 `.blend`。
2. 目标画幅正式首帧 PNG。
3. 技术预检结果。
4. 干净审核目录。

### 首帧人工门槛

GPT 先检查：

1. 是否一眼能认出目标场景。
2. 人物、设备和关系是否清楚。
3. 是否存在明显遮挡、穿模、横躺、漂浮或异常放大。
4. 主体是否足够大。
5. 是否明显不像默认 Blender 练习或随意素材拼装。

用户最终决定：

```text
APPROVED
REVISION_REQUIRED
STOP
```

首帧没有 `APPROVED`，禁止进入动画。

# P6：3–5 秒功能样片

### 目标

只验证整条视频最关键、最难的互动链是否真实可做。

### 范围原则

1. 只包含核心互动。
2. 使用低分辨率预览。
3. 不做完整时长。
4. 不做最终字幕、音效和包装。
5. 不把非核心美术问题设为阻断条件。

### 必须验证

1. 资产动作确实可用。
2. Root、Armature 和 Mesh 不分离。
3. 设备状态切换清楚。
4. 关键动作顺序正确。
5. 关键道具跟随关系正确。
6. 相机能看见完整互动。
7. 功能样片可以重复构建。

### 人工门槛

GPT 和用户判断关键动作是否清楚、节奏是否可接受、是否值得扩展成完整视频。

功能样片未通过，禁止进入完整时间轴。

# P7：完整动画配置冻结

### 输出

`animation_config.json` 或等价确定性配置。

### 至少包含

1. 总帧数和帧率。
2. 各段起止帧。
3. 每个角色的初始状态。
4. 移动路径和关键位置。
5. 旋转和朝向变化。
6. Action 名称和切换帧。
7. 设备状态切换。
8. 道具运动和父子关系。
9. 可见性变化。
10. 摄像机关键帧。
11. 灯光变化。
12. 渲染参数。
13. 必须质检的事件帧。
14. 每个剧情段的项目专用通过条件。

### 通过条件

所有剧情动作都能映射到具体对象、属性、起止帧和预期状态。

# P8：MCP 执行确定性构建

### 标准执行方式

```text
读取配置
→ 立即验证所有路径
→ 从空场景或已批准模板开始
→ Append 固定资产
→ 每步调用 ensure_scene_state()
→ 设置语义化对象名称
→ 写入布局、动作、设备状态、镜头和灯光
→ 保存版本化 .blend
→ 输出结构化构建摘要
```

### 脚本要求

1. 路径常量初始化后立即检查存在性。
2. 优先使用语义名称，不依赖导入顺序猜对象。
3. 不使用节点输入硬编码索引，优先按名称访问。
4. Blender 5.x 不确定 API 先做最小 smoke test。
5. 每步导入后重新确认 world、camera、render engine 和必要场景状态。
6. 不直接覆盖已批准 `.blend`。
7. 构建脚本和配置分离。
8. 构建阶段默认不做正式完整渲染。

### MCP 使用边界

1. 允许状态查询、场景查询、脚本执行、保存和授权渲染。
2. 不允许通过自然语言零散调用临场决定几百个参数。
3. MCP 执行失败时读取真实错误，不重复盲跑相同命令。
4. GUI 观察不能替代结构化验证。

# P9：项目技术门禁

每条视频必须拥有项目专用正式门禁入口，例如：

```text
scripts/project_gate.py
```

不得直接运行 `build_scene.py` 后宣布技术完成。

### 正式门禁流程

```text
创建唯一 run_id 和隔离运行目录
→ 构建或载入本轮 .blend
→ 发现关键事件帧
→ 生成事件帧快照或逐帧读取状态
→ 运行 asset_scene_preflight_check
→ 运行项目专用补充检查
→ 交叉验证结果一致性
→ 写出 gate_result.json
→ 决定是否授权预览
```

### 通用质检

按当前项目配置启用层级、站立、朝向、可见性、旋转、动画、材质、集合、地面、摄像机和投影组检查。

### 项目专用补充检查

必须覆盖通用检查不理解的剧情规则，例如：

1. 多名角色是否按指定顺序反应。
2. 某设备关闭后是否保持停止。
3. 其他设备是否继续工作。
4. 道具是否跟随正确角色。
5. 最终队伍、位置或状态是否形成预期结果。

### 建议门禁语义

门禁必须表达以下语义，但旧项目和通用门禁的实际 JSON 字段名可以不同：

```text
run_id
video_id
build_pass
static_preflight_pass
event_frame_preflight_pass
supplemental_pass
result_consistency_pass
technical_gate_pass
preview_authorized
full_render_authorized
failed_checks
```

实际字段名、现有 schema 与以上语义不一致时，不得伪造统一字段。应在 `VIDEO_PLAN.md` 中记录字段映射，或由项目适配层完成转换。

### 强制规则

1. 任一必要子检查失败，`technical_gate_pass = false`。
2. 门禁失败时不得授权预览或正式渲染。
3. `full_render_authorized` 默认保持 `false`，直到技术门禁通过且用户明确批准当前低清预览。
4. run_id 不匹配、结果缺失或 JSON 不一致时必须阻止。
5. 不得用旧门禁结果授权新版本场景。

# P10：关键帧与低清完整预览

### 前置条件

技术门禁通过。

### 输出顺序

```text
关键事件帧
→ Contact Sheet 或审核板
→ 低分辨率完整预览
```

### 技术检查

1. 预览帧真实存在。
2. 非黑屏、非纯色、包含预期对象。
3. 事件帧与当前 run_id 对应。
4. 关键动作未被裁切。
5. 低清视频可以完整解码。

### GPT 视觉审核

1. 不看字幕能否理解核心因果。
2. 动作是否太快、太慢或滑行。
3. 角色反应顺序是否清楚。
4. 设备状态变化是否明显。
5. 镜头是否遮挡关键事件。
6. 最终状态是否形成清楚结论。
7. 是否出现新的明显视觉错误。

### 用户裁定

```text
APPROVED_FOR_FINAL_RENDER
REVISION_REQUIRED
STOP
```

### 修正规则

每轮只修改一个主要变量，例如：

```text
只修角色退出路径
只修某个转身时机
只修关闭标识可见性
只修摄像机遮挡
```

不得在一轮同时修改角色、布局、镜头、灯光和材质。

# P11：正式渲染与输出验证

### 前置条件

1. 技术门禁通过。
2. 当前低清预览获得用户明确批准。
3. 本轮任务明确授权完整渲染。

### 正式渲染方式

默认：

```text
Blender 渲染 PNG 序列
→ 验证帧序列
→ FFmpeg 编码 MP4
→ 验证 MP4
```

不默认让 Blender 直接输出最终 MP4。

### PNG 序列最低检查

1. 文件数量等于目标帧数。
2. 首帧和末帧正确。
3. 没有缺帧。
4. 没有重复帧。
5. 没有损坏图片。
6. 分辨率一致且符合目标。
7. 没有意外文件混入。

### MP4 最低检查

1. 视频流存在。
2. 编码符合交付要求，默认 H.264。
3. 像素格式默认 `yuv420p`。
4. 分辨率正确。
5. 帧率正确。
6. 帧数正确。
7. 时长在容差内。
8. FFmpeg 完整解码退出码为 0。
9. 音频流数量符合当前视频设计。

当前仓库尚不存在一个可直接调用、以 `blender_output_artifact_check` 命名的独立通用入口。现有输出检查能力和旧项目验证代码只能作为底座或参考；每个正式视频必须由其 `FORMAL_OUTPUT_VALIDATION_ENTRY` 完成全部 PNG 与 MP4 最低检查。输出验证是强制门槛，不因未来通用检查器尚未完成而跳过。

# P12：后期包装、最终审核与交付

### 后期可使用

1. 剪映。
2. jianying-mcp。
3. Remotion。
4. FFmpeg。

### 后期负责

1. 标题和字幕。
2. 箭头、高亮和辅助图形。
3. 音效和音乐。
4. 转场。
5. 封面。
6. 平台安全区。

后期只能帮助解释，不能代替 Blender 中必须真实发生的人物或设备动作。

### 最终审核

技术：

1. 最终文件和验证结果对应。
2. 编码、帧率、分辨率和时长正确。
3. 没有旧版本混入。
4. 视频可以完整播放和解码。

视觉：

1. 第一秒是否抓人。
2. 核心故事是否清楚。
3. 字幕是否遮挡主体。
4. 关键动作是否明显。
5. 结尾是否形成明确结论。
6. 用户是否愿意发布。

### 最终 delivery

只包含当前任务真正需要的文件，例如：

```text
最终 MP4
封面图
必要字幕或后期项目文件
必要的简洁验证结果
```

禁止混入：

1. 完整临时帧序列。
2. 历史失败版本。
3. 临时 `.blend`。
4. 无关测试输出。
5. 大型第三方原始资产。
6. 重复报告和无价值证据包。

## 九、固定异常排查顺序

渲染、投影或动画异常时，按以下顺序排查：

```text
对象和角色层级
→ 姿势与 Action
→ Root 旋转
→ 尺寸与缩放
→ 地面接触
→ 世界位置
→ bbox 与投影输入
→ 摄像机
→ 灯光
→ 材质与后期
```

在前六项通过前，禁止优先调整：

```text
ortho_scale
shift_y
camera distance
camera target
lens
```

修复必须基于真实数据和复现，不得仅凭一张异常渲染图猜根因。

## 十、正式入口与禁止绕过

每条视频必须在 `VIDEO_PLAN.md` 中记录：

```text
FORMAL_BUILD_ENTRY
FORMAL_GATE_ENTRY
FORMAL_PREVIEW_ENTRY
FORMAL_FINAL_RENDER_ENTRY
FORMAL_OUTPUT_VALIDATION_ENTRY
```

旧项目通过这些字段映射真实入口，不强制入口符合第六节的目录模板。字段指向的文件不存在、仍属实验脚本或尚未批准时，必须填写 `NOT_ASSIGNED` 或 `LEGACY_REFERENCE_ONLY`，不得猜测一个模板路径。

禁止：

1. 直接运行构建脚本后宣布完成。
2. 门禁失败后改用其他渲染脚本。
3. 手动点击 Blender 渲染来绕过授权。
4. 使用旧 run_id 或旧结果文件授权新版本。
5. Claude 临时编写不受门禁控制的完整渲染脚本。
6. 只凭终端出现 `Render Saved` 就认定成功。

允许用于诊断的独立最小脚本必须明确标记为诊断脚本，不得产生正式交付。

## 十一、人工审核点

只有以下节点默认需要用户视觉裁定：

1. 最终资产候选的视觉风格。
2. 正式首帧。
3. 3–5 秒功能样片。
4. 低清完整预览。
5. 最终成片。

其他技术选择由 GPT 决定，Claude Code 执行。

人工审核后，由 GPT 将反馈转换为一个明确的主要修改变量和可验证任务。不得把“看着不对”“继续优化”“做到满意”为原文直接发送给 Claude Code。

## 十二、每轮 Claude Code 指令固定结构

所有正式生产任务至少包含：

```text
TASK_ID
CURRENT_STAGE
UNIQUE_MAIN_GOAL
BACKGROUND
AUTHORITATIVE_INPUTS
MUST_IMPLEMENT
MUST_VERIFY
ACCEPTANCE_CRITERIA
ALLOW_MODIFY
DO_NOT_MODIFY
AUTHORIZED_OPERATIONS
FORBIDDEN_OPERATIONS
STOP_CONDITIONS
MUST_REPORT
MUST_UPLOAD
```

### 指令必须做到

1. 只有一个主要目标。
2. 明确输入文件和真实路径。
3. 明确允许和禁止修改范围。
4. 明确是否授权打开 `.blend`、渲染或完整回归。
5. 明确程序化通过条件。
6. 明确失败即停止。
7. 明确输出文件和 delivery 目录。
8. 明确不得自动进入下一阶段。

### 禁止开放式指令

```text
调整直到满意
看效果继续优化
根据画面自行判断
自动进入下一阶段
尝试不同参数找到最佳效果
顺便修复其他问题
```

## 十三、Claude Code 完成报告最低字段

Claude Code 首先必须保留根目录 `CLAUDE.md` 对完成报告规定的字段和命名。本节只增加视频生产阶段需要的字段；两者重叠时不得删除 `CLAUDE.md` 要求的字段，也不得用 GPT 后续补写代替 Claude Code 对真实执行结果的报告。

```text
TASK_ID:
TASK_STATUS:
CURRENT_STAGE:
UNIQUE_MAIN_GOAL:
FILES_MODIFIED:
BLENDER_EXECUTED:
REAL_BLEND_OPENED:
RENDER_EXECUTED:
TECHNICAL_GATE_RESULT:
TESTS_OR_VALIDATIONS_RUN:
FAILED_CHECKS:
PRODUCTION_PROGRESS_THIS_ROUND:
OUTPUT_FILES:
DELIVERY_FOLDER:
DELIVERY_FILES:
DELIVERY_FILE_COUNT:
ALL_UPLOAD_FILES_IN_ONE_FOLDER: TRUE
UNRELATED_FILES_IN_DELIVERY: 0
NEXT_STAGE_STARTED: FALSE
```

如任务未授权某项操作，必须明确写 `NOT_AUTHORIZED`，不得伪装为通过。

## 十四、交付规则

1. 本轮所有需要用户上传的文件放进同一个干净 `delivery` 文件夹。
2. `delivery` 中不得存在无关文件。
3. 1–3 个文件默认直接上传。
4. 4 个及以上文件只有在保留目录结构、依赖关系或形成自包含交付确有价值时才生成 ZIP。
5. 普通任务不默认生成 Manifest、SHA256、完整报告或证据包。
6. 最终视频生产优先于报告和打包。

## 十五、止损规则

### 技术止损

1. 同一技术问题两轮后仍未解决：停止自动修正。
2. 连续两轮没有真实生产进展：触发止损审查。
3. 连续两轮渲染验证失败：进入独立最小诊断，不重写完整构建脚本。
4. 第三轮仍失败：如实报告 `PARTIAL` 或真实阻断，决定换资产、简化目标或暂停。

### 资产止损

1. 核心动作需要大规模拆模、重绑或重做材质：比较替换资产成本。
2. 资产能力明显不足：换资产或改剧情，不无限修资产。
3. 风格不匹配且两轮视觉调整无明显改善：停止该资产路线。

### 审美止损

首帧或低清预览经过两轮主要视觉返工仍未达到用户接受标准，由 GPT 提出继续、换方案或停止建议，最终由用户决定。

## 十六、新对话接管协议

任何新的 GPT 主控对话接管视频项目时，必须按顺序真实读取：

```text
1. CLAUDE.md
2. VIDEO_PRODUCTION_EXECUTION_STANDARD.md
3. 当前视频 VIDEO_PLAN.md
4. VIDEO_PLAN 指定的当前阶段权威文件
5. 当前正式入口脚本和最近交付文件
```

首次状态判断必须说明：

1. 这条视频要表达什么。
2. 当前做到哪个阶段。
3. 哪些内容已经技术通过。
4. 哪些内容已经获得用户审美批准。
5. 当前唯一阻断是什么。
6. 唯一下一任务是什么。

不得用历史对话记忆、Claude 终端声明或旧报告替代实际文件读取。

用户明确说“下一步”后，GPT 才生成一个当前阶段的 Claude Code 执行指令。不得一次生成多个阶段或自动推进。

## 十七、VIDEO_PLAN.md 模板

````markdown
# <VIDEO_TITLE> — VIDEO_PLAN

```text
VIDEO_ID:
VIDEO_TITLE:
PLATFORM:
ASPECT_RATIO:
TARGET_RESOLUTION:
TARGET_FPS:
TARGET_DURATION:
CURRENT_STAGE:
ACTIVE_TASK_ID:
ACTIVE_TASK_STATUS:
UNIQUE_NEXT_TASK:
LAST_TECHNICAL_GATE:
LAST_VISUAL_REVIEW:
USER_VISUAL_APPROVAL:
CURRENT_APPROVED_BLEND:
CURRENT_APPROVED_PREVIEW:
STOP_LOSS_TRIGGERED: FALSE
FORMAL_BUILD_ENTRY:
FORMAL_GATE_ENTRY:
FORMAL_PREVIEW_ENTRY:
FORMAL_FINAL_RENDER_ENTRY:
FORMAL_OUTPUT_VALIDATION_ENTRY:
```

## 1. 视频目标

## 2. 观众最终应理解的结论

## 3. 已锁定的故事和规格

## 4. 已批准资产

## 5. 当前阶段状态

## 6. 已通过的技术门槛

## 7. 用户已批准的视觉版本

## 8. 当前阻断问题

## 9. 当前唯一下一任务

## 10. 推迟的 QUALITY 与 TECH_DEBT

## 11. 版本与审核记录
````

## 十八、当前仓库接入原则

本规范批准后，仓库应按以下顺序接入：

1. 将本文件保存为根目录 `VIDEO_PRODUCTION_EXECUTION_STANDARD.md`。
2. 在根目录 `CLAUDE.md` 中只增加一条简短引用，不复制整份规范。
3. 为当前收银项目创建 `VIDEO_PLAN.md`，从真实仓库文件重建当前状态。
4. 明确该项目的正式构建、门禁、预览、最终渲染和输出验证入口。
5. 识别旧项目中哪些脚本只是历史实验、哪些仍是正式入口。
6. 只有完成以上状态整理后，才继续下一轮资产或视频生产任务。

不得为了接入本规范而重写已锁定的通用质检代码，也不得重新运行无关回归。

## 十九、R2 技术审核修订记录

R2 只处理会影响执行真实性或入口识别的问题：

1. P0 新增 `script_execute` 真实成功标记和 stdout smoke test。
2. Live GUI 改为非默认、需单独验证和明确授权的可选能力。
3. 明确动画状态、摄像机和投影检查只覆盖已配置的采样与结构条件，不等于连续运动或审美验证。
4. 旧项目通过 `VIDEO_PLAN.md` 映射真实入口，不强制迁移到模板目录。
5. 建议门禁字段改为语义要求，允许旧 schema 通过映射接入。
6. 明确当前仓库没有独立命名为 `blender_output_artifact_check` 的可直接调用通用入口。
7. Claude Code 报告继续以 `CLAUDE.md` 为基础，本规范只增加视频阶段字段。

本次未重写通用质检代码、旧项目目录或历史脚本。

## 二十、最终原则

以后所有视频都遵守下面这句话：

> 先冻结故事与资产能力，再使用固定资产和确定性脚本构建；让 blender-mcp 执行，让质检代码拦截客观错误，让 GPT 和用户判断画面；技术门槛未通过不渲染，审美未批准不扩展，最终目标始终是完成并交付视频。
