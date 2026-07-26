from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.inventory import HandSlot, InventoryItem, plan_hand_equip
from dnd_board_game.world import Coordinate, PathResult

from .action_economy import ActionEconomyCost, ActionUse, consume_action
from .conditions import (
    CombatCondition,
    ConditionState,
    add_condition,
    effective_movement_speed,
    grappled_actor_ids,
    has_condition,
    normalize_grapple_conditions,
    remove_condition,
    standing_movement_cost,
)
from .initiative import InitiativeEntry, InitiativeOrder
from .stealth import HiddenState, reveal_actor


class CombatStatus(StrEnum):
    ACTIVE = "active"
    FINISHED = "finished"
    STOPPED = "stopped"


@dataclass(frozen=True, slots=True)
class TurnActionState:
    action_use: ActionUse = ActionUse.ACTION_AVAILABLE
    bonus_action_use: ActionUse = ActionUse.ACTION_AVAILABLE
    reaction_available: bool = True
    movement_used_feet: int = 0
    extra_movement_feet: int = 0
    object_interaction_available: bool = True
    two_weapon_trigger_item_id: str | None = None
    attack_action_active: bool = False
    attacks_used: int = 0
    attacks_maximum: int = 0


@dataclass(frozen=True, slots=True)
class TurnActionUseResult:
    state: CombatState
    accepted: bool
    message: str


@dataclass(frozen=True, slots=True)
class TurnMovementUseResult:
    state: CombatState
    accepted: bool
    message: str
    movement_remaining_feet: int


@dataclass(frozen=True, slots=True)
class ConditionChangeResult:
    state: CombatState
    accepted: bool
    actor: Actor
    message: str
    movement_cost_feet: int = 0


@dataclass(frozen=True, slots=True)
class ObjectInteractionUseResult:
    state: CombatState
    accepted: bool
    used_action: bool
    message: str
    interaction_count: int = 1


@dataclass(frozen=True, slots=True)
class ActionEconomyUseResult:
    state: CombatState
    accepted: bool
    requested_cost: ActionEconomyCost
    spent_cost: ActionEconomyCost | None
    message: str


@dataclass(frozen=True, slots=True)
class PickupDroppedWeaponResult:
    state: CombatState
    accepted: bool
    actor: Actor
    weapon: InventoryItem | None
    used_action: bool
    message: str


@dataclass(frozen=True, slots=True)
class EquipWeaponResult:
    state: CombatState
    accepted: bool
    actor: Actor
    weapon: InventoryItem | None
    replaced_weapons: tuple[InventoryItem, ...]
    used_action: bool
    message: str


@dataclass(frozen=True, slots=True)
class DropWeaponResult:
    state: CombatState
    accepted: bool
    actor: Actor
    weapon: InventoryItem | None
    dropped_weapon: DroppedWeapon | None
    message: str


@dataclass(frozen=True, slots=True)
class StowWeaponResult:
    state: CombatState
    accepted: bool
    actor: Actor
    weapon: InventoryItem | None
    used_action: bool
    message: str


@dataclass(frozen=True, slots=True)
class ShieldUseResult:
    state: CombatState
    accepted: bool
    actor: Actor
    shield: InventoryItem | None
    replaced_items: tuple[InventoryItem, ...]
    message: str


@dataclass(frozen=True, slots=True)
class DroppedWeapon:
    id: str
    source_actor_id: ActorId
    weapon: InventoryItem
    position: Coordinate
    dropped_round: int


@dataclass(frozen=True, slots=True)
class CombatState:
    actors: tuple[Actor, ...]
    initiative_order: InitiativeOrder
    turn_action: TurnActionState = TurnActionState()
    status: CombatStatus = CombatStatus.ACTIVE
    winner: Faction | None = None
    spent_reaction_actor_ids: frozenset[ActorId] = frozenset()
    dropped_weapons: tuple[DroppedWeapon, ...] = ()
    hidden_states: tuple[HiddenState, ...] = ()
    condition_states: tuple[ConditionState, ...] = ()

    @property
    def round_number(self) -> int:
        return self.initiative_order.round_number


def start_combat(
    actors: tuple[Actor, ...],
    initiative_order: InitiativeOrder,
    hidden_states: tuple[HiddenState, ...] = (),
    condition_states: tuple[ConditionState, ...] = (),
) -> CombatState:
    if not actors:
        raise ValueError("Cannot start combat without actors.")
    order = _sync_order_actor_states(initiative_order, actors)
    first_actor = next(actor for actor in actors if actor.id == order.current_actor.id)
    state = CombatState(
        actors=actors,
        initiative_order=order,
        turn_action=_turn_action_for(first_actor, frozenset()),
        hidden_states=hidden_states,
        condition_states=tuple(
            condition
            for condition in condition_states
            if condition.actor_id in {str(actor.id) for actor in actors}
        ),
    )
    return _with_finished_status(state)


