import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


class RomLayoutUnknownError(RuntimeError):
    """Raised when no known expansion layout matches the repo. Error code E_ROM_LAYOUT_UNKNOWN."""


@dataclass(frozen=True)
class RomLayout:
    species_info: list[Path]
    moves_info: Path
    abilities: Path
    types_info: Path
    items: Path
    level_up_learnsets: Path
    teachable_learnsets: Path
    egg_moves: Path
    wild_encounters_json: Path
    trainers: Path
    trainers_format: str
    config_headers: list[Path]
    layout_id: str


@dataclass(frozen=True)
class RomPin:
    repo_path: Path
    hack_sha: str
    hack_dirty: bool
    upstream_remote: str | None
    upstream_sha: str | None
    expansion_version: str | None


def probe_layout(repo_path: Path) -> RomLayout:
    """Detect which expansion layout this repo uses.

    Raises RomLayoutUnknownError listing which expected paths were missing.
    Never guesses: if species data cannot be located, it raises.
    """
    repo = Path(repo_path).resolve()
    missing: list[str] = []

    # Check species info
    species_single = repo / "src/data/pokemon/species_info.h"
    species_multi = list(repo.glob("src/data/pokemon/species_info/*.h"))

    species_files: list[Path] = []
    if species_single.exists():
        species_files = [species_single]
    elif species_multi:
        species_files = species_multi
    else:
        missing.append("src/data/pokemon/species_info.h or species_info/*.h")

    # Moves info
    moves = repo / "src/data/moves_info.h"
    if not moves.exists():
        moves = repo / "src/data/battle_moves.h"
    if not moves.exists():
        missing.append("src/data/moves_info.h")

    # Abilities
    abilities = repo / "src/data/abilities.h"
    if not abilities.exists():
        missing.append("src/data/abilities.h")

    # Types info
    types = repo / "src/data/types_info.h"
    if not types.exists():
        types = repo / "src/battle_main.c"
    if not types.exists():
        missing.append("src/data/types_info.h")

    # Items
    items = repo / "src/data/items.h"
    if not items.exists():
        missing.append("src/data/items.h")

    # Learnsets
    lvl = repo / "src/data/pokemon/level_up_learnsets.h"
    if not lvl.exists():
        missing.append("src/data/pokemon/level_up_learnsets.h")

    teach = repo / "src/data/pokemon/teachable_learnsets.h"
    if not teach.exists():
        missing.append("src/data/pokemon/teachable_learnsets.h")

    egg = repo / "src/data/pokemon/egg_moves.h"
    if not egg.exists():
        missing.append("src/data/pokemon/egg_moves.h")

    # Wild encounters
    wild = repo / "src/data/wild_encounters.json"
    if not wild.exists():
        missing.append("src/data/wild_encounters.json")

    # Trainers
    trainers = repo / "src/data/trainers.party"
    trainers_fmt = "party"
    if not trainers.exists():
        trainers = repo / "src/data/trainers.h"
        trainers_fmt = "c_headers"
    if not trainers.exists():
        missing.append("src/data/trainers.party or trainers.h")

    if missing:
        raise RomLayoutUnknownError(
            f"Failed to probe ROM layout for '{repo}': missing expected files: {', '.join(missing)}"
        )

    config_headers = [
        p
        for p in [
            repo / "include/config/battle.h",
            repo / "include/config/pokemon.h",
            repo / "include/config/species_enabled.h",
        ]
        if p.exists()
    ]

    return RomLayout(
        species_info=species_files,
        moves_info=moves,
        abilities=abilities,
        types_info=types,
        items=items,
        level_up_learnsets=lvl,
        teachable_learnsets=teach,
        egg_moves=egg,
        wild_encounters_json=wild,
        trainers=trainers,
        trainers_format=trainers_fmt,
        config_headers=config_headers,
        layout_id="expansion_1_9_plus",
    )


def read_pin(repo_path: Path) -> RomPin:
    """Read git SHAs and dirty state via subprocess git calls."""
    repo = Path(repo_path).resolve()

    def run_git(args: list[str]) -> str | None:
        try:
            res = subprocess.run(
                ["git", "-C", str(repo)] + args,
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                return res.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            return None
        return None

    sha = run_git(["rev-parse", "HEAD"]) or "0000000000000000000000000000000000000000"
    status = run_git(["status", "--porcelain"])
    dirty = bool(status)

    upstream_remote = run_git(["config", "--get", "remote.origin.url"])
    upstream_sha = run_git(["rev-parse", "@{u}"])

    version: str | None = None
    exp_h = repo / "include/constants/expansion.h"
    if exp_h.exists():
        text = exp_h.read_text(encoding="utf-8")
        m = re.search(r'#define\s+EXPANSION_VERSION\s+"([^"]+)"', text)
        if m:
            version = m.group(1)

    return RomPin(
        repo_path=repo,
        hack_sha=sha,
        hack_dirty=dirty,
        upstream_remote=upstream_remote,
        upstream_sha=upstream_sha,
        expansion_version=version,
    )
