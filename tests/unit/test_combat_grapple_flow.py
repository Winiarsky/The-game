from dataclasses import replace

import pytest

from dnd_board_game.actors import AbilityScores, Actor, ActorId, CreatureSize, Faction, ProficiencyProfile
from dnd_board_game.application import CombatGrappleFlowService, GrappleMode
from dnd_board_game.combat import (
    CombatCondition,
    ConditionState,
    effective_movement_speed,
    InitiativeEntry,
    InitiativeOrder,
    grappled_by,
    has_condition,
    movement_remaining,
    path_with_condition_cost,
    replace_actor,
    start_combat,
    use_dash,
    use_movement,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.inventory import InventoryItem
from dnd_board_game.world import BoardState, Coordinate, find_path


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


def _state(active: Actor, other: Actor):
    request = D20RollRequest()
    order = InitiativeOrder(
        (
            InitiativeEntry(active, resolve_d20_roll(D20RollInput(request, 20)), 0, 0),
            InitiativeEntry(other, resolve_d20_roll(D20RollInput(request, 10)), 0, 1),
        )
    )
    return start_combat((active, other), order)


def test_prepare_grapple_uses_athletics_against_best_defense() -> None:
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 1), strength=16, skills=("athletics",))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(2, 1), dexterity=14, skills=("acrobatics",))

    pending = CombatGrappleFlowService().prepare(
        state=_state(hero, goblin),
        mode=GrappleMode.START,
        target_id="goblin",
    )

    assert pending.actor_skill == "athletics"
    assert pending.opponent_skill == "acrobatics"
    assert pending.as_payload()["actor_check"]["modifier_total"] == 5
    assert pending.as_payload()["opponent_check"]["modifier_total"] == 4


def test_grapple_requires_a_free_hand() -> None:
    crossbow = InventoryItem(
        "crossbow",
        "Kusza",
        "weapon",
        hands_required=2,
    )
    hero = replace(
        _actor("hero", Faction.ALLY, Coordinate(1, 1), strength=16),
        inventory=(crossbow,),
    )
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(2, 1))
    state = _state(hero, goblin)
    service = CombatGrappleFlowService()

    assert service.can_start(state, "goblin") is False
    with pytest.raises(ValueError, match="wolnej ręki"):
        service.prepare(state=state, mode=GrappleMode.START, target_id="goblin")


def test_grapple_rejects_target_more_than_one_size_larger() -> None:
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 1), size=CreatureSize.MEDIUM)
    giant = _actor("giant", Faction.ENEMY, Coordinate(2, 1), size=CreatureSize.HUGE)
    state = _state(hero, giant)
    service = CombatGrappleFlowService()

    assert not service.can_start(state, "giant")
    with pytest.raises(ValueError, match="jest za duży.*najwyżej rozmiaru duży"):
        service.prepare(state=state, mode=GrappleMode.START, target_id="giant")


def test_grapple_allows_target_exactly_one_size_larger() -> None:
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 1), size=CreatureSize.MEDIUM)
    ogre = _actor("ogre", Faction.ENEMY, Coordinate(2, 1), size=CreatureSize.LARGE)

    assert CombatGrappleFlowService().can_start(_state(hero, ogre), "ogre")


def test_one_handed_weapon_leaves_a_hand_free_for_grapple() -> None:
    sword = InventoryItem("sword", "Miecz", "weapon")
    hero = replace(
        _actor("hero", Faction.ALLY, Coordinate(1, 1), strength=16),
        inventory=(sword,),
    )
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(2, 1))
    state = _state(hero, goblin)

    assert CombatGrappleFlowService().can_start(state, "goblin") is True


def test_successful_grapple_applies_sourced_condition_and_consumes_action() -> None:
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 1), strength=16, skills=("athletics",))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(2, 1), dexterity=14)
    state = _state(hero, goblin)
    service = CombatGrappleFlowService()
    pending = service.prepare(state=state, mode=GrappleMode.START, target_id="goblin")

    result = service.resolve(
        state=state,
        pending=pending,
        actor_natural_roll=15,
        opponent_natural_roll=5,
    )

    assert result.succeeded
    assert has_condition(result.state.condition_states, "goblin", CombatCondition.GRAPPLED)
    assert grappled_by(result.state.condition_states, "goblin") == "hero"
    assert result.state.turn_action.action_use.value == "action_used"


