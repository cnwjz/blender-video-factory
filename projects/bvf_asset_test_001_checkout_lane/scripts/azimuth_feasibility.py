"""
CAMERA_AZIMUTH_FEASIBILITY_AUDIT: Test 5 azimuth angles at fixed 25deg elevation, 24mm HORIZONTAL.
"""
import bpy, os, math, shutil
from mathutils import Vector
import bpy_extras.object_utils as obj_utils

PROJ = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane"
BLEND_IN = os.path.join(PROJ, "scene", "L1_step02_checkout_final.blend")
REP = os.path.join(PROJ, "reports", "CAMERA_AZIMUTH_FEASIBILITY_AUDIT_REPORT.md")
PREVIEW = os.path.join(PROJ, "reviews", "CAMERA_AZIMUTH_FEASIBILITY_AUDIT_PREVIEW.png")
UPL = os.path.join(PROJ, "reviews", "UPLOAD_NEXT", "CAMERA_AZIMUTH_FEASIBILITY_AUDIT")
os.makedirs(UPL, exist_ok=True)
for f in os.listdir(UPL): os.remove(os.path.join(UPL, f))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=BLEND_IN)
bpy.context.scene.frame_set(20)
scene = bpy.context.scene
scene.render.resolution_x = 540; scene.render.resolution_y = 960

# ── Essential objects + world vertices ────────────────────
ESSENTIAL_NAMES = ([f"{c}_Root" for c in ["Customer_01","Customer_02","Customer_03","Customer_04","Employee_01","Employee_02"]]
                   + ["Cashier_Left_Root", "Cashier_Right_Root", "Product_L", "Product_R", "Basket"])
essential = [bpy.data.objects.get(n) for n in ESSENTIAL_NAMES if bpy.data.objects.get(n)]

world_verts = []
obj_verts = {}  # per-object vertices for overlap checks
for obj in essential:
    meshes = [o for o in obj.children_recursive if o.type == 'MESH'] if obj.type != 'MESH' else [obj]
    if not meshes: continue
    dg = bpy.context.evaluated_depsgraph_get()
    ov = []
    for m in meshes:
        eo = m.evaluated_get(dg); me = eo.to_mesh()
        if me is None: continue
        for v in me.vertices: ov.append(eo.matrix_world @ v.co)
        eo.to_mesh_clear()
    world_verts.extend(ov)
    obj_verts[obj.name] = ov

xs = [p.x for p in world_verts]; ys = [p.y for p in world_verts]; zs = [p.z for p in world_verts]
target = Vector((sum(xs)/len(xs), sum(ys)/len(ys), sum(zs)/len(zs) + 0.10))
print(f"Target: {target}")

# ── Camera helpers ────────────────────────────────────────
LENS = 24; SENSOR_FIT = 'HORIZONTAL'
AZIMUTHS = [35, 45, 55, 65, 75]

def make_direction(azimuth_deg):
    """Unit direction: x>0, y<0, z>0. Elevation 25deg, azimuth from -Y toward +X."""
    az = math.radians(azimuth_deg)
    el = math.radians(25)
    return Vector((math.sin(az) * math.cos(el),
                   -math.cos(az) * math.cos(el),
                   math.sin(el))).normalized()

def project_all(cam_obj):
    xs = []; ys = []; c = 0
    for v in world_verts:
        s = obj_utils.world_to_camera_view(scene, cam_obj, v)
        if s.z < 0: c += 1; continue
        xs.append(s.x); ys.append(s.y)
    if not xs: return (0,1,0,1,c)
    return (min(xs),max(xs),min(ys),max(ys),c)

def screen_bbox_for(obj_names):
    """Get 2D screen bbox for named essential objects using scene camera."""
    cam = scene.camera
    if not cam: return None
    xs = []; ys = []
    for name in obj_names:
        ov = obj_verts.get(name, [])
        if not ov: continue
        for v in ov:
            s = obj_utils.world_to_camera_view(scene, cam, v)
            if s.z < 0: continue
            xs.append(s.x); ys.append(s.y)
    if not xs: return None
    return (min(xs), max(xs), min(ys), max(ys))

