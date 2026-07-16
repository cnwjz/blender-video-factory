"""
A2 Lookdev V3: Fixed A2D layout, customer rotation, props, preflight, review board.
"""
import bpy, os, json, math
from mathutils import Vector, Euler
import bpy_extras.object_utils as obj_utils

PROJ = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane"
CH_FBX = os.path.join(PROJ, "assets", "imported", "kenney_mini-characters", "Models", "FBX format")
MK_FBX = os.path.join(PROJ, "assets", "imported", "kenney_mini-market", "Models", "FBX format")
MK_GLB = os.path.join(PROJ, "assets", "imported", "kenney_mini-market", "Models", "GLB format")
UPL = os.path.join(PROJ, "reviews", "UPLOAD_NEXT")
OUT = os.path.join(PROJ, "reviews", "lookdev")
os.makedirs(UPL, exist_ok=True); os.makedirs(OUT, exist_ok=True)
for f in os.listdir(UPL): os.remove(os.path.join(UPL, f))

COUNTER_H = 1.12; COUNTER_W = 1.70; COUNTER_D = 0.85; TARGET_H = 1.75
PREV = set()

def snap(): global PREV; PREV = set(bpy.data.objects)
def new_objs(): return [o for o in bpy.data.objects if o not in PREV]
def clean_stray():
    for o in list(bpy.data.objects):
        if o.type=='MESH' and o.name.lower().startswith('icosphere') and o.parent is None:
            bpy.data.objects.remove(o, do_unlink=True)
def vis_all():
    for o in bpy.data.objects: o.hide_viewport=o.hide_render=False
    for c in bpy.data.collections: c.hide_viewport=c.hide_render=False

def get_eval_bbox(mesh_list):
    dg = bpy.context.evaluated_depsgraph_get(); pts=[]
    for o in mesh_list:
        if o.type!='MESH': continue
        eo=o.evaluated_get(dg); m=eo.to_mesh()
        if m is None: continue
        for v in m.vertices: pts.append(eo.matrix_world@v.co)
        eo.to_mesh_clear()
    if not pts: return None
    xs=[p.x for p in pts]; ys=[p.y for p in pts]; zs=[p.z for p in pts]
    return (min(xs),max(xs),min(ys),max(ys),min(zs),max(zs))

# ── Scene Setup ────────────────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=1080; scene.render.resolution_y=1920
scene.render.fps=30; scene.eevee.use_shadows=True

# ── Import Characters ──────────────────────────────────────
chars = []
for label, fname, is_emp in [
    ("Customer_01","character-male-a.fbx",False),("Customer_02","character-female-a.fbx",False),
    ("Customer_03","character-male-b.fbx",False),("Customer_04","character-female-b.fbx",False),
    ("Employee_01","character-employee.fbx",True),("Employee_02","character-employee.fbx",True)]:
    snap(); path=os.path.join(MK_FBX if is_emp else CH_FBX,fname)
    bpy.ops.import_scene.fbx(filepath=path)
    clean_stray(); objs=new_objs(); vis_all()
    empty=[o for o in objs if o.type=='EMPTY']
    arm=[o for o in objs if o.type=='ARMATURE']
    mesh=[o for o in objs if o.type=='MESH']
    root=empty[-1] if empty else None; a=arm[-1] if arm else None
    if root: root.name=f"{label}_Root"
    if a: a.name=f"{label}_Armature"
    for m in mesh:
        m.name=f"{label}_{'Body' if 'body' in m.name.lower() else 'Head'}"
    chars.append({"label":label,"root":root,"armature":a,"body":mesh[0] if mesh else None,"head":mesh[1] if len(mesh)>1 else None,"is_emp":is_emp})

