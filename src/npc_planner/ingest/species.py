from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from npc_planner.ingest.cparse import (
    CExpr,
    CMacroCall,
    CParseError,
    _clean_string_literal,
    parse_array_initializer,
)
from npc_planner.ingest.rom_probe import RomLayout

MAPPED_FIELDS: frozenset[str] = frozenset(
    {
        "baseHP",
        "baseAttack",
        "baseDefense",
        "baseSpAttack",
        "baseSpDefense",
        "baseSpeed",
        "types",
        "abilities",
        "hiddenAbility",
        "speciesName",
        "natDexNum",
    }
)

IGNORED_FIELDS: frozenset[str] = frozenset()


class SpeciesParseError(ValueError):
    """Raised on malformed species initializers or missing required fields."""


@dataclass(frozen=True)
class BaseStats:
    hp: int
    attack: int
    defense: int
    sp_attack: int
    sp_defense: int
    speed: int


@dataclass(frozen=True)
class SpeciesRecord:
    rom_id: str
    species_name: str
    national_dex: int | None
    base_stats: BaseStats
    types: tuple[str, ...]
    raw_types: tuple[str, ...]
    abilities: tuple[str, ...]
    hidden_ability: str | None
    source_file: str
    source_record: str
    unparsed_fields: tuple[str, ...]
    symbolic_fields: tuple[tuple[str, str], ...]
    unevaluated_fields: tuple[tuple[str, str], ...]
    source_type: str = "rom_extract"
    confidence: float = 0.80
    raw_initializer_keys: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        sym_keys = tuple(k for k, _ in self.symbolic_fields)
        if sym_keys != tuple(sorted(sym_keys)):
            raise SpeciesParseError("symbolic_fields must be sorted by key")
        uneval_keys = tuple(k for k, _ in self.unevaluated_fields)
        if uneval_keys != tuple(sorted(uneval_keys)):
            raise SpeciesParseError("unevaluated_fields must be sorted by key")

        # Three-way disjointness
        all_sets = [
            set(self.unparsed_fields),
            set(sym_keys),
            set(uneval_keys),
        ]
        for i, a in enumerate(all_sets):
            for j, b in enumerate(all_sets):
                if i < j:
                    overlap = a & b
                    if overlap:
                        raise SpeciesParseError(
                            f"field in multiple sets: {sorted(overlap)}"
                        )

    @property
    def symbolic_map(self) -> dict[str, str]:
        return dict(self.symbolic_fields)

    @property
    def unevaluated_map(self) -> dict[str, str]:
        return dict(self.unevaluated_fields)


def _extract_types(val: object, key: str) -> tuple[str, ...]:
    raw_types: list[str] = []
    if isinstance(val, list):
        for item in val:
            if isinstance(item, str):
                raw_types.append(item)
    elif isinstance(val, CMacroCall):
        for arg in val.args:
            if isinstance(arg, str):
                raw_types.append(arg)
    elif isinstance(val, str):
        raw_types.append(val)

    if not raw_types:
        raise SpeciesParseError(f"E_SPECIES_NO_TYPES: Missing or empty types for {key}")

    return tuple(raw_types)


def _extract_abilities(val: object) -> tuple[str, ...]:
    abs_list: list[str] = []
    if isinstance(val, list):
        for item in val:
            if isinstance(item, str):
                abs_list.append(item)
    elif isinstance(val, CMacroCall):
        for arg in val.args:
            if isinstance(arg, str):
                abs_list.append(arg)
    elif isinstance(val, str):
        abs_list.append(val)
    return tuple(abs_list)