def current_actor(state: CombatState) -> Actor:
    current_id = state.initiative_order.current_actor.id
    return actor_by_id(state, current_id)


def actor_by_id(state: CombatState, actor_id: ActorId) -> Actor:
    for actor in state.actors:
        if actor.id == actor_id:
            return actor
    raise ValueError(f"Unknown combat actor: {actor_id}.")


def replace_actor(state: CombatState, updated_actor: Actor) -> CombatState:
    previous_actor = actor_by_id(state, updated_actor.id)
    dropped_weapons = state.dropped_weapons
    if previous_actor.hp > 0 and updated_actor.hp <= 0:
        updated_actor, newly_dropped = _drop_equipped_weapons(
            updated_actor,
            round_number=state.round_number,
        )
        known_ids = {item.id for item in dropped_weapons}
        dropped_weapons = (*dropped_weapons, *(item for item in newly_dropped if item.id not in known_ids))
    actors = tuple(updated_actor if actor.id == updated_actor.id else actor for actor in state.actors)
    if all(actor.id != updated_actor.id for actor in state.actors):
        raise ValueError(f"Unknown combat actor: {updated_actor.id}.")
    hidden_states = state.hidden_states
    if updated_actor.is_defeated():
        hidden_states = reveal_actor(hidden_states, str(updated_actor.id))
    synced = replace(
        state,
        actors=actors,
        initiative_order=_sync_order_actor_states(state.initiative_order, actors),
        dropped_weapons=dropped_weapons,
        hidden_states=hidden_states,
        condition_states=normalize_grapple_conditions(state.condition_states, actors),
    )
    return _with_finished_status(synced)


def _drop_equipped_weapons(
    actor: Actor,
    *,
    round_number: int,
) -> tuple[Actor, tuple[DroppedWeapon, ...]]:
    inventory: list[InventoryItem] = []
    dropped: list[DroppedWeapon] = []
    for item in actor.inventory:
        if item.kind != "weapon" or not item.equipped or not item.available:
            inventory.append(item)
            continue
        unequipped = replace(item, equipped=False, held_in=())
        inventory.append(unequipped)
        dropped.append(
            DroppedWeapon(
                id=f"dropped:{actor.id}:{item.id}",
                source_actor_id=actor.id,
                weapon=unequipped,
                position=actor.position,
                dropped_round=round_number,
            )
        )
    return replace(actor, inventory=tuple(inventory)), tuple(dropped)


def use_turn_action(state: CombatState) -> TurnActionUseResult:
    if state.status != CombatStatus.ACTIVE:
        return TurnActionUseResult(state, False, "Walka nie jest aktywna.")
    try:
        action_use = consume_action(state.turn_action.action_use)
    except ValueError:
        return TurnActionUseResult(state, False, "Akcja w tej turze została już zużyta.")
    return TurnActionUseResult(
        replace(state, turn_action=replace(state.turn_action, action_use=action_use)),
        True,
        "Akcja została zużyta.",
    )


def attack_action_remaining(state: CombatState, actor: Actor | None = None) -> int:
    """Return attacks still available from the current Attack action."""
    if state.status != CombatStatus.ACTIVE:
        return 0
    acting = actor or current_actor(state)
    if acting.id != current_actor(state).id or acting.is_defeated():
        return 0
    turn = state.turn_action
    if turn.attack_action_active:
        return max(0, turn.attacks_maximum - turn.attacks_used)
    if turn.action_use == ActionUse.ACTION_AVAILABLE:
        return acting.attacks_per_action
    return 0


def can_use_attack_action(state: CombatState, actor: Actor | None = None) -> bool:
    return attack_action_remaining(state, actor) > 0


