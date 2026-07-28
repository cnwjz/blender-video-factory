"""Animation State I2 — Configuration semantics CPython tests (R2).

Tests MODEL_A sub-key rules, configuration semantics, aggregation,
dependency NOT_CHECKED cascade, read counts, integration control flow,
and overall matrix using fake Python objects (no Blender required).
"""

import pytest


class FakeAction:
    def __init__(self, name):
        self.name = name


class FakeAnimData:
    def __init__(self, action=None):
        self.action = action


class FakePoseData:
    def __init__(self, pose_position):
        self.pose_position = pose_position


class FakeObj:
    def __init__(self, name, anim_data=None, data=None):
        self.name = name
        self.animation_data = anim_data
        self.data = data


class FakeScene:
    def __init__(self, objects=None, frame_current=1):
        self.objects = objects if objects is not None else []
        self.frame_current = frame_current


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_target(animation_state):
    return {"target_id": "A", "root_object_name": "r",
            "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
            "animation_state": animation_state}


def _make_scene(obj_name="Armature", anim_data=None, data=None, frame=1):
    obj = FakeObj(obj_name, anim_data, data)
    return FakeScene([obj], frame)


def _check(target, scene):
    from protocol_guard.phase3_min.blender_scene_reader import _check_animation_state
    return _check_animation_state(scene, target)


# ---------------------------------------------------------------------------
# F-002: Read count probe — getter-based real counting
# ---------------------------------------------------------------------------

class CountedObj:
    """Object that counts real attribute reads via property getters."""
    def __init__(self, name, anim_data=None, data=None):
        self._name = name
        self._anim_data = anim_data
        self._data = data
        self.anim_data_reads = 0
        self.data_reads = 0

    @property
    def name(self):
        return self._name

    @property
    def animation_data(self):
        self.anim_data_reads += 1
        return self._anim_data

    @property
    def data(self):
        self.data_reads += 1
        return self._data


class CountedScene:
    def __init__(self, obj, frame=1):
        self.objects = [obj]
        self.frame_current = frame


def test_anim_data_read_count_zero_when_not_configured():
    """require_animation_data=false, expected_action_name not set → 0 reads."""
    ad = FakeAnimData(FakeAction("idle"))
    obj = CountedObj("Armature", ad)
    scene = CountedScene(obj)
    target = _make_target({"animation_object_name": "Armature",
                           "require_animation_data": False})
    result = _check(target, scene)
    assert obj.anim_data_reads == 0
    assert "animation_data" not in result
    assert "action_name" not in result


def test_anim_data_read_count_one_when_both_configured():
    """require_animation_data=true AND expected_action_name set → exactly 1 read."""
    ad = FakeAnimData(FakeAction("idle"))
    obj = CountedObj("Armature", ad)
    scene = CountedScene(obj)
    target = _make_target({"animation_object_name": "Armature",
                           "require_animation_data": True,
                           "expected_action_name": "idle"})
    result = _check(target, scene)
    assert obj.anim_data_reads == 1, (
        f"Expected 1 animation_data read, got {obj.anim_data_reads}")
    assert result["animation_data"] == {"result": "PASS", "animation_data_present": True}
    assert result["action_name"] == {"result": "PASS", "action_name": "idle"}


# ---------------------------------------------------------------------------
# 1. Block missing / null -> NOT_CHECKED
# ---------------------------------------------------------------------------

def test_block_missing():
    target = {"target_id": "A", "root_object_name": "r",
              "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH"}
    result = _check(target, _make_scene())
    assert result == {"result": "NOT_CHECKED", "note": "ANIMATION_STATE_NOT_CONFIGURED"}


def test_block_null():
    target = _make_target(None)
    result = _check(target, _make_scene())
    assert result == {"result": "NOT_CHECKED", "note": "ANIMATION_STATE_NOT_CONFIGURED"}


# ---------------------------------------------------------------------------
# 2. MODEL_A: only animation_object sub-key when all optional fields absent
# ---------------------------------------------------------------------------

