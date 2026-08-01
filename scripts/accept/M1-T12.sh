#!/usr/bin/env bash
# Acceptance for M1-T12 - moves extractor, symbolic_fields mapping, M1-T00z sentinel.
# Run from the repository root:  bash scripts/accept/M1-T12.sh
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/accept/_lib.sh
source "${HERE}/_lib.sh"

PY="python3"
PROBE="scripts/accept/M1-T12_checks.py"

# ---------------------------------------------------------------- preamble --

expect_exit 0 make_gate make gate

expect_no_stdout "reformatted" ruff_paths_agree \
  "${PY}" -m pre_commit run --all-files

expect_exit 0 card_present test -f docs/tasks/M1-T12.md

# ------------------------------------------------------------- Part A ------

expect_stdout "11.14" sentinel_rule_documented \
  grep -F "11.14" EXECUTION_PROTOCOL.md

expect_stdout "sentinel_todo=True" sentinel_present_in_ledger \
  "${PY}" "${PROBE}" sentinel-present

expect_stdout "ci_scope=True" ci_scope_reverted \
  "${PY}" "${PROBE}" ci-scope

expect_stdout "guards_excluded=True" ci_scope_excludes_guards \
  "${PY}" "${PROBE}" ci-scope-excludes-guards

expect_stdout "guard_paths=True" guard_paths_declared \
  "${PY}" "${PROBE}" guard-paths

TMPMSG="$(mktemp)"
trap 'rm -f "${TMPMSG}"' EXIT

# Rule 11.13 negative assertions
printf '%s\n' "chore(ci): touch a hook   [ci]" > "${TMPMSG}"
expect_exit 1 ci_tag_cannot_touch_hooks \
  "${PY}" scripts/hooks/files_within_allowlist.py "${TMPMSG}" \
    --files scripts/hooks/task_id_required.py

# Rule 11.13 positive assertion
printf '%s\n' "feat(ingest): moves extractor   [M1-T12]" > "${TMPMSG}"
expect_exit 0 task_tag_may_touch_hooks \
  "${PY}" scripts/hooks/files_within_allowlist.py "${TMPMSG}" \
    --files scripts/hooks/task_id_required.py

# Doneness predicate status-only assertion
expect_stdout "no_sha_conjunct=True placeholder=True" done_predicate_status_only \
  "${PY}" "${PROBE}" done-predicate

# Open tag accepted assertion
printf '%s\n' "feat(ingest): sentinel check   [M1-T00z]" > "${TMPMSG}"
expect_exit 0 open_tag_accepted \
  "${PY}" scripts/hooks/task_id_required.py "${TMPMSG}"

# ------------------------------------------------------------- Part B ------

expect_stdout "disjoint=True" symbolic_fields_disjoint \
  "${PY}" "${PROBE}" symbolic-disjoint

expect_stdout "moves_count=2 uncovered=()" moves_extracted \
  "${PY}" "${PROBE}" moves-extract

expect_stdout "natdex=symbol recorded=NATIONAL_DEX_SKARMORY" national_dex_resolved \
  "${PY}" "${PROBE}" national-dex

# ------------------------------------------------------ Part C regression ---

expect_stdout "counts=species:2 moves:2" counts_reports_keys \
  "${PY}" "${PROBE}" counts

expect_exit 0 t11c_harness_still_passes bash scripts/accept/M1-T11c.sh

expect_exit 0 species_tests \
  "${PY}" -m pytest tests/unit/test_species_ingest.py -q
expect_exit 0 moves_tests \
  "${PY}" -m pytest tests/unit/test_moves_ingest.py -q
expect_exit 0 hook_tests "${PY}" -m pytest tests/unit/test_hooks.py -q
expect_exit 0 audit_tests "${PY}" -m pytest tests/unit/test_audit_commits.py -q

# ----------------------------------------------------------- card intact ----

CARD_COMMIT="$(git log --format=%H -1 milestone/M1 -- docs/tasks/M1-T12.md)"
expect_no_stdout "M1-T12.md" card_unmodified_since \
  bash -c 'git diff --name-only '"${CARD_COMMIT}"'..HEAD -- docs/tasks/M1-T12.md'

expect_stdout "ok" accept_scripts_parse \
  bash -c 'for f in scripts/accept/*.sh; do bash -n "$f" || exit 1; done; echo ok'

accept_summary
