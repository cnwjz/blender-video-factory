# COLLAB PROTOCOL CODE ARCHITECTURE AUDIT

Date: 2026-07-15
Status: CODE_GUARD_PARTIALLY_FEASIBLE

---

## 1. Current Repository Facts

### 1.1 Environment

| Item | Value |
|------|-------|
| Python | 3.14.5 (system) |
| Blender Python | 3.13.9 (bundled) |
| Blender CLI | `blender.exe --background --python <script>` |
| OS | Windows 10 Pro |
| Project root | `D:\blender-video-factory\` |

### 1.2 Existing Code Inventory

| Pattern | Scripts using it |
|---------|-----------------|
| `bpy.ops.wm.read_factory_settings` + `open_mainfile` | 15+ scripts |
| `bpy.ops.wm.save_mainfile` | 15+ scripts |
| `get_world_bbox(mesh_list)` | **8 different definitions** across 8 scripts |
| `world_to_camera_view` projection | 4 scripts |
| SHA256 | 1 script (verify_azimuth_65.py) |
| Save-reopen validation | 4 scripts (L1A, L1A4, L1B, verify_azimuth) |
| UPLOAD_NEXT copy | 10+ scripts (inconsistent: some clear dir, some don't) |
| Transform snapshot + comparison | 2 scripts (L1A4, L1A5) |

### 1.3 Key Inconsistencies

1. `get_world_bbox` exists in 8 copies with different parameter names and edge case handling. No shared module.
2. UPLOAD_NEXT cleanup is inconsistent: some scripts `os.remove` individual files, some call `shutil.rmtree`, some use subdirectories.
3. `verify_azimuth_65.py` is the only script with SHA256, PIL debug overlay, and formal report generation — all others lack these.
4. No script validates its input file before execution.
5. No script prevents execution if locked objects would be modified.
6. All scripts assume they are the sole authority — no guard layer exists.

### 1.4 Existing Reusable Code

- `verify_azimuth_65.py`: SHA256 computation, PIL debug overlay, save-reopen param verification
- `L1A4_apply_idle.py`: Transform snapshot before/after, structured state JSON
- `framing_feasibility_audit.py`: Binary search over distance parameter, projection metrics collection
- `azimuth_feasibility.py`: Multi-configuration sweep with structured comparison table
- `build_library.py`: Per-character validation (14 checks), report generation from structured data

---

## 2. Module-by-Module Codeability Assessment

### Legend
- **FULL**: Can be completely automated in Python
- **PARTIAL**: Requires one human decision point (Y/N gate)
- **MANUAL**: Cannot be reliably automated; requires GPT or user judgment

| # | Module | Feasibility | Rationale |
|---|--------|-------------|-----------|
| 1 | task.yaml JSON Schema validation | **FULL** | Standard `jsonschema` library. All task card fields are well-defined. |
| 2 | PROJECT_STATE.yaml schema + write permissions | **FULL** | Schema validation: full. Write-permission enforcement: partial — a guard script can reject writes but cannot prevent `Write` tool from bypassing it. |
| 3 | task snapshot + SHA256 freeze | **FULL** | Copy task.yaml to `tasks/<id>/frozen_task.yaml`, compute SHA. Already demonstrated in verify_azimuth_65.py. |
| 4 | confirm_then_execute gate | **PARTIAL** | Guard creates `approvals/<task_id>.json` with `status: pending_understanding`. User/GPT sets `status: authorized`. Guard checks before executing. Claude Code can physically skip the check by not calling the guard. |
| 5 | direct_execute whitelist | **FULL** | Guard checks task type against whitelist. Purely deterministic. |
| 6 | Blender unified entry | **FULL** | `protocol_guard.cli run <task_id>` — validates, snapshots, launches `blender --background --python`, captures output, runs post-execution checks. Demonstrated pattern in 20+ scripts. |
| 7 | Input file + lock snapshot | **FULL** | SHA256 of input blend, JSON snapshot of locked object transforms. Both already implemented in separate scripts. |
| 8 | Post-execution transform comparison | **FULL** | Compare pre/post transform snapshots. Already implemented in L1A4_apply_idle.py and L1A_validate_append.py. |
| 9 | TECHNICAL_RESULT enum + evidence_status | **FULL** | Python `Enum` with 6 values (5 core + EVIDENCE_RECOVERED). Guard reads script output JSON and assigns result. |
| 10 | One-time evidence recovery | **FULL** | Re-read files, re-compute SHA, re-validate. If consistent → EVIDENCE_RECOVERED. If not → EVIDENCE_INVALID. |
| 11 | clean/debug/report same-source chain | **FULL** | Guard enforces that debug is derived from clean render. Clean render SHA recorded; debug must be generated from same file. |
| 12 | Save-reopen verification | **FULL** | Blend → save → reopen → compare params. Pattern demonstrated in 4 scripts. |
| 13 | Two-round retry limit | **FULL** | Counter in PROJECT_STATE.yaml incremented by guard on each TECHNICAL_FAIL. Third attempt blocked unless ROOT_CAUSE_AUDIT task type. |
| 14 | ROOT_CAUSE_AUDIT gate | **FULL** | Guard checks task type field. Deterministic. |
| 15 | UPLOAD_NEXT safe archive + whitelist | **FULL** | Guard archives old UPLOAD_NEXT to `UPLOAD_NEXT_archive/<task_id>/`, then writes only whitelisted files. |
| 16 | protocol_guard + schemas tamper check | **PARTIAL** | SHA256 of guard code stored at install time. Guard can verify itself on startup. But a determined Claude Code invocation can bypass `python -m protocol_guard` entirely and run `blender --background` directly. |
| 17 | Auto calibration test | **FULL** | `python -m protocol_guard.cli calibrate` — opens known scene, reads transforms, sets test camera, renders, verifies. Self-contained. |
| 18 | project_work_paused gate | **FULL** | Guard reads `PROJECT_STATE.yaml.phase_approved`. If False, rejects any task with `type != "audit"`. |

---

## 3. Content That CANNOT Be Code-Enforced

These must remain in short documentation (CLAUDE.md or PROTOCOL.md):

| Content | Why Not Codeable | Who Decides |
|---------|-----------------|-------------|
| Visual quality judgment | No programmatic metric exists for "looks like a supermarket" | GPT + User |
| Channel readability assessment | Can measure overlap ratio but not "can a human understand this" | GPT |
| Publish-worthiness | Subjective | User |
| Whether to continue after 2 failures | Business decision | User |
| Whether a parameter conflict requires a new task card | Requires understanding of intent | GPT |
| Whether skip_understanding_check should be toggled | Trust decision | User |

---

## 4. Bypass Risk Analysis

### 4.1 Can Claude Code skip the guard and run Blender directly?

**Yes.** The guard is a Python CLI wrapper. Claude Code can always execute `blender.exe --background --python <script>` directly, bypassing `python -m protocol_guard.cli run`.

**Mitigation**: The guard cannot be a hard security boundary. It is a **convention enforcer** that makes the correct path the easiest path. The true enforcement is:
1. CLAUDE.md rules that mandate guard usage
2. Post-hoc audit: PROJECT_STATE.yaml tracks `last_guard_run` timestamp; if a blend file is newer than the last guard run, evidence is suspect
3. GPT can detect bypass by checking whether `evidence/<task_id>/` exists

### 4.2 Can Claude Code modify the guard code itself?

**Yes.** The guard is Python code on disk with the same permissions as the project.

**Mitigation**: 
- Guard SHA256 stored in PROJECT_STATE.yaml at install time
- Guard startup self-check: `sha256(protocol_guard/)` vs stored value
- Guard/task mismatch → TECHNICAL_FAIL with "guard tampered"
- **Cannot prevent modification, only detect it after the fact**

### 4.3 Guard Location: Project-Internal vs External

| Location | Pros | Cons |
|----------|------|------|
| `D:\blender-video-factory\protocol_guard\` | Single repo, easier path management | Same write permissions as project, Claude Code can modify |
| `D:\bvf-protocol-guard\` | Separate from project, harder to accidentally modify | Needs PYTHONPATH management, another directory to maintain |

**Recommendation**: **Project-internal** (`D:\blender-video-factory\protocol_guard\`). The guard is a convention tool, not a security tool. Putting it externally adds complexity without meaningfully increasing protection. The SHA256 self-check is sufficient tamper detection.

---

## 5. Recommended Architecture

### 5.1 Minimum Viable Version (MVP)

Only these modules needed for v1:

```
D:\blender-video-factory\protocol_guard\
  __init__.py
  __main__.py          # python -m protocol_guard <command>
  cli.py               # argparse entry: validate, understand, authorize, run, verify, deliver
  schemas/
    task_card.json      # JSON Schema for task YAML
    project_state.json  # JSON Schema for PROJECT_STATE.yaml
  frozen/
    __init__.py
    snapshot.py         # SHA256 freeze of task + input blend
  evidence/
    __init__.py
    chain.py            # clean/debug/report verification
  state/
    __init__.py
    project_state.py    # read/write PROJECT_STATE.yaml with field-level permissions
  result.py             # TECHNICAL_RESULT enum
  upload.py             # UPLOAD_NEXT archive + whitelist delivery
