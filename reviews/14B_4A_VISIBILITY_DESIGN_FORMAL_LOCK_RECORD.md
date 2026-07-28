# 14B-4A Visibility Design Formal Lock Record

```text
TASK_ID: 14B_4A_VISIBILITY_DESIGN_R2_LOCK_SYNC
DATE: 2026-07-18
VISIBILITY_DESIGN_VERSION: R2
VISIBILITY_DESIGN_STATUS: LOCKED
USER_APPROVED: TRUE
IMPLEMENTATION_AUTHORIZED: FALSE
IMPLEMENTATION_STATUS: NOT_STARTED
```

## Locked Design Documents

| Document | Location |
|----------|----------|
| Requirement Audit R2 | reviews/14B_4A_VISIBILITY_REQUIREMENT_AUDIT_R2.md |
| Design R2 | reviews/14B_4A_VISIBILITY_DESIGN_R2.md |
| Design Report | reviews/14B_4A_VISIBILITY_DESIGN_R2_REPORT.md |

## Locked Fields

- `visibility.require_not_hidden_viewport` (bool or None)
- `visibility.require_not_hidden_render` (bool or None)

## Locked Design Decisions

- Missing/null/false: no check performed (false ≠ require hidden)
- Field independence: each field reads its property independently
- Read-once cache: each Blender property read at most once per check invocation
- 2 runtime ERROR operations: READ_ROOT_HIDE_VIEWPORT, READ_ROOT_HIDE_RENDER
- ERROR > FAIL > PASS aggregation
- Root-only check (no children, no descendants)
- Write forbidden (read-only boundary)
- No mathutils, no matrix, no scene traversal
