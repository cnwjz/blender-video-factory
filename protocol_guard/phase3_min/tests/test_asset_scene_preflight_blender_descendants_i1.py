"""Tests for 14B-2C-I1: required descendant name checking.

These tests run via subprocess to Blender 5.1.2.
"""
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


def _make_test_blend_with_grandchildren(tmp_dir, blend_name, scene_name="Scene",
                                          render_engine="BLENDER_EEVEE",
                                          root_objects=None, children_map=None,
                                          grandchildren_map=None):
    obj_lines = ""
    if root_objects:
        for obj_spec in root_objects:
            oname = obj_spec["name"]
            otype = obj_spec["type"]
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
    r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf],
                       capture_output=True, text=True)
    os.unlink(sf)
    assert r.returncode == 0, f"Blend creation failed: {r.stderr}"
    return os.path.join(tmp_dir, blend_name)


def _make_spec_file_d(tmp_dir, **overrides):
    spec = {
        "schema_version": "1",
        "checker": "asset_scene_preflight_check",
        "source_requirement_version": "Blender 固定资产模板路线 v4",
        "repository_root": tmp_dir.replace("\\", "/"),
        "blend_path": overrides.pop("blend_path", "test.blend"),
        "scene_name": overrides.pop("scene_name", "Scene"),
        "targets": overrides.pop("targets", [{"target_id": "T", "root_object_name": "R",
            "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH"}]),
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
         "--spec", spec_path,
         "--dependency-site-packages", DEPS_SITE],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    lines = r.stdout.split("\n")
    result_lines = [l for l in lines if l.startswith("PHASE3_RESULT_JSON=")]
    result_line = result_lines[0] if len(result_lines) == 1 else None
    line_count = len(result_lines)
    return (r.returncode, r.stdout, r.stderr, result_line, line_count)


# ════════════════ 14B-2C-I1 Tests ════════════════

