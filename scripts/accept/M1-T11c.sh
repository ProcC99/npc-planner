#!/usr/bin/env bash
# Acceptance for M1-T11c — fixes T11c probe tautology & uses is_task_done_in_ledger_head.
# Run from repository root:  bash scripts/accept/M1-T11c.sh
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/accept/_lib.sh
source "${HERE}/_lib.sh"

PY="python3"
PROBE="scripts/accept/M1-T11c_checks.py"

# --------------------------------------------------------------- card ----

expect_exit 0 card_present test -f docs/tasks/M1-T11c.md

expect_stdout "11.13" self_gating_rule_documented \
  bash -c 'grep -oF "11.13" EXECUTION_PROTOCOL.md | head -n1'

expect_stdout "unsafe-fixes" unsafe_fixes_prohibited \
  bash -c 'grep -oF "unsafe-fixes" EXECUTION_PROTOCOL.md | head -n1'

# ------------------------------------------------------------- Part A ------

expect_stdout "ci_scope=True" ci_scope_reverted \
  "${PY}" "${PROBE}" ci-scope

expect_stdout "guards_excluded=True" ci_scope_excludes_guards \
  "${PY}" "${PROBE}" ci-scope-excludes-guards

expect_stdout "guard_paths=True" guard_paths_declared \
  "${PY}" "${PROBE}" guard-paths

TMPMSG="$(mktemp)"
trap 'rm -f "${TMPMSG}"' EXIT

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

printf '%s\n' "fix(ingest): guard work   [M1-T11c]" > "${TMPMSG}"
expect_exit 0 task_tag_may_touch_hooks \
  "${PY}" scripts/hooks/files_within_allowlist.py "${TMPMSG}" \
    --files scripts/hooks/task_id_required.py

expect_stdout "no_sha_conjunct=True" done_predicate_status_only \
  "${PY}" "${PROBE}" done-predicate

expect_stdout "17 with violations" audit_flags_ci_widening \
  "${PY}" scripts/audit_commits.py --range milestone/M1

expect_stdout "5124036" audit_names_the_widening \
  "${PY}" scripts/audit_commits.py --range milestone/M1

# ------------------------------------------------------------- Part B ------

expect_stdout "uncovered=()" coverage_clean \
  "${PY}" "${PROBE}" coverage-clean

expect_stdout "detects=True" coverage_detects_from_source \
  "${PY}" "${PROBE}" coverage-detects

expect_stdout "not_fatal=True" unknown_key_is_a_finding_not_a_crash \
  "${PY}" "${PROBE}" unknown-key-not-fatal

expect_stdout "mapped_fields=True" mapped_fields_declared \
  "${PY}" "${PROBE}" mapped-fields

expect_stdout "species_name=Skarmory" species_name_captured \
  "${PY}" "${PROBE}" species-name

expect_stdout "no_id_fallback=True" no_species_id_fallback \
  "${PY}" "${PROBE}" no-id-fallback

expect_stdout "name_required=True,True" missing_or_empty_name_raises \
  "${PY}" "${PROBE}" name-required

expect_stdout "natdex=" national_dex_resolved \
  "${PY}" "${PROBE}" national-dex

expect_stdout "ignored_empty=True" ignored_fields_emptied \
  "${PY}" "${PROBE}" ignored-empty

expect_stdout "keys_seen:" counts_reports_keys_seen \
  "${PY}" "${PROBE}" counts

# ------------------------------------------------------ Part C regression ---

expect_exit 0 t11b_harness_still_passes bash scripts/accept/M1-T11b.sh

expect_exit 0 species_tests \
  "${PY}" -m pytest tests/unit/test_species_ingest.py -q
expect_exit 0 hook_tests "${PY}" -m pytest tests/unit/test_hooks.py -q
expect_exit 0 audit_tests "${PY}" -m pytest tests/unit/test_audit_commits.py -q

# ----------------------------------------------------------- card intact ----

CARD_COMMIT="$(git log --reverse --format=%H milestone/M1 -- docs/tasks/M1-T11c.md | head -1)"
expect_no_stdout "M1-T11c.md" card_unmodified_since \
  bash -c 'git diff --name-only '"${CARD_COMMIT}"'..HEAD -- docs/tasks/M1-T11c.md'

expect_exit 0 card_not_touched_after_branch \
  bash -c '[ "$(git rev-list --count "$(git merge-base milestone/M1 HEAD)"..HEAD -- docs/tasks/M1-T11c.md)" = "0" ]'

expect_stdout "ok" accept_scripts_parse \
  bash -c 'for f in scripts/accept/*.sh; do bash -n "$f" || exit 1; done; echo ok'

accept_summary 30
