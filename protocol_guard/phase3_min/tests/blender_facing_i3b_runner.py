"""Blender runner for 14B-3B I3B: real mathutils Facing validation.

Usage: blender --background --factory-startup --python this_file

Inlines the LOCKED _check_facing_forward_axis algorithm using real
mathutils.Matrix/Vector. Algorithm is byte-identical to production
per design R2C1 Section 2.
"""
import math, json, mathutils

# ── locked 14A core helpers (inlined) ──────────────────────────────────

_AXIS_MAP = {
    "+X": (1.0, 0.0, 0.0), "-X": (-1.0, 0.0, 0.0),
    "+Y": (0.0, 1.0, 0.0), "-Y": (0.0, -1.0, 0.0),
    "+Z": (0.0, 0.0, 1.0), "-Z": (0.0, 0.0, -1.0),
}


def axis_to_vector(name):
    v = _AXIS_MAP.get(name)
    if v is None:
        raise ValueError(f"Unknown axis: {name!r}")
    return list(v)


def vector_angle_degrees(a, b):
    dot = a[0]*b[0] + a[1]*b[1] + a[2]*b[2]
    dot = max(-1.0, min(1.0, dot))
    return math.degrees(math.acos(dot))


# ── locked facing algorithm (design R2C1 Sec 2) ────────────────────────

def check_facing_forward_axis(target, root_obj):
    facing = target.get("facing")
    if not isinstance(facing, dict):
        return {"result": "NOT_CHECKED", "forward_axis": {
            "result": "NOT_CHECKED", "note": "FORWARD_AXIS_RULES_NOT_CONFIGURED"}}

    local_fwd = facing.get("local_forward_axis")
    expected_fwd = facing.get("expected_world_forward_axis")
    tolerance = facing.get("facing_tolerance_degrees")

    if local_fwd is None or expected_fwd is None or tolerance is None:
        return {"result": "NOT_CHECKED", "forward_axis": {
            "result": "NOT_CHECKED", "note": "FORWARD_AXIS_RULES_NOT_CONFIGURED"}}

    local_vec = axis_to_vector(local_fwd)
    expected_vec = axis_to_vector(expected_fwd)

    # Step 1
    try:
        mw = root_obj.matrix_world
    except Exception:
        return {"result": "ERROR", "forward_axis": {
            "result": "ERROR", "error_type": "FACING_FORWARD_AXIS_ERROR",
            "operation": "READ_ROOT_MATRIX_WORLD", "note": "READ_ROOT_MATRIX_WORLD_FAILED"}}

    # Step 2
    try:
        m3 = mw.to_3x3()
    except Exception:
        return {"result": "ERROR", "forward_axis": {
            "result": "ERROR", "error_type": "FACING_FORWARD_AXIS_ERROR",
            "operation": "CONVERT_ROOT_MATRIX_WORLD_TO_3X3",
            "note": "CONVERT_ROOT_MATRIX_WORLD_TO_3X3_FAILED"}}

    # Step 3
    try:
        world_fwd_v = m3 @ mathutils.Vector(local_vec)
        world_fwd = (world_fwd_v.x, world_fwd_v.y, world_fwd_v.z)
    except Exception:
        return {"result": "ERROR", "forward_axis": {
            "result": "ERROR", "error_type": "FACING_FORWARD_AXIS_ERROR",
            "operation": "TRANSFORM_LOCAL_FORWARD_AXIS",
            "note": "TRANSFORM_LOCAL_FORWARD_AXIS_FAILED"}}

    # Step 4
    if not (math.isfinite(world_fwd[0]) and math.isfinite(world_fwd[1])
            and math.isfinite(world_fwd[2])):
        return {"result": "ERROR", "forward_axis": {
            "result": "ERROR", "error_type": "FACING_FORWARD_AXIS_ERROR",
            "operation": "NORMALIZE_WORLD_FORWARD_AXIS",
            "note": "NONFINITE_WORLD_FORWARD_VECTOR"}}

    try:
        length = math.sqrt(world_fwd[0]**2 + world_fwd[1]**2 + world_fwd[2]**2)
    except (OverflowError, ValueError):
        return {"result": "ERROR", "forward_axis": {
            "result": "ERROR", "error_type": "FACING_FORWARD_AXIS_ERROR",
            "operation": "NORMALIZE_WORLD_FORWARD_AXIS",
            "note": "NONFINITE_WORLD_FORWARD_VECTOR"}}

    if not math.isfinite(length):
        return {"result": "ERROR", "forward_axis": {
            "result": "ERROR", "error_type": "FACING_FORWARD_AXIS_ERROR",
            "operation": "NORMALIZE_WORLD_FORWARD_AXIS",
            "note": "NONFINITE_WORLD_FORWARD_VECTOR"}}

    if length == 0.0:
        return {"result": "ERROR", "forward_axis": {
            "result": "ERROR", "error_type": "FACING_FORWARD_AXIS_ERROR",
            "operation": "NORMALIZE_WORLD_FORWARD_AXIS",
            "note": "ZERO_LENGTH_FORWARD_VECTOR"}}

    actual_world = [world_fwd[0]/length, world_fwd[1]/length, world_fwd[2]/length]

    # Step 5
    try:
        angle = vector_angle_degrees(actual_world, expected_vec)
    except Exception:
        return {"result": "ERROR", "forward_axis": {
            "result": "ERROR", "error_type": "FACING_FORWARD_AXIS_ERROR",
            "operation": "COMPUTE_FORWARD_AXIS_ANGLE",
            "note": "COMPUTE_FORWARD_AXIS_ANGLE_FAILED"}}

    passes = angle <= tolerance
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


