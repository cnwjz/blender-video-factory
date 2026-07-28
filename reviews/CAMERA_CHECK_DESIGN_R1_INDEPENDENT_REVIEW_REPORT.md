# Camera Check Design R1 Independent Review Report

**TASK_ID**: CAMERA_CHECK_DESIGN_R1_INDEPENDENT_REVIEW
**TASK_TYPE**: DESIGN_INDEPENDENT_REVIEW
**MASTER_MAP_VERSION**: R77
**DATE**: 2026-07-26
**DESIGN_UNDER_REVIEW**: reviews/CAMERA_CHECK_DESIGN_R1.md

---

## 1. 独立复验结论

```text
INDEPENDENT_REVIEW_STATUS: ALL_CHECKS_PASS
BLOCKING_DESIGN_DEFECT_COUNT: 0
DIRECT_DESIGN_DEFECT_COUNT: 1
NON_BLOCKING_CLARITY_ISSUE_COUNT: 3
TRUE_BLOCKING_ISSUES: 0
```

设计 R1 满足 `ALL_CHECKS_PASS` 标准：14 项 DF 全部唯一决定、3 项 DG 全部关闭、算法与 R1/R2 合同一致、结果字典唯一、failure_code 优先级唯一、ERROR operation 穷尽、集成完整、Scope Guard 最小调整、测试矩阵充分、实施拆分符合精简流程。

1 个 DIRECT_DESIGN_DEFECT（读取次数表与缓存策略矛盾）可在设计锁定前通过单行修正消除。3 个 NON_BLOCKING_CLARITY_ISSUE 不阻断设计通过。

---

## 2. 实际读取文件

| # | 路径 | 读取范围 |
|---|------|---------|
| 1 | `CLAUDE.md` | 全文 |
| 2 | `reviews/PROJECT_CODEIFICATION_MASTER_MAP.md` | 全文 (R77) |
| 3 | `reviews/CAMERA_CHECK_ORIGINAL_REQUIREMENT_AUDIT_REPORT.md` | 全文 (R3 Correction) |
| 4 | `reviews/CAMERA_CHECK_DESIGN_R1.md` | 全文 (1127 行) |
| 5 | `GLOBAL_CODEIFICATION_AUDIT_INPUTS/02_phase3_design/ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md` | §4, §10.1, §10.2, §10.3 |
| 6 | `protocol_guard/phase3_min/asset_scene_preflight_core.py` | L390-408 (_validate_camera_check) |
| 7 | `protocol_guard/phase3_min/blender_scene_reader.py` | 结构浏览 (验证 _collect_geometry_scope_objects 存在和签名) |
| 8 | `protocol_guard/phase3_min/asset_scene_preflight_check.py` | 结构浏览 (验证 _collect_target_errors 和 _validate_and_open_spec) |
| 9 | `reviews/GROUND_CONTACT_DESIGN_R2.md` | 参考 (evaluated geometry, error patterns) |
| 10 | `reviews/MATERIAL_ASSIGNMENT_DESIGN_R1.md` | 参考 (per-target integration) |

R1 Implementation Contract (ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT.md):
磁盘和 git 历史均不存在。复验使用任务指定的 §19 算法进行核对。

---

## 3. R1/R2 合并复验

```text
R1_R2_MERGE_VALID: TRUE
```

| 合同项 | R1 § | R2 § | 设计 § | 判定 |
|--------|------|------|--------|------|
| Geometry source | §12 | §4 | §8 | REPLACED correctly: R2 evaluated depsgraph |
| Per-target projection | §19 | §10.1 | §10 | RETAINED algorithm, bbox source updated to evaluated geometry |
| Global projection groups | — | §10.2 | §4 excluded | Correctly excluded from Camera Check scope |
| Screen bbox limitations | — | §10.3 | §11 | Geometric margins only, as per R2 |
| Raw bound_box | §12 | — | §4, §19.2 | Correctly forbidden |

验证通过：
- R1 §12 raw bound_box 没有被恢复 ✓
- R1 §19 投影算法完整保留 ✓
- R2 §4 evaluated geometry 作为唯一几何来源 ✓
- R2 §4.2 "Aggregate all world-space vertices across all geometry-scope meshes" 正确实施 ✓
- R2 §4.3 零顶点/NaN/to_mesh_clear 合同正确映射到设计 ✓

