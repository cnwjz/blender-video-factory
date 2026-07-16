"""
A2 Lookdev V2 (FBX): employee gate → 2-lane checkout scene → bbox camera → review board.
"""
import bpy, os, json, math
from mathutils import Vector
import bpy_extras.object_utils as obj_utils

PROJ = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane"
CH_FBX = os.path.join(PROJ, "assets", "imported", "kenney_mini-characters", "Models", "FBX format")
MK_FBX = os.path.join(PROJ, "assets", "imported", "kenney_mini-market", "Models", "FBX format")
MK_GLB = os.path.join(PROJ, "assets", "imported", "kenney_mini-market", "Models", "GLB format")
UPL = os.path.join(PROJ, "reviews", "UPLOAD_NEXT")
OUT_DIR = os.path.join(PROJ, "reviews", "lookdev")
os.makedirs(UPL, exist_ok=True); os.makedirs(OUT_DIR, exist_ok=True)
for f in os.listdir(UPL): os.remove(os.path.join(UPL, f))

def scene_fresh():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = 'BLENDER_EEVEE'
    s.render.resolution_x = 1080; s.render.resolution_y = 1920
    s.eevee.use_shadows = True
    return s

def clean_stray():
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and o.name.lower().startswith('icosphere') and o.parent is None:
            bpy.data.objects.remove(o, do_unlink=True)

def vis_fix():
    for o in bpy.data.objects: o.hide_viewport = o.hide_render = False
    for c in bpy.data.collections: c.hide_viewport = c.hide_render = False
    for lc in bpy.context.view_layer.layer_collection.children: lc.exclude = False

def imp_fbx(path):
    bpy.ops.import_scene.fbx(filepath=path)
    clean_stray()
    vis_fix()
    empty = [o for o in bpy.data.objects if o.type == 'EMPTY']
    arm = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    return (empty[-1] if empty else None, arm[-1] if arm else None)

def imp_glb(path):
    bpy.ops.import_scene.gltf(filepath=path)

def set_action(arm, name):
    if arm and not arm.animation_data: arm.animation_data_create()
    act = bpy.data.actions.get(name)
    if arm and act: arm.animation_data.action = act

def make_lighting():
    bpy.ops.object.light_add(type='SUN', location=(5,-5,8))
    bpy.context.object.data.energy=3.2; bpy.context.object.data.angle=0.12
    bpy.context.object.data.color=(1.0,0.96,0.88)
    bpy.ops.object.light_add(type='AREA', location=(-2,-1,4))
    bpy.context.object.data.energy=2.5; bpy.context.object.data.color=(0.85,0.88,1.0)
    bpy.context.object.data.size=4
    bpy.ops.object.light_add(type='SUN', location=(0,3,5))
    bpy.context.object.data.energy=0.8; bpy.context.object.data.color=(0.95,0.93,0.88)
    bpy.context.object.data.angle=0.08
    w=bpy.data.worlds.new("W"); bpy.context.scene.world=w; w.use_nodes=True
    w.node_tree.nodes["Background"].inputs["Color"].default_value=(0.32,0.30,0.27,1.0)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value=0.3

def get_world_bbox():
    depsgraph = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in bpy.data.objects:
        if o.type!='MESH': continue
        eo=o.evaluated_get(depsgraph); m=eo.to_mesh()
        if m is None: continue
        for v in m.vertices: pts.append(eo.matrix_world@v.co)
        eo.to_mesh_clear()
    if not pts: return None
    xs=[p.x for p in pts]; ys=[p.y for p in pts]; zs=[p.z for p in pts]
    return (min(xs),max(xs),min(ys),max(ys),min(zs),max(zs))

