import pytest
from pydantic import ValidationError

from npc_planner.db.models import (
    AbilityRow,
    FormRow,
    MoveRow,
    TrainerSpecRow,
    TypeMatchupRow,
)


def test_form_row_validation() -> None:
    form = FormRow(
        form_id="skarmory",
        species_slug="skarmory",
        type_1="steel",
        type_2="flying",
        base_hp=65,
        base_atk=80,
        base_def=140,
        base_spa=40,
        base_spd=70,
        base_spe=70,
    )
    assert form.form_id == "skarmory"
    assert form.base_hp == 65


def test_move_row_validation() -> None:
    move = MoveRow(
        move_slug="thunderbolt",
        move_name="Thunderbolt",
        type_slug="electric",
        damage_class="special",
    )
    assert move.move_slug == "thunderbolt"
    assert move.damage_class == "special"


def test_type_matchup_multiplier_validation() -> None:
    matchup = TypeMatchupRow(
        attacking_type="fire", defending_type="grass", multiplier=2.0
    )
    assert matchup.multiplier == 2.0

    with pytest.raises(ValidationError):
        TypeMatchupRow(attacking_type="fire", defending_type="grass", multiplier=3.0)


def test_trainer_spec_validation() -> None:
    trainer = TrainerSpecRow(
        trainer_id="gym_04_marlon",
        name="Marlon",
        trainer_tier="gym_leader",
        difficulty_target="challenging",
        level_min=30,
        level_max=33,
    )
    assert trainer.trainer_id == "gym_04_marlon"
    assert trainer.trainer_tier == "gym_leader"


def test_ability_row_validation() -> None:
    ability = AbilityRow(
        ability_slug="sturdy",
        ability_name="Sturdy",
    )
    assert ability.ability_slug == "sturdy"
