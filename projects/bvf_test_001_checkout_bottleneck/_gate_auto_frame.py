"""
Gate auto-frame step. Calls video_pipeline.auto_framing.scan_ortho_params.
No fallback algorithm — if scan_ortho_params fails, gate fails.
"""
import json, math, os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
sys.path.insert(0, PROJECT_ROOT)
from video_pipeline.auto_framing import scan_ortho_params, is_narrative_object

RES_X, RES_Y = 540, 960
MIN_VERT = 0.50; MIN_L, MIN_R, MIN_T, MIN_B = 0.04, 0.04, 0.03, 0.03


def parse_args():
    frames, outdir = None, None
    for i, a in enumerate(sys.argv):
        if a == "--frames" and i + 1 < len(sys.argv): frames = json.loads(sys.argv[i+1])
        elif a == "--outdir" and i + 1 < len(sys.argv): outdir = sys.argv[i+1]
    return frames or [1, 90, 150, 240, 345], outdir or SCRIPT_DIR


def is_narrative(obj):
    return is_narrative_object(obj.name) and obj.name not in (
        "Floor", "BackWall", "Sun", "Fill", "Rim", "GrayWorld") and \
        obj.type not in ('LIGHT', 'CAMERA')


def make_frame_data_func(scene, cam_obj, frames, bpy_module, bpy_extras_mod, Vector_cls):
    """Return a closure for scan_ortho_params. ALL deps passed explicitly."""
    bpy = bpy_module
    bpy_extras = bpy_extras_mod
    Vector = Vector_cls
    def frame_data_func(ortho_scale, shift_x, shift_y):
        cam_obj.data.ortho_scale = ortho_scale
        cam_obj.data.shift_x = shift_x; cam_obj.data.shift_y = shift_y
        scene.camera = cam_obj
        all_data = []
        for frame in frames:
            scene.frame_set(frame); bpy.context.view_layer.update()
            pts = []
            for obj in bpy.data.objects:
                if not is_narrative(obj) or obj.hide_viewport or obj.hide_render: continue
                if not hasattr(obj, 'bound_box'): continue
                for corner in obj.bound_box:
                    wc = obj.matrix_world @ Vector(corner)
                    ndc = bpy_extras.object_utils.world_to_camera_view(scene, cam_obj, wc)
                    pts.append((ndc.x, ndc.y, obj.name))
            all_data.append((frame, pts))
        return all_data
    return frame_data_func


