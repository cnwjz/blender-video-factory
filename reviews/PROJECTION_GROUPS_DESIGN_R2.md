# Projection Groups Runtime Design R2

```text
DOCUMENT_ID: PROJECTION_GROUPS_DESIGN
DESIGN_VERSION: R2
TASK_ID: PROJECTION_GROUPS_DESIGN_R2_CORRECTION
SOURCE_DESIGN_VERSION: R1
TARGET_DESIGN_VERSION: R2
MASTER_MAP_VERSION: R79
DATE: 2026-07-26
DESIGN_STATUS: COMPLETED_PENDING_INDEPENDENT_REVIEW
FORMALLY_LOCKED: FALSE
IMPLEMENTATION_AUTHORIZED: FALSE
DESIGN_AUTHORIZATION: USER_EXPLICITLY_AUTHORIZED

BASELINE_COMMIT: d44679fc11c5069a17277395bb6c52b5a6dfc799
REFERENCE_DESIGN: CAMERA_CHECK_DESIGN_R2.md (FORMALLY_LOCKED)

R2_CORRECTIONS:
  C1: 统一结果合同 — 16 键唯一集合，含 target_ids (spec 顺序)
  C2: 独立场景缓存 — Projection Groups 独立物化 scene.objects，不依赖 _target_caches
  C3: 禁止静默遗漏 — additional_object_names 缺失/多匹配/非 MESH → 明确 FAIL
  C4: 组级 ERROR 集成 — build_error_result 支持 projection_groups，保留完整组级详情
  C5: 消除全文矛盾 — 计数、优先级、测试矩阵、pre-open 规则数全部一致
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
    投影算法 (§9)、evaluated geometry (§8)、camera 查找 (§6)、
    screen bbox 检查 (§10)、result dict (§11)、cleanup contract (§8.2)

PRIORITY_4: R1 §19 (Recovered, embedded in Camera Check Design R2)
  — RETAINED_PROJECTION_ALGORITHM:
    8-corner bbox → world_to_camera_view → z-filter → screen bbox → mvc

PRIORITY_5: PROJECTION_GROUPS_ORIGINAL_REQUIREMENT_AUDIT_REPORT.md (R2 Correction)
  — DESIGN_INPUT: 15 fixed requirements, 32 design freedoms, 8 documentation gaps.
    AUDIT_RESULT: REQUIREMENTS_SUFFICIENT_FOR_DESIGN.
```

---

## 2. 设计目标

1. 为 Projection Groups 字段组定义唯一、完整、可独立实现和测试的运行时设计。
2. 关闭原始需求审计中的全部 32 项 DESIGN_FREEDOM 和 8 项 DOCUMENTATION_GAP。
3. 全文内部一致：无计数冲突、优先级与检查顺序一致、pre-open 规则数与文本一致。
4. 结果字典键集合唯一（统一 16 键），支持 `assert_dict_equal` 精确断言。
5. 所有异常路径有唯一 operation，所有 FAIL 有唯一 failure_code。
6. Projection Groups 独立物化 `scene.objects`，不依赖 Camera Check 的 `_target_caches`。
7. 任何列入 `target_ids` 或 `additional_object_names` 的来源不得在 PASS 路径被静默忽略。
8. 组级 ERROR 通过 `build_error_result` 的 `projection_groups` 参数完整保留。
9. 复用 Camera Check 已锁定的 evaluated geometry、投影算法、camera 查找、screen bbox 模型。
10. required_screen_bbox: X containment + Y minimum coverage，四个值源自 spec。

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
  — 使用 world_to_camera_view
  — projection_group_results 按 group_id 排序 (R2 §11.2)
  — 检查只证明几何边界，不证明视觉质量 (R2 §10.3)
  — required_screen_bbox mixed axial model (X containment, Y coverage)
  — to_mesh_clear() in finally block

EXPLICITLY_EXCLUDED:
  — 遮挡 (ray casting / occlusion)
  — 视觉质量、美学判断
  — 相机排查顺序 — DEFER_REQUIRES_STATE
  — 保存重开持久化
  — 渲染结果
  — 修改 Camera Check 已锁定设计、生产代码或测试
  — 修改 per_target_results 结构
  — 修改 _check_root_objects 的 _target_caches 逻辑
  — dimensions / height / horizontal ratio / landmark / stray objects

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

INIT (在 _check_projection_groups 入口，所有 per-group 循环之前):

  _pg_scene_cache = None  # lazy-init

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
          "scene_materialization_index": {id(o): idx for idx, o
                                          in enumerate(scene_objects_ordered)},
      }
      return _pg_scene_cache

SCENE_OBJECTS_MATERIALIZATION_COUNT: 1
  — scene.objects 在 Projection Groups 入口物化一次。
  — 所有投影组共享同一份 cache。
  — Cache 包含 name→id 映射用于 camera 和 additional_object 查找，
    避免重复读取 obj.name。
```

### 4.2 Depsgraph

```text
DEPGRAPH_MATERIALIZATION:
  整个 Projection Groups 检查中 depsgraph 只获取一次。
  所有投影组共享同一个 depsgraph。

  depsgraph = bpy.context.evaluated_depsgraph_get()
  (ERROR GET_EVALUATED_DEPSGRAPH on failure — 整组级别，
   在第一个投影组需要 depsgraph 时获取)

COUNT: ≤ 1
```

### 4.3 obj.name 和 obj.type 读取

```text
obj.name:
  — camera_object_name 匹配：通过 scene_name_by_id (已在 cache 中)
  — additional_object_names 匹配：通过 scene_name_by_id
  — 不重新读取 obj.name

obj.type:
  — camera_obj.type：一次 (camera 匹配成功后)
  — additional MESH 对象：不读取 obj.type (只对匹配到的对象检查 type)
  — geometry_scope MESH: 通过 _collect_geometry_scope_objects 收集 (复用现有 helper)

