"""Tests for 14B-2D-I2B2: lookup error priority order verification."""
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
    assert r.returncode == 0, r.stdout + "\n" + r.stderr
    assert "PASS=OK" in r.stdout, r.stdout + "\n" + r.stderr
    assert "Traceback" not in r.stderr, r.stdout + "\n" + r.stderr
    assert "AssertionError" not in r.stderr, r.stdout + "\n" + r.stderr
    return r


def _base(body):
    body_indented = "\n".join("    " + line for line in body.split("\n"))
    return f'''
import json, sys, os, traceback
sys.path.insert(0, r"{DEPS_SITE}")
sys.path.insert(0, r"{PROJECT_ROOT}")
from protocol_guard.phase3_min.blender_scene_reader import _check_descendants

class FOTrack:
    def __init__(self, name, otype="EMPTY", objects_ok=True, children_ok=True,
                 name_ok=True, type_ok=True):
        self.name_val = name; self._otype = otype
        self._objects_ok = objects_ok; self._children_ok = children_ok
        self._name_ok = name_ok; self._type_ok = type_ok
        self._kids = []
        self.reads = {{"name": False, "children": False, "type": False}}
    @property
    def name(self):
        self.reads["name"] = True
        if not self._name_ok: raise RuntimeError("name failed")
        return self.name_val
    @property
    def children(self):
        self.reads["children"] = True
        if not self._children_ok: raise RuntimeError("children failed")
        return self._kids
    @property
    def type(self):
        self.reads["type"] = True
        if not self._type_ok: raise RuntimeError("type failed")
        return self._otype

class FSTrack:
    def __init__(self, objs, objects_ok=True):
        self._objs = list(objs); self._objects_ok = objects_ok
    @property
    def objects(self):
        if not self._objects_ok: raise RuntimeError("objects failed")
        return self._objs

try:
{body_indented}
except Exception:
    traceback.print_exc()
    sys.exit(1)
'''


class TestSceneObjectsErrorStopsTypeRead:
    def test_scene_objects_error_no_type_read(self):
        r = _run_blender(_base('''
body = FOTrack("Body", type_ok=False)
root = FOTrack("R"); root._kids = [body]
scene = FSTrack([root, body], objects_ok=False)
t = {"hierarchy": {"required_descendant_types": {"Body": "MESH"}}}
result = _check_descendants(scene, root, t)
assert result["result"] == "ERROR"
assert result["error_type"] == "DESCENDANT_LOOKUP_ERROR"
assert result["operation"] == "READ_SCENE_OBJECTS"
assert body.reads["type"] == False
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestRootChildrenErrorStopsTypeRead:
    def test_root_children_error_no_type_read(self):
        r = _run_blender(_base('''
body = FOTrack("Body", type_ok=False)
root = FOTrack("R", children_ok=False); root._kids = [body]
scene = FSTrack([root, body])
t = {"hierarchy": {"required_descendant_types": {"Body": "MESH"}}}
result = _check_descendants(scene, root, t)
assert result["result"] == "ERROR"
assert result["error_type"] == "DESCENDANT_LOOKUP_ERROR"
assert result["operation"] == "READ_ROOT_CHILDREN"
assert body.reads["type"] == False
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestDescendantNameErrorStopsChildrenAndType:
    def test_name_error_no_children_or_type_read(self):
        r = _run_blender(_base('''
body = FOTrack("Body", name_ok=False, type_ok=False)
root = FOTrack("R"); root._kids = [body]
scene = FSTrack([root, body])
t = {"hierarchy": {"required_descendant_types": {"Body": "MESH"}}}
result = _check_descendants(scene, root, t)
assert result["result"] == "ERROR"
assert result["error_type"] == "DESCENDANT_LOOKUP_ERROR"
assert result["operation"] == "READ_DESCENDANT_NAME"
assert body.reads["children"] == False
assert body.reads["type"] == False
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestDescendantChildrenErrorStopsTypeRead:
    def test_children_error_no_type_read(self):
        r = _run_blender(_base('''
body = FOTrack("Body", children_ok=False, type_ok=False)
root = FOTrack("R"); root._kids = [body]
scene = FSTrack([root, body])
t = {"hierarchy": {"required_descendant_types": {"Body": "MESH"}}}
result = _check_descendants(scene, root, t)
assert result["result"] == "ERROR"
assert result["error_type"] == "DESCENDANT_LOOKUP_ERROR"
assert result["operation"] == "READ_DESCENDANT_CHILDREN"
assert body.reads["type"] == False
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestAllNormalThenTypeError:
    def test_all_four_normal_then_type_error(self):
        r = _run_blender(_base('''
body = FOTrack("Body", type_ok=False)
root = FOTrack("R"); root._kids = [body]
scene = FSTrack([root, body])
t = {"hierarchy": {"required_descendant_types": {"Body": "MESH"}}}
result = _check_descendants(scene, root, t)
assert result["result"] == "ERROR"
assert result["error_type"] == "DESCENDANT_LOOKUP_ERROR"
assert result["operation"] == "READ_DESCENDANT_TYPE"
assert body.reads["name"] == True
assert body.reads["children"] == True
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestTypeErrorStillPrecedesAmbiguity:
    def test_type_error_before_ambiguity_preserved(self):
        r = _run_blender(_base('''
d1 = FOTrack("Body", type_ok=False)
d2 = FOTrack("Body")
root = FOTrack("R"); root._kids = [d1, d2]
scene = FSTrack([root, d1, d2])
t = {"hierarchy": {"required_descendant_types": {"Body": "MESH"}}}
result = _check_descendants(scene, root, t)
assert result["result"] == "ERROR"
assert result["error_type"] == "DESCENDANT_LOOKUP_ERROR"
assert result["operation"] == "READ_DESCENDANT_TYPE"
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestErrorResultOmitsFields:
    def test_name_error_omits_normal_fields(self):
        r = _run_blender(_base('''
body = FOTrack("Body", name_ok=False)
root = FOTrack("R"); root._kids = [body]
scene = FSTrack([root, body])
t = {"hierarchy": {
    "required_descendant_names": ["Body"],
    "required_descendant_types": {"Body": "MESH"},
    "forbidden_descendant_name_patterns": ["*"],
}}
result = _check_descendants(scene, root, t)
assert result["result"] == "ERROR"
assert "actual_names" not in result
assert "required" not in result
assert "forbidden" not in result
assert "required_types" not in result
assert "ambiguous_name_counts" not in result
print("PASS=OK")
'''))
        assert r.returncode == 0
