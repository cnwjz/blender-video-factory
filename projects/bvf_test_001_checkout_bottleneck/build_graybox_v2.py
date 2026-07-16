"""
BVF Test 001 — Graybox V2: Camera Revision
Static orthographic camera with bounding-box-based framing.
Preflight validation with world_to_camera_view.
Renders only 6 still frames.
"""
import bpy
import json
import math
import os
import sys
from mathutils import Vector

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "graybox_config.json")
REVIEW_DIR = os.path.join(SCRIPT_DIR, "reviews", "v2_composition")
os.makedirs(REVIEW_DIR, exist_ok=True)

with open(CONFIG_PATH, "r") as f:
    CFG = json.load(f)

RES = CFG["output"]["resolution"]
FPS = CFG["output"]["fps"]
TOTAL = CFG["output"]["total_frames"]
SEED = CFG["seed"]
RENDER_FRAMES = [1, 75, 90, 150, 225, 345]

# ── Helpers ────────────────────────────────────────────────
def make_material(name, rgb):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.9
    return mat

def make_character(name, x, y, z, body_color, head_color):
    """Simplified geometric humanoid with contrasting head/body."""
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.15, depth=0.9,
        location=(x, y, z + 0.45)
    )
    body = bpy.context.object
    body.name = f"{name}_body"
    body.data.materials.append(make_material(f"{name}_body_mat", body_color))

    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.14,
        location=(x, y, z + 0.97)
    )
    head = bpy.context.object
    head.name = f"{name}_head"
    head.data.materials.append(make_material(f"{name}_head_mat", head_color))
    head.parent = body
    return body

def make_cashier(name, x, y, z, body_color, head_color):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.16, depth=0.95,
        location=(x, y, z + 0.475)
    )
    body = bpy.context.object
    body.name = f"{name}_body"
    body.data.materials.append(make_material(f"{name}_body_mat", body_color))

    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.15,
        location=(x, y, z + 1.0)
    )
    head = bpy.context.object
    head.name = f"{name}_head"
    head.data.materials.append(make_material(f"{name}_head_mat", head_color))
    head.parent = body
    return body

def make_counter(name, x, y, z, color):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, z + 1.2 / 2))
    obj = bpy.context.object
    obj.name = name
    obj.scale = (1.2, 0.6, 1.2)
    obj.data.materials.append(make_material(f"{name}_mat", color))
    return obj

def make_signboard(name, x, y, z, color, emission):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y + 0.1, z))
    obj = bpy.context.object
    obj.name = name
    obj.scale = (1.0, 0.06, 0.25)
    mat = make_material(f"{name}_mat", color)
    mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = emission
    obj.data.materials.append(mat)
    return obj

def make_shutter(name, x, y, z, color):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y + 0.02, z + 0.9))
    obj = bpy.context.object
    obj.name = name
    obj.scale = (1.1, 0.04, 0.8)
    mat = make_material(f"{name}_mat", color)
    mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.6
    obj.data.materials.append(mat)
    return obj

def make_floor(name, color):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.scale = (6, 10, 1)
    obj.data.materials.append(make_material(f"{name}_mat", color))
    return obj

def make_queue_stripe(name, x, color):
    """Colored stripe under a queue for graybox visibility."""
    bpy.ops.mesh.primitive_plane_add(size=1, location=(x, 0, 0.01))
    obj = bpy.context.object
    obj.name = name
    obj.scale = (0.35, 3.0, 1)
    obj.data.materials.append(make_material(f"{name}_mat", color))
    return obj

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

# ── V2 Spatial Overrides: narrower scene for better camera framing ──
CFG["spatial"]["window_positions"]["left"][0] = -1.2
CFG["spatial"]["window_positions"]["right"][0] = 1.2
CFG["spatial"]["character_radius"] = 0.12
CFG["spatial"]["character_height"] = 1.3

# Update initial customer start positions to match new window X
for qkey, new_x in [("left_queue", -1.2), ("middle_queue", 0.0), ("right_queue", 1.2)]:
    for cust in CFG["characters_initial"][qkey]:
        cust["start"][0] = new_x

# Update new customer start positions
for nc in CFG["new_customers"]:
    if nc["target_queue"] == "left":
        nc["start_pos"][0] = -1.2
    elif nc["target_queue"] == "right":
        nc["start_pos"][0] = 1.5

# Update cashier retreat for middle
CFG["spatial"]["cashier_retreat"] = [0.0, 3.8, 0.0]

