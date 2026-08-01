#!/usr/bin/env python3
"""Single-line probes used by scripts/accept/M1-T11.sh.

Each subcommand prints exactly one line of the form `key=value`, so the shell
side stays free of embedded C fixtures and quoting games. Keeping the synthetic
headers here also means they are lint-checked and type-checked like everything
else, instead of hiding inside a shell string.

Usage:  python3 scripts/accept/M1-T11_checks.py <probe>
"""

from __future__ import annotations

import sys
from pathlib import Path

from npc_planner.ingest.rom_probe import RomLayout, probe_layout
from npc_planner.ingest.species import (
    IGNORED_FIELDS,
    MAPPED_FIELDS,
    SpeciesParseError,
    SpeciesRecord,
    audit_species_coverage,
    parse_species,
    read_species_with_source,
)

FIXTURE = Path("tests/fixtures/fake_rom")

STATS_ONLY_FIVE = """
const struct SpeciesInfo gSpeciesInfo[] = {
    [SPECIES_TESTMON] = {
        .baseHP = 50, .baseAttack = 50, .baseDefense = 50,
        .baseSpAttack = 50, .baseSpDefense = 50,
        .types = MON_TYPES(TYPE_NORMAL),
        .abilities = { ABILITY_RUN_AWAY },
        .speciesName = _("Testmon"),
    },
};
"""

NO_TYPES = """
const struct SpeciesInfo gSpeciesInfo[] = {
    [SPECIES_TESTMON] = {
        .baseHP = 50, .baseAttack = 50, .baseDefense = 50,
        .baseSpAttack = 50, .baseSpDefense = 50, .baseSpeed = 50,
        .abilities = { ABILITY_RUN_AWAY },
        .speciesName = _("Testmon"),
    },
};
"""

MONOTYPE_TWICE = """
const struct SpeciesInfo gSpeciesInfo[] = {
    [SPECIES_TESTMON] = {
        .baseHP = 50, .baseAttack = 50, .baseDefense = 50,
        .baseSpAttack = 50, .baseSpDefense = 50, .baseSpeed = 50,
        .types = MON_TYPES(TYPE_ELECTRIC, TYPE_ELECTRIC),
        .abilities = { ABILITY_STATIC },
        .speciesName = _("Testmon"),
    },
};
"""

WELL_FORMED = """
const struct SpeciesInfo gSpeciesInfo[] = {
    [SPECIES_TESTMON] = {
        .baseHP = 50, .baseAttack = 50, .baseDefense = 50,
        .baseSpAttack = 50, .baseSpDefense = 50, .baseSpeed = 50,
        .types = MON_TYPES(TYPE_NORMAL),
        .abilities = { ABILITY_RUN_AWAY },
        .speciesName = _("Testmon"),
    },
};
"""

DUPLICATE_KEY = WELL_FORMED.replace(
    "};",
    """    [SPECIES_TESTMON] = {
        .baseHP = 60, .baseAttack = 60, .baseDefense = 60,
        .baseSpAttack = 60, .baseSpDefense = 60, .baseSpeed = 60,
        .types = MON_TYPES(TYPE_NORMAL),
        .abilities = { ABILITY_RUN_AWAY },
        .speciesName = _("Testmon"),
    },
};""",
)

UNKNOWN_KEY = WELL_FORMED.replace(
    '.speciesName = _("Testmon"),',
    '.speciesName = _("Testmon"),\n        .someUnknownRomField = 123,',
)


def _load() -> tuple[RomLayout, str, tuple[SpeciesRecord, ...]]:
    layout = probe_layout(FIXTURE)
    text, records = read_species_with_source(layout)
    return layout, text, records


def _raises(text: str) -> bool:
    try:
        parse_species(text, "synthetic.h")
    except SpeciesParseError:
        return True
    return False


def probe_skarmory() -> str:
    _, _, records = _load()
    by_id = {r.rom_id: r for r in records}
    s = by_id.get("SPECIES_SKARMORY")
    if s is None:
        return "skarmory=absent"
    b = s.base_stats
    return (
        f"skarmory={b.hp}|{b.attack}|{b.defense}|{b.sp_attack}|{b.sp_defense}|{b.speed}|"
        f"{','.join(s.types)}|{s.hidden_ability}|{s.abilities[0]}"
    )


def probe_invariants() -> str:
    _, _, records = _load()
    stats = [
        v
        for r in records
        for v in (
            r.base_stats.hp,
            r.base_stats.attack,
            r.base_stats.defense,
            r.base_stats.sp_attack,
            r.base_stats.sp_defense,
            r.base_stats.speed,
        )
    ]
    ok = (
        all(isinstance(v, int) and 0 <= v <= 255 for v in stats)
        and all(t.startswith("TYPE_") for r in records for t in r.types)
        and all(a.startswith("ABILITY_") for r in records for a in r.abilities)
        and all(1 <= len(r.types) <= 2 for r in records)
        and all(not r.source_file.startswith("/") for r in records)
    )
    return f"invariants={ok}"


def probe_ordering() -> str:
    layout, _, records = _load()
    ids = [r.rom_id for r in records]
    _, r_recs = read_species_with_source(layout)
    return f"ordering={ids == sorted(ids) and r_recs == records}"


def probe_provenance() -> str:
    _, _, records = _load()
    ok = all(
        r.source_type == "rom_extract" and abs(r.confidence - 0.80) < 1e-9
        for r in records
    )
    return f"provenance={ok}"


def probe_coverage_clean() -> str:
    _, text, records = _load()
    return f"uncovered={audit_species_coverage(text, records)}"


def probe_coverage_detects() -> str:
    found = audit_species_coverage(UNKNOWN_KEY, [])
    return f"detects={'someUnknownRomField' in found}"


def probe_ignored_pinned() -> str:
    return f"ignored_pinned={isinstance(IGNORED_FIELDS, frozenset)}"


def probe_refusals() -> str:
    return f"refusals={_raises(STATS_ONLY_FIVE)},{_raises(NO_TYPES)},{_raises(DUPLICATE_KEY)}"


def probe_monotype() -> str:
    r = parse_species(MONOTYPE_TWICE, "synthetic.h")[0]
    return f"monotype={len(r.types)}/{len(r.raw_types)}"


def probe_string_only() -> str:
    return f"string_only={len(parse_species(WELL_FORMED, 'synthetic.h')) == 1}"


def probe_counts() -> str:
    _, text, records = _load()
    unparsed = {k for r in records for k in r.unparsed_fields}
    seen = set(MAPPED_FIELDS) | set(IGNORED_FIELDS) | unparsed
    seen |= set(audit_species_coverage(text, records))
    return f"counts=species:{len(records)} keys_seen:{len(seen)} unparsed_keys:{len(unparsed)} ignored:{len(IGNORED_FIELDS)}"


PROBES = {
    "skarmory": probe_skarmory,
    "invariants": probe_invariants,
    "ordering": probe_ordering,
    "provenance": probe_provenance,
    "coverage-clean": probe_coverage_clean,
    "coverage-detects": probe_coverage_detects,
    "ignored-pinned": probe_ignored_pinned,
    "refusals": probe_refusals,
    "monotype": probe_monotype,
    "string-only": probe_string_only,
    "counts": probe_counts,
}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in PROBES:
        sys.stderr.write(f"usage: M1-T11_checks.py <{'|'.join(PROBES)}>\n")
        return 2
    sys.stdout.write(PROBES[argv[1]]())
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
