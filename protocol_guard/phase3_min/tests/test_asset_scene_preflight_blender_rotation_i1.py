"""Tests for Rotation I1: NOT_CHECKED semantics + integration."""
import ast
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

import pytest

_bpy = types.ModuleType("bpy")
sys.modules["bpy"] = _bpy

from protocol_guard.phase3_min.blender_scene_reader import _check_rotation, _check_root_objects
from protocol_guard.phase3_min.asset_scene_preflight_check import _validate_rotation_rules_preopen


def _rot_spec(erw=None, tol=None):
    d = {}
    if erw is not None: d["expected_world_rotation_euler_degrees"] = erw
    if tol is not None: d["rotation_tolerance_degrees"] = tol
    return {"rotation": d}


class TestNotChecked:
    def test_rotation_missing(self):
        r = _check_rotation({}, None)
        assert r == {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"}

    def test_rotation_null(self):
        r = _check_rotation({"rotation": None}, None)
        assert r == {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"}

    def test_rotation_empty(self):
        r = _check_rotation({"rotation": {}}, None)
        assert r == {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"}

    def test_erw_none_tol_present(self):
        r = _check_rotation(_rot_spec(erw=None, tol=2.0), None)
        assert r == {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"}

    def test_both_none(self):
        r = _check_rotation(_rot_spec(erw=None, tol=None), None)
        assert r == {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"}

    def test_only_tolerance_present(self):
        r = _check_rotation(_rot_spec(tol=2.0), None)
        assert r == {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"}


class TestI3Boundary:
    def test_quaternion_code_present(self):
        src = open(os.path.join(ROOT, "protocol_guard", "phase3_min",
                                 "blender_scene_reader.py"), encoding="utf-8").read()
        fn = None
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_check_rotation":
                fn = node
                break
        assert fn is not None
        body = ast.unparse(fn)
        assert "to_quaternion" in body
        assert "quaternion_min_angle_degrees" in body


class TestPreOpen:
    def test_erw_present_tol_missing_detected(self):
        errs = _validate_rotation_rules_preopen([{
            "target_id": "A",
            "rotation": {"expected_world_rotation_euler_degrees": [0, 0, 0]},
        }])
        assert len(errs) == 1
        assert "INVALID_ROTATION_RULE_RELATION" in errs[0]

    def test_erw_present_tol_present_ok(self):
        errs = _validate_rotation_rules_preopen([{
            "target_id": "A",
            "rotation": {"expected_world_rotation_euler_degrees": [0, 0, 0],
                          "rotation_tolerance_degrees": 2.0},
        }])
        assert errs == []

    def test_erw_none_tol_none_ok(self):
        assert _validate_rotation_rules_preopen([{"target_id": "A", "rotation": {}}]) == []

    def test_rotation_not_dict_skipped(self):
        assert _validate_rotation_rules_preopen([{"target_id": "A", "rotation": None}]) == []

    def test_rotation_missing_skipped(self):
        assert _validate_rotation_rules_preopen([{"target_id": "A"}]) == []


class TestPreOpenWiring:
    def test_preopen_catches_rotation_before_path_validation(self):
        import json, tempfile, subprocess
        td = tempfile.mkdtemp()
        try:
            spec = {
                "schema_version": "1",
                "checker": "asset_scene_preflight_check",
                "source_requirement_version": "Blender 固定资产模板路线 v4",
                "spec_sha256": "0" * 64,
                "repository_root": td,
                "blend_path": "nonexistent.blend",
                "scene_name": "Scene",
                "global_rules": {},
                "targets": [{
                    "target_id": "A", "root_object_name": "Root",
                    "expected_root_type": "EMPTY",
                    "geometry_scope": "SELF_AND_DESCENDANT_MESHES",
                    "rotation": {"expected_world_rotation_euler_degrees": [0, 0, 0]},
                }],
            }
            spec_path = os.path.join(td, "spec.json")
            with open(spec_path, "w") as f: json.dump(spec, f)
            script = (
                f"import sys, os\n"
                f"sys.path.insert(0, r'{ROOT}')\n"
                f"_bpy = __import__('types').ModuleType('bpy')\n"
                f"sys.modules['bpy'] = _bpy\n"
                f"from protocol_guard.phase3_min.asset_scene_preflight_check import _validate_and_open_spec\n"
                f"code, result = _validate_and_open_spec(r'{spec_path}')\n"
                f"assert code == 2, f'exit: {{code}}'\n"
                f"errs = result.get('input_errors', [])\n"
                f"assert any('INVALID_ROTATION_RULE_RELATION' in e for e in errs), f'errs: {{errs}}'\n"
                f"print('PASS=PREOPEN_WIRED')\n"
            )
            sf = os.path.join(td, "run.py")
            with open(sf, "w") as f: f.write(script)
            r = subprocess.run(["python", sf], capture_output=True, text=True)
            assert r.returncode == 0 and "PASS=PREOPEN_WIRED" in r.stdout, (
                f"FAILED: {r.stdout} {r.stderr}"
            )
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)


class TestEntryWiring:
    def test_check_rotation_entry_and_independence(self):
        """Prove _check_rotation wired with sentinel, checks execute independently."""
        import tempfile, subprocess
        td = tempfile.mkdtemp()
        try:
            # Build script via string concatenation to avoid f-string/tab issues
            lines = [
                "import sys, os, types",
                f"sys.path.insert(0, r'{ROOT}')",
                "_bpy = types.ModuleType('bpy')",
                "sys.modules['bpy'] = _bpy",
                "_mu = types.ModuleType('mathutils')",
                "sys.modules['mathutils'] = _mu",
                "_call_counts = {}",
                "_sentinels = {'_check_rotation': {'result':'NOT_CHECKED','note':'ROTATION_I2_ENTRY_SENTINEL'}}",
                "from protocol_guard.phase3_min import blender_scene_reader as reader",
                "for name in ['_check_direct_children','_check_descendants','_check_standing_up_axis','_check_facing_forward_axis','_check_visibility','_check_rotation']:",
                "    def _wrap(fn_name):",
                "        def _w(*args):",
                "            _call_counts[fn_name] = _call_counts.get(fn_name, 0) + 1",
                "            return _sentinels.get(fn_name, {})",
                "        return _w",
                "    setattr(reader, name, _wrap(name))",
                "class Obj:",
                "    type = 'EMPTY'",
                "    name = 'Root'",
                "obj = Obj()",
                "class FS:",
                "    def __init__(self, objs): self.objects = list(objs)",
                "results = reader._check_root_objects(FS([obj]), [{'target_id':'A','root_object_name':'Root','expected_root_type':'EMPTY','rotation':{'expected_world_rotation_euler_degrees':[0,0,0],'rotation_tolerance_degrees':2.0}}])",
                "chk = results[0]['checks']",
                "assert 'rotation' in chk",
                "assert chk['rotation'] == {'result':'NOT_CHECKED','note':'ROTATION_I2_ENTRY_SENTINEL'}",
                "assert _call_counts.get('_check_rotation') == 1",
                "assert _call_counts.get('_check_standing_up_axis') == 1",
                "assert _call_counts.get('_check_facing_forward_axis') == 1",
                "assert _call_counts.get('_check_visibility') == 1",
                "assert 'overall' in results[0]",
                "print('PASS=ENTRY_WIRED')",
            ]
            script = "\n".join(lines)
            sf = os.path.join(td, "run.py")
            with open(sf, "w") as f: f.write(script)
            r = subprocess.run(["python", sf], capture_output=True, text=True)
            assert r.returncode == 0 and "PASS=ENTRY_WIRED" in r.stdout, (
                f"FAILED: {r.stdout} {r.stderr}"
            )
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)


class TestIntegration:
    def test_root_not_found_rotation_not_checked(self):
        import tempfile, subprocess
        td = tempfile.mkdtemp()
        try:
            script = (
                f"import sys, os, types\n"
                f"sys.path.insert(0, r'{ROOT}')\n"
                f"_bpy = types.ModuleType('bpy')\nsys.modules['bpy'] = _bpy\n"
                f"from protocol_guard.phase3_min.blender_scene_reader import _check_root_objects\n"
                f"class FS:\n    def __init__(self, objs): self.objects = list(objs)\n"
                f"results = _check_root_objects(FS([]), [{{'target_id':'A','root_object_name':'R','expected_root_type':'EMPTY','rotation':{{'expected_world_rotation_euler_degrees':[0,0,0],'rotation_tolerance_degrees':2.0}}}}])\n"
                f"rot = results[0]['checks']['rotation']\n"
                f"assert rot['result'] == 'NOT_CHECKED'\n"
                f"assert rot['note'] == 'ROOT_OBJECT_NOT_FOUND'\n"
                f"print('PASS=OK')\n"
            )
            sf = os.path.join(td, "run.py")
            with open(sf, "w") as f: f.write(script)
            r = subprocess.run(["python", sf], capture_output=True, text=True)
            assert r.returncode == 0 and "PASS=OK" in r.stdout, f"FAILED: {r.stdout} {r.stderr}"
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_rotation_integrated_in_checks_keys(self):
        import tempfile, subprocess
        td = tempfile.mkdtemp()
        try:
            script = (
                f"import sys, os, types\n"
                f"sys.path.insert(0, r'{ROOT}')\n"
                f"_bpy = types.ModuleType('bpy')\nsys.modules['bpy'] = _bpy\n"
                f"from protocol_guard.phase3_min.blender_scene_reader import _check_root_objects\n"
                f"class Obj:\n    type = 'MESH'\n    name = 'obj'\nobj = Obj()\n"
                f"class FS:\n    def __init__(self, objs): self.objects = list(objs)\n"
                f"results = _check_root_objects(FS([obj]), [{{'target_id':'A','root_object_name':'obj','expected_root_type':'EMPTY','rotation':{{'expected_world_rotation_euler_degrees':[0,0,0],'rotation_tolerance_degrees':2.0}}}}])\n"
                f"chk = results[0]['checks']\n"
                f"assert 'rotation' in chk\n"
                f"assert chk['rotation']['note'] == 'ROOT_OBJECT_TYPE_MISMATCH'\n"
                f"assert 'object_type' in chk\n"
                f"print('PASS=OK')\n"
            )
            sf = os.path.join(td, "run.py")
            with open(sf, "w") as f: f.write(script)
            r = subprocess.run(["python", sf], capture_output=True, text=True)
            assert r.returncode == 0 and "PASS=OK" in r.stdout, f"FAILED: {r.stdout} {r.stderr}"
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)


def test_test_file_self_parse():
    with open(__file__, "r", encoding="utf-8") as f:
        ast.parse(f.read())


def test_test_file_no_skip_xfail():
    with open(__file__, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = None
            if isinstance(node.func, ast.Attribute): name = node.func.attr
            elif isinstance(node.func, ast.Name): name = node.func.id
            if name in ("skip", "skipif", "xfail", "importorskip"):
                raise AssertionError(f"line {node.lineno}: {name}()")
