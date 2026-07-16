"""
L1-B2: Rotate counters 90deg Z, align along Y axis, test portrait framing feasibility.
"""
import bpy, os, math, shutil
from mathutils import Vector
import bpy_extras.object_utils as obj_utils

PROJ = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane"
BLEND_IN = os.path.join(PROJ, "scene", "L1_step02_checkout_final.blend")
BLEND_OUT = os.path.join(PROJ, "scene", "L1_step02_portrait_axis_test.blend")
REP = os.path.join(PROJ, "reports", "L1_B2_PORTRAIT_AXIS_FEASIBILITY_REPORT.md")
PREVIEW = os.path.join(PROJ, "reviews", "L1_B2_PORTRAIT_AXIS_FEASIBILITY_PREVIEW.png")
UPL = os.path.join(PROJ, "reviews", "UPLOAD_NEXT", "L1_B2_PORTRAIT_AXIS_FEASIBILITY")
os.makedirs(UPL, exist_ok=True)
for f in os.listdir(UPL): os.remove(os.path.join(UPL, f))

# ── Open and snapshot original transforms ──────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=BLEND_IN)
bpy.context.scene.frame_set(20); bpy.context.view_layer.update()
scene = bpy.context.scene

# Snapshot original Root rotations
CHAR_NAMES = ["Customer_01","Customer_02","Customer_03","Customer_04","Employee_01","Employee_02"]
snap_rot = {}
for n in CHAR_NAMES:
    r = bpy.data.objects.get(n + "_Root")
    if r: snap_rot[n] = Vector(r.rotation_euler)

# ── Get cashier roots ─────────────────────────────────────
cl = bpy.data.objects.get("Cashier_Left_Root")
cr = bpy.data.objects.get("Cashier_Right_Root")
if not cl or not cr: print("ERROR: missing cashier roots"); exit()

def get_meshes_under(root):
    return [o for o in root.children_recursive if o.type == 'MESH']

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

# ── Rotate counters Z=90° ─────────────────────────────────
for root in [cl, cr]:
    root.rotation_euler.z = math.radians(90)
bpy.context.view_layer.update()

# Measure counter sizes after rotation
bb_L = get_bbox(get_meshes_under(cl))
bb_R = get_bbox(get_meshes_under(cr))
if bb_L and bb_R:
    print(f"Left counter: ({bb_L[0]:.2f},{bb_L[2]:.2f},{bb_L[4]:.2f})->({bb_L[1]:.2f},{bb_L[3]:.2f},{bb_L[5]:.2f})")
    print(f"  Size: DX={bb_L[1]-bb_L[0]:.2f} DY={bb_L[3]-bb_L[2]:.2f} DZ={bb_L[5]-bb_L[4]:.2f}")
    # Verify: DY > DX * 4
    dy = bb_L[3]-bb_L[2]; dx = bb_L[1]-bb_L[0]
    y_long = dy > dx * 4.0
    print(f"  Y-long axis check: DY/DX={dy/dx:.1f} > 4.0 = {y_long}")
    if not y_long:
        print("ERROR: counter long axis not along Y")

# ── Position counters at center coordinates ────────────────
CX_L, CX_R = -1.20, 1.20
CY = 0.80

for root, cx in [(cl, CX_L), (cr, CX_R)]:
    bb = get_bbox(get_meshes_under(root))
    if bb:
        bcx = (bb[0]+bb[1])/2; bcy = (bb[2]+bb[3])/2
        root.location.x += cx - bcx
        root.location.y += CY - bcy
        # Keep Z grounded (already at 0)

bpy.context.view_layer.update()
bb_L = get_bbox(get_meshes_under(cl))
bb_R = get_bbox(get_meshes_under(cr))
print(f"After positioning:")
print(f"  Left: ({bb_L[0]:.2f},{bb_L[2]:.2f},{bb_L[4]:.2f})->({bb_L[1]:.2f},{bb_L[3]:.2f},{bb_L[5]:.2f})")
print(f"  Right: ({bb_R[0]:.2f},{bb_R[2]:.2f},{bb_R[4]:.2f})->({bb_R[1]:.2f},{bb_R[3]:.2f},{bb_R[5]:.2f})")

# Check counters don't overlap
if bb_L and bb_R:
    ox = max(0, min(bb_L[1],bb_R[1])-max(bb_L[0],bb_R[0]))
    oy = max(0, min(bb_L[3],bb_R[3])-max(bb_L[2],bb_R[2]))
    ctr_overlap = ox > 0.01 and oy > 0.01
    print(f"  Counter overlap: {ctr_overlap}")

