"""Probe script for M1-T12b acceptance suite.

Run via bash scripts/accept/M1-T12b.sh.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Fix python import path
HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "src"))

from npc_planner.ingest.cparse import CExpr, _parse_c_value, parse_array_initializer
from npc_planner.ingest.moves import (
    MAPPED_FIELDS,
    audit_moves_coverage,
    read_moves,
)
from npc_planner.ingest.rom_probe import probe_layout
from npc_planner.ingest.species import SpeciesRecord

FIXTURE = REPO / "tests" / "fixtures" / "fake_rom"


def probe_split_removed() -> str:
    """Verify 'split' is not in MAPPED_FIELDS."""
    return f"split_absent={'split' not in MAPPED_FIELDS}"


def probe_will_o_wisp_name() -> str:
    """Will-O-Wisp name must come from COMPOUND_STRING, not rom_id derivation."""
    layout = probe_layout(FIXTURE)
    records = read_moves(layout)
    by_id = {r.rom_id: r for r in records}
    m = by_id.get("MOVE_WILL_O_WISP")
    if m is None:
        return "will_o_wisp=absent"
    derived = "MOVE_WILL_O_WISP".removeprefix("MOVE_").replace("_", " ").title()
    return (
        f"name={m.move_name} derived={derived} discriminates={m.move_name != derived}"
    )


def probe_compound_string_name() -> str:
    """COMPOUND_STRING is in the name macro check list."""
    layout = probe_layout(FIXTURE)
    records = read_moves(layout)
    by_id = {r.rom_id: r for r in records}
    m = by_id.get("MOVE_FLAMETHROWER")
    if m is None:
        return "flamethrower=absent"
    return f"name={m.move_name} correct={m.move_name == 'Flamethrower'}"


def probe_ternary_unevaluated() -> str:
    """Ternary expressions land in unevaluated_fields, not symbolic_fields."""
    layout = probe_layout(FIXTURE)
    records = read_moves(layout)
    by_id = {r.rom_id: r for r in records}
    m = by_id.get("MOVE_FLAMETHROWER")
    if m is None:
        return "flamethrower=absent"
    has_power_uneval = "power" in m.unevaluated_map
    power_is_none = m.power is None
    return f"power_unevaluated={has_power_uneval} power_none={power_is_none}"


def probe_cexpr_structural() -> str:
    """CExpr structural classification works."""
    val, _ = _parse_c_value("B >= GEN_6 ? 90 : 95", 0)
    is_cexpr = isinstance(val, CExpr)
    if is_cexpr:
        has_idents = len(val.identifiers) > 0
        return f"cexpr={is_cexpr} has_idents={has_idents} idents={val.identifiers}"
    return f"cexpr={is_cexpr}"


def probe_cexpr_single_ident_is_str() -> str:
    """Single identifiers remain str, not CExpr."""
    val, _ = _parse_c_value("DAMAGE_CATEGORY_PHYSICAL", 0)
    return f"type={type(val).__name__} val={val}"


def probe_toxic_category() -> str:
    """MOVE_TOXIC has DAMAGE_CATEGORY_STATUS via .category (not .split)."""
    layout = probe_layout(FIXTURE)
    records = read_moves(layout)
    by_id = {r.rom_id: r for r in records}
    m = by_id.get("MOVE_TOXIC")
    if m is None:
        return "toxic=absent"
    return f"category={m.category} correct={m.category == 'DAMAGE_CATEGORY_STATUS'}"


def probe_unevaluated_fields_present() -> str:
    """Both MoveRecord and SpeciesRecord have unevaluated_fields."""
    import dataclasses

    layout = probe_layout(FIXTURE)
    records = read_moves(layout)
    move_ok = all(hasattr(r, "unevaluated_fields") for r in records)
    species_field_names = [f.name for f in dataclasses.fields(SpeciesRecord)]
    species_ok = "unevaluated_fields" in species_field_names
    return f"move_has={move_ok} species_has={species_ok}"


def probe_coverage_audit() -> str:
    """Coverage audit against fake_rom fixture."""
    layout = probe_layout(FIXTURE)
    records = read_moves(layout)
    path = FIXTURE / "src" / "data" / "moves_info.h"
    text = path.read_text(encoding="utf-8")
    uncovered = audit_moves_coverage(text, records)
    # moveEffect and chance are false positives from ADDITIONAL_EFFECTS nesting
    real_uncovered = [k for k in uncovered if k not in ("moveEffect", "chance")]
    return f"uncovered={real_uncovered}"


def probe_duplicate_key_detection() -> str:
    """Duplicate key detection in cparse raises CParseError."""
    from npc_planner.ingest.cparse import CParseError

    text = """
const int arr[] = {
    [FOO] = {
        .name = 1,
        .name = 2,
    },
};
"""
    try:
        parse_array_initializer(text, "arr")
        return "duplicate_key=not_detected"
    except CParseError:
        return "duplicate_key=detected"


PROBES = {
    "split-removed": probe_split_removed,
    "will-o-wisp-name": probe_will_o_wisp_name,
    "compound-string-name": probe_compound_string_name,
    "ternary-unevaluated": probe_ternary_unevaluated,
    "cexpr-structural": probe_cexpr_structural,
    "cexpr-single-ident": probe_cexpr_single_ident_is_str,
    "toxic-category": probe_toxic_category,
    "unevaluated-fields": probe_unevaluated_fields_present,
    "coverage-audit": probe_coverage_audit,
    "duplicate-key": probe_duplicate_key_detection,
}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in PROBES:
        sys.stderr.write(f"usage: M1-T12b_checks.py <{'|'.join(PROBES)}>\n")
        return 2
    sys.stdout.write(PROBES[argv[1]]())
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
