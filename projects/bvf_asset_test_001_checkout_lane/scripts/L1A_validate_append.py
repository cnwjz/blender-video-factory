"""
L1-A: Append character library, validate structured state, save, re-open, re-validate.
"""
import bpy, os, json, math
from mathutils import Vector, Matrix

PROJ = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane"
LIB = os.path.join(PROJ, "scene", "character_library_v1.blend")
OUT_BLEND = os.path.join(PROJ, "scene", "L1_step01_characters.blend")
OUT_JSON = os.path.join(PROJ, "reports", "L1_A_motion_state.json")
OUT_REPORT = os.path.join(PROJ, "reports", "L1_A_TECHNICAL_REPORT.md")
os.makedirs(os.path.join(PROJ, "reports"), exist_ok=True)

# ── Mapping ────────────────────────────────────────────────
MAPPING = [
    ("CHR_MALE_A", "Customer_01_Root"),
    ("CHR_FEMALE_A", "Customer_02_Root"),
    ("CHR_MALE_B", "Customer_03_Root"),
    ("CHR_FEMALE_B", "Customer_04_Root"),
    ("CHR_EMPLOYEE", "Employee_01_Root"),
    ("CHR_EMPLOYEE", "Employee_02_Root"),
]

TARGET_H = 1.75
REPORT_LINES = []
def log(s): print(s); REPORT_LINES.append(s)

# ── Helpers ────────────────────────────────────────────────
def fresh_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = 'BLENDER_EEVEE'
    s.render.resolution_x = 1080; s.render.resolution_y = 1920
    return s

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

def extract_state(label):
    """Extract structured state for one character instance by walking hierarchy from Root."""
    root_name = label + "_Root"
    root = bpy.data.objects.get(root_name)
    # Walk children to find Armature, then Body/Head under Armature
    arm = None; body = None; head = None
    if root:
        for child in root.children:
            if child.type == 'ARMATURE':
                arm = child
                for gc in child.children:
                    if gc.type == 'MESH':
                        if not body: body = gc
                        elif not head: head = gc
    arm_name = arm.name if arm else None
    body_name = body.name if body else None
    head_name = head.name if head else None

    state = {
        "instance_name": label,
        "root_name": root_name,
        "armature_name": arm_name,
        "body_name": body_name,
        "head_name": head_name,
        "root_exists": root is not None,
        "armature_exists": arm is not None,
        "body_exists": body is not None,
        "head_exists": head is not None,
    }

    if not all([root, arm, body, head]):
        state["validation_result"] = "FAILED — missing object"
        return state

    # Hierarchy
    state["body_parent"] = body.parent.name if body.parent else None
    state["head_parent"] = head.parent.name if head.parent else None
    state["body_parent_is_armature"] = body.parent == arm
    state["head_parent_is_armature"] = head.parent == arm
    state["armature_parent_is_root"] = arm.parent == root

    # World transforms
    state["root_matrix_world"] = [[round(v, 4) for v in row] for row in root.matrix_world]
    state["armature_matrix_world"] = [[round(v, 4) for v in row] for row in arm.matrix_world]

    # BBox
    meshes = [o for o in [body, head] if o and o.type == 'MESH']
    bb = get_world_bbox(meshes)
    if bb:
        mx, MX, my, MY, mz, MZ = bb
        state["bbox_min"] = [round(mx,4), round(my,4), round(mz,4)]
        state["bbox_max"] = [round(MX,4), round(MY,4), round(MZ,4)]
        h = MZ - mz; w = MX - mx; d = MY - my
        state["height"] = round(h, 4)
        state["width"] = round(w, 4)
        state["depth"] = round(d, 4)
        state["height_width_ratio"] = round(h / max(w, 0.001), 4)
        state["lowest_z"] = round(mz, 4)
        state["highest_z"] = round(MZ, 4)

        # Head/body centers
        bb_body = get_world_bbox([body]) if body else None
        bb_head = get_world_bbox([head]) if head else None
        if bb_body: state["body_center_z"] = round((bb_body[4]+bb_body[5])/2, 4)
        if bb_head: state["head_center_z"] = round((bb_head[4]+bb_head[5])/2, 4)
    else:
        state["height"] = 0

    # Forward direction from Armature (or Root if armature unavailable)
    ref = arm if arm else root
    local_fwd = ref.matrix_world.to_3x3() @ Vector((0, 1, 0))
    state["forward_direction"] = [round(v, 4) for v in local_fwd]

    # Stray objects
    all_objs = list(bpy.data.objects)
    ico_count = sum(1 for o in all_objs if o.type == 'MESH' and o.name.lower().startswith('icosphere') and o.parent is None)
    state["icosphere_count"] = ico_count

    # Visibility
    state["root_hide_render"] = root.hide_render
    state["body_hide_render"] = body.hide_render
    state["head_hide_render"] = head.hide_render

    # Collection visibility
    state["collections_render_visible"] = []
    for col in root.users_collection:
        state["collections_render_visible"].append({"name": col.name, "hide_render": col.hide_render})

    # Validation
    issues = []
    if not state.get("armature_parent_is_root"): issues.append("Armature not child of Root")
    if not state.get("body_parent_is_armature"): issues.append("Body not child of Armature")
    if not state.get("head_parent_is_armature"): issues.append("Head not child of Armature")
    if state.get("icosphere_count", 0) > 0: issues.append(f"Icosphere count={ico_count}")
    if state.get("body_hide_render"): issues.append("Body hide_render=True")
    if state.get("head_hide_render"): issues.append("Head hide_render=True")

    h = state.get("height", 0)
    ratio = state.get("height_width_ratio", 0)
    if h > 0:
        if abs(h - TARGET_H) > 0.15: issues.append(f"Height={h:.3f} vs target {TARGET_H}")
    if ratio > 0:
        if ratio < 0.85: issues.append(f"H:W ratio={ratio:.3f} < 0.85")

    lowest = state.get("lowest_z", 0)
    if abs(lowest) > 0.05: issues.append(f"Lowest Z={lowest:.4f} not at ground")

    head_cz = state.get("head_center_z", 0)
    body_cz = state.get("body_center_z", 0)
    if head_cz and body_cz and head_cz <= body_cz:
        issues.append(f"Head center Z={head_cz:.3f} <= Body center Z={body_cz:.3f}")

    state["issues"] = issues
    state["validation_result"] = "PASSED" if not issues else "FAILED — " + "; ".join(issues)
    return state