# ── Position characters ───────────────────────────────────
# Counters span Y roughly from -0.75 to +2.35.
# Employee side: Y < counter min (negative side)
# Customer side: Y > counter max (positive side)
counter_y_max = max(bb_L[3], bb_R[3]) if bb_L and bb_R else 2.0
counter_y_min = min(bb_L[2], bb_R[2]) if bb_L and bb_R else -0.5

# Employee at counter back (Y < counter_min), Customer at front (Y > counter_max)
emp_y = counter_y_min - 0.5
cust_start_y = counter_y_max + 0.5
cust_gap = 1.40  # spacing between customers

positions = {
    "Employee_01": (CX_L, emp_y),
    "Employee_02": (CX_R, emp_y),
    "Customer_01": (CX_L, cust_start_y),
    "Customer_02": (CX_L, cust_start_y + cust_gap),
    "Customer_03": (CX_L, cust_start_y + cust_gap * 2),
    "Customer_04": (CX_R, cust_start_y),
}

for label, (px, py) in positions.items():
    root = bpy.data.objects.get(label + "_Root")
    if root:
        root.location.x = px
        root.location.y = py
        # Keep Z and rotation from original
        print(f"  {label}: ({px:.2f}, {py:.2f})")

bpy.context.view_layer.update()

# Rotation check
rot_ok = True
for n in CHAR_NAMES:
    r = bpy.data.objects.get(n + "_Root")
    if r:
        orig = snap_rot[n]
        curr = Vector(r.rotation_euler)
        if (orig - curr).length > 0.001:
            print(f"  ROTATION CHANGE: {n}")
            rot_ok = False
print(f"  Rotations preserved: {rot_ok}")

# ── Structural validation ──────────────────────────────────
char_roots = [bpy.data.objects.get(n + "_Root") for n in CHAR_NAMES if bpy.data.objects.get(n + "_Root")]

cc_ov = 0; ctr_ov_char = 0; gf = 0
for i, r1 in enumerate(char_roots):
    m1 = get_meshes_under(r1)
    bb1 = get_bbox(m1)
    if not bb1: continue
    if abs(bb1[4]) > 0.12: gf += 1
    for j, r2 in enumerate(char_roots):
        if j <= i: continue
        m2 = get_meshes_under(r2)
        bb2 = get_bbox(m2)
        if not bb2: continue
        ox = max(0, min(bb1[1],bb2[1])-max(bb1[0],bb2[0]))
        oy = max(0, min(bb1[3],bb2[3])-max(bb1[2],bb2[2]))
        if ox > 0.02 and oy > 0.02: cc_ov += 1
    for ctr_meshes in [get_meshes_under(cl), get_meshes_under(cr)]:
        for co in ctr_meshes:
            bb_c = get_bbox([co])
            if not bb_c: continue
            ox = max(0, min(bb1[1],bb_c[1])-max(bb1[0],bb_c[0]))
            oy = max(0, min(bb1[3],bb_c[3])-max(bb1[2],bb_c[2]))
            if ox > 0.02 and oy > 0.02: ctr_ov_char += 1

# Counter bbox overlap check
ctr_ctr_ov = False
if bb_L and bb_R:
    ox = max(0, min(bb_L[1],bb_R[1])-max(bb_L[0],bb_R[0]))
    oy = max(0, min(bb_L[3],bb_R[3])-max(bb_L[2],bb_R[2]))
    ctr_ctr_ov = ox > 0.01 and oy > 0.01

struct_ok = (len(char_roots)==6 and cc_ov==0 and ctr_ov_char==0 and not ctr_ctr_ov and gf==0 and rot_ok)
print(f"\n  Structure: chars={len(char_roots)}/6 CC={cc_ov} CTR={ctr_ov_char} CTR_CTR={ctr_ctr_ov} GF={gf} ROT={rot_ok} OK={struct_ok}")

if not struct_ok:
    print("STRUCTURE FAILED — stopping")