def use_attack_action(
    state: CombatState,
    actor: Actor | None = None,
    *,
    maximum_attacks: int | None = None,
) -> TurnActionUseResult:
    """Spend one attack, starting the Attack action when necessary."""
    if state.status != CombatStatus.ACTIVE:
        return TurnActionUseResult(state, False, "Walka nie jest aktywna.")
    acting = actor or current_actor(state)
    if acting.id != current_actor(state).id:
        return TurnActionUseResult(state, False, "Tylko aktywny aktor może wykonać atak.")
    turn = state.turn_action
    if turn.attack_action_active:
        if turn.attacks_used >= turn.attacks_maximum:
            return TurnActionUseResult(
                state,
                False,
                "Akcja ataku jest już zużyta: wykorzystano wszystkie dostępne ataki.",
            )
        updated = replace(turn, attacks_used=turn.attacks_used + 1)
    else:
        if turn.action_use != ActionUse.ACTION_AVAILABLE:
            return TurnActionUseResult(state, False, "Akcja w tej turze została już zużyta.")
        maximum = acting.attacks_per_action if maximum_attacks is None else int(maximum_attacks)
        if maximum < 1:
            return TurnActionUseResult(state, False, "Liczba ataków musi być dodatnia.")
        updated = replace(
            turn,
            action_use=ActionUse.ACTION_USED,
            attack_action_active=True,
            attacks_used=1,
            attacks_maximum=maximum,
        )
    remaining = max(0, updated.attacks_maximum - updated.attacks_used)
    return TurnActionUseResult(
        replace(state, turn_action=updated),
        True,
        f"Wykorzystano atak. Pozostało ataków: {remaining}.",
    )


def use_bonus_action(state: CombatState) -> TurnActionUseResult:
    if state.status != CombatStatus.ACTIVE:
        return TurnActionUseResult(state, False, "Walka nie jest aktywna.")
    try:
        bonus_action_use = consume_action(state.turn_action.bonus_action_use)
    except ValueError:
        return TurnActionUseResult(state, False, "Akcja bonusowa w tej turze została już zużyta.")
    return TurnActionUseResult(
        replace(state, turn_action=replace(state.turn_action, bonus_action_use=bonus_action_use)),
        True,
        "Akcja bonusowa została zużyta.",
    )


def set_two_weapon_trigger(state: CombatState, item_id: str | None) -> CombatState:
    return replace(
        state,
        turn_action=replace(state.turn_action, two_weapon_trigger_item_id=item_id),
    )


def use_object_interaction(state: CombatState) -> ObjectInteractionUseResult:
    if state.status != CombatStatus.ACTIVE:
        return ObjectInteractionUseResult(state, False, False, "Walka nie jest aktywna.")
    if state.turn_action.object_interaction_available:
        return ObjectInteractionUseResult(
            replace(
                state,
                turn_action=replace(state.turn_action, object_interaction_available=False),
            ),
            True,
            False,
            "Wykorzystano darmową interakcję z obiektem w tej turze.",
        )
    action = use_turn_action(state)
    if not action.accepted:
        return ObjectInteractionUseResult(state, False, False, "Brak darmowej interakcji i dostępnej akcji.")
    return ObjectInteractionUseResult(
        action.state,
        True,
        True,
        "Dodatkowa interakcja z obiektem zużyła akcję.",
    )


def use_object_interactions(state: CombatState, count: int) -> ObjectInteractionUseResult:
    """Atomically pay for one or two object interactions in the current turn.

    D&D 5e 2014 grants one free interaction. A second interaction may use the
    actor's action. More than two discrete interactions cannot fit in this base
    turn economy without a feature that provides an additional action.
    """

    if count < 1:
        raise ValueError("Liczba interakcji z obiektem musi być dodatnia.")
    if count > 2:
        return ObjectInteractionUseResult(
            state,
            False,
            False,
            "Ta czynność wymaga więcej niż dwóch interakcji z obiektami w jednej turze.",
            count,
        )
    updated_state = state
    used_action = False
    messages: list[str] = []
    for _ in range(count):
        result = use_object_interaction(updated_state)
        if not result.accepted:
            return ObjectInteractionUseResult(state, False, False, result.message, count)
        updated_state = result.state
        used_action = used_action or result.used_action
        messages.append(result.message)
    return ObjectInteractionUseResult(
        updated_state,
        True,
        used_action,
        " ".join(messages),
        count,
    )


def can_use_object_interactions(state: CombatState, count: int = 1) -> bool:
    if state.status != CombatStatus.ACTIVE or count < 1 or count > 2:
        return False
    if count == 1:
        return (
            state.turn_action.object_interaction_available
            or state.turn_action.action_use == ActionUse.ACTION_AVAILABLE
        )
    return (
        state.turn_action.object_interaction_available
        and state.turn_action.action_use == ActionUse.ACTION_AVAILABLE
    )


