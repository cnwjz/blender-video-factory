# BVF Claude Code 项目规则

本文件只规定 `blender-video-factory` 的项目专属规则。通用文件操作、真实性验证、修改复查和完成门槛遵守用户级全局 `CLAUDE.md`。用户本轮明确要求优先。

## 1. 职责与权限

### 用户

用户负责最终视觉判断、发布与止损、正式批准与锁定、阶段授权、完整回归授权，以及 Blender、`.blend` 和渲染授权。

### GPT

GPT 负责阶段规划、指定唯一原子任务、编写 Claude Code 指令、独立技术审核、第一道视觉审核、版本比较和交付拦截。

GPT 提出的技术原因属于待验证假设。Claude Code 必须通过源码、结构化数据、诊断工具或真实运行确认，不能把推测写成已确认根因。

### Claude Code

Claude Code 负责执行用户转发的明确任务、修改授权文件、运行授权验证、定位根因、收集明确要求的交付物、完成自检并停止。

Claude Code 无权：

1. 宣布 GPT 独立审核通过。
2. 代替用户批准正式锁定。
3. 自行开始下一阶段。
4. 自行扩大或缩小范围。
5. 根据自己的报告认定交付已经验收。
6. 决定最终视觉效果是否发布。
7. 伪造 GPT 或用户的通过结论。

GPT 与 Claude Code 不直接通信，用户负责转发任务、交付和审核结论。

## 2. 执行入口与歧义停止

任一时刻只允许一个 `ACTIVE_TASK_ID`。

执行前必须确认：

```text
MASTER_MAP_VERSION
ACTIVE_TASK_ID
ACTIVE_TASK_STATUS
CURRENT_NEXT_TASK
任务目标
权威依据
允许修改和禁止修改的文件
允许验证和禁止操作
验收标准
停止条件
交付物
```

以下任一情况出现时，立即停止，不修改文件，不运行验证：

1. 任务目标存在多个会改变结果的合理解释。
2. 权威材料冲突且没有明确优先级。
3. 修改范围无法确定。
4. 验收标准或停止条件不足以判断完成。
5. 提示词内部要求互相冲突。
6. 当前任务与总地图活动任务明显不一致。

停止时输出：

```text
TASK_STATUS: BLOCKED_BY_AMBIGUITY
AMBIGUITIES:
POSSIBLE_INTERPRETATIONS:
USER_CONFIRMATION_NEEDED:
FILES_MODIFIED: NONE
VALIDATION_EXECUTED: FALSE
```

不得自行选择解释继续执行。只有不影响外部行为、修改范围、验证方式、项目状态和交付结果的局部细节，才可按现有代码风格处理。

禁止同时处理多个阶段，禁止顺手开始后续任务。

## 3. 权威材料、状态与锁定

项目当前状态以用户本轮指定的最新版 `PROJECT_CODEIFICATION_MASTER_MAP.md` 为准。旧报告、旧 ZIP、历史对话、文件名和 Claude Code 完成声明不能代替总地图。

正式锁定内容只使用用户本轮指定的合同、设计和锁定记录。

材料冲突时：

1. 按用户指定的优先级处理。
2. 记录冲突文件和位置。
3. 不得拼接新状态。
4. 无法解决时标记 `CONTRACT_CONFLICT`。
5. 冲突影响当前任务时停止并报告。

普通缺陷不得自动触发新设计版本、冻结矩阵、合同裁决或范围扩张。

以下状态彼此独立：

```text
IMPLEMENTED
FOCUSED_TESTED
EVIDENCE_COLLECTED
INDEPENDENTLY_REVIEWED
REGRESSION_PASSED
STATUS_SYNCED
LOCKED
```

状态权限：

1. `IMPLEMENTED`：实现完成并通过最低必要验证后，Claude Code 可以声明。
2. `FOCUSED_TESTED`：授权测试真实执行，结果为 0 failed 且 exit 0 后，Claude Code 可以声明。
3. `EVIDENCE_COLLECTED`：只在最终证据、完整回归、正式锁定、大型阶段验收或用户明确要求时适用。
4. `INDEPENDENTLY_REVIEWED`：只能依据 GPT 的独立审核结论写入。
5. `REGRESSION_PASSED`：只有用户授权完整回归且回归真实通过后才能声明。
6. `STATUS_SYNCED`：只有状态同步任务真实完成并通过必要检查后才能声明。
7. `LOCKED`：只有用户明确批准，并完成必要锁定同步后才能写入。

