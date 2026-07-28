# 全局代码化总账审计报告

**TASK_ID**: GLOBAL_CODEIFICATION_AUDIT
**BASELINE**: d44679fc11c5069a17277395bb6c52b5a6dfc799
**AUDIT_DATE**: 2026-07-18

---

## 一、这件事是什么

这是一个 Blender 视频工厂项目。目标是用代码自动检查组装的 Blender 角色资产是否符合标准模板，再交给渲染流水线使用，避免人工反复排查。

核心机制叫 **Asset Scene Preflight Check**（资产场景预检）。它读取一个 `.blend` 文件，对照一份 spec 规范，检查角色是否摆正、骨架是否正确、材质是否存在、动画是否就绪等。

**为什么做这个？** 因为在这个流水线里，一个错误的人物朝向或缺失的骨骼会浪费大量渲染时间。用代码在渲染前自动发现这些问题，比渲染完再修快得多。

**谁在做？** Claude Code 负责写代码和跑测试，GPT 负责设计审核和视觉判断，用户做最终决策。

---

## 二、已经完成代码化的内容

以下要求已经通过源码和测试验证，确认已落实：

| # | 要求 | 实现位置 | 测试 | 锁定阶段 |
|---|------|---------|------|---------|
| 1 | Scene 基础读取（场景是否存在、渲染引擎、当前帧） | blender_scene_reader.py | basic.py (85 tests) | 14B-1 |
| 2 | 根对象唯一存在与类型检查 | blender_scene_reader.py | basic.py (7 tests) | 14B-2A |
| 3 | 直接子对象必需名称检查 | blender_scene_reader.py | basic.py (4 tests) | 14B-2B |
| 4 | 直接子对象允许列表检查 | blender_scene_reader.py | basic.py (7 tests) | 14B-2B |
| 5 | 直接子对象禁止模式检查（glob） | blender_scene_reader.py | basic.py (9 tests) | 14B-2B |
| 6 | 后代必需名称检查（递归遍历） | blender_scene_reader.py | descendants_i1.py (26) | 14B-2C |
| 7 | 后代禁止模式检查（glob） | blender_scene_reader.py | descendants_i2.py (29) | 14B-2C |
| 8 | 同名后代歧义检测（ERROR） | blender_scene_reader.py | descendants_i3a.py (9) | 14B-2C |
| 9 | 后代读取异常边界（4个operation） | blender_scene_reader.py | descendants_i3b1.py (9) | 14B-2C |
| 10 | 要求后代类型映射检查 | blender_scene_reader.py | types_i1b+i2a+i2b1+i2b2 (47) | 14B-2D |
| 11 | 后代 type 读取异常边界 | blender_scene_reader.py | types_i2a.py (9) | 14B-2D |
| 12 | type 读取优先于名称歧义 | blender_scene_reader.py | types_i2b1.py (12) | 14B-2D |
| 13 | type 值按对象身份缓存，不重复读取 | blender_scene_reader.py | types_i1b.py (19) | 14B-2D |
| 14 | Scene membership 使用 Python 身份判断 | blender_scene_reader.py | 全后代测试验证 | 14B-2C |
| 15 | 非目标 Scene 分支剪枝 | blender_scene_reader.py | 全后代测试验证 | 14B-2C |
| 16 | 预打开输入验证（所有descendant规则） | asset_scene_preflight_check.py | validation_i1a.py (17) | 14B-2D |
| 17 | Standing Up Axis 三字段预验证 | asset_scene_preflight_check.py | standing_i1.py (11) | 14B-3A I1A |
| 18 | Standing Up Axis PASS/FAIL/NOT_CHECKED | blender_scene_reader.py | standing_i1b.py (13) | 14B-3A I1B |
| 19 | 14A Core 全部字段 schema 验证 | asset_scene_preflight_core.py | test_core.py (139) | 14A |
| 20 | 目录级测试 harness 硬化（防假通过） | i3a.py, i2.py | 49 tests | 14B-2C H1/H2 |

---

## 三、部分完成的内容

