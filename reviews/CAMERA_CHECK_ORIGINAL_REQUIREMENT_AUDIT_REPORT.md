# Camera Check Original Requirement Audit Report

**TASK_ID**: CAMERA_CHECK_ORIGINAL_REQUIREMENT_AUDIT
**TASK_TYPE**: ORIGINAL_REQUIREMENT_AUDIT
**MASTER_MAP_VERSION**: R77
**DATE**: 2026-07-26
**BASELINE_COMMIT**: d44679fc11c5069a17277395bb6c52b5a6dfc799
**CORRECTION**: R3 — 最终状态统一与 DF-14 分类修正

---

## 1. 任务身份与权威材料优先级

### 1.1 任务身份

```text
TASK_ID: CAMERA_CHECK_ORIGINAL_REQUIREMENT_AUDIT
TASK_TYPE: ORIGINAL_REQUIREMENT_AUDIT
MASTER_MAP_VERSION: R77
```

### 1.2 权威优先级

```text
1. 原始业务需求 — Blender 固定资产模板路线 新对话交接文档 v4
2. 当前锁定 Schema — asset_scene_preflight_core.py _validate_camera_check
3. 正式 Implementation Contract R2 — ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md
4. 当前生产代码真实状态 — blender_scene_reader.py / asset_scene_preflight_check.py
5. 正式设计规格 — PHASE_3_MINIMUM_DESIGN_SPEC_R1.md
6. 历史审计和覆盖率报告
```

### 1.3 审计结论

```text
AUDIT_STATUS: COMPLETED
AUDIT_RESULT: REQUIREMENTS_SUFFICIENT_FOR_DESIGN
AUDIT_COVERAGE_GAP_COUNT: 1
AUDIT_COVERAGE_GAP:
  R2 §10.1 引用的 R1 Section 19 原始文本无法获取
  — ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT.md (R1) 磁盘和 git 历史均不存在
```

R2 §10.1 引用 "R1 Section 19" 作为 Per-Target Camera Check 的保留合同。R1 Implementation Contract 文件在磁盘和 git 历史中均不存在，R2 §10.1 的一句摘要（"projection uses evaluated geometry bbox corners (not raw bound_box)"）是唯一可用的 R1 衍生信息。

该缺失源属于历史审计覆盖缺口。它不构成真实合同冲突。它不阻止 Camera Check 进入设计阶段。设计必须以当前原始需求（V4）、锁定 Schema 和 R2 正文为权威边界。不得凭空恢复或猜测 R1 Section 19 的内容。

R2 §4（Evaluated Geometry Contract）、§10.1（Per-Target Projection）、§10.2（Global Projection Groups）和 §10.3（Projection Limitations）为 Camera Check 提供了充分的合同基础。

---

## 2. 实际读取文件清单

| # | 路径 | 类型 | 存在 | 读取范围 |
|---|------|------|------|---------|
| 1 | `reviews/PROJECT_CODEIFICATION_MASTER_MAP.md` | 总地图 | YES | 全文 (R77) |
| 2 | `CLAUDE.md` | 项目规则 | YES | 全文 |
| 3 | `GLOBAL_CODEIFICATION_AUDIT_INPUTS/01_authoritative_requirements/Blender_固定资产模板路线_新对话交接文档_v4.md` | 原始需求 | YES | 全文 (1–1812 行) |
| 4 | `protocol_guard/phase3_min/asset_scene_preflight_core.py` | Schema 源码 | YES | _validate_camera_check (L390–408) + projection_groups 验证 (L223–274) |
| 5 | `protocol_guard/phase3_min/blender_scene_reader.py` | Reader 源码 | YES | 全文 (2761 行) — 确认无 _check_camera_check |
| 6 | `protocol_guard/phase3_min/asset_scene_preflight_check.py` | Entry 源码 | YES | 全文 (597 行) — 确认无 camera_check 专用 pre-open validator |
| 7 | `GLOBAL_CODEIFICATION_AUDIT_INPUTS/02_phase3_design/ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md` | 实现合同 R2 | YES | §4 Evaluated Geometry Contract + §10.1 Per-Target Projection + §10.2 Global Projection Groups + §10.3 Projection Limitations |
| 8 | `GLOBAL_CODEIFICATION_AUDIT_INPUTS/02_phase3_design/PHASE_3_MINIMUM_DESIGN_SPEC_R1.md` | 设计规格 R1 | YES | §5.2 Input schema + §5.3 Output schema (camera_visible 历史字段) |
| 9 | `reviews/GLOBAL_CODEIFICATION_AUDIT_REPORT.md` | 历史审计 | YES | 全文 |
| 10 | `reviews/POST_14B_3B_GLOBAL_REMAINING_REQUIREMENTS_AUDIT_R1_REPORT.md` | 历史审计 | YES | §3 camera_check SCHEMA_ONLY |
| 11 | `reviews/PHASE_3_CURRENT_IMPLEMENTATION_COVERAGE_AUDIT.md` | 覆盖率审计 | YES | §2.17 camera_check CORE_VALIDATION_ONLY |
| 12 | `protocol_guard/phase3_min/tests/test_asset_scene_preflight_core.py` | Schema 测试 | YES | camera_check + projection_groups 测试段 |
| — | `ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT.md` (R1) | 实现合同 R1 | **MISSING** | 磁盘和 git 历史均不存在 |

