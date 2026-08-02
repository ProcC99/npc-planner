"""Probe script for M1-T12d acceptance suite.

Run via bash scripts/accept/M1-T12d.sh.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "src"))

from npc_planner.ingest.cparse import CParseError, parse_array_initializer


def probe_ci_branch_filter() -> str:
    """gate.yml triggers on milestone/** branch pushes."""
    gate_yml = REPO / ".github" / "workflows" / "gate.yml"
    text = gate_yml.read_text(encoding="utf-8")
    is_valid = ('branches: [main, "milestone/**"]' in text) or (
        'branches: ["milestone/**"]' in text
    )
    return f"filter_valid={is_valid}"


def probe_preprocessor_cparse_error() -> str:
    """parse_array_initializer raises CParseError on preprocessor conditional directives."""
    text = """
const int arr[] = {
    [FOO] = {
        .name = 1,
#if B_EXPANSION >= GEN_6
        .power = 90,
#endif
    },
};
"""
    try:
        parse_array_initializer(text, "arr")
        return "cparse_error=not_raised"
    except CParseError as e:
        return f"cparse_error=raised message_valid={'preprocessor' in str(e)}"


PROBES = {
    "ci-branch-filter": probe_ci_branch_filter,
    "preprocessor-cparse-error": probe_preprocessor_cparse_error,
}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in PROBES:
        sys.stderr.write(f"usage: M1-T12d_checks.py <{'|'.join(PROBES)}>\n")
        return 2
    sys.stdout.write(PROBES[argv[1]]())
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
