# Post-14B-3B Next Atomic Task R1

```text
TASK_DRAFT_STATUS: AWAITING_INDEPENDENT_REVIEW
IMPLEMENTATION_AUTHORIZED: FALSE
DATE: 2026-07-18
BASIS: PROJECT_CODEIFICATION_MASTER_MAP.md R15
```

## Recommendation

```text
NEXT_ATOMIC_TASK: 14B_4A_VISIBILITY_DESIGN_R1
```

## Rationale

1. Lowest complexity (reads two boolean attributes only)
2. No dependency on evaluated geometry or depsgraph
3. Following the proven Standing → Facing design→implement→test→lock pattern
4. Quickest path to the 4th locked field group

## Scope

```text
FIELD_GROUP: visibility
14A SCHEMA FIELDS:
  visibility.require_not_hidden_viewport (bool or None)
  visibility.require_not_hidden_render (bool or None)
```

## Required Inputs

```text
PROJECT_CODEIFICATION_MASTER_MAP.md (R15)
Blender 固定资产模板路线 v4 original requirement document
protocol_guard/phase3_min/asset_scene_preflight_core.py (_validate_visibility)
protocol_guard/phase3_min/blender_scene_reader.py (_check_root_objects)
Standing lock record (14B_3A_FORMAL_LOCK_RECORD.md)
Facing lock record (14B_3B_FORMAL_LOCK_RECORD.md)
Existing scope guard test
```

## Forbidden

```text
Re-design locked hierarchy/standing/facing
Modify 14A Core
Run Blender or open .blend during design phase
Begin implementation before design is independently reviewed and locked
```

## Deliverables (design phase only)

```text
reviews/14B_4A_VISIBILITY_REQUIREMENT_AUDIT.md
reviews/14B_4A_VISIBILITY_DESIGN_R1.md
```

## Status

```text
IMPLEMENTATION_STARTED: FALSE
```
