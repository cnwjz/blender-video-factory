"""I3 Blender runner R3 — Object lookup validation for Animation State.

Runs inside Blender 5.1.2 with --background --factory-startup.
Uses app handlers for safety monitoring, creates a separate test scene,
and restores complete pre-test state including handlers.
"""

import json
import sys
import os

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
_phase3_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _phase3_dir not in sys.path:
    sys.path.insert(0, _phase3_dir)

import bpy
from blender_scene_reader import _check_animation_state


def _snapshot():
    return {
        "scene_names": sorted([s.name for s in bpy.data.scenes]),
        "object_names": sorted([o.name for o in bpy.data.objects]),
        "mesh_names": sorted([m.name for m in bpy.data.meshes]),
        "armature_names": sorted([a.name for a in bpy.data.armatures]),
        "active_scene_name": bpy.context.scene.name if bpy.context.scene else None,
        "filepath": bpy.data.filepath,
    }


def main():
    # ---- Safety handlers ----
    load_count = [0]
    save_count = [0]
    render_count = [0]

    def on_load(*args):
        load_count[0] += 1

    def on_save(*args):
        save_count[0] += 1

    def on_render(*args):
        render_count[0] += 1

    bpy.app.handlers.load_post.append(on_load)
    bpy.app.handlers.save_post.append(on_save)
    bpy.app.handlers.render_post.append(on_render)
    filepath_before = bpy.data.filepath

    # ---- Pre-state ----
    pre_state = _snapshot()

    # ---- Remove default Cube (factory startup creates it) ----
    # We'll restore it later
    had_cube = "Cube" in bpy.data.objects

    # ---- Create a separate test scene (don't modify factory-startup scene) ----
    original_scene = bpy.context.scene
    original_scene_objects_before = sorted([o.name for o in original_scene.objects])

    test_scene = bpy.data.scenes.new("_I3_TargetScene")
    other_scene = bpy.data.scenes.new("_I3_OtherScene")

    # Create objects in test scenes
    bpy.context.window.scene = other_scene
    other_mesh_data = bpy.data.meshes.new("_I3_OtherMeshData")
    other_obj = bpy.data.objects.new("_I3_OtherAnimObj", other_mesh_data)
    other_scene.collection.objects.link(other_obj)

    bpy.context.window.scene = test_scene
    root_empty = bpy.data.objects.new("_I3_RootEmpty", None)
    test_scene.collection.objects.link(root_empty)

    arm_data = bpy.data.armatures.new("_I3_ArmData")
    arm_obj = bpy.data.objects.new("_I3_Armature", arm_data)
    test_scene.collection.objects.link(arm_obj)

    mesh_data = bpy.data.meshes.new("_I3_MeshData")
    mesh_obj = bpy.data.objects.new("_I3_AnimMesh", mesh_data)
    test_scene.collection.objects.link(mesh_obj)

    our_objects = {"_I3_RootEmpty", "_I3_Armature", "_I3_AnimMesh", "_I3_OtherAnimObj"}
    our_meshes = {"_I3_MeshData", "_I3_OtherMeshData"}
    our_armatures = {"_I3_ArmData"}
    our_scenes = {"_I3_TargetScene", "_I3_OtherScene"}

    # ---- 6 scenarios ----
    scenarios = [
        ("1_root_object_allowed", test_scene,
         {"animation_state": {"animation_object_name": "_I3_RootEmpty"}}),
        ("2_non_root_non_armature_allowed", test_scene,
         {"animation_state": {"animation_object_name": "_I3_AnimMesh"}}),
        ("3_case_sensitive_mismatch", test_scene,
         {"animation_state": {"animation_object_name": "_i3_animmesh"}}),
        ("4_missing_object", test_scene,
         {"animation_state": {"animation_object_name": "_I3_NonExistent"}}),
        ("5_other_scene_object_from_target", test_scene,
         {"animation_state": {"animation_object_name": "_I3_OtherAnimObj"}}),
        ("6_other_scene_object_from_own_scene", other_scene,
         {"animation_state": {"animation_object_name": "_I3_OtherAnimObj"}}),
    ]
    results = []
    for name, scene, t in scenarios:
        r = _check_animation_state(scene, t)
        results.append({"scenario": name, "result": r})

    # ---- Cleanup: remove all test-created data ----
    # Remove objects from test scene
    for obj_name in list(test_scene.collection.objects.keys()):
        obj = test_scene.collection.objects[obj_name]
        test_scene.collection.objects.unlink(obj)
        if obj.name in our_objects:
            bpy.data.objects.remove(obj)
    for obj_name in list(other_scene.collection.objects.keys()):
        obj = other_scene.collection.objects[obj_name]
        other_scene.collection.objects.unlink(obj)
        if obj.name in our_objects:
            bpy.data.objects.remove(obj)

    # Remove our scenes
    bpy.context.window.scene = original_scene
    bpy.data.scenes.remove(test_scene)
    bpy.data.scenes.remove(other_scene)

    # Remove our data blocks
    for m in list(bpy.data.meshes):
        if m.name in our_meshes:
            bpy.data.meshes.remove(m)
    for a in list(bpy.data.armatures):
        if a.name in our_armatures:
            bpy.data.armatures.remove(a)

    # ---- Remove handlers ----
    try:
        bpy.app.handlers.load_post.remove(on_load)
    except ValueError:
        pass
    try:
        bpy.app.handlers.save_post.remove(on_save)
    except ValueError:
        pass
    try:
        bpy.app.handlers.render_post.remove(on_render)
    except ValueError:
        pass
    handlers_restored = (
        on_load not in bpy.app.handlers.load_post
        and on_save not in bpy.app.handlers.save_post
        and on_render not in bpy.app.handlers.render_post
    )

    # ---- Post-state ----
    original_scene_objects_after = sorted([o.name for o in original_scene.objects])
    post_state = _snapshot()
    pre_equals_post = pre_state == post_state

    remaining_ours = [o.name for o in bpy.data.objects if o.name in our_objects]
    remaining_our_m = [m.name for m in bpy.data.meshes if m.name in our_meshes]
    remaining_our_a = [a.name for a in bpy.data.armatures if a.name in our_armatures]
    remaining_our_s = [s.name for s in bpy.data.scenes if s.name in our_scenes]

    # ---- Output ----
    output = {
        "BLENDER_VERSION": bpy.app.version_string,
        "scenarios": results,
        "safety": {
            "load_event_count": load_count[0],
            "save_event_count": save_count[0],
            "render_event_count": render_count[0],
            "filepath_before": filepath_before,
            "filepath_after": bpy.data.filepath,
            "filepath_unchanged": bpy.data.filepath == filepath_before,
            "handlers_restored": handlers_restored,
        },
        "cleanup": {
            "our_objects_removed": len(remaining_ours) == 0,
            "remaining_our_objects": remaining_ours,
            "our_meshes_removed": len(remaining_our_m) == 0,
            "remaining_our_meshes": remaining_our_m,
            "our_armatures_removed": len(remaining_our_a) == 0,
            "remaining_our_armatures": remaining_our_a,
            "our_scenes_removed": len(remaining_our_s) == 0,
            "remaining_our_scenes": remaining_our_s,
            "original_scene_objects_before": original_scene_objects_before,
            "original_scene_objects_after": original_scene_objects_after,
            "original_scene_objects_restored": original_scene_objects_after == original_scene_objects_before,
            "active_scene_restored": bpy.context.scene == original_scene,
            "pre_state_equals_post_state": pre_equals_post,
        },
    }
    print("BLENDER_ANIMATION_STATE_I3_RESULTS_START")
    print(json.dumps(output, indent=2, default=str))
    print("BLENDER_ANIMATION_STATE_I3_RESULTS_END")


if __name__ == "__main__":
    main()
