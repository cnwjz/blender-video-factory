"""Tests for 14B-3B I3B FINAL_CORRECTION_R1."""
import os, sys, json, subprocess, tempfile, hashlib, textwrap, math

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, PROJECT_ROOT)

BLENDER = r"D:\Windows software\blender\blender.exe"
DEPS = r"C:\Users\Administrator\AppData\Local\Temp\bpy_yaml"
ENTRY = os.path.join(PROJECT_ROOT, "protocol_guard", "phase3_min",
                     "asset_scene_preflight_check.py")

_r = subprocess.run([BLENDER, "--version"], capture_output=True, text=True,
                     encoding="utf-8", errors="replace")
assert "5.1.2" in (_r.stdout or "") + (_r.stderr or ""), "Wrong Blender"


def _log_subprocess(purpose, wdir, cmd, rc, stdout, stderr, prefix, line_count):
    print(f"\n{'='*60}")
    print(f"PROCESS_PURPOSE: {purpose}")
    print(f"WORKING_DIRECTORY: {wdir}")
    print(f"COMMAND: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    print(f"RETURN_CODE: {rc}")
    print(f"STDOUT_BEGIN\n{stdout}\nSTDOUT_END")
    print(f"STDERR_BEGIN\n{stderr}\nSTDERR_END")
    print(f"RESULT_PREFIX: {prefix}")
    print(f"RESULT_LINE_COUNT: {line_count}")
    print(f"{'='*60}\n")


def _sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def _run_facing_check(purpose, scene_name, targets, blend_path):
    td = tempfile.mkdtemp(prefix="facing_i3b_")
    try:
        spec = {
            "schema_version": "1", "checker": "asset_scene_preflight_check",
            "source_requirement_version": "Blender 固定资产模板路线 v4",
            "repository_root": td,
            "blend_path": os.path.basename(blend_path),
            "scene_name": scene_name, "global_rules": {},
            "targets": targets,
        }
        spec_path = os.path.join(td, "spec.json")
        with open(spec_path, "w") as f:
            json.dump(spec, f)
        import shutil
        dest = os.path.join(td, os.path.basename(blend_path))
        shutil.copy2(blend_path, dest)
        sha_before = _sha256(dest)
        cmd = [BLENDER, "--background", "--factory-startup",
               "--python", ENTRY, "--",
               "--spec", spec_path, "--dependency-site-packages", DEPS]
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120)
        lines = [L for L in (r.stdout or "").splitlines() if L.startswith("PHASE3_RESULT_JSON=")]
        _log_subprocess(purpose, td, cmd, r.returncode, r.stdout, r.stderr,
                        "PHASE3_RESULT_JSON=", len(lines))
        sha_after = _sha256(dest)
        assert sha_before == sha_after, "SHA256 changed"
        assert len(lines) == 1, f"Expected 1 PHASE3_RESULT_JSON, got {len(lines)}"
        assert r.returncode != 0 or lines, "returncode 0 but no result line"
        result = json.loads(lines[0].split("=", 1)[1])
        return r.returncode, result
    finally:
        shutil.rmtree(td, ignore_errors=True)


def _get_facing_internal(purpose, blend_path):
    td = tempfile.mkdtemp(prefix="facing_int_")
    try:
        dest = os.path.join(td, os.path.basename(blend_path))
        import shutil
        shutil.copy2(blend_path, dest)
        script = textwrap.dedent(f"""
        import sys, os, json
        sys.path.insert(0, r"{PROJECT_ROOT}")
        sys.path.insert(0, r"{DEPS}")
        import bpy, mathutils
        bpy.ops.wm.open_mainfile(filepath=r'{dest}')
        scene = bpy.context.scene
        root_obj = None
        for obj in scene.objects:
            if obj.name == 'R':
                root_obj = obj; break
        assert root_obj is not None
        from protocol_guard.phase3_min.blender_scene_reader import _check_root_objects
        target_spec = {{
            "target_id": "A",
            "root_object_name": "R",
            "expected_root_type": "EMPTY",
            "geometry_scope": "SELF_MESH",
            "facing": {{
                "local_forward_axis": "+Y",
                "expected_world_forward_axis": "+Y",
                "facing_tolerance_degrees": 5.0
            }}
        }}
        targets = [target_spec]
        results = _check_root_objects(scene, targets)
        t = results[0]
        output = {{
            "overall": t["overall"],
            "facing": t["checks"]["facing"],
        }}
        print("I3B_FACING_INTERNAL_JSON=" + json.dumps(output, ensure_ascii=False, separators=(",",":")))
        """)
        cmd = [BLENDER, "--background", "--factory-startup", "--python-expr", script]
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
        lines = [L for L in (r.stdout or "").splitlines() if L.startswith("I3B_FACING_INTERNAL_JSON=")]
        _log_subprocess(purpose, td, "blender --background --factory-startup --python-expr ...",
                        r.returncode, r.stdout, r.stderr, "I3B_FACING_INTERNAL_JSON=", len(lines))
        assert r.returncode == 0, f"Internal subprocess failed: rc={r.returncode}"
        assert len(lines) == 1, f"Expected 1 I3B_FACING_INTERNAL_JSON, got {len(lines)}"
        return json.loads(lines[0].split("=", 1)[1])
    finally:
        shutil.rmtree(td, ignore_errors=True)


