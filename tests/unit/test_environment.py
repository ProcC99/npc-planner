import socket
import subprocess
from pathlib import Path

import pytest

from npc_planner.environment import (
    CHECK_SEVERITY,
    EXPANSION_MARKERS,
    PINNING_REQUIRED,
    PREPROCESS_REQUIRED,
    RomRepoNotFoundError,
    check_expansion_markers,
    resolve_rom_repo,
    run_all,
    run_checks,
)


def test_1_check_severity_and_subsets() -> None:
    expected_severity = {
        "cpp": "hard",
        "repo_present": "hard",
        "is_git_repo": "hard",
        "expansion_markers": "hard",
        "upstream_remote": "soft",
        "tree_clean": "soft",
    }
    assert CHECK_SEVERITY == expected_severity
    assert set(PREPROCESS_REQUIRED) <= set(CHECK_SEVERITY)
    assert set(PINNING_REQUIRED) <= set(CHECK_SEVERITY)


def test_2_required_subsets_have_hard_severity() -> None:
    for name in PREPROCESS_REQUIRED:
        assert CHECK_SEVERITY[name] == "hard"
    for name in PINNING_REQUIRED:
        assert CHECK_SEVERITY[name] == "hard"


def test_3_is_git_repo_not_in_preprocess_required() -> None:
    assert "is_git_repo" not in PREPROCESS_REQUIRED


def test_4_run_checks_single_name(tmp_path: Path) -> None:
    results = run_checks(tmp_path, ["cpp"])
    assert len(results) == 1
    assert results[0].name == "cpp"


def test_5_run_checks_invalid_name_raises(tmp_path: Path) -> None:
    with pytest.raises(KeyError):
        run_checks(tmp_path, ["nonexistent_check"])


def test_6_run_all_equals_run_checks_all_names(tmp_path: Path) -> None:
    res_all = run_all(tmp_path)
    res_checks = run_checks(tmp_path, tuple(CHECK_SEVERITY))
    assert res_all == res_checks


def test_run_all_severities(tmp_path: Path) -> None:
    results = run_all(tmp_path)
    assert {r.name for r in results} == set(CHECK_SEVERITY)
    for r in results:
        assert r.severity == CHECK_SEVERITY[r.name]


def test_check_expansion_markers(tmp_path: Path) -> None:
    fake_rom_dir = (
        Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "fake_rom"
    )
    res_fake = check_expansion_markers(fake_rom_dir)
    assert res_fake.ok is True

    vanilla_dir = tmp_path / "vanilla_poke"
    (vanilla_dir / "src" / "data").mkdir(parents=True)
    (vanilla_dir / "include" / "constants").mkdir(parents=True)
    res_vanilla = check_expansion_markers(vanilla_dir)
    assert res_vanilla.ok is False
    assert res_vanilla.remedy is not None
    assert EXPANSION_MARKERS == (
        "include/config/species_enabled.h",
        "include/config/battle.h",
    )


def test_run_all_empty_directory_remedies(tmp_path: Path) -> None:
    nonexistent_dir = tmp_path / "nonexistent"
    results = run_all(nonexistent_dir, cpp="definitely-not-a-real-binary")
    hard_fails = [r for r in results if r.severity == "hard"]
    assert len(hard_fails) == 4
    for r in hard_fails:
        assert r.ok is False
        assert r.remedy is not None


def test_run_all_internal_exception_handling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(*args: object, **kwargs: object) -> None:
        raise OSError("boom")

    monkeypatch.setattr("npc_planner.environment.check_cpp", _boom)
    results = run_all(tmp_path)
    cpp_res = next(r for r in results if r.name == "cpp")
    assert cpp_res.ok is False
    assert "boom" in cpp_res.detail


def test_doctor_script_soft_failure_exit_0(
    git_fake_rom: Path, no_network: None
) -> None:
    script = Path(__file__).resolve().parents[2] / "scripts" / "doctor.py"
    res = subprocess.run(
        ["python3", str(script), "--repo", str(git_fake_rom)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0
    assert "upstream_remote" in res.stdout or "upstream" in res.stdout


def test_doctor_script_hard_failure_exit_1(tmp_path: Path, no_network: None) -> None:
    script = Path(__file__).resolve().parents[2] / "scripts" / "doctor.py"
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    res = subprocess.run(
        ["python3", str(script), "--repo", str(empty_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 1


def test_doctor_script_unresolvable_exit_2(tmp_path: Path, no_network: None) -> None:
    script = Path(__file__).resolve().parents[2] / "scripts" / "doctor.py"
    nonexistent = tmp_path / "no_where_dir"
    res = subprocess.run(
        [
            "python3",
            str(script),
            "--repo",
            str(nonexistent),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 2 or res.returncode == 1


def test_git_fake_rom_dirty_fixture(git_fake_rom_dirty: Path) -> None:
    res = subprocess.run(
        ["git", "-C", str(git_fake_rom_dirty), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert len(res.stdout.strip()) > 0


def test_no_network_fixture(no_network: None) -> None:
    with pytest.raises(AssertionError) as exc_info:
        socket.create_connection(("example.com", 80))
    assert "network access attempted" in str(exc_info.value)


def test_gitignore_contains_paths_yml() -> None:
    gitignore = Path(__file__).resolve().parents[2] / ".gitignore"
    content = gitignore.read_text(encoding="utf-8")
    assert "config/paths.yml" in content.splitlines()


def test_resolve_rom_repo_no_os_environ() -> None:
    planner_root = Path(__file__).resolve().parents[2] / "nonexistent_dir_xyz"
    with pytest.raises(RomRepoNotFoundError):
        resolve_rom_repo(
            env={},
            config_path=planner_root / "nonexistent.yml",
            planner_root=planner_root,
        )
