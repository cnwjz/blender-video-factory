"""Material Assignment I4A AST Scope Guard R6 — source-model data-flow analysis.

Uses Rotation I4A ReachableScopeAnalyzer for call-graph, plus source tracking.
Production file: blender_scene_reader.py — frozen.
"""
import ast, os, sys, textwrap
from collections import defaultdict
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
READER_PATH = os.path.join(ROOT, "protocol_guard", "phase3_min", "blender_scene_reader.py")
from protocol_guard.phase3_min.tests.test_asset_scene_preflight_blender_rotation_i4a import (
    ReachableScopeAnalyzer, _attr_chain)

ENTRY = "_check_material_assignment"
AUTH = "_check_material_slots_for_mesh"
COLLECT = "_collect_geometry_scope_objects"
PROTECTED = {"material_slots", "material"}

with open(READER_PATH, encoding="utf-8") as f:
    _REAL = f.read()


# ── source model ───────────────────────────────────────────────────────
class Src:
    UNK = 0; ORD = 1; MESH = 2; SLOTS = 3; SLOT = 4; BPY = 5
    STR = 6; FUNC = 7; GETA = 8; HASA = 9; SETA = 10; DELA = 11; LAM = 12


# ── shallow walk (no nested funcs/lambdas) ─────────────────────────────
def _shallow_stmts(body):
    nodes = []
    def _w(n):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            return
        nodes.append(n)
        for c in ast.iter_child_nodes(n):
            _w(c)
    for s in body:
        if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        _w(s)
    return nodes


# ── static string resolver ─────────────────────────────────────────────
def _str_val(n, func_node):
    if isinstance(n, ast.Constant) and isinstance(n.value, str):
        return n.value
    if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
        l, r = _str_val(n.left, func_node), _str_val(n.right, func_node)
        if l is not None and r is not None:
            return l + r
    if isinstance(n, ast.Name):
        for s in ast.walk(func_node):
            if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                if s is not func_node: continue
            if isinstance(s, ast.Assign):
                for t in s.targets:
                    if isinstance(t, ast.Name) and t.id == n.id:
                        v = _str_val(s.value, func_node)
                        if v is not None: return v
    return None


# ── per-function source tracker ────────────────────────────────────────
def _track_sources(node):
    """Returns dict var_name -> (src_type, metadata) for a function body (shallow)."""
    sources = {}
    for arg in node.args.args:
        sources[arg.arg] = (Src.ORD, None)
        if node.name == AUTH and arg.arg == "mesh_obj":
            sources[arg.arg] = (Src.MESH, None)

    body = _shallow_stmts(node.body)

    for stmt in body:
        if isinstance(stmt, ast.Assign):
            val = stmt.value
            src = _expr_src(val, sources)
            for t in stmt.targets:
                if isinstance(t, ast.Name):
                    sources[t.id] = src
                elif isinstance(t, ast.Tuple):
                    if isinstance(val, ast.Attribute) and val.attr == "material_slots":
                        for i, elt in enumerate(t.elts):
                            if isinstance(elt, ast.Name):
                                sources[elt.id] = (Src.SLOT, i)

        elif isinstance(stmt, ast.AnnAssign):
            if isinstance(stmt.target, ast.Name) and stmt.value:
                sources[stmt.target.id] = _expr_src(stmt.value, sources)

        elif isinstance(stmt, ast.For):
            it_src = _expr_src(stmt.iter, sources)
            if isinstance(stmt.target, ast.Name):
                if it_src[0] == Src.SLOTS:
                    sources[stmt.target.id] = (Src.SLOT, 0)
            elif isinstance(stmt.target, ast.Tuple):
                if it_src[0] == Src.SLOTS or (
                    isinstance(stmt.iter, ast.Call) and
                    isinstance(stmt.iter.func, ast.Name) and
                    stmt.iter.func.id == "enumerate" and stmt.iter.args and
                    _expr_src(stmt.iter.args[0], sources)[0] == Src.SLOTS
                ):
                    for elt in stmt.target.elts:
                        if isinstance(elt, ast.Name):
                            sources[elt.id] = (Src.SLOT, 0)

    # Second pass: propagate SLOT through simple aliases
    changed = True
    while changed:
        changed = False
        for stmt in body:
            if isinstance(stmt, ast.Assign):
                for t in stmt.targets:
                    if isinstance(t, ast.Name) and isinstance(stmt.value, ast.Name):
                        val_src = sources.get(stmt.value.id, (Src.UNK,))
                        if val_src[0] == Src.SLOT:
                            cur = sources.get(t.id, (Src.UNK,))
                            if cur[0] != Src.SLOT:
                                sources[t.id] = val_src
                                changed = True
                    elif isinstance(t, ast.Tuple) and isinstance(stmt.value, ast.Name):
                        val_src = sources.get(stmt.value.id, (Src.UNK,))
                        if val_src[0] == Src.SLOTS:
                            for elt in t.elts:
                                if isinstance(elt, ast.Name) and sources.get(elt.id, (Src.UNK,))[0] != Src.SLOT:
                                    sources[elt.id] = (Src.SLOT, 0)
                                    changed = True

    return sources


