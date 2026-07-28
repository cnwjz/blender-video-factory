# Collection Rules 设计审计输入收集报告

```text
TASK_ID: COLLECTION_RULES_DESIGN_AUDIT_INPUT_COLLECTION
MASTER_MAP_VERSION: R70
REPORT_DATE: 2026-07-25
```

## 1. 实际读取的文件

| # | 文件路径 | 类型 |
|---|---------|------|
| 1 | `reviews/PROJECT_CODEIFICATION_MASTER_MAP.md` (R70) | 总地图 |
| 2 | `CLAUDE.md` (项目根) | 项目规则 |
| 3 | `GLOBAL_CODEIFICATION_AUDIT_INPUTS/01_authoritative_requirements/Blender_固定资产模板路线_新对话交接文档_v4.md` | 权威需求 |
| 4 | `GLOBAL_CODEIFICATION_AUDIT_INPUTS/02_phase3_design/PHASE_3_MINIMUM_DESIGN_SPEC_R1.md` | 设计规格 |
| 5 | `GLOBAL_CODEIFICATION_AUDIT_INPUTS/02_phase3_design/ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md` | 实现合同 |
| 6 | `protocol_guard/phase3_min/asset_scene_preflight_core.py` | 14A 核心 |
| 7 | `protocol_guard/phase3_min/asset_scene_preflight_check.py` | 检查器入口 |
| 8 | `protocol_guard/phase3_min/blender_scene_reader.py` | Blender 读取器 |
| 9 | `protocol_guard/phase3_min/tests/test_asset_scene_preflight_core.py` | 14A 测试 |
| 10 | `reviews/GLOBAL_CODEIFICATION_AUDIT_REPORT.md` | 全局审计 |
| 11 | `reviews/POST_14B_3B_GLOBAL_REMAINING_REQUIREMENTS_AUDIT_R1_REPORT.md` | 剩余需求审计 |
| 12 | `reviews/PHASE_3_CURRENT_IMPLEMENTATION_COVERAGE_AUDIT.md` | 实现覆盖审计 |
| 13 | `reviews/PHASE_3_CURRENT_IMPLEMENTATION_COVERAGE_AUDIT.json` | 覆盖审计 JSON |
| 14 | `GLOBAL_CODEIFICATION_AUDIT_INPUTS/03_locked_stage_evidence/14B_2A_SCOPE_GIT_AND_LOCK_EVIDENCE.txt` | 范围锁定证据 |
| 15 | `GLOBAL_CODEIFICATION_AUDIT_INPUTS/03_locked_stage_evidence/14B_2C_FINAL_REVIEW_REPORT.md` | 14B-2C 最终审核 |
| 16 | `reviews/14B_3B_FACING_DESIGN_R1.md` | Facing 设计 (交叉引用) |
| 17 | `reviews/14B_4A_VISIBILITY_DESIGN_R1.md` | Visibility 设计 (交叉引用) |
| 18 | `reviews/14B_4A_VISIBILITY_FORMAL_LOCK_RECORD.md` | Visibility 锁定记录 (交叉引用) |

## 2. 原始需求材料原文位置与摘要

### 2.1 Blender 固定资产模板路线 新对话交接文档 v4

**§2 已包含角色** (行 655-661):
```text
Collection: CHR_MALE_A
Collection: CHR_MALE_B
Collection: CHR_FEMALE_A
Collection: CHR_FEMALE_B
Collection: CHR_EMPLOYEE
```

**§3 已确认状态** (行 665-672):
- "每个角色独立 Collection，已通过三视图验证"
- "后续禁止从原始 FBX 重复导入这五个角色"
- "后续禁止修改库内角色原始结构"

**§5 使用方式** (行 691-698):
- "推荐使用 Append Collection"
- "后续模板稳定后再评估 Link Collection"

**§6 使用规则** (行 702-704):
- "只 Append 已验证 Collection"
- "禁止 Append 整个 Scene"

**§7 角色库预检** (行 714-723):
- "五个角色 Collection 存在" (检查项 2)

**L1-A 指令** (行 1353-1394):
- 五个固定角色 Collection 在新场景中稳定 Append 并保持已验证状态
- 六个角色实例：CHR_MALE_A→Customer_01_Root, CHR_FEMALE_A→Customer_02_Root, CHR_MALE_B→Customer_03_Root, CHR_FEMALE_B→Customer_04_Root, CHR_EMPLOYEE→Employee_01_Root, CHR_EMPLOYEE→Employee_02_Root
- "只允许重命名 Append 后的顶层 Collection 或已验证 Root 实例"
- 检查要求包含 "Collection 与对象存在性"

**摘要**: 原始需求要求验证五个固定角色 Collection 存在，以及 Append 后的 Collection 和对象存在性。这是全局层级（bpy.data.collections）的检查需求，也涉及 per-target 的对象在 Collection 中的成员关系。