---

## 3. 原始业务需求及精确出处

### 3.1 V4 交接文档中的相机相关要求

**§十·1 核心工作模式**（行 744）：
> 使用 `world_to_camera_view` 完成数学投影与裁切检查

**§十·3 Claude Code 适合承担的任务**（行 766）：
> 通过 bbox 与 `world_to_camera_view` 计算摄像机构图

**§七·最高优先级流程修正**（行 502–538）：
> 角色层级 → 角色姿势 → Root 旋转 → 角色尺寸 → 地面接触 → 角色世界位置 → essential bbox → 摄像机目标 → 摄像机距离与焦距
> 在前六项通过前，禁止优先调整 ortho_scale、shift_y、camera distance、camera target

**§十二·首帧构图原则**（行 1044–1069）：
> 程序化通过条件：
> 1. essential objects 裁切数量 = 0
> 2. 所有人物完整进入安全区
> 3. 两个收银通道完整进入安全区
> 4. 顶部无意义空白不超过 15%
> 5. 底部无意义空白不超过 15%
> 6. 左右安全边距不低于 4%
> 7. 相机不进入任何 essential object 的 bbox

**§十五·L1-C 指令**（行 1269–1277）：
> 使用 bbox 与 world_to_camera_view 设置透视 3/4 斜俯视摄像机
> 程序化通过条件：essential objects 裁切数量为 0、所有人物完整进入安全区、顶部空白 ≤ 15%、底部空白 ≤ 15%、左右安全边距 ≥ 4%、相机不进入任何 essential object bbox

### 3.2 原始需求的权威分类

| ID | 需求内容 | 来源路径 | 来源段落 |
|----|---------|---------|---------|
| CR-01 | 使用 `world_to_camera_view` 完成数学投影与裁切检查 | 交接文档 v4 | §十·1 |
| CR-02 | 用 bbox 与投影计算摄像机构图 | 交接文档 v4 | §十·3 |
| CR-03 | essential objects 裁切数量为 0 | 交接文档 v4 | §十二·L1-C |
| CR-04 | 所有目标完整进入安全区 | 交接文档 v4 | §十二·L1-C |
| CR-05 | 顶部空白 ≤ 15%、底部空白 ≤ 15% | 交接文档 v4 | §十二·L1-C |
| CR-06 | 左右安全边距 ≥ 4% | 交接文档 v4 | §十二·L1-C |
| CR-07 | 相机不进入任何 essential object bbox | 交接文档 v4 | §十二·L1-C |
| CR-08 | 相机排查顺序：层级→姿势→旋转→尺寸→地面接触→位置→bbox→相机 | 交接文档 v4 | §七 |
| CR-09 | 禁止在前六项未通过时调整相机参数 | 交接文档 v4 | §七, §十·6 |

### 3.3 需求归属判定

CR-03（essential objects 裁切数量）和 CR-07（相机不进入 essential object bbox）涉及跨目标联合 bbox 和 essential objects 多对象概念。根据 R2 §10.2 的 Projection Groups 算法定义（"Aggregate all evaluated geometry world vertices from all targets listed in target_ids... Compute union world bbox"），多对象联合投影属于 Projection Groups 的专属范围。单目标 Camera Check 的几何范围仅限于 `target.geometry_scope`（由 R2 §4 合同链确定 — 见 §5.3 和 §10.1）。

CR-04（所有目标完整进入安全区）可以通过 per-target Camera Check + 全局投影组成果实现。"安全区" 概念对应 `required_screen_bbox`。

CR-05 和 CR-06（百分比边距约束）是可代码化的几何规则，R2 §10.3 明确确认："V4-41 (top/bottom empty ≤15%) and V4-42 (left/right margin ≥4%) are geometric rules codifiable via projection." 边界值必须来自 spec 的 `required_screen_bbox`，禁止硬编码百分比阈值。如何将百分比约束映射到 `required_screen_bbox` 的比较方向属于设计裁定（DF-14）。

CR-08 和 CR-09（相机排查顺序、禁止优先调整相机）属于 `DEFER_REQUIRES_STATE`（需要跨时间点的状态比较，Design Spec R1 §7.1 已明确排除）。

---

## 4. 当前 Schema 字段与验证语义

### 4.1 字段定义

来源：`protocol_guard/phase3_min/asset_scene_preflight_core.py` 第 390–408 行

```python
def _validate_camera_check(t, i, errs):
    cc = t.get("camera_check")
    if cc is None: return
    if not isinstance(cc, dict): errs.append(...); return
    if not isinstance(cc.get("camera_object_name"), str) or cc["camera_object_name"] == "":
        errs.append(...)
    mvc = cc.get("minimum_visible_projected_corner_count", -1)
    if isinstance(mvc, bool) or (not isinstance(mvc, int)) or mvc < 0:
        errs.append(...)
    rsb = cc.get("required_screen_bbox")
    if not isinstance(rsb, dict):
        errs.append(...)
    else:
        for k in ("min_left", "max_right", "min_bottom", "max_top"):
            v = rsb.get(k)
            if v is None or isinstance(v, bool) or not isinstance(v, (int, float)):
                errs.append(...)
            elif math.isnan(v) or math.isinf(v):
                errs.append(...)
```