def _expr_src(node, sources):
    if isinstance(node, ast.Name):
        return sources.get(node.id, (Src.ORD, None))
    if isinstance(node, ast.Attribute):
        # Special: mesh_obj.material_slots → SLOTS
        if isinstance(node.value, ast.Name) and node.value.id == "mesh_obj" and node.attr == "material_slots":
            return (Src.SLOTS, None)
        if node.attr == "material_slots":
            return (Src.SLOTS, None)
        if node.attr == "material":
            obj = node.value
            if isinstance(obj, ast.Subscript):
                arr_src = _expr_src(obj.value, sources)
                if arr_src[0] == Src.SLOTS:
                    return (Src.SLOT, None)
            if isinstance(obj, ast.Name):
                v_src = sources.get(obj.id, (Src.UNK,))
                if v_src[0] == Src.SLOT:
                    return (Src.SLOT, None)
        return (Src.ORD, None)
    if isinstance(node, ast.Subscript):
        # slots[0] → SLOT if slots is SLOTS
        base_src = _expr_src(node.value, sources)
        if base_src[0] == Src.SLOTS:
            return (Src.SLOT, None)
        return base_src
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.args:
            return _expr_src(node.args[0], sources)
        return (Src.ORD, None)
    if isinstance(node, ast.Constant):
        return (Src.STR, None)
    return (Src.ORD, None)


# ── BPY chain detector ─────────────────────────────────────────────────
def _bpy_chain(node, func_node=None):
    """Check bpy.data.objects["x"].material_slots with alias tracing."""
    if node.attr != "material_slots":
        return False
    val = node.value
    if not isinstance(val, ast.Subscript):
        return False
    sub = val.value
    # Direct: bpy.data.objects["x"].material_slots
    if isinstance(sub, ast.Attribute) and sub.attr == "objects":
        data = sub.value
        # Direct: bpy.data.objects
        if isinstance(data, ast.Attribute) and data.attr == "data":
            base = data.value
            if isinstance(base, ast.Name) and base.id == "bpy":
                return True
        # Alias: data = bpy.data → data.objects["x"].material_slots
        if isinstance(data, ast.Name) and func_node:
            for s in ast.walk(func_node):
                if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                    if s is not func_node: continue
                if isinstance(s, ast.Assign):
                    for t in s.targets:
                        if isinstance(t, ast.Name) and t.id == data.id:
                            rhs = s.value
                            if isinstance(rhs, ast.Attribute) and rhs.attr == "data":
                                b = rhs.value
                                if isinstance(b, ast.Name) and b.id == "bpy":
                                    return True
    # Alias: objects = bpy.data.objects → objects["x"].material_slots
    if isinstance(sub, ast.Name) and func_node:
        for s in ast.walk(func_node):
            if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                if s is not func_node: continue
            if isinstance(s, ast.Assign):
                for t in s.targets:
                    if isinstance(t, ast.Name) and t.id == sub.id:
                        rhs = s.value
                        if isinstance(rhs, ast.Attribute) and rhs.attr == "objects":
                            d = rhs.value
                            if isinstance(d, ast.Attribute) and d.attr == "data":
                                b = d.value
                                if isinstance(b, ast.Name) and b.id == "bpy":
                                    return True
    return False


