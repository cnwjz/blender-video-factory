"""Animation State I3 R3 — Real Blender Object Lookup tests.

Runs blender_animation_state_i3_runner.py inside Blender 5.1.2 subprocess
and validates 6 object lookup scenarios, version, safety, and cleanup.
"""

import json, os, subprocess

import pytest

BLENDER_EXE = os.environ.get("BLENDER_EXE", r"D:\Windows software\blender\blender.exe")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
RUNNER_PATH = os.path.join(PROJECT_ROOT, "protocol_guard", "phase3_min", "tests",
                           "blender_animation_state_i3_runner.py")
PHASE3_DIR = os.path.join(PROJECT_ROOT, "protocol_guard", "phase3_min")
PY_SITE = r"C:\Users\Administrator\AppData\Roaming\Python\Python314\site-packages"
EXPECTED_BLENDER_VERSION = "5.1.2"


def _run_blender():
    cmd = [BLENDER_EXE, "--background", "--factory-startup",
           "--python-use-system-env", "--python", RUNNER_PATH]
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT};{PHASE3_DIR};{PY_SITE}"
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)


def _parse(stdout):
    lines = stdout.split("\n")
    in_block = False; buf = []
    for line in lines:
        if "BLENDER_ANIMATION_STATE_I3_RESULTS_START" in line:
            in_block = True; continue
        if "BLENDER_ANIMATION_STATE_I3_RESULTS_END" in line: break
        if in_block: buf.append(line)
    return json.loads("\n".join(buf))


@pytest.fixture(scope="module")
def i3d():
    p = _run_blender()
    return p, _parse(p.stdout)


def test_blender_exit_zero(i3d):
    p, d = i3d; assert p.returncode == 0


def test_blender_version_exact(i3d):
    p, d = i3d
    assert d["BLENDER_VERSION"] == EXPECTED_BLENDER_VERSION


def test_background_factory_startup(i3d):
    p, d = i3d
    assert "--background" in p.args
    assert "--factory-startup" in p.args


def test_no_blend_arguments(i3d):
    p, d = i3d
    for a in p.args:
        assert not a.endswith(".blend"), f".blend arg: {a}"


def test_safety_events(i3d):
    p, d = i3d
    s = d["safety"]
    assert s["load_event_count"] == 0, f"load_count: {s['load_event_count']}"
    assert s["save_event_count"] == 0, f"save_count: {s['save_event_count']}"
    assert s["render_event_count"] == 0, f"render_count: {s['render_event_count']}"
    assert s["filepath_unchanged"] is True
    assert s["handlers_restored"] is True


# ---------------------------------------------------------------------------
# Scenario assertions
# ---------------------------------------------------------------------------
def test_scenario_count(i3d):
    p, d = i3d; assert len(d["scenarios"]) == 6


def test_s1_root_object(i3d):
    s = i3d[1]["scenarios"][0]
    assert s["scenario"] == "1_root_object_allowed"
    assert s["result"] == {"animation_object": {"result": "PASS", "object_name": "_I3_RootEmpty"}, "result": "PASS"}


def test_s2_non_root_non_armature(i3d):
    s = i3d[1]["scenarios"][1]
    assert s["scenario"] == "2_non_root_non_armature_allowed"
    assert s["result"] == {"animation_object": {"result": "PASS", "object_name": "_I3_AnimMesh"}, "result": "PASS"}


def test_s3_case_sensitive(i3d):
    s = i3d[1]["scenarios"][2]
    assert s["scenario"] == "3_case_sensitive_mismatch"
    assert s["result"] == {"animation_object": {"result": "FAIL", "failure_code": "ANIMATION_OBJECT_NOT_FOUND", "object_name": "_i3_animmesh"}, "result": "FAIL"}


def test_s4_missing(i3d):
    s = i3d[1]["scenarios"][3]
    assert s["scenario"] == "4_missing_object"
    assert s["result"] == {"animation_object": {"result": "FAIL", "failure_code": "ANIMATION_OBJECT_NOT_FOUND", "object_name": "_I3_NonExistent"}, "result": "FAIL"}


def test_s5_other_scene_from_target(i3d):
    s = i3d[1]["scenarios"][4]
    assert s["scenario"] == "5_other_scene_object_from_target"
    assert s["result"] == {"animation_object": {"result": "FAIL", "failure_code": "ANIMATION_OBJECT_NOT_FOUND", "object_name": "_I3_OtherAnimObj"}, "result": "FAIL"}


def test_s6_other_scene_from_own(i3d):
    s = i3d[1]["scenarios"][5]
    assert s["scenario"] == "6_other_scene_object_from_own_scene"
    assert s["result"] == {"animation_object": {"result": "PASS", "object_name": "_I3_OtherAnimObj"}, "result": "PASS"}


# ---------------------------------------------------------------------------
# Cleanup (single test with all structured assertions)
# ---------------------------------------------------------------------------
def test_cleanup_verified(i3d):
    p, d = i3d
    c = d["cleanup"]
    assert c["our_objects_removed"] is True, f"Objects: {c['remaining_our_objects']}"
    assert c["our_meshes_removed"] is True, f"Meshes: {c['remaining_our_meshes']}"
    assert c["our_armatures_removed"] is True, f"Armatures: {c['remaining_our_armatures']}"
    assert c["our_scenes_removed"] is True, f"Scenes: {c['remaining_our_scenes']}"
    assert c["active_scene_restored"] is True
    assert c["pre_state_equals_post_state"] is True
    assert c["original_scene_objects_after"] == c["original_scene_objects_before"]
    assert c["original_scene_objects_restored"] is True
