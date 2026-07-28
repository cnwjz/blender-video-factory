"""Material Assignment I3 focused tests — open_blend_and_get_scene integration.

All tests use monkeypatch, no Blender.
"""
import pytest
from protocol_guard.phase3_min.blender_scene_reader import (
    open_blend_and_get_scene,
    _recompute_target_overall,
)


def _make_target(tag):
    return {"material_assignment": {"require_material_assignment_presence": True},
            "geometry_scope": "SELF_MESH", "root_object_name": tag}


MA_PASS = {"result": "PASS", "per_mesh": [{"mesh_name": "m", "result": "PASS", "slot_count": 1}]}
MA_FAIL = {"result": "FAIL", "failure_code": "MATERIAL_ASSIGNMENT_FAILURE",
           "per_mesh": [{"mesh_name": "m", "result": "FAIL", "failure_code": "MESH_HAS_NO_MATERIAL_SLOTS"}]}
MA_ERROR = {"result": "ERROR", "per_mesh": [
    {"mesh_name": "m", "result": "ERROR", "error_type": "MATERIAL_ASSIGNMENT_COMPUTATION_ERROR",
     "operation": "READ_MATERIAL_SLOTS", "note": "READ_MATERIAL_SLOTS_FAILED"}]}
MA_NOT_CHECKED = {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"}
AS_PASS = {"result": "PASS", "animation_object": {"result": "PASS", "object_name": "root"}}
ROOT_PASS = {"object_exists": {"result": "PASS"}, "object_type": {"result": "PASS", "actual": "MESH"}}


# ── integration tests ──────────────────────────────────────────────────
class TestIntegration:
    @pytest.fixture(autouse=True)
    def patch_bpy(self, monkeypatch):
        import protocol_guard.phase3_min.blender_scene_reader as bsr

        class _FakeBpy:
            class ops:
                class wm:
                    @staticmethod
                    def open_mainfile(filepath):
                        return {"FINISHED"}
            class data:
                class scenes:
                    @staticmethod
                    def get(name):
                        return type("SceneObj", (), {
                            "name": name,
                            "render": type("Rend", (), {"engine": "BLENDER_EEVEE"})(),
                            "objects": [],
                            "frame_current": 1.0,
                        })()
            class context:
                scene = type("S", (), {"name": "Scene"})()
                screen = type("Scr", (), {"scene": type("S2", (), {"name": "Scene"})()})()

        monkeypatch.setattr(bsr, "bpy", _FakeBpy())

    def _patch_checks(self, monkeypatch, ma_results=None, ma_fn=None):
        import protocol_guard.phase3_min.blender_scene_reader as bsr
        events = []

        def fake_root(scene, targets, _target_caches=None):
            events.append("root_checks")
            results = []
            for t in targets:
                results.append({
                    "target_id": t.get("root_object_name", ""),
                    "root_object_name": t.get("root_object_name", ""),
                    "overall": "PASS",
                    "checks": {
                        "object_exists": {"result": "PASS"},
                        "object_type": {"result": "PASS", "actual": "MESH"},
                    },
                })
            return results

        def fake_animation(scene, target):
            tag = target.get("root_object_name", "?")
            events.append(f"animation:{tag}")
            return {"result": "PASS", "animation_object": {"result": "PASS", "object_name": tag}}

        def fake_material(scene, target, target_result):
            tag = target.get("root_object_name", "?")
            events.append(f"material:{tag}")
            if ma_fn:
                return ma_fn(tag, target_result)
            if ma_results and tag in ma_results:
                return ma_results[tag]
            return MA_PASS

        monkeypatch.setattr(bsr, "_check_root_objects", fake_root)
        monkeypatch.setattr(bsr, "_check_animation_state", fake_animation)
        monkeypatch.setattr(bsr, "_check_material_assignment", fake_material)
        return events

    def _patch_with_recompute(self, monkeypatch, ma_results=None, ma_fn=None):
        """Patch all functions including recompute with recording wrapper."""
        import protocol_guard.phase3_min.blender_scene_reader as bsr
        real_recompute = bsr._recompute_target_overall
        events = []
        recompute_checks_ids = []

        def fake_root(scene, targets, _target_caches=None):
            events.append("root_checks")
            results = []
            for t in targets:
                results.append({
                    "target_id": t.get("root_object_name", ""),
                    "root_object_name": t.get("root_object_name", ""),
                    "overall": "PASS",
                    "checks": {
                        "object_exists": {"result": "PASS"},
                        "object_type": {"result": "PASS", "actual": "MESH"},
                    },
                })
            return results

        def fake_animation(scene, target):
            tag = target.get("root_object_name", "?")
            events.append(f"animation:{tag}")
            return {"result": "PASS", "animation_object": {"result": "PASS", "object_name": tag}}

        checks_id_by_tag = {}

        def fake_material(scene, target, target_result):
            tag = target.get("root_object_name", "?")
            events.append(f"material:{tag}")
            checks_id_by_tag[tag] = id(target_result.get("checks", {}))
            if ma_fn:
                return ma_fn(tag, target_result)
            if ma_results and tag in ma_results:
                return ma_results[tag]
            return MA_PASS

        def fake_recompute(checks):
            # Map checks identity back to tag
            tag = None
            for t, cid in checks_id_by_tag.items():
                if cid == id(checks):
                    tag = t
                    break
            events.append(f"recompute:{tag}")
            recompute_checks_ids.append(id(checks))
            return real_recompute(checks)

        monkeypatch.setattr(bsr, "_check_root_objects", fake_root)
        monkeypatch.setattr(bsr, "_check_animation_state", fake_animation)
        monkeypatch.setattr(bsr, "_check_material_assignment", fake_material)
        monkeypatch.setattr(bsr, "_recompute_target_overall", fake_recompute)
        return events, checks_id_by_tag, recompute_checks_ids

    def test_call_order(self, monkeypatch):
        events = self._patch_checks(monkeypatch)
        open_blend_and_get_scene("dummy.blend", "Scene", None,
                                 targets=[_make_target("t1")])
        assert events == ["root_checks", "animation:t1", "material:t1"]

    def test_exact_call_order_with_recompute(self, monkeypatch):
        events, _, _ = self._patch_with_recompute(monkeypatch)
        open_blend_and_get_scene("dummy.blend", "Scene", None,
                                 targets=[_make_target("t1")])
        assert events == [
            "root_checks",
            "animation:t1",
            "material:t1",
            "recompute:t1",
        ]

    def test_multi_target_exact_order(self, monkeypatch):
        events, _, _ = self._patch_with_recompute(monkeypatch)
        open_blend_and_get_scene("dummy.blend", "Scene", None,
                                 targets=[_make_target("t1"), _make_target("t2")])
        assert events == [
            "root_checks",
            "animation:t1", "material:t1", "recompute:t1",
            "animation:t2", "material:t2", "recompute:t2",
        ]

    def test_recompute_checks_identity(self, monkeypatch):
        import protocol_guard.phase3_min.blender_scene_reader as bsr
        events, checks_id_by_tag, recompute_checks_ids = self._patch_with_recompute(
            monkeypatch)
        r = open_blend_and_get_scene("dummy.blend", "Scene", None,
                                     targets=[_make_target("t1")])
        tr = r["per_target_results"][0]
        checks_id = id(tr["checks"])
        assert checks_id_by_tag["t1"] == checks_id
        assert len(recompute_checks_ids) == 1
        assert recompute_checks_ids[0] == checks_id

    def test_result_written_to_correct_key(self, monkeypatch):
        import protocol_guard.phase3_min.blender_scene_reader as bsr
        monkeypatch.setattr(bsr, "_check_root_objects",
                            lambda s, t, _target_caches=None: [{"target_id": "t1", "root_object_name": "t1", "overall": "PASS",
                                           "checks": ROOT_PASS.copy()}])
        monkeypatch.setattr(bsr, "_check_animation_state", lambda s, t, _target_caches=None: AS_PASS)
        monkeypatch.setattr(bsr, "_check_material_assignment", lambda s, t, ptr: MA_PASS)
        r = open_blend_and_get_scene("dummy.blend", "Scene", None,
                                     targets=[_make_target("t1")])
        tr = r["per_target_results"][0]
        assert "material_assignment_presence_check" in tr["checks"]
        assert tr["checks"]["material_assignment_presence_check"] == MA_PASS

    def test_scene_none_no_merge_loop(self, monkeypatch):
        import protocol_guard.phase3_min.blender_scene_reader as bsr
        monkeypatch.setattr(bsr.bpy.data.scenes, "get", lambda name: None)
        monkeypatch.setattr(bsr, "_check_root_objects", lambda s, t, _target_caches=None: [])
        called = []
        monkeypatch.setattr(bsr, "_check_animation_state",
                            lambda s, t, _target_caches=None: called.append("anim") or AS_PASS)
        monkeypatch.setattr(bsr, "_check_material_assignment",
                            lambda s, t, ptr: called.append("ma") or MA_PASS)
        r = open_blend_and_get_scene("dummy.blend", "Scene", None,
                                     targets=[_make_target("t1")])
        assert called == []
        assert r["per_target_results"] == []

    def test_empty_targets_no_calls(self, monkeypatch):
        events = self._patch_checks(monkeypatch)
        open_blend_and_get_scene("dummy.blend", "Scene", None, targets=[])
        assert "animation:" not in str(events)
        assert "material:" not in str(events)

    def test_returns_scene_basic_and_per_target(self, monkeypatch):
        import protocol_guard.phase3_min.blender_scene_reader as bsr
        monkeypatch.setattr(bsr, "_check_root_objects",
                            lambda s, t, _target_caches=None: [{"target_id": "t1", "root_object_name": "t1", "overall": "PASS",
                                           "checks": ROOT_PASS.copy()}])
        monkeypatch.setattr(bsr, "_check_animation_state", lambda s, t, _target_caches=None: AS_PASS)
        monkeypatch.setattr(bsr, "_check_material_assignment", lambda s, t, ptr: MA_PASS)
        r = open_blend_and_get_scene("dummy.blend", "Scene", None,
                                     targets=[_make_target("t1")])
        assert "scene_basic" in r
        assert "per_target_results" in r

    def test_only_one_recompute_per_target(self, monkeypatch):
        events, _, _ = self._patch_with_recompute(monkeypatch)
        open_blend_and_get_scene("dummy.blend", "Scene", None,
                                 targets=[_make_target("t1")])
        recompute_count = sum(1 for e in events if e.startswith("recompute:"))
        assert recompute_count == 1

    def test_material_receives_actual_target_result_object(self, monkeypatch):
        import protocol_guard.phase3_min.blender_scene_reader as bsr

        actual_target_result = {
            "target_id": "t1",
            "root_object_name": "t1",
            "overall": "PASS",
            "checks": {
                "object_exists": {"result": "PASS"},
                "object_type": {"result": "PASS", "actual": "MESH"},
            },
        }

        captured = []

        monkeypatch.setattr(bsr, "_check_root_objects",
                            lambda scene, targets, _target_caches=None: [actual_target_result])
        monkeypatch.setattr(bsr, "_check_animation_state",
                            lambda scene, target: AS_PASS)

        def fake_material(scene, target, target_result):
            captured.append(target_result)
            return MA_PASS

        monkeypatch.setattr(bsr, "_check_material_assignment", fake_material)

        result = open_blend_and_get_scene(
            "dummy.blend", "Scene", None,
            targets=[_make_target("t1")],
        )

        assert len(captured) == 1
        assert captured[0] is actual_target_result
        assert result["per_target_results"][0] is actual_target_result
        assert captured[0] is result["per_target_results"][0]


# ── overall via real open_blend_and_get_scene ───────────────────────────
class TestOverallViaRealEntry:
    @pytest.fixture(autouse=True)
    def patch_bpy(self, monkeypatch):
        import protocol_guard.phase3_min.blender_scene_reader as bsr

        class _FakeBpy:
            class ops:
                class wm:
                    @staticmethod
                    def open_mainfile(filepath):
                        return {"FINISHED"}
            class data:
                class scenes:
                    @staticmethod
                    def get(name):
                        return type("SceneObj", (), {
                            "name": name, "frame_current": 1.0,
                            "render": type("Rend", (), {"engine": "BLENDER_EEVEE"})(),
                            "objects": [],
                        })()
            class context:
                scene = type("S", (), {"name": "Scene"})()
                screen = type("Scr", (), {"scene": type("S2", (), {"name": "Scene"})()})()

        monkeypatch.setattr(bsr, "bpy", _FakeBpy())

    def _setup(self, monkeypatch, ma_result):
        import protocol_guard.phase3_min.blender_scene_reader as bsr

        monkeypatch.setattr(bsr, "_check_root_objects",
                            lambda s, t, _target_caches=None: [{"target_id": "t1", "root_object_name": "t1",
                                           "overall": "PASS", "checks": ROOT_PASS.copy()}])
        monkeypatch.setattr(bsr, "_check_animation_state", lambda s, t, _target_caches=None: AS_PASS)
        monkeypatch.setattr(bsr, "_check_material_assignment",
                            lambda s, t, ptr: ma_result)

    def test_ma_fail_overall_fail(self, monkeypatch):
        self._setup(monkeypatch, MA_FAIL)
        r = open_blend_and_get_scene("dummy.blend", "Scene", None,
                                     targets=[_make_target("t1")])
        assert r["per_target_results"][0]["overall"] == "FAIL"
        assert "material_assignment_presence_check" in r["per_target_results"][0]["checks"]

    def test_ma_error_overall_error(self, monkeypatch):
        self._setup(monkeypatch, MA_ERROR)
        r = open_blend_and_get_scene("dummy.blend", "Scene", None,
                                     targets=[_make_target("t1")])
        assert r["per_target_results"][0]["overall"] == "ERROR"

    def test_ma_not_checked_overall_pass(self, monkeypatch):
        self._setup(monkeypatch, MA_NOT_CHECKED)
        r = open_blend_and_get_scene("dummy.blend", "Scene", None,
                                     targets=[_make_target("t1")])
        assert r["per_target_results"][0]["overall"] == "PASS"

    def test_other_error_ma_fail_overall_error(self, monkeypatch):
        import protocol_guard.phase3_min.blender_scene_reader as bsr
        monkeypatch.setattr(bsr, "_check_root_objects",
                            lambda s, t, _target_caches=None: [{"target_id": "t1", "root_object_name": "t1",
                                           "overall": "PASS",
                                           "checks": {"object_exists": {"result": "ERROR",
                                                                        "error_type": "SOME_ERROR"},
                                                       "object_type": {"result": "PASS",
                                                                       "actual": "MESH"}}}])
        monkeypatch.setattr(bsr, "_check_animation_state", lambda s, t, _target_caches=None: AS_PASS)
        monkeypatch.setattr(bsr, "_check_material_assignment",
                            lambda s, t, ptr: MA_FAIL)
        r = open_blend_and_get_scene("dummy.blend", "Scene", None,
                                     targets=[_make_target("t1")])
        assert r["per_target_results"][0]["overall"] == "ERROR"


# ── overall aggregation (direct) ───────────────────────────────────────
class TestOverall:
    def test_ma_fail_overall_fail(self):
        checks = {"object_exists": {"result": "PASS"}, "object_type": {"result": "PASS"},
                   "material_assignment_presence_check": MA_FAIL}
        assert _recompute_target_overall(checks) == "FAIL"

    def test_ma_error_overall_error(self):
        checks = {"object_exists": {"result": "PASS"}, "object_type": {"result": "PASS"},
                   "material_assignment_presence_check": MA_ERROR}
        assert _recompute_target_overall(checks) == "ERROR"

    def test_ma_not_checked_does_not_lift_overall(self):
        checks = {"object_exists": {"result": "PASS"}, "object_type": {"result": "PASS"},
                   "material_assignment_presence_check": MA_NOT_CHECKED}
        assert _recompute_target_overall(checks) == "PASS"

    def test_other_fail_ma_pass_overall_fail(self):
        checks = {"object_exists": {"result": "FAIL"}, "object_type": {"result": "PASS"},
                   "material_assignment_presence_check": MA_PASS}
        assert _recompute_target_overall(checks) == "FAIL"

    def test_other_error_ma_fail_overall_error(self):
        checks = {"object_exists": {"result": "ERROR"}, "object_type": {"result": "PASS"},
                   "material_assignment_presence_check": MA_FAIL}
        assert _recompute_target_overall(checks) == "ERROR"
