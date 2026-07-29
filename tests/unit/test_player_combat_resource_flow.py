from dataclasses import dataclass, replace
from random import Random

import pytest

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.application import PlayerCombatResourceFlowService
from dnd_board_game.combat import (
    ActionUse,
    ActiveCombatEffect,
    CombatState,
    CombatCondition,
    ConditionState,
    DamageComponentInput,
    DamageType,
    InitiativeEntry,
    InitiativeOrder,
    SpellArea,
    SpellAreaShape,
    SpellSlotState,
    apply_damage_result,
    replace_actor,
    resolve_damage,
    move_moonbeam_zone,
    actor_in_silence_zone,
    start_combat,
)
from dnd_board_game.inventory import InventoryItem
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    EffectDuration,
    resolve_d20_roll,
)
from dnd_board_game.world import BoardDimensions, BoardState, Coordinate


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
    effect_kind: str | None = None
    effect_options: tuple[str, ...] = ()
    condition: CombatCondition | None = None
    concentration: bool = False
    duration: str = "next_turn_start"
    cast_flag: str = ""
    upcast_value_per_level: int = 0
    area: SpellArea | None = None
    save_ability: str | None = None
    save_dc: int | None = None
    save_timing: str | None = None
    damage_die_sides: int = 0
    ongoing_damage_dice_count: int = 0
    damage_type: str = ""
    save_damage_on_success: str = "none"


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


