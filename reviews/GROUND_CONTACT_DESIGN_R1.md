# Ground Contact Runtime Design R2

```text
DOCUMENT_ID: GROUND_CONTACT_DESIGN
DESIGN_VERSION: R2
TASK_ID: GROUND_CONTACT_DESIGN_R1_R2_CORRECTION
MASTER_MAP_VERSION: R75
DATE: 2026-07-26
DESIGN_STATUS: FORMALLY_LOCKED
FORMALLY_LOCKED: TRUE
IMPLEMENTATION_AUTHORIZED: FALSE
DESIGN_AUTHORIZATION: USER_EXPLICITLY_AUTHORIZED
```

## 1. 文档身份与状态

```text
TASK_TYPE: DESIGN_CORRECTION
SOURCE_DESIGN_VERSION: R1
TARGET_DESIGN_VERSION: R2
PRODUCTION_PROGRESS_THIS_ROUND: FALSE

WHY_THIS_NON_PRODUCTION_WORK_IS_NECESSARY:
  R1 的 root 解析、geometry-scope ERROR 边界、
  world-space operation、清理次数和实施拆分仍不闭环，
  直接按其实现会修改锁定函数并产生错误分类。

WHAT_DECISION_IT_UNLOCKS:
  形成可直接实施、不会侵犯锁定代码、
  且符合精简流程的 Ground Contact 唯一设计合同。

EXIT_CONDITION:
  七个固定阻断点全部修复，
  正文、伪代码、矩阵和机器摘要一致，然后立即停止。
```

## 2. 权威来源和优先级

```text
PRIORITY_1: Blender_固定资产模板路线_新对话交接文档_v4.md
  — AUTHORITATIVE_REQUIREMENT:
    §7.5 "人物脚底接近地面"
    §9 L1-A "脚底接近地面"
    §9 固定约束 "人物脚底最低点与地面误差在项目容差内"
    §9 L1-B 通过条件 "顾客脚底接地"
    §10 L1-D "顾客脚底接地"

PRIORITY_2: ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md §4, §14
  — AUTHORITATIVE_IMPLEMENTATION_CONTRACT:
    evaluated geometry 数据链 (depsgraph → evaluated_get → to_mesh → vertices → to_mesh_clear)
    matrix_world 变换到世界空间
    to_mesh_clear 放 finally
    零顶点 → FAIL (NO_EVALUATED_GEOMETRY)
    to_mesh/to_mesh_clear 异常 → ERROR
    顶点含 NaN → FAIL

PRIORITY_3: asset_scene_preflight_core.py lines 343-348
  — LOCKED_SCHEMA:
    target.ground_contact.ground_z (optional finite number)
    target.ground_contact.ground_contact_tolerance (optional finite number, >= 0)

PRIORITY_4: PHASE_3_MINIMUM_DESIGN_SPEC_R1.md §5.9, §5.10
  — APPLICABLE_GENERIC_RULES:
    数值比较使用绝对差值 |actual - expected| <= tolerance
    actual 为 NaN → FAIL
    actual 为 Infinity → FAIL
    等于 tolerance 时 PASS
    禁止保存、修改 transform/visibility/material、渲染

PRIORITY_5: GROUND_CONTACT_ORIGINAL_REQUIREMENT_AUDIT_REPORT.md (R2 Correction)
  — AUDIT_RESULT: REQUIREMENTS_SUFFICIENT_FOR_DESIGN
    TRUE_CONTRACT_CONFLICTS: 0
    DESIGN_FREEDOMS: 16 (DM-01 至 DM-16)
    DOCUMENTATION_GAPS: 1 (DG-01: operation/failure_code 未命名)

PRIORITY_6: PROJECT_CODEIFICATION_MASTER_MAP.md R75
  — CURRENT_STATE: NOT_STARTED_RUNTIME, DESIGN_AUTHORIZED: FALSE → 本轮授予 TRUE

PRIORITY_7: CLAUDE.md
  — PROJECT_RULES

REFERENCE_CONVENTION:
  — ROTATION_DESIGN_R3.md (result structure, ERROR mapping, read count table)
  — MATERIAL_ASSIGNMENT_DESIGN_R1.md (geometry scope reuse, per-target integration)
  — ANIMATION_STATE_DESIGN_R5.md (independent per-target check integration)
  — COLLECTION_RULES_DESIGN_R1.md (pre-open 验证, ERROR 聚合模式)
```

## 3. 设计目标

1. 为 Ground Contact 字段组定义唯一、完整、可独立实现和测试的运行时设计。
2. 所有 16 项审计 DM 均给出唯一最终决定，不保留"实现时再决定"的语义。
3. 结果字典键集合唯一，支持 `assert_dict_equal` 精确断言。
4. 所有异常路径有唯一 operation，所有 FAIL 有唯一 failure_code。
5. 配置、前置条件、算法、结果、清理、集成和副作用边界全部封闭。

## 4. 明确非目标

```text
EXPLICITLY_EXCLUDED:
  — 视觉质量判断 (HUMAN_JUDGMENT_ONLY)
  — 角色站立状态判断 (由 Standing 字段组负责)
  — 角色朝向判断 (由 Facing 字段组负责)
  — 角色层级判断 (由 Hierarchy 字段组负责)
  — 地面视觉外观
  — 碰撞检测或物理模拟
  — 自动修正角色位置
  — 自动调整 ground_z
  — 保存 .blend
  — 渲染
  — 跨帧动画验证
  — 真实项目 .blend 验证 (REAL_PROJECT_BLEND_OPENED: FALSE)
```

## 5. 已锁定输入事实

以下事实来自权威材料，本轮不得重新设计：

```text
F-01: Ground Contact 使用 evaluated geometry 的 lowest_z (R2 §4, §14)
F-02: depsgraph = bpy.context.evaluated_depsgraph_get() (R2 §4.1)
F-03: evaluated = obj.evaluated_get(depsgraph) (R2 §4.2)
F-04: mesh = evaluated.to_mesh() (R2 §4.2)
F-05: 顶点通过 evaluated.matrix_world 变换到世界空间 (R2 §4.2)
F-06: to_mesh_clear 必须在 finally 中执行，并且仅对成功返回临时 mesh 的 to_mesh() 调用执行 (R2 §4.2)
F-07: 零顶点 → FAIL with NO_EVALUATED_GEOMETRY (R2 §4.3)
F-08: depsgraph 求值失败 → ERROR (R2 §4.3)
F-09: to_mesh 或 to_mesh_clear 异常 → ERROR (R2 §4.3)
F-10: 数值比较使用 abs(actual_lowest_z - ground_z) <= ground_contact_tolerance (R1 §5.9, R2 §14)
F-11: 等于 tolerance 时 PASS (R1 §5.9 公式)
F-12: NaN 或 Infinity 的实际数值必须 FAIL (R1 §5.9, R2 §4.3)
F-13: 0.0 tolerance 是合法值 (14A Core Schema)
F-14: 不得保存、渲染、修改 transform/visibility/material/render settings/scene camera/对象集合 (R1 §5.10)
F-15: Schema 字段路径: target.ground_contact.ground_z, target.ground_contact.ground_contact_tolerance (14A Core)
F-16: R1 顶层字段 target.ground_z / target.ground_contact_tolerance 已被嵌套 Schema 取代，不得恢复
F-17: geometry_scope 字段: target.geometry_scope (必填，SELF_MESH / DESCENDANT_MESHES / SELF_AND_DESCENDANT_MESHES)
F-18: _check_root_objects: MUST_NOT_MODIFY — Ground Contact 只读取已有 checks.object_exists 和 checks.object_type，不在 _check_root_objects 中添加任何分支
F-19: _recompute_target_overall 自动纳入新增 checks.*.result
F-20: 结果嵌套路径: checks.ground_contact
```

## 6. 配置启用语义

### 6.1 判定模型

Ground Contact 采用**全有或全无 (all-or-nothing)** 配置模型：

```text
RULE:
  ground_contact 缺失或为 null:
    → NOT_CHECKED

  ground_contact 为 dict，且 ground_z 与 ground_contact_tolerance 都是 absent/null:
    → NOT_CHECKED

  两个字段都为非 None:
    → 启用 Ground Contact 检查

  恰好一个字段为非 None:
    → 打开 .blend 前 INPUT ERROR
```

理由：
- ground_z 没有 tolerance 无法比较；tolerance 没有 ground_z 没有参照点。
- 与 Standing Up Axis 的三字段 all-or-nothing 模式一致。
- 不得发明未经材料支持的默认值（禁止默认 ground_z=0.0 或 tolerance=0.02）。

### 6.2 配置状态表

