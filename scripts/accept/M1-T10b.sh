#!/usr/bin/env bash
# Acceptance for M1-T10b - corrected ROM config reader + done-tag loophole.
# Run from the repository root:  bash scripts/accept/M1-T10b.sh
#
# Never use `set -e` here: every check must run so the summary is complete.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/accept/_lib.sh
source "${HERE}/_lib.sh"

PY="python3"
FIX="tests/fixtures/fake_rom"

# ---------------------------------------------------------------- preamble --

expect_exit 0 make_gate make gate

# The gate and the hooks must agree. If this reformats anything, the two-ruff
# problem has come back and every later result is untrustworthy.
expect_no_stdout "reformatted" ruff_paths_agree \
  "${PY}" -m pre_commit run --all-files

# --------------------------------------------------------- Step 0 landed ----

expect_exit 0 stale_t11_deleted test -f docs/tasks/M1-T11.md
expect_exit 0 stale_t12_deleted test -f docs/tasks/M1-T12.md
expect_exit 0 card_present test -f docs/tasks/M1-T10b.md

expect_stdout "11.11" ci_scope_documented \
  grep "11.11" EXECUTION_PROTOCOL.md

expect_stdout "ok" card_is_protocol_tagged \
  bash -c 'git log --format=%s -1 -- docs/tasks/M1-T10b.md | grep -qF "[protocol]" && echo ok'

# ------------------------------------------------------------ hygiene -------

expect_exit 1 no_eval_in_src \
  grep -rnF -e "eval(" -e "exec(" -e "literal_eval" -e "compile(" \
    src/npc_planner/ingest/rom_config.py

# ------------------------------------------------- the four regressions -----

read -r -d "" LOAD <<"PYEOF"
from pathlib import Path
from npc_planner.ingest.rom_probe import probe_layout
from npc_planner.ingest.rom_config import (
    BASELINE_SYMBOLS,
    LIMIT_SYMBOLS,
    RomConfigError,
    audit_coverage,
    enabled_generations,
    physical_special_split_enabled,
    read_rom_config,
)

layout = probe_layout(Path("tests/fixtures/fake_rom"))
cfg = read_rom_config(layout)
buckets = (
    cfg.battle, cfg.species, cfg.pokemon, cfg.limits,
    cfg.constants, cfg.versions, cfg.ai_flags, cfg.difficulties,
)
PYEOF

expect_stdout "split=3" split_flag_present \
  "${PY}" -c "${LOAD}"$'\n'"print('split=%s' % cfg.battle['B_PHYSICAL_SPECIAL_SPLIT'])"

expect_stdout "matchups=3" type_matchups_resolved \
  "${PY}" -c "${LOAD}"$'\n'"print('matchups=%s' % cfg.battle['B_UPDATED_TYPE_MATCHUPS'])"

expect_stdout "split_enabled=False" split_predicate_false \
  "${PY}" -c "${LOAD}"$'\n'"print('split_enabled=%s' % physical_special_split_enabled(cfg))"

expect_stdout "hidden=1" hidden_abilities_present \
  "${PY}" -c "${LOAD}"$'\n'"print('hidden=%s' % cfg.pokemon['P_HIDDEN_ABILITIES'])"

expect_stdout "gens=[1, 2, 3]" gen1_enabled \
  "${PY}" -c "${LOAD}"$'\n'"print('gens=%s' % sorted(enabled_generations(cfg)))"

expect_stdout "gen9=0" gen9_disabled \
  "${PY}" -c "${LOAD}"$'\n'"print('gen9=%s' % cfg.species['P_GEN_9_POKEMON'])"

expect_stdout "easy=0" difficulty_easy_zero \
  "${PY}" -c "${LOAD}"$'\n'"print('easy=%s' % cfg.difficulties['DIFFICULTY_EASY'])"

expect_stdout "default=1" difficulty_default \
  "${PY}" -c "${LOAD}"$'\n'"print('default=%s' % cfg.difficulties['DIFFICULTY_DEFAULT'])"

# ------------------------------------------------------ no guard leakage ----

expect_stdout "guards=0" no_guard_keys \
  "${PY}" -c "${LOAD}"$'\n'"print('guards=%d' % sum(1 for b in buckets for k in b if k.startswith('GUARD_')))"

expect_stdout "defines=0" no_define_values \
  "${PY}" -c "${LOAD}"$'\n'"print('defines=%d' % sum(1 for b in buckets for v in b.values() if isinstance(v, str) and v.lstrip().startswith('#define')))"

expect_stdout "ignored_ok=True" guards_recorded_as_ignored \
  "${PY}" -c "${LOAD}"$'\n'"print('ignored_ok=%s' % any(s.startswith('GUARD_') for s in cfg.ignored))"

# -------------------------------------------------------- bucket hygiene ----

expect_stdout "limits_ok=True" limits_allowlisted \
  "${PY}" -c "${LOAD}"$'\n'"print('limits_ok=%s' % set(cfg.limits).issubset(LIMIT_SYMBOLS))"

expect_stdout "party=6 moves=4 items=4 boxes=14" limit_values \
  "${PY}" -c "${LOAD}"$'\n'"print('party=%s moves=%s items=%s boxes=%s' % (cfg.limits['PARTY_SIZE'], cfg.limits['MAX_MON_MOVES'], cfg.limits['MAX_TRAINER_ITEMS'], cfg.limits['NUM_STORAGE_BOXES']))"

expect_stdout "versions_split=True" versions_split \
  "${PY}" -c "${LOAD}"$'\n'"print('versions_split=%s' % (cfg.versions['EXPANSION_VERSION_MINOR'] == 9 and 'EXPANSION_VERSION_MAJOR' in cfg.versions and not any(k.startswith('EXPANSION_VERSION_') for k in cfg.limits)))"

