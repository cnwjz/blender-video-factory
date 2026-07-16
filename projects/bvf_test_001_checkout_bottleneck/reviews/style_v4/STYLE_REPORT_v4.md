# Style Report v4 — Final Publication Threshold Test

Date: 2026-07-14 | Phase: 4D

## Camera (Locked from V3)

| ortho_scale | shift_y | Type |
|-------------|---------|------|
| 6.90 | -0.26 | ORTHO, 50 deg |

## Preflight

| Frame | Top Empty | 0 Clipped | Pass |
|-------|-----------|-----------|------|
| F001 | 15.1% | 0 | PASS |
| F090 | 10.8% | 0 | PASS |
| F150 | 10.8% | 0 | PASS |
| F345 | 10.8% | 0 | PASS |

## V4 Changes from V3

1. **Cashier height**: Root Z raised to counter surface level. Cashiers now visible (head + torso above counter). Legs hidden behind counter. No "legs poking out" effect.
2. **Rim light**: Added overhead contour sun light for character-ground separation.
3. **Shutter**: Thicker (0.05 vs 0.03), taller (0.75 vs 0.7), rougher material. More visible warm orange.
4. **Character colors**: 5 distinct low-saturation clothing colors with body/head contrast.

## Color Rules (Enforced)

- Warm orange #EB6B21: MIDDLE SHUTTER ONLY
- Left/right counters: warm gray-beige (no orange)
- Character skin: warm beige
- Clothes: 5 muted earth tones, no high-saturation colors

## Output

- `scene_style_v4_final_test.blend` (saved as `scene_style_v4.blend`)
- `reviews/style_v4/F001-F345_style_v4.png`
- `reviews/UPLOAD_NEXT/review_board_style_v4.png`
