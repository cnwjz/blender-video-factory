# CODE GUARD MVP Phase 1.2 — Patch Integrity Report

Date: 2026-07-15
Status: **PHASE_1_2_TECHNICAL_PASS = True**

---

## 1. 六个漏洞修复说明

### 修复一：state_patch_requested 字段白名单
- **task_card.schema.json**: `state_patch_requested.fields.propertyNames` 增加 19 个合法 PROJECT_STATE 字段名枚举
- **task_schema.py**: `validate_task_card()` 调用 `_get_ps_field_names()` 从 project_state.schema.json 动态读取合法字段，逐 key 验证

### 修复二：CLAUDE 权限改为严格白名单
- **project_state.py** `validate_patch()`: CLAUDE 分支改为 `blocked = requested - CLAUDE_WRITABLE`，任何不在白名单内的字段一律拒绝
- `project_id` 等字段不再能通过 "不在 RESTRICTED_FIELDS 中" 的边缘情况写入

### 修复三：apply_patch_document 原子写入
- 新增 `validate_patch_document()` 验证完整 patch 文档 Schema
- 新增 `apply_patch_document()` 9 步原子流程:
  1. 验证 patch 文档 Schema → 2. 验证 actor 权限 → 3-4. 深复制 → 5. 应用字段 → 6. 自动生成 change_log → 7. 验证候选状态 → 8. 返回
- 旧 `apply_patch()` 保留为兼容包装器

### 修复四：change_log 自动追加
- **state_patch.schema.json**: fields 白名单移除 `change_log`
- **project_state.py** `apply_patch_document()`: 自动生成带 timestamp/actor/task_id/fields_changed/reason 的日志条目
- `validate_patch_document()` 拒绝 fields 中包含 change_log 的补丁
- GPT_PROPOSAL 通过审批后 actor 记录为 USER_APPROVED

### 修复五：严格日期时间验证
- **project_state.py**: 使用 `datetime.fromisoformat()` + `utcoffset() is not None` 验证
- 拒绝: 无效日期 (月 99, 时 25)、无时区、空字符串
- 接受: Z 结尾、+HH:MM 偏移
- **project_state.schema.json**: `format: "date-time"` 应用于 last_execution_time、change_log[].timestamp、locked_assets[].approved_at

### 修复六：allowed/forbidden 修改权限冲突检测
- **task_schema.py**: target 相同 + fields 有交集 → 拒绝，逐字段报告冲突
- 仅检测完全相同的 target 字符串，通配符解析留到 Phase 2

### 修复七：PROJECT_STATE 记录纠正
- 第三条 change_log actor: CLAUDE → SYSTEM_MIGRATION
- reason 追加 "Authorized by user instruction for Phase 1.1 schema migration."

---

## 2. 修改文件清单

| # | 文件 | 变更类型 |
|---|------|----------|
| 1 | `protocol_guard\schemas\state_patch.schema.json` | +task_id required, -change_log from fields |
| 2 | `protocol_guard\schemas\task_card.schema.json` | state_patch_requested.fields.propertyNames whitelist |
| 3 | `protocol_guard\schemas\project_state.schema.json` | date-time format, approved_at nullable |
| 4 | `protocol_guard\task_schema.py` | PS field whitelist, allowed/forbidden conflict |
| 5 | `protocol_guard\state\project_state.py` | full rewrite: strict whitelist, apply_patch_document, datetime validation, auto change_log |
| 6 | `protocol_guard\tests\test_task_schema.py` | +6 new tests |
| 7 | `protocol_guard\tests\test_project_state.py` | +24 new tests |
| 8 | `PROJECT_STATE.yaml` | change_log actor fix, last_task_id, pending_review |

---

## 3. 新 apply_patch_document 流程

```
apply_patch_document(state_data, patch_doc, approval=None)
  │
  ├─ 1. validate_patch_document(patch_doc)   ← Schema + change_log rejection
  ├─ 2. validate_patch(actor, fields)         ← strict whitelist
  ├─ 3. candidate = copy.deepcopy(state_data)
  ├─ 4. applied_fields = copy.deepcopy(fields)
  ├─ 5. candidate.update(applied_fields)
  ├─ 6. auto-generate change_log entry
  ├─ 7. validate_state(candidate)             ← full Schema + datetime + SHA256 + enum
  ├─ 8. return (True, candidate, [])
  │
  └─ Any failure → return (False, state_data, errors)
```

---

## 4. CLAUDE 字段白名单

CLAUDE 仅可写入:
- last_task_id
- last_task_card_sha256
- last_technical_result
- evidence_status
- evidence_sha256
- output_files
- last_execution_time

任何其他字段 (包括 project_id、未知字段) → 拒绝。

---

## 5. change_log 自动生成规则

