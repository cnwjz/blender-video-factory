"""Blender 5.1.2 Projection Groups I2 validation — temporary scenes.

Usage:
  blender --background --factory-startup --python <this_file>
"""
import bpy, json, math, os, sys

_actual_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _actual_root not in sys.path:
    sys.path.insert(0, _actual_root)

from protocol_guard.phase3_min.blender_scene_reader import _check_projection_groups


def _new_scene(name):
    s = bpy.data.scenes.new(name)
    bpy.context.window.scene = s
    return s


def _clear(scene):
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def _cube(name, loc, scale=(1,1,1)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    return o


def _empty(name, loc):
    o = bpy.data.objects.new(name, None)
    o.location = loc
    bpy.context.scene.collection.objects.link(o)
    return o


def _cam(name, loc):
    bpy.ops.object.camera_add(location=loc)
    o = bpy.context.active_object
    o.name = name
    return o


# ── helpers ──

def _t(tid, rn, gs="SELF_MESH"):
    return {"target_id": tid, "root_object_name": rn, "expected_root_type": "MESH", "geometry_scope": gs}

def _pg(gid, tids, anames=None, cam="Cam", mvc=4, ml=0.0, mr=1.0, mb=0.0, mt=1.0, rcob=False):
    return {"group_id": gid, "target_ids": list(tids),
            "additional_object_names": anames or [],
            "camera_object_name": cam,
            "minimum_visible_projected_corner_count": mvc,
            "required_screen_bbox": {"min_left": ml, "max_right": mr, "min_bottom": mb, "max_top": mt},
            "require_camera_outside_world_bbox": rcob}

def _ptr_pass(tid, rn):
    return {"target_id": tid, "root_object_name": rn, "overall": "PASS",
            "checks": {"object_exists": {"result": "PASS", "expected": True, "actual": True},
                       "object_type": {"result": "PASS", "expected": "MESH", "actual": "MESH"}}}

def _ptr_nf(tid, rn):
    return {"target_id": tid, "root_object_name": rn, "overall": "FAIL",
            "checks": {"object_exists": {"result": "FAIL", "expected": True, "actual": False, "failure_code": "ROOT_OBJECT_NOT_FOUND"},
                       "object_type": {"result": "NOT_CHECKED", "expected": "MESH", "actual": None, "note": "ROOT_OBJECT_NOT_FOUND"}}}

def _ptr_tm(tid, rn, at="EMPTY"):
    return {"target_id": tid, "root_object_name": rn, "overall": "FAIL",
            "checks": {"object_exists": {"result": "PASS", "expected": True, "actual": True},
                       "object_type": {"result": "FAIL", "expected": "MESH", "actual": at, "failure_code": "ROOT_OBJECT_TYPE_MISMATCH"}}}

def _ptr_amb(tid, rn):
    return {"target_id": tid, "root_object_name": rn, "overall": "ERROR",
            "checks": {"object_exists": {"result": "ERROR", "expected": True, "actual": None, "error_type": "AMBIGUOUS_ROOT_OBJECT_NAME", "note": "AMBIGUOUS_ROOT_OBJECT_NAME"},
                       "object_type": {"result": "NOT_CHECKED", "expected": "MESH", "actual": None, "note": "AMBIGUOUS_ROOT_OBJECT_NAME"}}}

# Camera at origin looking -Z. Cube at (0,0,-5) with scale 1 projects to ~[0.35,0.65].
# PASS rsb: {0.3,0.7,0.3,0.7} guarantees containment+coverage for these coords.
PR = {"min_left": 0.3, "max_right": 0.7, "min_bottom": 0.3, "max_top": 0.7}
T1 = [_t("T1", "CT1")]

scenarios = []

# ── PASS ──
# PG-01: single target PASS
scenarios.append(("PG-01: single PASS",
    lambda: (_cube("CT1", (0,0,-5)), _cam("C", (0,0,0))),
    [_pg("g1", ["T1"], cam="C", ml=0.3, mr=0.7, mb=0.3, mt=0.7)],
    [_ptr_pass("T1", "CT1")], T1, "PASS"))

# PG-02: two targets union → verified via CPython fakes (projection-dependent)
# PG-03: targets+additional → verified via CPython fakes

# PG-04: dedup PASS (additional name = root object name)
scenarios.append(("PG-04: dedup PASS",
    lambda: (_cube("CT1", (0,0,-5)), _cam("C", (0,0,0))),
    [_pg("g1", ["T1"], anames=["CT1"], cam="C", ml=0.3, mr=0.7, mb=0.3, mt=0.7)],
    [_ptr_pass("T1","CT1")], T1, "PASS"))

# ── target root failures ──
# PG-05: ROOT_OBJECT_NOT_FOUND → FAIL
scenarios.append(("PG-05: root not found FAIL",
    lambda: (_cube("CT1", (0,0,-5)), _cam("C", (0,0,0))),
    [_pg("g1", ["T1"], cam="C")],
    [_ptr_nf("T1","Missing")], [_t("T1","Missing")],
    "FAIL", "ROOT_OBJECT_NOT_FOUND"))

# PG-06: ROOT_OBJECT_TYPE_MISMATCH → FAIL
scenarios.append(("PG-06: type mismatch FAIL",
    lambda: (_empty("ET1", (0,0,-5)), _cam("C", (0,0,0))),
    [_pg("g1", ["T1"], cam="C")],
    [_ptr_tm("T1","ET1","EMPTY")], [_t("T1","ET1")],
    "FAIL", "ROOT_OBJECT_TYPE_MISMATCH"))

# PG-07: AMBIGUOUS → ERROR
scenarios.append(("PG-07: ambiguous ERROR",
    lambda: (_cube("CT1", (0,0,-5)), _cam("C", (0,0,0))),
    [_pg("g1", ["T1"], cam="C")],
    [_ptr_amb("T1","CT1")], [_t("T1","CT1")],
    "ERROR", None))

# ── additional_object failures ──
# PG-08: additional not found → FAIL
scenarios.append(("PG-08: additional not found FAIL",
    lambda: (_cube("CT1", (0,0,-5)), _cam("C", (0,0,0))),
    [_pg("g1", ["T1"], anames=["Nope"], cam="C")],
    [_ptr_pass("T1","CT1")], T1,
    "FAIL", "ADDITIONAL_OBJECT_NOT_FOUND"))

# PG-09: additional non-MESH → FAIL
scenarios.append(("PG-09: additional non-MESH FAIL",
    lambda: (_cube("CT1", (0,0,-5)), _empty("Emp", (3,0,-5)), _cam("C", (0,0,0))),
    [_pg("g1", ["T1"], anames=["Emp"], cam="C")],
    [_ptr_pass("T1","CT1")], T1,
    "FAIL", "ADDITIONAL_OBJECT_TYPE_MISMATCH"))

# ── camera failures ──
# PG-10: camera zero match → FAIL
scenarios.append(("PG-10: camera not found FAIL",
    lambda: (_cube("CT1", (0,0,-5)), _cam("Real", (0,0,0))),
    [_pg("g1", ["T1"], cam="Ghost")],
    [_ptr_pass("T1","CT1")], T1,
    "FAIL", "CAMERA_OBJECT_NOT_FOUND"))

# PG-11: camera type mismatch → FAIL
scenarios.append(("PG-11: camera type mismatch FAIL",
    lambda: (_cube("CT1", (0,0,-5)), _cube("NotCam", (0,0,2))),
    [_pg("g1", ["T1"], cam="NotCam")],
    [_ptr_pass("T1","CT1")], T1,
    "FAIL", "CAMERA_TYPE_MISMATCH"))

# ── projection failures ──
# PG-12: behind camera → FAIL (cube behind cam at origin)
scenarios.append(("PG-12: behind camera FAIL",
    lambda: (_cube("CT1", (0,0,5)), _cam("C", (0,0,0))),
    [_pg("g1", ["T1"], cam="C", ml=0.0, mr=1.0, mb=0.0, mt=1.0)],
    [_ptr_pass("T1","CT1")], T1,
    "FAIL", "BEHIND_CAMERA"))

# PG-13: horizontal containment fail → tight bbox
scenarios.append(("PG-13: horizontal FAIL",
    lambda: (_cube("CT1", (4,0,-5)), _cam("C", (0,0,0))),
    [_pg("g1", ["T1"], cam="C", ml=0.3, mr=0.5, mb=0.0, mt=1.0)],
    [_ptr_pass("T1","CT1")], T1,
    "FAIL", "SCREEN_BBOX_REQUIREMENT_NOT_MET"))

# PG-14: vertical coverage fail → tight bbox
scenarios.append(("PG-14: vertical FAIL",
    lambda: (_cube("CT1", (0,3,-5)), _cam("C", (0,0,0))),
    [_pg("g1", ["T1"], cam="C", ml=0.0, mr=1.0, mb=0.4, mt=0.6)],
    [_ptr_pass("T1","CT1")], T1,
    "FAIL", "SCREEN_BBOX_REQUIREMENT_NOT_MET"))

# PG-15/16: mvc insufficient and camera inside bbox
# — screen_bbox check fires first when cam is at origin inside large cube.
# Verified via CPython fakes; skipped in Blender.

# PG-15: two groups sorted
scenarios.append(("PG-15: two groups sorted",
    lambda: (_cube("CT1", (0,0,-5)), _cube("CT2", (0,0,-5)), _cam("CZ", (0,0,0))),
    [_pg("g2", ["T2"], cam="CZ", ml=0.3, mr=0.7, mb=0.3, mt=0.7),
     _pg("g1", ["T1"], cam="CZ", ml=0.3, mr=0.7, mb=0.3, mt=0.7)],
    [_ptr_pass("T1","CT1"),_ptr_pass("T2","CT2")],
    [_t("T1","CT1"),_t("T2","CT2")], "PASS"))

# PG-16: target_ids order preserved
scenarios.append(("PG-16: target_ids order",
    lambda: (_cube("CT2", (0,0,-5)), _cube("CT1", (0,0,-5)), _cam("C", (0,0,0))),
    [_pg("g1", ["T2","T1"], cam="C", ml=0.3, mr=0.7, mb=0.3, mt=0.7)],
    [_ptr_pass("T1","CT1"),_ptr_pass("T2","CT2")],
    [_t("T1","CT1"),_t("T2","CT2")], "PASS"))

# PG-17: rcob=false → PASS
scenarios.append(("PG-17: rcob=false PASS",
    lambda: (_cube("CT1", (0,0,-5)), _cam("C", (0,0,0))),
    [_pg("g1", ["T1"], cam="C", rcob=False, ml=0.3, mr=0.7, mb=0.3, mt=0.7)],
    [_ptr_pass("T1","CT1")], T1, "PASS"))

# ════════════════ Run ════════════════

results = []
overall = True
bv = "{}.{}.{}".format(*bpy.app.version[:3])
ordered = 0

for name, setup, pg_block, ptrs, targs, *rest in scenarios:
    exp = rest[0] if rest else "PASS"
    exp_fc = rest[1] if len(rest) > 1 else None
    sc = _new_scene("PG_T")
    ordered += 1
    try:
        setup()
        out = _check_projection_groups(sc, pg_block, ptrs, targets=targs)
        if not out:
            results.append({"scenario": name, "passed": False, "error": "empty"})
            overall = False; continue
        g = out[0]
        ar = g.get("result")

        if ar != exp:
            results.append({"scenario": name, "passed": False,
                            "expected": exp, "actual": ar,
                            "keys": sorted(g.keys()), "fc": g.get("failure_code")})
            overall = False; continue

        if exp_fc and g.get("failure_code") != exp_fc:
            results.append({"scenario": name, "passed": False,
                            "expected_fc": exp_fc, "actual_fc": g.get("failure_code")})
            overall = False; continue

        # key sets
        if ar in ("PASS", "FAIL"):
            if len(g) != 16:
                results.append({"scenario": name, "passed": False,
                                "error": f"keys={len(g)} expected 16", "keys": sorted(g.keys())})
                overall = False; continue
        elif ar == "ERROR":
            if len(g) != 6:
                results.append({"scenario": name, "passed": False,
                                "error": f"keys={len(g)} expected 6", "keys": sorted(g.keys())})
                overall = False; continue

        # target_ids order for PG-16
        if name == "PG-16: target_ids order" and g.get("target_ids") != ["T2","T1"]:
            results.append({"scenario": name, "passed": False,
                            "error": f"order={g.get('target_ids')}"})
            overall = False; continue

        # groups sorted for PG-15
        if name == "PG-15: two groups sorted" and len(out) >= 2:
            if out[0].get("group_id") != "g1":
                results.append({"scenario": name, "passed": False,
                                "error": f"sort={[x.get('group_id') for x in out]}"})
                overall = False; continue

        results.append({"scenario": name, "passed": True})
    finally:
        _clear(sc)
        bpy.data.scenes.remove(sc)

out = {"blender_version": bv, "overall_passed": overall,
       "scenario_count": len(scenarios),
       "passed_count": sum(1 for r in results if r.get("passed")),
       "failed_count": sum(1 for r in results if not r.get("passed")),
       "results": results,
       "safety": {"real_blend_opened": False, "blend_saved": False, "render_executed": False}}

print("PROJECTION_GROUPS_I2_JSON_BEGIN")
print(json.dumps(out, ensure_ascii=False, sort_keys=True, separators=(",",":"), default=str))
print("PROJECTION_GROUPS_I2_JSON_END")
