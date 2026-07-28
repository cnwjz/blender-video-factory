"""Tests for 14B-2C-I3B1: DESCENDANT_LOOKUP_ERROR boundaries."""
import json, os, subprocess, sys, tempfile
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
BLENDER_EXE = r"D:\Windows software\blender\blender.exe"
DEPS_SITE = r"C:\Users\Administrator\AppData\Roaming\Python\Python314\site-packages"


def _run_blender(script):
    td = tempfile.mkdtemp()
    sf = os.path.join(td, "run.py")
    with open(sf, "w") as f: f.write(script)
    r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    os.unlink(sf)
    import shutil; shutil.rmtree(td, ignore_errors=True)
    return r


def _base_script(body):
    return f'''
import json, sys, os
sys.path.insert(0, r"{DEPS_SITE}")
sys.path.insert(0, r"{PROJECT_ROOT}")
from protocol_guard.phase3_min.blender_scene_reader import _check_descendants, _collect_descendants
from protocol_guard.phase3_min.asset_scene_preflight_check import _collect_target_errors

class FakeObj:
    def __init__(self, name, children_ok=True, name_ok=True):
        self._name = name
        self._children_ok = children_ok
        self._name_ok = name_ok
        self.type = "EMPTY"
        self._kids = []
    @property
    def name(self):
        if not self._name_ok: raise RuntimeError("name failed")
        return self._name
    @property
    def children(self):
        if not self._children_ok: raise RuntimeError("children failed")
        return self._kids

class FakeScene:
    def __init__(self, objs, objects_ok=True):
        self._objs = list(objs)
        self._objects_ok = objects_ok
    @property
    def objects(self):
        if not self._objects_ok: raise RuntimeError("objects failed")
        return self._objs

{body}
'''


class TestReadSceneObjects:
    def test_scene_objects_exception(self):
        r = _run_blender(_base_script('''
scene = FakeScene([], objects_ok=False)
root_obj = FakeObj("R")
target = {"hierarchy": {"required_descendant_names": []}}
result = _check_descendants(scene, root_obj, target)
assert result["result"] == "ERROR"
assert result["error_type"] == "DESCENDANT_LOOKUP_ERROR"
assert result["operation"] == "READ_SCENE_OBJECTS"
assert result["note"] == "READ_SCENE_OBJECTS_FAILED"
assert "actual_names" not in result
print("PASS=OK")
'''))
        assert r.returncode == 0
        assert any(l.startswith("PASS=OK") for l in r.stdout.split("\n"))


class TestReadRootChildren:
    def test_root_children_exception(self):
        r = _run_blender(_base_script('''
root_obj = FakeObj("R", children_ok=False)
child = FakeObj("Child")
root_obj._kids = [child]
scene = FakeScene([child])
target = {"hierarchy": {"required_descendant_names": []}}
result = _check_descendants(scene, root_obj, target)
assert result["result"] == "ERROR"
assert result["error_type"] == "DESCENDANT_LOOKUP_ERROR"
assert result["operation"] == "READ_ROOT_CHILDREN"
print("PASS=OK")
'''))
        assert r.returncode == 0
        assert any(l.startswith("PASS=OK") for l in r.stdout.split("\n"))


class TestReadDescendantName:
    def test_descendant_name_exception(self):
        r = _run_blender(_base_script('''
child = FakeObj("Bad", name_ok=False)
root_obj = FakeObj("R")
root_obj._kids = [child]
scene = FakeScene([child])
target = {"hierarchy": {"required_descendant_names": []}}
result = _check_descendants(scene, root_obj, target)
assert result["result"] == "ERROR"
assert result["error_type"] == "DESCENDANT_LOOKUP_ERROR"
assert result["operation"] == "READ_DESCENDANT_NAME"
print("PASS=OK")
'''))
        assert r.returncode == 0
        assert any(l.startswith("PASS=OK") for l in r.stdout.split("\n"))


class TestReadDescendantChildren:
    def test_descendant_children_exception(self):
        r = _run_blender(_base_script('''
child = FakeObj("Child", children_ok=False)
root_obj = FakeObj("R")
root_obj._kids = [child]
scene = FakeScene([child])
target = {"hierarchy": {"required_descendant_names": []}}
result = _check_descendants(scene, root_obj, target)
assert result["result"] == "ERROR"
assert result["error_type"] == "DESCENDANT_LOOKUP_ERROR"
assert result["operation"] == "READ_DESCENDANT_CHILDREN"
print("PASS=OK")
'''))
        assert r.returncode == 0
        assert any(l.startswith("PASS=OK") for l in r.stdout.split("\n"))


