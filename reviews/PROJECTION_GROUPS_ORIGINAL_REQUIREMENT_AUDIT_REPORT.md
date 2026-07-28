# Projection Groups Original Requirement Audit Report

```text
TASK_ID: PROJECTION_GROUPS_ORIGINAL_REQUIREMENT_AUDIT
TASK_TYPE: READ_ONLY_ORIGINAL_REQUIREMENT_AUDIT
MASTER_MAP_VERSION: R79
DATE: 2026-07-26
BASELINE_COMMIT: d44679fc11c5069a17277395bb6c52b5a6dfc799
```

---

## 1. 人话结论

Projection Groups 是整个 asset_scene_preflight_check 的最后一个未开始字段组。与 Camera Check 不同，它**不是**从 V4 原始需求直接派生的——V4 交接文档没有任何地方提到 `projection_groups` 这个词。这个概念完全来自 R2 Implementation Contract §10.2 的创建。

R2 §10.2 给出了 10 个叶子字段（7 个直接字段）的 Schema、5 步高层算法和基本语义，足以支撑进入设计阶段。但相对于 Camera Check 拥有 R1 §19（投影算法）+ R2 §4（evaluated geometry）+ 14 项审计 DF 全部在设计阶段关闭，Projection Groups 的现有材料要薄得多。设计阶段需要裁定的事项包括：结果字典结构、NOT_CHECKED 条件、failure code / error type / operation 命名、空数组行为、缺失对象行为、联合 bbox 的空几何情况等——这些都是 Camera Check 设计已经解决的问题，可以在 Projection Groups 设计中复用相同的模式。

```text
AUDIT_RESULT: REQUIREMENTS_SUFFICIENT_FOR_DESIGN
TRUE_BLOCKING_ISSUES: 0
TRUE_CONTRACT_CONFLICTS: 0
```

---

## 2. 权威材料及优先级

```text
PRIORITY_1: ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md §10.2
  — AUTHORITATIVE_IMPLEMENTATION_CONTRACT:
    唯一直接定义 projection_groups 的来源。
    §10.2 "Global Projection Groups (New)" — 明确标注 NEW。
    §10.3 "Projection Limitations" — 几何边界 vs 视觉质量。
    §11.2 — 规范化规则 (projection_group_results 按 group_id 排序)。
    §15.2 — 测试类别 (联合 bbox 投影 2 个, 相机在 bbox 外 1 个)。

PRIORITY_2: asset_scene_preflight_core.py L223-274
  — LOCKED_SCHEMA:
    _validate_spec 内的 projection_groups 验证。
    10 个叶子字段（7 个直接字段）+ group_id 唯一性 + target_ids 引用 + bbox 顺序。

PRIORITY_3: Blender_固定资产模板路线_新对话交接文档_v4.md
  — AUTHORITATIVE_REQUIREMENT (间接):
    §十二·L1-C "essential objects 裁切数量 = 0"
    §十二·L1-C "所有人物完整进入安全区"
    §十二·L1-C "两个收银通道完整进入安全区"
    §十二·L1-C "左右安全边距 ≥ 4%"
    §十二·L1-C "相机不进入任何 essential object 的 bbox"
    这些是多对象联合投影需求，属于 Projection Groups 的业务范围。
    但 V4 没有 projection_groups 这个结构概念。

PRIORITY_4: CAMERA_CHECK_ORIGINAL_REQUIREMENT_AUDIT_REPORT.md (R3, R77)
  — SUPPORTING_BOUNDARY_DOCUMENT:
    §7 Camera Check 与 Projection Groups 的边界。
    CR-03、CR-07 明确归入 Projection Groups。

PRIORITY_5: CAMERA_CHECK_DESIGN_R2.md (FORMALLY_LOCKED)
  — SUPPORTING_REFERENCE:
    §4 EXPLICITLY_EXCLUDED: 跨 target 联合构图 → Projection Groups。
    提供投影算法、evaluated geometry、camera 查找等可复用模式。

PRIORITY_6: 锁定设计惯例 (间接参考)
  — GROUND_CONTACT_DESIGN_R2.md: evaluated geometry, cleanup contract
  — ROTATION_DESIGN_R3.md: result structure, ERROR mapping
  — ANIMATION_STATE_DESIGN_R5.md: independent per-target check
  — COLLECTION_RULES_DESIGN_R1.md: pre-open validation
```

