"""Tests for Rotation I2 R2: world quaternion + ERROR branches + exact contracts."""
import ast
import math
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

import pytest

_mu = sys.modules["mathutils"]
_mu.__dict__.setdefault("_captures", {})
_mu_captures = _mu.__dict__["_captures"]

class _FakeEuler:
    """Euler mock that populates captures from the current mathutils module."""
    def __init__(self, angles, order):
        self.angles = tuple(angles)
        import sys as __s
        _caps = __s.modules["mathutils"].__dict__.get("_captures", {})
        _caps.setdefault("euler_angles", []).append(angles)
        _caps.setdefault("euler_order", []).append(order)
        _caps.setdefault("euler_calls", 0)
        _caps["euler_calls"] += 1
    def to_quaternion(self):
        import sys as __s
        _caps = __s.modules["mathutils"].__dict__.get("_captures", {})
        _caps.setdefault("to_q_calls", 0)
        _caps["to_q_calls"] += 1
        import math as _m
        hx, hy, hz = self.angles[0]/2, self.angles[1]/2, self.angles[2]/2
        cx, sx = _m.cos(hx), _m.sin(hx)
        cy, sy = _m.cos(hy), _m.sin(hy)
        cz, sz = _m.cos(hz), _m.sin(hz)
        w = cx*cy*cz - sx*sy*sz
        x = sx*cy*cz + cx*sy*sz
        y = cx*sy*cz - sx*cy*sz
        z = cx*cy*sz + sx*sy*cz
        class Q:
            def normalize(self): pass
        q = Q()
        q.w, q.x, q.y, q.z = w, x, y, z
        return q

_mu.__dict__["Euler"] = _FakeEuler

from protocol_guard.phase3_min.blender_scene_reader import _check_rotation, _expected_euler_to_quaternion

def _raw_i2_setup_teardown(_mu, _g):
    """Generator: save state, set fresh Euler+captures, yield, restore.
    Exposed as a raw function so probe tests can call it directly."""
    # ── Save module attrs ──
    _had_euler = "Euler" in _mu.__dict__
    _saved_euler = _mu.__dict__.get("Euler")
    _had_captures = "_captures" in _mu.__dict__
    _saved_captures = _mu.__dict__.get("_captures")
    # ── Save global ──
    _had_global_captures = "_mu_captures" in _g
    _saved_global_captures = _g.get("_mu_captures")
    # ── Setup ──
    _fresh = {}
    _mu.__dict__["_captures"] = _fresh
    _mu.__dict__["Euler"] = _FakeEuler
    _g["_mu_captures"] = _fresh
    yield
    # ── Restore module attrs ──
    if _had_euler:
        _mu.__dict__["Euler"] = _saved_euler
    else:
        _mu.__dict__.pop("Euler", None)
    if _had_captures:
        _mu.__dict__["_captures"] = _saved_captures
    else:
        _mu.__dict__.pop("_captures", None)
    # ── Restore global ──
    if _had_global_captures:
        _g["_mu_captures"] = _saved_global_captures
    else:
        _g.pop("_mu_captures", None)

@pytest.fixture(autouse=True)
def _setup_i2_euler_and_captures():
    """Autouse fixture wrapping the raw generator."""
    import sys as _sys
    return (yield from _raw_i2_setup_teardown(_sys.modules["mathutils"], globals()))


def _valid_spec():
    return {"rotation": {
        "expected_world_rotation_euler_degrees": [0, 0, 0],
        "rotation_tolerance_degrees": 2.0,
    }}

def _obj(mw_raises=None, to_quat_tuple=(1.0, 0.0, 0.0, 0.0), to_q_raises=None):
    class Obj:
        type = "EMPTY"
        _mw_reads = 0
        _to_q_calls = 0
        @property
        def matrix_world(self):
            self._mw_reads += 1
            if mw_raises:
                raise mw_raises
            return _FakeMWObject(self, to_quat_tuple, to_q_raises)
    class _FakeMWObject:
        def __init__(self, parent, quat_tuple, raises):
            self._parent = parent
            self._quat_tuple = quat_tuple
            self._raises = raises
        def to_quaternion(self):
            self._parent._to_q_calls += 1
            if self._raises:
                raise self._raises
            class Q: pass
            q = Q()
            q.w, q.x, q.y, q.z = self._quat_tuple
            return q
    return Obj()

