"""Task card validation using JSON Schema v2 + cross-field constraint checks.

v1.2: state_patch_requested.fields whitelist from PS schema, allowed/forbidden conflict detection."""
import json
import os
import yaml

_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schemas", "task_card.schema.json")
PS_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schemas", "project_state.schema.json")


def _load_schema():
    with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_ps_schema():
    with open(PS_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_ps_field_names():
    """Dynamically load valid PROJECT_STATE field names from the PS schema."""
    ps = _load_ps_schema()
    return set(ps.get("properties", {}).keys())


def _unique_ids(items, key):
    seen = set()
    dups = set()
    for item in items:
        val = item.get(key)
        if val in seen:
            dups.add(val)
        seen.add(val)
    return dups


def validate_task_card(task_data, schema=None):
    """Validate a task card dict. Returns (is_valid, list_of_errors)."""
    import jsonschema

    if schema is None:
        schema = _load_schema()

    errors = []

    # 1. JSON Schema structural validation
    try:
        jsonschema.validate(instance=task_data, schema=schema)
    except jsonschema.ValidationError as e:
        errors.append(f"Schema violation: {e.message}")
        return False, errors

    # 2. primary_variable must be a non-empty single string
    pv = task_data.get("primary_variable")
    if not isinstance(pv, str) or len(pv) == 0:
        errors.append("primary_variable must be a non-empty single string")

    # 3. Cross-field constraint: no parameter overlaps
    pv_set = {pv} if isinstance(pv, str) and pv else set()

    fixed = task_data.get("fixed_params", {})
    if not isinstance(fixed, dict):
        errors.append("fixed_params must be an object")
        fixed_keys = set()
    else:
        fixed_keys = set(fixed.keys())

    dep_vars = task_data.get("dependent_variables", [])
    dep_names = set()
    if isinstance(dep_vars, list):
        for dv in dep_vars:
            if isinstance(dv, dict) and "name" in dv:
                dep_names.add(dv["name"])

    dup_pv_dep = pv_set & dep_names
    dup_pv_fixed = pv_set & fixed_keys
    dup_dep_fixed = dep_names & fixed_keys

    if dup_pv_dep:
        errors.append(f"Parameters in both primary_variable and dependent_variables: {dup_pv_dep}")
    if dup_pv_fixed:
        errors.append(f"Parameters in both primary_variable and fixed_params: {dup_pv_fixed}")
    if dup_dep_fixed:
        errors.append(f"Parameters in both dependent_variables and fixed_params: {dup_dep_fixed}")

    # 4. dependent_variables: each name must be unique
    if isinstance(dep_vars, list):
        dep_name_dups = _unique_ids(dep_vars, "name")
        if dep_name_dups:
            errors.append(f"Duplicate dependent_variable names: {dep_name_dups}")

    # 5. preflight_checks: check_id must be unique
    preflight = task_data.get("preflight_checks", [])
    if isinstance(preflight, list):
        pf_dups = _unique_ids(preflight, "check_id")
        if pf_dups:
            errors.append(f"Duplicate preflight check_ids: {pf_dups}")

    # 6. technical_pass_conditions: condition_id must be unique
    conditions = task_data.get("technical_pass_conditions", [])
    if isinstance(conditions, list):
        cond_dups = _unique_ids(conditions, "condition_id")
        if cond_dups:
            errors.append(f"Duplicate condition_ids: {cond_dups}")

        for cond in conditions:
            op = cond.get("operator")
            exp = cond.get("expected")
            if op == "between":
                if not isinstance(exp, list) or len(exp) != 2 or not all(isinstance(v, (int, float)) for v in exp):
                    errors.append(f"condition_id={cond.get('condition_id')}: 'between' operator requires expected=[min, max] as two numbers")
            elif op == "in":
                if not isinstance(exp, list) or len(exp) == 0:
                    errors.append(f"condition_id={cond.get('condition_id')}: 'in' operator requires expected as non-empty array")

    # 7. locked_items: lock_id must be unique
    locks = task_data.get("locked_items", [])
    if isinstance(locks, list):
        lock_dups = _unique_ids(locks, "lock_id")
        if lock_dups:
            errors.append(f"Duplicate lock_ids: {lock_dups}")

    # 8. evidence_required: evidence_id must be unique
    evidence = task_data.get("evidence_required", [])
    if isinstance(evidence, list):
        ev_dups = _unique_ids(evidence, "evidence_id")
        if ev_dups:
            errors.append(f"Duplicate evidence_ids: {ev_dups}")

    # 9. allowed_modifications vs forbidden_modifications conflict detection
    allowed = task_data.get("allowed_modifications", [])
    forbidden = task_data.get("forbidden_modifications", [])
    if isinstance(allowed, list) and isinstance(forbidden, list):
        for a in allowed:
            a_target = a.get("target", "")
            a_fields = set(a.get("fields", []))
            for f in forbidden:
                f_target = f.get("target", "")
                f_fields = set(f.get("fields", []))
                if a_target == f_target:
                    conflict = a_fields & f_fields
                    if conflict:
                        for cfield in sorted(conflict):
                            errors.append(f"Modification conflict: '{a_target}.{cfield}' is in both allowed_modifications and forbidden_modifications")

    # 10. state_patch_requested: if not null, validate fields against PS schema
    spr = task_data.get("state_patch_requested")
    if spr is not None:
        if not isinstance(spr, dict):
            errors.append("state_patch_requested must be null or an object")
        else:
            if "fields" not in spr or not isinstance(spr.get("fields"), dict) or len(spr.get("fields", {})) == 0:
                errors.append("state_patch_requested.fields must be a non-empty object")
            if "reason" not in spr or not isinstance(spr.get("reason"), str) or len(spr.get("reason", "")) == 0:
                errors.append("state_patch_requested.reason must be a non-empty string")
            if set(spr.keys()) - {"fields", "reason"}:
                errors.append("state_patch_requested has unknown fields beyond 'fields' and 'reason'")
            # Validate field names against PROJECT_STATE schema
            ps_field_names = _get_ps_field_names()
            for field_name in spr.get("fields", {}):
                if field_name not in ps_field_names:
                    errors.append(f"state_patch_requested.fields contains unknown PROJECT_STATE field: '{field_name}'")

    return (len(errors) == 0, errors)


def load_task_card(task_path):
    """Load a task card YAML file and return the parsed dict."""
    with open(task_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_task_file(task_path):
    """Load and validate a task card YAML file. Returns (is_valid, errors)."""
    task_data = load_task_card(task_path)
    return validate_task_card(task_data)