---

## 3. 实际读取文件清单

| # | 路径 | 类型 | 存在 | 读取范围 |
|---|------|------|------|---------|
| 1 | `reviews/PROJECT_CODEIFICATION_MASTER_MAP.md` | 总地图 | YES | R79 全文相关段 |
| 2 | `CLAUDE.md` | 项目规则 | YES | 全文 |
| 3 | `GLOBAL_CODEIFICATION_AUDIT_INPUTS/01_authoritative_requirements/Blender_固定资产模板路线_新对话交接文档_v4.md` | 原始需求 | YES | projection 相关段 |
| 4 | `protocol_guard/phase3_min/asset_scene_preflight_core.py` | Schema 源码 | YES | L223-274 (_validate_spec projection_groups), L700-732 (build_pass/fail_result) |
| 5 | `protocol_guard/phase3_min/asset_scene_preflight_check.py` | Entry 源码 | YES | 全文 — 确认无 projection_groups 专用 pre-open validator |
| 6 | `protocol_guard/phase3_min/blender_scene_reader.py` | Reader 源码 | YES | Grep 确认 — 无 _check_projection_groups |
| 7 | `GLOBAL_CODEIFICATION_AUDIT_INPUTS/02_phase3_design/ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md` | 实现合同 R2 | YES | §10.2, §10.3, §11.2, §15.2, §16, §17 |
| 8 | `GLOBAL_CODEIFICATION_AUDIT_INPUTS/02_phase3_design/PHASE_3_MINIMUM_DESIGN_SPEC_R1.md` | 设计规格 R1 | YES | Grep 确认 — 无 projection_groups |
| 9 | `reviews/CAMERA_CHECK_ORIGINAL_REQUIREMENT_AUDIT_REPORT.md` | Camera Check 审计 | YES | §4.5, §7, §10 |
| 10 | `reviews/CAMERA_CHECK_DESIGN_R2.md` | Camera Check 设计 | YES | §1, §4, 边界声明 |
| 11 | `reviews/GLOBAL_CODEIFICATION_AUDIT_REPORT.md` | 全局审计 | YES | §4, §7, §8, §9 |
| 12 | `reviews/POST_14B_3B_GLOBAL_REMAINING_REQUIREMENTS_AUDIT_R1_REPORT.md` | 剩余需求审计 | YES | §3, §9 |
| 13 | `reviews/PHASE_3_CURRENT_IMPLEMENTATION_COVERAGE_AUDIT.md` | 覆盖率审计 | YES | §2.19, §4 |
| 14 | `protocol_guard/phase3_min/tests/test_asset_scene_preflight_core.py` | Schema 测试 | YES | projection_groups 测试段 (L353-391, L570-579, L754-757, L833-840) |
| — | `GLOBAL_CODEIFICATION_AUDIT_INPUTS/02_phase3_design/ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT.md` (R1) | 实现合同 R1 | **MISSING** | 磁盘和 git 历史均不存在 |

---

## 4. 当前 Schema 已经强制的内容

来源：`asset_scene_preflight_core.py` L223-274

### 4.1 字段类型和值域验证

| 字段 | 类型要求 | 值域/约束 |
|------|---------|----------|
| `projection_groups` 本身 | list 或 None | None → 不产生输入错误 |
| `projection_groups[i]` | dict | 非 dict → ERROR |
| `group_id` | non-empty str | 数组内唯一 |
| `target_ids` | list | 每个元素必须是已知 target_id |
| `additional_object_names` | list | 只检查是 array |
| `camera_object_name` | non-empty str | 空字符串 → ERROR |
| `minimum_visible_projected_corner_count` | int (非 bool) | ≥ 0 |
| `required_screen_bbox` | dict | 必须存在 |
| `.min_left` `.max_right` `.min_bottom` `.max_top` | number (非 bool) | 必须是有限值 (非 NaN/Inf) |
| bbox 顺序 | — | `min_left > max_right` → ERROR, `min_bottom > max_top` → ERROR |
| `require_camera_outside_world_bbox` | bool | 非 bool → ERROR |

