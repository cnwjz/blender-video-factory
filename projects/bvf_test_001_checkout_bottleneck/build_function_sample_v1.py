"""
FUNCTION_SAMPLE_V1_R1 — Fixed build with proper character loading, camera framing, and verification.
"""
import bpy, os, json, math
from mathutils import Vector, Euler

# === PATHS (validated immediately) ===
ME = os.path.abspath(__file__)
PROJ = os.path.dirname(ME)
ENV = os.path.join(PROJ, "output", "asset_audit_checkout_candidate_01", "work", "Supermercado")
CHAR = os.path.join(PROJ, "output", "character_audit_candidate_01", "work", "Blends", "Blends")
OUT = os.path.join(PROJ, "output", "function_sample_v1_r1")
W = os.path.join(OUT, "work")
DEL = os.path.join(OUT, "delivery")
for d in [OUT, W, DEL]: os.makedirs(d, exist_ok=True)

assert os.path.exists(ENV), f"ENV missing: {ENV}"
assert os.path.exists(CHAR), f"CHAR missing: {CHAR}"

# === FRESH SCENE ===
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = 30; sc.frame_start = 1; sc.frame_end = 135

# === WORLD ===
w = bpy.data.worlds.new("Bright"); w.color = (0.72, 0.72, 0.72); sc.world = w

# === IMPORT ENVIRONMENT ===
print("=== Env ===")
for fn in ['cashier.fbx', 'Milk.fbx', 'Bread.fbx', 'Juice.fbx', 'Eggs.fbx']:
    fp = os.path.join(ENV, fn)
    if os.path.exists(fp): bpy.ops.import_scene.fbx(filepath=fp)

# === LOAD CASHIER (Worker_Male) ===
print("=== Cashier ===")
with bpy.data.libraries.load(os.path.join(CHAR, "Worker_Male.blend"), link=False) as (df, dt):
    dt.collections = [c for c in df.collections if c]
    dt.objects = df.objects; dt.actions = df.actions
for coll in dt.collections:
    if coll:
        try: sc.collection.children.link(coll)
        except: pass

# === LOAD CUSTOMER (Casual_Bald) ===
print("=== Customer ===")
with bpy.data.libraries.load(os.path.join(CHAR, "Casual_Bald.blend"), link=False) as (df, dt):
    dt.collections = [c for c in df.collections if c]
    dt.objects = df.objects; dt.actions = df.actions
for coll in dt.collections:
    if coll:
        try: sc.collection.children.link(coll)
        except: pass

# === RENAME TO UNIQUE SEMANTIC NAMES ===
arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
if len(arms) >= 2:
    # Cashier = first armature loaded
    cashier = arms[0]; cashier.name = "Cashier_Armature"
    for c in cashier.children:
        if c.type == 'MESH': c.name = "Cashier_Body"
    # Customer = second
    customer = arms[1]; customer.name = "Customer_Armature"
    for c in customer.children:
        if c.type == 'MESH': c.name = "Customer_Body"
elif len(arms) == 1:
    cashier = arms[0]; cashier.name = "Cashier_Armature"
    for c in cashier.children:
        if c.type == 'MESH': c.name = "Cashier_Body"
    customer = None
else:
    cashier = customer = None

print(f"Cashier: {cashier.name if cashier else 'NONE'}")
print(f"Customer: {customer.name if customer else 'NONE'}")

# === SCALE: env up, chars down ===
ENV_S = 8.0; CHAR_S = 0.8
char_meshes = set()
for o in bpy.data.objects:
    if o.type == 'MESH':
        for mod in o.modifiers:
            if mod.type == 'ARMATURE': char_meshes.add(o.name)
for o in bpy.data.objects:
    if o.type == 'MESH' and o.name not in char_meshes:
        o.scale = Vector((ENV_S, ENV_S, ENV_S))
if cashier: cashier.scale = Vector((CHAR_S, CHAR_S, CHAR_S))
if customer: customer.scale = Vector((CHAR_S, CHAR_S, CHAR_S))
bpy.context.view_layer.update()

# === POSITION ===
if cashier: cashier.location = Vector((0, -0.4, 0))
if customer: customer.location = Vector((0, 0.9, 0))

# === BELT DETECTION ===
env_m = [o for o in bpy.data.objects if o.type=='MESH' and o.name not in char_meshes]
belt = None
for o in env_m:
    bb = [o.matrix_world @ Vector(v) for v in o.bound_box]
    xs, zs = [b.x for b in bb], [b.z for b in bb]
    w2, h2 = max(xs)-min(xs), max(zs)-min(zs)
    if 1.5 < w2 < 15 and h2 < 0.6: belt = o; break
