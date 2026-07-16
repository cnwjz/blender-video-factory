"""
Cashier FBX isolation audit. Classify asset, test with characters, render preview.
"""
import bpy, os, json, math, shutil
from mathutils import Vector

PROJ = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane"
BLEND_IN = os.path.join(PROJ, "scene", "L1_step01_idle_grounded.blend")
FBX_PATH = r"D:\blender-video-factory\assets\third_party\pensamientoazul_supermarket\Supermercado\cashier.fbx"
OUT_BLEND = os.path.join(PROJ, "scene", "cashier_fbx_isolation_audit.blend")
PREVIEW = os.path.join(PROJ, "reviews", "CASHIER_FBX_ISOLATION_PREVIEW.png")
REP = os.path.join(PROJ, "reports", "CASHIER_FBX_ISOLATION_REPORT.md")
JSON_OUT = os.path.join(PROJ, "reports", "CASHIER_FBX_ISOLATION_STATE.json")
UPL = os.path.join(PROJ, "reviews", "UPLOAD_NEXT", "CASHIER_FBX_ISOLATION")
os.makedirs(UPL, exist_ok=True)
for f in os.listdir(UPL): os.remove(os.path.join(UPL, f))

# ── Open characters ───────────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=BLEND_IN)
bpy.context.scene.frame_set(20); bpy.context.view_layer.update()

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'; scene.render.resolution_x = 540; scene.render.resolution_y = 960
scene.eevee.use_shadows = True

# Hide all characters except Customer_01 and Employee_01
ALL_CHARS = ["Customer_01","Customer_02","Customer_03","Customer_04","Employee_01","Employee_02"]
for label in ALL_CHARS:
    root = bpy.data.objects.get(label + "_Root")
    if root and label not in ("Customer_01","Employee_01"):
        root.hide_render = True
        for c in root.children_recursive: c.hide_render = True

# ── Import cashier.fbx ────────────────────────────────────
PREV = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=FBX_PATH)
new_objs = [o for o in bpy.data.objects if o not in PREV]

print(f"Imported: {len(new_objs)} objects")
for o in new_objs:
    parent = o.parent.name if o.parent else "NONE"
    mesh_info = f"verts={len(o.data.vertices)}" if o.type == 'MESH' else ""
    arm_info = f"bones={len(o.data.bones)}" if o.type == 'ARMATURE' else ""
    print(f"  [{o.type[0]}] {o.name:40s} parent={parent:20s} {mesh_info}{arm_info}")

# ── BBox analysis ─────────────────────────────────────────
mesh_objs = [o for o in new_objs if o.type == 'MESH']
empty_objs = [o for o in new_objs if o.type == 'EMPTY']
arm_objs = [o for o in new_objs if o.type == 'ARMATURE']

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

bb = get_world_bbox(mesh_objs)
if bb:
    mx,MX,my,MY,mz,MZ = bb
    w = MX-mx; d = MY-my; h = MZ-mz
    print(f"\n  BBox: ({mx:.2f},{my:.2f},{mz:.2f}) → ({MX:.2f},{MY:.2f},{MZ:.2f})")
    print(f"  Size: W={w:.2f} D={d:.2f} H={h:.2f}")
    print(f"  Top surface Z: {MZ:.2f}")
else:
    w = d = h = MZ = 0
    print("  No mesh bbox found!")

# ── Classify asset ─────────────────────────────────────────
# Use name + dimensions to classify
names = [o.name.lower() for o in mesh_objs]
all_names = " ".join(names)
asset_type = "other"
if any(k in all_names for k in ["register","cash_reg","caja","pos"]):
    asset_type = "register_only"
elif any(k in all_names for k in ["counter","checkout","desk","countertop","mesa","mostrador"]):
    if any(k in all_names for k in ["register","cash_reg","caja","pos"]):
        asset_type = "counter_with_register"
    else:
        asset_type = "counter_only"
elif w > 1.0 and d > 0.5 and h > 0.6:
    asset_type = "counter_only"  # looks like a counter by dimensions
elif w < 0.6 and d < 0.6 and h < 0.6:
    asset_type = "register_only"  # small object, likely a register

print(f"  Asset type: {asset_type}")

# ── Character positioning ──────────────────────────────────
cust = bpy.data.objects.get("Customer_01_Root")
emp = bpy.data.objects.get("Employee_01_Root")

if cust: cust.location = Vector((0, my - 0.6, cust.location.z))
if emp: emp.location = Vector((0, my + d + 0.5, emp.location.z))
bpy.context.view_layer.update()

# ── Overlap checks ────────────────────────────────────────
def get_meshes_under(root):
    return [o for o in root.children_recursive if o.type == 'MESH']

cust_meshes = get_meshes_under(cust) if cust else []
emp_meshes = get_meshes_under(emp) if emp else []

cust_overlap = 0; emp_overlap = 0
for o in mesh_objs:
    bb_o = get_world_bbox([o])
    if bb_o:
        bb_c = get_world_bbox(cust_meshes)
        if bb_c:
            ox = max(0, min(bb_o[1],bb_c[1])-max(bb_o[0],bb_c[0]))
            oy = max(0, min(bb_o[3],bb_c[3])-max(bb_o[2],bb_c[2]))
            if ox > 0.01 and oy > 0.01: cust_overlap += 1
        bb_e = get_world_bbox(emp_meshes)
        if bb_e:
            ox = max(0, min(bb_o[1],bb_e[1])-max(bb_o[0],bb_e[0]))
            oy = max(0, min(bb_o[3],bb_e[3])-max(bb_o[2],bb_e[2]))
            if ox > 0.01 and oy > 0.01: emp_overlap += 1

