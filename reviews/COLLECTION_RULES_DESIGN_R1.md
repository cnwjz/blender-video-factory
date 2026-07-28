# Collection Rules Runtime Design R1

```text
DOCUMENT_ID: COLLECTION_RULES_DESIGN
DESIGN_VERSION: R1
TASK_ID: COLLECTION_RULES_DESIGN_R1
MASTER_MAP_VERSION: R70
DATE: 2026-07-25
DESIGN_STATUS: COMPLETED_PENDING_INDEPENDENT_CHECK
FORMALLY_LOCKED: FALSE
IMPLEMENTATION_AUTHORIZED: FALSE
```

## 1. 权威来源与优先级

```text
PRIORITY_1: Blender_固定资产模板路线_新对话交接文档_v4.md
  — AUTHORITATIVE_REQUIREMENT: "五个角色 Collection 存在" (§7.2),
    "Collection 与对象存在性" (L1-A §1)

PRIORITY_2: ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md §3
  — AUTHORITATIVE_REQUIREMENT: bpy.data.collections.get(), glob matching,
    object.users_collection, recursive ancestor closure,
    at-least-one required collection satisfaction

PRIORITY_3: asset_scene_preflight_core.py L202-221, L411-419
  — LOCKED_SCHEMA: collection_rules (global optional dict),
    targets[i].required_collection_names (per-target optional array)

PRIORITY_4: PROJECT_CODEIFICATION_MASTER_MAP.md R70
  — CURRENT_STATE: COLLECTION_RULES: NOT_STARTED_RUNTIME (SCHEMA_ONLY)

PRIORITY_5: CLAUDE.md
  — PROJECT_RULES

DESIGN_INPUT:
  — COLLECTION_RULES_ORIGINAL_REQUIREMENT_AUDIT_REPORT.md (R2 Correction)
    AUDIT_RESULT: REQUIREMENTS_SUFFICIENT_FOR_DESIGN
    TRUE_CONTRACT_CONFLICTS: 0
    RULE_LAYER_RELATION: TWO_COMPATIBLE_RULE_LAYERS
    DESIGN_FREEDOM_COUNT: 14
    DESIGN_MUST_DECIDE_COUNT: 9

REFERENCE_CONVENTION:
  — MATERIAL_ASSIGNMENT_DESIGN_R1.md (result structure, ERROR mapping,
    read count table, cache contract, integration pattern, scope guard contract)
  — ANIMATION_STATE_DESIGN_R5.md (independent per-target check integration,
    sub-key existence model, scope guard conventions)
```

## 2. 固定范围和明确排除项

```text
FIXED_SCOPE:
  — 全局层: collection_rules.required_collection_names
  — 全局层: collection_rules.forbidden_collection_name_patterns
  — Per-target 层: targets[i].required_collection_names
  — 全局结果键名: collection_rules (在 global_results 下)
  — Per-target 结果键名: collection_membership (在 checks 下)
  — 两层独立启用、独立输出

EXPLICITLY_EXCLUDED:
  — Collection 内部对象结构验证（属于 Hierarchy）
  — Collection 视觉外观
  — Collection 可见性设置（属于 Visibility）
  — 真实项目 .blend 验证
  — Append / Link 操作
  — 角色库文件路径验证
  — 保存重开后的 Collection 持久化

MUST_NOT_MODIFY:
  — 14A Core schema (asset_scene_preflight_core.py)
  — _check_root_objects() 的现有行为和返回结构
  — Hierarchy, Standing, Facing, Visibility, Rotation,
    Animation State, Material Assignment 的生产代码和测试
  — 任何已锁定设计或锁定记录
  — global_results.scene_basic 的现有结构
  — _recompute_target_overall() 的聚合逻辑
```

## 3. 两层配置和启用语义

### 3.1 全局层: collection_rules

严格按以下优先级判定：

```text
Step G1: spec 中 collection_rules 字段缺失或为 None
  → 全局不启用
  → global_results 不创建 collection_rules 键
  → 不读取 bpy 数据
  → 不影响整体退出状态

Step G2: collection_rules 为非空 dict
  → 在 global_results 中创建 "collection_rules" 键
  → 评估 required_collection_names 子字段 (G3)
  → 评估 forbidden_collection_name_patterns 子字段 (G4)

Step G3: required_collection_names 子字段
  → 字段缺失 → NOT_CHECKED, note: "REQUIRED_COLLECTION_NAMES_NOT_CONFIGURED"
  → 为 null → NOT_CHECKED, note: "REQUIRED_COLLECTION_NAMES_NOT_CONFIGURED"
  → 为空数组 [] → NOT_CHECKED, note: "REQUIRED_COLLECTION_NAMES_NOT_CONFIGURED"
  → 为非空数组 → 执行全局 required 检查 (§9)
  → 所有 NOT_CHECKED 路径不读取 bpy 数据

Step G4: forbidden_collection_name_patterns 子字段
  → 字段缺失 → NOT_CHECKED, note: "FORBIDDEN_COLLECTION_NAME_PATTERNS_NOT_CONFIGURED"
  → 为 null → NOT_CHECKED, note: "FORBIDDEN_COLLECTION_NAME_PATTERNS_NOT_CONFIGURED"
  → 为空数组 [] → NOT_CHECKED, note: "FORBIDDEN_COLLECTION_NAME_PATTERNS_NOT_CONFIGURED"
  → 为非空数组 → 执行全局 forbidden 检查 (§9)
  → 所有 NOT_CHECKED 路径不读取 bpy 数据

Step G5: collection_rules 为空对象 {}
  → 创建 collection_rules 键
  → required → NOT_CHECKED (G3 字段缺失)
  → forbidden → NOT_CHECKED (G4 字段缺失)
  → 不读取 bpy 数据
```

### 3.2 配置语义表 — 全局层

| 配置状态 | required 行为 | forbidden 行为 | 读取 bpy 数据 |
|----------|-------------|---------------|-------------|
| collection_rules 缺失 | 不创建键 | 不创建键 | 否 |
| collection_rules: null | 不创建键 | 不创建键 | 否 |
| collection_rules: {} | NOT_CHECKED | NOT_CHECKED | 否 |
| required_collection_names 缺失 | NOT_CHECKED | 按 G4 | 仅当 forbidden 启用 |
| required_collection_names: null | NOT_CHECKED | 按 G4 | 仅当 forbidden 启用 |
| required_collection_names: [] | NOT_CHECKED | 按 G4 | 仅当 forbidden 启用 |
| required_collection_names: ["A"] | 执行检查 | 按 G4 | 是 |
| forbidden_collection_name_patterns 缺失 | 按 G3 | NOT_CHECKED | 仅当 required 启用 |
| forbidden_collection_name_patterns: null | 按 G3 | NOT_CHECKED | 仅当 required 启用 |
| forbidden_collection_name_patterns: [] | 按 G3 | NOT_CHECKED | 仅当 required 启用 |
| forbidden_collection_name_patterns: ["*test*"] | 按 G3 | 执行检查 | 是 |

