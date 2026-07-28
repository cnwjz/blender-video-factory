# Camera Check Runtime Design R1

```text
DOCUMENT_ID: CAMERA_CHECK_DESIGN
DESIGN_VERSION: R1
TASK_ID: CAMERA_CHECK_DESIGN_R1
MASTER_MAP_VERSION: R77
DATE: 2026-07-26
DESIGN_STATUS: COMPLETED_PENDING_INDEPENDENT_REVIEW
FORMALLY_LOCKED: FALSE
IMPLEMENTATION_AUTHORIZED: FALSE
DESIGN_AUTHORIZATION: USER_EXPLICITLY_AUTHORIZED
DESIGN_AUTHORIZATION_DATE: 2026-07-26

RECOVERED_R1_SOURCE_USED: TRUE
RECOVERED_R1_SOURCE_PROVENANCE: USER_PROVIDED_HISTORICAL_LIBRARY_COPY
  — R1 §19 投影算法嵌入 R2 §10.1 并作为本次设计 §10 的算法基础
  — R1 §12 raw bound_box 已被 R2 §4 明确替换
  — R1 §20 结果/退出码合同已被 R2 整体框架覆盖
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
    §10.1 Per-Target Projection (retains R1 §19, replaces raw bound_box
          with evaluated geometry)
    §10.2 Global Projection Groups (separate checker, not Camera Check)
    §10.3 Projection Limitations

PRIORITY_4: R1 Implementation Contract §19 (Recovered)
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
  — GROUND_CONTACT_DESIGN_R2.md (evaluated geometry, geometry_scope reuse, error patterns)
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
    AUDIT_COVERAGE_GAP_COUNT: 1 (R1 §19 original text not on disk)
```

## 2. R1/R2 合并与替换矩阵

```text
TOPIC                        | R1 §      | R2 §      | RESULT
-----------------------------|-----------|-----------|---------------------------
Geometry source              | §12       | §4        | REPLACED: R2 evaluated geometry
Per-target projection        | §19       | §10.1     | RETAINED + MODIFIED:
                             |           |           |   algorithm retained,
                             |           |           |   bbox source changed to
                             |           |           |   evaluated geometry corners
Global projection groups     | —         | §10.2     | NEW: separate checker
Screen bbox limitations      | —         | §10.3     | NEW: geometric margins only
World-space bbox algorithm   | §12       | §4.2      | REPLACED: evaluated depsgraph
Result/exit code             | §20       | §13, §15  | SUPERSEDED: R2 framework
```

## 3. 设计目标

1. 为 Camera Check 字段组定义唯一、完整、可独立实现和测试的运行时设计。
2. 所有 14 项审计 DF 和 3 项 DG 均给出唯一最终决定。
3. 结果字典键集合唯一，支持 `assert_dict_equal` 精确断言。
4. 所有异常路径有唯一 operation，所有 FAIL 有唯一 failure_code，错误优先级唯一。
5. 配置、前置条件、算法、结果、清理、集成和副作用边界全部封闭。

## 4. 固定范围与明确非目标

```text
FIXED_SCOPE:
  — Schema 6 leaf fields: camera_object_name, minimum_visible_projected_corner_count,
    required_screen_bbox.min_left/.max_right/.min_bottom/.max_top
  — target.geometry_scope 复用
  — R2 §4 evaluated geometry 数据链
  — R1 §19 投影算法 (8 角点 → projection → z-filter → screen bbox → mvc)
  — 结果键名: checks.camera_check
  — 独立 per-target 检查，不跨 target 聚合

EXPLICITLY_EXCLUDED:
  — 遮挡关系 (ray casting / occlusion)
  — 画面是否好看、视觉层级、超市识别
  — 跨 target 联合构图 → Projection Groups
  — additional_object_names → Projection Groups
  — 相机是否在 essential objects 联合 bbox 内 → Projection Groups
  — 保存重开 persistence
  — 渲染结果
  — 历史 Draft "camera_visible" boolean (Design Spec R1 §5.2, §5.3 — SUPERSEDED_OR_STALE_DRAFT)

MUST_NOT_MODIFY:
  — 14A Core schema (_validate_camera_check)
  — _check_root_objects 的返回结构
  — Hierarchy, Standing, Facing, Visibility, Rotation, Animation State,
    Material Assignment, Ground Contact, Collection Rules 的生产代码和测试
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
  → checks.camera_check KEY NOT CREATED in per_target_result.checks

  camera_check 缺失、null 或非 dict（14A 会在 pre-open 拒绝非 dict）时：
  → Camera Check 完全不参与该 target 的 overall 聚合
```

