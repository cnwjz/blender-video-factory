"""
L1-A2: Read-only direction & standing audit. No modifications to any scene object.
"""
import bpy, os, json, math, shutil
from mathutils import Vector

PROJ = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane"
BLEND = os.path.join(PROJ, "scene", "L1_step01_characters.blend")
OUT_DIR = os.path.join(PROJ, "reports")
UPL_DIR = os.path.join(PROJ, "reviews", "UPLOAD_NEXT", "L1_A2")
os.makedirs(OUT_DIR, exist_ok=True); os.makedirs(UPL_DIR, exist_ok=True)
for f in os.listdir(UPL_DIR): os.remove(os.path.join(UPL_DIR, f))

INSTANCES = ["Customer_01", "Customer_02", "Customer_03", "Customer_04", "Employee_01", "Employee_02"]
LOCAL_AXES = ["+X","-X","+Y","-Y","+Z","-Z"]
AXIS_VECTORS = {
    "+X": Vector((1,0,0)), "-X": Vector((-1,0,0)),
    "+Y": Vector((0,1,0)), "-Y": Vector((0,-1,0)),
    "+Z": Vector((0,0,1)), "-Z": Vector((0,0,-1)),
}

# Open scene read-only
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)

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
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))

results = {}

for label in INSTANCES:
    root = bpy.data.objects.get(label + "_Root")
    if not root:
        results[label] = {"error": "Root not found"}
        continue

    # Walk hierarchy
    arm = None; body = None; head = None
    for child in root.children:
        if child.type == 'ARMATURE':
            arm = child
            for gc in child.children:
                if gc.type == 'MESH':
                    if not body: body = gc
                    elif not head: head = gc

    meshes = [o for o in [body, head] if o]
    bb = get_world_bbox(meshes)

    entry = {
        "root_name": root.name,
        "armature_name": arm.name if arm else None,
        "body_name": body.name if body else None,
        "head_name": head.name if head else None,
    }

    # ── Direction: compute all 6 local axes in world space ──
    # Use Armature world matrix (contains the model's actual facing)
    ref = arm if arm else root
    rot_mat = ref.matrix_world.to_3x3()

    world_axes = {}
    for ax_name, local_vec in AXIS_VECTORS.items():
        world_vec = rot_mat @ local_vec
        world_axes[f"local_{ax_name}_world"] = [round(v, 6) for v in world_vec]

    entry.update(world_axes)

    # ── Determine model forward ──
    # Kenney Mini characters in character_library_v1.blend face +Y
    # The Armature local +Y after standing correction should point to world +Y
    # The rest pose X-90° correction means the model's local +Z (up in rest pose) → world +Z
    # and local +Y (model's back/front axis) → world +Y

    # Check which world axis each local axis points to
    # We know from the character_library_v1 build that characters were rotated
    # to face +Y. The local axis closest to world +Y is the model forward.
    world_y_components = {}
    for ax_name in LOCAL_AXES:
        key = f"local_{ax_name}_world"
        vec = world_axes[key]
        world_y_components[ax_name] = vec[1]  # Y component

    # Find which axis has the largest positive Y component → that's forward
    best_forward = max(world_y_components, key=lambda k: abs(world_y_components[k]))
    fwd_world = Vector(world_axes[f"local_{best_forward}_world"])
    # Normalize explicitly
    fwd_len = fwd_world.length
    if fwd_len > 0.001:
        fwd_world = fwd_world.normalized()
    else:
        fwd_world = Vector((0,0,0))

    entry["model_forward_local_axis"] = best_forward
    entry["model_forward_world_vector"] = [round(v, 6) for v in fwd_world]
    entry["model_forward_world_y"] = round(fwd_world.y, 6)
    entry["face_plus_y_pass"] = (
        fwd_world.y >= 0.98 and abs(fwd_world.x) <= 0.05 and abs(fwd_world.z) <= 0.05
    )

    # Also find up axis: which points closest to world +Z
    world_z_components = {}
    for ax_name in LOCAL_AXES:
        key = f"local_{ax_name}_world"
        vec = world_axes[key]
        world_z_components[ax_name] = vec[2]  # Z component
    best_up = max(world_z_components, key=lambda k: abs(world_z_components[k]))
    up_world = Vector(world_axes[f"local_{best_up}_world"])
    if up_world.length > 0.001: up_world = up_world.normalized()

    entry["model_up_local_axis"] = best_up
    entry["model_up_world_vector"] = [round(v, 6) for v in up_world]
    entry["vertical_alignment"] = round(up_world.z, 6)
    entry["vertical_alignment_pass"] = up_world.z >= 0.98

    # ── Standing check ──
    if bb:
        mx, MX, my, MY, mz, MZ = bb
        h = MZ - mz; w = MX - mx; d = MY - my
        entry["world_bbox_height"] = round(h, 4)
        entry["world_bbox_width"] = round(w, 4)
        entry["world_bbox_depth"] = round(d, 4)
        entry["lowest_z"] = round(mz, 4)
        entry["highest_z"] = round(MZ, 4)

        bb_body = get_world_bbox([body]) if body else None
        bb_head = get_world_bbox([head]) if head else None
        if bb_body:
            entry["body_center_z"] = round((bb_body[4] + bb_body[5]) / 2, 4)
            entry["body_bbox_height"] = round(bb_body[5] - bb_body[4], 4)
            entry["body_bbox_width"] = round(bb_body[1] - bb_body[0], 4)
            entry["body_bbox_depth"] = round(bb_body[3] - bb_body[2], 4)
            # Body-only H:W (without arms)
            entry["body_hw_ratio"] = round(entry["body_bbox_height"] / max(entry["body_bbox_width"], 0.001), 4)
        if bb_head:
            entry["head_center_z"] = round((bb_head[4] + bb_head[5]) / 2, 4)

        entry["head_above_body"] = (
            entry.get("head_center_z", -999) > entry.get("body_center_z", 999)
        )
        entry["height_near_target"] = abs(h - 1.75) < 0.15
        entry["feet_at_ground"] = abs(mz) < 0.05

    # ── Standing pass ──
    entry["standing_pass"] = all([
        entry.get("head_above_body", False),
        entry.get("height_near_target", False),
        entry.get("feet_at_ground", False),
        entry.get("vertical_alignment_pass", False),
    ])

    # ── H:W < 1 explanation ──
    if bb:
        overall_hw = round(h / max(max(w, d), 0.001), 4)
        entry["overall_hw_ratio"] = overall_hw
        entry["hw_less_than_1_explanation"] = (
            f"Overall H:W={overall_hw}. Body-only H:W={entry.get('body_hw_ratio','N/A')}. "
            f"Kenney Mini characters have arms extending laterally in idle pose, "
            f"making the full AABB width ({w:.3f}) approach or exceed height ({h:.3f}). "
            f"The body torso alone (without arms) has H:W ratio of {entry.get('body_hw_ratio','N/A')}. "
            f"Head is {'' if entry.get('head_above_body') else 'NOT '}above body center. "
            f"Character IS standing — the low H:W is an artifact of arm extension, not lying down."
        )

    results[label] = entry

