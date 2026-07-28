# Projection Groups Runtime Design R1

```text
DOCUMENT_ID: PROJECTION_GROUPS_DESIGN
DESIGN_VERSION: R1
TASK_ID: PROJECTION_GROUPS_DESIGN_R1
MASTER_MAP_VERSION: R79
DATE: 2026-07-26
DESIGN_STATUS: COMPLETED_PENDING_INDEPENDENT_REVIEW
FORMALLY_LOCKED: FALSE
IMPLEMENTATION_AUTHORIZED: FALSE
DESIGN_AUTHORIZATION: USER_EXPLICITLY_AUTHORIZED

BASELINE_COMMIT: d44679fc11c5069a17277395bb6c52b5a6dfc799
REFERENCE_DESIGN: CAMERA_CHECK_DESIGN_R2.md (FORMALLY_LOCKED)
```

---

## 1. 权威来源与优先级

```text
PRIORITY_1: ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md §10.2
  — AUTHORITATIVE_IMPLEMENTATION_CONTRACT:
    Global Projection Groups (New) — 唯一直接定义 projection_groups 的合同来源。

PRIORITY_2: asset_scene_preflight_core.py L223-274
  — LOCKED_SCHEMA:
    _validate_spec 内的 projection_groups 验证。
    10 个叶子字段（7 个直接字段）的类型、值域和关系验证。

PRIORITY_3: CAMERA_CHECK_DESIGN_R2.md (FORMALLY_LOCKED)
  — REFERENCE_IMPLEMENTATION_PATTERN:
    投影算法（§9）、evaluated geometry（§8）、camera 查找（§6）、
    屏幕 bbox 检查（§10）、result dict（§11）、entry integration（§13）、
    read count（§16）。Projection Groups 复用同一基础设施。

PRIORITY_4: R1 §19 (Recovered, embedded in Camera Check Design R2)
  — RETAINED_PROJECTION_ALGORITHM:
    8-corner bbox projection → world_to_camera_view → z-filter → screen bbox → mvc

PRIORITY_5: PROJECTION_GROUPS_ORIGINAL_REQUIREMENT_AUDIT_REPORT.md (R2 Correction)
  — DESIGN_INPUT:
    15 fixed requirements, 32 design freedoms, 8 documentation gaps.
    AUDIT_RESULT: REQUIREMENTS_SUFFICIENT_FOR_DESIGN.
```

---

## 2. 设计目标

1. 为 Projection Groups 字段组定义唯一、完整、可独立实现和测试的运行时设计。
2. 关闭原始需求审计中的全部 32 项 DESIGN_FREEDOM 和 8 项 DOCUMENTATION_GAP。
3. 结果字典键集合唯一，支持 `assert_dict_equal` 精确断言。
4. 所有异常路径有唯一 operation，所有 FAIL 有唯一 failure_code，错误优先级唯一。
5. 配置、前置条件、算法、结果、清理、集成和副作用边界全部封闭。
6. 复用 Camera Check 已锁定的基础设施（evaluated geometry、投影算法、camera 查找、screen bbox 检查模型）。
7. required_screen_bbox 采用与 Camera Check 一致的 axial mixed model：X axis containment、Y axis minimum coverage。
8. 四个 bbox 配置值源自 spec，禁止硬编码百分比阈值。

---

## 3. 固定范围与明确非目标

```text
FIXED_SCOPE:
  — 10-leaf-field schema (7 direct fields)
  — target_ids 使用对应 target 的 geometry_scope
  — additional_object_names 使用对象自身 full MESH geometry
  — 所有来源按对象 identity 去重后形成 union world bbox
  — 几何来源为 evaluated geometry (R2 §4)
  — 任一 evaluated mesh 零顶点或非有限顶点必须 FAIL (R2 §4.3)
  — 使用 world_to_camera_view
  — projection_group_results 按 group_id 排序 (R2 §11.2)
  — target_ids 保持 spec 顺序 (R2 §11.2)
  — 检查只证明几何边界，不证明视觉质量 (R2 §10.3)
  — required_screen_bbox mixed axial model (X=h containment, Y=v coverage)
  — to_mesh_clear() in finally block

EXPLICITLY_EXCLUDED:
  — 遮挡 (ray casting / occlusion)
  — 视觉质量、美学判断
  — 相机排查顺序 — DEFER_REQUIRES_STATE
  — 保存重开持久化
  — 渲染结果
  — 修改 Camera Check 已锁定设计、生产代码或测试
  — 修改 per_target_results 结构
  — dimensions / height / horizontal ratio / landmark / stray objects

MUST_NOT_MODIFY:
  — 14A Core schema (_validate_spec)
  — Camera Check 生产代码和测试
  — _check_root_objects 返回值结构
  — Hierarchy 到 Camera Check 的任何已锁定内容
  — 任何已锁定设计或锁定记录
```

---

## 4. 配置和启用语义

### 4.1 启用判定

```text
ENABLED:
  spec.projection_groups is not None AND isinstance(projection_groups, list)
  → Projection Groups 运行时检查激活

DISABLED:
  spec.projection_groups is None
  → _base_result 的 projection_group_results 保持为 []
  → Projection Groups 完全不参与顶层 result 聚合

EMPTY:
  spec.projection_groups == []
  → projection_group_results 保持为 []
  → Projection Groups 不参与顶层 result 聚合
  → 这是合法的：没有投影组需要检查，整体不影响 PASS/FAIL/ERROR
```

### 4.2 与顶层 result 的关系

```text
投影组的 per-group result 聚合为顶层 projection_group_overall：

  projection_group_overall = "PASS"
    — 所有 enabled group 的 per-group result 为 PASS

  projection_group_overall = "FAIL"
    — 无 ERROR，至少一个 enabled group 的 per-group result 为 FAIL

  projection_group_overall = "ERROR"
    — 至少一个 enabled group 的 per-group result 为 ERROR

projection_group_overall 参与顶层 result：

  顶层 result 聚合（在 _validate_and_open_spec 中）：
    per_target_results overall + scene_basic + global_results
    + projection_group_overall → 顶层 PASS/FAIL/ERROR

  ERROR 优先：
    任一 per-target overall == "ERROR"
    OR global_collection_error
    OR projection_group_overall == "ERROR"
    → EXIT_ERROR

  FAIL：
    无 ERROR，但：
    任一 per-target overall == "FAIL"
    OR scene_basic FAIL
    OR global_collection_fail
    OR projection_group_overall == "FAIL"
    → EXIT_FAIL

  PASS：
    所有 overall 为 PASS
    → EXIT_PASS
```