matrix_world:
  — camera_obj.matrix_world: 每个投影组一次 (获取相机位置 + 投影变换)
  — evaluated.matrix_world: 每个 evaluated mesh 一次
```

### 4.4 Scope Guard

```text
Phase 3 minimum AST Scope Guard 授权：

需确认 _check_projection_groups 名称在授权集合中。

其调用的函数 (world_to_camera_view, matrix_world, evaluated_depsgraph_get,
evaluated_get, to_mesh, to_mesh_clear, _collect_geometry_scope_objects)
已在 Camera Check 的 Scope Guard 授权中。
```

---

## 5. 配置和启用语义

### 5.1 启用判定

```text
ENABLED:
  spec.projection_groups is not None AND isinstance(projection_groups, list)
  → Projection Groups 运行时检查激活
  → _check_projection_groups 执行

DISABLED:
  spec.projection_groups is None
  → _base_result 的 projection_group_results 保持为 []
  → Projection Groups 完全不参与顶层 result 聚合

EMPTY:
  spec.projection_groups == []
  → projection_group_results 保持为 []
  → 合法：没有投影组需要检查
```

### 5.2 与顶层 result 的关系

```text
projection_group_overall 聚合所有投影组的 per-group result：

  projection_group_overall = "PASS"
    — projection_groups 为 null 或 []
    OR 所有 enabled group 的 result 为 PASS

  projection_group_overall = "FAIL"
    — 无 ERROR，至少一个 group 的 result 为 FAIL

  projection_group_overall = "ERROR"
    — 至少一个 group 的 result 为 ERROR

集成到 _validate_and_open_spec 的顶层判定：

  if (target_error or global_collection_error
      or projection_group_overall == "ERROR"):
      → EXIT_ERROR
      → build_error_result(spec, spec_sha, err_msgs,
                           projection_groups=pg_results)
      → err_msgs 包含每个 ERROR group 的摘要

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

BUILD_ERROR_RESULT:
  需扩展 build_error_result 接受 projection_groups 参数：
    def build_error_result(spec, spec_sha256, input_errors,
                           projection_groups=None):
        r = _base_result(spec, spec_sha256)
        r["result"] = "ERROR"
        if input_errors:
            r["input_errors"] = list(input_errors)
        if projection_groups is not None:
            r["projection_group_results"] = projection_groups
        return r

  当 projection_group_overall == "ERROR" 时：
    — build_error_result 收到 projection_groups=pg_results
    — 完整保留每组的 ERROR result dict (含 group_id, error_type, operation, note)
    — 同时在 input_errors 中添加摘要行
    — 不丢失组级详情
```

---

## 6. Pre-open 专用字段关系验证

### 6.1 验证函数

```text
FUNCTION: _validate_projection_groups_rules_preopen(spec)

LOCATION: asset_scene_preflight_check.py
CALL SITE: _validate_and_open_spec，在 _validate_camera_check_rules_preopen 之后

SCHEMA_VS_PREOPEN:
  14A Schema 验证：类型、值域 (mvc >= 0 有限整数、非 NaN/Inf 数值、非 bool)、
  关系 (bbox 顺序、group_id 唯一、target_id 引用)。
  Pre-open 验证：mvc <= 8、bbox [0,1]、元素非空、无重复、非空来源。
  Camera Check 还验证 mvc <= 8 和 bbox 值位于 [0,1]，
  Projection Groups 通过本 pre-open 函数达到相同级别。
```

### 6.2 验证规则 (共 7 条)

```text
RULE_1: minimum_visible_projected_corner_count <= 8
  SCOPE: 每个 projection_groups[i]
  ERROR: INVALID_PROJECTION_GROUP_RULE_VALUE:
         group_id '{gid}' minimum_visible_projected_corner_count > 8
  RATIONALE: 联合 bbox 也是 8 个角点。mvc > 8 永远无法满足。

RULE_2: required_screen_bbox 四个值位于 [0, 1]
  SCOPE: 每个 projection_groups[i].required_screen_bbox
  ERROR: INVALID_PROJECTION_GROUP_RULE_VALUE:
         group_id '{gid}' required_screen_bbox.{k} = {v} out of [0, 1]
  RATIONALE: 这些值描述屏幕归一化范围内的业务边界。

RULE_3: additional_object_names 每个元素为 non-empty string
  SCOPE: 每个 projection_groups[i].additional_object_names[j]
  ERROR: INVALID_PROJECTION_GROUP_RULE_VALUE:
         group_id '{gid}' additional_object_names[{j}] must be a non-empty string

RULE_4: target_ids 无重复 target_id
  SCOPE: 每个 projection_groups[i].target_ids
  ERROR: INVALID_PROJECTION_GROUP_RULE_VALUE:
         group_id '{gid}' duplicate target_id '{tid}' in target_ids

RULE_5: additional_object_names 无重复名称
  SCOPE: 每个 projection_groups[i].additional_object_names
  ERROR: INVALID_PROJECTION_GROUP_RULE_VALUE:
         group_id '{gid}' duplicate object name '{name}'
         in additional_object_names

RULE_6: target_ids 和 additional_object_names 不得同时为空
  SCOPE: 每个 projection_groups[i]
  ERROR: INVALID_PROJECTION_GROUP_RULE_VALUE:
         group_id '{gid}' both target_ids and additional_object_names are empty

RULE_7: 14A Schema 已涵盖（pre-open 不重复验证）：
  — group_id 非空字符串 + 唯一性
  — target_ids 每个元素是已知 target_id
  — camera_object_name 非空字符串
  — mvc 为非 bool 整数 >= 0
  — bbox 四个值为有限数值
  — bbox min_left ≤ max_right、min_bottom ≤ max_top
  — require_camera_outside_world_bbox 为 bool
