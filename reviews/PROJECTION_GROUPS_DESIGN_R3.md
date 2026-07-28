# Projection Groups Runtime Design R3

```text
DOCUMENT_ID: PROJECTION_GROUPS_DESIGN
DESIGN_VERSION: R3
TASK_ID: PROJECTION_GROUPS_DESIGN_R3_CORRECTION
SOURCE_DESIGN_VERSION: R2
TARGET_DESIGN_VERSION: R3
MASTER_MAP_VERSION: R79
DATE: 2026-07-26
DESIGN_STATUS: COMPLETED_PENDING_INDEPENDENT_REVIEW
FORMALLY_LOCKED: FALSE
IMPLEMENTATION_AUTHORIZED: FALSE
DESIGN_AUTHORIZATION: USER_EXPLICITLY_AUTHORIZED

BASELINE_COMMIT: d44679fc11c5069a17277395bb6c52b5a6dfc799
REFERENCE_DESIGN: CAMERA_CHECK_DESIGN_R2.md (FORMALLY_LOCKED)

R3_CORRECTIONS:
  C1: target_ids root failures → FAIL ROOT_OBJECT_NOT_FOUND / ROOT_OBJECT_TYPE_MISMATCH
       / ERROR RESOLVE_TARGET_GEOMETRY (不再静默忽略)
  C2: world_to_camera_view(scene, camera_obj, Vector(corner_ws)) — 与 Camera Check 一致
  C3: 检查顺序 screen bbox → mvc — 与 Camera Check R1 §19 step 6 一致
  C4: PRE_OPEN_RULE_COUNT=6, FAILURE_CODE_COUNT=12, RESULT_DICT_FORM_COUNT=14
       ERROR 固定 6 键, PASS/FAIL 固定 16 键所有字段始终存在
```

---

## 1. 权威来源与优先级

```text
PRIORITY_1: ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md §10.2
  — AUTHORITATIVE_IMPLEMENTATION_CONTRACT:
    Global Projection Groups (New) — 唯一直接定义 projection_groups 的合同来源。

PRIORITY_2: asset_scene_preflight_core.py L223-274, L701-740
  — LOCKED_SCHEMA:
    _validate_spec projection_groups 验证 + _base_result/build_*_result

PRIORITY_3: CAMERA_CHECK_DESIGN_R2.md (FORMALLY_LOCKED)
  — REFERENCE_IMPLEMENTATION_PATTERN:
    投影算法 (§9 R1 §19: 8-corner → z-filter → screen bbox → mvc)、
    evaluated geometry (§8)、camera 查找 (§6)、
    screen bbox 检查 (§10)、result dict (§11)、cleanup contract (§8.2)

PRIORITY_4: blender_scene_reader.py L3017, L3066
  — PRODUCTION_REFERENCE:
    world_to_camera_view(scene, camera_obj, corner) — scene 为第一参数
    R1 §19 step 6: screen bbox check before mvc

PRIORITY_5: PROJECTION_GROUPS_ORIGINAL_REQUIREMENT_AUDIT_REPORT.md (R2 Correction)
  — DESIGN_INPUT: 15 fixed requirements, 32 design freedoms, 8 documentation gaps.
```

---

## 2. 设计目标

1. 为 Projection Groups 字段组定义唯一、完整、可独立实现和测试的运行时设计。
2. 关闭原始需求审计中的全部 32 项 DESIGN_FREEDOM 和 8 项 DOCUMENTATION_GAP。
3. 全文内部一致：无计数冲突、优先级与检查顺序一致、pre-open 规则数 6。
4. 结果字典：PASS/FAIL 固定 16 键，ERROR 固定 6 键，所有字段始终存在。
5. 所有异常路径有唯一 operation，所有 FAIL 有唯一 failure_code。
6. Projection Groups 独立物化 scene.objects，不依赖 _target_caches。
7. target_ids 中任何 root 失败即 FAIL/ERROR，不静默忽略。
8. 组级 ERROR 通过 build_error_result 的 projection_groups 参数完整保留。
9. 复用 Camera Check 的 world_to_camera_view(scene, camera_obj, Vector(corner)) 签名。
10. 检查顺序 screen bbox → mvc，与 Camera Check R1 §19 一致。

---

## 3. 固定范围与明确非目标

```text
FIXED_SCOPE:
  — 10-leaf-field schema (7 direct fields)
  — target_ids 保持 spec 顺序 (R2 §11.2)
  — target_ids 使用对应 target 的 geometry_scope
  — additional_object_names 使用对象自身 full MESH geometry
  — 所有来源按对象 identity 去重后形成 union world bbox
  — 几何来源为 evaluated geometry (R2 §4)
  — 任一 evaluated mesh 零顶点或非有限顶点必须 FAIL (R2 §4.3)
  — world_to_camera_view(scene, camera_obj, Vector(corner_ws))
  — projection_group_results 按 group_id 排序 (R2 §11.2)
  — 检查只证明几何边界，不证明视觉质量 (R2 §10.3)
  — required_screen_bbox mixed axial model (X containment, Y coverage)
  — to_mesh_clear() in finally block

EXPLICITLY_EXCLUDED:
  — 遮挡 (ray casting / occlusion)
  — 视觉质量、美学判断
  — 相机排查顺序 — DEFER_REQUIRES_STATE
  — 保存重开持久化、渲染结果
  — 修改 Camera Check 已锁定设计、生产代码或测试
  — 修改 per_target_results 结构
  — 修改 _check_root_objects 的 _target_caches 逻辑

MUST_NOT_MODIFY:
  — 14A Core schema (_validate_spec)
  — Camera Check 生产代码和测试
  — _check_root_objects 返回值结构
  — Hierarchy 到 Camera Check 的任何已锁定内容
  — 任何已锁定设计或锁定记录
```

---

## 4. 场景缓存与读取次数

### 4.1 独立场景物化

