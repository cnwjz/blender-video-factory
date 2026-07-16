"""
L1-B: Market asset layout. Import Mini Market GLB, build counters, position characters, validate.
"""
import bpy, os, json, math, shutil
from mathutils import Vector

PROJ = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane"
BLEND_IN = os.path.join(PROJ, "scene", "L1_step01_idle_grounded.blend")
BLEND_OUT = os.path.join(PROJ, "scene", "L1_step02_checkout.blend")
MK_GLB = os.path.join(PROJ, "assets", "imported", "kenney_mini-market", "Models", "GLB format")
REV = os.path.join(PROJ, "reviews")
REP = os.path.join(PROJ, "reports")
UPL = os.path.join(PROJ, "reviews", "UPLOAD_NEXT", "L1_B")
os.makedirs(REV, exist_ok=True); os.makedirs(REP, exist_ok=True); os.makedirs(UPL, exist_ok=True)
for f in os.listdir(UPL): os.remove(os.path.join(UPL, f))

# ── Open ───────────────────────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=BLEND_IN)
bpy.context.scene.frame_set(20); bpy.context.view_layer.update()

INSTANCES = ["Customer_01","Customer_02","Customer_03","Customer_04","Employee_01","Employee_02"]
PREV = set()

def snap_objs(): global PREV; PREV = set(bpy.data.objects)
def new_objs(): return [o for o in bpy.data.objects if o not in PREV]
def get_world_bbox(mesh_list):
    dg = bpy.context.evaluated_depsgraph_get(); pts = []
    for o in mesh_list:
        if o.type != 'MESH': continue
        eo = o.evaluated_get(dg); m = eo.to_mesh()
        if m is None: continue
        for v in m.vertices: pts.append(eo.matrix_world @ v.co)
        eo.to_mesh_clear()
    if not pts: return None
    xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
    return (min(xs),max(xs),min(ys),max(ys),min(zs),max(zs))

def imp_g(path):
    snap_objs(); bpy.ops.import_scene.gltf(filepath=os.path.join(MK_GLB, path))
    return new_objs()

def make_mat(name, rgb):
    m = bpy.data.materials.new(name); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*rgb, 1.0)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.6
    return m

# ── Import market assets ───────────────────────────────────
print("Importing Mini Market...")
# Two cash registers
reg_L = imp_g("cash-register.glb")
reg_R = imp_g("cash-register.glb")
# Display bread + fruit
bread = imp_g("display-bread.glb")
fruit = imp_g("display-fruit.glb")
# Freezer (background)
freezer = imp_g("freezers-standing.glb")
# Shopping basket
basket = imp_g("shopping-basket.glb")

print(f"  Scene objects: {len(bpy.data.objects)}")

# ── Build two counters ─────────────────────────────────────
COUNTER_W = 1.9; COUNTER_D = 0.85; COUNTER_H = 1.15
LANE_L_X = -2.0; LANE_R_X = 2.0; COUNTER_Y = 2.0

counters = {}
for label, cx in [("Counter_L", LANE_L_X), ("Counter_R", LANE_R_X)]:
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, COUNTER_Y, COUNTER_H/2))
    c = bpy.context.object; c.name = label
    c.scale = (COUNTER_W/2, COUNTER_D/2, COUNTER_H/2)
    m = make_mat(f"{label}_M", (0.74, 0.70, 0.63))
    c.data.materials.append(m)
    # Bevel
    bm = c.modifiers.new("Bevel", 'BEVEL'); bm.width = 0.02; bm.segments = 2
    # Conveyor belt
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, COUNTER_Y, COUNTER_H + 0.02))
    b = bpy.context.object; b.name = f"{label}_Belt"; b.scale = (1.1, 0.35, 0.02)
    b.data.materials.append(make_mat(f"{label}_BeltM", (0.12, 0.10, 0.08)))
    counters[label] = (c, b)

# ── Position market assets ─────────────────────────────────
# Cash registers on counters, employee side
for reg_objs, cx in [(reg_L, LANE_L_X), (reg_R, LANE_R_X)]:
    for o in reg_objs:
        if o.type == 'MESH':
            o.location = (cx, COUNTER_Y + 0.15, COUNTER_H + 0.03)
            o.scale = (1.5, 1.5, 1.5)

# Display bread + fruit on counters (customer side)
for o in bread:
    if o.type == 'MESH': o.location = (LANE_L_X - 0.3, COUNTER_Y - 0.1, COUNTER_H + 0.03)
for o in fruit:
    if o.type == 'MESH': o.location = (LANE_R_X + 0.3, COUNTER_Y - 0.1, COUNTER_H + 0.03)

# Freezer in background
for o in freezer:
    if o.type == 'MESH': o.location = (0, COUNTER_Y + 1.5, 0)
    o.scale = (1.5, 1.5, 1.5) if hasattr(o,'scale') else None

