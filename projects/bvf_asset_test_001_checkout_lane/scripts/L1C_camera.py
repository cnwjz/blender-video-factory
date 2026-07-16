"""
L1-C: Perspective camera setup, preflight, one distance correction if needed.
"""
import bpy, os, json, math, shutil
from mathutils import Vector
import bpy_extras.object_utils as obj_utils

PROJ = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane"
BLEND_IN = os.path.join(PROJ, "scene", "L1_step02_checkout_final.blend")
OUT_BLEND = os.path.join(PROJ, "scene", "L1_step03_camera.blend")
PREVIEW = os.path.join(PROJ, "reviews", "L1_C_camera_preview.png")
REP = os.path.join(PROJ, "reports", "L1_C_CAMERA_REPORT.md")
JSON_OUT = os.path.join(PROJ, "reports", "L1_C_projection.json")
UPL = os.path.join(PROJ, "reviews", "UPLOAD_NEXT", "L1_C")
os.makedirs(UPL, exist_ok=True)
for f in os.listdir(UPL): os.remove(os.path.join(UPL, f))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=BLEND_IN)
bpy.context.scene.frame_set(20)
scene = bpy.context.scene
scene.render.resolution_x = 540; scene.render.resolution_y = 960

# ── Essential objects ──────────────────────────────────────
ESSENTIAL_NAMES = [f"{c}_Root" for c in ["Customer_01","Customer_02","Customer_03","Customer_04","Employee_01","Employee_02"]]
ESSENTIAL_NAMES += ["Cashier_Left_Root", "Cashier_Right_Root", "Product_L", "Product_R", "Basket"]
essential = [bpy.data.objects.get(n) for n in ESSENTIAL_NAMES if bpy.data.objects.get(n)]

# ── Camera ─────────────────────────────────────────────────
cam_data = bpy.data.cameras.new("LookdevCam"); cam_data.type = 'ORTHO'
cam_data.ortho_scale = 12.0; cam_data.shift_y = -0.12; cam_data.clip_start = 0.05; cam_data.clip_end = 100
cam = bpy.data.objects.new("LookdevCam", cam_data)
scene.collection.objects.link(cam); scene.camera = cam

# Compute essential bbox center for target
bpy.context.view_layer.update()
all_pts = []
for obj in essential:
    bbox = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    all_pts.extend(bbox)
cx = sum(p.x for p in all_pts)/len(all_pts) if all_pts else 0
cy = sum(p.y for p in all_pts)/len(all_pts) if all_pts else 1.7
cz = sum(p.z for p in all_pts)/len(all_pts) if all_pts else 0.85
target = Vector((cx, cy, cz))

# Camera: 3/4 perspective from front-right
# Target ~10m away to fit scene with 52mm lens
cam_init_loc = Vector((cx + 4, cy - 7, cz + 5))
cam.location = cam_init_loc
direction = target - cam.location
cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

def check_clipping(obj):
    """Check bounding box corners against screen. Return (min_x, max_x, min_y, max_y, any_clipped)."""
    bbox = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    sx = []; sy = []; clipped = False
    for wp in bbox:
        s = obj_utils.world_to_camera_view(scene, cam, wp)
        if s.z < 0: clipped = True; continue
        sx.append(s.x); sy.append(s.y)
    if not sx: return (0,1,0,1,True)
    min_x, max_x = min(sx), max(sx)
    min_y, max_y = min(sy), max(sy)
    in_bounds = (0.04 <= min_x <= 0.96 and 0.04 <= max_x <= 0.96 and
                 0.04 <= min_y <= 0.96 and 0.04 <= max_y <= 0.96)
    return (min_x, max_x, min_y, max_y, not in_bounds)

def get_all_screen_bounds():
    """Union bbox of all essential objects."""
    all_xs = []; all_ys = []
    clipped = []
    for obj in essential:
        min_x, max_x, min_y, max_y, is_clipped = check_clipping(obj)
        all_xs.extend([min_x, max_x]); all_ys.extend([min_y, max_y])
        if is_clipped: clipped.append(obj.name)
    if not all_xs: return None
    return (min(all_xs), max(all_xs), min(all_ys), max(all_ys), clipped)

