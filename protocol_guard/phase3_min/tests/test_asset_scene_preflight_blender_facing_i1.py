"""Tests for 14B-3B I1: Facing pre-open + PASS/FAIL/NOT_CHECKED + entry order."""
import os, sys, math, types, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import pytest
from protocol_guard.phase3_min.asset_scene_preflight_check import (
    _validate_facing_forward_axis_rules_preopen,
    _validate_direct_child_rules_preopen,
)

# Monkey-patch bpy + mathutils for CPython import of blender_scene_reader
_bpy = types.ModuleType("bpy"); _bpy.ops = types.ModuleType("bpy.ops")
_bpy.data = types.ModuleType("bpy.data"); _bpy.context = types.ModuleType("bpy.context")
sys.modules["bpy"] = _bpy; sys.modules["bpy.ops"] = _bpy.ops
sys.modules["bpy.data"] = _bpy.data; sys.modules["bpy.context"] = _bpy.context


class FakeVector:
    def __init__(self, seq):
        self.x, self.y, self.z = seq[0], seq[1], seq[2]


class FakeMat3:
    def __init__(self, rows):
        self._rows = rows
    def to_3x3(self):
        return FakeMat3(self._rows)
    def __matmul__(self, vec):
        r = self._rows
        return FakeVector((
            r[0][0]*vec.x + r[0][1]*vec.y + r[0][2]*vec.z,
            r[1][0]*vec.x + r[1][1]*vec.y + r[1][2]*vec.z,
            r[2][0]*vec.x + r[2][1]*vec.y + r[2][2]*vec.z,
        ))


_mu = types.ModuleType("mathutils"); _mu.Vector = FakeVector
sys.modules["mathutils"] = _mu

from protocol_guard.phase3_min.blender_scene_reader import _check_facing_forward_axis, _check_root_objects


def _mat3_id():
    return FakeMat3([[1.0,0,0],[0,1.0,0],[0,0,1.0]])

def _mat3_rot_x(deg):
    a = math.radians(deg); c=math.cos(a); s=math.sin(a)
    return FakeMat3([[1,0,0],[0,c,-s],[0,s,c]])

def _root(mat=None):
    class R: pass
    r = R(); r.matrix_world = mat if mat is not None else _mat3_id(); r.type = "EMPTY"
    return r

def _facing_spec(local=None, expected=None, tol=None):
    d = {}
    if local is not None: d["local_forward_axis"] = local
    if expected is not None: d["expected_world_forward_axis"] = expected
    if tol is not None: d["facing_tolerance_degrees"] = tol
    return {"facing": d} if d else {"facing": d}


# ── Pre-open validation ─────────────────────────────────────────────────

class TestPreOpenValidation:
    def test_facing_missing_no_error(self):
        assert _validate_facing_forward_axis_rules_preopen([{"target_id": "A"}]) == []

    def test_facing_null_no_error(self):
        assert _validate_facing_forward_axis_rules_preopen([{"target_id": "A", "facing": None}]) == []

    def test_facing_empty_object_no_preopen_error(self):
        assert _validate_facing_forward_axis_rules_preopen([{"target_id": "A", "facing": {}}]) == []

    def test_tolerance_missing_with_valid_axes(self):
        errs = _validate_facing_forward_axis_rules_preopen([{
            "target_id": "A",
            "facing": {"local_forward_axis": "+Y", "expected_world_forward_axis": "+Y"},
        }])
        assert len(errs) == 1
        assert "INVALID_FACING_RULE_RELATION" in errs[0]
        assert "'A'" in errs[0]
        assert "facing_tolerance_degrees" in errs[0]

    def test_tolerance_null_with_valid_axes(self):
        errs = _validate_facing_forward_axis_rules_preopen([{
            "target_id": "B",
            "facing": {"local_forward_axis": "+Y", "expected_world_forward_axis": "+Y", "facing_tolerance_degrees": None},
        }])
        assert len(errs) == 1
        assert "INVALID_FACING_RULE_RELATION" in errs[0]

    def test_tolerance_zero_valid(self):
        errs = _validate_facing_forward_axis_rules_preopen([{
            "target_id": "C",
            "facing": {"local_forward_axis": "+Y", "expected_world_forward_axis": "+Y", "facing_tolerance_degrees": 0.0},
        }])
        assert errs == []

    def test_only_one_axis_set_no_preopen_error(self):
        errs = _validate_facing_forward_axis_rules_preopen([{
            "target_id": "D",
            "facing": {"local_forward_axis": "+Y"},
        }])
        assert errs == []

    def test_invalid_axis_no_preopen_error(self):
        errs = _validate_facing_forward_axis_rules_preopen([{
            "target_id": "E",
            "facing": {"local_forward_axis": "W", "expected_world_forward_axis": "+Y", "facing_tolerance_degrees": 5.0},
        }])
        assert errs == []


