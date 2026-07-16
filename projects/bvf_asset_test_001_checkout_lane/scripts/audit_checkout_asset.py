"""
Checkout asset fit audit: test 4 Mini Market candidates as counter proxies.
"""
import bpy, os, json, math, shutil
from mathutils import Vector

PROJ = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane"
BLEND_IN = os.path.join(PROJ, "scene", "L1_step01_idle_grounded.blend")
MK_GLB = os.path.join(PROJ, "assets", "imported", "kenney_mini-market", "Models", "GLB format")
DIAG = os.path.join(PROJ, "reviews", "checkout_asset_fit")
UPL = os.path.join(PROJ, "reviews", "UPLOAD_NEXT", "CHECKOUT_ASSET_FIT")
REP_DIR = os.path.join(PROJ, "reports")
OUT_BLEND = os.path.join(PROJ, "scene", "checkout_asset_fit_test.blend")
os.makedirs(DIAG, exist_ok=True); os.makedirs(UPL, exist_ok=True)
for f in os.listdir(UPL): os.remove(os.path.join(UPL, f))

CANDIDATES = [
    ("C01", "bottle-return.glb"),
    ("C02", "shelf-end.glb"),
    ("C03", "display-bread.glb"),
    ("C04", "display-fruit.glb"),
]

# ── Open idle characters ──────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=BLEND_IN)
bpy.context.scene.frame_set(20); bpy.context.view_layer.update()

# ── Scene-wide setup ──────────────────────────────────────
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 540; scene.render.resolution_y = 960
scene.eevee.use_shadows = True
world = bpy.data.worlds.new("FitW"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.40, 0.38, 0.35, 1.0)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.4
bpy.ops.object.light_add(type='SUN', location=(4, -4, 7))
bpy.context.object.data.energy = 3.0; bpy.context.object.data.angle = 0.12
bpy.ops.object.light_add(type='AREA', location=(-2, -1, 4))
bpy.context.object.data.energy = 2.0; bpy.context.object.data.size = 4

PREV = set()
def snap(): global PREV; PREV = set(bpy.data.objects)
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

def make_mat(name, rgb):
    m = bpy.data.materials.new(name); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*rgb,1.0)
    return m

# Import all 4 candidates once
imported = {}
for cid, fname in CANDIDATES:
    snap()
    bpy.ops.import_scene.gltf(filepath=os.path.join(MK_GLB, fname))
    objs = [o for o in new_objs() if o.type == 'MESH']
    imported[cid] = {"file": fname, "objects": objs}
    print(f"  {cid} {fname}: {len(objs)} meshes")

# Import cash-register
snap(); bpy.ops.import_scene.gltf(filepath=os.path.join(MK_GLB, "cash-register.glb"))
reg_objs = [o for o in new_objs() if o.type == 'MESH']

# Duplicate register 3 more times (one per zone)
reg_copies = [reg_objs[0]]  # first is original
for i in range(3):
    copy_o = reg_objs[0].copy(); copy_o.data = reg_objs[0].data
    copy_o.name = f"cash-register_copy{i}"
    scene.collection.objects.link(copy_o)
    reg_copies.append(copy_o)
print(f"  Registers: {len(reg_copies)}")

# ── Ground planes ──────────────────────────────────────────
for gi in range(4):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(gi*5 - 7.5, -0.5, -0.005))
    f = bpy.context.object; f.name = f"Floor_{gi}"; f.scale = (2, 3.5, 1)
    f.data.materials.append(make_mat(f"FloorM_{gi}", (0.35, 0.33, 0.30)))

# ── Character references ──────────────────────────────────
cust_root = bpy.data.objects.get("Customer_01_Root")
emp_root = bpy.data.objects.get("Employee_01_Root")

