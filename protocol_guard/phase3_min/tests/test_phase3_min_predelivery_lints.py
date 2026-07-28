"""Smoke + adversarial tests for L5 pre-delivery lint tools."""
import ast
import json
import os
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

LINT_MASTER_MAP = os.path.join(
    ROOT, "protocol_guard", "phase3_min", "lint_master_map.py"
)
LINT_DELIVERY_ZIP = os.path.join(
    ROOT, "protocol_guard", "phase3_min", "lint_delivery_zip.py"
)
LINT_FOCUSED_TEST = os.path.join(
    ROOT, "protocol_guard", "phase3_min", "lint_focused_test.py"
)
# F-005: Authoritative master map at reviews/
REAL_MAP = os.path.join(ROOT, "reviews", "PROJECT_CODEIFICATION_MASTER_MAP.md")


def _run_lint(script, args_list):
    cmd = [sys.executable, script] + args_list
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


# ═══════════════════════════════════════════════════════════════════════
# lint_master_map.py
# ═══════════════════════════════════════════════════════════════════════

def _parse_top_block_fields(map_path):
    """Parse the top current-state block of the master map (before '## 一、')."""
    with open(map_path, encoding="utf-8") as f:
        content = f.read()
    # Extract top block: from start to "## 一、"
    top = content.split("\n## 一、")[0] if "\n## 一、" in content else content
    fields = {}
    for line in top.split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if key in ("VERSION", "ACTIVE_TASK_ID", "ACTIVE_TASK_STATUS",
                       "UNIQUE_NEXT_ATOMIC_TASK", "CURRENT_NEXT_TASK",
                       "CURRENT_NEXT_ACTION"):
                if key in fields:
                    raise ValueError(f"Duplicate field {key} in top block")
                fields[key] = val
    # All 6 must be present
    for fld in ("VERSION", "ACTIVE_TASK_ID", "ACTIVE_TASK_STATUS",
                "UNIQUE_NEXT_ATOMIC_TASK", "CURRENT_NEXT_TASK",
                "CURRENT_NEXT_ACTION"):
        if fld not in fields:
            raise ValueError(f"Missing field {fld} in top block")
    return fields


def _make_base_args():
    fields = _parse_top_block_fields(REAL_MAP)
    return [
        "--map-path", REAL_MAP,
        "--expected-version", fields["VERSION"],
        "--expected-active-task", fields["ACTIVE_TASK_ID"],
        "--expected-active-status", fields["ACTIVE_TASK_STATUS"],
        "--expected-unique-next-atomic-task", fields["UNIQUE_NEXT_ATOMIC_TASK"],
        "--expected-next-task", fields["CURRENT_NEXT_TASK"],
        "--expected-next-action", fields["CURRENT_NEXT_ACTION"],
    ]


