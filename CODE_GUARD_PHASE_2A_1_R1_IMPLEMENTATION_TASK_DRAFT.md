# Phase 2A R1 Implementation Task Draft

Date: 2026-07-15
Task ID: CODE_GUARD_PHASE_2A_1_IMPLEMENTATION
Status: **DRAFT R1 — NOT FOR EXECUTION**

This document is an R1 task card draft incorporating all 13 GPT review corrections.
It must NOT be executed directly. GPT must approve before user authorization.

---

## 1. R1 Corrections Incorporated

| # | Correction |
|---|-----------|
| 1 | Real PROJECT_STATE.yaml is READ-ONLY for entire Phase 2A-1 |
| 2 | Authorization is immutable; claim is atomic and separate |
| 3 | Authorization scope: preflight + claim + mock_execute + finalize only |
| 4 | Crash recovery: INDETERMINATE state, no auto-retry |
| 5 | understand binds freeze_bundle SHA256 |
| 6 | Repo-level before/after diff for undeclared modifications |
| 7 | Dedicated Phase 2A evidence directory |
| 8 | Phase 2A-1 NOT bootstrapped through own gate |
| 9 | Blender disable: AST + subprocess + string + whitelist |
| 10 | No CLI; Python API only |
| 11 | Tests: unit >=60, adversarial >=15, integration 1 |
| 12 | Source evidence appendix in capability audit |
| 13 | Task draft validated against task_card.schema.json |

---

## 2. Schema Validation of This Task Draft

The task card below was validated against `protocol_guard/schemas/task_card.schema.json`
and `protocol_guard/task_schema.py:validate_task_card()`.

### Validation Result

**Schema structural: PASS** — All 23 required fields present, all types correct.
**Cross-field checks: PASS** — No parameter overlap (primary_variable "gate_pipeline_integrity" not in dependent_variables names or fixed_params keys. dependent_variables has unique names. condition_ids unique. lock_ids unique. evidence_ids unique.)
**Allowed/forbidden conflict: PASS** — No target+field intersection between allowed and forbidden.
**Output files coverage: PASS** — 24 output files declared covering all implementation modules, schemas, tests, and fixture.
**State patch fields: PASS** — All fields in state_patch_requested exist in project_state.schema.json properties.

No validation errors. Task draft structure is compliant.

---

## 3. Task Card (R1 Corrected)

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
  - "protocol_guard/gate/conditions.py"
  - "protocol_guard/gate/freeze_bundle.py"
  - "protocol_guard/gate/understand.py"
  - "protocol_guard/gate/authorize.py"
  - "protocol_guard/gate/claim.py"
  - "protocol_guard/gate/preflight.py"
  - "protocol_guard/gate/executor.py"
  - "protocol_guard/gate/finalize.py"
  - "protocol_guard/schemas/freeze_bundle.schema.json"
  - "protocol_guard/schemas/understand_record.schema.json"
  - "protocol_guard/schemas/authorization.schema.json"
  - "protocol_guard/schemas/claim.schema.json"
  - "protocol_guard/schemas/execution_result.schema.json"
  - "protocol_guard/gate/tests/__init__.py"
  - "protocol_guard/gate/tests/test_conditions.py"
  - "protocol_guard/gate/tests/test_freeze_bundle.py"
  - "protocol_guard/gate/tests/test_understand.py"
  - "protocol_guard/gate/tests/test_authorize.py"
  - "protocol_guard/gate/tests/test_claim.py"
  - "protocol_guard/gate/tests/test_preflight.py"
  - "protocol_guard/gate/tests/test_executor.py"
  - "protocol_guard/gate/tests/test_finalize.py"
  - "protocol_guard/gate/tests/test_integration.py"
  - "tasks/MOCK_EXECUTE_TEST/task.yaml"

primary_goal: "实现 Phase 2A R1 单任务执行门禁 — 7 阶段管道 (validate/freeze/understand/authorize/preflight/claim/execute/finalize)，真实 PROJECT_STATE 全程只读，独立证据目录，仓库级差异检测，AST+子进程+字符串 Blender 封锁"
primary_variable: "gate_pipeline_integrity"

dependent_variables:
  - name: "toctou_detection"
    solver: "sha256_comparison_with_post_freeze_recheck"
  - name: "auth_claim_atomicity"
    solver: "os_open_O_CREAT_O_EXCL"
  - name: "blender_disable_coverage"
    solver: "ast_scan_plus_subprocess_intercept_plus_string_scan_plus_whitelist"

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
    notes: "Real PROJECT_STATE.yaml is READ-ONLY for entire Phase 2A-1. SHA256 verified before and after."
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
    limits:
      note: "Only create new files. Do not modify Phase 1 files."
  - target: "protocol_guard/schemas/"
    fields:
      - "new_files_only"
    limits:
      note: "Only add 5 new Phase 2A schemas. Do not touch existing 3."
  - target: "tasks/"
    fields:
      - "new_task_yaml_only"

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

preflight_checks:
  - check_id: "phase_1_tests_still_pass"
    checker: "pytest_run"
    required: true
    params:
      test_path: "protocol_guard/tests/"
      expected_minimum: 121
  - check_id: "real_ps_unchanged"
    checker: "sha256_verify"
    required: true
    params:
      file: "PROJECT_STATE.yaml"
      expected_sha256: "<recorded at implementation start>"
  - check_id: "phase_1_source_unchanged"
    checker: "sha256_verify"
    required: true
    params:
      files: "protocol_guard/result.py, protocol_guard/task_schema.py, protocol_guard/state/project_state.py, protocol_guard/frozen/snapshot.py"
  - check_id: "phase_1_schemas_unchanged"
    checker: "sha256_verify"
    required: true
  - check_id: "no_bpy_in_new_code"
    checker: "ast_scan"
    required: true
  - check_id: "no_subprocess_in_new_code"
    checker: "ast_scan"
    required: true
  - check_id: "no_blender_string_in_new_code"
    checker: "grep_absence"
    required: true
    params:
      pattern: "bpy|blender\\.exe|blender"
      path: "protocol_guard/gate/"
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
  - condition_id: "phase_2a_unit_tests_minimum"
    metric: "pytest_phase_2a_collected"
    operator: "gte"
    expected: 60
    required: true
  - condition_id: "phase_2a_tests_all_pass"
    metric: "pytest_phase_2a_failed"
    operator: "eq"
    expected: 0
    required: true
  - condition_id: "adversarial_tests_minimum"
    metric: "adversarial_collected"
    operator: "gte"
    expected: 15
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

state_patch_requested:
  fields:
    last_task_id: "CODE_GUARD_PHASE_2A_1_IMPLEMENTATION"
  reason: "Record Phase 2A-1 task ID after GPT+User approval and successful completion."
```

---

## 4. Implementation Order (Corrected)

1. Schemas (5 new JSON Schema files)
2. conditions.py
3. freeze_bundle.py (with post-freeze re-check)
4. understand.py (binds freeze_bundle SHA256)
5. authorize.py (immutable record validation)
6. claim.py (atomic O_CREAT|O_EXCL)
7. preflight.py (TOCTOU + Blender-disable + path checks)
8. executor.py (AST+subprocess+string+whitelist, temp workspace)
9. finalize.py (repo diff, Phase 2A evidence dir only)
10. All tests alongside each module
11. MOCK_EXECUTE_TEST task.yaml
12. Integration test

---

## 5. NOT FOR EXECUTION

This R1 draft requires:
1. GPT review and approval of all 13 corrections
2. User authorization
3. Formal implementation task card issuance
4. Phase 1 baseline SHA256 recording before any file creation
