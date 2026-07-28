"""Camera Check I2 R2 — pytest wrapper for Blender 5.1.2 validation runner."""
import json, os, subprocess, sys, pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
BLENDER_EXE = os.environ.get("BLENDER_EXE", r"D:\Windows software\blender\blender.exe")
RUNNER = os.path.join(PROJECT_ROOT, "protocol_guard", "phase3_min", "tests",
                      "blender_camera_check_validation_runner.py")


@pytest.fixture(scope="module")
def blender_result():
    assert os.path.isfile(BLENDER_EXE), f"Blender not found: {BLENDER_EXE}"
    assert os.path.isfile(RUNNER), f"Runner not found: {RUNNER}"
    cmd = [BLENDER_EXE, "--background", "--factory-startup",
           "--python-use-system-env", "--python", RUNNER]
    proc = subprocess.run(cmd, capture_output=True, timeout=300,
                          encoding="utf-8", errors="replace",
                          cwd=PROJECT_ROOT,
                          env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    assert proc.returncode == 0, (
        f"Blender exit={proc.returncode}\nSTDOUT:{stdout[:2000]}\nSTDERR:{stderr[:2000]}")
    assert "Traceback" not in stdout, f"Traceback in stdout:\n{stdout[:2000]}"
    assert "Traceback" not in stderr, f"Traceback in stderr:\n{stderr[:2000]}"
    assert "AssertionError" not in stdout, f"AssertionError in stdout"
    assert "AssertionError" not in stderr, f"AssertionError in stderr"
    assert stdout.count("CAMERA_CHECK_I2_JSON_BEGIN") == 1, f"BEGIN count={stdout.count('CAMERA_CHECK_I2_JSON_BEGIN')}"
    assert stdout.count("CAMERA_CHECK_I2_JSON_END") == 1, f"END count={stdout.count('CAMERA_CHECK_I2_JSON_END')}"
    begin = stdout.find("CAMERA_CHECK_I2_JSON_BEGIN") + len("CAMERA_CHECK_I2_JSON_BEGIN")
    end = stdout.find("CAMERA_CHECK_I2_JSON_END")
    data = json.loads(stdout[begin:end].strip())
    return data


class TestCameraCheckBlender:
    def test_blender_version(self, blender_result):
        assert blender_result["blender_version"] == "5.1.2"

    def test_factory_startup(self, blender_result):
        assert blender_result["factory_startup"] is True

    def test_scenario_count(self, blender_result):
        assert blender_result["scenario_count"] == 22

    def test_scenarios_length(self, blender_result):
        assert len(blender_result["scenarios"]) == 22

    def test_scenario_ids_order(self, blender_result):
        ids = [s["scenario_id"] for s in blender_result["scenarios"]]
        expected = [f"CC-BL-{i:02d}" for i in range(1, 23)]
        assert ids == expected, f"order mismatch: {ids}"

    def test_no_duplicate_ids(self, blender_result):
        ids = [s["scenario_id"] for s in blender_result["scenarios"]]
        assert len(ids) == len(set(ids))

    def test_overall_passed(self, blender_result):
        assert blender_result["overall_passed"] is True

    def test_safety_fields(self, blender_result):
        assert blender_result["real_project_blend_opened"] is False
        assert blender_result["real_project_blend_saved"] is False
        assert blender_result["render_executed"] is False
        assert blender_result["user_asset_modified"] is False
        assert blender_result["temporary_files_created"] == []

    @pytest.mark.parametrize("idx", list(range(22)))
    def test_each_scenario_passed(self, blender_result, idx):
        s = blender_result["scenarios"][idx]
        assert s["passed"], f"{s['scenario_id']} FAILED: expected={s['expected']}, actual={s['actual']}"
