"""
L1-C2: Perspective camera, 55mm VERTICAL, fixed direction, binary distance search.
"""
import bpy, os, json, math, shutil
from mathutils import Vector
import bpy_extras.object_utils as obj_utils

PROJ = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane"
BLEND_IN = os.path.join(PROJ, "scene", "L1_step02_checkout_final.blend")
OUT_BLEND = os.path.join(PROJ, "scene", "L1_step03_camera_v2.blend")
PREVIEW = os.path.join(PROJ, "reviews", "L1_C_camera_preview_v2.png")
REP = os.path.join(PROJ, "reports", "L1_C_CAMERA_REPORT_v2.md")
UPL = os.path.join(PROJ, "reviews", "UPLOAD_NEXT", "L1_C2")
os.makedirs(UPL, exist_ok=True)
for f in os.listdir(UPL): os.remove(os.path.join(UPL, f))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=BLEND_IN)
bpy.context.scene.frame_set(20)
scene = bpy.context.scene
scene.render.resolution_x = 540; scene.render.resolution_y = 960

# ── Essential objects + joint bbox ────────────────────────
ESSENTIAL_NAMES = [f"{c}_Root" for c in ["Customer_01","Customer_02","Customer_03","Customer_04","Employee_01","Employee_02"]]
ESSENTIAL_NAMES += ["Cashier_Left_Root", "Cashier_Right_Root", "Product_L", "Product_R", "Basket"]
essential = [bpy.data.objects.get(n) for n in ESSENTIAL_NAMES if bpy.data.objects.get(n)]

all_pts = []
for obj in essential:
    bbox = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    all_pts.extend(bbox)
cx = sum(p.x for p in all_pts) / len(all_pts)
cy = sum(p.y for p in all_pts) / len(all_pts)
cz = sum(p.z for p in all_pts) / len(all_pts)
target = Vector((cx, cy, cz + 0.10))
print(f"Target: ({cx:.2f}, {cy:.2f}, {cz:.2f}+0.10)")

# ── Perspective camera ────────────────────────────────────
cam_data = bpy.data.cameras.new("Cam"); cam_data.type = 'PERSP'
cam_data.lens = 55; cam_data.sensor_fit = 'VERTICAL'
cam_data.clip_start = 0.05; cam_data.clip_end = 200
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam); scene.camera = cam

cam_dir = Vector((0.65, -1.0, 0.55)).normalized()
cam.location = target - cam_dir * 15.0  # initial guess
cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()

def get_all_bounds():
    """Return (ux_min, ux_max, uy_min, uy_max, clipped_list)."""
    xs = []; ys = []; clipped = []
    for obj in essential:
        bbox = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        obj_xs = []; obj_ys = []; obj_clipped = False
        for wp in bbox:
            s = obj_utils.world_to_camera_view(scene, cam, wp)
            if s.z < 0: obj_clipped = True; continue
            obj_xs.append(s.x); obj_ys.append(s.y)
        if not obj_xs: clipped.append(obj.name); continue
        min_x, max_x = min(obj_xs), max(obj_xs)
        min_y, max_y = min(obj_ys), max(obj_ys)
        xs.extend([min_x, max_x]); ys.extend([min_y, max_y])
        if min_x < 0.05 or max_x > 0.95 or min_y < 0.08 or max_y > 0.92:
            obj_clipped = True
        if obj_clipped: clipped.append(obj.name)
    if not xs: return (0, 1, 0, 1, clipped)
    return (min(xs), max(xs), min(ys), max(ys), clipped)

def evaluate(distance):
    """Set camera at given distance, return bounds dict."""
    cam.location = target - cam_dir * distance
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.view_layer.update()
    ux_min, ux_max, uy_min, uy_max, clipped = get_all_bounds()
    return {
        "distance": distance,
        "content_h": uy_max - uy_min,
        "content_w": ux_max - ux_min,
        "top": 1 - uy_max,
        "bot": uy_min,
        "left": ux_min,
        "right": 1 - ux_max,
        "clipped": len(clipped),
        "clipped_names": clipped,
    }