```text
Projection Groups 不依赖 _check_root_objects 的 _target_caches。
_target_caches 仅在 camera_check-enabled target 存在且 root 匹配成功时填充。

Projection Groups 在自身入口独立物化 scene.objects：

  _pg_scene_cache = None

  def _ensure_pg_scene_cache(scene):
      nonlocal _pg_scene_cache
      if _pg_scene_cache is not None:
          return _pg_scene_cache
      try:
          scene_objects_ordered = list(scene.objects)
      except Exception:
          return {"error": True, "operation": "READ_SCENE_OBJECTS"}
      scene_name_by_id = {}
      try:
          for obj in scene_objects_ordered:
              scene_name_by_id[id(obj)] = obj.name
      except Exception:
          return {"error": True, "operation": "READ_SCENE_OBJECTS"}
      _pg_scene_cache = {
          "scene_objects_ordered": scene_objects_ordered,
          "scene_name_by_id": scene_name_by_id,
          "scene_member_ids": {id(o) for o in scene_objects_ordered},
          "scene_materialization_index": {
              id(o): idx for idx, o in enumerate(scene_objects_ordered)
          },
      }
      return _pg_scene_cache

SCENE_OBJECTS_MATERIALIZATION_COUNT: 1
```

### 4.2 Depsgraph

```text
整个 Projection Groups 检查中 depsgraph 只获取一次。
所有投影组共享同一个 depsgraph。
COUNT: ≤ 1
```

### 4.3 obj.name / obj.type / matrix_world 读取

```text
obj.name:
  — camera 和 additional_object 匹配均通过 scene_name_by_id (已在 cache)
obj.type:
  — camera_obj.type: 一次
  — additional_object: 仅对匹配到的对象检查 type
matrix_world:
  — camera_obj.matrix_world: 每个投影组一次
  — evaluated.matrix_world: 每个 evaluated mesh 一次
```

### 4.4 Scope Guard

```text
需确认 _check_projection_groups 在授权集合中。
其调用的 world_to_camera_view, matrix_world, evaluated_depsgraph_get,
evaluated_get, to_mesh, to_mesh_clear, _collect_geometry_scope_objects
已在 Camera Check 授权中。
```

---

## 5. 配置和启用语义

### 5.1 启用判定

```text
ENABLED:
  spec.projection_groups is not None AND isinstance(projection_groups, list)
  → _check_projection_groups 执行

DISABLED (null):
  → _base_result 的 projection_group_results: []

EMPTY ([]):
  → projection_group_results: []
  → 合法：没有投影组需要检查
```

### 5.2 与顶层 result 的关系

```text
projection_group_overall:
  "PASS"  — null, [], 或所有 enabled group 的 result 为 PASS
  "FAIL"  — 无 ERROR，至少一个 group 的 result 为 FAIL
  "ERROR" — 至少一个 group 的 result 为 ERROR

顶层判定 (_validate_and_open_spec):

  if (target_error or global_collection_error
      or projection_group_overall == "ERROR"):
      → EXIT_ERROR
      → build_error_result(..., projection_groups=pg_results)
      → err_msgs 含每组 ERROR 的摘要

  elif (any_scene_fail or any_target_fail or global_collection_fail
        or projection_group_overall == "FAIL"):
      → EXIT_FAIL
      → build_fail_result(..., projection_groups=pg_results)

  else:
      → EXIT_PASS
      → build_pass_result(..., projection_groups=pg_results)
```

### 5.3 输出键存在性

```text
projection_groups 为 null 或 []:
  projection_group_results: [] (来自 _base_result)

projection_groups 非空:
  projection_group_results: [每个投影组的 per-group result dict]

BUILD_ERROR_RESULT 扩展:
  def build_error_result(spec, spec_sha256, input_errors,
                         projection_groups=None):
      r = _base_result(spec, spec_sha256)
      r["result"] = "ERROR"
      if input_errors:
          r["input_errors"] = list(input_errors)
      if projection_groups is not None:
          r["projection_group_results"] = projection_groups
      return r

  当 projection_group_overall == "ERROR":
    — build_error_result 收到 projection_groups=pg_results
    — 每组 ERROR 详情完整保留
    — input_errors 同时含摘要行
  pre-open ERROR (reader 之前):
    — projection_groups=None → _base_result 保留 []
```

---

## 6. Pre-open 专用字段关系验证

### 6.1 验证函数

```text
FUNCTION: _validate_projection_groups_rules_preopen(spec)
LOCATION: asset_scene_preflight_check.py
CALL SITE: _validate_and_open_spec，在 _validate_camera_check_rules_preopen 之后

14A Schema 已涵盖（pre-open 不重复）：
  — group_id 非空 + 唯一、target_ids 引用、camera_object_name 非空
  — mvc >= 0 (非 bool 整数)、bbox 四个有限数值、非 bool
  — bbox min_left ≤ max_right、min_bottom ≤ max_top
  — require_camera_outside_world_bbox 为 bool

Pre-open 验证新增以下 6 条规则：
```

### 6.2 验证规则 (共 6 条)

```text
RULE_1: minimum_visible_projected_corner_count <= 8
  ERROR: INVALID_PROJECTION_GROUP_RULE_VALUE:
         group_id '{gid}' mvc > 8
  RATIONALE: 联合 bbox 8 个角点，mvc > 8 永无法满足。

RULE_2: required_screen_bbox 四个值位于 [0, 1]
  ERROR: INVALID_PROJECTION_GROUP_RULE_VALUE:
         group_id '{gid}' required_screen_bbox.{k} = {v} out of [0, 1]
  RATIONALE: 屏幕归一化范围内的业务边界。

RULE_3: additional_object_names 每个元素为 non-empty string
  ERROR: INVALID_PROJECTION_GROUP_RULE_VALUE:
         group_id '{gid}' additional_object_names[{j}] must be non-empty

RULE_4: target_ids 无重复 target_id
  ERROR: INVALID_PROJECTION_GROUP_RULE_VALUE:
         group_id '{gid}' duplicate target_id '{tid}'

RULE_5: additional_object_names 无重复名称
  ERROR: INVALID_PROJECTION_GROUP_RULE_VALUE:
         group_id '{gid}' duplicate name '{name}'

RULE_6: target_ids 和 additional_object_names 不得同时为空
  ERROR: INVALID_PROJECTION_GROUP_RULE_VALUE:
         group_id '{gid}' both are empty
```

---

## 7. Camera 查找

