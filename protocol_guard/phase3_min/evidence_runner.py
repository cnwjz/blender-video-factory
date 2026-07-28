"""Standardized pytest evidence runner.

Produces a predictable output file capturing:
  - exact test command (via list2cmdline for correct space handling)
  - working directory
  - full stdout + stderr
  - pytest exit code

Usage:
    python evidence_runner.py <test_file> <output_path>
"""

import os
import subprocess
import sys


def run_and_capture(test_file, output_path):
    """Run pytest on test_file, write standardized evidence to output_path.

    Creates parent directories automatically.
    Returns the pytest exit code.
    """
    cwd = os.getcwd()
    cmd = [sys.executable, "-m", "pytest", test_file, "-vv"]

    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    combined = proc.stdout
    if proc.stderr:
        combined += "\n" + proc.stderr

    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"TEST_COMMAND: {subprocess.list2cmdline(cmd)}\n")
        f.write(f"CWD: {cwd}\n")
        f.write(combined)
        if not combined.endswith("\n"):
            f.write("\n")
        f.write(f"PYTEST_EXIT_CODE: {proc.returncode}\n")

    return proc.returncode


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <test_file> <output_path>")
        sys.exit(1)
    rc = run_and_capture(sys.argv[1], sys.argv[2])
    sys.exit(rc)
