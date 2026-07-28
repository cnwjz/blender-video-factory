# Ground Contact Formal Lock Record

```text
FIELD_GROUP: GROUND_CONTACT
TASK_ID: GROUND_CONTACT_FORMAL_LOCK_SYNC
DATE: 2026-07-26
FINAL_LOCK_STATUS: FORMALLY_LOCKED
FINAL_LOCK_APPROVAL: USER_EXPLICITLY_APPROVED
FINAL_LOCK_APPROVAL_DATE: 2026-07-26
MASTER_MAP_VERSION: R77
DESIGN_VERSION: R2
```

## Lock Authority

```text
USER_FORMAL_APPROVAL: 批准正式锁定 Ground Contact 字段组
LOCK_BASIS: USER_FORMAL_APPROVAL
LOCK_DATE: 2026-07-26
```

## Locked Scope

```text
Ground Contact Design R2 (FORMALLY_LOCKED)
Ground Contact Implementation (COMPLETED)
  — pre-open config validation
  — _check_ground_contact (scene, target, per_target_result)
  — Root condition reading (read-only from existing checks)
  — scene.objects materialization + root resolution
  — _collect_geometry_scope_objects reuse
  — evaluated depsgraph + evaluated_get + to_mesh + matrix_world + to_mesh_clear
  — world-space lowest Z aggregation
  — PASS/FAIL/ERROR/NOT_CHECKED
  — entry integration (open_blend_and_get_scene)
  — _collect_target_errors integration
Ground Contact CPython focused tests (73 passed, 0 failed)
Ground Contact Blender 5.1.2 validation (14/14 scenarios, entry PASS+FAIL)
Legacy scope test alignment (Facing I3A + Scene Basic)
Collection Rules locked structure restoration
Technical protocol_guard regression (1796 passed, 0 failed, 2 skipped)
Full unfiltered protocol_guard regression (see Final Results)
User formal lock approval (GRANTED)
```

## Final Design Contract

```text
Config fields:
  target.ground_contact.ground_z
  target.ground_contact.ground_contact_tolerance

Config semantics:
  Both absent/null → NOT_CHECKED
  Exactly one present → pre-open INPUT ERROR
  Both present → check enabled

geometry_scope:
  SELF_MESH / DESCENDANT_MESHES / SELF_AND_DESCENDANT_MESHES
  (reuses target.geometry_scope)

Geometry source:
  bpy.context.evaluated_depsgraph_get()
  obj.evaluated_get(depsgraph)
  evaluated.to_mesh()
  evaluated.matrix_world
  world-space vertex Z via matrix_world @ vertex.co
  evaluated.to_mesh_clear() in finally

Comparison:
  absolute_error = abs(actual_lowest_z - ground_z)
  absolute_error <= tolerance → PASS
  absolute_error > tolerance → FAIL

failure_code (3):
  GROUND_CONTACT_OUT_OF_TOLERANCE
  NO_EVALUATED_GEOMETRY
  NON_FINITE_EVALUATED_VERTEX_Z

error_type:
  GROUND_CONTACT_COMPUTATION_ERROR

operation (12):
  READ_SCENE_OBJECTS
  RESOLVE_ROOT_OBJECT
  READ_ROOT_CHILDREN
  READ_DESCENDANT_CHILDREN
  READ_DESCENDANT_TYPE
  GET_EVALUATED_DEPSGRAPH
  EVALUATED_GET
  TO_MESH
  TO_MESH_CLEAR
  READ_EVALUATED_MATRIX_WORLD
  READ_MESH_VERTICES
  TRANSFORM_VERTEX_TO_WORLD_SPACE

Result dict forms (6):
  NOT_CHECKED (2 keys)
  PASS (6 keys)
  FAIL/TOLERANCE (7 keys)
  FAIL/NO_GEOM (4 keys)
  FAIL/NON_FINITE (5 keys)
  ERROR (4 keys)

Forbidden:
  object.bound_box
  raw mesh vertices without world-space transform
  root_obj.matrix_world for ground contact
  save, render, transform modification, collection modification
```

## Final Results

```text
Ground Contact CPython focused:  73 passed, 0 failed, 0 skipped, exit 0
Ground Contact Blender wrapper:  25 passed, 0 failed, 0 skipped, exit 0
Ground Contact Blender scenarios: 14/14 passed
  entry PASS case: passed
  entry FAIL case: passed
Collection Rules Scope Guard:    68 passed, 0 failed, 0 skipped, exit 0
Technical protocol_guard:        1796 passed, 0 failed, 2 skipped, exit 0
  (TestLintMasterMap excluded before R77 status sync)
Full unfiltered protocol_guard:  1812 passed, 0 failed, 0 errors, 2 skipped, exit 0
TRUE_BLOCKING_ISSUES:             0
```