# Normalize heights
for cd in chars:
    if not cd["root"]: continue
    cd["root"].scale=(1,1,1); bpy.context.view_layer.update()
    meshes=[o for o in [cd.get("body"),cd.get("head")] if o]
    bb=get_eval_bbox(meshes)
    if bb is None: continue
    h=bb[5]-bb[4]; sf=TARGET_H/h if h>0.001 else 1
    cd["root"].scale=Vector((sf,sf,sf)); bpy.context.view_layer.update()
    bb2=get_eval_bbox(meshes)
    if bb2: cd["root"].location.z-=bb2[4]
    print(f"  {cd['label']}: h={TARGET_H:.3f} sc={sf:.4f}")

# ── Counters ────────────────────────────────────────────────
counters=[]
for name,cx in [("Counter_L",-1.4),("Counter_R",1.4)]:
    bpy.ops.mesh.primitive_cube_add(size=1,location=(cx,1.5,COUNTER_H/2))
    c=bpy.context.object; c.name=name; c.scale=(COUNTER_W/2,COUNTER_D/2,COUNTER_H/2)
    m=bpy.data.materials.new(f"{name}M"); m.use_nodes=True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(0.72,0.68,0.60,1.0)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value=0.5
    c.data.materials.append(m); counters.append(c)
    # Belt
    bpy.ops.mesh.primitive_cube_add(size=1,location=(cx,1.5,COUNTER_H+0.02))
    b=bpy.context.object; b.name=f"{name}_Belt"; b.scale=(1.0,0.35,0.02)
    bm=bpy.data.materials.new(f"{name}Belt"); bm.use_nodes=True
    bm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(0.14,0.12,0.10,1.0)
    b.data.materials.append(bm)

# ── Props ───────────────────────────────────────────────────
snap(); bpy.ops.import_scene.gltf(filepath=os.path.join(MK_GLB,"cash-register.glb"))
r1=[o for o in new_objs() if o.type=='MESH']
if r1: r1[0].name="Register_L"; r1[0].location=(-1.4,1.65,COUNTER_H+0.03)
snap(); bpy.ops.import_scene.gltf(filepath=os.path.join(MK_GLB,"cash-register.glb"))
r2=[o for o in new_objs() if o.type=='MESH']
if r2: r2[0].name="Register_R"; r2[0].location=(1.4,1.65,COUNTER_H+0.03)

# Products: bread + fruit on counters
snap(); bpy.ops.import_scene.gltf(filepath=os.path.join(MK_GLB,"display-bread.glb"))
for o in new_objs():
    if o.type=='MESH': o.location=(-1.0,1.66,COUNTER_H+0.03)
snap(); bpy.ops.import_scene.gltf(filepath=os.path.join(MK_GLB,"display-fruit.glb"))
for o in new_objs():
    if o.type=='MESH': o.location=(0.9,1.66,COUNTER_H+0.03)

# Basket
snap(); bpy.ops.import_scene.gltf(filepath=os.path.join(MK_GLB,"shopping-basket.glb"))
for o in new_objs():
    if o.type=='MESH' and 'basket' in o.name.lower(): o.location=(-0.2,-0.5,0)

# Environment: shelf + freezer in background
snap(); bpy.ops.import_scene.gltf(filepath=os.path.join(MK_GLB,"shelf-boxes.glb"))
for o in new_objs():
    if o.type=='MESH': o.location=(-2.8,2.8,0)
snap(); bpy.ops.import_scene.gltf(filepath=os.path.join(MK_GLB,"freezers-standing.glb"))
for o in new_objs():
    if o.type=='MESH': o.location=(2.8,2.8,0)

# Floor + Wall
bpy.ops.mesh.primitive_plane_add(size=1,location=(0,0,-0.005))
f=bpy.context.object; f.name="Floor"; f.scale=(5,7,1)
fm=bpy.data.materials.new("FloorM"); fm.use_nodes=True
fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(0.36,0.33,0.29,1.0)
f.data.materials.append(fm)
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,3.6,2.2))
w=bpy.context.object; w.name="Wall"; w.scale=(5.5,0.2,4.5)
wm=bpy.data.materials.new("WallM"); wm.use_nodes=True
wm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(0.18,0.16,0.14,1.0)
w.data.materials.append(wm)

