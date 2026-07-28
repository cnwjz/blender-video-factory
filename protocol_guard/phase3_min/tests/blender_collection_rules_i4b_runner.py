"""Blender runner for Collection Rules I4B R2: 13 real Blender 5.1.2 scenarios.

Usage: blender --background --factory-startup --python-use-system-env --python this_file
"""
import sys, os, json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DEPS = r"C:\Users\Administrator\AppData\Roaming\Python\Python314\site-packages"
sys.path.insert(0, DEPS)
sys.path.insert(0, PROJECT_ROOT)

import bpy
from protocol_guard.phase3_min.blender_scene_reader import (
    _check_collection_rules_global,
    _check_root_objects,
    _check_collection_membership,
    _check_material_assignment,
    _recompute_target_overall,
)


def _clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for col in list(bpy.data.collections):
        if col != bpy.context.scene.collection:
            bpy.data.collections.remove(col)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat)


def _new_collection(name, parent_col=None):
    col = bpy.data.collections.new(name)
    if parent_col is not None:
        parent_col.children.link(col)
    else:
        bpy.context.scene.collection.children.link(col)
    return col


def _new_mesh_object(name, collection=None):
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.active_object
    obj.name = name
    if collection is not None:
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        collection.objects.link(obj)
    return obj


def _new_material(name):
    return bpy.data.materials.new(name=name)


