"""Lint PROJECT_CODEIFICATION_MASTER_MAP.md for internal state consistency.

All expected values must be passed as CLI arguments. Nothing is hardcoded.

Exit codes: 0 = pass, 1 = content mismatch, 2 = usage/IO error.
"""
import argparse
import re
import sys


STATE_FIELDS = [
    "ACTIVE_TASK_ID",
    "ACTIVE_TASK_STATUS",
    "UNIQUE_NEXT_ATOMIC_TASK",
    "CURRENT_NEXT_TASK",
    "CURRENT_NEXT_ACTION",
]

# Line-start anchored, exact field name, colon. re.MULTILINE for ^ per-line.
FIELD_PATTERNS = {
    f: re.compile(r"^\s*" + f + r":\s*(.+)", re.MULTILINE) for f in STATE_FIELDS
}
VERSION_PATTERN = re.compile(r"^VERSION:\s*(\S+)", re.MULTILINE)

# Section header: "## N、..." or "## N. ..." where N is Chinese or Arabic numeral.
SECTION_HEADER_RE = re.compile(r"^##\s+([一二三四五六七八九十\d]+)[、.].*")


def read_map(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (FileNotFoundError, PermissionError) as e:
        print(f"ERROR: cannot read map: {e}", file=sys.stderr)
        sys.exit(2)


def find_sections(text):
    """Return list of (start_line, end_line, section_number_str, raw_title).

    Section 0 is TOP (before first header), with number_str="TOP".
    """
    lines = text.split("\n")
    sections = []
    current_start = 0
    current_number = "TOP"
    current_title = "TOP"
    for i, line in enumerate(lines):
        m = SECTION_HEADER_RE.match(line)
        if m:
            sections.append((current_start, i, current_number, current_title))
            current_start = i
            current_number = m.group(1)
            current_title = line.strip()
    sections.append((current_start, len(lines), current_number, current_title))
    return sections, lines


def get_section_block(sections, lines, exact_number):
    """Return block text for section whose number matches exact_number exactly."""
    for start, end, number_str, title in sections:
        if number_str == exact_number:
            return "\n".join(lines[start:end])
    return None


def check_fields_in_block(block_text, block_label):
    """Return (errors, found_values) for one block."""
    errors = []
    found_values = {}
    for field_name in STATE_FIELDS:
        pattern = FIELD_PATTERNS[field_name]
        matches = pattern.findall(block_text)
        if len(matches) == 0:
            errors.append(f"MISSING: {field_name} not found in {block_label}")
        elif len(matches) > 1:
            errors.append(
                f"DUPLICATE: {field_name} appears {len(matches)} times in {block_label}"
            )
        else:
            found_values[field_name] = matches[0].strip()
    return errors, found_values


def main():
    parser = argparse.ArgumentParser(description="Lint master map consistency")
    parser.add_argument("--map-path", required=True)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--expected-active-task", required=True)
    parser.add_argument("--expected-active-status", required=True)
    parser.add_argument("--expected-unique-next-atomic-task", required=True)
    parser.add_argument("--expected-next-task", required=True)
    parser.add_argument("--expected-next-action", required=True)
    args = parser.parse_args()

    expected_map = {
        "ACTIVE_TASK_ID": args.expected_active_task,
        "ACTIVE_TASK_STATUS": args.expected_active_status,
        "UNIQUE_NEXT_ATOMIC_TASK": args.expected_unique_next_atomic_task,
        "CURRENT_NEXT_TASK": args.expected_next_task,
        "CURRENT_NEXT_ACTION": args.expected_next_action,
    }

    text = read_map(args.map_path)
    sections, lines = find_sections(text)
    errors = []

    # ── VERSION ──
    version_matches = VERSION_PATTERN.findall(text)
    if len(version_matches) == 0:
        errors.append("MISSING: VERSION not found anywhere in map")
    elif len(version_matches) > 1:
        errors.append(
            f"OCCURRENCE_COUNT: VERSION appears {len(version_matches)} times, expected 1"
        )
    elif version_matches[0].strip() != args.expected_version:
        errors.append(
            f"MISMATCH: VERSION: expected '{args.expected_version}', "
            f"got '{version_matches[0].strip()}'"
        )

    # ── Three state blocks (exact section number matching) ──
    block_specs = [
        ("TOP", "TOP_BLOCK"),
        ("十一", "SECTION_11_BLOCK"),
        ("十五", "SECTION_15_BLOCK"),
    ]

    block_results = {}
    all_block_values = []
    occurrence_ok = True

    for exact_number, block_label in block_specs:
        block_text = get_section_block(sections, lines, exact_number)
        if block_text is None:
            display_names = {
                "TOP": "TOP (before first section header)",
                "十一": "SECTION_11 (## 十一、)",
                "十五": "SECTION_15 (## 十五、)",
            }
            errors.append(f"MISSING: {display_names[exact_number]} not found")
            block_results[block_label] = {"valid": False, "values": {}}
            continue

        block_errors, found_values = check_fields_in_block(block_text, block_label)
        errors.extend(block_errors)
        block_results[block_label] = {
            "valid": len(block_errors) == 0,
            "values": found_values,
        }
        if found_values:
            all_block_values.append(found_values)

    # ── Global occurrence counts (each field exactly 3) ──
    for field_name in STATE_FIELDS:
        pattern = FIELD_PATTERNS[field_name]
        count = len(pattern.findall(text))
        if count != 3:
            occurrence_ok = False
            errors.append(
                f"OCCURRENCE_COUNT: {field_name} appears {count} times, expected 3"
            )

    # ── Cross-block value consistency ──
    three_block_ok = all(
        block_results.get(bl, {}).get("valid", False)
        for bl in ["TOP_BLOCK", "SECTION_11_BLOCK", "SECTION_15_BLOCK"]
    )
    if three_block_ok and len(all_block_values) == 3:
        for field_name in STATE_FIELDS:
            vals = [bv[field_name] for bv in all_block_values]
            if len(set(vals)) != 1:
                three_block_ok = False
                details = "; ".join(
                    f"{bl}: '{v}'"
                    for bl, v in zip(
                        ["TOP_BLOCK", "SECTION_11_BLOCK", "SECTION_15_BLOCK"], vals
                    )
                )
                errors.append(
                    f"CONFLICT: {field_name} differs across blocks: {details}"
                )

    # ── Value matching against expectations ──
    if all_block_values:
        ref = all_block_values[0]
        for field_name in STATE_FIELDS:
            actual = ref.get(field_name, "")
            expected = expected_map[field_name]
            if actual and actual != expected:
                errors.append(
                    f"MISMATCH: {field_name}: expected '{expected}', got '{actual}'"
                )

    mismatch_count = len(errors)

    # ── Output ──
    print(f"LINT_MASTER_MAP_STATUS: {'PASS' if mismatch_count == 0 else 'FAIL'}")
    print(f"MAP_VERSION_MATCH: {args.expected_version}")
    print(f"ACTIVE_TASK_MATCH: {args.expected_active_task}")
    print(f"ACTIVE_STATUS_MATCH: {args.expected_active_status}")
    print(f"UNIQUE_NEXT_ATOMIC_TASK_MATCH: {args.expected_unique_next_atomic_task}")
    print(f"NEXT_TASK_MATCH: {args.expected_next_task}")
    print(f"NEXT_ACTION_MATCH: {args.expected_next_action}")
    print(f"TOP_BLOCK_VALID: {block_results.get('TOP_BLOCK', {}).get('valid', False)}")
    print(f"SECTION_11_BLOCK_VALID: {block_results.get('SECTION_11_BLOCK', {}).get('valid', False)}")
    print(f"SECTION_15_BLOCK_VALID: {block_results.get('SECTION_15_BLOCK', {}).get('valid', False)}")
    print(f"OCCURRENCE_COUNTS_MATCH: {occurrence_ok}")
    print(f"THREE_CURRENT_STATE_BLOCKS_MATCH: {three_block_ok}")
    print(f"MISMATCH_COUNT: {mismatch_count}")
    if errors:
        print(f"MISMATCH_LINES: {'; '.join(errors)}")
    else:
        print("MISMATCH_LINES: None")

    if mismatch_count > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