```

---

## 7. Camera 查找

```text
复用 Camera Check 的 camera 查找合同 (CAMERA_CHECK_DESIGN_R2 §6)。

每个投影组独立查找其 camera_object_name。

ALGORITHM (per group, 使用 §4.1 的 _pg_scene_cache):
  从 scene_name_by_id 查找 camera_object_name
  遍历 scene_objects_ordered 进行 name 匹配 (id 关联回实际 bpy 对象)

  零匹配 → FAIL CAMERA_OBJECT_NOT_FOUND
  多匹配 → FAIL CAMERA_OBJECT_NOT_FOUND
  camera_obj.type != 'CAMERA' → FAIL CAMERA_TYPE_MISMATCH (actual_type 记录)
  obj.name/obj.type 读取异常 → ERROR RESOLVE_CAMERA_OBJECT

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
每个 projection group 的几何来源来自两类：

SOURCE_1: target_ids 中每个 target
  — 从 per_target_results 按 target_id 查找对应的 target result
  — 读取 checks.object_exists.result 和 checks.object_type.result
    确定该 target 的 root 前置条件：
      PASS → 使用 _collect_geometry_scope_objects 获取 geometry_scope MESH
      FAIL (ROOT_OBJECT_NOT_FOUND / ROOT_OBJECT_TYPE_MISMATCH / ERROR)
        → 该 target 不贡献几何
        → 记录在 per_source_summary 中

SOURCE_2: additional_object_names 中每个名称
  — 在 scene_name_by_id 中精确查找 (区分大小写，通过 _pg_scene_cache)
  — 零匹配 → FAIL (failure_code: ADDITIONAL_OBJECT_NOT_FOUND)
      记录 missing_name
  — 多匹配 → 不自动跳过；记录歧义但不挑选
      当前仲裁：多匹配 → FAIL (failure_code: ADDITIONAL_OBJECT_NOT_FOUND)
      记录 ambiguous_name + match_count
  — 唯一匹配 + type != 'MESH' → FAIL (failure_code: ADDITIONAL_OBJECT_TYPE_MISMATCH)
      记录 actual_type
  — 唯一匹配 + type == 'MESH' → 计入联合几何
  — name/type 读取异常 → ERROR RESOLVE_ADDITIONAL_OBJECT

每个 additional_object_name 被独立检查。
任一名称触发 FAIL 即该投影组整体 FAIL。
不静默跳过。
```

### 8.2 去重

```text
所有成功收集的 MESH 对象按 Python id(obj) 去重。

去重时机：在 target_ids 和 additional_object_names 全部解析完毕后。
去重后的 mesh_objects 列表传入 evaluated geometry 迭代。
```

### 8.3 空来源

```text
去重后 mesh_objects 为空：
  → FAIL (failure_code: NO_EVALUATED_GEOMETRY)
  → evaluated_mesh_names: []
```

---

## 9. Evaluated Geometry 算法

```text
完全复用 Camera Check 的 evaluated geometry 算法
(CAMERA_CHECK_DESIGN_R2 §8)，差异仅为 mesh_objects 来自 §8 的联合收集：

1. depsgraph = <从 §4.2 的共享 depsgraph> (已获取)
   (ERROR GET_EVALUATED_DEPSGRAPH on failure)

2. mesh_objects = <联合收集 + 去重结果>

3. if len(mesh_objects) == 0:
       → FAIL NO_EVALUATED_GEOMETRY

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

           for v in mesh.vertices:
               vertex_co = v.co
               (ERROR READ_MESH_VERTICES on failure)

               world_co = mw @ vertex_co
               (ERROR TRANSFORM_VERTEX_TO_WORLD_SPACE on failure)

               if not (isfinite(world_co.x) and isfinite(world_co.y)
                       and isfinite(world_co.z)):
                   pending_non_finite = True
                   continue

               all_world_vertices.append(world_co)
       finally:
           evaluated.to_mesh_clear()
           (ERROR TO_MESH_CLEAR on failure — overrides ALL pending results)

5. if pending_non_finite:
       → FAIL NON_FINITE_EVALUATED_VERTEX
   elif pending_zero_vertex:
       → FAIL NO_EVALUATED_GEOMETRY
   elif len(all_world_vertices) == 0:
       → FAIL NO_EVALUATED_GEOMETRY

6. to_mesh_clear() 在 finally 块中。
   主异常 + cleanup 异常同时发生 → cleanup ERROR 优先。
```

---

## 10. Union World Bbox 与投影

### 10.1 Union World Bbox

```text
从 all_world_vertices 计算联合 world-space bbox：

  min_x = min(v.x for v in all_world_vertices)
  max_x = max(v.x for v in all_world_vertices)
  min_y = min(v.y for v in all_world_vertices)
  max_y = max(v.y for v in all_world_vertices)
  min_z = min(v.z for v in all_world_vertices)
  max_z = max(v.z for v in all_world_vertices)

8 个 bbox 角点（世界空间）：
  C0: (min_x, min_y, min_z)    C4: (min_x, min_y, max_z)
  C1: (max_x, min_y, min_z)    C5: (max_x, min_y, max_z)
  C2: (min_x, max_y, min_z)    C6: (min_x, max_y, max_z)
  C3: (max_x, max_y, min_z)    C7: (max_x, max_y, max_z)

COMPUTE_UNION_BBOX 异常 → ERROR
```

### 10.2 8 角点投影算法

```text
复用 R1 §19 (与 Camera Check 完全一致)：

1. 8 个 bbox 角点逐一执行 world_to_camera_view(camera_obj, corner)
2. 返回 (projected_x, projected_y, projected_z)
3. 丢弃 projected_z <= 0 的角点
4. 剩余 0 个 → FAIL BEHIND_CAMERA
5. 计算 screen bbox: min_x, max_x, min_y, max_y
6. surviving corners < mvc → FAIL INSUFFICIENT_VISIBLE_PROJECTED_CORNERS
7. screen bbox 满足 required_screen_bbox? (见 §11)

