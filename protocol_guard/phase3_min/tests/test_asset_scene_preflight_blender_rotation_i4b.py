"""Tests for Rotation I4B R2: real Blender mathutils validation with exact assertions."""
import ast
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

RUNNER_PATH = os.path.join(ROOT, "protocol_guard", "phase3_min", "tests", "blender_rotation_i4b_runner.py")
CHECKER_PATH = os.path.join(ROOT, "protocol_guard", "phase3_min", "asset_scene_preflight_check.py")
DEPS_PATH = r"C:\Users\Administrator\AppData\Roaming\Python\Python314\site-packages"
BLENDER_EXE = os.environ.get("BLENDER_EXE", r"D:\Windows software\blender\blender.exe")


def _blender(script, *args):
    cmd = [BLENDER_EXE, "--background", "--factory-startup", "--python", script] + list(args)
    print(f"=== BLENDER CMD: {' '.join(cmd)} ===")
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
    print(f"BLENDER RETURN_CODE: {proc.returncode}")
    print(f"BLENDER STDOUT:\n{proc.stdout}")
    print(f"BLENDER STDERR:\n{proc.stderr}")
    print("=== END BLENDER EVIDENCE ===")
    return proc


def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(65536)
            if not chunk: break
            h.update(chunk)
    return h.hexdigest()


def _run_runner():
    proc = _blender(RUNNER_PATH)
    result_line = None
    for line in proc.stdout.split("\n"):
        if line.startswith("BLENDER_ROTATION_I4B_RESULTS="):
            result_line = line[len("BLENDER_ROTATION_I4B_RESULTS="):]
            break
    results = json.loads(result_line) if result_line else []
    return results, proc.stdout, proc.stderr, proc.returncode


def _find(name, results):
    for r in results:
        if r.get("name") == name:
            return r
    return None


def _run_checker(tmpdir, spec_path):
    cmd = [
        BLENDER_EXE, "--background", "--factory-startup",
        "--python", CHECKER_PATH, "--",
        "--spec", spec_path,
        "--dependency-site-packages", DEPS_PATH,
    ]
    print(f"=== CHECKER CMD: {' '.join(cmd)} ===")
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
    print(f"CHECKER RETURN_CODE: {proc.returncode}")
    print(f"CHECKER STDOUT:\n{proc.stdout}")
    print(f"CHECKER STDERR:\n{proc.stderr}")
    result_line = None
    for line in proc.stdout.split("\n"):
        if line.startswith("PHASE3_RESULT_JSON="):
            result_line = line[len("PHASE3_RESULT_JSON="):]
            break
    result = json.loads(result_line) if result_line else None
    if result:
        print(f"CHECKER RESULT: {json.dumps(result, ensure_ascii=False)}")
    print("=== END CHECKER EVIDENCE ===")
    return result, proc


def _make_blend_script(tmpdir, object_specs):
    """Generate Blender script to create .blend with named empties at given rotations."""
    lines = [
        "import bpy",
        "bpy.ops.wm.read_homefile(use_empty=True)",
        "for obj in list(bpy.data.objects):",
        "    bpy.data.objects.remove(obj, do_unlink=True)",
    ]
    for i, spec in enumerate(object_specs):
        name, rx, ry, rz = spec[0], spec[1], spec[2], spec[3]
        lines.append(f"bpy.ops.object.add(type='EMPTY')")
        lines.append(f"obj = bpy.context.object")
        lines.append(f"obj.name = '{name}'")
        lines.append(f"obj.rotation_euler = ({rx}, {ry}, {rz})")
    lines.append("bpy.context.view_layer.update()")
    lines.append(f"bpy.ops.wm.save_as_mainfile(filepath=r'{tmpdir}/test.blend')")
    script = "\n".join(lines)
    spath = os.path.join(tmpdir, "make_blend.py")
    with open(spath, "w", encoding="utf-8") as f:
        f.write(script)
    return spath