### 4.2 字段语义矩阵

| 字段路径 | 类型 | 必填 | 空值行为 | Schema 约束 |
|---------|------|------|---------|------------|
| `camera_check` | object | 否 | None → 整个块跳过 | 必须是 dict |
| `camera_object_name` | string | 是（块存在时） | 空字符串 → ERROR | 非空字符串 |
| `minimum_visible_projected_corner_count` | integer | 是（块存在时） | 默认 -1 → ERROR | 非 bool 整数，≥ 0 |
| `required_screen_bbox` | object | 是（块存在时） | 非 dict → ERROR | 必须是对象 |
| `required_screen_bbox.min_left` | number | 是（块存在时） | None → ERROR | 有限数值，拒绝 bool |
| `required_screen_bbox.max_right` | number | 是（块存在时） | None → ERROR | 有限数值，拒绝 bool |
| `required_screen_bbox.min_bottom` | number | 是（块存在时） | None → ERROR | 有限数值，拒绝 bool |
| `required_screen_bbox.max_top` | number | 是（块存在时） | None → ERROR | 有限数值，拒绝 bool |

### 4.3 CURRENT_SCHEMA_FIELD_COUNT 计数口径

```text
叶子字段数量: 6

1. camera_object_name
2. minimum_visible_projected_corner_count
3. required_screen_bbox.min_left
4. required_screen_bbox.max_right
5. required_screen_bbox.min_bottom
6. required_screen_bbox.max_top

camera_check 和 required_screen_bbox 是容器节点，不计入叶子字段数量。
```

### 4.4 Schema 确认的关键行为

| 行为 | 结果 | 证据 |
|------|------|------|
| camera_check 缺失或 null | 整个块跳过，不报错 | `if cc is None: return` |
| camera_check 块存在时所有 6 个叶子字段必填 | 缺失任一 → ERROR | 各字段无 None 跳过逻辑 — 这是 CURRENT_SCHEMA_FACT |
| bool 当作 mvc | 拒绝 | `isinstance(mvc, bool)` 检查 |
| bool 当作 bbox 值 | 拒绝 | `isinstance(v, bool)` 检查 |
| NaN/Inf bbox 值 | 拒绝 | `math.isnan(v) or math.isinf(v)` |
| mvc = 0 | 允许 | `mvc < 0` 才拒绝 |
| mvc = 8（任意非负整数） | 允许 | 无上限约束 |
| 屏幕边界值范围 | 无 0–1 限制 | Schema 不检查 0≤v≤1 |
| min_left ≤ max_right | 不检查 | Schema 不验证顺序 |
| min_bottom ≤ max_top | 不检查 | Schema 不验证顺序 |

### 4.5 Camera Check 与 Projection Groups Schema 差异

| 差异点 | camera_check | projection_groups |
|--------|-------------|-------------------|
| 对象范围 | 单 target（per-target） | 多 target_ids + additional_object_names |
| 组标识 | 无 group_id | 必须有 group_id（唯一） |
| 相机位置要求 | 无 | `require_camera_outside_world_bbox` (bool) |
| 目标引用验证 | 不引用其他 target | `target_ids` 引用必须指向已知 target_id |
| `min_left > max_right` 验证 | 不检查 | 检查 |
| `min_bottom > max_top` 验证 | 不检查 | 检查 |
| mvc 验证 | 相同逻辑 | 相同逻辑 |
| bbox 值验证 (finite, non-bool) | 相同逻辑 | 相同逻辑 |

两个 Schema 验证函数对共享字段（同样名称的 bbox 边界）施加了不同级别的验证。这是一个 **CURRENT_SCHEMA_FACT**（设计阶段应裁定是否统一 — 见 DF-09）。

### 4.6 当前 Schema 测试覆盖

来源：`protocol_guard/phase3_min/tests/test_asset_scene_preflight_core.py`

| 测试 | 覆盖内容 | 说明 |
|------|---------|------|
| `test_camera_check_valid` (L329) | 完整有效块 → 0 errors | 直接测试 `_validate_camera_check` |
| `test_mvc_bool_rejected` (L581) | mvc = True → 拒绝 | 直接测试 `_validate_camera_check` |
| `test_screen_bbox_nan_rejected` (L570) | bbox 值为 NaN → 拒绝 | 测试 `_validate_projection_groups`，未直接执行 `_validate_camera_check`；共享字段类型验证逻辑相同，可用作参考 |

未覆盖的 Schema 场景（留作设计/实施阶段的测试计划，不属于本轮阻断）：
- camera_check 缺失/None 的行为
- camera_object_name 为空字符串
- mvc 为负数
- required_screen_bbox 不是 dict
- bbox 字段缺失 (None)
- bbox 字段为 bool 值
- bbox 字段为 Inf
- 整个 camera_check 为 non-dict
- camera_check 块中 6 个叶子字段全部缺失时是否触发所有验证

---

## 5. 正式实现合同中的 Camera Check 要求

来源：`ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT_R2.md`

### 5.1 §10.1 Per-Target Projection (Retained)

```text
The per-target camera check from R1 Section 19 is retained with the modification
that projection uses evaluated geometry bbox corners (not raw bound_box).
```

