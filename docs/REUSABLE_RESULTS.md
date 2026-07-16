# BVF Test 001 — Reusable Results

Date: 2026-07-14

---

## Preserved Capabilities

### Environment & Tools
- **Blender environment audit script** (`temp_audit.py`) — version, GPU, Python, render backend check
- **Blender 5.1 API compatibility notes**: `use_nodes` deprecation, `fcurves` access, Eevee Next attribute changes
- **FFmpeg PNG→MP4 pipeline**: frame extraction, contact sheet generation, video encoding

### Character & Animation
- **Character Root hierarchy pattern**: Root Empty + Body/Head local children. All animation on Root. Prevents detachment bugs.
- **Queue diversion animation**: Three-phase movement (step back → lateral → forward) for customer rerouting
- **Deterministic scene configuration**: `graybox_config.json` + single bpy build script = reproducible output

### Camera & Composition
- **Camera projection preflight**: `world_to_camera_view` bounding box check across key frames
- **Cross-frame composition preflight**: Union bbox across F001/F150/F345 for automated ortho_scale + shift_y calculation
- **Scan-based camera optimization**: Grid search over ortho×shift parameter space with score function
- **Ortho camera framing rules**: Top dead space ≤16%, side margins ≥5%, bottom margin ≥6%

### Rendering Pipeline
- **PNG sequence rendering**: `blender --background --python build.py` for headless render
- **Contact sheet generation**: PIL-based standard (8 frames) and dense (every 0.25s, 47 frames) sheets
- **Review board generation**: 2×2 1080p composite for human review
- **UPLOAD_NEXT pattern**: Single directory for reviewer handoff

### Project Structure
- **Phase gate documents**: INPUT.yaml, direction.json, shots.json, HUMAN_REVIEW.md
- **Stage status tracking**: AUDIT_DECISION.md → GRAYBOX_REPORT.md → STYLE_REPORT.md chain
- **Build script versioning**: v1→v4 with preserved outputs, no overwrites

### MCP Integration
- **blender-mcp**: Status reports, scene queries, script execution
- **jianying-mcp**: Draft creation, track management, text segments, export (validated but unused in this test)
- **FFmpeg CLI**: Direct pipeline as vfx-mcp replacement

## Files Worth Reusing

```
graybox_config.json         — Deterministic scene parameters
build_graybox_v3.py         — Reference for Root hierarchy pattern
build_style_v3.py           — Reference for camera optimization algorithm
temp_audit.py               — Environment check
temp_contact_sheets_v3.py   — Contact sheet generator
```