world_to_camera_view 调用异常 → ERROR PROJECT_BBOX_CORNER
```

### 10.3 边界语义

```text
projected_z <= 0 → 丢弃 (含 z == 0，相机平面上 → 不可见)

required_screen_bbox 边界比较使用包含相等：
  screen_min_x >= min_left (含等于)
  screen_max_x <= max_right (含等于)
  screen_min_y <= min_bottom (含等于)
  screen_max_y >= max_top (含等于)
```

---

## 11. Screen Bbox 检查模型

```text
HORIZONTAL_MODEL: SAFE_MARGIN_CONTAINMENT
  screen_min_x >= min_left AND screen_max_x <= max_right

VERTICAL_MODEL: MINIMUM_COVERAGE
  screen_min_y <= min_bottom AND screen_max_y >= max_top

CHECK:
  水平不满足 + 垂直不满足 → FAIL SCREEN_BBOX_REQUIREMENT_NOT_MET
    failed_checks: ["horizontal_containment", "vertical_coverage"]
  仅水平不满足 → FAIL SCREEN_BBOX_REQUIREMENT_NOT_MET
    failed_checks: ["horizontal_containment"]
  仅垂直不满足 → FAIL SCREEN_BBOX_REQUIREMENT_NOT_MET
    failed_checks: ["vertical_coverage"]

与 Camera Check 完全一致的 mixed axial model。
```

---

## 12. require_camera_outside_world_bbox

```text
条件: require_camera_outside_world_bbox == true

定义: camera_world_loc = camera_obj.matrix_world.translation

  camera 在 bbox 内/面上的判定:
    union_min_x <= camera.x <= union_max_x AND
    union_min_y <= camera.y <= union_max_y AND
    union_min_z <= camera.z <= union_max_z

  if require_camera_outside_world_bbox AND inside:
      → FAIL CAMERA_INSIDE_WORLD_BBOX
      camera_world_location: [x, y, z]
      union_bbox: [min_x, max_x, min_y, max_y, min_z, max_z]

  if require_camera_outside_world_bbox AND NOT inside:
      → 满足 (相机在 bbox 任一轴严格在外部)

  面上算 inside (camera.x == min_x 等 → FAIL)

与 screen bbox / mvc 独立检查，任一不满足即 FAIL。
```

---

## 13. 失败优先级与检查顺序

### 13.1 Per-Group 优先级 (从高到低)

```text
ERROR                                          (优先级 0)
  > CAMERA_OBJECT_NOT_FOUND                     (优先级 1)
  > CAMERA_TYPE_MISMATCH                        (优先级 2)
  > ADDITIONAL_OBJECT_NOT_FOUND                 (优先级 3)
  > ADDITIONAL_OBJECT_TYPE_MISMATCH             (优先级 4)
  > NON_FINITE_EVALUATED_VERTEX                 (优先级 5)
  > NO_EVALUATED_GEOMETRY                       (优先级 6)
  > BEHIND_CAMERA                               (优先级 7)
  > SCREEN_BBOX_REQUIREMENT_NOT_MET             (优先级 8)
  > INSUFFICIENT_VISIBLE_PROJECTED_CORNERS      (优先级 9)
  > CAMERA_INSIDE_WORLD_BBOX                    (优先级 10)
  > PASS                                        (优先级 11)

每个投影组返回遇到的第一个非 PASS 结果 (短路径返回)。
```

### 13.2 检查顺序 (与优先级一致)

```text
每个投影组的运行时检查按以下顺序 (即优先级顺序)：

1.  camera_object_name 解析 (→ ERROR RESOLVE_CAMERA_OBJECT
    或 CAMERA_OBJECT_NOT_FOUND 或 CAMERA_TYPE_MISMATCH)
2.  additional_object_names 解析 (→ ERROR RESOLVE_ADDITIONAL_OBJECT
    或 ADDITIONAL_OBJECT_NOT_FOUND 或 ADDITIONAL_OBJECT_TYPE_MISMATCH)
3.  target_ids geometry_scope 收集 (→ ERROR COLLECT_GEOMETRY_SCOPE
    或 per-target 记录在 per_source_summary)
4.  去重
5.  空来源检查 (→ NO_EVALUATED_GEOMETRY)
6.  depsgraph 获取 (→ ERROR GET_EVALUATED_DEPSGRAPH)
7.  evaluated geometry 迭代 (→ ERROR EVALUATED_GET/TO_MESH/
    READ_EVALUATED_MATRIX_WORLD/READ_MESH_VERTICES/
    TRANSFORM_VERTEX_TO_WORLD_SPACE/TO_MESH_CLEAR
    或 NON_FINITE_EVALUATED_VERTEX 或 NO_EVALUATED_GEOMETRY)
