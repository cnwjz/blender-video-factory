"""Tests for Blender entry point + scene basic reader.

These tests run via subprocess to Blender 5.1.2.
No bpy import at module level — bpy is only used inside Blender subprocesses.
"""

import json, os, subprocess, sys, tempfile, hashlib
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
BLENDER_EXE = r"D:\Windows software\blender\blender.exe"
CHECKER_SCRIPT = os.path.join(PROJECT_ROOT, "protocol_guard", "phase3_min", "asset_scene_preflight_check.py")


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk: break
            h.update(chunk)
    return h.hexdigest()


def _make_test_blend(tmp_dir, blend_name, scene_name="Scene", render_engine="BLENDER_EEVEE", objects=None):
    """Create a minimal .blend via Blender subprocess. Returns path.

    objects: optional list of dicts with 'name' and 'type' keys (e.g. 'EMPTY', 'MESH').
    """
    obj_lines = ""
    if objects:
        for obj_spec in objects:
            oname = obj_spec["name"]
            otype = obj_spec["type"]
            if otype == "MESH":
                obj_lines += f'''
mesh = bpy.data.meshes.new("{oname}_mesh")
obj = bpy.data.objects.new("{oname}", mesh)
'''
            else:
                obj_lines += f'''
obj = bpy.data.objects.new("{oname}", None)
'''
            obj_lines += '''
scene.collection.objects.link(obj)
'''
    script = f'''
import bpy
scene = bpy.context.scene
scene.name = "{scene_name}"
scene.render.engine = "{render_engine}"
{obj_lines}
bpy.ops.wm.save_as_mainfile(filepath=r"{os.path.join(tmp_dir, blend_name)}")
'''
    sf = os.path.join(tmp_dir, "make_blend.py")
    with open(sf, "w") as f: f.write(script)
    r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf],
                       capture_output=True, text=True)
    os.unlink(sf)
    assert r.returncode == 0, f"Blend creation failed: {r.stderr}"
    return os.path.join(tmp_dir, blend_name)


def _make_test_blend_with_children(tmp_dir, blend_name, scene_name="Scene",
                                   render_engine="BLENDER_EEVEE", root_objects=None,
                                   children_map=None):
    """Create a .blend with objects and optional parent-child relationships.

    root_objects: list of {"name": str, "type": str}
    children_map: dict of parent_name -> [{"name": str, "type": str}]
    Uses indexed variable names to support dots/special chars in object names.
    """
    idx = [0]
    def next_var():
        v = f"o{idx[0]}"
        idx[0] += 1
        return v

    obj_lines = ""
    root_vars = {}
    if root_objects:
        for obj_spec in root_objects:
            v = next_var()
            root_vars[obj_spec["name"]] = v
            oname = obj_spec["name"]
            otype = obj_spec["type"]
            if otype == "MESH":
                obj_lines += f'''
mesh = bpy.data.meshes.new("{oname}_mesh")
{v} = bpy.data.objects.new("{oname}", mesh)
'''
            else:
                obj_lines += f'''
{v} = bpy.data.objects.new("{oname}", None)
'''
            obj_lines += f'''
scene.collection.objects.link({v})
'''
    # Create children and set parents
    child_vars = []
    if children_map:
        for parent_name, child_specs in children_map.items():
            pv = root_vars.get(parent_name, parent_name)
            for cs in child_specs:
                cname = cs["name"]
                ctype = cs.get("type", "EMPTY")
                v = next_var()
                if ctype == "MESH":
                    obj_lines += f'''
mesh = bpy.data.meshes.new("{cname}_mesh")
{v} = bpy.data.objects.new("{cname}", mesh)
'''
                else:
                    obj_lines += f'''
{v} = bpy.data.objects.new("{cname}", None)
'''
                obj_lines += f'''
scene.collection.objects.link({v})
{v}.parent = {pv}
'''
    script = f'''
import bpy
scene = bpy.context.scene
scene.name = "{scene_name}"
scene.render.engine = "{render_engine}"
{obj_lines}
bpy.ops.wm.save_as_mainfile(filepath=r"{os.path.join(tmp_dir, blend_name)}")
'''
    sf = os.path.join(tmp_dir, "make_blend.py")
    with open(sf, "w") as f: f.write(script)
    r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf],
                       capture_output=True, text=True)
    os.unlink(sf)
    assert r.returncode == 0, f"Blend creation failed: {r.stderr}"
    return os.path.join(tmp_dir, blend_name)


def _make_two_scene_blend(tmp_dir, blend_name, target_scene="TargetScene", other_scene="OtherScene",
                          other_objects=None):
    """Create a .blend with two scenes. Objects go into other_scene. Returns path."""
    obj_lines = ""
    if other_objects:
        for obj_spec in other_objects:
            oname = obj_spec["name"]
            otype = obj_spec["type"]
            if otype == "MESH":
                obj_lines += f'''
mesh = bpy.data.meshes.new("{oname}_mesh")
obj = bpy.data.objects.new("{oname}", mesh)
'''
            else:
                obj_lines += f'''
obj = bpy.data.objects.new("{oname}", None)
'''
            obj_lines += '''
scene2.collection.objects.link(obj)
'''
    script = f'''
import bpy
scene1 = bpy.context.scene
scene1.name = "{target_scene}"
scene1.render.engine = "BLENDER_EEVEE"
bpy.ops.scene.new(type='NEW')
scene2 = bpy.context.scene
scene2.name = "{other_scene}"
scene2.render.engine = "BLENDER_EEVEE"
{obj_lines}
bpy.ops.wm.save_as_mainfile(filepath=r"{os.path.join(tmp_dir, blend_name)}")
'''
    sf = os.path.join(tmp_dir, "make_blend.py")
    with open(sf, "w") as f: f.write(script)
    r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf],
                       capture_output=True, text=True)
    os.unlink(sf)
    assert r.returncode == 0, f"Blend creation failed: {r.stderr}"
    return os.path.join(tmp_dir, blend_name)


def _make_spec_file(tmp_dir, **overrides):
    """Write a minimal valid spec to tmp_dir/spec.json. Returns path."""
    spec = {
        "schema_version": "1",
        "checker": "asset_scene_preflight_check",
        "source_requirement_version": "Blender 固定资产模板路线 v4",
        "repository_root": tmp_dir.replace("\\", "/"),
        "blend_path": overrides.pop("blend_path", "test.blend"),
        "scene_name": overrides.pop("scene_name", "Scene"),
        "targets": [
            {"target_id": "T", "root_object_name": "r", "expected_root_type": "EMPTY",
             "geometry_scope": "SELF_MESH"}
        ],
        "global_rules": {},
    }
    spec_name = overrides.pop("_spec_name", "spec.json")
    spec.update(overrides)
    sf = os.path.join(tmp_dir, spec_name)
    with open(sf, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False)
    return sf


DEPS_SITE = r"C:\Users\Administrator\AppData\Roaming\Python\Python314\site-packages"


