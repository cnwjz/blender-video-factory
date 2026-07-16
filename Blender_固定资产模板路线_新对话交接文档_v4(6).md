# Blender 固定资产模板路线，新对话交接文档 v4

> 交接日期：2026-07-14  
> 工作目录：`D:\blender-video-factory`  
> 当前实验项目：`bvf_asset_test_001_checkout_lane`  
> 适用对象：新的 GPT 对话、新的 Claude Code 会话、后续人工审核  
> 本文档优先级：高于此前所有 Blender 资产驱动交接文档、旧 A2 指令与 v3 交接文档  
> 当前阶段：角色标准化阻塞已经解除，`blender-motion-state-inspection` 已纳入强制诊断流程，下一步从固定角色库创建首帧模板  
> 核心文件：`character_library_v1.blend`
> 执行模型：Claude Code 负责确定性构建与技术验证，用户和 GPT 负责渲染结果的视觉审核  

---

## 一、当前结论

Blender 路线仍然值得继续测试。

上一轮原生几何体路线已经证明：

1. Blender 5.1.2、Eevee、PNG 序列、FFmpeg 和命令行渲染稳定可用。
2. Claude Code 可以通过 Blender Python 构建确定性场景。
3. Blender 可以清楚表现窗口关闭、人物分流和队伍增长。
4. 灰盒阶段的静音因果表达已经通过人工审核。
5. 原生球体、圆柱和方块无法在可接受返工成本内达到抖音发布级视觉。
6. 失败集中在发布级美术方法，Blender 的空间动画与技术链路已经通过。

随后启动了资产驱动实验，使用：

```text
Kenney Mini Characters
Kenney Mini Market
```

当前已经确认：

1. Kenney 两套资产风格统一。
2. 资产许可证为 CC0，可用于商业项目。
3. Mini Market 场景与设备资产可以正常导入。
4. Mini Characters 的 FBX 文件包含完整层级、Armature、骨骼和动作。
5. 单人物静态、idle 和 walk 已经正常渲染。
6. GLB 人物导入会产生游离 Icosphere，后续人物统一使用 FBX。
7. 角色横躺问题已经定位。
8. 标准角色库已经建立。
9. 每个角色已经独立验证。
10. 下一次首帧不再从原始 FBX 重新导入人物。

新的固定方法为：

```text
固定角色库
＋
固定市场资产
＋
固定灯光与摄像机模板
＋
Claude Code 负责摆放、数量、动作和渲染
＋
人工负责首帧锁定与发布价值判断
```

---

## 二、当前真正需要回答的问题

下一阶段只验证：

> 从已验证的 `character_library_v1.blend` 中调用标准角色，再配合 Kenney Mini Market 资产，能否做出一张稳定、完整、明显高于原生几何 V4 的竖屏首帧？

当前不验证：

1. 完整 11.5 秒机制动画。
2. 多人复杂分流。
3. 自动批量生产。
4. 完整剪映后期。
5. 多套资产混搭。
6. 新的人物包。
7. 全自动资产标准化。
8. 自动美术设计。

首帧通过后，才进入简单动作测试。

---

## 三、项目历史与阶段结果

### 1. 原始 Remotion 路线

Remotion 已经证明可以完成：

1. 参数化 UI 动画。
2. 精确时间控制。
3. 分 Scene 渲染。
4. FFmpeg 抽帧。
5. 自动视觉审核。
6. 外部音频与字幕导入。

主要问题：

1. 画面容易接近产品演示或 PPT。
2. 空间、人物和真实动作不足。
3. 每个 Scene 都需要成熟 Motion Designer 级视觉设计。
4. 工程返工很多，整条视频仍缺少抖音原生感。

Remotion 仓库继续保留：

```text
D:\video-factory
```

禁止删除或重构。

### 2. Blender 原生几何灰盒路线

项目：

```text
bvf_test_001_checkout_bottleneck
```

题目：

> 一个收银窗口关闭后，队伍为什么突然变长？

验证结果：

| 阶段 | 结果 |
|---|---|
| 环境审计 | 通过 |
| Blender 5.1.2 | 通过 |
| Eevee | 通过 |
| FFmpeg | 通过 |
| 灰盒机制 | 通过 |
| 角色 Root 层级 | 通过 |
| 摄像机构图预检 | 通过 |
| 动作修正 | 通过 |
| 原生几何发布美术 | 未通过 |
| 完整风格视频 | 取消 |

原生几何路线成功沉淀：

1. Character Root Empty 层级。
2. 人物分流动画。
3. 摄像机投影预检。
4. 跨帧联合包围盒。
5. PNG 序列渲染。
6. FFmpeg 编码。
7. Contact sheet。
8. `UPLOAD_NEXT` 审核目录。
9. 确定性配置。
10. 构建脚本版本化。

原生几何路线失败原因：

1. 人物与环境由基础几何体拼接。
2. Claude Code 同时承担建模、灯光、美术、动画和工程职责。
3. 四轮风格返工仍保留三维练习感。
4. 超市识别和人物可信度不足。
5. 返工成本超过首片验证范围。

该结论只否定旧方法，不否定 Blender。

---

## 四、资产驱动实验的资产状态

### 1. 当前固定资产

人物：

```text
Kenney Mini Characters
```

市场与设备：

```text
Kenney Mini Market
```

已测试设备包括：

1. `cash-register`
2. `character-employee`
3. `display-bread`
4. `display-fruit`
5. `freezer`
6. 收银台或 checkout 相关资产
7. 地面与墙体资产
8. 购物篮或购物车资产

### 2. 许可证状态

Kenney Mini 系列采用 CC0。

本地项目已建立：

```text
assets\ASSET_MANIFEST_DRAFT.md
assets\licenses\
reports\ASSET_AUDIT.md
```

后续仍需保留：

1. 资产名称。
2. 来源。
3. 许可证。
4. 下载日期。
5. 本地路径。
6. 格式。
7. 修改记录。

禁止把第三方原始资产打包进对外交接文件。

### 3. 人物格式规则

人物强制使用 FBX。

禁止继续使用人物 GLB。

原因：

1. Blender 5.1 导入人物 GLB 时产生额外 Icosphere。
2. Icosphere 没有父级，会以漂浮球体进入渲染。
3. FBX 层级更干净。
4. FBX 包含完整动作库。

正确层级：

```text
Top Empty
└── Armature
    ├── body-mesh
    └── head-mesh
```

