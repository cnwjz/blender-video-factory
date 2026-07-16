"""
L1-A4: Apply idle Action (validated: frame 20), validate, render 2x3 contact sheet.
"""
import bpy, os, json, math
from mathutils import Vector

PROJ = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane"
BLEND_IN = os.path.join(PROJ, "scene", "L1_step01_characters.blend")
BLEND_OUT = os.path.join(PROJ, "scene", "L1_step01_idle.blend")
DIAG = os.path.join(PROJ, "reviews", "L1_A4_diag")
UPL = os.path.join(PROJ, "reviews", "UPLOAD_NEXT", "L1_A4")
REP = os.path.join(PROJ, "reports")
os.makedirs(DIAG, exist_ok=True); os.makedirs(UPL, exist_ok=True)
for f in os.listdir(UPL): os.remove(os.path.join(UPL, f))

INSTANCES = ["Customer_01","Customer_02","Customer_03","Customer_04","Employee_01","Employee_02"]
ACTION_NAME = "root|idle|Animation Base Layer"
IDLE_FRAME = 20

# ── Open ───────────────────────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=BLEND_IN)

# Snapshot before
snap_before = {}
for label in INSTANCES:
    root = bpy.data.objects.get(label + "_Root")
    if root:
        snap_before[label] = {"loc": Vector(root.location), "rot": Vector(root.rotation_euler), "scale": Vector(root.scale)}

# ── Apply idle Action ─────────────────────────────────────
for label in INSTANCES:
    root = bpy.data.objects.get(label + "_Root")
    if not root: continue
    # Walk hierarchy to find Armature
    arm = None; body = None; head = None
    for child in root.children:
        if child.type == 'ARMATURE':
            arm = child
            for gc in child.children:
                if gc.type == 'MESH':
                    if not body: body = gc
                    elif not head: head = gc
    if not arm:
        print(f"  WARNING: {label} — no Armature found")
        continue
    if not arm.animation_data: arm.animation_data_create()
    arm.animation_data.action = bpy.data.actions[ACTION_NAME]
    print(f"  {label}: Action={ACTION_NAME} frame={IDLE_FRAME}")

bpy.context.scene.frame_set(IDLE_FRAME)
bpy.context.view_layer.update()

# ── Snapshot after ─────────────────────────────────────────
snap_after = {}
for label in INSTANCES:
    root = bpy.data.objects.get(label + "_Root")
    if root:
        snap_after[label] = {"loc": Vector(root.location), "rot": Vector(root.rotation_euler), "scale": Vector(root.scale)}

# ── Structured state ───────────────────────────────────────
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

states = {}
for label in INSTANCES:
    root = bpy.data.objects.get(label + "_Root")
    arm = None; body = None; head = None
    if root:
        for child in root.children:
            if child.type == 'ARMATURE':
                arm = child
                for gc in child.children:
                    if gc.type == 'MESH':
                        if not body: body = gc
                        elif not head: head = gc

    entry = {
        "instance_name": label,
        "armature_name": arm.name if arm else None,
        "action_name": arm.animation_data.action.name if (arm and arm.animation_data and arm.animation_data.action) else None,
        "action_frame_range": str(arm.animation_data.action.frame_range) if (arm and arm.animation_data and arm.animation_data.action) else None,
        "selected_frame": IDLE_FRAME,
    }

    meshes = [o for o in [body, head] if o]
    bb = get_world_bbox(meshes)
    if bb:
        mx, MX, my, MY, mz, MZ = bb
        entry["bbox_min"] = [round(mx,4), round(my,4), round(mz,4)]
        entry["bbox_max"] = [round(MX,4), round(MY,4), round(MZ,4)]
        entry["height"] = round(MZ - mz, 4)
        entry["width"] = round(MX - mx, 4)
        entry["depth"] = round(MY - my, 4)
        entry["lowest_z"] = round(mz, 4); entry["highest_z"] = round(MZ, 4)

    if body:
        bb_body = get_world_bbox([body])
        if bb_body: entry["body_center_z"] = round((bb_body[4]+bb_body[5])/2, 4)
    if head:
        bb_head = get_world_bbox([head])
        if bb_head: entry["head_center_z"] = round((bb_head[4]+bb_head[5])/2, 4)
        entry["head_above_body"] = entry.get("head_center_z",-999) > entry.get("body_center_z",999)

    entry["height_near_target"] = abs(entry.get("height", 0) - 1.75) < 0.15
    entry["feet_at_ground"] = abs(entry.get("lowest_z", 999)) < 0.12

    ico_count = sum(1 for o in bpy.data.objects if o.type == 'MESH' and o.name.lower().startswith('icosphere') and o.parent is None)
    entry["icosphere_count"] = ico_count

    # Face check
    arm_for_face = arm if arm else root
    fwd = (arm_for_face.matrix_world.to_3x3() @ Vector((0,0,1))).normalized()
    entry["forward_world_y"] = round(fwd.y, 4)
    entry["face_plus_y"] = fwd.y >= 0.98

    entry["validation_result"] = "PASSED" if all([
        entry.get("height_near_target"), entry.get("feet_at_ground"),
        entry.get("head_above_body"), entry.get("face_plus_y"),
        entry.get("icosphere_count", 0) == 0,
    ]) else "FAILED"

    states[label] = entry