def test_model_a_object_only():
    target = _make_target({"animation_object_name": "Armature"})
    result = _check(target, _make_scene("Armature"))
    assert list(result.keys()) == ["animation_object", "result"]
    assert result["animation_object"] == {"result": "PASS", "object_name": "Armature"}
    assert result["result"] == "PASS"


def test_model_a_object_not_found():
    target = _make_target({"animation_object_name": "Missing"})
    result = _check(target, _make_scene("Armature"))
    assert "animation_object" in result
    assert result["animation_object"]["result"] == "FAIL"
    assert result["animation_object"]["failure_code"] == "ANIMATION_OBJECT_NOT_FOUND"
    assert result["result"] == "FAIL"


def test_animation_object_subkey_always_present():
    target = _make_target({"animation_object_name": "X"})
    result = _check(target, _make_scene("X"))
    assert "animation_object" in result
    assert result["animation_object"] == {"result": "PASS", "object_name": "X"}


# ---------------------------------------------------------------------------
# 3. require_animation_data → animation_data sub-key
# ---------------------------------------------------------------------------

def test_animation_data_true_with_data_present():
    ad = FakeAnimData(FakeAction("idle"))
    scene = _make_scene("Armature", ad)
    target = _make_target({"animation_object_name": "Armature",
                           "require_animation_data": True})
    result = _check(target, scene)
    assert "animation_data" in result
    assert result["animation_data"] == {"result": "PASS", "animation_data_present": True}


def test_animation_data_true_with_data_none():
    scene = _make_scene("Armature", None)
    target = _make_target({"animation_object_name": "Armature",
                           "require_animation_data": True})
    result = _check(target, scene)
    assert "animation_data" in result
    assert result["animation_data"]["result"] == "FAIL"
    assert result["animation_data"]["failure_code"] == "ANIMATION_DATA_NOT_PRESENT"


def test_animation_data_false_omits_subkey():
    scene = _make_scene("Armature", FakeAnimData())
    target = _make_target({"animation_object_name": "Armature",
                           "require_animation_data": False})
    result = _check(target, scene)
    assert "animation_data" not in result


def test_animation_data_null_omits_subkey():
    scene = _make_scene("Armature", FakeAnimData())
    target = _make_target({"animation_object_name": "Armature",
                           "require_animation_data": None})
    result = _check(target, scene)
    assert "animation_data" not in result


def test_animation_data_missing_omits_subkey():
    scene = _make_scene("Armature", FakeAnimData())
    target = _make_target({"animation_object_name": "Armature"})
    result = _check(target, scene)
    assert "animation_data" not in result


# ---------------------------------------------------------------------------
# 4. expected_action_name → action_name sub-key
# ---------------------------------------------------------------------------

def test_action_name_set_match():
    ad = FakeAnimData(FakeAction("idle"))
    scene = _make_scene("Armature", ad)
    target = _make_target({"animation_object_name": "Armature",
                           "expected_action_name": "idle"})
    result = _check(target, scene)
    assert "action_name" in result
    assert result["action_name"] == {"result": "PASS", "action_name": "idle"}


def test_action_name_set_mismatch():
    ad = FakeAnimData(FakeAction("walk"))
    scene = _make_scene("Armature", ad)
    target = _make_target({"animation_object_name": "Armature",
                           "expected_action_name": "idle"})
    result = _check(target, scene)
    assert "action_name" in result
    assert result["action_name"]["result"] == "FAIL"
    assert result["action_name"]["failure_code"] == "ACTION_NAME_MISMATCH"


def test_action_name_set_action_none():
    ad = FakeAnimData(None)
    scene = _make_scene("Armature", ad)
    target = _make_target({"animation_object_name": "Armature",
                           "expected_action_name": "idle"})
    result = _check(target, scene)
    assert "action_name" in result
    assert result["action_name"]["result"] == "FAIL"
    assert result["action_name"]["failure_code"] == "ACTION_NAME_MISMATCH"


def test_action_name_null_omits_subkey():
    ad = FakeAnimData(FakeAction("idle"))
    scene = _make_scene("Armature", ad)
    target = _make_target({"animation_object_name": "Armature",
                           "expected_action_name": None})
    result = _check(target, scene)
    assert "action_name" not in result


