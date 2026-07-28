"""Smoke and adversarial tests for protocol_guard infrastructure tools.

Covers: assertions.py, evidence_runner.py, zip_builder.py, conftest.py
"""
import ast
import os
import subprocess
import sys
import tempfile
import zipfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from protocol_guard.phase3_min.tests.assertions import assert_dict_equal, assert_no_extra_keys, assert_result_has_fields
from protocol_guard.phase3_min.evidence_runner import run_and_capture
from protocol_guard.phase3_min.zip_builder import build_zip, verify_zip, _validate_arcname


# ═══════════════════════════════════════════════════════════════════════
# assertions.py
# ═══════════════════════════════════════════════════════════════════════

class TestAssertDictEqualStrictTypes:
    def test_rejects_true_vs_1(self):
        with pytest.raises(AssertionError, match="type"):
            assert_dict_equal({"x": True}, {"x": 1})

    def test_rejects_1_vs_1_0(self):
        with pytest.raises(AssertionError, match="type"):
            assert_dict_equal({"x": 1}, {"x": 1.0})

    def test_rejects_false_vs_0(self):
        with pytest.raises(AssertionError, match="type"):
            assert_dict_equal({"x": False}, {"x": 0})

    def test_accepts_same_type_and_value(self):
        assert_dict_equal({"x": True}, {"x": True})
        assert_dict_equal({"x": 1}, {"x": 1})
        assert_dict_equal({"x": 1.0}, {"x": 1.0})
        assert_dict_equal({"x": False}, {"x": False})

    def test_accepts_str_vs_str(self):
        assert_dict_equal({"a": "hello"}, {"a": "hello"})

    def test_accepts_none(self):
        assert_dict_equal({"a": None}, {"a": None})

    def test_rejects_none_vs_false(self):
        with pytest.raises(AssertionError, match="type"):
            assert_dict_equal({"a": None}, {"a": False})


class TestAssertDictEqualKeys:
    def test_rejects_extra_key(self):
        with pytest.raises(AssertionError, match="extra keys"):
            assert_dict_equal({"a": 1, "b": 2}, {"a": 1})

    def test_rejects_missing_key(self):
        with pytest.raises(AssertionError, match="missing keys"):
            assert_dict_equal({"a": 1}, {"a": 1, "b": 2})

    def test_nested_extra_key(self):
        with pytest.raises(AssertionError, match="extra keys"):
            assert_dict_equal({"a": {"x": 1, "y": 2}}, {"a": {"x": 1}})

    def test_nested_missing_key(self):
        with pytest.raises(AssertionError, match="missing keys"):
            assert_dict_equal({"a": {"x": 1}}, {"a": {"x": 1, "y": 2}})

    def test_correct_recursive_match(self):
        assert_dict_equal(
            {"a": {"x": 1, "y": "z"}, "b": 2},
            {"a": {"x": 1, "y": "z"}, "b": 2},
        )


class TestAssertNoExtraKeys:
    def test_allowed(self):
        assert_no_extra_keys({"a": 1, "b": 2}, {"a", "b", "c"})

    def test_rejects_extra(self):
        with pytest.raises(AssertionError, match="extra keys"):
            assert_no_extra_keys({"a": 1, "d": 2}, {"a"})


class TestAssertResultHasFields:
    def test_all_present(self):
        assert_result_has_fields({"a": 1, "b": 2}, {"a", "b"})

    def test_missing(self):
        with pytest.raises(AssertionError, match="missing"):
            assert_result_has_fields({"a": 1}, {"a", "b"})


# ═══════════════════════════════════════════════════════════════════════
# evidence_runner.py
# ═══════════════════════════════════════════════════════════════════════

