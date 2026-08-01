# Progress Ledger — NPC Team Planner

Updated in the same commit as the work. A fresh session reads this file first
and picks up the first `todo`.

Status: `todo | in-progress | done | blocked | reverted`

**Blocked is a first-class outcome.** A precise one-sentence question costs five
minutes of human time. A guess costs a day of debugging three milestones later.

---

## M1 — Core Schema, Baseline Import & CLI Stub  → tag `m1-core`

| Task | Status | Commit | Gate | Description |
|---|---|---|---|---|
| M1-T01 | done | af35512 | check ✅ | `pyproject.toml` + package init + `config.py` path resolution |
| M1-T02 | done | c3e21f3 | check ✅ | `models/envelope.py`: generic `Envelope[T]` + its unit tests |
| M1-T03 | done | 817e7fa | check ✅ | `db/schema.sql`: 26 domain tables (DDL only, no views) |
| M1-T04 | done | b75a15c | check ✅ | `db/schema.sql`: 5 staging tables + 2 views + `docs/schema_manifest.txt` |
| M1-T05 | done | pending | check ✅ | `db/session.py`: connection factory, WAL, `foreign_keys=ON` |
| M1-T06 | todo | — | — | `db/models.py`: Pydantic row models for the 26 domain tables |
| M1-T07 | todo | — | — | `tests/fixtures/m1_tiny/`: 10-species fixture dataset (data authoring) |
| M1-T08 | todo | — | — | `scripts/fetch_baseline.py`: network-isolated dump fetcher |
| M1-T09 | todo | — | — | `ingest/baseline.py`: disk-only load of raw dumps into `stg_*` |
| M1-T10 | todo | — | — | `ingest/provenance.py`: `record_field`, `entity_confidence`, `uncertainties` |
| M1-T11 | todo | — | — | `ingest/build.py`: orchestration + `planner.db.lock.json` |
| M1-T12 | todo | — | — | `cli/main.py` stub + `data build` + `pokemon show` + smoke tests |

## M2 — Overlay Engine & Baseline Diffing  → tag `m2-overlay`

| Task | Status | Commit | Gate | Description |
|---|---|---|---|---|
| M2-T01 | todo | — | — | `ingest/overlay.py`: YAML envelope header parse + schema validation |
| M2-T02 | todo | — | — | 5-layer precedence merge + per-field provenance stamping |
| M2-T03 | todo | — | — | `diff_against_baseline()` |
| M2-T04 | todo | — | — | `cli/commands/diff_baseline.py` + smoke test |

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
| M3-T08 | todo | — | — | `cli/commands/explain.py` + golden `explain_sheer_cold.txt` |
| M3-T09 | todo | — | — | Invariant test: no analysis fn callable without a `LegalityContext` |

## M4 — Analytical Core & Moveset Synthesizer  → tag `m4-analysis`

| Task | Status | Commit | Gate | Description |
|---|---|---|---|---|
| M4-T01 | todo | — | — | `analysis/types.py`: `type_matrix` + property test on multipliers |
| M4-T02 | todo | — | — | `analysis/defense.py`: raw typing profile |
| M4-T03 | todo | — | — | `analysis/defense.py`: ability-adjusted profile + effective bulk |
| M4-T04 | todo | — | — | `analysis/coverage.py`: `moveset_coverage` weighted by player pool |
| M4-T05 | todo | — | — | `analysis/coverage.py`: `team_coverage` + walling-combo detector |
| M4-T06 | todo | — | — | `analysis/roles.py`: 8-role classifier with competence scores |
| M4-T07 | todo | — | — | `analysis/movesets.py`: `legal_move_pool` |
| M4-T08 | todo | — | — | `analysis/movesets.py`: `synthesize_movesets` (top 5 legal 4-move sets) |
| M4-T09 | todo | — | — | `cli/commands/movesets.py` + smoke test |

## M5 — Config Scorers, Difficulty & Counterplay  → tag `m5-scoring`

| Task | Status | Commit | Gate | Description |
|---|---|---|---|---|
| M5-T01 | todo | — | — | `config/scoring.yml` + loader + schema validation |
| M5-T02 | todo | — | — | `config/roles.yml` + `config/archetypes.yml` + `config/difficulty.yml` |
| M5-T03 | todo | — | — | `scoring_pokemon.py`: StatProfile, Typing, MovePool components |
| M5-T04 | todo | — | — | `scoring_pokemon.py`: Ability, Availability, AIUsability, ThemeFit + penalties |
| M5-T05 | todo | — | — | `scoring_team.py`: Coverage, DefensiveSynergy, RoleCompleteness |
| M5-T06 | todo | — | — | `scoring_team.py`: ThemeCoherence, DifficultyFit, SharedWeaknessPenalty |
| M5-T07 | todo | — | — | Invariant test: zero float literals in scorer bodies (AST walk) |
| M5-T08 | todo | — | — | `analysis/difficulty.py`: index + band mapping + hard gates |
| M5-T09 | todo | — | — | `player_resources()` derived from progression stages |
| M5-T10 | todo | — | — | `analysis/counterplay.py`: `team_counterplay`, min-member availability |
| M5-T11 | todo | — | — | `tests/fixtures/gym_04_manual.yml` hand-written team (data authoring) |
| M5-T12 | todo | — | — | Expand `data/hack/` to 60 species (data authoring, no code) |
| M5-T13 | todo | — | — | `cli/commands/score_team.py` + smoke test |

## M6 — Generation Engine, Exporters & Testing  → tag `m6-generate`

| Task | Status | Commit | Gate | Description |
|---|---|---|---|---|
| M6-T01 | todo | — | — | `generate/pool.py` + `E_POOL_TOO_SMALL` / `W_THIN_POOL` |
| M6-T02 | todo | — | — | `generate/search.py`: beam search (width 16–24), deterministic ordering |
| M6-T03 | todo | — | — | `generate/search.py`: local-search swap optimizer |
| M6-T04 | todo | — | — | `generate/variants.py`: easier / standard / harder transforms |
| M6-T05 | todo | — | — | Hard-reject checks (counterplay floor, softlock, level delta) |
| M6-T06 | todo | — | — | `generate/pipeline.py` orchestration |
| M6-T07 | todo | — | — | `validate/validators.py`: the 12 `E_*` codes |
| M6-T08 | todo | — | — | `validate/report.py` + `cli` `validate` / `uncertainties` commands |
| M6-T09 | todo | — | — | `tests/fixtures/broken/`: one negative fixture per `E_*` code |
| M6-T10 | todo | — | — | `analysis/charts.py` |
| M6-T11 | todo | — | — | `export/markdown.py` |
| M6-T12 | todo | — | — | `export/csv.py`: balance sheet + `export_chart_csv` |
| M6-T13 | todo | — | — | `export/jsonspec.py` round-trip test |
| M6-T14 | todo | — | — | `cli/commands/generate_team.py` + smoke test |
| M6-T15 | todo | — | — | `tests/golden/`: subprocess determinism + inverse-seed assertion |
| M6-T16 | todo | — | — | `tests/performance/`: perf budget on a pinned fixture DB |

---

**Total: 63 tasks.** Every row touches ≤5 files and is describable in one
sentence without the word "and". Rows that needed an "and" were split.