def _make_spec(tmpdir, targets, scene_name="Scene"):
    spec = {
        "schema_version": "1", "checker": "asset_scene_preflight_check",
        "source_requirement_version": "Blender 固定资产模板路线 v4",
        "repository_root": str(tmpdir), "blend_path": "test.blend",
        "scene_name": scene_name, "targets": targets, "global_rules": {},
    }
    spath = os.path.join(str(tmpdir), "spec.json")
    with open(spath, "w", encoding="utf-8") as f:
        json.dump(spec, f)
    return spath


# ═══════════════════════════════════════════════════════════════════════
# Runner tests — exact assertions on structured JSON
# ═══════════════════════════════════════════════════════════════════════

class TestI4BBlenderRunner:

    @classmethod
    def setup_class(cls):
        cls.results, cls.stdout, cls.stderr, cls.rc = _run_runner()
        print("=== BLENDER RUNNER EVIDENCE ===")
        print(f"RETURN_CODE: {cls.rc}")
        print(f"STDOUT:\n{cls.stdout}")
        print(f"STDERR:\n{cls.stderr}")
        print("=== END BLENDER RUNNER EVIDENCE ===")

    def test_blender_exit_zero(self):
        assert self.rc == 0, f"exit={self.rc}\nstderr:\n{self.stderr}"

    def test_results_count(self):
        assert len(self.results) == 18, f"got {len(self.results)}"

    # ── q/-q ──────────────────────────────────────────────────

    def test_q_neg_q_non_trivial(self):
        r = _find("q_neg_q_non_trivial", self.results)
        assert abs(r["angle"]) < 0.001, f"angle={r['angle']} not ~0"
        # Verify q and -q are component-wise negation
        for i in range(4):
            assert abs(r["q"][i] + r["neg_q"][i]) < 0.001, f"q[{i}]={r['q'][i]}, nq[{i}]={r['neg_q'][i]}"
        # Verify quaternion is non-trivial (not identity)
        assert abs(r["q"][0] - 0.9239) < 0.01, f"q.w={r['q'][0]} should be ~0.9239"

    # ── Identity ──────────────────────────────────────────────

    def test_identity_PASS(self):
        r = _find("identity_0deg", self.results)
        assert r["result"] == "PASS"
        assert abs(r["angle"]) < 0.001
        assert r["actual_quat"] == [1.0, 0.0, 0.0, 0.0]
        assert r["expected_quat"] == [1.0, 0.0, 0.0, 0.0]

    # ── 90° rotations ─────────────────────────────────────────

    def test_rot_x_90_PASS(self):
        r = _find("rot_x_90", self.results)
        assert r["result"] == "PASS"
        assert abs(r["angle"]) < 0.001
        aq = r["actual_quat"]
        assert abs(aq[0] - 0.7071) < 0.001, f"aq.w={aq[0]}"
        assert abs(aq[1] - 0.7071) < 0.001, f"aq.x={aq[1]}"
        assert abs(aq[2]) < 0.001, f"aq.y={aq[2]}"
        assert abs(aq[3]) < 0.001, f"aq.z={aq[3]}"
        eq = r["expected_quat"]
        assert abs(eq[0] - 0.7071) < 0.001, f"eq.w={eq[0]}"
        assert abs(eq[1] - 0.7071) < 0.001, f"eq.x={eq[1]}"
        assert abs(eq[2]) < 0.001, f"eq.y={eq[2]}"
        assert abs(eq[3]) < 0.001, f"eq.z={eq[3]}"

    def test_rot_y_90_PASS(self):
        r = _find("rot_y_90", self.results)
        assert r["result"] == "PASS"
        assert abs(r["angle"]) < 0.001
        aq = r["actual_quat"]
        assert abs(aq[0] - 0.7071) < 0.001, f"aq.w={aq[0]}"
        assert abs(aq[1]) < 0.001, f"aq.x={aq[1]}"
        assert abs(aq[2] - 0.7071) < 0.001, f"aq.y={aq[2]}"
        assert abs(aq[3]) < 0.001, f"aq.z={aq[3]}"
        eq = r["expected_quat"]
        assert abs(eq[0] - 0.7071) < 0.001, f"eq.w={eq[0]}"
        assert abs(eq[1]) < 0.001, f"eq.x={eq[1]}"
        assert abs(eq[2] - 0.7071) < 0.001, f"eq.y={eq[2]}"
        assert abs(eq[3]) < 0.001, f"eq.z={eq[3]}"

    def test_rot_z_90_PASS(self):
        r = _find("rot_z_90", self.results)
        assert r["result"] == "PASS"
        assert abs(r["angle"]) < 0.001
        aq = r["actual_quat"]
        assert abs(aq[0] - 0.7071) < 0.001, f"aq.w={aq[0]}"
        assert abs(aq[1]) < 0.001, f"aq.x={aq[1]}"
        assert abs(aq[2]) < 0.001, f"aq.y={aq[2]}"
        assert abs(aq[3] - 0.7071) < 0.001, f"aq.z={aq[3]}"
        eq = r["expected_quat"]
        assert abs(eq[0] - 0.7071) < 0.001, f"eq.w={eq[0]}"
        assert abs(eq[1]) < 0.001, f"eq.x={eq[1]}"
        assert abs(eq[2]) < 0.001, f"eq.y={eq[2]}"
        assert abs(eq[3] - 0.7071) < 0.001, f"eq.z={eq[3]}"

    # ── Uniform scale ─────────────────────────────────────────

    def test_uniform_scale_2_PASS(self):
        r = _find("uniform_scale_2", self.results)
        assert r["result"] == "PASS"
        assert abs(r["angle"]) < 0.1
        assert r["actual_quat"] == [1.0, 0.0, 0.0, 0.0]

    def test_uniform_scale_05_PASS(self):
        r = _find("uniform_scale_05", self.results)
        assert r["result"] == "PASS"
        assert abs(r["angle"]) < 0.1
        assert r["actual_quat"] == [1.0, 0.0, 0.0, 0.0]

    # ── Non-uniform scale ─────────────────────────────────────

    def test_nonuniform_scale(self):
        r = _find("nonuniform_scale", self.results)
        assert r["result"] == "PASS"
        assert r["angle"] == 0.0
        assert r["actual_quat"] == [1.0, 0.0, 0.0, 0.0]

    # ── Negative scale ────────────────────────────────────────

    def test_negative_scale(self):
        r = _find("negative_scale", self.results)
        assert r["result"] == "PASS"
        assert r["angle"] == 0.0
        assert r["actual_quat"] == [1.0, 0.0, 0.0, 0.0]

    # ── Shear ─────────────────────────────────────────────────

    def test_shear_x_to_y_FAIL(self):
        r = _find("shear_x_to_y", self.results)
        assert r["result"] == "FAIL"
        assert 13.09 < r["angle"] < 13.11, f"angle={r['angle']}"
        assert r["failure_code"] == "OBJECT_ROTATION_OUT_OF_TOLERANCE"
        aq = r["actual_quat"]
        assert abs(aq[0] - 0.99347) < 0.0001, f"aq.w={aq[0]}"
        assert abs(aq[1] - 0.0) < 0.0001, f"aq.x={aq[1]}"
        assert abs(aq[2] - 0.0) < 0.0001, f"aq.y={aq[2]}"
        assert abs(aq[3] + 0.11408) < 0.0001, f"aq.z={aq[3]}"

    def test_shear_y_to_z_FAIL(self):
        r = _find("shear_y_to_z", self.results)
        assert r["result"] == "FAIL"
        assert 13.09 < r["angle"] < 13.11, f"angle={r['angle']}"
        assert r["failure_code"] == "OBJECT_ROTATION_OUT_OF_TOLERANCE"
        aq = r["actual_quat"]
        assert abs(aq[0] - 0.99347) < 0.0001, f"aq.w={aq[0]}"
        assert abs(aq[1] + 0.11408) < 0.0001, f"aq.x={aq[1]}"
        assert abs(aq[2] - 0.0) < 0.0001, f"aq.y={aq[2]}"
        assert abs(aq[3] - 0.0) < 0.0001, f"aq.z={aq[3]}"

    # ── X reflection ──────────────────────────────────────────

    def test_x_reflection_FAIL(self):
        r = _find("x_reflection", self.results)
        assert r["result"] == "FAIL"
        assert 179.99 < r["angle"] < 180.01, f"angle={r['angle']}"
        assert r["failure_code"] == "OBJECT_ROTATION_OUT_OF_TOLERANCE"
        aq = r["actual_quat"]
        # x_reflection produces q ≈ [0, -1, 0, 0] (or equivalent [0, 1, 0, 0])
        assert abs(aq[0]) < 0.001, f"aq.w={aq[0]}"
        assert abs(abs(aq[1]) - 1.0) < 0.001, f"aq.x={aq[1]}"
        assert abs(aq[2]) < 0.001, f"aq.y={aq[2]}"
        assert abs(aq[3]) < 0.001, f"aq.z={aq[3]}"

    # ── Tolerance boundaries ──────────────────────────────────

    def test_angle_lt_tol_PASS(self):
        r = _find("angle_lt_tol", self.results)
        assert r["result"] == "PASS"
        assert 2.99 < r["angle"] < 3.01, f"angle={r['angle']}"
        assert "failure_code" not in r
        aq = r["actual_quat"]
        # 3deg X rotation: q = [cos(1.5deg), sin(1.5deg), 0, 0]
        assert abs(aq[0] - 0.99966) < 0.0001, f"aq.w={aq[0]}"
        assert abs(aq[1] - 0.02618) < 0.0001, f"aq.x={aq[1]}"
        assert abs(aq[2]) < 0.0001, f"aq.y={aq[2]}"
        assert abs(aq[3]) < 0.0001, f"aq.z={aq[3]}"

    def test_angle_eq_tol_PASS_and_angle_close_to_tolerance(self):
        r = _find("angle_eq_tol", self.results)
        assert r["result"] == "PASS"
        assert 4.99 < r["angle"] < 5.01, f"angle={r['angle']} not ~5.0"
        aq = r["actual_quat"]
        assert abs(aq[0] - 0.99905) < 0.0001, f"aq.w={aq[0]}"
        assert abs(aq[1] - 0.04362) < 0.0001, f"aq.x={aq[1]}"
        assert abs(aq[2]) < 0.0001, f"aq.y={aq[2]}"
        assert abs(aq[3]) < 0.0001, f"aq.z={aq[3]}"

    def test_angle_gt_tol_FAIL(self):
        r = _find("angle_gt_tol", self.results)
        assert r["result"] == "FAIL"
        assert 9.99 < r["angle"] < 10.01, f"angle={r['angle']}"
        assert r["failure_code"] == "OBJECT_ROTATION_OUT_OF_TOLERANCE"
        aq = r["actual_quat"]
        assert abs(aq[0] - 0.99619) < 0.0001, f"aq.w={aq[0]}"
        assert abs(aq[1] - 0.08716) < 0.0001, f"aq.x={aq[1]}"
        assert abs(aq[2]) < 0.0001, f"aq.y={aq[2]}"
        assert abs(aq[3]) < 0.0001, f"aq.z={aq[3]}"

    # ── 180° ──────────────────────────────────────────────────

    def test_angle_180deg_FAIL(self):
        r = _find("angle_180deg", self.results)
        assert r["result"] == "FAIL"
        assert 179.99 < r["angle"] < 180.01, f"angle={r['angle']}"
        assert r["failure_code"] == "OBJECT_ROTATION_OUT_OF_TOLERANCE"
        aq = r["actual_quat"]
        # 180deg X rotation: q ≈ [0, 1, 0, 0]
        assert abs(aq[0]) < 0.001, f"aq.w={aq[0]}"
        assert abs(aq[1] - 1.0) < 0.001, f"aq.x={aq[1]}"
        assert abs(aq[2]) < 0.001, f"aq.y={aq[2]}"
        assert abs(aq[3]) < 0.001, f"aq.z={aq[3]}"

    # ── NOT_CHECKED ───────────────────────────────────────────

    def test_not_checked_null(self):
        r = _find("not_checked_null", self.results)
        assert r["result"] == "NOT_CHECKED"

    def test_not_checked_missing(self):
        r = _find("not_checked_missing", self.results)
        assert r["result"] == "NOT_CHECKED"


