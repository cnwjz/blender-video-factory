# 14B-4A Visibility Design R1

```text
TASK_ID: 14B_4A_VISIBILITY_DESIGN_R1
BASELINE: d44679fc11c5069a17277395bb6c52b5a6dfc799
DESIGN_STATUS: DRAFT_FOR_INDEPENDENT_REVIEW
IMPLEMENTATION_AUTHORIZED: FALSE
```

## 1. Fields

| Field | Type | Meaning |
|-------|------|---------|
| `visibility.require_not_hidden_viewport` | `bool` or `None` | If `true`, assert `root_obj.hide_viewport == false` |
| `visibility.require_not_hidden_render` | `bool` or `None` | If `true`, assert `root_obj.hide_render == false` |

Both fields are independent. No all-or-nothing constraint. No pre-open relational validation (14A schema already validates type).

## 2. Configuration Semantics

| visibility state | Behavior |
|-----------------|----------|
| missing / null | NOT_CHECKED (`VISIBILITY_RULES_NOT_CONFIGURED`) |
| `{}` | NOT_CHECKED (no fields configured) |
| `{"require_not_hidden_viewport": null, "require_not_hidden_render": null}` | NOT_CHECKED (both fields None, same as empty) |
| `{"require_not_hidden_viewport": true}` | Execute: check `hide_viewport == false` |
| `{"require_not_hidden_render": true}` | Execute: check `hide_render == false` |
| `{"require_not_hidden_viewport": false}` | Depends — `false` means "I do NOT require it to be visible". This is a no-op (NOT_CHECKED for this field), not "I require it to be hidden". See §2.1. |
| Both true | Execute both checks |
| One true, one null/false | Execute the true one; NOT_CHECKED for the other |

### 2.1 False semantics

`require_not_hidden_viewport: false` does NOT mean "require it to be hidden". It means "do not require it to be visible". There is no positive assertion for "must be hidden". The spec only encodes "must NOT be hidden". If a future requirement needs "must be hidden", a new field would be needed. For now, `false` is equivalent to omitting the field — the check is not performed.

## 3. Algorithm

```
Step 1: read root_obj.hide_viewport (property access, no try/except needed)
Step 2: read root_obj.hide_render (property access, no try/except needed)
Step 3: for each configured field (value == True):
  if hide_viewport == True and require_not_hidden_viewport == True → FAIL
  if hide_render == True and require_not_hidden_render == True → FAIL
Step 4: PASS if no failures
```

No matrix math. No normalization. No angle computation. No `mathutils` import needed.

### 3.1 Where to read

Both `hide_viewport` and `hide_render` are direct boolean properties on `bpy.types.Object`. Read directly from `root_obj` (the verified unique root object). No scene traversal. No children. No descendants. Check applies only to the root object itself.

## 4. Result Structure

```json
{
  "visibility": {
    "result": "PASS" | "FAIL" | "NOT_CHECKED",
    "viewport": {
      "result": "PASS" | "FAIL" | "NOT_CHECKED",
      "require_not_hidden": true,
      "actual_hidden": false
    },
    "render": {
      "result": "PASS" | "FAIL" | "NOT_CHECKED",
      "require_not_hidden": true,
      "actual_hidden": false
    }
  }
}
```

### 4.1 NOT_CHECKED

```json
{
  "visibility": {
    "result": "NOT_CHECKED",
    "viewport": {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"},
    "render": {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"}
  }
}
```

### 4.2 PASS

```json
{
  "visibility": {
    "result": "PASS",
    "viewport": {"result": "PASS", "require_not_hidden": true, "actual_hidden": false},
    "render": {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"}
  }
}
```

### 4.3 FAIL

```json
{
  "visibility": {
    "result": "FAIL",
    "viewport": {"result": "FAIL", "failure_code": "OBJECT_HIDDEN_IN_VIEWPORT", "require_not_hidden": true, "actual_hidden": true},
    "render": {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"}
  }
}
```

### 4.4 No runtime ERROR operations

Unlike Standing/Facing, there are no risky operations (no matrix access, no math functions). Reading `hide_viewport` and `hide_render` from a valid Blender Object cannot raise exceptions. If the root object doesn't exist or type mismatches, the check returns NOT_CHECKED (following the same root precondition pattern as Standing/Facing).

## 5. Failure Codes

| Code | Meaning |
|------|---------|
| `OBJECT_HIDDEN_IN_VIEWPORT` | `require_not_hidden_viewport == True` but `hide_viewport == True` |
| `OBJECT_HIDDEN_IN_RENDER` | `require_not_hidden_render == True` but `hide_render == True` |

## 6. Target Overall Aggregation

Same as Standing/Facing: ERROR > FAIL > PASS. Visibility participates alongside direct_children, descendants, standing, and facing.

Since Visibility has no ERROR operations, it only contributes FAIL or PASS/NOT_CHECKED.

## 7. Root Precondition Behavior

| Condition | Visibility |
|-----------|-----------|
| Root not found | NOT_CHECKED, note=ROOT_OBJECT_NOT_FOUND |
| Type mismatch | NOT_CHECKED, note=ROOT_OBJECT_TYPE_MISMATCH |
| Ambiguous name | NOT_CHECKED, note=AMBIGUOUS_ROOT_OBJECT_NAME |

## 8. Scope Boundary

**In scope**: `root_obj.hide_viewport`, `root_obj.hide_render`, root object only.

**Not in scope**: Children visibility, descendant visibility, render result visibility, material-driven hiding, collection-based visibility, animation-driven visibility toggles. These are deferred to their respective field groups (material, animation, collection_rules).

## 9. Implementation Phases

```text
I1: PASS/FAIL/NOT_CHECKED + overall aggregation + _check_root_objects integration
I2: Scope guard update (allow hide_viewport/hide_render reads)
E:  Facing + Visibility + 14A Core + full regression + evidence
```

No I3B (no real Blender needed — CPython fake objects sufficient for boolean reads).
