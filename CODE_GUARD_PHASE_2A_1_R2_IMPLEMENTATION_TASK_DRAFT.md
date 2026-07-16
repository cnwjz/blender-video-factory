# Phase 2A R2 Implementation Task Draft

Date: 2026-07-15
Task ID: CODE_GUARD_PHASE_2A_1_IMPLEMENTATION
Status: **DRAFT R2 — NOT FOR EXECUTION**

---

## 1. R2 Validation Evidence

The task card YAML below was actually validated using the current disk implementations:

```
Call: validate_task_card(task_data)
is_valid: True
errors: []
Task YAML raw bytes SHA256: 3dd1f735f7d8e2b2e12031970f01cc97018cadce6c8ff9f6f6bee9f3c3abf043
Task YAML byte length: 9185
output_files count: 33
state_patch_requested: None
```

Validated against:
- `protocol_guard/schemas/task_card.schema.json` (disk, Phase 1 locked)
- `protocol_guard/task_schema.py` → `validate_task_card()` (disk, Phase 1 locked)

Cross-field checks verified:
- No parameter overlap (primary vs dependent vs fixed)
- dependent_variables names unique
- condition_ids unique
- lock_ids unique
- evidence_ids unique
- allowed/forbidden no target+field intersection
- state_patch_requested.fields whitelist check (not triggered — value is null)

All locked_items entries have no `notes` field (schema compliance).

---

## 2. Task Card (R2 Final)