```text
复用 Camera Check 的 camera 查找合同 (CAMERA_CHECK_DESIGN_R2 §6)。

每个投影组独立查找其 camera_object_name。

ALGORITHM (per group, 使用 §4.1 的 _pg_scene_cache):
  通过 scene_name_by_id 查找 camera_object_name
  遍历 scene_objects_ordered 进行精确区分大小写匹配

  零匹配 → FAIL CAMERA_OBJECT_NOT_FOUND
  多匹配 → FAIL CAMERA_OBJECT_NOT_FOUND
  camera_obj.type != 'CAMERA' → FAIL CAMERA_TYPE_MISMATCH
  name/type 读取异常 → ERROR RESOLVE_CAMERA_OBJECT

FORBIDDEN:
  bpy.context.scene
  bpy.data.objects.get()
  bpy.data.cameras
  scene.camera
```

---

## 8. 联合几何收集

### 8.1 来源对象收集 (No Silent Skip)

```text
SOURCE_1: target_ids 中每个 target (按 spec 顺序)
  — 从 per_target_results 按 target_id 查找对应 target result
  — 读取 checks.object_exists 和 checks.object_type:
      object_exists.result == "PASS" AND object_type.result == "PASS"
        → 使用 _collect_geometry_scope_objects 获取 MESH
      object_exists.failure_code == "ROOT_OBJECT_NOT_FOUND"
        → FAIL ROOT_OBJECT_NOT_FOUND (整组立即返回)
      object_type.failure_code == "ROOT_OBJECT_TYPE_MISMATCH"
        → FAIL ROOT_OBJECT_TYPE_MISMATCH (整组立即返回)
      object_exists.result == "ERROR" (AMBIGUOUS_ROOT_OBJECT_NAME
        / ROOT_LOOKUP_ERROR)
        → ERROR RESOLVE_TARGET_GEOMETRY (整组立即返回)
      per_target_results 中找不到 target_id (结构异常)
        → ERROR RESOLVE_TARGET_GEOMETRY

  多个 target 同时失败时：按 target_ids 的 spec 顺序选择第一个结果。

SOURCE_2: additional_object_names 中每个名称
  — 在 scene_name_by_id 中精确查找
  — 零匹配 → FAIL ADDITIONAL_OBJECT_NOT_FOUND
  — 多匹配 → FAIL ADDITIONAL_OBJECT_NOT_FOUND
  — 唯一匹配 + type != 'MESH' → FAIL ADDITIONAL_OBJECT_TYPE_MISMATCH
  — 唯一匹配 + type == 'MESH' → 计入联合几何
  — name/type 读取异常 → ERROR RESOLVE_ADDITIONAL_OBJECT
```

### 8.2 去重

```text
所有成功收集的 MESH 对象按 Python id(obj) 去重。
去重时机：target_ids 和 additional_object_names 全部解析完毕后。
```

### 8.3 空来源

```text
去重后 mesh_objects 为空：
  → FAIL NO_EVALUATED_GEOMETRY
```

---

## 9. Evaluated Geometry 算法

```text
完全复用 Camera Check 的 evaluated geometry 算法
(CAMERA_CHECK_DESIGN_R2 §8)，mesh_objects 来自 §8 的联合收集：

1. depsgraph = 共享 depsgraph (已在 §4.2 获取)
   (ERROR GET_EVALUATED_DEPSGRAPH)

2. mesh_objects = 联合收集 + 去重结果
   if len(mesh_objects) == 0 → FAIL NO_EVALUATED_GEOMETRY

3. pending_zero_vertex = False
   pending_non_finite = False
   evaluated_mesh_names = []
   all_world_vertices = []

   for mesh_obj, mesh_name in mesh_objects:
       evaluated = mesh_obj.evaluated_get(depsgraph)
       (ERROR EVALUATED_GET)
       mesh = evaluated.to_mesh()
       (ERROR TO_MESH)
       evaluated_mesh_names.append(mesh_name)
       try:
           mw = evaluated.matrix_world
           (ERROR READ_EVALUATED_MATRIX_WORLD)
           if len(mesh.vertices) == 0:
               pending_zero_vertex = True; continue
           for v in mesh.vertices:
               vertex_co = v.co
               (ERROR READ_MESH_VERTICES)
               world_co = mw @ vertex_co
               (ERROR TRANSFORM_VERTEX_TO_WORLD_SPACE)
               if not (isfinite(world_co.x) and isfinite(world_co.y)
                       and isfinite(world_co.z)):
                   pending_non_finite = True; continue
               all_world_vertices.append(world_co)
       finally:
           evaluated.to_mesh_clear()
           (ERROR TO_MESH_CLEAR — overrides ALL pending)

4. if pending_non_finite → FAIL NON_FINITE_EVALUATED_VERTEX
   elif pending_zero_vertex → FAIL NO_EVALUATED_GEOMETRY
   elif len(all_world_vertices) == 0 → FAIL NO_EVALUATED_GEOMETRY

5. to_mesh_clear() 在 finally 块中。
   主异常 + cleanup 异常 → cleanup ERROR 优先。
```

---

## 10. Union World Bbox 与投影

### 10.1 Union World Bbox

```text
从 all_world_vertices 计算联合 world-space bbox：
  min_x, max_x, min_y, max_y, min_z, max_z

8 个 bbox 角点（世界空间）：
  C0: (min_x, min_y, min_z)    C4: (min_x, min_y, max_z)
  C1: (max_x, min_y, min_z)    C5: (max_x, min_y, max_z)
  C2: (min_x, max_y, min_z)    C6: (min_x, max_y, max_z)
  C3: (max_x, max_y, min_z)    C7: (max_x, max_y, max_z)
```

### 10.2 8 角点投影算法

```text
复用 R1 §19 投影算法。
签名与 Camera Check 生产代码一致：
  from bpy_extras.object_utils import world_to_camera_view
  from mathutils import Vector

  projected = world_to_camera_view(scene, camera_obj, Vector(corner_ws))
  返回 (projected_x, projected_y, projected_z)

检查顺序与 Camera Check R1 §19 step 6 一致：

1. 8 个 bbox 角点逐一执行 world_to_camera_view(scene, camera_obj, Vector(c))
2. 丢弃 projected_z <= 0 的角点
3. 剩余 0 个 → FAIL BEHIND_CAMERA
4. 计算 screen bbox: min_x, max_x, min_y, max_y
5. 检查 screen bbox 满足 required_screen_bbox (→ §11)
6. 检查 surviving corners >= mvc (→ INSUFFICIENT_VISIBLE_PROJECTED_CORNERS)
7. PASS

world_to_camera_view 调用异常 → ERROR PROJECT_BBOX_CORNER
```

