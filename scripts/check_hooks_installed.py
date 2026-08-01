#!/usr/bin/env python3
"""Fail if pre-commit is not actually installed into .git/hooks.

Rationale (Amendment 11 rev 3, section 11.9): between M1-T00b and M1-T08c the
repository carried a full .pre-commit-config.yaml and a scripts/hooks/ directory,
but `make hooks` had never been run. Every hook was inert. Three task cards
recorded gate claims that no hook had ever evaluated.

An uninstalled hook layer must be a loud failure, not a silent pass.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REQUIRED_STAGES = ("pre-commit", "commit-msg")
MARKER = "pre-commit"


def git_dir() -> Path:
    out = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        print("check-hooks-installed: not a git repository", file=sys.stderr)
        raise SystemExit(2)
    return Path(out.stdout.strip())


def hooks_path() -> Path:
    out = subprocess.run(
        ["git", "config", "--get", "core.hooksPath"],
        capture_output=True,
        text=True,
        check=False,
    )
    configured = out.stdout.strip()
    if configured:
        return Path(configured)
    return git_dir() / "hooks"


def main() -> int:
    base = hooks_path()
    missing: list[str] = []
    inert: list[str] = []

    for stage in REQUIRED_STAGES:
        script = base / stage
        if not script.exists():
            missing.append(str(script))
            continue
        try:
            text = script.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:  # pragma: no cover - unreadable hook
            inert.append(f"{script} (unreadable: {exc})")
            continue
        if MARKER not in text:
            inert.append(str(script))

    if not missing and not inert:
        print(f"hooks installed: {' '.join(REQUIRED_STAGES)}")
        return 0

    print("check-hooks-installed: the hook layer is not active.", file=sys.stderr)
    print(file=sys.stderr)
    for path in missing:
        print(f"  missing:   {path}", file=sys.stderr)
    for path in inert:
        print(f"  not wired: {path}", file=sys.stderr)
    print(file=sys.stderr)
    print(
        "Every guard in .pre-commit-config.yaml is currently doing nothing.",
        file=sys.stderr,
    )
    print(
        "Any gate claim made in this state is vacuous. Install them:", file=sys.stderr
    )
    print(file=sys.stderr)
    print("    make hooks", file=sys.stderr)
    print(file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
