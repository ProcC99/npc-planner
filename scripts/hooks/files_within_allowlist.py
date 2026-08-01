#!/usr/bin/env python3
"""Reject commits that stage files outside their task card's allowlist.

Protocol Amendment 11.8. Runs at the `commit-msg` stage, so the task id is available.

Also enforces Amendment 11.1 (revised): the task card must already be committed in HEAD
before the task branch does any work. If the card is missing from HEAD, the commit is
rejected, because an untracked card cannot be an authority over anything.

Exit 0 to allow, 1 to reject.
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
import sys

TASK_TAG = re.compile(r"\[(M\d+-T\d+[a-z]?)\]")

# The section whose bullet list defines the allowlist.
ALLOW_HEADING = re.compile(r"^#+\s*Files you may create or modify\s*$", re.IGNORECASE)
NEXT_HEADING = re.compile(r"^#+\s+")
# Bullet lines look like:  - `path/to/file.py`   (trailing prose after the backticks is ignored)
BULLET = re.compile(r"^\s*[-*]\s+`([^`]+)`")

# Bookkeeping files every task is permitted to touch.
ALWAYS_ALLOWED = ("docs/LEDGER.md",)


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False)


def staged_files() -> list[str]:
    result = _git("diff", "--cached", "--name-only")
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def card_text_from_head(card_path: str) -> str | None:
    """Read the card as committed in HEAD, not as it sits on disk.

    Reading from HEAD is deliberate: a card edited in the working tree must not be
    able to widen its own allowlist for the commit currently being made.
    """
    result = _git("show", f"HEAD:{card_path}")
    if result.returncode != 0:
        return None
    return result.stdout


def parse_allowlist(card_text: str) -> list[str]:
    patterns: list[str] = []
    in_section = False
    for line in card_text.splitlines():
        if ALLOW_HEADING.match(line):
            in_section = True
            continue
        if in_section:
            if NEXT_HEADING.match(line):
                break
            match = BULLET.match(line)
            if match:
                patterns.append(match.group(1).strip())
    return patterns


def is_allowed(path: str, patterns: list[str]) -> bool:
    if path in ALWAYS_ALLOWED:
        return True
    for pattern in patterns:
        if path == pattern or fnmatch.fnmatch(path, pattern):
            return True
        # A directory pattern such as `tests/fixtures/fake_rom/` covers everything beneath it.
        if pattern.endswith("/") and path.startswith(pattern):
            return True
    return False


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "files-within-allowlist: expected a commit message file path",
            file=sys.stderr,
        )
        return 1

    try:
        with open(argv[1], encoding="utf-8") as handle:
            message = handle.read()
    except OSError as exc:
        print(
            f"files-within-allowlist: cannot read commit message: {exc}",
            file=sys.stderr,
        )
        return 1

    match = TASK_TAG.search(message)
    if match is None:
        # Untagged commits are the concern of task_id_required.py.
        return 0

    task_id = match.group(1)
    card_path = f"docs/tasks/{task_id}.md"

    card_text = card_text_from_head(card_path)
    if card_text is None:
        print(
            f"\nfiles-within-allowlist: {card_path} is not committed in HEAD.\n"
            "\n"
            "Protocol Amendment 11.1: the task card is committed to the milestone branch\n"
            "BEFORE the task branch is created. An untracked card has no authority, and\n"
            "card immutability cannot be enforced against a file git has never seen.\n"
            "\n"
            "  git checkout milestone/<M>\n"
            f"  git add {card_path}\n"
            f'  git commit -m "docs(tasks): add {task_id} card"\n'
            f"  git checkout -b task/{task_id}\n",
            file=sys.stderr,
        )
        return 1

    patterns = parse_allowlist(card_text)
    if not patterns:
        print(
            f"\nfiles-within-allowlist: {card_path} has no parseable\n"
            '"Files you may create or modify" bullet list.\n'
            "\n"
            "Expected bullets of the form:   - `src/npc_planner/thing.py`\n",
            file=sys.stderr,
        )
        return 1

    violations = [p for p in staged_files() if not is_allowed(p, patterns)]
    if violations:
        print(
            f"\nfiles-within-allowlist: commit tagged [{task_id}] stages "
            f"{len(violations)} file(s) outside the card allowlist.\n",
            file=sys.stderr,
        )
        for path in violations:
            print(f"  outside allowlist: {path}", file=sys.stderr)
        print(
            "\nAllowed by " + card_path + ":",
            file=sys.stderr,
        )
        for pattern in patterns:
            print(f"  {pattern}", file=sys.stderr)
        for path in ALWAYS_ALLOWED:
            print(f"  {path}  (always allowed)", file=sys.stderr)
        print(
            "\nUnrelated work belongs in its own commit. Protocol scaffolding, hook\n"
            "installation, and documentation restructuring are chore commits, not task\n"
            "commits. Unstage the extras:\n"
            "\n  git restore --staged " + " ".join(violations) + "\n",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
