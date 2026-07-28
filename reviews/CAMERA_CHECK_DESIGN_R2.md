# Camera Check Runtime Design R2

```text
DOCUMENT_ID: CAMERA_CHECK_DESIGN
DESIGN_VERSION: R2
TASK_ID: CAMERA_CHECK_DESIGN_R2_CORRECTION
SOURCE_DESIGN_VERSION: R1
TARGET_DESIGN_VERSION: R2
MASTER_MAP_VERSION: R77
DATE: 2026-07-26
DESIGN_STATUS: FORMALLY_LOCKED
FORMALLY_LOCKED: TRUE
FORMAL_LOCK_DATE: 2026-07-26
FORMAL_LOCK_APPROVAL: USER_EXPLICITLY_APPROVED
IMPLEMENTATION_AUTHORIZED: FALSE
DESIGN_AUTHORIZATION: USER_EXPLICITLY_AUTHORIZED
DESIGN_AUTHORIZATION_DATE: 2026-07-26

RECOVERED_R1_SOURCE_USED: TRUE
RECOVERED_R1_SOURCE_VALIDATION:
  VERIFIED_FROM_TASK_SPEC_EMBEDDED_SECTION_19
RECOVERED_R1_SOURCE_PROVENANCE:
  GPT_PRETASK_EXTRACTION_FROM_USER_LIBRARY_COPY
R1_SOURCE_DIRECTLY_READ_BY_CLAUDE_CODE:
  FALSE
R1_PROJECT_DISK_STATUS: MISSING
R1_GIT_HISTORY_STATUS: MISSING
```

## 1. 权威来源与优先级

```text
PRIORITY_1: Blender_固定资产模板路线_新对话交接文档_v4.md
  — AUTHORITATIVE_REQUIREMENT:
    §十·1 "使用 world_to_camera_view 完成数学投影与裁切检查"
    §十·3 "通过 bbox 与 world_to_camera_view 计算摄像机构图"
    §十二 "essential objects 裁切数量 = 0, 所有人物完整进入安全区,
           顶部空白 ≤ 15%, 底部空白 ≤ 15%, 左右安全边距 ≥ 4%"

PRIORITY_2: asset_scene_preflight_core.py lines 390-408
  — LOCKED_SCHEMA:
    _validate_camera_check — 6 leaf fields:
    camera_object_name (non-empty string)
    minimum_visible_projected_corner_count (non-bool integer >= 0)
    required_screen_bbox.min_left, .max_right, .min_bottom, .max_top
    (each: non-bool finite number)

PRIORITY_3: ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md
  — AUTHORITATIVE_IMPLEMENTATION_CONTRACT:
    §4 Evaluated Geometry Contract (replaces R1 §12)
      §4.2 Algorithm — aggregate all world-space vertices
      §4.3 Edge Cases — zero vertices → FAIL NO_EVALUATED_GEOMETRY,
                       NaN vertices → FAIL
    §10.1 Per-Target Projection (retains R1 §19, replaces raw bound_box
          with evaluated geometry)
    §10.2 Global Projection Groups (separate checker, not Camera Check)
    §10.3 Projection Limitations (geometric margins only)

PRIORITY_4: R1 Implementation Contract §19 (Recovered, embedded in task spec)
  — RETAINED_BY_R2_§10_1:
    8-corner bbox projection algorithm:
    (1) Get 8 world-space bbox corners
    (2) Project each via world_to_camera_view
    (3) Discard corners with projected_z <= 0
    (4) If zero corners remain → FAIL with BEHIND_CAMERA
    (5) Compute screen bbox from projected_x/projected_y of survivors
    (6) Check against required_screen_bbox
    (7) Check surviving corner count >= minimum_visible_projected_corner_count
  — SUPERSEDED_PARTS:
    R1 §12 raw bound_box → replaced by R2 §4 evaluated geometry

PRIORITY_5: Current production code — blender_scene_reader.py, asset_scene_preflight_check.py
  — CURRENT_RUNTIME_FACT: _check_camera_check does not exist; no entry integration

PRIORITY_6: Locked design conventions:
  — GROUND_CONTACT_DESIGN_R2.md (evaluated geometry, error patterns, cleanup contract)
  — MATERIAL_ASSIGNMENT_DESIGN_R1.md (per-target integration, error collection)
  — ANIMATION_STATE_DESIGN_R5.md (independent per-target check, scope guard)
  — COLLECTION_RULES_DESIGN_R1.md (pre-open validation, ERROR aggregation)
  — ROTATION_DESIGN_R3.md (result structure, ERROR mapping, read count)

DESIGN_INPUT:
  — CAMERA_CHECK_ORIGINAL_REQUIREMENT_AUDIT_REPORT.md (R3 Correction)
    AUDIT_RESULT: REQUIREMENTS_SUFFICIENT_FOR_DESIGN
    TRUE_CONTRACT_CONFLICTS: 0
    DESIGN_FREEDOMS: 14 (DF-01 to DF-14)
    DOCUMENTATION_GAPS: 3 (DG-01 to DG-03)
    AUDIT_COVERAGE_GAP_COUNT: 1
```

## 2. R1/R2 合并与替换矩阵

```text
TOPIC                        | R1 §      | R2 §      | RESULT
-----------------------------|-----------|-----------|---------------------------
Geometry source              | §12       | §4        | REPLACED: R2 evaluated geometry
Per-target projection        | §19       | §10.1     | RETAINED + MODIFIED: algorithm
                             |           |           |   retained, bbox source changed
                             |           |           |   to evaluated geometry corners
Global projection groups     | —         | §10.2     | NEW: separate checker
Screen bbox limitations      | —         | §10.3     | NEW: geometric margins only
World-space bbox algorithm   | §12       | §4.2      | REPLACED: evaluated depsgraph
Zero-vertex contract         | —         | §4.3      | FAIL NO_EVALUATED_GEOMETRY
NaN vertex contract          | —         | §4.3      | FAIL per Section 13
Result/exit code             | §20       | §13, §15  | SUPERSEDED: R2 framework
```

## 3. 设计目标

