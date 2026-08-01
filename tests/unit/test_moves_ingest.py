from pathlib import Path
from typing import Any

import pytest

from npc_planner.ingest.moves import (
    MoveParseError,
    MoveRecord,
    audit_moves_coverage,
    parse_moves,
    read_moves,
)
from npc_planner.ingest.rom_probe import probe_layout


@pytest.fixture
def fake_rom_layout() -> object:
    root = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "fake_rom"
    return probe_layout(root)


def layout_path(layout: object) -> Path:
    l_any: Any = layout
    return Path(l_any.moves_info)


# ── fake_rom integration tests ──────────────────────────────────────────────


def test_1_moves_read_from_fake_rom(fake_rom_layout: object) -> None:
    records = read_moves(fake_rom_layout)  # type: ignore[arg-type]
    by_id = {r.rom_id: r for r in records}
    assert "MOVE_FLAMETHROWER" in by_id
    assert "MOVE_EARTHQUAKE" in by_id
    assert "MOVE_TOXIC" in by_id
    assert "MOVE_WILL_O_WISP" in by_id


def test_2_flamethrower_fields(fake_rom_layout: object) -> None:
    records = read_moves(fake_rom_layout)  # type: ignore[arg-type]
    by_id = {r.rom_id: r for r in records}
    m = by_id["MOVE_FLAMETHROWER"]
    assert m.move_name == "Flamethrower"
    assert m.type == "TYPE_FIRE"
    # power is a ternary → unevaluated
    assert m.power is None
    assert ("power", "B_UPDATED_MOVE_DATA >= GEN_6 ? 90 : 95") in m.unevaluated_fields
    assert m.accuracy == 100
    assert m.pp == 15
    assert m.target == "TARGET_SELECTED"
    assert m.category == "DAMAGE_CATEGORY_SPECIAL"
    assert m.effect == "EFFECT_HIT"


def test_3_earthquake_fields(fake_rom_layout: object) -> None:
    records = read_moves(fake_rom_layout)  # type: ignore[arg-type]
    by_id = {r.rom_id: r for r in records}
    m = by_id["MOVE_EARTHQUAKE"]
    assert m.move_name == "Earthquake"
    assert m.type == "TYPE_GROUND"
    assert m.power == 100
    assert m.accuracy == 100
    assert m.pp == 10
    assert m.target == "TARGET_FOES_AND_ALLY"
    assert m.category == "DAMAGE_CATEGORY_PHYSICAL"
    assert m.effect == "EFFECT_EARTHQUAKE"
    assert "damagesUnderground" in m.unparsed_fields
    assert "skyBattleBanned" in m.unparsed_fields


def test_3b_toxic_fields(fake_rom_layout: object) -> None:
    records = read_moves(fake_rom_layout)  # type: ignore[arg-type]
    by_id = {r.rom_id: r for r in records}
    m = by_id["MOVE_TOXIC"]
    assert m.move_name == "Toxic"
    assert m.type == "TYPE_POISON"
    assert m.power == 0
    # accuracy is a ternary → unevaluated
    assert m.accuracy is None
    assert (
        "accuracy",
        "B_UPDATED_MOVE_DATA >= GEN_5 ? 90 : 85",
    ) in m.unevaluated_fields
    assert m.category == "DAMAGE_CATEGORY_STATUS"
    assert m.effect == "EFFECT_NON_VOLATILE_STATUS"


def test_3c_will_o_wisp_name_not_derivable(fake_rom_layout: object) -> None:
    """Will-O-Wisp's display name includes hyphens not present in the ROM ID.

    Derivation from MOVE_WILL_O_WISP would yield 'Will O Wisp', so this
    test discriminates: if the COMPOUND_STRING macro is not extracted, it fails.
    """
    records = read_moves(fake_rom_layout)  # type: ignore[arg-type]
    by_id = {r.rom_id: r for r in records}
    m = by_id["MOVE_WILL_O_WISP"]
    assert m.move_name == "Will-O-Wisp"
    assert m.type == "TYPE_FIRE"
    assert m.category == "DAMAGE_CATEGORY_STATUS"


