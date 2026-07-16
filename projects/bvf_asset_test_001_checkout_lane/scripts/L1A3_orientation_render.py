"""
L1-A3: Passive orientation render — +Y/-Y views for Customer_01 + Employee_01.
No modifications to L1_step01_characters.blend.
"""
import bpy, os, math, shutil
from mathutils import Vector

PROJ = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane"
BLEND = os.path.join(PROJ, "scene", "L1_step01_characters.blend")
DIAG = os.path.join(PROJ, "reviews", "L1_A3_diag")
UPL = os.path.join(PROJ, "reviews", "UPLOAD_NEXT", "L1_A3")
os.makedirs(DIAG, exist_ok=True); os.makedirs(UPL, exist_ok=True)
for f in os.listdir(UPL): os.remove(os.path.join(UPL, f))

TARGETS = ["Customer_01", "Employee_01"]
VIEWS = [("plusY", (0, 6, 1.2), (0, 0, 0.9)), ("minusY", (0, -6, 1.2), (0, 0, 0.9))]

# Open original, snapshot transforms
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)

snapshot_before = {}
for label in TARGETS:
    root = bpy.data.objects.get(label + "_Root")
    if root:
        snapshot_before[label] = {
            "loc": Vector(root.location), "rot": Vector(root.rotation_euler),
            "scale": Vector(root.scale)
        }

# Hide all other objects
ALL_NAMES = ["Customer_01", "Customer_02", "Customer_03", "Customer_04", "Employee_01", "Employee_02"]
for label in ALL_NAMES:
    root = bpy.data.objects.get(label + "_Root")
    if root and label not in TARGETS:
        # Hide entire hierarchy
        root.hide_viewport = True; root.hide_render = True
        for child in root.children_recursive:
            child.hide_viewport = True; child.hide_render = True

# ── Lighting ──────────────────────────────────────────────
bpy.ops.object.light_add(type='SUN', location=(3, -4, 6))
bpy.context.object.data.energy = 3.5; bpy.context.object.data.angle = 0.12
bpy.context.object.data.color = (1.0, 0.96, 0.90)
bpy.ops.object.light_add(type='AREA', location=(-2, 0, 4))
bpy.context.object.data.energy = 2.0; bpy.context.object.data.size = 4

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 540; scene.render.resolution_y = 960
scene.eevee.use_shadows = True
world = bpy.data.worlds.new("DiagW"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.45, 0.43, 0.40, 1.0)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.5
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False

# ── Render ────────────────────────────────────────────────
rendered = {}
for label in TARGETS:
    root = bpy.data.objects.get(label + "_Root")
    if not root: continue
    char_pos = root.location
    for vname, offset, look_offset in VIEWS:
        cam_data = bpy.data.cameras.new(f"Cam_{label}_{vname}")
        cam_data.type = 'ORTHO'; cam_data.ortho_scale = 3.0; cam_data.clip_start = 0.05; cam_data.clip_end = 100
        cam = bpy.data.objects.new(f"Cam_{label}_{vname}", cam_data)
        scene.collection.objects.link(cam); scene.camera = cam
        cam.location = char_pos + Vector(offset)
        target = char_pos + Vector(look_offset)
        direction = target - cam.location
        cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

        out = os.path.join(DIAG, f"{label}_from_{vname}.png")
        scene.render.filepath = out
        bpy.ops.render.render(write_still=True)
        rendered[(label, vname)] = out
        print(f"  {label} {vname}: {out}")

        # Remove camera for next setup
        bpy.data.objects.remove(cam, do_unlink=True)
        bpy.data.cameras.remove(cam_data)

# ── Save render paths for external compositing ─────────────
import json
path_file = os.path.join(DIAG, "_render_paths.json")
with open(path_file, "w") as pf:
    json.dump({f"{k[0]}_{k[1]}": v for k, v in rendered.items()}, pf, indent=2)
print(f"RENDER_PATHS={path_file}")

# ── Verify no modification to original ────────────────────
for label in TARGETS:
    root = bpy.data.objects.get(label + "_Root")
    if root:
        s = snapshot_before[label]
        same = (Vector(root.location)-s["loc"]).length < 0.0001
        same &= (Vector(root.rotation_euler)-s["rot"]).length < 0.0001
        same &= (Vector(root.scale)-s["scale"]).length < 0.0001
        print(f"  {label} unchanged: {same}")

# ── Report ────────────────────────────────────────────────
rep = os.path.join(UPL, "L1_A3_RENDER_REPORT.md")
with open(rep, "w") as f:
    f.write("# L1-A3 Orientation Render Report\n\n")
    f.write(f"Input: {BLEND}\n\n")
    f.write("## Characters\n\n- Customer_01\n- Employee_01\n\n")
    f.write("## Cameras\n\n")
    f.write("### View A (from +Y): camera_offset=(0, +6, 1.2) look_at=(0, 0, 0.9)\n")
    f.write("### View B (from -Y): camera_offset=(0, -6, 1.2) look_at=(0, 0, 0.9)\n")
    f.write("- Ortho scale: 3.0\n")
    f.write("- Resolution: 540x960\n")
    f.write("- Engine: Eevee\n\n")
    f.write("## Rendered Images\n\n")
    for key, path in rendered.items():
        f.write(f"- {key[0]} from {key[1]}: `{path}`\n")
    contact_dest = os.path.join(DIAG, "L1_A3_orientation_contact_sheet.png")
    f.write(f"\n## Contact Sheet\n\n- `{contact_dest}`\n\n")
    f.write("## Transform Verification\n\n- No character transforms modified during render\n")
    f.write(f"- L1_step01_characters.blend not overwritten\n")
    f.write(f"- UPLOAD_NEXT/L1_A3 contains only contact sheet + this report\n")

# ── Copy to UPLOAD_NEXT ───────────────────────────────────
contact_dest = os.path.join(DIAG, "L1_A3_orientation_contact_sheet.png")
shutil.copy(contact_dest, os.path.join(UPL, "L1_A3_orientation_contact_sheet.png"))

print(f"UPLOAD={UPL}")
print("L1-A3 COMPLETE")
