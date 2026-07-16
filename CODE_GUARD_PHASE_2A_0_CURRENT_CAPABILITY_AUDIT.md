# Phase 2A Current Capability Audit

Date: 2026-07-15
Task: CODE_GUARD_PHASE_2A_0_SINGLE_TASK_GATE_DESIGN_AUDIT

---

## 1. Phase 1 Inventory — Complete Module List

```
protocol_guard/
  __init__.py                          # Package marker
  result.py                            # TechnicalResult + EvidenceStatus enums
  task_schema.py                       # Task card YAML loader + validator
  state/
    __init__.py                        # Package marker
    project_state.py                   # Core: validate_state, save_state, apply_patch_document,
                                       #        build_evidence_manifest, verify_evidence_manifest,
                                       #        validate_patch, validate_patch_document,
                                       #        apply_patch (legacy wrapper)
  frozen/
    __init__.py                        # Package marker
    snapshot.py                        # freeze_task + verify_frozen_task (SHA256 copy+verify)
  schemas/
    task_card.schema.json              # 23 required fields, structured v2 format
    project_state.schema.json          # 20+ required fields, SHA256/date-time formats
    state_patch.schema.json            # actor + task_id + fields + reason, field whitelist
  tests/
    test_result.py                     # 7 tests — enum correctness
    test_task_schema.py                # 34 tests — task card validation
    test_project_state.py              # 75 tests — state, patches, save_state, manifest
    test_snapshot.py                   # 5 tests — freeze/verify
```

External to protocol_guard/:
```
PROJECT_STATE.yaml                    # Locked Phase 1 state
evidence_manifest.json                # Phase 1.4 manifest (no self-reference)
tasks/EXAMPLE_TASK/task.yaml          # v2 example task card
HUMAN_COLLAB_RULES.md                 # Collaboration rules (<900 chars)
```

---

## 2. Capability Map Against Phase 2A Requirements

### 2.1 validate

| Sub-capability | Status | Location |
|---------------|--------|----------|
| Task card Schema validation | **EXISTS** | task_schema.py:validate_task_card() — JSON Schema + 10 cross-field checks |
| Cross-field parameter overlap | **EXISTS** | task_schema.py — primary/dependent/fixed overlap detection |
| Allowed/forbidden conflict | **EXISTS** | task_schema.py — same-target field intersection check |
| State patch field whitelist | **EXISTS** | task_schema.py:_get_ps_field_names() from PS schema |
| PROJECT_STATE Schema validation | **EXISTS** | project_state.py:validate_state() — Schema + datetime + SHA256 + enum |
| Stop condition evaluation | **NOT YET** | stop_conditions are defined in task card but never evaluated by code |
| Allowed modification range check | **NOT YET** | Allowed modifications have target + fields but no runtime enforcement |
| Blocked operations check | **NOT YET** | PROJECT_STATE.blocked_operations is stored but not cross-referenced |

### 2.2 freeze

| Sub-capability | Status | Location |
|---------------|--------|----------|
| Task card SHA256 freeze | **EXISTS** | snapshot.py:freeze_task() — copy + SHA256, reject overwrite |
| Task card change detection | **EXISTS** | snapshot.py:verify_frozen_task() — SHA256 comparison |
| Pre-execution PROJECT_STATE canonical SHA | **EXISTS (partial)** | project_state.py:_canonical_state_hash() — but not persisted as freeze artifact |
| Input file SHA256 | **NOT YET** | No function to hash declared input_files before execution |
| Multi-artifact freeze atomic batch | **NOT YET** | No single freeze call that snapshots task + state + inputs together |

### 2.3 understand

| Sub-capability | Status | Location |
|---------------|--------|----------|
| Structured understanding record | **NOT YET** | No schema or module exists |
| Binding to frozen task SHA256 | **NOT YET** | — |
| Conflict detection in task spec | **PARTIAL** | task_schema.py errors are validation-time only; no "understand" artifact |

### 2.4 authorize

| Sub-capability | Status | Location |
|---------------|--------|----------|
| Authorization data structure | **NOT YET** | No schema or module |
| One-time use token | **NOT YET** | — |
| Scope binding (task_id, SHA chain) | **NOT YET** | — |
| Expiry conditions | **NOT YET** | — |
| Consumption tracking | **NOT YET** | — |

### 2.5 preflight

| Sub-capability | Status | Location |
|---------------|--------|----------|
| Phase 1 lock check | **PARTIAL** | project_state.py can read phase_approved but no gate function |
| Task card unchanged since freeze | **EXISTS (callable)** | snapshot.py:verify_frozen_task() |
| PROJECT_STATE unchanged | **PARTIAL** | _canonical_state_hash() exists but not compared to freeze snapshot |
| Input files unchanged | **NOT YET** | — |
| Authorization exists + unused | **NOT YET** | — |
| Blocked_operations check | **NOT YET** | — |
| Locked_assets modification check | **NOT YET** | — |
| Diagnostic-only output misuse check | **NOT YET** | — |

### 2.6 mock execute

| Sub-capability | Status | Location |
|---------------|--------|----------|
| Blender-free task runner | **NOT YET** | — |
| Execution result JSON | **NOT YET** | — |
| Output file SHA256 | **EXISTS (callable)** | _sha256_file() in project_state.py |

### 2.7 finalize

| Sub-capability | Status | Location |
|---------------|--------|----------|
| Structured execution result | **NOT YET** | — |
| Actual vs declared output comparison | **NOT YET** | — |
| Undeclared file modification detection | **NOT YET** | — |
| Authorization consumed state | **NOT YET** | — |
| Stop condition evaluation against results | **NOT YET** | — |

---

## 3. Reusable Phase 1 Assets (Direct)

