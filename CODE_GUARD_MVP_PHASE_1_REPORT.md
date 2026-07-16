# CODE GUARD MVP Phase 1 — 实施报告

Date: 2026-07-15
Status: **PHASE_1_TECHNICAL_PASS = True**

---

## 1. 创建文件清单

### protocol_guard/ 核心模块
| # | 文件 | 用途 |
|---|------|------|
| 1 | `protocol_guard\__init__.py` | 包标识 |
| 2 | `protocol_guard\result.py` | TECHNICAL_RESULT 枚举 (5 values) + EvidenceStatus 枚举 (3 values) |
| 3 | `protocol_guard\task_schema.py` | 任务卡 JSON Schema 验证 + 跨字段约束检查 |
| 4 | `protocol_guard\state\__init__.py` | state 包标识 |
| 5 | `protocol_guard\state\project_state.py` | PROJECT_STATE 读写 + 字段级 actor 权限 (validate/validate_patch/apply_patch) |
| 6 | `protocol_guard\frozen\__init__.py` | frozen 包标识 |
| 7 | `protocol_guard\frozen\snapshot.py` | SHA256 任务卡冻结 + 验证 (freeze_task/verify_frozen_task) |

### JSON Schema
| # | 文件 | 用途 |
|---|------|------|
| 8 | `schemas\task_card.schema.json` | 任务卡 JSON Schema (23 required fields, 2 enum constraints) |
| 9 | `schemas\project_state.schema.json` | PROJECT_STATE JSON Schema (9 required fields) |
| 10 | `schemas\state_patch.schema.json` | 状态补丁 JSON Schema (actor + fields) |

### 测试文件
| # | 文件 | 用例数 |
|---|------|--------|
| 11 | `tests\test_result.py` | 7 (枚举值正确性) |
| 12 | `tests\test_task_schema.py` | 12 (Schema 验证 + 跨字段约束) |
| 13 | `tests\test_project_state.py` | 14 (状态验证 + 字段权限) |
| 14 | `tests\test_snapshot.py` | 5 (冻结/验证) |

### 项目根目录
| # | 文件 | 用途 |
|---|------|------|
| 15 | `PROJECT_STATE.yaml` | 项目初始状态 (bvf_asset_test_001_checkout_lane) |
| 16 | `tasks\EXAMPLE_TASK\task.yaml` | 示例任务卡 |
| 17 | `HUMAN_COLLAB_RULES.md` | 人类协作规则 (<800 中文字) |

### 目录
```
tasks\
approvals\
evidence\
protocol_guard\schemas\
protocol_guard\state\
protocol_guard\frozen\
protocol_guard\tests\
reviews\PROTOCOL_IMPLEMENTATION_UPLOAD\
```

---

## 2. Schema 字段

### task_card.schema.json
- 23 个必填字段
- `execution_mode` 枚举: `confirm_then_execute`, `direct_execute`
- `task_type` 枚举: AUDIT, MODIFICATION, ROOT_CAUSE_AUDIT, CALIBRATION, PROTOCOL_MAINTENANCE
- `primary_variable`: 必须是单个非空字符串 (跨字段约束在 task_schema.py 中强制)
- `dependent_variables` / `fixed_params`: 必须与 primary_variable 无交集 (跨字段约束)
- `visual_intent` / `visual_forbidden`: 允许自然语言, Schema 不做技术判断

### project_state.schema.json
- 9 个必填字段
- `last_technical_result` 枚举: 5 个允许值
- `evidence_status` 枚举: VALID, RECOVERED, INVALID

### state_patch.schema.json
- 2 个必填字段: actor, fields
- actor 枚举: CLAUDE, GPT_PROPOSAL, USER_APPROVED

---

## 3. 权限矩阵

| 字段分组 | CLAUDE | GPT_PROPOSAL | USER_APPROVED |
|----------|--------|-------------|---------------|
| last_task_id | write | — | write |
| last_task_card_sha256 | write | — | write |
| last_technical_result | write | — | write |
| evidence_status | write | — | write |
| evidence_sha256 | write | — | write |
| output_files | write | — | write |
| last_execution_time | write | — | write |
| workflow_phase | **blocked** | **blocked** | write |
| scene_phase | **blocked** | **blocked** | write |
| phase_approved | **blocked** | **blocked** | write |
| locked_assets | **blocked** | **blocked** | write |
| unlocked_assets | **blocked** | **blocked** | write |
| blocked_operations | **blocked** | **blocked** | write |
| failed_paths | **blocked** | **blocked** | write |
| project_work_paused | **blocked** | **blocked** | write |
| protocol_version | **blocked** | **blocked** | write |

