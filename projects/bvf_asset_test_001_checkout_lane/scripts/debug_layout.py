"""
A2D: Multi-asset spatial & camera debug. Fixed layout, 4 ortho views + 3/4 perspective.
No animation, no environment beyond counters+ground, unique naming, bbox validation.
"""
import bpy, os, json, math
from mathutils import Vector
import bpy_extras.object_utils as obj_utils

PROJ = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane"
CH_FBX = os.path.join(PROJ, "assets", "imported", "kenney_mini-characters", "Models", "FBX format")
MK_FBX = os.path.join(PROJ, "assets", "imported", "kenney_mini-market", "Models", "FBX format")
MK_GLB = os.path.join(PROJ, "assets", "imported", "kenney_mini-market", "Models", "GLB format")
UPL = os.path.join(PROJ, "reviews", "UPLOAD_NEXT")
TMP = os.path.join(PROJ, "reviews", "_ldbg")
os.makedirs(UPL, exist_ok=True); os.makedirs(TMP, exist_ok=True)
for f in os.listdir(UPL): os.remove(os.path.join(UPL, f))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1080
scene.render.resolution_y = 1080
scene.eevee.use_shadows = True

# ── Helpers ────────────────────────────────────────────────
prev_objs = set()
def pre_snapshot():
    global prev_objs
    prev_objs = set(bpy.data.objects)

def post_snapshot():
    return [o for o in bpy.data.objects if o not in prev_objs]

def delete_lonely_icospheres():
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and o.name.lower().startswith('icosphere') and o.parent is None:
            bpy.data.objects.remove(o, do_unlink=True)

def fix_all_visibility():
    for o in bpy.data.objects:
        o.hide_viewport = False; o.hide_render = False
    for c in bpy.data.collections:
        c.hide_viewport = False; c.hide_render = False

def get_eval_bbox(mesh_objects):
    """Joint world bounding box of evaluated meshes."""
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in mesh_objects:
        if o.type != 'MESH': continue
        eo = o.evaluated_get(dg); m = eo.to_mesh()
        if m is None: continue
        for v in m.vertices: pts.append(eo.matrix_world @ v.co)
        eo.to_mesh_clear()
    if not pts: return None
    xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))

def camera_lookat(cam, target, scene):
    direction = target - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

def preflight_check(essential_meshes, cam, scene):
    dg = bpy.context.evaluated_depsgraph_get()
    for o in essential_meshes:
        if o.type != 'MESH': continue
        eo = o.evaluated_get(dg); m = eo.to_mesh()
        if m is None: continue
        for v in m.vertices:
            s = obj_utils.world_to_camera_view(scene, cam, eo.matrix_world @ v.co)
            if s.z < 0: eo.to_mesh_clear(); return False  # behind camera
            if s.x < 0.05 or s.x > 0.95 or s.y < 0.06 or s.y > 0.94:
                eo.to_mesh_clear(); return False
        eo.to_mesh_clear()
    return True

# ── IMPORT CHARACTERS ──────────────────────────────────────
char_data = []

for label, fname in [
    ("Customer_01", "character-male-a.fbx"),
    ("Customer_02", "character-female-a.fbx"),
    ("Customer_03", "character-male-b.fbx"),
    ("Customer_04", "character-female-b.fbx"),
    ("Employee_01", "character-employee.fbx"),
    ("Employee_02", "character-employee.fbx"),
]:
    pre_snapshot()
    path = os.path.join(MK_FBX if "employee" in fname else CH_FBX, fname)
    if "employee" in fname:
        bpy.ops.import_scene.fbx(filepath=path)
    else:
        bpy.ops.import_scene.fbx(filepath=path)
    delete_lonely_icospheres()
    new = post_snapshot()
    fix_all_visibility()

    # Find Empty, Armature, body, head
    empty = [o for o in new if o.type == 'EMPTY']
    arm = [o for o in new if o.type == 'ARMATURE']
    meshes = [o for o in new if o.type == 'MESH']

    # Create collection
    col = bpy.data.collections.new(label)
    scene.collection.children.link(col)

    # Rename and move to collection
    if empty:
        e = empty[-1]; e.name = f"{label}_Root"
        for c in list(e.users_collection): c.objects.unlink(e)
        col.objects.link(e)
    if arm:
        a = arm[-1]; a.name = f"{label}_Armature"
        for c in list(a.users_collection): c.objects.unlink(a)
        col.objects.link(a)
    # Rename meshes
    for i, m in enumerate(meshes):
        if 'body' in m.name.lower() or i == 0:
            m.name = f"{label}_Body"
        else:
            m.name = f"{label}_Head"
        for c in list(m.users_collection): c.objects.unlink(m)
        col.objects.link(m)

    # Find renamed objects
    root = bpy.data.objects.get(f"{label}_Root")
    arm_obj = bpy.data.objects.get(f"{label}_Armature")
    body = bpy.data.objects.get(f"{label}_Body")
    head = bpy.data.objects.get(f"{label}_Head")

    char_data.append({
        "label": label, "root": root, "armature": arm_obj,
        "body": body, "head": head
    })
    print(f"  {label}: Root={root!=None} Arm={arm_obj!=None} Body={body!=None} Head={head!=None}")

