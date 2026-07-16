"""
BVF Test 001 — Phase 4D: Final style test - cashier fix, rim light, orange shutter
"""
import bpy, json, math, os
from mathutils import Vector
import bpy_extras.object_utils as obj_utils

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "graybox_config.json")
REVIEW_DIR = os.path.join(SCRIPT_DIR, "reviews", "style_v4")
os.makedirs(REVIEW_DIR, exist_ok=True)

with open(CONFIG_PATH) as f: CFG = json.load(f)

RES = (1080, 1920)
FPS = CFG["output"]["fps"]
TOTAL = CFG["output"]["total_frames"]
sp = CFG["spatial"]

# V4 spatial + diversion overrides
sp["window_positions"]["left"][0] = -1.2; sp["window_positions"]["right"][0] = 1.2
for qk, nx in [("left_queue",-1.2),("middle_queue",0.0),("right_queue",1.2)]:
    for c in CFG["characters_initial"][qk]: c["start"][0] = nx
for nc in CFG["new_customers"]:
    if nc["target_queue"]=="left": nc["start_pos"][0] = -1.2
    elif nc["target_queue"]=="right": nc["start_pos"][0] = 1.2
CFG["diversion"]["customer_1"]["frames"] = [106,145]
CFG["diversion"]["customer_2"]["frames"] = [121,160]
CFG["diversion"]["customer_3"]["frames"] = [136,180]

ST = {
    "wall": (0.16, 0.14, 0.12), "floor": (0.22, 0.20, 0.18),
    "counter": (0.83, 0.78, 0.72), "counter_edge": (0.73, 0.68, 0.62),
    "conveyor": (0.18, 0.16, 0.14), "scanner": (0.35, 0.33, 0.30),
    "sign_on": (0.96, 0.90, 0.82), "sign_off": (0.10, 0.09, 0.09),
    # V3: Warm orange ONLY for middle shutter. Left/right shutters stay invisible/normal.
    "shutter_orange": (0.92, 0.42, 0.13),
    "shelf": (0.28, 0.25, 0.22), "shelf_support": (0.20, 0.18, 0.16),
    "char_skin": (0.75, 0.68, 0.60),
    "char_clothes": [(0.55,0.48,0.40),(0.42,0.37,0.32),(0.48,0.43,0.37),
                     (0.55,0.50,0.44),(0.60,0.52,0.44)],
    "cashier_top": (0.62, 0.58, 0.52), "cashier_bottom": (0.32, 0.30, 0.28),
    "product_box": (0.65, 0.58, 0.48), "product_bottle": (0.62, 0.55, 0.47),
}

def mat_new(name, rgb, rough=0.85, emit=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    n = m.node_tree.nodes
    bsdf = n["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb,1.0)
    bsdf.inputs["Roughness"].default_value = rough
    if emit>0:
        bsdf.inputs["Emission Strength"].default_value = emit
        bsdf.inputs["Emission Color"].default_value = (*rgb,1.0)
    if alpha<1.0: m.blend_method='BLEND'; bsdf.inputs["Alpha"].default_value=alpha
    return m

# ── Geometry builders ─────────────────────────────────────
def lowpoly_character(root, name, skin_col, cloth_col, is_cashier=False):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.14, location=(0,0,1.02))
    head = bpy.context.object; head.name=f"{name}_Head"; head.parent=root
    head.data.materials.append(mat_new(f"{name}_skin", skin_col, 0.65))
    head.scale=(1.0,0.92,1.05); bpy.ops.object.shade_smooth()

    bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,0.68))
    torso=bpy.context.object; torso.name=f"{name}_Torso"; torso.parent=root
    torso.scale=(0.14,0.10,0.20)
    cloth=ST["cashier_top"] if is_cashier else cloth_col
    torso.data.materials.append(mat_new(f"{name}_cloth", cloth, 0.75))

    if is_cashier:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,0.62))
        apron=bpy.context.object; apron.name=f"{name}_Apron"; apron.parent=root
        apron.scale=(0.15,0.11,0.12)
        apron.data.materials.append(mat_new(f"{name}_apron", ST["cashier_bottom"], 0.7))

    for side,sx in [("L",-0.045),("R",0.045)]:
        bpy.ops.mesh.primitive_cylinder_add(radius=0.038, depth=0.40, location=(sx,0,0.28))
        leg=bpy.context.object; leg.name=f"{name}_Leg{side}"; leg.parent=root
        leg.data.materials.append(mat_new(f"{name}_leg",(0.22,0.20,0.18),0.85))

    for side,sx in [("L",-0.17),("R",0.17)]:
        bpy.ops.mesh.primitive_cylinder_add(radius=0.026, depth=0.28, location=(sx,0,0.65))
        arm=bpy.context.object; arm.name=f"{name}_Arm{side}"; arm.parent=root
        arm.rotation_euler=(0.25,0,0.1*(1 if side=="R" else -1))
        arm.data.materials.append(mat_new(f"{name}_arm", skin_col, 0.65))

