# Kenney Character Import & Animation Audit

Date: 2026-07-14

---

## 1. Animation Validation

4-panel board at `UPLOAD_NEXT/character_animation_validation_board.png`

| Panel | Action | Frames | Character | Result |
|-------|--------|--------|-----------|--------|
| Top-left | `root\|idle` | 1-82 | male-a | Plays correctly — breathing idle loop |
| Top-right | `root\|walk` | 1-42 | male-a | Plays correctly — **in-place cycle** |
| Bottom-left | `root\|static` | 1-7 | employee | Static pose, correct counter position |
| Bottom-right | idle + static | — | female-a + employee | Both visible, proper scale |

## 2. Walk Motion Analysis

**Walk is an in-place cycle.** The Armature animates locally — the Empty root does not translate. Tested: Empty position at frame 1 = (0, -0.3, 0), frame 30 = (0, -0.3, 0). No root motion displacement.

**Implication**: Customer walking must be driven by animating the Empty root's `location` while the Armature plays `root|walk`, producing a natural walk-with-displacement effect.

## 3. FBX Hierarchy (confirmed across all imports)

```
[E] character-male-a (Empty root)  ← MOVE + SCALE HERE ONLY
  [A] root (Armature, 6 bones)    ← ANIMATION ACTION HERE
    [M] body-mesh (298 verts)
    [M] head-mesh (191 verts)
```

## 4. Stray Object Cleanup

- GLB import: Creates stray Icosphere (orphaned, no parent) — deleted automatically on import
- FBX import: Clean hierarchy with no orphans
- **Rule: Use FBX exclusively for all character imports**

## 5. Import Rules (locked)

1. All characters: use FBX from `Models/FBX format/`
2. Props/environment: use GLB from `Models/GLB format/` (no stray objects for props)
3. On FBX import, delete any stray Icosphere meshes with no parent
4. All world transforms go on the top-level Empty
5. Animation Actions go on the Armature
6. Never set world position on body-mesh or head-mesh directly

## 6. Available Animations (32 total)

| Action | Frames | Type | Use |
|--------|--------|------|-----|
| `root\|static` | 1-7 | Static pose | Standing customers, cashiers |
| `root\|idle` | 1-82 | In-place loop | Waiting/breathing |
| `root\|walk` | 1-42 | In-place cycle | Walking (with Empty displacement) |
| `root\|sprint` | 1-31 | In-place cycle | Fast walking |
| `root\|crouch` | 1-12 | Static | Bending down |
| `root\|emote-yes` | 1-42 | In-place | Nodding |
| `root\|emote-no` | 1-42 | In-place | Head shake |
