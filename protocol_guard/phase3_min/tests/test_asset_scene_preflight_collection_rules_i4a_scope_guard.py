"""Collection Rules I4A R5 — unbounded scope walker + fixed-point + comprehensions.

Production: blender_scene_reader.py — frozen.
"""
import ast, os, sys, textwrap
from collections import defaultdict
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
READER_PATH = os.path.join(ROOT, "protocol_guard", "phase3_min", "blender_scene_reader.py")
with open(READER_PATH, encoding="utf-8") as f:
    _REAL = f.read()

class T:
    UNK=0; ORD=1; BPY=2; B_DATA=3; B_COLL=4; C_LIST=5; C_OBJ=6
    R_OBJ=7; G=8; H=9; S=10; D=11; RET_PARAM=12

AUTH_B = {"_check_collection_rules_global", "_materialize_bpy_data_collections"}
AUTH_U = {"_check_collection_membership"}
AUTH_CH = {"_materialize_collection_ancestor_index"}
AUTH_CN = {"_check_collection_rules_global", "_materialize_bpy_data_collections"}
CR = {*AUTH_B, *AUTH_U, *AUTH_CH, *AUTH_CN,
      "_compute_ancestor_closure", "_resolve_root_for_collection_rules",
      "_cr_global_error", "_cr_per_target_error"}
PROT = {"users_collection", "children", "name"}
BLTN = {"getattr":T.G,"hasattr":T.H,"setattr":T.S,"delattr":T.D}


def _attr_chain(node):
    parts, cur = [], node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr); cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id); return list(reversed(parts))
    return None