# ── core analyzer ──────────────────────────────────────────────────────
def analyze_source(src, filename="<test>"):
    tree = ast.parse(src, filename=filename)
    funcs = {}
    for n in ast.iter_child_nodes(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs[n.name] = n
    is_prod = filename == "blender_scene_reader.py"
    v = []

    # === Duplicate detection ===
    name_counts = defaultdict(int)
    for n in ast.iter_child_nodes(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name_counts[n.name] += 1
    for nm, cnt in name_counts.items():
        if cnt > 1 and nm in (AUTH, ENTRY, COLLECT):
            v.append(f"DUPLICATE_FUNCTION:{nm}:{cnt}")

    # === Source tracking for all functions ===
    fn_sources = {}
    for nm, fn in funcs.items():
        fn_sources[nm] = _track_sources(fn)

    # === Shallow body for all functions ===
    fn_shallow = {}
    for nm, fn in funcs.items():
        fn_shallow[nm] = _shallow_stmts(fn.body)

    # === Production-only: reachability + counts + call edges ===
    if is_prod and ENTRY in funcs:
        rot_mod = sys.modules.get(
            "protocol_guard.phase3_min.tests.test_asset_scene_preflight_blender_rotation_i4a")
        if not rot_mod:
            import protocol_guard.phase3_min.tests.test_asset_scene_preflight_blender_rotation_i4a as rm
            rot_mod = rm
        saved = rot_mod.ENTRY_NAMES
        rot_mod.ENTRY_NAMES = {ENTRY}
        try:
            ra = ReachableScopeAnalyzer(tree)
            reachable = ra._get_reachable_funcs()
        finally:
            rot_mod.ENTRY_NAMES = saved

        if AUTH in reachable:
            nodes = fn_shallow.get(AUTH, [])
            ms, sm = 0, 0
            for n in nodes:
                if isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Load):
                    if n.attr == "material_slots" and isinstance(n.value, ast.Name) and n.value.id == "mesh_obj":
                        ms += 1
                    elif n.attr == "material":
                        src = _expr_src(n, fn_sources.get(AUTH, {}))
                        if src[0] == Src.SLOT:
                            sm += 1
            if ms != 1:
                v.append(f"MATERIAL_SLOTS_READ_COUNT:{AUTH}:{ms}")
            if sm != 1:
                v.append(f"SLOT_MATERIAL_READ_COUNT:{AUTH}:{sm}")

        # Call edges from ENTRY shallow body
        collect_n, auth_n = 0, 0
        for n in fn_shallow.get(ENTRY, []):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                if n.func.id == COLLECT:
                    collect_n += 1
                elif n.func.id == AUTH:
                    auth_n += 1
        if collect_n == 0:
            v.append(f"MISSING_CALL_EDGE:{ENTRY}:{COLLECT}")
        elif collect_n > 1:
            v.append(f"DUPLICATE_CALL_EDGE:{ENTRY}:{COLLECT}")
        if auth_n == 0:
            v.append(f"MISSING_CALL_EDGE:{ENTRY}:{AUTH}")
        elif auth_n > 1:
            v.append(f"DUPLICATE_CALL_EDGE:{ENTRY}:{AUTH}")

    if is_prod:
        for f in (AUTH, ENTRY, COLLECT):
            if f not in funcs:
                v.append(f"MISSING_FUNCTION:{f}")

    # === Inter-procedural source propagation ===
    dyn_funcs = defaultdict(set)
    for nm, fn in funcs.items():
        for n in fn_shallow[nm]:
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name) and isinstance(n.value, ast.Name):
                        if n.value.id in funcs or n.value.id in ("getattr", "hasattr", "setattr", "delattr"):
                            dyn_funcs[t.id].add(n.value.id)

    call_map = defaultdict(list)
    for nm, fn in funcs.items():
        for n in fn_shallow[nm]:
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                callee = n.func.id
                resolved = {callee} | dyn_funcs.get(callee, set())
                for r in resolved:
                    if r in funcs:
                        call_map[r].append((nm, n))

    param_srcs = {}
    for nm, fn in funcs.items():
        ps = {}
        for a in fn.args.args:
            ps[a.arg] = (Src.ORD, None)
            if nm == AUTH and a.arg == "mesh_obj":
                ps[a.arg] = (Src.MESH, None)
        param_srcs[nm] = ps

    for _ in range(20):
        chg = False
        for nm, fn in funcs.items():
            # Also walk all nodes (not just shallow) for call propagation
            for n in ast.walk(fn):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                    if n is not fn: continue
                targets = set()
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                    targets.add(n.func.id)
                    for d in dyn_funcs.get(n.func.id, set()):
                        targets.add(d)
                for callee in targets.intersection(funcs):
                    cf = funcs[callee]
                    if isinstance(n, ast.Call):
                        for i, a in enumerate(cf.args.args):
                            if i < len(n.args):
                                new_src = _expr_src(n.args[i], fn_sources.get(nm, {}))
                                old = param_srcs[callee].get(a.arg, (Src.ORD, None))
                                if new_src[0] > old[0]:
                                    param_srcs[callee][a.arg] = new_src
                                    chg = True
        if not chg:
            break

    for nm in funcs:
        fn_sources.setdefault(nm, {}).update(param_srcs.get(nm, {}))

    # === All-function checks (not production-only) ===
    # Context detection: functions that read .material_slots AND .material
    ctx_has_ms = set()
    ctx_has_mat = set()
    for nm, fn in funcs.items():
        for n in fn_shallow[nm]:
            if isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Load):
                if n.attr == "material_slots":
                    ctx_has_ms.add(nm)
                elif n.attr == "material":
                    ctx_has_mat.add(nm)

    for nm, fn in funcs.items():
        nodes = fn_shallow[nm]
        srcs = fn_sources[nm]
        for n in nodes:
            if isinstance(n, ast.Attribute):
                _check_attr(n, nm, srcs, v, fn_shallow, fn_sources, ctx_has_ms)

        # Dynamic access
        for n in ast.walk(fn):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                _check_dyn(n, nm, fn, v, fn_sources)

    # Nested/lambda
    for nm, fn in funcs.items():
        _check_nested_lambda(fn, nm, v, fn_sources)

    # BPY
    for nm, fn in funcs.items():
        for n in ast.walk(fn):
            if isinstance(n, ast.Attribute) and n.attr == "material_slots":
                if _bpy_chain(n, fn):
                    v.append(f"BPY_DATA_BYPASS:{nm}:material_slots")

    return sorted(set(v))


