import shutil
from pathlib import Path

pytest = __import__("pytest")

from npc_planner.ingest.rom_config import (
    RomConfigError,
    evaluate_int_expr,
    read_rom_config,
)
from npc_planner.ingest.rom_probe import probe_layout


@pytest.fixture
def fake_rom_layout() -> object:
    root = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "fake_rom"
    return probe_layout(root)


# ------------------- must-pass tests 1-15 -------------------


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
            # Power of 2 check
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
