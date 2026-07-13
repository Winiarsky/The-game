from random import Random

import pytest

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.application import EnemyTurnFlowService, EnemyTurnTransitionKind
from dnd_board_game.combat import (
    ActiveCombatEffect,
    AttackSource,
    AttackSourceType,
    CombatState,
    InitiativeEntry,
    InitiativeOrder,
    start_combat,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.world import BLOCKING_TERRAIN, BoardState, Coordinate


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
    return AttackSource(
        "Miecz",
        AttackSourceType.WEAPON,
        5,
        D20RollRequest(),
        damage_fixed=1,
    )


def test_plan_validates_enemy_turn_and_preserves_intent_event() -> None:
    service = EnemyTurnFlowService()
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(0, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 0))

    transition = service.plan(
        state=_state(enemy, hero),
        board=BoardState(),
        attack_sources_by_actor={enemy.id: _source()},
    )

    assert transition.enemy_id == "enemy"
    assert transition.intent.target is not None
    assert transition.event_type == "ui_combat_enemy_turn_intent"
    assert dict(transition.event_payload)["target_id"] == "hero"

    with pytest.raises(ValueError, match="To nie jest tura przeciwnika"):
        service.plan(
            state=_state(hero, enemy),
            board=BoardState(),
            attack_sources_by_actor={enemy.id: _source()},
        )


def test_adjacent_enemy_result_is_classified_as_attack_confirmation() -> None:
    service = EnemyTurnFlowService()
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(0, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 0))
    state = _state(enemy, hero)
    sources = {enemy.id: _source()}
    intent = service.plan(state=state, board=BoardState(), attack_sources_by_actor=sources)

    transition = service.resolve(
        state=state,
        intent=intent.intent,
        board=BoardState(),
        attack_sources_by_actor=sources,
        active_effects=(),
        rng=Random(1),
    )

    assert transition.kind == EnemyTurnTransitionKind.ATTACK
    assert transition.result.target is not None
    assert transition.result.target.id == "hero"
    assert transition.message_title == "Atak przeciwnika"


def test_enemy_approach_is_classified_as_movement_confirmation() -> None:
    service = EnemyTurnFlowService()
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(0, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(8, 0))
    state = _state(enemy, hero)
    sources = {enemy.id: _source()}
    intent = service.plan(state=state, board=BoardState(), attack_sources_by_actor=sources)

    transition = service.resolve(
        state=state,
        intent=intent.intent,
        board=BoardState(),
        attack_sources_by_actor=sources,
        active_effects=(),
        rng=Random(2),
    )

    assert transition.kind == EnemyTurnTransitionKind.MOVEMENT
    assert transition.result.movement_path is not None
    assert transition.message_title == "Ruch przeciwnika"


def test_ready_enemy_moves_trigger_uses_real_ai_movement_path() -> None:
    service = EnemyTurnFlowService()
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(0, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(4, 0))
    state = _state(enemy, hero)
    sources = {enemy.id: _source(), hero.id: _source()}
    ready = ActiveCombatEffect(
        id="ready:hero",
        actor_id="hero",
        kind="ready_attack",
        label="Ready",
        object_id="combat_action:ready:enemy_moves",
        value=0,
    )
    intent = service.plan(state=state, board=BoardState(), attack_sources_by_actor=sources)

    transition = service.resolve(
        state=state,
        intent=intent.intent,
        board=BoardState(),
        attack_sources_by_actor=sources,
        active_effects=(ready,),
        rng=Random(3),
    )

    assert transition.kind == EnemyTurnTransitionKind.READY
    assert transition.result.movement_path is not None
    assert transition.result.movement_path.origin != transition.result.movement_path.destination
    assert transition.ready_trigger is not None
    assert transition.ready_trigger.readied_actor_id == "hero"
    assert transition.ready_trigger.trigger == "enemy_moves"


def test_leaving_blocked_adjacent_hero_reach_prompts_opportunity_attack() -> None:
    service = EnemyTurnFlowService()
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    nearby_hero = _actor("nearby", Faction.ALLY, Coordinate(0, 0))
    distant_hero = _actor("distant", Faction.ALLY, Coordinate(6, 0))
    state = _state(enemy, nearby_hero, distant_hero)
    board = BoardState()
    board.add_wall(nearby_hero.position, enemy.position)
    board.set_terrain(Coordinate(0, 1), BLOCKING_TERRAIN)
    board.set_terrain(Coordinate(1, 1), BLOCKING_TERRAIN)
    sources = {
        enemy.id: _source(),
        nearby_hero.id: _source(),
        distant_hero.id: _source(),
    }
    intent = service.plan(state=state, board=board, attack_sources_by_actor=sources)

    transition = service.resolve(
        state=state,
        intent=intent.intent,
        board=board,
        attack_sources_by_actor=sources,
        active_effects=(),
        rng=Random(4),
    )

    assert transition.kind == EnemyTurnTransitionKind.OPPORTUNITY
    assert transition.threat_actor_ids == ("nearby",)
    assert transition.event_type == "ui_combat_enemy_opportunity_pending"
