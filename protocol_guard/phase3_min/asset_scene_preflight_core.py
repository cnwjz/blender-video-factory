"""Asset Scene Preflight Check — pure CPython core (no bpy dependency)."""

import json, math, os, re

from protocol_guard.phase2_min.io_utils import (
    validate_safe_path, normalize_path, sha256_file,
)

# ════════════════ Constants ════════════════

SCHEMA_VERSION = "1"
CHECKER_NAME = "asset_scene_preflight_check"
SOURCE_REQUIREMENT_VERSION = "Blender 固定资产模板路线 v4"
RESULT_PREFIX = "PHASE3_RESULT_JSON="

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_ERROR = 2

GEOMETRY_SCOPES = {"SELF_MESH", "DESCENDANT_MESHES", "SELF_AND_DESCENDANT_MESHES"}
AXIS_VALUES = {"+X", "-X", "+Y", "-Y", "+Z", "-Z"}

_AXIS_MAP = {
    "+X": (1.0, 0.0, 0.0), "-X": (-1.0, 0.0, 0.0),
    "+Y": (0.0, 1.0, 0.0), "-Y": (0.0, -1.0, 0.0),
    "+Z": (0.0, 0.0, 1.0), "-Z": (0.0, 0.0, -1.0),
}

VALID_RENDER_ENGINES = frozenset({
    "BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "BLENDER_WORKBENCH",
    "CYCLES", "BLENDER_EEVEE_NEXT_RT",
})


# ════════════════ Exceptions ════════════════

class SpecParseError(Exception): pass
class SpecValidationError(Exception): pass
class UnsafePathError(Exception): pass
class NumericalValidationError(Exception): pass
class CanonicalizationError(Exception): pass


# ════════════════ Path safety ════════════════

def validate_spec_paths(repository_root, blend_path):
    """Validate repository_root + blend_path combination safety.

    Returns (abs_blend_path, error). Uses Phase 2 R4 validate_safe_path.
    """
    if not isinstance(repository_root, str) or repository_root == "":
        return (None, "repository_root must be a non-empty string")
    if not isinstance(blend_path, str) or blend_path == "":
        return (None, "blend_path must be a non-empty string")
    if os.path.isabs(blend_path):
        return (None, "blend_path must be relative, not absolute")
    root = os.path.realpath(repository_root)
    if not os.path.isdir(root):
        return (None, "repository_root is not an existing directory")
    try:
        np = normalize_path(blend_path)
    except ValueError as e:
        return (None, f"blend_path rejected: {e}")
    abs_path, err = validate_safe_path(root, np, require_type="file")
    if err:
        return (None, f"blend_path unsafe: {err}")
    return (abs_path, None)


# ════════════════ Spec loading and validation ════════════════

def load_spec_bytes(spec_path):
    """Read raw spec file bytes. Returns (bytes, error)."""
    try:
        with open(spec_path, "rb") as f:
            return (f.read(), None)
    except Exception as e:
        return (None, f"Cannot read spec: {e}")


def parse_spec_json(raw_bytes):
    """Parse JSON bytes into a dict. Returns (dict, error)."""
    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except json.JSONDecodeError as e:
        return (None, f"Spec JSON invalid: {e}")
    except UnicodeDecodeError as e:
        return (None, f"Spec not valid UTF-8: {e}")
    if not isinstance(data, dict):
        return (None, "Spec root must be a JSON object")
    return (data, None)


