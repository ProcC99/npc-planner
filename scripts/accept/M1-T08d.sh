#!/usr/bin/env bash
# scripts/accept/M1-T08d.sh
#
# Acceptance for M1-T08d - allowlist enforcement, card commit order,
# derivable manifest count.
#
# Run as exactly one argument:   bash scripts/accept/M1-T08d.sh

set -uo pipefail
cd "$(dirname "$0")/../.." || exit 1
# shellcheck source=scripts/accept/_lib.sh
source "scripts/accept/_lib.sh"

# ---------------------------------------------------------------- gate
expect_exit 0 make_check make check

# ------------------------------- Amendment 11.6: re-run the earlier acceptance
expect_exit 0 t08_backfill bash scripts/accept/M1-T08.sh

# ------------------------------------------------- hook is actually registered
expect_stdout "files-within-allowlist" hook_registered cat .pre-commit-config.yaml

# ------------------------- Amendment 11.1 rev 2: cards are tracked in HEAD
expect_exit 0 card_t08c_tracked git cat-file -e HEAD:docs/tasks/M1-T08c.md
expect_exit 0 card_t08d_tracked git cat-file -e HEAD:docs/tasks/M1-T08d.md

# --------------------------------- the manifest count is derived, not literal
expect_stdout "count_matches_layout=ok" manifest_derivable python3 -c "
import json, pathlib, subprocess, sys, tempfile
from npc_planner.ingest.rom_probe import probe_layout, PREPROCESSABLE_FIELDS
from dataclasses import fields
names = {f.name for f in fields(probe_layout(pathlib.Path('tests/fixtures/fake_rom')))}
assert set(PREPROCESSABLE_FIELDS) <= names
assert 'wild_encounters_json' not in PREPROCESSABLE_FIELDS
assert 'trainers' not in PREPROCESSABLE_FIELDS
out = tempfile.mkdtemp()
subprocess.run([sys.executable, 'scripts/preprocess_rom.py',
                '--repo', 'tests/fixtures/fake_rom', '--output', out], check=True)
layout = probe_layout(pathlib.Path('tests/fixtures/fake_rom'))
man = json.loads((pathlib.Path(out) / 'ROM_MANIFEST.json').read_text())
assert len(man['preprocessed']) == len(layout.preprocessable_paths())
print('count_matches_layout=ok')
"

# ---------------------- no literal preprocessed count survives anywhere
expect_stdout "no_literal_counts=ok" no_literal_counts python3 -c "
import pathlib, re
pattern = re.compile(r'preprocessed..\\s*\\)?\\s*==\\s*[0-9]+')
bad = []
for root in ('tests', 'scripts'):
    for path in pathlib.Path(root).rglob('*'):
        if path.suffix not in ('.py', '.sh'):
            continue
        if pattern.search(path.read_text(errors='ignore')):
            bad.append(str(path))
assert not bad, 'literal preprocessed count in: %r' % bad
print('no_literal_counts=ok')
"

# ------------------------------------ the duplicated amendment became a stub
expect_stdout "stub=ok" amendment_stub python3 -c "
import pathlib
n = pathlib.Path('docs/PROTOCOL_AMENDMENT_11.md').stat().st_size
assert n < 400, 'still %d bytes, expected a stub' % n
print('stub=ok')
"

# --------------------------- section 11 now precedes Appendix A
expect_stdout "ordering=ok" section_11_before_appendix python3 -c "
import pathlib
lines = pathlib.Path('EXECUTION_PROTOCOL.md').read_text().splitlines()
sec = next(i for i, l in enumerate(lines) if l.startswith('## 11.'))
app = next(i for i, l in enumerate(lines) if l.startswith('## Appendix A'))
assert sec < app, 'section 11 at %d, appendix at %d' % (sec, app)
print('ordering=ok')
"

# ------------------- every acceptance script parses, discovered dynamically
expect_stdout "all_parse=ok" accept_scripts_parse bash -c '
rc=0
for f in scripts/accept/*.sh; do
    bash -n "$f" || rc=1
done
[ "$rc" -eq 0 ] && echo all_parse=ok
'

accept_summary
