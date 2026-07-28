"""Tests for 14B-2D-I1A: required_descendant_types input validation."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from protocol_guard.phase3_min.asset_scene_preflight_check import _validate_direct_child_rules_preopen


def _has_error(errors, fragment):
    return any(fragment in e for e in errors)


class TestFieldMissingNullEmpty:
    def test_field_missing_no_error(self):
        targets = [{"target_id": "A", "hierarchy": {}}]
        errs = _validate_direct_child_rules_preopen(targets)
        assert not _has_error(errs, "INVALID_DESCENDANT_TYPE_RULE_VALUE")

    def test_field_null_no_error(self):
        targets = [{"target_id": "A", "hierarchy": {"required_descendant_types": None}}]
        errs = _validate_direct_child_rules_preopen(targets)
        assert not _has_error(errs, "INVALID_DESCENDANT_TYPE_RULE_VALUE")

    def test_field_empty_object_no_error(self):
        targets = [{"target_id": "A", "hierarchy": {"required_descendant_types": {}}}]
        errs = _validate_direct_child_rules_preopen(targets)
        assert not _has_error(errs, "INVALID_DESCENDANT_TYPE_RULE_VALUE")


class TestValidKeyValues:
    def test_single_valid_key_value_no_error(self):
        targets = [{"target_id": "A", "hierarchy": {"required_descendant_types": {"Armature": "ARMATURE"}}}]
        errs = _validate_direct_child_rules_preopen(targets)
        assert not _has_error(errs, "INVALID_DESCENDANT_TYPE_RULE_VALUE")

    def test_multiple_valid_key_values_no_error(self):
        targets = [{"target_id": "A", "hierarchy": {"required_descendant_types": {
            "Armature": "ARMATURE", "Body": "MESH", "Head": "MESH"
        }}}]
        errs = _validate_direct_child_rules_preopen(targets)
        assert not _has_error(errs, "INVALID_DESCENDANT_TYPE_RULE_VALUE")

    def test_unknown_type_string_accepted(self):
        targets = [{"target_id": "A", "hierarchy": {"required_descendant_types": {"Custom": "FUTURE_BLENDER_TYPE"}}}]
        errs = _validate_direct_child_rules_preopen(targets)
        assert not _has_error(errs, "INVALID_DESCENDANT_TYPE_RULE_VALUE")


class TestInvalidKeys:
    def test_empty_string_key_rejected(self):
        targets = [{"target_id": "A", "hierarchy": {"required_descendant_types": {"": "MESH"}}}]
        errs = _validate_direct_child_rules_preopen(targets)
        assert _has_error(errs, "INVALID_DESCENDANT_TYPE_RULE_VALUE")
        assert any("empty descendant name" in e for e in errs)

    def test_non_string_key_rejected(self):
        targets = [{"target_id": "A", "hierarchy": {"required_descendant_types": {1: "MESH"}}}]
        errs = _validate_direct_child_rules_preopen(targets)
        assert _has_error(errs, "INVALID_DESCENDANT_TYPE_RULE_VALUE")
        assert any("non-string key" in e for e in errs)


class TestInvalidValues:
    def test_null_value_rejected(self):
        targets = [{"target_id": "A", "hierarchy": {"required_descendant_types": {"Body": None}}}]
        errs = _validate_direct_child_rules_preopen(targets)
        assert _has_error(errs, "INVALID_DESCENDANT_TYPE_RULE_VALUE")
        assert any("'Body'" in e for e in errs)

    def test_empty_string_value_rejected(self):
        targets = [{"target_id": "A", "hierarchy": {"required_descendant_types": {"Body": ""}}}]
        errs = _validate_direct_child_rules_preopen(targets)
        assert _has_error(errs, "INVALID_DESCENDANT_TYPE_RULE_VALUE")
        assert any("'Body'" in e for e in errs)

    def test_numeric_value_rejected(self):
        targets = [{"target_id": "A", "hierarchy": {"required_descendant_types": {"Body": 123}}}]
        errs = _validate_direct_child_rules_preopen(targets)
        assert _has_error(errs, "INVALID_DESCENDANT_TYPE_RULE_VALUE")

    def test_bool_value_rejected(self):
        targets = [{"target_id": "A", "hierarchy": {"required_descendant_types": {"Body": True}}}]
        errs = _validate_direct_child_rules_preopen(targets)
        assert _has_error(errs, "INVALID_DESCENDANT_TYPE_RULE_VALUE")

    def test_list_value_rejected(self):
        targets = [{"target_id": "A", "hierarchy": {"required_descendant_types": {"Body": ["MESH"]}}}]
        errs = _validate_direct_child_rules_preopen(targets)
        assert _has_error(errs, "INVALID_DESCENDANT_TYPE_RULE_VALUE")

    def test_object_value_rejected(self):
        targets = [{"target_id": "A", "hierarchy": {"required_descendant_types": {"Body": {"type": "MESH"}}}}]
        errs = _validate_direct_child_rules_preopen(targets)
        assert _has_error(errs, "INVALID_DESCENDANT_TYPE_RULE_VALUE")


class TestMultipleErrorsStable:
    def test_multiple_errors_sorted(self):
        targets = [{"target_id": "Z", "hierarchy": {"required_descendant_types": {
            "Body": "", "Armature": None, "Head": 123
        }}}]
        errs = _validate_direct_child_rules_preopen(targets)
        type_errs = [e for e in errs if "INVALID_DESCENDANT_TYPE_RULE_VALUE" in e]
        assert len(type_errs) == 3
        # Should be sorted by key: Armature, Body, Head
        assert "Armature" in type_errs[0]
        assert "Body" in type_errs[1]
        assert "Head" in type_errs[2]


class TestExistingRulesUnaffected:
    def test_direct_child_validation_unchanged(self):
        targets = [{"target_id": "A", "hierarchy": {
            "required_direct_child_names": [""],
            "required_descendant_types": {"Valid": "MESH"},
        }}]
        errs = _validate_direct_child_rules_preopen(targets)
        assert _has_error(errs, "INVALID_DIRECT_CHILD_RULE_VALUE")
        assert not _has_error(errs, "INVALID_DESCENDANT_TYPE_RULE_VALUE")

    def test_descendant_name_validation_unchanged(self):
        targets = [{"target_id": "A", "hierarchy": {
            "required_descendant_names": [""],
            "required_descendant_types": {"Valid": "MESH"},
        }}]
        errs = _validate_direct_child_rules_preopen(targets)
        assert _has_error(errs, "INVALID_DESCENDANT_RULE_VALUE")
        assert any("required_descendant_names" in e for e in errs)
        assert not _has_error(errs, "INVALID_DESCENDANT_TYPE_RULE_VALUE")
