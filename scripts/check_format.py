#!/usr/bin/env python3
"""Validate a daily-practice markdown file against the reader app's strict parser contract."""

import re
import sys


def check(path):
    problems = []

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    lines = text.splitlines()

    # First line must match "# Daily Practice - YYYY-MM-DD"
    if not lines or not re.match(r"^# Daily Practice - \d{4}-\d{2}-\d{2}\s*$", lines[0]):
        problems.append(
            "First line must match '# Daily Practice - YYYY-MM-DD', got: "
            + (repr(lines[0]) if lines else "<empty file>")
        )

    # Exactly one '## DSA' and one '## CS Fundamentals', DSA before CS Fundamentals.
    h2_positions = [
        (i, line.strip())
        for i, line in enumerate(lines)
        if re.match(r"^## \S", line.strip()) or line.strip() == "##"
    ]
    h2_headings = [h for _, h in h2_positions]

    dsa_count = h2_headings.count("## DSA")
    cs_count = h2_headings.count("## CS Fundamentals")

    if dsa_count != 1:
        problems.append(f"Expected exactly one '## DSA' heading, found {dsa_count}.")
    if cs_count != 1:
        problems.append(f"Expected exactly one '## CS Fundamentals' heading, found {cs_count}.")

    dsa_idx = None
    cs_idx = None
    if dsa_count == 1 and cs_count == 1:
        dsa_idx = h2_positions[h2_headings.index("## DSA")][0]
        cs_idx = h2_positions[h2_headings.index("## CS Fundamentals")][0]
        if dsa_idx > cs_idx:
            problems.append("'## DSA' must come before '## CS Fundamentals'.")

    # Slice out section bodies (line indices) for further checks.
    if dsa_idx is not None and cs_idx is not None and dsa_idx < cs_idx:
        dsa_lines = lines[dsa_idx + 1 : cs_idx]
        cs_lines = lines[cs_idx + 1 :]
    elif dsa_idx is not None:
        dsa_lines = lines[dsa_idx + 1 :]
        cs_lines = []
    elif cs_idx is not None:
        dsa_lines = []
        cs_lines = lines[cs_idx + 1 :]
    else:
        dsa_lines = []
        cs_lines = []

    # DSA section: a '###' heading starting with literal 'Question:' and ending in '(...)',
    # plus at least one further '###' block after it. No '**Answer:**' allowed here.
    dsa_h3 = [
        (i, line.strip())
        for i, line in enumerate(dsa_lines)
        if line.strip().startswith("### ")
    ]
    question_headings = [
        (i, h) for i, h in dsa_h3 if re.match(r"^### Question:.*\(.+\)\s*$", h)
    ]
    if not question_headings:
        problems.append(
            "DSA section must contain a '### Question: <Name> (<Topic> — <Difficulty>)' heading."
        )
    else:
        q_idx = question_headings[0][0]
        later_h3 = [i for i, _ in dsa_h3 if i > q_idx]
        if not later_h3:
            problems.append(
                "DSA section must contain at least one further '###' block after the Question heading."
            )

    for i, line in enumerate(dsa_lines):
        if re.search(r"\*\*answer:?\*\*", line.strip(), re.IGNORECASE):
            problems.append(
                f"'**Answer:**' marker must not appear in the DSA section (found near line {dsa_idx + 2 + i})."
            )

    # CS Fundamentals section: exactly three '### N. Subject (Format)' headings, numbered 1-3.
    cs_h3 = [
        (i, line.strip())
        for i, line in enumerate(cs_lines)
        if line.strip().startswith("### ")
    ]
    numbered_pattern = re.compile(r"^### (\d+)\.\s+.+\(.+\)\s*$")
    numbered_headings = []
    for i, h in cs_h3:
        m = numbered_pattern.match(h)
        if m:
            numbered_headings.append((i, h, int(m.group(1))))
        else:
            problems.append(
                f"CS Fundamentals heading does not match '### N. Subject (Format)': {h!r}"
            )

    if len(numbered_headings) != 3:
        problems.append(
            f"Expected exactly 3 numbered CS Fundamentals headings, found {len(numbered_headings)}."
        )
    else:
        nums = [n for _, _, n in numbered_headings]
        if nums != [1, 2, 3]:
            problems.append(f"CS Fundamentals headings must be numbered 1, 2, 3 in order; found {nums}.")

    for i, h, _ in numbered_headings:
        # Check the parenthetical portion for an em-dash; the heading text outside
        # parentheses must not contain one either.
        m = re.match(r"^### \d+\.\s+(.+?)\s*\((.+)\)\s*$", h)
        if m:
            outside = m.group(1)
            if "—" in outside:
                problems.append(f"Heading must not use an em-dash outside the parenthetical: {h!r}")
            inside = m.group(2)
            if "—" in inside:
                problems.append(f"Heading parenthetical must not contain an em-dash: {h!r}")

    # Exactly one '**Answer:**' (or '**Answer**') line, alone on its own line, under each
    # of the three numbered headings; three total in the CS Fundamentals section.
    answer_line_re = re.compile(r"^\*\*answer:?\*\*$", re.IGNORECASE)
    cs_answer_lines = [i for i, line in enumerate(cs_lines) if answer_line_re.match(line.strip())]

    if len(cs_answer_lines) != 3:
        problems.append(
            f"Expected exactly 3 '**Answer:**' marker lines in CS Fundamentals section, found {len(cs_answer_lines)}."
        )

    if len(numbered_headings) == 3 and len(cs_answer_lines) == 3:
        bounds = [i for i, _, _ in numbered_headings] + [len(cs_lines)]
        for k in range(3):
            start, end = bounds[k], bounds[k + 1]
            count_in_range = sum(1 for i in cs_answer_lines if start < i < end)
            if count_in_range != 1:
                problems.append(
                    f"CS Fundamentals question {k + 1} must have exactly one '**Answer:**' marker "
                    f"under it, found {count_in_range}."
                )

    # No <details>/<summary> tags anywhere.
    if re.search(r"<details|<summary", text, re.IGNORECASE):
        problems.append("File must not contain '<details>' or '<summary>' tags.")

    if problems:
        print(f"FAIL {path}")
        for idx, p in enumerate(problems, 1):
            print(f"{idx}. {p}")
        return 1

    print(f"ok {path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: check_format.py <path-to-markdown-file>", file=sys.stderr)
        sys.exit(2)
    sys.exit(check(sys.argv[1]))