控制规则：

1. 世界位置只写 Top Empty。
2. 世界旋转只写 Top Empty。
3. 世界缩放只写 Top Empty。
4. Action 只赋给 Armature。
5. Body 和 Head 不写世界坐标。
6. 四肢 Mesh 不单独移动。
7. 不对 Armature做场景级平移。
8. 不在正式场景中重新标准化人物。

---

## 五、Claude Code 对整个过程的关键诊断

### 1. GLB 与 FBX 的误判

最初使用 GLB。

GLB 导入后出现：

1. 游离 Icosphere。
2. 层级不干净。
3. 人物对象与场景对象混杂。
4. 漂浮球体进入渲染。

当时将漂浮球体归因为坐标或相机问题，因此反复调整位置，浪费了大量时间。

后续审计确认：

```text
FBX 才是当前人物的正确导入格式
```

FBX 提供：

```text
Empty
→ Armature
→ Body / Head
```

并包含完整动作库。

### 2. 人物横躺问题

FBX 导入后的 Rest Pose 可能为横躺状态。

早期只检查了包围盒高度数值，没有检查角色主轴、头脚关系和高宽比。

关键错误信号：

```text
H:W ratio 约为 0.9
```

正常站立人形的高度不应小于或接近宽度。

横躺状态下：

1. 头和身体 Z 坐标接近。
2. 包围盒高度看似有效。
3. 相机预检仍可能通过。
4. 角色进入场景后呈现横躺或零件错乱。

该问题穿透了：

1. lookdev_v1
2. lookdev_v2
3. lookdev_v3
4. A2D 多资产布局

说明旧预检标准不完整。

### 3. 相机长期被错误归因

多次出现：

1. 看不见人物。
2. 人物被裁切。
3. 相机贴近模型。
4. 画面只剩局部几何体。

当时优先调整：

1. `ortho_scale`
2. `shift_y`
3. camera distance
4. target point

真正问题多数来自：

1. 人物横躺。
2. 角色 Root 旋转错误。
3. 人物尺寸错误。
4. 多角色导入后的缩放不一致。
5. 包围盒输入本身错误。

相机预检逻辑并没有完全失效。

失效的是它依赖的角色状态。

后续必须遵守：

> 人物站立、朝向、层级、比例没有通过时，禁止调整正式相机。

### 4. 没有先完成角色孤立验证

正确顺序应为：

```text
单角色导入
→ 单角色站立验证
→ 单角色朝向验证
→ 单角色层级验证
→ 单角色三视图验证
→ 保存固定角色库
→ 场景搭建
```

实际执行顺序曾经是：

```text
多角色导入
→ 场景搭建
→ 自动相机
→ Lookdev
→ 发现异常
→ 逐层倒查人物
```

这是资产驱动实验中最大的流程错误。

### 5. Blender 5.1 API 摩擦

已遇到：

1. `Material.use_nodes` 弃用提示。
2. `fcurves` 访问方式变化。
3. Eevee AO 属性改名。
4. Principled BSDF 输入索引变化。
5. 部分 Eevee 阴影属性废弃。
6. Keyframe 与 ID Block 路径限制。

这些问题已积累兼容经验，不需要在新对话中重新审计。

后续脚本要求：

1. 优先使用节点输入名称。
2. 不依赖固定索引。
3. 不使用已确认废弃的 Eevee 属性。
4. 所有 Blender 5.1 兼容修复集中到公共模块。
5. 不在每个构建脚本重复写兼容补丁。

---

## 六、当前阻塞已经解除

Claude Code 的最新确认：

1. 标准角色库已经建立。
2. 每个角色已经独立验证。
3. 人物站立、朝向和层级已经修正。
4. 后续可以直接使用 `character_library_v1.blend`。
5. 后续不再从原始 FBX 重复导入。
6. 下一步可以重新开始首帧。

因此，此前准备的以下任务全部取消：

```text
character_library_board_v2
manual_baseline_v1
继续单人物调试
继续 FBX 格式对比
继续自动角色标准化
```

新对话不要重新执行这些任务。


---

## 七、最高优先级流程修正

本轮实验消耗大量时间的根本原因已经明确：

> 角色资产在进入场景前，没有完成孤立结构验证、朝向验证、姿势验证和比例验证。

过去的错误流程：

```text
导入资产
→ 直接搭建完整场景
→ 渲染结果异常
→ 优先怀疑摄像机
→ 调整相机与取景
→ 角色结构问题继续存在
→ 进入下一轮 lookdev
```

以后强制执行：

```text
单个新角色资产导入
→ 提取结构化状态
→ 检查对象层级
→ 检查骨骼与变换矩阵
→ 检查 bbox 高宽深比例
→ 矫正站立方向
→ 归一化高度
→ 渲染正面、侧面、3/4 三视图
→ 人工确认
→ 保存标准角色库
→ 才允许进入场景搭建
```

该顺序属于硬门槛，任何新人物包、动物包、带骨骼道具或动画角色都必须执行。

### 1. 新资产进入场景前的强制门槛

每个角色必须独立通过：

1. 顶层控制节点存在。
2. Armature 存在。
3. Mesh 层级明确。
4. Body、Head 与四肢没有游离。
5. 不存在额外漂浮 Mesh。
6. 人物主轴与世界 Z 轴关系合理。
7. 角色处于站立状态。
8. 头部中心明显高于身体中心。
9. 脚部接近地面。
10. bbox 高度明显大于宽度。
11. 最终高度归一化到项目标准。
12. 正面方向被记录。
13. Rest Pose、static、idle 的可用状态被记录。
14. 正面、侧面和 3/4 三视图全部通过。
15. 保存并重新打开后状态不变。

任何一项失败，禁止进入多人场景。

### 2. Kenney Mini Characters 的已知标准化规则

当前已确认：

```text
原始格式：FBX
正确层级：Empty → Armature → Body / Head
原始 Rest Pose：横躺
站立修正：Top Empty 绕 X 轴旋转 90°
标准高度：1.75 Blender 单位
正面方向：已在角色库中统一
```

横躺状态的重要信号：

```text
H:W ratio 约为 0.9
头部与身体的 Z 坐标接近
人物高度没有明显大于宽度
```

以后不能只判断：

```text
bbox height > 0
```

必须同时判断：

```text
height / width
head_center_z > body_center_z
vertical_axis_alignment
lowest_point_near_ground
```

