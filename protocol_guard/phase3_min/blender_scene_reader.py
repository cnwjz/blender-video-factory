"""Blender scene reader — basic scene facts + root object identity via bpy.

This module MUST be executed inside a Blender process (import bpy).
It reads the currently-loaded or opened .blend file and returns
plain Python dicts. No bpy/material/mathutils objects leak to callers.
"""

import bpy


def _check_direct_children(scene, root_obj, target):
    """Check direct children of a verified root object in the target scene.

    Only called when root_object exists and type matches (14B-2A PASS).
    Reads only root_obj.children + scene.objects membership.
    Includes exception boundaries for DIRECT_CHILD_LOOKUP_ERROR.

    Args:
        scene: bpy Scene for membership verification.
        root_obj: The verified unique root object.
        target: Target dict from spec.

    Returns: direct_children result dict.
    """
    hierarchy = target.get("hierarchy")
    if not isinstance(hierarchy, dict):
        return {"result": "NOT_CHECKED", "note": "HIERARCHY_NOT_CONFIGURED"}

    required = hierarchy.get("required_direct_child_names")
    allowed = hierarchy.get("allowed_direct_child_names")
    forbidden = hierarchy.get("forbidden_direct_child_name_patterns")

    has_any = (required is not None or allowed is not None or forbidden is not None)
    if not has_any:
        return {"result": "NOT_CHECKED", "note": "DIRECT_CHILD_RULES_NOT_CONFIGURED"}

    # Deduplicate spec lists (set semantics, case-sensitive)
    required_dedup = None
    if required is not None and isinstance(required, list):
        seen = set()
        required_dedup = []
        for item in required:
            if isinstance(item, str) and item not in seen:
                seen.add(item)
                required_dedup.append(item)

    allowed_dedup = None
    if allowed is not None and isinstance(allowed, list):
        seen = set()
        allowed_dedup = []
        for item in allowed:
            if isinstance(item, str) and item not in seen:
                seen.add(item)
                allowed_dedup.append(item)

    forbidden_dedup = None
    if forbidden is not None and isinstance(forbidden, list):
        seen = set()
        forbidden_dedup = []
        for item in forbidden:
            if isinstance(item, str) and item not in seen:
                seen.add(item)
                forbidden_dedup.append(item)

    # Collect scene-membership-filtered direct children using Python identity
    try:
        scene_objects = list(scene.objects)
    except Exception:
        return _lookup_error("READ_SCENE_OBJECTS")

    try:
        raw_children = list(root_obj.children)
    except Exception:
        return _lookup_error("READ_ROOT_CHILDREN")

    scene_children = [
        child
        for child in raw_children
        if any(child is sobj for sobj in scene_objects)
    ]

    # Read child names with exception boundary
    try:
        actual_names_raw = [c.name for c in scene_children]
    except Exception:
        return _lookup_error("READ_CHILD_NAME")

    # Sort actual names deterministically
    actual_names = sorted(actual_names_raw, key=lambda n: (n.casefold(), n))

    # Duplicate name detection
    from collections import Counter
    name_counts = Counter(actual_names)
    duplicates = {n: c for n, c in name_counts.items() if c > 1}
    if duplicates:
        return {
            "result": "ERROR",
            "error_type": "AMBIGUOUS_DIRECT_CHILD_NAME",
            "ambiguous_name_counts": dict(sorted(duplicates.items(), key=lambda x: (x[0].casefold(), x[0]))),
        }

    # --- Forbidden check (run first for dedup) ---
    forbidden_result = _build_forbidden_result(forbidden_dedup, actual_names)

    # --- Required check ---
    required_result = _build_required_result(required_dedup, actual_names)

    # --- Allowed check (excludes forbidden matches) ---
    allowed_result = _build_allowed_result(allowed_dedup, actual_names, forbidden_result)

    # --- Aggregate sub-results ---
    sub_results = [required_result["result"], allowed_result["result"], forbidden_result["result"]]
    dc_result = _aggregate_check_results(sub_results)

    return {
        "result": dc_result,
        "actual_names": actual_names,
        "required": required_result,
        "allowed": allowed_result,
        "forbidden": forbidden_result,
    }


def _aggregate_check_results(results):
    """Aggregate check sub-results with priority: ERROR > FAIL > PASS."""
    if "ERROR" in results:
        return "ERROR"
    elif "FAIL" in results:
        return "FAIL"
    else:
        return "PASS"


def _lookup_error(operation):
    """Build a stable DIRECT_CHILD_LOOKUP_ERROR result."""
    return {
        "result": "ERROR",
        "error_type": "DIRECT_CHILD_LOOKUP_ERROR",
        "operation": operation,
        "note": operation + "_FAILED",
    }


def _build_required_result(required, actual_names):
    if required is None:
        return {
            "result": "NOT_CHECKED",
            "required_expected_names": None,
            "required_missing_names": None,
            "note": "REQUIRED_DIRECT_CHILD_NAMES_NOT_CONFIGURED",
        }
    required_list = list(required)
    required_list.sort(key=lambda n: (n.casefold(), n))
    actual_set = set(actual_names)
    missing = [r for r in required_list if r not in actual_set]
    missing.sort(key=lambda n: (n.casefold(), n))
    if missing:
        return {
            "result": "FAIL",
            "required_expected_names": required_list,
            "required_missing_names": missing,
            "failure_code": "REQUIRED_DIRECT_CHILD_MISSING",
        }
    if len(required_list) == 0:
        return {"result": "PASS", "required_expected_names": [], "required_missing_names": []}
    return {"result": "PASS", "required_expected_names": required_list, "required_missing_names": []}


def _build_allowed_result(allowed, actual_names, forbidden_result):
    if allowed is None:
        return {
            "result": "NOT_CHECKED",
            "allowed_expected_names": None,
            "allowed_unexpected_names": None,
            "note": "ALLOWED_DIRECT_CHILD_NAMES_NOT_CONFIGURED",
        }
    allowed_list = list(allowed)
    allowed_list.sort(key=lambda n: (n.casefold(), n))
    allowed_set = set(allowed_list)

    forbidden_names = set()
    if forbidden_result is not None and forbidden_result.get("result") == "FAIL":
        forbidden_names = set(forbidden_result.get("forbidden_match_names", []))

    unexpected = [
        n for n in actual_names
        if n not in allowed_set and n not in forbidden_names
    ]
    unexpected.sort(key=lambda n: (n.casefold(), n))

    if unexpected:
        return {
            "result": "FAIL",
            "allowed_expected_names": allowed_list,
            "allowed_unexpected_names": unexpected,
            "failure_code": "UNEXPECTED_DIRECT_CHILD",
        }
    if len(allowed_list) == 0:
        return {"result": "PASS", "allowed_expected_names": [], "allowed_unexpected_names": []}
    return {"result": "PASS", "allowed_expected_names": allowed_list, "allowed_unexpected_names": []}


def _build_forbidden_result(forbidden, actual_names):
    if forbidden is None:
        return {
            "result": "NOT_CHECKED",
            "forbidden_patterns": None,
            "forbidden_match_names": None,
            "note": "FORBIDDEN_DIRECT_CHILD_NAME_PATTERNS_NOT_CONFIGURED",
        }
    from protocol_guard.phase3_min.asset_scene_preflight_core import casefold_glob_match
    forbidden_list = list(forbidden)
    forbidden_list.sort(key=lambda n: (n.casefold(), n))
    matches = []
    for name in actual_names:
        for pat in forbidden_list:
            if casefold_glob_match(name, pat):
                matches.append(name)
                break
    matches.sort(key=lambda n: (n.casefold(), n))
    if matches:
        return {
            "result": "FAIL",
            "forbidden_patterns": forbidden_list,
            "forbidden_match_names": matches,
            "failure_code": "FORBIDDEN_DIRECT_CHILD_NAME",
        }
    if len(forbidden_list) == 0:
        return {"result": "PASS", "forbidden_patterns": [], "forbidden_match_names": []}
    return {"result": "PASS", "forbidden_patterns": forbidden_list, "forbidden_match_names": []}


def _descendant_lookup_error(operation):
    """Build a stable DESCENDANT_LOOKUP_ERROR result."""
    return {
        "result": "ERROR",
        "error_type": "DESCENDANT_LOOKUP_ERROR",
        "operation": operation,
        "note": operation + "_FAILED",
    }


def _collect_descendants(scene, root_obj):
    """Recursively collect all descendant objects within the target scene.

    Uses Python identity (is) for scene membership. Excludes root_obj itself.
    Only traverses children that are themselves scene members.

    Args:
        scene: bpy Scene for membership verification.
        root_obj: The verified unique root object.

    Returns: (items, error) where items is list of (name, obj) tuples sorted
    by name, and error is None. On read failure, items is None and error is
    a DESCENDANT_LOOKUP_ERROR dict.
    """
    try:
        scene_objects = list(scene.objects)
    except Exception:
        return (None, _descendant_lookup_error("READ_SCENE_OBJECTS"))

    scene_id_set = {id(so) for so in scene_objects}
    collected = []
    try:
        stack = list(root_obj.children)
    except Exception:
        return (None, _descendant_lookup_error("READ_ROOT_CHILDREN"))
    visited_ids = {id(root_obj)}

    while stack:
        child = stack.pop()
        cid = id(child)
        if cid in visited_ids:
            continue
        visited_ids.add(cid)
        if cid not in scene_id_set:
            continue
        # Scene member — record (by identity, not by name)
        try:
            child_name = child.name
        except Exception:
            return (None, _descendant_lookup_error("READ_DESCENDANT_NAME"))
        collected.append((child_name, child))
        try:
            child_children = list(child.children)
        except Exception:
            return (None, _descendant_lookup_error("READ_DESCENDANT_CHILDREN"))
        for gc in child_children:
            if id(gc) not in visited_ids:
                stack.append(gc)

    return (sorted(collected, key=lambda x: (x[0].casefold(), x[0])), None)


def _check_descendants(scene, root_obj, target):
    """Check required_descendant_names + forbidden_descendant_name_patterns
    against all scene-member descendants.

    Only called when root_object exists and type matches.

    Args:
        scene: bpy Scene for membership verification.
        root_obj: The verified unique root object.
        target: Target dict from spec.

    Returns: descendants result dict.
    """
    hierarchy = target.get("hierarchy")
    if not isinstance(hierarchy, dict):
        return {"result": "NOT_CHECKED", "note": "HIERARCHY_NOT_CONFIGURED"}

    req_desc = hierarchy.get("required_descendant_names")
    forb_desc = hierarchy.get("forbidden_descendant_name_patterns")
    req_types = hierarchy.get("required_descendant_types")

    has_any = (req_desc is not None or forb_desc is not None or req_types is not None)
    if not has_any:
        return {
            "result": "NOT_CHECKED",
            "note": "DESCENDANT_RULES_NOT_CONFIGURED",
            "required": _build_descendant_required(None, []),
            "forbidden": _build_descendant_forbidden(None, []),
            "required_types": _build_descendant_required_types(None, []),
        }

    # Collect descendants
    desc_items, lookup_err = _collect_descendants(scene, root_obj)
    if lookup_err is not None:
        return lookup_err  # DESCENDANT_LOOKUP_ERROR takes priority

    actual_names = [name for name, _obj in desc_items]

    # Check type on ALL required_descendant_types referenced objects
    # BEFORE checking ambiguity — READ_DESCENDANT_TYPE > AMBIGUITY
    # Cache values by object identity so builder never re-reads .type
    type_cache = {}
    if req_types is not None and isinstance(req_types, dict):
        for name in sorted(req_types.keys(), key=lambda n: (n.casefold(), n)):
            for nm, obj in desc_items:
                if nm == name:
                    oid = id(obj)
                    if oid not in type_cache:
                        try:
                            type_cache[oid] = obj.type
                        except Exception:
                            return {
                                "result": "ERROR",
                                "error_type": "DESCENDANT_LOOKUP_ERROR",
                                "operation": "READ_DESCENDANT_TYPE",
                                "descendant_name": name,
                                "note": "READ_DESCENDANT_TYPE_FAILED",
                            }

    # Check for ambiguous (duplicate identity) descendant names
    from collections import Counter
    name_counts = Counter(actual_names)
    duplicates = {n: c for n, c in name_counts.items() if c > 1}
    if duplicates:
        return {
            "result": "ERROR",
            "error_type": "AMBIGUOUS_DESCENDANT_NAME",
            "ambiguous_name_counts": dict(sorted(duplicates.items(), key=lambda x: (x[0].casefold(), x[0]))),
        }

    # --- Required check ---
    req_result = _build_descendant_required(req_desc, actual_names)

    # --- Forbidden check ---
    forb_result = _build_descendant_forbidden(forb_desc, actual_names)

    # --- Required types check (uses cached type values, never re-reads .type) ---
    types_result = _build_descendant_required_types(req_types, desc_items, type_cache)

    # --- Aggregate ---
    sub_results = [req_result["result"], forb_result["result"], types_result["result"]]
    if "ERROR" in sub_results:
        dc_result = "ERROR"
    elif "FAIL" in sub_results:
        dc_result = "FAIL"
    else:
        dc_result = "PASS"

    result = {
        "result": dc_result,
        "actual_names": actual_names,
        "required": req_result,
        "forbidden": forb_result,
        "required_types": types_result,
    }

    return result


def _build_descendant_required(req_desc, actual_names):
    if req_desc is None:
        return {
            "result": "NOT_CHECKED",
            "required_expected_names": None,
            "required_missing_names": None,
            "note": "REQUIRED_DESCENDANT_NAMES_NOT_CONFIGURED",
        }
    seen = set()
    req_list = []
    for item in req_desc:
        if isinstance(item, str) and item not in seen:
            seen.add(item)
            req_list.append(item)
    req_list.sort(key=lambda n: (n.casefold(), n))
    actual_set = set(actual_names)
    missing = [r for r in req_list if r not in actual_set]
    missing.sort(key=lambda n: (n.casefold(), n))
    if len(req_list) == 0:
        return {"result": "PASS", "required_expected_names": [], "required_missing_names": []}
    if missing:
        return {
            "result": "FAIL",
            "required_expected_names": req_list,
            "required_missing_names": missing,
            "failure_code": "REQUIRED_DESCENDANT_MISSING",
        }
    return {"result": "PASS", "required_expected_names": req_list, "required_missing_names": []}


def _build_descendant_forbidden(forb_desc, actual_names):
    if forb_desc is None:
        return {
            "result": "NOT_CHECKED",
            "forbidden_patterns": None,
            "forbidden_match_names": None,
            "note": "FORBIDDEN_DESCENDANT_NAME_PATTERNS_NOT_CONFIGURED",
        }
    from protocol_guard.phase3_min.asset_scene_preflight_core import casefold_glob_match
    seen = set()
    forb_list = []
    for item in forb_desc:
        if isinstance(item, str) and item not in seen:
            seen.add(item)
            forb_list.append(item)
    forb_list.sort(key=lambda n: (n.casefold(), n))
    matches = []
    for name in actual_names:
        for pat in forb_list:
            if casefold_glob_match(name, pat):
                matches.append(name)
                break
    matches = sorted(set(matches), key=lambda n: (n.casefold(), n))
    if len(forb_list) == 0:
        return {"result": "PASS", "forbidden_patterns": [], "forbidden_match_names": []}
    if matches:
        return {
            "result": "FAIL",
            "forbidden_patterns": forb_list,
            "forbidden_match_names": matches,
            "failure_code": "FORBIDDEN_DESCENDANT_NAME",
        }
    return {"result": "PASS", "forbidden_patterns": forb_list, "forbidden_match_names": []}


def _build_descendant_required_types(req_types, desc_items, type_cache=None):
    """Check required_descendant_types against descendant objects.

    Args:
        req_types: dict of {name: expected_type} or None.
        desc_items: list of (name, obj) tuples from _collect_descendants.
        type_cache: dict mapping id(obj) -> type value. Builder uses
            cached values and must NOT access obj.type directly.

    Returns: required_types result dict.
    """
    if type_cache is None:
        type_cache = {}
    if req_types is None:
        return {
            "result": "NOT_CHECKED",
            "checks": None,
            "note": "REQUIRED_DESCENDANT_TYPES_NOT_CONFIGURED",
        }
    if not isinstance(req_types, dict):
        return {
            "result": "NOT_CHECKED",
            "checks": None,
            "note": "REQUIRED_DESCENDANT_TYPES_NOT_CONFIGURED",
        }

    if len(req_types) == 0:
        return {"result": "PASS", "checks": []}

    # Build name-to-object map from descendants (by identity, not name)
    name_to_objs = {}
    for name, obj in desc_items:
        if name not in name_to_objs:
            name_to_objs[name] = []
        name_to_objs[name].append(obj)

    checks = []
    for name in sorted(req_types.keys(), key=lambda n: (n.casefold(), n)):
        expected_type = req_types[name]
        objs = name_to_objs.get(name, [])

        if len(objs) == 0:
            checks.append({
                "name": name,
                "expected_type": expected_type,
                "actual_type": None,
                "result": "FAIL",
                "failure_code": "REQUIRED_DESCENDANT_FOR_TYPE_NOT_FOUND",
            })
        else:
            oid = id(objs[0])
            actual_type = type_cache[oid]
            match = (actual_type == expected_type)
            checks.append({
                "name": name,
                "expected_type": expected_type,
                "actual_type": actual_type,
                "result": "PASS" if match else "FAIL",
            })
            if not match:
                checks[-1]["failure_code"] = "REQUIRED_DESCENDANT_TYPE_MISMATCH"

    has_fail = any(c["result"] == "FAIL" for c in checks)
    return {
        "result": "FAIL" if has_fail else "PASS",
        "checks": checks,
    }