| # | ground_contact | ground_z | ground_contact_tolerance | 结果 | 阶段 |
|---|---|---|---|---|---|
| 1 | 缺失 | N/A | N/A | NOT_CHECKED | 运行时 |
| 2 | null | N/A | N/A | NOT_CHECKED | 运行时 |
| 3 | {} | absent | absent | NOT_CHECKED | 运行时 |
| 4 | {} 或 present | null | null | NOT_CHECKED | 运行时 |
| 5 | present | present (finite) | present (finite, >=0) | 执行检查 | 运行时 |
| 6 | present | present (finite) | absent/null | INPUT ERROR | 打开 .blend 前 |
| 7 | present | absent/null | present (finite, >=0) | INPUT ERROR | 打开 .blend 前 |

### 6.3 Pre-open 错误格式

```text
ERROR PREFIX: "INVALID_GROUND_CONTACT_RULE_RELATION"
MESSAGE FORMAT:
  "INVALID_GROUND_CONTACT_RULE_RELATION: target '<target_id>' "
  "ground_contact missing required fields: [<sorted_field_list>]"

缺失字段列表稳定顺序 (casefold):
  ["ground_contact_tolerance"]  — 当 ground_z 存在而 tolerance 缺失
  ["ground_z"]                  — 当 tolerance 存在而 ground_z 缺失

多 target 错误稳定顺序:
  按 target_id casefold 排序。
  同一 target 只产生一条错误（即使两个字段各有问题，缺失列表聚合后为一条）。

示例:
  target 'CHR_A': ground_z=0.0, tolerance=None
    → "INVALID_GROUND_CONTACT_RULE_RELATION: target 'CHR_A' "
      "ground_contact missing required fields: ['ground_contact_tolerance']"

  target 'CHR_B': ground_z=None, tolerance=0.02
    → "INVALID_GROUND_CONTACT_RULE_RELATION: target 'CHR_B' "
      "ground_contact missing required fields: ['ground_z']"
```

### 6.4 验证位置

配置关系验证发生在**打开 .blend 之前**（pre-open 层），与 Standing Up Axis 的 `_validate_standing_up_axis_rules_preopen` 处于同一层级。

原因：
- 部分配置是明确的用户错误，不应等到运行时才发现。
- 与 Standing 的 all-or-nothing 模式完全一致。
- Pre-open ERROR 阻止打开 .blend（exit 2），节省资源。

### 6.5 判定伪代码

```python
def _validate_ground_contact_rules_preopen(targets):
    """Validate all-or-nothing: exactly one of {ground_z, tolerance} present → ERROR."""
    errors = []
    fields = ["ground_z", "ground_contact_tolerance"]
    for target in targets:
        tid = target.get("target_id", "")
        gc = target.get("ground_contact")
        if not isinstance(gc, dict):
            continue

        present = [f for f in fields if gc.get(f) is not None]
        if len(present) == 1:
            missing = sorted(
                [f for f in fields if f not in present],
                key=lambda n: (n.casefold(), n),
            )
            errors.append(
                f"INVALID_GROUND_CONTACT_RULE_RELATION: target '{tid}' "
                f"ground_contact missing required fields: {missing}"
            )
    return sorted(errors, key=lambda e: (e.casefold(), e))
```

## 7. Root 前置条件与 geometry scope

### 7.1 Root 前置条件行为

Ground Contact 不修改 `_check_root_objects`。Root 前置结果只由 `_check_ground_contact(scene, target, per_target_result)` 读取已有 `checks.object_exists` 和 `checks.object_type` 后决定。

Ground Contact 不要求 root 为特定 type。EMPTY、ARMATURE、MESH 均可。

| 已有 root 状态 | Ground Contact 结果 | note |
|---|---|---|
| ROOT_OBJECT_NOT_FOUND (object_exists.result == "FAIL") | NOT_CHECKED | ROOT_OBJECT_NOT_FOUND |
| AMBIGUOUS_ROOT_OBJECT_NAME (object_exists.error_type == "AMBIGUOUS_ROOT_OBJECT_NAME") | NOT_CHECKED | AMBIGUOUS_ROOT_OBJECT_NAME |
| ROOT_OBJECT_TYPE_MISMATCH (object_type.result == "FAIL") | NOT_CHECKED | ROOT_OBJECT_TYPE_MISMATCH |
| 已有 root 阶段为 ERROR (object_exists.result == "ERROR") | NOT_CHECKED | ROOT_LOOKUP_ERROR |
| root 不在目标 Scene (由后续 RESOLVE_ROOT_OBJECT 自行判明) | NOT_CHECKED | ROOT_OBJECT_NOT_FOUND |

检测逻辑（读取已有 checks，不做新 bpy 调用）：

```python
checks = per_target_result.get("checks", {})
obj_exists = checks.get("object_exists", {})
obj_type = checks.get("object_type", {})

if obj_exists.get("result") == "FAIL":
    return NOT_CHECKED("ROOT_OBJECT_NOT_FOUND")
if obj_exists.get("error_type") == "AMBIGUOUS_ROOT_OBJECT_NAME":
    return NOT_CHECKED("AMBIGUOUS_ROOT_OBJECT_NAME")
if obj_exists.get("result") == "ERROR":
    return NOT_CHECKED("ROOT_LOOKUP_ERROR")
if obj_type.get("result") == "FAIL":
    return NOT_CHECKED("ROOT_OBJECT_TYPE_MISMATCH")
```

### 7.2 geometry_scope 来源

```text
决策: 直接复用 target.geometry_scope，不新增 Ground Contact 专用 scope 字段。

理由:
  — target.geometry_scope 已定义三种取值 (SELF_MESH, DESCENDANT_MESHES, SELF_AND_DESCENDANT_MESHES)
  — 该字段为 14A Core 必填项，语义覆盖 Ground Contact 需求
  — Material Assignment 已采用相同复用模式
  — 无需重新表达已锁定的语义

取值:
  SELF_MESH:               仅 root 自身，且仅当 root_type == 'MESH' 时纳入
  DESCENDANT_MESHES:       root 的所有递归后代中 type == 'MESH' 的 Scene member，不含 root
  SELF_AND_DESCENDANT_MESHES: 以上两者的并集（identity 去重）
```

### 7.3 对象收集

直接复用已锁定的 `_collect_geometry_scope_objects()` helper（`blender_scene_reader.py` lines 1659-1751）。

该 helper 已经处理：
- Scene membership 过滤（identity-based）
- 非 MESH 对象排除
- 递归 descendants
- 确定性排序（name casefold + materialization index）
- identity 去重
- Scene 外分支剪枝

Ground Contact 不得重新实现等效逻辑。

### 7.4 非 MESH root 行为

```text
SELF_MESH + root type != 'MESH': geometry scope objects = []  → NO_EVALUATED_GEOMETRY (FAIL)
DESCENDANT_MESHES + root type != 'MESH': 正常收集后代 MESH，root 自身不参与
SELF_AND_DESCENDANT_MESHES + root type != 'MESH': SELF 部分为空，仅 DESCENDANT_MESHES
```

## 8. Evaluated Geometry 算法

### 8.1 完整伪代码