class TestLookupErrorPriority:
    def test_lookup_error_excludes_other_keys(self):
        r = _run_blender(_base_script('''
child = FakeObj("Child", children_ok=False)
root_obj = FakeObj("R")
root_obj._kids = [child]
scene = FakeScene([child])
target = {"hierarchy": {
    "required_descendant_names": ["Missing"],
    "forbidden_descendant_name_patterns": ["Child*"],
}}
result = _check_descendants(scene, root_obj, target)
assert result["result"] == "ERROR"
assert result["error_type"] == "DESCENDANT_LOOKUP_ERROR"
assert "actual_names" not in result
assert "ambiguous_name_counts" not in result
assert "required" not in result
assert "forbidden" not in result
print("PASS=OK")
'''))
        assert r.returncode == 0
        assert any(l.startswith("PASS=OK") for l in r.stdout.split("\n"))


class TestLookupErrorTargetOverall:
    def test_target_overall_computed_by_check_root_objects(self):
        r = _run_blender(_base_script('''
from protocol_guard.phase3_min.blender_scene_reader import _check_root_objects

child = FakeObj("Child", children_ok=False)
root_obj = FakeObj("R")
root_obj._kids = [child]
scene = FakeScene([root_obj, child])
target = {
    "target_id": "A",
    "root_object_name": "R",
    "expected_root_type": "EMPTY",
    "hierarchy": {"required_descendant_names": []},
}
results = _check_root_objects(scene, [target])
assert len(results) == 1
t = results[0]
assert t["overall"] == "ERROR"
dd = t["checks"]["descendants"]
assert dd["result"] == "ERROR"
assert dd["error_type"] == "DESCENDANT_LOOKUP_ERROR"
assert dd["operation"] == "READ_DESCENDANT_CHILDREN"
# direct_children must not mask descendants ERROR
assert t["checks"]["direct_children"]["result"] != "ERROR"

errs = _collect_target_errors(results)
assert any("DESCENDANT_LOOKUP_ERROR" in e for e in errs)
assert any("READ_DESCENDANT_CHILDREN" in e for e in errs)
print("PASS=OK")
'''))
        assert r.returncode == 0
        assert any(l.startswith("PASS=OK") for l in r.stdout.split("\n"))


class TestLookupErrorTopLevelMessage:
    def test_top_level_error_message_contains_all_fields(self):
        r = _run_blender(_base_script('''
child = FakeObj("Child", name_ok=False)
root_obj = FakeObj("R")
root_obj._kids = [child]
scene = FakeScene([child])
target = {"target_id": "A", "root_object_name": "R",
    "hierarchy": {"required_descendant_names": []}}
result = _check_descendants(scene, root_obj, target)
per_target = [{
    "target_id": "A", "root_object_name": "R",
    "checks": {
        "object_exists": {"result": "PASS"},
        "object_type": {"result": "PASS"},
        "direct_children": {"result": "NOT_CHECKED"},
        "descendants": result,
    },
    "overall": "ERROR",
}]
errs = _collect_target_errors(per_target)
assert len(errs) == 1
msg = errs[0]
assert "DESCENDANT_LOOKUP_ERROR" in msg
assert "target 'A'" in msg
assert "root_object_name 'R'" in msg
assert "operation 'READ_DESCENDANT_NAME'" in msg
print("PASS=OK")
'''))
        assert r.returncode == 0
        assert any(l.startswith("PASS=OK") for l in r.stdout.split("\n"))


class TestLookupErrorPrecedesAmbiguity:
    def test_lookup_error_returns_before_ambiguity_check(self):
        r = _run_blender(_base_script('''
dup_ok = FakeObj("Duplicate", children_ok=True)
dup_bad = FakeObj("Duplicate", children_ok=False)
root_obj = FakeObj("R")
root_obj._kids = [dup_ok, dup_bad]
scene = FakeScene([root_obj, dup_ok, dup_bad])
target = {"hierarchy": {"required_descendant_names": []}}
result = _check_descendants(scene, root_obj, target)
assert result["result"] == "ERROR"
assert result["error_type"] == "DESCENDANT_LOOKUP_ERROR"
assert result["operation"] == "READ_DESCENDANT_CHILDREN"
assert "ambiguous_name_counts" not in result
assert "actual_names" not in result
assert "required" not in result
assert "forbidden" not in result
print("PASS=OK")
'''))
        assert r.returncode == 0
        assert any(l.startswith("PASS=OK") for l in r.stdout.split("\n"))


class TestNormalPathSmoke:
    def test_two_level_normal_path_still_works(self):
        r = _run_blender(_base_script('''
child = FakeObj("Child")
grandchild = FakeObj("Grandchild")
child._kids = [grandchild]
root_obj = FakeObj("R")
root_obj._kids = [child]
scene = FakeScene([root_obj, child, grandchild])
target = {"hierarchy": {"required_descendant_names": ["Grandchild"]}}
result = _check_descendants(scene, root_obj, target)
assert result["result"] == "PASS"
assert "Child" in result["actual_names"]
assert "Grandchild" in result["actual_names"]
assert result["required"]["result"] == "PASS"
assert result["required"]["required_missing_names"] == []
assert result["forbidden"]["result"] == "NOT_CHECKED"
print("PASS=OK")
'''))
        assert r.returncode == 0
        assert any(l.startswith("PASS=OK") for l in r.stdout.split("\n"))