def _check_standing_up_axis(target, root_obj):
    """Check standing up_axis: PASS/FAIL/NOT_CHECKED only.

    No runtime ERROR handling in I1B. Returns NOT_CHECKED if any of the
    three up_axis fields is None. Uses axis_to_vector, vector_angle_degrees
    from locked 14A core.

    Args:
        target: Target dict from spec.
        root_obj: The verified unique root object.

    Returns: standing result dict.
    """
    standing = target.get("standing")
    if not isinstance(standing, dict):
        return {
            "result": "NOT_CHECKED",
            "up_axis": {"result": "NOT_CHECKED", "note": "UP_AXIS_RULES_NOT_CONFIGURED"},
        }

    local_up = standing.get("local_up_axis")
    expected_up = standing.get("expected_world_up_axis")
    tolerance = standing.get("up_axis_tolerance_degrees")

    if local_up is None and expected_up is None and tolerance is None:
        return {
            "result": "NOT_CHECKED",
            "up_axis": {"result": "NOT_CHECKED", "note": "UP_AXIS_RULES_NOT_CONFIGURED"},
        }

    # All three must be configured at this point (pre-open ensures this)
    from protocol_guard.phase3_min.asset_scene_preflight_core import (
        axis_to_vector, vector_angle_degrees,
    )
    import mathutils
    import math

    local_vec = axis_to_vector(local_up)
    expected_vec = axis_to_vector(expected_up)

    # Step 1: Read matrix_world (at most once)
    try:
        mw = root_obj.matrix_world
    except Exception:
        return {
            "result": "ERROR",
            "up_axis": {
                "result": "ERROR",
                "error_type": "STANDING_UP_AXIS_ERROR",
                "operation": "READ_ROOT_MATRIX_WORLD",
                "note": "READ_ROOT_MATRIX_WORLD_FAILED",
            },
        }

    # Step 2: Convert to 3x3 (at most once)
    try:
        m3 = mw.to_3x3()
    except Exception:
        return {
            "result": "ERROR",
            "up_axis": {
                "result": "ERROR",
                "error_type": "STANDING_UP_AXIS_ERROR",
                "operation": "CONVERT_ROOT_MATRIX_WORLD_TO_3X3",
                "note": "CONVERT_ROOT_MATRIX_WORLD_TO_3X3_FAILED",
            },
        }

    # Step 3: Transform local up axis
    try:
        world_up_v = m3 @ mathutils.Vector(local_vec)
        world_up = (world_up_v.x, world_up_v.y, world_up_v.z)
    except Exception:
        return {
            "result": "ERROR",
            "up_axis": {
                "result": "ERROR",
                "error_type": "STANDING_UP_AXIS_ERROR",
                "operation": "TRANSFORM_LOCAL_UP_AXIS",
                "note": "TRANSFORM_LOCAL_UP_AXIS_FAILED",
            },
        }

    # Step 4: Validate and normalize
    # Check for non-finite components
    if not (math.isfinite(world_up[0]) and math.isfinite(world_up[1]) and math.isfinite(world_up[2])):
        return {
            "result": "ERROR",
            "up_axis": {
                "result": "ERROR",
                "error_type": "STANDING_UP_AXIS_ERROR",
                "operation": "NORMALIZE_WORLD_UP_AXIS",
                "note": "NONFINITE_WORLD_UP_VECTOR",
            },
        }

    try:
        length = math.sqrt(world_up[0]**2 + world_up[1]**2 + world_up[2]**2)
    except (OverflowError, ValueError):
        return {
            "result": "ERROR",
            "up_axis": {
                "result": "ERROR",
                "error_type": "STANDING_UP_AXIS_ERROR",
                "operation": "NORMALIZE_WORLD_UP_AXIS",
                "note": "NONFINITE_WORLD_UP_VECTOR",
            },
        }

    if not math.isfinite(length):
        return {
            "result": "ERROR",
            "up_axis": {
                "result": "ERROR",
                "error_type": "STANDING_UP_AXIS_ERROR",
                "operation": "NORMALIZE_WORLD_UP_AXIS",
                "note": "NONFINITE_WORLD_UP_VECTOR",
            },
        }

    if length == 0.0:
        return {
            "result": "ERROR",
            "up_axis": {
                "result": "ERROR",
                "error_type": "STANDING_UP_AXIS_ERROR",
                "operation": "NORMALIZE_WORLD_UP_AXIS",
                "note": "ZERO_LENGTH_UP_VECTOR",
            },
        }

    actual_world = [world_up[0]/length, world_up[1]/length, world_up[2]/length]

    # Step 5: Compute angle
    try:
        angle = vector_angle_degrees(actual_world, expected_vec)
    except Exception:
        return {
            "result": "ERROR",
            "up_axis": {
                "result": "ERROR",
                "error_type": "STANDING_UP_AXIS_ERROR",
                "operation": "COMPUTE_UP_AXIS_ANGLE",
                "note": "COMPUTE_UP_AXIS_ANGLE_FAILED",
            },
        }

    passes = (angle <= tolerance)

    return {
        "result": "PASS" if passes else "FAIL",
        "up_axis": {
            "result": "PASS" if passes else "FAIL",
            "local_up_axis": local_up,
            "expected_world_up_axis": expected_up,
            "actual_world_up_direction": actual_world,
            "angle_degrees": angle,
            "tolerance_degrees": tolerance,
        } | ({} if passes else {"failure_code": "STANDING_UP_AXIS_DEVIATION"}),
    }


def _check_facing_forward_axis(target, root_obj):
    """Check facing forward_axis: PASS/FAIL/NOT_CHECKED (I1 only).

    Reads matrix_world at most once. Uses axis_to_vector and
    vector_angle_degrees from locked 14A core. Algorithm is the same
    transform pipeline as Standing (design R2C1 Section 2).

    Args:
        target: Target dict from spec.
        root_obj: The verified unique root object.

    Returns: facing result dict.
    """
    facing = target.get("facing")
    if not isinstance(facing, dict):
        return {
            "result": "NOT_CHECKED",
            "forward_axis": {"result": "NOT_CHECKED", "note": "FORWARD_AXIS_RULES_NOT_CONFIGURED"},
        }

    local_fwd = facing.get("local_forward_axis")
    expected_fwd = facing.get("expected_world_forward_axis")
    tolerance = facing.get("facing_tolerance_degrees")

    if local_fwd is None or expected_fwd is None or tolerance is None:
        return {
            "result": "NOT_CHECKED",
            "forward_axis": {"result": "NOT_CHECKED", "note": "FORWARD_AXIS_RULES_NOT_CONFIGURED"},
        }

    from protocol_guard.phase3_min.asset_scene_preflight_core import (
        axis_to_vector, vector_angle_degrees,
    )
    import mathutils
    import math

    local_vec = axis_to_vector(local_fwd)
    expected_vec = axis_to_vector(expected_fwd)

    # Step 1: Read matrix_world (at most once)
    try:
        mw = root_obj.matrix_world
    except Exception:
        return {
            "result": "ERROR",
            "forward_axis": {
                "result": "ERROR",
                "error_type": "FACING_FORWARD_AXIS_ERROR",
                "operation": "READ_ROOT_MATRIX_WORLD",
                "note": "READ_ROOT_MATRIX_WORLD_FAILED",
            },
        }

    # Step 2: Convert to 3x3 (at most once)
    try:
        m3 = mw.to_3x3()
    except Exception:
        return {
            "result": "ERROR",
            "forward_axis": {
                "result": "ERROR",
                "error_type": "FACING_FORWARD_AXIS_ERROR",
                "operation": "CONVERT_ROOT_MATRIX_WORLD_TO_3X3",
                "note": "CONVERT_ROOT_MATRIX_WORLD_TO_3X3_FAILED",
            },
        }

    # Step 3: Transform local forward axis
    try:
        world_fwd_v = m3 @ mathutils.Vector(local_vec)
        world_fwd = (world_fwd_v.x, world_fwd_v.y, world_fwd_v.z)
    except Exception:
        return {
            "result": "ERROR",
            "forward_axis": {
                "result": "ERROR",
                "error_type": "FACING_FORWARD_AXIS_ERROR",
                "operation": "TRANSFORM_LOCAL_FORWARD_AXIS",
                "note": "TRANSFORM_LOCAL_FORWARD_AXIS_FAILED",
            },
        }

    # Step 4: Validate and normalize
    if not (math.isfinite(world_fwd[0]) and math.isfinite(world_fwd[1]) and math.isfinite(world_fwd[2])):
        return {
            "result": "ERROR",
            "forward_axis": {
                "result": "ERROR",
                "error_type": "FACING_FORWARD_AXIS_ERROR",
                "operation": "NORMALIZE_WORLD_FORWARD_AXIS",
                "note": "NONFINITE_WORLD_FORWARD_VECTOR",
            },
        }

    try:
        length = math.sqrt(world_fwd[0]**2 + world_fwd[1]**2 + world_fwd[2]**2)
    except (OverflowError, ValueError):
        return {
            "result": "ERROR",
            "forward_axis": {
                "result": "ERROR",
                "error_type": "FACING_FORWARD_AXIS_ERROR",
                "operation": "NORMALIZE_WORLD_FORWARD_AXIS",
                "note": "NONFINITE_WORLD_FORWARD_VECTOR",
            },
        }

    if not math.isfinite(length):
        return {
            "result": "ERROR",
            "forward_axis": {
                "result": "ERROR",
                "error_type": "FACING_FORWARD_AXIS_ERROR",
                "operation": "NORMALIZE_WORLD_FORWARD_AXIS",
                "note": "NONFINITE_WORLD_FORWARD_VECTOR",
            },
        }

    if length == 0.0:
        return {
            "result": "ERROR",
            "forward_axis": {
                "result": "ERROR",
                "error_type": "FACING_FORWARD_AXIS_ERROR",
                "operation": "NORMALIZE_WORLD_FORWARD_AXIS",
                "note": "ZERO_LENGTH_FORWARD_VECTOR",
            },
        }

    actual_world = [world_fwd[0]/length, world_fwd[1]/length, world_fwd[2]/length]

    # Step 5: Compute angle
    try:
        angle = vector_angle_degrees(actual_world, expected_vec)
    except Exception:
        return {
            "result": "ERROR",
            "forward_axis": {
                "result": "ERROR",
                "error_type": "FACING_FORWARD_AXIS_ERROR",
                "operation": "COMPUTE_FORWARD_AXIS_ANGLE",
                "note": "COMPUTE_FORWARD_AXIS_ANGLE_FAILED",
            },
        }

    passes = (angle <= tolerance)

    return {
        "result": "PASS" if passes else "FAIL",
        "forward_axis": {
            "result": "PASS" if passes else "FAIL",
            "local_forward_axis": local_fwd,
            "expected_world_forward_axis": expected_fwd,
            "actual_world_forward_direction": actual_world,
            "angle_degrees": angle,
            "tolerance_degrees": tolerance,
        } | ({} if passes else {"failure_code": "FACING_FORWARD_AXIS_DEVIATION"}),
    }


