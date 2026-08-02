#!/usr/bin/env bash
# Acceptance suite for M1-T12g - suite count reconciliation, M1-T10b re-integration & ratchet audit baseline
# Run from repository root: bash scripts/accept/M1-T12g.sh
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/accept/_lib.sh
source "${HERE}/_lib.sh"

PROBE="scripts/accept/M1-T12g_checks.py"

expect_exit 0 card_present test -f docs/tasks/M1-T12g.md

expect_stdout "t10b_present=True" gate_yml_t10b \
  "${PY}" "${PROBE}" t10b-present

expect_stdout "d5dbc28_documented=True" audit_baseline_documented \
  "${PY}" "${PROBE}" audit-baseline

expect_exit 0 audit_commits_first_parent \
  "${PY}" scripts/audit_commits.py --range d5dbc28..HEAD --first-parent

expect_exit 0 make_gate make gate

accept_summary 5
