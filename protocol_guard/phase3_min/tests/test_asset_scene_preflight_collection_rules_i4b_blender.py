"""Collection Rules I4B R2 — Blender 5.1.2 validation with independent expected.

Launches Blender subprocess once (module scope).
Pytest holds its own frozen EXPECTED_SCENARIOS.
"""
import ast, json, os, subprocess, sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

BLENDER = os.environ.get("BLENDER_EXE", r"D:\Windows software\blender\blender.exe")
RUNNER = os.path.join(ROOT, "protocol_guard", "phase3_min", "tests",
                      "blender_collection_rules_i4b_runner.py")
REQUIRED_BLENDER_VERSION = "5.1.2"

EXPECTED_IDS = [
    "CR-I4B-01", "CR-I4B-02", "CR-I4B-03", "CR-I4B-04", "CR-I4B-05",
    "CR-I4B-06", "CR-I4B-07", "CR-I4B-08", "CR-I4B-09", "CR-I4B-10",
    "CR-I4B-11", "CR-I4B-12", "CR-I4B-13",
]

# ═══ pytest-side frozen expected (independent of runner) ═══

EXPECTED_SCENARIOS = {
    "CR-I4B-01": {
        "result": "PASS",
        "required": {"result": "PASS", "required_names": ["CHR_TEST"], "missing_names": []},
        "forbidden": {"result": "NOT_CHECKED",
                      "note": "FORBIDDEN_COLLECTION_NAME_PATTERNS_NOT_CONFIGURED"},
    },
    "CR-I4B-02": {
        "result": "FAIL", "failure_code": "COLLECTION_RULES_FAILURE",
        "required": {"result": "FAIL", "failure_code": "REQUIRED_COLLECTION_MISSING",
                     "required_names": ["NONEXISTENT"], "missing_names": ["NONEXISTENT"]},
        "forbidden": {"result": "NOT_CHECKED",
                      "note": "FORBIDDEN_COLLECTION_NAME_PATTERNS_NOT_CONFIGURED"},
    },
    "CR-I4B-03": {
        "result": "FAIL", "failure_code": "COLLECTION_RULES_FAILURE",
        "required": {"result": "NOT_CHECKED",
                     "note": "REQUIRED_COLLECTION_NAMES_NOT_CONFIGURED"},
        "forbidden": {"result": "FAIL", "failure_code": "FORBIDDEN_COLLECTION_MATCHED",
                      "forbidden_patterns": ["*test*"], "matched_collections": ["test_temp"]},
    },
    "CR-I4B-04": {
        "result": "PASS",
        "required": {"result": "NOT_CHECKED",
                     "note": "REQUIRED_COLLECTION_NAMES_NOT_CONFIGURED"},
        "forbidden": {"result": "PASS", "forbidden_patterns": ["*nope*"],
                      "matched_collections": []},
    },
    "CR-I4B-05": {
        "collection_result": {
            "result": "PASS",
            "required": {"result": "PASS", "required_names": ["EMPTY_REQUIRED"], "missing_names": []},
            "forbidden": {"result": "NOT_CHECKED",
                          "note": "FORBIDDEN_COLLECTION_NAME_PATTERNS_NOT_CONFIGURED"},
        },
        "collection_object_count": 0,
    },
    "CR-I4B-06": {
        "result": "PASS", "required_names": ["CHR_A"],
        "direct_collections": ["CHR_A"], "ancestor_collections": [],
        "matched_names": ["CHR_A"], "missing_names": [],
    },
    "CR-I4B-07": {
        "result": "PASS", "required_names": ["Parent"],
        "direct_collections": ["CHR_A"], "ancestor_collections": ["Parent"],
        "matched_names": ["Parent"], "missing_names": [],
    },
    "CR-I4B-08": {
        "result": "PASS", "required_names": ["Grandparent"],
        "direct_collections": ["CHR_A"],
        "ancestor_collections": ["Grandparent", "Parent"],
        "matched_names": ["Grandparent"], "missing_names": [],
    },
    "CR-I4B-09": {
        "result": "PASS", "required_names": ["CHR_A"],
        "direct_collections": ["CHR_A", "Other"], "ancestor_collections": [],
        "matched_names": ["CHR_A"], "missing_names": [],
    },
    "CR-I4B-10": {
        "result": "FAIL", "failure_code": "TARGET_NOT_IN_REQUIRED_COLLECTION",
        "required_names": ["CHR_A", "CHR_B"], "direct_collections": ["Other"],
        "ancestor_collections": [], "matched_names": [],
        "missing_names": ["CHR_A", "CHR_B"],
    },
    "CR-I4B-11": {
        "global": {
            "result": "PASS",
            "required": {"result": "PASS", "required_names": ["GLOBAL_OK"], "missing_names": []},
            "forbidden": {"result": "NOT_CHECKED",
                          "note": "FORBIDDEN_COLLECTION_NAME_PATTERNS_NOT_CONFIGURED"},
        },
        "per_target": {
            "result": "PASS", "required_names": ["CHR_A"],
            "direct_collections": ["CHR_A"], "ancestor_collections": [],
            "matched_names": ["CHR_A"], "missing_names": [],
        },
    },
    "CR-I4B-12": {"ma": "PASS", "cr": "PASS", "overall": "PASS"},
    "CR-I4B-13": {
        "membership": {
            "result": "PASS", "required_names": ["ParentA"],
            "direct_collections": ["Shared"],
            "ancestor_collections": ["ParentA", "ParentB"],
            "matched_names": ["ParentA"], "missing_names": [],
        },
        "shared_parent_count": 2,
    },
}


