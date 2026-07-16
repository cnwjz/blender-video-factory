# Phase 2A Implementation Task Draft

Date: 2026-07-15
Task ID: CODE_GUARD_PHASE_2A_1_IMPLEMENTATION
Status: **DRAFT — NOT FOR EXECUTION**

This document is a task card draft for GPT review. It must NOT be executed directly.
The user must transfer it to GPT, receive approval, and issue an authorized task card.

---

## 1. Task Summary

Implement the Phase 2A single-task execution gate MVP. This covers the full
validate → freeze → understand → authorize → preflight → mock execute → finalize
pipeline for a single Blender-free mock task.

---

## 2. Task Card Draft

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
output_files:
  - "protocol_guard/gate/__init__.py"
  - "protocol_guard/gate/conditions.py"
  - "protocol_guard/gate/freeze_bundle.py"
  - "protocol_guard/gate/understand.py"
  - "protocol_guard/gate/authorize.py"
  - "protocol_guard/gate/preflight.py"
  - "protocol_guard/gate/executor.py"
  - "protocol_guard/gate/finalize.py"
  - "protocol_guard/gate/cli.py"
  - "protocol_guard/schemas/understand_record.schema.json"
  - "protocol_guard/schemas/authorization.schema.json"
  - "protocol_guard/schemas/freeze_bundle.schema.json"
  - "protocol_guard/schemas/execution_result.schema.json"
  - "protocol_guard/gate/tests/__init__.py"
  - "protocol_guard/gate/tests/test_conditions.py"
  - "protocol_guard/gate/tests/test_freeze_bundle.py"
  - "protocol_guard/gate/tests/test_understand.py"
  - "protocol_guard/gate/tests/test_authorize.py"
  - "protocol_guard/gate/tests/test_preflight.py"
  - "protocol_guard/gate/tests/test_executor.py"
  - "protocol_guard/gate/tests/test_finalize.py"
  - "tasks/MOCK_EXECUTE_TEST/task.yaml"

primary_goal: "实现 Phase 2A 单任务执行门禁 MVP 的 7 阶段完整管道"
primary_variable: "gate_pipeline_integrity"

dependent_variables:
  - name: "toctou_detection"
    solver: "sha256_comparison"
  - name: "auth_consumption"
    solver: "boolean_toggle_with_file_persistence"

fixed_params:
  phase_1_locked: true
  blender_forbidden: true
  project_state_schema: "unchanged"
  task_card_schema: "unchanged"

locked_items:
  - lock_id: "phase_1_modules"
    resource_type: "protocol_code"
    selector: "protocol_guard/result.py, task_schema.py, state/project_state.py, frozen/snapshot.py"
    protected_fields:
      - "all"
  - lock_id: "phase_1_schemas"
    resource_type: "protocol_code"
    selector: "protocol_guard/schemas/task_card.schema.json, project_state.schema.json, state_patch.schema.json"
    protected_fields:
      - "all"
  - lock_id: "phase_1_tests"
    resource_type: "protocol_code"
    selector: "protocol_guard/tests/*"
    protected_fields:
      - "all"
  - lock_id: "project_state"
    resource_type: "file"
    selector: "PROJECT_STATE.yaml"
    protected_fields:
      - "workflow_phase"
      - "phase_approved"
      - "locked_assets"
      - "blocked_operations"
      - "diagnostic_only_outputs"
      - "scene_phase"

allowed_modifications:
  - target: "protocol_guard/gate/"
    fields:
      - "all_new_files"
  - target: "protocol_guard/schemas/"
    fields:
      - "new_files_only"
    limits:
      note: "Only add new Phase 2A schemas. Do not modify existing."
  - target: "PROJECT_STATE.yaml"
    fields:
      - "last_task_id"
      - "last_technical_result"
      - "evidence_status"
      - "last_execution_time"
      - "output_files"
      - "evidence_sha256"
      - "change_log"
    limits:
      note: "Only via apply_patch_document with CLAUDE actor during finalize."

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
      - "workflow_phase"
      - "phase_approved"
      - "locked_assets"
      - "blocked_operations"
      - "diagnostic_only_outputs"
      - "scene_phase"

