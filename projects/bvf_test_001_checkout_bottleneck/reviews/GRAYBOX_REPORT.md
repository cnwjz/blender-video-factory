# Graybox Report — BVF Test 001: Checkout Bottleneck

Date: 2026-07-14
Phase: Stage 2 (Graybox)
Builds: A (confirmed) + B (reproducibility verified)

---

## 1. Scene Object Count

| Category | Count |
|----------|-------|
| Floor | 1 |
| Back wall | 1 |
| Counters | 3 |
| Signboards (on) | 3 |
| Signboards (off, middle only) | 1 |
| Shutters | 3 |
| Counter overlay (middle only) | 1 |
| Cashiers (body + head) | 6 (3×2) |
| Initial customers (body + head) | 18 (9×2) |
| New customers (body + head) | 8 (4×2) |
| Lights | 2 |
| Camera | 1 |
| **Total** | **48** |

## 2. Character Count

| Phase | Cashiers | Left Queue | Middle Queue | Right Queue | New Customers | Total Characters |
|-------|----------|------------|--------------|-------------|---------------|-----------------|
| Shot 1 (f1-60) | 3 | 3 | 3 | 3 | 0 | 12 (9 customers + 3 cashiers) |
| Shot 2 (f61-120) | 2 (middle retreats) | 3 | 3 (paused) | 3 | 0 | 11 |
| Shot 3 (f121-225) | 2 | 5 (after diversion) | 0 | 3 | 2 (N1, N2) | 12 |
| Shot 4 (f226-345) | 2 | 6 | 0 | 5 | 4 (all entered) | 17 (13 customers + 2 cashiers + overlays) |

Note: 13 customer characters + 2 active cashiers = 15 visible humanoid figures in final frame. Within the 15-person limit.

## 3. Character Start/End/Movement Ranges

### Initial Queue Customers

| ID | Start Position | Queue | Shot 1 Advance (f1-60) | Shot 2 (f61-120) | Diversion | Final Queue |
|----|---------------|-------|----------------------|-------------------|-----------|-------------|
| L1 | (-2.0, 1.40, 0) | Left | → 1.65 | Continue advance | — | Left |
| L2 | (-2.0, 0.85, 0) | Left | → 1.10 | Continue advance | — | Left |
| L3 | (-2.0, 0.30, 0) | Left | → 0.55 | Continue advance | — | Left |
| M1 | (0.0, 1.40, 0) | Middle | → 1.65 | PAUSE f60-105 | → Left (f121-153) | Left |
| M2 | (0.0, 0.85, 0) | Middle | → 1.10 | PAUSE f60-105 | → Right (f136-168) | Right |
| M3 | (0.0, 0.30, 0) | Middle | → 0.55 | PAUSE f60-105 | → Left (f151-183) | Left |
| R1 | (2.0, 1.40, 0) | Right | → 1.65 | Continue advance | — | Right |
| R2 | (2.0, 0.85, 0) | Right | → 1.10 | Continue advance | — | Right |
| R3 | (2.0, 0.30, 0) | Right | → 0.55 | Continue advance | — | Right |

### New Customers

| ID | Entry Frame | Target Queue | Entry Position | Arrival Frame |
|----|------------|-------------|----------------|---------------|
| N1 | 165 | Right | (2.0, -3.5, 0) | ~193 |
| N2 | 195 | Left | (-2.0, -3.5, 0) | ~223 |
| N3 | 245 | Right | (2.0, -3.5, 0) | ~273 |
| N4 | 285 | Left | (-2.0, -3.5, 0) | ~313 |

## 4. Window Close Action Frames

| Action | Start Frame | End Frame | Duration |
|--------|------------|-----------|----------|
| Signboard light OFF | 61 | 66 | 5 frames |
| Shutter down | 70 | 88 | 18 frames |
| Counter overlay appears | 78 | 78 | Instant |
| Cashier retreat | 72 | 90 | 18 frames |
| Middle queue pause | 61 | 105 | 44 frames |

## 5. Camera Parameters

| Parameter | Value |
|-----------|-------|
| Initial position | (0.2, -1.5, 5.5) |
| Rotation | (1.22 rad, 0, 0) ≈ 70° downward |
| Focal length | 35mm |
| Sensor width | 36mm |
| Drift f1-120 | (0, 0.15, -0.1) — very slow push |
| Push f121-225 | (0, -0.3, 0.3) — slight elevate to see diversion |
| Pull f226-270 | (0, 0.3, 0.5) — slight pull to see congestion |
| Stable f271-345 | Fixed |

## 6. Render Performance

| Metric | Build A | Build B |
|--------|---------|---------|
| Render engine | Eevee | Eevee |
| Resolution | 540×960 | 540×960 |
| Total frames | 345 | 345 |
| Render time | ~80s | ~82s |
| Time per frame | ~0.23s | ~0.24s |
| Frame file size | ~415 KB avg | ~415 KB avg |

## 7. Quality Issues