8.  union bbox 计算 (→ ERROR COMPUTE_UNION_BBOX)
9.  8 角点投影 (→ ERROR PROJECT_BBOX_CORNER 或 BEHIND_CAMERA)
10. mvc 检查 (→ INSUFFICIENT_VISIBLE_PROJECTED_CORNERS)
11. screen bbox 检查 (→ SCREEN_BBOX_REQUIREMENT_NOT_MET)
12. require_camera_outside_world_bbox 检查 (→ CAMERA_INSIDE_WORLD_BBOX)
13. PASS
```

---

## 14. 结果字典

### 14.1 统一键集合 (16 keys)

```text
所有 PASS 和 FAIL 的 per-group result 共享同一 16 键集合：

  1.  result              — "PASS" / "FAIL"
  2.  group_id            — 来自 spec
  3.  target_ids          — 保持 spec 顺序
  4.  camera_object_name  — 来自 spec
  5.  evaluated_mesh_names— 实际评估的 mesh 名称列表
  6.  surviving_corners   — 可见 bbox 角点数
  7.  screen_bbox         — {"min_x", "max_x", "min_y", "max_y} 或 null
  8.  required_screen_bbox— 来自 spec
  9.  minimum_visible_projected_corner_count — 来自 spec
  10. camera_world_location— [x, y, z] 或 null
  11. require_camera_outside_world_bbox — 来自 spec
  12. union_bbox          — {"min_x","max_x","min_y","max_y","min_z","max_z"} 或 null
  13. per_source_summary  — target_ids + additional_object_names 解析详情
  14. failed_checks       — 仅 FAIL 时有用值，PASS 时为 null
  15. actual_type         — 仅 CAMERA_TYPE_MISMATCH/ADDITIONAL_OBJECT_TYPE_MISMATCH
                            时有用值，PASS 时为 null
  16. failure_code        — 仅 FAIL 时有用值，PASS 时为 null

不可用字段设为 null (Python None)，不省略键。
```

### 14.2 PASS 示例

```json
{
  "result": "PASS",
  "group_id": "essential_objects",
  "target_ids": ["CHR_MALE_A", "CHR_EMPLOYEE_01"],
  "camera_object_name": "Camera_Persp_3_4",
  "evaluated_mesh_names": ["CHR_Male_Body", "CHR_Employee_Body", "CashRegister_mesh"],
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
      "CHR_MALE_A": {"root_status": "PASS", "geometry_scope": "SELF_AND_DESCENDANT_MESHES",
                     "mesh_objects_found": 2},
      "CHR_EMPLOYEE_01": {"root_status": "PASS", "geometry_scope": "SELF_MESH",
                          "mesh_objects_found": 1}
    },
    "additional_object_names": {
      "CashRegister_01": {"status": "found", "type": "MESH"},
      "CheckoutCounter": {"status": "found", "type": "MESH"}
    }
  },
  "failed_checks": null,
  "actual_type": null,
  "failure_code": null
}
```

### 14.3 FAIL 示例 (ADDITIONAL_OBJECT_NOT_FOUND)

```json
{
  "result": "FAIL",
  "group_id": "essential_objects",
  "target_ids": ["CHR_MALE_A"],
  "camera_object_name": "Camera_Persp_3_4",
  "failure_code": "ADDITIONAL_OBJECT_NOT_FOUND",
  "evaluated_mesh_names": ["CHR_Male_Body"],
  "surviving_corners": null,
  "screen_bbox": null,
  "required_screen_bbox": {"min_left": 0.04, "max_right": 0.96,
                           "min_bottom": 0.15, "max_top": 0.85},
  "minimum_visible_projected_corner_count": 4,
  "camera_world_location": [2.0, -5.0, 3.0],
  "require_camera_outside_world_bbox": false,
  "union_bbox": null,
  "per_source_summary": {
    "target_ids": {
      "CHR_MALE_A": {"root_status": "PASS", "geometry_scope": "SELF_MESH",
                     "mesh_objects_found": 1}
    },
    "additional_object_names": {
      "MissingObj": {"status": "not_found"}
    }
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
  "target_ids": ["CHR_MALE_A", "CHR_EMPLOYEE_01"],
  "camera_object_name": "Camera_Persp_3_4",
  "failure_code": "SCREEN_BBOX_REQUIREMENT_NOT_MET",
  "evaluated_mesh_names": ["CHR_Male_Body", "CHR_Employee_Body"],
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
      "CHR_MALE_A": {"root_status": "PASS", "geometry_scope": "SELF_AND_DESCENDANT_MESHES",
                     "mesh_objects_found": 2},
      "CHR_EMPLOYEE_01": {"root_status": "PASS", "geometry_scope": "SELF_MESH",
                          "mesh_objects_found": 1}
    },
    "additional_object_names": {}
  },
  "failed_checks": ["horizontal_containment"],
  "actual_type": null
}
```

### 14.5 ERROR 示例

```json
{
  "result": "ERROR",
  "group_id": "essential_objects",
  "target_ids": ["CHR_MALE_A"],
  "error_type": "PROJECTION_GROUP_COMPUTATION_ERROR",
  "operation": "GET_EVALUATED_DEPSGRAPH",
  "note": "GET_EVALUATED_DEPSGRAPH_FAILED"
}
```

### 14.6 键集合汇总

```text
PASS/FAIL unified key set (16):
  result, group_id, target_ids, camera_object_name,
  evaluated_mesh_names, surviving_corners, screen_bbox,
  required_screen_bbox, minimum_visible_projected_corner_count,
  camera_world_location, require_camera_outside_world_bbox,
  union_bbox, per_source_summary, failed_checks, actual_type,
  failure_code

  PASS 时: failure_code=null, failed_checks=null, actual_type=null
  FAIL 时: failure_code 有值; failed_checks/actual_type 按需有值

ERROR key set (5):
  result, group_id, target_ids, error_type, operation, note
  (共 6 keys)

NON_PARTICIPATING:
  projection_group_results: [] (disabled or empty)
```

---

## 15. Failure Codes、Error Types 和 Operations

### 15.1 Failure Codes (10)

```text
1.  CAMERA_OBJECT_NOT_FOUND
    — 相机零匹配或多匹配

2.  CAMERA_TYPE_MISMATCH
    — 相机对象存在但 type != 'CAMERA'

3.  ADDITIONAL_OBJECT_NOT_FOUND
    — additional_object_names 中对象在场景中零匹配或多匹配

4.  ADDITIONAL_OBJECT_TYPE_MISMATCH
    — additional_object_names 中对象不是 MESH type

5.  NON_FINITE_EVALUATED_VERTEX
    — 任一 evaluated mesh 顶点世界坐标为 NaN 或 Inf