def pickup_dropped_weapon(state: CombatState, dropped_weapon_id: str) -> PickupDroppedWeaponResult:
    actor = current_actor(state)
    if actor.faction != Faction.ALLY or actor.is_defeated():
        return PickupDroppedWeaponResult(state, False, actor, None, False, "Ten aktor nie może podnieść broni.")
    dropped = next((item for item in state.dropped_weapons if item.id == dropped_weapon_id), None)
    if dropped is None:
        return PickupDroppedWeaponResult(state, False, actor, None, False, "Broń nie leży już na planszy.")
    if actor.position != dropped.position:
        return PickupDroppedWeaponResult(state, False, actor, None, False, "Aby podnieść broń, trzeba stać na jej polu.")
    interaction = use_object_interaction(state)
    if not interaction.accepted:
        return PickupDroppedWeaponResult(state, False, actor, None, False, interaction.message)

    updated_state = interaction.state
    source = actor_by_id(updated_state, dropped.source_actor_id)
    if source.id != actor.id:
        source = replace(source, inventory=tuple(item for item in source.inventory if item.id != dropped.weapon.id))
        updated_state = replace_actor(updated_state, source)
        actor = current_actor(updated_state)
        existing_ids = {item.id for item in actor.inventory}
        weapon = dropped.weapon
        if weapon.id in existing_ids:
            weapon = replace(weapon, id=f"{weapon.id}_{dropped.source_actor_id}")
        actor = replace(actor, inventory=(*actor.inventory, replace(weapon, equipped=False, held_in=())))
    else:
        weapon = dropped.weapon
        actor = replace(
            actor,
            inventory=tuple(
                replace(item, equipped=False, held_in=(), available=True) if item.id == weapon.id else item
                for item in actor.inventory
            ),
        )
    updated_state = replace_actor(updated_state, actor)
    updated_state = replace(
        updated_state,
        dropped_weapons=tuple(item for item in updated_state.dropped_weapons if item.id != dropped.id),
    )
    cost = "zużywając akcję" if interaction.used_action else "w ramach darmowej interakcji z obiektem"
    return PickupDroppedWeaponResult(
        updated_state,
        True,
        actor,
        weapon,
        interaction.used_action,
        f"{actor.name} podnosi {weapon.name} {cost}. Broń pozostaje niewyposażona.",
    )


def equip_weapon(
    state: CombatState,
    weapon_id: str,
    *,
    preferred_hand: HandSlot | None = None,
) -> EquipWeaponResult:
    actor = current_actor(state)
    if actor.faction != Faction.ALLY or actor.is_defeated():
        return EquipWeaponResult(state, False, actor, None, (), False, "Ten aktor nie może wyposażyć broni.")
    weapon = next((item for item in actor.inventory if item.id == weapon_id), None)
    if weapon is None:
        return EquipWeaponResult(state, False, actor, None, (), False, "Tej broni nie ma w ekwipunku bohatera.")
    if weapon.kind != "weapon" or not weapon.available:
        return EquipWeaponResult(state, False, actor, weapon, (), False, "Ten przedmiot nie jest dostępną bronią.")
    if weapon.equipped:
        return EquipWeaponResult(state, False, actor, weapon, (), False, "Ta broń jest już wyposażona.")

    plan = plan_hand_equip(actor.inventory, weapon_id, preferred_slot=preferred_hand)
    replaced_weapons = tuple(
        item for item in actor.inventory if item.id in plan.replaced_item_ids
    )
    interaction_count = 1 + len(replaced_weapons)
    interaction = use_object_interactions(state, interaction_count)
    if not interaction.accepted:
        return EquipWeaponResult(state, False, actor, weapon, (), False, interaction.message)

    actor = current_actor(interaction.state)
    actor = replace(actor, inventory=plan.inventory)
    updated_state = replace_actor(interaction.state, actor)
    equipped = next(item for item in actor.inventory if item.id == weapon_id)
    cost = (
        "zużywając darmową interakcję i akcję"
        if interaction.used_action and interaction.interaction_count > 1
        else "zużywając akcję"
        if interaction.used_action
        else "w ramach darmowej interakcji z obiektem"
    )
    if replaced_weapons:
        previous = ", ".join(item.name for item in replaced_weapons)
        message = (
            f"{actor.name} chowa {previous} i wyposaża {equipped.name} "
            f"{_hand_slots_label(equipped.held_in)} {cost}."
        )
    else:
        message = f"{actor.name} wyposaża {equipped.name} {_hand_slots_label(equipped.held_in)} {cost}."
    return EquipWeaponResult(
        updated_state,
        True,
        actor,
        equipped,
        replaced_weapons,
        interaction.used_action,
        message,
    )