def test_action_name_missing_omits_subkey():
    ad = FakeAnimData(FakeAction("idle"))
    scene = _make_scene("Armature", ad)
    target = _make_target({"animation_object_name": "Armature"})
    result = _check(target, scene)
    assert "action_name" not in result


def test_action_name_empty_string_omitted():
    scene = _make_scene("Armature")
    target = _make_target({"animation_object_name": "Armature",
                           "expected_action_name": ""})
    result = _check(target, scene)
    assert "action_name" not in result


def test_action_name_standalone_data_none():
    scene = _make_scene("Armature", None)
    target = _make_target({"animation_object_name": "Armature",
                           "expected_action_name": "idle"})
    result = _check(target, scene)
    assert "animation_data" not in result
    assert "action_name" in result
    assert result["action_name"]["result"] == "FAIL"
    assert result["action_name"]["failure_code"] == "ACTION_NAME_MISMATCH"


def test_action_name_standalone_data_present():
    ad = FakeAnimData(FakeAction("idle"))
    scene = _make_scene("Armature", ad)
    target = _make_target({"animation_object_name": "Armature",
                           "expected_action_name": "idle"})
    result = _check(target, scene)
    assert "animation_data" not in result
    assert "action_name" in result
    assert result["action_name"] == {"result": "PASS", "action_name": "idle"}


# ---------------------------------------------------------------------------
# 5. expected_pose_position → pose_position sub-key
# ---------------------------------------------------------------------------

def test_pose_position_set_match():
    pd = FakePoseData("POSE")
    scene = _make_scene("Armature", data=pd)
    target = _make_target({"animation_object_name": "Armature",
                           "expected_pose_position": "POSE"})
    result = _check(target, scene)
    assert "pose_position" in result
    assert result["pose_position"] == {"result": "PASS", "pose_position": "POSE"}


def test_pose_position_set_mismatch():
    pd = FakePoseData("REST")
    scene = _make_scene("Armature", data=pd)
    target = _make_target({"animation_object_name": "Armature",
                           "expected_pose_position": "POSE"})
    result = _check(target, scene)
    assert "pose_position" in result
    assert result["pose_position"]["result"] == "FAIL"
    assert result["pose_position"]["failure_code"] == "POSE_POSITION_MISMATCH"


def test_pose_position_set_data_none():
    scene = _make_scene("Armature", data=None)
    target = _make_target({"animation_object_name": "Armature",
                           "expected_pose_position": "POSE"})
    result = _check(target, scene)
    assert "pose_position" in result
    assert result["pose_position"]["result"] == "ERROR"
    assert result["pose_position"]["operation"] == "READ_OBJECT_DATA"


def test_pose_position_set_pp_none():
    pd = FakePoseData(None)
    scene = _make_scene("Armature", data=pd)
    target = _make_target({"animation_object_name": "Armature",
                           "expected_pose_position": "POSE"})
    result = _check(target, scene)
    assert "pose_position" in result
    assert result["pose_position"]["result"] == "FAIL"
    assert result["pose_position"]["failure_code"] == "POSE_POSITION_MISMATCH"


def test_pose_position_null_omits_subkey():
    pd = FakePoseData("POSE")
    scene = _make_scene("Armature", data=pd)
    target = _make_target({"animation_object_name": "Armature",
                           "expected_pose_position": None})
    result = _check(target, scene)
    assert "pose_position" not in result


def test_pose_position_missing_omits_subkey():
    pd = FakePoseData("POSE")
    scene = _make_scene("Armature", data=pd)
    target = _make_target({"animation_object_name": "Armature"})
    result = _check(target, scene)
    assert "pose_position" not in result


# ---------------------------------------------------------------------------
# 6. record_current_frame → current_frame sub-key
# ---------------------------------------------------------------------------

def test_record_current_frame_true():
    scene = _make_scene("Armature", frame=42)
    target = _make_target({"animation_object_name": "Armature",
                           "record_current_frame": True})
    result = _check(target, scene)
    assert "current_frame" in result
    assert result["current_frame"] == {"result": "PASS", "current_frame": 42}