def _assert_fail_structure(fa, label, expected_local, expected_world,
                            expected_direction, expected_angle, expected_tolerance,
                            expected_failure_code="FACING_FORWARD_AXIS_DEVIATION"):
    assert fa["result"] == "FAIL", f"{label}: result != FAIL"
    assert fa["failure_code"] == expected_failure_code, f"{label}: wrong failure_code"
    assert fa["local_forward_axis"] == expected_local, f"{label}: wrong local"
    assert fa["expected_world_forward_axis"] == expected_world, f"{label}: wrong expected"
    d = fa["actual_world_forward_direction"]
    for i, exp in enumerate(expected_direction):
        assert abs(d[i] - exp) < 0.001, f"{label}: direction[{i}]={d[i]} != {exp}"
    assert abs(fa["angle_degrees"] - expected_angle) < 0.01, f"{label}: wrong angle"
    assert fa["tolerance_degrees"] == expected_tolerance, f"{label}: wrong tolerance"


def _make_facing_target(local, expected, tol, root_name="R", root_type="EMPTY"):
    return {
        "target_id": "A", "root_object_name": root_name,
        "expected_root_type": root_type, "geometry_scope": "SELF_MESH",
        "facing": {"local_forward_axis": local,
                    "expected_world_forward_axis": expected,
                    "facing_tolerance_degrees": tol},
    }


def _setup_blend(matrix_rotation_deg=None, matrix_scale=None):
    td = tempfile.mkdtemp(prefix="facing_blend_")
    bp = os.path.join(td, "test.blend")
    mw_code = "mw = mathutils.Matrix.Identity(4)"
    if matrix_rotation_deg:
        mw_code = f"mw = mathutils.Matrix.Rotation(math.radians({matrix_rotation_deg}), 4, 'X')"
    if matrix_scale:
        mw_code = f"mw = mathutils.Matrix.Diagonal({matrix_scale})"
    script = textwrap.dedent(f"""
    import bpy, mathutils, math
    bpy.ops.wm.read_factory_settings(use_empty=True)
    obj = bpy.data.objects.new('R', None)
    obj.empty_display_type = 'PLAIN_AXES'
    bpy.context.scene.collection.objects.link(obj)
    {mw_code}
    obj.matrix_world = mw
    bpy.ops.wm.save_as_mainfile(filepath=r'{bp}')
    """)
    r = subprocess.run([BLENDER, "--background", "--factory-startup",
                         "--python-expr", script],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=60)
    assert r.returncode == 0, f"setup_blend failed: {r.stderr}"
    return bp


# ═══════════════ Tests ══════════════════════════════════════════════════


