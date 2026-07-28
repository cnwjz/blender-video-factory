"""Lint focused test files for structural hygiene and optional policy compliance.

Checks performed on every --test-path:
  - file exists, non-zero, ast.parse succeeds
  - at least one test_ function present
  - no skip/xfail/importorskip markers
  - no early return in test_ functions (bare or valued)

Optional --policy-json enables deeper AST-level checks.
Policy JSON schema is validated before use.

Exit codes: 0 = pass, 1 = violations found, 2 = usage/IO/JSON error.
"""
import argparse
import ast
import json
import os
import sys

FORBIDDEN_DECORATORS = {"skip", "skipif", "xfail", "importorskip"}
FORBIDDEN_FUNCTIONS = {
    "skip", "skipif", "xfail", "importorskip",
    "pytest.mark.skip", "pytest.mark.skipif", "pytest.mark.xfail",
    "pytest.skip", "pytest.xfail", "pytest.importorskip",
    "unittest.skip", "unittest.skipIf", "unittest.skipUnless",
}


def _validate_policy(policy):
    """Validate policy JSON schema. Returns list of error strings (empty = valid)."""
    errors = []
    if not isinstance(policy, dict):
        return ["POLICY_JSON_INVALID: top-level must be an object"]
    allowed_top = {"required_assert_literals", "required_assignments", "required_calls"}
    for key in policy:
        if key not in allowed_top:
            errors.append(f"POLICY_JSON_INVALID: unknown key '{key}'")
    # required_assert_literals
    if "required_assert_literals" in policy:
        ral = policy["required_assert_literals"]
        if not isinstance(ral, dict):
            errors.append("POLICY_JSON_INVALID: required_assert_literals must be an object")
        else:
            for test_name, literals in ral.items():
                if not isinstance(test_name, str) or not test_name:
                    errors.append("POLICY_JSON_INVALID: test name must be non-empty string")
                if not isinstance(literals, list):
                    errors.append(f"POLICY_JSON_INVALID: {test_name} value must be a list")
                else:
                    for item in literals:
                        if not isinstance(item, str):
                            errors.append(f"POLICY_JSON_INVALID: {test_name} item must be string")
    # required_assignments
    if "required_assignments" in policy:
        ra = policy["required_assignments"]
        if not isinstance(ra, dict):
            errors.append("POLICY_JSON_INVALID: required_assignments must be an object")
        else:
            for test_name, specs in ra.items():
                if not isinstance(test_name, str) or not test_name:
                    errors.append("POLICY_JSON_INVALID: test name must be non-empty string")
                if not isinstance(specs, list):
                    errors.append(f"POLICY_JSON_INVALID: {test_name} value must be a list")
                else:
                    for spec in specs:
                        if not isinstance(spec, dict):
                            errors.append(f"POLICY_JSON_INVALID: {test_name} item must be object")
                        else:
                            t = spec.get("target", "")
                            s = spec.get("source", "")
                            if not isinstance(t, str) or not t:
                                errors.append("POLICY_JSON_INVALID: target must be non-empty string")
                            if not isinstance(s, str) or not s:
                                errors.append("POLICY_JSON_INVALID: source must be non-empty string")
    # required_calls
    if "required_calls" in policy:
        rc = policy["required_calls"]
        if not isinstance(rc, dict):
            errors.append("POLICY_JSON_INVALID: required_calls must be an object")
        else:
            for test_name, specs in rc.items():
                if not isinstance(test_name, str) or not test_name:
                    errors.append("POLICY_JSON_INVALID: test name must be non-empty string")
                if not isinstance(specs, list):
                    errors.append(f"POLICY_JSON_INVALID: {test_name} value must be a list")
                else:
                    for spec in specs:
                        if not isinstance(spec, dict):
                            errors.append(f"POLICY_JSON_INVALID: {test_name} item must be object")
                        else:
                            r = spec.get("receiver", "")
                            m = spec.get("method", "")
                            la = spec.get("literal_args", [])
                            if not isinstance(r, str) or not r:
                                errors.append("POLICY_JSON_INVALID: receiver must be non-empty string")
                            if not isinstance(m, str) or not m:
                                errors.append("POLICY_JSON_INVALID: method must be non-empty string")
                            if not isinstance(la, list):
                                errors.append("POLICY_JSON_INVALID: literal_args must be a list")
    return errors