### 5.2 输出键存在性

```text
camera_check 缺失/null:
  checks dict 中不存在 "camera_check" 键
  _recompute_target_overall 不会看到该键 → 不参与聚合

根对象前置条件失败 (ROOT_OBJECT_NOT_FOUND / AMBIGUOUS_ROOT_OBJECT_NAME
/ ROOT_LOOKUP_ERROR / ROOT_OBJECT_TYPE_MISMATCH):
  与 Ground Contact、Material Assignment 一致：
  checks.camera_check = {"result": "NOT_CHECKED", "note": "<前置失败原因>"}
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
  world_to_camera_view produces x/y in [0, 1]. Values outside this range
  cannot be meaningfully compared to projected screen coordinates.
```

DF-06: mvc > 8 → pre-open INPUT ERROR (不是运行时 FAIL — 这是永不满足的配置)
DF-08: bbox 顺序 → pre-open 验证，与 projection_groups 统一
DF-09: [0, 1] 范围 → pre-open 验证
DF-10: 额外 pre-open 规则 → 上述四条
DF-11: mvc max = 8

## 6. Camera 查找合同

### 6.1 解析策略

```text
LOOKUP_METHOD: 遍历 scene.objects，精确区分大小写匹配 camera_object_name
RATIONALE: 与 root_object_name 解析 (_check_root_objects) 一致

ALGORITHM:
  camera_obj = None
  match_count = 0
  for obj in scene.objects:
      if obj.name == camera_object_name:
          match_count += 1
          if match_count == 1:
              camera_obj = obj
          else:
              camera_obj = None  # ambiguous

  if match_count == 0:
      → FAIL (failure_code: CAMERA_OBJECT_NOT_FOUND)
  elif match_count > 1:
      → FAIL (failure_code: CAMERA_OBJECT_NOT_FOUND)
      # 同名歧义与缺失归入同一 failure_code；
      # 场景中同名 Camera 歧义本身是场景错误
  elif camera_obj.type != 'CAMERA':
      → FAIL (failure_code: CAMERA_TYPE_MISMATCH,
              actual_type: camera_obj.type)

  # obj.name / obj.type 读取异常:
  → ERROR (operation: RESOLVE_CAMERA_OBJECT)
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
  scene.camera (当前活动相机不相关 — Camera Check 使用命名相机)
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
  SELF_MESH — root 自身（当 root_type == 'MESH'）
  DESCENDANT_MESHES — 所有后代 MESH
  SELF_AND_DESCENDANT_MESHES — root + 后代 MESH

REUSE_HELPER: _collect_geometry_scope_objects (blender_scene_reader.py)
  — 已锁定，Ground Contact 和 Material Assignment 共用
  — Camera Check 复用同一调用，不重新实现
```

## 8. Evaluated Geometry 算法

### 8.1 算法（与 Ground Contact 共享 R2 §4）

```text
1. depsgraph = bpy.context.evaluated_depsgraph_get()
2. mesh_objects = _collect_geometry_scope_objects(...)
3. if len(mesh_objects) == 0 → FAIL (NO_EVALUATED_GEOMETRY)

4. all_world_vertices = []
   for mesh_obj, mesh_name in mesh_objects:
       evaluated = mesh_obj.evaluated_get(depsgraph)
       mesh = evaluated.to_mesh()
       try:
           mw = evaluated.matrix_world
           if len(mesh.vertices) == 0: continue
           for v in mesh.vertices:
               world = mw @ v.co
               if not (isfinite(world.x) and isfinite(world.y) and isfinite(world.z)):
                   non_finite_found = True; continue
               all_world_vertices.append(world)
       finally:
           evaluated.to_mesh_clear()

5. if len(all_world_vertices) == 0:
       if non_finite_found → FAIL (NON_FINITE_EVALUATED_VERTEX)
       else → FAIL (NO_EVALUATED_GEOMETRY)
```

### 8.2 清理合同

```text
to_mesh_clear() 在 finally 块中执行。
如果 to_mesh_clear 抛异常:
  → ERROR (operation: TO_MESH_CLEAR)
  该 ERROR 覆盖 finally 块之前的任何 pending PASS/FAIL 结果
  (与 Ground Contact R2 合同一致)

主异常 + cleanup 异常同时发生:
  cleanup ERROR 优先 → 返回 TO_MESH_CLEAR ERROR
  (R2 Design: return-in-finally pattern)
```

DF-07: 空 geometry scope → FAIL NO_EVALUATED_GEOMETRY

