# BVF Test 001 — Final Validation Report

Date: 2026-07-14 | Project: bvf_test_001_checkout_bottleneck

---

## 1. Executive Summary

Blender Video Factory route validation completed. Blender is technically capable but the publication-level visual quality did not reach the Douyin content threshold within acceptable iteration cost.

**Final recommendation**: Pause Blender route. Retain repository for mechanism pre-visualization and graybox spatial animation. Do not proceed to full visual production pipeline in current form.

---

## 2. Stage Status

| Stage | Status | Notes |
|-------|--------|-------|
| stage_0_environment | **passed** | Blender 5.1.2, Eevee, FFmpeg, CLI render all confirmed |
| stage_1_direction | **passed** | Mechanism, shots, visual direction documented |
| stage_2_graybox | **passed** | 345-frame graybox rendered, silent understanding confirmed via human review |
| stage_3_action_revision | **passed** | Cashier hide, diversion timing, camera framing fixed |
| stage_4_composition | **passed** | Preflight-driven ortho camera, 0 clipped objects, 10.8% top dead space |
| stage_4_publication_style | **failed** | 4 style iterations (v1-v4) did not reach publication threshold |
| full_style_render | **cancelled** | Not attempted — 4D failed before full render |
| post_production | **cancelled** | JianYing post-production not started |
| final_status | **route_validation_completed** | |
| blender_route_status | **paused** | |

---

## 3. What Worked

1. **Blender 5.1.2 environment**: Full audit passed. `--background`, Eevee, PNG sequence, FFmpeg pipeline all functional.
2. **blender-mcp**: Used for status checks, environment queries. Core scene construction via deterministic bpy scripts.
3. **Graybox mechanism**: Three-window checkout → middle close → customer diversion → queue congestion successfully expressed in 345 frames.
4. **Silent understanding**: Human review confirmed the causal mechanism is visible without audio or text.
5. **Camera preflight**: Cross-frame bounding-box validation with `world_to_camera_view` automated framing checks.
6. **Character Root hierarchy**: Root-empty pattern solved head-body detachment from earlier approaches.
7. **Deterministic build**: graybox_config.json + single bpy script produced reproducible output.
8. **FFmpeg pipeline**: PNG→MP4 encoding and contact sheet generation working reliably.

---

## 4. What Failed

1. **Publication visual quality**: After style_v1 through style_v4, the low-poly miniature look still read as "3D exercise" rather than "designed Douyin content."
2. **Cashier rendering**: Final V4 still showed positional issues with cashiers behind counters — heads and legs not consistently in correct relationship.
3. **Warm orange emphasis**: Despite exclusive orange shutter material, the middle-close signal was weaker than intended when viewed standalone at F090.
4. **Scene recognizability**: Supermarket identity (conveyors, products, shelves) was present but insufficient to overcome the "low-poly practice" impression.
5. **Iteration cost**: 4 style rounds consumed more effort than the initial verification scope allowed, with marginal improvement per round.

---

## 5. Comparison with Remotion Route

| Dimension | Remotion (original) | Blender (tested) |
|-----------|-------------------|------------------|
| First-frame impact | UI/animation, reads as "designed" | 3D scene, reads as "CG exercise" |
| Spatial presence | 2D/2.5D | True 3D with depth |
| Character visibility | Phone UI / abstract | Geometric humanoids |
| Silent mechanism clarity | Requires text overlays | Spatial actions self-explanatory |
| Iteration cost | Per-Scene React component | Per-script bpy rebuild + render |
| Douyin nativeness | Closer to platform content style | Further from platform content style |

Blender did NOT clearly outperform Remotion in the dimensions that matter for Douyin (first-frame appeal, platform nativeness, designed feel).

---

## 6. Stop-loss Assessment

Per the handoff document Section 17 stop-loss criteria:

| Criterion | Assessment |
|-----------|-----------|
| Silent mechanism understanding | Achieved (graybox) |
| Doesn't look like 3D homework | **Not achieved** (style iterations failed) |
| Asset and action cost controllable | Partially (graybox is cheap; style is expensive) |
| Claude Code can rebuild scenes stably | Yes (deterministic bpy scripts) |
| Render speed acceptable | Yes (82s for 345 frames at 540p) |
| Visually better than Remotion | **Not demonstrated** |
| User willing to continue this style | No (human review rejected 4D) |

**Stop-loss triggered on: visual quality below platform threshold + iteration cost exceeding scope.**

---

## 7. Disposition

- Blender repository (`D:\blender-video-factory`): **Preserved** — not deleted
- Remotion repository (`D:\video-factory`): **Preserved** — not modified
- Blender route: **Paused**, not abandoned
- Future Blender use: Mechanism pre-viz, spatial mockups, graybox animation
- Next action: Return to Remotion or evaluate alternative visual approaches
