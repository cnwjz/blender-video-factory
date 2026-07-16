# Low Poly Miniature Visual Look — Report v1

Date: 2026-07-14
Phase: Stage 4A (Visual Style Development — 4 Frames Only)

---

## 1. Style Direction

```
Low Poly Miniature Supermarket Checkout
Warm-tone, geometric, readable at thumbnail scale
Target: recognizable as a designed 3D short, not Blender default
```

## 2. Geometry Changes from V4 Graybox

| Element | Graybox (V4) | Style (V1) |
|---------|-------------|-----------|
| Characters | Cylinder + sphere | Ico-sphere head, cube torso, cylinder legs/arms |
| Counter | Plain cube | Beveled cube + conveyor belt strip + scanner bump |
| Signboard | Simple cube | Wide signboard with emission glow |
| Shutter | Dark gray cube | Warm orange thin slab |
| Floor | Flat gray plane | Warm dark uniform plane |
| Background | Single wall | Wall + 2 shelf silhouette groups |
| Queue stripes | Gray planes | Removed (not needed with styled scene) |

## 3. Color Palette

| Surface | Color | Purpose |
|---------|-------|--------|
| Wall | Warm charcoal #2A241E | Background |
| Floor | Warm dark gray #383330 | Ground |
| Counter body | Cream #D4C8B8 | Main architecture |
| Conveyor belt | Dark brown-gray #3B3530 | Checkout detail |
| Scanner | Dark gray #595450 | POS detail |
| Active signboard | Warm cream #F5E6D0 (emissive) | Open window |
| Off signboard | Near-black #1A1816 | Closed window |
| Shutter (closed) | Warm orange #E87830 | Closure signal |
| Shelf frame | Warm dark #47403A | Background context |
| Character skin | Warm beige #BFAE99 | Unified skin tone |
| Character clothes | 5 muted earth tones | Customer variety |
| Cashier | Lighter top, darker pants | Role distinction |

**Warm orange used EXCLUSIVELY on the closed middle window shutter.** No high-saturation blue, green, or purple anywhere.

## 4. Lighting

| Light | Type | Energy | Color | Purpose |
|-------|------|--------|-------|---------|
| Sun | Directional | 2.8 | Warm (1.0, 0.95, 0.88) | Main key light, soft shadows |
| Fill | Area | 1.5 | Cool-neutral (0.85, 0.85, 0.90) | Subtle fill |
| World | Background | 0.15 | Warm dark (0.25, 0.22, 0.20) | Ambient base |

- Soft shadows enabled with large sun angle
- No AO (Blender 5.1 Eevee Next API differs)

## 5. Camera

- Type: Orthographic (same as V4)
- ortho_scale: 9.2
- Resolution: 1080×1920 (up from 540×960)
- Same framing as V4 graybox

## 6. Four Test Frames

| Frame | Time | Content |
|-------|------|---------|
| F001 | 0.0s | Three open windows, three short queues, supermarket context |
| F090 | 3.0s | Middle closed: warm orange shutter, dark sign, cashier hidden |
| F150 | 5.0s | Characters mid-diversion, low-poly humanoids visible |
| F345 | 11.5s | Final congestion: two long queues, empty middle, closed shutter |

## 7. Known Issues

1. **Character recognizability**: Ico-sphere heads + cube torsos are more humanoid than V4 cylinders but may still read as abstract. Pending visual review.
2. **Shelf silhouettes**: Only 2 shelf groups added as background context. More may be needed for supermarket recognizability.
3. **Floor tile pattern**: Not implemented yet (uniform floor). Can add checker/tile in next iteration.
4. **No AO**: Blender 5.1 Eevee Next doesn't have `use_gtao`. Contact shadows between characters and floor may be weaker than desired.

## 8. Animation Preservation

- All V4 animation preserved: Root empties, keyframes, timing unchanged
- Character meshes replaced on same Roots — no animation data modified
- Window close: F61-F90, diversion: F106-F180, final hold: F321-F345

## 9. Decision

**Pending human review** of `reviews/style_v1/F*.png` and `contact_sheet_style_v1.png`.