# ── COUNTERS ────────────────────────────────────────────────
COUNTER_H = 1.12
COUNTER_W = 1.70
COUNTER_D = 0.85

counters = []
for label, cx in [("Counter_L", -1.4), ("Counter_R", 1.4)]:
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, 1.5, COUNTER_H/2))
    c = bpy.context.object; c.name = label
    c.scale = (COUNTER_W/2, COUNTER_D/2, COUNTER_H/2)
    m = bpy.data.materials.new(f"{label}_Mat")
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.72, 0.68, 0.60, 1.0)
    c.data.materials.append(m)
    counters.append(c)
    # Conveyor belt
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, 1.5, COUNTER_H + 0.02))
    b = bpy.context.object; b.name = f"{label}_Belt"
    b.scale = (1.0, 0.35, 0.02)
    bm = bpy.data.materials.new(f"{label}BeltM")
    bm.use_nodes = True
    bm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.14, 0.12, 0.10, 1.0)
    b.data.materials.append(bm)

# Cash registers
pre_snapshot()
imp_glb_path = os.path.join(MK_GLB, "cash-register.glb")
bpy.ops.import_scene.gltf(filepath=imp_glb_path)
reg_new = [o for o in post_snapshot() if o.type == 'MESH']
if reg_new:
    reg_new[0].name = "Register_L"; reg_new[0].location = (-1.4, 1.65, COUNTER_H + 0.03)
    # Import second register
    pre_snapshot()
    bpy.ops.import_scene.gltf(filepath=imp_glb_path)
    reg_new2 = [o for o in post_snapshot() if o.type == 'MESH']
    if reg_new2:
        reg_new2[0].name = "Register_R"; reg_new2[0].location = (1.4, 1.65, COUNTER_H + 0.03)

# Floor
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -0.005))
floor = bpy.context.object; floor.name = "Floor"; floor.scale = (5, 6, 1)
fm = bpy.data.materials.new("FloorM")
fm.use_nodes = True
fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.38, 0.35, 0.30, 1.0)
floor.data.materials.append(fm)

# ── NORMALIZE CHARACTER HEIGHTS ────────────────────────────
TARGET_H = 1.75
for cd in char_data:
    root = cd["root"]
    if not root: continue
    # Reset scale, measure
    root.scale = (1, 1, 1)
    dg = bpy.context.evaluated_depsgraph_get()
    bpy.context.view_layer.update()
    meshes = [o for o in [cd["body"], cd["head"]] if o]
    bb = get_eval_bbox(meshes)
    if bb is None: continue
    h = bb[5] - bb[4]
    sf = TARGET_H / h if h > 0.001 else 1.0
    root.scale = Vector((sf, sf, sf))
    dg = bpy.context.evaluated_depsgraph_get()
    bpy.context.view_layer.update()
    bb2 = get_eval_bbox(meshes)
    if bb2 is None: continue
    min_z = bb2[4]
    # Align feet to Z=0
    root.location.z -= min_z
    print(f"  {cd['label']}: native_h={h:.3f} scale={sf:.3f} final_h={bb2[5]-bb2[4]:.3f}")

# ── FIXED LAYOUT ───────────────────────────────────────────
# Position characters at fixed coordinates
# Left lane: counter at X=-1.4, employee behind, 3 customers in queue
# Right lane: counter at X=1.4, employee behind, 1 customer in queue

layout = {
    "Employee_01":  (-1.4, 1.9, 0),   # behind left counter
    "Employee_02":  (1.4, 1.9, 0),    # behind right counter
    "Customer_01":  (-1.4, 0.2, 0),   # left queue front
    "Customer_02":  (-1.4, -0.9, 0),  # left queue middle
    "Customer_03":  (-1.4, -2.0, 0),  # left queue back
    "Customer_04":  (1.4, 0.2, 0),    # right queue front
}

for cd in char_data:
    label = cd["label"]
    if label in layout and cd["root"]:
        x, y, z = layout[label]
        cd["root"].location = Vector((x, y, cd["root"].location.z + z))
        print(f"  {label} → ({x}, {y}, {cd['root'].location.z:.3f})")

# ── LIGHTING ───────────────────────────────────────────────
world = bpy.data.worlds.new("W"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.45, 0.42, 0.38, 1.0)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.5
bpy.ops.object.light_add(type='SUN', location=(5, -5, 8))
bpy.context.object.data.energy = 2.5; bpy.context.object.data.angle = 0.1
bpy.ops.object.light_add(type='AREA', location=(-2, -1, 4))
bpy.context.object.data.energy = 1.8; bpy.context.object.data.size = 4

