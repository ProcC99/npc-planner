#!/usr/bin/env python3
"""Every commit must name the task it belongs to: [M3-T04].

This is what makes `git log` an audit trail rather than a pile of 'fix stuff'.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

TASK_RE = re.compile(r"\[M[1-6]-T\d{2}[a-z]?\]")
TYPE_RE = re.compile(r"^(feat|fix|test|refactor|chore|docs|data|revert)\([a-z]+\): .+")
EXEMPT_PREFIXES = ("Merge ", "Revert ", "fixup!", "squash!")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        return 0
    msg = Path(argv[1]).read_text(encoding="utf-8")
    first = msg.splitlines()[0] if msg.splitlines() else ""

    if first.startswith(EXEMPT_PREFIXES):
        return 0

    problems: list[str] = []
    if not TASK_RE.search(msg):
        problems.append("missing task id, e.g. [M3-T04]")
    if not TYPE_RE.match(first):
        problems.append(
            "subject must be '<type>(<scope>): <imperative summary>'\n"
            "      type  = feat|fix|test|refactor|chore|docs|data|revert\n"
            "      scope = db|ingest|rules|analysis|generate|validate|export|cli|config|ci"
        )
    if "tests/golden" in msg.lower() and "golden approved" not in msg.lower():
        problems.append(
            "golden change requires the words 'golden approved' in the message"
        )

    if problems:
        print("BLOCKED by task-id-required hook\n")
        for p in problems:
            print(f"  - {p}")
        print(
            "\nExample:\n"
            "  feat(rules): resolve ruleset extends chain   [M3-T04]\n\n"
            "  Legality evaluation needs a single flattened ruleset.\n\n"
            "  Tests: 5 unit tests incl. cycle + missing-parent\n"
            "  Gate:  make check green"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
