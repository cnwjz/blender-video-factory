"""
BVF Test 001 — Scene Data Collection v1 (Diagnostic, read-only).
Run: blender --background scene_graybox_A.blend --python diagnose_scene_v1.py

Reads scene objects, camera, visibility and frustum data at key frames.
Generates diagnostic screenshots from 4 angles. Does NOT modify/save .blend.
"""
import bpy
import json
import math
import os
import sys
from mathutils import Vector

# ── Configuration ────────────────────────────────────────────
FRAMES = [1, 90, 150, 240, 345]
RES_X, RES_Y = 540, 960
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "diagnostics", "scene_data_v1")
os.makedirs(OUT_DIR, exist_ok=True)
JSON_PATH = os.path.join(OUT_DIR, "scene_data_v1.json")

# ── Helpers ──────────────────────────────────────────────────
def get_world_bbox(obj):
    """Return world-space AABB as (min_x, max_x, min_y, max_y, min_z, max_z)."""
    if not hasattr(obj, 'bound_box') or obj.type == 'EMPTY':
        loc = obj.matrix_world.translation
        return (loc.x, loc.x, loc.y, loc.y, loc.z, loc.z)
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs = [c.x for c in corners]; ys = [c.y for c in corners]; zs = [c.z for c in corners]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def bbox_center(bb):
    return ((bb[0] + bb[1]) / 2, (bb[2] + bb[3]) / 2, (bb[4] + bb[5]) / 2)


def is_in_frustum(cam_obj, world_point, scene):
    """Check if a world-space point is inside the camera frustum (0-1 NDC)."""
    v = bpy_extras.object_utils.world_to_camera_view(
        scene, cam_obj, Vector(world_point)
    )
    return 0 <= v.x <= 1 and 0 <= v.y <= 1 and v.z > 0


def bbox_in_frustum(cam_obj, obj, scene):
    """Return FULLY_INSIDE / PARTIALLY_INSIDE / OUTSIDE for object bbox vs camera frustum."""
    if obj.hide_viewport or obj.hide_render:
        return "HIDDEN"
    bb = get_world_bbox(obj)
    corners = [
        (bb[0], bb[2], bb[4]), (bb[0], bb[2], bb[5]),
        (bb[0], bb[3], bb[4]), (bb[0], bb[3], bb[5]),
        (bb[1], bb[2], bb[4]), (bb[1], bb[2], bb[5]),
        (bb[1], bb[3], bb[4]), (bb[1], bb[3], bb[5]),
    ]
    inside = 0; total = 0
    for c in corners:
        total += 1
        v = bpy_extras.object_utils.world_to_camera_view(scene, cam_obj, Vector(c))
        if 0 <= v.x <= 1 and 0 <= v.y <= 1 and v.z > 0:
            inside += 1

    if inside == 0:
        return "OUTSIDE"
    elif inside == total:
        return "FULLY_INSIDE"
    return "PARTIALLY_INSIDE"


def get_obj_data(obj, cam_obj, scene):
    """Return dict of key properties for one object."""
    mw = obj.matrix_world
    loc = mw.translation
    rot = mw.to_euler('XYZ')
    bb = get_world_bbox(obj)
    bc = bbox_center(bb)
    frustum = bbox_in_frustum(cam_obj, obj, scene) if cam_obj else "NO_CAMERA"
    return {
        "name": obj.name,
        "type": obj.type,
        "parent": obj.parent.name if obj.parent else None,
        "world_location": [round(loc.x, 4), round(loc.y, 4), round(loc.z, 4)],
        "world_rotation_euler_deg": [round(math.degrees(r), 2) for r in rot],
        "hide_viewport": obj.hide_viewport,
        "hide_render": obj.hide_render,
        "world_bbox": [round(v, 4) for v in bb],
        "world_bbox_center": [round(v, 4) for v in bc],
        "frustum_status": frustum,
        "has_animation_data": obj.animation_data is not None,
    }


def get_camera_data(cam_obj):
    """Return dict of camera properties."""
    d = cam_obj.data
    return {
        "name": cam_obj.name,
        "type": d.type,
        "world_location": [round(cam_obj.location.x, 4),
                           round(cam_obj.location.y, 4),
                           round(cam_obj.location.z, 4)],
        "world_rotation_euler_deg": [round(math.degrees(r), 2)
                                      for r in cam_obj.matrix_world.to_euler('XYZ')],
        "lens": round(d.lens, 2) if d.type == 'PERSP' else None,
        "ortho_scale": round(d.ortho_scale, 4) if d.type == 'ORTHO' else None,
        "sensor_width": d.sensor_width,
        "sensor_height": d.sensor_height,
        "sensor_fit": d.sensor_fit,
        "shift_x": round(d.shift_x, 4),
        "shift_y": round(d.shift_y, 4),
        "clip_start": d.clip_start,
        "clip_end": d.clip_end,
        "angle": round(d.angle, 4) if d.type == 'PERSP' else None,
    }