### 4.3 输出键存在性

```text
projection_groups 为 null 或缺失：
  projection_group_results 键存在，值为 []

projection_groups 为 []：
  projection_group_results 键存在，值为 []

projection_groups 非空：
  projection_group_results 键存在，值为每个投影组的 per-group result

BUILD_ERROR_RESULT:
  build_error_result 通过 _base_result 保留 projection_group_results: []。
  这与 Camera Check 的 input_errors 路径行为一致
  — 当前生产代码中 _base_result 已初始化 projection_group_results: []。
  无需修改 _base_result。详见 §16.2 入口集成。
```

---

## 5. Pre-open 专用字段关系验证

### 5.1 新增验证函数

除 14A Schema 的通用验证之外，新增 `_validate_projection_groups_rules_preopen`：

```text
FUNCTION: _validate_projection_groups_rules_preopen(spec)

LOCATION: asset_scene_preflight_check.py (与 _validate_camera_check_rules_preopen 同级)

CALL SITE: _validate_and_open_spec，在 _validate_camera_check_rules_preopen 之后

SCHEMA_VS_PREOPEN:
  14A Schema 验证：类型（int、str、bool、list、dict）、值域（mvc >= 0、
  有限数值、非 bool）、关系（bbox 顺序、group_id 唯一、target_id 引用）。
  Pre-open 验证：mvc <= 8、bbox [0,1]、additional_object_names 元素、
  target_ids 去重、空来源。
  Schema 与 Camera Check pre-open 不完全等价；
  Camera Check 还验证 mvc <= 8 和 bbox 值位于 [0,1]，
  Projection Groups 通过本 pre-open 函数达到相同级别的验证。
```

### 5.2 验证规则

```text
RULE_1: minimum_visible_projected_corner_count <= 8
  SCOPE: 每个 projection_groups[i]
  ERROR: INVALID_PROJECTION_GROUP_RULE_VALUE:
         group_id '{gid}' minimum_visible_projected_corner_count > 8

  RATIONALE: 联合 bbox 也是 8 个角点。mvc > 8 永远无法满足。

RULE_2: required_screen_bbox 四个值位于 [0, 1]
  SCOPE: 每个 projection_groups[i].required_screen_bbox.{min_left,max_right,min_bottom,max_top}
  ERROR: INVALID_PROJECTION_GROUP_RULE_VALUE:
         group_id '{gid}' required_screen_bbox.{k} out of [0, 1]

  RATIONALE: 与 Camera Check 一致。
    这些值描述屏幕归一化范围内的业务边界。
    projected x/y 可以超出 [0,1]（目标部分在屏幕外），
    但配置的 required 边界必须在 [0,1] 内。

RULE_3: 14A Schema 已涵盖（不重复）：
  — group_id 非空字符串 + 唯一性
  — target_ids 每个元素是已知 target_id
  — camera_object_name 非空字符串
  — mvc 为非 bool 整数 >= 0
  — bbox 四个值为有限数值
  — bbox min_left ≤ max_right、min_bottom ≤ max_top
  — require_camera_outside_world_bbox 为 bool

RULE_4: additional_object_names 元素验证
  SCOPE: 每个 projection_groups[i].additional_object_names[j]
  ERROR: INVALID_PROJECTION_GROUP_RULE_VALUE:
         group_id '{gid}' additional_object_names[{j}] must be a non-empty string

RULE_5: target_ids 不得包含重复 target_id
  SCOPE: 每个 projection_groups[i].target_ids
  ERROR: INVALID_PROJECTION_GROUP_RULE_VALUE:
         group_id '{gid}' duplicate target_id '{tid}' in target_ids

RULE_6: additional_object_names 不得包含重复名称
  SCOPE: 每个 projection_groups[i].additional_object_names
  ERROR: INVALID_PROJECTION_GROUP_RULE_VALUE:
         group_id '{gid}' duplicate object name '{name}' in additional_object_names

RULE_7: target_ids 与 additional_object_names 不得同时为空
  SCOPE: 每个 projection_groups[i]
  ERROR: INVALID_PROJECTION_GROUP_RULE_VALUE:
         group_id '{gid}' both target_ids and additional_object_names are empty
```

### 5.3 Pre-open 错误阻断

```text
pre-open 验证返回非空错误列表 → 立即 EXIT_ERROR。
与 Camera Check、Ground Contact 等一致。
```

---

## 6. Camera 查找合同

### 6.1 解析策略

```text
复用 Camera Check 的 camera 查找合同（CAMERA_CHECK_DESIGN_R2 §6）：

LOOKUP_METHOD: 遍历 scene.objects，精确区分大小写匹配 camera_object_name

每个 projection group 独立查找一次其 camera_object_name。
Projection Groups 运行时在 per-target loop 之后执行，
此时 scene.objects 已经物化（_target_caches 可用）。

CAMERA_NOT_SHARED_ACROSS_GROUPS:
  每个投影组有自己的 camera_object_name，不共享查找结果。
  不同组可能指定不同相机。

ALGORITHM (per group):
  camera_match_count = 0
  camera_obj = None
  for obj in scene_objects_ordered:
      if obj.name == camera_object_name:
          camera_match_count += 1
          if camera_match_count == 1:
              camera_obj = obj
          else:
              camera_obj = None

  零匹配 → FAIL CAMERA_OBJECT_NOT_FOUND
  多匹配 → FAIL CAMERA_OBJECT_NOT_FOUND
  camera_obj.type != 'CAMERA' → FAIL CAMERA_TYPE_MISMATCH
  obj.name / obj.type 读取异常 → ERROR RESOLVE_CAMERA_OBJECT

FALLBACK (无 _target_caches 时):
  自行物化 scene.objects。
```