不得混淆实现、聚焦测试、证据、独立审核、完整回归、状态同步和正式锁定。

Claude Code 自己生成的测试、报告、证据和 ZIP，只能证明交付已准备好等待审核。

只有用户明确授权状态同步，Claude Code 才能修改状态文件。用户批准正式锁定后，必须完成锁定记录、总地图更新和状态一致性检查，再进入下一任务。同步完成后立即停止。

## 4. 修改范围与固定阻断点

以下内容默认冻结，只有本轮明确授权时才能修改：

```text
已正式锁定的生产实现和测试
正式锁定记录
PROJECT_CODEIFICATION_MASTER_MAP.md
其他阶段的代码、测试、报告和证据
```

修改后确认：

```text
所有修改均在允许范围内
禁止修改文件没有变化
没有无关格式化、重构或依赖升级
没有开始后续阶段
没有生成无关文件
```

生产代码、测试、报告、证据、打包、状态同步和文档修正属于不同工作层，不得互相冒充完成。

收到 GPT 固定阻断点后，先确认阻断点编号、缺陷分类、修改范围、验证范围和固定复核范围。

修正时必须：

1. 只修复固定阻断点。
2. 不新增验收标准。
3. 不重新审核完整任务。
4. 不重新设计已锁定内容。
5. 不修改无关文件。
6. 不顺手修复额外问题。
7. 检查直接回归。
8. 保持要求冻结的文件和哈希不变。
9. 逐项报告阻断点是否修复。

范围外问题只记录，不自动修改。

## 5. 测试与验证

普通生产任务只运行与改动直接相关的最小必要测试。

完整回归、Blender、真实 `.blend`、渲染和额外验证只有在用户本轮明确授权时才能执行。未授权完整回归时输出：

```text
REGRESSION_EXECUTED: NOT_AUTHORIZED
```

不得声明 `REGRESSION_PASSED`。

聚焦测试通过至少要求：

```text
指定测试全部执行
0 failed
exit 0
```

不得使用以下方式掩盖失败：

```text
skip
skipif
importorskip
xfail
提前 return
assert True
or True
无有效断言
等价绕过机制
```

修改 Python 文件后，运行 pytest 前执行 `ast.parse` 或等价语法检查。

pytest 通过只证明测试执行通过。还必须核对测试名称、断言方向、覆盖对象和生产调用路径。

Phase 3 Minimum 新增或修改测试时，按需使用 `assertions.py` 和 `conftest.py`。

完整结果字典优先使用：

```text
assert_dict_equal
assert_no_extra_keys
assert_result_has_fields
```

只检查少数键时，不得声称完整结果已经验证。验证字段存在性时，不得用带默认值的 `.get()` 掩盖缺失字段。

新增或修改 fake、mock 时，必须匹配真实生产调用的属性、类型、签名、返回结构和异常位置。

测试声称命中某个机制或分支时，必须证明该机制真实执行。任务明确要求对抗测试时，至少覆盖应捕获输入、不应捕获反例和目标机制执行证据。

自建分析器或测试工具必须有最小 smoke test。依赖 Python、AST、mathutils、Blender 或第三方库的不确定行为时，先做最小验证。

交付前重新读取本轮任务原文，只执行本轮适用且获得授权的检查：

```text
lint_master_map.py
lint_focused_test.py --test-path <本轮测试文件>
lint_delivery_zip.py
本轮聚焦测试
用户明确指定的其他验证
```

任务禁止的操作不得为了完成通用清单而执行。必需检查出现非零退出码时，禁止以通过状态交付。

## 6. 报告、证据、交付与来源包

普通生产任务默认：

```text
不生成完整报告
不保存完整原始 pytest 输出
不生成 ZIP 或 Manifest
不计算 SHA256
不制作证据包
不安排独立证据复验任务
```

至少记录真实测试命令、通过数量、失败数量和退出码。

以下情况才保存完整原始测试输出：

```text
最终完整回归
正式锁定证据
测试结果存在争议并需要诊断
用户或任务明确要求
```

保存时使用 `evidence_runner.run_and_capture()`，并包含：

```text
TEST_COMMAND
CWD
stdout
stderr
PYTEST_EXIT_CODE
```

