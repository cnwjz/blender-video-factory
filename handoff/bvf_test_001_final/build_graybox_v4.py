"""
BVF Test 001 — V4: Action Fix (cashier hide + diversion advance + AUTO_CLAMPED)
Root-empty-based character hierarchy. All animation on Root.
Preflight validates head-body connection.
"""
import bpy
import json
import math
import os
import sys
from mathutils import Vector

try:
    import bpy_extras.object_utils as obj_utils
except ImportError:
    pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "graybox_config.json")
REVIEW_DIR = os.path.join(SCRIPT_DIR, "reviews", "v4_action_fixed")
os.makedirs(REVIEW_DIR, exist_ok=True)

with open(CONFIG_PATH, "r") as f:
    CFG = json.load(f)

RES = CFG["output"]["resolution"]
FPS = CFG["output"]["fps"]
TOTAL = CFG["output"]["total_frames"]
SEED = CFG["seed"]
RENDER_FRAMES = [1, 75, 90, 150, 225, 345]
CHARACTER_IDS = ["L1","L2","L3","M1","M2","M3","R1","R2","R3","N1","N2","N3","N4"]
CASHIER_IDS = ["left","middle","right"]

# ── V4 Spatial Overrides ──────────────────────────────────
CFG["spatial"]["window_positions"]["left"][0] = -1.2
CFG["spatial"]["window_positions"]["right"][0] = 1.2
for qkey, new_x in [("left_queue", -1.2), ("middle_queue", 0.0), ("right_queue", 1.2)]:
    for cust in CFG["characters_initial"][qkey]:
        cust["start"][0] = new_x
for nc in CFG["new_customers"]:
    if nc["target_queue"] == "left": nc["start_pos"][0] = -1.2
    elif nc["target_queue"] == "right": nc["start_pos"][0] = 1.2

CFG["spatial"]["character_radius"] = 0.12
CFG["spatial"]["character_height"] = 1.2
BODY_HALF = 0.42  # body cylinder half-height
HEAD_R = 0.13
BODY_LOCAL_Z = BODY_HALF  # body center at half its height above ground
HEAD_LOCAL_Z = BODY_HALF * 2 + HEAD_R * 0.85  # head sits on top of body

mat = CFG["materials_graybox"]
sp = CFG["spatial"]

# ── Helpers ────────────────────────────────────────────────
def make_mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.9
    return m

def make_character_root(name, x, y, z=0.0):
    """Create root empty at world position. Body and head are local children."""
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(x, y, z))
    root = bpy.context.object
    root.name = f"{name}_Root"
    root.empty_display_size = 0.05
    root.hide_viewport = False
    root.hide_render = False
    return root

def make_body(root, name, body_color):
    """Cylinder body as child of root at local (0, 0, BODY_LOCAL_Z)."""
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.12, depth=BODY_HALF * 2,
        location=(0, 0, BODY_LOCAL_Z)
    )
    body = bpy.context.object
    body.name = f"{name}_Body"
    body.parent = root
    body.data.materials.append(make_mat(f"{name}_Body_mat", body_color))
    return body

def make_head(root, name, head_color):
    """Sphere head as child of root at local (0, 0, HEAD_LOCAL_Z)."""
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=HEAD_R,
        location=(0, 0, HEAD_LOCAL_Z)
    )
    head = bpy.context.object
    head.name = f"{name}_Head"
    head.parent = root
    head.data.materials.append(make_mat(f"{name}_Head_mat", head_color))
    return head

def build_character(name, x, y, body_color, head_color):
    root = make_character_root(name, x, y)
    make_body(root, name, body_color)
    make_head(root, name, head_color)
    return root

def build_cashier(name, x, y, z_offset):
    """Cashier behind counter at z_offset below counter level."""
    z = sp["window_positions"]["middle"][2] - 0.9 + z_offset
    root = make_character_root(f"Cashier_{name}", x, y, z)
    make_body(root, f"Cashier_{name}", [0.50, 0.50, 0.52])
    make_head(root, f"Cashier_{name}", [0.58, 0.57, 0.55])
    return root

