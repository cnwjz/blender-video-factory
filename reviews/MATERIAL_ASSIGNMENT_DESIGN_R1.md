# Material Assignment Runtime Design R1

```text
DOCUMENT_ID: MATERIAL_ASSIGNMENT_DESIGN
DESIGN_VERSION: R1
TASK_ID: MATERIAL_ASSIGNMENT_DESIGN
MASTER_MAP_VERSION: R62
DATE: 2026-07-24
DESIGN_STATUS: COMPLETED_PENDING_INDEPENDENT_CHECK
FORMALLY_LOCKED: FALSE
IMPLEMENTATION_AUTHORIZED: FALSE
```

## 1. 权威来源与优先级

```text
PRIORITY_1: Blender_固定资产模板路线_新对话交接文档_v4.md
  — AUTHORITATIVE_REQUIREMENT: "材质没有丢失" (§九.7.7), "材质不丢失" (§十四.1.6)

PRIORITY_2: ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md §8
  — AUTHORITATIVE_REQUIREMENT: slot count >= 1, slot.material is not None, 排除纹理/Image/Shader/外观

PRIORITY_3: PHASE_3_MINIMUM_DESIGN_SPEC_R1.md
  — DESIGN_DRAFT: global.require_no_missing_materials 作为示例 JSON 字段 (§5.2)

PRIORITY_4: asset_scene_preflight_core.py lines 361-367
  — LOCKED_SCHEMA: target.material_assignment.require_material_assignment_presence (optional bool)

PRIORITY_5: PROJECT_CODEIFICATION_MASTER_MAP.md R62
  — CURRENT_STATE: DESIGN_AUTHORIZED_NOT_STARTED

PRIORITY_6: CLAUDE.md
  — PROJECT_RULES

DESIGN_INPUT:
  — MATERIAL_ASSIGNMENT_ORIGINAL_REQUIREMENT_AUDIT_REPORT.md (R2 Correction)
    AUDIT_RESULT: REQUIREMENTS_SUFFICIENT_FOR_DESIGN, CONTRACT_CONFLICTS: 0,
    DESIGN_FREEDOMS: 12, DOCUMENTATION_GAPS: 6

REFERENCE_CONVENTION:
  — ROTATION_DESIGN_R3.md (result structure, ERROR mapping, read count table conventions)
  — ANIMATION_STATE_DESIGN_R5.md (independent per-target check integration, scope guard conventions)
```

## 2. 固定范围和明确排除项

```text
FIXED_SCOPE:
  — 配置字段: target.material_assignment.require_material_assignment_presence (optional bool)
  — geometry_scope 字段: target.geometry_scope (必填，14A Core 已验证)
  — 结果字段名: material_assignment_presence_check
  — 最低检查: geometry scope 内每个 MESH 至少 1 个 material slot, 每个 slot.material 非 None

EXPLICITLY_EXCLUDED:
  — 贴图文件存在性
  — Image datablock 加载状态
  — Shader Node 连接正确性
  — 材质视觉外观
  — 渲染结果
  — Kenney 原生材质风格的视觉判断 (HUMAN_JUDGMENT_ONLY)
  — 保存重开后的材质持久化验证 (见 §17)

MUST_NOT_MODIFY:
  — 14A Core schema (asset_scene_preflight_core.py)
  — _check_root_objects 的返回结构
  — Hierarchy, Standing, Facing, Visibility, Rotation, Animation State 的生产代码和测试
  — 任何已锁定设计或锁定记录
  — global_rules 验证逻辑
```

## 3. 配置字段及运行时语义

```text
FIELD_PATH: target.material_assignment
TYPE: optional dict (None / absent = 不启用检查)
SUBFIELD: require_material_assignment_presence
SUBFIELD_TYPE: optional bool (None / absent / false / true)
```

### 3.1 运行时判定顺序

严格按以下优先级：

```text
Step 1: target.material_assignment 缺失或为 None
  → NOT_CHECKED
  → note: "MATERIAL_ASSIGNMENT_NOT_CONFIGURED"
  → 不读取任何 bpy 属性，不检查 root 前置条件
  → 返回

Step 2: material_assignment 为 dict（包括 {}）
  → 读取 require_material_assignment_presence 子字段
  → 缺失、None 或 false:
    → NOT_CHECKED
    → note: "REQUIREMENT_NOT_CONFIGURED"
    → 不读取任何 bpy 属性，不检查 root 前置条件
    → 返回
  → true:
    → 进入 Step 3

Step 3: require_material_assignment_presence 为 true
  → 检查 root 前置条件（见 §11）
  → root 前置不满足 → NOT_CHECKED（相应 note）
  → root 前置满足 → 执行材质检查
```

### 3.2 配置语义表