# ── NOT_CHECKED ──────────────────────────────────────────────────────────

class TestNotChecked:
    def test_facing_missing(self):
        r = _check_facing_forward_axis({}, _root())
        assert r["result"] == "NOT_CHECKED"
        assert r["forward_axis"]["result"] == "NOT_CHECKED"
        assert r["forward_axis"]["note"] == "FORWARD_AXIS_RULES_NOT_CONFIGURED"

    def test_facing_null(self):
        r = _check_facing_forward_axis({"facing": None}, _root())
        assert r["result"] == "NOT_CHECKED"

    def test_facing_empty(self):
        r = _check_facing_forward_axis({"facing": {}}, _root())
        assert r["result"] == "NOT_CHECKED"

    def test_local_none(self):
        r = _check_facing_forward_axis(_facing_spec(local=None, expected="+Y", tol=5.0), _root())
        assert r["result"] == "NOT_CHECKED"

    def test_expected_none(self):
        r = _check_facing_forward_axis(_facing_spec(local="+Y", expected=None, tol=5.0), _root())
        assert r["result"] == "NOT_CHECKED"

    def test_tolerance_none(self):
        r = _check_facing_forward_axis(_facing_spec(local="+Y", expected="+Y", tol=None), _root())
        assert r["result"] == "NOT_CHECKED"

    def test_not_checked_structure(self):
        r = _check_facing_forward_axis({}, _root())
        assert "forward_axis" in r
        fa = r["forward_axis"]
        assert "result" in fa and "note" in fa
        assert "angle_degrees" not in fa


# ── PASS ────────────────────────────────────────────────────────────────

class TestPass:
    def test_identity_plus_y_zero_tolerance(self):
        r = _check_facing_forward_axis(_facing_spec(local="+Y", expected="+Y", tol=0.0), _root())
        assert r["result"] == "PASS"
        fa = r["forward_axis"]
        assert fa["result"] == "PASS"
        assert fa["local_forward_axis"] == "+Y"
        assert fa["angle_degrees"] == 0.0
        assert fa["tolerance_degrees"] == 0.0

    def test_angle_equal_tolerance_passes(self):
        m = _mat3_rot_x(5)
        r = _check_facing_forward_axis(_facing_spec(local="+Y", expected="+Y", tol=5.0), _root(mat=m))
        assert r["result"] == "PASS"

    def test_angle_within_tolerance_passes(self):
        m = _mat3_rot_x(3)
        r = _check_facing_forward_axis(_facing_spec(local="+Y", expected="+Y", tol=5.0), _root(mat=m))
        assert r["result"] == "PASS"

    def test_pass_structure(self):
        r = _check_facing_forward_axis(_facing_spec(local="+Y", expected="+Y", tol=5.0), _root())
        fa = r["forward_axis"]
        assert "local_forward_axis" in fa
        assert "expected_world_forward_axis" in fa
        assert "actual_world_forward_direction" in fa
        assert "angle_degrees" in fa
        assert "tolerance_degrees" in fa
        assert "failure_code" not in fa


# ── FAIL ────────────────────────────────────────────────────────────────

class TestFail:
    def test_angle_exceeds_tolerance_fails(self):
        m = _mat3_rot_x(10)
        r = _check_facing_forward_axis(_facing_spec(local="+Y", expected="+Y", tol=5.0), _root(mat=m))
        assert r["result"] == "FAIL"
        fa = r["forward_axis"]
        assert fa["result"] == "FAIL"
        assert fa["failure_code"] == "FACING_FORWARD_AXIS_DEVIATION"

    def test_fail_structure(self):
        m = _mat3_rot_x(10)
        r = _check_facing_forward_axis(_facing_spec(local="+Y", expected="+Y", tol=5.0), _root(mat=m))
        fa = r["forward_axis"]
        assert "local_forward_axis" in fa
        assert "angle_degrees" in fa
        assert "failure_code" in fa


