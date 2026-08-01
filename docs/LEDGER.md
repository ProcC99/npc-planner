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
| M1-T00 | done | fedd831 | check ✅ | `environment.py` + `scripts/doctor.py`: environment doctor & ROM repo resolution |
| M1-T00b | done | 990edc9 | check ✅ | `environment.py` + `scripts/doctor.py`: explicit severity model, exit contract & shared fixtures |
| M1-T01 | done | af35512 | check ✅ | `pyproject.toml` + package init + `config.py` path resolution |
| M1-T02 | done | c3e21f3 | check ✅ | `models/envelope.py`: generic `Envelope[T]` + its unit tests |
| M1-T03 | done | 817e7fa | check ✅ | `db/schema.sql`: 26 domain tables (DDL only, no views) |
| M1-T04 | done | b75a15c | check ✅ | `db/schema.sql`: 5 staging tables + 2 views + `docs/schema_manifest.txt` |
| M1-T05 | done | 641e5f6 | check ✅ | `db/session.py`: connection factory, WAL, `foreign_keys=ON` |
| M1-T06 | done | c2943c1 | check ✅ | `db/models.py`: Pydantic row models for the 26 domain tables |
| M1-T07 | done | 44fa31c | check ✅ | `tests/fixtures/fake_rom/`: fake expansion repo fixture tree |
| M1-T08 | done | 78ac4df | check ✅ | `rom_probe.py` + `preprocess_rom.py`: ROM layout probe, git pinning, cpp harness |
| M1-T08b | done | 7e74720 | check ✅ | `preprocess_rom.py`: route repo resolution through environment & preflight check exit 3 |
| M1-T08c | done | 9abb6e8 | check ✅ | `environment.py` + `preprocess_rom.py`: scope preprocess preflight, git-optional pinning |
| M1-T08d | done | 0e999bc | check ✅ | `files_within_allowlist.py`: enforce card allowlist, derivable manifest count |
| M1-T08e | done | ef6e0c6 | check ✅ | `task_id_required.py` + `files_within_allowlist.py`: close untagged loophole, make gate, history audit |
| M1-T09 | done | 15feb07 | check ✅ | `cparse.py`: designated-initializer C parser |
| M1-T10 | done | 1487f98 | check ✅ | `ingest/rom_config.py`: config-header reader (`B_*`, `P_*`, limits, AI flags) |
| M1-T10b | done | 2fe6d25 | check ✅ | `ingest/rom_config.py`: correct config reader bucketing & symbol coverage |
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

---

## Known Historical Violations (Audited by M1-T08e / M1-T10b)

These pre-T08e/T10b commits contained scope or allowlist violations when checked retrospectively by `scripts/audit_commits.py`.
Per Amendment 11, history is not rewritten; violations are recorded here for transparency.

- `7b86b79` (M1-T01): touched files outside allowlist (`.gitignore`, `Makefile`, `README.md`, `docs/schema_manifest.txt`, `docs/tasks/M3-T02.md`, `scripts/check_schema_manifest.py`, `scripts/hooks/*`, `tests/integration/test_init.py`)
- `f02628d` (M1-T03): touched file outside allowlist (`scripts/check_schema_manifest.py`)
- `a911ccb` (M1-T04): touched file outside allowlist (`tests/unit/test_schema_ddl.py`)
- `bec24b7`: untagged commit
- `9544c72`: untagged commit (`docs(tasks): add task cards for M1-T10, M1-T11, M1-T12`)
- `141b6d7` (M1-T07): touched files outside allowlist (`docs/tasks/M1-T08.md`, `docs/tasks/M1-T09.md`)
- `5782db7` (M1-T00): touched files outside allowlist (`docs/PREREQUISITES.md`, `src/npc_planner/config.py`)
- `837226f`: untagged commit
- `d45f410` (M1-T00b): touched file outside allowlist (`docs/tasks/M1-T08b.md`)
- `0d561ef` (M1-T08b): touched file outside allowlist (`scripts/doctor.py`)
- `eb67381` (M1-T08c): tagged `[M1-T08c]` but card `docs/tasks/M1-T08c.md` was not committed in tree
- `3d68f61`: untagged commit (`docs(tasks): commit M1-T08c and M1-T08d cards`)
- `872e751`: untagged commit (`fixup! update task_id_required to support task letter suffixes`)
- `052b862`: untagged commit (`fixup! add M1-T08e card`)
- `7d22d8f` (M1-T08e): tag reused after task recorded done in ledger (tag-shopping, not malice)
- `737dc19` (M1-T08e): tag reused after task recorded done in ledger (tag-shopping, not malice)

- 2026-08-01 [ci]: added `scripts/review_bundle.sh` and `review-bundle` Makefile target per M1-T11 Step 0b.