def main():
    import bpy, bpy_extras, bpy_extras.object_utils
    from mathutils import Vector

    frames, outdir = parse_args()
    scene = bpy.context.scene

    cam = scene.camera
    if cam is None:
        for obj in bpy.data.objects:
            if obj.type == 'CAMERA': cam = obj; break
    if cam is None: print(json.dumps({"error":"no camera"})); sys.exit(1)
    if cam.animation_data: cam.animation_data_clear()

    # Narrative bbox (identical to proven debug script)
    all_c = []
    for f in frames:
        scene.frame_set(f); bpy.context.view_layer.update()
        for obj in bpy.data.objects:
            if not is_narrative(obj) or obj.hide_viewport or obj.hide_render: continue
            if not hasattr(obj, 'bound_box'): continue
            for c in obj.bound_box: all_c.append(obj.matrix_world @ Vector(c))
    xs = [c.x for c in all_c]; ys = [c.y for c in all_c]; zs = [c.z for c in all_c]
    cx = (min(xs) + max(xs)) / 2; cy = (min(ys) + max(ys)) / 2; cz = (min(zs) + max(zs)) / 2
    cam_x = cx - 0.8; cam_y = min(ys) - 5.0; cam_z = max(zs) + 3.0
    direction = Vector((cx - cam_x, cy - cam_y, cz - cam_z))
    pitch = math.atan2(-direction.z, math.sqrt(direction.x**2 + direction.y**2))
    yaw = math.atan2(direction.x, direction.y)
    cam.data.type = 'ORTHO'; cam.location = (cam_x, cam_y, cam_z)
    cam.rotation_euler = (pitch, 0.0, yaw)
    cam.data.sensor_width = 36.0; cam.data.sensor_height = 24.0
    cam.data.sensor_fit = 'AUTO'; cam.data.clip_end = 200.0
    scene.camera = cam

    # ── Inline frame data function (matches proven debug script) ──
    def fdf(ortho, sx, sy):
        cam.data.ortho_scale = ortho
        cam.data.shift_x = sx; cam.data.shift_y = sy
        scene.camera = cam
        all_data = []
        for frame in frames:
            scene.frame_set(frame); bpy.context.view_layer.update()
            pts = []
            for obj in bpy.data.objects:
                if not is_narrative(obj) or obj.hide_viewport or obj.hide_render: continue
                if not hasattr(obj, 'bound_box'): continue
                for corner in obj.bound_box:
                    wc = obj.matrix_world @ Vector(corner)
                    ndc = bpy_extras.object_utils.world_to_camera_view(scene, cam, wc)
                    pts.append((ndc.x, ndc.y, obj.name))
            all_data.append((frame, pts))
        return all_data

    # ~120 candidates total: ortho(8) × sx(5) × sy(3) = 120 < 200
    ortho_range = [16.0, 14.0, 13.0, 12.0, 11.5, 11.0, 10.5, 10.0]
    sx_range = [0.100, 0.130, 0.156, 0.170, 0.200]
    sy_range = [0.300, 0.345, 0.390]
    best = scan_ortho_params(fdf, ortho_range, sx_range, sy_range,
                             min_vert_occupancy=MIN_VERT, min_left_margin=MIN_L,
                             min_right_margin=MIN_R, min_top_margin=MIN_T,
                             min_bot_margin=MIN_B)

    print(f"DEBUG scan: best={best}", flush=True)
    if best[0] is None:
        # scan_ortho_params failed — gate fails
        result = {"pass": False, "error": "scan_ortho_params_no_solution",
                  "frames_used": len(frames), "scan_ortho_params_called": True}
        print(f"AUTO_FRAME_RESULT={json.dumps(result)}")
        return

    ortho, sx, sy, score, details = best
    cam.data.ortho_scale = ortho
    if sx is not None: cam.data.shift_x = sx
    if sy is not None: cam.data.shift_y = sy
    scene.camera = cam

    # Save
    blend_name = os.path.basename(bpy.context.blend_data.filepath or
        os.path.join(SCRIPT_DIR, "scene_graybox_gate_output.blend"))
    bpy.ops.wm.save_mainfile(filepath=os.path.join(SCRIPT_DIR, blend_name))

    # Output
    cam_loc = cam.location; cam_rot = cam.rotation_euler
    all_pts = []
    for f in frames:
        scene.frame_set(f); bpy.context.view_layer.update()
        for obj in bpy.data.objects:
            if not is_narrative(obj) or obj.hide_viewport or obj.hide_render: continue
            if not hasattr(obj, 'bound_box'): continue
            for corner in obj.bound_box:
                wc = obj.matrix_world @ Vector(corner)
                ndc = bpy_extras.object_utils.world_to_camera_view(scene, cam, wc)
                if ndc.z > 0: all_pts.append((ndc.x, ndc.y))
    mnx = min(p[0] for p in all_pts) if all_pts else 0
    mxx = max(p[0] for p in all_pts) if all_pts else 1
    mny = min(p[1] for p in all_pts) if all_pts else 0
    mxy = max(p[1] for p in all_pts) if all_pts else 1
    result = {
        "pass": True, "camera_type": "ORTHO",
        "camera_location": [round(cam_loc.x, 2), round(cam_loc.y, 2), round(cam_loc.z, 2)],
        "camera_rotation_deg": [round(math.degrees(cam_rot.x), 1), 0.0, round(math.degrees(cam_rot.z), 1)],
        "ortho_scale": round(ortho, 2),
        "shift_x": round(cam.data.shift_x, 4), "shift_y": round(cam.data.shift_y, 4),
        "vert_occupancy_pct": round((mxy - mny) * 100, 1),
        "horiz_occupancy_pct": round((mxx - mnx) * 100, 1),
        "margins_pct": [round(mnx * 100, 1), round((1 - mxx) * 100, 1),
                        round((1 - mxy) * 100, 1), round(mny * 100, 1)],
        "frames_used": len(frames), "scan_ortho_params_called": True,
    }
    print(f"AUTO_FRAME_RESULT={json.dumps(result)}")


if __name__ == "__main__":
    main()