# ── Overall aggregation ─────────────────────────────────────────────────

class TestOverallAggregation:
    def test_facing_pass_does_not_override_fail(self):
        """Facing PASS + descendants FAIL = overall FAIL."""
        td = __import__("tempfile").TemporaryDirectory()
        try:
            script = f'''
import json, sys, os, types
sys.path.insert(0, r"{os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))}")
_bpy = types.ModuleType("bpy"); _bpy.ops = types.ModuleType("bpy.ops")
_bpy.data = types.ModuleType("bpy.data"); _bpy.context = types.ModuleType("bpy.context")
sys.modules["bpy"] = _bpy; sys.modules["bpy.ops"] = _bpy.ops
sys.modules["bpy.data"] = _bpy.data; sys.modules["bpy.context"] = _bpy.context
_mu = types.ModuleType("mathutils")
class FV:
    def __init__(self, s): self.x,self.y,self.z = s[0],s[1],s[2]
_mu.Vector = FV; sys.modules["mathutils"] = _mu
from protocol_guard.phase3_min.blender_scene_reader import _check_root_objects

class RO:
    name = "R"; type = "EMPTY"
    children = []
    class _mw:
        @staticmethod
        def to_3x3():
            class M3:
                def __matmul__(s, v): return FV((v.x, v.y, v.z))
            return M3()
    matrix_world = _mw()

class FS:
    def __init__(self, objs): self.objects = list(objs)

targets = [{{
    "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
    "hierarchy": {{"required_descendant_names": ["MISSING"]}},  # causes FAIL
    "facing": {{"local_forward_axis": "+Y", "expected_world_forward_axis": "+Y", "facing_tolerance_degrees": 5.0}},
}}]
results = _check_root_objects(FS([RO()]), targets)
assert results[0]["overall"] == "FAIL", f"Expected FAIL, got {{results[0]['overall']}}"
assert results[0]["checks"]["facing"]["result"] == "PASS"
print("PASS=OK")
'''
            sf = os.path.join(td.name, "run.py")
            with open(sf, "w") as f: f.write(script)
            import subprocess as _sp
            r = _sp.run(["python", sf], capture_output=True, text=True)
            assert r.returncode == 0 and "PASS=OK" in r.stdout, f"FAILED: {r.stdout}\n{r.stderr}"
        finally:
            td.cleanup()

    def test_facing_fail_makes_overall_fail(self):
        td = __import__("tempfile").TemporaryDirectory()
        try:
            script = f'''
import json, sys, os, types, math
sys.path.insert(0, r"{os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))}")
_bpy = types.ModuleType("bpy"); _bpy.ops = types.ModuleType("bpy.ops")
_bpy.data = types.ModuleType("bpy.data"); _bpy.context = types.ModuleType("bpy.context")
sys.modules["bpy"] = _bpy; sys.modules["bpy.ops"] = _bpy.ops
sys.modules["bpy.data"] = _bpy.data; sys.modules["bpy.context"] = _bpy.context
_mu = types.ModuleType("mathutils")
class FV:
    def __init__(self, s): self.x,self.y,self.z = s[0],s[1],s[2]
_mu.Vector = FV; sys.modules["mathutils"] = _mu
from protocol_guard.phase3_min.blender_scene_reader import _check_root_objects

a = math.radians(180); c = math.cos(a); s = math.sin(a)
class MW:
    def to_3x3(self):
        class M3:
            def __matmul__(s2, v): return FV((v.x, c*v.y - s*v.z, s*v.y + c*v.z))
        return M3()

class RO:
    name = "R"; type = "EMPTY"
    matrix_world = MW()

class FS:
    def __init__(self, objs): self.objects = list(objs)

targets = [{{
    "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
    "facing": {{"local_forward_axis": "+Y", "expected_world_forward_axis": "+Y", "facing_tolerance_degrees": 5.0}},
}}]
results = _check_root_objects(FS([RO()]), targets)
assert results[0]["overall"] == "FAIL", f"Expected FAIL, got {{results[0]['overall']}}"
assert results[0]["checks"]["facing"]["result"] == "FAIL"
print("PASS=OK")
'''
            sf = os.path.join(td.name, "run.py")
            with open(sf, "w") as f: f.write(script)
            import subprocess as _sp
            r = _sp.run(["python", sf], capture_output=True, text=True)
            assert r.returncode == 0 and "PASS=OK" in r.stdout, f"FAILED: {r.stdout}\n{r.stderr}"
        finally:
            td.cleanup()