1. 为 Camera Check 字段组定义唯一、完整、可独立实现和测试的运行时设计。
2. 所有 14 项审计 DF 和 3 项 DG 均给出唯一最终决定。
3. 结果字典键集合唯一，支持 `assert_dict_equal` 精确断言。
4. 所有异常路径有唯一 operation，所有 FAIL 有唯一 failure_code，错误优先级唯一。
5. 配置、前置条件、算法、结果、清理、集成和副作用边界全部封闭。
6. R2 §4.3 的零顶点和 NaN 合同完整实施 — 任一 mesh 违规即 FAIL，无延迟聚合。
7. required_screen_bbox 采用轴向混合语义：X 轴 containment，Y 轴 minimum coverage。
8. 四个配置值源自 spec，禁止硬编码百分比阈值。

## 4. 固定范围与明确非目标

```text
FIXED_SCOPE:
  — Schema 6 leaf fields (see §5)
  — target.geometry_scope 复用
  — R2 §4 evaluated geometry 数据链
  — R2 §4.3 zero-vertex → FAIL + NaN → FAIL per-mesh contract
  — R1 §19 投影算法 (8 角点 → projection → z-filter → screen bbox → mvc)
  — required_screen_bbox mixed axial model (X=h containment, Y=v coverage)
  — 结果键名: checks.camera_check
  — 独立 per-target 检查，不跨 target 聚合

EXPLICITLY_EXCLUDED:
  — 遮挡关系 (ray casting / occlusion)
  — 视觉质量、超市识别
  — 跨 target 联合构图 → Projection Groups
  — additional_object_names → Projection Groups
  — 相机是否在 essential objects 联合 bbox 内 → Projection Groups
  — 保存重开 persistence
  — 渲染结果
  — 历史 Draft "camera_visible" boolean (SUPERSEDED_OR_STALE_DRAFT)

MUST_NOT_MODIFY:
  — 14A Core schema (_validate_camera_check)
  — _check_root_objects 的返回结构
  — Hierarchy 到 Collection Rules 的生产代码和测试
  — 任何已锁定设计或锁定记录
```

## 5. 配置和启用语义

### 5.1 启用判定

```text
ENABLED:
  target.camera_check is not None AND isinstance(camera_check, dict)
  — 14A Schema 保证块存在时 6 个叶子字段已通过类型和值域验证

DISABLED:
  target.camera_check is None
  → checks dict 中不存在 "camera_check" 键
  → Camera Check 完全不参与该 target 的 overall 聚合
```

### 5.2 输出键存在性

```text
camera_check 缺失/null:
  checks dict 中不存在 "camera_check" 键

根对象前置条件失败 (ROOT_OBJECT_NOT_FOUND / AMBIGUOUS_ROOT_OBJECT_NAME
/ ROOT_LOOKUP_ERROR / ROOT_OBJECT_TYPE_MISMATCH):
  checks.camera_check = {"result": "NOT_CHECKED", "note": "<前置失败原因>"}
  与 Ground Contact、Material Assignment 一致。
```

### 5.3 Pre-open 专用字段关系验证

除 14A Schema 的 `_validate_camera_check` 之外，新增 `_validate_camera_check_rules_preopen`：

```text
RULE_1: minimum_visible_projected_corner_count <= 8
  ERROR: INVALID_CAMERA_CHECK_RULE_VALUE: mvc > 8

RULE_2: required_screen_bbox.min_left <= required_screen_bbox.max_right
  ERROR: INVALID_CAMERA_CHECK_RULE_RELATION: min_left > max_right

RULE_3: required_screen_bbox.min_bottom <= required_screen_bbox.max_top
  ERROR: INVALID_CAMERA_CHECK_RULE_RELATION: min_bottom > max_top

RULE_4: all four bbox values in [0, 1]
  ERROR: INVALID_CAMERA_CHECK_RULE_VALUE: bbox value out of [0, 1]

RATIONALE:
  world_to_camera_view 的 projected x/y 可以小于 0 或大于 1，
  这正是目标位于屏幕外时的正常数学结果。
  要求 required_screen_bbox 的四个配置值位于 [0,1]，
  是因为这些值描述屏幕归一化范围内的业务边界，
  不代表 projected x/y 永远位于 [0,1]。
```

DF-06: mvc > 8 → pre-open ERROR
DF-08: bbox 顺序 → pre-open 验证, 与 projection_groups 统一
DF-09: bbox [0,1] 范围 → pre-open 验证
DF-10: extra pre-open rules → 上述四条
DF-11: mvc max = 8

## 6. Camera 查找合同

### 6.1 解析策略

```text
LOOKUP_METHOD: 遍历 scene.objects，精确区分大小写匹配 camera_object_name
RATIONALE: 与 root_object_name 解析 (_check_root_objects) 一致

ALGORITHM:
  camera_obj = None
  match_count = 0
  for obj in scene_objects_ordered:
      if obj.name == camera_object_name:
          match_count += 1
          if match_count == 1:
              camera_obj = obj
          else:
              camera_obj = None

  if match_count == 0:
      → FAIL (failure_code: CAMERA_OBJECT_NOT_FOUND)
  elif match_count > 1:
      → FAIL (failure_code: CAMERA_OBJECT_NOT_FOUND)
  elif camera_obj.type != 'CAMERA':
      → FAIL (failure_code: CAMERA_TYPE_MISMATCH,
              actual_type: camera_obj.type)

  # obj.name / obj.type 读取异常:
  → ERROR (operation: RESOLVE_CAMERA_OBJECT)

NOTE: scene_objects_ordered 为 scene.objects 恰好物化一次的结果
      (见 §16 读取次数合同)。
```

DF-01: 解析策略 → scene.objects 精确区分大小写
DF-02: Camera 不在目标 Scene → FAIL CAMERA_OBJECT_NOT_FOUND
DF-03: type != CAMERA → FAIL CAMERA_TYPE_MISMATCH

### 6.2 禁止项

```text
FORBIDDEN:
  bpy.context.scene
  bpy.data.objects.get()
  bpy.data.cameras
  scene.camera
```

## 7. Root 和 Geometry Scope 前置条件

### 7.1 Root 前置条件（只读）

