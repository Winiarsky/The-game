from random import Random

import pytest

from dataclasses import replace

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    CreatureSize,
    DamageAffinityProfile,
    Faction,
    FeatureGrant,
    FeatureSourceKind,
)
from dnd_board_game.application import EnemyTurnFlowService, EnemyTurnTransitionKind
from dnd_board_game.combat import (
    ActiveCombatEffect,
    AttackKind,
    AttackSource,
    AttackSourceType,
    CombatState,
    InitiativeEntry,
    InitiativeOrder,
    DamageType,
    start_combat,
)
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    RollModifier,
    RollModifierType,
    resolve_d20_roll,
)
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


def test_large_enemy_attack_opens_giant_killer_reaction_for_adjacent_ranger() -> None:
    service = EnemyTurnFlowService()
    enemy = replace(
        _actor("enemy", Faction.ENEMY, Coordinate(0, 0)),
        size=CreatureSize.LARGE,
    )
    ranger = replace(
        _actor("ranger", Faction.ALLY, Coordinate(1, 0)),
        features=(
            FeatureGrant(
                "giant_killer",
                "Giant Killer",
                FeatureSourceKind.SUBCLASS,
                "hunter",
            ),
        ),
    )
    state = _state(enemy, ranger)
    sources = {enemy.id: _source(), ranger.id: _source()}
    intent = service.plan(
        state=state,
        board=BoardState(),
        attack_sources_by_actor=sources,
    )

    transition = service.resolve(
        state=state,
        intent=intent.intent,
        board=BoardState(),
        attack_sources_by_actor=sources,
        active_effects=(),
        rng=Random(2),
    )

    assert transition.kind == EnemyTurnTransitionKind.REACTION
    assert transition.reaction_window is not None
    option = transition.reaction_window.current_option
    assert option.kind.value == "ready_attack"
    assert option.effect_id == "giant_killer"
    assert option.trigger_event == "giant_killer"


def test_enemy_multiattack_uses_next_data_driven_source() -> None:
    service = EnemyTurnFlowService()
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(0, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 0))
    first_source = replace(_source(), name="Pierwszy", id="first")
    second_source = replace(_source(), name="Drugi", id="second")
    sources = {enemy.id: first_source}
    sequence = {enemy.id: (first_source, second_source)}
    state = _state(enemy, hero)

    first_intent = service.plan(
        state=state,
        board=BoardState(),
        attack_sources_by_actor=sources,
        multiattack_sources_by_actor=sequence,
    )
    first = service.resolve(
        state=state,
        intent=first_intent.intent,
        board=BoardState(),
        attack_sources_by_actor=sources,
        multiattack_sources_by_actor=sequence,
        active_effects=(),
        rng=Random(1),
    )
    second_intent = service.plan(
        state=first.result.state,
        board=BoardState(),
        attack_sources_by_actor=sources,
        multiattack_sources_by_actor=sequence,
    )
    second = service.resolve(
        state=first.result.state,
        intent=second_intent.intent,
        board=BoardState(),
        attack_sources_by_actor=sources,
        multiattack_sources_by_actor=sequence,
        active_effects=(),
        rng=Random(2),
    )

    assert first.result.source is not None and first.result.source.id == "first"
    assert first.result.state.turn_action.attacks_used == 1
    assert second.result.source is not None and second.result.source.id == "second"
    assert second.result.state.turn_action.attacks_used == 2


def test_enemy_save_flow_applies_manual_roll_then_damage_affinity() -> None:
    service = EnemyTurnFlowService()
    enemy = _actor("guardian", Faction.ENEMY, Coordinate(0, 0))
    hero = replace(
        _actor("hero", Faction.ALLY, Coordinate(1, 0)),
        damage_affinities=DamageAffinityProfile(resistances=(DamageType.SLASHING,)),
    )
    state = _state(enemy, hero)
    source = replace(
        _source(),
        name="Kamienny podmuch",
        damage_fixed=8,
        damage_type="slashing",
        save_ability="dexterity",
        save_dc=12,
        save_damage_on_success="half",
    )
    sources = {enemy.id: source}
    intent = service.plan(state=state, board=BoardState(), attack_sources_by_actor=sources)
    pending = service.resolve(
        state=state,
        intent=intent.intent,
        board=BoardState(),
        attack_sources_by_actor=sources,
        active_effects=(),
        rng=Random(1),
    )

    resolved = service.resolve_player_saving_throw(
        result=pending.result,
        natural_roll=10,
    )

    assert pending.result.saving_throw_request is not None
    assert pending.message_title == "Efekt przeciwnika"
    assert resolved.saving_throw.success is True  # 10 + DEX 2 = ST 12
    assert resolved.result.damage is not None
    assert resolved.result.damage.total_before_reduction == 4  # save halves first
    assert resolved.result.damage.total_applied == 2  # resistance halves again
    assert resolved.result.updated_target is not None
    assert resolved.result.updated_target.hp == 8


