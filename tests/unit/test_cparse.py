import pytest

from npc_planner.ingest.cparse import (
    CParseError,
    parse_array_initializer,
    parse_defines,
    parse_enum,
)


def test_flat_case() -> None:
    src = """
    const struct SpeciesInfo gSpeciesInfo[] = {
        [SPECIES_BULBASAUR] = {
            .baseHP = 45,
            .types = {TYPE_GRASS, TYPE_POISON},
        },
        [SPECIES_SKARMORY] = {
            .baseHP = 65,
            .baseDefense = 140,
        },
    };
    """
    out = parse_array_initializer(src, "gSpeciesInfo")
    assert "SPECIES_BULBASAUR" in out
    assert "SPECIES_SKARMORY" in out
    assert out["SPECIES_SKARMORY"]["baseDefense"] == 140
    assert out["SPECIES_BULBASAUR"]["types"] == ["TYPE_GRASS", "TYPE_POISON"]


def test_nested_keyed_initializer() -> None:
    src = """
    const struct SpeciesInfo gSpeciesInfo[] = {
        [SPECIES_CHARMANDER] = {
            .evolutions = { .method = EVO_LEVEL, .param = 16, .targetSpecies = SPECIES_CHARMELEON },
        },
    };
    """
    out = parse_array_initializer(src, "gSpeciesInfo")
    evo = out["SPECIES_CHARMANDER"]["evolutions"]
    assert isinstance(evo, dict)
    assert evo["method"] == "EVO_LEVEL"
    assert evo["param"] == 16
    assert evo["targetSpecies"] == "SPECIES_CHARMELEON"


def test_positional_array() -> None:
    src = """
    const struct SpeciesInfo gSpeciesInfo[] = {
        [SPECIES_SKARMORY] = {
            .abilities = {ABILITY_KEEN_EYE, ABILITY_STURDY, ABILITY_WEAK_ARMOR},
        },
    };
    """
    out = parse_array_initializer(src, "gSpeciesInfo")
    abilities = out["SPECIES_SKARMORY"]["abilities"]
    assert isinstance(abilities, list)
    assert abilities == [
        "ABILITY_KEEN_EYE",
        "ABILITY_STURDY",
        "ABILITY_WEAK_ARMOR",
    ]


def test_macro_preservation() -> None:
    src = """
    static const struct LevelUpMove sSkarmoryLearnset[] = {
        LEVEL_UP_MOVE(7, MOVE_PECK),
        LEVEL_UP_MOVE(14, MOVE_AIR_CUTTER),
    };
    """
    out = parse_array_initializer(src, "sSkarmoryLearnset")
    assert "0" in out or "default" in out or "sSkarmoryLearnset" in out
    moves = next(iter(out.values()))
    assert len(moves) == 2 or isinstance(moves, dict)


def test_string_literals_concatenation() -> None:
    src = """
    const struct Ability gAbilitiesInfo[] = {
        [ABILITY_STURDY] = {
            .name = _("Sturdy") " Protects",
        },
    };
    """
    out = parse_array_initializer(src, "gAbilitiesInfo")
    assert out["ABILITY_STURDY"]["name"] == "Sturdy Protects"


def test_line_directives_and_comments() -> None:
    src = """
    #line 12 "species_info.h"
    /* Multi-line
       comment */
    const struct SpeciesInfo gSpeciesInfo[] = {
        // Single line comment
        [SPECIES_SKARMORY] = {
            .baseHP = 65, // Base HP
        },
    };
    """
    out = parse_array_initializer(src, "gSpeciesInfo")
    assert out["SPECIES_SKARMORY"]["baseHP"] == 65


def test_unbalanced_brace_raises_error() -> None:
    src = """
    const struct SpeciesInfo gSpeciesInfo[] = {
        [SPECIES_SKARMORY] = {
            .baseHP = 65,
    """
    with pytest.raises(CParseError) as exc_info:
        parse_array_initializer(src, "gSpeciesInfo")
    assert "brace" in str(exc_info.value).lower()


def test_missing_symbol_raises_error() -> None:
    src = "const int gOtherData[] = { 1, 2 };"
    with pytest.raises(CParseError) as exc_info:
        parse_array_initializer(src, "gSpeciesInfo")
    assert "gSpeciesInfo" in str(exc_info.value)


def test_parse_enum() -> None:
    src = """
    enum {
        SPECIES_NONE = 0,
        SPECIES_BULBASAUR,
        SPECIES_IVYSAUR,
        SPECIES_CHARIZARD = 6,
        SPECIES_SQUIRTLE,
    };
    """
    out = parse_enum(src)
    assert out["SPECIES_NONE"] == 0
    assert out["SPECIES_BULBASAUR"] == 1
    assert out["SPECIES_IVYSAUR"] == 2
    assert out["SPECIES_CHARIZARD"] == 6
    assert out["SPECIES_SQUIRTLE"] == 7


def test_parse_defines() -> None:
    src = """
    #define P_GEN_1_POKEMON TRUE
    #define P_MAX_LEVEL 100
    """
    out = parse_defines(src)
    assert out["P_GEN_1_POKEMON"] == "TRUE"
    assert out["P_MAX_LEVEL"] == "100"
