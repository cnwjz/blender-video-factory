# Material Assignment Design Audit Input Collection Report

```text
TASK_ID: MATERIAL_ASSIGNMENT_DESIGN_AUDIT_INPUT_COLLECTION_R2_CORRECTION
MASTER_MAP_VERSION: R58
DATE: 2026-07-24
TASK_STATUS: COMPLETED_PENDING_INDEPENDENT_CHECK
```

## Collection Scope

```text
COLLECTION_SCOPE: DESIGN_AUDIT_INPUT_COLLECTION
MATERIALS_READ_COMPLETELY: TRUE
```

## Mandatory Files

```text
MANDATORY_FILES_FOUND: 10
MANDATORY_FILES_MISSING: 0
```

### 1. CLAUDE.md

```text
PROJECT_RELATIVE_PATH: CLAUDE.md
SIZE_BYTES: 13687
SHA256: 2BDB43B6F48058677A2652C7075E8503AD959E1D3281505CB04E23D635AFE147
INCLUSION_REASON: 项目执行规则，约束 Material Assignment 实施边界和验证要求
```

### 2. PROJECT_CODEIFICATION_MASTER_MAP.md

```text
PROJECT_RELATIVE_PATH: reviews/PROJECT_CODEIFICATION_MASTER_MAP.md
SIZE_BYTES: 25543
SHA256: C6112DCDE1F2FEA9DCBA49784F7BB44402ED3C5138163A1EEAFFBF39F47769CE
INCLUSION_REASON: R58 权威状态总地图；定义 Material Assignment 当前 SCHEMA_ONLY 状态、锁定边界和唯一下一步
```

### 3. Blender_固定资产模板路线_新对话交接文档_v4.md

```text
PROJECT_RELATIVE_PATH: GLOBAL_CODEIFICATION_AUDIT_INPUTS/01_authoritative_requirements/Blender_固定资产模板路线_新对话交接文档_v4.md
SIZE_BYTES: 46705
SHA256: 8031F8D12D2F9963C1A2DC7975E95BC41874571B39D10559ECA767C799D5502A
INCLUSION_REASON: 原始业务要求权威来源；包含"材质没有丢失"(§九.7.7)、"材质不丢失"(§十四.1.6)、保存重开验证(§十六 L1-D)、保留 Kenney 原生材质(§十三.1)
```

注意：项目根目录存在文件 `Blender_固定资产模板路线_新对话交接文档_v4(6).md`（名称带编号后缀），判断为下载副本。Canonical 路径为上述 `GLOBAL_CODEIFICATION_AUDIT_INPUTS` 目录中的版本。

### 4. PHASE_3_MINIMUM_DESIGN_SPEC_R1.md

```text
PROJECT_RELATIVE_PATH: GLOBAL_CODEIFICATION_AUDIT_INPUTS/02_phase3_design/PHASE_3_MINIMUM_DESIGN_SPEC_R1.md
SIZE_BYTES: 24913
SHA256: A2E9671A838CF0CDC8846FA0123ADD9B1B82AD08903854B96933D853FB6F68DF
INCLUSION_REASON: Phase 3 R1 设计；定义 require_no_missing_materials 在 global 层级(§5.2)、PASS/FAIL/ERROR 语义(§5.5)、字段类型 boolean
```

### 5. ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md

```text
PROJECT_RELATIVE_PATH: GLOBAL_CODEIFICATION_AUDIT_INPUTS/02_phase3_design/ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md
SIZE_BYTES: 20006
SHA256: 7B59E3761756A7EB51B8A6CD6DEB992F1B37FCB21A3C16643B259EC8C9F59380
INCLUSION_REASON: R2 实现合同；定义 material_assignment_presence_check 重命名(§8.2)、slot count + null slot detection 边界(§8.1)、geometry scope MESH 范围(§4)、不验证纹理/节点树/外观(§8.2)
```

### 6. asset_scene_preflight_core.py

```text
PROJECT_RELATIVE_PATH: protocol_guard/phase3_min/asset_scene_preflight_core.py
SIZE_BYTES: 34163
SHA256: 9B5DAA1CF7A8C568F418BF2A8B2A93CAB09B7513EC3B47B47C4896E823982F10
INCLUSION_REASON: 14A Core；包含 schema 验证 _validate_material_assignment (line 361-367)、GEOMETRY_SCOPES 定义 (line 20)、结果构建器、error_boundary、canonicalization、serialization 框架
```

