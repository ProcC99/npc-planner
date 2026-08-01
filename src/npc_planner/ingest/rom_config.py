from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from npc_planner.ingest.cparse import parse_defines
from npc_planner.ingest.rom_probe import RomLayout


class RomConfigError(ValueError):
    """Raised when essential ROM config files are missing or unreadable."""


@dataclass(frozen=True)
class UnevaluatedExpr:
    symbol: str
    source_file: str
    raw: str
    reason: str


@dataclass(frozen=True)
class RomConfig:
    battle: Mapping[str, int | str]
    species: Mapping[str, int | str]
    pokemon: Mapping[str, int | str]
    limits: Mapping[str, int]
    ai_flags: Mapping[str, int]
    difficulties: Mapping[str, int]
    unevaluated: tuple[UnevaluatedExpr, ...]


def evaluate_int_expr(raw: str, known: Mapping[str, int]) -> int | None:
    """Evaluate C integer expressions involving literals, shifts, |, +, -, and known symbols."""
    raw_str = raw.strip()
    if not raw_str:
        return None

    tokens: list[tuple[str, str]] = []
    i = 0
    n = len(raw_str)
    while i < n:
        c = raw_str[i]
        if c.isspace():
            i += 1
            continue
        if c in ("(", ")", "|", "+", "-"):
            tokens.append(("OP", c))
            i += 1
            continue
        if c == "<" and i + 1 < n and raw_str[i + 1] == "<":
            tokens.append(("OP", "<<"))
            i += 2
            continue
        if c == "0" and i + 1 < n and (raw_str[i + 1] in ("x", "X")):
            j = i + 2
            while j < n and raw_str[j] in "0123456789abcdefABCDEF":
                j += 1
            tokens.append(("HEX", raw_str[i:j]))
            i = j
            continue
        if c.isdigit():
            j = i
            while j < n and raw_str[j].isdigit():
                j += 1
            tokens.append(("DEC", raw_str[i:j]))
            i = j
            continue
        if c.isalpha() or c == "_":
            j = i
            while j < n and (raw_str[j].isalnum() or raw_str[j] == "_"):
                j += 1
            tokens.append(("IDENT", raw_str[i:j]))
            i = j
            continue
        return None

    if not tokens:
        return None

    pos = 0

    def parse_expr() -> int | None:
        return parse_bitwise_or()

    def parse_bitwise_or() -> int | None:
        nonlocal pos
        val = parse_add_sub()
        if val is None:
            return None
        while pos < len(tokens) and tokens[pos] == ("OP", "|"):
            pos += 1
            rhs = parse_add_sub()
            if rhs is None:
                return None
            val = val | rhs
        return val

    def parse_add_sub() -> int | None:
        nonlocal pos
        val = parse_shift()
        if val is None:
            return None
        while (
            pos < len(tokens)
            and tokens[pos][0] == "OP"
            and tokens[pos][1] in ("+", "-")
        ):
            op = tokens[pos][1]
            pos += 1
            rhs = parse_shift()
            if rhs is None:
                return None
            if op == "+":
                val = val + rhs
            else:
                val = val - rhs
        return val

    def parse_shift() -> int | None:
        nonlocal pos
        val = parse_primary()
        if val is None:
            return None
        while pos < len(tokens) and tokens[pos] == ("OP", "<<"):
            pos += 1
            rhs = parse_primary()
            if rhs is None:
                return None
            val = val << rhs
        return val

    def parse_primary() -> int | None:
        nonlocal pos
        if pos >= len(tokens):
            return None
        t_type, t_val = tokens[pos]
        if t_type == "DEC":
            pos += 1
            try:
                return int(t_val, 10)
            except ValueError:
                return None
        if t_type == "HEX":
            pos += 1
            try:
                return int(t_val, 16)
            except ValueError:
                return None
        if t_type == "IDENT":
            pos += 1
            if t_val in known:
                return known[t_val]
            return None
        if t_type == "OP" and t_val == "(":
            pos += 1
            val = parse_expr()
            if val is None:
                return None
            if pos >= len(tokens) or tokens[pos] != ("OP", ")"):
                return None
            pos += 1
            return val
        return None

    res = parse_expr()
    if res is not None and pos == len(tokens):
        return res
    return None