_ERROR_KEYS = {"result", "error_type", "operation", "note"}


def test_fixture_restores_global_and_module_captures():
    """Manually invoke raw generator: prove setup creates fresh shared dict,
    teardown restores original (different) global and module objects.
    Outer try/finally guarantees autouse fixture state is restored."""
    import sys as _sys
    _mu = _sys.modules["mathutils"]
    _g = globals()

    # ── Save autouse fixture's current state ──
    _saved_global = _g.get("_mu_captures")
    _had_global = "_mu_captures" in _g
    _saved_module = _mu.__dict__.get("_captures")
    _had_module_captures = "_captures" in _mu.__dict__

    _gen = None
    try:
        # ── Construct two different originals ──
        _module_original = {}
        _global_original = {}
        _mu.__dict__["_captures"] = _module_original
        _g["_mu_captures"] = _global_original

        # ── Manually run the raw generator ──
        _gen = _raw_i2_setup_teardown(_mu, _g)
        next(_gen)  # setup
        # During setup: module captures should be fresh, global should match
        _during_module = _mu.__dict__["_captures"]
        _during_global = _g["_mu_captures"]
        assert _during_module is _during_global, "global must be same object as module during fixture"
        assert _during_module is not _module_original, "fresh dict must differ from module_original"
        assert _during_module is not _global_original, "fresh dict must differ from global_original"
        assert len(_during_module) == 0, "fresh dict should be empty"
        _during_module["probe"] = True
        with pytest.raises(StopIteration):
            next(_gen)  # yield → teardown (raises StopIteration when done)
        # After teardown: module and global restored to their own originals
        assert _mu.__dict__["_captures"] is _module_original, (
            "module _captures should be restored to module_original"
        )
        assert _g["_mu_captures"] is _global_original, (
            "global _mu_captures should be restored to global_original"
        )
    except StopIteration:
        pass  # not expected here — pytest.raises already caught it
    finally:
        # ── Restore autouse fixture's state unconditionally ──
        if _gen is not None:
            try:
                _gen.close()
            except Exception:
                pass
        if _had_module_captures:
            _mu.__dict__["_captures"] = _saved_module
        else:
            _mu.__dict__.pop("_captures", None)
        if _had_global:
            _g["_mu_captures"] = _saved_global
        else:
            _g.pop("_mu_captures", None)


