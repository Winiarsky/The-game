from dataclasses import replace

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.combat import (
    ActiveCombatEffect,
    AttackSource,
    AttackSourceType,
    CombatStatus,
    InitiativeEntry,
    InitiativeOrder,
    current_actor,
    finish_turn,
    movement_remaining,
    opportunity_attackers_for_movement,
    reaction_available_for,
    replace_actor,
    start_combat,
    use_bonus_action,
    use_dash,
    use_actor_reaction,
    use_movement,
    use_reaction,
    use_turn_action,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.world import BoardState, Coordinate, find_path


def _actor(actor_id: str, faction: Faction, col: int, hp: int = 10) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id,
        ac=12,
        hp=hp,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(col, 0),
        faction=faction,
        ability_scores=AbilityScores(dexterity=14),
    )


def _order(*actors: Actor) -> InitiativeOrder:
    request = D20RollRequest()
    entries = []
    for index, actor in enumerate(actors):
        roll = resolve_d20_roll(D20RollInput(request, 20 - index))
        entries.append(InitiativeEntry(actor, roll, 2, index))
    return InitiativeOrder(tuple(entries))


def test_start_combat_selects_first_initiative_actor():
    hero = _actor("hero", Faction.ALLY, 0)
    goblin = _actor("goblin", Faction.ENEMY, 1)

    state = start_combat((hero, goblin), _order(hero, goblin))

    assert current_actor(state).id == hero.id
    assert state.round_number == 1


def test_turn_action_can_only_be_used_once():
    hero = _actor("hero", Faction.ALLY, 0)
    goblin = _actor("goblin", Faction.ENEMY, 1)
    state = start_combat((hero, goblin), _order(hero, goblin))

    first = use_turn_action(state)
    second = use_turn_action(first.state)

    assert first.accepted is True
    assert second.accepted is False
    assert "już zużyta" in second.message


def test_finish_turn_advances_actor_and_resets_action():
    hero = _actor("hero", Faction.ALLY, 0)
    goblin = _actor("goblin", Faction.ENEMY, 1)
    state = use_turn_action(start_combat((hero, goblin), _order(hero, goblin))).state

    state = finish_turn(state)

    assert current_actor(state).id == goblin.id
    assert use_turn_action(state).accepted is True
    assert movement_remaining(state, goblin) == goblin.speed_feet


def test_bonus_action_can_only_be_used_once_and_resets_on_next_turn():
    hero = _actor("hero", Faction.ALLY, 0)
    goblin = _actor("goblin", Faction.ENEMY, 1)
    state = start_combat((hero, goblin), _order(hero, goblin))

    first = use_bonus_action(state)
    second = use_bonus_action(first.state)
    next_turn = finish_turn(first.state)

    assert first.accepted is True
    assert first.state.turn_action.bonus_action_use.value == "action_used"
    assert second.accepted is False
    assert "Akcja bonusowa" in second.message
    assert next_turn.turn_action.bonus_action_use.value == "action_available"


def test_reaction_can_only_be_used_once_and_resets_on_next_turn():
    hero = _actor("hero", Faction.ALLY, 0)
    goblin = _actor("goblin", Faction.ENEMY, 1)
    state = start_combat((hero, goblin), _order(hero, goblin))

    first = use_reaction(state)
    second = use_reaction(first.state)
    next_turn = finish_turn(first.state)

    assert first.accepted is True
    assert first.state.turn_action.reaction_available is False
    assert second.accepted is False
    assert "Reakcja" in second.message
    assert next_turn.turn_action.reaction_available is True


def test_non_current_actor_reaction_tracks_until_that_actor_turn_starts():
    hero = _actor("hero", Faction.ALLY, 0)
    goblin = _actor("goblin", Faction.ENEMY, 1)
    state = start_combat((hero, goblin), _order(hero, goblin))

    spent = use_actor_reaction(state, goblin)
    repeated = use_actor_reaction(spent.state, goblin)
    goblin_turn = finish_turn(spent.state)

    assert spent.accepted is True
    assert reaction_available_for(spent.state, goblin) is False
    assert repeated.accepted is False
    assert current_actor(goblin_turn).id == goblin.id
    assert reaction_available_for(goblin_turn, goblin) is True


def test_opportunity_attack_triggers_when_leaving_enemy_melee_reach():
    hero = _actor("hero", Faction.ALLY, 0)
    goblin = _actor("goblin", Faction.ENEMY, 1)
    state = start_combat((hero, goblin), _order(hero, goblin))
    source = AttackSource("Szabla", AttackSourceType.WEAPON, 5, D20RollRequest())

    threats = opportunity_attackers_for_movement(
        state,
        hero,
        Coordinate(0, 0),
        Coordinate(-1, 0),
        {goblin.id: source},
    )

    assert [threat.attacker.id for threat in threats] == [goblin.id]


def test_opportunity_attack_detection_is_symmetric_for_hero_reactions():
    hero = _actor("hero", Faction.ALLY, 1)
    goblin = _actor("goblin", Faction.ENEMY, 0)
    state = start_combat((goblin, hero), _order(goblin, hero))
    source = AttackSource("Miecz", AttackSourceType.WEAPON, 5, D20RollRequest())

    threats = opportunity_attackers_for_movement(
        state,
        goblin,
        Coordinate(0, 0),
        Coordinate(-1, 0),
        {hero.id: source},
    )

    assert [threat.attacker.id for threat in threats] == [hero.id]


