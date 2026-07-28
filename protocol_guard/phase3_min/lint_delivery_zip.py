"""Lint a deliverable ZIP against expected entries.

Calls zip_builder.verify_zip() internally for namelist, size, ast.parse,
testzip checks. Adds duplicate detection and expected-entry validation.

Usage:
    python lint_delivery_zip.py \
        --zip-path reviews/UPLOAD_NEXT/.../upload.zip \
        --expected-entry PROJECT_CODEIFICATION_MASTER_MAP.md \
        --expected-entry reviews/14B_4A_VISIBILITY_I2_COMPLETION_RECORD.md \
        --expected-entry reviews/14B_4A_VISIBILITY_I2_STATUS_SYNC_REPORT.md

Exit codes: 0 = pass, 1 = ZIP verification failed, 2 = usage/IO error.
"""
import argparse
import os
import sys
import zipfile


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from protocol_guard.phase3_min.zip_builder import verify_zip


def main():
    parser = argparse.ArgumentParser(description="Lint deliverable ZIP")
    parser.add_argument("--zip-path", required=True)
    parser.add_argument("--expected-entry", action="append", default=[],
                        dest="expected_entries")
    args = parser.parse_args()

    # Validate expected entries
    if not args.expected_entries:
        print("ERROR: --expected-entry is required at least once", file=sys.stderr)
        sys.exit(2)

    # Check for duplicates in expected entries
    if len(args.expected_entries) != len(set(args.expected_entries)):
        seen = {}
        dups = []
        for e in args.expected_entries:
            if e in seen:
                dups.append(e)
            seen[e] = True
        print(f"LINT_DELIVERY_ZIP_STATUS: FAIL")
        print(f"ERROR: duplicate --expected-entry values: {dups}")
        sys.exit(1)

    # Validate each expected entry
    for entry in args.expected_entries:
        if not entry:
            print("ERROR: --expected-entry cannot be empty", file=sys.stderr)
            sys.exit(2)
        if os.path.isabs(entry) or entry.startswith("/") or entry.startswith("\\"):
            print(f"ERROR: --expected-entry cannot be absolute: {entry}", file=sys.stderr)
            sys.exit(2)
        import ntpath
        drive, _ = ntpath.splitdrive(entry)
        if drive:
            print(f"ERROR: --expected-entry cannot have drive letter: {entry}", file=sys.stderr)
            sys.exit(2)
        if ".." in entry.split("/") or ".." in entry.split("\\"):
            print(f"ERROR: --expected-entry cannot contain '..': {entry}", file=sys.stderr)
            sys.exit(2)

    # Check ZIP exists and is non-zero
    if not os.path.exists(args.zip_path):
        print(f"LINT_DELIVERY_ZIP_STATUS: FAIL")
        print(f"ERROR: ZIP not found: {args.zip_path}")
        sys.exit(1)
    if os.path.getsize(args.zip_path) == 0:
        print(f"LINT_DELIVERY_ZIP_STATUS: FAIL")
        print(f"ERROR: ZIP is zero-size: {args.zip_path}")
        sys.exit(1)

    # Check for duplicate entries in ZIP namelist
    try:
        with zipfile.ZipFile(args.zip_path, "r") as z:
            names = z.namelist()
            if len(names) != len(set(names)):
                dups = [n for n in names if names.count(n) > 1]
                print(f"LINT_DELIVERY_ZIP_STATUS: FAIL")
                print(f"ERROR: duplicate entries in ZIP: {list(set(dups))}")
                sys.exit(1)
    except zipfile.BadZipFile as e:
        print(f"LINT_DELIVERY_ZIP_STATUS: FAIL")
        print(f"ERROR: bad ZIP file: {e}")
        sys.exit(1)

    # Run verify_zip (covers: namelist match, size>0, ast.parse, testzip, no dirs, no nested ZIPs)
    try:
        verify_zip(args.zip_path, args.expected_entries)
    except (AssertionError, ValueError) as e:
        print(f"LINT_DELIVERY_ZIP_STATUS: FAIL")
        print(f"ZIP_VERIFIED: FALSE")
        print(f"ERROR: {e}")
        sys.exit(1)

    # All good
    print(f"LINT_DELIVERY_ZIP_STATUS: PASS")
    print(f"ZIP_ENTRY_COUNT: {len(args.expected_entries)}")
    print(f"EXPECTED_ENTRY_COUNT: {len(args.expected_entries)}")
    print(f"ZIP_NAMELIST_EXACT: TRUE")
    print(f"ZIP_TESTZIP_OK: TRUE")
    print(f"ZIP_VERIFIED: TRUE")
    sys.exit(0)


if __name__ == "__main__":
    main()