R2 的规定（唯一可直接引用的合同文本）：
1. **几何来源**：使用 evaluated geometry bbox corners（不是 raw `object.bound_box`）
2. **作用域**：Per-target — 对每个目标独立执行
3. **投影函数**：`world_to_camera_view`

注意：R1 Section 19 的原始文本无法获取，R2 的一句摘要没有说明 R1 原文是否包含额外的算法细节、失败条件或结果结构。这些内容在 R2 中可能被假设为已知而省略。

### 5.2 §10.2 Global Projection Groups (New)

投影组是**附加**的多目标/对象联合检查，不属于 Camera Check 的 per-target 范围。两者共享：
- `camera_object_name`
- `minimum_visible_projected_corner_count`
- `required_screen_bbox`
- `world_to_camera_view` 投影函数
- evaluated geometry 作为几何来源

### 5.3 §4 Evaluated Geometry Contract — 对 Camera Check 的约束链

R2 §4.1（Primary Geometry Source）：
> v1 MUST use the evaluated dependency graph at the current scene frame

R2 §4.2（Algorithm）：
> 1. Get evaluated object via `object.evaluated_get(depsgraph)`
> 2. Call `evaluated.to_mesh()` to obtain a temporary evaluated Mesh
> 3. Iterate `mesh.vertices`; transform each vertex by `evaluated.matrix_world`
> 4. **Aggregate all world-space vertices across all geometry-scope meshes**
> 5. Call `evaluated.to_mesh_clear()` in a `finally` block

R2 §4.2 的步骤 4 直接规定："Aggregate all world-space vertices across all geometry-scope meshes"。这为 Camera Check 的 per-target 几何聚合提供了明确的 AUTHORITATIVE_IMPLEMENTATION_CONTRACT 约束：

- **`target.geometry_scope`** 决定哪些 MESH 对象参与计算 — 这是已有的合同事实，Camera Check 复用该字段。
- **多 Mesh 聚合方式** — 所有 geometry_scope 内的 MESH 对象的全部世界空间顶点聚合为一个集合，再从中计算 per-target union world bbox。
- **Bbox 计算** — 从聚合后的全部世界空间顶点取出 min/max 各轴分量，形成 per-target world-space bbox 的 8 个角点。

R2 §5.1（BBox from Evaluated Geometry）进一步确认：
> All world-space bbox values are computed from the evaluated geometry vertex positions, not from `object.bound_box`.

### 5.4 §10.3 Projection Limitations

```text
Screen bbox checks verify geometric margins. They do NOT verify that empty
space is "visually meaningful" or that the composition "identifies the
supermarket." V4-41 (top/bottom empty ≤15%) and V4-42 (left/right margin ≥4%)
are geometric rules codifiable via projection. Whether empty regions are
visually acceptable is a separate human judgment question.
```

R2 §10.3 确认 CR-05 和 CR-06 的百分比边距属于可代码化的几何规则。边界值必须来自 spec 的 `required_screen_bbox`，禁止硬编码百分比阈值。

---

## 6. 当前生产代码与测试覆盖状态

### 6.1 Reader 中的 Camera Check

**状态：完全不存在。**

- `blender_scene_reader.py` 中**不存在** `_check_camera_check` 函数
- `_check_root_objects()` 的 NOT_CHECKED 模板（行 1167–1183 / 1206–1231 / 1268–1311）中**不包含** `camera_check` 键
- `open_blend_and_get_scene()` 的主循环（行 2722–2754）中**没有** camera_check 调用
- `_recompute_target_overall()` 通用遍历所有 checks 子键，但当前不会有 camera_check 条目
- `_collect_target_errors()` 中**没有** camera_check 错误收集

### 6.2 Entry 中的 Camera Check

**状态：Schema 级 pre-open 已验证；没有 Camera-Check 专用的字段关系验证器。**

`_validate_and_open_spec()` 在路径验证和打开 `.blend` 前执行 `validate_spec(spec)`。`validate_spec` 通过 `_validate_camera_check` 完成以下 pre-open 验证：

- camera_object_name 存在且非空
- minimum_visible_projected_corner_count 为非 bool 整数且 ≥ 0
- required_screen_bbox 为 dict 且四个边界字段均为有限数值
- 各字段拒绝 bool、NaN、Inf

当前缺少的是：
- 额外的 camera-check 专用字段关系验证（如 mvc 与角点总数的关系、bbox 边界顺序、0–1 范围）
- Blender 运行时 `_check_camera_check` 函数
- 入口集成（NOT_CHECKED 填充、per_target_result 写入、错误收集）

### 6.3 与已有字段组的集成状态对比

| 集成点 | Ground Contact | Camera Check |
|--------|---------------|-------------|
| Schema（14A core） | ✓ | ✓ |
| 通用 Schema pre-open 验证 | ✓ `validate_spec` → `_validate_ground_contact` | ✓ `validate_spec` → `_validate_camera_check` |
| 专用字段关系 pre-open 验证 | ✓ `_validate_ground_contact_rules_preopen` | ✗ |
| 依赖读取现有 checks | ✓ `checks.object_exists` `checks.object_type` | ✗ |
| Reader 运行时函数 | ✓ `_check_ground_contact` | ✗ |
| NOT_CHECKED 填充 | ✓ `_check_root_objects` 3 个模板 | ✗ |
| per_target_result.checks 写入 | ✓ `open_blend_and_get_scene` 主循环 | ✗ |
| overall 聚合 | ✓ `_recompute_target_overall` | ✗ (自动覆盖但无数据) |
| 顶层错误收集 | ✓ `_collect_target_errors` | ✗ |

