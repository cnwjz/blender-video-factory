"""Blender runner for Rotation I4B R2: real Blender Objects + production imports.

Usage:
  blender --background --factory-startup --python this_file

All matrix scenarios use real Blender Objects with matrix_world set directly.
Calls production _check_rotation, _expected_euler_to_quaternion, and
quaternion_min_angle_degrees via direct import — no code duplication.
"""
import sys, os, json, math, hashlib

# Add project root and deps so production imports work inside Blender
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DEPS = r"C:\Users\Administrator\AppData\Roaming\Python\Python314\site-packages"
sys.path.insert(0, DEPS)
sys.path.insert(0, PROJECT_ROOT)

import bpy
import mathutils

from protocol_guard.phase3_min.asset_scene_preflight_core import (
    quaternion_min_angle_degrees,
)
from protocol_guard.phase3_min.blender_scene_reader import (
    _check_rotation,
    _expected_euler_to_quaternion,
)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(65536)
            if not chunk: break
            h.update(chunk)
    return h.hexdigest()


def make_empty(name, matrix):
    """Create a Blender empty with given world matrix."""
    bpy.ops.object.add(type='EMPTY')
    obj = bpy.context.object
    obj.name = name
    obj.matrix_world = matrix
    bpy.context.view_layer.update()
    return obj


def check(target, obj):
    """Call production _check_rotation on a real Blender Object."""
    return _check_rotation(target, obj)