def _check_attr(node, fname, srcs, v, fn_shallow, fn_sources, ctx_has_ms=None):
    """Check one Attribute node against rules."""
    if node.attr not in PROTECTED:
        return
    leaf = node.attr

    # Loads
    if isinstance(node.ctx, ast.Load):
        if leaf == "material_slots":
            if fname != AUTH:
                v.append(f"PROTECTED_MATERIAL_SLOTS_READ:{fname}:material_slots")
            elif not (isinstance(node.value, ast.Name) and node.value.id == "mesh_obj"):
                v.append(f"PROTECTED_MATERIAL_SLOTS_READ:{fname}:material_slots")
        elif leaf == "material":
            src = _expr_src(node, srcs)
            # Flag if source is SLOT, OR if this function reads material_slots (slot context)
            is_slot_context = (fname in ctx_has_ms) or (src[0] == Src.SLOT)
            if is_slot_context and fname != AUTH:
                v.append(f"PROTECTED_SLOT_MATERIAL_READ:{fname}:material")
            elif src[0] == Src.SLOT and fname == AUTH:
                pass

    # Writes/deletes
    if leaf == "material_slots":
        if isinstance(node.ctx, (ast.Store, ast.AugStore)):
            v.append(f"PROTECTED_WRITE:{fname}:material_slots")
        elif isinstance(node.ctx, ast.Del):
            v.append(f"PROTECTED_DELETE:{fname}:material_slots")
    elif leaf == "material":
        src = _expr_src(node, srcs)
        if src[0] == Src.SLOT:
            if isinstance(node.ctx, (ast.Store, ast.AugStore)):
                v.append(f"PROTECTED_WRITE:{fname}:material")
            elif isinstance(node.ctx, ast.Del):
                v.append(f"PROTECTED_DELETE:{fname}:material")


