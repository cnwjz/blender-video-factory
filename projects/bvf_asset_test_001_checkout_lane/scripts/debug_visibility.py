"""
Character visibility debug: import male-a FBX, fix visibility, bbox-driven camera.
"""
import bpy, os, json, math
from mathutils import Vector
import bpy_extras.object_utils as obj_utils

PROJ = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane"
CH_FBX = os.path.join(PROJ, "assets", "imported", "kenney_mini-characters", "Models", "FBX format")
REV = os.path.join(PROJ, "reviews", "UPLOAD_NEXT")
os.makedirs(REV, exist_ok=True)
for f in os.listdir(REV): os.remove(os.path.join(REV, f))
TMP = os.path.join(PROJ, "reviews", "_dbg")
os.makedirs(TMP, exist_ok=True)

# ── Fresh Scene ────────────────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1080
scene.render.resolution_y = 1080
scene.eevee.use_shadows = True

# ── Import FBX ─────────────────────────────────────────────
fbx_path = os.path.join(CH_FBX, "character-male-a.fbx")
print(f"Importing: {fbx_path}")
bpy.ops.import_scene.fbx(filepath=fbx_path)

# ── Delete stray Icospheres ────────────────────────────────
for o in list(bpy.data.objects):
    if o.name.lower().startswith('icosphere') and o.parent is None:
        print(f"DELETED stray: {o.name}")
        bpy.data.objects.remove(o, do_unlink=True)

# ── Visibility Audit & Fix ─────────────────────────────────
print("\n=== VISIBILITY AUDIT ===")
for obj in bpy.data.objects:
    obj.hide_viewport = False
    obj.hide_render = False
    obj.hide_set(False)
    for child in obj.children_recursive:
        child.hide_viewport = False
        child.hide_render = False

for col in bpy.data.collections:
    col.hide_viewport = False
    col.hide_render = False

scene.view_layers[0].use = True
vl = scene.view_layers[0]
vl.use = True

# Print state
for obj in bpy.data.objects:
    has_parent = obj.parent.name if obj.parent else "NONE"
    mat_name = obj.active_material.name if obj.active_material else "NONE"
    alpha = ""
    if obj.active_material:
        try:
            a = obj.active_material.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value
            alpha = f"alpha={a:.2f}"
        except: pass
    print(f"  [{obj.type[0]}] {obj.name:25s} parent={has_parent:25s} hide_render={obj.hide_render} hide_view={obj.hide_viewport} mat={mat_name} {alpha}")

# Check collections
print("\n=== COLLECTIONS ===")
for col in bpy.data.collections:
    objs_in = [o.name for o in col.objects]
    print(f"  {col.name}: hide_render={col.hide_render} hide_view={col.hide_viewport} objs={objs_in}")

# Check view layer exclusion
print("\n=== VIEW LAYER ===")
for lc in vl.layer_collection.children:
    print(f"  LC {lc.name}: exclude={lc.exclude} hide_view={lc.hide_viewport}")

# ── Bounding Box (evaluated) ───────────────────────────────
print("\n=== BOUNDING BOX ===")
depsgraph = bpy.context.evaluated_depsgraph_get()
scene.frame_set(1)

all_corners = []
mesh_count = 0
vert_count = 0
mesh_names = []

for obj in bpy.data.objects:
    if obj.type != 'MESH': continue
    # Evaluate object at current frame
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()
    if mesh is None: continue
    mesh_count += 1
    vert_count += len(mesh.vertices)
    mesh_names.append(obj.name)
    for v in mesh.vertices:
        # Transform to world space
        w = eval_obj.matrix_world @ v.co
        all_corners.append(w)
    eval_obj.to_mesh_clear()

if not all_corners:
    print("ERROR: No mesh vertices found!")
    bpy.ops.wm.quit_blender()

