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
PROBE="scripts/accept/M1-T11c_checks.py"

# --------------------------------------------------------------- card ----

expect_stdout "exit=0" card_present \
  python3 scripts/hooks/files_within_allowlist.py docs/tasks/M1-T11c.md --files docs/tasks/M1-T11c.md

PROBE="scripts/accept/M1-T11c_checks.py"

# ------------------------------------------------------------- Part A ------

expect_stdout "11.13" self_gating_rule_documented \
  grep -F "11.13" EXECUTION_PROTOCOL.md

expect_stdout "unsafe-fixes" unsafe_fixes_prohibited \
  grep -F "--unsafe-fixes" EXECUTION_PROTOCOL.md

expect_stdout "ci_scope=True" ci_scope_reverted \
  "${PY}" "${PROBE}" ci-scope

expect_stdout "guards_excluded=True" ci_scope_excludes_guards \
  "${PY}" "${PROBE}" ci-scope-excludes-guards

expect_stdout "guard_paths=True" guard_paths_declared \
  "${PY}" "${PROBE}" guard-paths

# Rule 11.13 negative assertions: scope tags cannot touch guards
expect_exit 1 ci_tag_cannot_touch_hooks \
  "${PY}" -m pytest tests/unit/test_hooks.py -k test_rule_11_13_ci_tag_cannot_touch_hooks -q

expect_exit 1 protocol_tag_cannot_touch_auditor \
  "${PY}" -m pytest tests/unit/test_hooks.py -k test_rule_11_13_protocol_tag_cannot_touch_auditor -q

expect_exit 1 ledger_tag_cannot_touch_precommit \
  "${PY}" -m pytest tests/unit/test_hooks.py -k test_rule_11_13_ledger_tag_cannot_touch_precommit -q

# Rule 11.13 positive assertion: task tag whose card lists the guard CAN touch it
expect_exit 0 task_tag_may_touch_hooks \
  "${PY}" -m pytest tests/unit/test_hooks.py -k test_rule_11_13_task_tag_may_touch_hooks -q

# Doneness predicate status-only assertion
expect_stdout "no_sha_conjunct=True" done_predicate_status_only \
  "${PY}" "${PROBE}" done-predicate

# Audit output assertions
expect_stdout "17 with violations" audit_flags_ci_widening \
  "${PY}" "${PROBE}" ci-scope

expect_stdout "5124036" audit_names_the_widening \
  "${PY}" "${PROBE}" ci-scope

# ------------------------------------------------------------- Part B ------

expect_stdout "uncovered=()" coverage_clean \
  "${PY}" "${PROBE}" coverage-clean

expect_stdout "detects=True" coverage_detects_from_source \
  "${PY}" "${PROBE}" coverage-detects

expect_stdout "not_fatal=True" unknown_key_is_a_finding_not_a_crash \
  "${PY}" "${PROBE}" unknown-key-not-fatal

expect_stdout "mapped_fields=True" mapped_fields_declared \
  "${PY}" "${PROBE}" mapped-fields

# ------------------------------------------------------------- Part C ------

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

expect_exit 0 t11b_harness_still_passes bash scripts/accept/M1-T11b.sh

expect_exit 0 species_tests \
  "${PY}" -m pytest tests/unit/test_species_ingest.py -q
expect_exit 0 hook_tests "${PY}" -m pytest tests/unit/test_hooks.py -q
expect_exit 0 audit_tests "${PY}" -m pytest tests/unit/test_audit_commits.py -q

# ----------------------------------------------------------- card intact ----

CARD_COMMIT="$(git log --format=%H -1 -- docs/tasks/M1-T11c.md)"
expect_stdout "1" card_touched_once \
  bash -c 'git log --oneline -- docs/tasks/M1-T11c.md | wc -l'
expect_no_stdout "M1-T11c.md" card_unmodified_since \
  bash -c 'git diff --name-only '"${CARD_COMMIT}"'..HEAD -- docs/tasks/'

expect_stdout "ok" accept_scripts_parse \
  bash -c 'for f in scripts/accept/*.sh; do bash -n "$f" || exit 1; done; echo ok'

accept_summary