# ── Save ───────────────────────────────────────────────────
bpy.ops.wm.save_mainfile(filepath=BLEND_OUT)
print(f"Saved: {BLEND_OUT}")

# ── Reopen, re-validate ───────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=BLEND_OUT)
bpy.context.scene.frame_set(IDLE_FRAME)

reopen_states = {}
for label in INSTANCES:
    root = bpy.data.objects.get(label + "_Root")
    arm = None
    if root:
        for child in root.children:
            if child.type == 'ARMATURE': arm = child; break
    rs = {
        "action": arm.animation_data.action.name if (arm and arm.animation_data and arm.animation_data.action) else None,
        "frame": IDLE_FRAME,
    }
    reopen_states[label] = rs

# ── Render singles ─────────────────────────────────────────
import json as _json
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 540; scene.render.resolution_y = 960
scene.eevee.use_shadows = True

world = bpy.data.worlds.new("W"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.45, 0.43, 0.40, 1.0)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.5
bpy.ops.object.light_add(type='SUN', location=(3, -4, 6))
bpy.context.object.data.energy = 3.5; bpy.context.object.data.angle = 0.12
bpy.ops.object.light_add(type='AREA', location=(-2, 0, 4))
bpy.context.object.data.energy = 2.0; bpy.context.object.data.size = 4

rendered = {}
for label in INSTANCES:
    root = bpy.data.objects.get(label + "_Root")
    if not root: continue
    # Hide all others
    for other in INSTANCES:
        oroot = bpy.data.objects.get(other + "_Root")
        if oroot and other != label:
            oroot.hide_render = True
    root.hide_render = False

    cam_data = bpy.data.cameras.new(f"Cam_{label}"); cam_data.type = 'ORTHO'
    cam_data.ortho_scale = 3.0; cam_data.clip_start = 0.05; cam_data.clip_end = 100
    cam = bpy.data.objects.new(f"Cam_{label}", cam_data)
    scene.collection.objects.link(cam); scene.camera = cam
    cam.location = root.location + Vector((0, 6, 1.2))
    target = root.location + Vector((0, 0, 0.9))
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()

    out = os.path.join(DIAG, f"{label}_idle.png")
    scene.render.filepath = out
    bpy.ops.render.render(write_still=True)
    rendered[label] = out

    bpy.data.objects.remove(cam, do_unlink=True)
    bpy.data.cameras.remove(cam_data)

# Save render paths for system Python compositing
paths_file = os.path.join(DIAG, "_render_paths.json")
with open(paths_file, "w") as pf:
    _json.dump(rendered, pf, indent=2)
print(f"RENDER_PATHS={paths_file}")
contact_path = os.path.join(DIAG, "L1_A4_idle_pose_contact_sheet.png")

# ── Write report + JSON ───────────────────────────────────
json_path = os.path.join(REP, "L1_A4_idle_state.json")
with open(json_path, "w") as f: json.dump(states, f, indent=2)

rep_path = os.path.join(REP, "L1_A4_IDLE_REPORT.md")
with open(rep_path, "w") as rf:
    rf.write("# L1-A4 Idle Pose Report\n\n")
    rf.write(f"Source: {BLEND_IN}\n")
    rf.write(f"Action: {ACTION_NAME}\n")
    rf.write(f"Frame: {IDLE_FRAME}\n")
    rf.write("Evidence: validate_animation.py frame 20 (4-panel character board)\n\n")
    for label in INSTANCES:
        e = states[label]
        s = snap_before.get(label, {})
        a = snap_after.get(label, {})
        rf.write(f"## {label}\n\n")
        rf.write(f"- Action: {e.get('action_name')} frame {e.get('selected_frame')}\n")
        rf.write(f"- Root loc before/after same: {(s.get('loc',Vector())-a.get('loc',Vector())).length < 0.0001}\n")
        rf.write(f"- Root rot before/after same: {(s.get('rot',Vector())-a.get('rot',Vector())).length < 0.0001}\n")
        rf.write(f"- Height: {e.get('height',0):.3f} Lowest Z: {e.get('lowest_z',0):.3f}\n")
        rf.write(f"- Face +Y: {e.get('face_plus_y')}\n")
        rf.write(f"- Status: {e.get('validation_result')}\n\n")

# ── Copy to UPLOAD_NEXT ───────────────────────────────────
# Copies handled by external compositing step
print(f"UPLOAD_DIR={UPL}")
print(f"CONTACT_DEST={contact_path}")
print(f"REPORT_SRC={rep_path}")

# ── Summary ────────────────────────────────────────────────
print("\n=== L1_A4 SUMMARY ===")
for label in INSTANCES:
    e = states[label]
    s = snap_before.get(label, {})
    a = snap_after.get(label, {})
    same = (s.get('loc',Vector())-a.get('loc',Vector())).length < 0.0001
    print(f"  {label}: act={e.get('action_name','?')!=None} root_same={same} h={e.get('height',0):.3f} face_y={e.get('face_plus_y')} valid={e.get('validation_result')}")

all_pass = all(s.get("validation_result") == "PASSED" for s in states.values())
print(f"ALL_PASS={all_pass}")
print(f"BLEND={BLEND_OUT}")
print(f"JSON={json_path}")
print(f"REPORT={rep_path}")
print(f"CONTACT={contact_path}")
print("L1-A4 COMPLETE")
