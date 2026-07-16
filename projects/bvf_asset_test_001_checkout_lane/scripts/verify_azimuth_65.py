"""
CAMERA_AZIMUTH_65_EXACT_VERIFY — reproduce 65deg azimuth, validate, render clean+debug.
"""
import bpy, os, math, json, shutil, hashlib, time
from mathutils import Vector
import bpy_extras.object_utils as obj_utils

PROJ = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane"
BLEND_IN = os.path.join(PROJ, "scene", "L1_step02_checkout_final.blend")
BLEND_OUT = os.path.join(PROJ, "scene", "CAMERA_AZIMUTH_65_EXACT_VERIFY.blend")
CLEAN = os.path.join(PROJ, "reviews", "AZIMUTH_65_CLEAN.png")
DEBUG = os.path.join(PROJ, "reviews", "AZIMUTH_65_DEBUG.png")
REP = os.path.join(PROJ, "reports", "AZIMUTH_65_VERIFY_REPORT.md")
UPL = os.path.join(PROJ, "reviews", "UPLOAD_NEXT")

SCRIPT_START = time.time()
os.makedirs(UPL, exist_ok=True)
for f in os.listdir(UPL):
    fp = os.path.join(UPL, f)
    if os.path.isfile(fp): os.remove(fp)
    elif os.path.isdir(fp): shutil.rmtree(fp, ignore_errors=True)
for f in [CLEAN, DEBUG]:
    if os.path.exists(f): os.remove(f)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=BLEND_IN)
bpy.context.scene.frame_set(20); bpy.context.view_layer.update()
scene = bpy.context.scene
scene.render.resolution_x = 540; scene.render.resolution_y = 960

# ── Essential objects + world vertices + target ────────────
CHAR_NAMES = ["Customer_01","Customer_02","Customer_03","Customer_04","Employee_01","Employee_02"]
ESSENTIAL_NAMES = [f"{c}_Root" for c in CHAR_NAMES] + ["Cashier_Left_Root","Cashier_Right_Root","Product_L","Product_R","Basket"]
essential_objs = [bpy.data.objects.get(n) for n in ESSENTIAL_NAMES if bpy.data.objects.get(n)]

# Collect evaluated world vertices (for projection)
world_verts = []
essential_meshes = []
for obj in essential_objs:
    meshes = [o for o in obj.children_recursive if o.type == 'MESH'] if obj.type != 'MESH' else [obj]
    essential_meshes.extend(meshes)

for m in essential_meshes:
    dg = bpy.context.evaluated_depsgraph_get(); eo = m.evaluated_get(dg); me = eo.to_mesh()
    if me is None: continue
    for v in me.vertices: world_verts.append(eo.matrix_world @ v.co)
    eo.to_mesh_clear()

xs = [p.x for p in world_verts]; ys = [p.y for p in world_verts]; zs = [p.z for p in world_verts]
target = Vector((sum(xs)/len(xs), sum(ys)/len(ys), sum(zs)/len(zs) + 0.10))
print(f"Target: {target}")

# ── Camera (exact 65deg azimuth) ───────────────────────────
AZIMUTH = 65; ELEVATION = 25; DISTANCE = 5.4; LENS = 24; SENSOR_FIT = 'HORIZONTAL'

az = math.radians(AZIMUTH); el = math.radians(ELEVATION)
cam_dir = Vector((math.sin(az)*math.cos(el), -math.cos(az)*math.cos(el), math.sin(el))).normalized()
print(f"Direction: {cam_dir}")

cam_data = bpy.data.cameras.new("VerifyCam"); cam_data.type = 'PERSP'
cam_data.lens = LENS; cam_data.sensor_fit = SENSOR_FIT
cam_data.clip_start = 0.05; cam_data.clip_end = 500
cam = bpy.data.objects.new("VerifyCam", cam_data)
scene.collection.objects.link(cam); scene.camera = cam
cam.location = target + cam_dir * DISTANCE
cam.rotation_euler = (target - cam.location).to_track_quat('-Z','Y').to_euler()
bpy.context.view_layer.update()

