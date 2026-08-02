# scripts/accept/M1-T12g_checks.py
"""Acceptance check probes for M1-T12g."""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def probe_gate_yml_t10b() -> str:
    gate_yml = _REPO_ROOT / ".github" / "workflows" / "gate.yml"
    text = gate_yml.read_text()
    if "scripts/accept/M1-T10b.sh" in text:
        return "t10b_present=True"
    return "t10b_present=False"


def probe_audit_baseline() -> str:
    audit_py = _REPO_ROOT / "scripts" / "audit_commits.py"
    text = audit_py.read_text()
    if "d5dbc28" in text:
        return "d5dbc28_documented=True"
    return "d5dbc28_documented=False"


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: M1-T12g_checks.py <probe>", file=sys.stderr)
        return 2
    cmd = sys.argv[1]
    if cmd == "t10b-present":
        print(probe_gate_yml_t10b())
        return 0
    elif cmd == "audit-baseline":
        print(probe_audit_baseline())
        return 0
    print(f"unknown probe: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