class TestEvidenceRunner:
    def test_creates_parent_directory(self):
        td = tempfile.mkdtemp()
        try:
            test_py = os.path.join(td, "test_trivial.py")
            with open(test_py, "w") as f:
                f.write("def test_pass(): assert 1 == 1")
            out = os.path.join(td, "sub", "nested", "output.txt")
            rc = run_and_capture(test_py, out)
            assert rc == 0
            assert os.path.exists(out)
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_saves_stdout(self):
        td = tempfile.mkdtemp()
        try:
            test_py = os.path.join(td, "test_ok.py")
            with open(test_py, "w") as f:
                f.write("def test_pass(): assert 1 == 1")
            out = os.path.join(td, "output.txt")
            run_and_capture(test_py, out)
            with open(out, encoding="utf-8") as f:
                content = f.read()
            assert "test_pass" in content
            assert "PASSED" in content
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_saves_stderr(self, monkeypatch):
        """Prove proc.stderr is written to the output file."""
        STDOUT_MARKER = "STDOUT_CONTENT_XYZ"
        STDERR_MARKER = "STDERR_CONTENT_ABC"
        EXIT_CODE = 3

        class FakeResult:
            stdout = STDOUT_MARKER
            stderr = STDERR_MARKER
            returncode = EXIT_CODE

        def fake_run(cmd, capture_output, text, cwd):
            return FakeResult

        monkeypatch.setattr(subprocess, "run", fake_run)

        td = tempfile.mkdtemp()
        try:
            out = os.path.join(td, "output.txt")
            rc = run_and_capture("dummy_test.py", out)
            assert rc == EXIT_CODE
            with open(out, encoding="utf-8") as f:
                content = f.read()
            assert STDOUT_MARKER in content, "stdout marker missing"
            assert STDERR_MARKER in content, "stderr marker missing"
            assert f"PYTEST_EXIT_CODE: {EXIT_CODE}" in content, "exit code missing"
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_records_exit_code(self):
        td = tempfile.mkdtemp()
        try:
            test_py = os.path.join(td, "test_pass.py")
            with open(test_py, "w") as f:
                f.write("def test_pass(): assert True")
            out = os.path.join(td, "output.txt")
            rc = run_and_capture(test_py, out)
            assert rc == 0
            with open(out, encoding="utf-8") as f:
                content = f.read()
            assert "PYTEST_EXIT_CODE: 0" in content
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_returns_exit_code(self):
        td = tempfile.mkdtemp()
        try:
            test_py = os.path.join(td, "test_mix.py")
            with open(test_py, "w") as f:
                f.write("def test_ok(): pass\ndef test_bad(): assert 0")
            out = os.path.join(td, "output.txt")
            rc = run_and_capture(test_py, out)
            assert rc == 1
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_command_contains_spaces_correctly(self):
        td = tempfile.mkdtemp()
        try:
            test_py = os.path.join(td, "test with spaces.py")
            with open(test_py, "w") as f:
                f.write("def test_ok(): pass")
            out = os.path.join(td, "out dir", "output.txt")
            rc = run_and_capture(test_py, out)
            assert rc == 0
            with open(out, encoding="utf-8") as f:
                content = f.read()
            expected_cmd = subprocess.list2cmdline(
                [sys.executable, "-m", "pytest", test_py, "-vv"]
            )
            first_line = content.split("\n")[0]
            expected_first = f"TEST_COMMAND: {expected_cmd}"
            assert first_line == expected_first, (
                f"command line mismatch\n  expected: {expected_first}\n  got:      {first_line}"
            )
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════
# zip_builder.py
# ═══════════════════════════════════════════════════════════════════════

class TestValidateArcname:
    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="empty"):
            _validate_arcname("")

    def test_absolute_rejected(self):
        with pytest.raises(ValueError, match="absolute"):
            _validate_arcname("/abs.py")

    def test_parent_traversal_rejected(self):
        with pytest.raises(ValueError, match="parent"):
            _validate_arcname("../a.py")

    def test_forward_slash_directory_allowed(self):
        """dir/a.py is now allowed (only .. and absolute are rejected)."""
        _validate_arcname("dir/a.py")

    def test_backslash_directory_allowed(self):
        """dir\a.py is now allowed (only .. and absolute are rejected)."""
        _validate_arcname(r"dir\a.py")

    def test_zip_ext_rejected(self):
        with pytest.raises(ValueError, match=".zip"):
            _validate_arcname("file.zip")

    def test_drive_relative_rejected(self):
        with pytest.raises(ValueError, match="drive"):
            _validate_arcname("C:relative.py")

    def test_plain_filename_accepted(self):
        _validate_arcname("report.md")
        _validate_arcname("test.py")
        _validate_arcname("output.txt")