print(f"Belt: {belt.name if belt else 'NONE'}")

# === PRODUCTS ===
def obj_width(o):
    bb = [o.matrix_world @ Vector(v) for v in o.bound_box]
    xs = [b.x for b in bb]; return max(xs)-min(xs)
prods = [o for o in env_m if o != belt and 0.05 < obj_width(o) < 4.0]
if belt and prods:
    bb = [belt.matrix_world @ Vector(v) for v in belt.bound_box]
    by = (min(b.y for b in bb)+max(b.y for b in bb))/2
    bz = max(b.z for b in bb)
    for i,p in enumerate(prods[:6]):
        p.location = Vector((-1.2+i*0.5, by, bz+0.3))
print(f"Products: {len(prods)}")

# === STATUS LIGHT ===
bpy.ops.mesh.primitive_cylinder_add(radius=0.6, depth=0.2, location=(1.5, -0.3, 4.5))
sl = bpy.context.object; sl.name="StatusLight_Green"
mg = bpy.data.materials.new("M_Green"); mg.use_nodes=True; mg.node_tree.nodes.clear()
e = mg.node_tree.nodes.new('ShaderNodeEmission')
e.inputs['Color'].default_value=(0.1,0.9,0.15,1); e.inputs['Strength'].default_value=3.0
mg.node_tree.links.new(e.outputs['Emission'], mg.node_tree.nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])
sl.data.materials.append(mg)

sr = sl.copy(); sr.data=sl.data.copy(); sr.name="StatusLight_Red"
sc.collection.objects.link(sr); sr.location=sl.location
mr = bpy.data.materials.new("M_Red"); mr.use_nodes=True; mr.node_tree.nodes.clear()
e2 = mr.node_tree.nodes.new('ShaderNodeEmission')
e2.inputs['Color'].default_value=(0.9,0.08,0.08,1); e2.inputs['Strength'].default_value=3.0
mr.node_tree.links.new(e2.outputs['Emission'], mr.node_tree.nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])
sr.data.materials.clear(); sr.data.materials.append(mr)

sr.hide_viewport=True; sr.hide_render=True
sr.keyframe_insert('hide_viewport',frame=1); sr.keyframe_insert('hide_render',frame=1)
sr.hide_viewport=False; sr.hide_render=False
sr.keyframe_insert('hide_viewport',frame=36); sr.keyframe_insert('hide_render',frame=36)
sl.hide_viewport=True; sl.hide_render=True
sl.keyframe_insert('hide_viewport',frame=36); sl.keyframe_insert('hide_render',frame=36)
sl.hide_viewport=False; sl.hide_render=False
sl.keyframe_insert('hide_viewport',frame=1); sl.keyframe_insert('hide_render',frame=1)
print("StatusLight: OK")

# === CLOSE SIGN ===
bpy.ops.mesh.primitive_plane_add(size=3.0, location=(0, 0.2, -1.5))
sg = bpy.context.object; sg.name="CloseSign"
ms = bpy.data.materials.new("M_Sign"); ms.use_nodes=True; ms.node_tree.nodes.clear()
e3 = ms.node_tree.nodes.new('ShaderNodeEmission')
e3.inputs['Color'].default_value=(1,0.85,0.1,1); e3.inputs['Strength'].default_value=1.5
ms.node_tree.links.new(e3.outputs['Emission'], ms.node_tree.nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])
sg.data.materials.append(ms)
sg.rotation_euler=Euler((math.radians(75),0,0),'XYZ')
sg.location.z=-1.5
sg.keyframe_insert('location',index=2,frame=1); sg.keyframe_insert('location',index=2,frame=42)
sg.location.z=0.5; sg.keyframe_insert('location',index=2,frame=52)
print("CloseSign: OK")

bpy.context.view_layer.update()

# === CAMERA FRAMING (bbox-based, excluding outliers) ===
print("=== Camera ===")
# Filter: only objects likely to be in the scene center
# === CAMERA (manual position, proven from step2 test) ===
cd = bpy.data.cameras.new("Cam"); cam = bpy.data.objects.new("Cam", cd)
sc.collection.objects.link(cam); cd.lens = 40; sc.camera = cam
cam.location = Vector((0, -6.5, 3.5))
cam.rotation_euler = Euler((math.radians(62), 0, 0), 'XYZ')
sc.render.resolution_x = 540; sc.render.resolution_y = 960
print(f"Camera: {cam.location}, rot=62deg pitch")

# === SCENE RENDER SETTINGS ===
if sc.world and sc.world.node_tree: sc.world.node_tree.nodes.clear()
sc.world.color = (0.72, 0.72, 0.72)
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'FLAT'
sc.display.shading.color_type = 'MATERIAL'

