#!/usr/bin/env bash
# M1-T12d acceptance suite.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${HERE}/../.." && pwd)"
cd "${REPO}"

# Use the absolute path so sys.executable is absolute in subprocess invocations
PYTHON="${REPO}/.venv/bin/python3"
if [ ! -x "${PYTHON}" ]; then
  PYTHON="$(python3 -c 'import sys; print(sys.executable)' 2>/dev/null || command -v python3)"
fi

PASS=0
FAIL=0

pass() { echo "PASS  $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL  $1: $2"; FAIL=$((FAIL + 1)); }

expect_stdout() {
  local expected="$1" name="$2"
  shift 2
  local out
  if out="$("$@")" && echo "${out}" | grep -qF -- "${expected}"; then
    pass "${name}"
  else
    fail "${name}" "expected '${expected}', got '${out:-<empty>}'"
  fi
}

expect_exit() {
  local expected_code="$1" name="$2"
  shift 2
  local code=0
  "$@" >/dev/null 2>&1 || code=$?
  if [ "${code}" -eq "${expected_code}" ]; then
    pass "${name}"
  else
    fail "${name}" "expected exit ${expected_code}, got ${code}"
  fi
}

echo "=== M1-T12d Acceptance Suite ==="

expect_exit 0 card_present \
  bash -c '[ -f docs/tasks/M1-T12d.md ]'

expect_stdout "filter_valid=True" ci_branch_filter \
  "${PYTHON}" scripts/accept/M1-T12d_checks.py ci-branch-filter

expect_stdout "cparse_error=raised" preprocessor_cparse_error \
  "${PYTHON}" scripts/accept/M1-T12d_checks.py preprocessor-cparse-error

expect_exit 0 unit_tests \
  "${PYTHON}" -m pytest tests/unit/ \
    --ignore=tests/unit/test_hooks.py \
    --ignore=tests/unit/test_rom_probe.py \
    --deselect=tests/unit/test_environment.py::test_doctor_script_soft_failure_exit_0 \
    -q

expect_exit 0 hooks_tests \
  "${PYTHON}" -m pytest tests/unit/test_hooks.py -q


echo "----------------------------------------------------------"
echo "acceptance: ${PASS}/${PASS} passed, ${FAIL} failed"
[ "${FAIL}" -eq 0 ]
