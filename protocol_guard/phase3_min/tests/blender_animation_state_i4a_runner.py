"""I4A Blender runner — Runtime PASS/FAIL validation for Animation State.

Runs inside Blender 5.1.2 with --background --factory-startup.
Creates test Scene/Armature/Action, calls _check_animation_state for 14 scenarios.
"""

import json, sys, os

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path: sys.path.insert(0, _project_root)
_phase3_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _phase3_dir not in sys.path: sys.path.insert(0, _phase3_dir)

import bpy
from blender_scene_reader import _check_animation_state


def _snapshot():
    return {
        "scene_names": sorted([s.name for s in bpy.data.scenes]),
        "object_names": sorted([o.name for o in bpy.data.objects]),
        "mesh_names": sorted([m.name for m in bpy.data.meshes]),
        "armature_names": sorted([a.name for a in bpy.data.armatures]),
        "action_names": sorted([ac.name for ac in bpy.data.actions]),
        "active_scene_name": bpy.context.scene.name if bpy.context.scene else None,
        "filepath": bpy.data.filepath,
    }


def main():
    # Safety tracking
    load_count = [0]; save_count = [0]; render_count = [0]
    def on_load(*a): load_count[0] += 1
    def on_save(*a): save_count[0] += 1
    def on_render(*a): render_count[0] += 1
    bpy.app.handlers.load_post.append(on_load)
    bpy.app.handlers.save_post.append(on_save)
    bpy.app.handlers.render_post.append(on_render)
    fp_before = bpy.data.filepath

    pre_state = _snapshot()
    original_scene = bpy.context.scene
    original_scene_objects_before = sorted([o.name for o in original_scene.objects])

    # Create test scene
    test_scene = bpy.data.scenes.new("_I4A_Scene")
    bpy.context.window.scene = test_scene

    # Create Armature object
    arm_data = bpy.data.armatures.new("_I4A_ArmData")
    arm_obj = bpy.data.objects.new("_I4A_Armature", arm_data)
    test_scene.collection.objects.link(arm_obj)

    # Create action for matching
    action_walk = bpy.data.actions.new("Walk")
    action_run = bpy.data.actions.new("Run")

    our_objects = {"_I4A_Armature"}
    our_meshes = set()
    our_armatures = {"_I4A_ArmData"}
    our_actions = {"Walk", "Run"}
    our_scenes = {"_I4A_Scene"}

    results = []

    # ---------------------------------------------------------------
    # Helper: Armature with AnimData
    # ---------------------------------------------------------------
    def make_arm_with_anim(action=None):
        a = bpy.data.objects.new("_I4A_Tmp", bpy.data.armatures.new("_I4A_TmpData"))
        test_scene.collection.objects.link(a)
        if not a.animation_data:
            a.animation_data_create()
        if action:
            a.animation_data.action = action
        return a

    def cleanup_tmp():
        for o in list(test_scene.collection.objects):
            if o.name.startswith("_I4A_Tmp"):
                test_scene.collection.objects.unlink(o)
                bpy.data.objects.remove(o)
        for a in list(bpy.data.armatures):
            if a.name.startswith("_I4A_Tmp"):
                bpy.data.armatures.remove(a)

    # ===============================================================
    # 1: require_animation_data=true, AnimData present → PASS
    # ===============================================================
    a1 = make_arm_with_anim(action_walk)
    r1 = _check_animation_state(test_scene, {"animation_state": {
        "animation_object_name": a1.name, "require_animation_data": True}})
    results.append({"scenario": "1_animation_data_pass", "result": r1})
    cleanup_tmp()

    # ===============================================================
    # 2: require_animation_data=true, AnimData None → FAIL
    # ===============================================================
    a2 = bpy.data.objects.new("_I4A_TmpNoAD", bpy.data.armatures.new("_I4A_TmpNoADData"))
    test_scene.collection.objects.link(a2)
    r2 = _check_animation_state(test_scene, {"animation_state": {
        "animation_object_name": a2.name, "require_animation_data": True}})
    results.append({"scenario": "2_animation_data_none_fail", "result": r2})
    cleanup_tmp()

    # ===============================================================
    # 3: Scenario A: req_ad=true, action name matches → PASS
    # ===============================================================
    a3 = make_arm_with_anim(action_walk)
    r3 = _check_animation_state(test_scene, {"animation_state": {
        "animation_object_name": a3.name, "require_animation_data": True,
        "expected_action_name": "Walk"}})
    results.append({"scenario": "3_scenario_a_pass", "result": r3})
    cleanup_tmp()

    # ===============================================================
    # 4: Scenario A: req_ad=true, AnimData None → anim_data FAIL, action_name N/C
    # ===============================================================
    a4 = bpy.data.objects.new("_I4A_TmpNoAD2", bpy.data.armatures.new("_I4A_TmpNoADData2"))
    test_scene.collection.objects.link(a4)
    r4 = _check_animation_state(test_scene, {"animation_state": {
        "animation_object_name": a4.name, "require_animation_data": True,
        "expected_action_name": "Walk"}})
    results.append({"scenario": "4_scenario_a_dependency", "result": r4})
    cleanup_tmp()

    # ===============================================================
    # 5: Scenario B: req_ad=false, action match → PASS
    # ===============================================================
    a5 = make_arm_with_anim(action_walk)
    r5 = _check_animation_state(test_scene, {"animation_state": {
        "animation_object_name": a5.name, "require_animation_data": False,
        "expected_action_name": "Walk"}})
    results.append({"scenario": "5_scenario_b_pass", "result": r5})
    cleanup_tmp()

    # ===============================================================
    # 6: Scenario B: req_ad=false, AnimData None → action_name FAIL
    # ===============================================================
    a6 = bpy.data.objects.new("_I4A_TmpNoAD3", bpy.data.armatures.new("_I4A_TmpNoADData3"))
    test_scene.collection.objects.link(a6)
    r6 = _check_animation_state(test_scene, {"animation_state": {
        "animation_object_name": a6.name, "require_animation_data": False,
        "expected_action_name": "Walk"}})
    results.append({"scenario": "6_scenario_b_missing_data_fail", "result": r6})
    cleanup_tmp()

    # ===============================================================
    # 7: AnimData present, action is None → FAIL
    # ===============================================================
    a7 = make_arm_with_anim(action=None)
    r7 = _check_animation_state(test_scene, {"animation_state": {
        "animation_object_name": a7.name, "expected_action_name": "Walk"}})
    results.append({"scenario": "7_action_none_fail", "result": r7})
    cleanup_tmp()

    # ===============================================================
    # 8: Action name mismatch → FAIL
    # ===============================================================
    a8 = make_arm_with_anim(action_run)
    r8 = _check_animation_state(test_scene, {"animation_state": {
        "animation_object_name": a8.name, "expected_action_name": "Walk"}})
    results.append({"scenario": "8_action_mismatch_fail", "result": r8})
    cleanup_tmp()

    # ===============================================================
    # 9: expected_pose_position POSE, actual POSE → PASS
    # ===============================================================
    a9 = make_arm_with_anim(action_walk)
    a9.data.pose_position = "POSE"
    r9 = _check_animation_state(test_scene, {"animation_state": {
        "animation_object_name": a9.name, "expected_pose_position": "POSE"}})
    results.append({"scenario": "9_pose_pass", "result": r9})
    cleanup_tmp()

    # ===============================================================
    # 10: expected_pose_position REST, actual REST → PASS
    # ===============================================================
    a10 = make_arm_with_anim(action_walk)
    a10.data.pose_position = "REST"
    r10 = _check_animation_state(test_scene, {"animation_state": {
        "animation_object_name": a10.name, "expected_pose_position": "REST"}})
    results.append({"scenario": "10_rest_pass", "result": r10})
    cleanup_tmp()

    # ===============================================================
    # 11: expected_pose_position POSE, actual REST → FAIL
    # ===============================================================
    a11 = make_arm_with_anim(action_walk)
    a11.data.pose_position = "REST"
    r11 = _check_animation_state(test_scene, {"animation_state": {
        "animation_object_name": a11.name, "expected_pose_position": "POSE"}})
    results.append({"scenario": "11_pose_mismatch_fail", "result": r11})
    cleanup_tmp()

    # ===============================================================
    # 12: record_current_frame=true, frame=37 → PASS
    # ===============================================================
    test_scene.frame_current = 37
    r12 = _check_animation_state(test_scene, {"animation_state": {
        "animation_object_name": arm_obj.name, "record_current_frame": True}})
    results.append({"scenario": "12_current_frame_pass", "result": r12})

    # ===============================================================
    # 13: All PASS combined
    # ===============================================================
    a13 = make_arm_with_anim(action_walk)
    a13.data.pose_position = "POSE"
    test_scene.frame_current = 42
    r13 = _check_animation_state(test_scene, {"animation_state": {
        "animation_object_name": a13.name, "require_animation_data": True,
        "expected_action_name": "Walk", "expected_pose_position": "POSE",
        "record_current_frame": True}})
    results.append({"scenario": "13_combined_all_pass", "result": r13})
    cleanup_tmp()

    # ===============================================================
    # 14: Combined with action mismatch → FAIL
    # ===============================================================
    a14 = make_arm_with_anim(action_run)
    a14.data.pose_position = "POSE"
    test_scene.frame_current = 42
    r14 = _check_animation_state(test_scene, {"animation_state": {
        "animation_object_name": a14.name, "require_animation_data": True,
        "expected_action_name": "Walk", "expected_pose_position": "POSE",
        "record_current_frame": True}})
    results.append({"scenario": "14_combined_fail_aggregation", "result": r14})
    cleanup_tmp()

    # ===============================================================
    # Cleanup
    # ===============================================================
    bpy.context.window.scene = test_scene
    for o in list(test_scene.collection.objects):
        test_scene.collection.objects.unlink(o)
        bpy.data.objects.remove(o)
    bpy.context.window.scene = original_scene
    bpy.data.scenes.remove(test_scene)
    for m in list(bpy.data.meshes):
        if m.name in our_meshes: bpy.data.meshes.remove(m)
    for a in list(bpy.data.armatures):
        if a.name in our_armatures or a.name.startswith("_I4A_Tmp"):
            bpy.data.armatures.remove(a)
    for ac in list(bpy.data.actions):
        if ac.name in our_actions: bpy.data.actions.remove(ac)

    # Remove handlers
    try: bpy.app.handlers.load_post.remove(on_load)
    except ValueError: pass
    try: bpy.app.handlers.save_post.remove(on_save)
    except ValueError: pass
    try: bpy.app.handlers.render_post.remove(on_render)
    except ValueError: pass

    original_scene_objects_after = sorted([o.name for o in original_scene.objects])
    post_state = _snapshot()
    remaining_o = [o for o in bpy.data.objects if o.name.startswith("_I4A")]
    remaining_m = [m for m in bpy.data.meshes if m.name.startswith("_I4A")]
    remaining_a = [a for a in bpy.data.armatures if a.name.startswith("_I4A")]
    remaining_ac = [ac for ac in bpy.data.actions if ac.name in our_actions]
    remaining_s = [s for s in bpy.data.scenes if s.name.startswith("_I4A")]

    output = {
        "BLENDER_VERSION": bpy.app.version_string,
        "scenarios": results,
        "safety": {
            "load_event_count": load_count[0],
            "save_event_count": save_count[0],
            "render_event_count": render_count[0],
            "filepath_before": fp_before,
            "filepath_after": bpy.data.filepath,
            "filepath_unchanged": bpy.data.filepath == fp_before,
            "handlers_restored": (on_load not in bpy.app.handlers.load_post
                                  and on_save not in bpy.app.handlers.save_post
                                  and on_render not in bpy.app.handlers.render_post),
        },
        "cleanup": {
            "our_objects_removed": len(remaining_o) == 0,
            "our_meshes_removed": len(remaining_m) == 0,
            "our_armatures_removed": len(remaining_a) == 0,
            "our_actions_removed": len(remaining_ac) == 0,
            "our_scenes_removed": len(remaining_s) == 0,
            "original_scene_objects_before": original_scene_objects_before,
            "original_scene_objects_after": original_scene_objects_after,
            "original_scene_objects_restored": original_scene_objects_after == original_scene_objects_before,
            "active_scene_restored": bpy.context.scene == original_scene,
            "pre_state_equals_post_state": pre_state == post_state,
        },
    }
    print("BLENDER_ANIMATION_STATE_I4A_RESULTS_START")
    print(json.dumps(output, indent=2, default=str))
    print("BLENDER_ANIMATION_STATE_I4A_RESULTS_END")


if __name__ == "__main__":
    main()