def lint_file(test_path, policy=None):
    """Return dict of findings for one test file."""
    findings = {
        "path": test_path,
        "errors": [],
        "test_function_count": 0,
        "skip_xfail_count": 0,
        "early_return_count": 0,
        "assert_policy_failures": 0,
        "assignment_policy_failures": 0,
        "call_policy_failures": 0,
    }

    if not os.path.exists(test_path):
        findings["errors"].append(f"FILE_NOT_FOUND: {test_path}")
        return findings
    if os.path.getsize(test_path) == 0:
        findings["errors"].append(f"FILE_EMPTY: {test_path}")
        return findings

    try:
        with open(test_path, encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=test_path)
    except SyntaxError as e:
        findings["errors"].append(f"SYNTAX_ERROR: {e}")
        return findings

    test_funcs = []

    class FuncVisitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            if node.name.startswith("test_"):
                test_funcs.append(node)
            self.generic_visit(node)
        visit_AsyncFunctionDef = visit_FunctionDef

    FuncVisitor().visit(tree)
    findings["test_function_count"] = len(test_funcs)

    if len(test_funcs) == 0:
        findings["errors"].append("NO_TEST_FUNCTIONS: file has no test_ functions")

    # Decorators + call names
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for dec in node.decorator_list:
                name = _dec_name(dec)
                if name and name in FORBIDDEN_DECORATORS:
                    findings["errors"].append(
                        f"SKIP_XFAIL: @{name} at line {getattr(dec, 'lineno', '?')}"
                    )
                    findings["skip_xfail_count"] += 1
        if isinstance(node, ast.Call):
            name = _call_name(node)
            if name and name in FORBIDDEN_FUNCTIONS:
                findings["errors"].append(
                    f"SKIP_XFAIL: {name}() at line {getattr(node, 'lineno', '?')}"
                )
                findings["skip_xfail_count"] += 1
            elif isinstance(node.func, ast.Attribute) and node.func.attr in FORBIDDEN_DECORATORS:
                findings["errors"].append(
                    f"SKIP_XFAIL: .{node.func.attr}() at line {getattr(node, 'lineno', '?')}"
                )
                findings["skip_xfail_count"] += 1

    # F-001: Early return — catch ALL Return nodes (bare + valued)
    for fn in test_funcs:
        for node in ast.walk(fn):
            if isinstance(node, ast.Return):
                findings["errors"].append(
                    f"EARLY_RETURN: {fn.name} at line {node.lineno}"
                )
                findings["early_return_count"] += 1

    # Policy checks
    if policy:
        _check_policy(findings, tree, test_funcs, policy)

    return findings


def _dec_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _call_name(node):
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        chain = []
        cur = node.func
        while isinstance(cur, ast.Attribute):
            chain.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            chain.append(cur.id)
            return ".".join(reversed(chain))
        return ".".join(reversed(chain))
    return None


def _find_test_func(test_funcs, name):
    for fn in test_funcs:
        if fn.name == name:
            return fn
    return None