def test_targeted_status_spell_creates_typed_ac_effect_and_cast_flag() -> None:
    from dnd_board_game.combat import combat_armor_class

    service = PlayerCombatResourceFlowService()
    cleric = _actor(
        "cleric",
        Faction.ALLY,
        Coordinate(0, 0),
        spell_slots=(SpellSlotState(1, 1, 1),),
    )
    ally = _actor("ally", Faction.ALLY, Coordinate(1, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(3, 0))
    state = _state(cleric, ally, enemy)
    action = _Action(
        id="shield_of_faith",
        action_type="targeted_status",
        label="Shield of Faith",
        value=2,
        target_faction="ally",
        range_feet=60,
        spell_level=1,
        effect_kind="spell_ac_bonus",
        concentration=True,
        duration="concentration",
        cast_flag="cast_shield_of_faith",
    )

    started = service.start_concentration(
        state=state,
        active_effects=(),
        action=action,
    )
    assert started.pending_action is not None
    confirmed = service.confirm_concentration(
        state=state,
        active_effects=(),
        action=action,
        pending=started.pending_action,
        target_id="ally",
    )

    assert confirmed.active_effects[0].kind == "spell_ac_bonus"
    assert combat_armor_class(ally, confirmed.active_effects) == 14
    assert confirmed.scene_flag_changes == (("cast_shield_of_faith", True),)


def test_true_strike_effect_is_owned_by_caster_and_remembers_enemy_target() -> None:
    service = PlayerCombatResourceFlowService()
    caster = _actor("caster", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    action = _Action(
        id="true_strike",
        action_type="targeted_status",
        label="Prawdziwe uderzenie",
        value=0,
        target_faction="enemy",
        range_feet=30,
        effect_kind="next_attack_advantage",
        concentration=True,
        duration="concentration",
    )
    state = _state(caster, enemy)

    started = service.start_concentration(
        state=state,
        active_effects=(),
        action=action,
    )
    assert started.pending_action is not None
    confirmed = service.confirm_concentration(
        state=state,
        active_effects=(),
        action=action,
        pending=started.pending_action,
        target_id="enemy",
    )

    effect = confirmed.active_effects[0]
    assert effect.actor_id == "caster"
    assert effect.target_actor_id == "enemy"
    assert effect.kind == "next_attack_advantage"


def test_resistance_creates_physical_d4_save_bonus_on_selected_ally() -> None:
    service = PlayerCombatResourceFlowService()
    caster = _actor("caster", Faction.ALLY, Coordinate(0, 0))
    ally = _actor("ally", Faction.ALLY, Coordinate(1, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(3, 0))
    action = _Action(
        id="resistance",
        action_type="targeted_status",
        label="Odporność",
        value=4,
        target_faction="ally",
        range_feet=5,
        effect_kind="resistance_roll_bonus",
        concentration=True,
        duration="concentration",
    )
    state = _state(caster, ally, enemy)
    started = service.start_concentration(
        state=state,
        active_effects=(),
        action=action,
    )
    assert started.pending_action is not None

    confirmed = service.confirm_concentration(
        state=state,
        active_effects=(),
        action=action,
        pending=started.pending_action,
        target_id="ally",
    )

    effect = confirmed.active_effects[0]
    assert effect.actor_id == "ally"
    assert effect.kind == "resistance_roll_bonus"
    assert effect.value == 4
    assert effect.duration == EffectDuration.CONCENTRATION


def test_protection_from_poison_neutralizes_poison_and_keeps_hour_effect() -> None:
    service = PlayerCombatResourceFlowService()
    cleric = _actor(
        "cleric",
        Faction.ALLY,
        Coordinate(0, 0),
        spell_slots=(SpellSlotState(2, 1, 1),),
    )
    ally = _actor("ally", Faction.ALLY, Coordinate(1, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(3, 0))
    state = replace(
        _state(cleric, ally, enemy),
        condition_states=(
            ConditionState(
                "ally",
                CombatCondition.POISONED,
                source_actor_id="cleric",
                source_label="Trucizna testowa",
            ),
        ),
    )
    action = _Action(
        id="protection_from_poison",
        action_type="targeted_status",
        label="Ochrona przed trucizną",
        value=0,
        target_faction="ally",
        range_feet=5,
        spell_level=2,
        effect_kind="protection_from_poison",
        duration="encounter",
    )

    started = service.start_concentration(
        state=state,
        active_effects=(),
        action=action,
    )
    confirmed = service.confirm_concentration(
        state=started.state,
        active_effects=(),
        action=action,
        pending=started.pending_action,
        target_id="ally",
    )

    assert confirmed.state.condition_states == ()
    assert confirmed.active_effects[0].kind == "protection_from_poison"
    assert confirmed.active_effects[0].actor_id == "ally"
    assert confirmed.active_effects[0].duration == EffectDuration.UNTIL_ENCOUNTER_END


def test_casting_invisibility_ends_previous_invisibility_on_caster() -> None:
    service = PlayerCombatResourceFlowService()
    wizard = _actor(
        "wizard",
        Faction.ALLY,
        Coordinate(0, 0),
        spell_slots=(SpellSlotState(2, 1, 1),),
    )
    ally = _actor("ally", Faction.ALLY, Coordinate(1, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(3, 0))
    state = _state(wizard, ally, enemy)
    old_effect = ActiveCombatEffect(
        id="old-invisibility",
        actor_id="wizard",
        kind="invisibility",
        label="Niewidzialność",
        object_id="spell:invisibility",
        value=0,
        source_actor_id="other-caster",
        target_actor_id="wizard",
        duration=EffectDuration.CONCENTRATION,
    )
    action = _Action(
        id="invisibility",
        action_type="targeted_status",
        label="Niewidzialność",
        value=0,
        target_faction="ally",
        range_feet=5,
        spell_level=2,
        effect_kind="invisibility",
        concentration=True,
        duration="concentration",
    )

    started = service.start_concentration(
        state=state,
        active_effects=(old_effect,),
        action=action,
    )
    assert started.pending_action is not None
    confirmed = service.confirm_concentration(
        state=state,
        active_effects=(old_effect,),
        action=action,
        pending=started.pending_action,
        target_id="ally",
    )

    assert all(effect.id != old_effect.id for effect in confirmed.active_effects)
    assert len(confirmed.active_effects) == 1
    assert confirmed.active_effects[0].kind == "invisibility"
    assert confirmed.active_effects[0].actor_id == "ally"


def test_levitate_allows_willing_ally_but_hostile_target_makes_constitution_save() -> None:
    from dnd_board_game.combat import effective_movement_speed, levitation_altitude_feet

    service = PlayerCombatResourceFlowService()
    wizard = replace(
        _actor(
            "wizard",
            Faction.ALLY,
            Coordinate(0, 0),
            spell_slots=(SpellSlotState(2, 2, 2),),
        ),
        spell_save_dc=15,
    )
    ally = _actor("ally", Faction.ALLY, Coordinate(1, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 0), constitution=10)
    action = _Action(
        id="levitate",
        action_type="targeted_status",
        label="Lewitacja",
        value=20,
        target_faction="any",
        range_feet=60,
        spell_level=2,
        effect_kind="levitate",
        concentration=True,
        duration="concentration",
        save_ability="constitution",
    )

    ally_started = service.start_concentration(
        state=_state(wizard, ally, enemy),
        active_effects=(),
        action=action,
    )
    ally_result = service.confirm_concentration(
        state=ally_started.state,
        active_effects=(),
        action=action,
        pending=ally_started.pending_action,
        target_id="ally",
        rng=Random(1),
    )

    assert levitation_altitude_feet("ally", ally_result.active_effects) == 20
    assert effective_movement_speed(ally, (), ally_result.active_effects) == 0
    assert dict(ally_result.event_payload)["saving_throws"] == {}

    enemy_state = replace(
        ally_result.state,
        turn_action=replace(ally_result.state.turn_action, action_use=ActionUse.ACTION_AVAILABLE),
    )
    enemy_started = service.start_concentration(
        state=enemy_state,
        active_effects=ally_result.active_effects,
        action=action,
    )
    enemy_result = service.confirm_concentration(
        state=enemy_started.state,
        active_effects=ally_result.active_effects,
        action=action,
        pending=enemy_started.pending_action,
        target_id="enemy",
        rng=Random(1),
    )

    assert levitation_altitude_feet("enemy", enemy_result.active_effects) == 20
    assert "enemy" in dict(enemy_result.event_payload)["saving_throws"]


def test_magic_weapon_requires_and_records_one_specific_nonmagical_weapon() -> None:
    service = PlayerCombatResourceFlowService()
    wizard = _actor(
        "wizard",
        Faction.ALLY,
        Coordinate(0, 0),
        spell_slots=(SpellSlotState(2, 1, 1),),
    )
    fighter = _actor(
        "fighter",
        Faction.ALLY,
        Coordinate(1, 0),
        inventory=(
            InventoryItem("longsword", "Długi miecz", "weapon"),
            InventoryItem("longbow", "Długi łuk", "weapon"),
        ),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(3, 0))
    state = _state(wizard, fighter, enemy)
    action = _Action(
        id="magic_weapon",
        action_type="targeted_status",
        label="Magiczna broń",
        value=1,
        target_faction="ally",
        range_feet=5,
        spell_level=2,
        effect_kind="magic_weapon",
        concentration=True,
        duration="concentration",
    )
    started = service.start_concentration(
        state=state,
        active_effects=(),
        action=action,
    )

    with pytest.raises(ValueError, match="konkretną broń"):
        service.confirm_concentration(
            state=state,
            active_effects=(),
            action=action,
            pending=started.pending_action,
            target_id="fighter",
        )

    confirmed = service.confirm_concentration(
        state=state,
        active_effects=(),
        action=action,
        pending=started.pending_action,
        target_id="fighter",
        effect_option="longsword",
    )

    assert confirmed.active_effects[0].object_id == "weapon:longsword"
    assert confirmed.active_effects[0].value == 1


def test_moonbeam_creates_empty_board_zone_and_caster_can_move_it_with_action() -> None:
    service = PlayerCombatResourceFlowService()
    druid = replace(
        _actor(
            "druid",
            Faction.ALLY,
            Coordinate(0, 0),
            spell_slots=(SpellSlotState(2, 1, 1),),
        ),
        spell_save_dc=14,
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(10, 10))
    state = _state(druid, enemy)
    board = BoardState(BoardDimensions(cols=20, rows=20))
    action = _Action(
        id="moonbeam",
        action_type="targeted_status",
        label="Księżycowy promień",
        value=0,
        target_faction="any",
        range_feet=120,
        spell_level=2,
        effect_kind="ongoing_damage_zone",
        concentration=True,
        duration="concentration",
        area=SpellArea(SpellAreaShape.RADIUS, radius_feet=5),
        save_ability="constitution",
        damage_die_sides=10,
        ongoing_damage_dice_count=2,
        damage_type="radiant",
        save_damage_on_success="half",
    )
    started = service.start_concentration(
        state=state,
        active_effects=(),
        action=action,
        board=board,
    )
    selected = service.select_concentration_area(
        state=state,
        board=board,
        action=action,
        pending=started.pending_action,
        position=Coordinate(5, 5),
    )
    assert selected.selected_target_ids == ()

    confirmed = service.confirm_concentration(
        state=state,
        active_effects=(),
        action=action,
        pending=selected,
    )
    zone = confirmed.active_effects[0]
    assert zone.anchor_position == Coordinate(5, 5)
    assert zone.value == 5
    assert zone.kind == "ongoing_damage_zone:2:10:radiant:constitution:half"

    next_turn = replace(
        confirmed.state,
        turn_action=replace(
            confirmed.state.turn_action,
            action_use=ActionUse.ACTION_AVAILABLE,
        ),
    )
    moved = move_moonbeam_zone(
        next_turn,
        confirmed.active_effects,
        effect_id=zone.id,
        destination=Coordinate(15, 5),
        board=board,
    )
    assert moved.effect_after.anchor_position == Coordinate(15, 5)
    assert moved.state.turn_action.action_use == ActionUse.ACTION_USED


def test_flaming_sphere_zone_moves_thirty_feet_with_bonus_action() -> None:
    caster = _actor("wizard", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(10, 10))
    state = _state(caster, enemy)
    board = BoardState(BoardDimensions(cols=20, rows=20))
    sphere = ActiveCombatEffect(
        id="sphere:wizard",
        actor_id="wizard",
        kind="ongoing_damage_zone:2:6:fire:dexterity:half",
        label="Płonąca kula",
        object_id="combat_action:flaming_sphere",
        value=5,
        anchor_position=Coordinate(2, 2),
        source_actor_id="wizard",
        duration=EffectDuration.CONCENTRATION,
    )

    moved = move_moonbeam_zone(
        state,
        (sphere,),
        effect_id=sphere.id,
        destination=Coordinate(8, 2),
        board=board,
    )

    assert moved.effect_after.anchor_position == Coordinate(8, 2)
    assert moved.state.turn_action.action_use == ActionUse.ACTION_AVAILABLE
    assert moved.state.turn_action.bonus_action_use == ActionUse.ACTION_USED
    with pytest.raises(ValueError, match="30 ft"):
        move_moonbeam_zone(
            state,
            (sphere,),
            effect_id=sphere.id,
            destination=Coordinate(9, 2),
            board=board,
        )


def test_silence_creates_board_anchored_twenty_foot_zone() -> None:
    service = PlayerCombatResourceFlowService()
    bard = _actor(
        "bard",
        Faction.ALLY,
        Coordinate(0, 0),
        spell_slots=(SpellSlotState(2, 1, 1),),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(4, 4))
    state = _state(bard, enemy)
    board = BoardState(BoardDimensions(cols=20, rows=20))
    action = _Action(
        id="silence",
        action_type="targeted_status",
        label="Cisza",
        value=0,
        target_faction="any",
        range_feet=120,
        spell_level=2,
        effect_kind="silence_zone",
        concentration=True,
        duration="concentration",
        area=SpellArea(SpellAreaShape.RADIUS, radius_feet=20),
    )

    started = service.start_concentration(
        state=state,
        active_effects=(),
        action=action,
        board=board,
    )
    assert started.pending_action is not None
    selected = service.select_concentration_area(
        state=state,
        board=board,
        action=action,
        pending=started.pending_action,
        position=Coordinate(5, 5),
    )
    confirmed = service.confirm_concentration(
        state=state,
        active_effects=(),
        action=action,
        pending=selected,
    )

    zone = confirmed.active_effects[0]
    assert zone.kind == "silence_zone"
    assert zone.anchor_position == Coordinate(5, 5)
    assert zone.value == 20
    assert actor_in_silence_zone(enemy, confirmed.active_effects) is True
    assert actor_in_silence_zone(bard, confirmed.active_effects) is False


def test_fog_cloud_creates_empty_board_anchored_twenty_foot_zone() -> None:
    service = PlayerCombatResourceFlowService()
    caster = _actor(
        "wizard",
        Faction.ALLY,
        Coordinate(0, 0),
        spell_slots=(SpellSlotState(1, 1, 1),),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(10, 10))
    state = _state(caster, enemy)
    board = BoardState(BoardDimensions(cols=20, rows=20))
    action = _Action(
        id="fog_cloud",
        action_type="targeted_status",
        label="Chmura mgły",
        value=0,
        target_faction="any",
        range_feet=120,
        spell_level=1,
        effect_kind="obscuring_zone",
        concentration=True,
        duration="concentration",
        area=SpellArea(SpellAreaShape.RADIUS, radius_feet=20),
    )

    started = service.start_concentration(
        state=state,
        active_effects=(),
        action=action,
        board=board,
    )
    selected = service.select_concentration_area(
        state=state,
        board=board,
        action=action,
        pending=started.pending_action,
        position=Coordinate(5, 5),
    )
    confirmed = service.confirm_concentration(
        state=state,
        active_effects=(),
        action=action,
        pending=selected,
    )

    zone = confirmed.active_effects[0]
    assert zone.kind == "obscuring_zone"
    assert zone.anchor_position == Coordinate(5, 5)
    assert zone.value == 20
    assert zone.actor_id == str(caster.id)


def test_darkness_creates_empty_board_anchored_fifteen_foot_zone() -> None:
    service = PlayerCombatResourceFlowService()
    caster = _actor(
        "warlock",
        Faction.ALLY,
        Coordinate(0, 0),
        spell_slots=(SpellSlotState(2, 1, 1),),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(10, 10))
    state = _state(caster, enemy)
    board = BoardState(BoardDimensions(cols=20, rows=20))
    action = _Action(
        id="darkness",
        action_type="targeted_status",
        label="Ciemność",
        value=15,
        target_faction="any",
        range_feet=60,
        spell_level=2,
        effect_kind="obscuring_zone",
        concentration=True,
        duration="concentration",
        area=SpellArea(SpellAreaShape.RADIUS, radius_feet=15),
    )

    started = service.start_concentration(
        state=state,
        active_effects=(),
        action=action,
        board=board,
    )
    selected = service.select_concentration_area(
        state=state,
        board=board,
        action=action,
        pending=started.pending_action,
        position=Coordinate(5, 5),
    )
    confirmed = service.confirm_concentration(
        state=state,
        active_effects=(),
        action=action,
        pending=selected,
    )

    zone = confirmed.active_effects[0]
    assert zone.kind == "obscuring_zone"
    assert zone.anchor_position == Coordinate(5, 5)
    assert zone.value == 15


@pytest.mark.parametrize(
    ("spell_id", "label", "concentration", "side_feet"),
    (
        ("entangle", "Oplątanie", True, 20),
        ("grease", "Śliskość", False, 10),
    ),
)
def test_area_control_spell_keeps_difficult_terrain_zone(
    spell_id: str,
    label: str,
    concentration: bool,
    side_feet: int,
) -> None:
    service = PlayerCombatResourceFlowService()
    caster = _actor(
        "druid",
        Faction.ALLY,
        Coordinate(0, 0),
        spell_slots=(SpellSlotState(1, 1, 1),),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(5, 5))
    state = _state(caster, enemy)
    board = BoardState(BoardDimensions(cols=12, rows=12))
    action = _Action(
        id=spell_id,
        action_type="targeted_status",
        label=label,
        value=0,
        target_faction="any",
        target_count=20,
        range_feet=90,
        spell_level=1,
        effect_kind="apply_condition",
        condition=(
            CombatCondition.RESTRAINED
            if spell_id == "entangle"
            else CombatCondition.PRONE
        ),
        concentration=concentration,
        duration="concentration" if concentration else "encounter",
        area=SpellArea(SpellAreaShape.CUBE, length_feet=side_feet),
    )

    started = service.start_concentration(
        state=state,
        active_effects=(),
        action=action,
        board=board,
    )
    selected = service.select_concentration_area(
        state=state,
        board=board,
        action=action,
        pending=started.pending_action,
        position=Coordinate(5, 5),
    )
    confirmed = service.confirm_concentration(
        state=state,
        active_effects=(),
        action=action,
        pending=selected,
    )

    zone = next(
        effect
        for effect in confirmed.active_effects
        if effect.kind == f"{spell_id}_zone"
    )
    assert zone.anchor_position == Coordinate(5, 5)
    assert zone.value == side_feet
    assert zone.duration == (
        EffectDuration.CONCENTRATION
        if concentration
        else EffectDuration.UNTIL_ENCOUNTER_END
    )


def test_spider_climb_applies_concentration_mobility_to_board_selected_ally() -> None:
    service = PlayerCombatResourceFlowService()
    wizard = _actor(
        "wizard",
        Faction.ALLY,
        Coordinate(0, 0),
        spell_slots=(SpellSlotState(2, 1, 1),),
    )
    ally = _actor("ally", Faction.ALLY, Coordinate(1, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(4, 0))
    state = _state(wizard, ally, enemy)
    action = _Action(
        id="spider_climb",
        action_type="targeted_status",
        label="Pajęcza wspinaczka",
        value=0,
        target_faction="ally",
        range_feet=5,
        spell_level=2,
        effect_kind="spider_climb",
        concentration=True,
        duration="concentration",
    )

    started = service.start_concentration(
        state=state,
        active_effects=(),
        action=action,
    )
    assert started.pending_action is not None
    assert "ally" in started.pending_action.target_ids
    confirmed = service.confirm_concentration(
        state=state,
        active_effects=(),
        action=action,
        pending=started.pending_action,
        target_id="ally",
    )

    assert confirmed.active_effects[0].actor_id == "ally"
    assert confirmed.active_effects[0].kind == "spider_climb"
    assert confirmed.active_effects[0].duration == EffectDuration.CONCENTRATION


def test_spike_growth_creates_empty_board_anchored_twenty_foot_zone() -> None:
    service = PlayerCombatResourceFlowService()
    druid = _actor(
        "druid",
        Faction.ALLY,
        Coordinate(0, 0),
        spell_slots=(SpellSlotState(2, 1, 1),),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(10, 10))
    state = _state(druid, enemy)
    board = BoardState(BoardDimensions(cols=20, rows=20))
    action = _Action(
        id="spike_growth",
        action_type="targeted_status",
        label="Kolczaste zarośla",
        value=0,
        target_faction="any",
        range_feet=150,
        spell_level=2,
        effect_kind="spike_growth_zone",
        concentration=True,
        duration="concentration",
        area=SpellArea(SpellAreaShape.RADIUS, radius_feet=20),
    )

    started = service.start_concentration(
        state=state,
        active_effects=(),
        action=action,
        board=board,
    )
    assert started.pending_action is not None
    selected = service.select_concentration_area(
        state=state,
        board=board,
        action=action,
        pending=started.pending_action,
        position=Coordinate(5, 5),
    )
    confirmed = service.confirm_concentration(
        state=state,
        active_effects=(),
        action=action,
        pending=selected,
    )

    zone = confirmed.active_effects[0]
    assert zone.kind == "spike_growth_zone"
    assert zone.anchor_position == Coordinate(5, 5)
    assert zone.value == 20


def test_area_status_spell_selects_center_and_all_creatures_on_board() -> None:
    service = PlayerCombatResourceFlowService()
    caster = _actor(
        "wizard",
        Faction.ALLY,
        Coordinate(0, 0),
        spell_slots=(SpellSlotState(1, 1, 1),),
    )
    ally = _actor("ally", Faction.ALLY, Coordinate(5, 4))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(6, 4))
    distant = _actor("distant", Faction.ENEMY, Coordinate(9, 9))
    state = _state(caster, ally, enemy, distant)
    board = BoardState(BoardDimensions(cols=12, rows=12))
    action = _Action(
        id="sleep",
        action_type="targeted_status",
        label="Sen",
        value=0,
        target_faction="any",
        target_count=20,
        range_feet=90,
        spell_level=1,
        effect_kind="apply_condition",
        area=SpellArea(SpellAreaShape.RADIUS, radius_feet=10),
    )

    started = service.start_concentration(
        state=state,
        active_effects=(),
        action=action,
        board=board,
    )
    assert started.pending_action is not None
    assert started.pending_action.target_ids == ()

    selected = service.select_concentration_area(
        state=state,
        board=board,
        action=action,
        pending=started.pending_action,
        position=Coordinate(5, 4),
    )

    assert set(selected.selected_target_ids) == {"ally", "enemy"}
    assert selected.anchor == Coordinate(5, 4)
    assert Coordinate(6, 4) in selected.area_positions


def test_enhance_ability_constitution_grants_advantage_effect_and_two_d6_temp_hp() -> None:
    service = PlayerCombatResourceFlowService()
    caster = _actor(
        "bard",
        Faction.ALLY,
        Coordinate(0, 0),
        spell_slots=(SpellSlotState(2, 1, 1),),
    )
    ally = _actor("ally", Faction.ALLY, Coordinate(1, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(5, 0))
    state = _state(caster, ally, enemy)
    action = _Action(
        id="enhance_ability",
        action_type="targeted_status",
        label="Wzmocnienie cechy",
        value=0,
        target_faction="ally",
        range_feet=5,
        spell_level=2,
        effect_kind="ability_check_advantage",
        effect_options=(
            "strength",
            "dexterity",
            "constitution",
            "intelligence",
            "wisdom",
            "charisma",
        ),
        concentration=True,
        duration="concentration",
        damage_die_sides=6,
    )
    started = service.start_concentration(
        state=state,
        active_effects=(),
        action=action,
    )

    confirmed = service.confirm_concentration(
        state=state,
        active_effects=(),
        action=action,
        pending=started.pending_action,
        target_id="ally",
        effect_option="constitution",
        roll_total=9,
    )

    enhanced = next(actor for actor in confirmed.state.actors if str(actor.id) == "ally")
    assert enhanced.temp_hp == 9
    assert confirmed.active_effects[0].kind == "ability_check_advantage:constitution"
    assert confirmed.active_effects[0].duration == EffectDuration.CONCENTRATION


def test_heat_metal_board_targets_only_creatures_with_usable_metal_object() -> None:
    service = PlayerCombatResourceFlowService()
    caster = _actor(
        "druid",
        Faction.ALLY,
        Coordinate(0, 0),
        spell_slots=(SpellSlotState(2, 1, 1),),
    )
    armored = _actor(
        "armored",
        Faction.ENEMY,
        Coordinate(4, 0),
        inventory=(
            InventoryItem(
                "chain_mail",
                "Kolczuga",
                "armor",
                properties=("metallic",),
                equipped=True,
            ),
        ),
    )
    unarmored = _actor("unarmored", Faction.ENEMY, Coordinate(5, 0))
    state = _state(caster, armored, unarmored)
    action = _Action(
        id="heat_metal",
        action_type="targeted_status",
        label="Rozgrzanie metalu",
        value=0,
        target_faction="enemy",
        range_feet=60,
        spell_level=2,
        effect_kind="ongoing_damage",
        concentration=True,
        duration="concentration",
        damage_die_sides=8,
        ongoing_damage_dice_count=2,
        damage_type="fire",
    )

    started = service.start_concentration(
        state=state,
        active_effects=(),
        action=action,
    )

    assert started.pending_action.target_ids == ("armored",)


def test_aid_upcast_increases_current_and_maximum_hit_points() -> None:
    service = PlayerCombatResourceFlowService()
    cleric = _actor(
        "cleric",
        Faction.ALLY,
        Coordinate(0, 0),
        spell_slots=(SpellSlotState(3, 1, 1),),
    )
    ally = _actor("ally", Faction.ALLY, Coordinate(1, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(3, 0))
    state = _state(cleric, ally, enemy)
    action = _Action(
        id="aid",
        action_type="targeted_status",
        label="Aid",
        value=5,
        target_faction="ally",
        range_feet=30,
        spell_level=2,
        effect_kind="max_hit_points_bonus",
        duration="long_rest",
        cast_flag="cast_aid",
        upcast_value_per_level=5,
    )

    started = service.start_concentration(
        state=state,
        active_effects=(),
        action=action,
        cast_level=3,
    )
    confirmed = service.confirm_concentration(
        state=state,
        active_effects=(),
        action=action,
        pending=started.pending_action,
        target_id="ally",
    )

    updated = next(
        actor for actor in confirmed.state.actors if str(actor.id) == "ally"
    )
    assert updated.hp == 30
    assert updated.max_hp == 30


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
