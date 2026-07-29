from dataclasses import replace

from dnd_board_game.actors import AbilityScores, Actor, ActorId, DeathSaveState, Faction
from dnd_board_game.combat import (
    ActionEconomyCost,
    ActiveCombatEffect,
    AttackSource,
    AttackSourceType,
    CombatStatus,
    CombatCondition,
    ConditionState,
    InitiativeEntry,
    InitiativeOrder,
    current_actor,
    drop_weapon,
    equip_weapon,
    expend_thrown_weapon,
    finish_turn,
    movement_remaining,
    pickup_dropped_weapon,
    opportunity_attackers_for_movement,
    reaction_available_for,
    replace_actor,
    start_combat,
    attack_action_remaining,
    can_use_attack_action,
    stow_weapon,
    use_bonus_action,
    use_action_economy_cost,
    use_dash,
    use_actor_reaction,
    use_movement,
    use_object_interaction,
    use_reaction,
    use_turn_action,
    use_attack_action,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.inventory import HandSlot, InventoryItem
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


def test_thrown_weapon_leaves_inventory_hand_and_can_be_recovered() -> None:
    hero = replace(
        _actor("hero", Faction.ALLY, 0),
        inventory=(
            InventoryItem(
                "javelin",
                "Oszczep",
                "weapon",
                equipped=True,
                hands_required=1,
                held_in=(HandSlot.MAIN_HAND,),
            ),
        ),
    )
    goblin = _actor("goblin", Faction.ENEMY, 2)
    state = start_combat((hero, goblin), _order(hero, goblin))

    thrown = expend_thrown_weapon(
        state,
        str(hero.id),
        "javelin",
        goblin.position,
    )

    updated = next(actor for actor in thrown.actors if actor.id == hero.id)
    assert updated.inventory[0].quantity == 0
    assert updated.inventory[0].equipped is False
    assert thrown.dropped_weapons[0].weapon.quantity == 1
    assert thrown.dropped_weapons[0].position == goblin.position


def test_start_combat_carries_known_exploration_conditions() -> None:
    hero = _actor("hero", Faction.ALLY, 0)
    goblin = _actor("goblin", Faction.ENEMY, 1)

    state = start_combat(
        (hero, goblin),
        _order(hero, goblin),
        condition_states=(
            ConditionState("hero", CombatCondition.PRONE),
            ConditionState("someone_else", CombatCondition.PRONE),
        ),
    )

    assert state.condition_states == (
        ConditionState("hero", CombatCondition.PRONE),
    )


def test_turn_action_can_only_be_used_once():
    hero = _actor("hero", Faction.ALLY, 0)
    goblin = _actor("goblin", Faction.ENEMY, 1)
    state = start_combat((hero, goblin), _order(hero, goblin))

    first = use_turn_action(state)
    second = use_turn_action(first.state)

    assert first.accepted is True
    assert second.accepted is False
    assert "już zużyta" in second.message


def test_attack_action_budget_allows_multiple_attacks_and_resets_next_turn():
    hero = replace(_actor("hero", Faction.ALLY, 0), attacks_per_action=2)
    goblin = _actor("goblin", Faction.ENEMY, 1)
    state = start_combat((hero, goblin), _order(hero, goblin))

    first = use_attack_action(state, hero)
    second = use_attack_action(first.state, hero)
    third = use_attack_action(second.state, hero)

    assert first.accepted is True
    assert first.state.turn_action.action_use.value == "action_used"
    assert attack_action_remaining(first.state, hero) == 1
    assert can_use_attack_action(first.state, hero) is True
    assert second.accepted is True
    assert attack_action_remaining(second.state, hero) == 0
    assert third.accepted is False
    assert finish_turn(second.state).turn_action.attack_action_active is False


def test_attack_action_does_not_unlock_after_another_main_action():
    hero = replace(_actor("hero", Faction.ALLY, 0), attacks_per_action=2)
    goblin = _actor("goblin", Faction.ENEMY, 1)
    state = use_turn_action(start_combat((hero, goblin), _order(hero, goblin))).state

    result = use_attack_action(state, hero)

    assert result.accepted is False
    assert attack_action_remaining(state, hero) == 0


def test_remaining_movement_can_be_spent_between_attacks():
    hero = replace(_actor("hero", Faction.ALLY, 0), attacks_per_action=2)
    goblin = _actor("goblin", Faction.ENEMY, 4)
    board = BoardState()
    state = start_combat((hero, goblin), _order(hero, goblin))
    after_first = use_attack_action(state, hero).state
    path = find_path(board, hero, after_first.actors, Coordinate(1, 0))

    movement = use_movement(after_first, hero, path)

    assert movement.accepted is True
    assert movement.movement_remaining_feet == 25
    assert can_use_attack_action(movement.state, current_actor(movement.state)) is True


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


def test_first_object_interaction_is_free_and_second_uses_action() -> None:
    hero = _actor("hero", Faction.ALLY, 0)
    goblin = _actor("goblin", Faction.ENEMY, 1)
    state = start_combat((hero, goblin), _order(hero, goblin))

    first = use_object_interaction(state)
    second = use_object_interaction(first.state)

    assert first.accepted is True
    assert first.used_action is False
    assert first.state.turn_action.object_interaction_available is False
    assert first.state.turn_action.action_use.value == "action_available"
    assert second.accepted is True
    assert second.used_action is True
    assert second.state.turn_action.action_use.value == "action_used"


def test_equipping_one_handed_weapon_uses_free_off_hand_and_object_interaction() -> None:
    sword = InventoryItem("sword", "Miecz", "weapon", equipped=True)
    axe = InventoryItem("axe", "Topór", "weapon", equipped=False)
    hero = replace(_actor("hero", Faction.ALLY, 0), inventory=(sword, axe))
    goblin = _actor("goblin", Faction.ENEMY, 1)
    state = start_combat((hero, goblin), _order(hero, goblin))

    result = equip_weapon(state, "axe")

    equipped_actor = current_actor(result.state)
    assert result.accepted is True
    assert result.used_action is False
    assert result.replaced_weapons == ()
    assert {item.id: item.equipped for item in equipped_actor.inventory} == {"sword": True, "axe": True}
    assert next(item for item in equipped_actor.inventory if item.id == "sword").held_in == (HandSlot.MAIN_HAND,)
    assert next(item for item in equipped_actor.inventory if item.id == "axe").held_in == (HandSlot.OFF_HAND,)
    assert result.state.turn_action.object_interaction_available is False
    assert result.state.turn_action.action_use.value == "action_available"


def test_weapon_swap_cannot_fit_after_free_interaction_was_already_spent() -> None:
    sword = InventoryItem("sword", "Miecz", "weapon", equipped=True)
    axe = InventoryItem("axe", "Topór", "weapon", equipped=False)
    hammer = InventoryItem("hammer", "Młot", "weapon", equipped=False)
    hero = replace(_actor("hero", Faction.ALLY, 0), inventory=(sword, axe, hammer))
    goblin = _actor("goblin", Faction.ENEMY, 1)
    state = start_combat((hero, goblin), _order(hero, goblin))

    first = equip_weapon(state, "axe")
    second = equip_weapon(first.state, "hammer")

    assert second.accepted is False
    assert "Brak darmowej interakcji" in second.message
    assert {item.id: item.equipped for item in current_actor(second.state).inventory} == {
        "sword": True,
        "axe": True,
        "hammer": False,
    }


def test_action_economy_cost_dispatches_action_bonus_and_free_costs() -> None:
    hero = _actor("hero", Faction.ALLY, 0)
    goblin = _actor("goblin", Faction.ENEMY, 1)
    state = start_combat((hero, goblin), _order(hero, goblin))

    free = use_action_economy_cost(state, ActionEconomyCost.FREE)
    bonus = use_action_economy_cost(free.state, ActionEconomyCost.BONUS_ACTION)
    action = use_action_economy_cost(bonus.state, ActionEconomyCost.ACTION)

    assert free.accepted and free.spent_cost == ActionEconomyCost.FREE
    assert bonus.accepted and bonus.state.turn_action.bonus_action_use.value == "action_used"
    assert action.accepted and action.state.turn_action.action_use.value == "action_used"


def test_dropping_equipped_weapon_is_free_and_places_it_on_current_tile() -> None:
    sword = InventoryItem("sword", "Miecz", "weapon", equipped=True)
    hero = replace(_actor("hero", Faction.ALLY, 0), inventory=(sword,))
    goblin = _actor("goblin", Faction.ENEMY, 1)
    state = start_combat((hero, goblin), _order(hero, goblin))

    result = drop_weapon(state, "sword")

    assert result.accepted is True
    assert current_actor(result.state).inventory[0].equipped is False
    assert result.dropped_weapon is not None
    assert result.dropped_weapon.position == hero.position
    assert result.state.dropped_weapons == (result.dropped_weapon,)
    assert result.state.turn_action.object_interaction_available is True
    assert result.state.turn_action.action_use.value == "action_available"


def test_stowing_weapon_uses_free_interaction_then_action() -> None:
    sword = InventoryItem("sword", "Miecz", "weapon", equipped=True)
    axe = InventoryItem("axe", "Topór", "weapon", equipped=True)
    hero = replace(_actor("hero", Faction.ALLY, 0), inventory=(sword, axe))
    goblin = _actor("goblin", Faction.ENEMY, 1)
    state = start_combat((hero, goblin), _order(hero, goblin))

    first = stow_weapon(state, "sword")
    second = stow_weapon(first.state, "axe")

    assert first.accepted and first.used_action is False
    assert second.accepted and second.used_action is True
    assert second.state.turn_action.action_use.value == "action_used"
    assert not any(item.equipped for item in current_actor(second.state).inventory)


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


def test_expeditious_retreat_dash_uses_bonus_action() -> None:
    hero = _actor("hero", Faction.ALLY, 0)
    goblin = _actor("goblin", Faction.ENEMY, 2)
    state = start_combat((hero, goblin), _order(hero, goblin))
    effect = ActiveCombatEffect(
        id="expeditious-retreat:hero",
        actor_id="hero",
        kind="bonus_action_dash",
        label="Szybki odwrót",
        object_id="spell:expeditious_retreat",
        value=1,
    )

    dashed = use_dash(state, hero, (effect,))

    assert dashed.accepted is True
    assert dashed.state.turn_action.action_use.value == "action_available"
    assert dashed.state.turn_action.bonus_action_use.value == "action_used"
    assert dashed.state.turn_action.extra_movement_feet == hero.speed_feet


def test_longstrider_effect_increases_available_board_movement() -> None:
    hero = _actor("hero", Faction.ALLY, 0)
    goblin = _actor("goblin", Faction.ENEMY, 8)
    state = start_combat((hero, goblin), _order(hero, goblin))
    effect = ActiveCombatEffect(
        id="longstrider:hero",
        actor_id="hero",
        kind="speed_bonus",
        label="Długie kroki",
        object_id="spell:longstrider",
        value=10,
    )

    assert movement_remaining(state, hero, (effect,)) == 40


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


def test_dying_hero_remains_in_initiative_for_death_save() -> None:
    hero = replace(_actor("hero", Faction.ALLY, 0), uses_death_saves=True)
    goblin = _actor("goblin", Faction.ENEMY, 1)
    state = start_combat((hero, goblin), _order(hero, goblin))

    state = replace_actor(state, replace(hero, hp=0))
    goblin_turn = finish_turn(state)
    hero_turn = finish_turn(goblin_turn)

    assert state.status == CombatStatus.ACTIVE
    assert current_actor(hero_turn).id == hero.id
    assert current_actor(hero_turn).needs_death_save() is True
    assert hero_turn.turn_action.action_use.value == "action_used"
    assert movement_remaining(hero_turn, current_actor(hero_turn)) == 0


def test_stable_last_hero_no_longer_keeps_combat_active() -> None:
    hero = replace(
        _actor("hero", Faction.ALLY, 0),
        hp=0,
        uses_death_saves=True,
        death_saves=DeathSaveState(stable=True),
    )
    goblin = _actor("goblin", Faction.ENEMY, 1)

    state = start_combat((hero, goblin), _order(hero, goblin))

    assert state.status == CombatStatus.FINISHED
    assert state.winner == Faction.ENEMY


def test_actor_drops_equipped_weapon_once_when_reduced_to_zero_hp() -> None:
    sword = InventoryItem("sword", "Miecz", "weapon", equipped=True)
    hero = replace(
        _actor("hero", Faction.ALLY, 0),
        uses_death_saves=True,
        inventory=(sword,),
    )
    goblin = _actor("goblin", Faction.ENEMY, 1)
    state = start_combat((hero, goblin), _order(hero, goblin))

    dropped = replace_actor(state, replace(hero, hp=0))
    repeated = replace_actor(dropped, next(actor for actor in dropped.actors if actor.id == hero.id))

    updated_hero = next(actor for actor in dropped.actors if actor.id == hero.id)
    assert updated_hero.inventory[0].equipped is False
    assert len(dropped.dropped_weapons) == 1
    assert dropped.dropped_weapons[0].weapon.name == "Miecz"
    assert dropped.dropped_weapons[0].position == hero.position
    assert repeated.dropped_weapons == dropped.dropped_weapons


def test_active_hero_picks_up_dropped_weapon_from_own_tile_without_equipping_it() -> None:
    picker = _actor("picker", Faction.ALLY, 0)
    sword = InventoryItem("sword", "Miecz", "weapon", equipped=True)
    owner = replace(
        _actor("owner", Faction.ALLY, 0),
        uses_death_saves=True,
        inventory=(sword,),
    )
    goblin = _actor("goblin", Faction.ENEMY, 4)
    state = start_combat((picker, owner, goblin), _order(picker, owner, goblin))
    dropped = replace_actor(state, replace(owner, hp=0))

    result = pickup_dropped_weapon(dropped, dropped.dropped_weapons[0].id)

    updated_picker = next(actor for actor in result.state.actors if actor.id == picker.id)
    updated_owner = next(actor for actor in result.state.actors if actor.id == owner.id)
    assert result.accepted is True
    assert result.used_action is False
    assert result.state.dropped_weapons == ()
    assert updated_picker.inventory[-1].name == "Miecz"
    assert updated_picker.inventory[-1].equipped is False
    assert updated_owner.inventory == ()
    assert result.state.turn_action.action_use.value == "action_available"
