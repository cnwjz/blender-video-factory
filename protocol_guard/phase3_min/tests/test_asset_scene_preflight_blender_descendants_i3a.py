"""Tests for 14B-2C-I3A: AMBIGUOUS_DESCENDANT_NAME detection."""
import json, os, subprocess, sys, tempfile
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
BLENDER_EXE = r"D:\Windows software\blender\blender.exe"
DEPS_SITE = r"C:\Users\Administrator\AppData\Roaming\Python\Python314\site-packages"


def _run_blender_script(script):
    td = tempfile.mkdtemp()
    sf = os.path.join(td, "run.py")
    with open(sf, "w") as f: f.write(script)
    r = subprocess.run([BLENDER_EXE, "--background", "--factory-startup", "--python", sf],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    os.unlink(sf)
    import shutil; shutil.rmtree(td, ignore_errors=True)
    assert r.returncode == 0, f"returncode={r.returncode}\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
    assert r.stdout.count("PASS=OK\n") == 1, f"PASS=OK not exactly once\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
    assert "Traceback" not in r.stderr, f"Traceback in stderr\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
    assert "AssertionError" not in r.stderr, f"AssertionError in stderr\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
    return r


def _fake_script_body(children_setup, target_setup, extra_asserts=""):
    cs = "\n".join("    " + line for line in children_setup.split("\n"))
    ts = "\n".join("    " + line for line in target_setup.split("\n"))
    ea = "\n".join("    " + line for line in extra_asserts.split("\n"))
    return f'''
import json, sys, os, traceback
try:
    sys.path.insert(0, r"{DEPS_SITE}")
    sys.path.insert(0, r"{PROJECT_ROOT}")
    from protocol_guard.phase3_min.blender_scene_reader import _check_descendants
    from protocol_guard.phase3_min.asset_scene_preflight_check import _collect_target_errors

    class FakeObj:
        def __init__(self, name):
            self.name = name
            self._children = []
            self.type = "EMPTY"
        @property
        def children(self):
            return self._children

    class FakeScene:
        def __init__(self, objs):
            self.objects = list(objs)

{cs}
{ts}
    result = _check_descendants(scene, root_obj, target)
    print("RESULT=" + json.dumps(result, sort_keys=True, ensure_ascii=False))
{ea}
    print("PASS=OK")
except BaseException:
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
'''


class TestAmbiguousSameLevel:
    def test_same_level_duplicate_names(self):
        r = _run_blender_script(_fake_script_body(
            children_setup='''
child1 = FakeObj("Body"); child2 = FakeObj("Body")
root_obj = FakeObj("R")
root_obj._children = [child1, child2]
scene = FakeScene([child1, child2])
''',
            target_setup='''target = {"hierarchy": {"required_descendant_names": []}}''',
        ))
        result_lines = [l for l in r.stdout.split("\n") if l.startswith("RESULT=")]
        assert len(result_lines) == 1, f"Expected 1 RESULT line, got {len(result_lines)}"
        result = json.loads(result_lines[0][len("RESULT="):])
        assert result["result"] == "ERROR"
        assert result["error_type"] == "AMBIGUOUS_DESCENDANT_NAME"
        assert result["ambiguous_name_counts"]["Body"] == 2
        assert "required" not in result
        assert "forbidden" not in result


class TestAmbiguousDifferentDepths:
    def test_shallow_and_deep_duplicate(self):
        r = _run_blender_script(_fake_script_body(
            children_setup='''
body1 = FakeObj("Body")
body2 = FakeObj("Body")
child = FakeObj("Child")
child._children = [body2]
root_obj = FakeObj("R")
root_obj._children = [body1, child]
scene = FakeScene([body1, child, body2])
''',
            target_setup='''target = {"hierarchy": {"required_descendant_names": []}}''',
        ))
        result_lines = [l for l in r.stdout.split("\n") if l.startswith("RESULT=")]
        assert len(result_lines) == 1
        result = json.loads(result_lines[0][len("RESULT="):])
        assert result["result"] == "ERROR"
        assert result["ambiguous_name_counts"]["Body"] == 2


class TestAmbiguousDifferentBranches:
    def test_different_branches_duplicate(self):
        r = _run_blender_script(_fake_script_body(
            children_setup='''
mesh_a = FakeObj("Mesh"); mesh_b = FakeObj("Mesh")
branch_a = FakeObj("BranchA"); branch_b = FakeObj("BranchB")
branch_a._children = [mesh_a]; branch_b._children = [mesh_b]
root_obj = FakeObj("R")
root_obj._children = [branch_a, branch_b]
scene = FakeScene([branch_a, branch_b, mesh_a, mesh_b])
''',
            target_setup='''target = {"hierarchy": {"required_descendant_names": []}}''',
        ))
        result_lines = [l for l in r.stdout.split("\n") if l.startswith("RESULT=")]
        assert len(result_lines) == 1
        result = json.loads(result_lines[0][len("RESULT="):])
        assert result["result"] == "ERROR"
        assert result["ambiguous_name_counts"]["Mesh"] == 2


class TestAmbiguousMultiGroupSorting:
    def test_multiple_groups_sorted_keys(self):
        r = _run_blender_script(_fake_script_body(
            children_setup='''
a1 = FakeObj("armature"); a2 = FakeObj("armature")
a3 = FakeObj("Armature"); a4 = FakeObj("Armature"); a5 = FakeObj("Armature")
b1 = FakeObj("body"); b2 = FakeObj("body")
root_obj = FakeObj("R")
root_obj._children = [a1, a2, a3, a4, a5, b1, b2]
scene = FakeScene([a1, a2, a3, a4, a5, b1, b2])
''',
            target_setup='''target = {"hierarchy": {"required_descendant_names": []}}''',
        ))
        result_lines = [l for l in r.stdout.split("\n") if l.startswith("RESULT=")]
        assert len(result_lines) == 1
        result = json.loads(result_lines[0][len("RESULT="):])
        assert result["result"] == "ERROR"
        counts = result["ambiguous_name_counts"]
        keys = list(counts.keys())
        assert keys == ["Armature", "armature", "body"]  # casefold order
        assert counts["Armature"] == 3
        assert counts["armature"] == 2
        assert counts["body"] == 2


class TestAmbiguousCaseDifferentNotDuplicate:
    def test_case_different_names_not_ambiguous(self):
        r = _run_blender_script(_fake_script_body(
            children_setup='''
child1 = FakeObj("Body"); child2 = FakeObj("body")
root_obj = FakeObj("R")
root_obj._children = [child1, child2]
scene = FakeScene([child1, child2])
''',
            target_setup='''target = {"hierarchy": {"required_descendant_names": []}}''',
        ))
        result_lines = [l for l in r.stdout.split("\n") if l.startswith("RESULT=")]
        assert len(result_lines) == 1
        result = json.loads(result_lines[0][len("RESULT="):])
        assert result["result"] == "PASS"  # Not ambiguous
        assert "error_type" not in result


class TestAmbiguousDot001NotDuplicate:
    def test_dot_001_not_ambiguous(self):
        r = _run_blender_script(_fake_script_body(
            children_setup='''
child1 = FakeObj("Body"); child2 = FakeObj("Body.001")
root_obj = FakeObj("R")
root_obj._children = [child1, child2]
scene = FakeScene([child1, child2])
''',
            target_setup='''target = {"hierarchy": {"required_descendant_names": []}}''',
        ))
        result_lines = [l for l in r.stdout.split("\n") if l.startswith("RESULT=")]
        assert len(result_lines) == 1
        result = json.loads(result_lines[0][len("RESULT="):])
        assert result["result"] == "PASS"


class TestAmbiguousUnusedNameStillErrors:
    def test_unused_name_still_ambiguous(self):
        r = _run_blender_script(_fake_script_body(
            children_setup='''
dup1 = FakeObj("UnusedDuplicate"); dup2 = FakeObj("UnusedDuplicate")
root_obj = FakeObj("R")
root_obj._children = [dup1, dup2]
scene = FakeScene([dup1, dup2])
''',
            target_setup='''target = {"hierarchy": {
    "required_descendant_names": ["OtherName"],
    "forbidden_descendant_name_patterns": ["OtherPattern"],
}}''',
        ))
        result_lines = [l for l in r.stdout.split("\n") if l.startswith("RESULT=")]
        assert len(result_lines) == 1
        result = json.loads(result_lines[0][len("RESULT="):])
        assert result["result"] == "ERROR"
        assert result["error_type"] == "AMBIGUOUS_DESCENDANT_NAME"
        assert result["ambiguous_name_counts"]["UnusedDuplicate"] == 2
        assert "required" not in result
        assert "forbidden" not in result


class TestAmbiguousPrecedesRequiredAndForbidden:
    def test_ambiguity_precedes_rules(self):
        r = _run_blender_script(_fake_script_body(
            children_setup='''
dup1 = FakeObj("X"); dup2 = FakeObj("X")
root_obj = FakeObj("R")
root_obj._children = [dup1, dup2]
scene = FakeScene([dup1, dup2])
''',
            target_setup='''target = {"hierarchy": {
    "required_descendant_names": ["Missing"],
    "forbidden_descendant_name_patterns": ["X*"],
}}''',
        ))
        result_lines = [l for l in r.stdout.split("\n") if l.startswith("RESULT=")]
        assert len(result_lines) == 1
        result = json.loads(result_lines[0][len("RESULT="):])
        assert result["result"] == "ERROR"
        assert result["error_type"] == "AMBIGUOUS_DESCENDANT_NAME"
        assert "required" not in result
        assert "forbidden" not in result


class TestAmbiguousTopLevelErrorCollection:
    def test_collect_target_errors_from_ambiguous(self):
        r = _run_blender_script(_fake_script_body(
            children_setup='''
dup1 = FakeObj("X"); dup2 = FakeObj("X"); dup3 = FakeObj("Y"); dup4 = FakeObj("Y")
root_obj = FakeObj("R")
root_obj._children = [dup1, dup2, dup3, dup4]
scene = FakeScene([dup1, dup2, dup3, dup4])
''',
            target_setup='''target = {
    "target_id": "A",
    "root_object_name": "R",
    "hierarchy": {"required_descendant_names": []},
}''',
            extra_asserts='''
# Simulate what the entry point does with an ERROR target
per_target = [{
    "target_id": "A",
    "root_object_name": "R",
    "checks": {
        "object_exists": {"result": "PASS"},
        "object_type": {"result": "PASS"},
        "direct_children": {"result": "NOT_CHECKED"},
        "descendants": result,
    },
    "overall": "ERROR",
}]
errs = _collect_target_errors(per_target)
assert len(errs) >= 2  # X and Y
has_x = any("'X' has 2" in e for e in errs)
has_y = any("'Y' has 2" in e for e in errs)
assert has_x and has_y
# Messages for X should come before Y (casefold order)
x_idx = next(i for i, e in enumerate(errs) if "'X'" in e)
y_idx = next(i for i, e in enumerate(errs) if "'Y'" in e)
assert x_idx < y_idx, f"Expected X before Y: {errs}"
print("COLLECT_OK=1")
''',
        ))
        collect_lines = [l for l in r.stdout.split("\n") if l.startswith("COLLECT_OK=")]
        assert len(collect_lines) == 1
        assert collect_lines[0] == "COLLECT_OK=1"


class TestHarnessCatchesChildFailure:
    def test_assert_error_in_child_fails_pytest(self):
        with pytest.raises(AssertionError) as exc_info:
            _run_blender_script(_fake_script_body(
                children_setup='''
child1 = FakeObj("Body"); child2 = FakeObj("Body")
root_obj = FakeObj("R")
root_obj._children = [child1, child2]
scene = FakeScene([child1, child2])
''',
                target_setup='''target = {"hierarchy": {"required_descendant_names": []}}''',
                extra_asserts='''assert False, "injected child failure"''',
            ))
        msg = str(exc_info.value)
        assert "AssertionError" in msg
        assert "returncode" in msg
        assert "STDOUT:" in msg
        assert "STDERR:" in msg


class TestHarnessCatchesMissingPassOk:
    def test_missing_pass_ok_fails_pytest(self):
        script = '''
import sys
print("hello")
sys.exit(0)
'''
        with pytest.raises(AssertionError) as exc_info:
            _run_blender_script(script)
        msg = str(exc_info.value)
        assert "PASS=OK" in msg
        assert "STDOUT:" in msg
        assert "STDERR:" in msg


class TestHarnessCatchesDuplicatePassOk:
    def test_double_pass_ok_fails_pytest(self):
        script = '''
import sys
print("PASS=OK")
print("PASS=OK")
sys.exit(0)
'''
        with pytest.raises(AssertionError) as exc_info:
            _run_blender_script(script)
        msg = str(exc_info.value)
        assert "PASS=OK" in msg
        assert "STDOUT:" in msg
        assert "STDERR:" in msg


class TestHarnessCatchesStderrTraceback:
    def test_stderr_traceback_fails_pytest(self):
        script = '''
import sys
print("PASS=OK")
sys.stderr.write("Traceback (most recent call last):\\n")
sys.exit(0)
'''
        with pytest.raises(AssertionError) as exc_info:
            _run_blender_script(script)
        msg = str(exc_info.value)
        assert "Traceback" in msg
        assert "STDOUT:" in msg
        assert "STDERR:" in msg


class TestHarnessCatchesStderrAssertionError:
    def test_stderr_assertion_error_fails_pytest(self):
        script = '''
import sys
print("PASS=OK")
sys.stderr.write("AssertionError: something went wrong\\n")
sys.exit(0)
'''
        with pytest.raises(AssertionError) as exc_info:
            _run_blender_script(script)
        msg = str(exc_info.value)
        assert "AssertionError" in msg
        assert "STDOUT:" in msg
        assert "STDERR:" in msg