def build_lowpoly_char(name, x, y, cloth_idx, is_cashier):
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(x,y,0))
    root=bpy.context.object; root.name=f"{name}_Root"; root.empty_display_size=0.05
    lowpoly_character(root, name, ST["char_skin"], ST["char_clothes"][cloth_idx%5], is_cashier)
    return root

def build_cashier(name, x, y, z_off=0.0):
    cz = sp["window_positions"]["middle"][2]+z_off  # V4: Cashier at counter-top height (head visible above)
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(x,y,cz))
    root=bpy.context.object; root.name=f"Cashier_{name}_Root"; root.empty_display_size=0.05
    lowpoly_character(root, f"Cashier_{name}", ST["char_skin"], ST["cashier_top"], True)
    return root

def styled_counter(name, x, y, z):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, z+1.1/2))
    ctr = bpy.context.object; ctr.name=name
    ctr.scale=(1.05,0.48,1.1); ctr.data.materials.append(mat_new(f"{name}_mat", ST["counter"],0.6))
    bm=ctr.modifiers.new("Bevel",'BEVEL');bm.width=0.025;bm.segments=2

    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y-0.01, z+1.1+0.025))
    belt=bpy.context.object; belt.name=f"{name}_Belt"
    belt.scale=(0.80,0.40,0.035); belt.data.materials.append(mat_new(f"{name}_belt", ST["conveyor"],0.4))

    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y+0.12, z+1.1+0.06))
    scan=bpy.context.object; scan.name=f"{name}_Scanner"
    scan.scale=(0.14,0.10,0.07); scan.data.materials.append(mat_new(f"{name}_scan", ST["scanner"],0.35))

    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y+0.12, z+1.1+0.10))
    ind=bpy.context.object; ind.name=f"{name}_ScanTop"
    ind.scale=(0.06,0.04,0.015)
    ind.data.materials.append(mat_new(f"{name}_ind",(0.45,0.42,0.38),0.3))
    return ctr

def add_product(x, y, z, w, d, h, color):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, z+h/2))
    prod=bpy.context.object; prod.name=f"Product_{x:.1f}_{y:.1f}"
    prod.scale=(w,d,h); prod.data.materials.append(mat_new(f"Prod_{x:.1f}",color,0.6))
    return prod

def styled_signboard(name, x, y, z, is_on=True):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y+0.05, z))
    obj=bpy.context.object; obj.name=name; obj.scale=(0.85,0.04,0.2)
    c = ST["sign_on"] if is_on else ST["sign_off"]
    e = 2.5 if is_on else 0.0
    obj.data.materials.append(mat_new(f"{name}_mat", c, 0.5, e))
    return obj

def styled_shutter(name, x, y, z, is_middle=False):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y+0.01, z+0.7))
    obj=bpy.context.object; obj.name=name
    # V4: Thicker, taller shutter for better visibility
    obj.scale=(0.95,0.05,0.75)
    color = ST["shutter_orange"] if is_middle else (0.25,0.23,0.20)
    obj.data.materials.append(mat_new(f"{name}_mat", color, 0.35))
    return obj

def make_floor():
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0,-0.5,0))
    obj=bpy.context.object; obj.name="Floor"; obj.scale=(5,8,1)
    obj.data.materials.append(mat_new("Floor_mat", ST["floor"], 0.95))
    for col_x in [-1.2, 0.0, 1.2]:
        bpy.ops.mesh.primitive_plane_add(size=1, location=(col_x, -0.5, 0.003))
        z=bpy.context.object; z.name=f"QueueZone_{col_x:.0f}"
        z.scale=(0.32,4.5,1); z.data.materials.append(mat_new(f"QZ_{col_x:.0f}",(0.26,0.24,0.22),0.9))

def make_wall():
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0,4.5,2.2))
    obj=bpy.context.object; obj.name="Wall"; obj.scale=(5.5,0.2,4.5)
    obj.data.materials.append(mat_new("Wall_mat", ST["wall"], 0.9))