| 配置状态 | require_material_assignment_presence | 结果 | note |
|---|---|---|---|
| material_assignment 缺失 | N/A | NOT_CHECKED | MATERIAL_ASSIGNMENT_NOT_CONFIGURED |
| material_assignment: None | N/A | NOT_CHECKED | MATERIAL_ASSIGNMENT_NOT_CONFIGURED |
| material_assignment: {} | absent | NOT_CHECKED | REQUIREMENT_NOT_CONFIGURED |
| require_..._presence 缺失 | absent | NOT_CHECKED | REQUIREMENT_NOT_CONFIGURED |
| require_..._presence: None | None | NOT_CHECKED | REQUIREMENT_NOT_CONFIGURED |
| require_..._presence: false | false | NOT_CHECKED | REQUIREMENT_NOT_CONFIGURED |
| require_..._presence: true | true | 执行检查 | — |

### 3.3 require_material_assignment_presence 的 false 语义

`false` 与 absent/null 行为一致——不执行检查，输出 NOT_CHECKED。Schema 验证已在 14A Core 完成（非 dict 或子字段非 bool 且非 None 时报错）。

## 4. Legacy global 字段裁定

```text
FIELD: global.require_no_missing_materials (R1 Design Spec §5.2 示例)
STATUS: LEGACY_R1_EXAMPLE_NOT_VALIDATED_BY_CURRENT_SCHEMA_MAPPING_UNRESOLVED
RULING:
  — 该字段出现在 PHASE_3_MINIMUM_DESIGN_SPEC_R1.md 的示例 JSON 中，不是独立验收条款
  — 当前 14A Core schema 不显式验证该字段
  — R2 §8 以 "R1 Continuation" 开头但未显式引用或废弃该字段
  — 不构成 CONTRACT_CONFLICT
  — 本设计不依赖、不修改、不废弃该字段
```

## 5. geometry_scope 来源

```text
GEOMETRY_SCOPE_PATH: target.geometry_scope
  — target 级必填字段，14A Core 已验证为以下三者之一:
    SELF_MESH
    DESCENDANT_MESHES
    SELF_AND_DESCENDANT_MESHES
  — Material Assignment 直接使用 target["geometry_scope"]
  — 不从 material_assignment 块读取
  — 不设置默认值
  — 不根据 root type 或 hierarchy 自动推断
```

## 6. geometry_scope 对象收集算法

### 6.1 枚举定义

```text
SELF_MESH: 仅 root_obj 本身，且仅当 root_type_value == 'MESH' 时纳入
DESCENDANT_MESHES: root_obj 的所有递归后代中 type == 'MESH' 的 Scene member，不含 root_obj
SELF_AND_DESCENDANT_MESHES: SELF_MESH 与 DESCENDANT_MESHES 的并集
```

### 6.2 一次 Scene 物化

配置启用且 root 前置条件通过后，恰好一次读取 `scene.objects`：

```text
scene_objects_ordered = list(scene.objects)
  If raises → ERROR (operation: READ_SCENE_OBJECTS)

从 scene_objects_ordered 构建:
  scene_member_ids = {id(obj) for obj in scene_objects_ordered}
  scene_materialization_index = {id(obj): idx for idx, obj in enumerate(scene_objects_ordered)}
  scene_name_by_id = {}
```

### 6.3 Root 独立解析

```text
对 scene_objects_ordered 中每个 obj，最多读取一次 obj.name:
  If raises → ERROR (operation: RESOLVE_ROOT_OBJECT)
  写入 scene_name_by_id[id(obj)]

精确匹配 target["root_object_name"]（大小写敏感）：
  matches = [id for id, name in scene_name_by_id.items() if name == target["root_object_name"]
              and id in scene_member_ids]
  If len(matches) != 1 → ERROR (operation: RESOLVE_ROOT_OBJECT)

root_obj = scene_objects_ordered[...] (from match)
root_type_value = per_target_result["checks"]["object_type"]["actual"]
  (复用已锁定 root check 结果，不再次读取 root_obj.type)
```

### 6.4 对象收集 helper

```text
_collect_geometry_scope_objects(
    scene_objects_ordered,
    scene_member_ids,
    scene_materialization_index,
    scene_name_by_id,
    root_obj,
    root_type_value,
    geometry_scope_value,
)

该 helper:
  不得读取 scene.objects
  不得读取任何 obj.name（名称全部来自 scene_name_by_id）
  不得读取 root_obj.type（使用 root_type_value 参数）
  可读取: root_obj.children, descendant.children, descendant.type
```

### 6.5 算法

