# Ground Contact 原始需求审计报告

```text
TASK_ID: GROUND_CONTACT_ORIGINAL_REQUIREMENT_AUDIT
MASTER_MAP_VERSION: R74
TASK_TYPE: ORIGINAL_REQUIREMENT_AUDIT
DATE: 2026-07-26
CORRECTION: R2 — 补齐 R1 容差/非有限值/副作用规则，统一分类，重算计数
TASK_STATUS: COMPLETED_PENDING_INDEPENDENT_CHECK
```

## 1. 任务身份

```text
TASK_ID: GROUND_CONTACT_ORIGINAL_REQUIREMENT_AUDIT
TASK_TYPE: ORIGINAL_REQUIREMENT_AUDIT
AUDIT_RESULT_PENDING: FALSE
```

## 2. 实际读取文件

| # | 文件 | 类型 |
|---|------|------|
| 1 | `GLOBAL_CODEIFICATION_AUDIT_INPUTS/01_authoritative_requirements/Blender_固定资产模板路线_新对话交接文档_v4.md` | AUTHORITATIVE_BUSINESS_REQUIREMENT |
| 2 | `GLOBAL_CODEIFICATION_AUDIT_INPUTS/02_phase3_design/PHASE_3_MINIMUM_DESIGN_SPEC_R1.md` | DESIGN_SPEC_REFERENCE |
| 3 | `GLOBAL_CODEIFICATION_AUDIT_INPUTS/02_phase3_design/ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md` | AUTHORITATIVE_IMPLEMENTATION_CONTRACT |
| 4 | `protocol_guard/phase3_min/asset_scene_preflight_core.py` | LOCKED_SCHEMA |
| 5 | `protocol_guard/phase3_min/blender_scene_reader.py` | CURRENT_PRODUCTION_CODE |
| 6 | `protocol_guard/phase3_min/asset_scene_preflight_check.py` | CURRENT_PRODUCTION_ENTRY |
| 7 | `protocol_guard/phase3_min/tests/test_asset_scene_preflight_core.py` | SCHEMA_TEST |
| 8 | `reviews/PROJECT_CODEIFICATION_MASTER_MAP.md` | AUTHORITY_STATE (R74) |
| 9 | `CLAUDE.md` | PROJECT_RULES |

## 3. 权威来源和优先级

| Priority | Source | Role |
|----------|--------|------|
| 1 | Blender 固定资产模板路线 新对话交接文档 v4 | AUTHORITATIVE_BUSINESS_REQUIREMENT |
| 2 | ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md | AUTHORITATIVE_IMPLEMENTATION_CONTRACT |
| 3 | PHASE_3_MINIMUM_DESIGN_SPEC_R1.md | DESIGN_SPEC_REFERENCE |
| 4 | asset_scene_preflight_core.py L343-348 | LOCKED_SCHEMA |
| 5 | blender_scene_reader.py + asset_scene_preflight_check.py | CURRENT_RUNTIME_STATE |

## 4. 原始业务需求

### 4.1 强制要求 (AUTHORITATIVE)

| # | 来源 | 行 | 原文 |
|---|------|----|------|
| BR-01 | 交接文档 v4 §7.5 | 720 | "人物脚底接近地面" |
| BR-02 | 交接文档 v4 §9 L1-A | 1389 | "脚底接近地面" |
| BR-03 | 交接文档 v4 §9 固定约束 | 812 | "人物脚底最低点与地面误差在项目容差内" |
| BR-04 | 交接文档 v4 §9 L1-B 通过条件 | 1236 | "顾客脚底接地" |
| BR-05 | 交接文档 v4 §10 L1-D | 1456 | "顾客脚底接地" |
| BR-06 | 交接文档 v4 §9 L1-A 执行内容 | 1189 | "检查层级、站立状态、face +Y、1.75 高度、脚底接触和游离 Mesh" |
| BR-07 | 交接文档 v4 §10 排查顺序 | 1395 | "地面接触"在排查顺序中排第5位 |