GPT_PROPOSAL: 只能生成建议, 禁止直接写入任何字段。需要 USER_APPROVED 审批后才能通过 apply_patch 生效。

---

## 4. 冻结流程

1. `freeze_task(task_path, frozen_dir)` 复制任务卡 YAML + 写入 SHA256 文件
2. 若 `frozen_task.yaml` 已存在, 拒绝覆盖 (返回 error)
3. `verify_frozen_task(task_path, frozen_dir)` 比较当前 SHA256 与冻结 SHA256
4. 修改任务卡后验证失败 -> 需要提升 `task_card_version` 或更换 `task_id`

---

## 5. 测试列表 (38 项)

### test_result.py (7)
1. test_valid_main_results — 5个主结果正确
2. test_evidence_recovered_not_main_result — EVIDENCE_RECOVERED 不是主结果
3. test_technical_pass_is_valid — TECHNICAL_PASS 可构造
4. test_illegal_result_rejected — 非法结果抛出 ValueError
5. test_evidence_recovered_is_not_a_technical_result — EVIDENCE_RECOVERED 不能构造 TechnicalResult
6. test_valid_evidence_statuses — 3个证据状态正确
7. test_illegal_evidence_status_rejected — 非法证据状态抛出 ValueError

### test_task_schema.py (12)
8. test_valid_task_passes — 合法任务卡通过
9. test_missing_required_field_fails — 缺失必填字段失败
10. test_invalid_execution_mode_fails — 非法 execution_mode 失败
11. test_primary_variable_not_single_string_fails — primary_variable 是数组时失败
12. test_empty_primary_variable_fails — primary_variable 为空时失败
13. test_duplicate_in_dependent_and_fixed_fails — 同参数在 dependent 和 fixed 中失败
14. test_duplicate_primary_and_dependent_fails — 同参数在 primary 和 dependent 中失败
15. test_duplicate_primary_and_fixed_fails — 同参数在 primary 和 fixed 中失败
16. test_direct_execute_mode_is_valid — direct_execute 为合法值
17. test_task_type_modification_is_valid — MODIFICATION 为合法类型
18. test_visual_intent_allows_natural_language — 视觉描述允许自然语言
19. test_invalid_task_type_fails — 非法 task_type 失败

### test_project_state.py (14)
20. test_initial_project_state_passes — 磁盘 PROJECT_STATE.yaml 通过 Schema
21. test_invalid_technical_result_fails — 非法技术结果失败
22. test_invalid_evidence_status_fails — 非法证据状态失败
23. test_missing_required_field_fails — 缺失必填字段失败
24. test_claude_can_write_runtime_fields — CLAUDE 写运行时字段通过
25. test_claude_cannot_write_locked_assets — CLAUDE 写 locked_assets 被拒绝
26. test_claude_cannot_write_scene_phase — CLAUDE 写 scene_phase 被拒绝
27. test_gpt_proposal_cannot_write_directly — GPT_PROPOSAL 不能直接写入
28. test_user_approved_can_write_restricted_fields — USER_APPROVED 可写受限字段
29. test_apply_claude_runtime_patch_succeeds — CLAUDE apply_patch 运行时字段成功
30. test_apply_claude_restricted_patch_rejected — CLAUDE apply_patch 受限字段被拒绝
31. test_apply_user_approved_restricted_patch_succeeds — USER_APPROVED apply_patch 成功
32. test_gpt_proposal_with_approval_succeeds — GPT_PROPOSAL+approval 成功
33. test_gpt_proposal_without_approval_rejected — GPT_PROPOSAL 无 approval 被拒绝

### test_snapshot.py (5)
34. test_first_freeze_succeeds — 首次冻结成功
35. test_verify_succeeds_on_unchanged_task — 未修改任务验证通过
36. test_modified_task_fails_verification — 已修改任务 SHA 验证失败
37. test_existing_frozen_rejects_overwrite — 已存在冻结快照拒绝覆盖
38. test_freezing_nonexistent_dir_creates_it — 不存在目录自动创建

---

## 6. pytest 完整结果

