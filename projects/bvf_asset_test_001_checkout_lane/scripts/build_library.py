"""
CNG_v1: Character Normalization Gate.
Standardize 5 characters → character_library_v1.blend → validation board.
"""
import bpy, os, json, math
from mathutils import Vector, Euler, Matrix
import bpy_extras.object_utils as obj_utils

PROJ = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane"
CH_FBX = os.path.join(PROJ, "assets", "imported", "kenney_mini-characters", "Models", "FBX format")
MK_FBX = os.path.join(PROJ, "assets", "imported", "kenney_mini-market", "Models", "FBX format")
UPL = os.path.join(PROJ, "reviews", "UPLOAD_NEXT")
TMP = os.path.join(PROJ, "reviews", "_libtmp")
os.makedirs(UPL, exist_ok=True); os.makedirs(TMP, exist_ok=True)
for f in os.listdir(UPL): os.remove(os.path.join(UPL, f))

TARGET_H = 1.75
REPORT = []

def log(s): print(s); REPORT.append(s)

CHAR_SPECS = [
    ("CHR_MALE_A", "character-male-a.fbx", False),
    ("CHR_FEMALE_A", "character-female-a.fbx", False),
    ("CHR_MALE_B", "character-male-b.fbx", False),
    ("CHR_FEMALE_B", "character-female-b.fbx", False),
    ("CHR_EMPLOYEE", "character-employee.fbx", True),
]

def fresh_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene; s.render.engine = 'BLENDER_EEVEE'
    s.render.resolution_x = 1080; s.render.resolution_y = 1080
    s.eevee.use_shadows = True; return s

def get_world_bbox(mesh_objects):
    dg = bpy.context.evaluated_depsgraph_get(); pts=[]
    for o in mesh_objects:
        if o.type != 'MESH': continue
        eo=o.evaluated_get(dg); m=eo.to_mesh()
        if m is None: continue
        for v in m.vertices: pts.append(eo.matrix_world @ v.co)
        eo.to_mesh_clear()
    if not pts: return None
    xs=[p.x for p in pts]; ys=[p.y for p in pts]; zs=[p.z for p in pts]
    return (min(xs),max(xs),min(ys),max(ys),min(zs),max(zs))

def normalize_char(root, armature, body, head):
    """Normalize scale → 1.75h, align feet to Z=0, face +Y."""
    meshes = [o for o in [body, head] if o]
    # Reset scale
    root.scale = Vector((1,1,1))
    bpy.context.view_layer.update()
    bb = get_world_bbox(meshes)
    if bb is None: return
    h = bb[5]-bb[4]
    if h < 0.001: return
    sf = TARGET_H / h
    root.scale = Vector((sf, sf, sf))
    bpy.context.view_layer.update()
    bb2 = get_world_bbox(meshes)
    if bb2 is None: return
    # Feet to ground
    root.location.z -= bb2[4]
    root.location.x = 0; root.location.y = 0
    # Upright standing + face +Y.
    # Kenney FBX imports lying down (X/Y dominant, Z minimal).
    # Need X-axis 90° rotation to make character stand upright.
    # Then Z=π to face +Y direction.
    root.rotation_euler = Euler((math.pi/2, 0, math.pi), 'XYZ')
    return sf

def validate(label, root, armature, body, head, pose_name, pose_frame):
    """Run all validation checks. Return (pass, issues)."""
    issues = []
    ok = True
    if not root: ok=False; issues.append("Root missing"); return ok, issues
    if not armature: ok=False; issues.append("Armature missing")
    if not body: ok=False; issues.append("Body missing")
    if not head: ok=False; issues.append("Head missing")
    if not ok: return ok, issues

    meshes = [o for o in [body, head] if o]
    bb = get_world_bbox(meshes)
    if bb is None: ok=False; issues.append("BBox invalid"); return ok, issues

    mx,MX,my,MY,mz,MZ = bb
    h = MZ-mz; w = MX-mx; d = MY-my
    if h < 0.5: ok=False; issues.append(f"Height={h:.2f} < 0.5")
    if w < 0.1: ok=False; issues.append(f"Width={w:.2f} < 0.1")
    if mz > 0.05: ok=False; issues.append(f"Lowest Z={mz:.3f} > 0.05 — feet not on ground")

    # Ratio check: humanoid should be taller than wide
    ratio = h / max(w, d, 0.001)
    if ratio < 0.85: ok=False; issues.append(f"H:W ratio={ratio:.2f} < 0.85 — possibly lying down")

    if ratio > 0.9 and ratio < 1.5: issues.append(f"H:W ratio={ratio:.1f} — wide but may be arms-out pose (non-blocking)")

    # Head above body center
    bb_body = get_world_bbox([body]) if body else None
    bb_head = get_world_bbox([head]) if head else None
    if bb_body and bb_head:
        body_cz = (bb_body[4]+bb_body[5])/2
        head_cz = (bb_head[4]+bb_head[5])/2
        if head_cz <= body_cz: ok=False; issues.append(f"Head Z={head_cz:.2f} <= Body Z={body_cz:.2f}")

    # Uprightness: bbox height should be the dominant dimension and Z-aligned
    # Check if bbox height > width and depth
    if h < w * 0.8: ok=False; issues.append(f"Height({h:.2f}) < Width({w:.2f}) — likely horizontal")

    # Floating parts: bbox should be contiguous (no gap > 0.3 between body and head)
    if bb_body and bb_head:
        gap = bb_head[4] - bb_body[5]  # head min Z - body max Z
        if abs(gap) > 0.4: ok=False; issues.append(f"Head-body gap={gap:.3f} > 0.4")

    # Hide render check
    for o in [body, head]:
        if o and o.hide_render: ok=False; issues.append(f"{o.name} hide_render=True")

    # Collection visibility
    for col in root.users_collection:
        if col.hide_render: ok=False; issues.append(f"Collection {col.name} hidden")

    return ok, issues