### 6.2 禁止项

```text
FORBIDDEN:
  bpy.context.scene
  bpy.data.objects.get()
  bpy.data.cameras
  scene.camera
```

---

## 7. 联合几何聚合

### 7.1 来源对象收集

```text
每个 projection group 的几何来源来自两类：

SOURCE_1: target_ids 中每个 target 的 geometry_scope MESH 对象
  — 使用 _collect_geometry_scope_objects(...) 为每个 target_id 独立收集
  — 传入该 target 对应的 root_obj 和 geometry_scope_value
  — 复用 Camera Check 已锁定的 helper 函数

SOURCE_2: additional_object_names 中的每个对象
  — 在 scene.objects 中按名称精确匹配（区分大小写）
  — 零匹配 → 跳过（不报错，不阻止其他对象聚合）
  — 多匹配 → 跳过所有同名对象（不报错，不阻止其他对象聚合）
  — 匹配到的对象类型不是 MESH → 跳过
  — 匹配到的对象类型是 MESH → 计入联合几何
  — name 读取异常 → ERROR RESOLVE_ADDITIONAL_OBJECT

RATIONALE (additional_object_names 跳过而非 FAIL):
  additional_object_names 是 spec 声明其想包含的对象。
  对象不在场景中或不是 MESH 属于配置与实际场景之间的差异，
  不应阻止已有几何的投影检查。
  如果结果是没有几何可检查 → NO_EVALUATED_GEOMETRY。
```

### 7.2 按对象 Identity 去重

```text
DEDUP:
  所有收集到的 MESH 对象按 Python id(obj) 去重。

  同一个 MESH 对象可能同时出现在：
    — 多个 target_id 的 geometry_scope 内
    — additional_object_names 与 target geometry_scope 之间

  去重保证每个 MESH 对象的顶点只被计入一次。

DEDUP_TIME: 在 evaluated geometry 迭代之前执行。
```

### 7.3 空来源

```text
去重后 mesh_objects 为空：
  → FAIL (failure_code: NO_EVALUATED_GEOMETRY)
  → evaluated_mesh_names: []
```

---

## 8. Evaluated Geometry 算法

### 8.1 算法

```text
完全复用 Camera Check 的 evaluated geometry 算法
(CAMERA_CHECK_DESIGN_R2 §8)，差异仅为 mesh_objects 来自联合收集：

1. depsgraph = bpy.context.evaluated_depsgraph_get()
   (ERROR GET_EVALUATED_DEPSGRAPH on failure)

2. mesh_objects = <联合收集 + 去重的结果>
   (ERROR on RuntimeError from _collect_geometry_scope_objects
    OR ERROR on name read exception from additional_object_names resolution)

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

6. Continue to union bbox computation (§9)
```

### 8.2 清理合同

```text
to_mesh_clear() 在 finally 块中执行。

如果 to_mesh_clear 抛异常:
  → ERROR (operation: TO_MESH_CLEAR)
  覆盖 finally 块之前的任何 pending result
  — 与 Camera Check 和 Ground Contact 合同一致: return-in-finally pattern

主异常 + cleanup 异常同时发生:
  cleanup ERROR 优先 → 返回 TO_MESH_CLEAR ERROR
```

---

## 9. Union World Bbox 与投影

### 9.1 Union World Bbox

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
```

### 9.2 8 角点投影算法

```text
复用 R1 §19 投影算法（与 Camera Check 完全一致）：

1. 对 8 个 bbox 角点逐一执行 world_to_camera_view(camera_obj, corner)
2. 返回 (projected_x, projected_y, projected_z)

3. 丢弃 projected_z <= 0 的角点（在相机后方或相机平面上）
4. 如果剩余角点数 == 0：
       → FAIL (failure_code: BEHIND_CAMERA)
       记录 surviving_corners: 0

5. 从 surviving corners 的 projected_x/y 计算 screen-space bbox：
       screen_min_x = min(projected_x)    screen_max_x = max(projected_x)
       screen_min_y = min(projected_y)    screen_max_y = max(projected_y)

6. 检查 surviving corner count >= minimum_visible_projected_corner_count
       不足 → FAIL (failure_code: INSUFFICIENT_VISIBLE_PROJECTED_CORNERS)
       记录 surviving_corners: <实际数量>

7. 检查 screen bbox 是否满足 required_screen_bbox（见 §10）
```

### 9.3 Projected z = 0 的精确语义

```text
projected_z <= 0 → 丢弃。
includes: z == 0（角点恰好在相机平面上 → 不可见）

与 Camera Check 完全一致。
```

### 9.4 边界相等语义

```text
required_screen_bbox 的边界比较使用包含相等：

X 轴 containment:
  screen_min_x >= min_left  → 满足（允许恰好在边界上）
  screen_max_x <= max_right → 满足（允许恰好在边界上）

Y 轴 minimum coverage:
  screen_min_y <= min_bottom → 满足（允许恰好在边界上）
  screen_max_y >= max_top    → 满足（允许恰好在边界上）

与 Camera Check 完全一致。
```

---

## 10. Screen Bbox 检查模型

### 10.1 轴向语义

```text
与 Camera Check 一致，采用 mixed axial model：

HORIZONTAL_MODEL: SAFE_MARGIN_CONTAINMENT
  screen_min_x >= min_left AND screen_max_x <= max_right
  → 投影的水平范围必须在配置的安全边距内
  对应 V4 "左右安全边距 ≥ 4%"（配置侧指定）

VERTICAL_MODEL: MINIMUM_COVERAGE
  screen_min_y <= min_bottom AND screen_max_y >= max_top
  → 投影的垂直范围必须覆盖配置要求的最小区域
  对应 V4 "顶部空白 ≤ 15%, 底部空白 ≤ 15%"（配置侧指定）

RATIONALE:
  联合 bbox 投影的水平扩展不得超过安全边距（防止切边）。
  联合 bbox 投影的垂直范围必须填满要求的画面比例（防止过多空白）。
