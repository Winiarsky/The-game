from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from dnd_board_game.actors import Actor, ActorId, Faction, actor_has_feature
from dnd_board_game.inventory import (
    AmmunitionUse,
    HandSlot,
    InventoryItem,
    LootBundle,
    plan_hand_equip,
)
from dnd_board_game.world import Coordinate, PathResult
from dnd_board_game.rules import ActiveEffect
from dnd_board_game.rules.shared_mana import SharedMana

from .action_economy import ActionEconomyCost, ActionUse, consume_action
from .conditions import (
    CombatCondition,
    ConditionState,
    add_condition,
    condition_blocks_actions,
    condition_blocks_reactions,
    effective_movement_speed,
    grappled_actor_ids,
    has_condition,
    normalize_grapple_conditions,
    remove_condition,
    standing_movement_cost,
)
from .initiative import InitiativeEntry, InitiativeOrder
from .long_casting import LongCastState
from .stealth import HiddenState, reveal_actor, reveal_to_observer
from .summoning import SummonedCreatureState


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
    bonus_attacks_remaining: int = 0
    bonus_attack_source_id: str = ""
    bonus_action_spell_cast: bool = False
    leveled_action_spell_cast: bool = False
    movement_action_used: bool = False
    weapon_change_available: bool = True
    shared_speed_halved: bool = False
    shared_bonus_actions_used: int = 0
    rune_special_used: bool = False


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
class ChangeWeaponResult:
    state: CombatState
    accepted: bool
    actor: Actor
    weapon: InventoryItem | None
    replaced_items: tuple[InventoryItem, ...]
    message: str


@dataclass(frozen=True, slots=True)
class DropWeaponResult:
    state: CombatState
    accepted: bool
    actor: Actor
    weapon: InventoryItem | None
    dropped_weapon: DroppedWeapon | None
    message: str


def expend_thrown_weapon(
    state: CombatState,
    actor_id: str,
    item_id: str,
    position: Coordinate,
) -> CombatState:
    """Remove one thrown weapon and place it as recoverable battlefield equipment."""

    actor = next(
        (candidate for candidate in state.actors if str(candidate.id) == actor_id),
        None,
    )
    if actor is None:
        raise ValueError("Nie znaleziono aktora rzucającego bronią.")
    weapon = next(
        (
            item
            for item in actor.inventory
            if item.id == item_id or item.source_ref == item_id
        ),
        None,
    )
    if weapon is None or weapon.kind != "weapon" or not weapon.available:
        raise ValueError("Brak dostępnego egzemplarza rzucanej broni.")
    remaining_quantity = weapon.quantity - 1
    remaining = replace(
        weapon,
        quantity=remaining_quantity,
        equipped=weapon.equipped if remaining_quantity > 0 else False,
        held_in=weapon.held_in if remaining_quantity > 0 else (),
    )
    updated_actor = replace(
        actor,
        inventory=tuple(
            remaining if item.id == weapon.id else item
            for item in actor.inventory
        ),
    )
    thrown = replace(weapon, quantity=1, equipped=False, held_in=())
    dropped = DroppedWeapon(
        id=(
            f"thrown:{actor.id}:{weapon.id}:{state.round_number}:"
            f"{len(state.dropped_weapons)}"
        ),
        source_actor_id=actor.id,
        weapon=thrown,
        position=position,
        dropped_round=state.round_number,
    )
    return replace(
        replace_actor(state, updated_actor),
        dropped_weapons=(*state.dropped_weapons, dropped),
    )


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
class AmmunitionExpenditure:
    shooter_actor_id: ActorId
    shooter_faction: Faction
    ammunition_type: str
    item: InventoryItem
    quantity: int


@dataclass(frozen=True, slots=True)
class BattlefieldLoot:
    id: str
    position: Coordinate
    bundle: LootBundle


@dataclass(frozen=True, slots=True)
class EnemyOutcome:
    actor_id: str
    actor_name: str
    outcome: str
    round_number: int