expect_stdout "sides=0,1" constants_bucket \
  "${PY}" -c "${LOAD}"$'\n'"print('sides=%s,%s' % (cfg.constants['B_SIDE_PLAYER'], cfg.constants['B_SIDE_OPPONENT']))"

expect_stdout "sides_not_limits=True" sides_not_in_limits \
  "${PY}" -c "${LOAD}"$'\n'"print('sides_not_limits=%s' % ('B_SIDE_PLAYER' not in cfg.limits))"

expect_stdout "baseline=11" baseline_symbols_pinned \
  "${PY}" -c "${LOAD}"$'\n'"print('baseline=%d' % len(BASELINE_SYMBOLS))"

# ------------------------------------------------------------- coverage -----

expect_stdout "uncovered=()" coverage_clean \
  "${PY}" -c "${LOAD}"$'\n'"print('uncovered=%s' % (audit_coverage(layout, cfg),))"

# The guard must be able to fail. Drop one parsed symbol and the auditor has
# to notice; if this prints detects=False the check is decorative.
expect_stdout "detects=True" coverage_detects_loss \
  "${PY}" -c "${LOAD}"$'\n'"import dataclasses"$'\n'"broken = dataclasses.replace(cfg, limits={k: v for k, v in cfg.limits.items() if k != 'PARTY_SIZE'})"$'\n'"print('detects=%s' % (len(audit_coverage(layout, broken)) > 0))"

# ----------------------------------------------------- unchanged from T10 ---

expect_stdout "bad=1 smart=8192 basic=7" ai_flags_intact \
  "${PY}" -c "${LOAD}"$'\n'"print('bad=%s smart=%s basic=%s' % (cfg.ai_flags['AI_FLAG_CHECK_BAD_MOVE'], cfg.ai_flags['AI_FLAG_SMART_SWITCHING'], cfg.ai_flags['AI_FLAG_BASIC_TRAINER']))"

expect_stdout "runtime_ok=True" unevaluated_reported \
  "${PY}" -c "${LOAD}"$'\n'"print('runtime_ok=%s' % ('AI_FLAG_RUNTIME_TUNED' not in cfg.ai_flags and any(u.symbol == 'AI_FLAG_RUNTIME_TUNED' for u in cfg.unevaluated)))"

expect_stdout "deterministic=True" deterministic \
  "${PY}" -c "${LOAD}"$'\n'"print('deterministic=%s' % (read_rom_config(layout) == cfg))"

expect_stdout "raises=True" split_predicate_raises \
  "${PY}" -c "${LOAD}"$'\n'"import dataclasses"$'\n'"empty = dataclasses.replace(cfg, battle={})"$'\n'"
try:
    physical_special_split_enabled(empty)
    print('raises=False')
except RomConfigError:
    print('raises=True')
"

# ------------------------------------------------------ done-tag loophole ---

TMPMSG="$(mktemp)"
trap 'rm -f "${TMPMSG}"' EXIT

printf '%s\n' "chore(ci): reuse a finished tag   [M1-T08e]" > "${TMPMSG}"
expect_exit 1 done_tag_rejected \
  "${PY}" scripts/hooks/task_id_required.py "${TMPMSG}"

printf '%s\n' "feat(ingest): open task work   [M1-T99z]" > "${TMPMSG}"
expect_exit 0 open_tag_accepted \
  "${PY}" scripts/hooks/task_id_required.py "${TMPMSG}"

printf '%s\n' "feat(ingest): finished task work   [M1-T10b]" > "${TMPMSG}"
expect_exit 1 done_tag_rejected_t10b \
  "${PY}" scripts/hooks/task_id_required.py "${TMPMSG}"

printf '%s\n' "chore(ci): unify formatter   [ci]" > "${TMPMSG}"
expect_exit 0 ci_tag_accepted \
  "${PY}" scripts/hooks/task_id_required.py "${TMPMSG}"

printf '%s\n' "chore: no tag at all" > "${TMPMSG}"
expect_exit 1 untagged_still_rejected \
  "${PY}" scripts/hooks/task_id_required.py "${TMPMSG}"

expect_stdout "CI_SCOPE" ci_scope_present \
  grep "CI_SCOPE" scripts/audit_commits.py

expect_exit 1 protocol_scope_excludes_precommit \
  bash -c 'grep -A6 "PROTOCOL_SCOPE" scripts/audit_commits.py | grep -qF ".pre-commit-config.yaml"'

# --------------------------------------------------------------- audit ------

expect_stdout "17 with violations" audit_two_new_violations \
  "${PY}" scripts/audit_commits.py --range milestone/M1

expect_stdout "7d22d8f" audit_flags_first_tagshop \
  bash -c '${PY} scripts/audit_commits.py --range milestone/M1 | grep 7d22d8f'
expect_stdout "737dc19" audit_flags_second_tagshop \
  bash -c '${PY} scripts/audit_commits.py --range milestone/M1 | grep 737dc19'

# --------------------------------------------------------------- suites -----

expect_exit 0 rom_config_tests "${PY}" -m pytest tests/unit/test_rom_config.py -q
expect_exit 0 hook_tests "${PY}" -m pytest tests/unit/test_hooks.py -q
expect_exit 0 audit_tests "${PY}" -m pytest tests/unit/test_audit_commits.py -q

# ----------------------------------------------------------- card intact ----

expect_no_stdout "M1-T10b.md" card_unmodified \
  git diff --name-only milestone/M1...HEAD -- docs/tasks/

expect_stdout "ok" accept_scripts_parse \
  bash -c 'for f in scripts/accept/*.sh; do bash -n "$f" || exit 1; done; echo ok'

accept_summary 46