class TestPass:
    def test_identity_zero_angle(self):
        """F-001: 0deg PASS. Identity matrix: +Y->+Y, angle=0, tol=0."""
        bp = _setup_blend(matrix_rotation_deg=0)
        rc, result = _run_facing_check("F-001 identity 0deg", "Scene",
                                        [_make_facing_target("+Y", "+Y", 0.0)], bp)
        assert rc == 0
        assert result["result"] == "PASS"
        t = result["per_target_results"][0]
        assert t["overall"] == "PASS"
        fa = t["checks"]["facing"]["forward_axis"]
        assert fa["result"] == "PASS"
        assert fa["local_forward_axis"] == "+Y"
        assert fa["expected_world_forward_axis"] == "+Y"
        d = fa["actual_world_forward_direction"]
        assert d == [0.0, 1.0, 0.0], f"direction={d}"
        assert fa["angle_degrees"] == 0.0
        assert fa["tolerance_degrees"] == 0.0
        assert "failure_code" not in fa
        os.unlink(bp)

    def test_within_tolerance(self):
        """F-002: 3deg X-rot, tol=5, PASS with direction~=(0,cos3,sin3)."""
        bp = _setup_blend(matrix_rotation_deg=3)
        rc, result = _run_facing_check("F-002 within tol 3deg", "Scene",
                                        [_make_facing_target("+Y", "+Y", 5.0)], bp)
        assert rc == 0
        assert result["result"] == "PASS"
        t = result["per_target_results"][0]
        assert t["overall"] == "PASS"
        fa = t["checks"]["facing"]["forward_axis"]
        assert fa["result"] == "PASS"
        assert fa["local_forward_axis"] == "+Y"
        assert fa["expected_world_forward_axis"] == "+Y"
        d = fa["actual_world_forward_direction"]
        c3, s3 = math.cos(math.radians(3)), math.sin(math.radians(3))
        assert abs(d[0]-0.0)<0.001 and abs(d[1]-c3)<0.001 and abs(d[2]-s3)<0.001
        assert abs(fa["angle_degrees"] - 3.0) < 0.01
        assert fa["tolerance_degrees"] == 5.0
        os.unlink(bp)

    def test_equal_tolerance_strict(self):
        """F-003: Equal tolerance strict. angle==tolerance, strict ==."""
        bp = _setup_blend(matrix_rotation_deg=10)
        rc1, result1 = _run_facing_check("F-003 step1", "Scene",
                                          [_make_facing_target("+Y", "+Y", 99.0)], bp)
        assert rc1 == 0
        exact_angle = result1["per_target_results"][0]["checks"]["facing"]["forward_axis"]["angle_degrees"]
        assert exact_angle > 0

        rc2, result2 = _run_facing_check("F-003 step2", "Scene",
                                          [_make_facing_target("+Y", "+Y", exact_angle)], bp)
        assert rc2 == 0
        assert result2["result"] == "PASS"
        t = result2["per_target_results"][0]
        assert t["overall"] == "PASS"
        fa = t["checks"]["facing"]["forward_axis"]
        assert fa["result"] == "PASS"
        assert fa["local_forward_axis"] == "+Y"
        assert fa["expected_world_forward_axis"] == "+Y"
        c10, s10 = math.cos(math.radians(10)), math.sin(math.radians(10))
        d = fa["actual_world_forward_direction"]
        assert abs(d[0]-0.0)<0.001 and abs(d[1]-c10)<0.001 and abs(d[2]-s10)<0.001
        assert fa["angle_degrees"] == fa["tolerance_degrees"], (
            f"angle={fa['angle_degrees']} != tol={fa['tolerance_degrees']}")
        os.unlink(bp)

    def test_nonuniform_scale_normalizes(self):
        """F-006: Non-uniform (2,3,4) normalizes to +Y, angle=0."""
        bp = _setup_blend(matrix_scale=(2, 3, 4, 1))
        rc, result = _run_facing_check("F-006 nonuniform scale", "Scene",
                                        [_make_facing_target("+Y", "+Y", 1.0)], bp)
        assert rc == 0
        assert result["result"] == "PASS"
        t = result["per_target_results"][0]
        assert t["overall"] == "PASS"
        fa = t["checks"]["facing"]["forward_axis"]
        assert fa["result"] == "PASS"
        assert fa["local_forward_axis"] == "+Y"
        assert fa["expected_world_forward_axis"] == "+Y"
        d = fa["actual_world_forward_direction"]
        assert abs(d[0]-0.0)<0.001 and abs(d[1]-1.0)<0.001 and abs(d[2]-0.0)<0.001
        norm = (d[0]**2 + d[1]**2 + d[2]**2) ** 0.5
        assert abs(norm - 1.0) < 1e-6
        assert fa["angle_degrees"] == 0.0
        assert fa["tolerance_degrees"] == 1.0
        os.unlink(bp)