```text
FUNCTION _check_ground_contact(scene, target, per_target_result):
    # ── Step 1: 解析配置 ──
    gc_block = target.get("ground_contact")
    if gc_block is None or not isinstance(gc_block, dict):
        return {"result": "NOT_CHECKED", "note": "GROUND_CONTACT_NOT_CONFIGURED"}

    gz = gc_block.get("ground_z")
    tol = gc_block.get("ground_contact_tolerance")
    if gz is None and tol is None:
        return {"result": "NOT_CHECKED", "note": "GROUND_CONTACT_NOT_CONFIGURED"}
    # Pre-open 保证: 此时 gz 和 tol 都为非 None

    ground_z = gz
    tolerance = tol

    # ── Step 2: 检查已有 root 前置结果 ──
    checks = per_target_result.get("checks", {})
    obj_exists = checks.get("object_exists", {})
    obj_type = checks.get("object_type", {})

    if obj_exists.get("result") == "FAIL":
        return {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_NOT_FOUND"}
    if obj_exists.get("error_type") == "AMBIGUOUS_ROOT_OBJECT_NAME":
        return {"result": "NOT_CHECKED", "note": "AMBIGUOUS_ROOT_OBJECT_NAME"}
    if obj_exists.get("result") == "ERROR":
        return {"result": "NOT_CHECKED", "note": "ROOT_LOOKUP_ERROR"}
    if obj_type.get("result") == "FAIL":
        return {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_TYPE_MISMATCH"}

    # ── Step 3: 物化 scene.objects 恰好一次 ──
    try:
        scene_objects_ordered = list(scene.objects)
    except Exception:
        return ERROR(READ_SCENE_OBJECTS)

    scene_member_ids = {id(obj) for obj in scene_objects_ordered}
    scene_materialization_index = {
        id(obj): idx for idx, obj in enumerate(scene_objects_ordered)
    }

    # ── Step 4: 建立 name_by_id 并精确解析唯一 root ──
    scene_name_by_id = {}
    root_matches = []
    root_obj_name = target["root_object_name"]
    try:
        for obj in scene_objects_ordered:
            oname = obj.name
            scene_name_by_id[id(obj)] = oname
            if oname == root_obj_name:
                root_matches.append(obj)
    except Exception:
        return ERROR(RESOLVE_ROOT_OBJECT)

    if len(root_matches) != 1:
        # missing or ambiguous — but we already checked root preconditions above.
        # This is a defensive guard against race conditions.
        return {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_NOT_FOUND"}

    root_obj = root_matches[0]
    root_type_value = obj_type.get("actual")

    # ── Step 5: 以完整七参数调用 _collect_geometry_scope_objects ──
    geometry_scope_value = target["geometry_scope"]
    try:
        mesh_objects = _collect_geometry_scope_objects(
            scene_objects_ordered=scene_objects_ordered,
            scene_member_ids=scene_member_ids,
            scene_materialization_index=scene_materialization_index,
            scene_name_by_id=scene_name_by_id,
            root_obj=root_obj,
            root_type_value=root_type_value,
            geometry_scope_value=geometry_scope_value,
        )
    except RuntimeError as e:
        op = str(e)
        return ERROR(op)

    # ── Step 6: 空几何 → FAIL ──
    if len(mesh_objects) == 0:
        return FAIL(NO_EVALUATED_GEOMETRY, ground_z, tolerance)

    # ── Step 7: 获取 depsgraph (恰好一次) ──
    try:
        depsgraph = bpy.context.evaluated_depsgraph_get()
    except Exception:
        return ERROR(GET_EVALUATED_DEPSGRAPH)

    # ── Step 8: 遍历每个 MESH 对象 ──
    actual_lowest_z = float('inf')
    non_finite_found = False
    zero_vertex_found = False
    evaluated_mesh_names = []

    for mesh_obj, mesh_name in mesh_objects:
        evaluated_mesh_names.append(mesh_name)

        # 8a: evaluated_get (恰好一次)
        try:
            evaluated = mesh_obj.evaluated_get(depsgraph)
        except Exception:
            return ERROR(EVALUATED_GET)

        # 8b: to_mesh (恰好一次)
        try:
            mesh = evaluated.to_mesh()
        except Exception:
            return ERROR(TO_MESH)

        try:
            # 8c: 读取 matrix_world (恰好一次)
            try:
                mw = evaluated.matrix_world
            except Exception:
                return ERROR(READ_EVALUATED_MATRIX_WORLD)

            # 8d: 检查零顶点
            try:
                vertex_count = len(mesh.vertices)
            except Exception:
                return ERROR(READ_MESH_VERTICES)

            if vertex_count == 0:
                zero_vertex_found = True
                continue

            # 8e: 遍历顶点 — 世界空间变换 + 最低 Z 聚合
            try:
                for v in mesh.vertices:
                    # TRANSFORM_VERTEX_TO_WORLD_SPACE
                    try:
                        world_co = mw @ v.co
                        world_z = world_co.z
                    except Exception:
                        return ERROR(TRANSFORM_VERTEX_TO_WORLD_SPACE)

                    # COMPUTE_LOWEST_Z: 非有限值检查
                    if not math.isfinite(world_z):
                        non_finite_found = True
                        continue

                    # COMPUTE_LOWEST_Z: 最低 Z 聚合
                    if world_z < actual_lowest_z:
                        actual_lowest_z = world_z
            except Exception:
                return ERROR(READ_MESH_VERTICES)
        finally:
            # 8f: to_mesh_clear 在 finally 中 (恰好一次，仅因 to_mesh 已成功)
            try:
                evaluated.to_mesh_clear()
            except Exception:
                return ERROR(TO_MESH_CLEAR)

    # ── Step 9: 聚合判定 ──
    if zero_vertex_found:
        return FAIL(NO_EVALUATED_GEOMETRY, ground_z, tolerance)

    if non_finite_found:
        return FAIL(NON_FINITE_EVALUATED_VERTEX_Z, ground_z, tolerance,
                    evaluated_mesh_names=evaluated_mesh_names)

    if not math.isfinite(actual_lowest_z):
        return FAIL(NO_EVALUATED_GEOMETRY, ground_z, tolerance)

    # ── Step 10: 容差比较 ──
    absolute_error = abs(actual_lowest_z - ground_z)
    if absolute_error <= tolerance:
        return PASS(ground_z, tolerance, actual_lowest_z, absolute_error,
                    evaluated_mesh_names)
    else:
        return FAIL(GROUND_CONTACT_OUT_OF_TOLERANCE, ground_z, tolerance,
                    actual_lowest_z, absolute_error, evaluated_mesh_names)
```

### 8.2 读取次数合同

| 操作 | 每个 target 调用次数 | 条件 |
|---|---|---|
| `scene.objects` 遍历 | 恰好 1 次 | 配置启用 + root 前置通过 |
| `obj.name` 读取 | 每个 scene object 恰好 1 次 | 同上（构建 name_by_id） |
| `_collect_geometry_scope_objects` | 恰好 1 次 | 同上 |
| `bpy.context.evaluated_depsgraph_get()` | 恰好 1 次 | 配置启用 + root 前置通过 + geometry scope 非空 |
| `obj.evaluated_get(depsgraph)` | 每个 MESH 恰好 1 次 | 同上 |
| `evaluated.to_mesh()` | 每个 MESH 恰好 1 次 | 同上 |
| `evaluated.matrix_world` | 每个成功 to_mesh 的 MESH 恰好 1 次 | to_mesh 已成功 |
| `mesh.vertices` 迭代 | 每个成功 to_mesh 的 MESH 恰好 1 次 | to_mesh 已成功 |
| `evaluated.to_mesh_clear()` | 每个成功 to_mesh 的 MESH 恰好 1 次 | to_mesh 已成功（finally） |
| `evaluated.to_mesh_clear()` | 0 次 | to_mesh 未成功或未调用 |

不跨 target 缓存 depsgraph、evaluated 对象或 mesh。

### 8.3 清理合同

```text
GUARANTEE:
  对每个成功返回临时 mesh 的 to_mesh() 调用:
    to_mesh_clear() 恰好调用一次，并位于 finally 中。
    无论后续顶点遍历、坐标变换或聚合是否成功，清理必然执行。

  evaluated_get 失败:
    to_mesh_clear 调用 0 次（未进入 to_mesh）。

  to_mesh 抛异常或没有成功产生临时 mesh:
    to_mesh_clear 调用 0 次。

TO_MESH_CLEAR ERROR 优先级:
  to_mesh_clear 失败时，如果此前已有其他 ERROR 或 FAIL，to_mesh_clear ERROR 覆盖之前的判定。
  理由: 临时 mesh 泄漏是数据完整性错误，比 PASS/FAIL 更严重。
```

### 8.4 depsgraph 作用域

```text
决策: 每个 target 的 Ground Contact 检查恰好获取一次 depsgraph。

理由:
  — depsgraph 是场景级对象，每个 target 获取一次足够
  — 不跨 target 缓存避免了复杂的生命周期管理
  — 与 Material Assignment 的 scene.objects 物化模式一致（按需获取，局部缓存）
```

## 9. 多对象、空几何与非有限值

### 9.1 actual_lowest_z 聚合

```text
决策: actual_lowest_z = 所有有效 world-space 顶点的全局最小 Z 值。

聚合方式:
  — 跨所有 geometry scope MESH 对象的所有顶点
  — 只聚合 math.isfinite(world_z) == True 的值
  — 初始值 +inf，逐顶点更新
  — 最终值在所有对象遍历完成后确定
```

### 9.2 各场景行为

