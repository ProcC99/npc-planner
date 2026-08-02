#!/usr/bin/env python3
"""Acceptance probes for M1-T12f."""

import subprocess
import sys
from pathlib import Path


def check_tag_t12d() -> None:
    proc = subprocess.run(
        ["git", "rev-parse", "done/M1-T12d^{commit}"],
        capture_output=True,
        text=True,
        check=True,
    )
    sha = proc.stdout.strip()
    expected = "372eb9af434b0144dbdc952ce7a8f3ff042f0dde"
    print(f"t12d_sha={sha[:7]} correct={sha == expected}")


def check_protocol_11_17() -> None:
    text = Path("EXECUTION_PROTOCOL.md").read_text(encoding="utf-8")
    print(f"11_17_present={'11.17 Verified reporting' in text}")


def check_ledger_t12g() -> None:
    text = Path("docs/LEDGER.md").read_text(encoding="utf-8")
    print(f"t12g_todo_present={'M1-T12g' in text}")


def main() -> int:
    if len(sys.argv) < 2:
        return 1
    cmd = sys.argv[1]
    if cmd == "tag-t12d":
        check_tag_t12d()
    elif cmd == "protocol-11-17":
        check_protocol_11_17()
    elif cmd == "ledger-t12g":
        check_ledger_t12g()
    else:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