def test_tied_grapple_fails_but_still_consumes_action() -> None:
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 1), strength=14)
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(2, 1), strength=14)
    state = _state(hero, goblin)
    service = CombatGrappleFlowService()
    pending = service.prepare(state=state, mode=GrappleMode.START, target_id="goblin")

    result = service.resolve(
        state=state,
        pending=pending,
        actor_natural_roll=10,
        opponent_natural_roll=10,
    )

    assert not result.succeeded
    assert not has_condition(result.state.condition_states, "goblin", CombatCondition.GRAPPLED)
    assert result.state.turn_action.action_use.value == "action_used"
    assert "Remis" in result.message_body


def test_grappled_hero_can_escape_with_better_skill() -> None:
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 1), dexterity=16, skills=("acrobatics",))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(2, 1), strength=12, skills=("athletics",))
    state = replace(
        _state(hero, goblin),
        condition_states=(ConditionState("hero", CombatCondition.GRAPPLED, "goblin"),),
    )
    service = CombatGrappleFlowService()
    pending = service.prepare(state=state, mode=GrappleMode.ESCAPE)

    result = service.resolve(
        state=state,
        pending=pending,
        actor_natural_roll=15,
        opponent_natural_roll=5,
    )

    assert pending.actor_skill == "acrobatics"
    assert result.succeeded
    assert grappled_by(result.state.condition_states, "hero") is None


def test_grapple_sets_target_movement_to_zero() -> None:
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 1))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(2, 1))
    state = replace(
        _state(hero, goblin),
        condition_states=(ConditionState("hero", CombatCondition.GRAPPLED, "goblin"),),
    )
    path = find_path(BoardState(), hero, state.actors, Coordinate(1, 2))

    adjusted = path_with_condition_cost(
        path,
        state.condition_states,
        "hero",
        movement_budget_feet=30,
    )

    assert movement_remaining(state, hero) == 0
    assert not adjusted.valid


def test_grappler_drags_target_with_halved_speed_into_previous_tile() -> None:
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 1))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(2, 1))
    state = replace(
        _state(hero, goblin),
        condition_states=(ConditionState("goblin", CombatCondition.GRAPPLED, "hero"),),
    )
    path = find_path(BoardState(), hero, state.actors, Coordinate(1, 2))
    path = path_with_condition_cost(
        path,
        state.condition_states,
        "hero",
        movement_budget_feet=30,
    )

    moved = use_movement(state, hero, path)

    moved_hero = next(actor for actor in moved.state.actors if str(actor.id) == "hero")
    moved_goblin = next(actor for actor in moved.state.actors if str(actor.id) == "goblin")
    assert moved.accepted
    assert effective_movement_speed(hero, state.condition_states) == 15
    assert path.cost_feet == 5
    assert moved.movement_remaining_feet == 10
    assert moved_hero.position == Coordinate(1, 2)
    assert moved_goblin.position == Coordinate(1, 1)
    assert grappled_by(moved.state.condition_states, "goblin") == "hero"


def test_dash_uses_halved_grappling_speed() -> None:
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 1))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(2, 1))
    state = replace(
        _state(hero, goblin),
        condition_states=(ConditionState("goblin", CombatCondition.GRAPPLED, "hero"),),
    )

    dashed = use_dash(state, hero)

    assert dashed.accepted
    assert dashed.state.turn_action.extra_movement_feet == 15
    assert movement_remaining(dashed.state, hero) == 30


def test_grapple_ends_when_grappler_is_defeated() -> None:
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 1))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(2, 1))
    state = replace(
        _state(hero, goblin),
        condition_states=(ConditionState("goblin", CombatCondition.GRAPPLED, "hero"),),
    )

    updated = replace_actor(state, replace(hero, hp=0))

    assert grappled_by(updated.condition_states, "goblin") is None


def test_grapple_ends_when_forced_movement_separates_the_pair() -> None:
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 1))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(2, 1))
    state = replace(
        _state(hero, goblin),
        condition_states=(ConditionState("goblin", CombatCondition.GRAPPLED, "hero"),),
    )

    updated = replace_actor(state, replace(goblin, position=Coordinate(3, 1)))

    assert grappled_by(updated.condition_states, "goblin") is None
