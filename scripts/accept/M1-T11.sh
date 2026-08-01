#!/usr/bin/env bash
# Acceptance for M1-T11 - species ingest plus the T10b carry-over corrections.
# Run from the repository root:  bash scripts/accept/M1-T11.sh
#
# Never use `set -e`: several assertions expect a non-zero exit code, and the
# summary must always print. The data probes live in M1-T11_checks.py so that
# the synthetic C fixtures are lint- and type-checked rather than buried in
# shell strings.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/accept/_lib.sh
source "${HERE}/_lib.sh"

PY="python3"
PROBE="scripts/accept/M1-T11_checks.py"

# ---------------------------------------------------------------- preamble --

expect_exit 0 make_gate make gate

expect_no_stdout "reformatted" ruff_paths_agree \
  "${PY}" -m pre_commit run --all-files

# ---------------------------------------------------------- Step 0 landed ---

expect_exit 0 card_present test -f docs/tasks/M1-T11.md

expect_stdout "ok" card_is_protocol_tagged \
  bash -c 'git log --format=%s -1 -- docs/tasks/M1-T11.md | grep -qF "[protocol]" && echo ok'

expect_stdout "11.12" frozen_scripts_documented \
  bash -c 'grep -oF "11.12" EXECUTION_PROTOCOL.md | head -n1'

expect_stdout "ff-only" section_2_amended \
  bash -c 'grep -oF "ff-only" EXECUTION_PROTOCOL.md | head -n1'

expect_exit 0 review_bundle_script_present test -f scripts/review_bundle.sh

expect_stdout "review-bundle" review_bundle_target \
  bash -c 'grep -oF "review-bundle" Makefile | head -n1'

# ------------------------------------------------------------- hygiene ------

expect_exit 1 no_eval_in_src \
  grep -rnF -e "eval(" -e "exec(" -e "literal_eval" -e "compile(" \
    src/npc_planner/ingest/species.py

# --------------------------------------------------------------- species ----

expect_stdout "skarmory=65|80|140|40|70|70|TYPE_STEEL,TYPE_FLYING|ABILITY_WEAK_ARMOR|ABILITY_KEEN_EYE" \
  skarmory_record "${PY}" "${PROBE}" skarmory

expect_stdout "invariants=True" species_invariants "${PY}" "${PROBE}" invariants

expect_stdout "ordering=True" sorted_and_deterministic "${PY}" "${PROBE}" ordering

expect_stdout "provenance=True" provenance_pinned "${PY}" "${PROBE}" provenance

# ------------------------------------------------------- coverage guard -----

expect_stdout "uncovered=()" coverage_clean "${PY}" "${PROBE}" coverage-clean

# The guard must be able to fail. If this prints detects=False it is decorative
# and the clean result above means nothing.
expect_stdout "detects=True" coverage_detects_unknown_key \
  "${PY}" "${PROBE}" coverage-detects

expect_stdout "ignored_pinned=True" ignored_fields_pinned \
  "${PY}" "${PROBE}" ignored-pinned

# ------------------------------------------------------ refusal to guess ----

# Missing stat, missing types, duplicate key - all three must raise, never
# default to zero or last-one-wins.
expect_stdout "refusals=True,True,True" refuses_to_guess \
  "${PY}" "${PROBE}" refusals

expect_stdout "monotype=1/2" monotype_normalised "${PY}" "${PROBE}" monotype

expect_stdout "string_only=True" parse_needs_no_filesystem \
  "${PY}" "${PROBE}" string-only

# Not an assertion - the three numbers the card asks you to report.
expect_stdout "counts=" reported_counts "${PY}" "${PROBE}" counts

# ---------------------------------------------------- ledger / done-tag -----

expect_stdout "unparsable=()" every_ledger_row_parses \
  "${PY}" scripts/hooks/task_id_required.py --list-unparsable-rows

TMPMSG="$(mktemp)"
trap 'rm -f "${TMPMSG}"' EXIT

printf '%s\n' "feat(ingest): species   [M1-T99z]" > "${TMPMSG}"
expect_exit 0 open_tag_accepted \
  "${PY}" scripts/hooks/task_id_required.py "${TMPMSG}"

# This is the check that was silently passing in T10b.
printf '%s\n' "fix(ingest): reuse a finished tag   [M1-T10b]" > "${TMPMSG}"
expect_exit 1 done_tag_t10b_now_rejected \
  "${PY}" scripts/hooks/task_id_required.py "${TMPMSG}"

printf '%s\n' "fix(ingest): unknown task   [M1-T99z]" > "${TMPMSG}"
expect_exit 0 unknown_tag_fails_open \
  "${PY}" scripts/hooks/task_id_required.py "${TMPMSG}"

# Failing open is allowed. Failing open silently is not.
printf '%s\n' "fix(ingest): unknown task   [M1-T99z]" > "${TMPMSG}"
expect_stdout "done-tag check skipped" fail_open_is_audible \
  "${PY}" scripts/hooks/task_id_required.py "${TMPMSG}"

printf '%s\n' "chore: no tag at all" > "${TMPMSG}"
expect_exit 1 untagged_still_rejected \
  "${PY}" scripts/hooks/task_id_required.py "${TMPMSG}"

# T10b's frozen acceptance script, corrected here under 11.12.
expect_stdout "M1-T99z" t10b_script_retargeted \
  bash -c 'grep -oF "M1-T99z" scripts/accept/M1-T10b.sh | head -n1'

# ---------------------------------------------------------------- audit -----

expect_stdout "17 with violations" audit_no_new_violations \
  "${PY}" scripts/audit_commits.py --range milestone/M1

# --------------------------------------------------------------- suites -----

expect_exit 0 species_tests "${PY}" -m pytest tests/unit/test_species_ingest.py -q
expect_exit 0 hook_tests "${PY}" -m pytest tests/unit/test_hooks.py -q
expect_exit 0 rom_config_tests "${PY}" -m pytest tests/unit/test_rom_config.py -q

# ----------------------------------------------------------- card intact ----

expect_no_stdout "M1-T11.md" card_unmodified \
  git diff --name-only milestone/M1...HEAD -- docs/tasks/

expect_stdout "ok" accept_scripts_parse \
  bash -c 'for f in scripts/accept/*.sh; do bash -n "$f" || exit 1; done; echo ok'

accept_summary