class TestDescendantsBasicPass:
    def test_required_is_direct_child(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_grandchildren(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Armature"}, {"name": "Body"}]})
            sf = _make_spec_file_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_descendant_names": ["Body"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 0
            assert lcount == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "PASS"
            dd = result["per_target_results"][0]["checks"]["descendants"]
            assert dd["result"] == "PASS"
            assert dd["required"]["result"] == "PASS"
            assert dd["required"]["required_missing_names"] == []
        finally:
            td.cleanup()

    def test_required_is_grandchild(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_grandchildren(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Child"}]},
                grandchildren_map={"Child": [{"name": "Grandchild"}]})
            sf = _make_spec_file_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_descendant_names": ["Grandchild"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 0
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "PASS"
            dd = result["per_target_results"][0]["checks"]["descendants"]
            assert dd["result"] == "PASS"
            assert "Grandchild" in dd["actual_names"]
        finally:
            td.cleanup()

    def test_required_is_deep_descendant(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_grandchildren(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "L1"}]},
                grandchildren_map={"L1": [{"name": "L2"}]})
            # Add L3 under L2
            add_script = f'''
import bpy
bpy.ops.wm.open_mainfile(filepath=r"{os.path.join(td.name, 'test.blend')}")
L3 = bpy.data.objects.new("L3", None)
bpy.context.scene.collection.objects.link(L3)
L3.parent = bpy.data.objects["L2"]
bpy.ops.wm.save_as_mainfile(filepath=r"{os.path.join(td.name, 'test.blend')}")
'''
            sf3 = os.path.join(td.name, "add_l3.py")
            with open(sf3, "w") as f: f.write(add_script)
            r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf3],
                               capture_output=True, text=True)
            os.unlink(sf3)
            assert r.returncode == 0

            sf = _make_spec_file_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_descendant_names": ["L3"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 0
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "PASS"
        finally:
            td.cleanup()

    def test_multiple_required_all_exist(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_grandchildren(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Armature"}]},
                grandchildren_map={"Armature": [{"name": "Bone"}]})
            sf = _make_spec_file_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_descendant_names": ["Armature", "Bone"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 0
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dd = result["per_target_results"][0]["checks"]["descendants"]
            assert dd["result"] == "PASS"
            assert dd["required"]["required_missing_names"] == []
        finally:
            td.cleanup()


class TestDescendantsFail:
    def test_one_required_missing(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_grandchildren(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Armature"}]})
            sf = _make_spec_file_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_descendant_names": ["Armature", "Body"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dd = result["per_target_results"][0]["checks"]["descendants"]
            assert dd["result"] == "FAIL"
            assert dd["required"]["result"] == "FAIL"
            assert dd["required"]["failure_code"] == "REQUIRED_DESCENDANT_MISSING"
            assert "Body" in dd["required"]["required_missing_names"]
        finally:
            td.cleanup()

    def test_multiple_required_missing(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_grandchildren(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Armature"}]})
            sf = _make_spec_file_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_descendant_names": ["Body", "Head"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dd = result["per_target_results"][0]["checks"]["descendants"]
            assert dd["result"] == "FAIL"
            assert len(dd["required"]["required_missing_names"]) == 2
        finally:
            td.cleanup()

    def test_case_sensitive_required(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_grandchildren(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "armature"}]})
            sf = _make_spec_file_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_descendant_names": ["Armature"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dd = result["per_target_results"][0]["checks"]["descendants"]
            assert dd["result"] == "FAIL"
            assert "Armature" in dd["required"]["required_missing_names"]
        finally:
            td.cleanup()

    def test_similar_name_not_match(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_grandchildren(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "BodySimilar"}]})
            sf = _make_spec_file_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_descendant_names": ["Body"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dd = result["per_target_results"][0]["checks"]["descendants"]
            assert dd["result"] == "FAIL"
        finally:
            td.cleanup()

    def test_root_name_not_considered_descendant(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_grandchildren(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Child"}]})
            sf = _make_spec_file_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_descendant_names": ["R"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dd = result["per_target_results"][0]["checks"]["descendants"]
            assert dd["result"] == "FAIL"
            assert "R" in dd["required"]["required_missing_names"]
        finally:
            td.cleanup()


class TestDescendantsSceneScope:
    def test_descendant_only_in_other_scene(self):
        td = tempfile.TemporaryDirectory()
        try:
            # Create blend with two scenes, descendant only in other scene
            script = f'''
import bpy
s1 = bpy.context.scene
s1.name = "TargetScene"
s1.render.engine = "BLENDER_EEVEE"
bpy.ops.scene.new(type='NEW')
s2 = bpy.context.scene
s2.name = "OtherScene"
s2.render.engine = "BLENDER_EEVEE"
R = bpy.data.objects.new("R", None)
s1.collection.objects.link(R)
Child = bpy.data.objects.new("Child", None)
s2.collection.objects.link(Child)
Child.parent = R
bpy.ops.wm.save_as_mainfile(filepath=r"{os.path.join(td.name, 'test.blend')}")
'''
            sf = os.path.join(td.name, "make_blend.py")
            with open(sf, "w") as f: f.write(script)
            r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf],
                               capture_output=True, text=True)
            os.unlink(sf)
            assert r.returncode == 0

            sf2 = _make_spec_file_d(td.name, scene_name="TargetScene", targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_descendant_names": ["Child"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf2)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dd = result["per_target_results"][0]["checks"]["descendants"]
            assert dd["result"] == "FAIL"
        finally:
            td.cleanup()

    def test_intermediate_not_in_scene_cuts_branch(self):
        td = tempfile.TemporaryDirectory()
        try:
            script = f'''
import bpy
s1 = bpy.context.scene
s1.name = "TargetScene"
s1.render.engine = "BLENDER_EEVEE"
bpy.ops.scene.new(type='NEW')
s2 = bpy.context.scene
s2.name = "OtherScene"
s2.render.engine = "BLENDER_EEVEE"
R = bpy.data.objects.new("R", None)
s1.collection.objects.link(R)
Mid = bpy.data.objects.new("Mid", None)
s2.collection.objects.link(Mid)  # Mid is in OtherScene, not TargetScene
Mid.parent = R
Deep = bpy.data.objects.new("Deep", None)
s2.collection.objects.link(Deep)
Deep.parent = Mid
bpy.ops.wm.save_as_mainfile(filepath=r"{os.path.join(td.name, 'test.blend')}")
'''
            sf = os.path.join(td.name, "make_blend.py")
            with open(sf, "w") as f: f.write(script)
            r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf],
                               capture_output=True, text=True)
            os.unlink(sf)
            assert r.returncode == 0

            sf2 = _make_spec_file_d(td.name, scene_name="TargetScene", targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_descendant_names": ["Deep"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf2)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dd = result["per_target_results"][0]["checks"]["descendants"]
            assert dd["result"] == "FAIL"
            assert "Deep" in dd["required"]["required_missing_names"]
        finally:
            td.cleanup()


class TestDescendantsConfig:
    def test_field_missing(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_grandchildren(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Child"}]})
            sf = _make_spec_file_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 0
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dd = result["per_target_results"][0]["checks"]["descendants"]
            assert dd["result"] == "NOT_CHECKED"
            assert dd["note"] == "HIERARCHY_NOT_CONFIGURED"
        finally:
            td.cleanup()

    def test_field_empty_array(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_grandchildren(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Child"}]})
            sf = _make_spec_file_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_descendant_names": []},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 0
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dd = result["per_target_results"][0]["checks"]["descendants"]
            assert dd["result"] == "PASS"
            assert "Child" in dd["actual_names"]
            assert dd["required"]["required_expected_names"] == []
        finally:
            td.cleanup()

    def test_duplicate_values_dedup(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_grandchildren(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Armature"}]})
            sf = _make_spec_file_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_descendant_names": ["Armature", "Armature"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 0
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dd = result["per_target_results"][0]["checks"]["descendants"]
            assert dd["result"] == "PASS"
            assert dd["required"]["required_expected_names"] == ["Armature"]
        finally:
            td.cleanup()

    def test_invalid_empty_string_preopen_error(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_grandchildren(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}])
            sf = _make_spec_file_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_descendant_names": [""]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 2
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "ERROR"
            assert any("INVALID_DESCENDANT_RULE_VALUE" in e for e in result["input_errors"])
        finally:
            td.cleanup()

    def test_invalid_non_string_preopen_error(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_grandchildren(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}])
            sf = _make_spec_file_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_descendant_names": [123]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 2
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            assert result["result"] == "ERROR"
            assert any("INVALID_DESCENDANT_RULE_VALUE" in e for e in result["input_errors"])
        finally:
            td.cleanup()


class TestDescendantsPrecondition:
    def test_root_not_found_descendants_not_checked(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_grandchildren(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "Other", "type": "EMPTY"}])
            sf = _make_spec_file_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "Missing",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_descendant_names": ["X"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dd = result["per_target_results"][0]["checks"]["descendants"]
            assert dd["result"] == "NOT_CHECKED"
            assert dd["note"] == "ROOT_OBJECT_NOT_FOUND"
        finally:
            td.cleanup()

    def test_type_mismatch_descendants_not_checked(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_grandchildren(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "MESH"}],
                children_map={"R": [{"name": "Child"}]})
            sf = _make_spec_file_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_descendant_names": ["Child"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dd = result["per_target_results"][0]["checks"]["descendants"]
            assert dd["result"] == "NOT_CHECKED"
            assert dd["note"] == "ROOT_OBJECT_TYPE_MISMATCH"
        finally:
            td.cleanup()


class TestDescendantsVsDirectChildren:
    def test_grandchild_not_satisfy_direct_required(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_grandchildren(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Child"}]},
                grandchildren_map={"Child": [{"name": "Grandchild"}]})
            sf = _make_spec_file_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {
                    "required_direct_child_names": ["Grandchild"],
                    "required_descendant_names": ["Grandchild"],
                },
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 1  # FAIL due to missing direct child
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dc = result["per_target_results"][0]["checks"]["direct_children"]
            dd = result["per_target_results"][0]["checks"]["descendants"]
            assert dc["required"]["result"] == "FAIL"  # Grandchild not a direct child
            assert dd["required"]["result"] == "PASS"  # But IS a descendant
            assert "Grandchild" in dc["required"]["required_missing_names"]
            assert dd["required"]["required_missing_names"] == []
        finally:
            td.cleanup()


class TestDescendantsDeterminism:
    def test_stable_sorting(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_grandchildren(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "ZChild"}]},
                grandchildren_map={"ZChild": [{"name": "AChild"}]})
            sf = _make_spec_file_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_descendant_names": ["ZChild", "AChild"]},
            }])
            _, _, _, r1, l1 = _run_checker(sf)
            _, _, _, r2, l2 = _run_checker(sf)
            assert l1 == 1 and l2 == 1
            assert r1 == r2
        finally:
            td.cleanup()

    def test_blend_sha256_unchanged(self):
        td = tempfile.TemporaryDirectory()
        try:
            bp = _make_test_blend_with_grandchildren(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "Armature"}]},
                grandchildren_map={"Armature": [{"name": "Bone"}]})
            sha_before = _sha256_file(bp)
            sf = _make_spec_file_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_descendant_names": ["Armature", "Bone"]},
            }])
            _run_checker(sf)
            sha_after = _sha256_file(bp)
            assert sha_before == sha_after
        finally:
            td.cleanup()


