# Style Report v3 — Phase 4C

Date: 2026-07-14

## Camera

| Parameter | v2 | v3 |
|-----------|-----|-----|
| ortho_scale | 7.9 | 6.90 |
| shift_y | 0.11 | -0.30 |
| Method | Manual guess | Scan-based bbox optimization |

**Frame | top_empty | bot_margin | clipped | PASS**
F1 | 0.111 | 0.331 | 0 | PASS
F90 | 0.111 | 0.355 | 0 | PASS
F150 | 0.111 | 0.299 | 0 | PASS
F345 | 0.111 | 0.255 | 0 | PASS

Top dead space: 11.1% (target 10-16%). All frames pass preflight.

## Color Fix

- Warm orange (#E56B21) used ONLY on middle shutter
- Left/right counters: warm gray-beige (#CCC2B3) — no orange
- Left/right shutters never visible (stay above counter)

## Supermarket Recognition

- Products added to left conveyor: 2 boxes + 1 bottle
- Products added to right conveyor: 1 box + 1 bottle
- All products in muted beige/brown tones
- No orange on products
- Middle conveyor remains empty (closed window)

## Character & Animation

- All V4 animation preserved unchanged
- Low-poly characters with apron for cashiers
- 13 customers + 3 cashiers via Root hierarchy

## Preflight

Full preflight JSON at `composition_preflight_v3.json`. All 4 frames passed.
