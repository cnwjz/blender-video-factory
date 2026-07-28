"""Tests for 14B-3A-I2: real Blender mathutils matrix boundary tests.

Spawns Blender once with the runner script, then asserts all scenarios.
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import pytest

BLENDER = r"D:\Windows software\blender\blender.exe"
RUNNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blender_standing_i2_runner.py")


def _run_blender_once():
    """Spawn Blender with the runner, return parsed results dict keyed by name."""
    r = subprocess.run(
        [BLENDER, "--background", "--factory-startup", "--python", RUNNER],
        capture_output=True, text=True, timeout=120,
    )
    assert r.returncode == 0, f"Blender exit {r.returncode}: {r.stdout}\n{r.stderr}"
    assert "PASS=OK" in r.stdout, f"Missing PASS=OK: {r.stdout}\n{r.stderr}"
    assert "Traceback" not in r.stderr, f"Traceback in stderr: {r.stderr}"
    assert "AssertionError" not in r.stderr, f"AssertionError in stderr: {r.stderr}"

    for line in r.stdout.splitlines():
        if line.startswith("BLENDER_STANDING_I2_RESULTS="):
            return {e["name"]: e for e in json.loads(line.split("=", 1)[1])}
    raise AssertionError(f"No BLENDER_STANDING_I2_RESULTS line in stdout:\n{r.stdout}")


@pytest.fixture(scope="module")
def blender_results():
    return _run_blender_once()


class TestIdentity:
    def test_identity_plus_z_pass(self, blender_results):
        e = blender_results["identity_+Z_to_+Z_PASS"]
        assert e["result"] == "PASS"
        assert e["ua_result"] == "PASS"
        assert e["angle_degrees"] == 0.0


class TestRotation:
    def test_rot_x_90_z_to_minus_y(self, blender_results):
        e = blender_results["rot_x_90_+Z_to_-Y_PASS"]
        assert e["result"] == "PASS"
        assert e["ua_result"] == "PASS"
        d = e["direction"]
        assert abs(d[0] - 0.0) < 0.001
        assert abs(d[1] - (-1.0)) < 0.001
        assert abs(d[2] - 0.0) < 0.001

    def test_rot_y_90_z_to_plus_x(self, blender_results):
        e = blender_results["rot_y_90_+Z_to_+X_PASS"]
        assert e["result"] == "PASS"
        assert e["ua_result"] == "PASS"
        d = e["direction"]
        assert abs(d[0] - 1.0) < 0.001
        assert abs(d[1] - 0.0) < 0.001
        assert abs(d[2] - 0.0) < 0.001


class TestNegativeScale:
    def test_neg_z_scale_180_deg_fail(self, blender_results):
        e = blender_results["neg_z_scale_180deg_FAIL"]
        assert e["result"] == "FAIL"
        assert e["ua_result"] == "FAIL"
        assert e["failure_code"] == "STANDING_UP_AXIS_DEVIATION"
        assert e["angle_degrees"] == pytest.approx(180.0, abs=0.01)


class TestNonUniformScale:
    def test_nonuniform_scale_normalizes(self, blender_results):
        e = blender_results["nonuniform_scale_234_PASS"]
        assert e["result"] == "PASS"
        assert e["ua_result"] == "PASS"
        d = e["direction"]
        norm = (d[0]**2 + d[1]**2 + d[2]**2) ** 0.5
        assert abs(norm - 1.0) < 1e-6

    def test_rot_and_scale_combined(self, blender_results):
        e = blender_results["rot_x90_and_scale_234_PASS"]
        assert e["result"] == "PASS"
        assert e["ua_result"] == "PASS"
        d = e["direction"]
        assert abs(d[0] - 0.0) < 0.001
        assert abs(d[1] - (-1.0)) < 0.001
        assert abs(d[2] - 0.0) < 0.001


class TestShear:
    def test_shear_zx_tol30_pass(self, blender_results):
        e = blender_results["shear_zx_tol30_PASS"]
        assert e["result"] == "PASS"
        assert e["ua_result"] == "PASS"
        # angle between (0.5,0,1) and (0,0,1) ≈ 26.565° < 30°
        assert e["angle_degrees"] < 30.0

    def test_shear_zx_tol10_fail(self, blender_results):
        e = blender_results["shear_zx_tol10_FAIL"]
        assert e["result"] == "FAIL"
        assert e["ua_result"] == "FAIL"
        assert e["failure_code"] == "STANDING_UP_AXIS_DEVIATION"
        # angle between (0.5,0,1) and (0,0,1) ≈ 26.565° > 10°
        assert e["angle_degrees"] > 10.0


class TestZeroScaleError:
    def test_zero_z_scale_normalize_error(self, blender_results):
        e = blender_results["zero_z_scale_ERROR"]
        assert e["result"] == "ERROR"
        assert e["ua_result"] == "ERROR"
        assert e["operation"] == "NORMALIZE_WORLD_UP_AXIS"
        assert e["note"] == "ZERO_LENGTH_UP_VECTOR"


class TestAllScenariosMatch:
    def test_all_expected_results_match(self, blender_results):
        for name, e in blender_results.items():
            assert e["result"] == e["exp_result"], (
                f"{name}: expected {e['exp_result']}, got {e['result']}"
            )
