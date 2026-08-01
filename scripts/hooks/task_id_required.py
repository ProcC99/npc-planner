#!/usr/bin/env python3
"""Every non-merge commit must carry exactly one recognised scope tag.

Protocol Amendment 11 rev 3, section 11.7 (Correction D).

Valid scope tags:
  * Task tag:     [M<n>-T<id>]
  * Ledger tag:   [ledger]
  * Protocol tag: [protocol]
  * CI tag:       [ci]
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

TASK_TAG = re.compile(r"\[(M\d+-T\d+[a-z]?)\]")
SCOPE_TAG = re.compile(r"\[(ledger|protocol|ci)\]")


@dataclass(frozen=True)
class LedgerRow:
    task_id: str
    status: str
    sha: str
    check: str
    description: str


def parse_ledger_rows(text: str) -> tuple[LedgerRow, ...]:
    rows: list[LedgerRow] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 6:
            task_id = parts[1]
            status = parts[2]
            sha = parts[3]
            check = parts[4]
            desc = parts[5]
            if task_id in ("Task", "---") or task_id.startswith((":-", "---")):
                continue
            if TASK_TAG.match(f"[{task_id}]"):
                rows.append(
                    LedgerRow(
                        task_id=task_id,
                        status=status,
                        sha=sha,
                        check=check,
                        description=desc,
                    )
                )
    return tuple(rows)


def unparsable_ledger_rows(text: str) -> tuple[str, ...]:
    unparsable: list[str] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 6:
            task_id = parts[1]
            if task_id in ("Task", "---") or task_id.startswith((":-", "---")):
                continue
            if not TASK_TAG.match(f"[{task_id}]"):
                unparsable.append(line)
        else:
            if not any(w in line for w in ("Task", "---", ":-")):
                unparsable.append(line)
    return tuple(unparsable)


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


def is_task_done_in_ledger_head(task_id: str) -> tuple[bool, str, bool]:
    proc = subprocess.run(
        ["git", "show", "HEAD:docs/LEDGER.md"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return False, "", False

    text = proc.stdout
    rows = parse_ledger_rows(text)
    found_row = False
    for r in rows:
        if r.task_id == task_id:
            found_row = True
            if r.status == "done":
                sha_val = r.sha if (r.sha and r.sha != "—") else "placeholder"
                if sha_val == "placeholder":
                    print(
                        f"note: task {task_id} is recorded done with placeholder commit hash '—' in LEDGER.md",
                        file=sys.stderr,
                    )
                return True, sha_val, True
    return False, "", found_row


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        return 0

    if argv[1] == "--list-unparsable-rows":
        proc = subprocess.run(
            ["git", "show", "HEAD:docs/LEDGER.md"],
            capture_output=True,
            text=True,
            check=False,
        )
        text = (
            proc.stdout
            if proc.returncode == 0
            else Path("docs/LEDGER.md").read_text(encoding="utf-8")
        )
        unparsable = unparsable_ledger_rows(text)
        print(f"unparsable={unparsable}")
        return 0 if not unparsable else 1

    if argv[1] == "--list-rows":
        proc = subprocess.run(
            ["git", "show", "HEAD:docs/LEDGER.md"],
            capture_output=True,
            text=True,
            check=False,
        )
        text = (
            proc.stdout
            if proc.returncode == 0
            else Path("docs/LEDGER.md").read_text(encoding="utf-8")
        )
        rows = parse_ledger_rows(text)
        for r in rows:
            print(r)
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
        completed, commit_hash, found_row = is_task_done_in_ledger_head(task_id)
        if completed:
            print(
                "BLOCKED by task-id-required hook\n\n"
                f"  - task {task_id} is recorded done at {commit_hash}; its tag cannot authorise new work.\n"
                "    open a lettered follow-up card, or use [ci] / [ledger] / [protocol].\n",
                file=sys.stderr,
            )
            return 1
        if not found_row:
            print(
                f"note: no parsable ledger row for {task_id}; done-tag check skipped",
                file=sys.stderr,
            )

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
