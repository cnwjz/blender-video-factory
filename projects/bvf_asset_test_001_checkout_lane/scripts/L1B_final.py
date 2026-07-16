"""
L1-B FINAL: Import cashier.fbx twice, standardize, Z90 rotate, position chars, validate, render.
"""
import bpy, os, math, shutil
from mathutils import Vector

PROJ = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane"
BLEND_IN = os.path.join(PROJ, "scene", "L1_step01_idle_grounded.blend")
FBX_PATH = r"D:\blender-video-factory\assets\third_party\pensamientoazul_supermarket\Supermercado\cashier.fbx"
OUT_BLEND = os.path.join(PROJ, "scene", "L1_step02_checkout_final.blend")
PREVIEW = os.path.join(PROJ, "reviews", "L1_B_FINAL_preview.png")
REP = os.path.join(PROJ, "reports", "L1_B_FINAL_REPORT.md")
UPL = os.path.join(PROJ, "reviews", "UPLOAD_NEXT", "L1_B_FINAL")
COUNTER_SF = 5.997
CX_L, CX_R = -1.8, 1.8
os.makedirs(UPL, exist_ok=True)
for f in os.listdir(UPL): os.remove(os.path.join(UPL, f))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=BLEND_IN)
bpy.context.scene.frame_set(20); bpy.context.view_layer.update()
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'; scene.render.resolution_x = 540; scene.render.resolution_y = 960
scene.eevee.use_shadows = True

def get_bbox(mesh_list):
    dg = bpy.context.evaluated_depsgraph_get(); pts = []
    for o in mesh_list:
        if o.type != 'MESH': continue
        eo = o.evaluated_get(dg); m = eo.to_mesh()
        if m is None: continue
        for v in m.vertices: pts.append(eo.matrix_world @ v.co)
        eo.to_mesh_clear()
    if not pts: return None
    xs=[p.x for p in pts]; ys=[p.y for p in pts]; zs=[p.z for p in pts]
    return (min(xs),max(xs),min(ys),max(ys),min(zs),max(zs))

def import_cashier(label):
    PREV = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=FBX_PATH)
    new = [o for o in bpy.data.objects if o not in PREV]
    meshes = [o for o in new if o.type == 'MESH']
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0,0,0))
    root = bpy.context.object; root.name = label; root.empty_display_size = 0.1
    for m in meshes: m.parent = root
    root.scale = (COUNTER_SF, COUNTER_SF, COUNTER_SF)
    bpy.context.view_layer.update()
    bb = get_bbox(meshes)
    if bb: root.location.z = -bb[4]
    bpy.context.view_layer.update()
    return root, meshes

# Import 2 counters
left_root, left_meshes = import_cashier("Cashier_Left_Root")
right_root, right_meshes = import_cashier("Cashier_Right_Root")

# NO Z-rotation — keep original orientation (counter front faces +Y)
# Position at target X,Y
for root, cx, cy in [(left_root, CX_L, 0.30), (right_root, CX_R, 0.30)]:
    bpy.context.view_layer.update()
    bb = get_bbox([o for o in root.children_recursive if o.type=='MESH'])
    if bb:
        bcx = (bb[0]+bb[1])/2; bcy = (bb[2]+bb[3])/2
        root.location.x += cx - bcx
        root.location.y += cy - bcy
        print(f"  {root.name}: bbox({bb[0]:.2f},{bb[2]:.2f})→({bb[1]:.2f},{bb[3]:.2f}) target=({cx},{cy})")

bpy.context.view_layer.update()
bb_L = get_bbox([o for o in left_root.children_recursive if o.type=='MESH'])
bb_R = get_bbox([o for o in right_root.children_recursive if o.type=='MESH'])
print(f"  Left: ({bb_L[0]:.2f},{bb_L[2]:.2f},{bb_L[4]:.2f})→({bb_L[1]:.2f},{bb_L[3]:.2f},{bb_L[5]:.2f})")
print(f"  Right: ({bb_R[0]:.2f},{bb_R[2]:.2f},{bb_R[4]:.2f})→({bb_R[1]:.2f},{bb_R[3]:.2f},{bb_R[5]:.2f})")

# Without Z90: counter W=3.1(X) D=0.38(Y) H=0.95(Z)
# Counter front is +Y side (customer approach), back is -Y side (employee area)
# Counter Y range: front ~ bb[3], back ~ bb[2]
counter_front_y = max(bb_L[3], bb_R[3]) if bb_L and bb_R else 0.5
counter_back_y = min(bb_L[2], bb_R[2]) if bb_L and bb_R else 0.1

# Customers in front of counter (+Y side)
cust_Y = [
    counter_front_y + 1.0,
    counter_front_y + 2.4,
    counter_front_y + 3.8,
]
for label, cy in [("Customer_01", cust_Y[0]), ("Customer_02", cust_Y[1]), ("Customer_03", cust_Y[2])]:
    root = bpy.data.objects.get(label + "_Root")
    if root:
        root.location = Vector((CX_L, cy, root.location.z))
        root.rotation_euler.z = 0  # face -Y toward counter
        print(f"  {label}: X={CX_L} Y={cy:.2f}")

# Right customer
cr = bpy.data.objects.get("Customer_04_Root")
if cr:
    cr.location = Vector((CX_R, cust_Y[0], cr.location.z))
    cr.rotation_euler.z = 0  # face -Y toward counter

