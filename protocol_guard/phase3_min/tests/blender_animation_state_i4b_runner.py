"""I4B Blender runner 鈥?Runtime ERROR boundary validation."""

import json, sys, os

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path: sys.path.insert(0, _project_root)
_phase3_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _phase3_dir not in sys.path: sys.path.insert(0, _phase3_dir)

import bpy
from blender_scene_reader import _check_animation_state
import protocol_guard.phase3_min.asset_scene_preflight_check as check_mod


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


class _FakeObj:
    """Mutable stand-in for a bpy Object that raises on specific attributes."""
    def __init__(self, name, anim_data=None, data_obj=None, pose_pos=None,
                 raise_anim_data=False, raise_action=False, raise_aname=False,
                 raise_data=False, raise_pp=False):
        self.name = name
        self._anim_data = anim_data
        self._data_obj = data_obj
        self._raise_anim_data = raise_anim_data
        self._raise_action = raise_action
        self._raise_aname = raise_aname
        self._raise_data = raise_data
        self._raise_pp = raise_pp
        self._pose_pos = pose_pos

    @property
    def animation_data(self):
        if self._raise_anim_data: raise RuntimeError("forced ad error")
        return self._anim_data

    @property
    def data(self):
        if self._raise_data: raise RuntimeError("forced data error")
        return self._data_obj

    def __getattr__(self, name):
        if name == "animation_data":
            if self._raise_anim_data: raise RuntimeError("forced ad error")
            return self._anim_data
        if name == "data":
            if self._raise_data: raise RuntimeError("forced data error")
            return self._data_obj
        raise AttributeError(name)


class _FakeAD:
    def __init__(self, action=None, raise_action=False, raise_aname=False):
        self.action = action
        self._raise_action = raise_action

    @property
    def action(self):
        if self._raise_action: raise RuntimeError("forced action ref error")
        return self._action

    @action.setter
    def action(self, v):
        self._action = v


class _FakeAction:
    def __init__(self, name=None, raise_name=False):
        self._name = name
        self._raise_name = raise_name

    @property
    def name(self):
        if self._raise_name: raise RuntimeError("forced action.name error")
        return self._name

    @name.setter
    def name(self, v):
        self._name = v


class _FakeData:
    def __init__(self, pose_position=None, raise_pp=False):
        self._pose_position = pose_position
        self._raise_pp = raise_pp

    @property
    def pose_position(self):
        if self._raise_pp: raise RuntimeError("forced pp error")
        return self._pose_position

    @pose_position.setter
    def pose_position(self, v):
        self._pose_position = v


class _FakeScene:
    def __init__(self, objects=None, frame_current=None, raise_cf=False):
        self.objects = objects if objects is not None else []
        self._frame_current = frame_current
        self._raise_cf = raise_cf

    @property
    def frame_current(self):
        if self._raise_cf: raise RuntimeError("forced cf error")
        return self._frame_current

    @frame_current.setter
    def frame_current(self, v):
        self._frame_current = v


class _RaiseIterObj:
    """Object whose .name raises during iteration."""
    @property
    def name(self):
        raise RuntimeError("forced name error")