```
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-7.4.4, pluggy-1.6.0
rootdir: D:\blender-video-factory

protocol_guard/tests/test_project_state.py::TestProjectStateSchema::test_initial_project_state_passes PASSED
protocol_guard/tests/test_project_state.py::TestProjectStateSchema::test_invalid_technical_result_fails PASSED
protocol_guard/tests/test_project_state.py::TestProjectStateSchema::test_invalid_evidence_status_fails PASSED
protocol_guard/tests/test_project_state.py::TestProjectStateSchema::test_missing_required_field_fails PASSED
protocol_guard/tests/test_project_state.py::TestFieldPermissions::test_claude_can_write_runtime_fields PASSED
protocol_guard/tests/test_project_state.py::TestFieldPermissions::test_claude_cannot_write_locked_assets PASSED
protocol_guard/tests/test_project_state.py::TestFieldPermissions::test_claude_cannot_write_scene_phase PASSED
protocol_guard/tests/test_project_state.py::TestFieldPermissions::test_gpt_proposal_cannot_write_directly PASSED
protocol_guard/tests/test_project_state.py::TestFieldPermissions::test_user_approved_can_write_restricted_fields PASSED
protocol_guard/tests/test_project_state.py::TestApplyPatch::test_apply_claude_runtime_patch_succeeds PASSED
protocol_guard/tests/test_project_state.py::TestApplyPatch::test_apply_claude_restricted_patch_rejected PASSED
protocol_guard/tests/test_project_state.py::TestApplyPatch::test_apply_user_approved_restricted_patch_succeeds PASSED
protocol_guard/tests/test_project_state.py::TestApplyPatch::test_gpt_proposal_with_approval_succeeds PASSED
protocol_guard/tests/test_project_state.py::TestApplyPatch::test_gpt_proposal_without_approval_rejected PASSED
protocol_guard/tests/test_result.py::TestTechnicalResult::test_valid_main_results PASSED
protocol_guard/tests/test_result.py::TestTechnicalResult::test_evidence_recovered_not_main_result PASSED
protocol_guard/tests/test_result.py::TestTechnicalResult::test_technical_pass_is_valid PASSED
protocol_guard/tests/test_result.py::TestTechnicalResult::test_illegal_result_rejected PASSED
protocol_guard/tests/test_result.py::TestTechnicalResult::test_evidence_recovered_is_not_a_technical_result PASSED
protocol_guard/tests/test_result.py::TestEvidenceStatus::test_valid_evidence_statuses PASSED
protocol_guard/tests/test_result.py::TestEvidenceStatus::test_illegal_evidence_status_rejected PASSED
protocol_guard/tests/test_snapshot.py::TestFreezeTask::test_first_freeze_succeeds PASSED
protocol_guard/tests/test_snapshot.py::TestFreezeTask::test_verify_succeeds_on_unchanged_task PASSED
protocol_guard/tests/test_snapshot.py::TestFreezeTask::test_modified_task_fails_verification PASSED
protocol_guard/tests/test_snapshot.py::TestFreezeTask::test_existing_frozen_rejects_overwrite PASSED
protocol_guard/tests/test_snapshot.py::TestFreezeTask::test_freezing_nonexistent_dir_creates_it PASSED
protocol_guard/tests/test_task_schema.py::TestTaskCardValidation::test_valid_task_passes PASSED
... (remaining all PASSED)

============================= 38 passed in 0.26s ==============================
```

**38 通过, 0 失败.**

---

## 7. 失败测试及修复记录

无。首次运行全部通过。

---

## 8. 未实现模块 (Phase 2+)

根据审计报告，以下模块明确推迟到 MVP 之后:

- `gate.py` — confirm_then_execute 门禁 + direct_execute 白名单
- `retry_limit.py` — 2 轮回合限制 + ROOT_CAUSE_AUDIT 强制
- `transform_snapshot.py` — 对象变换前后比较
- `self_check.py` — Guard SHA256 防篡改
- `calibrate.py` — 自动校准测试
- `evidence/chain.py` — clean/debug/report 证据链验证
- `upload.py` — UPLOAD_NEXT 安全归档
- `cli.py` — 统一 CLI 入口

---

## 9. 合规检查

| 检查项 | 状态 |
|--------|------|
| 是否运行 Blender | **否** |
| 是否打开/保存任何 blend 文件 | **否** |
| 是否渲染 | **否** |
| 是否修改现有场景脚本 | **否** |
| 是否恢复相机任务 | **否** |
| 是否进入 L1-D | **否** |
| 是否创建 bypass 命令 | **否** |
| 是否实现完整 Guard | **否** (仅 Phase 1) |
| 是否修改 CLAUDE.md | **否** |
| 是否创建 EVIDENCE_RECOVERED 主结果 | **否** |
