"""Tests for 14B-2D-I2B1: READ_DESCENDANT_TYPE priority over AMBIGUITY."""
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

class FO:
    def __init__(self, name, otype="EMPTY", type_ok=True):
        self.name = name; self._type = otype; self._type_ok = type_ok; self._kids = []
        self.type_read_count = 0
    @property
    def children(self): return self._kids
    @property
    def type(self):
        self.type_read_count += 1
        if not self._type_ok: raise RuntimeError("type read failed")
        return self._type

class FS:
    def __init__(self, objs): self.objects = list(objs)

try:
{body_indented}
except Exception:
    traceback.print_exc()
    sys.exit(1)
'''


class TestTypeLookupPrecedesAmbiguity:
    def test_first_dup_type_throws(self):
        r = _run_blender(_base('''
d1 = FO("Body", "MESH", type_ok=False)
d2 = FO("Body", "MESH", type_ok=True)
root = FO("R"); root._kids = [d1, d2]
scene = FS([root, d1, d2])
t = {"hierarchy": {"required_descendant_types": {"Body": "MESH"}}}
result = _check_descendants(scene, root, t)
assert result["result"] == "ERROR"
assert result["error_type"] == "DESCENDANT_LOOKUP_ERROR"
assert result["operation"] == "READ_DESCENDANT_TYPE"
assert result["descendant_name"] == "Body"
assert "actual_names" not in result
assert "ambiguous_name_counts" not in result
print("PASS=OK")
'''))
        assert r.returncode == 0

    def test_second_dup_type_throws(self):
        r = _run_blender(_base('''
d1 = FO("Body", "MESH", type_ok=True)
d2 = FO("Body", "MESH", type_ok=False)
root = FO("R"); root._kids = [d1, d2]
scene = FS([root, d1, d2])
t = {"hierarchy": {"required_descendant_types": {"Body": "MESH"}}}
result = _check_descendants(scene, root, t)
assert result["result"] == "ERROR"
assert result["error_type"] == "DESCENDANT_LOOKUP_ERROR"
assert result["descendant_name"] == "Body"
print("PASS=OK")
'''))
        assert r.returncode == 0

    def test_both_types_normal_ambiguity_wins(self):
        r = _run_blender(_base('''