# ── test harness ───────────────────────────────────────────────────────

class FakeRoot:
    def __init__(self, matrix):
        self.matrix_world = matrix
        self.type = "EMPTY"


def check(local, expected, tol, matrix):
    return check_facing_forward_axis(
        {"facing": {"local_forward_axis": local,
                     "expected_world_forward_axis": expected,
                     "facing_tolerance_degrees": tol}},
        FakeRoot(matrix))


def run():
    results = []
    ident = mathutils.Matrix.Identity(4)

    scenarios = [
        ("identity_+Y_to_+Y_PASS", "+Y", "+Y", 0.0, ident, "PASS"),
        ("rot_3deg_within_tol5_PASS", "+Y", "+Y", 5.0,
         mathutils.Matrix.Rotation(math.radians(3), 4, 'X'), "PASS"),
        ("angle_eq_tol5_PASS", "+Y", "+Y", 5.0,
         mathutils.Matrix.Rotation(math.radians(5), 4, 'X'), "PASS"),
        ("angle_gt_tol5_FAIL", "+Y", "+Y", 5.0,
         mathutils.Matrix.Rotation(math.radians(10), 4, 'X'), "FAIL"),
        ("rot_x_90_FAIL", "+Y", "+Y", 5.0,
         mathutils.Matrix.Rotation(math.radians(90), 4, 'X'), "FAIL"),
        ("nonuniform_234_PASS", "+Y", "+Y", 1.0,
         mathutils.Matrix.Diagonal((2, 3, 4, 1)), "PASS"),
        ("neg_scale_Y_180_FAIL", "+Y", "+Y", 5.0,
         mathutils.Matrix.Diagonal((1, -1, 1, 1)), "FAIL"),
        ("zero_scale_Y_ERROR", "+Y", "+Y", 5.0,
         mathutils.Matrix.Diagonal((1, 0, 1, 1)), "ERROR"),
    ]

    for name, local, expected, tol, mat, exp_result in scenarios:
        r = check(local, expected, tol, mat)
        entry = {
            "name": name, "exp_result": exp_result,
            "result": r["result"], "fa_result": r["forward_axis"]["result"],
        }
        fa = r["forward_axis"]
        if fa["result"] == "ERROR":
            entry["operation"] = fa.get("operation")
            entry["note"] = fa.get("note")
        elif fa["result"] in ("PASS", "FAIL"):
            entry["angle_degrees"] = fa.get("angle_degrees")
            entry["direction"] = fa.get("actual_world_forward_direction")
            if "failure_code" in fa:
                entry["failure_code"] = fa["failure_code"]
        results.append(entry)

    print("BLENDER_FACING_I3B_RESULTS=" + json.dumps(results, ensure_ascii=False, separators=(",", ":")))
    print("PASS=OK")


if __name__ == "__main__":
    run()