### 3.3 Per-target 层: targets[i].required_collection_names

```text
Step P1: target 中 required_collection_names 字段缺失
  → NOT_CHECKED
  → note: "REQUIRED_COLLECTION_NAMES_NOT_CONFIGURED"
  → 不读取任何 bpy 数据，不检查 root 前置条件

Step P2: required_collection_names 为 null
  → NOT_CHECKED
  → note: "REQUIRED_COLLECTION_NAMES_NOT_CONFIGURED"
  → 不读取任何 bpy 数据，不检查 root 前置条件

Step P3: required_collection_names 为空数组 []
  → NOT_CHECKED
  → note: "REQUIRED_COLLECTION_NAMES_NOT_CONFIGURED"
  → 不读取任何 bpy 数据，不检查 root 前置条件

Step P4: required_collection_names 为非空数组
  → 检查 root 前置条件 (§11)
  → root 前置不满足 → NOT_CHECKED（相应 note）
  → root 前置满足 → 执行 per-target 检查 (§10)
```

### 3.4 配置语义表 — Per-target 层

| 配置状态 | 结果 | note |
|---------|------|------|
| required_collection_names 缺失 | NOT_CHECKED | REQUIRED_COLLECTION_NAMES_NOT_CONFIGURED |
| required_collection_names: null | NOT_CHECKED | REQUIRED_COLLECTION_NAMES_NOT_CONFIGURED |
| required_collection_names: [] | NOT_CHECKED | REQUIRED_COLLECTION_NAMES_NOT_CONFIGURED |
| required_collection_names: ["A"] | 进入 root 前置检查 | — |

## 4. 全局结果结构

### 4.1 键名

```text
GLOBAL_RESULTS_KEY: "collection_rules"
PARENT: global_results 顶级键
```

### 4.2 结构

```python
# 全局 NOT_CHECKED (collection_rules 为空或只有未配置子字段)
{
    "global_results": {
        "scene_basic": { ... },  # 不受影响
        "collection_rules": {
            "result": "NOT_CHECKED",
            "required": {
                "result": "NOT_CHECKED",
                "note": "REQUIRED_COLLECTION_NAMES_NOT_CONFIGURED"
            },
            "forbidden": {
                "result": "NOT_CHECKED",
                "note": "FORBIDDEN_COLLECTION_NAME_PATTERNS_NOT_CONFIGURED"
            }
        }
    }
}

# 全局 PASS (两个子检查均 PASS 或一个 PASS + 一个 NOT_CHECKED)
{
    "global_results": {
        "collection_rules": {
            "result": "PASS",
            "required": {
                "result": "PASS",
                "required_names": ["CHR_MALE_A", "CHR_MALE_B"],
                "missing_names": []
            },
            "forbidden": {
                "result": "PASS",
                "forbidden_patterns": ["*test*"],
                "matched_collections": []
            }
        }
    }
}

# 全局 FAIL (至少一个子检查 FAIL)
{
    "global_results": {
        "collection_rules": {
            "result": "FAIL",
            "failure_code": "COLLECTION_RULES_FAILURE",
            "required": {
                "result": "FAIL",
                "failure_code": "REQUIRED_COLLECTION_MISSING",
                "required_names": ["CHR_MALE_A", "CHR_MALE_B"],
                "missing_names": ["CHR_MALE_B"]
            },
            "forbidden": {
                "result": "PASS",
                "forbidden_patterns": ["*test*"],
                "matched_collections": []
            }
        }
    }
}

# 全局 ERROR (任一 bpy 读取异常)
{
    "global_results": {
        "collection_rules": {
            "result": "ERROR",
            "error_type": "COLLECTION_RULES_COMPUTATION_ERROR",
            "operation": "MATERIALIZE_BPY_DATA_COLLECTIONS",
            "note": "MATERIALIZE_BPY_DATA_COLLECTIONS_FAILED",
            "required": {
                "result": "NOT_CHECKED",
                "note": "GLOBAL_ERROR_SHORT_CIRCUIT"
            },
            "forbidden": {
                "result": "NOT_CHECKED",
                "note": "GLOBAL_ERROR_SHORT_CIRCUIT"
            }
        }
    }
}
```

### 4.3 聚合规则

```text
顶层 result:
  ERROR > FAIL > PASS > NOT_CHECKED

两个子检查独立聚合:
  required.result: 独立评定
  forbidden.result: 独立评定
  顶层 = max(required.result, forbidden.result) 按 ERROR > FAIL > PASS > NOT_CHECKED
```

### 4.4 精确键集合

```text
GLOBAL_TOP_LEVEL_KEYS:
  NOT_CHECKED (两个子检查均 NOT_CHECKED): ["result", "required", "forbidden"]
  PASS:    ["result", "required", "forbidden"]
  FAIL:    ["result", "failure_code", "required", "forbidden"]
  ERROR:   ["result", "error_type", "operation", "note", "required", "forbidden"]

REQUIRED_SUB_KEYS:
  NOT_CHECKED: ["result", "note"]
  PASS:    ["result", "required_names", "missing_names"]
  FAIL:    ["result", "failure_code", "required_names", "missing_names"]

FORBIDDEN_SUB_KEYS:
  NOT_CHECKED: ["result", "note"]
  PASS:    ["result", "forbidden_patterns", "matched_collections"]
  FAIL:    ["result", "failure_code", "forbidden_patterns", "matched_collections"]

SORTING:
  required_names: 按 casefold 排序
  missing_names: 按 casefold 排序
  forbidden_patterns: 去重后按 casefold 排序
  matched_collections: 按 casefold 排序
```

### 4.5 Canonicalization 复用

使用已存在的 `_NAME_LIST_WHITELIST` 预留字段：

```text
missing_required_collections  → 全局 required 子检查的 missing_names
forbidden_collection_matches  → 全局 forbidden 子检查的 matched_collections
```

这些字段已在 `_NAME_LIST_WHITELIST` 中注册，按 `_is_unordered_name_field` 规则自动排序。

## 5. Per-target 结果结构

### 5.1 键名

```text
CHECKS_KEY: "collection_membership"
PARENT: per_target_results[i].checks 顶级键
```

### 5.2 结构

