from dataclasses import replace

import pytest

from dnd_board_game.actors import AbilityScores, Actor, ActorId, DeathSaveState, Faction
from dnd_board_game.application import StabilizationMethod, legal_stabilization_targets, resolve_combat_stabilization
from dnd_board_game.combat import InitiativeEntry, InitiativeOrder, start_combat
from dnd_board_game.inventory import InventoryItem
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.world import Coordinate


def _actor(actor_id: str, faction: Faction, position: Coordinate, *, wisdom: int = 10) -> Actor:
    return Actor(
        id=ActorId(actor_id), name=actor_id, ac=12, hp=10, temp_hp=0,
        speed_feet=30, position=position, faction=faction,
        ability_scores=AbilityScores(wisdom=wisdom),
    )


def _state(stabilizer: Actor, target: Actor, enemy: Actor):
    actors = (stabilizer, target, enemy)
    entries = tuple(
        InitiativeEntry(actor, resolve_d20_roll(D20RollInput(D20RollRequest(), 20 - index)), 0, index)
        for index, actor in enumerate(actors)
    )
    return start_combat(actors, InitiativeOrder(entries))


def _dying(actor: Actor) -> Actor:
    return replace(actor, hp=0, uses_death_saves=True, death_saves=DeathSaveState(failures=1))


def test_medicine_stabilization_uses_action_and_applies_wisdom_modifier() -> None:
    healer = _actor("healer", Faction.ALLY, Coordinate(0, 0), wisdom=14)
    target = _dying(_actor("target", Faction.ALLY, Coordinate(1, 0)))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(5, 0))
    result = resolve_combat_stabilization(
        _state(healer, target, enemy), target_id="target",
        method=StabilizationMethod.MEDICINE, natural_roll=8,
    )

    updated_target = next(actor for actor in result.state.actors if actor.id == target.id)
    assert result.total == 10
    assert result.success is True
    assert updated_target.death_saves == DeathSaveState(stable=True)
    assert result.state.turn_action.action_use.value == "action_used"


def test_failed_medicine_check_still_uses_action() -> None:
    healer = _actor("healer", Faction.ALLY, Coordinate(0, 0))
    target = _dying(_actor("target", Faction.ALLY, Coordinate(1, 0)))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(5, 0))
    result = resolve_combat_stabilization(
        _state(healer, target, enemy), target_id="target",
        method=StabilizationMethod.MEDICINE, natural_roll=9,
    )

    assert result.success is False
    assert result.state.turn_action.action_use.value == "action_used"
    assert next(actor for actor in result.state.actors if actor.id == target.id).needs_death_save() is True


def test_healers_kit_stabilizes_without_roll_and_consumes_one_use() -> None:
    kit = InventoryItem(
        "healers_kit",
        "Zestaw uzdrowiciela",
        "tool",
        charges_maximum=10,
        charges_current=2,
    )
    healer = replace(_actor("healer", Faction.ALLY, Coordinate(0, 0)), inventory=(kit,))
    target = _dying(_actor("target", Faction.ALLY, Coordinate(1, 0)))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(5, 0))
    result = resolve_combat_stabilization(
        _state(healer, target, enemy), target_id="target",
        method=StabilizationMethod.HEALERS_KIT,
    )

    assert result.success is True
    assert result.kit_remaining == 1
    assert result.natural_roll is None


def test_only_adjacent_dying_allies_are_legal_targets() -> None:
    healer = _actor("healer", Faction.ALLY, Coordinate(0, 0))
    far_target = _dying(_actor("target", Faction.ALLY, Coordinate(2, 0)))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    state = _state(healer, far_target, enemy)

    assert legal_stabilization_targets(state, healer) == ()
    with pytest.raises(ValueError, match="legalnym celem"):
        resolve_combat_stabilization(
            state, target_id="target", method=StabilizationMethod.MEDICINE, natural_roll=20,
        )