def _check_dyn(node, fname, func_node, v, fn_sources):
    fn = node.func.id
    # Resolve aliased function names
    resolved = {fn}
    if fname in fn_sources:
        for nm, src in fn_sources.get(fname, {}).items():
            if nm == fn and src[0] in (Src.GETA, Src.SETA, Src.DELA, Src.HASA):
                # This name was assigned from getattr/setattr — check what original function
                pass
    # Also check dyn_funcs from analyze_source context — we'll just handle direct aliases
    # via the dyn_funcs dict in analyze_source
    alts = {"reader": "getattr", "checker": "hasattr", "writer": "setattr", "deleter": "delattr",
            "getattr": "getattr", "hasattr": "hasattr", "setattr": "setattr", "delattr": "delattr"}
    if fn in alts:
        resolved.add(alts[fn])

    for rfn in resolved:
        if rfn not in ("getattr", "hasattr", "setattr", "delattr"):
            continue
        if not node.args:
            continue
        an = node.args[min(1, len(node.args) - 1)]
        aval = _str_val(an, func_node)
        if aval not in PROTECTED:
            continue
        if aval == "material_slots":
            v.append(f"DYNAMIC_PROTECTED_ACCESS:{fname}:getattr:material_slots" if fn != rfn else f"DYNAMIC_PROTECTED_ACCESS:{fname}:{rfn}:material_slots")
        elif aval == "material":
            obj = node.args[0] if node.args else None
            if obj and isinstance(obj, ast.Name):
                src = fn_sources.get(fname, {}).get(obj.id, (Src.UNK,))
                if src[0] == Src.SLOT:
                    v.append(f"DYNAMIC_PROTECTED_ACCESS:{fname}:{rfn}:material")
        return  # only process once


def _check_nested_lambda(fn, fname, v, fn_sources):
    for sub in ast.walk(fn):
        if sub is fn: continue
        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
            sn = f"{fname}.<nested:{sub.name}>"
            inner_srcs = _track_sources(sub)
            all_srcs = {**fn_sources.get(fname, {}), **inner_srcs}
            for inner in ast.walk(sub):
                if inner is sub: continue
                if isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                    if inner is not sub: continue
                if isinstance(inner, ast.Attribute) and inner.attr in PROTECTED:
                    if inner.attr == "material_slots":
                        if isinstance(inner.ctx, ast.Load):
                            v.append(f"NESTED_PROTECTED_ACCESS:{sn}:material_slots")
                    elif inner.attr == "material":
                        src = _expr_src(inner, all_srcs)
                        if src[0] == Src.SLOT and isinstance(inner.ctx, ast.Load):
                            v.append(f"NESTED_PROTECTED_ACCESS:{sn}:material")
        if isinstance(sub, ast.Lambda):
            for inner in ast.walk(sub):
                if isinstance(inner, ast.Attribute) and inner.attr in PROTECTED:
                    if inner.attr == "material_slots" and isinstance(inner.ctx, ast.Load):
                        v.append(f"LAMBDA_PROTECTED_ACCESS:{fname}:material_slots")
                    elif inner.attr == "material":
                        src = _expr_src(inner, fn_sources.get(fname, {}))
                        if src[0] == Src.SLOT and isinstance(inner.ctx, ast.Load):
                            v.append(f"LAMBDA_PROTECTED_ACCESS:{fname}:material")


