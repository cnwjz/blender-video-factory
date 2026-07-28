# Collection Rules 原始需求审计报告

```text
TASK_ID: COLLECTION_RULES_ORIGINAL_REQUIREMENT_AUDIT
MASTER_MAP_VERSION: R70
AUDIT_DATE: 2026-07-25
TASK_TYPE: ORIGINAL_REQUIREMENT_AUDIT
PRECEDING_TASK: COLLECTION_RULES_DESIGN_AUDIT_INPUT_COLLECTION
CORRECTION: R2 — 修正 Blender Collection API 描述错误、空值语义前后矛盾、输出层级和计数不一致
```

## 1. 权威来源和优先级

按权威递减排列：

| 优先级 | 来源 | 类型 | 权威级别 |
|--------|------|------|----------|
| 1 | `Blender_固定资产模板路线_新对话交接文档_v4.md` | 原始业务需求 | AUTHORITATIVE_BUSINESS_REQUIREMENT |
| 2 | `asset_scene_preflight_core.py` L202-221, L411-419 | 14A Schema 合同（已锁定） | AUTHORITATIVE_SCHEMA_CONTRACT |
| 3 | `ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md` §3 | 实现合同（已发布） | AUTHORITATIVE_IMPLEMENTATION_CONTRACT |
| 4 | `PHASE_3_MINIMUM_DESIGN_SPEC_R1.md` §10.1 | 设计规格 | DESIGN_SPEC_REFERENCE |
| 5 | `14B_2A_SCOPE_GIT_AND_LOCK_EVIDENCE.txt` | 范围锁定证据 | LOCK_EVIDENCE |
| 6 | `GLOBAL_CODEIFICATION_AUDIT_REPORT.md` | 历史审计摘要 | HISTORICAL_AUDIT_SUMMARY |
| 7 | `POST_14B_3B_GLOBAL_REMAINING_REQUIREMENTS_AUDIT_R1_REPORT.md` | 历史审计摘要 | HISTORICAL_AUDIT_SUMMARY |
| 8 | `PHASE_3_CURRENT_IMPLEMENTATION_COVERAGE_AUDIT.md` | 实现覆盖率审计 | COVERAGE_AUDIT |
| 9 | `COLLECTION_RULES_DESIGN_AUDIT_INPUT_COLLECTION_REPORT.md` | 输入收集报告 | INPUT_COLLECTION_REPORT |

**冲突解决规则**：优先级 1 > 2 > 3 > 其余。历史审计摘要中的概括性分类不得覆盖原始需求或 schema 的具体条款。优先级 2 和 3 的内容描述不同粒度时，取更精确者。

## 2. 原始业务需求

### 2.1 权威需求原文

来自 `Blender_固定资产模板路线_新对话交接文档_v4.md`：

**§2 已包含角色**（行 655-661）:
```text
Collection: CHR_MALE_A
Collection: CHR_MALE_B
Collection: CHR_FEMALE_A
Collection: CHR_FEMALE_B
Collection: CHR_EMPLOYEE
```

**§7 角色库预检**（行 714-723）:
```text
正式首帧构建前，只检查：
1. 文件存在且可正常打开。
2. 五个角色 Collection 存在。
3-8. ...
```

**L1-A 指令**（行 1383-1385）:
```text
使用 blender-motion-state-inspection 提取结构化状态，至少检查：
1. Collection 与对象存在性。
2-9. ...
```

### 2.2 需求提取

```text
BUSINESS_REQUIREMENT_CR_01:
  SOURCE: 交接文档 v4 §7.2 + L1-A §1
  DESCRIPTION: 验证指定名称的 Collection 在 bpy.data.collections 中存在
  TYPE: 可代码化
  HARD_REQUIREMENT: TRUE

BUSINESS_REQUIREMENT_CR_02:
  SOURCE: 交接文档 v4 L1-A §1
  DESCRIPTION: 验证 Append 后的对象在 Collection 中的存在性
  TYPE: 可代码化
  HARD_REQUIREMENT: TRUE
  NOTE: 此需求对应 per-target 的 Collection 成员关系检查

BUSINESS_REQUIREMENT_CR_03:
  SOURCE: 交接文档 v4 §6.1, §6.2
  DESCRIPTION: 只允许使用已验证的 Collection
  TYPE: DOCUMENT_ONLY
  HARD_REQUIREMENT: FALSE
  REASON: "已验证"是人工判断，无法代码化

BUSINESS_REQUIREMENT_CR_04:
  SOURCE: 交接文档 v4 §2
  DESCRIPTION: 五个具体角色 Collection 名称 (CHR_MALE_A 等)
  TYPE: 业务实例参数
  HARD_REQUIREMENT: FALSE
  REASON: 名称应通过 spec 参数化传入，不应在代码中硬编码
```