### 4.2 当前 Schema 不检查的内容

```text
- target_ids 是否为空数组 → 允许
- additional_object_names 元素是否为空字符串 → 无检查
- additional_object_names 元素是否重复 → 无检查
- target_ids 是否重复 → 无检查
- bbox 值是否在 [0,1] 范围 → 无检查
- mvc 上限 → 无检查 (任意非负整数均可)
- camera_object_name 是否为纯空白 → 无检查 (只检查空字符串)
```

### 4.3 结果构建框架

`build_pass_result` 和 `build_fail_result` 接受 `projection_groups` 参数 → 写入 `projection_group_results`。

`_base_result` 初始化 `projection_group_results: []`。

`build_error_result` (input_errors 路径) 不包含 `projection_group_results`。

### 4.4 规范化规则 (R2 §11.2)

```text
- projection_group_results 按 group_id 排序
- target_ids within projection_group 保持 spec 顺序
```

### 4.5 当前 Schema 测试覆盖

| 测试 | 覆盖 |
|------|------|
| `test_projection_group_valid` (L353) | 完整有效块 → 0 errors |
| `test_projection_group_unknown_target` (L366) | target_id 引用未知 → ERROR |
| `test_projection_bbox_order_invalid` (L379) | min_left > max_right → ERROR |
| `test_screen_bbox_nan_rejected` (L570) | bbox 值为 NaN → ERROR |
| `test_projection_groups_sorted` (L754) | 规范化按 group_id 排序 |
| `test_projection_group_results_name_list_sorted` (L833) | 投影组结果内名称列表排序 |

未覆盖的 Schema 场景（设计/实施阶段补充，不属于本轮阻断）：
- projection_groups 为 None / 空数组的静默通过
- group_id 为空字符串
- group_id 重复
- camera_object_name 为空字符串
- mvc 为 bool
- mvc 为负数
- required_screen_bbox 非 dict
- bbox 字段缺失 (None)
- bbox 字段为 bool
- bbox 字段为 Inf
- require_camera_outside_world_bbox 非 bool
- target_ids 包含重复 target_id
- additional_object_names 为非数组类型
- min_bottom > max_top

---

## 5. 字段逐项裁定表

每项给出分类和依据。

### 5.1 projection_groups (顶层字段)

| 属性 | 值 |
|------|-----|
| 分类 | AUTHORITATIVE_REQUIREMENT |
| 来源 | R2 §10.2 + 当前 Schema L223-274 |
| 缺失或 null | 当前 14A Schema 不产生 projection_groups 输入错误 |
| 空数组 | 当前 14A Schema 接受空数组 `[]`，不产生 projection_groups 输入错误 |
| 运行时启用条件 | 设计自由（见 DF-PG-01, DF-PG-02） |
| 是否参与 overall 聚合 | 设计自由（见 DF-PG-26, DF-PG-27） |
| 备注 | R2 §17: `GLOBAL_PROJECTION_GROUP_SUPPORTED = TRUE` |

### 5.2 group_id

| 属性 | 值 |
|------|-----|
| 分类 | AUTHORITATIVE_REQUIREMENT |
| 来源 | R2 §10.2 示例: `"group_id": "essential_objects"` |
| Schema 强制 | non-empty str + 数组内唯一 |
| 作用范围 | 标识单个投影组；用于结果排序 (R2 §11.2 规则 7) |
| 设计未裁定 | group_id 是否需要符合特定命名规则 |

### 5.3 target_ids

| 属性 | 值 |
|------|-----|
| 分类 | AUTHORITATIVE_REQUIREMENT |
| 来源 | R2 §10.2: "All targets listed in target_ids (their geometry_scope)" |
| Schema 强制 | array，每个元素必须是已知 target_id |
| 文档缺口 | 空数组是否允许？target_ids 重复是否拒绝？引用自身缺失时的运行时行为？ |
| 设计未裁定 | target_ids 空 + additional_object_names 空 → 投影组是否有意义？ |

