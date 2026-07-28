"""Unified ZIP builder with built-in verification.

build_zip(zip_path, files_dict)  — create ZIP from {arcname: source_path}
verify_zip(zip_path, expected_names) — comprehensive verification

Usage from packaging scripts:
    from protocol_guard.phase3_min.zip_builder import build_zip, verify_zip
    build_zip("output.zip", {"a.py": "src/a.py", "b.md": "reports/b.md"})
    verify_zip("output.zip", ["a.py", "b.md"])
"""

import ast
import io
import os
import zipfile


def _is_same_file(path_a, path_b):
    """Return True if path_a and path_b point to the same real file.

    Uses os.path.samefile when available; falls back to normalized
    realpath comparison on OSError (e.g. one path does not exist yet).
    """
    try:
        return os.path.samefile(path_a, path_b)
    except OSError:
        return os.path.normcase(os.path.realpath(path_a)) == os.path.normcase(os.path.realpath(path_b))


def _validate_arcname(arcname):
    """Raise ValueError if arcname is not a safe, plain filename."""
    if not arcname:
        raise ValueError(f"build_zip: empty arcname not allowed")
    if os.path.isabs(arcname) or arcname.startswith("/") or arcname.startswith("\\"):
        raise ValueError(f"build_zip: absolute path not allowed: {arcname}")
    # Reject drive-relative paths like C:relative.py (cross-platform)
    import ntpath
    drive, _ = ntpath.splitdrive(arcname)
    if drive:
        raise ValueError(f"build_zip: drive-relative path not allowed: {arcname}")
    if ".." in arcname.split("/") or ".." in arcname.split("\\"):
        raise ValueError(f"build_zip: parent traversal not allowed: {arcname}")
    if arcname.endswith("/"):
        raise ValueError(f"build_zip: directory entry not allowed: {arcname}")
    if arcname.lower().endswith(".zip"):
        raise ValueError(f"build_zip: .zip entry not allowed: {arcname}")


def build_zip(zip_path, files_dict):
    """Create a ZIP at zip_path from {arcname: source_path} mapping.

    Validates:
      - each arcname is a plain filename (no dirs, no .., no absolute)
      - each source exists, has size > 0, and is not the output ZIP
      - source content is not a ZIP file (via zipfile.is_zipfile)
    """
    for arcname, src in files_dict.items():
        _validate_arcname(arcname)
        if _is_same_file(src, zip_path):
            raise ValueError(f"build_zip: source cannot be the output ZIP: {src}")
        if not os.path.exists(src):
            raise FileNotFoundError(f"build_zip: source not found: {src}")
        if os.path.getsize(src) == 0:
            raise ValueError(f"build_zip: zero-size source: {src}")
        if zipfile.is_zipfile(src):
            raise ValueError(f"build_zip: source is a ZIP file (by content): {src}")

    os.makedirs(os.path.dirname(zip_path) or ".", exist_ok=True)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for arcname, src in sorted(files_dict.items()):
            z.write(src, arcname)


def verify_zip(zip_path, expected_names):
    """Verify a ZIP archive meets delivery standards.

    Checks:
      1. namelist matches expected_names exactly (sorted compare)
      2. Every entry has a safe arcname (no dirs, no .., no absolute)
      3. Every entry is readable and size > 0
      4. Every entry is not itself a ZIP (via zipfile.is_zipfile on data)
      5. Every .py entry passes ast.parse
      6. testzip() returns None (no corruption)
      7. No directory entries or nested ZIPs

    Returns None on success. Raises AssertionError on any violation.
    """
    expected = sorted(expected_names)

    with zipfile.ZipFile(zip_path, "r") as z:
        names = sorted(z.namelist())
        assert names == expected, (
            f"verify_zip: namelist mismatch\n  expected: {expected}\n  got:      {names}"
        )

        for n in names:
            _validate_arcname(n)

            data = z.read(n)
            assert len(data) > 0, f"verify_zip: zero-size entry: {n}"

            if zipfile.is_zipfile(io.BytesIO(data)):
                raise AssertionError(f"verify_zip: entry is a ZIP file (by content): {n}")

            if n.endswith(".py"):
                try:
                    ast.parse(data.decode("utf-8"))
                except SyntaxError as e:
                    raise AssertionError(f"verify_zip: ast.parse failed for {n}: {e}") from e

        corrupt = z.testzip()
        assert corrupt is None, f"verify_zip: testzip corruption at: {corrupt}"

    return None