### 7. asset_scene_preflight_check.py

```text
PROJECT_RELATIVE_PATH: protocol_guard/phase3_min/asset_scene_preflight_check.py
SIZE_BYTES: 20140
SHA256: 2B72FE9AAF370FE1E143368DC066B263AFEDC56975B6DCDBB35CD6224632F5EF
INCLUSION_REASON: Blender 入口点；包含 _collect_target_errors、overall 判定、pre-open 验证、reader 调用链；当前不包含 material_assignment 运行时调用
```

### 8. blender_scene_reader.py

```text
PROJECT_RELATIVE_PATH: protocol_guard/phase3_min/blender_scene_reader.py
SIZE_BYTES: 61369
SHA256: A99712EAD731B515992FF11A43BA31F9A9F247B01D0AFA01257D580D85858DE6
INCLUSION_REASON: Blender Scene Reader；包含 _check_root_objects、_aggregate_check_results (ERROR>FAIL>PASS)、_recompute_target_overall；当前无 _check_material_assignment 函数
```

### 9. test_asset_scene_preflight_core.py

```text
PROJECT_RELATIVE_PATH: protocol_guard/phase3_min/tests/test_asset_scene_preflight_core.py
SIZE_BYTES: 44021
SHA256: 9B8F28ECE7D54CC9FE6EEC09D2CD9B691E643430B1342012F91306159B63980E
INCLUSION_REASON: 14A Core 测试；包含 test_material_assignment_valid (line 298-304)，验证 schema 接受 require_material_assignment_presence 布尔字段
```

### 10. test_asset_scene_preflight_blender_scene_basic.py

```text
PROJECT_RELATIVE_PATH: protocol_guard/phase3_min/tests/test_asset_scene_preflight_blender_scene_basic.py
SIZE_BYTES: 119460
SHA256: 4743169662C3A6308C99116158A1EB1453402733635B64C2315DA974A0B9FC15
INCLUSION_REASON: Blender Scene Basic 测试；包含已锁定字段组的运行时测试，可用于确认 material_slots 未被任何现有检查读取
```

## Additional Files

```text
ADDITIONAL_FILES_INCLUDED: 0
```

所有搜索词命中的额外文件（如 ANIMATION_STATE_DESIGN_R5.md、GLOBAL_CODEIFICATION_AUDIT_REPORT.md、14A_FINAL_SOURCE_SNAPSHOT.txt 等）经审核后判断：其包含的信息已由上面 10 份强制材料充分覆盖，无需额外纳入。具体判断：

- `reviews/ANIMATION_STATE_DESIGN_R5.md`: 锁定设计，但 master map R58 §6.1 已完整记录 Animation State 锁定字段和边界，core.py 的 _validate_animation_state 已展示字段结构
- `GLOBAL_CODEIFICATION_AUDIT_INPUTS/03_locked_stage_evidence/*.txt`: 历史快照，非权威当前状态
- 各类 `*_TEST_OUTPUT.txt` 和 UPLOAD_NEXT 下的 ZIP/文件: 历史证据，非 canonical 源文件

## Boundary Evidence Tracing

### 1. 原始业务要求中的"材质不丢失"具体出处

- **V4 交接文档 §九.7.7** (角色库预检): "材质没有丢失" — 作为角色库预检第 7 条
- **V4 交接文档 §十四.1.6** (L1 首帧验收标准——稳定性): "材质不丢失" — 首帧稳定性验收条件
- **V4 交接文档 §十三.1** (灯光与美术原则): "保留 Kenney 原生材质风格" — 约束材质修改范围

### 2. 保存并重新打开后材质不丢失的要求出处

- **V4 交接文档 §十四.1.5**: "保存并重新打开后状态不变" + §十四.1.6: "材质不丢失"
- **V4 交接文档 §十六 L1-D**: "保存后关闭并重新打开 L1_lookdev_v1.blend，验证：...3. 材质不丢失"

### 3. Phase 3 R1 中 require_no_missing_materials 的位置、层级和类型

- **Design Spec R1 §5.2**: `preflight_spec.global.require_no_missing_materials`
  - 层级: `global`（非 per-target）
  - 类型: `boolean`
  - 示例值: `false`
  - 不在 per-target 的 checks 中

### 4. R2 中 slot count、null slot detection 和 geometry scope 边界

