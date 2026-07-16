"""Test mock executor with real input fixtures."""
import os, tempfile, yaml, pytest
from protocol_guard.gate.executor import mock_execute, _check_imports

class TestExecutorAST:
    def test_no_bpy(self): assert len(_check_imports("import bpy")) > 0
    def test_no_subprocess(self): assert len(_check_imports("import subprocess")) > 0
    def test_no_ctypes(self): assert len(_check_imports("import ctypes")) > 0
    def test_no_eval(self): assert len(_check_imports("eval('1+1')")) > 0
    def test_no_exec(self): assert len(_check_imports("exec('x=1')")) > 0
    def test_no_compile(self): assert len(_check_imports("compile('x','','exec')")) > 0
    def test_clean_imports(self): assert len(_check_imports("import os\nimport json")) == 0
    def test_unknown_import_rejected(self): assert len(_check_imports("import unknown_xyz")) > 0

class TestMockExecute:
    def test_execute_with_real_input(self):
        with tempfile.TemporaryDirectory() as td:
            inp = os.path.join(td, "in.txt")
            with open(inp, "w", encoding="utf-8") as f: f.write("hello world")
            task = {"task_id":"EX1","task_card_version":2,"input_files":["in.txt"],"output_files":["out.txt"],"primary_goal":"T","primary_variable":"x","dependent_variables":[],"fixed_params":{},"locked_items":[],"allowed_modifications":[],"forbidden_modifications":[],"preflight_checks":[],"technical_pass_conditions":[],"visual_intent":"","visual_forbidden":"","evidence_required":[],"upload_dir":"d","upload_files":["out.txt"],"stop_conditions":[],"state_patch_requested":None}
            tp = os.path.join(td, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            ws = os.path.join(td, "ws")
            ok, result, errs = mock_execute(tp, ws)
            assert ok, f"Failed: {errs}"
            assert "out.txt" in result["output_files"]
            out_path = os.path.join(ws, "out.txt")
            assert os.path.exists(out_path)

    def test_missing_input_fails(self):
        with tempfile.TemporaryDirectory() as td:
            task = {"task_id":"EX2","task_card_version":2,"input_files":["missing.txt"],"output_files":["out.txt"],"primary_goal":"T","primary_variable":"x","dependent_variables":[],"fixed_params":{},"locked_items":[],"allowed_modifications":[],"forbidden_modifications":[],"preflight_checks":[],"technical_pass_conditions":[],"visual_intent":"","visual_forbidden":"","evidence_required":[],"upload_dir":"d","upload_files":["out.txt"],"stop_conditions":[],"state_patch_requested":None}
            tp = os.path.join(td, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            ok, _, errs = mock_execute(tp, os.path.join(td, "ws"))
            assert not ok

    def test_output_generated_and_sha_correct(self):
        with tempfile.TemporaryDirectory() as td:
            inp = os.path.join(td, "in.txt")
            with open(inp, "w", encoding="utf-8") as f: f.write("test")
            task = {"task_id":"EX3","task_card_version":2,"input_files":["in.txt"],"output_files":["out.txt"],"primary_goal":"T","primary_variable":"x","dependent_variables":[],"fixed_params":{},"locked_items":[],"allowed_modifications":[],"forbidden_modifications":[],"preflight_checks":[],"technical_pass_conditions":[],"visual_intent":"","visual_forbidden":"","evidence_required":[],"upload_dir":"d","upload_files":["out.txt"],"stop_conditions":[],"state_patch_requested":None}
            tp = os.path.join(td, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            ws = os.path.join(td, "ws")
            ok, result, _ = mock_execute(tp, ws)
            assert ok
            assert "out.txt" in result["output_files"]
            assert len(result["output_files"]["out.txt"]) == 64

    def test_subprocess_blocked(self, monkeypatch):
        import subprocess
        def fake(*a,**kw): raise RuntimeError("blocked")
        monkeypatch.setattr(subprocess, "run", fake)
        monkeypatch.setattr(subprocess, "Popen", fake)
        with pytest.raises(RuntimeError, match="blocked"): subprocess.run(["echo"])