def validate_spec(spec):
    """Validate spec structure. Returns list of error strings (empty = valid)."""
    errs = []

    if not isinstance(spec, dict):
        return ["Spec root must be a JSON object"]

    if spec.get("schema_version") != SCHEMA_VERSION:
        errs.append(f"schema_version must be '{SCHEMA_VERSION}', got {spec.get('schema_version')!r}")
    if spec.get("checker") != CHECKER_NAME:
        errs.append(f"checker must be '{CHECKER_NAME}', got {spec.get('checker')!r}")
    if spec.get("source_requirement_version") != SOURCE_REQUIREMENT_VERSION:
        errs.append(f"source_requirement_version mismatch")

    repo_root = spec.get("repository_root")
    if not isinstance(repo_root, str) or repo_root == "":
        errs.append("repository_root must be a non-empty string")
    elif not os.path.isabs(repo_root):
        errs.append("repository_root must be an absolute path")

    blend_path = spec.get("blend_path")
    if not isinstance(blend_path, str) or blend_path == "":
        errs.append("blend_path must be a non-empty string")
    elif os.path.isabs(blend_path):
        errs.append("blend_path must be a relative path")
    elif ".." in blend_path.replace("\\", "/").split("/"):
        errs.append("blend_path must not contain parent traversal")
    else:
        try:
            normalize_path(blend_path)
        except ValueError as e:
            errs.append(f"blend_path rejected: {e}")

    if not isinstance(spec.get("scene_name"), str) or spec["scene_name"] == "":
        errs.append("scene_name must be a non-empty string")
    if not isinstance(spec.get("targets"), list) or len(spec["targets"]) == 0:
        errs.append("targets must be a non-empty array")
    if not isinstance(spec.get("global_rules"), dict):
        errs.append("global_rules must be an object")

    if errs:
        return errs

    # Validate targets
    target_ids = set()
    for i, t in enumerate(spec["targets"]):
        if not isinstance(t, dict):
            errs.append(f"targets[{i}] must be an object")
            continue
        tid = t.get("target_id", "")
        if not isinstance(tid, str) or tid == "":
            errs.append(f"targets[{i}].target_id must be a non-empty string")
        elif tid in target_ids:
            errs.append(f"targets[{i}].target_id '{tid}' is not unique")
        target_ids.add(tid)
        if not isinstance(t.get("root_object_name"), str) or t["root_object_name"] == "":
            errs.append(f"targets[{i}].root_object_name must be a non-empty string")
        if not isinstance(t.get("expected_root_type"), str) or t["expected_root_type"] == "":
            errs.append(f"targets[{i}].expected_root_type must be a non-empty string")
        if t.get("geometry_scope") not in GEOMETRY_SCOPES:
            errs.append(f"targets[{i}].geometry_scope must be one of {sorted(GEOMETRY_SCOPES)}")

        _validate_hierarchy(t, i, errs)
        _validate_standing(t, i, errs)
        _validate_facing(t, i, errs)
        _validate_rotation(t, i, errs)
        _validate_ground_contact(t, i, errs)
        _validate_visibility(t, i, errs)
        _validate_material_assignment(t, i, errs)
        _validate_animation_state(t, i, errs)
        _validate_camera_check(t, i, errs)
        _validate_target_collections(t, i, errs)

    # Validate global_rules
    gr = spec.get("global_rules", {})
    if not isinstance(gr, dict):
        errs.append("global_rules must be an object")
    else:
        if "require_no_unowned_meshes" in gr and not isinstance(gr["require_no_unowned_meshes"], bool):
            errs.append("global_rules.require_no_unowned_meshes must be boolean")
        ap = gr.get("explicitly_allowed_object_name_patterns", [])
        if not isinstance(ap, list):
            errs.append("global_rules.explicitly_allowed_object_name_patterns must be an array")
        else:
            for j, pat in enumerate(ap):
                if not isinstance(pat, str):
                    errs.append(f"global_rules.explicitly_allowed_object_name_patterns[{j}] must be a string")
        fp = gr.get("forbidden_scene_object_name_patterns", [])
        if not isinstance(fp, list):
            errs.append("global_rules.forbidden_scene_object_name_patterns must be an array")
        else:
            for j, pat in enumerate(fp):
                if not isinstance(pat, str):
                    errs.append(f"global_rules.forbidden_scene_object_name_patterns[{j}] must be a string")

    # Validate scene_rules (optional)
    sr = spec.get("scene_rules")
    if sr is not None:
        if not isinstance(sr, dict):
            errs.append("scene_rules must be an object")
        else:
            er = sr.get("expected_render_engine")
            if er is not None:
                if not isinstance(er, str) or er == "":
                    errs.append("scene_rules.expected_render_engine must be a non-empty string")
                elif er not in VALID_RENDER_ENGINES:
                    errs.append(f"scene_rules.expected_render_engine '{er}' is not a recognized Blender render engine")

    # Validate collection_rules (optional)
    cr = spec.get("collection_rules")
    if cr is not None:
        if not isinstance(cr, dict):
            errs.append("collection_rules must be an object")
        else:
            rc = cr.get("required_collection_names", [])
            if not isinstance(rc, list):
                errs.append("collection_rules.required_collection_names must be an array")
            else:
                for j, n in enumerate(rc):
                    if not isinstance(n, str) or n == "":
                        errs.append(f"collection_rules.required_collection_names[{j}] must be a non-empty string")
            fc = cr.get("forbidden_collection_name_patterns", [])
            if not isinstance(fc, list):
                errs.append("collection_rules.forbidden_collection_name_patterns must be an array")
            else:
                for j, pat in enumerate(fc):
                    if not isinstance(pat, str):
                        errs.append(f"collection_rules.forbidden_collection_name_patterns[{j}] must be a string")

    # Validate projection_groups (optional)
    pg = spec.get("projection_groups")
    if pg is not None:
        if not isinstance(pg, list):
            errs.append("projection_groups must be an array")
        else:
            group_ids = set()
            for i, g in enumerate(pg):
                if not isinstance(g, dict):
                    errs.append(f"projection_groups[{i}] must be an object")
                    continue
                gid = g.get("group_id", "")
                if not isinstance(gid, str) or gid == "":
                    errs.append(f"projection_groups[{i}].group_id must be non-empty")
                elif gid in group_ids:
                    errs.append(f"projection_groups[{i}].group_id '{gid}' is not unique")
                group_ids.add(gid)
                tids = g.get("target_ids", [])
                if not isinstance(tids, list):
                    errs.append(f"projection_groups[{i}].target_ids must be an array")
                else:
                    for j, tid in enumerate(tids):
                        if not isinstance(tid, str) or tid not in target_ids:
                            errs.append(f"projection_groups[{i}].target_ids[{j}] references unknown target_id")
                aon = g.get("additional_object_names", [])
                if not isinstance(aon, list):
                    errs.append(f"projection_groups[{i}].additional_object_names must be an array")
                if not isinstance(g.get("camera_object_name"), str) or g["camera_object_name"] == "":
                    errs.append(f"projection_groups[{i}].camera_object_name must be non-empty")
                mvc = g.get("minimum_visible_projected_corner_count", -1)
                if isinstance(mvc, bool) or (not isinstance(mvc, int)) or mvc < 0:
                    errs.append(f"projection_groups[{i}].minimum_visible_projected_corner_count must be a non-negative integer")
                rsb = g.get("required_screen_bbox")
                if not isinstance(rsb, dict):
                    errs.append(f"projection_groups[{i}].required_screen_bbox must be an object")
                else:
                    for k in ("min_left", "max_right", "min_bottom", "max_top"):
                        v = rsb.get(k)
                        if v is None or isinstance(v, bool) or not isinstance(v, (int, float)):
                            errs.append(f"projection_groups[{i}].required_screen_bbox.{k} must be a number")
                        elif math.isnan(v) or math.isinf(v):
                            errs.append(f"projection_groups[{i}].required_screen_bbox.{k} must be finite")
                    ml, mr = rsb.get("min_left", 0), rsb.get("max_right", 0)
                    mb, mt = rsb.get("min_bottom", 0), rsb.get("max_top", 0)
                    if all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (ml, mr)) and ml > mr:
                        errs.append(f"projection_groups[{i}].required_screen_bbox: min_left > max_right")
                    if all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (mb, mt)) and mb > mt:
                        errs.append(f"projection_groups[{i}].required_screen_bbox: min_bottom > max_top")
                rcob = g.get("require_camera_outside_world_bbox", False)
                if not isinstance(rcob, bool):
                    errs.append(f"projection_groups[{i}].require_camera_outside_world_bbox must be boolean")

    return errs