# ── Duplicate characters 3 more times (for 4 total test zones) ──
# Create duplicates of the customer/employee hierarchy
def dup_char(src_root, new_name):
    """Duplicate a character root and all its children."""
    new_root = src_root.copy()
    new_root.data = src_root.data  # Empty data
    new_root.name = new_name
    scene.collection.objects.link(new_root)
    # Copy children
    for child in src_root.children:
        new_child = child.copy()
        if child.data: new_child.data = child.data
        new_child.name = new_name.replace("_Root", "") + "_" + child.name.split("_", 1)[-1]
        new_child.parent = new_root
        scene.collection.objects.link(new_child)
        # Copy children's children (meshes)
        for gc in child.children:
            new_gc = gc.copy()
            if gc.data: new_gc.data = gc.data
            new_gc.parent = new_child
            scene.collection.objects.link(new_gc)
    return new_root

cust_copies = [cust_root]
emp_copies = [emp_root]
for i in range(1, 4):
    cust_copies.append(dup_char(cust_root, f"Customer_A{i+1}_Root"))
    emp_copies.append(dup_char(emp_root, f"Employee_A{i+1}_Root"))

# Hide the last 3 character sets
for i in range(1, 4):
    for c in cust_copies[i].children_recursive: c.hide_render = True
    cust_copies[i].hide_render = True
    for c in emp_copies[i].children_recursive: c.hide_render = True
    emp_copies[i].hide_render = True

# ── Test each candidate ────────────────────────────────────
results = {}
for ci, (cid, cdata) in enumerate(imported.items()):
    meshes = cdata["objects"]
    bb = get_world_bbox(meshes)
    if not bb: results[cid] = {"error": "no bbox"}; continue
    mx, MX, my, MY, mz, MZ = bb
    raw_w = MX-mx; raw_d = MY-my; raw_h = MZ-mz

    # Target counter height 0.80-1.10, width ~1.5-2.0
    target_h = 0.95
    sf = target_h / max(raw_h, 0.001)
    # Clamp scale to reasonable range
    sf = max(0.3, min(3.0, sf))

    # Position in test zone
    zone_x = ci * 5 - 7.5
    # Move candidate to zone, center it
    for o in meshes:
        o.location.x += zone_x - (mx+MX)/2
        o.location.y += 0 - (my+MY)/2
        o.location.z += 0 - mz
        o.scale *= sf

    # Re-measure
    bpy.context.view_layer.update()
    bb2 = get_world_bbox(meshes)
    if not bb2: continue
    mx2, MX2, my2, MY2, mz2, MZ2 = bb2
    final_h = MZ2 - mz2; final_w = MX2 - mx2; final_d = MY2 - my2
    surface_z = MZ2  # top of counter

    # Position cash register on counter (back side)
    reg_x = (mx2 + MX2) / 2
    reg_y = my2 + final_d * 0.65  # back side of counter
    reg = reg_copies[ci]
    reg.location = (reg_x, reg_y, surface_z + 0.02)
    reg.hide_render = False

    # Customer in front
    cust = cust_copies[ci]
    cust.location = Vector((reg_x, my2 - 0.7, cust.location.z))
    for c in cust.children_recursive: c.hide_render = False
    cust.hide_render = False

    # Employee behind
    emp = emp_copies[ci]
    emp.location = Vector((reg_x, my2 + final_d + 0.5, emp.location.z))
    for c in emp.children_recursive: c.hide_render = False
    emp.hide_render = False

    bpy.context.view_layer.update()

    # Checks
    cust_meshes = [o for o in cust.children_recursive if o.type == 'MESH']
    emp_meshes = [o for o in emp.children_recursive if o.type == 'MESH']
    bb_cust = get_world_bbox(cust_meshes)
    bb_emp = get_world_bbox(emp_meshes)

    # Overlap: bbox intersection
    overlap_cust = 0; overlap_emp = 0
    for o in meshes:
        bb_o = get_world_bbox([o])
        if bb_o and bb_cust:
            ox = max(0, min(bb_o[1],bb_cust[1])-max(bb_o[0],bb_cust[0]))
            oy = max(0, min(bb_o[3],bb_cust[3])-max(bb_o[2],bb_cust[2]))
            if ox > 0.02 and oy > 0.02: overlap_cust += 1
        if bb_o and bb_emp:
            ox = max(0, min(bb_o[1],bb_emp[1])-max(bb_o[0],bb_emp[0]))
            oy = max(0, min(bb_o[3],bb_emp[3])-max(bb_o[2],bb_emp[2]))
            if ox > 0.02 and oy > 0.02: overlap_emp += 1

    # Separation: can customer and employee be on opposite sides?
    cust_y = cust.location.y; emp_y = emp.location.y
    separation = emp_y - cust_y
    counter_span = final_d
    separated = separation > counter_span * 0.6  # counter should be between them

    # Cash register on top surface
    can_place_reg = surface_z > 0.5 and final_w > 0.8 and final_d > 0.4

    results[cid] = {
        "file": cdata["file"],
        "raw_bbox": [round(v,3) for v in bb],
        "scale": round(sf, 3),
        "final_w": round(final_w, 3),
        "final_d": round(final_d, 3),
        "final_h": round(final_h, 3),
        "overlap_cust": overlap_cust,
        "overlap_emp": overlap_emp,
        "separated": separated,
        "can_place_reg": can_place_reg,
        "surface_z": round(surface_z, 3),
        "issues": []
    }

    # Print for real-time feedback
    fits = overlap_cust == 0 and overlap_emp == 0 and separated and can_place_reg
    print(f"  {cid}: w={final_w:.2f} d={final_d:.2f} h={final_h:.2f} sf={sf:.2f} overlap(C={overlap_cust},E={overlap_emp}) sep={separated} reg={can_place_reg} FIT={fits}")