6.  NO_EVALUATED_GEOMETRY
    — 去重后零 MESH 对象 OR 所有 MESH 零顶点 OR 所有顶点被非有限过滤

7.  BEHIND_CAMERA
    — 所有 8 个 bbox 角点 projected_z <= 0

8.  SCREEN_BBOX_REQUIREMENT_NOT_MET
    — screen bbox 不满足 required_screen_bbox

9.  INSUFFICIENT_VISIBLE_PROJECTED_CORNERS
    — surviving corners < minimum_visible_projected_corner_count

10. CAMERA_INSIDE_WORLD_BBOX
    — require_camera_outside_world_bbox=true 且相机在 union bbox 内或面上
```

### 15.2 Error Types (1)

```text
PROJECTION_GROUP_COMPUTATION_ERROR
  — 统一的 ERROR type
```

### 15.3 Operations (14)

```text
RESOLVE_CAMERA_OBJECT          — camera_object_name 查找异常
RESOLVE_ADDITIONAL_OBJECT      — additional_object_names name/type 读取异常
READ_SCENE_OBJECTS             — scene.objects 物化失败
COLLECT_GEOMETRY_SCOPE         — _collect_geometry_scope_objects 抛出 RuntimeError
GET_EVALUATED_DEPSGRAPH        — bpy.context.evaluated_depsgraph_get() 失败
EVALUATED_GET                  — obj.evaluated_get(depsgraph) 失败
TO_MESH                        — evaluated.to_mesh() 失败
TO_MESH_CLEAR                  — evaluated.to_mesh_clear() 失败 (覆盖 pending)
READ_EVALUATED_MATRIX_WORLD    — evaluated.matrix_world 读取失败
READ_MESH_VERTICES             — mesh.vertices 或 v.co 读取失败
TRANSFORM_VERTEX_TO_WORLD_SPACE— mw @ vertex_co 运算失败
COMPUTE_UNION_BBOX             — all_world_vertices 聚合后 bbox 计算异常
PROJECT_BBOX_CORNER            — world_to_camera_view 调用异常
RESOLVE_TARGET_GEOMETRY        — per_target_results 查找 target_id 失败 (结构异常)
```

---

## 16. Per-Source 结果跟踪

```text
每个投影组的 per_source_summary 包含两类来源的完整解析结果：

target_ids:
  每个 target_id → {
    "root_status": "PASS" | "ROOT_OBJECT_NOT_FOUND" |
                   "ROOT_OBJECT_TYPE_MISMATCH" | "ROOT_LOOKUP_ERROR",
    "geometry_scope": spec 中的 geometry_scope 值,
    "mesh_objects_found": 整数,
    "mesh_names": [string, ...]
  }
  注：root 前置失败的 target 的 mesh_objects_found=0, mesh_names=[]

additional_object_names:
  每个名称 → {
    "status": "found" | "not_found" | "ambiguous",
    "type": "MESH" | actual_type | null,
    "match_count": 整数 (仅 ambiguous),
    "contributing": true/false
  }

per_source_summary 在所有 PASS 和 FAIL 结果中均完整填充。
```

---

## 17. 入口集成

### 17.1 open_blend_and_get_scene 修改

```text
新增参数:
  projection_groups_block = spec.get("projection_groups")

在 per-target loop 和 _recompute_target_overall 全部完成后调用:

  pg_results = _check_projection_groups(
      scene,
      projection_groups_block,
      per_target_results,
      targets=targets,
  )
  scene_data["projection_group_results"] = pg_results

注意：不传入 _target_caches。Projection Groups 使用 §4.1 的独立缓存。
```

### 17.2 _validate_and_open_spec 修改

```text
PRE-OPEN:
  pg_errs = _validate_projection_groups_rules_preopen(spec)
  pre_open_errs.extend(pg_errs)
  (在 _validate_camera_check_rules_preopen 之后)

READER CALL:
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
  if (target_error or global_collection_error
      or projection_group_overall == "ERROR"):
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
    if not pg_results:
        return "PASS"
    results = [g["result"] for g in pg_results]
    if any(r == "ERROR" for r in results):
        return "ERROR"
    if any(r == "FAIL" for r in results):
        return "FAIL"
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

注意：
  — pre-open ERROR (在 reader 之前) 时 projection_groups=None
    → _base_result 保留 projection_group_results: []
  — reader 产生组级 ERROR 时 projection_groups=pg_results
    → 完整保留每组详情
  — input_errors 同时包含每组 ERROR 的摘要行
