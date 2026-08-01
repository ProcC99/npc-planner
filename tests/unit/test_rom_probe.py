import json
import socket
import subprocess
from pathlib import Path

import pytest

from npc_planner.ingest.rom_probe import (
    RomLayoutUnknownError,
    probe_layout,
    read_pin,
)


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access attempted in offline task")

    monkeypatch.setattr(socket.socket, "connect", _boom)
    monkeypatch.setattr(socket, "create_connection", _boom)


def test_probe_layout_fake_rom(no_network: None) -> None:
    fake_rom_dir = (
        Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "fake_rom"
    )
    layout = probe_layout(fake_rom_dir)
    assert layout.layout_id == "expansion_1_9_plus"
    assert layout.trainers_format == "party"
    assert layout.moves_info.name == "moves_info.h"


def test_probe_layout_missing_path_raises(tmp_path: Path, no_network: None) -> None:
    incomplete = tmp_path / "bad_rom"
    incomplete.mkdir()
    (incomplete / "include" / "config").mkdir(parents=True)

    with pytest.raises(RomLayoutUnknownError) as exc_info:
        probe_layout(incomplete)
    assert "species_info" in str(exc_info.value).lower()


def test_read_pin_fake_rom(tmp_path: Path, no_network: None) -> None:
    fake_rom_dir = (
        Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "fake_rom"
    )
    pin = read_pin(fake_rom_dir)
    assert pin.repo_path == fake_rom_dir
    assert isinstance(pin.hack_dirty, bool)


def test_preprocess_rom_script(tmp_path: Path, no_network: None) -> None:
    fake_rom_dir = (
        Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "fake_rom"
    )
    output_dir = tmp_path / "romdata"
    script = Path(__file__).resolve().parents[2] / "scripts" / "preprocess_rom.py"

    res = subprocess.run(
        [
            "python3",
            str(script),
            "--repo",
            str(fake_rom_dir),
            "--output",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, f"Script failed: {res.stderr}"
    assert (output_dir / "ROM_MANIFEST.json").exists()

    manifest = json.loads(
        (output_dir / "ROM_MANIFEST.json").read_text(encoding="utf-8")
    )
    assert manifest["layout_id"] == "expansion_1_9_plus"

    species_i = (output_dir / "species_info.i").read_text(encoding="utf-8")
    assert "SPECIES_SKARMORY" in species_i
    # Must honour #if P_GEN_9_POKEMON == TRUE (which is FALSE)
    assert "GEN9_GUARD" not in species_i