# ═══════════════════════════════════════════════════════════
# BUILD CHARACTER LIBRARY
# ═══════════════════════════════════════════════════════════
scene = fresh_scene()
scene.render.resolution_x = 5400  # Wide board: 5 chars × 1080
scene.render.resolution_y = 1080

# Basic lighting
world = bpy.data.worlds.new("LibW"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.50, 0.48, 0.44, 1.0)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
bpy.ops.object.light_add(type='SUN', location=(3, -5, 6))
bpy.context.object.data.energy = 3.0; bpy.context.object.data.angle = 0.15
bpy.ops.object.light_add(type='AREA', location=(-2, 0, 3))
bpy.context.object.data.energy = 2.0; bpy.context.object.data.size = 5

all_chars = []
for idx, (col_name, fname, is_emp) in enumerate(CHAR_SPECS):
    log(f"\n{'='*50}\n{col_name}\n{'='*50}")
    path = os.path.join(MK_FBX if is_emp else CH_FBX, fname)

    # Import
    prev = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in prev]

    # Clean stray
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and o.name.lower().startswith('icosphere') and o.parent is None:
            bpy.data.objects.remove(o, do_unlink=True)

    # Find objects
    empty = [o for o in new if o.type == 'EMPTY']
    arm = [o for o in new if o.type == 'ARMATURE']
    meshes = [o for o in new if o.type == 'MESH']
    root = empty[-1] if empty else None
    arm_obj = arm[-1] if arm else None
    body = None; head = None
    for m in meshes:
        if 'body' in m.name.lower(): body = m
        elif 'head' in m.name.lower(): head = m
    if not body and meshes: body = meshes[0]
    if not head and len(meshes) > 1: head = meshes[1]

    # Rename
    if root: root.name = f"{col_name}_Root"
    if arm_obj: arm_obj.name = f"{col_name}_Armature"
    if body: body.name = f"{col_name}_Body"
    if head: head.name = f"{col_name}_Head"

    # Create collection
    col = bpy.data.collections.new(col_name)
    scene.collection.children.link(col)
    for name in ["_Root", "_Armature", "_Body", "_Head"]:
        o = bpy.data.objects.get(f"{col_name}{name}")
        if o:
            for c in list(o.users_collection): c.objects.unlink(o)
            col.objects.link(o)
            o.hide_viewport = False; o.hide_render = False

    # Re-fetch
    root = bpy.data.objects.get(f"{col_name}_Root")
    arm_obj = bpy.data.objects.get(f"{col_name}_Armature")
    body = bpy.data.objects.get(f"{col_name}_Body")
    head = bpy.data.objects.get(f"{col_name}_Head")

    # Try rest pose first
    if arm_obj:
        if arm_obj.animation_data: arm_obj.animation_data.action = None
    scene.frame_set(1)
    bpy.context.view_layer.update()

    # Check if rest pose is T-pose or lying down
    meshes_chk = [o for o in [body, head] if o]
    bb_rest = get_world_bbox(meshes_chk)
    rest_ratio = 0
    if bb_rest:
        h_r = bb_rest[5]-bb_rest[4]; w_r = bb_rest[1]-bb_rest[0]
        rest_ratio = h_r/max(w_r, 0.001)
        log(f"  Rest pose: h={h_r:.2f} w={w_r:.2f} ratio={rest_ratio:.1f}")

    # Determine best pose
    pose_source = "rest"
    pose_frame = 1

    if rest_ratio < 0.8:  # Rest pose is too wide = probably T-pose or lying
        log(f"  Rest pose unsuitable (ratio={rest_ratio:.1f}), trying actions...")

        # Try static action
        if arm_obj:
            if not arm_obj.animation_data: arm_obj.animation_data_create()
            act = bpy.data.actions.get("root|static|Animation Base Layer")
            if act:
                arm_obj.animation_data.action = act
                scene.frame_set(3)
                bpy.context.view_layer.update()
                bb_static = get_world_bbox(meshes_chk)
                if bb_static:
                    hs = bb_static[5]-bb_static[4]; ws = bb_static[1]-bb_static[0]
                    rs = hs/max(ws, 0.001)
                    log(f"  static action f3: h={hs:.2f} w={ws:.2f} ratio={rs:.1f}")
                    if rs > 0.9:
                        pose_source = "root|static|Animation Base Layer"
                        pose_frame = 3
                        log(f"  Using static action")

        # If static didn't work, try idle
        if pose_source == "rest":
            if arm_obj:
                act_idle = bpy.data.actions.get("root|idle|Animation Base Layer")
                if act_idle:
                    arm_obj.animation_data.action = act_idle
                    for ftry in [1, 10, 20, 30, 40, 50, 60, 70, 80]:
                        scene.frame_set(ftry)
                        bpy.context.view_layer.update()
                        bb_i = get_world_bbox(meshes_chk)
                        if bb_i:
                            hi = bb_i[5]-bb_i[4]; wi = bb_i[1]-bb_i[0]
                            ri = hi/max(wi, 0.001)
                            if ri > 1.0:
                                pose_source = "root|idle|Animation Base Layer"
                                pose_frame = ftry
                                log(f"  idle action f{ftry}: h={hi:.2f} ratio={ri:.1f} — OK")
                                break
                            else:
                                log(f"  idle f{ftry}: ratio={ri:.1f} — skip")

    scene.frame_set(pose_frame)
    bpy.context.view_layer.update()

    # Normalize scale and position
    sf = normalize_char(root, arm_obj, body, head)
    if sf: log(f"  Scale: {sf:.4f}")

    # Validate
    passed, issues = validate(col_name, root, arm_obj, body, head, pose_source, pose_frame)
    log(f"  POSE: {pose_source} frame {pose_frame}")
    log(f"  VALIDATION: {'PASSED' if passed else 'FAILED'}")
    for i in issues: log(f"    {i}")

    all_chars.append({
        "col_name": col_name, "root": root, "armature": arm_obj,
        "body": body, "head": head, "pose_source": pose_source,
        "pose_frame": pose_frame, "passed": passed, "issues": issues
    })