---

## 4. DF/DG 完整性矩阵

```text
ALL_DF_DECISIONS_VALID: TRUE
ALL_DG_CLOSED: TRUE
```

### 4.1 DF-01 至 DF-14 逐项验证

| ID | 设计决定 | 位置 | 判定 | 备注 |
|----|---------|------|------|------|
| DF-01 | scene.objects, exact case-sensitive | §6.1 | VALID | 与 root_object_name 解析一致 |
| DF-02 | FAIL CAMERA_OBJECT_NOT_FOUND | §6.1 | VALID | capture 缺失 + 歧义 |
| DF-03 | FAIL CAMERA_TYPE_MISMATCH | §6.1 | VALID | 独立 failure_code |
| DF-04 | z <= 0 → discard | §10.2 | VALID | 与 R1 §19 步骤 3 一致 |
| DF-05 | boundary → included as visible | §10.3 | VALID | 边界包含语义确定 |
| DF-06 | mvc > 8 → pre-open ERROR | §5.3 | VALID | 永不满足的配置在 pre-open 阻断 |
| DF-07 | empty geometry → FAIL NO_EVALUATED_GEOMETRY | §8.1 | VALID | 与 Ground Contact 一致 |
| DF-08 | bbox 顺序 → pre-open | §5.3 | VALID | 与 projection_groups 统一 |
| DF-09 | bbox [0,1] → pre-open | §5.3 | VALID | world_to_camera_view x/y ∈ [0,1] |
| DF-10 | 4 pre-open rules | §5.3 | VALID | 穷尽 |
| DF-11 | mvc max = 8 | §5.3 | VALID | 8-corner bbox |
| DF-12 | 7 failure_codes, precedence | §14 | VALID | 互不冲突 |
| DF-13 | CAMERA_CHECK_COMPUTATION_ERROR + 17 ops | §15 | VALID | 遵循命名风格 |
| DF-14 | containment, 4 edges inward, spec-sourced | §11 | VALID | 禁止硬编码百分比 |

### 4.2 DG-01 至 DG-03 逐项验证

| ID | 设计关闭方式 | 位置 | 判定 |
|----|------------|------|------|
| DG-01 | NOT_CHECKED 条件: config absent + root precondition | §12.1 | CLOSED |
| DG-02 | 11 种结果字典形态, 精确键集 | §13 | CLOSED |
| DG-03 | bbox 顺序 pre-open 统一, 无需结果层处理 | §5.3 | CLOSED |

---

## 5. Schema / Pre-open 复验

```text
SCHEMA_CONTRACT_VALID: TRUE
```

验证通过：
- camera_check 缺失/null → key not created ✓ (与 Animation State/Material Assignment 惯例一致)
- 14A Core _validate_camera_check 不可修改 ✓ (6 leaf fields 保持原样)
- 新增 _validate_camera_check_rules_preopen 在 asset_scene_preflight_check.py ✓
- mvc <= 8 pre-open ✓
- bbox [0,1] pre-open ✓
- bbox 顺序 pre-open ✓
- 等于边界时合法 ✓ (bbox value == 0 or == 1 → valid)
- 错误文本精确 ✓ (INVALID_CAMERA_CHECK_RULE_VALUE / INVALID_CAMERA_CHECK_RULE_RELATION)

---

## 6. Camera 查找复验

```text
CAMERA_LOOKUP_CONTRACT_VALID: TRUE
```

验证通过：
- scene.objects 遍历 ✓ (非 bpy.data.objects, 非 bpy.context.scene)
- 精确区分大小写 ✓
- 同名歧义 → CAMERA_OBJECT_NOT_FOUND ✓ (共用 failure_code，但 reason 可由 spec 端诊断。与 root 同名歧义的处理一致 — 都归入 ERROR/NOT_FOUND 而不强制拆分)
- type != CAMERA → CAMERA_TYPE_MISMATCH ✓
- obj.name / obj.type 读异常 → RESOLVE_CAMERA_OBJECT ERROR ✓

