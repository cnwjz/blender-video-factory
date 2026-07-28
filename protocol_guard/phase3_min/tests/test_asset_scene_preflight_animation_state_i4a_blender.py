"""Animation State I4A R3 — Real Blender Runtime PASS/FAIL tests."""

import json, os, subprocess

import pytest

BLENDER_EXE = os.environ.get("BLENDER_EXE", r"D:\Windows software\blender\blender.exe")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
RUNNER = os.path.join(PROJECT_ROOT, "protocol_guard", "phase3_min", "tests",
                      "blender_animation_state_i4a_runner.py")
PHASE3_DIR = os.path.join(PROJECT_ROOT, "protocol_guard", "phase3_min")
PY_SITE = r"C:\Users\Administrator\AppData\Roaming\Python\Python314\site-packages"
EXPECTED_BLENDER = "5.1.2"

EXPECTED_SCENARIOS = [
    # (name, result_dict)
    ("1_animation_data_pass", {
        "animation_object": {"result": "PASS", "object_name": "_I4A_Tmp"},
        "animation_data": {"result": "PASS", "animation_data_present": True},
        "result": "PASS",
    }),
    ("2_animation_data_none_fail", {
        "animation_object": {"result": "PASS", "object_name": "_I4A_TmpNoAD"},
        "animation_data": {"result": "FAIL", "failure_code": "ANIMATION_DATA_NOT_PRESENT"},
        "result": "FAIL",
    }),
    ("3_scenario_a_pass", {
        "animation_object": {"result": "PASS", "object_name": "_I4A_Tmp"},
        "animation_data": {"result": "PASS", "animation_data_present": True},
        "action_name": {"result": "PASS", "action_name": "Walk"},
        "result": "PASS",
    }),
    ("4_scenario_a_dependency", {
        "animation_object": {"result": "PASS", "object_name": "_I4A_TmpNoAD2"},
        "animation_data": {"result": "FAIL", "failure_code": "ANIMATION_DATA_NOT_PRESENT"},
        "action_name": {"result": "NOT_CHECKED", "note": "ANIMATION_DATA_NOT_AVAILABLE"},
        "result": "FAIL",
    }),
    ("5_scenario_b_pass", {
        "animation_object": {"result": "PASS", "object_name": "_I4A_Tmp"},
        "action_name": {"result": "PASS", "action_name": "Walk"},
        "result": "PASS",
    }),
    ("6_scenario_b_missing_data_fail", {
        "animation_object": {"result": "PASS", "object_name": "_I4A_TmpNoAD3"},
        "action_name": {"result": "FAIL", "failure_code": "ACTION_NAME_MISMATCH"},
        "result": "FAIL",
    }),
    ("7_action_none_fail", {
        "animation_object": {"result": "PASS", "object_name": "_I4A_Tmp"},
        "action_name": {"result": "FAIL", "failure_code": "ACTION_NAME_MISMATCH"},
        "result": "FAIL",
    }),
    ("8_action_mismatch_fail", {
        "animation_object": {"result": "PASS", "object_name": "_I4A_Tmp"},
        "action_name": {"result": "FAIL", "failure_code": "ACTION_NAME_MISMATCH"},
        "result": "FAIL",
    }),
    ("9_pose_pass", {
        "animation_object": {"result": "PASS", "object_name": "_I4A_Tmp"},
        "pose_position": {"result": "PASS", "pose_position": "POSE"},
        "result": "PASS",
    }),
    ("10_rest_pass", {
        "animation_object": {"result": "PASS", "object_name": "_I4A_Tmp"},
        "pose_position": {"result": "PASS", "pose_position": "REST"},
        "result": "PASS",
    }),
    ("11_pose_mismatch_fail", {
        "animation_object": {"result": "PASS", "object_name": "_I4A_Tmp"},
        "pose_position": {"result": "FAIL", "failure_code": "POSE_POSITION_MISMATCH"},
        "result": "FAIL",
    }),
    ("12_current_frame_pass", {
        "animation_object": {"result": "PASS", "object_name": "_I4A_Armature"},
        "current_frame": {"result": "PASS", "current_frame": 37},
        "result": "PASS",
    }),
    ("13_combined_all_pass", {
        "animation_object": {"result": "PASS", "object_name": "_I4A_Tmp"},
        "animation_data": {"result": "PASS", "animation_data_present": True},
        "action_name": {"result": "PASS", "action_name": "Walk"},
        "pose_position": {"result": "PASS", "pose_position": "POSE"},
        "current_frame": {"result": "PASS", "current_frame": 42},
        "result": "PASS",
    }),
    ("14_combined_fail_aggregation", {
        "animation_object": {"result": "PASS", "object_name": "_I4A_Tmp"},
        "animation_data": {"result": "PASS", "animation_data_present": True},
        "action_name": {"result": "FAIL", "failure_code": "ACTION_NAME_MISMATCH"},
        "pose_position": {"result": "PASS", "pose_position": "POSE"},
        "current_frame": {"result": "PASS", "current_frame": 42},
        "result": "FAIL",
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
        if "BLENDER_ANIMATION_STATE_I4A_RESULTS_START" in line:
            in_block = True; continue
        if "BLENDER_ANIMATION_STATE_I4A_RESULTS_END" in line: break
        if in_block: buf.append(line)
    return json.loads("\n".join(buf))


@pytest.fixture(scope="module")
def d():
    p = _run(); assert p.returncode == 0, f"Blender exit {p.returncode}\nSTDERR:\n{p.stderr}"
    return p, _parse(p.stdout)


def test_blender_version_and_exit(d):
    assert d[0].returncode == 0
    assert d[1]["BLENDER_VERSION"] == EXPECTED_BLENDER


def test_factory_startup_and_no_blend_args(d):
    p = d[0]
    assert "--factory-startup" in p.args
    assert "--background" in p.args
    for a in p.args:
        assert not a.endswith(".blend"), f".blend arg: {a}"


def test_safety(d):
    s = d[1]["safety"]
    assert s["load_event_count"] == 0; assert s["save_event_count"] == 0
    assert s["render_event_count"] == 0; assert s["filepath_unchanged"] is True
    assert s["handlers_restored"] is True


def test_cleanup(d):
    c = d[1]["cleanup"]
    assert c["our_objects_removed"] is True
    assert c["our_meshes_removed"] is True
    assert c["our_armatures_removed"] is True
    assert c["our_actions_removed"] is True
    assert c["our_scenes_removed"] is True
    assert c["active_scene_restored"] is True
    assert c["pre_state_equals_post_state"] is True
    assert c["original_scene_objects_after"] == c["original_scene_objects_before"]
    assert c["original_scene_objects_restored"] is True


def test_scenario_count(d):
    assert len(d[1]["scenarios"]) == 14


def test_full_scenario_list_exact(d):
    """Full exact assertion over all 14 scenarios — names, wrapper keys, result dicts."""
    actual = d[1]["scenarios"]
    assert len(actual) == 14
    for i, (exp_name, exp_result) in enumerate(EXPECTED_SCENARIOS):
        a = actual[i]
        # Wrapper dict: exactly {"scenario": ..., "result": ...}
        assert set(a.keys()) == {"scenario", "result"}, (
            f"S{i+1}: wrapper keys {set(a.keys())} != {{scenario, result}}")
        assert a["scenario"] == exp_name, (
            f"S{i+1}: expected name '{exp_name}', got '{a['scenario']}'")
        # Result dict: exact equality including object_name
        assert a["result"] == exp_result, (
            f"S{i+1}: result mismatch\nExpected: {exp_result}\nActual:   {a['result']}")


def test_s1(d):  assert d[1]["scenarios"][0]["result"] == EXPECTED_SCENARIOS[0][1]
def test_s2(d):  assert d[1]["scenarios"][1]["result"] == EXPECTED_SCENARIOS[1][1]
def test_s3(d):  assert d[1]["scenarios"][2]["result"] == EXPECTED_SCENARIOS[2][1]
def test_s4(d):  assert d[1]["scenarios"][3]["result"] == EXPECTED_SCENARIOS[3][1]
def test_s5(d):  assert d[1]["scenarios"][4]["result"] == EXPECTED_SCENARIOS[4][1]
def test_s6(d):  assert d[1]["scenarios"][5]["result"] == EXPECTED_SCENARIOS[5][1]
def test_s7(d):  assert d[1]["scenarios"][6]["result"] == EXPECTED_SCENARIOS[6][1]
def test_s8(d):  assert d[1]["scenarios"][7]["result"] == EXPECTED_SCENARIOS[7][1]
def test_s9(d):  assert d[1]["scenarios"][8]["result"] == EXPECTED_SCENARIOS[8][1]
def test_s10(d): assert d[1]["scenarios"][9]["result"] == EXPECTED_SCENARIOS[9][1]
def test_s11(d): assert d[1]["scenarios"][10]["result"] == EXPECTED_SCENARIOS[10][1]
def test_s12(d): assert d[1]["scenarios"][11]["result"] == EXPECTED_SCENARIOS[11][1]
def test_s13(d): assert d[1]["scenarios"][12]["result"] == EXPECTED_SCENARIOS[12][1]
def test_s14(d): assert d[1]["scenarios"][13]["result"] == EXPECTED_SCENARIOS[13][1]