### 2.2 ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md

**§3 Collection Contract** (行 73-91):
```json
"collection_rules": {
  "required_collection_names": ["CHR_MALE_A", "CHR_MALE_B"],
  "forbidden_collection_name_patterns": []
}
```

算法定义:
1. `required_collection_names`: 对每个名称，`bpy.data.collections.get(name)` 必须返回非 None Collection。缺失 → FAIL。
2. `forbidden_collection_name_patterns`: Glob 模式。任何名称匹配的 Collection → FAIL。
3. Target-to-collection 链接: 使用 `object.users_collection` 遍历对象的间接成员链。检查 target 的 root object 是否（直接或通过递归父子 collection 成员关系）属于至少一个 required collection。
4. Collection 存在性与对象层级独立。Collection 可以存在但包含零个对象；Collection 可以通过中间 collection 链接包含 target 的 root object。两种场景均有效，只要 spec 的 required collections 存在。

**摘要**: 这是最接近设计文档的材料，但并非正式锁定的设计文档。定义了核心数据源（bpy.data.collections, users_collection）和两级检查（Collection 存在性 + Target 成员关系）。

### 2.3 PHASE_3_MINIMUM_DESIGN_SPEC_R1.md

**§10.1 Integration Validation** (行 526-528):
- "Run against the 5 character collections in character_library_v1.blend"
- 集成验证计划中提到需要验证 5 个角色 PASS

### 2.4 全局审计和实现覆盖报告

**GLOBAL_CODEIFICATION_AUDIT_REPORT.md** (行 180):
- "collection_rules（collection 存在性 + 禁制）" — 归类为中复杂度
- 标注为"全局规则，非 per-target"

**PHASE_3_CURRENT_IMPLEMENTATION_COVERAGE_AUDIT.json** (行 28):
```json
"collection_rules": {
  "status": "CORE_VALIDATION_ONLY",
  "production": "NOT IN READER",
  "tests": "core.py (schema validation only)",
  "blender_tests": 0,
  "cpython_tests": 0
}
```

**POST_14B_3B_GLOBAL_REMAINING_REQUIREMENTS_AUDIT_R1_REPORT.md** (行 45):
| 5 | collection_rules | SCHEMA_ONLY | Medium | bpy.data.collections, users_collection |

## 3. 当前 14A Schema 精确字段路径

### 3.1 全局层: `collection_rules` (OPTIONAL)

位置: spec 根级

```json
"collection_rules": {
  "required_collection_names": ["<non-empty-string>"],
  "forbidden_collection_name_patterns": ["<string>"]
}
```

| 字段路径 | 类型 | 必填 | 允许值 |
|---------|------|------|--------|
| `collection_rules` | object 或 null | 否 | — |
| `collection_rules.required_collection_names` | array[string] | 否 (字段可选，存在则必须是 array) | 非空字符串 |
| `collection_rules.forbidden_collection_name_patterns` | array[string] | 否 (字段可选，存在则必须是 array) | 任意字符串 |

