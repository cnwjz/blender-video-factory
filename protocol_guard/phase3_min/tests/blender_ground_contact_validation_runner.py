"""Blender runner for Ground Contact validation: 14 scenarios + entry integration.

Usage:
  blender --background --factory-startup --python-use-system-env --python this_file

Outputs a single-line JSON marker:
  GROUND_CONTACT_BLENDER_VALIDATION_JSON=<compact-json>
"""
import sys, os, json, tempfile, math

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DEPS = r"C:\Users\Administrator\AppData\Roaming\Python\Python314\site-packages"
sys.path.insert(0, DEPS)
sys.path.insert(0, PROJECT_ROOT)

import bpy
from protocol_guard.phase3_min.blender_scene_reader import (
    _check_ground_contact,
    open_blend_and_get_scene,
    _recompute_target_overall,
)


def _clear_scene():
    """Remove all objects, meshes, materials from current data."""
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh, do_unlink=True)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat, do_unlink=True)
    # Remove orphan collections except master
    for coll in list(bpy.data.collections):
        if coll.name != "Collection":
            bpy.data.collections.remove(coll)


def _make_cube(name, size=1.0, location=(0, 0, 0)):
    """Create a cube mesh object."""
    bpy.ops.mesh.primitive_cube_add(size=size, location=location)
    obj = bpy.context.active_object
    obj.name = name
    return obj


def _make_empty(name, location=(0, 0, 0)):
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=location)
    obj = bpy.context.active_object
    obj.name = name
    return obj


def _make_plane(name, size=2.0, location=(0, 0, 0)):
    bpy.ops.mesh.primitive_plane_add(size=size, location=location)
    obj = bpy.context.active_object
    obj.name = name
    return obj


def _root_pass(root_type="EMPTY"):
    return {"checks": {"object_exists": {"result": "PASS"},
                       "object_type": {"result": "PASS", "actual": root_type}}}


def _lowest_z_from_result(r):
    """Extract actual_lowest_z from a PASS or FAIL result, else None."""
    return r.get("actual_lowest_z")