def make_shelf_group(x, y, z):
    for hz in [z+0.3, z+0.9]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, hz))
        s=bpy.context.object; s.name=f"Shelf_{x:.0f}_{hz:.0f}"
        s.scale=(0.7,0.12,0.03); s.data.materials.append(mat_new("Shelf_mat", ST["shelf"], 0.7))
    for sx in [x-0.6, x+0.6]:
        bpy.ops.mesh.primitive_cylinder_add(radius=0.02, depth=1.2, location=(sx, y, z+0.6))
        sp=bpy.context.object; sp.name=f"ShelfSupport_{sx:.0f}"
        sp.data.materials.append(mat_new("ShelfSup_mat", ST["shelf_support"], 0.8))

# ── Clear Scene ────────────────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=RES[0]; scene.render.resolution_y=RES[1]
scene.render.fps=FPS; scene.frame_start=1; scene.frame_end=TOTAL
scene.render.image_settings.file_format='PNG'

# ── Environment ────────────────────────────────────────────
make_floor(); make_wall()
make_shelf_group(-3.2, 4.3, 0); make_shelf_group(3.2, 4.3, 0)

# ── Counters, Signboards, Shutters ─────────────────────────
counters={}; signs={}; shutters={}
pm=sp["window_positions"]["middle"]
for key in ["left","middle","right"]:
    pos=sp["window_positions"][key]
    counters[key]=styled_counter(f"Counter_{key}", pos[0], sp["counter_y"], pos[2])
    signs[key]=styled_signboard(f"Sign_{key}", pos[0], pos[1], sp["signboard_z"], True)
    shutters[key]=styled_shutter(f"Shutter_{key}", pos[0], pos[1], pos[2], key=="middle")
    if key!="middle":
        shutters[key].location.z=pos[2]+0.9
        shutters[key].keyframe_insert(data_path="location", frame=1, index=2)

# Products on left/right conveyors
for key, wx in [("left",-1.2),("right",1.2)]:
    bz = sp["window_positions"][key][2]+1.1+0.03
    by = sp["counter_y"]
    # 2 boxes + 1 bottle on left, 1 box + 1 bottle on right
    if key=="left":
        add_product(wx-0.25, by+0.05, bz, 0.08, 0.06, 0.06, ST["product_box"])
        add_product(wx, by+0.08, bz, 0.07, 0.06, 0.05, ST["product_box"])
        add_product(wx+0.25, by+0.03, bz, 0.03, 0.03, 0.10, ST["product_bottle"])
    else:
        add_product(wx-0.22, by+0.05, bz, 0.08, 0.06, 0.06, ST["product_box"])
        add_product(wx+0.18, by+0.06, bz, 0.03, 0.03, 0.09, ST["product_bottle"])
    # Left/right counter colors: warm gray-beige (no orange)
    counters[key].data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(0.80,0.76,0.70,1.0)

# Off signboard (middle)
off_sign=styled_signboard("Sign_middle_off", pm[0], pm[1], sp["signboard_z"], False)
off_sign.hide_viewport=True; off_sign.hide_render=True
off_sign.keyframe_insert(data_path="hide_viewport", frame=1)
off_sign.keyframe_insert(data_path="hide_render", frame=1)
off_sign.hide_viewport=False; off_sign.hide_render=False
off_sign.keyframe_insert(data_path="hide_viewport", frame=66)
off_sign.keyframe_insert(data_path="hide_render", frame=66)

signs["middle"].hide_viewport=False; signs["middle"].hide_render=False
signs["middle"].keyframe_insert(data_path="hide_viewport", frame=1)
signs["middle"].keyframe_insert(data_path="hide_render", frame=1)
signs["middle"].hide_viewport=True; signs["middle"].hide_render=True
signs["middle"].keyframe_insert(data_path="hide_viewport", frame=66)
signs["middle"].keyframe_insert(data_path="hide_render", frame=66)

# Counter overlay
bpy.ops.mesh.primitive_cube_add(size=1, location=(pm[0], sp["counter_y"], pm[2]+1.1/2))
overlay=bpy.context.object; overlay.name="Counter_middle_overlay"
overlay.scale=(1.07,0.50,1.12)
om=mat_new("Overlay_mat",(0.06,0.05,0.04),0.9,0,0.65)
overlay.data.materials.append(om)
overlay.hide_viewport=True; overlay.hide_render=True
overlay.keyframe_insert(data_path="hide_viewport", frame=1)
overlay.keyframe_insert(data_path="hide_render", frame=1)
overlay.hide_viewport=False; overlay.hide_render=False
overlay.keyframe_insert(data_path="hide_viewport", frame=78)
overlay.keyframe_insert(data_path="hide_render", frame=78)