- **R2 §8.1**: "Material checks remain: slot count and null slot detection."
- **R2 §8.2**: "Each MESH in geometry scope has at least one material slot; Each material slot has a non-None .material reference"
- **R2 §8.2 排除范围**: 不验证纹理文件存在性、图像数据块加载、着色器节点树连接、材质视觉外观
- **R2 §4**: geometry_scope 通过 evaluated dependency graph 获取，范围由 per-target 的 `geometry_scope` 字段控制 (`SELF_MESH` / `DESCENDANT_MESHES` / `SELF_AND_DESCENDANT_MESHES`)

### 5. R2 中 material_assignment_presence_check 重命名说明

- **R2 §8.2**: "The result field is renamed from `require_materials_present` to `material_assignment_presence_check` to reflect the limited scope."
- 注意: 当前 14A schema 中的配置字段名为 `require_material_assignment_presence`（与 R2 的结果字段名 `material_assignment_presence_check` 不同，一个是配置项一个是结果项）

### 6. 当前 14A schema 实际接受的 Material Assignment 字段

- **asset_scene_preflight_core.py** `_validate_material_assignment` (line 361-367):
  - 字段路径: `target.material_assignment` (optional dict)
  - 接受的子字段: `require_material_assignment_presence` (optional bool, 默认 None 表示不启用)
  - schema 验证: 字段为 None 时跳过；非 dict 时报错；`require_material_assignment_presence` 非 bool 时报错
- **test_asset_scene_preflight_core.py** `test_material_assignment_valid` (line 298-304): 验证 schema 接受 `{"require_material_assignment_presence": True}`

### 7. 当前生产代码是否已经存在任何 Material Assignment 运行时逻辑

- **NOT_FOUND**: 不存在任何 Material Assignment 运行时逻辑
- blender_scene_reader.py: 无 `_check_material_assignment` 函数
- asset_scene_preflight_check.py: `_check_root_objects` 不包含 material_assignment 检查分支
- open_blend_and_get_scene: 不调用任何材质检查
- 当前状态: `SCHEMA_ONLY` — 仅 schema 验证通过，无运行时实现

### 8. geometry_scope 当前实际定义及其与 Hierarchy、Scene membership 的关系

以下仅列出输入材料中直接存在的证据：

```text
GEOMETRY_SCOPE_ENUM_VALUES:
  SELF_MESH
  DESCENDANT_MESHES
  SELF_AND_DESCENDANT_MESHES

来源: asset_scene_preflight_core.py line 20

R2_MATERIAL_BOUNDARY:
  Each MESH in geometry scope has at least one material slot.
  Each material slot has a non-None .material reference.

来源: ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md §8.2

CURRENT_MATERIAL_ASSIGNMENT_RUNTIME_IMPLEMENTATION: NOT_FOUND

GEOMETRY_SCOPE_OBJECT_SELECTION: NOT_FOUND_AS_LOCKED_RUNTIME_DEFINITION
  三个 geometry_scope 枚举值的对象收集算法（哪些 MESH 进入检查范围、
  非 MESH root 的处理、Scene 外后代、分支剪枝、对象身份去重）在
  当前已锁定的输入材料中均未定义。

MATERIAL_ASSIGNMENT_SCENE_MEMBERSHIP_RELATION: NOT_FOUND
  geometry_scope 与 Scene membership 的关系（是否沿袭 Hierarchy 的
  scene.objects identity 过滤、是否独立定义）在输入材料中未明确。
```

R2 §4 描述了 geometry_scope 使用 evaluated dependency graph 获取顶点数据，但该描述针对的是已进入 geometry_scope 的 MESH 如何获取顶点，而非 geometry_scope 本身的对象收集算法。

### 9. 已锁定字段组对 material_slots 的禁止读取或隔离边界

- 审计结论: 所有 6 个已锁定字段组 (hierarchy, standing, facing, visibility, rotation, animation_state) 的运行时检查均不读取 `material_slots`
- Animation State scope guard (I5) 仅保护 `_check_animation_state` 函数内的 `scene.objects`、`obj.name`、`obj.animation_data`、`action.name`、`obj.data.pose_position`、`scene.frame_current` 访问
- `material_slots` 属性当前未被任何生产代码读取
- `material_slots` 当前未被现有生产检查读取。未来允许读取的位置、Scope Guard 边界和集成方式均待后续设计决定。

### 10. 当前结果结构、overall 聚合和 ERROR 收集框架所在文件