### 3. 摄像机问题的诊断顺序

渲染结果异常时，按以下顺序排查：

```text
角色层级
→ 角色姿势
→ Root 旋转
→ 角色尺寸
→ 地面接触
→ 角色世界位置
→ essential bbox
→ 摄像机目标
→ 摄像机距离与焦距
```

在前六项通过前，禁止优先调整：

```text
ortho_scale
shift_y
camera distance
camera target
```

相机预检只能证明输入的包围盒进入画面，无法证明角色本身处于正确状态。

---

## 八、强制使用的诊断 Skill

新安装并纳入流程：

```text
blender-motion-state-inspection
```

Claude Code 提供的信息：

```text
版本来源：已安装 Skill
安装量记录：约 1.3K
安全状态：通过 Socket / Snyk 审计
```

以上安装量与审计状态来自 Claude Code 本轮总结，后续如需对外发布或正式归档，应重新核对 Skill 页面与本地版本信息。

### 1. Skill 的用途

该 Skill 用于在截图前提取结构化状态，包括：

1. 对象层级。
2. Empty、Armature 与 Mesh 关系。
3. 骨骼名称。
4. 对象变换矩阵。
5. Root 位置、旋转和缩放。
6. bbox 尺寸与比例。
7. 动画与逐帧状态。
8. 接触与地面关系。
9. 角色零件是否脱离。
10. 导入结果属于正常角色还是破损状态。

### 2. 强制诊断原则

以后所有角色诊断必须采用：

```text
先提取数据
→ 再判断结构
→ 再渲染截图
→ 数据与截图共同作为证据
```

禁止仅凭最终渲染图推测根因。

### 3. 新资产标准诊断输出

建议每个新角色生成：

```text
reports/<asset_id>_motion_state.json
reviews/<asset_id>_front.png
reviews/<asset_id>_side.png
reviews/<asset_id>_three_quarter.png
```

结构化状态至少记录：

```text
source_file
format
top_root_name
armature_name
mesh_names
bone_names
parent_hierarchy
root_matrix_world
armature_matrix_world
mesh_matrix_world
bbox_min
bbox_max
bbox_size
height_width_ratio
head_center_z
body_center_z
lowest_z
highest_z
ground_contact
pose_source
action_name
frame
stray_meshes
visibility_states
validation_result
```

### 4. Skill 的使用边界

该 Skill 负责诊断和证据提取。

它不替代：

1. 人工构图判断。
2. 发布级美术判断。
3. 资产风格一致性判断。
4. 抖音观看价值判断。
5. 最终动画节奏判断。

---

## 九、固定角色库

### 1. 核心文件

```text
D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane\scene\character_library_v1.blend
```

新 Claude Code 会话必须先确认该文件的真实路径。如果实际位于其他目录，以磁盘真实路径为准。

### 2. 已包含角色

```text
Collection: CHR_MALE_A
Collection: CHR_MALE_B
Collection: CHR_FEMALE_A
Collection: CHR_FEMALE_B
Collection: CHR_EMPLOYEE
```

### 3. 已确认状态

1. 五个角色全部归一化到 1.75 Blender 单位高度。
2. 五个角色朝向统一（face +Y）。
3. Empty → Armature → Body/Head 层级正确。
4. Rest Pose 站立修正已完成。
5. 每个角色独立 Collection，已通过三视图验证。
6. 后续禁止从原始 FBX 重复导入这五个角色。
7. 后续禁止再次归一化角色高度。
8. 后续禁止修改库内角色原始结构。

### 4. 站立修正方法（已内置于角色库，无需重做）

Kenney Mini Characters FBX 导入后 Rest Pose 为横躺状态（H:W ratio ~0.9，头身 Z 坐标接近）。

修正操作（已作用于每个 Top Empty）：

```text
Top Empty rotation_euler = (math.pi/2, 0, math.pi)
即：绕 X 轴旋转 90°（扶正站立）+ 绕 Z 轴旋转 180°（face +Y）
```

角色库保存的是修正后的状态。后续 Append 到场景时角色已处于站立姿态，无需再次旋转。

**注意**：仅 Mesh 局部坐标、Edit Mode 顶点方向或底层未应用数据可能保留原始横向结构。在 Object Mode 世界视图和最终渲染中，角色必须呈现为站立状态。若 Object Mode 视口或渲染中人物横躺，必须判定预检失败，禁止继续。

### 5. 使用方式

推荐使用 Append Collection：

1. 场景内可以独立调整角色位置和 Action。
2. 降低外部链接路径失效风险。
3. 不修改角色库原文件。
4. 适合当前实验规模。

后续模板稳定后再评估 Link Collection。

### 6. 使用规则

1. 只 Append 已验证 Collection。
2. 禁止 Append 整个 Scene。
3. 禁止重新导入原始 FBX。
4. 禁止重新缩放角色 Mesh。
5. 禁止重新判断人物 Up Axis。
6. 禁止修改库内原始 Armature 层级。
7. 场景变换写在已验证 Root。
8. Append 后立即保存新场景。
9. 角色库文件保持只读使用原则。

### 7. 角色库预检

正式首帧构建前，只检查：

1. 文件存在且可正常打开。
2. 五个角色 Collection 存在。
3. Append 后人物完整。
4. 人物为站立状态。
5. 人物脚底接近地面。
6. 人物正面方向符合库内记录（face +Y）。
7. 材质没有丢失。
8. 不存在额外 Icosphere 或横躺人物。

预检失败时停止。禁止现场重新标准化。


---

## 十、Claude Code 的实际工作方式与职责边界

### 1. 核心工作模式

Claude Code 不具备对 Blender 视口、渲染图、截图和视频进行视觉判断的能力。

Claude Code 主要通过以下信息工作：

1. 执行 Blender Python，也就是 `bpy` 脚本。
2. 读取对象名称、层级、坐标、旋转、缩放和可见性状态。
3. 读取 bbox、H:W ratio、头身中心、脚底高度和地面接触数据。
4. 使用 `world_to_camera_view` 完成数学投影与裁切检查。
5. 读取 Blender、FFmpeg、诊断 Skill 和验证脚本的命令输出。
6. 输出渲染文件，交由用户和 GPT 进行人工视觉审核。

默认执行方式为：

```text
确定性配置
→ bpy 构建
→ 结构化预检
→ 数学投影验证
→ 渲染输出
→ 技术校验
→ 停止
→ 人工视觉审核
```

