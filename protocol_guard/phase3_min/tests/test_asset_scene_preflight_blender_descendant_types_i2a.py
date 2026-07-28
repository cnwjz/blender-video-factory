"""Tests for 14B-2D-I2A: READ_DESCENDANT_TYPE lookup error."""
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
        self.name = name
        self._type = otype
        self._type_ok = type_ok
        self._kids = []
    @property
    def children(self):
        return self._kids
    @property
    def type(self):
        if not self._type_ok: raise RuntimeError("type read failed")
        return self._type

class FS:
    def __init__(self, objs):
        self.objects = list(objs)

try:
{body_indented}
except Exception:
    traceback.print_exc()
    sys.exit(1)
'''


class TestTypeReadError:
    def test_type_read_throws_error(self):
        r = _run_blender(_base('''
body = FO("Body", "MESH", type_ok=False)
root = FO("R"); root._kids = [body]
scene = FS([root, body])
t = {"hierarchy": {"required_descendant_types": {"Body": "MESH"}}}
result = _check_descendants(scene, root, t)
assert result["result"] == "ERROR"
assert result["error_type"] == "DESCENDANT_LOOKUP_ERROR"
assert result["operation"] == "READ_DESCENDANT_TYPE"
assert result["descendant_name"] == "Body"
assert result["note"] == "READ_DESCENDANT_TYPE_FAILED"
assert "actual_names" not in result
assert "required" not in result
assert "forbidden" not in result
assert "required_types" not in result
print("PASS=OK")
'''))
        assert r.returncode == 0

    def test_error_omits_normal_fields(self):
        r = _run_blender(_base('''
body = FO("Body", "MESH", type_ok=False)
root = FO("R"); root._kids = [body]
scene = FS([root, body])
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


class TestUnreferencedTypeNotRead:
    def test_unreferenced_type_throw_not_accessed(self):
        r = _run_blender(_base('''
class FORead:
    def __init__(self, name, otype="EMPTY", type_ok=True):
        self.name = name; self._type = otype; self._type_ok = type_ok; self._kids = []
    @property
    def children(self): return self._kids
    @property
    def type(self):
        if not self._type_ok: raise RuntimeError("unreferenced read")
        return self._type

ref = FORead("Body", "MESH", type_ok=True)
unref = FORead("Head", "MESH", type_ok=False)  # throws if read
root = FORead("R"); root._kids = [ref, unref]
scene = FS([root, ref, unref])
t = {"hierarchy": {"required_descendant_types": {"Body": "MESH"}}}
result = _check_descendants(scene, root, t)
assert result["result"] == "PASS"
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestNameNotFoundNoTypeRead:
    def test_name_not_found_no_type_read(self):
        r = _run_blender(_base('''
safe = FO("Other", "MESH", type_ok=False)  # would throw if read
root = FO("R"); root._kids = [safe]
scene = FS([root, safe])
t = {"hierarchy": {"required_descendant_types": {"Missing": "MESH"}}}
result = _check_descendants(scene, root, t)
rt = result["required_types"]
assert rt["result"] == "FAIL"
assert rt["checks"][0]["failure_code"] == "REQUIRED_DESCENDANT_FOR_TYPE_NOT_FOUND"
assert rt["checks"][0]["actual_type"] is None
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestStableFirstError:
    def test_multiple_errors_stable_first_by_casefold(self):
        r = _run_blender(_base('''
z = FO("Zulu", "MESH", type_ok=False)
a = FO("Alpha", "EMPTY", type_ok=False)
root = FO("R"); root._kids = [z, a]
scene = FS([root, z, a])
t = {"hierarchy": {"required_descendant_types": {"Zulu": "MESH", "Alpha": "EMPTY"}}}
result = _check_descendants(scene, root, t)
assert result["result"] == "ERROR"
assert result["error_type"] == "DESCENDANT_LOOKUP_ERROR"
# Alpha sorts before Zulu by casefold
assert result["descendant_name"] == "Alpha"
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestNormalBehaviorPreserved:
    def test_type_match_still_works(self):
        r = _run_blender(_base('''
body = FO("Body", "MESH")
root = FO("R"); root._kids = [body]
scene = FS([root, body])
t = {"hierarchy": {"required_descendant_types": {"Body": "MESH"}}}
result = _check_descendants(scene, root, t)
rt = result["required_types"]
assert rt["result"] == "PASS"
assert rt["checks"][0]["result"] == "PASS"
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
assert rt["checks"][0]["failure_code"] == "REQUIRED_DESCENDANT_TYPE_MISMATCH"
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestAmbiguityPreserved:
    def test_ambiguity_still_errors_when_no_type_exception(self):
        r = _run_blender(_base('''
dup1 = FO("Dup", "MESH"); dup2 = FO("Dup", "MESH")
root = FO("R"); root._kids = [dup1, dup2]
scene = FS([root, dup1, dup2])
t = {"hierarchy": {"required_descendant_types": {"Dup": "MESH"}}}
result = _check_descendants(scene, root, t)
assert result["result"] == "ERROR"
assert result["error_type"] == "AMBIGUOUS_DESCENDANT_NAME"
print("PASS=OK")
'''))
        assert r.returncode == 0


class TestTopLevelErrorCollection:
    def test_top_level_error_message(self):
        r = _run_blender(_base('''
from protocol_guard.phase3_min.asset_scene_preflight_check import _collect_target_errors

body = FO("Body", "MESH", type_ok=False)
root = FO("R"); root._kids = [body]
scene = FS([root, body])
t = {"hierarchy": {"required_descendant_types": {"Body": "MESH"}}}
result = _check_descendants(scene, root, t)
assert result["error_type"] == "DESCENDANT_LOOKUP_ERROR"

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
assert len(errs) >= 1
msg = errs[0]
assert "DESCENDANT_LOOKUP_ERROR" in msg
assert "target 'A'" in msg
assert "root_object_name 'R'" in msg
assert "operation 'READ_DESCENDANT_TYPE'" in msg
print("PASS=OK")
'''))
        assert r.returncode == 0