def test_enemy_save_flow_accepts_bardic_inspiration_modifier() -> None:
    service = EnemyTurnFlowService()
    enemy = _actor("guardian", Faction.ENEMY, Coordinate(0, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 0))
    state = _state(enemy, hero)
    source = replace(
        _source(),
        damage_fixed=8,
        save_ability="dexterity",
        save_dc=15,
        save_damage_on_success="half",
    )
    sources = {enemy.id: source}
    intent = service.plan(
        state=state,
        board=BoardState(),
        attack_sources_by_actor=sources,
    )
    pending = service.resolve(
        state=state,
        intent=intent.intent,
        board=BoardState(),
        attack_sources_by_actor=sources,
        active_effects=(),
        rng=Random(1),
    )

    resolved = service.resolve_player_saving_throw(
        result=pending.result,
        natural_roll=10,
        additional_modifiers=(
            RollModifier(
                "Bardic Inspiration k6",
                3,
                RollModifierType.FEATURE,
                stacking_key="bardic_inspiration",
            ),
        ),
    )

    assert resolved.saving_throw.success is True
    assert resolved.saving_throw.total == 15


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

    assert transition.kind == EnemyTurnTransitionKind.REACTION
    assert transition.result.movement_path is not None
    assert transition.result.movement_path.origin != transition.result.movement_path.destination
    assert transition.reaction_window is not None
    assert transition.reaction_window.current_option.kind.value == "ready_attack"
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

    assert transition.kind == EnemyTurnTransitionKind.REACTION
    assert transition.reaction_window is not None
    assert transition.reaction_window.current_option.kind.value == "opportunity_attack"
    assert transition.threat_actor_ids == ("nearby",)
    assert transition.event_type == "ui_combat_enemy_opportunity_pending"


def test_enemy_movement_collects_ready_and_opportunity_into_one_ordered_window() -> None:
    service = EnemyTurnFlowService()
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    nearby_hero = _actor("nearby", Faction.ALLY, Coordinate(0, 0))
    ranged_hero = _actor("ranged", Faction.ALLY, Coordinate(6, 0))
    state = _state(enemy, nearby_hero, ranged_hero)
    board = BoardState()
    board.add_wall(nearby_hero.position, enemy.position)
    board.set_terrain(Coordinate(0, 1), BLOCKING_TERRAIN)
    board.set_terrain(Coordinate(1, 1), BLOCKING_TERRAIN)
    ranged_source = replace(
        _source(),
        range_feet=30,
        attack_kind=AttackKind.RANGED,
    )
    sources = {
        enemy.id: _source(),
        nearby_hero.id: _source(),
        ranged_hero.id: ranged_source,
    }
    ready = ActiveCombatEffect(
        id="ready:ranged",
        actor_id="ranged",
        kind="ready_attack",
        label="Ready",
        object_id="combat_action:ready:enemy_moves",
        value=0,
    )
    intent = service.plan(
        state=state,
        board=board,
        attack_sources_by_actor=sources,
    )

    transition = service.resolve(
        state=state,
        intent=intent.intent,
        board=board,
        attack_sources_by_actor=sources,
        active_effects=(ready,),
        rng=Random(4),
    )

    assert transition.kind == EnemyTurnTransitionKind.REACTION
    assert transition.reaction_window is not None
    assert [
        option.kind.value for option in transition.reaction_window.options
    ] == ["ready_attack", "opportunity_attack"]
    assert [
        option.reactor_actor_id for option in transition.reaction_window.options
    ] == ["ranged", "nearby"]