## 9. World BBox 8 角点算法

```text
INPUT: all_world_vertices (list of mathutils.Vector in world space)

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
       projected_corners.append((
           projected.x, projected.y, projected.z,
       ))

2. front_corners = [(x, y) for (x, y, z) in projected_corners if z > 0]

3. if len(front_corners) == 0:
       → FAIL (failure_code: BEHIND_CAMERA)

4. screen_min_x = min(x for (x, y) in front_corners)
   screen_max_x = max(x for (x, y) in front_corners)
   screen_min_y = min(y for (x, y) in front_corners)
   screen_max_y = max(y for (x, y) in front_corners)

5. actual_screen_bbox = {
       "min_x": screen_min_x, "max_x": screen_max_x,
       "min_y": screen_min_y, "max_y": screen_max_y,
   }

6. visible_count = len(front_corners)

7. minimum_visible = target.camera_check.minimum_visible_projected_corner_count
   if visible_count < minimum_visible:
       → FAIL (failure_code: INSUFFICIENT_VISIBLE_PROJECTED_CORNERS)

8. screen bbox boundary check (see §11)
```

### 10.2 z == 0 处理

```text
DM-04:
  projected_z == 0 → 视为在相机后方（与 z < 0 同等处理，丢弃）
  RATIONALE: z == 0 位于相机平面上或极其接近，Blender 中与 z < 0 行为类似
```

DF-04: z ≤ 0 → 丢弃，视为不可见

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
  z 非有限也投影失败
```

## 11. required_screen_bbox 精确比较式

### 11.1 统一语义模型

```text
MODEL: CONTAINMENT (安全区包含)
  target 的 projected screen bbox 必须被 required_screen_bbox 完全包含

COMPARISON (all four edges):
  screen_min_x >= required_screen_bbox.min_left
  screen_max_x <= required_screen_bbox.max_right
  screen_min_y >= required_screen_bbox.min_bottom
  screen_max_y <= required_screen_bbox.max_top

X 和 Y 使用统一的 containment 模型。
不区分安全区/覆盖区 — 四个边界全部 use "target inside zone" 语义。
```

### 11.2 边界等式

```text
screen_min_x == min_left → PASS (包含边界)
screen_max_x == max_right → PASS (包含边界)
screen_min_y == min_bottom → PASS (包含边界)
screen_max_y == max_top → PASS (包含边界)
```

### 11.3 FAIL 条件

```text
Any of:
  screen_min_x < min_left
  screen_max_x > max_right
  screen_min_y < min_bottom
  screen_max_y > max_top
→ FAIL (failure_code: SCREEN_BBOX_BOUNDARY_EXCEEDED)
```

### 11.4 百分比约束的映射 (CR-05, CR-06)

```text
BOUNDARY_VALUES_SOURCE: SPEC_REQUIRED_SCREEN_BBOX
HARDCODED_PERCENTAGE_VALUES_ALLOWED: FALSE