# ── inline / synthetic tests ────────────────────────────────────────────────


SYNTHETIC_MOVE_WITH_SYMBOLS = """
const struct MoveInfo gMovesInfo[] = {
    [MOVE_SOLAR_BEAM] = {
        .name = _("Solar Beam"),
        .type = TYPE_GRASS,
        .power = MOVE_POWER_VARIES,
        .accuracy = 100,
        .pp = 10,
        .effect = EFFECT_SOLARBEAM,
        .target = TARGET_SELECTED,
        .priority = MOVE_PRIORITY_NORMAL,
        .category = DAMAGE_CATEGORY_SPECIAL,
    },
};
"""


def test_4_symbolic_numeric_fields() -> None:
    records = parse_moves(SYNTHETIC_MOVE_WITH_SYMBOLS, "synthetic.h")
    assert len(records) == 1
    m = records[0]
    assert m.power is None
    assert m.symbolic_map["power"] == "MOVE_POWER_VARIES"
    assert m.priority is None
    assert m.symbolic_map["priority"] == "MOVE_PRIORITY_NORMAL"
    assert m.category == "DAMAGE_CATEGORY_SPECIAL"
    assert m.effect == "EFFECT_SOLARBEAM"


SYNTHETIC_MOVE_NO_CATEGORY = """
const struct MoveInfo gMovesInfo[] = {
    [MOVE_POUND] = {
        .name = _("Pound"),
        .type = TYPE_NORMAL,
        .power = 40,
        .accuracy = 100,
        .pp = 35,
    },
};
"""


def test_5_category_absent_when_omitted() -> None:
    records = parse_moves(SYNTHETIC_MOVE_NO_CATEGORY, "synthetic.h")
    assert len(records) == 1
    m = records[0]
    assert m.category is None


def test_6_disjointness_and_sortedness_invariants() -> None:
    # Overlapping key in symbolic + unparsed raises MoveParseError
    with pytest.raises(MoveParseError, match="field in multiple sets"):
        MoveRecord(
            rom_id="MOVE_TEST",
            move_name="Test",
            type="TYPE_NORMAL",
            power=None,
            accuracy=100,
            pp=35,
            effect="EFFECT_HIT",
            target="TARGET_SELECTED",
            priority=0,
            category="DAMAGE_CATEGORY_PHYSICAL",
            source_file="test.h",
            source_record="test",
            unparsed_fields=("power",),
            symbolic_fields=(("power", "MOVE_POWER_VARIES"),),
            unevaluated_fields=(),
        )

    # Unsorted symbolic_fields raises MoveParseError
    with pytest.raises(MoveParseError, match="symbolic_fields must be sorted"):
        MoveRecord(
            rom_id="MOVE_TEST",
            move_name="Test",
            type="TYPE_NORMAL",
            power=None,
            accuracy=100,
            pp=35,
            effect="EFFECT_HIT",
            target="TARGET_SELECTED",
            priority=0,
            category="DAMAGE_CATEGORY_PHYSICAL",
            source_file="test.h",
            source_record="test",
            unparsed_fields=(),
            symbolic_fields=(("priority", "0"), ("accuracy", "100")),
            unevaluated_fields=(),
        )

    # Unsorted unevaluated_fields raises MoveParseError
    with pytest.raises(MoveParseError, match="unevaluated_fields must be sorted"):
        MoveRecord(
            rom_id="MOVE_TEST",
            move_name="Test",
            type="TYPE_NORMAL",
            power=None,
            accuracy=100,
            pp=35,
            effect="EFFECT_HIT",
            target="TARGET_SELECTED",
            priority=0,
            category="DAMAGE_CATEGORY_PHYSICAL",
            source_file="test.h",
            source_record="test",
            unparsed_fields=(),
            symbolic_fields=(),
            unevaluated_fields=(("power", "X"), ("accuracy", "Y")),
        )