### 5.4 additional_object_names

| 属性 | 值 |
|------|-----|
| 分类 | AUTHORITATIVE_REQUIREMENT |
| 来源 | R2 §10.2: "All objects listed in additional_object_names (their full MESH geometry)" |
| Schema 强制 | array (不检查元素) |
| 文档缺口 | 空数组允许？名称在 Scene 中不存在？非 MESH 类型对象？名称歧义？名称不在任何 target 的 geometry_scope 内？ |
| 设计未裁定 | "full MESH geometry" = 包括子对象？只读该对象自身？ |

### 5.5 camera_object_name

| 属性 | 值 |
|------|-----|
| 分类 | AUTHORITATIVE_REQUIREMENT |
| 来源 | R2 §10.2 示例: `"camera_object_name": "Camera_Persp_3_4"` |
| Schema 强制 | non-empty str |
| 文档缺口 | 相机不在 Scene 对象中？对象类型不是 CAMERA？ |
| 参考 | Camera Check Design R2 已裁定：零匹配 → CAMERA_OBJECT_NOT_FOUND、多匹配 → CAMERA_OBJECT_NOT_FOUND、类型非 CAMERA → CAMERA_TYPE_MISMATCH。Projection Groups 是否复用这一归类仍属于设计自由。 |

### 5.6 minimum_visible_projected_corner_count

| 属性 | 值 |
|------|-----|
| 分类 | AUTHORITATIVE_REQUIREMENT |
| 来源 | R2 §10.2，与 Camera Check 共享语义 |
| Schema 强制 | non-bool int ≥ 0 |
| 文档缺口 | 相对于联合 bbox 8 角点，mvc > 8 是否允许？实际可见角点可能少于 8（部分角点在相机后方）。 |
| 设计自由 | Camera Check 设计裁定 mvc > 8 → pre-open ERROR。Projection Groups 可复用。 |

### 5.7 required_screen_bbox (整体)

| 属性 | 值 |
|------|-----|
| 分类 | AUTHORITATIVE_REQUIREMENT |
| 来源 | R2 §10.2 + Schema |
| 结构 | {min_left, max_right, min_bottom, max_top} |

### 5.8 required_screen_bbox.min_left / max_right / min_bottom / max_top

| 属性 | 值 |
|------|-----|
| 分类 | AUTHORITATIVE_REQUIREMENT |
| 来源 | R2 §10.2 示例: `{"min_left": 0.04, "max_right": 0.96, "min_bottom": 0.15, "max_top": 0.85}` |
| Schema 强制 | number (非 bool) + finite + 顺序关系 |
| 文档缺口 | 值是否应限制在 [0,1]？Camera Check 设计裁定 [0,1]（描述屏幕归一化范围），Projection Groups 的 Schema 不限制。 |
| 设计未裁定 | **轴向语义**：Camera Check 使用 HORIZONTAL=SAFE_MARGIN_CONTAINMENT (screen bbox 在 required 内)、VERTICAL=MINIMUM_COVERAGE (screen bbox 覆盖 required)。Projection Groups 是否使用相同模型？R2 §10.2 只说 "Check screen bbox boundaries against required_screen_bbox"，未指定方向。 |

### 5.9 require_camera_outside_world_bbox

| 属性 | 值 |
|------|-----|
| 分类 | AUTHORITATIVE_REQUIREMENT |
| 来源 | R2 §10.2: "verify camera location is outside the union bbox" |
| Schema 强制 | bool，默认 False |
| 文档缺口 | "outside" 的精确语义：完全在外部（严格不等）vs 边界接触也算？每个轴独立检查还是 3D 包含？联合 bbox 面/边/角上的相机算 inside 还是 outside？ |
| 设计未裁定 | 相机在 bbox 面上一侧为 inside 还是 outside？ |

### 5.10 geometry_scope 适用范围

