#!/usr/bin/env bash
# Acceptance for M1-T08e. Run from the repository root:
#     bash scripts/accept/M1-T08e.sh
#
# Uses the shared harness from M1-T08c, which records failures and keeps going
# rather than aborting on the first one. Never set -e in this file.

set -uo pipefail
cd "$(dirname "$0")/../.." || exit 2
# shellcheck source=scripts/accept/_lib.sh
source scripts/accept/_lib.sh

# --- the gate itself -------------------------------------------------------

expect_exit 0 make_gate make gate

# make gate must not repair its own input; a --fix anywhere in the recipe means
# the style check can never fail.
expect_exit 1 gate_has_no_fix \
  bash -c 'sed -n "/^gate:/,/^$/p" Makefile | grep -q -- "--fix"'

expect_exit 1 check_has_no_fix \
  bash -c 'sed -n "/^check:/,/^$/p" Makefile | grep -q -- "--fix"'

# --- hooks must be installed, and their absence must be loud ---------------

expect_exit 0 hooks_installed python3 scripts/check_hooks_installed.py

expect_stdout "hooks-check" check_depends_on_hooks \
  bash -c 'grep -E "^check:" Makefile'

# In a bare temp repo with no hooks, the checker must fail and name a stage.
expect_exit 1 hooks_absent_detected bash -c '
  tmp=$(mktemp -d) || exit 9
  trap "rm -rf \"$tmp\"" EXIT
  root=$(pwd)
  git -C "$tmp" init -q
  cd "$tmp" && python3 "$root/scripts/check_hooks_installed.py"
'

# --- the loophole is closed ------------------------------------------------

# The exact M1-T08d subject that escaped the allowlist must now be rejected.
expect_exit 1 fixup_subject_rejected bash -c '
  msg=$(mktemp) || exit 9
  trap "rm -f \"$msg\"" EXIT
  printf "%s\n" "fixup! update task_id_required to support task letter suffixes" > "$msg"
  python3 scripts/hooks/task_id_required.py "$msg"
'

# A bare untagged subject is rejected.
expect_exit 1 untagged_rejected bash -c '
  msg=$(mktemp) || exit 9
  trap "rm -f \"$msg\"" EXIT
  printf "%s\n" "chore: tidy up" > "$msg"
  python3 scripts/hooks/task_id_required.py "$msg"
'

# Each of the three tags is accepted on its own.
for tag in "[M1-T08e]" "[ledger]" "[protocol]"; do
  label="tag_accepted_$(printf "%s" "$tag" | tr -d "[]" | tr "-" "_")"
  expect_exit 0 "$label" bash -c '
    msg=$(mktemp) || exit 9
    trap "rm -f \"$msg\"" EXIT
    printf "%s\n" "chore(ci): example   $1" > "$msg"
    python3 scripts/hooks/task_id_required.py "$msg"
  ' _ "$tag"
done

# Two tags at once is rejected.
expect_exit 1 double_tag_rejected bash -c '
  msg=$(mktemp) || exit 9
  trap "rm -f \"$msg\"" EXIT
  printf "%s\n" "chore(ci): example   [M1-T08e] [ledger]" > "$msg"
  python3 scripts/hooks/task_id_required.py "$msg"
'

# --- scope tags carry real file restrictions -------------------------------

expect_stdout "LEDGER_SCOPE" ledger_scope_present \
  grep -o "LEDGER_SCOPE" scripts/hooks/files_within_allowlist.py

expect_stdout "PROTOCOL_SCOPE" protocol_scope_present \
  grep -o "PROTOCOL_SCOPE" scripts/hooks/files_within_allowlist.py

# The HEAD-not-worktree property from M1-T08d must still hold. Weakening it
# while adding scope tags would defeat the whole hook (11.5).
expect_stdout "HEAD" head_read_preserved \
  bash -c 'grep -o "git show HEAD\|show\", \"HEAD" scripts/hooks/files_within_allowlist.py | head -1'

# --- both hooks are registered ---------------------------------------------

expect_stdout "files-within-allowlist" allowlist_hook_registered \
  bash -c 'grep -o "files-within-allowlist" .pre-commit-config.yaml | head -1'

expect_stdout "task-id-required" task_id_hook_registered \
  bash -c 'grep -oE "task.id.required" .pre-commit-config.yaml | head -1'

# --- the audit tool works --------------------------------------------------

expect_exit 0 audit_tool_runs bash -c 'python3 scripts/audit_commits.py --help >/dev/null'

# The audit must read cards from the audited commit, not from the tip.
expect_stdout "sha" audit_reads_from_commit \
  bash -c 'grep -o "f\"{sha}:{card_path}\"" scripts/audit_commits.py | head -1'

# --- tests exist and pass ---------------------------------------------------

expect_exit 0 hook_tests pytest tests/unit/test_hooks.py -q
expect_exit 0 audit_tests pytest tests/unit/test_audit_commits.py -q

# --- protocol text ----------------------------------------------------------

expect_stdout "ok" section_11_before_appendix bash -c '
  s=$(grep -n "^## 11\|^## Section 11" EXECUTION_PROTOCOL.md | head -1 | cut -d: -f1)
  a=$(grep -n "^## Appendix A" EXECUTION_PROTOCOL.md | head -1 | cut -d: -f1)
  if [ -n "$s" ] && [ -n "$a" ] && [ "$s" -lt "$a" ]; then echo "ordering=ok"; fi
'

expect_stdout "ok" amendment_is_stub bash -c '
  n=$(wc -l < docs/PROTOCOL_AMENDMENT_11.md)
  if [ "$n" -lt 20 ] && grep -q "Superseded" docs/PROTOCOL_AMENDMENT_11.md; then echo "stub=ok"; fi
'

expect_stdout "ok" no_verify_documented bash -c '
  if grep -q -- "--no-verify" EXECUTION_PROTOCOL.md; then echo "prohibition=ok"; fi
'

# --- every acceptance script still parses ----------------------------------

expect_stdout "ok" accept_scripts_parse bash -c '
  for f in scripts/accept/*.sh; do bash -n "$f" || exit 1; done
  echo "all_parse=ok"
'

accept_summary
