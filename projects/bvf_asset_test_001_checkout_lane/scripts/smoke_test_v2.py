"""
A1 Smoke Test v2 — 3-panel board: solo char | char+counter | full scene
"""
import bpy, os, math
from mathutils import Vector

PROJ = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane"
CHARS_GLB = os.path.join(PROJ, "assets", "imported", "kenney_mini-characters", "Models", "GLB format")
MKT_GLB = os.path.join(PROJ, "assets", "imported", "kenney_mini-market", "Models", "GLB format")
OUT = os.path.join(PROJ, "reviews", "asset_smoke")
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 2880
scene.render.resolution_y = 1080
scene.eevee.use_shadows = True

def imp(p):
    bpy.ops.import_scene.gltf(filepath=p)
    return bpy.context.selected_objects

# ── Import all ─────────────────────────────────────────────
char_c = imp(os.path.join(CHARS_GLB, "character-male-a.glb"))  # customer
char_f = imp(os.path.join(CHARS_GLB, "character-female-a.glb"))  # female variant
emp = imp(os.path.join(MKT_GLB, "character-employee.glb"))  # cashier
cr = imp(os.path.join(MKT_GLB, "cash-register.glb"))  # register
bread = imp(os.path.join(MKT_GLB, "display-bread.glb"))
fruit = imp(os.path.join(MKT_GLB, "display-fruit.glb"))
freezer = imp(os.path.join(MKT_GLB, "freezer.glb"))
floor = imp(os.path.join(MKT_GLB, "floor.glb"))

# Move floor to origin
for f in floor:
    f.location = (0, 0, -0.01)
    f.scale = (3, 3, 1)

# ── Panel 1: Solo Character (centered at X=-4.5) ──────────
cx = -4.5
for c in char_c:
    c.location.x += cx
    c.location.y = 0
    c.location.z = 0
# Add ground disc
bpy.ops.mesh.primitive_cylinder_add(radius=0.8, depth=0.02, location=(cx, 0, -0.01))

# ── Panel 2: Character + Counter + Cashier (X=0) ──────────
# Use female character as customer
for c in char_f:
    c.location.x += -0.6
    c.location.y = 0.5
    c.location.z = 0
# Cash register
for c in cr:
    c.location.x += 0.3
    c.location.y = 0.2
    c.location.z = 0
# Employee (behind counter)
for e in emp:
    e.location.x += 0.3
    e.location.y = 0.7
    e.location.z = 0

bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -0.01))
bpy.context.object.scale = (3, 3, 1)

# ── Panel 3: Full Scene (X=4.5) ───────────────────────────
# Another male character
char_m2 = imp(os.path.join(CHARS_GLB, "character-male-b.glb"))
for c in char_m2:
    c.location.x = 3.8
    c.location.y = 0.5
    c.location.z = 0
# Cash register
imp_cr2 = imp(os.path.join(MKT_GLB, "cash-register.glb"))
for c in imp_cr2:
    c.location.x = 4.8
    c.location.y = 0.2
    c.location.z = 0
# Bread display
for b in bread:
    b.location.x = 3.5
    b.location.y = 1.0
    b.location.z = 0
# Fruit display
for f in fruit:
    f.location.x = 5.5
    f.location.y = 1.0
    f.location.z = 0
# Freezer background
for fz in freezer:
    fz.location.x = 4.5
    fz.location.y = 1.8
    fz.location.z = 0

bpy.ops.mesh.primitive_plane_add(size=1, location=(4.5, 0, -0.01))
bpy.context.object.scale = (3, 3, 1)

# ── Lighting ──────────────────────────────────────────────
bpy.ops.object.light_add(type='SUN', location=(5, -5, 8))
bpy.context.object.data.energy = 3.5
bpy.context.object.data.color = (1, 0.96, 0.88)
bpy.context.object.data.angle = 0.12

bpy.ops.object.light_add(type='AREA', location=(-2, -1, 4))
bpy.context.object.data.energy = 2.0
bpy.context.object.data.color = (0.85, 0.88, 1.0)

w = bpy.data.worlds.new("W")
scene.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.35, 0.33, 0.30, 1.0)
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.25

# ── Camera: ortho, full scene view ─────────────────────────
cam_data = bpy.data.cameras.new("Cam")
cam_data.type = 'ORTHO'
cam_obj = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj
cam_obj.location = (0, -4.5, 6)
cam_obj.rotation_euler = (math.radians(52), 0, 0)
cam_data.ortho_scale = 10.0

# ── Render ────────────────────────────────────────────────
out = os.path.join(OUT, "smoke_test_v2.png")
scene.render.filepath = out
bpy.ops.render.render(write_still=True)

# ── Audit Summary ─────────────────────────────────────────
print(f"\nTotal objects: {len(bpy.data.objects)}")
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
verts = sum(len(o.data.vertices) for o in meshes)
mats = len(set(s.material.name for o in meshes for s in o.material_slots if s.material))
print(f"Meshes: {len(meshes)}, Total verts: {verts}, Unique mats: {mats}")
print(f"Character variants tested: male-a, female-a, male-b")
print(f"Counter items: cash-register, display-bread, display-fruit")
print(f"Background: freezer")
print(f"Employee: character-employee")
print(f"Rendered: {out}")
print("SMOKE TEST V2 COMPLETE")