```python
# Per-target NOT_CHECKED (配置未启用或 root 前置失败)
{
    "result": "NOT_CHECKED",
    "note": "REQUIRED_COLLECTION_NAMES_NOT_CONFIGURED"
}
{
    "result": "NOT_CHECKED",
    "note": "ROOT_OBJECT_NOT_FOUND"
}
{
    "result": "NOT_CHECKED",
    "note": "AMBIGUOUS_ROOT_OBJECT_NAME"
}
{
    "result": "NOT_CHECKED",
    "note": "ROOT_OBJECT_TYPE_MISMATCH"
}

# Per-target PASS (root 属于至少一个 required collection)
{
    "result": "PASS",
    "required_names": ["CHR_MALE_A"],
    "direct_collections": ["CHR_MALE_A"],
    "ancestor_collections": ["Characters"],
    "matched_names": ["CHR_MALE_A"],
    "missing_names": []
}

# Per-target FAIL (root 不属于任何 required collection)
{
    "result": "FAIL",
    "failure_code": "TARGET_NOT_IN_REQUIRED_COLLECTION",
    "required_names": ["CHR_MALE_A", "CHR_MALE_B"],
    "direct_collections": ["OtherCollection"],
    "ancestor_collections": [],
    "matched_names": [],
    "missing_names": ["CHR_MALE_A", "CHR_MALE_B"]
}

# Per-target ERROR (bpy 读取异常)
{
    "result": "ERROR",
    "error_type": "COLLECTION_RULES_COMPUTATION_ERROR",
    "operation": "READ_ROOT_USERS_COLLECTION",
    "note": "READ_ROOT_USERS_COLLECTION_FAILED"
}
```

### 5.3 精确键集合

```text
PER_TARGET_KEYS:
  NOT_CHECKED:                   ["result", "note"]
  PASS:                          ["result", "required_names", "direct_collections",
                                  "ancestor_collections", "matched_names", "missing_names"]
  FAIL:                          ["result", "failure_code", "required_names",
                                  "direct_collections", "ancestor_collections",
                                  "matched_names", "missing_names"]
  ERROR (root-level):            ["result", "error_type", "operation", "note"]
  ERROR (ancestor-closure):      ["result", "error_type", "operation", "note",
                                  "collection_name"]

SORTING:
  required_names: 按 casefold 排序
  direct_collections: 按 casefold 排序
  ancestor_collections: 按 casefold 排序
  matched_names: 按 casefold 排序
  missing_names: 按 casefold 排序
```

### 5.4 Canonicalization 复用

使用已存在的 `_NAME_LIST_WHITELIST` 预留字段：

```text
missing_required_collection_names → per-target 的 missing_names
```

该字段已在 `_NAME_LIST_WHITELIST` 中注册，按 `_is_unordered_name_field` 规则自动排序。

## 6. Collection 数据模型

### 6.1 Blender API 事实

```text
FACT_1: object.users_collection 只返回对象直接所属的 Collection。
        Collection 是 Blender 中的一等对象，通过 Python identity 区分。

FACT_2: Collection 没有 users_collection 属性。

FACT_3: Collection 的祖先关系通过 collection.children 反向推导。
        如果 collection A 的 children 中包含 collection B，
        则 A 是 B 的祖先。

FACT_4: bpy.data.collections 包含当前 .blend 中的所有 Collection，
        不论它们是否链接到当前 Scene。

FACT_5: 一个对象可以直接属于多个 Collection（多对多关系）。

FACT_6: 一个 Collection 可以被多个父级 Collection 包含。

FACT_7: Scene master collection 是场景的根 Collection，
        可通过 scene.collection 访问。
```

### 6.2 祖先反向索引

```text
定义:
  child→parent 反向索引: dict[id(child)] → list[id(parent)]

构建:
  物化 bpy.data.collections 中的所有 Collection。
  对每个 collection，遍历其 .children，记录 child id → parent id。

  一个 child 有多个 parent → 列表包含所有 parent id。

  遍历时使用 visited identity 集合防止无限循环。
  Blender 通常不允许循环，但防御式编码仍然需要 visited 集合。
```

## 7. Scene Collection 范围裁定

### 7.1 裁定

```text
SCENE_COLLECTION_SCOPE: OPTION_B — 允许 bpy.data.collections 中
  当前目标 Scene 外的 Collection 满足条件。
```

### 7.2 理由

```text
1. Collection 存在性是全局文件级属性。
   Impl Contract R2 §3.4: "Collection existence is independent of object hierarchy."
   同样，Collection 存在性独立于 Scene 链接。

2. 原始业务需求（交接文档 v4 L1-A）检查 "Collection 与对象存在性"，
   不限定 Scene 成员身份。

3. 对象可能通过 Append 操作被添加到任意 Collection，
   这些 Collection 未必在目标 Scene Collection 树中。

4. 按 bpy.data.collections 全量搜索的语义更简洁、更可预测，
   不需要额外 Scene 过滤逻辑。
```

### 7.3 影响

```text
- 全局 required/forbidden: 已在 bpy.data.collections 全量中操作，不受影响。
- Per-target 祖先闭包: 祖先 Collection 可能不在当前 Scene 内。
  direct_collections 和 ancestor_collections 字段会反映实际成员关系。
- Scene master collection: 可能出现在祖先闭包中（如果它是直接 Collection 的祖先）。
  不特殊处理——它与普通 Collection 行为一致。
```

## 8. 全局检查算法

### 8.1 一次 Collection 物化

```text
函数: _check_collection_rules_global(collection_rules_block)
文件: blender_scene_reader.py

Algorithm:
1. 判定启用 (§3 G1-G5)。未启用 → 不创建 global_results key，直接返回 None。

2. 一次性物化 bpy.data.collections:
   try:
       all_collections = list(bpy.data.collections)
   except → ERROR (operation: MATERIALIZE_BPY_DATA_COLLECTIONS)

3. 构建集合名称映射:
   collection_names = set()
   for col in all_collections:
       try:
           collection_names.add(col.name)
       except → ERROR (operation: READ_COLLECTION_NAME, collection 可能是
           Python identity 无法解析名称的异常对象)

4. 执行 required 检查（若启用）:
   required_names_list = sorted(set(required_collection_names), key=casefold)
   missing_names = []
   for name in required_names_list:
       if name not in collection_names:
           missing_names.append(name)
   missing_names.sort(key=casefold)

   If missing_names:
       required.result = FAIL, missing_names = [...]
   Else:
       required.result = PASS, missing_names = []

5. 执行 forbidden 检查（若启用）:
   forbidden_patterns_list = sorted(set(forbidden_collection_name_patterns),
                                    key=casefold)
   matched = []
   for col_name in sorted(collection_names, key=casefold):
       for pat in forbidden_patterns_list:
           if casefold_glob_match(col_name, pat):
               matched.append(col_name)
               break  # 一个 collection 命中即记录
   matched_collections = sorted(set(matched), key=casefold)

   If matched_collections:
       forbidden.result = FAIL, matched_collections = [...]
   Else:
       forbidden.result = PASS, matched_collections = []

6. 聚合:
   顶层 result = ERROR > FAIL > PASS > NOT_CHECKED
   failure_code (FAIL): "COLLECTION_RULES_FAILURE"
```

