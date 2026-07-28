"""
Gate step: Render 5 key frame previews.
Authorization: --gate-result <path> --run-id <id> (CLI only, no env fallback).
"""
import os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from gate_integrity import authorize_preview_render

FRAMES = [1, 90, 150, 240, 345]


def parse_args():
    gate_result, run_id = None, None
    argv = sys.argv
    for i, a in enumerate(argv):
        if a == "--gate-result" and i + 1 < len(argv):
            gate_result = argv[i + 1]
        elif a == "--run-id" and i + 1 < len(argv):
            run_id = argv[i + 1]
    return gate_result, run_id


def check_authorization(gate_result_path, run_id):
    """Check authorization via gate_integrity.authorize_preview_render."""
    if not gate_result_path or not run_id:
        print("RENDER BLOCKED: missing --gate-result or --run-id")
        return False
    authorized, reason = authorize_preview_render(gate_result_path, run_id)
    if not authorized:
        print(f"RENDER BLOCKED: {reason}")
        return False
    return True


def render_previews(out_dir):
    import bpy
    os.makedirs(out_dir, exist_ok=True)
    scene = bpy.context.scene
    scene.render.resolution_x = 540
    scene.render.resolution_y = 960
    scene.render.image_settings.file_format = 'PNG'
    for frame in FRAMES:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        out = os.path.join(out_dir, f"frame_{frame:04d}.png")
        scene.render.filepath = out
        bpy.ops.render.render(write_still=True)
        print(f"  Rendered: {out}")
    print(f"RENDER_COMPLETE={len(FRAMES)}")


def main():
    gate_result_path, run_id = parse_args()
    if not check_authorization(gate_result_path, run_id):
        sys.exit(1)
    out_dir = os.environ.get("GATE_OUT_DIR",
        os.path.join(SCRIPT_DIR, "diagnostics", "full_gate_v1_r2"))
    render_previews(out_dir)


if __name__ == "__main__":
    main()
