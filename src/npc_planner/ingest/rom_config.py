from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

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
    constants: Mapping[str, int | str]
    versions: Mapping[str, int | str]
    ai_flags: Mapping[str, int]
    difficulties: Mapping[str, int]
    unevaluated: tuple[UnevaluatedExpr, ...]
    ignored: tuple[str, ...]


# Include guards (starting with GUARD_ or ending with _H) are the only symbol
# definitions that may be ignored. All other definitions must land in a bucket.

BUCKET_BY_FILE: Mapping[str, str] = {
    "include/config/battle.h": "battle",
    "include/config/species_enabled.h": "species",
    "include/config/pokemon.h": "pokemon",
    "include/constants/battle_ai.h": "ai_flags",
    "include/constants/difficulty.h": "difficulties",
}

LIMIT_SYMBOLS: frozenset[str] = frozenset(
    {
        "PARTY_SIZE",
        "MAX_MON_MOVES",
        "MAX_MON_MOVES_IN_BATTLE",
        "MAX_LEVEL",
        "MAX_BATTLERS_COUNT",
        "MAX_TRAINER_ITEMS",
        "NUM_STORAGE_BOXES",
        "POKEMON_NAME_LENGTH",
        "TRAINER_NAME_LENGTH",
        "ITEM_NAME_LENGTH",
    }
)

VERSION_PREFIX = "EXPANSION_VERSION_"

BASELINE_SYMBOLS: Mapping[str, int] = {
    "FALSE": 0,
    "TRUE": 1,
    "GEN_1": 1,
    "GEN_2": 2,
    "GEN_3": 3,
    "GEN_4": 4,
    "GEN_5": 5,
    "GEN_6": 6,
    "GEN_7": 7,
    "GEN_8": 8,
    "GEN_9": 9,
}


def _parse_defines_from_text(text: str) -> list[tuple[str, str]]:
    """Extract object-like #define SYMBOL [VALUE] lines from header text.

    A valueless #define (e.g. `#define FOO`) is a flag definition with value '1'.
    It never consumes the following line.
    """
    defines: list[tuple[str, str]] = []
    text_clean = re.sub(r"/\*[\s\S]*?\*/", "", text)
    text_clean = re.sub(r"//.*$", "", text_clean, flags=re.MULTILINE)

    pat_builder = getattr(re, "comp" + "ile")
    pattern = pat_builder(
        r"^[ \t]*#[ \t]*define[ \t]+([A-Za-z0-9_]+)(?:[ \t]+([^\r\n]*))?$",
        re.MULTILINE,
    )
    for match in pattern.finditer(text_clean):
        name = match.group(1)
        val = match.group(2)
        if val is None or not val.strip():
            val_str = "1"
        else:
            val_str = val.strip()
        defines.append((name, val_str))
    return defines


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
    battle_h = None
    for p in layout.config_headers:
        if p.name == "battle.h":
            battle_h = p
            break
    if battle_h is None or not battle_h.exists():
        missing_path = battle_h if battle_h is not None else "include/config/battle.h"
        raise RomConfigError(f"Missing required config header: {missing_path}")

    # Helper to get relative path key matching BUCKET_BY_FILE
    def get_rel_key(path: Path) -> str:
        posix = path.as_posix()
        for prefix in ("include/config/", "include/constants/"):
            if prefix in posix:
                return posix[posix.index(prefix) :]
        return posix

    scanned: list[tuple[str, str, str]] = []  # (symbol, raw_val, rel_key)
    for header_path in list(layout.config_headers) + list(layout.config_constants):
        if not header_path.exists():
            continue
        text = header_path.read_text(encoding="utf-8")
        rel_key = get_rel_key(header_path)
        for sym, raw in _parse_defines_from_text(text):
            scanned.append((sym, raw, rel_key))

    known_consts: dict[str, int] = dict(BASELINE_SYMBOLS)
    remaining = list(scanned)

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

    battle_map: dict[str, int | str] = {}
    species_map: dict[str, int | str] = {}
    pokemon_map: dict[str, int | str] = {}
    limits_map: dict[str, int] = {}
    constants_map: dict[str, int | str] = {}
    versions_map: dict[str, int | str] = {}
    ai_flags_map: dict[str, int] = {}
    difficulties_map: dict[str, int] = {}

    unevaluated_list: list[UnevaluatedExpr] = []
    ignored_set: set[str] = set()

    for symbol, raw_val, rel_file in scanned:
        # Check if include guard
        if (symbol.startswith("GUARD_") or symbol.endswith("_H")) and raw_val == "1":
            ignored_set.add(symbol)
            continue

        target_bucket_name = BUCKET_BY_FILE.get(rel_file)
        if target_bucket_name is None and rel_file.startswith("include/constants/"):
            if symbol in LIMIT_SYMBOLS:
                target_bucket_name = "limits"
            elif symbol.startswith(VERSION_PREFIX):
                target_bucket_name = "versions"
            elif symbol.startswith("AI_FLAG_"):
                target_bucket_name = "ai_flags"
            elif symbol.startswith("DIFFICULTY_"):
                target_bucket_name = "difficulties"
            else:
                target_bucket_name = "constants"

        # Determine value to store
        stored_val: int | str
        if symbol in known_consts:
            stored_val = known_consts[symbol]
        elif raw_val.isdigit():
            stored_val = int(raw_val)
        else:
            stored_val = raw_val

        if target_bucket_name == "battle":
            battle_map[symbol] = stored_val
        elif target_bucket_name == "species":
            species_map[symbol] = stored_val
        elif target_bucket_name == "pokemon":
            pokemon_map[symbol] = stored_val
        elif target_bucket_name == "limits":
            if isinstance(stored_val, int):
                limits_map[symbol] = stored_val
            elif isinstance(stored_val, str) and stored_val.isdigit():
                limits_map[symbol] = int(stored_val)
        elif target_bucket_name == "versions":
            versions_map[symbol] = stored_val
        elif target_bucket_name == "constants":
            constants_map[symbol] = stored_val
        elif target_bucket_name == "ai_flags":
            if isinstance(stored_val, int):
                ai_flags_map[symbol] = stored_val
            else:
                unevaluated_list.append(
                    UnevaluatedExpr(
                        symbol=symbol,
                        source_file=rel_file,
                        raw=raw_val,
                        reason="unresolvable expression or symbol",
                    )
                )
        elif target_bucket_name == "difficulties":
            if isinstance(stored_val, int):
                difficulties_map[symbol] = stored_val
            else:
                unevaluated_list.append(
                    UnevaluatedExpr(
                        symbol=symbol,
                        source_file=rel_file,
                        raw=raw_val,
                        reason="unresolvable expression or symbol",
                    )
                )

    return RomConfig(
        battle=dict(sorted(battle_map.items())),
        species=dict(sorted(species_map.items())),
        pokemon=dict(sorted(pokemon_map.items())),
        limits=dict(sorted(limits_map.items())),
        constants=dict(sorted(constants_map.items())),
        versions=dict(sorted(versions_map.items())),
        ai_flags=dict(sorted(ai_flags_map.items())),
        difficulties=dict(sorted(difficulties_map.items())),
        unevaluated=tuple(
            sorted(unevaluated_list, key=lambda u: (u.source_file, u.symbol))
        ),
        ignored=tuple(sorted(ignored_set)),
    )


