from dataclasses import replace
from typing import Callable

import pytest

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.application import CombatReactionFlowService, PlayerReactionFlowService
from dnd_board_game.combat import (
    ActiveCombatEffect,
    AttackSource,
    AttackSourceType,
    CombatState,
    EnemyAutoTurnResult,
    InitiativeEntry,
    InitiativeOrder,
    reaction_available_for,
    replace_actor,
    start_combat,
    use_actor_reaction,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.world import BoardState, Coordinate, PathResult, find_path


def _actor(
    actor_id: str,
    faction: Faction,
    position: Coordinate,
    *,
    hp: int = 10,
) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id.title(),
        ac=12,
        hp=hp,
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


def _source(*, damage_fixed: int = 3) -> AttackSource:
    return AttackSource(
        "Miecz",
        AttackSourceType.WEAPON,
        5,
        D20RollRequest(),
        damage_fixed=damage_fixed,
    )


def _path(state: CombatState, actor: Actor) -> PathResult:
    return find_path(BoardState(), actor, state.actors, Coordinate(0, 2))


def _roll(natural_roll: int) -> Callable[[D20RollRequest], D20RollInput]:
    return lambda request: D20RollInput(request, natural_roll)


def test_missed_opportunity_attack_consumes_reaction_then_moves() -> None:
    service = CombatReactionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    state = _state(hero, goblin)

    resolution = service.resolve_opportunity_movement(
        state=state,
        actor_id="hero",
        path=_path(state, hero),
        threat_actor_ids=("goblin",),
        attack_sources_by_actor={goblin.id: _source()},
        active_effects=(),
        roll_d20=_roll(1),
        roll_damage=lambda _sides: 1,
    )

    moved = next(actor for actor in resolution.state.actors if actor.id == hero.id)
    updated_goblin = next(actor for actor in resolution.state.actors if actor.id == goblin.id)
    assert moved.position == Coordinate(0, 2)
    assert moved.hp == 10
    assert resolution.movement_performed
    assert not reaction_available_for(resolution.state, updated_goblin)
    assert "pudło" in resolution.message_body


def test_hit_applies_damage_and_completes_movement() -> None:
    service = CombatReactionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    state = _state(hero, goblin)

    resolution = service.resolve_opportunity_movement(
        state=state,
        actor_id="hero",
        path=_path(state, hero),
        threat_actor_ids=("goblin",),
        attack_sources_by_actor={goblin.id: _source()},
        active_effects=(),
        roll_d20=_roll(20),
        roll_damage=lambda _sides: 1,
    )

    moved = next(actor for actor in resolution.state.actors if actor.id == hero.id)
    assert moved.position == Coordinate(0, 2)
    assert moved.hp == 7
    assert len(resolution.applied_damages) == 1
    assert "trafienie" in resolution.message_body


def test_lethal_opportunity_attack_stops_movement() -> None:
    service = CombatReactionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0), hp=3)
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    state = _state(hero, goblin)

    resolution = service.resolve_opportunity_movement(
        state=state,
        actor_id="hero",
        path=_path(state, hero),
        threat_actor_ids=("goblin",),
        attack_sources_by_actor={goblin.id: _source()},
        active_effects=(),
        roll_d20=_roll(20),
        roll_damage=lambda _sides: 1,
    )

    defeated = next(actor for actor in resolution.state.actors if actor.id == hero.id)
    assert defeated.position == Coordinate(0, 0)
    assert defeated.hp == 0
    assert not resolution.movement_performed
    assert "pada przed wykonaniem ruchu" in resolution.message_body


def test_spent_or_missing_threat_is_skipped_and_movement_still_happens() -> None:
    service = CombatReactionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    state = _state(hero, goblin)
    state = use_actor_reaction(state, goblin).state

    resolution = service.resolve_opportunity_movement(
        state=state,
        actor_id="hero",
        path=_path(state, hero),
        threat_actor_ids=("missing", "goblin"),
        attack_sources_by_actor={goblin.id: _source()},
        active_effects=(),
        roll_d20=lambda _request: pytest.fail("No attack roll expected."),
        roll_damage=lambda _sides: pytest.fail("No damage roll expected."),
    )

    moved = next(actor for actor in resolution.state.actors if actor.id == hero.id)
    assert moved.position == Coordinate(0, 2)
    assert resolution.applied_damages == ()


