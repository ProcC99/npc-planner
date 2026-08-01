from pathlib import Path

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


def test_1_moves_read_from_fake_rom(fake_rom_layout: object) -> None:
    records = read_moves(fake_rom_layout)  # type: ignore[arg-type]
    by_id = {r.rom_id: r for r in records}
    assert "MOVE_FLAMETHROWER" in by_id
    assert "MOVE_EARTHQUAKE" in by_id


def test_2_flamethrower_fields(fake_rom_layout: object) -> None:
    records = read_moves(fake_rom_layout)  # type: ignore[arg-type]
    by_id = {r.rom_id: r for r in records}
    m = by_id["MOVE_FLAMETHROWER"]
    assert m.move_name == "Flamethrower"
    assert m.type == "TYPE_FIRE"
    assert m.power == 95
    assert m.accuracy == 100
    assert m.pp == 15
    assert m.target == "MOVE_TARGET_SELECTED"
    assert m.category == "SPLIT_SPECIAL"


def test_3_earthquake_fields(fake_rom_layout: object) -> None:
    records = read_moves(fake_rom_layout)  # type: ignore[arg-type]
    by_id = {r.rom_id: r for r in records}
    m = by_id["MOVE_EARTHQUAKE"]
    assert m.move_name == "Earthquake"
    assert m.type == "TYPE_GROUND"
    assert m.power == 100
    assert m.accuracy == 100
    assert m.pp == 10
    assert m.target == "MOVE_TARGET_FOES_AND_ALLY"
    assert m.category == "SPLIT_PHYSICAL"


SYNTHETIC_MOVE_WITH_SYMBOLS = """
const struct MoveInfo gMovesInfo[] = {
    [MOVE_SOLAR_BEAM] = {
        .name = _("Solar Beam"),
        .type = TYPE_GRASS,
        .power = MOVE_POWER_VARIES,
        .accuracy = 100,
        .pp = 10,
        .effect = EFFECT_SOLARBEAM,
        .target = MOVE_TARGET_SELECTED,
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
    # Overlapping key in both sets raises MoveParseError
    with pytest.raises(MoveParseError, match="field in both sets"):
        MoveRecord(
            rom_id="MOVE_TEST",
            move_name="Test",
            type="TYPE_NORMAL",
            power=None,
            accuracy=100,
            pp=35,
            effect="EFFECT_HIT",
            target="MOVE_TARGET_SELECTED",
            priority=0,
            category="SPLIT_PHYSICAL",
            source_file="test.h",
            source_record="test",
            unparsed_fields=("power",),
            symbolic_fields=(("power", "MOVE_POWER_VARIES"),),
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
            target="MOVE_TARGET_SELECTED",
            priority=0,
            category="SPLIT_PHYSICAL",
            source_file="test.h",
            source_record="test",
            unparsed_fields=(),
            symbolic_fields=(("priority", "0"), ("accuracy", "100")),
        )


def test_7_coverage_audit_fake_rom(fake_rom_layout: object) -> None:
    path = layout_path(fake_rom_layout)
    text = path.read_text()
    records = parse_moves(text, str(path))
    uncovered = audit_moves_coverage(text, records)
    assert uncovered == ()


from typing import Any


def layout_path(layout: object) -> Path:
    l_any: Any = layout
    return Path(l_any.moves_info)