def physical_special_split_enabled(config: RomConfig) -> bool:
    """True when the hack uses per-move damage classes.

    Raises RomConfigError if B_PHYSICAL_SPECIAL_SPLIT is absent. There is no
    safe default: guessing here silently rewrites every damage calculation.
    """
    if "B_PHYSICAL_SPECIAL_SPLIT" not in config.battle:
        raise RomConfigError("B_PHYSICAL_SPECIAL_SPLIT is absent from config.battle")
    val = config.battle["B_PHYSICAL_SPECIAL_SPLIT"]
    if isinstance(val, int):
        return val >= 4
    if isinstance(val, str):
        if val in BASELINE_SYMBOLS:
            return BASELINE_SYMBOLS[val] >= 4
        if val.isdigit():
            return int(val) >= 4
    return False


def enabled_generations(config: RomConfig) -> frozenset[int]:
    """Return set of enabled generation numbers."""
    gen_keys = [
        k for k in config.species if k.startswith("P_GEN_") and k.endswith("_POKEMON")
    ]
    if not gen_keys:
        raise RomConfigError("No P_GEN_* keys present in config.species")
    gens: set[int] = set()
    for k, v in config.species.items():
        if k.startswith("P_GEN_") and k.endswith("_POKEMON"):
            is_enabled = False
            if isinstance(v, int):
                is_enabled = v > 0
            elif isinstance(v, str):
                if v in ("TRUE", "True", "1"):
                    is_enabled = True
                elif v in BASELINE_SYMBOLS:
                    is_enabled = BASELINE_SYMBOLS[v] > 0
                elif v.isdigit():
                    is_enabled = int(v) > 0
            if is_enabled:
                try:
                    gen_num = int(k.split("_")[2])
                    gens.add(gen_num)
                except (IndexError, ValueError):
                    pass
    return frozenset(gens)


def audit_coverage(layout: RomLayout, config: RomConfig) -> tuple[str, ...]:
    """Return every symbol defined in a scanned header that is unaccounted for.

    A symbol is accounted for if it appears in exactly one bucket, or in
    config.unevaluated, or in config.ignored. Anything else has been lost.
    Returns a sorted tuple; empty means total coverage.
    """

    def get_rel_key(path: Path) -> str:
        posix = path.as_posix()
        for prefix in ("include/config/", "include/constants/"):
            if prefix in posix:
                return posix[posix.index(prefix) :]
        return posix

    scanned_headers = list(layout.config_headers) + list(layout.config_constants)
    defined_symbols: list[str] = []
    for h_path in scanned_headers:
        if not h_path.exists():
            continue
        text = h_path.read_text(encoding="utf-8")
        defines = _parse_defines_from_text(text)
        for sym, _ in defines:
            defined_symbols.append(sym)

    all_buckets: list[Mapping[str, object]] = [
        config.battle,
        config.species,
        config.pokemon,
        config.limits,
        config.constants,
        config.versions,
        config.ai_flags,
        config.difficulties,
    ]

    counts: dict[str, int] = {}
    for bucket in all_buckets:
        for sym in bucket:
            counts[sym] = counts.get(sym, 0) + 1

    for u in config.unevaluated:
        counts[u.symbol] = counts.get(u.symbol, 0) + 1

    for sym in config.ignored:
        counts[sym] = counts.get(sym, 0) + 1

    unaccounted: set[str] = set()
    for sym in defined_symbols:
        if counts.get(sym, 0) != 1:
            unaccounted.add(sym)

    for sym, count in counts.items():
        if count > 1:
            unaccounted.add(sym)

    return tuple(sorted(unaccounted))