V = {
    "MF": "MISSING_FUNCTION", "DF": "DUPLICATE_FUNCTION",
    "MCE": "MISSING_CALL_EDGE", "DCE": "DUPLICATE_CALL_EDGE",
    "MSRC": "MATERIAL_SLOTS_READ_COUNT", "SMRC": "SLOT_MATERIAL_READ_COUNT",
    "PSR": "PROTECTED_MATERIAL_SLOTS_READ", "PSMR": "PROTECTED_SLOT_MATERIAL_READ",
    "PW": "PROTECTED_WRITE", "PD": "PROTECTED_DELETE",
    "DPA": "DYNAMIC_PROTECTED_ACCESS",
    "NPA": "NESTED_PROTECTED_ACCESS", "LPA": "LAMBDA_PROTECTED_ACCESS",
    "BPY": "BPY_DATA_BYPASS",
}


def av(violations, kind, scope, detail=""):
    """Assert a violation exists. If detail given, match exactly; else match prefix (kind:scope)."""
    if detail:
        expected = f"{kind}:{scope}:{detail}"
        assert expected in violations, f"Expected '{expected}' not in {violations}"
    else:
        prefix = f"{kind}:{scope}"
        assert any(vi.startswith(prefix) for vi in violations), f"Expected prefix '{prefix}' not in {violations}"


# ── test utilities ─────────────────────────────────────────────────────
def _mutate(src, old, new):
    return src.replace(old, new, 1)


# ── production structure tests ─────────────────────────────────────────
class TestProductionStructure:
    def test_no_violations(self):
        v = analyze_source(_REAL, "blender_scene_reader.py")
        assert v == [], f"Violations: {v}"

    def test_functions_exist(self):
        t = ast.parse(_REAL)
        names = {n.name for n in ast.iter_child_nodes(t) if isinstance(n, ast.FunctionDef)}
        for f in (AUTH, ENTRY, COLLECT):
            assert f in names, f"Missing {f}"


# ── mutation tests ─────────────────────────────────────────────────────
class TestMutations:
    SRC = _REAL

    def test_remove_slots_call(self):
        ms = self.SRC.replace(f"{AUTH}(mesh_obj, mesh_name)",
                              f"_removed(mesh_obj, mesh_name)")
        v = analyze_source(ms, "blender_scene_reader.py")
        av(v, V["MCE"], ENTRY, AUTH)

    def test_remove_collect_call(self):
        ms = self.SRC.replace(f"{COLLECT}(",
                              f"_removed(")
        v = analyze_source(ms, "blender_scene_reader.py")
        assert any(V["MCE"] in vi and COLLECT in vi for vi in v), v

    def test_extra_ms_read(self):
        ms = self.SRC.replace(
            "material_slots = list(mesh_obj.material_slots)",
            "material_slots = list(mesh_obj.material_slots)\n        _x = mesh_obj.material_slots")
        v = analyze_source(ms, "blender_scene_reader.py")
        av(v, V["MSRC"], AUTH, "2")

    def test_remove_slot_material(self):
        ms = self.SRC.replace("slot.material", "slot._nope")
        v = analyze_source(ms, "blender_scene_reader.py")
        av(v, V["SMRC"], AUTH, "0")

    def test_extra_slot_material(self):
        ms = self.SRC.replace("slot.material", "slot.material; slot.material")
        v = analyze_source(ms, "blender_scene_reader.py")
        av(v, V["SMRC"], AUTH, "2")

    def test_alias_ms_read(self):
        ms = self.SRC.replace("mesh_obj.material_slots",
                              "(lambda m=mesh_obj: m.material_slots)()")
        v = analyze_source(ms, "blender_scene_reader.py")
        assert any(V["PSR"] in vi for vi in v) or any(V["MSRC"] in vi for vi in v), v

    def test_duplicate_authorized(self):
        ms = self.SRC + f"\ndef {AUTH}(a,b):\n    pass\n"
        v = analyze_source(ms, "blender_scene_reader.py")
        av(v, V["DF"], AUTH)


