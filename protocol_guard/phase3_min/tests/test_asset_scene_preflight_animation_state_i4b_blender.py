"""Animation State I4B R2 — Real Blender Runtime ERROR boundary tests."""

import json, os, subprocess

import pytest

BLENDER_EXE = os.environ.get("BLENDER_EXE", r"D:\Windows software\blender\blender.exe")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
RUNNER = os.path.join(PROJECT_ROOT, "protocol_guard", "phase3_min", "tests",
                      "blender_animation_state_i4b_runner.py")
PHASE3_DIR = os.path.join(PROJECT_ROOT, "protocol_guard", "phase3_min")
PY_SITE = r"C:\Users\Administrator\AppData\Roaming\Python\Python314\site-packages"

EXPECTED = [
    # 1: LOOKUP_ANIMATION_OBJECT error
    ("lookup_animation_object_error", {
        "animation_object": {"result":"ERROR","error_type":"ANIMATION_STATE_COMPUTATION_ERROR","operation":"LOOKUP_ANIMATION_OBJECT","note":"LOOKUP_ANIMATION_OBJECT_FAILED"},
        "result":"ERROR",
    }),
    # 2: Ambiguous name
    ("ambiguous_animation_object_name", {
        "animation_object": {"result":"ERROR","error_type":"ANIMATION_STATE_COMPUTATION_ERROR","operation":"RESOLVE_ANIMATION_OBJECT_NAME","note":"AMBIGUOUS_ANIMATION_OBJECT_NAME"},
        "result":"ERROR",
    }),
    # 3: READ_ANIMATION_OBJECT_NAME
    ("read_animation_object_name_error", {
        "animation_object": {"result":"ERROR","error_type":"ANIMATION_STATE_COMPUTATION_ERROR","operation":"READ_ANIMATION_OBJECT_NAME","note":"READ_ANIMATION_OBJECT_NAME_FAILED"},
        "result":"ERROR",
    }),
    # 4: Scenario A — req_ad=true + ean set, ad raises → anim_data ERROR, action_name NOT_CHECKED
    ("read_animation_data_error_scenario_a", {
        "animation_object": {"result":"PASS","object_name":"A4"},
        "animation_data": {"result":"ERROR","error_type":"ANIMATION_STATE_COMPUTATION_ERROR","operation":"READ_ANIMATION_DATA","note":"READ_ANIMATION_DATA_FAILED"},
        "action_name": {"result":"NOT_CHECKED","note":"ANIMATION_DATA_NOT_AVAILABLE"},
        "result":"ERROR",
    }),
    # 5: Scenario B — req_ad not set, ad raises → action_name ERROR (READ_ANIMATION_DATA)
    ("read_animation_data_error_scenario_b", {
        "animation_object": {"result":"PASS","object_name":"A5"},
        "action_name": {"result":"ERROR","error_type":"ANIMATION_STATE_COMPUTATION_ERROR","operation":"READ_ANIMATION_DATA","note":"READ_ANIMATION_DATA_FAILED"},
        "result":"ERROR",
    }),
    # 6: READ_ACTION_REFERENCE
    ("read_action_reference_error", {
        "animation_object": {"result":"PASS","object_name":"A6"},
        "action_name": {"result":"ERROR","error_type":"ANIMATION_STATE_COMPUTATION_ERROR","operation":"READ_ACTION_REFERENCE","note":"READ_ACTION_REFERENCE_FAILED"},
        "result":"ERROR",
    }),
    # 7: READ_ACTION_NAME
    ("read_action_name_error", {
        "animation_object": {"result":"PASS","object_name":"A7"},
        "action_name": {"result":"ERROR","error_type":"ANIMATION_STATE_COMPUTATION_ERROR","operation":"READ_ACTION_NAME","note":"READ_ACTION_NAME_FAILED"},
        "result":"ERROR",
    }),
    # 8: READ_OBJECT_DATA exception
    ("read_object_data_exception", {
        "animation_object": {"result":"PASS","object_name":"A8"},
        "pose_position": {"result":"ERROR","error_type":"ANIMATION_STATE_COMPUTATION_ERROR","operation":"READ_OBJECT_DATA","note":"READ_OBJECT_DATA_FAILED"},
        "result":"ERROR",
    }),
    # 9: obj.data is None → READ_OBJECT_DATA_FAILED
    ("read_object_data_none", {
        "animation_object": {"result":"PASS","object_name":"A9"},
        "pose_position": {"result":"ERROR","error_type":"ANIMATION_STATE_COMPUTATION_ERROR","operation":"READ_OBJECT_DATA","note":"READ_OBJECT_DATA_FAILED"},
        "result":"ERROR",
    }),
    # 10: READ_POSE_POSITION
    ("read_pose_position_error", {
        "animation_object": {"result":"PASS","object_name":"A10"},
        "pose_position": {"result":"ERROR","error_type":"ANIMATION_STATE_COMPUTATION_ERROR","operation":"READ_POSE_POSITION","note":"READ_POSE_POSITION_FAILED"},
        "result":"ERROR",
    }),
    # 11: READ_CURRENT_FRAME
    ("read_current_frame_error", {
        "animation_object": {"result":"PASS","object_name":"X"},
        "current_frame": {"result":"ERROR","error_type":"ANIMATION_STATE_COMPUTATION_ERROR","operation":"READ_CURRENT_FRAME","note":"READ_CURRENT_FRAME_FAILED"},
        "result":"ERROR",
    }),
    # 12: anim_obj ERROR → dependencies N/C, frame independent
    ("animation_object_error_dependencies", {
        "animation_object": {"result":"ERROR","error_type":"ANIMATION_STATE_COMPUTATION_ERROR","operation":"RESOLVE_ANIMATION_OBJECT_NAME","note":"AMBIGUOUS_ANIMATION_OBJECT_NAME"},
        "animation_data": {"result":"NOT_CHECKED","note":"ANIMATION_OBJECT_UNAVAILABLE"},
        "action_name": {"result":"NOT_CHECKED","note":"ANIMATION_OBJECT_UNAVAILABLE"},
        "pose_position": {"result":"NOT_CHECKED","note":"ANIMATION_OBJECT_UNAVAILABLE"},
        "current_frame": {"result":"PASS","current_frame":42},
        "result":"ERROR",
    }),
    # 13: Three simultaneous ERRORs
    ("three_simultaneous_errors", {
        "animation_object": {"result":"PASS","object_name":"A13"},
        "animation_data": {"result":"ERROR","error_type":"ANIMATION_STATE_COMPUTATION_ERROR","operation":"READ_ANIMATION_DATA","note":"READ_ANIMATION_DATA_FAILED"},
        "action_name": {"result":"NOT_CHECKED","note":"ANIMATION_DATA_NOT_AVAILABLE"},
        "pose_position": {"result":"ERROR","error_type":"ANIMATION_STATE_COMPUTATION_ERROR","operation":"READ_OBJECT_DATA","note":"READ_OBJECT_DATA_FAILED"},
        "current_frame": {"result":"ERROR","error_type":"ANIMATION_STATE_COMPUTATION_ERROR","operation":"READ_CURRENT_FRAME","note":"READ_CURRENT_FRAME_FAILED"},
        "result":"ERROR",
    }),
]


