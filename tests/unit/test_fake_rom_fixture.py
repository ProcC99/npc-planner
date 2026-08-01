import json
from pathlib import Path


def test_fake_rom_fixture_structure() -> None:
    fake_rom_dir = (
        Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "fake_rom"
    )
    assert fake_rom_dir.exists()

    expected_files = [
        fake_rom_dir / "include" / "constants" / "expansion.h",
        fake_rom_dir / "include" / "config" / "battle.h",
        fake_rom_dir / "include" / "config" / "pokemon.h",
        fake_rom_dir / "include" / "config" / "species_enabled.h",
        fake_rom_dir / "src" / "data" / "pokemon" / "species_info.h",
        fake_rom_dir / "src" / "data" / "moves_info.h",
        fake_rom_dir / "src" / "data" / "abilities.h",
        fake_rom_dir / "src" / "data" / "types_info.h",
        fake_rom_dir / "src" / "data" / "items.h",
        fake_rom_dir / "src" / "data" / "pokemon" / "level_up_learnsets.h",
        fake_rom_dir / "src" / "data" / "pokemon" / "teachable_learnsets.h",
        fake_rom_dir / "src" / "data" / "pokemon" / "egg_moves.h",
        fake_rom_dir / "src" / "data" / "wild_encounters.json",
        fake_rom_dir / "src" / "data" / "trainers.party",
    ]

    for f in expected_files:
        assert f.exists(), f"Missing fake_rom fixture file: {f}"

    species_content = (
        fake_rom_dir / "src" / "data" / "pokemon" / "species_info.h"
    ).read_text(encoding="utf-8")
    assert "SPECIES_SKARMORY" in species_content
    assert "GEN9_GUARD" in species_content

    wild_json = json.loads(
        (fake_rom_dir / "src" / "data" / "wild_encounters.json").read_text(
            encoding="utf-8"
        )
    )
    assert isinstance(wild_json, dict)

    trainers_party = (fake_rom_dir / "src" / "data" / "trainers.party").read_text(
        encoding="utf-8"
    )
    assert "Marlon" in trainers_party