# Basket near left queue
for o in basket:
    if o.type == 'MESH': o.location = (LANE_L_X + 0.5, -1.0, 0)

# ── Floor + Wall ──────────────────────────────────────────
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -1.0, -0.005))
f = bpy.context.object; f.name = "Floor"; f.scale = (6, 8, 1)
f.data.materials.append(make_mat("FloorM", (0.35, 0.33, 0.30)))

bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 4.5, 2.5))
w = bpy.context.object; w.name = "Wall"; w.scale = (6.5, 0.2, 5.0)
w.data.materials.append(make_mat("WallM", (0.17, 0.15, 0.13)))

# ── Layout characters ─────────────────────────────────────
# Employees behind counters, rotated 180 Z to face -Y (toward customers)
# Customers in front, facing +Y (face +Y default)
layout = {
    "Employee_01": (LANE_L_X, COUNTER_Y + 0.8, 0, 0),    # rotate Z from π→0 to face -Y
    "Employee_02": (LANE_R_X, COUNTER_Y + 0.8, 0, 0),    # rotate Z from π→0 to face -Y
    "Customer_01": (LANE_L_X, COUNTER_Y - 1.0, 0, math.pi),     # keep library Z=π → face +Y
    "Customer_02": (LANE_L_X, COUNTER_Y - 2.5, 0, math.pi),
    "Customer_03": (LANE_L_X, COUNTER_Y - 4.0, 0, math.pi),
    "Customer_04": (LANE_R_X, COUNTER_Y - 1.0, 0, math.pi),     # keep library Z=π → face +Y
}

for label, (x, y, z_off, rz) in layout.items():
    root = bpy.data.objects.get(label + "_Root")
    if root:
        root.location.x = x
        root.location.y = y
        root.location.z = root.location.z + z_off
        # Only Z rotation changes allowed
        rot = root.rotation_euler.copy()
        rot.z = rz
        root.rotation_euler = rot
        print(f"  {label}: ({x:.1f}, {y:.1f}, {root.location.z:.3f}) rz={rz}")

# ── VALIDATION ─────────────────────────────────────────────
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
issues = []
overlap_count = 0
spacing_fails = 0
facing_fails = 0
ground_fails = 0

# Facing check
def world_forward(root):
    arm = None
    for c in root.children:
        if c.type == 'ARMATURE': arm = c; break
    ref = arm if arm else root
    # Try local +Z first (model forward per L1-A2)
    return (ref.matrix_world.to_3x3() @ Vector((0,0,1))).normalized()

for label, (cx, cy, _, _) in layout.items():
    root = bpy.data.objects.get(label + "_Root")
    if not root: continue
    fwd = world_forward(root)
    pos = root.location
    if "Employee" in label:
        target = Vector((pos.x, COUNTER_Y - 1.0, pos.z))
    else:
        target = Vector((pos.x, COUNTER_Y, pos.z))
    desired = (target - pos).normalized()
    dot = fwd.dot(desired)
    print(f"  FACE {label}: fwd=({fwd.x:.3f},{fwd.y:.3f},{fwd.z:.3f}) desired=({desired.x:.3f},{desired.y:.3f},{desired.z:.3f}) dot={dot:.3f}")
    if dot < 0.95: facing_fails += 1; issues.append(f"{label}: facing dot={dot:.3f}")

# Character-Character overlap
chars_root_names = [l + "_Root" for l in INSTANCES]
char_roots = [bpy.data.objects.get(n) for n in chars_root_names if bpy.data.objects.get(n)]
for i, r1 in enumerate(char_roots):
    for j, r2 in enumerate(char_roots):
        if j <= i: continue
        # Get all meshes under each root
        def root_meshes(r):
            out = []
            for c in r.children_recursive:
                if c.type == 'MESH': out.append(c)
            return out
        m1 = root_meshes(r1); m2 = root_meshes(r2)
        bb1 = get_world_bbox(m1); bb2 = get_world_bbox(m2)
        if bb1 and bb2:
            ox = max(0, min(bb1[1],bb2[1]) - max(bb1[0],bb2[0]))
            oy = max(0, min(bb1[3],bb2[3]) - max(bb1[2],bb2[2]))
            if ox > 0 and oy > 0:
                overlap_count += 1; issues.append(f"Char overlap: {r1.name} vs {r2.name}")

# Spacing: left queue Y must be decreasing
left_queue_y = []
for l in ["Customer_01","Customer_02","Customer_03"]:
    r = bpy.data.objects.get(l + "_Root")
    if r: left_queue_y.append(r.location.y)
for i in range(len(left_queue_y)-1):
    if left_queue_y[i] <= left_queue_y[i+1]:
        spacing_fails += 1