class TestLintMasterMap:
    @property
    def BASE_ARGS(self):
        return _make_base_args()

    def test_map_path_is_reviews(self):
        """REAL_MAP points to reviews/ copy, which must exist."""
        assert REAL_MAP == os.path.join(ROOT, "reviews", "PROJECT_CODEIFICATION_MASTER_MAP.md")
        assert os.path.exists(REAL_MAP), f"Map missing: {REAL_MAP}"

    def test_current_map_passes(self):
        rc, stdout, stderr = _run_lint(LINT_MASTER_MAP, self.BASE_ARGS)
        assert rc == 0, f"exit={rc} stdout={stdout} stderr={stderr}"
        assert "LINT_MASTER_MAP_STATUS: PASS" in stdout
        assert "THREE_CURRENT_STATE_BLOCKS_MATCH: True" in stdout
        assert stderr == ""

    def test_version_mismatch_fails(self):
        args = list(self.BASE_ARGS)
        args[args.index("--expected-version") + 1] = "R99"
        rc, stdout, stderr = _run_lint(LINT_MASTER_MAP, args)
        assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
        assert "MISMATCH" in stdout
        assert "MISMATCH_COUNT:" in stdout
        assert "Traceback" not in stderr

    def test_wrong_active_task_fails(self):
        args = list(self.BASE_ARGS)
        args[args.index("--expected-active-task") + 1] = "WRONG_TASK"
        rc, stdout, stderr = _run_lint(LINT_MASTER_MAP, args)
        assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
        assert "MISMATCH" in stdout
        assert "Traceback" not in stderr

    def test_wrong_active_status_fails(self):
        args = list(self.BASE_ARGS)
        args[args.index("--expected-active-status") + 1] = "WRONG_STATUS"
        rc, stdout, stderr = _run_lint(LINT_MASTER_MAP, args)
        assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
        assert "MISMATCH" in stdout
        assert "Traceback" not in stderr

    def test_wrong_unique_next_atomic_task_fails(self):
        args = list(self.BASE_ARGS)
        args[args.index("--expected-unique-next-atomic-task") + 1] = "WRONG_UNIQUE"
        rc, stdout, stderr = _run_lint(LINT_MASTER_MAP, args)
        assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
        assert "MISMATCH" in stdout
        assert "Traceback" not in stderr

    def test_wrong_next_task_fails(self):
        args = list(self.BASE_ARGS)
        args[args.index("--expected-next-task") + 1] = "WRONG_NEXT"
        rc, stdout, stderr = _run_lint(LINT_MASTER_MAP, args)
        assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
        assert "MISMATCH" in stdout
        assert "Traceback" not in stderr

    def test_wrong_next_action_fails(self):
        args = list(self.BASE_ARGS)
        args[args.index("--expected-next-action") + 1] = "Wrong action text"
        rc, stdout, stderr = _run_lint(LINT_MASTER_MAP, args)
        assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
        assert "MISMATCH" in stdout
        assert "Traceback" not in stderr

    def test_missing_field_fails(self):
        td = tempfile.mkdtemp()
        try:
            mp = os.path.join(td, "map.md")
            with open(mp, "w", encoding="utf-8") as f:
                f.write("VERSION: R56\n")
                f.write("ACTIVE_TASK_ID: ANIMATION_STATE_E\n")
                f.write("ACTIVE_TASK_STATUS: AUTHORIZED_NOT_STARTED\n")
            args = [
                "--map-path", mp,
                "--expected-version", "R56",
                "--expected-active-task", "ANIMATION_STATE_E",
                "--expected-active-status", "AUTHORIZED_NOT_STARTED",
                "--expected-unique-next-atomic-task", "MISSING_FIELD",
                "--expected-next-task", "MISSING_FIELD",
                "--expected-next-action", "Missing field test",
            ]
            rc, stdout, stderr = _run_lint(LINT_MASTER_MAP, args)
            assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "MISSING" in stdout
            assert "Traceback" not in stderr
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_three_block_conflict_fails(self):
        td = tempfile.mkdtemp()
        try:
            mp = os.path.join(td, "map.md")
            with open(mp, "w", encoding="utf-8") as f:
                f.write("VERSION: R56\n")
                f.write("ACTIVE_TASK_ID: TASK_A\n")
                f.write("ACTIVE_TASK_STATUS: STATUS_A\n")
                f.write("UNIQUE_NEXT_ATOMIC_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_ACTION: Action A\n")
                f.write("## 十一、\n")
                f.write("ACTIVE_TASK_ID: TASK_A\n")
                f.write("ACTIVE_TASK_STATUS: STATUS_A\n")
                f.write("UNIQUE_NEXT_ATOMIC_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_ACTION: Action A\n")
                f.write("## 十五、\n")
                f.write("ACTIVE_TASK_ID: TASK_B\n")
                f.write("ACTIVE_TASK_STATUS: STATUS_A\n")
                f.write("UNIQUE_NEXT_ATOMIC_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_ACTION: Action A\n")
            args = [
                "--map-path", mp,
                "--expected-version", "R56",
                "--expected-active-task", "TASK_A",
                "--expected-active-status", "STATUS_A",
                "--expected-unique-next-atomic-task", "TASK_A",
                "--expected-next-task", "TASK_A",
                "--expected-next-action", "Action A",
            ]
            rc, stdout, stderr = _run_lint(LINT_MASTER_MAP, args)
            assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "CONFLICT" in stdout
            assert "Traceback" not in stderr
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_occurrence_count_wrong_fails(self):
        td = tempfile.mkdtemp()
        try:
            mp = os.path.join(td, "map.md")
            with open(mp, "w", encoding="utf-8") as f:
                f.write("VERSION: R56\n")
                f.write("ACTIVE_TASK_ID: TASK_A\n")
                f.write("ACTIVE_TASK_STATUS: STATUS_A\n")
                f.write("UNIQUE_NEXT_ATOMIC_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_ACTION: Action A\n")
                f.write("## 十一、\n")
                f.write("ACTIVE_TASK_ID: TASK_A\n")
                f.write("ACTIVE_TASK_STATUS: STATUS_A\n")
                f.write("UNIQUE_NEXT_ATOMIC_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_ACTION: Action A\n")
                # Only 2 occurrences of each state field, not 3
            args = [
                "--map-path", mp,
                "--expected-version", "R56",
                "--expected-active-task", "TASK_A",
                "--expected-active-status", "STATUS_A",
                "--expected-unique-next-atomic-task", "TASK_A",
                "--expected-next-task", "TASK_A",
                "--expected-next-action", "Action A",
            ]
            rc, stdout, stderr = _run_lint(LINT_MASTER_MAP, args)
            assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "OCCURRENCE_COUNT" in stdout
            assert "Traceback" not in stderr
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_three_blocks_all_at_top_fails(self):
        """All three state blocks in TOP with no §11 or §15 blocks must fail."""
        td = tempfile.mkdtemp()
        try:
            mp = os.path.join(td, "map.md")
            with open(mp, "w", encoding="utf-8") as f:
                f.write("VERSION: R56\n")
                for _ in range(3):
                    f.write("ACTIVE_TASK_ID: TASK_A\n")
                    f.write("ACTIVE_TASK_STATUS: STATUS_A\n")
                    f.write("UNIQUE_NEXT_ATOMIC_TASK: TASK_A\n")
                    f.write("CURRENT_NEXT_TASK: TASK_A\n")
                    f.write("CURRENT_NEXT_ACTION: Action A\n")
                    f.write("\n")
            args = [
                "--map-path", mp,
                "--expected-version", "R56",
                "--expected-active-task", "TASK_A",
                "--expected-active-status", "STATUS_A",
                "--expected-unique-next-atomic-task", "TASK_A",
                "--expected-next-task", "TASK_A",
                "--expected-next-action", "Action A",
            ]
            rc, stdout, stderr = _run_lint(LINT_MASTER_MAP, args)
            assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "SECTION_11_BLOCK_VALID: False" in stdout
            assert "SECTION_15_BLOCK_VALID: False" in stdout
            assert "Traceback" not in stderr
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_prefix_impostor_fields_not_counted(self):
        """OLD_ACTIVE_TASK_ID etc. must not count. Fake-only fails; valid+fake passes."""
        td = tempfile.mkdtemp()
        try:
            # Part A: prefix-only fake fields → must fail
            mp_a = os.path.join(td, "map_fake_only.md")
            with open(mp_a, "w", encoding="utf-8") as f:
                f.write("VERSION: R56\n")
                f.write("OLD_ACTIVE_TASK_ID: OLD_VALUE\n")
                f.write("PREVIOUS_ACTIVE_TASK_STATUS: OLD_VALUE\n")
                f.write("XUNIQUE_NEXT_ATOMIC_TASK: OLD_VALUE\n")
                f.write("OLD_CURRENT_NEXT_TASK: OLD_VALUE\n")
                f.write("PREVIOUS_CURRENT_NEXT_ACTION: Old action\n")
                f.write("\n## 十一、\n")
                f.write("OLD_ACTIVE_TASK_ID: OLD_VALUE\n")
                f.write("PREVIOUS_CURRENT_NEXT_ACTION: Old action\n")
                f.write("\n## 十五、\n")
                f.write("OLD_ACTIVE_TASK_ID: OLD_VALUE\n")
                f.write("PREVIOUS_CURRENT_NEXT_ACTION: Old action\n")
            args_fake = [
                "--map-path", mp_a,
                "--expected-version", "R56",
                "--expected-active-task", "TASK_A",
                "--expected-active-status", "STATUS_A",
                "--expected-unique-next-atomic-task", "TASK_A",
                "--expected-next-task", "TASK_A",
                "--expected-next-action", "Action A",
            ]
            rc_a, stdout_a, stderr_a = _run_lint(LINT_MASTER_MAP, args_fake)
            assert rc_a == 1, f"Part A exit={rc_a} stdout={stdout_a} stderr={stderr_a}"
            assert "MISSING" in stdout_a
            assert "Traceback" not in stderr_a

            # Part B: valid fields + prefix impostors → must pass
            mp_b = os.path.join(td, "map_valid_plus_fake.md")
            with open(mp_b, "w", encoding="utf-8") as f:
                f.write("VERSION: R56\n")
                f.write("ACTIVE_TASK_ID: TASK_A\n")
                f.write("ACTIVE_TASK_STATUS: STATUS_A\n")
                f.write("UNIQUE_NEXT_ATOMIC_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_ACTION: Action A\n")
                f.write("OLD_ACTIVE_TASK_ID: SHOULD_BE_IGNORED\n")
                f.write("\n## 十一、当前唯一下一步\n")
                f.write("ACTIVE_TASK_ID: TASK_A\n")
                f.write("ACTIVE_TASK_STATUS: STATUS_A\n")
                f.write("UNIQUE_NEXT_ATOMIC_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_ACTION: Action A\n")
                f.write("PREVIOUS_CURRENT_NEXT_ACTION: SHOULD_BE_IGNORED\n")
                f.write("\n## 十五、当前状态摘要\n")
                f.write("ACTIVE_TASK_ID: TASK_A\n")
                f.write("ACTIVE_TASK_STATUS: STATUS_A\n")
                f.write("UNIQUE_NEXT_ATOMIC_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_ACTION: Action A\n")
                f.write("XUNIQUE_NEXT_ATOMIC_TASK: SHOULD_BE_IGNORED\n")
            args_valid = [
                "--map-path", mp_b,
                "--expected-version", "R56",
                "--expected-active-task", "TASK_A",
                "--expected-active-status", "STATUS_A",
                "--expected-unique-next-atomic-task", "TASK_A",
                "--expected-next-task", "TASK_A",
                "--expected-next-action", "Action A",
            ]
            rc_b, stdout_b, stderr_b = _run_lint(LINT_MASTER_MAP, args_valid)
            assert rc_b == 0, f"Part B exit={rc_b} stdout={stdout_b} stderr={stderr_b}"
            assert "LINT_MASTER_MAP_STATUS: PASS" in stdout_b
            assert "Traceback" not in stderr_b
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_extra_formal_field_outside_three_blocks_fails(self):
        """A 4th occurrence of ACTIVE_TASK_ID outside the three blocks must fail."""
        td = tempfile.mkdtemp()
        try:
            mp = os.path.join(td, "map.md")
            with open(mp, "w", encoding="utf-8") as f:
                f.write("VERSION: R56\n")
                f.write("ACTIVE_TASK_ID: TASK_A\n")
                f.write("ACTIVE_TASK_STATUS: STATUS_A\n")
                f.write("UNIQUE_NEXT_ATOMIC_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_ACTION: Action A\n")
                f.write("\n## 十一、当前唯一下一步\n")
                f.write("ACTIVE_TASK_ID: TASK_A\n")
                f.write("ACTIVE_TASK_STATUS: STATUS_A\n")
                f.write("UNIQUE_NEXT_ATOMIC_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_ACTION: Action A\n")
                f.write("\n## 十五、当前状态摘要\n")
                f.write("ACTIVE_TASK_ID: TASK_A\n")
                f.write("ACTIVE_TASK_STATUS: STATUS_A\n")
                f.write("UNIQUE_NEXT_ATOMIC_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_ACTION: Action A\n")
                f.write("\n## 十六、附录\n")
                f.write("ACTIVE_TASK_ID: TASK_A\n")
            args = [
                "--map-path", mp, "--expected-version", "R56",
                "--expected-active-task", "TASK_A",
                "--expected-active-status", "STATUS_A",
                "--expected-unique-next-atomic-task", "TASK_A",
                "--expected-next-task", "TASK_A",
                "--expected-next-action", "Action A",
            ]
            rc, stdout, stderr = _run_lint(LINT_MASTER_MAP, args)
            assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "OCCURRENCE_COUNTS_MATCH: False" in stdout
            assert "OCCURRENCE_COUNT" in stdout
            assert "Traceback" not in stderr
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_section_21_not_accepted_as_section_11(self):
        """Section 二十一、must not be treated as section 十一、."""
        td = tempfile.mkdtemp()
        try:
            mp = os.path.join(td, "map.md")
            with open(mp, "w", encoding="utf-8") as f:
                f.write("VERSION: R56\n")
                f.write("ACTIVE_TASK_ID: TASK_A\n")
                f.write("ACTIVE_TASK_STATUS: STATUS_A\n")
                f.write("UNIQUE_NEXT_ATOMIC_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_ACTION: Action A\n")
                f.write("\n## 二十一、其他内容\n")
                f.write("ACTIVE_TASK_ID: TASK_A\n")
                f.write("ACTIVE_TASK_STATUS: STATUS_A\n")
                f.write("UNIQUE_NEXT_ATOMIC_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_ACTION: Action A\n")
                f.write("\n## 十五、当前状态摘要\n")
                f.write("ACTIVE_TASK_ID: TASK_A\n")
                f.write("ACTIVE_TASK_STATUS: STATUS_A\n")
                f.write("UNIQUE_NEXT_ATOMIC_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_ACTION: Action A\n")
            args = [
                "--map-path", mp, "--expected-version", "R56",
                "--expected-active-task", "TASK_A",
                "--expected-active-status", "STATUS_A",
                "--expected-unique-next-atomic-task", "TASK_A",
                "--expected-next-task", "TASK_A",
                "--expected-next-action", "Action A",
            ]
            rc, stdout, stderr = _run_lint(LINT_MASTER_MAP, args)
            assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "SECTION_11_BLOCK_VALID: False" in stdout
            assert "Traceback" not in stderr
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_section_25_not_accepted_as_section_15(self):
        """Section 二十五、must not be treated as section 十五、."""
        td = tempfile.mkdtemp()
        try:
            mp = os.path.join(td, "map.md")
            with open(mp, "w", encoding="utf-8") as f:
                f.write("VERSION: R56\n")
                f.write("ACTIVE_TASK_ID: TASK_A\n")
                f.write("ACTIVE_TASK_STATUS: STATUS_A\n")
                f.write("UNIQUE_NEXT_ATOMIC_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_ACTION: Action A\n")
                f.write("\n## 十一、当前唯一下一步\n")
                f.write("ACTIVE_TASK_ID: TASK_A\n")
                f.write("ACTIVE_TASK_STATUS: STATUS_A\n")
                f.write("UNIQUE_NEXT_ATOMIC_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_ACTION: Action A\n")
                f.write("\n## 二十五、其他内容\n")
                f.write("ACTIVE_TASK_ID: TASK_A\n")
                f.write("ACTIVE_TASK_STATUS: STATUS_A\n")
                f.write("UNIQUE_NEXT_ATOMIC_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_TASK: TASK_A\n")
                f.write("CURRENT_NEXT_ACTION: Action A\n")
            args = [
                "--map-path", mp, "--expected-version", "R56",
                "--expected-active-task", "TASK_A",
                "--expected-active-status", "STATUS_A",
                "--expected-unique-next-atomic-task", "TASK_A",
                "--expected-next-task", "TASK_A",
                "--expected-next-action", "Action A",
            ]
            rc, stdout, stderr = _run_lint(LINT_MASTER_MAP, args)
            assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "SECTION_15_BLOCK_VALID: False" in stdout
            assert "Traceback" not in stderr
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════
# lint_delivery_zip.py
# ═══════════════════════════════════════════════════════════════════════