```text
READ_EXISTING_CHECKS:
  checks.object_exists.result
  checks.object_type.result

PRECONDITION_MAP:
  object_exists.result == "FAIL"              → NOT_CHECKED: ROOT_OBJECT_NOT_FOUND
  object_exists.error_type == "AMBIGUOUS_ROOT_OBJECT_NAME" → NOT_CHECKED: AMBIGUOUS_ROOT_OBJECT_NAME
  object_exists.result == "ERROR"             → NOT_CHECKED: ROOT_LOOKUP_ERROR
  object_type.result == "FAIL"                → NOT_CHECKED: ROOT_OBJECT_TYPE_MISMATCH

AGREEMENT: 与 Ground Contact、Material Assignment、Collection Rules 完全一致
```

### 7.2 Geometry Scope

```text
REUSE: target.geometry_scope (14A Core validated)

SCOPE_VALUES:
  SELF_MESH
  DESCENDANT_MESHES
  SELF_AND_DESCENDANT_MESHES

REUSE_HELPER: _collect_geometry_scope_objects (blender_scene_reader.py)
  — 已锁定，Ground Contact 和 Material Assignment 共用
  — Camera Check 复用同一调用
```

## 8. Evaluated Geometry 算法

### 8.1 算法（R2 §4.2 + §4.3）

```text
1. depsgraph = bpy.context.evaluated_depsgraph_get()
   (ERROR GET_EVALUATED_DEPSGRAPH on failure)

2. mesh_objects = _collect_geometry_scope_objects(...)
   (ERROR on RuntimeError from _collect)

3. if len(mesh_objects) == 0:
       → FAIL (failure_code: NO_EVALUATED_GEOMETRY)

4. pending_zero_vertex = False
   pending_non_finite = False
   evaluated_mesh_names = []
   all_world_vertices = []

   for mesh_obj, mesh_name in mesh_objects:
       evaluated = mesh_obj.evaluated_get(depsgraph)
       (ERROR EVALUATED_GET on failure)

       mesh = evaluated.to_mesh()
       (ERROR TO_MESH on failure)

       evaluated_mesh_names.append(mesh_name)

       try:
           mw = evaluated.matrix_world
           (ERROR READ_EVALUATED_MATRIX_WORLD on failure)

           if len(mesh.vertices) == 0:
               pending_zero_vertex = True
               continue
               # §4.3: zero vertices → FAIL NO_EVALUATED_GEOMETRY
               # Still execute to_mesh_clear() in finally

           for v in mesh.vertices:
               vertex_co = v.co
               (ERROR READ_MESH_VERTICES on failure)

               world_co = mw @ vertex_co
               (ERROR TRANSFORM_VERTEX_TO_WORLD_SPACE on failure)

               if not (isfinite(world_co.x) and isfinite(world_co.y)
                       and isfinite(world_co.z)):
                   pending_non_finite = True
                   continue
                   # §4.3: NaN/Inf → FAIL NON_FINITE_EVALUATED_VERTEX
                   # Still execute to_mesh_clear() in finally

               all_world_vertices.append(world_co)
       finally:
           evaluated.to_mesh_clear()
           (ERROR TO_MESH_CLEAR on failure — overrides ALL pending results)

5. if pending_non_finite:
       → FAIL (failure_code: NON_FINITE_EVALUATED_VERTEX)
   elif pending_zero_vertex:
       → FAIL (failure_code: NO_EVALUATED_GEOMETRY)
   elif len(all_world_vertices) == 0:
       → FAIL (failure_code: NO_EVALUATED_GEOMETRY)

6. Continue to bbox computation (§9)
```

### 8.2 清理合同

```text
to_mesh_clear() 在 finally 块中执行。

如果 to_mesh_clear 抛异常:
  → ERROR (operation: TO_MESH_CLEAR)
  该 ERROR 覆盖 finally 块之前的任何 pending result
  — 无论 pending_zero_vertex、pending_non_finite、all_world_vertices 状态
  (与 Ground Contact R2 合同一致: return-in-finally pattern)

主异常 + cleanup 异常同时发生:
  cleanup ERROR 优先 → 返回 TO_MESH_CLEAR ERROR
```

### 8.3 零顶点与 NaN/Inf 合同 (R2 §4.3)

```text
ZERO_VERTEX_POLICY:
  任一 geometry-scope MESH 的 evaluated mesh 为零顶点
  → target 产生 pending FAIL: NO_EVALUATED_GEOMETRY
  仍必须先执行该 mesh 对应的 to_mesh_clear()
  如果 cleanup 成功 → 返回 FAIL
  如果 cleanup 失败 → 返回 TO_MESH_CLEAR ERROR (覆盖 pending FAIL)

NON_FINITE_VERTEX_POLICY:
  任一 geometry-scope evaluated vertex 的世界空间 x/y/z 为 NaN/Inf/-Inf
  → target 产生 pending FAIL: NON_FINITE_EVALUATED_VERTEX
  仍必须先执行该 mesh 对应的 to_mesh_clear()
  如果 cleanup 成功 → 返回 FAIL
  如果 cleanup 失败 → 返回 TO_MESH_CLEAR ERROR (覆盖 pending FAIL)

PRECEDENCE (同时出现零顶点和非有限顶点):
  NON_FINITE_EVALUATED_VERTEX > NO_EVALUATED_GEOMETRY

evaluated_mesh_names:
  按确定性顺序记录所有成功完成 evaluated_get + to_mesh 的 scope MESH 名称，
  包括产生零顶点或非有限顶点的 evaluated mesh。
```

DF-07: 空 geometry scope → FAIL NO_EVALUATED_GEOMETRY

## 9. World BBox 8 角点算法

```text
INPUT: all_world_vertices (list of mathutils.Vector in world space)
       — 保证非空且全部有限 (validated by §8.1 steps 4-5)

1. min_x = min(v.x for v in all_world_vertices)
   max_x = max(v.x for v in all_world_vertices)
   min_y = min(v.y for v in all_world_vertices)
   max_y = max(v.y for v in all_world_vertices)
   min_z = min(v.z for v in all_world_vertices)
   max_z = max(v.z for v in all_world_vertices)

2. 8 corners (world space):
   (min_x, min_y, min_z)  (max_x, min_y, min_z)
   (min_x, max_y, min_z)  (max_x, max_y, min_z)
   (min_x, min_y, max_z)  (max_x, min_y, max_z)
   (min_x, max_y, max_z)  (max_x, max_y, max_z)

NO DEDUP: 即使 bbox 在某些轴退化（如 plane），8 个角点始终生成
```

## 10. Projection 算法

### 10.1 步骤（R1 §19 保留顺序）