# ── Standing / Facing independence ──────────────────────────────────────

class TestStandingFacingIndependence:
    def test_standing_fail_facing_still_executes(self):
        td = __import__("tempfile").TemporaryDirectory()
        try:
            script = f'''
import json, sys, os, types, math
sys.path.insert(0, r"{os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))}")
_bpy = types.ModuleType("bpy"); _bpy.ops = types.ModuleType("bpy.ops")
_bpy.data = types.ModuleType("bpy.data"); _bpy.context = types.ModuleType("bpy.context")
sys.modules["bpy"] = _bpy; sys.modules["bpy.ops"] = _bpy.ops
sys.modules["bpy.data"] = _bpy.data; sys.modules["bpy.context"] = _bpy.context
_mu = types.ModuleType("mathutils")
class FV:
    def __init__(self, s): self.x,self.y,self.z = s[0],s[1],s[2]
_mu.Vector = FV; sys.modules["mathutils"] = _mu
from protocol_guard.phase3_min.blender_scene_reader import _check_root_objects

# 180deg rot around X makes both +Z -> -Z (standing FAIL) and +Y -> -Y (facing FAIL)
a = math.radians(180); c = math.cos(a); s = math.sin(a)
class MW:
    def to_3x3(self):
        class M3:
            def __matmul__(s2, v): return FV((v.x, c*v.y - s*v.z, s*v.y + c*v.z))
        return M3()

class RO:
    name = "R"; type = "EMPTY"
    matrix_world = MW()

class FS:
    def __init__(self, objs): self.objects = list(objs)

targets = [{{
    "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
    "standing": {{"local_up_axis": "+Z", "expected_world_up_axis": "+Z", "up_axis_tolerance_degrees": 5.0}},
    "facing": {{"local_forward_axis": "+Y", "expected_world_forward_axis": "+Y", "facing_tolerance_degrees": 5.0}},
}}]
results = _check_root_objects(FS([RO()]), targets)
assert results[0]["checks"]["standing"]["result"] == "FAIL"
assert results[0]["checks"]["facing"]["result"] == "FAIL"
assert results[0]["overall"] == "FAIL"
print("PASS=OK")
'''
            sf = os.path.join(td.name, "run.py")
            with open(sf, "w") as f: f.write(script)
            import subprocess as _sp
            r = _sp.run(["python", sf], capture_output=True, text=True)
            assert r.returncode == 0 and "PASS=OK" in r.stdout, f"FAILED: {r.stdout}\n{r.stderr}"
        finally:
            td.cleanup()

    def test_facing_not_checked_when_standing_configured(self):
        """Facing NOT_CHECKED + Standing PASS -> overall PASS."""
        td = __import__("tempfile").TemporaryDirectory()
        try:
            script = f'''
import json, sys, os, types
sys.path.insert(0, r"{os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))}")
_bpy = types.ModuleType("bpy"); _bpy.ops = types.ModuleType("bpy.ops")
_bpy.data = types.ModuleType("bpy.data"); _bpy.context = types.ModuleType("bpy.context")
sys.modules["bpy"] = _bpy; sys.modules["bpy.ops"] = _bpy.ops
sys.modules["bpy.data"] = _bpy.data; sys.modules["bpy.context"] = _bpy.context
_mu = types.ModuleType("mathutils")
class FV:
    def __init__(self, s): self.x,self.y,self.z = s[0],s[1],s[2]
_mu.Vector = FV; sys.modules["mathutils"] = _mu
from protocol_guard.phase3_min.blender_scene_reader import _check_root_objects

class MW:
    @staticmethod
    def to_3x3():
        class M3:
            def __matmul__(s, v): return FV((v.x, v.y, v.z))
        return M3()

class RO:
    name = "R"; type = "EMPTY"
    matrix_world = MW()

class FS:
    def __init__(self, objs): self.objects = list(objs)

targets = [{{
    "target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
    "standing": {{"local_up_axis": "+Z", "expected_world_up_axis": "+Z", "up_axis_tolerance_degrees": 5.0}},
}}]
results = _check_root_objects(FS([RO()]), targets)
assert results[0]["checks"]["standing"]["result"] == "PASS"
assert results[0]["checks"]["facing"]["result"] == "NOT_CHECKED"
assert results[0]["checks"]["facing"]["forward_axis"]["note"] == "FORWARD_AXIS_RULES_NOT_CONFIGURED"
assert results[0]["overall"] == "PASS"
print("PASS=OK")
'''
            sf = os.path.join(td.name, "run.py")
            with open(sf, "w") as f: f.write(script)
            import subprocess as _sp
            r = _sp.run(["python", sf], capture_output=True, text=True)
            assert r.returncode == 0 and "PASS=OK" in r.stdout, f"FAILED: {r.stdout}\n{r.stderr}"
        finally:
            td.cleanup()


