"""Tests for 14B-2C-I2: forbidden descendant name patterns + aggregation."""
import json, os, subprocess, sys, tempfile, hashlib
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
BLENDER_EXE = r"D:\Windows software\blender\blender.exe"
CHECKER_SCRIPT = os.path.join(PROJECT_ROOT, "protocol_guard", "phase3_min", "asset_scene_preflight_check.py")
DEPS_SITE = r"C:\Users\Administrator\AppData\Roaming\Python\Python314\site-packages"


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk: break
            h.update(chunk)
    return h.hexdigest()


def _make_blend_with_tree(tmp_dir, blend_name, scene_name="Scene",
                           render_engine="BLENDER_EEVEE",
                           root_objects=None, children_map=None,
                           grandchildren_map=None):
    obj_lines = ""
    if root_objects:
        for obj_spec in root_objects:
            oname = obj_spec["name"]
            otype = obj_spec.get("type", "EMPTY")
            if otype == "MESH":
                obj_lines += f'mesh = bpy.data.meshes.new("{oname}_mesh")\n{oname} = bpy.data.objects.new("{oname}", mesh)\n'
            else:
                obj_lines += f'{oname} = bpy.data.objects.new("{oname}", None)\n'
            obj_lines += f'scene.collection.objects.link({oname})\n'
    if children_map:
        for parent_name, child_specs in children_map.items():
            for cs in child_specs:
                cname = cs["name"]; ctype = cs.get("type", "EMPTY")
                if ctype == "MESH":
                    obj_lines += f'mesh = bpy.data.meshes.new("{cname}_mesh")\n{cname} = bpy.data.objects.new("{cname}", mesh)\n'
                else:
                    obj_lines += f'{cname} = bpy.data.objects.new("{cname}", None)\n'
                obj_lines += f'scene.collection.objects.link({cname})\n{cname}.parent = {parent_name}\n'
    if grandchildren_map:
        for parent_name, gc_specs in grandchildren_map.items():
            for gs in gc_specs:
                gname = gs["name"]; gtype = gs.get("type", "EMPTY")
                if gtype == "MESH":
                    obj_lines += f'mesh = bpy.data.meshes.new("{gname}_mesh")\n{gname} = bpy.data.objects.new("{gname}", mesh)\n'
                else:
                    obj_lines += f'{gname} = bpy.data.objects.new("{gname}", None)\n'
                obj_lines += f'scene.collection.objects.link({gname})\n{gname}.parent = {parent_name}\n'
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
    r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf], capture_output=True, text=True)
    os.unlink(sf)
    assert r.returncode == 0, f"Blend creation failed: {r.stderr}"
    return os.path.join(tmp_dir, blend_name)


def _make_spec_d(tmp_dir, **overrides):
    spec = {
        "schema_version": "1", "checker": "asset_scene_preflight_check",
        "source_requirement_version": "Blender 固定资产模板路线 v4",
        "repository_root": tmp_dir.replace("\\", "/"),
        "blend_path": overrides.pop("blend_path", "test.blend"),
        "scene_name": overrides.pop("scene_name", "Scene"),
        "targets": overrides.pop("targets", [{"target_id": "T", "root_object_name": "R", "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH"}]),
        "global_rules": {},
    }
    spec.update(overrides)
    sf = os.path.join(tmp_dir, "spec.json")
    with open(sf, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False)
    return sf