# ── Binary search for content height 74-82% ────────────────
lo, hi = 5.0, 40.0
iterations = 0
best = None
for i in range(8):
    iterations += 1
    mid = (lo + hi) / 2
    r = evaluate(mid)
    print(f"  dist={mid:.1f} h={r['content_h']:.3f} top={r['top']:.3f} bot={r['bot']:.3f} left={r['left']:.3f} right={r['right']:.3f} clipped={r['clipped']}")

    # Check pass
    passes = (r['content_h'] >= 0.74 and r['content_h'] <= 0.82 and
              r['content_w'] <= 0.88 and r['top'] >= 0.08 and r['top'] <= 0.13 and
              r['bot'] >= 0.08 and r['bot'] <= 0.15 and
              r['left'] >= 0.05 and r['right'] >= 0.05 and r['clipped'] == 0)
    if passes:
        best = r
        break

    if r['clipped'] > 0 or r['content_w'] > 0.88:
        # Too close — objects clip, need to go further
        lo = mid + 1.0
    elif r['content_h'] < 0.74:
        # Content too small — need to get closer
        hi = mid - 1.0
    else:
        # Content too large — need to go further
        lo = mid + 1.0

# If binary search didn't find exact match, take the closest
if best is None:
    best_dist = lo
    best = evaluate(best_dist)
    best["distance"] = best_dist

# ── Check camera not inside any bbox ───────────────────────
cam_inside = False
for obj in essential:
    bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs = [p.x for p in bb]; ys = [p.y for p in bb]; zs = [p.z for p in bb]
    if min(xs) <= cam.location.x <= max(xs) and min(ys) <= cam.location.y <= max(ys) and min(zs) <= cam.location.z <= max(zs):
        cam_inside = True; break

all_pass = (best['clipped'] == 0 and 0.74 <= best['content_h'] <= 0.82 and
            best['content_w'] <= 0.88 and 0.08 <= best['top'] <= 0.13 and
            0.08 <= best['bot'] <= 0.15 and best['left'] >= 0.05 and
            best['right'] >= 0.05 and not cam_inside)

print(f"\n  FINAL: dist={best['distance']:.1f} h={best['content_h']:.3f} w={best['content_w']:.3f}")
print(f"  Margins: T={best['top']:.3f} B={best['bot']:.3f} L={best['left']:.3f} R={best['right']:.3f}")
print(f"  Clipped={best['clipped']} CamIn={cam_inside} PASS={all_pass}")

# ── Render ─────────────────────────────────────────────────
scene.render.filepath = PREVIEW; bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_mainfile(filepath=OUT_BLEND)

# ── Report ─────────────────────────────────────────────────
with open(REP, "w") as f:
    f.write("# L1-C2 Camera Report v2\n\n")
    f.write(f"- Type: PERSP\n- Lens: 55mm, sensor_fit=VERTICAL\n")
    f.write(f"- Location: {cam.location}\n- Target: {target}\n")
    f.write(f"- Direction: {cam_dir}\n- Distance: {best['distance']:.2f}\n")
    f.write(f"- Content height: {best['content_h']:.3f} ({best['content_h']*100:.0f}%)\n")
    f.write(f"- Content width: {best['content_w']:.3f} ({best['content_w']*100:.0f}%)\n")
    f.write(f"- Top: {best['top']:.3f} Bot: {best['bot']:.3f} Left: {best['left']:.3f} Right: {best['right']:.3f}\n")
    f.write(f"- Clipped: {best['clipped']} ({best['clipped_names']})\n")
    f.write(f"- Camera in bbox: {cam_inside}\n")
    f.write(f"- Iterations: {iterations}\n- All pass: {all_pass}\n")

# ── Upload ─────────────────────────────────────────────────
shutil.copy(PREVIEW, os.path.join(UPL, "L1_C_camera_preview_v2.png"))
shutil.copy(REP, os.path.join(UPL, "L1_C_CAMERA_REPORT_v2.md"))
print(f"UPLOAD={UPL}")
print("L1-C2 DONE")
