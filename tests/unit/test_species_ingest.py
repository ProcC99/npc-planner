from pathlib import Path

import pytest

from npc_planner.ingest.rom_probe import probe_layout
from npc_planner.ingest.species import (
    IGNORED_FIELDS,
    MAPPED_FIELDS,
    BaseStats,
    SpeciesParseError,
    audit_species_coverage,
    parse_species,
    read_species,
    read_species_with_source,
)


@pytest.fixture
def fake_rom_layout() -> object:
    root = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "fake_rom"
    return probe_layout(root)


# ------------------- must-pass tests 1-20 for species ingest ------------------


def test_1_skarmory_present(fake_rom_layout: object) -> None:
    records = read_species(fake_rom_layout)  # type: ignore[arg-type]
    by_id = {r.rom_id: r for r in records}
    assert "SPECIES_SKARMORY" in by_id


def test_2_skarmory_base_stats(fake_rom_layout: object) -> None:
    records = read_species(fake_rom_layout)  # type: ignore[arg-type]
    s = next(r for r in records if r.rom_id == "SPECIES_SKARMORY")
    assert s.base_stats == BaseStats(
        hp=65, attack=80, defense=140, sp_attack=40, sp_defense=70, speed=70
    )


def test_3_skarmory_types(fake_rom_layout: object) -> None:
    records = read_species(fake_rom_layout)  # type: ignore[arg-type]
    s = next(r for r in records if r.rom_id == "SPECIES_SKARMORY")
    assert s.types == ("TYPE_STEEL", "TYPE_FLYING")


def test_4_skarmory_hidden_ability(fake_rom_layout: object) -> None:
    records = read_species(fake_rom_layout)  # type: ignore[arg-type]
    s = next(r for r in records if r.rom_id == "SPECIES_SKARMORY")
    assert s.hidden_ability == "ABILITY_WEAK_ARMOR"


def test_5_skarmory_abilities_order(fake_rom_layout: object) -> None:
    records = read_species(fake_rom_layout)  # type: ignore[arg-type]
    s = next(r for r in records if r.rom_id == "SPECIES_SKARMORY")
    assert s.abilities[0] == "ABILITY_KEEN_EYE"
    assert s.abilities[1] == "ABILITY_STURDY"


def test_6_ability_none_survives(fake_rom_layout: object) -> None:
    records = read_species(fake_rom_layout)  # type: ignore[arg-type]
    guard = next((r for r in records if "ABILITY_NONE" in r.abilities), None)
    assert guard is not None
    assert "ABILITY_NONE" in guard.abilities


def test_7_synthetic_monotype_twice() -> None:
    text = """
    const struct SpeciesInfo gSpeciesInfo[] = {
        [SPECIES_TESTMON] = {
            .baseHP = 50, .baseAttack = 50, .baseDefense = 50,
            .baseSpAttack = 50, .baseSpDefense = 50, .baseSpeed = 50,
            .types = {TYPE_ELECTRIC, TYPE_ELECTRIC},
            .abilities = {ABILITY_STATIC},
            .speciesName = _("Testmon"),
        },
    };
    """
    recs = parse_species(text, "synthetic.h")
    assert len(recs) == 1
    assert recs[0].types == ("TYPE_ELECTRIC",)
    assert recs[0].raw_types == ("TYPE_ELECTRIC", "TYPE_ELECTRIC")


def test_8_missing_base_stat_raises() -> None:
    text = """
    const struct SpeciesInfo gSpeciesInfo[] = {
        [SPECIES_TESTMON] = {
            .baseHP = 50, .baseAttack = 50, .baseDefense = 50,
            .baseSpAttack = 50, .baseSpDefense = 50,
            .types = {TYPE_NORMAL},
            .abilities = {ABILITY_RUN_AWAY},
            .speciesName = _("Testmon"),
        },
    };
    """
    with pytest.raises(SpeciesParseError) as exc_info:
        parse_species(text, "synthetic.h")
    assert "baseSpeed" in str(exc_info.value)