# ════════════════ 14B-2C-I1-R1 Additional Tests ════════════════


class TestDescendantsNullField:
    def test_field_explicit_null(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_grandchildren(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}])
            sf = _make_spec_file_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_descendant_names": None},
            }])
            rc, _, _, rline, lcount = _run_checker(sf)
            assert rc == 0
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dd = result["per_target_results"][0]["checks"]["descendants"]
            assert dd["result"] == "NOT_CHECKED"
            assert dd["note"] == "DESCENDANT_RULES_NOT_CONFIGURED"
        finally:
            td.cleanup()


class TestDescendantsMultiScene:
    def test_descendant_linked_to_both_scenes_counted_once(self):
        td = tempfile.TemporaryDirectory()
        try:
            script = f'''
import bpy
s1 = bpy.context.scene
s1.name = "TargetScene"
s1.render.engine = "BLENDER_EEVEE"
R = bpy.data.objects.new("R", None)
s1.collection.objects.link(R)
Child = bpy.data.objects.new("Child", None)
s1.collection.objects.link(Child)
Child.parent = R
bpy.ops.scene.new(type='NEW')
s2 = bpy.context.scene
s2.name = "OtherScene"
s2.render.engine = "BLENDER_EEVEE"
s2.collection.objects.link(Child)
bpy.ops.wm.save_as_mainfile(filepath=r"{os.path.join(td.name, 'test.blend')}")
'''
            sf = os.path.join(td.name, "make_blend.py")
            with open(sf, "w") as f: f.write(script)
            r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf],
                               capture_output=True, text=True)
            os.unlink(sf)
            assert r.returncode == 0

            sf2 = _make_spec_file_d(td.name, scene_name="TargetScene", targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_descendant_names": ["Child"]},
            }])
            rc, _, _, rline, lcount = _run_checker(sf2)
            assert rc == 0
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            dd = result["per_target_results"][0]["checks"]["descendants"]
            assert dd["result"] == "PASS"
            assert dd["actual_names"].count("Child") == 1
        finally:
            td.cleanup()