def test_opportunity_attack_supports_ten_foot_reach_but_not_ranged_weapons():
    hero = _actor("hero", Faction.ALLY, 0)
    reach_enemy = _actor("reach_enemy", Faction.ENEMY, 2)
    archer = _actor("archer", Faction.ENEMY, 6)
    state = start_combat((hero, reach_enemy, archer), _order(hero, reach_enemy, archer))
    reach_source = AttackSource("Halabarda", AttackSourceType.WEAPON, 10, D20RollRequest())
    ranged_source = AttackSource("Kusza", AttackSourceType.WEAPON, 80, D20RollRequest())

    threats = opportunity_attackers_for_movement(
        state,
        hero,
        Coordinate(0, 0),
        Coordinate(-1, 0),
        {reach_enemy.id: reach_source, archer.id: ranged_source},
    )

    assert [threat.attacker.id for threat in threats] == [reach_enemy.id]


def test_opportunity_attack_does_not_trigger_after_disengage():
    hero = _actor("hero", Faction.ALLY, 0)
    goblin = _actor("goblin", Faction.ENEMY, 1)
    state = start_combat((hero, goblin), _order(hero, goblin))
    source = AttackSource("Szabla", AttackSourceType.WEAPON, 5, D20RollRequest())

    threats = opportunity_attackers_for_movement(
        state,
        hero,
        Coordinate(0, 0),
        Coordinate(-1, 0),
        {goblin.id: source},
        active_effects=(
            ActiveCombatEffect(
                id="disengage-hero",
                actor_id=str(hero.id),
                kind="disengage_until_turn_end",
                label="Odwrót",
                object_id="basic_action",
                value=0,
            ),
        ),
    )

    assert threats == ()


def test_movement_before_and_after_action_uses_shared_turn_pool():
    hero = _actor("hero", Faction.ALLY, 0)
    goblin = _actor("goblin", Faction.ENEMY, 5)
    state = start_combat((hero, goblin), _order(hero, goblin))
    board = BoardState()

    first_move = use_movement(state, hero, find_path(board, hero, state.actors, Coordinate(1, 0)))
    after_action = use_turn_action(first_move.state).state
    moved_hero = next(actor for actor in after_action.actors if actor.id == hero.id)
    second_move = use_movement(after_action, moved_hero, find_path(board, moved_hero, after_action.actors, Coordinate(2, 0)))

    assert first_move.accepted is True
    assert movement_remaining(first_move.state, moved_hero) == 25
    assert second_move.accepted is True
    assert movement_remaining(second_move.state, next(actor for actor in second_move.state.actors if actor.id == hero.id)) == 20


def test_movement_cannot_exceed_remaining_speed():
    hero = _actor("hero", Faction.ALLY, 0)
    goblin = _actor("goblin", Faction.ENEMY, 10)
    state = start_combat((hero, goblin), _order(hero, goblin))
    board = BoardState()
    long_path = find_path(board, hero, state.actors, Coordinate(6, 0))

    result = use_movement(state, hero, long_path)

    assert result.accepted is True
    moved_hero = next(actor for actor in result.state.actors if actor.id == hero.id)
    too_far = use_movement(result.state, moved_hero, find_path(board, moved_hero, result.state.actors, Coordinate(7, 0)))

    assert too_far.accepted is False
    assert "Za mało ruchu" in too_far.message


def test_dash_uses_action_and_adds_extra_movement_until_turn_end():
    hero = _actor("hero", Faction.ALLY, 0)
    goblin = _actor("goblin", Faction.ENEMY, 10)
    state = start_combat((hero, goblin), _order(hero, goblin))
    board = BoardState()

    dashed = use_dash(state, hero)
    moved = use_movement(dashed.state, hero, find_path(board, replace(hero, speed_feet=60), state.actors, Coordinate(8, 0)))
    next_turn = finish_turn(dashed.state)

    assert dashed.accepted is True
    assert dashed.state.turn_action.action_use.value == "action_used"
    assert dashed.state.turn_action.extra_movement_feet == 30
    assert movement_remaining(dashed.state, hero) == 60
    assert moved.accepted is True
    assert movement_remaining(moved.state, next(actor for actor in moved.state.actors if actor.id == hero.id)) == 20
    assert next_turn.turn_action.extra_movement_feet == 0


def test_finish_turn_wraps_to_next_round():
    hero = _actor("hero", Faction.ALLY, 0)
    goblin = _actor("goblin", Faction.ENEMY, 1)
    state = start_combat((hero, goblin), _order(hero, goblin))

    state = finish_turn(finish_turn(state))

    assert current_actor(state).id == hero.id
    assert state.round_number == 2


def test_defeated_side_finishes_combat():
    hero = _actor("hero", Faction.ALLY, 0)
    goblin = _actor("goblin", Faction.ENEMY, 1)
    state = start_combat((hero, goblin), _order(hero, goblin))

    state = replace_actor(state, replace(goblin, hp=0))

    assert state.status == CombatStatus.FINISHED
    assert state.winner == Faction.ALLY