def _run():
    cmd = [BLENDER_EXE, "--background", "--factory-startup",
           "--python-use-system-env", "--python", RUNNER]
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT};{PHASE3_DIR};{PY_SITE}"
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)


def _parse(stdout):
    lines = stdout.split("\n"); in_block = False; buf = []
    for line in lines:
        if "BLENDER_ANIMATION_STATE_I4B_RESULTS_START" in line:
            in_block = True; continue
        if "BLENDER_ANIMATION_STATE_I4B_RESULTS_END" in line: break
        if in_block: buf.append(line)
    return json.loads("\n".join(buf))


@pytest.fixture(scope="module")
def d():
    p = _run(); data = _parse(p.stdout)
    assert p.returncode == 0, f"Exit {p.returncode}\nSTDERR:\n{p.stderr}"
    assert len(data["scenarios"]) == 14
    return p, data


def test_exit_zero(d): assert d[0].returncode == 0
def test_blender_version(d): assert d[1]["BLENDER_VERSION"] == "5.1.2"

def test_factory_startup_and_safety(d):
    p = d[0]
    assert "--factory-startup" in p.args; assert "--background" in p.args
    for a in p.args: assert not a.endswith(".blend")
    s = d[1]["safety"]
    assert s["load_event_count"] == 0; assert s["save_event_count"] == 0
    assert s["render_event_count"] == 0; assert s["filepath_unchanged"] is True
    assert s["handlers_restored"] is True