@pytest.fixture(scope="module")
def results():
    assert os.path.isfile(BLENDER), f"Blender not found: {BLENDER}"
    assert os.path.isfile(RUNNER), f"Runner not found: {RUNNER}"

    proc = subprocess.run(
        [BLENDER, "--background", "--factory-startup", "--python-use-system-env", "--python", RUNNER],
        capture_output=True, text=True, timeout=180,
    )
    assert proc.returncode == 0, f"Blender exit {proc.returncode}\nstderr:\n{proc.stderr}"

    stdout = proc.stdout
    begin = stdout.find("COLLECTION_RULES_I4B_JSON_BEGIN")
    end = stdout.find("COLLECTION_RULES_I4B_JSON_END")
    assert begin >= 0, "JSON_BEGIN marker not found"
    assert end > begin, "JSON_END marker not found or before BEGIN"

    json_str = stdout[begin + len("COLLECTION_RULES_I4B_JSON_BEGIN"):end]
    return json.loads(json_str)


def test_blender_version(results):
    assert results["blender_version"] == REQUIRED_BLENDER_VERSION

def test_factory_startup(results):
    assert results["factory_startup"] is True

def test_no_real_blend(results):
    assert results["real_project_blend_opened"] is False
    assert results["blend_saved"] is False
    assert results["render_executed"] is False

def test_scenario_count(results):
    assert results["scenario_count"] == 13
    assert len(results["scenarios"]) == 13

def test_scenario_ids(results):
    actual_ids = [s["scenario_id"] for s in results["scenarios"]]
    assert actual_ids == EXPECTED_IDS
    assert len(set(actual_ids)) == 13


@pytest.mark.parametrize("idx,scenario_id", list(enumerate(EXPECTED_IDS)))
def test_scenario_exact(results, idx, scenario_id):
    scenario = results["scenarios"][idx]
    expected = EXPECTED_SCENARIOS[scenario_id]

    assert scenario["scenario_id"] == scenario_id
    assert scenario["expected"] == expected, \
        f"{scenario_id}: runner expected differs from pytest expected"
    assert scenario["actual"] == expected, \
        f"{scenario_id}: actual != expected\nexpected: {expected}\nactual: {scenario['actual']}"
    assert scenario["actual"] == scenario["expected"], \
        f"{scenario_id}: actual != runner expected"
    assert scenario["passed"] is True


def test_overall_passed(results):
    assert results["overall_passed"] is True

def test_cleanup(results):
    c = results["cleanup"]
    assert c["objects"] == 0
    assert c["collections"] == 0
    assert c["meshes"] == 0
    assert c["materials"] == 0


def test_runner_no_forbidden_calls():
    with open(RUNNER, encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src)
    forbidden = {"bpy.ops.wm.open_mainfile", "bpy.ops.wm.save_as_mainfile",
                 "bpy.ops.wm.save_mainfile", "bpy.ops.render.render",
                 "bpy.data.libraries.load", "bpy.data.libraries.write"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            parts = []; cur = node.func
            while isinstance(cur, ast.Attribute):
                parts.append(cur.attr); cur = cur.value
            if isinstance(cur, ast.Name):
                chain = ".".join([cur.id] + list(reversed(parts)))
                for fb in forbidden:
                    if chain.startswith(fb):
                        pytest.fail(f"Forbidden call: {chain}")
