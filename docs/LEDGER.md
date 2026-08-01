# Progress Ledger — NPC Team Planner

Updated in the same commit as the work. A fresh session reads this file first
and picks up the first `todo`.

Status: `todo | in-progress | done | blocked | reverted`

**Blocked is a first-class outcome.** A precise one-sentence question costs five
minutes of human time. A guess costs a day of debugging three milestones later.

---

## M1 — Core Schema, ROM-Sourced Ingest & CLI Stub  → tag `m1-core`

| Task | Status | Commit | Gate | Description |
|---|---|---|---|---|
| M1-T00 | done | pending | check ✅ | `environment.py` + `scripts/doctor.py`: environment doctor & ROM repo resolution |
| M1-T01 | done | af35512 | check ✅ | `pyproject.toml` + package init + `config.py` path resolution |
| M1-T02 | done | c3e21f3 | check ✅ | `models/envelope.py`: generic `Envelope[T]` + its unit tests |
| M1-T03 | done | 817e7fa | check ✅ | `db/schema.sql`: 26 domain tables (DDL only, no views) |
| M1-T04 | done | b75a15c | check ✅ | `db/schema.sql`: 5 staging tables + 2 views + `docs/schema_manifest.txt` |
| M1-T05 | done | 641e5f6 | check ✅ | `db/session.py`: connection factory, WAL, `foreign_keys=ON` |
| M1-T06 | done | c2943c1 | check ✅ | `db/models.py`: Pydantic row models for the 26 domain tables |
| M1-T07 | done | 44fa31c | check ✅ | `tests/fixtures/fake_rom/`: fake expansion repo fixture tree |
| M1-T08 | done | 78ac4df | check ✅ | `rom_probe.py` + `preprocess_rom.py`: ROM layout probe, git pinning, cpp harness |
| M1-T09 | done | 15feb07 | check ✅ | `cparse.py`: designated-initializer C parser |
| M1-T10 | todo | — | — | `ingest/rom_config.py`: config-header reader (`B_*`, `P_*`, limits, AI flags) |
| M1-T11 | todo | — | — | `ingest/extract/species.py`: species and forms extractor |
| M1-T12 | todo | — | — | `ingest/extract/moves.py`: moves extractor |
| M1-T13 | todo | — | — | `ingest/extract/abilities.py`: abilities extractor |
| M1-T14 | todo | — | — | `ingest/extract/types.py`: types and matchup-matrix extractor |
| M1-T15 | todo | — | — | `ingest/extract/learnsets_levelup.py`: level-up learnset extractor |
| M1-T16 | todo | — | — | `ingest/extract/learnsets_teachable.py`: teachable and egg learnset extractor |
| M1-T17 | todo | — | — | `ingest/extract/evolutions.py`: evolutions extractor |
| M1-T18 | todo | — | — | `ingest/extract/items.py`: items extractor |
| M1-T19 | todo | — | — | `ingest/extract/encounters.py`: wild-encounter JSON loader |
| M1-T20 | todo | — | — | `ingest/extract/trainers_party.py`: trainer `.party` reader |
| M1-T21 | todo | — | — | `ingest/stage.py`: staging writer (extracted records to `stg_*`) |
| M1-T22 | todo | — | — | `ingest/provenance.py`: provenance stamping (`rom_extract`, confidence, source_record) |
| M1-T23 | todo | — | — | `ingest/build.py`: build orchestrator and `planner.db.lock.json` writer |
| M1-T24 | todo | — | — | `cli/main.py`: CLI stub (`data build`, `pokemon show`) |

## M2 — Overlay Engine & Baseline Diffing  → tag `m2-overlay`

| Task | Status | Commit | Gate | Description |
|---|---|---|---|---|
| M2-T01 | todo | — | — | `ingest/overlay.py`: YAML envelope header parse + schema validation |
| M2-T02 | todo | — | — | 5-layer precedence merge + per-field provenance stamping |
| M2-T03 | todo | — | — | `diff_against_upstream()` via `git show` |
| M2-T04 | todo | — | — | `cli/commands/diff_upstream.py` + smoke test |

## M3 — Ruleset Chain & Legality Engine  → tag `m3-legality`

| Task | Status | Commit | Gate | Description |
|---|---|---|---|---|
| M3-T01 | todo | — | — | 3 ruleset YAML files (data authoring) |
| M3-T02 | todo | — | — | `rules/ruleset.py`: `resolve()` extends chain, cycle + missing-parent errors |
| M3-T03 | todo | — | — | `resolve_damage_class()` across the 3 damage-class models |
| M3-T04 | todo | — | — | `rules/context.py`: `LegalityContext` builder |
| M3-T05 | todo | — | — | `legality.py` dimensions 1–6 (implementation & availability) |
| M3-T06 | todo | — | — | `legality.py` dimensions 7–12 (AI, tech, uncertainty, bans, gates) |
| M3-T07 | todo | — | — | `LegalityVerdict` + `LegalityFailure` suggestion strings |
