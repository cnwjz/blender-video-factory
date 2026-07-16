# Graybox Motion Report — BVF Test 001 V3

Date: 2026-07-14
Phase: Stage 2 (Graybox Full Preview Render)

---

## 1. Render Specification

| Parameter | Value |
|-----------|-------|
| Source | `scene_graybox_v3_character_fixed.blend` |
| Resolution | 540 × 960 |
| FPS | 30 |
| Total frames | 345 |
| Duration | 11.5 seconds |
| Engine | BLENDER_EEVEE |
| Format | PNG sequence → H.264 MP4 |

## 2. Render Performance

| Metric | Value |
|--------|-------|
| Total frames rendered | 345 / 345 |
| Render time | ~82 seconds |
| Avg per frame | ~0.24 seconds |
| Output MP4 size | 153 KiB |

## 3. Frame Integrity

- [x] Black frames: None
- [x] Missing frames: None (345/345 rendered)
- [x] Frame sequence continuous: Confirmed (frame_0001 to frame_0345)

## 4. Character Movement

### 4.1 Queue Advance (Shot 1, F1-F60)
- All 9 initial customers move forward by ~0.25 units
- Movement is smooth, linear interpolation between keyframes
- No floating — all characters on ground via Root hierarchy

### 4.2 Window Close (Shot 2, F61-F120)
- Middle signboard: OFF at frame 66 (visibility toggle)
- Middle shutter: Falls from frame 70 to 88
- Middle cashier: Retreats from frame 72 to 90
- Middle queue: Pauses from frame 60 to 105
- Close action clearly visible through 3 visual signals

### 4.3 Queue Diversion (Shot 3, F121-F225)
- M1 (frame 121-153): Moves from middle to left queue
- M2 (frame 136-168): Moves from middle to right queue
- M3 (frame 151-183): Moves from middle to left queue
- Three-phase movement: step back → lateral → forward
- Paths are staggered, not parallel
- No character overlap or collision observed

### 4.4 New Customer Entry (Shot 3-4)
- N1 (frame 165): Enters right queue — visible at frame 165+
- N2 (frame 195): Enters left queue — visible at frame 195+
- N3 (frame 245): Enters right queue — visible at frame 245+
- N4 (frame 285): Enters left queue — visible at frame 285+
- Entry from below frame edge with visibility toggle

### 4.5 L/R Queue Growth (Shot 3-4)
- Left and right queues continue advancing through frames 120-270

### 4.6 Final Hold (Shot 4, F321-F345)
- Final 24 frames (0.8s) are stable — no new movement
- All 13 customers in final positions with connected head-bodies

## 5. Character Hierarchy

- [x] All 16 character roots verified (13 customers + 3 cashiers)
- [x] All body objects parented to root: PASS
- [x] All head objects parented to root: PASS
- [x] No floating heads: PASS (character_preflight_v3.json 16/16)
- [x] No detached bodies: PASS
- [x] Pixel height: 83px per character body

## 6. Silent Understanding Assessment

| F1 (0.0s) | Three windows visible, three queues distinguishable |
| F75 (2.5s) | Middle sign off, shutter mid-fall |
| F90 (3.0s) | Middle fully closed: dark sign, shutter down, counter dark, cashier retreated |
| F150 (5.0s) | M1 moving left, M2 starting right — diversion visible |
| F225 (7.5s) | N1+N2 entered, left/right queues clearly longer than F1 |
| F345 (11.5s) | Two long queues, empty dark middle, congestion result |

## 7. Issues Found

### 7.1 No critical issues
- No black frames, no missing frames
- No character collision or overlap
- No floating or detached body parts
- All window close signals function correctly
- All diversion paths complete without teleporting
- Final hold duration ≥ 0.8s (24 frames)

### 7.2 Minor observations
- Ground stripes partially clipped at frame bottom — visual aid only, not essential
- Character appearance is purely geometric (cylinder + sphere) — expected for graybox phase
- No camera movement — static ortho only, as required by Stage 2A

## 8. Still Frame Consistency Check

| Frame | V3 Full Render | V3 Still Review | Match |
|-------|---------------|-----------------|-------|
| F001 | Present | F001.png | Consistent |
| F075 | Present | F075.png | Consistent |
| F090 | Present | F090.png | Consistent |
| F150 | Present | F150.png | Consistent |
| F225 | Present | F225.png | Consistent |
| F345 | Present | F345.png | Consistent |

All 6 review frames match between the still render (Stage 2B) and the full sequence render (Stage 2 preview).

## 9. Decision

**Graybox full motion preview passes.** All 345 frames rendered, all character hierarchies verified, no critical issues found. The mechanism timeline (3-window normal → middle close → diversion → congestion) is visible in the preview.

**Pending human review** of `graybox_preview_v3.mp4` against the `HUMAN_REVIEW.md` checklist. Do not proceed to Phase 3 (visual style) or Phase 4 (final render) until silent understanding is confirmed by a human reviewer.