def run():
    results = []
    ident = mathutils.Matrix.Identity(4)

    # ── q/-q equivalence (non-trivial quaternion) ──────────────
    # Use a 45° X rotation to get a non-trivial unit quaternion
    q = mathutils.Quaternion((0.9238795325112867, 0.3826834323650898, 0.0, 0.0))
    nq = mathutils.Quaternion((-0.9238795325112867, -0.3826834323650898, 0.0, 0.0))
    angle_q_nq = quaternion_min_angle_degrees(
        (q.w, q.x, q.y, q.z), (nq.w, nq.x, nq.y, nq.z))
    results.append({
        "name": "q_neg_q_non_trivial",
        "q": [q.w, q.x, q.y, q.z],
        "neg_q": [nq.w, nq.x, nq.y, nq.z],
        "angle": angle_q_nq,
        "assert": "angle_0deg_via_abs_dot",
    })

    # ── Identity ──────────────────────────────────────────────
    stage = bpy.context.scene  # ensure clean context
    obj = make_empty("IdObj", ident)
    r = check({"rotation": {"expected_world_rotation_euler_degrees": [0,0,0],
                              "rotation_tolerance_degrees": 0.0}}, obj)
    results.append({"name": "identity_0deg", "result": r["result"],
                    "actual_quat": r.get("actual_quaternion"),
                    "expected_quat": r.get("expected_quaternion"),
                    "angle": r.get("angle_degrees"),
                    "assert": {"result": "PASS", "angle_lt": 0.001}})
    bpy.data.objects.remove(obj, do_unlink=True)

    # ── X 90° rotation ────────────────────────────────────────
    rx90 = mathutils.Matrix.Rotation(math.radians(90), 4, 'X')
    obj = make_empty("RX90", rx90)
    r = check({"rotation": {"expected_world_rotation_euler_degrees": [90,0,0],
                              "rotation_tolerance_degrees": 0.5}}, obj)
    results.append({"name": "rot_x_90", "result": r["result"],
                    "actual_quat": r.get("actual_quaternion"),
                    "expected_quat": r.get("expected_quaternion"),
                    "angle": r.get("angle_degrees"),
                    "assert": {"result": "PASS", "angle_lt": 0.1}})
    bpy.data.objects.remove(obj, do_unlink=True)

    # ── Y 90° rotation ────────────────────────────────────────
    ry90 = mathutils.Matrix.Rotation(math.radians(90), 4, 'Y')
    obj = make_empty("RY90", ry90)
    r = check({"rotation": {"expected_world_rotation_euler_degrees": [0,90,0],
                              "rotation_tolerance_degrees": 0.5}}, obj)
    results.append({"name": "rot_y_90", "result": r["result"],
                    "actual_quat": r.get("actual_quaternion"),
                    "expected_quat": r.get("expected_quaternion"),
                    "angle": r.get("angle_degrees"),
                    "assert": {"result": "PASS", "angle_lt": 0.1}})
    bpy.data.objects.remove(obj, do_unlink=True)

    # ── Z 90° rotation ────────────────────────────────────────
    rz90 = mathutils.Matrix.Rotation(math.radians(90), 4, 'Z')
    obj = make_empty("RZ90", rz90)
    r = check({"rotation": {"expected_world_rotation_euler_degrees": [0,0,90],
                              "rotation_tolerance_degrees": 0.5}}, obj)
    results.append({"name": "rot_z_90", "result": r["result"],
                    "actual_quat": r.get("actual_quaternion"),
                    "expected_quat": r.get("expected_quaternion"),
                    "angle": r.get("angle_degrees"),
                    "assert": {"result": "PASS", "angle_lt": 0.1}})
    bpy.data.objects.remove(obj, do_unlink=True)

    # ── Uniform scale 2 ───────────────────────────────────────
    us2 = mathutils.Matrix.Diagonal((2, 2, 2, 1))
    obj = make_empty("US2", us2)
    r = check({"rotation": {"expected_world_rotation_euler_degrees": [0,0,0],
                              "rotation_tolerance_degrees": 0.5}}, obj)
    results.append({"name": "uniform_scale_2", "result": r["result"],
                    "actual_quat": r.get("actual_quaternion"),
                    "expected_quat": r.get("expected_quaternion"),
                    "angle": r.get("angle_degrees"),
                    "assert": {"result": "PASS", "angle_lt": 0.1}})
    bpy.data.objects.remove(obj, do_unlink=True)

    # ── Uniform scale 0.5 ─────────────────────────────────────
    us05 = mathutils.Matrix.Diagonal((0.5, 0.5, 0.5, 1))
    obj = make_empty("US05", us05)
    r = check({"rotation": {"expected_world_rotation_euler_degrees": [0,0,0],
                              "rotation_tolerance_degrees": 0.5}}, obj)
    results.append({"name": "uniform_scale_05", "result": r["result"],
                    "actual_quat": r.get("actual_quaternion"),
                    "expected_quat": r.get("expected_quaternion"),
                    "angle": r.get("angle_degrees"),
                    "assert": {"result": "PASS", "angle_lt": 0.1}})
    bpy.data.objects.remove(obj, do_unlink=True)

    # ── Non-uniform scale (2,1,1) ─────────────────────────────
    nus = mathutils.Matrix.Diagonal((2, 1, 1, 1))
    obj = make_empty("NUS", nus)
    r = check({"rotation": {"expected_world_rotation_euler_degrees": [0,0,0],
                              "rotation_tolerance_degrees": 0.5}}, obj)
    results.append({"name": "nonuniform_scale", "result": r["result"],
                    "actual_quat": r.get("actual_quaternion"),
                    "expected_quat": r.get("expected_quaternion"),
                    "angle": r.get("angle_degrees"),
                    "assert": {"result": r["result"], "angle": r.get("angle_degrees")}})
    bpy.data.objects.remove(obj, do_unlink=True)

    # ── Negative scale (-1,-1,-1) ─────────────────────────────
    ns = mathutils.Matrix.Diagonal((-1, -1, -1, 1))
    obj = make_empty("NS", ns)
    r = check({"rotation": {"expected_world_rotation_euler_degrees": [0,0,0],
                              "rotation_tolerance_degrees": 0.5}}, obj)
    results.append({"name": "negative_scale", "result": r["result"],
                    "actual_quat": r.get("actual_quaternion"),
                    "expected_quat": r.get("expected_quaternion"),
                    "angle": r.get("angle_degrees"),
                    "assert": {"result": r["result"], "actual_quat": r.get("actual_quaternion")}})
    bpy.data.objects.remove(obj, do_unlink=True)

    # ── X→Y shear ─────────────────────────────────────────────
    shear_xy = mathutils.Matrix(((1, 0.5, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))
    obj = make_empty("ShearXY", shear_xy)
    r = check({"rotation": {"expected_world_rotation_euler_degrees": [0,0,0],
                              "rotation_tolerance_degrees": 1.0}}, obj)
    results.append({"name": "shear_x_to_y", "result": r["result"],
                    "actual_quat": r.get("actual_quaternion"),
                    "expected_quat": r.get("expected_quaternion"),
                    "angle": r.get("angle_degrees"),
                    "failure_code": r.get("failure_code"),
                    "assert": {"result": "FAIL", "angle_gt": 10.0,
                               "failure_code": "OBJECT_ROTATION_OUT_OF_TOLERANCE"}})
    bpy.data.objects.remove(obj, do_unlink=True)

    # ── Y→Z shear ─────────────────────────────────────────────
    shear_yz = mathutils.Matrix(((1, 0, 0, 0), (0, 1, 0.5, 0), (0, 0, 1, 0), (0, 0, 0, 1)))
    obj = make_empty("ShearYZ", shear_yz)
    r = check({"rotation": {"expected_world_rotation_euler_degrees": [0,0,0],
                              "rotation_tolerance_degrees": 1.0}}, obj)
    results.append({"name": "shear_y_to_z", "result": r["result"],
                    "actual_quat": r.get("actual_quaternion"),
                    "expected_quat": r.get("expected_quaternion"),
                    "angle": r.get("angle_degrees"),
                    "failure_code": r.get("failure_code"),
                    "assert": {"result": "FAIL", "angle_gt": 10.0,
                               "failure_code": "OBJECT_ROTATION_OUT_OF_TOLERANCE"}})
    bpy.data.objects.remove(obj, do_unlink=True)

    # ── X reflection ──────────────────────────────────────────
    xrefl = mathutils.Matrix.Diagonal((-1, 1, 1, 1))
    obj = make_empty("XRefl", xrefl)
    r = check({"rotation": {"expected_world_rotation_euler_degrees": [0,0,0],
                              "rotation_tolerance_degrees": 0.5}}, obj)
    results.append({"name": "x_reflection", "result": r["result"],
                    "actual_quat": r.get("actual_quaternion"),
                    "expected_quat": r.get("expected_quaternion"),
                    "angle": r.get("angle_degrees"),
                    "failure_code": r.get("failure_code"),
                    "assert": {"result": "FAIL", "angle_gt": 150.0,
                               "failure_code": "OBJECT_ROTATION_OUT_OF_TOLERANCE"}})
    bpy.data.objects.remove(obj, do_unlink=True)

    # ── Tolerance: angle < tol ────────────────────────────────
    r3m = mathutils.Matrix.Rotation(math.radians(3), 4, 'X')
    obj = make_empty("R3", r3m)
    r = check({"rotation": {"expected_world_rotation_euler_degrees": [0,0,0],
                              "rotation_tolerance_degrees": 5.0}}, obj)
    results.append({"name": "angle_lt_tol", "result": r["result"],
                    "actual_quat": r.get("actual_quaternion"),
                    "angle": r.get("angle_degrees"),
                    "tolerance": 5.0,
                    "assert": {"result": "PASS", "angle_gt": 2.5, "angle_lt": 3.5}})
    bpy.data.objects.remove(obj, do_unlink=True)

    # ── Tolerance: angle = tol (MUST be PASS, angle ≈ tolerance) ─
    r5m = mathutils.Matrix.Rotation(math.radians(5), 4, 'X')
    obj = make_empty("R5", r5m)
    r = check({"rotation": {"expected_world_rotation_euler_degrees": [0,0,0],
                              "rotation_tolerance_degrees": 5.0}}, obj)
    results.append({"name": "angle_eq_tol", "result": r["result"],
                    "actual_quat": r.get("actual_quaternion"),
                    "angle": r.get("angle_degrees"),
                    "tolerance": 5.0,
                    "assert": {"result": "PASS", "angle_gt": 4.9, "angle_lt": 5.1}})
    bpy.data.objects.remove(obj, do_unlink=True)

    # ── Tolerance: angle > tol ────────────────────────────────
    r10m = mathutils.Matrix.Rotation(math.radians(10), 4, 'X')
    obj = make_empty("R10", r10m)
    r = check({"rotation": {"expected_world_rotation_euler_degrees": [0,0,0],
                              "rotation_tolerance_degrees": 5.0}}, obj)
    results.append({"name": "angle_gt_tol", "result": r["result"],
                    "actual_quat": r.get("actual_quaternion"),
                    "angle": r.get("angle_degrees"),
                    "tolerance": 5.0,
                    "failure_code": r.get("failure_code"),
                    "assert": {"result": "FAIL", "angle_gt": 9.5, "angle_lt": 10.5,
                               "failure_code": "OBJECT_ROTATION_OUT_OF_TOLERANCE"}})
    bpy.data.objects.remove(obj, do_unlink=True)

    # ── 180° difference ───────────────────────────────────────
    r180m = mathutils.Matrix.Rotation(math.radians(180), 4, 'X')
    obj = make_empty("R180", r180m)
    r = check({"rotation": {"expected_world_rotation_euler_degrees": [0,0,0],
                              "rotation_tolerance_degrees": 1.0}}, obj)
    results.append({"name": "angle_180deg", "result": r["result"],
                    "actual_quat": r.get("actual_quaternion"),
                    "angle": r.get("angle_degrees"),
                    "failure_code": r.get("failure_code"),
                    "assert": {"result": "FAIL", "angle_gt": 179.0, "angle_lt": 181.0,
                               "failure_code": "OBJECT_ROTATION_OUT_OF_TOLERANCE"}})
    bpy.data.objects.remove(obj, do_unlink=True)

    # ── NOT_CHECKED ───────────────────────────────────────────
    obj = make_empty("NCObj", ident)
    r = _check_rotation({"rotation": None}, obj)
    results.append({"name": "not_checked_null", "result": r["result"],
                    "assert": {"result": "NOT_CHECKED"}})
    bpy.data.objects.remove(obj, do_unlink=True)

    obj = make_empty("NCObj2", ident)
    r = _check_rotation({}, obj)
    results.append({"name": "not_checked_missing", "result": r["result"],
                    "assert": {"result": "NOT_CHECKED"}})
    bpy.data.objects.remove(obj, do_unlink=True)

    print("BLENDER_VERSION=" + (bpy.app.version_string if hasattr(bpy.app, 'version_string') else str(bpy.app.version)))
    print("BLENDER_PYTHON_VERSION=" + sys.version.split()[0])
    print("BLENDER_ROTATION_I4B_RESULTS=" + json.dumps(results, ensure_ascii=False, separators=(",", ":")))
    print("PASS=OK")


if __name__ == "__main__":
    # Create a fresh scene for clean testing
    bpy.ops.wm.read_homefile(use_empty=True)
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    run()
