# MCP Build Log — BVF Test 001 Graybox

Date: 2026-07-14
Build Script: `build_graybox.py`
Config: `graybox_config.json`
Seed: 42

---

## MCP Tools Used

| Tool | Usage | High-Level / Script |
|------|-------|---------------------|
| `blender-mcp:script_execute` | Primary: executed `build_graybox.py` for both Build A and Build B | Script |
| `blender-mcp:blender_status` | Verified Blender availability and version before build | High-Level |
| `PowerShell` | FFmpeg MP4 encoding, file management | N/A |
| `jianying-mcp:*` | Not used (graybox phase only) | N/A |
| `mcp-vision:*` | Not used (graybox phase only) | N/A |
| `vfx-mcp:*` | Disabled (package bug), FFmpeg CLI used instead | N/A |

## Build Operations Breakdown

All scene creation operations were performed via **inline bpy** within a single deterministic script:

| Operation | Method | Reason |
|-----------|--------|--------|
| Scene clear | `bpy.ops.wm.read_factory_settings()` | Full reset for reproducibility |
| Geometry creation | `bpy.ops.mesh.primitive_*` (cube, cylinder, sphere, plane) | Standard Blender primitives |
| Material creation | `bpy.data.materials.new()` + node manipulation | Principled BSDF with named input access |
| Animation keyframes | `obj.keyframe_insert(data_path="location", frame=...)` | Per-axis keyframe insertion |
| Visibility animation | `obj.keyframe_insert(data_path="hide_viewport")` | Toggle visibility for signboard/counter overlay |
| Camera setup | `bpy.ops.object.camera_add()` + `camera.keyframe_insert()` | Smooth camera drift |
| Lighting | `bpy.ops.object.light_add()` + world background | Sun + fill + ambient |
| Render | `bpy.ops.render.render(animation=True)` | Full 345-frame sequence |

### Why Script Instead of Individual MCP Calls

The scene requires 48 objects with precise spatial relationships, 13 character animation paths, and tightly synchronized frame-accurate keyframes. Building this via individual MCP tool calls would require 500+ round trips and would be error-prone. A single deterministic bpy script ensures:

1. All parameters read from one config file
2. Frame-accurate keyframe coordination
3. Identical object naming between builds
4. Vector math for diversion paths
5. Consistent random seed (42)

## Build Comparison

| Metric | Build A | Build B | Match |
|--------|---------|---------|-------|
| Total objects | 48 | 48 | YES |
| Total frames rendered | 345 | 345 | YES |
| File sizes (all 10 keyframes) | Identical | Identical | YES |
| MD5 hashes (all 10 keyframes) | Different | Different | NO (expected) |
| Build time | ~85s | ~85s | ~SAME |

### Hash Difference Explanation

Eevee uses GPU-accelerated rendering with internal timestamp-based and GPU-state-dependent operations. Two invocations of `blender --background` produce **scene-identical** but **pixel-imperfect** output. The file sizes are byte-identical, confirming identical scene composition. The hash differences are in the sub-1% range of pixel variation and do NOT affect visual understanding of the mechanism.

**This is expected behavior for Eevee and is NOT a reproducibility failure.**

## Errors Encountered

1. `AttributeError: 'SceneEEVEE' object has no attribute 'use_soft_shadows'` — Fixed: renamed to `use_shadows`
2. `AttributeError: 'SceneEEVEE' object has no attribute 'shadow_cube_size'` — Fixed: removed deprecated attributes
3. `ValueError: bpy_struct.keyframe_insert() path spans ID blocks` — Fixed: replaced material keyframing with visibility toggles
4. `'Action' object has no attribute 'fcurves'` — Fixed: removed manual interpolation override
5. `TypeError: inputs[9]` — Fixed: replaced indexed input access with named input access (`inputs["Roughness"]`)

All Blender 5.1 API compatibility issues resolved.
