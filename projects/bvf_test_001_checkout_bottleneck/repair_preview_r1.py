"""
BVF Test 001 — Preview Repair R1
Run: blender --background scene_graybox_A.blend --python repair_preview_r1.py

Fixes:
  1. Head parenting: sets local position after parent (was doubling world coords)
  2. Camera: replaces animated PERSP camera with fixed ORTHO oblique camera
  3. Renders 5 key frames to diagnostics/preview_repair_r1/
  4. Saves as scene_graybox_B_preview.blend

Does NOT modify scene_graybox_A.blend.
"""
import bpy
import json
import math
import os
import sys
from mathutils import Vector

# ── Config ───────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_BLEND = os.path.join(SCRIPT_DIR, "scene_graybox_A.blend")
OUTPUT_BLEND = os.path.join(SCRIPT_DIR, "scene_graybox_B_preview.blend")
PREVIEW_DIR = os.path.join(SCRIPT_DIR, "diagnostics", "preview_repair_r1")
FRAMES = [1, 90, 150, 240, 345]
RES_X, RES_Y = 540, 960
CHECK_JSON = os.path.join(PREVIEW_DIR, "frustum_check_r1.json")
os.makedirs(PREVIEW_DIR, exist_ok=True)

# ── 1. Fix head parenting ────────────────────────────────────
def fix_character_head(body_obj, head_z_offset):
    """Fix head local position after parent to body.

    ROOT CAUSE: build_graybox.py make_character() created head at
    absolute world (x, y, z+head_z) then called head.parent = body
    without setting head.location. Blender's parent inverse matrix
    preserved original world coords as local offset, causing
    head world = body world + original_world → doubled X and Y.

    Fix: set head.location to local coords relative to body center.
    """
    for child in body_obj.children:
        if child.name.endswith("_head") and child.type == 'MESH':
            # Set local position: head should be directly above body
            # body origin is at geometric center (half depth from base)
            # head local: (0, 0, head_offset) relative to body origin
            child.location = (0.0, 0.0, head_z_offset)
            print(f"  Fixed: {child.name} parent={body_obj.name} "
                  f"local=({child.location.x:.3f}, {child.location.y:.3f}, {child.location.z:.3f})")


def fix_all_heads():
    """Find all character and cashier body objects, fix their head children."""
    fixed = 0
    for obj in bpy.data.objects:
        name = obj.name
        # Character bodies: L1_body, M2_body, R3_body, N4_body
        if name.endswith("_body") and obj.type == 'MESH':
            has_head = any(c.name.endswith("_head") for c in obj.children)
            if has_head:
                # Determine head Z offset based on body type
                # Character body: cylinder radius=0.15 depth=0.9 → top at z=0.45,
                #   head placed at z+0.97 → offset = 0.52 from body origin
                # Cashier body: cylinder radius=0.16 depth=0.95 → top at z=0.475,
                #   head placed at z+1.0 → offset = 0.525 from body origin
                is_cashier = name.startswith("Cashier_")
                if is_cashier:
                    # Body center at 0.475, head at 1.0 → offset = 0.525
                    z_off = 0.525
                else:
                    # Body center at 0.45, head at 0.97 → offset = 0.52
                    z_off = 0.52
                fix_character_head(obj, z_off)
                fixed += 1
    print(f"Fixed {fixed} character/cashier head hierarchies")


# ── 2. Fix camera ────────────────────────────────────────────
def compute_narrative_bbox(frames):
    """Compute union world bbox of all narrative objects across key frames.

    Narrative objects: customer bodies+heads, cashier bodies+heads,
    counters, signs, shutters. Excludes Floor, BackWall, lights, cameras.
    """
    scene = bpy.context.scene
    all_corners = []

    # Identify narrative objects by name pattern
    narrative = []
    for obj in bpy.data.objects:
        n = obj.name
        if n in ("Floor", "BackWall", "Sun", "Fill", "Rim", "GrayWorld"):
            continue
        if obj.type == 'LIGHT' or obj.type == 'CAMERA':
            continue
        if n.startswith("DiagCam_"):
            continue
        # Include: *_body, *_head, Counter_*, Sign_*, Shutter_*
        if (n.endswith("_body") or n.endswith("_head") or
            n.startswith("Counter_") or n.startswith("Sign_") or
            n.startswith("Shutter_")):
            narrative.append(obj)

    print(f"Narrative objects for bbox: {len(narrative)}")

    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()

        for obj in narrative:
            if obj.hide_viewport or obj.hide_render:
                continue
            if not hasattr(obj, 'bound_box') or obj.type == 'EMPTY':
                loc = obj.matrix_world.translation
                all_corners.append(loc)
                continue
            for corner in obj.bound_box:
                wc = obj.matrix_world @ Vector(corner)
                all_corners.append(wc)

    if not all_corners:
        return None, None

    xs = [c.x for c in all_corners]
    ys = [c.y for c in all_corners]
    zs = [c.z for c in all_corners]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)), narrative