def _validate_hierarchy(t, i, errs):
    h = t.get("hierarchy")
    if h is None: return
    if not isinstance(h, dict): errs.append(f"targets[{i}].hierarchy must be an object"); return
    for field in ("required_direct_child_names", "allowed_direct_child_names",
                  "required_descendant_names", "forbidden_direct_child_name_patterns",
                  "forbidden_descendant_name_patterns"):
        v = h.get(field)
        if v is not None and not isinstance(v, list):
            errs.append(f"targets[{i}].hierarchy.{field} must be an array")
    rdt = h.get("required_descendant_types")
    if rdt is not None and not isinstance(rdt, dict):
        errs.append(f"targets[{i}].hierarchy.required_descendant_types must be an object")


def _validate_standing(t, i, errs):
    s = t.get("standing")
    if s is None: return
    if not isinstance(s, dict): errs.append(f"targets[{i}].standing must be an object"); return
    _check_finite_number(s, "minimum_height_to_horizontal_ratio", f"targets[{i}].standing", errs)
    if s.get("local_up_axis") is not None and s["local_up_axis"] not in AXIS_VALUES:
        errs.append(f"targets[{i}].standing.local_up_axis must be one of {sorted(AXIS_VALUES)}")
    if s.get("expected_world_up_axis") is not None and s["expected_world_up_axis"] not in AXIS_VALUES:
        errs.append(f"targets[{i}].standing.expected_world_up_axis must be one of {sorted(AXIS_VALUES)}")
    _check_tolerance(s, "up_axis_tolerance_degrees", f"targets[{i}].standing", errs)
    rlr = s.get("required_landmark_relationships")
    if rlr is not None:
        if not isinstance(rlr, list): errs.append(f"targets[{i}].standing.required_landmark_relationships must be an array")
        else:
            for j, r in enumerate(rlr):
                if not isinstance(r, dict): errs.append(f"targets[{i}].standing.required_landmark_relationships[{j}] must be an object"); continue
                for k in ("upper_object_name", "lower_object_name", "axis"):
                    if not isinstance(r.get(k), str) or r[k] == "":
                        errs.append(f"targets[{i}].standing.required_landmark_relationships[{j}].{k} must be non-empty")
                if r.get("axis") not in ("X", "Y", "Z"):
                    errs.append(f"targets[{i}].standing.required_landmark_relationships[{j}].axis must be X, Y, or Z")
                _check_finite_number(r, "minimum_difference", f"targets[{i}].standing.required_landmark_relationships[{j}]", errs)