```

### 17.5 _collect_target_errors

```text
Projection Groups ERROR 不在 _collect_target_errors 中收集。
其 ERROR 通过 projection_group_overall → EXIT_ERROR → build_error_result 路径处理。
```

---

## 18. 设计关闭矩阵

### 18.1 DESIGN_FREEDOM 关闭 (DF-PG-01 至 DF-PG-32)

| ID | 最终决定 | 设计节 | 实施 | 测试 |
|----|---------|--------|------|------|
| DF-PG-01 | 结果字典 — 统一 16 键 (PASS/FAIL) + 6 键 (ERROR) | §14 | I1 | I1 |
| DF-PG-02 | PASS/FAIL/ERROR 条件 | §5.2, §13, §14 | I1 | I1 |
| DF-PG-03 | failure_code — 10 个 | §15.1 | I1 | I1 |
| DF-PG-04 | error_type + operation — 1 type, 14 ops | §15 | I1 | I1 |
| DF-PG-05 | 优先级 — 检查顺序一致 | §13.1, §13.2 | I2 | I2 |
| DF-PG-06 | target_ids 空 → additional only | §8.3 | I2 | I2 |
| DF-PG-07 | target_ids 重复 → pre-open ERROR | §6.2 RULE_4 | I1 | I1 |
| DF-PG-08 | additional_object_names 空 → 正常 | §8.1 | I2 | I2 |
| DF-PG-09 | 都空 → pre-open ERROR | §6.2 RULE_6 | I1 | I1 |
| DF-PG-10 | additional 不存在 → FAIL ADDITIONAL_OBJECT_NOT_FOUND | §8.1 | I2 | I2 |
| DF-PG-11 | additional 非 MESH → FAIL ADDITIONAL_OBJECT_TYPE_MISMATCH | §8.1 | I2 | I2 |
| DF-PG-12 | 重复对象 → 按 id() 去重 | §8.2 | I2 | I2 |
| DF-PG-13 | camera 解析 → 复用 Camera Check | §7 | I2 | I2 |
| DF-PG-14 | 相机不在 Scene → FAIL CAMERA_OBJECT_NOT_FOUND | §7 | I2 | I2 |
| DF-PG-15 | type != CAMERA → FAIL CAMERA_TYPE_MISMATCH | §7 | I2 | I2 |
| DF-PG-16 | 多匹配 → FAIL CAMERA_OBJECT_NOT_FOUND | §7 | I2 | I2 |
| DF-PG-17 | 8 角点投影 — 复用 R1 §19 | §10.2 | I2 | I2 |
| DF-PG-18 | mvc > 8 → pre-open ERROR | §6.2 RULE_1 | I1 | I1 |
| DF-PG-19 | mvc = 0 → 允许 | §6.2 | I2 | I2 |
| DF-PG-20 | 全在相机后 → FAIL BEHIND_CAMERA | §10.2 | I2 | I2 |
| DF-PG-21 | 轴向语义 — X containment, Y coverage | §11 | I2 | I2 |
| DF-PG-22 | camera outside — 逐轴严格外 | §12 | I2 | I2 |
| DF-PG-23 | 空联合 bbox → FAIL NO_EVALUATED_GEOMETRY | §8.3 | I2 | I2 |
| DF-PG-24 | 零顶点/非有限 → FAIL, failure_code 已定 | §9, §14, §15.1 | I2 | I2 |
| DF-PG-25 | per-group — 单组单 result | §14 | I1 | I1 |
| DF-PG-26 | 顶层投影组聚合 | §5.2 | I1 | I1 |
| DF-PG-27 | 多组聚合 — 任一 ERROR/FAIL | §5.2, §17.3 | I1 | I1 |
| DF-PG-28 | pre-open — 7 rules | §6 | I1 | I1 |
| DF-PG-29 | 读取次数 — 独立 cache, 单次 depsgraph | §4 | I2 | I2 |
| DF-PG-30 | camera inside bbox → FAIL | §12 | I2 | I2 |
| DF-PG-31 | additional 元素 — pre-open 拒绝空字符串 | §6.2 RULE_3 | I1 | I1 |
| DF-PG-32 | 配置值源自 spec, 禁止硬编码百分比 | §2 (goal 10) | I2 | I2 |

### 18.2 DOCUMENTATION_GAP 关闭 (DG-PG-01 至 DG-PG-08)

| ID | 最终决定 | 设计节 |
|----|---------|--------|
| DG-PG-01 | 设计以 R2 §10.2 为权威来源 | §1 |
| DG-PG-02 | NOT_CHECKED — 无 per-group NOT_CHECKED; null/[] → 整体跳过 | §5.1, §14.6 |
| DG-PG-03 | 结果字典 — 完整定义 | §14 |
| DG-PG-04 | failure_code / error_type / operation — 完整定义 | §15 |
| DG-PG-05 | require_camera_outside_world_bbox 精确语义 | §12 |
| DG-PG-06 | R1 不存在 — 不影响 | §1 |
| DG-PG-07 | Design Spec R1 不含 projection_groups — R2 新增 | §1 |
| DG-PG-08 | required_screen_bbox 轴向语义 — mixed axial model | §11 |

---

## 19. 实施拆分

```text
I1: pre-open、结果框架和入口集成
  — _validate_projection_groups_rules_preopen (7 pre-open rules)
  — build_error_result 扩展 (projection_groups 参数)
  — _compute_projection_group_overall
  — _validate_and_open_spec 集成 (pre-open + overall + result builders)
  — open_blend_and_get_scene 参数集成
  — _check_projection_groups 桩函数
  — 全部 result dict 精确键集定义
  — CPython 聚焦测试 (~35 tests)

I2: Blender 运行时
  — _check_projection_groups 完整实现
  — 独立场景缓存 (_pg_scene_cache)
  — camera_object_name 解析
  — additional_object_names 解析 (含 FAIL 路径)
  — target_ids geometry_scope 收集 (含 root 前置条件处理)
  — 去重
  — evaluated geometry 迭代
  — union bbox + 8 角点投影
  — screen bbox + mvc + camera outside bbox 检查
  — per_source_summary
  — 单次 depsgraph
  — Scope Guard 授权集合更新
  — Blender 临时场景验证 (~24 scenarios)
  — pytest wrapper

E: 聚焦测试、完整回归和锁定
  — I1+I2 全部测试通过
  — 完整 protocol_guard 回归
  — 14A Core 回归
  — 直接回归
  — 生产缺陷确认
```

---

## 20. 测试矩阵

### 20.1 I1 CPython Tests (~35 tests)

```text
Pre-open 验证 (10):
  — mvc > 8 → ERROR
  — bbox min_left 超出 [0,1] → ERROR
  — bbox max_right 超出 [0,1] → ERROR
  — bbox min_bottom 超出 [0,1] → ERROR
  — bbox max_top 超出 [0,1] → ERROR
  — additional_object_names 空字符串 → ERROR
  — target_ids 重复 → ERROR
  — additional_object_names 重复 → ERROR
  — target_ids + additional_object_names 都空 → ERROR
  — 全部 valid → 0 errors