def setup_fixed_ortho_camera(bbox, narrative):
    """Create fixed orthographic camera covering the narrative bbox.

    Target framing:
      - Upper 25-35%: counters + window status (Y >= counter area)
      - Lower 65-75%: customer queues and movement area
    """
    scene = bpy.context.scene

    # Remove old camera animation
    old_cam = scene.camera
    if old_cam and old_cam.animation_data:
        old_cam.animation_data_clear()
        print(f"Cleared animation on: {old_cam.name}")

    min_x, max_x, min_y, max_y, min_z, max_z = bbox
    span_x = max_x - min_x
    span_y = max_y - min_y
    span_z = max_z - min_z

    cx = (min_x + max_x) / 2
    cy = (min_y + max_y) / 2
    cz = (min_z + max_z) / 2

    print(f"Narrative bbox: X[{min_x:.2f}, {max_x:.2f}] Y[{min_y:.2f}, {max_y:.2f}] Z[{min_z:.2f}, {max_z:.2f}]")
    print(f"  Center: ({cx:.2f}, {cy:.2f}, {cz:.2f})")
    print(f"  Span: X={span_x:.2f} Y={span_y:.2f} Z={span_z:.2f}")

    # Ortho camera from oblique above.
    # Strategy: position camera, aim at narrative bbox center, then compute
    # ortho_scale precisely from the max projection of all bbox corners onto
    # the camera's local Y axis (vertical on screen) and X axis.
    cam_x = cx
    # Place behind and above the scene at a moderate distance
    cam_y = min_y - 3.0
    cam_z = max_z + 4.0

    # Aim at bbox center
    target_y = cy
    target_z = cz
    dy = target_y - cam_y
    dz = target_z - cam_z
    pitch_rad = math.atan2(-dz, dy)
    pitch_deg = math.degrees(pitch_rad)

    # Convert old camera
    if old_cam and old_cam.type == 'CAMERA':
        cam_obj = old_cam
    else:
        cam_data = bpy.data.cameras.new("Camera_data")
        cam_obj = bpy.data.objects.new("Camera", cam_data)
        scene.collection.objects.link(cam_obj)

    cam_obj.data.type = 'ORTHO'
    cam_obj.location = (cam_x, cam_y, cam_z)
    cam_obj.rotation_euler = (pitch_rad, 0.0, 0.0)

    # Compute camera local axes
    cos_p = math.cos(pitch_rad)
    sin_p = math.sin(pitch_rad)
    # Camera local X = world X (1,0,0) — horizontal on screen
    # Camera local Y = (0, -sin_p, cos_p) — vertical on screen (up)
    # Camera local Z = (0, cos_p, sin_p) — view direction (forward)

    aspect = RES_X / RES_Y  # 0.5625

    # Collect all narrative bbox corners across all frames, project onto
    # camera local X and Y to find required ortho_scale
    scene.frame_set(FRAMES[0])
    bpy.context.view_layer.update()

    max_abs_local_x = 0.0
    max_local_y = float('-inf')
    min_local_y = float('inf')

    for frame in FRAMES:
        scene.frame_set(frame)
        bpy.context.view_layer.update()

        for obj in narrative:
            if obj.hide_viewport or obj.hide_render:
                continue
            if not hasattr(obj, 'bound_box'):
                wc = obj.matrix_world.translation
                # Project world coords to camera local
                rx = wc.x - cam_x  # local X = world X (simplified for pure pitch rotation)
                ry = -(wc.y - cam_y) * sin_p + (wc.z - cam_z) * cos_p
                max_abs_local_x = max(max_abs_local_x, abs(rx))
                max_local_y = max(max_local_y, ry)
                min_local_y = min(min_local_y, ry)
                continue

            for corner in obj.bound_box:
                wc = obj.matrix_world @ Vector(corner)
                # Project to camera local coords (camera has only pitch rotation)
                rx = wc.x - cam_x
                ry = -(wc.y - cam_y) * sin_p + (wc.z - cam_z) * cos_p
                max_abs_local_x = max(max_abs_local_x, abs(rx))
                max_local_y = max(max_local_y, ry)
                min_local_y = min(min_local_y, ry)

    # Required ortho_scale from X: need 2*max_abs_local_x visible width
    ortho_from_x = max_abs_local_x * 2.0 * 1.10  # 10% margin

    # Required ortho_scale from Y: visible height = ortho_scale/aspect
    # need to cover from min_local_y to max_local_y
    half_height_needed = max(abs(max_local_y), abs(min_local_y)) * 1.10
    full_height_needed = half_height_needed * 2.0
    ortho_from_y = full_height_needed * aspect

    ortho_scale = max(ortho_from_x, ortho_from_y, 1.0)

    cam_obj.data.ortho_scale = round(ortho_scale, 2)
    cam_obj.data.sensor_width = 36.0
    cam_obj.data.sensor_height = 24.0
    cam_obj.data.sensor_fit = 'AUTO'
    cam_obj.data.clip_end = 200.0
    cam_obj.data.shift_x = 0.0
    cam_obj.data.shift_y = 0.0

    scene.camera = cam_obj

    visible_h = cam_obj.data.ortho_scale / aspect
    print(f"Camera: ORTHO at ({cam_x:.2f}, {cam_y:.2f}, {cam_z:.2f})")
    print(f"  Rotation: ({pitch_deg:.1f}°, 0°, 0°)")
    print(f"  ortho_scale: {cam_obj.data.ortho_scale:.2f}")
    print(f"  Visible world height: {visible_h:.2f}")
    print(f"  Max local Y range: [{min_local_y:.2f}, {max_local_y:.2f}]")
    print(f"  Max abs local X: {max_abs_local_x:.2f}")

    return cam_obj