# ── Characters ─────────────────────────────────────────────
char_roots={}
for qkey in ["left_queue","middle_queue","right_queue"]:
    for i,cust in enumerate(CFG["characters_initial"][qkey]):
        sc=cust["start"]
        ci=hash(cust["id"])%5
        root=build_lowpoly_char(cust["id"], sc[0], sc[1], ci, False)
        char_roots[cust["id"]]={"root":root,"start":sc.copy(),"queue":qkey.split("_")[0]}

cashier_roots={}
for key in ["left","middle","right"]:
    pos=sp["window_positions"][key]
    root=build_cashier(key, pos[0], pos[1]-0.3, 0.0)
    cashier_roots[key]=root

# ── Animation (IDENTICAL to V4) ────────────────────────────
for cid,data in char_roots.items():
    root=data["root"]; sy=data["start"][1]
    root.location.y=sy; root.keyframe_insert(data_path="location", frame=1, index=1)
    root.location.y=sy+0.25; root.keyframe_insert(data_path="location", frame=60, index=1)
    root.keyframe_insert(data_path="location", frame=1, index=0)

ms=shutters["middle"]
sz_s,sz_e=pm[2]+0.9,pm[2]-0.1
ms.location.z=sz_s; ms.keyframe_insert(data_path="location", frame=1, index=2)
ms.keyframe_insert(data_path="location", frame=70, index=2)
ms.location.z=sz_e; ms.keyframe_insert(data_path="location", frame=88, index=2)

cr=cashier_roots["middle"]
cr.location.y=pm[1]-0.3; cr.keyframe_insert(data_path="location", frame=1, index=1)
cr.location.y=3.8; cr.keyframe_insert(data_path="location", frame=90, index=1)
cr.hide_viewport=False; cr.hide_render=False
cr.keyframe_insert(data_path="hide_viewport", frame=1)
cr.keyframe_insert(data_path="hide_render", frame=1)
cr.hide_viewport=True; cr.hide_render=True
cr.keyframe_insert(data_path="hide_viewport", frame=90)
cr.keyframe_insert(data_path="hide_render", frame=90)
for child in cr.children:
    child.hide_viewport=False; child.hide_render=False
    child.keyframe_insert(data_path="hide_viewport", frame=1)
    child.keyframe_insert(data_path="hide_render", frame=1)

for cid in ["M1","M2","M3"]:
    root=char_roots[cid]["root"]
    root.keyframe_insert(data_path="location", frame=60, index=1)
    root.keyframe_insert(data_path="location", frame=105, index=1)

div=CFG["diversion"]
for ck in ["customer_1","customer_2","customer_3"]:
    d=div[ck]; cid=d["id"]; fs,fe=d["frames"]
    tx=sp["window_positions"][d["to"]][0]; ty=sp["queue_start_y"]-(2.5*sp["queue_spacing_y"])
    root=char_roots[cid]["root"]
    sx=char_roots[cid]["start"][0]; sy=char_roots[cid]["start"][1]+0.25
    m1=fs+(fe-fs)//3; m2=fs+2*(fe-fs)//3; sb=sy-0.6
    root.location.y=sy; root.keyframe_insert(data_path="location", frame=120, index=1)
    root.location.y=sb; root.keyframe_insert(data_path="location", frame=m1, index=1)
    root.location.x=sx; root.keyframe_insert(data_path="location", frame=m1, index=0)
    root.location.x=tx; root.keyframe_insert(data_path="location", frame=m2, index=0)
    root.location.y=sb; root.keyframe_insert(data_path="location", frame=m2, index=1)
    root.location.y=ty; root.keyframe_insert(data_path="location", frame=fe, index=1)
    root.location.y=ty; root.keyframe_insert(data_path="location", frame=TOTAL, index=1)
    root.location.x=tx; root.keyframe_insert(data_path="location", frame=TOTAL, index=0)