def test_cleanup(d):
    c = d[1]["cleanup"]
    assert c["our_objects_removed"] is True; assert c["our_meshes_removed"] is True
    assert c["our_armatures_removed"] is True; assert c["our_actions_removed"] is True
    assert c["our_scenes_removed"] is True
    assert c["active_scene_restored"] is True
    assert c["pre_state_equals_post_state"] is True


# Full exact assertion: names and full dicts for first 13 scenarios
def test_scenario_names_and_order(d):
    names = [s["scenario"] for s in d[1]["scenarios"]]
    assert names == [e[0] for e in EXPECTED] + ["collect_target_errors_order_and_messages"]

@pytest.mark.parametrize("i,exp_name,exp_result", [(i, *e) for i, e in enumerate(EXPECTED)])
def test_scenario_exact(i, exp_name, exp_result, d):
    s = d[1]["scenarios"][i]
    assert set(s.keys()) == {"scenario", "result"}, f"S{i}: wrapper keys {set(s.keys())}"
    assert s["scenario"] == exp_name
    assert s["result"] == exp_result, f"S{i} {exp_name}:\nExpected: {exp_result}\nActual:   {s['result']}"


# 14: _collect_target_errors — 8-group order + full messages
EXPECTED_COLLECTED = [
    "AMBIGUOUS_ROOT_OBJECT_NAME: target 'T14' root_object_name 'R14' has 2 matches",
    "AMBIGUOUS_DIRECT_CHILD_NAME: target 'T14' root_object_name 'R14' direct child name 'C1' has 2 matches",
    "AMBIGUOUS_DESCENDANT_NAME: target 'T14' root_object_name 'R14' descendant name 'D1' has 2 matches",
    "STANDING_UP_AXIS_ERROR: target 'T14' root_object_name 'R14' operation 'COMPUTE_UP_AXIS_ANGLE'",
    "FACING_FORWARD_AXIS_ERROR: target 'T14' root_object_name 'R14' operation 'COMPUTE_FORWARD_AXIS_ANGLE'",
    "VISIBILITY_READ_ERROR: target 'T14' root_object_name 'R14' operation 'READ_ROOT_HIDE_VIEWPORT'",
    "ROTATION_COMPUTATION_ERROR: target 'T14' root_object_name 'R14' operation 'CONVERT_ROOT_MATRIX_WORLD_TO_QUATERNION'",
    "ANIMATION_STATE_COMPUTATION_ERROR: target 'T14' animation_state operation 'RESOLVE_ANIMATION_OBJECT_NAME'",
    "ANIMATION_STATE_COMPUTATION_ERROR: target 'T14' animation_state operation 'READ_OBJECT_DATA'",
    "ANIMATION_STATE_COMPUTATION_ERROR: target 'T14' animation_state operation 'READ_CURRENT_FRAME'",
]

def test_collect_errors(d):
    s = d[1]["scenarios"][13]
    assert s["scenario"] == "collect_target_errors_order_and_messages"
    assert set(s.keys()) == {"scenario", "collected"}
    c = s["collected"]
    assert c == EXPECTED_COLLECTED, (
        f"Mismatch in collected messages.\nExpected ({len(EXPECTED_COLLECTED)}):\n{EXPECTED_COLLECTED}\n"
        f"Actual ({len(c)}):\n{c}")