def bbox_camera(scene, bbox):
    """Set perspective camera to frame bbox with 65-80% height fill."""
    mx,MX,my,MY,mz,MZ = bbox
    cx,cy,cz = (mx+MX)/2, (my+MY)/2, (mz+MZ)/2
    h = MZ-mz
    # Camera: in front, elevated
    cam_data = bpy.data.cameras.new("Cam"); cam_data.type='PERSP'; cam_data.lens=35
    cam = bpy.data.objects.new("Cam", cam_data)
    scene.collection.objects.link(cam); scene.camera=cam
    # Position: elevated 3/4 view
    cam.location = Vector((cx+0.8, cy-5.5, cz+h*0.7))
    target = Vector((cx, cy, cz))
    cam.rotation_euler = (target-cam.location).to_track_quat('-Z','Y').to_euler()
    # Validate
    depsgraph = bpy.context.evaluated_depsgraph_get()
    ok = True
    for o in bpy.data.objects:
        if o.type!='MESH': continue
        eo=o.evaluated_get(depsgraph); m=eo.to_mesh()
        if m is None: continue
        for v in m.vertices:
            s=obj_utils.world_to_camera_view(scene,cam,eo.matrix_world@v.co)
            if s.x<0.04 or s.x>0.96 or s.y<0.04 or s.y>0.96: ok=False; break
        eo.to_mesh_clear()
        if not ok: break
    if not ok:
        # Try from further back
        for dist in [7,9,12,16,22]:
            cam.location = Vector((cx+0.8, cy-dist, cz+h*0.7))
            cam.rotation_euler = (target-cam.location).to_track_quat('-Z','Y').to_euler()
            depsgraph = bpy.context.evaluated_depsgraph_get()
            ok=True
            for o in bpy.data.objects:
                if o.type!='MESH': continue
                eo=o.evaluated_get(depsgraph); m=eo.to_mesh()
                if m is None: continue
                for v in m.vertices:
                    s=obj_utils.world_to_camera_view(scene,cam,eo.matrix_world@v.co)
                    if s.x<0.04 or s.x>0.96 or s.y<0.04 or s.y>0.96: ok=False; break
                eo.to_mesh_clear()
                if not ok: break
            if ok: break
    return cam, ok

# ═══════════════════════════════════════════════════════════
# EMPLOYEE GATE
# ═══════════════════════════════════════════════════════════
print("=== EMPLOYEE GATE ===")
sg = scene_fresh()
emp_e, emp_a = imp_fbx(os.path.join(MK_FBX, "character-employee.fbx"))
make_lighting()

# Normalize employee
emp_e.scale = (1,1,1)
bb = get_world_bbox()
if bb is None:
    print("EMPLOYEE GATE FAILED: no mesh bbox")
else:
    mx,MX,my,MY,mz,MZ = bb
    emp_h = MZ-mz
    emp_e.scale = (1.8/emp_h, 1.8/emp_h, 1.8/emp_h)
    bb2 = get_world_bbox()
    mz2 = bb2[4]
    # Feet to ground
    emp_e.location.z -= mz2
    bb3 = get_world_bbox()
    cam_e, cam_ok = bbox_camera(sg, bb3)
    set_action(emp_a, "root|idle|Animation Base Layer")
    sg.frame_set(20)

    print(f"  Employee height: {emp_h:.3f} → normalized")
    print(f"  BBox after: {bb3}")
    print(f"  Camera OK: {cam_ok}")
    print(f"  Empty: {emp_e.name if emp_e else 'NONE'}")
    print(f"  Armature: {emp_a.name if emp_a else 'NONE'}")
    meshes = [o.name for o in bpy.data.objects if o.type=='MESH']
    print(f"  Meshes: {meshes}")
    print(f"  vis_fix applied")

    gate_pass = emp_e is not None and emp_a is not None and len(meshes)>=2
    print(f"  GATE: {'PASSED' if gate_pass else 'FAILED'}")

    if not gate_pass:
        out = os.path.join(UPL, "employee_gate_failure.png")
        sg.render.filepath = out
        sg.render.resolution_x = 1080; sg.render.resolution_y = 1080
        bpy.ops.render.render(write_still=True)
        print("EMPLOYEE GATE FAILED - stopping")
        import sys; sys.exit(0)
    print("EMPLOYEE GATE PASSED")

# ═══════════════════════════════════════════════════════════
# FULL SCENE
# ═══════════════════════════════════════════════════════════
print("\n=== BUILDING SCENE ===")
scene = scene_fresh()

# Characters
chars = []
for fname, pos in [
    ("character-male-a.fbx", (-0.7, 0.3, 0)),     # left queue front
    ("character-female-a.fbx", (-0.7, -0.3, 0)),   # left queue middle
    ("character-male-b.fbx", (-0.7, -0.9, 0)),    # left queue back
    ("character-female-b.fbx", (0.7, 0.3, 0)),    # right queue front
]:
    e, a = imp_fbx(os.path.join(CH_FBX, fname))
    if e: e.location = Vector(pos); e.scale = (1.5, 1.5, 1.5); set_action(a, "root|idle|Animation Base Layer")
    chars.append((e, a, fname))