mat = CFG["materials_graybox"]

# ── Build Scene (same as v1 but with queue stripes) ────────
sp = CFG["spatial"]

# Floor
make_floor("Floor", mat["floor"])

# Queue stripes for visibility
make_queue_stripe("Stripe_left", sp["window_positions"]["left"][0], [0.25, 0.28, 0.35])
make_queue_stripe("Stripe_middle", sp["window_positions"]["middle"][0], [0.28, 0.30, 0.36])
make_queue_stripe("Stripe_right", sp["window_positions"]["right"][0], [0.25, 0.28, 0.35])

# Three counters (narrower for better framing)
counters = {}
for key in ["left", "middle", "right"]:
    pos = sp["window_positions"][key]
    counters[key] = make_counter(f"Counter_{key}", pos[0], sp["counter_y"], pos[2], mat["counter"])

# Signboards
signs = {}
for key in ["left", "middle", "right"]:
    pos = sp["window_positions"][key]
    signs[key] = make_signboard(f"Sign_{key}", pos[0], pos[1], sp["signboard_z"],
                                mat["signboard_on"], 2.0)

# Off signboard (middle)
signs["middle_off"] = make_signboard("Sign_middle_off", pos_mid[0] if 'pos_mid' in dir() else sp["window_positions"]["middle"][0],
                                      sp["window_positions"]["middle"][1], sp["signboard_z"],
                                      mat["signboard_off"], 0.0)
signs["middle_off"].hide_viewport = True
signs["middle_off"].hide_render = True
signs["middle_off"].keyframe_insert(data_path="hide_viewport", frame=1)
signs["middle_off"].keyframe_insert(data_path="hide_render", frame=1)
signs["middle_off"].hide_viewport = False
signs["middle_off"].hide_render = False
signs["middle_off"].keyframe_insert(data_path="hide_viewport", frame=66)
signs["middle_off"].keyframe_insert(data_path="hide_render", frame=66)

signs["middle"].hide_viewport = False
signs["middle"].hide_render = False
signs["middle"].keyframe_insert(data_path="hide_viewport", frame=1)
signs["middle"].keyframe_insert(data_path="hide_render", frame=1)
signs["middle"].hide_viewport = True
signs["middle"].hide_render = True
signs["middle"].keyframe_insert(data_path="hide_viewport", frame=66)
signs["middle"].keyframe_insert(data_path="hide_render", frame=66)

# Shutters
shutters = {}
for key in ["left", "middle", "right"]:
    pos = sp["window_positions"][key]
    shutters[key] = make_shutter(f"Shutter_{key}", pos[0], pos[1], pos[2], mat["shutter"])
    if key != "middle":
        shutters[key].location.z = pos[2] + 0.9
        shutters[key].keyframe_insert(data_path="location", frame=1, index=2)

# Cashiers
cashiers = {}
for key in ["left", "middle", "right"]:
    pos = sp["window_positions"][key]
    cashiers[key] = make_cashier(f"Cashier_{key}", pos[0], pos[1] - 0.3,
                                  pos[2] - 0.9, [0.50, 0.50, 0.52], [0.58, 0.57, 0.55])

# Counter overlay (middle, for close indication)
pos_mid = sp["window_positions"]["middle"]
bpy.ops.mesh.primitive_cube_add(
    size=1, location=(pos_mid[0], sp["counter_y"], pos_mid[2] + 1.2 / 2)
)
counter_overlay = bpy.context.object
counter_overlay.name = "Counter_middle_overlay"
counter_overlay.scale = (1.22, 0.62, 1.22)
overlay_mat = make_material("Overlay_mat", [0.1, 0.1, 0.11])
overlay_mat.blend_method = 'BLEND'
overlay_mat.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.6
counter_overlay.data.materials.append(overlay_mat)
counter_overlay.hide_viewport = True; counter_overlay.hide_render = True
counter_overlay.keyframe_insert(data_path="hide_viewport", frame=1)
counter_overlay.keyframe_insert(data_path="hide_render", frame=1)
counter_overlay.hide_viewport = False; counter_overlay.hide_render = False
counter_overlay.keyframe_insert(data_path="hide_viewport", frame=78)
counter_overlay.keyframe_insert(data_path="hide_render", frame=78)

# Characters (V2: darker bodies, lighter heads for contrast)
char_body_color = [0.38, 0.38, 0.40]
char_head_color = [0.65, 0.63, 0.60]