| 属性 | 值 |
|------|-----|
| 分类 | AUTHORITATIVE_REQUIREMENT |
| 来源 | R2 §10.2 step 1 |
| 固定要求 | `target_ids`：使用对应 target 的 `geometry_scope`。`additional_object_names`：使用所列对象自身的 full MESH geometry。 |
| 设计未裁定 | 具体查找、去重、空集合、异常和结果表达（见 DF-PG-06 至 DF-PG-12, DF-PG-23） |

---

## 6. Camera Check 与 Projection Groups 边界

### 6.1 已确立的边界

```text
Camera Check (已锁定):
  — Per-target 独立检查
  — 由 target.camera_check 块触发
  — geometry_scope 内 MESH → per-target union bbox → 8 角点投影
  — 结果写入 per_target_results[i].checks.camera_check
  — required_screen_bbox mixed axial model (X containment, Y coverage)

Projection Groups (待设计):
  — 跨 target + additional_object_names 联合检查
  — 由 spec.projection_groups 数组触发
  — 所有 target_ids 内 target 的 geometry_scope MESH
    + additional_object_names 的 full MESH
    → 联合 union world bbox → 8 角点投影
  — 结果写入 projection_group_results[j]
  — require_camera_outside_world_bbox (Camera Check 没有)
```

### 6.2 共享基础设施

```text
world_to_camera_view
bpy.context.evaluated_depsgraph_get()
obj.evaluated_get(depsgraph)
to_mesh() / to_mesh_clear() (finally block)
evaluated geometry world bbox 计算
camera_object_name 解析 (零匹配/多匹配 → CAMERA_OBJECT_NOT_FOUND, 类型非 CAMERA → CAMERA_TYPE_MISMATCH)
minimum_visible_projected_corner_count 语义
geometry_scope 语义
零顶点 → FAIL + NaN → FAIL per-mesh 合同 (R2 §4.3)
```

### 6.3 边界确认

```text
CAMERA_CHECK_BOUNDARY_CONFIRMED: TRUE
```

Camera Check 已锁定的内容不被本审计重新裁定。Projection Groups 复用但不得重新定义 Camera Check 的合同。

---

## 7. 可直接进入设计的固定需求

以下来自 R2 §10.2 + 当前 Schema，属于明确强制要求：

```text
F-01: projection_groups 为 null 或缺失时，当前 14A Schema 不产生输入错误；空数组被 14A Schema 接受
F-02: 10 个叶子字段的类型和值域 (Schema 已强制)
F-03: group_id 数组内唯一
F-04: target_ids 引用必须指向已知 target_id
F-05: required_screen_bbox 的 4 个字段必须存在且为有限数值
F-06: min_left ≤ max_right, min_bottom ≤ max_top
F-07: 几何来源为 evaluated geometry (R2 §4)
F-08: 任一 evaluated mesh 零顶点或非有限顶点必须导致 FAIL (R2 §4.3)
F-09: 聚合算法: target_ids geometry_scope MESH + additional_object_names full MESH → union world bbox (R2 §10.2)
F-10: 投影函数: world_to_camera_view
F-11: require_camera_outside_world_bbox 为 bool，默认 false
F-12: projection_group_results 按 group_id 排序 (R2 §11.2)
F-13: target_ids within projection_group 保持 spec 顺序 (R2 §11.2)
F-14: 屏幕 bbox 检查只验证几何边界，不验证视觉或美学 (R2 §10.3)
F-15: projection_groups 不影响 per_target_results (不同结果位置)
```

---

## 8. 必须由设计裁定的自由项