def stow_weapon(state: CombatState, weapon_id: str) -> StowWeaponResult:
    actor = current_actor(state)
    if actor.faction != Faction.ALLY or actor.is_defeated():
        return StowWeaponResult(state, False, actor, None, False, "Ten aktor nie może schować broni.")
    weapon = next((item for item in actor.inventory if item.id == weapon_id), None)
    if weapon is None:
        return StowWeaponResult(state, False, actor, None, False, "Tej broni nie ma w ekwipunku bohatera.")
    if weapon.kind != "weapon" or not weapon.available or not weapon.equipped:
        return StowWeaponResult(state, False, actor, weapon, False, "Można schować tylko wyposażoną broń.")
    interaction = use_object_interaction(state)
    if not interaction.accepted:
        return StowWeaponResult(state, False, actor, weapon, False, interaction.message)
    actor = current_actor(interaction.state)
    stowed = replace(weapon, equipped=False, held_in=())
    actor = replace(
        actor,
        inventory=tuple(stowed if item.id == weapon_id else item for item in actor.inventory),
    )
    updated_state = replace_actor(interaction.state, actor)
    cost = "zużywając akcję" if interaction.used_action else "w ramach darmowej interakcji z obiektem"
    return StowWeaponResult(
        updated_state,
        True,
        actor,
        stowed,
        interaction.used_action,
        f"{actor.name} chowa {weapon.name} {cost}.",
    )


def drop_weapon(state: CombatState, weapon_id: str) -> DropWeaponResult:
    actor = current_actor(state)
    if actor.faction != Faction.ALLY or actor.is_defeated():
        return DropWeaponResult(state, False, actor, None, None, "Ten aktor nie może upuścić broni.")
    weapon = next((item for item in actor.inventory if item.id == weapon_id), None)
    if weapon is None:
        return DropWeaponResult(state, False, actor, None, None, "Tej broni nie ma w ekwipunku bohatera.")
    if weapon.kind != "weapon" or not weapon.available or not weapon.equipped:
        return DropWeaponResult(state, False, actor, weapon, None, "Można upuścić tylko wyposażoną broń.")

    unequipped = replace(weapon, equipped=False, held_in=())
    actor = replace(
        actor,
        inventory=tuple(unequipped if item.id == weapon_id else item for item in actor.inventory),
    )
    updated_state = replace_actor(state, actor)
    dropped = DroppedWeapon(
        id=f"dropped:{actor.id}:{weapon.id}",
        source_actor_id=actor.id,
        weapon=unequipped,
        position=actor.position,
        dropped_round=state.round_number,
    )
    updated_state = replace(
        updated_state,
        dropped_weapons=(*updated_state.dropped_weapons, dropped),
    )
    return DropWeaponResult(
        updated_state,
        True,
        actor,
        unequipped,
        dropped,
        f"{actor.name} upuszcza {weapon.name} na polu {actor.position.as_tuple()}. Nie zużywa to akcji ani interakcji.",
    )


def don_shield(state: CombatState, shield_id: str) -> ShieldUseResult:
    actor = current_actor(state)
    if actor.faction != Faction.ALLY or actor.is_defeated():
        return ShieldUseResult(state, False, actor, None, (), "Ten aktor nie może założyć tarczy.")
    shield = next((item for item in actor.inventory if item.id == shield_id), None)
    if shield is None:
        return ShieldUseResult(state, False, actor, None, (), "Tej tarczy nie ma w ekwipunku bohatera.")
    if shield.kind != "shield" or not shield.available:
        return ShieldUseResult(state, False, actor, shield, (), "Ten przedmiot nie jest dostępną tarczą.")
    if shield.equipped:
        return ShieldUseResult(state, False, actor, shield, (), "Ta tarcza jest już założona.")
    proficiency_id = shield.armor_proficiency or "shield"
    if not actor.proficiencies.is_armor_proficient(proficiency_id):
        return ShieldUseResult(
            state,
            False,
            actor,
            shield,
            (),
            f"{actor.name} nie ma biegłości wymaganej przez tarczę ({proficiency_id}).",
        )
    if any(item.kind == "shield" and item.equipped and item.available for item in actor.inventory):
        return ShieldUseResult(state, False, actor, shield, (), "Aktor może korzystać tylko z jednej tarczy.")
    if grappled_actor_ids(state.condition_states, str(actor.id)):
        return ShieldUseResult(
            state,
            False,
            actor,
            shield,
            (),
            "Nie można założyć tarczy podczas utrzymywania chwytu.",
        )
    plan = plan_hand_equip(actor.inventory, shield_id)
    action = use_turn_action(state)
    if not action.accepted:
        return ShieldUseResult(state, False, actor, shield, (), action.message)
    actor = current_actor(action.state)
    replaced_items = tuple(item for item in actor.inventory if item.id in plan.replaced_item_ids)
    actor = replace(actor, inventory=plan.inventory)
    updated_state = replace_actor(action.state, actor)
    equipped = next(item for item in actor.inventory if item.id == shield_id)
    replaced_label = (
        f" Chowa: {', '.join(item.name for item in replaced_items)}."
        if replaced_items
        else ""
    )
    return ShieldUseResult(
        updated_state,
        True,
        actor,
        equipped,
        replaced_items,
        f"{actor.name} zakłada {equipped.name}, zajmując jedną rękę i zużywając akcję.{replaced_label}",
    )