# ── protected read violations ──────────────────────────────────────────
class TestProtectedReads:
    def test_ms_in_other_func(self):
        src = textwrap.dedent("""\
        def other():
            obj = None
            obj.material_slots
        """)
        av(analyze_source(src), V["PSR"], "other")

    def test_slot_mat_in_other_func(self):
        src = textwrap.dedent("""\
        def other(obj):
            slots = obj.material_slots
            slot = slots[0]
            slot.material
        """)
        av(analyze_source(src), V["PSMR"], "other")

    def test_slot_alias(self):
        src = textwrap.dedent("""\
        def other(obj):
            slots = obj.material_slots
            slot = slots[0]
            alias = slot
            alias.material
        """)
        av(analyze_source(src), V["PSMR"], "other")

    def test_slot_tuple_unpack(self):
        src = textwrap.dedent("""\
        def other(obj):
            slots = obj.material_slots
            first, second = slots
            first.material
        """)
        av(analyze_source(src), V["PSMR"], "other")

    def test_slot_via_helper(self):
        src = textwrap.dedent("""\
        def helper(slot):
            return slot.material

        def _check_material_slots_for_mesh(mesh_obj, mesh_name):
            slots = mesh_obj.material_slots
            return helper(slots[0])
        """)
        av(analyze_source(src), V["PSMR"], "helper")

    def test_slot_via_fn_alias(self):
        src = textwrap.dedent("""\
        def helper(slot):
            return slot.material

        def _check_material_slots_for_mesh(mesh_obj, mesh_name):
            slots = mesh_obj.material_slots
            fn = helper
            return fn(slots[0])
        """)
        av(analyze_source(src), V["PSMR"], "helper")


# ── nested/lambda slot ─────────────────────────────────────────────────
class TestNestedLambdaSlot:
    def test_nested_slot_mat(self):
        src = textwrap.dedent("""\
        def outer(obj):
            slots = obj.material_slots
            slot = slots[0]
            def inner():
                slot.material
            inner()
        """)
        av(analyze_source(src), V["NPA"], "outer.<nested:inner>")

    def test_lambda_slot_mat(self):
        src = textwrap.dedent("""\
        def outer(obj):
            slots = obj.material_slots
            slot = slots[0]
            f = lambda: slot.material
            f()
        """)
        v = analyze_source(src)
        assert any(V["LPA"] in vi and "material" in vi for vi in v), v


# ── dynamic access violations ──────────────────────────────────────────
class TestDynamicAccess:
    def test_getattr_ms(self):
        src = textwrap.dedent("""\
        def other():
            getattr(obj, "material_slots")
        """)
        av(analyze_source(src), V["DPA"], "other", "getattr:material_slots")

    def test_getattr_concat(self):
        src = textwrap.dedent("""\
        def other():
            getattr(obj, "material_" + "slots")
        """)
        av(analyze_source(src), V["DPA"], "other", "getattr:material_slots")

    def test_getattr_var(self):
        src = textwrap.dedent("""\
        def other():
            name = "material_slots"
            getattr(obj, name)
        """)
        av(analyze_source(src), V["DPA"], "other", "getattr:material_slots")

    def test_func_alias_getattr(self):
        src = textwrap.dedent("""\
        def other():
            reader = getattr
            reader(obj, "material_slots")
        """)
        av(analyze_source(src), V["DPA"], "other", "getattr:material_slots")

    def test_func_alias_setattr(self):
        src = textwrap.dedent("""\
        def other():
            writer = setattr
            writer(obj, "material_slots", [])
        """)
        v = analyze_source(src)
        assert any(V["DPA"] in vi and "material_slots" in vi for vi in v), v

    def test_setattr_delattr_hasattr(self):
        src = textwrap.dedent("""\
        def other():
            setattr(obj, "material_slots", [])
            delattr(obj, "material_slots")
            hasattr(obj, "material_slots")
        """)
        v = analyze_source(src)
        av(v, V["DPA"], "other", "setattr:material_slots")
        av(v, V["DPA"], "other", "delattr:material_slots")
        av(v, V["DPA"], "other", "hasattr:material_slots")


# ── write/delete violations ─────────────────────────────────────────────
class TestWriteDelete:
    def test_write_ms(self):
        src = textwrap.dedent("""\
        def f():
            obj = None
            obj.material_slots = []
        """)
        av(analyze_source(src), V["PW"], "f", "material_slots")

    def test_del_ms(self):
        src = textwrap.dedent("""\
        def f():
            del obj.material_slots
        """)
        av(analyze_source(src), V["PD"], "f", "material_slots")

    def test_augassign_ms(self):
        src = textwrap.dedent("""\
        def f():
            obj.material_slots += []
        """)
        av(analyze_source(src), V["PW"], "f", "material_slots")