```text
DF-PG-01: 结果字典结构 — 键集合、字段名、嵌套层级
DF-PG-02: PASS / FAIL / ERROR / NOT_CHECKED 的精确条件
DF-PG-03: failure_code 命名 (至少: 屏幕 bbox 不满足、mvc 不足、相机在 bbox 内、无评估几何等)
DF-PG-04: error_type 命名和 operation 列表
DF-PG-05: 错误优先级 (哪些 ERROR 优先于哪些 FAIL)
DF-PG-06: target_ids 为空数组的行为 (0 个 target → 联合 bbox 来源只有 additional_object_names?)
DF-PG-07: target_ids 包含重复 target_id → pre-open ERROR 还是运行时去重?
DF-PG-08: additional_object_names 为空数组 → 正常 (只有 target_ids 提供几何)
DF-PG-09: target_ids 和 additional_object_names 都为空 → FAIL、ERROR 还是 pre-open ERROR?
DF-PG-10: additional_object_names 中对象不存在 → ERROR? FAIL? 跳过?
DF-PG-11: additional_object_names 中对象不是 MESH → ERROR? 跳过?
DF-PG-12: additional_object_names 中存在与 target geometry_scope MESH 重复的对象 → 去重还是双倍计入?
DF-PG-13: camera_object_name 解析策略 (复用 Camera Check: 遍历 scene.objects 精确匹配)
DF-PG-14: 相机不在 Scene 对象中 → CAMERA_OBJECT_NOT_FOUND?
DF-PG-15: 相机 type 不是 CAMERA → CAMERA_TYPE_MISMATCH?
DF-PG-16: 相机对象多匹配 → CAMERA_OBJECT_NOT_FOUND? 还是独立 failure code? (Camera Check 使用 CAMERA_OBJECT_NOT_FOUND，Projection Groups 是否复用为设计自由)
DF-PG-17: 联合 bbox 8 角点投影模型 (复用 R1 §19: 8 角点 → world_to_camera_view → z≤0 丢弃 → BEHIND_CAMERA)
DF-PG-18: 联合 bbox 的 mvc > 8 → pre-open ERROR? 还是 mvc 永远 ≤ 8?
DF-PG-19: mvc = 0 → 允许 (与 Camera Check 一致)
DF-PG-20: 联合 bbox 的所有 8 角点都在相机后方 → BEHIND_CAMERA? 整组 FAIL?
DF-PG-21: required_screen_bbox 的轴向语义 — X 轴 containment、Y 轴 minimum coverage (与 Camera Check 一致) 还是全部 containment? 还是全部 coverage?
DF-PG-22: require_camera_outside_world_bbox — outside 的精确定义 (严格外 vs 允许面接触? 逐轴 vs 3D 包含?)
DF-PG-23: 联合 bbox 为空 (所有 source 都无评估几何) — 整组 NOT_CHECKED?
DF-PG-24: 联合 bbox 中零顶点或非有限顶点 — R2 §4.3 已固定要求任一 evaluated mesh 零顶点或非有限顶点 → FAIL。设计需裁定：该固定 FAIL 如何写入投影组结果字典、使用什么 failure_code、如何参与错误优先级和顶层聚合。
DF-PG-25: per-group overall result 的聚合逻辑
DF-PG-26: projection_group_results 与顶层 result (PASS/FAIL/ERROR) 的关系
DF-PG-27: 多个投影组时的错误聚合 ("任一 FAIL → overall FAIL"? "任一 ERROR → overall ERROR"?)
DF-PG-28: Projection Groups 是否需要独立的 pre-open 专用字段关系验证 (类似 Camera Check 的 _validate_camera_check_rules_preopen)
DF-PG-29: 读取次数合同 (是否符合 SCENE_OBJECTS_MATERIALIZATION_COUNT = EXACTLY_ONCE_PER_ENABLED_TARGET)
DF-PG-30: require_camera_outside_world_bbox = true 且 camera 在 bbox 内 → FAIL 还是 ERROR?
DF-PG-31: additional_object_names 的元素类型 (是否允许空字符串? 纯空白?)
DF-PG-32: 四个配置值是否直接源自 spec 禁止硬编码百分比阈值 — Camera Check Design R2 有此裁定，但不能替 Projection Groups 创建既定合同。
```

---

## 9. 文档缺口