只要数据提取与预检逻辑完整，优先使用 `--background` 无头执行。Live GUI 不作为 Claude Code 的视觉判断工具。

### 2. Claude Code 适合承担的任务

1. 根据确定性 JSON、Python 常量或明确参数构建场景。
2. 检查对象是否存在、层级是否正确、角色是否站立、脚底是否接地。
3. 检查游离 Mesh、裁切对象、头身分离、尺寸异常和 bbox 比例异常。
4. 通过 bbox 与 `world_to_camera_view` 计算摄像机构图。
5. 执行构建、预检、渲染、文件保存和回归验证闭环。
6. 生成版本化输出，不覆盖已通过版本。
7. 在技术条件失败时停止，并报告失败对象、数据和阶段。

### 3. Claude Code 不承担的任务

1. 判断画面是否好看。
2. 判断画面是否具有抖音发布潜力。
3. 从零发明美术风格。
4. 根据渲染图自行决定下一步。
5. 通过连续盲目试参寻找满意结果。
6. 在多个基础变量都未验证时同时修改角色、布局、相机和灯光。
7. 代替用户完成最终首帧锁定与发布价值判断。

风格方向、视觉参考、画面吸引力和发布潜力必须由用户与 GPT 根据渲染输出判断。

### 4. 后续提示词的固定结构

所有面向 Claude Code 的 Blender 提示词必须包含：

1. **确定性输入**：资产路径、Collection 名称、对象名称、坐标、旋转、尺寸、帧号和输出路径。
2. **唯一验证变量**：每个阶段只验证一个主要变量。
3. **锁定项**：明确本阶段禁止修改的角色、布局、相机、灯光、材质或动作。
4. **程序化通过条件**：使用数量、比例、坐标、安全区、裁切数和结构状态表达。
5. **固定排查顺序**：出现异常时按照文档规定顺序诊断。
6. **失败即停止规则**：不得绕过失败条件进入后续阶段。
7. **明确输出**：指定 `.blend`、JSON、报告、预览图或正式渲染文件。
8. **停止点**：输出完成后停止，等待新的明确指令。

禁止使用以下开放式表述：

```text
调整直到满意
看效果继续优化
根据画面自行判断
自动进入下一阶段
尝试不同参数找到最佳效果
```

提示词应改写为可验证条件，例如：

```text
essential objects 裁切数量 = 0
顶部无意义空白 ≤ 15%
底部无意义空白 ≤ 15%
左右安全边距 ≥ 4%
人物脚底最低点与地面误差在项目容差内
检测到异常对象时停止并报告对象名称
```

### 5. 人工视觉审核闭环

凡是涉及构图、美术、遮挡观感、画面吸引力和发布潜力的阶段，必须采用：

```text
Claude Code 渲染并输出文件
→ Claude Code 停止
→ 用户上传图片或视频
→ 用户与 GPT 完成人工视觉审核
→ 用户向 Claude Code 发送新的明确指令
→ 执行下一阶段
```

人工确认不发生在同一次 Claude Code 执行中。

Claude Code 输出预览后，禁止自行推断“人工已经确认”，也禁止自动继续正式渲染或动画制作。

如需查看 Blender GUI，由用户在本机人工打开对应 `.blend` 文件。Claude Code 保持停止状态，并根据用户后续提供的明确修改参数执行。

### 6. 固定异常排查顺序

渲染或投影结果异常时，必须依次检查：

```text
角色层级
→ 角色姿势
→ Root 旋转
→ 角色尺寸
→ 地面接触
→ 角色世界位置
→ bbox 与投影数据
→ 摄像机
```

前六项通过前，禁止修改：

```text
ortho_scale
shift_y
camera distance
camera target
焦距
```

每次修复只处理已被数据证实的根因。修复后使用 `verify` 实际运行检查输出，禁止只修改代码而不执行验证。

### 7. 当前可用工具

```text
blender-mcp
blender-motion-state-inspection
diagnose
verify
```

用途：

1. `blender-mcp`：状态查询与场景操作。
2. `blender-motion-state-inspection`：提取层级、骨骼、变换矩阵、bbox、动作和逐帧状态。
3. `diagnose`：按照复现、缩小范围、建立假设、打点、修复和回归的顺序排查问题。
4. `verify`：改动后实际执行构建或检查命令，确认输出符合要求。


### 7. 三方协作规则与文件优先级

项目根目录中的 `CLAUDE.md` 是 Claude Code 的常驻执行规则。新的 Claude Code 会话开始前必须先读取该文件。

本交接文档负责记录项目状态、阶段目标、资产状态和当前任务。`CLAUDE.md` 负责约束用户、GPT 与 Claude Code 的协作方式。两份文件发生冲突时，按以下范围分别执行：

1. 项目状态、当前阶段、资产路径和本轮任务，以本交接文档为准。
2. 三方职责、每轮输出格式、诊断流程、返工限制和版本管理，以 `CLAUDE.md` 为准。
3. 当前轮用户给出的明确新指令优先于历史任务，但不得绕过新资产孤立验证和失败即停规则。

三方固定职责：

1. 用户负责最终视觉裁定、风格方向、发布决定和最终止损。
2. GPT 负责阶段规划、编写 Claude Code 指令、第一道视觉审核、版本比较和拦截明显不合格结果。
3. Claude Code 负责确定性构建、结构化验证、技术根因定位、渲染输出和回归检查，不负责判断画面是否好看或是否具备发布价值。

每轮 Claude Code 渲染完成后，必须停止并输出以下结构化摘要：

```markdown
## 本轮结果
- 通过: [验证条件 + 实测值]
- 未通过: [验证条件 + 实测值]
- 新发现: [可能影响后续轮次的问题]
- 建议下一轮优先解决: [仅 1 个变量]
```

随后执行固定协作闭环：

```text
Claude Code 输出量化报告与渲染文件
→ GPT 查看图片并进行第一道视觉审核
→ 明显不合格结果由 GPT 拦截
→ 通过 GPT 初审后由用户最终裁定
→ 用户明确放行后才进入下一阶段
```

硬性限制：

