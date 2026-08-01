#!/usr/bin/env python3
"""Reject a commit that removes a test function without a written waiver.

Waiver: add a file under docs/waivers/ in the same commit explaining why.
"""

from __future__ import annotations

import subprocess
import sys

MARKERS = ("def test_", "async def test_")
SKIP_MARKERS = ("@pytest.mark.skip", "@pytest.mark.xfail", "pytest.skip(")


def staged_diff() -> str:
    return subprocess.run(
        ["git", "diff", "--cached", "--unified=0", "--", "tests/"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout


def staged_files() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    return [f for f in out.splitlines() if f.strip()]


def main() -> int:
    diff = staged_diff()
    removed = [
        ln
        for ln in diff.splitlines()
        if ln.startswith("-")
        and not ln.startswith("---")
        and any(m in ln for m in MARKERS)
    ]
    added_skips = [
        ln
        for ln in diff.splitlines()
        if ln.startswith("+")
        and not ln.startswith("+++")
        and any(m in ln for m in SKIP_MARKERS)
    ]

    has_waiver = any(f.startswith("docs/waivers/") for f in staged_files())

    problems: list[str] = []
    if removed and not has_waiver:
        problems.append("This commit deletes test functions:")
        problems += [f"    {ln}" for ln in removed]
    if added_skips and not has_waiver:
        problems.append("This commit adds skip/xfail markers:")
        problems += [f"    {ln}" for ln in added_skips]

    if problems:
        print("BLOCKED by no-test-deletion hook\n")
        print("\n".join(problems))
        print(
            "\nIf the test is genuinely wrong, add docs/waivers/<task-id>.md in the"
            "\nsame commit stating why. Never delete a test to make a build pass."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