```

### 10.2 检查算法

```text
HORIZONTAL CHECK:
  if screen_min_x < min_left OR screen_max_x > max_right:
      → FAIL (failure_code: SCREEN_BBOX_REQUIREMENT_NOT_MET)
      failed_checks: ["horizontal_containment"]
      detail: {screen_min_x, screen_max_x, required_min_left, required_max_right}

VERTICAL CHECK:
  if screen_min_y > min_bottom OR screen_max_y < max_top:
      → FAIL (failure_code: SCREEN_BBOX_REQUIREMENT_NOT_MET)
      failed_checks: ["vertical_coverage"]
      detail: {screen_min_y, screen_max_y, required_min_bottom, required_max_top}

OTHER COMBINATIONS:
  水平不满足 + 垂直不满足
      → FAIL SCREEN_BBOX_REQUIREMENT_NOT_MET
      failed_checks: ["horizontal_containment", "vertical_coverage"]
```

---

## 11. require_camera_outside_world_bbox

### 11.1 精确数学语义

```text
条件：
  require_camera_outside_world_bbox == true

定义：
  camera_world_loc = camera_obj.matrix_world.translation

  camera_outside_bbox =
    camera_world_loc.x < union_min_x OR camera_world_loc.x > union_max_x OR
    camera_world_loc.y < union_min_y OR camera_world_loc.y > union_max_y OR
    camera_world_loc.z < union_min_z OR camera_world_loc.z > union_max_z

  即：相机在 union bbox 的任一轴上严格在外部。
  "outside" = 完全不相交（分离轴判定，非 3D 包含）。

边界：
  相机恰好在 bbox 面上（camera.x == min_x 等）→ 不算 outside
  → FAIL CAMERA_INSIDE_WORLD_BBOX

算法：
  camera_loc = camera_obj.matrix_world.translation
  inside = (
      union_min_x <= camera_loc.x <= union_max_x AND
      union_min_y <= camera_loc.y <= union_max_y AND
      union_min_z <= camera_loc.z <= union_max_z
  )
  if require_camera_outside_world_bbox and inside:
      → FAIL (failure_code: CAMERA_INSIDE_WORLD_BBOX)
      camera_world_location: [x, y, z]
      union_bbox: [min_x, max_x, min_y, max_y, min_z, max_z]
```

### 11.2 与 Screen Bbox 检查的关系

```text
独立检查，与 screen bbox / mvc 并行。

任一不满足 → FAIL。
多个不满足 → 同一 FAIL code 聚合（见 §13 优先级）。
```

---

## 12. 失败优先级

### 12.1 Per-Group 优先级

```text
ERROR > CAMERA_OBJECT_NOT_FOUND > CAMERA_TYPE_MISMATCH
> NON_FINITE_EVALUATED_VERTEX > NO_EVALUATED_GEOMETRY
> BEHIND_CAMERA > SCREEN_BBOX_REQUIREMENT_NOT_MET
> INSUFFICIENT_VISIBLE_PROJECTED_CORNERS > CAMERA_INSIDE_WORLD_BBOX
> PASS

说明：
  — 每个投影组返回遇到的第一个（最高优先级）非 PASS 结果。
  — ERROR 优先于所有 FAIL。
  — 同一组内不需要聚合多个 failure_code：
    一旦遇到更高优先级的条件，立即返回。
```

### 12.2 检查顺序

```text
每个投影组的运行时检查按以下顺序执行：

1. camera_object_name 解析
2. 来源对象收集（target_ids geometry_scope + additional_object_names）
3. 去重
4. 空来源检查
5. depsgraph 获取
6. evaluated geometry 迭代（零顶点、非有限、to_mesh_clear）
7. union bbox 计算
8. 8 角点投影
9. mvc 检查
10. screen bbox 检查
11. require_camera_outside_world_bbox 检查
12. PASS
```

---

## 13. 结果字典

### 13.1 Per-Group Result Dict (PASS)

```json
{
  "result": "PASS",
  "group_id": "essential_objects",
  "camera_object_name": "Camera_Persp_3_4",
  "evaluated_mesh_names": ["CHR_Male_Body", "CHR_Employee_Body", "CashRegister_mesh"],
  "surviving_corners": 8,
  "screen_bbox": {"min_x": 0.12, "max_x": 0.88, "min_y": 0.10, "max_y": 0.92},
  "required_screen_bbox": {"min_left": 0.04, "max_right": 0.96, "min_bottom": 0.15, "max_top": 0.85},
  "camera_world_location": [2.0, -5.0, 3.0],
  "require_camera_outside_world_bbox": true
}
```

### 13.2 Per-Group Result Dict (FAIL)

```json
{
  "result": "FAIL",
  "group_id": "essential_objects",
  "failure_code": "SCREEN_BBOX_REQUIREMENT_NOT_MET",
  "failed_checks": ["horizontal_containment"],
  "camera_object_name": "Camera_Persp_3_4",
  "evaluated_mesh_names": ["CHR_Male_Body", "CHR_Employee_Body"],
  "surviving_corners": 8,
  "screen_bbox": {"min_x": -0.05, "max_x": 0.88, "min_y": 0.10, "max_y": 0.92},
  "required_screen_bbox": {"min_left": 0.04, "max_right": 0.96, "min_bottom": 0.15, "max_top": 0.85},
  "camera_world_location": [2.0, -5.0, 3.0],
  "require_camera_outside_world_bbox": false
}
```

### 13.3 Per-Group Result Dict (ERROR)

```json
{
  "result": "ERROR",
  "group_id": "essential_objects",
  "error_type": "PROJECTION_GROUP_COMPUTATION_ERROR",
  "operation": "GET_EVALUATED_DEPSGRAPH",
  "note": "GET_EVALUATED_DEPSGRAPH_FAILED"
}
```

### 13.4 Per-Group Result Dict (NOT_CHECKED)

Projection Groups 没有 NOT_CHECKED per-group 结果。
启用判定在 pre-group 级别（spec.projection_groups 为 null/[] → 整体不运行）。

如果所有 per-target root preconditions 都失败导致无法解析任何 target 的 geometry_scope
且 additional_object_names 也为空 → 通过空来源进入 NO_EVALUATED_GEOMETRY FAIL。
这比引入额外的 NOT_CHECKED 更简单，且语义更精确（确实没有可评估的几何）。

### 13.5 Key Sets Summary

```text
PASS keys (9):
  result, group_id, camera_object_name, evaluated_mesh_names,
  surviving_corners, screen_bbox, required_screen_bbox,
  camera_world_location, require_camera_outside_world_bbox