- **asset_scene_preflight_core.py**: `_base_result()` (line 701-714) 定义顶层结果结构；`build_pass_result`/`build_fail_result`/`build_error_result` (line 717-740) 构建三种结果；`error_boundary()` (line 745-766) 捕获所有异常并转为 ERROR；`canonicalize_phase3_result()` (line 640-680) 规范化输出；`serialize_result_line()` (line 685-696) 序列化
- **asset_scene_preflight_check.py**: `_collect_target_errors()` (line 261-375) 收集所有 ERROR 目标的稳定错误消息；`_validate_and_open_spec()` (line 404-486) 主流程；overall 判定逻辑 (line 468-486)
- **blender_scene_reader.py**: `_aggregate_check_results()` (line 124-131) 子结果聚合 (ERROR > FAIL > PASS)；`_recompute_target_overall()` (line 1596-1607) 重算 per-target overall
- 聚合优先级: ERROR > FAIL > PASS > NOT_CHECKED（跨所有层级一致）

## Candidate Conflicts and Gaps

以下为已识别但本轮不裁决的候选问题：

```text
CANDIDATE_01: require_no_missing_materials (R1 global) vs material_assignment_presence_check (R2 per-target result) 的字段层级关系
CANDIDATE_02: R2 合同结果字段名 material_assignment_presence_check vs 当前 schema 配置字段名 require_material_assignment_presence 的命名不一致
CANDIDATE_03: R1 global.require_no_missing_materials (boolean) 与 R2 per-target slot count + null slot detection 的范围差异
CANDIDATE_04: "材质不丢失" (V4) 的语义范围——是否仅等于 assignment presence (R2)，或包含纹理/图像数据块完整性
CANDIDATE_05: 保存重开要求 (V4 §十四.1.5) 是否属于 DEFER_REQUIRES_STATE（当前无可靠执行日志）
CANDIDATE_06: geometry_scope 的对象收集算法（三个枚举值的准确 MESH 集合、非 MESH root 行为、Scene 外后代、分支剪枝、对象身份去重）——当前 GEOMETRY_SCOPE_OBJECT_SELECTION 和 MATERIAL_ASSIGNMENT_SCENE_MEMBERSHIP_RELATION 均为 NOT_FOUND
CANDIDATE_07: 无材质槽 (slot count = 0) 和空材质槽 (slot.material is None) 是否使用同一 failure code
CANDIDATE_08: 属性读取异常 (material_slots 访问失败) 是否进入 ERROR
CANDIDATE_09: 材质槽读取次数、缓存和稳定顺序
CANDIDATE_10: 多个 MESH (DESCENDANT_MESHES / SELF_AND_DESCENDANT_MESHES) 的结果结构和聚合方式
CANDIDATE_11: material_assignment 在 reader 中的集成位置——animation_state 当前采用 _check_root_objects 之后独立调用的方式；material_assignment 是否复用、调整或采用其他集成位置，仍待后续原始需求审计与设计决定
CANDIDATE_12: "保留 Kenney 原生材质风格" (V4 §十三.1) 是否可代码化——当前归类 HUMAN_JUDGMENT_ONLY
```

## Input Sufficiency

```text
INPUT_SUFFICIENCY: SUFFICIENT_FOR_ORIGINAL_REQUIREMENT_AUDIT
TRUE_BLOCKING_ISSUES: 0
```

充分性理由：
- 10 份强制材料全部定位并完整读取
- 原始业务要求出处 (V4 交接文档) 中"材质不丢失"的三个引用点已定位
- R1 字段定义 (global.require_no_missing_materials) 已定位
- R2 合同边界 (slot count, null slot detection, geometry scope, 重命名) 已定位
- 当前 schema 验证代码已定位
- 当前生产实现状态已确认 (SCHEMA_ONLY, 无运行时逻辑)
- geometry_scope 定义已定位
- 已锁定字段组隔离边界已分析
- 结果框架文件已定位
- 12 个候选冲突和缺口已记录但不裁决
- 0 份强制材料缺失
- 0 个真实阻断点

充分性仅代表可以开始下一轮原始需求审计，不代表 Material Assignment 要求已完成审计。
```

## Frozen Files Integrity

```text
FROZEN_FILES_CHECKED: 7
FROZEN_FILES_ALL_MATCH: TRUE
FROZEN_FILES_MODIFIED: 0
MASTER_MAP_MODIFIED: FALSE
PRODUCTION_CODE_MODIFIED: FALSE
EXISTING_TESTS_MODIFIED: FALSE
```