```
1. Compute root_mesh:
   If geometry_scope is SELF_MESH or SELF_AND_DESCENDANT_MESHES:
     If root_type_value == 'MESH' and id(root_obj) in scene_member_ids:
       root_mesh = [(root_obj, scene_name_by_id[id(root_obj)])]
     Else:
       root_mesh = []   (non-MESH root → empty)
   If geometry_scope is DESCENDANT_MESHES:
     root_mesh = []

2. If geometry_scope is SELF_MESH:
     Sort root_mesh by (name.casefold(), name, scene_materialization_index[id(obj)])
     Return root_mesh directly. Stop.

3. If geometry_scope is DESCENDANT_MESHES or SELF_AND_DESCENDANT_MESHES:
   a. Descendant traversal:
      visited_ids = {id(root_obj)}
      Read root_obj.children (at most once). If raises → ERROR (READ_ROOT_CHILDREN)
      Push all children onto stack.
      While stack not empty:
        child = stack.pop()
        if id(child) in visited_ids: continue   (cycle guard)
        visited_ids.add(id(child))
        if id(child) in scene_member_ids:
          cname = scene_name_by_id[id(child)]
          collected.append((child, cname))
        Push children of child onto stack (read child.children at most once per child;
        if raises → ERROR: READ_DESCENDANT_CHILDREN)
      Scene 外对象不加入结果，但遍历继续进入其 children
      （可能存在 Scene 内更深后代）

   b. For each (dobj, dname) in collected:
      Read dobj.type (at most once per object, cached by id)
      If raises → ERROR (READ_DESCENDANT_TYPE)
      If dobj.type == 'MESH': add to descendant_meshes

   c. If geometry_scope is SELF_AND_DESCENDANT_MESHES:
      if root_mesh non-empty and id(root_mesh[0][0]) in {id(o) for o, _ in descendant_meshes}:
          skip root_mesh
      result = root_mesh + descendant_meshes

   d. If geometry_scope is DESCENDANT_MESHES:
      result = descendant_meshes only

4. Sort result by (name.casefold(), name, scene_materialization_index[id(obj)])
   name from scene_name_by_id cache

5. Return result (list of (obj, name) tuples, deterministically ordered)
```

## 7. 材质槽读取算法

```
Algorithm: CheckMaterialPresence(mesh_objects)

Input:
  mesh_objects: list of (obj, name) tuples from CollectGeometryScopeObjects

Steps:
For each (mesh_obj, mesh_name) in mesh_objects:
  1. Read mesh_obj.material_slots:
     — 属性读取 + 完整列表物化 + len()
     — If raises → per_mesh: ERROR (operation: READ_MATERIAL_SLOTS, mesh_name: mesh_name,
       note: "READ_MATERIAL_SLOTS_FAILED")
     — Continue to next MESH

  2. If len(material_slots) == 0:
     per_mesh: FAIL (failure_code: MESH_HAS_NO_MATERIAL_SLOTS, mesh_name: mesh_name)
     Continue to next MESH

  3. for slot_index, slot in enumerate(material_slots):
     (material_slots 已在步骤 1 物化为普通 Python 列表，enumerate 不触发 bpy 读取)

     Read slot.material (at most once per slot):
       If raises → per_mesh: ERROR (operation: READ_SLOT_MATERIAL, mesh_name: mesh_name,
         slot_index: slot_index, note: "READ_SLOT_MATERIAL_FAILED")
       Continue to next MESH

     If slot.material is None:
       Record null_slot_index = slot_index
       Continue checking remaining slots

  4. After all slots:
     If ERROR from step 3: per_mesh result = ERROR
     If null_slot_indices non-empty:
       per_mesh: FAIL (failure_code: NULL_MATERIAL_SLOT, mesh_name: mesh_name,
                       null_slot_indices: [...])
     Else:
       per_mesh: PASS (mesh_name: mesh_name, slot_count: len(material_slots))

Aggregation:
  — Any per_mesh ERROR → overall ERROR
  — Else any per_mesh FAIL → overall FAIL
  — Else if mesh_objects empty → overall NOT_CHECKED (note: "NO_MESH_IN_GEOMETRY_SCOPE")
  — Else all PASS → overall PASS
```

## 8. 结果模型

### 8.1 NOT_CHECKED

```python
{"result": "NOT_CHECKED", "note": "MATERIAL_ASSIGNMENT_NOT_CONFIGURED"}
{"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"}
{"result": "NOT_CHECKED", "note": "ROOT_OBJECT_NOT_FOUND"}
{"result": "NOT_CHECKED", "note": "AMBIGUOUS_ROOT_OBJECT_NAME"}
{"result": "NOT_CHECKED", "note": "ROOT_OBJECT_TYPE_MISMATCH"}
{"result": "NOT_CHECKED", "note": "ROOT_LOOKUP_ERROR"}
{"result": "NOT_CHECKED", "note": "NO_MESH_IN_GEOMETRY_SCOPE"}
```

