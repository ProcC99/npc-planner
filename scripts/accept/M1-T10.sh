#!/usr/bin/env bash
# Acceptance for M1-T10. Run from the repository root:
#     bash scripts/accept/M1-T10.sh
#
# Uses the shared harness from M1-T08c: records failures and keeps going.
# Never set -e in this file.

set -uo pipefail
cd "$(dirname "$0")/../.." || exit 2
# shellcheck source=scripts/accept/_lib.sh
source scripts/accept/_lib.sh

FAKE=tests/fixtures/fake_rom

# --- the gate --------------------------------------------------------------

expect_exit 0 make_gate make gate

# Step 0a: the two ruff paths must agree. If pre-commit reformats anything
# straight after a clean gate, the formatter fight is still live.
expect_exit 1 ruff_paths_agree \
  bash -c 'python3 -m pre_commit run --all-files 2>&1 | grep -q "file reformatted"'

# --- no code execution on ROM input ----------------------------------------

for bad in eval exec ast.literal_eval compile; do
  label="no_$(printf "%s" "$bad" | tr "." "_")"
  expect_exit 1 "$label" \
    bash -c 'grep -rEn "(^|[^A-Za-z_.])'"$bad"'[[:space:]]*\(" src/npc_planner --include="*.py"'
done

# --- values read out of the fixture ----------------------------------------

read_cfg() {
  PYTHONPATH=. python3 - "$@" <<'PY'
import json
import sys
from pathlib import Path

from npc_planner.ingest.rom_probe import probe_layout
from npc_planner.ingest.rom_config import read_rom_config

layout = probe_layout(Path("tests/fixtures/fake_rom"))
cfg = read_rom_config(layout)
what = sys.argv[1]
if what == "dump":
    print(
        json.dumps(
            {
                "limits": dict(cfg.limits),
                "ai_flags": dict(cfg.ai_flags),
                "difficulties": dict(cfg.difficulties),
                "battle": dict(cfg.battle),
                "species": dict(cfg.species),
                "unevaluated": [u.symbol for u in cfg.unevaluated],
            },
            indent=2,
            sort_keys=True,
            default=str,
        )
    )
else:
    section, key = what.split(":", 1)
    print(getattr(cfg, section)[key])
PY
}

expect_stdout "6"    party_size          bash -c "$(declare -f read_cfg); read_cfg limits:PARTY_SIZE"
expect_stdout "4"    max_mon_moves       bash -c "$(declare -f read_cfg); read_cfg limits:MAX_MON_MOVES"
expect_stdout "14"   hex_literal         bash -c "$(declare -f read_cfg); read_cfg limits:NUM_STORAGE_BOXES"
expect_stdout "4"    trainer_items       bash -c "$(declare -f read_cfg); read_cfg limits:MAX_TRAINER_ITEMS"
expect_stdout "1"    ai_flag_first       bash -c "$(declare -f read_cfg); read_cfg ai_flags:AI_FLAG_CHECK_BAD_MOVE"
expect_stdout "8192" ai_flag_shift_13    bash -c "$(declare -f read_cfg); read_cfg ai_flags:AI_FLAG_SMART_SWITCHING"
expect_stdout "7"    ai_flag_composite   bash -c "$(declare -f read_cfg); read_cfg ai_flags:AI_FLAG_BASIC_TRAINER"
expect_stdout "1"    difficulty_default  bash -c "$(declare -f read_cfg); read_cfg difficulties:DIFFICULTY_DEFAULT"

# The unevaluable flag must be reported, and must NOT have leaked into ai_flags
# with a fabricated value.
expect_stdout "AI_FLAG_RUNTIME_TUNED" unevaluated_reported \
  bash -c "$(declare -f read_cfg); read_cfg dump | grep -o AI_FLAG_RUNTIME_TUNED | head -1"

expect_exit 1 unevaluated_not_in_flags \
  bash -c "$(declare -f read_cfg); read_cfg dump | python3 -c '