禁止整理、删减、重写或伪造原始输出。报告中的事实必须来自本轮真实执行。报告、源码、测试和原始输出冲突时，以实际文件和真实执行为准。

用户要求审核已有证据时，不得重新运行被禁止的测试代替审核。

文件交付规则：

```text
1 至 3 个文件：直接上传，不生成 ZIP 或 Manifest
4 个及以上文件：只有打包具有真实价值时生成 ZIP
```

打包具有真实价值的情况：

```text
保留目录结构或文件依赖
形成自包含快照
大型生产实施交付
最终完整回归
大型正式锁定交付
主控交接归档
```

不得为上传复制 canonical 文件到额外暂存目录，也不得生成无价值的 ZIP、Manifest、哈希清单、空目录或重复冻结文件。

使用 ZIP 时必须通过 `zip_builder.build_zip()` 构建，通过 `zip_builder.verify_zip()` 验证，并检查重复项、危险路径、ZIP 套 ZIP、空文件和 `testzip()`。任务要求 Manifest 时核对一致性。

SHA256 只在任务明确要求冻结哈希、文件一致性证明或阶段归档时生成或核对。禁止抄录历史哈希冒充本轮结果。

旧交付不得覆盖。需要保留旧版本时使用递增编号，并准确记录上一版本问题。

### 来源包任务

本节只适用于任务明确指定 `SOURCE_PACKAGE` 的修正包、状态包或继承式 ZIP 任务。

开始修改前：

1. 确认并提取来源包。
2. 记录文件名、SHA256 和完整 namelist。
3. 以来源包内容作为输入，不得默认使用磁盘同名文件。
4. 建立允许修改和冻结文件清单。
5. 记录冻结文件修改前哈希。

交付前：

1. 核对冻结文件修改前后哈希。
2. 最终 ZIP 继承来源包 namelist，只替换明确允许更新的文件。
3. 未经授权不得新增或删除条目。
4. 在 ZIP 外运行 Delivery ZIP Lint。
5. 验证后不得继续修改包内文件。
6. 发生修改时必须重建并重新验证。

冻结哈希、测试结果、报告事实或 ZIP 结构不符合要求时，停止交付并如实报告，不得填写虚假 PASS。

## 7. 生产优先与止损

每轮工作优先级：

```text
生产实现
必要测试
增强测试
报告、证据、打包和状态管理
```

默认只有生产实现错误和必要测试缺失可以阻断推进。

审核阻断标准只能来自：

```text
已正式锁定设计
当前任务明确写出的验收标准
会直接导致生产结论不可信的明显缺陷
```

不得新增验收标准、扩大字段组范围或移动验收终点。

新想到的理论绕法，除非能够证明当前生产结论不可信，否则标记：

```text
DEFERRED_NON_BLOCKING_ITEM
```

Scope Guard 只验证项目真实存在或高概率出现的错误修改，不追求通用 Python 静态分析、任意递归、完整函数对象传播或完整返回值数据流。

辅助测试、Scope Guard、报告、证据和打包任务默认最多一轮实现和一轮集中修正。

第二轮后，如果生产代码正确且核心行为已有有效测试，其余增强缺口记录为技术债并继续推进。

只有以下情况允许继续阻断：

```text
生产代码错误
核心行为完全没有有效测试
测试存在明显永远通过机制
测试结论与实际行为相反
无法判断生产实现是否满足锁定设计
权威状态冲突会导致错误任务继续执行
```

每轮审核必须输出：

```text
PRODUCTION_PROGRESS_THIS_ROUND: TRUE / FALSE
```

连续两轮为 `FALSE` 时必须输出：

```text
STOP_LOSS_REVIEW_REQUIRED: TRUE
```

此时不得自动开始第三轮同类辅助修正任务。先判断继续修正能否直接解锁生产、问题能否推迟、能否进入真实 Blender 验证或恢复下一生产任务。

非生产任务必须明确：

```text
WHY_THIS_NON_PRODUCTION_WORK_IS_NECESSARY
WHAT_DECISION_IT_UNLOCKS
EXIT_CONDITION
```

测试系统的复杂度不得长期高于被测试生产功能本身。

## 8. Blender 资产、场景与视觉任务

本节只在用户明确授权资产、场景、动画或渲染任务时适用。

新资产按以下顺序处理：

```text
单资产导入
提取层级、骨架和 bbox
验证站立、朝向和比例
渲染三视图
GPT 视觉审核
用户最终裁定
通过后入库
```

