"""
CASHIER_STANDARDIZATION_V1: Import, parent, orient, uniform scale, 4-view board.
"""
import bpy, os, math, json, shutil
from mathutils import Vector

PROJ = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane"
FBX = r"D:\blender-video-factory\assets\third_party\pensamientoazul_supermarket\Supermercado\cashier.fbx"
OUT_BLEND = os.path.join(PROJ, "scene", "cashier_standardized_v1.blend")
DIAG = os.path.join(PROJ, "reviews", "cashier_std_diag")
UPL = os.path.join(PROJ, "reviews", "UPLOAD_NEXT", "CASHIER_STANDARDIZATION")
REP = os.path.join(PROJ, "reports", "CASHIER_STANDARDIZATION_REPORT.md")
os.makedirs(DIAG, exist_ok=True); os.makedirs(UPL, exist_ok=True)
for f in os.listdir(UPL): os.remove(os.path.join(UPL, f))

TARGET_COUNTER_Z = 0.95

# ── Import ─────────────────────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'; scene.render.resolution_x = 1080; scene.render.resolution_y = 1080
scene.eevee.use_shadows = True

meshes = [o for o in bpy.data.objects if o.type == 'MESH']
print(f"Imported: {len(meshes)} meshes")
for m in meshes: print(f"  {m.name}: {len(m.data.vertices)}v")

# Record original
orig_names = [m.name for m in meshes]

def get_bbox():
    dg = bpy.context.evaluated_depsgraph_get(); pts = []
    for o in bpy.data.objects:
        if o.type != 'MESH': continue
        eo = o.evaluated_get(dg); m = eo.to_mesh()
        if m is None: continue
        for v in m.vertices: pts.append(eo.matrix_world @ v.co)
        eo.to_mesh_clear()
    if not pts: return None
    xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
    return (min(xs),max(xs),min(ys),max(ys),min(zs),max(zs))

bb_raw = get_bbox()
print(f"Raw bbox: {bb_raw}")
print(f"Raw size: W={bb_raw[1]-bb_raw[0]:.3f} D={bb_raw[3]-bb_raw[2]:.3f} H={bb_raw[5]-bb_raw[4]:.3f}")

# ── Create CASHIER_ROOT + parent ───────────────────────────
bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0,0,0))
root = bpy.context.object; root.name = "CASHIER_ROOT"; root.empty_display_size = 0.1

for m in meshes:
    m.parent = root

# Model is standing correctly — just very small at import scale. No rotation needed.
raw_h = bb_raw[5]-bb_raw[4]; raw_w = bb_raw[1]-bb_raw[0]; raw_d = bb_raw[3]-bb_raw[2]
oh = raw_h; ow = raw_w; od = raw_d
print(f"Oriented (no rotation): W={ow:.3f} D={od:.3f} H={oh:.3f}")

# ── Uniform scale to target counter height ─────────────────
# Target: counter surface at ~0.95. The top surface should be the maximum Z.
# Apply uniform scale to root
sf = TARGET_COUNTER_Z / max(oh, 0.001)
root.scale = Vector((sf, sf, sf))
bpy.context.view_layer.update()

bb_final = get_bbox()
fh = bb_final[5]-bb_final[4]; fw = bb_final[1]-bb_final[0]; fd = bb_final[3]-bb_final[2]
lowest_z = bb_final[4]; highest_z = bb_final[5]
print(f"Final size: W={fw:.3f} D={fd:.3f} H={fh:.3f}")
print(f"Top surface Z: {highest_z:.3f}")

# ── Align bottom to Z=0 ───────────────────────────────────
root.location.z = -lowest_z * sf + 0  # Correct for root Z after parenting
# Actually, after parenting, the root's children positions are relative to root.
# The world bbox is what matters. Let me adjust root.location.z to bring lowest_z to 0.
# Since root is at (0,0,0) with scale sf, the world positions are root.matrix_world @ child_local.
# Just offset root by -lowest_z in world units / sf to compensate.
root.location.z = -lowest_z
bpy.context.view_layer.update()

bb_final2 = get_bbox()
final_lowest = bb_final2[4]
final_highest = bb_final2[5]
print(f"After Z-align: lowest={final_lowest:.4f} highest={final_highest:.4f} counter_top={final_highest:.3f}")

# ── Reference pillar + grid ────────────────────────────────
bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=1.75, location=(fw/2+0.3, 0, 0.875))
pillar = bpy.context.object; pillar.name = "HeightRef_1.75"
m = bpy.data.materials.new("RefM"); m.use_nodes = True
m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.3, 0.5, 0.7, 1.0)
pillar.data.materials.append(m)

# Grid lines on ground
bpy.ops.mesh.primitive_plane_add(size=1, location=(0,0,-0.002))
g = bpy.context.object; g.name = "Grid"; g.scale = (3,3,1)
gm = bpy.data.materials.new("GridM"); gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.45, 0.43, 0.40, 1.0)
g.data.materials.append(gm)

# ── Lighting + World ───────────────────────────────────────
world = bpy.data.worlds.new("StdW"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.42, 0.40, 0.37, 1.0)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.5
bpy.ops.object.light_add(type='SUN', location=(5,-5,8))
bpy.context.object.data.energy = 3.0; bpy.context.object.data.angle = 0.12
bpy.ops.object.light_add(type='AREA', location=(-3,-2,4))
bpy.context.object.data.energy = 2.0; bpy.context.object.data.size = 4