1. 新资产必须完成孤立结构验证和三视图验证后才能进入场景。
2. 渲染异常按“层级、姿势、Root 旋转、尺寸、地面接触、世界位置、bbox、相机”的顺序排查。
3. 前六项未通过前，禁止优先修改 `ortho_scale`、`shift_y` 或 `camera distance`。
4. 首帧最多允许两轮主要返工。
5. 两轮返工后仍未通过，由 GPT 提出止损意见，最终决定由用户作出。
6. 禁止持续编写 v5、v6、v7 式补丁流程。
7. 每轮只允许一个主要修改变量。

---

## 十一、下一阶段：固定角色库首帧测试

阶段名称：

```text
L1 Fixed Library Lookdev
```

目标：

> 从 `character_library_v1.blend` 调用标准人物，再配合 Kenney Mini Market，做出一张稳定的超市收银首帧。

本阶段只做一张首帧。

不做动画。

不做窗口关闭。

不做多人分流。

不做完整视频。

### 1. 首帧范围

建议包含：

1. 两个收银通道。
2. 两名收银员。
3. 四名顾客。
4. 左队三人。
5. 右队一人。
6. 两台收银机。
7. 少量商品。
8. 一个购物篮或购物车。
9. 一组低对比展示柜或 freezer。
10. 简洁地面与背景。

### 2. 人物使用

顾客从角色库选择真实 Collection：

1. `CHR_MALE_A`
2. `CHR_FEMALE_A`
3. `CHR_MALE_B`
4. `CHR_FEMALE_B`

收银员使用 `CHR_EMPLOYEE`，Append 两次，场景中重命名 Root 为 `Employee_01_Root` 和 `Employee_02_Root`。

### 3. 姿势

首帧优先使用角色库中已经锁定的站立姿势。

可以使用：

```text
static
```

或经过验证的：

```text
idle frame
```

当前首帧禁止重新测试 walk。

### 4. 位置与朝向

1. 收银员位于柜台后方。
2. 顾客位于传送带前方。
3. 顾客朝向收银员。
4. 收银员朝向顾客。
5. 左队三人保持合理间距。
6. 右队一人靠近第二个通道。
7. 人物脚底接触地面。
8. 不允许人物与柜台穿模。
9. 不允许顾客朝向镜头。
10. 场景摆放只修改角色 Root。

### 5. 市场资产

继续使用已经下载的 Mini Market。

允许：

1. checkout 或收银台。
2. cash-register。
3. display-bread。
4. display-fruit。
5. freezer。
6. 购物篮。
7. 少量盒装商品。
8. 地面和墙体。

市场资产只导入一次。

场景稳定后保存为固定模板。

---

## 十二、首帧构图原则

输出规格：

```text
1080×1920
30fps
Eevee
```

摄像机：

```text
透视 3/4 斜俯视
```

要求：

1. 第一眼认出超市收银区。
2. 两个收银通道同时可读。
3. 排队方向清楚。
4. 收银员与顾客关系清楚。
5. 主体占画面主要区域。
6. 顶部无意义空白不超过 15%。
7. 底部无意义空白不超过 15%。
8. 左右安全边距不低于 4%。
9. 全部人物完整显示。
10. 收银台和商品完整显示。
11. 不接近纯顶视。
12. 相机不进入模型。
13. 画面不被单个人物局部占满。
14. 前景、中景和背景有层次。
15. 不使用复杂自动相机搜索。

正确顺序：

```text
先确认人物状态
→ 再摆场景
→ 渲染低分辨率预览
→ 根据预览调整相机
→ 预览无法完成视觉判断时停止，由用户在本机打开 `.blend` 人工检查
```

禁止顺序：

```text
先自动算相机
→ 再发现人物横躺
```

---

## 十三、首帧灯光与美术原则

渲染器：

```text
Eevee
```

使用：

1. 柔和主光。
2. 低强度正面补光。
3. 轻微轮廓光。
4. 中性环境光。
5. 适量接触阴影。

要求：

1. 保留 Kenney 原生材质风格。
2. 人物服装颜色可辨认。
3. 人物与地面分离。
4. 阴影集中在脚下。
5. 柜台轮廓清楚。
6. 背景对比度低于主体。
7. 画面不灰暗发闷。
8. 不使用体积雾。
9. 不使用景深。
10. 不使用运动模糊。
11. 不混入其他风格资产。
12. 不修改角色库人物造型。

---

## 十四、L1 首帧验收标准

### 1. 稳定性

1. 所有人物站立。
2. 没有横躺。
3. 没有漂浮 Icosphere。
4. 没有头身或四肢分离。
5. 保存并重新打开后状态不变。
6. 材质不丢失。
7. 角色 Root 结构不变。

### 2. 场景关系

1. 顾客站在柜台前。
2. 收银员站在柜台后。
3. 顾客朝向收银员。
4. 收银员朝向顾客。
5. 两条队伍可读。
6. 商品位于传送带或购物篮。
7. 收银机位于正确位置。
8. 不存在人物穿模。

### 3. 超市识别

1. 第一眼认出超市结账区。
2. 收银台、收银机与商品可辨认。
3. 环境资产只起辅助作用。
4. 不依赖文字解释。

### 4. 构图

1. 主体足够大。
2. 人物完整。
3. 两个通道完整。
4. 顶部和底部空白受控。
5. 不出现相机钻模。
6. 不出现局部异常放大。

### 5. 发布潜力

1. 明显高于原生几何 V4。
2. 明显高于错误的 lookdev_v1、v2、v3。
3. 不像 Blender 默认练习。
4. 不像素材随意拼装。
5. 用户愿意继续看下一秒。
6. 用户愿意继续做动画测试。

首帧未通过时禁止进入动画。

首帧最多允许两轮主要调整。

---

## 十五、L1 执行原则

L1 拆分为四个独立关卡。每个关卡只验证一个主要变量，每个关卡必须由一条新的 Claude Code 指令启动。

```text
L1-A 固定角色 Append 与结构状态
→ L1-B 市场资产空间布局
→ L1-C 摄像机构图
→ L1-D 灯光与正式首帧
```

### 1. L1-A：固定角色 Append 与结构状态

唯一验证变量：

```text
五个固定角色 Collection 能否在新场景中稳定 Append，并保持已验证状态
```

执行内容：

1. 从 `character_library_v1.blend` Append 六个角色实例。
2. 检查层级、站立状态、face +Y、1.75 高度、脚底接触和游离 Mesh。
3. 保存 `L1_step01_characters.blend`。
4. 输出 `L1_A_TECHNICAL_REPORT.md` 与结构化 JSON。
5. 完成后停止。

本关卡禁止：