def _run_checker(spec_path):
    """Run the checker via Blender. Returns (exit_code, stdout, stderr, result_line)."""
    r = subprocess.run(
        [BLENDER_EXE, "--background", "--factory-startup",
         "--python", CHECKER_SCRIPT, "--",
         "--spec", spec_path,
         "--dependency-site-packages", DEPS_SITE],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    lines = r.stdout.split("\n")
    result_lines = [l for l in lines if l.startswith("PHASE3_RESULT_JSON=")]
    result_line = result_lines[0] if len(result_lines) == 1 else None
    line_count = len(result_lines)
    return (r.returncode, r.stdout, r.stderr, result_line, line_count)


# ════════════════════ Tests ════════════════════

class TestSceneBasicPass:
    def test_scene_exists_render_engine_match(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                             objects=[{"name": "r", "type": "EMPTY"}])
            sf = _make_spec_file(td.name, scene_rules={"expected_render_engine": "BLENDER_EEVEE"})
            rc, stdout, stderr, rline, lcount = _run_checker(sf)
            assert rc == 0
            assert lcount == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "PASS"
            sb = result["global_results"]["scene_basic"]
            assert sb["scene_exists"]["result"] == "PASS"
            assert sb["render_engine"]["result"] == "PASS"
        finally:
            td.cleanup()

    def test_scene_exists_no_render_engine_spec(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                             objects=[{"name": "r", "type": "EMPTY"}])
            sf = _make_spec_file(td.name)
            rc, stdout, stderr, rline, lcount = _run_checker(sf)
            assert rc == 0
            assert lcount == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "PASS"
            sb = result["global_results"]["scene_basic"]
            assert sb["render_engine"]["result"] == "NOT_CHECKED"
            assert sb["render_engine"]["note"] == "NO_EXPECTED_RENDER_ENGINE"
        finally:
            td.cleanup()


class TestSceneBasicFail:
    def test_scene_not_found(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend(td.name, "test.blend", "ExistingScene", "BLENDER_EEVEE")
            sf = _make_spec_file(td.name, scene_name="NonExistentScene")
            rc, stdout, stderr, rline, lcount = _run_checker(sf)
            assert rc == 1
            assert lcount == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "FAIL"
            sb = result["global_results"]["scene_basic"]
            assert sb["scene_exists"]["result"] == "FAIL"
            assert sb["scene_exists"]["failure_code"] == "SCENE_NOT_FOUND"
        finally:
            td.cleanup()

    def test_render_engine_mismatch(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend(td.name, "test.blend", "Scene", "CYCLES",
                             objects=[{"name": "r", "type": "EMPTY"}])
            sf = _make_spec_file(td.name, scene_rules={"expected_render_engine": "BLENDER_EEVEE"})
            rc, stdout, stderr, rline, lcount = _run_checker(sf)
            assert rc == 1
            assert lcount == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "FAIL"
            sb = result["global_results"]["scene_basic"]
            assert sb["render_engine"]["result"] == "FAIL"
            assert sb["render_engine"]["failure_code"] == "RENDER_ENGINE_MISMATCH"
            assert sb["render_engine"]["expected"] == "BLENDER_EEVEE"
            assert sb["render_engine"]["actual"] == "CYCLES"
        finally:
            td.cleanup()


class TestSceneBasicError:
    def test_invalid_spec_json(self):
        td = tempfile.TemporaryDirectory()
        try:
            sf = os.path.join(td.name, "spec.json")
            with open(sf, "w") as f: f.write("not json")
            rc, stdout, stderr, rline, lcount = _run_checker(sf)
            assert rc == 2
            assert lcount == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "ERROR"
        finally:
            td.cleanup()

    def test_invalid_spec_contract(self):
        td = tempfile.TemporaryDirectory()
        try:
            sf = _make_spec_file(td.name, checker="wrong_checker_name")
            rc, stdout, stderr, rline, lcount = _run_checker(sf)
            assert rc == 2
            assert lcount == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "ERROR"
        finally:
            td.cleanup()

    def test_blend_path_not_found(self):
        td = tempfile.TemporaryDirectory()
        try:
            sf = _make_spec_file(td.name, blend_path="nonexistent.blend")
            rc, stdout, stderr, rline, lcount = _run_checker(sf)
            assert rc == 2
            assert lcount == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "ERROR"
        finally:
            td.cleanup()

    def test_corrupted_blend(self):
        td = tempfile.TemporaryDirectory()
        try:
            corrupted = os.path.join(td.name, "corrupt.blend")
            with open(corrupted, "wb") as f:
                f.write(b"NOT A BLENDER FILE")
            sf = _make_spec_file(td.name, blend_path="corrupt.blend")
            rc, stdout, stderr, rline, lcount = _run_checker(sf)
            assert rc == 2
            assert lcount == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "ERROR"
        finally:
            td.cleanup()


class TestDeterministic:
    def test_deterministic_output(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                             objects=[{"name": "r", "type": "EMPTY"}])
            sf = _make_spec_file(td.name, scene_rules={"expected_render_engine": "BLENDER_EEVEE"})
            _, _, _, r1, l1 = _run_checker(sf)
            _, _, _, r2, l2 = _run_checker(sf)
            assert l1 == 1 and l2 == 1
            assert r1 == r2
        finally:
            td.cleanup()


class TestBlendUnchanged:
    def test_production_code_did_not_save_blend(self):
        """Verify production code does not call save operations."""
        for rel_path in (
            "protocol_guard/phase3_min/asset_scene_preflight_check.py",
            "protocol_guard/phase3_min/blender_scene_reader.py",
        ):
            fp = os.path.join(PROJECT_ROOT, rel_path)
            with open(fp, encoding="utf-8") as f:
                content = f.read()
            assert "save_as_mainfile" not in content, f"{rel_path} calls save_as_mainfile"
            assert "save_mainfile" not in content, f"{rel_path} calls save_mainfile"

    def test_blend_still_readable_after_check(self):
        """Verify .blend remains openable after checker run (no corruption)."""
        td = tempfile.TemporaryDirectory()
        try:
            bp = _make_test_blend(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                                  objects=[{"name": "r", "type": "EMPTY"}])
            sf = _make_spec_file(td.name, scene_rules={"expected_render_engine": "BLENDER_EEVEE"})
            _run_checker(sf)
            # Verify the file still exists and has valid size
            assert os.path.exists(bp)
            assert os.path.getsize(bp) > 0
        finally:
            td.cleanup()


class TestScopeStatic:
    def test_production_code_has_no_beyond_scope_imports(self):
        """Verify production files don't contain beyond-scope bpy API calls.

        .matrix_world is allowed ONLY in _check_standing_up_axis (Standing Up Axis,
        14B-3A). All other functions must not reference it. AST-verified below.
        """
        # ── string-based forbidden list (excludes .matrix_world) ──────────
        for rel_path in (
            "protocol_guard/phase3_min/asset_scene_preflight_check.py",
            "protocol_guard/phase3_min/blender_scene_reader.py",
        ):
            fp = os.path.join(PROJECT_ROOT, rel_path)
            with open(fp, encoding="utf-8") as f:
                content = f.read().lower()
            forbidden = [
                # evaluated_depsgraph_get / evaluated_get / to_mesh / to_mesh_clear
                #   are allowed ONLY in _check_ground_contact — verified by
                #   AST-level function-scoped checks below.
                ".bound_box",
                # users_collection governed by dedicated Collection Rules I4A scope guard
                # material_slots governed by dedicated Material Assignment I4A scope guard
                # animation_data governed by dedicated Animation State I5 scope guard
                "hide_get(",
                "render.render", "save_as_mainfile", "save_mainfile",
                "bpy.data.objects.get", "bpy.data.objects[",
                ".parent",
                ".location", ".rotation_euler", ".rotation_quaternion",
            ]
            for kw in forbidden:
                assert kw not in content, f"{rel_path} contains forbidden API: {kw}"

        # ── AST-based .matrix_world scoping ───────────────────────────────
        import ast
        reader_fp = os.path.join(PROJECT_ROOT,
            "protocol_guard", "phase3_min", "blender_scene_reader.py")
        with open(reader_fp, encoding="utf-8") as f:
            reader_tree = ast.parse(f.read(), filename=reader_fp)

        checker_fp = os.path.join(PROJECT_ROOT,
            "protocol_guard", "phase3_min", "asset_scene_preflight_check.py")
        with open(checker_fp, encoding="utf-8") as f:
            checker_tree = ast.parse(f.read(), filename=checker_fp)

        def _count_matrix_world_attr_loads(tree):
            """Count Attribute nodes where attr=='matrix_world' and ctx is Load."""
            count = 0
            for node in ast.walk(tree):
                if (isinstance(node, ast.Attribute)
                        and node.attr == "matrix_world"
                        and isinstance(node.ctx, ast.Load)):
                    count += 1
            return count

        # asset_scene_preflight_check.py must NOT use .matrix_world at all
        assert _count_matrix_world_attr_loads(checker_tree) == 0, (
            "asset_scene_preflight_check.py must not access .matrix_world"
        )

        # Find _check_standing_up_axis in reader
        standing_fn = None
        for node in ast.walk(reader_tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_check_standing_up_axis":
                standing_fn = node
                break
        assert standing_fn is not None, (
            "_check_standing_up_axis not found in blender_scene_reader.py"
        )

        # _check_standing_up_axis must have exactly 1 .matrix_world Load
        standing_count = _count_matrix_world_attr_loads(standing_fn)
        assert standing_count == 1, (
            f"_check_standing_up_axis must have exactly 1 .matrix_world read, "
            f"found {standing_count}"
        )

        # _check_facing_forward_axis must have exactly 1 .matrix_world Load
        facing_fn = None
        for node in ast.walk(reader_tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_check_facing_forward_axis":
                facing_fn = node
                break
        assert facing_fn is not None, (
            "_check_facing_forward_axis not found in blender_scene_reader.py"
        )
        facing_count = _count_matrix_world_attr_loads(facing_fn)
        assert facing_count == 1, (
            f"_check_facing_forward_axis must have exactly 1 .matrix_world read, "
            f"found {facing_count}"
        )

        # _check_rotation must have exactly 1 .matrix_world Load
        rotation_fn = None
        for node in ast.walk(reader_tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_check_rotation":
                rotation_fn = node
                break
        assert rotation_fn is not None, (
            "_check_rotation not found in blender_scene_reader.py"
        )
        rotation_count = _count_matrix_world_attr_loads(rotation_fn)
        assert rotation_count == 1, (
            f"_check_rotation must have exactly 1 .matrix_world read, "
            f"found {rotation_count}"
        )

        # _check_ground_contact must have exactly 1 .matrix_world Load
        gc_fn = None
        for node in ast.walk(reader_tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_check_ground_contact":
                gc_fn = node
                break
        assert gc_fn is not None, "_check_ground_contact not found"
        gc_mw = _count_matrix_world_attr_loads(gc_fn)
        assert gc_mw == 1, f"_check_ground_contact matrix_world={gc_mw}, expected 1"

        # All OTHER functions in reader must have 0 .matrix_world reads
        allowed_mw = {"_check_standing_up_axis", "_check_facing_forward_axis",
                       "_check_rotation", "_check_ground_contact",
                       "_check_camera_check", "_check_projection_groups"}
        for node in ast.iter_child_nodes(reader_tree):
            if isinstance(node, ast.FunctionDef) and node.name not in allowed_mw:
                fn_count = _count_matrix_world_attr_loads(node)
                assert fn_count == 0, (
                    f"Function '{node.name}' in blender_scene_reader.py "
                    f"must not access .matrix_world, found {fn_count} occurrence(s)"
                )

        # ── AST-based evaluated geometry API scoping ──────────────────
        def _count_call_attr(tree, attr):
            """Count Attribute calls where .attr == attr."""
            c = 0
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr == attr:
                        c += 1
            return c

        def _count_call_name(tree, name):
            """Count calls to a simple Name (e.g. to_mesh_clear())."""
            c = 0
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id == name:
                        c += 1
            return c

        # _check_ground_contact must have exactly 1 call to each eval API
        # evaluated_depsgraph_get is called as bpy.context.evaluated_depsgraph_get()
        gc_edg = _count_call_attr(gc_fn, "evaluated_depsgraph_get")
        assert gc_edg == 1, f"_check_ground_contact evaluated_depsgraph_get={gc_edg}, expected 1"
        gc_evg = _count_call_attr(gc_fn, "evaluated_get")
        assert gc_evg == 1, f"_check_ground_contact evaluated_get={gc_evg}, expected 1"
        gc_tm = _count_call_attr(gc_fn, "to_mesh")
        assert gc_tm == 1, f"_check_ground_contact to_mesh={gc_tm}, expected 1"
        gc_tmc = _count_call_attr(gc_fn, "to_mesh_clear")
        assert gc_tmc == 1, f"_check_ground_contact to_mesh_clear={gc_tmc}, expected 1"

        # checker must have 0 of these evaluated geometry calls
        assert _count_call_attr(checker_tree, "evaluated_depsgraph_get") == 0
        assert _count_call_attr(checker_tree, "evaluated_get") == 0
        assert _count_call_attr(checker_tree, "to_mesh") == 0
        assert _count_call_attr(checker_tree, "to_mesh_clear") == 0

        # _check_camera_check must have exactly 1 call to each eval API
        cc_fn = None
        for node in ast.walk(reader_tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_check_camera_check":
                cc_fn = node
                break
        if cc_fn is not None:
            cc_edg = _count_call_attr(cc_fn, "evaluated_depsgraph_get")
            assert cc_edg == 1, f"_check_camera_check evaluated_depsgraph_get={cc_edg}, expected 1"
            cc_evg = _count_call_attr(cc_fn, "evaluated_get")
            assert cc_evg == 1, f"_check_camera_check evaluated_get={cc_evg}, expected 1"
            cc_tm = _count_call_attr(cc_fn, "to_mesh")
            assert cc_tm == 1, f"_check_camera_check to_mesh={cc_tm}, expected 1"
            cc_tmc = _count_call_attr(cc_fn, "to_mesh_clear")
            assert cc_tmc == 1, f"_check_camera_check to_mesh_clear={cc_tmc}, expected 1"

        # All OTHER reader functions must have 0 of these calls
        eval_apis = ["evaluated_depsgraph_get", "evaluated_get", "to_mesh", "to_mesh_clear"]
        for node in ast.iter_child_nodes(reader_tree):
            if isinstance(node, ast.FunctionDef) and node.name not in ("_check_ground_contact", "_check_camera_check", "_check_projection_groups"):
                for api in eval_apis:
                    c = _count_call_attr(node, api)
                    assert c == 0, (
                        f"Function '{node.name}' must not call {api}, found {c} call(s)"
                    )

        # ── world_to_camera_view scoping ──
        def _count_call_name_import(tree, name):
            """Count calls where func is a Name referencing `name`."""
            c = 0
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id == name:
                        c += 1
            return c

        # _check_camera_check must have exactly 1 world_to_camera_view call site
        if cc_fn is not None:
            cc_wtcv = _count_call_name_import(cc_fn, "world_to_camera_view")
            assert cc_wtcv == 1, f"_check_camera_check world_to_camera_view={cc_wtcv}, expected 1"

        # All OTHER reader functions must have 0 world_to_camera_view calls
        for node in ast.iter_child_nodes(reader_tree):
            if isinstance(node, ast.FunctionDef) and node.name not in ("_check_camera_check", "_check_projection_groups"):
                c = _count_call_name_import(node, "world_to_camera_view")
                assert c == 0, (
                    f"Function '{node.name}' must not call world_to_camera_view, found {c} call(s)"
                )

        # checker must have 0 world_to_camera_view
        assert _count_call_name_import(checker_tree, "world_to_camera_view") == 0, (
            "asset_scene_preflight_check.py must not call world_to_camera_view"
        )

    def test_production_code_no_render_or_save_ops(self):
        """Verify production code does not call render or save ops."""
        for rel_path in (
            "protocol_guard/phase3_min/asset_scene_preflight_check.py",
            "protocol_guard/phase3_min/blender_scene_reader.py",
        ):
            fp = os.path.join(PROJECT_ROOT, rel_path)
            with open(fp, encoding="utf-8") as f:
                content = f.read()
            assert "bpy.ops.render.render" not in content, f"{rel_path} calls render"
            assert "bpy.ops.wm.save_as_mainfile" not in content, f"{rel_path} calls save_as_mainfile"
            assert "bpy.ops.wm.save_mainfile" not in content, f"{rel_path} calls save_mainfile"

    def test_direct_children_no_recursive_child_access(self):
        """_check_direct_children must NOT read child.children — only
        _collect_descendants is authorized for recursive traversal (14B-2C)."""
        fp = os.path.join(PROJECT_ROOT, "protocol_guard", "phase3_min", "blender_scene_reader.py")
        with open(fp, encoding="utf-8") as f:
            content = f.read()
        # Find _check_direct_children function body
        # It ends where the next top-level def starts
        import re
        func_match = re.search(r'def _check_direct_children\(.*?\):(.*?)(?=\n(?:def |class |$))', content, re.DOTALL)
        if func_match:
            func_body = func_match.group(1)
            assert "child.children" not in func_body, (
                "_check_direct_children must not use child.children"
            )
        else:
            raise AssertionError("Could not find _check_direct_children function")


# ════════════════ 14B-2A-I Focused Tests ════════════════

class TestRootObjectPass:
    def test_single_target_root_exists_correct_type(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                             objects=[{"name": "Root_A", "type": "EMPTY"}])
            sf = _make_spec_file(td.name, targets=[
                {"target_id": "A", "root_object_name": "Root_A",
                 "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH"},
            ])
            rc, stdout, stderr, rline, lcount = _run_checker(sf)
            assert rc == 0
            assert lcount == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "PASS"
            ptr = result["per_target_results"]
            assert len(ptr) == 1
            assert ptr[0]["target_id"] == "A"
            assert ptr[0]["overall"] == "PASS"
            assert ptr[0]["checks"]["object_exists"]["result"] == "PASS"
            assert ptr[0]["checks"]["object_type"]["result"] == "PASS"
        finally:
            td.cleanup()

    def test_multiple_targets_all_pass_sorted(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                             objects=[
                                 {"name": "Root_B", "type": "EMPTY"},
                                 {"name": "Root_A", "type": "EMPTY"},
                             ])
            sf = _make_spec_file(td.name, targets=[
                {"target_id": "B", "root_object_name": "Root_B",
                 "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH"},
                {"target_id": "A", "root_object_name": "Root_A",
                 "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH"},
            ])
            rc, stdout, stderr, rline, lcount = _run_checker(sf)
            assert rc == 0
            assert lcount == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "PASS"
            ptr = result["per_target_results"]
            assert len(ptr) == 2
            # 14A canonicalization sorts by target_id.casefold()
            assert ptr[0]["target_id"] == "A"
            assert ptr[1]["target_id"] == "B"
            for t in ptr:
                assert t["overall"] == "PASS"
        finally:
            td.cleanup()


class TestRootObjectFail:
    def test_single_target_root_not_found(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend(td.name, "test.blend", "Scene", "BLENDER_EEVEE")
            sf = _make_spec_file(td.name, targets=[
                {"target_id": "A", "root_object_name": "Root_A",
                 "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH"},
            ])
            rc, stdout, stderr, rline, lcount = _run_checker(sf)
            assert rc == 1
            assert lcount == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "FAIL"
            ptr = result["per_target_results"]
            assert len(ptr) == 1
            assert ptr[0]["target_id"] == "A"
            assert ptr[0]["overall"] == "FAIL"
            assert ptr[0]["checks"]["object_exists"]["result"] == "FAIL"
            assert ptr[0]["checks"]["object_exists"]["failure_code"] == "ROOT_OBJECT_NOT_FOUND"
            assert ptr[0]["checks"]["object_type"]["result"] == "NOT_CHECKED"
            assert ptr[0]["checks"]["object_type"]["note"] == "ROOT_OBJECT_NOT_FOUND"
        finally:
            td.cleanup()

    def test_single_target_type_mismatch(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                             objects=[{"name": "Root_A", "type": "MESH"}])
            sf = _make_spec_file(td.name, targets=[
                {"target_id": "A", "root_object_name": "Root_A",
                 "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH"},
            ])
            rc, stdout, stderr, rline, lcount = _run_checker(sf)
            assert rc == 1
            assert lcount == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "FAIL"
            ptr = result["per_target_results"]
            assert len(ptr) == 1
            assert ptr[0]["target_id"] == "A"
            assert ptr[0]["overall"] == "FAIL"
            assert ptr[0]["checks"]["object_exists"]["result"] == "PASS"
            assert ptr[0]["checks"]["object_type"]["result"] == "FAIL"
            assert ptr[0]["checks"]["object_type"]["failure_code"] == "ROOT_OBJECT_TYPE_MISMATCH"
            assert ptr[0]["checks"]["object_type"]["expected"] == "EMPTY"
            assert ptr[0]["checks"]["object_type"]["actual"] == "MESH"
        finally:
            td.cleanup()

    def test_object_in_other_scene_only(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_two_scene_blend(td.name, "test.blend",
                                  target_scene="TargetScene", other_scene="OtherScene",
                                  other_objects=[{"name": "Root_A", "type": "EMPTY"}])
            sf = _make_spec_file(td.name, scene_name="TargetScene", targets=[
                {"target_id": "A", "root_object_name": "Root_A",
                 "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH"},
            ])
            rc, stdout, stderr, rline, lcount = _run_checker(sf)
            assert rc == 1
            assert lcount == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "FAIL"
            ptr = result["per_target_results"]
            assert len(ptr) == 1
            assert ptr[0]["overall"] == "FAIL"
            assert ptr[0]["checks"]["object_exists"]["failure_code"] == "ROOT_OBJECT_NOT_FOUND"
        finally:
            td.cleanup()

    def test_case_sensitive_name_match(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                             objects=[{"name": "Root_A", "type": "EMPTY"}])
            sf = _make_spec_file(td.name, targets=[
                {"target_id": "A", "root_object_name": "root_a",
                 "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH"},
            ])
            rc, stdout, stderr, rline, lcount = _run_checker(sf)
            assert rc == 1
            assert lcount == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "FAIL"
            ptr = result["per_target_results"]
            assert ptr[0]["checks"]["object_exists"]["failure_code"] == "ROOT_OBJECT_NOT_FOUND"
        finally:
            td.cleanup()

    def test_multiple_targets_mixed_fail(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                             objects=[{"name": "Root_A", "type": "EMPTY"}])
            sf = _make_spec_file(td.name, targets=[
                {"target_id": "A", "root_object_name": "Root_A",
                 "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH"},
                {"target_id": "B", "root_object_name": "Root_B",
                 "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH"},
            ])
            rc, stdout, stderr, rline, lcount = _run_checker(sf)
            assert rc == 1
            assert lcount == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "FAIL"
            ptr = result["per_target_results"]
            assert len(ptr) == 2
            results_by_id = {t["target_id"]: t["overall"] for t in ptr}
            assert results_by_id["A"] == "PASS"
            assert results_by_id["B"] == "FAIL"
        finally:
            td.cleanup()


class TestBlendIntegrity:
    def test_blend_sha256_unchanged_after_check(self):
        td = tempfile.TemporaryDirectory()
        try:
            bp = _make_test_blend(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                                  objects=[{"name": "Root_A", "type": "EMPTY"}])
            sha_before = _sha256_file(bp)
            sf = _make_spec_file(td.name, targets=[
                {"target_id": "A", "root_object_name": "Root_A",
                 "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH"},
            ])
            _run_checker(sf)
            sha_after = _sha256_file(bp)
            assert sha_before == sha_after, f"Blend modified: {sha_before} -> {sha_after}"
        finally:
            td.cleanup()


# ════════════════ 14B-2B-I Focused Tests ════════════════


def _make_spec_with_hierarchy(tmp_dir, targets, **overrides):
    """Make a spec file with hierarchy-configured targets. Returns path."""
    spec = {
        "schema_version": "1",
        "checker": "asset_scene_preflight_check",
        "source_requirement_version": "Blender 固定资产模板路线 v4",
        "repository_root": tmp_dir.replace("\\", "/"),
        "blend_path": overrides.pop("blend_path", "test.blend"),
        "scene_name": overrides.pop("scene_name", "Scene"),
        "targets": targets,
        "global_rules": {},
    }
    spec_name = overrides.pop("_spec_name", "spec.json")
    spec.update(overrides)
    sf = os.path.join(tmp_dir, spec_name)
    with open(sf, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False)
    return sf


class TestPreopenValidation:
    """21.1: Input validation before opening .blend."""

    def test_required_subset_of_allowed_passes(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                             objects=[{"name": "R", "type": "EMPTY"}])
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {
                    "required_direct_child_names": ["Armature"],
                    "allowed_direct_child_names": ["Armature", "Body"],
                },
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc in (0, 1)  # PASS or FAIL depending on blend state
            assert lcount == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] != "ERROR"  # Not an input error
        finally:
            td.cleanup()

    def test_required_not_subset_of_allowed_errors(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                             objects=[{"name": "R", "type": "EMPTY"}])
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {
                    "required_direct_child_names": ["Armature"],
                    "allowed_direct_child_names": ["Body"],
                },
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 2
            assert lcount == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "ERROR"
            assert any("INVALID_DIRECT_CHILD_RULE_RELATION" in e for e in result["input_errors"])
        finally:
            td.cleanup()

    def test_required_not_empty_allowed_empty_errors(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                             objects=[{"name": "R", "type": "EMPTY"}])
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {
                    "required_direct_child_names": ["Armature"],
                    "allowed_direct_child_names": [],
                },
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 2
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "ERROR"
            assert any("INVALID_DIRECT_CHILD_RULE_RELATION" in e for e in result["input_errors"])
        finally:
            td.cleanup()

    def test_empty_string_in_name_list(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                             objects=[{"name": "R", "type": "EMPTY"}])
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_direct_child_names": [""]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 2
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "ERROR"
            assert any("INVALID_DIRECT_CHILD_RULE_VALUE" in e for e in result["input_errors"])
        finally:
            td.cleanup()

    def test_non_string_in_name_list_caught(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                             objects=[{"name": "R", "type": "EMPTY"}])
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_direct_child_names": [123]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 2
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "ERROR"
            assert any("INVALID_DIRECT_CHILD_RULE_VALUE" in e for e in result["input_errors"])
        finally:
            td.cleanup()

    def test_multiple_targets_with_errors(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                             objects=[{"name": "R1", "type": "EMPTY"}, {"name": "R2", "type": "EMPTY"}])
            sf = _make_spec_with_hierarchy(td.name, targets=[
                {"target_id": "A", "root_object_name": "R1",
                 "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                 "hierarchy": {"required_direct_child_names": ["X"],
                               "allowed_direct_child_names": ["Y"]}},
                {"target_id": "B", "root_object_name": "R2",
                 "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                 "hierarchy": {"required_direct_child_names": [""]}},
            ])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 2
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "ERROR"
            errors = result["input_errors"]
            assert any("INVALID_DIRECT_CHILD_RULE_RELATION" in e for e in errors)
            assert any("INVALID_DIRECT_CHILD_RULE_VALUE" in e for e in errors)
        finally:
            td.cleanup()

    def test_input_errors_do_not_open_blend(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                             objects=[{"name": "R", "type": "EMPTY"}])
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_direct_child_names": ["X"],
                              "allowed_direct_child_names": ["Y"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 2
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "ERROR"
            assert any("INVALID_DIRECT_CHILD_RULE_RELATION" in e for e in result["input_errors"])
        finally:
            td.cleanup()


class TestRequiredDirectChildren:
    """21.2: required_direct_child_names."""

    def test_all_required_present(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Armature"}, {"name": "Body"}]})
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_direct_child_names": ["Armature", "Body"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 0
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            rq = result["per_target_results"][0]["checks"]["direct_children"]["required"]
            assert rq["result"] == "PASS"
            assert "failure_code" not in rq
        finally:
            td.cleanup()

    def test_missing_required(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Armature"}]})
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_direct_child_names": ["Armature", "Body"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            rq = result["per_target_results"][0]["checks"]["direct_children"]["required"]
            assert rq["result"] == "FAIL"
            assert rq["failure_code"] == "REQUIRED_DIRECT_CHILD_MISSING"
            assert "Body" in rq["required_missing_names"]
            assert rq["required_expected_names"] == ["Armature", "Body"]
        finally:
            td.cleanup()

    def test_case_sensitive_required(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "armature"}]})
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_direct_child_names": ["Armature"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            rq = result["per_target_results"][0]["checks"]["direct_children"]["required"]
            assert rq["result"] == "FAIL"
            assert "Armature" in rq["required_missing_names"]
        finally:
            td.cleanup()

    def test_armature_exact_not_dot_001(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Armature.001"}]})
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_direct_child_names": ["Armature"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            rq = result["per_target_results"][0]["checks"]["direct_children"]["required"]
            assert rq["result"] == "FAIL"
        finally:
            td.cleanup()


class TestAllowedDirectChildren:
    """21.3: allowed_direct_child_names."""

    def test_all_in_allowed(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Armature"}, {"name": "Body"}]})
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"allowed_direct_child_names": ["Armature", "Body"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 0
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            al = result["per_target_results"][0]["checks"]["direct_children"]["allowed"]
            assert al["result"] == "PASS"
            assert "failure_code" not in al
        finally:
            td.cleanup()

    def test_unexpected_child(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Body"}]})
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"allowed_direct_child_names": ["Armature"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            al = result["per_target_results"][0]["checks"]["direct_children"]["allowed"]
            assert al["result"] == "FAIL"
            assert al["failure_code"] == "UNEXPECTED_DIRECT_CHILD"
            assert "Body" in al["allowed_unexpected_names"]
        finally:
            td.cleanup()

    def test_allowed_case_sensitive(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "armature"}]})
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"allowed_direct_child_names": ["Armature"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            al = result["per_target_results"][0]["checks"]["direct_children"]["allowed"]
            assert al["result"] == "FAIL"
            assert "armature" in al["allowed_unexpected_names"]
        finally:
            td.cleanup()

    def test_allowed_missing_no_restriction(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Anything"}]})
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_direct_child_names": []},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 0
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dc = result["per_target_results"][0]["checks"]["direct_children"]
            assert dc["allowed"]["result"] == "NOT_CHECKED"
            assert dc["allowed"]["note"] == "ALLOWED_DIRECT_CHILD_NAMES_NOT_CONFIGURED"
            assert "failure_code" not in dc["allowed"]
        finally:
            td.cleanup()

    def test_allowed_empty_no_children_allowed(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Extra"}]})
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"allowed_direct_child_names": []},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            al = result["per_target_results"][0]["checks"]["direct_children"]["allowed"]
            assert al["result"] == "FAIL"
            assert al["failure_code"] == "UNEXPECTED_DIRECT_CHILD"
            assert "Extra" in al["allowed_unexpected_names"]
        finally:
            td.cleanup()

    def test_allowed_empty_no_children_passes(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}])
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"allowed_direct_child_names": []},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 0
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            al = result["per_target_results"][0]["checks"]["direct_children"]["allowed"]
            assert al["result"] == "PASS"
        finally:
            td.cleanup()


class TestForbiddenDirectChildren:
    """21.4: forbidden_direct_child_name_patterns."""

    def test_forbidden_pattern_match(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Icosphere.001"}]})
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_direct_child_name_patterns": ["Icosphere*"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            fb = result["per_target_results"][0]["checks"]["direct_children"]["forbidden"]
            assert fb["result"] == "FAIL"
            assert fb["failure_code"] == "FORBIDDEN_DIRECT_CHILD_NAME"
            assert "Icosphere.001" in fb["forbidden_match_names"]
        finally:
            td.cleanup()

    def test_forbidden_case_insensitive(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "icosphere"}]})
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_direct_child_name_patterns": ["Icosphere*"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            fb = result["per_target_results"][0]["checks"]["direct_children"]["forbidden"]
            assert fb["result"] == "FAIL"
            assert "icosphere" in fb["forbidden_match_names"]
        finally:
            td.cleanup()

    def test_forbidden_exact_no_dot_001(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Icosphere.001"}]})
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_direct_child_name_patterns": ["Icosphere"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 0  # Exact "Icosphere" doesn't match "Icosphere.001"
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            fb = result["per_target_results"][0]["checks"]["direct_children"]["forbidden"]
            assert fb["result"] == "PASS"
            assert "failure_code" not in fb
        finally:
            td.cleanup()

    def test_required_name_also_forbidden(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Armature"}]})
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {
                    "required_direct_child_names": ["Armature"],
                    "forbidden_direct_child_name_patterns": ["Armature*"],
                },
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dc = result["per_target_results"][0]["checks"]["direct_children"]
            assert dc["required"]["result"] == "PASS"  # Required satisfied
            assert dc["forbidden"]["result"] == "FAIL"  # But forbidden triggered
        finally:
            td.cleanup()

    def test_allowed_name_also_forbidden(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Armature"}]})
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {
                    "allowed_direct_child_names": ["Armature"],
                    "forbidden_direct_child_name_patterns": ["Armature*"],
                },
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dc = result["per_target_results"][0]["checks"]["direct_children"]
            assert dc["forbidden"]["result"] == "FAIL"
        finally:
            td.cleanup()

    def test_forbidden_empty_passes(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Anything"}]})
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_direct_child_name_patterns": []},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 0
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            fb = result["per_target_results"][0]["checks"]["direct_children"]["forbidden"]
            assert fb["result"] == "PASS"
            assert "failure_code" not in fb
        finally:
            td.cleanup()


class TestForbiddenUnexpectedDedup:
    """21.5: Forbidden match excludes from unexpected."""

    def test_child_in_neither_allowed_nor_forbidden(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Stray"}]})
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {
                    "allowed_direct_child_names": ["Armature"],
                    "forbidden_direct_child_name_patterns": ["Icosphere*"],
                },
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            al = result["per_target_results"][0]["checks"]["direct_children"]["allowed"]
            assert al["result"] == "FAIL"
            assert "Stray" in al["allowed_unexpected_names"]
        finally:
            td.cleanup()

    def test_child_in_forbidden_not_in_unexpected(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Icosphere.001"}]})
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {
                    "allowed_direct_child_names": ["Armature"],
                    "forbidden_direct_child_name_patterns": ["Icosphere*"],
                },
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dc = result["per_target_results"][0]["checks"]["direct_children"]
            assert dc["forbidden"]["result"] == "FAIL"
            assert "Icosphere.001" in dc["forbidden"]["forbidden_match_names"]
            assert "Icosphere.001" not in dc["allowed"]["allowed_unexpected_names"]
            assert "failure_code" not in dc["allowed"]
        finally:
            td.cleanup()


class TestRootPreconditionFail:
    """21.6: Direct children when root precondition fails."""

    def test_root_not_found_direct_children_not_checked(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend(td.name, "test.blend", "Scene", "BLENDER_EEVEE")
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "Missing",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_direct_child_names": ["X"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dc = result["per_target_results"][0]["checks"]["direct_children"]
            assert dc["result"] == "NOT_CHECKED"
            assert dc["note"] == "ROOT_OBJECT_NOT_FOUND"
        finally:
            td.cleanup()

    def test_type_mismatch_direct_children_not_checked(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "MESH"}],
                children_map={"R": [{"name": "Child"}]})
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_direct_child_names": ["Child"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dc = result["per_target_results"][0]["checks"]["direct_children"]
            assert dc["result"] == "NOT_CHECKED"
            assert dc["note"] == "ROOT_OBJECT_TYPE_MISMATCH"
        finally:
            td.cleanup()


class TestHierarchyScope:
    """21.7: Only one level — no grandchild processing."""

    def test_grandchild_not_satisfy_required(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Child"}]})
            # Create grandchild in a second pass
            gc_script = f'''
import bpy
bpy.ops.wm.open_mainfile(filepath=r"{os.path.join(td.name, 'test.blend')}")
scene = bpy.data.scenes["Scene"]
gc = bpy.data.objects.new("Grandchild", None)
scene.collection.objects.link(gc)
gc.parent = bpy.data.objects["Child"]
bpy.ops.wm.save_as_mainfile(filepath=r"{os.path.join(td.name, 'test.blend')}")
'''
            sf2 = os.path.join(td.name, "add_gc.py")
            with open(sf2, "w") as f: f.write(gc_script)
            r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf2],
                               capture_output=True, text=True)
            os.unlink(sf2)
            assert r.returncode == 0, f"Grandchild creation failed: {r.stderr}"

            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_direct_child_names": ["Grandchild"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            rq = result["per_target_results"][0]["checks"]["direct_children"]["required"]
            assert rq["result"] == "FAIL"
            assert "Grandchild" in rq["required_missing_names"]
        finally:
            td.cleanup()

    def test_child_only_in_other_scene_not_counted(self):
        td = tempfile.TemporaryDirectory()
        try:
            # Create blend: R in TargetScene, Child parented to R but NOT linked to any scene
            script = f'''
import bpy
scene = bpy.context.scene
scene.name = "TargetScene"
scene.render.engine = "BLENDER_EEVEE"
R = bpy.data.objects.new("R", None)
scene.collection.objects.link(R)
# Create Child parented to R but NOT linked to any scene
Child = bpy.data.objects.new("Child", None)
Child.parent = R
# Child is NOT linked to TargetScene — it's in bpy.data.objects but not scene.objects
bpy.ops.wm.save_as_mainfile(filepath=r"{os.path.join(td.name, 'test.blend')}")
'''
            sf2 = os.path.join(td.name, "make_blend.py")
            with open(sf2, "w") as f: f.write(script)
            r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf2],
                               capture_output=True, text=True)
            os.unlink(sf2)
            assert r.returncode == 0, f"Blend creation failed: {r.stderr}"

            sf = _make_spec_with_hierarchy(td.name, scene_name="TargetScene", targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_direct_child_names": ["Child"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dc = result["per_target_results"][0]["checks"]["direct_children"]
            assert dc["required"]["result"] == "FAIL"
        finally:
            td.cleanup()


class TestMultiTargetDeterminism:
    """21.8 + 21.9: Multi-target + determinism."""

    def test_multiple_targets_all_executed(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "RA", "type": "EMPTY"}, {"name": "RB", "type": "EMPTY"}],
                children_map={
                    "RA": [{"name": "ChildA"}],
                    "RB": [{"name": "ChildB"}],
                })
            sf = _make_spec_with_hierarchy(td.name, targets=[
                {"target_id": "B", "root_object_name": "RB",
                 "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                 "hierarchy": {"required_direct_child_names": ["ChildB"]}},
                {"target_id": "A", "root_object_name": "RA",
                 "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                 "hierarchy": {"required_direct_child_names": ["ChildA"]}},
            ])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 0
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            ptr = result["per_target_results"]
            assert len(ptr) == 2
            assert ptr[0]["target_id"] == "A"  # Sorted by casefold
            assert ptr[1]["target_id"] == "B"
            assert ptr[0]["overall"] == "PASS"
            assert ptr[1]["overall"] == "PASS"
        finally:
            td.cleanup()

    def test_required_order_variation_same_output(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "RA", "type": "EMPTY"}],
                children_map={"RA": [{"name": "Armature"}, {"name": "Body"}]})
            sf1 = _make_spec_with_hierarchy(td.name, _spec_name="spec_req_a.json", targets=[{
                "target_id": "A", "root_object_name": "RA",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_direct_child_names": ["Body", "Armature"]},
            }])
            sf2 = _make_spec_with_hierarchy(td.name, _spec_name="spec_req_b.json", targets=[{
                "target_id": "A", "root_object_name": "RA",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_direct_child_names": ["Armature", "Body"]},
            }])
            assert sf1 != sf2
            # _spec_name must not leak into spec JSON
            for sf in (sf1, sf2):
                with open(sf, encoding="utf-8") as f:
                    loaded = json.load(f)
                assert "_spec_name" not in loaded
            _, _, _, r1, l1 = _run_checker(sf1)
            _, _, _, r2, l2 = _run_checker(sf2)
            assert l1 == 1 and l2 == 1
            j1 = json.loads(r1[len("PHASE3_RESULT_JSON="):])
            j2 = json.loads(r2[len("PHASE3_RESULT_JSON="):])
            assert j1["per_target_results"] == j2["per_target_results"]
            assert j1["global_results"] == j2["global_results"]
            assert j1["projection_group_results"] == j2["projection_group_results"]
            assert j1["result"] == j2["result"]
        finally:
            td.cleanup()

    def test_forbidden_order_variation_same_output(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "RA", "type": "EMPTY"}],
                children_map={"RA": [{"name": "Icosphere.001"}]})
            sf1 = _make_spec_with_hierarchy(td.name, _spec_name="spec_fb_a.json", targets=[{
                "target_id": "A", "root_object_name": "RA",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_direct_child_name_patterns": ["X*", "Icosphere*"]},
            }])
            sf2 = _make_spec_with_hierarchy(td.name, _spec_name="spec_fb_b.json", targets=[{
                "target_id": "A", "root_object_name": "RA",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_direct_child_name_patterns": ["Icosphere*", "X*"]},
            }])
            assert sf1 != sf2
            for sf in (sf1, sf2):
                with open(sf, encoding="utf-8") as f:
                    loaded = json.load(f)
                assert "_spec_name" not in loaded
            _, _, _, r1, l1 = _run_checker(sf1)
            _, _, _, r2, l2 = _run_checker(sf2)
            assert l1 == 1 and l2 == 1
            j1 = json.loads(r1[len("PHASE3_RESULT_JSON="):])
            j2 = json.loads(r2[len("PHASE3_RESULT_JSON="):])
            assert j1["per_target_results"] == j2["per_target_results"]
            assert j1["global_results"] == j2["global_results"]
            assert j1["projection_group_results"] == j2["projection_group_results"]
            assert j1["result"] == j2["result"]
        finally:
            td.cleanup()

    def test_multiple_fail_types_simultaneous(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Icosphere.001"}, {"name": "Stray"}]})
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {
                    "required_direct_child_names": ["Armature"],
                    "allowed_direct_child_names": ["Armature"],
                    "forbidden_direct_child_name_patterns": ["Icosphere*"],
                },
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dc = result["per_target_results"][0]["checks"]["direct_children"]
            assert dc["result"] == "FAIL"
            assert dc["required"]["result"] == "FAIL"
            assert dc["forbidden"]["result"] == "FAIL"
            assert dc["allowed"]["result"] == "FAIL"
        finally:
            td.cleanup()


class TestDirectChildDuplicate:
    """21.8: Duplicate direct child names -> ERROR."""

    def test_duplicate_direct_child_errors(self):
        td = tempfile.TemporaryDirectory()
        try:
            # Blender prevents duplicate names — use fake objects via
            # custom Blender script to test duplicate detection directly.
            test_script = f'''
import bpy, json, sys, os
sys.path.insert(0, r"{DEPS_SITE}")
sys.path.insert(0, r"{PROJECT_ROOT}")
from protocol_guard.phase3_min.blender_scene_reader import _check_direct_children

bpy.ops.wm.read_factory_settings(use_empty=True)

class FakeObj:
    def __init__(self, name):
        self.name = name

class FakeScene:
    def __init__(self, objs):
        self.objects = list(objs)

child_a = FakeObj("Armature")
child_b = FakeObj("Armature")
root = FakeObj("R")
root.children = [child_a, child_b]
scene = FakeScene([child_a, child_b])

target = {{
    "target_id": "A",
    "hierarchy": {{"required_direct_child_names": ["Armature"]}}
}}
result = _check_direct_children(scene, root, target)
print("RESULT=" + json.dumps(result, sort_keys=True, default=str, ensure_ascii=False))
'''
            sf = os.path.join(td.name, "run.py")
            with open(sf, "w") as f: f.write(test_script)
            r = subprocess.run(
                [BLENDER_EXE, "--background", "--factory-startup", "--python", sf],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
            os.unlink(sf)
            assert r.returncode == 0, f"Script failed: {r.stderr}"
            for line in r.stdout.split("\n"):
                if line.startswith("RESULT="):
                    result = json.loads(line[len("RESULT="):])
                    assert result["result"] == "ERROR"
                    assert result["error_type"] == "AMBIGUOUS_DIRECT_CHILD_NAME"
                    assert result["ambiguous_name_counts"]["Armature"] == 2
                    break
            else:
                raise AssertionError(f"No RESULT line. stdout: {r.stdout[:500]}")
        finally:
            td.cleanup()


class TestBlendIntegrity14B2B:
    """21.10: Read-only and scope boundary."""

    def test_blend_sha256_unchanged_with_hierarchy(self):
        td = tempfile.TemporaryDirectory()
        try:
            bp = _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Armature"}, {"name": "Body"}]})
            sha_before = _sha256_file(bp)
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {
                    "required_direct_child_names": ["Armature", "Body"],
                    "allowed_direct_child_names": ["Armature", "Body"],
                },
            }])
            _run_checker(sf)
            sha_after = _sha256_file(bp)
            assert sha_before == sha_after, f"Blend modified with hierarchy check"
        finally:
            td.cleanup()


# ════════════════ 14B-2B-I R1 Tests ════════════════


class TestNotCheckedSubResults:
    """8.1: Field-missing NOT_CHECKED sub-results."""

    def test_required_missing_not_checked(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "A"}]})
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"allowed_direct_child_names": ["A"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 0
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dc = result["per_target_results"][0]["checks"]["direct_children"]
            rq = dc["required"]
            assert rq["result"] == "NOT_CHECKED"
            assert rq["required_expected_names"] is None
            assert rq["required_missing_names"] is None
            assert rq["note"] == "REQUIRED_DIRECT_CHILD_NAMES_NOT_CONFIGURED"
            assert "failure_code" not in rq
        finally:
            td.cleanup()

    def test_forbidden_missing_not_checked(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "A"}]})
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_direct_child_names": ["A"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 0
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dc = result["per_target_results"][0]["checks"]["direct_children"]
            fb = dc["forbidden"]
            assert fb["result"] == "NOT_CHECKED"
            assert fb["forbidden_patterns"] is None
            assert fb["forbidden_match_names"] is None
            assert fb["note"] == "FORBIDDEN_DIRECT_CHILD_NAME_PATTERNS_NOT_CONFIGURED"
            assert "failure_code" not in fb
        finally:
            td.cleanup()

    def test_all_three_subkeys_present_when_any_configured(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "A"}]})
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_direct_child_names": ["A"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 0
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dc = result["per_target_results"][0]["checks"]["direct_children"]
            assert "required" in dc
            assert "allowed" in dc
            assert "forbidden" in dc
            assert dc["allowed"]["result"] == "NOT_CHECKED"
            assert dc["forbidden"]["result"] == "NOT_CHECKED"
        finally:
            td.cleanup()


