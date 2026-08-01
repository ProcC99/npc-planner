# NPC Team Planner — Execution Protocol

**Audience:** the implementing agent (assumed to be a low-cost model with a short context window, weak long-range consistency, and a tendency to declare success early).

**Purpose:** make every unit of work small, independently verifiable, and cheaply revertible, so that a wrong turn costs one commit instead of one milestone.

This document is normative. Where it conflicts with `implementation_plan.md`, this document wins on *process*; the plan wins on *content*.

---

## 0. The Prime Directives

These exist because they are the specific ways a cheap model destroys a codebase. Read them before every task.

1. **Never modify a test to make it pass.** If a test fails, the code is wrong, or the test is wrong *and you must say so explicitly and stop*. Changing an assertion to match observed output is a protocol violation.
2. **Never regenerate a golden snapshot to make it pass.** Golden files change only via `make golden-update`, only when a human has approved the diff, and only in a commit that touches nothing else.
3. **Never delete, skip, or `xfail` a test to unblock yourself.** Stop and report instead.
4. **Never write a stub that returns a plausible value.** A not-yet-implemented function raises `NotImplementedError`. A function that returns `0.0`, `[]`, or `None` to keep the pipeline running is worse than a crash, because it silently poisons every score downstream.
5. **Never touch a file outside the task's declared file list.** If you believe you must, stop and report.
6. **Never invent an API.** If you do not know a library's signature, check the installed package or the docs. Do not guess a `pydantic` or `typer` call and hope.
7. **Never mark a task complete with a failing or skipped check.** `make check` green is the only definition of done.
8. **One task, one commit, one green check.** Do not batch.

---

## 1. Work Decomposition

The six milestones (M1–M6) each break into **tasks**. A task is the atomic unit of work and must satisfy:

- Touches **≤ 5 files** (excluding its own test file).
- Is described by a **single sentence** without the word "and".
- Ships with tests **in the same commit**.
- Has **one acceptance command** that a human can run.
- Takes the implementing model **one focused session** — no cross-session state.

If a task cannot meet all five, it is not a task; split it.

### Task card format

Every task is written up before implementation, in `docs/tasks/M<n>-T<nn>.md`, using this template. The implementing model receives **only the card and the files it names** — not the whole plan.

```markdown
# M3-T04 — Ruleset inheritance resolver

## Goal
Resolve a ruleset id through its `extends` chain into a single flattened Ruleset object.

## Files you may create or modify
- src/npc_planner/rules/ruleset.py
- tests/unit/test_ruleset_resolve.py

## Files you may read but NOT modify
- src/npc_planner/db/models.py
- data/rulesets/*.yml

## Files you may NOT touch
- everything else

## Contract
```python
def resolve(ruleset_id: str, *, registry: RulesetRegistry) -> Ruleset:
    """Flatten `extends` chain, child keys override parent keys.

    Raises CircularExtendsError on a cycle.
    Raises UnknownRulesetError if any id in the chain is missing.
    List-valued keys (bans, clauses) CONCATENATE unless the child sets
    `replace_<key>: true`.
    """
```

## Must-pass tests
1. `vanilla_gen3` resolves to itself, no parent.
2. `gba_modernized_no_items` resolves through 2 levels; `damage_class_model == "split"` inherited from the middle layer.
3. Child ban list concatenates with parent's; `replace_bans: true` discards parent's.
4. A 3-node cycle raises `CircularExtendsError`.
5. Unknown parent id raises `UnknownRulesetError` naming the missing id.

## Out of scope — do NOT implement
- Damage class resolution per move (that is M3-T05)
- Any legality evaluation

## Acceptance command
```bash
make check && python -c "from npc_planner.rules.ruleset import resolve; print(resolve('gba_modernized_no_items').damage_class_model)"
# expected: split
```

## Definition of Done
- [ ] All 5 must-pass tests written and passing
- [ ] `make check` green
- [ ] No file outside the allowed list changed (`git diff --name-only` verified)
- [ ] Ledger row updated
```

The **"Out of scope"** section is not optional. It is the single most effective guard against a cheap model helpfully implementing four adjacent things badly.

---

## 2. Git Discipline

### Branch topology

```
main                  # always green, always releasable
 └── milestone/M3     # long-lived per milestone, merged to main at tag
      └── task/M3-T04 # short-lived, one task, squashed into milestone branch
```

