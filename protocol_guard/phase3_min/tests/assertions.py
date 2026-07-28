"""Shared assertion helpers for protocol_guard tests.

Import in test files as:
    from protocol_guard.phase3_min.tests.assertions import assert_dict_equal
"""


def _values_equal(actual, expected):
    """Strict equality: same type AND same value.

    Rejects cross-type coercions like True == 1, 1 == 1.0, False == 0.
    """
    if type(actual) is not type(expected):
        return False
    return actual == expected


def assert_dict_equal(actual, expected, path=""):
    """Recursive dict equality with exact key-set AND strict type check.

    Fails on:
      - extra keys in actual not in expected
      - missing keys in expected not in actual
      - value type mismatch (True vs 1, 1 vs 1.0, False vs 0)
      - value content mismatch
      - nested dicts compared recursively
    """
    __tracebackhide__ = True
    assert isinstance(actual, dict), f"{path}: expected dict, got {type(actual).__name__}"
    assert isinstance(expected, dict), f"{path}: expected dict, got {type(expected).__name__}"
    a_keys = set(actual.keys())
    e_keys = set(expected.keys())
    extra = a_keys - e_keys
    missing = e_keys - a_keys
    assert not extra, f"{path}: extra keys {extra}"
    assert not missing, f"{path}: missing keys {missing}"
    for k in e_keys:
        full = f"{path}.{k}" if path else k
        if isinstance(expected[k], dict):
            assert isinstance(actual[k], dict), (
                f"{full}: expected dict, got {type(actual[k]).__name__}"
            )
            assert_dict_equal(actual[k], expected[k], full)
        else:
            ok = _values_equal(actual[k], expected[k])
            assert ok, (
                f"{full}: expected {expected[k]!r} (type {type(expected[k]).__name__}), "
                f"got {actual[k]!r} (type {type(actual[k]).__name__})"
            )


def assert_no_extra_keys(obj, allowed, label="result"):
    """Verify a dict has no keys beyond the allowed set."""
    __tracebackhide__ = True
    extra = set(obj.keys()) - set(allowed)
    assert not extra, f"{label}: extra keys {extra}"


def assert_result_has_fields(result, required_fields, label="result"):
    """Verify a dict contains all required top-level fields."""
    __tracebackhide__ = True
    missing = set(required_fields) - set(result.keys())
    assert not missing, f"{label}: missing required fields {missing}"