def doff_shield(state: CombatState, shield_id: str) -> ShieldUseResult:
    actor = current_actor(state)
    if actor.faction != Faction.ALLY or actor.is_defeated():
        return ShieldUseResult(state, False, actor, None, (), "Ten aktor nie może zdjąć tarczy.")
    shield = next((item for item in actor.inventory if item.id == shield_id), None)
    if shield is None:
        return ShieldUseResult(state, False, actor, None, (), "Tej tarczy nie ma w ekwipunku bohatera.")
    if shield.kind != "shield" or not shield.available or not shield.equipped:
        return ShieldUseResult(state, False, actor, shield, (), "Ta tarcza nie jest obecnie założona.")
    action = use_turn_action(state)
    if not action.accepted:
        return ShieldUseResult(state, False, actor, shield, (), action.message)
    actor = current_actor(action.state)
    unequipped = replace(shield, equipped=False, held_in=())
    actor = replace(
        actor,
        inventory=tuple(unequipped if item.id == shield_id else item for item in actor.inventory),
    )
    updated_state = replace_actor(action.state, actor)
    return ShieldUseResult(
        updated_state,
        True,
        actor,
        unequipped,
        (),
        f"{actor.name} zdejmuje {shield.name}, zwalniając rękę i zużywając akcję.",
    )


def _hand_slots_label(slots: tuple[HandSlot, ...]) -> str:
    if len(slots) == 2:
        return "w obu rękach"
    if slots == (HandSlot.OFF_HAND,):
        return "w drugiej ręce"
    return "w głównej ręce"


def use_reaction(state: CombatState) -> TurnActionUseResult:
    return use_actor_reaction(state, current_actor(state))


def reaction_available_for(state: CombatState, actor: Actor) -> bool:
    return (
        state.status == CombatStatus.ACTIVE
        and not actor.is_defeated()
        and actor.id not in state.spent_reaction_actor_ids
    )


def use_actor_reaction(state: CombatState, actor: Actor) -> TurnActionUseResult:
    if state.status != CombatStatus.ACTIVE:
        return TurnActionUseResult(state, False, "Walka nie jest aktywna.")
    if not reaction_available_for(state, actor):
        return TurnActionUseResult(state, False, "Reakcja w tej rundzie została już zużyta.")
    spent = frozenset((*state.spent_reaction_actor_ids, actor.id))
    turn_action = state.turn_action
    if actor.id == current_actor(state).id:
        turn_action = replace(turn_action, reaction_available=False)
    return TurnActionUseResult(
        replace(state, spent_reaction_actor_ids=spent, turn_action=turn_action),
        True,
        "Reakcja została zużyta.",
    )


def can_pay_action_economy_cost(state: CombatState, cost: ActionEconomyCost) -> bool:
    if state.status != CombatStatus.ACTIVE:
        return False
    if cost == ActionEconomyCost.FREE:
        return True
    if cost == ActionEconomyCost.ACTION:
        return state.turn_action.action_use == ActionUse.ACTION_AVAILABLE
    if cost == ActionEconomyCost.BONUS_ACTION:
        return state.turn_action.bonus_action_use == ActionUse.ACTION_AVAILABLE
    if cost == ActionEconomyCost.REACTION:
        return reaction_available_for(state, current_actor(state))
    if cost == ActionEconomyCost.OBJECT_INTERACTION:
        return (
            state.turn_action.object_interaction_available
            or state.turn_action.action_use == ActionUse.ACTION_AVAILABLE
        )
    return False