| # | 要求 | 已完成 | 缺失 | 差距 |
|---|------|--------|------|------|
| 1 | Standing Up Axis 运行时 | PASS/FAIL/NOT_CHECKED + 归一化 + 0.0容差 | 零长度向量ERROR、NaN/Inf ERROR、_collect_target_errors扩展、真实Blender矩阵边界测试 | I1C 待实施 |
| 2 | Blender 测试 harness | i3a.py 和 i2.py 已硬化 | 仍有部分测试使用旧 `_run_checker` helper（无防假通过） | 低优先级 |

---

## 四、尚未代码化但应该代码化的内容

这些要求已由14A Core完成schema验证，但blender_scene_reader中尚未实现运行时检查：

| # | 字段 | 14A Core | Reader | 需要读取的Blender属性 | 复杂度 |
|---|------|---------|--------|----------------------|--------|
| 1 | standing 错误处理 | ✓ | ✗ | 同上 | 中 |
| 2 | facing (朝向) | ✓ | ✗ | matrix_world.to_3x3 | 中 |
| 3 | rotation (旋转) | ✓ | ✗ | rotation_quaternion / rotation_euler | 中 |
| 4 | ground_contact (地面接触) | ✓ | ✗ | evaluated depsgraph + to_mesh | 高 |
| 5 | visibility (可见性) | ✓ | ✗ | hide_viewport, hide_render | 低 |
| 6 | material_assignment (材质) | ✓ | ✗ | material_slots | 中 |
| 7 | animation_state (动画状态) | ✓ | ✗ | animation_data, action | 中 |
| 8 | camera_check (相机检查) | ✓ | ✗ | world_to_camera_view | 高 |
| 9 | collection_rules (集合规则) | ✓ | ✗ | bpy.data.collections, users_collection | 中 |
| 10 | projection_groups (投影组) | ✓ | ✗ | world_to_camera_view, bbox | 高 |
| 11 | blender_output_artifact_check | — | ✗ | 全新检查器 | 高 |

---

## 五、不适合代码化的内容

这些要求无法用自动化代码检查，需要人工判断：

- 渲染结果的视觉质量判断（GPT 和用户负责）
- 单个变量的优先处理选择
- 是否发布最终决策
- FBX 重新导入是否发生（需要执行日志）
- "不退回基础几何"等策略性约束

---

## 六、已废弃或冲突的内容

| 冲突 | 来源 | 裁决 |
|------|------|------|
| 15项 vs 11项 ADD_TO_MINIMAL_PHASE_3 | Design Spec R1 Sec 2 | 实际为15项，R1修正为15项 |
| PE-01~PE-05 原是 PARTIALLY | 初次审计 | R1修正为 DOCUMENT_ONLY / HUMAN_JUDGMENT_ONLY |
| Phase 3 scope frozen | 初次审计 | R1修正为 FALSE |
| PCA 方案 | 早期设计 | R2设计明确排除，改用 matrix_world.to_3x3() 归一化 |
| bounding_box 作为主要几何来源 | R1实现合同 | R2合同改为 evaluated depsgraph |

---

## 七、当前真实完成比例

### 计算说明
计算范围：14A Core 中已定义的、可被代码自动验证的规则。不包括文档规则、人工判断规则和已废弃规则。

**加权规则**：每个"字段组"（如 standing）计为1个单位。字段组内的子字段不单独计数。完整实现 = schema验证 + reader运行时 + Blender测试 + harness硬化。

| 分类 | 数量 |
|------|------|
| 已定义字段组总数 | 11 (hierarchy, standing, facing, rotation, ground_contact, visibility, material, animation, camera, collection, projection) |
| 完全实现 | 1 (hierarchy — 包括 direct_children + descendants) |
| 部分实现 | 1 (standing — 50%) |
| 完全未实现 | 9 (facing, rotation, ground_contact, visibility, material, animation, camera, collection, projection) |

### 辅助检查器
| checker | 状态 |
|---------|------|
| asset_scene_preflight_check | 字段级完成度 ~15% |
| blender_output_artifact_check | 0%（不存在） |

### Phase 3 主范围

```
ASSET_SCENE_PREFLIGHT_FIELD_GROUP_COUNT: 11
 (hierarchy, standing, facing, rotation, ground_contact,
  visibility, material_assignment, animation_state,
  camera_check, collection_rules, projection_groups)

INDEPENDENT_OUTPUT_CHECKER_COUNT: 1
 (blender_output_artifact_check)

TOTAL_MAJOR_PHASE3_FUNCTION_LINES: 12
```