new_roots={}
for nc in CFG["new_customers"]:
    fid=nc["frame"]; spx,spy,spz=nc["start_pos"]
    ci=hash(nc["id"])%5
    root=build_lowpoly_char(nc["id"], spx, spy, ci, False)
    new_roots[nc["id"]]=root
    ttx=sp["window_positions"][nc["target_queue"]][0]; tty=sp["queue_start_y"]-(3.5*sp["queue_spacing_y"])
    ee=min(fid+28,TOTAL)
    root.location.y=spy; root.keyframe_insert(data_path="location", frame=1, index=1)
    root.keyframe_insert(data_path="location", frame=fid, index=1)
    root.location.y=tty; root.keyframe_insert(data_path="location", frame=ee, index=1)
    root.keyframe_insert(data_path="location", frame=TOTAL, index=1)
    root.hide_viewport=True; root.hide_render=True
    root.keyframe_insert(data_path="hide_viewport", frame=1)
    root.keyframe_insert(data_path="hide_render", frame=1)
    root.hide_viewport=False; root.hide_render=False
    root.keyframe_insert(data_path="hide_viewport", frame=fid)
    root.keyframe_insert(data_path="hide_render", frame=fid)
    for child in root.children:
        child.hide_viewport=True; child.hide_render=True
        child.keyframe_insert(data_path="hide_viewport", frame=1)
        child.keyframe_insert(data_path="hide_render", frame=1)
        child.hide_viewport=False; child.hide_render=False
        child.keyframe_insert(data_path="hide_viewport", frame=fid)
        child.keyframe_insert(data_path="hide_render", frame=fid)

for cids in [["L1","L2","L3"],["R1","R2","R3"]]:
    for cid in cids:
        if cid in char_roots:
            root=char_roots[cid]["root"]; cy=root.location.y
            root.keyframe_insert(data_path="location", frame=120, index=1)
            root.location.y=cy+0.35; root.keyframe_insert(data_path="location", frame=270, index=1)
            root.keyframe_insert(data_path="location", frame=TOTAL, index=1)

# ── Lighting ───────────────────────────────────────────────
w=scene.world=bpy.data.worlds.new("StyleWorld")
w.use_nodes=True
w.node_tree.nodes["Background"].inputs["Color"].default_value=(0.25,0.22,0.20,1.0)
w.node_tree.nodes["Background"].inputs["Strength"].default_value=0.15

bpy.ops.object.light_add(type='SUN', location=(4,-4,7))
sun=bpy.context.object; sun.name="Sun"; sun.data.energy=2.8
sun.data.color=(1.0,0.95,0.88); sun.data.angle=0.15

bpy.ops.object.light_add(type='AREA', location=(-2,-1,3))
fill=bpy.context.object; fill.name="Fill"; fill.data.energy=1.5
fill.data.color=(0.85,0.85,0.90); fill.data.size=4

scene.eevee.use_shadows=True

# V4: Rim/contour light for character-ground separation
bpy.ops.object.light_add(type='SUN', location=(0,2,6))
rim=bpy.context.object; rim.name="Rim"; rim.data.energy=1.0
rim.data.color=(0.95,0.92,0.88); rim.data.angle=0.1

# ── V3: BBOX-DRIVEN CAMERA ────────────────────────────────
# Essential object name patterns for bounding box
ESSENTIAL_PATTERNS = ["Counter_","Sign_","Cashier_","_Root","_Body","_Head","_Torso","_Leg","_Arm","_Apron","Product_","Shutter_"]
def is_essential(obj_name):
    return any(p in obj_name for p in ESSENTIAL_PATTERNS)

def get_bbox_at_frame(frame, cam_obj):
    """Get screen-space bounding box of all essential objects (include off-screen)."""
    scene.frame_set(frame)
    all_xs,all_ys=[],[]
    for obj in bpy.data.objects:
        if not is_essential(obj.name): continue
        if obj.hide_viewport or obj.hide_render: continue
        corners=[obj.matrix_world @ Vector(c) for c in obj.bound_box]
        for corner in corners:
            p=obj_utils.world_to_camera_view(scene, cam_obj, corner)
            all_xs.append(p.x); all_ys.append(p.y)
    if not all_xs: return None
    return (min(all_xs),max(all_xs),min(all_ys),max(all_ys))

# Set up camera first with initial guess for preflight
cam_data=bpy.data.cameras.new("Cam_Style"); cam_data.type='ORTHO'
cam=bpy.data.objects.new("Cam_Style", cam_data)
scene.collection.objects.link(cam); scene.camera=cam

# Camera: ortho with manual optimization via preflight
cam.location=Vector((0,-4.8,8.5))
cam.rotation_euler=(math.radians(50),0,0)