# ── Tech camera (one for all 4 zones) ─────────────────────
cam_data = bpy.data.cameras.new("FitCam"); cam_data.type = 'ORTHO'
cam_data.ortho_scale = 18.0; cam_data.clip_start = 0.05; cam_data.clip_end = 100
cam = bpy.data.objects.new("FitCam", cam_data)
scene.collection.objects.link(cam); scene.camera = cam
cam.location = (0, -10, 8); cam.rotation_euler = (math.radians(48), 0, 0)

# ── Save ───────────────────────────────────────────────────
bpy.ops.wm.save_mainfile(filepath=OUT_BLEND)
print(f"Saved: {OUT_BLEND}")

# ── Render 4 individual frames + composite ─────────────────
rendered = {}
for ci, cid in enumerate([c[0] for c in CANDIDATES]):
    out = os.path.join(DIAG, f"fit_{cid}.png")
    scene.render.filepath = out
    bpy.ops.render.render(write_still=True)
    rendered[cid] = out
    print(f"  Render {cid}: {out}")

# Write render paths for system Python composite
paths_file = os.path.join(DIAG, "_paths.json")
with open(paths_file, "w") as f: json.dump(rendered, f, indent=2)

# Write report
rep_path = os.path.join(REP_DIR, "CHECKOUT_ASSET_FIT_REPORT.md")
with open(rep_path, "w") as rf:
    rf.write("# Checkout Asset Fit Report\n\n")
    for cid in [c[0] for c in CANDIDATES]:
        r = results.get(cid, {"error": "no data"})
        if "error" in r:
            rf.write(f"## {cid}\n\nError: {r['error']}\n\n")
            continue
        fits = r["overlap_cust"]==0 and r["overlap_emp"]==0 and r["separated"] and r["can_place_reg"]
        rf.write(f"## {cid}: {r['file']}\n\n")
        rf.write(f"- Raw bbox: {r['raw_bbox']}\n")
        rf.write(f"- Scale: {r['scale']}\n")
        rf.write(f"- Final W×D×H: {r['final_w']}×{r['final_d']}×{r['final_h']}\n")
        rf.write(f"- Surface Z: {r['surface_z']}\n")
        rf.write(f"- Can place register: {r['can_place_reg']}\n")
        rf.write(f"- Overlap customer: {r['overlap_cust']}\n")
        rf.write(f"- Overlap employee: {r['overlap_emp']}\n")
        rf.write(f"- Separated (both sides): {r['separated']}\n")
        rf.write(f"- **Programmatic fit: {fits}**\n\n")

print(f"REPORT={rep_path}")
print(f"PATHS={paths_file}")
print("AUDIT DONE")