def test_record_current_frame_false_omits_subkey():
    scene = _make_scene("Armature")
    target = _make_target({"animation_object_name": "Armature",
                           "record_current_frame": False})
    result = _check(target, scene)
    assert "current_frame" not in result


def test_record_current_frame_null_omits_subkey():
    scene = _make_scene("Armature")
    target = _make_target({"animation_object_name": "Armature",
                           "record_current_frame": None})
    result = _check(target, scene)
    assert "current_frame" not in result


def test_record_current_frame_missing_omits_subkey():
    scene = _make_scene("Armature")
    target = _make_target({"animation_object_name": "Armature"})
    result = _check(target, scene)
    assert "current_frame" not in result


def test_record_current_frame_none_value():
    scene = _make_scene("Armature", frame=None)
    target = _make_target({"animation_object_name": "Armature",
                           "record_current_frame": True})
    result = _check(target, scene)
    assert "current_frame" in result
    assert result["current_frame"] == {"result": "PASS", "current_frame": None}


# ---------------------------------------------------------------------------
# 7. Top-level aggregation
# ---------------------------------------------------------------------------

def test_aggregation_all_pass():
    ad = FakeAnimData(FakeAction("idle"))
    pd = FakePoseData("POSE")
    scene = _make_scene("Armature", ad, pd, frame=1)
    target = _make_target({"animation_object_name": "Armature",
                           "require_animation_data": True,
                           "expected_action_name": "idle",
                           "expected_pose_position": "POSE",
                           "record_current_frame": True})
    result = _check(target, scene)
    assert result["result"] == "PASS"


def test_aggregation_one_fail():
    scene = _make_scene("Armature", FakeAnimData())
    target = _make_target({"animation_object_name": "Armature",
                           "require_animation_data": True,
                           "expected_action_name": "idle"})
    result = _check(target, scene)
    assert result["action_name"]["result"] == "FAIL"
    assert result["result"] == "FAIL"


def test_aggregation_error_over_fail():
    """FAIL (action_name mismatch) + ERROR (data=None -> pose_position ERROR) → ERROR."""
    ad = FakeAnimData(FakeAction("walk"))  # will mismatch "idle"
    scene = _make_scene("Armature", ad, data=None)  # data=None → pose_position ERROR
    target = _make_target({"animation_object_name": "Armature",
                           "expected_action_name": "idle",
                           "expected_pose_position": "POSE"})
    result = _check(target, scene)
    assert result["action_name"]["result"] == "FAIL"
    assert result["action_name"]["failure_code"] == "ACTION_NAME_MISMATCH"
    assert result["pose_position"]["result"] == "ERROR"
    assert result["pose_position"]["operation"] == "READ_OBJECT_DATA"
    assert result["result"] == "ERROR", (
        f"Expected ERROR (ERROR > FAIL), got {result['result']}")


def test_aggregation_no_subkeys_pass():
    target = _make_target({"animation_object_name": "Armature"})
    scene = _make_scene("Armature")
    result = _check(target, scene)
    assert result["animation_object"]["result"] == "PASS"
    assert result["result"] == "PASS"


# ---------------------------------------------------------------------------
# 8. Dependency NOT_CHECKED cascade
# ---------------------------------------------------------------------------

def test_dependency_object_not_found_cascades():
    target = _make_target({"animation_object_name": "Missing",
                           "require_animation_data": True,
                           "expected_action_name": "idle",
                           "expected_pose_position": "POSE"})
    scene = _make_scene("Armature")
    result = _check(target, scene)
    assert result["animation_object"]["result"] == "FAIL"
    assert result["animation_data"]["result"] == "NOT_CHECKED"
    assert result["animation_data"]["note"] == "ANIMATION_OBJECT_NOT_FOUND"
    assert result["action_name"]["result"] == "NOT_CHECKED"
    assert result["action_name"]["note"] == "ANIMATION_OBJECT_NOT_FOUND"
    assert result["pose_position"]["result"] == "NOT_CHECKED"
    assert result["pose_position"]["note"] == "ANIMATION_OBJECT_NOT_FOUND"