def parse_species(text: str, source_file: str) -> tuple[SpeciesRecord, ...]:
    """Parse species initializers from C text into SpeciesRecord instances sorted by rom_id."""
    clean_file = source_file.lstrip("/")

    # Check duplicate species keys
    keys_in_text = re.findall(r"\[\s*([A-Za-z0-9_]+)\s*\]\s*=\s*\{", text)
    seen_keys: set[str] = set()
    for k in keys_in_text:
        if k.startswith("SPECIES_"):
            if k in seen_keys:
                raise SpeciesParseError(f"Duplicate species key '{k}' in {clean_file}")
            seen_keys.add(k)

    try:
        raw_items = parse_array_initializer(text, "gSpeciesInfo")
    except CParseError as exc:
        raise SpeciesParseError(str(exc)) from exc

    records: list[SpeciesRecord] = []
    for key, fields in raw_items.items():
        if not key.startswith("SPECIES_"):
            continue

        raw_keys_tuple = tuple(fields.keys())

        # Validate species_name
        if "speciesName" not in fields:
            raise SpeciesParseError(f"Missing speciesName field for {key}")
        raw_name = fields["speciesName"]
        if not isinstance(raw_name, str):
            raise SpeciesParseError(f"Invalid speciesName for {key}")
        clean_name = _clean_string_literal(raw_name)
        if not clean_name:
            raise SpeciesParseError(f"Empty speciesName for {key}")
        species_name = clean_name

        # Validate national_dex
        national_dex: int | None = None
        symbolic_list: list[tuple[str, str]] = []
        unevaluated_list: list[tuple[str, str]] = []
        if "natDexNum" in fields:
            raw_dex = fields["natDexNum"]
            if isinstance(raw_dex, int):
                national_dex = raw_dex
            elif isinstance(raw_dex, str) and raw_dex.isdigit():
                national_dex = int(raw_dex)
            elif isinstance(raw_dex, CExpr):
                national_dex = None
                unevaluated_list.append(("natDexNum", raw_dex.raw))
            else:
                national_dex = None
                symbolic_list.append(("natDexNum", str(raw_dex)))

        # Validate base stats
        stat_names = (
            ("baseHP", "hp"),
            ("baseAttack", "attack"),
            ("baseDefense", "defense"),
            ("baseSpAttack", "sp_attack"),
            ("baseSpDefense", "sp_defense"),
            ("baseSpeed", "speed"),
        )
        stat_vals: dict[str, int] = {}
        for c_name, py_name in stat_names:
            if c_name not in fields:
                raise SpeciesParseError(f"Missing base stat '{c_name}' for {key}")
            raw_v = fields[c_name]
            if not isinstance(raw_v, int) or not (0 <= raw_v <= 255):
                raise SpeciesParseError(
                    f"Invalid stat '{c_name}' value {raw_v} for {key}"
                )
            stat_vals[py_name] = raw_v

        base_stats = BaseStats(
            hp=stat_vals["hp"],
            attack=stat_vals["attack"],
            defense=stat_vals["defense"],
            sp_attack=stat_vals["sp_attack"],
            sp_defense=stat_vals["sp_defense"],
            speed=stat_vals["speed"],
        )

        # Parse types
        if "types" not in fields:
            raise SpeciesParseError(
                f"E_SPECIES_NO_TYPES: Missing types field for {key}"
            )
        raw_types = _extract_types(fields["types"], key)
        for t in raw_types:
            if not t.startswith("TYPE_"):
                raise SpeciesParseError(
                    f"Type '{t}' does not start with TYPE_ for {key}"
                )

        # Normalise types (preserve order, deduplicate)
        norm_types_list: list[str] = []
        for t in raw_types:
            if t not in norm_types_list:
                norm_types_list.append(t)
        norm_types = tuple(norm_types_list)

        # Parse abilities
        raw_abilities = _extract_abilities(fields.get("abilities", []))
        for a in raw_abilities:
            if not a.startswith("ABILITY_"):
                raise SpeciesParseError(
                    f"Ability '{a}' does not start with ABILITY_ for {key}"
                )

        hidden_ability: str | None = None
        if "hiddenAbility" in fields and isinstance(fields["hiddenAbility"], str):
            hidden_ability = fields["hiddenAbility"]
        elif len(raw_abilities) >= 3 and raw_abilities[2] != "ABILITY_NONE":
            hidden_ability = raw_abilities[2]

        # Determine unparsed fields
        unparsed: set[str] = set()
        for k in fields:
            if k not in MAPPED_FIELDS and k not in IGNORED_FIELDS:
                unparsed.add(k)

        symbolic_sorted = tuple(sorted(symbolic_list, key=lambda x: x[0]))
        unevaluated_sorted = tuple(sorted(unevaluated_list, key=lambda x: x[0]))

        records.append(
            SpeciesRecord(
                rom_id=key,
                species_name=species_name,
                national_dex=national_dex,
                base_stats=base_stats,
                types=norm_types,
                raw_types=raw_types,
                abilities=raw_abilities,
                hidden_ability=hidden_ability,
                source_file=clean_file,
                source_record=key,
                unparsed_fields=tuple(sorted(unparsed)),
                symbolic_fields=symbolic_sorted,
                unevaluated_fields=unevaluated_sorted,
                source_type="rom_extract",
                confidence=0.80,
                raw_initializer_keys=raw_keys_tuple,
            )
        )

    records.sort(key=lambda r: r.rom_id)
    return tuple(records)


def read_species(layout: RomLayout) -> tuple[SpeciesRecord, ...]:
    """Read and parse species information from layout.species_info."""
    _, records = read_species_with_source(layout)
    return records


def read_species_with_source(
    layout: RomLayout,
) -> tuple[str, tuple[SpeciesRecord, ...]]:
    """Read species C source text and parse records from layout.species_info."""
    all_texts: list[str] = []
    all_records: list[SpeciesRecord] = []

    all_paths = list(layout.config_headers) + list(layout.species_info)
    root = (
        all_paths[0].parents[2]
        if len(all_paths[0].parents) >= 3
        else all_paths[0].parent
    )

    for p in layout.species_info:
        if p.exists():
            text = p.read_text(encoding="utf-8")
            all_texts.append(text)
            try:
                rel_path = str(p.relative_to(root))
            except ValueError:
                rel_path = str(p)
            recs = parse_species(text, rel_path)
            all_records.extend(recs)

    all_records.sort(key=lambda r: r.rom_id)
    combined_text = "\n".join(all_texts)
    return combined_text, tuple(all_records)


def audit_species_coverage(
    text: str, records: Sequence[SpeciesRecord]
) -> tuple[str, ...]:
    """Every `.identifier =` key appearing inside gSpeciesInfo[] in `text` that is not

    in MAPPED_FIELDS, not in IGNORED_FIELDS, and not recorded in any record's
    unparsed_fields, symbolic_map, or unevaluated_map. Empty means genuinely total
    coverage.
    """
    raw_keys_in_text: set[str] = set(re.findall(r"\.([A-Za-z0-9_]+)\s*=", text))
    unparsed_in_records: set[str] = {k for r in records for k in r.unparsed_fields}
    symbolic_keys_in_records: set[str] = {k for r in records for k in r.symbolic_map}
    unevaluated_keys_in_records: set[str] = {
        k for r in records for k in r.unevaluated_map
    }

    accounted = (
        MAPPED_FIELDS
        | IGNORED_FIELDS
        | unparsed_in_records
        | symbolic_keys_in_records
        | unevaluated_keys_in_records
    )
    unaccounted = raw_keys_in_text - accounted
    return tuple(sorted(unaccounted))