def use_action_economy_cost(
    state: CombatState,
    cost: ActionEconomyCost,
) -> ActionEconomyUseResult:
    """Consume one declared cost through the shared combat-turn contract."""

    if cost == ActionEconomyCost.FREE:
        if state.status != CombatStatus.ACTIVE:
            return ActionEconomyUseResult(state, False, cost, None, "Walka nie jest aktywna.")
        return ActionEconomyUseResult(state, True, cost, ActionEconomyCost.FREE, "Czynność nie zużywa zasobu tury.")
    if cost == ActionEconomyCost.ACTION:
        result = use_turn_action(state)
        return ActionEconomyUseResult(result.state, result.accepted, cost, cost if result.accepted else None, result.message)
    if cost == ActionEconomyCost.BONUS_ACTION:
        result = use_bonus_action(state)
        return ActionEconomyUseResult(result.state, result.accepted, cost, cost if result.accepted else None, result.message)
    if cost == ActionEconomyCost.REACTION:
        result = use_reaction(state)
        return ActionEconomyUseResult(result.state, result.accepted, cost, cost if result.accepted else None, result.message)
    interaction = use_object_interaction(state)
    spent_cost = (
        ActionEconomyCost.ACTION
        if interaction.accepted and interaction.used_action
        else ActionEconomyCost.OBJECT_INTERACTION
        if interaction.accepted
        else None
    )
    return ActionEconomyUseResult(
        interaction.state,
        interaction.accepted,
        cost,
        spent_cost,
        interaction.message,
    )


def movement_remaining(state: CombatState, actor: Actor) -> int:
    speed = effective_movement_speed(actor, state.condition_states)
    return max(0, speed + state.turn_action.extra_movement_feet - state.turn_action.movement_used_feet)


def use_dash(state: CombatState, actor: Actor) -> TurnActionUseResult:
    if actor.id != current_actor(state).id:
        return TurnActionUseResult(state, False, "To nie jest tura tego aktora.")
    action_result = use_turn_action(state)
    if not action_result.accepted:
        return action_result
    dash_speed = effective_movement_speed(actor, state.condition_states)
    updated = replace(
        action_result.state,
        turn_action=replace(
            action_result.state.turn_action,
            extra_movement_feet=action_result.state.turn_action.extra_movement_feet + dash_speed,
        ),
    )
    return TurnActionUseResult(
        updated,
        True,
        f"Dash: {actor.name} dostaje dodatkowe {dash_speed} feet ruchu w tej turze.",
    )


def drop_prone(state: CombatState, actor: Actor) -> ConditionChangeResult:
    if state.status != CombatStatus.ACTIVE:
        return ConditionChangeResult(state, False, actor, "Walka nie jest aktywna.")
    if actor.id != current_actor(state).id:
        return ConditionChangeResult(state, False, actor, "To nie jest tura tego aktora.")
    if actor.is_defeated():
        return ConditionChangeResult(state, False, actor, "Pokonany aktor nie może zmienić pozycji.")
    if has_condition(state.condition_states, str(actor.id), CombatCondition.PRONE):
        return ConditionChangeResult(state, False, actor, f"{actor.name} już jest powalony.")
    updated = replace(
        state,
        condition_states=add_condition(
            state.condition_states,
            str(actor.id),
            CombatCondition.PRONE,
        ),
    )
    return ConditionChangeResult(updated, True, actor, f"{actor.name} pada na ziemię.")


def stand_up(state: CombatState, actor: Actor) -> ConditionChangeResult:
    if state.status != CombatStatus.ACTIVE:
        return ConditionChangeResult(state, False, actor, "Walka nie jest aktywna.")
    if actor.id != current_actor(state).id:
        return ConditionChangeResult(state, False, actor, "To nie jest tura tego aktora.")
    if actor.is_defeated():
        return ConditionChangeResult(state, False, actor, "Pokonany aktor nie może wstać.")
    if not has_condition(state.condition_states, str(actor.id), CombatCondition.PRONE):
        return ConditionChangeResult(state, False, actor, f"{actor.name} nie jest powalony.")
    cost = standing_movement_cost(actor)
    remaining = movement_remaining(state, actor)
    if cost > remaining:
        return ConditionChangeResult(
            state,
            False,
            actor,
            f"Za mało ruchu, aby wstać. Koszt: {cost} feet, pozostało: {remaining} feet.",
            cost,
        )
    updated = replace(
        state,
        condition_states=remove_condition(
            state.condition_states,
            str(actor.id),
            CombatCondition.PRONE,
        ),
        turn_action=replace(
            state.turn_action,
            movement_used_feet=state.turn_action.movement_used_feet + cost,
        ),
    )
    return ConditionChangeResult(
        updated,
        True,
        actor,
        f"{actor.name} wstaje, wydając {cost} feet ruchu.",
        cost,
    )


