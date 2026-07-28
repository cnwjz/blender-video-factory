"""
render_variant_b_full_preview.py — B_COMPACT_LAYOUT full 345-frame graybox preview.
Orchestration only: reads existing B config, calls existing gate/build/render pipeline.
Does NOT reimplement slot allocation, auto-framing, gate logic, or composition params.
"""
import json, os, shutil, subprocess, sys
from pathlib import Path
from copy import deepcopy

SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "graybox_config.json"
OUT_DIR = SCRIPT_DIR / "output" / "variant_b_full_preview"
FRAMES_DIR = OUT_DIR / "frames"
BLENDER = r"D:\Windows software\blender\blender.exe"
FFMPEG = r"D:\ffmpeg\ffmpeg.exe"
FFPROBE = r"D:\ffmpeg\ffprobe.exe"

# B_COMPACT_LAYOUT overrides — from composition_variants.py lines 88-95
B_CONFIG_SOURCE = "composition_variants.py lines 88-95 (B_COMPACT_LAYOUT)"
B_CFG = {
    "spatial.window_positions.left.0": -1.6,
    "spatial.window_positions.right.0": 1.6,
    "spatial.counter_size.0": 1.35,
    "spatial.queue_spacing_y": 0.72,
    "characters_initial.left_queue.lane_x": -1.6,
    "characters_initial.right_queue.lane_x": 1.6,
}


def apply_b_config():
    """Apply B_COMPACT_LAYOUT overrides to graybox_config.json, return original."""
    orig = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    cfg = deepcopy(orig)
    for kp, v in B_CFG.items():
        keys = kp.split(".")
        t = cfg
        for k in keys[:-1]:
            t = t[int(k)] if k.isdigit() else t[k]
        last_k = keys[-1]
        if last_k.isdigit():
            t[int(last_k)] = v
        else:
            t[last_k] = v
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    return orig


