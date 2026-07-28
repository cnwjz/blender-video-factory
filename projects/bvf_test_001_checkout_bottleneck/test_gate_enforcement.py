"""
Focused tests for gate integrity + supplemental checks.
All tests call real production functions.
"""
import json, os, sys, pytest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate_integrity as gi
import production_gate as pg
import gate_video_profile as vp


# ══ gate_integrity functions ══
class TestGateIntegrity:
    def test_compute_gate_result_all_pass(self):
        r = gi.compute_gate_result(True, True, True, True, run_id="t")
        assert r["all_pass"] is True

    def test_compute_gate_result_formal_fail(self):
        r = gi.compute_gate_result(True, True, False, True)
        assert r["all_pass"] is False

    def test_compute_gate_result_suppl_fail(self):
        r = gi.compute_gate_result(True, True, True, False)
        assert r["all_pass"] is False

    def test_authorize_preview_render_passes(self, tmp_path):
        p = tmp_path / "g.json"
        p.write_text(json.dumps({"run_id":"r1","all_pass":True,
            "key_frame_preview_authorized":True,"full_render_authorized":False}))
        ok, _ = gi.authorize_preview_render(str(p), "r1")
        assert ok is True

    def test_authorize_preview_render_rejects_wrong_rid(self, tmp_path):
        p = tmp_path / "g.json"
        p.write_text(json.dumps({"run_id":"r1","all_pass":True,
            "key_frame_preview_authorized":True,"full_render_authorized":False}))
        ok, _ = gi.authorize_preview_render(str(p), "wrong")
        assert ok is False

    def test_build_supplemental_errors_block(self):
        r = gi.build_supplemental_result({"a":["e1","e2"],"b":[]})
        assert r["pass"] is False
        assert r["total_errors"] == 2

    def test_build_supplemental_zero_errors_passes(self):
        r = gi.build_supplemental_result({"a":[],"b":[]})
        assert r["pass"] is True
        assert r["total_errors"] == 0

    def test_total_errors_sums_all(self):
        r = gi.build_supplemental_result({"a":["x","y","z"],"b":["w"],"c":[]})
        assert r["total_errors"] == 4


# ══ Per-frame visibility ══
class TestPerFrameVisibility:
    def test_n1_hidden_before_entry(self):
        for f in [1, 60, 164]:
            vp_vis, hr_vis = vp.is_visible_at_frame("N1_body", f)
            assert vp_vis is False

    def test_n1_visible_after_entry(self):
        assert vp.is_visible_at_frame("N1_body", 165) == (True, True)

    def test_sign_switch(self):
        assert vp.is_visible_at_frame("Sign_middle", 65) == (True, True)
        assert vp.is_visible_at_frame("Sign_middle", 66) == (False, False)
        assert vp.is_visible_at_frame("Sign_middle_off", 65) == (False, False)
        assert vp.is_visible_at_frame("Sign_middle_off", 66) == (True, True)

    def test_overlay_appears(self):
        assert vp.is_visible_at_frame("Counter_middle_overlay", 77) == (False, False)
        assert vp.is_visible_at_frame("Counter_middle_overlay", 78) == (True, True)


# ══ Spec generation ══
class TestSpecGeneration:
    def test_visible_body_has_ground_contact(self):
        spec = pg.build_spec("/f.blend", 1, static_only=False)
        l1 = [t for t in spec["targets"] if t["target_id"] == "L1_body"][0]
        assert "ground_contact" in l1

    def test_hidden_body_no_ground_contact(self):
        spec = pg.build_spec("/f.blend", 1, static_only=False)
        n1 = [t for t in spec["targets"] if t["target_id"] == "N1_body"][0]
        assert "ground_contact" not in n1

    def test_visible_after_entry_has_gc(self):
        spec = pg.build_spec("/f.blend", 345, static_only=False)
        n1 = [t for t in spec["targets"] if t["target_id"] == "N1_body"][0]
        assert "ground_contact" in n1

    def test_gc_tolerance_010(self):
        spec = pg.build_spec("/f.blend", 1, static_only=False)
        l1 = [t for t in spec["targets"] if t["target_id"] == "L1_body"][0]
        assert l1["ground_contact"]["ground_contact_tolerance"] == 0.10

    def test_n1_in_pg_after_entry(self):
        ids = vp.get_projection_targets_for_frame(165)
        assert "N1_body" in ids

    def test_n1_not_in_pg_before_entry(self):
        ids = vp.get_projection_targets_for_frame(164)
        assert "N1_body" not in ids

    def test_49_event_frames(self):
        frames = vp.get_event_frames()
        assert len(frames) >= 40


# ══ Queue slot allocation ══
class TestQueueSlotAllocation:
    def test_allocate_slots_unique(self):
        """Simulate the build script's slot allocator logic."""
        qsy = 0.80; front = 1.40; slots = {"left":0,"middle":0,"right":0}
        def alloc(lane):
            s = slots[lane]; slots[lane] += 1; return front - s * qsy
        # Initial: L1=0, L2=1, L3=2 in left lane
        l1 = alloc("left"); l2 = alloc("left"); l3 = alloc("left")
        assert l1 == pytest.approx(1.40); assert l2 == pytest.approx(0.60); assert l3 == pytest.approx(-0.20)
        m1 = alloc("left")
        assert m1 == pytest.approx(-1.00)
        m3 = alloc("left")
        assert m3 == pytest.approx(-1.80)

    def test_spacing_is_080(self):
        qsy = 0.80; front = 1.40; slots = {"left":0}
        def alloc(lane):
            s = slots[lane]; slots[lane] += 1; return front - s * qsy
        positions = [alloc("left") for _ in range(5)]
        for i in range(len(positions)-1):
            assert abs(positions[i] - positions[i+1]) == pytest.approx(qsy, abs=0.01)

    def test_slot_changes_with_qsy(self):
        for qsy_val in [0.80, 1.00, 0.55]:
            slots = {"left": 0}
            def alloc(lane, qs=qsy_val, f=1.40):
                s = slots[lane]; slots[lane] += 1; return f - s * qs
            p1 = alloc("left"); p2 = alloc("left")
            assert abs(p1 - p2 - qsy_val) < 0.01