| 场景 | 行为 | 结果 | failure_code |
|---|---|---|---|
| geometry scope 无 MESH | 不获取 depsgraph | FAIL | NO_EVALUATED_GEOMETRY |
| 仅一个 MESH，正常 | 正常算法 | PASS 或 FAIL | GROUND_CONTACT_OUT_OF_TOLERANCE (如超出) |
| 多个 MESH，所有正常 | 取全局最小 Z | PASS 或 FAIL | 同上 |
| 同一对象重复到达 | identity 去重（已由 helper 保证） | 正常 | — |
| 某个 MESH 零顶点 | 标记 zero_vertex_found，跳过该对象 | FAIL | NO_EVALUATED_GEOMETRY |
| 所有 MESH 零顶点 | 全部跳过 | FAIL | NO_EVALUATED_GEOMETRY |
| 部分有效、部分零顶点 | 零顶点触发 FAIL | FAIL | NO_EVALUATED_GEOMETRY |
| to_mesh 返回 None | 不会发生 (Blender API 返回 Mesh 或抛异常) | ERROR (如异常) | TO_MESH |
| 部分顶点非有限、部分有限 | 非有限标记，跳过非有限顶点 | FAIL | NON_FINITE_EVALUATED_VERTEX_Z |
| 所有顶点非有限 | actual_lowest_z 保持 +inf | FAIL | NON_FINITE_EVALUATED_VERTEX_Z |

### 9.3 非有限值详细处理

```text
本地顶点坐标为 NaN:
  经 matrix_world 变换后 world_z 为 NaN
  → math.isfinite(world_z) == False
  → non_finite_found = True, 跳过此顶点

本地顶点坐标为 Infinity:
  经 matrix_world 变换后 world_z 为 Inf 或 -Inf
  → math.isfinite(world_z) == False
  → non_finite_found = True, 跳过此顶点

matrix_world 含 NaN 导致 world_z 为 NaN:
  → 同上

matrix_world 含 Inf 导致 world_z 为 Inf:
  → 同上

所有顶点非有限:
  → actual_lowest_z 保持 +inf
  → math.isfinite(actual_lowest_z) == False
  → FAIL (NON_FINITE_EVALUATED_VERTEX_Z)
```

## 10. PASS / FAIL / ERROR / NOT_CHECKED 完整矩阵

### 10.1 NOT_CHECKED

| 条件 | note |
|---|---|
| ground_contact 缺失 | GROUND_CONTACT_NOT_CONFIGURED |
| ground_contact: null | GROUND_CONTACT_NOT_CONFIGURED |
| ground_contact: {} | GROUND_CONTACT_NOT_CONFIGURED |
| ground_z: null 且 tolerance: null | GROUND_CONTACT_NOT_CONFIGURED |
| ROOT_OBJECT_NOT_FOUND | ROOT_OBJECT_NOT_FOUND |
| AMBIGUOUS_ROOT_OBJECT_NAME | AMBIGUOUS_ROOT_OBJECT_NAME |
| ROOT_OBJECT_TYPE_MISMATCH | ROOT_OBJECT_TYPE_MISMATCH |
| 已有 root 阶段为 ERROR | ROOT_LOOKUP_ERROR |
| root 不在目标 Scene | ROOT_OBJECT_NOT_FOUND |

NOT_CHECKED 时不得读取任何 bpy 属性。

### 10.2 PASS

| 条件 |
|---|
| geometry scope 非空 |
| 所有 MESH 至少一个顶点 |
| 所有 world-space Z 为有限值 |
| abs(actual_lowest_z - ground_z) <= ground_contact_tolerance |

### 10.3 FAIL

| 条件 | failure_code |
|---|---|
| abs(actual_lowest_z - ground_z) > ground_contact_tolerance | GROUND_CONTACT_OUT_OF_TOLERANCE |
| geometry scope 无 MESH 对象 | NO_EVALUATED_GEOMETRY |
| 任一 MESH 对象零顶点 | NO_EVALUATED_GEOMETRY |
| 所有 world-space Z 为有限值但 lowest_z 非有限 (不应发生) | NO_EVALUATED_GEOMETRY |
| 任一 world-space Z 非有限 (NaN/Inf) | NON_FINITE_EVALUATED_VERTEX_Z |

### 10.4 ERROR

| 条件 | operation |
|---|---|
| scene.objects 读取失败 | READ_SCENE_OBJECTS |
| root 对象名解析失败 | RESOLVE_ROOT_OBJECT |
| _collect_geometry_scope_objects 内部 READ_ROOT_CHILDREN 异常 | READ_ROOT_CHILDREN |
| _collect_geometry_scope_objects 内部 READ_DESCENDANT_CHILDREN 异常 | READ_DESCENDANT_CHILDREN |
| _collect_geometry_scope_objects 内部 READ_DESCENDANT_TYPE 异常 | READ_DESCENDANT_TYPE |
| depsgraph 获取失败 | GET_EVALUATED_DEPSGRAPH |
| evaluated_get 失败 | EVALUATED_GET |
| to_mesh 失败 | TO_MESH |
| to_mesh_clear 失败 | TO_MESH_CLEAR |
| matrix_world 读取失败 | READ_EVALUATED_MATRIX_WORLD |
| mesh.vertices 迭代/读取 vertex.co 失败 | READ_MESH_VERTICES |
| world-space 顶点坐标转换失败 | TRANSFORM_VERTEX_TO_WORLD_SPACE |

注意: `COMPUTE_LOWEST_Z`（有限值检查和最低 Z 聚合）是纯 Python 数值运算，无独立 bpy 调用，不产生独立 ERROR operation。非有限值产生 FAIL，不是 ERROR。

### 10.5 PASS/FAIL 方向

```text
对称容差: 上下两个方向使用相同的 abs(actual_lowest_z - ground_z) <= tolerance。

角色浮在 ground_z 上方 (actual_lowest_z > ground_z):
  absolute_error = actual_lowest_z - ground_z
  > tolerance → FAIL (GROUND_CONTACT_OUT_OF_TOLERANCE)

角色穿入 ground_z 下方 (actual_lowest_z < ground_z):
  absolute_error = ground_z - actual_lowest_z
  > tolerance → FAIL (GROUND_CONTACT_OUT_OF_TOLERANCE)

tolerance == 0.0:
  absolute_error == 0.0 → PASS
  absolute_error > 0.0 → FAIL

不区分"悬空"和"穿地"为不同的 failure_code。两者都是超出容差。
```

## 11. 精确结果字典

### 11.1 NOT_CHECKED

```python
{
    "result": "NOT_CHECKED",
    "note": "<REASON>",
}
```

键集合: `{"result", "note"}`

note 取值:
- `"GROUND_CONTACT_NOT_CONFIGURED"`
- `"ROOT_OBJECT_NOT_FOUND"`
- `"AMBIGUOUS_ROOT_OBJECT_NAME"`
- `"ROOT_OBJECT_TYPE_MISMATCH"`
- `"ROOT_LOOKUP_ERROR"`

### 11.2 PASS

```python
{
    "result": "PASS",
    "ground_z": <float>,
    "ground_contact_tolerance": <float>,
    "actual_lowest_z": <float>,
    "absolute_error": <float>,
    "evaluated_mesh_names": [<str>, ...],
}
```

键集合: `{"result", "ground_z", "ground_contact_tolerance", "actual_lowest_z", "absolute_error", "evaluated_mesh_names"}`

- `evaluated_mesh_names` 按 (casefold, name) 排序，与 geometry scope 对象收集顺序一致
- 所有数值均为有限 float

### 11.3 FAIL — GROUND_CONTACT_OUT_OF_TOLERANCE

```python
{
    "result": "FAIL",
    "failure_code": "GROUND_CONTACT_OUT_OF_TOLERANCE",
    "ground_z": <float>,
    "ground_contact_tolerance": <float>,
    "actual_lowest_z": <float>,
    "absolute_error": <float>,
    "evaluated_mesh_names": [<str>, ...],
}
```

键集合: `{"result", "failure_code", "ground_z", "ground_contact_tolerance", "actual_lowest_z", "absolute_error", "evaluated_mesh_names"}`

### 11.4 FAIL — NO_EVALUATED_GEOMETRY

```python
{
    "result": "FAIL",
    "failure_code": "NO_EVALUATED_GEOMETRY",
    "ground_z": <float>,
    "ground_contact_tolerance": <float>,
}
```

键集合: `{"result", "failure_code", "ground_z", "ground_contact_tolerance"}`

省略: `actual_lowest_z`, `absolute_error`, `evaluated_mesh_names`

### 11.5 FAIL — NON_FINITE_EVALUATED_VERTEX_Z

```python
{
    "result": "FAIL",
    "failure_code": "NON_FINITE_EVALUATED_VERTEX_Z",
    "ground_z": <float>,
    "ground_contact_tolerance": <float>,
    "evaluated_mesh_names": [<str>, ...],
}
```

键集合: `{"result", "failure_code", "ground_z", "ground_contact_tolerance", "evaluated_mesh_names"}`

省略: `actual_lowest_z`, `absolute_error`

理由: NON_FINITE 意味着 evaluated geometry 数据不可信，提供 actual_lowest_z 可能错误引导诊断。

### 11.6 ERROR