# Facing
cust_facing = 0; emp_facing = 0
for label, root, target_y in [("Customer", cust, my), ("Employee", emp, my+d)]:
    if not root: continue
    arm = None
    for c in root.children:
        if c.type == 'ARMATURE': arm = c; break
    ref = arm if arm else root
    fwd = (ref.matrix_world.to_3x3() @ Vector((0,0,1))).normalized()
    desired = Vector((0, 1 if label=="Customer" else -1, 0)).normalized()
    dot = fwd.dot(desired)
    if label == "Customer": cust_facing = dot
    else: emp_facing = dot

print(f"  Overlap: cust={cust_overlap} emp={emp_overlap}")
print(f"  Facing: cust_dot={cust_facing:.3f} emp_dot={emp_facing:.3f}")

# Can support register/products?
can_reg = MZ > 0.5 and w > 0.3
can_prod = MZ > 0.5 and w > 0.4
visual_sep = cust_overlap == 0 and emp_overlap == 0 and (my + d) - my > 0.3
can_be_counter = asset_type in ("counter_only", "counter_with_register") and cust_overlap==0 and emp_overlap==0 and can_reg and can_prod and visual_sep

# ── Ground ─────────────────────────────────────────────────
bpy.ops.mesh.primitive_plane_add(size=1, location=(0,-0.5,-0.005))
g = bpy.context.object; g.name = "Floor"; g.scale = (4,5,1)
m = bpy.data.materials.new("FloorM"); m.use_nodes = True
m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.35,0.33,0.30,1.0)
g.data.materials.append(m)

# ── Lighting ───────────────────────────────────────────────
world = bpy.data.worlds.new("AuditW"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.40,0.38,0.35,1.0)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.4
bpy.ops.object.light_add(type='SUN', location=(4,-4,7))
bpy.context.object.data.energy = 3.0; bpy.context.object.data.angle = 0.12
bpy.ops.object.light_add(type='AREA', location=(-2,-1,4))
bpy.context.object.data.energy = 2.0; bpy.context.object.data.size = 4

# ── Camera ─────────────────────────────────────────────────
cam_data = bpy.data.cameras.new("AuditCam"); cam_data.type = 'ORTHO'
cam_data.ortho_scale = 6.0; cam_data.clip_start = 0.05; cam_data.clip_end = 100
cam = bpy.data.objects.new("AuditCam", cam_data); scene.collection.objects.link(cam); scene.camera = cam
cam.location = (0, -5, 5); cam.rotation_euler = (math.radians(45), 0, 0)

# ── Render ─────────────────────────────────────────────────
scene.render.filepath = PREVIEW; bpy.ops.render.render(write_still=True)
print(f"Preview: {PREVIEW}")

# ── Save ───────────────────────────────────────────────────
bpy.ops.wm.save_mainfile(filepath=OUT_BLEND)

# ── JSON ───────────────────────────────────────────────────
state = {
    "file": FBX_PATH,
    "object_names": [o.name for o in new_objs],
    "mesh_count": len(mesh_objs),
    "empty_count": len(empty_objs),
    "armature_count": len(arm_objs),
    "asset_type": asset_type,
    "bbox_min": [mx,MY,mz] if bb else None,
    "bbox_max": [MX,MY,MZ] if bb else None,
    "dimensions_xyz": [w,d,h],
    "top_surface_z": MZ,
    "can_support_register": can_reg,
    "can_support_products": can_prod,
    "customer_overlap": cust_overlap,
    "employee_overlap": emp_overlap,
    "customer_facing_dot": round(cust_facing,3),
    "employee_facing_dot": round(emp_facing,3),
    "visual_separation_pass": visual_sep,
    "can_be_checkout_counter": can_be_counter,
}
with open(JSON_OUT,"w") as f: json.dump(state, f, indent=2)

# ── Report ─────────────────────────────────────────────────
with open(REP,"w") as f:
    f.write("# Cashier FBX Isolation Audit Report\n\n")
    f.write(f"File: {FBX_PATH}\n\n")
    f.write(f"## Objects\n\n{len(new_objs)} objects imported:\n")
    for o in new_objs:
        f.write(f"- [{o.type[0]}] {o.name} (parent={o.parent.name if o.parent else 'NONE'})\n")
    f.write(f"\n## Structure\n\n- Meshes: {len(mesh_objs)}\n- Empties: {len(empty_objs)}\n- Armatures: {len(arm_objs)}\n")
    f.write(f"\n## BBox\n\n- Min: ({mx:.2f},{my:.2f},{mz:.2f})\n- Max: ({MX:.2f},{MY:.2f},{MZ:.2f})\n")
    f.write(f"- Size: {w:.2f}×{d:.2f}×{h:.2f}\n- Top surface Z: {MZ:.2f}\n")
    f.write(f"\n## Classification\n\n**{asset_type}**\n\n")
    f.write(f"## Fit Test\n\n")
    f.write(f"- Customer overlap: {cust_overlap}\n- Employee overlap: {emp_overlap}\n")
    f.write(f"- Customer facing dot: {cust_facing:.3f}\n- Employee facing dot: {emp_facing:.3f}\n")
    f.write(f"- Can support register: {can_reg}\n- Can support products: {can_prod}\n")
    f.write(f"- Visual separation: {visual_sep}\n")
    f.write(f"- **Can serve as checkout counter: {can_be_counter}**\n")

# ── UPLOAD_NEXT ────────────────────────────────────────────
shutil.copy(PREVIEW, os.path.join(UPL, "CASHIER_FBX_ISOLATION_PREVIEW.png"))
shutil.copy(REP, os.path.join(UPL, "CASHIER_FBX_ISOLATION_REPORT.md"))

print(f"\nSUMMARY: type={asset_type} can_counter={can_be_counter}")
print("AUDIT DONE")