def test_dependency_object_fail_frame_independent():
    target = _make_target({"animation_object_name": "Missing",
                           "record_current_frame": True})
    scene = _make_scene("Armature", frame=5)
    result = _check(target, scene)
    assert result["animation_object"]["result"] == "FAIL"
    assert "current_frame" in result
    assert result["current_frame"]["result"] == "PASS"
    assert result["current_frame"]["current_frame"] == 5


def test_dependency_anim_data_fail_action_name_not_checked():
    ad = None
    scene = _make_scene("Armature", ad)
    target = _make_target({"animation_object_name": "Armature",
                           "require_animation_data": True,
                           "expected_action_name": "idle"})
    result = _check(target, scene)
    assert result["animation_data"]["result"] == "FAIL"
    assert result["animation_data"]["failure_code"] == "ANIMATION_DATA_NOT_PRESENT"
    assert result["action_name"]["result"] == "NOT_CHECKED"
    assert result["action_name"]["note"] == "ANIMATION_DATA_NOT_AVAILABLE"


def test_dependency_data_fail_pose_independent():
    ad = FakeAnimData(FakeAction("idle"))
    pd = FakePoseData("POSE")
    scene = _make_scene("Armature", ad, pd)
    target = _make_target({"animation_object_name": "Armature",
                           "require_animation_data": True,
                           "expected_action_name": "idle",
                           "expected_pose_position": "POSE"})
    result = _check(target, scene)
    assert result["animation_data"]["result"] == "PASS"
    assert result["action_name"]["result"] == "PASS"
    assert result["pose_position"]["result"] == "PASS"


# ---------------------------------------------------------------------------
# 9. _recompute_target_overall unit tests
# ---------------------------------------------------------------------------

def test_recompute_overall_all_pass():
    from protocol_guard.phase3_min.blender_scene_reader import _recompute_target_overall
    checks = {"object_exists": {"result": "PASS"}, "animation_state": {"result": "PASS"}}
    assert _recompute_target_overall(checks) == "PASS"


def test_recompute_overall_as_fail_root_pass():
    from protocol_guard.phase3_min.blender_scene_reader import _recompute_target_overall
    checks = {"object_exists": {"result": "PASS"}, "animation_state": {"result": "FAIL"}}
    assert _recompute_target_overall(checks) == "FAIL"


def test_recompute_overall_as_error_root_fail():
    from protocol_guard.phase3_min.blender_scene_reader import _recompute_target_overall
    checks = {"object_exists": {"result": "FAIL"}, "animation_state": {"result": "ERROR"}}
    assert _recompute_target_overall(checks) == "ERROR"


def test_recompute_overall_as_pass_root_fail():
    from protocol_guard.phase3_min.blender_scene_reader import _recompute_target_overall
    checks = {"object_exists": {"result": "FAIL"}, "animation_state": {"result": "PASS"}}
    assert _recompute_target_overall(checks) == "FAIL"


def test_recompute_overall_not_checked_ignored():
    from protocol_guard.phase3_min.blender_scene_reader import _recompute_target_overall
    checks = {"object_exists": {"result": "PASS"},
              "animation_state": {"result": "NOT_CHECKED"}}
    assert _recompute_target_overall(checks) == "PASS"


# ---------------------------------------------------------------------------
# F-004: Full 12-combination overall matrix (Design R5 §4.4)
# ---------------------------------------------------------------------------

OVERALL_MATRIX = [
    # (pre_animation, animation_state, expected_overall)
    ("ERROR", "ERROR", "ERROR"),
    ("ERROR", "FAIL", "ERROR"),
    ("ERROR", "PASS", "ERROR"),
    ("ERROR", "NOT_CHECKED", "ERROR"),
    ("FAIL", "ERROR", "ERROR"),
    ("FAIL", "FAIL", "FAIL"),
    ("FAIL", "PASS", "FAIL"),
    ("FAIL", "NOT_CHECKED", "FAIL"),
    ("PASS", "ERROR", "ERROR"),
    ("PASS", "FAIL", "FAIL"),
    ("PASS", "PASS", "PASS"),
    ("PASS", "NOT_CHECKED", "PASS"),
]


