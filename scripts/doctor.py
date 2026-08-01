#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

from npc_planner.environment import RomRepoNotFoundError, resolve_rom_repo, run_all


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run environment preflight checks for pokeemerald-expansion repo."
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="Path to pokeemerald-expansion repo tree.",
    )
    parser.add_argument(
        "--cpp",
        default="cpp",
        help="Path or name of C preprocessor binary.",
    )
    args = parser.parse_args()

    try:
        repo_path = resolve_rom_repo(explicit=args.repo)
    except RomRepoNotFoundError as e:
        print(f"[FAIL] Environment Resolution Error:\n{e}", file=sys.stderr)
        sys.exit(2)

    print(f"Checking environment for ROM repository: {repo_path}\n")

    results = run_all(repo_path, cpp=args.cpp)

    hard_fail = False
    for res in results:
        status_str = "[OK]  " if res.ok else "[FAIL]"
        prefix = f"{status_str} ({res.severity.upper()}) {res.name}"
        print(f"{prefix}: {res.detail}")
        if not res.ok:
            if res.severity == "hard":
                hard_fail = True
            if res.remedy:
                print(f"       -> Remedy: {res.remedy}")
        print()

    if hard_fail:
        print(
            "Environment check FAILED: hard requirement(s) missing.",
            file=sys.stderr,
        )
        sys.exit(1)
    else:
        print("Environment check PASSED.")
        sys.exit(0)


if __name__ == "__main__":
    main()