### 6.4 当前运行时缺失清单 (CURRENT_RUNTIME_FACT)

| ID | 缺失项 | 位置 |
|----|--------|------|
| RF-01 | `_check_root_objects()` 3 个 NOT_CHECKED 模板不包含 camera_check | `blender_scene_reader.py` |
| RF-02 | `open_blend_and_get_scene()` 主循环不调用 camera_check | `blender_scene_reader.py` |
| RF-03 | `_collect_target_errors()` 不收集 camera_check ERROR | `asset_scene_preflight_check.py` |
| RF-04 | `_check_camera_check` 运行时函数不存在 | `blender_scene_reader.py` |

### 6.5 当前生产代码中的 world_to_camera_view

在整个 `protocol_guard/phase3_min/` 目录中：
- **调用次数**：0 次
- `world_to_camera_view` 只在 Scope Guard 禁止列表中出现（`test_asset_scene_preflight_blender_scene_basic.py` L411, `test_asset_scene_preflight_blender_visibility_i2.py` L22），作为当前不允许调用的函数

---

## 7. Camera Check 与 Projection Groups 的边界

### 7.1 结构差异

| 维度 | Camera Check | Projection Groups |
|------|-------------|-------------------|
| 作用粒度 | 单 target（per-target） | 跨 target + 额外对象 |
| 触发方式 | target.camera_check 块存在 | spec.projection_groups 数组存在 |
| 几何范围 | target.geometry_scope 内的 MESH（R2 §4.2 合同链） | target_ids 内所有 target 的 geometry_scope + additional_object_names |
| 结果位置 | per_target_results[i].checks.camera_check | projection_group_results[j] |
| 相机位置要求 | 无明确要求 | require_camera_outside_world_bbox |
| 屏幕 bbox | 检查单目标投影 | 检查多目标联合投影 |
| mvc | 检查单目标角点可见性 | 检查组联合角点可见性 |

### 7.2 共享基础设施

| 共享组件 | 用途 |
|---------|------|
| `world_to_camera_view` | 投影 bbox 角点到屏幕空间 |
| `bpy.context.evaluated_depsgraph_get()` | 获取 evaluated depsgraph |
| `obj.evaluated_get(depsgraph)` | 获取 evaluated 对象 |
| `to_mesh()` / `to_mesh_clear()` | 获取/释放 evaluated mesh |
| evaluated geometry world bbox | 为投影提供 world-space 角点 |
| geometry_scope 语义 | 确定哪些 MESH 参与计算 |
| `camera_object_name` | 指定使用哪个相机 |
| `minimum_visible_projected_corner_count` | 角点可见性门槛 |
| `required_screen_bbox` | 屏幕空间边界约束 |

### 7.3 权威边界裁决

| 需求 | 归属 | 理由 |
|------|------|------|
| 单目标投影可见性 | Camera Check | R2 §10.1 Per-Target Projection |
| 单目标屏幕边界约束 | Camera Check | Per-target geometry_scope → union bbox → projection |
| 多目标联合投影构图 | Projection Groups | R2 §10.2 单独定义 |
| "essential objects" 裁切数量（CR-03） | Projection Groups | 涉及多对象联合 bbox 聚合 |
| 相机是否在 world bbox 内（CR-07） | Projection Groups | `require_camera_outside_world_bbox` 只在投影组中 |
| 百分比边距约束（CR-05, CR-06） | 两者均可适用 | 单目标 vs 多目标场景；几何逻辑相同 |
| 角点可见性门槛 | 两者共享 | 语义相同，仅作用范围不同 |

---

## 8. 可代码化需求矩阵

| ID | 需求内容 | 来源 | 权威级别 | Schema 覆盖 | 运行时覆盖 | 分类 | 设计阶段需裁定 |
|----|---------|------|---------|------------|-----------|------|-------------|
| CR-01 | 使用 world_to_camera_view 完成数学投影与裁切检查 | V4 §十·1 | AUTHORITATIVE_REQUIREMENT | PARTIAL (字段定义) | NO | CODE_ENFORCEABLE | YES — 裁切与可见性的语义 |
| CR-02 | 通过 bbox 与投影计算摄像机构图 | V4 §十·3 | AUTHORITATIVE_REQUIREMENT | PARTIAL | NO | CODE_ENFORCEABLE | YES — bbox 角点投影的边界判定 |
| CR-03 | essential objects 裁切数量为 0 | V4 §十二·L1-C | AUTHORITATIVE_REQUIREMENT | NO | NO | OUT_OF_CAMERA_CHECK_SCOPE | NO — 属于 Projection Groups 多对象联合投影 |
| CR-04 | 所有目标完整进入安全区 | V4 §十二·L1-C | AUTHORITATIVE_REQUIREMENT | PARTIAL (screen_bbox 定义) | NO | CODE_ENFORCEABLE | YES — "安全区"与 required_screen_bbox 的关系 |
| CR-05 | 顶部空白 ≤ 15%、底部空白 ≤ 15% | V4 §十二·L1-C + R2 §10.3 | AUTHORITATIVE_REQUIREMENT | NO | NO | CODE_ENFORCEABLE | YES — bbox 比较方向和 required_screen_bbox 语义 (DF-14) |
| CR-06 | 左右安全边距 ≥ 4% | V4 §十二·L1-C + R2 §10.3 | AUTHORITATIVE_REQUIREMENT | NO | NO | CODE_ENFORCEABLE | YES — bbox 比较方向和 required_screen_bbox 语义 (DF-14) |
| CR-07 | 相机不进入任何 essential object bbox | V4 §十二·L1-C | AUTHORITATIVE_REQUIREMENT | NO | NO | OUT_OF_CAMERA_CHECK_SCOPE | NO — 属于 Projection Groups `require_camera_outside_world_bbox` |
| CR-08 | 相机排查顺序（层级→姿势→…→相机） | V4 §七 | AUTHORITATIVE_REQUIREMENT | NO | NO | DEFER_REQUIRES_STATE | NO — Design Spec R1 §7.1 已排除 |
| CR-09 | 禁止在前六项未通过时调整相机参数 | V4 §七, §十·6 | AUTHORITATIVE_REQUIREMENT | NO | NO | DEFER_REQUIRES_STATE | NO — Design Spec R1 §7.1 已排除 |