### 10.3 边界语义

```text
projected_z <= 0 → 丢弃 (含 z == 0)

required_screen_bbox 包含相等：
  screen_min_x >= min_left, screen_max_x <= max_right
  screen_min_y <= min_bottom, screen_max_y >= max_top
```

---

## 11. Screen Bbox 检查模型

```text
HORIZONTAL_MODEL: SAFE_MARGIN_CONTAINMENT
  screen_min_x >= min_left AND screen_max_x <= max_right

VERTICAL_MODEL: MINIMUM_COVERAGE
  screen_min_y <= min_bottom AND screen_max_y >= max_top

不满足 → FAIL SCREEN_BBOX_REQUIREMENT_NOT_MET
  failed_checks: ["horizontal_containment"] / ["vertical_coverage"] / 两者
```

---

## 12. require_camera_outside_world_bbox

```text
条件: require_camera_outside_world_bbox == true

camera_world_loc = camera_obj.matrix_world.translation

inside = (
    union_min_x <= camera.x <= union_max_x AND
    union_min_y <= camera.y <= union_max_y AND
    union_min_z <= camera.z <= union_max_z
)

if require_camera_outside_world_bbox and inside:
    → FAIL CAMERA_INSIDE_WORLD_BBOX
    面上算 inside (camera.x == min_x → FAIL)

if require_camera_outside_world_bbox and not inside:
    → 满足

require_camera_outside_world_bbox == false:
    → 不检查，字段始终存在于结果中 (值为 false)
```

---

## 13. 失败优先级与检查顺序

### 13.1 Per-Group 优先级与检查顺序 (一致)

```text
优先级与检查顺序完全一致 (从高到低)：

  ERROR                                          (优先级 0)
    RESOLVE_CAMERA_OBJECT / RESOLVE_ADDITIONAL_OBJECT /
    READ_SCENE_OBJECTS / RESOLVE_TARGET_GEOMETRY /
    COLLECT_GEOMETRY_SCOPE / GET_EVALUATED_DEPSGRAPH /
    EVALUATED_GET / TO_MESH / READ_EVALUATED_MATRIX_WORLD /
    READ_MESH_VERTICES / TRANSFORM_VERTEX_TO_WORLD_SPACE /
    TO_MESH_CLEAR / COMPUTE_UNION_BBOX / PROJECT_BBOX_CORNER
      (任一异常 → 立即返回 ERROR)

  > CAMERA_OBJECT_NOT_FOUND                       (优先级 1)
  > CAMERA_TYPE_MISMATCH                          (优先级 2)
  > ADDITIONAL_OBJECT_NOT_FOUND                   (优先级 3)
  > ADDITIONAL_OBJECT_TYPE_MISMATCH               (优先级 4)
  > ROOT_OBJECT_NOT_FOUND                         (优先级 5)
  > ROOT_OBJECT_TYPE_MISMATCH                     (优先级 6)
  > NON_FINITE_EVALUATED_VERTEX                   (优先级 7)
  > NO_EVALUATED_GEOMETRY                         (优先级 8)
  > BEHIND_CAMERA                                 (优先级 9)
  > SCREEN_BBOX_REQUIREMENT_NOT_MET               (优先级 10)
  > INSUFFICIENT_VISIBLE_PROJECTED_CORNERS        (优先级 11)
  > CAMERA_INSIDE_WORLD_BBOX                      (优先级 12)
  > PASS                                          (优先级 13)

短路径：遇到第一个非 PASS 结果立即返回。
```

### 13.2 运行时检查顺序 (per group)

```text
1.  camera_object_name 解析
2.  target_ids root 前置条件检查 (per_target_results — 遇 FAIL/ERROR 即返回)
3.  additional_object_names 解析
4.  去重
5.  空来源检查
6.  depsgraph 获取
7.  evaluated geometry 迭代
8.  union bbox 计算
9.  8 角点投影 (world_to_camera_view)
10. screen bbox 检查 (§11)
11. mvc 检查 (surviving_corners >= mvc)
12. require_camera_outside_world_bbox 检查 (§12)
13. PASS
```

---

## 14. 结果字典

### 14.1 统一键集合

```text
PASS/FAIL: 固定 16 键，所有字段始终存在，不可用时为 null

  1.  result              — "PASS" / "FAIL"
  2.  group_id            — 来自 spec
  3.  target_ids          — 保持 spec 顺序
  4.  camera_object_name  — 来自 spec
  5.  evaluated_mesh_names— [string, ...] 或 []
  6.  surviving_corners   — int 或 null
  7.  screen_bbox         — {min_x, max_x, min_y, max_y} 或 null
  8.  required_screen_bbox— {min_left, max_right, min_bottom, max_top}
  9.  minimum_visible_projected_corner_count — int
  10. camera_world_location— [x, y, z] 或 null
  11. require_camera_outside_world_bbox — bool (始终存在)
  12. union_bbox          — {min_x,max_x,min_y,max_y,min_z,max_z} 或 null
  13. per_source_summary  — 见 §16
  14. failed_checks       — [string, ...] 或 null
  15. actual_type         — string 或 null
  16. failure_code        — string 或 null

  PASS:  failure_code=null, failed_checks=null, actual_type=null
  FAIL:  failure_code 有值; failed_checks/actual_type 按需有值/为 null

ERROR: 固定 6 键
  1.  result      — "ERROR"
  2.  group_id    — 来自 spec
  3.  target_ids  — 保持 spec 顺序
  4.  error_type  — "PROJECTION_GROUP_COMPUTATION_ERROR"
  5.  operation   — 见 §15.3
  6.  note        — "{OPERATION}_FAILED"

NON_PARTICIPATING:
  projection_group_results: []
```