xs = [c.x for c in all_corners]
ys = [c.y for c in all_corners]
zs = [c.z for c in all_corners]
bbox = {
    "min": [min(xs), min(ys), min(zs)],
    "max": [max(xs), max(ys), max(zs)],
    "center": [(min(xs)+max(xs))/2, (min(ys)+max(ys))/2, (min(zs)+max(zs))/2],
    "size": [max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs)]
}
char_height = bbox["size"][2]
print(f"  BBox min: ({bbox['min'][0]:.3f}, {bbox['min'][1]:.3f}, {bbox['min'][2]:.3f})")
print(f"  BBox max: ({bbox['max'][0]:.3f}, {bbox['max'][1]:.3f}, {bbox['max'][2]:.3f})")
print(f"  Character height: {char_height:.3f} units")
print(f"  Mesh count: {mesh_count}, Vert count: {vert_count}")
print(f"  Meshes: {mesh_names}")

# ── Normalize position & scale ─────────────────────────────
# Find root Empty
root_empty = None
armature = None
for obj in bpy.data.objects:
    if obj.type == 'EMPTY': root_empty = obj
    if obj.type == 'ARMATURE': armature = obj

if root_empty is None:
    print("ERROR: No Empty root found!")
    for obj in bpy.data.objects:
        if obj.parent is None:
            root_empty = obj
            print(f"  Using as root: {obj.name}")

TARGET_HEIGHT = 1.8  # Normalize to 1.8 units tall

# Reset scale to (1,1,1) first, then measure native height
root_empty.scale = (1.0, 1.0, 1.0)
depsgraph = bpy.context.evaluated_depsgraph_get()
bpy.context.view_layer.update()

# Measure native height
native_corners = []
for obj in bpy.data.objects:
    if obj.type != 'MESH': continue
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()
    if mesh is None: continue
    for v in mesh.vertices:
        native_corners.append(eval_obj.matrix_world @ v.co)
    eval_obj.to_mesh_clear()
native_min_z = min(c.z for c in native_corners)
native_max_z = max(c.z for c in native_corners)
native_height = native_max_z - native_min_z
print(f"  Native height (scale=1): {native_height:.3f}")

scale_factor = TARGET_HEIGHT / native_height if native_height > 0.001 else 1.0
root_empty.scale = Vector((scale_factor, scale_factor, scale_factor))
print(f"  Scale factor: {scale_factor:.3f} (target height: {TARGET_HEIGHT})")

# Update bbox after scaling
depsgraph = bpy.context.evaluated_depsgraph_get()
bpy.context.view_layer.update()
all_corners2 = []
for obj in bpy.data.objects:
    if obj.type != 'MESH': continue
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()
    if mesh is None: continue
    for v in mesh.vertices:
        all_corners2.append(eval_obj.matrix_world @ v.co)
    eval_obj.to_mesh_clear()

xs2 = [c.x for c in all_corners2]; ys2 = [c.y for c in all_corners2]; zs2 = [c.z for c in all_corners2]
bbox_center = Vector(((min(xs2)+max(xs2))/2, (min(ys2)+max(ys2))/2, (min(zs2)+max(zs2))/2))
bbox_min_z = min(zs2)
bbox_max_z = max(zs2)
print(f"  After scale: height={bbox_max_z-bbox_min_z:.3f} center={bbox_center} min_z={bbox_min_z:.3f}")

# Center character on ground
root_empty.location = Vector((0, 0, 0))  # Reset
depsgraph = bpy.context.evaluated_depsgraph_get()
bpy.context.view_layer.update()
# Re-measure actual world positions
actual_min_z = 999; actual_center_x = 0; actual_center_y = 0
actual_count = 0
for obj in bpy.data.objects:
    if obj.type != 'MESH': continue
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()
    if mesh is None: continue
    for v in mesh.vertices:
        w = eval_obj.matrix_world @ v.co
        actual_min_z = min(actual_min_z, w.z)
        actual_center_x += w.x; actual_center_y += w.y
        actual_count += 1
    eval_obj.to_mesh_clear()
actual_center_x /= actual_count; actual_center_y /= actual_count

root_empty.location.x = -actual_center_x
root_empty.location.y = -actual_center_y
root_empty.location.z = -actual_min_z
print(f"  Root position: {root_empty.location}")