def use_movement(state: CombatState, actor: Actor, path: PathResult) -> TurnMovementUseResult:
    remaining = movement_remaining(state, actor)
    if state.status != CombatStatus.ACTIVE:
        return TurnMovementUseResult(state, False, "Walka nie jest aktywna.", remaining)
    if actor.id != current_actor(state).id:
        return TurnMovementUseResult(state, False, "To nie jest tura tego aktora.", remaining)
    if not path.valid:
        return TurnMovementUseResult(state, False, "Nie można wykonać ruchu na wybrane pole.", remaining)
    if path.cost_feet > remaining:
        return TurnMovementUseResult(
            state,
            False,
            f"Za mało ruchu. Koszt: {path.cost_feet} feet, pozostało: {remaining} feet.",
            remaining,
        )
    dragged_ids = grappled_actor_ids(state.condition_states, str(actor.id))
    updated_state = state
    dragged_actor: Actor | None = None
    if dragged_ids and len(path.path) > 1:
        dragged_actor = actor_by_id(state, ActorId(dragged_ids[0]))
        updated_state = replace_actor(
            updated_state,
            replace(dragged_actor, position=path.path[-2]),
        )
    updated_actor = replace(actor, position=path.destination)
    updated_state = replace_actor(updated_state, updated_actor)
    movement_used = state.turn_action.movement_used_feet + path.cost_feet
    updated_state = replace(updated_state, turn_action=replace(updated_state.turn_action, movement_used_feet=movement_used))
    updated_remaining = movement_remaining(updated_state, updated_actor)
    return TurnMovementUseResult(
        updated_state,
        True,
        (
            f"Ruch wykonany na {path.destination.as_tuple()}; "
            f"przestaw {dragged_actor.name} na {path.path[-2].as_tuple()}. "
            f"Pozostało ruchu: {updated_remaining} feet."
            if dragged_actor is not None
            else f"Ruch wykonany na {path.destination.as_tuple()}. Pozostało ruchu: {updated_remaining} feet."
        ),
        updated_remaining,
    )


def finish_turn(state: CombatState) -> CombatState:
    finished_state = _with_finished_status(state)
    if finished_state.status != CombatStatus.ACTIVE:
        return finished_state
    order = _sync_order_actor_states(finished_state.initiative_order, finished_state.actors).advance_turn(skip_defeated=True)
    next_actor = actor_by_id(finished_state, order.current_actor.id)
    spent = frozenset(actor_id for actor_id in finished_state.spent_reaction_actor_ids if actor_id != next_actor.id)
    return replace(
        finished_state,
        initiative_order=order,
        spent_reaction_actor_ids=spent,
        turn_action=_turn_action_for(next_actor, spent),
    )


def _turn_action_for(
    actor: Actor,
    spent_reaction_actor_ids: frozenset[ActorId],
) -> TurnActionState:
    if actor.is_defeated():
        return TurnActionState(
            action_use=ActionUse.ACTION_USED,
            bonus_action_use=ActionUse.ACTION_USED,
            reaction_available=False,
            movement_used_feet=actor.speed_feet,
            object_interaction_available=False,
        )
    return TurnActionState(reaction_available=actor.id not in spent_reaction_actor_ids)


def stop_combat(state: CombatState) -> CombatState:
    return replace(state, status=CombatStatus.STOPPED)


def combat_is_finished(state: CombatState) -> bool:
    return state.status == CombatStatus.FINISHED or combat_winner(state) is not None


def combat_winner(state: CombatState) -> Faction | None:
    allies_alive = any(
        actor.faction == Faction.ALLY and actor.can_take_combat_turn()
        for actor in state.actors
    )
    enemies_alive = any(
        actor.faction == Faction.ENEMY and actor.can_take_combat_turn()
        for actor in state.actors
    )
    if allies_alive and not enemies_alive:
        return Faction.ALLY
    if enemies_alive and not allies_alive:
        return Faction.ENEMY
    return None


def _with_finished_status(state: CombatState) -> CombatState:
    winner = combat_winner(state)
    if winner is None:
        return state
    return replace(state, status=CombatStatus.FINISHED, winner=winner)


def _sync_order_actor_states(order: InitiativeOrder, actors: tuple[Actor, ...]) -> InitiativeOrder:
    actor_map = {actor.id: actor for actor in actors}
    entries: list[InitiativeEntry] = []
    for entry in order.entries:
        actor = actor_map.get(entry.actor.id, entry.actor)
        entries.append(replace(entry, actor=actor))
    return InitiativeOrder(tuple(entries), order.current_index, order.round_number)