# ═══════════════════════════════════════════════════════════════════════
# Entry-point tests via production checker subprocess
# ═══════════════════════════════════════════════════════════════════════

class TestEntryPointRotation:

    def test_rotation_pass_via_entry(self, tmp_path):
        blend_script = _make_blend_script(str(tmp_path), [("T", 0, 0, 0)])
        r = _blender(blend_script)
        print(f"=== BLEND CREATE: returncode={r.returncode} ===")
        assert r.returncode == 0

        bp = os.path.join(str(tmp_path), "test.blend")
        before_sha = _sha256(bp)
        print(f"BLEND SHA256 BEFORE: {before_sha}")
        spec = _make_spec(str(tmp_path), [{
            "target_id": "t1", "root_object_name": "T",
            "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
            "rotation": {"expected_world_rotation_euler_degrees": [0, 0, 0],
                         "rotation_tolerance_degrees": 0.5},
        }])
        result, proc = _run_checker(str(tmp_path), spec)
        assert result is not None, f"no result\n{proc.stdout}\n{proc.stderr}"
        assert result["result"] == "PASS", f"got {result['result']}"
        rot = result["per_target_results"][0]["checks"]["rotation"]
        assert rot["result"] == "PASS"
        assert abs(rot["angle_degrees"]) < 0.001
        after_sha = _sha256(bp)
        print(f"BLEND SHA256 AFTER: {after_sha}")
        assert after_sha == before_sha, ".blend SHA256 changed"

    def test_rotation_fail_via_entry(self, tmp_path):
        blend_script = _make_blend_script(str(tmp_path), [("T", 1.5708, 0, 0)])
        r = _blender(blend_script)
        assert r.returncode == 0

        bp = os.path.join(str(tmp_path), "test.blend")
        before_sha = _sha256(bp)
        print(f"BLEND SHA256 BEFORE: {before_sha}")
        spec = _make_spec(str(tmp_path), [{
            "target_id": "t1", "root_object_name": "T",
            "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
            "rotation": {"expected_world_rotation_euler_degrees": [0, 0, 0],
                         "rotation_tolerance_degrees": 5.0},
        }])
        result, proc = _run_checker(str(tmp_path), spec)
        assert result
        assert result["result"] == "FAIL"
        rot = result["per_target_results"][0]["checks"]["rotation"]
        assert rot["result"] == "FAIL"
        assert rot["failure_code"] == "OBJECT_ROTATION_OUT_OF_TOLERANCE"
        assert 89.9 < rot["angle_degrees"] < 90.1, f"angle={rot['angle_degrees']}"
        after_sha = _sha256(bp)
        print(f"BLEND SHA256 AFTER: {after_sha}")
        assert after_sha == before_sha

    def test_rotation_not_checked_via_entry(self, tmp_path):
        blend_script = _make_blend_script(str(tmp_path), [("T", 0, 0, 0)])
        r = _blender(blend_script)
        assert r.returncode == 0

        spec = _make_spec(str(tmp_path), [{
            "target_id": "t1", "root_object_name": "T",
            "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
        }])
        result, proc = _run_checker(str(tmp_path), spec)
        assert result
        rot = result["per_target_results"][0]["checks"]["rotation"]
        assert rot["result"] == "NOT_CHECKED"