### 8.2 PASS

```python
{
    "result": "PASS",
    "per_mesh": [
        {"mesh_name": "body-mesh", "result": "PASS", "slot_count": 2},
        {"mesh_name": "head-mesh", "result": "PASS", "slot_count": 2},
    ]
}
```

### 8.3 FAIL

```python
{
    "result": "FAIL",
    "failure_code": "MATERIAL_ASSIGNMENT_FAILURE",
    "per_mesh": [
        {"mesh_name": "body-mesh", "result": "FAIL",
         "failure_code": "MESH_HAS_NO_MATERIAL_SLOTS"},
        {"mesh_name": "head-mesh", "result": "PASS", "slot_count": 1},
    ]
}
```

```python
{
    "result": "FAIL",
    "failure_code": "MATERIAL_ASSIGNMENT_FAILURE",
    "per_mesh": [
        {"mesh_name": "body-mesh", "result": "FAIL",
         "failure_code": "NULL_MATERIAL_SLOT", "null_slot_indices": [0]},
        {"mesh_name": "head-mesh", "result": "PASS", "slot_count": 1},
    ]
}
```

### 8.4 ERROR（geometry scope 阶段，无 per_mesh）

```python
{
    "result": "ERROR",
    "error_type": "MATERIAL_ASSIGNMENT_COMPUTATION_ERROR",
    "operation": "READ_SCENE_OBJECTS",
    "note": "READ_SCENE_OBJECTS_FAILED"
}
```

### 8.5 ERROR（材质槽阶段，含 per_mesh）

```python
{
    "result": "ERROR",
    "per_mesh": [
        {"mesh_name": "body-mesh", "result": "ERROR",
         "error_type": "MATERIAL_ASSIGNMENT_COMPUTATION_ERROR",
         "operation": "READ_MATERIAL_SLOTS",
         "note": "READ_MATERIAL_SLOTS_FAILED"},
        {"mesh_name": "head-mesh", "result": "PASS", "slot_count": 1},
    ]
}
```

```python
{
    "result": "ERROR",
    "per_mesh": [
        {"mesh_name": "body-mesh", "result": "ERROR",
         "error_type": "MATERIAL_ASSIGNMENT_COMPUTATION_ERROR",
         "operation": "READ_SLOT_MATERIAL",
         "note": "READ_SLOT_MATERIAL_FAILED",
         "slot_index": 2},
        {"mesh_name": "head-mesh", "result": "PASS", "slot_count": 1},
    ]
}
```

### 8.6 精确键集合

```text
PER_MESH_RESULT_KEYS:
  PASS:                          ["mesh_name", "result", "slot_count"]
  FAIL / MESH_HAS_NO_MATERIAL_SLOTS: ["mesh_name", "result", "failure_code"]
  FAIL / NULL_MATERIAL_SLOT:    ["mesh_name", "result", "failure_code", "null_slot_indices"]
  ERROR / READ_MATERIAL_SLOTS:   ["mesh_name", "result", "error_type", "operation", "note"]
  ERROR / READ_SLOT_MATERIAL:   ["mesh_name", "result", "error_type", "operation", "note", "slot_index"]

TOP_LEVEL_KEYS:
  NOT_CHECKED:              ["result", "note"]
  PASS:                     ["result", "per_mesh"]
  FAIL:                     ["result", "failure_code", "per_mesh"]
  ERROR (geometry scope):   ["result", "error_type", "operation", "note"]
  ERROR (per_mesh):         ["result", "per_mesh"]

SORTING:
  per_mesh 以 mesh_objects 输入顺序为准（§6.5 步骤 4 排序，不重新排序）
  null_slot_indices 按升序排列
```

## 9. failure code

```text
CLOSED_FAILURE_CODE_SET:

  MESH_HAS_NO_MATERIAL_SLOTS
    — 触发: len(material_slots) == 0
    — 位置: per_mesh FAIL

  NULL_MATERIAL_SLOT
    — 触发: 至少一个 slot.material is None
    — 位置: per_mesh FAIL
    — 附带: null_slot_indices (list of int, 升序)

  MATERIAL_ASSIGNMENT_FAILURE
    — 触发: 任意 per_mesh FAIL（整体聚合）
    — 位置: material_assignment_presence_check 顶层

MULTIPLE_FAILURES:
  — 每个 FAIL MESH 各自携带 failure_code
  — 顶层统一为 MATERIAL_ASSIGNMENT_FAILURE
  — per_mesh 以 mesh_objects 输入顺序为准
```

## 10. ERROR 合同

### 10.1 Error Type

```text
ERROR_TYPE: MATERIAL_ASSIGNMENT_COMPUTATION_ERROR (uniform)
```

