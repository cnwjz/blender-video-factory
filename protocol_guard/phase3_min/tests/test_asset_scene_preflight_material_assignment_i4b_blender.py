"""Material Assignment I4B — real Blender 5.1.2 validation, 12 scenarios."""
import json, os, subprocess, pytest

RUNNER = os.path.join(os.path.dirname(__file__), "blender_material_assignment_i4b_runner.py")
BLENDER = os.environ.get("BLENDER_EXE", r"D:\Windows software\blender\blender.exe")


def _run():
    cmd = [BLENDER, "--background", "--factory-startup",
           "--python-use-system-env", "--python", RUNNER]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return r


@pytest.fixture(scope="module")
def result():
    r = _run()
    assert r.returncode == 0, f"Blender exit={r.returncode} stderr={r.stderr[:500]}"
    # Extract JSON block from stdout (indented multi-line)
    out = r.stdout
    start = out.index("{")
    end = out.rindex("}") + 1
    data = json.loads(out[start:end])
    return data


class TestI4BBlender:
    def test_blender_exit_zero(self, result):
        assert "blender_version" in result

    def test_blender_version_5_1_2(self, result):
        assert result["blender_version"] == "5.1.2", f"Got {result['blender_version']}"

    def test_scenario_count_12(self, result):
        assert result["scenario_count"] == 12

    def test_unique_scenario_ids(self, result):
        ids = [s["scenario_id"] for s in result["scenarios"]]
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {ids}"

    def test_all_12_passed(self, result):
        passed = sum(1 for s in result["scenarios"] if s["passed"])
        failed = [(s["scenario_id"], s.get("actual", "")) for s in result["scenarios"] if not s["passed"]]
        assert len(failed) == 0, f"Failed scenarios: {failed}"
        assert passed == 12, f"Passed: {passed}/12"

    def test_overall_passed(self, result):
        assert result["overall_passed"] is True
