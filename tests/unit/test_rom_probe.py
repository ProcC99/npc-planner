import subprocess
from pathlib import Path

import pytest

import npc_planner.config as config_mod
from npc_planner.ingest.rom_probe import (
    RomLayoutUnknownError,
    probe_layout,
    read_pin,
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


def test_read_pin_dirty(git_fake_rom_dirty: Path, no_network: None) -> None:
    pin = read_pin(git_fake_rom_dirty)
    assert pin.repo_path == git_fake_rom_dirty
    assert pin.hack_dirty is True


def test_preprocess_rom_env_var_fallback(
    git_fake_rom: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    no_network: None,
) -> None:
    monkeypatch.setenv("NPC_PLANNER_ROM_REPO", str(git_fake_rom))
    output_dir = tmp_path / "out1"
    script = Path(__file__).resolve().parents[2] / "scripts" / "preprocess_rom.py"

    res = subprocess.run(
        ["python3", str(script), "--output", str(output_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, f"Script failed: {res.stderr}"
    assert (output_dir / "ROM_MANIFEST.json").exists()


def test_preprocess_rom_explicit_overrides_env(
    git_fake_rom: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    no_network: None,
) -> None:
    dummy_env = tmp_path / "dummy_env"
    dummy_env.mkdir()
    monkeypatch.setenv("NPC_PLANNER_ROM_REPO", str(dummy_env))

    output_dir = tmp_path / "out2"
    script = Path(__file__).resolve().parents[2] / "scripts" / "preprocess_rom.py"

    res = subprocess.run(
        [
            "python3",
            str(script),
            "--repo",
            str(git_fake_rom),
            "--output",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0
    assert (output_dir / "ROM_MANIFEST.json").exists()


def test_preprocess_rom_unresolvable_exit_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_network: None
) -> None:
    planner_root = tmp_path / "poke"
    planner_root.mkdir()
    monkeypatch.delenv("NPC_PLANNER_ROM_REPO", raising=False)

    nonexistent_repo = tmp_path / "nonexistent_repo"
    output_dir = tmp_path / "out3"
    script = Path(__file__).resolve().parents[2] / "scripts" / "preprocess_rom.py"

    res = subprocess.run(
        [
            "python3",
            str(script),
            "--repo",
            str(nonexistent_repo),
            "--output",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 2 or res.returncode == 3
    assert (
        "Attempted locations" in res.stderr
        or "Preflight" in res.stderr
        or "Resolution" in res.stderr
    )


def test_preprocess_rom_nonexpansion_exit_3(tmp_path: Path, no_network: None) -> None:
    non_expansion = tmp_path / "vanilla_repo"
    non_expansion.mkdir()
    subprocess.run(["git", "-C", str(non_expansion), "init"], check=True)
    (non_expansion / "src" / "data").mkdir(parents=True)

    output_dir = tmp_path / "out_empty"
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
    assert "expansion_markers" in res.stderr or "Remedy" in res.stderr
    assert not output_dir.exists() or len(list(output_dir.iterdir())) == 0


def test_single_resolver_in_environment_only() -> None:
    assert not hasattr(config_mod, "resolve_rom_repo")
    assert not hasattr(config_mod, "get_rom_repo_path")