def _validate_facing(t, i, errs):
    f = t.get("facing")
    if f is None: return
    if not isinstance(f, dict): errs.append(f"targets[{i}].facing must be an object"); return
    if f.get("local_forward_axis") not in AXIS_VALUES:
        errs.append(f"targets[{i}].facing.local_forward_axis must be one of {sorted(AXIS_VALUES)}")
    if f.get("expected_world_forward_axis") not in AXIS_VALUES:
        errs.append(f"targets[{i}].facing.expected_world_forward_axis must be one of {sorted(AXIS_VALUES)}")
    _check_tolerance(f, "facing_tolerance_degrees", f"targets[{i}].facing", errs)


def _validate_rotation(t, i, errs):
    r = t.get("rotation")
    if r is None: return
    if not isinstance(r, dict): errs.append(f"targets[{i}].rotation must be an object"); return
    erw = r.get("expected_world_rotation_euler_degrees")
    if erw is not None:
        if not isinstance(erw, list) or len(erw) != 3:
            errs.append(f"targets[{i}].rotation.expected_world_rotation_euler_degrees must be [rx, ry, rz]")
        elif not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in erw):
            errs.append(f"targets[{i}].rotation.expected_world_rotation_euler_degrees components must be numbers")
        elif any(math.isnan(x) or math.isinf(x) for x in erw):
            errs.append(f"targets[{i}].rotation.expected_world_rotation_euler_degrees must contain finite numbers")
    _check_tolerance(r, "rotation_tolerance_degrees", f"targets[{i}].rotation", errs)