### 14.2 PASS 示例

```json
{
  "result": "PASS",
  "group_id": "essential_objects",
  "target_ids": ["CHR_MALE_A", "CHR_EMPLOYEE_01"],
  "camera_object_name": "Camera_Persp_3_4",
  "evaluated_mesh_names": ["CHR_Male_Body", "CHR_Employee_Body"],
  "surviving_corners": 8,
  "screen_bbox": {"min_x": 0.12, "max_x": 0.88, "min_y": 0.10, "max_y": 0.92},
  "required_screen_bbox": {"min_left": 0.04, "max_right": 0.96,
                           "min_bottom": 0.15, "max_top": 0.85},
  "minimum_visible_projected_corner_count": 4,
  "camera_world_location": [2.0, -5.0, 3.0],
  "require_camera_outside_world_bbox": true,
  "union_bbox": {"min_x": -1.0, "max_x": 3.0, "min_y": -2.0, "max_y": 2.0,
                 "min_z": 0.0, "max_z": 2.0},
  "per_source_summary": {
    "target_ids": {
      "CHR_MALE_A": {"root_status": "PASS",
                     "geometry_scope": "SELF_AND_DESCENDANT_MESHES",
                     "mesh_objects_found": 2,
                     "mesh_names": ["CHR_Male_Body", "CHR_Male_Clothes"]},
      "CHR_EMPLOYEE_01": {"root_status": "PASS",
                          "geometry_scope": "SELF_MESH",
                          "mesh_objects_found": 1,
                          "mesh_names": ["CHR_Employee_Body"]}
    },
    "additional_object_names": {
      "CashRegister_01": {"status": "found", "type": "MESH", "contributing": true}
    }
  },
  "failed_checks": null,
  "actual_type": null,
  "failure_code": null
}
```

### 14.3 FAIL 示例 (ROOT_OBJECT_NOT_FOUND)

```json
{
  "result": "FAIL",
  "group_id": "essential_objects",
  "target_ids": ["CHR_MALE_A", "CHR_MISSING"],
  "camera_object_name": "Camera_Persp_3_4",
  "failure_code": "ROOT_OBJECT_NOT_FOUND",
  "evaluated_mesh_names": [],
  "surviving_corners": null,
  "screen_bbox": null,
  "required_screen_bbox": {"min_left": 0.04, "max_right": 0.96,
                           "min_bottom": 0.15, "max_top": 0.85},
  "minimum_visible_projected_corner_count": 4,
  "camera_world_location": null,
  "require_camera_outside_world_bbox": false,
  "union_bbox": null,
  "per_source_summary": {
    "target_ids": {
      "CHR_MALE_A": {"root_status": "PASS",
                     "geometry_scope": "SELF_MESH",
                     "mesh_objects_found": 1,
                     "mesh_names": []},
      "CHR_MISSING": {"root_status": "ROOT_OBJECT_NOT_FOUND",
                      "geometry_scope": "SELF_MESH",
                      "mesh_objects_found": 0,
                      "mesh_names": []}
    },
    "additional_object_names": {}
  },
  "failed_checks": null,
  "actual_type": null
}
```

### 14.4 FAIL 示例 (SCREEN_BBOX_REQUIREMENT_NOT_MET)

```json
{
  "result": "FAIL",
  "group_id": "essential_objects",
  "target_ids": ["CHR_MALE_A"],
  "camera_object_name": "Camera_Persp_3_4",
  "failure_code": "SCREEN_BBOX_REQUIREMENT_NOT_MET",
  "evaluated_mesh_names": ["CHR_Male_Body"],
  "surviving_corners": 8,
  "screen_bbox": {"min_x": -0.05, "max_x": 0.88, "min_y": 0.10, "max_y": 0.92},
  "required_screen_bbox": {"min_left": 0.04, "max_right": 0.96,
                           "min_bottom": 0.15, "max_top": 0.85},
  "minimum_visible_projected_corner_count": 4,
  "camera_world_location": [2.0, -5.0, 3.0],
  "require_camera_outside_world_bbox": false,
  "union_bbox": {"min_x": -1.0, "max_x": 3.0, "min_y": -2.0, "max_y": 2.0,
                 "min_z": 0.0, "max_z": 2.0},
  "per_source_summary": {
    "target_ids": {
      "CHR_MALE_A": {"root_status": "PASS",
                     "geometry_scope": "SELF_MESH",
                     "mesh_objects_found": 1,
                     "mesh_names": ["CHR_Male_Body"]}
    },
    "additional_object_names": {}
  },
  "failed_checks": ["horizontal_containment"],
  "actual_type": null
}
```

### 14.5 ERROR 示例 (6 keys)

```json
{
  "result": "ERROR",
  "group_id": "essential_objects",
  "target_ids": ["CHR_MALE_A"],
  "error_type": "PROJECTION_GROUP_COMPUTATION_ERROR",
  "operation": "RESOLVE_TARGET_GEOMETRY",
  "note": "RESOLVE_TARGET_GEOMETRY_FAILED"
}
```

---

## 15. Failure Codes、Error Types 和 Operations

### 15.1 Failure Codes (12)

```text
1.  CAMERA_OBJECT_NOT_FOUND
    — 相机零匹配或多匹配

2.  CAMERA_TYPE_MISMATCH
    — 相机对象存在但 type != 'CAMERA'

3.  ADDITIONAL_OBJECT_NOT_FOUND
    — additional_object_names 中对象零匹配或多匹配

4.  ADDITIONAL_OBJECT_TYPE_MISMATCH
    — additional_object_names 中对象不是 MESH

5.  ROOT_OBJECT_NOT_FOUND
    — target_ids 中某 target 的 root 未在场景中找到

6.  ROOT_OBJECT_TYPE_MISMATCH
    — target_ids 中某 target 的 root type 与 spec 不匹配

7.  NON_FINITE_EVALUATED_VERTEX
    — 任一 evaluated mesh 顶点世界坐标为 NaN 或 Inf

8.  NO_EVALUATED_GEOMETRY
    — 去重后零 MESH / 所有 MESH 零顶点 / 所有顶点被非有限过滤

9.  BEHIND_CAMERA
    — 所有 8 个 bbox 角点 projected_z <= 0

10. SCREEN_BBOX_REQUIREMENT_NOT_MET
    — screen bbox 不满足 required_screen_bbox

11. INSUFFICIENT_VISIBLE_PROJECTED_CORNERS
    — surviving corners < minimum_visible_projected_corner_count

12. CAMERA_INSIDE_WORLD_BBOX
    — require_camera_outside_world_bbox=true 且相机在 union bbox 内/面上
```

