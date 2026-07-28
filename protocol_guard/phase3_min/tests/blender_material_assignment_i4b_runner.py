"""Blender runner for Material Assignment I4B: 12 real Blender 5.1.2 scenarios.

Usage: blender --background --factory-startup --python-use-system-env --python this_file
"""
import sys, os, json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DEPS = r"C:\Users\Administrator\AppData\Roaming\Python\Python314\site-packages"
sys.path.insert(0, DEPS)
sys.path.insert(0, PROJECT_ROOT)

import bpy
from protocol_guard.phase3_min.blender_scene_reader import _check_material_assignment


def _clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat, do_unlink=True)


def _make_mesh(name, material=None):
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.active_object
    obj.name = name
    if material is not None:
        if obj.data.materials:
            obj.data.materials[0] = material
        elif material:
            obj.data.materials.append(material)
    else:
        obj.data.materials.clear()
    return obj


def _make_empty(name):
    bpy.ops.object.empty_add(type="PLAIN_AXES")
    obj = bpy.context.active_object
    obj.name = name
    return obj


def _new_material(name):
    mat = bpy.data.materials.new(name=name)
    return mat


def _root_pass(actual="MESH"):
    return {"checks": {"object_exists": {"result": "PASS"}, "object_type": {"result": "PASS", "actual": actual}}}