def _run_checker(spec_path):
    r = subprocess.run(
        [BLENDER_EXE, "--background", "--factory-startup",
         "--python", CHECKER_SCRIPT, "--",
         "--spec", spec_path, "--dependency-site-packages", DEPS_SITE],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    lines = r.stdout.split("\n")
    result_lines = [l for l in lines if l.startswith("PHASE3_RESULT_JSON=")]
    result_line = result_lines[0] if len(result_lines) == 1 else None
    return (r.returncode, r.stdout, r.stderr, result_line, len(result_lines))


def _run_checker_hardened(spec_path, expected_returncode):
    r = subprocess.run(
        [BLENDER_EXE, "--background", "--factory-startup",
         "--python", CHECKER_SCRIPT, "--",
         "--spec", spec_path, "--dependency-site-packages", DEPS_SITE],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == expected_returncode, (
        f"Expected returncode {expected_returncode}, got {r.returncode}\n"
        f"STDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
    )
    assert "Traceback" not in r.stderr, f"Traceback in stderr\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
    assert "AssertionError" not in r.stderr, f"AssertionError in stderr\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
    result_lines = [l for l in r.stdout.split("\n") if l.startswith("PHASE3_RESULT_JSON=")]
    assert len(result_lines) == 1, (
        f"Expected 1 PHASE3_RESULT_JSON line, got {len(result_lines)}\n"
        f"STDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
    )
    try:
        return json.loads(result_lines[0][len("PHASE3_RESULT_JSON="):])
    except json.JSONDecodeError:
        raise AssertionError(
            f"Invalid PHASE3_RESULT_JSON, returncode {r.returncode}\n"
            f"STDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
        )


# ════════════════ 14B-2C-I2 Tests ════════════════

class TestForbiddenBasic:
    def test_direct_child_matches_forbidden(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "TempObj"}]})
            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_descendant_name_patterns": ["*Temp*"]},
            }])
            result = _run_checker_hardened(sf, expected_returncode=1)
            fb = result["per_target_results"][0]["checks"]["descendants"]["forbidden"]
            assert fb["result"] == "FAIL"
            assert fb["failure_code"] == "FORBIDDEN_DESCENDANT_NAME"
            assert "TempObj" in fb["forbidden_match_names"]
        finally:
            td.cleanup()

    def test_grandchild_matches_forbidden(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Child"}]},
                grandchildren_map={"Child": [{"name": "TempObj"}]})
            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_descendant_name_patterns": ["*Temp*"]},
            }])
            result = _run_checker_hardened(sf, expected_returncode=1)
            fb = result["per_target_results"][0]["checks"]["descendants"]["forbidden"]
            assert fb["result"] == "FAIL"
            assert "TempObj" in fb["forbidden_match_names"]
        finally:
            td.cleanup()

    def test_no_match_passes(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "SafeObj"}]})
            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_descendant_name_patterns": ["*Temp*"]},
            }])
            result = _run_checker_hardened(sf, expected_returncode=0)
            fb = result["per_target_results"][0]["checks"]["descendants"]["forbidden"]
            assert fb["result"] == "PASS"
            assert "failure_code" not in fb
        finally:
            td.cleanup()


class TestForbiddenGlob:
    def test_casefold_match(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "tempobj"}]})
            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_descendant_name_patterns": ["TempObj"]},
            }])
            result = _run_checker_hardened(sf, expected_returncode=1)
            fb = result["per_target_results"][0]["checks"]["descendants"]["forbidden"]
            assert fb["result"] == "FAIL"
        finally:
            td.cleanup()

    def test_star_wildcard(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "PrefixTestSuffix"}]})
            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_descendant_name_patterns": ["Prefix*Suffix"]},
            }])
            result = _run_checker_hardened(sf, expected_returncode=1)
            fb = result["per_target_results"][0]["checks"]["descendants"]["forbidden"]
            assert fb["result"] == "FAIL"
        finally:
            td.cleanup()

    def test_exact_pattern_no_dot_match(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Obj"}]})
            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_descendant_name_patterns": ["Obj"]},
            }])
            result = _run_checker_hardened(sf, expected_returncode=1)
        finally:
            td.cleanup()


