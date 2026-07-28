"""
BVF Test 001 — Graybox Scene Builder
Deterministic build from graybox_config.json.
Run: blender --background --python build_graybox.py
"""
import bpy
import json
import math
import os
import sys
from mathutils import Vector, Euler

# ── Constants ──────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "graybox_config.json")
OUT_DIR = os.path.join(SCRIPT_DIR, "graybox_frames")
COMPARE_DIR = os.path.join(SCRIPT_DIR, "reviews", "keyframes")
# OUT_DIR and COMPARE_DIR are shared between builds; per-build comparison handled separately

# ── Load Config ────────────────────────────────────────────
with open(CONFIG_PATH, "r") as f:
    CFG = json.load(f)

RES = CFG["output"]["resolution"]
FPS = CFG["output"]["fps"]
TOTAL = CFG["output"]["total_frames"]
SEED = CFG["seed"]
COMPARE_FRAMES = CFG["comparison_frames"]

# ── Helpers ────────────────────────────────────────────────
def make_material(name, rgb):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.9
    return mat

def make_character(name, x, y, z, color, radius=None, height=None):
    """Simplified geometric humanoid: cylinder body + sphere head."""
    if radius is None: radius = CFG["spatial"].get("character_radius", 0.15)
    if height is None: height = CFG["spatial"].get("character_height", 1.4)
    body_depth = height * 0.643  # body is ~64% of total height
    head_radius = radius * 0.93
    body_z = body_depth / 2
    head_z = body_depth + head_radius * 0.5
    local_head_z = head_z - body_z
    # Body
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=body_depth,
        location=(x, y, z + body_z)
    )
    body = bpy.context.object
    body.name = f"{name}_body"
    mat = make_material(f"{name}_mat", color)
    body.data.materials.append(mat)

    # Head
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=head_radius,
        location=(0, 0, 0)
    )
    head = bpy.context.object
    head.name = f"{name}_head"
    head.data.materials.append(mat)

    head.parent = body
    head.location = (0, 0, local_head_z)

    return body

def make_cashier(name, x, y, z, color):
    """Cashier standing behind counter."""
    r = CFG["spatial"].get("character_radius", 0.15) * 1.07  # slightly larger
    h = CFG["spatial"].get("character_height", 1.4) * 1.07
    body_depth = h * 0.643
    head_radius = r * 0.93
    body_z = body_depth / 2
    local_head_z = body_depth + head_radius * 0.5 - body_z

    bpy.ops.mesh.primitive_cylinder_add(
        radius=r, depth=body_depth,
        location=(x, y, z + body_z)
    )
    body = bpy.context.object
    body.name = f"{name}_body"
    mat = make_material(f"{name}_mat", color)
    body.data.materials.append(mat)

    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=head_radius,
        location=(0, 0, 0)
    )
    head = bpy.context.object
    head.name = f"{name}_head"
    head.data.materials.append(mat)
    head.parent = body
    head.location = (0, 0, local_head_z)
    return body