### 15.2 Error Types (1)

```text
PROJECTION_GROUP_COMPUTATION_ERROR
```

### 15.3 Operations (14)

```text
1.  RESOLVE_CAMERA_OBJECT          — camera name/type 读取异常
2.  RESOLVE_ADDITIONAL_OBJECT      — additional_object name/type 读取异常
3.  READ_SCENE_OBJECTS             — scene.objects 物化失败
4.  RESOLVE_TARGET_GEOMETRY        — per_target_results 结构异常或 target root 查找异常
5.  COLLECT_GEOMETRY_SCOPE         — _collect_geometry_scope_objects RuntimeError
6.  GET_EVALUATED_DEPSGRAPH        — depsgraph 获取失败
7.  EVALUATED_GET                  — obj.evaluated_get 失败
8.  TO_MESH                        — evaluated.to_mesh() 失败
9.  TO_MESH_CLEAR                  — to_mesh_clear() 失败 (覆盖 pending)
10. READ_EVALUATED_MATRIX_WORLD    — matrix_world 读取失败
11. READ_MESH_VERTICES             — mesh.vertices / v.co 读取失败
12. TRANSFORM_VERTEX_TO_WORLD_SPACE— mw @ vertex_co 失败
13. COMPUTE_UNION_BBOX             — bbox 计算异常
14. PROJECT_BBOX_CORNER            — world_to_camera_view 调用异常
```

---

## 16. Per-Source 结果跟踪

```text
per_source_summary (PASS 和 FAIL 均完整填充):

target_ids (按 spec 顺序):
  每个 target_id → {
    "root_status": "PASS" | "ROOT_OBJECT_NOT_FOUND" |
                   "ROOT_OBJECT_TYPE_MISMATCH" | "ROOT_LOOKUP_ERROR",
    "geometry_scope": spec 中的值,
    "mesh_objects_found": int,
    "mesh_names": [string, ...]
  }

additional_object_names (按 spec 顺序):
  每个名称 → {
    "status": "found" | "not_found" | "ambiguous",
    "type": "MESH" | actual_type | null,
    "match_count": int (仅 ambiguous),
    "contributing": true/false
  }
```

---

## 17. 入口集成

### 17.1 open_blend_and_get_scene 修改

```text
新增参数 projection_groups_block。

在 per-target loop 全部完成后调用:
  pg_results = _check_projection_groups(
      scene, projection_groups_block,
      per_target_results, targets=targets,
  )
  scene_data["projection_group_results"] = pg_results

不传入 _target_caches。使用 §4.1 的独立缓存。
```

### 17.2 _validate_and_open_spec 修改

```text
PRE-OPEN:
  pg_errs = _validate_projection_groups_rules_preopen(spec)
  pre_open_errs.extend(pg_errs)

READER:
  projection_groups_block = spec.get("projection_groups")
  scene_data = reader.open_blend_and_get_scene(
      abs_blend, spec["scene_name"], scene_rules, targets,
      collection_rules_block=collection_rules_block,
      projection_groups_block=projection_groups_block,
  )

OVERALL:
  pg_results = scene_data.get("projection_group_results", [])
  projection_group_overall = _compute_projection_group_overall(pg_results)

ERROR PATH:
  if target_error or global_collection_error
     or projection_group_overall == "ERROR":
      err_msgs = [...]
      if projection_group_overall == "ERROR":
          for pg in pg_results:
              if pg.get("result") == "ERROR":
                  err_msgs.append(
                      f"PROJECTION_GROUP_COMPUTATION_ERROR: "
                      f"group_id='{pg['group_id']}' "
                      f"operation='{pg.get('operation','UNKNOWN')}'"
                  )
      return (EXIT_ERROR,
              build_error_result(spec, spec_sha, err_msgs,
                                 projection_groups=pg_results))

FAIL PATH:
      return (EXIT_FAIL,
              build_fail_result(spec, spec_sha,
                  per_target=per_target_results,
                  global_r=global_results,
                  projection_groups=pg_results))

PASS PATH:
      return (EXIT_PASS,
              build_pass_result(spec, spec_sha,
                  per_target=per_target_results,
                  global_r=global_results,
                  projection_groups=pg_results))
```

### 17.3 _compute_projection_group_overall

```text
def _compute_projection_group_overall(pg_results):
    if not pg_results: return "PASS"
    results = [g["result"] for g in pg_results]
    if any(r == "ERROR" for r in results): return "ERROR"
    if any(r == "FAIL" for r in results): return "FAIL"
    return "PASS"
```

### 17.4 build_error_result 扩展

```text
def build_error_result(spec, spec_sha256, input_errors,
                       projection_groups=None):
    r = _base_result(spec, spec_sha256)
    r["result"] = "ERROR"
    if input_errors:
        r["input_errors"] = list(input_errors)
    if projection_groups is not None:
        r["projection_group_results"] = projection_groups
    return r
```

---

## 18. 设计关闭矩阵

### 18.1 DESIGN_FREEDOM 关闭 (DF-PG-01 至 DF-PG-32)