| Asset | Can be reused for |
|-------|-------------------|
| `result.py` — TechnicalResult + EvidenceStatus enums | All Phase 2A result codes. Already complete. |
| `task_schema.py:validate_task_card()` | validate step |
| `task_schema.py:load_task_card()` | freeze step (load before hash) |
| `project_state.py:validate_state()` | preflight step |
| `project_state.py:_canonical_state_hash()` | freeze step (capture state) + preflight (comparison) |
| `project_state.py:_sha256_file()` | freeze + preflight + finalize |
| `project_state.py:save_state()` | finalize (update task record atomically) |
| `project_state.py:apply_patch_document()` | finalize (if state update needed) |
| `project_state.py:validate_patch()` | authorize (scope check) |
| `project_state.py:build_evidence_manifest()` | finalize (output evidence) |
| `snapshot.py:freeze_task()` | freeze step |
| `snapshot.py:verify_frozen_task()` | preflight step |
| `task_card.schema.json` | validate step (unchanged) |
| `project_state.schema.json` | validate + preflight (unchanged) |
| `state_patch.schema.json` | finalize (unchanged) |

---

## 4. Capability Gaps — New Modules Required

| # | Gap | Must be new module | Rationale |
|---|-----|-------------------|-----------|
| 1 | Stop condition evaluator | `gate/conditions.py` | Needs to map stop_conditions to actions |
| 2 | Multi-artifact freeze bundle | `gate/freeze_bundle.py` | task + state + inputs in one atomic snapshot |
| 3 | Understanding record schema + writer | `gate/understand.py` | New data structure, new JSON Schema |
| 4 | Authorization record schema + lifecycle | `gate/authorize.py` | One-time token, scope binding, consumption |
| 5 | Preflight gate (all checks in order) | `gate/preflight.py` | Orchestrates all pre-execution checks |
| 6 | Mock executor | `gate/executor.py` | Blender-free file operations |
| 7 | Finalizer (results + evidence + state update) | `gate/finalize.py` | Post-execution audit |
| 8 | CLI entry point | `gate/cli.py` or `__main__.py` | Single entry for all gate commands |

---

## 5. New Schemas Required (Independent, not modifying Phase 1)

| Schema | Purpose | Phase 1 impact |
|--------|---------|---------------|
| `schemas/understand_record.schema.json` | Structured understanding | None — new file |
| `schemas/authorization.schema.json` | One-time auth token | None — new file |
| `schemas/freeze_bundle.schema.json` | Multi-artifact freeze manifest | None — new file |
| `schemas/execution_result.schema.json` | Structured task result | None — new file |

All four are independent Phase 2A schemas. No Phase 1 schema requires modification.

---

## 6. Existing Defects in Phase 1

**None found that require modification.** Phase 1 code is functionally complete for its designed scope.

Two observations (not defects, do not require Phase 1 changes):
1. `snapshot.py:freeze_task()` uses `shutil.copy2` for task card copying — adequate for Phase 2A reuse
2. `project_state.py` has both `_sha256_file()` and `snapshot.py` has its own `_sha256_file()` — duplicate but not a defect; Phase 2A should import from one canonical source

---

## 7. PROJECT_STATE Read/Write in Phase 2A

| Field | Phase 2A access | Notes |
|-------|----------------|-------|
| `phase_approved` | **READ ONLY** | Must be true to proceed |
| `workflow_phase` | **READ ONLY** | Must be "code_guard_phase_1_locked" |
| `blocked_operations` | **READ ONLY** | Preflight cross-reference |
| `locked_assets` | **READ ONLY** | Preflight cross-reference |
| `diagnostic_only_outputs` | **READ ONLY** | Preflight cross-reference |
| `last_task_id` | **WRITE (finalize)** | Update to executed task ID |
| `last_technical_result` | **WRITE (finalize)** | Set result after execution |
| `evidence_status` | **WRITE (finalize)** | Set after evidence verification |
| `last_execution_time` | **WRITE (finalize)** | Update timestamp |
| `output_files` | **WRITE (finalize)** | Record output evidence |
| `evidence_sha256` | **WRITE (finalize)** | Manifest SHA after execution |
| `change_log` | **WRITE (finalize)** | Append execution record |

All writes use existing `apply_patch_document()` with CLAUDE actor. No new write paths.

---

## 8. Authorization Storage Decision

**Independent file per authorization** (`approvals/<task_id>.json`), not in PROJECT_STATE.

Rationale:
- Authorization is a transient, consumable artifact — not permanent project state
- Independent files avoid self-referencing in evidence manifest
- One file per authorization prevents multi-task state coupling
- Consumption tracking: the file itself is deleted or marked consumed

---

## 9. Self-Reference Prevention

The Phase 1.4 pattern (evidence_manifest.json excludes itself and PROJECT_STATE raw hash) is reused:
- Freeze bundle: records task + state hash, NOT freeze_bundle.json itself
- Authorization: records task + state + input hashes, NOT authorization.json itself
- Execution result: records output hashes, NOT result.json itself

Each artifact is independently verifiable against its predecessor in the chain.

---

## 10. Phase 2A Completion Criteria

1. All 7 gate stages have pytest tests (at minimum: 1 pass + 1 fail each)
2. Mock executor completes without importing bpy or calling blender.exe
3. Full mock task: validate → freeze → understand → authorize → preflight → execute → finalize → all pass
4. Independent adversarial test validates: TOCTOU detection, double-authorization rejection, crash recovery
5. Zero modifications to Phase 1 source files
6. Zero modifications to Phase 1 schemas
7. PROJECT_STATE remains locked throughout (phase_approved=true, workflow_phase unchanged)
8. All new schemas pass jsonschema validation