```text
from bpy_extras.object_utils import world_to_camera_view

1. projected_corners = []
   for corner_ws in WORLD_BBOX_CORNERS:
       projected = world_to_camera_view(scene, camera_obj, corner_ws)
       (ERROR PROJECT_WORLD_CORNER on failure or non-finite result)
       projected_corners.append((projected.x, projected.y, projected.z))

2. front_corners = [(x, y) for (x, y, z) in projected_corners if z > 0]

3. if len(front_corners) == 0:
       → FAIL (failure_code: BEHIND_CAMERA)

4. screen_min_x = min(x for (x, y) in front_corners)
   screen_max_x = max(x for (x, y) in front_corners)
   screen_min_y = min(y for (x, y) in front_corners)
   screen_max_y = max(y for (x, y) in front_corners)
   (ERROR COMPUTE_SCREEN_BBOX on failure)

5. actual_screen_bbox = {
       "min_x": screen_min_x, "max_x": screen_max_x,
       "min_y": screen_min_y, "max_y": screen_max_y,
   }

6. screen bbox requirement check (see §11)
   if screen bbox does not satisfy required_screen_bbox:
       → FAIL (failure_code: SCREEN_BBOX_REQUIREMENT_NOT_MET)

7. visible_count = len(front_corners)
   minimum_visible = target.camera_check.minimum_visible_projected_corner_count
   if visible_count < minimum_visible:
       → FAIL (failure_code: INSUFFICIENT_VISIBLE_PROJECTED_CORNERS)

8. → PASS
```

### 10.2 z == 0 处理

```text
DF-04:
  projected_z == 0 → 视为在相机后方（与 z < 0 同等处理，丢弃）
  RATIONALE: z == 0 位于相机平面上或极其接近
```

### 10.3 边界包含规则

```text
DF-05:
  角点恰好位于屏幕边界 (如 x == 0, x == 1, y == 0, y == 1):
  视为可见，参与 front_corners 计数和 screen bbox 计算
```

### 10.4 非有限投影

```text
world_to_camera_view 返回 NaN/Inf 的 x, y 或 z:
  → ERROR (operation: PROJECT_WORLD_CORNER)
```

## 11. required_screen_bbox 精确比较式

### 11.1 轴向混合语义

```text
HORIZONTAL_MODEL: SAFE_MARGIN_CONTAINMENT
  目标投影的 X 轴 bbox 必须在安全区域内。
  X 轴字段表达允许目标所在的安全区域。

VERTICAL_MODEL: MINIMUM_COVERAGE
  目标投影的 Y 轴 bbox 必须达到的最低画面覆盖范围。
  Y 轴字段表达目标必须达到的最低画面覆盖。

required_screen_bbox 的字段名称沿用锁定 Schema，
但四个字段并不共同表达一个普通的 containment rectangle。
X 轴和 Y 轴使用不同的业务语义。
```

### 11.2 四条数学比较式

```text
LEFT:
  screen_min_x >= required_screen_bbox.min_left
  → 目标左边界在左侧安全边距之后

RIGHT:
  screen_max_x <= required_screen_bbox.max_right
  → 目标右边界在右侧安全边距之后

BOTTOM:
  screen_min_y <= required_screen_bbox.min_bottom
  → 目标下边界位于或低于底部空白上限

TOP:
  screen_max_y >= required_screen_bbox.max_top
  → 目标上边界至少达到顶部空白下限
```

### 11.3 边界等式

```text
screen_min_x == min_left → PASS (包含安全边界)
screen_max_x == max_right → PASS (包含安全边界)
screen_min_y == min_bottom → PASS (恰好到达覆盖边界)
screen_max_y == max_top → PASS (恰好到达覆盖边界)
```

### 11.4 FAIL 条件

```text
Any of:
  screen_min_x < min_left
  screen_max_x > max_right
  screen_min_y > min_bottom
  screen_max_y < max_top
→ FAIL (failure_code: SCREEN_BBOX_REQUIREMENT_NOT_MET)

名称 SCREEN_BBOX_REQUIREMENT_NOT_MET 同时覆盖两种语义:
  — "超过安全边界" (X 轴: min_x too far left, max_x too far right)
  — "未达到覆盖阈值" (Y 轴: min_y too high, max_y too low)
```

### 11.5 百分比约束的映射 (CR-05, CR-06)

```text
BOUNDARY_VALUES_SOURCE: SPEC_REQUIRED_SCREEN_BBOX
HARDCODED_PERCENTAGE_VALUES_ALLOWED: FALSE

CR-06 "左右安全边距 >= 4%":
  由 spec 表达为:
    min_left = 0.04    → screen_min_x >= 0.04
    max_right = 0.96   → screen_max_x <= 0.96

CR-05 "顶部空白 <= 15%, 底部空白 <= 15%":
  由 spec 表达为:
    max_top = 0.85     → screen_max_y >= 0.85  (目标必须到达 85% 处)
    min_bottom = 0.15  → screen_min_y <= 0.15  (目标不能高于 15%)

这些值由用户写入 spec。Camera Check 不内置任何固定百分比阈值。
```

DF-14: 比较方向 → X 轴 containment, Y 轴 minimum coverage, spec-sourced

## 12. PASS / FAIL / ERROR / NOT_CHECKED

### 12.1 判定顺序（优先级递减）

```text
PRIORITY 1 — NOT_CHECKED (短路所有):
  camera_check block is None
  → checks.camera_check key not created

PRIORITY 2 — NOT_CHECKED (key created with note):
  Root precondition failure
  → {"result": "NOT_CHECKED", "note": "<reason>"}

PRIORITY 3 — ERROR (短路所有 FAIL):
  Any bpy read exception caught → ERROR with operation

PRIORITY 4 — FAIL (按优先级):
  a. CAMERA_OBJECT_NOT_FOUND
  b. CAMERA_TYPE_MISMATCH
  c. NON_FINITE_EVALUATED_VERTEX
     — §4.3 NaN/Inf contract; higher priority than zero-vertex
  d. NO_EVALUATED_GEOMETRY
     — §4.3 zero-vertex contract, empty geometry scope
  e. BEHIND_CAMERA (all corners z <= 0)
  f. SCREEN_BBOX_REQUIREMENT_NOT_MET (any boundary violation)
  g. INSUFFICIENT_VISIBLE_PROJECTED_CORNERS (visible < mvc)

PRIORITY 5 — PASS
```

