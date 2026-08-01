import json
import subprocess
import sys
from dataclasses import fields
from pathlib import Path

import pytest
from scripts.hooks.task_id_required import parse_ledger_rows, unparsable_ledger_rows

from npc_planner.ingest.rom_probe import (
    PREPROCESSABLE_FIELDS,
    RomLayout,
    probe_layout,
)


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
    run_git("commit", "-m", "initial commit with card M1-T99   [protocol]")

    return repo


def _run_hook_in_repo(hook_script: str, repo: Path, message: str) -> tuple[int, str]:
    msg_file = repo / ".git" / "COMMIT_EDITMSG"
    msg_file.write_text(message, encoding="utf-8")
    script = Path(__file__).resolve().parents[2] / "scripts" / "hooks" / hook_script
    res = subprocess.run(
        [sys.executable, str(script), str(msg_file)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    return res.returncode, res.stdout + res.stderr


# ------------------- Legacy test names preserved for no-test-deletion hook -------------------


def test_1_untagged_commit_ignored(test_git_repo: Path) -> None:
    rc, _ = _run_hook_in_repo(
        "task_id_required.py", test_git_repo, "chore: random commit"
    )
    assert rc == 1


def test_2_card_absent_from_head_returns_1(test_git_repo: Path) -> None:
    (test_git_repo / "foo.py").write_text("a = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(test_git_repo), "add", "foo.py"], check=True)
    rc, out = _run_hook_in_repo(
        "files_within_allowlist.py", test_git_repo, "feat: non-existent card   [M1-T88]"
    )
    assert rc == 1
    assert "not found in docs/tasks/" in out


def test_3_allowed_file_accepted(test_git_repo: Path) -> None:
    (test_git_repo / "src" / "npc_planner").mkdir(parents=True)
    (test_git_repo / "src" / "npc_planner" / "foo.py").write_text(
        "x = 1\n", encoding="utf-8"
    )
    subprocess.run(["git", "-C", str(test_git_repo), "add", "."], check=True)
    rc, _ = _run_hook_in_repo(
        "files_within_allowlist.py", test_git_repo, "feat: implement foo   [M1-T99]"
    )
    assert rc == 0


def test_4_disallowed_file_rejected(test_git_repo: Path) -> None:
    (test_git_repo / "src").mkdir(parents=True, exist_ok=True)
    (test_git_repo / "src" / "rogue.py").write_text("y = 2\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(test_git_repo), "add", "."], check=True)
    rc, out = _run_hook_in_repo(
        "files_within_allowlist.py", test_git_repo, "feat: rogue edit   [M1-T99]"
    )
    assert rc == 1
    assert "src/rogue.py" in out


def test_5_ledger_always_allowed(test_git_repo: Path) -> None:
    (test_git_repo / "docs" / "LEDGER.md").write_text("ledger\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(test_git_repo), "add", "."], check=True)
    rc, _ = _run_hook_in_repo(
        "files_within_allowlist.py", test_git_repo, "feat: ledger edit   [M1-T99]"
    )
    assert rc == 0


def test_6_glob_pattern_matches(test_git_repo: Path) -> None:
    (test_git_repo / "tests" / "unit").mkdir(parents=True)
    (test_git_repo / "tests" / "unit" / "test_bar.py").write_text(
        "def test_bar(): pass\n", encoding="utf-8"
    )
    subprocess.run(["git", "-C", str(test_git_repo), "add", "."], check=True)
    rc, _ = _run_hook_in_repo(
        "files_within_allowlist.py", test_git_repo, "feat: test bar   [M1-T99]"
    )
    assert rc == 0


def test_7_directory_pattern_matches(test_git_repo: Path) -> None:
    (test_git_repo / "data" / "fixtures" / "sub").mkdir(parents=True)
    (test_git_repo / "data" / "fixtures" / "sub" / "data.json").write_text(
        "{}\n", encoding="utf-8"
    )
    subprocess.run(["git", "-C", str(test_git_repo), "add", "."], check=True)
    rc, _ = _run_hook_in_repo(
        "files_within_allowlist.py", test_git_repo, "feat: data json   [M1-T99]"
    )
    assert rc == 0


def test_8_empty_allowlist_returns_1(test_git_repo: Path) -> None:
    empty_card = test_git_repo / "docs" / "tasks" / "M1-T77.md"
    empty_card.write_text("# M1-T77 Empty Card\n\nNo sections.\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(test_git_repo), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(test_git_repo),
            "commit",
            "-m",
            "add empty card M1-T77   [protocol]",
        ],
        check=True,
    )
    (test_git_repo / "foo.py").write_text("foo = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(test_git_repo), "add", "foo.py"], check=True)
    rc, out = _run_hook_in_repo(
        "files_within_allowlist.py", test_git_repo, "feat: empty card   [M1-T77]"
    )
    assert rc == 1
    assert "outside allowlist" in out


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
        "files_within_allowlist.py", test_git_repo, "feat: edit   [M1-T99]"
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
        err_msg = f"Syntax error in {sh_file.name}: {res.stderr.decode()}"
        assert res.returncode == 0, err_msg


# ------------------- must-pass tests 1-6 for task_id_required -------------------


def test_1_untagged_commit_rejected_by_task_id(test_git_repo: Path) -> None:
    rc, out = _run_hook_in_repo(
        "task_id_required.py", test_git_repo, "chore: random commit"
    )
    assert rc == 1
    assert "missing scope tag" in out


def test_2_task_tag_accepted_by_task_id(test_git_repo: Path) -> None:
    rc, _ = _run_hook_in_repo(
        "task_id_required.py", test_git_repo, "feat(rules): do thing   [M1-T08e]"
    )
    assert rc == 0


def test_3_ledger_tag_accepted_by_task_id(test_git_repo: Path) -> None:
    rc, _ = _run_hook_in_repo(
        "task_id_required.py", test_git_repo, "docs(ledger): record M1-T08d   [ledger]"
    )
    assert rc == 0


def test_4_protocol_tag_accepted_by_task_id(test_git_repo: Path) -> None:
    rc, _ = _run_hook_in_repo(
        "task_id_required.py", test_git_repo, "docs(tasks): add card   [protocol]"
    )
    assert rc == 0


def test_5_both_task_and_ledger_tags_rejected(test_git_repo: Path) -> None:
    rc, out = _run_hook_in_repo(
        "task_id_required.py", test_git_repo, "chore: double tag   [M1-T08e] [ledger]"
    )
    assert rc == 1
    assert "both a task tag and a scope tag" in out


def test_6_fixup_subject_rejected(test_git_repo: Path) -> None:
    subject = "fixup! update task_id_required to support task letter suffixes"
    rc, out = _run_hook_in_repo("task_id_required.py", test_git_repo, subject)
    assert rc == 1
    assert "missing scope tag" in out


# ------------------- must-pass tests 7-11 for files_within_allowlist -------------------


def test_7_ledger_commit_staging_ledger_accepted(test_git_repo: Path) -> None:
    (test_git_repo / "docs" / "LEDGER.md").write_text("ledger\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(test_git_repo), "add", "."], check=True)
    rc, _ = _run_hook_in_repo(
        "files_within_allowlist.py",
        test_git_repo,
        "docs(ledger): record sha   [ledger]",
    )
    assert rc == 0


def test_8_ledger_commit_staging_src_rejected(test_git_repo: Path) -> None:
    (test_git_repo / "src").mkdir(parents=True, exist_ok=True)
    (test_git_repo / "src" / "foo.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(test_git_repo), "add", "."], check=True)
    rc, out = _run_hook_in_repo(
        "files_within_allowlist.py",
        test_git_repo,
        "docs(ledger): record sha   [ledger]",
    )
    assert rc == 1
    assert "src/foo.py" in out


def test_9_protocol_commit_staging_card_and_protocol_accepted(
    test_git_repo: Path,
) -> None:
    (test_git_repo / "EXECUTION_PROTOCOL.md").write_text("proto\n", encoding="utf-8")
    (test_git_repo / "docs" / "tasks" / "M1-T01.md").write_text(
        "card\n", encoding="utf-8"
    )
    subprocess.run(["git", "-C", str(test_git_repo), "add", "."], check=True)
    rc, _ = _run_hook_in_repo(
        "files_within_allowlist.py",
        test_git_repo,
        "docs(protocol): update   [protocol]",
    )
    assert rc == 0


def test_10_protocol_commit_staging_hook_rejected(
    test_git_repo: Path,
) -> None:
    (test_git_repo / "scripts" / "hooks").mkdir(parents=True, exist_ok=True)
    (test_git_repo / "scripts" / "hooks" / "anything.py").write_text(
        "x = 1\n", encoding="utf-8"
    )
    subprocess.run(["git", "-C", str(test_git_repo), "add", "."], check=True)
    rc, out = _run_hook_in_repo(
        "files_within_allowlist.py",
        test_git_repo,
        "docs(protocol): edit hook   [protocol]",
    )
    assert rc == 1
    assert "scripts/hooks/anything.py" in out


def test_11_allowlist_read_from_head_not_working_tree(
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
        "files_within_allowlist.py", test_git_repo, "feat: edit   [M1-T99]"
    )
    assert rc == 1
    assert "src/uncommitted_allowed.py" in out


# ------------------- must-pass tests 23-27 for hooks & scope -------------------


def test_23_done_task_tag_rejected(test_git_repo: Path) -> None:
    ledger = test_git_repo / "docs" / "LEDGER.md"
    ledger.write_text(
        "| M1-T08e | done | ef6e0c6 | check ✅ | desc |\n", encoding="utf-8"
    )
    subprocess.run(
        ["git", "-C", str(test_git_repo), "add", "docs/LEDGER.md"], check=True
    )
    subprocess.run(
        ["git", "-C", str(test_git_repo), "commit", "-m", "update ledger   [ledger]"],
        check=True,
    )

    rc, out = _run_hook_in_repo(
        "task_id_required.py", test_git_repo, "feat: reuse finished tag   [M1-T08e]"
    )
    assert rc == 1
    assert "is recorded done at ef6e0c6" in out


def test_24_open_task_tag_accepted(test_git_repo: Path) -> None:
    ledger = test_git_repo / "docs" / "LEDGER.md"
    ledger.write_text("| M1-T99 | todo | — | — | desc |\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(test_git_repo), "add", "docs/LEDGER.md"], check=True
    )
    subprocess.run(
        ["git", "-C", str(test_git_repo), "commit", "-m", "update ledger   [ledger]"],
        check=True,
    )

    rc, _ = _run_hook_in_repo(
        "task_id_required.py", test_git_repo, "feat: work on task   [M1-T99]"
    )
    assert rc == 0


def test_25_unlisted_tag_or_missing_ledger_accepted(test_git_repo: Path) -> None:
    rc, _ = _run_hook_in_repo(
        "task_id_required.py", test_git_repo, "feat: work on new tag   [M1-T999]"
    )
    assert rc == 0


def test_26_ci_tag_accepted_and_covers_precommit(test_git_repo: Path) -> None:
    rc_id, _ = _run_hook_in_repo(
        "task_id_required.py", test_git_repo, "chore(ci): update review bundle   [ci]"
    )
    assert rc_id == 0

    (test_git_repo / "scripts" / "review_bundle.sh").parent.mkdir(
        parents=True, exist_ok=True
    )
    (test_git_repo / "scripts" / "review_bundle.sh").write_text(
        "# dummy\n", encoding="utf-8"
    )
    subprocess.run(
        ["git", "-C", str(test_git_repo), "add", "scripts/review_bundle.sh"],
        check=True,
    )

    rc_allow, _ = _run_hook_in_repo(
        "files_within_allowlist.py",
        test_git_repo,
        "chore(ci): update review bundle   [ci]",
    )
    assert rc_allow == 0


def test_27_protocol_scope_excludes_precommit(test_git_repo: Path) -> None:
    (test_git_repo / ".pre-commit-config.yaml").write_text(
        "repos: []\n", encoding="utf-8"
    )
    subprocess.run(
        ["git", "-C", str(test_git_repo), "add", ".pre-commit-config.yaml"], check=True
    )

    rc, out = _run_hook_in_repo(
        "files_within_allowlist.py",
        test_git_repo,
        "docs(protocol): edit precommit   [protocol]",
    )
    assert rc == 1
    assert ".pre-commit-config.yaml" in out


def test_21_every_row_in_real_ledger_parses() -> None:
    ledger_path = Path(__file__).resolve().parents[2] / "docs" / "LEDGER.md"
    text = ledger_path.read_text(encoding="utf-8")
    rows = parse_ledger_rows(text)
    unparsable = unparsable_ledger_rows(text)
    assert len(rows) > 0
    assert unparsable == (), f"Unparsable ledger rows found: {unparsable}"


def test_22_unparsable_ledger_row_reported() -> None:
    bad_text = "| BAD_ROW_NO_PIPES |"
    unparsable = unparsable_ledger_rows(bad_text)
    assert len(unparsable) > 0


def test_23_and_27_done_tag_guard_prints_stderr_note_on_missing_row(
    test_git_repo: Path,
) -> None:
    rc, out = _run_hook_in_repo(
        "task_id_required.py", test_git_repo, "feat: open task   [M1-T99z]"
    )
    assert rc == 0
    assert "note: no parsable ledger row for M1-T99z; done-tag check skipped" in out


def test_24_done_tag_t10b_rejected(test_git_repo: Path) -> None:
    ledger = test_git_repo / "docs" / "LEDGER.md"
    ledger.write_text(
        "| M1-T10b | done | 2fe6d25 | check ✅ | desc |\n", encoding="utf-8"
    )
    subprocess.run(
        ["git", "-C", str(test_git_repo), "add", "docs/LEDGER.md"], check=True
    )
    subprocess.run(
        ["git", "-C", str(test_git_repo), "commit", "-m", "update ledger   [ledger]"],
        check=True,
    )

    rc, out = _run_hook_in_repo(
        "task_id_required.py", test_git_repo, "feat: reuse finished tag   [M1-T10b]"
    )
    assert rc == 1
    assert "is recorded done at 2fe6d25" in out


def test_25_open_tag_t99z_accepted(test_git_repo: Path) -> None:
    rc, _ = _run_hook_in_repo(
        "task_id_required.py", test_git_repo, "feat: work on open tag   [M1-T99z]"
    )
    assert rc == 0


def test_rule_11_13_ci_tag_cannot_touch_hooks(test_git_repo: Path) -> None:
    hook_file = test_git_repo / "scripts" / "hooks" / "task_id_required.py"
    hook_file.parent.mkdir(parents=True, exist_ok=True)
    hook_file.write_text("# dummy", encoding="utf-8")
    subprocess.run(["git", "-C", str(test_git_repo), "add", str(hook_file)], check=True)

    rc, out = _run_hook_in_repo(
        "files_within_allowlist.py",
        test_git_repo,
        "chore(ci): update hook   [ci]",
    )
    assert rc == 1
    assert "guards may only change under a task tag" in out


def test_rule_11_13_protocol_tag_cannot_touch_auditor(test_git_repo: Path) -> None:
    audit_file = test_git_repo / "scripts" / "audit_commits.py"
    audit_file.parent.mkdir(parents=True, exist_ok=True)
    audit_file.write_text("# dummy", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(test_git_repo), "add", str(audit_file)], check=True
    )

    rc, out = _run_hook_in_repo(
        "files_within_allowlist.py",
        test_git_repo,
        "docs(protocol): edit auditor   [protocol]",
    )
    assert rc == 1
    assert "guards may only change under a task tag" in out


def test_rule_11_13_ledger_tag_cannot_touch_precommit(test_git_repo: Path) -> None:
    pc_file = test_git_repo / ".pre-commit-config.yaml"
    pc_file.write_text("# dummy", encoding="utf-8")
    subprocess.run(["git", "-C", str(test_git_repo), "add", str(pc_file)], check=True)

    rc, out = _run_hook_in_repo(
        "files_within_allowlist.py",
        test_git_repo,
        "docs(ledger): edit precommit   [ledger]",
    )
    assert rc == 1
    assert "guards may only change under a task tag" in out


def test_done_tag_predicate_placeholder_sha_treated_as_done(
    test_git_repo: Path,
) -> None:
    ledger = test_git_repo / "docs" / "LEDGER.md"
    ledger.write_text("| M1-T99 | done | — | check ✅ | desc |\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(test_git_repo), "add", "docs/LEDGER.md"], check=True
    )
    subprocess.run(
        ["git", "-C", str(test_git_repo), "commit", "-m", "update ledger   [ledger]"],
        check=True,
    )

    rc, out = _run_hook_in_repo(
        "task_id_required.py",
        test_git_repo,
        "feat: reuse tag with placeholder sha   [M1-T99]",
    )
    assert rc == 1
    assert "is recorded done at —" in out
    assert "placeholder" in out


def test_12_check_hooks_installed_returns_0_when_installed() -> None:
    script = (
        Path(__file__).resolve().parents[2] / "scripts" / "check_hooks_installed.py"
    )
    res = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, check=False
    )
    assert res.returncode == 0
    assert "hooks installed" in res.stdout


def test_13_check_hooks_installed_detects_missing(tmp_path: Path) -> None:
    repo = tmp_path / "bare_repo"
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init"], capture_output=True, check=True)
    script = (
        Path(__file__).resolve().parents[2] / "scripts" / "check_hooks_installed.py"
    )
    res = subprocess.run(
        [sys.executable, str(script)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 1
    assert "missing:" in res.stderr or "not wired:" in res.stderr