@dataclass(frozen=True, slots=True)
class EnemyAiRuntimeState:
    profile_id: str = ""
    encounter_seed: int = 7
    starting_morale: int = 0
    morale: int = 0
    used_morale_events: tuple[str, ...] = ()
    previous_targets: tuple[tuple[str, str], ...] = ()
    decision_counts: tuple[tuple[str, int], ...] = ()
    outcomes: tuple[EnemyOutcome, ...] = ()

    @property
    def escaped_actor_ids(self) -> frozenset[str]:
        return frozenset(
            outcome.actor_id
            for outcome in self.outcomes
            if outcome.outcome == "escaped"
        )


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
    ammunition_expenditures: tuple[AmmunitionExpenditure, ...] = ()
    battlefield_loot: tuple[BattlefieldLoot, ...] = ()
    long_casts: tuple[LongCastState, ...] = ()
    summoned_creatures: tuple[SummonedCreatureState, ...] = ()
    enemy_ai: EnemyAiRuntimeState = EnemyAiRuntimeState()
    damage_received_by_actor: tuple[tuple[str, int], ...] = ()
    shared_mana: SharedMana | None = None

    @property
    def round_number(self) -> int:
        return self.initiative_order.round_number


def start_combat(
    actors: tuple[Actor, ...],
    initiative_order: InitiativeOrder,
    hidden_states: tuple[HiddenState, ...] = (),
    condition_states: tuple[ConditionState, ...] = (),
    *,
    mana_excluded: tuple[str, ...] = (),
    rune_deck: tuple[str, ...] | None = None,
) -> CombatState:
    if not actors:
        raise ValueError("Cannot start combat without actors.")
    from dnd_board_game.actors.mana_passives import reset_mana_passives
    actors = tuple(reset_mana_passives(a) for a in actors)
    order = _sync_order_actor_states(initiative_order, actors)
    first_actor = next(actor for actor in actors if actor.id == order.current_actor.id)
    state = CombatState(
        actors=actors,
        initiative_order=order,
        turn_action=_turn_action_for(first_actor, frozenset(), actors),
        hidden_states=hidden_states,
        condition_states=tuple(
            condition
            for condition in condition_states
            if condition.actor_id in {str(actor.id) for actor in actors}
        ),
    )
    from dnd_board_game.actors.resources import uses_shared_mana
    if any(uses_shared_mana(a) for a in actors):
        state = replace(state, shared_mana=SharedMana(turn_actor=str(first_actor.id)))
        if any(f.feature_id == "pooled_mana_v01" for a in actors for f in a.features):
            from dnd_board_game.rules.pooled_mana import new_mana
            from dnd_board_game.rules.shared_mana import sync_pool
            from dnd_board_game.scenarios.pooled_mana_catalog import hero_profile
            heroes = tuple(str(a.id) for a in actors if any(f.feature_id == "pooled_mana_v01" for f in a.features))
            state = replace(state, shared_mana=sync_pool(state.shared_mana, new_mana(heroes, str(first_actor.id), values={h: hero_profile(h)["values"] for h in heroes}, excluded=mana_excluded)))

    if any(any(f.feature_id == "rune_resource_v01" for f in a.features) for a in actors):
        from dnd_board_game.rules.runes import RESOURCE_RUNES, new_runes
        from dnd_board_game.rules.shared_mana import sync_runes
        heroes = tuple(str(a.id) for a in actors if a.faction == Faction.ALLY)
        # Randomness belongs to the caller; absent injection gives a stable deck.
        # Runtime sessions supply an already shuffled deck at combat activation.
        deck = rune_deck if rune_deck is not None else tuple(r for _ in heroes for r in RESOURCE_RUNES)
        state = replace(state, shared_mana=sync_runes(SharedMana(turn_actor=str(first_actor.id)), new_runes(heroes, deck)))
    if any(f.feature_id == "rune_baskets_v02" for a in actors for f in a.features):
        from dnd_board_game.rules.rune_baskets import new_baskets
        from dnd_board_game.scenarios.rune_basket_catalog import load_rune_basket_catalog
        catalog = load_rune_basket_catalog()['heroes']
        capacities = {str(a.id): catalog[str(a.id)]['capacities'] for a in actors
                      if a.faction == Faction.ALLY and str(a.id) in catalog}
        state = replace(state, shared_mana=sync_runes(SharedMana(turn_actor=str(first_actor.id)), new_baskets(capacities)))
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
    damage_received = dict(state.damage_received_by_actor)
    hp_lost = max(0, previous_actor.hp - updated_actor.hp)
    if hp_lost:
        actor_id = str(updated_actor.id)
        damage_received[actor_id] = damage_received.get(actor_id, 0) + hp_lost
    condition_states = state.condition_states
    if updated_actor.hp < previous_actor.hp:
        condition_states = tuple(
            condition
            for condition in condition_states
            if not (
                condition.actor_id == str(updated_actor.id)
                and condition.condition == CombatCondition.TURNED
            )
        )
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
    enemy_ai = state.enemy_ai
    if (
        previous_actor.faction == Faction.ENEMY
        and previous_actor.hp > 0
        and updated_actor.hp <= 0
        and all(
            outcome.actor_id != str(updated_actor.id)
            for outcome in enemy_ai.outcomes
        )
    ):
        enemy_ai = replace(
            enemy_ai,
            outcomes=(
                *enemy_ai.outcomes,
                EnemyOutcome(
                    actor_id=str(updated_actor.id),
                    actor_name=updated_actor.name,
                    outcome="dead",
                    round_number=state.round_number,
                ),
            ),
        )
    synced = replace(
        state,
        actors=actors,
        initiative_order=_sync_order_actor_states(state.initiative_order, actors),
        dropped_weapons=dropped_weapons,
        hidden_states=hidden_states,
        condition_states=normalize_grapple_conditions(condition_states, actors),
        enemy_ai=enemy_ai,
        damage_received_by_actor=tuple(sorted(damage_received.items())),
    )
    return _with_finished_status(synced)


