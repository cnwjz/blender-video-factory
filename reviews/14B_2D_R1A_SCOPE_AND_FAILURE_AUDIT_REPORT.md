# 14B-2D R1A Scope and Failure Audit Report

**TASK_ID**: 14B_2D_R1A_SCOPE_AND_FAILURE_AUDIT
**BASELINE**: d44679fc11c5069a17277395bb6c52b5a6dfc799
**HEAD_UNCHANGED**: TRUE

## 1. Unauthorized Production Code Changes

### Change A: `_build_descendant_required_types` — type read exception boundary (lines 475-508)
- **Purpose**: Catch `obj.type` RuntimeError, return DESCENDANT_LOOKUP_ERROR
- **Added**: `try: actual_type = objs[0].type` / `except Exception: return DESCENDANT_LOOKUP_ERROR`
- **Matches Review Issue 1**: PARTIALLY (handles unique-object case, not ambiguity case)

### Change B: Aggregation ERROR check (lines 365-376)
- **Added**: `if types_result.get("error_type") == "DESCENDANT_LOOKUP_ERROR": return types_result`
- **Modified**: aggregation now checks `"ERROR" in sub_results` before `"FAIL" in sub_results`
- **Matches Review Issue 1**: YES (propagates ERROR from types_result)

**UNAUTHORIZED_PRODUCTION_CHANGE_COUNT**: 2 (both in `_check_descendants` / `_build_descendant_required_types`)
**PRODUCTION_CHANGE_FULLY_DOCUMENTED**: TRUE

## 2. Test Harness Changes

All 4 files verified:
- `_run_blender()`: returncode==0 check, PASS=OK check, no Traceback, no AssertionError
- Child scripts: try/except with traceback.print_exc() + sys.exit(1)
- `body_indented` correctly wraps test code in try block

**TEST_HARNESS_REQUIREMENTS_ALL_PRESENT**: TRUE

## 3. All Failing Tests

| # | File | Function | Expected | Actual |
|---|------|----------|----------|--------|
| 1 | test_..._i2b1.py | TestTypeLookupPrecedesAmbiguity::test_first_dup_type_throws | DESCENDANT_LOOKUP_ERROR | AMBIGUOUS_DESCENDANT_NAME |
| 2 | test_..._i2b1.py | TestErrorResultOmitFields::test_error_omits_normal_fields | DESCENDANT_LOOKUP_ERROR | AMBIGUOUS_DESCENDANT_NAME |
| 3 | test_..._i2b2.py | TestTypeErrorStillPrecedesAmbiguity::test_type_error_before_ambiguity_preserved | DESCENDANT_LOOKUP_ERROR | AMBIGUOUS_DESCENDANT_NAME |

**TOTAL_FAILING_TESTS**: 3
**ALL_FAILING_TEST_NAMES_IDENTIFIED**: TRUE

All 3 failures share the same root cause: the ambiguity block's type-read loop checks only the first matching object and breaks. The non-throwing object appears first in sorted `desc_items`.

## 4. Root Cause: Ambiguous Type Read

**DIAGNOSTIC FINDINGS**:
```
d1 (type_ok=False): id=2053607541120
d2 (type_ok=True):  id=2053607371984

desc_items after _collect_descendants (sorted by name.casefold):
  ITEM[0]: Body, id=2053607371984 (= d2, type_ok=True,  type OK)
  ITEM[1]: Body, id=2053607541120 (= d1, type_ok=False, type RAISES)
```

The ambiguity block iterates `desc_items` in sorted order:
```python
for nm, obj in desc_items:
    if nm == name:
        try:
            _ = obj.type     # ITEM[0]: d2 type OK → no exception
        except Exception:
            return {...}      # never reached
        break                # EXITS here — ITEM[1] (d1, type raises) NEVER CHECKED
```

Because `_collect_descendants` sorts by `(name.casefold(), name)`, and both objects have the same name, the non-throwing object (d2, tested first) precedes the throwing object (d1). The `break` after first match prevents checking d1.

**AMBIGUOUS_TYPE_READ_ROOT_CAUSE_IDENTIFIED**: TRUE
**ACTUAL_OBJECT_READ_ORDER**: Non-throwing object first (stack LIFO order reversed by sort stability)
**THROWING_OBJECT_READ_COUNT**: 0 (never reached due to break)
**NON_THROWING_OBJECT_READ_COUNT**: 1

**Fix**: The ambiguity block must check ALL matching objects, not break after first. Or: check type on ALL objects before returning AMBIGUOUS_DESCENDANT_NAME.

## Boundaries
| PRODUCTION_FILES_MODIFIED_THIS_TASK | 0 |
| TEST_FILES_MODIFIED_THIS_TASK | 0 |
| BLENDER_RUN | TRUE |
| BLENDER_EXECUTION_SCOPE | FACTORY_STARTUP_DIAGNOSTIC_ONLY |
| REAL_BLEND_OPENED | FALSE |
| RENDER_RUN | FALSE |
| SAVE_RUN | FALSE |
| GIT_COMMIT_RUN | FALSE |
| GIT_PUSH_RUN | FALSE |
| NEXT_TASK_STARTED | FALSE |