def _run():
    results = {
        "task_id": "GROUND_CONTACT_BLENDER_VALIDATION",
        "blender_version": ".".join(str(x) for x in bpy.app.version[:3]),
        "real_project_blend_opened": False,
        "scenarios": [],
    }

    # ═══ GC-BL-01: SELF_MESH, MESH root, vertex on ground_z ═══
    _clear_scene()
    root = _make_cube("root", size=2.0, location=(0, 0, 1.0))
    # Cube half-size=1, lowest vertex at Z=0 (world space: 0+1=1, but wait:
    # location shifts center to (0,0,1), so lowest vertex Z = 0)
    # Actually: Cube primitive is centered at origin, size=2 means half-extent=1.
    # After location=(0,0,1), lowest world Z = 0.
    target = {"ground_contact": {"ground_z": 0.0, "ground_contact_tolerance": 0.01},
              "geometry_scope": "SELF_MESH", "root_object_name": "root",
              "target_id": "T1"}
    r = _check_ground_contact(bpy.context.scene, target, _root_pass("MESH"))
    results["scenarios"].append({
        "scenario_id": "GC-BL-01",
        "description": "SELF_MESH MESH root on ground_z",
        "passed": r["result"] == "PASS" and "root" in r.get("evaluated_mesh_names", []),
        "expected": "PASS",
        "actual": r["result"],
    })

    # ═══ GC-BL-02: SELF_MESH, EMPTY root → NO_EVALUATED_GEOMETRY ═══
    _clear_scene()
    root = _make_empty("root", location=(0, 0, 0))
    target = {"ground_contact": {"ground_z": 0.0, "ground_contact_tolerance": 0.01},
              "geometry_scope": "SELF_MESH", "root_object_name": "root",
              "target_id": "T2"}
    r = _check_ground_contact(bpy.context.scene, target, _root_pass("EMPTY"))
    results["scenarios"].append({
        "scenario_id": "GC-BL-02",
        "description": "SELF_MESH EMPTY root → NO_EVALUATED_GEOMETRY",
        "passed": r["result"] == "FAIL" and r.get("failure_code") == "NO_EVALUATED_GEOMETRY",
        "expected": "FAIL/NO_EVALUATED_GEOMETRY",
        "actual": f"{r['result']}/{r.get('failure_code', 'N/A')}",
    })

    # ═══ GC-BL-03: DESCENDANT_MESHES, EMPTY root, MESH child ═══
    _clear_scene()
    root = _make_empty("root", location=(0, 0, 0))
    child = _make_cube("child", size=2.0, location=(0, 0, 0.5))
    child.parent = root
    target = {"ground_contact": {"ground_z": -0.5, "ground_contact_tolerance": 0.01},
              "geometry_scope": "DESCENDANT_MESHES", "root_object_name": "root",
              "target_id": "T3"}
    r = _check_ground_contact(bpy.context.scene, target, _root_pass("EMPTY"))
    # child cube: half-extent=1, center at (0,0,0.5), lowest world Z = -0.5
    results["scenarios"].append({
        "scenario_id": "GC-BL-03",
        "description": "DESCENDANT_MESHES: EMPTY root + MESH child",
        "passed": r["result"] == "PASS" and "child" in r.get("evaluated_mesh_names", []),
        "expected": "PASS",
        "actual": r["result"],
    })

    # ═══ GC-BL-04: SELF_AND_DESCENDANT_MESHES, MESH root + MESH child ═══
    _clear_scene()
    root = _make_cube("root", size=2.0, location=(0, 0, 0.5))
    child = _make_cube("child", size=2.0, location=(0, 0, -1.0))
    child.parent = root
    # child relative to root: world Z = 0.5 + (-1.0) = -0.5, lowest vertex = -1.5
    # root lowest vertex: 0.5 - 1.0 = -0.5
    # global lowest = -1.5
    target = {"ground_contact": {"ground_z": -1.5, "ground_contact_tolerance": 0.01},
              "geometry_scope": "SELF_AND_DESCENDANT_MESHES",
              "root_object_name": "root", "target_id": "T4"}
    r = _check_ground_contact(bpy.context.scene, target, _root_pass("MESH"))
    names = r.get("evaluated_mesh_names", [])
    passed = (r["result"] == "PASS" and "root" in names and "child" in names
              and abs(r.get("actual_lowest_z", 999) - (-1.5)) < 0.001)
    results["scenarios"].append({
        "scenario_id": "GC-BL-04",
        "description": "SELF_AND_DESCENDANT_MESHES: both in names, global lowest",
        "passed": passed,
        "expected": "PASS, root+child in names, lowest=-1.5",
        "actual": f"{r['result']}, names={names}, lowest={r.get('actual_lowest_z', 'N/A')}",
    })

    # ═══ GC-BL-05: World-space transform — object location shifts Z ═══
    _clear_scene()
    root = _make_empty("root")
    child = _make_cube("child", size=2.0, location=(0, 0, 1.25))
    child.parent = root
    # Cube half-extent=1, center at Z=1.25 → lowest vertex Z=0.25
    target = {"ground_contact": {"ground_z": 0.25, "ground_contact_tolerance": 0.001},
              "geometry_scope": "DESCENDANT_MESHES", "root_object_name": "root",
              "target_id": "T5"}
    r = _check_ground_contact(bpy.context.scene, target, _root_pass("EMPTY"))
    passed = (r["result"] == "PASS"
              and abs(r.get("actual_lowest_z", 999) - 0.25) < 0.005)
    results["scenarios"].append({
        "scenario_id": "GC-BL-05",
        "description": "World-space Z from object transform",
        "passed": passed,
        "expected": "PASS, actual_lowest_z=0.25",
        "actual": f"{r['result']}, lowest={r.get('actual_lowest_z', 'N/A')}",
    })

    # ═══ GC-BL-06: Multi-mesh global lowest ═══
    _clear_scene()
    root = _make_empty("root")
    m1 = _make_cube("m1", size=2.0, location=(0, 0, 2.0))
    m1.parent = root
    m2 = _make_cube("m2", size=2.0, location=(0, 0, -1.0))
    m2.parent = root
    m3 = _make_cube("m3", size=2.0, location=(0, 0, 0.5))
    m3.parent = root
    # m1 lowest Z = 1.0, m2 lowest Z = -2.0, m3 lowest Z = -0.5 → global = -2.0
    target = {"ground_contact": {"ground_z": -2.0, "ground_contact_tolerance": 0.001},
              "geometry_scope": "DESCENDANT_MESHES", "root_object_name": "root",
              "target_id": "T6"}
    r = _check_ground_contact(bpy.context.scene, target, _root_pass("EMPTY"))
    passed = (r["result"] == "PASS"
              and abs(r.get("actual_lowest_z", 999) - (-2.0)) < 0.005
              and len(r.get("evaluated_mesh_names", [])) == 3)
    results["scenarios"].append({
        "scenario_id": "GC-BL-06",
        "description": "3 meshes with different lowest Z",
        "passed": passed,
        "expected": "PASS, lowest=-2.0, 3 mesh names",
        "actual": f"{r['result']}, lowest={r.get('actual_lowest_z','N/A')}, names={r.get('evaluated_mesh_names',[])}",
    })

    # ═══ GC-BL-07: Tolerance boundary — above ═══
    _clear_scene()
    root = _make_cube("root", size=2.0, location=(0, 0, 0.0))
    # Cube lowest Z = -1.0. ground_z = -1.0, tolerance=0.0 → exact match → PASS
    target = {"ground_contact": {"ground_z": -1.0, "ground_contact_tolerance": 0.0},
              "geometry_scope": "SELF_MESH", "root_object_name": "root",
              "target_id": "T7"}
    r = _check_ground_contact(bpy.context.scene, target, _root_pass("MESH"))
    results["scenarios"].append({
        "scenario_id": "GC-BL-07",
        "description": "Tolerance boundary: exact match (tolerance=0)",
        "passed": r["result"] == "PASS",
        "expected": "PASS",
        "actual": r["result"],
    })

    # ═══ GC-BL-08: Tolerance boundary — below (穿地) ═══
    _clear_scene()
    root = _make_cube("root", size=2.0, location=(0, 0, -0.1))
    # Cube lowest Z = -1.1. ground_z = -1.0, tolerance=0.05 → |(-1.1)-(-1.0)|=0.1 > 0.05 → FAIL
    target = {"ground_contact": {"ground_z": -1.0, "ground_contact_tolerance": 0.05},
              "geometry_scope": "SELF_MESH", "root_object_name": "root",
              "target_id": "T8"}
    r = _check_ground_contact(bpy.context.scene, target, _root_pass("MESH"))
    passed = r["result"] == "FAIL" and r.get("failure_code") == "GROUND_CONTACT_OUT_OF_TOLERANCE"
    results["scenarios"].append({
        "scenario_id": "GC-BL-08",
        "description": "Below ground, out of tolerance → FAIL (穿地)",
        "passed": passed,
        "expected": "FAIL/GROUND_CONTACT_OUT_OF_TOLERANCE",
        "actual": f"{r['result']}/{r.get('failure_code','N/A')}",
    })

    # ═══ GC-BL-09: Tolerance boundary — above (悬空) ═══
    _clear_scene()
    root = _make_cube("root", size=2.0, location=(0, 0, 0.2))
    # Cube lowest Z = -0.8. ground_z = -1.0, tolerance=0.05 → |(-0.8)-(-1.0)|=0.2 > 0.05 → FAIL
    target = {"ground_contact": {"ground_z": -1.0, "ground_contact_tolerance": 0.05},
              "geometry_scope": "SELF_MESH", "root_object_name": "root",
              "target_id": "T9"}
    r = _check_ground_contact(bpy.context.scene, target, _root_pass("MESH"))
    passed = r["result"] == "FAIL" and r.get("failure_code") == "GROUND_CONTACT_OUT_OF_TOLERANCE"
    results["scenarios"].append({
        "scenario_id": "GC-BL-09",
        "description": "Above ground, out of tolerance → FAIL (悬空)",
        "passed": passed,
        "expected": "FAIL/GROUND_CONTACT_OUT_OF_TOLERANCE",
        "actual": f"{r['result']}/{r.get('failure_code','N/A')}",
    })

    # ═══ GC-BL-10: Tolerance=0.0, slight deviation → FAIL ═══
    _clear_scene()
    root = _make_cube("root", size=2.0, location=(0, 0, 0.001))
    # Cube lowest Z = -0.999. ground_z = -1.0, tolerance=0.0 → FAIL
    target = {"ground_contact": {"ground_z": -1.0, "ground_contact_tolerance": 0.0},
              "geometry_scope": "SELF_MESH", "root_object_name": "root",
              "target_id": "T10"}
    r = _check_ground_contact(bpy.context.scene, target, _root_pass("MESH"))
    passed = r["result"] == "FAIL"
    results["scenarios"].append({
        "scenario_id": "GC-BL-10",
        "description": "tolerance=0.0, slight deviation → FAIL",
        "passed": passed,
        "expected": "FAIL",
        "actual": r["result"],
    })

    # ═══ GC-BL-11: Zero vertices → NO_EVALUATED_GEOMETRY ═══
    _clear_scene()
    root = _make_empty("root")
    # Create a mesh with zero vertices using bmesh
    import bmesh
    empty_mesh_data = bpy.data.meshes.new("empty_mesh")
    zero_v = bpy.data.objects.new("zero_v", empty_mesh_data)
    bpy.context.scene.collection.objects.link(zero_v)
    zero_v.parent = root
    target = {"ground_contact": {"ground_z": 0.0, "ground_contact_tolerance": 0.01},
              "geometry_scope": "DESCENDANT_MESHES", "root_object_name": "root",
              "target_id": "T11"}
    r = _check_ground_contact(bpy.context.scene, target, _root_pass("EMPTY"))
    passed = r["result"] == "FAIL" and r.get("failure_code") == "NO_EVALUATED_GEOMETRY"
    results["scenarios"].append({
        "scenario_id": "GC-BL-11",
        "description": "Zero-vertex mesh → NO_EVALUATED_GEOMETRY",
        "passed": passed,
        "expected": "FAIL/NO_EVALUATED_GEOMETRY",
        "actual": f"{r['result']}/{r.get('failure_code','N/A')}",
    })

    # ═══ GC-BL-12: Evaluated modifier geometry (Solidify) ═══
    _clear_scene()
    root = _make_empty("root")
    plane = _make_plane("plane", size=2.0, location=(0, 0, 0.0))
    plane.parent = root
    # Add Solidify modifier — original plane has Z=0, solidify makes it thicker
    mod = plane.modifiers.new(name="Solidify", type="SOLIDIFY")
    mod.thickness = 0.4  # total thickness 0.4, extends downward by -0.2
    mod.offset = -1.0    # offset entirely below original plane
    # Evaluated: lowest vertex Z ≈ -0.4 (plane center at 0, thickness 0.4 downward)
    target = {"ground_contact": {"ground_z": -0.4, "ground_contact_tolerance": 0.005},
              "geometry_scope": "DESCENDANT_MESHES", "root_object_name": "root",
              "target_id": "T12"}
    r = _check_ground_contact(bpy.context.scene, target, _root_pass("EMPTY"))
    # The evaluated mesh should have vertices below Z=0 (plane's original vertices)
    # Verify actual_lowest_z < 0 (modifier effect, not just original geometry)
    actual_z = r.get("actual_lowest_z", 0)
    passed = r["result"] == "PASS" and actual_z < -0.1
    results["scenarios"].append({
        "scenario_id": "GC-BL-12",
        "description": "Solidify modifier → evaluated geometry lowest Z",
        "passed": passed,
        "expected": f"PASS, actual_lowest_z≈-0.4",
        "actual": f"{r['result']}, lowest={actual_z}",
    })

    # ═══ GC-BL-13: Scene membership filtering — real separate Scene ═══
    _clear_scene()
    root = _make_empty("root")
    child = _make_cube("inside", size=2.0, location=(0, 0, 0))
    child.parent = root
    # child cube half-extent=1 at Z=0 → lowest Z = -1.0

    # Create outside MESH in a different Scene, then parent to root
    outside_scene = bpy.data.scenes.new("OutsideScene")
    bpy.context.window.scene = outside_scene
    outside = _make_cube("outside", size=2.0, location=(0, 0, -5.0))
    # outside cube half-extent=1 at Z=-5 → lowest Z = -6.0 (much lower)
    # Switch back to target scene
    bpy.context.window.scene = bpy.data.scenes["Scene"]
    # parent outside to root — it is reachable from root.children but NOT in target scene
    outside.parent = root
    # Verify assertions
    target_scene = bpy.data.scenes["Scene"]
    outside_in_target_scene = outside.name in {o.name for o in target_scene.objects}
    outside_reachable_from_root = outside in list(root.children)

    target = {"ground_contact": {"ground_z": -1.0, "ground_contact_tolerance": 0.001},
              "geometry_scope": "DESCENDANT_MESHES", "root_object_name": "root",
              "target_id": "T13"}
    r = _check_ground_contact(target_scene, target, _root_pass("EMPTY"))
    names = r.get("evaluated_mesh_names", [])
    # If outside were erroneously included, actual_lowest_z would be -6.0 (FAIL).
    # With correct filtering, only 'inside' at -1.0 is used → PASS.
    passed = (r["result"] == "PASS" and "inside" in names and "outside" not in names
              and abs(r.get("actual_lowest_z", 999) - (-1.0)) < 0.005
              and not outside_in_target_scene
              and outside_reachable_from_root)
    results["scenarios"].append({
        "scenario_id": "GC-BL-13",
        "description": "Scene membership: outside in different scene excluded",
        "passed": passed,
        "expected": "PASS, only 'inside', outside excluded",
        "actual": f"{r['result']}, names={names}, lowest={r.get('actual_lowest_z','N/A')}",
        "outside_in_target_scene": outside_in_target_scene,
        "outside_reachable_from_root": outside_reachable_from_root,
    })

    # Clean up the extra scene
    bpy.data.scenes.remove(outside_scene, do_unlink=True)

    # ═══ GC-BL-14: Deterministic order — repeat run ═══
    _clear_scene()
    root = _make_empty("root")
    # Create meshes in non-alphabetical order
    c = _make_cube("z_mesh", size=1.0, location=(0, 0, 0.5)); c.parent = root
    a = _make_cube("a_mesh", size=1.0, location=(0, 0, 0.5)); a.parent = root
    b = _make_cube("m_mesh", size=1.0, location=(0, 0, 0.5)); b.parent = root
    target = {"ground_contact": {"ground_z": 0.0, "ground_contact_tolerance": 0.01},
              "geometry_scope": "DESCENDANT_MESHES", "root_object_name": "root",
              "target_id": "T14"}
    r1 = _check_ground_contact(bpy.context.scene, target, _root_pass("EMPTY"))
    r2 = _check_ground_contact(bpy.context.scene, target, _root_pass("EMPTY"))
    names1 = r1.get("evaluated_mesh_names", [])
    names2 = r2.get("evaluated_mesh_names", [])
    passed = (names1 == names2 and r1["actual_lowest_z"] == r2["actual_lowest_z"])
    results["scenarios"].append({
        "scenario_id": "GC-BL-14",
        "description": "Deterministic order across two runs",
        "passed": passed,
        "expected": "identical names and lowest_z",
        "actual": f"r1={names1}, r2={names2}, z1={r1.get('actual_lowest_z')}, z2={r2.get('actual_lowest_z')}",
    })

    # ═══ Entry integration test (PASS + FAIL) ═══
    entry_pass_case_passed = False
    entry_fail_case_passed = False
    entry_integration_passed = False
    tmp_dir = None
    tmp_cleaned = False
    try:
        _clear_scene()
        root = _make_empty("root")
        child = _make_cube("child", size=2.0, location=(0, 0, 0.5))
        child.parent = root
        # child cube half-extent=1 at Z=0.5 → lowest Z = -0.5

        # Save to temporary blend
        tmp_dir = tempfile.mkdtemp(prefix="gc_val_")
        tmp_blend = os.path.join(tmp_dir, "temp.blend")
        bpy.ops.wm.save_as_mainfile(filepath=tmp_blend)

        # ── PASS case ──
        spec_targets_pass = [{
            "target_id": "T1",
            "root_object_name": "root",
            "expected_root_type": "EMPTY",
            "geometry_scope": "DESCENDANT_MESHES",
            "ground_contact": {"ground_z": -0.5, "ground_contact_tolerance": 0.01},
        }]
        scene_data = open_blend_and_get_scene(
            absolute_blend_path=tmp_blend,
            scene_name="Scene",
            spec_scene_rules=None,
            targets=spec_targets_pass,
            collection_rules_block=None,
        )
        ptr = scene_data.get("per_target_results", [])
        if len(ptr) >= 1:
            checks = ptr[0].get("checks", {})
            gc = checks.get("ground_contact", {})
            gc_pass_ok = (gc.get("result") == "PASS"
                          and abs(gc.get("actual_lowest_z", 999) - (-0.5)) < 0.005)
            overall_pass_ok = ptr[0].get("overall") == "PASS"
            other_ok = (
                "object_exists" in checks
                and "object_type" in checks
                and "animation_state" in checks
                and "material_assignment_presence_check" in checks
                and "collection_membership" in checks
            )
            entry_pass_case_passed = gc_pass_ok and overall_pass_ok and other_ok

        # ── FAIL case ──
        spec_targets_fail = [{
            "target_id": "T1",
            "root_object_name": "root",
            "expected_root_type": "EMPTY",
            "geometry_scope": "DESCENDANT_MESHES",
            "ground_contact": {"ground_z": 999.0, "ground_contact_tolerance": 0.01},
        }]
        scene_data2 = open_blend_and_get_scene(
            absolute_blend_path=tmp_blend,
            scene_name="Scene",
            spec_scene_rules=None,
            targets=spec_targets_fail,
            collection_rules_block=None,
        )
        ptr2 = scene_data2.get("per_target_results", [])
        if len(ptr2) >= 1:
            checks2 = ptr2[0].get("checks", {})
            gc2 = checks2.get("ground_contact", {})
            gc_fail_ok = (gc2.get("result") == "FAIL"
                          and gc2.get("failure_code") == "GROUND_CONTACT_OUT_OF_TOLERANCE")
            overall_fail_ok = ptr2[0].get("overall") == "FAIL"
            other2_ok = (
                "object_exists" in checks2
                and "object_type" in checks2
                and "animation_state" in checks2
                and "material_assignment_presence_check" in checks2
                and "collection_membership" in checks2
            )
            entry_fail_case_passed = gc_fail_ok and overall_fail_ok and other2_ok

        entry_integration_passed = entry_pass_case_passed and entry_fail_case_passed
    except Exception as e:
        entry_integration_passed = False
    finally:
        import shutil
        if tmp_dir is not None:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            tmp_cleaned = not os.path.exists(tmp_dir)
        else:
            tmp_cleaned = True

    # Summary
    all_passed = all(s["passed"] for s in results["scenarios"])
    results["scenario_count"] = len(results["scenarios"])
    results["passed_count"] = sum(1 for s in results["scenarios"] if s["passed"])
    results["failed_count"] = sum(1 for s in results["scenarios"] if not s["passed"])
    results["entry_pass_case_passed"] = entry_pass_case_passed
    results["entry_fail_case_passed"] = entry_fail_case_passed
    results["entry_integration_passed"] = entry_integration_passed
    results["temporary_files_cleaned"] = tmp_cleaned
    results["overall_passed"] = all_passed and entry_integration_passed and tmp_cleaned

    # Single-line compact JSON output
    prefix = "GROUND_CONTACT_BLENDER_VALIDATION_JSON="
    print(prefix + json.dumps(results, ensure_ascii=True, separators=(",", ":")), flush=True)

    if not all_passed or not entry_integration_passed:
        sys.exit(1)


if __name__ == "__main__":
    _run()
