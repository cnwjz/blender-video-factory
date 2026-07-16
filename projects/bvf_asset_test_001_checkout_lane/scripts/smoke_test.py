"""
A1 Smoke Test: Import Kenney assets, check compatibility, render board.
"""
import bpy, os, sys, json, math
from mathutils import Vector

PROJ = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane"
CHARS_GLB = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane\assets\imported\kenney_mini-characters\Models\GLB format"
MKT_GLB = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane\assets\imported\kenney_mini-market\Models\GLB format"
OUT = os.path.join(PROJ, "reviews", "asset_smoke")
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.film_transparent = True
scene.eevee.use_shadows = True

# ── Import assets ─────────────────────────────────────────
def imp_glb(path):
    bpy.ops.import_scene.gltf(filepath=path)
    return bpy.context.selected_objects

print("Importing character...")
male_glb = os.path.join(CHARS_GLB, "character-male-a.glb")
chars = imp_glb(male_glb)
char = chars[0] if chars else None
print(f"  {len(chars)} objects, root: {char.name if char else 'N/A'}")

print("Importing employee...")
emp_glb = os.path.join(MKT_GLB, "character-employee.glb")
emps = imp_glb(emp_glb)
emp = emps[0] if emps else None
print(f"  {len(emps)} objects")

print("Importing cash register...")
cr_glb = os.path.join(MKT_GLB, "cash-register.glb")
crs = imp_glb(cr_glb)
print(f"  {len(crs)} objects")

print("Importing display bread...")
bread_glb = os.path.join(MKT_GLB, "display-bread.glb")
breads = imp_glb(bread_glb)

print("Importing display fruit...")
fruit_glb = os.path.join(MKT_GLB, "display-fruit.glb")
fruits = imp_glb(fruit_glb)

print("Importing floor...")
floor_glb = os.path.join(MKT_GLB, "floor.glb")
floors = imp_glb(floor_glb)

print("Importing freezer...")
freezer_glb = os.path.join(MKT_GLB, "freezer.glb")
freezers = imp_glb(freezer_glb)

total = len(bpy.data.objects)
print(f"Total objects in scene: {total}")

# ── Position assets for the board ─────────────────────────
# Layout: 3 columns
# Col 0: Character solo (centered)
# Col 1: Character + counter + employee
# Col 2: Full scene (character, counter, products, shelf background)

def move_to(obj, x, y, z=0):
    """Move root object to world position."""
    if obj:
        obj.location = Vector((x, y, z))

# Ground plane (shared)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -0.01))
ground = bpy.context.object
ground.name = "SmokeGround"
ground.scale = (10, 10, 1)

# Col 0: solo male character at (-3, 0)
if char:
    move_to(char, -3, 0, 0)

# Col 1: character + counter + employee at (0, 0)
if char:
    # Duplicate character for col 1 and 2 isn't straightforward with GLB imports.
    # Let's use the employee as a stand-in or import more variants.
    pass
if emp:
    move_to(emp, 0.5, -0.5, 0)

# Move cash register
for obj in crs:
    if obj.type == 'MESH':
        obj.location.x += 0
        obj.location.y += 0.3
        obj.location.z = 0

# Move bread display to col 1
for obj in breads:
    obj.location.x += -0.8
    obj.location.y += 0.5
    obj.location.z = 0

# Move display fruit to col 2
for obj in fruits:
    obj.location.x += 2.2
    obj.location.y += 0.5
    obj.location.z = 0

# Position freezer at back
for obj in freezers:
    obj.location.x += 2
    obj.location.y += -1.5
    obj.location.z = 0

# ── Lighting ──────────────────────────────────────────────
bpy.ops.object.light_add(type='SUN', location=(5, -5, 8))
sun = bpy.context.object
sun.data.energy = 3; sun.data.color = (1, 0.96, 0.90)
sun.data.angle = 0.1

bpy.ops.object.light_add(type='AREA', location=(-2, 0, 4))
fill = bpy.context.object
fill.data.energy = 1.5; fill.data.color = (0.88, 0.88, 1.0); fill.data.size = 4

world = bpy.data.worlds.new("SmokeWorld")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.4, 0.38, 0.35, 1.0)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.3

# ── Camera ────────────────────────────────────────────────
bpy.ops.object.camera_add(location=(0, -5, 5))
cam = bpy.context.object
cam.name = "SmokeCam"
scene.camera = cam
cam.rotation_euler = (math.radians(55), 0, 0)
cam.rotation_euler = (math.radians(55), 0, 0)  # Looking down at scene

# ── Render ────────────────────────────────────────────────
out = os.path.join(OUT, "smoke_test.png")
scene.render.filepath = out
bpy.ops.render.render(write_still=True)
print(f"Rendered: {out}")

# ── Object Audit ──────────────────────────────────────────
print("\n=== Asset Audit ===")
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        mats = [s.material.name for s in obj.material_slots if s.material]
        print(f"  {obj.name}: verts={len(obj.data.vertices)} mats={mats[:3]}")

print("SMOKE TEST COMPLETE")