### 4.2 参考事实 (REFERENCE, 非强制要求)

| # | 来源 | 行 | 内容 |
|---|------|----|------|
| RF-01 | 交接文档 v4 §8 | 740 | "脚底高度和地面接触数据"由 bpy 脚本读取 |

### 4.3 需求总结

```text
BUSINESS_REQUIREMENT:
  人物脚底最低点与地面的垂直距离必须在项目容差内。
  适用于所有角色，属于强制业务要求。
  在地面接触未通过时，不得优先调整相机参数。

CODE_ENFORCEABLE:
  YES — 通过 evaluated geometry 计算 world-space 最低 Z 座标，
  与配置的 ground_z 比较。

HARD_REQUIREMENT: TRUE
```

## 5. 当前 Schema 合同

来源: `asset_scene_preflight_core.py` L343-348

### 5.1 字段路径

```text
FIELD_PATH: targets[i].ground_contact
TYPE: optional dict (None / absent = not configured)
SUBFIELDS:
  ground_z: optional finite number (rejects bool, NaN, Inf)
  ground_contact_tolerance: optional finite number >= 0 (rejects bool, NaN, Inf)
```

### 5.2 Schema 事实

| # | 事实 |
|---|------|
| SF-01 | ground_contact 是 per-target 可选 dict |
| SF-02 | ground_z 和 ground_contact_tolerance 各自独立可选 |
| SF-03 | 没有 all-or-nothing 规则 |
| SF-04 | 两个子字段均为 absent/null 时，Schema 接受 |
| SF-05 | 0.0 tolerance 是有效值 |
| SF-06 | bool 不被接受为数字 |
| SF-07 | NaN 和 Inf 被拒绝 |
| SF-08 | 缺失 ground_contact 的 target 由 Schema 正常接受 |

## 6. Implementation Contract R2

### 6.1 明确规定

| # | 规定 | 依据 |
|---|------|------|
| IC-01 | 主要几何源 = evaluated dependency graph | §4.1 |
| IC-02 | depsgraph = bpy.context.evaluated_depsgraph_get() | §4 示例 |
| IC-03 | evaluated = obj.evaluated_get(depsgraph) | §4 示例 |
| IC-04 | mesh = evaluated.to_mesh() | §4 示例 |
| IC-05 | 顶点通过 evaluated.matrix_world 变换到世界空间 | §4.2 |
| IC-06 | evaluated.to_mesh_clear() 放 finally | §4.2 |
| IC-07 | 零顶点 → FAIL with NO_EVALUATED_GEOMETRY | §4.3 |
| IC-08 | to_mesh/to_mesh_clear 异常 → ERROR | §4.3 |
| IC-09 | 顶点含 NaN → FAIL | §4.3 |
| IC-10 | depsgraph 求值失败 → ERROR | §4.3 |
| IC-11 | Ground Contact 使用 evaluated geometry lowest_z | §14 行 485 |

### 6.2 未明确规定

| # | 缺口 |
|---|------|
| DG-01 | 未给出 Ground Contact 专用 operation 名称、failure_code、结果字典键集 |

## 7. Phase 3 Design Spec R1

### 7.1 与 Ground Contact 直接相关

| # | 内容 | 行 | 分类 |
|---|------|----|------|
| DS-01 | 示例 spec: ground_z: 0.0, ground_contact_tolerance: 0.02 在 target 顶层 | 156-157 | SUPERSEDED_OR_STALE_DRAFT — 字段层级已被 14A Schema 嵌套化统一 |
| DS-02 | 示例输出: ground_contact: {result: PASS, actual_lowest_z: 0.001} | 192 | DESIGN_REFERENCE_NOT_BINDING — 输出键名候选，未锁定 |
| DS-03 | 测试: "Lowest Z too far from ground_z → FAIL" | 478 | DESIGN_REFERENCE_NOT_BINDING — 说明 FAIL 条件 |
| DS-04 | 容差: ground_contact_tolerance: 0.02 | 157 | DESIGN_REFERENCE_NOT_BINDING — 示例值 |