class TestDirectChildLookupError:
    """8.2: DIRECT_CHILD_LOOKUP_ERROR exception boundaries."""

    def test_scene_objects_access_error(self):
        td = tempfile.TemporaryDirectory()
        try:
            test_script = f'''
import bpy, json, sys, os
sys.path.insert(0, r"{DEPS_SITE}")
sys.path.insert(0, r"{PROJECT_ROOT}")
from protocol_guard.phase3_min.blender_scene_reader import _check_direct_children

bpy.ops.wm.read_factory_settings(use_empty=True)

class BadScene:
    @property
    def objects(self):
        raise RuntimeError("boom")

root = bpy.data.objects.new("R", None)
target = {{"target_id": "A", "hierarchy": {{"required_direct_child_names": ["X"]}}}}
result = _check_direct_children(BadScene(), root, target)
print("RESULT=" + json.dumps(result, sort_keys=True, default=str, ensure_ascii=False))
'''
            sf = os.path.join(td.name, "run.py")
            with open(sf, "w") as f: f.write(test_script)
            r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            os.unlink(sf)
            assert r.returncode == 0
            for line in r.stdout.split("\n"):
                if line.startswith("RESULT="):
                    result = json.loads(line[len("RESULT="):])
                    assert result["result"] == "ERROR"
                    assert result["error_type"] == "DIRECT_CHILD_LOOKUP_ERROR"
                    assert result["operation"] == "READ_SCENE_OBJECTS"
                    break
        finally:
            td.cleanup()

    def test_root_children_access_error(self):
        td = tempfile.TemporaryDirectory()
        try:
            test_script = f'''
import bpy, json, sys, os
sys.path.insert(0, r"{DEPS_SITE}")
sys.path.insert(0, r"{PROJECT_ROOT}")
from protocol_guard.phase3_min.blender_scene_reader import _check_direct_children

bpy.ops.wm.read_factory_settings(use_empty=True)

class BadRoot:
    @property
    def children(self):
        raise RuntimeError("boom")

scene = bpy.context.scene
target = {{"target_id": "A", "hierarchy": {{"required_direct_child_names": ["X"]}}}}
result = _check_direct_children(scene, BadRoot(), target)
print("RESULT=" + json.dumps(result, sort_keys=True, default=str, ensure_ascii=False))
'''
            sf = os.path.join(td.name, "run.py")
            with open(sf, "w") as f: f.write(test_script)
            r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            os.unlink(sf)
            assert r.returncode == 0
            for line in r.stdout.split("\n"):
                if line.startswith("RESULT="):
                    result = json.loads(line[len("RESULT="):])
                    assert result["result"] == "ERROR"
                    assert result["error_type"] == "DIRECT_CHILD_LOOKUP_ERROR"
                    assert result["operation"] == "READ_ROOT_CHILDREN"
                    break
        finally:
            td.cleanup()

    def test_child_name_access_error(self):
        td = tempfile.TemporaryDirectory()
        try:
            test_script = f'''
import bpy, json, sys, os
sys.path.insert(0, r"{DEPS_SITE}")
sys.path.insert(0, r"{PROJECT_ROOT}")
from protocol_guard.phase3_min.blender_scene_reader import _check_direct_children

bpy.ops.wm.read_factory_settings(use_empty=True)

class BadChild:
    @property
    def name(self):
        raise RuntimeError("name access error")

class FakeScene:
    def __init__(self, objs):
        self.objects = list(objs)

class FakeRoot:
    def __init__(self, children):
        self.children = children

bc = BadChild()
scene = FakeScene([bc])
root = FakeRoot([bc])
target = {{"target_id": "A", "hierarchy": {{"required_direct_child_names": ["X"]}}}}
result = _check_direct_children(scene, root, target)
print("RESULT=" + json.dumps(result, sort_keys=True, default=str, ensure_ascii=False))
'''
            sf = os.path.join(td.name, "run.py")
            with open(sf, "w") as f: f.write(test_script)
            r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            os.unlink(sf)
            for line in r.stdout.split("\n"):
                if line.startswith("RESULT="):
                    result = json.loads(line[len("RESULT="):])
                    assert result["result"] == "ERROR"
                    assert result["error_type"] == "DIRECT_CHILD_LOOKUP_ERROR"
                    assert result["operation"] == "READ_CHILD_NAME"
                    break
            else:
                raise AssertionError(f"No RESULT line. stdout: {r.stdout[:500]}")
        finally:
            td.cleanup()


