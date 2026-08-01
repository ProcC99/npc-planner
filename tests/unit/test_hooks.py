import json
import subprocess
import sys
from dataclasses import fields
from pathlib import Path

import pytest

from npc_planner.ingest.rom_probe import PREPROCESSABLE_FIELDS, RomLayout, probe_layout


@pytest.fixture
def test_git_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a temporary git repository for testing hooks hermetically."""
    global_gitconfig = tmp_path / "fake_global.gitconfig"
    global_gitconfig.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_gitconfig))

    repo = tmp_path / "test_repo"
    repo.mkdir()

    def run_git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(repo)] + list(args),
            capture_output=True,
            text=True,
            check=True,
        )

    run_git("init")
    run_git("config", "user.name", "Test User")
    run_git("config", "user.email", "test@example.com")
    run_git("config", "commit.gpgsign", "false")

    (repo / "docs" / "tasks").mkdir(parents=True)
    card = repo / "docs" / "tasks" / "M1-T99.md"
    card.write_text(
        "# M1-T99 - Test Task\n\n"
        "## Files you may create or modify\n\n"
        "- `src/npc_planner/foo.py`\n"
        "- `tests/unit/test_*.py`\n"
        "- `data/fixtures/`\n",
        encoding="utf-8",
    )
    run_git("add", ".")
    run_git("commit", "-m", "initial commit with card M1-T99")

    return repo


def _run_hook_in_repo(repo: Path, message: str) -> tuple[int, str]:
    msg_file = repo / ".git" / "COMMIT_EDITMSG"
    msg_file.write_text(message, encoding="utf-8")
    script = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "hooks"
        / "files_within_allowlist.py"
    )
    res = subprocess.run(
        [sys.executable, str(script), str(msg_file)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    return res.returncode, res.stdout + res.stderr


def test_1_untagged_commit_ignored(test_git_repo: Path) -> None:
    (test_git_repo / "random.txt").write_text("random\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(test_git_repo), "add", "."], check=True)
    rc, _ = _run_hook_in_repo(test_git_repo, "chore: random commit")
    assert rc == 0


def test_2_card_absent_from_head_returns_1(test_git_repo: Path) -> None:
    rc, out = _run_hook_in_repo(test_git_repo, "feat: non-existent card [M1-T88]")
    assert rc == 1
    assert "not committed in HEAD" in out


def test_3_allowed_file_accepted(test_git_repo: Path) -> None:
    (test_git_repo / "src" / "npc_planner").mkdir(parents=True)
    (test_git_repo / "src" / "npc_planner" / "foo.py").write_text(
        "x = 1\n", encoding="utf-8"
    )
    subprocess.run(["git", "-C", str(test_git_repo), "add", "."], check=True)
    rc, _ = _run_hook_in_repo(test_git_repo, "feat: implement foo [M1-T99]")
    assert rc == 0


def test_4_disallowed_file_rejected(test_git_repo: Path) -> None:
    (test_git_repo / "src").mkdir(parents=True, exist_ok=True)
    (test_git_repo / "src" / "rogue.py").write_text("y = 2\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(test_git_repo), "add", "."], check=True)
    rc, out = _run_hook_in_repo(test_git_repo, "feat: rogue edit [M1-T99]")
    assert rc == 1
    assert "src/rogue.py" in out


def test_5_ledger_always_allowed(test_git_repo: Path) -> None:
    (test_git_repo / "docs" / "LEDGER.md").write_text("ledger\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(test_git_repo), "add", "."], check=True)
    rc, _ = _run_hook_in_repo(test_git_repo, "feat: ledger edit [M1-T99]")
    assert rc == 0


def test_6_glob_pattern_matches(test_git_repo: Path) -> None:
    (test_git_repo / "tests" / "unit").mkdir(parents=True)
    (test_git_repo / "tests" / "unit" / "test_bar.py").write_text(
        "def test_bar(): pass\n", encoding="utf-8"
    )
    subprocess.run(["git", "-C", str(test_git_repo), "add", "."], check=True)
    rc, _ = _run_hook_in_repo(test_git_repo, "feat: test bar [M1-T99]")
    assert rc == 0


def test_7_directory_pattern_matches(test_git_repo: Path) -> None:
    (test_git_repo / "data" / "fixtures" / "sub").mkdir(parents=True)
    (test_git_repo / "data" / "fixtures" / "sub" / "data.json").write_text(
        "{}\n", encoding="utf-8"
    )
    subprocess.run(["git", "-C", str(test_git_repo), "add", "."], check=True)
    rc, _ = _run_hook_in_repo(test_git_repo, "feat: data json [M1-T99]")
    assert rc == 0


def test_8_empty_allowlist_returns_1(test_git_repo: Path) -> None:
    empty_card = test_git_repo / "docs" / "tasks" / "M1-T77.md"
    empty_card.write_text("# M1-T77 Empty Card\n\nNo sections.\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(test_git_repo), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(test_git_repo), "commit", "-m", "add empty card M1-T77"],
        check=True,
    )
    (test_git_repo / "docs" / "LEDGER.md").write_text("ledger edit\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(test_git_repo), "add", "."], check=True)
    rc, out = _run_hook_in_repo(test_git_repo, "feat: empty card [M1-T77]")
    assert rc == 1
    assert "no parseable" in out


def test_9_allowlist_read_from_head_not_working_tree(
    test_git_repo: Path,
) -> None:
    card = test_git_repo / "docs" / "tasks" / "M1-T99.md"
    card.write_text(
        card.read_text(encoding="utf-8") + "- `src/uncommitted_allowed.py`\n",
        encoding="utf-8",
    )
    (test_git_repo / "src").mkdir(parents=True, exist_ok=True)
    (test_git_repo / "src" / "uncommitted_allowed.py").write_text(
        "a = 1\n", encoding="utf-8"
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(test_git_repo),
            "add",
            "src/uncommitted_allowed.py",
        ],
        check=True,
    )
    rc, out = _run_hook_in_repo(
        test_git_repo, "feat: uncommitted allowlist edit [M1-T99]"
    )
    assert rc == 1
    assert "src/uncommitted_allowed.py" in out


def test_10_preprocessable_fields_subset_of_rom_layout() -> None:
    layout_field_names = {f.name for f in fields(RomLayout)}
    assert set(PREPROCESSABLE_FIELDS) <= layout_field_names
    assert "wild_encounters" not in PREPROCESSABLE_FIELDS
    assert "trainers" not in PREPROCESSABLE_FIELDS


def test_11_manifest_count_equals_preprocessable_paths_count(
    tmp_path: Path, no_network: None
) -> None:
    fake_rom_dir = (
        Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "fake_rom"
    )
    layout = probe_layout(fake_rom_dir)
    expected_count = len(layout.preprocessable_paths())

    output_dir = tmp_path / "out_manifest_test"
    script = Path(__file__).resolve().parents[2] / "scripts" / "preprocess_rom.py"
    subprocess.run(
        [
            sys.executable,
            str(script),
            "--repo",
            str(fake_rom_dir),
            "--output",
            str(output_dir),
        ],
        check=True,
    )

    manifest = json.loads(
        (output_dir / "ROM_MANIFEST.json").read_text(encoding="utf-8")
    )
    assert len(manifest["preprocessed"]) == expected_count


def test_12_all_acceptance_scripts_syntax_check() -> None:
    accept_dir = Path(__file__).resolve().parents[2] / "scripts" / "accept"
    for sh_file in accept_dir.glob("*.sh"):
        res = subprocess.run(
            ["bash", "-n", str(sh_file)], capture_output=True, check=False
        )
        assert (
            res.returncode == 0
        ), f"Syntax error in {sh_file.name}: {res.stderr.decode()}"
