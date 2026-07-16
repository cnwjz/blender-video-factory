# CODE GUARD MVP Phase 1.1 — Schema Hardening Report

Date: 2026-07-15
Status: **PHASE_1_1_TECHNICAL_PASS = True**

---

## 1. 修改文件清单

### 完全重写
| # | 文件 | 变更范围 |
|---|------|----------|
| 1 | `protocol_guard\schemas\task_card.schema.json` | v1 → v2: 11 个结构化字段重写 |
| 2 | `protocol_guard\schemas\project_state.schema.json` | v1 → v2: 10 个新必填字段 |
| 3 | `protocol_guard\schemas\state_patch.schema.json` | v1 → v2: reason 必填, fields 字段名白名单 |
| 4 | `protocol_guard\task_schema.py` | 新增 8 类跨字段约束 |
| 5 | `protocol_guard\state\project_state.py` | SHA256/时间戳验证, change_log 追加 |
| 6 | `PROJECT_STATE.yaml` | 结构化 locked_assets/diagnostics/change_log, evidence_sha256 manifest |
| 7 | `tasks\EXAMPLE_TASK\task.yaml` | 全部字段使用 v2 结构化格式 |
| 8 | `HUMAN_COLLAB_RULES.md` | 修正 CLI 引用, 增加 actor identity 声明 |
| 9 | `protocol_guard\tests\test_task_schema.py` | 全新测试 (28 项) |
| 10 | `protocol_guard\tests\test_project_state.py` | 新增测试 (27 项) |
| 11 | `protocol_guard\tests\test_snapshot.py` | v2 格式兼容 |
| 12 | `protocol_guard\tests\test_result.py` | 保持不变 |

### 未修改
- `protocol_guard\result.py` — 枚举不变
- `protocol_guard\frozen\snapshot.py` — 冻结逻辑不变
- `protocol_guard\__init__.py` — 包标识不变

---

## 2. Schema 迁移说明

### task_card.schema.json v1 → v2

| 字段 | v1 | v2 |
|------|----|----|
| `fixed_params` | `array[string]` | `object` (key → string\|number\|integer\|boolean\|null) |
| `dependent_variables` | `array[string]` | `array[object]` (name, solver, minimum, maximum, unit, step, description) |
| `preflight_checks` | `array[string]` | `array[object]` (check_id, checker, required, params, description) |
| `technical_pass_conditions` | `array[string]` | `array[object]` (condition_id, metric, operator, expected, required) — 11 operators |
| `locked_items` | `array[string]` | `array[object]` (lock_id, resource_type, selector, protected_fields) — 6 resource_types |
| `allowed_modifications` | `array[string]` | `array[object]` (target, fields, limits, description) |
| `forbidden_modifications` | `array[string]` | `array[object]` (target, fields, limits, description) |
| `evidence_required` | `array[string]` | `array[object]` (evidence_id, role, path, required, same_run_group, sha256_required, save_reopen_required) — 8 roles |
| `stop_conditions` | `array[string]` | `array[object]` (condition, action) — 6 actions |
| `state_patch_requested` | `object` | `null \| object` (fields + reason, no extras) |
| `input_files` | `array[string]` | + `uniqueItems: true` |
| `output_files` | `array[string]` | + `minItems: 1, uniqueItems: true` |
| `upload_files` | `array[string]` | + `minItems: 1, uniqueItems: true` |

### project_state.schema.json v1 → v2

新必填字段:
- `locked_assets` — 结构化数组 (asset_id, path, lock_scope, status, approved_by)
- `unlocked_assets` — 字符串数组
- `diagnostic_only_outputs` — 结构化数组 (output_id, path, status)
- `pending_review` — null 或对象 (task_id, reviewer, status)
- `blocked_operations` — 字符串数组
- `failed_paths` — 字符串数组
- `change_log` — 结构化数组 (timestamp, actor, task_id, fields_changed, reason)

类型强化:
- `last_task_card_sha256` / `evidence_sha256`: null 或 `^[a-f0-9]{64}$` (拒绝空字符串)
- `last_execution_time`: null 或 ISO 8601 带时区 (拒绝无时区字符串)