# Pre-reopen validation
actual_dist = (cam.location - target).length
print(f"Actual distance: {actual_dist:.4f}m (target {DISTANCE}m)")

# Save + reopen (render AFTER reopen for consistency)
bpy.ops.wm.save_mainfile(filepath=BLEND_OUT)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=BLEND_OUT)
bpy.context.scene.frame_set(20); bpy.context.view_layer.update()
scene = bpy.context.scene

cam_r = bpy.data.objects.get("VerifyCam")
if not cam_r: cam_r = scene.camera
cam_data_r = cam_r.data
loc_r = cam_r.location
dist_r = (loc_r - target).length

# Verify azimuth/elevation
# camera_offset_direction = (loc_r - target).normalized() (from target toward camera)
odir = (loc_r - target).normalized()
actual_el = math.degrees(math.asin(odir.z))
actual_az_xy = math.atan2(odir.x, -odir.y)
actual_az = math.degrees(actual_az_xy) % 360

print(f"Reopen: loc={loc_r} dist={dist_r:.4f}m")
print(f"Reopen azimuth: {actual_az:.2f}deg (target {AZIMUTH})")
print(f"Reopen elevation: {actual_el:.2f}deg (target {ELEVATION})")

az_ok = abs(actual_az - AZIMUTH) < 0.1
el_ok = abs(actual_el - ELEVATION) < 0.1
dist_ok = abs(dist_r - DISTANCE) < 0.01
lens_ok = abs(cam_data_r.lens - LENS) < 0.01
print(f"Azimuth OK={az_ok} Elevation OK={el_ok} Distance OK={dist_ok} Lens OK={lens_ok}")

if not (az_ok and el_ok and dist_ok and lens_ok):
    print("VERIFICATION FAILED — stopping, no forged results")
    exit(1)

# ── Re-acquire essential objects + meshes after reopen ─────
essential_objs_r = [bpy.data.objects.get(n) for n in ESSENTIAL_NAMES if bpy.data.objects.get(n)]
essential_meshes_r = []
for obj in essential_objs_r:
    meshes = [c for c in obj.children_recursive if c.type == 'MESH'] if obj.type != 'MESH' else [obj]
    essential_meshes_r.extend(meshes)

# ── Projection ─────────────────────────────────────────────
dg = bpy.context.evaluated_depsgraph_get()
proj_xs = []; proj_ys = []
clipped_obj = 0
for m in essential_meshes_r:
    eo = m.evaluated_get(dg); me = eo.to_mesh()
    if me is None: continue
    obj_ok = True
    for v in me.vertices:
        s = obj_utils.world_to_camera_view(scene, cam_r, eo.matrix_world @ v.co)
        if s.z < 0 or s.x < 0.05 or s.x > 0.95 or s.y < 0.0 or s.y > 1.0: obj_ok = False
        else: proj_xs.append(s.x); proj_ys.append(s.y)
    eo.to_mesh_clear()
    if not obj_ok: clipped_obj += 1

ux_min = min(proj_xs); ux_max = max(proj_xs)
uy_min = min(proj_ys); uy_max = max(proj_ys)
ch = ux_max - ux_min; cw = uy_max - uy_min  # wait, that's wrong
content_w = ux_max - ux_min; content_h = uy_max - uy_min
top_m = 1 - uy_max; bot_m = uy_min
left_m = ux_min; right_m = 1 - ux_max

print(f"Projection: h={content_h:.4f} w={content_w:.4f}")
print(f"Margins: L={left_m:.4f} R={right_m:.4f} T={top_m:.4f} B={bot_m:.4f}")
print(f"Clipped objects: {clipped_obj}")

# Render clean (AFTER reopen, same state as debug)
scene.render.filepath = CLEAN; bpy.ops.render.render(write_still=True)
clean_time = time.time()
print(f"Clean render: {CLEAN}")