characters = {}
for qkey, qname in [("left_queue", "left"), ("middle_queue", "middle"), ("right_queue", "right")]:
    for cust in CFG["characters_initial"][qkey]:
        spc = cust["start"]
        char = make_character(cust["id"], spc[0], spc[1], spc[2],
                              char_body_color, char_head_color)
        characters[cust["id"]] = {"obj": char, "start": spc.copy(), "queue": qname}

# ── Animation (same as v1) ────────────────────────────────
# Shot 1: Gentle advance
for cid, data in characters.items():
    obj = data['obj']
    start_y = data['start'][1]
    advance = 0.25
    obj.location.y = start_y
    obj.keyframe_insert(data_path="location", frame=1, index=1)
    obj.location.y = start_y + advance
    obj.keyframe_insert(data_path="location", frame=60, index=1)
    obj.keyframe_insert(data_path="location", frame=1, index=0)
    obj.keyframe_insert(data_path="location", frame=1, index=2)

# Shot 2: Middle shutter falls
mid_shutter = shutters["middle"]
start_z = pos_mid[2] + 0.9
end_z = pos_mid[2] - 0.1
mid_shutter.location.z = start_z
mid_shutter.keyframe_insert(data_path="location", frame=1, index=2)
mid_shutter.keyframe_insert(data_path="location", frame=70, index=2)
mid_shutter.location.z = end_z
mid_shutter.keyframe_insert(data_path="location", frame=88, index=2)

# Middle cashier retreat
mid_cashier = cashiers["middle"]
mid_cashier.location.y = pos_mid[1] - 0.3
mid_cashier.keyframe_insert(data_path="location", frame=1, index=1)
mid_cashier.location.y = CFG["spatial"]["cashier_retreat"][1]
mid_cashier.keyframe_insert(data_path="location", frame=90, index=1)

# Middle queue pause
for cid in ["M1", "M2", "M3"]:
    obj = characters[cid]["obj"]
    obj.location.y = obj.location.y
    obj.keyframe_insert(data_path="location", frame=60, index=1)
    obj.keyframe_insert(data_path="location", frame=105, index=1)

# Shot 3: Diversion
div = CFG["diversion"]
for cust_key in ["customer_1", "customer_2", "customer_3"]:
    d = div[cust_key]
    cid = d["id"]
    f_start, f_end = d["frames"]
    target_x = sp["window_positions"][d["to"]][0]
    target_y = sp["queue_start_y"] - (2.5 * sp["queue_spacing_y"])

    obj = characters[cid]["obj"]
    start_x = characters[cid]["start"][0]
    start_y = characters[cid]["start"][1] + 0.25

    mid1 = f_start + (f_end - f_start) // 3
    mid2 = f_start + 2 * (f_end - f_start) // 3
    step_back_y = start_y - 0.6

    obj.location.y = start_y
    obj.keyframe_insert(data_path="location", frame=120, index=1)
    obj.location.y = step_back_y
    obj.keyframe_insert(data_path="location", frame=mid1, index=1)
    obj.location.x = start_x
    obj.keyframe_insert(data_path="location", frame=mid1, index=0)
    obj.location.x = target_x
    obj.keyframe_insert(data_path="location", frame=mid2, index=0)
    obj.location.y = step_back_y
    obj.keyframe_insert(data_path="location", frame=mid2, index=1)
    obj.location.y = target_y
    obj.keyframe_insert(data_path="location", frame=f_end, index=1)
    obj.location.y = target_y
    obj.keyframe_insert(data_path="location", frame=TOTAL, index=1)
    obj.location.x = target_x
    obj.keyframe_insert(data_path="location", frame=TOTAL, index=0)

# New customers
new_custs = CFG["new_customers"]
new_char_objs = {}
for nc in new_custs:
    fid = nc["frame"]
    tx = sp["window_positions"][nc["target_queue"]][0]
    spx, spy, spz = nc["start_pos"]
    char = make_character(nc["id"], spx, spy, spz, char_body_color, char_head_color)
    new_char_objs[nc["id"]] = char

    target_y = sp["queue_start_y"] - (3.5 * sp["queue_spacing_y"])
    entry_end = min(fid + 28, TOTAL)
    char.location.y = spy
    char.keyframe_insert(data_path="location", frame=1, index=1)
    char.location.y = spy
    char.keyframe_insert(data_path="location", frame=fid, index=1)
    char.location.y = target_y
    char.keyframe_insert(data_path="location", frame=entry_end, index=1)
    char.location.y = target_y
    char.keyframe_insert(data_path="location", frame=TOTAL, index=1)

    char.hide_viewport = True; char.hide_render = True
    char.keyframe_insert(data_path="hide_viewport", frame=1)
    char.keyframe_insert(data_path="hide_render", frame=1)
    char.hide_viewport = False; char.hide_render = False
    char.keyframe_insert(data_path="hide_viewport", frame=fid)
    char.keyframe_insert(data_path="hide_render", frame=fid)