# Manual tuning: scan ortho_scale and shift_y combinations
best=(None,None,999)
for ortho_try in [x/10 for x in range(65,100,2)]:  # 6.5-9.9
    for shift_try in [x/100 for x in range(-30,31,4)]:  # -0.30..0.30
        cam_data.ortho_scale=ortho_try
        cam_data.shift_y=shift_try
        score=0
        valid=True
        for frame in [1,150,345]:
            bb=get_bbox_at_frame(frame, cam)
            if not bb: valid=False; break
            ux_min,ux_max,uy_min,uy_max=bb
            top_empty=1-uy_max; bot_margin=uy_min
            left_margin=ux_min; right_margin=1-ux_max
            if left_margin<0.05 or right_margin<0.05 or top_empty<0.02: valid=False
            # Target: top_empty 0.10-0.16, bot_margin >=0.06
            te_score=0 if 0.10<=top_empty<=0.16 else min(abs(top_empty-0.10),abs(top_empty-0.16))*15
            bm_score=max(0,0.06-bot_margin)*25
            score+=te_score+bm_score
        if valid and score<best[2]:
            best=(ortho_try,shift_try,score)

cam_data.ortho_scale=best[0]; cam_data.shift_y=best[1]
print(f"Camera optimized: ortho={cam_data.ortho_scale:.2f} shift_y={cam_data.shift_y:.2f} score={best[2]:.3f}")

# ── Cross-frame Preflight ──────────────────────────────────
preflight={"frames":{}, "all_pass":True}
for frame in [1,90,150,345]:
    scene.frame_set(frame)
    xs,ys,clipped=[],[],[]
    for obj in bpy.data.objects:
        if not is_essential(obj.name): continue
        if obj.hide_viewport or obj.hide_render: continue
        corners=[obj.matrix_world @ Vector(c) for c in obj.bound_box]
        scr=[obj_utils.world_to_camera_view(scene, cam, c) for c in corners]
        any_visible=any(0<=p.x<=1 and 0<=p.y<=1 for p in scr)
        if not any_visible: continue
        in_bounds=all(0.05<=p.x<=0.95 and 0.06<=p.y<=0.94 for p in scr)
        if not in_bounds: clipped.append(obj.name)
        for p in scr:
            if 0<=p.x<=1 and 0<=p.y<=1: xs.append(p.x); ys.append(p.y)

    if xs:
        ex_min,ex_max=min(xs),max(xs)
        ey_min,ey_max=min(ys),max(ys)
        top_empty=1-ey_max; bot_margin=ey_min
        left_margin=ex_min; right_margin=1-ex_max
        fpass=(top_empty<=0.16 and ey_max<=0.94 and left_margin>=0.05
               and right_margin>=0.05 and len(clipped)==0)
    else:
        fpass=False; ex_min=ex_max=ey_min=ey_max=top_empty=bot_margin=left_margin=right_margin=0

    preflight["frames"][f"F{frame:03d}"]={
        "top_empty":round(top_empty,4),"bot_margin":round(bot_margin,4),
        "left_margin":round(left_margin,4),"right_margin":round(right_margin,4),
        "bbox":[round(ex_min,4),round(ex_max,4),round(ey_min,4),round(ey_max,4)],
        "clipped":clipped,"pass":fpass}
    if not fpass: preflight["all_pass"]=False
    print(f"  F{frame}: top={top_empty:.3f} bot={bot_margin:.3f} left={left_margin:.3f} right={right_margin:.3f} clipped={len(clipped)} {'PASS' if fpass else 'FAIL'}")

preflight_path=os.path.join(REVIEW_DIR,"composition_preflight_v4.json")
with open(preflight_path,"w") as f: json.dump(preflight,f,indent=2)
print(f"Preflight all_pass={preflight['all_pass']}")

if not preflight["all_pass"]:
    for fk,fd in preflight["frames"].items():
        if not fd["pass"]: print(f"  FAIL {fk}: {fd['clipped'][:5]}")
    print("ABORTING - preflight failed")
else:
    # ── Render ────────────────────────────────────────────
    for frame, label in [(1,"F001 Normal"),(90,"F090 Closed"),(150,"F150 Diversion"),(345,"F345 Congestion")]:
        scene.frame_set(frame)
        out=os.path.join(REVIEW_DIR,f"F{frame:03d}_style_v4.png")
        scene.render.filepath=out
        bpy.ops.render.render(write_still=True)
        print(f"  {label}: {out}")

    blend_path=os.path.join(SCRIPT_DIR,"scene_style_v4.blend")
    bpy.ops.wm.save_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")
    print("STYLE V3 COMPLETE")
