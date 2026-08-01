#!/usr/bin/env python3
"""Reject commits that modify the task card of the task they claim to implement.

Protocol Amendment 11.1: a task card is immutable for the duration of its own task.

Installed at the `commit-msg` stage, so the commit message (which carries the task id)
is available. pre-commit passes the path to the commit message file as argv[1].

Exit 0 to allow the commit, 1 to reject it.
"""

from __future__ import annotations

import re
import subprocess
import sys

# Matches the trailing task tag, e.g. "[M1-T08c]" or "[M3-T04]".
TASK_TAG = re.compile(r"\[(M\d+-T\d+[a-z]?)\]")


def staged_files() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("no-card-self-edit: expected a commit message file path", file=sys.stderr)
        return 1

    try:
        with open(argv[1], encoding="utf-8") as handle:
            message = handle.read()
    except OSError as exc:
        print(f"no-card-self-edit: cannot read commit message: {exc}", file=sys.stderr)
        return 1

    match = TASK_TAG.search(message)
    if match is None:
        # Task-id enforcement is a separate hook (task_id_required.py).
        # This hook has nothing to say about untagged commits.
        return 0

    task_id = match.group(1)
    own_card = f"docs/tasks/{task_id}.md"

    if own_card in staged_files():
        print(
            f"\nno-card-self-edit: commit is tagged [{task_id}] and modifies {own_card}.\n"
            "\n"
            "Protocol Amendment 11.1: a task card is immutable during its own task.\n"
            "The agent executing a task may not edit, truncate, or rewrite its own card.\n"
            "\n"
            "If the card is wrong, either:\n"
            f"  1. mark {task_id} `blocked` in docs/LEDGER.md with a reason, and stop; or\n"
            "  2. proceed and record the discrepancy in the commit body.\n"
            "\n"
            "Corrections belong in a follow-up card authored by the human.\n"
            f"\n  git restore --staged {own_card} && git checkout -- {own_card}\n",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
