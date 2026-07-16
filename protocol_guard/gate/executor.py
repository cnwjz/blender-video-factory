"""Mock executor with import whitelist enforced."""
import ast, hashlib, json, os, sys, tempfile, yaml

ALLOWED_IMPORTS = {"os","os.path","sys","json","hashlib","shutil","copy","tempfile","yaml","pathlib","textwrap","io","string","re","math","datetime","ast","uuid","protocol_guard.gate","protocol_guard.state","protocol_guard.result","protocol_guard.gate.attempt_state","protocol_guard.gate.claim","protocol_guard.gate.freeze_bundle","protocol_guard.gate.understand","protocol_guard.gate.authorize","protocol_guard.gate.preflight","protocol_guard.gate.executor","protocol_guard.gate.finalize","protocol_guard.gate.conditions","protocol_guard.gate.recovery","jsonschema"}
FORBIDDEN = {"bpy","subprocess","ctypes","multiprocessing","win32api","win32com","_winapi","socket","requests","urllib","http.client","concurrent.futures","threading","signal","msvcrt","importlib"}

def _check_imports(source):
    violations = []
    try: tree = ast.parse(source)
    except SyntaxError as e: return [f"AST error: {e}"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                n = alias.name.split(".")[0]
                if n in FORBIDDEN: violations.append(f"Forbidden import: {n}")
                if n not in ALLOWED_IMPORTS and n not in FORBIDDEN:
                    violations.append(f"Import not in whitelist: {n}")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                n = node.module.split(".")[0]
                if n in FORBIDDEN: violations.append(f"Forbidden import from: {n}")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ("eval","exec","compile"):
                violations.append(f"Forbidden builtin: {node.func.id}")
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "importlib":
                    violations.append("Forbidden: importlib.import_module")
    return violations

def mock_execute(task_path, workspace_dir):
    errors = []
    own = open(__file__, "r").read()
    v = _check_imports(own)
    if v: return (False, {"technical_result": "SPEC_INVALID", "errors": v}, v)

    if not os.path.exists(task_path): return (False, None, [f"Task not found: {task_path}"])
    with open(task_path, "r") as f: task = yaml.safe_load(f)

    os.makedirs(workspace_dir, exist_ok=True)
    input_files = task.get("input_files", [])
    outputs = task.get("output_files", [])

    if not input_files: return (False, None, ["No input files declared"])
    if not outputs: return (False, None, ["No output files declared"])

    state_dir = os.path.dirname(os.path.abspath(task_path))
    result_outputs = {}
    found_input = False

    for inf in input_files:
        if not inf.endswith(".txt"): continue
        inf_abs = os.path.join(state_dir, inf)
        if not os.path.exists(inf_abs): return (False, None, [f"Input not found: {inf}"])
        found_input = True
        with open(inf_abs, "r", encoding="utf-8") as f: content = f.read()
        transformed = content.upper()
        lines = len(content.splitlines())
        result_text = f"Lines: {lines}\n\n{transformed}"

        txt_outputs = [o for o in outputs if o.endswith(".txt")]
        if not txt_outputs: return (False, None, ["No .txt output declared"])
        out = txt_outputs[0]
        out_abs = os.path.join(workspace_dir, os.path.basename(out))
        with open(out_abs, "w", encoding="utf-8") as f: f.write(result_text)
        h = hashlib.sha256(open(out_abs, "rb").read()).hexdigest()
        result_outputs[out] = h
        break

    if not found_input: return (False, None, ["No .txt input found in declared inputs"])

    return (True, {"output_files": result_outputs, "workspace_dir": workspace_dir}, [])
