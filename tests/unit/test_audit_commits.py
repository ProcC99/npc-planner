import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from scripts.audit_commits import audit_commit
from scripts.audit_commits import main as audit_main


@pytest.fixture
def audit_git_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a temporary git repository for testing audit_commits."""
    global_gitconfig = tmp_path / "fake_global.gitconfig"
    global_gitconfig.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_gitconfig))

    repo = tmp_path / "audit_repo"
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

    # Initial setup
    (repo / "docs" / "tasks").mkdir(parents=True)
    (repo / "docs" / "tasks" / "M1-T01.md").write_text(
        "# M1-T01\n\n## Files you may create or modify\n\n- `src/a.py`\n",
        encoding="utf-8",
    )
    run_git("add", ".")
    run_git("commit", "-m", "init [protocol]")

    return repo


def test_14_audit_commits_reports_untagged_and_off_allowlist(
    audit_git_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def run_git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(audit_git_repo)] + list(args),
            capture_output=True,
            text=True,
            check=True,
        )

    # Commit 1: clean task commit
    (audit_git_repo / "src").mkdir(parents=True, exist_ok=True)
    (audit_git_repo / "src" / "a.py").write_text("a = 1\n", encoding="utf-8")
    run_git("add", ".")
    run_git("commit", "-m", "feat(db): clean commit   [M1-T01]")

    # Commit 2: untagged commit
    (audit_git_repo / "src" / "b.py").write_text("b = 2\n", encoding="utf-8")
    run_git("add", ".")
    run_git("commit", "-m", "chore: untagged commit")

    # Commit 3: task commit touching off-allowlist file
    (audit_git_repo / "src" / "off.py").write_text("off = 3\n", encoding="utf-8")
    run_git("add", ".")
    run_git("commit", "-m", "feat(db): off allowlist   [M1-T01]")

    monkeypatch.chdir(audit_git_repo)
    # Run audit on range HEAD~3..HEAD
    res_code = audit_main(["--range", "HEAD~3..HEAD"])
    assert res_code == 1


def test_15_audit_reads_card_from_commit_tree_not_tip(
    audit_git_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def run_git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(audit_git_repo)] + list(args),
            capture_output=True,
            text=True,
            check=True,
        )

    # Commit 1: task commit touching b.py (not in allowlist yet)
    (audit_git_repo / "src").mkdir(parents=True, exist_ok=True)
    (audit_git_repo / "src" / "b.py").write_text("b = 1\n", encoding="utf-8")
    run_git("add", ".")
    run_git("commit", "-m", "feat(db): add b   [M1-T01]")

    commit1_sha = run_git("rev-parse", "HEAD").stdout.strip()

    # Commit 2: widen card on tip
    (audit_git_repo / "docs" / "tasks" / "M1-T01.md").write_text(
        "# M1-T01\n\n## Files you may create or modify\n\n- `src/a.py`\n- `src/b.py`\n",
        encoding="utf-8",
    )
    run_git("add", ".")
    run_git("commit", "-m", "docs(tasks): widen M1-T01 card   [protocol]")

    # Auditing commit1_sha directly must report b.py as outside allowlist because in commit1 tree, b.py was not allowed!
    monkeypatch.chdir(audit_git_repo)
    problems = audit_commit(commit1_sha)
    assert any("outside the M1-T01 allowlist: src/b.py" in p for p in problems)
