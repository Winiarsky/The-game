from dataclasses import dataclass, replace
from random import Random

import pytest

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.application import PlayerCombatResourceFlowService
from dnd_board_game.combat import (
    ActionUse,
    ActiveCombatEffect,
    CombatState,
    DamageComponentInput,
    DamageType,
    InitiativeEntry,
    InitiativeOrder,
    SpellSlotState,
    apply_damage_result,
    replace_actor,
    resolve_damage,
    start_combat,
)
from dnd_board_game.inventory import InventoryItem
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.world import Coordinate


@dataclass(frozen=True)
class _Action:
    id: str
    action_type: str
    label: str
    value: int
    target_faction: str = "self"
    target_count: int = 1
    upcast_targets_per_level: int = 0
    range_feet: int = 0
    spell_level: int = 0
    prepared: bool = True
    source_item_id: str | None = None


def _actor(
    actor_id: str,
    faction: Faction,
    position: Coordinate,
    *,
    constitution: int = 10,
    inventory: tuple[InventoryItem, ...] = (),
    spell_slots: tuple[SpellSlotState, ...] = (),
) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id.title(),
        ac=12,
        hp=20,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
        ability_scores=AbilityScores(constitution=constitution),
        inventory=inventory,
        spell_slots=spell_slots,
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


def _concentration_action() -> _Action:
    return _Action(
        id="bless",
        action_type="concentration_attack_bonus",
        label="Błogosławieństwo",
        value=1,
        target_faction="ally",
        target_count=3,
        upcast_targets_per_level=1,
        range_feet=30,
        spell_level=1,
    )


def test_strength_potion_consumes_item_action_and_replaces_previous_effect() -> None:
    service = PlayerCombatResourceFlowService()
    potion = InventoryItem("potion", "Napój siły", "consumable", quantity=1)
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0), inventory=(potion,))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    old_effect = ActiveCombatEffect(
        id="old-potion",
        actor_id="hero",
        kind="strength_potion",
        label="Stary napój",
        object_id="test:old",
        value=1,
    )
    action = _Action(
        id="drink",
        action_type="strength_potion",
        label="Napój siły",
        value=2,
        source_item_id="potion",
    )

    transition = service.use_strength_potion(
        state=_state(hero, enemy),
        active_effects=(old_effect,),
        action=action,
    )

    updated_hero = next(actor for actor in transition.state.actors if actor.id == hero.id)
    assert updated_hero.inventory[0].quantity == 0
    assert transition.state.turn_action.action_use == ActionUse.ACTION_USED
    assert len(transition.active_effects) == 1
    assert transition.active_effects[0].value == 2
    assert transition.event_type == "ui_combat_strength_potion_used"


def test_concentration_start_and_confirmation_consume_slot_and_create_effect() -> None:
    service = PlayerCombatResourceFlowService()
    cleric = _actor(
        "cleric",
        Faction.ALLY,
        Coordinate(0, 0),
        spell_slots=(SpellSlotState(1, 2, 2),),
    )
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 0))
    state = _state(cleric, hero, enemy)

    started = service.start_concentration(
        state=state,
        active_effects=(),
        action=_concentration_action(),
    )
    assert started.pending_action is not None
    assert set(started.pending_action.target_ids) == {"cleric", "hero"}

    confirmed = service.confirm_concentration(
        state=state,
        active_effects=(),
        action=_concentration_action(),
        pending=started.pending_action,
        target_id="hero",
    )

    updated_cleric = next(
        actor for actor in confirmed.state.actors if actor.id == cleric.id
    )
    assert updated_cleric.spell_slots[0].remaining == 1
    assert confirmed.state.turn_action.action_use == ActionUse.ACTION_USED
    assert confirmed.active_effects[0].source_actor_id == "cleric"
    assert confirmed.active_effects[0].target_actor_id == "hero"
    assert confirmed.event_type == "ui_combat_concentration_confirmed"


def test_upcast_concentration_spell_applies_one_effect_per_selected_target() -> None:
    service = PlayerCombatResourceFlowService()
    cleric = _actor(
        "cleric",
        Faction.ALLY,
        Coordinate(0, 0),
        spell_slots=(SpellSlotState(1, 1, 1), SpellSlotState(2, 1, 1)),
    )
    allies = (
        _actor("hero", Faction.ALLY, Coordinate(1, 0)),
        _actor("rogue", Faction.ALLY, Coordinate(2, 0)),
        _actor("wizard", Faction.ALLY, Coordinate(3, 0)),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(5, 0))
    state = _state(cleric, *allies, enemy)

    started = service.start_concentration(
        state=state,
        active_effects=(),
        action=_concentration_action(),
        cast_level=2,
    )
    assert started.pending_action is not None
    assert started.pending_action.cast_level == 2
    assert started.pending_action.maximum_targets == 4

    selected_ids = tuple(
        str(actor.id)
        for actor in (cleric, *allies)
    )
    confirmed = service.confirm_concentration(
        state=state,
        active_effects=(),
        action=_concentration_action(),
        pending=started.pending_action,
        target_ids=selected_ids,
    )

    assert {effect.target_actor_id for effect in confirmed.active_effects} == set(
        selected_ids
    )
    assert len(confirmed.active_effects) == 4
    updated_cleric = next(
        actor for actor in confirmed.state.actors if actor.id == cleric.id
    )
    assert updated_cleric.spell_slots[0].remaining == 1
    assert updated_cleric.spell_slots[1].remaining == 0
    assert dict(confirmed.event_payload)["cast_level"] == 2
    assert dict(confirmed.event_payload)["target_ids"] == list(selected_ids)

    broken = service.resolve_concentration_check(
        state=confirmed.state,
        active_effects=confirmed.active_effects,
        actor_id="cleric",
        effect_ids=tuple(effect.id for effect in confirmed.active_effects),
        damage=10,
        dc=10,
        natural_roll=1,
    )
    assert broken.active_effects == ()