# ── Arrange in library (spaced along X) ────────────────────
spacing = 2.5
for i, cd in enumerate(all_chars):
    if cd["root"]:
        cd["root"].location.x = (i - 2) * spacing
        cd["root"].location.y = 0
        cd["root"].location.z = cd["root"].location.z  # keep feet at Z=0

# ── Camera: front ortho for all 5 ──────────────────────────
# Camera looking from front (+Y direction)
cam_data = bpy.data.cameras.new("LibCam"); cam_data.type = 'ORTHO'
cam_data.ortho_scale = 7.5; cam_data.clip_start = 0.05; cam_data.clip_end = 100
cam = bpy.data.objects.new("LibCam", cam_data)
scene.collection.objects.link(cam); scene.camera = cam
cam.location = (0, -6, 0.9)
cam.rotation_euler = (0, 0, 0)

# ── Render 3 views: front, side, 3/4 ──────────────────────
views = {"front": (0, -8, 0.9, 0, 0, 0, 7.5),
         "side":  (8, 0, 0.9, math.radians(90), 0, math.radians(90), 7.5),
         "three_q": (4, -6, 3.5, 0, 0, 0, 8.5)}

for vname, (lx, ly, lz, rx, ry, rz, oscale) in views.items():
    cam.location = (lx, ly, lz); cam.rotation_euler = (rx, ry, rz)
    cam_data.ortho_scale = oscale
    out = os.path.join(TMP, f"lib_{vname}.png")
    scene.render.filepath = out
    bpy.ops.render.render(write_still=True)
    log(f"  Rendered: {vname} → {out}")

# ── Save library ───────────────────────────────────────────
lib_path = os.path.join(PROJ, "scene", "character_library_v1.blend")
bpy.ops.wm.save_mainfile(filepath=lib_path)
log(f"Library saved: {lib_path}")

# ── Composite validation board (system Python) ─────────────
log_path = os.path.join(TMP, "report.json")
with open(log_path, "w") as f:
    json.dump([{
        "col_name": cd["col_name"], "pose_source": cd["pose_source"],
        "pose_frame": cd["pose_frame"], "passed": cd["passed"],
        "issues": cd["issues"],
        "root_scale": [round(v,4) for v in cd["root"].scale] if cd["root"] else []
    } for cd in all_chars], f, indent=2)

# Report
rep_path = os.path.join(PROJ, "reports", "CHARACTER_NORMALIZATION_REPORT_v1.md")
with open(rep_path, "w") as rf:
    rf.write("# Character Normalization Report v1\n\nDate: 2026-07-14\n\n")
    for cd in all_chars:
        rf.write(f"## {cd['col_name']}\n\n")
        rf.write(f"- Pose: {cd['pose_source']} frame {cd['pose_frame']}\n")
        rf.write(f"- Scale: {[round(v,4) for v in cd['root'].scale] if cd['root'] else 'N/A'}\n")
        rf.write(f"- Validation: {'PASSED' if cd['passed'] else 'FAILED'}\n")
        if cd["issues"]:
            for i in cd["issues"]: rf.write(f"  - {i}\n")
        rf.write("\n")

print(f"REPORT_PATH={rep_path}")
print(f"LOG_PATH={log_path}")
print("LIBRARY DONE")