```python
{
    "result": "ERROR",
    "error_type": "GROUND_CONTACT_COMPUTATION_ERROR",
    "operation": "<OP>",
    "note": "<OP>_FAILED",
}
```

键集合: `{"result", "error_type", "operation", "note"}`

省略: 所有正常结果字段 (ground_z, tolerance, actual_lowest_z, absolute_error, evaluated_mesh_names, failure_code)

### 11.7 键集合摘要

| 状态 | 必有键 | 键数量 |
|---|---|---|
| NOT_CHECKED | result, note | 2 |
| PASS | result, ground_z, ground_contact_tolerance, actual_lowest_z, absolute_error, evaluated_mesh_names | 6 |
| FAIL (TOLERANCE) | result, failure_code, ground_z, ground_contact_tolerance, actual_lowest_z, absolute_error, evaluated_mesh_names | 7 |
| FAIL (NO_GEOM) | result, failure_code, ground_z, ground_contact_tolerance | 4 |
| FAIL (NON_FINITE) | result, failure_code, ground_z, ground_contact_tolerance, evaluated_mesh_names | 5 |
| ERROR | result, error_type, operation, note | 4 |

每种状态的键集合唯一。不得出现可选字段（同一状态有时有、有时没有某键）。如果一种 FAIL sub-type 有不同于另一种的键集合，它们是不同的结果字典形式。

## 12. Failure Code 封闭集合

```text
GROUND_CONTACT_OUT_OF_TOLERANCE
  — abs(actual_lowest_z - ground_z) > ground_contact_tolerance
  — 包含悬空和穿地两种情况
  — 对称容差

NO_EVALUATED_GEOMETRY
  — geometry scope 中无 MESH 对象
  — geometry scope 中所有 MESH 对象均为零顶点
  — 复用 R2 §4.3 已定义 code

NON_FINITE_EVALUATED_VERTEX_Z
  — 任一 world-space 顶点 Z 坐标为 NaN 或 Infinity
  — 覆盖本地坐标非有限、matrix_world 导致的非有限
```

封闭: 共 3 个。不新增、不合并、不省略。

## 13. ERROR Type 和 Operation 枚举

### 13.1 error_type

```text
唯一 error_type: GROUND_CONTACT_COMPUTATION_ERROR
```

不区分不同 operation 的 error_type。与 Rotation (`ROTATION_COMPUTATION_ERROR`)、Material Assignment (`MATERIAL_ASSIGNMENT_COMPUTATION_ERROR`)、Animation State (`ANIMATION_STATE_COMPUTATION_ERROR`)、Collection Rules (`COLLECTION_RULES_COMPUTATION_ERROR`) 的命名约定一致。

### 13.2 Operation 封闭枚举

共 12 个 operation，分属三个阶段。

**Scene 物化 + Root 解析阶段：**

```text
READ_SCENE_OBJECTS
  — list(scene.objects) 异常
  — 场景级操作

RESOLVE_ROOT_OBJECT
  — scene.objects 遍历中 obj.name 读取异常
  — 场景级操作
```

**Geometry scope 对象收集阶段（由 _collect_geometry_scope_objects 抛出 RuntimeError）：**

```text
READ_ROOT_CHILDREN
  — list(root_obj.children) 异常
  — 对象级操作

READ_DESCENDANT_CHILDREN
  — list(descendant.children) 异常
  — 对象级操作

READ_DESCENDANT_TYPE
  — descendant.type 读取异常
  — 对象级操作
```

**Evaluated geometry 阶段：**

```text
GET_EVALUATED_DEPSGRAPH
  — bpy.context.evaluated_depsgraph_get() 异常
  — 场景级操作

EVALUATED_GET
  — obj.evaluated_get(depsgraph) 异常
  — 对象级操作

TO_MESH
  — evaluated.to_mesh() 异常
  — 对象级操作

TO_MESH_CLEAR
  — evaluated.to_mesh_clear() 异常
  — 对象级操作，在 finally 块中发生
  — 覆盖之前累积的 PASS/FAIL 结果

READ_EVALUATED_MATRIX_WORLD
  — evaluated.matrix_world 属性读取异常
  — 对象级操作

READ_MESH_VERTICES
  — len(mesh.vertices) 或 mesh.vertices 迭代或 vertex.co 读取异常
  — 对象级操作

TRANSFORM_VERTEX_TO_WORLD_SPACE
  — mw @ v.co 矩阵乘法异常
  — 或读取 world_co.z 异常
  — 顶点级操作
```

### 13.3 ERROR 字典嵌套

```text
嵌套路径: checks.ground_contact
  {
    "result": "ERROR",
    "error_type": "GROUND_CONTACT_COMPUTATION_ERROR",
    "operation": "<op>",
    "note": "<op>_FAILED",
  }

顶层 errors 收集:
  Ground Contact ERROR 在 _collect_target_errors 的固定位置收集，
  位于 rotation 之后、material_assignment 之前。

  收集格式:
    "GROUND_CONTACT_COMPUTATION_ERROR: target '<tid>' root_object_name '<rn>' operation '<op>'"

  不得重新排序、重写或改变其他已锁定字段的错误收集顺序。

  多个 target 按现有 per_target_results 顺序收集。
  Ground Contact 本身每个 target 最多产生一个 ERROR 消息
  （算法在第一个 ERROR 时立即返回）。
```

## 14. 缓存、调用次数与清理合同

### 14.1 缓存生命周期

| 值 | 缓存范围 | 生命周期 |
|---|---|---|
| ground_z, tolerance | 函数局部变量 | 单次 `_check_ground_contact` 调用 |
| scene_objects_ordered | 函数局部 | 单次调用 |
| scene_member_ids | 函数局部 | 单次调用 |
| scene_materialization_index | 函数局部 | 单次调用 |
| scene_name_by_id | 函数局部 | 单次调用 |
| root_obj | 函数局部 | 单次调用 |
| geometry scope objects | 函数局部 | 单次调用 |
| depsgraph | 函数局部 | 单次调用内 |
| evaluated object | 循环局部 | 单个 MESH 迭代 |
| to_mesh 结果 | 循环局部 | 单个 MESH 迭代 |
| matrix_world | 循环局部 | 单个 MESH 迭代 |
| actual_lowest_z | 函数局部 | 跨所有 MESH 聚合 |

不跨 target 缓存。不跨 check 缓存。不引入全局缓存。

### 14.2 异常后清理

```text
GUARANTEE:
  — to_mesh 成功后，to_mesh_clear 必然在 finally 中执行
  — to_mesh 失败时，不调用 to_mesh_clear（因为没有需要清理的临时 mesh）
  — evaluated_get 失败时，不调用 to_mesh 或 to_mesh_clear
  — depsgraph 获取失败时，不访问任何 evaluated 对象
  — scene.objects / RESOLVE_ROOT_OBJECT 失败时，不获取 depsgraph
  — 无论 Ground Contact 结果是 PASS/FAIL/ERROR/NOT_CHECKED，清理完全
```

## 15. 集成位置与 overall / errors / exit code

### 15.1 blender_scene_reader.py

```text
新增函数: _check_ground_contact(scene, target, per_target_result)
  — 位于文件后半部分，在 _check_collection_membership 之后
  — 遵循与 _check_material_assignment 相同的签名约定
  — 自行读取已有 per_target_result["checks"]["object_exists"] 和 ["object_type"]
  — 自行物化 scene.objects 并解析 root

修改函数: open_blend_and_get_scene
  — 在 per-target 循环中，在 Material Assignment 和 Collection Rules 之间调用
  — gc_result = _check_ground_contact(scene, target, target_result)
  — target_result["checks"]["ground_contact"] = gc_result
  — 顺序: animation_state → material_assignment → ground_contact → collection_rules → overall

MUST_NOT_MODIFY:
  — _check_root_objects: 不在其中添加任何 ground_contact 分支
```

### 15.2 asset_scene_preflight_check.py

```text
新增函数: _validate_ground_contact_rules_preopen(targets)
  — 在 _validate_and_open_spec 中调用，位于 rotation validation 之后
  — 验证 all-or-nothing: 若恰好一个子字段为非 None → INPUT ERROR
  — 返回按 casefold 排序的错误消息列表

修改函数: _collect_target_errors
  — 添加 ground_contact ERROR 收集，位于 rotation ERROR 之后、material_assignment 之前:
    gc = checks.get("ground_contact", {})
    if gc.get("result") == "ERROR":
        op = gc.get("operation", "UNKNOWN")
        err_msgs.append(
            f"GROUND_CONTACT_COMPUTATION_ERROR: target '{tid}' "
            f"root_object_name '{rn}' operation '{op}'"
        )
  — 不改变 rotation、material_assignment 或其他已锁定字段的错误收集代码和顺序

修改函数: _validate_and_open_spec
  — 在 pre-open validation 序列中添加:
    gc_errs = _validate_ground_contact_rules_preopen(targets)
    pre_open_errs.extend(gc_errs)

顶层 errors:
  — GROUND_CONTACT_COMPUTATION_ERROR 与其他 ERROR 一起
  — 通过 _collect_target_errors → err_msgs → build_error_result
  — 最终进入 input_errors
```

