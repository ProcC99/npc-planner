import json
import subprocess
from pathlib import Path

import pytest

import npc_planner.config as config_mod
from npc_planner.ingest.rom_probe import (
    RomLayoutUnknownError,
    probe_layout,
    read_pin,
)

FORBIDDEN_IN_CONFIG = (
    "NPC_PLANNER_ROM_REPO",
    "pokeemerald-expansion",
    "get_rom_repo_path",
    "resolve_rom_repo",
)


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


def test_7_read_pin_non_git(tmp_path: Path, no_network: None) -> None:
    plain_dir = tmp_path / "plain_dir"
    plain_dir.mkdir()
    pin = read_pin(plain_dir)
    assert pin.pinned is False
    assert pin.hack_sha is None
    assert pin.hack_dirty is False
    assert pin.expansion_version == "unpinned"


def test_8_read_pin_git_fake_rom(git_fake_rom: Path, no_network: None) -> None:
    pin = read_pin(git_fake_rom)
    assert pin.pinned is True
    assert pin.hack_sha is not None
    assert len(pin.hack_sha) == 40


def test_9_read_pin_git_fake_rom_dirty(
    git_fake_rom_dirty: Path, no_network: None
) -> None:
    pin = read_pin(git_fake_rom_dirty)
    assert pin.pinned is True
    assert pin.hack_dirty is True


def test_10_and_11_preprocess_rom_fake_rom(tmp_path: Path, no_network: None) -> None:
    fake_rom_dir = (
        Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "fake_rom"
    )
    output_dir = tmp_path / "fake_rom_out"
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
    assert res.returncode == 0
    assert "unpinned" in res.stderr
    assert (output_dir / "ROM_MANIFEST.json").exists()

    manifest = json.loads(
        (output_dir / "ROM_MANIFEST.json").read_text(encoding="utf-8")
    )
    assert manifest["pinned"] is False


def test_12_preprocess_rom_nonexpansion_exit_3(
    tmp_path: Path, no_network: None
) -> None:
    non_expansion = tmp_path / "vanilla_repo"
    non_expansion.mkdir()
    subprocess.run(["git", "-C", str(non_expansion), "init"], check=True)
    (non_expansion / "src" / "data").mkdir(parents=True)

    output_dir = tmp_path / "out_never_created" / "sub"
    script = Path(__file__).resolve().parents[2] / "scripts" / "preprocess_rom.py"

    res = subprocess.run(
        [
            "python3",
            str(script),
            "--repo",
            str(non_expansion),
            "--output",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 3
    assert not output_dir.exists()


def test_13_preprocess_rom_bad_cpp_exit_3(
    git_fake_rom: Path, tmp_path: Path, no_network: None
) -> None:
    output_dir = tmp_path / "out_bad_cpp"
    script = Path(__file__).resolve().parents[2] / "scripts" / "preprocess_rom.py"

    res = subprocess.run(
        [
            "python3",
            str(script),
            "--repo",
            str(git_fake_rom),
            "--output",
            str(output_dir),
            "--cpp",
            "definitely-not-a-real-binary",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 3


def test_14_config_clean_source_text() -> None:
    config_file = (
        Path(__file__).resolve().parents[2] / "src" / "npc_planner" / "config.py"
    )
    src = config_file.read_text(encoding="utf-8")
    for bad in FORBIDDEN_IN_CONFIG:
        assert bad not in src, f"Forbidden string '{bad}' found in config.py"
    assert not hasattr(config_mod, "resolve_rom_repo")


def test_15_probe_does_not_import_environment() -> None:
    probe_file = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "npc_planner"
        / "ingest"
        / "rom_probe.py"
    )
    src = probe_file.read_text(encoding="utf-8")
    assert "npc_planner.environment" not in src
    assert "from ..environment" not in src


def test_16_acceptance_scripts_syntax() -> None:
    root = Path(__file__).resolve().parents[2]
    lib_sh = root / "scripts" / "accept" / "_lib.sh"
    t08c_sh = root / "scripts" / "accept" / "M1-T08c.sh"

    res_lib = subprocess.run(
        ["bash", "-n", str(lib_sh)], capture_output=True, check=False
    )
    assert res_lib.returncode == 0, f"Syntax error in _lib.sh: {res_lib.stderr}"

    res_t08c = subprocess.run(
        ["bash", "-n", str(t08c_sh)], capture_output=True, check=False
    )
    assert res_t08c.returncode == 0, f"Syntax error in M1-T08c.sh: {res_t08c.stderr}"
