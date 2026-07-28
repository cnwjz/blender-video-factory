# 14B-4A Visibility Requirement Audit R1

```text
TASK_ID: 14B_4A_VISIBILITY_DESIGN_R1
DATE: 2026-07-18
BASELINE: d44679fc11c5069a17277395bb6c52b5a6dfc799
```

## 1. 14A Schema Status

File: `asset_scene_preflight_core.py` `_validate_visibility` (lines 351-358)

```python
def _validate_visibility(t, i, errs):
    v = t.get("visibility")
    if v is None: return
    if not isinstance(v, dict): errs.append(f"targets[{i}].visibility must be an object"); return
    for field in ("require_not_hidden_viewport", "require_not_hidden_render"):
        val = v.get(field)
        if val is not None and not isinstance(val, bool):
            errs.append(f"targets[{i}].visibility.{field} must be boolean")
```

### Fields

| Field | Type | Valid | None behavior |
|-------|------|-------|---------------|
| `visibility.require_not_hidden_viewport` | `bool` or `None` | `True` / `False` | Schema skips (field optional) |
| `visibility.require_not_hidden_render` | `bool` or `None` | `True` / `False` | Schema skips (field optional) |

### Configuration matrix per 14A

| visibility state | 14A Schema |
|-----------------|------------|
| missing / null | no error |
| `{}` | no error |
| `{"require_not_hidden_viewport": true}` | no error |
| `{"require_not_hidden_viewport": false}` | no error |
| `{"require_not_hidden_viewport": "yes"}` | ERROR (not bool) |
| `require_not_hidden_viewport: null` | no error |

Key difference from Facing: both fields are independent booleans with no all-or-nothing constraint. No tolerance. No axis names. No pre-open relational validation needed.

## 2. Original Document Evidence

Source: `Blender_固定资产模板路线_新对话交接文档_v4.md`

| # | Line | Text | Classification |
|---|------|------|---------------|
| E1 | 625 | `visibility_states` as data field | Structural requirement — visibility state is a recorded data point |
| E2 | 739 | "读取对象名称、层级、坐标、旋转、缩放和可见性状态" | Operational requirement — visibility must be readable via bpy |
| E3 | 1053-1054 | "全部人物完整显示。收银台和商品完整显示" | Visual requirement — characters must be visible in viewport |
| E4 | 1392 | "必要对象未被隐藏或禁用渲染" | Validation requirement — objects must not be hidden or render-disabled |

E3 and E4 are the core code-enforceable requirements: verify that required objects are not hidden in viewport and not disabled for render.

## 3. Code-Enforceable Scope

**In scope**: Check that `root_obj.hide_viewport` and `root_obj.hide_render` match spec expectations (e.g. `require_not_hidden_viewport: true` means `hide_viewport == False`).

**Out of scope**: Visual confirmation that a character "displays completely" (line 1053-1054) — this is a render-time visual check, not a boolean attribute check. The boolean check can confirm the object is not hidden, but cannot confirm it's fully within frame or unobstructed. Classified as HUMAN_JUDGMENT_ONLY.

## 4. Summary

```text
VISIBILITY_FIELDS_FOUND: 2 (require_not_hidden_viewport, require_not_hidden_render)
DOCUMENT_CONFLICTS_FOUND: 0
CODE_ENFORCEABLE: Both boolean reads. No geometry. No scene traversal beyond root object.
```