### 12.2 多 FAIL 条件同时出现

```text
只报告优先级最高的 FAIL。

例:
  non_finite vertex + zero vertex → NON_FINITE_EVALUATED_VERTEX (4c > 4d)
  camera missing + geometry empty → CAMERA_OBJECT_NOT_FOUND (4a > 4c)
  bbox violation + insufficient corners → SCREEN_BBOX_REQUIREMENT_NOT_MET (4f > 4g)
```

DG-01: NOT_CHECKED → PRIORITY 1 + PRIORITY 2

## 13. 精确结果字典

### 13.1 NOT_CHECKED (根前置条件)

```json
{"result": "NOT_CHECKED", "note": "ROOT_OBJECT_NOT_FOUND"}
```
keys: `result`, `note`

### 13.2 NOT_CHECKED (配置缺失)

key NOT created in checks dict.

### 13.3 PASS

```json
{
  "result": "PASS",
  "camera_object_name": "Camera_Persp",
  "projected_corner_count": 8,
  "front_facing_projected_corner_count": 8,
  "minimum_visible_projected_corner_count": 8,
  "actual_screen_bbox": {"min_x": 0.12, "max_x": 0.88, "min_y": 0.08, "max_y": 0.92},
  "required_screen_bbox": {"min_left": 0.04, "max_right": 0.96, "min_bottom": 0.15, "max_top": 0.85},
  "evaluated_mesh_names": ["Body", "Head"]
}
```
keys (9): `result`, `camera_object_name`, `projected_corner_count`,
  `front_facing_projected_corner_count`, `minimum_visible_projected_corner_count`,
  `actual_screen_bbox`, `required_screen_bbox`, `evaluated_mesh_names`

PASS example: screen_min_x=0.12 >= 0.04 ✓, screen_max_x=0.88 <= 0.96 ✓,
              screen_min_y=0.08 <= 0.15 ✓, screen_max_y=0.92 >= 0.85 ✓

### 13.4 FAIL (CAMERA_OBJECT_NOT_FOUND)

```json
{
  "result": "FAIL",
  "failure_code": "CAMERA_OBJECT_NOT_FOUND",
  "camera_object_name": "NonExistentCamera"
}
```
keys (3): `result`, `failure_code`, `camera_object_name`

FAIL/CAMERA_TYPE_MISMATCH 额外包含 `actual_type` (4 keys)

### 13.5 FAIL (NON_FINITE_EVALUATED_VERTEX)

```json
{
  "result": "FAIL",
  "failure_code": "NON_FINITE_EVALUATED_VERTEX",
  "evaluated_mesh_names": ["Body"]
}
```
keys (3): `result`, `failure_code`, `evaluated_mesh_names`

### 13.6 FAIL (NO_EVALUATED_GEOMETRY)

```json
{
  "result": "FAIL",
  "failure_code": "NO_EVALUATED_GEOMETRY",
  "evaluated_mesh_names": []
}
```
keys (3): `result`, `failure_code`, `evaluated_mesh_names`

### 13.7 FAIL (BEHIND_CAMERA)

```json
{
  "result": "FAIL",
  "failure_code": "BEHIND_CAMERA",
  "camera_object_name": "Camera_Persp",
  "projected_corner_count": 8,
  "front_facing_projected_corner_count": 0,
  "evaluated_mesh_names": ["Body"]
}
```
keys (6): `result`, `failure_code`, `camera_object_name`,
  `projected_corner_count`, `front_facing_projected_corner_count`,
  `evaluated_mesh_names`

### 13.8 FAIL (INSUFFICIENT_VISIBLE_PROJECTED_CORNERS)

```json
{
  "result": "FAIL",
  "failure_code": "INSUFFICIENT_VISIBLE_PROJECTED_CORNERS",
  "camera_object_name": "Camera_Persp",
  "projected_corner_count": 8,
  "front_facing_projected_corner_count": 3,
  "minimum_visible_projected_corner_count": 8,
  "evaluated_mesh_names": ["Body"]
}
```
keys (7)

### 13.9 FAIL (SCREEN_BBOX_REQUIREMENT_NOT_MET)

```json
{
  "result": "FAIL",
  "failure_code": "SCREEN_BBOX_REQUIREMENT_NOT_MET",
  "camera_object_name": "Camera_Persp",
  "projected_corner_count": 8,
  "front_facing_projected_corner_count": 8,
  "minimum_visible_projected_corner_count": 8,
  "actual_screen_bbox": {"min_x": -0.05, "max_x": 0.90, "min_y": 0.20, "max_y": 0.80},
  "required_screen_bbox": {"min_left": 0.04, "max_right": 0.96, "min_bottom": 0.15, "max_top": 0.85},
  "evaluated_mesh_names": ["Body"]
}
```
keys (9)

Example violation: screen_min_x=-0.05 < 0.04 (X violation) AND
                    screen_max_y=0.80 < 0.85 (Y violation)

### 13.10 ERROR

```json
{
  "result": "ERROR",
  "error_type": "CAMERA_CHECK_COMPUTATION_ERROR",
  "operation": "TO_MESH_CLEAR",
  "note": "TO_MESH_CLEAR_FAILED"
}
```
keys (4): `result`, `error_type`, `operation`, `note`

### 13.11 结果字典形态汇总

```text
RESULT_DICT_FORM_COUNT: 11
  1. NOT_CHECKED (key not created) — camera_check is None
  2. NOT_CHECKED (2 keys) — root precondition failure
  3. PASS (9 keys)
  4. FAIL/CAMERA_OBJECT_NOT_FOUND (3 keys)
  5. FAIL/CAMERA_TYPE_MISMATCH (4 keys)
  6. FAIL/NON_FINITE_EVALUATED_VERTEX (3 keys)
  7. FAIL/NO_EVALUATED_GEOMETRY (3 keys)
  8. FAIL/BEHIND_CAMERA (6 keys)
  9. FAIL/INSUFFICIENT_VISIBLE_PROJECTED_CORNERS (7 keys)
  10. FAIL/SCREEN_BBOX_REQUIREMENT_NOT_MET (9 keys)
  11. ERROR (4 keys)
```