FAIL keys (variable):
  result, group_id, failure_code,
  [+ failed_checks] (SCREEN_BBOX_REQUIREMENT_NOT_MET only),
  [+ surviving_corners] (INSUFFICIENT_VISIBLE_PROJECTED_CORNERS only),
  [+ camera_object_name] (CAMERA_OBJECT_NOT_FOUND, CAMERA_TYPE_MISMATCH only),
  [+ actual_type] (CAMERA_TYPE_MISMATCH only),
  [+ evaluated_mesh_names] (non-camera FAILs only),
  [+ screen_bbox] (projection-related FAILs only),
  [+ required_screen_bbox] (SCREEN_BBOX_REQUIREMENT_NOT_MET only),
  [+ camera_world_location] (CAMERA_INSIDE_WORLD_BBOX only),
  [+ require_camera_outside_world_bbox] (CAMERA_INSIDE_WORLD_BBOX only)

  Design decision: all FAIL forms include the same 9 PASS keys plus
  the failure-specific extra keys. This simplifies exact-key-set assertions.

ERROR keys (5):
  result, group_id, error_type, operation, note

NON_PARTICIPATING:
  projection_group_results: [] (disabled or empty)
```

### 13.6 Exact Key Sets — All FAIL Forms

```text
FAIL form 1: CAMERA_OBJECT_NOT_FOUND
  keys: result, group_id, failure_code, camera_object_name,
        evaluated_mesh_names, surviving_corners, screen_bbox,
        required_screen_bbox, camera_world_location,
        require_camera_outside_world_bbox
  Note: evaluated_mesh_names=[], surviving_corners=0,
        screen_bbox/camera_world_location=None,
        required_screen_bbox/require_camera_outside_world_bbox
        = spec configured values

FAIL form 2: CAMERA_TYPE_MISMATCH
  keys: same as form 1 + actual_type

FAIL form 3: NON_FINITE_EVALUATED_VERTEX
  keys: same as form 1 (minus camera_object_name)
  Note: evaluated_mesh_names populated with names up to the failing mesh

FAIL form 4: NO_EVALUATED_GEOMETRY
  keys: same as form 1
  Note: evaluated_mesh_names=[]

FAIL form 5: BEHIND_CAMERA
  keys: same as form 1
  Note: surviving_corners=0, screen_bbox=None

FAIL form 6: SCREEN_BBOX_REQUIREMENT_NOT_MET
  keys: same as form 1 + failed_checks

FAIL form 7: INSUFFICIENT_VISIBLE_PROJECTED_CORNERS
  keys: same as form 1
  Note: surviving_corners < mvc

FAIL form 8: CAMERA_INSIDE_WORLD_BBOX
  keys: same as form 1
  Note: camera_world_location populated, union_bbox populated
```

### 13.7 统一键集合设计

```text
DESIGN_DECISION: 每个 FAIL form 包含完全相同的键集合（共 14 键）：

  result, group_id, failure_code,
  camera_object_name, evaluated_mesh_names,
  surviving_corners, screen_bbox,
  required_screen_bbox, camera_world_location,
  require_camera_outside_world_bbox,
  failed_checks, actual_type, union_bbox, minimum_visible_projected_corner_count

不可用字段设为 null（Python None），不省略键。

RATIONALE: 与 Camera Check 一致的结构化方法 — 统一键集合支持 assert_dict_equal
精确断言、简化测试编写。

FINAL_PASS_KEY_SET (16):
  result, group_id, camera_object_name, evaluated_mesh_names,
  surviving_corners, screen_bbox, required_screen_bbox,
  camera_world_location, require_camera_outside_world_bbox,
  minimum_visible_projected_corner_count, union_bbox,
  per_source_summary, failed_checks, actual_type, failure_code, note

其中 PASS 时: failure_code=null, failed_checks=null, actual_type=null, note=null
```

---

## 14. Failure Codes、Error Types 和 Operations

### 14.1 Failure Codes (7)

```text
CAMERA_OBJECT_NOT_FOUND
  — 相机对象零匹配或多匹配

CAMERA_TYPE_MISMATCH
  — 相机对象存在但 type != 'CAMERA'

NON_FINITE_EVALUATED_VERTEX
  — 任一 evaluated mesh 顶点世界坐标为 NaN 或 Inf

NO_EVALUATED_GEOMETRY
  — 去重后零 MESH 对象 OR 所有 MESH 零顶点 OR 所有顶点被非有限过滤

BEHIND_CAMERA
  — 所有 8 个 bbox 角点 projected_z <= 0

SCREEN_BBOX_REQUIREMENT_NOT_MET
  — screen bbox 不满足 required_screen_bbox

INSUFFICIENT_VISIBLE_PROJECTED_CORNERS
  — surviving corners < minimum_visible_projected_corner_count

CAMERA_INSIDE_WORLD_BBOX
  — require_camera_outside_world_bbox=true 且相机在 union bbox 内或面上
```

### 14.2 Error Types (1)

```text
PROJECTION_GROUP_COMPUTATION_ERROR
  — 统一的 ERROR type，与 Camera Check 的 CAMERA_CHECK_COMPUTATION_ERROR 一致
