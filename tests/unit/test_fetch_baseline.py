import json
import subprocess
import sys
from pathlib import Path


def test_fetch_baseline_fixture_mode(tmp_path: Path) -> None:
    output_dir = tmp_path / "raw"
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "fetch_baseline.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--fixture",
            "m1_tiny",
            "--output",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert output_dir.exists()

    expected_files = [
        "meta.json",
        "species.json",
        "forms.json",
        "moves.json",
        "abilities.json",
        "type_matchups.json",
    ]
    for name in expected_files:
        file_path = output_dir / name
        assert file_path.exists()
        data = json.loads(file_path.read_text(encoding="utf-8"))
        assert data is not None


def test_fetch_baseline_help() -> None:
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "fetch_baseline.py"
    result = subprocess.run(
        [sys.executable, str(script_path), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "baseline" in result.stdout.lower()
