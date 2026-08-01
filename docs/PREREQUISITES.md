# Prerequisites and ROM repository acquisition

> Gap identified: no document, card, or script in the project acquires or locates the
> pokeemerald-expansion source tree. `ROM_SOURCING.md` and `M1-T08` both begin from
> `--repo <path>` as a given. Nothing establishes that path.

---

## 1. Ownership boundary: the planner never clones

Acquiring the ROM source is a **human, one-time, out-of-band prerequisite**, not an automated
step in the planner.

This is deliberate. The entire point of the ROM-sourcing change was to remove network access
from the toolchain. If `data build` could `git clone`, you would have reintroduced the network
dependency, the reproducibility hole, and the CI-needs-internet problem in a worse form - a
clone is far less deterministic than an HTTP GET, because branch heads move.

| Action | Who | When |
| --- | --- | --- |
| Clone / fork the expansion base | you, manually | once, before M1 |
| Add `upstream` remote and fetch tags | you, manually | once, before M1 |
| Locate the repo on disk | planner, via config | every run |
| Verify the repo is usable | planner, via `doctor` | every run, and in CI |
| Read data out of the repo | planner, via `cpp` + parser | every build |

The planner's only responsibilities are **locate**, **verify**, and **read**.

---

## 2. One-time setup

### 2.1 Recommended directory layout

Sibling directories, not nested:

```
/home/jpurple/workish/
  poke/                        <- the planner (this project)
  pokeemerald-expansion/       <- your hack, forked from RHH
```

**Do not make the ROM repo a git submodule of the planner.** Three reasons: the hack is the
primary artefact and the planner is a tool that reads it, so the dependency direction would be
inverted; submodule pinning would fight your own hack development, since every ROM commit would
dirty the planner repo; and the expansion tree is large, making every planner clone expensive.

### 2.2 Getting the base

If you have not yet started your hack:

```bash
cd /home/jpurple/workish
git clone https://github.com/rh-hideout/pokeemerald-expansion.git
cd pokeemerald-expansion
git checkout -b myhack expansion/1.15.0     # pin to a release tag, not master
```

If your hack already exists as a fork, ensure the upstream remote is present - this is what
`data diff-upstream` depends on:

```bash
cd /home/jpurple/workish/pokeemerald-expansion
git remote add upstream https://github.com/rh-hideout/pokeemerald-expansion.git
git fetch upstream --tags
```

Without `upstream` fetched, `diff-upstream` has nothing to compare against and must fail with a
clear remedy rather than silently reporting zero differences.

### 2.3 Pin the base version

Record the exact upstream commit your hack forked from. This is the `upstream_sha` in
`planner.db.lock.json`:

```bash
git merge-base HEAD upstream/master
```

If your history is not a clean fork of upstream, set the pin explicitly in `config/paths.yml`
instead of deriving it.

### 2.4 System dependency: a C preprocessor

```bash
cpp --version        # any gcc or clang cpp is fine
```

You do **not** need `agbcc`, `arm-none-eabi-gcc`, `devkitPro`, or the ability to build a ROM.
The planner only preprocesses; it never compiles.

---

## 3. How the planner locates the repo

Resolution precedence, highest first:

1. Explicit CLI flag: `--repo /path/to/pokeemerald-expansion`
2. Environment variable: `NPC_PLANNER_ROM_REPO`
3. `config/paths.yml` key `rom_repo`
4. Sibling-directory convention: `../pokeemerald-expansion` relative to the planner root

If none resolve, fail with `E_ROM_REPO_NOT_FOUND` and print all four locations that were tried.
Do not fall back to a default path that might exist and contain something else.

`config/paths.yml` is machine-specific and therefore **gitignored**, with a committed
`config/paths.example.yml` alongside it.

```yaml
# config/paths.example.yml
rom_repo: /home/jpurple/workish/pokeemerald-expansion
upstream_sha: null      # null = derive via git merge-base
cpp: cpp
```

---

## 4. CI and test story

CI must **never** clone the expansion repo. Tests run against `tests/fixtures/fake_rom/`, a
minimal committed tree of a few hundred lines that reproduces the real layout: config headers
with `#if` guards, a two-species `species_info.h`, a short `moves_info.h`, and a `trainers.party`.

This keeps the check ladder fast and hermetic, and it means a layout regression is caught by a
fixture diff rather than by an eight-minute clone.

The real repo is exercised only by `make gate`, and only when `NPC_PLANNER_ROM_REPO` is set.
When it is unset, gate skips those checks and says so out loud rather than passing silently.

---

## 5. What breaks without this document

| Missing piece | Symptom |
| --- | --- |
| No acquisition step | Implementer invents a path, or worse, adds a `git clone` to `build.py` |
| No `upstream` remote | `diff-upstream` reports zero changes; every hack edit looks like vanilla |
| No `cpp` check | Extraction fails deep inside the pipeline with a `FileNotFoundError` on the binary |
| No resolution precedence | Four cards hard-code four different paths |
| No CI story | Someone adds a clone to CI, and the build needs internet again |