# ═══════════════════════════════════════════════════════════
# BUILD
# ═══════════════════════════════════════════════════════════
scene = fresh_scene()
log("=== L1-A: Append Character Library ===")
log(f"Library: {LIB}")
log(f"Target height: {TARGET_H}")

# Append collections
prev_objs = set(bpy.data.objects)
for col_name, inst_name in MAPPING:
    log(f"  Append {col_name} → {inst_name}")
    dir_path = LIB + "\\Collection\\"
    bpy.ops.wm.append(directory=dir_path, filename=col_name, link=False, do_reuse_local_id=False)

    # Find the new objects
    current_objs = set(bpy.data.objects)
    new_objs = [o for o in current_objs if o not in prev_objs]
    prev_objs = current_objs

    log(f"    New objects: {len(new_objs)}")

    if not new_objs:
        log(f"    ERROR: No objects appended for {col_name}!")
        continue

    # Find the root: top-level Empty with no parent
    roots = [o for o in new_objs if o.type == 'EMPTY' and o.parent is None]
    if roots:
        root = roots[-1]
        old_name = root.name
        root.name = inst_name
        log(f"    Root: {old_name} → {inst_name}")
    else:
        # Try any top-level object
        tops = [o for o in new_objs if o.parent is None]
        if tops:
            log(f"    WARNING: No Empty root. Top objects: {[o.name for o in tops]}")
            # Use the collection to group them
        else:
            log(f"    WARNING: All new objects have parents — likely appended into existing hierarchy")

# Count instances
log(f"\nTotal objects in scene: {len(bpy.data.objects)}")

# ── Extract state for all 6 instances ──────────────────────
INSTANCE_NAMES = ["Customer_01", "Customer_02", "Customer_03", "Customer_04", "Employee_01", "Employee_02"]
all_states = {}
for name in INSTANCE_NAMES:
    log(f"  Extracting: {name}")
    all_states[name] = extract_state(name)

# Check Employee independence
emp1 = bpy.data.objects.get("Employee_01_Root")
emp2 = bpy.data.objects.get("Employee_02_Root")
employees_independent = (emp1 is not None and emp2 is not None and emp1 != emp2)