```text
DG-PG-01: V4 原始需求不直接包含 projection_groups 概念。
  影响: 低。R2 §10.2 提供了足够的合同基础。
  处理: 设计以 R2 §10.2 为权威来源。

DG-PG-02: projection_groups 的 NOT_CHECKED 条件未在任何合同中定义。
  影响: 中。需要设计裁定。
  类比: Camera Check: camera_check 缺失 → 键不存在；
         根对象前置失败 → NOT_CHECKED with note。

DG-PG-03: projection_groups 的结果字典结构未在任何合同中定义。
  影响: 中。需要设计裁定。

DG-PG-04: failure_code / error_type / operation 列表未定义。
  影响: 中。需要设计裁定。

DG-PG-05: require_camera_outside_world_bbox 的比较语义未精确描述。
  影响: 中。R2 §10.2 只说 "verify camera location is outside the union bbox"。

DG-PG-06: R1 Implementation Contract 不存在 (同 Camera Check 审计发现)。
  影响: 低。R2 §10.2 为 Projection Groups 的完整定义，不依赖 R1。

DG-PG-07: PHASE_3_MINIMUM_DESIGN_SPEC_R1.md 不包含 projection_groups。
  影响: 低。R1 设计规格在 R2 合同之前编写，projection_groups 是 R2 新增的。
  处理: 设计直接以 R2 §10.2 和当前 Schema 为准。

DG-PG-08: required_screen_bbox 的轴向语义未定。
  影响: 高。这是投影组最核心的检查语义。R2 §10.2 只说 "Check screen bbox boundaries against required_screen_bbox"。
  类比: Camera Check 裁定为 HORIZONTAL=containment, VERTICAL=minimum_coverage。
  处理: 设计必须裁定是复用 Camera Check 模型还是使用不同的轴向语义。
```

---

## 10. 真实合同冲突

**无。**

经过对所有权威材料的逐项比对：

- R2 §10.2 独立定义 Projection Groups，不与任何其他合同冲突。
- Camera Check 已锁定边界明确排除了跨 target 联合投影。
- V4 间接需求（essential objects、安全区）与 R2 §10.2 方向一致。
- 不存在两个权威来源对同一事项提出不可调和的强制要求。

```text
TRUE_CONTRACT_CONFLICT_COUNT: 0
```

---

## 11. Camera Check Schema 不一致

Camera Check 原始审计报告记录的 DG-03（Camera Check 与 projection_groups 的 bbox 顺序验证不一致）已在 Camera Check 设计阶段解决：Camera Check 新增了 `_validate_camera_check_rules_preopen` 统一执行 bbox 顺序和 [0,1] 范围验证。Projection Groups 的 Schema 验证 (bbox 顺序 + finite + 非 bool) 与 Camera Check 的 pre-open 验证功能等价。

DF-08（Camera Check Design R2）也确认了："bbox 顺序 → pre-open 验证, 与 projection_groups 统一"。

---

## 12. 范围外内容

```text
OUT_OF_SCOPE:
  — 遮挡 (ray casting / occlusion) — R2 §10.3
  — 视觉质量和美学 — HUMAN_JUDGMENT_ONLY
  — 构图识别 ("是否能认出超市") — HUMAN_JUDGMENT_ONLY
  — 相机排查顺序 — DEFER_REQUIRES_STATE
  — 保存重开持久化
  — 渲染验证
  — 修改 Camera Check 已锁定设计
  — blender_output_artifact_check (独立检查器)
  — dimensions / height / horizontal ratio / landmark / stray objects (NOT_PRESENT_IN_CURRENT_SPEC)
```

---

## 13. 当前生产代码状态

```text
projection_groups 在生产代码中:
  — asset_scene_preflight_core.py: Schema 验证 + build_pass/fail_result 框架 ✓
  — asset_scene_preflight_check.py: 无投影组专用代码 ✗
  — blender_scene_reader.py: 无 _check_projection_groups 函数 ✗
  — 测试: 6 个 core.py Schema 测试 ✓
  — Blender 测试: 0 ✗
  — CPython 运行时测试: 0 ✗
```

---

## 14. 是否足以进入设计

```text
REQUIREMENTS_SUFFICIENT_FOR_DESIGN: TRUE
```

判断依据：