### 10.2 Operation 集合（恰好 7 个）

| Operation | 包含的 bpy 操作 | 说明 |
|---|---|---|
| READ_SCENE_OBJECTS | scene.objects 属性读取 + 迭代 + 完整列表物化 | 构建 id set / index / name cache |
| RESOLVE_ROOT_OBJECT | scene_objects_ordered 中每个 obj.name 读取并缓存；精确匹配 target.root_object_name | 确认恰好一个匹配 |
| READ_ROOT_CHILDREN | root_obj.children 属性读取 + 完整列表物化 | descendant 遍历初始化 |
| READ_DESCENDANT_CHILDREN | descendant.children 属性读取 + 列表物化 | DFS 遍历扩展 |
| READ_DESCENDANT_TYPE | descendant.type 属性读取 | MESH 过滤 |
| READ_MATERIAL_SLOTS | mesh_obj.material_slots 属性读取 + 完整列表物化 + len() | 仅 _check_material_slots_for_mesh |
| READ_SLOT_MATERIAL | slot.material 属性读取 | 仅 _check_material_slots_for_mesh。包含 slot_index |

所有 ERROR note 固定为 `<OPERATION>_FAILED`。

### 10.3 短路

```text
GEOMETRY_SCOPE 阶段 ERROR:
  READ_SCENE_OBJECTS, RESOLVE_ROOT_OBJECT, READ_ROOT_CHILDREN,
  READ_DESCENDANT_CHILDREN, READ_DESCENDANT_TYPE
  → 整体结果为 ERROR（无 per_mesh），不检查任何 MESH

材质槽阶段 ERROR:
  READ_MATERIAL_SLOTS, READ_SLOT_MATERIAL
  → 局部 ERROR：仅该 MESH
  → 其他 MESH 继续检查
  → 至少一个 MESH ERROR → 整体 ERROR
```

### 10.4 顶层 ERROR 收集

```text
在 asset_scene_preflight_check.py _collect_target_errors 中:

geometry_scope 阶段 ERROR → 单条:
  "MATERIAL_ASSIGNMENT_COMPUTATION_ERROR: target '{tid}' material_assignment operation '{op}'"

材质槽阶段 ERROR → 按 per_mesh 逐条:
  "MATERIAL_ASSIGNMENT_COMPUTATION_ERROR: target '{tid}' material_assignment operation '{op}' mesh '{mesh_name}'"

消息按 (operation, mesh_name or "") 稳定排序
```

## 11. 属性读取次数

| 属性/操作 | 最大读取次数 | 说明 |
|---|---|---|
| scene.objects | 1 | 仅配置启用且 root 前置 PASS 时 (READ_SCENE_OBJECTS) |
| obj.name | 1 per scene member | 在 RESOLVE_ROOT_OBJECT 中统一读取并缓存到 scene_name_by_id |
| root_obj.type | 0 | 复用 per_target_result checks.object_type.actual |
| root_obj.children | 1 (仅 DESCENDANT_MESHES / SELF_AND_DESCENDANT_MESHES) | READ_ROOT_CHILDREN |
| descendant.children | 1 per visited descendant | READ_DESCENDANT_CHILDREN |
| descendant.type | 1 per scene member descendant | 按 id 缓存 (READ_DESCENDANT_TYPE) |
| mesh_obj.material_slots | 1 per MESH | 按 id 缓存 (READ_MATERIAL_SLOTS) |
| slot.material | 1 per slot | (READ_SLOT_MATERIAL) |

## 12. 缓存约定

```text
CACHE:
  — scene_name_by_id: RESOLVE_ROOT_OBJECT 时一次性构建，不再重复读取 obj.name
  — descendant type: dict[id(obj)] → type_str, 首次读取后缓存，异常不缓存
  — material_slots: dict[id(obj)] → slots_list, 首次读取后物化缓存，异常不缓存

NO_CACHE:
  — slot.material: 不跨 slot 缓存

READ_ONLY:
  — 不写入 bpy 属性，不修改 material_slots，不赋值 slot.material，不调用 bpy.ops
```

## 13. 前置条件和字段独立性

### 13.1 前置条件

只有配置启用（require_material_assignment_presence 为 true）后才评估：

```text
读取 per_target_result["checks"]:

object_exists.result == FAIL
  → NOT_CHECKED, note: "ROOT_OBJECT_NOT_FOUND"

object_exists.error_type == "AMBIGUOUS_ROOT_OBJECT_NAME"
  → NOT_CHECKED, note: "AMBIGUOUS_ROOT_OBJECT_NAME"

object_type.result == FAIL
  → NOT_CHECKED, note: "ROOT_OBJECT_TYPE_MISMATCH"

其他 object_exists / object_type 为非 PASS
  → NOT_CHECKED, note: "ROOT_LOOKUP_ERROR"

object_exists.result == PASS 且 object_type.result == PASS
  → 执行 Material Assignment
```