- `main` is protected. Nothing lands on it except a milestone merge.
- A milestone branch merges to `main` only when its **milestone gate** (§4) passes.
- Task branches are squash-merged into the milestone branch. One task = one commit on the milestone branch.

### Commit message format

Conventional Commits, with the task id mandatory:

```
<type>(<scope>): <imperative summary>   [M3-T04]

<why, not what — 1-3 lines>

Tests: <what was added>
Gate:  make check green / <failing gate if WIP>
```

`type` ∈ `feat | fix | test | refactor | chore | docs | data | revert`
`scope` ∈ `db | ingest | rules | analysis | generate | validate | export | cli | config | ci`

Example:

```
feat(rules): resolve ruleset extends chain   [M3-T04]

Legality evaluation needs a single flattened ruleset; resolving
lazily at call sites made bans order-dependent.

Tests: 5 unit tests incl. cycle + missing-parent failure modes
Gate:  make check green
```

### Commit cadence

- **Commit at every green check.** Never leave uncommitted green work.
- **Never commit red** to a task branch except as an explicit `wip:` commit that will be squashed away.
- **Never amend or force-push** a commit that has been merged into a milestone branch.
- **Never squash a milestone branch into a single commit at merge.** The per-task history is the audit trail; it is how a human bisects the model's mistakes.
- **The ledger sha is never written in the commit it describes.** The task commit is made and its sha becomes final; then the ledger row is written in a separate `[ledger]` commit. Two commits per task, always.


### Tags

Each milestone gate produces an annotated tag:

```bash
git tag -a m3-legality -m "M3 gate passed: ruleset chain + 12-dim legality + explain CLI"
```

Tags are the rollback anchors. If M5 goes badly, `git reset --hard m4-analysis` is a clean, known-good state.

### Required repo hygiene files

| File | Purpose |
|---|---|
| `.gitignore` | `planner.db`, `planner.db-wal`, `planner.db-shm`, `data/raw/baseline/`, `exports/`, `__pycache__/`, `.pytest_cache/`, `.venv/` |
| `.gitattributes` | `*.db binary`, `tests/golden/** -diff` (keeps diffs readable) |
| `data/raw/baseline/.gitkeep` | directory exists, contents never committed |
| `planner.db.lock.json` | **is** committed — it is the reproducibility contract |

The built database is never committed. The lockfile that proves how it was built always is.

---

## 3. The Check Ladder

Five rungs, each cheaper and more frequent than the one above. `make check` is rungs 1–4.

| Rung | Command | Runs | Budget |
|---|---|---|---|
| 1. Static | `make lint` | every save | < 5 s |
| 2. Contract | `make typecheck` | every save | < 15 s |
| 3. Unit | `make test-unit` | every commit | < 30 s |
| 4. Integration | `make test-int` | every commit | < 90 s |
| 5. Gate | `make gate` | every milestone | < 10 min |

### Makefile

```makefile
.PHONY: lint typecheck test-unit test-int check gate golden-update fresh

lint:
	ruff check src tests
	ruff format --check src tests

typecheck:
	mypy --strict src/npc_planner

test-unit:
	pytest tests/unit -q --maxfail=1

test-int:
	pytest tests/integration -q --maxfail=1

check: lint typecheck test-unit test-int
	@echo "✅ check green"

gate: check
	pytest tests/golden tests/performance -q
	npc-planner data build --strict
	npc-planner validate --fail-on error
	@echo "✅ gate green"

fresh:                       # reproducibility: build twice, compare
	rm -f data/processed/planner.db
	npc-planner data build --strict
	sha256sum data/processed/planner.db > /tmp/a
	rm -f data/processed/planner.db
	npc-planner data build --strict
	sha256sum data/processed/planner.db | sed 's|.*|&|' > /tmp/b
	diff <(cut -d' ' -f1 /tmp/a) <(cut -d' ' -f1 /tmp/b) && echo "✅ build reproducible"

golden-update:               # HUMAN APPROVAL REQUIRED — never run unprompted
	pytest tests/golden --snapshot-update
	@echo "⚠️  Review `git diff tests/golden` line by line before committing."
```

### Pre-commit hook (`.pre-commit-config.yaml`)

The hook is the enforcement mechanism, because a cheap model will not reliably self-police.

