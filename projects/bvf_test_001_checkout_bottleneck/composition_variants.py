"""Composition variants — run 3 config variants through gate."""
import json, os, shutil, subprocess, sys
from pathlib import Path
from copy import deepcopy

SCRIPT_DIR = Path(__file__).parent
OUT_BASE = SCRIPT_DIR / "diagnostics" / "composition_variants_v1"
CONFIG_PATH = SCRIPT_DIR / "graybox_config.json"

os.makedirs(OUT_BASE, exist_ok=True)
ORIG_CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def run_variant(name, cfg_overrides):
    out_dir = OUT_BASE / name
    os.makedirs(out_dir, exist_ok=True)

    # Write variant config
    cfg = deepcopy(ORIG_CONFIG)
    for kp, v in cfg_overrides.items():
        keys = kp.split(".")
        t = cfg
        for k in keys[:-1]: t = t[int(k)] if k.isdigit() else t[k]
        t[keys[-1]] = v
    vcfg = SCRIPT_DIR / f"graybox_config_{name}.json"
    with open(vcfg, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

    # Swap config
    CONFIG_PATH.rename(SCRIPT_DIR / "graybox_config_tmp.json")
    vcfg.rename(CONFIG_PATH)

    try:
        r = subprocess.run([sys.executable, str(SCRIPT_DIR / "production_gate.py")],
                          cwd=str(SCRIPT_DIR), capture_output=True, text=True,
                          timeout=900, encoding="utf-8", errors="replace")
        combined = r.stdout + r.stderr
        gate_pass = "COMPLETE: ALL_PASS" in combined

        # Find latest run
        runs = sorted(
            [d for d in (SCRIPT_DIR / "diagnostics" / "full_gate_runs").iterdir() if d.is_dir()],
            key=lambda d: d.stat().st_mtime, reverse=True)
        run_dir = runs[0] if runs else None

        # Copy outputs
        previews = 0
        for f in ["frame_0001.png","frame_0090.png","frame_0150.png","frame_0240.png","frame_0345.png"]:
            src = run_dir / f if run_dir else None
            if src and src.exists():
                shutil.copy2(src, out_dir / f); previews += 1

        for jf in ["production_gate_result.json","supplemental_check.json","formal_preflight_summary.json"]:
            src = run_dir / jf if run_dir else None
            if src and src.exists(): shutil.copy2(src, out_dir / jf)

        # Metrics
        m = {"gate_pass": gate_pass, "preview_count": previews}
        grf = run_dir / "production_gate_result.json" if run_dir else None
        if grf and grf.exists():
            gr = json.loads(grf.read_text(encoding="utf-8"))
            m["formal_pass"] = gr.get("formal_preflight_pass")
            m["suppl_pass"] = gr.get("supplemental_pass")
            cam = gr.get("camera", {})
            m.update({f"camera_{k}": v for k, v in cam.items()})

        sf = run_dir / "supplemental_check.json" if run_dir else None
        if sf and sf.exists():
            s = json.loads(sf.read_text(encoding="utf-8"))
            m["suppl_total_errors"] = s.get("total_errors", -1)

        return m, gate_pass, previews
    finally:
        # Restore
        if CONFIG_PATH.exists(): CONFIG_PATH.unlink()
        tmp = SCRIPT_DIR / "graybox_config_tmp.json"
        if tmp.exists(): tmp.rename(CONFIG_PATH)


# Run all 3 variants
results = {}

print("=== A: CAMERA ONLY (baseline) ===")
results["A"], a_ok, a_pv = run_variant("A_CAMERA_ONLY", {})
print(f"  Gate={a_ok} Previews={a_pv}")

print("=== B: COMPACT LAYOUT ===")
b_cfg = {
    "spatial.window_positions.left.0": -1.6,
    "spatial.window_positions.right.0": 1.6,
    "spatial.counter_size.0": 1.35,
    "spatial.queue_spacing_y": 0.72,
    "characters_initial.left_queue.lane_x": -1.6,
    "characters_initial.right_queue.lane_x": 1.6,
}
results["B"], b_ok, b_pv = run_variant("B_COMPACT_LAYOUT", b_cfg)
print(f"  Gate={b_ok} Previews={b_pv}")

print("=== C: CHARACTER FOCUS ===")
c_cfg = dict(b_cfg)
c_cfg.update({
    "spatial.character_radius": 0.18,
    "spatial.character_height": 1.7,
    "spatial.queue_spacing_y": 0.68,
})
results["C"], c_ok, c_pv = run_variant("C_CHARACTER_FOCUS", c_cfg)
print(f"  Gate={c_ok} Previews={c_pv}")

# Summary
summary = {"variants": results}
with open(OUT_BASE / "composition_variants_summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)
print(f"\nDone. Summary: {OUT_BASE / 'composition_variants_summary.json'}")
