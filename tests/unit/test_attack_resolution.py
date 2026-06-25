import pytest

from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.combat import (
    ActionUse,
    AttackDeclaration,
    AttackSource,
    AttackSourceType,
    actor_as_combat_target,
    resolve_attack,
)
from dnd_board_game.rules import AttackRollOutcome, D20RollInput, D20RollRequest, RollModifier, RollModifierType, resolve_d20_roll
from dnd_board_game.world import Coordinate


def _actor(actor_id: str, faction: Faction) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id,
        ac=13,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=faction,
    )


def _declaration() -> AttackDeclaration:
    hero = _actor("hero", Faction.ALLY)
    goblin = _actor("goblin", Faction.ENEMY)
    source = AttackSource(
        "Miecz",
        AttackSourceType.WEAPON,
        5,
        D20RollRequest(modifiers=(RollModifier("Premia", 5, RollModifierType.CUSTOM),)),
    )
    return AttackDeclaration(hero, actor_as_combat_target(goblin), source)


def _roll(natural: int, modifier: int = 0):
    request = D20RollRequest(modifiers=(RollModifier("Premia", modifier, RollModifierType.CUSTOM),))
    return resolve_d20_roll(D20RollInput(request, natural))


def test_attack_resolution_hit_miss_and_criticals():
    declaration = _declaration()

    assert resolve_attack(declaration, _roll(10, 3), ActionUse.ACTION_AVAILABLE).outcome == AttackRollOutcome.HIT
    assert resolve_attack(declaration, _roll(9, 3), ActionUse.ACTION_AVAILABLE).outcome == AttackRollOutcome.MISS
    assert resolve_attack(declaration, _roll(20, -10), ActionUse.ACTION_AVAILABLE).outcome == AttackRollOutcome.CRITICAL_HIT
    assert resolve_attack(declaration, _roll(1, 30), ActionUse.ACTION_AVAILABLE).outcome == AttackRollOutcome.CRITICAL_MISS


def test_attack_resolution_preserves_breakdown_and_consumes_action():
    declaration = _declaration()
    roll = _roll(10, 3)

    resolution = resolve_attack(declaration, roll, ActionUse.ACTION_AVAILABLE)

    assert resolution.attack_roll.breakdown.modifier_total == 3
    assert resolution.action_use == ActionUse.ACTION_USED


def test_attack_resolution_rejects_already_used_action():
    with pytest.raises(ValueError):
        resolve_attack(_declaration(), _roll(10, 3), ActionUse.ACTION_USED)
