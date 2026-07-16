# CODE GUARD MVP Phase 1.3 — Persistence Coherence Report

Date: 2026-07-15
Status: **PHASE_1_3_TECHNICAL_PASS = True**

---

## 1. 三个问题修复说明

### 修复一：安全且原子的 save_state

原问题: `save_state()` 直接写入 YAML，绕过 `validate_state()`。

修复后的原子流程:
1. `deepcopy(state_data)` → 深复制，不修改入参
2. `validate_state(candidate)` → 验证失败则返回 `(False, errors)`，不创建任何文件
3. 写入同目录临时文件 (`.project_state_tmp_*.yaml`)
4. 重新读取临时文件
5. `validate_state(re_read)` → 二次验证重读数据
6. `os.replace(tmp_path, state_path)` → 原子替换
7. 任一步失败 → 删除临时文件，保留原文件不变

新增私有函数 `_write_yaml_unchecked()` 仅供 `save_state()` 内部验证后调用。

### 修复二：GPT_PROPOSAL 来源日志

原问题: `original_actor` 被覆盖为 `USER_APPROVED` 后无法区分来源。

修复:
- `apply_patch_document()` 保留 `original_actor` 变量
- `original_actor == "GPT_PROPOSAL"` → change_log.actor = `USER_APPROVED`, reason = `[GPT_PROPOSAL via USER_APPROVED] <原reason>`
- 直接 `USER_APPROVED` → 无 GPT 前缀，reason 保持原样

### 修复三：PROJECT_STATE 任务一致性

- `last_task_id`: CODE_GUARD_MVP_PHASE_1_3_PERSISTENCE_COHERENCE
- `pending_review.task_id`: 匹配
- `output_files`: 5 个 Phase 1.3 文件
- `change_log`: 追加 Phase 1.2 历史记录 + Phase 1.3 当前记录
- `evidence_sha256`: 重新计算的 manifest SHA256
- `last_execution_time`: 本轮完成时的带时区时间

---

## 2. save_state 原子保存流程

```
save_state(state_data, state_path)
  │
  ├─ 1. candidate = copy.deepcopy(state_data)
  ├─ 2. validate_state(candidate) → fail? return (False, errors)
  ├─ 3. tempfile.mkstemp(dir=target_dir)
  ├─ 4. _write_yaml_unchecked(candidate, tmp_path)
  ├─ 5. re_read = yaml.safe_load(open(tmp_path))
  ├─ 6. validate_state(re_read) → fail? delete tmp, return (False, errors)
  ├─ 7. os.replace(tmp_path, state_path) → atomic on same filesystem
  └─ Any exception → delete tmp, return (False, errors)
```

---

## 3. GPT_PROPOSAL 日志修复

| 场景 | change_log.actor | change_log.reason |
|------|-----------------|-------------------|
| GPT_PROPOSAL + USER_APPROVED | USER_APPROVED | [GPT_PROPOSAL via USER_APPROVED] \<reason\> |
| 直接 USER_APPROVED | USER_APPROVED | \<reason\> |
| CLAUDE | CLAUDE | \<reason\> |

---

## 4. PROJECT_STATE 一致性结果

| 字段 | 值 |
|------|-----|
| last_task_id | CODE_GUARD_MVP_PHASE_1_3_PERSISTENCE_COHERENCE |
| pending_review.task_id | 匹配 ✓ |
| evidence_status | VALID |
| output_files | 5 个 Phase 1.3 文件 |
| change_log entries | 5 (init + P1 + P1.1 + P1.2 + P1.3) |
| last_execution_time | > Phase 1.2 completion |

---

## 5. 新增测试

### save_state (7)
- test_save_valid_state_succeeds
- test_save_invalid_state_fails
- test_invalid_state_does_not_create_file
- test_invalid_write_does_not_corrupt_existing_file
- test_save_state_does_not_modify_input
- test_saved_state_revalidates_on_reload
- test_temp_file_validation_catches_corruption

### GPT_PROPOSAL logging (3)
- test_gpt_proposal_log_reason_has_source_prefix
- test_direct_user_approved_no_gpt_prefix
- test_gpt_proposal_log_actor_is_user_approved

### PROJECT_STATE coherence (6)
- test_last_task_id_matches_pending_review
- test_output_files_belong_to_phase_1_3
- test_change_log_has_phase_1_2_record
- test_change_log_has_phase_1_3_record
- test_last_execution_time_after_phase_1_2
- test_current_project_state_passes_schema

### Enum regression (2)
- test_five_main_results_unchanged
- test_three_evidence_statuses_unchanged

---

## 6. pytest 结果

```
============================= test session starts =============================
collected 108 items

All 108 tests PASSED in 1.47s.
============================= 108 passed in 1.47s =============================
```

**108 通过, 0 失败。**

---

## 7. 独立对抗测试结果

```
RESULTS: 23 passed, 0 failed
```

---

## 8. evidence manifest 算法与最终 SHA256

算法:
1. 加载最终候选 PROJECT_STATE，临时将 evidence_sha256 设为 null
2. 对 5 个交付文件计算 SHA256
3. 按文件名排序生成 JSON manifest: `{"file": "sha256", ...}`
4. 对 manifest JSON 计算 SHA256 → evidence_sha256

最终值: `31ec1ce2f3e113e008e43606a5095aa2883f7f6e3c8126db26fabfdec8e9ee09`

Manifest 文件:
| 文件 | SHA256 |
|------|--------|
| adversarial_test_output.txt | 123a098cc591d59887eb70b17ce9c2c234708c76461ad86d47e868fdbdae79c6 |
| CODE_GUARD_MVP_PHASE_1_3_REPORT.md | 73390396632eb6f63089abb39289afcf6b6132a68e7ea0c49dab02e03d0fe6a7 |
| CODE_GUARD_MVP_PHASE_1_3_SOURCE_SNAPSHOT.txt | a34be2fa05e2aaaa2c391b945c3f5cd70629adbc5974e6272cd7923ec39b7f31 |
| PROJECT_STATE.yaml | 08be6e06fa4777c18a94135aa0af93fb9164215fc8336f9550c31db845cdaaa6 |
| pytest_output.txt | 359aca6ae69f013e4d8fc584c3fca6de0781a359ac265f123802c89cbc7ff5c9 |

---

## 9. 仍未实现的 Phase 2 模块

- Blender 统一运行入口 (cli.py)
- 授权门禁 (gate.py)
- 证据链验证 (evidence/chain.py)
- 保存重开验证
- 对象变换比较 (transform_snapshot.py)
- UPLOAD_NEXT 归档 (upload.py)
- 返工次数限制 (retry_limit.py)
- 校准任务 (calibrate.py)
- Guard 防篡改 (self_check.py)

---

## 10. 合规检查

| 检查项 | 状态 |
|--------|------|
| 是否运行 Blender | **否** |
| 是否修改场景 | **否** |
| 是否进入 Phase 2 | **否** |
| 是否创建 bypass | **否** |
| 是否修改 Schema | **否** |
| 是否修改 task_schema.py | **否** |