### 7.2 R1 通用规则（适用于 Ground Contact）

| # | 规则 | R1 出处 | 分类 |
|---|------|---------|------|
| TR-01 | 所有数值比较使用绝对差值: `|actual - expected| <= tolerance` | §5.9 | ALREADY_DEFINED — 适用于所有数值检查，包括 Ground Contact |
| TR-02 | actual 为 NaN → FAIL, note "actual_is_NaN" | §5.9 | ALREADY_DEFINED — R2 §4.3 也确认了 NaN 顶点 |
| TR-03 | actual 为 Infinity → FAIL, note "actual_is_infinite" | §5.9 | ALREADY_DEFINED |
| TR-04 | 等于 tolerance 时 PASS | §5.9 公式 | ALREADY_DEFINED — `<= tolerance` 公式已明确 |
| TR-05 | 禁止保存: MUST NOT call save_as_mainfile or any save operation | §5.10 | ALREADY_DEFINED |
| TR-06 | 不得修改对象 transform, visibility, material | §5.10 | ALREADY_DEFINED |
| TR-07 | 不得增删对象 | §5.10 | ALREADY_DEFINED |
| TR-08 | 不得修改渲染设置或场景相机 | §5.10 | ALREADY_DEFINED |
| TR-09 | 不得渲染 | §5.10 | ALREADY_DEFINED |
| TR-10 | PASS = 所有检查在容差内; FAIL = 至少一项超出容差 | §5.5 | ALREADY_DEFINED |

## 8. 当前运行时实现状态

| # | 事实 |
|---|------|
| RT-01 | blender_scene_reader.py 中不存在任何 ground_contact 相关函数 |
| RT-02 | asset_scene_preflight_check.py 中 _collect_target_errors 没有 ground_contact 分支 |
| RT-03 | open_blend_and_get_scene 中 per_target_results checks 没有 ground_contact 键 |
| RT-04 | overall 聚合不包含 ground_contact |
| RT-05 | 退出码判定不包含 ground_contact |
| RT-06 | depsgraph, evaluated_get, to_mesh, to_mesh_clear 在生产代码中全部 ABSENT (14B_2A 锁定证据) |

## 9. 材料差异和分类

| # | 差异 | 分类 |
|---|------|------|
| DIF-01 | ground_z 字段层级: target.ground_contact.ground_z (Schema) vs target.ground_z (R1 Spec) | SUPERSEDED_OR_STALE_DRAFT |
| DIF-02 | 两字段独立可选 vs R1 示例假设同时存在 | DESIGN_FREEDOM |
| DIF-03 | "脚底接地" vs "lowest_z" — 语义一致 | COMPATIBLE_DIFFERENT_GRANULARITY |

## 10. 与既有锁定能力的边界

| 能力 | 关系 |
|------|------|
| geometry_scope (target 级选项) | EXISTING_LOCKED_REUSABLE_FACT |
| Scene membership identity 过滤 | EXISTING_LOCKED_REUSABLE_FACT |
| _check_root_objects | EXISTING_LOCKED_REUSABLE_FACT — MUST NOT MODIFY |
| _recompute_target_overall | EXISTING_LOCKED_REUSABLE_FACT — 自动纳入 |
| _collect_target_errors | EXISTING_LOCKED_REUSABLE_FACT — 遵循既有模式 |
| depsgraph / evaluated_get / to_mesh / to_mesh_clear / mesh.vertices | REQUIRES_NEW_IMPLEMENTATION — 当前全部 ABSENT |

## 11. 设计阶段待裁定事项

