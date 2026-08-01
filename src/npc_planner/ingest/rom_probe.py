import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


class RomLayoutUnknownError(ValueError):
    """Raised when an expansion tree cannot be mapped to a layout specification."""


@dataclass(frozen=True)
class RomPin:
    repo_path: Path
    hack_sha: str | None
    hack_dirty: bool
    upstream_remote: str | None
    upstream_sha: str | None
    expansion_version: str | None
    pinned: bool


# RomLayout attributes that are C headers and therefore cpp-able.
# wild_encounters_json is JSON and trainers is a .party file; neither is preprocessed.
PREPROCESSABLE_FIELDS: tuple[str, ...] = (
    "species_info",
    "moves_info",
    "abilities",
    "types_info",
    "items",
    "level_up_learnsets",
    "teachable_learnsets",
    "egg_moves",
)


@dataclass(frozen=True)
class RomLayout:
    layout_id: str
    config_headers: tuple[Path, ...]
    config_constants: tuple[Path, ...]
    species_info: tuple[Path, ...]
    moves_info: Path
    abilities: Path
    types_info: Path
    items: Path
    level_up_learnsets: Path
    teachable_learnsets: Path
    egg_moves: Path
    wild_encounters: Path
    trainers: Path
    trainers_format: str  # "party" | "json"

    def preprocessable_paths(self) -> list[Path]:
        """De-duplicated paths for preprocessable C headers in this layout."""
        targets = ("species_info", "moves_info", "abilities", "types_info", "items")
        paths: list[Path] = []
        for name in targets:
            val = getattr(self, name)
            if isinstance(val, (tuple, list)):
                for p in val:
                    if p not in paths:
                        paths.append(p)
            elif isinstance(val, Path) and val not in paths:
                paths.append(val)
        return paths


def probe_layout(repo_path: Path) -> RomLayout:
    p = repo_path.resolve()

    species_h = p / "src" / "data" / "pokemon" / "species_info.h"
    moves_h = p / "src" / "data" / "moves_info.h"
    abilities_h = p / "src" / "data" / "abilities.h"
    types_h = p / "src" / "data" / "types_info.h"
    items_h = p / "src" / "data" / "items.h"
    levelup_h = p / "src" / "data" / "pokemon" / "level_up_learnsets.h"
    teachable_h = p / "src" / "data" / "pokemon" / "teachable_learnsets.h"
    egg_h = p / "src" / "data" / "pokemon" / "egg_moves.h"

    wild_json = p / "src" / "data" / "wild_encounters.json"
    trainers_party = p / "src" / "data" / "trainers.party"
    trainers_json = p / "src" / "data" / "trainers.json"

    essential_files = [
        species_h,
        moves_h,
        abilities_h,
        types_h,
        items_h,
        levelup_h,
        teachable_h,
        egg_h,
        wild_json,
    ]
    missing = [f for f in essential_files if not f.exists()]
    if missing:
        missing_str = ", ".join(str(f.relative_to(p)) for f in missing)
        raise RomLayoutUnknownError(
            f"Cannot detect ROM layout for '{p}': essential file(s) missing: {missing_str}"
        )

    if trainers_party.exists():
        t_path = trainers_party
        t_fmt = "party"
    elif trainers_json.exists():
        t_path = trainers_json
        t_fmt = "json"
    else:
        raise RomLayoutUnknownError(
            f"Cannot detect ROM layout for '{p}': missing trainers.party or trainers.json"
        )

    cfg_dir = p / "include" / "config"
    cfg_headers = (
        cfg_dir / "battle.h",
        cfg_dir / "pokemon.h",
        cfg_dir / "species_enabled.h",
    )

    const_dir = p / "include" / "constants"
    const_headers = tuple(sorted(const_dir.glob("*.h"))) if const_dir.exists() else ()

    return RomLayout(
        layout_id="expansion_1_9_plus",
        config_headers=cfg_headers,
        config_constants=const_headers,
        species_info=(species_h,),
        moves_info=moves_h,
        abilities=abilities_h,
        types_info=types_h,
        items=items_h,
        level_up_learnsets=levelup_h,
        teachable_learnsets=teachable_h,
        egg_moves=egg_h,
        wild_encounters=wild_json,
        trainers=t_path,
        trainers_format=t_fmt,
    )


def read_pin(repo_path: Path) -> RomPin:
    p = repo_path.resolve()

    def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(p)] + args,
            capture_output=True,
            text=True,
            check=False,
        )

    # Shell out to git to test if repo_path itself is the root of a Git repository
    res_toplevel = run_git(["rev-parse", "--show-toplevel"])
    if res_toplevel.returncode != 0 or Path(res_toplevel.stdout.strip()).resolve() != p:
        return RomPin(
            repo_path=p,
            hack_sha=None,
            hack_dirty=False,
            upstream_remote=None,
            upstream_sha=None,
            expansion_version="unpinned",
            pinned=False,
        )

    res_status = run_git(["status", "--porcelain"])
    hack_dirty = bool(res_status.stdout.strip())

    res_head = run_git(["rev-parse", "HEAD"])
    hack_sha = res_head.stdout.strip() if res_head.returncode == 0 else None

    res_remotes = run_git(["remote", "-v"])
    upstream_remote: str | None = None
    if res_remotes.returncode == 0 and "upstream" in res_remotes.stdout:
        for line in res_remotes.stdout.splitlines():
            if line.startswith("upstream"):
                parts = line.split()
                if len(parts) >= 2:
                    upstream_remote = parts[1]
                    break

    upstream_sha: str | None = None
    if upstream_remote:
        res_ush = run_git(["rev-parse", "upstream/HEAD"])
        if res_ush.returncode == 0:
            upstream_sha = res_ush.stdout.strip()

    expansion_version: str | None = None
    exp_header = p / "include" / "constants" / "expansion.h"
    if exp_header.exists():
        txt = exp_header.read_text(encoding="utf-8")
        m = re.search(r'#define\s+EXPANSION_VERSION\s+"([^"]+)"', txt)
        if m:
            expansion_version = m.group(1)

    if not expansion_version:
        expansion_version = "1.9.0+"

    return RomPin(
        repo_path=p,
        hack_sha=hack_sha,
        hack_dirty=hack_dirty,
        upstream_remote=upstream_remote,
        upstream_sha=upstream_sha,
        expansion_version=expansion_version,
        pinned=True,
    )
