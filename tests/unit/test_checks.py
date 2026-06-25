from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    RollModifier,
    RollModifierType,
    resolve_ability_check,
    resolve_d20_roll,
    resolve_saving_throw,
)


def _roll(natural_roll: int, modifier: int = 0):
    request = D20RollRequest(
        modifiers=(
            RollModifier("Test modifier", modifier, RollModifierType.CUSTOM),
        )
    )
    return resolve_d20_roll(D20RollInput(request=request, natural_roll=natural_roll))


def test_ability_check_succeeds_when_total_meets_dc():
    result = resolve_ability_check(_roll(12, 3), dc=15)

    assert result.success is True


def test_ability_check_fails_when_total_is_below_dc():
    result = resolve_ability_check(_roll(11, 3), dc=15)

    assert result.success is False


def test_natural_20_does_not_force_ability_check_success():
    result = resolve_ability_check(_roll(20, 0), dc=25)

    assert result.success is False


def test_natural_1_does_not_force_ability_check_failure():
    result = resolve_ability_check(_roll(1, 20), dc=20)

    assert result.success is True


def test_saving_throw_uses_same_dc_logic():
    success = resolve_saving_throw(_roll(15, 2), dc=17)
    failure = resolve_saving_throw(_roll(14, 2), dc=17)

    assert success.success is True
    assert failure.success is False