else:
    # ── Diagnostic camera ──────────────────────────────────
    essential_meshes = []
    for obj_name in [f"{n}_Root" for n in CHAR_NAMES] + ["Cashier_Left_Root","Cashier_Right_Root"]:
        o = bpy.data.objects.get(obj_name)
        if o: essential_meshes.extend(get_meshes_under(o))

    all_pts = []
    for o in essential_meshes:
        dg = bpy.context.evaluated_depsgraph_get(); eo = o.evaluated_get(dg); m = eo.to_mesh()
        if m is None: continue
        for v in m.vertices: all_pts.append(eo.matrix_world @ v.co)
        eo.to_mesh_clear()

    xs = [p.x for p in all_pts]; ys = [p.y for p in all_pts]; zs = [p.z for p in all_pts]
    target = Vector((sum(xs)/len(xs), sum(ys)/len(ys), sum(zs)/len(zs) + 0.10))

    az = math.radians(35); el = math.radians(25)
    cam_dir = Vector((math.sin(az)*math.cos(el), -math.cos(az)*math.cos(el), math.sin(el))).normalized()

    cam_data = bpy.data.cameras.new("DiagCam"); cam_data.type = 'PERSP'
    cam_data.lens = 24; cam_data.sensor_fit = 'HORIZONTAL'
    cam_data.clip_start = 0.05; cam_data.clip_end = 500
    cam = bpy.data.objects.new("DiagCam", cam_data)
    scene.collection.objects.link(cam); scene.camera = cam

    # Binary search for zero-clip distance
    lo, hi = 3.0, 40.0
    for _ in range(15):
        mid = (lo+hi)/2
        cam.location = target + cam_dir * mid
        cam.rotation_euler = (target - cam.location).to_track_quat('-Z','Y').to_euler()
        bpy.context.view_layer.update()
        # Check clipping
        clipped = 0
        for o in essential_meshes:
            dg = bpy.context.evaluated_depsgraph_get(); eo = o.evaluated_get(dg); me = eo.to_mesh()
            if me is None: continue
            obj_clip = False
            for v in me.vertices:
                s = obj_utils.world_to_camera_view(scene, cam, eo.matrix_world @ v.co)
                if s.z < 0 or s.x < 0.05 or s.x > 0.95 or s.y < 0.0 or s.y > 1.0: obj_clip = True; break
            eo.to_mesh_clear()
            if obj_clip: clipped += 1
        if clipped == 0: hi = mid - 0.2
        else: lo = mid + 0.5
        if hi - lo < 0.1: break

    dist = lo  # furthest non-clip distance... wait, we want the CLOSEST zero-clip
    # Actually use hi+0.2 or the last known zero-clip
    dist = hi + 0.5
    cam.location = target + cam_dir * dist
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.view_layer.update()

    # Project all essential vertices
    proj_xs = []; proj_ys = []
    for o in essential_meshes:
        dg = bpy.context.evaluated_depsgraph_get(); eo = o.evaluated_get(dg); me = eo.to_mesh()
        if me is None: continue
        for v in me.vertices:
            s = obj_utils.world_to_camera_view(scene, cam, eo.matrix_world @ v.co)
            if s.z < 0: continue
            proj_xs.append(s.x); proj_ys.append(s.y)
        eo.to_mesh_clear()

    ux_min, ux_max = min(proj_xs), max(proj_xs)
    uy_min, uy_max = min(proj_ys), max(proj_ys)
    content_h = uy_max - uy_min; content_w = ux_max - ux_min
    top_m = 1 - uy_max; bot_m = uy_min
    left_m = ux_min; right_m = 1 - ux_max

    # Clipped object count
    clipped_obj = 0
    for o in essential_meshes:
        dg = bpy.context.evaluated_depsgraph_get(); eo = o.evaluated_get(dg); me = eo.to_mesh()
        if me is None: continue
        ok = True
        for v in me.vertices:
            s = obj_utils.world_to_camera_view(scene, cam, eo.matrix_world @ v.co)
            if s.z < 0 or s.x < 0.05 or s.x > 0.95 or s.y < 0.0 or s.y > 1.0: ok = False; break
        eo.to_mesh_clear()
        if not ok: clipped_obj += 1

    # Channel overlap
    def screen_bbox(obj_names):
        px=[]; py=[]
        for name in obj_names:
            o = bpy.data.objects.get(name)
            if not o: continue
            for m in get_meshes_under(o):
                dg = bpy.context.evaluated_depsgraph_get(); eo = m.evaluated_get(dg); me = eo.to_mesh()
                if me is None: continue
                for v in me.vertices:
                    s = obj_utils.world_to_camera_view(scene, cam, eo.matrix_world @ v.co)
                    if s.z < 0: continue
                    px.append(s.x); py.append(s.y)
                eo.to_mesh_clear()
        if not px: return None
        return (min(px),max(px),min(py),max(py))

    def ov_ratio(bb1, bb2):
        if not bb1 or not bb2: return 1.0
        ox = max(0, min(bb1[1],bb2[1])-max(bb1[0],bb2[0]))
        oy = max(0, min(bb1[3],bb2[3])-max(bb1[2],bb2[2]))
        return ox*oy / max(min((bb1[1]-bb1[0])*(bb1[3]-bb1[2]), (bb2[1]-bb2[0])*(bb2[3]-bb2[2])), 0.0001)

    ctr_L_sb = screen_bbox(["Cashier_Left_Root"])
    ctr_R_sb = screen_bbox(["Cashier_Right_Root"])
    emp_L_sb = screen_bbox(["Employee_01_Root"])
    emp_R_sb = screen_bbox(["Employee_02_Root"])
    lq_sb = screen_bbox(["Customer_01_Root","Customer_02_Root","Customer_03_Root"])
    rq_sb = screen_bbox(["Customer_04_Root"])

    ctr_ov = ov_ratio(ctr_L_sb, ctr_R_sb)
    emp_ov = ov_ratio(emp_L_sb, emp_R_sb)
    q_ov = ov_ratio(lq_sb, rq_sb)
    sep = abs((ctr_R_sb[0]+ctr_R_sb[1])/2 - (ctr_L_sb[0]+ctr_L_sb[1])/2) if ctr_L_sb and ctr_R_sb else 0

    feas = (content_h >= 0.70 and content_h <= 0.86 and content_w <= 0.90 and
            left_m >= 0.05 and right_m >= 0.05 and clipped_obj == 0 and
            ctr_ov <= 0.20 and emp_ov <= 0.15 and q_ov <= 0.20 and sep >= 0.12)

    print(f"\n  Projection: h={content_h:.3f} w={content_w:.3f} top={top_m:.3f} bot={bot_m:.3f} L={left_m:.3f} R={right_m:.3f} clip={clipped_obj}")
    print(f"  Overlap: ctr={ctr_ov:.3f} emp={emp_ov:.3f} q={q_ov:.3f} sep={sep:.3f}")
    print(f"  PORTRAIT_FEASIBLE={feas}")

    # Render
    scene.render.filepath = PREVIEW; bpy.ops.render.render(write_still=True)

