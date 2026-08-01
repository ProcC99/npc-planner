#!/usr/bin/env python3
"""Golden snapshots may only change in a commit that touches nothing else.

This makes an unreviewed golden drift structurally impossible: a model cannot
sneak a regenerated snapshot in alongside the code change that broke it.
"""

from __future__ import annotations

import subprocess
import sys

GOLDEN_PREFIX = "tests/golden/"
ALLOWED_COMPANIONS = ("docs/LEDGER.md",)


def staged_files() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    return [f for f in out.splitlines() if f.strip()]


def main() -> int:
    files = staged_files()
    golden = [f for f in files if f.startswith(GOLDEN_PREFIX)]
    if not golden:
        return 0

    others = [
        f
        for f in files
        if not f.startswith(GOLDEN_PREFIX) and f not in ALLOWED_COMPANIONS
    ]
    if others:
        print("BLOCKED by no-golden-edit hook\n")
        print("Golden snapshots changed:")
        print("\n".join(f"    {f}" for f in golden))
        print("\nalongside non-golden files:")
        print("\n".join(f"    {f}" for f in others))
        print(
            "\nSplit this into two commits. The golden-only commit must be reviewed"
            "\nline by line and its message must contain 'golden approved'."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