class TestForbiddenConfig:
    def test_field_missing_forbidden_not_checked(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "X"}]})
            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_descendant_names": ["X"]},
            }])
            result = _run_checker_hardened(sf, expected_returncode=0)
            fb = result["per_target_results"][0]["checks"]["descendants"]["forbidden"]
            assert fb["result"] == "NOT_CHECKED"
            assert fb["forbidden_patterns"] is None
            assert fb["forbidden_match_names"] is None
            assert fb["note"] == "FORBIDDEN_DESCENDANT_NAME_PATTERNS_NOT_CONFIGURED"
        finally:
            td.cleanup()

    def test_field_empty_array_passes(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "X"}]})
            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_descendant_name_patterns": []},
            }])
            result = _run_checker_hardened(sf, expected_returncode=0)
            fb = result["per_target_results"][0]["checks"]["descendants"]["forbidden"]
            assert fb["result"] == "PASS"
            assert "failure_code" not in fb
        finally:
            td.cleanup()

    def test_duplicate_pattern_dedup(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "X"}]})
            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_descendant_name_patterns": ["X", "X"]},
            }])
            result = _run_checker_hardened(sf, expected_returncode=1)
            fb = result["per_target_results"][0]["checks"]["descendants"]["forbidden"]
            assert fb["forbidden_patterns"] == ["X"]  # deduped
        finally:
            td.cleanup()

    def test_empty_string_preopen_error(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}])
            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_descendant_name_patterns": [""]},
            }])
            result = _run_checker_hardened(sf, expected_returncode=2)
            assert any("INVALID_DESCENDANT_RULE_VALUE" in e for e in result["input_errors"])
        finally:
            td.cleanup()

    def test_non_string_preopen_error(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}])
            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_descendant_name_patterns": [None]},
            }])
            result = _run_checker_hardened(sf, expected_returncode=2)
            assert any("INVALID_DESCENDANT_RULE_VALUE" in e for e in result["input_errors"])
        finally:
            td.cleanup()


class TestForbiddenRequiredAggregation:
    def test_only_required_configured_forbidden_not_checked(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Armature"}]})
            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_descendant_names": ["Armature"]},
            }])
            result = _run_checker_hardened(sf, expected_returncode=0)
            dc = result["per_target_results"][0]["checks"]["descendants"]
            assert dc["result"] == "PASS"
            assert dc["forbidden"]["result"] == "NOT_CHECKED"
        finally:
            td.cleanup()

    def test_required_pass_forbidden_pass(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Armature"}]})
            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {
                    "required_descendant_names": ["Armature"],
                    "forbidden_descendant_name_patterns": ["*Temp*"],
                },
            }])
            _run_checker_hardened(sf, expected_returncode=0)
        finally:
            td.cleanup()

    def test_required_fail_forbidden_pass(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Armature"}]})
            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {
                    "required_descendant_names": ["Body"],
                    "forbidden_descendant_name_patterns": ["*Temp*"],
                },
            }])
            result = _run_checker_hardened(sf, expected_returncode=1)
            dc = result["per_target_results"][0]["checks"]["descendants"]
            assert dc["result"] == "FAIL"
            assert dc["required"]["result"] == "FAIL"
            assert dc["forbidden"]["result"] == "PASS"
        finally:
            td.cleanup()

    def test_required_pass_forbidden_fail(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Armature"}, {"name": "TempObj"}]})
            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {
                    "required_descendant_names": ["Armature"],
                    "forbidden_descendant_name_patterns": ["*Temp*"],
                },
            }])
            result = _run_checker_hardened(sf, expected_returncode=1)
            dc = result["per_target_results"][0]["checks"]["descendants"]
            assert dc["result"] == "FAIL"
            assert dc["required"]["result"] == "PASS"
            assert dc["forbidden"]["result"] == "FAIL"
        finally:
            td.cleanup()

    def test_required_name_also_matches_forbidden(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "TempObj"}]})
            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {
                    "required_descendant_names": ["TempObj"],
                    "forbidden_descendant_name_patterns": ["*Temp*"],
                },
            }])
            result = _run_checker_hardened(sf, expected_returncode=1)
            dc = result["per_target_results"][0]["checks"]["descendants"]
            assert dc["result"] == "FAIL"
            assert dc["required"]["result"] == "PASS"   # Required IS satisfied
            assert dc["forbidden"]["result"] == "FAIL"  # But also forbidden
        finally:
            td.cleanup()