1. **有明确的权威合同来源**：R2 §10.2 完整定义了 10 个叶子字段（7 个直接字段）、5 步算法和基本语义。
2. **Schema 已就位**：14A core 已实现完整的类型和值域验证。
3. **有可复用的设计模式**：Camera Check 已经在同一套基础设施（evaluated geometry、`world_to_camera_view`、camera 查找、bbox 投影、screen bbox 检查、mvc、NOT_CHECKED 模板、error collection、pre-open 验证）上完成并正式锁定。Projection Groups 的本质是 "Camera Check 的多对象联合版本"，可以系统复用车轮。
4. **边界清晰**：与 Camera Check 的分工已经明确且被双方文档确认。
5. **无真实合同冲突**。
6. **文档缺口虽然多（8 项），但都是设计阶段的正常输入**，且 Camera Check 的设计文件可以直接作为裁定模板。

设计阶段需要裁定的 32 项自由项（DF-PG-01 至 DF-PG-32）中，至少 20 项可以在 Camera Check 设计中找到对应裁定并复用或改编。这不是需求不足，而是正常的从合同到设计的转化工作。

```text
TRUE_BLOCKING_ISSUES: 0
RECOMMENDED_NEXT_STAGE: DESIGN_R1
```

---

## 15. 审计统计

```text
TASK_ID: PROJECTION_GROUPS_ORIGINAL_REQUIREMENT_AUDIT
AUDIT_STATUS: COMPLETED
MASTER_MAP_VERSION: R79

FILES_ACTUALLY_READ: 14
AUTHORITATIVE_SOURCE_LIST:
  - ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md §10.2, §10.3, §11.2, §15.2, §16, §17
  - asset_scene_preflight_core.py L223-274, L700-732
  - Blender_固定资产模板路线_新对话交接文档_v4.md (间接)
SUPPORTING_SOURCE_LIST:
  - CAMERA_CHECK_ORIGINAL_REQUIREMENT_AUDIT_REPORT.md
  - CAMERA_CHECK_DESIGN_R2.md
  - GLOBAL_CODEIFICATION_AUDIT_REPORT.md
  - POST_14B_3B_GLOBAL_REMAINING_REQUIREMENTS_AUDIT_R1_REPORT.md
  - PHASE_3_CURRENT_IMPLEMENTATION_COVERAGE_AUDIT.md
  - PROJECT_CODEIFICATION_MASTER_MAP.md R79
  - PHASE_3_MINIMUM_DESIGN_SPEC_R1.md (确认无 projection_groups)
  - test_asset_scene_preflight_core.py (projection_groups 测试段)
  - asset_scene_preflight_check.py (确认无专用代码)
  - blender_scene_reader.py (确认无 _check_projection_groups)

MISSING_EXPECTED_FILES:
  - ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT.md (R1) — 磁盘和 git 历史均不存在

EXISTING_SCHEMA_DIRECT_FIELD_COUNT: 7
EXISTING_SCHEMA_FIELD_COUNT: 10
  (group_id, target_ids, additional_object_names, camera_object_name,
   minimum_visible_projected_corner_count, required_screen_bbox.min_left,
   required_screen_bbox.max_right, required_screen_bbox.min_bottom,
   required_screen_bbox.max_top, require_camera_outside_world_bbox)
AUTHORITATIVE_REQUIREMENT_COUNT: 15 (F-01 至 F-15)
DOCUMENTATION_GAP_COUNT: 8 (DG-PG-01 至 DG-PG-08)
DESIGN_FREEDOM_COUNT: 32 (DF-PG-01 至 DF-PG-32)
TRUE_CONTRACT_CONFLICT_COUNT: 0
OUT_OF_SCOPE_COUNT: 8

CAMERA_CHECK_BOUNDARY_CONFIRMED: TRUE
SCHEMA_AND_REQUIREMENT_RELATION: CONSISTENT — Schema 实现了 R2 §10.2 的类型约束
REQUIREMENTS_SUFFICIENT_FOR_DESIGN: TRUE
TRUE_BLOCKING_ISSUES: 0
AUDIT_BLOCKING_UNRESOLVED_ITEMS: NONE
DESIGN_STAGE_UNRESOLVED_ITEMS:
  32 design freedoms (DF-PG-01 to DF-PG-32)
  8 documentation gaps (DG-PG-01 to DG-PG-08)
RECOMMENDED_NEXT_STAGE: DESIGN_R1
```

---

*Audit complete. Projection Groups has sufficient authoritative basis to proceed to formal design.*