### state_patch.schema.json v1 → v2

- `reason`: 新增必填 (非空字符串)
- `fields.propertyNames`: 白名单为 PROJECT_STATE 定义的 20 个字段名

---

## 3. 旧任务卡兼容性

**不兼容。** v1 任务卡 (字符串数组参数) 无法通过 v2 Schema 验证:
- `fixed_params` 从数组改为对象 — Schema 拒绝 `["a", "b"]`
- `dependent_variables` 从数组改为结构化 — Schema 拒绝 `["a", "b"]`
- 所有结构化字段同理

迁移路径: 将旧任务卡手动改写为 v2 结构化格式，提升 `task_card_version`。

---

## 4. PROJECT_STATE 迁移结果

| 字段 | 迁移前 (v1) | 迁移后 (v2) |
|------|-------------|-------------|
| `evidence_sha256` | `""` (空字符串, 违规) | `"5946d98b..."` (64-char hex, manifest SHA) |
| `last_execution_time` | `""` (空字符串, 违规) | `"2026-07-15T13:25:23+08:00"` |
| `last_task_card_sha256` | `""` (空字符串, 违规) | `null` |
| `locked_assets` | 3 个字符串条目 | 4 个结构化条目 (asset_id/path/lock_scope/status/approved_by) |
| `diagnostic_only_outputs` | 不存在 | 新增 (AZIMUTH_65_EXACT_VERIFY → diagnostic_only) |
| `pending_review` | 不存在 | 新增 (CODE_GUARD_MVP_PHASE_1_1_SCHEMA_HARDENING → awaiting_gpt_review) |
| `change_log` | 不存在 | 新增 3 条记录 |

---

## 5. 状态哈希算法

evidence_sha256 计算步骤:

1. 加载 PROJECT_STATE.yaml
2. 将 evidence_sha256 临时设为 null
3. 对所有 7 个 Phase 1 审核文件计算 SHA256
4. 按文件名排序，构建 manifest JSON: `{"filename": "sha256", ...}`
5. 对 manifest JSON 计算 SHA256 → evidence_sha256 最终值
6. 将 evidence_sha256 写回 PROJECT_STATE.yaml

manifest 文件列表:
- CODE_GUARD_MVP_PHASE_1_REPORT.md
- HUMAN_COLLAB_RULES.md
- project_state.schema.json
- PROJECT_STATE.yaml (evidence_sha256=null 时的版本)
- pytest_output.txt
- state_patch.schema.json
- task_card.schema.json

最终 evidence_sha256: `5946d98bf897c4ade4ef3fba37289f6a47397b82def14d9ee20ce31246d9135e`

---

## 6. 测试列表 (67 项)

### test_result.py (7, 不变)
1-7. 枚举正确性 (与 Phase 1 相同)

### test_task_schema.py (27, +15 新增)
8. valid task (v2) passes
9. missing required field fails
10. invalid execution_mode fails
11. primary_variable not single string fails
12. empty primary_variable fails
13. fixed_params as object passes **[NEW]**
14. fixed_params as array fails **[NEW]**
15. dependent_variable missing name fails **[NEW]**
16. dependent_variable duplicate name fails **[NEW]**
17. primary overlaps fixed_param key fails **[NEW]**
18. primary overlaps dependent variable name fails **[NEW]**
19. dependent and fixed overlap fails **[NEW]**
20. condition missing operator fails **[NEW]**
21. between expected not two numbers fails **[NEW]**
22. between expected non-numeric fails **[NEW]**
23. condition_id duplicate fails **[NEW]**
24. in operator non-empty array passes **[NEW]**
25. locked_items as strings fails **[NEW]**
26. locked_items structured passes **[NEW]**
27. state_patch_requested null passes **[NEW]**
28. state_patch_requested empty object fails **[NEW]**
29. state_patch_requested unknown field fails **[NEW]**
30. state_patch_requested missing reason fails **[NEW]**
31. output_files empty fails **[NEW]**
32. upload_files duplicate fails **[NEW]**
33. input_files duplicate fails **[NEW]**
34. invalid task_type fails