def read_rom_config(layout: RomLayout) -> RomConfig:
    """Read ROM configuration headers and constant definitions into a RomConfig object."""
    # 1. Config headers under include/config/
    battle_h = None
    for p in layout.config_headers:
        if p.name == "battle.h":
            battle_h = p
            break
    if battle_h is None or not battle_h.exists():
        missing_path = battle_h if battle_h is not None else "include/config/battle.h"
        raise RomConfigError(f"Missing required config header: {missing_path}")

    battle_map: dict[str, int | str] = {}
    species_map: dict[str, int | str] = {}
    pokemon_map: dict[str, int | str] = {}

    for header_path in layout.config_headers:
        if not header_path.exists():
            continue
        text = header_path.read_text(encoding="utf-8")
        defines = parse_defines(text)
        for name, val_str in defines.items():
            val_clean = val_str.strip()
            if val_clean.isdigit():
                parsed_val: int | str = int(val_clean)
            else:
                parsed_val = val_clean
            if name.startswith("B_"):
                battle_map[name] = parsed_val
            elif name.startswith("P_"):
                species_map[name] = parsed_val
            else:
                pokemon_map[name] = parsed_val

    # 2. Constant headers under include/constants/
    raw_constants: list[tuple[str, str, str]] = []
    for const_path in layout.config_constants:
        if not const_path.exists():
            continue
        rel_path = str(const_path)
        try:
            rel_path = const_path.as_posix()
            if "tests/fixtures/" in rel_path or "include/constants/" in rel_path:
                rel_path = rel_path[rel_path.index("include/constants/") :]
        except ValueError:
            pass

        text = const_path.read_text(encoding="utf-8")
        defines = parse_defines(text)
        for name, val_str in defines.items():
            raw_constants.append((name, val_str, rel_path))

    known_consts: dict[str, int] = {}
    remaining = list(raw_constants)

    # Iterative evaluation pass
    changed = True
    while changed:
        changed = False
        next_remaining = []
        for symbol, raw_val, src in remaining:
            evaluated = evaluate_int_expr(raw_val, known_consts)
            if evaluated is not None:
                known_consts[symbol] = evaluated
                changed = True
            else:
                next_remaining.append((symbol, raw_val, src))
        remaining = next_remaining

    limits_map: dict[str, int] = {}
    ai_flags_map: dict[str, int] = {}
    difficulties_map: dict[str, int] = {}
    unevaluated_list: list[UnevaluatedExpr] = []

    for symbol, raw_val, src in raw_constants:
        if symbol in known_consts:
            val = known_consts[symbol]
            if symbol.startswith("AI_FLAG_"):
                ai_flags_map[symbol] = val
            elif symbol.startswith("DIFFICULTY_"):
                difficulties_map[symbol] = val
            else:
                limits_map[symbol] = val
        else:
            if symbol.startswith(("AI_FLAG_", "DIFFICULTY_")) or symbol in (
                "PARTY_SIZE",
                "MAX_MON_MOVES",
                "NUM_STORAGE_BOXES",
                "MAX_TRAINER_ITEMS",
            ):
                unevaluated_list.append(
                    UnevaluatedExpr(
                        symbol=symbol,
                        source_file=src,
                        raw=raw_val,
                        reason="unresolvable expression or symbol",
                    )
                )

    # Deterministic sorting
    sorted_battle = dict(sorted(battle_map.items()))
    sorted_species = dict(sorted(species_map.items()))
    sorted_pokemon = dict(sorted(pokemon_map.items()))
    sorted_limits = dict(sorted(limits_map.items()))
    sorted_ai_flags = dict(sorted(ai_flags_map.items()))
    sorted_difficulties = dict(sorted(difficulties_map.items()))

    sorted_unevaluated = tuple(
        sorted(unevaluated_list, key=lambda u: (u.source_file, u.symbol))
    )

    return RomConfig(
        battle=sorted_battle,
        species=sorted_species,
        pokemon=sorted_pokemon,
        limits=sorted_limits,
        ai_flags=sorted_ai_flags,
        difficulties=sorted_difficulties,
        unevaluated=sorted_unevaluated,
    )


def physical_special_split_enabled(config: RomConfig) -> bool:
    val = config.battle.get("B_PHYSICAL_SPECIAL_SPLIT")
    return val in (1, "1", True, "TRUE", "True")


def enabled_generations(config: RomConfig) -> frozenset[int]:
    gens: set[int] = set()
    for k, v in config.species.items():
        if (
            k.startswith("P_GEN_")
            and k.endswith("_POKEMON")
            and v in (1, "1", True, "TRUE", "True")
        ):
            try:
                gen_num = int(k.split("_")[2])
                gens.add(gen_num)
            except ValueError:
                pass
    return frozenset(gens)