def find_distance(cam_dir):
    """Binary search for min distance with 0 clipped and L/R >= 5%."""
    cam_data = bpy.data.cameras.new("T"); cam_data.type = 'PERSP'
    cam_data.lens = LENS; cam_data.sensor_fit = SENSOR_FIT
    cam_data.clip_start = 0.05; cam_data.clip_end = 500
    cam_obj = bpy.data.objects.new("T", cam_data)
    scene.collection.objects.link(cam_obj)
    # Set as scene camera so screen_bbox_for can use it via scene.camera
    scene.camera = cam_obj

    lo, hi = 2.0, 50.0; best = None
    for _ in range(15):
        mid = (lo + hi) / 2
        cam_obj.location = target + cam_dir * mid
        cam_obj.rotation_euler = (target - cam_obj.location).to_track_quat('-Z', 'Y').to_euler()
        bpy.context.view_layer.update()
        ux_min, ux_max, uy_min, uy_max, _ = project_all(cam_obj)

        # Count clipped objects (any vertex outside safe bounds)
        clipped = 0
        for name in obj_verts:
            bb = screen_bbox_for([name])
            if bb is None: clipped += 1; continue
            if bb[0] < 0.05 or bb[1] > 0.95: clipped += 1
        left_m = ux_min; right_m = 1 - ux_max
        ok = (clipped == 0 and left_m >= 0.05 and right_m >= 0.05)
        if ok:
            best = (mid, uy_max-uy_min, ux_max-ux_min, left_m, right_m, 1-uy_max, uy_min, clipped, cam_obj)
            hi = mid - 0.15
        else:
            lo = mid + 0.3
        if hi - lo < 0.05: break

    if best is None:
        # Return the farthest tested
        cam_obj.location = target + cam_dir * lo
        cam_obj.rotation_euler = (target - cam_obj.location).to_track_quat('-Z', 'Y').to_euler()
        bpy.context.view_layer.update()
        ux_min, ux_max, uy_min, uy_max, _ = project_all(cam_obj)
        clipped = sum(1 for name in obj_verts if (bb := screen_bbox_for([name])) is None or bb[0] < 0.05 or bb[1] > 0.95)
        best = (lo, uy_max-uy_min, ux_max-ux_min, ux_min, 1-ux_max, 1-uy_max, uy_min, clipped, cam_obj)

    return best

results = []
best_overall = None

for az in AZIMUTHS:
    cam_dir = make_direction(az)
    print(f"\n  Azimuth {az}deg: dir=({cam_dir.x:.3f},{cam_dir.y:.3f},{cam_dir.z:.3f})")
    d, ch, cw, lm, rm, top, bot, clipped, cam_obj = find_distance(cam_dir)

    # Channel readability (scene.camera already set by find_distance)
    counter_L_bb = screen_bbox_for(["Cashier_Left_Root"])
    counter_R_bb = screen_bbox_for(["Cashier_Right_Root"])
    emp_L_bb = screen_bbox_for(["Employee_01_Root"])
    emp_R_bb = screen_bbox_for(["Employee_02_Root"])
    left_q_bb = screen_bbox_for([f"Customer_{i:02d}_Root" for i in range(1,4)])
    right_q_bb = screen_bbox_for(["Customer_04_Root"])

    def overlap_ratio(bb1, bb2):
        if not bb1 or not bb2: return 1.0
        ox = max(0, min(bb1[1],bb2[1]) - max(bb1[0],bb2[0]))
        oy = max(0, min(bb1[3],bb2[3]) - max(bb1[2],bb2[2]))
        area_overlap = ox * oy
        area1 = (bb1[1]-bb1[0]) * (bb1[3]-bb1[2])
        area2 = (bb2[1]-bb2[0]) * (bb2[3]-bb2[2])
        return area_overlap / max(min(area1, area2), 0.0001)

    ctr_ov = overlap_ratio(counter_L_bb, counter_R_bb)
    emp_ov = overlap_ratio(emp_L_bb, emp_R_bb)
    q_ov = overlap_ratio(left_q_bb, right_q_bb)

    # Counter center separation
    sep = 0
    if counter_L_bb and counter_R_bb:
        cl_cx = (counter_L_bb[0]+counter_L_bb[1])/2
        cr_cx = (counter_R_bb[0]+counter_R_bb[1])/2
        sep = abs(cr_cx - cl_cx)

    feas = (ch >= 0.70 and ch <= 0.82 and cw <= 0.90 and lm >= 0.05 and rm >= 0.05 and
            clipped == 0 and ctr_ov <= 0.20 and emp_ov <= 0.15 and q_ov <= 0.20 and sep >= 0.12)

    r = {"azimuth": az, "distance": round(d,1), "content_h": ch, "content_w": cw,
         "left": lm, "right": rm, "top": top, "bot": bot, "clipped": clipped,
         "ctr_ov": ctr_ov, "emp_ov": emp_ov, "q_ov": q_ov, "sep": sep, "feasible": feas}
    results.append(r)

    print(f"    d={d:.1f}m h={ch:.3f} w={cw:.3f} L={lm:.3f} R={rm:.3f} clip={clipped}")
    print(f"    ctr_ov={ctr_ov:.3f} emp_ov={emp_ov:.3f} q_ov={q_ov:.3f} sep={sep:.3f} FEAS={feas}")

    if not best_overall or (feas and (not best_overall.get('feasible') or ch > best_overall['content_h'])):
        best_overall = dict(r)
        best_overall['cam_dir'] = cam_dir