@pytest.mark.parametrize("pre,anim,expected", OVERALL_MATRIX)
def test_full_overall_matrix(pre, anim, expected):
    from protocol_guard.phase3_min.blender_scene_reader import _recompute_target_overall
    checks = {"object_exists": {"result": pre},
              "animation_state": {"result": anim}}
    assert _recompute_target_overall(checks) == expected, (
        f"pre={pre} × anim={anim} → expected {expected}")


# ---------------------------------------------------------------------------
# F-003: Integration control flow tests via open_blend_and_get_scene
# ---------------------------------------------------------------------------

class FakeBlenderTarget:
    """Minimal fake root object for _check_root_objects to find."""
    def __init__(self, name):
        self.name = name
        self.type = "EMPTY"
        self.children = []


class FakeRender:
    engine = "BLENDER_EEVEE"


class FakeBlenderScene:
    def __init__(self, objects=None, frame_current=1):
        self.name = "Scene"
        self.objects = objects if objects is not None else []
        self.frame_current = frame_current
        self.render = FakeRender()


# ---------------------------------------------------------------------------
# F-003: Integration control flow tests with call-counting wrappers
# ---------------------------------------------------------------------------

def _setup_reader_with_counters(scene):
    """Patch bpy, import reader, wrap _check_animation_state and
    _recompute_target_overall with call counters. Returns (reader, counters).
    """
    import sys, types, importlib

    bpy_module = types.ModuleType("bpy")
    bpy_module.data = types.ModuleType("bpy.data")

    _s = scene
    class FakeScenes:
        def get(self, name):
            return _s
    bpy_module.data.scenes = FakeScenes()

    class FakeContext:
        pass
    FakeContext.scene = _s
    bpy_module.context = FakeContext()

    class FakeOps:
        class wm:
            @staticmethod
            def open_mainfile(filepath):
                return {"FINISHED"}
    bpy_module.ops = FakeOps()

    sys.modules["bpy"] = bpy_module

    import protocol_guard.phase3_min.blender_scene_reader as reader
    importlib.reload(reader)

    counters = {"check": 0, "recompute": 0}
    _orig_check = reader._check_animation_state
    _orig_recompute = reader._recompute_target_overall

    def _counted_check(s, t):
        counters["check"] += 1
        return _orig_check(s, t)

    def _counted_recompute(c):
        counters["recompute"] += 1
        return _orig_recompute(c)

    reader._check_animation_state = _counted_check
    reader._recompute_target_overall = _counted_recompute

    return reader, counters


def test_scene_none_no_animation_state_called():
    """scene is None → _check_animation_state called 0 times, per_target_results=[]."""
    import sys, types, importlib

    bpy_module = types.ModuleType("bpy")
    bpy_module.data = types.ModuleType("bpy.data")

    class FakeScenes:
        def get(self, name):
            return None
    bpy_module.data.scenes = FakeScenes()

    class CtxScene:
        name = "Scene"
    class FakeContext:
        pass
    FakeContext.scene = CtxScene()
    bpy_module.context = FakeContext()

    class FakeOps:
        class wm:
            @staticmethod
            def open_mainfile(filepath):
                return {"FINISHED"}
    bpy_module.ops = FakeOps()

    sys.modules["bpy"] = bpy_module

    import protocol_guard.phase3_min.blender_scene_reader as reader
    importlib.reload(reader)

    counters = {"check": 0}
    _orig = reader._check_animation_state
    def _counted(s, t):
        counters["check"] += 1
        return _orig(s, t)
    reader._check_animation_state = _counted

    targets = [_make_target({"animation_object_name": "Armature",
                              "require_animation_data": True})]
    result = reader.open_blend_and_get_scene("/fake.blend", "Scene", None, targets)
    assert counters["check"] == 0, (
        f"Expected 0 calls to _check_animation_state, got {counters['check']}")
    assert result["per_target_results"] == [], (
        f"Expected [], got {result['per_target_results']}")