def _str_const(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        l, r = _str_const(node.left), _str_const(node.right)
        return (l + r) if (l is not None and r is not None) else None
    return None


def _walk_scope(node):
    """Recursive scope walker: yields (node, kind) where kind is 'normal', 'nested_fn', 'lambda', 'comp'."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield (child, 'nested_fn')
            continue
        if isinstance(child, ast.ClassDef):
            continue
        if isinstance(child, ast.Lambda):
            yield (child, 'lambda')
            continue
        if isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            yield (child, 'comp')
            continue
        yield (child, 'normal')
        yield from _walk_scope(child)


def _expr_tag(node, env):
    if isinstance(node, ast.Name):
        return env.get(node.id, (T.UNK, None))
    if isinstance(node, ast.Attribute):
        chain = _attr_chain(node)
        if chain:
            if chain == ["bpy", "data", "collections"]: return (T.B_COLL, None)
            if chain == ["bpy", "data"]: return (T.B_DATA, None)
            if len(chain)==3 and chain[1:]==["data","collections"]:
                bt = env.get(chain[0], (T.UNK, None))
                if bt[0] in {T.BPY, T.B_DATA}: return (T.B_COLL, "via")
            if chain[-1] == "users_collection": return (T.C_LIST, None)
            recv = _expr_tag(node.value, env)
            if recv[0] in {T.C_LIST, T.B_COLL, T.C_OBJ}: return (T.C_OBJ, None)
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in {"list","tuple","set","iter","enumerate"} and node.args:
            at = _expr_tag(node.args[0], env)
            if at[0] in {T.B_COLL, T.C_LIST}: return (T.C_LIST, None)
            return at
        if isinstance(node.func, ast.Attribute) and node.func.attr == "get":
            ot = _expr_tag(node.func.value, env)
            if ot[1]=="collection_by_id" or ot[0] in {T.C_LIST, T.C_OBJ}: return (T.C_OBJ, None)
        # Function call return tracking
        if isinstance(node.func, ast.Name) and node.func.id in env:
            ft = env[node.func.id]
            if ft[0] == T.RET_PARAM:
                # Return parameter index — resolve at call site
                param_idx = ft[1]
                if isinstance(param_idx, int) and param_idx < len(node.args):
                    return _expr_tag(node.args[param_idx], env)
            if ft[0] != T.UNK: return ft
    if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
        if node.generators:
            gs = _expr_tag(node.generators[0].iter, env)
            if gs[0] in {T.C_LIST, T.B_COLL}: return (T.C_OBJ, None)
            return gs
    if isinstance(node, ast.Subscript):
        ot = _expr_tag(node.value, env)
        if ot[0] in {T.C_LIST, T.B_COLL}: return (T.C_OBJ, None)
        return ot
    return (T.UNK, None)


def _build_local_env(func_body, param_env):
    """Build local environment recursively through control flow."""
    env = dict(param_env)

    def _walk(stmts):
        for stmt in stmts:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if isinstance(stmt, ast.Assign) and not isinstance(stmt.value, ast.Lambda):
                tag = _expr_tag(stmt.value, env)
                if isinstance(stmt.value, ast.Name):
                    if stmt.value.id in BLTN: tag = (BLTN[stmt.value.id], stmt.value.id)
                    ot = env.get(stmt.value.id, (T.UNK, None))
                    if ot[0] in {T.G,T.H,T.S,T.D}: tag = ot
                if isinstance(stmt.value, ast.Attribute):
                    c = _attr_chain(stmt.value)
                    if c == ["bpy","data"]: tag = (T.B_DATA, None)
                    if c == ["bpy","data","collections"]: tag = (T.B_COLL, None)
                for t in stmt.targets:
                    if isinstance(t, ast.Name) and tag[0] != T.UNK:
                        old = env.get(t.id, (T.UNK, None))
                        if old != tag: env[t.id] = tag
            elif isinstance(stmt, ast.For):
                it_tag = _expr_tag(stmt.iter, env)
                if isinstance(stmt.target, ast.Name):
                    if it_tag[0] in {T.C_LIST, T.B_COLL}: env[stmt.target.id] = (T.C_OBJ, None)
                    elif it_tag[0] not in {T.UNK, T.ORD}: env[stmt.target.id] = it_tag
                _walk(stmt.body)
                if stmt.orelse: _walk(stmt.orelse)
            elif isinstance(stmt, (ast.If, ast.While)):
                _walk(stmt.body)
                if stmt.orelse: _walk(stmt.orelse)
            elif isinstance(stmt, ast.With):
                _walk(stmt.body)
            elif isinstance(stmt, ast.Try):
                _walk(stmt.body)
                for h in stmt.handlers: _walk(h.body)
                if stmt.orelse: _walk(stmt.orelse)
                if stmt.finalbody: _walk(stmt.finalbody)
            elif isinstance(stmt, ast.Match):
                for c in stmt.cases: _walk(c.body)
    _walk(func_body)
    return env


def _compute_return_tag(func_body, env):
    """Compute return tag: (T.RET_PARAM, idx) for identity, or concrete tag."""
    for node in ast.walk(func_body):
        if isinstance(node, ast.Return) and node.value:
            if isinstance(node.value, ast.Name):
                # Check if it's a parameter
                if node.value.id in {a.arg for a in (getattr(ast.walk(func_body), '__not_needed__', None) or [])}:
                    pass
                param_names = set()
                # Get function args from parent FunctionDef
            rt = _expr_tag(node.value, env)
            if rt[0] != T.UNK:
                return rt
    return (T.UNK, None)


def _get_func_args(func_node):
    return [a.arg for a in func_node.args.args]


def analyze_source(source, filename="<test>"):
    tree = ast.parse(source)
    all_funcs = {n.name: n for n in ast.iter_child_nodes(tree)
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

    # Init param envs
    param_envs = {}
    for name, fn in all_funcs.items():
        pe = {}
        for arg in fn.args.args:
            t, m = T.UNK, None
            if arg.arg == "root_obj": t, m = T.R_OBJ, "root_obj"
            if arg.arg == "all_collections": t, m = T.C_LIST, "all_collections"
            if arg.arg == "direct_collections": t, m = T.C_LIST, "direct_collections"
            if arg.arg == "collection_by_id": m = "collection_by_id"
            pe[arg.arg] = (t, m)
        param_envs[name] = pe

    local_envs = {}
    ret_tags = {}

    # Build initial local envs
    for name, fn in all_funcs.items():
        local_envs[name] = _build_local_env(fn.body, param_envs[name])

    # Compute initial return tags (identity detection)
    for name, fn in all_funcs.items():
        args = _get_func_args(fn)
        for node in ast.walk(fn):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name != name:
                continue
            if isinstance(node, ast.Return) and node.value:
                if isinstance(node.value, ast.Name) and node.value.id in args:
                    idx = args.index(node.value.id)
                    ret_tags[name] = (T.RET_PARAM, idx)
                else:
                    rt = _expr_tag(node.value, local_envs[name])
                    if rt[0] != T.UNK:
                        ret_tags[name] = rt

    # Fixed-point: 10 rounds
    for iteration in range(10):
        changed = False

        # Rebuild local envs with current params
        for name, fn in all_funcs.items():
            new_env = _build_local_env(fn.body, param_envs[name])
            if new_env != local_envs.get(name):
                local_envs[name] = new_env
                changed = True

        # Recompute return tags
        for name, fn in all_funcs.items():
            env = local_envs[name]
            old_rt = ret_tags.get(name, (T.UNK, None))
            new_rt = (T.UNK, None)
            args = _get_func_args(fn)
            for node in ast.walk(fn):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name != name:
                    continue
                if isinstance(node, ast.Return) and node.value:
                    if isinstance(node.value, ast.Name) and node.value.id in args:
                        new_rt = (T.RET_PARAM, args.index(node.value.id))
                    elif isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                        # F-005: two-level return: _ha returns _hb(v) where _hb returns v
                        callee = node.value.func.id
                        if callee in ret_tags:
                            crt = ret_tags[callee]
                            if crt[0] == T.RET_PARAM and isinstance(crt[1], int) and crt[1] < len(node.value.args):
                                actual = node.value.args[crt[1]]
                                if isinstance(actual, ast.Name) and actual.id in args:
                                    new_rt = (T.RET_PARAM, args.index(actual.id))
                    if new_rt[0] == T.UNK:
                        rt = _expr_tag(node.value, env)
                        if rt[0] != T.UNK: new_rt = rt
                    break
            if new_rt != old_rt:
                ret_tags[name] = new_rt
                changed = True

        # Propagate call args
        for cname, cfn in all_funcs.items():
            cenv = local_envs[cname]
            for node, kind in _walk_scope(cfn):
                if kind != 'normal':
                    continue
                # Call argument propagation
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    callee = node.func.id
                    if callee in all_funcs:
                        callee_args = _get_func_args(all_funcs[callee])
                        for i, arg in enumerate(node.args):
                            if i >= len(callee_args): break
                            atag = _expr_tag(arg, cenv)
                            if atag[0] != T.UNK:
                                pname = callee_args[i]
                                old = param_envs[callee].get(pname, (T.UNK, None))
                                if old[0] == T.UNK:
                                    param_envs[callee][pname] = atag
                                    changed = True
                # Return assignment propagation
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name):
                        callee = node.value.func.id
                        if callee in ret_tags:
                            rt = ret_tags[callee]
                            if rt[0] != T.UNK:
                                # For RET_PARAM, resolve with actual args
                                resolved = rt
                                if rt[0] == T.RET_PARAM:
                                    idx = rt[1]
                                    if isinstance(idx, int) and idx < len(node.value.args):
                                        resolved = _expr_tag(node.value.args[idx], cenv)
                                if resolved[0] != T.UNK:
                                    for t in node.targets:
                                        if isinstance(t, ast.Name):
                                            cenv[t.id] = resolved
                                            changed = True

        if not changed:
            break

    # ── violation scan ──
    violations = []
    add = violations.append

    for fname, fn in all_funcs.items():
        env = local_envs[fname]
        counts = defaultdict(int)
        _scan_body(fn, fname, env, counts, add, all_funcs, local_envs)

    return sorted(violations)


def _scan_body(func, fname, env, counts, add, all_funcs, local_envs):
    """Recursive scope scanner."""
    for node, kind in _walk_scope(func):
        if kind == 'nested_fn':
            nested = node
            n_name = f"{fname}.<locals>.{nested.name}"
            n_env = dict(env)
            for arg in nested.args.args:
                n_env[arg.arg] = (T.UNK, None)
            # F-003: Propagate call args to nested
            for n2, k2 in _walk_scope(func):
                if k2 == 'normal' and isinstance(n2, ast.Call) and isinstance(n2.func, ast.Name):
                    if n2.func.id == nested.name:
                        n_args = _get_func_args(nested)
                        for i, arg in enumerate(n2.args):
                            if i >= len(n_args): break
                            atag = _expr_tag(arg, env)
                            if atag[0] != T.UNK:
                                n_env[n_args[i]] = atag
            n_counts = defaultdict(int)
            _scan_body(nested, n_name, n_env, n_counts, add, all_funcs, local_envs)
            continue

        if kind == 'lambda':
            lam = node
            l_name = f"{fname}.<lambda>"
            l_env = dict(env)
            for arg in lam.args.args:
                l_env[arg.arg] = (T.UNK, None)
            # F-004: Propagate call args to lambda
            for n2, k2 in _walk_scope(func):
                if k2 == 'normal' and isinstance(n2, ast.Call) and isinstance(n2.func, ast.Name):
                    if n2.func.id in env:
                        from_tag = _expr_tag(n2.func, env)
                    l_args = [a.arg for a in lam.args.args]
                    if l_args:
                        for i, arg in enumerate(n2.args):
                            if i >= len(l_args): break
                            atag = _expr_tag(arg, env)
                            if atag[0] != T.UNK:
                                l_env[l_args[i]] = atag
            l_counts = defaultdict(int)
            for n2, k2 in _walk_scope(lam):
                if k2 == 'normal' and isinstance(n2, ast.Attribute):
                    _check_read(n2, l_name, l_env, l_counts, add)
            continue

        if kind == 'comp':
            comp = node
            c_env = dict(env)
            for gen in comp.generators:
                it_tag = _expr_tag(gen.iter, c_env)
                if isinstance(gen.target, ast.Name):
                    if it_tag[0] in {T.C_LIST, T.B_COLL}:
                        c_env[gen.target.id] = (T.C_OBJ, None)
                    elif it_tag[0] not in {T.UNK, T.ORD}:
                        c_env[gen.target.id] = it_tag
            # Scan comp elements
            elt_nodes = [comp.elt] if hasattr(comp, 'elt') else []
            if hasattr(comp, 'key'): elt_nodes.append(comp.key)
            if hasattr(comp, 'value'): elt_nodes.append(comp.value)
            for elt in elt_nodes:
                for n2 in ast.walk(elt):
                    if isinstance(n2, ast.Attribute):
                        _check_read(n2, fname, c_env, counts, add)
                    _check_write_node(n2, fname, c_env, add)
                    _check_dynamic(n2, fname, c_env, add)
            continue

        if kind == 'normal':
            if isinstance(node, ast.Attribute):
                _check_read(node, fname, env, counts, add)
            _check_write_node(node, fname, env, add)
            _check_dynamic(node, fname, env, add)


def _check_read(node, fname, env, counts, add):
    if not isinstance(node.ctx, ast.Load): return
    chain = _attr_chain(node)
    if chain is None: return

    if chain == ["bpy","data","collections"]:
        counts["bpy"]+=1
        if fname not in AUTH_B: add(f"UNAUTHORIZED_READ:{fname}:bpy.data.collections")
        elif counts["bpy"]>1: add(f"EXTRA_AUTHORIZED_READ:{fname}:bpy.data.collections count={counts['bpy']}")
        return
    if len(chain)==2 and chain[-1]=="collections":
        receiver=node.value
        if isinstance(receiver, ast.Name):
            rt=env.get(receiver.id,(T.UNK,None))
            if rt[0] in {T.B_DATA, T.BPY}:
                counts["bpy"]+=1
                # F-002: alias is always a violation
                add(f"UNAUTHORIZED_ALIAS_READ:{fname}:bpy.data.collections")
                return
    if chain[-1]=="users_collection":
        counts["users"]+=1
        if fname not in AUTH_U: add(f"UNAUTHORIZED_READ:{fname}:users_collection")
        else:
            receiver=node.value
            if isinstance(receiver, ast.Name) and receiver.id!="root_obj": add(f"UNAUTHORIZED_ALIAS_READ:{fname}:users_collection via {receiver.id}")
            elif counts["users"]>1: add(f"EXTRA_AUTHORIZED_READ:{fname}:users_collection count={counts['users']}")
        return
    if chain[-1]=="children":
        receiver=node.value
        if isinstance(receiver, ast.Name):
            rt=env.get(receiver.id,(T.UNK,None))
            if rt[0] in {T.C_OBJ, T.C_LIST}:
                counts["ch"]+=1
                if fname not in AUTH_CH: add(f"COLLECTION_READ_OUTSIDE_SCOPE:{fname}:children")
                elif counts["ch"]>1: add(f"EXTRA_AUTHORIZED_READ:{fname}:children count={counts['ch']}")
        return
    if chain[-1]=="name":
        receiver=node.value
        if isinstance(receiver, ast.Name):
            rt=env.get(receiver.id,(T.UNK,None))
            if receiver.id in {"dc","parent_col"}: add(f"UNAUTHORIZED_READ:{fname}:{receiver.id}.name")
            elif rt[0]==T.C_OBJ:
                if fname not in AUTH_CN: add(f"COLLECTION_READ_OUTSIDE_SCOPE:{fname}:collection.name")
        return


def _check_write_node(node, fname, env, add):
    if isinstance(node,(ast.Assign,ast.AugAssign)):
        targets=node.targets if hasattr(node,'targets') else [node.target]
        for t in targets:
            if isinstance(t,ast.Attribute) and t.attr in PROT: _check_write(t,fname,env,add)
    if isinstance(node,ast.Delete):
        for t in node.targets:
            if isinstance(t,ast.Attribute) and t.attr in PROT: _check_write(t,fname,env,add)


def _check_write(target,fname,env,add):
    attr=target.attr; receiver=target.value
    if isinstance(receiver,ast.Name):
        rt=env.get(receiver.id,(T.UNK,None))
        if attr=="users_collection": add(f"WRITE_PROTECTED:{fname}:users_collection")
        elif attr=="children" and rt[0] in {T.C_OBJ,T.C_LIST}: add(f"WRITE_PROTECTED:{fname}:collection.children")


def _check_dynamic(node,fname,env,add):
    if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Name): return
    n=node.func.id; ftag=env.get(n,(T.UNK,None))
    is_dyn=n in {"getattr","hasattr","setattr","delattr"} or ftag[0] in {T.G,T.H,T.S,T.D}
    if is_dyn and node.args:
        s=_str_const(node.args[1]) if len(node.args)>=2 else None
        if s in PROT:
            recv=node.args[0]
            if isinstance(recv,ast.Name):
                rt=env.get(recv.id,(T.UNK,None))
                # F-001: getattr(root_obj, "users_collection") always forbidden
                root_obj_dyn = (s=="users_collection" and recv.id=="root_obj")
                if rt[0] in {T.C_OBJ,T.C_LIST,T.R_OBJ} or root_obj_dyn:
                    op=ftag[1] if ftag[1] in {"getattr","hasattr","setattr","delattr"} else n
                    if op in {"getattr","hasattr"}: add(f"DYNAMIC_ACCESS:{fname}:{op}:{s}")
                    else: add(f"WRITE_PROTECTED:{fname}:{op}:{s}")


# ════════════════ tests ═══════════════════════════════════════════════

class TestProduction:
    def test_real_zero(self): assert analyze_source(_REAL) == []
    def test_funcs_exist(self):
        t=ast.parse(_REAL)
        for n in CR: assert len([x for x in ast.walk(t) if isinstance(x,ast.FunctionDef) and x.name==n])==1,f"{n}"
    def test_no_impl(self):
        assert len([x for x in ast.walk(ast.parse(_REAL)) if isinstance(x,ast.FunctionDef) and x.name=="__check_collection_rules_global_impl"])==0
    def test_bpy_ct(self):
        t=ast.parse(_REAL);c=defaultdict(int)
        for f in ast.walk(t):
            if not isinstance(f,ast.FunctionDef): continue
            for n in ast.walk(f):
                if isinstance(n,ast.Attribute) and isinstance(n.ctx,ast.Load):
                    if _attr_chain(n)==["bpy","data","collections"]: c[f.name]+=1
        assert c["_check_collection_rules_global"]==1; assert c["_materialize_bpy_data_collections"]==1
    def test_users_ct(self):
        t=ast.parse(_REAL);c=defaultdict(int)
        for f in ast.walk(t):
            if not isinstance(f,ast.FunctionDef): continue
            for n in ast.walk(f):
                if isinstance(n,ast.Attribute) and isinstance(n.ctx,ast.Load) and n.attr=="users_collection": c[f.name]+=1
        assert c["_check_collection_membership"]==1
    def test_ch_ct(self):
        t=ast.parse(_REAL);c=defaultdict(int)
        for f in ast.walk(t):
            if not isinstance(f,ast.FunctionDef) or f.name not in CR: continue
            for n in ast.walk(f):
                if isinstance(n,ast.Attribute) and isinstance(n.ctx,ast.Load) and n.attr=="children": c[f.name]+=1
        assert c["_materialize_collection_ancestor_index"]==1; assert c.get("_compute_ancestor_closure",0)==0
    def test_cn_ct(self):
        t=ast.parse(_REAL);c=defaultdict(int)
        for f in ast.walk(t):
            if not isinstance(f,ast.FunctionDef) or f.name not in CR: continue
            for n in ast.walk(f):
                if isinstance(n,ast.Attribute) and isinstance(n.ctx,ast.Load) and n.attr=="name": c[f.name]+=1
        assert c["_check_collection_rules_global"]==1; assert c["_materialize_bpy_data_collections"]==1; assert c.get("_compute_ancestor_closure",0)==0


class TestFalsePositive:
    def test_color(self): assert analyze_source("def f():\n    color.children\n")==[]
    def test_collision(self): assert analyze_source("def f():\n    collision_obj.children\n")==[]
    def test_obj(self): assert analyze_source("def f():\n    obj.children\n")==[]
    def test_ordinary_for(self): assert analyze_source("def f():\n    for x in [1,2,3]:\n        x.children\n")==[]
    def test_ordinary_c(self): assert analyze_source("def f():\n    items=[1,2,3]\n    for c in items:\n        c.children\n")==[]
    def test_ordinary_col(self): assert analyze_source("def f():\n    objs=[1,2,3]\n    for col in objs:\n        col.children\n")==[]
    def test_cfg_children(self): assert analyze_source("def f(cfg):\n    cfg.children=[]\n")==[]
    def test_cfg_collections(self): assert analyze_source("def f(cfg):\n    cfg.collections=[]\n")==[]
    def test_getattr_cfg(self): assert analyze_source('def f(cfg):\n    getattr(cfg,"name")\n')==[]
    def test_getattr_alias_cfg(self): assert analyze_source('def f(cfg):\n    ga=getattr;ga(cfg,"children")\n')==[]
    def test_obj_name(self): assert analyze_source("def f(obj):\n    obj.name\n")==[]
    def test_action_name(self): assert analyze_source("def f(action):\n    action.name\n")==[]
    def test_scene(self): assert analyze_source("def f(scene):\n    scene.objects\n")==[]


class TestViolations:
    def test_unauth_bpy(self): assert any("UNAUTHORIZED_READ:_evil:bpy.data.collections" in x for x in analyze_source("def _evil():\n    bpy.data.collections\n"))
    def test_unauth_users(self): assert any("UNAUTHORIZED_READ:_evil:users_collection" in x for x in analyze_source("def _evil(root_obj):\n    root_obj.users_collection\n"))
    def test_unauth_ch(self):
        v=analyze_source("def _evil():\n    colls=list(bpy.data.collections)\n    for c in colls:\n        c.children\n")
        assert any("_evil" in x and "children" in x for x in v)
    def test_dc_name(self): assert any("dc.name" in x for x in analyze_source("def _compute_ancestor_closure(dc,po,cbi,nbi):\n    dc.name\n"))
    def test_parent_col_name(self): assert any("parent_col.name" in x for x in analyze_source("def _compute_ancestor_closure(dc,po,cbi,nbi):\n    parent_col=None\n    parent_col.name\n"))
    def test_write_users(self): assert any("WRITE_PROTECTED:_evil:users_collection" in x for x in analyze_source("def _evil(root_obj):\n    root_obj.users_collection=[]\n"))
    def test_augassign_users(self): assert any("WRITE_PROTECTED:_evil:users_collection" in x for x in analyze_source("def _evil(root_obj):\n    root_obj.users_collection+=[]\n"))
    def test_del_users(self): assert any("WRITE_PROTECTED:_evil:users_collection" in x for x in analyze_source("def _evil(root_obj):\n    del root_obj.users_collection\n"))
    def test_getattr_users(self): assert any("DYNAMIC_ACCESS:_evil:getattr:users_collection" in x for x in analyze_source('def _evil(root_obj):\n    getattr(root_obj,"users_collection")\n'))
    def test_setattr_users(self): assert any("WRITE_PROTECTED:_evil:setattr:users_collection" in x for x in analyze_source('def _evil(root_obj):\n    setattr(root_obj,"users_collection",[])\n'))
    def test_extra_bpy(self): assert any("EXTRA_AUTHORIZED_READ:_check_collection_rules_global:bpy.data.collections" in x for x in analyze_source("def _check_collection_rules_global(block):\n    bpy.data.collections\n    bpy.data.collections\n"))
    def test_extra_users(self): assert any("EXTRA_AUTHORIZED_READ:_check_collection_membership:users_collection" in x for x in analyze_source("def _check_collection_membership(s,t,p):\n    root_obj=None\n    root_obj.users_collection\n    root_obj.users_collection\n"))
    def test_alias_users(self): assert any("UNAUTHORIZED_ALIAS_READ:_check_collection_membership:users_collection" in x for x in analyze_source("def _check_collection_membership(s,t,p):\n    root_obj=None\n    alias=root_obj\n    alias.users_collection\n"))
    def test_nested_users(self): assert any("<locals>" in x and "users_collection" in x for x in analyze_source("def _check_collection_membership(s,t,p):\n    root_obj=None\n    def _h():\n        return root_obj.users_collection\n    _h()\n"))
    def test_lambda_users(self): assert any("<lambda>" in x and "users_collection" in x for x in analyze_source("def _check_collection_membership(s,t,p):\n    root_obj=None\n    f=lambda:root_obj.users_collection\n    f()\n"))
    def test_getattr_alias(self): assert any("DYNAMIC_ACCESS:_evil:getattr:users_collection" in x for x in analyze_source('def _evil(root_obj):\n    ga=getattr;ga(root_obj,"users_collection")\n'))
    def test_setattr_alias_children(self): assert any("WRITE_PROTECTED:_evil:setattr:children" in x for x in analyze_source("def _evil():\n    colls=list(bpy.data.collections)\n    for c in colls:\n        sa=setattr;sa(c,'children',[])\n"))
    def test_comp_name(self): assert any("collection.name" in x for x in analyze_source("def _evil():\n    colls=list(bpy.data.collections)\n    [c.name for c in colls]\n"))
    def test_coll_children_write(self): assert any("WRITE_PROTECTED:_evil:collection.children" in x for x in analyze_source("def _evil():\n    colls=list(bpy.data.collections)\n    for c in colls:\n        c.children=[]\n"))
    def test_coll_children_del(self): assert any("WRITE_PROTECTED:_evil:collection.children" in x for x in analyze_source("def _evil():\n    colls=list(bpy.data.collections)\n    for c in colls:\n        del c.children\n"))
    def test_helper_param(self): assert any("_h" in x and "children" in x for x in analyze_source("def _h(val):\n    val.children\ndef _evil():\n    colls=list(bpy.data.collections)\n    for c in colls:\n        _h(c)\n"))
    def test_helper_ordinary_clean(self): assert analyze_source("def _h(val):\n    val.children\ndef _evil():\n    items=[1,2,3]\n    for x in items:\n        _h(x)\n")==[]
    def test_two_level(self): assert any("_hb" in x and "children" in x for x in analyze_source("def _hb(val):\n    val.children\ndef _ha(val):\n    _hb(val)\ndef _evil():\n    colls=list(bpy.data.collections)\n    for c in colls:\n        _ha(c)\n"))
    def test_return_identity(self): assert any("_evil" in x and "children" in x for x in analyze_source("def _id(v):\n    return v\ndef _evil():\n    colls=list(bpy.data.collections)\n    for c in colls:\n        r=_id(c)\n        r.children\n"))
    def test_deep_scan(self):
        src="def _evil():\n    colls=list(bpy.data.collections)\n    if True:\n        for c in colls:\n            pass\n            c.children\n"
        assert any("_evil" in x and "children" in x for x in analyze_source(src))
    def test_deep_nested(self):
        src="def _check_collection_membership(s,t,p):\n    root_obj=None\n    if True:\n        def _h():\n            return root_obj.users_collection\n        _h()\n"
        assert any("<locals>" in x and "users_collection" in x for x in analyze_source(src))
    def test_bpy_alias_return(self): assert any("_evil" in x and "collections" in x for x in analyze_source("def _gd():\n    return bpy.data\ndef _evil():\n    d=_gd()\n    d.collections\n"))
    def test_genexp_children(self): assert any("_evil" in x and "children" in x for x in analyze_source("def _evil():\n    colls=list(bpy.data.collections)\n    tuple(c.children for c in colls)\n"))
    def test_ordinary_comp_clean(self):
        assert analyze_source("def f():\n    items=[1,2,3]\n    [x.name for x in items]\n")==[]
        assert analyze_source("def f():\n    items=[1,2,3]\n    tuple(x.children for x in items)\n")==[]
    # ── supplementary probes ──
    def test_nested_helper_collection_param(self):
        src=textwrap.dedent("""\
        def _evil():
            def _h(v):
                v.children
            colls=list(bpy.data.collections)
            for c in colls:
                _h(c)
        """)
        assert any("<locals>" in x and "children" in x for x in analyze_source(src))
    def test_nested_helper_ordinary_clean(self):
        assert analyze_source("def f():\n    def _h(v):\n        v.children\n    for v in [1,2,3]:\n        _h(v)\n")==[]
    def test_lambda_collection_param(self):
        src="def _evil():\n    colls=list(bpy.data.collections)\n    for c in colls:\n        r=lambda v:v.children\n        r(c)\n"
        assert any("<lambda>" in x and "children" in x for x in analyze_source(src))
    def test_lambda_ordinary_clean(self):
        assert analyze_source("def f():\n    for v in [1,2,3]:\n        r=lambda v:v.children\n        r(v)\n")==[]
    def test_two_level_return_param(self):
        src=textwrap.dedent("""\
        def _hb(v):
            return v
        def _ha(v):
            return _hb(v)
        def _evil():
            colls=list(bpy.data.collections)
            for c in colls:
                r=_ha(c)
                r.children
        """)
        assert any("_evil" in x and "children" in x for x in analyze_source(src))
    def test_two_level_return_ordinary_clean(self):
        src=textwrap.dedent("""\
        def _hb(v):
            return v
        def _ha(v):
            return _hb(v)
        def _evil():
            r=_ha(None)
            r.children
        """)
        assert analyze_source(src)==[]
    def test_auth_bpy_data_alias_forbidden(self):
        src="def _check_collection_rules_global(block):\n    d=bpy.data\n    list(d.collections)\n"
        assert any("UNAUTHORIZED_ALIAS_READ:_check_collection_rules_global:bpy.data.collections" in x for x in analyze_source(src))
    def test_root_obj_dynamic_no_env(self):
        v=analyze_source('def _check_collection_membership(s,t,p):\n    root_obj=None\n    getattr(root_obj,"users_collection")\n')
        assert any("DYNAMIC_ACCESS" in x and "users_collection" in x for x in v)


class TestMutations:
    def test_m1_unauth(self):
        v=analyze_source(_REAL+"\ndef _evil():\n    import bpy\n    bpy.data.collections\n")
        assert any("UNAUTHORIZED_READ:_evil:bpy.data.collections" in x for x in v)
    def test_m2_alias_users(self):
        assert "direct_colls = list(root_obj.users_collection)" in _REAL
        m=_REAL.replace("direct_colls = list(root_obj.users_collection)","alias = root_obj\n        direct_colls = list(alias.users_collection)")
        assert m!=_REAL;ast.parse(m)
        assert any("UNAUTHORIZED_ALIAS_READ" in x and "users_collection" in x for x in analyze_source(m))
    def test_m3_dc_name(self):
        assert "direct_name = name_by_id[did]" in _REAL
        m=_REAL.replace("direct_name = name_by_id[did]","direct_name = dc.name")
        assert m!=_REAL;ast.parse(m)
        assert any("dc.name" in x for x in analyze_source(m))
    def test_m4_parent_col_name(self):
        assert "pname = name_by_id[pid]" in _REAL
        m=_REAL.replace("pname = name_by_id[pid]","pname = parent_col.name")
        assert m!=_REAL;ast.parse(m)
        assert any("parent_col.name" in x for x in analyze_source(m))
    def test_m5_closure_children(self):
        assert "pids = parent_of.get(cid, [])" in _REAL
        m=_REAL.replace("pids = parent_of.get(cid, [])","pids = parent_of.get(cid, []); dc.children")
        assert m!=_REAL;ast.parse(m)
        assert any("_compute_ancestor_closure" in x and "children" in x for x in analyze_source(m))
    def test_m6_extra_bpy(self):
        assert "all_collections = list(bpy.data.collections)" in _REAL
        m=_REAL.replace("all_collections = list(bpy.data.collections)","all_collections = list(bpy.data.collections); bpy.data.collections")
        assert m!=_REAL;ast.parse(m)
        assert any("EXTRA_AUTHORIZED_READ:_check_collection_rules_global:bpy.data.collections" in x for x in analyze_source(m))
    def test_m7_nested_users(self):
        assert "direct_colls = list(root_obj.users_collection)" in _REAL
        m=_REAL.replace("direct_colls = list(root_obj.users_collection)","def _h():\n            return root_obj.users_collection\n        direct_colls = list(_h())")
        assert m!=_REAL;ast.parse(m)
        assert any("<locals>" in x and "users_collection" in x for x in analyze_source(m))
    def test_m8_getattr(self):
        assert 'root_obj.users_collection' in _REAL
        m=_REAL.replace('root_obj.users_collection','getattr(root_obj, "users_collection")')
        assert m!=_REAL
        v=analyze_source(m)
        assert any("DYNAMIC_ACCESS" in x and "users_collection" in x for x in v), f"M8 violations: {v}"
    def test_m9_data_alias(self):
        assert "all_collections = list(bpy.data.collections)" in _REAL
        m=_REAL.replace("all_collections = list(bpy.data.collections)","d = bpy.data; all_collections = list(d.collections)")
        assert m!=_REAL
        v=analyze_source(m)
        assert any("UNAUTHORIZED_ALIAS_READ" in x for x in v), f"M9 violations: {v}"
    def test_m10_extra_children(self):
        assert "children = list(col.children)" in _REAL
        m=_REAL.replace("children = list(col.children)","children = list(col.children); col.children")
        assert m!=_REAL;ast.parse(m)
        assert any("_materialize_collection_ancestor_index" in x and "children" in x for x in analyze_source(m))


def test_vacuous_self_check():
    with open(__file__, encoding="utf-8") as f: src=f.read()
    tree=ast.parse(src)
    issues=[]; seen=set()
    for node in ast.walk(tree):
        if isinstance(node,ast.FunctionDef) and node.name.startswith("test_"):
            if node.name in seen: issues.append(f"DUP:{node.name}")
            seen.add(node.name)
            has_assert=any(isinstance(n,ast.Assert) for n in ast.walk(node))
            has_pass_only=len(node.body)==1 and isinstance(node.body[0],ast.Pass)
            if not has_assert: issues.append(f"NO_ASSERT:{node.name}")
            if has_pass_only: issues.append(f"PASS_ONLY:{node.name}")
    assert issues==[],f"Vacuous:{issues}"