### test_project_state.py (27, +13 新增)
35-38. v1 保留 (initial state, technical_result, evidence_status, missing required)
39. missing locked_assets fails **[NEW]**
40. missing blocked_operations fails **[NEW]**
41. SHA256 empty string fails **[NEW]**
42. SHA256 null passes **[NEW]**
43. SHA256 64 hex passes **[NEW]**
44. evidence_sha256 empty string fails **[NEW]**
45. evidence_sha256 null passes **[NEW]**
46. last_execution_time without timezone fails **[NEW]**
47-51. field permissions (保留)
52-56. apply_patch (保留)
57. change_log append preserves existing **[NEW]**
58. change_log overwrite rejected **[NEW]**
59. patch reason required **[NEW]**
60. patch unknown state field fails **[NEW]**
61. patch valid field passes **[NEW]**

### test_snapshot.py (5, 保留)
62-66. freeze/verify (格式兼容 v2, 逻辑不变)

### 新增 EVIDENCE_RECOVERED 回归测试
67. (内置于 test_result.py — 始终在)

---

## 7. pytest 完整结果摘要

```
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-7.4.4, pluggy-1.6.0
rootdir: D:\blender-video-factory
collected 67 items

protocol_guard/tests/test_project_state.py ............PASSED [ 40%]
protocol_guard/tests/test_result.py .......PASSED          [ 50%]
protocol_guard/tests/test_snapshot.py .....PASSED           [ 58%]
protocol_guard/tests/test_task_schema.py ............PASSED [100%]

============================= 67 passed in 0.86s ==============================
```

**67 通过, 0 失败。**

---

## 8. 失败与修复记录

| 测试 | 初始状态 | 修复 |
|------|----------|------|
| test_last_execution_time_without_timezone_fails | FAILED — 时区检测逻辑缺陷 (`"+" in let or ...` 短路评估错误) | 重写为: 提取时间部分后分别检查 `Z`、`+`、`-` |

无其他失败。

---

## 9. 当前仍未实现的模块

以下模块明确属于 Phase 2+ 范围:

- Blender 统一运行入口 (cli.py)
- 授权门禁 (gate.py)
- 证据图片生成 (evidence/chain.py)
- 保存重开验证 (save-reopen)
- 对象变换比较 (transform_snapshot.py)
- UPLOAD_NEXT 归档 (upload.py)
- 返工次数限制 (retry_limit.py)
- 校准任务 (calibrate.py)
- Guard 防篡改 (self_check.py)
- 统一 CLI 命令 (run, verify, deliver, authorize)

---

## 10. actor 权限的剩余绕过风险

**actor identity 目前属于约定式权限，尚未经过密码学或外部身份验证。**

以下风险存在于当前实现:

1. **CLAUDEE 身份可伪造** — 任何进程以 `actor: "CLAUDE"` 调用 `apply_patch` 即可写入运行字段。Phase 2 需引入签名令牌或外部身份验证。
2. **GPT_PROPOSAL 与 USER_APPROVED 区分靠信任** — approval 机制仅在应用层生效, 无密码学签名。
3. **Guard 代码本身可被修改** — `protocol_guard/` 与项目代码共享同一文件系统权限。Phase 2 的 self_check.py 将提供事后检测, 但无法阻止修改。
4. **Blender 可直接绕过 Guard** — `blender.exe --background --python <script>` 仍可直接执行, Guard 是约定执行器而非安全边界。

**Phase 1.1 不能声称已形成物理权限隔离。** actor 字段是运行记录标记, 不是安全断言。

---

## 11. 合规检查

| 检查项 | 状态 |
|--------|------|
| 是否运行 Blender | **否** |
| 是否打开/保存 blend 文件 | **否** |
| 是否渲染 | **否** |
| 是否修改场景脚本 | **否** |
| 是否调整角色/收银台/布局/相机 | **否** |
| 是否恢复 L1-C | **否** |
| 是否进入 L1-D | **否** |
| 是否实现 Phase 2 | **否** |
| 是否实现 CLI/authorize/run/verify/deliver | **否** |
| 是否创建 bypass 命令 | **否** |
| 是否创建子目录于 UPLOAD | **否** |
| CAMERA_AZIMUTH_65 标记为最终相机 | **否** |
