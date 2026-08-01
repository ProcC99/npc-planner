#!/usr/bin/env python3
"""Reject commits that stage files outside their task card or scope allowlist.

Protocol Amendment 11 rev 3, section 11.8 (Correction D). Runs at the `commit-msg` stage.

Supports:
  * Task tags [M<n>-T<id>]: allowlist read from the card as committed in HEAD.
  * [ledger] tag: allows only docs/LEDGER.md.
  * [protocol] tag: allows EXECUTION_PROTOCOL.md, docs/PROTOCOL_AMENDMENT_*.md, docs/tasks/*.md.

Exit 0 to allow, 1 to reject.
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
import sys

TASK_TAG = re.compile(r"\[(M\d+-T\d+[a-z]?)\]")
SCOPE_TAG = re.compile(r"\[(ledger|protocol)\]")

ALLOW_HEADING = re.compile(r"^#+\s*Files you may create or modify\s*$", re.IGNORECASE)
NEXT_HEADING = re.compile(r"^#+\s+")
BULLET = re.compile(r"^\s*[-*]\s+`([^`]+)`")

ALWAYS_ALLOWED = ("docs/LEDGER.md",)

LEDGER_SCOPE = ("docs/LEDGER.md",)
PROTOCOL_SCOPE = (
    "EXECUTION_PROTOCOL.md",
    "docs/PROTOCOL_AMENDMENT_*.md",
    "docs/tasks/*.md",
    ".pre-commit-config.yaml",
)


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False)


def staged_files() -> list[str]:
    result = _git("diff", "--cached", "--name-only")
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def card_text_from_head(card_path: str) -> str | None:
    """Read the card as committed in HEAD, not as it sits on disk."""
    result = _git("show", "HEAD:" + card_path)
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


def is_allowed(path: str, patterns: tuple[str, ...] | list[str]) -> bool:
    for pattern in patterns:
        if pattern.endswith("/"):
            if path.startswith(pattern):
                return True
        elif path == pattern or fnmatch.fnmatch(path, pattern):
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

    task_match = TASK_TAG.search(message)
    scope_match = SCOPE_TAG.search(message)

    if not task_match and not scope_match:
        # Untagged commits are handled by task_id_required.py.
        return 0

    if scope_match and not task_match:
        scope_name = scope_match.group(1)
        allowed_patterns = LEDGER_SCOPE if scope_name == "ledger" else PROTOCOL_SCOPE
        violations = [p for p in staged_files() if not is_allowed(p, allowed_patterns)]
        if violations:
            print(
                f"\nfiles-within-allowlist: [{scope_name}] commit stages "
                f"{len(violations)} file(s) outside fixed [{scope_name}] scope.\n",
                file=sys.stderr,
            )
            for path in violations:
                print(f"  outside scope: {path}", file=sys.stderr)
            print(f"\nAllowed by [{scope_name}]:", file=sys.stderr)
            for pat in allowed_patterns:
                print(f"  {pat}", file=sys.stderr)
            return 1
        return 0

    assert task_match is not None
    task_id = task_match.group(1)
    card_path = f"docs/tasks/{task_id}.md"

    card_text = card_text_from_head(card_path)
    if card_text is None:
        print(
            f"\nfiles-within-allowlist: {card_path} is not committed in HEAD.\n"
            "\n"
            "Protocol Amendment 11.1: the task card is committed to the milestone branch\n"
            "BEFORE the task branch is created. An untracked card has no authority.\n",
            file=sys.stderr,
        )
        return 1

    patterns = parse_allowlist(card_text)
    if not patterns:
        print(
            f"\nfiles-within-allowlist: {card_path} has no parseable\n"
            '"Files you may create or modify" bullet list.\n',
            file=sys.stderr,
        )
        return 1

    allowed_all = list(patterns) + list(ALWAYS_ALLOWED)
    violations = [p for p in staged_files() if not is_allowed(p, allowed_all)]
    if violations:
        print(
            f"\nfiles-within-allowlist: commit tagged [{task_id}] stages "
            f"{len(violations)} file(s) outside the card allowlist.\n",
            file=sys.stderr,
        )
        for path in violations:
            print(f"  outside allowlist: {path}", file=sys.stderr)
        print(f"\nAllowed by {card_path}:", file=sys.stderr)
        for pattern in patterns:
            print(f"  {pattern}", file=sys.stderr)
        for path in ALWAYS_ALLOWED:
            print(f"  {path}  (always allowed)", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