d1 = FO("Body", "MESH", type_ok=True)
d2 = FO("Body", "MESH", type_ok=True)
root = FO("R"); root._kids = [d1, d2]
scene = FS([root, d1, d2])
t = {"hierarchy": {"required_descendant_types": {"Body": "MESH"}}}
result = _check_descendants(scene, root, t)
assert result["result"] == "ERROR"
assert result["error_type"] == "AMBIGUOUS_DESCENDANT_NAME"
assert result["ambiguous_name_counts"]["Body"] == 2
assert d1.type_read_count == 1
assert d2.type_read_count == 1
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestUnreferencedAmbiguityTypeNotRead:
    def test_unreferenced_duplicates_not_type_accessed(self):
        r = _run_blender(_base('''
class FORead:
    def __init__(self, name, otype="EMPTY", type_ok=True):
        self.name = name; self._type = otype; self._type_ok = type_ok; self._kids = []
        self.type_read = False
    @property
    def children(self): return self._kids
    @property
    def type(self):
        self.type_read = True
        if not self._type_ok: raise RuntimeError("type read failed")
        return self._type

d1 = FORead("Dup", "MESH", type_ok=False)
d2 = FORead("Dup", "MESH", type_ok=False)
root = FORead("R"); root._kids = [d1, d2]
scene = FS([root, d1, d2])
t = {"hierarchy": {"required_descendant_types": {"Other": "MESH"}}}
result = _check_descendants(scene, root, t)
assert result["result"] == "ERROR"
assert result["error_type"] == "AMBIGUOUS_DESCENDANT_NAME"
assert d1.type_read == False
assert d2.type_read == False
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestI2AUniquePreserved:
    def test_unique_object_type_error_still_works(self):
        r = _run_blender(_base('''
body = FO("Body", "MESH", type_ok=False)
root = FO("R"); root._kids = [body]
scene = FS([root, body])
t = {"hierarchy": {"required_descendant_types": {"Body": "MESH"}}}
result = _check_descendants(scene, root, t)
assert result["result"] == "ERROR"
assert result["error_type"] == "DESCENDANT_LOOKUP_ERROR"
assert result["operation"] == "READ_DESCENDANT_TYPE"
assert body.type_read_count == 1
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestI1NormalPreserved:
    def test_normal_type_match_still_works(self):
        r = _run_blender(_base('''
body = FO("Body", "MESH")
root = FO("R"); root._kids = [body]
scene = FS([root, body])
t = {"hierarchy": {"required_descendant_types": {"Body": "MESH"}}}
result = _check_descendants(scene, root, t)
rt = result["required_types"]
assert rt["result"] == "PASS"
assert rt["checks"][0]["result"] == "PASS"
assert body.type_read_count == 1
print("PASS=OK")
'''))
        assert r.returncode == 0

    def test_type_mismatch_still_works(self):
        r = _run_blender(_base('''
body = FO("Body", "EMPTY")
root = FO("R"); root._kids = [body]
scene = FS([root, body])
t = {"hierarchy": {"required_descendant_types": {"Body": "MESH"}}}
result = _check_descendants(scene, root, t)
rt = result["required_types"]
assert rt["result"] == "FAIL"
assert body.type_read_count == 1
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestErrorResultOmitFields:
    def test_error_omits_normal_fields(self):
        r = _run_blender(_base('''
d1 = FO("Body", "MESH", type_ok=False)
d2 = FO("Body", "MESH")
root = FO("R"); root._kids = [d1, d2]
scene = FS([root, d1, d2])
t = {"hierarchy": {
    "required_descendant_names": ["Body"],
    "required_descendant_types": {"Body": "MESH"},
    "forbidden_descendant_name_patterns": ["*"],
}}
result = _check_descendants(scene, root, t)
assert result["result"] == "ERROR"
assert result["error_type"] == "DESCENDANT_LOOKUP_ERROR"
assert "actual_names" not in result
assert "required" not in result
assert "forbidden" not in result
assert "required_types" not in result
assert "ambiguous_name_counts" not in result
print("PASS=OK")
'''))
        assert r.returncode == 0

class TestUnreferencedAmbiguityWithUniqueRefTypeError:
    def test_unreferenced_dup_unique_ref_type_error(self):
        r = _run_blender(_base('''
class FOTrack:
    def __init__(self, name, otype="EMPTY", type_ok=True):
        self.name = name; self._type = otype; self._type_ok = type_ok; self._kids = []; self.type_read = False
    @property
    def children(self): return self._kids
    @property
    def type(self):
        self.type_read = True
        if not self._type_ok: raise RuntimeError("type read failed")
        return self._type

dup1 = FOTrack("Dup")
dup2 = FOTrack("Dup")
body = FOTrack("Body", type_ok=False)
root = FOTrack("R"); root._kids = [dup1, dup2, body]
scene = FS([root, dup1, dup2, body])
t = {"hierarchy": {"required_descendant_types": {"Body": "MESH"}}}
result = _check_descendants(scene, root, t)
assert result["result"] == "ERROR"
assert result["error_type"] == "DESCENDANT_LOOKUP_ERROR"
assert result["operation"] == "READ_DESCENDANT_TYPE"
assert result["descendant_name"] == "Body"
assert dup1.type_read == False
assert dup2.type_read == False
assert body.type_read == True
print("PASS=OK")
'''))
        assert r.returncode == 0

    def test_unreferenced_dup_unique_ref_type_normal(self):
        r = _run_blender(_base('''
class FOTrack:
    def __init__(self, name, otype="EMPTY", type_ok=True):
        self.name = name; self._type = otype; self._type_ok = type_ok; self._kids = []; self.type_read = False
    @property
    def children(self): return self._kids
    @property
    def type(self):
        self.type_read = True
        if not self._type_ok: raise RuntimeError("type read failed")
        return self._type

dup1 = FOTrack("Dup")
dup2 = FOTrack("Dup")
body = FOTrack("Body", type_ok=True)
root = FOTrack("R"); root._kids = [dup1, dup2, body]
scene = FS([root, dup1, dup2, body])
t = {"hierarchy": {"required_descendant_types": {"Body": "MESH"}}}
result = _check_descendants(scene, root, t)
assert result["result"] == "ERROR"
assert result["error_type"] == "AMBIGUOUS_DESCENDANT_NAME"
assert dup1.type_read == False
assert dup2.type_read == False
assert body.type_read == True
print("PASS=OK")
'''))
        assert r.returncode == 0

class TestBuilderCacheOnly:
    def test_builder_uses_cache_not_object_type(self):
        r = _run_blender(_base('''
from protocol_guard.phase3_min.blender_scene_reader import _build_descendant_required_types

class ExplodingObj:
    def __init__(self, name):
        self.name = name
    @property
    def type(self):
        raise RuntimeError("builder must not read obj.type")
    @property
    def children(self):
        return []

obj = ExplodingObj("Body")
type_cache = {id(obj): "MESH"}
desc_items = [("Body", obj)]
req_types = {"Body": "MESH"}
result = _build_descendant_required_types(req_types, desc_items, type_cache)
assert result["result"] == "PASS"
assert result["checks"][0]["result"] == "PASS"
assert result["checks"][0]["actual_type"] == "MESH"
print("PASS=OK")
'''))
        assert r.returncode == 0

    def test_builder_ast_no_type_attribute_access(self):
        r = _run_blender(_base('''
import ast, inspect
from protocol_guard.phase3_min.blender_scene_reader import _build_descendant_required_types

source = inspect.getsource(_build_descendant_required_types)
tree = ast.parse(source)

class TypeAttrVisitor(ast.NodeVisitor):
    def __init__(self):
        self.count = 0
    def visit_Attribute(self, node):
        if isinstance(node.attr, str) and node.attr == "type":
            self.count += 1
        self.generic_visit(node)

v = TypeAttrVisitor()
v.visit(tree)
assert v.count == 0, f"builder has {v.count} obj.type attribute access nodes"
print("PASS=OK")
'''))
        assert r.returncode == 0
