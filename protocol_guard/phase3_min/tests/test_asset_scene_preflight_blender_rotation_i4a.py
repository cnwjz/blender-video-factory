"""Tests for Rotation I4A R6: return propagation, internal tagging, active-set recursion."""
import ast
import os
import sys
import textwrap
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

READER_PATH = os.path.join(ROOT, "protocol_guard", "phase3_min", "blender_scene_reader.py")

ENTRY_NAMES = {"_check_rotation", "_expected_euler_to_quaternion"}
FORBIDDEN_READ_PROPS = {"rotation_euler", "rotation_quaternion"}
FORBIDDEN_WRITE_PROPS = {"rotation_euler", "rotation_quaternion", "matrix_world"}


def _attr_chain(node):
    parts, cur = [], node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr); cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id); return list(reversed(parts))
    return None


def _shallow_nodes(body):
    """Walk body statements without descending into FunctionDef/AsyncFunctionDef/ClassDef."""
    all_nodes = []
    for stmt in body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        all_nodes.extend(ast.walk(stmt))
    return all_nodes


# Helper: exact violation match (avoids "2" matching "21")
def _has_v(violations, text):
    return any(x == text for x in violations)


class ReachableScopeAnalyzer:
    def __init__(self, tree):
        self.tree = tree
        self.all_funcs = {}
        self.nested_funcs = {}
        self.lambdas = {}
        self.func_aliases = {}
        self.local_aliases = {}
        self.lambda_aliases = {}
        self.local_parent = {}

        for n in ast.iter_child_nodes(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.all_funcs[n.name] = n

    def _get_reachable_funcs(self):
        reachable = {}
        per_func_aliases = defaultdict(dict)

        stack = list(self.all_funcs.get(n) for n in ENTRY_NAMES if n in self.all_funcs)
        while stack:
            fn = stack.pop()
            if fn.name in reachable:
                continue
            reachable[fn.name] = fn

            for node in fn.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    composite = f"{fn.name}.<locals>.{node.name}"
                    self.nested_funcs[(fn.name, node.name)] = node
                    self.local_parent[composite] = fn.name

            for node in ast.walk(fn):
                if isinstance(node, ast.Assign):
                    for t in node.targets:
                        if not isinstance(t, ast.Name):
                            continue
                        if isinstance(node.value, ast.Lambda):
                            self.lambdas[(fn.name, t.id)] = node.value
                        elif isinstance(node.value, ast.Name):
                            rhs = node.value.id
                            if rhs in self.all_funcs:
                                self.func_aliases[(fn.name, t.id)] = rhs
                                per_func_aliases[fn.name][t.id] = rhs
                                if rhs not in reachable:
                                    stack.append(self.all_funcs[rhs])
                            elif (fn.name, rhs) in self.nested_funcs:
                                self.local_aliases[(fn.name, t.id)] = rhs
                            elif (fn.name, rhs) in self.lambdas:
                                self.lambda_aliases[(fn.name, t.id)] = rhs
                            elif rhs in per_func_aliases.get(fn.name, {}):
                                target = per_func_aliases[fn.name][rhs]
                                self.func_aliases[(fn.name, t.id)] = target
                                per_func_aliases[fn.name][t.id] = target

                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    callee = node.func.id
                    if callee in self.all_funcs and callee not in reachable:
                        stack.append(self.all_funcs[callee])
                    elif callee in per_func_aliases.get(fn.name, {}):
                        target = per_func_aliases[fn.name][callee]
                        if target in self.all_funcs and target not in reachable:
                            stack.append(self.all_funcs[target])

        return reachable

    def _resolve_name(self, fname, name):
        seen = {name}
        current = name
        while True:
            if (fname, current) in self.func_aliases:
                target = self.func_aliases[(fname, current)]
                if target in seen: break
                seen.add(target); current = target; continue
            if (fname, current) in self.local_aliases:
                target = self.local_aliases[(fname, current)]
                if target in seen: break
                seen.add(target); current = target; continue
            if (fname, current) in self.lambda_aliases:
                target = self.lambda_aliases[(fname, current)]
                if target in seen: break
                seen.add(target); current = target; continue
            break
        return current

    def _tag_reachable_set(self, funcs):
        tags = defaultdict(dict)
        for fname, fn in funcs.items():
            for a in fn.args.args:
                if a.arg in ("root_obj", "matched_obj"):
                    tags[fname][a.arg] = "ROOT_OBJECT"

        changed = True
        iters = 0
        while changed and iters < 10:
            changed = False; iters += 1
            for fname, fn in funcs.items():
                local = dict(tags[fname])

                for node in ast.walk(fn):
                    if isinstance(node, ast.ImportFrom) and node.module == "mathutils":
                        for alias in node.names:
                            tag_name = alias.asname if alias.asname else alias.name
                            if alias.name == "Euler":
                                if local.get(tag_name) != "EULER_CONSTRUCTOR":
                                    local[tag_name] = "EULER_CONSTRUCTOR"; changed = True

                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            tag_name = alias.asname if alias.asname else alias.name
                            if alias.name == "mathutils":
                                if local.get(tag_name) != "MATHUTILS_MODULE":
                                    local[tag_name] = "MATHUTILS_MODULE"; changed = True

                    if isinstance(node, ast.Assign):
                        for t in node.targets:
                            if not isinstance(t, ast.Name): continue

                            if isinstance(node.value, ast.Name):
                                if node.value.id in local:
                                    if local.get(t.id) != local[node.value.id]:
                                        local[t.id] = local[node.value.id]; changed = True
                                elif node.value.id == "Euler":
                                    if local.get(t.id) != "EULER_CONSTRUCTOR":
                                        local[t.id] = "EULER_CONSTRUCTOR"; changed = True

                            if isinstance(node.value, ast.Attribute) and isinstance(node.value.ctx, ast.Load):
                                rcv = node.value.value
                                if isinstance(rcv, ast.Name) and local.get(rcv.id) == "ROOT_OBJECT":
                                    if node.value.attr == "matrix_world":
                                        if local.get(t.id) != "MATRIX_WORLD_VALUE":
                                            local[t.id] = "MATRIX_WORLD_VALUE"; changed = True

                            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute):
                                ch = _attr_chain(node.value.func)
                                if ch and ch[-1] == "to_quaternion" and local.get(ch[0]) == "MATRIX_WORLD_VALUE":
                                    if local.get(t.id) != "ACTUAL_QUATERNION":
                                        local[t.id] = "ACTUAL_QUATERNION"; changed = True

                            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                                if node.value.func.id == "Euler":
                                    if local.get(t.id) != "EULER_VALUE":
                                        local[t.id] = "EULER_VALUE"; changed = True
                                elif node.value.func.id == "_expected_euler_to_quaternion":
                                    if local.get(t.id) != "EXPECTED_QUATERNION":
                                        local[t.id] = "EXPECTED_QUATERNION"; changed = True
                                elif local.get(node.value.func.id) == "EULER_CONSTRUCTOR":
                                    if local.get(t.id) != "EULER_VALUE":
                                        local[t.id] = "EULER_VALUE"; changed = True

                            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute):
                                if node.value.func.attr == "Euler":
                                    rcv = node.value.func.value
                                    if isinstance(rcv, ast.Name) and local.get(rcv.id) == "MATHUTILS_MODULE":
                                        if local.get(t.id) != "EULER_VALUE":
                                            local[t.id] = "EULER_VALUE"; changed = True

                            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute):
                                ch2 = _attr_chain(node.value.func)
                                if ch2 and ch2[-1] == "to_quaternion" and local.get(ch2[0]) == "EULER_VALUE":
                                    if local.get(t.id) != "EXPECTED_QUATERNION":
                                        local[t.id] = "EXPECTED_QUATERNION"; changed = True

                            if isinstance(node.value, ast.Attribute) and node.value.attr == "to_quaternion":
                                rcv = node.value.value
                                if isinstance(rcv, ast.Name):
                                    if local.get(rcv.id) == "MATRIX_WORLD_VALUE":
                                        if local.get(t.id) != "MATRIX_TO_QUATERNION_METHOD":
                                            local[t.id] = "MATRIX_TO_QUATERNION_METHOD"; changed = True
                                    elif local.get(rcv.id) == "EULER_VALUE":
                                        if local.get(t.id) != "EULER_TO_QUATERNION_METHOD":
                                            local[t.id] = "EULER_TO_QUATERNION_METHOD"; changed = True

                            if isinstance(node.value, ast.Lambda):
                                if local.get(t.id) != "LAMBDA_FUNC":
                                    local[t.id] = "LAMBDA_FUNC"; changed = True
                            if isinstance(node.value, ast.Name) and node.value.id in funcs:
                                if local.get(t.id) != f"FUNC_ALIAS:{node.value.id}":
                                    local[t.id] = f"FUNC_ALIAS:{node.value.id}"; changed = True

                    # Parameter propagation
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                        callee = node.func.id
                        actual_callee = self._resolve_name(fname, callee)
                        if actual_callee not in funcs: continue
                        callee_fn = funcs[actual_callee]
                        for i, arg in enumerate(node.args):
                            if isinstance(arg, ast.Name) and arg.id in local:
                                for ci, ca in enumerate(callee_fn.args.args):
                                    if ci == i:
                                        if tags[actual_callee].get(ca.arg) != local[arg.id]:
                                            tags[actual_callee][ca.arg] = local[arg.id]; changed = True
                        for kw in node.keywords:
                            if isinstance(kw.value, ast.Name) and kw.value.id in local:
                                if tags[actual_callee].get(kw.arg) != local[kw.value.id]:
                                    tags[actual_callee][kw.arg] = local[kw.value.id]; changed = True

                    # Return value propagation from top-level calls
                    if isinstance(node, ast.Assign):
                        for t in node.targets:
                            if isinstance(t, ast.Name) and isinstance(node.value, ast.Call):
                                if isinstance(node.value.func, ast.Name):
                                    callee = node.value.func.id
                                    actual_callee = self._resolve_name(fname, callee)
                                    if actual_callee in funcs:
                                        callee_fn = funcs[actual_callee]
                                        for rn in ast.walk(callee_fn):
                                            if isinstance(rn, ast.Return) and isinstance(rn.value, ast.Name):
                                                src = tags[actual_callee].get(rn.value.id)
                                                if src and local.get(t.id) != src:
                                                    local[t.id] = src; changed = True
                                            if isinstance(rn, ast.Return) and isinstance(rn.value, ast.Attribute):
                                                rcv = rn.value.value
                                                if isinstance(rcv, ast.Name) and rn.value.attr == "matrix_world":
                                                    if tags[actual_callee].get(rcv.id) == "ROOT_OBJECT":
                                                        if local.get(t.id) != "MATRIX_WORLD_VALUE":
                                                            local[t.id] = "MATRIX_WORLD_VALUE"; changed = True

                tags[fname] = local
        return tags

    def _propagate_tags_in_body(self, body, initial_tags):
        """Fixed-point tag propagation within a local function/lambda body."""
        local_tags = dict(initial_tags)
        changed = True
        while changed:
            changed = False
            for stmt in body:
                for node in ast.walk(stmt):
                    if isinstance(node, ast.Assign):
                        for t in node.targets:
                            if not isinstance(t, ast.Name): continue
                            # Simple alias
                            if isinstance(node.value, ast.Name):
                                if node.value.id in local_tags:
                                    if local_tags.get(t.id) != local_tags[node.value.id]:
                                        local_tags[t.id] = local_tags[node.value.id]; changed = True
                            # mw2 = obj.matrix_world
                            if isinstance(node.value, ast.Attribute) and isinstance(node.value.ctx, ast.Load):
                                rcv = node.value.value
                                if isinstance(rcv, ast.Name) and local_tags.get(rcv.id) == "ROOT_OBJECT":
                                    if node.value.attr == "matrix_world":
                                        if local_tags.get(t.id) != "MATRIX_WORLD_VALUE":
                                            local_tags[t.id] = "MATRIX_WORLD_VALUE"; changed = True
                            # method = mw2.to_quaternion (no call — method alias)
                            if isinstance(node.value, ast.Attribute) and node.value.attr == "to_quaternion":
                                rcv = node.value.value
                                if isinstance(rcv, ast.Name):
                                    if local_tags.get(rcv.id) == "MATRIX_WORLD_VALUE":
                                        if local_tags.get(t.id) != "MATRIX_TO_QUATERNION_METHOD":
                                            local_tags[t.id] = "MATRIX_TO_QUATERNION_METHOD"; changed = True
                                    elif local_tags.get(rcv.id) == "EULER_VALUE":
                                        if local_tags.get(t.id) != "EULER_TO_QUATERNION_METHOD":
                                            local_tags[t.id] = "EULER_TO_QUATERNION_METHOD"; changed = True
                            # q = mw2.to_quaternion() — to_quaternion call
                            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute):
                                ch = _attr_chain(node.value.func)
                                if ch and ch[-1] == "to_quaternion" and local_tags.get(ch[0]) == "MATRIX_WORLD_VALUE":
                                    if local_tags.get(t.id) != "ACTUAL_QUATERNION":
                                        local_tags[t.id] = "ACTUAL_QUATERNION"; changed = True
        return local_tags

    def _compute_return_tag(self, fname, callee_name, args, keywords, fn_tags, funcs, tags):
        """Determine the tag of the return value from a local/lambda call.
        Also handles top-level function calls in return statements."""
        resolved = self._resolve_name(fname, callee_name)

        # Top-level function
        if resolved in funcs:
            callee_fn = funcs[resolved]
            arg_tags = {}
            for i, arg in enumerate(args):
                if isinstance(arg, ast.Name) and arg.id in fn_tags:
                    for ci, ca in enumerate(callee_fn.args.args):
                        if ci == i: arg_tags[ca.arg] = fn_tags[arg.id]
            for kw in keywords:
                if isinstance(kw.value, ast.Name) and kw.value.id in fn_tags:
                    arg_tags[kw.arg] = fn_tags[kw.value.id]
            # Use pre-computed tags for the callee to determine return
            callee_tags = tags.get(resolved, {})
            callee_merged = dict(callee_tags)
            callee_merged.update(arg_tags)
            for node in ast.walk(callee_fn):
                if isinstance(node, ast.Return) and node.value:
                    if isinstance(node.value, ast.Name):
                        return callee_merged.get(node.value.id)
                    if isinstance(node.value, ast.Attribute):
                        ch = _attr_chain(node.value)
                        if ch and callee_merged.get(ch[0]) == "ROOT_OBJECT" and ch[-1] == "matrix_world":
                            return "MATRIX_WORLD_VALUE"

        # Nested function
        nested_key = (fname, resolved)
        if nested_key in self.nested_funcs:
            nested_fn = self.nested_funcs[nested_key]
            arg_tags = {}
            for i, arg in enumerate(args):
                if isinstance(arg, ast.Name) and arg.id in fn_tags:
                    for ci, ca in enumerate(nested_fn.args.args):
                        if ci == i: arg_tags[ca.arg] = fn_tags[arg.id]
            for kw in keywords:
                if isinstance(kw.value, ast.Name) and kw.value.id in fn_tags:
                    arg_tags[kw.arg] = fn_tags[kw.value.id]
            # Propagate local tags
            prop = self._propagate_tags_in_body(nested_fn.body, arg_tags)
            for node in ast.walk(nested_fn):
                if isinstance(node, ast.Return) and node.value:
                    if isinstance(node.value, ast.Name):
                        return prop.get(node.value.id)
                    if isinstance(node.value, ast.Attribute):
                        ch = _attr_chain(node.value)
                        if ch and prop.get(ch[0]) == "ROOT_OBJECT" and ch[-1] == "matrix_world":
                            return "MATRIX_WORLD_VALUE"
                    if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                        return self._compute_return_tag(
                            nested_key[0], node.value.func.id,
                            node.value.args, node.value.keywords, prop, funcs, tags)

        # Lambda
        lambda_key = (fname, resolved)
        if lambda_key in self.lambdas:
            lam = self.lambdas[lambda_key]
            arg_tags = {}
            for i, arg in enumerate(args):
                if isinstance(arg, ast.Name) and arg.id in fn_tags:
                    for ci, ca in enumerate(lam.args.args):
                        if ci == i: arg_tags[ca.arg] = fn_tags[arg.id]
            for kw in keywords:
                if isinstance(kw.value, ast.Name) and kw.value.id in fn_tags:
                    arg_tags[kw.arg] = fn_tags[kw.value.id]
            body = lam.body
            if isinstance(body, ast.Name):
                return arg_tags.get(body.id)
            if isinstance(body, ast.Attribute):
                ch = _attr_chain(body)
                if ch and arg_tags.get(ch[0]) == "ROOT_OBJECT" and ch[-1] == "matrix_world":
                    return "MATRIX_WORLD_VALUE"
            # Lambda body is a call: lambda obj: helper(obj)
            if isinstance(body, ast.Call) and isinstance(body.func, ast.Name):
                return self._compute_return_tag(
                    fname, body.func.id, body.args, body.keywords, arg_tags, funcs, tags)

        return None

    def _count_nodes(self, all_nodes, fn_tags):
        mw_loads = 0; tq_calls = 0; euler_count = 0; order = None; etq_count = 0
        for node in all_nodes:
            if isinstance(node, ast.Attribute) and node.attr == "matrix_world" and isinstance(node.ctx, ast.Load):
                rcv = node.value
                if isinstance(rcv, ast.Name) and fn_tags.get(rcv.id) == "ROOT_OBJECT":
                    mw_loads += 1
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "to_quaternion":
                    ch = _attr_chain(node.func)
                    if ch and fn_tags.get(ch[0]) == "MATRIX_WORLD_VALUE":
                        tq_calls += 1
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "Euler":
                    euler_count += 1
                    if order is None and len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                        order = node.args[1].value
                elif fn_tags.get(node.func.id) == "EULER_CONSTRUCTOR":
                    euler_count += 1
                    if order is None and len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                        order = node.args[1].value
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "Euler":
                    rcv = node.func.value
                    if isinstance(rcv, ast.Name) and fn_tags.get(rcv.id) == "MATHUTILS_MODULE":
                        euler_count += 1
                        if order is None and len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                            order = node.args[1].value
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "to_quaternion":
                    ch = _attr_chain(node.func)
                    if ch and fn_tags.get(ch[0]) == "EULER_VALUE":
                        etq_count += 1
        return mw_loads, tq_calls, euler_count, order, etq_count

    def _check_forbidden(self, all_nodes, fn_tags):
        fv = []
        for node in all_nodes:
            if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
                if node.attr in FORBIDDEN_READ_PROPS:
                    rcv = node.value
                    if isinstance(rcv, ast.Name) and fn_tags.get(rcv.id) == "ROOT_OBJECT":
                        fv.append(f"FORBIDDEN_READ: {node.attr} (line {node.lineno})")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "getattr" and len(node.args) >= 2:
                    a0, a1 = node.args[0], node.args[1]
                    if isinstance(a0, ast.Name) and fn_tags.get(a0.id) == "ROOT_OBJECT":
                        if isinstance(a1, ast.Constant) and a1.value in FORBIDDEN_READ_PROPS:
                            fv.append(f"FORBIDDEN_GETATTR: {a1.value} (line {node.lineno})")
            if isinstance(node, ast.Attribute) and isinstance(node.ctx, (ast.Store, ast.Del)):
                rcv = node.value
                if isinstance(rcv, ast.Name) and fn_tags.get(rcv.id) in ("ROOT_OBJECT", "MATRIX_WORLD_VALUE", "EULER_VALUE"):
                    fv.append(f"FORBIDDEN_WRITE: {node.attr} {type(node.ctx).__name__} (line {node.lineno})")
            if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Attribute):
                rcv = node.target.value
                if isinstance(rcv, ast.Name) and fn_tags.get(rcv.id) in ("ROOT_OBJECT", "MATRIX_WORLD_VALUE", "EULER_VALUE"):
                    fv.append(f"FORBIDDEN_AUGASSIGN: {node.target.attr} (line {node.lineno})")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in ("setattr", "delattr") and len(node.args) >= 2:
                    a0 = node.args[0]
                    if isinstance(a0, ast.Name) and fn_tags.get(a0.id) in ("ROOT_OBJECT", "MATRIX_WORLD_VALUE", "EULER_VALUE"):
                        fv.append(f"FORBIDDEN_{node.func.id.upper()}: (line {node.lineno})")
        return fv

    def _build_call_tags(self, call_node, caller_tags, callee_fn):
        arg_tags = {}
        for i, arg in enumerate(call_node.args):
            if isinstance(arg, ast.Name) and arg.id in caller_tags:
                for ci, ca in enumerate(callee_fn.args.args):
                    if ci == i: arg_tags[ca.arg] = caller_tags[arg.id]
        for kw in call_node.keywords:
            if isinstance(kw.value, ast.Name) and kw.value.id in caller_tags:
                arg_tags[kw.arg] = caller_tags[kw.value.id]
        return arg_tags

    def _resolve_local_call_v2(self, fname, callee_name, args, keywords, fn_tags, funcs, active, tags):
        """Handle calls to nested functions / lambdas via alias chains.
        active: set of currently-active function names to prevent recursion re-entry."""
        resolved = self._resolve_name(fname, callee_name)

        # Nested function
        nested_key = (fname, resolved)
        if nested_key in self.nested_funcs:
            nested_fn = self.nested_funcs[nested_key]
            local_key = f"{fname}.<locals>.{resolved}"
            if local_key in active:
                return (0, 0, 0, None, 0, [])  # recursion guard
            active.add(local_key)

            arg_tags = {}
            for i, arg in enumerate(args):
                if isinstance(arg, ast.Name) and arg.id in fn_tags:
                    for ci, ca in enumerate(nested_fn.args.args):
                        if ci == i: arg_tags[ca.arg] = fn_tags[arg.id]
            for kw in keywords:
                if isinstance(kw.value, ast.Name) and kw.value.id in fn_tags:
                    arg_tags[kw.arg] = fn_tags[kw.value.id]

            # Propagate tags within body
            prop = self._propagate_tags_in_body(nested_fn.body, arg_tags)

            mw = tq = ec = etq = 0; order = None; fv = []

            shallow = _shallow_nodes(nested_fn.body)
            nm, nt, ne, no, netq = self._count_nodes(shallow, prop)
            mw += nm; tq += nt; ec += ne; etq += netq
            if order is None: order = no
            fv.extend(self._check_forbidden(shallow, prop))

            for sub_node in ast.walk(nested_fn):
                if isinstance(sub_node, ast.Call) and isinstance(sub_node.func, ast.Name):
                    sub_callee = sub_node.func.id
                    sub_resolved = self._resolve_name(nested_key[0], sub_callee)

                    # Top-level function called from local
                    if sub_resolved in funcs:
                        sub_tags = self._build_call_tags(sub_node, prop, funcs[sub_resolved])
                        nm2, nt2, ne2, no2, netq2, fv2 = self._traverse(
                            sub_resolved, sub_tags, funcs, tags, active, None)
                        mw += nm2; tq += nt2; ec += ne2; etq += netq2
                        if order is None: order = no2
                        fv.extend(fv2)

                    # Nested/lambda call
                    nm2, nt2, ne2, no2, netq2, fv2 = self._resolve_local_call_v2(
                        nested_key[0], sub_callee, sub_node.args, sub_node.keywords,
                        prop, funcs, active, tags)
                    mw += nm2; tq += nt2; ec += ne2; etq += netq2
                    if order is None: order = no2
                    fv.extend(fv2)

                    tag = prop.get(sub_node.func.id)
                    if tag == "MATRIX_TO_QUATERNION_METHOD": tq += 1
                    elif tag == "EULER_TO_QUATERNION_METHOD": etq += 1

            active.discard(local_key)
            return mw, tq, ec, order, etq, fv

        # Lambda
        lambda_key = (fname, resolved)
        if lambda_key in self.lambdas:
            lam = self.lambdas[lambda_key]
            lambda_name = f"{fname}.<lambda>.{resolved}"
            if lambda_name in active:
                return (0, 0, 0, None, 0, [])
            active.add(lambda_name)

            arg_tags = {}
            for i, arg in enumerate(args):
                if isinstance(arg, ast.Name) and arg.id in fn_tags:
                    for ci, ca in enumerate(lam.args.args):
                        if ci == i: arg_tags[ca.arg] = fn_tags[arg.id]
            for kw in keywords:
                if isinstance(kw.value, ast.Name) and kw.value.id in fn_tags:
                    arg_tags[kw.arg] = fn_tags[kw.value.id]

            mw = tq = ec = etq = 0; order = None; fv = []

            lam_nodes = list(ast.walk(lam.body))
            nm, nt, ne, no, netq = self._count_nodes(lam_nodes, arg_tags)
            mw += nm; tq += nt; ec += ne; etq += netq
            if order is None: order = no
            fv.extend(self._check_forbidden(lam_nodes, arg_tags))

            # Sub-calls from lambda body to top-level or local
            for sub_node in ast.walk(lam.body):
                if isinstance(sub_node, ast.Call) and isinstance(sub_node.func, ast.Name):
                    sub_callee = sub_node.func.id
                    sub_resolved = self._resolve_name(fname, sub_callee)
                    if sub_resolved in funcs:
                        sub_tags = self._build_call_tags(sub_node, arg_tags, funcs[sub_resolved])
                        nm2, nt2, ne2, no2, netq2, fv2 = self._traverse(
                            sub_resolved, sub_tags, funcs, tags, active, None)
                        mw += nm2; tq += nt2; ec += ne2; etq += netq2
                        if order is None: order = no2
                        fv.extend(fv2)
                    nm2, nt2, ne2, no2, netq2, fv2 = self._resolve_local_call_v2(
                        fname, sub_callee, sub_node.args, sub_node.keywords,
                        arg_tags, funcs, active, tags)
                    mw += nm2; tq += nt2; ec += ne2; etq += netq2
                    if order is None: order = no2
                    fv.extend(fv2)
                    tag = arg_tags.get(sub_node.func.id)
                    if tag == "MATRIX_TO_QUATERNION_METHOD": tq += 1
                    elif tag == "EULER_TO_QUATERNION_METHOD": etq += 1

            active.discard(lambda_name)
            return mw, tq, ec, order, etq, fv

        return (0, 0, 0, None, 0, [])

    def _traverse(self, fname, fn_tags, funcs, tags, active, visited_entries):
        """Recursively count violations from fname with given arg_tags.
        active: set of currently-active function names (prevents recursion re-entry).
        visited_entries: set of entry points already traversed (cross-entry dedup)."""
        if visited_entries is None:
            visited_entries = set()

        is_entry = fname in ENTRY_NAMES
        if is_entry:
            if fname in visited_entries:
                return (0, 0, 0, None, 0, [])
            visited_entries.add(fname)

        fn = funcs.get(fname)
        if fn is None:
            return (0, 0, 0, None, 0, [])

        if fname in active:
            return (0, 0, 0, None, 0, [])  # recursion guard
        active.add(fname)

        merged = dict(tags.get(fname, {}))
        merged.update(fn_tags)

        # Pre-pass: propagate return tags from local/lambda calls in assignments
        local_returns = {}
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                        ret_tag = self._compute_return_tag(
                            fname, node.value.func.id, node.value.args, node.value.keywords,
                            merged, funcs, tags)
                        if ret_tag:
                            local_returns[t.id] = ret_tag
        merged.update(local_returns)

        mw = tq = ec = etq = 0; order = None; fv = []

        shallow = _shallow_nodes(fn.body)
        nm, nt, ne, no, netq = self._count_nodes(shallow, merged)
        mw += nm; tq += nt; ec += ne; etq += netq
        if order is None: order = no
        fv.extend(self._check_forbidden(shallow, merged))

        for node in ast.walk(fn):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                callee_name = node.func.id
                resolved = self._resolve_name(fname, callee_name)

                if resolved in funcs and resolved != fname:
                    sub_tags = self._build_call_tags(node, merged, funcs[resolved])
                    nm, nt, ne, no, netq, sfv = self._traverse(
                        resolved, sub_tags, funcs, tags, active, visited_entries)
                    mw += nm; tq += nt; ec += ne; etq += netq
                    if order is None: order = no
                    fv.extend(sfv)

                nm, nt, ne, no, netq, sfv = self._resolve_local_call_v2(
                    fname, resolved, node.args, node.keywords, merged, funcs, active, tags)
                mw += nm; tq += nt; ec += ne; etq += netq
                if order is None: order = no
                fv.extend(sfv)

            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                tag = merged.get(node.func.id)
                if tag == "MATRIX_TO_QUATERNION_METHOD": tq += 1
                elif tag == "EULER_TO_QUATERNION_METHOD": etq += 1

        active.discard(fname)
        return mw, tq, ec, order, etq, fv

    def analyze(self):
        violations = []
        funcs = self._get_reachable_funcs()
        tags = self._tag_reachable_set(funcs)

        cr_fn = funcs.get("_check_rotation")
        ee_fn = funcs.get("_expected_euler_to_quaternion")
        if cr_fn is None:
            violations.append("MISSING: _check_rotation"); return violations
        if ee_fn is None:
            violations.append("MISSING: _expected_euler_to_quaternion"); return violations

        active = set()
        visited_entries = set()
        mw1, tq1, ec1, o1, etq1, fv1 = self._traverse(
            "_check_rotation", {}, funcs, tags, active, visited_entries)
        mw2, tq2, ec2, o2, etq2, fv2 = self._traverse(
            "_expected_euler_to_quaternion", {}, funcs, tags, active, visited_entries)

        total_mw = mw1 + mw2; total_tq = tq1 + tq2
        total_ec = ec1 + ec2; total_etq = etq1 + etq2
        order = o1 if o1 is not None else o2
        violations.extend(fv1); violations.extend(fv2)

        if total_mw != 1:
            violations.append(f"MW_LOAD_COUNT: {total_mw} (expected 1)")
        if total_tq != 1:
            violations.append(f"TO_QUATERNION_COUNT: {total_tq} (expected 1)")
        if total_ec != 1:
            violations.append(f"EULER_COUNT: {total_ec} (expected 1)")
        if order != "XYZ":
            violations.append(f"EULER_ORDER: {order} (expected XYZ)")
        if total_etq != 1:
            violations.append(f"EULER_TO_Q_COUNT: {total_etq} (expected 1)")

        return sorted(set(violations))


