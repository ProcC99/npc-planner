# Execution Protocol - Amendment 11

> Append as §11 of `EXECUTION_PROTOCOL.md`. Effective from `M1-T08c` onward.
>
> Every rule here exists because something already went wrong. The cause is named in each case,
> so that a future reader can judge whether the rule still earns its place.

---

## 11.1 Task cards are immutable during their own task

**A task card must never appear in its own "Files you may create or modify" list.**

The agent executing `M1-TXX` may not edit, truncate, reformat, or rewrite `docs/tasks/M1-TXX.md`.
It may read it as many times as it likes.

*Cause:* `M1-T00b` and `M1-T08b` both listed themselves as modifiable. Both were rewritten during
execution to roughly 24% of their original length, and in both cases the deleted material was the
Must-pass tests section. The Definition of Done then referred to "all 11 must-pass tests" in a
document that no longer contained any. A task that can edit its own acceptance criteria has no
acceptance criteria.

If a card is wrong, the only legal responses are:

1. Mark the task `blocked` in `docs/LEDGER.md` with a one-sentence reason, and stop.
2. Continue, and record the discrepancy in the commit body.

A follow-up card corrects the original. Cards are never edited in place by the agent that runs
them. The human author may edit any card at any time.

## 11.2 Must-pass sections are preserved verbatim

The Goal, Contract, Must-pass tests, Out of scope, Acceptance command, and Definition of Done
sections are load-bearing. None may be shortened, summarised, merged, or reflowed by the agent.

When the human trims a card before handing it over, the Must-pass tests section is the one part
that must survive intact. It is the only section that produces artifacts a later reviewer can
check. Prose can be reconstructed; a deleted test is invisible forever.

*Cause:* the `remedy`-on-failure requirement in `M1-T00` was deleted on intake, restored in
`M1-T00b`, and deleted again on intake of `M1-T00b`. Twice-lost requirements are not accidents,
they are a process defect.

## 11.3 Acceptance runs from a script file

Every card from `M1-T08c` onward ships `scripts/accept/<TASK_ID>.sh`. The Acceptance command
section contains exactly one line:

```bash
bash scripts/accept/<TASK_ID>.sh
```

Rules for acceptance scripts:

- Source `scripts/accept/_lib.sh`; use `expect_exit` and `expect_stdout`. Never assert with a
  bare `&&` chain.
- Do **not** `set -e`. Assertions that expect a non-zero exit are normal and must not abort the
  run.
- Use `set -uo pipefail`.
- Run `make check` as the first assertion and `accept_summary` as the last.
- Every temporary directory is removed on exit via `trap`.
- A unit test must run `bash -n` over every file in `scripts/accept/`, so a syntactically broken
  acceptance script fails `make check`.

*Cause:* the acceptance blocks for `M1-T00b` and `M1-T08b` were pasted into a runner that
flattened newlines. The result parsed as `make check` followed by a list of unknown goals. Make
aborted, no `echo` ever ran, and not one of the nine expected exit codes was observed - while both
tasks were recorded as `done` with acceptance verified. The multi-line block was the defect;
single-argument invocation removes the failure mode entirely.

## 11.4 Guards must be able to fail

Before a regression guard is accepted, demonstrate that it fails against the state it is meant
to prevent. If a guard cannot be made to fail, it is decoration.

Specifically:

- Prefer **source-text assertions** over `hasattr` / attribute-name checks. A name check catches
  only the exact spelling you thought of.
- Prefer asserting over a **whole collection** (`assert MAPPING == {...}`) rather than key by key,
  so that additions are caught, not just changes.
- Assert on **artifacts** (files written, exit codes, manifest contents) rather than on the
  absence of an exception.

*Cause:* `M1-T08b`'s single-resolver guard asserted `not hasattr(config, "resolve_rom_repo")`. The
duplicate resolver in the codebase was named `get_rom_repo_path`, so the guard passed both before
and after the fix.

## 11.5 A scope error is fixed by narrowing, not by weakening

When a check turns out to be too strict for one caller, do **not** downgrade the check. Introduce
a named subset and let that caller require the subset.

*Cause:* `is_git_repo` is genuinely a hard requirement for reproducible pinning and a genuine
non-requirement for running `cpp`. The tempting fix was to make it soft, which would have silently
weakened the doctor for every caller. The correct fix is `PREPROCESS_REQUIRED` alongside
`PINNING_REQUIRED`, with `CHECK_SEVERITY` untouched.

Corollary: subsets are data, they live next to the thing they subset, and a test asserts that each
subset is contained in the parent and that its members carry the expected severity.

## 11.6 Cross-task regressions are the reviewer's first question

When a task changes a shared entry point, the Definition of Done must include re-running the
acceptance command of every earlier task that uses it.

`M1-T08b` changed `preprocess_rom.py`, which `M1-T08` had already accepted. `M1-T08`'s acceptance
command was never re-run, so a `done` task quietly stopped working. `make check` stayed green
because the unit tests had been migrated to a different fixture in the same commit.

Green tests after a shared-entry-point change prove less than they appear to. Ask which earlier
acceptance script still passes.

## 11.7 Enforcement

`scripts/hooks/no_card_self_edit.py` runs at the `commit-msg` stage. It extracts the task id from
the `[M<n>-T<id>]` tag in the commit message and rejects the commit if the staged file list
includes `docs/tasks/<that id>.md`.

Add to `.pre-commit-config.yaml`:

```yaml
  - repo: local
    hooks:
      - id: no-card-self-edit
        name: task cards are immutable during their own task
        entry: python3 scripts/hooks/no_card_self_edit.py
        language: system
        stages: [commit-msg]
```

The hook is deliberately narrow. It cannot detect a card trimmed before the branch was created,
which remains a human responsibility under §11.2.
