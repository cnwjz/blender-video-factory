"""Stop condition evaluator for Phase 2A gate."""

from protocol_guard.result import TechnicalResult

ACTION_MAP = {
    "stop_before_execution": TechnicalResult.TECHNICAL_FAIL,
    "stop_current_task": TechnicalResult.TECHNICAL_FAIL,
    "mark_technical_fail": TechnicalResult.TECHNICAL_FAIL,
    "mark_constraint_conflict": TechnicalResult.CONSTRAINT_CONFLICT,
    "mark_evidence_invalid": TechnicalResult.EVIDENCE_INVALID,
    "mark_spec_invalid": TechnicalResult.SPEC_INVALID,
}


def evaluate_stop_conditions(stop_conditions, context):
    """Evaluate stop conditions against a context dict.

    Args:
        stop_conditions: list of {condition, action} dicts from task card
        context: dict of metric_name -> actual_value (e.g. {"clipped_count": 0})

    Returns:
        (triggered: bool, action: str|None, condition_name: str|None)
    """
    for sc in stop_conditions:
        cond_name = sc.get("condition", "")
        action = sc.get("action", "stop_current_task")
        if cond_name in context and context[cond_name]:
            return (True, action, cond_name)
    return (False, None, None)


def action_to_result(action):
    """Map stop condition action to TechnicalResult."""
    return ACTION_MAP.get(action, TechnicalResult.TECHNICAL_FAIL)