# ── 3. Render key frames ─────────────────────────────────────
def render_key_frames(cam_obj):
    """Render only the 5 key frames."""
    scene = bpy.context.scene
    scene.render.resolution_x = RES_X
    scene.render.resolution_y = RES_Y
    scene.render.image_settings.file_format = 'PNG'
    scene.camera = cam_obj

    for frame in FRAMES:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        out_path = os.path.join(PREVIEW_DIR, f"frame_{frame:04d}.png")
        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        print(f"  Rendered: {out_path}")


# ── 4. Frustum check ─────────────────────────────────────────
def run_frustum_check(cam_obj):
    """Check all narrative objects are in camera frustum at each key frame."""
    scene = bpy.context.scene
    import bpy_extras.object_utils as obj_utils

    results = {}
    all_pass = True

    for frame in FRAMES:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        fd = {"frame": frame, "objects": {}}

        for obj in bpy.data.objects:
            n = obj.name
            if n in ("Floor", "BackWall", "Sun", "Fill", "GrayWorld"):
                continue
            if obj.type in ('LIGHT', 'CAMERA'):
                continue
            if not (n.endswith("_body") or n.endswith("_head") or
                    n.startswith("Counter_") or n.startswith("Sign_") or
                    n.startswith("Shutter_")):
                continue

            if obj.hide_viewport or obj.hide_render:
                fd["objects"][n] = "HIDDEN"
                continue

            if not hasattr(obj, 'bound_box'):
                continue

            inside = 0
            total = 0
            for corner in obj.bound_box:
                wc = obj.matrix_world @ Vector(corner)
                v = obj_utils.world_to_camera_view(scene, cam_obj, wc)
                total += 1
                if 0.0 <= v.x <= 1.0 and 0.0 <= v.y <= 1.0 and v.z > 0:
                    inside += 1

            if inside == 0:
                status = "OUTSIDE"
                all_pass = False
            elif inside == total:
                status = "FULLY_INSIDE"
            else:
                status = "PARTIALLY_INSIDE"
                all_pass = False

            fd["objects"][n] = status

        results[str(frame)] = fd

    results["all_pass"] = all_pass
    return results