### 15.3 调用顺序

```text
open_blend_and_get_scene 内 per-target 循环:
  1. animation_state      (_check_animation_state)
  2. material_assignment  (_check_material_assignment)
  3. ground_contact       (_check_ground_contact)       ← NEW
  4. collection_membership (_check_collection_membership)
  5. overall              (_recompute_target_overall)

_recompute_target_overall 自动包含 ground_contact.result:
  sub_results.append(checks["ground_contact"]["result"])
  → ERROR > FAIL > PASS > NOT_CHECKED
```

### 15.4 退出码

```text
Ground Contact PASS  → 不影响整体 exit code
Ground Contact FAIL  → 至少一个 target FAIL → exit 1 (EXIT_FAIL)
Ground Contact ERROR → exit 2 (EXIT_ERROR)
Ground Contact NOT_CHECKED → 不影响
```

## 16. 确定性与副作用边界

### 16.1 确定性保证

```text
D-01: 同一 .blend + 同一 spec → 相同 actual_lowest_z (逐位一致)
D-02: geometry scope 对象顺序确定 (name casefold + materialization index)
D-03: 顶点遍历顺序由 Blender mesh.vertices 顺序确定 (稳定)
D-04: actual_lowest_z 从 +inf 单调递减，对顶点遍历顺序不敏感
D-05: 输出 JSON 经 canonicalize_phase3_result 排序
```

### 16.2 副作用边界 — 禁止操作

```text
MUST NOT:
  — 修改任何对象的 transform (location, rotation_euler, rotation_quaternion, scale)
  — 修改 parent / children 关系
  — 修改 collection membership
  — 修改 hide_viewport / hide_render / hide_get 状态
  — 修改 material / material_slots
  — 修改 mesh datablock (vertices, edges, faces)
  — 调用 bpy.ops.wm.save_as_mainfile 或任何保存操作
  — 渲染 (bpy.ops.render.render 等)
  — 切换场景 (bpy.context.scene = ...)
  — 改变 current frame (scene.frame_current = ...)
  — 改变 active object
  — 调用具有场景副作用的 bpy.ops
  — 修改 render settings
  — 修改 scene camera
```

### 16.3 临时数据清理

```text
to_mesh 产生的临时 Mesh:
  — 每个成功调用 to_mesh() 的 MESH 对象，to_mesh_clear() 在 finally 中执行
  — to_mesh 未成功时不调用 to_mesh_clear
  — 不保留临时 Mesh 引用
  — 函数返回时所有临时 evaluated mesh 已清理

depsgraph:
  — 不持有跨调用引用
  — 函数返回时局部变量自然释放
```

## 17. 测试矩阵

### 17.1 生产实现测试

与 `GROUND_CONTACT_IMPLEMENTATION` 任务对应的最小必要测试。

```
配置与 NOT_CHECKED:
  1. ground_contact 缺失 → NOT_CHECKED, note=GROUND_CONTACT_NOT_CONFIGURED
  2. ground_contact: None → NOT_CHECKED, note=GROUND_CONTACT_NOT_CONFIGURED
  3. ground_contact: {} → NOT_CHECKED, note=GROUND_CONTACT_NOT_CONFIGURED
  4. ground_z: None, tolerance: None → NOT_CHECKED, note=GROUND_CONTACT_NOT_CONFIGURED

Pre-open 部分配置 ERROR:
  5. ground_z present, tolerance absent → pre-open INPUT ERROR
  6. ground_z present, tolerance: None → pre-open INPUT ERROR
  7. ground_z absent, tolerance present → pre-open INPUT ERROR
  8. ground_z: None, tolerance present → pre-open INPUT ERROR
  9. pre-open ERROR message 精确格式
  10. 多 target 错误按 target_id casefold 排序

完整配置:
  11. both present (finite) → 检查启用 (pre-open 不报错)
  12. tolerance: 0.0 → 合法，不报错

Root 前置条件:
  13. root not found → NOT_CHECKED (ROOT_OBJECT_NOT_FOUND)
  14. root ambiguous → NOT_CHECKED (AMBIGUOUS_ROOT_OBJECT_NAME)
  15. root type mismatch → NOT_CHECKED (ROOT_OBJECT_TYPE_MISMATCH)
  16. root lookup ERROR → NOT_CHECKED (ROOT_LOOKUP_ERROR)

Evaluated geometry 算法 (mock bpy):
  17. 单 MESH, 顶点在 ground_z 上 → PASS
  18. 单 MESH, 顶点在容差边界 (== tolerance) → PASS
  19. 单 MESH, 顶点在容差外 (> tolerance) → FAIL (OUT_OF_TOLERANCE)
  20. 单 MESH, 顶点低于 ground_z → FAIL (OUT_OF_TOLERANCE)
  21. 单 MESH, 0.0 tolerance, exact match → PASS
  22. 单 MESH, 0.0 tolerance, deviation → FAIL
  23. 两个 MESH, 取全局最低 Z → PASS/FAIL
  24. geometry scope 无 MESH → FAIL (NO_EVALUATED_GEOMETRY)
  25. MESH 零顶点 → FAIL (NO_EVALUATED_GEOMETRY)
  26. 顶点 NaN → FAIL (NON_FINITE_EVALUATED_VERTEX_Z)
  27. 顶点 Inf → FAIL (NON_FINITE_EVALUATED_VERTEX_Z)
  28. 混合 NaN 和正常顶点 → FAIL (NON_FINITE_EVALUATED_VERTEX_Z)

Scene 物化 + geometry scope ERROR:
  29. scene.objects 读取异常 → ERROR (READ_SCENE_OBJECTS)
  30. obj.name 读取异常 → ERROR (RESOLVE_ROOT_OBJECT)
  31. root_obj.children 读取异常 → ERROR (READ_ROOT_CHILDREN)
  32. descendant.children 读取异常 → ERROR (READ_DESCENDANT_CHILDREN)
  33. descendant.type 读取异常 → ERROR (READ_DESCENDANT_TYPE)

Evaluated geometry ERROR:
  34. depsgraph 异常 → ERROR (GET_EVALUATED_DEPSGRAPH)
  35. evaluated_get 异常 → ERROR (EVALUATED_GET)
  36. to_mesh 异常 → ERROR (TO_MESH)
  37. to_mesh_clear 异常 → ERROR (TO_MESH_CLEAR)
  38. matrix_world 读取异常 → ERROR (READ_EVALUATED_MATRIX_WORLD)
  39. mesh.vertices 读取异常 → ERROR (READ_MESH_VERTICES)
  40. world-space 转换异常 → ERROR (TRANSFORM_VERTEX_TO_WORLD_SPACE)

结果字典精确键集合:
  41. NOT_CHECKED
  42. PASS
  43. FAIL (TOLERANCE)
  44. FAIL (NO_GEOM)
  45. FAIL (NON_FINITE)
  46. ERROR

集成与独立性:
  47. Ground Contact FAIL 不影响其他 check 结果
  48. Ground Contact ERROR 使 target overall = ERROR
  49. gc PASS + other PASS → overall PASS
  50. gc FAIL + other PASS → overall FAIL
  51. gc ERROR + other PASS → overall ERROR
  52. _collect_target_errors 中 ground_contact 在 rotation 之后、material_assignment 之前
  53. to_mesh_clear 在 finally 中执行 (验证清理合同)
  54. to_mesh 未成功时不调用 to_mesh_clear (验证零次调用)
```

### 17.2 测试环境

```text
CPython + bpy mock:
  — 使用 unittest.mock 或 pytest monkeypatch
  — Mock bpy.context, bpy.data, scene.objects, object.evaluated_get, evaluated.to_mesh 等
  — 测试 pre-open 验证、NOT_CHECKED 语义、算法逻辑、PASS/FAIL 判定、ERROR 传播、清理合同
  — 不运行 Blender
```

## 18. Blender 5.1.2 验证矩阵

### 18.1 固定边界

```text
BLENDER_VERSION: 5.1.2
FACTORY_STARTUP: TRUE
REAL_PROJECT_BLEND_OPENED: FALSE
TEMP_BLEND_SAVED: FALSE
RENDER_EXECUTED: FALSE
JSON_MARKER_PROTOCOL: 与 Collection Rules I4B 和 Material Assignment I4B 格式一致
```