tests/
  test_schemas.py
  test_freeze.py
  test_evidence.py
```

MVP explicitly defers: confirm_then_execute gate, retry counter, ROOT_CAUSE_AUDIT enforcement, auto calibration.

### 5.2 Full Version

Add after MVP validated:

```
protocol_guard/
  gate.py               # confirm_then_execute + direct_execute whitelist
  transform_snapshot.py # pre/post-execution object transform comparison
  retry_limit.py        # 2-round counter + ROOT_CAUSE_AUDIT enforcement
  self_check.py         # Guard SHA256 tamper detection
  calibrate.py          # Auto calibration test runner
```

### 5.3 Project Directory Additions

```
D:\blender-video-factory\
  PROJECT_STATE.yaml          # NEW: single source of truth
  tasks/                      # NEW: task cards
    <task_id>.yaml
  approvals/                  # NEW: authorization tokens
    <task_id>.json
  evidence/                   # NEW: per-task evidence
    <task_id>/
      clean.png
      debug.png
      report.md
      chain.json
  UPLOAD_NEXT_archive/        # NEW: safe archive
    <task_id>/
```

### 5.4 Module Dependency Order

```
schemas/         ← no deps
result.py        ← no deps
state/           ← schemas
frozen/          ← schemas
upload.py        ← no deps
evidence/        ← frozen
gate.py          ← state, frozen
calibrate.py     ← evidence, state
cli.py           ← all above
```

### 5.5 Files to Create (MVP)

```
D:\blender-video-factory\protocol_guard\__init__.py
D:\blender-video-factory\protocol_guard\__main__.py
D:\blender-video-factory\protocol_guard\cli.py
D:\blender-video-factory\protocol_guard\result.py
D:\blender-video-factory\protocol_guard\upload.py
D:\blender-video-factory\protocol_guard\schemas\task_card.json
D:\blender-video-factory\protocol_guard\schemas\project_state.json
D:\blender-video-factory\protocol_guard\frozen\__init__.py
D:\blender-video-factory\protocol_guard\frozen\snapshot.py
D:\blender-video-factory\protocol_guard\evidence\__init__.py
D:\blender-video-factory\protocol_guard\evidence\chain.py
D:\blender-video-factory\protocol_guard\state\__init__.py
D:\blender-video-factory\protocol_guard\state\project_state.py
D:\blender-video-factory\protocol_guard\tests\test_schemas.py
D:\blender-video-factory\protocol_guard\tests\test_freeze.py
D:\blender-video-factory\protocol_guard\tests\test_evidence.py
D:\blender-video-factory\PROJECT_STATE.yaml
D:\blender-video-factory\tasks\.gitkeep
D:\blender-video-factory\approvals\.gitkeep
D:\blender-video-factory\evidence\.gitkeep
```

### 5.6 Existing Files to Modify

```
D:\blender-video-factory\CLAUDE.md  — add: "All task execution must use python -m protocol_guard.cli run"
```

**No existing scripts or blend files need modification.** The guard wraps them, not replaces them. Existing scripts continue to work as `blender --background --python <script>`, which is what `protocol_guard.cli run` invokes internally.

### 5.7 Auto Test Plan

| Test | What It Proves |
|------|---------------|
| `test_schemas.py` | Valid task cards pass; invalid (missing field, wrong type) fail |
| `test_freeze.py` | SHA256 freeze is deterministic; modified task produces different hash |
| `test_evidence.py` | Clean SHA matches report; debug is derived from same clean; modified clean → EVIDENCE_INVALID |
| `test_calibrate.py` | Full calibrate flow: open scene → verify transforms → render → evidence → pass |

All tests runnable via `python -m pytest protocol_guard/tests/` without Blender (mock the Blender subprocess).

---

## 6. Migration Risk Assessment

| Risk | Level | Mitigation |
|------|-------|-----------|
| Adding guard breaks existing scripts | Low | Guard is a wrapper, not a replacement. Scripts unchanged. |
| Guard adds latency to task execution | Low | SHA256, snapshot, copy operations add < 2 seconds |
| PROJECT_STATE.yaml diverges from reality | Medium | Guard enforces state updates. Manual edits outside guard are detectable by timestamp mismatch. |
| UPLOAD_NEXT_archive accumulates disk usage | Low | Archive is compressed blend files + PNGs. < 5MB per task. Manual cleanup every 20 tasks. |
| Guard code bugs block all work | Medium | `python -m protocol_guard.cli bypass` emergency mode that skips all checks and logs a warning. |

---

## 7. Recommended Implementation Order

1. **Schemas + result.py + PROJECT_STATE.yaml** — foundation, no Blender dependency
2. **frozen/snapshot.py** — SHA256 freeze, already proven
3. **upload.py** — UPLOAD_NEXT archive + whitelist, replaces inconsistent per-script logic
4. **evidence/chain.py** — clean/debug/report verification
5. **cli.py validate + understand + run + verify + deliver** — connects all modules
6. **CLAUDE.md update** — mandate guard usage
7. **calibrate.py + auto tests** — prove the guard works end-to-end
8. **gate.py + retry_limit.py** — deferred to post-MVP

---

## 8. Final Conclusion

**CODE_GUARD_PARTIALLY_FEASIBLE**

**Can code**: Schema validation, SHA256 freezing, evidence chain verification, save-reopen validation, UPLOAD_NEXT safe delivery, retry counting, transform comparison, calibration testing — **14 of 18 modules (78%)**.

**Cannot code**: Preventing Claude Code from bypassing the guard entirely, enforcing permission boundaries at the OS level, visual quality judgment — **these remain convention-based and rely on CLAUDE.md + GPT oversight**.

**The guard is a convention enforcer, not a security tool.** It makes the correct path the default and the easiest option, but cannot physically prevent a `blender.exe --background` call. Tamper detection via SHA256 self-check is the strongest available protection within the current architecture.