def test_root_pass_animation_state_executed():
    """Root PASS + Animation State FAIL → overall recomputed to FAIL."""
    root_obj = FakeBlenderTarget("r")
    anim_obj = FakeObj("Armature", FakeAnimData(FakeAction("walk")))
    scene = FakeBlenderScene([root_obj, anim_obj])
    reader, c = _setup_reader_with_counters(scene)

    targets = [{
        "target_id": "A",
        "root_object_name": "r",
        "expected_root_type": "EMPTY",
        "geometry_scope": "SELF_MESH",
        "animation_state": {
            "animation_object_name": "Armature",
            "expected_action_name": "idle",  # will mismatch "walk" → FAIL
        },
    }]
    result = reader.open_blend_and_get_scene("/fake.blend", "Scene", None, targets)
    pr = result["per_target_results"]; assert len(pr) == 1
    checks = pr[0]["checks"]
    assert c["check"] == 1, f"check calls: {c['check']}"
    assert c["recompute"] == 1, f"recompute calls: {c['recompute']}"
    assert "animation_state" in checks
    assert checks["animation_state"]["result"] == "FAIL", (
        f"Expected animation_state FAIL, got {checks['animation_state']['result']}")
    assert pr[0]["overall"] == "FAIL", (
        f"Expected overall FAIL (PASS × FAIL), got {pr[0]['overall']}")


def test_root_fail_animation_state_still_executed():
    """ROOT_NOT_FOUND + Animation State ERROR → overall recomputed to ERROR."""
    anim_obj = FakeObj("Armature", data=None)  # data=None → pose ERROR
    scene = FakeBlenderScene([anim_obj])
    reader, c = _setup_reader_with_counters(scene)

    targets = [{
        "target_id": "A",
        "root_object_name": "r",  # not in scene
        "expected_root_type": "EMPTY",
        "geometry_scope": "SELF_MESH",
        "animation_state": {
            "animation_object_name": "Armature",
            "expected_pose_position": "POSE",  # data=None → ERROR
        },
    }]
    result = reader.open_blend_and_get_scene("/fake.blend", "Scene", None, targets)
    pr = result["per_target_results"]; assert len(pr) == 1
    checks = pr[0]["checks"]
    assert c["check"] == 1, f"check calls: {c['check']}"
    assert c["recompute"] == 1, f"recompute calls: {c['recompute']}"
    assert "animation_state" in checks
    assert checks["animation_state"]["result"] == "ERROR", (
        f"Expected animation_state ERROR, got {checks['animation_state']['result']}")
    assert pr[0]["overall"] == "ERROR", (
        f"Expected overall ERROR (FAIL × ERROR), got {pr[0]['overall']}")


def test_root_error_animation_state_still_executed():
    """AMBIGUOUS_ROOT + Animation State PASS → overall stays ERROR."""
    r1 = FakeBlenderTarget("r"); r2 = FakeBlenderTarget("r")
    anim_obj = FakeObj("Armature")
    scene = FakeBlenderScene([r1, r2, anim_obj])
    reader, c = _setup_reader_with_counters(scene)

    targets = [{
        "target_id": "A",
        "root_object_name": "r",
        "expected_root_type": "EMPTY",
        "geometry_scope": "SELF_MESH",
        "animation_state": {
            "animation_object_name": "Armature",
        },
    }]
    result = reader.open_blend_and_get_scene("/fake.blend", "Scene", None, targets)
    pr = result["per_target_results"]; assert len(pr) == 1
    checks = pr[0]["checks"]
    assert c["check"] == 1, f"check calls: {c['check']}"
    assert c["recompute"] == 1, f"recompute calls: {c['recompute']}"
    assert "animation_state" in checks
    # Pre-animation: ambiguous root → ERROR
    # Animation State: PASS (object found, no sub-checks configured)
    # Final: ERROR (ERROR dominates)
    assert checks["animation_state"]["result"] == "PASS"
    assert pr[0]["overall"] == "ERROR", (
        f"Expected overall ERROR (ERROR × PASS), got {pr[0]['overall']}")