class TestLintDeliveryZip:
    def _make_zip(self, entries):
        td = tempfile.mkdtemp()
        zp = os.path.join(td, "test.zip")
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
            for arc, content in entries.items():
                z.writestr(arc, content)
        return zp, td

    def _run(self, zip_path, entries):
        args = ["--zip-path", zip_path]
        for e in entries:
            args.extend(["--expected-entry", e])
        return _run_lint(LINT_DELIVERY_ZIP, args)

    def test_valid_zip_with_flat_files_passes(self):
        zp, td = self._make_zip({"a.py": "x = 1", "b.md": "# hello"})
        try:
            rc, stdout, stderr = self._run(zp, ["a.py", "b.md"])
            assert rc == 0, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "LINT_DELIVERY_ZIP_STATUS: PASS" in stdout
            assert "ZIP_VERIFIED: TRUE" in stdout
            assert stderr == ""
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_missing_file_fails(self):
        zp, td = self._make_zip({"a.py": "x = 1"})
        try:
            rc, stdout, stderr = self._run(zp, ["a.py", "b.md"])
            assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "LINT_DELIVERY_ZIP_STATUS: FAIL" in stdout
            assert "namelist" in stdout.lower()
            assert "Traceback" not in stderr
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_extra_file_fails(self):
        zp, td = self._make_zip({"a.py": "x = 1", "b.md": "# h"})
        try:
            rc, stdout, stderr = self._run(zp, ["a.py"])
            assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "namelist" in stdout.lower()
            assert "Traceback" not in stderr
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_duplicate_expected_entry_fails(self):
        zp, td = self._make_zip({"a.py": "x = 1"})
        try:
            rc, stdout, stderr = self._run(zp, ["a.py", "a.py"])
            assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "duplicate" in stdout.lower()
            assert "Traceback" not in stderr
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_bad_zip_fails(self):
        td = tempfile.mkdtemp()
        try:
            zp = os.path.join(td, "bad.zip")
            with open(zp, "w") as f:
                f.write("not a zip")
            rc, stdout, stderr = self._run(zp, ["a.py"])
            assert rc == 1
            assert "LINT_DELIVERY_ZIP_STATUS: FAIL" in stdout
            assert "bad zip file" in stdout.lower()
            assert "Traceback" not in stderr
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_python_syntax_error_fails(self):
        zp, td = self._make_zip({"bad.py": "def broken("})
        try:
            rc, stdout, stderr = self._run(zp, ["bad.py"])
            assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "ast" in stdout.lower()
            assert "Traceback" not in stderr
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_zero_size_zip_fails(self):
        td = tempfile.mkdtemp()
        try:
            zp = os.path.join(td, "empty.zip")
            with open(zp, "w") as f:
                pass
            rc, stdout, stderr = self._run(zp, ["a.py"])
            assert rc == 1
            assert "LINT_DELIVERY_ZIP_STATUS: FAIL" in stdout
            assert "zero-size" in stdout.lower()
            assert "Traceback" not in stderr
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_expected_entry_with_absolute_fails(self):
        td = tempfile.mkdtemp()
        try:
            zp = os.path.join(td, "t.zip")
            with zipfile.ZipFile(zp, "w") as z:
                z.writestr("a.py", "x=1")
            rc, stdout, stderr = _run_lint(LINT_DELIVERY_ZIP, [
                "--zip-path", zp, "--expected-entry", "/abs/a.py",
            ])
            assert rc == 2, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "absolute" in stderr.lower()
            assert "Traceback" not in stderr
            assert stdout == ""
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    # F-004A: reviews/ path ZIP test (calls lint, asserts PASS)
    def test_drive_relative_expected_entry_fails(self):
        td = tempfile.mkdtemp()
        try:
            zp = os.path.join(td, "t.zip")
            with zipfile.ZipFile(zp, "w") as z:
                z.writestr("a.py", "x=1")
            rc, stdout, stderr = _run_lint(LINT_DELIVERY_ZIP, [
                "--zip-path", zp, "--expected-entry", "C:relative.py",
            ])
            assert rc == 2, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "drive" in stderr.lower()
            assert "Traceback" not in stderr
            assert stdout == ""
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_reviews_path_zip_passes(self):
        zp, td = self._make_zip({
            "reviews/example.md": "# reviews markdown",
            "source.py": "x = 1",
        })
        try:
            rc, stdout, stderr = self._run(zp, ["reviews/example.md", "source.py"])
            assert rc == 0, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "LINT_DELIVERY_ZIP_STATUS: PASS" in stdout
            assert "ZIP_NAMELIST_EXACT: TRUE" in stdout
            assert "ZIP_VERIFIED: TRUE" in stdout
            assert stderr == ""
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    # F-004A: Flattened path (expected reviews/x but ZIP has flat x)
    def test_flattened_path_rejected(self):
        zp, td = self._make_zip({"example.md": "# md", "source.py": "x = 1"})
        try:
            rc, stdout, stderr = self._run(zp, ["reviews/example.md", "source.py"])
            assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "LINT_DELIVERY_ZIP_STATUS: FAIL" in stdout
            assert "namelist" in stdout.lower()
            assert "Traceback" not in stderr
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    # F-004B: Directory entry must be caught specifically
    def test_directory_entry_rejected(self):
        td = tempfile.mkdtemp()
        try:
            zp = os.path.join(td, "d.zip")
            with zipfile.ZipFile(zp, "w") as z:
                z.writestr("reviews/", "")
                z.writestr("reviews/a.py", "x=1")
            rc, stdout, stderr = _run_lint(LINT_DELIVERY_ZIP, [
                "--zip-path", zp,
                "--expected-entry", "reviews/",
                "--expected-entry", "reviews/a.py",
            ])
            assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "LINT_DELIVERY_ZIP_STATUS: FAIL" in stdout
            assert "directory" in stdout.lower(), f"no 'directory' in: {stdout}"
            assert "Traceback" not in stderr
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    # F-004C: Inner ZIP detected by content (renamed to non-.zip extension)
    def test_inner_zip_rejected(self):
        td = tempfile.mkdtemp()
        try:
            inner = os.path.join(td, "inner.zip")
            with zipfile.ZipFile(inner, "w") as z:
                z.writestr("x.txt", "hello")
            renamed = os.path.join(td, "payload.dat")
            import shutil
            shutil.copy2(inner, renamed)
            zp = os.path.join(td, "outer.zip")
            with zipfile.ZipFile(zp, "w") as z:
                z.write(renamed, "payload.dat")
            rc, stdout, stderr = _run_lint(LINT_DELIVERY_ZIP, [
                "--zip-path", zp, "--expected-entry", "payload.dat",
            ])
            assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "LINT_DELIVERY_ZIP_STATUS: FAIL" in stdout
            assert "zip file" in stdout.lower() and "content" in stdout.lower(), (
                f"no 'ZIP file (by content)' in: {stdout}"
            )
            assert "Traceback" not in stderr
        finally:
            shutil.rmtree(td, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════
# lint_focused_test.py
# ═══════════════════════════════════════════════════════════════════════

class TestLintFocusedTest:
    def _run(self, paths, policy_path=None):
        args = []
        for p in paths:
            args.extend(["--test-path", p])
        if policy_path:
            args.extend(["--policy-json", policy_path])
        return _run_lint(LINT_FOCUSED_TEST, args)

    def test_normal_test_passes(self):
        td = tempfile.mkdtemp()
        try:
            tp = os.path.join(td, "test_ok.py")
            with open(tp, "w") as f:
                f.write("def test_pass(): assert 1 == 1")
            rc, stdout, stderr = self._run([tp])
            assert rc == 0, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "LINT_FOCUSED_TEST_STATUS: PASS" in stdout
            assert stderr == ""
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_ast_parse_failure_fails(self):
        td = tempfile.mkdtemp()
        try:
            tp = os.path.join(td, "test_bad.py")
            with open(tp, "w") as f:
                f.write("def broken(")
            rc, stdout, stderr = self._run([tp])
            assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "LINT_FOCUSED_TEST_STATUS: FAIL" in stdout
            assert "Traceback" not in stderr
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_skip_decorator_fails(self):
        td = tempfile.mkdtemp()
        try:
            tp = os.path.join(td, "test_skip.py")
            with open(tp, "w") as f:
                f.write("import pytest\n@pytest.mark.skip\ndef test_x(): pass")
            rc, stdout, stderr = self._run([tp])
            assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "SKIP_XFAIL" in stdout
            assert "SKIP_XFAIL_VIOLATION_COUNT: 1" in stdout
            assert "TOTAL_VIOLATIONS: 1" in stdout
            assert "Traceback" not in stderr
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_skipif_decorator_fails(self):
        td = tempfile.mkdtemp()
        try:
            tp = os.path.join(td, "test_sf.py")
            with open(tp, "w") as f:
                f.write("import pytest\n@pytest.mark.skipif(True, reason='')\ndef test_x(): pass")
            rc, stdout, stderr = self._run([tp])
            assert rc == 1
            assert "LINT_FOCUSED_TEST_STATUS: FAIL" in stdout
            assert "SKIP_XFAIL" in stdout
            assert "skipif" in stdout.lower()
            assert "SKIP_XFAIL_VIOLATION_COUNT: 1" in stdout
            assert "TOTAL_VIOLATIONS: 1" in stdout
            assert "Traceback" not in stderr
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_xfail_decorator_fails(self):
        td = tempfile.mkdtemp()
        try:
            tp = os.path.join(td, "test_xf.py")
            with open(tp, "w") as f:
                f.write("import pytest\n@pytest.mark.xfail\ndef test_x(): pass")
            rc, stdout, stderr = self._run([tp])
            assert rc == 1
            assert "LINT_FOCUSED_TEST_STATUS: FAIL" in stdout
            assert "SKIP_XFAIL" in stdout
            assert "xfail" in stdout.lower()
            assert "SKIP_XFAIL_VIOLATION_COUNT: 1" in stdout
            assert "TOTAL_VIOLATIONS: 1" in stdout
            assert "Traceback" not in stderr
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_importorskip_call_fails(self):
        td = tempfile.mkdtemp()
        try:
            tp = os.path.join(td, "test_ios.py")
            with open(tp, "w") as f:
                f.write("import pytest\npytest.importorskip('nonexistent')\ndef test_x(): pass")
            rc, stdout, stderr = self._run([tp])
            assert rc == 1
            assert "LINT_FOCUSED_TEST_STATUS: FAIL" in stdout
            assert "SKIP_XFAIL" in stdout
            assert "importorskip" in stdout.lower()
            assert "SKIP_XFAIL_VIOLATION_COUNT: 1" in stdout
            assert "TOTAL_VIOLATIONS: 1" in stdout
            assert "Traceback" not in stderr
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_bare_return_fails(self):
        td = tempfile.mkdtemp()
        try:
            tp = os.path.join(td, "test_br.py")
            with open(tp, "w") as f:
                f.write("def test_x():\n return")
            rc, stdout, stderr = self._run([tp])
            assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "EARLY_RETURN" in stdout
            assert "EARLY_RETURN_COUNT: 1" in stdout
            assert "TOTAL_VIOLATIONS: 1" in stdout
            assert "Traceback" not in stderr
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_valued_return_fails(self):
        td = tempfile.mkdtemp()
        try:
            tp = os.path.join(td, "test_vr.py")
            with open(tp, "w") as f:
                f.write("def test_x():\n return 42")
            rc, stdout, stderr = self._run([tp])
            assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "EARLY_RETURN" in stdout
            assert "EARLY_RETURN_COUNT: 1" in stdout
            assert "TOTAL_VIOLATIONS: 1" in stdout
            assert "Traceback" not in stderr
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_policy_assert_literal_pass(self):
        td = tempfile.mkdtemp()
        try:
            tp = os.path.join(td, "test_pol.py")
            with open(tp, "w") as f:
                f.write("def test_x():\n v = ['VISIBILITY_WRITE']\n assert 'VISIBILITY_WRITE' in v")
            pol = os.path.join(td, "policy.json")
            with open(pol, "w") as f:
                json.dump({"required_assert_literals": {"test_x": ["VISIBILITY_WRITE"]}}, f)
            rc, stdout, stderr = self._run([tp], pol)
            assert rc == 0, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "LINT_FOCUSED_TEST_STATUS: PASS" in stdout
            assert stderr == ""
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_assert_msg_literal_fails(self):
        td = tempfile.mkdtemp()
        try:
            tp = os.path.join(td, "test_msg.py")
            with open(tp, "w") as f:
                f.write("def test_x():\n assert True, 'VISIBILITY_WRITE'")
            pol = os.path.join(td, "policy.json")
            with open(pol, "w") as f:
                json.dump({"required_assert_literals": {"test_x": ["VISIBILITY_WRITE"]}}, f)
            rc, stdout, stderr = self._run([tp], pol)
            assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "POLICY_ASSERT" in stdout
            assert "ASSERT_POLICY_FAILURE_COUNT: 1" in stdout
            assert "TOTAL_VIOLATIONS: 1" in stdout
            assert "Traceback" not in stderr
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_policy_assert_literal_in_assignment_only_fails(self):
        td = tempfile.mkdtemp()
        try:
            tp = os.path.join(td, "test_pol2.py")
            with open(tp, "w") as f:
                f.write("def test_x():\n x = 'VISIBILITY_WRITE'\n assert True")
            pol = os.path.join(td, "policy.json")
            with open(pol, "w") as f:
                json.dump({"required_assert_literals": {"test_x": ["VISIBILITY_WRITE"]}}, f)
            rc, stdout, stderr = self._run([tp], pol)
            assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "POLICY_ASSERT" in stdout
            assert "ASSERT_POLICY_FAILURE_COUNT: 1" in stdout
            assert "TOTAL_VIOLATIONS: 1" in stdout
            assert "Traceback" not in stderr
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_policy_assignment_pass(self):
        td = tempfile.mkdtemp()
        try:
            tp = os.path.join(td, "test_assign.py")
            with open(tp, "w") as f:
                f.write("def test_x():\n alias = vis\n assert alias")
            pol = os.path.join(td, "policy.json")
            with open(pol, "w") as f:
                json.dump({"required_assignments": {"test_x": [{"target": "alias", "source": "vis"}]}}, f)
            rc, stdout, stderr = self._run([tp], pol)
            assert rc == 0, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "LINT_FOCUSED_TEST_STATUS: PASS" in stdout
            assert stderr == ""
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_policy_assignment_missing_fails(self):
        td = tempfile.mkdtemp()
        try:
            tp = os.path.join(td, "test_assign2.py")
            with open(tp, "w") as f:
                f.write("def test_x():\n x = 1\n assert x")
            pol = os.path.join(td, "policy.json")
            with open(pol, "w") as f:
                json.dump({"required_assignments": {"test_x": [{"target": "alias", "source": "vis"}]}}, f)
            rc, stdout, stderr = self._run([tp], pol)
            assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "POLICY_ASSIGN" in stdout
            assert "ASSIGNMENT_POLICY_FAILURE_COUNT: 1" in stdout
            assert "TOTAL_VIOLATIONS: 1" in stdout
            assert "Traceback" not in stderr
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_policy_call_pass(self):
        td = tempfile.mkdtemp()
        try:
            tp = os.path.join(td, "test_call.py")
            with open(tp, "w") as f:
                f.write("def test_x():\n alias = type('o',(),{})()\n alias.get('forbidden_key')\n assert 1")
            pol = os.path.join(td, "policy.json")
            with open(pol, "w") as f:
                json.dump({"required_calls": {"test_x": [{"receiver": "alias", "method": "get", "literal_args": ["forbidden_key"]}]}}, f)
            rc, stdout, stderr = self._run([tp], pol)
            assert rc == 0, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "LINT_FOCUSED_TEST_STATUS: PASS" in stdout
            assert stderr == ""
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_policy_call_wrong_receiver_fails(self):
        td = tempfile.mkdtemp()
        try:
            tp = os.path.join(td, "test_call2.py")
            with open(tp, "w") as f:
                f.write("def test_x():\n vis = {}\n vis.get('forbidden_key')\n assert 1")
            pol = os.path.join(td, "policy.json")
            with open(pol, "w") as f:
                json.dump({"required_calls": {"test_x": [{"receiver": "alias", "method": "get", "literal_args": ["forbidden_key"]}]}}, f)
            rc, stdout, stderr = self._run([tp], pol)
            assert rc == 1, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "POLICY_CALL" in stdout
            assert "CALL_POLICY_FAILURE_COUNT: 1" in stdout
            assert "TOTAL_VIOLATIONS: 1" in stdout
            assert "Traceback" not in stderr
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_invalid_policy_JSON_exits_2(self):
        td = tempfile.mkdtemp()
        try:
            tp = os.path.join(td, "test_any.py")
            with open(tp, "w") as f:
                f.write("def test_x(): pass")
            pol = os.path.join(td, "policy.json")
            with open(pol, "w") as f:
                f.write("not json")
            rc, stdout, stderr = _run_lint(LINT_FOCUSED_TEST, ["--test-path", tp, "--policy-json", pol])
            assert rc == 2, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "POLICY_JSON_INVALID" in stderr
            assert "Traceback" not in stderr
            assert stdout == ""
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)

    def test_policy_bad_schema_exits_2(self):
        td = tempfile.mkdtemp()
        try:
            tp = os.path.join(td, "test_any.py")
            with open(tp, "w") as f:
                f.write("def test_x(): pass")
            pol = os.path.join(td, "policy.json")
            with open(pol, "w") as f:
                json.dump({"required_assert_literals": {"test_x": [42]}}, f)
            rc, stdout, stderr = _run_lint(LINT_FOCUSED_TEST, ["--test-path", tp, "--policy-json", pol])
            assert rc == 2, f"exit={rc} stdout={stdout} stderr={stderr}"
            assert "POLICY_JSON_INVALID" in stderr
            assert "Traceback" not in stderr
            assert stdout == ""
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════
# Self-integrity
# ═══════════════════════════════════════════════════════════════════════

def test_test_file_self_parse():
    with open(__file__, "r", encoding="utf-8") as f:
        ast.parse(f.read())


def test_test_file_no_skip_xfail():
    with open(__file__, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in ("skip", "skipif", "xfail", "importorskip"):
                    raise AssertionError(f"line {node.lineno}: {node.func.attr}()")
            elif isinstance(node.func, ast.Name):
                if node.func.id in ("skip", "skipif", "xfail", "importorskip"):
                    raise AssertionError(f"line {node.lineno}: {node.func.id}()")
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            for dec in node.decorator_list:
                name = None
                if isinstance(dec, ast.Attribute):
                    name = dec.attr
                elif isinstance(dec, ast.Name):
                    name = dec.id
                if name in ("skip", "skipif", "xfail", "importorskip"):
                    raise AssertionError(f"line {dec.lineno}: @{name}")