DG-02: 结果字典结构 → 11 种形态已定义
DG-03: bbox 边界顺序 → DF-08 通过 pre-open 验证统一

## 14. Failure Code 与优先级

```text
FAILURE_CODE_COUNT: 7

1. CAMERA_OBJECT_NOT_FOUND
2. CAMERA_TYPE_MISMATCH
3. NON_FINITE_EVALUATED_VERTEX
     → R2 §4.3 NaN/Inf contract; per-mesh immediate trigger
4. NO_EVALUATED_GEOMETRY
     → R2 §4.3 zero-vertex contract; per-mesh immediate trigger
5. BEHIND_CAMERA
6. INSUFFICIENT_VISIBLE_PROJECTED_CORNERS
7. SCREEN_BBOX_REQUIREMENT_NOT_MET
     → covers both "超过安全边界" (X axis) and "未达到覆盖阈值" (Y axis)

PRECEDENCE (first match wins):
  ERROR
  > CAMERA_OBJECT_NOT_FOUND
  > CAMERA_TYPE_MISMATCH
  > NON_FINITE_EVALUATED_VERTEX
  > NO_EVALUATED_GEOMETRY
  > BEHIND_CAMERA
  > SCREEN_BBOX_REQUIREMENT_NOT_MET
  > INSUFFICIENT_VISIBLE_PROJECTED_CORNERS
  > PASS
```

DF-12: failure_code → 7 个，优先级已定

## 15. Error Type 与 Operation

### 15.1 Error Type

```text
ERROR_TYPE: CAMERA_CHECK_COMPUTATION_ERROR
```

### 15.2 Operation 全集

```text
ERROR_OPERATION_COUNT: 17

Camera resolution:
  1. RESOLVE_CAMERA_OBJECT

Geometry scope:
  2. READ_SCENE_OBJECTS
  3. RESOLVE_ROOT_OBJECT
  4. READ_ROOT_CHILDREN
  5. READ_DESCENDANT_CHILDREN
  6. READ_DESCENDANT_TYPE

Evaluated geometry:
  7. GET_EVALUATED_DEPSGRAPH
  8. EVALUATED_GET
  9. TO_MESH
  10. READ_EVALUATED_MATRIX_WORLD
  11. READ_MESH_VERTICES
  12. TRANSFORM_VERTEX_TO_WORLD_SPACE
  13. TO_MESH_CLEAR

Projection:
  14. IMPORT_WORLD_TO_CAMERA_VIEW
  15. PROJECT_WORLD_CORNER

Screen bbox:
  16. COMPUTE_SCREEN_BBOX
  17. COMPARE_SCREEN_BBOX
```

DF-13: error_type + 17 operations

## 16. 读取次数与缓存合同

### 16.1 每个 Target 的最大读取次数

```text
OPERATION                     | MAX_READS | NOTE
------------------------------|-----------|---------------------------
scene.objects                 | 1         | one materialized collection
                              |           | shared by root, camera and
                              |           | geometry scope
obj.name                      | N+1       | N = scene.objects count
obj.type (camera)             | 1         | camera_obj.type
_collect_geometry_scope_objects| 1        | 复用已锁定 helper
depsgraph                     | 1         |
evaluated_get                 | M         | M = scope MESH count
to_mesh                       | M         |
evaluated.matrix_world        | M         |
mesh.vertices                 | M         |
to_mesh_clear                 | M         | in finally per MESH
world_to_camera_view          | 8         | 8 corners
```

### 16.2 缓存策略

```text
SCENE_OBJECTS_MATERIALIZATION_COUNT: EXACTLY_ONCE_PER_ENABLED_TARGET

同一份 scene.objects 物化结果同时用于:
  1. root resolution 索引构建 (scene_member_ids, scene_materialization_index)
  2. Camera exact-name lookup
  3. scene membership (scene_name_by_id)
  4. _collect_geometry_scope_objects 的输入

PER_TARGET_CACHE:
  — depsgraph: 1 次获取
  — _collect_geometry_scope_objects: 1 次调用
  — all_world_vertices / world bbox: 计算后缓存

NO_CROSS_TARGET_CACHE:
  — 每个 target 独立计算，不跨 target 共享

REUSE:
  — _collect_geometry_scope_objects: 直接复用，不重新实现
```

## 17. 清理和异常优先级

```text
PRIMARY ALGORITHM EXCEPTION:
  — 任何 bpy 读异常 → ERROR with operation

CLEANUP (to_mesh_clear):
  — 位于 finally 块
  — 如果 to_mesh_clear 抛异常:
      → TO_MESH_CLEAR ERROR
      该 ERROR 覆盖 finally 之前设置的任何 pending result
      (包括 pending_zero_vertex, pending_non_finite, all_world_vertices)
  — 与 Ground Contact R2 合同一致: return-in-finally pattern

MULTIPLE EXCEPTIONS:
  — 主算法异常 + cleanup 异常: cleanup ERROR 优先
  — RuntimeError from _collect_geometry_scope_objects: 转为 ERROR
```

## 18. 集成合同

### 18.1 函数签名

```python
def _check_camera_check(scene, target, per_target_result):
    """Check camera projection for a single target.

    Args:
        scene: bpy.types.Scene (may be None).
        target: target dict from spec.
        per_target_result: result dict from _check_root_objects.

    Returns:
        checks.camera_check result dict, or None if camera_check not configured.
    """
```

### 18.2 调用顺序

```text
open_blend_and_get_scene per-target loop:
  1. _check_animation_state
  2. _check_material_assignment
  3. _check_ground_contact
  4. _check_camera_check          ← after Ground Contact, before Collection Rules
  5. _check_collection_membership
  6. _recompute_target_overall
```

### 18.3 Checks 写入

```text
if camera_check_result is not None:
    target_result["checks"]["camera_check"] = camera_check_result
```

### 18.4 _recompute_target_overall

```text
现有通用遍历自动覆盖:
  ERROR > FAIL > PASS
  (camera_check NOT_CHECKED/absent 不参与 top-level 聚合)
```

### 18.5 _collect_target_errors

```text
cc = checks.get("camera_check", {})
if cc.get("result") == "ERROR":
    op = cc.get("operation", "UNKNOWN")
    err_msgs.append(
        f"CAMERA_CHECK_COMPUTATION_ERROR: target '{tid}' "
        f"root_object_name '{rn}' operation '{op}'"
    )
# 插入位置: Ground Contact ERROR 收集之后, Collection Rules ERROR 之前
```