def test_7_coverage_audit_fake_rom(fake_rom_layout: object) -> None:
    path = layout_path(fake_rom_layout)
    text = path.read_text(encoding="utf-8")
    records = parse_moves(text, str(path))
    uncovered = audit_moves_coverage(text, records)
    # The regex picks up .moveEffect and .chance from inside ADDITIONAL_EFFECTS({})
    # which are nested macro args, not top-level initializer keys. These are
    # false positives from the flat regex — acceptable for now.
    assert set(uncovered) <= {"chance", "moveEffect"}


def test_8_coverage_audit_detects_uncovered_key() -> None:
    """A key in the source text that no record accounts for is uncovered.

    audit_moves_coverage scans the source text with a flat regex, then
    subtracts MAPPED_FIELDS, IGNORED_FIELDS, unparsed, symbolic, and
    unevaluated keys.  A key that doesn't appear in any of those sets is
    genuinely uncovered.
    """
    # Build a text with an extra key that parse_moves will put in unparsed_fields.
    # Then call audit with an *empty* record list — the key is in the text but
    # no record accounts for it.
    text = """
const struct MoveInfo gMovesInfo[] = {
    [MOVE_POUND] = {
        .name = _("Pound"),
        .type = TYPE_NORMAL,
        .power = 40,
        .accuracy = 100,
        .pp = 35,
        .mysteryField = 42,
    },
};
"""
    # Empty records: no field is accounted for
    uncovered = audit_moves_coverage(text, ())
    assert "mysteryField" in uncovered


SYNTHETIC_NEGATIVE_PRIORITY = """
const struct MoveInfo gMovesInfo[] = {
    [MOVE_COUNTER] = {
        .name = _("Counter"),
        .type = TYPE_FIGHTING,
        .power = 0,
        .accuracy = 100,
        .pp = 20,
        .priority = -6,
        .category = DAMAGE_CATEGORY_PHYSICAL,
    },
};
"""


def test_9_negative_priority() -> None:
    records = parse_moves(SYNTHETIC_NEGATIVE_PRIORITY, "synthetic.h")
    assert len(records) == 1
    m = records[0]
    assert m.priority == -6


SYNTHETIC_COMPOUND_STRING_NAME = """
const struct MoveInfo gMovesInfo[] = {
    [MOVE_THUNDER_WAVE] = {
        .name = COMPOUND_STRING("Thunder Wave"),
        .type = TYPE_ELECTRIC,
        .power = 0,
        .accuracy = 90,
        .pp = 20,
        .category = DAMAGE_CATEGORY_STATUS,
    },
};
"""


def test_10_compound_string_name_extraction() -> None:
    """COMPOUND_STRING macro for .name is extracted, not derived from rom_id."""
    records = parse_moves(SYNTHETIC_COMPOUND_STRING_NAME, "synthetic.h")
    assert len(records) == 1
    m = records[0]
    # Derivation from MOVE_THUNDER_WAVE would give "Thunder Wave" too — but this
    # confirms the macro path works; Will-O-Wisp (test_3c) discriminates.
    assert m.move_name == "Thunder Wave"


SYNTHETIC_COMPOUND_STRING_MULTI_ARG = """
const struct MoveInfo gMovesInfo[] = {
    [MOVE_BAD] = {
        .name = COMPOUND_STRING("foo", "bar"),
        .type = TYPE_NORMAL,
        .power = 0,
        .accuracy = 100,
        .pp = 20,
    },
};
"""


def test_11_compound_string_arity_guard() -> None:
    """COMPOUND_STRING with !=1 arg raises MoveParseError."""
    with pytest.raises(MoveParseError, match="has 2 args, expected 1"):
        parse_moves(SYNTHETIC_COMPOUND_STRING_MULTI_ARG, "synthetic.h")