class TestBuildZipContentDetection:
    """ZIP content detection via zipfile.is_zipfile (handles all ZIP magics)."""

    def test_real_zip_rejected_by_build(self):
        td = tempfile.mkdtemp()
        try:
            zp = os.path.join(td, "real.zip")
            with zipfile.ZipFile(zp, "w") as z:
                z.writestr("x.txt", "hello")
            with pytest.raises(ValueError, match="ZIP file"):
                build_zip(os.path.join(td, "out.zip"), {"data.dat": zp})
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_renamed_zip_rejected_by_build(self):
        td = tempfile.mkdtemp()
        try:
            zp = os.path.join(td, "real.zip")
            with zipfile.ZipFile(zp, "w") as z:
                z.writestr("x.txt", "hello")
            renamed = os.path.join(td, "not_a_zip.dat")
            os.rename(zp, renamed)
            with pytest.raises(ValueError, match="ZIP file"):
                build_zip(os.path.join(td, "out.zip"), {"data.dat": renamed})
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_empty_zip_rejected_by_build(self):
        """Empty ZIP (PK\x05\x06 only) must be rejected via is_zipfile."""
        td = tempfile.mkdtemp()
        try:
            empty_zp = os.path.join(td, "empty.zip")
            with zipfile.ZipFile(empty_zp, "w") as z:
                pass  # no entries — still a valid ZIP with EOCD record
            renamed = os.path.join(td, "empty.dat")
            os.rename(empty_zp, renamed)
            with pytest.raises(ValueError, match="ZIP file"):
                build_zip(os.path.join(td, "out.zip"), {"payload.dat": renamed})
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_plain_file_accepted(self):
        td = tempfile.mkdtemp()
        try:
            f = os.path.join(td, "plain.txt")
            with open(f, "w") as fh:
                fh.write("hello world")
            zp = os.path.join(td, "out.zip")
            build_zip(zp, {"plain.txt": f})
            verify_zip(zp, ["plain.txt"])
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_verify_rejects_zip_content_in_entry(self):
        td = tempfile.mkdtemp()
        try:
            inner = os.path.join(td, "inner.zip")
            with zipfile.ZipFile(inner, "w") as z:
                z.writestr("x.txt", "hello")
            renamed = os.path.join(td, "notazip.dat")
            os.rename(inner, renamed)
            zp = os.path.join(td, "outer.zip")
            with zipfile.ZipFile(zp, "w") as z:
                with open(renamed, "rb") as fh:
                    z.writestr("payload.dat", fh.read())
            with pytest.raises(AssertionError, match="ZIP file.*content"):
                verify_zip(zp, ["payload.dat"])
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_verify_rejects_empty_zip_in_entry(self):
        """Empty ZIP as entry must also be rejected."""
        td = tempfile.mkdtemp()
        try:
            empty_zp = os.path.join(td, "empty.zip")
            with zipfile.ZipFile(empty_zp, "w") as z:
                pass  # valid empty ZIP (EOCD only)
            zp = os.path.join(td, "outer.zip")
            with zipfile.ZipFile(zp, "w") as z:
                with open(empty_zp, "rb") as fh:
                    z.writestr("payload.dat", fh.read())
            with pytest.raises(AssertionError, match="ZIP file.*content"):
                verify_zip(zp, ["payload.dat"])
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)


class TestBuildZipSameFileDetection:
    """Same-file detection via os.path.samefile + normcase/realpath fallback."""

    def test_rejects_source_equals_output_literal(self):
        td = tempfile.mkdtemp()
        try:
            zp = os.path.join(td, "same.zip")
            with pytest.raises(ValueError, match="output ZIP"):
                build_zip(zp, {"x.txt": zp})
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_rejects_different_path_same_file(self, monkeypatch):
        """Different paths resolved to the same real file via samefile."""
        td = tempfile.mkdtemp()
        try:
            real = os.path.join(td, "real.txt")
            with open(real, "w") as f:
                f.write("data")
            zp = os.path.join(td, "out.zip")
            alias = os.path.join(td, "alias.txt")
            with open(alias, "w") as f:
                f.write("other data")

            def fake_samefile(a, b):
                return True

            monkeypatch.setattr(os.path, "samefile", fake_samefile)
            with pytest.raises(ValueError, match="output ZIP"):
                build_zip(zp, {"x.txt": alias})
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_different_unrelated_file_allowed(self):
        td = tempfile.mkdtemp()
        try:
            src = os.path.join(td, "src.txt")
            with open(src, "w") as f:
                f.write("x")
            zp = os.path.join(td, "out.zip")
            build_zip(zp, {"src.txt": src})
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)