关于同名歧义与缺失共用 failure_code：设计 §6.1 明确说明两者都归入 CAMERA_OBJECT_NOT_FOUND，原因是"场景中同名 Camera 歧义本身是场景错误"。这与 root_object check 的做法不完全一致（root 同名歧义是 ERROR AMBIGUOUS_ROOT_OBJECT_NAME，不是 FAIL）。但 Camera Check 在这里有意简化：Camera 不是 per-target 的 identity 对象，同名歧义 Camera 的场景本身就是配置错误，从 Camera Check 的角度 FAIL 是合理的。这个设计选择明确且有理由支持。

---

## 7. Geometry 与 Projection 复验

```text
PROJECTION_ALGORITHM_VALID: TRUE
```

### 7.1 Evaluated Geometry

验证通过：
- target.geometry_scope 复用 ✓
- _collect_geometry_scope_objects 复用 ✓
- evaluated_depsgraph_get → evaluated_get → to_mesh → vertices → to_mesh_clear ✓
- matrix_world @ vertex.co 世界空间变换 ✓
- 零顶点 → continue (aggregate later) ✓
- 非有限顶点 → non_finite_found=True, continue ✓
- 空 geometry scope → FAIL NO_EVALUATED_GEOMETRY ✓
- 全零顶点且无非有限 → FAIL NO_EVALUATED_GEOMETRY ✓
- 全非有限 → FAIL NON_FINITE_EVALUATED_VERTEX ✓
- to_mesh_clear in finally ✓
- return-in-finally: cleanup ERROR > main result ✓

### 7.2 Projection Algorithm

验证通过 (对照 R1 §19 7 步顺序):
1. 8 world-space bbox corners ✓
2. world_to_camera_view(scene, camera_obj, corner_ws) ✓
3. z <= 0 → discard ✓ (z == 0 明确归入 discard — §10.2 有理由)
4. all z <= 0 → FAIL BEHIND_CAMERA ✓
5. front_corners → screen bbox ✓
6. visible count >= mvc ✓
7. screen bbox 边界检查 ✓

关键确认：
- visible count 只按 z > 0 计算 ✓
- x/y 越界不影响 visible count ✓ (各自独立 FAIL)
- 非有限 x/y/z → ERROR PROJECT_WORLD_CORNER ✓
- 判断使用未舍入值 ✓ (结果保留原始值)

---

## 8. required_screen_bbox 数学复验

```text
BBOX_COMPARISON_VALID: TRUE
```

四条比较式已验证一致：
```
screen_min_x >= min_left     (左边界 → containment inward)
screen_max_x <= max_right    (右边界 → containment inward)
screen_min_y >= min_bottom   (底边界 → containment inward)
screen_max_y <= max_top      (顶边界 → containment inward)
```

模型: CONTAINMENT (安全区包含) — target screen bbox 必须在 required_screen_bbox 内部。

四个方向使用统一语义 ✓。不区分 X/Y 的安全区/覆盖区模型 ✓。

边界等式：screen_min_x == min_left → PASS ✓ (包含边界)

百分比映射自洽：
- CR-05 "顶部空白 ≤ 15%" → max_top = 0.85, 检查 screen_max_y <= 0.85 ✓
- CR-06 "左右边距 ≥ 4%" → min_left = 0.04, max_right = 0.96, 检查 screen_min_x >= 0.04 且 screen_max_x <= 0.96 ✓

BOUNDARY_VALUES_SOURCE: SPEC_REQUIRED_SCREEN_BBOX ✓
HARDCODED_PERCENTAGE_VALUES_ALLOWED: FALSE ✓

---

## 9. 结果字典与 failure_code 复验

```text
RESULT_DICT_CONTRACT_VALID: TRUE
FAILURE_PRECEDENCE_VALID: TRUE
```

### 9.1 结果字典

