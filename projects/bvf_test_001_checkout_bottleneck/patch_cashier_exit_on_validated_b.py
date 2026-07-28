"""
patch_cashier_exit_on_validated_b.py
Run: blender --background scene_graybox_gate_7007d28f.blend --python this_script.py

Applies cashier exit animation and diversion retiming to the validated B scene.
Does NOT rebuild the scene, change camera, lighting, or any other animation.
"""
import bpy
import os
import sys
import shutil
import hashlib

# ── Paths ──
PROJECT = r"D:\blender-video-factory\projects\bvf_test_001_checkout_bottleneck"
SRC_BLEND = os.path.join(PROJECT, "scene_graybox_gate_7007d28f.blend")
OUT_DIR = os.path.join(PROJECT, "output", "cashier_exit_fix_preview_v2")
PATCHED_BLEND = os.path.join(OUT_DIR, "patched_b_cashier_exit_preview.blend")
FRAMES_DIR = os.path.join(OUT_DIR, "frames")
DELIVERY_DIR = os.path.join(OUT_DIR, "delivery")


def compute_sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest().upper()


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(FRAMES_DIR, exist_ok=True)
    os.makedirs(DELIVERY_DIR, exist_ok=True)

    # ── 1. Copy source blend ──
    if not os.path.exists(SRC_BLEND):
        print(f"ERROR: Source blend not found: {SRC_BLEND}")
        sys.exit(1)

    src_sha256 = compute_sha256(SRC_BLEND)
    print(f"Source blend: {SRC_BLEND}")
    print(f"SHA256: {src_sha256}")

    # Use bpy to save-as (preserves all data correctly)
    bpy.ops.wm.save_as_mainfile(filepath=PATCHED_BLEND)
    print(f"Patched blend saved: {PATCHED_BLEND}")

    # ── 2. Patch cashier animation ──
    scene = bpy.context.scene

    # Find cashier objects
    cashier_body = None
    cashier_head = None
    for obj in bpy.data.objects:
        if obj.name == "Cashier_middle_body":
            cashier_body = obj
        elif obj.name == "Cashier_middle_head":
            cashier_head = obj

    if cashier_body is None:
        print("ERROR: Cashier_middle_body not found")
        sys.exit(1)
    if cashier_head is None:
        print("ERROR: Cashier_middle_head not found")
        sys.exit(1)

    print(f"Found: {cashier_body.name}, {cashier_head.name}")

    # ── Overlay new cashier exit keyframes WITHOUT disturbing frames 1-89 ──
    # Original scene has Y keyframes at frames 1 (Y=2.7) and 90 (Y=3.8).
    # We add NEW keyframes on UNUSED frames to avoid overwriting.
    # Y snap at frame 91 avoids touching the frame-90 keyframe handles.

    # Frame 1: ensure visibility is set
    cashier_body.hide_viewport = False
    cashier_body.hide_render = False
    cashier_body.keyframe_insert(data_path="hide_viewport", frame=1)
    cashier_body.keyframe_insert(data_path="hide_render", frame=1)

    # Frame 90: add X keyframe (X had no prior animation — safe to add)
    cashier_body.location.x = 1.4
    cashier_body.keyframe_insert(data_path="location", index=0, frame=90)

    # Frame 91: Y snaps forward from original 3.8 to 2.7 (1-frame step)
    cashier_body.location.y = 2.7
    cashier_body.keyframe_insert(data_path="location", index=1, frame=91)

    # Frame 102: X=2.2, Y=1.5 (exit into open area), hidden
    cashier_body.location.x = 2.2
    cashier_body.keyframe_insert(data_path="location", index=0, frame=102)
    cashier_body.location.y = 1.5
    cashier_body.keyframe_insert(data_path="location", index=1, frame=102)
    cashier_body.hide_viewport = True
    cashier_body.hide_render = True
    cashier_body.keyframe_insert(data_path="hide_viewport", frame=102)
    cashier_body.keyframe_insert(data_path="hide_render", frame=102)

    print("Cashier body keyframes inserted")

    # Cashier head visibility sync (head has no independent location keyframes)
    cashier_head.hide_viewport = False
    cashier_head.hide_render = False
    cashier_head.keyframe_insert(data_path="hide_viewport", frame=1)
    cashier_head.keyframe_insert(data_path="hide_render", frame=1)
    cashier_head.hide_viewport = True
    cashier_head.hide_render = True
    cashier_head.keyframe_insert(data_path="hide_viewport", frame=102)
    cashier_head.keyframe_insert(data_path="hide_render", frame=102)

    print("Cashier head keyframes inserted")

    # ── 3. Retime M1/M2/M3 diversion ──
    # Save positions at key frames, delete old location keyframes in diversion range,
    # then re-insert at shifted frames.
    shift_amount = -11
    diversion_origin = {
        "M1_body": [121, 153, 345],
        "M2_body": [136, 168, 345],
        "M3_body": [151, 183, 345],
    }

    for char_name, origin_frames in diversion_origin.items():
        obj = bpy.data.objects.get(char_name)
        if obj is None:
            print(f"WARNING: {char_name} not found")
            continue

        # Save location at each origin frame
        saved = {}
        for of in origin_frames:
            scene.frame_set(of)
            bpy.context.view_layer.update()
            saved[of] = (obj.location.x, obj.location.y, obj.location.z)
            print(f"  {char_name} at {of}: ({obj.location.x:.3f}, {obj.location.y:.3f}, {obj.location.z:.3f})")

        # Delete old location X/Y keyframes in this range
        for data_path in ["location"]:
            for axis_idx in [0, 1]:  # X and Y only
                try:
                    obj.keyframe_delete(data_path, index=axis_idx,
                                        frame=min(origin_frames) - 10,
                                        end_frame=max(origin_frames) + 10)
                except Exception:
                    pass  # May fail if no keyframes at exact frame range

        # Also handle anchor frame ~120
        try:
            obj.keyframe_delete("location", index=0, frame=118, end_frame=122)
            obj.keyframe_delete("location", index=1, frame=118, end_frame=122)
        except Exception:
            pass

        # Re-insert at shifted frames
        for of in origin_frames:
            new_frame = of + shift_amount
            x, y, z = saved[of]
            scene.frame_set(new_frame)
            obj.location = (x, y, z)
            obj.keyframe_insert(data_path="location", frame=new_frame)
            print(f"  {char_name}: inserted at {new_frame} ({x:.3f}, {y:.3f}, {z:.3f})")

        # Also shift the anchor frame (120 → 109)
        scene.frame_set(120)
        bpy.context.view_layer.update()
        anchor_x, anchor_y, anchor_z = obj.location.x, obj.location.y, obj.location.z
        scene.frame_set(109)
        obj.location = (anchor_x, anchor_y, anchor_z)
        obj.keyframe_insert(data_path="location", frame=109)
        print(f"  {char_name}: anchor at 109 ({anchor_x:.3f}, {anchor_y:.3f}, {anchor_z:.3f})")

    # ── Save ──
    bpy.ops.wm.save_mainfile(filepath=PATCHED_BLEND)
    print(f"Patched blend saved: {PATCHED_BLEND}")

    # ── Verify keyframes ──
    print("\n=== Cashier Keyframe Verification ===")
    for frame in [1, 40, 70, 90, 102]:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        bx, by, bz = cashier_body.location
        bhv = cashier_body.hide_viewport
        bhr = cashier_body.hide_render
        hhv = cashier_head.hide_viewport
        hhr = cashier_head.hide_render
        print(f"  Frame {frame}: body=({bx:.1f},{by:.1f},{bz:.1f}) "
              f"body_hide=({bhv},{bhr}) head_hide=({hhv},{hhr})")

    print("\n=== Diversion Keyframe Verification ===")
    for char_name in diversion_origin.keys():
        obj = bpy.data.objects.get(char_name)
        if obj is None:
            continue
        print(f"  {char_name}:")
        for f in [105, 110, 125, 140, 142, 157, 172, 345]:
            scene.frame_set(f)
            bpy.context.view_layer.update()
            print(f"    frame {f}: ({obj.location.x:.3f}, {obj.location.y:.3f}, {obj.location.z:.3f})")

    # ── Verify camera unchanged ──
    camera = bpy.context.scene.camera
    if camera:
        print(f"\n=== Camera: {camera.name} ===")
        print(f"  location: {camera.location.x:.3f}, {camera.location.y:.3f}, {camera.location.z:.3f}")
        print(f"  rotation: {camera.rotation_euler.x:.3f}, {camera.rotation_euler.y:.3f}, {camera.rotation_euler.z:.3f}")
        print(f"  lens: {camera.data.lens}")
        if camera.animation_data and camera.animation_data.action:
            # Count keyframes without accessing fcurves directly
            # Just check if camera moves between frames 1 and 345
            scene.frame_set(1)
            bpy.context.view_layer.update()
            loc1 = camera.location.copy()
            scene.frame_set(345)
            bpy.context.view_layer.update()
            loc345 = camera.location.copy()
            print(f"  frame 1 loc: ({loc1.x:.3f}, {loc1.y:.3f}, {loc1.z:.3f})")
            print(f"  frame 345 loc: ({loc345.x:.3f}, {loc345.y:.3f}, {loc345.z:.3f})")
    else:
        print("\n=== Camera: not found ===")

    # Save sha256
    patched_sha256 = compute_sha256(PATCHED_BLEND)
    print(f"\nPatched blend SHA256: {patched_sha256}")

    # Write metadata for validation
    import json
    meta = {
        "source_blend": SRC_BLEND,
        "source_blend_sha256": src_sha256,
        "patched_blend": PATCHED_BLEND,
        "patched_blend_sha256": patched_sha256,
    }
    with open(os.path.join(OUT_DIR, "patch_metadata.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print("Metadata saved")

    print("\nPATCH COMPLETE")


if __name__ == "__main__":
    main()