feasible_any = any(r['feasible'] for r in results)
print(f"\n  Any feasible: {feasible_any}")

# ── Render best ────────────────────────────────────────────
if best_overall and 'cam_dir' in best_overall:
    cam_data = bpy.data.cameras.new("BestCam"); cam_data.type = 'PERSP'
    cam_data.lens = LENS; cam_data.sensor_fit = SENSOR_FIT
    cam_data.clip_start = 0.05; cam_data.clip_end = 500
    cam_obj = bpy.data.objects.new("BestCam", cam_data)
    scene.collection.objects.link(cam_obj); scene.camera = cam_obj
    az_dir = best_overall['cam_dir']
    cam_obj.location = target + az_dir * best_overall['distance']
    cam_obj.rotation_euler = (target - cam_obj.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = PREVIEW; bpy.ops.render.render(write_still=True)
    print(f"Preview: {PREVIEW}")

# ── Determine limitation ───────────────────────────────────
if feasible_any:
    limitation = "none"
else:
    # Find the config with highest content_h
    best_by_h = max(results, key=lambda r: r['content_h'])
    if best_by_h['content_h'] < 0.70: limitation = "height_target_unreachable"
    elif max(r['ctr_ov'] for r in results) < 0.20 and max(r['q_ov'] for r in results) > 0.20: limitation = "queues_overlap"
    elif max(r['ctr_ov'] for r in results) > 0.20: limitation = "checkout_channels_overlap"
    else: limitation = "projection_metric_error"

# ── Report ─────────────────────────────────────────────────
with open(REP, "w") as f:
    f.write("# Camera Azimuth Feasibility Audit\n\n")
    f.write(f"## Fixed Parameters\n\n- Lens: {LENS}mm, sensor_fit={SENSOR_FIT}\n")
    f.write(f"- Elevation: 25deg\n- Resolution: 540x960\n- Target: {target}\n\n")
    f.write("## Results\n\n")
    f.write("| Azimuth | Dist(m) | Content H | Content W | Left | Right | Clip | Ctr OV | Emp OV | Q OV | Sep | Feasible |\n")
    f.write("|---------|---------|-----------|-----------|------|-------|------|--------|--------|------|-----|----------|\n")
    for r in results:
        f.write(f"| {r['azimuth']}deg | {r['distance']:.1f} | {r['content_h']:.3f} | {r['content_w']:.3f} | {r['left']:.3f} | {r['right']:.3f} | {r['clipped']} | {r['ctr_ov']:.3f} | {r['emp_ov']:.3f} | {r['q_ov']:.3f} | {r['sep']:.3f} | **{r['feasible']}** |\n")
    f.write(f"\n## Conclusion\n\n- azimuth_framing_feasible: **{feasible_any}**\n")
    f.write(f"- Primary limitation: **{limitation}**\n")

# ── Upload ─────────────────────────────────────────────────
shutil.copy(REP, os.path.join(UPL, "CAMERA_AZIMUTH_FEASIBILITY_AUDIT_REPORT.md"))
if os.path.exists(PREVIEW):
    shutil.copy(PREVIEW, os.path.join(UPL, "CAMERA_AZIMUTH_FEASIBILITY_AUDIT_PREVIEW.png"))
print(f"UPLOAD={UPL}")
print("AUDIT DONE")
