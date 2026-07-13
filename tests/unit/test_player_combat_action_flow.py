from random import Random

import pytest

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.application import PlayerCombatActionFlowService
from dnd_board_game.combat import (
    ActionUse,
    ActiveCombatEffect,
    AttackSource,
    AttackSourceType,
    CombatState,
    HealingSource,
    HealingSourceType,
    InitiativeEntry,
    InitiativeOrder,
    current_actor,
    start_combat,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.world import BoardState, Coordinate


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
    order = InitiativeOrder(
        tuple(
            InitiativeEntry(
                actor,
                resolve_d20_roll(D20RollInput(D20RollRequest(), 20 - index)),
                2,
                index,
            )
            for index, actor in enumerate(actors)
        )
    )
    return start_combat(tuple(actors), order)


def _source() -> AttackSource:
    return AttackSource(
        name="Miecz",
        source_type=AttackSourceType.WEAPON,
        range_feet=5,
        attack_roll_request=D20RollRequest(),
        damage_hint="1d8",
        damage_type="slashing",
        id="sword",
    )


def test_source_selection_validates_active_hero_and_preserves_event_contract() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    state = _state(hero, enemy)

    attack = service.select_attack_source(
        state=state,
        sources=(_source(),),
        source_id="sword",
    )
    healing = service.select_healing_source(
        state=state,
        sources=(
            HealingSource(
                id="heal",
                name="Leczenie ran",
                source_type=HealingSourceType.SPELL,
                range_feet=5,
            ),
        ),
        source_id="heal",
    )

    assert attack.actor_id == "hero"
    assert attack.event_type == "ui_combat_attack_source_selected"
    assert dict(attack.event_payload) == {"actor_id": "hero", "source_id": "sword"}
    assert healing.event_type == "ui_combat_healing_source_selected"

    with pytest.raises(ValueError, match="Nieznane źródło ataku"):
        service.select_attack_source(state=state, sources=(_source(),), source_id="missing")
    with pytest.raises(ValueError, match="To nie jest tura bohatera"):
        service.select_attack_source(
            state=_state(enemy, hero),
            sources=(_source(),),
            source_id="sword",
        )


def test_staged_attack_moves_from_target_preview_through_damage() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    state = _state(hero, enemy)
    source = _source()
    penalty = ActiveCombatEffect(
        id="penalty",
        actor_id="hero",
        kind="grant_next_attack_penalty",
        label="Kara",
        object_id="test:penalty",
        value=-1,
    )

    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        position=enemy.position,
        active_effects=(penalty,),
    )
    assert selected.pending is not None
    assert selected.pending.stage == "confirm_attack"

    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        pending=selected.pending,
        active_effects=(penalty,),
        rng=Random(1),
    )
    assert confirmed.pending is not None
    assert confirmed.pending.stage == "attack_roll"

    rolled = service.submit_attack_roll(
        state=state,
        board=BoardState(),
        source=source,
        pending=confirmed.pending,
        active_effects=(penalty,),
        natural_roll=20,
    )
    assert rolled.pending is not None
    assert rolled.pending.stage == "damage_roll"
    assert rolled.pending.critical is True
    assert rolled.active_effects == ()
    assert rolled.state.turn_action.action_use == ActionUse.ACTION_USED

    damaged = service.submit_damage(
        state=rolled.state,
        source=source,
        pending=rolled.pending,
        active_effects=rolled.active_effects,
        damage=5,
    )
    updated_enemy = next(actor for actor in damaged.state.actors if actor.id == enemy.id)
    assert updated_enemy.hp == 5
    assert damaged.pending is None
    assert damaged.applied_damage is not None
    assert damaged.event_type == "ui_combat_player_damage_roll"


def test_missed_attack_spends_action_and_finishes_pending_flow() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    state = _state(hero, enemy)
    pending = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=_source(),
        position=enemy.position,
        active_effects=(),
    ).pending
    assert pending is not None
    pending = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=_source(),
        pending=pending,
        active_effects=(),
        rng=Random(1),
    ).pending
    assert pending is not None

    transition = service.submit_attack_roll(
        state=state,
        board=BoardState(),
        source=_source(),
        pending=pending,
        active_effects=(),
        natural_roll=1,
    )

    assert transition.pending is None
    assert transition.state.turn_action.action_use == ActionUse.ACTION_USED
    assert "pudłuje" in transition.message_body
    assert dict(transition.event_payload)["hit"] is False


def test_direct_attack_compatibility_transition_applies_damage() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))

    transition = service.resolve_direct_attack(
        state=_state(hero, enemy),
        board=BoardState(),
        source=_source(),
        target_id="enemy",
        active_effects=(),
        natural_roll=20,
        damage=4,
    )

    assert current_actor(transition.state).id == hero.id
    assert transition.state.turn_action.action_use == ActionUse.ACTION_USED
    assert next(actor for actor in transition.state.actors if actor.id == enemy.id).hp == 6
    assert transition.applied_damage is not None
    assert transition.event_type == "ui_combat_player_attack"