# === ANIMATIONS ===
print("=== Animation ===")
idles = sorted([a for a in bpy.data.actions if 'idle' in a.name.lower()], key=lambda x: x.name)
walks = sorted([a for a in bpy.data.actions if 'walk' in a.name.lower() and 'carry' not in a.name.lower()], key=lambda x: x.name)
# Cashier uses first idle/walk set, customer uses second
if cashier:
    cashier.animation_data_create()
    cashier.animation_data.action = idles[0] if idles else None
if customer:
    customer.animation_data_create()
    customer.animation_data.action = idles[1] if len(idles)>1 else (idles[0] if idles else None)
cashier_walk = walks[0] if walks else None
print(f"  Idles: {len(idles)}, Walks: {len(walks)}")

# === ANIMATION KEYFRAMES ===
# Products move (1-35)
for p in prods[:6]:
    sy = p.location.y; p.keyframe_insert('location', index=1, frame=1)
    p.location.y = sy + 2.5; p.keyframe_insert('location', index=1, frame=35)
# Products stop (36-60)
for p in prods[:6]:
    p.keyframe_insert('location', index=1, frame=36)
    p.keyframe_insert('location', index=1, frame=60)
# Cashier turn + walk (60-115)
if cashier:
    cashier.rotation_euler = Euler((0,0,0),'XYZ')
    cashier.keyframe_insert('rotation_euler', index=2, frame=60)
    cashier.rotation_euler = Euler((0, math.radians(-130), 0),'XYZ')
    cashier.keyframe_insert('rotation_euler', index=2, frame=78)
    if cashier_walk: cashier.animation_data.action = cashier_walk
    cashier.location = Vector((0, -0.4, 0))
    cashier.keyframe_insert('location', frame=78)
    cashier.location = Vector((-3, -2.5, 0))
    cashier.keyframe_insert('location', frame=115)
# Customer turn (90-125)
if customer:
    customer.rotation_euler = Euler((0,0,0),'XYZ')
    customer.keyframe_insert('rotation_euler', index=2, frame=1)
    customer.keyframe_insert('rotation_euler', index=2, frame=90)
    customer.rotation_euler = Euler((0, math.radians(-55), 0),'XYZ')
    customer.keyframe_insert('rotation_euler', index=2, frame=125)

# === SAVE .blend FOR INSPECTION ===
blend_path = os.path.join(W, "function_sample_v1_scene.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print(f"Scene saved to: {blend_path}")

# === RENDER DIAGNOSTIC FRAMES FIRST ===
print("=== Diagnostic renders ===")
sc.render.resolution_x = 540; sc.render.resolution_y = 960
diag_dir = os.path.join(W, "diagnostic_frames"); os.makedirs(diag_dir, exist_ok=True)
for fnum in [20, 45, 52, 78, 105, 125, 135]:
    sc.frame_set(fnum)
    sc.render.filepath = os.path.join(diag_dir, f"diag_f{fnum:04d}.png")
    bpy.ops.render.render(write_still=True)
    print(f"  Frame {fnum}: {os.path.getsize(sc.render.filepath)} bytes")

# === RENDER FULL PREVIEW ===
print("=== Full preview ===")
prev_dir = os.path.join(W, "preview_frames"); os.makedirs(prev_dir, exist_ok=True)
sc.render.image_settings.file_format = 'PNG'
sc.render.filepath = os.path.join(prev_dir, "frame_")
bpy.ops.render.render(animation=True)
nf = len([f for f in os.listdir(prev_dir) if f.endswith('.png')])
print(f"  Preview: {nf} frames")

# === CONTACT SHEET KEYFRAMES ===
print("=== Contact sheet ===")
sheet_dir = os.path.join(W, "sheet_frames"); os.makedirs(sheet_dir, exist_ok=True)
sheet_frames = [
    ('01_RUNNING', 20), ('02_LIGHT_RED', 45), ('03_PRODUCTS_STOPPED', 52),
    ('04_SIGN_APPEARS', 52), ('05_CASHIER_TURN', 78), ('06_CASHIER_EXIT', 105),
    ('07_CUSTOMER_TURN', 125), ('08_FINAL', 135),
]
for lb, fn in sheet_frames:
    sc.frame_set(fn)
    sc.render.filepath = os.path.join(sheet_dir, f"{lb}.png")
    bpy.ops.render.render(write_still=True)
print(f"  Sheet: {len(sheet_frames)} frames")

print(f"=== BUILD COMPLETE: {len(bpy.data.objects)} objects, {nf} preview frames ===")
