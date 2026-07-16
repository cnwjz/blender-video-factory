# Camera Revision Report — BVF Test 001 V2

Date: 2026-07-14
Phase: Stage 2A (Camera Composition Rework)

---

## 1. V1 Camera Problem Root Cause

v1 used a **perspective** camera at position (0.2, -1.5, 5.5) with rotation (1.22 rad ≈ 70°) looking nearly straight down. Root causes:

1. **Excessive pitch angle (70°)**: The camera was pointed almost vertically downward, collapsing the Z axis and making queues appear as thin lines rather than distinct rows.
2. **Camera too close**: Position Y=-1.5 meant the camera was behind the customers. With perspective, near objects appeared large while far objects (counters) appeared tiny.
3. **No bounding-box calculation**: Camera was hardcoded to fixed coordinates without checking whether all essential objects were visible.
4. **Camera movement obscured framing**: The subtle drift/zoom (0.15m movement) was enough to push edge objects out of frame, but the movement was too small to register as intentional.

**Result**: First frame showed only counters. Queues, customer movement, and congestion results were completely outside the frame.

## 2. V2 Camera Configuration

| Parameter | Value |
|-----------|-------|
| Type | ORTHO |
| Location | (0.0, -5.0, 9.0) |
| Rotation | (50°, 0, 0) = (0.8727 rad, 0, 0) |
| ortho_scale | 10.0 |
| Movement | STATIC (no keyframes) |

**Design rationale**: Orthographic projection eliminates perspective distortion, ensuring all characters appear at consistent size regardless of depth. The 50° angle provides an oblique view that clearly shows both counters (upper area) and queues extending downward.

## 3. Spatial Layout Adjustments

Changed from v1 config to improve camera coverage:

| Parameter | v1 | v2 |
|-----------|----|----|
| Window X spacing | ±2.0 | ±1.2 |
| Counter width | 1.2 | 1.2 (unchanged) |
| Character radius | 0.15 | 0.12 |
| Character height | 1.4 | 1.3 |

Window spacing reduced by 40% (4.0 → 2.4 units between outer windows).

## 4. Frame-by-Frame Visibility

| Frame | Counters | Customers | Cashiers | Clipped | Notes |
|-------|----------|-----------|----------|---------|-------|
| F1 | 3 | 9 | 3 | 0 | Full scene visible, 3 queues distinguishable |
| F75 | 3 | 9 | 3 | 0 | Middle shutter mid-fall, light off |
| F90 | 3 | 9 | 2 (mid retreated) | 0 | Middle fully closed, queue paused |
| F150 | 3 | 9 | 2 | 0 | M1 moving left, M2 starting right path |
| F225 | 3 | 11 | 2 | 0 | N1+N2 entered, queues growing |
| F345 | 3 | 13 | 2 | 0 | Final congestion, middle dark/closed |

## 5. Preflight Validation Results (camera_preflight_v2.json)

```
Counters visible: 3/3 PASS
Cashiers visible: 3/3 PASS
Initial customers visible: 9/9 PASS
Clipped objects: 0 PASS
Min character pixel height: 84px PASS (≥55px requirement)
ALL PASS: True
```

## 6. Silent Understanding Assessment (V2)

| Frame | Criterion | Status |
|-------|-----------|--------|
| F1 | Three windows + three queues visible in first second | Pending review |
| F1 | All 9 customers with complete bodies visible | Confirmed (preflight) |
| F1 | Three queues distinguishable with lateral gaps | Pending review (queue stripes added) |
| F75 | Middle window closing action visible (shutter mid-fall) | Pending review |
| F90 | Middle window fully closed (shutter down, sign off, counter dark) | Pending review |
| F150 | Middle queue customer moving sideways (diversion) | Pending review |
| F225 | Left and right queues growing, new customers visible | Pending review |
| F345 | Two long queues + empty dark middle window | Pending review |

## 7. Unresolved Issues

1. **Graybox recognizability**: Despite improved framing, simplified cylinder+sphere characters may still be hard to understand as "people in a queue." This is expected for graybox and will improve with visual style in Phase 4.
2. **Camera angle tradeoff**: 50° is a compromise — steeper would show more queue length but less counter visibility. Shallower would show more counter detail but compress queue depth. 50° was chosen for balanced visibility.
3. **Window close remains animated through visibility toggles**, not material property keyframes (Blender 5.1 limitation).