```

### 14.3 Operations (13)

```text
RESOLVE_CAMERA_OBJECT        — camera_object_name 查找失败（name 读取异常）
RESOLVE_ADDITIONAL_OBJECT    — additional_object_names 中对象 name 读取异常
READ_SCENE_OBJECTS           — scene.objects 物化失败
COLLECT_GEOMETRY_SCOPE       — _collect_geometry_scope_objects 抛出 RuntimeError
GET_EVALUATED_DEPSGRAPH      — bpy.context.evaluated_depsgraph_get() 失败
EVALUATED_GET                — obj.evaluated_get(depsgraph) 失败
TO_MESH                      — evaluated.to_mesh() 失败
TO_MESH_CLEAR                — evaluated.to_mesh_clear() 失败（覆盖所有 pending result）
READ_EVALUATED_MATRIX_WORLD  — evaluated.matrix_world 读取失败
READ_MESH_VERTICES           — mesh.vertices 或 v.co 读取失败
TRANSFORM_VERTEX_TO_WORLD_SPACE — mw @ vertex_co 运算失败
COMPUTE_UNION_BBOX           — all_world_vertices 聚合后 bbox 计算异常
PROJECT_BBOX_CORNER          — world_to_camera_view 调用异常
```

---

## 15. 读取次数合同

### 15.1 Scene Objects

```text
SCENE_OBJECTS_MATERIALIZATION:
  scene.objects 在 _check_root_objects 的 per-target 缓存阶段已物化。
  Projection Groups 在 per-target loop 之后执行，
  通过 _target_caches 中的已物化数据访问 object 名称和 identity。

  不得独立重新物化 scene.objects。
```

### 15.2 Depsgraph

```text
DEPGRAPH_MATERIALIZATION:
  bpy.context.evaluated_depsgraph_get() 在每个投影组中调用一次。
  N 个投影组 → N 次 depsgraph 调用。

  因为不同投影组可能指定不同相机（不同 camera_object_name），
  无法在组间共享相机对象，但 depsgraph 可以共享。

OPTIMIZATION:
  整个 Projection Groups 检查中 depsgraph 只获取一次。
  所有投影组共享同一个 depsgraph。
```

### 15.3 obj.name 读取

```text
单次遍历：所有投影组的 camera_object_name 解析
和 additional_object_names 解析共享一次 scene.objects 遍历的 name 查询。

使用 _target_caches 中的 scene_name_by_id 时，
name 已在 root 阶段读取完成 → 零额外 name 读取。
```

### 15.4 matrix_world 读取

```text
camera_obj.matrix_world: 每个投影组一次（获取相机位置）。
evaluated.matrix_world: 每个 evaluated mesh 一次（与 Camera Check 相同）。

Scope Guard 授权集合需包含 _check_projection_groups。
```

---

## 16. 入口集成

### 16.1 open_blend_and_get_scene 修改

```text
新增参数：
  projection_groups_block = spec.get("projection_groups")

在 per-target loop 之后调用：

  pg_results = _check_projection_groups(
      scene,
      projection_groups_block,
      per_target_results,
      _target_caches=_target_caches,
      targets=targets,
  )

  scene_data["projection_group_results"] = pg_results

集成位置：在 per-target loop 的整体 recompute 之后、
在 return scene_data 之前。
```

### 16.2 _validate_and_open_spec 修改

```text
新增 pre-open 调用：
  pg_errs = _validate_projection_groups_rules_preopen(spec)
  pre_open_errs.extend(pg_errs)

在 _validate_camera_check_rules_preopen 之后。

新增 projection_groups_block 传递：
  projection_groups_block = spec.get("projection_groups")

  scene_data = reader.open_blend_and_get_scene(
      abs_blend, spec["scene_name"], scene_rules, targets,
      collection_rules_block=collection_rules_block,
      projection_groups_block=projection_groups_block,
  )

新增 projection_group_overall 判定：
  pg_results = scene_data.get("projection_group_results", [])
  projection_group_overall = _compute_projection_group_overall(pg_results)

  加入 overall 判定：
    target_error OR global_collection_error OR projection_group_overall == "ERROR"
    → EXIT_ERROR

新增 projection_group_results 传入 build_pass/build_fail：
  build_pass_result(..., projection_groups=pg_results)
  build_fail_result(..., projection_groups=pg_results)
```

### 16.3 _compute_projection_group_overall

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

### 16.4 禁止在 _collect_target_errors 中收集

```text
Projection Groups ERROR 不在 _collect_target_errors 中收集。
Projection Groups 有自己独立的 per-group result 结构。
其 ERROR 通过 projection_group_overall → EXIT_ERROR 路径处理。
```

---

## 17. Per-Source 结果跟踪

### 17.1 Per-Source Summary

```text
每个投影组的 PASS 和 FAIL 结果包含 per_source_summary：

per_source_summary: {
  "target_ids": {
    "CHR_MALE_A": {
      "geometry_scope": "SELF_AND_DESCENDANT_MESHES",
      "mesh_objects_found": 3,
      "mesh_objects_contributing": 3
    },
    ...
  },
  "additional_object_names": {
    "CashRegister_01": {"status": "found", "type": "MESH"},
    "NonexistentObj": {"status": "not_found"},
    "NonMeshObj": {"status": "wrong_type", "actual_type": "EMPTY"}
  }
}

