import pytest

from dnd_board_game.actors import (
    CreatureSize,
    can_grapple_or_shove_size,
    creature_size_label_pl,
    largest_grapple_or_shove_target,
)


@pytest.mark.parametrize(
    ("attacker", "target", "allowed"),
    (
        (CreatureSize.SMALL, CreatureSize.TINY, True),
        (CreatureSize.SMALL, CreatureSize.MEDIUM, True),
        (CreatureSize.SMALL, CreatureSize.LARGE, False),
        (CreatureSize.MEDIUM, CreatureSize.LARGE, True),
        (CreatureSize.MEDIUM, CreatureSize.HUGE, False),
        (CreatureSize.GARGANTUAN, CreatureSize.GARGANTUAN, True),
    ),
)
def test_grapple_and_shove_size_limit(
    attacker: CreatureSize,
    target: CreatureSize,
    allowed: bool,
) -> None:
    assert can_grapple_or_shove_size(attacker, target) is allowed


def test_largest_target_and_polish_label_are_explicit() -> None:
    maximum = largest_grapple_or_shove_target(CreatureSize.MEDIUM)

    assert maximum == CreatureSize.LARGE
    assert creature_size_label_pl(maximum) == "duży"