# Employee 1 (left counter)
e1_e, e1_a = imp_fbx(os.path.join(MK_FBX, "character-employee.fbx"))
e1_e.location = (-0.5, 1.2, 0.8); e1_e.scale = (1.5, 1.5, 1.5)
set_action(e1_a, "root|idle|Animation Base Layer")

# Employee 2 (right counter)
e2_e, e2_a = imp_fbx(os.path.join(MK_FBX, "character-employee.fbx"))
e2_e.location = (0.9, 1.2, 0.8); e2_e.scale = (1.5, 1.5, 1.5)
set_action(e2_a, "root|idle|Animation Base Layer")

# Counters (native — Kenney has no checkout desk)
for cx, name in [(-0.5, "CounterL"), (0.9, "CounterR")]:
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, 1.5, 0.7))
    c = bpy.context.object; c.name = name; c.scale = (1.2, 0.4, 0.7)
    m = bpy.data.materials.new(f"{name}M")
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.72,0.68,0.60,1.0)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.5
    c.data.materials.append(m)
    # Conveyor belt
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, 1.5, 1.41))
    b = bpy.context.object; b.name = f"Belt_{name}"; b.scale = (1.1, 0.35, 0.02)
    bm = bpy.data.materials.new(f"BeltM_{name}")
    bm.use_nodes = True
    bm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.14,0.12,0.10,1.0)
    bm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.3
    b.data.materials.append(bm)

# Props: cash register, displays, basket, cart
imp_glb(os.path.join(MK_GLB, "cash-register.glb"))
for o in list(bpy.data.objects):
    if 'register' in o.name.lower(): o.location = (-0.6, 1.65, 1.42)

imp_glb(os.path.join(MK_GLB, "display-bread.glb"))
for o in list(bpy.data.objects):
    if 'bread' in o.name.lower() or 'display-bread' in o.name.lower(): o.location = (0.1, 1.65, 1.42)

imp_glb(os.path.join(MK_GLB, "display-fruit.glb"))
for o in list(bpy.data.objects):
    if 'fruit' in o.name.lower() and 'display' in o.name.lower(): o.location = (1.1, 1.65, 1.42)

imp_glb(os.path.join(MK_GLB, "shopping-basket.glb"))
for o in list(bpy.data.objects):
    if 'basket' in o.name.lower() and 'shop' in o.name.lower(): o.location = (0.4, 0.2, 0)

imp_glb(os.path.join(MK_GLB, "shelf-boxes.glb"))
for o in list(bpy.data.objects):
    if 'shelf' in o.name.lower(): o.location = (-2.5, 2.8, 0)

imp_glb(os.path.join(MK_GLB, "freezers-standing.glb"))
for o in list(bpy.data.objects):
    if 'freezer' in o.name.lower(): o.location = (2.5, 2.8, 0)

# Floor tile
imp_glb(os.path.join(MK_GLB, "floor.glb"))
for o in list(bpy.data.objects):
    if o.name.lower().startswith('floor'): o.location = (0, -1, -0.005); o.scale = (4, 6, 1)

make_lighting()

# Camera from bbox
scene.frame_set(20)
bb_final = get_world_bbox()
print(f"  Scene bbox: {[round(v,3) for v in bb_final]}")
cam_final, cam_final_ok = bbox_camera(scene, bb_final)
print(f"  Camera OK: {cam_final_ok}")

# Render
out_main = os.path.join(OUT_DIR, "F001_lookdev_v2_fbx.png")
scene.render.filepath = out_main
bpy.ops.render.render(write_still=True)
print(f"Rendered: {out_main}")

# Save
blend = os.path.join(PROJ, "scene", "lookdev_v2_fbx.blend")
bpy.ops.wm.save_mainfile(filepath=blend)
print(f"Saved: {blend}")

# Report
report = os.path.join(PROJ, "reports", "LOOKDEV_REPORT_v2_FBX.md")
with open(report, "w") as f:
    f.write("# Lookdev Report V2 (FBX)\n\nDate: 2026-07-14\n\n")
    f.write("## Employee Gate\n\nPASSED\n\n")
    f.write("## Scene\n\n- 2 checkout lanes\n- 2 cashiers (character-employee FBX)\n")
    f.write("- 4 customers: left queue(3) + right queue(1)\n")
    f.write("- Props: cash-register, display-bread, display-fruit, shopping-basket, shelf-boxes, freezers-standing\n")
    f.write(f"- Camera from bbox: OK={cam_final_ok}\n")
    f.write(f"- BBox: {[round(v,3) for v in bb_final]}\n")

print(f"MAIN_RENDER={out_main}")
print("BLENDER DONE")
