"""Test stop condition evaluator."""
from protocol_guard.gate.conditions import evaluate_stop_conditions, action_to_result
from protocol_guard.result import TechnicalResult

class TestConditions:
    def test_no_trigger(self):
        triggered, action, cond = evaluate_stop_conditions(
            [{"condition": "x", "action": "stop_current_task"}], {"x": False})
        assert not triggered

    def test_triggered(self):
        triggered, action, cond = evaluate_stop_conditions(
            [{"condition": "fail", "action": "mark_technical_fail"}], {"fail": True})
        assert triggered
        assert action == "mark_technical_fail"

    def test_action_mapping(self):
        assert action_to_result("stop_before_execution") == TechnicalResult.TECHNICAL_FAIL
        assert action_to_result("mark_constraint_conflict") == TechnicalResult.CONSTRAINT_CONFLICT
        assert action_to_result("mark_evidence_invalid") == TechnicalResult.EVIDENCE_INVALID
        assert action_to_result("mark_spec_invalid") == TechnicalResult.SPEC_INVALID
        assert action_to_result("unknown") == TechnicalResult.TECHNICAL_FAIL

    def test_context_partial_match(self):
        triggered, action, cond = evaluate_stop_conditions(
            [{'condition': 'a', 'action': 'mark_technical_fail'},
             {'condition': 'b', 'action': 'stop_current_task'}],
            {'a': False, 'b': True})
        assert triggered
        assert cond == 'b'

    def test_single_condition_list(self):
        triggered, action, cond = evaluate_stop_conditions(
            [{'condition': 'only', 'action': 'mark_spec_invalid'}],
            {'only': True})
        assert triggered
        assert action == 'mark_spec_invalid'

    def test_stop_before_execution_maps_to_technical_fail(self):
        from protocol_guard.gate.conditions import action_to_result
        from protocol_guard.result import TechnicalResult
        assert action_to_result('stop_before_execution') == TechnicalResult.TECHNICAL_FAIL

    def test_stop_current_task_maps_to_technical_fail(self):
        from protocol_guard.gate.conditions import action_to_result
        from protocol_guard.result import TechnicalResult
        assert action_to_result('stop_current_task') == TechnicalResult.TECHNICAL_FAIL

    def test_all_actions_covered(self):
        from protocol_guard.gate.conditions import ACTION_MAP
        assert len(ACTION_MAP) == 6

    def test_evaluate_empty_context(self):
        triggered, action, cond = evaluate_stop_conditions(
            [{"condition":"x","action":"stop_current_task"}], {})
        assert not triggered
