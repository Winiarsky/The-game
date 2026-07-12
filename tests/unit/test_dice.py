import pytest

from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    RollMode,
    RollModifier,
    RollModifierType,
    build_modifier_breakdown,
    resolve_d20_roll,
    roll_instruction,
)


def _modifier(
    label: str,
    value: int,
    modifier_type: RollModifierType = RollModifierType.CUSTOM,
    stacking_key: str | None = None,
) -> RollModifier:
    return RollModifier(label, value, modifier_type, stacking_key=stacking_key)


def test_roll_instruction_shows_normal_mode_and_final_modifier():
    request = D20RollRequest(
        modifiers=(
            _modifier("Strength modifier", 3, RollModifierType.ABILITY),
            _modifier("Cover penalty", -2, RollModifierType.COVER),
        )
    )

    instruction = roll_instruction(request)

    assert "Rzuć 1d20" in instruction.message
    assert "Końcowy modyfikator: +1" in instruction.message
    assert instruction.breakdown.modifier_total == 1


def test_roll_instruction_shows_advantage_and_disadvantage_expectations():
    advantage = roll_instruction(D20RollRequest(mode=RollMode.ADVANTAGE))
    disadvantage = roll_instruction(D20RollRequest(mode=RollMode.DISADVANTAGE))

    assert "Rzuć 2d20 z przewagą i wpisz oba wyniki" in advantage.message
    assert "Rzuć 2d20 z utrudnieniem i wpisz oba wyniki" in disadvantage.message


def test_advantage_uses_higher_roll_and_stores_both_results():
    request = D20RollRequest(mode=RollMode.ADVANTAGE, modifiers=(_modifier("Bonus", 2),))

    result = resolve_d20_roll(D20RollInput(request=request, natural_roll=4, natural_roll_2=17))

    assert result.natural_rolls == (4, 17)
    assert result.natural_roll == 17
    assert result.total == 19


def test_disadvantage_uses_lower_roll_and_stores_both_results():
    request = D20RollRequest(mode=RollMode.DISADVANTAGE, modifiers=(_modifier("Bonus", 2),))

    result = resolve_d20_roll(D20RollInput(request=request, natural_roll=4, natural_roll_2=17))

    assert result.natural_rolls == (4, 17)
    assert result.natural_roll == 4
    assert result.total == 6


def test_advantage_validates_second_roll_when_provided():
    request = D20RollRequest(mode=RollMode.ADVANTAGE)

    with pytest.raises(ValueError):
        resolve_d20_roll(D20RollInput(request=request, natural_roll=10, natural_roll_2=0))


def test_different_bonuses_and_penalties_sum_into_active_breakdown():
    request = D20RollRequest(
        modifiers=(
            _modifier("Strength modifier", 3, RollModifierType.ABILITY),
            _modifier("Magic weapon", 1, RollModifierType.ITEM, "magic_weapon"),
            _modifier("Cover penalty", -2, RollModifierType.COVER),
        )
    )

    result = resolve_d20_roll(D20RollInput(request=request, natural_roll=12))

    assert result.breakdown.modifier_total == 2
    assert result.total == 14
    assert [modifier.label for modifier in result.breakdown.active_modifiers] == [
        "Strength modifier",
        "Cover penalty",
        "Magic weapon",
    ]


def test_duplicate_stacking_key_keeps_one_component_and_marks_ignored():
    breakdown = build_modifier_breakdown(
        (
            _modifier("Proficiency bonus", 2, RollModifierType.PROFICIENCY, "proficiency"),
            _modifier("Duplicate proficiency", 2, RollModifierType.PROFICIENCY, "proficiency"),
            _modifier("Better item bonus", 2, RollModifierType.ITEM, "item_bonus"),
            _modifier("Weak item bonus", 1, RollModifierType.ITEM, "item_bonus"),
        )
    )

    assert breakdown.modifier_total == 4
    assert [modifier.label for modifier in breakdown.active_modifiers] == [
        "Proficiency bonus",
        "Better item bonus",
    ]
    assert [modifier.label for modifier in breakdown.ignored_modifiers] == [
        "Duplicate proficiency",
        "Weak item bonus",
    ]


def test_duplicate_penalties_keep_strongest_penalty():
    breakdown = build_modifier_breakdown(
        (
            _modifier("Light penalty", -1, RollModifierType.SITUATIONAL, "same_penalty"),
            _modifier("Heavy penalty", -3, RollModifierType.SITUATIONAL, "same_penalty"),
        )
    )

    assert breakdown.modifier_total == -3
    assert breakdown.active_modifiers[0].label == "Heavy penalty"
    assert breakdown.ignored_modifiers[0].label == "Light penalty"


def test_natural_roll_must_be_between_1_and_20():
    request = D20RollRequest()

    with pytest.raises(ValueError):
        resolve_d20_roll(D20RollInput(request=request, natural_roll=0))
    with pytest.raises(ValueError):
        resolve_d20_roll(D20RollInput(request=request, natural_roll=21))


def test_natural_1_and_20_flags_are_detected():
    request = D20RollRequest(modifiers=(_modifier("Bonus", 10),))

    natural_one = resolve_d20_roll(D20RollInput(request=request, natural_roll=1))
    natural_twenty = resolve_d20_roll(D20RollInput(request=request, natural_roll=20))

    assert natural_one.is_natural_1 is True
    assert natural_one.is_natural_20 is False
    assert natural_one.total == 11
    assert natural_twenty.is_natural_20 is True
    assert natural_twenty.is_natural_1 is False
    assert natural_twenty.total == 30
