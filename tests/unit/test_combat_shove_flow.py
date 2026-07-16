from dataclasses import replace

import pytest

from dnd_board_game.actors import AbilityScores, Actor, ActorId, CreatureSize, Faction, ProficiencyProfile
from dnd_board_game.application import CombatShoveFlowService, ShoveMode
from dnd_board_game.combat import (
    CombatCondition,
    InitiativeEntry,
    InitiativeOrder,
    has_condition,
    start_combat,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.world import BLOCKING_TERRAIN, BoardState, Coordinate


def _actor(
    actor_id: str,
    faction: Faction,
    position: Coordinate,
    *,
    strength: int = 10,
    dexterity: int = 10,
    skills: tuple[str, ...] = (),
    size: CreatureSize = CreatureSize.MEDIUM,
) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id.title(),
        ac=12,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
        size=size,
        ability_scores=AbilityScores(strength=strength, dexterity=dexterity),
        proficiency_bonus=2,
        proficiencies=ProficiencyProfile(skills=skills),
    )


def _state(hero: Actor, target: Actor):
    request = D20RollRequest()
    order = InitiativeOrder(
        (
            InitiativeEntry(hero, resolve_d20_roll(D20RollInput(request, 20)), 0, 0),
            InitiativeEntry(target, resolve_d20_roll(D20RollInput(request, 10)), 0, 1),
        )
    )
    return start_combat((hero, target), order)


def test_prepare_shove_uses_athletics_and_targets_best_defense() -> None:
    service = CombatShoveFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 1), strength=16, skills=("athletics",))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(2, 1), dexterity=14, skills=("acrobatics",))

    pending = service.prepare(
        state=_state(hero, goblin),
        board=BoardState(),
        target_id="goblin",
        mode=ShoveMode.PRONE,
    )

    assert pending.defender_skill == "acrobatics"
    assert pending.as_payload()["attacker_check"]["modifier_total"] == 5
    assert pending.as_payload()["defender_check"]["modifier_total"] == 4


def test_shove_rejects_target_more_than_one_size_larger() -> None:
    service = CombatShoveFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 1), size=CreatureSize.SMALL)
    ogre = _actor("ogre", Faction.ENEMY, Coordinate(2, 1), size=CreatureSize.LARGE)
    state = _state(hero, ogre)

    assert service.available_modes(
        state=state,
        board=BoardState(),
        target_id="ogre",
    ) == ()
    with pytest.raises(ValueError, match="jest za duży.*najwyżej rozmiaru średni"):
        service.prepare(
            state=state,
            board=BoardState(),
            target_id="ogre",
            mode=ShoveMode.PRONE,
        )


def test_successful_shove_can_apply_prone_and_consumes_action() -> None:
    service = CombatShoveFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 1), strength=16, skills=("athletics",))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(2, 1), dexterity=14, skills=("acrobatics",))
    state = _state(hero, goblin)
    pending = service.prepare(state=state, board=BoardState(), target_id="goblin", mode=ShoveMode.PRONE)

    result = service.resolve(
        state=state,
        board=BoardState(),
        pending=pending,
        attacker_natural_roll=12,
        defender_natural_roll=5,
    )

    assert result.succeeded
    assert has_condition(result.state.condition_states, "goblin", CombatCondition.PRONE)
    assert result.state.turn_action.action_use.value == "action_used"


def test_shove_replaces_only_one_attack_for_extra_attack_actor() -> None:
    service = CombatShoveFlowService()
    hero = replace(
        _actor("hero", Faction.ALLY, Coordinate(1, 1), strength=16, skills=("athletics",)),
        attacks_per_action=2,
    )
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(2, 1))
    state = _state(hero, goblin)
    pending = service.prepare(
        state=state,
        board=BoardState(),
        target_id="goblin",
        mode=ShoveMode.PRONE,
    )

    result = service.resolve(
        state=state,
        board=BoardState(),
        pending=pending,
        attacker_natural_roll=20,
        defender_natural_roll=1,
    )

    assert result.state.turn_action.attacks_used == 1
    assert result.state.turn_action.attacks_maximum == 2
    assert service.available_modes(
        state=result.state,
        board=BoardState(),
        target_id="goblin",
    )


def test_tied_shove_preserves_target_state_but_consumes_action() -> None:
    service = CombatShoveFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 1), strength=16, skills=("athletics",))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(2, 1), dexterity=14, skills=("acrobatics",))
    state = _state(hero, goblin)
    pending = service.prepare(state=state, board=BoardState(), target_id="goblin", mode=ShoveMode.PRONE)

    result = service.resolve(
        state=state,
        board=BoardState(),
        pending=pending,
        attacker_natural_roll=4,
        defender_natural_roll=5,
    )

    assert not result.succeeded
    assert not has_condition(result.state.condition_states, "goblin", CombatCondition.PRONE)
    assert result.state.turn_action.action_use.value == "action_used"
    assert "Remis" in result.message_body


def test_successful_push_moves_target_one_tile_directly_away() -> None:
    service = CombatShoveFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 1), strength=16, skills=("athletics",))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(2, 1))
    state = _state(hero, goblin)
    pending = service.prepare(state=state, board=BoardState(), target_id="goblin", mode=ShoveMode.PUSH)

    result = service.resolve(
        state=state,
        board=BoardState(),
        pending=pending,
        attacker_natural_roll=15,
        defender_natural_roll=5,
    )

    moved = next(actor for actor in result.state.actors if str(actor.id) == "goblin")
    assert moved.position == Coordinate(3, 1)


def test_push_is_not_available_when_destination_is_blocked() -> None:
    service = CombatShoveFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 1), strength=16)
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(2, 1))
    board = BoardState()
    board.set_terrain(Coordinate(3, 1), BLOCKING_TERRAIN)

    modes = service.available_modes(
        state=_state(hero, goblin),
        board=board,
        target_id="goblin",
    )

    assert modes == (ShoveMode.PRONE,)