# Employees behind counter (-Y side), centered on counter X
emp_L = bpy.data.objects.get("Employee_01_Root")
emp_R = bpy.data.objects.get("Employee_02_Root")
if emp_L: emp_L.location = Vector((CX_L, counter_back_y - 0.5, emp_L.location.z)); emp_L.rotation_euler.z = math.pi  # face +Y toward customers
if emp_R: emp_R.location = Vector((CX_R, counter_back_y - 0.5, emp_R.location.z)); emp_R.rotation_euler.z = math.pi
bpy.context.view_layer.update()

# Products on counter tops
def make_box(x, y, z, w, d, h, name):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, z+h/2))
    o = bpy.context.object; o.name = name; o.scale = (w/2, d/2, h/2)
    m = bpy.data.materials.new(f"{name}M"); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.65,0.55,0.42,1.0)
    o.data.materials.append(m)
    return o

ctz = bb_L[5]
make_box(CX_L, counter_front_y-0.3, ctz, 0.12, 0.10, 0.08, "Product_L")
make_box(CX_R, counter_front_y-0.3, ctz, 0.12, 0.10, 0.08, "Product_R")

# Basket on ground
bpy.ops.mesh.primitive_cylinder_add(radius=0.15, depth=0.15, location=(CX_R+0.5, counter_front_y-0.5, 0.075))
basket = bpy.context.object; basket.name = "Basket"
bm = bpy.data.materials.new("BasketM"); bm.use_nodes = True
bm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.55,0.45,0.35,1.0)
basket.data.materials.append(bm)

# Floor
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -2, -0.005))
g = bpy.context.object; g.name = "Floor"; g.scale = (5, 10, 1)
gm = bpy.data.materials.new("FloorM"); gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.35,0.33,0.30,1.0)
g.data.materials.append(gm)

# Lighting
world = bpy.data.worlds.new("W"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.38,0.35,0.32,1.0)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.4
bpy.ops.object.light_add(type='SUN', location=(5,-5,8))
bpy.context.object.data.energy = 3.0; bpy.context.object.data.angle = 0.12

# Tech camera
cam_data = bpy.data.cameras.new("Cam"); cam_data.type = 'ORTHO'
cam_data.ortho_scale = 16.0; cam_data.clip_start = 0.05; cam_data.clip_end = 100
cam = bpy.data.objects.new("Cam", cam_data); scene.collection.objects.link(cam); scene.camera = cam
cam.location = (3, -10, 9)
cam.rotation_euler = (Vector((0, -3, 1.0)) - cam.location).to_track_quat('-Z','Y').to_euler()

# Validation
bpy.context.view_layer.update()
char_roots = [bpy.data.objects.get(n) for n in ["Customer_01_Root","Customer_02_Root","Customer_03_Root","Customer_04_Root","Employee_01_Root","Employee_02_Root"] if bpy.data.objects.get(n)]
counter_meshes = list(left_root.children_recursive) + list(right_root.children_recursive)
counter_meshes = [o for o in counter_meshes if o.type=='MESH']

cc_ov = 0; ctr_ov = 0; gf = 0
for i, r1 in enumerate(char_roots):
    m1 = [o for o in r1.children_recursive if o.type=='MESH']
    bb1 = get_bbox(m1)
    if not bb1: continue
    if abs(bb1[4]) > 0.12: gf += 1
    for j, r2 in enumerate(char_roots):
        if j <= i: continue
        m2 = [o for o in r2.children_recursive if o.type=='MESH']
        bb2 = get_bbox(m2)
        if not bb2: continue
        ox = max(0,min(bb1[1],bb2[1])-max(bb1[0],bb2[0]))
        oy = max(0,min(bb1[3],bb2[3])-max(bb1[2],bb2[2]))
        if ox>0.03 and oy>0.03: cc_ov += 1
    for co in counter_meshes:
        bb_c = get_bbox([co])
        if not bb_c: continue
        ox = max(0,min(bb1[1],bb_c[1])-max(bb1[0],bb_c[0]))
        oy = max(0,min(bb1[3],bb_c[3])-max(bb1[2],bb_c[2]))
        if ox>0.03 and oy>0.03: ctr_ov += 1

pf = sum(1 for o in bpy.data.objects if o.name.startswith('Product_') and o.location.z < ctz-0.01)
bf = 1 if abs(basket.location.z-0.075) > 0.03 else 0
all_pass = len(char_roots)==6 and cc_ov==0 and ctr_ov==0 and gf==0 and pf==0 and bf==0
print(f"  Chars:{len(char_roots)}/6 CC:{cc_ov} CTR:{ctr_ov} GR:{gf} PF:{pf} BF:{bf} PASS={all_pass}")

# Save + render
bpy.ops.wm.save_mainfile(filepath=OUT_BLEND)
scene.render.filepath = PREVIEW; bpy.ops.render.render(write_still=True)

# Report
with open(REP,"w") as f:
    f.write("# L1-B FINAL Report\n\n")
    f.write(f"Left bbox: {bb_L}\nRight bbox: {bb_R}\n\n")
    for r in char_roots: f.write(f"- {r.name}: {r.location}\n")
    f.write(f"\nCC overlap:{cc_ov} CTR overlap:{ctr_ov} Ground:{gf} Prod float:{pf} Basket:{bf}\n")
    f.write(f"All pass: {all_pass}\n")

shutil.copy(PREVIEW, os.path.join(UPL, "L1_B_FINAL_preview.png"))
shutil.copy(REP, os.path.join(UPL, "L1_B_FINAL_REPORT.md"))
print(f"ALL_PASS={all_pass}")
print("DONE")