| # | 形态 | 键数 | 判定 |
|---|------|------|------|
| 1 | NOT_CHECKED (key not created) | 0 | VALID |
| 2 | NOT_CHECKED (root precondition) | 2 | VALID: result, note |
| 3 | PASS | 9 | VALID: 9 个字段齐全 |
| 4 | FAIL CAMERA_OBJECT_NOT_FOUND | 3 | VALID: result, failure_code, camera_object_name |
| 5 | FAIL CAMERA_TYPE_MISMATCH | 4 | VALID: +actual_type |
| 6 | FAIL NO_EVALUATED_GEOMETRY | 3 | VALID: result, failure_code, evaluated_mesh_names |
| 7 | FAIL NON_FINITE_EVALUATED_VERTEX | 3 | VALID: 同结构 |
| 8 | FAIL BEHIND_CAMERA | 6 | VALID: +camera +projection counts |
| 9 | FAIL INSUFFICIENT_VISIBLE | 7 | VALID: +mvc |
| 10 | FAIL SCREEN_BBOX_BOUNDARY_EXCEEDED | 9 | VALID: +actual+required bboxes |
| 11 | ERROR | 4 | VALID: result, error_type, operation, note |

确认：11 种形态, 每种键集精确 ✓
确认：不同 FAIL 路径无临时附加字段 ✓
确认：RESULT_DICT_FORM_COUNT = 11 ✓

### 9.2 failure_code 优先级

```
ERROR > CAMERA_OBJECT_NOT_FOUND > CAMERA_TYPE_MISMATCH
> NO_EVALUATED_GEOMETRY > NON_FINITE_EVALUATED_VERTEX
> BEHIND_CAMERA > INSUFFICIENT_VISIBLE_PROJECTED_CORNERS
> SCREEN_BBOX_BOUNDARY_EXCEEDED
> PASS
```

验证：优先级线性唯一 ✓, 与算法执行顺序一致 ✓

同时出现多 FAIL:
- Camera missing + geometry empty → CAMERA_OBJECT_NOT_FOUND (4a > 4c) ✓
- Geometry empty + bbox exceed → NO_EVALUATED_GEOMETRY (4c > 4g) ✓
- Behind camera + insufficient corners → BEHIND_CAMERA (4e > 4f) ✓

---

## 10. ERROR Operation 复验

```text
ERROR_OPERATION_SET_VALID: TRUE
```

17 operations 已验证穷尽：

| 类别 | Operations | 覆盖 |
|------|-----------|------|
| Camera | RESOLVE_CAMERA_OBJECT | obj.name/type 读异常 |
| Geometry scope | READ_SCENE_OBJECTS, RESOLVE_ROOT_OBJECT, READ_ROOT_CHILDREN, READ_DESCENDANT_CHILDREN, READ_DESCENDANT_TYPE | _collect 路径 + root 解析 |
| Evaluated | GET_EVALUATED_DEPSGRAPH, EVALUATED_GET, TO_MESH, READ_EVALUATED_MATRIX_WORLD, READ_MESH_VERTICES, TRANSFORM_VERTEX_TO_WORLD_SPACE, TO_MESH_CLEAR | 完整 depsgraph 数据链 |
| Projection | IMPORT_WORLD_TO_CAMERA_VIEW, PROJECT_WORLD_CORNER | import + per-corner call |
| Screen bbox | COMPUTE_SCREEN_BBOX, COMPARE_SCREEN_BBOX | min/max 计算 + 比较 |

确认：无 UNKNOWN / GENERAL_ERROR / COMPUTE 等宽泛 operation ✓
确认：每个 operation 对应唯一异常边界 ✓

---

## 11. 读取次数复验

```text
READ_COUNT_CONTRACT_VALID: TRUE
DIRECT_DESIGN_DEFECT: 1 — scene.objects MAX_READS 矛盾
```

### 11.1 发现的设计缺陷 (DIRECT_DESIGN_DEFECT)

**DEFECT-01**: §16.1 读取次数表中 `scene.objects MAX_READS = 2` 与 §16.2 缓存策略 `scene.objects materialization: 最多 1 次` 矛盾。

**位置**: §16.1 L750; §16.2 L767

**具体内容**:
- §16.1: `scene.objects | 2 | root resolution + camera lookup (可合并为1)`
- §16.2: `scene.objects materialization: 最多 1 次 (resolve root + find camera 共享)`