1. 导入 Mini Market。
2. 搭建收银区。
3. 设置正式摄像机。
4. 设置正式灯光。
5. 根据渲染图判断视觉质量。

L1-A 可以根据结构化数据完成技术审核。收到新的明确指令后才进入 L1-B。

### 2. L1-B：市场资产空间布局

唯一验证变量：

```text
固定角色与固定市场资产的空间关系是否正确
```

锁定项：

1. 角色层级。
2. 角色高度。
3. 角色底层站立修正。
4. 角色 Collection 内部结构。
5. 已验证 Action 名称。

执行内容：

1. 从 `L1_step01_characters.blend` 开始。
2. 导入两个收银台、两个 cash-register、商品、购物篮或购物车、辅助展示资产、地面和背景墙。
3. 设置左队三人、右队一人、两名 Employee 位于柜台后方。
4. 使用固定技术相机和中性基础灯光，仅用于检查空间关系。
5. 输出 540×960 布局预览。
6. 保存 `L1_step02_checkout.blend`。
7. 完成后停止，等待人工视觉审核。

本关卡通过条件：

1. 规定对象全部存在。
2. 人物穿模数量为 0。
3. 顾客与收银台空间关系正确。
4. Employee 位于柜台后方。
5. 顾客脚底接地。
6. 顾客朝向对应收银通道。
7. 两条队伍在空间上可区分。

本关卡禁止修改正式摄像机与发布级灯光。

### 3. L1-C：摄像机构图

唯一验证变量：

```text
锁定布局在竖屏透视摄像机中的构图是否满足程序化条件
```

锁定项：

1. 全部人物的位置、姿势和朝向。
2. 全部市场资产的位置与尺寸。
3. 地面与背景布局。
4. 材质。
5. 技术灯光。

执行内容：

1. 从人工通过的 `L1_step02_checkout.blend` 开始。
2. 使用 bbox 与 `world_to_camera_view` 设置透视 3/4 斜俯视摄像机。
3. 输出投影检查 JSON。
4. 渲染 540×960 构图预览。
5. 保存 `L1_step03_camera.blend`。
6. 完成后停止，等待人工视觉审核。

程序化通过条件：

1. essential objects 裁切数量为 0。
2. 所有人物完整进入安全区。
3. 两个收银通道完整进入安全区。
4. 顶部无意义空白不超过 15%。
5. 底部无意义空白不超过 15%。
6. 左右安全边距不低于 4%。
7. 相机不进入任何 essential object 的 bbox。
8. 不使用自动网格搜索进行盲目试参。

人工视觉审核只判断构图可读性、层次、遮挡关系和第一眼识别度。收到新的明确指令后才进入 L1-D。

### 4. L1-D：灯光与正式首帧

唯一验证变量：

```text
锁定角色、布局与摄像机后，正式灯光能否形成可审核的首帧
```

锁定项：

1. 人物位置、姿势和朝向。
2. 市场资产布局。
3. 正式摄像机位置、旋转和焦距。
4. 所有对象尺寸。

执行内容：

1. 从人工通过的 `L1_step03_camera.blend` 开始。
2. 设置柔和主光、低强度正面补光、轻微轮廓光和中性环境光。
3. 保留 Kenney 原生材质。
4. 渲染 1080×1920 正式首帧。
5. 保存 `L1_lookdev_v1.blend`。
6. 关闭并重新打开文件，执行保存稳定性验证。
7. 输出正式 PNG 和报告。
8. 完成后停止。

本关卡禁止：

1. 修改角色和布局。
2. 修改已通过的摄像机。
3. 新增动画。
4. 渲染 MP4。
5. 自行判断首帧是否达到发布级质量。

### 5. 阶段切换规则

每个关卡只能通过一条新的明确指令启动。

```text
执行当前关卡
→ 输出文件与结构化摘要
→ Claude Code 停止
→ GPT 进行第一道视觉审核
→ 通过 GPT 初审后由用户最终裁定
→ 用户发送下一关卡指令
```

禁止在同一次 Claude Code 执行中自动完成 L1-A、L1-B、L1-C 和 L1-D。

### 6. GUI 使用规则

Claude Code 无法通过 Live GUI 获得视觉判断能力。

需要人工查看时：

1. Claude Code 保存当前 `.blend` 和预览图后停止。
2. 用户在本机打开 `.blend` 或查看输出图片。
3. GPT 先完成第一道视觉审核，并整理明确修改参数。
4. 用户决定是否放行或返工。
5. Claude Code 根据新的明确指令执行。

### 7. 返工上限

L1 正式首帧最多允许两轮主要视觉返工。

每轮返工必须先指出锁定项、唯一修改变量、具体参数与可验证条件。禁止连续生成 v1、v2、v3、v4、v5 式开放补丁。

---

## 十六、直接发送给 Claude Code 的分阶段指令

以下四段指令必须分开发送。当前只发送 L1-A。前一关卡完成并通过审核后，才发送后一关卡。

### L1-A 指令：固定角色 Append 与结构状态

```text
请在 D:\blender-video-factory 执行 L1-A 固定角色 Append 与结构状态验证。

先完整读取《Blender 固定资产模板路线，新对话交接文档 v4》，重点遵守“Claude Code 的实际工作方式与职责边界”和“L1 执行原则”。

本关卡唯一验证变量：
五个固定角色 Collection 能否在新场景中稳定 Append，并保持角色库中已经验证的层级、站立、尺寸和朝向状态。

输入角色库：
D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane\scene\character_library_v1.blend

只读检查角色 Collection：
CHR_MALE_A
CHR_FEMALE_A
CHR_MALE_B
CHR_FEMALE_B
CHR_EMPLOYEE

从空场景开始，使用 File Append Collection 方式创建六个角色实例：
CHR_MALE_A → Customer_01_Root
CHR_FEMALE_A → Customer_02_Root
CHR_MALE_B → Customer_03_Root
CHR_FEMALE_B → Customer_04_Root
CHR_EMPLOYEE → Employee_01_Root
CHR_EMPLOYEE 再次 Append → Employee_02_Root

只允许重命名 Append 后的顶层 Collection 或已验证 Root 实例。禁止修改内部 Armature、骨骼、Body、Head 和 Mesh 名称。

使用 blender-motion-state-inspection 提取结构化状态，至少检查：
1. Collection 与对象存在性。
2. Empty → Armature → Mesh 层级。
3. 世界空间站立状态。
4. 角色高度约 1.75 Blender 单位。
5. 正面方向 face +Y。
6. 脚底接近地面。
7. 游离 Mesh 数量为 0。
8. 额外 Icosphere 数量为 0。
9. 必要对象未被隐藏或禁用渲染。

异常排查顺序固定为：
角色层级 → 角色姿势 → Root 旋转 → 角色尺寸 → 地面接触 → 角色世界位置 → bbox 与投影数据 → 摄像机。

前六项通过前禁止修改任何相机参数。

本关卡禁止：
1. 导入 Mini Market。
2. 搭建收银区。
3. 设置正式摄像机。
4. 设置正式灯光。
5. 新增动画或关键帧。
6. 重新导入原始 FBX。
7. 修改 character_library_v1.blend。
8. 自动进入 L1-B。

输出：
projects\bvf_asset_test_001_checkout_lane\scene\L1_step01_characters.blend
projects\bvf_asset_test_001_checkout_lane\reports\L1_A_TECHNICAL_REPORT.md
projects\bvf_asset_test_001_checkout_lane\reports\L1_A_motion_state.json

运行 verify 检查输出文件真实存在且可重新打开。

完成后停止，只报告技术通过项、失败项、输出路径和是否允许进入 L1-B。不要执行 L1-B。
```