def _check_visibility(target, root_obj):
    """Check visibility: PASS/FAIL/NOT_CHECKED/ERROR.

    Only reads hide_viewport / hide_render when the corresponding
    require_not_hidden_* field is true. Each read at most once.
    Fields are independent — one ERROR does not block the other.
    """
    vis = target.get("visibility")
    if not isinstance(vis, dict):
        return {
            "result": "NOT_CHECKED",
            "viewport": {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"},
            "render": {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"},
        }

    req_vp = vis.get("require_not_hidden_viewport")
    req_hr = vis.get("require_not_hidden_render")

    vp_result = None
    hr_result = None
    vp_cache = None
    hr_cache = None

    # Viewport check
    if req_vp is True:
        try:
            vp_cache = root_obj.hide_viewport
        except Exception:
            vp_result = {
                "result": "ERROR",
                "error_type": "VISIBILITY_READ_ERROR",
                "operation": "READ_ROOT_HIDE_VIEWPORT",
                "note": "READ_ROOT_HIDE_VIEWPORT_FAILED",
            }
    else:
        vp_result = {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"}

    # Render check
    if req_hr is True:
        try:
            hr_cache = root_obj.hide_render
        except Exception:
            hr_result = {
                "result": "ERROR",
                "error_type": "VISIBILITY_READ_ERROR",
                "operation": "READ_ROOT_HIDE_RENDER",
                "note": "READ_ROOT_HIDE_RENDER_FAILED",
            }
    else:
        hr_result = {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"}

    # Build results from cache
    if vp_result is None:
        if vp_cache:
            vp_result = {"result": "FAIL", "failure_code": "OBJECT_HIDDEN_IN_VIEWPORT",
                         "require_not_hidden": True, "actual_hidden": True}
        else:
            vp_result = {"result": "PASS", "require_not_hidden": True, "actual_hidden": False}

    if hr_result is None:
        if hr_cache:
            hr_result = {"result": "FAIL", "failure_code": "OBJECT_HIDDEN_IN_RENDER",
                         "require_not_hidden": True, "actual_hidden": True}
        else:
            hr_result = {"result": "PASS", "require_not_hidden": True, "actual_hidden": False}

    # Aggregate: ERROR > FAIL > PASS > NOT_CHECKED
    if vp_result["result"] == "ERROR" or hr_result["result"] == "ERROR":
        overall = "ERROR"
    elif vp_result["result"] == "FAIL" or hr_result["result"] == "FAIL":
        overall = "FAIL"
    elif vp_result["result"] == "PASS" or hr_result["result"] == "PASS":
        overall = "PASS"
    else:
        overall = "NOT_CHECKED"

    return {
        "result": overall,
        "viewport": vp_result,
        "render": hr_result,
    }


def _expected_euler_to_quaternion(erw):
    """Convert [rx, ry, rz] in degrees to (w, x, y, z) quaternion tuple.

    Sole authorized Euler-to-quaternion conversion. Uses XYZ intrinsic
    Tait-Bryan order as locked in Rotation Design R3.

    Returns a 4-tuple of finite floats on success.
    Raises exceptions on conversion failure.
    """
    import math
    from mathutils import Euler

    rx, ry, rz = erw
    euler = Euler((
        math.radians(rx),
        math.radians(ry),
        math.radians(rz),
    ), 'XYZ')
    quat = euler.to_quaternion()
    quat.normalize()
    return (quat.w, quat.x, quat.y, quat.z)


def _check_rotation(target, root_obj):
    """Check rotation: I2 world quaternion + expected Euler conversion.

    I2 implements matrix_world.to_quaternion() extraction, expected
    Euler-to-quaternion conversion, and 7 ERROR branches for read/convert
    operations. Angle comparison and PASS/FAIL are deferred to I3.
    """
    import math

    rot = target.get("rotation")
    if not isinstance(rot, dict):
        return {
            "result": "NOT_CHECKED",
            "note": "REQUIREMENT_NOT_CONFIGURED",
        }

    erw = rot.get("expected_world_rotation_euler_degrees")
    if erw is None:
        return {
            "result": "NOT_CHECKED",
            "note": "REQUIREMENT_NOT_CONFIGURED",
        }
    tol = rot.get("rotation_tolerance_degrees")
    # tol is guaranteed present by pre-open validation

    # Step 1: Read matrix_world (at most once)
    try:
        mw = root_obj.matrix_world
    except Exception:
        return {
            "result": "ERROR",
            "error_type": "ROTATION_COMPUTATION_ERROR",
            "operation": "READ_ROOT_MATRIX_WORLD",
            "note": "READ_ROOT_MATRIX_WORLD_FAILED",
        }

    # Step 2: Convert to quaternion
    try:
        actual_quat = mw.to_quaternion()
    except Exception:
        return {
            "result": "ERROR",
            "error_type": "ROTATION_COMPUTATION_ERROR",
            "operation": "CONVERT_ROOT_MATRIX_WORLD_TO_QUATERNION",
            "note": "CONVERT_ROOT_MATRIX_WORLD_TO_QUATERNION_FAILED",
        }

    actual_tuple = (actual_quat.w, actual_quat.x, actual_quat.y, actual_quat.z)
    # Validate actual quaternion
    if any(math.isnan(v) or math.isinf(v) for v in actual_tuple):
        return {
            "result": "ERROR",
            "error_type": "ROTATION_COMPUTATION_ERROR",
            "operation": "CONVERT_ROOT_MATRIX_WORLD_TO_QUATERNION",
            "note": "NONFINITE_ROTATION_QUATERNION",
        }
    la = math.sqrt(sum(v * v for v in actual_tuple))
    if la == 0.0:
        return {
            "result": "ERROR",
            "error_type": "ROTATION_COMPUTATION_ERROR",
            "operation": "CONVERT_ROOT_MATRIX_WORLD_TO_QUATERNION",
            "note": "ZERO_LENGTH_ROTATION_QUATERNION",
        }

    # Step 3: Convert expected Euler to quaternion
    try:
        expected_tuple = _expected_euler_to_quaternion(erw)
    except Exception:
        return {
            "result": "ERROR",
            "error_type": "ROTATION_COMPUTATION_ERROR",
            "operation": "CONVERT_EXPECTED_EULER_TO_QUATERNION",
            "note": "CONVERT_EXPECTED_EULER_TO_QUATERNION_FAILED",
        }

    # Validate expected quaternion
    if any(math.isnan(v) or math.isinf(v) for v in expected_tuple):
        return {
            "result": "ERROR",
            "error_type": "ROTATION_COMPUTATION_ERROR",
            "operation": "CONVERT_EXPECTED_EULER_TO_QUATERNION",
            "note": "NONFINITE_ROTATION_QUATERNION",
        }
    le = math.sqrt(sum(v * v for v in expected_tuple))
    if le == 0.0:
        return {
            "result": "ERROR",
            "error_type": "ROTATION_COMPUTATION_ERROR",
            "operation": "CONVERT_EXPECTED_EULER_TO_QUATERNION",
            "note": "ZERO_LENGTH_ROTATION_QUATERNION",
        }

    # Step 4: Compute quaternion angle
    from protocol_guard.phase3_min.asset_scene_preflight_core import (
        quaternion_min_angle_degrees,
    )
    try:
        angle_degrees = quaternion_min_angle_degrees(actual_tuple, expected_tuple)
    except Exception:
        return {
            "result": "ERROR",
            "error_type": "ROTATION_COMPUTATION_ERROR",
            "operation": "COMPUTE_ROTATION_ANGLE",
            "note": "COMPUTE_ROTATION_ANGLE_FAILED",
        }

    if math.isnan(angle_degrees) or math.isinf(angle_degrees):
        return {
            "result": "ERROR",
            "error_type": "ROTATION_COMPUTATION_ERROR",
            "operation": "COMPUTE_ROTATION_ANGLE",
            "note": "NONFINITE_ROTATION_ANGLE",
        }

    # Step 5: Tolerance comparison
    if angle_degrees <= tol:
        return {
            "result": "PASS",
            "expected_world_rotation_euler_degrees": erw,
            "expected_quaternion": list(expected_tuple),
            "actual_quaternion": list(actual_tuple),
            "angle_degrees": angle_degrees,
            "tolerance_degrees": tol,
        }
    else:
        return {
            "result": "FAIL",
            "failure_code": "OBJECT_ROTATION_OUT_OF_TOLERANCE",
            "expected_world_rotation_euler_degrees": erw,
            "expected_quaternion": list(expected_tuple),
            "actual_quaternion": list(actual_tuple),
            "angle_degrees": angle_degrees,
            "tolerance_degrees": tol,
        }


def _check_root_objects(scene, targets, _target_caches=None):
    """Check root object existence, type, and direct children for all targets.

    For each target, performs a FULL traversal of scene.objects counting
    case-sensitive exact name matches. Only reads object.type after confirming
    exactly one unique match. Direct children checked only when root exists
    and type matches.

    Args:
        scene: bpy Scene to search in (may be None if scene not found).
        targets: list of target dicts from spec.
        _target_caches: optional dict keyed by target_id, populated with
            per-target runtime cache for Camera Check reuse.
            Each cache entry: dict with scene_objects_ordered, scene_name_by_id,
            root_obj, scene_member_ids, scene_materialization_index.

    Returns: list of per_target_result dicts (empty if scene is None).
    """
    if scene is None:
        return []

    results = []

    for target in targets:
        target_id = target.get("target_id", "")
        root_name = target.get("root_object_name", "")
        expected_type = target.get("expected_root_type", "")

        match_count = 0
        matched_obj = None

        try:
            scene_objs = list(scene.objects)
        except Exception:
            results.append({
                "target_id": target_id,
                "root_object_name": root_name,
                "checks": {
                    "object_exists": {"result": "ERROR", "expected": True, "actual": None, "note": "DIRECT_CHILD_LOOKUP_ERROR"},
                    "object_type": {"result": "NOT_CHECKED", "expected": expected_type, "actual": None, "note": "DIRECT_CHILD_LOOKUP_ERROR"},
                    "direct_children": {"result": "ERROR", "error_type": "DIRECT_CHILD_LOOKUP_ERROR", "operation": "READ_SCENE_OBJECTS", "note": "READ_SCENE_OBJECTS_FAILED"},
                },
                "overall": "ERROR",
            })
            continue

        name_by_id = {}
        name_read_error = None
        try:
            for obj in scene_objs:
                oname = obj.name
                name_by_id[id(obj)] = oname
                if oname == root_name:
                    match_count += 1
                    if match_count == 1:
                        matched_obj = obj
                    else:
                        matched_obj = None
        except Exception as e:
            name_read_error = e
            # Record failure in per-target cache for Camera Check
            if _target_caches is not None and isinstance(target.get("camera_check"), dict):
                _target_caches[target_id] = {
                    "name_read_error": True,
                    "error_operation": "RESOLVE_CAMERA_OBJECT",
                }

        # If name read failed for a camera_check-enabled target,
        # build minimal result and let Camera Check consume the cache
        if name_read_error is not None:
            results.append({
                "target_id": target_id,
                "root_object_name": root_name,
                "checks": {
                    "object_exists": {"result": "ERROR", "expected": True, "actual": None, "note": "DIRECT_CHILD_LOOKUP_ERROR"},
                    "object_type": {"result": "NOT_CHECKED", "expected": expected_type, "actual": None, "note": "DIRECT_CHILD_LOOKUP_ERROR"},
                    "direct_children": {"result": "ERROR", "error_type": "DIRECT_CHILD_LOOKUP_ERROR", "operation": "READ_SCENE_OBJECTS", "note": "READ_SCENE_OBJECTS_FAILED"},
                },
                "overall": "ERROR",
            })
            continue

        if match_count == 0:
            results.append({
                "target_id": target_id,
                "root_object_name": root_name,
                "checks": {
                    "object_exists": {
                        "result": "FAIL",
                        "expected": True,
                        "actual": False,
                        "failure_code": "ROOT_OBJECT_NOT_FOUND",
                    },
                    "object_type": {
                        "result": "NOT_CHECKED",
                        "expected": expected_type,
                        "actual": None,
                        "note": "ROOT_OBJECT_NOT_FOUND",
                    },
                    "direct_children": {
                        "result": "NOT_CHECKED",
                        "note": "ROOT_OBJECT_NOT_FOUND",
                    },
                    "descendants": {
                        "result": "NOT_CHECKED",
                        "note": "ROOT_OBJECT_NOT_FOUND",
                    },
                    "standing": {
                        "result": "NOT_CHECKED",
                        "up_axis": {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_NOT_FOUND"},
                    },
                    "facing": {
                        "result": "NOT_CHECKED",
                        "forward_axis": {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_NOT_FOUND"},
                    },
                    "visibility": {
                        "result": "NOT_CHECKED",
                        "viewport": {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_NOT_FOUND"},
                        "render": {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_NOT_FOUND"},
                    },
                    "rotation": {
                        "result": "NOT_CHECKED",
                        "note": "ROOT_OBJECT_NOT_FOUND",
                    },
                    "camera_check": {
                        "result": "NOT_CHECKED",
                        "note": "ROOT_OBJECT_NOT_FOUND",
                    },
                },
                "overall": "FAIL",
            })
        elif match_count == 1:
            actual_type = matched_obj.type
            type_ok = (actual_type == expected_type)

            checks = {
                "object_exists": {
                    "result": "PASS",
                    "expected": True,
                    "actual": True,
                },
                "object_type": {
                    "result": "PASS" if type_ok else "FAIL",
                    "expected": expected_type,
                    "actual": actual_type,
                },
            }

            if not type_ok:
                checks["object_type"]["failure_code"] = "ROOT_OBJECT_TYPE_MISMATCH"
                checks["direct_children"] = {
                    "result": "NOT_CHECKED",
                    "note": "ROOT_OBJECT_TYPE_MISMATCH",
                }
                checks["descendants"] = {
                    "result": "NOT_CHECKED",
                    "note": "ROOT_OBJECT_TYPE_MISMATCH",
                }
                checks["standing"] = {
                    "result": "NOT_CHECKED",
                    "up_axis": {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_TYPE_MISMATCH"},
                }
                checks["facing"] = {
                    "result": "NOT_CHECKED",
                    "forward_axis": {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_TYPE_MISMATCH"},
                }
                checks["visibility"] = {
                    "result": "NOT_CHECKED",
                    "viewport": {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_TYPE_MISMATCH"},
                    "render": {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_TYPE_MISMATCH"},
                }
                checks["rotation"] = {
                    "result": "NOT_CHECKED",
                    "note": "ROOT_OBJECT_TYPE_MISMATCH",
                }
                checks["camera_check"] = {
                    "result": "NOT_CHECKED",
                    "note": "ROOT_OBJECT_TYPE_MISMATCH",
                }
                overall = "FAIL"
            else:
                # Root exists and type matches — check direct children + descendants
                # Populate per-target runtime cache for Camera Check reuse
                if _target_caches is not None and isinstance(target.get("camera_check"), dict):
                    _target_caches[target_id] = {
                        "scene_objects_ordered": scene_objs,
                        "scene_name_by_id": name_by_id,
                        "root_obj": matched_obj,
                        "scene_member_ids": {id(o) for o in scene_objs},
                        "scene_materialization_index": {id(o): idx for idx, o in enumerate(scene_objs)},
                    }
                dc = _check_direct_children(scene, matched_obj, target)
                checks["direct_children"] = dc
                dd = _check_descendants(scene, matched_obj, target)
                checks["descendants"] = dd
                su = _check_standing_up_axis(target, matched_obj)
                checks["standing"] = su
                ff = _check_facing_forward_axis(target, matched_obj)
                checks["facing"] = ff
                vis = _check_visibility(target, matched_obj)
                checks["visibility"] = vis
                rot = _check_rotation(target, matched_obj)
                checks["rotation"] = rot

                # Compute overall: ERROR > FAIL > PASS
                dc_r = dc.get("result")
                dd_r = dd.get("result")
                su_r = su.get("result")
                ff_r = ff.get("result")
                vis_r = vis.get("result")
                rot_r = rot.get("result")
                if dc_r == "ERROR" or dd_r == "ERROR" or su_r == "ERROR" or ff_r == "ERROR" or vis_r == "ERROR" or rot_r == "ERROR":
                    overall = "ERROR"
                elif dc_r == "FAIL" or dd_r == "FAIL" or su_r == "FAIL" or ff_r == "FAIL" or vis_r == "FAIL" or rot_r == "FAIL":
                    overall = "FAIL"
                else:
                    overall = "PASS"

            results.append({
                "target_id": target_id,
                "root_object_name": root_name,
                "checks": checks,
                "overall": overall,
            })
        else:
            results.append({
                "target_id": target_id,
                "root_object_name": root_name,
                "checks": {
                    "object_exists": {
                        "result": "ERROR",
                        "expected": True,
                        "actual": True,
                        "error_type": "AMBIGUOUS_ROOT_OBJECT_NAME",
                        "match_count": match_count,
                    },
                    "object_type": {
                        "result": "NOT_CHECKED",
                        "expected": expected_type,
                        "actual": None,
                        "note": "AMBIGUOUS_ROOT_OBJECT_NAME",
                    },
                    "direct_children": {
                        "result": "NOT_CHECKED",
                        "note": "AMBIGUOUS_ROOT_OBJECT_NAME",
                    },
                    "descendants": {
                        "result": "NOT_CHECKED",
                        "note": "AMBIGUOUS_ROOT_OBJECT_NAME",
                    },
                    "standing": {
                        "result": "NOT_CHECKED",
                        "up_axis": {"result": "NOT_CHECKED", "note": "AMBIGUOUS_ROOT_OBJECT_NAME"},
                    },
                    "facing": {
                        "result": "NOT_CHECKED",
                        "forward_axis": {"result": "NOT_CHECKED", "note": "AMBIGUOUS_ROOT_OBJECT_NAME"},
                    },
                    "visibility": {
                        "result": "NOT_CHECKED",
                        "viewport": {"result": "NOT_CHECKED", "note": "AMBIGUOUS_ROOT_OBJECT_NAME"},
                        "render": {"result": "NOT_CHECKED", "note": "AMBIGUOUS_ROOT_OBJECT_NAME"},
                    },
                    "rotation": {
                        "result": "NOT_CHECKED",
                        "note": "AMBIGUOUS_ROOT_OBJECT_NAME",
                    },
                    "camera_check": {
                        "result": "NOT_CHECKED",
                        "note": "AMBIGUOUS_ROOT_OBJECT_NAME",
                    },
                },
                "overall": "ERROR",
            })

    # Remove camera_check NOT_CHECKED entries for targets where
    # camera_check is not configured (missing or None).
    for idx, result in enumerate(results):
        if idx < len(targets):
            cc_block = targets[idx].get("camera_check")
            if not isinstance(cc_block, dict):
                result["checks"].pop("camera_check", None)
    return results


def _check_animation_state(scene, target):
    """Check animation state for a single target.

    Args:
        scene: bpy Scene to search in (may be None).
        target: target dict from spec.

    Returns: checks.animation_state result dict.
    """
    as_block = target.get("animation_state")
    if as_block is None or not isinstance(as_block, dict):
        return {"result": "NOT_CHECKED", "note": "ANIMATION_STATE_NOT_CONFIGURED"}

    obj_name = as_block.get("animation_object_name", "")

    # Look up animation object in scene
    match_count = 0
    matched_obj = None
    lookup_exception = False
    name_exception = False
    try:
        for obj in scene.objects:
            try:
                oname = obj.name
            except Exception:
                name_exception = True
                break
            if oname == obj_name:
                match_count += 1
                if match_count == 1:
                    matched_obj = obj
                else:
                    matched_obj = None
    except Exception:
        lookup_exception = True

    result = {}

    # animation_object sub-key
    if lookup_exception:
        result["animation_object"] = {
            "result": "ERROR",
            "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
            "operation": "LOOKUP_ANIMATION_OBJECT",
            "note": "LOOKUP_ANIMATION_OBJECT_FAILED",
        }
    elif name_exception:
        result["animation_object"] = {
            "result": "ERROR",
            "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
            "operation": "READ_ANIMATION_OBJECT_NAME",
            "note": "READ_ANIMATION_OBJECT_NAME_FAILED",
        }
    elif match_count == 0:
        result["animation_object"] = {
            "result": "FAIL",
            "failure_code": "ANIMATION_OBJECT_NOT_FOUND",
            "object_name": obj_name,
        }
    elif match_count > 1:
        result["animation_object"] = {
            "result": "ERROR",
            "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
            "operation": "RESOLVE_ANIMATION_OBJECT_NAME",
            "note": "AMBIGUOUS_ANIMATION_OBJECT_NAME",
        }
    else:
        result["animation_object"] = {
            "result": "PASS",
            "object_name": obj_name,
        }

    obj_ok = (match_count == 1 and not lookup_exception and not name_exception)

    req_ad = as_block.get("require_animation_data")
    ean = as_block.get("expected_action_name")
    ean_set = isinstance(ean, str) and ean != ""

    # Read obj.animation_data at most once (Design R5 §11.2 cache contract).
    # Cached when either require_animation_data=true or expected_action_name is set.
    ad_cached = None
    ad_exception = False
    if obj_ok and (req_ad is True or ean_set):
        try:
            ad_cached = matched_obj.animation_data
        except Exception:
            ad_exception = True

    # animation_data sub-key (MODEL_A: only when require_animation_data is true)
    if req_ad is True:
        if not obj_ok:
            result["animation_data"] = {
                "result": "NOT_CHECKED",
                "note": "ANIMATION_OBJECT_NOT_FOUND" if match_count == 0 else "ANIMATION_OBJECT_UNAVAILABLE",
            }
        elif ad_exception:
            result["animation_data"] = {
                "result": "ERROR",
                "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
                "operation": "READ_ANIMATION_DATA",
                "note": "READ_ANIMATION_DATA_FAILED",
            }
        elif ad_cached is None:
            result["animation_data"] = {
                "result": "FAIL",
                "failure_code": "ANIMATION_DATA_NOT_PRESENT",
            }
        else:
            result["animation_data"] = {
                "result": "PASS",
                "animation_data_present": True,
            }

    # action_name sub-key (MODEL_A: only when expected_action_name is non-null string)
    if ean_set:
        if not obj_ok:
            result["action_name"] = {
                "result": "NOT_CHECKED",
                "note": "ANIMATION_OBJECT_NOT_FOUND" if match_count == 0 else "ANIMATION_OBJECT_UNAVAILABLE",
            }
        elif req_ad is True and result.get("animation_data", {}).get("result") in ("FAIL", "ERROR"):
            result["action_name"] = {
                "result": "NOT_CHECKED",
                "note": "ANIMATION_DATA_NOT_AVAILABLE",
            }
        elif ad_exception:
            result["action_name"] = {
                "result": "ERROR",
                "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
                "operation": "READ_ANIMATION_DATA",
                "note": "READ_ANIMATION_DATA_FAILED",
            }
        elif ad_cached is None:
            result["action_name"] = {
                "result": "FAIL",
                "failure_code": "ACTION_NAME_MISMATCH",
            }
        else:
            action = None
            action_exception = False
            try:
                action = ad_cached.action
            except Exception:
                action_exception = True
            if action_exception:
                result["action_name"] = {
                    "result": "ERROR",
                    "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
                    "operation": "READ_ACTION_REFERENCE",
                    "note": "READ_ACTION_REFERENCE_FAILED",
                }
            elif action is None:
                result["action_name"] = {
                    "result": "FAIL",
                    "failure_code": "ACTION_NAME_MISMATCH",
                }
            else:
                aname = None
                aname_exception = False
                try:
                    aname = action.name
                except Exception:
                    aname_exception = True
                if aname_exception:
                    result["action_name"] = {
                        "result": "ERROR",
                        "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
                        "operation": "READ_ACTION_NAME",
                        "note": "READ_ACTION_NAME_FAILED",
                    }
                elif aname is None or aname != ean:
                    result["action_name"] = {
                        "result": "FAIL",
                        "failure_code": "ACTION_NAME_MISMATCH",
                    }
                else:
                    result["action_name"] = {
                        "result": "PASS",
                        "action_name": aname,
                    }

    # pose_position sub-key (MODEL_A: only when expected_pose_position is non-null string)
    epp = as_block.get("expected_pose_position")
    if isinstance(epp, str) and epp in ("POSE", "REST"):
        if not obj_ok:
            result["pose_position"] = {
                "result": "NOT_CHECKED",
                "note": "ANIMATION_OBJECT_NOT_FOUND" if match_count == 0 else "ANIMATION_OBJECT_UNAVAILABLE",
            }
        else:
            obj_data = None
            data_exception = False
            try:
                obj_data = matched_obj.data
            except Exception:
                data_exception = True
            if data_exception:
                result["pose_position"] = {
                    "result": "ERROR",
                    "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
                    "operation": "READ_OBJECT_DATA",
                    "note": "READ_OBJECT_DATA_FAILED",
                }
            elif obj_data is None:
                result["pose_position"] = {
                    "result": "ERROR",
                    "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
                    "operation": "READ_OBJECT_DATA",
                    "note": "READ_OBJECT_DATA_FAILED",
                }
            else:
                pp_val = None
                pp_exception = False
                try:
                    pp_val = obj_data.pose_position
                except Exception:
                    pp_exception = True
                if pp_exception:
                    result["pose_position"] = {
                        "result": "ERROR",
                        "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
                        "operation": "READ_POSE_POSITION",
                        "note": "READ_POSE_POSITION_FAILED",
                    }
                elif pp_val is None:
                    result["pose_position"] = {
                        "result": "FAIL",
                        "failure_code": "POSE_POSITION_MISMATCH",
                    }
                elif pp_val != epp:
                    result["pose_position"] = {
                        "result": "FAIL",
                        "failure_code": "POSE_POSITION_MISMATCH",
                    }
                else:
                    result["pose_position"] = {
                        "result": "PASS",
                        "pose_position": pp_val,
                    }

    # current_frame sub-key (MODEL_A: only when record_current_frame is true)
    rcf = as_block.get("record_current_frame")
    if rcf is True:
        cf = None
        cf_exception = False
        try:
            cf = scene.frame_current
        except Exception:
            cf_exception = True
        if cf_exception:
            result["current_frame"] = {
                "result": "ERROR",
                "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
                "operation": "READ_CURRENT_FRAME",
                "note": "READ_CURRENT_FRAME_FAILED",
            }
        else:
            result["current_frame"] = {
                "result": "PASS",
                "current_frame": cf,
            }

    # Top-level aggregation: scan all present sub-key results
    sub_results = [
        result[k]["result"]
        for k in result
        if isinstance(result[k], dict) and "result" in result[k]
    ]
    if any(r == "ERROR" for r in sub_results):
        result["result"] = "ERROR"
    elif any(r == "FAIL" for r in sub_results):
        result["result"] = "FAIL"
    else:
        result["result"] = "PASS"

    return result


def _check_material_slots_for_mesh(mesh_obj, mesh_name):
    """Check material slots for a single MESH object — I2 ERROR support.

    Reads mesh_obj.material_slots at most once, each slot.material at most once.
    Returns per_mesh PASS / FAIL / ERROR dict.

    I2 adds: READ_MATERIAL_SLOTS and READ_SLOT_MATERIAL ERROR branches.

    Args:
        mesh_obj: bpy.types.Object where obj.type == 'MESH'.
        mesh_name: cached name string.

    Returns: per_mesh result dict.
    """
    try:
        material_slots = list(mesh_obj.material_slots)
    except Exception:
        return {
            "mesh_name": mesh_name,
            "result": "ERROR",
            "error_type": "MATERIAL_ASSIGNMENT_COMPUTATION_ERROR",
            "operation": "READ_MATERIAL_SLOTS",
            "note": "READ_MATERIAL_SLOTS_FAILED",
        }

    if len(material_slots) == 0:
        return {
            "mesh_name": mesh_name,
            "result": "FAIL",
            "failure_code": "MESH_HAS_NO_MATERIAL_SLOTS",
        }

    null_indices = []
    for i, slot in enumerate(material_slots):
        try:
            mat = slot.material
        except Exception:
            return {
                "mesh_name": mesh_name,
                "result": "ERROR",
                "error_type": "MATERIAL_ASSIGNMENT_COMPUTATION_ERROR",
                "operation": "READ_SLOT_MATERIAL",
                "note": "READ_SLOT_MATERIAL_FAILED",
                "slot_index": i,
            }
        if mat is None:
            null_indices.append(i)

    if null_indices:
        return {
            "mesh_name": mesh_name,
            "result": "FAIL",
            "failure_code": "NULL_MATERIAL_SLOT",
            "null_slot_indices": null_indices,
        }

    return {
        "mesh_name": mesh_name,
        "result": "PASS",
        "slot_count": len(material_slots),
    }


def _collect_geometry_scope_objects(
    scene_objects_ordered,
    scene_member_ids,
    scene_materialization_index,
    scene_name_by_id,
    root_obj,
    root_type_value,
    geometry_scope_value,
):
    """Collect MESH objects within geometry scope.

    Does NOT read scene.objects, obj.name, or root_obj.type.
    Reads: root_obj.children, descendant.children, descendant.type.

    Args:
        scene_objects_ordered: list(scene.objects), ordered.
        scene_member_ids: set(id(obj) for obj in scene_objects_ordered).
        scene_materialization_index: dict(id(obj) → index in scene_objects_ordered).
        scene_name_by_id: dict(id(obj) → name), pre-built.
        root_obj: the unique root object.
        root_type_value: per_target_result.checks.object_type.actual.
        geometry_scope_value: one of SELF_MESH / DESCENDANT_MESHES / SELF_AND_DESCENDANT_MESHES.

    Returns: list of (obj, name) tuples, deterministically ordered.
    """
    # Compute root_mesh
    root_mesh = []
    if geometry_scope_value in ("SELF_MESH", "SELF_AND_DESCENDANT_MESHES"):
        if root_type_value == "MESH" and id(root_obj) in scene_member_ids:
            root_name = scene_name_by_id[id(root_obj)]
            root_mesh = [(root_obj, root_name)]

    if geometry_scope_value == "SELF_MESH":
        root_mesh.sort(key=lambda item: (
            item[1].casefold(), item[1], scene_materialization_index[id(item[0])]))
        return root_mesh

    # DESCENDANT_MESHES or SELF_AND_DESCENDANT_MESHES
    visited_ids = {id(root_obj)}
    collected = []

    # READ_ROOT_CHILDREN
    try:
        root_children = list(root_obj.children)
    except Exception:
        raise RuntimeError("READ_ROOT_CHILDREN")

    stack = list(root_children)

    while stack:
        child = stack.pop()
        cid = id(child)
        if cid in visited_ids:
            continue
        visited_ids.add(cid)

        if cid in scene_member_ids:
            cname = scene_name_by_id[cid]
            collected.append((child, cname))

        # READ_DESCENDANT_CHILDREN
        try:
            child_children = list(child.children)
        except Exception:
            raise RuntimeError("READ_DESCENDANT_CHILDREN")
        stack.extend(child_children)

    descendant_meshes = []
    type_cache = {}
    for dobj, dname in collected:
        cid = id(dobj)
        if cid not in type_cache:
            # READ_DESCENDANT_TYPE
            try:
                type_cache[cid] = dobj.type
            except Exception:
                raise RuntimeError("READ_DESCENDANT_TYPE")
        if type_cache[cid] == "MESH":
            descendant_meshes.append((dobj, dname))

    if geometry_scope_value == "SELF_AND_DESCENDANT_MESHES":
        if root_mesh:
            root_id = id(root_mesh[0][0])
            desc_ids = {id(o) for o, _ in descendant_meshes}
            if root_id in desc_ids:
                root_mesh = []
        result = root_mesh + descendant_meshes
    else:
        result = descendant_meshes

    result.sort(key=lambda item: (
        item[1].casefold(), item[1], scene_materialization_index[id(item[0])]))
    return result


def _check_material_assignment(scene, target, per_target_result):
    """Check material assignment presence for a single target — full I2 ERROR support.

    I2 adds: 7 ERROR operations, local/global short-circuit, formal ERROR result dicts.

    Args:
        scene: bpy.types.Scene (may be None).
        target: target dict from spec.
        per_target_result: result dict from _check_root_objects for this target.

    Returns: checks.material_assignment_presence_check result dict.
    """
    # --- Step 1: configuration ---
    ma_block = target.get("material_assignment")
    if ma_block is None or not isinstance(ma_block, dict):
        return {"result": "NOT_CHECKED", "note": "MATERIAL_ASSIGNMENT_NOT_CONFIGURED"}

    require = ma_block.get("require_material_assignment_presence")
    if require is not True:
        return {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"}

    # --- Step 2: root preconditions ---
    checks = per_target_result.get("checks", {})
    obj_exists = checks.get("object_exists", {})
    obj_type = checks.get("object_type", {})

    if obj_exists.get("result") == "FAIL":
        return {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_NOT_FOUND"}

    if obj_exists.get("error_type") == "AMBIGUOUS_ROOT_OBJECT_NAME":
        return {"result": "NOT_CHECKED", "note": "AMBIGUOUS_ROOT_OBJECT_NAME"}

    if obj_type.get("result") == "FAIL":
        return {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_TYPE_MISMATCH"}

    obj_exists_ok = (
        obj_exists.get("result") == "PASS"
        and obj_type.get("result") == "PASS"
    )
    if not obj_exists_ok:
        return {"result": "NOT_CHECKED", "note": "ROOT_LOOKUP_ERROR"}

    # --- Step 3: READ_SCENE_OBJECTS ---
    geometry_scope_value = target["geometry_scope"]
    root_obj_name = target["root_object_name"]

    try:
        scene_objects_ordered = list(scene.objects)
    except Exception:
        return {
            "result": "ERROR",
            "error_type": "MATERIAL_ASSIGNMENT_COMPUTATION_ERROR",
            "operation": "READ_SCENE_OBJECTS",
            "note": "READ_SCENE_OBJECTS_FAILED",
        }

    scene_member_ids = {id(obj) for obj in scene_objects_ordered}
    scene_materialization_index = {
        id(obj): idx for idx, obj in enumerate(scene_objects_ordered)
    }

    # --- Step 4: RESOLVE_ROOT_OBJECT ---
    scene_name_by_id = {}
    root_matches = []
    try:
        for obj in scene_objects_ordered:
            oname = obj.name
            scene_name_by_id[id(obj)] = oname
            if oname == root_obj_name:
                root_matches.append(obj)
    except Exception:
        return {
            "result": "ERROR",
            "error_type": "MATERIAL_ASSIGNMENT_COMPUTATION_ERROR",
            "operation": "RESOLVE_ROOT_OBJECT",
            "note": "RESOLVE_ROOT_OBJECT_FAILED",
        }

    if len(root_matches) != 1:
        return {
            "result": "ERROR",
            "error_type": "MATERIAL_ASSIGNMENT_COMPUTATION_ERROR",
            "operation": "RESOLVE_ROOT_OBJECT",
            "note": "RESOLVE_ROOT_OBJECT_FAILED",
        }

    root_obj = root_matches[0]
    root_type_value = obj_type.get("actual")

    # --- Step 5: geometry scope (READ_ROOT_CHILDREN, READ_DESCENDANT_CHILDREN, READ_DESCENDANT_TYPE) ---
    try:
        mesh_objects = _collect_geometry_scope_objects(
            scene_objects_ordered=scene_objects_ordered,
            scene_member_ids=scene_member_ids,
            scene_materialization_index=scene_materialization_index,
            scene_name_by_id=scene_name_by_id,
            root_obj=root_obj,
            root_type_value=root_type_value,
            geometry_scope_value=geometry_scope_value,
        )
    except RuntimeError as e:
        op = str(e)
        return {
            "result": "ERROR",
            "error_type": "MATERIAL_ASSIGNMENT_COMPUTATION_ERROR",
            "operation": op,
            "note": op + "_FAILED",
        }

    # --- Step 6: check each MESH (READ_MATERIAL_SLOTS, READ_SLOT_MATERIAL) ---
    per_mesh_results = []
    for mesh_obj, mesh_name in mesh_objects:
        pm = _check_material_slots_for_mesh(mesh_obj, mesh_name)
        per_mesh_results.append(pm)

    # --- Step 7: aggregate ---
    if not per_mesh_results:
        return {"result": "NOT_CHECKED", "note": "NO_MESH_IN_GEOMETRY_SCOPE"}

    has_error = any(pm["result"] == "ERROR" for pm in per_mesh_results)
    has_fail = any(pm["result"] == "FAIL" for pm in per_mesh_results)

    if has_error:
        return {"result": "ERROR", "per_mesh": per_mesh_results}
    if has_fail:
        return {
            "result": "FAIL",
            "failure_code": "MATERIAL_ASSIGNMENT_FAILURE",
            "per_mesh": per_mesh_results,
        }
    return {"result": "PASS", "per_mesh": per_mesh_results}


# ════════════════ Collection Rules ════════════════


class _CollectionRulesError(Exception):
    """Internal exception for Collection Rules ERROR propagation.

    Carries operation and optional collection_name for building
    precise COLLECTION_RULES_COMPUTATION_ERROR result dicts.
    """
    def __init__(self, operation, collection_name=None):
        self.operation = operation
        self.collection_name = collection_name


def _cr_global_error(operation):
    """Build a global Collection Rules ERROR result dict."""
    return {
        "result": "ERROR",
        "error_type": "COLLECTION_RULES_COMPUTATION_ERROR",
        "operation": operation,
        "note": operation + "_FAILED",
        "required": {
            "result": "NOT_CHECKED",
            "note": "GLOBAL_ERROR_SHORT_CIRCUIT",
        },
        "forbidden": {
            "result": "NOT_CHECKED",
            "note": "GLOBAL_ERROR_SHORT_CIRCUIT",
        },
    }


def _cr_per_target_error(operation, collection_name=None):
    """Build a per-target Collection Rules ERROR result dict."""
    err = {
        "result": "ERROR",
        "error_type": "COLLECTION_RULES_COMPUTATION_ERROR",
        "operation": operation,
        "note": operation + "_FAILED",
    }
    if collection_name is not None:
        err["collection_name"] = collection_name
    return err


def _check_collection_rules_global(collection_rules_block):
    """Check global Collection Rules: required existence + forbidden glob.

    Args:
        collection_rules_block: spec.collection_rules dict or None.

    Returns:
        None if global layer is completely disabled.
        Otherwise full collection_rules result dict for global_results.
    """
    try:
        # --- Step G1: block missing or None ---
        if collection_rules_block is None or not isinstance(collection_rules_block, dict):
            return None

        # --- Step G2: determine sub-field enablement ---
        required_enabled = False
        forbidden_enabled = False

        rc = collection_rules_block.get("required_collection_names")
        if rc is not None and isinstance(rc, list) and len(rc) > 0:
            required_enabled = True

        fc = collection_rules_block.get("forbidden_collection_name_patterns")
        if fc is not None and isinstance(fc, list) and len(fc) > 0:
            forbidden_enabled = True

        # --- Step G3/G4: materialize bpy.data.collections only if needed ---
        all_collections = None
        name_by_id = None
        collection_names = set()
        if required_enabled or forbidden_enabled:
            # G1: MATERIALIZE_BPY_DATA_COLLECTIONS
            try:
                all_collections = list(bpy.data.collections)
            except _CollectionRulesError:
                raise
            except Exception:
                raise _CollectionRulesError("MATERIALIZE_BPY_DATA_COLLECTIONS")
            # G2: READ_COLLECTION_NAME for each collection
            name_by_id = {}
            try:
                for col in all_collections:
                    cname = col.name
                    name_by_id[id(col)] = cname
                    collection_names.add(cname)
            except _CollectionRulesError:
                raise
            except Exception:
                raise _CollectionRulesError("READ_COLLECTION_NAME")

        # --- Required sub-check ---
        if required_enabled:
            try:
                required_list = sorted(set(rc), key=lambda n: (n.casefold(), n))
                missing = [n for n in required_list if n not in collection_names]
                missing.sort(key=lambda n: (n.casefold(), n))
            except _CollectionRulesError:
                raise
            except Exception:
                raise _CollectionRulesError("RESOLVE_REQUIRED_COLLECTION")
            if missing:
                required_result = {
                    "result": "FAIL",
                    "failure_code": "REQUIRED_COLLECTION_MISSING",
                    "required_names": required_list,
                    "missing_names": missing,
                }
            else:
                required_result = {
                    "result": "PASS",
                    "required_names": required_list,
                    "missing_names": [],
                }
        else:
            required_result = {
                "result": "NOT_CHECKED",
                "note": "REQUIRED_COLLECTION_NAMES_NOT_CONFIGURED",
            }

        # --- Forbidden sub-check ---
        if forbidden_enabled:
            from protocol_guard.phase3_min.asset_scene_preflight_core import casefold_glob_match

            try:
                forbidden_list = sorted(set(fc), key=lambda n: (n.casefold(), n))
                matched = []
                for col_name in sorted(collection_names, key=lambda n: (n.casefold(), n)):
                    for pat in forbidden_list:
                        matched_flag = casefold_glob_match(col_name, pat)
                        if matched_flag:
                            matched.append(col_name)
                            break
                matched_dedup = sorted(set(matched), key=lambda n: (n.casefold(), n))
            except _CollectionRulesError:
                raise
            except Exception:
                raise _CollectionRulesError("MATCH_FORBIDDEN_PATTERN")
            if matched_dedup:
                forbidden_result = {
                    "result": "FAIL",
                    "failure_code": "FORBIDDEN_COLLECTION_MATCHED",
                    "forbidden_patterns": forbidden_list,
                    "matched_collections": matched_dedup,
                }
            else:
                forbidden_result = {
                    "result": "PASS",
                    "forbidden_patterns": forbidden_list,
                    "matched_collections": [],
                }
        else:
            forbidden_result = {
                "result": "NOT_CHECKED",
                "note": "FORBIDDEN_COLLECTION_NAME_PATTERNS_NOT_CONFIGURED",
            }

        # --- Aggregate ---
        sub_results = [required_result["result"], forbidden_result["result"]]
        if "FAIL" in sub_results:
            top = {"result": "FAIL", "failure_code": "COLLECTION_RULES_FAILURE",
                   "required": required_result, "forbidden": forbidden_result}
        elif "PASS" in sub_results:
            top = {"result": "PASS", "required": required_result, "forbidden": forbidden_result}
        else:
            top = {"result": "NOT_CHECKED", "required": required_result, "forbidden": forbidden_result}
        return top
    except _CollectionRulesError as e:
        return _cr_global_error(e.operation)


def _materialize_bpy_data_collections():
    """Materialize all collections from bpy.data.collections.

    Returns:
        (all_collections, name_by_id): all_collections is list[bpy.types.Collection],
        name_by_id is dict[id] -> name.

    Raises:
        _CollectionRulesError on failure (called from per-target context).
    """
    try:
        all_collections = list(bpy.data.collections)
    except _CollectionRulesError:
        raise
    except Exception:
        raise _CollectionRulesError("MATERIALIZE_BPY_DATA_COLLECTIONS")
    name_by_id = {}
    for col in all_collections:
        try:
            name_by_id[id(col)] = col.name
        except _CollectionRulesError:
            raise
        except Exception:
            raise _CollectionRulesError(
                "READ_COLLECTION_NAME_PER_TARGET",
                collection_name="<UNREADABLE_COLLECTION>",
            )
    return all_collections, name_by_id


def _materialize_collection_ancestor_index(all_collections, name_by_id):
    """Build child->parent reverse index from collection children.

    Args:
        all_collections: list of bpy.types.Collection.
        name_by_id: dict[id] -> name, pre-built.

    Returns:
        (parent_of, collection_by_id):
          parent_of: dict[id(child)] -> list[id(parent)]
          collection_by_id: dict[id] -> collection

    Raises:
        _CollectionRulesError on failure.
    """
    parent_of = {}
    collection_by_id = {}
    visited_pairs = set()
    for col in all_collections:
        cid = id(col)
        collection_by_id[cid] = col
        try:
            children = list(col.children)
        except _CollectionRulesError:
            raise
        except Exception:
            cname = name_by_id.get(cid, "<UNREADABLE_COLLECTION>")
            raise _CollectionRulesError(
                "READ_COLLECTION_CHILDREN_PER_TARGET",
                collection_name=cname,
            )
        for child in children:
            pair = (cid, id(child))
            if pair in visited_pairs:
                continue
            visited_pairs.add(pair)
            ch_id = id(child)
            if ch_id not in parent_of:
                parent_of[ch_id] = []
            parent_of[ch_id].append(cid)
            if ch_id not in collection_by_id:
                collection_by_id[ch_id] = child
    return parent_of, collection_by_id


def _compute_ancestor_closure(direct_collections, parent_of, collection_by_id, name_by_id):
    """Compute ancestor collection names from direct collections.

    Args:
        direct_collections: list of bpy.types.Collection (direct members).
        parent_of: dict[id(child)] -> list[id(parent)].
        collection_by_id: dict[id] -> bpy.types.Collection.
        name_by_id: dict[id] -> name.

    Returns:
        (direct_names, ancestor_names): both sorted lists of unique names.
    """
    direct_names = []
    direct_ids = set()
    for dc in direct_collections:
        did = id(dc)
        if did in direct_ids:
            continue
        direct_ids.add(did)
        direct_name = name_by_id[did]
        direct_names.append(direct_name)
    direct_names.sort(key=lambda n: (n.casefold(), n))

    visited_ids = set(direct_ids)
    stack = list(direct_collections)
    ancestor_names_raw = []

    while stack:
        col = stack.pop()
        cid = id(col)
        pids = parent_of.get(cid, [])
        for pid in pids:
            if pid in visited_ids:
                continue
            visited_ids.add(pid)
            parent_col = collection_by_id.get(pid)
            if parent_col is not None:
                pname = name_by_id[pid]
                ancestor_names_raw.append(pname)
                stack.append(parent_col)

    ancestor_names = sorted(set(ancestor_names_raw), key=lambda n: (n.casefold(), n))
    return direct_names, ancestor_names


def _resolve_root_for_collection_rules(scene, target, per_target_result):
    """Resolve the unique root object for Collection Rules per-target check.

    Args:
        scene: bpy.types.Scene.
        target: target dict from spec.
        per_target_result: result dict from _check_root_objects.

    Returns:
        (root_obj, error_or_none): root_obj is the unique matched object
        and error_or_none is an ERROR dict on failure, or (None, None)
        when no unique match exists without I/O error.

    Raises:
        _CollectionRulesError on bpy read failure (P4).
    """
    root_name = target["root_object_name"]

    # P4: RESOLVE_ROOT_OBJECT_FOR_COLLECTION
    try:
        scene_objs = list(scene.objects)
    except _CollectionRulesError:
        raise
    except Exception:
        raise _CollectionRulesError("RESOLVE_ROOT_OBJECT_FOR_COLLECTION")

    matches = []
    try:
        for obj in scene_objs:
            if obj.name == root_name:
                matches.append(obj)
    except _CollectionRulesError:
        raise
    except Exception:
        raise _CollectionRulesError("RESOLVE_ROOT_OBJECT_FOR_COLLECTION")

    if len(matches) != 1:
        return None, None

    root_obj = matches[0]
    return root_obj, None


def _check_collection_membership(scene, target, per_target_result):
    """Check per-target Collection membership for a single target.

    Args:
        scene: bpy.types.Scene.
        target: target dict from spec.
        per_target_result: result dict from _check_root_objects.

    Returns:
        checks.collection_membership result dict.
    """
    # --- Step P1-P3: config ---
    rc = target.get("required_collection_names")
    if rc is None or not isinstance(rc, list) or len(rc) == 0:
        return {"result": "NOT_CHECKED", "note": "REQUIRED_COLLECTION_NAMES_NOT_CONFIGURED"}

    # --- Step P4: root preconditions ---
    checks = per_target_result.get("checks", {})
    obj_exists = checks.get("object_exists", {})
    obj_type = checks.get("object_type", {})

    if obj_exists.get("result") == "FAIL":
        return {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_NOT_FOUND"}
    if obj_exists.get("error_type") == "AMBIGUOUS_ROOT_OBJECT_NAME":
        return {"result": "NOT_CHECKED", "note": "AMBIGUOUS_ROOT_OBJECT_NAME"}
    if obj_type.get("result") == "FAIL":
        return {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_TYPE_MISMATCH"}

    obj_exists_ok = (
        obj_exists.get("result") == "PASS"
        and obj_type.get("result") == "PASS"
    )
    if not obj_exists_ok:
        return {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_TYPE_MISMATCH"}

    # --- Resolve root (P4) ---
    try:
        root_obj, _ = _resolve_root_for_collection_rules(scene, target, per_target_result)
    except _CollectionRulesError as e:
        return _cr_per_target_error(e.operation, e.collection_name)
    if root_obj is None:
        return {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_NOT_FOUND"}

    # --- Read direct collections (P1: READ_ROOT_USERS_COLLECTION) ---
    try:
        direct_colls = list(root_obj.users_collection)
    except _CollectionRulesError:
        raise
    except Exception:
        return _cr_per_target_error("READ_ROOT_USERS_COLLECTION")

    # --- Materialize ancestor index ---
    try:
        all_collections, name_by_id = _materialize_bpy_data_collections()
    except _CollectionRulesError as e:
        return _cr_per_target_error(e.operation, e.collection_name)

    try:
        parent_of, collection_by_id = _materialize_collection_ancestor_index(
            all_collections, name_by_id)
    except _CollectionRulesError as e:
        return _cr_per_target_error(e.operation, e.collection_name)

    # --- Compute closure ---
    direct_names, ancestor_names = _compute_ancestor_closure(
        direct_colls, parent_of, collection_by_id, name_by_id)

    # --- Match ---
    required_set = set(rc)
    all_collection_names = set(direct_names) | set(ancestor_names)
    matched = sorted(
        [n for n in required_set if n in all_collection_names],
        key=lambda n: (n.casefold(), n),
    )
    missing = sorted(
        [n for n in required_set if n not in all_collection_names],
        key=lambda n: (n.casefold(), n),
    )
    required_names = sorted(required_set, key=lambda n: (n.casefold(), n))

    if matched:
        return {
            "result": "PASS",
            "required_names": required_names,
            "direct_collections": direct_names,
            "ancestor_collections": ancestor_names,
            "matched_names": matched,
            "missing_names": missing,
        }
    else:
        return {
            "result": "FAIL",
            "failure_code": "TARGET_NOT_IN_REQUIRED_COLLECTION",
            "required_names": required_names,
            "direct_collections": direct_names,
            "ancestor_collections": ancestor_names,
            "matched_names": [],
            "missing_names": missing,
        }


def _check_ground_contact(scene, target, per_target_result):
    """Check ground contact: evaluated geometry lowest world-space Z vs ground_z.

    Reads existing checks.object_exists and checks.object_type for root
    preconditions. Does NOT modify _check_root_objects.

    Args:
        scene: bpy.types.Scene (may be None).
        target: target dict from spec.
        per_target_result: result dict from _check_root_objects for this target.

    Returns: checks.ground_contact result dict.
    """
    import math

    # ── Step 1: config ──
    gc_block = target.get("ground_contact")
    if gc_block is None or not isinstance(gc_block, dict):
        return {"result": "NOT_CHECKED", "note": "GROUND_CONTACT_NOT_CONFIGURED"}

    ground_z = gc_block.get("ground_z")
    tolerance = gc_block.get("ground_contact_tolerance")
    if ground_z is None and tolerance is None:
        return {"result": "NOT_CHECKED", "note": "GROUND_CONTACT_NOT_CONFIGURED"}
    # Pre-open ensures both are non-None at this point

    # ── Step 2: root preconditions (read existing checks only) ──
    checks = per_target_result.get("checks", {})
    obj_exists = checks.get("object_exists", {})
    obj_type = checks.get("object_type", {})

    if obj_exists.get("result") == "FAIL":
        return {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_NOT_FOUND"}
    if obj_exists.get("error_type") == "AMBIGUOUS_ROOT_OBJECT_NAME":
        return {"result": "NOT_CHECKED", "note": "AMBIGUOUS_ROOT_OBJECT_NAME"}
    if obj_exists.get("result") == "ERROR":
        return {"result": "NOT_CHECKED", "note": "ROOT_LOOKUP_ERROR"}
    if obj_type.get("result") == "FAIL":
        return {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_TYPE_MISMATCH"}

    # ── Step 3: materialize scene.objects once ──
    try:
        scene_objects_ordered = list(scene.objects)
    except Exception:
        return {
            "result": "ERROR",
            "error_type": "GROUND_CONTACT_COMPUTATION_ERROR",
            "operation": "READ_SCENE_OBJECTS",
            "note": "READ_SCENE_OBJECTS_FAILED",
        }

    scene_member_ids = {id(obj) for obj in scene_objects_ordered}
    scene_materialization_index = {
        id(obj): idx for idx, obj in enumerate(scene_objects_ordered)
    }

    # ── Step 4: build name_by_id and resolve root ──
    root_obj_name = target["root_object_name"]
    scene_name_by_id = {}
    root_matches = []
    try:
        for obj in scene_objects_ordered:
            oname = obj.name
            scene_name_by_id[id(obj)] = oname
            if oname == root_obj_name:
                root_matches.append(obj)
    except Exception:
        return {
            "result": "ERROR",
            "error_type": "GROUND_CONTACT_COMPUTATION_ERROR",
            "operation": "RESOLVE_ROOT_OBJECT",
            "note": "RESOLVE_ROOT_OBJECT_FAILED",
        }

    if len(root_matches) != 1:
        return {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_NOT_FOUND"}

    root_obj = root_matches[0]
    root_type_value = obj_type.get("actual")

    # ── Step 5: collect geometry scope objects ──
    geometry_scope_value = target["geometry_scope"]
    try:
        mesh_objects = _collect_geometry_scope_objects(
            scene_objects_ordered=scene_objects_ordered,
            scene_member_ids=scene_member_ids,
            scene_materialization_index=scene_materialization_index,
            scene_name_by_id=scene_name_by_id,
            root_obj=root_obj,
            root_type_value=root_type_value,
            geometry_scope_value=geometry_scope_value,
        )
    except RuntimeError as e:
        op = str(e)
        return {
            "result": "ERROR",
            "error_type": "GROUND_CONTACT_COMPUTATION_ERROR",
            "operation": op,
            "note": op + "_FAILED",
        }

    # ── Step 6: empty geometry → FAIL ──
    if len(mesh_objects) == 0:
        return {
            "result": "FAIL",
            "failure_code": "NO_EVALUATED_GEOMETRY",
            "ground_z": ground_z,
            "ground_contact_tolerance": tolerance,
        }

    # ── Step 7: get depsgraph once ──
    try:
        depsgraph = bpy.context.evaluated_depsgraph_get()
    except Exception:
        return {
            "result": "ERROR",
            "error_type": "GROUND_CONTACT_COMPUTATION_ERROR",
            "operation": "GET_EVALUATED_DEPSGRAPH",
            "note": "GET_EVALUATED_DEPSGRAPH_FAILED",
        }

    # ── Step 8: iterate MESH objects ──
    actual_lowest_z = float('inf')
    non_finite_found = False
    zero_vertex_found = False
    evaluated_mesh_names = []

    for mesh_obj, mesh_name in mesh_objects:
        evaluated_mesh_names.append(mesh_name)

        # 8a: evaluated_get
        try:
            evaluated = mesh_obj.evaluated_get(depsgraph)
        except Exception:
            return {
                "result": "ERROR",
                "error_type": "GROUND_CONTACT_COMPUTATION_ERROR",
                "operation": "EVALUATED_GET",
                "note": "EVALUATED_GET_FAILED",
            }

        # 8b: to_mesh
        try:
            mesh = evaluated.to_mesh()
        except Exception:
            return {
                "result": "ERROR",
                "error_type": "GROUND_CONTACT_COMPUTATION_ERROR",
                "operation": "TO_MESH",
                "note": "TO_MESH_FAILED",
            }

        try:
            # 8c: read matrix_world
            try:
                mw = evaluated.matrix_world
            except Exception:
                return {
                    "result": "ERROR",
                    "error_type": "GROUND_CONTACT_COMPUTATION_ERROR",
                    "operation": "READ_EVALUATED_MATRIX_WORLD",
                    "note": "READ_EVALUATED_MATRIX_WORLD_FAILED",
                }

            # 8d: check zero vertices
            try:
                vertex_count = len(mesh.vertices)
            except Exception:
                return {
                    "result": "ERROR",
                    "error_type": "GROUND_CONTACT_COMPUTATION_ERROR",
                    "operation": "READ_MESH_VERTICES",
                    "note": "READ_MESH_VERTICES_FAILED",
                }

            if vertex_count == 0:
                zero_vertex_found = True
                continue

            # 8e: iterate vertices — read co, transform, aggregate
            try:
                for v in mesh.vertices:
                    try:
                        vertex_co = v.co
                    except Exception:
                        return {
                            "result": "ERROR",
                            "error_type": "GROUND_CONTACT_COMPUTATION_ERROR",
                            "operation": "READ_MESH_VERTICES",
                            "note": "READ_MESH_VERTICES_FAILED",
                        }

                    try:
                        world_co = mw @ vertex_co
                        world_z = world_co.z
                    except Exception:
                        return {
                            "result": "ERROR",
                            "error_type": "GROUND_CONTACT_COMPUTATION_ERROR",
                            "operation": "TRANSFORM_VERTEX_TO_WORLD_SPACE",
                            "note": "TRANSFORM_VERTEX_TO_WORLD_SPACE_FAILED",
                        }

                    if not math.isfinite(world_z):
                        non_finite_found = True
                        continue

                    if world_z < actual_lowest_z:
                        actual_lowest_z = world_z
            except Exception:
                return {
                    "result": "ERROR",
                    "error_type": "GROUND_CONTACT_COMPUTATION_ERROR",
                    "operation": "READ_MESH_VERTICES",
                    "note": "READ_MESH_VERTICES_FAILED",
                }
        finally:
            # 8f: to_mesh_clear in finally — overrides pending result
            try:
                evaluated.to_mesh_clear()
            except Exception:
                return {
                    "result": "ERROR",
                    "error_type": "GROUND_CONTACT_COMPUTATION_ERROR",
                    "operation": "TO_MESH_CLEAR",
                    "note": "TO_MESH_CLEAR_FAILED",
                }

    # ── Step 9: aggregate ──
    if zero_vertex_found:
        return {
            "result": "FAIL",
            "failure_code": "NO_EVALUATED_GEOMETRY",
            "ground_z": ground_z,
            "ground_contact_tolerance": tolerance,
        }

    if non_finite_found:
        return {
            "result": "FAIL",
            "failure_code": "NON_FINITE_EVALUATED_VERTEX_Z",
            "ground_z": ground_z,
            "ground_contact_tolerance": tolerance,
            "evaluated_mesh_names": evaluated_mesh_names,
        }

    if not math.isfinite(actual_lowest_z):
        return {
            "result": "FAIL",
            "failure_code": "NO_EVALUATED_GEOMETRY",
            "ground_z": ground_z,
            "ground_contact_tolerance": tolerance,
        }

    # ── Step 10: tolerance comparison ──
    absolute_error = abs(actual_lowest_z - ground_z)
    if absolute_error <= tolerance:
        return {
            "result": "PASS",
            "ground_z": ground_z,
            "ground_contact_tolerance": tolerance,
            "actual_lowest_z": actual_lowest_z,
            "absolute_error": absolute_error,
            "evaluated_mesh_names": evaluated_mesh_names,
        }
    else:
        return {
            "result": "FAIL",
            "failure_code": "GROUND_CONTACT_OUT_OF_TOLERANCE",
            "ground_z": ground_z,
            "ground_contact_tolerance": tolerance,
            "actual_lowest_z": actual_lowest_z,
            "absolute_error": absolute_error,
            "evaluated_mesh_names": evaluated_mesh_names,
        }


def _check_camera_check(scene, target, per_target_result, _target_cache=None):
    """Check camera projection for a single target.

    Args:
        scene: bpy.types.Scene (may be None).
        target: target dict from spec.
        per_target_result: result dict from _check_root_objects for this target.
        _target_cache: per-target runtime cache dict from _check_root_objects,
            containing scene_objects_ordered, scene_name_by_id, root_obj,
            scene_member_ids, scene_materialization_index.
            If provided, used directly. If None, materialized internally.

    Returns:
        checks.camera_check result dict, or None if camera_check not configured.
    """
    import math

    # ── Step 1: config ──
    cc_block = target.get("camera_check")
    if cc_block is None or not isinstance(cc_block, dict):
        return None

    camera_object_name = cc_block["camera_object_name"]
    mvc = cc_block["minimum_visible_projected_corner_count"]
    rsb = cc_block["required_screen_bbox"]

    # ── Step 2: check for name_read_error in cache (before root preconditions) ──
    if _target_cache is not None and _target_cache.get("name_read_error"):
        return {
            "result": "ERROR",
            "error_type": "CAMERA_CHECK_COMPUTATION_ERROR",
            "operation": _target_cache.get("error_operation", "RESOLVE_CAMERA_OBJECT"),
            "note": "RESOLVE_CAMERA_OBJECT_FAILED",
        }

    # ── Step 3: root preconditions (read existing checks only) ──
    checks = per_target_result.get("checks", {})
    obj_exists = checks.get("object_exists", {})
    obj_type = checks.get("object_type", {})

    if obj_exists.get("result") == "FAIL":
        return {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_NOT_FOUND"}
    if obj_exists.get("error_type") == "AMBIGUOUS_ROOT_OBJECT_NAME":
        return {"result": "NOT_CHECKED", "note": "AMBIGUOUS_ROOT_OBJECT_NAME"}
    if obj_exists.get("result") == "ERROR":
        return {"result": "NOT_CHECKED", "note": "ROOT_LOOKUP_ERROR"}
    if obj_type.get("result") == "FAIL":
        return {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_TYPE_MISMATCH"}

    # ── Step 4: use per-target cache or materialize once ──
    if _target_cache is not None:
        scene_objects_ordered = _target_cache["scene_objects_ordered"]
        scene_name_by_id = _target_cache["scene_name_by_id"]
        root_obj = _target_cache["root_obj"]
        scene_member_ids = _target_cache["scene_member_ids"]
        scene_materialization_index = _target_cache["scene_materialization_index"]
        root_type_value = obj_type.get("actual")
        # Camera lookup from cached names (no re-read of obj.name)
        camera_match_count = 0
        camera_obj = None
        try:
            for oid, oname in scene_name_by_id.items():
                if oname == camera_object_name:
                    camera_match_count += 1
                    if camera_match_count == 1:
                        for obj in scene_objects_ordered:
                            if id(obj) == oid:
                                camera_obj = obj
                                break
                    else:
                        camera_obj = None
        except Exception:
            return {
                "result": "ERROR",
                "error_type": "CAMERA_CHECK_COMPUTATION_ERROR",
                "operation": "RESOLVE_CAMERA_OBJECT",
                "note": "RESOLVE_CAMERA_OBJECT_FAILED",
            }
    else:
        try:
            scene_objects_ordered = list(scene.objects)
        except Exception:
            return {
                "result": "ERROR",
                "error_type": "CAMERA_CHECK_COMPUTATION_ERROR",
                "operation": "READ_SCENE_OBJECTS",
                "note": "READ_SCENE_OBJECTS_FAILED",
            }
        scene_member_ids = {id(obj) for obj in scene_objects_ordered}
        scene_materialization_index = {
            id(obj): idx for idx, obj in enumerate(scene_objects_ordered)
        }
        # Single-pass name iteration
        root_obj_name = target["root_object_name"]
        scene_name_by_id = {}
        root_matches = []
        camera_match_count = 0
        camera_obj = None
        try:
            for obj in scene_objects_ordered:
                oname = obj.name
                scene_name_by_id[id(obj)] = oname
                if oname == root_obj_name:
                    root_matches.append(obj)
                if oname == camera_object_name:
                    camera_match_count += 1
                    if camera_match_count == 1:
                        camera_obj = obj
                    else:
                        camera_obj = None
        except Exception:
            return {
                "result": "ERROR",
                "error_type": "CAMERA_CHECK_COMPUTATION_ERROR",
                "operation": "RESOLVE_ROOT_OBJECT",
                "note": "RESOLVE_ROOT_OBJECT_FAILED",
            }
        if len(root_matches) != 1:
            return {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_NOT_FOUND"}
        root_obj = root_matches[0]
        root_type_value = obj_type.get("actual")

    # ── Step 4: camera lookup result ──
    if camera_match_count == 0:
        return {
            "result": "FAIL",
            "failure_code": "CAMERA_OBJECT_NOT_FOUND",
            "camera_object_name": camera_object_name,
        }
    if camera_match_count > 1:
        return {
            "result": "FAIL",
            "failure_code": "CAMERA_OBJECT_NOT_FOUND",
            "camera_object_name": camera_object_name,
        }

    try:
        camera_type = camera_obj.type
    except Exception:
        return {
            "result": "ERROR",
            "error_type": "CAMERA_CHECK_COMPUTATION_ERROR",
            "operation": "RESOLVE_CAMERA_OBJECT",
            "note": "RESOLVE_CAMERA_OBJECT_FAILED",
        }

    if camera_type != "CAMERA":
        return {
            "result": "FAIL",
            "failure_code": "CAMERA_TYPE_MISMATCH",
            "camera_object_name": camera_object_name,
            "actual_type": camera_type,
        }

    # ── Step 6: collect geometry scope objects ──
    geometry_scope_value = target["geometry_scope"]
    try:
        mesh_objects = _collect_geometry_scope_objects(
            scene_objects_ordered=scene_objects_ordered,
            scene_member_ids=scene_member_ids,
            scene_materialization_index=scene_materialization_index,
            scene_name_by_id=scene_name_by_id,
            root_obj=root_obj,
            root_type_value=root_type_value,
            geometry_scope_value=geometry_scope_value,
        )
    except RuntimeError as e:
        op = str(e)
        return {
            "result": "ERROR",
            "error_type": "CAMERA_CHECK_COMPUTATION_ERROR",
            "operation": op,
            "note": op + "_FAILED",
        }

    # ── Step 7: empty geometry scope ──
    if len(mesh_objects) == 0:
        return {
            "result": "FAIL",
            "failure_code": "NO_EVALUATED_GEOMETRY",
            "evaluated_mesh_names": [],
        }

    # ── Step 8: get depsgraph once ──
    try:
        depsgraph = bpy.context.evaluated_depsgraph_get()
    except Exception:
        return {
            "result": "ERROR",
            "error_type": "CAMERA_CHECK_COMPUTATION_ERROR",
            "operation": "GET_EVALUATED_DEPSGRAPH",
            "note": "GET_EVALUATED_DEPSGRAPH_FAILED",
        }

    # ── Step 9: iterate MESH objects ──
    pending_zero_vertex = False
    pending_non_finite = False
    evaluated_mesh_names = []
    all_world_vertices = []

    for mesh_obj, mesh_name in mesh_objects:
        # 9a: evaluated_get
        try:
            evaluated = mesh_obj.evaluated_get(depsgraph)
        except Exception:
            return {
                "result": "ERROR",
                "error_type": "CAMERA_CHECK_COMPUTATION_ERROR",
                "operation": "EVALUATED_GET",
                "note": "EVALUATED_GET_FAILED",
            }

        # 9b: to_mesh
        try:
            mesh = evaluated.to_mesh()
        except Exception:
            return {
                "result": "ERROR",
                "error_type": "CAMERA_CHECK_COMPUTATION_ERROR",
                "operation": "TO_MESH",
                "note": "TO_MESH_FAILED",
            }

        evaluated_mesh_names.append(mesh_name)

        try:
            # 9c: read matrix_world
            try:
                mw = evaluated.matrix_world
            except Exception:
                return {
                    "result": "ERROR",
                    "error_type": "CAMERA_CHECK_COMPUTATION_ERROR",
                    "operation": "READ_EVALUATED_MATRIX_WORLD",
                    "note": "READ_EVALUATED_MATRIX_WORLD_FAILED",
                }

            # 9d: check zero vertices (§4.3)
            try:
                vertex_count = len(mesh.vertices)
            except Exception:
                return {
                    "result": "ERROR",
                    "error_type": "CAMERA_CHECK_COMPUTATION_ERROR",
                    "operation": "READ_MESH_VERTICES",
                    "note": "READ_MESH_VERTICES_FAILED",
                }

            if vertex_count == 0:
                pending_zero_vertex = True
                continue

            # 9e: iterate vertices
            try:
                for v in mesh.vertices:
                    try:
                        vertex_co = v.co
                    except Exception:
                        return {
                            "result": "ERROR",
                            "error_type": "CAMERA_CHECK_COMPUTATION_ERROR",
                            "operation": "READ_MESH_VERTICES",
                            "note": "READ_MESH_VERTICES_FAILED",
                        }

                    try:
                        world_co = mw @ vertex_co
                    except Exception:
                        return {
                            "result": "ERROR",
                            "error_type": "CAMERA_CHECK_COMPUTATION_ERROR",
                            "operation": "TRANSFORM_VERTEX_TO_WORLD_SPACE",
                            "note": "TRANSFORM_VERTEX_TO_WORLD_SPACE_FAILED",
                        }

                    if not (math.isfinite(world_co.x) and math.isfinite(world_co.y)
                            and math.isfinite(world_co.z)):
                        pending_non_finite = True
                        continue

                    all_world_vertices.append(world_co)
            except Exception:
                return {
                    "result": "ERROR",
                    "error_type": "CAMERA_CHECK_COMPUTATION_ERROR",
                    "operation": "READ_MESH_VERTICES",
                    "note": "READ_MESH_VERTICES_FAILED",
                }
        finally:
            # 9f: to_mesh_clear in finally
            try:
                evaluated.to_mesh_clear()
            except Exception:
                return {
                    "result": "ERROR",
                    "error_type": "CAMERA_CHECK_COMPUTATION_ERROR",
                    "operation": "TO_MESH_CLEAR",
                    "note": "TO_MESH_CLEAR_FAILED",
                }

    # ── Step 10: aggregate ──
    if pending_non_finite:
        return {
            "result": "FAIL",
            "failure_code": "NON_FINITE_EVALUATED_VERTEX",
            "evaluated_mesh_names": evaluated_mesh_names,
        }

    if pending_zero_vertex:
        return {
            "result": "FAIL",
            "failure_code": "NO_EVALUATED_GEOMETRY",
            "evaluated_mesh_names": evaluated_mesh_names,
        }

    if len(all_world_vertices) == 0:
        return {
            "result": "FAIL",
            "failure_code": "NO_EVALUATED_GEOMETRY",
            "evaluated_mesh_names": evaluated_mesh_names,
        }

    # ── Step 11: compute world bbox 8 corners ──
    min_x = min(v.x for v in all_world_vertices)
    max_x = max(v.x for v in all_world_vertices)
    min_y = min(v.y for v in all_world_vertices)
    max_y = max(v.y for v in all_world_vertices)
    min_z = min(v.z for v in all_world_vertices)
    max_z = max(v.z for v in all_world_vertices)

    world_corners = [
        (min_x, min_y, min_z), (max_x, min_y, min_z),
        (min_x, max_y, min_z), (max_x, max_y, min_z),
        (min_x, min_y, max_z), (max_x, min_y, max_z),
        (min_x, max_y, max_z), (max_x, max_y, max_z),
    ]

    # ── Step 12: projection (R1 §19 order) ──
    try:
        from bpy_extras.object_utils import world_to_camera_view
    except Exception:
        return {
            "result": "ERROR",
            "error_type": "CAMERA_CHECK_COMPUTATION_ERROR",
            "operation": "IMPORT_WORLD_TO_CAMERA_VIEW",
            "note": "IMPORT_WORLD_TO_CAMERA_VIEW_FAILED",
        }

    import mathutils
    projected_corners = []
    try:
        for corner_ws in world_corners:
            v = mathutils.Vector(corner_ws)
            projected = world_to_camera_view(scene, camera_obj, v)
            if not (math.isfinite(projected.x) and math.isfinite(projected.y)
                    and math.isfinite(projected.z)):
                return {
                    "result": "ERROR",
                    "error_type": "CAMERA_CHECK_COMPUTATION_ERROR",
                    "operation": "PROJECT_WORLD_CORNER",
                    "note": "PROJECT_WORLD_CORNER_FAILED",
                }
            projected_corners.append((projected.x, projected.y, projected.z))
    except Exception:
        return {
            "result": "ERROR",
            "error_type": "CAMERA_CHECK_COMPUTATION_ERROR",
            "operation": "PROJECT_WORLD_CORNER",
            "note": "PROJECT_WORLD_CORNER_FAILED",
        }

    # 2. Discard z <= 0
    front_corners = [(x, y) for (x, y, z) in projected_corners if z > 0]
    projected_corner_count = len(projected_corners)

    # 3. Zero front-facing corners → BEHIND_CAMERA
    if len(front_corners) == 0:
        return {
            "result": "FAIL",
            "failure_code": "BEHIND_CAMERA",
            "camera_object_name": camera_object_name,
            "projected_corner_count": projected_corner_count,
            "front_facing_projected_corner_count": 0,
            "evaluated_mesh_names": evaluated_mesh_names,
        }

    # 4. Compute screen bbox
    try:
        screen_min_x = min(x for (x, y) in front_corners)
        screen_max_x = max(x for (x, y) in front_corners)
        screen_min_y = min(y for (x, y) in front_corners)
        screen_max_y = max(y for (x, y) in front_corners)
    except Exception:
        return {
            "result": "ERROR",
            "error_type": "CAMERA_CHECK_COMPUTATION_ERROR",
            "operation": "COMPUTE_SCREEN_BBOX",
            "note": "COMPUTE_SCREEN_BBOX_FAILED",
        }

    front_facing_count = len(front_corners)

    # 5. Check required_screen_bbox (R1 §19 step 6, before mvc)
    min_left = rsb["min_left"]
    max_right = rsb["max_right"]
    min_bottom = rsb["min_bottom"]
    max_top = rsb["max_top"]

    try:
        bbox_violation = (
            screen_min_x < min_left
            or screen_max_x > max_right
            or screen_min_y > min_bottom
            or screen_max_y < max_top
        )
    except Exception:
        return {
            "result": "ERROR",
            "error_type": "CAMERA_CHECK_COMPUTATION_ERROR",
            "operation": "COMPARE_SCREEN_BBOX",
            "note": "COMPARE_SCREEN_BBOX_FAILED",
        }

    if bbox_violation:
        return {
            "result": "FAIL",
            "failure_code": "SCREEN_BBOX_REQUIREMENT_NOT_MET",
            "camera_object_name": camera_object_name,
            "projected_corner_count": projected_corner_count,
            "front_facing_projected_corner_count": front_facing_count,
            "minimum_visible_projected_corner_count": mvc,
            "actual_screen_bbox": {
                "min_x": screen_min_x, "max_x": screen_max_x,
                "min_y": screen_min_y, "max_y": screen_max_y,
            },
            "required_screen_bbox": {
                "min_left": min_left, "max_right": max_right,
                "min_bottom": min_bottom, "max_top": max_top,
            },
            "evaluated_mesh_names": evaluated_mesh_names,
        }

    # 6. Check minimum_visible_projected_corner_count (R1 §19 step 7)
    if front_facing_count < mvc:
        return {
            "result": "FAIL",
            "failure_code": "INSUFFICIENT_VISIBLE_PROJECTED_CORNERS",
            "camera_object_name": camera_object_name,
            "projected_corner_count": projected_corner_count,
            "front_facing_projected_corner_count": front_facing_count,
            "minimum_visible_projected_corner_count": mvc,
            "evaluated_mesh_names": evaluated_mesh_names,
        }

    # ── Step 13: PASS ──
    return {
        "result": "PASS",
        "camera_object_name": camera_object_name,
        "projected_corner_count": projected_corner_count,
        "front_facing_projected_corner_count": front_facing_count,
        "minimum_visible_projected_corner_count": mvc,
        "actual_screen_bbox": {
            "min_x": screen_min_x, "max_x": screen_max_x,
            "min_y": screen_min_y, "max_y": screen_max_y,
        },
        "required_screen_bbox": {
            "min_left": min_left, "max_right": max_right,
            "min_bottom": min_bottom, "max_top": max_top,
        },
        "evaluated_mesh_names": evaluated_mesh_names,
    }


def _check_projection_groups(scene, projection_groups_block,
                             per_target_results, targets=None):
    """Check projection groups — full runtime implementation.

    Design R3 §7-§16.

    Args:
        scene: bpy.types.Scene (may be None).
        projection_groups_block: spec.projection_groups list or None.
        per_target_results: list of per-target result dicts from _check_root_objects.
        targets: list of target dicts from spec (may be None or empty).

    Returns: list of per-group result dicts, sorted by group_id.
    """
    import math

    if projection_groups_block is None or not isinstance(projection_groups_block, list):
        return []
    if len(projection_groups_block) == 0:
        return []
    if targets is None:
        targets = []

    # ── Independent scene cache (design §4.1) ──
    try:
        scene_objects_ordered = list(scene.objects)
    except Exception:
        errs = [
            {"result": "ERROR", "group_id": g.get("group_id", ""),
             "target_ids": g.get("target_ids", []),
             "error_type": "PROJECTION_GROUP_COMPUTATION_ERROR",
             "operation": "READ_SCENE_OBJECTS",
             "note": "READ_SCENE_OBJECTS_FAILED"}
            for g in projection_groups_block if isinstance(g, dict)
        ]
        errs.sort(key=lambda r: (r.get("group_id", "").casefold(),
                                  r.get("group_id", "")))
        return errs

    scene_name_by_id = {}
    try:
        for obj in scene_objects_ordered:
            scene_name_by_id[id(obj)] = obj.name
    except Exception:
        errs = [
            {"result": "ERROR", "group_id": g.get("group_id", ""),
             "target_ids": g.get("target_ids", []),
             "error_type": "PROJECTION_GROUP_COMPUTATION_ERROR",
             "operation": "READ_SCENE_OBJECTS",
             "note": "READ_SCENE_OBJECTS_FAILED"}
            for g in projection_groups_block if isinstance(g, dict)
        ]
        errs.sort(key=lambda r: (r.get("group_id", "").casefold(),
                                  r.get("group_id", "")))
        return errs

    scene_member_ids = {id(o) for o in scene_objects_ordered}
    scene_materialization_index = {
        id(o): idx for idx, o in enumerate(scene_objects_ordered)
    }

    # Build target_id → (per_target_result, target_dict) map
    ptr_by_tid = {}
    target_by_tid = {}
    for ptr in per_target_results:
        tid = ptr.get("target_id", "")
        ptr_by_tid[tid] = ptr
    for t in targets:
        tid = t.get("target_id", "")
        target_by_tid[tid] = t

    # ── Shared depsgraph (design §4.2, ≤1 call) ──
    depsgraph = None

    def _ensure_depsgraph():
        nonlocal depsgraph
        if depsgraph is not None:
            return (depsgraph, None)
        try:
            dg = bpy.context.evaluated_depsgraph_get()
            depsgraph = dg
            return (dg, None)
        except Exception:
            return (None, {
                "result": "ERROR",
                "error_type": "PROJECTION_GROUP_COMPUTATION_ERROR",
                "operation": "GET_EVALUATED_DEPSGRAPH",
                "note": "GET_EVALUATED_DEPSGRAPH_FAILED",
            })

    # ── Helper: build 16-key FAIL ──
    def _make_fail_16(gid, tids, cam_name, failure_code,
                      evaluated_mesh_names=None,
                      surviving_corners=None,
                      screen_bbox=None,
                      rsb=None, mvc=None,
                      cam_loc=None, rcob=False,
                      union_bbox=None, per_source=None,
                      failed_checks=None, actual_type=None):
        if evaluated_mesh_names is None:
            evaluated_mesh_names = []
        if per_source is None:
            per_source = {}
        if rsb is None:
            rsb = {}
        return {
            "result": "FAIL",
            "group_id": gid,
            "target_ids": list(tids),
            "camera_object_name": cam_name,
            "failure_code": failure_code,
            "evaluated_mesh_names": list(evaluated_mesh_names),
            "surviving_corners": surviving_corners,
            "screen_bbox": screen_bbox,
            "required_screen_bbox": dict(rsb),
            "minimum_visible_projected_corner_count": mvc,
            "camera_world_location": cam_loc,
            "require_camera_outside_world_bbox": rcob,
            "union_bbox": union_bbox,
            "per_source_summary": per_source,
            "failed_checks": failed_checks,
            "actual_type": actual_type,
        }

    # ── Helper: build 6-key ERROR ──
    def _make_error_6(gid, tids, operation, note):
        return {
            "result": "ERROR",
            "group_id": gid,
            "target_ids": list(tids),
            "error_type": "PROJECTION_GROUP_COMPUTATION_ERROR",
            "operation": operation,
            "note": note,
        }

    results = []

    for group in projection_groups_block:
        if not isinstance(group, dict):
            continue
        gid = group.get("group_id", "")
        tids = group.get("target_ids", [])
        if not isinstance(tids, list):
            tids = []
        aon = group.get("additional_object_names", [])
        if not isinstance(aon, list):
            aon = []
        cam_name = group.get("camera_object_name", "")
        mvc = group.get("minimum_visible_projected_corner_count", 4)
        rsb = group.get("required_screen_bbox", {})
        rcob = group.get("require_camera_outside_world_bbox", False)
        if not isinstance(rcob, bool):
            rcob = False
        if not isinstance(rsb, dict):
            rsb = {}

        # ── Step 1: camera lookup ──
        camera_match_count = 0
        camera_obj = None
        try:
            for oid, oname in scene_name_by_id.items():
                if oname == cam_name:
                    camera_match_count += 1
                    if camera_match_count == 1:
                        for obj in scene_objects_ordered:
                            if id(obj) == oid:
                                camera_obj = obj
                                break
                    else:
                        camera_obj = None
        except Exception:
            results.append(_make_error_6(
                gid, tids, "RESOLVE_CAMERA_OBJECT",
                "RESOLVE_CAMERA_OBJECT_FAILED"))
            continue

        if camera_match_count == 0:
            results.append(_make_fail_16(
                gid, tids, cam_name, "CAMERA_OBJECT_NOT_FOUND",
                rsb=rsb, mvc=mvc, rcob=rcob))
            continue
        if camera_match_count > 1:
            results.append(_make_fail_16(
                gid, tids, cam_name, "CAMERA_OBJECT_NOT_FOUND",
                rsb=rsb, mvc=mvc, rcob=rcob))
            continue

        try:
            camera_type = camera_obj.type
        except Exception:
            results.append(_make_error_6(
                gid, tids, "RESOLVE_CAMERA_OBJECT",
                "RESOLVE_CAMERA_OBJECT_FAILED"))
            continue

        if camera_type != "CAMERA":
            results.append(_make_fail_16(
                gid, tids, cam_name, "CAMERA_TYPE_MISMATCH",
                actual_type=camera_type, rsb=rsb, mvc=mvc, rcob=rcob))
            continue

        # ── Step 2: target_ids root precondition check ──
        per_source_targets = {}
        all_mesh_objects = []

        for tid in tids:
            ptr = ptr_by_tid.get(tid)
            target = target_by_tid.get(tid)
            if ptr is None:
                results.append(_make_error_6(
                    gid, tids, "RESOLVE_TARGET_GEOMETRY",
                    "RESOLVE_TARGET_GEOMETRY_FAILED"))
                break
            checks = ptr.get("checks", {})
            obj_exists = checks.get("object_exists", {})
            obj_type = checks.get("object_type", {})

            # ROOT_OBJECT_NOT_FOUND
            if obj_exists.get("failure_code") == "ROOT_OBJECT_NOT_FOUND":
                per_source_targets[tid] = {
                    "root_status": "ROOT_OBJECT_NOT_FOUND",
                    "geometry_scope": target.get("geometry_scope", "") if target else "",
                    "mesh_objects_found": 0,
                    "mesh_names": [],
                }
                results.append(_make_fail_16(
                    gid, tids, cam_name, "ROOT_OBJECT_NOT_FOUND",
                    rsb=rsb, mvc=mvc, rcob=rcob,
                    per_source={"target_ids": per_source_targets,
                                "additional_object_names": {}}))
                break
            # ROOT_OBJECT_TYPE_MISMATCH
            if obj_type.get("failure_code") == "ROOT_OBJECT_TYPE_MISMATCH":
                per_source_targets[tid] = {
                    "root_status": "ROOT_OBJECT_TYPE_MISMATCH",
                    "geometry_scope": target.get("geometry_scope", "") if target else "",
                    "mesh_objects_found": 0,
                    "mesh_names": [],
                }
                results.append(_make_fail_16(
                    gid, tids, cam_name, "ROOT_OBJECT_TYPE_MISMATCH",
                    rsb=rsb, mvc=mvc, rcob=rcob,
                    per_source={"target_ids": per_source_targets,
                                "additional_object_names": {}}))
                break
            # AMBIGUOUS / ROOT_LOOKUP_ERROR
            if obj_exists.get("result") == "ERROR":
                results.append(_make_error_6(
                    gid, tids, "RESOLVE_TARGET_GEOMETRY",
                    "RESOLVE_TARGET_GEOMETRY_FAILED"))
                break
            if obj_type.get("result") == "FAIL":
                per_source_targets[tid] = {
                    "root_status": "ROOT_OBJECT_TYPE_MISMATCH",
                    "geometry_scope": target.get("geometry_scope", "") if target else "",
                    "mesh_objects_found": 0,
                    "mesh_names": [],
                }
                results.append(_make_fail_16(
                    gid, tids, cam_name, "ROOT_OBJECT_TYPE_MISMATCH",
                    rsb=rsb, mvc=mvc, rcob=rcob,
                    per_source={"target_ids": per_source_targets,
                                "additional_object_names": {}}))
                break

            # Root PASS — collect geometry scope
            root_obj = None
            try:
                for obj in scene_objects_ordered:
                    if scene_name_by_id.get(id(obj)) == ptr.get("root_object_name", ""):
                        root_obj = obj
                        break
            except Exception:
                results.append(_make_error_6(
                    gid, tids, "RESOLVE_TARGET_GEOMETRY",
                    "RESOLVE_TARGET_GEOMETRY_FAILED"))
                break

            if root_obj is None:
                per_source_targets[tid] = {
                    "root_status": "ROOT_OBJECT_NOT_FOUND",
                    "geometry_scope": target.get("geometry_scope", "") if target else "",
                    "mesh_objects_found": 0,
                    "mesh_names": [],
                }
                results.append(_make_fail_16(
                    gid, tids, cam_name, "ROOT_OBJECT_NOT_FOUND",
                    rsb=rsb, mvc=mvc, rcob=rcob,
                    per_source={"target_ids": per_source_targets,
                                "additional_object_names": {}}))
                break

            try:
                mesh_objs = _collect_geometry_scope_objects(
                    scene_objects_ordered=scene_objects_ordered,
                    scene_member_ids=scene_member_ids,
                    scene_materialization_index=scene_materialization_index,
                    scene_name_by_id=scene_name_by_id,
                    root_obj=root_obj,
                    root_type_value=obj_type.get("actual"),
                    geometry_scope_value=target.get("geometry_scope", "SELF_MESH"),
                )
            except RuntimeError:
                results.append(_make_error_6(
                    gid, tids, "COLLECT_GEOMETRY_SCOPE",
                    "COLLECT_GEOMETRY_SCOPE_FAILED"))
                break

            per_source_targets[tid] = {
                "root_status": "PASS",
                "geometry_scope": target.get("geometry_scope", ""),
                "mesh_objects_found": len(mesh_objs),
                "mesh_names": [n for _, n in mesh_objs],
            }
            all_mesh_objects.extend(mesh_objs)

        # If target loop was broken by early result, skip remainder
        if results and results[-1]["group_id"] == gid:
            # Error/fail already appended, but need to add per_source for
            # targets that were already processed before break
            continue

        # ── Step 3: additional_object_names ──
        per_source_additional = {}
        additional_mesh_objects = []

        for name in aon:
            if not isinstance(name, str) or name == "":
                continue
            match_count = 0
            matched_obj = None
            try:
                for oid, oname in scene_name_by_id.items():
                    if oname == name:
                        match_count += 1
                        if match_count == 1:
                            for obj in scene_objects_ordered:
                                if id(obj) == oid:
                                    matched_obj = obj
                                    break
                        else:
                            matched_obj = None
            except Exception:
                results.append(_make_error_6(
                    gid, tids, "RESOLVE_ADDITIONAL_OBJECT",
                    "RESOLVE_ADDITIONAL_OBJECT_FAILED"))
                break

            if match_count == 0:
                per_source_additional[name] = {"status": "not_found",
                                                "type": None, "contributing": False}
                results.append(_make_fail_16(
                    gid, tids, cam_name, "ADDITIONAL_OBJECT_NOT_FOUND",
                    rsb=rsb, mvc=mvc, rcob=rcob,
                    per_source={"target_ids": per_source_targets,
                                "additional_object_names": per_source_additional}))
                break
            if match_count > 1:
                per_source_additional[name] = {"status": "ambiguous",
                                                "type": None, "match_count": match_count,
                                                "contributing": False}
                results.append(_make_fail_16(
                    gid, tids, cam_name, "ADDITIONAL_OBJECT_NOT_FOUND",
                    rsb=rsb, mvc=mvc, rcob=rcob,
                    per_source={"target_ids": per_source_targets,
                                "additional_object_names": per_source_additional}))
                break

            try:
                atype = matched_obj.type
            except Exception:
                results.append(_make_error_6(
                    gid, tids, "RESOLVE_ADDITIONAL_OBJECT",
                    "RESOLVE_ADDITIONAL_OBJECT_FAILED"))
                break

            if atype != "MESH":
                per_source_additional[name] = {"status": "wrong_type",
                                                "type": atype, "contributing": False}
                results.append(_make_fail_16(
                    gid, tids, cam_name, "ADDITIONAL_OBJECT_TYPE_MISMATCH",
                    actual_type=atype,
                    rsb=rsb, mvc=mvc, rcob=rcob,
                    per_source={"target_ids": per_source_targets,
                                "additional_object_names": per_source_additional}))
                break

            per_source_additional[name] = {"status": "found", "type": "MESH",
                                            "contributing": True}
            additional_mesh_objects.append((matched_obj, name))

        if results and results[-1]["group_id"] == gid:
            continue

        # ── Step 4: dedup by id() ──
        seen_ids = set()
        deduped = []
        for mobj, mname in all_mesh_objects + additional_mesh_objects:
            oid = id(mobj)
            if oid not in seen_ids:
                seen_ids.add(oid)
                deduped.append((mobj, mname))

        # ── Step 5: empty source check ──
        if len(deduped) == 0:
            results.append(_make_fail_16(
                gid, tids, cam_name, "NO_EVALUATED_GEOMETRY",
                rsb=rsb, mvc=mvc, rcob=rcob,
                per_source={"target_ids": per_source_targets,
                            "additional_object_names": per_source_additional}))
            continue

        # ── Step 6: depsgraph ──
        dg, dg_err = _ensure_depsgraph()
        if dg_err is not None:
            dg_err["group_id"] = gid
            dg_err["target_ids"] = list(tids)
            results.append(dg_err)
            continue

        # ── Step 7: evaluated geometry iteration ──
        pending_zero_vertex = False
        pending_non_finite = False
        evaluated_mesh_names = []
        all_world_vertices = []

        eval_error = None
        cleanup_failed = False
        for mesh_obj, mesh_name in deduped:
            if cleanup_failed:
                break
            try:
                evaluated = mesh_obj.evaluated_get(dg)
            except Exception:
                eval_error = _make_error_6(
                    gid, tids, "EVALUATED_GET", "EVALUATED_GET_FAILED")
                break

            try:
                mesh = evaluated.to_mesh()
            except Exception:
                eval_error = _make_error_6(
                    gid, tids, "TO_MESH", "TO_MESH_FAILED")
                break

            evaluated_mesh_names.append(mesh_name)

            try:
                try:
                    mw = evaluated.matrix_world
                except Exception:
                    eval_error = _make_error_6(
                        gid, tids, "READ_EVALUATED_MATRIX_WORLD",
                        "READ_EVALUATED_MATRIX_WORLD_FAILED")
                    break

                try:
                    vertex_count = len(mesh.vertices)
                except Exception:
                    eval_error = _make_error_6(
                        gid, tids, "READ_MESH_VERTICES",
                        "READ_MESH_VERTICES_FAILED")
                    break

                if vertex_count == 0:
                    pending_zero_vertex = True
                    continue

                try:
                    for v in mesh.vertices:
                        try:
                            vertex_co = v.co
                        except Exception:
                            eval_error = _make_error_6(
                                gid, tids, "READ_MESH_VERTICES",
                                "READ_MESH_VERTICES_FAILED")
                            break

                        try:
                            world_co = mw @ vertex_co
                        except Exception:
                            eval_error = _make_error_6(
                                gid, tids, "TRANSFORM_VERTEX_TO_WORLD_SPACE",
                                "TRANSFORM_VERTEX_TO_WORLD_SPACE_FAILED")
                            break

                        if not (math.isfinite(world_co.x) and math.isfinite(world_co.y)
                                and math.isfinite(world_co.z)):
                            pending_non_finite = True
                            continue

                        all_world_vertices.append(world_co)
                    if eval_error:
                        break
                except Exception:
                    eval_error = _make_error_6(
                        gid, tids, "READ_MESH_VERTICES",
                        "READ_MESH_VERTICES_FAILED")

                if eval_error:
                    break
            finally:
                try:
                    evaluated.to_mesh_clear()
                except Exception:
                    eval_error = _make_error_6(
                        gid, tids, "TO_MESH_CLEAR",
                        "TO_MESH_CLEAR_FAILED")
                    cleanup_failed = True

        if eval_error is not None:
            results.append(eval_error)
            continue

        # ── Step 8: aggregate ──
        if pending_non_finite:
            results.append(_make_fail_16(
                gid, tids, cam_name, "NON_FINITE_EVALUATED_VERTEX",
                evaluated_mesh_names=evaluated_mesh_names,
                rsb=rsb, mvc=mvc, rcob=rcob,
                per_source={"target_ids": per_source_targets,
                            "additional_object_names": per_source_additional}))
            continue
        if pending_zero_vertex:
            results.append(_make_fail_16(
                gid, tids, cam_name, "NO_EVALUATED_GEOMETRY",
                evaluated_mesh_names=evaluated_mesh_names,
                rsb=rsb, mvc=mvc, rcob=rcob,
                per_source={"target_ids": per_source_targets,
                            "additional_object_names": per_source_additional}))
            continue
        if len(all_world_vertices) == 0:
            results.append(_make_fail_16(
                gid, tids, cam_name, "NO_EVALUATED_GEOMETRY",
                evaluated_mesh_names=evaluated_mesh_names,
                rsb=rsb, mvc=mvc, rcob=rcob,
                per_source={"target_ids": per_source_targets,
                            "additional_object_names": per_source_additional}))
            continue

        # ── Step 9: union world bbox ──
        try:
            min_x = min(v.x for v in all_world_vertices)
            max_x = max(v.x for v in all_world_vertices)
            min_y = min(v.y for v in all_world_vertices)
            max_y = max(v.y for v in all_world_vertices)
            min_z = min(v.z for v in all_world_vertices)
            max_z = max(v.z for v in all_world_vertices)
        except Exception:
            results.append(_make_error_6(
                gid, tids, "COMPUTE_UNION_BBOX",
                "COMPUTE_UNION_BBOX_FAILED"))
            continue

        union_bbox_dict = {"min_x": min_x, "max_x": max_x,
                           "min_y": min_y, "max_y": max_y,
                           "min_z": min_z, "max_z": max_z}

        world_corners = [
            (min_x, min_y, min_z), (max_x, min_y, min_z),
            (min_x, max_y, min_z), (max_x, max_y, min_z),
            (min_x, min_y, max_z), (max_x, min_y, max_z),
            (min_x, max_y, max_z), (max_x, max_y, max_z),
        ]

        # ── Step 10: projection ──
        try:
            from bpy_extras.object_utils import world_to_camera_view
        except Exception:
            results.append(_make_error_6(
                gid, tids, "PROJECT_BBOX_CORNER",
                "PROJECT_BBOX_CORNER_FAILED"))
            continue

        import mathutils
        projected_corners = []
        try:
            for corner_ws in world_corners:
                v = mathutils.Vector(corner_ws)
                projected = world_to_camera_view(scene, camera_obj, v)
                if not (math.isfinite(projected.x) and math.isfinite(projected.y)
                        and math.isfinite(projected.z)):
                    results.append(_make_error_6(
                        gid, tids, "PROJECT_BBOX_CORNER",
                        "PROJECT_BBOX_CORNER_FAILED"))
                    break
                projected_corners.append((projected.x, projected.y, projected.z))
        except Exception:
            results.append(_make_error_6(
                gid, tids, "PROJECT_BBOX_CORNER",
                "PROJECT_BBOX_CORNER_FAILED"))
            continue

        if results and results[-1].get("group_id") == gid:
            continue

        front_corners = [(x, y) for (x, y, z) in projected_corners if z > 0]
        projected_corner_count = len(projected_corners)

        # BEHIND_CAMERA
        if len(front_corners) == 0:
            results.append(_make_fail_16(
                gid, tids, cam_name, "BEHIND_CAMERA",
                evaluated_mesh_names=evaluated_mesh_names,
                surviving_corners=0,
                union_bbox=union_bbox_dict,
                rsb=rsb, mvc=mvc, rcob=rcob,
                per_source={"target_ids": per_source_targets,
                            "additional_object_names": per_source_additional}))
            continue

        # Compute screen bbox
        try:
            screen_min_x = min(x for (x, y) in front_corners)
            screen_max_x = max(x for (x, y) in front_corners)
            screen_min_y = min(y for (x, y) in front_corners)
            screen_max_y = max(y for (x, y) in front_corners)
        except Exception:
            results.append(_make_error_6(
                gid, tids, "PROJECT_BBOX_CORNER",
                "PROJECT_BBOX_CORNER_FAILED"))
            continue

        screen_bbox_dict = {"min_x": screen_min_x, "max_x": screen_max_x,
                            "min_y": screen_min_y, "max_y": screen_max_y}
        front_facing_count = len(front_corners)

        # ── Step 11: screen bbox check (before mvc, Design R3 §13.2) ──
        ml = rsb.get("min_left", 0)
        mr = rsb.get("max_right", 1)
        mb = rsb.get("min_bottom", 0)
        mt = rsb.get("max_top", 1)

        try:
            h_fail = screen_min_x < ml or screen_max_x > mr
            v_fail = screen_min_y > mb or screen_max_y < mt
        except Exception:
            results.append(_make_error_6(
                gid, tids, "PROJECT_BBOX_CORNER",
                "PROJECT_BBOX_CORNER_FAILED"))
            continue

        if h_fail or v_fail:
            failed = []
            if h_fail:
                failed.append("horizontal_containment")
            if v_fail:
                failed.append("vertical_coverage")
            results.append(_make_fail_16(
                gid, tids, cam_name, "SCREEN_BBOX_REQUIREMENT_NOT_MET",
                evaluated_mesh_names=evaluated_mesh_names,
                surviving_corners=front_facing_count,
                screen_bbox=screen_bbox_dict,
                union_bbox=union_bbox_dict,
                rsb=rsb, mvc=mvc, rcob=rcob,
                failed_checks=failed,
                per_source={"target_ids": per_source_targets,
                            "additional_object_names": per_source_additional}))
            continue

        # ── Step 12: mvc check ──
        if front_facing_count < mvc:
            results.append(_make_fail_16(
                gid, tids, cam_name, "INSUFFICIENT_VISIBLE_PROJECTED_CORNERS",
                evaluated_mesh_names=evaluated_mesh_names,
                surviving_corners=front_facing_count,
                screen_bbox=screen_bbox_dict,
                union_bbox=union_bbox_dict,
                rsb=rsb, mvc=mvc, rcob=rcob,
                per_source={"target_ids": per_source_targets,
                            "additional_object_names": per_source_additional}))
            continue

        # ── Step 13: camera location ──
        try:
            cam_loc = camera_obj.matrix_world.translation
            cam_world_loc = [cam_loc.x, cam_loc.y, cam_loc.z]
        except Exception:
            results.append(_make_error_6(
                gid, tids, "RESOLVE_CAMERA_OBJECT",
                "RESOLVE_CAMERA_OBJECT_FAILED"))
            continue

        # ── Step 14: require_camera_outside_world_bbox ──
        if rcob:
            inside = (
                min_x <= cam_loc.x <= max_x
                and min_y <= cam_loc.y <= max_y
                and min_z <= cam_loc.z <= max_z
            )
            if inside:
                results.append(_make_fail_16(
                    gid, tids, cam_name, "CAMERA_INSIDE_WORLD_BBOX",
                    evaluated_mesh_names=evaluated_mesh_names,
                    surviving_corners=front_facing_count,
                    screen_bbox=screen_bbox_dict,
                    union_bbox=union_bbox_dict,
                    cam_loc=cam_world_loc,
                    rsb=rsb, mvc=mvc, rcob=rcob,
                    per_source={"target_ids": per_source_targets,
                                "additional_object_names": per_source_additional}))
                continue

        # ── Step 15: PASS ──
        results.append({
            "result": "PASS",
            "group_id": gid,
            "target_ids": list(tids),
            "camera_object_name": cam_name,
            "evaluated_mesh_names": evaluated_mesh_names,
            "surviving_corners": front_facing_count,
            "screen_bbox": screen_bbox_dict,
            "required_screen_bbox": dict(rsb),
            "minimum_visible_projected_corner_count": mvc,
            "camera_world_location": cam_world_loc,
            "require_camera_outside_world_bbox": rcob,
            "union_bbox": union_bbox_dict,
            "per_source_summary": {"target_ids": per_source_targets,
                                   "additional_object_names": per_source_additional},
            "failed_checks": None,
            "actual_type": None,
            "failure_code": None,
        })

    # Sort by group_id (R2 §11.2)
    results.sort(key=lambda r: (r.get("group_id", "").casefold(),
                                 r.get("group_id", "")))
    return results


def _recompute_target_overall(checks):
    """Recompute a target's overall from all checks.*.result values."""
    sub_results = []
    for key, val in checks.items():
        if isinstance(val, dict) and "result" in val:
            sub_results.append(val["result"])
    if any(r == "ERROR" for r in sub_results):
        return "ERROR"
    elif any(r == "FAIL" for r in sub_results):
        return "FAIL"
    else:
        return "PASS"


def open_blend_and_get_scene(absolute_blend_path, scene_name, spec_scene_rules,
                             targets=None, collection_rules_block=None,
                             projection_groups_block=None):
    """Open .blend, read specified Scene, return basic facts + root object results.

    Args:
        absolute_blend_path: Absolute path to .blend (pre-validated by 14A).
        scene_name: Scene name from spec.
        spec_scene_rules: scene_rules dict from spec (may be None).
        targets: list of target dicts from spec (may be None or empty).
        collection_rules_block: spec.collection_rules dict or None (may be None).
        projection_groups_block: spec.projection_groups list or None (may be None).

    Returns: dict with scene_basic, global_results, per_target_results,
             and projection_group_results.
    """
    if targets is None:
        targets = []

    # Open the blend file
    result = bpy.ops.wm.open_mainfile(filepath=absolute_blend_path)
    if result != {"FINISHED"}:
        return {"error": f"open_mainfile returned {result}", "error_type": "OPEN_FAILED"}

    # Find the specified scene
    scene = bpy.data.scenes.get(scene_name)
    context_scene_name = bpy.context.scene.name

    scene_exists = scene is not None
    actual_render_engine = scene.render.engine if scene else None
    current_frame = scene.frame_current if scene else None

    expected_render_engine = None
    if isinstance(spec_scene_rules, dict):
        expected_render_engine = spec_scene_rules.get("expected_render_engine")

    # Build scene_basic result
    checks = {}

    # scene_exists
    checks["scene_exists"] = {
        "result": "PASS" if scene_exists else "FAIL",
        "expected": True,
        "actual": scene_exists,
    }
    if not scene_exists:
        checks["scene_exists"]["failure_code"] = "SCENE_NOT_FOUND"

    # scene_name
    actual_name = scene.name if scene else None
    checks["scene_name"] = {
        "result": "PASS" if (scene_exists and actual_name == scene_name) else "NOT_CHECKED",
        "expected": scene_name,
        "actual": actual_name,
    }

    # context_scene_name (recorded only, not judged)
    checks["context_scene_name"] = {
        "result": "NOT_CHECKED",
        "actual": context_scene_name,
        "note": "RECORDED_ONLY",
    }

    # render_engine
    if expected_render_engine is not None and scene_exists:
        match = actual_render_engine == expected_render_engine
        checks["render_engine"] = {
            "result": "PASS" if match else "FAIL",
            "expected": expected_render_engine,
            "actual": actual_render_engine,
        }
        if not match:
            checks["render_engine"]["failure_code"] = "RENDER_ENGINE_MISMATCH"
    elif scene_exists:
        checks["render_engine"] = {
            "result": "NOT_CHECKED",
            "actual": actual_render_engine,
            "note": "NO_EXPECTED_RENDER_ENGINE",
        }
    else:
        checks["render_engine"] = {
            "result": "NOT_CHECKED",
            "actual": None,
            "note": "SCENE_NOT_FOUND",
        }

    # current_frame (recorded only)
    checks["current_frame"] = {
        "result": "NOT_CHECKED",
        "actual": current_frame,
        "note": "RECORDED_ONLY",
    }

    # ── Global results ──
    global_results = {
        "scene_basic": checks,
    }

    # Root object identity checks (14B-2A-I) — must remain first
    _target_caches = {}
    per_target_results = _check_root_objects(scene, targets, _target_caches=_target_caches)

    # ── Global Collection Rules (after root checks, before per-target loop) ──
    global_cr = _check_collection_rules_global(collection_rules_block)
    if global_cr is not None:
        global_results["collection_rules"] = global_cr

    # Per-target checks: Animation State → Material Assignment → Ground Contact → Camera Check → Collection Rules → overall
    if scene is not None:
        for i, target in enumerate(targets):
            if i >= len(per_target_results):
                continue

            target_result = per_target_results[i]

            as_result = _check_animation_state(scene, target)
            target_result["checks"]["animation_state"] = as_result

            ma_result = _check_material_assignment(
                scene,
                target,
                target_result,
            )
            target_result["checks"]["material_assignment_presence_check"] = ma_result

            gc_result = _check_ground_contact(
                scene,
                target,
                target_result,
            )
            target_result["checks"]["ground_contact"] = gc_result

            # Camera Check with per-target runtime cache from root phase
            cc_cache = _target_caches.get(target.get("target_id", ""))
            cc_result = _check_camera_check(
                scene,
                target,
                target_result,
                _target_cache=cc_cache,
            )
            if cc_result is not None:
                target_result["checks"]["camera_check"] = cc_result
            elif not isinstance(target.get("camera_check"), dict):
                # camera_check not configured: ensure key absent
                target_result["checks"].pop("camera_check", None)

            cr_result = _check_collection_membership(
                scene,
                target,
                target_result,
            )
            target_result["checks"]["collection_membership"] = cr_result

            target_result["overall"] = _recompute_target_overall(
                target_result["checks"])

    # ── Projection Groups (after per-target loop) ──
    pg_results = _check_projection_groups(
        scene, projection_groups_block,
        per_target_results, targets=targets,
    )

    return {
        "scene_basic": checks,
        "global_results": global_results,
        "per_target_results": per_target_results,
        "projection_group_results": pg_results,
    }
