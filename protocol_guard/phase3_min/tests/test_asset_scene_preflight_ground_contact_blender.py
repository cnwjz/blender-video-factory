"""Ground Contact Blender 5.1.2 validation — 14 scenarios + entry integration."""
import json, os, subprocess, pytest

RUNNER = os.path.join(os.path.dirname(__file__),
                       "blender_ground_contact_validation_runner.py")
BLENDER = os.environ.get("BLENDER_EXE", r"D:\Windows software\blender\blender.exe")


def _run_blender():
    cmd = [BLENDER, "--background", "--factory-startup",
           "--python-use-system-env", "--python", RUNNER]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    return r


@pytest.fixture(scope="module")
def result():
    r = _run_blender()
    assert r.returncode == 0, (
        f"Blender exit={r.returncode}\nstderr={r.stderr[:800]}\n"
        f"stdout={r.stdout[:800]}"
    )
    # Extract JSON from the marker line
    prefix = "GROUND_CONTACT_BLENDER_VALIDATION_JSON="
    out = r.stdout
    marker_start = out.find(prefix)
    assert marker_start != -1, f"Marker line not found in stdout: {out[:500]}"
    after_prefix = out[marker_start + len(prefix):]
    # Find end of JSON (next newline or end)
    newline = after_prefix.find("\n")
    if newline != -1:
        json_str = after_prefix[:newline]
    else:
        json_str = after_prefix.strip()
    data = json.loads(json_str)
    return data


class TestGroundContactBlender:
    """High-level assertions on the Blender validation run."""

    def test_blender_exit_zero(self, result):
        assert "task_id" in result

    def test_blender_version(self, result):
        assert result["blender_version"].startswith("5.1"), (
            f"Expected 5.1.x, got {result['blender_version']}")

    def test_real_project_not_opened(self, result):
        assert result["real_project_blend_opened"] is False

    def test_scenario_count(self, result):
        assert result["scenario_count"] >= 14, (
            f"Expected >=14 scenarios, got {result['scenario_count']}")

    def test_no_failures(self, result):
        assert result["failed_count"] == 0, (
            f"Failed scenarios: "
            f"{[s['scenario_id'] for s in result['scenarios'] if not s['passed']]}")

    def test_all_passed_equal_scenario_count(self, result):
        assert result["passed_count"] == result["scenario_count"]

    def test_entry_integration_passed(self, result):
        assert result["entry_integration_passed"] is True, (
            "Entry integration test did not pass")

    def test_entry_pass_case_passed(self, result):
        assert result.get("entry_pass_case_passed") is True, (
            "Entry PASS case did not pass")

    def test_entry_fail_case_passed(self, result):
        assert result.get("entry_fail_case_passed") is True, (
            "Entry FAIL case did not pass")

    def test_temporary_files_cleaned(self, result):
        assert result["temporary_files_cleaned"] is True

    def test_overall_passed(self, result):
        assert result["overall_passed"] is True


class TestGroundContactBlenderScenarios:
    """Per-scenario assertions."""

    @pytest.fixture(scope="module")
    def scenarios(self, result):
        return {s["scenario_id"]: s for s in result["scenarios"]}

    def test_self_mesh_mesh_root(self, scenarios):
        assert scenarios["GC-BL-01"]["passed"] is True

    def test_self_mesh_empty_root(self, scenarios):
        assert scenarios["GC-BL-02"]["passed"] is True

    def test_descendant_meshes(self, scenarios):
        assert scenarios["GC-BL-03"]["passed"] is True

    def test_self_and_descendant_meshes(self, scenarios):
        assert scenarios["GC-BL-04"]["passed"] is True

    def test_world_space_transform(self, scenarios):
        assert scenarios["GC-BL-05"]["passed"] is True

    def test_multi_mesh_global_lowest(self, scenarios):
        assert scenarios["GC-BL-06"]["passed"] is True

    def test_tolerance_boundary_exact(self, scenarios):
        assert scenarios["GC-BL-07"]["passed"] is True

    def test_tolerance_boundary_below(self, scenarios):
        assert scenarios["GC-BL-08"]["passed"] is True

    def test_tolerance_boundary_above(self, scenarios):
        assert scenarios["GC-BL-09"]["passed"] is True

    def test_zero_tolerance_fail(self, scenarios):
        assert scenarios["GC-BL-10"]["passed"] is True

    def test_zero_vertices(self, scenarios):
        assert scenarios["GC-BL-11"]["passed"] is True

    def test_evaluated_modifier_geometry(self, scenarios):
        assert scenarios["GC-BL-12"]["passed"] is True

    def test_scene_membership(self, scenarios):
        s = scenarios["GC-BL-13"]
        assert s["passed"] is True
        assert s.get("outside_in_target_scene") is False, (
            f"outside_in_target_scene should be False, got {s.get('outside_in_target_scene')}")
        assert s.get("outside_reachable_from_root") is True, (
            f"outside_reachable_from_root should be True, got {s.get('outside_reachable_from_root')}")

    def test_deterministic_order(self, scenarios):
        assert scenarios["GC-BL-14"]["passed"] is True