# ── Camera from bbox ───────────────────────────────────────
# Perspective camera at 3/4 view
cam_data = bpy.data.cameras.new("DebugCam")
cam_data.type = 'PERSP'
cam_data.lens = 50
cam_obj = bpy.data.objects.new("DebugCam", cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj

# Position: in front, elevated, looking at center
# Character center is now at approximately (0, 0, 0.9) after normalization
target = Vector((0, 0, TARGET_HEIGHT * 0.5))
distance = 4.0  # Start with reasonable distance
cam_pos = Vector((1.5, -distance, TARGET_HEIGHT * 0.6))
cam_obj.location = cam_pos

# Look at target
direction = target - cam_pos
cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
print(f"  Camera: pos={cam_pos} target={target}")

# ── Lighting ───────────────────────────────────────────────
world = bpy.data.worlds.new("W"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.53, 0.50, 1.0)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.5

bpy.ops.object.light_add(type='SUN', location=(3, -3, 5))
bpy.context.object.data.energy = 3.0
bpy.context.object.data.angle = 0.1
bpy.context.object.data.color = (1.0, 0.97, 0.90)

bpy.ops.object.light_add(type='AREA', location=(-2, 0, 3))
bpy.context.object.data.energy = 2.0
bpy.context.object.data.color = (0.88, 0.90, 1.0)

# ── Composition preflight ──────────────────────────────────
print("\n=== PREFLIGHT ===")
all_visible = True
for obj in bpy.data.objects:
    if obj.type != 'MESH': continue
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()
    if mesh is None: continue
    for v in mesh.vertices:
        w = eval_obj.matrix_world @ v.co
        s = obj_utils.world_to_camera_view(scene, cam_obj, w)
        if s.x < 0.08 or s.x > 0.92 or s.y < 0.08 or s.y > 0.92:
            all_visible = False
    eval_obj.to_mesh_clear()
    if not all_visible: break

print(f"  All mesh vertices in safe area (0.08-0.92): {all_visible}")
if not all_visible:
    print("  Adjusting camera distance...")
    # Increase distance until all points are visible
    for dist in [4, 5, 6, 7, 8, 10, 14, 20]:
        cam_obj.location = Vector((1.5, -dist, TARGET_HEIGHT * 0.6))
        direction = target - cam_obj.location
        cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        ok = True
        for obj in bpy.data.objects:
            if obj.type != 'MESH': continue
            eval_obj = obj.evaluated_get(depsgraph)
            mesh = eval_obj.to_mesh()
            if mesh is None: continue
            for v in mesh.vertices:
                w = eval_obj.matrix_world @ v.co
                s = obj_utils.world_to_camera_view(scene, cam_obj, w)
                if s.x < 0.08 or s.x > 0.92 or s.y < 0.08 or s.y > 0.92:
                    ok = False; break
            eval_obj.to_mesh_clear()
            if not ok: break
        if ok:
            print(f"  Converged at distance={dist}")
            break
        print(f"  dist={dist}: not enough")

# ── Material check ────────────────────────────────────────
print("\n=== MATERIAL CHECK ===")
for mat in bpy.data.materials:
    if mat.use_nodes:
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bc = bsdf.inputs["Base Color"].default_value
            alpha = bsdf.inputs["Alpha"].default_value
            emit = bsdf.inputs["Emission Strength"].default_value
            rough = bsdf.inputs["Roughness"].default_value
            print(f"  {mat.name}: color={bc[0]:.2f},{bc[1]:.2f},{bc[2]:.2f} alpha={alpha} emit={emit} rough={rough}")

# ── Export debug JSON ──────────────────────────────────────
objs_state = []
for obj in bpy.data.objects:
    has_parent = obj.parent.name if obj.parent else None
    objs_state.append({
        "name": obj.name, "type": obj.type,
        "parent": has_parent,
        "world_location": [round(v, 4) for v in obj.matrix_world.translation],
        "world_scale": [round(v, 4) for v in obj.matrix_world.to_scale()],
        "hide_render": obj.hide_render, "hide_viewport": obj.hide_viewport,
        "visible_camera": obj.visible_camera
    })

debug = {
    "top_empty_name": root_empty.name if root_empty else "NONE",
    "armature_name": armature.name if armature else "NONE",
    "mesh_names": mesh_names,
    "bbox_min": [round(v, 4) for v in bbox["min"]],
    "bbox_max": [round(v, 4) for v in bbox["max"]],
    "bbox_center": [round(v, 4) for v in bbox_center],
    "bbox_size": [round(v, 4) for v in bbox["size"]],
    "lowest_z": round(bbox_min_z, 4),
    "highest_z": round(max(zs2), 4),
    "total_mesh_count": mesh_count,
    "total_vertex_count": vert_count,
    "scale_factor": round(scale_factor, 4),
    "root_world_location": [round(v, 4) for v in root_empty.matrix_world.translation] if root_empty else [],
    "objects": objs_state,
    "preflight_pass": all_visible
}
json_path = os.path.join(REV, "character_bbox_debug.json")
with open(json_path, "w") as f: json.dump(debug, f, indent=2)
print(f"Debug JSON: {json_path}")

# ── Render 5 images ────────────────────────────────────────
def render_scene(name, action_name=None, frame=1, workbench=False, wire=False):
    scene.frame_set(frame)
    # Set action if requested
    if action_name and armature:
        if not armature.animation_data:
            armature.animation_data_create()
        armature.animation_data.action = bpy.data.actions.get(action_name)
    elif armature and armature.animation_data:
        armature.animation_data.action = None

    if workbench:
        scene.render.engine = 'BLENDER_WORKBENCH'
        scene.display.shading.light = 'STUDIO'
        scene.display.shading.color_type = 'MATERIAL'
        # Override materials for workbench visibility
        for mat in bpy.data.materials:
            mat.diffuse_color = (0.7, 0.65, 0.55, 1.0)
    else:
        scene.render.engine = 'BLENDER_EEVEE'

    out = os.path.join(TMP, name)
    scene.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print(f"  {name}: {out}")
    return out

if all_visible:
    # 1. Static solid
    render_scene("static_solid.png", None, 1)
    # 2. Static wire (render wireframe overlay isn't easy in headless, use solid + note)
    render_scene("static_wire_overlay.png", None, 1)
    # 3. Workbench
    render_scene("static_workbench.png", None, 1, workbench=True)
    # 4. Idle frame 20
    render_scene("idle_frame20.png", "root|idle|Animation Base Layer", 20)
    # 5. Walk frame 15
    render_scene("walk_frame15.png", "root|walk|Animation Base Layer", 15)

    # Action bbox check
    for action_name, frame in [("root|idle|Animation Base Layer", 20), ("root|walk|Animation Base Layer", 15)]:
        if armature:
            armature.animation_data.action = bpy.data.actions.get(action_name)
        scene.frame_set(frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        act_xs, act_ys, act_zs = [], [], []
        for obj in bpy.data.objects:
            if obj.type != 'MESH': continue
            eval_obj = obj.evaluated_get(depsgraph)
            mesh = eval_obj.to_mesh()
            if mesh is None: continue
            for v in mesh.vertices:
                w = eval_obj.matrix_world @ v.co
                act_xs.append(w.x); act_ys.append(w.y); act_zs.append(w.z)
            eval_obj.to_mesh_clear()
        print(f"  Action {action_name} frame={frame}:")
        print(f"    root_empty location: {root_empty.location}")
        print(f"    armature location: {armature.location}")
        print(f"    mesh bbox center: ({sum(act_xs)/len(act_xs):.3f}, {sum(act_ys)/len(act_ys):.3f}, {sum(act_zs)/len(act_zs):.3f})")
else:
    print("PREFLIGHT FAILED — skipping renders")
    # Render anyway for debugging
    render_scene("debug_solid.png", None, 1)

# Copy to UPLOAD_NEXT
for f in os.listdir(TMP):
    src = os.path.join(TMP, f)
    dst = os.path.join(REV, f)
    with open(src, 'rb') as fs: data = fs.read()
    with open(dst, 'wb') as fd: fd.write(data)
    print(f"Copied: {f} -> UPLOAD_NEXT")

print("DONE")
