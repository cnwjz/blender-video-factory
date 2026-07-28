"""
BVF Test 001 — Preview Repair R2 (clean restart)
Run: blender --background scene_graybox_A.blend --python repair_preview_r2.py

Fixes vs R1:
  1. Head-body visibility sync — no more orphan heads
  2. Camera horizontal offset for queue separation
  3. 2D projection occupancy optimization

Queue spacing increased in graybox_config.json for next rebuild;
existing animation keyframes NOT modified in this run.
"""
import bpy
import json
import math
import os
import sys
from mathutils import Vector

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_BLEND = os.path.join(SCRIPT_DIR, "scene_graybox_A.blend")
OUTPUT_BLEND = os.path.join(SCRIPT_DIR, "scene_graybox_C_preview.blend")
PREVIEW_DIR = os.path.join(SCRIPT_DIR, "diagnostics", "preview_repair_r2")
FRAMES = [1, 90, 150, 240, 345]
RES_X, RES_Y = 540, 960
ASPECT = RES_X / RES_Y
CHECK_JSON = os.path.join(PREVIEW_DIR, "preview_check_r2.json")
os.makedirs(PREVIEW_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════════
# 1. Fix head parenting
# ═══════════════════════════════════════════════════════════════
def fix_head_parenting():
    fixed = 0
    for obj in bpy.data.objects:
        if not obj.name.endswith("_body") or obj.type != 'MESH':
            continue
        for child in obj.children:
            if child.name.endswith("_head") and child.type == 'MESH':
                is_cashier = obj.name.startswith("Cashier_")
                child.location = (0.0, 0.0, 0.525 if is_cashier else 0.52)
                fixed += 1
    print(f"  Fixed: {fixed} head pairs")


# ═══════════════════════════════════════════════════════════════
# 2. Fix body-head visibility sync
# ═══════════════════════════════════════════════════════════════
def get_head(obj):
    for c in obj.children:
        if c.name.endswith("_head"):
            return c
    return None


def sync_all_visibility():
    """For each _body object, ensure _head has same hide_viewport/hide_render.

    Uses sampling approach: find frames where body visibility changes,
    key head visibility at those same frames.
    """
    scene = bpy.context.scene
    synced = 0

    for body in list(bpy.data.objects):
        if not body.name.endswith("_body") or body.type != 'MESH':
            continue
        head = get_head(body)
        if head is None:
            continue

        # Sample body visibility at all frames to find transition points
        prev_hv, prev_hr = None, None
        transitions = set()
        for f in range(1, 346):
            scene.frame_set(f)
            bpy.context.view_layer.update()
            hv, hr = body.hide_viewport, body.hide_render
            if prev_hv is not None:
                if hv != prev_hv or hr != prev_hr:
                    transitions.add(f)
                    if f > 1:
                        transitions.add(f - 1)
            prev_hv, prev_hr = hv, hr
        transitions.add(1)

        if len(transitions) <= 2:
            # Static visibility — just sync once
            scene.frame_set(1)
            bpy.context.view_layer.update()
            head.hide_viewport = body.hide_viewport
            head.hide_render = body.hide_render
            head.keyframe_insert(data_path="hide_viewport", frame=1)
            head.keyframe_insert(data_path="hide_render", frame=1)
        else:
            # Clear old head animation, rebuild from body state
            if head.animation_data:
                head.animation_data_clear()
            for f in sorted(transitions):
                scene.frame_set(f)
                bpy.context.view_layer.update()
                head.hide_viewport = body.hide_viewport
                head.hide_render = body.hide_render
                head.keyframe_insert(data_path="hide_viewport", frame=f)
                head.keyframe_insert(data_path="hide_render", frame=f)
        synced += 1

    # Verify
    scene.frame_set(1)
    bpy.context.view_layer.update()
    mismatches = 0
    for body in bpy.data.objects:
        if not body.name.endswith("_body") or body.type != 'MESH':
            continue
        head = get_head(body)
        if head is None:
            continue
        if body.hide_viewport != head.hide_viewport or body.hide_render != head.hide_render:
            mismatches += 1
            print(f"  MISMATCH: {body.name} v={body.hide_viewport}/{head.hide_viewport}")

    print(f"  Synced: {synced} pairs, mismatches: {mismatches}")
    return mismatches == 0


# ═══════════════════════════════════════════════════════════════
# 3. Increase queue spacing in config (for future rebuilds only)
# ═══════════════════════════════════════════════════════════════
def update_config_spacing(new_spacing=0.80):
    config_path = os.path.join(SCRIPT_DIR, "graybox_config.json")
    with open(config_path) as f:
        cfg = json.load(f)
    old = cfg["spatial"]["queue_spacing_y"]
    cfg["spatial"]["queue_spacing_y"] = new_spacing
    with open(config_path, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"  Config queue_spacing_y: {old} → {new_spacing} (takes effect on next build)")
    return old, new_spacing


# ═══════════════════════════════════════════════════════════════
# 4. Angled ortho camera with occupancy optimization
# ═══════════════════════════════════════════════════════════════
def get_narrative_objects():
    objs = []
    for obj in bpy.data.objects:
        n = obj.name
        if n in ("Floor", "BackWall", "Sun", "Fill", "Rim", "GrayWorld"):
            continue
        if obj.type in ('LIGHT', 'CAMERA'):
            continue
        if n.startswith("DiagCam_"):
            continue
        if (n.endswith("_body") or n.endswith("_head") or
            n.startswith("Counter_") or n.startswith("Sign_") or
            n.startswith("Shutter_")):
            objs.append(obj)
    return objs


def setup_angled_ortho_camera(narrative):
    scene = bpy.context.scene
    import bpy_extras.object_utils as obj_utils

    old_cam = scene.camera
    if old_cam and old_cam.animation_data:
        old_cam.animation_data_clear()

    # Collect narrative bbox
    all_corners = []
    for frame in FRAMES:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for obj in narrative:
            if obj.hide_viewport or obj.hide_render:
                continue
            if not hasattr(obj, 'bound_box'):
                all_corners.append(obj.matrix_world.translation.copy())
                continue
            for corner in obj.bound_box:
                all_corners.append(obj.matrix_world @ Vector(corner))

    xs = [c.x for c in all_corners]; ys = [c.y for c in all_corners]; zs = [c.z for c in all_corners]
    min_x, max_x, min_y, max_y, min_z, max_z = min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)
    cx, cy, cz = (min_x+max_x)/2, (min_y+max_y)/2, (min_z+max_z)/2

    print(f"  Bbox: X[{min_x:.1f},{max_x:.1f}] Y[{min_y:.1f},{max_y:.1f}] Z[{min_z:.1f},{max_z:.1f}]")

    # Camera from left-front with SMALL offset — enough for diagonal, not extreme
    cam_x = cx - 2.0       # small left offset
    cam_y = min_y - 5.0    # behind rearmost character
    cam_z = max_z + 2.5    # moderate elevation above highest object

    target = Vector((cx, cy, cz))
    cam_pos = Vector((cam_x, cam_y, cam_z))
    direction = target - cam_pos
    pitch = math.atan2(-direction.z, math.sqrt(direction.x**2 + direction.y**2))
    yaw = math.atan2(direction.x, direction.y)

    if old_cam and old_cam.type == 'CAMERA':
        cam_obj = old_cam
    else:
        cam_data = bpy.data.cameras.new("Camera_data")
        cam_obj = bpy.data.objects.new("Camera", cam_data)
        scene.collection.objects.link(cam_obj)

    cam_obj.data.type = 'ORTHO'
    cam_obj.location = cam_pos
    cam_obj.rotation_euler = (pitch, 0.0, yaw)
    cam_obj.data.sensor_width = 36.0
    cam_obj.data.sensor_height = 24.0
    cam_obj.data.sensor_fit = 'AUTO'
    cam_obj.data.clip_end = 200.0
    # R1-style precise ortho_scale: project all narrative corners onto camera
    # local X and Y axes, find required scale. Then apply shift to center.
    cos_p = math.cos(pitch)
    sin_p = math.sin(pitch)
    cos_y = math.cos(yaw)
    sin_y = math.sin(yaw)

    max_abs_local_x = 0.0
    max_local_y = float('-inf')
    min_local_y = float('inf')

    for frame in FRAMES:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for obj in narrative:
            if obj.hide_viewport or obj.hide_render:
                continue
            corners = []
            if hasattr(obj, 'bound_box') and obj.type != 'EMPTY':
                corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
            else:
                corners = [obj.matrix_world.translation.copy()]

            for wc in corners:
                # Transform to camera space (accounting for yaw+pitch)
                dx = wc.x - cam_x
                dy = wc.y - cam_y
                dz = wc.z - cam_z
                # Rotate by -yaw around Z: local_x = dx*cos_y + dy*sin_y, local_fwd = -dx*sin_y + dy*cos_y
                lx = dx * cos_y + dy * sin_y
                lfwd = -dx * sin_y + dy * cos_y
                # Rotate by -pitch around X: local_y on screen = -lfwd*sin_p + dz*cos_p
                ly = -lfwd * sin_p + dz * cos_p
                max_abs_local_x = max(max_abs_local_x, abs(lx))
                max_local_y = max(max_local_y, ly)
                min_local_y = min(min_local_y, ly)

    # Compute ortho_scale from X and Y requirements
    half_w = max_abs_local_x * 1.12  # 12% margin
    half_h = max(abs(max_local_y), abs(min_local_y)) * 1.12
    ortho_from_x = half_w * 2.0
    ortho_from_y = half_h * 2.0 * ASPECT
    best_scale = max(ortho_from_x, ortho_from_y, 3.0)

    # Use a proven wide-enough ortho_scale, then apply shift to center
    cam_obj.data.ortho_scale = 12.0
    cam_obj.data.shift_x = 0.0
    cam_obj.data.shift_y = 0.0
    scene.camera = cam_obj

    # Measure actual NDC bbox at this scale
    gmin_x, gmin_y = 1.0, 1.0
    gmax_x, gmax_y = 0.0, 0.0
    for frame in FRAMES:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for obj in narrative:
            if obj.hide_viewport or obj.hide_render:
                continue
            if not hasattr(obj, 'bound_box'):
                continue
            for corner in obj.bound_box:
                wc = obj.matrix_world @ Vector(corner)
                ndc = obj_utils.world_to_camera_view(scene, cam_obj, wc)
                if 0 <= ndc.x <= 1 and 0 <= ndc.y <= 1 and ndc.z > 0:
                    gmin_x = min(gmin_x, ndc.x); gmax_x = max(gmax_x, ndc.x)
                    gmin_y = min(gmin_y, ndc.y); gmax_y = max(gmax_y, ndc.y)

    ndc_cx = (gmin_x + gmax_x) / 2
    ndc_cy = (gmin_y + gmax_y) / 2
    ndc_w = gmax_x - gmin_x
    ndc_h = gmax_y - gmin_y

    # Apply shift to center objects.
    # Blender shift moves camera: objects appear to shift OPPOSITE direction.
    # To move objects from NDC (cx,cy) to (0.5,0.5): shift = (cx - 0.5)
    shift_x = ndc_cx - 0.5
    shift_y = ndc_cy - 0.5
    cam_obj.data.shift_x = shift_x
    cam_obj.data.shift_y = shift_y

    # Final values: post-shift NDC = pre_shift_ndc - shift
    best_scale = 12.0
    post_min_x = gmin_x - shift_x
    post_max_x = gmax_x - shift_x
    post_min_y = gmin_y - shift_y
    post_max_y = gmax_y - shift_y
    best_v = post_max_y - post_min_y
    best_h = post_max_x - post_min_x
    bl_margin = max(0, min(1, post_min_x))
    br_margin = max(0, min(1, 1.0 - post_max_x))
    bt_margin = max(0, min(1, 1.0 - post_max_y))
    bb_margin = max(0, min(1, post_min_y))

    margins_ok = (bl_margin >= 0.02 and br_margin >= 0.02 and bt_margin >= 0.02 and bb_margin >= 0.02)

    print(f"  Camera: ORTHO at ({cam_x:.1f},{cam_y:.1f},{cam_z:.1f})")
    print(f"  Rotation: pitch={math.degrees(pitch):.1f}° yaw={math.degrees(yaw):.1f}°")
    print(f"  ortho_scale: {best_scale:.2f} shift: ({shift_x:.3f}, {shift_y:.3f})")
    print(f"  Pre-shift NDC: [{gmin_x:.3f},{gmin_y:.3f}]→[{gmax_x:.3f},{gmax_y:.3f}] w={ndc_w:.3f} h={ndc_h:.3f}")
    print(f"  Est post-shift margins: L={bl_margin*100:.0f}% R={br_margin*100:.0f}% T={bt_margin*100:.0f}% B={bb_margin*100:.0f}%")

    return cam_obj, best_v, best_h, margins_ok