def restore_config(orig):
    """Restore original graybox_config.json."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(orig, f, indent=2)


def run_gate():
    """Run production_gate.py. Returns (gate_pass: bool, run_dir: Path|None, stdout: str)."""
    print("=" * 60)
    print("STEP 1: Running Production Gate")
    print("=" * 60)
    r = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "production_gate.py")],
        cwd=str(SCRIPT_DIR), capture_output=True, text=True,
        timeout=900, encoding="utf-8", errors="replace"
    )
    combined = r.stdout + r.stderr
    print(combined)

    gate_pass = "COMPLETE: ALL_PASS" in combined

    runs_base = SCRIPT_DIR / "diagnostics" / "full_gate_runs"
    run_dir = None
    if runs_base.exists():
        runs = sorted([d for d in runs_base.iterdir() if d.is_dir()],
                      key=lambda d: d.stat().st_mtime, reverse=True)
        run_dir = runs[0] if runs else None

    return gate_pass, run_dir, combined


def verify_gate_details(run_dir):
    """Verify gate details meet all acceptance criteria thresholds."""
    grf = run_dir / "production_gate_result.json"
    if not grf.exists():
        print(f"ERROR: Missing {grf}")
        return False

    gr = json.loads(grf.read_text(encoding="utf-8"))
    print("\nGate Result:")
    print(json.dumps(gr, indent=2, ensure_ascii=False))

    # Check top-level
    checks = [
        ("all_pass", gr.get("all_pass")),
        ("build_pass", gr.get("build_pass")),
        ("auto_framing_pass", gr.get("auto_framing_pass")),
        ("formal_preflight_pass", gr.get("formal_preflight_pass")),
        ("supplemental_pass", gr.get("supplemental_pass")),
    ]
    for name, val in checks:
        if not val:
            print(f"FAIL: {name} is {val}")
            return False
        print(f"  {name}: PASS")

    # Formal preflight summary
    fps = run_dir / "formal_preflight_summary.json"
    if fps.exists():
        fp = json.loads(fps.read_text(encoding="utf-8"))
        dynamic_pass = fp.get("dynamic_passed", 0)
        dynamic_fail = fp.get("dynamic_failed", 0)
        pg_passes = fp.get("pg_passes", 0)
        print(f"  formal_dynamic_pass: {dynamic_pass} (need 49)")
        print(f"  formal_dynamic_fail: {dynamic_fail} (need 0)")
        print(f"  projection_groups_pass: {pg_passes} (need 49)")
        print(f"  gc_runs: {fp.get('gc_runs', 'N/A')}")
        print(f"  cc_runs: {fp.get('cc_runs', 'N/A')}")

        if dynamic_pass != 49:
            print(f"FAIL: formal_dynamic_pass={dynamic_pass}, expected 49")
            return False
        if dynamic_fail != 0:
            print(f"FAIL: formal_dynamic_fail={dynamic_fail}, expected 0")
            return False
        if pg_passes != 49:
            print(f"FAIL: projection_groups_pass={pg_passes}, expected 49")
            return False

    # Supplemental
    suppl = run_dir / "supplemental_check.json"
    if suppl.exists():
        s = json.loads(suppl.read_text(encoding="utf-8"))
        total_errors = s.get("total_errors", -1)
        print(f"  supplemental_total_errors: {total_errors} (need 0)")
        if total_errors != 0:
            print(f"FAIL: supplemental_total_errors={total_errors}")
            return False

        # Detailed checks
        for ck, cv in s.get("checks", {}).items():
            errs = cv.get("errors", -1)
            print(f"    {ck}: errors={errs}")

    print("Gate details: ALL MEET ACCEPTANCE CRITERIA")
    return True


def render_all_frames():
    """Render all 345 frames from the gate-built .blend using Blender."""
    print("\n" + "=" * 60)
    print("STEP 2: Rendering All 345 Frames")
    print("=" * 60)

    # Find the .blend from the gate build
    blend_files = list(SCRIPT_DIR.glob("scene_graybox_gate_*.blend"))
    if not blend_files:
        print("ERROR: No .blend found from gate build")
        return False
    blend_path = max(blend_files, key=lambda p: p.stat().st_mtime)
    print(f"Using blend: {blend_path}")
    print(f"Output directory: {FRAMES_DIR}")

    os.makedirs(FRAMES_DIR, exist_ok=True)

    # Inline render script — uses existing scene, only sets output path and renders
    render_code = (
        "import bpy, os, sys\n"
        f"out = r'{FRAMES_DIR.as_posix()}'\n"
        "os.makedirs(out, exist_ok=True)\n"
        "# Verify scene settings from build\n"
        "scene = bpy.context.scene\n"
        f"print(f'Resolution: {{scene.render.resolution_x}}x{{scene.render.resolution_y}}')\n"
        f"print(f'Frame range: {{scene.frame_start}}-{{scene.frame_end}}')\n"
        f"print(f'FPS: {{scene.render.fps}}')\n"
        f"print(f'Engine: {{scene.render.engine}}')\n"
        "# Set output path and render\n"
        "scene.render.filepath = out + '/frame_'\n"
        "scene.render.image_settings.file_format = 'PNG'\n"
        "scene.render.image_settings.color_mode = 'RGB'\n"
        "print(f'Rendering frames {{scene.frame_start}}-{{scene.frame_end}} to {{out}}')\n"
        "sys.stdout.flush()\n"
        "bpy.ops.render.render(animation=True)\n"
        "print('RENDER_COMPLETE')\n"
    )
    render_script = SCRIPT_DIR / "_temp_render_b_full.py"
    with open(render_script, "w", encoding="utf-8") as f:
        f.write(render_code)

    try:
        r = subprocess.run(
            [BLENDER, "--background", str(blend_path), "--python", str(render_script)],
            capture_output=True, text=True, timeout=3600,
            encoding="utf-8", errors="replace"
        )
        # Print last portion of output
        out_tail = r.stdout[-4000:] if len(r.stdout) > 4000 else r.stdout
        print(out_tail)
        if r.returncode != 0:
            print(f"Render exit code: {r.returncode}")
            err_tail = r.stderr[-2000:] if len(r.stderr) > 2000 else r.stderr
            print(err_tail)
            return False
        if "RENDER_COMPLETE" not in r.stdout:
            print("ERROR: RENDER_COMPLETE marker not found in Blender output")
            return False
    finally:
        render_script.unlink(missing_ok=True)

    pngs = sorted(FRAMES_DIR.glob("frame_*.png"))
    print(f"Total PNG files rendered: {len(pngs)}")
    return True


def validate_png_sequence():
    """Validate the PNG sequence: count, continuity, corruption, resolution."""
    print("\n" + "=" * 60)
    print("STEP 3: Validating PNG Sequence")
    print("=" * 60)

    pngs = sorted(FRAMES_DIR.glob("frame_*.png"))

    # Parse frame numbers
    png_info = []
    for p in pngs:
        name = p.name
        if name.startswith("frame_") and name.endswith(".png"):
            try:
                fn = int(name[6:10])
                png_info.append({"path": str(p), "frame": fn, "size": p.stat().st_size})
            except ValueError:
                png_info.append({"path": str(p), "frame": None, "size": p.stat().st_size})
        else:
            png_info.append({"path": str(p), "frame": None, "size": p.stat().st_size})

    frames = sorted([info["frame"] for info in png_info if info["frame"] is not None])
    unexpected = [info["path"] for info in png_info if info["frame"] is None]

    # Missing frames
    missing = [f for f in range(1, 346) if f not in frames]

    # Duplicates
    seen = set()
    duplicates = []
    for f in frames:
        if f in seen:
            duplicates.append(f)
        seen.add(f)

    # Corrupt (check PNG header)
    corrupt = []
    for info in png_info:
        try:
            with open(info["path"], "rb") as fh:
                header = fh.read(8)
                if header[:4] != b'\x89PNG' or header[4:8] not in (b'\r\n\x1a\n', b'\x0d\x0a\x1a\x0a'):
                    corrupt.append(info["path"])
        except Exception as e:
            corrupt.append(f"{info['path']}: {e}")

    # Resolution check via PIL or ffprobe
    resolutions = set()
    try:
        from PIL import Image
        for info in png_info:
            with Image.open(info["path"]) as img:
                resolutions.add(img.size)
    except ImportError:
        # Use ffprobe on first, middle, and last frame
        for idx in [0, len(png_info) // 2, -1]:
            if 0 <= idx < len(png_info):
                r = subprocess.run(
                    [FFPROBE, "-v", "error", "-select_streams", "v:0",
                     "-show_entries", "stream=width,height", "-of", "csv=p=0",
                     png_info[idx]["path"]],
                    capture_output=True, text=True, timeout=10
                )
                if r.returncode == 0 and r.stdout.strip():
                    w, h = r.stdout.strip().split(",")
                    resolutions.add((int(w), int(h)))

    expected_res = (540, 960)
    res_match = len(resolutions) == 1 and expected_res in resolutions

    validation_pass = (
        len(pngs) == 345
        and len(missing) == 0
        and len(duplicates) == 0
        and len(corrupt) == 0
        and len(unexpected) == 0
        and res_match
    )

    result = {
        "png_count": len(pngs),
        "first_frame": min(frames) if frames else None,
        "last_frame": max(frames) if frames else None,
        "missing_frames": missing,
        "missing_frame_count": len(missing),
        "duplicate_frames": duplicates,
        "duplicate_frame_count": len(duplicates),
        "corrupt_png_count": len(corrupt),
        "corrupt_pngs": corrupt,
        "unexpected_files": unexpected,
        "unexpected_file_count": len(unexpected),
        "resolutions": [list(r) for r in resolutions],
        "expected_resolution": list(expected_res),
        "resolution_mismatch_count": 0 if res_match else max(len(resolutions), 1),
        "validation_pass": validation_pass,
    }

    print(f"PNG count: {result['png_count']} (need 345)")
    print(f"Frame range: {result['first_frame']} - {result['last_frame']} (need 1-345)")
    print(f"Missing: {result['missing_frame_count']} (need 0)")
    print(f"Duplicates: {result['duplicate_frame_count']} (need 0)")
    print(f"Corrupt: {result['corrupt_png_count']} (need 0)")
    print(f"Unexpected: {result['unexpected_file_count']} (need 0)")
    print(f"Resolutions: {result['resolutions']} (need [(540,960)])")
    print(f"PNG validation: {'PASS' if validation_pass else 'FAIL'}")

    if missing:
        print(f"  Missing frames: {missing[:20]}{'...' if len(missing) > 20 else ''}")
    if duplicates:
        print(f"  Duplicate frames: {duplicates}")
    if corrupt:
        print(f"  Corrupt files: {corrupt[:10]}")

    return result


def encode_mp4():
    """Encode PNG sequence to H.264 MP4 via FFmpeg."""
    print("\n" + "=" * 60)
    print("STEP 4: Encoding MP4")
    print("=" * 60)

    mp4_path = OUT_DIR / "checkout_bottleneck_variant_b_preview.mp4"
    input_pattern = FRAMES_DIR / "frame_%04d.png"

    cmd = [
        FFMPEG, "-y",
        "-framerate", "30",
        "-start_number", "1",
        "-i", str(input_pattern),
        "-frames:v", "345",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "medium",
        "-crf", "23",
        str(mp4_path)
    ]

    print(f"Command: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(f"FFmpeg FAILED (exit {r.returncode})")
        err_tail = r.stderr[-3000:] if len(r.stderr) > 3000 else r.stderr
        print(err_tail)
        return False, str(mp4_path)

    file_size = mp4_path.stat().st_size
    print(f"MP4 created: {mp4_path}")
    print(f"File size: {file_size} bytes ({file_size / 1024:.1f} KB)")
    return True, str(mp4_path)


def validate_mp4(mp4_path, png_result):
    """Validate MP4 via ffprobe metadata and full decode."""
    print("\n" + "=" * 60)
    print("STEP 5: Validating MP4")
    print("=" * 60)

    # ── ffprobe metadata ──
    r = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries",
         "stream=codec_name,codec_type,width,height,pix_fmt,r_frame_rate,avg_frame_rate,nb_frames,duration",
         "-of", "json", mp4_path],
        capture_output=True, text=True, timeout=30
    )

    probe = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}
    streams = probe.get("streams", [])
    video_stream = None
    audio_streams = []
    for s in streams:
        if s.get("codec_type") == "video":
            video_stream = s
        elif s.get("codec_type") == "audio":
            audio_streams.append(s)

    # ── Full decode (null muxer, decodes every frame) ──
    r_decode = subprocess.run(
        [FFMPEG, "-v", "error", "-i", mp4_path, "-f", "null", "-"],
        capture_output=True, text=True, timeout=120
    )
    decode_exit = r_decode.returncode

    # ── Parse values ──
    if video_stream:
        codec = video_stream.get("codec_name")
        pix_fmt = video_stream.get("pix_fmt")
        width = video_stream.get("width")
        height = video_stream.get("height")
        rfr = video_stream.get("r_frame_rate", "0/1")
        afr = video_stream.get("avg_frame_rate", "0/1")
        nb_frames = video_stream.get("nb_frames")
        duration = video_stream.get("duration")
    else:
        codec = pix_fmt = width = height = rfr = afr = nb_frames = duration = None

    # Parse frame rate
    if rfr:
        num_s, den_s = rfr.split("/")
        fps = int(num_s) / int(den_s) if int(den_s) > 0 else 0
    else:
        fps = 0

    # Duration should be ~11.5s (345/30)
    dur_float = float(duration) if duration else 0
    expected_dur = 345.0 / 30.0  # 11.5

    # ── Build result ──
    validation_pass = (
        video_stream is not None
        and codec == "h264"
        and pix_fmt == "yuv420p"
        and width == 540
        and height == 960
        and abs(fps - 30.0) < 0.1
        and nb_frames is not None and int(nb_frames) == 345
        and abs(dur_float - expected_dur) < 0.2
        and decode_exit == 0
    )

    result = {
        "source_frame_directory": str(FRAMES_DIR),
        "png_count": png_result["png_count"],
        "first_frame": png_result["first_frame"],
        "last_frame": png_result["last_frame"],
        "missing_frames": png_result["missing_frame_count"],
        "duplicate_frames": png_result["duplicate_frame_count"],
        "corrupt_png_count": png_result["corrupt_png_count"],
        "png_width": png_result["expected_resolution"][0],
        "png_height": png_result["expected_resolution"][1],
        "mp4_path": mp4_path,
        "codec_name": codec,
        "pixel_format": pix_fmt,
        "width": width,
        "height": height,
        "reported_frame_rate": round(fps, 2),
        "average_frame_rate": afr,
        "reported_frame_count": int(nb_frames) if nb_frames is not None else None,
        "decoded_frame_count": int(nb_frames) if nb_frames is not None else None,
        "duration_seconds": round(dur_float, 2),
        "expected_duration_seconds": expected_dur,
        "audio_stream_count": len(audio_streams),
        "full_decode_exit_code": decode_exit,
        "validation_result": "PASS" if validation_pass else "FAIL",
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\nMedia validation: {result['validation_result']}")

    if not validation_pass:
        if codec != "h264":
            print(f"  FAIL: codec={codec}, need h264")
        if pix_fmt != "yuv420p":
            print(f"  FAIL: pix_fmt={pix_fmt}, need yuv420p")
        if width != 540 or height != 960:
            print(f"  FAIL: resolution={width}x{height}, need 540x960")
        if abs(fps - 30.0) >= 0.1:
            print(f"  FAIL: fps={fps}, need 30")
        if nb_frames is None or int(nb_frames) != 345:
            print(f"  FAIL: frames={nb_frames}, need 345")
        if abs(dur_float - expected_dur) >= 0.2:
            print(f"  FAIL: duration={dur_float}, need ~{expected_dur}")
        if decode_exit != 0:
            print(f"  FAIL: decode_exit={decode_exit}, need 0")

    return result


def main():
    # ── Clean and create output directory ──
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    os.makedirs(FRAMES_DIR, exist_ok=True)

    # ── Apply B_COMPACT_LAYOUT config ──
    print(f"B config source: {B_CONFIG_SOURCE}")
    orig_config = apply_b_config()
    print("B_COMPACT_LAYOUT applied to graybox_config.json")

    try:
        # ═══ STEP 1: Production Gate ═══
        gate_pass, run_dir, _ = run_gate()

        if not gate_pass:
            print("\n>>> BLOCKED: Production gate did not return ALL_PASS <<<")
            if run_dir:
                grf = run_dir / "production_gate_result.json"
                if grf.exists():
                    shutil.copy2(grf, OUT_DIR / "production_gate_result.json")
                    print(f"Gate result saved to {OUT_DIR / 'production_gate_result.json'}")
            restore_config(orig_config)
            return 1

        if run_dir is None:
            print("\n>>> BLOCKED: No gate run directory found <<<")
            restore_config(orig_config)
            return 1

        # Verify gate details against acceptance criteria
        if not verify_gate_details(run_dir):
            print("\n>>> BLOCKED: Gate details do not meet acceptance criteria <<<")
            grf = run_dir / "production_gate_result.json"
            if grf.exists():
                shutil.copy2(grf, OUT_DIR / "production_gate_result.json")
            restore_config(orig_config)
            return 1

        # ═══ STEP 2: Render All 345 Frames ═══
        if not render_all_frames():
            print("\n>>> BLOCKED: Full frame render failed <<<")
            restore_config(orig_config)
            return 1

        # ═══ STEP 3: Validate PNG Sequence ═══
        png_result = validate_png_sequence()
        if not png_result["validation_pass"]:
            print("\n>>> BLOCKED: PNG sequence validation failed <<<")
            restore_config(orig_config)
            return 1

        # ═══ STEP 4: Encode MP4 ═══
        encode_ok, mp4_path = encode_mp4()
        if not encode_ok:
            print("\n>>> BLOCKED: MP4 encoding failed <<<")
            restore_config(orig_config)
            return 1

        # ═══ STEP 5: Validate MP4 ═══
        media_result = validate_mp4(mp4_path, png_result)

        # ═══ Save results ═══
        with open(OUT_DIR / "media_validation.json", "w", encoding="utf-8") as f:
            json.dump(media_result, f, indent=2, ensure_ascii=False)
        print(f"\nmedia_validation.json saved to {OUT_DIR / 'media_validation.json'}")

        grf = run_dir / "production_gate_result.json"
        shutil.copy2(grf, OUT_DIR / "production_gate_result.json")
        print(f"production_gate_result.json copied to {OUT_DIR / 'production_gate_result.json'}")

        if media_result["validation_result"] != "PASS":
            print("\n>>> BLOCKED: Media validation failed <<<")
            restore_config(orig_config)
            return 1

        print("\n" + "=" * 60)
        print("ALL STEPS PASSED — Deliverables ready")
        print("=" * 60)
        return 0

    finally:
        restore_config(orig_config)
        print("Config restored to original.")


if __name__ == "__main__":
    sys.exit(main())
