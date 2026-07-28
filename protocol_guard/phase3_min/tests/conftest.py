"""Pytest configuration for protocol_guard phase3_min tests.

Auto-loaded by pytest. Provides shared fixtures.
Sets up minimal Blender stub modules so protocol_guard imports work outside Blender.
"""
import sys
import types

import pytest

# ── Blender stubs — autouse fixture with precise save/restore ──
@pytest.fixture(autouse=True)
def _ensure_mathutils_stubs():
    """Save mathutils state, ensure stubs exist, restore after test."""
    import sys as _sys, types as _types
    # ── Save ──
    _saved_mu = _sys.modules.get("mathutils")
    _had_mathutils = "mathutils" in _sys.modules
    if _saved_mu is not None:
        _saved_dict = dict(_saved_mu.__dict__)
        _had_captures = "_captures" in _saved_mu.__dict__
        _saved_captures = _saved_mu.__dict__.get("_captures")
        _had_euler = "Euler" in _saved_mu.__dict__
        _saved_euler = _saved_mu.__dict__.get("Euler")
    else:
        _saved_dict = None; _had_captures = False; _saved_captures = None
        _had_euler = False; _saved_euler = None
    # ── Setup ──
    try:
        if _saved_mu is None:
            _mu = _types.ModuleType("mathutils")
            _mu.__dict__["_captures"] = {}
            _sys.modules["mathutils"] = _mu
        else:
            _mu = _saved_mu
            _mu.__dict__.setdefault("_captures", {})
        if "Euler" not in _mu.__dict__:
            class _StubEuler:
                def __init__(self, angles, order):
                    self.angles = tuple(angles); self.order = order
                def to_quaternion(self):
                    import math as _m
                    hx, hy, hz = self.angles[0]/2, self.angles[1]/2, self.angles[2]/2
                    cx = _m.cos(hx); sx = _m.sin(hx)
                    cy = _m.cos(hy); sy = _m.sin(hy)
                    cz = _m.cos(hz); sz = _m.sin(hz)
                    class Q: pass
                    q = Q()
                    q.w = cx*cy*cz - sx*sy*sz
                    q.x = sx*cy*cz + cx*sy*sz
                    q.y = cx*sy*cz - sx*cy*sz
                    q.z = cx*cy*sz + sx*sy*cz
                    q.normalize = lambda: None
                    return q
            _mu.__dict__["Euler"] = _StubEuler
        yield
    finally:
        if not _had_mathutils:
            _sys.modules.pop("mathutils", None)
        else:
            _saved_mu.__dict__.clear()
            if _saved_dict is not None:
                _saved_mu.__dict__.update(_saved_dict)
            _sys.modules["mathutils"] = _saved_mu

if "bpy" not in sys.modules:
    _bpy = types.ModuleType("bpy")
    sys.modules["bpy"] = _bpy
if "mathutils" not in sys.modules:
    _mu = types.ModuleType("mathutils")
    _mu.__dict__["_captures"] = {}
    sys.modules["mathutils"] = _mu


@pytest.fixture
def assert_d():
    """Shortcut to assertions.assert_dict_equal for concise test code."""
    from protocol_guard.phase3_min.tests.assertions import assert_dict_equal
    return assert_dict_equal