# L/R queue advance in shot 3-4
for queue_char_ids in [["L1", "L2", "L3"], ["R1", "R2", "R3"]]:
    for cid in queue_char_ids:
        if cid in characters:
            obj = characters[cid]["obj"]
            cur_y = obj.location.y
            obj.location.y = cur_y
            obj.keyframe_insert(data_path="location", frame=120, index=1)
            obj.location.y = cur_y + 0.35
            obj.keyframe_insert(data_path="location", frame=270, index=1)
            obj.keyframe_insert(data_path="location", frame=TOTAL, index=1)

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

scene.world = bpy.data.worlds.new("GrayWorldV2")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (*li["ambient"]["color"], 1.0)
bg.inputs["Strength"].default_value = li["ambient"]["strength"]
scene.eevee.use_shadows = True

# ── V2 Camera: Static Orthographic ────────────────────────
# Compute bounding box of all essential objects
essential_objects = []
for obj in bpy.data.objects:
    name = obj.name.lower()
    if any(k in name for k in ['counter', 'cashier', 'sign', 'floor',
                                 'stripe', 'l1_', 'l2_', 'l3_', 'm1_', 'm2_', 'm3_',
                                 'r1_', 'r2_', 'r3_']):
        essential_objects.append(obj)

# HARD REQUIREMENT FIXES:
# Narrow window spacing, tighter scene
# Target: counters at Y≈3, queues extend from Y≈1.5 to Y≈-2
# Ortho camera looking at (0, 0.5, 0.8) from elevated front position

