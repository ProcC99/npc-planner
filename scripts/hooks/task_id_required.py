#!/usr/bin/env python3
"""Every non-merge commit must carry exactly one recognised scope tag.

Protocol Amendment 11 rev 3, section 11.7 (Correction D).

Valid scope tags:
  * Task tag:     [M<n>-T<id>]
  * Ledger tag:   [ledger]
  * Protocol tag: [protocol]
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

TASK_TAG = re.compile(r"\[(M\d+-T\d+[a-z]?)\]")
SCOPE_TAG = re.compile(r"\[(ledger|protocol)\]")


def is_merge_commit() -> bool:
    proc = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        git_dir = Path(proc.stdout.strip())
        if (git_dir / "MERGE_HEAD").exists():
            return True
    return False


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        return 0

    if is_merge_commit():
        return 0

    msg = Path(argv[1]).read_text(encoding="utf-8")
    first_line = msg.splitlines()[0] if msg.splitlines() else ""

    task_match = TASK_TAG.search(first_line)
    scope_match = SCOPE_TAG.search(first_line)

    if task_match and scope_match:
        print(
            "BLOCKED by task-id-required hook\n\n"
            "  - subject contains both a task tag and a scope tag; use exactly one\n",
            file=sys.stderr,
        )
        return 1

    if not task_match and not scope_match:
        print(
            "BLOCKED by task-id-required hook\n\n"
            "  - missing scope tag. Subject must carry exactly one tag:\n"
            "      * Task tag:     [M<n>-T<id>] (e.g. [M1-T08e])\n"
            "      * Ledger tag:   [ledger]\n"
            "      * Protocol tag: [protocol]\n\n"
            "Example:\n"
            "  chore(ci): enforce card allowlist   [M1-T08e]\n",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
