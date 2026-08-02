#!/usr/bin/env bash
# scripts/accept/M1-T12f.sh
# Acceptance suite for M1-T12f: bookkeeping, tag reconciliation, protocol & successor tracking.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/accept/_lib.sh
source "${HERE}/_lib.sh"

PROBE="scripts/accept/M1-T12f_checks.py"

# ---------------------------------------------------------------- card ----

expect_exit 0 card_present \
  test -f docs/tasks/M1-T12f.md

# ----------------------------------------------------------- checks ----

expect_stdout "correct=True" tag_t12d_retagged \
  "${PY}" "${PROBE}" tag-t12d

expect_stdout "11_17_present=True" protocol_11_17 \
  "${PY}" "${PROBE}" protocol-11-17

expect_stdout "t12g_todo_present=True" ledger_t12g_todo \
  "${PY}" "${PROBE}" ledger-t12g

expect_exit 0 audit_commits_first_parent \
  "${PY}" scripts/audit_commits.py --range d5dbc28..HEAD --first-parent

# ---------------------------------------------------------------- gate ----

expect_exit 0 make_gate \
  make gate

accept_summary 6