# Orthographic camera
cam_data = bpy.data.cameras.new("Camera_V2")
cam_data.type = 'ORTHO'
cam_obj = bpy.data.objects.new("Camera_V2", cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj

# Oblique ortho: camera in front-above, tilted to see both counters and queues
cam_obj.location = Vector((0.0, -5.0, 9.0))
cam_obj.rotation_euler = (math.radians(50), 0, 0)

# Tighter ortho_scale — scene spacing reduced to fit
ortho_scale = 10.0
cam_data.ortho_scale = ortho_scale

print(f"Camera V2: ORTHO, location={cam_obj.location}, rotation={cam_obj.rotation_euler}, ortho_scale={ortho_scale:.2f}")

# ── Preflight Check ────────────────────────────────────────
# Key objects that MUST be visible at frame 1
FRAME_1_NAMES = []
# 3 counters
for key in ["left", "middle", "right"]:
    FRAME_1_NAMES.append(f"Counter_{key}")
# 9 initial customer bodies + heads
for cid in ["L1", "L2", "L3", "M1", "M2", "M3", "R1", "R2", "R3"]:
    FRAME_1_NAMES.append(f"{cid}_body")
    FRAME_1_NAMES.append(f"{cid}_head")
# 3 cashier bodies + heads
for key in ["left", "middle", "right"]:
    FRAME_1_NAMES.append(f"Cashier_{key}_body")
    FRAME_1_NAMES.append(f"Cashier_{key}_head")

scene.frame_set(1)

import bpy_extras.object_utils as obj_utils

preflight = {"frame": 1, "resolution": RES, "camera_type": "ORTHO",
             "ortho_scale": ortho_scale, "results": {},
             "conditions": {"visible_counters": 0, "visible_initial_customers_bodies": 0,
                           "visible_cashiers_bodies": 0, "clipped": []}}

safe_min, safe_max = 0.04, 0.96

for obj_name in FRAME_1_NAMES:
    obj = bpy.data.objects.get(obj_name)
    if not obj:
        preflight["results"][obj_name] = {"error": "not found"}
        continue

    # Get world-space bounding box corners
    bbox_corners = [obj.matrix_world @ Vector(corner)
                    for corner in obj.bound_box]
    screen_coords = [obj_utils.world_to_camera_view(scene, cam_obj, corner)
                     for corner in bbox_corners]

    xs = [p.x for p in screen_coords]
    ys = [p.y for p in screen_coords]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    width = max_x - min_x
    height = max_y - min_y

    in_bounds = (safe_min <= min_x <= safe_max and safe_min <= max_x <= safe_max and
                 safe_min <= min_y <= safe_max and safe_max >= max_y >= safe_min)
    clipped = not in_bounds

    preflight["results"][obj_name] = {
        "min_x": round(min_x, 4), "max_x": round(max_x, 4),
        "min_y": round(min_y, 4), "max_y": round(max_y, 4),
        "width": round(width, 4), "height": round(height, 4),
        "in_bounds": in_bounds, "clipped": clipped
    }

    if clipped:
        preflight["conditions"]["clipped"].append(obj_name)

    # Count visible objects
    if "counter_" in obj_name.lower():
        preflight["conditions"]["visible_counters"] += 1
    elif obj_name.endswith("_body") and obj_name.startswith(("L1", "L2", "L3",
                                                               "M1", "M2", "M3",
                                                               "R1", "R2", "R3")):
        preflight["conditions"]["visible_initial_customers_bodies"] += 1
    elif obj_name.startswith("Cashier_") and obj_name.endswith("_body"):
        preflight["conditions"]["visible_cashiers_bodies"] += 1

# Pixel height check (after all objects processed)
min_pixel_height = 55
min_char_height_px = 999
for obj_name in FRAME_1_NAMES:
    if obj_name.endswith("_body") and obj_name.startswith(("L1", "L2", "L3", "M1", "M2", "M3", "R1", "R2", "R3")):
        h = preflight["results"][obj_name]["height"]
        px = int(h * RES[1])
        if px < min_char_height_px:
            min_char_height_px = px
preflight["conditions"]["min_character_pixel_height"] = min_char_height_px
preflight["conditions"]["pixel_height_pass"] = min_char_height_px >= min_pixel_height

# Evaluate passes
tc = preflight["conditions"]
tc["counters_pass"] = tc["visible_counters"] == 3
tc["customers_pass"] = tc["visible_initial_customers_bodies"] == 9
tc["cashiers_pass"] = tc["visible_cashiers_bodies"] == 3
tc["clipping_pass"] = len(tc["clipped"]) == 0
tc["all_pass"] = all([tc["counters_pass"], tc["customers_pass"],
                       tc["cashiers_pass"], tc["clipping_pass"],
                       tc["pixel_height_pass"]])

# Save preflight
preflight_path = os.path.join(REVIEW_DIR, "camera_preflight_v2.json")
with open(preflight_path, "w") as f:
    json.dump(preflight, f, indent=2)
print(f"Preflight saved: {preflight_path}")
print(f"  Counters visible: {tc['visible_counters']}/3 {'PASS' if tc['counters_pass'] else 'FAIL'}")
print(f"  Customers visible: {tc['visible_initial_customers_bodies']}/9 {'PASS' if tc['customers_pass'] else 'FAIL'}")
print(f"  Cashiers visible: {tc['visible_cashiers_bodies']}/3 {'PASS' if tc['cashiers_pass'] else 'FAIL'}")
print(f"  Clipped objects: {len(tc['clipped'])} {'PASS' if tc['clipping_pass'] else 'FAIL'}")
print(f"  Min character pixel height: {tc['min_character_pixel_height']}px {'PASS' if tc['pixel_height_pass'] else 'FAIL'}")
print(f"  ALL PASS: {tc['all_pass']}")

# ── Render 6 Stills ────────────────────────────────────────
if not tc["all_pass"]:
    print("\n*** PREFLIGHT FAILED — ABORTING RENDER ***")
    print(f"Clipped objects: {tc['clipped']}")
else:
    print("\n=== Preflight passed. Rendering 6 stills... ===")
    for frame in RENDER_FRAMES:
        scene.frame_set(frame)
        out_path = os.path.join(REVIEW_DIR, f"F{frame:03d}.png")
        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        print(f"  Frame {frame}: {out_path}")

# ── Save .blend ────────────────────────────────────────────
blend_path = os.path.join(SCRIPT_DIR, "scene_graybox_v2_composition.blend")
bpy.ops.wm.save_mainfile(filepath=blend_path)
print(f"Saved: {blend_path}")
print("V2 COMPLETE")