| ID | 最终决定 | 设计节 | 实施 | 测试 |
|----|---------|--------|------|------|
| DF-PG-01 | 结果字典 — PASS/FAIL 16 键, ERROR 6 键 | §14 | I1 | I1 |
| DF-PG-02 | PASS/FAIL/ERROR 条件 | §5.2, §13, §14 | I1 | I1 |
| DF-PG-03 | failure_code — 12 个 | §15.1 | I1 | I1 |
| DF-PG-04 | error_type + operation — 1 type, 14 ops | §15 | I1 | I1 |
| DF-PG-05 | 优先级 = 检查顺序 | §13 | I2 | I2 |
| DF-PG-06 | target_ids 空 → additional only | §8.3 | I2 | I2 |
| DF-PG-07 | target_ids 重复 → pre-open ERROR | §6.2 RULE_4 | I1 | I1 |
| DF-PG-08 | additional_object_names 空 → 正常 | §8.1 | I2 | I2 |
| DF-PG-09 | 都空 → pre-open ERROR | §6.2 RULE_6 | I1 | I1 |
| DF-PG-10 | additional 不存在 → FAIL | §8.1 | I2 | I2 |
| DF-PG-11 | additional 非 MESH → FAIL | §8.1 | I2 | I2 |
| DF-PG-12 | 重复对象 → id() 去重 | §8.2 | I2 | I2 |
| DF-PG-13 | camera 解析 → 复用 Camera Check | §7 | I2 | I2 |
| DF-PG-14 | 相机不在 Scene → FAIL | §7 | I2 | I2 |
| DF-PG-15 | type != CAMERA → FAIL | §7 | I2 | I2 |
| DF-PG-16 | 多匹配 → FAIL | §7 | I2 | I2 |
| DF-PG-17 | 8 角点投影 — 复用 R1 §19 | §10.2 | I2 | I2 |
| DF-PG-18 | mvc > 8 → pre-open ERROR | §6.2 RULE_1 | I1 | I1 |
| DF-PG-19 | mvc = 0 → 允许 | §6.2 | I2 | I2 |
| DF-PG-20 | BEHIND_CAMERA | §10.2 | I2 | I2 |
| DF-PG-21 | mixed axial model | §11 | I2 | I2 |
| DF-PG-22 | camera outside — 逐轴严格外 | §12 | I2 | I2 |
| DF-PG-23 | 空 bbox → NO_EVALUATED_GEOMETRY | §8.3 | I2 | I2 |
| DF-PG-24 | 零顶点/非有限 → FAIL | §9, §14, §15.1 | I2 | I2 |
| DF-PG-25 | per-group 单 result | §14 | I1 | I1 |
| DF-PG-26 | 顶层 projection_group_overall | §5.2 | I1 | I1 |
| DF-PG-27 | 多组聚合 | §5.2, §17.3 | I1 | I1 |
| DF-PG-28 | pre-open — 6 rules | §6 | I1 | I1 |
| DF-PG-29 | 读取次数 — 独立 cache, 单次 depsgraph | §4 | I2 | I2 |
| DF-PG-30 | camera inside bbox → FAIL | §12 | I2 | I2 |
| DF-PG-31 | additional 元素 pre-open | §6.2 RULE_3 | I1 | I1 |
| DF-PG-32 | 配置值源自 spec | §2 | I2 | I2 |

### 18.2 DOCUMENTATION_GAP 关闭 (DG-PG-01 至 DG-PG-08)

| ID | 最终决定 | 设计节 |
|----|---------|--------|
| DG-PG-01 | 以 R2 §10.2 为权威来源 | §1 |
| DG-PG-02 | NOT_CHECKED — 无 per-group; null/[] → 整体跳过 | §5.1, §14.1 |
| DG-PG-03 | 结果字典完整定义 | §14 |
| DG-PG-04 | failure_code/error_type/operation 完整定义 | §15 |
| DG-PG-05 | require_camera_outside_world_bbox 精确语义 | §12 |
| DG-PG-06 | R1 不存在 — 不影响 | §1 |
| DG-PG-07 | Design Spec R1 不含 projection_groups | §1 |
| DG-PG-08 | required_screen_bbox 轴向语义 | §11 |

---

## 19. 实施拆分

```text
I1: pre-open (6 rules)、结果框架、入口集成
  — _validate_projection_groups_rules_preopen
  — build_error_result 扩展
  — _compute_projection_group_overall
  — _validate_and_open_spec 集成
  — open_blend_and_get_scene 参数集成
  — 结果字典精确键集定义
  — CPython 聚焦测试 (~38 tests)

I2: Blender 运行时
  — _check_projection_groups 完整实现
  — 独立场景缓存
  — camera + additional + target_ids 解析
  — 去重 + evaluated geometry + union bbox + 投影
  — screen bbox → mvc → camera outside bbox
  — per_source_summary
  — 单次 depsgraph
  — Scope Guard
  — Blender 场景 (~26 scenarios) + pytest wrapper

E: 回归 + 锁定
  — I1+I2 全部通过
  — 完整 protocol_guard + 14A Core + 直接回归
```

---

## 20. 测试矩阵

### 20.1 I1 CPython Tests (~38 tests)

```text
Pre-open 验证 (10):
  — mvc > 8 → ERROR
  — bbox min_left / max_right / min_bottom / max_top 超出 [0,1] → ERROR (4)
  — additional_object_names 空字符串 → ERROR
  — target_ids 重复 → ERROR
  — additional_object_names 重复 → ERROR
  — target_ids + additional_object_names 都空 → ERROR
  — 全部 valid → 0 errors

启用判定 (4):
  — projection_groups null → []
  — projection_groups [] → []
  — projection_groups 非空 → projection_group_results 非空
  — 全部 PASS → projection_group_overall: PASS

聚合 (5):
  — 任一 ERROR → projection_group_overall: ERROR
  — 任一 FAIL → projection_group_overall: FAIL
  — 全部 PASS → projection_group_overall: PASS
  — projection_group_overall ERROR → EXIT_ERROR + build_error_result 含 pg_results
  — projection_group_overall FAIL → EXIT_FAIL + build_fail_result 含 pg_results

入口集成 (8):
  — build_pass_result 含 projection_group_results
  — build_fail_result 含 projection_group_results
  — build_error_result 含 projection_groups (组级 ERROR)
  — build_error_result 不含 projection_groups (pre-open ERROR) → []
  — pre-open ERROR 阻断
  — 调用链顺序
  — projection_groups_block 传递
  — _collect_target_errors 不收集投影组 ERROR

结果字典键集 (11):
  — PASS 精确 16 键
  — FAIL CAMERA_OBJECT_NOT_FOUND 精确 16 键
  — FAIL ADDITIONAL_OBJECT_NOT_FOUND 精确 16 键
  — FAIL ROOT_OBJECT_NOT_FOUND 精确 16 键
  — FAIL ROOT_OBJECT_TYPE_MISMATCH 精确 16 键
  — FAIL SCREEN_BBOX_REQUIREMENT_NOT_MET 精确 16 键 (含 failed_checks)
  — FAIL NON_FINITE_EVALUATED_VERTEX 精确 16 键
  — FAIL INSUFFICIENT_VISIBLE_PROJECTED_CORNERS 精确 16 键
  — FAIL CAMERA_INSIDE_WORLD_BBOX 精确 16 键
  — ERROR 精确 6 键
  — null 键值验证 (PASS 时 failure_code/failed_checks/actual_type = null)
```