- `ruff` + `ruff-format`
- `mypy` on changed files
- **custom hook: `no-test-deletion`** — rejects a commit whose diff removes a `def test_` line without a matching `docs/waivers/` entry
- **custom hook: `no-golden-edit`** — rejects any commit that touches `tests/golden/` alongside non-golden files
- **custom hook: `task-id-required`** — rejects a commit message without a `[M<n>-T<nn>]` tag
- `check-added-large-files --maxkb=512`

---

## 4. Milestone Gates

A milestone is not done when its files exist. It is done when its gate passes. Each gate is cumulative — M4's gate re-runs M1–M3's checks.

| Gate | Must pass | Human-verifiable proof |
|---|---|---|
| **G1** | `make gate`; `fresh` build reproducible; 10-species fixture loads; every row in `provenance` has non-null `source_type` | `npc-planner pokemon show skarmory` prints stats + `official_baseline` provenance |
| **G2** | G1 + overlay precedence tests for all 5 layers + diff is non-empty and correct | `npc-planner data diff-baseline --scope species` shows Skarmory Def 65→140, `hack_override` |
| **G3** | G2 + all 12 dimensions individually unit-tested pass **and** fail + invariant test: no analysis fn callable without `LegalityContext` | `npc-planner explain --entity move --key sheer-cold --trainer data/trainers/gym_04.yml` prints 12 rows, one FAIL with a reason |
| **G4** | G3 + type matrix property test (N×N complete, multipliers ∈ {0,.25,.5,1,2,4}) + coverage weighted by player pool, not uniform | `npc-planner movesets pelipper --level 33` returns ≥1 legal set and a non-empty `excluded` array with reasons |
| **G5** | G4 + every scoring weight loaded from `config/*.yml` (grep: zero float literals in scorer bodies) + difficulty hard-gates reject | `npc-planner score-team --file tests/fixtures/gym_04_manual.yml` prints per-component breakdown summing to the total |
| **G6** | G5 + golden determinism + perf budget + all 12 `E_*` codes triggered by negative fixtures | `npc-planner generate-team --trainer data/trainers/gym_04.yml --seed 1337 --variants all` → 3 variants, each with counterplay ≥ band floor |

**Gate failure protocol:** do not patch forward. `git reset --hard` to the previous tag, re-read the failing task card, and redo the single task that broke it.

---

## 5. Anti-Regression Harness

Because a cheap model will happily break M2 while writing M5, these run on **every** commit from the milestone they are introduced onward.

### 5.1 Invariant tests (`tests/unit/test_invariants.py`)

Cheap, absolute, and they catch architectural drift rather than logic bugs.

- No function in `analysis/` or `generate/` is callable without a `LegalityContext`. Enforce by signature inspection over the module, not by hand-written cases — that way new functions are covered automatically.
- No scorer module contains a bare float literal outside a docstring or a default of `None`. Enforced by AST walk. This is what keeps config-as-data from quietly eroding.
- Every `E_*` and `W_*` code in the catalogue has at least one raising site and one test.
- Every public function has a return type annotation.
- The set of tables in `schema.sql` equals the set in `docs/schema_manifest.txt` exactly. This kills the "21 vs 26 tables" class of drift permanently.

### 5.2 Smoke suite (`tests/integration/test_smoke.py`)

One test per CLI command, asserting exit code 0 and a well-formed `Envelope`. Added the moment each command exists. Runs in under 20 s. This is the single highest-value-per-token test file in the repo.

### 5.3 Golden snapshots (`tests/golden/`)

Committed, human-reviewed, byte-compared:

- `planner.db.lock.json` for the fixture dataset
- `type_matrix.csv`
- `explain_sheer_cold.txt`
- `movesets_pelipper_33.json`
- `generate_gym04_seed1337.json`

Rules: a golden diff in a PR requires a human to say the words "golden approved" in the merge commit. A golden diff that appears in a commit alongside source changes is auto-rejected by the pre-commit hook.

### 5.4 Negative fixtures (`tests/fixtures/broken/`)

One deliberately malformed overlay per `E_*` code, named after it (`E_LEARNSET_MISSING_MOVE.yml`). The test parametrizes over the directory, so adding a code without a fixture fails collection. This makes the validator suite self-enforcing.

---

## 6. Progress Ledger

`docs/LEDGER.md`, updated in the same commit as the work. This is how a fresh session recovers context without re-reading the codebase.