# ── Save ───────────────────────────────────────────────────
bpy.ops.wm.save_mainfile(filepath=BLEND_OUT)

# ── Report ─────────────────────────────────────────────────
with open(REP, "w") as f:
    f.write("# L1-B2 Portrait Axis Feasibility Report\n\n")
    f.write("## Counter Layout\n\n")
    f.write(f"- Left Root: {cl.location} rot={cl.rotation_euler}\n")
    f.write(f"- Right Root: {cr.location} rot={cr.rotation_euler}\n")
    if bb_L: f.write(f"- Left bbox: {bb_L}\n")
    if bb_R: f.write(f"- Right bbox: {bb_R}\n")
    f.write("\n## Characters\n\n")
    for n in CHAR_NAMES:
        r = bpy.data.objects.get(n+"_Root")
        if r: f.write(f"- {n}: {r.location} rot={r.rotation_euler}\n")
    f.write(f"\n## Structure\n\n- CC overlap: {cc_ov}\n- CTR overlap: {ctr_ov_char}\n- CTR-CTR overlap: {ctr_ctr_ov}\n- Ground fails: {gf}\n- Rot preserved: {rot_ok}\n- Structure OK: {struct_ok}\n")
    if struct_ok:
        f.write(f"\n## Projection\n\n- Content H: {content_h:.3f} W: {content_w:.3f}\n- Margins: top={top_m:.3f} bot={bot_m:.3f} left={left_m:.3f} right={right_m:.3f}\n- Clipped: {clipped_obj}\n")
        f.write(f"- Ctr ov: {ctr_ov:.3f} Emp ov: {emp_ov:.3f} Q ov: {q_ov:.3f} Sep: {sep:.3f}\n")
        f.write(f"- **portrait_axis_feasible: {feas}**\n")

# ── Upload ─────────────────────────────────────────────────
shutil.copy(REP, os.path.join(UPL, "L1_B2_PORTRAIT_AXIS_FEASIBILITY_REPORT.md"))
if os.path.exists(PREVIEW):
    shutil.copy(PREVIEW, os.path.join(UPL, "L1_B2_PORTRAIT_AXIS_FEASIBILITY_PREVIEW.png"))
print(f"UPLOAD={UPL}")
print("DONE")