FAIL 时 per_source_summary 仍然完整填充（反映实际找到了什么）。
```

---

## 18. 设计关闭矩阵

### 18.1 DESIGN_FREEDOM 关闭 (DF-PG-01 至 DF-PG-32)

| ID | 最终决定 | 设计节 | 实施 | 测试 |
|----|---------|--------|------|------|
| DF-PG-01 | 结果字典结构 — 见 §13 | §13 | I1 | I1 |
| DF-PG-02 | PASS/FAIL/ERROR/NOT_CHECKED — 见 §4.2, §12, §13 | §4, §12, §13 | I1 | I1 |
| DF-PG-03 | failure_code — 7 个，见 §14.1 | §14.1 | I1 | I1 |
| DF-PG-04 | error_type + operation — 1 error type, 13 operations, 见 §14 | §14 | I1 | I1 |
| DF-PG-05 | 优先级 — 见 §12.1 | §12.1 | I2 | I2 |
| DF-PG-06 | target_ids 空 → additional_object_names 可单独提供几何 | §7.3 | I2 | I2 |
| DF-PG-07 | target_ids 重复 → pre-open ERROR | §5.2 RULE_5 | I1 | I1 |
| DF-PG-08 | additional_object_names 空 → 正常 | §7.1 | I2 | I2 |
| DF-PG-09 | target_ids 和 additional_object_names 都空 → pre-open ERROR | §5.2 RULE_7 | I1 | I1 |
| DF-PG-10 | additional_object_names 对象不存在 → 跳过 | §7.1 | I2 | I2 |
| DF-PG-11 | additional_object_names 非 MESH → 跳过 | §7.1 | I2 | I2 |
| DF-PG-12 | 重复对象 → 按 id() 去重 | §7.2 | I2 | I2 |
| DF-PG-13 | camera 解析 → 复用 Camera Check 精确匹配 | §6 | I2 | I2 |
| DF-PG-14 | 相机不在 Scene → FAIL CAMERA_OBJECT_NOT_FOUND | §6.1 | I2 | I2 |
| DF-PG-15 | type != CAMERA → FAIL CAMERA_TYPE_MISMATCH | §6.1 | I2 | I2 |
| DF-PG-16 | 多匹配 → FAIL CAMERA_OBJECT_NOT_FOUND | §6.1 | I2 | I2 |
| DF-PG-17 | 8 角点投影模型 — 复用 R1 §19 | §9 | I2 | I2 |
| DF-PG-18 | mvc > 8 → pre-open ERROR | §5.2 RULE_1 | I1 | I1 |
| DF-PG-19 | mvc = 0 → 允许 | §5.2 | I2 | I2 |
| DF-PG-20 | 8 角点全在相机后方 → FAIL BEHIND_CAMERA | §9.2 | I2 | I2 |
| DF-PG-21 | 轴向语义 — X containment, Y coverage | §10.1 | I2 | I2 |
| DF-PG-22 | camera outside — 逐轴严格外，面上算 inside | §11.1 | I2 | I2 |
| DF-PG-23 | 空联合 bbox → FAIL NO_EVALUATED_GEOMETRY | §7.3 | I2 | I2 |
| DF-PG-24 | 零顶点/非有限 → FAIL，failure_code 和结果字典已定 | §8, §13, §14.1 | I2 | I2 |
| DF-PG-25 | per-group overall — 单组单 result | §13 | I1 | I1 |
| DF-PG-26 | 顶层聚合 → projection_group_overall | §4.2 | I1 | I1 |
| DF-PG-27 | 多组聚合 → 任一 ERROR 即 ERROR, 任一 FAIL 即 FAIL | §4.2, §16.3 | I1 | I1 |
| DF-PG-28 | pre-open 验证 — _validate_projection_groups_rules_preopen | §5 | I1 | I1 |
| DF-PG-29 | 读取次数 — 复用 _target_caches, 单次 depsgraph | §15 | I2 | I2 |
| DF-PG-30 | camera inside bbox → FAIL CAMERA_INSIDE_WORLD_BBOX | §11.1 | I2 | I2 |
| DF-PG-31 | additional_object_names 元素 — pre-open 拒绝空字符串 | §5.2 RULE_4 | I1 | I1 |
| DF-PG-32 | 四个配置值源自 spec，禁止硬编码百分比 | §2 (design goal 8) | I2 | I2 |

### 18.2 DOCUMENTATION_GAP 关闭 (DG-PG-01 至 DG-PG-08)

| ID | 最终决定 | 设计节 |
|----|---------|--------|
| DG-PG-01 | 设计以 R2 §10.2 为权威来源 | §1 |
| DG-PG-02 | NOT_CHECKED 条件 — 无 per-group NOT_CHECKED; null/[] → 整体跳过 | §4.1, §13.4 |
| DG-PG-03 | 结果字典结构 — 完整定义 | §13 |
| DG-PG-04 | failure_code/error_type/operation — 完整定义 | §14 |
| DG-PG-05 | require_camera_outside_world_bbox 精确语义 — 逐轴严格外 | §11.1 |
| DG-PG-06 | R1 不存在 — 不影响，R2 §10.2 为完整定义 | §1 |
| DG-PG-07 | Design Spec R1 不包含 projection_groups — R2 新增，直接使用 R2 §10.2 | §1 |
| DG-PG-08 | required_screen_bbox 轴向语义 — mixed axial model | §10.1 |
```

---

## 19. 实施拆分

### 19.1 I1: Pre-open、结果框架和入口集成

```text
SCOPE:
  — _validate_projection_groups_rules_preopen (pre-open 6 rules)
  — _compute_projection_group_overall
  — build_pass_result / build_fail_result projection_groups 参数集成
  — _validate_and_open_spec 集成 (pre-open + overall + build_*_result)
  — open_blend_and_get_scene 参数和结果集成
  — _check_projection_groups 桩函数 (返回空结果)
  — projection_group_results 键在所有 _base_result 中的存在
  — _collect_target_errors 明确不收集投影组 ERROR
  — 全部 result dict 形式的精确键集定义（CPython 测试用）
  — CPython 聚焦测试 (~30 tests)

NOT_IN_I1:
  — Blender 运行时
  — 联合几何收集
  — 投影算法
  — camera 查找
  — Scope Guard
```

### 19.2 I2: Blender 运行时

```text
SCOPE:
  — _check_projection_groups 完整实现
  — camera_object_name 解析
  — 联合几何收集 (target_ids geometry_scope + additional_object_names)
  — 去重
  — evaluated geometry 迭代 (复用 Camera Check 模式)
  — union bbox 计算
  — 8 角点投影 (world_to_camera_view)
  — screen bbox 检查
  — mvc 检查
  — require_camera_outside_world_bbox 检查
  — per_source_summary
  — depsgraph 共享
  — _target_caches 读取
  — Scope Guard 授权集合更新
  — Blender 临时场景验证 (~20 scenarios)
  — pytest wrapper

NOT_IN_I2:
  — 修改已锁定 Camera Check 生产代码
```

### 19.3 E: 聚焦测试、完整回归和锁定