### 18.6 NOT_CHECKED 填充

```text
_check_root_objects 的三个 NOT_CHECKED 模板均需添加:
  "camera_check": {"result": "NOT_CHECKED", "note": "<对应原因>"}

三个模板: ROOT_OBJECT_NOT_FOUND / ROOT_OBJECT_TYPE_MISMATCH / AMBIGUOUS_ROOT_OBJECT_NAME
```

## 19. 只读与 Scope Guard

### 19.1 新授权 API

```text
AUTHORIZED_FOR_CAMERA_CHECK:
  bpy_extras.object_utils.world_to_camera_view
  scene.objects (existing)
  object.name (existing)
  object.type (existing)
  bpy.context.evaluated_depsgraph_get (existing)
  obj.evaluated_get (existing)
  evaluated.to_mesh (existing)
  evaluated.matrix_world (existing)
  mesh.vertices (existing)
  evaluated.to_mesh_clear (existing)
  _collect_geometry_scope_objects (existing helper)
```

### 19.2 继续禁止

```text
FORBIDDEN_GLOBALLY:
  save, render, transform modification, visibility modification,
  material modification, collection modification
  bpy.context.scene (作为 active scene)
  object.bound_box
```

### 19.3 Scope Guard 调整

```text
test_asset_scene_preflight_blender_scene_basic.py:
  从 file-level string ban 删除 "world_to_camera_view"
  新增 AST-level per-function check:
    _check_camera_check: world_to_camera_view call sites <= 1
    所有其他函数: world_to_camera_view call sites == 0
    asset_scene_preflight_check.py: world_to_camera_view call sites == 0

test_asset_scene_preflight_blender_visibility_i2.py:
  从 string ban 删除 "world_to_camera_view"
```

## 20. CPython 测试矩阵

```text
CPYTHON_TEST_SCENARIO_COUNT: 54

配置和启用:
  1. camera_check is None → key not created
  2. camera_check 缺失 → key not created
  3. camera_check is dict with all fields → check enabled

Pre-open 验证:
  4. mvc = 9 → INVALID_CAMERA_CHECK_RULE_VALUE
  5. min_left > max_right → INVALID_CAMERA_CHECK_RULE_RELATION
  6. min_bottom > max_top → INVALID_CAMERA_CHECK_RULE_RELATION
  7. bbox < 0 → INVALID_CAMERA_CHECK_RULE_VALUE
  8. bbox > 1 → INVALID_CAMERA_CHECK_RULE_VALUE
  9. bbox == 0 / == 1 → valid pre-open

Root 前置条件:
  10-13. NOT_CHECKED × 4

Camera 查找:
  14. Camera found → PASS path
  15. Camera not found → FAIL CAMERA_OBJECT_NOT_FOUND
  16. Camera ambiguous → FAIL CAMERA_OBJECT_NOT_FOUND
  17. Camera type != CAMERA → FAIL CAMERA_TYPE_MISMATCH
  18. Camera name read exception → ERROR

Zero-vertex (F-002):
  19. Single MESH with zero vertices → FAIL NO_EVALUATED_GEOMETRY
  20. One MESH with vertices, another MESH zero → FAIL NO_EVALUATED_GEOMETRY
  21. to_mesh_clear ERROR overrides pending zero-vertex FAIL

Non-finite (F-003):
  22. NaN vertex → FAIL NON_FINITE_EVALUATED_VERTEX
  23. Inf vertex → FAIL NON_FINITE_EVALUATED_VERTEX
  24. to_mesh_clear ERROR overrides pending NaN FAIL
  25. NaN + zero-vertex → NON_FINITE_EVALUATED_VERTEX (priority)

精确结果字典:
  26-36. 11 种形态 assert_dict_equal 验证

failure_code 优先级:
  37. non_finite > zero_vertex
  38. camera missing > non_finite
  39. bbox_req_not_met > insufficient_corners (screen bbox violation + visible_count 不足 → SCREEN_BBOX_REQUIREMENT_NOT_MET)

operation 映射:
  40-46. 主要 ERROR operation

读取次数:
  47. scene.objects == 1

_collect_target_errors:
  48. camera_check ERROR → error message collected

总体聚合:
  49. camera_check ERROR → target overall ERROR
  50. camera_check FAIL → target overall FAIL

Vertical comparison (F-001):
  51. screen_min_y > min_bottom → FAIL
  52. screen_max_y < max_top → FAIL
  53. screen_min_y == min_bottom → PASS
  54. screen_max_y == max_top → PASS
```

## 21. Blender 5.1.2 临时验证矩阵

```text
BLENDER_TEST_SCENARIO_COUNT: 22

CC-BL-01: Perspective Camera PASS — all 8 corners z>0, mvc=8,
          screen_min_x>=0.04, screen_max_x<=0.96,
          screen_min_y<=0.15, screen_max_y>=0.85
CC-BL-02: Orthographic Camera PASS
CC-BL-03: All 8 corners z <= 0 → FAIL BEHIND_CAMERA
CC-BL-04: 4 corners z <= 0, 4 z > 0, mvc=4 → PASS
CC-BL-05: Left boundary FAIL — screen_min_x < min_left
CC-BL-06: Right boundary FAIL — screen_max_x > max_right
CC-BL-07: Bottom boundary FAIL — screen_min_y > min_bottom
CC-BL-08: Top boundary FAIL — screen_max_y < max_top
CC-BL-09: Exactly on boundary → PASS (all 4 edges)
CC-BL-10: Multiple MESH union bbox (SELF_AND_DESCENDANT_MESHES)
CC-BL-11: SELF_MESH geometry scope
CC-BL-12: DESCENDANT_MESHES geometry scope
CC-BL-13: Modifier (Solidify on plane) → evaluated geometry change
CC-BL-14: Zero-vertex Mesh → FAIL NO_EVALUATED_GEOMETRY
CC-BL-15: Non-finite vertex → FAIL NON_FINITE_EVALUATED_VERTEX
CC-BL-16: Zero-vertex + non-finite same mesh → FAIL NON_FINITE
CC-BL-17: Two targets share same Camera → independent results
CC-BL-18: Entry PASS
CC-BL-19: Entry FAIL — camera not found
CC-BL-20: Entry ERROR — depsgraph failure
CC-BL-21: Multiple targets, mixed pass/fail → correct per-target results
CC-BL-22: Empty geometry scope → FAIL NO_EVALUATED_GEOMETRY

ALL .blend FILES: TEMPORARY
REAL_PROJECT_BLEND_OPENED: FALSE
REAL_PROJECT_BLEND_SAVED: FALSE
RENDER_EXECUTED: FALSE
```

