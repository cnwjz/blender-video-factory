"""
Gate step: Create temp snapshot .blend files at each event frame.
Run: blender --background scene.blend --python _gate_snapshots.py -- --frames [...] --outdir <dir>
"""
import bpy
import json
import os
import sys


def parse_args():
    frames = None
    outdir = None
    argv = sys.argv
    for i, a in enumerate(argv):
        if a == "--frames" and i + 1 < len(argv):
            frames = json.loads(argv[i + 1])
        elif a == "--outdir" and i + 1 < len(argv):
            outdir = argv[i + 1]
    return frames, outdir


def main():
    frames, outdir = parse_args()
    if frames is None or outdir is None:
        print("ERROR: missing --frames or --outdir")
        sys.exit(1)

    os.makedirs(outdir, exist_ok=True)
    scene = bpy.context.scene

    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()

        snap_path = os.path.join(outdir, f"snapshot_{frame:04d}.blend")
        bpy.ops.wm.save_mainfile(filepath=snap_path)
        print(f"  Saved snapshot {frame:04d}")

    print(f"SNAPSHOTS_CREATED={len(frames)}")


if __name__ == "__main__":
    main()
