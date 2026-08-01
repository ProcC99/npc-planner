from __future__ import annotations

import re
from typing import Union

CValue = Union[int, str, list["CValue"], dict[str, "CValue"], "CMacroCall"]


class CParseError(ValueError):
    """Raised on unbalanced braces or malformed initialisers. Carries line and column."""


class CMacroCall:
    """An unexpanded function-like macro, e.g. LEVEL_UP_MOVE(7, MOVE_PECK)."""

    def __init__(self, name: str, args: list[CValue]) -> None:
        self.name = name
        self.args = args

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CMacroCall):
            return False
        return self.name == other.name and self.args == other.args

    def __repr__(self) -> str:
        return f"CMacroCall({self.name!r}, {self.args!r})"


def _strip_comments_and_line_directives(text: str) -> str:
    """Strip C comments (/* ... */, // ...) and #line directives."""
    text = re.sub(r"^\s*#line.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"/\*[\s\S]*?\*/", "", text)
    text = re.sub(r"//.*$", "", text, flags=re.MULTILINE)
    return text


def _clean_string_literal(val: str) -> str:
    """Unwrap C string literals like _("Sturdy") " Protects" -> "Sturdy Protects"."""
    val = re.sub(r"_\(\s*\"([^\"]*)\"\s*\)", r'"\1"', val)
    matches = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', val)
    if matches:
        return "".join(matches)
    return val.strip()


def parse_array_initializer(text: str, symbol: str) -> dict[str, dict[str, CValue]]:
    """Extract `TYPE symbol[] = { [KEY] = { .field = value, ... }, ... };` from text.

    Returns a mapping of KEY (as written, e.g. "SPECIES_SKARMORY") to a field dict.
    Raises CParseError if `symbol` is absent or braces are unbalanced.
    """
    clean_text = _strip_comments_and_line_directives(text)

    pattern = re.compile(
        rf"\b{re.escape(symbol)}\s*(?:\[[^\]]*\])*\s*=\s*\{{", re.MULTILINE
    )
    match = pattern.search(clean_text)
    if not match:
        raise CParseError(f"Symbol '{symbol}' not found in C source text.")

    start_pos = match.end() - 1
    brace_count = 0
    end_pos = -1

    for i in range(start_pos, len(clean_text)):
        char = clean_text[i]
        if char == "{":
            brace_count += 1
        elif char == "}":
            brace_count -= 1
            if brace_count == 0:
                end_pos = i + 1
                break

    if brace_count != 0 or end_pos == -1:
        line_no = clean_text[:start_pos].count("\n") + 1
        raise CParseError(
            f"Unbalanced braces in array initializer for '{symbol}' at line {line_no}."
        )

    body = clean_text[start_pos + 1 : end_pos - 1].strip()

    items: dict[str, dict[str, CValue]] = {}
    default_counter = 0

    i = 0
    n = len(body)

    while i < n:
        while i < n and body[i] in " \t\r\n,":
            i += 1
        if i >= n:
            break

        key_match = re.match(r"\[\s*([A-Za-z0-9_]+)\s*\]\s*=\s*", body[i:])
        if key_match:
            key = key_match.group(1)
            i += key_match.end()
        else:
            key = str(default_counter)
            default_counter += 1

        val, next_i = _parse_c_value(body, i)
        i = next_i

        if isinstance(val, dict):
            items[key] = val
        elif isinstance(val, list):
            items[key] = {"values": val}
        else:
            items[key] = {"value": val}

    return items


def _parse_c_value(text: str, start: int) -> tuple[CValue, int]:
    """Parse a single C value starting at index start."""
    n = len(text)
    while start < n and text[start] in " \t\r\n":
        start += 1

    if start >= n:
        return "", start

    if text[start] == "{":
        brace_count = 1
        i = start + 1
        inner_start = i
        while i < n and brace_count > 0:
            if text[i] == "{":
                brace_count += 1
            elif text[i] == "}":
                brace_count -= 1
            i += 1

        if brace_count != 0:
            line_no = text[:start].count("\n") + 1
            raise CParseError(f"Unbalanced braces in nested value at line {line_no}.")

        inner = text[inner_start : i - 1].strip()
        parsed_inner = _parse_inner_braces(inner)
        return parsed_inner, i

    if text[start] == '"' or text[start:].startswith('_("'):
        i = start
        while i < n and text[i] not in ",}\n;":
            i += 1
        chunk = text[start:i].strip()
        return _clean_string_literal(chunk), i

    i = start
    while i < n and text[i] not in ",}\n;":
        if text[i] == "(":
            paren_count = 1
            i += 1
            while i < n and paren_count > 0:
                if text[i] == "(":
                    paren_count += 1
                elif text[i] == ")":
                    paren_count -= 1
                i += 1
            continue
        i += 1

    token = text[start:i].strip()

    macro_match = re.match(r"^([A-Za-z0-9_]+)\s*\((.*)\)$", token, re.DOTALL)
    if macro_match:
        mname = macro_match.group(1)
        margs_raw = macro_match.group(2).strip()
        args: list[CValue] = []
        if margs_raw:
            for sub in margs_raw.split(","):
                sub_str = sub.strip()
                if sub_str.isdigit() or (
                    sub_str.startswith("-") and sub_str[1:].isdigit()
                ):
                    args.append(int(sub_str))
                else:
                    args.append(sub_str)
        return CMacroCall(mname, args), i

    if token.isdigit():
        return int(token), i
    if token.startswith("-") and token[1:].isdigit():
        return int(token), i

    return token, i


def _parse_inner_braces(inner: str) -> dict[str, CValue] | list[CValue]:
    """Parse inner content of braces into dict (keyed) or list (positional)."""
    if not inner:
        return {}

    # Find top-level field assignments: .field = ...
    # We must respect brace depth so nested .field = inside sub-objects are not matched at top level
    field_matches: list[tuple[str, int, int]] = []
    i = 0
    n = len(inner)
    brace_depth = 0

    while i < n:
        if inner[i] == "{":
            brace_depth += 1
            i += 1
        elif inner[i] == "}":
            brace_depth -= 1
            i += 1
        elif (
            brace_depth == 0
            and inner[i] == "."
            and (i == 0 or inner[i - 1] in " \t\r\n,;")
        ):
            m = re.match(r"\.([A-Za-z0-9_]+)\s*=\s*", inner[i:])
            if m:
                fname = m.group(1)
                val_start = i + m.end()
                field_matches.append((fname, i, val_start))
                i += m.end()
            else:
                i += 1
        else:
            i += 1

    if field_matches:
        result_dict: dict[str, CValue] = {}
        for idx, (fname, _start_pos, val_start) in enumerate(field_matches):
            if idx + 1 < len(field_matches):
                val_end = field_matches[idx + 1][1]
            else:
                val_end = len(inner)

            raw_chunk = inner[val_start:val_end].strip().rstrip(", \t\r\n")
            res_val, _ = _parse_c_value(raw_chunk, 0)
            result_dict[fname] = res_val

        return result_dict

    # Positional list: {a, b, c}
    items: list[CValue] = []
    parts = inner.split(",")
    for p in parts:
        p_str = p.strip()
        if not p_str:
            continue
        if p_str.isdigit() or p_str.startswith("-") and p_str[1:].isdigit():
            items.append(int(p_str))
        else:
            items.append(p_str)
    return items


def parse_enum(text: str, enum_name: str | None = None) -> dict[str, int]:
    """Extract enum members and their resolved integer values, honouring implicit
    increment and explicit `= N` assignments."""
    clean = _strip_comments_and_line_directives(text)
    pattern = re.compile(r"enum\s*(?:[A-Za-z0-9_]+)?\s*\{([^\}]*)\}", re.DOTALL)

    result: dict[str, int] = {}
    for match in pattern.finditer(clean):
        body = match.group(1)
        current_val = 0
        for entry in body.split(","):
            entry = entry.strip()
            if not entry:
                continue
            if "=" in entry:
                k, v = entry.split("=", 1)
                k_str = k.strip()
                v_str = v.strip()
                if v_str.isdigit():
                    current_val = int(v_str)
                elif v_str.startswith(("0x", "0X")):
                    current_val = int(v_str, 16)
                result[k_str] = current_val
                current_val += 1
            else:
                k_str = entry.strip()
                if k_str:
                    result[k_str] = current_val
                    current_val += 1
    return result


def parse_defines(text: str) -> dict[str, str]:
    """Extract object-like `#define NAME value` pairs from an unpreprocessed header."""
    result: dict[str, str] = {}
    pattern = re.compile(r"^\s*#\s*define\s+([A-Za-z0-9_]+)\s+(.+?)$", re.MULTILINE)
    for match in pattern.finditer(text):
        name = match.group(1)
        val = match.group(2).strip()
        if "(" not in name:
            result[name] = val
    return result
