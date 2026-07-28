"""Asset Scene Preflight Check — Blender entry point.

Usage:
  blender --background --factory-startup --python <this_file> -- --spec <spec.json> --dependency-site-packages <dir>

Requires --dependency-site-packages pointing to a directory containing PyYAML
so that the locked 14A core module can be imported in Blender's Python.
"""

import os, sys


def _bootstrap_error(msg):
    """Minimal error output before 14A core is available."""
    import json
    result = {
        "schema_version": "1",
        "checker": "asset_scene_preflight_check",
        "source_requirement_version": "Blender 固定资产模板路线 v4",
        "spec_sha256": "",
        "blend_path": "",
        "scene_name": "",
        "per_target_results": [],
        "global_results": {},
        "projection_group_results": [],
        "input_errors": [msg],
        "result": "ERROR",
    }
    print("PHASE3_RESULT_JSON=" + json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")), flush=True)
    sys.exit(2)


def _parse_args(argv):
    """Parse --spec and --dependency-site-packages from argv. Returns dict or (None, error)."""
    spec_path = None
    deps_path = None
    i = 0
    while i < len(argv):
        if argv[i] == "--spec" and i + 1 < len(argv):
            if spec_path is not None:
                return (None, "Duplicate --spec argument")
            spec_path = argv[i + 1]
            i += 2
        elif argv[i] == "--dependency-site-packages" and i + 1 < len(argv):
            if deps_path is not None:
                return (None, "Duplicate --dependency-site-packages argument")
            deps_path = argv[i + 1]
            i += 2
        else:
            i += 1

    if spec_path is None:
        return (None, "Missing --spec argument")
    if deps_path is None:
        return (None, "Missing --dependency-site-packages argument")
    if not os.path.isabs(deps_path):
        return (None, "--dependency-site-packages must be an absolute path")
    if not os.path.isdir(deps_path):
        return (None, f"--dependency-site-packages is not a directory: {deps_path}")

    return ({"spec_path": spec_path, "deps_path": deps_path}, None)


def _validate_direct_child_rules_preopen(targets):
    """Validate direct child rule values and relations before opening .blend.

    Returns a list of error message strings (empty if all valid).
    Checks in-scope values then required⊆allowed relation.
    """
    errors = []
    for target in targets:
        tid = target.get("target_id", "")
        hierarchy = target.get("hierarchy")
        if not isinstance(hierarchy, dict):
            continue

        required = hierarchy.get("required_direct_child_names")
        allowed = hierarchy.get("allowed_direct_child_names")
        forbidden = hierarchy.get("forbidden_direct_child_name_patterns")
        req_desc = hierarchy.get("required_descendant_names")
        forb_desc = hierarchy.get("forbidden_descendant_name_patterns")
        req_types = hierarchy.get("required_descendant_types")

        # Collect valid names for relation check
        valid_required = []
        valid_allowed = []

        # Value validation
        for field_name, field_val in [
            ("required_direct_child_names", required),
            ("allowed_direct_child_names", allowed),
            ("forbidden_direct_child_name_patterns", forbidden),
        ]:
            if field_val is None:
                continue
            if not isinstance(field_val, list):
                continue
            for idx, item in enumerate(field_val):
                if not isinstance(item, str) or item == "":
                    errors.append(
                        f"INVALID_DIRECT_CHILD_RULE_VALUE: target '{tid}' "
                        f"field '{field_name}' index {idx} must be a non-empty string"
                    )
                elif field_name == "required_direct_child_names":
                    valid_required.append(item)
                elif field_name == "allowed_direct_child_names":
                    valid_allowed.append(item)

        # Relation validation: required ⊆ allowed (only when allowed exists)
        # Uses set semantics: case-sensitive dedup before checking
        if allowed is not None and isinstance(allowed, list):
            allowed_set = set(valid_allowed)
            if required is None:
                req_set = set()
            elif isinstance(required, list):
                req_set = set(valid_required)
            else:
                req_set = set()
            not_in_allowed = sorted(
                req_set - allowed_set,
                key=lambda n: (n.casefold(), n),
            )
            if not_in_allowed:
                errors.append(
                    f"INVALID_DIRECT_CHILD_RULE_RELATION: target '{tid}' "
                    f"required names not present in allowed_direct_child_names: {not_in_allowed}"
                )

        # Value validation: required_descendant_names (14B-2C-I1)
        if req_desc is not None and isinstance(req_desc, list):
            for idx, item in enumerate(req_desc):
                if not isinstance(item, str) or item == "":
                    errors.append(
                        f"INVALID_DESCENDANT_RULE_VALUE: target '{tid}' "
                        f"field 'required_descendant_names' index {idx} must be a non-empty string"
                    )

        # Value validation: forbidden_descendant_name_patterns (14B-2C-I2)
        if forb_desc is not None and isinstance(forb_desc, list):
            for idx, item in enumerate(forb_desc):
                if not isinstance(item, str) or item == "":
                    errors.append(
                        f"INVALID_DESCENDANT_RULE_VALUE: target '{tid}' "
                        f"field 'forbidden_descendant_name_patterns' index {idx} must be a non-empty string"
                    )

        # Value validation: required_descendant_types (14B-2D-I1A)
        if req_types is not None and isinstance(req_types, dict):
            invalid_keys = sorted(
                [k for k in req_types if not isinstance(k, str) or k == ""],
                key=lambda k: (str(k).casefold() if isinstance(k, str) else str(k), str(k)),
            )
            for k in invalid_keys:
                if not isinstance(k, str):
                    errors.append(
                        f"INVALID_DESCENDANT_TYPE_RULE_VALUE: target '{tid}' "
                        f"field 'required_descendant_types' contains a non-string key"
                    )
                else:
                    errors.append(
                        f"INVALID_DESCENDANT_TYPE_RULE_VALUE: target '{tid}' "
                        f"field 'required_descendant_types' contains an empty descendant name"
                    )
            for k in sorted(req_types.keys(), key=lambda x: (str(x).casefold() if isinstance(x, str) else str(x))):
                if not isinstance(k, str) or k == "":
                    continue  # already reported above
                v = req_types[k]
                if not isinstance(v, str) or v == "":
                    errors.append(
                        f"INVALID_DESCENDANT_TYPE_RULE_VALUE: target '{tid}' "
                        f"field 'required_descendant_types' key '{k}' must map to a non-empty string"
                    )

    return errors


def _validate_standing_up_axis_rules_preopen(targets):
    """Validate standing up_axis field group: all-or-nothing.

    Returns list of error strings (empty if valid).
    """
    errors = []
    up_axis_fields = [
        "local_up_axis",
        "expected_world_up_axis",
        "up_axis_tolerance_degrees",
    ]
    for target in targets:
        tid = target.get("target_id", "")
        standing = target.get("standing")
        if not isinstance(standing, dict):
            continue

        present = []
        missing = []
        for fn in up_axis_fields:
            if standing.get(fn) is not None:
                present.append(fn)
            else:
                missing.append(fn)

        if 0 < len(present) < 3:
            missing.sort(key=lambda n: (n.casefold(), n))
            errors.append(
                f"INVALID_UP_AXIS_RULE_RELATION: target '{tid}' "
                f"standing up_axis missing required fields: {missing}"
            )

    return errors


def _validate_facing_forward_axis_rules_preopen(targets):
    """Validate facing forward_axis field group: tolerance required when axes present.

    Only triggers when both axis fields are valid (in AXIS_VALUES) but
    facing_tolerance_degrees is missing or None. 14A schema already catches
    invalid/missing axis fields because facing's axis checks lack an is-not-None
    guard (unlike standing).
    """
    from protocol_guard.phase3_min.asset_scene_preflight_core import AXIS_VALUES
    errors = []
    for target in targets:
        tid = target.get("target_id", "")
        facing = target.get("facing")
        if not isinstance(facing, dict):
            continue
        la = facing.get("local_forward_axis")
        ew = facing.get("expected_world_forward_axis")
        tol = facing.get("facing_tolerance_degrees")
        if (la in AXIS_VALUES) and (ew in AXIS_VALUES) and (tol is None):
            errors.append(
                f"INVALID_FACING_RULE_RELATION: target '{tid}' "
                f"facing forward_axis missing required fields: ['facing_tolerance_degrees']"
            )
    return errors


def _validate_rotation_rules_preopen(targets):
    """Validate rotation field group: tolerance required when expected value present.

    Only triggers when expected_world_rotation_euler_degrees is present but
    rotation_tolerance_degrees is missing or None. 14A schema validates field
    types and values independently.
    """
    errors = []
    for target in targets:
        tid = target.get("target_id", "")
        rot = target.get("rotation")
        if not isinstance(rot, dict):
            continue
        erw = rot.get("expected_world_rotation_euler_degrees")
        tol = rot.get("rotation_tolerance_degrees")
        if erw is not None and tol is None:
            errors.append(
                f"INVALID_ROTATION_RULE_RELATION: target '{tid}' "
                f"rotation missing required fields: ['rotation_tolerance_degrees']"
            )
    return errors


def _validate_ground_contact_rules_preopen(targets):
    """Validate all-or-nothing: exactly one of {ground_z, tolerance} present → ERROR.

    Returns list of error strings (empty if valid). Sorted by casefold.
    """
    errors = []
    fields = ["ground_z", "ground_contact_tolerance"]
    for target in targets:
        tid = target.get("target_id", "")
        gc = target.get("ground_contact")
        if not isinstance(gc, dict):
            continue
        present = [f for f in fields if gc.get(f) is not None]
        if len(present) == 1:
            missing = sorted(
                [f for f in fields if f not in present],
                key=lambda n: (n.casefold(), n),
            )
            errors.append(
                f"INVALID_GROUND_CONTACT_RULE_RELATION: target '{tid}' "
                f"ground_contact missing required fields: {missing}"
            )
    return sorted(errors, key=lambda e: (e.casefold(), e))


def _validate_camera_check_rules_preopen(targets):
    """Validate Camera Check field group pre-open rules.

    Returns list of error strings (empty if valid). Sorted by casefold.
    """
    import math
    errors = []
    for target in targets:
        tid = target.get("target_id", "")
        cc = target.get("camera_check")
        if cc is None or not isinstance(cc, dict):
            continue

        # RULE_1: mvc <= 8
        mvc = cc.get("minimum_visible_projected_corner_count", -1)
        if isinstance(mvc, int) and not isinstance(mvc, bool) and mvc > 8:
            errors.append(
                f"INVALID_CAMERA_CHECK_RULE_VALUE: target '{tid}' "
                f"field 'minimum_visible_projected_corner_count' must be <= 8, got {mvc}"
            )

        # RULE_2-3: bbox ordering
        rsb = cc.get("required_screen_bbox")
        if isinstance(rsb, dict):
            ml = rsb.get("min_left")
            mr = rsb.get("max_right")
            mb = rsb.get("min_bottom")
            mt = rsb.get("max_top")
            all_numeric = all(
                isinstance(v, (int, float)) and not isinstance(v, bool)
                for v in (ml, mr, mb, mt)
                if v is not None
            )
            if all_numeric and ml is not None and mr is not None and ml > mr:
                errors.append(
                    f"INVALID_CAMERA_CHECK_RULE_RELATION: target '{tid}' "
                    f"camera_check required_screen_bbox.min_left > max_right"
                )
            if all_numeric and mb is not None and mt is not None and mb > mt:
                errors.append(
                    f"INVALID_CAMERA_CHECK_RULE_RELATION: target '{tid}' "
                    f"camera_check required_screen_bbox.min_bottom > max_top"
                )

            # RULE_4: bbox values in [0, 1]
            for k in ("min_left", "max_right", "min_bottom", "max_top"):
                v = rsb.get(k)
                if v is not None and isinstance(v, (int, float)) and not isinstance(v, bool):
                    if v < 0.0 or v > 1.0:
                        errors.append(
                            f"INVALID_CAMERA_CHECK_RULE_VALUE: target '{tid}' "
                            f"camera_check required_screen_bbox.{k} out of [0,1], got {v}"
                        )

    return sorted(errors, key=lambda e: (e.casefold(), e))


def _validate_projection_groups_rules_preopen(spec):
    """Validate Projection Groups field group pre-open rules.

    Returns list of error strings (empty if valid). Sorted by casefold.

    RULE_1: mvc <= 8
    RULE_2: required_screen_bbox values in [0, 1]
    RULE_3: additional_object_names elements must be non-empty string
    RULE_4: target_ids must not contain duplicates
    RULE_5: additional_object_names must not contain duplicates
    RULE_6: target_ids and additional_object_names must not both be empty
    """
    import math
    errors = []
    pg = spec.get("projection_groups")
    if pg is None or not isinstance(pg, list):
        return errors

    for i, group in enumerate(pg):
        if not isinstance(group, dict):
            continue
        gid = group.get("group_id", "")

        # RULE_1: mvc <= 8
        mvc = group.get("minimum_visible_projected_corner_count", -1)
        if isinstance(mvc, int) and not isinstance(mvc, bool) and mvc > 8:
            errors.append(
                f"INVALID_PROJECTION_GROUP_RULE_VALUE: group_id '{gid}' "
                f"field 'minimum_visible_projected_corner_count' must be <= 8, got {mvc}"
            )

        # RULE_2: required_screen_bbox values in [0, 1]
        rsb = group.get("required_screen_bbox")
        if isinstance(rsb, dict):
            for k in ("min_left", "max_right", "min_bottom", "max_top"):
                v = rsb.get(k)
                if v is not None and isinstance(v, (int, float)) and not isinstance(v, bool):
                    if v < 0.0 or v > 1.0:
                        errors.append(
                            f"INVALID_PROJECTION_GROUP_RULE_VALUE: group_id '{gid}' "
                            f"required_screen_bbox.{k} out of [0,1], got {v}"
                        )

        # RULE_3: additional_object_names elements non-empty string
        aon = group.get("additional_object_names", [])
        if isinstance(aon, list):
            for j, name in enumerate(aon):
                if not isinstance(name, str) or name == "":
                    errors.append(
                        f"INVALID_PROJECTION_GROUP_RULE_VALUE: group_id '{gid}' "
                        f"additional_object_names[{j}] must be a non-empty string"
                    )

        # RULE_4: target_ids no duplicates
        tids = group.get("target_ids", [])
        if isinstance(tids, list):
            seen = set()
            for tid in tids:
                if isinstance(tid, str) and tid != "":
                    if tid in seen:
                        errors.append(
                            f"INVALID_PROJECTION_GROUP_RULE_VALUE: group_id '{gid}' "
                            f"duplicate target_id '{tid}' in target_ids"
                        )
                    seen.add(tid)

        # RULE_5: additional_object_names no duplicates
        if isinstance(aon, list):
            seen = set()
            for name in aon:
                if isinstance(name, str) and name != "":
                    if name in seen:
                        errors.append(
                            f"INVALID_PROJECTION_GROUP_RULE_VALUE: group_id '{gid}' "
                            f"duplicate object name '{name}' in additional_object_names"
                        )
                    seen.add(name)

        # RULE_6: target_ids and additional_object_names not both empty
        tids_empty = not isinstance(tids, list) or len(tids) == 0
        aon_empty = not isinstance(aon, list) or len(aon) == 0
        if tids_empty and aon_empty:
            errors.append(
                f"INVALID_PROJECTION_GROUP_RULE_VALUE: group_id '{gid}' "
                f"both target_ids and additional_object_names are empty"
            )

    return sorted(errors, key=lambda e: (e.casefold(), e))


def _compute_projection_group_overall(pg_results):
    """Compute overall projection_group result from per-group results.

    Returns "PASS", "FAIL", or "ERROR".
    """
    if not pg_results:
        return "PASS"
    results = [g["result"] for g in pg_results]
    if any(r == "ERROR" for r in results):
        return "ERROR"
    if any(r == "FAIL" for r in results):
        return "FAIL"
    return "PASS"


def _collect_target_errors(per_target_results):
    """Collect stable error messages from all ERROR targets.

    Handles AMBIGUOUS_ROOT_OBJECT_NAME, AMBIGUOUS_DIRECT_CHILD_NAME,
    DIRECT_CHILD_LOOKUP_ERROR, and any future ERROR types.
    """
    err_msgs = []
    collection_rule_errors = []
    for t in per_target_results:
        if t.get("overall") != "ERROR":
            continue
        tid = t.get("target_id", "")
        rn = t.get("root_object_name", "")
        checks = t.get("checks", {})

        oe = checks.get("object_exists", {})
        if oe.get("result") == "ERROR":
            et = oe.get("error_type", "")
            if et == "AMBIGUOUS_ROOT_OBJECT_NAME":
                err_msgs.append(
                    f"AMBIGUOUS_ROOT_OBJECT_NAME: target '{tid}' "
                    f"root_object_name '{rn}' has {oe.get('match_count', '?')} matches"
                )
            elif et == "DIRECT_CHILD_LOOKUP_ERROR":
                operation = oe.get("operation", "UNKNOWN")
                err_msgs.append(
                    f"DIRECT_CHILD_LOOKUP_ERROR: target '{tid}' "
                    f"root_object_name '{rn}' operation '{operation}'"
                )

        dc = checks.get("direct_children", {})
        if dc.get("result") == "ERROR":
            et = dc.get("error_type", "")
            if et == "AMBIGUOUS_DIRECT_CHILD_NAME":
                anc = dc.get("ambiguous_name_counts", {})
                for cname in sorted(anc.keys(), key=lambda n: (n.casefold(), n)):
                    count = anc[cname]
                    err_msgs.append(
                        f"AMBIGUOUS_DIRECT_CHILD_NAME: target '{tid}' "
                        f"root_object_name '{rn}' direct child name "
                        f"'{cname}' has {count} matches"
                    )
            elif et == "DIRECT_CHILD_LOOKUP_ERROR":
                operation = dc.get("operation", "UNKNOWN")
                err_msgs.append(
                    f"DIRECT_CHILD_LOOKUP_ERROR: target '{tid}' "
                    f"root_object_name '{rn}' operation '{operation}'"
                )

        dd = checks.get("descendants", {})
        if dd.get("result") == "ERROR":
            et = dd.get("error_type", "")
            if et == "AMBIGUOUS_DESCENDANT_NAME":
                anc = dd.get("ambiguous_name_counts", {})
                for cname in sorted(anc.keys(), key=lambda n: (n.casefold(), n)):
                    count = anc[cname]
                    err_msgs.append(
                        f"AMBIGUOUS_DESCENDANT_NAME: target '{tid}' "
                        f"root_object_name '{rn}' descendant name "
                        f"'{cname}' has {count} matches"
                    )
            elif et == "DESCENDANT_LOOKUP_ERROR":
                operation = dd.get("operation", "UNKNOWN")
                err_msgs.append(
                    f"DESCENDANT_LOOKUP_ERROR: target '{tid}' "
                    f"root_object_name '{rn}' operation '{operation}'"
                )

        su = checks.get("standing", {}).get("up_axis", {})
        if su.get("result") == "ERROR":
            op = su.get("operation", "UNKNOWN")
            err_msgs.append(
                f"STANDING_UP_AXIS_ERROR: target '{tid}' "
                f"root_object_name '{rn}' operation '{op}'"
            )

        ff = checks.get("facing", {}).get("forward_axis", {})
        if ff.get("result") == "ERROR":
            op = ff.get("operation", "UNKNOWN")
            err_msgs.append(
                f"FACING_FORWARD_AXIS_ERROR: target '{tid}' "
                f"root_object_name '{rn}' operation '{op}'"
            )

        vs = checks.get("visibility", {})
        for sub in ("viewport", "render"):
            v = vs.get(sub, {})
            if v.get("result") == "ERROR":
                op = v.get("operation", "UNKNOWN")
                err_msgs.append(
                    f"VISIBILITY_READ_ERROR: target '{tid}' "
                    f"root_object_name '{rn}' operation '{op}'"
                )

        rot = checks.get("rotation", {})
        if rot.get("result") == "ERROR":
            op = rot.get("operation", "UNKNOWN")
            err_msgs.append(
                f"ROTATION_COMPUTATION_ERROR: target '{tid}' "
                f"root_object_name '{rn}' operation '{op}'"
            )

        # Ground Contact
        gc = checks.get("ground_contact", {})
        if gc.get("result") == "ERROR":
            op = gc.get("operation", "UNKNOWN")
            err_msgs.append(
                f"GROUND_CONTACT_COMPUTATION_ERROR: target '{tid}' "
                f"root_object_name '{rn}' operation '{op}'"
            )

        # Material Assignment
        ma = checks.get("material_assignment_presence_check", {})
        if ma.get("result") == "ERROR":
            per_mesh = ma.get("per_mesh")
            if per_mesh is not None:
                ma_errors = []
                for pm in per_mesh:
                    if pm.get("result") == "ERROR":
                        op = pm.get("operation", "UNKNOWN")
                        mn = pm.get("mesh_name", "")
                        msg = (
                            f"MATERIAL_ASSIGNMENT_COMPUTATION_ERROR: target '{tid}' "
                            f"material_assignment operation '{op}' mesh '{mn}'"
                        )
                        ma_errors.append((op, mn, msg))
                ma_errors.sort(key=lambda item: (item[0], item[1]))
                err_msgs.extend(item[2] for item in ma_errors)
            else:
                op = ma.get("operation", "UNKNOWN")
                err_msgs.append(
                    f"MATERIAL_ASSIGNMENT_COMPUTATION_ERROR: target '{tid}' "
                    f"material_assignment operation '{op}'"
                )

        anim_state = checks.get("animation_state", {})
        if anim_state.get("result") == "ERROR":
            sub_order = ["animation_object", "animation_data", "action_name",
                         "pose_position", "current_frame"]
            for sub_key in sub_order:
                sub = anim_state.get(sub_key, {})
                if sub.get("result") == "ERROR":
                    op = sub.get("operation", "UNKNOWN")
                    err_msgs.append(
                        f"ANIMATION_STATE_COMPUTATION_ERROR: target '{tid}' "
                        f"animation_state operation '{op}'"
                    )

        # Camera Check
        cc = checks.get("camera_check", {})
        if cc.get("result") == "ERROR":
            op = cc.get("operation", "UNKNOWN")
            err_msgs.append(
                f"CAMERA_CHECK_COMPUTATION_ERROR: target '{tid}' "
                f"root_object_name '{rn}' operation '{op}'"
            )

        # Collection Rules
        cr = checks.get("collection_membership", {})
        if cr.get("result") == "ERROR":
            op = cr.get("operation", "UNKNOWN")
            cn = cr.get("collection_name", "")
            if cn:
                msg = (
                    f"COLLECTION_RULES_COMPUTATION_ERROR: target '{tid}' "
                    f"collection_rules operation '{op}' collection '{cn}'"
                )
            else:
                msg = (
                    f"COLLECTION_RULES_COMPUTATION_ERROR: target '{tid}' "
                    f"collection_rules operation '{op}'"
                )
            collection_rule_errors.append((op, cn, msg))

    collection_rule_errors.sort(key=lambda item: (item[0], item[1]))
    err_msgs.extend(item[2] for item in collection_rule_errors)
    return err_msgs


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parsed, arg_err = _parse_args(argv)
    if arg_err:
        _bootstrap_error(arg_err)

    # Setup paths before importing 14A
    deps = parsed["deps_path"]
    sys.path.insert(0, deps)

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    try:
        from protocol_guard.phase3_min.asset_scene_preflight_core import (
            serialize_result_line, error_boundary,
        )
    except ImportError as e:
        _bootstrap_error(f"Cannot import 14A core after adding dependency path: {e}")

    exit_code, result = error_boundary(_validate_and_open_spec, parsed["spec_path"])
    print(serialize_result_line(result), end="", flush=True)
    sys.exit(exit_code)


def _validate_and_open_spec(spec_path):
    """Validated entry: load -> schema -> pre-open -> path -> Reader -> open.

    Exposed as module-level function so entry-order tests can monkeypatch
    validate_spec_paths and verify that pre-open errors block path validation.
    """
    from protocol_guard.phase3_min.asset_scene_preflight_core import (
        load_spec_bytes, parse_spec_json, validate_spec, validate_spec_paths,
        build_pass_result, build_fail_result, build_error_result,
        EXIT_PASS, EXIT_FAIL, EXIT_ERROR,
    )
    from protocol_guard.phase2_min.io_utils import sha256_file

    # 1. Load spec file
    raw, load_err = load_spec_bytes(spec_path)
    if raw is None:
        return (EXIT_ERROR, build_error_result({}, "", [load_err]))

    spec_sha = sha256_file(spec_path)

    # 2. Parse and validate spec structure (schema only, no paths)
    spec, parse_err = parse_spec_json(raw)
    if spec is None:
        return (EXIT_ERROR, build_error_result({}, spec_sha, [parse_err]))

    errs = validate_spec(spec)
    if errs:
        return (EXIT_ERROR, build_error_result({}, spec_sha, errs))

    # 3. Pre-open configuration checks BEFORE path validation
    targets = spec.get("targets", [])
    pre_open_errs = _validate_direct_child_rules_preopen(targets)
    standing_errs = _validate_standing_up_axis_rules_preopen(targets)
    pre_open_errs.extend(standing_errs)
    facing_errs = _validate_facing_forward_axis_rules_preopen(targets)
    pre_open_errs.extend(facing_errs)
    rotation_errs = _validate_rotation_rules_preopen(targets)
    pre_open_errs.extend(rotation_errs)
    gc_errs = _validate_ground_contact_rules_preopen(targets)
    pre_open_errs.extend(gc_errs)
    cc_errs = _validate_camera_check_rules_preopen(targets)
    pre_open_errs.extend(cc_errs)
    pg_errs = _validate_projection_groups_rules_preopen(spec)
    pre_open_errs.extend(pg_errs)
    if pre_open_errs:
        return (EXIT_ERROR, build_error_result(spec, spec_sha, pre_open_errs))

    # 4. Path validation (only if all pre-open checks pass)
    repo_root = spec.get("repository_root", "")
    blend_path = spec.get("blend_path", "")
    abs_blend, path_err = validate_spec_paths(repo_root, blend_path)
    if path_err:
        return (EXIT_ERROR, build_error_result(spec, spec_sha, [path_err]))

    import protocol_guard.phase3_min.blender_scene_reader as reader
    scene_rules = spec.get("scene_rules")
    collection_rules_block = spec.get("collection_rules")
    projection_groups_block = spec.get("projection_groups")
    scene_data = reader.open_blend_and_get_scene(
        abs_blend, spec["scene_name"], scene_rules, targets,
        collection_rules_block=collection_rules_block,
        projection_groups_block=projection_groups_block,
    )

    if "error" in scene_data:
        return (EXIT_ERROR, build_error_result(spec, spec_sha,
                [f"{scene_data.get('error_type', 'OPEN_ERROR')}: {scene_data['error']}"]))

    scene_basic = scene_data.get("scene_basic", {})
    per_target_results = scene_data.get("per_target_results", [])
    pg_results = scene_data.get("projection_group_results", [])

    projection_group_overall = _compute_projection_group_overall(pg_results)

    global_results = scene_data.get("global_results")
    if not isinstance(global_results, dict):
        global_results = {"scene_basic": scene_basic}
    else:
        global_results.setdefault("scene_basic", scene_basic)

    global_cr = global_results.get("collection_rules", {})
    global_collection_error = (
        isinstance(global_cr, dict)
        and global_cr.get("result") == "ERROR"
    )
    global_collection_fail = (
        isinstance(global_cr, dict)
        and global_cr.get("result") == "FAIL"
    )

    target_error = any(
        t.get("overall") == "ERROR"
        for t in per_target_results
    )
    if target_error or global_collection_error or projection_group_overall == "ERROR":
        err_msgs = []
        if global_collection_error:
            operation = global_cr.get("operation", "UNKNOWN")
            err_msgs.append(
                "COLLECTION_RULES_COMPUTATION_ERROR: "
                f"global collection_rules operation '{operation}'"
            )
        if target_error:
            err_msgs.extend(_collect_target_errors(per_target_results))
        if projection_group_overall == "ERROR":
            for pg in pg_results:
                if pg.get("result") == "ERROR":
                    err_msgs.append(
                        "PROJECTION_GROUP_COMPUTATION_ERROR: "
                        f"group_id='{pg.get('group_id','')}' "
                        f"operation='{pg.get('operation','UNKNOWN')}'"
                    )
        return (EXIT_ERROR, build_error_result(spec, spec_sha, err_msgs,
                projection_groups=pg_results))

    any_scene_fail = any(
        v.get("result") == "FAIL"
        for v in scene_basic.values()
        if isinstance(v, dict)
    )
    any_target_fail = any(
        t.get("overall") == "FAIL"
        for t in per_target_results
    )

    if any_scene_fail or any_target_fail or global_collection_fail or projection_group_overall == "FAIL":
        return (EXIT_FAIL, build_fail_result(spec, spec_sha,
                per_target=per_target_results, global_r=global_results,
                projection_groups=pg_results))
    return (EXIT_PASS, build_pass_result(spec, spec_sha,
            per_target=per_target_results, global_r=global_results,
            projection_groups=pg_results))


if __name__ == "__main__":
    main()
