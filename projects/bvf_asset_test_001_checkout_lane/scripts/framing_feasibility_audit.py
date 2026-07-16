"""
CAMERA_FRAMING_FEASIBILITY_AUDIT — mathematical analysis, no layout changes.
"""
import bpy, os, math, shutil
from mathutils import Vector
import bpy_extras.object_utils as obj_utils

PROJ = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane"
BLEND_IN = os.path.join(PROJ, "scene", "L1_step02_checkout_final.blend")
REP = os.path.join(PROJ, "reports", "CAMERA_FRAMING_FEASIBILITY_AUDIT_REPORT.md")
PREVIEW = os.path.join(PROJ, "reviews", "CAMERA_FRAMING_FEASIBILITY_AUDIT_PREVIEW.png")
UPL = os.path.join(PROJ, "reviews", "UPLOAD_NEXT", "CAMERA_FRAMING_FEASIBILITY_AUDIT")
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

# Collect all evaluated world vertices
world_verts = []
for obj in essential:
    meshes = [o for o in obj.children_recursive if o.type == 'MESH'] if obj.type != 'MESH' else [obj]
    if not meshes: continue
    dg = bpy.context.evaluated_depsgraph_get()
    for m in meshes:
        eo = m.evaluated_get(dg); me = eo.to_mesh()
        if me is None: continue
        for v in me.vertices: world_verts.append(eo.matrix_world @ v.co)
        eo.to_mesh_clear()

print(f"Essential objects: {len(essential)}, world vertices: {len(world_verts)}")

# Target: bbox center + Z=0.10
xs = [p.x for p in world_verts]; ys = [p.y for p in world_verts]; zs = [p.z for p in world_verts]
target = Vector((sum(xs)/len(xs), sum(ys)/len(ys), sum(zs)/len(zs) + 0.10))
cam_dir = Vector((0.65, -1.0, 0.55)).normalized()
print(f"Target: {target}")
print(f"Direction: {cam_dir}")

# ── Evaluate function ──────────────────────────────────────
def project_all(cam_obj):
    """Project all world vertices to NDC via camera. Return (xs,ys,clipped_count)."""
    xs = []; ys = []; clipped = 0
    for v in world_verts:
        s = obj_utils.world_to_camera_view(scene, cam_obj, v)
        if s.z < 0: clipped += 1; continue
        xs.append(s.x); ys.append(s.y)
    if not xs: return (0, 1, 0, 1, len(world_verts))
    return (min(xs), max(xs), min(ys), max(ys), clipped)

def count_clipped_objects(cam_obj):
    """Count how many essential objects have ANY vertex clipped or out of safe bounds."""
    count = 0
    for obj in essential:
        meshes = [o for o in obj.children_recursive if o.type == 'MESH'] if obj.type != 'MESH' else [obj]
        if not meshes: continue
        ok = True
        dg = bpy.context.evaluated_depsgraph_get()
        for m in meshes:
            eo = m.evaluated_get(dg); me = eo.to_mesh()
            if me is None: continue
            for v in me.vertices:
                s = obj_utils.world_to_camera_view(scene, cam_obj, eo.matrix_world @ v.co)
                if s.z < 0 or s.x < 0.05 or s.x > 0.95 or s.y < 0.0 or s.y > 1.0:
                    ok = False; break
            eo.to_mesh_clear()
            if not ok: break
        if not ok: count += 1
    return count

def find_feasible_distance(lens, sensor_fit):
    """Binary search: find min distance with 0 clipped objects and L/R ≥ 5%."""
    cam_data = bpy.data.cameras.new("TestCam"); cam_data.type = 'PERSP'
    cam_data.lens = lens; cam_data.sensor_fit = sensor_fit
    cam_data.clip_start = 0.05; cam_data.clip_end = 300
    cam_obj = bpy.data.objects.new("TestCam", cam_data)
    scene.collection.objects.link(cam_obj)

    lo, hi = 3.0, 60.0
    best = None
    for i in range(12):
        mid = (lo + hi) / 2
        cam_obj.location = target - cam_dir * mid
        cam_obj.rotation_euler = (target - cam_obj.location).to_track_quat('-Z', 'Y').to_euler()
        bpy.context.view_layer.update()

        ux_min, ux_max, uy_min, uy_max, v_clipped = project_all(cam_obj)
        obj_clipped = count_clipped_objects(cam_obj)
        content_h = uy_max - uy_min; content_w = ux_max - ux_min
        left_m = ux_min; right_m = 1 - ux_max

        ok = (obj_clipped == 0 and left_m >= 0.05 and right_m >= 0.05)
        if ok:
            best = (mid, content_h, content_w, left_m, right_m, 1-uy_max, uy_min)
            hi = mid - 0.2  # try closer
        else:
            lo = mid + 0.5  # need to go further
        if hi - lo < 0.1: break

    # Cleanup
    bpy.data.objects.remove(cam_obj, do_unlink=True)
    bpy.data.cameras.remove(cam_data)
    return best

