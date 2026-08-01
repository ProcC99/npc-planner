import json
from pathlib import Path


def test_fake_rom_fixture_structure() -> None:
    test_fake_rom_fixture_declared_paths_exist()
    test_fake_rom_fixture_no_undeclared_files()
    test_fake_rom_fixture_content_checks()


EXPECTED_RELATIVE_PATHS: tuple[str, ...] = (
    "include/constants/expansion.h",
    "include/constants/battle_ai.h",
    "include/constants/difficulty.h",
    "include/constants/global.h",
    "include/constants/battle.h",
    "include/constants/tms_hms.h",
    "include/constants/limits.h",
    "include/config/battle.h",
    "include/config/pokemon.h",
    "include/config/species_enabled.h",
    "src/data/pokemon/species_info.h",
    "src/data/moves_info.h",
    "src/data/abilities.h",
    "src/data/types_info.h",
    "src/data/items.h",
    "src/data/pokemon/level_up_learnsets.h",
    "src/data/pokemon/teachable_learnsets.h",
    "src/data/pokemon/egg_moves.h",
    "src/data/wild_encounters.json",
    "src/data/trainers.party",
)


def fake_rom_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "fake_rom"


def test_fake_rom_fixture_declared_paths_exist() -> None:
    root = fake_rom_dir()
    assert root.exists()

    for rel in EXPECTED_RELATIVE_PATHS:
        file_path = root / rel
        assert file_path.exists(), f"Missing declared fake_rom fixture file: {rel}"


def test_fake_rom_fixture_no_undeclared_files() -> None:
    root = fake_rom_dir()
    found_paths: set[str] = set()

    for path in root.rglob("*"):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            found_paths.add(rel)

    expected_set = set(EXPECTED_RELATIVE_PATHS)
    assert found_paths == expected_set, (
        f"Undeclared or missing files in fake_rom:\n"
        f"  Extra: {found_paths - expected_set}\n"
        f"  Missing: {expected_set - found_paths}"
    )


def test_fake_rom_fixture_content_checks() -> None:
    root = fake_rom_dir()
    species_content = (root / "src" / "data" / "pokemon" / "species_info.h").read_text(
        encoding="utf-8"
    )
    assert "SPECIES_SKARMORY" in species_content
    assert "GEN9_GUARD" in species_content

    wild_json = json.loads(
        (root / "src" / "data" / "wild_encounters.json").read_text(encoding="utf-8")
    )
    assert isinstance(wild_json, dict)

    trainers_party = (root / "src" / "data" / "trainers.party").read_text(
        encoding="utf-8"
    )
    assert "Marlon" in trainers_party