class TestForbiddenSortingDedup:
    def test_forbidden_patterns_sorted(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "BObj"}, {"name": "AObj"}]})
            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_descendant_name_patterns": ["Z*", "A*"]},
            }])
            result = _run_checker_hardened(sf, expected_returncode=1)
            fb = result["per_target_results"][0]["checks"]["descendants"]["forbidden"]
            assert fb["forbidden_patterns"] == ["A*", "Z*"]  # casefold sorted
            assert fb["forbidden_match_names"] == ["AObj"]  # only AObj matches A*
        finally:
            td.cleanup()

    def test_one_name_matches_multiple_patterns_once(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "X"}]})
            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_descendant_name_patterns": ["X", "*X*", "X*"]},
            }])
            result = _run_checker_hardened(sf, expected_returncode=1)
            fb = result["per_target_results"][0]["checks"]["descendants"]["forbidden"]
            assert fb["forbidden_match_names"] == ["X"]  # once only
        finally:
            td.cleanup()


class TestForbiddenDeterminism:
    def test_deterministic_output(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "A"}, {"name": "B"}]})
            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_descendant_name_patterns": ["B*", "A*"]},
            }])
            r1 = _run_checker_hardened(sf, expected_returncode=1)
            r2 = _run_checker_hardened(sf, expected_returncode=1)
            assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)
        finally:
            td.cleanup()


# ════════════════ 14B-2C-I2-R1 Structure Tests ════════════════


class TestDescendantsStructure:
    def test_only_forbidden_configured_required_not_checked(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "X"}]})
            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_descendant_name_patterns": ["*Z*"]},
            }])
            result = _run_checker_hardened(sf, expected_returncode=0)
            dc = result["per_target_results"][0]["checks"]["descendants"]
            assert dc["result"] == "PASS"
            assert dc["required"]["result"] == "NOT_CHECKED"
            assert dc["required"]["note"] == "REQUIRED_DESCENDANT_NAMES_NOT_CONFIGURED"
            assert dc["required"]["required_expected_names"] is None
            assert dc["forbidden"]["result"] == "PASS"
        finally:
            td.cleanup()

    def test_hierarchy_empty_dict(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}])
            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {},
            }])
            result = _run_checker_hardened(sf, expected_returncode=0)
            dc = result["per_target_results"][0]["checks"]["descendants"]
            assert dc["result"] == "NOT_CHECKED"
            assert dc["note"] == "DESCENDANT_RULES_NOT_CONFIGURED"
        finally:
            td.cleanup()

    def test_hierarchy_missing(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}])
            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
            }])
            result = _run_checker_hardened(sf, expected_returncode=0)
            dc = result["per_target_results"][0]["checks"]["descendants"]
            assert dc["result"] == "NOT_CHECKED"
            assert dc["note"] == "HIERARCHY_NOT_CONFIGURED"
        finally:
            td.cleanup()


class TestForbiddenQuestionMarkGlob:
    def test_question_mark_matches_single_char(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Temp1"}]})
            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_descendant_name_patterns": ["Temp?"]},
            }])
            result = _run_checker_hardened(sf, expected_returncode=1)
            fb = result["per_target_results"][0]["checks"]["descendants"]["forbidden"]
            assert fb["result"] == "FAIL"
            assert fb["failure_code"] == "FORBIDDEN_DESCENDANT_NAME"
            assert "Temp1" in fb["forbidden_match_names"]
        finally:
            td.cleanup()


class TestForbiddenDeepDescendant:
    def test_third_level_deep_forbidden_match(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Level1"}]},
                grandchildren_map={"Level1": [{"name": "Level2"}]})
            add_script = f'''
import bpy
bpy.ops.wm.open_mainfile(filepath=r"{os.path.join(td.name, 'test.blend')}")
L3 = bpy.data.objects.new("ForbiddenDeep", None)
bpy.context.scene.collection.objects.link(L3)
L3.parent = bpy.data.objects["Level2"]
bpy.ops.wm.save_as_mainfile(filepath=r"{os.path.join(td.name, 'test.blend')}")
'''
            sf3 = os.path.join(td.name, "add_l3.py")
            with open(sf3, "w") as f: f.write(add_script)
            r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf3],
                               capture_output=True, text=True)
            os.unlink(sf3)
            assert r.returncode == 0

            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_descendant_name_patterns": ["*deep*"]},
            }])
            result = _run_checker_hardened(sf, expected_returncode=1)
            dd = result["per_target_results"][0]["checks"]["descendants"]
            assert dd["result"] == "FAIL"
            assert "ForbiddenDeep" in dd["forbidden"]["forbidden_match_names"]
        finally:
            td.cleanup()