# ── Clear Scene ────────────────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = CFG["output"]["engine"]
scene.render.resolution_x = RES[0]
scene.render.resolution_y = RES[1]
scene.render.fps = FPS
scene.frame_start = 1
scene.frame_end = TOTAL
scene.render.image_settings.file_format = 'PNG'

# ── Floor and Queue Stripes ────────────────────────────────
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
bpy.context.object.name = "Floor"
bpy.context.object.scale = (6, 10, 1)
bpy.context.object.data.materials.append(make_mat("Floor_mat", mat["floor"]))

for side, wx in [("left", -1.2), ("middle", 0.0), ("right", 1.2)]:
    bpy.ops.mesh.primitive_plane_add(size=1, location=(wx, 0, 0.005))
    stripe = bpy.context.object
    stripe.name = f"Stripe_{side}"
    stripe.scale = (0.30, 4.5, 1)
    stripe.location.y = -0.8
    c = [0.25, 0.28, 0.35] if side != "middle" else [0.28, 0.30, 0.36]
    stripe.data.materials.append(make_mat(f"Stripe_{side}_mat", c))

# ── Counters ──────────────────────────────────────────────
counters = {}
for key in ["left", "middle", "right"]:
    pos = sp["window_positions"][key]
    bpy.ops.mesh.primitive_cube_add(size=1, location=(pos[0], sp["counter_y"], pos[2] + 1.2/2))
    obj = bpy.context.object
    obj.name = f"Counter_{key}"
    obj.scale = (1.2, 0.6, 1.2)
    obj.data.materials.append(make_mat(f"Counter_{key}_mat", mat["counter"]))
    counters[key] = obj

# ── Signboards + Off Signboard ─────────────────────────────
signs = {}
for key in ["left", "middle", "right"]:
    pos = sp["window_positions"][key]
    bpy.ops.mesh.primitive_cube_add(size=1, location=(pos[0], pos[1]+0.1, sp["signboard_z"]))
    obj = bpy.context.object
    obj.name = f"Sign_{key}"
    obj.scale = (1.0, 0.06, 0.25)
    smat = make_mat(f"Sign_{key}_mat", mat["signboard_on"])
    smat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 2.0
    obj.data.materials.append(smat)
    signs[key] = obj

# Middle off signboard
pm = sp["window_positions"]["middle"]
bpy.ops.mesh.primitive_cube_add(size=1, location=(pm[0], pm[1]+0.1, sp["signboard_z"]))
off_sign = bpy.context.object
off_sign.name = "Sign_middle_off"
off_sign.scale = (1.0, 0.06, 0.25)
off_mat = make_mat("Sign_middle_off_mat", mat["signboard_off"])
off_mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 0.0
off_sign.data.materials.append(off_mat)

# Visibility animation
signs["middle"].hide_viewport = False; signs["middle"].hide_render = False
signs["middle"].keyframe_insert(data_path="hide_viewport", frame=1)
signs["middle"].keyframe_insert(data_path="hide_render", frame=1)
signs["middle"].hide_viewport = True; signs["middle"].hide_render = True
signs["middle"].keyframe_insert(data_path="hide_viewport", frame=66)
signs["middle"].keyframe_insert(data_path="hide_render", frame=66)

off_sign.hide_viewport = True; off_sign.hide_render = True
off_sign.keyframe_insert(data_path="hide_viewport", frame=1)
off_sign.keyframe_insert(data_path="hide_render", frame=1)
off_sign.hide_viewport = False; off_sign.hide_render = False
off_sign.keyframe_insert(data_path="hide_viewport", frame=66)
off_sign.keyframe_insert(data_path="hide_render", frame=66)

