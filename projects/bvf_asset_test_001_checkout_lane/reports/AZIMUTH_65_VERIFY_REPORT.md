# AZIMUTH 65 EXACT VERIFY Report

## Camera Parameters (Reopen Verified)

| Parameter | Target | Actual | Pass |
|-----------|--------|--------|------|
| Lens | 24mm | 24mm | ✓ |
| Azimuth | 65° | 65.00° | ✓ |
| Elevation | 25° | 25.00° | ✓ |
| Distance | 5.4m | 5.4000m | ✓ |
| Sensor fit | HORIZONTAL | HORIZONTAL | ✓ |
| Resolution | 540×960 | 540×960 | ✓ |

## Projection (evaluated mesh vertices → NDC)

| Metric | Value |
|--------|-------|
| Content height | 47.88% |
| Content width | 72.55% |
| Left margin | 19.78% |
| Right margin | 7.67% |
| Top margin | 39.39% |
| Bottom margin | 12.73% |
| Clipped objects | 0 |

Height ~48.3% confirmed: YES (diff = 0.004)

## File Verification

| File | Size | SHA256 |
|------|------|--------|
| AZIMUTH_65_CLEAN.png | 540×960 | 05f5016cf0b21e2372991fb17585c7119125ba5557aea041736325442a5e7d0b |
| AZIMUTH_65_DEBUG.png | 540×960 | a34b84e397cc669870582fd150bfa9c63423acb19cd082409f5157337e109c7a |

Both created from same render pass. Debug overlay shows the exact NDC bbox used for projection calculation.

## Scene

- Input: L1_step02_checkout_final.blend
- Output: CAMERA_AZIMUTH_65_EXACT_VERIFY.blend
- Save-reopen: passed (all params preserved)