### 8.2 确定性

```text
- list(bpy.data.collections) 的物化顺序由 Blender 内部决定，
  但所有后续排序操作（required_names, missing_names, forbidden_patterns,
  matched_collections, collection_names 遍历）均为显式排序。
- 最终输出与物化顺序无关。
```

## 9. Per-target 祖先闭包算法

### 9.1 总函数

```text
函数: _check_collection_membership(scene, target, per_target_result)
文件: blender_scene_reader.py

Algorithm:
1. 判定配置 (§3 P1-P4)。未启用 → NOT_CHECKED。

2. Root 前置条件 (§11)。不满足 → NOT_CHECKED。

3. 物化 root_obj:
   从 per_target_result.checks.object_type 获取 root_type_value。
   按 target.root_object_name 在 scene.objects 中重新解析 root_obj
   （与 Material Assignment §6.3 相同模式）。

4. 物化祖先反向索引 (§6.2):
   _materialize_collection_ancestor_index()
   → 返回 dict[id(child)] → list[id(parent)]

5. 读取 root 的直接 Collection:
   try:
       direct_colls = list(root_obj.users_collection)
   except → ERROR (operation: READ_ROOT_USERS_COLLECTION)

6. 计算祖先闭包:
   _compute_ancestor_closure(direct_colls, ancestor_index)
   → 返回 (ancestor_names, error)

7. 匹配:
   all_collection_names = {c.name for c in direct_colls} | set(ancestor_names)
   required_names = sorted(set(target["required_collection_names"]), key=casefold)
   matched = [n for n in required_names if n in all_collection_names]
   missing = [n for n in required_names if n not in all_collection_names]

8. 结果:
   至少一个 matched → PASS
   没有 matched → FAIL (failure_code: TARGET_NOT_IN_REQUIRED_COLLECTION)
```

### 9.2 祖先反向索引物化

```text
函数: _materialize_collection_ancestor_index()
文件: blender_scene_reader.py

Algorithm:
1. try:
       all_collections = list(bpy.data.collections)
   except → ERROR (operation: MATERIALIZE_BPY_DATA_COLLECTIONS)

2. parent_of = {}  # dict: id(child) → list[id(parent)]
   visited_pairs = set()  # (parent_id, child_id) 防重复

   for col in all_collections:
       try:
           children = list(col.children)
       except → ERROR (operation: READ_COLLECTION_CHILDREN,
                       collection_name=col.name)
       for child in children:
           pair = (id(col), id(child))
           if pair in visited_pairs:
               continue
           visited_pairs.add(pair)
           cid = id(child)
           if cid not in parent_of:
               parent_of[cid] = []
           parent_of[cid].append(id(col))

3. return parent_of
```

### 9.3 祖先闭包计算

```text
函数: _compute_ancestor_closure(direct_colls, ancestor_index)
文件: blender_scene_reader.py

Algorithm:
1. 初始化:
   visited_ids = set()
   ancestor_names = []
   stack = list(direct_colls)  # 从直接 Collection 开始向上遍历

2. while stack:
       col = stack.pop()
       cid = id(col)
       if cid in visited_ids:
           continue
       visited_ids.add(cid)

       try:
           cname = col.name
       except → ERROR (operation: READ_COLLECTION_NAME)

       parent_ids = ancestor_index.get(cid, [])
       for pid in parent_ids:
           if pid not in visited_ids:
               # 需要在 all_collections 中通过 identity 查找
               # parent lookup 在 _materialize_collection_ancestor_index
               # 中已构建 id→parent_id 映射，但需要反查 parent 对象
               # 实际实现在 _materialize 时同时构建 id→name 缓存

3. return (ancestor_names, None)

注意: 精确实现需要在 _materialize_collection_ancestor_index 中
同时构建 id→name 缓存，以便 _compute_ancestor_closure 通过 parent id
获取 parent name 而不重新读取 parent.name。
详见 §14 缓存合同。
```

### 9.4 遍历终止条件

```text
- visited_ids 确保每个 collection 只处理一次
- 到达没有 parent 的根 collection 时自然终止
- 多父级时每个父级独立遍历
- 祖先名称去重: set(ancestor_names)
```

## 10. Forbidden glob 语义

```text
CASE_SENSITIVITY: casefold — 使用 14A core 中已有的 casefold_glob_match
  理由: 与 hierarchy forbidden patterns 一致；Blender collection 名称
  大小写敏感但 glob 模式通常应该不区分大小写

EMPTY_STRING_PATTERN: 有效 pattern
  casefold_glob_match 的 fnmatch 不匹配空字符串到任何非空名称
  空字符串 pattern 不会命中正常 collection
  不特殊处理——让 fnmatch 语义自然决定

DUPLICATE_PATTERNS: 去重
  forbidden_patterns 中的重复 pattern 仅保留一次
  去重后按 casefold 排序输出

MULTIPLE_PATTERNS_HIT_ONE_COLLECTION: 仅记录一次
  一个 collection 被多个 pattern 命中 → matched_collections 出现一次

ONE_PATTERN_HITS_MULTIPLE_COLLECTIONS: 全部记录
  matched_collections 包含所有命中名称

REQUIRED_NAME_ALSO_FORBIDDEN: 两者独立
  required 检查独立于 forbidden 检查
  required: PASS (collection 存在) + forbidden: FAIL (pattern 命中)
  → 顶层: FAIL

MATCHED_COLLECTIONS_SORTING: casefold 排序
```

## 11. Root 前置条件

```text
Root 对象获取:
  方式: 在 scene.objects 中按 target.root_object_name 精确匹配，
       读取 obj.name 并缓存。
  与 Material Assignment §6.3 相同的独立 root 解析模式。
  不修改 _check_root_objects()。

  不能复用 per_target_result 中的 Python object identity
  因为 _check_root_objects() 不暴露内部 matched_obj 引用。
  独立解析确保 identity 正确且不依赖未暴露的内部状态。

Root 前置判定:
  使用 per_target_result.checks 中的已锁定结果:

  object_exists.result == FAIL
    → NOT_CHECKED, note: "ROOT_OBJECT_NOT_FOUND"

  object_exists.error_type == "AMBIGUOUS_ROOT_OBJECT_NAME"
    → NOT_CHECKED, note: "AMBIGUOUS_ROOT_OBJECT_NAME"

  object_type.result == FAIL
    → NOT_CHECKED, note: "ROOT_OBJECT_TYPE_MISMATCH"

  object_exists.result == PASS 且 object_type.result == PASS
    → 执行 per-target 检查

Root type value:
  从 per_target_result.checks.object_type.actual 获取
  不再次读取 root_obj.type
```