CR-05 "顶部空白 ≤ 15%, 底部空白 ≤ 15%":
  由 spec 表达为:
    max_top = 0.85  (顶部 15% = 空白区，target 不能超出 85%）
    min_bottom = 0.15 (底部 15% = 空白区，target 不能低于 15%）

CR-06 "左右安全边距 ≥ 4%":
  由 spec 表达为:
    min_left = 0.04
    max_right = 0.96

这些值由用户写入 spec。Camera Check 不内置任何固定百分比阈值。
```

DF-14: 比较方向 → containment 统一模型，边界值来自 spec

## 12. PASS / FAIL / ERROR / NOT_CHECKED

### 12.1 判定顺序（优先级递减）

```text
PRIORITY 1 — NOT_CHECKED (短路所有后续):
  camera_check block is None
  → checks.camera_check key not created

PRIORITY 2 — NOT_CHECKED (key created with note):
  Root precondition failure (ROOT_OBJECT_NOT_FOUND / AMBIGUOUS /
  ROOT_LOOKUP_ERROR / ROOT_OBJECT_TYPE_MISMATCH)
  → {"result": "NOT_CHECKED", "note": "<reason>"}

PRIORITY 3 — ERROR (短路所有 FAIL):
  Any bpy read exception caught → ERROR with operation

PRIORITY 4 — FAIL (按优先级):
  a. CAMERA_OBJECT_NOT_FOUND (camera not found or ambiguous)
  b. CAMERA_TYPE_MISMATCH (type != CAMERA)
  c. NO_EVALUATED_GEOMETRY (geometry scope empty or all zero-vertex)
  d. NON_FINITE_EVALUATED_VERTEX (non-finite vertex found, no finite vertices)
  e. BEHIND_CAMERA (all corners z <= 0)
  f. INSUFFICIENT_VISIBLE_PROJECTED_CORNERS (visible < mvc)
  g. SCREEN_BBOX_BOUNDARY_EXCEEDED (any boundary violated)

PRIORITY 5 — PASS:
  All above pass → PASS
```

### 12.2 多 FAIL 条件同时出现

```text
只报告优先级最高的 FAIL。
例如 camera not found AND geometry scope empty:
  → FAIL with CAMERA_OBJECT_NOT_FOUND (4a > 4c)
例如 geometry scope empty AND bbox boundary exceeded:
  → FAIL with NO_EVALUATED_GEOMETRY (4c > 4g)
```

DG-01: NOT_CHECKED 条件 → 上述 PRIORITY 1 + PRIORITY 2

## 13. 精确结果字典

### 13.1 NOT_CHECKED (根前置条件)

```json
{
  "result": "NOT_CHECKED",
  "note": "ROOT_OBJECT_NOT_FOUND"
}
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
  "actual_screen_bbox": {
    "min_x": 0.12, "max_x": 0.88,
    "min_y": 0.20, "max_y": 0.80
  },
  "required_screen_bbox": {
    "min_left": 0.04, "max_right": 0.96,
    "min_bottom": 0.15, "max_top": 0.85
  },
  "evaluated_mesh_names": ["Body", "Head"]
}
```

keys (9): `result`, `camera_object_name`, `projected_corner_count`,
  `front_facing_projected_corner_count`, `minimum_visible_projected_corner_count`,
  `actual_screen_bbox`, `required_screen_bbox`, `evaluated_mesh_names`

### 13.4 FAIL (CAMERA_OBJECT_NOT_FOUND)

```json
{
  "result": "FAIL",
  "failure_code": "CAMERA_OBJECT_NOT_FOUND",
  "camera_object_name": "NonExistentCamera"
}
```

keys (3):
  FAIL/CAMERA_OBJECT_NOT_FOUND: `result`, `failure_code`, `camera_object_name`
  FAIL/CAMERA_TYPE_MISMATCH: `result`, `failure_code`, `camera_object_name`, `actual_type`

### 13.5 FAIL (NO_EVALUATED_GEOMETRY / NON_FINITE_EVALUATED_VERTEX)

```json
{
  "result": "FAIL",
  "failure_code": "NO_EVALUATED_GEOMETRY",
  "evaluated_mesh_names": []
}
```

keys (3): `result`, `failure_code`, `evaluated_mesh_names`

### 13.6 FAIL (BEHIND_CAMERA)

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

### 13.7 FAIL (INSUFFICIENT_VISIBLE_PROJECTED_CORNERS)

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

keys (7): `result`, `failure_code`, `camera_object_name`,
  `projected_corner_count`, `front_facing_projected_corner_count`,
  `minimum_visible_projected_corner_count`, `evaluated_mesh_names`

### 13.8 FAIL (SCREEN_BBOX_BOUNDARY_EXCEEDED)

```json
{
  "result": "FAIL",
  "failure_code": "SCREEN_BBOX_BOUNDARY_EXCEEDED",
  "camera_object_name": "Camera_Persp",
  "projected_corner_count": 8,
  "front_facing_projected_corner_count": 8,
  "minimum_visible_projected_corner_count": 8,
  "actual_screen_bbox": {"min_x": -0.05, "max_x": 0.90,
                         "min_y": 0.20, "max_y": 0.80},
  "required_screen_bbox": {"min_left": 0.04, "max_right": 0.96,
                           "min_bottom": 0.15, "max_top": 0.85},
  "evaluated_mesh_names": ["Body"]
}
```

keys (9): `result`, `failure_code`, `camera_object_name`,
  `projected_corner_count`, `front_facing_projected_corner_count`,
  `minimum_visible_projected_corner_count`,
  `actual_screen_bbox`, `required_screen_bbox`, `evaluated_mesh_names`

### 13.9 ERROR

```json
{
  "result": "ERROR",
  "error_type": "CAMERA_CHECK_COMPUTATION_ERROR",
  "operation": "GET_EVALUATED_DEPSGRAPH",
  "note": "GET_EVALUATED_DEPSGRAPH_FAILED"
}
```

keys (4): `result`, `error_type`, `operation`, `note`

### 13.10 结果字典形态汇总

```text
RESULT_DICT_FORM_COUNT: 11
  1. NOT_CHECKED (key not created) — camera_check is None
  2. NOT_CHECKED (2 keys) — root precondition failure
  3. PASS (9 keys)
  4. FAIL/CAMERA_OBJECT_NOT_FOUND (3 keys)
  5. FAIL/CAMERA_TYPE_MISMATCH (4 keys)
  6. FAIL/NO_EVALUATED_GEOMETRY (3 keys)
  7. FAIL/NON_FINITE_EVALUATED_VERTEX (3 keys)
  8. FAIL/BEHIND_CAMERA (6 keys)
  9. FAIL/INSUFFICIENT_VISIBLE_PROJECTED_CORNERS (7 keys)
  10. FAIL/SCREEN_BBOX_BOUNDARY_EXCEEDED (9 keys)
  11. ERROR (4 keys)

注: NON_FINITE 也包含 evaluated_mesh_names 与 NO_EVALUATED_GEOMETRY 同结构。
     BEHIND_CAMERA / INSUFFICIENT 各含不同程度的前端投影信息。
```

DG-02: 结果字典结构 → 上述全部 11 种形态已定义
DG-03: bbox 边界顺序 → DF-08 通过 pre-open 验证统一，无需在结果层处理

## 14. Failure Code 与优先级

```text
FAILURE_CODE_COUNT: 7

1. CAMERA_OBJECT_NOT_FOUND
     → camera not in scene.objects by exact name, or ambiguous
2. CAMERA_TYPE_MISMATCH
     → camera object found but object.type != 'CAMERA'
3. NO_EVALUATED_GEOMETRY
     → geometry scope 无 MESH 或全部零顶点且无非有限顶点
4. NON_FINITE_EVALUATED_VERTEX
     → 有非有限顶点且无有效有限顶点
5. BEHIND_CAMERA
     → 所有 8 个角点 projected_z <= 0
6. INSUFFICIENT_VISIBLE_PROJECTED_CORNERS
     → front_facing count < minimum_visible_projected_corner_count
7. SCREEN_BBOX_BOUNDARY_EXCEEDED
     → screen bbox 越界 (any of 4 edges)

PRECEDENCE (first match wins):
  ERROR > CAMERA_OBJECT_NOT_FOUND > CAMERA_TYPE_MISMATCH
  > NO_EVALUATED_GEOMETRY > NON_FINITE_EVALUATED_VERTEX
  > BEHIND_CAMERA > INSUFFICIENT_VISIBLE_PROJECTED_CORNERS
  > SCREEN_BBOX_BOUNDARY_EXCEEDED
  > PASS
```

DF-12: failure_code → 7 个，优先级已定

## 15. Error Type 与 Operation

### 15.1 Error Type

```text
ERROR_TYPE: CAMERA_CHECK_COMPUTATION_ERROR
  — 遵循 ROTATION_COMPUTATION_ERROR / GROUND_CONTACT_COMPUTATION_ERROR /
    MATERIAL_ASSIGNMENT_COMPUTATION_ERROR / ANIMATION_STATE_COMPUTATION_ERROR /
    COLLECTION_RULES_COMPUTATION_ERROR 命名风格
```

### 15.2 Operation 全集

```text
ERROR_OPERATION_COUNT: 17

Camera resolution:
  1. RESOLVE_CAMERA_OBJECT — scene.objects 遍历或 obj.name 读异常

Geometry scope:
  2. READ_SCENE_OBJECTS — list(scene.objects) 异常
  3. RESOLVE_ROOT_OBJECT — root 名解析异常
  4. READ_ROOT_CHILDREN — root_obj.children 异常 (via _collect)
  5. READ_DESCENDANT_CHILDREN — descendant.children 异常 (via _collect)
  6. READ_DESCENDANT_TYPE — descendant.type 异常 (via _collect)

Evaluated geometry:
  7. GET_EVALUATED_DEPSGRAPH — depsgraph 获取失败
  8. EVALUATED_GET — obj.evaluated_get 失败
  9. TO_MESH — evaluated.to_mesh 失败
  10. READ_EVALUATED_MATRIX_WORLD — evaluated.matrix_world 读异常
  11. READ_MESH_VERTICES — mesh.vertices 或 v.co 访问异常
  12. TRANSFORM_VERTEX_TO_WORLD_SPACE — mw @ vertex_co 异常
  13. TO_MESH_CLEAR — evaluated.to_mesh_clear 异常

Projection:
  14. IMPORT_WORLD_TO_CAMERA_VIEW — bpy_extras.object_utils 导入失败
  15. PROJECT_WORLD_CORNER — world_to_camera_view 调用异常或返回非有限值

Screen bbox:
  16. COMPUTE_SCREEN_BBOX — 从 front_corners 计算 min/max 异常
  17. COMPARE_SCREEN_BBOX — bbox 比较异常
```

DF-13: error_type + operation → CAMERA_CHECK_COMPUTATION_ERROR + 17 operations

## 16. 读取次数与缓存合同

### 16.1 每个 Target 的最大读取次数

```text
OPERATION                     | MAX_READS | NOTE
------------------------------|-----------|---------------------------
scene.objects                 | 2         | root resolution + camera lookup (可合并为1)
obj.name                      | N+1       | N = scene.objects count; root+camera lookup
obj.type (camera)             | 1         | camera_obj.type
_collect_geometry_scope_objects| 1        | 复用已锁定 helper
depsgraph                     | 1         | bpy.context.evaluated_depsgraph_get()
evaluated_get                 | M         | M = geometry scope MESH count
to_mesh                       | M         | per MESH
evaluated.matrix_world        | M         | per MESH
mesh.vertices                 | M         | per MESH
to_mesh_clear                 | M         | per MESH, in finally
world_to_camera_view          | 8         | 8 corners max
```

### 16.2 缓存策略

```text
PER_TARGET_CACHE:
  — scene.objects materialization: 最多 1 次 (resolve root + find camera 共享)
  — _collect_geometry_scope_objects: 1 次调用
  — depsgraph: 1 次
  — all_world_vertices / world bbox: 计算后缓存

NO_CROSS_TARGET_CACHE:
  — 每个 target 独立计算
  — 不跨 target 共享 Camera 对象或 depsgraph
  — 与 Ground Contact、Material Assignment 保持一致

REUSE:
  — _collect_geometry_scope_objects: 直接复用
  — 不重新实现 geometry scope 遍历
```

## 17. 清理和异常优先级

```text
PRIMARY ALGORITHM EXCEPTION:
  — 任何 bpy 读异常 → ERROR with operation
  — 已返回 ERROR 时不会再有 FAIL/PASS 提供

CLEANUP (to_mesh_clear):
  — 位于 finally 块
  — 如果 to_mesh_clear 抛异常:
      返回 TO_MESH_CLEAR ERROR
      该 ERROR 覆盖主算法返回的任何 pending 结果
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
        per_target_result: result dict from _check_root_objects for this target.

    Returns:
        checks.camera_check result dict (or None if camera_check not configured).
    """
```

### 18.2 调用顺序

```text
open_blend_and_get_scene per-target loop:
  1. _check_animation_state
  2. _check_material_assignment
  3. _check_ground_contact
  4. _check_camera_check          ← NEW: after Ground Contact, before Collection Rules
  5. _check_collection_membership
  6. _recompute_target_overall
```

### 18.3 Checks 写入

```text
target_result["checks"]["camera_check"] = camera_check_result
# 如果 camera_check 返回 None (未配置)，不写入该键
```

### 18.4 _recompute_target_overall

```text
现有通用遍历自动覆盖 camera_check:
  for key, val in checks.items():
      if isinstance(val, dict) and "result" in val:
          sub_results.append(val["result"])
  → ERROR > FAIL > PASS (no NOT_CHECKED in top-level agg)
```

### 18.5 _collect_target_errors

```text
新增 camera_check ERROR 收集:
  gc = checks.get("camera_check", {})  # 注: 变量名使用 cc
  if cc.get("result") == "ERROR":
      op = cc.get("operation", "UNKNOWN")
      err_msgs.append(
          f"CAMERA_CHECK_COMPUTATION_ERROR: target '{tid}' "
          f"root_object_name '{rn}' operation '{op}'"
      )
  # 插入位置: Ground Contact ERROR 收集之后，Collection Rules ERROR 之前
```

### 18.6 NOT_CHECKED 填充

```text
_check_root_objects 的三个 NOT_CHECKED 模板均需添加:
  "camera_check": {"result": "NOT_CHECKED", "note": "<对应原因>"}

三个模板对应:
  — ROOT_OBJECT_NOT_FOUND
  — ROOT_OBJECT_TYPE_MISMATCH
  — AMBIGUOUS_ROOT_OBJECT_NAME
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
CURRENT: world_to_camera_view 在 Scope Guard 中全局禁止

ADJUSTMENT:
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
CPYTHON_TEST_SCENARIO_COUNT: ~40

配置和启用:
  1. camera_check is None → key not created
  2. camera_check 缺失 → key not created
  3. camera_check is dict with all fields → check enabled

Pre-open 验证:
  4. mvc = -1 → schema ERROR (14A existing)
  5. mvc = 0 → valid
  6. mvc = 8 → valid
  7. mvc = 9 → INVALID_CAMERA_CHECK_RULE_VALUE
  8. mvc = True → schema ERROR
  9. bbox NaN → schema ERROR
  10. bbox Inf → schema ERROR
  11. bbox bool → schema ERROR
  12. min_left > max_right → INVALID_CAMERA_CHECK_RULE_RELATION
  13. min_bottom > max_top → INVALID_CAMERA_CHECK_RULE_RELATION
  14. bbox value < 0 → INVALID_CAMERA_CHECK_RULE_VALUE
  15. bbox value > 1 → INVALID_CAMERA_CHECK_RULE_VALUE
  16. bbox boundary exactly 0 or 1 → valid
  17. mvc = 8 with min_left <= max_right, all in [0,1] → valid pre-open

Root 前置条件:
  18. Root not found → NOT_CHECKED
  19. Root ambiguous → NOT_CHECKED
  20. Root type mismatch → NOT_CHECKED
  21. Root lookup error → NOT_CHECKED
  22. Root + type pass → proceeds to camera check

Camera 查找:
  23. Camera found in scene.objects → PASS path
  24. Camera not found → FAIL CAMERA_OBJECT_NOT_FOUND
  25. Camera ambiguous → FAIL CAMERA_OBJECT_NOT_FOUND
  26. Camera type != CAMERA → FAIL CAMERA_TYPE_MISMATCH
  27. Camera name read exception → ERROR RESOLVE_CAMERA_OBJECT

精确结果字典:
  28-38. 每类 result dict 的精确键集验证 (assert_dict_equal)

failure_code 优先级:
  39. Camera missing > geometry empty
  40. Geometry empty > behind camera
  41. Behind camera > insufficient corners

operation 映射:
  42-48. 主要 ERROR operation 的映射验证

读取次数:
  49-52. 关键 API 读取次数 contract

_collect_target_errors:
  53. camera_check ERROR → error message collected

总体聚合:
  54. camera_check ERROR → target overall ERROR
  55. camera_check FAIL → target overall FAIL
  56. camera_check PASS → target overall 由其他 checks 决定
```

## 21. Blender 5.1.2 临时验证矩阵

```text
BLENDER_TEST_SCENARIO_COUNT: ~20

CC-BL-01: Perspective Camera — 8 corners all in front, mvc=8, bbox within [0.04,0.96]×[0.15,0.85] → PASS
CC-BL-02: Orthographic Camera — same setup → PASS
CC-BL-03: All 8 corners z <= 0 → FAIL BEHIND_CAMERA
CC-BL-04: 4 corners z <= 0, 4 z > 0 → screen bbox from 4 survivors, mvc=4 → PASS
CC-BL-05: Left boundary FAIL — projected_min_x < min_left
CC-BL-06: Right boundary FAIL — projected_max_x > max_right
CC-BL-07: Bottom boundary FAIL — projected_min_y < min_bottom
CC-BL-08: Top boundary FAIL — projected_max_y > max_top
CC-BL-09: Exactly on boundary → PASS (左/右/上/下各至少1个场景)
CC-BL-10: Multiple MESH union bbox (SELF_AND_DESCENDANT_MESHES)
CC-BL-11: SELF_MESH geometry scope — correct
CC-BL-12: DESCENDANT_MESHES geometry scope — correct
CC-BL-13: Modifier (Solidify on plane) → evaluated geometry different from original
CC-BL-14: Zero-vertex Mesh → counted as no geometry (falls through to aggregate)
CC-BL-15: Non-finite vertex via evaluated geometry → FAIL NON_FINITE
CC-BL-16: Two targets share same Camera object → both PASS independently
CC-BL-17: Entry PASS — valid spec + scene, camera check passes
CC-BL-18: Entry FAIL — camera not found
CC-BL-19: Entry ERROR — depsgraph acquisition fails (e.g., None scene)
CC-BL-20: Multiple targets, one camera fail, one camera pass → correct per-target results

ALL .blend FILES: TEMPORARY (created by runner, cleaned after)
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
  — Entry integration: call order, checks writing, NOT_CHECKED templates,
    _collect_target_errors
  — Focused CPython tests (~40)
  — Scope Guard adjustment (test_asset_scene_preflight_blender_scene_basic.py,
    test_asset_scene_preflight_blender_visibility_i2.py)

I2 — Blender 5.1.2 Validation:
  — blender_camera_check_validation_runner.py (20 scenarios)
  — test_asset_scene_preflight_camera_check_blender.py (pytest wrapper)
  — 修复 I2 发现的直接生产或测试问题

E — Final Regression:
  — Camera Check focused tests 全部通过
  — 既有字段组 direct regression
  — protocol_guard full unfiltered regression
  — (状态同步和正式锁定为单独后续任务)

DEFAULT_PER_IMPLEMENTATION_ROUND:
  — NO_REPORT (unless task explicitly requires)
  — NO_ZIP
  — NO_MANIFEST
  — NO_SHA256_LIST
  — DIRECT_UPLOAD (1-3 files)
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
DF-08  | bbox ordering → pre-open validation (same as projection_groups) | §5.3
DF-09  | bbox [0,1] range → pre-open validation                   | §5.3
DF-10  | extra pre-open: mvc<=8, bbox order, bbox [0,1]           | §5.3
DF-11  | mvc max = 8                                              | §5.3
DF-12  | 7 failure_codes, precedence defined                      | §14
DF-13  | CAMERA_CHECK_COMPUTATION_ERROR, 17 operations            | §15
DF-14  | containment model, all 4 edges inward, spec-sourced      | §11

DG-01  | NOT_CHECKED 条件 §12 已定义                              | §12.1
DG-02  | 11 种结果字典形态 §13 已定义                             | §13
DG-03  | bbox 顺序 pre-open 统一，无需结果层处理                  | §5.3
```

## 24. Machine-Readable Summary

```text
TASK_ID: CAMERA_CHECK_DESIGN_R1
TASK_TYPE: COMPLETE_RUNTIME_DESIGN
MASTER_MAP_VERSION: R77

RECOVERED_R1_SOURCE_VALIDATION: VERIFIED_VIA_TASK_SPECIFICATION
RECOVERED_R1_SOURCE_USED: TRUE
  — R1 §19 algorithm (§10), §12 noted as superseded, §20 covered by R2 framework

DESIGN_FILE: reviews/CAMERA_CHECK_DESIGN_R1.md
DESIGN_STATUS: COMPLETED_PENDING_INDEPENDENT_REVIEW
DESIGN_VERSION: R1

ALL_DF_01_TO_DF_14_DECIDED: TRUE
ALL_DG_01_TO_DG_03_CLOSED: TRUE
UNRESOLVED_RUNTIME_SEMANTICS: 0

RESULT_DICT_FORM_COUNT: 11
FAILURE_CODE_COUNT: 7
ERROR_OPERATION_COUNT: 17
CPYTHON_TEST_SCENARIO_COUNT: ~40
BLENDER_TEST_SCENARIO_COUNT: ~20
IMPLEMENTATION_STAGE_COUNT: 3 (I1 + I2 + E)

TRUE_CONTRACT_CONFLICT_COUNT: 0
TRUE_BLOCKING_ISSUES: 0

FORMALLY_LOCKED: FALSE
IMPLEMENTATION_AUTHORIZED: FALSE

FIXED_SCOPE_GEOMETRY: target.geometry_scope + R2 §4 evaluated depsgraph
FIXED_SCOPE_PROJECTION: R1 §19 8-corner algorithm, world_to_camera_view
FIXED_SCOPE_SCHEMA: 6 leaf fields (14A Core locked)
FIXED_SCOPE_PREOPEN: 4 extra validation rules
FIXED_SCOPE_MODEL: containment (target screen bbox within required_screen_bbox)
FIXED_SCOPE_VALUES: BOUNDARY_VALUES_SOURCE = SPEC_REQUIRED_SCREEN_BBOX
HARDCODED_PERCENTAGE_VALUES_ALLOWED: FALSE

SIDE_EFFECTS:
  REAL_PROJECT_BLEND_OPENED: FALSE
  REAL_PROJECT_BLEND_SAVED: FALSE
  RENDER_EXECUTED: FALSE
  SAVE_FORBIDDEN: TRUE
  TRANSFORM_MODIFICATION_FORBIDDEN: TRUE
  MATERIAL_MODIFICATION_FORBIDDEN: TRUE
  COLLECTION_MODIFICATION_FORBIDDEN: TRUE
  READ_ONLY: TRUE
```

---

*Design R1 complete. All 14 DFs decided, all 3 DGs closed. Zero unresolved runtime semantics. Implementation NOT authorized — pending independent review and user formal lock approval.*
