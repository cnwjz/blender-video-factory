"""Tests for 14B-2D-I1B: required_descendant_types runtime checks."""
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
    def __init__(self, name, otype="EMPTY"):
        self.name = name
        self.type = otype
        self._kids = []
    @property
    def children(self):
        return self._kids

class FS:
    def __init__(self, objs):
        self.objects = list(objs)

try:
{body_indented}
except Exception:
    traceback.print_exc()
    sys.exit(1)
'''


class TestTypesFieldMissingNullEmpty:
    def test_field_missing(self):
        r = _run_blender(_base('''
root = FO("R"); root._kids = [FO("Body")]
scene = FS([root, root._kids[0]])
t = {"hierarchy": {}}
result = _check_descendants(scene, root, t)
rt = result["required_types"]
assert rt["result"] == "NOT_CHECKED"
assert rt["checks"] is None
assert "REQUIRED_DESCENDANT_TYPES_NOT_CONFIGURED" in rt["note"]
print("PASS=OK")
'''))
        assert r.returncode == 0

    def test_field_null(self):
        r = _run_blender(_base('''
root = FO("R"); root._kids = [FO("Body")]
scene = FS([root, root._kids[0]])
t = {"hierarchy": {"required_descendant_types": None}}
result = _check_descendants(scene, root, t)
rt = result["required_types"]
assert rt["result"] == "NOT_CHECKED"
print("PASS=OK")
'''))
        assert r.returncode == 0

    def test_field_empty_object(self):
        r = _run_blender(_base('''