```markdown
| Task | Status | Commit | Gate | Notes |
|---|---|---|---|---|
| M3-T03 | done | a91f2c3 | check ✅ | — |
| M3-T04 | done | 7de0b11 | check ✅ | replace_bans semantics differ from spec §8; spec updated |
| M3-T05 | blocked | — | — | needs decision: does Hidden Power damage class follow the split? |
| M3-T06 | todo | — | — | — |
```

Status ∈ `todo | in-progress | done | blocked | reverted`.

**Blocked is a first-class outcome.** The model should reach for it. A task marked `blocked` with a precise one-sentence question costs five minutes of human time; a task where the model guessed costs a day of debugging three milestones later.

---

## 7. Session Protocol for the Implementing Model

Every session, in order, no exceptions:

1. `git status` — confirm clean tree. If dirty, stop and report.
2. `git log --oneline -5` — orient.
3. Read `docs/LEDGER.md` — find the first `todo`.
4. Read **only** that task card and the files it names.
5. `make check` — confirm green *before* changing anything. If red on arrival, stop and report; do not attempt to fix inherited breakage inside a feature task.
6. `git checkout -b task/M<n>-T<nn>`.
7. **Write the tests first.** Run them. Confirm they fail for the right reason.
8. Implement until green.
9. `git diff --name-only` — verify against the card's allowed file list. Any extra file is a violation; revert it.
10. `make check`.
11. Commit with the full message format.
12. Update `docs/LEDGER.md`, amend into the commit.
13. Squash-merge into `milestone/M<n>`.
14. Stop. One task per session.

### Stop-and-report triggers

The model must halt and ask rather than proceed when any of these occur:

- A test fails and the fix appears to require changing the test.
- The task requires touching a file outside its list.
- The spec and the plan disagree.
- A required upstream function does not exist yet.
- The implementation would require a network call.
- Two consecutive attempts at the same failing test did not converge.
- A golden snapshot would need to change.

All seven are cheap to escalate and expensive to guess through.

---

## 8. Human Review Cadence

| When | What the human checks | Time |
|---|---|---|
| Per task | Commit diff — scope creep and stub-shaped code only | 2 min |
| Per 5 tasks | Ledger + `git log --stat` — is the shape still right? | 10 min |
| Per milestone gate | Run the proof command by hand. Read the golden diffs. | 30 min |
| Per golden change | Line by line, always | as needed |

The per-task review is deliberately shallow — you are looking for two things only: files that should not have changed, and functions that return a value without computing it.

---

## 9. Rollback Playbook

| Situation | Action |
|---|---|
| Task went wrong, not merged | `git checkout milestone/M<n> && git branch -D task/...` |
| Bad task merged into milestone | `git revert <sha>` — revert, never rewrite |
| Milestone gate fails, cause unclear | `git bisect start HEAD m<n-1>-<name>` then `git bisect run make check` |
| Milestone is structurally wrong | `git reset --hard m<n-1>-<name>`, rewrite the task cards, redo |
| Golden drifted silently | `git checkout m<n-1>-<name> -- tests/golden/` and re-run |

The tags make all five of these one-liners. That is their entire purpose.

---

## 10. Prompt Preamble for the Implementing Model

Prepend this to every task-execution prompt. It is short on purpose — a long preamble gets truncated or ignored.

```
You are implementing ONE task from a task card. Rules:

1. Read the card. Implement exactly what it says. Nothing adjacent.
2. Write tests first. Watch them fail. Then implement.
3. Touch only the files the card lists. Verify with `git diff --name-only`.
4. Never edit a test or a golden file to make something pass.
5. Never return a placeholder value. Unimplemented = raise NotImplementedError.
6. Do not guess an API. Check the installed package.
7. `make check` must be green before you commit. No skips, no xfail.
8. If you are stuck twice on the same failure, STOP and report the
   blocker in one sentence. Do not improvise.
9. Commit once, with the task id in the message. Update docs/LEDGER.md.
10. Then stop. Do not start the next task.
```

---

## 11. Execution Protocol — Amendment 11 (Rev 3)

Effective from `M1-T08c` onward.

Every rule here exists because something already went wrong. The cause is named in each case, so that a future reader can judge whether the rule still earns its place.

### 11.1 Task cards are immutable during their own task

**A task card must never appear in its own "Files you may create or modify" list.**

The agent executing `M1-TXX` may not edit, truncate, reformat, or rewrite `docs/tasks/M1-TXX.md`.
It may read it as many times as it likes.