def test_9_no_types_raises() -> None:
    text = """
    const struct SpeciesInfo gSpeciesInfo[] = {
        [SPECIES_TESTMON] = {
            .baseHP = 50, .baseAttack = 50, .baseDefense = 50,
            .baseSpAttack = 50, .baseSpDefense = 50, .baseSpeed = 50,
            .abilities = {ABILITY_RUN_AWAY},
            .speciesName = _("Testmon"),
        },
    };
    """
    with pytest.raises(SpeciesParseError) as exc_info:
        parse_species(text, "synthetic.h")
    assert "E_SPECIES_NO_TYPES" in str(exc_info.value)


def test_10_duplicate_species_keys_raises() -> None:
    text = """
    const struct SpeciesInfo gSpeciesInfo[] = {
        [SPECIES_TESTMON] = {
            .baseHP = 50, .baseAttack = 50, .baseDefense = 50,
            .baseSpAttack = 50, .baseSpDefense = 50, .baseSpeed = 50,
            .types = {TYPE_NORMAL},
            .abilities = {ABILITY_RUN_AWAY},
            .speciesName = _("Testmon"),
        },
        [SPECIES_TESTMON] = {
            .baseHP = 60, .baseAttack = 60, .baseDefense = 60,
            .baseSpAttack = 60, .baseSpDefense = 60, .baseSpeed = 60,
            .types = {TYPE_NORMAL},
            .abilities = {ABILITY_RUN_AWAY},
            .speciesName = _("Testmon"),
        },
    };
    """
    with pytest.raises(SpeciesParseError) as exc_info:
        parse_species(text, "synthetic.h")
    assert "Duplicate species key" in str(exc_info.value)


def test_11_all_stats_int_0_255(fake_rom_layout: object) -> None:
    records = read_species(fake_rom_layout)  # type: ignore[arg-type]
    for r in records:
        b = r.base_stats
        for stat_val in (
            b.hp,
            b.attack,
            b.defense,
            b.sp_attack,
            b.sp_defense,
            b.speed,
        ):
            assert isinstance(stat_val, int)
            assert 0 <= stat_val <= 255


def test_12_type_and_ability_prefixes(fake_rom_layout: object) -> None:
    records = read_species(fake_rom_layout)  # type: ignore[arg-type]
    for r in records:
        for t in r.types:
            assert t.startswith("TYPE_")
        for a in r.abilities:
            assert a.startswith("ABILITY_")


def test_13_audit_species_coverage_clean(fake_rom_layout: object) -> None:
    text, records = read_species_with_source(fake_rom_layout)  # type: ignore[arg-type]
    assert audit_species_coverage(text, records) == ()


def test_14_audit_species_coverage_detects_unknown_key(fake_rom_layout: object) -> None:
    text = """
    const struct SpeciesInfo gSpeciesInfo[] = {
        [SPECIES_TESTMON] = {
            .baseHP = 50, .baseAttack = 50, .baseDefense = 50,
            .baseSpAttack = 50, .baseSpDefense = 50, .baseSpeed = 50,
            .types = {TYPE_NORMAL},
            .abilities = {ABILITY_RUN_AWAY},
            .speciesName = _("Testmon"),
            .someUnknownRomField = 123,
        },
    };
    """
    recs = parse_species(text, "synthetic.h")
    assert "someUnknownRomField" in recs[0].unparsed_fields
    found = audit_species_coverage(text, [])
    assert "someUnknownRomField" in found


def test_15_ignored_fields_pinned() -> None:
    assert IGNORED_FIELDS == frozenset()


def test_16_read_species_deterministic(fake_rom_layout: object) -> None:
    r1 = read_species(fake_rom_layout)  # type: ignore[arg-type]
    r2 = read_species(fake_rom_layout)  # type: ignore[arg-type]
    assert r1 == r2


def test_17_records_sorted_by_rom_id(fake_rom_layout: object) -> None:
    records = read_species(fake_rom_layout)  # type: ignore[arg-type]
    ids = [r.rom_id for r in records]
    assert ids == sorted(ids)


def test_18_provenance_attributes(fake_rom_layout: object) -> None:
    records = read_species(fake_rom_layout)  # type: ignore[arg-type]
    for r in records:
        assert r.source_type == "rom_extract"
        assert abs(r.confidence - 0.80) < 1e-9
        assert not r.source_file.startswith("/")
        assert r.source_record.startswith("SPECIES_")


