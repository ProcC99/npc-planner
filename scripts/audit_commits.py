#!/usr/bin/env python3
"""Retroactively re-check every commit on a branch against the rules the hooks enforce.

Protocol Amendment 11, section 11.13.

Usage:
    python3 scripts/audit_commits.py                    # main..milestone/M1
    python3 scripts/audit_commits.py --range main..HEAD
    python3 scripts/audit_commits.py --range main..HEAD --since-task M1-T08

Exit codes: 0 clean, 1 violations found, 2 usage or git error.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys

TASK_TAG = re.compile(r"\[(M\d+-T\d+[a-z]?)\]")
SCOPE_TAG = re.compile(r"\[(ledger|protocol|ci)\]")

ALLOW_HEADING = re.compile(r"^#+\s*Files you may create or modify\s*$", re.IGNORECASE)
NEXT_HEADING = re.compile(r"^#+\s+")
BULLET = re.compile(r"^\s*[-*]\s+`([^`]+)`")

ALWAYS_ALLOWED = ("docs/LEDGER.md",)

LEDGER_SCOPE = ("docs/LEDGER.md",)
CI_SCOPE = (
    ".pre-commit-config.yaml",
    "Makefile",
    ".github/",
    "scripts/review_bundle.sh",
)
PROTOCOL_SCOPE = (
    "EXECUTION_PROTOCOL.md",
    "docs/PROTOCOL_AMENDMENT_*.md",
    "docs/tasks/*.md",
)
GUARD_PATHS = (
    "scripts/hooks/",
    "scripts/audit_commits.py",
    ".pre-commit-config.yaml",
)

# Commits whose violations have been triaged and recorded.
# Key: full sha.  Value: short human-readable reason.
KNOWN_VIOLATIONS: dict[str, str] = {
    "401de73ef52c01f5bf71f7fefa45b24893593953": (
        "M1-T12 card mutated after initial commit — "
        ".split → .category rename was a fixture fidelity violation (T12b remediation)"
    ),
    "d5dbc2829285098ff302dd0012586e9feffb717b": (
        "merge: integrate M1-T12d into milestone/M1 — merge commit created during T12d integration"
    ),
}


def git(*args: str) -> tuple[int, str]:
    proc = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    return proc.returncode, proc.stdout


def parse_allowlist(text: str) -> list[str]:
    """Pull backtick-quoted paths out of the card's allowlist section."""
    lines = text.splitlines()
    out: list[str] = []
    inside = False
    for line in lines:
        if ALLOW_HEADING.match(line):
            inside = True
            continue
        if inside and NEXT_HEADING.match(line):
            break
        if inside:
            found = BULLET.match(line)
            if found:
                out.append(found.group(1).strip())
    return out


def covered(path: str, patterns: tuple[str, ...] | list[str]) -> bool:
    for pattern in patterns:
        if pattern.endswith("/"):
            if path.startswith(pattern):
                return True
        elif path == pattern or fnmatch.fnmatch(path, pattern):
            return True
    return False


def is_done_tag_violation(sha: str, task_id: str, files: list[str]) -> str | None:
    if files == ["docs/LEDGER.md"]:
        return None
    rc, ledger_text = git("show", f"{sha}~1:docs/LEDGER.md")
    if rc != 0:
        return None
    for line in ledger_text.splitlines():
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 4:
            row_task = parts[1]
            row_status = parts[2]
            row_sha = parts[3]
            if row_task == task_id and row_status == "done":
                sha_str = row_sha if (row_sha and row_sha != "—") else "placeholder"
                return f"task {task_id} is recorded done at {sha_str}; tag reused"
    return None


