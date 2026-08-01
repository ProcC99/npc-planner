import socket
import subprocess
from pathlib import Path

import pytest

from npc_planner.environment import (
    RomRepoNotFoundError,
    check_cpp,
    check_expansion_markers,
    check_upstream_remote,
    resolve_rom_repo,
    run_all,
)


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access attempted in offline task")

    monkeypatch.setattr(socket.socket, "connect", _boom)
    monkeypatch.setattr(socket, "create_connection", _boom)


def test_resolve_rom_repo_explicit(tmp_path: Path, no_network: None) -> None:
    fake_repo = tmp_path / "explicit_repo"
    fake_repo.mkdir()
    res = resolve_rom_repo(explicit=fake_repo)
    assert res == fake_repo.resolve()


def test_resolve_rom_repo_env_precedence(tmp_path: Path, no_network: None) -> None:
    env_repo = tmp_path / "env_repo"
    env_repo.mkdir()
    res = resolve_rom_repo(env={"NPC_PLANNER_ROM_REPO": str(env_repo)})
    assert res == env_repo.resolve()


def test_resolve_rom_repo_not_found(tmp_path: Path, no_network: None) -> None:
    planner_root = tmp_path / "poke"
    planner_root.mkdir()
    with pytest.raises(RomRepoNotFoundError) as exc_info:
        resolve_rom_repo(
            env={},
            config_path=planner_root / "nonexistent.yml",
            planner_root=planner_root,
        )
    msg = str(exc_info.value)
    assert "NPC_PLANNER_ROM_REPO" in msg
    assert "sibling" in msg.lower() or "pokeemerald-expansion" in msg


def test_check_expansion_markers(tmp_path: Path, no_network: None) -> None:
    fake_rom_dir = (
        Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "fake_rom"
    )
    res_fake = check_expansion_markers(fake_rom_dir)
    assert res_fake.ok is True

    vanilla_dir = tmp_path / "vanilla_poke"
    (vanilla_dir / "src" / "data").mkdir(parents=True)
    res_vanilla = check_expansion_markers(vanilla_dir)
    assert res_vanilla.ok is False
    assert res_vanilla.remedy is not None


def test_check_upstream_remote(tmp_path: Path, no_network: None) -> None:
    git_dir = tmp_path / "git_repo"
    git_dir.mkdir()
    subprocess.run(["git", "-C", str(git_dir), "init"], check=True)

    res = check_upstream_remote(git_dir)
    assert res.ok is False
    assert res.severity == "soft"
    assert res.remedy is not None
    assert "git remote add upstream" in res.remedy


def test_check_cpp_nonexistent(no_network: None) -> None:
    res = check_cpp("definitely-not-a-real-binary")
    assert res.ok is False
    assert res.remedy is not None


def test_run_all_empty_directory(tmp_path: Path, no_network: None) -> None:
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    results = run_all(empty_dir, cpp="definitely-not-a-real-binary")
    assert isinstance(results, list)
    hard_failures = [r for r in results if r.severity == "hard" and not r.ok]
    assert len(hard_failures) > 0
    for f in hard_failures:
        assert f.remedy is not None


def test_doctor_script(tmp_path: Path, no_network: None) -> None:
    fake_rom_dir = (
        Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "fake_rom"
    )
    script = Path(__file__).resolve().parents[2] / "scripts" / "doctor.py"

    res_ok = subprocess.run(
        ["python3", str(script), "--repo", str(fake_rom_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_ok.returncode == 0

    empty_dir = tmp_path / "empty_repo"
    empty_dir.mkdir()
    res_fail = subprocess.run(
        ["python3", str(script), "--repo", str(empty_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_fail.returncode == 1