class TestI1SemanticsPreserved:
    def test_rotation_missing(self):
        r = _check_rotation({}, _obj())
        assert r == {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"}

    def test_rotation_null(self):
        r = _check_rotation({"rotation": None}, _obj())
        assert r == {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"}

    def test_rotation_empty(self):
        r = _check_rotation({"rotation": {}}, _obj())
        assert r == {"result": "NOT_CHECKED", "note": "REQUIREMENT_NOT_CONFIGURED"}

    def test_erw_none(self):
        r = _check_rotation({"rotation": {"expected_world_rotation_euler_degrees": None, "rotation_tolerance_degrees": 2.0}}, _obj())
        assert r["result"] == "NOT_CHECKED"


class TestMatrixWorldRead:
    def test_reads_matrix_world_once(self):
        obj = _obj()
        _check_rotation(_valid_spec(), obj)
        assert obj._mw_reads == 1
        assert obj._to_q_calls == 1

    def test_matrix_world_read_exception(self):
        obj = _obj(mw_raises=RuntimeError("boom"))
        r = _check_rotation(_valid_spec(), obj)
        assert set(r.keys()) == _ERROR_KEYS
        assert r["result"] == "ERROR"
        assert r["error_type"] == "ROTATION_COMPUTATION_ERROR"
        assert r["operation"] == "READ_ROOT_MATRIX_WORLD"
        assert r["note"] == "READ_ROOT_MATRIX_WORLD_FAILED"
        assert obj._to_q_calls == 0  # short-circuit


class TestActualQuaternionErrors:
    def test_to_quaternion_raises(self):
        obj = _obj(to_q_raises=RuntimeError("boom"))
        r = _check_rotation(_valid_spec(), obj)
        assert set(r.keys()) == _ERROR_KEYS
        assert r["result"] == "ERROR"
        assert r["error_type"] == "ROTATION_COMPUTATION_ERROR"
        assert r["operation"] == "CONVERT_ROOT_MATRIX_WORLD_TO_QUATERNION"
        assert r["note"] == "CONVERT_ROOT_MATRIX_WORLD_TO_QUATERNION_FAILED"

    def test_actual_nonfinite(self):
        for t in [(float('nan'), 0, 0, 0), (0, float('inf'), 0, 0)]:
            obj = _obj(to_quat_tuple=t)
            r = _check_rotation(_valid_spec(), obj)
            assert set(r.keys()) == _ERROR_KEYS
            assert r["result"] == "ERROR"
            assert r["error_type"] == "ROTATION_COMPUTATION_ERROR"
            assert r["operation"] == "CONVERT_ROOT_MATRIX_WORLD_TO_QUATERNION"
            assert r["note"] == "NONFINITE_ROTATION_QUATERNION"

    def test_actual_zero_length(self):
        obj = _obj(to_quat_tuple=(0.0, 0.0, 0.0, 0.0))
        r = _check_rotation(_valid_spec(), obj)
        assert set(r.keys()) == _ERROR_KEYS
        assert r["result"] == "ERROR"
        assert r["error_type"] == "ROTATION_COMPUTATION_ERROR"
        assert r["operation"] == "CONVERT_ROOT_MATRIX_WORLD_TO_QUATERNION"
        assert r["note"] == "ZERO_LENGTH_ROTATION_QUATERNION"


class TestExpectedEuler:
    def test_degrees_exactly_to_radians(self):
        _mu_captures.clear()
        erw = [90.0, -45.0, 180.0]
        q = _expected_euler_to_quaternion(erw)
        assert all(math.isfinite(v) for v in q)
        assert len(_mu_captures.get("euler_angles", [])) == 1
        captured = _mu_captures["euler_angles"][0]
        assert captured == (math.radians(90.0), math.radians(-45.0), math.radians(180.0))
        assert _mu_captures.get("euler_order", []) == ["XYZ"]
        assert _mu_captures.get("euler_calls") == 1
        assert _mu_captures.get("to_q_calls") == 1

    def test_euler_order_is_xyz(self):
        src = open(os.path.join(ROOT, "protocol_guard", "phase3_min", "blender_scene_reader.py"), encoding="utf-8").read()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_expected_euler_to_quaternion":
                assert "'XYZ'" in ast.unparse(node)
                return
        pytest.fail("not found")


class TestExpectedQuaternionErrors:
    def test_euler_conversion_raises(self):
        orig = _expected_euler_to_quaternion
        def _raise(*a): raise RuntimeError("boom")
        try:
            import protocol_guard.phase3_min.blender_scene_reader as reader
            reader._expected_euler_to_quaternion = _raise
            r = _check_rotation(_valid_spec(), _obj())
            assert set(r.keys()) == _ERROR_KEYS
            assert r["result"] == "ERROR"
            assert r["error_type"] == "ROTATION_COMPUTATION_ERROR"
            assert r["operation"] == "CONVERT_EXPECTED_EULER_TO_QUATERNION"
            assert r["note"] == "CONVERT_EXPECTED_EULER_TO_QUATERNION_FAILED"
        finally:
            reader._expected_euler_to_quaternion = orig

    def test_expected_nonfinite(self):
        orig = _expected_euler_to_quaternion
        def _nan(*a): return (float('nan'), 0, 0, 0)
        try:
            import protocol_guard.phase3_min.blender_scene_reader as reader
            reader._expected_euler_to_quaternion = _nan
            r = _check_rotation(_valid_spec(), _obj())
            assert set(r.keys()) == _ERROR_KEYS
            assert r["operation"] == "CONVERT_EXPECTED_EULER_TO_QUATERNION"
            assert r["result"] == "ERROR"
            assert r["error_type"] == "ROTATION_COMPUTATION_ERROR"
            assert r["note"] == "NONFINITE_ROTATION_QUATERNION"
        finally:
            reader._expected_euler_to_quaternion = orig

    def test_expected_zero_length(self):
        orig = _expected_euler_to_quaternion
        def _zero(*a): return (0.0, 0.0, 0.0, 0.0)
        try:
            import protocol_guard.phase3_min.blender_scene_reader as reader
            reader._expected_euler_to_quaternion = _zero
            r = _check_rotation(_valid_spec(), _obj())
            assert set(r.keys()) == _ERROR_KEYS
            assert r["operation"] == "CONVERT_EXPECTED_EULER_TO_QUATERNION"
            assert r["result"] == "ERROR"
            assert r["error_type"] == "ROTATION_COMPUTATION_ERROR"
            assert r["note"] == "ZERO_LENGTH_ROTATION_QUATERNION"
        finally:
            reader._expected_euler_to_quaternion = orig


class TestErrorShortCircuit:
    def _count_expected_calls(self, obj, check_fn_args):
        """Run check, return (result, expected_euler_call_count)."""
        import protocol_guard.phase3_min.blender_scene_reader as reader
        orig = reader._expected_euler_to_quaternion
        call_count = [0]
        def _counting_erw(erw):
            call_count[0] += 1
            return orig(erw)
        reader._expected_euler_to_quaternion = _counting_erw
        try:
            r = _check_rotation(*check_fn_args)
            return r, call_count[0]
        finally:
            reader._expected_euler_to_quaternion = orig

    def test_mw_error_blocks_to_q_and_expected(self):
        obj = _obj(mw_raises=RuntimeError("boom"))
        r, exp_calls = self._count_expected_calls(obj, (_valid_spec(), obj))
        assert r["result"] == "ERROR"
        assert r["operation"] == "READ_ROOT_MATRIX_WORLD"
        assert obj._to_q_calls == 0
        assert exp_calls == 0, f"expected Euler called {exp_calls} times"

    def test_actual_error_blocks_expected(self):
        obj = _obj(to_q_raises=RuntimeError("boom"))
        r, exp_calls = self._count_expected_calls(obj, (_valid_spec(), obj))
        assert r["result"] == "ERROR"
        assert r["operation"] == "CONVERT_ROOT_MATRIX_WORLD_TO_QUATERNION"
        assert exp_calls == 0

    def test_actual_nonfinite_blocks_expected(self):
        obj = _obj(to_quat_tuple=(float('nan'), 0, 0, 0))
        r, exp_calls = self._count_expected_calls(obj, (_valid_spec(), obj))
        assert r["result"] == "ERROR"
        assert r["operation"] == "CONVERT_ROOT_MATRIX_WORLD_TO_QUATERNION"
        assert r["note"] == "NONFINITE_ROTATION_QUATERNION"
        assert exp_calls == 0

    def test_actual_zero_blocks_expected(self):
        obj = _obj(to_quat_tuple=(0.0, 0.0, 0.0, 0.0))
        r, exp_calls = self._count_expected_calls(obj, (_valid_spec(), obj))
        assert r["result"] == "ERROR"
        assert r["operation"] == "CONVERT_ROOT_MATRIX_WORLD_TO_QUATERNION"
        assert r["note"] == "ZERO_LENGTH_ROTATION_QUATERNION"
        assert exp_calls == 0


class TestSuccessBoundary:
    def test_both_valid_returns_result(self):
        r = _check_rotation(_valid_spec(), _obj())
        assert r["result"] == "PASS"
        assert "angle_degrees" in r

    def test_angle_comparison_now_present_in_i3(self):
        src = open(os.path.join(ROOT, "protocol_guard", "phase3_min", "blender_scene_reader.py"), encoding="utf-8").read()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_check_rotation":
                assert "quaternion_min_angle_degrees" in ast.unparse(node)

    def test_collect_target_errors_has_rotation_collection(self):
        src = open(os.path.join(ROOT, "protocol_guard", "phase3_min", "asset_scene_preflight_check.py"), encoding="utf-8").read()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_collect_target_errors":
                body = ast.unparse(node)
                assert "rotation" in body, "_collect_target_errors must have rotation ERROR collection"


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