*Cause:* `M1-T00b` and `M1-T08b` both listed themselves as modifiable. Both were rewritten during execution to roughly 24% of their original length, and in both cases the deleted material was the Must-pass tests section. The Definition of Done then referred to "all 11 must-pass tests" in a document that no longer contained any. A task that can edit its own acceptance criteria has no acceptance criteria.

If a card is wrong, the only legal responses are:
1. Mark the task `blocked` in `docs/LEDGER.md` with a one-sentence reason, and stop.
2. Continue, and record the discrepancy in the commit body.

A follow-up card corrects the original. Cards are never edited in place by the agent that runs them. The human author may edit any card at any time.

**The task card is committed to the milestone branch before the task branch is created.**

```bash
git checkout milestone/M1
git add docs/tasks/M1-T08d.md
git commit -m "docs(tasks): add M1-T08d card"
git checkout -b task/M1-T08d
```

Card immutability cannot be enforced against a file git has never seen, and a card that is never committed is not part of the project's history at all.

The commit that adds a task card carries `[protocol]`, never the task's own tag. A task-tagged commit has its allowlist read from the card in `HEAD`, so it cannot be the commit that introduces that card.

### 11.2 Must-pass sections are preserved verbatim

The Goal, Contract, Must-pass tests, Out of scope, Acceptance command, and Definition of Done sections are load-bearing. None may be shortened, summarised, merged, or reflowed by the agent.

When the human trims a card before handing it over, the Must-pass tests section is the one part that must survive intact. It is the only section that produces artifacts a later reviewer can check. Prose can be reconstructed; a deleted test is invisible forever.

*Cause:* the `remedy`-on-failure requirement in `M1-T00` was deleted on intake, restored in `M1-T00b`, and deleted again on intake of `M1-T00b`. Twice-lost requirements are not accidents, they are a process defect.

### 11.3 Acceptance runs from a script file

Every card from `M1-T08c` onward ships `scripts/accept/<TASK_ID>.sh`. The Acceptance command section contains exactly one line:

```bash
bash scripts/accept/<TASK_ID>.sh
```

Rules for acceptance scripts:
- Source `scripts/accept/_lib.sh`; use `expect_exit` and `expect_stdout`. Never assert with a bare `&&` chain.
- Do **not** `set -e`. Assertions that expect a non-zero exit are normal and must not abort the run.
- Use `set -uo pipefail`.
- Run `make check` as the first assertion and `accept_summary` as the last.
- Every temporary directory is removed on exit via `trap`.
- A unit test must run `bash -n` over every file in `scripts/accept/`, so a syntactically broken acceptance script fails `make check`.

*Cause:* the acceptance blocks for `M1-T00b` and `M1-T08b` were pasted into a runner that flattened newlines. The result parsed as `make check` followed by a list of unknown goals. Make aborted, no `echo` ever ran, and not one of the nine expected exit codes was observed - while both tasks were recorded as `done` with acceptance verified. The multi-line block was the defect; single-argument invocation removes the failure mode entirely.

### 11.4 Guards must be able to fail

Before a regression guard is accepted, demonstrate that it fails against the state it is meant to prevent. If a guard cannot be made to fail, it is decoration.

Specifically:
- Prefer **source-text assertions** over `hasattr` / attribute-name checks. A name check catches only the exact spelling you thought of.
- Prefer asserting over a **whole collection** (`assert MAPPING == {...}`) rather than key by key, so that additions are caught, not just changes.
- Assert on **artifacts** (files written, exit codes, manifest contents) rather than on the absence of an exception.

*Cause:* `M1-T08b`'s single-resolver guard asserted `not hasattr(config, "resolve_rom_repo")`. The duplicate resolver in the codebase was named `get_rom_repo_path`, so the guard passed both before and after the fix.

### 11.5 A scope error is fixed by narrowing, not by weakening

When a check turns out to be too strict for one caller, do **not** downgrade the check. Introduce a named subset and let that caller require the subset.

*Cause:* `is_git_repo` is genuinely a hard requirement for reproducible pinning and a genuine non-requirement for running `cpp`. The tempting fix was to make it soft, which would have silently weakened the doctor for every caller. The correct fix is `PREPROCESS_REQUIRED` alongside `PINNING_REQUIRED`, with `CHECK_SEVERITY` untouched.

Corollary: subsets are data, they live next to the thing they subset, and a test asserts that each subset is contained in the parent and that its members carry the expected severity.

