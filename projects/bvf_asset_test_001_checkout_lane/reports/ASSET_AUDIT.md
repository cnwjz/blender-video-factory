# Asset Audit — A1 Smoke Test Results

Date: 2026-07-14 | Status: asset_smoke_testing

---

## A1 Smoke Test: PASSED

### Test Configuration

| Item | Asset | Format | Result |
|------|-------|--------|--------|
| Customer | character-male-a | GLB | PASS |
| Customer variant | character-female-a | GLB | PASS |
| Customer variant 2 | character-male-b | GLB | PASS |
| Cashier | character-employee | GLB | PASS |
| Register | cash-register | GLB | PASS |
| Bread display | display-bread | GLB | PASS |
| Fruit display | display-fruit | GLB | PASS |
| Freezer | freezer | GLB | PASS |
| Floor | floor | GLB | PASS |

### Compatibility Checks

| Check | Result |
|-------|--------|
| GLB import in Blender 5.1 | All 9 assets PASS |
| Materials preserved | Yes (colormap textures) |
| Normals correct | Yes |
| Eevee shadows | Yes |
| Mesh integrity | No missing faces |
| Vertex count (total) | 8,129 (23 meshes) |
| Scene objects | 30 |
| Unique materials | 10 |
| Texture resolution | 256px (Kenney Mini default) |

### Style Consistency

All assets belong to the **Kenney Mini** series:
- Same texture resolution (256px)
- Same material system (single colormap)
- Same poly density (~300-1,200 verts per asset)
- Same flat-shaded low-poly aesthetic
- Characters and environment share visual language

**Style consistency: PASSED**

### Character Assessment

- Static meshes (no rigging, no animations)
- Body + head as separate objects
- Can be combined under a Root Empty for positioning/animation
- Can use different gender variants for customer variety
- Employee character has distinct uniform appearance
- Scale appears consistent across all character variants

### Limitations Found

1. **No rigging**: Characters are static meshes — no built-in walk cycles or pose animations
2. **Single-pose**: Each character variant has one fixed pose
3. **No conveyor belt**: Mini Market lacks checkout-specific belt/counter — will proxy with native geometry or door/fence elements
4. **Low texture resolution**: 256px colormaps are stylistically consistent but limit close-up detail

## Decision

**A1 Smoke Test PASSED.** All Kenney Mini assets import cleanly in Blender 5.1 GLB format. Style is unified. Ready for A2 lookdev phase with these assets.