class TestBuildAndVerifyZip:
    def test_normal_zip_build_and_verify(self):
        td = tempfile.mkdtemp()
        try:
            a_py = os.path.join(td, "a_module.py")
            b_md = os.path.join(td, "b_doc.md")
            with open(a_py, "w") as f:
                f.write("x = 1")
            with open(b_md, "w") as f:
                f.write("# Header")
            zp = os.path.join(td, "out.zip")
            build_zip(zp, {"a_module.py": a_py, "b_doc.md": b_md})
            verify_zip(zp, ["a_module.py", "b_doc.md"])
            assert os.path.getsize(zp) > 0
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_rejects_missing_source(self):
        td = tempfile.mkdtemp()
        try:
            with pytest.raises(FileNotFoundError):
                build_zip(os.path.join(td, "out.zip"), {"x.py": os.path.join(td, "nope.py")})
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_rejects_nested_zip_by_extension(self):
        td = tempfile.mkdtemp()
        try:
            f = os.path.join(td, "some.txt")
            with open(f, "w") as fh:
                fh.write("x")
            with pytest.raises(ValueError, match=".zip"):
                build_zip(os.path.join(td, "out.zip"), {"inner.zip": f})
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_verify_rejects_wrong_namelist(self):
        td = tempfile.mkdtemp()
        try:
            f = os.path.join(td, "a.txt")
            with open(f, "w") as fh:
                fh.write("x")
            zp = os.path.join(td, "out.zip")
            build_zip(zp, {"a.txt": f})
            with pytest.raises(AssertionError, match="namelist"):
                verify_zip(zp, ["a.txt", "b.txt"])
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_verify_rejects_zero_size(self):
        td = tempfile.mkdtemp()
        try:
            zp = os.path.join(td, "bad.zip")
            with zipfile.ZipFile(zp, "w") as z:
                z.writestr("empty.txt", "")
            with pytest.raises(AssertionError, match="zero-size"):
                verify_zip(zp, ["empty.txt"])
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_verify_rejects_python_syntax_error(self):
        td = tempfile.mkdtemp()
        try:
            bad = os.path.join(td, "bad.py")
            with open(bad, "w") as f:
                f.write("def broken(  # unmatched paren")
            zp = os.path.join(td, "out.zip")
            build_zip(zp, {"bad.py": bad})
            with pytest.raises(AssertionError, match="ast.parse"):
                verify_zip(zp, ["bad.py"])
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════
# conftest.py
# ═══════════════════════════════════════════════════════════════════════

class TestConftestFixture:
    def test_assert_d_fixture_loaded(self, assert_d):
        """Verify pytest auto-loads assert_d from conftest.py."""
        assert_d({"x": 1}, {"x": 1})

    def test_assert_d_rejects_type_mismatch(self, assert_d):
        with pytest.raises(AssertionError, match="type"):
            assert_d({"v": True}, {"v": 1})


# ═══════════════════════════════════════════════════════════════════════
# Self-integrity checks
# ═══════════════════════════════════════════════════════════════════════

def test_test_file_self_parse():
    """This test file is valid Python."""
    with open(__file__, "r", encoding="utf-8") as f:
        ast.parse(f.read())


def test_test_file_no_skip_xfail():
    """No skip/xfail/importorskip in this test file."""
    with open(__file__, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in ("skip", "skipif", "xfail", "importorskip"):
                    raise AssertionError(f"line {node.lineno}: {node.func.attr}() not allowed")
            elif isinstance(node.func, ast.Name):
                if node.func.id in ("skip", "skipif", "xfail", "importorskip"):
                    raise AssertionError(f"line {node.lineno}: {node.func.id}() not allowed")
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Attribute) and dec.attr in ("skip", "skipif", "xfail", "importorskip"):
                    raise AssertionError(f"line {dec.lineno}: @{dec.attr} not allowed")
                if isinstance(dec, ast.Name) and dec.id in ("skip", "skipif", "xfail", "importorskip"):
                    raise AssertionError(f"line {dec.lineno}: @{dec.id} not allowed")
