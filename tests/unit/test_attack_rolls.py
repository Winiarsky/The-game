from dnd_board_game.rules import (
    AttackRollOutcome,
    D20RollInput,
    D20RollRequest,
    RollMode,
    RollModifier,
    RollModifierType,
    resolve_attack_roll,
    resolve_d20_roll,
)


def _attack_roll(natural_roll: int, modifier: int = 0, mode: RollMode = RollMode.NORMAL):
    request = D20RollRequest(
        mode=mode,
        modifiers=(
            RollModifier("Attack modifier", modifier, RollModifierType.CUSTOM),
        ),
    )
    return resolve_d20_roll(D20RollInput(request=request, natural_roll=natural_roll))


def test_attack_roll_hits_when_total_meets_ac():
    result = resolve_attack_roll(_attack_roll(12, 5), target_ac=17)

    assert result.outcome == AttackRollOutcome.HIT
    assert result.hits is True


def test_attack_roll_misses_when_total_is_below_ac():
    result = resolve_attack_roll(_attack_roll(11, 5), target_ac=17)

    assert result.outcome == AttackRollOutcome.MISS
    assert result.hits is False


def test_natural_20_is_critical_hit_even_with_low_total():
    result = resolve_attack_roll(_attack_roll(20, -10), target_ac=30)

    assert result.outcome == AttackRollOutcome.CRITICAL_HIT
    assert result.hits is True


def test_natural_1_is_critical_miss_even_with_high_total():
    result = resolve_attack_roll(_attack_roll(1, 30), target_ac=10)

    assert result.outcome == AttackRollOutcome.CRITICAL_MISS
    assert result.hits is False


def test_attack_roll_uses_active_modifier_breakdown():
    request = D20RollRequest(
        mode=RollMode.ADVANTAGE,
        modifiers=(
            RollModifier("Strength modifier", 3, RollModifierType.ABILITY),
            RollModifier("Proficiency bonus", 2, RollModifierType.PROFICIENCY, "proficiency"),
            RollModifier("Duplicate proficiency", 2, RollModifierType.PROFICIENCY, "proficiency"),
        ),
    )
    roll = resolve_d20_roll(D20RollInput(request=request, natural_roll=10))

    result = resolve_attack_roll(roll, target_ac=15)

    assert roll.breakdown.modifier_total == 5
    assert result.outcome == AttackRollOutcome.HIT
