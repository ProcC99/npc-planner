#!/usr/bin/env bash
# Acceptance for M1-T12b — fixture fidelity, CExpr, COMPOUND_STRING name extraction,
# protocol §11.15/§11.16.
# Run from the repository root:  bash scripts/accept/M1-T12b.sh
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/accept/_lib.sh
source "${HERE}/_lib.sh"

PY="python3"
PROBE="scripts/accept/M1-T12b_checks.py"

# ---------------------------------------------------------------- preamble --

expect_exit 0 card_present test -f docs/tasks/M1-T12b.md

# ---------------------------------------------------- §11.15 / §11.16 ------

expect_stdout "11.15" rule_11_15_documented \
  grep -F "11.15" EXECUTION_PROTOCOL.md

expect_stdout "11.16" rule_11_16_documented \
  grep -F "11.16" EXECUTION_PROTOCOL.md

expect_stdout "evidence" rule_11_15_content \
  grep -i "evidence" EXECUTION_PROTOCOL.md

expect_stdout "faithful" rule_11_16_content \
  grep -i "faithful" EXECUTION_PROTOCOL.md

# ----------------------------------------------------- Item 1: fixture ------

expect_stdout "split_absent=True" split_removed_from_mapped \
  "${PY}" "${PROBE}" split-removed

expect_stdout "category=DAMAGE_CATEGORY_STATUS" toxic_category \
  "${PY}" "${PROBE}" toxic-category

expect_stdout "discriminates=True" will_o_wisp_name_discriminates \
  "${PY}" "${PROBE}" will-o-wisp-name

expect_stdout "correct=True" compound_string_name_extraction \
  "${PY}" "${PROBE}" compound-string-name

# ---------------------------------------------- Item 5: CExpr + dedup ------

expect_stdout "cexpr=True" cexpr_structural_classification \
  "${PY}" "${PROBE}" cexpr-structural

expect_stdout "type=str" single_ident_stays_str \
  "${PY}" "${PROBE}" cexpr-single-ident

expect_stdout "power_unevaluated=True" ternary_routes_to_unevaluated \
  "${PY}" "${PROBE}" ternary-unevaluated

expect_stdout "duplicate_key=detected" duplicate_key_detection \
  "${PY}" "${PROBE}" duplicate-key

expect_stdout "move_has=True" unevaluated_fields_present \
  "${PY}" "${PROBE}" unevaluated-fields

expect_stdout "species_has=True" species_unevaluated_present \
  "${PY}" "${PROBE}" unevaluated-fields

# --------------------------------------------------- Item 1: coverage ------

expect_stdout "uncovered=[]" coverage_audit_clean \
  "${PY}" "${PROBE}" coverage-audit

# --------------------------------------------------------- unit tests ------

expect_exit 0 cparse_expr_tests \
  "${PY}" -m pytest tests/unit/test_cparse_expr.py -q
expect_exit 0 moves_tests \
  "${PY}" -m pytest tests/unit/test_moves_ingest.py -q
expect_exit 0 species_tests \
  "${PY}" -m pytest tests/unit/test_species_ingest.py -q
expect_exit 0 audit_tests \
  "${PY}" -m pytest tests/unit/test_audit_commits.py -q

# ----------------------------------------------- Item 3: audit_commits ------

expect_stdout "401de73" card_mutation_in_audit \
  bash -c 'grep 401de73 scripts/audit_commits.py'

# ----------------------------------------------------------- card intact ----

CARD_COMMIT="$(git log --reverse --format=%H HEAD milestone/M1 -- docs/tasks/M1-T12b.md 2>/dev/null | head -1)"
expect_no_stdout "M1-T12b.md" card_unmodified_since \
  bash -c 'git diff --name-only '"${CARD_COMMIT}"'..HEAD -- docs/tasks/M1-T12b.md'

expect_stdout "ok" accept_scripts_parse \
  bash -c 'for f in scripts/accept/*.sh; do bash -n "$f" || exit 1; done; echo ok'

accept_summary 23