class TestSpecDedup:
    """8.3: Duplicate spec values use set semantics."""

    def test_required_duplicates_deduplicated(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Armature"}]})
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_direct_child_names": ["Armature", "Armature"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 0
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            rq = result["per_target_results"][0]["checks"]["direct_children"]["required"]
            assert rq["required_expected_names"] == ["Armature"]
        finally:
            td.cleanup()

    def test_allowed_duplicates_deduplicated(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Extra"}]})
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"allowed_direct_child_names": ["A", "A"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            al = result["per_target_results"][0]["checks"]["direct_children"]["allowed"]
            assert al["allowed_expected_names"] == ["A"]
        finally:
            td.cleanup()

    def test_forbidden_duplicates_deduplicated(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Icosphere"}]})
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_direct_child_name_patterns": ["Icosphere*", "Icosphere*"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            fb = result["per_target_results"][0]["checks"]["direct_children"]["forbidden"]
            assert fb["forbidden_patterns"] == ["Icosphere*"]
        finally:
            td.cleanup()

    def test_case_difference_not_deduplicated(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}])
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_direct_child_names": ["Armature", "armature"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            rq = result["per_target_results"][0]["checks"]["direct_children"]["required"]
            assert len(rq["required_expected_names"]) == 2
            assert "Armature" in rq["required_expected_names"]
            assert "armature" in rq["required_expected_names"]
        finally:
            td.cleanup()


class TestGrandchildForbidden:
    """8.4: Grandchild doesn't trigger forbidden."""

    def test_grandchild_not_in_forbidden(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "DirectChild"}]})
            # Add grandchild under DirectChild
            gc_script = f'''
import bpy
bpy.ops.wm.open_mainfile(filepath=r"{os.path.join(td.name, 'test.blend')}")
scene = bpy.data.scenes["Scene"]
gc = bpy.data.objects.new("Icosphere.001", None)
scene.collection.objects.link(gc)
gc.parent = bpy.data.objects["DirectChild"]
bpy.ops.wm.save_as_mainfile(filepath=r"{os.path.join(td.name, 'test.blend')}")
'''
            sf2 = os.path.join(td.name, "add_gc.py")
            with open(sf2, "w") as f: f.write(gc_script)
            r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf2],
                               capture_output=True, text=True)
            os.unlink(sf2)
            assert r.returncode == 0

            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_direct_child_name_patterns": ["Icosphere*"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 0
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            fb = result["per_target_results"][0]["checks"]["direct_children"]["forbidden"]
            assert fb["result"] == "PASS"
            assert fb["forbidden_match_names"] == []
        finally:
            td.cleanup()