def check_head_body_alignment():
    """Verify head world X/Y match body, head Z > body Z."""
    errors = []
    for obj in bpy.data.objects:
        if not obj.name.endswith("_body") or obj.type != 'MESH':
            continue
        for child in obj.children:
            if not child.name.endswith("_head"):
                continue
            bw = obj.matrix_world.translation
            hw = child.matrix_world.translation
            dx = abs(hw.x - bw.x)
            dy = abs(hw.y - bw.y)
            if dx > 0.01 or dy > 0.01:
                errors.append(f"{child.name}: dx={dx:.4f} dy={dy:.4f} (FAIL)")
            elif hw.z <= bw.z:
                errors.append(f"{child.name}: head_z={hw.z:.4f} <= body_z={bw.z:.4f} (FAIL)")
            else:
                print(f"  OK: {child.name} body=({bw.x:.2f},{bw.y:.2f},{bw.z:.2f}) "
                      f"head=({hw.x:.2f},{hw.y:.2f},{hw.z:.2f})")

    if errors:
        print(f"\nHEAD/BODY ALIGNMENT ERRORS: {len(errors)}")
        for e in errors:
            print(f"  {e}")
    else:
        print(f"\nALL HEADS ALIGNED: 0 errors")
    return len(errors) == 0


# ── Main ─────────────────────────────────────────────────────
def main():
    print("=" * 56)
    print("BVF Test 001 — Preview Repair R1")
    print("=" * 56)

    scene = bpy.context.scene
    print(f"Scene: {scene.name}")

    # Step 1: Fix head parenting
    print("\n── Step 1: Fix head parenting ──")
    fix_all_heads()

    # Verify
    bpy.context.view_layer.update()
    head_ok = check_head_body_alignment()

    # Step 2: Compute narrative bbox and setup camera
    print("\n── Step 2: Setup fixed ortho camera ──")
    bbox, narrative = compute_narrative_bbox(FRAMES)
    if bbox is None:
        print("ERROR: Could not compute narrative bbox")
        sys.exit(1)
    cam = setup_fixed_ortho_camera(bbox, narrative)

    # Step 3: Render key frames
    print("\n── Step 3: Render 5 key frames ──")
    render_key_frames(cam)

    # Step 4: Frustum check
    print("\n── Step 4: Frustum check ──")
    check = run_frustum_check(cam)
    with open(CHECK_JSON, "w") as f:
        json.dump(check, f, indent=2)

    outside_count = 0
    partially_count = 0
    for fk, fd in check.items():
        if fk == "all_pass":
            continue
        for oname, status in fd["objects"].items():
            if status == "OUTSIDE":
                outside_count += 1
                print(f"  OUTSIDE: {oname} at frame {fk}")
            elif status == "PARTIALLY_INSIDE":
                partially_count += 1
                print(f"  PARTIAL: {oname} at frame {fk}")

    print(f"\nFrustum check: OUTSIDE={outside_count}, PARTIAL={partially_count}")
    print(f"All pass: {check['all_pass']}")

    # Step 5: Save as scene_graybox_B_preview.blend
    print(f"\n── Step 5: Save {OUTPUT_BLEND} ──")
    bpy.ops.wm.save_mainfile(filepath=OUTPUT_BLEND)
    print(f"Saved: {OUTPUT_BLEND}")

    print(f"\n{'=' * 56}")
    print("REPAIR COMPLETE")
    print(f"Blend:   {OUTPUT_BLEND}")
    print(f"Frames:  {PREVIEW_DIR}")
    print(f"Check:   {CHECK_JSON}")
    print(f"Heads OK: {head_ok}")
    print(f"Frustum: {'ALL_PASS' if check['all_pass'] else 'HAS_ISSUES'}")
    print(f"{'=' * 56}")


if __name__ == "__main__":
    try:
        import bpy_extras
        import bpy_extras.object_utils
    except ImportError as e:
        print(f"Import error: {e}")
        sys.exit(1)
    main()
