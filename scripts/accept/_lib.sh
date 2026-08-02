#!/usr/bin/env bash
# scripts/accept/_lib.sh
#
# Shared assertion helpers for task acceptance scripts.
#
# Deliberately does NOT `set -e`: several assertions expect a non-zero exit code,
# and `set -e` would abort the run before the summary is printed.
#
# Usage:
#   source "$(dirname "$0")/_lib.sh"
#   expect_exit 0 make_check make check
#   expect_stdout "pinned=False" manifest_unpinned python3 -c '...'
#   accept_summary

set -uo pipefail

_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [ -d "$_REPO_ROOT/.venv/bin" ]; then
    export PATH="$_REPO_ROOT/.venv/bin:$PATH"
fi
if [ -x "$_REPO_ROOT/.venv/bin/python3" ]; then
    PY="$_REPO_ROOT/.venv/bin/python3"
else
    PY="$(python3 -c 'import sys; print(sys.executable)' 2>/dev/null || command -v python3)"
fi
export PY

_ACCEPT_PASS=0
_ACCEPT_FAIL=0
_ACCEPT_LOG="$(mktemp)"

_accept_cleanup() { rm -f "$_ACCEPT_LOG"; }
trap _accept_cleanup EXIT

_accept_record() {
    # $1 = ok|no, $2 = label, $3 = detail
    if [ "$1" = "ok" ]; then
        _ACCEPT_PASS=$((_ACCEPT_PASS + 1))
        printf 'PASS  %-28s %s\n' "$2" "$3"
    else
        _ACCEPT_FAIL=$((_ACCEPT_FAIL + 1))
        printf 'FAIL  %-28s %s\n' "$2" "$3"
    fi
}

# expect_exit <want> <label> <cmd...>
expect_exit() {
    local want="$1"; shift
    local label="$1"; shift
    "$@" >"$_ACCEPT_LOG" 2>&1
    local got=$?
    if [ "$got" -eq "$want" ]; then
        _accept_record ok "$label" "exit=$got"
    else
        _accept_record no "$label" "want_exit=$want got_exit=$got"
        sed 's/^/      | /' "$_ACCEPT_LOG" | tail -n 20
    fi
}

# expect_stdout <substring> <label> <cmd...>
# Asserts the substring appears in combined stdout+stderr. Exit code is ignored.
expect_stdout() {
    local want="$1"; shift
    local label="$1"; shift
    "$@" >"$_ACCEPT_LOG" 2>&1
    if grep -qF -- "$want" "$_ACCEPT_LOG"; then
        _accept_record ok "$label" "found: $want"
    else
        _accept_record no "$label" "missing: $want"
        sed 's/^/      | /' "$_ACCEPT_LOG" | tail -n 20
    fi
}

# expect_no_stdout <substring> <label> <cmd...>
expect_no_stdout() {
    local unwanted="$1"; shift
    local label="$1"; shift
    "$@" >"$_ACCEPT_LOG" 2>&1
    if grep -qF -- "$unwanted" "$_ACCEPT_LOG"; then
        _accept_record no "$label" "unexpectedly found: $unwanted"
    else
        _accept_record ok "$label" "absent: $unwanted"
    fi
}

accept_summary() {
    local expected="${1:-0}"
    local total=$((_ACCEPT_PASS + _ACCEPT_FAIL))
    printf -- '----------------------------------------------------------\n'
    printf 'acceptance: %d/%d passed, %d failed\n' "$_ACCEPT_PASS" "$total" "$_ACCEPT_FAIL"
    if [ "$expected" -gt 0 ] && [ "$_ACCEPT_PASS" -ne "$expected" ]; then
        printf 'FAIL  expected %d passed checks, but got %d\n' "$expected" "$_ACCEPT_PASS"
        return 1
    fi
    if [ "$_ACCEPT_FAIL" -ne 0 ]; then
        return 1
    fi
    return 0
}