# Ground contact
for r in char_roots:
    meshes = []
    for c in r.children_recursive:
        if c.type == 'MESH': meshes.append(c)
    bb = get_world_bbox(meshes)
    if bb and abs(bb[4]) > 0.12:
        ground_fails += 1; issues.append(f"{r.name}: lowest_z={bb[4]:.3f}")

# ── Count regs, counters ──────────────────────────────────
reg_count = sum(1 for o in bpy.data.objects if 'register' in o.name.lower() and o.type == 'MESH')
counter_count = len([o for o in bpy.data.objects if o.name in ('Counter_L', 'Counter_R')])
char_count = len(char_roots)

all_pass = (
    char_count == 6 and counter_count >= 2 and reg_count >= 2 and
    overlap_count == 0 and spacing_fails == 0 and facing_fails == 0 and ground_fails == 0
)

print(f"\n  Characters: {char_count}/6 Counters: {counter_count}/2 Registers: {reg_count}/2")
print(f"  Overlaps: {overlap_count} Spacing: {spacing_fails} Facing: {facing_fails} Ground: {ground_fails}")
print(f"  ALL_PASS={all_pass}")

# ── Save, reopen, revalidate ──────────────────────────────
bpy.ops.wm.save_mainfile(filepath=BLEND_OUT)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=BLEND_OUT)
bpy.context.scene.frame_set(20); bpy.context.view_layer.update()

re_char = len([o for o in bpy.data.objects if o.name.endswith('_Root')])
re_reg = sum(1 for o in bpy.data.objects if 'register' in o.name.lower() and o.type == 'MESH')
reopen_ok = (re_char == 6 and re_reg >= 2)
print(f"  Reopen: chars={re_char}/6 regs={re_reg}/2 OK={reopen_ok}")

# ── Tech camera + render ───────────────────────────────────
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'; scene.render.resolution_x = 540; scene.render.resolution_y = 960
scene.eevee.use_shadows = True
world = bpy.data.worlds.new("TechW"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.35, 0.33, 0.30, 1.0)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35
bpy.ops.object.light_add(type='SUN', location=(4, -4, 7))
bpy.context.object.data.energy = 3.0; bpy.context.object.data.angle = 0.12
bpy.ops.object.light_add(type='AREA', location=(-2, -1, 4))
bpy.context.object.data.energy = 2.0; bpy.context.object.data.size = 4

cam_data = bpy.data.cameras.new("TechCam"); cam_data.type = 'ORTHO'
cam_data.ortho_scale = 16.0; cam_data.clip_start = 0.05; cam_data.clip_end = 100
cam = bpy.data.objects.new("TechCam", cam_data); scene.collection.objects.link(cam); scene.camera = cam
cam.location = (0, -5, 10); cam.rotation_euler = (math.radians(48), 0, 0)

preview = os.path.join(REV, "L1_B_layout_preview.png")
scene.render.filepath = preview; bpy.ops.render.render(write_still=True)
print(f"  Preview: {preview}")

# ── Reports ────────────────────────────────────────────────
json_path = os.path.join(REP, "L1_B_layout_state.json")
with open(json_path, "w") as f:
    json.dump({
        "characters": char_count, "counters": counter_count, "registers": reg_count,
        "overlap_count": overlap_count, "spacing_fails": spacing_fails,
        "facing_fails": facing_fails, "ground_fails": ground_fails,
        "all_pass": all_pass, "reopen_ok": reopen_ok, "issues": issues
    }, f, indent=2)

rep_path = os.path.join(REP, "L1_B_LAYOUT_REPORT.md")
with open(rep_path, "w") as rf:
    rf.write("# L1-B Layout Report\n\n")
    rf.write(f"Input: {BLEND_IN}\n\n")
    rf.write(f"## Counts\n\n- Characters: {char_count}/6\n- Counters: {counter_count}/2\n- Registers: {reg_count}/2\n\n")
    rf.write(f"## Validation\n\n")
    rf.write(f"- Character overlap: {overlap_count}\n- Spacing fails: {spacing_fails}\n- Facing fails: {facing_fails}\n- Ground fails: {ground_fails}\n\n")
    rf.write(f"- All pass: {all_pass}\n- Reopen OK: {reopen_ok}\n\n")
    if issues:
        rf.write("## Issues\n\n")
        for i in issues: rf.write(f"- {i}\n")

import shutil
shutil.copy(preview, os.path.join(UPL, "L1_B_layout_preview.png"))
shutil.copy(rep_path, os.path.join(UPL, "L1_B_LAYOUT_REPORT.md"))

print(f"  JSON={json_path}")
print(f"  REPORT={rep_path}")
print(f"  UPLOAD={UPL}")
print("L1-B COMPLETE")
