from dataclasses import replace

from dnd_board_game.actors import Actor, ActorId, Faction, ProficiencyProfile
from dnd_board_game.combat import (
    ActionUse,
    InitiativeEntry,
    InitiativeOrder,
    actor_as_combat_target,
    current_actor,
    doff_shield,
    don_shield,
    start_combat,
)
from dnd_board_game.inventory import (
    HandSlot,
    InventoryItem,
    effective_armor_class,
    free_hand_count,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.world import Coordinate


def _shield(*, equipped: bool = False) -> InventoryItem:
    return InventoryItem(
        "shield",
        "Tarcza",
        "shield",
        equipped=equipped,
        hands_required=1,
        held_in=(HandSlot.OFF_HAND,) if equipped else (),
        armor_class_bonus=2,
        armor_proficiency="shield",
    )


def _actor(*items: InventoryItem, proficient: bool = True) -> Actor:
    return Actor(
        id=ActorId("hero"),
        name="Bohater",
        ac=14,
        hp=20,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=Faction.ALLY,
        inventory=items,
        proficiencies=ProficiencyProfile(armor=("shield",) if proficient else ()),
    )


def _state(actor: Actor):
    enemy = replace(
        actor,
        id=ActorId("enemy"),
        name="Wróg",
        faction=Faction.ENEMY,
        position=Coordinate(1, 0),
        inventory=(),
    )
    request = D20RollRequest()
    hero_roll = resolve_d20_roll(D20RollInput(request, 20))
    enemy_roll = resolve_d20_roll(D20RollInput(request, 10))
    order = InitiativeOrder(
        (
            InitiativeEntry(actor, hero_roll, 0, 0),
            InitiativeEntry(enemy, enemy_roll, 0, 1),
        )
    )
    return start_combat((actor, enemy), order)


def test_equipped_shield_occupies_hand_and_adds_two_to_effective_ac() -> None:
    actor = _actor(_shield(equipped=True))

    assert free_hand_count(actor.inventory) == 1
    assert effective_armor_class(actor) == 16
    assert actor_as_combat_target(actor).ac == 16


def test_don_and_doff_shield_each_consume_action_and_update_hands() -> None:
    sword = InventoryItem(
        "sword",
        "Miecz",
        "weapon",
        hands_required=1,
        held_in=(HandSlot.MAIN_HAND,),
    )
    state = _state(_actor(sword, _shield()))

    donned = don_shield(state, "shield")

    assert donned.accepted
    assert donned.state.turn_action.action_use.value == "action_used"
    assert donned.shield is not None and donned.shield.held_in == (HandSlot.OFF_HAND,)
    assert effective_armor_class(donned.actor) == 16

    next_turn_state = replace(
        donned.state,
        turn_action=replace(donned.state.turn_action, action_use=ActionUse.ACTION_AVAILABLE),
    )
    doffed = doff_shield(next_turn_state, "shield")

    assert doffed.accepted
    assert doffed.state.turn_action.action_use.value == "action_used"
    assert doffed.shield is not None and not doffed.shield.equipped
    assert free_hand_count(doffed.actor.inventory) == 1
    assert effective_armor_class(doffed.actor) == 14


def test_actor_without_shield_proficiency_cannot_don_it_or_spend_action() -> None:
    state = _state(_actor(_shield(), proficient=False))

    result = don_shield(state, "shield")

    assert not result.accepted
    assert "biegłości" in result.message
    assert result.state.turn_action.action_use.value == "action_available"


def test_broken_or_unequipped_shield_does_not_add_ac() -> None:
    actor = _actor(_shield())
    broken = replace(actor, inventory=(replace(_shield(equipped=True), broken=True),))
    not_held = replace(actor, inventory=(replace(_shield(equipped=True), held_in=()),))

    assert effective_armor_class(actor) == 14
    assert effective_armor_class(broken) == 14
    assert effective_armor_class(not_held) == 14


def test_multiple_equipped_shields_do_not_stack_ac_bonus() -> None:
    main = replace(_shield(equipped=True), id="shield_main", held_in=(HandSlot.MAIN_HAND,))
    off = replace(_shield(equipped=True), id="shield_off", held_in=(HandSlot.OFF_HAND,))
    actor = _actor(main, off)

    assert free_hand_count(actor.inventory) == 0
    assert effective_armor_class(actor) == 16