def _check_policy(findings, tree, test_funcs, policy):
    # F-002: required_assert_literals — only scan ast.Assert.test, not Assert.msg
    for test_name, literals in policy.get("required_assert_literals", {}).items():
        fn = _find_test_func(test_funcs, test_name)
        if fn is None:
            findings["errors"].append(
                f"POLICY_ASSERT: test '{test_name}' not found"
            )
            findings["assert_policy_failures"] += 1
            continue
        for lit in literals:
            found = False
            for node in ast.walk(fn):
                if isinstance(node, ast.Assert):
                    # Only scan the .test subtree, not .msg
                    for sub in ast.walk(node.test):
                        if isinstance(sub, ast.Constant) and sub.value == lit:
                            found = True
                            break
                if found:
                    break
            if not found:
                findings["errors"].append(
                    f"POLICY_ASSERT: '{lit}' not in assert.test of {test_name}"
                )
                findings["assert_policy_failures"] += 1

    # Required assignments
    for test_name, specs in policy.get("required_assignments", {}).items():
        fn = _find_test_func(test_funcs, test_name)
        if fn is None:
            findings["errors"].append(
                f"POLICY_ASSIGN: test '{test_name}' not found"
            )
            findings["assignment_policy_failures"] += 1
            continue
        for spec in specs:
            target = spec.get("target")
            source = spec.get("source")
            found = False
            for node in ast.walk(fn):
                if isinstance(node, ast.Assign):
                    if (len(node.targets) == 1
                            and isinstance(node.targets[0], ast.Name)
                            and node.targets[0].id == target
                            and isinstance(node.value, ast.Name)
                            and node.value.id == source):
                        found = True
                        break
            if not found:
                findings["errors"].append(
                    f"POLICY_ASSIGN: '{target} = {source}' not found in {test_name}"
                )
                findings["assignment_policy_failures"] += 1

    # Required calls
    for test_name, specs in policy.get("required_calls", {}).items():
        fn = _find_test_func(test_funcs, test_name)
        if fn is None:
            findings["errors"].append(
                f"POLICY_CALL: test '{test_name}' not found"
            )
            findings["call_policy_failures"] += 1
            continue
        for spec in specs:
            receiver = spec.get("receiver")
            method = spec.get("method")
            literal_args = spec.get("literal_args", [])
            found = False
            for node in ast.walk(fn):
                if (isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr == method
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == receiver):
                    all_ok = True
                    for lit in literal_args:
                        lit_found = any(
                            isinstance(a, ast.Constant) and a.value == lit
                            for a in node.args
                        )
                        if not lit_found:
                            all_ok = False
                            break
                    if all_ok:
                        found = True
                        break
            if not found:
                findings["errors"].append(
                    f"POLICY_CALL: {receiver}.{method}({literal_args}) "
                    f"not found in {test_name}"
                )
                findings["call_policy_failures"] += 1


def main():
    parser = argparse.ArgumentParser(description="Lint focused test files")
    parser.add_argument("--test-path", action="append", default=[], dest="test_paths")
    parser.add_argument("--policy-json", default=None)
    args = parser.parse_args()

    if not args.test_paths:
        print("ERROR: --test-path is required", file=sys.stderr)
        sys.exit(2)

    policy = None
    if args.policy_json:
        try:
            with open(args.policy_json, encoding="utf-8") as f:
                policy = json.load(f)
        except FileNotFoundError as e:
            print(f"ERROR: policy file not found: {e}", file=sys.stderr)
            sys.exit(2)
        except json.JSONDecodeError as e:
            print(f"POLICY_JSON_INVALID: {e}", file=sys.stderr)
            sys.exit(2)

        # F-003: Validate policy schema
        schema_errors = _validate_policy(policy)
        if schema_errors:
            for se in schema_errors:
                print(se, file=sys.stderr)
            sys.exit(2)

    all_findings = []
    for tp in args.test_paths:
        f = lint_file(tp, policy)
        all_findings.append(f)

    # F-003: TOTAL_VIOLATIONS = count of unique errors only
    total_violations = sum(len(f["errors"]) for f in all_findings)

    status = "PASS" if total_violations == 0 else "FAIL"

    print(f"LINT_FOCUSED_TEST_STATUS: {status}")
    print(f"FILES_CHECKED: {len(args.test_paths)}")
    total_funcs = sum(f["test_function_count"] for f in all_findings)
    print(f"TEST_FUNCTION_COUNT: {total_funcs}")
    print(f"SKIP_XFAIL_VIOLATION_COUNT: {sum(f['skip_xfail_count'] for f in all_findings)}")
    print(f"EARLY_RETURN_COUNT: {sum(f['early_return_count'] for f in all_findings)}")
    print(f"ASSERT_POLICY_FAILURE_COUNT: {sum(f['assert_policy_failures'] for f in all_findings)}")
    print(f"ASSIGNMENT_POLICY_FAILURE_COUNT: {sum(f['assignment_policy_failures'] for f in all_findings)}")
    print(f"CALL_POLICY_FAILURE_COUNT: {sum(f['call_policy_failures'] for f in all_findings)}")
    print(f"TOTAL_VIOLATIONS: {total_violations}")
    for f in all_findings:
        for e in f["errors"]:
            print(f"  {f['path']}: {e}")

    if total_violations > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