## Frozen Production Hashes

```text
protocol_guard/phase3_min/blender_scene_reader.py:
  SHA256: 91ef4f316b49e13cea8834bf5742cab1238d319b3a0b40bee05ac41e04047550
protocol_guard/phase3_min/asset_scene_preflight_check.py:
  SHA256: 4f71b9b5ffff119daf4abe7d503485a19a8cf31491c0a6b42d589c03b3f29ea9
protocol_guard/phase3_min/asset_scene_preflight_core.py:
  SHA256: 9b5daa1cf7a8c568f418bf2a8b2a93cab09b7513ec3b47b47c4896e823982f10
```

## Frozen Test Hashes

```text
protocol_guard/phase3_min/tests/test_asset_scene_preflight_ground_contact.py:
  SHA256: c9ed8ad350740d0e99b94c17bcf0d76129139733b7a9d3bd7ed1599659620d14
protocol_guard/phase3_min/tests/blender_ground_contact_validation_runner.py:
  SHA256: a7f34b45deb1c5e5a6b603af0fa97868136a0f03756ce91122886b3f726fd21c
protocol_guard/phase3_min/tests/test_asset_scene_preflight_ground_contact_blender.py:
  SHA256: f3a4c5fab8c7834cc02aed4a2ec10c51803d954170496147115d21cb6abcefa7
protocol_guard/phase3_min/tests/test_asset_scene_preflight_blender_facing_i3a.py:
  SHA256: d8830b1cbb2d5f0d015af3e0c3a46dab9f021a525debe719bc86f8a416d2e3f1
protocol_guard/phase3_min/tests/test_asset_scene_preflight_blender_scene_basic.py:
  SHA256: ea1920a16206df02204ce2469077d95d7d390cf8cce1e3aab1a3c936a2a9001c
```

## Frozen Design Hashes

```text
reviews/GROUND_CONTACT_DESIGN_R1.md:
  SHA256: 5f8a1042a6792fe18e1a716a3b9a5ec30ef1b08e1cdbb9a91c908e8e4ed811e3
reviews/GROUND_CONTACT_DESIGN_R2_FORMAL_LOCK_RECORD.md:
  SHA256: 8aa8973d662251754c72a22241196d367ccf93f7c05ffab0ee8812f97b4f99c3
reviews/PROJECT_CODEIFICATION_MASTER_MAP.md:
  SHA256: 66675d42c45713386d9fbc211f8f886a5f5626f42a916c63ac7f5ad248800d47
```

## Auxiliary Regression Infrastructure Correction

```text
protocol_guard/phase3_min/tests/test_phase3_min_predelivery_lints.py:
  SHA256: 69e2b5f351feba1d7cc65aa5ee19866135dd0b123782b84d1f6dbd438896c571
  REASON: Fixed Python subprocess stdout/stderr UTF-8 decoding
  GROUND_CONTACT_CONTRACT_CHANGED: FALSE
  GROUND_CONTACT_PRODUCTION_CHANGED: FALSE
```

## Safety Boundary

```text
REAL_PROJECT_BLEND_OPENED: FALSE
REAL_PROJECT_BLEND_SAVED: FALSE
RENDER_EXECUTED: FALSE
USER_ASSET_MODIFIED: FALSE
TEMPORARY_FILES_CLEANED: TRUE
```

## Scope Test Alignment Note

```text
Facing I3A (test_asset_scene_preflight_blender_facing_i3a.py):
  _check_ground_contact added to authorized matrix_world functions.
  Assertion: matrix_world Load == 1 in _check_ground_contact.

Scene Basic (test_asset_scene_preflight_blender_scene_basic.py):
  Evaluated geometry APIs removed from file-level string ban.
  Added AST-level per-function check:
    _check_ground_contact: each API exactly 1 static call site.
    All other functions: 0 calls.
    asset_scene_preflight_check.py: 0 calls.

Existing Standing, Facing, Rotation protections retained.
```

## Lock Effect

```text
Ground Contact 设计、生产实现、核心测试、真实 Blender 验证、
入口集成和完整回归均完成并正式锁定。

后续修改 Ground Contact 的合同、生产实现或锁定测试，
必须经过新的用户明确授权。

本锁定不授权 Camera Check、Projection Groups
或其他未完成字段组。
```
