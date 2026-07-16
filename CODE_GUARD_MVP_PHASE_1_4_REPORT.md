# CODE GUARD MVP Phase 1.4 — Final Evidence Fix Report

Date: 2026-07-15
Status: **PHASE_1_4_TECHNICAL_PASS = True**

---

## 1. 两个问题修复说明

### 修复一：临时文件无条件清理

原问题: `save_state()` 在二次验证失败、读取异常、`os.replace()` 异常等路径中，临时文件未被删除。

修复: 使用 `tmp_path = None` + `try/finally` 模式。`os.replace()` 成功后设 `tmp_path = None`，`finally` 中无条件清理 `tmp_path`。

### 修复二：无自引用 evidence manifest

原问题: Phase 1.3 的 evidence manifest 将 `CODE_GUARD_MVP_PHASE_1_3_REPORT.md` 包含在文件哈希表中，但报告随后写入了所有文件 SHA256 值，导致报告 SHA256 无法稳定复现。同时 `PROJECT_STATE.yaml` 自身也被包含在 manifest 中，`evidence_sha256` 回写后形成循环。

修复: 新建独立的 `evidence_manifest.json`，仅包含 4 个非自引用文件 + canonical PROJECT_STATE (evidence_sha256=null) 的哈希。排除 `evidence_manifest.json` 自身、`PROJECT_STATE.yaml` 原始文件、报告中声明的报告自身 SHA256。

---

## 2. save_state 原子流程 (v1.4)

```
save_state(state_data, state_path)
  tmp_path = None
  try:
    candidate = deepcopy(state_data)
    validate_state(candidate) → fail? return (False, errors)
    tmp_path = tempfile.mkstemp(dir=target_dir)
    _write_yaml_unchecked(candidate, tmp_path)
    re_read = yaml.safe_load(tmp_path)
    validate_state(re_read) → fail? return (False, errors)  [finally cleans tmp]
    os.replace(tmp_path, state_path)
    tmp_path = None  [success — skip cleanup]
    return (True, [])
  except:
    return (False, errors)  [finally cleans tmp]
  finally:
    if tmp_path is not None and os.path.exists(tmp_path):
      os.remove(tmp_path)
```

---

## 3. 证据 manifest 算法

```
1. 准备候选 PROJECT_STATE (evidence_sha256=null)
2. canonical_json(state) → sort_keys=true, separators=(",",":"), ensure_ascii=false, UTF-8
3. SHA256(canonical_json) → project_state_normalization.sha256
4. 冻结 4 个交付文件 (之后不再修改)
5. SHA256(每个文件) → files map
6. 创建 evidence_manifest.json (确定性 JSON + 末尾一个换行)
7. SHA256(evidence_manifest.json) → 写入 PROJECT_STATE.evidence_sha256
8. save_state() 原子保存 PROJECT_STATE.yaml
9. verify_evidence_manifest() 完整验证
```

manifest 结构:
- schema_version
- task_id
- project_state_normalization: {method, sha256}
- files: {4 个文件名 → sha256}

不含: evidence_manifest.json 自身、PROJECT_STATE.yaml 原始哈希。

---

## 4. 修改文件清单

| # | 文件 | 变更 |
|---|------|------|
| 1 | `protocol_guard\state\project_state.py` | save_state try/finally, build/verify_evidence_manifest |
| 2 | `protocol_guard\tests\test_project_state.py` | 修复虚假测试 + 新增清理/manifest 测试 |
| 3 | `PROJECT_STATE.yaml` | Phase 1.4 一致性更新 |
| 4 | `evidence_manifest.json` | 新建 — 无自引用证据清单 |

---

## 5. 新增测试

### 临时文件清理 (6)
- test_reread_validation_failure_cleans_temp_file (真实 monkeypatch)
- test_reread_failure_preserves_existing_file
- test_read_exception_cleans_temp_file
- test_successful_save_leaves_no_temp_file
- (保留原有 6 个 save_state 测试)

### Manifest 验证 (8)
- test_manifest_no_self_reference
- test_report_modification_detected
- test_pytest_modification_detected
- test_state_non_sha_field_change_detected
- test_evidence_sha_writeback_passes
- test_sha_mismatch_detected
- test_task_id_mismatch_detected
- test_full_package_verifies

### 枚举回归 (2)

---

## 6. pytest 结果

见 pytest_output.txt。

最终值记录在:
- PROJECT_STATE.yaml (evidence_sha256)
- evidence_manifest.json

---

## 7. 仍未实现的 Phase 2 模块

- Blender 统一运行入口、授权门禁、证据链、保存重开、对象变换、UPLOAD_NEXT、返工限制、校准、防篡改

---

## 8. 合规

| 检查项 | 状态 |
|--------|------|
| 运行 Blender | 否 |
| 修改场景 | 否 |
| 修改 Schema | 否 |
| 进入 Phase 2 | 否 |
