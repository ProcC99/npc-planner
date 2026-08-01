#!/usr/bin/env bash
# scripts/accept/M1-T08c.sh
#
# Acceptance for M1-T08c - scope the preprocess preflight, git-optional pinning.
#
# Run as exactly one argument:   bash scripts/accept/M1-T08c.sh

set -uo pipefail
cd "$(dirname "$0")/../.." || exit 1
# shellcheck source=scripts/accept/_lib.sh
source "scripts/accept/_lib.sh"

FAKE_ROM="tests/fixtures/fake_rom"

OUT_OK="$(mktemp -d)"
OUT_BAD="$(mktemp -d)/never_created"
NON_EXPANSION="$(mktemp -d)"
git -C "$NON_EXPANSION" init -q

cleanup() { rm -rf "$OUT_OK" "$(dirname "$OUT_BAD")" "$NON_EXPANSION"; }
trap cleanup EXIT

# ---------------------------------------------------------------- gate
expect_exit 0 make_check make check

# ------------------------------------------------- subsets are well formed
expect_stdout "3 2" subsets_valid python3 -c "
from npc_planner.environment import PREPROCESS_REQUIRED, PINNING_REQUIRED, CHECK_SEVERITY
assert set(PREPROCESS_REQUIRED) <= set(CHECK_SEVERITY)
assert set(PINNING_REQUIRED) <= set(CHECK_SEVERITY)
assert all(CHECK_SEVERITY[n] == 'hard' for n in PREPROCESS_REQUIRED + PINNING_REQUIRED)
print(len(PREPROCESS_REQUIRED), len(PINNING_REQUIRED))
"

# --------------------------------- the exact regression this task fixes
expect_stdout "is_git_repo_absent=ok" no_git_in_preprocess python3 -c "
from npc_planner.environment import PREPROCESS_REQUIRED
assert 'is_git_repo' not in PREPROCESS_REQUIRED, PREPROCESS_REQUIRED
print('is_git_repo_absent=ok')
"

# ------------------------- preprocessing a non-git expansion tree succeeds
expect_exit 0 preprocess_fake_rom \
    python3 scripts/preprocess_rom.py --repo "$FAKE_ROM" --output "$OUT_OK"

expect_stdout "unpinned" warns_unpinned \
    python3 scripts/preprocess_rom.py --repo "$FAKE_ROM" --output "$OUT_OK"

expect_stdout "pinned=False" manifest_unpinned python3 -c "
import json, sys, pathlib
man = json.loads(pathlib.Path('$OUT_OK/ROM_MANIFEST.json').read_text())
print('pinned=' + str(man['pinned']))
"

expect_stdout "i_files_present=ok" emits_i_files python3 -c "
import pathlib
n = len(list(pathlib.Path('$OUT_OK').glob('*.i')))
assert n > 0, 'no .i files emitted'
print('i_files_present=ok')
"

# ------------------------------- a non-expansion tree is still refused
expect_exit 3 preprocess_non_expansion \
    python3 scripts/preprocess_rom.py --repo "$NON_EXPANSION" --output "$OUT_BAD"

expect_stdout "files_written=0" no_output_written python3 -c "
import pathlib
p = pathlib.Path('$OUT_BAD')
print('files_written=' + str(len(list(p.iterdir())) if p.exists() else 0))
"

# ------------------------------------------- read_pin degrades gracefully
expect_stdout "unpinned_pin=ok" read_pin_non_git python3 -c "
import pathlib
from npc_planner.ingest.rom_probe import read_pin
pin = read_pin(pathlib.Path('$FAKE_ROM'))
assert pin.pinned is False
assert pin.hack_sha is None
assert pin.hack_dirty is False
assert pin.expansion_version == 'unpinned'
print('unpinned_pin=ok')
"

# ------------------------------------ the guard that actually guards
expect_stdout "config_clean=ok" config_clean python3 -c "
import pathlib
src = pathlib.Path('src/npc_planner/config.py').read_text()
for bad in ('NPC_PLANNER_ROM_REPO', 'pokeemerald-expansion', 'get_rom_repo_path', 'resolve_rom_repo'):
    assert bad not in src, 'forbidden token in config.py: ' + bad
print('config_clean=ok')
"

expect_stdout "probe_isolated=ok" probe_no_env_import python3 -c "
import pathlib
src = pathlib.Path('src/npc_planner/ingest/rom_probe.py').read_text()
assert 'npc_planner.environment' not in src
assert 'from ..environment' not in src
print('probe_isolated=ok')
"

# ------------- the doctor is UNCHANGED: is_git_repo is still hard for it
expect_exit 1 doctor_unchanged \
    python3 scripts/doctor.py --repo "$FAKE_ROM"

# ----------------------------------------- acceptance scripts parse
expect_exit 0 accept_scripts_parse bash -n scripts/accept/_lib.sh
expect_exit 0 self_parses bash -n scripts/accept/M1-T08c.sh

accept_summary