启用判定 (4):
  — projection_groups null → projection_group_results: []
  — projection_groups [] → projection_group_results: []
  — projection_groups 非空 → projection_group_results 非空
  — 全部 PASS → projection_group_overall: PASS

聚合 (5):
  — 任一 ERROR → projection_group_overall: ERROR
  — 任一 FAIL → projection_group_overall: FAIL
  — 全部 PASS → projection_group_overall: PASS
  — projection_group_overall ERROR → EXIT_ERROR + build_error_result 含 pg_results
  — projection_group_overall FAIL → EXIT_FAIL + build_fail_result 含 pg_results

入口集成 (8):
  — build_pass_result 包含 projection_group_results
  — build_fail_result 包含 projection_group_results
  — build_error_result 含 projection_groups 参数 (组级 ERROR 路径)
  — build_error_result 不含 projection_groups 参数 (pre-open ERROR 路径) → []
  — pre-open ERROR 阻断
  — _validate_and_open_spec 调用链顺序
  — projection_groups_block 传递
  — _collect_target_errors 不收集投影组 ERROR

结果字典键集 (8):
  — PASS 精确 16 键
  — FAIL CAMERA_OBJECT_NOT_FOUND 精确 16 键
  — FAIL ADDITIONAL_OBJECT_NOT_FOUND 精确 16 键
  — FAIL SCREEN_BBOX_REQUIREMENT_NOT_MET 精确 16 键 (含 failed_checks)
  — FAIL NON_FINITE_EVALUATED_VERTEX 精确 16 键
  — FAIL 全部 10 个 failure_code 的键集一致性
  — ERROR 精确 6 键
  — null 键值验证 (PASS 时 failure_code/failed_checks/actual_type 为 null)
```

### 20.2 I2 Blender Scenarios (~24 scenarios)

```text
PG-BL-01: 单 target → union bbox = geometry_scope → PASS
PG-BL-02: 两个 target_ids → union bbox 聚合 → PASS
PG-BL-03: target_ids + additional_object_names → 去重 + union → PASS
PG-BL-04: target_ids 与 additional 重叠对象 → 按 id 去重 → PASS
PG-BL-05: additional 对象不存在 → FAIL ADDITIONAL_OBJECT_NOT_FOUND
PG-BL-06: additional 对象多匹配 → FAIL ADDITIONAL_OBJECT_NOT_FOUND
PG-BL-07: additional 对象非 MESH → FAIL ADDITIONAL_OBJECT_TYPE_MISMATCH
PG-BL-08: target root 未找到 → per_source_summary 记录, 其余来源继续
PG-BL-09: 所有 target root 失败 + additional 空 → FAIL NO_EVALUATED_GEOMETRY
PG-BL-10: 相机零匹配 → FAIL CAMERA_OBJECT_NOT_FOUND
PG-BL-11: 相机多匹配 → FAIL CAMERA_OBJECT_NOT_FOUND
PG-BL-12: 相机 type 非 CAMERA → FAIL CAMERA_TYPE_MISMATCH
PG-BL-13: 零顶点 mesh → FAIL NO_EVALUATED_GEOMETRY
PG-BL-14: 非有限顶点 → FAIL NON_FINITE_EVALUATED_VERTEX
PG-BL-15: 所有角点在相机后方 → FAIL BEHIND_CAMERA
PG-BL-16: 水平 containment 不满足 → FAIL SCREEN_BBOX_REQUIREMENT_NOT_MET
PG-BL-17: 垂直 coverage 不满足 → FAIL SCREEN_BBOX_REQUIREMENT_NOT_MET
PG-BL-18: 水平和垂直都不满足 → FAIL (failed_checks: 两项)
PG-BL-19: mvc 不足 → FAIL INSUFFICIENT_VISIBLE_PROJECTED_CORNERS
PG-BL-20: require_camera_outside=true 相机在 bbox 内 → FAIL CAMERA_INSIDE_WORLD_BBOX
PG-BL-21: require_camera_outside=true 相机在 bbox 外 → PASS
PG-BL-22: require_camera_outside=false → 不检查 (字段不出现)
PG-BL-23: 两个投影组 → 独立 per-group result → 正确聚合
PG-BL-24: to_mesh_clear 异常 → ERROR TO_MESH_CLEAR 覆盖 pending

额外验证 (pytest wrapper):
  — 所有 scenario returncode==0
  — JSON markers 恰好各一次
  — overall_passed field
  — 每组 result 含 16 键 (PASS/FAIL) 或 6 键 (ERROR)
  — target_ids 保持 spec 顺序
  — projection_group_results 按 group_id 排序
  — 读取次数: scene.objects 在 CHECK 前物化一次
```

### 20.3 E 回归范围

```text
完整 protocol_guard 回归 (所有已有测试)
14A Core 回归
直接回归 (Camera Check, Ground Contact, Material Assignment)
Scope Guard 回归
```

---

## 21. 设计统计

```text
RESULT_DICT_FORM_COUNT: 12 (1 PASS + 10 FAIL + 1 ERROR)
  (所有 FAIL 共享 16-key 集合，每个 failure_code 为不同 form)
FAILURE_CODE_COUNT: 10
ERROR_TYPE_COUNT: 1 (PROJECTION_GROUP_COMPUTATION_ERROR)
ERROR_OPERATION_COUNT: 14
PRE_OPEN_RULE_COUNT: 7
IMPLEMENTATION_STAGE_COUNT: 3 (I1, I2, E)
DESIGN_FREEDOM_CLOSED_COUNT: 32
DOCUMENTATION_GAP_CLOSED_COUNT: 8
UNRESOLVED_DESIGN_DECISIONS: 0
INTERNAL_CONTRADICTION_COUNT: 0
```

---

*Design R2 complete. All 32 design freedoms and 8 documentation gaps are closed. No internal contradictions. Awaiting independent review.*