---

## 9. HUMAN_JUDGMENT_ONLY 和 DEFER_REQUIRES_STATE

### 9.1 HUMAN_JUDGMENT_ONLY

| ID | 内容 | 理由 |
|----|------|------|
| HJ-01 | 画面是否好看、构图是否具有吸引力 | §十·3 明确：Claude Code 不判断视觉质量 |
| HJ-02 | 画面是否具有发布潜力 | §十·3 明确：发布潜力由用户和 GPT 判断 |
| HJ-03 | "主体占画面主要区域"、"前景中景背景有层次" | 构图质量需要人工视觉判断 |
| HJ-04 | "第一眼认出超市收银区" | 需要人类视觉识别 |

### 9.2 DEFER_REQUIRES_STATE

| ID | 内容 | 理由 |
|----|------|------|
| DS-01 | 相机排查顺序（CR-08） | 需要跨时间点的状态比较 — Design Spec R1 §7.1 已排除 |
| DS-02 | 禁止在结构检查通过前调整相机（CR-09） | 同上 — 两个无状态只读检查器无法验证时间顺序 |
| DS-03 | 最多两轮返工限制 | 需要执行日志 — Design Spec R1 §7.2 已排除 |

---

## 10. DESIGN_FREEDOM 清单

以下事项原始需求和正式合同未明确规定，需要在设计阶段裁定：

| ID | 问题 | 上下文 |
|----|------|--------|
| DF-01 | `camera_object_name` 解析策略：按名称匹配 `scene.objects`（类似 root_object）还是通过 `bpy.data.objects`？同名歧义如何处理？ | Schema 只验证字段存在，不规定解析策略 |
| DF-02 | Camera 对象不在目标 Scene 中时：ERROR、FAIL 还是 NOT_CHECKED？ | 合同未规定 |
| DF-03 | Camera 对象存在但 type 不是 'CAMERA'：ERROR 还是 FAIL？ | 合同未规定 |
| DF-04 | `world_to_camera_view` 返回 z ≤ 0 的角点如何处理？z ≤ 0 表示角点在相机后方 — 应视为不可见？还是 ERROR？ | 投影语义需要裁决 |
| DF-05 | 8 个 bbox 角点中，某个角点恰好位于屏幕边界（如 x=0 或 x=1）时的包含/排除规则 | 边界条件语义 |
| DF-06 | `minimum_visible_projected_corner_count` 是否允许大于角点总数（如 8 个角点要求 12 个可见）？应退化为 FAIL 还是 pre-open ERROR？ | 合同未规定 |
| DF-07 | 空 geometry scope（无 MESH）→ NOT_CHECKED、FAIL 还是 0 个角点 → FAIL？ | Ground Contact 用 NO_EVALUATED_GEOMETRY FAIL |
| DF-08 | Screen bbox 边界顺序：`min_left ≤ max_right` 和 `min_bottom ≤ max_top` 是否应像 projection_groups 一样由 Schema 验证？ | 当前 Schema 不一致 (CURRENT_SCHEMA_FACT) |
| DF-09 | 是否需要 `required_screen_bbox` 值限制在 [0, 1]？当前 Schema 允许任意有限值 | 语义约束 |
| DF-10 | 是否需要超出当前 Schema 的 extra Camera-Check-specific pre-open 验证规则？（如 mvc 上限、bbox 顺序、0–1 范围） | Schema 已有通用验证；需要裁决是否需要额外关系验证 |
| DF-11 | `minimum_visible_projected_corner_count` 的最大值是否有上限？当前无 | Schema 无上限 |
| DF-12 | FAIL 时 `failure_code` 的具体命名 | 合同未定义 camera_check 特定的 failure_code |
| DF-13 | ERROR 时 `error_type` 的具体命名；`operation` 列表 | 合同未定义 camera_check 特定的 error_type 和 operation |
| DF-14 | CR-05 和 CR-06（百分比边距约束）如何映射到 `required_screen_bbox` 的比较方向。必须裁定：<br>1. "顶部空白不超过 15%"对应 projected_top ≥ 0.85，还是 projected_top ≤ max_top？<br>2. "底部空白不超过 15%"对应 projected_bottom ≤ 0.15，还是 projected_bottom ≥ min_bottom？<br>3. "左右安全边距不低于 4%"对应 projected_left ≥ 0.04 且 projected_right ≤ 0.96。<br>4. `required_screen_bbox` 表达的是允许目标所在的安全区域，还是目标必须覆盖到的最小画面区域？ | BOUNDARY_VALUES_SOURCE: SPEC_REQUIRED_SCREEN_BBOX；HARDCODED_PERCENTAGE_VALUES_ALLOWED: FALSE |