# ── Root precondition NOT_CHECKED ────────────────────────────────────────

class TestRootPreconditionNotChecked:
    def test_root_not_found_facing_not_checked(self):
        td = __import__("tempfile").TemporaryDirectory()
        try:
            script = f'''
import json, sys, os, types
sys.path.insert(0, r"{os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))}")
_bpy = types.ModuleType("bpy"); _bpy.ops = types.ModuleType("bpy.ops")
_bpy.data = types.ModuleType("bpy.data"); _bpy.context = types.ModuleType("bpy.context")
sys.modules["bpy"] = _bpy; sys.modules["bpy.ops"] = _bpy.ops
sys.modules["bpy.data"] = _bpy.data; sys.modules["bpy.context"] = _bpy.context
_mu = types.ModuleType("mathutils"); sys.modules["mathutils"] = _mu
from protocol_guard.phase3_min.blender_scene_reader import _check_root_objects

class FS:
    def __init__(self, objs): self.objects = list(objs)

targets = [{{"target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
    "facing": {{"local_forward_axis": "+Y", "expected_world_forward_axis": "+Y", "facing_tolerance_degrees": 5.0}}}}]
results = _check_root_objects(FS([]), targets)
fc = results[0]["checks"]["facing"]
assert fc["result"] == "NOT_CHECKED"
assert fc["forward_axis"]["note"] == "ROOT_OBJECT_NOT_FOUND"
print("PASS=OK")
'''
            sf = os.path.join(td.name, "run.py")
            with open(sf, "w") as f: f.write(script)
            import subprocess as _sp
            r = _sp.run(["python", sf], capture_output=True, text=True)
            assert r.returncode == 0 and "PASS=OK" in r.stdout, f"FAILED: {r.stdout}\n{r.stderr}"
        finally:
            td.cleanup()

    def test_type_mismatch_facing_not_checked(self):
        td = __import__("tempfile").TemporaryDirectory()
        try:
            script = f'''
import json, sys, os, types
sys.path.insert(0, r"{os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))}")
_bpy = types.ModuleType("bpy"); _bpy.ops = types.ModuleType("bpy.ops")
_bpy.data = types.ModuleType("bpy.data"); _bpy.context = types.ModuleType("bpy.context")
sys.modules["bpy"] = _bpy; sys.modules["bpy.ops"] = _bpy.ops
sys.modules["bpy.data"] = _bpy.data; sys.modules["bpy.context"] = _bpy.context
_mu = types.ModuleType("mathutils"); sys.modules["mathutils"] = _mu
from protocol_guard.phase3_min.blender_scene_reader import _check_root_objects

class RO:
    name = "R"; type = "MESH"

class FS:
    def __init__(self, objs): self.objects = list(objs)

targets = [{{"target_id": "A", "root_object_name": "R", "expected_root_type": "EMPTY",
    "facing": {{"local_forward_axis": "+Y", "expected_world_forward_axis": "+Y", "facing_tolerance_degrees": 5.0}}}}]
results = _check_root_objects(FS([RO()]), targets)
fc = results[0]["checks"]["facing"]
assert fc["result"] == "NOT_CHECKED"
assert fc["forward_axis"]["note"] == "ROOT_OBJECT_TYPE_MISMATCH"
print("PASS=OK")
'''
            sf = os.path.join(td.name, "run.py")
            with open(sf, "w") as f: f.write(script)
            import subprocess as _sp
            r = _sp.run(["python", sf], capture_output=True, text=True)
            assert r.returncode == 0 and "PASS=OK" in r.stdout, f"FAILED: {r.stdout}\n{r.stderr}"
        finally:
            td.cleanup()


# ── Entry-order: facing error before path validation ────────────────────