root = FO("R"); root._kids = [FO("Body")]
scene = FS([root, root._kids[0]])
t = {"hierarchy": {"required_descendant_types": {}}}
result = _check_descendants(scene, root, t)
rt = result["required_types"]
assert rt["result"] == "PASS"
assert rt["checks"] == []
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestTypesBasicMatch:
    def test_single_direct_child_type_match(self):
        r = _run_blender(_base('''
body = FO("Body", "MESH")
root = FO("R"); root._kids = [body]
scene = FS([root, body])
t = {"hierarchy": {"required_descendant_types": {"Body": "MESH"}}}
result = _check_descendants(scene, root, t)
rt = result["required_types"]
assert rt["result"] == "PASS"
c = rt["checks"][0]
assert c["name"] == "Body"
assert c["expected_type"] == "MESH"
assert c["actual_type"] == "MESH"
assert c["result"] == "PASS"
assert "failure_code" not in c
print("PASS=OK")
'''))
        assert r.returncode == 0

    def test_deep_descendant_type_match(self):
        r = _run_blender(_base('''
deep = FO("Deep", "MESH")
mid = FO("Mid"); mid._kids = [deep]
root = FO("R"); root._kids = [mid]
scene = FS([root, mid, deep])
t = {"hierarchy": {"required_descendant_types": {"Deep": "MESH"}}}
result = _check_descendants(scene, root, t)
rt = result["required_types"]
assert rt["result"] == "PASS"
assert rt["checks"][0]["result"] == "PASS"
print("PASS=OK")
'''))
        assert r.returncode == 0

    def test_multiple_all_match(self):
        r = _run_blender(_base('''
a = FO("Armature", "ARMATURE")
b = FO("Body", "MESH")
root = FO("R"); root._kids = [a, b]
scene = FS([root, a, b])
t = {"hierarchy": {"required_descendant_types": {"Armature": "ARMATURE", "Body": "MESH"}}}
result = _check_descendants(scene, root, t)
rt = result["required_types"]
assert rt["result"] == "PASS"
for c in rt["checks"]:
    assert c["result"] == "PASS"
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestTypesNameNotFound:
    def test_name_not_found(self):
        r = _run_blender(_base('''
root = FO("R"); root._kids = [FO("Other")]
scene = FS([root, root._kids[0]])
t = {"hierarchy": {"required_descendant_types": {"Body": "MESH"}}}
result = _check_descendants(scene, root, t)
rt = result["required_types"]
assert rt["result"] == "FAIL"
c = rt["checks"][0]
assert c["name"] == "Body"
assert c["expected_type"] == "MESH"
assert c["actual_type"] is None
assert c["result"] == "FAIL"
assert c["failure_code"] == "REQUIRED_DESCENDANT_FOR_TYPE_NOT_FOUND"
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestTypesTypeMismatch:
    def test_type_mismatch(self):
        r = _run_blender(_base('''
body = FO("Body", "EMPTY")
root = FO("R"); root._kids = [body]
scene = FS([root, body])
t = {"hierarchy": {"required_descendant_types": {"Body": "MESH"}}}
result = _check_descendants(scene, root, t)
rt = result["required_types"]
assert rt["result"] == "FAIL"
c = rt["checks"][0]
assert c["result"] == "FAIL"
assert c["failure_code"] == "REQUIRED_DESCENDANT_TYPE_MISMATCH"
assert c["actual_type"] == "EMPTY"
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestTypesCaseSensitive:
    def test_name_case_sensitive(self):
        r = _run_blender(_base('''
body = FO("body", "MESH")
root = FO("R"); root._kids = [body]
scene = FS([root, body])
t = {"hierarchy": {"required_descendant_types": {"Body": "MESH"}}}
result = _check_descendants(scene, root, t)
rt = result["required_types"]
assert rt["result"] == "FAIL"
assert rt["checks"][0]["failure_code"] == "REQUIRED_DESCENDANT_FOR_TYPE_NOT_FOUND"
print("PASS=OK")
'''))
        assert r.returncode == 0

    def test_type_case_sensitive(self):
        r = _run_blender(_base('''
body = FO("Body", "mesh")
root = FO("R"); root._kids = [body]
scene = FS([root, body])
t = {"hierarchy": {"required_descendant_types": {"Body": "MESH"}}}
result = _check_descendants(scene, root, t)
rt = result["required_types"]
assert rt["result"] == "FAIL"
assert rt["checks"][0]["failure_code"] == "REQUIRED_DESCENDANT_TYPE_MISMATCH"
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestTypesMixedResults:
    def test_mixed_pass_fail(self):
        r = _run_blender(_base('''
a = FO("A", "MESH")
b = FO("B", "EMPTY")
root = FO("R"); root._kids = [a, b]
scene = FS([root, a, b])
t = {"hierarchy": {"required_descendant_types": {"A": "MESH", "B": "MESH", "C": "MESH"}}}
result = _check_descendants(scene, root, t)
rt = result["required_types"]
assert rt["result"] == "FAIL"
results = {c["name"]: c["result"] for c in rt["checks"]}
assert results["A"] == "PASS"
assert results["B"] == "FAIL"
assert results["C"] == "FAIL"
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestTypesOnlyTypesRule:
    def test_only_types_configured(self):
        r = _run_blender(_base('''
body = FO("Body", "MESH")
root = FO("R"); root._kids = [body]
scene = FS([root, body])
t = {"hierarchy": {"required_descendant_types": {"Body": "MESH"}}}
result = _check_descendants(scene, root, t)
assert result["result"] == "PASS"
assert result["required_types"]["result"] == "PASS"
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestTypesCombinedWithOtherRules:
    def test_with_required_names_overlap(self):
        r = _run_blender(_base('''
body = FO("Body", "MESH")
root = FO("R"); root._kids = [body]
scene = FS([root, body])
t = {"hierarchy": {
    "required_descendant_names": ["Body"],
    "required_descendant_types": {"Body": "MESH"},
}}
result = _check_descendants(scene, root, t)
assert result["result"] == "PASS"
assert result["required"]["result"] == "PASS"
assert result["required_types"]["result"] == "PASS"
print("PASS=OK")
'''))
        assert r.returncode == 0

    def test_with_forbidden_combined(self):
        r = _run_blender(_base('''
body = FO("Body", "MESH")
root = FO("R"); root._kids = [body]
scene = FS([root, body])
t = {"hierarchy": {
    "required_descendant_types": {"Body": "MESH"},
    "forbidden_descendant_name_patterns": ["Body*"],
}}
result = _check_descendants(scene, root, t)
assert result["result"] == "FAIL"
assert result["required_types"]["result"] == "PASS"
assert result["forbidden"]["result"] == "FAIL"
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestTypesRootExcluded:
    def test_root_not_satisfy_type_requirement(self):
        r = _run_blender(_base('''
body = FO("Body", "MESH")
root = FO("R", "MESH"); root._kids = [body]
scene = FS([root, body])
t = {"hierarchy": {"required_descendant_types": {"R": "MESH"}}}
result = _check_descendants(scene, root, t)
rt = result["required_types"]
assert rt["result"] == "FAIL"
assert rt["checks"][0]["failure_code"] == "REQUIRED_DESCENDANT_FOR_TYPE_NOT_FOUND"
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestTypesSceneScope:
    def test_other_scene_object_not_satisfy(self):
        r = _run_blender(_base('''
body_other = FO("Body", "MESH")
body_target = FO("Body", "EMPTY")
root = FO("R"); root._kids = [body_other, body_target]
scene = FS([root, body_target])  # only body_target in target scene
t = {"hierarchy": {"required_descendant_types": {"Body": "MESH"}}}
result = _check_descendants(scene, root, t)
rt = result["required_types"]
assert rt["result"] == "FAIL"
assert rt["checks"][0]["failure_code"] == "REQUIRED_DESCENDANT_TYPE_MISMATCH"
assert rt["checks"][0]["actual_type"] == "EMPTY"
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestTypesUnreferencedTypeNotRead:
    def test_unreferenced_type_not_read(self):
        r = _run_blender(_base('''
class FORead:
    def __init__(self, name, otype="EMPTY"):
        self.name = name; self._type = otype; self._kids = []
        self._type_read = False
    @property
    def children(self):
        return self._kids
    @property
    def type(self):
        self._type_read = True
        return self._type

referenced = FORead("Body", "MESH")
unreferenced = FORead("Head", "MESH")
root = FORead("R"); root._kids = [referenced, unreferenced]
scene = FS([root, referenced, unreferenced])
t = {"hierarchy": {"required_descendant_types": {"Body": "MESH"}}}
result = _check_descendants(scene, root, t)
assert result["required_types"]["result"] == "PASS"
assert referenced._type_read == True
assert unreferenced._type_read == False
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestTypesCheckSortOrder:
    def test_checks_sorted_by_name(self):
        r = _run_blender(_base('''
z = FO("zeta", "MESH")
a = FO("Alpha", "MESH")
aa = FO("alpha", "MESH")
root = FO("R"); root._kids = [z, a, aa]
scene = FS([root, z, a, aa])
t = {"hierarchy": {"required_descendant_types": {
    "zeta": "MESH", "Alpha": "MESH", "alpha": "MESH"
}}}
result = _check_descendants(scene, root, t)
names = [c["name"] for c in result["required_types"]["checks"]]
assert names == ["Alpha", "alpha", "zeta"]
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestTypesAmbiguityPreserved:
    def test_ambiguity_still_errors(self):
        r = _run_blender(_base('''
dup1 = FO("Dup", "MESH"); dup2 = FO("Dup", "MESH")
root = FO("R"); root._kids = [dup1, dup2]
scene = FS([root, dup1, dup2])
t = {"hierarchy": {"required_descendant_types": {"Dup": "MESH"}}}
result = _check_descendants(scene, root, t)
assert result["result"] == "ERROR"
assert result["error_type"] == "AMBIGUOUS_DESCENDANT_NAME"
assert "required_types" not in result
print("PASS=OK")
'''))
        assert r.returncode == 0