def classify_objects(all_objects):
    """Group objects by their naming convention."""
    customers = []
    cashiers = []
    counters = []
    signs = []
    shutters = []
    cameras = []
    lights = []
    other = []

    for obj in all_objects:
        n = obj.name
        if n == "Camera" or n.startswith("Cam_"):
            cameras.append(obj)
        elif n.endswith("_body") and (
            n.startswith("L") or n.startswith("M") or n.startswith("R") or n.startswith("N")
        ):
            customers.append(obj)
        elif n.startswith("Cashier_"):
            if n.endswith("_body"):
                cashiers.append(obj)
            elif n.endswith("_head"):
                pass  # heads are children, tracked with body
            else:
                other.append(obj)
        elif n.startswith("Counter_"):
            counters.append(obj)
        elif n.startswith("Sign_"):
            signs.append(obj)
        elif n.startswith("Shutter_"):
            shutters.append(obj)
        elif "light" in n.lower() or n in ("Sun", "Fill", "Rim"):
            lights.append(obj)
        elif n in ("Floor", "BackWall", "GrayWorld"):
            other.append(obj)
        elif n.endswith("_head"):
            pass  # child objects, tracked with parent
        elif n.endswith("_overlay"):
            counters.append(obj)  # overlay is part of counter
        else:
            other.append(obj)
    return customers, cashiers, counters, signs, shutters, cameras, lights, other


def make_diag_camera(name, location, rotation_euler_deg, cam_type='PERSP',
                     lens=50, ortho_scale=10.0, clip_end=200):
    """Create a temporary diagnostic camera. Does NOT save to .blend."""
    cam_data = bpy.data.cameras.new(name + "_data")
    cam_data.type = cam_type
    cam_data.lens = lens
    cam_data.ortho_scale = ortho_scale
    cam_data.clip_end = clip_end
    cam_obj = bpy.data.objects.new(name, cam_data)
    cam_obj.location = location
    cam_obj.rotation_euler = [math.radians(r) for r in rotation_euler_deg]
    bpy.context.scene.collection.objects.link(cam_obj)
    return cam_obj


def cleanup_diag_cameras(keep_names):
    """Remove diagnostic camera objects and their data."""
    for obj in list(bpy.data.objects):
        if obj.name in keep_names:
            continue
        if obj.type == 'CAMERA' and (obj.name.startswith("Diag_") or obj.name.startswith("DiagCam_")):
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if data and data.users == 0:
                bpy.data.cameras.remove(data)


def render_screenshot(frame, camera_obj, suffix, label):
    """Render one screenshot. Returns output path."""
    scene = bpy.context.scene
    scene.frame_set(frame)
    scene.camera = camera_obj
    scene.render.resolution_x = RES_X
    scene.render.resolution_y = RES_Y
    scene.render.image_settings.file_format = 'PNG'
    fname = f"frame_{frame:04d}_{suffix}.png"
    out_path = os.path.join(OUT_DIR, fname)
    scene.render.filepath = out_path
    bpy.ops.render.render(write_still=True)
    print(f"  [{label}] {fname}")
    return out_path


