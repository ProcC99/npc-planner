#!/usr/bin/env bash
# scripts/accept/M1-T12e.sh
# Acceptance suite for M1-T12e: environment and suite integrity.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/accept/_lib.sh
source "${HERE}/_lib.sh"

PROBE="scripts/accept/M1-T12e_checks.py"

# ---------------------------------------------------------------- card ----

expect_exit 0 card_present \
  test -f docs/tasks/M1-T12e.md

# ----------------------------------------------------------- checks ----

expect_stdout "gate_yml_valid=True" ci_gate_hooks \
  "${PY}" "${PROBE}" gate-yml

expect_stdout "gitignore_valid=True" gitignore_expansion \
  "${PY}" "${PROBE}" gitignore

expect_stdout "in_tree_rejected=True" in_tree_rom_rejected \
  "${PY}" "${PROBE}" in-tree-rejection

# --------------------------------------------------- acceptance suites ----

expect_exit 0 suite_t11 \
  bash scripts/accept/M1-T11.sh

expect_exit 0 suite_t11b \
  bash scripts/accept/M1-T11b.sh

expect_exit 0 suite_t11c \
  bash scripts/accept/M1-T11c.sh

expect_exit 0 suite_t12b \
  bash scripts/accept/M1-T12b.sh

expect_exit 0 suite_t12d \
  bash scripts/accept/M1-T12d.sh

# ---------------------------------------------------------------- gate ----

expect_exit 0 make_gate \
  make gate

accept_summary 10
