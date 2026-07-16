# Camera Azimuth Feasibility Audit

## Fixed Parameters

- Lens: 24mm, sensor_fit=HORIZONTAL
- Elevation: 25deg
- Resolution: 540x960
- Target: <Vector (-0.3935, 1.0174, 0.7482)>

## Results

| Azimuth | Dist(m) | Content H | Content W | Left | Right | Clip | Ctr OV | Emp OV | Q OV | Sep | Feasible |
|---------|---------|-----------|-----------|------|-------|------|--------|--------|------|-----|----------|
| 35deg | 6.5 | 0.272 | 0.759 | 0.181 | 0.060 | 0 | 0.000 | 0.000 | 0.000 | 0.385 | **False** |
| 45deg | 6.2 | 0.323 | 0.752 | 0.181 | 0.067 | 0 | 0.000 | 0.000 | 0.028 | 0.340 | **False** |
| 55deg | 5.7 | 0.399 | 0.733 | 0.183 | 0.084 | 0 | 0.016 | 0.001 | 0.110 | 0.347 | **False** |
| 65deg | 5.4 | 0.483 | 0.730 | 0.197 | 0.074 | 0 | 0.049 | 0.112 | 0.181 | 0.265 | **False** |
| 75deg | 5.2 | 0.534 | 0.799 | 0.108 | 0.092 | 0 | 0.106 | 0.160 | 0.226 | 0.132 | **False** |

## Conclusion

- azimuth_framing_feasible: **False**
- Primary limitation: **height_target_unreachable**