### 13.2 与其他字段组的独立性

```text
— 不依赖 Hierarchy / Standing / Facing / Visibility / Rotation / Animation State 的 PASS/FAIL
— 其他字段组 FAIL/ERROR 不阻止 Material Assignment
— Material Assignment ERROR 不阻止已完成的 root 检查和其他字段组结果
— 唯一阻断：root 无法定位（object_exists 或 object_type 非 PASS）
```

## 14. 生产集成

### 14.1 函数签名

```text
_check_material_assignment(scene, target, per_target_result)
  — 文件: protocol_guard/phase3_min/blender_scene_reader.py
  — scene: bpy.types.Scene（可能为 None）
  — target: 当前 target dict
  — per_target_result: _check_root_objects 已生成的纯 Python 结果
  — 输出: checks.material_assignment_presence_check 结果 dict

Helper:
  _collect_geometry_scope_objects(
    scene_objects_ordered, scene_member_ids, scene_materialization_index,
    scene_name_by_id, root_obj, root_type_value, geometry_scope_value)
  _check_material_slots_for_mesh(mesh_obj, mesh_name)
```

### 14.2 调用位置

在 `open_blend_and_get_scene()` 中，`_check_root_objects` 之后：

```python
if scene is not None:
    for i, target in enumerate(targets):
        target_result = per_target_results[i]

        as_result = _check_animation_state(scene, target)
        target_result["checks"]["animation_state"] = as_result

        ma_result = _check_material_assignment(
            scene,
            target,
            target_result,
        )
        target_result["checks"]["material_assignment_presence_check"] = ma_result

        target_result["overall"] = _recompute_target_overall(
            target_result["checks"]
        )
```

```text
scene is None:
  — 不进入 merge loop
  — 不调用 _check_animation_state / _check_material_assignment
  — per_target_results 保持空列表

不得在 _check_root_objects 函数内部调用 _check_material_assignment。
不得修改 _check_root_objects 的返回结构。
```

### 14.3 target overall

```text
material_assignment_presence_check.result 参与 _recompute_target_overall
checks 全部子键统一遍历: ERROR > FAIL > PASS
NOT_CHECKED 不提升 overall（等同于 PASS 对 overall 的影响）
```

## 15. AST Scope Guard 合同

```text
CORE_PROTECTED_ATTRIBUTES:
  obj.material_slots
  slot.material

唯一授权直接读取的函数:
  _check_material_slots_for_mesh

调用链:
  _check_material_assignment → _check_material_slots_for_mesh (每 MESH)
  _check_material_assignment → _collect_geometry_scope_objects
    (仅 scene.objects, obj.children, obj.type; 不读 material_slots/slot.material)

不得全局禁止已锁定函数使用 scene.objects / obj.name / obj.type / obj.children

FORBIDDEN_ALWAYS:
  写入 material_slots / slot.material
  getattr / setattr / delattr / hasattr 绕过
  别名 / lambda / 局部 helper / 顶层 helper / 动态字符串
  bpy.data 绕过
  不可达 helper 反例
```

## 16. CPython 测试矩阵

```text
I1 (配置语义 + geometry scope + PASS/FAIL/NOT_CHECKED):

Schema (继承现有):
  — material_assignment 缺失 → schema 接受
  — require_material_assignment_presence: true/false/null → schema 接受
  — require_material_assignment_presence: "not_bool" → schema ERROR

Configuration semantics:
  — 缺失 → MATERIAL_ASSIGNMENT_NOT_CONFIGURED
  — None → MATERIAL_ASSIGNMENT_NOT_CONFIGURED
  — {} → REQUIREMENT_NOT_CONFIGURED
  — false/null/absent → REQUIREMENT_NOT_CONFIGURED
  — true → 进入检查

Root preconditions:
  — object_exists FAIL → ROOT_OBJECT_NOT_FOUND
  — AMBIGUOUS_ROOT_OBJECT_NAME → AMBIGUOUS_ROOT_OBJECT_NAME
  — object_type FAIL → ROOT_OBJECT_TYPE_MISMATCH
  — 其他非 PASS → ROOT_LOOKUP_ERROR
  — PASS → 执行检查

geometry_scope:
  — SELF_MESH + MESH root → [root]
  — SELF_MESH + EMPTY root → []
  — DESCENDANT_MESHES → 递归收集
  — SELF_AND_DESCENDANT_MESHES + MESH root → root + descendants
  — SELF_AND_DESCENDANT_MESHES + EMPTY root → descendants only
  — identity 去重, 排序

slot check:
  — 2 slot 全部非 None → PASS
  — 0 slot → FAIL (MESH_HAS_NO_MATERIAL_SLOTS)
  — 1 slot None → FAIL (NULL_MATERIAL_SLOT)
  — 3 slot 第 1 个 None → FAIL
  — 混合 MESH → overall FAIL
  — 空 scope → NOT_CHECKED

Aggregation:
  — ALL PASS → PASS
  — ≥1 FAIL, 0 ERROR → FAIL
  — ≥1 ERROR → ERROR
  — 空 scope → NOT_CHECKED
```

