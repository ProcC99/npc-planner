#!/usr/bin/env bash
"""Probe script for M1-T12 acceptance suite.

Run via bash scripts/accept/M1-T12.sh.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Fix python import path
HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "src"))

from npc_planner.ingest.moves import audit_moves_coverage, read_moves
from npc_planner.ingest.rom_probe import probe_layout
from npc_planner.ingest.species import (
    audit_species_coverage,
    read_species_with_source,
)

FIXTURE = REPO / "tests" / "fixtures" / "fake_rom"


def _load_module(path: str, name: str) -> object:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO / path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


EXPECTED_CI_SCOPE = (
    ".pre-commit-config.yaml",
    "Makefile",
    ".github/",
    "scripts/review_bundle.sh",
)


def probe_ci_scope() -> str:
    allow = _load_module("scripts/hooks/files_within_allowlist.py", "fwa")
    audit = _load_module("scripts/audit_commits.py", "ac")
    same = (
        tuple(getattr(allow, "CI_" + "SCOPE")) == EXPECTED_CI_SCOPE
        and tuple(getattr(audit, "CI_" + "SCOPE")) == EXPECTED_CI_SCOPE
    )
    return f"ci_scope={same}"


def probe_ci_scope_excludes_guards() -> str:
    allow = _load_module("scripts/hooks/files_within_allowlist.py", "fwa")
    bad = [
        entry
        for entry in getattr(allow, "CI_" + "SCOPE")
        if entry.startswith(("scripts/hooks", "scripts/accept"))
        or entry == "scripts/audit_commits.py"
    ]
    return f"guards_excluded={not bad}"


def probe_guard_paths_declared() -> str:
    allow = _load_module("scripts/hooks/files_within_allowlist.py", "fwa")
    paths = tuple(getattr(allow, "GUARD_" + "PATHS"))
    ok = (
        "scripts/hooks/" in paths
        and "scripts/audit_commits.py" in paths
        and ".pre-commit-config.yaml" in paths
    )
    return f"guard_paths={ok}"


def probe_done_predicate_has_no_sha_conjunct() -> str:
    tid = _load_module("scripts/hooks/task_id_required.py", "tid")
    fn = tid.is_task_done_in_ledger_head
    res = fn("M1-T999", ledger_text="| M1-T999 | done | — | check ✅ | desc |\n")
    return f"no_sha_conjunct={res.is_done} placeholder={res.sha == '—'}"


def probe_sentinel_present() -> str:
    tid = _load_module("scripts/hooks/task_id_required.py", "tid")
    fn = tid.is_task_done_in_ledger_head
    text = (REPO / "docs" / "LEDGER.md").read_text(encoding="utf-8")
    res = fn("M1-T00z", ledger_text=text)
    return f"sentinel_todo={res.row_found and not res.is_done}"


def probe_coverage_clean() -> str:
    layout = probe_layout(FIXTURE)
    text, records = read_species_with_source(layout)
    return f"uncovered={audit_species_coverage(text, records)}"


def probe_symbolic_disjoint() -> str:
    layout = probe_layout(FIXTURE)
    _, records = read_species_with_source(layout)
    ok = all(set(r.unparsed_fields) & set(r.symbolic_map) == set() for r in records)
    return f"disjoint={ok}"


def probe_moves_extract() -> str:
    layout = probe_layout(FIXTURE)
    records = read_moves(layout)
    path = FIXTURE / "src" / "data" / "moves_info.h"
    text = path.read_text()
    uncovered = audit_moves_coverage(text, records)
    return f"moves_count={len(records)} uncovered={uncovered}"


def probe_species_name() -> str:
    layout = probe_layout(FIXTURE)
    _, records = read_species_with_source(layout)
    by_id = {r.rom_id: r for r in records}
    s = by_id.get("SPECIES_SKARMORY")
    if s is None:
        return "species_name=absent"
    return f"species_name={s.species_name}"


def probe_national_dex() -> str:
    layout = probe_layout(FIXTURE)
    _, records = read_species_with_source(layout)
    by_id = {r.rom_id: r for r in records}
    s = by_id.get("SPECIES_SKARMORY")
    if s is None:
        return "natdex=absent"
    if s.national_dex is None:
        sym = s.symbolic_map.get("natDexNum")
        return f"natdex=symbol recorded={sym}"
    return f"natdex=int:{s.national_dex}"


def probe_counts() -> str:
    layout = probe_layout(FIXTURE)
    _, records = read_species_with_source(layout)
    moves = read_moves(layout)
    return f"counts=species:{len(records)} moves:{len(moves)}"


PROBES = {
    "ci-scope": probe_ci_scope,
    "ci-scope-excludes-guards": probe_ci_scope_excludes_guards,
    "guard-paths": probe_guard_paths_declared,
    "done-predicate": probe_done_predicate_has_no_sha_conjunct,
    "sentinel-present": probe_sentinel_present,
    "coverage-clean": probe_coverage_clean,
    "symbolic-disjoint": probe_symbolic_disjoint,
    "moves-extract": probe_moves_extract,
    "species-name": probe_species_name,
    "national-dex": probe_national_dex,
    "counts": probe_counts,
}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in PROBES:
        sys.stderr.write(f"usage: M1-T12_checks.py <{'|'.join(PROBES)}>\n")
        return 2
    sys.stdout.write(PROBES[argv[1]]())
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