**影响**: 实施时无法确定 scene.objects 读取 1 次还是 2 次。

**推荐修正**: 将 §16.1 的 scene.objects MAX_READS 改为 1，删除 "(可合并为1)"。理由: `_check_camera_check` 在自己的函数体内调用 `list(scene.objects)` 恰好一次，同时用于 camera lookup 和构建 `scene_member_ids` / `scene_materialization_index` 传给 `_collect_geometry_scope_objects`。这与 Ground Contact 的 `_check_ground_contact` 模式完全一致——该函数也在自己体内物化 scene.objects 恰好一次。

**分级**: DIRECT_DESIGN_DEFECT（单行修正即可消除，不影响设计的整体有效性）

### 11.2 其余读取次数验证

| API | MAX_READS | 判定 |
|-----|-----------|------|
| obj.name | N+1 | VALID — scene.objects 遍历 |
| obj.type (camera) | 1 | VALID |
| _collect_geometry_scope_objects | 1 | VALID |
| depsgraph | 1 | VALID |
| evaluated_get / to_mesh / mw / vertices / to_mesh_clear | M per | VALID |
| world_to_camera_view | 8 | VALID — 8 corners |

---

## 12. 集成与 Scope Guard 复验

```text
INTEGRATION_CONTRACT_VALID: TRUE
SCOPE_GUARD_CONTRACT_VALID: TRUE
```

### 12.1 集成

验证通过：
- `_check_camera_check(scene, target, per_target_result)` ✓
- 调用顺序: after Ground Contact, before Collection Rules (L825-828) ✓
- 未配置返回 None → key not created ✓
- _recompute_target_overall 通用遍历自动覆盖 ✓
- _collect_target_errors 有精确 CAMERA_CHECK_COMPUTATION_ERROR 输出 ✓
- NOT_CHECKED 填充 → 3 个 _check_root_objects 模板 ✓

非阻断发现：§18.5 伪代码中变量名 `gc = checks.get("camera_check", {})` 与注释 "变量名使用 cc" 不一致。Ground Contact 在同一函数中已使用 `gc` 变量名。实施时应使用 `cc` 避免变量名冲突。→ NON_BLOCKING_CLARITY_ISSUE

### 12.2 Scope Guard

验证通过：
- 从 file-level string ban 移除 world_to_camera_view ✓
- AST-level per-function: _check_camera_check <= 1 call site ✓
- 其他函数: 0 call sites ✓
- asset_scene_preflight_check.py: 0 call sites ✓
- test_asset_scene_preflight_blender_visibility_i2.py: 从 string ban 移除 ✓
- 禁止 bpy.context.scene / object.bound_box ✓
- 不解除其他字段组保护 ✓

---

## 13. 测试矩阵与实施拆分复验

```text
TEST_MATRIX_VALID: TRUE
```

### 13.1 CPython 测试 (~40 scenarios)

覆盖验证：
- 配置缺失/null → key not created ✓
- Pre-open: mvc=-1/0/8/9/True, bbox NaN/Inf/bool/order/[0,1]/boundary ✓
- Root 前置条件: 4 种 NOT_CHECKED ✓
- Camera 查找: found/not found/ambiguous/type mismatch/ERROR ✓
- 结果字典: 11 种形态 assert_dict_equal ✓
- failure_code 优先级: 3 组 ✓
- operation 映射: 主要 ERROR 路径 ✓
- 读取次数 contract ✓
- _collect_target_errors: ERROR 收集 ✓
- 总体聚合: ERROR/FAIL/PASS ✓

### 13.2 Blender 测试 (~20 scenarios)

覆盖验证：
- Perspective + Orthographic camera ✓
- All/partial/zero front-facing corners ✓
- 4 boundary FAIL + 4 exact boundary PASS ✓
- Multiple MESH union bbox ✓
- 3 geometry_scope values ✓
- Modifier (evaluated geometry change) ✓
- Zero-vertex, non-finite edge cases ✓
- Two targets share camera ✓
- Entry PASS/FAIL/ERROR ✓

### 13.3 实施拆分