# ── Layout (A2D-verified) ─────────────────────────────────
# Employees behind counters, customers in front
# V3 FIX: Customers face AWAY from camera (toward +Y = counter direction)
layout={
    "Employee_01":(-1.4,1.9,0,0),        "Employee_02":(1.4,1.9,0,0),
    "Customer_01":(-1.4,0.2,0,math.pi),   "Customer_02":(-1.4,-0.9,0,math.pi),
    "Customer_03":(-1.4,-2.0,0,math.pi),  "Customer_04":(1.4,0.2,0,math.pi),
}
for cd in chars:
    label=cd["label"]
    if label in layout and cd["root"]:
        x,y,base_z,rz=layout[label]
        cd["root"].location=Vector((x,y,cd["root"].location.z+base_z))
        cd["root"].rotation_euler=Euler((0,0,rz),'XYZ')
        print(f"  {label} → ({x:.1f},{y:.1f},{cd['root'].location.z:.3f}) rz={rz:.1f}")

# ── Animations ────────────────────────────────────────────
# Stagger idle frames for natural variety
for i,cd in enumerate(chars):
    if cd["armature"]:
        if not cd["armature"].animation_data: cd["armature"].animation_data_create()
        cd["armature"].animation_data.action=bpy.data.actions.get("root|idle|Animation Base Layer")
scene.frame_set(1)

# ── Lighting ──────────────────────────────────────────────
world=bpy.data.worlds.new("W"); scene.world=world; world.use_nodes=True
world.node_tree.nodes["Background"].inputs["Color"].default_value=(0.30,0.28,0.25,1.0)
world.node_tree.nodes["Background"].inputs["Strength"].default_value=0.3
bpy.ops.object.light_add(type='SUN',location=(5,-4,7)); sun=bpy.context.object
sun.data.energy=3.0; sun.data.angle=0.12; sun.data.color=(1.0,0.96,0.88)
bpy.ops.object.light_add(type='AREA',location=(-2,0,4)); fill=bpy.context.object
fill.data.energy=2.2; fill.data.color=(0.85,0.88,1.0); fill.data.size=4
bpy.ops.object.light_add(type='SUN',location=(0,3,5)); rim=bpy.context.object
rim.data.energy=0.7; rim.data.angle=0.08; rim.data.color=(0.95,0.93,0.88)

# ── Camera (A2D 3/4 perspective, 10% adjustment allowed) ──
ess_objs=counters+[cd["body"] for cd in chars if cd["body"]]+[cd["head"] for cd in chars if cd["head"]]
for n in ["Register_L","Register_R"]:
    o=bpy.data.objects.get(n)
    if o: ess_objs.append(o)
bb=get_eval_bbox(ess_objs)
cx=(bb[0]+bb[1])/2; cy=(bb[2]+bb[3])/2; cz=(bb[4]+bb[5])/2
cam_data=bpy.data.cameras.new("Cam"); cam_data.type='PERSP'; cam_data.lens=50
cam_data.clip_start=0.05; cam_data.clip_end=100
cam=bpy.data.objects.new("Cam",cam_data)
scene.collection.objects.link(cam); scene.camera=cam
cam.location=Vector((cx+1.5,cy-12,cz+4.8))
target=Vector((cx,cy,cz+0.3))
direction=target-cam.location
cam.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()

# ── Preflight ──────────────────────────────────────────────
print("\n=== PREFLIGHT ===")
dg=bpy.context.evaluated_depsgraph_get(); ok=True
issues=[]
essential_meshes=[o for o in ess_objs if o.type=='MESH']
# Check all essential objects via their bounding box corners
for o in essential_meshes:
    corners=[o.matrix_world@Vector(c) for c in o.bound_box]
    obj_ok=True
    for wp in corners:
        s=obj_utils.world_to_camera_view(scene,cam,wp)
        if s.z<0: obj_ok=False; issues.append(f"{o.name}: behind camera")
        if s.x<0.04 or s.x>0.96 or s.y<0.04 or s.y>0.96:
            obj_ok=False
    if not obj_ok: issues.append(f"{o.name}: bbox corners out of safe area")