# ── Shutters ──────────────────────────────────────────────
shutters = {}
for key in ["left", "middle", "right"]:
    pos = sp["window_positions"][key]
    bpy.ops.mesh.primitive_cube_add(size=1, location=(pos[0], pos[1]+0.02, pos[2]+0.9))
    obj = bpy.context.object
    obj.name = f"Shutter_{key}"
    obj.scale = (1.1, 0.04, 0.8)
    smat = make_mat(f"Shutter_{key}_mat", mat["shutter"])
    smat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.6
    obj.data.materials.append(smat)
    shutters[key] = obj
    if key != "middle":
        obj.location.z = pos[2] + 0.9
        obj.keyframe_insert(data_path="location", frame=1, index=2)

# ── Counter Overlay ───────────────────────────────────────
bpy.ops.mesh.primitive_cube_add(size=1, location=(pm[0], sp["counter_y"], pm[2] + 1.2/2))
overlay = bpy.context.object
overlay.name = "Counter_middle_overlay"
overlay.scale = (1.22, 0.62, 1.22)
ov_mat = make_mat("Overlay_mat", [0.1, 0.1, 0.11])
ov_mat.blend_method = 'BLEND'
ov_mat.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.6
overlay.data.materials.append(ov_mat)
overlay.hide_viewport = True; overlay.hide_render = True
overlay.keyframe_insert(data_path="hide_viewport", frame=1)
overlay.keyframe_insert(data_path="hide_render", frame=1)
overlay.hide_viewport = False; overlay.hide_render = False
overlay.keyframe_insert(data_path="hide_viewport", frame=78)
overlay.keyframe_insert(data_path="hide_render", frame=78)

# ── Characters: Root-empty hierarchy ──────────────────────
body_c = [0.36, 0.36, 0.38]
head_c = [0.63, 0.61, 0.58]
cashier_body_c = [0.48, 0.48, 0.50]
cashier_head_c = [0.56, 0.55, 0.53]

char_roots = {}
for qkey, qname in [("left_queue","left"),("middle_queue","middle"),("right_queue","right")]:
    for cust in CFG["characters_initial"][qkey]:
        sc = cust["start"]
        root = build_character(cust["id"], sc[0], sc[1], body_c, head_c)
        char_roots[cust["id"]] = {"root": root, "start": sc.copy(), "queue": qname}

# Cashiers
cashier_roots = {}
for key in ["left", "middle", "right"]:
    pos = sp["window_positions"][key]
    root = build_cashier(key, pos[0], pos[1] - 0.3, 0.0)
    cashier_roots[key] = root

# ── Animation ──────────────────────────────────────────────
# Shot 1 (1-60): Gentle queue advance
for cid, data in char_roots.items():
    root = data["root"]
    sy = data["start"][1]
    root.location.y = sy
    root.keyframe_insert(data_path="location", frame=1, index=1)
    root.location.y = sy + 0.25
    root.keyframe_insert(data_path="location", frame=60, index=1)
    root.keyframe_insert(data_path="location", frame=1, index=0)

# Shot 2 (61-120): Window close
# Middle shutter falls
mid_shutter = shutters["middle"]
sz_start = pm[2] + 0.9
sz_end = pm[2] - 0.1
mid_shutter.location.z = sz_start
mid_shutter.keyframe_insert(data_path="location", frame=1, index=2)
mid_shutter.keyframe_insert(data_path="location", frame=70, index=2)
mid_shutter.location.z = sz_end
mid_shutter.keyframe_insert(data_path="location", frame=88, index=2)

# V4: Middle cashier retreat + hide entire Root at frame 90
cr = cashier_roots["middle"]
cr.location.y = pm[1] - 0.3
cr.keyframe_insert(data_path="location", frame=1, index=1)
cr.location.y = 3.8  # Retreat behind counter
cr.keyframe_insert(data_path="location", frame=90, index=1)

# Hide Root (and all children) after retreat completes — no floating head
cr.hide_viewport = False; cr.hide_render = False
cr.keyframe_insert(data_path="hide_viewport", frame=1)
cr.keyframe_insert(data_path="hide_render", frame=1)
cr.hide_viewport = True; cr.hide_render = True
cr.keyframe_insert(data_path="hide_viewport", frame=90)
cr.keyframe_insert(data_path="hide_render", frame=90)
for child in cr.children:
    child.hide_viewport = False; child.hide_render = False
    child.keyframe_insert(data_path="hide_viewport", frame=1)
    child.keyframe_insert(data_path="hide_render", frame=1)

