# 14B-4A Visibility Design R2

```text
TASK_ID: 14B_4A_VISIBILITY_DESIGN_R2
BASELINE: d44679fc11c5069a17277395bb6c52b5a6dfc799
DESIGN_STATUS: DRAFT_FOR_INDEPENDENT_REVIEW
IMPLEMENTATION_AUTHORIZED: FALSE
SUPERSEDES: 14B_4A_VISIBILITY_DESIGN_R1.md
```

## R2 Amendments

1. Added runtime ERROR contracts for `hide_viewport` and `hide_render` reads.
2. Added read-once cache contract and write-forbidden rules.
3. Field independence: one field's ERROR does not block the other.

All R1 content (fields, configuration, algorithm, result structure, failure codes, scope) preserved.

---

## 1. Fields (unchanged from R1)

| Field | Type | Meaning |
|-------|------|---------|
| `visibility.require_not_hidden_viewport` | `bool` or `None` | If `true`, assert `root_obj.hide_viewport == false` |
| `visibility.require_not_hidden_render` | `bool` or `None` | If `true`, assert `root_obj.hide_render == false` |

## 2. Configuration (unchanged)

| visibility state | Behavior |
|-----------------|----------|
| missing / null / `{}` / both null | NOT_CHECKED |
| one or both `true` | Execute matching checks |
| `false` | Equivalent to omitted (not a positive "must be hidden") |

## 3. Read-once and Cache Contract (R2)

Each configured field reads its Blender property at most once:

```text
require_not_hidden_viewport == true → read root_obj.hide_viewport once
require_not_hidden_render == true  → read root_obj.hide_render once
```

Read results are stored in local variables. Result construction must use cached values, never re-read Blender properties.

Fields where `require_not_hidden_*` is missing, null, or `false` must not read the corresponding Blender property at all.

## 4. Write Forbidden (R2)

The Visibility check must not write to `hide_viewport`, `hide_render`, or any other Blender object attribute. Read-only boundary.

## 5. Runtime ERROR Contracts (R2)

### 5.1 hide_viewport read fails

```json
{
  "visibility": {
    "result": "ERROR",
    "viewport": {
      "result": "ERROR",
      "error_type": "VISIBILITY_READ_ERROR",
      "operation": "READ_ROOT_HIDE_VIEWPORT",
      "note": "READ_ROOT_HIDE_VIEWPORT_FAILED"
    }
  }
}
```

### 5.2 hide_render read fails

```json
{
  "visibility": {
    "result": "ERROR",
    "render": {
      "result": "ERROR",
      "error_type": "VISIBILITY_READ_ERROR",
      "operation": "READ_ROOT_HIDE_RENDER",
      "note": "READ_ROOT_HIDE_RENDER_FAILED"
    }
  }
}
```

### 5.3 Both reads fail

```json
{
  "visibility": {
    "result": "ERROR",
    "viewport": {"result": "ERROR", "error_type": "VISIBILITY_READ_ERROR", "operation": "READ_ROOT_HIDE_VIEWPORT", "note": "READ_ROOT_HIDE_VIEWPORT_FAILED"},
    "render": {"result": "ERROR", "error_type": "VISIBILITY_READ_ERROR", "operation": "READ_ROOT_HIDE_RENDER", "note": "READ_ROOT_HIDE_RENDER_FAILED"}
  }
}
```

### 5.4 Operation names

| Operation | Note |
|-----------|------|
| `READ_ROOT_HIDE_VIEWPORT` | `READ_ROOT_HIDE_VIEWPORT_FAILED` |
| `READ_ROOT_HIDE_RENDER` | `READ_ROOT_HIDE_RENDER_FAILED` |

### 5.5 Field independence

- `hide_viewport` read ERROR does NOT prevent `hide_render` check (if configured).
- `hide_render` read ERROR does NOT prevent `hide_viewport` check (if configured).
- Target overall aggregation: ERROR > FAIL > PASS.

### 5.6 ERROR omission rules

On ERROR, the affected sub-dict (`viewport` or `render`) must NOT contain: `require_not_hidden`, `actual_hidden`, `failure_code`.

## 6. Algorithm (R2 amended)

```
Step 1: If require_not_hidden_viewport == true:
  try: hv = root_obj.hide_viewport; cache hv
  except → viewport ERROR (READ_ROOT_HIDE_VIEWPORT_FAILED)
Step 2: If require_not_hidden_render == true:
  try: hr = root_obj.hide_render; cache hr
  except → render ERROR (READ_ROOT_HIDE_RENDER_FAILED)
Step 3: For each cached value that succeeded:
  if cached == True and require == True → FAIL
  else → PASS
Step 4: Aggregate: ERROR > FAIL > PASS
```

## 7. Result Structure (unchanged from R1)

Same nested path: `checks.visibility.{viewport|render}`. Same PASS/FAIL/NOT_CHECKED fields.

### 7.1 FAIL

```json
{
  "visibility": {
    "result": "FAIL",
    "viewport": {"result": "FAIL", "failure_code": "OBJECT_HIDDEN_IN_VIEWPORT", "require_not_hidden": true, "actual_hidden": true},
    "render": {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"}
  }
}
```

## 8. _collect_target_errors (R2)

```python
vs = checks.get("visibility", {})
for sub in ("viewport", "render"):
    v = vs.get(sub, {})
    if v.get("result") == "ERROR":
        op = v.get("operation", "UNKNOWN")
        err_msgs.append(f"VISIBILITY_READ_ERROR: target '{tid}' root_object_name '{rn}' operation '{op}'")
```

Collection order: object_exists → direct_children → descendants → standing → facing → visibility.

## 9. Scope Boundary (unchanged from R1)

Root object only. No children. No descendants. No material/animation/collection/ground/camera/projection/render/output artifact.