def audit_commit(sha: str) -> list[str]:
    """Return a list of human-readable problems with this commit."""
    problems: list[str] = []

    rc, subject = git("log", "-1", "--format=%s", sha)
    if rc != 0:
        return [f"cannot read subject for {sha}"]
    subject = subject.strip()

    rc, files_out = git("show", "--name-only", "--format=", sha)
    if rc != 0:
        return [f"cannot list files for {sha}"]
    files = [line.strip() for line in files_out.splitlines() if line.strip()]
    if not files:
        return []

    task = TASK_TAG.search(subject)
    scope = SCOPE_TAG.search(subject)

    if task and scope:
        problems.append("carries both a task tag and a scope tag; use exactly one")
        return problems

    if not task and not scope:
        problems.append(
            "untagged commit. Untagged commits bypass the allowlist entirely, "
            "which is how scripts/hooks/task_id_required.py was modified outside "
            "any card during M1-T08d."
        )
        return problems

    if scope:
        scope_name = scope.group(1)
        # Check Rule 11.13: scope-tagged commit touching guards
        for f in files:
            for g in GUARD_PATHS:
                if f.startswith(g) or f == g.rstrip("/"):
                    problems.append(
                        f"guards may only change under a task tag; [{scope_name}] touched {f}"
                    )

        if scope_name == "ledger":
            allowed = LEDGER_SCOPE
        elif scope_name == "ci":
            allowed = CI_SCOPE
        else:
            allowed = PROTOCOL_SCOPE
        outside = [f for f in files if not covered(f, allowed)]
        for path in outside:
            problems.append(f"[{scope_name}] commit touches out-of-scope file: {path}")
        return problems

    assert task is not None
    task_id = task.group(1)

    done_err = is_done_tag_violation(sha, task_id, files)
    if done_err:
        problems.append(done_err)

    card_path = f"docs/tasks/{task_id}.md"
    rc, card_text = git("show", f"{sha}:{card_path}")
    if rc != 0:
        problems.append(
            f"tagged [{task_id}] but {card_path} does not exist in that commit's tree. "
            "The card was committed after the work, or not at all."
        )
        return problems

    allowed = parse_allowlist(card_text)
    if not allowed:
        problems.append(f"{card_path} has no parseable allowlist section")
        return problems

    allowed_all = list(allowed) + list(ALWAYS_ALLOWED)
    for path in files:
        if path == card_path:
            continue
        if not covered(path, allowed_all):
            problems.append(f"outside the {task_id} allowlist: {path}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--range", dest="rev_range", default="main..milestone/M1")
    parser.add_argument(
        "--since-task",
        default=None,
        help="Only report on commits whose task tag sorts at or after this id.",
    )
    parser.add_argument(
        "--first-parent",
        action="store_true",
        help="Follow only the first parent commit upon seeing a merge commit.",
    )
    args = parser.parse_args(argv)

    cmd = ["log", "--format=%H"]
    if args.first_parent:
        cmd.append("--first-parent")
    else:
        cmd.append("--no-merges")
    cmd.append(args.rev_range)

    rc, log = git(*cmd)
    if rc != 0:
        print(f"audit-commits: cannot walk {args.rev_range}", file=sys.stderr)
        return 2

    shas = [line.strip() for line in log.splitlines() if line.strip()]
    shas.reverse()

    total = 0
    bad = 0
    known_skipped = 0
    for sha in shas:
        _, subject = git("log", "-1", "--format=%s", sha)
        subject = subject.strip()
        if args.since_task:
            found = TASK_TAG.search(subject)
            if found and found.group(1) < args.since_task:
                continue
        total += 1
        if sha in KNOWN_VIOLATIONS:
            known_skipped += 1
            continue
        problems = audit_commit(sha)
        if problems:
            bad += 1
            print(f"{sha[:7]}  {subject}")
            for problem in problems:
                print(f"          - {problem}")

    print("-" * 62)
    summary_parts = [
        f"audit: {total - bad - known_skipped}/{total} commits clean",
        f"{bad} with violations",
    ]
    if known_skipped:
        summary_parts.append(f"{known_skipped} known (triaged)")
    print(", ".join(summary_parts))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