## 17. ERROR 测试矩阵

```text
I2 (全部 7 个 ERROR operation + _collect_target_errors 注册):

  — scene.objects 异常 → READ_SCENE_OBJECTS (geometry scope ERROR, 无 per_mesh)
  — name 读取或 root 匹配异常 → RESOLVE_ROOT_OBJECT (geometry scope ERROR, 无 per_mesh)
  — 匹配数 ≠ 1 → RESOLVE_ROOT_OBJECT (geometry scope ERROR, 无 per_mesh)
  — root_obj.children 异常 → READ_ROOT_CHILDREN (geometry scope ERROR, 无 per_mesh)
  — descendant.children 异常 → READ_DESCENDANT_CHILDREN (geometry scope ERROR, 无 per_mesh)
  — descendant.type 异常 → READ_DESCENDANT_TYPE (geometry scope ERROR, 无 per_mesh)
  — material_slots 异常 → READ_MATERIAL_SLOTS (per_mesh ERROR)
  — slot.material 异常 → READ_SLOT_MATERIAL (per_mesh ERROR, 含 slot_index)
  — geometry scope ERROR × 局部 ERROR 短路
  — geometry scope ERROR 无 per_mesh
  — _collect_target_errors 消息格式 × 2 类
```

## 18. Blender 5.1.2 验证矩阵

```text
I4B: 临时 Blender 场景 (--factory-startup --background), 12 scenarios:

  — MESH no slots → FAIL
  — MESH 1 valid slot → PASS
  — MESH 1 None slot → FAIL
  — MESH 2 valid slots → PASS
  — MESH mixed valid + None → FAIL
  — EMPTY root + MESH child → DESCENDANT_MESHES → PASS
  — EMPTY → EMPTY child → MESH grandchild → correct filter
  — 3 geometry_scope values × 1 scenario each
  — Scene 外分支排除
  — 3 MESH mix (2 PASS 1 FAIL) → overall FAIL
  — material_assignment + standing + facing → 独立结果 + overall 聚合

PROHIBITED: 真实项目 .blend, 保存, 渲染, 视觉判断
```

## 19. 保存重开功能归属

```text
REQUIREMENT: "保存并重新打开后材质不丢失"
  SOURCE: V4 §十四.1.5-6, §十六 L1-D

RULING:
  — asset_scene_preflight_check 是只读检查器，运行在单次 Blender 会话中
  — 保存重开验证需要跨会话状态比较 → 需要两次独立 Blender 调用
  — 类比 R2 §7.1 DO-11 (DEFER_OUT_OF_MINIMAL_PHASE_3)
  — 类比 Animation State Design R5 (DEFER_REQUIRES_STATE)
  — 当前会话检查只证明内存中存在有效材质引用
  — 不能推断保存操作行为

FUNCTIONAL_OWNERSHIP:
  — 当前会话材质状态: asset_scene_preflight_check (本设计)
  — 保存重开持久化: DEFER_REQUIRES_STATE
```

## 20. I1–I4B–E 实施拆分

### I1: Config + Geometry Scope + PASS/FAIL/NOT_CHECKED

```text
TASK: MATERIAL_ASSIGNMENT_I1
PROVES: 配置语义, root 前置判定, 独立 root 解析, geometry scope, slot 检查, 聚合
PRODUCTION_FILE: blender_scene_reader.py
TEST_FILE: test_asset_scene_preflight_material_assignment_i1.py (新增, CPython)
NOT_IMPLEMENTING: ERROR branches, _collect_target_errors, Blender, scope guard
BLENDER_REQUIRED: FALSE
```

### I2: ERROR Branches + Error Collection

```text
TASK: MATERIAL_ASSIGNMENT_I2
PROVES: 全部 7 个 ERROR operation, 局部/全局短路, geometry scope ERROR vs per_mesh ERROR,
        _collect_target_errors 注册
PRODUCTION_FILE: blender_scene_reader.py
MODIFIED_FILE: asset_scene_preflight_check.py (_collect_target_errors 新增 material_assignment 分支)
TEST_FILE: test_asset_scene_preflight_material_assignment_i2.py (新增, CPython)
MINIMUM_TESTS: 19 (7 ops + 2 geometry ERROR structures + 3 short-circuit + 5 error collection + 2 message format)
NOT_IMPLEMENTING: Blender, scope guard, target overall 集成
BLENDER_REQUIRED: FALSE
```