# ═══════════════════════════════════════════════════════════════════════
# Multi-check: Standing + Facing + Rotation — at least one FAIL
# ═══════════════════════════════════════════════════════════════════════

class TestMultiCheck:

    def test_standing_facing_rotation_one_fail(self, tmp_path):
        # Rotate 90° X — Rotation will FAIL, Standing and Facing should PASS
        blend_script = _make_blend_script(str(tmp_path), [("MT", 1.5708, 0, 0)])
        r = _blender(blend_script)
        assert r.returncode == 0

        bp = os.path.join(str(tmp_path), "test.blend")
        before_sha = _sha256(bp)
        print(f"BLEND SHA256 BEFORE: {before_sha}")
        spec = _make_spec(str(tmp_path), [{
            "target_id": "mt1", "root_object_name": "MT",
            "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
            "standing": {"local_up_axis": "+Z", "expected_world_up_axis": "+Z",
                         "up_axis_tolerance_degrees": 10.0},
            "facing": {"local_forward_axis": "+Y", "expected_world_forward_axis": "+Y",
                       "facing_tolerance_degrees": 10.0},
            "rotation": {"expected_world_rotation_euler_degrees": [0, 0, 0],
                         "rotation_tolerance_degrees": 5.0},
        }])
        result, proc = _run_checker(str(tmp_path), spec)
        assert result, f"no result\n{proc.stdout}\n{proc.stderr}"
        checks = result["per_target_results"][0]["checks"]

        # All three must be present
        assert "standing" in checks, f"missing standing in {list(checks.keys())}"
        assert "facing" in checks, f"missing facing"
        assert "rotation" in checks, f"missing rotation"

        # Standing: +Z→+Z on 90° X rotation → FAIL
        st = checks["standing"]["up_axis"]
        assert st["result"] == "FAIL", f"standing expected FAIL, got {st['result']}: angle={st.get('angle_degrees')}"
        assert 89.9 < st["angle_degrees"] < 90.1, f"standing angle={st['angle_degrees']}"

        # Facing: +Y→+Y on 90° X rotation → FAIL
        fa = checks["facing"]["forward_axis"]
        assert fa["result"] == "FAIL", f"facing expected FAIL, got {fa['result']}: angle={fa.get('angle_degrees')}"
        assert 89.9 < fa["angle_degrees"] < 90.1, f"facing angle={fa['angle_degrees']}"

        # Rotation: 90° X vs expected 0° → FAIL
        rot = checks["rotation"]
        assert rot["result"] == "FAIL", f"rotation expected FAIL, got {rot['result']}"
        assert rot["failure_code"] == "OBJECT_ROTATION_OUT_OF_TOLERANCE"
        assert 89.9 < rot["angle_degrees"] < 90.1, f"rotation angle={rot['angle_degrees']}"

        # Overall aggregation: FAIL (any FAIL → overall FAIL)
        assert result["result"] == "FAIL", f"overall expected FAIL, got {result['result']}"
        assert result["per_target_results"][0]["overall"] == "FAIL"

        after_sha = _sha256(bp)
        print(f"BLEND SHA256 AFTER: {after_sha}")
        assert after_sha == before_sha, ".blend SHA256 changed"


# ═══════════════════════════════════════════════════════════════════════
# Self-integrity
# ═══════════════════════════════════════════════════════════════════════

def test_runner_file_parseable():
    with open(RUNNER_PATH, encoding="utf-8") as f:
        ast.parse(f.read())


def test_test_file_self_parse():
    with open(__file__, encoding="utf-8") as f:
        ast.parse(f.read())


def test_test_file_no_skip_xfail():
    with open(__file__, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = None
            if isinstance(node.func, ast.Attribute): name = node.func.attr
            elif isinstance(node.func, ast.Name): name = node.func.id
            if name in ("skip", "skipif", "xfail", "importorskip"):
                raise AssertionError(f"line {node.lineno}: {name}()")