# ── 4-view camera renders ─────────────────────────────────
cx = (bb_final2[0]+bb_final2[1])/2; cy = (bb_final2[2]+bb_final2[3])/2; cz = bb_final2[5]/2
views = {
    "front":  ((cx, cy-8, cz), (0,0,0), 0),
    "side":   ((cx+8, cy, cz), (math.radians(90),0,math.radians(90)), 0),
    "top":    ((cx, cy, cz+8), (0,0,0), 0),
    "three_q":((cx+4, cy-6, cz+4), (0,0,0), 0),
}
rendered = {}
for vname, (loc, rot, _) in views.items():
    cam_data = bpy.data.cameras.new(f"Cam_{vname}"); cam_data.type = 'ORTHO'
    cam_data.ortho_scale = max(fw, fd, fh) * 1.5; cam_data.clip_start = 0.05; cam_data.clip_end = 100
    cam = bpy.data.objects.new(f"Cam_{vname}", cam_data)
    scene.collection.objects.link(cam); scene.camera = cam
    cam.location = Vector(loc); cam.rotation_euler = rot
    # For three_q view: look-at
    if vname == "three_q":
        target = Vector((cx, cy, cz))
        cam.rotation_euler = (target - cam.location).to_track_quat('-Z','Y').to_euler()
    out = os.path.join(DIAG, f"cashier_{vname}.png")
    scene.render.filepath = out; bpy.ops.render.render(write_still=True)
    rendered[vname] = out
    bpy.data.objects.remove(cam, do_unlink=True); bpy.data.cameras.remove(cam_data)

# Save paths for compositing
paths_file = os.path.join(DIAG, "_paths.json")
with open(paths_file,"w") as f: json.dump(rendered, f, indent=2)

# ── Save ───────────────────────────────────────────────────
bpy.ops.wm.save_mainfile(filepath=OUT_BLEND)

# Reopen verify
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=OUT_BLEND)
root_r = bpy.data.objects.get("CASHIER_ROOT")
# Only measure the 4 original asset meshes (exclude HeightRef_1.75 and Grid)
asset_meshes_r = [o for o in bpy.data.objects if o.type=='MESH' and o.parent == root_r]
mesh_under_root = len(asset_meshes_r) == 4
scale_uniform = abs(root_r.scale.x - root_r.scale.y) < 0.0001 and abs(root_r.scale.x - root_r.scale.z) < 0.0001

def get_bbox_filtered():
    dg = bpy.context.evaluated_depsgraph_get(); pts = []
    for o in asset_meshes_r:
        eo = o.evaluated_get(dg); m = eo.to_mesh()
        if m is None: continue
        for v in m.vertices: pts.append(eo.matrix_world @ v.co)
        eo.to_mesh_clear()
    if not pts: return None
    xs=[p.x for p in pts]; ys=[p.y for p in pts]; zs=[p.z for p in pts]
    return (min(xs),max(xs),min(ys),max(ys),min(zs),max(zs))

bb_r = get_bbox_filtered()
reopen_ok = bb_r and abs(bb_r[4]) < 0.02 and 0.85 < (bb_r[5]-bb_r[4]) < 1.3

print(f"\nReopen: meshes_under_root={mesh_under_root} uniform_scale={scale_uniform}")
if bb_r:
    print(f"  Final bbox: W={bb_r[1]-bb_r[0]:.3f} D={bb_r[3]-bb_r[2]:.3f} H={bb_r[5]-bb_r[4]:.3f}")
    print(f"  Lowest Z={bb_r[4]:.4f} Counter top={bb_r[5]:.3f}")
print(f"  Reopen OK={reopen_ok}")

# ── Report ─────────────────────────────────────────────────
with open(REP,"w") as f:
    f.write("# Cashier Standardization Report v1\n\n")
    f.write(f"File: {FBX}\n\n")
    f.write(f"## Original Import\n\n- Objects: {orig_names}\n- Raw bbox: {bb_raw}\n")
    f.write(f"- Raw size: W={raw_w:.3f} D={bb_raw[3]-bb_raw[2]:.3f} H={raw_h:.3f}\n\n")
    f.write(f"## Standardization\n\n- Root: CASHIER_ROOT\n- Root rotation: {[math.degrees(v) for v in root_r.rotation_euler]}\n")
    f.write(f"- Root uniform scale: {root_r.scale.x:.4f}\n")
    f.write(f"- Final bbox: {bb_r}\n")
    f.write(f"- Final size: W={bb_r[1]-bb_r[0]:.3f} D={bb_r[3]-bb_r[2]:.3f} H={bb_r[5]-bb_r[4]:.3f}\n")
    f.write(f"- Lowest Z: {bb_r[4]:.4f}\n- Counter top Z: {bb_r[5]:.3f}\n")
    f.write(f"- Meshes under root: {mesh_under_root}\n- Uniform scale: {scale_uniform}\n")
    f.write(f"- Reopen stable: {reopen_ok}\n")
    f.write(f"- 4 views: {DIAG}\n")

SUMMARY = {
    "orig_names": orig_names, "raw_bbox": bb_raw, "root_rotation": [math.degrees(v) for v in root_r.rotation_euler],
    "root_scale": root_r.scale.x, "final_bbox": bb_r, "lowest_z": bb_r[4], "counter_top_z": bb_r[5],
    "uniform_scale": scale_uniform, "reopen_ok": reopen_ok
}
print(f"SUMMARY={json.dumps(SUMMARY)}")
print(f"REPORT={REP}")
print(f"BLEND={OUT_BLEND}")
print(f"STANDARDIZE DONE")