# ── ESSENTIAL BBOX ─────────────────────────────────────────
ESSENTIAL_NAMES = []
for cd in char_data:
    for k in ["body", "head"]:
        o = cd.get(k)
        if o: ESSENTIAL_NAMES.append(o.name)
for c in counters: ESSENTIAL_NAMES.append(c.name)
for name in ["Register_L", "Register_R"]:
    o = bpy.data.objects.get(name)
    if o: ESSENTIAL_NAMES.append(o.name)

essential_objs = [bpy.data.objects[n] for n in ESSENTIAL_NAMES if bpy.data.objects.get(n)]
ess_bb = get_eval_bbox(essential_objs)
if ess_bb:
    print(f"\n  Essential BBox: min=({ess_bb[0]:.2f},{ess_bb[2]:.2f},{ess_bb[4]:.2f}) max=({ess_bb[1]:.2f},{ess_bb[3]:.2f},{ess_bb[5]:.2f})")
    ecx = (ess_bb[0]+ess_bb[1])/2; ecy = (ess_bb[2]+ess_bb[3])/2; ecz = (ess_bb[4]+ess_bb[5])/2
    bbox_center = Vector((ecx, ecy, ecz))
    bbox_size = Vector((ess_bb[1]-ess_bb[0], ess_bb[3]-ess_bb[2], ess_bb[5]-ess_bb[4]))
    print(f"  Center: {bbox_center} Size: {bbox_size}")

# ── 4-VIEW RENDERING ───────────────────────────────────────
# Create empty for bbox wireframe visualization
def make_bbox_empty(name, bb):
    bpy.ops.object.empty_add(type='CUBE', location=((bb[0]+bb[1])/2, (bb[2]+bb[3])/2, (bb[4]+bb[5])/2))
    e = bpy.context.object; e.name = name
    e.scale = ((bb[1]-bb[0])/2, (bb[3]-bb[2])/2, (bb[5]-bb[4])/2)
    e.show_in_front = True
    e.display_type = 'WIRE'
    return e

if ess_bb:
    bbox_empty = make_bbox_empty("EssentialBBox", ess_bb)

views = {
    "front_ortho":  {"loc": (ecx, ecy-8, ecz), "rot": (0,0,0), "ortho": True, "scale": max(bbox_size.x, bbox_size.z)*0.6},
    "side_ortho":   {"loc": (ecx+8, ecy, ecz), "rot": (math.radians(90), 0, math.radians(90)), "ortho": True, "scale": max(bbox_size.y, bbox_size.z)*0.6},
    "top_ortho":    {"loc": (ecx, ecy, ecz+8), "rot": (0, 0, 0), "ortho": True, "scale": max(bbox_size.x, bbox_size.y)*0.6},
    "persp_3-4":   {"loc": (ecx+3, ecy-8, ecz+4), "target": bbox_center + Vector((0,0,0.3)), "ortho": False, "lens": 50},
}

for vname, vcfg in views.items():
    cam_data = bpy.data.cameras.new(f"Cam_{vname}")
    if vcfg["ortho"]:
        cam_data.type = 'ORTHO'
        cam_data.ortho_scale = vcfg["scale"]
    else:
        cam_data.type = 'PERSP'
        cam_data.lens = vcfg["lens"]
    cam_data.clip_start = 0.05; cam_data.clip_end = 100

    cam = bpy.data.objects.new(f"Cam_{vname}", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.location = Vector(vcfg["loc"])
    if "target" in vcfg:
        camera_lookat(cam, vcfg["target"], scene)
    else:
        cam.rotation_euler = vcfg["rot"]

    out = os.path.join(TMP, f"{vname}.png")
    scene.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print(f"  {vname}: {out}")

# ── PARAM TABLE (for compositing) ──────────────────────────
params = {}
params["characters"] = []
for cd in char_data:
    if cd["root"]:
        params["characters"].append({
            "label": cd["label"],
            "root_loc": [round(v,3) for v in cd["root"].location],
            "root_scale": [round(v,3) for v in cd["root"].scale],
        })
params["counters"] = [
    {"label": "Counter_L", "size": [COUNTER_W, COUNTER_D, COUNTER_H]},
    {"label": "Counter_R", "size": [COUNTER_W, COUNTER_D, COUNTER_H]},
]
if ess_bb:
    params["bbox"] = {"min": [round(v,3) for v in ess_bb[::2]], "max": [round(v,3) for v in ess_bb[1::2]]}
    params["bbox_center"] = [round(v,3) for v in bbox_center]
    params["bbox_size"] = [round(v,3) for v in bbox_size]
params["camera_3_4"] = {"loc": [round(v,3) for v in views["persp_3-4"]["loc"]], "target": [round(v,3) for v in views["persp_3-4"].get("target",(0,0,0))], "lens": 50}
params_path = os.path.join(TMP, "params.json")
with open(params_path, "w") as f: json.dump(params, f, indent=2)

print("PARAMS_JSON=" + params_path)
print("BLENDER DONE")
