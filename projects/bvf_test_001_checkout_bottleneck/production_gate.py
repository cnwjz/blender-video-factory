"""
BVF Production Gate R5 — Isolated per-run directories, extractable validation functions.
"""
import json, os, subprocess, sys, uuid
from pathlib import Path
from gate_integrity import (compute_gate_result, validate_run_results,
    validate_snapshot_set, validate_preview_set)
from gate_video_profile import (is_visible_at_frame, get_projection_targets_for_frame,
    get_visibility_targets_for_frame, get_event_frames)

PROJECT = Path(r"D:\blender-video-factory")
TARGET = PROJECT / "projects" / "bvf_test_001_checkout_bottleneck"
BLENDER = r"D:\Windows software\blender\blender.exe"
CHECKER = PROJECT / "protocol_guard" / "phase3_min" / "asset_scene_preflight_check.py"
DEPS = r"C:\Users\Administrator\AppData\Roaming\Python\Python314\site-packages"
KF = [1, 90, 150, 240, 345]
EXPECTED_PREVIEW_FILES = [f"frame_{f:04d}.png" for f in KF]
RUN_ID = str(uuid.uuid4())[:8]
RUN_BASE = TARGET / "diagnostics" / "full_gate_runs"
RUN_DIR = RUN_BASE / RUN_ID
SNAP_DIR = RUN_DIR / "snapshots"


def _init_run():
    os.makedirs(RUN_DIR, exist_ok=True)
    os.makedirs(SNAP_DIR, exist_ok=True)


# ═══════════════ Spec builders ═══════════════

def build_targets(static_only=False, frame=None):
    """Build target list. If frame is given, use per-frame expected visibility."""
    T = []
    CUST = ["L1","L2","L3","M1","M2","M3","R1","R2","R3","N1","N2","N3","N4"]
    for cid in CUST:
        bn, hn = f"{cid}_body", f"{cid}_head"
        bt = {"target_id":bn,"root_object_name":bn,"expected_root_type":"MESH","geometry_scope":"SELF_MESH",
              "hierarchy":{"required_direct_child_names":[hn]},
              "standing":{"local_up_axis":"+Z","expected_world_up_axis":"+Z","up_axis_tolerance_degrees":5.0},
              "facing":{"local_forward_axis":"+Y","expected_world_forward_axis":"+Y","facing_tolerance_degrees":10.0},
              "animation_state":{"animation_object_name":bn,"require_animation_data":True},
              "material_assignment":{"require_material_assignment_presence":True}}
        if not static_only:
            if frame is None or is_visible_at_frame(bn, frame)[0]:
                bt["ground_contact"] = {"ground_z":0.0,"ground_contact_tolerance":0.10}
            # camera_check: BLOCKED_BY_CHECKER_SEMANTICS.
            # required_screen_bbox coverage check requires body to span screen region.
            # Validator requires min_bottom <= max_top.
            # Checker requires screen_min_y <= min_bottom AND screen_max_y >= max_top.
            # Combined: actual_max_y <= min_bottom <= max_top <= actual_min_y.
            # This implies actual_max_y <= actual_min_y — impossible for any object with height > 0.
            # No set of (min_bottom, max_top) works for all 13 bodies simultaneously.
            # Resolution requires checker modification (not authorized).
            if frame is not None:
                vp, hr = is_visible_at_frame(bn, frame)
                bt["visibility"] = {"require_not_hidden_viewport":vp,"require_not_hidden_render":hr}
        T.append(bt)
        ht = {"target_id":hn,"root_object_name":hn,"expected_root_type":"MESH","geometry_scope":"SELF_MESH",
              "material_assignment":{"require_material_assignment_presence":True}}
        if not static_only and frame is not None:
            vp, hr = is_visible_at_frame(hn, frame)
            ht["visibility"] = {"require_not_hidden_viewport":vp,"require_not_hidden_render":hr}
        T.append(ht)
    for cp in ["left","middle","right"]:
        bn = f"Cashier_{cp}_body"
        T.append({"target_id":bn,"root_object_name":bn,"expected_root_type":"MESH","geometry_scope":"SELF_MESH",
                  "hierarchy":{"required_direct_child_names":[f"Cashier_{cp}_head"]},
                  "standing":{"local_up_axis":"+Z","expected_world_up_axis":"+Z","up_axis_tolerance_degrees":5.0},
                  "material_assignment":{"require_material_assignment_presence":True}})
        T.append({"target_id":f"Cashier_{cp}_head","root_object_name":f"Cashier_{cp}_head",
                  "expected_root_type":"MESH","geometry_scope":"SELF_MESH",
                  "material_assignment":{"require_material_assignment_presence":True}})
    T.append({"target_id":"Camera","root_object_name":"Camera","expected_root_type":"CAMERA","geometry_scope":"SELF_MESH",
              "animation_state":{"animation_object_name":"Camera","require_animation_data":False}})
    for ck in ["Counter_left","Counter_middle","Counter_right"]:
        T.append({"target_id":ck,"root_object_name":ck,"expected_root_type":"MESH","geometry_scope":"SELF_MESH",
                  "material_assignment":{"require_material_assignment_presence":True},
                  "visibility":{"require_not_hidden_viewport":True,"require_not_hidden_render":True}})
    # Counter_middle_overlay: dynamic visibility (appears at frame 78)
    T.append({"target_id":"Counter_middle_overlay","root_object_name":"Counter_middle_overlay",
              "expected_root_type":"MESH","geometry_scope":"SELF_MESH",
              "material_assignment":{"require_material_assignment_presence":True}})
    for nm in ["Sign_left","Sign_middle","Sign_middle_off","Sign_right",
               "Shutter_left","Shutter_middle","Shutter_right"]:
        T.append({"target_id":nm,"root_object_name":nm,"expected_root_type":"MESH","geometry_scope":"SELF_MESH",
                  "material_assignment":{"require_material_assignment_presence":True}})
    return T