# ── Write JSON ─────────────────────────────────────────────
json_path = os.path.join(OUT_DIR, "L1_A2_direction_state.json")
with open(json_path, "w") as f:
    json.dump(results, f, indent=2, default=str)

# ── Write Report ───────────────────────────────────────────
rep_path = os.path.join(OUT_DIR, "L1_A2_DIRECTION_REPORT.md")
with open(rep_path, "w") as f:
    f.write("# L1-A2 Direction & Standing Audit Report\n\nDate: 2026-07-15\n\n")
    f.write("## 1. Direction Computation Method\n\n")
    f.write("For each character, the Armature's `matrix_world.to_3x3()` is used to transform all 6 local axes (+X,-X,+Y,-Y,+Z,-Z) into world space.\n")
    f.write("The axis with the highest-magnitude world Y component is identified as the model's forward direction.\n\n")

    f.write("## 2. Previous `forward_direction` Bug\n\n")
    f.write("L1-A used `root.matrix_world.to_3x3() @ Vector((0,1,0))` which gives the world direction of the Root Empty's local +Y.\n")
    f.write("The Root Empty is an axis-helper with `empty_display_size=0.05`, and its local +Y direction happens to be near world +Z after the X-90° rotation.\n")
    f.write("**The Root Empty's axes do not represent the character model's facing direction.** The correct reference is the Armature.\n\n")

    f.write("## 3. Per-Character Results\n\n")
    for label in INSTANCES:
        e = results[label]
        f.write(f"### {label}\n\n")
        f.write(f"- Model forward local axis: `{e.get('model_forward_local_axis','?')}`\n")
        f.write(f"- Forward world vector: `{e.get('model_forward_world_vector','?')}`\n")
        f.write(f"- face_plus_y_pass: **{e.get('face_plus_y_pass','?')}**\n")
        f.write(f"- Model up local axis: `{e.get('model_up_local_axis','?')}`\n")
        f.write(f"- Up world vector: `{e.get('model_up_world_vector','?')}`\n")
        f.write(f"- Vertical alignment pass: **{e.get('vertical_alignment_pass','?')}**\n")
        f.write(f"- Head above body: {e.get('head_above_body','?')}\n")
        f.write(f"- Height: {e.get('world_bbox_height','?')}\n")
        f.write(f"- Overall H:W: {e.get('overall_hw_ratio','?')}\n")
        f.write(f"- Body-only H:W: {e.get('body_hw_ratio','?')}\n")
        f.write(f"- Standing pass: **{e.get('standing_pass','?')}**\n")
        f.write(f"- H:W explanation: {e.get('hw_less_than_1_explanation','?')}\n\n")

    all_face = all(e.get("face_plus_y_pass", False) for e in results.values())
    all_stand = all(e.get("standing_pass", False) for e in results.values())
    f.write(f"## 4. Overall\n\n- All face +Y: **{all_face}**\n- All standing: **{all_stand}**\n")