### L1-B 指令：市场资产空间布局

仅在 L1-A 已通过后发送：

```text
请执行 L1-B 市场资产空间布局验证。

从已通过的文件开始：
projects\bvf_asset_test_001_checkout_lane\scene\L1_step01_characters.blend

本关卡唯一验证变量：
固定角色与本地 Kenney Mini Market 资产的空间关系。

锁定并禁止修改：
1. 角色内部层级。
2. 角色高度与底层站立修正。
3. 角色库原始结构。
4. 角色 Mesh 世界变换。

使用本地已有资产，不搜索、不下载新资产。加入：
1. 两个收银台。
2. 两个 cash-register。
3. 少量商品。
4. 一个购物篮或购物车。
5. 一个 display-bread、display-fruit 或 freezer。
6. 简单地面。
7. 简单背景墙。

确定性布局目标：
左通道三名顾客，右通道一名顾客，两名 Employee 分别位于两个柜台后方。顾客面对对应柜台，Employee 面对顾客。场景摆放只修改已验证 Root。

使用固定技术相机和中性基础灯光，仅用于空间关系预览。禁止在本关卡探索正式摄像机构图或发布级灯光。

程序化检查：
1. 规定对象全部存在。
2. 人物穿模数量为 0。
3. 人物与柜台明显重叠数量为 0。
4. 顾客脚底接地。
5. Employee 位于柜台后方。
6. 左右队伍空间可区分。
7. 顾客朝向对应收银通道。
8. 收银机位于柜台正确区域。

输出：
projects\bvf_asset_test_001_checkout_lane\scene\L1_step02_checkout.blend
projects\bvf_asset_test_001_checkout_lane\reviews\L1_B_layout_preview.png，540×960
projects\bvf_asset_test_001_checkout_lane\reports\L1_B_LAYOUT_REPORT.md

运行 verify 检查输出文件。

完成后停止。Claude Code 不判断预览图好坏，不自动调整到满意，也不进入 L1-C。等待用户与 GPT 人工审核。
```

### L1-C 指令：摄像机构图

仅在 L1-B 布局预览通过人工审核后发送：

```text
请执行 L1-C 摄像机构图验证。

从已通过的文件开始：
projects\bvf_asset_test_001_checkout_lane\scene\L1_step02_checkout.blend

本关卡唯一验证变量：
锁定布局在 1080×1920 竖屏透视摄像机中的构图。

锁定并禁止修改：
1. 全部人物位置、姿势和朝向。
2. 全部市场资产位置、旋转与尺寸。
3. 地面和背景布局。
4. 材质。
5. 技术灯光。

使用 bbox 与 world_to_camera_view 设置透视 3/4 斜俯视摄像机。

程序化通过条件：
1. essential objects 裁切数量 = 0。
2. 所有人物完整进入安全区。
3. 两个收银通道完整进入安全区。
4. 顶部无意义空白 ≤ 15%。
5. 底部无意义空白 ≤ 15%。
6. 左右安全边距 ≥ 4%。
7. 相机不进入任何 essential object bbox。
8. 不使用自动网格搜索或多轮盲目试参。

输出：
projects\bvf_asset_test_001_checkout_lane\scene\L1_step03_camera.blend
projects\bvf_asset_test_001_checkout_lane\reviews\L1_C_camera_preview.png，540×960
projects\bvf_asset_test_001_checkout_lane\reports\L1_C_CAMERA_REPORT.md
projects\bvf_asset_test_001_checkout_lane\reports\L1_C_projection.json

运行 verify 检查输出文件和投影条件。

完成后停止。Claude Code 不判断构图吸引力，不修改灯光，不进入 L1-D。等待用户与 GPT 人工审核。
```

### L1-D 指令：灯光与正式首帧

仅在 L1-C 构图预览通过人工审核后发送：

```text
请执行 L1-D 灯光与正式首帧输出。

从已通过的文件开始：
projects\bvf_asset_test_001_checkout_lane\scene\L1_step03_camera.blend

本关卡唯一验证变量：
锁定人物、布局和摄像机后，正式灯光能否生成可供人工审核的首帧。

锁定并禁止修改：
1. 人物位置、姿势与朝向。
2. 市场资产布局。
3. 摄像机位置、旋转与焦距。
4. 对象尺寸。

使用 Eevee，设置：
1. 柔和主光。
2. 低强度正面补光。
3. 轻微轮廓光。
4. 中性环境光。
5. 适量接触阴影。

保留 Kenney 原生材质。禁止体积雾、景深、运动模糊、正式动画和 MP4 渲染。

输出：
projects\bvf_asset_test_001_checkout_lane\scene\L1_lookdev_v1.blend
projects\bvf_asset_test_001_checkout_lane\reviews\L1_first_frame_v1.png，1080×1920
projects\bvf_asset_test_001_checkout_lane\reports\L1_LOOKDEV_REPORT_v1.md

保存后关闭并重新打开 L1_lookdev_v1.blend，验证：
1. 人物仍然站立。
2. 位置与朝向不变。
3. 材质不丢失。
4. 柜台与商品位置不变。
5. 摄像机与灯光不变。

清空：
projects\bvf_asset_test_001_checkout_lane\reviews\UPLOAD_NEXT\

只复制：
projects\bvf_asset_test_001_checkout_lane\reviews\UPLOAD_NEXT\L1_first_frame_v1.png

运行 verify 检查全部输出。

完成后停止。Claude Code 不判断发布潜力，不自动返工，不开始动画，不进入 L2。
```