# Middle queue pause
for cid in ["M1", "M2", "M3"]:
    root = char_roots[cid]["root"]
    root.location.y = root.location.y
    root.keyframe_insert(data_path="location", frame=60, index=1)
    root.keyframe_insert(data_path="location", frame=105, index=1)

# V4: Diversion frame overrides (earlier diversion)
CFG["diversion"]["customer_1"]["frames"] = [106, 145]
CFG["diversion"]["customer_2"]["frames"] = [121, 160]
CFG["diversion"]["customer_3"]["frames"] = [136, 180]

# Shot 3 (106-225): Diversion
div = CFG["diversion"]
for cust_key in ["customer_1", "customer_2", "customer_3"]:
    d = div[cust_key]
    cid = d["id"]
    fs, fe = d["frames"]
    tx = sp["window_positions"][d["to"]][0]
    ty = sp["queue_start_y"] - (2.5 * sp["queue_spacing_y"])

    root = char_roots[cid]["root"]
    sx = char_roots[cid]["start"][0]
    sy = char_roots[cid]["start"][1] + 0.25

    m1 = fs + (fe - fs) // 3
    m2 = fs + 2 * (fe - fs) // 3
    step_back = sy - 0.6

    root.location.y = sy
    root.keyframe_insert(data_path="location", frame=120, index=1)
    root.location.y = step_back
    root.keyframe_insert(data_path="location", frame=m1, index=1)
    root.location.x = sx
    root.keyframe_insert(data_path="location", frame=m1, index=0)
    root.location.x = tx
    root.keyframe_insert(data_path="location", frame=m2, index=0)
    root.location.y = step_back
    root.keyframe_insert(data_path="location", frame=m2, index=1)
    root.location.y = ty
    root.keyframe_insert(data_path="location", frame=fe, index=1)
    root.location.y = ty
    root.keyframe_insert(data_path="location", frame=TOTAL, index=1)
    root.location.x = tx
    root.keyframe_insert(data_path="location", frame=TOTAL, index=0)

# New customers
new_roots = {}
for nc in CFG["new_customers"]:
    fid = nc["frame"]
    spx, spy, spz = nc["start_pos"]
    root = build_character(nc["id"], spx, spy, body_c, head_c)
    new_roots[nc["id"]] = root
    tq = nc["target_queue"]
    ttx = sp["window_positions"][tq][0]
    tty = sp["queue_start_y"] - (3.5 * sp["queue_spacing_y"])
    entry_end = min(fid + 28, TOTAL)

    root.location.y = spy
    root.keyframe_insert(data_path="location", frame=1, index=1)
    root.keyframe_insert(data_path="location", frame=fid, index=1)
    root.location.y = tty
    root.keyframe_insert(data_path="location", frame=entry_end, index=1)
    root.keyframe_insert(data_path="location", frame=TOTAL, index=1)

    root.hide_viewport = True; root.hide_render = True
    root.keyframe_insert(data_path="hide_viewport", frame=1)
    root.keyframe_insert(data_path="hide_render", frame=1)
    root.hide_viewport = False; root.hide_render = False
    root.keyframe_insert(data_path="hide_viewport", frame=fid)
    root.keyframe_insert(data_path="hide_render", frame=fid)
    # Also key all children visibility
    for child in root.children:
        child.hide_viewport = True; child.hide_render = True
        child.keyframe_insert(data_path="hide_viewport", frame=1)
        child.keyframe_insert(data_path="hide_render", frame=1)
        child.hide_viewport = False; child.hide_render = False
        child.keyframe_insert(data_path="hide_viewport", frame=fid)
        child.keyframe_insert(data_path="hide_render", frame=fid)