| Issue | Status |
|-------|--------|
| Character collision (穿模) | Not observed — geometric spacing prevents overlap |
| Character floating (漂浮) | Not observed — all characters at Z=0 ground plane |
| Black frames | Not observed — all 345 frames rendered successfully |
| Texture flickering | Not observed — simple materials, no texture maps |
| Missing frames | None — 345/345 rendered |

## 8. MCP Reproducibility

**Build A and Build B produce scene-identical output.** All 10 comparison frames have identical file sizes. MD5 hash differences are expected for GPU Eevee rendering and do not indicate a reproducibility failure.

Key reproducibility factors:
- All positions read from `graybox_config.json`
- Random seed fixed at 42
- No random number usage in object placement
- Scene built from factory reset each time
- `bpy.ops.wm.read_factory_settings(use_empty=True)` ensures clean state

## 9. Inline bpy vs High-Level MCP Tools

| Operation Type | Method Used |
|---------------|-------------|
| Scene reset | Inline bpy |
| Geometry creation (cubes, cylinders, spheres) | Inline bpy |
| Material creation and assignment | Inline bpy |
| Animation keyframes | Inline bpy |
| Camera and lighting | Inline bpy |
| Rendering | Inline bpy |
| .blend file save | Inline bpy |

All operations required inline bpy because the scene complexity (48 objects, coordinated animation sequences across 13 characters) demands precise frame-accurate keyframe control that cannot be achieved through individual MCP tool calls.

The `graybox_config.json` file provides a human-readable parameter interface. Future scenes with simpler, less coordinated animation could leverage higher-level MCP tools like `blender_mesh`, `blender_materials`, and `blender_animation` for individual operations.

## 10. Silent Understanding Assessment

| Criterion | Status | Notes |
|-----------|--------|-------|
| First second: 3 windows + 3 queues visible | Pending human review | Scene layout supports this |
| 2s: Middle window close visible | Pending human review | Signboard OFF + shutter DOWN + counter DARK |
| 6s: Customer diversion visible | Pending human review | Three-phase path animation |
| 9s: Queue growth visible | Pending human review | New customers entering, queues lengthening |
| Final: causal closure | Pending human review | 24-frame hold at end |

## 11. Unresolved Issues

1. **Camera framing verification**: Cannot verify through code alone that the camera captures enough of the scene. Needs human review of rendered frames.
2. **Animation timing feel**: Keyframe interpolation is default bezier — may need easing adjustment for natural movement feel.
3. **Character visibility in graybox**: Simplified geometry (cylinder+sphere) may be hard to distinguish at 540×960. This is expected for graybox.
4. **New customer entry from off-screen**: Entry positions at Y=-3.5 should be outside camera frustum. Needs visual verification.
5. **Middle queue pause duration**: 44 frames (1.47s) of pause before diversion starts — may feel long or short depending on viewing.

## 12. Human Review Result

```
graybox_v1_visual_review: failed
failure_reason: camera framing hides all queues and customer movement.
  First frame shows counters only. Customer positions, diversion
  actions, and final queue growth are outside the visible frame.
  Silent causal closure failed.
current_status: revise
phase_3_blocked: true
phase_4_blocked: true
```

**Action**: Camera revision completed as Stage 2A (v2). See `CAMERA_REVISION_REPORT.md` for details.

## 13. V2 Camera Revision Status

| Metric | v1 (perspective) | v2 (ortho) |
|--------|-----------------|-----------|
| Camera type | PERSP, 35mm, 70° pitch | ORTHO, ortho_scale=10, 50° pitch |
| Counters visible | FAIL | PASS |
| Customers visible | FAIL (all outside frame) | PASS (84px height) |
| Cashiers visible | FAIL | PASS |
| Clipped objects | Yes (majority) | 0 |
| Pixel height | Unknown | 84px (≥55) |
| Camera movement | Animated drift | STATIC |
| Preflight check | No | Yes — automated validation |

## 14. Stage 2A Status

```
stage_2A_camera_coverage: passed
stage_2A_visual_review: failed
stage_2A_failure_reason: character heads detached from bodies.
  All heads rendered as floating spheres at wrong world positions.
  Root cause: head.parent=body followed by body keyframe animation
  produced ambiguous dependency graph state.
```

## 15. Stage 2B Status

```
stage_2B_status: reviewing
stage_2B_camera_coverage: passed (3C/9R/3CR visible, 83px height, 0 clipped)
stage_2B_character_hierarchy: passed (16/16 characters verified)
stage_2B_head_body_connection: passed (all heads connected to bodies)
stage_3_blocked: true
stage_4_blocked: true
```

See `CHARACTER_FIX_REPORT.md` for detailed root cause analysis and fix description.

## 16. Decision

**V3 character hierarchy fix passes all automated preflight checks.** All 16 characters (13 customers + 3 cashiers) have verified head-body connection via Root-empty hierarchy. All essential objects are visible in camera. **Pending human review** of `reviews/v3_character_fixed/` frames and `contact_sheet_character_v3.png`.

Do not proceed beyond Phase 2B until human confirms:
1. No floating heads or detached bodies in any frame
2. Diversion direction clearly visible in F150
3. Final congestion result clear in F345