```
I1: Production + pre-open + CPython tests + Scope Guard ✓
I2: Blender 5.1.2 validation ✓
E: Final regression ✓
DEFAULT: NO_REPORT / NO_ZIP / NO_MANIFEST / NO_SHA256 / DIRECT_UPLOAD ✓
```

---

## 14. 问题清单

### BLOCKING_DESIGN_DEFECT (0)

无。

### DIRECT_DESIGN_DEFECT (1)

| ID | 描述 | 位置 | 推荐修正 |
|----|------|------|---------|
| DEFECT-01 | scene.objects MAX_READS 在 §16.1 写为 2 但在 §16.2 写为 1 | §16.1 L750, §16.2 L767 | §16.1 MAX_READS 改为 1, 删除 "(可合并为1)" |

### NON_BLOCKING_CLARITY_ISSUE (3)

| ID | 描述 | 位置 |
|----|------|------|
| NB-01 | §18.5 伪代码变量名 `gc` 与注释 "变量名使用 cc" 不一致，且 `gc` 与 Ground Contact 的变量名冲突 | §18.5 L852 |
| NB-02 | §13.10 注释 "NON_FINITE 也包含 evaluated_mesh_names 与 NO_EVALUATED_GEOMETRY 同结构" — 两者确实都是 3 键但键名不同（NO_EVALUATED_GEOMETRY 不含 mvc 相关字段），表述可更精确 | §13.10 L660 |
| NB-03 | §10.2 中 `DM-04` 应为 `DF-04`（Design Freedom numbering, 非 Decision Matrix） | §10.2 L381 |

---

## 15. 机器可读摘要

```text
TASK_ID: CAMERA_CHECK_DESIGN_R1_INDEPENDENT_REVIEW
TASK_TYPE: DESIGN_INDEPENDENT_REVIEW
MASTER_MAP_VERSION: R77

INDEPENDENT_REVIEW_STATUS: ALL_CHECKS_PASS
R1_R2_MERGE_VALID: TRUE
ALL_DF_DECISIONS_VALID: TRUE
ALL_DG_CLOSED: TRUE
PROJECTION_ALGORITHM_VALID: TRUE
BBOX_COMPARISON_VALID: TRUE
RESULT_DICT_CONTRACT_VALID: TRUE
FAILURE_PRECEDENCE_VALID: TRUE
ERROR_OPERATION_SET_VALID: TRUE
READ_COUNT_CONTRACT_VALID: TRUE (with 1 DIRECT_DESIGN_DEFECT)
INTEGRATION_CONTRACT_VALID: TRUE
SCOPE_GUARD_CONTRACT_VALID: TRUE
TEST_MATRIX_VALID: TRUE

BLOCKING_DESIGN_DEFECT_COUNT: 0
DIRECT_DESIGN_DEFECT_COUNT: 1 (DEFECT-01: scene.objects MAX_READS contradiction)
NON_BLOCKING_CLARITY_ISSUE_COUNT: 3 (NB-01, NB-02, NB-03)
TRUE_BLOCKING_ISSUES: 0

FILES_ACTUALLY_READ: 10
FILES_MODIFIED: reviews/CAMERA_CHECK_DESIGN_R1_INDEPENDENT_REVIEW_REPORT.md (NEW)
DESIGN_MODIFIED: FALSE
PRODUCTION_CODE_MODIFIED: FALSE
TESTS_MODIFIED: FALSE
MASTER_MAP_MODIFIED: FALSE
TESTS_RUN: NONE
PYTEST_EXIT_CODE: NOT_APPLICABLE
BLENDER_EXECUTED: FALSE
REAL_PROJECT_BLEND_OPENED: FALSE
ZIP_CREATED: FALSE
MANIFEST_CREATED: FALSE

UPLOAD_NEXT_FILE: reviews/CAMERA_CHECK_DESIGN_R1_INDEPENDENT_REVIEW_REPORT.md
```

---

*Independent review complete. Design R1 passes all checks. One direct design defect (read count contradiction) requires a single-line fix before formal lock. Three non-blocking clarity issues. Zero blocking defects. Implementation NOT authorized — pending user formal lock approval.*