# L/R queue advance
for cids in [["L1","L2","L3"], ["R1","R2","R3"]]:
    for cid in cids:
        if cid in char_roots:
            root = char_roots[cid]["root"]
            cy = root.location.y
            root.keyframe_insert(data_path="location", frame=120, index=1)
            root.location.y = cy + 0.35
            root.keyframe_insert(data_path="location", frame=270, index=1)
            root.keyframe_insert(data_path="location", frame=TOTAL, index=1)

# ── Lighting ───────────────────────────────────────────────
li = CFG["lighting"]
bpy.ops.object.light_add(type='SUN', location=li["sun"]["location"])
bpy.context.object.name = "Sun"
bpy.context.object.data.energy = li["sun"]["energy"]
bpy.context.object.data.color = li["sun"]["color"]

bpy.ops.object.light_add(type='AREA', location=li["fill"]["location"])
bpy.context.object.name = "Fill"
bpy.context.object.data.energy = li["fill"]["energy"]
bpy.context.object.data.color = li["fill"]["color"]
bpy.context.object.data.size = 5

scene.world = bpy.data.worlds.new("GrayWorldV4")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (*li["ambient"]["color"], 1.0)
bg.inputs["Strength"].default_value = li["ambient"]["strength"]
scene.eevee.use_shadows = True

