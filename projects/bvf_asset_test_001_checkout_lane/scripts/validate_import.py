"""
Minimal import validation: 1 char + 1 employee + counter + ground.
FBX format with animation. No stray objects.
"""
import bpy, os, math

PROJ = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane"
CH_FBX = os.path.join(PROJ, "assets", "imported", "kenney_mini-characters", "Models", "FBX format")
MK_FBX = os.path.join(PROJ, "assets", "imported", "kenney_mini-market", "Models", "FBX format")
MK_GLB = os.path.join(PROJ, "assets", "imported", "kenney_mini-market", "Models", "GLB format")
REV = os.path.join(PROJ, "reviews", "UPLOAD_NEXT")
os.makedirs(REV, exist_ok=True)
# Clear UPLOAD_NEXT
for f in os.listdir(REV): os.remove(os.path.join(REV, f))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1080
scene.render.resolution_y = 1080
scene.eevee.use_shadows = True

# ── Import via FBX ────────────────────────────────────────
print("Importing character (FBX)...")
bpy.ops.import_scene.fbx(filepath=os.path.join(CH_FBX, "character-male-a.fbx"))
char_empty = [o for o in bpy.context.selected_objects if o.type == 'EMPTY'][0]
char_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]

# Set idle animation on character
char_arm.animation_data_create()
char_arm.animation_data.action = bpy.data.actions.get("root|idle|Animation Base Layer")
print(f"  Char root: {char_empty.name}")

print("Importing employee (FBX)...")
bpy.ops.import_scene.fbx(filepath=os.path.join(MK_FBX, "character-employee.fbx"))
emp_empty = [o for o in bpy.context.selected_objects if o.type == 'EMPTY'][0]
emp_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE' and o != char_arm][0]

# Set idle animation on employee
emp_arm.animation_data_create()
emp_arm.animation_data.action = bpy.data.actions.get("root|idle|Animation Base Layer")
print(f"  Emp root: {emp_empty.name}")

# Import register (GLB)
bpy.ops.import_scene.gltf(filepath=os.path.join(MK_GLB, "cash-register.glb"))

# ── Counter ────────────────────────────────────────────────
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0.8, 0.7))
ctr = bpy.context.object; ctr.name = "Counter"
ctr.scale = (1.2, 0.35, 0.7)
cm = bpy.data.materials.new("CounterMat")
cm.use_nodes = True
cm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.72, 0.68, 0.60, 1.0)
cm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.5
ctr.data.materials.append(cm)

# ── Floor ──────────────────────────────────────────────────
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -2, -0.01))
flr = bpy.context.object; flr.name = "Floor"; flr.scale = (4, 6, 1)
fm = bpy.data.materials.new("FloorMat")
fm.use_nodes = True
fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.38, 0.35, 0.30, 1.0)
fm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
flr.data.materials.append(fm)

# ── Position ────────────────────────────────────────────────
# Character: standing in front of counter
char_empty.location = (-0.3, -0.1, 0)
# Scale character (Kenney Mini chars are quite small)
char_empty.scale = (1.5, 1.5, 1.5)

# Employee: behind counter
emp_empty.location = (0, 1.1, 0.75)
emp_empty.scale = (1.5, 1.5, 1.5)

# Register on counter
for o in bpy.data.objects:
    if 'cash-register' in o.name.lower() or 'register' in o.name.lower():
        o.location = (0.1, 0.9, 1.42)

# ── Lighting ──────────────────────────────────────────────
bpy.ops.object.light_add(type='SUN', location=(5, -5, 8))
sun = bpy.context.object
sun.data.energy = 3.5; sun.data.angle = 0.12
sun.data.color = (1.0, 0.96, 0.88)

bpy.ops.object.light_add(type='AREA', location=(-2, -1, 4))
fill = bpy.context.object; fill.data.energy = 2.5
fill.data.color = (0.85, 0.88, 1.0); fill.data.size = 3

world = bpy.data.worlds.new("W"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.30,0.28,0.25,1.0)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.25

# ── Camera ────────────────────────────────────────────────
cam_data = bpy.data.cameras.new("Cam"); cam_data.type = 'ORTHO'
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam); scene.camera = cam
cam.location = (0, -3.5, 5.5)
cam.rotation_euler = (math.radians(45), 0, 0)
cam_data.ortho_scale = 5.5

# ── Object Audit ──────────────────────────────────────────
print(f"\nTotal objects: {len(bpy.data.objects)}")
for o in bpy.data.objects:
    children = len(o.children)
    parent = o.parent.name if o.parent else "NONE"
    mesh_info = f"verts={len(o.data.vertices)}" if o.type == 'MESH' else ""
    bone_info = f"bones={len(o.data.bones)}" if o.type == 'ARMATURE' else ""
    print(f"  [{o.type[0]:1s}] {o.name:35s} parent={parent:25s} kids={children} {mesh_info}{bone_info}")

# ── Render ────────────────────────────────────────────────
scene.frame_set(1)  # First frame for static/idle check
out = os.path.join(REV, "character_import_validation.png")
scene.render.filepath = out
bpy.ops.render.render(write_still=True)
print(f"Rendered: {out}")
print("VALIDATION COMPLETE")