---

## 11. DOCUMENTATION_GAP 清单

| ID | 缺失内容 | 影响 |
|----|---------|------|
| DG-01 | camera_check 的 NOT_CHECKED 条件未在任何正式合同中定义 | 设计阶段需裁定何时为 NOT_CHECKED、何时为 PASS/FAIL/ERROR |
| DG-02 | camera_check 的结果字典结构未在任何正式合同中定义（字段名、键集、failure_code 列表） | 设计阶段需裁定 |
| DG-03 | camera_check 与 projection_groups 的屏幕边界顺序验证不一致（camera_check 不检查 min_left>max_right，projection_groups 检查） | 设计阶段需裁定是否统一 |

---

## 12. TRUE_CONTRACT_CONFLICT 清单

**无真实合同冲突。**

经过对所有权威材料的逐项比对：

- Camera Check 原始需求（V4）要求数学投影和裁切检查
- 当前 Schema 定义了输入字段结构
- R2 §10.1 确认 Per-Target Projection 应保留
- R2 §4.2 规定了 geometry_scope 遍历和多 Mesh 顶点聚合
- 三者方向一致，没有互相矛盾的要求

R1 Section 19 的原始文本无法获取（AUDIT_COVERAGE_GAP）。设计应直接以 R2 §4、§10.1、§10.2、§10.3 为 Camera Check 的合同基础，不需要等待 R1 恢复。

---

## 13. 设计阶段必须裁定的问题

以下问题按优先级排列，必须在 Camera Check 设计阶段给出明确答案：

### 设计必须优先裁定

| # | 问题 | 关联 |
|---|------|------|
| 1 | `world_to_camera_view` 返回 z ≤ 0 的角点如何处理？ | DF-04 |
| 2 | 屏幕边界验证是否 0–1 限制？是否统一 bbox 顺序检查？ | DF-08, DF-09 |
| 3 | mvc 超过角点总数时的行为 | DF-06 |
| 4 | 空 geometry scope 的行为 | DF-07 |
| 5 | Camera 对象解析策略（同名歧义、type 检查、Scene 外 Camera） | DF-01, DF-02, DF-03 |
| 6 | 角点恰好位于屏幕边界的包含/排除规则 | DF-05 |

### 设计完成前必须关闭

| # | 问题 | 关联 |
|---|------|------|
| 7 | PASS / FAIL / ERROR / NOT_CHECKED 条件 | DF-12, DF-13, DG-01, DG-02 |
| 8 | failure_code 和 error_type 命名 | DF-12, DF-13 |
| 9 | operation 列表和错误优先级 | DF-13 |
| 10 | mvc 上限值 | DF-11 |
| 11 | Pre-open 额外字段关系验证规则（超出当前 Schema 的部分） | DF-10 |
| 12 | CR-05/CR-06 百分比约束如何映射到 `required_screen_bbox` 的比较方向；`required_screen_bbox` 的几何含义（安全区 vs 覆盖区） | DF-14 |

所有影响 PASS、FAIL、ERROR、NOT_CHECKED 语义、边界包含关系、mvc 合法范围、pre-open 错误条件、bbox 比较方向和语义的问题，都必须在设计阶段关闭。不得将验收语义推迟到实施阶段自行决定。

---

## 14. 审计结论

### 14.1 总体判断

```text
AUDIT_STATUS: COMPLETED
AUDIT_RESULT: REQUIREMENTS_SUFFICIENT_FOR_DESIGN
AUDIT_COVERAGE_GAP_COUNT: 1
AUDIT_COVERAGE_GAP:
  R2 §10.1 引用的 R1 Section 19 原始文本无法获取
  — ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT.md (R1) 不存在
```

Camera Check 满足进入设计阶段的充分条件：

1. **原始需求明确**：V4 交接文档清楚定义了 Camera Check 的业务目标 — 使用 `world_to_camera_view` 做数学投影和裁切检查，确保目标在相机画面内。

2. **Schema 已就位**：14A core 中 `_validate_camera_check` 已定义了 6 个叶子字段的类型和基本验证规则，覆盖 camera_object_name、minimum_visible_projected_corner_count、required_screen_bbox。

3. **实现合同有框架**：R2 合同 §10.1 确认 Per-Target Projection 应保留并改用 evaluated geometry。§4.2 规定了 geometry_scope 遍历和多 Mesh 顶点聚合。§10.3 明确了屏幕 bbox 的几何性质。

4. **无真实合同冲突**：原始需求、Schema、实现合同三者方向一致。

5. **与 Projection Groups 边界清晰**：Camera Check 是 per-target 的单目标检查；Projection Groups 是跨目标的联合检查。