| # | 问题 | 分类 |
|---|------|------|
| DM-01 | ground_z 缺失时的行为和结果 | DESIGN_MUST_DECIDE |
| DM-02 | tolerance 缺失时的行为和结果 | DESIGN_MUST_DECIDE |
| DM-03 | 只有 ground_z 没有 tolerance: 检查是否启用？结果？ | DESIGN_MUST_DECIDE |
| DM-04 | 只有 tolerance 没有 ground_z: 检查是否启用？结果？ | DESIGN_MUST_DECIDE |
| DM-05 | 两个字段都为 absent/null 时的行为和结果 | DESIGN_MUST_DECIDE |
| DM-06 | geometry_scope 来源（复用 target.geometry_scope 还是独立配置） | DESIGN_MUST_DECIDE |
| DM-07 | 检查范围：只 MESH / 所有 geometry scope 对象 | DESIGN_MUST_DECIDE |
| DM-08 | 多个 MESH 的聚合方式（取所有顶点最低 Z / per-mesh / 其他） | DESIGN_MUST_DECIDE |
| DM-09 | PASS/FAIL/ERROR/NOT_CHECKED 完整矩阵 | DESIGN_MUST_DECIDE |
| DM-10 | 结果字典精确键集合（ground_z, actual_lowest_z, tolerance 等） | DESIGN_MUST_DECIDE |
| DM-11 | failure_code 命名 | DESIGN_MUST_DECIDE |
| DM-12 | ERROR type 和 operation 枚举 | DESIGN_MUST_DECIDE |
| DM-13 | 属性读取次数和缓存合同 | DESIGN_MUST_DECIDE |
| DM-14 | Scope Guard 合同（保护 depsgraph/to_mesh/matrix_world 等） | DESIGN_MUST_DECIDE |
| DM-15 | Blender 5.1.2 临时场景验证矩阵 | DESIGN_MUST_DECIDE |
| DM-16 | 实施阶段拆分 (I1-I4B-E) | DESIGN_MUST_DECIDE |

## 12. 审计结论

```text
AUDIT_RESULT: REQUIREMENTS_SUFFICIENT_FOR_DESIGN
TRUE_CONTRACT_CONFLICTS: 0
TRUE_BLOCKING_ISSUES: 0

NEXT_RECOMMENDED_ACTION:
  可以开始 GROUND_CONTACT_DESIGN_R1，前提是用户授予正式设计授权。
```

### 判定依据

**原始业务需求充分**: 交接文档 v4 有 7 条强制要求明确要求"脚底接触地面"。需求可代码化（evaluated geometry lowest_z）。

**Schema 已就绪**: 14A Schema 已定义 ground_z 和 ground_contact_tolerance，两者独立可选。字段层级已被 14A 统一嵌套化。

**Implementation Contract R2 覆盖核心算法**: depsgraph → evaluated_get → to_mesh → world-space vertex → aggregate → to_mesh_clear 已被明确规定。零顶点、NaN、异常边界已有合同。唯一文档缺口是 operation/failure_code 未命名（DG-01）— 这属于设计阶段可合法制定的内容，不是阻断性合同缺失。

**R1 通用规则直接适用**: 绝对差值比较公式、NaN/Infinity FAIL、等于容差时 PASS（`<=`）、副作用禁令（不保存/不修改/不渲染）均为 ALREADY_DEFINED。Ground Contact 设计可以直接引用这些规则。

**运行时尚未开始**: 6 条运行时事实全部确认 Ground Contact 未实现，depsgraph/to_mesh 等数据源为 ABSENT。

**无合同冲突**: 所有材料一致指向同一个语义——检查最低点是否在 ground_z 的容差范围内。

## 13. 计数摘要