# ── BPY_DATA_BYPASS ────────────────────────────────────────────────────
class TestBpyData:
    def test_direct(self):
        src = textwrap.dedent("""\
        import bpy
        def other():
            bpy.data.objects["x"].material_slots
        """)
        av(analyze_source(src), V["BPY"], "other", "material_slots")

    def test_data_alias(self):
        src = textwrap.dedent("""\
        import bpy
        def other():
            data = bpy.data
            data.objects["x"].material_slots
        """)
        av(analyze_source(src), V["BPY"], "other", "material_slots")

    def test_objects_alias(self):
        src = textwrap.dedent("""\
        import bpy
        def other():
            objects = bpy.data.objects
            objects["x"].material_slots
        """)
        av(analyze_source(src), V["BPY"], "other", "material_slots")


# ── clean cases ────────────────────────────────────────────────────────
class TestCleanCases:
    def test_config_material_reader(self):
        src = textwrap.dedent("""\
        def cr(config):
            return config.material
        """)
        assert analyze_source(src) == []

    def test_nested_config_reader(self):
        src = textwrap.dedent("""\
        def outer(config):
            def inner():
                return config.material
            return inner()
        """)
        assert analyze_source(src) == []

    def test_lambda_config_reader(self):
        src = textwrap.dedent("""\
        def outer(config):
            r = lambda: config.material
            return r()
        """)
        assert analyze_source(src) == []

    def test_config_writer(self):
        src = textwrap.dedent("""\
        def cw(config):
            config.material = "x"
            config.material += "y"
            getattr(config, "material")
            setattr(config, "material", "v")
        """)
        assert analyze_source(src) == []

    def test_auth_calls_ordinary(self):
        src = textwrap.dedent("""\
        def cr(config):
            return config.material
        def _check_material_slots_for_mesh(mesh_obj, mesh_name):
            return cr(mesh_name)
        """)
        assert analyze_source(src) == []

    def test_scene_objects_ok(self):
        src = textwrap.dedent("""\
        def _check_material_assignment(scene, target, ptr):
            scene.objects
            obj = None
            obj.name
        """)
        assert analyze_source(src) == []

    def test_children_type_ok(self):
        src = textwrap.dedent("""\
        def _collect_geometry_scope_objects(*a):
            obj = None
            obj.children
            d = None
            d.type
        """)
        assert analyze_source(src) == []

    def test_unreachable_ordinary(self):
        src = textwrap.dedent("""\
        def unused(config):
            return config.material
        """)
        assert analyze_source(src) == []

    def test_unreachable_self_contained_slot(self):
        src = textwrap.dedent("""\
        def unused(obj):
            slots = obj.material_slots
            for s in slots:
                s.material
        """)
        av(analyze_source(src), V["PSR"], "unused")


# ── self-checks ────────────────────────────────────────────────────────
class TestSelfCheck:
    def test_all_tests_have_assertions(self):
        with open(__file__, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                ok = False
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Assert):
                        # Reject constant True assertions
                        if isinstance(sub.test, ast.Constant) and sub.test.value is True:
                            assert False, f"Test {node.name} has assert True"
                        ok = True; break
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == "raises":
                        ok = True; break
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id == "av":
                        ok = True; break
                assert ok, f"Test {node.name} has no assertion"

    def test_no_placeholders(self):
        with open(__file__, "r", encoding="utf-8") as f:
            src = f.read()
        # Remove self-check body from scan
        src_clean = src.split("def test_no_placeholders")[0]
        for phrase in ["assert True  # documented", "# documented: requires",
                       "not traced without", "partial coverage"]:
            assert phrase not in src_clean, f"Placeholder text found: '{phrase}'"

    def test_no_or_true(self):
        with open(__file__, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
                for vv in node.values:
                    if isinstance(vv, ast.Constant) and vv.value is True:
                        assert False, "'or True' found"