import json,sys
d=json.load(sys.stdin)
sys.exit(0 if \"AI_FLAG_RUNTIME_TUNED\" in d[\"ai_flags\"] else 1)
'"

# --- determinism -----------------------------------------------------------

expect_stdout "identical" deterministic \
  bash -c "$(declare -f read_cfg); a=\$(read_cfg dump); b=\$(read_cfg dump); [ \"\$a\" = \"\$b\" ] && echo identical"

# --- fixture manifest, no literal counts -----------------------------------

expect_exit 1 no_literal_count_in_fixture_test \
  bash -c 'grep -nE "==[[:space:]]*[0-9]+" tests/unit/test_fake_rom_fixture.py'

for h in battle_ai difficulty global battle tms_hms; do
  expect_exit 0 "fixture_has_$h" test -f "$FAKE/include/constants/$h.h"
done

# config/ and constants/ must not be conflated.
expect_stdout "config_constants" layout_field_present \
  bash -c 'grep -o "config_constants" src/npc_planner/ingest/rom_probe.py | head -1'

expect_exit 1 constants_not_in_config_headers \
  bash -c "PYTHONPATH=. python3 -c '
from pathlib import Path
from npc_planner.ingest.rom_probe import probe_layout
l = probe_layout(Path(\"tests/fixtures/fake_rom\"))
import sys
sys.exit(0 if any(\"constants\" in str(p) for p in l.config_headers) else 1)
'"

# --- missing headers -------------------------------------------------------

# Optional header absent: empty mapping, no exception.
expect_stdout "empty_ok" optional_header_missing bash -c '
  tmp=$(mktemp -d) || exit 9
  trap "rm -rf \"$tmp\"" EXIT
  cp -r tests/fixtures/fake_rom "$tmp/rom"
  rm -f "$tmp/rom/include/constants/difficulty.h"
  PYTHONPATH=. python3 -c "
from pathlib import Path
import sys
from npc_planner.ingest.rom_probe import probe_layout
from npc_planner.ingest.rom_config import read_rom_config
cfg = read_rom_config(probe_layout(Path(sys.argv[1])))
print(\"empty_ok\" if dict(cfg.difficulties) == {} else \"NOT_EMPTY\")
" "$tmp/rom"
'

# Required header absent: RomConfigError naming the path.
expect_stdout "named_ok" required_header_missing bash -c '
  tmp=$(mktemp -d) || exit 9
  trap "rm -rf \"$tmp\"" EXIT
  cp -r tests/fixtures/fake_rom "$tmp/rom"
  rm -f "$tmp/rom/include/config/battle.h"
  PYTHONPATH=. python3 -c "
from pathlib import Path
import sys
from npc_planner.ingest.rom_probe import probe_layout
from npc_planner.ingest.rom_config import read_rom_config, RomConfigError
try:
    read_rom_config(probe_layout(Path(sys.argv[1])))
except RomConfigError as exc:
    print(\"named_ok\" if \"battle.h\" in str(exc) else \"UNNAMED\")
except Exception as exc:
    print(type(exc).__name__)
" "$tmp/rom"
'

# --- tests -----------------------------------------------------------------

expect_exit 0 rom_config_tests  pytest tests/unit/test_rom_config.py -q
expect_exit 0 fixture_tests     pytest tests/unit/test_fake_rom_fixture.py -q
expect_exit 0 probe_tests       pytest tests/unit/test_rom_probe.py -q

# --- history stays clean ---------------------------------------------------

expect_stdout "14 with violations" no_new_violations \
  bash -c 'python3 scripts/audit_commits.py --range milestone/M1 | tail -1'

expect_stdout "ok" accept_scripts_parse bash -c '
  for f in scripts/accept/*.sh; do bash -n "$f" || exit 1; done
  echo "all_parse=ok"
'

accept_summary
