# Phase 2A R1 Current Capability Audit

Date: 2026-07-15
Task: CODE_GUARD_PHASE_2A_0_R1_DESIGN_CORRECTION
Previous: CODE_GUARD_PHASE_2A_0_SINGLE_TASK_GATE_DESIGN_AUDIT (GPT_REVIEW_FAILED)

---

## 1. Phase 1 Inventory

Same as v1 audit. 15 files in protocol_guard/, 121 passing tests. No changes.

---

## 2. Capability Gaps (Corrected)

### 2.1 Authorization Model (v1 ERROR)

v1 proposed `approvals/<task_id>.json` with a single `consumed` boolean toggled during finalize.

**R1 correction**: Authorization is an immutable record. Atomic claim is a separate artifact. Authorization scope excludes validate/freeze/understand/authorize itself.

### 2.2 PROJECT_STATE Write Boundary (v1 ERROR)

v1 proposed writing to real PROJECT_STATE.yaml during finalize via apply_patch_document().

**R1 correction**: Real PROJECT_STATE.yaml is READ-ONLY for entire Phase 2A-1. All state modification tests use temp dir fixtures. Real PROJECT_STATE write deferred to separate authorized phase.

### 2.3 Undeclared Modification Detection (v1 ERROR)

v1 proposed scanning only the output directory.

**R1 correction**: Repository-level before/after diff. All new/modified/deleted files detected. Path traversal and junction escape blocked.

### 2.4 Blender Disable (v1 INCOMPLETE)

v1 proposed only checking "no import bpy" and test asserting ImportError.

**R1 correction**: AST import scan, subprocess/Popen/os.system interception, string pattern check for bpy/blender/blender.exe, mock executor operation whitelist.

### 2.5 Evidence Directory (v1 ERROR)

v1 proposed writing to `evidence/<task_id>/` which could conflict with Phase 1 evidence.

**R1 correction**: Dedicated Phase 2A evidence directory: `reviews/PROTOCOL_IMPLEMENTATION_HISTORY/CODE_GUARD_PHASE_2A_1_IMPLEMENTATION/`

### 2.6 Bootstrapping (v1 ERROR)

v1 proposed validate→freeze→understand→authorize→preflight as gates for Phase 2A-1 itself.

**R1 correction**: Phase 2A-1 is implemented under existing GPT+User+Claude confirmation flow. New gate only tested against temp fixtures and mock tasks.

### 2.7 CLI (v1 ERROR)

v1 listed `gate/cli.py` as required module.

**R1 correction**: No CLI in Phase 2A-1. Python API only. CLI deferred.

---

## 3. Reusable Phase 1 Assets (with Source Evidence)

### 3.1 result.py — TechnicalResult + EvidenceStatus

- File: `protocol_guard/result.py`
- Functions: `TechnicalResult(Enum)`, `EvidenceStatus(Enum)`, `VALID_TECHNICAL_RESULTS`, `VALID_EVIDENCE_STATUSES`
- Current behavior: 5 main results + 3 evidence statuses, rejects EVIDENCE_RECOVERED as main result
- Tests: test_result.py (7 tests, all pass)
- Reuse: Direct import. No wrapper needed. All values are frozen by Phase 1 lock.
- Risk: None. Enum classes are immutable after definition.

### 3.2 task_schema.py — Task Card Validation

- File: `protocol_guard/task_schema.py`
- Functions: `validate_task_card(task_data, schema=None)`, `load_task_card(task_path)`, `validate_task_file(task_path)`
- Current behavior: JSON Schema structural check + 10 cross-field checks including allowed/forbidden conflict, state_patch field whitelist from PS schema
- Tests: test_task_schema.py (34 tests, all pass)
- Reuse: `validate_task_card()` for validate stage, `load_task_card()` for freeze stage
- Risk: `_load_ps_schema()` called on every validation loads from disk. Acceptable for Phase 2A volume. Cache if needed later.
- Private functions `_load_schema()`, `_load_ps_schema()`, `_get_ps_field_names()`, `_unique_ids()` are internal — Phase 2A must call only public API.

### 3.3 project_state.py — Core State Management

- File: `protocol_guard/state/project_state.py`
- Functions: `validate_state()`, `save_state()`, `apply_patch_document()`, `apply_patch()`, `validate_patch()`, `validate_patch_document()`, `load_state()`, `build_evidence_manifest()`, `verify_evidence_manifest()`, `_canonical_state_hash()`, `_sha256_file()`, `_sha256_bytes()`, `_canonical_json()`, `_validate_iso_datetime()`, `_write_yaml_unchecked()`
- Current behavior: Full state validation (Schema+datetime+SHA256+enum), atomic save with try/finally, field-level patch with CLAUDE whitelist, evidence manifest build/verify with no self-reference
- Tests: test_project_state.py (75 tests, all pass)
- Reuse: `validate_state()` for preflight, `_canonical_state_hash()` for freeze+preflight comparison, `_sha256_file()` for freeze+preflight+finalize, `_canonical_json()` for deterministic serialization
- Risk: `save_state()` and `apply_patch_document()` write to real PROJECT_STATE — Phase 2A-1 must NOT call these with real PROJECT_STATE path. Only used in tests with temp dir fixtures.
- Private functions: `_write_yaml_unchecked()` is private — Phase 2A must not call it. `_sha256_file()` and `_canonical_state_hash()` are private but stable utilities. Phase 2A should either import them (accepting private-API risk) or create thin wrappers. Recommended: thin public wrappers in gate modules that document the dependency.