class TestFail:
    def test_exceeds_tolerance(self):
        """F-004: 10deg X-rot, tol=5 -> FAIL, dir~=(0,cos10,sin10)."""
        bp = _setup_blend(matrix_rotation_deg=10)
        rc, result = _run_facing_check("F-004 exceeds tol", "Scene",
                                        [_make_facing_target("+Y", "+Y", 5.0)], bp)
        assert rc == 1
        assert result["result"] == "FAIL"
        t = result["per_target_results"][0]
        assert t["overall"] == "FAIL"
        fa = t["checks"]["facing"]["forward_axis"]
        c10, s10 = math.cos(math.radians(10)), math.sin(math.radians(10))
        _assert_fail_structure(fa, "F-004", "+Y", "+Y", (0.0, c10, s10), 10.0, 5.0)
        os.unlink(bp)

    def test_90deg_rotation(self):
        """F-005: 90deg X-rot, tol=5 -> FAIL, dir~=(0,0,1)."""
        bp = _setup_blend(matrix_rotation_deg=90)
        rc, result = _run_facing_check("F-005 90deg", "Scene",
                                        [_make_facing_target("+Y", "+Y", 5.0)], bp)
        assert rc == 1
        assert result["result"] == "FAIL"
        t = result["per_target_results"][0]
        assert t["overall"] == "FAIL"
        fa = t["checks"]["facing"]["forward_axis"]
        _assert_fail_structure(fa, "F-005", "+Y", "+Y", (0.0, 0.0, 1.0), 90.0, 5.0)
        os.unlink(bp)

    def test_negative_scale_flip(self):
        """F-007: Neg Y scale -> +Y flipped to -Y, angle=180, FAIL."""
        bp = _setup_blend(matrix_scale=(1, -1, 1, 1))
        rc, result = _run_facing_check("F-007 neg scale", "Scene",
                                        [_make_facing_target("+Y", "+Y", 5.0)], bp)
        assert rc == 1
        assert result["result"] == "FAIL"
        t = result["per_target_results"][0]
        assert t["overall"] == "FAIL"
        fa = t["checks"]["facing"]["forward_axis"]
        _assert_fail_structure(fa, "F-007", "+Y", "+Y", (0.0, -1.0, 0.0), 180.0, 5.0)
        assert fa["actual_world_forward_direction"] == [0.0, -1.0, 0.0]
        assert fa["angle_degrees"] == 180.0
        os.unlink(bp)


class TestError:
    def test_zero_scale_error_and_internal_structure(self):
        """F-008: Zero Y scale -> NORMALIZE_WORLD_FORWARD_AXIS ERROR."""
        bp = _setup_blend(matrix_scale=(1, 0, 1, 1))

        rc, result = _run_facing_check("F-008 entry", "Scene",
                                        [_make_facing_target("+Y", "+Y", 5.0)], bp)
        assert rc == 2
        assert result["result"] == "ERROR"
        errs = result.get("input_errors", [])
        facing_errs = [e for e in errs if "FACING_FORWARD_AXIS_ERROR" in e]
        assert len(facing_errs) == 1
        assert "NORMALIZE_WORLD_FORWARD_AXIS" in facing_errs[0]
        assert "target 'A'" in facing_errs[0]
        assert "root_object_name 'R'" in facing_errs[0]

        # F-008 entry-level per R5: per_target_results is always [] for ERROR
        assert result["per_target_results"] == [], (
            f"per_target_results should be empty for ERROR, got {result.get('per_target_results')}")

        # F-008 internal: verify via _check_root_objects
        internal = _get_facing_internal("F-008 internal", bp)
        assert internal["overall"] == "ERROR", f"target overall={internal['overall']}"
        assert internal["facing"]["result"] == "ERROR"
        fa = internal["facing"]["forward_axis"]
        assert fa["result"] == "ERROR"
        assert fa["error_type"] == "FACING_FORWARD_AXIS_ERROR"
        assert fa["operation"] == "NORMALIZE_WORLD_FORWARD_AXIS"
        assert fa["note"] == "ZERO_LENGTH_FORWARD_VECTOR"
        assert set(fa.keys()) == {"result", "error_type", "operation", "note"}, (
            f"Unexpected keys: {set(fa.keys())}")
        for forbidden in ["local_forward_axis", "expected_world_forward_axis",
                          "actual_world_forward_direction", "angle_degrees",
                          "tolerance_degrees", "failure_code"]:
            assert forbidden not in fa, f"ERROR forward_axis contains {forbidden}"
        os.unlink(bp)

    def test_zero_scale_blend_unchanged(self):
        """F-009: .blend SHA256 unchanged after ERROR check."""
        bp = _setup_blend(matrix_scale=(1, 0, 1, 1))
        sha_before = _sha256(bp)
        rc, _ = _run_facing_check("F-009 blend integrity", "Scene",
                                   [_make_facing_target("+Y", "+Y", 5.0)], bp)
        sha_after = _sha256(bp)
        assert rc == 2
        assert sha_before == sha_after, ".blend was modified"
        os.unlink(bp)