def _a(code):
    code = textwrap.dedent(code).strip()
    ast.parse(code)
    return ReachableScopeAnalyzer(ast.parse(code)).analyze()


# ═══════════════════════════════════════════════════════════════════════
# Production
# ═══════════════════════════════════════════════════════════════════════

class TestProduction:
    def test_scope_guard_clean(self):
        with open(READER_PATH, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=READER_PATH)
        assert ReachableScopeAnalyzer(tree).analyze() == []


# ═══════════════════════════════════════════════════════════════════════
# 24 Bad Probes (assertions use exact match via _has_v)
# ═══════════════════════════════════════════════════════════════════════

class TestAdversarialBad:

    def test_b01_second_mw_read(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    mw2 = root_obj.matrix_world
    q = mw.to_quaternion()
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert _has_v(v, "MW_LOAD_COUNT: 2 (expected 1)"), f"not detected: {v}"

    def test_b02_alias_second_mw(self):
        code = """
def _check_rotation(target, root_obj):
    obj = root_obj
    mw = obj.matrix_world
    mw2 = obj.matrix_world
    q = mw.to_quaternion()
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert _has_v(v, "MW_LOAD_COUNT: 2 (expected 1)"), f"not detected: {v}"

    def test_b03_helper_extra_mw(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    extra(root_obj)
    return q
def extra(obj):
    x = obj.matrix_world
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert _has_v(v, "MW_LOAD_COUNT: 2 (expected 1)"), f"not detected: {v}"

    def test_b04_multilevel_extra_mw(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    a(root_obj)
    return q
def a(obj):
    b(obj)
def b(obj):
    x = obj.matrix_world
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert _has_v(v, "MW_LOAD_COUNT: 2 (expected 1)"), f"not detected: {v}"

    def test_b05_second_to_quat(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    q2 = mw.to_quaternion()
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert _has_v(v, "TO_QUATERNION_COUNT: 2 (expected 1)"), f"not detected: {v}"

    def test_b06_method_alias_extra_call(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    method = mw.to_quaternion
    q2 = method()
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert _has_v(v, "TO_QUATERNION_COUNT: 2 (expected 1)"), f"not detected: {v}"

    def test_b07_helper_extra_to_quat(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    h(mw)
    return q
def h(mat):
    mat.to_quaternion()
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert _has_v(v, "TO_QUATERNION_COUNT: 2 (expected 1)"), f"not detected: {v}"

    def test_b08_second_euler(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    e2 = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert _has_v(v, "EULER_COUNT: 2 (expected 1)"), f"not detected: {v}"
        assert not _has_v(v, "MW_LOAD_COUNT: 0 (expected 1)")
        assert not _has_v(v, "TO_QUATERNION_COUNT: 0 (expected 1)")

    def test_b09_euler_alias_constructor(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    Constructor = Euler
    e2 = Constructor((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert _has_v(v, "EULER_COUNT: 2 (expected 1)"), f"not detected: {v}"
        assert not _has_v(v, "MW_LOAD_COUNT: 0 (expected 1)")
        assert not _has_v(v, "TO_QUATERNION_COUNT: 0 (expected 1)")

    def test_b10_helper_extra_euler(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    h()
    q = e.to_quaternion()
    return q
def h():
    from mathutils import Euler
    e2 = Euler((0,0,0), 'XYZ')
"""
        v = _a(code)
        assert _has_v(v, "EULER_COUNT: 2 (expected 1)"), f"not detected: {v}"
        assert not _has_v(v, "MW_LOAD_COUNT: 0 (expected 1)")
        assert not _has_v(v, "TO_QUATERNION_COUNT: 0 (expected 1)")

    def test_b11_multilevel_extra_euler(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    a()
    q = e.to_quaternion()
    return q
def a():
    b()
def b():
    from mathutils import Euler
    e2 = Euler((0,0,0), 'XYZ')
"""
        v = _a(code)
        assert _has_v(v, "EULER_COUNT: 2 (expected 1)"), f"not detected: {v}"
        assert not _has_v(v, "MW_LOAD_COUNT: 0 (expected 1)")
        assert not _has_v(v, "TO_QUATERNION_COUNT: 0 (expected 1)")

    def test_b12_second_euler_to_q(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    q2 = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert _has_v(v, "EULER_TO_Q_COUNT: 2 (expected 1)"), f"not detected: {v}"
        assert not _has_v(v, "MW_LOAD_COUNT: 0 (expected 1)")
        assert not _has_v(v, "TO_QUATERNION_COUNT: 0 (expected 1)")

    def test_b13_euler_method_alias(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    method = e.to_quaternion
    q = e.to_quaternion()
    q2 = method()
    return q
"""
        v = _a(code)
        assert _has_v(v, "EULER_TO_Q_COUNT: 2 (expected 1)"), f"not detected: {v}"
        assert not _has_v(v, "MW_LOAD_COUNT: 0 (expected 1)")
        assert not _has_v(v, "TO_QUATERNION_COUNT: 0 (expected 1)")

    def test_b14_read_rotation_euler(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    x = root_obj.rotation_euler
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert any("FORBIDDEN_READ: rotation_euler" in x for x in v), f"not detected: {v}"

    def test_b15_read_rotation_quat(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    x = root_obj.rotation_quaternion
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert any("FORBIDDEN_READ: rotation_quaternion" in x for x in v), f"not detected: {v}"

    def test_b16_getattr_rotation_euler(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    x = getattr(root_obj, 'rotation_euler')
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert any("FORBIDDEN_GETATTR: rotation_euler" in x for x in v), f"not detected: {v}"

    def test_b17_getattr_rotation_quat(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    x = getattr(root_obj, 'rotation_quaternion')
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert any("FORBIDDEN_GETATTR: rotation_quaternion" in x for x in v), f"not detected: {v}"

    def test_b18_direct_attr_write(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    root_obj.rotation_euler = (0,0,0)
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert any("FORBIDDEN_WRITE" in x and "rotation_euler" in x for x in v), f"not detected: {v}"

    def test_b19_del_attr(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    del root_obj.rotation_euler
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert any("FORBIDDEN_WRITE" in x and "Del" in x for x in v), f"not detected: {v}"

    def test_b20_augassign(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    root_obj.rotation_euler += 1
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert any("FORBIDDEN_AUGASSIGN" in x for x in v), f"not detected: {v}"

    def test_b21_setattr(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    setattr(root_obj, 'matrix_world', None)
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert any("FORBIDDEN_SETATTR" in x for x in v), f"not detected: {v}"

    def test_b22_delattr(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    delattr(root_obj, 'rotation_quaternion')
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert any("FORBIDDEN_DELATTR" in x for x in v), f"not detected: {v}"

    def test_b23_helper_write(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    h(root_obj)
    return q
def h(obj):
    obj.rotation_euler = (0,0,0)
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert any("FORBIDDEN_WRITE" in x for x in v), f"not detected: {v}"

    def test_b24_multilevel_write(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    a(root_obj)
    return q
def a(obj):
    b(obj)
def b(obj):
    setattr(obj, 'rotation_euler', (0,0,0))
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert any("FORBIDDEN_SETATTR" in x for x in v), f"not detected: {v}"


# ═══════════════════════════════════════════════════════════════════════
# R4 Verification Probes (preserved, adapted to _has_v for counts)
# ═══════════════════════════════════════════════════════════════════════

class TestVerificationR4:

    def test_local_helper_extra_mw(self):
        code = """
def _check_rotation(target, root_obj):
    def local(obj):
        return obj.matrix_world
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    local(root_obj)
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert _has_v(v, "MW_LOAD_COUNT: 2 (expected 1)"), f"not detected: {v}"

    def test_lambda_extra_mw(self):
        code = """
def _check_rotation(target, root_obj):
    f = lambda obj: obj.matrix_world
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    f(root_obj)
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert _has_v(v, "MW_LOAD_COUNT: 2 (expected 1)"), f"not detected: {v}"

    def test_func_alias_extra_mw(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    f = helper
    f(root_obj)
    return q
def helper(obj):
    return obj.matrix_world
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert _has_v(v, "MW_LOAD_COUNT: 2 (expected 1)"), f"not detected: {v}"

    def test_matrix_method_alias_extra_call(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    method = mw.to_quaternion
    q2 = method()
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert _has_v(v, "TO_QUATERNION_COUNT: 2 (expected 1)"), f"not detected: {v}"

    def test_euler_method_alias_extra_call(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    method = e.to_quaternion
    q = e.to_quaternion()
    q2 = method()
    return q
"""
        v = _a(code)
        assert _has_v(v, "EULER_TO_Q_COUNT: 2 (expected 1)"), f"not detected: {v}"

    def test_euler_from_import_alias_legal(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    return q
def _expected_euler_to_quaternion(values):
    from mathutils import Euler as E
    e = E(values, "XYZ")
    return e.to_quaternion()
"""
        assert _a(code) == []

    def test_euler_module_alias_legal(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    return q
def _expected_euler_to_quaternion(values):
    import mathutils as mu
    e = mu.Euler(values, "XYZ")
    return e.to_quaternion()
"""
        assert _a(code) == []

    def test_euler_variable_alias_legal(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    return q
def _expected_euler_to_quaternion(values):
    from mathutils import Euler
    Constructor = Euler
    e = Constructor(values, "XYZ")
    return e.to_quaternion()
"""
        assert _a(code) == []


# ═══════════════════════════════════════════════════════════════════════
# R5 Verification Probes (preserved, adapted to _has_v for counts)
# ═══════════════════════════════════════════════════════════════════════

class TestVerificationR5:

    def test_local_via_alias(self):
        code = """
def _check_rotation(target, root_obj):
    def local(obj):
        return obj.matrix_world
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    f = local
    f(root_obj)
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert _has_v(v, "MW_LOAD_COUNT: 2 (expected 1)"), f"not detected: {v}"

    def test_lambda_via_alias_chain(self):
        code = """
def _check_rotation(target, root_obj):
    f = lambda obj: obj.matrix_world
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    g = f
    g(root_obj)
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert _has_v(v, "MW_LOAD_COUNT: 2 (expected 1)"), f"not detected: {v}"

    def test_top_alias_chain(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    f = helper
    g = f
    g(root_obj)
    return q
def helper(obj):
    return obj.matrix_world
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert _has_v(v, "MW_LOAD_COUNT: 2 (expected 1)"), f"not detected: {v}"

    def test_local_read_rotation_euler(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    def local(obj):
        x = obj.rotation_euler
    local(root_obj)
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert any("FORBIDDEN_READ: rotation_euler" in x for x in v), f"not detected: {v}"

    def test_local_attr_write(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    def local(obj):
        obj.rotation_euler = (0,0,0)
    local(root_obj)
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert any("FORBIDDEN_WRITE" in x and "rotation_euler" in x for x in v), f"not detected: {v}"

    def test_local_setattr(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    def local(obj):
        setattr(obj, 'rotation_euler', (0,0,0))
    local(root_obj)
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert any("FORBIDDEN_SETATTR" in x for x in v), f"not detected: {v}"

    def test_lambda_setattr(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    f = lambda obj: setattr(obj, 'rotation_euler', (0,0,0))
    f(root_obj)
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert any("FORBIDDEN_SETATTR" in x for x in v), f"not detected: {v}"

    def test_helper_called_twice(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    helper(root_obj)
    helper(root_obj)
    return q
def helper(obj):
    x = obj.matrix_world
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert _has_v(v, "MW_LOAD_COUNT: 3 (expected 1)"), f"not detected: {v}"

    def test_helper_keyword_arg(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    helper(obj=root_obj)
    return q
def helper(obj):
    x = obj.matrix_world
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert _has_v(v, "MW_LOAD_COUNT: 2 (expected 1)"), f"not detected: {v}"

    def test_helper_return_mw_then_to_quat(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    x = get_mw(root_obj)
    q2 = x.to_quaternion()
    return q
def get_mw(obj):
    return obj.matrix_world
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert _has_v(v, "TO_QUATERNION_COUNT: 2 (expected 1)"), f"not detected: {v}"

    def test_helper_return_root_obj_then_read_euler(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    obj = get_root(root_obj)
    x = obj.rotation_euler
    return q
def get_root(obj):
    return obj
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert any("FORBIDDEN_READ: rotation_euler" in x for x in v), f"not detected: {v}"


# ═══════════════════════════════════════════════════════════════════════
# R6 Verification Probes: return propagation, internal tagging, recursion
# ═══════════════════════════════════════════════════════════════════════

class TestVerificationR6:

    def test_local_return_mw_legal_convert(self):
        """Local helper returns matrix_world, caller converts legally."""
        code = """
def _check_rotation(target, root_obj):
    def get_mw(obj):
        return obj.matrix_world
    x = get_mw(root_obj)
    q = x.to_quaternion()
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        assert _a(code) == []

    def test_lambda_return_mw_legal_convert(self):
        """Lambda returns matrix_world, caller converts legally."""
        code = """
def _check_rotation(target, root_obj):
    get_mw = lambda obj: obj.matrix_world
    x = get_mw(root_obj)
    q = x.to_quaternion()
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        assert _a(code) == []

    def test_local_return_root_obj_read_euler(self):
        """Local helper returns root_obj, caller reads rotation_euler."""
        code = """
def _check_rotation(target, root_obj):
    def get_root(obj):
        return obj
    x = get_root(root_obj)
    y = x.rotation_euler
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert any("FORBIDDEN_READ: rotation_euler" in x for x in v), f"not detected: {v}"

    def test_local_internal_extra_to_quat(self):
        """Local helper internally does an extra to_quaternion call."""
        code = """
def _check_rotation(target, root_obj):
    def local(obj):
        mw2 = obj.matrix_world
        q2 = mw2.to_quaternion()
        return q2
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    local(root_obj)
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert _has_v(v, "TO_QUATERNION_COUNT: 2 (expected 1)"), f"not detected: {v}"

    def test_local_internal_method_alias_extra(self):
        """Local helper uses method alias internally for extra tq call."""
        code = """
def _check_rotation(target, root_obj):
    def local(obj):
        mw2 = obj.matrix_world
        method = mw2.to_quaternion
        method()
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    local(root_obj)
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert _has_v(v, "TO_QUATERNION_COUNT: 2 (expected 1)"), f"not detected: {v}"

    def test_recursive_helper_extra_mw(self):
        """Recursive helper reads matrix_world exactly once per static body."""
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    recurse(root_obj, 3)
    return q
def recurse(obj, n):
    x = obj.matrix_world
    if n > 0:
        recurse(obj, n-1)
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert _has_v(v, "MW_LOAD_COUNT: 2 (expected 1)"), f"not detected: {v}"


# ═══════════════════════════════════════════════════════════════════════
# R7 Verification Probes: return helper() propagation
# ═══════════════════════════════════════════════════════════════════════

class TestVerificationR7:

    def test_local_return_top_helper_mw_legal(self):
        code = """
def _check_rotation(target, root_obj):
    def local(obj):
        return get_mw(obj)
    x = local(root_obj)
    q = x.to_quaternion()
    return q
def get_mw(obj):
    return obj.matrix_world
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        assert _a(code) == []

    def test_lambda_return_top_helper_mw_legal(self):
        code = """
def _check_rotation(target, root_obj):
    f = lambda obj: get_mw(obj)
    x = f(root_obj)
    q = x.to_quaternion()
    return q
def get_mw(obj):
    return obj.matrix_world
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        assert _a(code) == []

    def test_lambda_return_local_helper_mw_legal(self):
        code = """
def _check_rotation(target, root_obj):
    def local_mw(obj):
        return obj.matrix_world
    f = lambda obj: local_mw(obj)
    x = f(root_obj)
    q = x.to_quaternion()
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        assert _a(code) == []

    def test_local_return_top_identity_read_euler(self):
        code = """
def _check_rotation(target, root_obj):
    def local(obj):
        return identity(obj)
    x = local(root_obj)
    y = x.rotation_euler
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    return q
def identity(obj):
    return obj
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert any("FORBIDDEN_READ: rotation_euler" in x for x in v), f"not detected: {v}"


# ═══════════════════════════════════════════════════════════════════════
# Clean Probes
# ═══════════════════════════════════════════════════════════════════════

class TestAdversarialClean:
    def test_production_clean(self):
        with open(READER_PATH, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=READER_PATH)
        assert ReachableScopeAnalyzer(tree).analyze() == []

    def test_unused_helper_ignored(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    return q
def unused(obj):
    obj.rotation_euler = (0,0,0)
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        assert _a(code) == []

    def test_unused_local_helper_ignored(self):
        code = """
def _check_rotation(target, root_obj):
    def local(obj):
        return obj.matrix_world
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        assert _a(code) == []

    def test_unused_lambda_ignored(self):
        code = """
def _check_rotation(target, root_obj):
    f = lambda obj: obj.matrix_world
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        assert _a(code) == []

    def test_unused_func_alias_ignored(self):
        code = """
def _check_rotation(target, root_obj):
    f = helper
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    return q
def helper(obj):
    return obj.matrix_world
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        assert _a(code) == []

    def test_string_comment_no_false(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    msg = "rotation_euler"
    # rotation_euler
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        assert _a(code) == []

    def test_unrelated_to_quat_no_false(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    class Foo:
        def to_quaternion(self): return (1,0,0,0)
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        assert _a(code) == []

    def test_standing_facing_legal_mw(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
def _check_standing(target, root_obj):
    mw = root_obj.matrix_world
    local_y = mw.to_3x3() @ (0,1,0)
    return local_y
def _check_facing(target, root_obj):
    mw = root_obj.matrix_world
    fwd = mw.to_3x3() @ (0,-1,0)
    return fwd
"""
        assert _a(code) == []

    def test_euler_aliases_legal(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    return q
def _expected_euler_to_quaternion(values):
    from mathutils import Euler as E
    e = E(values, "XYZ")
    return e.to_quaternion()
"""
        assert _a(code) == []

    def test_uncalled_local_class_ignored(self):
        code = """
def _check_rotation(target, root_obj):
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    class Foo:
        def to_quaternion(self):
            return (1,0,0,0)
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        assert _a(code) == []

    def test_local_recursion_no_crash(self):
        code = """
def _check_rotation(target, root_obj):
    def recurse(obj, n):
        if n > 0:
            recurse(obj, n-1)
        return obj.matrix_world
    mw = root_obj.matrix_world
    q = mw.to_quaternion()
    recurse(root_obj, 3)
    return q
def _expected_euler_to_quaternion(erw):
    from mathutils import Euler
    e = Euler((0,0,0), 'XYZ')
    q = e.to_quaternion()
    return q
"""
        v = _a(code)
        assert _has_v(v, "MW_LOAD_COUNT: 2 (expected 1)"), f"not detected: {v}"


# ═══════════════════════════════════════════════════════════════════════
# Self-integrity
# ═══════════════════════════════════════════════════════════════════════

def test_no_len_greater_zero():
    with open(__file__, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_") and node.name != "test_no_len_greater_zero":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Compare) and isinstance(sub.left, ast.Call) and isinstance(sub.left.func, ast.Name):
                    if sub.left.func.id == "len" and any(isinstance(c, ast.Constant) and c.value == 0 for c in sub.comparators):
                        raise AssertionError(f"test {node.name}: len(x) > 0 not allowed (line {node.lineno})")


def test_no_bare_violations_assertions():
    with open(__file__, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_") and node.name not in (
                "test_no_len_greater_zero", "test_no_bare_violations_assertions",
                "test_test_file_self_parse", "test_test_file_no_skip_xfail",
                "test_all_bad_probes_exist", "test_all_probes_ast_parse",
                "test_b06_has_real_method_alias", "test_b13_has_real_method_alias",
                "test_b09_has_exact_euler_count_2"):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Assert):
                    if isinstance(sub.test, ast.Name):
                        raise AssertionError(f"test {node.name}: bare 'assert violations' not allowed")


def test_test_file_self_parse():
    with open(__file__, "r", encoding="utf-8") as f:
        ast.parse(f.read())


def test_test_file_no_skip_xfail():
    with open(__file__, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = None
            if isinstance(node.func, ast.Attribute): name = node.func.attr
            elif isinstance(node.func, ast.Name): name = node.func.id
            if name in ("skip", "skipif", "xfail", "importorskip"):
                raise AssertionError(f"line {node.lineno}: {name}()")


def test_all_bad_probes_exist():
    expected = {f"test_b{i:02d}" for i in range(1, 25)}
    found = set()
    with open(__file__, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_b"):
            base = node.name.split("_")[0] + "_" + node.name.split("_")[1]
            found.add(base)
    missing = expected - found
    assert not missing, f"missing bad probes: {missing}"


def test_all_probes_ast_parse():
    with open(__file__, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Assign) and any(
                        isinstance(t, ast.Name) and t.id == "code" for t in sub.targets):
                    if isinstance(sub.value, ast.Constant) and isinstance(sub.value.value, str):
                        code_str = textwrap.dedent(sub.value.value).strip()
                        ast.parse(code_str)


def test_b06_has_real_method_alias():
    with open(__file__, "r", encoding="utf-8") as f:
        content = f.read()
    assert "method = mw.to_quaternion" in content, "B06 missing: method = mw.to_quaternion"


def test_b13_has_real_method_alias():
    with open(__file__, "r", encoding="utf-8") as f:
        content = f.read()
    assert "method = e.to_quaternion" in content, "B13 missing: method = e.to_quaternion"


def test_b09_has_exact_euler_count_2():
    with open(__file__, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    found_b09 = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "test_b09_euler_alias_constructor":
            found_b09 = True
            found_assertion = False
            for sub in ast.walk(node):
                if isinstance(sub, ast.Assert):
                    code_str = ast.unparse(sub.test)
                    if 'EULER_COUNT: 2' in code_str:
                        found_assertion = True
                        break
            assert found_assertion, "B09 missing exact EULER_COUNT: 2 assertion"
    assert found_b09, "B09 test not found"