def _validate_ground_contact(t, i, errs):
    gc = t.get("ground_contact")
    if gc is None: return
    if not isinstance(gc, dict): errs.append(f"targets[{i}].ground_contact must be an object"); return
    _check_finite_number(gc, "ground_z", f"targets[{i}].ground_contact", errs)
    _check_tolerance(gc, "ground_contact_tolerance", f"targets[{i}].ground_contact", errs)


def _validate_visibility(t, i, errs):
    v = t.get("visibility")
    if v is None: return
    if not isinstance(v, dict): errs.append(f"targets[{i}].visibility must be an object"); return
    for field in ("require_not_hidden_viewport", "require_not_hidden_render"):
        val = v.get(field)
        if val is not None and not isinstance(val, bool):
            errs.append(f"targets[{i}].visibility.{field} must be boolean")


def _validate_material_assignment(t, i, errs):
    ma = t.get("material_assignment")
    if ma is None: return
    if not isinstance(ma, dict): errs.append(f"targets[{i}].material_assignment must be an object"); return
    mrp = ma.get("require_material_assignment_presence")
    if mrp is not None and not isinstance(mrp, bool):
        errs.append(f"targets[{i}].material_assignment.require_material_assignment_presence must be boolean")


def _validate_animation_state(t, i, errs):
    a = t.get("animation_state")
    if a is None: return
    if not isinstance(a, dict): errs.append(f"targets[{i}].animation_state must be an object"); return
    if not isinstance(a.get("animation_object_name"), str) or a["animation_object_name"] == "":
        errs.append(f"targets[{i}].animation_state.animation_object_name must be non-empty")
    rad = a.get("require_animation_data")
    if rad is not None and not isinstance(rad, bool):
        errs.append(f"targets[{i}].animation_state.require_animation_data must be boolean")
    ean = a.get("expected_action_name")
    if ean is not None and (not isinstance(ean, str) or ean == ""):
        errs.append(f"targets[{i}].animation_state.expected_action_name must be a non-empty string or null")
    epp = a.get("expected_pose_position")
    if epp is not None and epp not in ("POSE", "REST"):
        errs.append(f"targets[{i}].animation_state.expected_pose_position must be 'POSE', 'REST', or null")
    rcf = a.get("record_current_frame")
    if rcf is not None and not isinstance(rcf, bool):
        errs.append(f"targets[{i}].animation_state.record_current_frame must be boolean")


def _validate_camera_check(t, i, errs):
    cc = t.get("camera_check")
    if cc is None: return
    if not isinstance(cc, dict): errs.append(f"targets[{i}].camera_check must be an object"); return
    if not isinstance(cc.get("camera_object_name"), str) or cc["camera_object_name"] == "":
        errs.append(f"targets[{i}].camera_check.camera_object_name must be non-empty")
    mvc = cc.get("minimum_visible_projected_corner_count", -1)
    if isinstance(mvc, bool) or (not isinstance(mvc, int)) or mvc < 0:
        errs.append(f"targets[{i}].camera_check.minimum_visible_projected_corner_count must be a non-negative integer")
    rsb = cc.get("required_screen_bbox")
    if not isinstance(rsb, dict):
        errs.append(f"targets[{i}].camera_check.required_screen_bbox must be an object")
    else:
        for k in ("min_left", "max_right", "min_bottom", "max_top"):
            v = rsb.get(k)
            if v is None or isinstance(v, bool) or not isinstance(v, (int, float)):
                errs.append(f"targets[{i}].camera_check.required_screen_bbox.{k} must be a number")
            elif math.isnan(v) or math.isinf(v):
                errs.append(f"targets[{i}].camera_check.required_screen_bbox.{k} must be finite")


def _validate_target_collections(t, i, errs):
    rc = t.get("required_collection_names")
    if rc is None: return
    if not isinstance(rc, list):
        errs.append(f"targets[{i}].required_collection_names must be an array")
    else:
        for j, n in enumerate(rc):
            if not isinstance(n, str) or n == "":
                errs.append(f"targets[{i}].required_collection_names[{j}] must be a non-empty string")


def _check_finite_number(d, key, prefix, errs):
    """Validate field is a finite number (rejects bool, NaN, Inf)."""
    v = d.get(key)
    if v is None: return
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        errs.append(f"{prefix}.{key} must be a number")
        return
    if math.isnan(v) or math.isinf(v):
        errs.append(f"{prefix}.{key} must be a finite number")