```yaml
task_id: "CODE_GUARD_PHASE_2A_1_IMPLEMENTATION"
task_card_version: 1
protocol_version: "v1.0"
execution_mode: "confirm_then_execute"
task_type: "PROTOCOL_MAINTENANCE"

project_state_file: "PROJECT_STATE.yaml"
input_files:
  - "PROJECT_STATE.yaml"
  - "protocol_guard/result.py"
  - "protocol_guard/task_schema.py"
  - "protocol_guard/state/project_state.py"
  - "protocol_guard/frozen/snapshot.py"
  - "protocol_guard/schemas/task_card.schema.json"
  - "protocol_guard/schemas/project_state.schema.json"
  - "protocol_guard/schemas/state_patch.schema.json"
output_files:
  - "protocol_guard/gate/__init__.py"
  - "protocol_guard/gate/freeze_bundle.py"
  - "protocol_guard/gate/understand.py"
  - "protocol_guard/gate/authorize.py"
  - "protocol_guard/gate/claim.py"
  - "protocol_guard/gate/attempt_state.py"
  - "protocol_guard/gate/preflight.py"
  - "protocol_guard/gate/executor.py"
  - "protocol_guard/gate/finalize.py"
  - "protocol_guard/gate/conditions.py"
  - "protocol_guard/gate/recovery.py"
  - "protocol_guard/schemas/freeze_bundle.schema.json"
  - "protocol_guard/schemas/understand_record.schema.json"
  - "protocol_guard/schemas/authorization.schema.json"
  - "protocol_guard/schemas/claim.schema.json"
  - "protocol_guard/schemas/attempt_state.schema.json"
  - "protocol_guard/schemas/execution_result.schema.json"
  - "protocol_guard/gate/tests/__init__.py"
  - "protocol_guard/gate/tests/test_freeze_bundle.py"
  - "protocol_guard/gate/tests/test_understand.py"
  - "protocol_guard/gate/tests/test_authorize.py"
  - "protocol_guard/gate/tests/test_claim.py"
  - "protocol_guard/gate/tests/test_attempt_state.py"
  - "protocol_guard/gate/tests/test_preflight.py"
  - "protocol_guard/gate/tests/test_executor.py"
  - "protocol_guard/gate/tests/test_finalize.py"
  - "protocol_guard/gate/tests/test_conditions.py"
  - "protocol_guard/gate/tests/test_recovery.py"
  - "protocol_guard/gate/tests/test_integration.py"
  - "protocol_guard/gate/tests/test_adversarial.py"
  - "protocol_guard/gate/tests/fixtures/__init__.py"
  - "protocol_guard/gate/tests/fixtures/mock_input.txt"
  - "tasks/MOCK_EXECUTE_TEST/task.yaml"

primary_goal: "实现 Phase 2A R2 单任务执行门禁。7 阶段管道。真实 PROJECT_STATE 全程只读。不可变 claim + 原子 attempt_state。独立证据目录。仓库级差异检测。executor 导入白名单。"
primary_variable: "gate_pipeline_integrity"

dependent_variables:
  - name: "toctou_detection"
    solver: "sha256_comparison_with_post_freeze_recheck"
  - name: "auth_claim_atomicity"
    solver: "os_open_O_CREAT_O_EXCL"
  - name: "attempt_state_atomicity"
    solver: "tempfile_revalidate_os_replace"
  - name: "crash_recovery_correctness"
    solver: "attempt_state_transition_rules"
  - name: "blender_disable_coverage"
    solver: "import_whitelist_plus_ast_scan_plus_subprocess_intercept"

fixed_params:
  phase_1_locked: true
  real_ps_readonly: true
  blender_forbidden: true
  no_cli: true
  python_api_only: true

locked_items:
  - lock_id: "phase_1_all_modules"
    resource_type: "protocol_code"
    selector: "protocol_guard/result.py, protocol_guard/task_schema.py, protocol_guard/state/project_state.py, protocol_guard/frozen/snapshot.py"
    protected_fields:
      - "all"
  - lock_id: "phase_1_all_schemas"
    resource_type: "protocol_code"
    selector: "protocol_guard/schemas/task_card.schema.json, protocol_guard/schemas/project_state.schema.json, protocol_guard/schemas/state_patch.schema.json"
    protected_fields:
      - "all"
  - lock_id: "phase_1_all_tests"
    resource_type: "protocol_code"
    selector: "protocol_guard/tests/"
    protected_fields:
      - "all"
  - lock_id: "real_project_state"
    resource_type: "file"
    selector: "PROJECT_STATE.yaml"
    protected_fields:
      - "all_bytes"
      - "all_fields"
  - lock_id: "phase_1_evidence_files"
    resource_type: "file"
    selector: "evidence_manifest.json, pytest_output.txt, adversarial_test_output.txt, CODE_GUARD_MVP_PHASE_1_4_REPORT.md, CODE_GUARD_PHASE_1_4_SOURCE_SNAPSHOT.txt"
    protected_fields:
      - "all_bytes"
  - lock_id: "phase_1_blend_scenes"
    resource_type: "file"
    selector: "projects/"
    protected_fields:
      - "all"

allowed_modifications:
  - target: "protocol_guard/gate/"
    fields:
      - "all_new_files"
  - target: "protocol_guard/schemas/"
    fields:
      - "new_files_only"
  - target: "tasks/"
    fields:
      - "new_task_yaml_only"
  - target: "reviews/PROTOCOL_IMPLEMENTATION_HISTORY/CODE_GUARD_PHASE_2A_1_IMPLEMENTATION/"
    fields:
      - "all_new_evidence_files"
  - target: "reviews/UPLOAD_NEXT/"
    fields:
      - "copy_deliverables_only"

forbidden_modifications:
  - target: "protocol_guard/result.py"
    fields:
      - "any"
  - target: "protocol_guard/task_schema.py"
    fields:
      - "any"
  - target: "protocol_guard/state/project_state.py"
    fields:
      - "any"
  - target: "protocol_guard/frozen/snapshot.py"
    fields:
      - "any"
  - target: "protocol_guard/schemas/task_card.schema.json"
    fields:
      - "any"
  - target: "protocol_guard/schemas/project_state.schema.json"
    fields:
      - "any"
  - target: "protocol_guard/schemas/state_patch.schema.json"
    fields:
      - "any"
  - target: "protocol_guard/tests/"
    fields:
      - "any"
  - target: "PROJECT_STATE.yaml"
    fields:
      - "any"
  - target: "evidence_manifest.json"
    fields:
      - "any"
  - target: "projects/"
    fields:
      - "any"
  - target: "CODE_GUARD_MVP_PHASE_1_4_REPORT.md"
    fields:
      - "any"
  - target: "CODE_GUARD_PHASE_1_4_SOURCE_SNAPSHOT.txt"
    fields:
      - "any"
  - target: "reviews/"
    fields:
      - "any_except_explicitly_allowed"

preflight_checks:
  - check_id: "phase_1_tests_still_pass"
    checker: "pytest_run"
    required: true
    params:
      test_path: "protocol_guard/tests/"
  - check_id: "real_ps_unchanged"
    checker: "sha256_verify"
    required: true
  - check_id: "phase_1_source_unchanged"
    checker: "sha256_verify"
    required: true
  - check_id: "phase_1_schemas_unchanged"
    checker: "sha256_verify"
    required: true
  - check_id: "executor_no_forbidden_imports"
    checker: "ast_scan"
    required: true
  - check_id: "no_cli_created"
    checker: "file_absence"
    required: true
    params:
      path: "protocol_guard/gate/cli.py"

technical_pass_conditions:
  - condition_id: "phase_1_tests_all_pass"
    metric: "pytest_phase_1_failed"
    operator: "eq"
    expected: 0
    required: true
  - condition_id: "phase_2a_tests_all_pass"
    metric: "pytest_phase_2a_failed"
    operator: "eq"
    expected: 0
    required: true
  - condition_id: "adversarial_all_pass"
    metric: "adversarial_failed"
    operator: "eq"
    expected: 0
    required: true
  - condition_id: "integration_test_passes"
    metric: "integration_result"
    operator: "eq"
    expected: "TECHNICAL_PASS"
    required: true
  - condition_id: "real_ps_unchanged"
    metric: "real_ps_sha256_match"
    operator: "sha256_match"
    expected: true
    required: true
  - condition_id: "phase_1_files_unchanged"
    metric: "phase_1_files_modified"
    operator: "eq"
    expected: 0
    required: true
  - condition_id: "no_blender_called"
    metric: "blender_call_detected"
    operator: "eq"
    expected: false
    required: true
  - condition_id: "no_undeclared_modifications"
    metric: "undeclared_modification_count"
    operator: "eq"
    expected: 0
    required: true

visual_intent: "不适用 — 纯代码任务，无视觉输出"
visual_forbidden: "不适用 — 纯代码任务，无视觉输出"

evidence_required:
  - evidence_id: "pytest_output"
    role: "log"
    path: "reviews/PROTOCOL_IMPLEMENTATION_HISTORY/CODE_GUARD_PHASE_2A_1_IMPLEMENTATION/pytest_output.txt"
    required: true
  - evidence_id: "adversarial_output"
    role: "log"
    path: "reviews/PROTOCOL_IMPLEMENTATION_HISTORY/CODE_GUARD_PHASE_2A_1_IMPLEMENTATION/adversarial_test_output.txt"
    required: true
  - evidence_id: "execution_result"
    role: "json"
    path: "reviews/PROTOCOL_IMPLEMENTATION_HISTORY/CODE_GUARD_PHASE_2A_1_IMPLEMENTATION/execution_result.json"
    required: true
  - evidence_id: "evidence_manifest"
    role: "json"
    path: "reviews/PROTOCOL_IMPLEMENTATION_HISTORY/CODE_GUARD_PHASE_2A_1_IMPLEMENTATION/evidence_manifest.json"
    required: true

upload_dir: "reviews/UPLOAD_NEXT"
upload_files:
  - "CODE_GUARD_PHASE_2A_1_REPORT.md"
  - "CODE_GUARD_PHASE_2A_1_SOURCE_SNAPSHOT.txt"
  - "CODE_GUARD_PHASE_2A_1_PROTECTED_FILES_INTEGRITY.json"
  - "pytest_output.txt"
  - "adversarial_test_output.txt"
  - "execution_result.json"
  - "evidence_manifest.json"

stop_conditions:
  - condition: "any_phase_1_test_fails"
    action: "stop_current_task"
  - condition: "any_phase_1_file_modified"
    action: "mark_constraint_conflict"
  - condition: "real_project_state_modified"
    action: "mark_constraint_conflict"
  - condition: "bpy_or_blender_detected_in_new_code"
    action: "stop_before_execution"
  - condition: "undeclared_file_modification_detected"
    action: "mark_technical_fail"
  - condition: "cli_file_created"
    action: "mark_spec_invalid"

state_patch_requested: null
```

---

## 3. Implementation Order

1. Schemas (6 new JSON Schema files)
2. conditions.py (no deps beyond schemas)
3. freeze_bundle.py (depends on snapshot.py + project_state.py)
4. understand.py (depends on freeze_bundle.py)
5. authorize.py (validates, does not create — depends on freeze_bundle + understand)
6. claim.py (O_CREAT|O_EXCL — depends on authorize)
7. attempt_state.py (atomic transitions — depends on claim)
8. recovery.py (depends on claim + attempt_state + executor result)
9. preflight.py (depends on freeze_bundle + authorize + claim)
10. executor.py (import whitelist + AST + subprocess intercept)
11. finalize.py (repo diff + evidence — does NOT write real PS)
12. Tests alongside each module
13. test_adversarial.py (standalone)
14. test_integration.py (full pipeline)
15. MOCK_EXECUTE_TEST/task.yaml

---

## 4. NOT FOR EXECUTION

Requires:
1. GPT review and approval of all 13 R2 corrections
2. User authorization
3. Formal implementation task card issuance
4. Real PROJECT_STATE SHA256 baseline recording before any file creation
5. Phase 1 file integrity baseline recording before any file creation