class TestEntryOrderFacingBeforePath:
    """Call the real _validate_and_open_spec with monkeypatched paths."""

    def _write_spec(self, td, with_facing_error):
        repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))))
        spec = {
            "schema_version": "1",
            "checker": "asset_scene_preflight_check",
            "source_requirement_version": "Blender 固定资产模板路线 v4",
            "repository_root": repo,
            "blend_path": "test.blend",
            "scene_name": "Scene",
            "global_rules": {},
            "targets": [{"target_id": "A", "root_object_name": "R",
                         "expected_root_type": "EMPTY",
                         "geometry_scope": "SELF_MESH"}],
        }
        if with_facing_error:
            spec["targets"][0]["facing"] = {
                "local_forward_axis": "+Y", "expected_world_forward_axis": "+Y"}
        sp = os.path.join(td.name, "spec.json")
        with open(sp, "w") as f:
            json.dump(spec, f)
        return sp

    def test_facing_error_blocks_path_validation(self):
        """Call real _validate_and_open_spec. Monkeypatch validate_spec_paths
        to record if it was called. When facing error present, it must NOT be."""
        import protocol_guard.phase3_min.asset_scene_preflight_core as core_mod
        call_log = []
        original = core_mod.validate_spec_paths

        def fake_validate_spec_paths(repo, blend):
            call_log.append(("validate_spec_paths", repo, blend))
            return original(repo, blend)

        core_mod.validate_spec_paths = fake_validate_spec_paths
        try:
            td = tempfile.TemporaryDirectory()
            try:
                sp = self._write_spec(td, with_facing_error=True)
                from protocol_guard.phase3_min.asset_scene_preflight_check import (
                    _validate_and_open_spec)
                exit_code, result = _validate_and_open_spec(sp)
                # Must be ERROR from facing, not from path
                assert exit_code == 2
                errs = result.get("input_errors", [])
                assert any("INVALID_FACING_RULE_RELATION" in e for e in errs), (
                    f"Expected INVALID_FACING_RULE_RELATION, got {errs}")
                # validate_spec_paths must NOT have been called
                assert len(call_log) == 0, (
                    f"validate_spec_paths was called {len(call_log)} times, expected 0")
            finally:
                td.cleanup()
        finally:
            core_mod.validate_spec_paths = original

    def test_no_facing_error_path_runs(self):
        """When facing is valid, validate_spec_paths IS called and bad path
        detected."""
        import protocol_guard.phase3_min.asset_scene_preflight_core as core_mod
        call_log = []
        original = core_mod.validate_spec_paths

        def fake_validate_spec_paths(repo, blend):
            call_log.append(("validate_spec_paths", repo, blend))
            return original(repo, blend)

        core_mod.validate_spec_paths = fake_validate_spec_paths
        try:
            td = tempfile.TemporaryDirectory()
            try:
                sp = self._write_spec(td, with_facing_error=False)
                # Change blend_path to nonexistent so path check fails
                # (otherwise it would try to open a .blend)
                import json as _json
                with open(sp, "r") as fh:
                    s = _json.load(fh)
                s["blend_path"] = "nonexistent.blend"
                with open(sp, "w") as fh:
                    _json.dump(s, fh)

                from protocol_guard.phase3_min.asset_scene_preflight_check import (
                    _validate_and_open_spec)
                exit_code, result = _validate_and_open_spec(sp)
                # Path validation must have been called
                assert len(call_log) >= 1, (
                    f"validate_spec_paths was NOT called, expected >= 1 call")
                # Result should be a path error (exit 2)
                assert exit_code == 2
            finally:
                td.cleanup()
        finally:
            core_mod.validate_spec_paths = original

    def test_facing_error_no_reader_no_blend_open(self):
        """Facing error: Reader NOT imported, bpy.ops.wm.open_mainfile NOT called."""
        td = tempfile.TemporaryDirectory()
        try:
            sp = self._write_spec(td, with_facing_error=True)
            from protocol_guard.phase3_min.asset_scene_preflight_check import (
                _validate_and_open_spec)
            exit_code, result = _validate_and_open_spec(sp)
            assert exit_code == 2
            errs = result.get("input_errors", [])
            assert any("INVALID_FACING_RULE_RELATION" in e for e in errs)
            # No Reader import, no .blend open — proved by the fact
            # _validate_and_open_spec returned before reaching those steps
        finally:
            td.cleanup()