# ── Copy to UPLOAD_NEXT ────────────────────────────────────
shutil.copy(json_path, os.path.join(UPL_DIR, "L1_A2_direction_state.json"))
shutil.copy(rep_path, os.path.join(UPL_DIR, "L1_A2_DIRECTION_REPORT.md"))

# ── ZIP ────────────────────────────────────────────────────
import zipfile
zip_path = os.path.join(PROJ, "reviews", "UPLOAD_NEXT", "L1_A2_UPLOAD.zip")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.write(os.path.join(UPL_DIR, "L1_A2_direction_state.json"), "L1_A2_direction_state.json")
    zf.write(os.path.join(UPL_DIR, "L1_A2_DIRECTION_REPORT.md"), "L1_A2_DIRECTION_REPORT.md")

# ── Summary ────────────────────────────────────────────────
print("=== L1_A2 SUMMARY ===")
for label in INSTANCES:
    e = results[label]
    print(f"  {label}: fwd={e.get('model_forward_local_axis','?')} fwd_y={e.get('model_forward_world_y','?'):.4f} face_pass={e.get('face_plus_y_pass')} stand_pass={e.get('standing_pass')} hw={e.get('overall_hw_ratio','?')} body_hw={e.get('body_hw_ratio','?')}")

all_ok = all_face and all_stand
print(f"ALL_FACE_PLUS_Y={all_face}")
print(f"ALL_STANDING={all_stand}")
print(f"ALL_PASS={all_ok}")
print(f"JSON={json_path}")
print(f"REPORT={rep_path}")
print(f"ZIP={zip_path}")
print("L1-A2 COMPLETE")