## 12. PASS / FAIL / ERROR / NOT_CHECKED 矩阵

### 12.1 全局层

| 场景 | required | forbidden | 顶层 | failure_code |
|------|----------|-----------|------|-------------|
| collection_rules 缺失/null | — | — | 不创建键 | — |
| collection_rules: {} | NOT_CHECKED | NOT_CHECKED | NOT_CHECKED | — |
| required=[] + forbidden=[] | NOT_CHECKED | NOT_CHECKED | NOT_CHECKED | — |
| required 全部存在 + forbidden 已启用且无命中 | PASS | PASS | PASS | — |
| required 全部存在 + forbidden 未启用 | PASS | NOT_CHECKED | PASS | — |
| required 未启用 + forbidden 无命中 | NOT_CHECKED | PASS | PASS | — |
| required 缺失 1 个 + forbidden 无命中 | FAIL | PASS | FAIL | COLLECTION_RULES_FAILURE |
| required 全部存在 + forbidden 有命中 | PASS | FAIL | FAIL | COLLECTION_RULES_FAILURE |
| required 缺失 + forbidden 有命中 | FAIL | FAIL | FAIL | COLLECTION_RULES_FAILURE |
| bpy.data.collections 物化异常 | ERROR 短路 | ERROR 短路 | ERROR | — |
| collection.name 读取异常 | ERROR 短路 | ERROR 短路 | ERROR | — |

### 12.2 Per-target 层

| 场景 | 结果 | failure_code / note |
|------|------|-------------------|
| required_collection_names 缺失/null/[] | NOT_CHECKED | REQUIRED_COLLECTION_NAMES_NOT_CONFIGURED |
| root 不存在 | NOT_CHECKED | ROOT_OBJECT_NOT_FOUND |
| root 名称歧义 | NOT_CHECKED | AMBIGUOUS_ROOT_OBJECT_NAME |
| root 类型不匹配 | NOT_CHECKED | ROOT_OBJECT_TYPE_MISMATCH |
| 直接 Collection 命中 | PASS | — |
| 祖先 Collection 命中 | PASS | — |
| 多个 required 命中至少一个 | PASS | — |
| 无 required 命中 | FAIL | TARGET_NOT_IN_REQUIRED_COLLECTION |
| 直接 Collection 为空 + 祖先为空 | FAIL | TARGET_NOT_IN_REQUIRED_COLLECTION |
| obj.users_collection 读取异常 | ERROR | — |
| bpy.data.collections 物化异常 | ERROR | — |
| collection.children 读取异常 | ERROR | — |
| collection.name 读取异常 | ERROR | — |

### 12.3 与其他字段组的独立性

```text
— 不依赖 Hierarchy / Standing / Facing / Visibility / Rotation /
  Animation State / Material Assignment 的 PASS/FAIL
— 其他字段组 FAIL/ERROR 不阻止 Collection Rules
— Collection Rules ERROR 不阻止已完成的 root 检查和其他字段组结果
— 唯一阻断（per-target）: root 前置条件不满足
```

## 13. failure_code

```text
CLOSED_FAILURE_CODE_SET:

  REQUIRED_COLLECTION_MISSING
    — 触发: 全局 required 名称在 bpy.data.collections 中不存在
    — 位置: collection_rules.required

  FORBIDDEN_COLLECTION_MATCHED
    — 触发: 全局 forbidden pattern 命中至少一个 collection
    — 位置: collection_rules.forbidden

  COLLECTION_RULES_FAILURE
    — 触发: 任意全局子检查 FAIL
    — 位置: collection_rules 顶层

  TARGET_NOT_IN_REQUIRED_COLLECTION
    — 触发: root object 不属于任何 required collection
    — 位置: collection_membership 顶层
```

## 14. ERROR type 和 operation

### 14.1 Error Type

```text
ERROR_TYPE: COLLECTION_RULES_COMPUTATION_ERROR (uniform)
```

### 14.2 Operation 集合（恰好 9 个）

**全局层（5 个）**:

| # | Operation | 包含的 bpy 操作 | 说明 |
|---|-----------|---------------|------|
| G1 | MATERIALIZE_BPY_DATA_COLLECTIONS | bpy.data.collections 属性迭代 + list() 物化 | 一次性获取所有 Collection |
| G2 | READ_COLLECTION_NAME | collection.name 属性读取 | 构建名称集合 |
| G3 | RESOLVE_REQUIRED_COLLECTION | collection_names set 中的成员查找 | required 名称匹配 |
| G4 | MATCH_FORBIDDEN_PATTERN | casefold_glob_match 调用 | pattern 匹配 |
| G5 | READ_COLLECTION_CHILDREN_GLOBAL | collection.children 属性读取 + list() 物化 | 仅当全局需要读取 children |

**Per-target 层（4 个）**:

| # | Operation | 包含的 bpy 操作 | 说明 |
|---|-----------|---------------|------|
| P1 | READ_ROOT_USERS_COLLECTION | root_obj.users_collection 属性读取 + list() 物化 | 获取直接 Collection |
| P2 | READ_COLLECTION_CHILDREN_PER_TARGET | collection.children 属性读取 + list() 物化 | 构建祖先反向索引 |
| P3 | READ_COLLECTION_NAME_PER_TARGET | collection.name 属性读取 | 祖先闭包名称解析 |
| P4 | RESOLVE_ROOT_OBJECT_FOR_COLLECTION | scene.objects 中 obj.name 读取并缓存 | 独立 root 解析 |

### 14.3 短路规则

```text
全局层:
  G1 异常 → 全局 ERROR，两个子检查均短路为 NOT_CHECKED
  G2 异常 → 全局 ERROR，短路
  G5 异常 → 全局 ERROR（若全局 required 也读 children）

Per-target 层:
  P1 异常 → per-target ERROR，不执行祖先闭包
  P2 异常 → per-target ERROR (含 collection_name)
  P3 异常 → per-target ERROR (含 collection_name)
  P4 异常 → per-target ERROR

全局和 per-target ERROR 独立，互不短路。
```

### 14.4 顶层 ERROR 收集

```text
在 asset_scene_preflight_check.py _collect_target_errors 中新增 Collection Rules 分支:

全局 ERROR (在 _collect_target_errors 的参数中新增 global_results 访问或独立函数):

Per-target ERROR:
  "COLLECTION_RULES_COMPUTATION_ERROR: target '{tid}' collection_rules operation '{op}'"
  若附带了 collection_name:
  "COLLECTION_RULES_COMPUTATION_ERROR: target '{tid}' collection_rules operation '{op}' collection '{cname}'"

消息按 (operation, collection_name or "") 稳定排序。
```

## 15. 属性读取与缓存合同

### 15.1 全局层读取次数

