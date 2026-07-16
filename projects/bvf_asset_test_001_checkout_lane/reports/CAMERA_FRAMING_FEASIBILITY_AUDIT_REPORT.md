# Camera Framing Feasibility Audit

## Scene

- World vertices: 5487
- Target: <Vector (-0.3935, 1.0174, 0.7482)>
- Direction: <Vector (0.4949, -0.7614, 0.4188)>
- Resolution: 540x960

## Part 1: L1-C2 Re-Audit (55mm VERTICAL)

- HFOV=14.0deg VFOV=24.6deg
- At 18m: content fills ~50% vertically but edges clip severely
- At 22m: no clipping but content height ~28%
- Both share same target/direction/lens. The difference is **purely** distance.
- At close range, perspective divergence pushes side vertices beyond screen edges.
- At far range, all vertices fit but the narrow FOV makes them tiny.

## Part 2: Lens Feasibility Sweep

| Lens | Sensor Fit | Dist(m) | Content H | Content W | Left | Right | Feasible |
|------|-----------|---------|-----------|-----------|------|-------|----------|
| 24mm | HORIZONTAL | 5.6 | 0.504 | 0.782 | 0.154 | 0.064 | False |
| 28mm | HORIZONTAL | 6.4 | 0.458 | 0.748 | 0.189 | 0.063 | False |
| 35mm | HORIZONTAL | 8.1 | 0.390 | 0.722 | 0.193 | 0.086 | False |
| 50mm | VERTICAL | 25.6 | 0.377 | 0.845 | 0.105 | 0.050 | False |
| 55mm | VERTICAL | 28.1 | 0.376 | 0.845 | 0.103 | 0.052 | False |

## Conclusion

- framing_feasible: **False**
- Limitation: essential_set_too_wide
- Root cause: scene width (~7m / ~1.5m = 4.7:1) cannot achieve 70%+ vertical fill
  in a 9:16 portrait (0.56:1) without clipping edge objects.
- All tested lens/sensor combinations fail to simultaneously satisfy
  0 clipped objects AND ≥70% content height.