def test_19_parse_species_string_only() -> None:
    text = """
    const struct SpeciesInfo gSpeciesInfo[] = {
        [SPECIES_TESTMON] = {
            .baseHP = 50, .baseAttack = 50, .baseDefense = 50,
            .baseSpAttack = 50, .baseSpDefense = 50, .baseSpeed = 50,
            .types = {TYPE_NORMAL},
            .abilities = {ABILITY_RUN_AWAY},
            .speciesName = _("Testmon"),
        },
    };
    """
    recs = parse_species(text, "synthetic.h")
    assert len(recs) == 1
    assert recs[0].rom_id == "SPECIES_TESTMON"


def test_20_no_forbidden_eval_calls() -> None:
    module_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "npc_planner"
        / "ingest"
        / "species.py"
    )
    text = module_path.read_text(encoding="utf-8")
    for forbidden in ("eval(", "exec(", "literal_eval", "compile("):
        assert forbidden not in text


# ------------------- M1-T11b additional coverage & schema tests ---------------


def test_21_skarmory_species_name(fake_rom_layout: object) -> None:
    records = read_species(fake_rom_layout)  # type: ignore[arg-type]
    s = next(r for r in records if r.rom_id == "SPECIES_SKARMORY")
    assert s.species_name == "Skarmory"


def test_22_missing_or_empty_species_name_raises() -> None:
    no_name_text = """
    const struct SpeciesInfo gSpeciesInfo[] = {
        [SPECIES_TESTMON] = {
            .baseHP = 50, .baseAttack = 50, .baseDefense = 50,
            .baseSpAttack = 50, .baseSpDefense = 50, .baseSpeed = 50,
            .types = {TYPE_NORMAL},
            .abilities = {ABILITY_RUN_AWAY},
        },
    };
    """
    empty_name_text = """
    const struct SpeciesInfo gSpeciesInfo[] = {
        [SPECIES_TESTMON] = {
            .baseHP = 50, .baseAttack = 50, .baseDefense = 50,
            .baseSpAttack = 50, .baseSpDefense = 50, .baseSpeed = 50,
            .types = {TYPE_NORMAL},
            .abilities = {ABILITY_RUN_AWAY},
            .speciesName = _(""),
        },
    };
    """
    with pytest.raises(SpeciesParseError):
        parse_species(no_name_text, "synthetic.h")
    with pytest.raises(SpeciesParseError):
        parse_species(empty_name_text, "synthetic.h")


def test_23_national_dex_resolution(fake_rom_layout: object) -> None:
    records = read_species(fake_rom_layout)  # type: ignore[arg-type]
    by_id = {r.rom_id: r for r in records}
    skarmory = by_id["SPECIES_SKARMORY"]
    gen9 = by_id["SPECIES_GEN9_GUARD"]

    assert skarmory.national_dex is None
    assert skarmory.symbolic_map["natDexNum"] == "NATIONAL_DEX_SKARMORY"
    assert gen9.national_dex == 999


def test_24_no_species_name_equals_id(fake_rom_layout: object) -> None:
    records = read_species(fake_rom_layout)  # type: ignore[arg-type]
    for r in records:
        assert r.species_name != r.rom_id


def test_25_mapped_fields_frozenset() -> None:
    assert isinstance(MAPPED_FIELDS, frozenset)
    assert len(MAPPED_FIELDS) > 0
    assert "speciesName" in MAPPED_FIELDS
    assert "natDexNum" in MAPPED_FIELDS


def test_26_read_species_with_source(fake_rom_layout: object) -> None:
    text, records = read_species_with_source(fake_rom_layout)  # type: ignore[arg-type]
    assert len(text) > 0
    assert len(records) > 0


def test_27_species_disjointness_invariant(fake_rom_layout: object) -> None:
    records = read_species(fake_rom_layout)  # type: ignore[arg-type]
    for r in records:
        assert set(r.unparsed_fields) & set(r.symbolic_map.keys()) == set()