- 外部 patch fields 禁止包含 change_log
- 每次成功 apply 自动追加一条: {timestamp, actor, task_id, fields_changed[], reason}
- fields_changed 自动排序
- GPT_PROPOSAL 经审批后 actor=USER_APPROVED, reason 标注来源
- 失败时不产生日志

---

## 6. 严格时间验证规则

- 使用 `datetime.fromisoformat()` 真实解析
- 必须 `utcoffset() is not None`
- 接受: Z 后缀, +HH:MM, -HH:MM
- 拒绝: 空字符串, 无时区, 无效日期 (月=99, 时=25 等)

---

## 7. 修改权限冲突检测规则

- target 相同 + fields 有交集 → 失败
- target 相同 + fields 无交集 → 通过
- target 不同 → 通过
- 仅检测完全相同的 target 字符串 (通配符留 Phase 2)

---

## 8. PROJECT_STATE 纠正结果

- change_log[2].actor: CLAUDE → SYSTEM_MIGRATION
- change_log[2].reason: 追加 "Authorized by user instruction for Phase 1.1 schema migration."
- last_task_id: CODE_GUARD_MVP_PHASE_1_2_PATCH_INTEGRITY
- pending_review.task_id: 更新

---

## 9. 新增测试清单

### test_task_schema.py (+6)
- test_state_patch_unknown_ps_field_fails
- test_state_patch_known_ps_field_passes
- test_allowed_forbidden_same_target_same_field_fails
- test_allowed_forbidden_same_target_no_overlap_passes
- test_allowed_forbidden_different_target_passes

### test_project_state.py (+24)
- test_invalid_datetime_month_99_fails
- test_invalid_datetime_hour_25_fails
- test_valid_z_time_passes
- test_valid_offset_time_passes
- test_disk_project_state_by_schema
- test_change_log_entry_3_actor_is_system_migration
- test_claude_cannot_write_project_id
- test_claude_cannot_write_unknown_field
- test_claude_writes_valid_runtime_field_passes
- test_atomic_failure_no_partial_change
- test_invalid_enum_atomic_failure
- test_invalid_evidence_status_atomic_failure
- test_invalid_sha256_atomic_failure
- test_does_not_modify_original_state
- test_does_not_modify_original_patch
- test_change_log_in_fields_rejected
- test_auto_change_log_appended_on_success
- test_no_change_log_appended_on_failure
- test_gpt_proposal_without_approval_rejected
- test_gpt_proposal_with_approval_succeeds
- test_user_approved_writes_restricted_succeeds
- test_candidate_state_passes_schema_after_apply
- test_legacy_apply_patch_compatibility
- test_patch_task_id_required

---

## 10. pytest 完整结果摘要

```
============================= test session starts =============================
collected 90 items

All 90 tests PASSED in 1.20s.

Breakdown:
  test_project_state.py: 44 passed
  test_result.py:        7 passed
  test_snapshot.py:      5 passed
  test_task_schema.py:  34 passed

============================= 90 passed in 1.20s ==============================
```

**90 通过, 0 失败。**

---

## 11. Adversarial Test 完整结果

```
=== Phase 1.2 Adversarial Integrity Test ===

1. Unknown state patch rejected        PASS
2. CLAUDE project_id patch rejected    PASS
3. Invalid enum patch rejected atomically
     invalid enum rejected              PASS
     original state unchanged (no partial) PASS
     no change_log appended on failure  PASS
4. Invalid datetime rejected           PASS
5. Allowed and forbidden conflict rejected PASS
6. Input dictionaries unchanged
     original state_data unchanged      PASS
     original patch_doc unchanged       PASS
7. Successful patch appends exactly one log
     patch succeeded                    PASS
     exactly one log appended           PASS
     log entry has timestamp            PASS
     log entry has actor                PASS
     log entry has task_id              PASS
     log entry has fields_changed       PASS
     log entry has reason               PASS
8. change_log in fields explicitly rejected PASS

RESULTS: 17 passed, 0 failed
```

---

## 12. 失败与修复记录

无。首次运行全部通过。

---

## 13. 仍未实现的 Phase 2 模块

- Blender 统一运行入口 (cli.py)
- 授权门禁 (gate.py)
- 证据链验证 (evidence/chain.py)
- 保存重开验证
- 对象变换比较 (transform_snapshot.py)
- UPLOAD_NEXT 归档 (upload.py)
- 返工次数限制 (retry_limit.py)
- 校准任务 (calibrate.py)
- Guard 防篡改 (self_check.py)
- 通配符 selector 解析

---

## 14. 合规检查

| 检查项 | 状态 |
|--------|------|
| 是否运行 Blender | **否** |
| 是否修改场景 | **否** |
| 是否进入 Phase 2 | **否** |
| 是否创建 bypass | **否** |
| 是否修改 HUMAN_COLLAB_RULES.md | **否** |
| 是否修改五种技术结果 | **否** |
| 是否修改三种 evidence status | **否** |
