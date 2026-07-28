"""Tests for 14B-3A-I1A: standing up axis pre-open field validation."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from protocol_guard.phase3_min.asset_scene_preflight_check import _validate_standing_up_axis_rules_preopen
import pytest


class TestStandingPreopen:
    def test_standing_field_missing(self):
        targets = [{"target_id": "A"}]
        errs = _validate_standing_up_axis_rules_preopen(targets)
        assert errs == []

    def test_standing_null(self):
        targets = [{"target_id": "A", "standing": None}]
        errs = _validate_standing_up_axis_rules_preopen(targets)
        assert errs == []

    def test_standing_empty_object(self):
        targets = [{"target_id": "A", "standing": {}}]
        errs = _validate_standing_up_axis_rules_preopen(targets)
        assert errs == []

    def test_all_three_explicit_null(self):
        targets = [{"target_id": "A", "standing": {
            "local_up_axis": None,
            "expected_world_up_axis": None,
            "up_axis_tolerance_degrees": None,
        }}]
        errs = _validate_standing_up_axis_rules_preopen(targets)
        assert errs == []

    def test_all_three_configured_zero_tolerance(self):
        targets = [{"target_id": "A", "standing": {
            "local_up_axis": "+Z",
            "expected_world_up_axis": "+Z",
            "up_axis_tolerance_degrees": 0.0,
        }}]
        errs = _validate_standing_up_axis_rules_preopen(targets)
        assert errs == []

    def test_only_local_up_axis(self):
        targets = [{"target_id": "A", "standing": {"local_up_axis": "+Z"}}]
        errs = _validate_standing_up_axis_rules_preopen(targets)
        assert len(errs) == 1
        assert "INVALID_UP_AXIS_RULE_RELATION" in errs[0]
        assert "'A'" in errs[0]
        assert "expected_world_up_axis" in errs[0]
        assert "up_axis_tolerance_degrees" in errs[0]

    def test_only_expected_world_up_axis(self):
        targets = [{"target_id": "B", "standing": {"expected_world_up_axis": "+Y"}}]
        errs = _validate_standing_up_axis_rules_preopen(targets)
        assert len(errs) == 1
        assert "INVALID_UP_AXIS_RULE_RELATION" in errs[0]
        assert "'B'" in errs[0]
        assert "local_up_axis" in errs[0]
        assert "up_axis_tolerance_degrees" in errs[0]

    def test_only_tolerance(self):
        targets = [{"target_id": "C", "standing": {"up_axis_tolerance_degrees": 5.0}}]
        errs = _validate_standing_up_axis_rules_preopen(targets)
        assert len(errs) == 1
        assert "INVALID_UP_AXIS_RULE_RELATION" in errs[0]
        assert "'C'" in errs[0]
        assert "local_up_axis" in errs[0]
        assert "expected_world_up_axis" in errs[0]

    def test_local_plus_expected(self):
        targets = [{"target_id": "D", "standing": {"local_up_axis": "+Z", "expected_world_up_axis": "+Z"}}]
        errs = _validate_standing_up_axis_rules_preopen(targets)
        assert len(errs) == 1
        assert "up_axis_tolerance_degrees" in errs[0]

    def test_local_plus_tolerance(self):
        targets = [{"target_id": "E", "standing": {"local_up_axis": "+Z", "up_axis_tolerance_degrees": 2.0}}]
        errs = _validate_standing_up_axis_rules_preopen(targets)
        assert len(errs) == 1
        assert "expected_world_up_axis" in errs[0]

    def test_expected_plus_tolerance(self):
        targets = [{"target_id": "F", "standing": {"expected_world_up_axis": "+Z", "up_axis_tolerance_degrees": 2.0}}]
        errs = _validate_standing_up_axis_rules_preopen(targets)
        assert len(errs) == 1
        assert "local_up_axis" in errs[0]
