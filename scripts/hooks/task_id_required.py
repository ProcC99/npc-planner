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
SCOPE_TAG = re.compile(r"\[(ledger|protocol|ci)\]")


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


def is_task_done_in_ledger_head(task_id: str) -> tuple[bool, str]:
    proc = subprocess.run(
        ["git", "show", "HEAD:docs/LEDGER.md"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return False, ""

    for line in proc.stdout.splitlines():
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 4:
            row_task = parts[1]
            row_status = parts[2]
            row_sha = parts[3]
            if (
                row_task == task_id
                and row_status == "done"
                and row_sha
                and row_sha != "—"
            ):
                return True, row_sha
    return False, ""


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
            "      * Protocol tag: [protocol]\n"
            "      * CI tag:       [ci]\n\n"
            "Example:\n"
            "  chore(ci): enforce card allowlist   [M1-T08e]\n",
            file=sys.stderr,
        )
        return 1

    if task_match:
        task_id = task_match.group(1)
        is_done, sha = is_task_done_in_ledger_head(task_id)
        if is_done:
            print(
                "BLOCKED by task-id-required hook\n\n"
                f"  - task {task_id} is recorded done at {sha}; its tag cannot authorise new work.\n"
                "    open a lettered follow-up card, or use [ci] / [ledger] / [protocol].\n",
                file=sys.stderr,
            )
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