class TestForbiddenOtherScene:
    def test_other_scene_forbidden_not_triggered(self):
        td = tempfile.TemporaryDirectory()
        try:
            script = f'''
import bpy
s1 = bpy.context.scene
s1.name = "TargetScene"
s1.render.engine = "BLENDER_EEVEE"
R = bpy.data.objects.new("R", None)
s1.collection.objects.link(R)
bpy.ops.scene.new(type="NEW")
s2 = bpy.context.scene
s2.name = "OtherScene"
s2.render.engine = "BLENDER_EEVEE"
Bad = bpy.data.objects.new("ForbiddenObj", None)
s2.collection.objects.link(Bad)
Bad.parent = R
bpy.ops.wm.save_as_mainfile(filepath=r"{os.path.join(td.name, 'test.blend')}")
'''
            sf = os.path.join(td.name, "make_blend.py")
            with open(sf, "w") as f: f.write(script)
            r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf],
                               capture_output=True, text=True)
            os.unlink(sf)
            assert r.returncode == 0

            sf2 = _make_spec_d(td.name, scene_name="TargetScene", targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_descendant_name_patterns": ["*Forbidden*"]},
            }])
            result = _run_checker_hardened(sf2, expected_returncode=0)
            assert result["per_target_results"][0]["overall"] == "PASS"
            fb = result["per_target_results"][0]["checks"]["descendants"]["forbidden"]
            assert fb["result"] == "PASS"
            assert fb["forbidden_match_names"] == []
        finally:
            td.cleanup()


class TestForbiddenRequiredBothFail:
    def test_required_and_forbidden_both_fail(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "TempBody"}]})
            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {
                    "required_descendant_names": ["RequiredMissing"],
                    "forbidden_descendant_name_patterns": ["*temp*"],
                },
            }])
            result = _run_checker_hardened(sf, expected_returncode=1)
            t = result["per_target_results"][0]
            assert t["overall"] == "FAIL"
            dc = t["checks"]["descendants"]
            assert dc["result"] == "FAIL"
            assert dc["required"]["result"] == "FAIL"
            assert dc["required"]["required_missing_names"] == ["RequiredMissing"]
            assert dc["forbidden"]["result"] == "FAIL"
            assert dc["forbidden"]["forbidden_match_names"] == ["TempBody"]
        finally:
            td.cleanup()


class TestForbiddenExplicitNull:
    def test_forbidden_explicit_null_not_checked(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Body"}]})
            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {
                    "required_descendant_names": ["Body"],
                    "forbidden_descendant_name_patterns": None,
                },
            }])
            result = _run_checker_hardened(sf, expected_returncode=0)
            dc = result["per_target_results"][0]["checks"]["descendants"]
            assert dc["result"] == "PASS"
            assert dc["required"]["result"] == "PASS"
            assert dc["forbidden"]["result"] == "NOT_CHECKED"
            assert dc["forbidden"]["forbidden_patterns"] is None
            assert dc["forbidden"]["forbidden_match_names"] is None
            assert dc["forbidden"]["note"] == "FORBIDDEN_DESCENDANT_NAME_PATTERNS_NOT_CONFIGURED"
        finally:
            td.cleanup()


