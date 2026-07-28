"""
BVF Test 001 — Encode PNG frame sequence to MP4 preview.
Usage: python encode_preview.py

Reads existing frames from graybox_frames/, encodes H.264 MP4 to output/.
Does NOT modify frames, .blend files, or scene scripts.
"""
import subprocess
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FRAME_DIR = os.path.join(SCRIPT_DIR, "graybox_frames")
FRAME_PATTERN = os.path.join(FRAME_DIR, "frame_%04d.png")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "checkout_bottleneck_preview_v1.mp4")

# ── Source configuration (from graybox_config.json) ──────────
FPS = 30
START_FRAME = 1
END_FRAME = 345
RESOLUTION = (540, 960)

# ── FFmpeg path ──────────────────────────────────────────────
FFMPEG = r"D:\ffmpeg\ffmpeg.exe"


def verify_input():
    """Check frame directory and count before encoding."""
    if not os.path.isdir(FRAME_DIR):
        sys.exit(f"ERROR: Frame directory not found: {FRAME_DIR}")

    png_files = sorted(
        [f for f in os.listdir(FRAME_DIR) if f.startswith("frame_") and f.endswith(".png")]
    )
    if not png_files:
        sys.exit(f"ERROR: No frame_*.png files found in {FRAME_DIR}")

    first = png_files[0]
    last = png_files[-1]
    print(f"Frame dir:    {FRAME_DIR}")
    print(f"Frame count:  {len(png_files)}")
    print(f"First frame:  {first}")
    print(f"Last frame:   {last}")

    # Check for gaps
    expected = set(
        f"frame_{i:04d}.png" for i in range(START_FRAME, END_FRAME + 1)
    )
    actual = set(png_files)
    missing = expected - actual
    extra = actual - expected
    if missing:
        print(f"WARNING: Missing frames: {sorted(missing)[:10]}...")
    if extra:
        print(f"WARNING: Extra frames: {sorted(extra)[:10]}...")
    if not missing:
        print("Frame check:  ALL PRESENT (no gaps)")

    return len(png_files)


def run_ffmpeg():
    """Encode PNG sequence to H.264 MP4. Exit non-zero on failure."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    cmd = [
        FFMPEG,
        "-y",                         # overwrite output
        "-framerate", str(FPS),
        "-start_number", str(START_FRAME),
        "-i", FRAME_PATTERN,
        "-frames:v", str(END_FRAME - START_FRAME + 1),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "medium",
        "-crf", "23",
        "-movflags", "+faststart",
        OUTPUT_FILE,
    ]

    print(f"\nEncoding command:")
    print(" ".join(f'"{c}"' if " " in c else c for c in cmd))
    print()

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"FFmpeg STDERR:\n{result.stderr}")
        sys.exit(f"FFmpeg exited with code {result.returncode}")

    # Print the last few lines of stderr (FFmpeg writes info to stderr)
    stderr_tail = result.stderr.strip().split("\n")[-5:]
    for line in stderr_tail:
        print(line)

    if not os.path.isfile(OUTPUT_FILE):
        sys.exit(f"ERROR: Output file not created: {OUTPUT_FILE}")

    file_size = os.path.getsize(OUTPUT_FILE)
    if file_size == 0:
        sys.exit(f"ERROR: Output file is 0 bytes: {OUTPUT_FILE}")

    print(f"\nOutput:       {OUTPUT_FILE}")
    print(f"File size:    {file_size:,} bytes ({file_size / 1024:.1f} KB)")
    return OUTPUT_FILE


def verify_output():
    """Run ffprobe to verify codec, resolution, FPS, frame count, duration."""
    cmd = [
        r"D:\ffmpeg\ffprobe.exe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries",
        "stream=codec_name,width,height,pix_fmt,r_frame_rate,nb_frames,duration",
        "-of", "default=noprint_wrappers=1",
        OUTPUT_FILE,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"ffprobe failed: {result.stderr}")

    print("\n── ffprobe verification ──")
    print(result.stdout)

    # Decode check: read all frames, report errors
    decode_cmd = [
        FFMPEG,
        "-v", "error",
        "-i", OUTPUT_FILE,
        "-f", "null",
        "-",
    ]
    decode_result = subprocess.run(decode_cmd, capture_output=True, text=True)
    if decode_result.returncode != 0:
        print(f"DECODE CHECK FAILED: {decode_result.stderr}")
        sys.exit(1)

    errors = decode_result.stderr.strip()
    if errors:
        print(f"DECODE ERRORS: {errors}")
        sys.exit(1)

    print("Decode check: PASS (no errors)")


if __name__ == "__main__":
    print("=" * 56)
    print("BVF Test 001 — MP4 Preview Encoder")
    print("=" * 56)

    count = verify_input()
    output = run_ffmpeg()
    verify_output()

    print("\n" + "=" * 56)
    print("ENCODE COMPLETE")
    print(f"Output: {output}")
    print("=" * 56)