验证代码位置: [asset_scene_preflight_core.py:202-221](protocol_guard/phase3_min/asset_scene_preflight_core.py#L202-L221)

### 3.2 Per-Target 层: `targets[i].required_collection_names` (OPTIONAL)

| 字段路径 | 类型 | 必填 | 允许值 |
|---------|------|------|--------|
| `targets[i].required_collection_names` | array[string] | 否 | 非空字符串 |

验证代码位置: [asset_scene_preflight_core.py:411-419](protocol_guard/phase3_min/asset_scene_preflight_core.py#L411-L419)

### 3.3 字段关系

- 全局 `collection_rules` 和 per-target `targets[i].required_collection_names` 是**两个独立字段**，14A schema 对它们独立验证。
- 14A schema 不定义它们之间的语义关系（互斥、互补、覆盖等）。
- 当前测试只覆盖全局 schema 验证（`test_collection_rules_valid`），不覆盖 per-target 字段。

## 4. 当前运行时状态

### 4.1 生产实现

```text
EXISTS_IN_BLENDER_SCENE_READER: FALSE
```

在 `blender_scene_reader.py` 中不存在任何 `_check_collection_rules` 或类似函数。

`open_blend_and_get_scene()` 当前合并循环（行 1993-2011）只调用:
1. `_check_animation_state`
2. `_check_material_assignment`
3. `_recompute_target_overall`

不包含 Collection Rules 调用。

### 4.2 入口集成

```text
INTEGRATED_IN_OPEN_BLEND_AND_GET_SCENE: FALSE
INTEGRATED_IN_COLLECT_TARGET_ERRORS: FALSE
```

`_collect_target_errors()` 没有 Collection Rules 分支。

### 4.3 专项测试

```text
DEDICATED_COLLECTION_RULES_TEST_FILE: NONE
```

唯一相关测试是 `test_asset_scene_preflight_core.py` 中的:
- `TestSpecValidation::test_collection_rules_valid` (行 346-351) — 只验证 schema 接受有效配置

### 4.4 旧报告与旧设计

```text
COLLECTION_RULES_DESIGN_R1.md: DOES_NOT_EXIST
COLLECTION_RULES_DESIGN_LOCK_RECORD.md: DOES_NOT_EXIST
COLLECTION_RULES_FORMAL_LOCK_RECORD.md: DOES_NOT_EXIST
```

- `ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md` §3 包含算法大纲，但这**不是**正式锁定的字段组设计文档。
- 在多个其他字段组的设计文档中被列为 "out of scope" 或 "deferred"（参见 Facing Design R1、Visibility Design R1、Visibility Lock Record）。

### 4.5 主地图状态

```text
COLLECTION_RULES: NOT_STARTED_RUNTIME (R70 §十五)
状态: SCHEMA_ONLY (R70 §六 表)
复杂度: 中
主要读取: bpy.data.collections、users_collection
```

## 5. 既有锁定边界

### 5.1 Scene Membership (LOCKED)

`blender_scene_reader.py` 中已锁定的 scene membership 过滤机制：
- `_check_root_objects()`: 使用 `scene.objects` 遍历 + 名称匹配
- `_check_direct_children()`: `scene.objects` 成员过滤 + Python identity
- `_collect_descendants()`: `scene.objects` 成员过滤 + Python identity + 循环检测
- `_collect_geometry_scope_objects()`: `scene_member_ids` 预计算 + identity 过滤

**影响**: Collection Rules 的 `object.users_collection` 遍历可能需要在 scene membership 语境下判断，与已锁定的 scene membership 机制交互。

### 5.2 Hierarchy (LOCKED)

`_check_direct_children()` 和 `_check_descendants()` 已锁定。

**影响**: 不直接冲突。Collection Rules 检查的是 collection 成员关系，而非父子层级关系。

### 5.3 Root 和 Descendant 语义 (LOCKED)

Root object 解析、类型匹配和 ambiguous name 检测已锁定。

**影响**: Collection Rules 的 target-to-collection 关联需要使用已锁定的 root object 身份。如果 Collection Rules 需要遍历 `users_collection` 链，可能涉及 root object 的 collection 成员关系检查。

### 5.4 14B_2A Scope Guard Boundaries

从 14B_2A 范围锁定证据:
```text
users_collection: ABSENT (PASS)
bpy.data.collections: ABSENT (PASS)
```

这两个属性在 Hierarchy 锁定时在生产代码中不存在。**Collection Rules 将是首次在生产代码中访问 `bpy.data.collections` 和 `users_collection`。**

这意味着:
- 需要新的 Scope Guard (I4A/I5) 来保护这些 Blender API 访问
- 需要在 `blender_scene_reader.py` 中定义授权读取函数

### 5.5 per_target_results 结构 (LOCKED)

每个 target result 的 `checks` 字典结构、`overall` 重算和 `_collect_target_errors` 收集器已锁定。

**影响**: Collection Rules 需要遵循既有的 checks 字典结构和 overall 聚合语义。

### 5.6 全局结果 global_results (LOCKED)

`global_results` 当前只有 `scene_basic` 子键。Collection Rules 作为全局规则，可能需要在 `global_results` 中新增键。

### 5.7 其他已锁定字段组

已锁定的字段组（Hierarchy, Standing, Facing, Visibility, Rotation, Animation State, Material Assignment）都不依赖 `bpy.data.collections` 或 `users_collection`。Collection Rules 是新数据源，不与已锁定字段组共享数据路径。

## 6. 候选不一致与文档缺口

### 6.1 全局 vs Per-Target 语义未定义

**位置**: schema 有 `collection_rules`（全局）和 `targets[i].required_collection_names`（per-target）两个独立字段。

**问题**: 原始需求（交接文档 v4）提到 Collection 存在性属于全局层面（"五个角色 Collection 存在"），但 Implementation Contract R2 §3 只定义了全局 `collection_rules` 的算法。Per-target 字段在 schema 中存在但没有任何设计文档或算法定义。

**分类**: DOCUMENTATION_GAP — 需要在设计阶段裁定。

### 6.2 Target-to-Collection 链接算法未精确化

**位置**: Implementation Contract R2 行 88。

**问题**: "does the target's root object belong to at least one of the required collections" — 这个检查的 PASS/FAIL 语义不精确：
- root object 不属于任何 required collection → FAIL？
- root object 属于 forbidden collection → FAIL？
- root object 属于 required collection 但同时也属于 forbidden collection → ?

**分类**: UNDEFINED_SEMANTICS — 需要在设计阶段裁定。

### 6.3 全局规则 vs Per-Target 结果的输出结构

**位置**: 全局审计报告描述 "collection_rules — 全局规则，非 per-target"。

**问题**: 如果 collection_rules 是全局规则，其结果应该放在 `global_results` 而非 `per_target_results`。但目前没有任何字段组在 `global_results` 中（除了 `scene_basic`）。输出结构需要在设计中确定。

**分类**: UNDEFINED_SEMANTICS — 需要在设计阶段裁定。

### 6.4 预缓存 fields 暗示未实现结果

**位置**: [asset_scene_preflight_core.py:573-578](protocol_guard/phase3_min/asset_scene_preflight_core.py#L573-L578)

`_NAME_LIST_WHITELIST` 已包含:
```python
"missing_required_collections",
"missing_required_collection_names",
"forbidden_collection_matches",
```

这些是 canonicalization 层预缓存的字段名，暗示预期的结果字典结构。但从未有生产代码产出这些字段。

**分类**: 设计预留 — 不阻塞，但表明此前已有非正式设计预期。

### 6.5 缺少正式锁定设计文档

与其他已锁定字段组不同，Collection Rules 没有以下任一文档：
- `COLLECTION_RULES_DESIGN_R1.md`
- `COLLECTION_RULES_DESIGN_LOCK_RECORD.md`
- `COLLECTION_RULES_FORMAL_LOCK_RECORD.md`

Implementation Contract R2 §3 提供了算法大纲，但不是字段组级设计文档。其范围覆盖整个检查器，未包含:
- 完整 ERROR 操作枚举
- 结果字典键集
- 与 per-target 字段的交互规范
- Scope Guard 合约

**分类**: MISSING_DESIGN_ARTIFACT — 需要在设计前创建。

### 6.6 文档对 Collection Rules 范围的矛盾描述

| 来源 | 描述 |
|------|------|
| GLOBAL_CODEIFICATION_AUDIT_REPORT.md | "全局规则，非 per-target" |
| ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md §3 | 同时描述了全局 collection 存在性检查和 per-target `users_collection` 遍历 |
| 14A Schema | 同时有全局 `collection_rules` 和 per-target `required_collection_names` |

三个来源对范围的描述不一致。

**分类**: CONTRACT_CONFLICT — 需要在原始需求审计中裁决。

## 7. 后续原始需求审计需要回答的问题

1. Collection Rules 是纯全局规则、纯 per-target 规则，还是两者混合？
2. `collection_rules` 和 `targets[i].required_collection_names` 的语义关系是什么（互斥、互补、覆盖、独立）？
3. Collection 存在性检查是否只需要检查 `bpy.data.collections.get(name) is not None`？
4. Forbidden pattern 匹配范围是全局 `bpy.data.collections` 中的所有 collection，还是仅 target 所属的 collections？
5. Target-to-collection 成员关系检查需要遍历多深（仅 root object 的直接 users_collection，还是递归父级 collection）？
6. 如果 root object 同时属于 required 和 forbidden collection，哪个优先？
7. 检查输出应该放在 `global_results`、`per_target_results` 还是两者兼有？
8. 完整的 ERROR 操作有哪些（例如 READ_COLLECTION_LIST, RESOLVE_COLLECTION, READ_USERS_COLLECTION 等）？
9. 是否需要 per-collection 粒度结果，类似于 Material Assignment 的 per_mesh？
10. 原始需求"五个角色 Collection 存在" — 这是示例还是硬性要求？是否应该参数化为 spec 字段？

## 8. 输入充分性结论

```text
INPUT_SUFFICIENT_FOR_ORIGINAL_REQUIREMENT_AUDIT: TRUE
```

**理由**:
- 权威原始需求文档（Blender 交接文档 v4）已包含 Collection 相关的业务要求
- 14A schema 源码完整定义了 Collection Rules 字段结构
- Implementation Contract R2 §3 提供了算法大纲和核心数据源
- 既有锁定边界明确记录了 `bpy.data.collections` 和 `users_collection` 在层次锁定时不存在
- 已知文档缺口和冲突点已在本报告中记录

**未阻断原因**: 缺失的是设计裁定级别的信息（全局 vs per-target、精确算法、输出结构），这些应该在原始需求审计中裁决，而不是在输入收集阶段阻断。

## 9. 阻断审计的具体缺失项

```text
MISSING_BLOCKING_INPUTS: NONE
```

所有必要输入均已可访问。没有阻止原始需求审计的关键文件缺失。

以下为"存在但不完整"的项（不阻断）:
- 缺少正式锁定设计文档 (COLLECTION_RULES_DESIGN_R1.md) — 这是本轮需要产出的设计前序步骤
- 缺少 Scope Guard 合约 — 应在设计阶段定义
- 缺少专项测试文件 — 应在实现阶段创建