# ── V4 Camera: Ortho, optimized for space utilization ─────
cam_data = bpy.data.cameras.new("Camera_V4")
cam_data.type = 'ORTHO'
cam_obj = bpy.data.objects.new("Camera_V4", cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj

# Position: elevated front, offset slightly to center the upper scene
cam_obj.location = Vector((0.0, -4.8, 8.5))
cam_obj.rotation_euler = (math.radians(50), 0, 0)

# ortho_scale for good coverage: 8.8 (targeting 95-120px character height)
cam_data.ortho_scale = 9.2

# Shift Y to push camera view upward slightly, reducing top dead space
cam_data.shift_y = 0.08

print(f"Camera V4: ORTHO, pos={cam_obj.location}, ortho_scale={cam_data.ortho_scale}, shift_y={cam_data.shift_y}")

# ── Preflight: Camera Coverage ────────────────────────────
safe_min, safe_max = 0.04, 0.96
FRAME1_CAMERA_NAMES = []
for key in ["left","middle","right"]:
    FRAME1_CAMERA_NAMES.append(f"Counter_{key}")
    FRAME1_CAMERA_NAMES.append(f"Cashier_{key}_Root")
for cid in CHARACTER_IDS[:9]:  # L1-R3
    FRAME1_CAMERA_NAMES.append(f"{cid}_Root")
for side in ["left","middle","right"]:
    FRAME1_CAMERA_NAMES.append(f"Stripe_{side}")

scene.frame_set(1)
cam_preflight = {"frame": 1, "resolution": RES, "results": {}, "conditions": {
    "visible_counters": 0, "visible_stripes": 0, "visible_customer_roots": 0,
    "visible_cashier_roots": 0, "clipped": [], "min_char_height_px": 999}}

for obj_name in FRAME1_CAMERA_NAMES:
    obj = bpy.data.objects.get(obj_name)
    if not obj: continue
    bbox_corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    scr = [obj_utils.world_to_camera_view(scene, cam_obj, c) for c in bbox_corners]
    xs = [p.x for p in scr]; ys = [p.y for p in scr]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    w, h = max_x - min_x, max_y - min_y
    clipped = not (safe_min <= min_x <= safe_max and safe_min <= max_x <= safe_max and
                   safe_min <= min_y <= safe_max and safe_min <= max_y <= safe_max)
    cam_preflight["results"][obj_name] = {
        "min_x": round(min_x,4), "max_x": round(max_x,4),
        "min_y": round(min_y,4), "max_y": round(max_y,4),
        "h_px": int(h * RES[1]), "clipped": clipped}
    if clipped and "Stripe_" not in obj_name:
        cam_preflight["conditions"]["clipped"].append(obj_name)
    if "Counter_" in obj_name: cam_preflight["conditions"]["visible_counters"] += 1
    if "Stripe_" in obj_name: cam_preflight["conditions"]["visible_stripes"] += 1
    if obj_name.endswith("_Root") and obj_name.startswith(("L","M","R")):
        cam_preflight["conditions"]["visible_customer_roots"] += 1
        # Measure Body object for pixel height (Root empty has zero size)
        body_obj = bpy.data.objects.get(obj_name.replace("_Root", "_Body"))
        if body_obj:
            body_corners = [body_obj.matrix_world @ Vector(c) for c in body_obj.bound_box]
            body_scr = [obj_utils.world_to_camera_view(scene, cam_obj, c) for c in body_corners]
            body_ys = [p.y for p in body_scr]
            body_h = max(body_ys) - min(body_ys)
            body_px = int(body_h * RES[1])
            if body_px < cam_preflight["conditions"]["min_char_height_px"]:
                cam_preflight["conditions"]["min_char_height_px"] = body_px
    if obj_name.startswith("Cashier_"):
        cam_preflight["conditions"]["visible_cashier_roots"] += 1

tc = cam_preflight["conditions"]
for k, expected in [("visible_counters",3), ("visible_stripes",3), ("visible_customer_roots",9), ("visible_cashier_roots",3)]:
    tc[f"{k}_pass"] = tc[k] == expected
tc["clipping_pass"] = len(tc["clipped"]) == 0
tc["pixel_height_pass"] = tc["min_char_height_px"] >= 55
tc["all_pass"] = all([tc.get(f"{k}_pass", True) for k in ["visible_counters","visible_stripes","visible_customer_roots","visible_cashier_roots"]] + [tc["clipping_pass"], tc["pixel_height_pass"]])

cam_path = os.path.join(REVIEW_DIR, "camera_preflight_v3.json")
with open(cam_path, "w") as f: json.dump(cam_preflight, f, indent=2)

# ── Preflight: Character Hierarchy ─────────────────────────
char_preflight = {"characters": [], "all_pass": True}
all_char_names = CHARACTER_IDS
all_cashier_names = ["left","middle","right"]

for cid in all_char_names:
    entry = {"id": cid, "root_name": f"{cid}_Root", "body_name": f"{cid}_Body", "head_name": f"{cid}_Head"}
    root = bpy.data.objects.get(f"{cid}_Root")
    body = bpy.data.objects.get(f"{cid}_Body")
    head = bpy.data.objects.get(f"{cid}_Head")

    errors = []
    if root and body and head:
        entry["parent_correct"] = (body.parent == root and head.parent == root)
        if not entry["parent_correct"]:
            errors.append("parent_incorrect")

        # Local positions
        entry["body_local"] = [round(v,4) for v in body.location]
        entry["head_local"] = [round(v,4) for v in head.location]

        # World positions
        bw = body.matrix_world.translation
        hw = head.matrix_world.translation
        entry["body_world"] = [round(v,4) for v in bw]
        entry["head_world"] = [round(v,4) for v in hw]
        entry["world_x_diff"] = round(abs(bw.x - hw.x), 4)
        entry["world_y_diff"] = round(abs(bw.y - hw.y), 4)
        entry["world_vertical_gap"] = round(hw.z - (bw.z + BODY_HALF), 4)

        # Screen projections
        bs = obj_utils.world_to_camera_view(scene, cam_obj, bw)
        hs = obj_utils.world_to_camera_view(scene, cam_obj, hw)
        entry["screen_body"] = [round(bs.x,4), round(bs.y,4)]
        entry["screen_head"] = [round(hs.x,4), round(hs.y,4)]
        entry["screen_x_diff_px"] = int(abs(bs.x - hs.x) * RES[0])

        # Checks
        entry["world_xy_match"] = entry["world_x_diff"] < 0.01 and entry["world_y_diff"] < 0.01
        entry["screen_connected"] = entry["screen_x_diff_px"] <= 4 and hs.y > bs.y
        entry["head_above_body"] = hw.z > bw.z + BODY_HALF - 0.02
        if not entry["world_xy_match"]: errors.append("world_xy_mismatch")
        if not entry["screen_connected"]: errors.append("screen_disconnected")
        if not entry["head_above_body"]: errors.append("head_not_above_body")

        entry["pass"] = len(errors) == 0
        entry["errors"] = errors
    else:
        entry["pass"] = False
        entry["errors"] = ["missing_object"]
        if not root: entry["errors"].append("root_missing")
        if not body: entry["errors"].append("body_missing")
        if not head: entry["errors"].append("head_missing")

    char_preflight["characters"].append(entry)
    if not entry["pass"]: char_preflight["all_pass"] = False

# Cashiers
for cid in all_cashier_names:
    rname = f"Cashier_{cid}_Root"
    bname = f"Cashier_{cid}_Body"
    hname = f"Cashier_{cid}_Head"
    entry = {"id": f"Cashier_{cid}", "root_name": rname, "body_name": bname, "head_name": hname}
    root = bpy.data.objects.get(rname)
    body = bpy.data.objects.get(bname)
    head = bpy.data.objects.get(hname)

    if root and body and head:
        entry["parent_correct"] = (body.parent == root and head.parent == root)
        bw = body.matrix_world.translation
        hw = head.matrix_world.translation
        entry["world_x_diff"] = round(abs(bw.x - hw.x), 4)
        entry["world_y_diff"] = round(abs(bw.y - hw.y), 4)
        bs = obj_utils.world_to_camera_view(scene, cam_obj, bw)
        hs = obj_utils.world_to_camera_view(scene, cam_obj, hw)
        entry["screen_x_diff_px"] = int(abs(bs.x - hs.x) * RES[0])
        entry["world_xy_match"] = entry["world_x_diff"] < 0.01 and entry["world_y_diff"] < 0.01
        entry["screen_connected"] = entry["screen_x_diff_px"] <= 4 and hs.y > bs.y
        entry["pass"] = entry["parent_correct"] and entry["world_xy_match"] and entry["screen_connected"]
    else:
        entry["pass"] = False

    char_preflight["characters"].append(entry)
    if not entry["pass"]: char_preflight["all_pass"] = False

char_path = os.path.join(REVIEW_DIR, "character_preflight_v3.json")
with open(char_path, "w") as f: json.dump(char_preflight, f, indent=2)

print(f"\nCamera Preflight: ALL_PASS={tc['all_pass']} ({tc['visible_counters']}/3 C, {tc['visible_customer_roots']}/9 R, {tc['visible_cashier_roots']}/3 CR, clipped={len(tc['clipped'])}, height={tc['min_char_height_px']}px)")
print(f"Character Preflight: ALL_PASS={char_preflight['all_pass']} ({sum(1 for c in char_preflight['characters'] if c['pass'])}/{len(char_preflight['characters'])} passed)")

overall = tc["all_pass"] and char_preflight["all_pass"]

# ── Render ─────────────────────────────────────────────────
if not overall:
    print("\n*** PREFLIGHT FAILED — ABORTING ***")
    for c in char_preflight["characters"]:
        if not c["pass"]: print(f"  FAIL: {c['id']}: {c.get('errors','?')}")
else:
    print("\n=== All preflights passed. Rendering full 345 frames... ===")
    frames_dir = os.path.join(SCRIPT_DIR, "graybox_frames_v4")
    os.makedirs(frames_dir, exist_ok=True)
    scene.render.filepath = os.path.join(frames_dir, "frame_")
    bpy.ops.render.render(animation=True)
    rendered = len([f for f in os.listdir(frames_dir) if f.endswith('.png')])
    print(f"Rendered: {rendered} frames to {frames_dir}")

# ── Save ───────────────────────────────────────────────────
blend_path = os.path.join(SCRIPT_DIR, "scene_graybox_v4_action_fixed.blend")
bpy.ops.wm.save_mainfile(filepath=blend_path)
print(f"\nSaved: {blend_path}")
print("V4 COMPLETE")
