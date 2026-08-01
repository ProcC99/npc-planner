#!/usr/bin/env python3
"""Enforce task-level file allowlists for git commits.

Protocol Amendment 11, section 11.4.

A commit message carrying `[M<n>-T<id>]` is checked against the allowlist
declared in `docs/tasks/M<n>-T<id>.md`. Files staged in git that are not in the
task's allowlist cause the hook to exit 1 and block the commit.

Special scope tags:
  * [ledger]   allows ONLY docs/LEDGER.md
  * [protocol] allows ONLY EXECUTION_PROTOCOL.md
  * [ci]       allows ONLY .pre-commit-config.yaml, Makefile, .github/, scripts/review_bundle.sh
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

TASK_TAG = re.compile(r"\[(M\d+-T\d+[a-z]?)\]")
SCOPE_TAG = re.compile(r"\[(ledger|protocol|ci)\]")

CI_SCOPE = (
    ".pre-commit-config.yaml",
    "Makefile",
    ".github/",
    "scripts/review_bundle.sh",
)

PROTOCOL_SCOPE = (
    "EXECUTION_PROTOCOL.md",
    "docs/LEDGER.md",
    "docs/PROTOCOL_AMENDMENT_*.md",
    "docs/tasks/*.md",
)

ALWAYS_ALLOWED = ("docs/LEDGER.md",)

GUARD_PATHS = (
    "scripts/hooks/",
    "scripts/audit_commits.py",
    ".pre-commit-config.yaml",
)


def get_staged_files(repo_root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def find_task_card(repo_root: Path, task_id: str) -> Path | None:
    parts = task_id.split("-")
    if len(parts) < 2:
        return None
    milestone = parts[0]
    card_path = repo_root / "docs" / "tasks" / f"{task_id}.md"
    if card_path.exists():
        return card_path
    cards_dir = repo_root / "docs" / "tasks"
    if cards_dir.exists():
        for p in cards_dir.glob(f"{milestone}-*.md"):
            if p.stem == task_id:
                return p
    return None


def read_card_text_from_head(repo_root: Path, card_rel_path: str) -> str | None:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "show", f"HEAD:{card_rel_path}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        return proc.stdout
    return None


def parse_allowlist(text: str) -> list[str]:
    lines = text.splitlines()
    in_section = False
    allowlist: list[str] = []

    for line in lines:
        if line.startswith("## Files you may create or modify"):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            m = re.match(r"^\s*[-*]\s+`([^`]+)`", line)
            if m:
                allowlist.append(m.group(1).strip())
    return allowlist


def match_pattern(filepath: str, pattern: str) -> bool:
    import fnmatch

    clean_file = filepath.lstrip("/")
    clean_pat = pattern.lstrip("/")

    if clean_pat.endswith("/"):
        return clean_file.startswith(clean_pat) or (clean_file + "/").startswith(
            clean_pat
        )
    return fnmatch.fnmatch(clean_file, clean_pat)


def is_file_allowed(filepath: str, allowlist: list[str]) -> bool:
    if filepath in ALWAYS_ALLOWED:
        return True
    for pat in allowlist:
        if match_pattern(filepath, pat):
            return True
    return False


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        return 0

    msg_file = Path(argv[1])

    override_files: list[str] = []
    if "--files" in argv:
        idx = argv.index("--files")
        override_files = argv[idx + 1 :]

    msg = msg_file.read_text(encoding="utf-8")
    first_line = msg.splitlines()[0] if msg.splitlines() else ""

    task_match = TASK_TAG.search(first_line)
    scope_match = SCOPE_TAG.search(first_line)

    repo_root = Path.cwd()
    staged = override_files if override_files else get_staged_files(repo_root)

    if not staged:
        return 0

    if scope_match:
        scope = scope_match.group(1)

        # Rule 11.13: Guards may not be modified by scope-tagged commits
        for f in staged:
            for g in GUARD_PATHS:
                if f.startswith(g) or f == g.rstrip("/"):
                    print(
                        "BLOCKED by files-within-allowlist hook\n\n"
                        f"  - guards may only change under a task tag; [{scope}] touched {f}\n",
                        file=sys.stderr,
                    )
                    return 1

        if scope == "ledger":
            forbidden = [f for f in staged if f != "docs/LEDGER.md"]
            if forbidden:
                print(
                    "BLOCKED by files-within-allowlist hook\n\n"
                    "  - [ledger] tag permits only docs/LEDGER.md, but staged:\n"
                    + "\n".join(f"      * {f}" for f in forbidden),
                    file=sys.stderr,
                )
                return 1
            return 0

        if scope == "protocol":
            forbidden = [
                f
                for f in staged
                if not any(match_pattern(f, pat) for pat in PROTOCOL_SCOPE)
            ]
            if forbidden:
                print(
                    "BLOCKED by files-within-allowlist hook\n\n"
                    "  - [protocol] tag permits only EXECUTION_PROTOCOL.md and docs/LEDGER.md, but staged:\n"
                    + "\n".join(f"      * {f}" for f in forbidden),
                    file=sys.stderr,
                )
                return 1
            return 0

        if scope == "ci":
            forbidden = [
                f for f in staged if not any(match_pattern(f, pat) for pat in CI_SCOPE)
            ]
            if forbidden:
                print(
                    "BLOCKED by files-within-allowlist hook\n\n"
                    "  - [ci] tag permits only .pre-commit-config.yaml, Makefile, .github/, scripts/review_bundle.sh, but staged:\n"
                    + "\n".join(f"      * {f}" for f in forbidden),
                    file=sys.stderr,
                )
                return 1
            return 0

    if not task_match:
        return 0

    task_id = task_match.group(1)
    card_path = find_task_card(repo_root, task_id)

    if card_path is None:
        print(
            "BLOCKED by files-within-allowlist hook\n\n"
            f"  - task card for {task_id} not found in docs/tasks/\n",
            file=sys.stderr,
        )
        return 1

    card_rel_path = str(card_path.relative_to(repo_root))

    # Check if the task card itself is modified in this commit
    if f"docs/tasks/{card_path.name}" in staged or card_rel_path in staged:
        print(
            "BLOCKED by files-within-allowlist hook\n\n"
            f"  - task card docs/tasks/{card_path.name} is immutable during its own task\n",
            file=sys.stderr,
        )
        return 1

    head_card_text = read_card_text_from_head(repo_root, card_rel_path)
    if head_card_text is None:
        print(
            "BLOCKED by files-within-allowlist hook\n\n"
            f"  - task card {card_rel_path} is not committed in HEAD\n",
            file=sys.stderr,
        )
        return 1

    allowlist = parse_allowlist(head_card_text)
    forbidden = [f for f in staged if not is_file_allowed(f, allowlist)]

    if forbidden:
        print(
            "BLOCKED by files-within-allowlist hook\n\n"
            f"  - files staged outside allowlist for {task_id}:\n"
            + "\n".join(f"      * {f}" for f in forbidden)
            + "\n\nDeclared allowlist:\n"
            + "\n".join(f"      * {p}" for p in allowlist),
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
