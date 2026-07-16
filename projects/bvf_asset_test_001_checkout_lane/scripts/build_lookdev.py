"""
A2 Lookdev: Single-frame checkout scene with Kenney Mini assets.
1080×1920, Eevee, ortho camera. One frame only.
"""
import bpy, os, math
from mathutils import Vector

PROJ = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane"
CH = os.path.join(PROJ, "assets", "imported", "kenney_mini-characters", "Models", "GLB format")
MK = os.path.join(PROJ, "assets", "imported", "kenney_mini-market", "Models", "GLB format")
OUT = os.path.join(PROJ, "reviews", "lookdev")
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1080
scene.render.resolution_y = 1920
scene.eevee.use_shadows = True

def imp(path):
    bpy.ops.import_scene.gltf(filepath=path)
    return bpy.context.selected_objects

def move_group(objects, dx, dy, dz):
    for o in objects: o.location.x += dx; o.location.y += dy; o.location.z += dz

# ── Import Assets ─────────────────────────────────────────
print("Importing assets...")
floor_tile = imp(os.path.join(MK, "floor.glb"))
cashregn = imp(os.path.join(MK, "cash-register.glb"))
freezern = imp(os.path.join(MK, "freezers-standing.glb"))
shelf_bx = imp(os.path.join(MK, "shelf-boxes.glb"))
display_b = imp(os.path.join(MK, "display-bread.glb"))
display_f = imp(os.path.join(MK, "display-fruit.glb"))
columnn = imp(os.path.join(MK, "column.glb"))

# Characters
male_a = imp(os.path.join(CH, "character-male-a.glb"))
female_a = imp(os.path.join(CH, "character-female-a.glb"))
male_b = imp(os.path.join(CH, "character-male-b.glb"))
female_b = imp(os.path.join(CH, "character-female-b.glb"))
employee = imp(os.path.join(MK, "character-employee.glb"))

print(f"Objects: {len(bpy.data.objects)}")

# ── Build Counter (Kenney has no checkout counter — build from primitives) ──
# Main counter surface
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 1.5, 0.7))
counter = bpy.context.object
counter.name = "CheckoutCounter"
counter.scale = (1.5, 0.4, 0.7)

# Simple mat for counter — warm gray-beige
cm = bpy.data.materials.new("CounterMat")
cm.use_nodes = True
cm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.75, 0.70, 0.62, 1.0)
cm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.5
counter.data.materials.append(cm)

# Conveyor belt line on top
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 1.5, 1.41))
belt = bpy.context.object
belt.name = "ConveyorBelt"
belt.scale = (1.2, 0.35, 0.02)
bm = bpy.data.materials.new("BeltMat")
bm.use_nodes = True
bm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.15, 0.13, 0.11, 1.0)
bm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.35
belt.data.materials.append(bm)

# ── Second counter (right lane) ──
bpy.ops.mesh.primitive_cube_add(size=1, location=(1.6, 1.5, 0.7))
counter2 = bpy.context.object
counter2.name = "CheckoutCounter2"
counter2.scale = (1.5, 0.4, 0.7)
counter2.data.materials.append(cm)

bpy.ops.mesh.primitive_cube_add(size=1, location=(1.6, 1.5, 1.41))
belt2 = bpy.context.object
belt2.name = "ConveyorBelt2"
belt2.scale = (1.2, 0.35, 0.02)
belt2.data.materials.append(bm)

# ── Position Assets ───────────────────────────────────────
# Floor — scale to cover scene
for f in floor_tile:
    f.location = (0, 0, 0)
    f.scale = (5, 6, 1)

# Cash register on left counter
move_group(cashregn, -0.1, 1.65, 1.42)

# Display bread on counter
move_group(display_b, 0.4, 1.65, 1.42)

# Display fruit on counter
move_group(display_f, -0.6, 1.65, 1.42)

# Freezer background (behind counters)
move_group(freezern, 2.5, 2.5, 0)

# Shelf background
for s in shelf_bx:
    s.location = (-2.2, 2.5, 0)

# Column for structure
for c in columnn:
    c.location = (-2.5, 2.8, 0)

# Employee (cashier) behind left counter
move_group(employee, -0.1, 2.0, 0.75)

# Customer 1 — queued at left counter
move_group(male_a, -0.3, 0.8, 0)
# Customer 2 — behind customer 1
move_group(female_a, -0.3, 0.2, 0)
# Customer 3 — queued at right counter
move_group(male_b, 1.3, 0.8, 0)
# Customer 4 — behind customer 3
move_group(female_b, 1.3, 0.2, 0)

# ── Lighting ──────────────────────────────────────────────
bpy.ops.object.light_add(type='SUN', location=(4, -5, 9))
sun = bpy.context.object
sun.data.energy = 3.2; sun.data.angle = 0.12
sun.data.color = (1.0, 0.96, 0.88)

bpy.ops.object.light_add(type='AREA', location=(-2, -1, 4))
fill = bpy.context.object
fill.data.energy = 2.5; fill.data.color = (0.85, 0.88, 1.0)
fill.data.size = 3

# Rim light
bpy.ops.object.light_add(type='SUN', location=(0, 3, 5))
rim = bpy.context.object
rim.data.energy = 0.8; rim.data.color = (0.95, 0.93, 0.88)
rim.data.angle = 0.08

world = bpy.data.worlds.new("LookdevWorld")
scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.30, 0.28, 0.25, 1.0)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.25

# ── Camera: Ortho, bbox-driven ────────────────────────────
cam_data = bpy.data.cameras.new("LookdevCam")
cam_data.type = 'ORTHO'
cam_obj = bpy.data.objects.new("LookdevCam", cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj
cam_obj.location = (0.5, -4.5, 7.5)
cam_obj.rotation_euler = (math.radians(48), 0, 0)
cam_data.ortho_scale = 6.5
cam_data.shift_y = -0.15

# ── Render ────────────────────────────────────────────────
out = os.path.join(OUT, "F001_lookdev_v1.png")
scene.render.filepath = out
bpy.ops.render.render(write_still=True)
print(f"Rendered: {out}")

# ── Save ──────────────────────────────────────────────────
blend = os.path.join(PROJ, "scene", "lookdev_v1.blend")
bpy.ops.wm.save_mainfile(filepath=blend)
print(f"Saved: {blend}")
print("LOOKDEV V1 COMPLETE")