class TestMultiSceneChild:
    """8.5: Child linked to two scenes counted once."""

    def test_child_in_two_scenes_counted_once(self):
        td = tempfile.TemporaryDirectory()
        try:
            # Create blend with R in TargetScene, Child in both TargetScene and OtherScene
            script = f'''
import bpy
scene = bpy.context.scene
scene.name = "TargetScene"
scene.render.engine = "BLENDER_EEVEE"
R = bpy.data.objects.new("R", None)
scene.collection.objects.link(R)
Child = bpy.data.objects.new("Child", None)
scene.collection.objects.link(Child)
Child.parent = R

# Create OtherScene and link Child to it
bpy.ops.scene.new(type='NEW')
scene2 = bpy.context.scene
scene2.name = "OtherScene"
scene2.render.engine = "BLENDER_EEVEE"
scene2.collection.objects.link(Child)

bpy.ops.wm.save_as_mainfile(filepath=r"{os.path.join(td.name, 'test.blend')}")
'''
            sf2 = os.path.join(td.name, "make_blend.py")
            with open(sf2, "w") as f: f.write(script)
            r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf2],
                               capture_output=True, text=True)
            os.unlink(sf2)
            assert r.returncode == 0, f"Blend creation failed: {r.stderr}"

            sf = _make_spec_with_hierarchy(td.name, scene_name="TargetScene", targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_direct_child_names": ["Child"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 0
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dc = result["per_target_results"][0]["checks"]["direct_children"]
            assert dc["actual_names"] == ["Child"]
            assert dc["result"] == "PASS"
        finally:
            td.cleanup()


class TestSpecOrderDeterminism:
    """8.6: Different spec input order produces identical output."""

    def test_required_order_variation_same_output(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Armature"}, {"name": "Body"}]})
            sf1 = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_direct_child_names": ["Armature", "Body"]},
            }])
            sf2 = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_direct_child_names": ["Body", "Armature"]},
            }])
            _, _, _, r1, l1 = _run_checker(sf1)
            _, _, _, r2, l2 = _run_checker(sf2)
            assert l1 == 1 and l2 == 1
            assert r1 == r2
        finally:
            td.cleanup()

    def test_forbidden_order_variation_same_output(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Icosphere"}]})
            sf1 = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_direct_child_name_patterns": ["Icosphere*", "X*"]},
            }])
            sf2 = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_direct_child_name_patterns": ["X*", "Icosphere*"]},
            }])
            _, _, _, r1, l1 = _run_checker(sf1)
            _, _, _, r2, l2 = _run_checker(sf2)
            assert l1 == 1 and l2 == 1
            assert r1 == r2
        finally:
            td.cleanup()