### 14.2 审计覆盖缺口

```text
AUDIT_COVERAGE_GAP_COUNT: 1
AUDIT_COVERAGE_GAP:
  R2 §10.1 引用的 R1 Section 19 原始文本无法获取。
  该缺口属于历史审计覆盖缺口，不构成真实合同冲突。
  不阻止 Camera Check 进入设计阶段。
  设计必须以当前原始需求（V4）、锁定 Schema 和 R2 正文为权威边界。
  不得凭空恢复或猜测 R1 Section 19 的内容。
```

### 14.3 设计自由和文档缺口不构成阻断

14 项设计自由（DF-01 到 DF-14）和 3 项文档缺口（DG-01 到 DG-03）属于 Camera Check 的设计阶段正常需要裁定的事项。Ground Contact 和 Material Assignment 等已锁定字段组在设计阶段前有类似数量的未决事项。

### 14.4 与已完成字段组的可比性

Camera Check 的几何合同基础（R2 §4 evaluated geometry）已经在 Ground Contact 的正式锁定实现中得到验证。Camera Check 可以直接复用 `_collect_geometry_scope_objects` 和 evaluated depsgraph 流程。

---

## 15. 机器可读摘要

```text
TASK_ID: CAMERA_CHECK_ORIGINAL_REQUIREMENT_AUDIT
TASK_TYPE: ORIGINAL_REQUIREMENT_AUDIT
MASTER_MAP_VERSION: R77
CORRECTION: R3 — 最终状态统一与 DF-14 分类修正

AUDIT_STATUS: COMPLETED
AUDIT_RESULT: REQUIREMENTS_SUFFICIENT_FOR_DESIGN
AUDIT_COVERAGE_GAP_COUNT: 1
AUDIT_COVERAGE_GAP:
  R2 §10.1 引用的 R1 Section 19 原始文本无法获取
  — ASSET_SCENE_PREFLIGHT_IMPLEMENTATION_CONTRACT.md (R1) 磁盘和 git 历史均不存在

FILES_ACTUALLY_READ: 12 (plus 1 missing)
AUTHORITATIVE_REQUIREMENT_COUNT: 9 (CR-01 to CR-09)
CURRENT_SCHEMA_FIELD_COUNT: 6 (leaf fields — camera_object_name, minimum_visible_projected_corner_count, min_left, max_right, min_bottom, max_top)
CURRENT_RUNTIME_CAPABILITY_COUNT: 0
CODE_ENFORCEABLE_REQUIREMENT_COUNT: 5 (CR-01, CR-02, CR-04, CR-05, CR-06)
HUMAN_JUDGMENT_ONLY_COUNT: 4 (HJ-01, HJ-02, HJ-03, HJ-04)
DEFER_REQUIRES_STATE_COUNT: 3 (DS-01, DS-02, DS-03)
OUT_OF_CAMERA_CHECK_SCOPE_COUNT: 2 (CR-03, CR-07 → Projection Groups)
DESIGN_FREEDOM_COUNT: 14 (DF-01 to DF-14)
DOCUMENTATION_GAP_COUNT: 3 (DG-01, DG-02, DG-03)
CURRENT_RUNTIME_FACT_COUNT: 4 (RF-01, RF-02, RF-03, RF-04)
TRUE_CONTRACT_CONFLICT_COUNT: 0
TRUE_BLOCKING_ISSUES: 0

RUNTIME_IMPLEMENTATION_EXISTS: FALSE
REQUIREMENTS_SUFFICIENT_FOR_DESIGN: TRUE
DESIGN_AUTHORIZED: FALSE
IMPLEMENTATION_AUTHORIZED: FALSE

PRODUCTION_PROGRESS_THIS_ROUND: FALSE
WHY_THIS_NON_PRODUCTION_WORK_IS_NECESSARY:
  Camera Check 是下一个尚未实施的字段组。实施前必须确定原始业务需求、
  当前锁定 Schema、既有实现合同和历史设计材料之间的真实关系，
  防止把 Projection Groups、视觉构图判断或历史草案内容错误并入 Camera Check。

WHAT_DECISION_IT_UNLOCKS:
  判断 Camera Check 是否具备进入设计阶段的充分需求，并明确哪些内容
  已经由合同确定，哪些属于设计自由、文档缺口、人工判断、状态依赖
  或真实合同冲突。

EXIT_CONDITION:
  完成两项固定修正并输出 R3 最终版报告，
  然后立即停止，等待 GPT 独立审核和用户后续授权。

REAL_PROJECT_BLEND_OPENED: FALSE
REAL_PROJECT_BLEND_SAVED: FALSE
RENDER_EXECUTED: FALSE
TESTS_RUN: NONE
PYTEST_EXIT_CODE: NOT_APPLICABLE
BLENDER_EXECUTED: FALSE
MASTER_MAP_MODIFIED: FALSE
```

---

*R3 修正完成。修正了 F-001（审计状态统一为 COMPLETED/REQUIREMENTS_SUFFICIENT_FOR_DESIGN，增加 AUDIT_COVERAGE_GAP）、F-002（DF-14 从"参数来源"重写为"比较方向映射"）。未修改任何生产代码、测试、CLAUDE.md 或总地图。未运行 pytest 或 Blender。未生成 ZIP、Manifest 或 SHA256。*