### 3.4 snapshot.py — Task Freeze

- File: `protocol_guard/frozen/snapshot.py`
- Functions: `freeze_task(task_path, frozen_dir)`, `verify_frozen_task(task_path, frozen_dir)`
- Current behavior: Copies task.yaml + writes SHA256 file, rejects overwrite. Verify compares current SHA against stored.
- Tests: test_snapshot.py (5 tests, all pass)
- Reuse: `freeze_task()` for task card raw-byte SHA256 capture. `verify_frozen_task()` for TOCTOU detection.
- Risk: `freeze_task()` only handles individual task files. Phase 2A freeze_bundle wraps this with multi-artifact batch and post-freeze re-check. Private `_sha256_file()` duplicate exists here — Phase 2A should import from one canonical source (project_state.py).

### 3.5 JSON Schemas (Phase 1 — Immutable)

- Files: `task_card.schema.json`, `project_state.schema.json`, `state_patch.schema.json`
- Current behavior: Structural validation of task cards, project state, and state patches
- Reuse: Direct. No modification permitted.
- Risk: None. Schemas are validated by 121 existing tests.

---

## 4. New Phase 2A Modules (Corrected)

| # | Module | Purpose | Changed from v1 |
|---|--------|---------|-----------------|
| 1 | `gate/conditions.py` | Stop condition evaluator | Unchanged |
| 2 | `gate/freeze_bundle.py` | Multi-artifact freeze with post-freeze re-check | Added post-freeze re-check, reject on any change |
| 3 | `gate/understand.py` | Understanding record bound to freeze_bundle SHA256 | Binding corrected from task card SHA to freeze_bundle SHA |
| 4 | `gate/authorize.py` | Immutable authorization, scoped to preflight+claim+execute+finalize | Removed validate/freeze/understand/authorize from scope. Added all bindings |
| 5 | `gate/claim.py` | Atomic one-time authorization claim (NEW) | Was embedded in authorize/finalize. Now independent. |
| 6 | `gate/preflight.py` | Pre-execution gate | Added Blender-disable checks, path traversal checks |
| 7 | `gate/executor.py` | Mock executor in isolated temp workspace | Added AST+subprocess+string checks. Workspace isolation. |
| 8 | `gate/finalize.py` | Post-execution audit + evidence | Added repo-level diff. Does NOT write real PROJECT_STATE. |
| 9 | CLI entry | **REMOVED** — no CLI in Phase 2A-1 | Python API only |

---

## 5. New Schemas (Corrected)

| Schema | Changed from v1 |
|--------|-----------------|
| `freeze_bundle.schema.json` | Added input_files_raw_sha256 map, post_freeze_recheck_passed |
| `understand_record.schema.json` | Changed binding: freeze_bundle_sha256 (was task_card_sha256) |
| `authorization.schema.json` | Expanded to 12+ fields. Scope limited to preflight/claim/execute/finalize. Added GPT review reference. Removed consumed field (moved to claim). |
| `execution_result.schema.json` | Added attempt_id, claim_sha256, repo_diff section, blender_call_detected |
| `claim.schema.json` (NEW) | attempt_id, authorization_sha256, status enum (CLAIMED/EXECUTING/EXECUTED/FINALIZED/INDETERMINATE), claimed_at, process_id |

---

## 6. Real PROJECT_STATE Boundary (R1 NEW)

During Phase 2A-1 implementation and testing:

- Real `PROJECT_STATE.yaml` — **READ ONLY**. SHA256 recorded before implementation starts.
- All state-modifying tests use `tempfile.TemporaryDirectory()` fixtures.
- Real PROJECT_STATE write is a separate, future authorized phase.
- Phase 2A-1 completion criterion: real PROJECT_STATE SHA256 unchanged from pre-implementation baseline.

---

## 7. R1 Completion Criteria

1. Phase 1: 121 tests unchanged, all pass
2. Phase 2A: minimum 60 new tests, all pass
3. Adversarial: minimum 15 new tests, all pass
4. Real PROJECT_STATE.yaml: byte-identical before/after Phase 2A-1
5. All Phase 1 source, schema, test files: byte-identical before/after
6. Phase 1 evidence files: byte-identical before/after
7. No CLI created
8. No Blender executed
9. Mock executor operates entirely in temp workspaces
10. Authorization model: immutable record + atomic claim + crash recovery
11. Repository diff detects new/modified/deleted including path traversal
12. Blender disable: AST + subprocess + string checks all enforce
