#!/usr/bin/env bash
# Acceptance for M1-T11b - coverage re-sourcing, schema alignment, self-gating
# guards. Run from the repository root:  bash scripts/accept/M1-T11b.sh
#
# Never use `set -e`: several assertions expect a non-zero exit code, and the
# summary must always print.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/accept/_lib.sh
source "${HERE}/_lib.sh"

PY="python3"
PROBE="scripts/accept/M1-T11b_checks.py"

# ---------------------------------------------------------------- preamble --

expect_exit 0 make_gate make gate

expect_no_stdout "reformatted" ruff_paths_agree \
  "${PY}" -m pre_commit run --all-files

expect_exit 0 card_present test -f docs/tasks/M1-T11b.md

expect_stdout "11.13" self_gating_rule_documented \
  bash -c 'grep -oF "11.13" EXECUTION_PROTOCOL.md | head -n1'

expect_stdout "unsafe-fixes" unsafe_fixes_prohibited \
  bash -c 'grep -oF "unsafe-fixes" EXECUTION_PROTOCOL.md | head -n1'

# ---------------------------------------------------------- Part A guards ---

expect_stdout "ci_scope=True" ci_scope_reverted "${PY}" "${PROBE}" ci-scope

expect_stdout "guards_excluded=True" ci_scope_excludes_guards \
  "${PY}" "${PROBE}" ci-scope-excludes-guards

expect_stdout "guard_paths=True" guard_paths_declared \
  "${PY}" "${PROBE}" guard-paths

TMPMSG="$(mktemp)"
STAGED="$(mktemp)"
trap 'rm -f "${TMPMSG}" "${STAGED}"' EXIT

# A scope tag must not be able to reach a guard. Three tags, three guard paths.
printf '%s\n' "chore(ci): touch a hook   [ci]" > "${TMPMSG}"
expect_exit 1 ci_tag_cannot_touch_hooks \
  "${PY}" scripts/hooks/files_within_allowlist.py "${TMPMSG}" \
    --files scripts/hooks/task_id_required.py

printf '%s\n' "docs(protocol): touch the auditor   [protocol]" > "${TMPMSG}"
expect_exit 1 protocol_tag_cannot_touch_auditor \
  "${PY}" scripts/hooks/files_within_allowlist.py "${TMPMSG}" \
    --files scripts/audit_commits.py

printf '%s\n' "docs(ledger): touch pre-commit config   [ledger]" > "${TMPMSG}"
expect_exit 1 ledger_tag_cannot_touch_precommit \
  "${PY}" scripts/hooks/files_within_allowlist.py "${TMPMSG}" \
    --files .pre-commit-config.yaml

# The rule must not brick legitimate work: this card allowlists the hooks.
printf '%s\n' "fix(ingest): guard work   [M1-T11b]" > "${TMPMSG}"
expect_exit 0 task_tag_may_touch_hooks \
  "${PY}" scripts/hooks/files_within_allowlist.py "${TMPMSG}" \
    --files scripts/hooks/files_within_allowlist.py

expect_stdout "no_sha_conjunct=True" done_predicate_status_only \
  "${PY}" "${PROBE}" done-predicate

expect_stdout "17 with violations" audit_flags_ci_widening \
  "${PY}" scripts/audit_commits.py --range milestone/M1

expect_stdout "5124036" audit_names_the_widening \
  "${PY}" scripts/audit_commits.py --range milestone/M1

# -------------------------------------------------------- Part B coverage ---

expect_stdout "uncovered=()" coverage_clean "${PY}" "${PROBE}" coverage-clean

# The guard reads the source now, so a key the parser never recorded must still
# surface. If this prints detects=False the clean result above means nothing.
expect_stdout "detects=True" coverage_detects_from_source \
  "${PY}" "${PROBE}" coverage-detects

expect_stdout "not_fatal=True" unknown_key_is_a_finding_not_a_crash \
  "${PY}" "${PROBE}" unknown-key-not-fatal

expect_stdout "mapped_fields=True" mapped_fields_declared \
  "${PY}" "${PROBE}" mapped-fields

# --------------------------------------------------------- Part C schema ----

expect_stdout "species_name=Skarmory" species_name_captured \
  "${PY}" "${PROBE}" species-name

expect_stdout "no_id_fallback=True" no_species_id_fallback \
  "${PY}" "${PROBE}" no-id-fallback

expect_stdout "name_required=True,True" missing_or_empty_name_raises \
  "${PY}" "${PROBE}" name-required

# Reports which branch the fixture took; C3 asks you to state it in prose.
expect_stdout "natdex=" national_dex_resolved "${PY}" "${PROBE}" national-dex

expect_stdout "ignored_empty=True" ignored_fields_emptied \
  "${PY}" "${PROBE}" ignored-empty

# ------------------------------------------------------ Part D regression ---

expect_stdout "keys_seen:" counts_reports_keys_seen "${PY}" "${PROBE}" counts

expect_exit 0 t11_harness_still_passes bash scripts/accept/M1-T11.sh

expect_exit 0 species_tests \
  "${PY}" -m pytest tests/unit/test_species_ingest.py -q
expect_exit 0 hook_tests "${PY}" -m pytest tests/unit/test_hooks.py -q
expect_exit 0 audit_tests "${PY}" -m pytest tests/unit/test_audit_commits.py -q

# ----------------------------------------------------------- card intact ----

expect_no_stdout "M1-T11b.md" card_unmodified \
  git diff --name-only milestone/M1...HEAD -- docs/tasks/

expect_stdout "ok" accept_scripts_parse \
  bash -c 'for f in scripts/accept/*.sh; do bash -n "$f" || exit 1; done; echo ok'

accept_summary
