#!/usr/bin/env python3
"""Catch the worst low-cost-model failure mode: a function that returns a
plausible value without computing it.

A function body that is nothing but `return 0.0` / `return []` / `return {}`
/ `return None` / `pass` is almost always an unimplemented stub that will
silently poison every score downstream. Unimplemented must raise.

Opt out on a specific function with a `# stub-ok:` comment plus a reason.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

PLACEHOLDERS = (0, 0.0, "", None, False)


def staged_python() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    return [
        f
        for f in out.splitlines()
        if f.endswith(".py") and f.startswith("src/npc_planner/")
    ]


def is_placeholder_body(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    body = [
        n
        for n in node.body
        if not isinstance(n, ast.Expr) or not isinstance(n.value, ast.Constant)
    ]
    if len(body) != 1:
        return False
    stmt = body[0]
    if isinstance(stmt, ast.Pass):
        return True
    if isinstance(stmt, ast.Return):
        v = stmt.value
        if v is None:
            return True
        if isinstance(v, ast.Constant) and v.value in PLACEHOLDERS:
            return True
        if (
            isinstance(v, (ast.List, ast.Dict, ast.Set, ast.Tuple))
            and not getattr(v, "elts", None)
            and not getattr(v, "keys", None)
        ):
            return True
    return False


def main() -> int:
    offenders: list[str] = []
    for path in staged_python():
        p = Path(path)
        if not p.exists():
            continue
        src = p.read_text(encoding="utf-8")
        lines = src.splitlines()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not is_placeholder_body(node):
                continue
            window = "\n".join(
                lines[max(0, node.lineno - 2) : node.end_lineno or node.lineno]
            )
            if "stub-ok:" in window:
                continue
            offenders.append(f"    {path}:{node.lineno} {node.name}()")

    if offenders:
        print("BLOCKED by no-placeholder-return hook\n")
        print("These functions return a value without computing it:")
        print("\n".join(offenders))
        print(
            "\nAn unimplemented function must `raise NotImplementedError`, so the"
            "\npipeline fails loudly instead of producing a confident wrong score."
            "\nDeliberate no-op? Add a `# stub-ok: <reason>` comment."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