| 属性/操作 | 最大读取次数 | 说明 |
|----------|------------|------|
| bpy.data.collections 迭代 + list() | 1 | 全局检查启用时，一次性物化 |
| collection.name | 1 per collection | 构建名称集合时读取 |

### 15.2 Per-target 层读取次数

| 属性/操作 | 最大读取次数 | 说明 |
|----------|------------|------|
| bpy.data.collections 迭代 + list() | 1 per target（若 per-target 启用） | 祖先反向索引构建 |
| root_obj.users_collection | 1 per target | 获取直接 Collection |
| collection.children | 1 per collection（特定 parent） | 祖先反向索引构建 |
| collection.name | 1 per collection（direct + ancestor） | 通过 id→name 缓存 |
| scene.objects | 1 per target（若配置启用+root前置满足） | 独立 root 解析 |

### 15.3 缓存约定

```text
GLOBAL_LEVEL_CACHE:
  — all_collections: list(bpy.data.collections)，全局 helper 返回后可用
  — collection_names: set[str]，名称集合，一次性构建
  — name_by_id: dict[id(col)] → name，全局物化时构建

PER_TARGET_CACHE:
  — ancestor_index: dict[id(child)] → list[id(parent)]，每 target 构建一次
  — name_by_id (per-target): 在 _materialize_collection_ancestor_index 中构建，
    供 _compute_ancestor_closure 通过 parent id 获取名称
  — 不跨 target 复用 ancestor_index（不同 target 可能在不同时间点调用）

NO_CACHE:
  — obj.users_collection: 每次 per-target 检查时读取一次

READ_ONLY:
  — 不写入 bpy 属性，不修改 collection 结构，不调用 bpy.ops
```

## 16. 函数边界

### 16.1 候选函数签名

```text
全局层 (blender_scene_reader.py):

  _check_collection_rules_global(collection_rules_block)
    → 返回 global_results["collection_rules"] 的完整 dict
    → 若全局未启用，返回 None

  _materialize_bpy_data_collections()
    → 返回 (all_collections, name_by_id, error)
    → error 为 ERROR dict 或 None

Per-target 层 (blender_scene_reader.py):

  _check_collection_membership(scene, target, per_target_result)
    → 返回 checks.collection_membership 的完整 dict

  _materialize_collection_ancestor_index(all_collections, name_by_id)
    → 返回 (ancestor_index, error)
    → ancestor_index: dict[id(child)] → list[id(parent)]

  _compute_ancestor_closure(direct_colls, ancestor_index, name_by_id)
    → 返回 (ancestor_names, error)

  _resolve_root_for_collection_rules(scene, target, per_target_result)
    → 返回 (root_obj, error)
```

### 16.2 职责边界

```text
_check_collection_rules_global:
  — 读取: bpy.data.collections, collection.name
  — 禁止读取: obj.users_collection, obj.children, scene.objects

_check_collection_membership:
  — 读取: scene.objects, obj.name, obj.users_collection,
          collection.children, collection.name
  — 禁止读取: material_slots, animation_data, matrix_world 等

_materialize_collection_ancestor_index:
  — 唯一授权读取 collection.children
  — 唯一授权构建 id→name 缓存

_compute_ancestor_closure:
  — 不得重新读取 collection.children
  — 不得重新读取 collection.name（使用 name_by_id）
```

## 17. 生产集成顺序

### 17.1 open_blend_and_get_scene 中的调用位置

```python
def open_blend_and_get_scene(absolute_blend_path, scene_name,
                              spec_scene_rules, targets=None):
    # ... existing file open, scene lookup, scene_basic ...

    per_target_results = _check_root_objects(scene, targets)

    # --- Global Collection Rules (before per-target loop) ---
    collection_rules_block = spec.get("collection_rules") if spec else None
    global_cr = _check_collection_rules_global(collection_rules_block)
    if global_cr is not None:
        global_results["collection_rules"] = global_cr

    # --- Per-target checks ---
    if scene is not None:
        for i, target in enumerate(targets):
            if i >= len(per_target_results):
                continue

            target_result = per_target_results[i]

            as_result = _check_animation_state(scene, target)
            target_result["checks"]["animation_state"] = as_result

            ma_result = _check_material_assignment(scene, target, target_result)
            target_result["checks"]["material_assignment_presence_check"] = ma_result

            # NEW: Collection Rules per-target
            cr_result = _check_collection_membership(scene, target, target_result)
            target_result["checks"]["collection_membership"] = cr_result

            target_result["overall"] = _recompute_target_overall(
                target_result["checks"])

    return {"scene_basic": checks, "per_target_results": per_target_results}
```

### 17.2 调用顺序约束

```text
1. _check_root_objects 最先执行（已锁定）
2. 全局 Collection Rules 在 per-target loop 之前执行
   与 scene.objects 遍历无依赖关系
3. Per-target loop 内:
   Animation State → Material Assignment → Collection Rules
   Collection Rules 在 Material Assignment 之后、_recompute_target_overall 之前
4. 全局 Collection Rules ERROR 不影响 per-target 执行
5. Per-target Collection Rules ERROR 不影响同 target 内其他字段组
```

### 17.3 全局退出状态聚合

```text
整体 EXIT 判定:
  全局层:
    如果 global_cr["result"] == "ERROR" → EXIT_ERROR
    FAIL 不单独决定整体退出——per_target_results 的 FAIL 已经导致 EXIT_FAIL
    但如果所有 per_target 均 PASS 而 global FAIL → EXIT_FAIL

  具体集成:
    _validate_and_open_spec 中已有 any_error / any_fail 判定。
    在 any_error 检查中新增 global_results["collection_rules"]["result"] == "ERROR"。
    在 _collect_target_errors 中新增全局 ERROR 消息收集。
```

## 18. overall 和错误收集

### 18.1 target overall

```text
collection_membership.result 参与 _recompute_target_overall()。
checks 全部子键统一遍历: ERROR > FAIL > PASS。
NOT_CHECKED 不提升 overall（等同于 PASS 对 overall 的影响）。
```

### 18.2 _collect_target_errors 新增分支

```text
cr = checks.get("collection_membership", {})
if cr.get("result") == "ERROR":
    op = cr.get("operation", "UNKNOWN")
    cn = cr.get("collection_name", "")
    if cn:
        msg = (f"COLLECTION_RULES_COMPUTATION_ERROR: target '{tid}' "
               f"collection_rules operation '{op}' collection '{cn}'")
    else:
        msg = (f"COLLECTION_RULES_COMPUTATION_ERROR: target '{tid}' "
               f"collection_rules operation '{op}'")
    err_msgs.append(msg)

全局 ERROR 也需要独立收集（在 _validate_and_open_spec 中处理）。
```

## 19. Scope Guard 合同