### 18.2 场景列表

```
Grounded:
  1. 单 Mesh, 顶点恰好在 ground_z (0.0 tolerance) → PASS
  2. 单 Mesh, 顶点在容差内但不等于 ground_z → PASS
  3. 单 Mesh, 顶点在容差边界 (== tolerance) → PASS

Ungrounded:
  4. 单 Mesh, 顶点在容差外 (> tolerance, 浮空) → FAIL (OUT_OF_TOLERANCE)
  5. 单 Mesh, 顶点在容差外 (< ground_z, 穿地) → FAIL (OUT_OF_TOLERANCE)

Transform:
  6. 父子变换: parent Z=0.5, child Mesh 顶点 Z=0 → PASS (world Z = 0.5)
  7. 对象平移: Mesh 向上平移 → FAIL
  8. 对象旋转: Mesh 绕 X 轴旋转 90°, 顶点最低点改变 → 根据实际 world Z
  9. 对象缩放: 统一 2x 缩放，顶点 Z 翻倍 → 根据实际 world Z
  10. 负缩放: -1x Z 缩放，顶点 Z 反转 → 根据实际 world Z

Multiple Meshes:
  11. 两个 descendant Mesh, 取全局最低点 → PASS/FAIL
  12. 三个 Mesh, 最低点来自第二个

Geometry Scope:
  13. SELF_MESH: root 为 MESH, 仅自身 → PASS/FAIL
  14. DESCENDANT_MESHES: root 为 EMPTY, 只检查后代 MESH → PASS/FAIL
  15. SELF_AND_DESCENDANT_MESHES: root 为 MESH + 后代 MESH

Edge cases:
  16. object outside Scene → 不包括在 geometry scope (被 Scene membership 过滤)
  17. modifier: Subdivision Surface → evaluated vertex 比原始更多，取最低

Cleanup:
  18. to_mesh_clear: 验证临时 mesh 已清理 (通过 Blender 内部状态或重复运行一致性)
```

### 18.3 Blender Runner 格式

```text
Runner 文件: protocol_guard/phase3_min/tests/blender_ground_contact_runner.py

协议:
  — --factory-startup
  — 创建临时场景、对象和 mesh
  — 对每个 scenario 运行 _check_ground_contact 或等效调用
  — 输出 JSON marker: PHASE3_GC_RESULT_JSON=<results>
  — stdout exit: 0

Pytest 文件: protocol_guard/phase3_min/tests/test_asset_scene_preflight_ground_contact_blender.py
  — frozen independent expected dict
  — actual == expected 精确比较
  — subprocess 调用 Blender
```

## 19. 最小 Scope Guard

### 19.1 保护目标

Ground Contact Scope Guard 只保护以下核心合同：

```text
SG-01: 必须使用 evaluated geometry (bpy.context.evaluated_depsgraph_get)
SG-02: 必须使用 evaluated.matrix_world (不是 root_obj.matrix_world)
SG-03: 必须对每个 MESH 调用 evaluated_get
SG-04: 必须调用 to_mesh_clear (在 finally 中，且仅对成功 to_mesh 的对象)
SG-05: 不得使用 object.bound_box 作为 Ground Contact 几何源
SG-06: 不得使用原始 mesh 顶点坐标（未经 matrix_world 变换）
```

### 19.2 排除范围

```text
Scope Guard 不是通用 Python 静态分析器。不追求:
  — 任意递归
  — 完整函数对象传播
  — 完整返回值数据流
  — 通用变量名语义分析
  — 跨模块调用图
```

### 19.3 安排

```text
Scope Guard 不是默认实施步骤。

只有生产实现完成后能够证明存在高概率误改风险时，
才允许单独提议 GROUND_CONTACT_SCOPE_GUARD 任务。

否则: DEFERRED_NON_BLOCKING_ITEM
```

## 20. 精简实施任务拆分

### 20.1 总原则

```text
— 默认优先生产实现和必要测试
— 不默认生成完整报告、ZIP、Manifest、SHA256 清单
— 不默认创建独立证据包
— 每个任务只修改授权文件
```

### 20.2 GROUND_CONTACT_IMPLEMENTATION

一个主要生产实现任务，一次完成全部生产代码和最小必要测试。

```text
任务目标:
  完成 Ground Contact 全部生产代码和直接相关的最小必要 CPython 测试。

生产代码:
  blender_scene_reader.py:
    — 新增 _check_ground_contact(scene, target, per_target_result)
      包含: pre-open 之后到达的配置解析、root 前置读取、scene.objects 物化、
      root 解析、geometry scope 对象收集、evaluated geometry 算法、
      PASS/FAIL/ERROR/NOT_CHECKED 全部分支、to_mesh_clear 清理
    — 修改 open_blend_and_get_scene: 在 per-target 循环中添加调用

  asset_scene_preflight_check.py:
    — 新增 _validate_ground_contact_rules_preopen
    — 修改 _validate_and_open_spec: 添加 pre-open 调用
    — 修改 _collect_target_errors: 添加 ground_contact ERROR 收集

MUST_NOT_MODIFY:
  — _check_root_objects (任何分支均不添加 ground_contact 键)
  — 14A Core schema
  — 所有已锁定生产代码和测试

必要验证:
  — pytest: 最少 54 项 CPython tests (§17 矩阵)
  — 0 failed, exit 0

明确不做什么:
  — 不运行 Blender
  — 不创建 Scope Guard
  — 不创建 Blender runner
  — 不做真实 Blender 验证

生产进展: TRUE
退出条件: 所有测试通过，全部 12 个 ERROR operation、3 个 failure_code 和 6 种结果字典有测试覆盖
```

### 20.3 GROUND_CONTACT_BLENDER_VALIDATION

生产实现通过后，使用 Blender 5.1.2 临时场景验证。

```text
任务目标:
  在真实 Blender 5.1.2 中验证 Ground Contact 算法的端到端行为。

创建文件:
  protocol_guard/phase3_min/tests/blender_ground_contact_runner.py
  protocol_guard/phase3_min/tests/test_asset_scene_preflight_ground_contact_blender.py

允许修改文件:
  无生产文件修改

必要验证:
  — Blender runner: 18 scenarios, all passed
  — pytest: frozen independent expected 精确比较, 0 failed, exit 0
  — GROUND_CONTACT_IMPLEMENTATION 测试回归全部通过

固定边界:
  BLENDER_VERSION: 5.1.2
  FACTORY_STARTUP: TRUE
  REAL_PROJECT_BLEND_OPENED: FALSE
  BLEND_FILES_SAVED: FALSE
  RENDER_EXECUTED: FALSE

明确不做什么:
  — 不打开真实项目 .blend
  — 不修改生产代码
  — 不修改已锁定测试

生产进展: FALSE (验证任务)
退出条件: 所有 scenarios 通过，pytest 全部通过
```

### 20.4 GROUND_CONTACT_FINAL_REGRESSION

```text
任务目标:
  运行 Ground Contact 完整测试集，确认无回归。

必要验证:
  — Ground Contact 聚焦: 所有实施+Blender测试, 0 failed, exit 0
  — 14A Core 回归: 139 tests, 0 failed, exit 0
  — 完整 protocol_guard 回归: 需用户明确授权

允许修改文件:
  无 (纯验证)

完整回归授权:
  需用户本轮明确授权
  未授权时: REGRESSION_EXECUTED: NOT_AUTHORIZED

生产进展: FALSE
退出条件: 聚焦测试通过，完整回归通过（如授权）
```

### 20.5 GROUND_CONTACT_SCOPE_GUARD

```text
不列入默认实施步骤。

触发条件:
  仅在 GROUND_CONTACT_IMPLEMENTATION 完成后，
  能够证明核心 evaluated geometry 合同存在高概率误改风险时，
  才允许单独提议此任务。

否则: DEFERRED_NON_BLOCKING_ITEM
```

## 21. 已锁定内容保护清单

