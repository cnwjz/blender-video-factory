"""Tests for 14B-3A-I1C3: _collect_target_errors standing ERROR collection."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import pytest
from protocol_guard.phase3_min.asset_scene_preflight_check import _collect_target_errors


def _err_standing(op):
    return {
        "result": "ERROR",
        "up_axis": {
            "result": "ERROR",
            "error_type": "STANDING_UP_AXIS_ERROR",
            "operation": op,
            "note": op + "_FAILED",
        },
    }


def _err_descendants(op):
    return {
        "result": "ERROR",
        "error_type": "DESCENDANT_LOOKUP_ERROR",
        "operation": op,
        "note": op + "_FAILED",
    }


class TestStandingErrorCollected:
    def test_standing_error_alone(self):
        per_target = [{
            "target_id": "A",
            "root_object_name": "R",
            "overall": "ERROR",
            "checks": {
                "standing": _err_standing("READ_ROOT_MATRIX_WORLD"),
            },
        }]
        errs = _collect_target_errors(per_target)
        assert len(errs) == 1
        assert "STANDING_UP_AXIS_ERROR" in errs[0]
        assert "'A'" in errs[0]
        assert "'R'" in errs[0]
        assert "READ_ROOT_MATRIX_WORLD" in errs[0]

    def test_standing_error_with_descendants_error_order(self):
        per_target = [{
            "target_id": "A",
            "root_object_name": "R",
            "overall": "ERROR",
            "checks": {
                "descendants": _err_descendants("READ_DESCENDANT_NAME"),
                "standing": _err_standing("NORMALIZE_WORLD_UP_AXIS"),
            },
        }]
        errs = _collect_target_errors(per_target)
        assert len(errs) == 2
        assert "DESCENDANT_LOOKUP_ERROR" in errs[0]
        assert "READ_DESCENDANT_NAME" in errs[0]
        assert "STANDING_UP_AXIS_ERROR" in errs[1]
        assert "NORMALIZE_WORLD_UP_AXIS" in errs[1]

    def test_descendants_error_standing_pass_no_standing_error(self):
        per_target = [{
            "target_id": "A",
            "root_object_name": "R",
            "overall": "ERROR",
            "checks": {
                "descendants": _err_descendants("READ_DESCENDANT_NAME"),
                "standing": {
                    "result": "PASS",
                    "up_axis": {
                        "result": "PASS",
                        "local_up_axis": "+Z",
                        "expected_world_up_axis": "+Z",
                    },
                },
            },
        }]
        errs = _collect_target_errors(per_target)
        assert len(errs) == 1
        assert "DESCENDANT_LOOKUP_ERROR" in errs[0]

    def test_descendants_fail_standing_fail_no_top_level_error(self):
        per_target = [{
            "target_id": "A",
            "root_object_name": "R",
            "overall": "FAIL",
            "checks": {
                "descendants": {
                    "result": "FAIL",
                    "failure_code": "REQUIRED_DESCENDANT_MISSING",
                },
                "standing": {
                    "result": "FAIL",
                    "up_axis": {
                        "result": "FAIL",
                        "failure_code": "STANDING_UP_AXIS_DEVIATION",
                    },
                },
            },
        }]
        errs = _collect_target_errors(per_target)
        assert len(errs) == 0

    def test_operation_missing_uses_unknown(self):
        per_target = [{
            "target_id": "A",
            "root_object_name": "R",
            "overall": "ERROR",
            "checks": {
                "standing": {
                    "result": "ERROR",
                    "up_axis": {
                        "result": "ERROR",
                        "error_type": "STANDING_UP_AXIS_ERROR",
                        "note": "SOME_ERROR",
                    },
                },
            },
        }]
        errs = _collect_target_errors(per_target)
        assert len(errs) == 1
        assert "UNKNOWN" in errs[0]

    def test_standing_not_checked_no_error_collected(self):
        per_target = [{
            "target_id": "A",
            "root_object_name": "R",
            "overall": "ERROR",
            "checks": {
                "descendants": _err_descendants("READ_DESCENDANT_NAME"),
                "standing": {
                    "result": "NOT_CHECKED",
                    "up_axis": {"result": "NOT_CHECKED", "note": "ROOT_OBJECT_NOT_FOUND"},
                },
            },
        }]
        errs = _collect_target_errors(per_target)
        assert len(errs) == 1
        assert "DESCENDANT_LOOKUP_ERROR" in errs[0]

    def test_no_standing_key_no_error_collected(self):
        per_target = [{
            "target_id": "A",
            "root_object_name": "R",
            "overall": "ERROR",
            "checks": {
                "descendants": _err_descendants("READ_DESCENDANT_NAME"),
            },
        }]
        errs = _collect_target_errors(per_target)
        assert len(errs) == 1
        assert "DESCENDANT_LOOKUP_ERROR" in errs[0]

    def test_multiple_targets_preserve_order(self):
        per_target = [
            {
                "target_id": "A",
                "root_object_name": "RA",
                "overall": "ERROR",
                "checks": {
                    "standing": _err_standing("COMPUTE_UP_AXIS_ANGLE"),
                },
            },
            {
                "target_id": "B",
                "root_object_name": "RB",
                "overall": "PASS",
                "checks": {
                    "standing": {
                        "result": "PASS",
                        "up_axis": {"result": "PASS"},
                    },
                },
            },
            {
                "target_id": "C",
                "root_object_name": "RC",
                "overall": "ERROR",
                "checks": {
                    "standing": _err_standing("TRANSFORM_LOCAL_UP_AXIS"),
                },
            },
        ]
        errs = _collect_target_errors(per_target)
        assert len(errs) == 2
        assert "'A'" in errs[0] and "COMPUTE_UP_AXIS_ANGLE" in errs[0]
        assert "'C'" in errs[1] and "TRANSFORM_LOCAL_UP_AXIS" in errs[1]

    def test_error_message_format_exact(self):
        per_target = [{
            "target_id": "T1",
            "root_object_name": "Root",
            "overall": "ERROR",
            "checks": {
                "standing": _err_standing("CONVERT_ROOT_MATRIX_WORLD_TO_3X3"),
            },
        }]
        errs = _collect_target_errors(per_target)
        expected = (
            "STANDING_UP_AXIS_ERROR: target 'T1' "
            "root_object_name 'Root' operation 'CONVERT_ROOT_MATRIX_WORLD_TO_3X3'"
        )
        assert errs[0] == expected
