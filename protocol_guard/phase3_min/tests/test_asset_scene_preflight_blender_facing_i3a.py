"""Tests for 14B-3B I3A R5B: alias propagation, setattr/delattr, false-positive prevention."""
import ast, os, sys, textwrap, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

READER_PATH = os.path.join(ROOT, "protocol_guard", "phase3_min", "blender_scene_reader.py")
CHECKER_PATH = os.path.join(ROOT, "protocol_guard", "phase3_min", "asset_scene_preflight_check.py")

FACING_FIELDS = {"local_forward_axis", "expected_world_forward_axis", "facing_tolerance_degrees"}
MUTATION_METHODS = {"link", "unlink", "new", "remove", "clear", "append", "extend", "insert", "pop"}


def _collect_import_aliases(tree):
    """Collect {local_name: canonical} for subprocess/run etc. imports."""
    aliases = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "subprocess":
            for alias in node.names:
                name = alias.asname or alias.name
                aliases[name] = ("subprocess", alias.name)
    return aliases


def _attr_chain(node):
    parts = []
    cur = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return list(reversed(parts))
    return None


class FacingScopeAnalyzer:
    def __init__(self, reader_path, checker_path):
        self.reader_tree = self._parse(reader_path)
        self.checker_tree = self._parse(checker_path)

    def _parse(self, path):
        with open(path, encoding="utf-8") as f:
            return ast.parse(f.read(), filename=path)

    @staticmethod
    def _is_func(node):
        return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))

    def _top_funcs(self, tree):
        return {n.name: n for n in ast.iter_child_nodes(tree) if self._is_func(n)}

    def _walk_scope_aware(self, node):
        yield node
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef,
                                  ast.Lambda, ast.ClassDef)):
                continue
            yield from self._walk_scope_aware(child)

    def _collect_nested_funcs(self, node):
        result = {}
        for child in ast.iter_child_nodes(node):
            if self._is_func(child):
                result[child.name] = child
            else:
                result.update(self._collect_nested_funcs(child))
        return result

    def _collect_lambda_bindings(self, fn_node):
        bindings = {}
        for child in self._walk_scope_aware(fn_node):
            if isinstance(child, ast.Assign):
                if isinstance(child.value, ast.Lambda):
                    for t in child.targets:
                        if isinstance(t, ast.Name):
                            bindings[t.id] = child.value
        return bindings

    def _collect_class_names(self, fn_node):
        names = set()
        for child in ast.iter_child_nodes(fn_node):
            if isinstance(child, ast.ClassDef):
                names.add(child.name)
            elif not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                names.update(self._collect_class_names(child))
        return names

    def _looks_collection_like(self, receiver, local_aliases):
        """Chain contains 'collection'/'collections' OR name traces to collection source."""
        chain = _attr_chain(receiver)
        if chain:
            if any(w in ("collection", "collections") for w in chain):
                return True
        if isinstance(receiver, ast.Name):
            return local_aliases.get(receiver.id) == "collection"
        return False

    def _open_has_write_mode(self, call_node):
        if not (isinstance(call_node.func, ast.Name) and call_node.func.id == "open"):
            return None
        args = call_node.args
        kwargs = {kw.arg: kw.value for kw in call_node.keywords if kw.arg is not None}
        mode_val = None
        if len(args) >= 2:
            m = args[1]
            if isinstance(m, ast.Constant) and isinstance(m.value, str):
                mode_val = m.value
            else:
                return "UNKNOWN"
        elif "mode" in kwargs:
            m = kwargs["mode"]
            if isinstance(m, ast.Constant) and isinstance(m.value, str):
                mode_val = m.value
            else:
                return "UNKNOWN"
        if mode_val is None:
            return False
        for c in "wax+":
            if c in mode_val:
                return True
        return False

    def _param_names(self, fn):
        if not self._is_func(fn):
            return set()
        names = {a.arg for a in fn.args.args}
        if fn.args.vararg:
            names.add(fn.args.vararg.arg)
        return names

    def _collect_local_aliases(self, fn_node):
        """Collect local variable source types with alias chaining.
        Returns {name -> 'collection'|'bpyops'}.
        Plain aliases (x = y) inherit y's source. Attribute chains are
        checked for Blender context."""
        sources = {}
        for child in self._walk_scope_aware(fn_node):
            if isinstance(child, ast.Assign):
                src_type = None
                if isinstance(child.value, ast.Attribute):
                    chain = _attr_chain(child.value)
                    if chain:
                        if any(w in ("collection", "collections") for w in chain):
                            src_type = "collection"
                        elif len(chain) >= 2 and chain[0] == "bpy" and chain[1] == "ops":
                            src_type = "bpyops"
                elif isinstance(child.value, ast.Name):
                    src_type = sources.get(child.value.id)
                if src_type:
                    for t in child.targets:
                        if isinstance(t, ast.Name):
                            sources[t.id] = src_type
        return sources

    def _violations_in(self, fn_node, context, import_aliases=None):
        if import_aliases is None:
            import_aliases = {}
        found = []
        params = self._param_names(fn_node)
        reported_writes = set()
        local_aliases = self._collect_local_aliases(fn_node)

        # Track inline lambda calls: (lambda ...)(args) or await (lambda ...)(args)
        lambda_calls = []

        for child in self._walk_scope_aware(fn_node):
            # ── Inline Lambda calls ──
            # (lambda x: ...)(args)
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Lambda):
                lambda_calls.append(("lambda_call", child.lineno))
            # await (lambda x: ...)(args)
            if isinstance(child, ast.Await) and isinstance(child.value, ast.Call):
                if isinstance(child.value.func, ast.Lambda):
                    lambda_calls.append(("await_lambda_call", child.lineno))

            # ── setattr / delattr ──
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                if child.func.id == "setattr" and child.args:
                    arg0 = child.args[0]
                    if (isinstance(arg0, ast.Name) and arg0.id in params):
                        found.append(f"WRITE: setattr on param '{arg0.id}' in {context}")
                if child.func.id == "delattr" and child.args:
                    arg0 = child.args[0]
                    if (isinstance(arg0, ast.Name) and arg0.id in params):
                        found.append(f"WRITE: delattr on param '{arg0.id}' in {context}")

            # ── Writes ──
            if isinstance(child, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = (child.targets if isinstance(child, ast.Assign) else [child.target])
                for t in targets:
                    if isinstance(t, ast.Attribute):
                        key = (t.attr, getattr(t, "lineno", 0))
                        if key not in reported_writes:
                            reported_writes.add(key)
                            found.append(f"WRITE: {t.attr} in {context}")
                    elif isinstance(t, ast.Subscript):
                        base = t.value
                        if ((isinstance(base, ast.Name) and base.id in params)
                                or isinstance(base, ast.Attribute)):
                            found.append(f"WRITE: subscript in {context}")
            if isinstance(child, ast.Delete):
                for t in child.targets:
                    if isinstance(t, (ast.Attribute, ast.Subscript)):
                        found.append(f"WRITE: delete in {context}")

            # ── bpy.ops (direct + alias) ──
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                # Direct bpy.ops
                chain = _attr_chain(child.func)
                if chain and len(chain) >= 3 and chain[0] == "bpy" and chain[1] == "ops":
                    found.append(f"BPY_OPS: bpy.ops.{'.'.join(chain[2:])} in {context}")
                # Alias: ops = bpy.ops; ops.object.mode_set(...)
                # Check if func.value resolves to a bpyops alias through a chain
                cur = child.func
                while isinstance(cur, ast.Attribute):
                    cur = cur.value
                if isinstance(cur, ast.Name) and cur.id in local_aliases and local_aliases[cur.id] == "bpyops":
                    found.append(f"BPY_OPS: via alias '{cur.id}' in {context}")

            # ── subprocess (direct + import alias) ──
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                chain = _attr_chain(child.func)
                if chain and chain[0] == "subprocess" and chain[1] in (
                        "run", "call", "check_call", "check_output", "Popen"):
                    found.append(f"SUBPROCESS: {chain[1]} in {context}")
                if chain and chain[0] == "os" and chain[1] in ("system", "popen"):
                    found.append(f"OS_EXEC: {chain[1]} in {context}")
            # Import alias: from subprocess import run as execute; execute(...)
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                if child.func.id in import_aliases:
                    mod, fn = import_aliases[child.func.id]
                    if mod == "subprocess":
                        found.append(f"SUBPROCESS: {fn} (import alias) in {context}")

            # ── File writes ──
            if isinstance(child, ast.Call):
                mc = self._open_has_write_mode(child)
                if mc is True:
                    found.append(f"FILE_WRITE: open write mode in {context}")
                elif mc == "UNKNOWN":
                    found.append(f"FILE_WRITE: open dynamic mode in {context}")
                if isinstance(child.func, ast.Attribute):
                    if child.func.attr in ("write", "writelines"):
                        found.append(f"FILE_WRITE: .{child.func.attr}() in {context}")
                    if child.func.attr in ("write_text", "write_bytes"):
                        found.append(f"FILE_WRITE: Path.{child.func.attr}() in {context}")

            # ── Facing fields ──
            if isinstance(child, ast.Subscript) and isinstance(child.value, ast.Name):
                if child.value.id == "facing" and isinstance(child.slice, ast.Constant):
                    if child.slice.value not in FACING_FIELDS:
                        found.append(f"FIELD: facing['{child.slice.value}'] in {context}")
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                if (child.func.attr == "get" and isinstance(child.func.value, ast.Name)
                        and child.func.value.id == "facing" and child.args):
                    a0 = child.args[0]
                    if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
                        if a0.value not in FACING_FIELDS:
                            found.append(f"FIELD: facing.get('{a0.value}') in {context}")

            # ── Collection mutation (direct + alias) ──
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                if child.func.attr in MUTATION_METHODS:
                    receiver = child.func.value
                    if self._looks_collection_like(receiver, local_aliases):
                        found.append(f"MUTATION: {child.func.attr}() on collection in {context}")

        for kind, lineno in lambda_calls:
            found.append(f"UNSUPPORTED_REACHABLE_LAMBDA: {kind} at line {lineno} in {context}")

        return found

    def _resolve_call_target(self, callee_name, local_funcs, nested_funcs,
                              lambda_bindings, class_names):
        if callee_name in nested_funcs:
            return ("func", nested_funcs[callee_name])
        if callee_name in local_funcs:
            return ("func", local_funcs[callee_name])
        if callee_name in lambda_bindings:
            return ("lambda", None)
        if callee_name in class_names:
            return ("class", None)
        return (None, None)

    def analyze(self, entry_node, context, local_funcs, tree, depth=0, parent_nested=None):
        if depth > 20:
            return []
        import_aliases = _collect_import_aliases(tree)
        violations = list(self._violations_in(entry_node, context, import_aliases))

        nested_funcs = self._collect_nested_funcs(entry_node)
        if parent_nested:
            nested_funcs = {**parent_nested, **nested_funcs}
        lambda_bindings = self._collect_lambda_bindings(entry_node)
        class_names = self._collect_class_names(entry_node)

        for child in self._walk_scope_aware(entry_node):
            callee = None
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                callee = child.func.id
            elif isinstance(child, ast.Await) and isinstance(child.value, ast.Call):
                call = child.value
                if isinstance(call.func, ast.Name):
                    callee = call.func.id
            if callee is None:
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                    receiver = child.func.value
                    if isinstance(receiver, ast.Call) and isinstance(receiver.func, ast.Name):
                        if receiver.func.id in class_names:
                            violations.append(
                                f"UNSUPPORTED_REACHABLE_LOCAL_CLASS: "
                                f"{receiver.func.id}.{child.func.attr}() in {context}")
                continue

            kind, target = self._resolve_call_target(
                callee, local_funcs, nested_funcs, lambda_bindings, class_names)
            if kind == "lambda":
                violations.append(f"UNSUPPORTED_REACHABLE_LAMBDA: {callee} in {context}")
                continue
            if kind == "class":
                violations.append(f"UNSUPPORTED_REACHABLE_LOCAL_CLASS: {callee}() in {context}")
                continue
            if kind != "func":
                continue

            edge = (callee,)
            if edge in getattr(self, "cycles", set()):
                continue
            if not hasattr(self, "cycles"):
                self.cycles = set()
            self.cycles.add(edge)
            violations.extend(
                self.analyze(target, f"{context}->{callee}",
                             local_funcs, tree, depth + 1, nested_funcs))

        return violations

    def analyze_production(self):
        reader_funcs = self._top_funcs(self.reader_tree)
        checker_funcs = self._top_funcs(self.checker_tree)
        fn = reader_funcs.get("_check_facing_forward_axis")
        assert fn is not None, "_check_facing_forward_axis not found"
        all_v = list(self.analyze(fn, "facing_reader", reader_funcs, self.reader_tree))
        fn2 = checker_funcs.get("_validate_facing_forward_axis_rules_preopen")
        assert fn2 is not None, "_validate_facing_forward_axis_rules_preopen not found"
        all_v.extend(self.analyze(fn2, "facing_checker", checker_funcs, self.checker_tree))
        return all_v


def _analyze_snippet(code, entry_name):
    tree = ast.parse(textwrap.dedent(code))
    local = {}
    entry = None
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            local[node.name] = node
            if node.name == entry_name:
                entry = node
    assert entry is not None, f"Entry '{entry_name}' not found"
    a = FacingScopeAnalyzer.__new__(FacingScopeAnalyzer)
    a.reader_tree = tree
    a.checker_tree = tree
    a.cycles = set()
    return a.analyze(entry, entry_name, local, tree)


# ═══════════════ Production ═════════════════════════════════════════════

class TestProduction:
    def test_reader_clean(self):
        a = FacingScopeAnalyzer(READER_PATH, CHECKER_PATH)
        assert a.analyze_production() == []
    def test_preopen_no_blender(self):
        t = ast.parse(open(CHECKER_PATH, encoding="utf-8").read(), filename=CHECKER_PATH)
        fn = next(n for n in ast.walk(t) if isinstance(n, ast.FunctionDef)
                  and n.name == "_validate_facing_forward_axis_rules_preopen")
        s = list(fn.body)
        if s and isinstance(s[0], ast.Expr) and isinstance(s[0].value, ast.Constant) and isinstance(s[0].value.value, str):
            s = s[1:]
        b = ast.unparse(ast.Module(body=s, type_ignores=[]))
        for w in ["bpy", "blender_scene_reader", "mathutils", "subprocess"]:
            assert w not in b


class TestEntryMissing:
    def test_reader(self):
        td = tempfile.TemporaryDirectory()
        try:
            rp = os.path.join(td.name, "r.py"); cp = os.path.join(td.name, "c.py")
            with open(rp, "w") as f: f.write("")
            with open(cp, "w") as f: f.write("def _validate_facing_forward_axis_rules_preopen(): pass\n")
            with __import__("pytest").raises(AssertionError, match="not found"):
                FacingScopeAnalyzer(rp, cp).analyze_production()
        finally: td.cleanup()
    def test_checker(self):
        td = tempfile.TemporaryDirectory()
        try:
            rp = os.path.join(td.name, "r.py"); cp = os.path.join(td.name, "c.py")
            with open(rp, "w") as f: f.write("def _check_facing_forward_axis(): pass\n")
            with open(cp, "w") as f: f.write("")
            with __import__("pytest").raises(AssertionError, match="not found"):
                FacingScopeAnalyzer(rp, cp).analyze_production()
        finally: td.cleanup()
    def test_sync(self):
        with __import__("pytest").raises(AssertionError, match="not found"):
            _analyze_snippet("def x(): pass", "f")
    def test_async(self):
        assert any("WRITE" in x for x in _analyze_snippet("async def f(r): r.s=(1,1,1)", "f"))


class TestMatrix:
    def _c(self, t, a):
        return sum(1 for n in ast.walk(t) if isinstance(n, ast.Attribute) and n.attr == a and isinstance(n.ctx, ast.Load))
    def _cm(self, t, m):
        return sum(1 for n in ast.walk(t) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == m)
    def test_mw(self):
        t = ast.parse(open(READER_PATH, encoding="utf-8").read())
        fn = next(n for n in ast.walk(t) if isinstance(n, ast.FunctionDef) and n.name == "_check_facing_forward_axis")
        assert self._c(fn, "matrix_world") == 1
    def test_t3(self):
        t = ast.parse(open(READER_PATH, encoding="utf-8").read())
        fn = next(n for n in ast.walk(t) if isinstance(n, ast.FunctionDef) and n.name == "_check_facing_forward_axis")
        assert self._cm(fn, "to_3x3") == 1
    def test_other(self):
        t = ast.parse(open(READER_PATH, encoding="utf-8").read())
        ok = {"_check_standing_up_axis", "_check_facing_forward_axis",
              "_check_rotation", "_check_ground_contact",
              "_check_camera_check",
              "_check_projection_groups"}
        for n in ast.iter_child_nodes(t):
            if isinstance(n, ast.FunctionDef) and n.name not in ok:
                assert self._c(n, "matrix_world") == 0

        # _check_ground_contact has exactly 1 matrix_world Load
        gc_fn = next(n for n in ast.walk(t) if isinstance(n, ast.FunctionDef)
                     and n.name == "_check_ground_contact")
        assert self._c(gc_fn, "matrix_world") == 1
    def test_checker(self):
        assert self._c(ast.parse(open(CHECKER_PATH, encoding="utf-8").read()), "matrix_world") == 0


class TestIsolation:
    def _bd(self, fn):
        s = list(fn.body)
        if s and isinstance(s[0], ast.Expr) and isinstance(s[0].value, ast.Constant) and isinstance(s[0].value.value, str):
            s = s[1:]
        return ast.unparse(ast.Module(body=s, type_ignores=[]))
    def test_standing(self):
        t = ast.parse(open(READER_PATH, encoding="utf-8").read())
        fn = next(n for n in ast.walk(t) if isinstance(n, ast.FunctionDef) and n.name == "_check_standing_up_axis")
        b = self._bd(fn).lower()
        for w in ["forward_axis", "local_forward", "expected_world_forward"]:
            assert w not in b
    def test_facing(self):
        t = ast.parse(open(READER_PATH, encoding="utf-8").read())
        fn = next(n for n in ast.walk(t) if isinstance(n, ast.FunctionDef) and n.name == "_check_facing_forward_axis")
        b = self._bd(fn).lower()
        for w in ["up_axis", "local_up", "expected_world_up"]:
            assert w not in b


# ═══════════════ Prior adversarial (compressed) ════════════════════════

class TestW:  # Writes
    def test_a(self): assert any("WRITE" in x for x in _analyze_snippet("def f(r): r.s=(1,1,1)", "f"))
    def test_s(self): assert any("WRITE" in x for x in _analyze_snippet("def f(r): r.s[0]+=1", "f"))
    def test_d(self): assert any("WRITE" in x for x in _analyze_snippet("def f(r): del r['c']", "f"))

class TestBO:  # bpy/subprocess
    def test_b(self): assert any("BPY_OPS" in x for x in _analyze_snippet("def f(): bpy.ops.o.m(m='E')", "f"))
    def test_s(self): assert any("SUBPROCESS" in x for x in _analyze_snippet("def f(): subprocess.run(['x'])", "f"))

class TestFM:  # File mode
    def test_w(self): assert any("FILE_WRITE" in x for x in _analyze_snippet('def f(): open("x","w")', "f"))
    def test_k(self): assert any("FILE_WRITE" in x for x in _analyze_snippet('def f(): open("x",mode="w")', "f"))
    def test_dyn(self): assert any("FILE_WRITE" in x for x in _analyze_snippet('def f(m): open("x",m)', "f"))
    def test_r(self): assert not any("FILE_WRITE" in x for x in _analyze_snippet('def f(): open("x","r")', "f"))
    def test_fh(self): assert any("FILE_WRITE" in x for x in _analyze_snippet('def f(fh): fh.write("x")', "f"))
    def test_pw(self): assert any("FILE_WRITE" in x for x in _analyze_snippet('from pathlib import Path\ndef f(): Path("x").write_text("y")', "f"))

class TestFiM:  # Fields + mutation
    def test_s(self): assert any("FIELD" in x for x in _analyze_snippet('def f(facing): facing["gc"]', "f"))
    def test_g(self): assert any("FIELD" in x for x in _analyze_snippet('def f(facing): facing.get("gc")', "f"))
    def test_l(self): assert any("MUTATION" in x for x in _analyze_snippet('def f(s,r): s.collection.objects.link(r)', "f"))
    def test_a(self): assert any("MUTATION" in x for x in _analyze_snippet('def f(s,r): s.collection.objects.append(r)', "f"))

class TestHP:  # Helper prop
    def test_1(self): assert any("WRITE" in x and "h" in x for x in _analyze_snippet("def f(r): h(r)\ndef h(r): r.s=(1,1,1)", "f"))
    def test_u(self): assert not any("WRITE" in x for x in _analyze_snippet("def f(): pass\ndef h(r): r.s=(1,1,1)", "f"))
    def test_m(self): assert any("WRITE" in x and "b" in x for x in _analyze_snippet("def f(r): a(r)\ndef a(r): b(r)\ndef b(r): r.s=(1,1,1)", "f"))
    def test_c(self): assert any("WRITE" in x and "b" in x for x in _analyze_snippet("def f(r): a(r)\ndef a(r): b(r)\ndef b(r): a(r); r.s=(1,1,1)", "f"))

class TestAL:  # Append local
    def test_s(self): assert any("MUTATION" in x for x in _analyze_snippet('def f(s,r): s.collection.objects.append(r)', "f"))
    def test_l(self): assert not any("MUTATION" in x for x in _analyze_snippet("def f(): items=[]; items.append(42)", "f"))

class TestNF:  # No false
    def test_la(self): assert _analyze_snippet("def f(): x=42; y={}; y['k']='v'", "f") == []
    def test_ro(self): assert _analyze_snippet("def f(r): return r.matrix_world", "f") == []
    def test_af(self): assert _analyze_snippet("def f(f): f.get('local_forward_axis')", "f") == []

class TestNS:  # Nested scope
    def test_us(self): assert not any("WRITE" in x for x in _analyze_snippet("""
        def f():
            def h(r):
                r.s = (1, 1, 1)
            return 1
    """, "f"))
    def test_ua(self): assert not any("WRITE" in x for x in _analyze_snippet("""
        def f():
            async def h(r):
                r.s = (1, 1, 1)
            return 1
    """, "f"))
    def test_rs(self): assert any("WRITE" in x and "h" in x for x in _analyze_snippet("""
        def f(r):
            def h(x):
                x.s = (1, 1, 1)
            h(r)
    """, "f"))
    def test_ra(self): assert any("WRITE" in x and "h" in x for x in _analyze_snippet("""
        async def f(r):
            async def h(x):
                x.s = (1, 1, 1)
            await h(r)
    """, "f"))
    def test_ml(self): assert any("WRITE" in x and "b" in x for x in _analyze_snippet("""
        def f(r):
            def a(x):
                def b(y):
                    y.s = (1, 1, 1)
                b(x)
            a(r)
    """, "f"))
    def test_cy(self): assert any("WRITE" in x and "b" in x for x in _analyze_snippet("""
        def f(r):
            def a(x):
                b(x)
            def b(y):
                a(y)
                y.s = (1, 1, 1)
            a(r)
    """, "f"))
    def test_lu(self): assert not any("WRITE" in x for x in _analyze_snippet("""
        def f():
            h = lambda r: setattr(r, 's', (1, 1, 1))
            return 1
    """, "f"))
    def test_cu(self): assert not any("WRITE" in x for x in _analyze_snippet("""
        def f():
            class H:
                def m(self, r):
                    r.s = (1, 1, 1)
            return 1
    """, "f"))


class TestIB:  # if-block nested
    def test_if(self):
        assert any("WRITE" in x and "helper" in x for x in _analyze_snippet("""
            def f(r, flag=True):
                if flag:
                    def helper(x):
                        x.scale = (1, 1, 1)
                    helper(r)
        """, "f"))


class TestLS:  # Lexical shadowing
    def test_nv(self):
        assert any("WRITE" in x and "helper" in x for x in _analyze_snippet("""
            def helper(x): return x
            def f(r):
                def helper(x):
                    x.scale = (1, 1, 1)
                helper(r)
        """, "f"))
    def test_tv(self):
        assert not any("WRITE" in x for x in _analyze_snippet("""
            def helper(x):
                x.scale = (1, 1, 1)
            def f(r):
                def helper(x):
                    return x
                helper(r)
        """, "f"))


class TestRL:  # Lambda
    def test_called(self):
        assert any("UNSUPPORTED_REACHABLE_LAMBDA" in x for x in _analyze_snippet("""
            def f(r): h = lambda x: setattr(x,'s',(1,1,1)); h(r)
        """, "f"))
    def test_inline(self):
        assert any("UNSUPPORTED_REACHABLE_LAMBDA" in x for x in _analyze_snippet("""
            def f(r): (lambda x: setattr(x,'s',(1,1,1)))(r)
        """, "f"))
    def test_await_inline(self):
        v = _analyze_snippet("""
            async def f(r): await (lambda x: x.some_call(x))(r)
        """, "f")
        assert any("UNSUPPORTED_REACHABLE_LAMBDA" in x for x in v), f"await inline lambda not flagged: {v}"
    def test_uncalled(self):
        assert not any("UNSUPPORTED_REACHABLE_LAMBDA" in x for x in _analyze_snippet("""
            def f(r): h = lambda x: setattr(x,'s',(1,1,1)); return 1
        """, "f"))


class TestRC:  # Class
    def test_c(self):
        assert any("UNSUPPORTED_REACHABLE_LOCAL_CLASS" in x for x in _analyze_snippet("""
            def f(r):
                class H:
                    def m(self, x):
                        x.scale = (1, 1, 1)
                H().m(r)
        """, "f"))
    def test_u(self):
        assert not any("UNSUPPORTED_REACHABLE_LOCAL_CLASS" in x for x in _analyze_snippet("""
            def f(r):
                class H:
                    def m(self, x):
                        x.scale = (1, 1, 1)
                return 1
        """, "f"))


# ═══════════════ R5B: alias, setattr/delattr, false positive ═══════════

class TestSceneAlias:
    def test_direct_alias_append(self):
        v = _analyze_snippet("""
            def f(scene, root_obj):
                objects = scene.collection.objects
                objects.append(root_obj)
        """, "f")
        assert any("MUTATION" in x for x in v), f"alias not caught: {v}"

    def test_deep_alias_link(self):
        v = _analyze_snippet("""
            def f(scene, root_obj):
                collection = scene.collection
                objects = collection.objects
                objects.link(root_obj)
        """, "f")
        assert any("MUTATION" in x for x in v), f"deep alias not caught: {v}"

    def test_plain_alias_chain(self):
        v = _analyze_snippet("""
            def f(scene, root_obj):
                objects = scene.collection.objects
                destination = objects
                destination.append(root_obj)
        """, "f")
        assert any("MUTATION" in x for x in v), f"plain alias chain not caught: {v}"

    def test_three_level_alias_chain(self):
        v = _analyze_snippet("""
            def f(scene, root_obj):
                a = scene.collection.objects
                b = a
                c = b
                c.append(root_obj)
        """, "f")
        assert any("MUTATION" in x for x in v), f"three-level chain not caught: {v}"


class TestLocalObjectNoFalse:
    def test_holder(self):
        v = _analyze_snippet("""
            def f(value):
                result = Holder()
                result.objects.append(value)
        """, "f")
        assert not any("MUTATION" in x for x in v), f"false positive: {v}"

    def test_holder_aliased(self):
        v = _analyze_snippet("""
            def f(value):
                result = Holder()
                objects = result.objects
                destination = objects
                destination.append(value)
        """, "f")
        assert not any("MUTATION" in x for x in v), f"aliased local false positive: {v}"


class TestBpyOpsAlias:
    def test_alias(self):
        v = _analyze_snippet("""
            def f():
                ops = bpy.ops
                ops.object.mode_set(mode="EDIT")
        """, "f")
        assert any("BPY_OPS" in x for x in v), f"bpy alias not caught: {v}"


class TestSubprocessImportAlias:
    def test_import_alias(self):
        v = _analyze_snippet("""
            from subprocess import run as execute
            def f():
                execute(["blender", "--background"])
        """, "f")
        assert any("SUBPROCESS" in x for x in v), f"import alias not caught: {v}"


class TestSetattrDelattr:
    def test_setattr(self):
        v = _analyze_snippet("""
            def f(root_obj):
                setattr(root_obj, "scale", (1, 1, 1))
        """, "f")
        assert any("WRITE" in x for x in v), f"setattr not caught: {v}"

    def test_delattr(self):
        v = _analyze_snippet("""
            def f(root_obj):
                delattr(root_obj, "custom")
        """, "f")
        assert any("WRITE" in x for x in v), f"delattr not caught: {v}"