### I3: Integration + target overall

```text
TASK: MATERIAL_ASSIGNMENT_I3
PROVES: open_blend_and_get_scene merge loop 集成, animation_state 后调用, 结果写入, overall 重算
PRODUCTION_FILE: blender_scene_reader.py (仅修改 open_blend_and_get_scene)
TEST_FILE: test_asset_scene_preflight_material_assignment_i3.py (新增, CPython)
NOT_IMPLEMENTING: Blender, scope guard
NOT_MODIFIED: _check_root_objects, asset_scene_preflight_check.py
BLENDER_REQUIRED: FALSE
```

### I4A: AST Scope Guard

```text
TASK: MATERIAL_ASSIGNMENT_I4A
PROVES: material_slots / slot.material 仅 _check_material_slots_for_mesh,
        正向/反向/对抗探针全部通过
PRODUCTION_FILE: NONE (生产代码冻结)
TEST_FILE: test_asset_scene_preflight_material_assignment_i4a_scope_guard.py (新增, CPython AST)
BLENDER_REQUIRED: FALSE
```

### I4B: Blender 5.1.2 Validation

```text
TASK: MATERIAL_ASSIGNMENT_I4B
PROVES: 12 Blender 场景全部正确
PRODUCTION_FILE: NONE
TEST_FILE: test_asset_scene_preflight_material_assignment_i4b_blender.py (新增)
RUNNER_FILE: blender_material_assignment_i4b_runner.py (新增)
BLENDER_REQUIRED: TRUE
FACTORY_STARTUP: TRUE
```

### E: Final Regression

```text
TASK: MATERIAL_ASSIGNMENT_E
PROVES: Material Assignment, 14A Core, full protocol_guard 全部通过
PRODUCTION_CODE_MODIFIED: FALSE
EXISTING_TESTS_MODIFIED: FALSE
BLENDER_REQUIRED: TRUE (I4B runner)
REAL_PROJECT_BLEND_OPENED: FALSE
```

## 21. 追踪矩阵

```text
AUTHORITATIVE_REQUIREMENT_01–06: → §3, §7, §9, §17
DESIGN_FREEDOM_01–12: 全部唯一裁定
DOCUMENTATION_GAP_01–06: 全部明确处理
CONTRACT_CONFLICT: 0
```

## 22. 明确未包含内容

```text
NOT_IN_THIS_DESIGN:
  — 材质内容验证 (贴图/Image/Shader)
  — 材质视觉质量 / 名称匹配 / slot 数量上限
  — global.require_no_missing_materials
  — 保存重开持久化验证
  — 跨场景材质一致性
  — 非 MESH 对象材质检查
  — Kenney 原生材质风格视觉判断
```

## 23. 设计自洽检查

```text
SEMANTIC_CLOSURE:
  [x] 配置缺失 → MATERIAL_ASSIGNMENT_NOT_CONFIGURED
  [x] 配置 {} → REQUIREMENT_NOT_CONFIGURED
  [x] require false → REQUIREMENT_NOT_CONFIGURED
  [x] require true + root missing → ROOT_OBJECT_NOT_FOUND
  [x] require true + root ambiguous → AMBIGUOUS_ROOT_OBJECT_NAME
  [x] require true + type mismatch → ROOT_OBJECT_TYPE_MISMATCH
  [x] require true + root PASS → 执行检查
  [x] scene.objects 异常 → READ_SCENE_OBJECTS
  [x] name 读取或 root 匹配异常 → RESOLVE_ROOT_OBJECT
  [x] root children 异常 → READ_ROOT_CHILDREN
  [x] descendant children 异常 → READ_DESCENDANT_CHILDREN
  [x] descendant type 异常 → READ_DESCENDANT_TYPE
  [x] material_slots 异常 → READ_MATERIAL_SLOTS
  [x] slot.material 异常 → READ_SLOT_MATERIAL
  [x] 3 geometry_scope values
  [x] 无 MESH → NOT_CHECKED
  [x] 0 slot / 空 slot / 混合 PASS/FAIL/ERROR
  [x] animation_state + material_assignment 共存
  [x] target overall 重算
  [x] 没有不可达 operation
  [x] 没有 READ_MATERIAL_SLOT
  [x] 没有 matched_obj 作为 open_blend 局部变量
  [x] operation 恰好 7 个
  [x] 所有 Markdown 围栏配对
  [x] 无 TBD
  [x] 无自身 SHA256
```