def _check_tolerance(d, key, prefix, errs):
    v = d.get(key)
    if v is None: return
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        errs.append(f"{prefix}.{key} must be a number")
        return
    if math.isnan(v) or math.isinf(v):
        errs.append(f"{prefix}.{key} must be a finite number")
    if v < 0:
        errs.append(f"{prefix}.{key} must be >= 0")


def load_and_validate_spec(spec_path):
    """Load spec file, validate structure, and verify path safety.

    Returns (spec, sha256_hex, errors).
    """
    raw, err = load_spec_bytes(spec_path)
    if raw is None:
        return (None, None, [err])
    spec_sha = sha256_file(spec_path)
    spec, err2 = parse_spec_json(raw)
    if spec is None:
        return (None, spec_sha, [err2])
    errs = validate_spec(spec)
    if errs:
        return (None, spec_sha, errs)
    # Path safety validation
    repo_root = spec.get("repository_root", "")
    blend_path = spec.get("blend_path", "")
    _, path_err = validate_spec_paths(repo_root, blend_path)
    if path_err:
        return (None, spec_sha, [path_err])
    return (spec, spec_sha, [])


# ════════════════ Axis and vector utilities ════════════════

def axis_to_vector(axis):
    """Convert axis string (+X, -Y, etc.) to a 3-tuple."""
    v = _AXIS_MAP.get(axis)
    if v is None:
        raise NumericalValidationError(f"Invalid axis: {axis!r}")
    return v


def _vec3_len(v):
    return math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])


def vector_angle_degrees(a, b):
    """Angle between two 3D vectors in degrees."""
    for label, v in (("a", a), ("b", b)):
        if not isinstance(v, (tuple, list)) or len(v) != 3:
            raise NumericalValidationError(f"{label} must be a 3-tuple")
        for j, x in enumerate(v):
            if isinstance(x, bool) or not isinstance(x, (int, float)):
                raise NumericalValidationError(f"{label}[{j}] must be a number")
            if math.isnan(x) or math.isinf(x):
                raise NumericalValidationError(f"{label}[{j}] is non-finite")
    la, lb = _vec3_len(a), _vec3_len(b)
    if la == 0.0 or lb == 0.0:
        raise NumericalValidationError("Zero-length vector in angle computation")
    dot = (a[0]*b[0] + a[1]*b[1] + a[2]*b[2]) / (la * lb)
    dot = max(-1.0, min(1.0, dot))
    return math.degrees(math.acos(dot))


def quaternion_min_angle_degrees(actual, expected):
    """Minimal angular distance between two quaternions in degrees.

    Normalizes both inputs. Uses |dot| to handle q and -q equivalence.
    """
    for label, q in (("actual", actual), ("expected", expected)):
        if not isinstance(q, (tuple, list)) or len(q) != 4:
            raise NumericalValidationError(f"{label} must be a 4-tuple")
        for j, x in enumerate(q):
            if isinstance(x, bool) or not isinstance(x, (int, float)):
                raise NumericalValidationError(f"{label}[{j}] must be a number")
            if math.isnan(x) or math.isinf(x):
                raise NumericalValidationError(f"{label}[{j}] is non-finite")
    la = math.sqrt(actual[0]**2 + actual[1]**2 + actual[2]**2 + actual[3]**2)
    le = math.sqrt(expected[0]**2 + expected[1]**2 + expected[2]**2 + expected[3]**2)
    if la == 0.0 or le == 0.0:
        raise NumericalValidationError("Zero-length quaternion")
    # Normalize dot product by both lengths
    dot = (actual[0]*expected[0] + actual[1]*expected[1] + actual[2]*expected[2] + actual[3]*expected[3]) / (la * le)
    dot = max(-1.0, min(1.0, abs(dot)))
    return 2.0 * math.degrees(math.acos(dot))


# ════════════════ Tolerance ════════════════