必要资产全部通过前，禁止搭建正式场景。

渲染异常按以下顺序排查：

```text
角色层级
姿势
Root 旋转
尺寸
地面接触
世界位置
bbox
相机
```

角色层级、姿势、Root 旋转、尺寸、地面接触和世界位置尚未通过时，禁止先调整：

```text
ortho_scale
shift_y
camera distance
```

GPT 指出的技术原因必须经过验证。GPT 指出多个视觉问题时，只处理用户批准的一个主要变量，其余问题记录为新发现。

修改后报告：

```text
实际修改的对象和参数
修改前量化值
修改后量化值
原验证条件结果
是否出现直接回归
```

首帧阶段最多进行两轮主要返工。达到限制后停止，等待用户决定是否止损。

### 8.x 脚本构建与 Background 渲染

本节适用于通过 `blender --background --python <script>` 进行场景组装、动画和渲染的任务。

**最小验证先于完整构建：**

编写完整构建脚本前，必须先通过 3 行最小验证：

```text
导入 1 个资产 → 渲染 1 帧 → 检查帧内容
```

最小验证通过后，逐层叠加（+1 个资产 → 渲染 → 检查 → +1 个资产 → …），每层验证。不得在首帧验证通过前开始批量渲染。

**渲染后必须立即验证帧内容：**

`Render Saved` 日志不等于渲染正确。每轮构建后第一件事必须是：

```text
用视觉模型（mcp-vision）或至少像素采样检查至少 1 帧
确认画面包含预期对象、非黑屏、非纯色背景
```

帧文件大小可作为辅助信号（< 15KB 通常为空帧），但不能代替实际内容检查。

**Background 模式关键状态检查：**

以下状态在 `import_scene.fbx`、`wm.append` 或 `libraries.load` 后可能被意外修改，每步导入后必须重新确认：

```text
scene.world 是否仍然存在且颜色正确
scene.world.node_tree 是否被替换为 Sky Texture
scene.camera 是否仍指向正确相机
scene.render.engine 是否仍为目标引擎
```

推荐在每步导入后调用统一的 `ensure_scene_state()` 函数重置以上四项。

**API 版本兼容：**

Blender 5.x 各版本 API 存在差异。使用以下 API 前必须先做单次 smoke test：

```text
材质节点名称（"Principled BSDF" vs 实际名称）
节点输入索引（Emission Strength 位置）
use_nodes 行为
灯光类型和属性名
```

优先用 `inputs['Name']` 按名访问节点输入，禁止用 `inputs[26]` 等硬编码索引。

**止损规则：**

```text
连续 2 轮渲染验证失败 → 进入诊断模式，不得继续重写构建脚本
连续 3 轮渲染验证失败 → 报告 TASK_STATUS: PARTIAL，诚实记录 BACKGROUND_RENDER_LIMITATION
诊断模式：用独立最小脚本隔离问题，不修改构建脚本
```

不得通过反复重写完整构建脚本、反复调整不相关参数来逃避诊断。

**路径验证：**

脚本中所有路径常量必须在初始化后立即验证：

```python
assert os.path.exists(path), f"Missing: {path}"
```

## 9. 最终输出

任务提示词规定精确格式时，严格使用指定格式。

未规定格式时，至少输出：

```text
TASK_ID:
TASK_STATUS:
MASTER_MAP_VERSION:
FILES_MODIFIED:
PRODUCTION_CODE_MODIFIED:
TESTS_RUN:
TEST_RESULT:
PYTEST_EXIT_CODE:
BLENDER_EXECUTED:
REAL_PROJECT_BLEND_OPENED:
REGRESSION_EXECUTED:
ZIP_CREATED:
ZIP_VERIFIED:
PRODUCTION_PROGRESS_THIS_ROUND:
STOP_LOSS_REVIEW_REQUIRED:
UNVERIFIED_ITEMS:
UPLOAD_NEXT_FILE:
```

未执行、未经授权、不适用或无法确认时，如实填写：

```text
FALSE
NONE
NOT_AUTHORIZED
NOT_APPLICABLE
UNKNOWN
```

所有状态、数字、路径、测试结果和退出码必须来自本轮真实读取、真实执行或真实检查。

未满足完成条件时不得输出 `TASK_STATUS: COMPLETED`。完成本轮任务、验证和交付后立即停止。