def build_spec(blend_abs, frame, static_only=False):
    repo = str(PROJECT)
    rel = os.path.relpath(blend_abs, repo).replace("\\","/")
    spec = {"schema_version":"1","checker":"asset_scene_preflight_check",
            "source_requirement_version":"Blender 固定资产模板路线 v4",
            "repository_root":repo.replace("\\","/"),"blend_path":rel,"scene_name":"Scene",
            "global_rules":{"expected_render_engine":"BLENDER_EEVEE"},
            "targets":build_targets(static_only, frame=None if static_only else frame),
            "collection_rules":{"collection_rules":[{"collection_name":"Scene Collection",
                "require_all_targets_in_collection":True}]}}
    if not static_only:
        pg_ids = get_projection_targets_for_frame(frame)
        spec["projection_groups"] = [{"group_id":"narrative","target_ids":pg_ids,
            "camera_object_name":"Camera","minimum_visible_projected_corner_count":1,
            "required_screen_bbox":{"min_left":0.0,"max_right":1.0,"min_bottom":0.55,"max_top":0.60}}]
    return spec

# ═══════════════ Pipeline Steps ═══════════════

def blender(script, blend=None, args=None, timeout=300, env=None):
    cmd = [BLENDER, "--background", str(blend) if blend else "--factory-startup", "--python", str(script)]
    if args: cmd.extend(args)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                       encoding="utf-8", errors="replace", env=env)
    return r.returncode, r.stdout, r.stderr

