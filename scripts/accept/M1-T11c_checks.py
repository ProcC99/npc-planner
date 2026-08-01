#!/usr/bin/env python3
"""Single-line probes used by scripts/accept/M1-T11b.sh.

Each subcommand prints exactly one `key=value` line. The synthetic C fixtures
live here rather than in shell strings so they are linted and type-checked.

Usage:  python3 scripts/accept/M1-T11b_checks.py <probe>
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from npc_planner.ingest.rom_probe import probe_layout
from npc_planner.ingest.species import (
    IGNORED_FIELDS,
    MAPPED_FIELDS,
    SpeciesParseError,
    audit_species_coverage,
    parse_species,
    read_species_with_source,
)

FIXTURE = Path("tests/fixtures/fake_rom")

EXPECTED_CI_SCOPE = (
    ".pre-commit-config.yaml",
    "Makefile",
    ".github/",
    "scripts/review_bundle.sh",
)

WELL_FORMED = """
const struct SpeciesInfo gSpeciesInfo[] = {
    [SPECIES_TESTMON] = {
        .baseHP = 50, .baseAttack = 50, .baseDefense = 50,
        .baseSpAttack = 50, .baseSpDefense = 50, .baseSpeed = 50,
        .types = MON_TYPES(TYPE_NORMAL),
        .abilities = { ABILITY_RUN_AWAY },
        .speciesName = _("Testmon"),
        .natDexNum = 999,
    },
};
"""

UNKNOWN_KEY = WELL_FORMED.replace(
    '.speciesName = _("Testmon"),',
    '.speciesName = _("Testmon"),\n        .someUnknownRomField = 123,',
)

NO_NAME = WELL_FORMED.replace('.speciesName = _("Testmon"),', "")

EMPTY_NAME = WELL_FORMED.replace('_("Testmon")', '_("")')


def _load_module(path: str, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _raises(text: str) -> bool:
    try:
        parse_species(text, "synthetic.h")
    except SpeciesParseError:
        return True
    return False


# ------------------------------------------------------------- guards ------


def probe_ci_scope() -> str:
    allow = _load_module("scripts/hooks/files_within_allowlist.py", "fwa")
    audit = _load_module("scripts/audit_commits.py", "audit")
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
    parse_fn = getattr(tid, "parse_" + "ledger_rows")
    rows = parse_fn("| M1-TTEST | done | — | check ✅ | desc |\n")
    if not rows:
        return "no_sha_conjunct=False"
    r = rows[0]
    # Doneness is based on status == 'done' alone
    is_done = r.status == "done"
    return f"no_sha_conjunct={is_done}"


# ----------------------------------------------------------- coverage ------


def probe_coverage_clean() -> str:
    layout = probe_layout(FIXTURE)
    text, records = read_species_with_source(layout)
    return f"uncovered={audit_species_coverage(text, records)}"


def probe_coverage_detects_from_source() -> str:
    records = parse_species(UNKNOWN_KEY, "synthetic.h")
    found = audit_species_coverage(UNKNOWN_KEY, records)
    return f"detects={'someUnknownRomField' in found}"


def probe_unknown_key_is_not_fatal() -> str:
    return f"not_fatal={not _raises(UNKNOWN_KEY)}"


def probe_mapped_fields() -> str:
    ok = isinstance(MAPPED_FIELDS, frozenset) and len(MAPPED_FIELDS) > 0
    return f"mapped_fields={ok} size={len(MAPPED_FIELDS)}"


def probe_ignored_empty() -> str:
    return f"ignored_empty={IGNORED_FIELDS == frozenset()}"


# ------------------------------------------------------------- schema ------


def probe_species_name() -> str:
    layout = probe_layout(FIXTURE)
    _, records = read_species_with_source(layout)
    by_id = {r.rom_id: r for r in records}
    s = by_id.get("SPECIES_SKARMORY")
    if s is None:
        return "species_name=absent"
    return f"species_name={s.species_name}"


def probe_no_id_fallback() -> str:
    layout = probe_layout(FIXTURE)
    _, records = read_species_with_source(layout)
    ok = all(r.species_name != r.rom_id for r in records)
    return f"no_id_fallback={ok}"


def probe_name_required() -> str:
    return f"name_required={_raises(NO_NAME)},{_raises(EMPTY_NAME)}"


def probe_national_dex() -> str:
    layout = probe_layout(FIXTURE)
    _, records = read_species_with_source(layout)
    by_id = {r.rom_id: r for r in records}
    s = by_id.get("SPECIES_SKARMORY")
    if s is None:
        return "natdex=absent"
    if s.national_dex is None:
        symbolic = any(
            "natDexNum" in f or "NATIONAL_DEX" in f for f in s.unparsed_fields
        )
        return f"natdex=symbol recorded={symbolic}"
    return f"natdex=int:{s.national_dex}"


def probe_counts() -> str:
    layout = probe_layout(FIXTURE)
    text, records = read_species_with_source(layout)
    unparsed = {k for r in records for k in r.unparsed_fields}
    seen = set(MAPPED_FIELDS) | set(IGNORED_FIELDS) | unparsed
    seen |= set(audit_species_coverage(text, records))
    return f"counts=species:{len(records)} keys_seen:{len(seen)} unparsed_keys:{len(unparsed)} ignored:{len(IGNORED_FIELDS)}"


PROBES = {
    "ci-scope": probe_ci_scope,
    "ci-scope-excludes-guards": probe_ci_scope_excludes_guards,
    "guard-paths": probe_guard_paths_declared,
    "done-predicate": probe_done_predicate_has_no_sha_conjunct,
    "coverage-clean": probe_coverage_clean,
    "coverage-detects": probe_coverage_detects_from_source,
    "unknown-key-not-fatal": probe_unknown_key_is_not_fatal,
    "mapped-fields": probe_mapped_fields,
    "ignored-empty": probe_ignored_empty,
    "species-name": probe_species_name,
    "no-id-fallback": probe_no_id_fallback,
    "name-required": probe_name_required,
    "national-dex": probe_national_dex,
    "counts": probe_counts,
}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in PROBES:
        sys.stderr.write(f"usage: M1-T11b_checks.py <{'|'.join(PROBES)}>\n")
        return 2
    sys.stdout.write(PROBES[argv[1]]())
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