## 3. 当前 Schema 字段

### 3.1 全局层

位置：`spec.collection_rules`（可选，`null` 允许）

```json
"collection_rules": {
  "required_collection_names": ["非空字符串"],
  "forbidden_collection_name_patterns": ["字符串"]
}
```

| 属性 | `required_collection_names` | `forbidden_collection_name_patterns` |
|------|---------------------------|--------------------------------------|
| JSON 类型 | array[string] | array[string] |
| 字段可选 | 是 | 是 |
| 元素约束 | 非空字符串 | 任意字符串 |
| 空数组语义 | 未定义（defer to design） | 未定义（defer to design） |
| 字段缺失语义 | 未定义（defer to design） | 未定义（defer to design） |
| `collection_rules` 为 null | 未定义（defer to design） | 同上 |
| 仅 `collection_rules` 空对象 `{}` | 未定义（defer to design） | 同上 |
| 两个子字段分别启用时的顶层结果 | 未定义（defer to design） | 同上 |

14A 验证代码：[asset_scene_preflight_core.py:202-221](protocol_guard/phase3_min/asset_scene_preflight_core.py#L202-L221)

### 3.2 Per-target 层

位置：`spec.targets[i].required_collection_names`（可选）

| 属性 | 值 |
|------|-----|
| JSON 类型 | array[string] |
| 字段可选 | 是 |
| 元素约束 | 非空字符串 |
| 空数组语义 | 未定义（defer to design） |
| 字段缺失语义 | 未定义（defer to design） |

14A 验证代码：[asset_scene_preflight_core.py:411-419](protocol_guard/phase3_min/asset_scene_preflight_core.py#L411-L419)

### 3.3 Canonicalization 预留字段

[asset_scene_preflight_core.py:573-578](protocol_guard/phase3_min/asset_scene_preflight_core.py#L573-L578) 的 `_NAME_LIST_WHITELIST` 已包含：

```python
"missing_required_collections",
"missing_required_collection_names",
"forbidden_collection_matches",
```

这些字段名暗示历史预期但从未被生成，不代表已锁定的输出结构合同。

## 4. 全局 Collection 规则的确定需求

权威需求和 Implementation Contract R2 没有完整规定字段缺失、null、空数组、仅 `collection_rules` 空对象和两个全局子字段分别启用时的顶层结果语义。这些属于设计自由，由 `COLLECTION_RULES_DESIGN_R1` 唯一裁定。

候选行为（设计输入，不构成裁定）：
- 字段缺失或 null → 候选为 NOT_CHECKED
- 空数组 → 候选为 NOT_CHECKED 或 PASS
- 仅空对象 `{}` → 候选为 NOT_CHECKED

以下由明确合同支持的需求已确定：

### 4.1 `collection_rules.required_collection_names`

| 问题 | 裁定 | 依据 |
|------|------|------|
| 是否检查全局 Collection 存在性 | 是 | Impl Contract R2 §3.1: `bpy.data.collections.get(name)` must return non-None |
| 名称缺失时的结果 | FAIL | Impl Contract R2: "Missing → FAIL" |
| 名称匹配是否大小写敏感 | 是（Blender 原生语义） | `bpy.data.collections.get(name)` 使用 Blender 内部命名，大小写敏感 |
| "五个角色 Collection" 是否硬编码 | 否 | 名称来自业务实例，通过 spec `required_collection_names` 参数化 |

### 4.2 `collection_rules.forbidden_collection_name_patterns`

| 问题 | 裁定 | 依据 |
|------|------|------|
| Glob 匹配范围 | 全局 `bpy.data.collections` 中的所有 Collection | Impl Contract R2 §3.2: "Any collection whose name matches → FAIL" |
| Glob 命中结果 | FAIL | Impl Contract R2 §3.2 |
| Glob 匹配是否大小写敏感 | 设计自由 | Impl Contract R2 未指定；`casefold_glob_match` 函数已存在于 14A core |
| 多个 pattern 匹配同一 collection 时 | 报告一次即可 | 等同 forbidden hierarchy patterns 模式 |
| 与 required 同时命中时 | 两者独立检查，任何 FAIL 导致整体 FAIL | Impl Contract R2 未定义优先级，两者同级 |

### 4.3 全局规则的数据源和操作

```text
READ_BPY_DATA_COLLECTIONS_KEYS: 枚举 bpy.data.collections 中的所有 Collection 名称
READ_COLLECTION_BY_NAME: bpy.data.collections.get(name)
```

这些是全新的 Blender API 访问，需要 Scope Guard 保护。

## 5. Per-target Collection 规则的确定需求

全局字段的空值语义同样适用于 per-target 字段：字段缺失、null 和空数组的语义属于设计自由，由 `COLLECTION_RULES_DESIGN_R1` 裁定。root 前置失败后的结果状态（root 不存在、名称歧义、类型不匹配）也没有独立的权威依据，列入设计自由。

以下由明确合同支持的需求已确定：

### 5.1 `targets[i].required_collection_names`

| 问题 | 裁定 | 依据 |
|------|------|------|
| 是否属于有效需求范围 | 是 | Schema 中有字段定义；Impl Contract R2 §3.3 描述了 target-to-collection 链接 |
| 是否检查 target root 的 Collection 归属 | 是 | Impl Contract R2: "does the target's root object belong to at least one of the required collections?" |
| 遍历范围 | 直接 Collection + 递归祖先闭包 | Impl Contract R2: "directly or via any recursive parent-child collection membership" |
| 多个 required 名称满足条件 | 至少一个 | Impl Contract R2: "at least one of the required collections" |

### 5.2 Blender Collection 数据模型

```text
1. object.users_collection 只返回对象直接所属的 Collection。
   不存在 collection.users_collection 属性。

2. Collection 的祖先关系必须通过父级 Collection 的 children
   关系反向推导。

3. 后续设计至少需要考虑：
   a. 先读取 object.users_collection 取得直接 Collection；
   b. 再从允许的数据源物化 Collection 及其 children；
   c. 建立 child identity 到 parent identity 的反向索引；
   d. 从直接 Collection 向上计算祖先闭包。

4. 具体物化次数、缓存、排序、visited identity 集合、
   Scene master collection 是否纳入以及异常边界，
   全部留给 COLLECTION_RULES_DESIGN_R1。

5. 遍历终止、重复 Collection 和防重复访问机制留给设计。
   不得声称 Blender 层级绝对不需要 visited 或重复处理。
```

### 5.3 Per-target 数据源和操作

```text
READ_USERS_COLLECTION: obj.users_collection（只返回直接 Collection）
READ_COLLECTION_CHILDREN: collection.children
ANCESTOR_CLOSURE: 通过 child→parent 反向索引从直接 Collection 向上计算
```

需要 Scope Guard 保护。

## 6. 两层规则的关系

### 6.1 判定过程

三个来源对范围的描述：

| 来源 | 描述 | 粒度 |
|------|------|------|
| `GLOBAL_CODEIFICATION_AUDIT_REPORT.md` 行 199 | "collection_rules — 全局规则，非 per-target" | 概括性分类 |
| `ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md` §3 | 同时描述全局存在性 + per-target 对象归属检查 | 精确算法描述 |
| 14A Schema `validate_spec()` | 同时有全局 `collection_rules` 和 per-target `targets[i].required_collection_names` | 精确字段定义 |

审计报告中的"全局规则，非 per-target"是历史审计中的概括性简化标签——该标签强调了 Collection Rules 主要检查 `bpy.data.collections`（全局数据源）的事实，但"非 per-target"的描述与 Implementation Contract R2 §3.3 的对象归属检查和 schema 中 `targets[i].required_collection_names` 字段的存在矛盾。

这不是真正的合同冲突。Implementation Contract R2 §3 和 Schema 同时支持两种粒度。审计报告的概括性标签不足以构成权威冲突，因为它不享有前两者的权威级别。

### 6.2 最终裁定

```text
RULE_LAYER_RELATION: TWO_COMPATIBLE_RULE_LAYERS
```

两层规则独立、互补、可以共存于同一实现。

| 层级 | Spec 位置 | 检查内容 | 数据源 | 输出位置 |
|------|----------|---------|--------|---------|
| 全局 | `collection_rules` | Collection 存在性 + 禁制 | `bpy.data.collections` | 全局层结果（候选键名由设计裁定） |
| Per-target | `targets[i].required_collection_names` | Root object 是否属于 required collections | `obj.users_collection` + 祖先反向索引 | 对应 target 的检查结果（候选键名由设计裁定） |

注意：上表输出位置为候选方向，具体键名和结构由设计裁定，不属于已确定需求。

**证明**：
- Schema 允许两层同时存在且独立验证（不存在互斥约束）
- Implementation Contract R2 同时描述了两层（§3.1-3.2 全局，§3.3 per-target）
- 原始业务需求同时要求全局存在性和对象归属（交接文档 §7.2 + L1-A §1）
- 两层使用不同的 Blender API（`bpy.data.collections.get` vs `obj.users_collection`），数据路径不冲突
- 两层独立启用：全局规则触发不代表 per-target 规则触发，反之亦然

不属于 `TRUE_CONTRACT_CONFLICT`：没有任何两个权威来源提出相互排斥的要求。审计报告的概括性标签是简化，而非与 schema/合同矛盾的独立裁决。

## 7. 代码化范围

以下需求可以被确定为 CODE_ENFORCEABLE：

```text
CE-CR-01: 全局 Collection 存在性检查
  读取: bpy.data.collections
  检查: required_collection_names 中每个名称的 collection 是否存在
  结果: PASS (全部存在) / FAIL (至少一个缺失)

CE-CR-02: 全局 Collection 禁制检查
  读取: bpy.data.collections
  检查: 任何 collection 名称匹配 forbidden_collection_name_patterns
  结果: PASS (无匹配) / FAIL (至少一个匹配)

CE-CR-03: Per-target Collection 归属检查
  读取: obj.users_collection → 直接 Collection → 祖先反向索引
  检查: root object 是否属于至少一个 required_collection_names
  结果: PASS (至少一个满足) / FAIL (一个都不满足)

CE-CR-04: ERROR 边界
  读取: bpy.data.collections 不可访问，obj.users_collection 读取异常
  结果: ERROR (遵循已锁定 ERROR 收集模式)
```

以下为 DOCUMENT_ONLY / 不可代码化：

```text
DC-CR-01: "只使用已验证的 Collection" — "已验证"依赖人工判断
DC-CR-02: "禁止 Append 整个 Scene" — 操作约束，非检查器检查范围
DC-CR-03: 五个具体角色名称 — 业务实例参数，通过 spec 传入
```

## 8. 明确排除范围

以下不在本轮确定的需求中：

```text
- Collection 内部对象结构验证（属于 Hierarchy 检查器）
- Collection 视觉外观
- 本字段组与 Hierarchy 的交互（各自独立）
- Collection 的可见性设置（属于 Visibility 检查器）
- 真实项目 .blend 验证
- Append 操作本身（检查器只读，不执行 Append）
- Link Collection vs Append Collection 的选择
- 角色库文件路径验证
```

## 9. 与现有锁定边界的兼容性

### 9.1 Root Object 解析（LOCKED）

```text
兼容: TRUE
方式: 必须复用已锁定 root 解析语义和前置结果。
Python 对象 identity 是重新解析、缓存传递还是由独立 helper 获得，
由设计根据当前生产代码真实结构决定。
不得为了 Collection Rules 修改 _check_root_objects()，
除非后续任务得到单独明确授权。

root 失败时的降级: 没有独立权威依据固定其行为，
应由 COLLECTION_RULES_DESIGN_R1 裁定。
```

### 9.2 Scene Membership（LOCKED）

```text
兼容: TRUE
方式: 不修改现有 scene membership 过滤机制。
新增读取: bpy.data.collections（不在 Scene.objects 中过滤）。

Scene Collection 范围由设计决定:
  - per-target 归属检查是否只接受当前目标 Scene Collection 树中的
    直接 Collection 和祖先 Collection；
  - 如果对象同时属于当前 Scene 内外的多个 Collection，
    当前 Scene 外的 required Collection 是否允许满足条件。
本轮只登记该缺口，不自行裁定。
```

### 9.3 Hierarchy Direct Children 和 Descendants（LOCKED）

```text
兼容: TRUE
层级关系和 Collection 成员关系是正交维度。
Collection Rules 不读取 object.children / object.parent。
```

### 9.4 per_target_results checks 结构（LOCKED）

```text
兼容: TRUE
方式: 在 checks 字典中新增独立键。
这属于独立扩展——每个已锁定字段组都以相同方式扩展了 checks 字典：
  standing → checks.standing
  facing → checks.facing
  visibility → checks.visibility
  rotation → checks.rotation
  animation_state → checks.animation_state
  material_assignment_presence_check → checks.material_assignment_presence_check
```

### 9.5 target overall 聚合（LOCKED）

```text
兼容: TRUE
方式: _recompute_target_overall() 通过扫描 checks.*.result 值实现，新增 key 自动纳入聚合
不需要修改聚合逻辑
```

### 9.6 global_results 现有结构（LOCKED）

```text
兼容: TRUE
方式: global_results 当前包含 scene_basic 键。
全局层结果可以新增独立键（候选名称由设计裁定），
已锁定内容（scene_basic）不受影响。
```

### 9.7 _collect_target_errors（LOCKED）

```text
兼容: TRUE
方式: 按照既有 ERROR collection 模式新增 Collection Rules 分支
不影响现有 ERROR 类型的收集
```

### 9.8 其他已锁定字段组

```text
兼容: 全部 TRUE
方式: Collection Rules 使用的 bpy.data.collections、obj.users_collection
和 collection.children 与任何已锁定字段组的数据路径没有交集：
  - Hierarchy: object.name, children, parent, type
  - Standing/Facing: matrix_world.to_3x3()
  - Visibility: hide_viewport, hide_render
  - Rotation: matrix_world.to_quaternion()
  - Animation State: animation_data, action, pose_position
  - Material Assignment: material_slots, slot.material
```

### 9.9 Scope Guard Implications

```text
NEW_BPY_ACCESS_REQUIRED:
  bpy.data.collections (全局，遍历所有 Collection 名称并解析)
  obj.users_collection (per-object，只返回直接 Collection)
  collection.children (仅用于从直接 Collection 向上构建祖先反向索引)

这些 API 在 14B_2A 锁定时全部标记为 ABSENT。
Collection Rules 实现需要自己的 Scope Guard (I4A/I5) 阶段，
保护对以上 API 的授权访问路径。
具体物化次数、缓存策略和异常边界留给设计。
```

## 10. 真正的合同冲突

```text
TRUE_CONTRACT_CONFLICTS: 0
```

经过逐项审核，没有发现两个或多个权威来源提出相互排斥、无法在同一实现中同时满足的要求。

输入收集报告将三个来源的粒度差异标注为候选冲突，经本轮审计确认属于以下分别归类：

| 候选 | 实际归类 |
|------|---------|
| 审计报告"全局规则，非 per-target" vs Schema/合同 | DOCUMENTATION_GAP（审计报告概括性简化不精确） |
| Schema 双字段 vs Impl Contract R2 单段描述 | DESIGN_FREEDOM（字段独立，不互斥） |
| 全局规则 vs per-target 结果 | TWO_COMPATIBLE_RULE_LAYERS（已裁定为互补层） |

## 11. 文档缺口

```text
DOC-GAP-01:
  LOCATION: GLOBAL_CODEIFICATION_AUDIT_REPORT.md 行 199
  DESCRIPTION: "collection_rules — 全局规则，非 per-target" 忽略了 per-target 成员关系检查
  CLASSIFICATION: DOCUMENTATION_ONLY_NON_BLOCKING
  IMPACT: 如不修正，可能导致后续设计遗漏 per-target 检查
  RECOMMENDATION: 设计阶段引用本审计报告而非仅依赖全局审计报告的概括标签

DOC-GAP-02:
  LOCATION: Schema (asset_scene_preflight_core.py)
  DESCRIPTION: schema 未定义字段缺失、null、空数组、仅 collection_rules 空对象和
    子字段分别启用时的顶层结果语义
  CLASSIFICATION: DEFER_TO_DESIGN
  IMPACT: 设计阶段必须决定每种状态的行为
  RECOMMENDATION: 在设计文档中统一裁定，不分散到多个位置

DOC-GAP-03:
  LOCATION: Implementation Contract R2 §3
  DESCRIPTION: 未定义 forbidden pattern 的大小写敏感性
  CLASSIFICATION: DEFER_TO_DESIGN
  IMPACT: 设计必须选择使用 casefold_glob_match 或精确大小写匹配

DOC-GAP-04:
  LOCATION: Implementation Contract R2 §3.3
  DESCRIPTION: per-target 成员关系遍历的具体算法未定义
  CLASSIFICATION: DEFER_TO_DESIGN
  IMPACT: 设计阶段需要定义：
    - object.users_collection 的直接 Collection 物化方式
    - child→parent 反向索引的构建方式（通过 collection.children）
    - 祖先闭包遍历终止条件
    - 重复 Collection 和防重复访问（visited identity 集合）
    - required 和 forbidden 同时满足时的优先级

DOC-GAP-05:
  LOCATION: 审计发现
  DESCRIPTION: Scene Collection 范围未定义——per-target 归属检查是否只接受
    当前目标 Scene Collection 树中的直接 Collection 和祖先 Collection；
    对象同时属于 Scene 内外多个 Collection 时，外部 required Collection 是否允许满足
  CLASSIFICATION: DEFER_TO_DESIGN
  IMPACT: 没有明确定义时，实现可能错误地在 Scene 外部 Collection 中查找
```

## 12. 设计自由

以下事项不存在权威裁决，属于设计阶段可以自行决定的范围：

```text
DF-CR-01: 全局检查结果的具体键名和结构
DF-CR-02: Per-target 检查结果的具体键名和结构
DF-CR-03: ERROR 操作的完整枚举和命名约定
DF-CR-04: casefold_glob_match vs 精确匹配的选择
DF-CR-05: 实现分阶段（I1-I4B-E）的具体范围切分
DF-CR-06: 全局和 per-target 检查的调用顺序
DF-CR-07: 缺失 collection 的命名（failure_code）
DF-CR-08: per_collection、missing-name、matched-name 或其他
          Collection 专用结果粒度
DF-CR-09: 字段缺失、null、空数组、仅 collection_rules 空对象和
          子字段分别启用时的顶层结果语义
DF-CR-10: root 前置失败后的结果状态
          (root 不存在、名称歧义、类型不匹配)
DF-CR-11: Scene Collection 范围裁定
          (Scene 外 Collection 是否允许满足归属条件)
DF-CR-12: 完成整体 EXIT_PASS/EXIT_FAIL/EXIT_ERROR 的汇总方式
DF-CR-13: 祖先反向索引的物化次数、缓存、排序和
          Scene master collection 是否纳入
DF-CR-14: 遍历终止、重复 Collection 和防重复访问的具体机制
```

## 13. 后续设计必须决定的事项

以下必须在 `COLLECTION_RULES_DESIGN_R1` 中裁定：

```text
DESIGN_MUST_DECIDE_01: 字段为空/缺失/null 时的行为
  - 空数组的语义
  - 字段缺失的语义
  - null 的语义
  - 仅 collection_rules 空对象 `{}` 的语义
  - 两个全局子字段分别启用时的顶层结果
  （以上统一在设计文档中一次裁定，不得分散。）

DESIGN_MUST_DECIDE_02: Per-target 祖先闭包遍历算法
  - object.users_collection 的直接 Collection 物化
  - collection.children 的 child→parent 反向索引构建
  - 从直接 Collection 向上计算祖先闭包
  - 遍历终止条件
  - visited identity 集合和防重复访问
  - Scene master collection 处理

DESIGN_MUST_DECIDE_03: forbidden 与 required 冲突时的优先级
  - root 属于 required 同时又属于 forbidden → 如何处理?
  - 两者同级（任何 FAIL 导致整体 FAIL）?

DESIGN_MUST_DECIDE_04: 检查结果字典
  - 全局结果的具体键和值结构
  - Per-target 结果的具体键和值结构
  - 与 canonicalization 预留字段的一致性

DESIGN_MUST_DECIDE_05: ERROR 操作枚举
  - 读取 bpy.data.collections 的操作
  - 解析 Collection 名称的操作
  - 读取 obj.users_collection 的操作
  - 读取 collection.children 的操作
  - 祖先闭包计算中的其他可能 ERROR 操作

DESIGN_MUST_DECIDE_06: Scope Guard 合约
  - 授权读取 bpy.data.collections 的唯一函数
  - 授权读取 obj.users_collection 的唯一函数
  - 授权读取 collection.children 的唯一函数

DESIGN_MUST_DECIDE_07: 字段命名
  - Per-target 字段使用 target.required_collection_names（现有）
  - 全局字段使用 collection_rules.required_collection_names（现有）
  - 避免新增 schema 字段（现有字段已覆盖）

DESIGN_MUST_DECIDE_08: Scene 范围
  - per-target 归属检查是否只接受当前目标 Scene 内的 Collection
  - Scene 外 required Collection 是否允许满足条件

DESIGN_MUST_DECIDE_09: root 前置失败的结果状态
  - root 不存在时的结果状态
  - root 名称歧义时的结果状态
  - root 类型不匹配时的结果状态
```

## 14. 最终审计结论

```text
AUDIT_RESULT: REQUIREMENTS_SUFFICIENT_FOR_DESIGN
TRUE_CONTRACT_CONFLICTS: 0
DOCUMENTATION_GAP_COUNT: 5
DESIGN_FREEDOM_COUNT: 14
DESIGN_MUST_DECIDE_COUNT: 9
DESIGN_AUTHORIZED_BY_AUDIT: TRUE
NEXT_RECOMMENDED_TASK: COLLECTION_RULES_DESIGN_R1
```

### 判定依据

**全局规则**：原始需求（交接文档 v4）要求验证 Collection 存在性；Implementation Contract R2 §3.1-§3.2 定义了精确算法（`bpy.data.collections.get()` + glob matching）；14A schema 已定义字段结构。以下是合同确定的：名称缺失 → FAIL，glob 命中 → FAIL，大小写敏感匹配，五个名称不硬编码。

**Per-target 规则**：原始需求（L1-A）要求验证"Collection 与对象存在性"；Implementation Contract R2 §3.3 定义了对象归属检查；14A schema 已定义 `targets[i].required_collection_names` 字段。以下是合同确定的：检查 root 是否属于至少一个 required collection，范围包括直接 Collection 加递归祖先闭包。

**两层关系**：每个来源同时描述了全局层和 per-target 层。没有任何权威来源要求两层互斥。Schema 和 Implementation Contract R2 都支持两者共存。历史审计报告的概括性简化（"全局规则，非 per-target"）不构成权威冲突。归类为 `TWO_COMPATIBLE_RULE_LAYERS`。

**锁定边界兼容性**：所有已锁定边界（root 解析、scene membership、hierarchy、per_target_results、overall 聚合、global_results、ERROR collection、其他字段组）全部兼容。Collection Rules 需要新增对 `bpy.data.collections`、`obj.users_collection` 和 `collection.children` 的访问，但这属于 Scope Guard 阶段需要处理的独立扩展——不影响任何已锁定的代码路径。root 解析必须复用已锁定语义，不得修改 `_check_root_objects()`。

**需求闭环**：
- 为什么需要全局检查：原始需求要求"五个角色 Collection 存在"，Impl Contract R2 定义了 `bpy.data.collections.get()` 算法
- 为什么需要 per-target 检查：原始需求要求检查"Collection 与对象存在性"，Impl Contract R2 定义了对象归属检查
- 分别读取什么 Blender 数据：全局 → `bpy.data.collections`；per-target → `obj.users_collection` + `collection.children` 反向索引
- 是否独立启用：是——全局字段缺失时全局检查不执行，per-target 字段缺失时 per-target 检查不执行
- 分别代表什么客观问题：全局 FAIL → 要求的 Collection 在 .blend 中不存在；per-target FAIL → target root object 不属于任何要求的 Collection
- 可代码化内容：四个代码化需求（CE-CR-01 到 04）
- 留给设计阶段：14 个设计自由 + 9 个设计必须决定的事项
- 明确排除：Collection 内部结构、视觉外观、可见性、Append 操作、Link vs Append 选择、文件路径验证