### 20.2 I2 Blender Scenarios (~26 scenarios)

```text
PG-BL-01: single target → geometry_scope → PASS
PG-BL-02: two target_ids → union bbox → PASS
PG-BL-03: target_ids + additional → dedup → PASS
PG-BL-04: overlapping objects (target + additional) → id() dedup → PASS
PG-BL-05: target root not found → FAIL ROOT_OBJECT_NOT_FOUND
PG-BL-06: target root type mismatch → FAIL ROOT_OBJECT_TYPE_MISMATCH
PG-BL-07: target root ambiguous → ERROR RESOLVE_TARGET_GEOMETRY
PG-BL-08: additional not found → FAIL ADDITIONAL_OBJECT_NOT_FOUND
PG-BL-09: additional multi-match → FAIL ADDITIONAL_OBJECT_NOT_FOUND
PG-BL-10: additional non-MESH → FAIL ADDITIONAL_OBJECT_TYPE_MISMATCH
PG-BL-11: camera zero match → FAIL CAMERA_OBJECT_NOT_FOUND
PG-BL-12: camera multi match → FAIL CAMERA_OBJECT_NOT_FOUND
PG-BL-13: camera type mismatch → FAIL CAMERA_TYPE_MISMATCH
PG-BL-14: zero-vertex mesh → FAIL NO_EVALUATED_GEOMETRY
PG-BL-15: non-finite vertex → FAIL NON_FINITE_EVALUATED_VERTEX
PG-BL-16: all corners behind camera → FAIL BEHIND_CAMERA
PG-BL-17: horizontal containment fail → FAIL SCREEN_BBOX_REQUIREMENT_NOT_MET
PG-BL-18: vertical coverage fail → FAIL SCREEN_BBOX_REQUIREMENT_NOT_MET
PG-BL-19: both axes fail → FAIL (failed_checks: 2 items)
PG-BL-20: mvc insufficient → FAIL INSUFFICIENT_VISIBLE_PROJECTED_CORNERS
PG-BL-21: camera inside bbox (require_outside=true) → FAIL CAMERA_INSIDE_WORLD_BBOX
PG-BL-22: camera outside bbox (require_outside=true) → PASS
PG-BL-23: require_camera_outside=false → field present but not checked → PASS
PG-BL-24: two projection groups → independent results + correct aggregation
PG-BL-25: different cameras per group → independent lookup
PG-BL-26: to_mesh_clear exception → ERROR TO_MESH_CLEAR overrides pending

pytest wrapper:
  — all scenarios returncode==0
  — JSON markers exactly once each
  — PASS: 16 keys, FAIL: 16 keys, ERROR: 6 keys
  — target_ids preserves spec order
  — projection_group_results sorted by group_id
  — require_camera_outside_world_bbox always present
  — scene.objects read once before CHECK
```

### 20.3 ERROR operation 覆盖 (14 operations)

```text
RESOLVE_CAMERA_OBJECT          — PG-BL: camera name read exception
RESOLVE_ADDITIONAL_OBJECT      — PG-BL: additional name/type read exception
READ_SCENE_OBJECTS             — PG-BL: scene.objects materialization failure
RESOLVE_TARGET_GEOMETRY        — PG-BL: target root lookup ERROR (ambiguous)
COLLECT_GEOMETRY_SCOPE         — PG-BL: _collect_geometry_scope_objects RuntimeError
GET_EVALUATED_DEPSGRAPH        — PG-BL: depsgraph get failure
EVALUATED_GET                  — PG-BL: evaluated_get failure
TO_MESH                        — PG-BL: to_mesh failure
TO_MESH_CLEAR                  — PG-BL: to_mesh_clear failure (PG-BL-26)
READ_EVALUATED_MATRIX_WORLD    — PG-BL: matrix_world read failure
READ_MESH_VERTICES             — PG-BL: vertices read failure
TRANSFORM_VERTEX_TO_WORLD_SPACE— PG-BL: vertex transform failure
COMPUTE_UNION_BBOX             — PG-BL: bbox compute failure
PROJECT_BBOX_CORNER            — PG-BL: world_to_camera_view failure
```

### 20.4 E 回归范围

```text
完整 protocol_guard 回归
14A Core 回归
直接回归 (Camera Check, Ground Contact, Material Assignment 等)
Scope Guard 回归
```

---

## 21. Scope Guard

```text
需确认 _check_projection_groups 在 AST Scope Guard 授权集合中。
其调用的 world_to_camera_view(scene, camera_obj, Vector(corner)),
matrix_world, evaluated_depsgraph_get, evaluated_get, to_mesh,
to_mesh_clear, _collect_geometry_scope_objects 已在 Camera Check 授权中。
```

---

## 22. 设计统计

```text
RESULT_DICT_FORM_COUNT: 14 (1 PASS + 12 FAIL + 1 ERROR)
FAILURE_CODE_COUNT: 12
ERROR_TYPE_COUNT: 1 (PROJECTION_GROUP_COMPUTATION_ERROR)
ERROR_OPERATION_COUNT: 14
PRE_OPEN_RULE_COUNT: 6
IMPLEMENTATION_STAGE_COUNT: 3 (I1, I2, E)
DESIGN_FREEDOM_CLOSED_COUNT: 32
DOCUMENTATION_GAP_CLOSED_COUNT: 8
UNRESOLVED_DESIGN_DECISIONS: 0
INTERNAL_CONTRADICTION_COUNT: 0
```

---

*Design R3 complete. All 32 design freedoms and 8 documentation gaps closed. No internal contradictions. Awaiting independent review.*
