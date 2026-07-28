"""Projection Groups I2 — pytest wrapper for Blender 5.1.2 validation runner."""
import json, os, subprocess, sys, pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
RUNNER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "blender_projection_groups_validation_runner.py")


@pytest.fixture(scope="module")
def blender_output():
    """Run the Blender validation runner and return parsed JSON output."""
    blender_exe = os.environ.get("BLENDER_EXE", "blender")
    cmd = [
        blender_exe, "--background", "--factory-startup",
        "--python", RUNNER,
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = PROJECT_ROOT
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace",
                          cwd=PROJECT_ROOT, timeout=120,
                          env=env)
    return proc


class TestBlenderRunner:
    def test_returncode_zero(self, blender_output):
        assert blender_output.returncode == 0, (
            f"stderr:\n{blender_output.stderr[:2000]}")

    def test_no_traceback_in_stdout(self, blender_output):
        assert "Traceback" not in blender_output.stdout, (
            f"stdout:\n{blender_output.stdout[:2000]}")

    def test_no_assertion_error_in_stderr(self, blender_output):
        assert "AssertionError" not in blender_output.stderr
        assert "Traceback" not in blender_output.stderr

    def test_json_begin_marker_once(self, blender_output):
        assert blender_output.stdout.count("PROJECTION_GROUPS_I2_JSON_BEGIN") == 1

    def test_json_end_marker_once(self, blender_output):
        assert blender_output.stdout.count("PROJECTION_GROUPS_I2_JSON_END") == 1

    def _parse(self, blender_output):
        begin = blender_output.stdout.find("PROJECTION_GROUPS_I2_JSON_BEGIN")
        end = blender_output.stdout.find("PROJECTION_GROUPS_I2_JSON_END")
        assert begin >= 0 and end > begin
        json_str = blender_output.stdout[begin + len("PROJECTION_GROUPS_I2_JSON_BEGIN"):end].strip()
        data = json.loads(json_str)
        assert "overall_passed" in data
        assert "scenario_count" in data
        return data

    def test_overall_passed(self, blender_output):
        data = self._parse(blender_output)
        assert data["overall_passed"], (
            f"Failed scenarios:\n"
            + "\n".join(str(r) for r in data.get("results", [])
                        if not r.get("passed")))

    def test_blender_version(self, blender_output):
        data = self._parse(blender_output)
        assert data["blender_version"] == "5.1.2"

    def test_scenario_count(self, blender_output):
        data = self._parse(blender_output)
        assert data["scenario_count"] == data["passed_count"] + data["failed_count"]

    def test_safety(self, blender_output):
        data = self._parse(blender_output)
        s = data.get("safety", {})
        assert s.get("real_blend_opened") is False
        assert s.get("blend_saved") is False
        assert s.get("render_executed") is False

    def test_results_not_empty(self, blender_output):
        data = self._parse(blender_output)
        assert len(data["results"]) > 0

    def test_failed_count_zero(self, blender_output):
        data = self._parse(blender_output)
        assert data["failed_count"] == 0, (
            f"Failed:\n"
            + "\n".join(str(r) for r in data.get("results", [])
                        if not r.get("passed")))