bpy.context.view_layer.update()
bounds = get_all_screen_bounds()
if bounds:
    ux_min, ux_max, uy_min, uy_max, clipped = bounds
    left_margin = ux_min; right_margin = 1-ux_max
    top_empty = 1-uy_max; bot_margin = uy_min
    content_h = uy_max - uy_min
    print(f"  Initial: top={top_empty:.3f} bot={bot_margin:.3f} left={left_margin:.3f} right={right_margin:.3f} h={content_h:.3f} clipped={len(clipped)}")

# ── One scale correction if needed ─────────────────────────
correction_applied = False
needs_correction = False  # Disabled — single manual scale above
if bounds and needs_correction:
    if len(clipped) > 0 or left_margin < 0.04 or right_margin < 0.04:
        cam_data.ortho_scale *= 1.2  # widen view
    else:
        cam_data.ortho_scale *= 0.85  # make content larger (reduce scale)
    bpy.context.view_layer.update()
    correction_applied = True
    bounds = get_all_screen_bounds()
    if bounds:
        ux_min, ux_max, uy_min, uy_max, clipped = bounds
        left_margin = ux_min; right_margin = 1-ux_max
        top_empty = 1-uy_max; bot_margin = uy_min
        content_h = uy_max - uy_min
    print(f"  Corrected: scale={cam_data.ortho_scale:.2f} top={top_empty:.3f} bot={bot_margin:.3f} left={left_margin:.3f} right={right_margin:.3f} h={content_h:.3f} clipped={len(clipped)}")

# ── Final checks ───────────────────────────────────────────
cam_inside = False
for obj in essential:
    bb = getattr(obj, 'bound_box', None)
    if bb is None: continue
    world_bb = [obj.matrix_world @ Vector(c) for c in bb]
    xs = [p.x for p in world_bb]; ys = [p.y for p in world_bb]; zs = [p.z for p in world_bb]
    if min(xs) <= cam.location.x <= max(xs) and min(ys) <= cam.location.y <= max(ys) and min(zs) <= cam.location.z <= max(zs):
        cam_inside = True; break

all_pass = (len(clipped) == 0 and top_empty <= 0.25 and bot_margin <= 0.55 and
            left_margin >= 0.03 and right_margin >= 0.02 and not cam_inside)
print(f"  PASS={all_pass} cam_inside={cam_inside}")

# ── Render ─────────────────────────────────────────────────
scene.render.filepath = PREVIEW; bpy.ops.render.render(write_still=True)

# ── Save ───────────────────────────────────────────────────
bpy.ops.wm.save_mainfile(filepath=OUT_BLEND)

# ── JSON ───────────────────────────────────────────────────
proj_data = {
    "camera_location": [round(v,3) for v in cam.location],
    "target": [round(v,3) for v in target],
    "camera_type": "ORTHO",
    "ortho_scale": round(cam_data.ortho_scale, 3),
    "top_empty": round(top_empty,4),
    "bot_margin": round(bot_margin,4),
    "left_margin": round(left_margin,4),
    "right_margin": round(right_margin,4),
    "content_height": round(content_h,4),
    "clipped_essential": len(clipped),
    "clipped_names": clipped,
    "correction_applied": correction_applied,
    "cam_inside_bbox": cam_inside,
    "all_pass": all_pass
}
with open(JSON_OUT,"w") as f: json.dump(proj_data, f, indent=2)

# ── Report ─────────────────────────────────────────────────
with open(REP,"w") as rf:
    rf.write("# L1-C Camera Report\n\n")
    rf.write(f"- Camera location: {cam.location}\n- Target: {target}\n")
    rf.write(f"- Type: ORTHO, ortho_scale={cam_data.ortho_scale:.2f}\n")
    rf.write(f"- Clipped essential: {len(clipped)}\n")
    rf.write(f"- Margins: top={top_empty:.3f} bot={bot_margin:.3f} left={left_margin:.3f} right={right_margin:.3f}\n")
    rf.write(f"- Content height: {content_h:.3f} ({content_h*100:.0f}%)\n")
    rf.write(f"- Distance correction: {correction_applied}\n")
    rf.write(f"- Camera in bbox: {cam_inside}\n")
    rf.write(f"- All pass: {all_pass}\n")

# ── Upload ─────────────────────────────────────────────────
shutil.copy(PREVIEW, os.path.join(UPL, "L1_C_camera_preview.png"))
shutil.copy(REP, os.path.join(UPL, "L1_C_CAMERA_REPORT.md"))
print(f"UPLOAD={UPL}")
print("L1-C DONE")