def main():
    load_count = [0]; save_count = [0]; render_count = [0]
    def _on_l(*a): load_count[0] += 1
    def _on_s(*a): save_count[0] += 1
    def _on_r(*a): render_count[0] += 1
    handlers_before = (len(bpy.app.handlers.load_post), len(bpy.app.handlers.save_post),
                       len(bpy.app.handlers.render_post))
    bpy.app.handlers.load_post.append(_on_l)
    bpy.app.handlers.save_post.append(_on_s)
    bpy.app.handlers.render_post.append(_on_r)
    fp_before = bpy.data.filepath
    pre_state = _snapshot()

    results = []

    # ===============================================================
    # 1: LOOKUP_ANIMATION_OBJECT 鈥?scene.objects raises on __iter__
    # ===============================================================
    class _RaiseIter:
        def __init__(s): pass
        def __iter__(s): raise RuntimeError("forced lookup error")
    s1 = _FakeScene(_RaiseIter())
    r1 = _check_animation_state(s1, {"animation_state": {"animation_object_name": "X"}})
    results.append({"scenario": "lookup_animation_object_error", "result": r1})

    # ===============================================================
    # 2: AMBIGUOUS_ANIMATION_OBJECT_NAME
    # ===============================================================
    s2 = _FakeScene([_FakeObj("Dup"), _FakeObj("Dup")])
    r2 = _check_animation_state(s2, {"animation_state": {"animation_object_name": "Dup"}})
    results.append({"scenario": "ambiguous_animation_object_name", "result": r2})

    # ===============================================================
    # 3: READ_ANIMATION_OBJECT_NAME 鈥?obj.name raises
    # ===============================================================
    s3 = _FakeScene([_RaiseIterObj()])
    r3 = _check_animation_state(s3, {"animation_state": {"animation_object_name": "X"}})
    results.append({"scenario": "read_animation_object_name_error", "result": r3})

    # ===============================================================
    # 4: Scenario A 鈥?req_ad=true + expected_action_name, ad raises
    # ===============================================================
    a4 = _FakeObj("A4", raise_anim_data=True)
    s4 = _FakeScene([a4])
    r4 = _check_animation_state(s4, {"animation_state": {"animation_object_name":"A4","require_animation_data":True,"expected_action_name":"Walk"}})
    results.append({"scenario": "read_animation_data_error_scenario_a", "result": r4})

    # ===============================================================
    # 5: Scenario B 鈥?req_ad not set, ad raises for action_name
    # ===============================================================
    a5 = _FakeObj("A5", raise_anim_data=True)
    s5 = _FakeScene([a5])
    r5 = _check_animation_state(s5, {"animation_state": {"animation_object_name":"A5","expected_action_name":"Walk"}})
    results.append({"scenario": "read_animation_data_error_scenario_b", "result": r5})

    # ===============================================================
    # 6: READ_ACTION_REFERENCE 鈥?ad.action raises
    # ===============================================================
    ad6 = _FakeAD(raise_action=True)
    a6 = _FakeObj("A6", anim_data=ad6)
    s6 = _FakeScene([a6])
    r6 = _check_animation_state(s6, {"animation_state": {"animation_object_name":"A6","expected_action_name":"Walk"}})
    results.append({"scenario": "read_action_reference_error", "result": r6})

    # ===============================================================
    # 7: READ_ACTION_NAME 鈥?action.name raises
    # ===============================================================
    act7 = _FakeAction(raise_name=True)
    ad7 = _FakeAD(action=act7)
    a7 = _FakeObj("A7", anim_data=ad7)
    s7 = _FakeScene([a7])
    r7 = _check_animation_state(s7, {"animation_state": {"animation_object_name":"A7","expected_action_name":"Walk"}})
    results.append({"scenario": "read_action_name_error", "result": r7})

    # ===============================================================
    # 8: READ_OBJECT_DATA exception 鈥?obj.data raises
    # ===============================================================
    a8 = _FakeObj("A8", raise_data=True)
    s8 = _FakeScene([a8])
    r8 = _check_animation_state(s8, {"animation_state": {"animation_object_name":"A8","expected_pose_position":"POSE"}})
    results.append({"scenario": "read_object_data_exception", "result": r8})

    # ===============================================================
    # 9: READ_OBJECT_DATA 鈥?obj.data is None
    # ===============================================================
    a9 = _FakeObj("A9", data_obj=None)
    s9 = _FakeScene([a9])
    r9 = _check_animation_state(s9, {"animation_state": {"animation_object_name":"A9","expected_pose_position":"POSE"}})
    results.append({"scenario": "read_object_data_none", "result": r9})

    # ===============================================================
    # 10: READ_POSE_POSITION error
    # ===============================================================
    d10 = _FakeData(raise_pp=True)
    a10 = _FakeObj("A10", data_obj=d10)
    s10 = _FakeScene([a10])
    r10 = _check_animation_state(s10, {"animation_state": {"animation_object_name":"A10","expected_pose_position":"POSE"}})
    results.append({"scenario": "read_pose_position_error", "result": r10})

    # ===============================================================
    # 11: READ_CURRENT_FRAME error
    # ===============================================================
    s11 = _FakeScene([_FakeObj("X")], raise_cf=True)
    r11 = _check_animation_state(s11, {"animation_state": {"animation_object_name":"X","record_current_frame":True}})
    results.append({"scenario": "read_current_frame_error", "result": r11})

    # ===============================================================
    # 12: anim_obj ERROR 鈫?dependencies N/C, frame independent
    # ===============================================================
    d12a = _FakeObj("Dup12")
    d12b = _FakeObj("Dup12")
    s12 = _FakeScene([d12a, d12b], frame_current=42)
    r12 = _check_animation_state(s12, {"animation_state": {
        "animation_object_name":"Dup12","require_animation_data":True,
        "expected_action_name":"Walk","expected_pose_position":"POSE",
        "record_current_frame":True}})
    results.append({"scenario": "animation_object_error_dependencies", "result": r12})

    # ===============================================================
    # 13: Three simultaneous ERRORs
    # ===============================================================
    ad13 = _FakeAD(raise_action=True)
    a13 = _FakeObj("A13", raise_anim_data=True, data_obj=None)
    s13 = _FakeScene([a13], raise_cf=True)
    r13 = _check_animation_state(s13, {"animation_state": {
        "animation_object_name":"A13","require_animation_data":True,
        "expected_action_name":"Walk","expected_pose_position":"POSE",
        "record_current_frame":True}})
    results.append({"scenario": "three_simultaneous_errors", "result": r13})

    # ===============================================================
    # 14: _collect_target_errors — full 8-group order test
    # ===============================================================
    per_target = [{
        "target_id": "T14", "root_object_name": "R14",
        "checks": {
            "object_exists": {
                "result": "ERROR", "error_type": "AMBIGUOUS_ROOT_OBJECT_NAME",
                "match_count": 2,
            },
            "direct_children": {
                "result": "ERROR",
                "error_type": "AMBIGUOUS_DIRECT_CHILD_NAME",
                "ambiguous_name_counts": {"C1": 2},
            },
            "descendants": {
                "result": "ERROR",
                "error_type": "AMBIGUOUS_DESCENDANT_NAME",
                "ambiguous_name_counts": {"D1": 2},
            },
            "standing": {
                "result": "ERROR",
                "up_axis": {
                    "result": "ERROR",
                    "error_type": "STANDING_UP_AXIS_ERROR",
                    "operation": "COMPUTE_UP_AXIS_ANGLE",
                },
            },
            "facing": {
                "result": "ERROR",
                "forward_axis": {
                    "result": "ERROR",
                    "error_type": "FACING_FORWARD_AXIS_ERROR",
                    "operation": "COMPUTE_FORWARD_AXIS_ANGLE",
                },
            },
            "visibility": {
                "result": "ERROR",
                "viewport": {
                    "result": "ERROR",
                    "error_type": "VISIBILITY_READ_ERROR",
                    "operation": "READ_ROOT_HIDE_VIEWPORT",
                },
            },
            "rotation": {
                "result": "ERROR",
                "error_type": "ROTATION_COMPUTATION_ERROR",
                "operation": "CONVERT_ROOT_MATRIX_WORLD_TO_QUATERNION",
            },
            "animation_state": {
                "result": "ERROR",
                "animation_object": {
                    "result": "ERROR",
                    "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
                    "operation": "RESOLVE_ANIMATION_OBJECT_NAME",
                    "note": "AMBIGUOUS_ANIMATION_OBJECT_NAME",
                },
                "pose_position": {
                    "result": "ERROR",
                    "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
                    "operation": "READ_OBJECT_DATA",
                    "note": "READ_OBJECT_DATA_FAILED",
                },
                "current_frame": {
                    "result": "ERROR",
                    "error_type": "ANIMATION_STATE_COMPUTATION_ERROR",
                    "operation": "READ_CURRENT_FRAME",
                    "note": "READ_CURRENT_FRAME_FAILED",
                },
            },
        },
        "overall": "ERROR",
    }]
    collected = check_mod._collect_target_errors(per_target)
    results.append({"scenario": "collect_target_errors_order_and_messages",
                    "collected": collected})

    # Remove handlers and verify restoration
    try: bpy.app.handlers.load_post.remove(_on_l)
    except ValueError: pass
    try: bpy.app.handlers.save_post.remove(_on_s)
    except ValueError: pass
    try: bpy.app.handlers.render_post.remove(_on_r)
    except ValueError: pass
    handlers_restored = (_on_l not in bpy.app.handlers.load_post
                         and _on_s not in bpy.app.handlers.save_post
                         and _on_r not in bpy.app.handlers.render_post)

    # Post-state
    post_state = _snapshot()
    active_scene = bpy.context.scene
    post_names = sorted([s.name for s in bpy.data.scenes])

    # Check for our test scenes
    our_scene_remaining = [s for s in post_names if s.startswith("_I4B")]
    our_obj_remaining = [o.name for o in bpy.data.objects if o.name.startswith("_I4B")]
    our_mesh_remaining = [m.name for m in bpy.data.meshes if m.name.startswith("_I4B")]
    our_arm_remaining = [a.name for a in bpy.data.armatures if a.name.startswith("_I4B")]
    our_act_remaining = [ac.name for ac in bpy.data.actions if ac.name.startswith("_I4B")]

    output = {
        "BLENDER_VERSION": bpy.app.version_string,
        "scenarios": results,
        "safety": {
            "load_event_count": load_count[0], "save_event_count": save_count[0],
            "render_event_count": render_count[0],
            "filepath_before": fp_before, "filepath_after": bpy.data.filepath,
            "filepath_unchanged": bpy.data.filepath == fp_before,
            "handlers_restored": handlers_restored,
        },
        "cleanup": {
            "our_objects_removed": len(our_obj_remaining) == 0,
            "our_meshes_removed": len(our_mesh_remaining) == 0,
            "our_armatures_removed": len(our_arm_remaining) == 0,
            "our_actions_removed": len(our_act_remaining) == 0,
            "our_scenes_removed": len(our_scene_remaining) == 0,
            "active_scene_restored": bpy.context.scene.name == pre_state["active_scene_name"],
            "pre_state_equals_post_state": pre_state == post_state,
        },
    }
    print("BLENDER_ANIMATION_STATE_I4B_RESULTS_START")
    print(json.dumps(output, indent=2, default=str))
    print("BLENDER_ANIMATION_STATE_I4B_RESULTS_END")


if __name__ == "__main__":
    main()