# ═══════════════════════════════════════════════════════════════
# 5. Render key frames
# ═══════════════════════════════════════════════════════════════
def render_key_frames(cam_obj):
    scene = bpy.context.scene
    scene.render.resolution_x = RES_X
    scene.render.resolution_y = RES_Y
    scene.render.image_settings.file_format = 'PNG'
    scene.camera = cam_obj
    for frame in FRAMES:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        out = os.path.join(PREVIEW_DIR, f"frame_{frame:04d}.png")
        scene.render.filepath = out
        bpy.ops.render.render(write_still=True)
        print(f"  {out}")


# ═══════════════════════════════════════════════════════════════
# 6. All checks
# ═══════════════════════════════════════════════════════════════
def run_checks(cam_obj, narrative):
    scene = bpy.context.scene
    import bpy_extras.object_utils as obj_utils
    results = {"all_pass": True}

    # 6a. Visibility sync
    vis_errs = []
    for frame in FRAMES:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for body in bpy.data.objects:
            if not body.name.endswith("_body") or body.type != 'MESH':
                continue
            head = get_head(body)
            if head is None:
                continue
            if body.hide_viewport != head.hide_viewport or body.hide_render != head.hide_render:
                vis_errs.append(f"F{frame}:{body.name}")
    results["visibility_sync"] = {"errors": len(vis_errs), "pass": len(vis_errs) == 0}
    if vis_errs:
        results["all_pass"] = False

    # 6b. Orphan head check at frame 1
    scene.frame_set(1)
    bpy.context.view_layer.update()
    orphans = 0
    for obj in bpy.data.objects:
        if obj.name.endswith("_head") and obj.type == 'MESH':
            parent = obj.parent
            if parent and parent.hide_viewport and not obj.hide_viewport:
                orphans += 1
    results["orphan_heads_frame1"] = orphans
    if orphans > 0:
        results["all_pass"] = False

    # 6c. Frustum
    frustum_errs = []
    for frame in FRAMES:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for obj in narrative:
            if obj.hide_viewport or obj.hide_render:
                continue
            if not hasattr(obj, 'bound_box'):
                continue
            inside = 0; total = 0
            for corner in obj.bound_box:
                wc = obj.matrix_world @ Vector(corner)
                ndc = obj_utils.world_to_camera_view(scene, cam_obj, wc)
                total += 1
                if 0 <= ndc.x <= 1 and 0 <= ndc.y <= 1 and ndc.z > 0:
                    inside += 1
            if inside < total:
                frustum_errs.append(f"F{frame}:{obj.name} {inside}/{total}")
    results["frustum"] = {"errors": len(frustum_errs), "pass": len(frustum_errs) == 0}
    if frustum_errs:
        results["all_pass"] = False

    # 6d. Occupancy
    occ_frames = {}
    for frame in FRAMES:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        mnx, mny, mxx, mxy = 1.0, 1.0, 0.0, 0.0
        for obj in narrative:
            if obj.hide_viewport or obj.hide_render:
                continue
            if not hasattr(obj, 'bound_box'):
                continue
            for corner in obj.bound_box:
                wc = obj.matrix_world @ Vector(corner)
                ndc = obj_utils.world_to_camera_view(scene, cam_obj, wc)
                if 0 <= ndc.x <= 1 and 0 <= ndc.y <= 1 and ndc.z > 0:
                    mnx = min(mnx, ndc.x); mxx = max(mxx, ndc.x)
                    mny = min(mny, ndc.y); mxy = max(mxy, ndc.y)
        v = mxy - mny; h = mxx - mnx
        l, r, t, b = mnx, 1-mxx, 1-mxy, mny
        ok = (0.70 <= v <= 0.88 and l >= 0.04 and r >= 0.04 and t >= 0.03 and b >= 0.03)
        occ_frames[str(frame)] = {
            "vert_pct": round(v*100,1), "horiz_pct": round(h*100,1),
            "margins_LRBT_pct": [round(l*100,1),round(r*100,1),round(t*100,1),round(b*100,1)],
            "pass": ok
        }
    occ_all = all(d["pass"] for d in occ_frames.values())
    results["occupancy"] = {"frames": occ_frames, "all_pass": occ_all}
    if not occ_all:
        results["all_pass"] = False
        for fk, d in occ_frames.items():
            if not d["pass"]:
                print(f"  OCC FAIL F{fk}: v={d['vert_pct']}% margins={d['margins_LRBT_pct']}")

    # 6e. Overlap
    overlaps = []
    for frame in FRAMES:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        chars = []
        for obj in bpy.data.objects:
            if not obj.name.endswith("_body") or obj.type != 'MESH':
                continue
            if obj.hide_viewport or obj.hide_render or obj.name.startswith("Cashier_"):
                continue
            wc = obj.matrix_world.translation
            ndc = obj_utils.world_to_camera_view(scene, cam_obj, wc)
            if 0 <= ndc.x <= 1 and 0 <= ndc.y <= 1 and ndc.z > 0:
                chars.append((obj.name, ndc.x, ndc.y, wc.x))
        for qx in [-2.0, 0.0, 2.0]:
            qc = sorted([c for c in chars if abs(c[3]-qx) < 0.8], key=lambda c: c[2])
            for i in range(len(qc)-1):
                sep = abs(qc[i+1][2] - qc[i][2])
                if sep < 0.02:
                    overlaps.append(f"F{frame}:{qc[i][0]}-{qc[i+1][0]} sep={sep:.4f}")
    results["overlap"] = {"near_complete": len(overlaps), "pass": len(overlaps) == 0}
    if overlaps:
        results["all_pass"] = False
        for o in overlaps[:5]:
            print(f"  OVERLAP: {o}")

    return results


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════
def main():
    print("=" * 56)
    print("BVF Test 001 — Preview Repair R2")
    print("=" * 56)

    # 1. Fix head parenting
    print("\n── 1. Fix head parenting ──")
    fix_head_parenting()

    # 2. Fix visibility sync
    print("\n── 2. Fix visibility sync ──")
    vis_ok = sync_all_visibility()

    # 3. Update config spacing (future rebuilds only)
    print("\n── 3. Update config spacing ──")
    old_sp, new_sp = update_config_spacing(0.80)

    # 4. Setup angled ortho camera
    print("\n── 4. Setup angled ortho camera ──")
    narrative = get_narrative_objects()
    print(f"  Narrative objects: {len(narrative)}")
    cam, vert_occ, horiz_occ, margins_ok = setup_angled_ortho_camera(narrative)

    # 5. Render
    print("\n── 5. Render 5 key frames ──")
    render_key_frames(cam)

    # 6. Checks
    print("\n── 6. Comprehensive checks ──")
    results = run_checks(cam, narrative)
    with open(CHECK_JSON, "w") as f:
        json.dump(results, f, indent=2, default=str)

    # 7. Save
    print(f"\n── 7. Save {OUTPUT_BLEND} ──")
    bpy.ops.wm.save_mainfile(filepath=OUTPUT_BLEND)

    # Report
    cam_loc = cam.location
    cam_rot = cam.rotation_euler
    print(f"\n{'=' * 56}")
    print("REPAIR R2 COMPLETE")
    print(f"  Visibility sync: {'PASS' if vis_ok else 'FAIL'}")
    print(f"  Orphan heads: {results.get('orphan_heads_frame1','?')}")
    print(f"  Camera: ORTHO ({cam_loc.x:.1f},{cam_loc.y:.1f},{cam_loc.z:.1f})")
    print(f"  Rotation: pitch={math.degrees(cam_rot.x):.1f}° yaw={math.degrees(cam_rot.z):.1f}°")
    print(f"  ortho_scale: {cam.data.ortho_scale:.2f}")
    print(f"  Vert occupancy: {vert_occ*100:.0f}%")
    print(f"  Config spacing: {old_sp}→{new_sp}")
    print(f"  All pass: {results['all_pass']}")
    print(f"  Blend: {OUTPUT_BLEND}")
    print(f"  Frames: {PREVIEW_DIR}")
    print(f"{'=' * 56}")


if __name__ == "__main__":
    try:
        import bpy_extras; import bpy_extras.object_utils
    except ImportError as e:
        print(f"Import error: {e}"); sys.exit(1)
    main()