preflight_checks:
  - check_id: "phase_1_tests_still_pass"
    checker: "pytest_run"
    required: true
    params:
      test_path: "protocol_guard/tests/"
  - check_id: "no_bpy_import_in_new_code"
    checker: "grep_absence"
    required: true
    params:
      pattern: "import bpy"
      path: "protocol_guard/gate/"
  - check_id: "no_blender_exe_in_new_code"
    checker: "grep_absence"
    required: true
    params:
      pattern: "blender.exe"
      path: "protocol_guard/gate/"
  - check_id: "no_phase_1_file_modified"
    checker: "sha256_verify"
    required: true

technical_pass_conditions:
  - condition_id: "all_phase_1_tests_pass"
    metric: "pytest_phase_1_passed_count"
    operator: "eq"
    expected: 121
    required: true
  - condition_id: "all_phase_2a_tests_pass"
    metric: "pytest_phase_2a_failed_count"
    operator: "eq"
    expected: 0
    required: true
  - condition_id: "mock_pipeline_completes"
    metric: "pipeline_stages_completed"
    operator: "eq"
    expected: 7
    required: true
  - condition_id: "no_phase_1_modifications"
    metric: "phase_1_files_modified"
    operator: "eq"
    expected: 0
    required: true

visual_intent: "不适用 — 无视觉输出"
visual_forbidden: "不适用 — 无视觉输出"

evidence_required:
  - evidence_id: "pytest_output"
    role: "log"
    path: "pytest_output.txt"
    required: true
  - evidence_id: "adversarial_output"
    role: "log"
    path: "adversarial_test_output.txt"
    required: true
  - evidence_id: "evidence_manifest"
    role: "json"
    path: "evidence_manifest.json"
    required: true

upload_dir: "reviews/UPLOAD_NEXT"
upload_files:
  - "pytest_output.txt"
  - "adversarial_test_output.txt"
  - "evidence_manifest.json"
  - "PROJECT_STATE.yaml"

stop_conditions:
  - condition: "any_phase_1_test_fails"
    action: "stop_current_task"
  - condition: "any_phase_1_file_modified"
    action: "stop_before_execution"
  - condition: "bpy_import_found_in_new_code"
    action: "stop_before_execution"
  - condition: "project_state_locked_fields_modified"
    action: "mark_constraint_conflict"

state_patch_requested:
  fields:
    last_task_id: "CODE_GUARD_PHASE_2A_1_IMPLEMENTATION"
  reason: "Record Phase 2A implementation task ID after successful completion"
```

---

## 3. Implementation Order

1. **Schemas first** — 4 new JSON Schema files (no code dependency)
2. **conditions.py** — stop condition evaluator (depends only on task_card.schema.json)
3. **freeze_bundle.py** — multi-artifact freeze (depends on snapshot.py + project_state.py)
4. **understand.py** — understanding record (depends on freeze_bundle.py)
5. **authorize.py** — authorization lifecycle (depends on freeze_bundle.py)
6. **preflight.py** — pre-execution gate (depends on all above)
7. **executor.py** — mock executor (no Blender, depends on task card)
8. **finalize.py** — post-execution audit (depends on all above)
9. **cli.py** — entry point (depends on all above)
10. **Tests** — written alongside each module, not after
11. **MOCK_EXECUTE_TEST task card** — used for integration test

---

## 4. Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Phase 2A code accidentally modifies Phase 1 file | Preflight SHA256 check of all Phase 1 files before execution |
| Authorization consumed but finalize crashes | Finalize re-runnable; auth consumption is idempotent |
| Mock executor accidentally imports bpy | Test asserts ImportError; preflight greps for import bpy |
| New schemas conflict with Phase 1 schema loading | All new schemas in same directory but with distinct $id |

---

## 5. GPT Review Questions

1. Is the 7-stage pipeline the correct scope for Phase 2A, or should any stage be deferred?
2. Is the authorization-as-independent-file design acceptable, or should it use PROJECT_STATE?
3. Should the mock executor do more than text file transformation (e.g., file copy with SHA verification)?
4. Is the test matrix (20 unit + 10 adversarial) sufficient for Phase 2A sign-off?
5. Should the CLI expose shell commands (`python -m protocol_guard.gate.cli validate ...`) or remain Python API only for Phase 2A?

---

## 6. NOT FOR EXECUTION

This document is a design draft for GPT review only.

Do NOT implement Phase 2A until:
1. GPT reviews and approves this design
2. User approves GPT's review
3. A formal Phase 2A implementation task card is issued
4. The task card passes validate → freeze → understand → authorize → preflight