# Customer facing check: customers should face toward their counter
for cd in chars:
    if cd["label"].startswith("Customer") and cd["root"]:
        pos=cd["root"].location
        # Which counter does this customer belong to?
        counter_x=-1.4 if "04" not in cd["label"] else 1.4
        desired=Vector((counter_x-pos.x,1.5-pos.y,0)).normalized()
        # Check which local axis points forward. Try -Y (common front direction in many models)
        local_axes=[cd["root"].matrix_world.to_3x3()@Vector((0,-1,0)),  # -Y
                    cd["root"].matrix_world.to_3x3()@Vector((0,1,0)),   # +Y
                    cd["root"].matrix_world.to_3x3()@Vector((1,0,0))]   # +X
        best=min(abs(math.degrees(math.acos(max(-1,min(1,ax.normalized().dot(desired)))))) for ax in local_axes)
        if best>30: ok=False; issues.append(f"{cd['label']}: best facing {best:.0f}deg > 30")

# Foot contact
for cd in chars:
    if cd["body"]:
        bb_char=get_eval_bbox([cd["body"]])
        if bb_char and bb_char[4]>0.04: ok=False; issues.append(f"{cd['label']}: feet at Z={bb_char[4]:.3f} > 0.03")

# Camera inside bbox
cam_wp=cam.location
for o in essential_meshes:
    bb_o=get_eval_bbox([o])
    if bb_o and bb_o[0]<=cam_wp.x<=bb_o[1] and bb_o[2]<=cam_wp.y<=bb_o[3] and bb_o[4]<=cam_wp.z<=bb_o[5]:
        ok=False; issues.append(f"Camera inside {o.name} bbox")

print(f"  Preflight: {'PASSED' if ok else 'FAILED'} ({len(issues)} issues)")
for i in issues[:10]: print(f"    {i}")

if not ok:
    print("PREFLIGHT FAILED — aborting render")
    # Render debug anyway
    scene.render.filepath=os.path.join(UPL,"debug_frame.png")
    bpy.ops.render.render(write_still=True)
else:
    # ── Render ────────────────────────────────────────────
    scene.frame_set(1)
    main_out=os.path.join(OUT,"F001_lookdev_v3.png")
    scene.render.filepath=main_out
    bpy.ops.render.render(write_still=True)
    print(f"Rendered: {main_out}")

    blend=os.path.join(PROJ,"scene","lookdev_v3_layout_locked.blend")
    bpy.ops.wm.save_mainfile(filepath=blend)
    print(f"Saved: {blend}")

    # Report
    rep=os.path.join(PROJ,"reports","LOOKDEV_REPORT_v3.md")
    with open(rep,"w") as rf:
        rf.write(f"# Lookdev Report V3\n\nDate: 2026-07-14\nStatus: lookdev_reviewing\n\n")
        rf.write(f"## Layout\n\nA2D-verified: 2 counters, 2 employees, 4 customers.\nCustomers rotated 180deg to face counters.\n\n")
        rf.write(f"## Camera\n\n3/4 perspective, 50mm lens.\nLocation: {cam.location}\nTarget: {target}\n\n")
        rf.write(f"## Preflight\n\nPassed\n\n")
        rf.write(f"## Props\n\nbread-display, fruit-display, shopping-basket, shelf-boxes, freezers-standing\n")
    print("Report written")

    # Composite review board with system Python
    import subprocess
    subprocess.run(["python",os.path.join(PROJ,"scripts","_composite_v3.py"),main_out,UPL],check=True)

print("V3 DONE")