### 三种完成比例（计算口径不同）

**端到端运行时检查完成率**: 完全实现且已锁定的字段组为 1/11（hierarchy），standing 约 50%。约 **14%**。

**包含 Schema 基础工作的开发进度**: 每个字段组计为 1 个单元。完整运行时 = 3 分，部分运行时 = 1.5 分，仅 schema = 1 分。13.5/33 ≈ **41%**。

```text
END_TO_END_RUNTIME_ENFORCEMENT_COMPLETION: approximately 14%
INCLUDING_SCHEMA_DEVELOPMENT_PROGRESS: approximately 41%
TEST_INFRASTRUCTURE_MATURITY: approximately 85%
```

- 端到端: (1 × 3 + 0.5 × 3) / (11 × 3) = 4.5/33 ≈ 14%。只计 reader 运行时代码与测试。
- 含 Schema: (1 × 3 + 1 × 1.5 + 9 × 1) / (11 × 3) = 13.5/33 ≈ 41%。14A core 已为全部 11 个字段组完成 schema 验证，因此 9 个未实现字段组各得 1 分。
- 基础设施: harness 硬化、回归流程、证据包生成均已就绪，约 85%。

```
TOTAL_EFFECTIVE_REQUIREMENTS: 33 (11 field groups × 3 implementation phases)
CODE_ENFORCED_COUNT: 1 (hierarchy — end-to-end locked)
PARTIALLY_CODE_ENFORCED_COUNT: 1 (standing — I1A+I1B done, I1C pending)
PENDING_CODE_ENFORCEMENT_COUNT: 9 (remaining field groups, schema-only)
DOCUMENT_ONLY_COUNT: 5 (PE/operational rules)
HUMAN_JUDGMENT_ONLY_COUNT: 5 (visual quality, decisions)
DEFER_REQUIRES_STATE_COUNT: 2 (FBX reimport log, execution log)
OBSOLETE_OR_CONTRADICTED_COUNT: 2 (PCA, raw bound_box)
ESTIMATED_REMAINING_ATOMIC_TASK_COUNT: 25-30
```

---

## 八、剩余工作量

按实现复杂度分档：

### 低复杂度（每字段组 1-2 轮）
- standing error handling (14B-3A-I1C)
- visibility（读取 hide_viewport/hide_render）

### 中复杂度（每字段组 2-3 轮）
- facing（matrix_world 方向转换）
- rotation（四元数角度比较）
- material_assignment（material_slots 存在性）
- animation_state（animation_data + action name）
- collection_rules（collection 存在性 + 禁制）

### 高复杂度（每字段组 3-5 轮）
- ground_contact（需要 evaluated depsgraph + to_mesh）
- camera_check（需要 world_to_camera_view 投影）
- projection_groups（需要 bbox + 投影组）
- blender_output_artifact_check（全新检查器）

---

## 九、推荐后续任务顺序

1. **14B-3A-I1C** — 完成 standing 错误处理（最接近完成）
2. **14B-3A-E** — standing 最终证据（锁定 standing）
3. **facing** — 与 standing 同一套 matrix_world 机制，成本最低
4. **visibility** — 最简单的新字段，建立信心
5. **rotation** — 扩展 matrix_world 到四元数
6. **animation_state** — 不依赖几何
7. **material_assignment** — 需要读取 mesh 数据
8. **collection_rules** — 全局规则，非 per-target
9. **ground_contact** — 需要 evaluated geometry
10. **camera_check** — 需要投影
11. **projection_groups** — 最复杂
12. **blender_output_artifact_check** — 全新检查器

---

## 十、下一步唯一建议

**完成 14B-3A-I1C（standing 错误处理），然后做 standing 最终证据锁定。** 这是当前最接近完成的功能线，完成它可以让 "standing" 成为第二个完全锁定的字段组。之后再决定是否继续顺序推进 facing/visibility，或跳到更高优先级的业务需求。

---

*审计完成。未修改任何生产代码、测试或证据文件。未运行 Blender 或打开真实项目 .blend。*