```text
MUST_NOT_MODIFY:
  — 14A Core schema (asset_scene_preflight_core.py)
  — _check_root_objects (任何分支均不得添加 ground_contact 键)
  — _check_root_objects 的 signature 和调用约定
  — Hierarchy, Standing, Facing, Visibility, Rotation, Animation State 的生产代码
  — Material Assignment 的生产代码
  — Collection Rules 的生产代码
  — 已锁定字段组的测试文件
  — 已锁定设计文档和锁定记录
  — PROJECT_CODEIFICATION_MASTER_MAP.md
  — CLAUDE.md
  — Phase 2 协议文件

MAY_MODIFY (需本轮授权):
  — blender_scene_reader.py: 新增 _check_ground_contact, 修改 open_blend_and_get_scene per-target 循环
  — asset_scene_preflight_check.py: 新增 pre-open validation, 修改 _collect_target_errors (仅在固定位置插入)

NEW_FILES (需本轮授权):
  — reviews/GROUND_CONTACT_DESIGN_R1.md (本轮已修改为 R2)
  — protocol_guard/phase3_min/tests/test_asset_scene_preflight_ground_contact.py (生产实现测试)
  — protocol_guard/phase3_min/tests/blender_ground_contact_runner.py (Blender runner)
  — protocol_guard/phase3_min/tests/test_asset_scene_preflight_ground_contact_blender.py (Blender pytest)
  — (条件) protocol_guard/phase3_min/tests/test_asset_scene_preflight_ground_contact_scope_guard.py
```

## 22. 设计完成条件

```text
DESIGN_COMPLETENESS:
  [x] 所有 16 个 DM 均已给出唯一决定
  [x] 所有配置组合均有定义
  [x] 所有 geometry scope 情况均有定义
  [x] 所有运行时状态均有唯一结果
  [x] 所有异常均有唯一 operation
  [x] 所有 FAIL 均有唯一 failure_code
  [x] 所有结果字典键集合唯一
  [x] 所有清理路径均有定义
  [x] 不存在"以后再决定"的实现语义
  [x] 不存在互相矛盾的章节
  [x] 不存在未经授权的 Schema 修改
  [x] 不存在 Ground Contact 之外的范围扩张
  [x] _check_root_objects 在 MUST_NOT_MODIFY 中，且不在 MAY_MODIFY 中
  [x] 所有 ERROR operation 与其伪代码 try/except 块一一对应
  [x] 配置规则表、伪代码和 pre-open 验证一致（部分配置 → INPUT ERROR）
  [x] to_mesh_clear 次数表达为条件式（仅 to_mesh 成功后执行）
  [x] 实施拆分为 3 个默认任务 + 1 个条件任务

TRUE_CONTRACT_CONFLICTS: 0
UNRESOLVED_DESIGN_DECISIONS: 0
TRUE_BLOCKING_ISSUES: 0

ALLOWED_DEFERRED_TO_IMPLEMENTATION:
  — 不影响外部合同的局部函数名
  — 纯内部代码布局
  — 不影响读取次数和异常边界的局部重构
```

## 23. Machine-readable Summary

```text
GROUND_CONTACT_DESIGN_VERSION: R2
GROUND_CONTACT_DESIGN_STATUS: FORMALLY_LOCKED
GROUND_CONTACT_DESIGN_AUTHORIZATION: USER_EXPLICITLY_AUTHORIZED
GROUND_CONTACT_IMPLEMENTATION_AUTHORIZED: FALSE

GROUND_CONTACT_CONFIG_MODEL: ALL_OR_NOTHING
GROUND_CONTACT_PRE_OPEN_VALIDATION: TRUE
GROUND_CONTACT_SCHEMA_NO_MODIFICATION: TRUE
GROUND_CONTACT_CHECK_ROOT_OBJECTS_MODIFIED: FALSE

GROUND_CONTACT_GEOMETRY_SOURCE: EVALUATED_DEPSGRAPH
GROUND_CONTACT_GEOMETRY_SCOPE_SOURCE: target.geometry_scope (REUSED)
GROUND_CONTACT_GEOMETRY_SCOPE_NEW_FIELD: FALSE

GROUND_CONTACT_ROOT_RESOLUTION:
  source: per_target_result.checks.object_exists + object_type (READ-ONLY)
  scene_objects_materialization: exactly once per check
  root_lookup: by name match against scene_name_by_id

GROUND_CONTACT_READ_COUNTS:
  scene.objects: 1 per target
  obj.name: 1 per scene object
  _collect_geometry_scope_objects: 1 per target
  depsgraph: 1 per target (if scope non-empty)
  evaluated_get: 1 per MESH in scope
  to_mesh: 1 per MESH in scope
  matrix_world: 1 per successful to_mesh
  mesh.vertices: 1 iteration per successful to_mesh
  to_mesh_clear: 1 per successful to_mesh (finally), 0 otherwise

GROUND_CONTACT_ERROR_TYPE: GROUND_CONTACT_COMPUTATION_ERROR
GROUND_CONTACT_OPERATION_COUNT: 12

GROUND_CONTACT_OPERATIONS:
  Scene/Root: READ_SCENE_OBJECTS, RESOLVE_ROOT_OBJECT
  Geometry Scope: READ_ROOT_CHILDREN, READ_DESCENDANT_CHILDREN, READ_DESCENDANT_TYPE
  Evaluated: GET_EVALUATED_DEPSGRAPH, EVALUATED_GET, TO_MESH, TO_MESH_CLEAR,
             READ_EVALUATED_MATRIX_WORLD, READ_MESH_VERTICES, TRANSFORM_VERTEX_TO_WORLD_SPACE

GROUND_CONTACT_FAILURE_CODES:
  GROUND_CONTACT_OUT_OF_TOLERANCE
  NO_EVALUATED_GEOMETRY
  NON_FINITE_EVALUATED_VERTEX_Z

GROUND_CONTACT_RESULT_DICT_STATES:
  NOT_CHECKED: 1 form (2 keys)
  PASS: 1 form (6 keys)
  FAIL: 3 forms (4, 5, 7 keys)
  ERROR: 1 form (4 keys)

GROUND_CONTACT_TOLERANCE: SYMMETRIC
GROUND_CONTACT_COMPARISON: abs(actual_lowest_z - ground_z) <= ground_contact_tolerance

GROUND_CONTACT_IMPLEMENTATION_SPLIT:
  GROUND_CONTACT_IMPLEMENTATION: 1 production task (~54 CPython tests)
  GROUND_CONTACT_BLENDER_VALIDATION: real Blender 5.1.2 (18 scenarios)
  GROUND_CONTACT_FINAL_REGRESSION: focused + full regression
  GROUND_CONTACT_SCOPE_GUARD: DEFERRED_NON_BLOCKING_ITEM (conditional only)

GROUND_CONTACT_LEAN_PRODUCTION:
  DEFAULT_NO_REPORT: TRUE
  DEFAULT_NO_ZIP: TRUE
  DEFAULT_NO_MANIFEST: TRUE
  DEFAULT_NO_SHA256: TRUE
  DIRECT_UPLOAD: TRUE

GROUND_CONTACT_CANONICAL_REFERENCE_FIELD_GROUPS:
  ROTATION_DESIGN_R3: result structure, ERROR mapping, read count convention
  MATERIAL_ASSIGNMENT_DESIGN_R1: geometry scope reuse, per-target integration
  ANIMATION_STATE_DESIGN_R5: independent per-target check integration

GROUND_CONTACT_NEXT_RECOMMENDED_TASK: GROUND_CONTACT_IMPLEMENTATION (requires user authorization)
```

## 24. DM-to-Decision Cross-Reference

| DM | 问题 | 决定章节 |
|----|------|---------|
| DM-01 | ground_z 缺失时的行为和结果 | §6.2 #6: pre-open INPUT ERROR |
| DM-02 | tolerance 缺失时的行为和结果 | §6.2 #7: pre-open INPUT ERROR |
| DM-03 | 只有 ground_z: 检查是否启用 | §6.2 #6: pre-open INPUT ERROR |
| DM-04 | 只有 tolerance: 检查是否启用 | §6.2 #7: pre-open INPUT ERROR |
| DM-05 | 两个字段都为 absent/null | §6.2 #1-4: NOT_CHECKED |
| DM-06 | geometry_scope 来源 | §7.2: 复用 target.geometry_scope |
| DM-07 | 检查范围: 只 MESH / 所有对象 | §7.3-7.4: 只 MESH, 通过 helper 过滤 |
| DM-08 | 多个 MESH 的聚合方式 | §9.1: 全局最小 world-space Z |
| DM-09 | PASS/FAIL/ERROR/NOT_CHECKED 完整矩阵 | §10 |
| DM-10 | 结果字典精确键集合 | §11 |
| DM-11 | failure_code 命名 | §12: 3 codes |
| DM-12 | ERROR type 和 operation 枚举 | §13: 1 error_type, 12 operations |
| DM-13 | 属性读取次数和缓存合同 | §14 |
| DM-14 | Scope Guard 合同 | §19 |
| DM-15 | Blender 5.1.2 临时场景验证矩阵 | §18 |
| DM-16 | 实施阶段拆分 | §20 |

```text
DM_RESOLVED: 16 of 16
DM_UNRESOLVED: 0
```
