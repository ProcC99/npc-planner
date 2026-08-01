#!/usr/bin/env bash
# scripts/accept/M1-T08.sh
#
# Backfilled acceptance for M1-T08 (ROM layout probe + cpp preprocessing harness).
#
# M1-T08 was accepted with an inline multi-line command that was never successfully
# executed, and its behaviour has since been changed twice, by M1-T08b and M1-T08c.
# Protocol Amendment 11.6: a shared entry point that changes must have every earlier
# acceptance re-run.
#
# Run as exactly one argument:   bash scripts/accept/M1-T08.sh

set -uo pipefail
cd "$(dirname "$0")/../.." || exit 1
# shellcheck source=scripts/accept/_lib.sh
source "scripts/accept/_lib.sh"

FAKE_ROM="tests/fixtures/fake_rom"
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT

# ------------------------------------------------------- probe the layout
expect_stdout "expansion_1_9_plus" layout_id python3 -c "
import pathlib
from npc_planner.ingest.rom_probe import probe_layout
layout = probe_layout(pathlib.Path('$FAKE_ROM'))
print(layout.layout_id)
"

expect_stdout "trainers_format=party" trainers_format python3 -c "
import pathlib
from npc_planner.ingest.rom_probe import probe_layout
layout = probe_layout(pathlib.Path('$FAKE_ROM'))
print('trainers_format=' + layout.trainers_format)
"

# ------------------------------------------------------------ preprocess
expect_exit 0 preprocess \
    python3 scripts/preprocess_rom.py --repo "$FAKE_ROM" --output "$OUT"

# The count is derived from RomLayout, never written as a literal.
# See M1-T08d: the original acceptance asserted 5 with nothing to derive it from.
expect_stdout "count_matches_layout=ok" manifest_count python3 -c "
import json, pathlib
from npc_planner.ingest.rom_probe import probe_layout
layout = probe_layout(pathlib.Path('$FAKE_ROM'))
expected = len(layout.preprocessable_paths())
man = json.loads(pathlib.Path('$OUT/ROM_MANIFEST.json').read_text())
got = len(man['preprocessed'])
assert got == expected, 'manifest has %d preprocessed, layout derives %d' % (got, expected)
print('count_matches_layout=ok')
"

expect_stdout "every_entry_hashed=ok" manifest_hashes python3 -c "
import json, pathlib
man = json.loads(pathlib.Path('$OUT/ROM_MANIFEST.json').read_text())
for name, sha in man['preprocessed'].items():
    assert isinstance(sha, str) and sha.startswith('sha256:') and len(sha) == 71, (name, sha)
print('every_entry_hashed=ok')
"

# The fake_rom fixture is not a git repository, so the build is unpinned (M1-T08c).
expect_stdout "pinned=False" manifest_unpinned python3 -c "
import json, pathlib
man = json.loads(pathlib.Path('$OUT/ROM_MANIFEST.json').read_text())
print('pinned=' + str(man['pinned']))
"

# ------------------------------- the gen-9 guard must have been stripped by cpp
expect_stdout "gen9_guard_absent=ok" gen9_guard python3 -c "
import pathlib
hits = [p.name for p in pathlib.Path('$OUT').glob('*.i')
        if 'GEN9_GUARD' in p.read_text(errors='ignore')]
assert not hits, 'GEN9_GUARD survived preprocessing in: %r' % hits
print('gen9_guard_absent=ok')
"

accept_summary