def _run():
    results = {
        "task_id": "COLLECTION_RULES_I4B",
        "blender_version": ".".join(str(x) for x in bpy.app.version[:3]),
        "factory_startup": True,
        "real_project_blend_opened": False,
        "blend_saved": False,
        "render_executed": False,
        "scenario_count": 13,
        "scenarios": [],
    }

    # ── CR-I4B-01: required Collection exists ──
    _clear_scene()
    _new_collection("CHR_TEST")
    actual = _check_collection_rules_global({"required_collection_names": ["CHR_TEST"]})
    expected = {
        "result": "PASS",
        "required": {"result": "PASS", "required_names": ["CHR_TEST"], "missing_names": []},
        "forbidden": {"result": "NOT_CHECKED",
                      "note": "FORBIDDEN_COLLECTION_NAME_PATTERNS_NOT_CONFIGURED"},
    }
    results["scenarios"].append({
        "scenario_id": "CR-I4B-01",
        "description": "required Collection exists -> global PASS",
        "expected": expected, "actual": actual, "passed": actual == expected,
    })

    # ── CR-I4B-02: required Collection missing ──
    _clear_scene()
    actual = _check_collection_rules_global({"required_collection_names": ["NONEXISTENT"]})
    expected = {
        "result": "FAIL", "failure_code": "COLLECTION_RULES_FAILURE",
        "required": {"result": "FAIL", "failure_code": "REQUIRED_COLLECTION_MISSING",
                     "required_names": ["NONEXISTENT"], "missing_names": ["NONEXISTENT"]},
        "forbidden": {"result": "NOT_CHECKED",
                      "note": "FORBIDDEN_COLLECTION_NAME_PATTERNS_NOT_CONFIGURED"},
    }
    results["scenarios"].append({
        "scenario_id": "CR-I4B-02",
        "description": "required Collection missing -> global FAIL",
        "expected": expected, "actual": actual, "passed": actual == expected,
    })

    # ── CR-I4B-03: forbidden pattern match ──
    _clear_scene()
    _new_collection("test_temp")
    actual = _check_collection_rules_global({"forbidden_collection_name_patterns": ["*test*"]})
    expected = {
        "result": "FAIL", "failure_code": "COLLECTION_RULES_FAILURE",
        "required": {"result": "NOT_CHECKED",
                     "note": "REQUIRED_COLLECTION_NAMES_NOT_CONFIGURED"},
        "forbidden": {"result": "FAIL", "failure_code": "FORBIDDEN_COLLECTION_MATCHED",
                      "forbidden_patterns": ["*test*"], "matched_collections": ["test_temp"]},
    }
    results["scenarios"].append({
        "scenario_id": "CR-I4B-03",
        "description": "forbidden pattern matched -> global FAIL",
        "expected": expected, "actual": actual, "passed": actual == expected,
    })

    # ── CR-I4B-04: forbidden no match ──
    _clear_scene()
    _new_collection("CHR_SAFE")
    actual = _check_collection_rules_global({"forbidden_collection_name_patterns": ["*nope*"]})
    expected = {
        "result": "PASS",
        "required": {"result": "NOT_CHECKED",
                     "note": "REQUIRED_COLLECTION_NAMES_NOT_CONFIGURED"},
        "forbidden": {"result": "PASS", "forbidden_patterns": ["*nope*"],
                      "matched_collections": []},
    }
    results["scenarios"].append({
        "scenario_id": "CR-I4B-04",
        "description": "forbidden pattern no match -> global PASS",
        "expected": expected, "actual": actual, "passed": actual == expected,
    })

    # ── CR-I4B-05: empty Collection exists ──
    _clear_scene()
    empty_col = _new_collection("EMPTY_REQUIRED")
    prod_result = _check_collection_rules_global({"required_collection_names": ["EMPTY_REQUIRED"]})
    actual = {"collection_result": prod_result, "collection_object_count": len(empty_col.objects)}
    expected = {
        "collection_result": {
            "result": "PASS",
            "required": {"result": "PASS", "required_names": ["EMPTY_REQUIRED"], "missing_names": []},
            "forbidden": {"result": "NOT_CHECKED",
                          "note": "FORBIDDEN_COLLECTION_NAME_PATTERNS_NOT_CONFIGURED"},
        },
        "collection_object_count": 0,
    }
    results["scenarios"].append({
        "scenario_id": "CR-I4B-05",
        "description": "empty Collection exists -> PASS with object_count=0",
        "expected": expected, "actual": actual, "passed": actual == expected,
    })

    # ── CR-I4B-06: root directly in required Collection ──
    _clear_scene()
    col_a = _new_collection("CHR_A")
    _new_mesh_object("root", collection=col_a)
    target = {"target_id": "T1", "root_object_name": "root", "expected_root_type": "MESH",
              "required_collection_names": ["CHR_A"]}
    ptr = _check_root_objects(bpy.context.scene, [target])[0]
    actual = _check_collection_membership(bpy.context.scene, target, ptr)
    expected = {"result": "PASS", "required_names": ["CHR_A"], "direct_collections": ["CHR_A"],
                "ancestor_collections": [], "matched_names": ["CHR_A"], "missing_names": []}
    results["scenarios"].append({
        "scenario_id": "CR-I4B-06",
        "description": "root directly in required Collection -> PASS",
        "expected": expected, "actual": actual, "passed": actual == expected,
    })

    # ── CR-I4B-07: one-level ancestor ──
    _clear_scene()
    parent = _new_collection("Parent")
    child = _new_collection("CHR_A", parent_col=parent)
    _new_mesh_object("root", collection=child)
    target = {"target_id": "T1", "root_object_name": "root", "expected_root_type": "MESH",
              "required_collection_names": ["Parent"]}
    ptr = _check_root_objects(bpy.context.scene, [target])[0]
    actual = _check_collection_membership(bpy.context.scene, target, ptr)
    expected = {"result": "PASS", "required_names": ["Parent"], "direct_collections": ["CHR_A"],
                "ancestor_collections": ["Parent"], "matched_names": ["Parent"], "missing_names": []}
    results["scenarios"].append({
        "scenario_id": "CR-I4B-07",
        "description": "one-level ancestor -> PASS",
        "expected": expected, "actual": actual, "passed": actual == expected,
    })

    # ── CR-I4B-08: multi-level ancestor ──
    _clear_scene()
    gp = _new_collection("Grandparent")
    p = _new_collection("Parent", parent_col=gp)
    c = _new_collection("CHR_A", parent_col=p)
    _new_mesh_object("root", collection=c)
    target = {"target_id": "T1", "root_object_name": "root", "expected_root_type": "MESH",
              "required_collection_names": ["Grandparent"]}
    ptr = _check_root_objects(bpy.context.scene, [target])[0]
    actual = _check_collection_membership(bpy.context.scene, target, ptr)
    expected = {"result": "PASS", "required_names": ["Grandparent"],
                "direct_collections": ["CHR_A"],
                "ancestor_collections": ["Grandparent", "Parent"],
                "matched_names": ["Grandparent"], "missing_names": []}
    results["scenarios"].append({
        "scenario_id": "CR-I4B-08",
        "description": "multi-level ancestor -> PASS",
        "expected": expected, "actual": actual, "passed": actual == expected,
    })

    # ── CR-I4B-09: root in multiple direct Collections ──
    _clear_scene()
    col1 = _new_collection("CHR_A")
    col2 = _new_collection("Other")
    root_obj = _new_mesh_object("root", collection=col1)
    col2.objects.link(root_obj)
    target = {"target_id": "T1", "root_object_name": "root", "expected_root_type": "MESH",
              "required_collection_names": ["CHR_A"]}
    ptr = _check_root_objects(bpy.context.scene, [target])[0]
    actual = _check_collection_membership(bpy.context.scene, target, ptr)
    expected = {"result": "PASS", "required_names": ["CHR_A"],
                "direct_collections": ["CHR_A", "Other"], "ancestor_collections": [],
                "matched_names": ["CHR_A"], "missing_names": []}
    results["scenarios"].append({
        "scenario_id": "CR-I4B-09",
        "description": "root in multiple direct Collections -> PASS",
        "expected": expected, "actual": actual, "passed": actual == expected,
    })

    # ── CR-I4B-10: root not in any required Collection ──
    _clear_scene()
    other = _new_collection("Other")
    _new_mesh_object("root", collection=other)
    target = {"target_id": "T1", "root_object_name": "root", "expected_root_type": "MESH",
              "required_collection_names": ["CHR_A", "CHR_B"]}
    ptr = _check_root_objects(bpy.context.scene, [target])[0]
    actual = _check_collection_membership(bpy.context.scene, target, ptr)
    expected = {"result": "FAIL", "failure_code": "TARGET_NOT_IN_REQUIRED_COLLECTION",
                "required_names": ["CHR_A", "CHR_B"], "direct_collections": ["Other"],
                "ancestor_collections": [], "matched_names": [],
                "missing_names": ["CHR_A", "CHR_B"]}
    results["scenarios"].append({
        "scenario_id": "CR-I4B-10",
        "description": "root not in required -> FAIL",
        "expected": expected, "actual": actual, "passed": actual == expected,
    })

    # ── CR-I4B-11: global + per-target coexistence ──
    _clear_scene()
    _new_collection("GLOBAL_OK")
    chr_a = _new_collection("CHR_A")
    _new_mesh_object("root", collection=chr_a)
    global_r = _check_collection_rules_global({"required_collection_names": ["GLOBAL_OK"]})
    target = {"target_id": "T1", "root_object_name": "root", "expected_root_type": "MESH",
              "required_collection_names": ["CHR_A"]}
    ptr = _check_root_objects(bpy.context.scene, [target])[0]
    per_t = _check_collection_membership(bpy.context.scene, target, ptr)
    actual = {"global": global_r, "per_target": per_t}
    expected = {
        "global": {"result": "PASS",
                   "required": {"result": "PASS", "required_names": ["GLOBAL_OK"], "missing_names": []},
                   "forbidden": {"result": "NOT_CHECKED",
                                 "note": "FORBIDDEN_COLLECTION_NAME_PATTERNS_NOT_CONFIGURED"}},
        "per_target": {"result": "PASS", "required_names": ["CHR_A"],
                       "direct_collections": ["CHR_A"], "ancestor_collections": [],
                       "matched_names": ["CHR_A"], "missing_names": []},
    }
    results["scenarios"].append({
        "scenario_id": "CR-I4B-11",
        "description": "global + per-target coexist -> both PASS",
        "expected": expected, "actual": actual, "passed": actual == expected,
    })

    # ── CR-I4B-12: Collection Rules + Material Assignment ──
    _clear_scene()
    mat = _new_material("test_mat")
    chr_a = _new_collection("CHR_A")
    root_obj = _new_mesh_object("root", collection=chr_a)
    root_obj.data.materials.append(mat)
    target_full = {"target_id": "T1", "root_object_name": "root", "expected_root_type": "MESH",
                   "required_collection_names": ["CHR_A"], "geometry_scope": "SELF_MESH",
                   "material_assignment": {"require_material_assignment_presence": True}}
    root_res = _check_root_objects(bpy.context.scene, [target_full])[0]
    ma_r = _check_material_assignment(bpy.context.scene, target_full, root_res)
    cr_r = _check_collection_membership(bpy.context.scene, target_full, root_res)
    checks = {"material_assignment_presence_check": ma_r, "collection_membership": cr_r}
    overall = _recompute_target_overall(checks)
    actual = {"ma": ma_r["result"], "cr": cr_r["result"], "overall": overall}
    expected = {"ma": "PASS", "cr": "PASS", "overall": "PASS"}
    results["scenarios"].append({
        "scenario_id": "CR-I4B-12",
        "description": "Collection Rules + Material Assignment -> both PASS",
        "expected": expected, "actual": actual, "passed": actual == expected,
    })

    # ── CR-I4B-13: multi-parent ancestor closure ──
    _clear_scene()
    parent_a = _new_collection("ParentA")
    parent_b = _new_collection("ParentB")
    shared = _new_collection("Shared", parent_col=parent_a)
    parent_b.children.link(shared)
    _new_mesh_object("root", collection=shared)
    pc = 0
    for c in bpy.data.collections:
        if c != bpy.context.scene.collection and shared in list(c.children):
            pc += 1
    target = {"target_id": "T1", "root_object_name": "root", "expected_root_type": "MESH",
              "required_collection_names": ["ParentA"]}
    ptr = _check_root_objects(bpy.context.scene, [target])[0]
    membership = _check_collection_membership(bpy.context.scene, target, ptr)
    actual = {"membership": membership, "shared_parent_count": pc}
    expected = {
        "membership": {"result": "PASS", "required_names": ["ParentA"],
                       "direct_collections": ["Shared"],
                       "ancestor_collections": ["ParentA", "ParentB"],
                       "matched_names": ["ParentA"], "missing_names": []},
        "shared_parent_count": 2,
    }
    results["scenarios"].append({
        "scenario_id": "CR-I4B-13",
        "description": "multi-parent ancestor closure -> PASS",
        "expected": expected, "actual": actual, "passed": actual == expected,
    })

    # ── Final cleanup check ──
    _clear_scene()
    results["cleanup"] = {
        "objects": len(bpy.data.objects),
        "collections": sum(1 for _ in bpy.data.collections if _ != bpy.context.scene.collection),
        "meshes": len(bpy.data.meshes),
        "materials": len(bpy.data.materials),
    }

    results["overall_passed"] = all(s["passed"] for s in results["scenarios"])

    print("COLLECTION_RULES_I4B_JSON_BEGIN")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    print("COLLECTION_RULES_I4B_JSON_END")


if __name__ == "__main__":
    _run()