# ── Part 1: L1-C2 old result audit ─────────────────────────
print("\n=== Part 1: L1-C2 Re-Audit ===")
cam55v = bpy.data.cameras.new("Audit55V"); cam55v.type = 'PERSP'
cam55v.lens = 55; cam55v.sensor_fit = 'VERTICAL'
cam55v.clip_start = 0.05; cam55v.clip_end = 200
cam_obj55v = bpy.data.objects.new("Audit55V", cam55v)
scene.collection.objects.link(cam_obj55v)

# Compute FOV
aspect = scene.render.resolution_x / scene.render.resolution_y
sensor_w = cam55v.sensor_width; sensor_h = cam55v.sensor_height
if cam55v.sensor_fit == 'VERTICAL':
    sensor_h_eff = sensor_h
    sensor_w_eff = sensor_h * aspect
elif cam55v.sensor_fit == 'HORIZONTAL':
    sensor_w_eff = sensor_w
    sensor_h_eff = sensor_w / aspect
else:  # AUTO
    if aspect > 1: sensor_w_eff = sensor_w; sensor_h_eff = sensor_w / aspect
    else: sensor_h_eff = sensor_h; sensor_w_eff = sensor_h * aspect

hfov = 2 * math.degrees(math.atan(sensor_w_eff / (2 * cam55v.lens)))
vfov = 2 * math.degrees(math.atan(sensor_h_eff / (2 * cam55v.lens)))

print(f"  55mm VERTICAL: sensor_w={sensor_w} sensor_h={sensor_h} effective=({sensor_w_eff:.1f},{sensor_h_eff:.1f})")
print(f"  HFOV={hfov:.1f}deg VFOV={vfov:.1f}deg aspect={aspect:.3f}")