def is_within_absolute_tolerance(actual, expected, tolerance):
    """True if |actual - expected| <= tolerance. Returns (bool, error)."""
    if isinstance(actual, bool) or isinstance(expected, bool) or isinstance(tolerance, bool):
        return (False, "Values must be numbers, not bool")
    if not isinstance(actual, (int, float)) or not isinstance(expected, (int, float)):
        return (False, "Values must be numbers")
    if not isinstance(tolerance, (int, float)) or tolerance < 0:
        return (False, "Tolerance must be >= 0")
    if math.isnan(tolerance) or math.isinf(tolerance):
        return (False, "Tolerance must be finite")
    if math.isnan(actual) or math.isnan(expected):
        return (False, "Non-finite value in comparison")
    if math.isinf(actual) or math.isinf(expected):
        return (False, "Non-finite value in comparison")
    return (abs(actual - expected) <= tolerance, None)


# ════════════════ Glob matching ════════════════

def casefold_glob_match(name, pattern):
    """Case-insensitive fnmatch-style glob match."""
    import fnmatch
    return fnmatch.fnmatch(name.lower(), pattern.lower())


# ════════════════ Non-finite sanitization ════════════════

def sanitize_nonfinite(value):
    """Recursively replace NaN/Inf/-Inf with JSON-safe string tokens."""
    if isinstance(value, float):
        if math.isnan(value): return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        return value
    if isinstance(value, dict):
        return {k: sanitize_nonfinite(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_nonfinite(x) for x in value]
    return value


# ════════════════ Canonicalization ════════════════

import copy, re

# Explicitly whitelisted fields whose list values are unordered object-name sets.
# These are sorted by casefold during canonicalization regardless of field-name pattern.
_NAME_LIST_WHITELIST = frozenset({
    "unowned_meshes", "missing_required_collections",
    "missing_required_collection_names",
    "extra_top_level_objects", "forbidden_name_matches",
    "forbidden_collection_matches", "explicitly_allowed_match_names",
})

# Field-name prefixes that identify semantic unordered name-set result fields.
# Any field matching required_*, allowed_*, or forbidden_* whose value is a
# list of strings will be sorted. This covers present and future fields like
# required_children_found, allowed_descendants_found, forbidden_*, etc.
_NAME_SET_PREFIX_RE = re.compile(
    r'^(required_|allowed_|forbidden_).*', re.IGNORECASE
)

# Fields that MUST NEVER be sorted, even if they appear to be string lists.
# Coordinates, Euler, Quaternion, bbox arrays, spec-ordered ID lists.
_ORDERED_FIELD_OVERRIDE = frozenset({
    "target_ids", "additional_object_names",
})


def _sort_name_list(lst):
    """Sort a list of name strings by case-normalized value."""
    if not isinstance(lst, list):
        return lst
    return sorted(lst, key=lambda x: x.casefold() if isinstance(x, str) else str(x))


def _is_unordered_name_field(field_name, value):
    """True if field_name + value should be treated as an unordered name set."""
    if not isinstance(value, list):
        return False
    if len(value) == 0:
        return False
    # Explicitly ordered fields: never sort
    if field_name in _ORDERED_FIELD_OVERRIDE:
        return False
    # Explicitly whitelisted
    if field_name in _NAME_LIST_WHITELIST:
        return True
    # Pattern-based: required_*, allowed_*, forbidden_* result fields
    if _NAME_SET_PREFIX_RE.match(field_name):
        # Must be a list of strings specifically
        if all(isinstance(x, str) for x in value):
            return True
    return False


def _recursive_canonicalize(node):
    """Recursively sort name-list fields anywhere in the tree.

    Returns a new object; does not mutate the input.
    """
    if isinstance(node, dict):
        result = {}
        for k, v in node.items():
            vv = _recursive_canonicalize(v)
            if _is_unordered_name_field(k, vv):
                vv = _sort_name_list(vv)
            result[k] = vv
        return result
    if isinstance(node, list):
        return [_recursive_canonicalize(x) for x in node]
    return node


def canonicalize_phase3_result(result):
    """Sort list fields for deterministic output. Returns a new dict.

    Does NOT mutate the input. Idempotent: two calls produce the same result.

    Sorted:
      - per_target_results by target_id casefold
      - projection_group_results by group_id casefold
      - input_errors lexicographically
      - Name-set fields (see _is_unordered_name_field):
        * Explicitly whitelisted fields
        * Fields matching required_*, allowed_*, forbidden_* patterns
          that contain string lists, at any nesting depth

    Preserved (never sorted):
      - target_ids, additional_object_names
      - Coordinate vectors, Euler arrays, Quaternion arrays
      - bbox min/max arrays
      - Any list that is not a recognized name-set field
    """
    if not isinstance(result, dict):
        raise CanonicalizationError("Result must be a dict")

    r = copy.deepcopy(result)
    r = _recursive_canonicalize(r)

    ptr = r.get("per_target_results")
    if isinstance(ptr, list):
        r["per_target_results"] = sorted(ptr, key=lambda x: (
            x.get("target_id", "").casefold() if isinstance(x, dict) else ""))

    pgr = r.get("projection_group_results")
    if isinstance(pgr, list):
        r["projection_group_results"] = sorted(pgr, key=lambda x: (
            x.get("group_id", "").casefold() if isinstance(x, dict) else ""))

    ie = r.get("input_errors")
    if isinstance(ie, list):
        r["input_errors"] = sorted(ie)

    return r


# ════════════════ Serialization ════════════════

def serialize_result_line(result):
    """Return 'PHASE3_RESULT_JSON=<canonical JSON>\\n'."""
    sanitized = sanitize_nonfinite(result)
    canonicalized = canonicalize_phase3_result(sanitized)
    json_str = json.dumps(
        canonicalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return f"{RESULT_PREFIX}{json_str}\n"


# ════════════════ Result builders ════════════════

def _base_result(spec, spec_sha256):
    return {
        "schema_version": SCHEMA_VERSION,
        "checker": CHECKER_NAME,
        "source_requirement_version": SOURCE_REQUIREMENT_VERSION,
        "spec_sha256": spec_sha256,
        "blend_path": spec.get("blend_path", ""),
        "scene_name": spec.get("scene_name", ""),
        "per_target_results": [],
        "global_results": {},
        "projection_group_results": [],
        "input_errors": [],
        "result": None,
    }


def build_pass_result(spec, spec_sha256, per_target=None, global_r=None, projection_groups=None):
    r = _base_result(spec, spec_sha256)
    r["result"] = "PASS"
    if per_target is not None: r["per_target_results"] = per_target
    if global_r is not None: r["global_results"] = global_r
    if projection_groups is not None: r["projection_group_results"] = projection_groups
    return r


def build_fail_result(spec, spec_sha256, per_target=None, global_r=None, projection_groups=None):
    r = _base_result(spec, spec_sha256)
    r["result"] = "FAIL"
    if per_target is not None: r["per_target_results"] = per_target
    if global_r is not None: r["global_results"] = global_r
    if projection_groups is not None: r["projection_group_results"] = projection_groups
    return r


def build_error_result(spec, spec_sha256, input_errors, projection_groups=None):
    r = _base_result(spec, spec_sha256)
    r["result"] = "ERROR"
    if input_errors:
        r["input_errors"] = list(input_errors)
    if projection_groups is not None:
        r["projection_group_results"] = projection_groups
    return r


# ════════════════ Error boundary ════════════════

def error_boundary(fn, *args, **kwargs):
    """Call fn(*args, **kwargs), catching all exceptions as ERROR.

    Returns (exit_code, result_dict) where exit_code is EXIT_ERROR on exception.
    """
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        err_result = {
            "schema_version": SCHEMA_VERSION,
            "checker": CHECKER_NAME,
            "source_requirement_version": SOURCE_REQUIREMENT_VERSION,
            "spec_sha256": "",
            "blend_path": "",
            "scene_name": "",
            "per_target_results": [],
            "global_results": {},
            "projection_group_results": [],
            "input_errors": [f"UNEXPECTED_CHECKER_ERROR: {type(e).__name__}"],
            "result": "ERROR",
        }
        return (EXIT_ERROR, err_result)