### 11.6 Cross-task regressions are the reviewer's first question

When a task changes a shared entry point, the Definition of Done must include re-running the acceptance command of every earlier task that uses it.

`M1-T08b` changed `preprocess_rom.py`, which `M1-T08` had already accepted. `M1-T08`'s acceptance command was never re-run, so a `done` task quietly stopped working. `make check` stayed green because the unit tests had been migrated to a different fixture in the same commit.

Green tests after a shared-entry-point change prove less than they appear to. Ask which earlier acceptance script still passes.

### 11.7 Scope tags and enforcement

Every non-merge commit must carry exactly one recognised scope tag in its subject:

| Tag | Meaning | Files that may be staged |
|---|---|---|
| `[M<n>-T<id>]` | Task work | The card's allowlist, plus `docs/LEDGER.md` |
| `[ledger]` | Ledger bookkeeping only | `docs/LEDGER.md` |
| `[protocol]` | Protocol and card text only | `EXECUTION_PROTOCOL.md`, `docs/PROTOCOL_AMENDMENT_*.md`, `docs/tasks/*.md` |
| `[ci]` | CI mechanism only | `.pre-commit-config.yaml`, `Makefile`, `.github/` |

Enforced by `scripts/hooks/task_id_required.py` and `scripts/hooks/files_within_allowlist.py` at the `commit-msg` stage.

A task tag may only be used while that task is open. Once `docs/LEDGER.md` records the task as `done` with a commit sha, further commits carrying that tag are rejected. Follow-up work needs a new lettered card.

### 11.8 Staged files must fall within the card's allowlist

A commit tagged `[M<n>-T<id>]` may stage only files matching the bullet list under **"Files you may create or modify"** in `docs/tasks/M<n>-T<id>.md`, plus `docs/LEDGER.md`.

The allowlist is read from the card **as committed in HEAD**, never from the working tree. A card edited locally must not be able to widen its own allowlist for the commit being made.

Work that does not fit belongs in a separate chore commit. Protocol scaffolding, hook installation, and documentation restructuring are chore work, not task work.

Enforced by `scripts/hooks/files_within_allowlist.py` at the `commit-msg` stage.

### 11.9 `--no-verify` is prohibited

`--no-verify` is prohibited. If a hook blocks a commit, fix the commit or fix the hook under a card in its own commit.
Prohibition is checked by:
1. `scripts/check_hooks_installed.py` as the first step of `make check`.
2. `scripts/audit_commits.py` at every milestone close to audit historical commits.

### 11.10 Working-tree gate without committing

`make gate` runs the identical set of checks the hooks run against the working tree without creating a commit:

```make
gate:
	python3 scripts/check_hooks_installed.py
	python3 -m ruff format --check src tests scripts
	python3 -m ruff check src tests scripts
	python3 -m mypy --strict src/npc_planner
	python3 -m pytest tests/unit -q
	python3 -m pytest tests/integration -q
	python3 scripts/check_schema_manifest.py
	python3 -m pre_commit run --all-files
```

Note `ruff format --check` and `ruff check` with no `--fix`. Edit until `make gate` is green, then `git add`, then commit once. If you have amended more than twice, stop and report instead of continuing.

### 11.11 CI scope

Changes to CI mechanism files - `.pre-commit-config.yaml`, `Makefile`, `.github/` - are tagged `[ci]`. A `[ci]` commit must touch only those paths and must add a dated line to `docs/LEDGER.md` naming what changed and why. `.pre-commit-config.yaml` is **not** part of `[protocol]` scope: a protocol commit edits the rules as written, never the machinery that enforces them.

---

## Appendix A — Task Count Estimate

| Milestone | Tasks | Rationale |
|---|---|---|
| M1 | 6 | schema, session, envelope, fetch script, baseline load, provenance |
| M2 | 4 | overlay parse, precedence merge, diff, build orchestration |
| M3 | 6 | 3 ruleset files, resolver, context, legality ×2, explain CLI |
| M4 | 6 | type matrix, defense, coverage, roles, move pool, synthesizer |
| M5 | 8 | 4 config files, 2 scorers, difficulty, player_resources, counterplay |
| M6 | 9 | pool, search, local search, variants, pipeline, 3 exporters, test suites |

**≈ 39 tasks.** If any milestone's task list comes out under half these numbers, the tasks are too big for the model executing them.
