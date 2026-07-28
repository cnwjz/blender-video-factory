"""Blender runner for 14B-3A-I2: real mathutils matrix boundary tests.

Usage:
  blender --background --factory-startup --python this_file

Does NOT open any .blend file. Inlines the locked _check_standing_up_axis
algorithm using real mathutils.Matrix/Vector. The algorithm is identical
to blender_scene_reader.py:_check_standing_up_axis per design R2.
"""
import sys, os, json, math
import mathutils

# ── locked 14A core helpers (inlined to avoid yaml import chain) ──────────

_AXIS_MAP = {
    "+X": (1.0, 0.0, 0.0), "-X": (-1.0, 0.0, 0.0),
    "+Y": (0.0, 1.0, 0.0), "-Y": (0.0, -1.0, 0.0),
    "+Z": (0.0, 0.0, 1.0), "-Z": (0.0, 0.0, -1.0),
}


def axis_to_vector(axis_name):
    v = _AXIS_MAP.get(axis_name)
    if v is None:
        raise ValueError(f"Unknown axis name: {axis_name!r}")
    return list(v)


def vector_angle_degrees(a, b):
    dot = a[0]*b[0] + a[1]*b[1] + a[2]*b[2]
    dot = max(-1.0, min(1.0, dot))
    return math.degrees(math.acos(dot))


# ── locked _check_standing_up_axis (design R2, same as blender_scene_reader.py) ──

def check_standing_up_axis(target, root_obj):
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


# ── test harness ──────────────────────────────────────────────────────────

class FakeRoot:
    def __init__(self, matrix, otype="EMPTY"):
        self.matrix_world = matrix
        self.type = otype


def _check(local, expected, tol, matrix):
    target = {"standing": {
        "local_up_axis": local,
        "expected_world_up_axis": expected,
        "up_axis_tolerance_degrees": tol,
    }}
    return check_standing_up_axis(target, FakeRoot(matrix))


def run():
    results = []

    ident = mathutils.Matrix.Identity(4)

    scenarios = [
        ("identity_+Z_to_+Z_PASS", "+Z", "+Z", 0.0, ident, "PASS"),

        ("rot_x_90_+Z_to_-Y_PASS", "+Z", "-Y", 1.0,
         mathutils.Matrix.Rotation(math.radians(90), 4, 'X'), "PASS"),

        ("rot_y_90_+Z_to_+X_PASS", "+Z", "+X", 1.0,
         mathutils.Matrix.Rotation(math.radians(90), 4, 'Y'), "PASS"),

        ("neg_z_scale_180deg_FAIL", "+Z", "+Z", 5.0,
         mathutils.Matrix.Diagonal((1, 1, -1, 1)), "FAIL"),

        ("nonuniform_scale_234_PASS", "+Z", "+Z", 1.0,
         mathutils.Matrix.Diagonal((2, 3, 4, 1)), "PASS"),

        ("rot_x90_and_scale_234_PASS", "+Z", "-Y", 1.0,
         mathutils.Matrix.Rotation(math.radians(90), 4, 'X')
         @ mathutils.Matrix.Diagonal((2, 3, 4, 1)), "PASS"),

        ("shear_zx_tol30_PASS", "+Z", "+Z", 30.0,
         mathutils.Matrix(((1, 0, 0.5, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))), "PASS"),

        ("shear_zx_tol10_FAIL", "+Z", "+Z", 10.0,
         mathutils.Matrix(((1, 0, 0.5, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))), "FAIL"),

        ("zero_z_scale_ERROR", "+Z", "+Z", 5.0,
         mathutils.Matrix.Diagonal((1, 1, 0, 1)), "ERROR"),
    ]

    for name, local, expected, tol, mat, exp_result in scenarios:
        r = _check(local, expected, tol, mat)
        entry = {
            "name": name,
            "local": local,
            "expected_world": expected,
            "tolerance": tol,
            "exp_result": exp_result,
            "result": r["result"],
            "ua_result": r["up_axis"]["result"],
        }
        u = r["up_axis"]
        if u["result"] == "ERROR":
            entry["operation"] = u.get("operation")
            entry["note"] = u.get("note")
        elif u["result"] in ("PASS", "FAIL"):
            entry["angle_degrees"] = u.get("angle_degrees")
            entry["direction"] = u.get("actual_world_up_direction")
            if "failure_code" in u:
                entry["failure_code"] = u["failure_code"]
        results.append(entry)

    print("BLENDER_STANDING_I2_RESULTS=" + json.dumps(results, ensure_ascii=False, separators=(",", ":")))
    print("PASS=OK")


if __name__ == "__main__":
    run()