def record_ammunition_expenditure(
    state: CombatState,
    shooter: Actor,
    use: AmmunitionUse,
) -> CombatState:
    """Record ammunition actually fired during this encounter."""

    if state.status != CombatStatus.ACTIVE:
        raise ValueError("Ammunition can only be fired during active combat.")
    entries = tuple(
        AmmunitionExpenditure(
            shooter_actor_id=shooter.id,
            shooter_faction=shooter.faction,
            ammunition_type=use.ammunition_type,
            item=item,
            quantity=item.quantity,
        )
        for item in use.consumed_items
    )
    return replace(state, ammunition_expenditures=(*state.ammunition_expenditures, *entries))


def recoverable_ammunition_quantity(
    state: CombatState,
    ammunition_type: str,
    *,
    faction: Faction = Faction.ALLY,
) -> int:
    fired = sum(
        entry.quantity
        for entry in state.ammunition_expenditures
        if entry.shooter_faction == faction
        and entry.ammunition_type == ammunition_type
    )
    return fired // 2


def finalize_ammunition_recovery(
    state: CombatState,
    winner: Faction | None,
) -> CombatState:
    if winner != Faction.ALLY or state.battlefield_loot:
        return state
    grouped: dict[str, list[AmmunitionExpenditure]] = {}
    for entry in state.ammunition_expenditures:
        if entry.shooter_faction == Faction.ALLY:
            grouped.setdefault(entry.ammunition_type, []).append(entry)
    items: list[InventoryItem] = []
    for ammunition_type, entries in grouped.items():
        remaining_recovery = sum(entry.quantity for entry in entries) // 2
        if remaining_recovery <= 0:
            continue
        recovered_by_id: dict[str, InventoryItem] = {}
        for entry in entries:
            if remaining_recovery <= 0:
                break
            recovered_quantity = min(entry.quantity, remaining_recovery)
            recovered = replace(
                entry.item,
                quantity=recovered_quantity,
                equipped=False,
                held_in=(),
            )
            current = recovered_by_id.get(recovered.id)
            recovered_by_id[recovered.id] = (
                replace(current, quantity=current.quantity + recovered.quantity)
                if current is not None
                else recovered
            )
            remaining_recovery -= recovered_quantity
        items.extend(recovered_by_id.values())
    if not items:
        return state
    defeated_enemy = next(
        (
            actor
            for actor in state.actors
            if actor.faction == Faction.ENEMY and actor.is_defeated()
        ),
        None,
    )
    position = (
        defeated_enemy.position
        if defeated_enemy is not None
        else next(
            actor.position
            for actor in state.actors
            if actor.faction == Faction.ALLY and not actor.is_defeated()
        )
    )
    bundle = LootBundle(
        id="battlefield:recovered_ammunition",
        label="Odzyskana amunicja",
        items=tuple(items),
    )
    return replace(
        state,
        battlefield_loot=(
            BattlefieldLoot(
                id="recovered_ammunition",
                position=position,
                bundle=bundle,
            ),
        ),
    )


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
    from .runes import rune_resolution
    if rune_resolution(state):
        return TurnActionUseResult(state, True, "Koszt mocy runicznej został opłacony.")
    if state.status != CombatStatus.ACTIVE:
        return TurnActionUseResult(state, False, "Walka nie jest aktywna.")
    actor = current_actor(state)
    if condition_blocks_actions(state.condition_states, str(actor.id)):
        return TurnActionUseResult(
            state,
            False,
            "Stan aktywnego aktora blokuje wykonywanie akcji.",
        )
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
    if (
        acting.id != current_actor(state).id
        or acting.is_defeated()
        or condition_blocks_actions(state.condition_states, str(acting.id))
    ):
        return 0
    turn = state.turn_action
    if turn.attack_action_active:
        return max(0, turn.attacks_maximum - turn.attacks_used)
    from .runes import rune_resolution
    if rune_resolution(state):
        return acting.attacks_per_action
    if turn.action_use == ActionUse.ACTION_AVAILABLE:
        return 1 if state.shared_mana and state.shared_mana.runes else acting.attacks_per_action
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
        from .runes import rune_resolution
        if turn.action_use != ActionUse.ACTION_AVAILABLE and not rune_resolution(state):
            return TurnActionUseResult(state, False, "Akcja w tej turze została już zużyta.")
        maximum = acting.attacks_per_action if maximum_attacks is None else int(maximum_attacks)
        if state.shared_mana and state.shared_mana.runes and not rune_resolution(state):
            maximum = 1
        if maximum < 1:
            return TurnActionUseResult(state, False, "Liczba ataków musi być dodatnia.")
        updated = replace(
            turn,
            action_use=turn.action_use if rune_resolution(state) else ActionUse.ACTION_USED,
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
    from .runes import rune_resolution
    if rune_resolution(state):
        return TurnActionUseResult(state, True, "Koszt mocy runicznej został opłacony.")
    if state.status != CombatStatus.ACTIVE:
        return TurnActionUseResult(state, False, "Walka nie jest aktywna.")
    actor = current_actor(state)
    if condition_blocks_actions(state.condition_states, str(actor.id)):
        return TurnActionUseResult(
            state,
            False,
            "Stan aktywnego aktora blokuje wykonywanie akcji bonusowych.",
        )
    if state.shared_mana is not None:
        maximum = shared_bonus_action_limit(state, actor)
        used = state.turn_action.shared_bonus_actions_used
        if used >= maximum:
            return TurnActionUseResult(state, False, "Akcje dodatkowe w tej turze zostały zużyte.")
        return TurnActionUseResult(replace(state, turn_action=replace(state.turn_action,
            shared_bonus_actions_used=used+1,
            bonus_action_use=ActionUse.ACTION_AVAILABLE if used+1 < maximum else ActionUse.ACTION_USED)),
            True, "Wykorzystano akcję dodatkową.")
    try:
        bonus_action_use = consume_action(state.turn_action.bonus_action_use)
    except ValueError:
        return TurnActionUseResult(state, False, "Akcja bonusowa w tej turze została już zużyta.")
    return TurnActionUseResult(
        replace(state, turn_action=replace(state.turn_action, bonus_action_use=bonus_action_use)),
        True,
        "Akcja bonusowa została zużyta.",
    )


def grant_bonus_attacks(
    state: CombatState,
    *,
    count: int,
    source_id: str,
) -> CombatState:
    if count < 1 or not source_id.strip():
        raise ValueError("Bonusowe ataki wymagają dodatniej liczby i źródła.")
    return replace(
        state,
        turn_action=replace(
            state.turn_action,
            bonus_attacks_remaining=count,
            bonus_attack_source_id=source_id,
        ),
    )


def use_bonus_attack(
    state: CombatState,
    *,
    source_id: str,
) -> TurnActionUseResult:
    turn = state.turn_action
    if (
        turn.bonus_attacks_remaining < 1
        or turn.bonus_attack_source_id != source_id
    ):
        return TurnActionUseResult(
            state,
            False,
            "Ten bonusowy atak nie jest dostępny.",
        )
    remaining = turn.bonus_attacks_remaining - 1
    return TurnActionUseResult(
        replace(
            state,
            turn_action=replace(
                turn,
                bonus_attacks_remaining=remaining,
                bonus_attack_source_id=(
                    turn.bonus_attack_source_id if remaining else ""
                ),
            ),
        ),
        True,
        f"Wykorzystano bonusowy atak. Pozostało: {remaining}.",
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


def change_weapon(state: CombatState, weapon_id: str) -> ChangeWeaponResult:
    """Select one active weapon using the simplified once-per-turn loadout change.

    The older object-interaction based equip/stow functions remain available to
    rules fixtures, but the board-game combat UI uses this atomic operation.
    A one-handed weapon preserves an equipped shield when possible; a two-handed
    weapon puts away every other held item.
    """

    actor = current_actor(state)
    if actor.faction != Faction.ALLY or actor.is_defeated():
        return ChangeWeaponResult(
            state, False, actor, None, (), "Ten aktor nie może zmienić broni."
        )
    weapon = next((item for item in actor.inventory if item.id == weapon_id), None)
    if weapon is None:
        return ChangeWeaponResult(
            state, False, actor, None, (), "Tej broni nie ma w ekwipunku bohatera."
        )
    if weapon.kind != "weapon" or not weapon.available or weapon.quantity <= 0:
        return ChangeWeaponResult(
            state, False, actor, weapon, (), "Ten przedmiot nie jest dostępną bronią."
        )
    if weapon.equipped:
        return ChangeWeaponResult(
            state,
            True,
            actor,
            weapon,
            (),
            f"{weapon.name} jest już aktywną bronią {actor.name}.",
        )
    if not state.turn_action.weapon_change_available:
        return ChangeWeaponResult(
            state,
            False,
            actor,
            weapon,
            (),
            "Darmowa zmiana broni w tej turze została już wykorzystana.",
        )

    # The simplified selector represents a complete loadout swap, not a series
    # of individual stow/draw interactions. Keep a shield for a one-handed
    # weapon, but free both hands for a two-handed weapon.
    required_hands = max(1, weapon.hands_required)
    retained_shield_ids = {
        item.id
        for item in actor.inventory
        if required_hands == 1 and item.kind == "shield" and item.equipped
    }
    replaced = tuple(
        item
        for item in actor.inventory
        if item.equipped and item.id != weapon_id and item.id not in retained_shield_ids
    )
    base_inventory = tuple(
        replace(item, equipped=False, held_in=())
        if item.id in {entry.id for entry in replaced}
        else item
        for item in actor.inventory
    )
    plan = plan_hand_equip(base_inventory, weapon_id)
    updated_actor = replace(actor, inventory=plan.inventory)
    updated_state = replace_actor(
        replace(
            state,
            turn_action=replace(
                state.turn_action,
                weapon_change_available=False,
                two_weapon_trigger_item_id=None,
            ),
        ),
        updated_actor,
    )
    equipped = next(item for item in updated_actor.inventory if item.id == weapon_id)
    previous = ", ".join(item.name for item in replaced)
    detail = f"; odłożono: {previous}" if previous else ""
    return ChangeWeaponResult(
        updated_state,
        True,
        updated_actor,
        equipped,
        replaced,
        f"{actor.name} wybiera broń: {equipped.name}{detail}. Darmowa zmiana broni została wykorzystana.",
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
        and not condition_blocks_reactions(state.condition_states, str(actor.id))
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
    from .runes import rune_resolution
    if rune_resolution(state) and cost in {ActionEconomyCost.ACTION, ActionEconomyCost.BONUS_ACTION}:
        return True
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


def movement_remaining(
    state: CombatState,
    actor: Actor,
    active_effects: tuple[ActiveEffect, ...] = (),
) -> int:
    if state.shared_mana and any(e.actor_id == str(actor.id) and e.kind == "smoke_screen_hide_pending" for e in active_effects):
        return state.shared_mana.smoke_movement if effective_movement_speed(actor, state.condition_states, active_effects) > 0 else 0
    if state.shared_mana and state.shared_mana.pending_actor == str(actor.id) and state.shared_mana.pending_ability in {"unstoppable", "blade_dance"}:
        if effective_movement_speed(actor, state.condition_states, active_effects) <= 0:
            return 0
        return state.shared_mana.technique_movement
    if state.turn_action.movement_action_used:
        return 0
    speed = effective_movement_speed(actor, state.condition_states, active_effects)
    if state.turn_action.shared_speed_halved:
        speed = (speed // 10) * 5
    if actor_has_feature(actor, "mira_shadow_stealth") and any(
        hidden.actor_id == str(actor.id) for hidden in state.hidden_states
    ):
        speed = min(speed, 20)
    return max(0, speed + state.turn_action.extra_movement_feet - state.turn_action.movement_used_feet)


def use_movement_action(state: CombatState, actor: Actor) -> TurnMovementUseResult:
    """Spend the whole voluntary movement budget on a Garran movement technique."""

    from .runes import rune_resolution
    if rune_resolution(state) and state.turn_action.movement_action_used:
        return TurnMovementUseResult(state, True, "Cały ruch opłacono przy zatwierdzeniu mocy.", 0)
    if state.status != CombatStatus.ACTIVE or actor.id != current_actor(state).id:
        return TurnMovementUseResult(state, False, "To nie jest aktywna tura tego aktora.", 0)
    if actor.is_defeated():
        return TurnMovementUseResult(state, False, "Pokonany aktor nie może działać.", 0)
    if state.turn_action.movement_action_used:
        return TurnMovementUseResult(state, False, "Akcja ruchu została już wykorzystana.", 0)
    if state.turn_action.movement_used_feet > 0:
        return TurnMovementUseResult(
            state,
            False,
            "Technikę ruchową trzeba wybrać przed dobrowolnym ruchem.",
            movement_remaining(state, actor),
        )
    updated = replace(
        state,
        turn_action=replace(state.turn_action, movement_action_used=True),
    )
    return TurnMovementUseResult(updated, True, "Wykorzystano akcję ruchu.", 0)


def use_dash(
    state: CombatState,
    actor: Actor,
    active_effects: tuple[ActiveEffect, ...] = (),
) -> TurnActionUseResult:
    if actor.id != current_actor(state).id:
        return TurnActionUseResult(state, False, "To nie jest tura tego aktora.")
    bonus_action_dash = actor_has_feature(actor, "cunning_action") or any(
        effect.actor_id == str(actor.id)
        and effect.kind == "bonus_action_dash"
        for effect in active_effects
    )
    action_result = (
        use_bonus_action(state)
        if bonus_action_dash
        and state.turn_action.bonus_action_use == ActionUse.ACTION_AVAILABLE
        else use_turn_action(state)
    )
    if not action_result.accepted:
        return action_result
    dash_speed = effective_movement_speed(
        actor,
        state.condition_states,
        active_effects,
    )
    if state.turn_action.shared_speed_halved:
        dash_speed = (dash_speed // 10) * 5
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


def use_movement(
    state: CombatState,
    actor: Actor,
    path: PathResult,
    active_effects: tuple[ActiveEffect, ...] = (),
) -> TurnMovementUseResult:
    remaining = movement_remaining(state, actor, active_effects)
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
    technique = state.shared_mana and state.shared_mana.pending_actor == str(actor.id) and state.shared_mana.pending_ability in {"unstoppable", "blade_dance"}
    smoke = state.shared_mana and any(e.actor_id == str(actor.id) and e.kind == "smoke_screen_hide_pending" for e in active_effects)
    if smoke:
        updated_state = replace(updated_state, shared_mana=replace(state.shared_mana, smoke_movement=state.shared_mana.smoke_movement-path.cost_feet))
    if technique:
        updated_state = replace(updated_state, shared_mana=replace(state.shared_mana, technique_movement=state.shared_mana.technique_movement-path.cost_feet))
    movement_used = state.turn_action.movement_used_feet + (0 if technique or smoke else path.cost_feet)
    updated_state = replace(updated_state, turn_action=replace(updated_state.turn_action, movement_used_feet=movement_used))
    updated_remaining = movement_remaining(
        updated_state,
        updated_actor,
        active_effects,
    )
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
    ending_actor = current_actor(finished_state)
    if actor_has_feature(ending_actor, "mira_shadow_stealth"):
        hidden_states = finished_state.hidden_states
        for observer in finished_state.actors:
            if (
                observer.faction not in {ending_actor.faction, Faction.NEUTRAL}
                and not observer.is_defeated()
                and max(
                    abs(observer.position.col - ending_actor.position.col),
                    abs(observer.position.row - ending_actor.position.row),
                ) <= 1
            ):
                hidden_states = reveal_to_observer(
                    hidden_states,
                    str(ending_actor.id),
                    str(observer.id),
                )
        finished_state = replace(finished_state, hidden_states=hidden_states)
    order = _sync_order_actor_states(
        finished_state.initiative_order,
        finished_state.actors,
    ).advance_turn(
        skip_defeated=True,
        skip_actor_ids=finished_state.enemy_ai.escaped_actor_ids,
    )
    next_actor = actor_by_id(finished_state, order.current_actor.id)
    mana = finished_state.shared_mana
    if mana is not None:
        from dnd_board_game.rules.shared_mana import begin_mana_turn
        mana = begin_mana_turn(mana, str(next_actor.id), round_end=order.round_number > finished_state.round_number)
    spent = frozenset(actor_id for actor_id in finished_state.spent_reaction_actor_ids if actor_id != next_actor.id)
    from dnd_board_game.rules.rune_baskets import RuneBaskets
    if mana and isinstance(mana.runes, RuneBaskets):
        spent = frozenset() if order.round_number > finished_state.round_number else finished_state.spent_reaction_actor_ids
    return replace(
        finished_state,
        initiative_order=order,
        spent_reaction_actor_ids=spent,
        turn_action=_turn_action_for(next_actor, spent, finished_state.actors),
        shared_mana=mana,
    )


def _turn_action_for(
    actor: Actor,
    spent_reaction_actor_ids: frozenset[ActorId],
    actors: tuple[Actor, ...] = (),
) -> TurnActionState:
    if actor.is_defeated():
        return TurnActionState(
            action_use=ActionUse.ACTION_USED,
            bonus_action_use=ActionUse.ACTION_USED,
            reaction_available=False,
            movement_used_feet=actor.speed_feet,
            object_interaction_available=False,
        )
    from dnd_board_game.actors.resources import uses_shared_mana
    from .runes import uses_runes
    halved = uses_shared_mana(actor) and not uses_runes(actor) and str(actor.id) == "garran" and any(
        a.faction not in {actor.faction, Faction.NEUTRAL} and not a.is_defeated()
        and max(abs(a.position.col-actor.position.col), abs(a.position.row-actor.position.row)) <= 1
        for a in actors)
    return TurnActionState(reaction_available=actor.id not in spent_reaction_actor_ids, shared_speed_halved=halved)


def hymn_affects(source: Actor, actor: Actor) -> bool:
    return (source.faction == actor.faction and not source.is_unconscious()
            and not source.is_defeated()
            and max(abs(source.position.col-actor.position.col), abs(source.position.row-actor.position.row))*5 <= 30)


def shared_bonus_action_limit(state: CombatState, actor: Actor) -> int:
    if state.shared_mana is None:
        return 1
    return 2 if any(str(source.id) in state.shared_mana.hymn_sources
                    and hymn_affects(source, actor)
                    for source in state.actors) else 1


def stop_combat(state: CombatState) -> CombatState:
    return replace(state, status=CombatStatus.STOPPED, long_casts=())


def combat_is_finished(state: CombatState) -> bool:
    return state.status == CombatStatus.FINISHED or combat_winner(state) is not None


def refresh_combat_status(state: CombatState) -> CombatState:
    return _with_finished_status(state)


def combat_winner(state: CombatState) -> Faction | None:
    allies_alive = any(
        actor.faction == Faction.ALLY and actor.can_take_combat_turn()
        for actor in state.actors
    )
    enemies_alive = any(
        actor.faction == Faction.ENEMY
        and str(actor.id) not in state.enemy_ai.escaped_actor_ids
        and actor.can_take_combat_turn()
        for actor in state.actors
    )
    if allies_alive and not enemies_alive:
        return Faction.ALLY
    if enemies_alive and not allies_alive:
        return Faction.ENEMY
    return None


def initialize_enemy_ai(
    state: CombatState,
    *,
    profile_id: str,
    starting_morale: int,
    encounter_seed: int = 7,
) -> CombatState:
    if not profile_id:
        return state
    return replace(
        state,
        enemy_ai=EnemyAiRuntimeState(
            profile_id=profile_id,
            encounter_seed=encounter_seed,
            starting_morale=starting_morale,
            morale=starting_morale,
        ),
    )


def apply_enemy_ai_morale_delta(
    state: CombatState,
    *,
    event_id: str,
    delta: int,
    minimum: int = 0,
    maximum: int | None = None,
) -> CombatState:
    """Apply a one-shot authored morale event without loading content in rules code."""

    if not state.enemy_ai.profile_id or event_id in state.enemy_ai.used_morale_events:
        return state
    upper = state.enemy_ai.starting_morale if maximum is None else maximum
    morale = max(minimum, min(upper, state.enemy_ai.morale + delta))
    return replace(
        state,
        enemy_ai=replace(
            state.enemy_ai,
            morale=morale,
            used_morale_events=(*state.enemy_ai.used_morale_events, event_id),
        ),
    )


def escape_enemy(state: CombatState, actor_id: ActorId) -> CombatState:
    actor = actor_by_id(state, actor_id)
    if actor.faction != Faction.ENEMY:
        raise ValueError("Only an active enemy can escape an encounter.")
    if actor.is_defeated():
        raise ValueError("A defeated enemy cannot escape.")
    if str(actor.id) in state.enemy_ai.escaped_actor_ids:
        return state
    enemy_ai = replace(
        state.enemy_ai,
        outcomes=(
            *state.enemy_ai.outcomes,
            EnemyOutcome(
                actor_id=str(actor.id),
                actor_name=actor.name,
                outcome="escaped",
                round_number=state.round_number,
            ),
        ),
    )
    escaped_actor = replace(actor, faction=Faction.NEUTRAL)
    return _with_finished_status(
        replace(
            state,
            actors=tuple(
                escaped_actor if candidate.id == actor.id else candidate
                for candidate in state.actors
            ),
            initiative_order=_sync_order_actor_states(
                state.initiative_order,
                tuple(
                    escaped_actor if candidate.id == actor.id else candidate
                    for candidate in state.actors
                ),
            ),
            enemy_ai=enemy_ai,
        )
    )


def _with_finished_status(state: CombatState) -> CombatState:
    winner = combat_winner(state)
    if winner is None:
        return state
    finished = replace(
        state,
        status=CombatStatus.FINISHED,
        winner=winner,
        long_casts=(),
    )
    return finalize_ammunition_recovery(finished, winner)


def _sync_order_actor_states(order: InitiativeOrder, actors: tuple[Actor, ...]) -> InitiativeOrder:
    actor_map = {actor.id: actor for actor in actors}
    entries: list[InitiativeEntry] = []
    for entry in order.entries:
        actor = actor_map.get(entry.actor.id, entry.actor)
        entries.append(replace(entry, actor=actor))
    return InitiativeOrder(tuple(entries), order.current_index, order.round_number)