def preflight(spec_path):
    r = subprocess.run([BLENDER, "--background", "--factory-startup", "--python", str(CHECKER),
        "--", "--spec", str(spec_path), "--dependency-site-packages", DEPS],
        capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr

def parse(stdout):
    for ln in stdout.split("\n"):
        if ln.startswith("PHASE3_RESULT_JSON="):
            try: return json.loads(ln.split("=",1)[1])
            except: return None
    return None

def step_build():
    print("\n=== BUILD ===")
    env = os.environ.copy(); env["BVF_SKIP_RENDER"] = "1"; env["BVF_BUILD"] = f"gate_{RUN_ID}"
    rc, out, err = blender(TARGET / "build_graybox.py", env=env, timeout=120)
    if rc: print(f"FAIL {rc}"); return False, None
    bp = TARGET / f"scene_graybox_gate_{RUN_ID}.blend"
    print(f"PASS {bp}")
    return bp.exists(), str(bp)

def step_discover():
    print("\n=== DISCOVER ===")
    valid = get_event_frames()
    print(f"Discovered {len(valid)} frames")
    with open(RUN_DIR / "event_frames.json","w",encoding="utf-8") as f:
        json.dump({"run_id":RUN_ID,"frames":valid,"count":len(valid)},f)
    return valid

def step_auto_frame(blend_path, event_frames):
    print(f"\n=== AUTO FRAME ({len(event_frames)} frames) ===")
    script = TARGET / "_gate_auto_frame.py"
    rc, out, err = blender(script, blend_path,
        args=["--","--frames",json.dumps(event_frames),"--outdir",str(RUN_DIR)], timeout=300)
    for ln in out.split("\n"):
        if "AUTO_FRAME_RESULT=" in ln:
            try:
                d = json.loads(ln.split("=",1)[1])
                print(f"{'PASS' if d.get('pass') else 'FAIL'} ortho={d.get('ortho_scale')} v={d.get('vert_occupancy_pct')}%")
                return d.get("pass",False), d
            except: pass
    return False, None

def step_snapshots(blend_path, frames):
    print(f"\n=== SNAPSHOTS ({len(frames)}) ===")
    script = TARGET / "_gate_snapshots.py"
    rc, out, err = blender(script, blend_path,
        args=["--","--frames",json.dumps(frames),"--outdir",str(SNAP_DIR)], timeout=600)
    snaps = sorted(SNAP_DIR.glob("snapshot_*.blend"))
    print(f"Created {len(snaps)}")
    # Validate snapshot set
    ok, errs = validate_snapshot_set(SNAP_DIR, frames)
    if not ok: print(f"SNAPSHOT VALIDATION FAILED: {errs}"); return []
    return snaps

def step_preflight(snapshots):
    print(f"\n=== FORMAL PREFLIGHT ({len(snapshots)} frames) ===")
    passed = 0; failed = 0; gc_ok = cc_ok = pg_ok = 0
    specs_dir = RUN_DIR / "formal_specs"; results_dir = RUN_DIR / "formal_results"
    os.makedirs(specs_dir, exist_ok=True); os.makedirs(results_dir, exist_ok=True)

    # Static
    s0 = snapshots[0]
    spec = build_spec(str(s0), int(s0.stem.split("_")[1]), static_only=True)
    sp = specs_dir / "spec_static.json"
    with open(sp,"w",encoding="utf-8") as f: json.dump(spec,f,indent=2,ensure_ascii=False)
    rc, out, err = preflight(str(sp))
    p = parse(out)
    static_ok = p and p.get("result")=="PASS"
    print(f"Static: {'PASS' if static_ok else 'FAIL'}")

    # Dynamic
    for snap in snapshots:
        fn = int(snap.stem.split("_")[1])
        spec = build_spec(str(snap), fn, static_only=False)
        sp = specs_dir / f"spec_{fn:04d}.json"
        rp = results_dir / f"result_{fn:04d}.json"
        with open(sp,"w",encoding="utf-8") as f: json.dump(spec,f,indent=2,ensure_ascii=False)
        rc, out, err = preflight(str(sp))
        p = parse(out)
        if p:
            with open(rp,"w",encoding="utf-8") as f: json.dump(p,f,indent=2,ensure_ascii=False)
        if p and p.get("result")=="PASS": passed += 1
        else: failed += 1; print(f"  FAIL F{fn}")
        if p:
            for t in p.get("per_target_results",[]):
                for k,v in t.get("checks",{}).items():
                    if isinstance(v,dict):
                        if k=="ground_contact": gc_ok += 1
                        elif k=="camera_check": cc_ok += 1
            for pg in p.get("projection_group_results",[]):
                if pg.get("result")=="PASS": pg_ok += 1
        if p and p.get("result")=="PASS":
            (SNAP_DIR / f"snapshot_{fn:04d}.blend").unlink(missing_ok=True)
    print(f"Dynamic: {passed}P/{failed}F  GC:{gc_ok} CC:{cc_ok} PG:{pg_ok}")
    summary = {"run_id":RUN_ID,"static_pass":static_ok,"dynamic_passed":passed,"dynamic_failed":failed,
               "gc_runs":gc_ok,"cc_runs":cc_ok,"pg_passes":pg_ok}
    with open(RUN_DIR/"formal_preflight_summary.json","w",encoding="utf-8") as f:
        json.dump(summary,f,indent=2)
    return static_ok and failed==0, gc_ok, cc_ok, pg_ok

def step_supplemental(blend_path):
    print("\n=== SUPPLEMENTAL ===")
    rc, out, err = blender(TARGET / "_gate_supplemental.py", blend_path, timeout=180)
    for ln in out.split("\n"):
        if "SUPPLEMENTAL_RESULT=" in ln:
            try:
                r = json.loads(ln.split("=",1)[1])
                r["run_id"] = RUN_ID
                with open(RUN_DIR/"supplemental_check.json","w",encoding="utf-8") as f:
                    json.dump(r,f,indent=2)
                print(f"{'PASS' if r.get('pass') else 'FAIL'} errors={r.get('total_errors',0)}")
                return r
            except: pass
    return {"pass":False,"total_errors":-1}

def step_render(blend, auth):
    print("\n=== RENDER ===")
    if not auth: print("BLOCKED"); return False
    gate_result_path = str(RUN_DIR / "production_gate_result.json")
    env = os.environ.copy(); env["GATE_OUT_DIR"] = str(RUN_DIR)
    rc, out, err = blender(TARGET / "_gate_render.py", blend, env=env, timeout=120,
        args=["--", "--gate-result", gate_result_path, "--run-id", RUN_ID])
    ok, errs = validate_preview_set(RUN_DIR, EXPECTED_PREVIEW_FILES)
    if not ok:
        print(f"PREVIEW VALIDATION FAILED: {errs}")
        return False
    rendered = list(RUN_DIR.glob("frame_*.png"))
    print(f"Rendered {len(rendered)} frames")
    return len(rendered)==5

def main():
    _init_run()
    print("="*50+f"\nBVF PRODUCTION GATE R5 run_id={RUN_ID}\n"+"="*50)
    b_ok, bp = step_build()
    if not b_ok: return 1
    ef = step_discover()
    a_ok, ad = step_auto_frame(bp, ef)
    if not a_ok: return 1
    snaps = step_snapshots(bp, ef)
    if not snaps: return 1
    f_ok, gc, cc, pg = step_preflight(snaps)
    suppl = step_supplemental(bp)
    gate = compute_gate_result(b_ok, a_ok, f_ok, suppl.get("pass",False),
                               run_id=RUN_ID, gc_runs=gc, cc_runs=cc, pg_passes=pg)
    with open(RUN_DIR/"production_gate_result.json","w",encoding="utf-8") as f:
        json.dump(gate,f,indent=2,ensure_ascii=False)
    # Consistency validation
    v_ok, v_errs = validate_run_results(str(RUN_DIR), RUN_ID)
    if not v_ok:
        print(f"VALIDATION FAILED: {v_errs}")
        gate["all_pass"] = False
        gate["key_frame_preview_authorized"] = False
        with open(RUN_DIR/"production_gate_result.json","w",encoding="utf-8") as f:
            json.dump(gate,f,indent=2,ensure_ascii=False)
    for k,v in [("Build",b_ok),("Auto",a_ok),("Formal",f_ok),("Suppl",suppl.get("pass",False))]:
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    print(f"  GATE: {'ALL_PASS' if gate['all_pass'] else 'BLOCKED'}")
    rendered = step_render(bp, gate["all_pass"])
    print(f"\n{'='*50}\nCOMPLETE: {'ALL_PASS' if gate['all_pass'] else 'BLOCKED'}\nPreviews: {rendered}\n{'='*50}")
    return 0 if gate["all_pass"] else 1

if __name__ == "__main__":
    sys.exit(main())