class TestTypeMismatchChildrenNotRead:
    """8.7: Type mismatch does not access root.children."""

    def test_type_mismatch_direct_children_not_checked_with_children_present(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "MESH"}],
                children_map={"R": [{"name": "Child"}]})
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_direct_child_names": ["Child"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["per_target_results"][0]["checks"]["object_type"]["result"] == "FAIL"
            dc = result["per_target_results"][0]["checks"]["direct_children"]
            assert dc["result"] == "NOT_CHECKED"
            assert dc["note"] == "ROOT_OBJECT_TYPE_MISMATCH"
            # If children had been read, actual_names would contain "Child"
            assert "actual_names" not in dc
        finally:
            td.cleanup()


class TestPreopenValidationProof:
    """8.8: Invalid direct child rules caught before opening .blend."""

    def test_invalid_rules_caught_with_valid_blend(self):
        td = tempfile.TemporaryDirectory()
        try:
            # Create a valid blend so load_and_validate_spec passes
            _make_test_blend(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                             objects=[{"name": "R", "type": "EMPTY"}])
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_direct_child_names": ["X"],
                              "allowed_direct_child_names": ["Y"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 2
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "ERROR"
            errors = result["input_errors"]
            assert any("INVALID_DIRECT_CHILD_RULE_RELATION" in e for e in errors)
            # The checker should NOT have opened the blend — the error is from pre-open
            # which runs before bpy.ops.wm.open_mainfile
        finally:
            td.cleanup()


# ════════════════ 14B-2B-I R2 Tests ════════════════


class TestPreopenRelationSetSemantics:
    """Section 5: Pre-open relation validation uses set semantics."""

    def test_duplicate_required_in_relation_error_once(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                             objects=[{"name": "R", "type": "EMPTY"}])
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {
                    "required_direct_child_names": ["Armature", "Armature"],
                    "allowed_direct_child_names": [],
                },
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 2
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "ERROR"
            errors = result["input_errors"]
            rel_errors = [e for e in errors if "INVALID_DIRECT_CHILD_RULE_RELATION" in e]
            assert len(rel_errors) == 1
            # Armature should appear only once
            assert rel_errors[0].count("Armature") == 1
        finally:
            td.cleanup()

    def test_case_different_required_not_merged_in_relation(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                             objects=[{"name": "R", "type": "EMPTY"}])
            sf = _make_spec_with_hierarchy(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {
                    "required_direct_child_names": ["Armature", "armature"],
                    "allowed_direct_child_names": ["Armature"],
                },
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 2
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "ERROR"
            errors = result["input_errors"]
            rel_errors = [e for e in errors if "INVALID_DIRECT_CHILD_RULE_RELATION" in e]
            assert len(rel_errors) == 1
            # Only "armature" should be listed as missing (case-sensitive)
            assert "armature" in rel_errors[0]
        finally:
            td.cleanup()


class TestAggregationPriority:
    """Section 6: ERROR > FAIL > PASS in direct_children aggregation."""

    def test_error_priority_over_fail_in_aggregation(self):
        td = tempfile.TemporaryDirectory()
        try:
            test_script = f'''
import bpy, json, sys, os
sys.path.insert(0, r"{DEPS_SITE}")
sys.path.insert(0, r"{PROJECT_ROOT}")
from protocol_guard.phase3_min.blender_scene_reader import _check_direct_children

bpy.ops.wm.read_factory_settings(use_empty=True)

class FakeObj:
    def __init__(self, name):
        self.name = name

class FakeScene:
    def __init__(self, objs):
        self.objects = list(objs)

# Create scenario: two children with same name (ERROR) + required missing (FAIL)
child_a = FakeObj("Armature")
child_b = FakeObj("Armature")
root = FakeObj("R")
root.children = [child_a, child_b]
scene = FakeScene([child_a, child_b])

target = {{
    "target_id": "A",
    "hierarchy": {{
        "required_direct_child_names": ["Armature", "Body"],
    }}
}}
result = _check_direct_children(scene, root, target)
print("RESULT=" + json.dumps(result, sort_keys=True, default=str, ensure_ascii=False))
'''
            sf = os.path.join(td.name, "run.py")
            with open(sf, "w") as f: f.write(test_script)
            r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            os.unlink(sf)
            assert r.returncode == 0
            for line in r.stdout.split("\n"):
                if line.startswith("RESULT="):
                    result = json.loads(line[len("RESULT="):])
                    # Duplicate names cause ERROR, which must win over FAIL from missing required
                    assert result["result"] == "ERROR"
                    assert result["error_type"] == "AMBIGUOUS_DIRECT_CHILD_NAME"
                    break
            else:
                raise AssertionError("No RESULT line")
        finally:
            td.cleanup()


class TestLookupErrorFullPath:
    """Section 7: Full path proof for DIRECT_CHILD_LOOKUP_ERROR."""

    def test_lookup_error_through_full_path(self):
        td = tempfile.TemporaryDirectory()
        try:
            test_script = f'''
import bpy, json, sys, os
sys.path.insert(0, r"{DEPS_SITE}")
sys.path.insert(0, r"{PROJECT_ROOT}")
from protocol_guard.phase3_min.blender_scene_reader import _check_root_objects

bpy.ops.wm.read_factory_settings(use_empty=True)

class BadScene:
    @property
    def objects(self):
        raise RuntimeError("scene.objects failed")

# Create a real root object
R = bpy.data.objects.new("Root_A", None)
bpy.context.scene.collection.objects.link(R)

targets = [{{
    "target_id": "A",
    "root_object_name": "Root_A",
    "expected_root_type": "EMPTY",
    "hierarchy": {{"required_direct_child_names": ["X"]}},
}}]

bad_scene = BadScene()
results = _check_root_objects(bad_scene, targets)
result = results[0]
print("RESULT=" + json.dumps({{
    "overall": result["overall"],
    "dc_result": result["checks"]["direct_children"]["result"],
    "dc_error_type": result["checks"]["direct_children"]["error_type"],
    "dc_operation": result["checks"]["direct_children"]["operation"],
}}, sort_keys=True, ensure_ascii=False))
'''
            sf = os.path.join(td.name, "run.py")
            with open(sf, "w") as f: f.write(test_script)
            r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            os.unlink(sf)
            assert r.returncode == 0
            result_lines = [l for l in r.stdout.split("\n") if l.startswith("RESULT=")]
            assert len(result_lines) == 1
            result = json.loads(result_lines[0][len("RESULT="):])
            assert result["overall"] == "ERROR"
            assert result["dc_result"] == "ERROR"
            assert result["dc_error_type"] == "DIRECT_CHILD_LOOKUP_ERROR"
            assert result["dc_operation"] == "READ_SCENE_OBJECTS"
        finally:
            td.cleanup()


class TestTypeMismatchChildrenProof:
    """Section 8: Type mismatch does NOT read root.children (exploding proof)."""

    def test_type_mismatch_exploding_children_not_accessed(self):
        td = tempfile.TemporaryDirectory()
        try:
            test_script = f'''
import bpy, json, sys, os
sys.path.insert(0, r"{DEPS_SITE}")
sys.path.insert(0, r"{PROJECT_ROOT}")
from protocol_guard.phase3_min.blender_scene_reader import _check_root_objects

bpy.ops.wm.read_factory_settings(use_empty=True)

class ExplodingObj:
    def __init__(self):
        self.name = "Root_A"
        self.type = "MESH"
    @property
    def children(self):
        raise AssertionError("children must not be read on type mismatch")

scene = bpy.context.scene

targets = [{{
    "target_id": "A",
    "root_object_name": "Root_A",
    "expected_root_type": "EMPTY",
    "hierarchy": {{"required_direct_child_names": ["X"]}},
}}]

# Need the fake root to be found in scene.objects
# Wrap scene to include our fake root
class WrappedScene:
    def __init__(self, real, extras):
        self._real = real
        self._extras = extras
    @property
    def objects(self):
        return list(self._real.objects) + list(self._extras)

fake_root = ExplodingObj()
ws = WrappedScene(scene, [fake_root])
try:
    results = _check_root_objects(ws, targets)
    result = results[0]
    print("RESULT=" + json.dumps({{
        "overall": result["overall"],
        "object_exists": result["checks"]["object_exists"]["result"],
        "object_type_result": result["checks"]["object_type"]["result"],
        "object_type_fc": result["checks"]["object_type"].get("failure_code"),
        "dc_result": result["checks"]["direct_children"]["result"],
        "dc_note": result["checks"]["direct_children"]["note"],
    }}, sort_keys=True, ensure_ascii=False))
except AssertionError:
    print("EXPLODED=children_accessed")
'''
            sf = os.path.join(td.name, "run.py")
            with open(sf, "w") as f: f.write(test_script)
            r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            os.unlink(sf)
            # Must find RESULT line, not EXPLODED
            for line in r.stdout.split("\n"):
                if line.startswith("EXPLODED="):
                    raise AssertionError("root.children was accessed despite type mismatch")
            result_lines = [l for l in r.stdout.split("\n") if l.startswith("RESULT=")]
            assert len(result_lines) == 1
            result = json.loads(result_lines[0][len("RESULT="):])
            assert result["object_exists"] == "PASS"
            assert result["object_type_result"] == "FAIL"
            assert result["object_type_fc"] == "ROOT_OBJECT_TYPE_MISMATCH"
            assert result["dc_result"] == "NOT_CHECKED"
            assert result["dc_note"] == "ROOT_OBJECT_TYPE_MISMATCH"
            assert result["overall"] == "FAIL"
        finally:
            td.cleanup()


class TestRuleValidationBeforeBlendOpen:
    """Pre-open direct child rule checks happen after 14A validation
    but before bpy.ops.wm.open_mainfile. Proof: use existing corrupt blend
    file that passes path check but would fail on open — the rule error
    (not OPEN_ERROR) is returned."""

    def test_relation_error_caught_before_open(self):
        td = tempfile.TemporaryDirectory()
        try:
            corrupt = os.path.join(td.name, "corrupt.blend")
            with open(corrupt, "wb") as f:
                f.write(b"NOT A BLENDER FILE")
            sf = _make_spec_with_hierarchy(td.name, blend_path="corrupt.blend", targets=[{
                "target_id": "A", "root_object_name": "Root_A",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {
                    "required_direct_child_names": ["Armature"],
                    "allowed_direct_child_names": [],
                },
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 2
            assert lcount == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "ERROR"
            assert result["spec_sha256"] != ""
            errors = result["input_errors"]
            assert any("INVALID_DIRECT_CHILD_RULE_RELATION" in e for e in errors)
            assert not any("OPEN_ERROR" in e for e in errors)
            assert not any("OPEN_FAILED" in e for e in errors)
        finally:
            td.cleanup()

    def test_value_error_caught_before_open(self):
        td = tempfile.TemporaryDirectory()
        try:
            corrupt = os.path.join(td.name, "corrupt.blend")
            with open(corrupt, "wb") as f:
                f.write(b"NOT A BLENDER FILE")
            sf = _make_spec_with_hierarchy(td.name, blend_path="corrupt.blend", targets=[{
                "target_id": "A", "root_object_name": "Root_A",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_direct_child_names": [123]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 2
            assert lcount == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "ERROR"
            assert result["spec_sha256"] != ""
            errors = result["input_errors"]
            assert any("INVALID_DIRECT_CHILD_RULE_VALUE" in e for e in errors)
            assert not any("OPEN_ERROR" in e for e in errors)
            assert not any("OPEN_FAILED" in e for e in errors)
        finally:
            td.cleanup()


class TestAllowedOrderDeterminism:
    """Section 10: Allowed list order variation produces identical output."""

    def test_allowed_order_variation_same_output(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_children(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Armature"}, {"name": "Body"}]})
            sf1 = _make_spec_with_hierarchy(td.name, _spec_name="spec_al_a.json", targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"allowed_direct_child_names": ["Armature", "Body"]},
            }])
            sf2 = _make_spec_with_hierarchy(td.name, _spec_name="spec_al_b.json", targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"allowed_direct_child_names": ["Body", "Armature"]},
            }])
            assert sf1 != sf2
            for sf in (sf1, sf2):
                with open(sf, encoding="utf-8") as f:
                    loaded = json.load(f)
                assert "_spec_name" not in loaded
            _, _, _, r1, l1 = _run_checker(sf1)
            _, _, _, r2, l2 = _run_checker(sf2)
            assert l1 == 1 and l2 == 1
            j1 = json.loads(r1[len("PHASE3_RESULT_JSON="):])
            j2 = json.loads(r2[len("PHASE3_RESULT_JSON="):])
            assert j1["per_target_results"] == j2["per_target_results"]
            assert j1["global_results"] == j2["global_results"]
            assert j1["projection_group_results"] == j2["projection_group_results"]
            assert j1["result"] == j2["result"]
        finally:
            td.cleanup()


# ════════════════ 14B-2B-I R3 Tests ════════════════


class TestLookupErrorFullPipeline:
    """Full top-level ERROR path: _check_root_objects → _collect_target_errors."""

    def test_scene_objects_error_full_pipeline(self):
        td = tempfile.TemporaryDirectory()
        try:
            test_script = f'''
import bpy, json, sys, os
sys.path.insert(0, r"{DEPS_SITE}")
sys.path.insert(0, r"{PROJECT_ROOT}")
from protocol_guard.phase3_min.blender_scene_reader import _check_root_objects
from protocol_guard.phase3_min.asset_scene_preflight_check import _collect_target_errors

bpy.ops.wm.read_factory_settings(use_empty=True)

class BadScene:
    @property
    def objects(self):
        raise RuntimeError("boom")

targets = [{{
    "target_id": "A", "root_object_name": "Root_A",
    "expected_root_type": "EMPTY",
    "hierarchy": {{"required_direct_child_names": ["X"]}},
}}]

results = _check_root_objects(BadScene(), targets)
assert len(results) == 1
t = results[0]
assert t["overall"] == "ERROR", f"Expected ERROR, got {{t['overall']}}"
dc = t["checks"]["direct_children"]
assert dc["result"] == "ERROR"
assert dc["error_type"] == "DIRECT_CHILD_LOOKUP_ERROR"
assert dc["operation"] == "READ_SCENE_OBJECTS"

errs = _collect_target_errors(results)
assert len(errs) >= 1
has_dc = any("DIRECT_CHILD_LOOKUP_ERROR" in e for e in errs)
assert has_dc, f"Errors: {{errs}}"
has_op = any("READ_SCENE_OBJECTS" in e for e in errs)
assert has_op, f"Errors: {{errs}}"

print("PASS=" + json.dumps({{
    "overall": t["overall"], "dc_error_type": dc["error_type"],
    "dc_operation": dc["operation"], "errors_collected": len(errs),
}}))
'''
            sf = os.path.join(td.name, "run.py")
            with open(sf, "w") as f: f.write(test_script)
            r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            os.unlink(sf)
            assert r.returncode == 0, f"Script failed: {r.stderr}"
            result_lines = [l for l in r.stdout.split("\n") if l.startswith("PASS=")]
            assert len(result_lines) == 1
            result = json.loads(result_lines[0][len("PASS="):])
            assert result["overall"] == "ERROR"
            assert result["dc_error_type"] == "DIRECT_CHILD_LOOKUP_ERROR"
            assert result["dc_operation"] == "READ_SCENE_OBJECTS"
            assert result["errors_collected"] >= 1
        finally:
            td.cleanup()

    def test_same_instance_included_in_scene(self):
        td = tempfile.TemporaryDirectory()
        try:
            test_script = f'''
import bpy, json, sys, os
sys.path.insert(0, r"{DEPS_SITE}")
sys.path.insert(0, r"{PROJECT_ROOT}")
from protocol_guard.phase3_min.blender_scene_reader import _check_direct_children

bpy.ops.wm.read_factory_settings(use_empty=True)

class FakeObj:
    def __init__(self, name):
        self.name = name

class FakeScene:
    def __init__(self, objs):
        self.objects = list(objs)

child = FakeObj("Child")
scene = FakeScene([child])
root = FakeObj("R")
root.children = [child]
target = {{"target_id": "A", "hierarchy": {{"required_direct_child_names": ["Child"]}}}}
r = _check_direct_children(scene, root, target)
assert r["result"] == "PASS"
assert r["actual_names"] == ["Child"]
assert r["required"]["result"] == "PASS"
assert r["required"]["required_missing_names"] == []
print("PASS=OK")
'''
            sf = os.path.join(td.name, "run.py")
            with open(sf, "w") as f: f.write(test_script)
            r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            os.unlink(sf)
            assert r.returncode == 0, f"Script failed: {r.stderr}"
            result_lines = [l for l in r.stdout.split("\n") if l.startswith("PASS=")]
            assert len(result_lines) == 1
            assert result_lines[0] == "PASS=OK"
        finally:
            td.cleanup()

    def test_equal_distinct_instance_excluded_from_scene(self):
        td = tempfile.TemporaryDirectory()
        try:
            test_script = f'''
import bpy, json, sys, os
sys.path.insert(0, r"{DEPS_SITE}")
sys.path.insert(0, r"{PROJECT_ROOT}")
from protocol_guard.phase3_min.blender_scene_reader import _check_direct_children

bpy.ops.wm.read_factory_settings(use_empty=True)

class EqualButDistinctObject:
    eq_call_count = 0

    def __init__(self, name):
        self.name = name

    def __hash__(self):
        return 1

    def __eq__(self, other):
        type(self).eq_call_count += 1
        return True

class FakeScene:
    def __init__(self, objs):
        self.objects = list(objs)

scene_obj = EqualButDistinctObject("Child")
root_child = EqualButDistinctObject("Child")
assert scene_obj is not root_child

scene = FakeScene([scene_obj])
root = EqualButDistinctObject("R")
root.children = [root_child]
target = {{"target_id": "A", "hierarchy": {{"required_direct_child_names": ["Child"]}}}}
r = _check_direct_children(scene, root, target)
assert r["result"] == "FAIL"
assert r["actual_names"] == []
assert r["required"]["result"] == "FAIL"
assert r["required"]["failure_code"] == "REQUIRED_DIRECT_CHILD_MISSING"
assert r["required"]["required_missing_names"] == ["Child"]
assert EqualButDistinctObject.eq_call_count == 0
print("PASS=OK")
'''
            sf = os.path.join(td.name, "run.py")
            with open(sf, "w") as f: f.write(test_script)
            r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            os.unlink(sf)
            assert r.returncode == 0, f"Script failed: {r.stderr}"
            result_lines = [l for l in r.stdout.split("\n") if l.startswith("PASS=")]
            assert len(result_lines) == 1
            assert result_lines[0] == "PASS=OK"
        finally:
            td.cleanup()


class TestAggregateCheckResults:
    """_aggregate_check_results ERROR > FAIL > PASS priority proof."""

    def test_error_over_fail_priority(self):
        td = tempfile.TemporaryDirectory()
        try:
            test_script = f'''
import json, sys, os
sys.path.insert(0, r"{DEPS_SITE}")
sys.path.insert(0, r"{PROJECT_ROOT}")
from protocol_guard.phase3_min.blender_scene_reader import _aggregate_check_results

r1 = _aggregate_check_results(["ERROR", "FAIL", "PASS"])
assert r1 == "ERROR", f"Expected ERROR, got {{r1}}"
r2 = _aggregate_check_results(["FAIL", "PASS", "NOT_CHECKED"])
assert r2 == "FAIL", f"Expected FAIL, got {{r2}}"
r3 = _aggregate_check_results(["PASS", "NOT_CHECKED", "PASS"])
assert r3 == "PASS", f"Expected PASS, got {{r3}}"
r4 = _aggregate_check_results(["PASS", "ERROR", "NOT_CHECKED"])
assert r4 == "ERROR", f"Expected ERROR, got {{r4}}"
r5 = _aggregate_check_results(["NOT_CHECKED", "NOT_CHECKED", "NOT_CHECKED"])
assert r5 == "PASS", f"Expected PASS, got {{r5}}"
print("PASS=OK")
'''
            sf = os.path.join(td.name, "run.py")
            with open(sf, "w") as f: f.write(test_script)
            r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            os.unlink(sf)
            assert r.returncode == 0, f"Script failed: {r.stderr}"
            result_lines = [l for l in r.stdout.split("\n") if l.startswith("PASS=")]
            assert len(result_lines) == 1
            assert result_lines[0] == "PASS=OK"
        finally:
            td.cleanup()