# ── Save ───────────────────────────────────────────────────
bpy.ops.wm.save_mainfile(filepath=OUT_BLEND)
log(f"\nSaved: {OUT_BLEND}")

# ── Close and re-open, re-validate ─────────────────────────
log("\n--- Re-open validation ---")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=OUT_BLEND)

reopen_states = {}
for name in INSTANCE_NAMES:
    reopen_states[name] = extract_state(name)

# Compare
reopen_issues = []
for name in INSTANCE_NAMES:
    s1 = all_states[name]
    s2 = reopen_states[name]
    if s1["validation_result"] != s2["validation_result"]:
        reopen_issues.append(f"{name}: validation changed on reopen")
    if abs(s1.get("height", 0) - s2.get("height", 0)) > 0.01:
        reopen_issues.append(f"{name}: height changed ({s1.get('height',0):.3f}→{s2.get('height',0):.3f})")

if reopen_issues:
    log("  REOPEN ISSUES:")
    for i in reopen_issues: log(f"    {i}")
else:
    log("  Reopen validation: PASSED (all states preserved)")

# ── JSON output ────────────────────────────────────────────
output_json = {
    "source_library": LIB,
    "target_height": TARGET_H,
    "instances": all_states,
    "reopen_instances": reopen_states,
    "reopen_consistency_pass": len(reopen_issues) == 0,
    "employees_independent": employees_independent,
    "total_objects": len(bpy.data.objects),
    "all_pass": all(s["validation_result"] == "PASSED" for s in all_states.values()) and len(reopen_issues) == 0 and employees_independent
}
with open(OUT_JSON, "w") as f:
    json.dump(output_json, f, indent=2, default=str)
log(f"JSON: {OUT_JSON}")

# ── Report ─────────────────────────────────────────────────
with open(OUT_REPORT, "w") as f:
    f.write("# L1-A Technical Report\n\n")
    f.write(f"Date: 2026-07-15\n")
    f.write(f"Library: {LIB}\n")
    f.write(f"Target height: {TARGET_H}\n\n")
    for name in INSTANCE_NAMES:
        s = all_states[name]
        f.write(f"## {name}\n\n")
        f.write(f"- Root: {s['root_exists']} Armature: {s['armature_exists']} Body: {s['body_exists']} Head: {s['head_exists']}\n")
        if s.get('height'):
            f.write(f"- Height: {s['height']:.3f} Width: {s['width']:.3f} H:W: {s['height_width_ratio']:.3f}\n")
            f.write(f"- Lowest Z: {s['lowest_z']:.3f} Highest Z: {s['highest_z']:.3f}\n")
        f.write(f"- Forward: {s.get('forward_direction', 'N/A')}\n")
        f.write(f"- Icosphere: {s.get('icosphere_count', '?')}\n")
        f.write(f"- Result: {s['validation_result']}\n")
        if s.get('issues'):
            for i in s['issues']: f.write(f"  - {i}\n")
        f.write("\n")
    f.write(f"## Reopen Consistency\n\n")
    f.write(f"- Pass: {len(reopen_issues)==0}\n")
    if reopen_issues:
        for i in reopen_issues: f.write(f"  - {i}\n")
    f.write(f"\n## Employees Independent\n\n- {employees_independent}\n")
    f.write(f"\n## Overall\n\n- All pass: {output_json['all_pass']}\n")

log(f"Report: {OUT_REPORT}")
log("L1-A COMPLETE")

# Print essentials for Claude Code output
print("\n=== L1_A_SUMMARY ===")
print(f"ALL_PASS={output_json['all_pass']}")
for name in INSTANCE_NAMES:
    s = all_states[name]
    status = "PASS" if s["validation_result"] == "PASSED" else "FAIL"
    print(f"  {name}: {status} h={s.get('height',0):.3f} ratio={s.get('height_width_ratio',0):.3f}")
print(f"REOPEN_CONSISTENT={len(reopen_issues)==0}")
print(f"EMPLOYEES_INDEPENDENT={employees_independent}")
print(f"JSON={OUT_JSON}")
print(f"REPORT={OUT_REPORT}")
print(f"BLEND={OUT_BLEND}")