# ── Generate debug overlay ─────────────────────────────────
from PIL import Image, ImageDraw

clean_img = Image.open(CLEAN)
W, H = clean_img.size
# NDC to pixel: x_px = ndc_x * W, y_px = (1 - ndc_y) * H (flip Y)
px_min_x = int(ux_min * W); px_max_x = int(ux_max * W)
px_min_y = int((1 - uy_max) * H); px_max_y = int((1 - uy_min) * H)

debug_img = clean_img.copy()
draw = ImageDraw.Draw(debug_img)
# Draw bbox rectangle
draw.rectangle([px_min_x, px_min_y, px_max_x, px_max_y], outline=(0, 255, 128), width=2)
# Draw margin indicators
draw.text((px_min_x+2, px_min_y-14), f"W:{content_w*100:.0f}% H:{content_h*100:.0f}%", fill=(0,255,128))
debug_img.save(DEBUG)
debug_time = time.time()
print(f"Debug render: {DEBUG}")

# ── SHA256 ─────────────────────────────────────────────────
def sha256(path):
    with open(path, "rb") as f: return hashlib.sha256(f.read()).hexdigest()

clean_sha = sha256(CLEAN)
debug_sha = sha256(DEBUG)

# ── Report ─────────────────────────────────────────────────
with open(REP, "w") as f:
    f.write("# AZIMUTH 65 EXACT VERIFY Report\n\n")
    f.write("## Camera Parameters\n\n")
    f.write(f"- Lens: {cam_data_r.lens}mm, sensor_fit={cam_data_r.sensor_fit}\n")
    f.write(f"- Azimuth: {actual_az:.4f}deg (target {AZIMUTH}, diff={abs(actual_az-AZIMUTH):.4f})\n")
    f.write(f"- Elevation: {actual_el:.4f}deg (target {ELEVATION}, diff={abs(actual_el-ELEVATION):.4f})\n")
    f.write(f"- Distance: {dist_r:.4f}m (target {DISTANCE}, diff={abs(dist_r-DISTANCE):.4f})\n")
    f.write(f"- Resolution: 540x960\n")
    f.write(f"- Reopen pass: az={az_ok} el={el_ok} dist={dist_ok} lens={lens_ok}\n\n")
    f.write("## Projection\n\n")
    f.write(f"- Content height: {content_h:.4f} ({content_h*100:.1f}%)\n")
    f.write(f"- Content width: {content_w:.4f} ({content_w*100:.1f}%)\n")
    f.write(f"- Left margin: {left_m:.4f} Right margin: {right_m:.4f}\n")
    f.write(f"- Top margin: {top_m:.4f} Bottom margin: {bot_m:.4f}\n")
    f.write(f"- Clipped objects: {clipped_obj}\n")
    f.write(f"- Height ~48.3%: {abs(content_h-0.483)<0.005}\n\n")
    f.write("## File Verification\n\n")
    f.write(f"- Clean: {CLEAN} ({W}x{H}) SHA256={clean_sha}\n")
    f.write(f"- Debug: {DEBUG} ({debug_img.size[0]}x{debug_img.size[1]}) SHA256={debug_sha}\n")
    f.write(f"- Clean created: {clean_time - SCRIPT_START:.1f}s after start\n")
    f.write(f"- Debug created: {debug_time - SCRIPT_START:.1f}s after start\n")

# ── Copy to UPLOAD_NEXT ───────────────────────────────────
shutil.copy(CLEAN, os.path.join(UPL, "AZIMUTH_65_CLEAN.png"))
shutil.copy(DEBUG, os.path.join(UPL, "AZIMUTH_65_DEBUG.png"))
shutil.copy(REP, os.path.join(UPL, "AZIMUTH_65_VERIFY_REPORT.md"))
print(f"UPLOAD_NEXT ready: {len(os.listdir(UPL))} files")
print("DONE")