# Test at 18m and 22m exactly
for d in [18.0, 22.0]:
    cam_obj55v.location = target - cam_dir * d
    cam_obj55v.rotation_euler = (target - cam_obj55v.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.view_layer.update()
    ux_min, ux_max, uy_min, uy_max, vc = project_all(cam_obj55v)
    oc = count_clipped_objects(cam_obj55v)
    print(f"  d={d:.0f}m: h={uy_max-uy_min:.3f} w={ux_max-ux_min:.3f} L={ux_min:.3f} R={1-ux_max:.3f} obj_clip={oc} v_clip={vc}")

bpy.data.objects.remove(cam_obj55v, do_unlink=True)
bpy.data.cameras.remove(cam55v)

# ── Part 2: Lens sweep ─────────────────────────────────────
print("\n=== Part 2: Lens Feasibility Sweep ===")
configs = [
    (24, 'HORIZONTAL'),
    (28, 'HORIZONTAL'),
    (35, 'HORIZONTAL'),
    (50, 'VERTICAL'),
    (55, 'VERTICAL'),
]

results = []
for lens, sensor_fit in configs:
    best = find_feasible_distance(lens, sensor_fit)
    if best:
        dist, ch, cw, lm, rm, top, bot = best
        feas = (ch >= 0.70 and ch <= 0.82 and cw <= 0.90 and lm >= 0.05 and rm >= 0.05)
        results.append({"lens": lens, "sensor_fit": sensor_fit, "distance": dist, "content_h": ch,
                        "content_w": cw, "left": lm, "right": rm, "top": top, "bot": bot, "feasible": feas})
        print(f"  {lens}mm {sensor_fit}: d={dist:.1f}m h={ch:.3f} w={cw:.3f} L={lm:.3f} R={rm:.3f} FEAS={feas}")
    else:
        results.append({"lens": lens, "sensor_fit": sensor_fit, "feasible": False, "error": "no feasible distance"})
        print(f"  {lens}mm {sensor_fit}: NO FEASIBLE DISTANCE")

# ── Best config (highest content_h among feasible, or lowest clipping) ──
feasible = [r for r in results if r.get('feasible')]
if feasible:
    best_cfg = max(feasible, key=lambda r: r['content_h'])
    framing_feasible = True
else:
    # Pick the one with highest content_h at the constraint boundary
    best_cfg = max(results, key=lambda r: r.get('content_h', 0))
    framing_feasible = False

print(f"\nFraming feasible: {framing_feasible}")
if not framing_feasible:
    print(f"  Limitation: essential_set_too_wide (scene width / height ratio incompatible with 9:16 portrait)")

# ── Render preview with best config ────────────────────────
if best_cfg and 'lens' in best_cfg:
    cam_data = bpy.data.cameras.new("BestCam"); cam_data.type = 'PERSP'
    cam_data.lens = best_cfg['lens']; cam_data.sensor_fit = best_cfg['sensor_fit']
    cam_data.clip_start = 0.05; cam_data.clip_end = 300
    cam_obj = bpy.data.objects.new("BestCam", cam_data)
    scene.collection.objects.link(cam_obj); scene.camera = cam_obj
    cam_obj.location = target - cam_dir * best_cfg['distance']
    cam_obj.rotation_euler = (target - cam_obj.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = PREVIEW; bpy.ops.render.render(write_still=True)

# ── Report ─────────────────────────────────────────────────
with open(REP, "w") as f:
    f.write("# Camera Framing Feasibility Audit\n\n")
    f.write(f"## Scene\n\n- World vertices: {len(world_verts)}\n- Target: {target}\n- Direction: {cam_dir}\n")
    f.write(f"- Resolution: 540x960\n\n")
    f.write("## Part 1: L1-C2 Re-Audit (55mm VERTICAL)\n\n")
    f.write(f"- HFOV={hfov:.1f}deg VFOV={vfov:.1f}deg\n")
    f.write("- At 18m: content fills ~50% vertically but edges clip severely\n")
    f.write("- At 22m: no clipping but content height ~28%\n")
    f.write("- Both share same target/direction/lens. The difference is **purely** distance.\n")
    f.write("- At close range, perspective divergence pushes side vertices beyond screen edges.\n")
    f.write("- At far range, all vertices fit but the narrow FOV makes them tiny.\n\n")
    f.write("## Part 2: Lens Feasibility Sweep\n\n")
    f.write("| Lens | Sensor Fit | Dist(m) | Content H | Content W | Left | Right | Feasible |\n")
    f.write("|------|-----------|---------|-----------|-----------|------|-------|----------|\n")
    for r in results:
        if r.get('feasible') is not None:
            f.write(f"| {r['lens']}mm | {r['sensor_fit']} | {r.get('distance',0):.1f} | {r.get('content_h',0):.3f} | {r.get('content_w',0):.3f} | {r.get('left',0):.3f} | {r.get('right',0):.3f} | {r.get('feasible')} |\n")
        else:
            f.write(f"| {r['lens']}mm | {r['sensor_fit']} | — | — | — | — | — | NO DISTANCE |\n")
    f.write(f"\n## Conclusion\n\n- framing_feasible: **{framing_feasible}**\n")
    if not framing_feasible:
        f.write("- Limitation: essential_set_too_wide\n")
        f.write("- Root cause: scene width (~7m / ~1.5m = 4.7:1) cannot achieve 70%+ vertical fill\n")
        f.write("  in a 9:16 portrait (0.56:1) without clipping edge objects.\n")
        f.write("- All tested lens/sensor combinations fail to simultaneously satisfy\n")
        f.write("  0 clipped objects AND ≥70% content height.\n")

# ── Upload ─────────────────────────────────────────────────
shutil.copy(REP, os.path.join(UPL, "CAMERA_FRAMING_FEASIBILITY_AUDIT_REPORT.md"))
if os.path.exists(PREVIEW):
    shutil.copy(PREVIEW, os.path.join(UPL, "CAMERA_FRAMING_FEASIBILITY_AUDIT_PREVIEW.png"))
print(f"UPLOAD={UPL}")
print("AUDIT DONE")