```text
SCOPE:
  — I1 + I2 全部测试通过
  — 完整 protocol_guard 回归
  — 14A Core 回归
  — 直接回归（Camera Check 测试等）
  — 生产缺陷确认
  — 正式锁定证据

NOT_IN_E:
  — 真实项目 .blend 验证
  — 渲染
```

---

## 20. 测试矩阵

### 20.1 I1 CPython Tests (~30 tests)

```text
Pre-open 验证 (8):
  — mvc > 8 → ERROR
  — bbox 值超出 [0,1] → ERROR（四个边界各一）
  — additional_object_names 空字符串 → ERROR
  — target_ids 重复 → ERROR
  — additional_object_names 重复 → ERROR
  — target_ids + additional_object_names 都空 → ERROR

启用判定 (4):
  — projection_groups null → projection_group_results: []
  — projection_groups [] → projection_group_results: []
  — projection_groups 非空 → projection_group_results 非空
  — projection_groups 非空且全部 PASS → projection_group_overall: PASS

聚合 (5):
  — 任一 ERROR → projection_group_overall: ERROR
  — 任一 FAIL（无 ERROR）→ projection_group_overall: FAIL
  — 全部 PASS → projection_group_overall: PASS
  — projection_group_overall ERROR → EXIT_ERROR
  — projection_group_overall FAIL（无其他 FAIL/ERROR）→ EXIT_FAIL

入口集成 (6):
  — pass/fail/error result builder 包含 projection_group_results
  — build_error_result (input_errors) 保持 projection_group_results: []
  — pre-open ERROR 阻断路径验证
  — _validate_and_open_spec 调用链顺序
  — projection_groups_block 传递到 open_blend_and_get_scene
  — _collect_target_errors 不收集投影组 ERROR

结果字典键集 (7):
  — PASS 精确键集
  — 每个 FAIL form 精确键集
  — ERROR 精确键集
  — null 键值验证
```

### 20.2 I2 Blender Scenarios (~20 scenarios)

```text
PG-BL-01: 单 target + no additional → union bbox = target geometry_scope → PASS
PG-BL-02: 两个 target_ids → union bbox 聚合 → PASS
PG-BL-03: target_ids + additional_object_names → 去重 + union → PASS
PG-BL-04: additional_object_names 中对象不存在 → 跳过 → 剩余几何 → PASS
PG-BL-05: additional_object_names 中对象非 MESH → 跳过 → PASS
PG-BL-06: target_ids 和 additional_object_names 重叠对象 → 按 id 去重 → PASS
PG-BL-07: 相机零匹配 → FAIL CAMERA_OBJECT_NOT_FOUND
PG-BL-08: 相机多匹配 → FAIL CAMERA_OBJECT_NOT_FOUND
PG-BL-09: 相机 type 非 CAMERA → FAIL CAMERA_TYPE_MISMATCH
PG-BL-10: 零顶点 mesh → FAIL NO_EVALUATED_GEOMETRY (per R2 §4.3)
PG-BL-11: 所有角点在相机后方 → FAIL BEHIND_CAMERA
PG-BL-12: 水平 containment 不满足 → FAIL SCREEN_BBOX_REQUIREMENT_NOT_MET
PG-BL-13: 垂直 coverage 不满足 → FAIL SCREEN_BBOX_REQUIREMENT_NOT_MET
PG-BL-14: mvc 不足 → FAIL INSUFFICIENT_VISIBLE_PROJECTED_CORNERS
PG-BL-15: require_camera_outside_world_bbox=true 相机在 bbox 内 → FAIL
PG-BL-16: require_camera_outside_world_bbox=true 相机在 bbox 外 → PASS
PG-BL-17: require_camera_outside_world_bbox=false（默认）→ 不检查
PG-BL-18: 两个投影组 → 独立 per-group result → 聚合
PG-BL-19: 不同组不同相机 → 各自独立查找
PG-BL-20: to_mesh_clear 异常 → ERROR TO_MESH_CLEAR 覆盖 pending
```

### 20.3 E 回归范围

```text
完整 protocol_guard 回归
14A Core 回归
直接回归（Camera Check、Ground Contact、Material Assignment 测试）
```

---

## 21. Scope Guard

```text
Phase 3 minimum AST Scope Guard 授权：

需添加 _check_projection_groups 对以下函数的访问：
  — world_to_camera_view (已在 Camera Check 授权中)
  — matrix_world (已在 Camera Check 授权中)
  — evaluated_depsgraph_get (已在 Camera Check 授权中)
  — evaluated_get (已在 Camera Check 授权中)
  — to_mesh (已在 Camera Check 授权中)
  — to_mesh_clear (已在 Camera Check 授权中)
  — _collect_geometry_scope_objects (已在 Camera Check 授权中)
  — bpy.context (已在 Camera Check 授权中)
  — bpy.data.scenes (已在 Camera Check 授权中)

Camera Check 已授权的函数可能无需额外更新。
需确认 _check_projection_groups 名称本身在授权集合中。
```

---

## 22. 设计统计

```text
RESULT_DICT_FORM_COUNT: 10 (1 PASS + 8 FAIL + 1 ERROR)
FAILURE_CODE_COUNT: 8 (CAMERA_OBJECT_NOT_FOUND, CAMERA_TYPE_MISMATCH,
  NON_FINITE_EVALUATED_VERTEX, NO_EVALUATED_GEOMETRY, BEHIND_CAMERA,
  SCREEN_BBOX_REQUIREMENT_NOT_MET, INSUFFICIENT_VISIBLE_PROJECTED_CORNERS,
  CAMERA_INSIDE_WORLD_BBOX)
ERROR_TYPE_COUNT: 1 (PROJECTION_GROUP_COMPUTATION_ERROR)
ERROR_OPERATION_COUNT: 13
IMPLEMENTATION_STAGE_COUNT: 3 (I1, I2, E)
DESIGN_FREEDOM_CLOSED_COUNT: 32
DOCUMENTATION_GAP_CLOSED_COUNT: 8
UNRESOLVED_DESIGN_DECISIONS: 0
```

---

*Design R1 complete. All 32 design freedoms and 8 documentation gaps are closed. Awaiting independent review.*