def test_concentration_spell_rejects_more_targets_than_cast_level_allows() -> None:
    service = PlayerCombatResourceFlowService()
    cleric = _actor(
        "cleric",
        Faction.ALLY,
        Coordinate(0, 0),
        spell_slots=(SpellSlotState(1, 1, 1),),
    )
    allies = tuple(
        _actor(f"ally-{index}", Faction.ALLY, Coordinate(index, 0))
        for index in range(1, 4)
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(5, 0))
    state = _state(cleric, *allies, enemy)
    started = service.start_concentration(
        state=state,
        active_effects=(),
        action=_concentration_action(),
        cast_level=1,
    )
    assert started.pending_action is not None

    with pytest.raises(ValueError, match="maksymalnie 3"):
        service.confirm_concentration(
            state=state,
            active_effects=(),
            action=_concentration_action(),
            pending=started.pending_action,
            target_ids=tuple(str(actor.id) for actor in (cleric, *allies)),
        )


def test_concentration_target_selection_can_be_toggled_for_board_input() -> None:
    service = PlayerCombatResourceFlowService()
    cleric = _actor(
        "cleric",
        Faction.ALLY,
        Coordinate(0, 0),
        spell_slots=(SpellSlotState(1, 1, 1),),
    )
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 0))
    started = service.start_concentration(
        state=_state(cleric, hero, enemy),
        active_effects=(),
        action=_concentration_action(),
    )
    assert started.pending_action is not None

    selected = service.toggle_concentration_target(
        started.pending_action,
        "hero",
    )
    assert selected.selected_target_ids == ("hero",)

    cleared = service.toggle_concentration_target(selected, "hero")
    assert cleared.selected_target_ids == ()


def test_damage_prompts_ally_check_and_failure_removes_concentration() -> None:
    service = PlayerCombatResourceFlowService()
    cleric = _actor(
        "cleric",
        Faction.ALLY,
        Coordinate(0, 0),
        constitution=12,
        spell_slots=(SpellSlotState(1, 2, 2),),
    )
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 0))
    state = _state(cleric, hero, enemy)
    started = service.start_concentration(
        state=state,
        active_effects=(),
        action=_concentration_action(),
    )
    assert started.pending_action is not None
    confirmed = service.confirm_concentration(
        state=state,
        active_effects=(),
        action=_concentration_action(),
        pending=started.pending_action,
        target_id="hero",
    )
    cleric_after = next(
        actor for actor in confirmed.state.actors if actor.id == cleric.id
    )
    damage = resolve_damage((DamageComponentInput(12, DamageType.SLASHING, "test"),))
    applied = apply_damage_result(cleric_after, damage)
    damaged_state = replace_actor(confirmed.state, applied.actor_after)

    prompted = service.handle_damage(
        state=damaged_state,
        active_effects=confirmed.active_effects,
        applied_damage=applied,
        rng=Random(1),
    )
    assert prompted is not None
    assert prompted.pending_check is not None
    assert prompted.pending_check.dc == 10

    failed = service.resolve_concentration_check(
        state=damaged_state,
        active_effects=prompted.active_effects,
        actor_id=prompted.pending_check.actor_id,
        effect_ids=prompted.pending_check.effect_ids,
        damage=prompted.pending_check.damage,
        dc=prompted.pending_check.dc,
        natural_roll=1,
    )

    assert failed.active_effects == ()
    assert dict(failed.event_payload)["success"] is False
    assert dict(failed.event_payload)["removed_effect_ids"]


def test_successful_concentration_check_keeps_effect() -> None:
    service = PlayerCombatResourceFlowService()
    cleric = _actor("cleric", Faction.ALLY, Coordinate(0, 0), constitution=12)
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    state = _state(cleric, enemy)
    effect = ActiveCombatEffect(
        id="bless-effect",
        actor_id="cleric",
        kind="concentration_attack_bonus",
        label="Błogosławieństwo",
        object_id="combat_action:bless",
        value=1,
        source_actor_id="cleric",
        target_actor_id="cleric",
    )

    transition = service.resolve_concentration_check(
        state=state,
        active_effects=(effect,),
        actor_id="cleric",
        effect_ids=(effect.id,),
        damage=12,
        dc=10,
        natural_roll=20,
    )

    assert transition.active_effects == (effect,)
    assert dict(transition.event_payload)["success"] is True
    assert "koncentracja utrzymana" in transition.message_body


def test_exhaustion_gives_concentration_save_disadvantage() -> None:
    service = PlayerCombatResourceFlowService()
    cleric = replace(
        _actor("cleric", Faction.ALLY, Coordinate(0, 0), constitution=12),
        exhaustion_level=3,
    )
    state = _state(cleric)
    effect = ActiveCombatEffect(
        id="focus",
        actor_id="cleric",
        kind="concentration_attack_bonus",
        label="Skupienie",
        object_id="test",
        value=1,
        source_actor_id="cleric",
        target_actor_id="cleric",
    )

    transition = service.resolve_concentration_check(
        state=state,
        active_effects=(effect,),
        actor_id="cleric",
        effect_ids=(effect.id,),
        damage=1,
        dc=10,
        natural_roll=20,
        natural_roll_2=1,
    )

    assert transition.active_effects == ()
    assert dict(transition.event_payload)["natural_roll"] == 1
