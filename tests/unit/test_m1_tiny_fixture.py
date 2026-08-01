import json
from pathlib import Path


def test_m1_tiny_files_exist_and_valid_json() -> None:
    fixture_dir = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "m1_tiny"
    expected_files = [
        "meta.json",
        "species.json",
        "forms.json",
        "moves.json",
        "abilities.json",
        "type_matchups.json",
    ]
    for filename in expected_files:
        file_path = fixture_dir / filename
        assert file_path.exists(), f"Missing fixture file {filename}"
        data = json.loads(file_path.read_text(encoding="utf-8"))
        assert isinstance(data, (dict, list))


def test_m1_tiny_species_and_forms_count() -> None:
    fixture_dir = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "m1_tiny"
    species = json.loads((fixture_dir / "species.json").read_text(encoding="utf-8"))
    forms = json.loads((fixture_dir / "forms.json").read_text(encoding="utf-8"))
    assert len(species) == 10
    assert len(forms) >= 10
    form_ids = [f["form_id"] for f in forms]
    assert "skarmory" in form_ids


def test_m1_tiny_moves_and_abilities() -> None:
    fixture_dir = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "m1_tiny"
    moves = json.loads((fixture_dir / "moves.json").read_text(encoding="utf-8"))
    abilities = json.loads((fixture_dir / "abilities.json").read_text(encoding="utf-8"))
    matchups = json.loads(
        (fixture_dir / "type_matchups.json").read_text(encoding="utf-8")
    )
    assert len(moves) > 0
    assert len(abilities) > 0
    assert len(matchups) > 0