```text
AUTHORITATIVE_REQUIREMENT_COUNT: 7 (BR-01 to BR-07)
AUTHORITATIVE_REFERENCE_FACT_COUNT: 1 (RF-01)
SCHEMA_FACT_COUNT: 8 (SF-01 to SF-08)
IMPLEMENTATION_CONTRACT_FACT_COUNT: 11 (IC-01 to IC-11)
CURRENT_RUNTIME_FACT_COUNT: 6 (RT-01 to RT-06)
DESIGN_MUST_DECIDE_ENTRY_COUNT: 16 (DM-01 to DM-16)
DESIGN_FREEDOM_COUNT: 16 (same as DESIGN_MUST_DECIDE — all items are design-stage decisions)
DOCUMENTATION_GAP_COUNT: 1 (DG-01: R2 未给出 Ground Contact 专用 operation/failure_code 命名)
TRUE_CONTRACT_CONFLICT_COUNT: 0
TRUE_BLOCKING_ISSUES: 0
SUPERSEDED_OR_STALE_COUNT: 1 (DIF-01)
COMPATIBLE_DIFFERENT_GRANULARITY_COUNT: 1 (DIF-03)
```

## 14. 文件修改和执行记录

```text
PRODUCTION_PROGRESS_THIS_ROUND: FALSE
WHY_THIS_NON_PRODUCTION_WORK_IS_NECESSARY:
  Ground Contact 当前只有 Schema，原始业务要求、旧设计规格、R2 合同和当前 Schema 的关系尚未经过正式审计。
  设计前必须先确认需求是否充分，并识别真实合同冲突、文档缺口和合法设计自由。

STOP_LOSS_STATUS:
  本轮是该审计报告唯一允许的集中修正轮。

WHAT_DECISION_IT_UNLOCKS:
  确认 Ground Contact 是否具有可靠、内部一致、可复算的设计输入。

EXIT_CONDITION:
  报告覆盖完整，分类一致，所有计数可由编号条目复算，然后立即停止。

PRODUCTION_CODE_MODIFIED: FALSE
TESTS_MODIFIED: FALSE
MASTER_MAP_MODIFIED: FALSE
CLAUDE_MD_MODIFIED: FALSE
PYTEST_EXECUTED: FALSE
BLENDER_EXECUTED: FALSE
REAL_PROJECT_BLEND_OPENED: FALSE
RENDER_EXECUTED: FALSE
ZIP_CREATED: FALSE
```

## 15. Machine-readable Summary

```text
GROUND_CONTACT_REQUIREMENT_AUDIT_RESULT: REQUIREMENTS_SUFFICIENT_FOR_DESIGN
GROUND_CONTACT_AUDIT_RESULT_PENDING: FALSE
GROUND_CONTACT_TRUE_CONTRACT_CONFLICTS: 0
GROUND_CONTACT_DOCUMENTATION_GAPS: 1
GROUND_CONTACT_DESIGN_FREEDOMS: 16
GROUND_CONTACT_DESIGN_MUST_DECIDES: 16
GROUND_CONTACT_RUNTIME_IMPLEMENTED: FALSE
GROUND_CONTACT_DATA_SOURCES:
  bpy.context.evaluated_depsgraph_get
  obj.evaluated_get(depsgraph)
  evaluated.to_mesh() / evaluated.to_mesh_clear()
  mesh.vertices
  evaluated.matrix_world
GROUND_CONTACT_LOCKED_BOUNDARIES:
  geometry_scope (REUSABLE)
  _check_root_objects (REUSABLE, MUST NOT MODIFY)
  _recompute_target_overall (REUSABLE, AUTO)
  _collect_target_errors (REUSABLE, PATTERN)
GROUND_CONTACT_R1_GENERIC_RULES_APPLICABLE:
  Absolute difference tolerance (TR-01)
  NaN/Infinity FAIL (TR-02, TR-03)
  Equal-to-tolerance PASS (TR-04)
  Side-effect prohibitions (TR-05 to TR-09)
GROUND_CONTACT_NEXT_RECOMMENDED_TASK: GROUND_CONTACT_DESIGN_R1 (requires user authorization)
```
