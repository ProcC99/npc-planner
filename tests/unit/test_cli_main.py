from pathlib import Path

from typer.testing import CliRunner

from npc_planner.cli.main import app

runner = CliRunner()


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "NPC Team Planner" in result.stdout


def test_cli_data_build(tmp_path: Path) -> None:
    fixture_dir = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "m1_tiny"
    db_out = tmp_path / "planner.db"

    result = runner.invoke(
        app,
        [
            "data",
            "build",
            "--raw-dir",
            str(fixture_dir),
            "--db-out",
            str(db_out),
        ],
    )
    assert result.exit_code == 0
    assert db_out.exists()


def test_cli_pokemon_show(tmp_path: Path) -> None:
    fixture_dir = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "m1_tiny"
    db_out = tmp_path / "planner.db"

    # Build DB first
    runner.invoke(
        app,
        [
            "data",
            "build",
            "--raw-dir",
            str(fixture_dir),
            "--db-out",
            str(db_out),
        ],
    )

    result = runner.invoke(
        app,
        [
            "pokemon",
            "show",
            "skarmory",
            "--db",
            str(db_out),
        ],
    )
    assert result.exit_code == 0
    assert "skarmory" in result.stdout.lower()
    assert "steel" in result.stdout.lower()