# ── Main ─────────────────────────────────────────────────────
def main():
    import bpy_extras.object_utils

    scene = bpy.context.scene
    print(f"Scene: {scene.name}")
    print(f"Objects in scene: {len(scene.objects)}")
    print(f"Total bpy.data.objects: {len(bpy.data.objects)}")

    # ── Find active camera ───────────────────────────────────
    active_cam = scene.camera
    if active_cam is None:
        # Try to find any camera
        for obj in bpy.data.objects:
            if obj.type == 'CAMERA':
                active_cam = obj
                break
    if active_cam is None:
        print("ERROR: No camera found in scene")
        sys.exit(1)

    print(f"Active camera: {active_cam.name}")

    # ── Classify objects ─────────────────────────────────────
    all_objs = list(bpy.data.objects)
    customers, cashiers, counters, signs, shutters, cameras, lights, other = classify_objects(all_objs)

    print(f"Customers: {len(customers)}")
    print(f"Cashiers: {len(cashiers)}")
    print(f"Counters: {len(counters)}")
    print(f"Signs: {len(signs)}")
    print(f"Shutters: {len(shutters)}")
    print(f"Cameras: {len(cameras)}")
    print(f"Lights: {len(lights)}")
    print(f"Other: {len(other)}")
    for o in other:
        print(f"  Other: {o.name} ({o.type})")

    # ── Camera data ──────────────────────────────────────────
    cam_data = get_camera_data(active_cam)
    print(f"\nCamera data: {json.dumps(cam_data, indent=2)}")

    # ── Per-frame data collection ────────────────────────────
    result = {
        "project": "bvf_test_001_checkout_bottleneck",
        "source_blend": "scene_graybox_A.blend",
        "source_build_script": "build_graybox.py",
        "source_config": "graybox_config.json",
        "active_camera": cam_data,
        "key_frames": {},
        "object_classification": {
            "customer_ids": [c.name for c in customers],
            "cashier_ids": [c.name for c in cashiers],
            "counter_ids": [c.name for c in counters],
            "sign_ids": [s.name for s in signs],
            "shutter_ids": [s.name for s in shutters],
            "light_ids": [l.name for l in lights],
            "other_ids": [o.name for o in other],
        },
    }

    for frame in FRAMES:
        scene.frame_set(frame)
        scene.view_layers[0].update()
        bpy.context.view_layer.update()

        fd = {
            "frame": frame,
            "active_camera_location": [round(active_cam.location.x, 4),
                                        round(active_cam.location.y, 4),
                                        round(active_cam.location.z, 4)],
            "customers": {},
            "cashiers": {},
            "counters": {},
            "signs": {},
            "shutters": {},
        }

        # Customers (body objects)
        for obj in customers:
            fd["customers"][obj.name] = get_obj_data(obj, active_cam, scene)
            # Also record children (heads)
            for child in obj.children:
                key = f"{obj.name}::child::{child.name}"
                fd["customers"][key] = get_obj_data(child, active_cam, scene)

        # Cashiers (body objects)
        for obj in cashiers:
            fd["cashiers"][obj.name] = get_obj_data(obj, active_cam, scene)

        # Counters
        for obj in counters:
            fd["counters"][obj.name] = get_obj_data(obj, active_cam, scene)

        # Signs
        for obj in signs:
            fd["signs"][obj.name] = get_obj_data(obj, active_cam, scene)

        # Shutters
        for obj in shutters:
            fd["shutters"][obj.name] = get_obj_data(obj, active_cam, scene)

        result["key_frames"][str(frame)] = fd

    # ── Generate diagnostic screenshots ──────────────────────
    print("\n── Generating diagnostic screenshots ──")
    screenshots = []

    # Keep track of cameras to clean up
    original_camera_name = active_cam.name

    # Calculate scene extents for diag cameras
    all_bb_points = []
    for obj in customers + cashiers + counters:
        bb = get_world_bbox(obj)
        all_bb_points.append(Vector((bb[0], bb[2], bb[4])))
        all_bb_points.append(Vector((bb[1], bb[3], bb[5])))

    if all_bb_points:
        min_x = min(p.x for p in all_bb_points); max_x = max(p.x for p in all_bb_points)
        min_y = min(p.y for p in all_bb_points); max_y = max(p.y for p in all_bb_points)
        min_z = min(p.z for p in all_bb_points); max_z = max(p.z for p in all_bb_points)
    else:
        min_x, max_x, min_y, max_y, min_z, max_z = -3, 3, -4, 5, 0, 3

    cx = (min_x + max_x) / 2
    cy = (min_y + max_y) / 2
    cz = (min_z + max_z) / 2
    span = max(max_x - min_x, max_y - min_y, 1.0)

    # B: Oblique view — positioned to see all counters + customers
    diag_oblique = make_diag_camera(
        "DiagCam_Oblique",
        location=(cx, min_y - span * 1.2, cz + span * 0.4),
        rotation_euler_deg=(55, 0, 0),
        cam_type='PERSP', lens=35,
    )

    # C: Top-down ortho
    diag_top = make_diag_camera(
        "DiagCam_Top",
        location=(cx, cy, cz + span * 1.5),
        rotation_euler_deg=(0, 0, 0),
        cam_type='ORTHO', ortho_scale=span * 1.4,
    )

    # D: Side view
    diag_side = make_diag_camera(
        "DiagCam_Side",
        location=(max_x + span * 1.2, cy, cz + span * 0.3),
        rotation_euler_deg=(60, 0, -90),
        cam_type='PERSP', lens=35,
    )

    for frame in FRAMES:
        scene.frame_set(frame)
        scene.view_layers[0].update()
        bpy.context.view_layer.update()
        # Must set scene camera before each render (render resets context)
        # A: Active camera
        scene.camera = active_cam
        sp = render_screenshot(frame, active_cam, "camera", f"F{frame:04d}-Camera")
        screenshots.append(sp)

        # B: Oblique
        scene.camera = diag_oblique
        sp = render_screenshot(frame, diag_oblique, "oblique", f"F{frame:04d}-Oblique")
        screenshots.append(sp)

        # C: Top
        scene.camera = diag_top
        sp = render_screenshot(frame, diag_top, "top", f"F{frame:04d}-Top")
        screenshots.append(sp)

        # D: Side
        scene.camera = diag_side
        sp = render_screenshot(frame, diag_side, "side", f"F{frame:04d}-Side")
        screenshots.append(sp)

    # Restore original camera
    scene.camera = active_cam

    # Cleanup diagnostic cameras
    cleanup_diag_cameras([original_camera_name])
    print("Diagnostic cameras cleaned up.")

    # ── Save JSON ──────────────────────────────────────────
    with open(JSON_PATH, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nScene data saved: {JSON_PATH}")

    # ── Summary ─────────────────────────────────────────────
    print(f"\n{'='*50}")
    print(f"DIAGNOSTIC COMPLETE")
    print(f"Screenshots: {len(screenshots)}")
    print(f"Data JSON: {JSON_PATH}")
    print(f"Output dir: {OUT_DIR}")
    print(f"{'='*50}")


if __name__ == "__main__":
    try:
        import bpy_extras
        import bpy_extras.object_utils
    except ImportError as e:
        print(f"Import error: {e}")
        sys.exit(1)
    main()
