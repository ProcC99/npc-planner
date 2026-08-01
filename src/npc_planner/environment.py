import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

Severity = Literal["hard", "soft"]


class RomRepoNotFoundError(RuntimeError):
    """No ROM repo could be resolved. Error code E_ROM_REPO_NOT_FOUND."""


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    severity: Severity
    detail: str
    remedy: str | None  # shell command or instruction; None when ok


def resolve_rom_repo(
    explicit: Path | str | None = None,
    env: dict[str, str] | None = None,
    config_path: Path | str | None = None,
    planner_root: Path | str | None = None,
) -> Path:
    """Resolve the ROM repo path.

    Precedence: explicit > env NPC_PLANNER_ROM_REPO > config/paths.yml rom_repo
              > sibling ../pokeemerald-expansion
    """
    candidates: list[tuple[str, Path]] = []

    if explicit is not None:
        p_exp = Path(explicit).resolve()
        candidates.append(("explicit CLI argument", p_exp))
        if p_exp.exists() and p_exp.is_dir():
            return p_exp

    env_map = env if env is not None else dict(os.environ)
    if env_map.get("NPC_PLANNER_ROM_REPO"):
        p_env = Path(env_map["NPC_PLANNER_ROM_REPO"]).resolve()
        candidates.append(("env NPC_PLANNER_ROM_REPO", p_env))
        if p_env.exists() and p_env.is_dir():
            return p_env

    root = (
        Path(planner_root).resolve()
        if planner_root
        else Path(__file__).resolve().parents[2]
    )
    cfg_file = Path(config_path).resolve() if config_path else root / "config/paths.yml"
    if cfg_file.exists():
        try:
            data = yaml.safe_load(cfg_file.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("rom_repo"):
                p_cfg = Path(data["rom_repo"]).resolve()
                candidates.append(("config/paths.yml key 'rom_repo'", p_cfg))
                if p_cfg.exists() and p_cfg.is_dir():
                    return p_cfg
        except (OSError, yaml.YAMLError, ValueError):
            pass

    p_sib = (root.parent / "pokeemerald-expansion").resolve()
    candidates.append(
        ("sibling directory convention '../pokeemerald-expansion'", p_sib)
    )
    if p_sib.exists() and p_sib.is_dir():
        return p_sib

    attempted_str = "\n".join(f"  - {label}: {p}" for label, p in candidates)
    raise RomRepoNotFoundError(
        "Failed to locate pokeemerald-expansion repo tree (Error E_ROM_REPO_NOT_FOUND).\n"
        f"Attempted locations:\n{attempted_str}\n"
        "Remedy: Specify --repo /path/to/repo, set NPC_PLANNER_ROM_REPO, or edit config/paths.yml."
    )


def check_cpp(cpp: str = "cpp") -> CheckResult:
    binary = shutil.which(cpp)
    if binary:
        return CheckResult(
            name="C preprocessor (cpp)",
            ok=True,
            severity="hard",
            detail=f"Found C preprocessor at {binary}",
            remedy=None,
        )
    return CheckResult(
        name="C preprocessor (cpp)",
        ok=False,
        severity="hard",
        detail=f"C preprocessor '{cpp}' not found in PATH",
        remedy="Install GCC/Clang C preprocessor (e.g., 'sudo apt install build-essential' or 'gcc')",
    )


def check_repo_present(repo_path: Path) -> CheckResult:
    p = repo_path.resolve()
    if p.exists() and p.is_dir():
        return CheckResult(
            name="ROM repo directory",
            ok=True,
            severity="hard",
            detail=f"Directory exists at {p}",
            remedy=None,
        )
    return CheckResult(
        name="ROM repo directory",
        ok=False,
        severity="hard",
        detail=f"ROM repo directory '{p}' does not exist",
        remedy=f"Clone pokeemerald-expansion into '{p}'",
    )


def check_is_git_repo(repo_path: Path) -> CheckResult:
    p = repo_path.resolve()
    if (p / ".git").exists() or (p / "HEAD").exists():
        return CheckResult(
            name="Git repository",
            ok=True,
            severity="hard",
            detail=f"Directory '{p}' is a valid Git repository",
            remedy=None,
        )
    try:
        res = subprocess.run(
            ["git", "-C", str(p), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and "true" in res.stdout.strip():
            return CheckResult(
                name="Git repository",
                ok=True,
                severity="hard",
                detail=f"Directory '{p}' is inside a Git work tree",
                remedy=None,
            )
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass

    return CheckResult(
        name="Git repository",
        ok=False,
        severity="hard",
        detail=f"Directory '{p}' is not a Git repository",
        remedy=f"Run 'git init' inside '{p}' or clone a fresh repository",
    )


def check_expansion_markers(repo_path: Path) -> CheckResult:
    p = repo_path.resolve()
    markers = [
        p / "include/config/species_enabled.h",
        p / "include/config/battle.h",
        p / "include/config/pokemon.h",
    ]
    found = [m for m in markers if m.exists()]
    if found:
        return CheckResult(
            name="pokeemerald-expansion markers",
            ok=True,
            severity="hard",
            detail=f"Found {len(found)} expansion config markers in '{p}'",
            remedy=None,
        )
    return CheckResult(
        name="pokeemerald-expansion markers",
        ok=False,
        severity="hard",
        detail=f"Directory '{p}' does not contain pokeemerald-expansion config headers (appears to be vanilla pret or empty)",
        remedy=f"Ensure '{p}' is a pokeemerald-expansion repository (e.g. fork of rh-hideout/pokeemerald-expansion)",
    )


def check_upstream_remote(repo_path: Path) -> CheckResult:
    p = repo_path.resolve()
    try:
        res = subprocess.run(
            ["git", "-C", str(p), "remote", "-v"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and "upstream" in res.stdout:
            return CheckResult(
                name="Git upstream remote",
                ok=True,
                severity="soft",
                detail="Upstream remote configured in Git repository",
                remedy=None,
            )
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass

    return CheckResult(
        name="Git upstream remote",
        ok=False,
        severity="soft",
        detail=f"Repository '{p}' has no 'upstream' remote configured",
        remedy="git remote add upstream https://github.com/rh-hideout/pokeemerald-expansion.git && git fetch upstream --tags",
    )


def check_tree_clean(repo_path: Path) -> CheckResult:
    p = repo_path.resolve()
    try:
        res = subprocess.run(
            ["git", "-C", str(p), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and not res.stdout.strip():
            return CheckResult(
                name="Git working tree clean",
                ok=True,
                severity="soft",
                detail="Working tree is clean",
                remedy=None,
            )
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass

    return CheckResult(
        name="Git working tree clean",
        ok=False,
        severity="soft",
        detail=f"Working tree in '{p}' has uncommitted changes",
        remedy="Commit or stash local changes in the ROM repository before running strict builds",
    )


def run_all(repo_path: Path, cpp: str = "cpp") -> list[CheckResult]:
    """Run every check. Never raises; failures are reported as CheckResult rows."""
    results: list[CheckResult] = []

    try:
        results.append(check_cpp(cpp))
    except (OSError, RuntimeError, ValueError) as e:
        results.append(
            CheckResult("C preprocessor (cpp)", False, "hard", str(e), "Install cpp")
        )

    try:
        results.append(check_repo_present(repo_path))
    except (OSError, RuntimeError, ValueError) as e:
        results.append(
            CheckResult(
                "ROM repo directory",
                False,
                "hard",
                str(e),
                "Specify valid repo directory",
            )
        )

    try:
        results.append(check_is_git_repo(repo_path))
    except (OSError, RuntimeError, ValueError) as e:
        results.append(
            CheckResult(
                "Git repository",
                False,
                "hard",
                str(e),
                "Run git init in repo directory",
            )
        )

    try:
        results.append(check_expansion_markers(repo_path))
    except (OSError, RuntimeError, ValueError) as e:
        results.append(
            CheckResult(
                "pokeemerald-expansion markers",
                False,
                "hard",
                str(e),
                "Provide expansion repo",
            )
        )

    try:
        results.append(check_upstream_remote(repo_path))
    except (OSError, RuntimeError, ValueError) as e:
        results.append(
            CheckResult(
                "Git upstream remote",
                False,
                "soft",
                str(e),
                "git remote add upstream <url>",
            )
        )

    try:
        results.append(check_tree_clean(repo_path))
    except (OSError, RuntimeError, ValueError) as e:
        results.append(
            CheckResult(
                "Git working tree clean",
                False,
                "soft",
                str(e),
                "Stash uncommitted changes",
            )
        )

    return results