```text
CORE_PROTECTED_ATTRIBUTES:
  bpy.data.collections
  obj.users_collection
  collection.children
  collection.name (per-target context)

唯一授权直接读取的函数:
  全局层:
    _check_collection_rules_global → bpy.data.collections, collection.name
    _materialize_bpy_data_collections → bpy.data.collections, collection.name
  Per-target 层:
    _check_collection_membership → obj.users_collection (via root obj)
    _materialize_collection_ancestor_index → collection.children, collection.name
    _resolve_root_for_collection_rules → scene.objects, obj.name

其他生产函数禁止直接读取:
  — bpy.data.collections (必须通过 _check_collection_rules_global
    或 _materialize_collection_ancestor_index)
  — obj.users_collection (必须通过 _check_collection_membership)
  — collection.children (必须通过 _materialize_collection_ancestor_index)

FORBIDDEN_ALWAYS:
  — 写入 users_collection / collection.children
  — getattr / setattr / delattr / hasattr 绕过
  — 别名 / lambda / 局部 helper / 动态字符串绕过
  — bpy.data 绕过直接访问

ALLOWED_ALWAYS:
  — scene.objects（已在 14B_2A 后授权多个读取点）
  — obj.name（已在 14B_2A 后广泛授权）
  — collection.name（唯一在此设计中授权）

SCOPE_GUARD_COVERAGE:
  默认不要求:
    — 任意深度递归调用分析
    — 完整函数对象传播
    — 所有 lambda 组合
    — 动态字符串拼接
    — 完整 Python 数据流语义
    — 恶意攻击式代码变形
```

## 20. CPython 测试矩阵

```text
I1 (配置语义 + 全局 required/forbidden + per-target 归属 + PASS/FAIL/NOT_CHECKED):

  Schema (继承现有):
    — collection_rules 缺失 → schema 接受
    — collection_rules: {} → schema 接受
    — required_collection_names: ["A"] → schema 接受
    — required_collection_names: [""] → schema ERROR
    — forbidden_collection_name_patterns: ["*test*"] → schema 接受
    — targets[i].required_collection_names: ["A"] → schema 接受
    — targets[i].required_collection_names: [""] → schema ERROR

  全局配置语义:
    — collection_rules 缺失 → global_results 无 collection_rules 键
    — collection_rules: null → global_results 无 collection_rules 键
    — collection_rules: {} → NOT_CHECKED, 两个子检查 NOT_CHECKED
    — required 缺失/null/[] → NOT_CHECKED
    — forbidden 缺失/null/[] → NOT_CHECKED

  全局 required:
    — 全部存在 → PASS, missing_names=[]
    — 部分缺失 → FAIL, missing_names 列出
    — 全部缺失 → FAIL, missing_names 列出全部
    — 重复名称去重（set 语义）

  全局 forbidden:
    — 无命中 → PASS, matched_collections=[]
    — 有命中 → FAIL, matched_collections 列出
    — 多个 pattern 命中同一 collection → 记录一次
    — 一个 pattern 命中多个 collection → 全部记录
    — 重复 pattern 去重
    — casefold 匹配验证

  Per-target 配置语义:
    — required_collection_names 缺失/null/[] → NOT_CHECKED

  Per-target root 前置:
    — ROOT_OBJECT_NOT_FOUND → NOT_CHECKED
    — AMBIGUOUS_ROOT_OBJECT_NAME → NOT_CHECKED
    — ROOT_OBJECT_TYPE_MISMATCH → NOT_CHECKED

  Per-target 归属:
    — 直接 Collection 命中 → PASS
    — 祖先 Collection 命中 → PASS
    — 无命中 → FAIL
    — 多个 required 命中至少一个 → PASS
    — 对象属于多个 Collection 且至少一个匹配 → PASS

  聚合:
    — 全局 PASS + per-target PASS → 各自独立输出
    — 全局 FAIL + per-target PASS → 各自独立输出
    — global_results 结构完整
```

## 21. Blender 5.1.2 临时场景矩阵

```text
I4B: 临时 Blender 场景 (--factory-startup --background), 13 scenarios:

  CR-I4B-01: required Collection 存在 → 全局 PASS
    创建 Collection "CHR_TEST" → required=["CHR_TEST"] → PASS

  CR-I4B-02: required Collection 缺失 → 全局 FAIL
    required=["NONEXISTENT"] → FAIL, missing_names=["NONEXISTENT"]

  CR-I4B-03: forbidden pattern 命中 → 全局 FAIL
    创建 Collection "test_temp" → forbidden=["*test*"] → FAIL

  CR-I4B-04: forbidden pattern 无命中 → 全局 PASS
    forbidden=["*nope*"] → PASS

  CR-I4B-05: Collection 存在但为空 → 全局 PASS
    required Collection 存在（无对象）→ 存在性通过

  CR-I4B-06: root 直接属于 required Collection → per-target PASS
    root → scene.collection.objects.link → Collection "CHR_A"
    required=["CHR_A"] → PASS

  CR-I4B-07: root 通过一层父 Collection 满足 → per-target PASS
    Collection "Parent" children=["CHR_A"]; root 在 "CHR_A" 中
    required=["Parent"] → PASS (祖先命中)

  CR-I4B-08: root 通过多层祖先满足 → per-target PASS
    "Grandparent" → "Parent" → "CHR_A" → root
    required=["Grandparent"] → PASS

  CR-I4B-09: root 属于多个 Collection 且其中一个满足 → per-target PASS
    root 在 "Other" 和 "CHR_A" 中; required=["CHR_A"] → PASS

  CR-I4B-10: root 完全不属于 required Collection → per-target FAIL
    root 在 "Other" 中; required=["CHR_A", "CHR_B"] → FAIL

  CR-I4B-11: 全局和 per-target 同时启用
    collection_rules (全局) + target.required_collection_names (per-target)
    → 独立结果，各自输出

  CR-I4B-12: Collection Rules + Material Assignment 共存
    root MESH 有 material + 在 required Collection 中
    → 两个检查独立 PASS

  CR-I4B-13: 一个 Collection 被多个父级链接 → 祖先闭包正确
    "ParentA" children=["Shared"]; "ParentB" children=["Shared"]
    root 在 "Shared" 中; required=["ParentA"] → PASS

Each scenario specifies:
  — 对象和 Collection 拓扑
  — Scene membership
  — 输入配置
  — 期望结果
  — 该场景证明的唯一行为

PROHIBITED: 真实项目 .blend, 保存, 渲染, 视觉判断
```

## 22. 实施任务拆分

### I1: Config + Global + Per-target PASS/FAIL/NOT_CHECKED

