#!/usr/bin/env python3
"""Probe checks for M1-T12e acceptance suite."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from npc_planner.environment import RomRepoNotFoundError, resolve_rom_repo


def check_gate_yml() -> bool:
    gate_yml = ROOT / ".github" / "workflows" / "gate.yml"
    content = gate_yml.read_text(encoding="utf-8")
    return "make hooks" in content


def check_gitignore() -> bool:
    gitignore = ROOT / ".gitignore"
    content = gitignore.read_text(encoding="utf-8")
    return "pokeemerald-expansion/" in content.splitlines()


def check_in_tree_rejection() -> bool:
    in_tree = ROOT / "pokeemerald-expansion"
    try:
        resolve_rom_repo(explicit=in_tree, planner_root=ROOT)
        return False
    except RomRepoNotFoundError:
        return True


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: M1-T12e_checks.py <probe_name>", file=sys.stderr)
        sys.exit(2)

    probe = sys.argv[1]
    if probe == "gate-yml":
        print(f"gate_yml_valid={check_gate_yml()}")
    elif probe == "gitignore":
        print(f"gitignore_valid={check_gitignore()}")
    elif probe == "in-tree-rejection":
        print(f"in_tree_rejected={check_in_tree_rejection()}")
    else:
        print(f"Unknown probe: {probe}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
