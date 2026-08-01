import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

Severity = Literal["hard", "soft"]

CHECK_SEVERITY: dict[str, Severity] = {
    "cpp": "hard",
    "repo_present": "hard",
    "is_git_repo": "hard",
    "expansion_markers": "hard",
    "upstream_remote": "soft",
    "tree_clean": "soft",
}

EXPANSION_MARKERS: tuple[str, ...] = (
    "include/config/species_enabled.h",
    "include/config/battle.h",
)

# Checks that must pass before it is safe to run `cpp` over a tree.
# Git is deliberately absent: preprocessing reads files, it does not read history.
PREPROCESS_REQUIRED: tuple[str, ...] = (
    "cpp",
    "repo_present",
    "expansion_markers",
)

# Checks that must pass before a build may claim to be reproducibly pinned.
PINNING_REQUIRED: tuple[str, ...] = (
    "repo_present",
    "is_git_repo",
)


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

    env_map = env if env is not None else {}
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
    severity = CHECK_SEVERITY["cpp"]
    if binary:
        return CheckResult(
            name="cpp",
            ok=True,
            severity=severity,
            detail=f"Found C preprocessor at {binary}",
            remedy=None,
        )
    return CheckResult(
        name="cpp",
        ok=False,
        severity=severity,
        detail=f"C preprocessor '{cpp}' not found in PATH",
        remedy="Install GCC/Clang C preprocessor (e.g., 'sudo apt install build-essential' or 'gcc')",
    )


def check_repo_present(repo_path: Path) -> CheckResult:
    p = repo_path.resolve()
    severity = CHECK_SEVERITY["repo_present"]
    if p.exists() and p.is_dir():
        return CheckResult(
            name="repo_present",
            ok=True,
            severity=severity,
            detail=f"Directory exists at {p}",
            remedy=None,
        )
    return CheckResult(
        name="repo_present",
        ok=False,
        severity=severity,
        detail=f"ROM repo directory '{p}' does not exist",
        remedy=f"Clone pokeemerald-expansion into '{p}'",
    )


def check_is_git_repo(repo_path: Path) -> CheckResult:
    p = repo_path.resolve()
    severity = CHECK_SEVERITY["is_git_repo"]
    if (p / ".git").exists():
        return CheckResult(
            name="is_git_repo",
            ok=True,
            severity=severity,
            detail=f"Directory '{p}' is a valid Git repository",
            remedy=None,
        )
    try:
        res = subprocess.run(
            ["git", "-C", str(p), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and Path(res.stdout.strip()).resolve() == p:
            return CheckResult(
                name="is_git_repo",
                ok=True,
                severity=severity,
                detail=f"Directory '{p}' is a Git repository root",
                remedy=None,
            )
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass

    return CheckResult(
        name="is_git_repo",
        ok=False,
        severity=severity,
        detail=f"Directory '{p}' is not a Git repository",
        remedy=f"Run 'git init' inside '{p}' or clone a fresh repository",
    )


def check_expansion_markers(repo_path: Path) -> CheckResult:
    p = repo_path.resolve()
    severity = CHECK_SEVERITY["expansion_markers"]
    found = [m for m in EXPANSION_MARKERS if (p / m).exists()]
    if found:
        return CheckResult(
            name="expansion_markers",
            ok=True,
            severity=severity,
            detail=f"Found {len(found)} expansion config markers in '{p}'",
            remedy=None,
        )
    return CheckResult(
        name="expansion_markers",
        ok=False,
        severity=severity,
        detail=f"Directory '{p}' does not contain pokeemerald-expansion config headers (appears to be vanilla pret or empty)",
        remedy=f"Ensure '{p}' is a pokeemerald-expansion repository (e.g. fork of rh-hideout/pokeemerald-expansion)",
    )


def check_upstream_remote(repo_path: Path) -> CheckResult:
    p = repo_path.resolve()
    severity = CHECK_SEVERITY["upstream_remote"]
    try:
        res = subprocess.run(
            ["git", "-C", str(p), "remote", "-v"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and "upstream" in res.stdout:
            return CheckResult(
                name="upstream_remote",
                ok=True,
                severity=severity,
                detail="Upstream remote configured in Git repository",
                remedy=None,
            )
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass

    return CheckResult(
        name="upstream_remote",
        ok=False,
        severity=severity,
        detail=f"Repository '{p}' has no 'upstream' remote configured",
        remedy="git remote add upstream https://github.com/rh-hideout/pokeemerald-expansion.git && git fetch upstream --tags",
    )


def check_tree_clean(repo_path: Path) -> CheckResult:
    p = repo_path.resolve()
    severity = CHECK_SEVERITY["tree_clean"]
    try:
        res = subprocess.run(
            ["git", "-C", str(p), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and not res.stdout.strip():
            return CheckResult(
                name="tree_clean",
                ok=True,
                severity=severity,
                detail="Working tree is clean",
                remedy=None,
            )
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass

    return CheckResult(
        name="tree_clean",
        ok=False,
        severity=severity,
        detail=f"Working tree in '{p}' has uncommitted changes",
        remedy="Commit or stash local changes in the ROM repository before running strict builds",
    )


def run_checks(
    repo_path: Path,
    names: Sequence[str],
    cpp: str = "cpp",
) -> list[CheckResult]:
    """Run only the named checks, in the order given.

    Raises KeyError if any name is not a key of CHECK_SEVERITY.
    Never raises for check failures; those are returned as CheckResult rows.
    """
    results: list[CheckResult] = []

    for name in names:
        if name not in CHECK_SEVERITY:
            raise KeyError(f"Unknown check name: {name}")

        try:
            if name == "cpp":
                res = check_cpp(cpp)
            elif name == "repo_present":
                res = check_repo_present(repo_path)
            elif name == "is_git_repo":
                res = check_is_git_repo(repo_path)
            elif name == "expansion_markers":
                res = check_expansion_markers(repo_path)
            elif name == "upstream_remote":
                res = check_upstream_remote(repo_path)
            elif name == "tree_clean":
                res = check_tree_clean(repo_path)
            else:
                raise KeyError(f"Unhandled check name: {name}")
            results.append(res)
        except (OSError, RuntimeError, ValueError) as e:
            results.append(
                CheckResult(
                    name=name,
                    ok=False,
                    severity=CHECK_SEVERITY[name],
                    detail=f"Check raised internal exception: {e}",
                    remedy="Investigate system error",
                )
            )

    return results


def run_all(repo_path: Path, cpp: str = "cpp") -> list[CheckResult]:
    """Equivalent to run_checks(repo_path, tuple(CHECK_SEVERITY), cpp)."""
    return run_checks(repo_path, tuple(CHECK_SEVERITY), cpp=cpp)
