import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def git_fake_rom(tmp_path: Path) -> Path:
    """Fixture that copies fake_rom to a tmp directory and initializes a clean git repo inside it."""
    source_dir = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "fake_rom"
    target_dir = tmp_path / "fake_rom_git"
    shutil.copytree(source_dir, target_dir)

    subprocess.run(["git", "-C", str(target_dir), "init"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(target_dir),
            "config",
            "user.email",
            "test@example.com",
        ],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(target_dir), "config", "user.name", "Test User"],
        check=True,
    )
    subprocess.run(["git", "-C", str(target_dir), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(target_dir), "commit", "-m", "initial commit"],
        check=True,
    )
    return target_dir