---

## 十七、L1 通过后的下一步

L1 通过后保存：

```text
checkout_template_v1.blend
```

该文件成为后续视频模板。

下一阶段只测试：

```text
一名顾客使用 walk
＋
角色 Root 从中间通道移动到旁边队尾
```

动画原则：

1. Armature 播放已验证 walk。
2. Root 负责世界位移。
3. 其余角色使用固定站立或 idle。
4. 不同时加入窗口关闭。
5. 不同时加入三人分流。
6. 不移动摄像机。
7. 只做 2 至 3 秒。
8. 输出一个短 MP4 和 dense contact sheet。

通过后，再扩展为 4 至 6 秒机制测试。

---

## 十八、严格禁止重复的旧路径

新 GPT 和 Claude Code 必须遵守：

1. 不使用人物 GLB。
2. 不重新下载人物包。
3. 不重新搜索 Poly Haven。
4. 不使用 Sketchfab 解决当前问题。
5. 不退回基础几何人物。
6. 不从原始 FBX 重建多人场景。
7. 不重新自动标准化五名角色。
8. 不继续 character library 多视图评审板。
9. 不自动计算人物 Up Axis。
10. 不在人物状态未通过时调整相机。
11. 不生成 15 格或多相机复杂评审板。
12. 不一次执行从空场景到完整视频的单体大型脚本。允许分阶段执行并在阶段间保存独立文件。
13. 不开始多人动画。
14. 不渲染完整视频。
15. 不进入剪映。
16. 不修改 `D:\video-factory`。
17. 不继续原生几何项目 style_v5。
18. 不删除任何历史文件。

---

## 十九、统一上传规则

上传目录：

```text
projects\bvf_asset_test_001_checkout_lane\reviews\UPLOAD_NEXT
```

L1 阶段只允许放：

```text
L1_first_frame_v1.png
```

用户上传该文件即可。

如果执行失败，只放一张：

```text
L1_failure_state.png
```

并附失败说明。

技术调试阶段不再默认上传：

1. `.blend`
2. 大量 JSON
3. 多视图板
4. 全部日志
5. 原始资产

GPT 需要核查时再指定文件。

---

## 二十、当前状态机

```text
environment_passed
graybox_mechanism_passed
native_geometry_style_failed
asset_smoke_passed
kenney_fbx_audit_passed
single_character_static_passed
single_character_idle_passed
single_character_walk_passed
glb_route_disabled
horizontal_rest_pose_bug_identified
camera_misattribution_identified
motion_state_inspection_skill_active
character_library_v1_ready
five_characters_normalized_to_1_75
fixed_library_lookdev_pending
```

当前唯一有效状态：

```text
fixed_library_lookdev_pending
```

---

## 二十一、新 GPT 对话建议上传文件

最小上传：

```text
Blender_固定资产模板路线_新对话交接文档_v4.md
```

需要核查证据时再上传：

```text
FINAL_VALIDATION_REPORT.md
REUSABLE_RESULTS.md
KENNEY_CHARACTER_IMPORT_AUDIT.md
```

如果角色库路径或 Collection 名称不清楚，可上传 Claude Code 的最新角色库报告。

不需要一次上传：

1. 所有失败图片。
2. 所有 contact sheet。
3. 全部构建脚本。
4. 所有 `.blend`。
5. 整个仓库 ZIP。

---

## 二十二、新 GPT 对话第一条消息

```text
请完整读取我上传的《Blender 固定资产模板路线，新对话交接文档 v4》。

此前角色与场景问题已经完成复盘。现在已经确认：

1. 人物必须使用 Kenney FBX。
2. GLB 路线已禁用。
3. 横躺 Rest Pose 是长期误判的主要根因。
4. 过去大量相机返工来自错误人物状态。
5. 标准角色库 character_library_v1.blend 已经建立。
6. 五个角色全部归一化到 1.75 单位高度，朝向统一，层级正确。
7. 后续不再从原始 FBX 重复导入。
8. blender-motion-state-inspection 已纳入强制诊断流程，必须先提取结构化状态，再以截图确认。
9. 当前只做固定角色库首帧 L1。
10. 首帧通过前禁止动画。
11. 不再生成复杂评审板。

请先复述你对当前状态、已解决问题、固定角色库用法、L1 目标与禁止事项的理解。确认无误后，再审核交接文档中的 Claude Code L1 指令，不要扩大任务范围。
```

---

## 二十三、最终生产设想

如果固定角色库首帧和简单 walk 测试都通过，最终生产方式为：

```text
固定资产库
↓
固定超市场景模板
↓
Claude Code复制角色与设备
↓
修改人数、位置与动作
↓
Blender输出空间动画镜头
↓
剪映加入配音、字幕、音效与节奏
↓
用户人工锁定
```

优先内容：

1. 排队和服务瓶颈。
2. 超市货架和库存。
3. 道路拥堵传播。
4. 电梯停靠。
5. 仓储与物流。
6. 外卖接单距离。
7. 人流容量。
8. 供需、距离和等待。
9. 多任务占用空间。
10. 物品数量累积。

暂不适合：

1. 人物对话剧情。
2. 面部表演。
3. 写实历史还原。
4. 复杂城市。
5. 大型灾难。
6. 战斗与多人接触。
7. 写实角色短剧。

---

## 二十四、最终交接结论

当前无需继续讨论：

> Blender 能不能从空场景自动生成完整视频？

下一步只验证：

> 通过已验证的固定角色库和统一市场资产，Claude Code 能不能稳定搭出一张有发布潜力的首帧？

角色标准化阻塞已经解除。

当前唯一下一步：

```text
执行 L1-A 固定角色 Append 与结构状态验证
→ Claude Code 输出技术报告并停止
→ 审核通过后发送 L1-B
→ L1-B 输出布局预览并停止
→ 人工审核后发送 L1-C
→ L1-C 输出构图预览并停止
→ 人工审核后发送 L1-D
→ L1-D 输出正式首帧并停止
→ 用户和 GPT 完成人工发布潜力判断
```
