import dataclasses
import shutil
from pathlib import Path

pytest = __import__("pytest")

from npc_planner.ingest.rom_config import (
    BASELINE_SYMBOLS,
    LIMIT_SYMBOLS,
    RomConfigError,
    audit_coverage,
    enabled_generations,
    evaluate_int_expr,
    physical_special_split_enabled,
    read_rom_config,
)
from npc_planner.ingest.rom_probe import probe_layout


@pytest.fixture
def fake_rom_layout() -> object:
    root = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "fake_rom"
    return probe_layout(root)


# ------------------- must-pass tests 1-15 (legacy signatures preserved) -------------------


def test_1_party_size_limit(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    assert cfg.limits["PARTY_SIZE"] == 6


def test_2_max_mon_moves_limit(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    assert cfg.limits["MAX_MON_MOVES"] == 4


def test_3_num_storage_boxes_hex_literal(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    assert cfg.limits["NUM_STORAGE_BOXES"] == 14


def test_4_max_trainer_items_from_battle_h(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    assert cfg.limits["MAX_TRAINER_ITEMS"] == 4


def test_5_ai_flag_check_bad_move(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    assert cfg.ai_flags["AI_FLAG_CHECK_BAD_MOVE"] == 1


def test_6_ai_flag_smart_switching_shift_13(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    assert cfg.ai_flags["AI_FLAG_SMART_SWITCHING"] == 8192


def test_7_ai_flag_basic_trainer_composite(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    assert cfg.ai_flags["AI_FLAG_BASIC_TRAINER"] == 7


def test_8_difficulty_default_resolves_symbol(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    assert cfg.difficulties["DIFFICULTY_DEFAULT"] == 1


def test_9_ai_flag_runtime_tuned_in_unevaluated(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    assert "AI_FLAG_RUNTIME_TUNED" not in cfg.ai_flags

    uneval_symbols = [u.symbol for u in cfg.unevaluated]
    assert "AI_FLAG_RUNTIME_TUNED" in uneval_symbols

    target = next(u for u in cfg.unevaluated if u.symbol == "AI_FLAG_RUNTIME_TUNED")
    assert target.reason != ""


def test_10_evaluate_int_expr_shift_and_or() -> None:
    val = evaluate_int_expr("(1 << 3) | 0x10", {})
    assert val == 24


def test_11_evaluate_int_expr_unknown_returns_none() -> None:
    val = evaluate_int_expr("SOME_UNKNOWN", {})
    assert val is None


def test_12_ai_flags_powers_of_two_or_composite(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    for sym, val in cfg.ai_flags.items():
        assert val > 0, f"{sym} value is not positive: {val}"
        if sym != "AI_FLAG_BASIC_TRAINER":
            assert (val & (val - 1)) == 0, f"{sym} is not a power of 2: {val}"


def test_13_missing_optional_difficulty_header_ok(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "fake_rom"
    temp_rom = tmp_path / "fake_rom_copy"
    shutil.copytree(root, temp_rom)

    diff_header = temp_rom / "include" / "constants" / "difficulty.h"
    diff_header.unlink()

    layout = probe_layout(temp_rom)
    cfg = read_rom_config(layout)
    assert dict(cfg.difficulties) == {}


def test_14_missing_required_battle_header_raises(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "fake_rom"
    temp_rom = tmp_path / "fake_rom_copy"
    shutil.copytree(root, temp_rom)

    battle_header = temp_rom / "include" / "config" / "battle.h"
    battle_header.unlink()

    layout = probe_layout(temp_rom)
    with pytest.raises(RomConfigError) as exc_info:
        read_rom_config(layout)
    assert "battle.h" in str(exc_info.value)


def test_15_read_rom_config_is_deterministic(fake_rom_layout: object) -> None:
    cfg1 = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    cfg2 = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    assert cfg1 == cfg2
    assert list(cfg1.ai_flags) == list(cfg2.ai_flags)


# ------------------- must-pass tests 1-22 for M1-T10b rom_config -------------------


def test_1_b_physical_special_split_value(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    assert cfg.battle["B_PHYSICAL_SPECIAL_SPLIT"] == 3


def test_2_b_updated_type_matchups_value(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    assert cfg.battle["B_UPDATED_TYPE_MATCHUPS"] == 3


def test_3_physical_special_split_enabled_false(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    assert physical_special_split_enabled(cfg) is False


def test_4_physical_special_split_enabled_raises_when_absent(
    fake_rom_layout: object,
) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    empty_battle_cfg = dataclasses.replace(cfg, battle={})
    with pytest.raises(RomConfigError) as exc_info:
        physical_special_split_enabled(empty_battle_cfg)
    assert "B_PHYSICAL_SPECIAL_SPLIT" in str(exc_info.value)


def test_5_p_hidden_abilities_value(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    assert cfg.pokemon["P_HIDDEN_ABILITIES"] == 1


def test_6_p_gen_1_pokemon_value(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    assert cfg.species["P_GEN_1_POKEMON"] == 1


def test_7_p_gen_9_pokemon_value(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    assert cfg.species["P_GEN_9_POKEMON"] == 0


def test_8_enabled_generations_set(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    assert enabled_generations(cfg) == frozenset({1, 2, 3})


def test_9_difficulties_easy_and_default(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    assert cfg.difficulties["DIFFICULTY_EASY"] == 0
    assert cfg.difficulties["DIFFICULTY_DEFAULT"] == 1


def test_10_no_guard_keys_in_mappings(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    all_mappings = (
        cfg.battle,
        cfg.species,
        cfg.pokemon,
        cfg.limits,
        cfg.constants,
        cfg.versions,
        cfg.ai_flags,
        cfg.difficulties,
    )
    for m in all_mappings:
        for k in m:
            assert not k.startswith("GUARD_"), f"Guard key {k} in mapping"


def test_11_no_define_strings_in_values(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    all_mappings = (
        cfg.battle,
        cfg.species,
        cfg.pokemon,
        cfg.limits,
        cfg.constants,
        cfg.versions,
        cfg.ai_flags,
        cfg.difficulties,
    )
    for m in all_mappings:
        for v in m.values():
            if isinstance(v, str):
                assert not v.lstrip().startswith("#define"), (
                    f"Unparsed #define string value: {v}"
                )


def test_12_valueless_define_flag_one(tmp_path: Path) -> None:
    temp_rom = tmp_path / "fake_rom_valueless"
    root = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "fake_rom"
    shutil.copytree(root, temp_rom)

    (temp_rom / "include" / "constants" / "custom.h").write_text(
        "#define FOO\n", encoding="utf-8"
    )

    layout = probe_layout(temp_rom)
    layout = dataclasses.replace(
        layout,
        config_constants=layout.config_constants
        + (temp_rom / "include" / "constants" / "custom.h",),
    )
    cfg = read_rom_config(layout)
    assert cfg.constants["FOO"] == 1


def test_13_include_guard_ignored(tmp_path: Path) -> None:
    temp_rom = tmp_path / "fake_rom_guard"
    root = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "fake_rom"
    shutil.copytree(root, temp_rom)

    (temp_rom / "include" / "constants" / "guard_test.h").write_text(
        "#define GUARD_X_H\n", encoding="utf-8"
    )

    layout = probe_layout(temp_rom)
    layout = dataclasses.replace(
        layout,
        config_constants=layout.config_constants
        + (temp_rom / "include" / "constants" / "guard_test.h",),
    )
    cfg = read_rom_config(layout)
    assert "GUARD_X_H" in cfg.ignored
    assert "GUARD_X_H" not in cfg.constants


def test_14_limits_constrained_to_limit_symbols(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    assert set(cfg.limits) <= LIMIT_SYMBOLS
    assert cfg.limits["PARTY_SIZE"] == 6
    assert cfg.limits["MAX_MON_MOVES"] == 4
    assert cfg.limits["MAX_TRAINER_ITEMS"] == 4
    assert cfg.limits["NUM_STORAGE_BOXES"] == 14


def test_15_versions_mapping_and_major_version(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    assert cfg.versions["EXPANSION_VERSION_MINOR"] == 9
    assert cfg.versions["EXPANSION_VERSION_PATCH"] == 0
    assert "EXPANSION_VERSION_MAJOR" in cfg.versions
    assert cfg.versions["EXPANSION_VERSION_MAJOR"] == 1


def test_16_constants_mapping_sides_not_in_limits(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    assert cfg.constants["B_SIDE_PLAYER"] == 0
    assert cfg.constants["B_SIDE_OPPONENT"] == 1
    assert "B_SIDE_PLAYER" not in cfg.limits
    assert "B_SIDE_OPPONENT" not in cfg.limits


def test_17_audit_coverage_clean(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    assert audit_coverage(fake_rom_layout, cfg) == ()  # type: ignore[arg-type]


def test_18_audit_coverage_detects_missing_symbol(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    broken_limits = {k: v for k, v in cfg.limits.items() if k != "PARTY_SIZE"}
    broken_cfg = dataclasses.replace(cfg, limits=broken_limits)
    uncovered = audit_coverage(fake_rom_layout, broken_cfg)  # type: ignore[arg-type]
    assert "PARTY_SIZE" in uncovered


def test_19_baseline_symbols_pinned() -> None:
    assert len(BASELINE_SYMBOLS) == 11
    assert BASELINE_SYMBOLS["FALSE"] == 0
    assert BASELINE_SYMBOLS["TRUE"] == 1
    for gen in range(1, 10):
        assert BASELINE_SYMBOLS[f"GEN_{gen}"] == gen


def test_20_ai_flags_intact(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    assert cfg.ai_flags["AI_FLAG_CHECK_BAD_MOVE"] == 1
    assert cfg.ai_flags["AI_FLAG_SMART_SWITCHING"] == 8192
    assert cfg.ai_flags["AI_FLAG_BASIC_TRAINER"] == 7


def test_21_ai_flag_runtime_tuned_unevaluated(fake_rom_layout: object) -> None:
    cfg = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    assert "AI_FLAG_RUNTIME_TUNED" not in cfg.ai_flags
    assert any(u.symbol == "AI_FLAG_RUNTIME_TUNED" for u in cfg.unevaluated)


def test_22_read_rom_config_equals(fake_rom_layout: object) -> None:
    cfg1 = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    cfg2 = read_rom_config(fake_rom_layout)  # type: ignore[arg-type]
    assert cfg1 == cfg2