def _run():
    results = {"blender_version": ".".join(str(x) for x in bpy.app.version[:3]), "scenarios": []}

    # --- MA-I4B-01: MESH root, SELF_MESH, no material slot ---
    _clear_scene()
    root = _make_mesh("root", material=None)
    root.data.materials.clear()
    target = {"material_assignment": {"require_material_assignment_presence": True},
              "geometry_scope": "SELF_MESH", "root_object_name": "root"}
    r = _check_material_assignment(bpy.context.scene, target, _root_pass())
    results["scenarios"].append({"scenario_id": "MA-I4B-01", "passed": r["result"] == "FAIL",
                                 "expected": "FAIL", "actual": r["result"], "detail": str(r)})

    # --- MA-I4B-02: MESH root, SELF_MESH, 1 valid material slot ---
    _clear_scene()
    mat = _new_material("mat1")
    root = _make_mesh("root", material=mat)
    target = {"material_assignment": {"require_material_assignment_presence": True},
              "geometry_scope": "SELF_MESH", "root_object_name": "root"}
    r = _check_material_assignment(bpy.context.scene, target, _root_pass())
    results["scenarios"].append({"scenario_id": "MA-I4B-02", "passed": r["result"] == "PASS",
                                 "expected": "PASS", "actual": r["result"]})

    # --- MA-I4B-03: MESH root, SELF_MESH, 1 slot, slot.material is None ---
    _clear_scene()
    root = _make_mesh("root", material=_new_material("dummy"))
    root.data.materials[0] = None
    target = {"material_assignment": {"require_material_assignment_presence": True},
              "geometry_scope": "SELF_MESH", "root_object_name": "root"}
    r = _check_material_assignment(bpy.context.scene, target, _root_pass())
    results["scenarios"].append({"scenario_id": "MA-I4B-03", "passed": r["result"] == "FAIL",
                                 "expected": "FAIL", "actual": r["result"]})

    # --- MA-I4B-04: MESH root, SELF_MESH, 2 valid material slots ---
    _clear_scene()
    root = _make_mesh("root", material=_new_material("m1"))
    root.data.materials.append(_new_material("m2"))
    target = {"material_assignment": {"require_material_assignment_presence": True},
              "geometry_scope": "SELF_MESH", "root_object_name": "root"}
    r = _check_material_assignment(bpy.context.scene, target, _root_pass())
    results["scenarios"].append({"scenario_id": "MA-I4B-04", "passed": r["result"] == "PASS",
                                 "expected": "PASS", "actual": r["result"]})

    # --- MA-I4B-05: MESH root, SELF_MESH, mixed valid + None slot ---
    _clear_scene()
    root = _make_mesh("root", material=_new_material("ok"))
    root.data.materials.append(None)
    target = {"material_assignment": {"require_material_assignment_presence": True},
              "geometry_scope": "SELF_MESH", "root_object_name": "root"}
    r = _check_material_assignment(bpy.context.scene, target, _root_pass())
    slot_ok = r.get("per_mesh", [{}])[0].get("null_slot_indices") == [1]
    results["scenarios"].append({"scenario_id": "MA-I4B-05",
                                 "passed": r["result"] == "FAIL" and slot_ok,
                                 "expected": "FAIL, null_slot_indices=[1]", "actual": str(r)})

    # --- MA-I4B-06: EMPTY root, MESH child, DESCENDANT_MESHES ---
    _clear_scene()
    empty_root = _make_empty("root")
    child = _make_mesh("child", material=_new_material("cm"))
    child.parent = empty_root
    target = {"material_assignment": {"require_material_assignment_presence": True},
              "geometry_scope": "DESCENDANT_MESHES", "root_object_name": "root"}
    r = _check_material_assignment(bpy.context.scene, target, _root_pass("EMPTY"))
    results["scenarios"].append({"scenario_id": "MA-I4B-06", "passed": r["result"] == "PASS",
                                 "expected": "PASS", "actual": r["result"]})

    # --- MA-I4B-07: EMPTY root → EMPTY child → MESH grandchild, DESCENDANT_MESHES ---
    _clear_scene()
    empty_root = _make_empty("root")
    empty_child = _make_empty("mid")
    empty_child.parent = empty_root
    grandchild = _make_mesh("deep", material=_new_material("d"))
    grandchild.parent = empty_child
    target = {"material_assignment": {"require_material_assignment_presence": True},
              "geometry_scope": "DESCENDANT_MESHES", "root_object_name": "root"}
    r = _check_material_assignment(bpy.context.scene, target, _root_pass("EMPTY"))
    results["scenarios"].append({"scenario_id": "MA-I4B-07",
                                 "passed": r["result"] == "PASS" and len(r.get("per_mesh", [])) == 1,
                                 "expected": "PASS, 1 MESH", "actual": str(r)})

    # --- MA-I4B-08: MESH root valid, MESH child missing material, SELF_MESH ---
    _clear_scene()
    self_root = _make_mesh("root", material=_new_material("ok"))
    self_child = _make_mesh("child", material=None)
    self_child.data.materials.clear()
    self_child.parent = self_root
    target = {"material_assignment": {"require_material_assignment_presence": True},
              "geometry_scope": "SELF_MESH", "root_object_name": "root"}
    r = _check_material_assignment(bpy.context.scene, target, _root_pass())
    results["scenarios"].append({"scenario_id": "MA-I4B-08",
                                 "passed": r["result"] == "PASS" and len(r.get("per_mesh", [])) == 1,
                                 "expected": "PASS, only root checked", "actual": str(r)})

    # --- MA-I4B-09: MESH root + MESH child, SELF_AND_DESCENDANT_MESHES, both valid ---
    _clear_scene()
    both_root = _make_mesh("root", material=_new_material("r"))
    both_child = _make_mesh("child", material=_new_material("c"))
    both_child.parent = both_root
    target = {"material_assignment": {"require_material_assignment_presence": True},
              "geometry_scope": "SELF_AND_DESCENDANT_MESHES", "root_object_name": "root"}
    r = _check_material_assignment(bpy.context.scene, target, _root_pass())
    results["scenarios"].append({"scenario_id": "MA-I4B-09",
                                 "passed": r["result"] == "PASS" and len(r.get("per_mesh", [])) == 2,
                                 "expected": "PASS, 2 MESH", "actual": str(r)})

    # --- MA-I4B-10: Scene 外 descendant branch excluded ---
    _clear_scene()
    empty_root = _make_empty("root")
    inside = _make_mesh("inside", material=_new_material("ok"))
    inside.parent = empty_root
    outside = _make_mesh("outside", material=None)
    outside.data.materials.clear()
    outside.parent = empty_root
    ext_coll = bpy.data.collections.new("External")
    for coll in list(outside.users_collection):
        coll.objects.unlink(outside)
    ext_coll.objects.link(outside)
    # Verify scene membership
    scene_objs = {o.name for o in bpy.context.scene.objects}
    inside_in_scene = "inside" in scene_objs
    outside_in_scene = "outside" in scene_objs
    outside_is_child = outside.parent is empty_root
    target = {"material_assignment": {"require_material_assignment_presence": True},
              "geometry_scope": "DESCENDANT_MESHES", "root_object_name": "root"}
    r = _check_material_assignment(bpy.context.scene, target, _root_pass("EMPTY"))
    pm_names = [pm["mesh_name"] for pm in r.get("per_mesh", [])]
    passed = (r["result"] == "PASS" and len(r.get("per_mesh", [])) == 1
              and "inside" in pm_names and "outside" not in pm_names)
    results["scenarios"].append({"scenario_id": "MA-I4B-10",
                                 "passed": passed,
                                 "expected": "PASS, only inside checked",
                                 "actual": str(r),
                                 "inside_in_scene": inside_in_scene,
                                 "outside_in_scene": outside_in_scene,
                                 "outside_is_root_child": outside_is_child,
                                 "per_mesh_names": pm_names})

    # --- MA-I4B-11: 3 MESH, 2 PASS, 1 FAIL, overall FAIL ---
    _clear_scene()
    parent = _make_empty("root")
    m1 = _make_mesh("m1", material=_new_material("ok1")); m1.parent = parent
    m2 = _make_mesh("m2", material=_new_material("ok2")); m2.parent = parent
    m3 = _make_mesh("m3", material=None); m3.data.materials.clear(); m3.parent = parent
    target = {"material_assignment": {"require_material_assignment_presence": True},
              "geometry_scope": "DESCENDANT_MESHES", "root_object_name": "root"}
    r = _check_material_assignment(bpy.context.scene, target, _root_pass("EMPTY"))
    checks = {"object_exists": {"result": "PASS"}, "object_type": {"result": "PASS"},
              "material_assignment_presence_check": r}
    from protocol_guard.phase3_min.blender_scene_reader import _recompute_target_overall
    overall = _recompute_target_overall(checks)
    pm_count = len(r.get("per_mesh", []))
    passed = (pm_count == 3 and r["result"] == "FAIL" and overall == "FAIL")
    results["scenarios"].append({"scenario_id": "MA-I4B-11",
                                 "passed": passed,
                                 "expected": "FAIL, per_mesh=3, overall=FAIL",
                                 "actual": str(r),
                                 "overall": overall})

    # --- MA-I4B-12: Multi-field-group with standing + facing ---
    _clear_scene()
    multi_root = _make_mesh("root", material=_new_material("m"))
    from protocol_guard.phase3_min.blender_scene_reader import (
        _check_standing_up_axis, _check_facing_forward_axis, _recompute_target_overall,
        _check_root_objects,
    )
    standing_t = {
        "material_assignment": {"require_material_assignment_presence": True},
        "geometry_scope": "SELF_MESH",
        "root_object_name": "root",
        "standing": {"local_up_axis": "+Z", "expected_world_up_axis": "+Z",
                     "up_axis_tolerance_degrees": 0.1},
        "facing": {"local_forward_axis": "-Y", "expected_world_forward_axis": "-Y",
                   "facing_tolerance_degrees": 0.1},
    }
    per_target = {"checks": {"object_exists": {"result": "PASS"}, "object_type": {"result": "PASS", "actual": "MESH"}}}
    ma = _check_material_assignment(bpy.context.scene, standing_t, per_target)
    per_target["checks"]["material_assignment_presence_check"] = ma
    su = _check_standing_up_axis(standing_t, multi_root)
    per_target["checks"]["standing"] = su
    ff = _check_facing_forward_axis(standing_t, multi_root)
    per_target["checks"]["facing"] = ff
    overall = _recompute_target_overall(per_target["checks"])
    all_ok = (ma["result"] == "PASS" and su["up_axis"]["result"] == "PASS"
              and ff["forward_axis"]["result"] == "PASS" and overall == "PASS")
    results["scenarios"].append({"scenario_id": "MA-I4B-12",
                                 "passed": all_ok,
                                 "expected": "all PASS", "actual": f"MA={ma['result']} SU={su['up_axis']['result']} FF={ff['forward_axis']['result']} overall={overall}"})

    # Summary
    all_passed = all(s["passed"] for s in results["scenarios"])
    results["scenario_count"] = len(results["scenarios"])
    results["overall_passed"] = all_passed
    print(json.dumps(results, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    _run()