class TestDescendantsAmbiguousRoot:
    def test_ambiguous_root_descendants_not_checked(self):
        td = tempfile.TemporaryDirectory()
        try:
            test_script = f'''
import bpy, json, sys, os
sys.path.insert(0, r"{DEPS_SITE}")
sys.path.insert(0, r"{PROJECT_ROOT}")
from protocol_guard.phase3_min.blender_scene_reader import _check_root_objects

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

class FakeDupObj:
    def __init__(self, name):
        self.name = name
        self.type = "EMPTY"
    @property
    def children(self):
        return []

class FakeScene:
    def __init__(self, objs):
        self.objects = list(objs)

o1 = FakeDupObj("SameName")
o2 = FakeDupObj("SameName")
fake_scene = FakeScene([o1, o2])

targets = [{{
    "target_id": "A",
    "root_object_name": "SameName",
    "expected_root_type": "EMPTY",
    "hierarchy": {{"required_descendant_names": ["X"]}},
}}]
results = _check_root_objects(fake_scene, targets)
t = results[0]
assert t["overall"] == "ERROR"
dd = t["checks"]["descendants"]
assert dd["result"] == "NOT_CHECKED"
assert dd["note"] == "AMBIGUOUS_ROOT_OBJECT_NAME"
print("PASS=OK")
'''
            sf = os.path.join(td.name, "run.py")
            with open(sf, "w") as f: f.write(test_script)
            r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            os.unlink(sf)
            assert r.returncode == 0, f"Blender failed: {r.stderr[-300:]}"
            result_lines = [l for l in r.stdout.split("\n") if l.startswith("PASS=")]
            assert len(result_lines) == 1, f"Got {len(result_lines)} PASS lines, stderr: {r.stderr[-300:]}"
            assert result_lines[0] == "PASS=OK"
        finally:
            td.cleanup()


class TestDescendantsNameOrder:
    def test_actual_names_sorted(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_grandchildren(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}],
                children_map={"R": [{"name": "ZChild"}]},
                grandchildren_map={"ZChild": [{"name": "AChild"}]})
            sf = _make_spec_file_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_descendant_names": []},
            }])
            _, _, _, rline, lcount = _run_checker(sf)
            assert lcount == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            actual = result["per_target_results"][0]["checks"]["descendants"]["actual_names"]
            assert actual == ["AChild", "ZChild"]  # casefold order
        finally:
            td.cleanup()

    def test_required_missing_names_sorted(self):
        td = tempfile.TemporaryDirectory()
        try:
            _make_test_blend_with_grandchildren(td.name, "test.blend", "Scene", "BLENDER_EEVEE",
                root_objects=[{"name": "R", "type": "EMPTY"}])
            sf = _make_spec_file_d(td.name, targets=[{
                "target_id": "A", "root_object_name": "R",
                "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH",
                "hierarchy": {"required_descendant_names": ["ZName", "AName"]},
            }])
            _, _, _, rline, lcount = _run_checker(sf)
            assert lcount == 1
            result = json.loads(rline[len("PHASE3_RESULT_JSON="):])
            missing = result["per_target_results"][0]["checks"]["descendants"]["required"]["required_missing_names"]
            assert missing == ["AName", "ZName"]  # casefold order
        finally:
            td.cleanup()