def test_unknown_mover_is_rejected() -> None:
    service = CombatReactionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    state = _state(hero, goblin)

    with pytest.raises(ValueError, match="Aktor oczekującego ruchu nie istnieje"):
        service.resolve_opportunity_movement(
            state=state,
            actor_id="missing",
            path=_path(state, hero),
            threat_actor_ids=("goblin",),
            attack_sources_by_actor={goblin.id: _source()},
            active_effects=(),
            roll_d20=_roll(20),
            roll_damage=lambda _sides: 1,
        )


def test_player_reaction_roll_consumes_reaction_and_reports_miss() -> None:
    service = PlayerReactionFlowService()
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    state = _state(goblin, hero)

    resolution = service.resolve_attack_roll(
        state=state,
        attacker_id="hero",
        target_id="goblin",
        attack_sources_by_actor={hero.id: _source()},
        active_effects=(),
        natural_roll=1,
    )

    updated_hero = next(actor for actor in resolution.state.actors if actor.id == hero.id)
    assert not reaction_available_for(resolution.state, updated_hero)
    assert not resolution.hit
    assert resolution.attack_roll.natural_roll == 1
    assert "pudłuje" in resolution.message


def test_ready_reaction_consumes_ready_and_next_attack_effects() -> None:
    service = PlayerReactionFlowService()
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    state = _state(goblin, hero)
    ready = ActiveCombatEffect(
        id="ready:hero",
        actor_id="hero",
        kind="ready_attack",
        label="Ready",
        object_id="combat_action:ready:enemy_moves",
        value=0,
    )
    penalty = ActiveCombatEffect(
        id="penalty:hero",
        actor_id="hero",
        kind="grant_next_attack_penalty",
        label="Kara",
        object_id="rubble",
        value=-2,
    )

    resolution = service.resolve_attack_roll(
        state=state,
        attacker_id="hero",
        target_id="goblin",
        attack_sources_by_actor={hero.id: _source()},
        active_effects=(ready, penalty),
        natural_roll=20,
        consumed_effect_id=ready.id,
    )

    assert resolution.hit
    assert resolution.critical
    assert resolution.active_effects == ()


def test_player_reaction_damage_updates_target_and_clamps_negative_input() -> None:
    service = PlayerReactionFlowService()
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    state = _state(goblin, hero)

    damaged = service.apply_damage(
        state=state,
        attacker_id="hero",
        target_id="goblin",
        attack_sources_by_actor={hero.id: _source()},
        active_effects=(),
        damage=4,
    )
    unchanged = service.apply_damage(
        state=state,
        attacker_id="hero",
        target_id="goblin",
        attack_sources_by_actor={hero.id: _source()},
        active_effects=(),
        damage=-5,
    )

    assert damaged.applied_damage.hp_after == 6
    assert unchanged.applied_damage.damage.total_applied == 0


def test_ready_trigger_detection_uses_enemy_movement_and_legal_range() -> None:
    service = PlayerReactionFlowService()
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(2, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    state = _state(goblin, hero)
    moved_goblin = replace(goblin, position=Coordinate(1, 0))
    path = find_path(BoardState(), goblin, state.actors, moved_goblin.position)
    enemy_result = EnemyAutoTurnResult(
        state=replace_actor(state, moved_goblin),
        enemy=goblin,
        target=None,
        message="Goblin rusza się.",
        movement_path=path,
        moved_enemy=moved_goblin,
    )
    ready = ActiveCombatEffect(
        id="ready:hero",
        actor_id="hero",
        kind="ready_attack",
        label="Ready",
        object_id="combat_action:ready:enemy_moves",
        value=0,
    )

    trigger = service.detect_ready_attack(
        state=state,
        enemy_result=enemy_result,
        board=BoardState(),
        attack_sources_by_actor={hero.id: _source()},
        active_effects=(ready,),
    )

    assert trigger is not None
    assert trigger.readied_actor_id == "hero"
    assert trigger.target_id == "goblin"
    assert trigger.trigger == "enemy_moves"
