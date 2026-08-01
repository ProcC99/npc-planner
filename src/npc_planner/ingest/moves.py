from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

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
        "name",
        "type",
        "power",
        "accuracy",
        "pp",
        "effect",
        "target",
        "priority",
        "category",
    }
)

IGNORED_FIELDS: frozenset[str] = frozenset()


class MoveParseError(ValueError):
    """Raised on malformed move initializers or missing required fields."""


@dataclass(frozen=True)
class MoveRecord:
    rom_id: str
    move_name: str
    type: str | None
    power: int | None
    accuracy: int | None
    pp: int | None
    effect: str | None
    target: str | None
    priority: int | None
    category: str | None
    source_file: str
    source_record: str
    unparsed_fields: tuple[str, ...]
    symbolic_fields: tuple[tuple[str, str], ...]
    unevaluated_fields: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        sym_keys = tuple(k for k, _ in self.symbolic_fields)
        if sym_keys != tuple(sorted(sym_keys)):
            raise MoveParseError("symbolic_fields must be sorted by key")
        uneval_keys = tuple(k for k, _ in self.unevaluated_fields)
        if uneval_keys != tuple(sorted(uneval_keys)):
            raise MoveParseError("unevaluated_fields must be sorted by key")

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
                        raise MoveParseError(
                            f"field in multiple sets: {sorted(overlap)}"
                        )

    @property
    def symbolic_map(self) -> dict[str, str]:
        return dict(self.symbolic_fields)

    @property
    def unevaluated_map(self) -> dict[str, str]:
        return dict(self.unevaluated_fields)


def _parse_int_or_symbol(
    val: Any,
    field_name: str,
    symbolic: list[tuple[str, str]],
    unevaluated: list[tuple[str, str]],
) -> int | None:
    if val is None:
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, CExpr):
        unevaluated.append((field_name, val.raw))
        return None
    if isinstance(val, str):
        if val.isdigit() or (val.startswith("-") and val[1:].isdigit()):
            return int(val)
        symbolic.append((field_name, val))
        return None
    symbolic.append((field_name, str(val)))
    return None


def _parse_str_or_expr(
    val: Any,
    field_name: str,
    unevaluated: list[tuple[str, str]],
) -> str | None:
    """Extract a string-typed mapped field, routing CExpr to unevaluated_fields."""
    if val is None:
        return None
    if isinstance(val, CExpr):
        unevaluated.append((field_name, val.raw))
        return None
    return str(val)


def parse_moves(text: str, source_file: str) -> tuple[MoveRecord, ...]:
    records: list[MoveRecord] = []
    try:
        raw_items = parse_array_initializer(text, "gMovesInfo")
    except CParseError as err:
        raise MoveParseError(f"C parse error in {source_file}: {err}") from err

    for rom_id, raw_dict in raw_items.items():
        if not rom_id.startswith("MOVE_"):
            continue

        symbolic_list: list[tuple[str, str]] = []
        unevaluated_list: list[tuple[str, str]] = []

        # Name
        raw_name = raw_dict.get("name")
        if isinstance(raw_name, CMacroCall) and raw_name.name in (
            "_",
            "g",
            "COMPOUND_STRING",
        ):
            if len(raw_name.args) != 1:
                raise MoveParseError(
                    f"name macro {raw_name.name} has {len(raw_name.args)} args, "
                    f"expected 1 for {rom_id}"
                )
            move_name = _clean_string_literal(str(raw_name.args[0]))
        elif isinstance(raw_name, str):
            move_name = _clean_string_literal(raw_name)
        else:
            move_name = rom_id.removeprefix("MOVE_").replace("_", " ").title()

        # Type, Effect, Target — all str | None with CExpr routing
        move_type = _parse_str_or_expr(
            raw_dict.get("type", "TYPE_NONE"), "type", unevaluated_list
        )
        effect = _parse_str_or_expr(
            raw_dict.get("effect", "EFFECT_HIT"), "effect", unevaluated_list
        )
        target = _parse_str_or_expr(
            raw_dict.get("target", "TARGET_SELECTED"), "target", unevaluated_list
        )

        # Power, Accuracy, PP, Priority
        power = _parse_int_or_symbol(
            raw_dict.get("power"), "power", symbolic_list, unevaluated_list
        )
        accuracy = _parse_int_or_symbol(
            raw_dict.get("accuracy"), "accuracy", symbolic_list, unevaluated_list
        )
        pp = _parse_int_or_symbol(
            raw_dict.get("pp"), "pp", symbolic_list, unevaluated_list
        )
        priority = _parse_int_or_symbol(
            raw_dict.get("priority"), "priority", symbolic_list, unevaluated_list
        )

        # Category (verbatim symbol if present, else None)
        raw_cat = raw_dict.get("category")
        category = _parse_str_or_expr(raw_cat, "category", unevaluated_list)

        # Unparsed keys
        unparsed_set: set[str] = set()
        for k in raw_dict:
            if k not in MAPPED_FIELDS and k not in IGNORED_FIELDS:
                unparsed_set.add(k)

        symbolic_sorted = tuple(sorted(symbolic_list, key=lambda x: x[0]))
        unevaluated_sorted = tuple(sorted(unevaluated_list, key=lambda x: x[0]))
        unparsed_tuple = tuple(sorted(unparsed_set))

        records.append(
            MoveRecord(
                rom_id=rom_id,
                move_name=move_name,
                type=move_type,
                power=power,
                accuracy=accuracy,
                pp=pp,
                effect=effect,
                target=target,
                priority=priority,
                category=category,
                source_file=source_file,
                source_record=rom_id,
                unparsed_fields=unparsed_tuple,
                symbolic_fields=symbolic_sorted,
                unevaluated_fields=unevaluated_sorted,
            )
        )

    records.sort(key=lambda r: r.rom_id)
    return tuple(records)


def read_moves(layout: RomLayout) -> tuple[MoveRecord, ...]:
    path = layout.moves_info
    if not path.exists():
        return ()
    return parse_moves(path.read_text(encoding="utf-8"), str(path))


def audit_moves_coverage(
    text: str,
    records: Sequence[MoveRecord],
) -> tuple[str, ...]:
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