class TestForbiddenExactPatternSimilarName:
    def test_exact_pattern_not_match_dot_001(self):
        td = tempfile.TemporaryDirectory()
        try:
            script = f'''
import bpy
scene = bpy.context.scene
scene.name = "Scene"
scene.render.engine = "BLENDER_EEVEE"
R = bpy.data.objects.new("R", None)
scene.collection.objects.link(R)
c = bpy.data.objects.new("Obj.001", None)
scene.collection.objects.link(c)
c.parent = R
bpy.ops.wm.save_as_mainfile(filepath=r"{os.path.join(td.name, 'test.blend')}")
'''
            sf = os.path.join(td.name, "make_blend.py")
            with open(sf, "w") as f: f.write(script)
            r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf],
                               capture_output=True, text=True)
            os.unlink(sf)
            assert r.returncode == 0

            sf2 = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_descendant_name_patterns": ["Obj"]},
            }])
            result = _run_checker_hardened(sf2, expected_returncode=0)
            assert result["per_target_results"][0]["overall"] == "PASS"
            dd = result["per_target_results"][0]["checks"]["descendants"]
            assert dd["result"] == "PASS"
            fb = dd["forbidden"]
            assert fb["result"] == "PASS"
            assert fb["forbidden_match_names"] == []
        finally:
            td.cleanup()


class TestForbiddenMatchNamesOrder:
    def test_forbidden_match_names_explicitly_sorted(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_blend_with_tree(td.name, "test.blend", root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "betaTemp"}, {"name": "AlphaTemp"}, {"name": "alphaTemp"}]})
            sf = _make_spec_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
                "geometry_scope": "SELF_MESH",
                "hierarchy": {"forbidden_descendant_name_patterns": ["*Temp*"]},
            }])
            result = _run_checker_hardened(sf, expected_returncode=1)
            fb = result["per_target_results"][0]["checks"]["descendants"]["forbidden"]
            assert fb["result"] == "FAIL"
            assert fb["forbidden_match_names"] == ["AlphaTemp", "alphaTemp", "betaTemp"]
        finally:
            td.cleanup()


class TestHardenedHelperNegative:
    """Negative tests for _run_checker_hardened — no Blender execution."""

    class FakeResult:
        def __init__(self, rc, out, err):
            self.returncode = rc
            self.stdout = out
            self.stderr = err

    def test_wrong_returncode_rejected(self, monkeypatch):
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: self.FakeResult(1, 'PHASE3_RESULT_JSON={"result":"PASS"}\n', ""))
        with pytest.raises(AssertionError, match="returncode"):
            _run_checker_hardened("fake.json", expected_returncode=0)

    def test_missing_result_json_rejected(self, monkeypatch):
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: self.FakeResult(0, "no result here\n", ""))
        with pytest.raises(AssertionError, match="PHASE3_RESULT_JSON"):
            _run_checker_hardened("fake.json", expected_returncode=0)

    def test_duplicate_result_json_rejected(self, monkeypatch):
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: self.FakeResult(0, 'PHASE3_RESULT_JSON={"a":1}\nPHASE3_RESULT_JSON={"b":2}\n', ""))
        with pytest.raises(AssertionError, match="PHASE3_RESULT_JSON"):
            _run_checker_hardened("fake.json", expected_returncode=0)

    def test_invalid_json_rejected(self, monkeypatch):
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: self.FakeResult(0, "PHASE3_RESULT_JSON=not valid json\n", ""))
        with pytest.raises(AssertionError, match="Invalid PHASE3_RESULT_JSON"):
            _run_checker_hardened("fake.json", expected_returncode=0)

    def test_stderr_traceback_rejected(self, monkeypatch):
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: self.FakeResult(0, 'PHASE3_RESULT_JSON={"result":"PASS"}\n', "Traceback (most recent call last):\n"))
        with pytest.raises(AssertionError, match="Traceback"):
            _run_checker_hardened("fake.json", expected_returncode=0)

    def test_stderr_assertion_error_rejected(self, monkeypatch):
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: self.FakeResult(0, 'PHASE3_RESULT_JSON={"result":"PASS"}\n', "AssertionError: failed\n"))
        with pytest.raises(AssertionError, match="AssertionError"):
            _run_checker_hardened("fake.json", expected_returncode=0)
