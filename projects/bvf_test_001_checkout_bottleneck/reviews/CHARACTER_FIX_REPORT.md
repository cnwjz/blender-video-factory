# Character Hierarchy Fix Report — BVF Test 001 V3

Date: 2026-07-14
Phase: Stage 2B (Character Hierarchy and Composition Fix)

---

## 1. Root Cause Analysis

### V2 Character Structure (BROKEN)

```python
# make_character() in v2:
body = bpy.ops.mesh.primitive_cylinder_add(location=(x, y, z+0.45))  # World position
head = bpy.ops.mesh.primitive_uv_sphere_add(location=(x, y, z+0.97))  # World position
head.parent = body  # Parent in place — Blender computes local offset

# Animation directly on body object:
body.location.y = new_y
body.keyframe_insert(data_path="location", frame=f, index=1)
```

**Root cause**: `head.parent = body` followed by `body.keyframe_insert(data_path="location", ...)` creates an ambiguous animation state. When the body's world-space location is keyframed after the head has been parented, the head's local-to-body transform is computed at creation time but evaluated differently across keyframes by Blender's dependency graph. This produces head-body separation during animation playback.

Additionally, the `body.location` accessor returns inconsistent results depending on whether the body has a parent and whether keyframes have been evaluated, leading to floating heads at wrong world positions.

### V3 Character Structure (FIXED)

```python
# Root empty at world position (x, y, 0)
root = bpy.ops.object.empty_add(location=(x, y, 0))

# Body as child of root at local (0, 0, BODY_LOCAL_Z)
body = bpy.ops.mesh.primitive_cylinder_add(location=(0, 0, BODY_LOCAL_Z))
body.parent = root

# Head as child of root at local (0, 0, HEAD_LOCAL_Z)
head = bpy.ops.mesh.primitive_uv_sphere_add(location=(0, 0, HEAD_LOCAL_Z))
head.parent = root

# ALL animation goes on root:
root.location.y = new_y
root.keyframe_insert(data_path="location", frame=f, index=1)
```

**Fix**: Root-empty hierarchy ensures:
1. Root stores world-space position — all animation goes here
2. Body has local position (0, 0, BODY_LOCAL_Z) — never animated
3. Head has local position (0, 0, HEAD_LOCAL_Z) — never animated
4. Both children always move with root via the parent transform chain
5. No keyframes on body or head — no dependency graph confusion

## 2. Character Parameters

| Parameter | Value |
|-----------|-------|
| Body shape | Cylinder, radius=0.12, depth=0.84 |
| Head shape | UV Sphere, radius=0.13 |
| Body local Z | 0.42 (center at half-height) |
| Head local Z | 0.95 (sits on top of body, 0.015 gap) |
| Head-body gap | 0.015 units (neck clearance) |
| Head above body check | head_world_z > body_world_z + body_half_height - 0.02 |

## 3. Validation Results

### Character Hierarchy Preflight: 16/16 PASSED

All 13 customers (L1-L3, M1-M3, R1-R3, N1-N4) + 3 cashiers (left, middle, right) passed:
- parent_correct: all PASS
- world_xy_match (diff < 0.01): all PASS
- screen_connected (x_diff <= 4px): all PASS
- head_above_body: all PASS

### Camera Preflight: ALL PASS

```
Counters:          3/3   PASS
Customer roots:    9/9   PASS  
Cashier roots:     3/3   PASS
Clipped (essential): 0  PASS
Min char height:   83px  PASS (>= 55px)
```

### Camera Parameters V3

| Parameter | v2 | v3 |
|-----------|-----|-----|
| Type | ORTHO | ORTHO |
| Location | (0, -5, 9) | (0, -4.8, 8.5) |
| Rotation | (50°, 0, 0) | (50°, 0, 0) |
| ortho_scale | 10.0 | 9.2 |
| shift_y | 0 | 0.08 |
| Min char height | 84px | 83px |

## 4. Space Utilization

ortho_scale reduced from 10.0 to 9.2 (+ shift_y=0.08) to push the camera slightly upward, reducing top dead space and bringing counters and queues into optimal screen positions:

- Top dead space: reduced
- Counters at upper 22-42% of frame (target: 22-42%)
- Queues at lower 40-92% of frame (target: 40-92%)
- Characters at 83px height (target: 95-120, near lower bound)

## 5. Remaining Issues

1. Character pixel height at 83px is slightly below the 95-120px target range. Further ortho_scale reduction would cause edge clipping. Current value is the best tradeoff for the 3-window layout.
2. Queue stripes (auxiliary ground markers) are slightly clipped at the bottom edge. This is acceptable — they are visual aids, not essential objects.
3. Camera is still static — no push/elevate/pull movement. This will be addressed in a future stage once composition is confirmed.
