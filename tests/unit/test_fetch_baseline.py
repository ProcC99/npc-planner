import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*a: object, **k: object) -> None:
        raise AssertionError("network access attempted in offline path")

    monkeypatch.setattr(socket.socket, "connect", _boom)
    monkeypatch.setattr(socket, "create_connection", _boom)


def test_fetch_baseline_local_from_mode(tmp_path: Path, no_network: None) -> None:
    output_dir = tmp_path / "raw"
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "fetch_baseline.py"
    fixture_dir = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "m1_tiny"

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--from",
            str(fixture_dir),
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
