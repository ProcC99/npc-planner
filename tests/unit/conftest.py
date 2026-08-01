import shutil
import socket
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access attempted in offline task")

    monkeypatch.setattr(socket.socket, "connect", _boom)
    monkeypatch.setattr(socket, "create_connection", _boom)


@pytest.fixture
def git_fake_rom(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Copy tests/fixtures/fake_rom into tmp_path and git init it.

    Sets local user.name and user.email, disables gpgsign, and isolates GIT_CONFIG_GLOBAL.
    """
    global_gitconfig = tmp_path / "fake_global.gitconfig"
    global_gitconfig.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_gitconfig))

    source_dir = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "fake_rom"
    target_dir = tmp_path / "fake_rom_git"
    shutil.copytree(source_dir, target_dir)

    def run_git(args: list[str]) -> None:
        subprocess.run(
            ["git", "-C", str(target_dir)] + args,
            check=True,
            capture_output=True,
            text=True,
        )

    run_git(["init"])
    run_git(["config", "user.name", "Test User"])
    run_git(["config", "user.email", "test@example.com"])
    run_git(["config", "commit.gpgsign", "false"])
    run_git(["add", "."])
    run_git(["commit", "-m", "initial commit"])

    return target_dir


@pytest.fixture
def git_fake_rom_dirty(git_fake_rom: Path) -> Path:
    """As git_fake_rom, plus one uncommitted modification to a tracked file."""
    tracked_file = git_fake_rom / "src" / "data" / "abilities.h"
    tracked_file.write_text(
        tracked_file.read_text(encoding="utf-8") + "\n// dirty modification\n",
        encoding="utf-8",
    )
    return git_fake_rom
