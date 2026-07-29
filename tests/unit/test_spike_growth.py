from dnd_board_game.combat import (
    ActiveCombatEffect,
    spike_growth_damage_dice_count,
    spike_growth_damaging_steps,
)
from dnd_board_game.world import Coordinate


def test_spike_growth_rolls_two_d4_for_each_five_foot_step_inside_zone() -> None:
    zone = ActiveCombatEffect(
        id="spike-growth:zone",
        actor_id="druid",
        kind="spike_growth_zone",
        label="Kolczaste zarośla",
        object_id="combat_action:spike_growth",
        value=10,
        anchor_position=Coordinate(3, 0),
    )
    path = (
        Coordinate(0, 0),
        Coordinate(1, 0),
        Coordinate(2, 0),
        Coordinate(3, 0),
        Coordinate(4, 0),
        Coordinate(5, 0),
        Coordinate(6, 0),
    )

    assert spike_growth_damaging_steps(path, (zone,)) == 5
    assert spike_growth_damage_dice_count(path, (zone,)) == 10