def make_counter(name, x, y, z, color):
    """Counter/checkout desk."""
    bpy.ops.mesh.primitive_cube_add(
        size=1,
        location=(x, y, z + 1.2 / 2)
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = (1.6, 0.8, 1.2)
    obj.data.materials.append(make_material(f"{name}_mat", color))
    return obj

def make_signboard(name, x, y, z, color):
    """Light sign above window."""
    bpy.ops.mesh.primitive_cube_add(
        size=1,
        location=(x, y + 0.1, z)
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = (1.2, 0.08, 0.3)
    mat = make_material(f"{name}_mat", color)
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 2.0
    obj.data.materials.append(mat)
    return obj

def make_shutter(name, x, y, z, color):
    """Roll-down shutter above counter."""
    bpy.ops.mesh.primitive_cube_add(
        size=1,
        location=(x, y + 0.02, z + 0.9)
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = (1.5, 0.05, 0.9)
    mat = make_material(f"{name}_mat", color)
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.6
    obj.data.materials.append(mat)
    return obj

def make_floor(name, color):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.scale = (6, 6, 1)
    obj.data.materials.append(make_material(f"{name}_mat", color))
    return obj

def make_wall(name, color):
    """Back wall behind counters."""
    bpy.ops.mesh.primitive_cube_add(
        size=1,
        location=(0, 4.0, 2.0)
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = (6, 0.2, 4)
    obj.data.materials.append(make_material(f"{name}_mat", color))
    return obj

def quad_bezier(t, p0, p1, p2):
    """Quadratic bezier for smooth diversion paths."""
    u = 1 - t
    return u * u * p0 + 2 * u * t * p1 + t * t * p2

# ── Clear Scene ────────────────────────────────────────────
def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.engine = CFG["output"]["engine"]
    bpy.context.scene.render.resolution_x = RES[0]
    bpy.context.scene.render.resolution_y = RES[1]
    bpy.context.scene.render.fps = FPS
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = TOTAL
    bpy.context.scene.render.image_settings.file_format = 'PNG'
    bpy.context.scene.render.image_settings.color_mode = 'RGB'
    bpy.context.scene.render.film_transparent = False

# ── Build Scene ────────────────────────────────────────────
def build_scene():
    mat = CFG["materials_graybox"]

    # Floor and back wall
    make_floor("Floor", mat["floor"])
    make_wall("BackWall", [0.22, 0.22, 0.24])

    # Three counters
    counters = {}
    for side, key in [("left", "left"), ("middle", "middle"), ("right", "right")]:
        pos = CFG["spatial"]["window_positions"][key]
        name = f"Counter_{side}"
        obj = make_counter(name, pos[0], CFG["spatial"]["counter_y"], pos[2], mat["counter"])
        counters[key] = obj

    # Signboards
    signs = {}
    for key in ["left", "middle", "right"]:
        pos = CFG["spatial"]["window_positions"][key]
        name = f"Sign_{key}"
        obj = make_signboard(name, pos[0], pos[1], CFG["spatial"]["signboard_z"],
                            mat["signboard_on"])
        signs[key] = obj

    # Shutters (only middle visible and animated)
    shutters = {}
    for key in ["left", "middle", "right"]:
        pos = CFG["spatial"]["window_positions"][key]
        name = f"Shutter_{key}"
        obj = make_shutter(name, pos[0], pos[1], pos[2], mat["shutter"])
        shutters[key] = obj
        # Position shutters at top (open) for left and right
        if key != "middle":
            obj.location.z = pos[2] + 0.9
            obj.keyframe_insert(data_path="location", frame=1)

    # Cashiers
    cashiers = {}
    for key in ["left", "middle", "right"]:
        pos = CFG["spatial"]["window_positions"][key]
        name = f"Cashier_{key}"
        obj = make_cashier(name, pos[0], pos[1] - 0.3, pos[2] - 0.9, mat["cashier"])
        cashiers[key] = obj

    # ── Unified queue slot allocator ──
    qsy = CFG["spatial"]["queue_spacing_y"]
    qsy_front = CFG["spatial"]["queue_start_y"]
    lane_slots = {"left": 0, "middle": 0, "right": 0}  # next available slot per lane

    def allocate_slot(lane_name):
        """Return Y position for the next available slot in lane."""
        slot = lane_slots[lane_name]
        lane_slots[lane_name] += 1
        return qsy_front - slot * qsy

    # Initial customers — positions from slot allocator
    characters = {}
    for queue_key in ["left_queue", "middle_queue", "right_queue"]:
        qdata = CFG["characters_initial"][queue_key]
        lane_x = qdata["lane_x"]
        lane_name = queue_key.replace("_queue", "")
        color = qdata["color"]
        for cid in qdata["ids"]:
            cy = allocate_slot(lane_name)
            sp = [lane_x, cy, 0.0]
            char = make_character(cid, sp[0], sp[1], sp[2], color)
            characters[cid] = {"obj": char, "color": color,
                               "start": sp, "queue": lane_name}

    # ── Animation Setup ────────────────────────────────────
    scene = bpy.context.scene
    sp = CFG["spatial"]
    wc = CFG["window_close"]
    div = CFG["diversion"]
    new_custs = CFG["new_customers"]

    # --- Shot 1 (1-60): Gentle queue advance ---
    for cid, data in characters.items():
        obj = data["obj"]
        start_y = data["start"][1]
        # Slight forward movement (towards counter at higher Y)
        advance = 0.25
        obj.location.y = start_y
        obj.keyframe_insert(data_path="location", frame=1, index=1)
        obj.location.y = start_y + advance
        obj.keyframe_insert(data_path="location", frame=60, index=1)

        # Also key X and Z at frame 1
        obj.keyframe_insert(data_path="location", frame=1, index=0)
        obj.keyframe_insert(data_path="location", frame=1, index=2)

    # --- Shot 2 (61-120): Window close ---
    # Use dual-object material swap for signboard:
    # "On" signboard (already created) and "off" signboard (created here)
    mid_sign_on = signs["middle"]
    pos_mid = sp["window_positions"]["middle"]
    mid_sign_off = make_signboard("Sign_middle_off", pos_mid[0], pos_mid[1],
                                   sp["signboard_z"], mat["signboard_off"])
    # Remove emission from off signboard
    mid_sign_off.data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 0.0

    # Visibility keyframes: on visible 1-66, off visible 66-345
    mid_sign_on.hide_viewport = False; mid_sign_on.hide_render = False
    mid_sign_on.keyframe_insert(data_path="hide_viewport", frame=1)
    mid_sign_on.keyframe_insert(data_path="hide_render", frame=1)
    mid_sign_on.hide_viewport = True; mid_sign_on.hide_render = True
    mid_sign_on.keyframe_insert(data_path="hide_viewport", frame=66)
    mid_sign_on.keyframe_insert(data_path="hide_render", frame=66)

    mid_sign_off.hide_viewport = True; mid_sign_off.hide_render = True
    mid_sign_off.keyframe_insert(data_path="hide_viewport", frame=1)
    mid_sign_off.keyframe_insert(data_path="hide_render", frame=1)
    mid_sign_off.hide_viewport = False; mid_sign_off.hide_render = False
    mid_sign_off.keyframe_insert(data_path="hide_viewport", frame=66)
    mid_sign_off.keyframe_insert(data_path="hide_render", frame=66)

    # Counter color: overlay approach — create a dark overlay cube
    # that fades in opacity or toggles visibility (frames 72-84)
    bpy.ops.mesh.primitive_cube_add(
        size=1, location=(pos_mid[0], sp["counter_y"], pos_mid[2] + 1.2 / 2)
    )
    counter_overlay = bpy.context.object
    counter_overlay.name = "Counter_middle_overlay"
    counter_overlay.scale = (1.62, 0.82, 1.22)
    overlay_mat = make_material("Overlay_mat", [0.1, 0.1, 0.11])
    overlay_mat.use_nodes = True
    # Use a dark translucent material
    overlay_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.1, 0.1, 0.11, 1.0)
    overlay_mat.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.7
    overlay_mat.blend_method = 'BLEND'
    counter_overlay.data.materials.append(overlay_mat)

    counter_overlay.hide_viewport = True; counter_overlay.hide_render = True
    counter_overlay.keyframe_insert(data_path="hide_viewport", frame=1)
    counter_overlay.keyframe_insert(data_path="hide_render", frame=1)
    counter_overlay.hide_viewport = False; counter_overlay.hide_render = False
    counter_overlay.keyframe_insert(data_path="hide_viewport", frame=78)
    counter_overlay.keyframe_insert(data_path="hide_render", frame=78)

    # Middle shutter: falls down (frames 70-88)
    mid_shutter = shutters["middle"]
    start_z = sp["window_positions"]["middle"][2] + 0.9
    end_z = sp["window_positions"]["middle"][2] - 0.1
    mid_shutter.location.z = start_z
    mid_shutter.keyframe_insert(data_path="location", frame=1, index=2)
    mid_shutter.location.z = start_z
    mid_shutter.keyframe_insert(data_path="location", frame=70, index=2)
    mid_shutter.location.z = end_z
    mid_shutter.keyframe_insert(data_path="location", frame=88, index=2)

    # Middle cashier: walk out from behind counter to the right, then exit through open area (frames 82-102)
    mid_cashier = cashiers["middle"]
    cashier_start_y = CFG["spatial"]["window_positions"]["middle"][1] - 0.3  # 2.7
    cashier_start_x = CFG["spatial"]["window_positions"]["middle"][0]  # 0.0

    # Hold initial position at frame 1
    mid_cashier.location.x = cashier_start_x
    mid_cashier.location.y = cashier_start_y
    mid_cashier.keyframe_insert(data_path="location", frame=1, index=0)
    mid_cashier.keyframe_insert(data_path="location", frame=1, index=1)
    mid_cashier.keyframe_insert(data_path="location", frame=1, index=2)

    # Phase 1 (82-90): step out from behind middle counter to the right (X: 0.0→1.4)
    mid_cashier.location.y = cashier_start_y
    mid_cashier.keyframe_insert(data_path="location", frame=82, index=1)
    mid_cashier.location.x = cashier_start_x
    mid_cashier.keyframe_insert(data_path="location", frame=82, index=0)
    mid_cashier.location.z = mid_cashier.location.z
    mid_cashier.keyframe_insert(data_path="location", frame=82, index=2)
    mid_cashier.location.x = 1.4
    mid_cashier.keyframe_insert(data_path="location", frame=90, index=0)

    # Phase 2 (90-102): continue moving forward-right into open area (X: 1.4→2.2, Y: 2.7→1.5)
    mid_cashier.location.x = 2.2
    mid_cashier.keyframe_insert(data_path="location", frame=102, index=0)
    mid_cashier.location.y = 1.5
    mid_cashier.keyframe_insert(data_path="location", frame=102, index=1)
    mid_cashier.location.z = mid_cashier.location.z
    mid_cashier.keyframe_insert(data_path="location", frame=102, index=2)

    # Frame 1: ensure cashier body visible
    mid_cashier.hide_viewport = False
    mid_cashier.hide_render = False
    mid_cashier.keyframe_insert(data_path="hide_viewport", frame=1)
    mid_cashier.keyframe_insert(data_path="hide_render", frame=1)

    # Frame 102: hide cashier body (matches patch_cashier_exit_on_validated_b.py)
    mid_cashier.hide_viewport = True
    mid_cashier.hide_render = True
    mid_cashier.keyframe_insert(data_path="hide_viewport", frame=102)
    mid_cashier.keyframe_insert(data_path="hide_render", frame=102)

    # XYZ hold at TOTAL — stabilize DG evaluation for hidden animated objects
    mid_cashier.location.x = 2.2
    mid_cashier.keyframe_insert(data_path="location", frame=TOTAL, index=0)
    mid_cashier.location.y = 1.5
    mid_cashier.keyframe_insert(data_path="location", frame=TOTAL, index=1)
    mid_cashier.location.z = mid_cashier.location.z
    mid_cashier.keyframe_insert(data_path="location", frame=TOTAL, index=2)

    # Cashier head visibility sync (matches patch lines 98-106)
    for child in mid_cashier.children:
        if child.name.endswith("_head"):
            child.hide_viewport = False
            child.hide_render = False
            child.keyframe_insert(data_path="hide_viewport", frame=1)
            child.keyframe_insert(data_path="hide_render", frame=1)
            child.hide_viewport = True
            child.hide_render = True
            child.keyframe_insert(data_path="hide_viewport", frame=102)
            child.keyframe_insert(data_path="hide_render", frame=102)

    # Middle queue customers pause (stop advancing after frame 60)
    for cid in ["M1", "M2", "M3"]:
        obj = characters[cid]["obj"]
        # Hold position at frame 60
        obj.location.y = obj.location.y  # Current
        obj.keyframe_insert(data_path="location", frame=60, index=1)
        obj.keyframe_insert(data_path="location", frame=105, index=1)

    # --- Shot 3 (121-225): Diversion + new customers ---
    # Diversion paths
    diversion_paths = []
    for cust_key in ["customer_1", "customer_2", "customer_3"]:
        d = div[cust_key]
        cid = d["id"]
        f_start, f_end = d["frames"]
        target_queue = d["to"]
        target_x = sp["window_positions"][target_queue][0]

        # Target Y: allocate unique slot in target lane
        target_y = allocate_slot(target_queue)

        # Three-phase path: step back → sideways → forward
        obj = characters[cid]["obj"]
        start_x = characters[cid]["start"][0]
        start_y = characters[cid]["start"][1] + 0.25  # After shot 1 advance

        mid_frames = f_start + (f_end - f_start) // 3
        mid2_frames = f_start + 2 * (f_end - f_start) // 3

        # Phase 1: step back (away from counter, lower Y)
        step_back_y = start_y - 0.6
        obj.location.y = start_y
        obj.keyframe_insert(data_path="location", frame=f_start, index=1)
        obj.location.y = step_back_y
        obj.keyframe_insert(data_path="location", frame=mid_frames, index=1)

        # Phase 2: sideways move
        obj.location.x = start_x
        obj.keyframe_insert(data_path="location", frame=mid_frames, index=0)
        obj.location.x = target_x
        obj.keyframe_insert(data_path="location", frame=mid2_frames, index=0)

        # Phase 3: move forward into new queue
        obj.location.y = step_back_y
        obj.keyframe_insert(data_path="location", frame=mid2_frames, index=1)
        obj.location.y = target_y
        obj.keyframe_insert(data_path="location", frame=f_end, index=1)

        # Hold after diversion
        obj.location.y = target_y
        obj.keyframe_insert(data_path="location", frame=TOTAL, index=1)
        obj.location.x = target_x
        obj.keyframe_insert(data_path="location", frame=TOTAL, index=0)

        diversion_paths.append({
            "id": cid, "start": f_start, "end": f_end,
            "from_x": start_x, "to_x": target_x, "target_queue": target_queue
        })

    # New customers enter — positions computed from queue_spacing_y
    new_char_objs = {}
    for nc in new_custs:
        fid = nc["frame"]
        qkey = nc["target_queue"]
        lane_x = CFG["characters_initial"][qkey]["lane_x"]
        color = nc["color"]
        # Entry from below, Y = new_customer_entry_y
        spy = CFG["spatial"]["new_customer_entry_y"]
        spx, spz = lane_x, 0.0
        char = make_character(nc["id"], spx, spy, spz, color)
        new_char_objs[nc["id"]] = char

        # Target Y: allocate unique slot in target lane
        lane_key = qkey.replace("_queue", "")
        target_y = allocate_slot(lane_key)
        entry_end = min(fid + 28, TOTAL)
        char.location.y = spy
        char.keyframe_insert(data_path="location", frame=1, index=1)
        char.location.y = spy
        char.keyframe_insert(data_path="location", frame=fid, index=1)
        char.location.y = target_y
        char.keyframe_insert(data_path="location", frame=entry_end, index=1)

        # Hold
        char.location.y = target_y
        char.keyframe_insert(data_path="location", frame=TOTAL, index=1)

        # Set visibility: hidden before entry
        char.hide_viewport = True
        char.hide_render = True
        char.keyframe_insert(data_path="hide_viewport", frame=1)
        char.keyframe_insert(data_path="hide_render", frame=1)
        char.hide_viewport = False
        char.hide_render = False
        char.keyframe_insert(data_path="hide_viewport", frame=fid)
        char.keyframe_insert(data_path="hide_render", frame=fid)

        # BUG FIX (R2): sync head visibility with body
        for child in char.children:
            if child.name.endswith("_head"):
                child.hide_viewport = True
                child.hide_render = True
                child.keyframe_insert(data_path="hide_viewport", frame=1)
                child.keyframe_insert(data_path="hide_render", frame=1)
                child.hide_viewport = False
                child.hide_render = False
                child.keyframe_insert(data_path="hide_viewport", frame=fid)
                child.keyframe_insert(data_path="hide_render", frame=fid)

    # R1, R2, R3 also get gentle advance in Shot 3-4 (frames 121-270)
    # L1, L2, L3 same
    for queue_char_ids in [["L1", "L2", "L3"], ["R1", "R2", "R3"]]:
        extra_advance = 0.35  # Additional advance for queue movement
        for cid in queue_char_ids:
            if cid in characters:
                obj = characters[cid]["obj"]
                cur_y = obj.location.y
                obj.location.y = cur_y
                obj.keyframe_insert(data_path="location", frame=120, index=1)
                obj.location.y = cur_y + extra_advance
                obj.keyframe_insert(data_path="location", frame=270, index=1)
                obj.keyframe_insert(data_path="location", frame=TOTAL, index=1)

    # New customers also slowly advance after entering
    for nc in new_custs:
        cid = nc["id"]
        if cid in new_char_objs:
            obj = new_char_objs[cid]
            cur_y = obj.location.y
            final_advance = 0.2
            obj.keyframe_insert(data_path="location", frame=TOTAL, index=1)
            # Small advance at end
            obj.location.y = cur_y + final_advance
            # Insert a keyframe near the end
            hold_frame = min(nc["frame"] + 28 + 20, TOTAL)
            obj.keyframe_insert(data_path="location", frame=hold_frame, index=1)

    # ── Lighting ────────────────────────────────────────────
    li = CFG["lighting"]
    bpy.ops.object.light_add(type='SUN', location=li["sun"]["location"])
    sun = bpy.context.object
    sun.name = "Sun"
    sun.data.energy = li["sun"]["energy"]
    sun.data.color = li["sun"]["color"]

    bpy.ops.object.light_add(type='AREA', location=li["fill"]["location"])
    fill = bpy.context.object
    fill.name = "Fill"
    fill.data.energy = li["fill"]["energy"]
    fill.data.color = li["fill"]["color"]
    fill.data.size = 5

    bpy.context.scene.world = bpy.data.worlds.new("GrayWorld")
    bpy.context.scene.world.use_nodes = True
    bg = bpy.context.scene.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*li["ambient"]["color"], 1.0)
    bg.inputs["Strength"].default_value = li["ambient"]["strength"]

    # Eevee settings
    bpy.context.scene.eevee.use_shadows = True

    # ── Camera ──────────────────────────────────────────────
    bpy.ops.object.camera_add(location=CFG["camera"]["location"])
    cam = bpy.context.object
    cam.name = "Camera"
    cam.data.lens = CFG["camera"]["focal_length"]
    cam.data.sensor_width = CFG["camera"]["sensor_width"]
    cam.rotation_euler = CFG["camera"]["rotation"]
    scene.camera = cam

    # Camera movements
    cam_loc = Vector(CFG["camera"]["location"])
    cam.keyframe_insert(data_path="location", frame=1)

    # Frames 1-120: slight drift
    drift = Vector(CFG["camera"]["movements"]["frames_1_120"]["drift"])
    target = cam_loc + drift
    for axis in range(3):
        cam.location[axis] = target[axis]
    cam.keyframe_insert(data_path="location", frame=120)

    # Frames 121-225: push + elevate
    offset2 = Vector(CFG["camera"]["movements"]["frames_121_225"]["offset"])
    target2 = target + offset2
    cam.location = target2
    cam.keyframe_insert(data_path="location", frame=225)

    # Frames 226-270: pull out
    offset3 = Vector(CFG["camera"]["movements"]["frames_226_270"]["offset"])
    target3 = target2 + offset3
    cam.location = target3
    cam.keyframe_insert(data_path="location", frame=270)

    # Frames 271-345: stable
    cam.keyframe_insert(data_path="location", frame=345)

    # Smooth interpolation (default bezier is fine for graybox)

    return {
        "counters": counters, "signs": signs, "shutters": shutters,
        "cashiers": cashiers, "characters": characters,
        "new_characters": new_char_objs, "camera": cam
    }

# ── Render Comparison Frames ───────────────────────────────
def render_comparison_frames():
    scene = bpy.context.scene
    for frame in COMPARE_FRAMES:
        scene.frame_set(frame)
        out_path = os.path.join(COMPARE_DIR, f"frame_{frame:04d}.png")
        scene.render.filepath = out_path
        scene.render.image_settings.file_format = 'PNG'
        bpy.ops.render.render(write_still=True)
        print(f"  Rendered frame {frame}: {out_path}")

# ── Render Full Sequence ───────────────────────────────────
def render_full():
    scene = bpy.context.scene
    scene.render.filepath = os.path.join(OUT_DIR, "frame_")
    print(f"Rendering {TOTAL} frames to {OUT_DIR}...")
    bpy.ops.render.render(animation=True)
    rendered = sorted([f for f in os.listdir(OUT_DIR) if f.endswith('.png')])
    print(f"Rendered {len(rendered)} frames")
    return rendered

# ── Main ───────────────────────────────────────────────────
if __name__ == "__main__":
    import random
    random.seed(SEED)

    build_name = os.environ.get("BVF_BUILD", "A")
    blend_name = f"scene_graybox_{build_name}.blend"
    skip_full_render = os.environ.get("BVF_SKIP_RENDER", "0") == "1"
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(COMPARE_DIR, exist_ok=True)

    print("=" * 50)
    print(f"BVF Graybox Builder — Build {build_name}")
    print(f"Config: {CONFIG_PATH}")
    print(f"Resolution: {RES[0]}x{RES[1]} @ {FPS}fps")
    print(f"Total frames: {TOTAL}")
    print(f"Seed: {SEED}")
    print("=" * 50)

    clear_scene()
    print("Scene cleared.")

    objects = build_scene()
    print("Scene built.")

    # Total objects: floor + wall + 3 counters + 3 signs + 3 shutters + 3 cashiers
    # + (9 initial customers × 2 parts) + (4 new customers × 2 parts)
    # + 2 lights + 1 camera = 44 objects
    total_objs = len(bpy.data.objects)
    print(f"Total objects: {total_objs}")

    # Render comparison frames
    print("Rendering comparison frames...")
    render_comparison_frames()

    # Full render (skip if rebuilding just for .blend)
    if not skip_full_render:
        rendered = render_full()
        print(f"Rendered {len(rendered)} frames total.")
    else:
        print("Skipped full render (--skip-render)")

    # Save .blend at frame 1 (stable state for downstream checks)
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    blend_path = os.path.join(SCRIPT_DIR, blend_name)
    bpy.ops.wm.save_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")
    print("BUILD COMPLETE")
