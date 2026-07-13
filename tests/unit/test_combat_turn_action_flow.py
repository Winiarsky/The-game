import pytest

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.application import CombatTurnActionFlowService
from dnd_board_game.combat import (
    AttackSource,
    AttackSourceType,
    CombatState,
    InitiativeEntry,
    InitiativeOrder,
    start_combat,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.world import Coordinate


def _actor(actor_id: str, faction: Faction, position: Coordinate) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id.title(),
        ac=12,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
        ability_scores=AbilityScores(dexterity=14),
    )


def _state(*actors: Actor) -> CombatState:
    request = D20RollRequest()
    order = InitiativeOrder(
        tuple(
            InitiativeEntry(
                actor,
                resolve_d20_roll(D20RollInput(request, 20 - index)),
                2,
                index,
            )
            for index, actor in enumerate(actors)
        )
    )
    return start_combat(tuple(actors), order)


def _source() -> AttackSource:
    return AttackSource("Miecz", AttackSourceType.WEAPON, 5, D20RollRequest())


def test_dash_consumes_action_and_extends_movement() -> None:
    service = CombatTurnActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(4, 0))

    transition = service.use_dash(state=_state(hero, goblin), active_effects=())

    assert transition.state.turn_action.action_use.value == "action_used"
    assert transition.state.turn_action.extra_movement_feet == 30
    assert dict(transition.event_payload) == {
        "actor_id": "hero",
        "extra_movement_feet": 30,
    }


def test_dodge_and_disengage_create_explicit_turn_effects() -> None:
    service = CombatTurnActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(4, 0))
    state = _state(hero, goblin)

    dodged = service.use_dodge(state=state, active_effects=())
    disengaged = service.use_disengage(state=state, active_effects=())

    assert dodged.active_effects[0].kind == "dodge_until_next_turn"
    assert dodged.state.turn_action.action_use.value == "action_used"
    assert disengaged.active_effects[0].kind == "disengage_until_turn_end"
    assert disengaged.state.turn_action.action_use.value == "action_used"


def test_help_preparation_and_confirmation_create_advantage_effect() -> None:
    service = CombatTurnActionFlowService()
    helper = _actor("helper", Faction.ALLY, Coordinate(0, 0))
    ally = _actor("ally", Faction.ALLY, Coordinate(0, 1))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    state = _state(helper, ally, goblin)

    preparation = service.prepare_help(state=state)
    confirmed = service.confirm_help(
        state=state,
        active_effects=(),
        helper_id=preparation.helper_id,
        ally_ids=preparation.ally_ids,
        target_ids=preparation.target_ids,
        ally_id="ally",
        target_id="goblin",
    )

    assert preparation.ally_ids == ("ally",)
    assert preparation.target_ids == ("goblin",)
    effect = confirmed.active_effects[0]
    assert effect.kind == "help_attack_advantage"
    assert effect.actor_id == "ally"
    assert effect.target_actor_id == "goblin"


def test_ready_preparation_and_confirmation_create_trigger_effect() -> None:
    service = CombatTurnActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(4, 0))
    state = _state(hero, goblin)

    preparation = service.prepare_ready(
        state=state,
        attack_sources_by_actor={hero.id: _source()},
    )
    confirmed = service.confirm_ready(
        state=state,
        active_effects=(),
        actor_id=preparation.actor_id,
        triggers=preparation.triggers,
        trigger="enemy_moves",
    )

    assert preparation.triggers == ("enemy_moves", "enemy_attacks")
    assert confirmed.active_effects[0].kind == "ready_attack"
    assert confirmed.active_effects[0].object_id == "combat_action:ready:enemy_moves"
    assert confirmed.state.turn_action.action_use.value == "action_used"


def test_actions_reject_enemy_turn_and_missing_help_targets() -> None:
    service = CombatTurnActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(4, 0))

    with pytest.raises(ValueError, match="To nie jest tura bohatera"):
        service.use_dash(state=_state(goblin, hero), active_effects=())

    with pytest.raises(ValueError, match="Brak żywego sojusznika"):
        service.prepare_help(state=_state(hero, goblin))