## 22. 精简实施拆分

```text
IMPLEMENTATION_STAGE_COUNT: 3

I1 — Production Implementation:
  — _validate_camera_check_rules_preopen() in asset_scene_preflight_check.py
  — _check_camera_check() in blender_scene_reader.py
    (含 per-mesh zero-vertex FAIL + NaN/Inf FAIL + to_mesh_clear contract)
  — Entry integration: call order, checks writing, NOT_CHECKED templates,
    _collect_target_errors
  — Focused CPython tests (54)
  — Scope Guard adjustment

I2 — Blender 5.1.2 Validation:
  — blender_camera_check_validation_runner.py (~22 scenarios)
  — test_asset_scene_preflight_camera_check_blender.py (pytest wrapper)
  — 修复 I2 发现的直接生产或测试问题

E — Final Regression:
  — Camera Check focused tests 全部通过
  — 既有字段组 direct regression
  — protocol_guard full unfiltered regression

DEFAULT_PER_IMPLEMENTATION_ROUND:
  NO_REPORT (unless task explicitly requires)
  NO_ZIP / NO_MANIFEST / NO_SHA256_LIST
  DIRECT_UPLOAD (1-3 files)
```

## 23. DF / DG 到最终决定交叉表

```text
ID     | 决定                                                      | 位置
-------|-----------------------------------------------------------|------
DF-01  | scene.objects, exact case-sensitive match                 | §6.1
DF-02  | FAIL CAMERA_OBJECT_NOT_FOUND                              | §6.1
DF-03  | FAIL CAMERA_TYPE_MISMATCH                                 | §6.1
DF-04  | z <= 0 → discard, not visible                            | §10.2
DF-05  | corner on boundary → included as visible                 | §10.3
DF-06  | mvc > 8 → pre-open INPUT ERROR                           | §5.3
DF-07  | empty geometry scope → FAIL NO_EVALUATED_GEOMETRY        | §8.1
DF-08  | bbox ordering → pre-open validation                      | §5.3
DF-09  | bbox [0,1] range → pre-open validation                   | §5.3
DF-10  | extra pre-open rules: mvc<=8, bbox order, bbox [0,1]     | §5.3
DF-11  | mvc max = 8                                              | §5.3
DF-12  | 7 failure_codes, precedence defined                      | §14
DF-13  | CAMERA_CHECK_COMPUTATION_ERROR, 17 operations            | §15
DF-14  | X containment + Y minimum coverage, spec-sourced         | §11

DG-01  | NOT_CHECKED conditions defined                           | §12.1
DG-02  | 11 result dict forms with exact key sets                 | §13
DG-03  | bbox ordering pre-open unified, no result-layer handling | §5.3
```

## 24. Machine-Readable Summary

```text
TASK_ID: CAMERA_CHECK_DESIGN_R2_CORRECTION
TASK_TYPE: DESIGN_CORRECTION
SOURCE_DESIGN_VERSION: R1
TARGET_DESIGN_VERSION: R2
MASTER_MAP_VERSION: R77

RECOVERED_R1_SOURCE_VALIDATION:
  VERIFIED_FROM_TASK_SPEC_EMBEDDED_SECTION_19
RECOVERED_R1_SOURCE_PROVENANCE:
  GPT_PRETASK_EXTRACTION_FROM_USER_LIBRARY_COPY
R1_SOURCE_DIRECTLY_READ_BY_CLAUDE_CODE: FALSE
RECOVERED_R1_SOURCE_USED: TRUE

DESIGN_FILE: reviews/CAMERA_CHECK_DESIGN_R2.md
DESIGN_VERSION: R2
DESIGN_STATUS: FORMALLY_LOCKED
FORMALLY_LOCKED: TRUE
FORMAL_LOCK_DATE: 2026-07-26
IMPLEMENTATION_AUTHORIZED: FALSE

HORIZONTAL_MODEL: SAFE_MARGIN_CONTAINMENT
VERTICAL_MODEL: MINIMUM_COVERAGE
ZERO_VERTEX_POLICY: per-mesh immediate FAIL NO_EVALUATED_GEOMETRY, to_mesh_clear required
NON_FINITE_VERTEX_POLICY: per-mesh immediate FAIL NON_FINITE_EVALUATED_VERTEX, to_mesh_clear required
SCENE_OBJECTS_MATERIALIZATION_COUNT: EXACTLY_ONCE_PER_ENABLED_TARGET

ALL_DF_01_TO_DF_14_DECIDED: TRUE
ALL_DG_01_TO_DG_03_CLOSED: TRUE
UNRESOLVED_RUNTIME_SEMANTICS: 0

RESULT_DICT_FORM_COUNT: 11
FAILURE_CODE_COUNT: 7
ERROR_OPERATION_COUNT: 17
CPYTHON_TEST_SCENARIO_COUNT: 54
BLENDER_TEST_SCENARIO_COUNT: 22
IMPLEMENTATION_STAGE_COUNT: 3 (I1 + I2 + E)

TRUE_CONTRACT_CONFLICT_COUNT: 0
TRUE_BLOCKING_ISSUES: 0

FORMALLY_LOCKED: FALSE
IMPLEMENTATION_AUTHORIZED: FALSE

BOUNDARY_VALUES_SOURCE: SPEC_REQUIRED_SCREEN_BBOX
HARDCODED_PERCENTAGE_VALUES_ALLOWED: FALSE

SIDE_EFFECTS:
  REAL_PROJECT_BLEND_OPENED: FALSE
  REAL_PROJECT_BLEND_SAVED: FALSE
  RENDER_EXECUTED: FALSE
  SAVE_FORBIDDEN: TRUE
  TRANSFORM_MODIFICATION_FORBIDDEN: TRUE
  READ_ONLY: TRUE
```

---

*Camera Check Design R2 is formally locked. Implementation remains unauthorized pending separate user approval.*