```text
TASK: COLLECTION_RULES_I1
PROVES: 全局配置语义, 全局 required, 全局 forbidden,
        per-target 配置语义, root 前置, 祖先闭包, 归属检查, 聚合
PRODUCTION_FILE: blender_scene_reader.py
TEST_FILE: test_asset_scene_preflight_collection_rules_i1.py (新增, CPython)
NOT_IMPLEMENTING: ERROR branches, _collect_target_errors 集成,
                  open_blend_and_get_scene 集成, Blender, scope guard
BLENDER_REQUIRED: FALSE
```

### I2: ERROR Branches + Error Collection

```text
TASK: COLLECTION_RULES_I2
PROVES: 全部 9 个 ERROR operation, 全局短路, per-target 短路,
        _collect_target_errors 注册
PRODUCTION_FILE: blender_scene_reader.py
MODIFIED_FILE: asset_scene_preflight_check.py (_collect_target_errors 新增)
TEST_FILE: test_asset_scene_preflight_collection_rules_i2.py (新增, CPython)
NOT_IMPLEMENTING: open_blend_and_get_scene 集成, Blender, scope guard
BLENDER_REQUIRED: FALSE
```

### I3: Integration + overall + global exit

```text
TASK: COLLECTION_RULES_I3
PROVES: open_blend_and_get_scene 集成, 调用顺序, global_results 写入,
        per_target_results 写入, overall 重算, 全局退出状态
PRODUCTION_FILE: blender_scene_reader.py (仅修改 open_blend_and_get_scene)
MODIFIED_FILE: asset_scene_preflight_check.py (全局 ERROR 处理)
TEST_FILE: test_asset_scene_preflight_collection_rules_i3.py (新增, CPython)
NOT_IMPLEMENTING: Blender, scope guard
NOT_MODIFIED: _check_root_objects
BLENDER_REQUIRED: FALSE
```

### I4A: AST Scope Guard

```text
TASK: COLLECTION_RULES_I4A
PROVES: bpy.data.collections / obj.users_collection / collection.children
        仅授权函数访问, 正向/反向/对抗探针全部通过
PRODUCTION_FILE: NONE (生产代码冻结)
TEST_FILE: test_asset_scene_preflight_collection_rules_i4a_scope_guard.py
           (新增, CPython AST)
BLENDER_REQUIRED: FALSE
```

### I4B: Blender 5.1.2 Validation

```text
TASK: COLLECTION_RULES_I4B
PROVES: 13 Blender 场景全部正确
PRODUCTION_FILE: NONE
TEST_FILE: test_asset_scene_preflight_collection_rules_i4b_blender.py (新增)
RUNNER_FILE: blender_collection_rules_i4b_runner.py (新增)
BLENDER_REQUIRED: TRUE
FACTORY_STARTUP: TRUE
```

### E: Final Regression

```text
TASK: COLLECTION_RULES_E
PROVES: Collection Rules focused, 14A Core, full protocol_guard 全部通过
PRODUCTION_CODE_MODIFIED: FALSE
EXISTING_TESTS_MODIFIED: FALSE
BLENDER_REQUIRED: TRUE (I4B runner)
REAL_PROJECT_BLEND_OPENED: FALSE
```

## 23. 明确不实施内容

```text
NOT_IN_THIS_DESIGN:
  — 材质存在性验证（属于 Material Assignment）
  — Collection 内部对象结构验证（属于 Hierarchy）
  — Collection 可见性验证（属于 Visibility）
  — 真实项目 .blend 验证
  — Append / Link 操作执行
  — 保存重开持久化验证
  — 角色库文件路径验证
  — 全局 required 和 per-target required 之间的交叉验证
  — Scene master collection 特殊处理
```

## 24. 锁定边界兼容性

```text
14A_CORE_SCHEMA: COMPATIBLE (不新增/修改字段，仅使用现有字段)
_check_root_objects: COMPATIBLE (独立 root 解析，不修改其行为)
HIERARCHY: COMPATIBLE (正交维度，不读取 object.children/parent)
STANDING: COMPATIBLE (无共享数据路径)
FACING: COMPATIBLE (无共享数据路径)
VISIBILITY: COMPATIBLE (无共享数据路径)
ROTATION: COMPATIBLE (无共享数据路径)
ANIMATION_STATE: COMPATIBLE (无共享数据路径)
MATERIAL_ASSIGNMENT: COMPATIBLE (无共享数据路径)
TARGET_OVERALL_AGGREGATION: COMPATIBLE (_recompute_target_overall 自动纳入新 key)
GLOBAL_RESULTS: COMPATIBLE (新增独立键，不修改 scene_basic)
_collect_target_errors: COMPATIBLE (新增分支，不修改现有分支)
```

## 25. 设计自洽检查

```text
SEMANTIC_CLOSURE:
  [x] collection_rules 缺失 → 不创建 global_results key
  [x] collection_rules: null → 不创建 global_results key
  [x] collection_rules: {} → NOT_CHECKED × 2, 不读 bpy
  [x] required 缺失/null/[] → NOT_CHECKED, 不读 bpy
  [x] forbidden 缺失/null/[] → NOT_CHECKED, 不读 bpy
  [x] required 非空 → 执行检查, 物化 bpy.data.collections
  [x] forbidden 非空 → 执行检查, 复用同次物化
  [x] required 全部存在 → PASS
  [x] required 部分缺失 → FAIL, COLLECTION_RULES_FAILURE
  [x] forbidden 无命中 → PASS
  [x] forbidden 有命中 → FAIL, COLLECTION_RULES_FAILURE
  [x] bpy.data.collections 异常 → ERROR, 全部短路
  [x] per-target required 缺失/null/[] → NOT_CHECKED
  [x] per-target root 不存在 → NOT_CHECKED
  [x] per-target root 歧义 → NOT_CHECKED
  [x] per-target root 类型不匹配 → NOT_CHECKED
  [x] per-target 直接命中 → PASS
  [x] per-target 祖先命中 → PASS
  [x] per-target 无命中 → FAIL, TARGET_NOT_IN_REQUIRED_COLLECTION
  [x] obj.users_collection 异常 → ERROR
  [x] collection.children 异常 → ERROR
  [x] 全局 + per-target 独立启用
  [x] 全局 + per-target 共存且独立
  [x] Collection Rules + Material Assignment 共存
  [x] 多父级 Collection → 祖先闭包正确处理
  [x] 名称按 casefold 排序
  [x] casefold_glob_match 用于 forbidden pattern
  [x] 所有 canonicalization 预留字段已复用
  [x] 没有 collection.users_collection 引用
  [x] 没有硬编码五个角色名称
  [x] 没有修改 _check_root_objects
  [x] FAIL 条件不建模成 ERROR
  [x] 没有 TBD / 待实现时决定 / 按情况处理
  [x] 精确 9 个 ERROR operation (5 global + 4 per-target)
  [x] 精确 4 个 failure_code
  [x] 所有 Markdown 围栏配对
  [x] 无自身 SHA256
```
