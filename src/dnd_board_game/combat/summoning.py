from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    CreatureSize,
)
from dnd_board_game.rules import (
    D20RollRequest,
    RollModifier,
    RollModifierType,
)
from dnd_board_game.world import BoardState, Coordinate, line_of_sight_clear

from .attack_flow import AttackKind, AttackSource, AttackSourceType
from .damage import DamageType
from .initiative import InitiativeEntry, InitiativeOrder
from .spells import grid_distance_feet

if TYPE_CHECKING:
    from .session import CombatState


@dataclass(frozen=True, slots=True)
class SummonDefinition:
    id: str
    name: str
    size: CreatureSize
    ac: int
    hp: int
    speed_feet: int
    ability_scores: AbilityScores
    attack_id: str
    attack_name: str
    attack_bonus: int
    attack_range_feet: int
    attack_damage_fixed: int
    attack_damage_type: DamageType

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.name.strip():
            raise ValueError("Summon definition requires an id and name.")
        if self.ac < 0 or self.hp < 1 or self.speed_feet < 0:
            raise ValueError("Summon defensive statistics are invalid.")
        if not self.attack_id.strip() or not self.attack_name.strip():
            raise ValueError("Summon attack requires an id and name.")
        if self.attack_range_feet < 5 or self.attack_range_feet % 5:
            raise ValueError("Summon attack range must be a positive multiple of 5.")
        if self.attack_damage_fixed < 0:
            raise ValueError("Summon attack damage cannot be negative.")


@dataclass(frozen=True, slots=True)
class SummonedCreatureState:
    actor_id: ActorId
    owner_actor_id: ActorId
    spell_id: str
    definition: SummonDefinition
    concentration_effect_id: str

    def __post_init__(self) -> None:
        if not self.spell_id.strip() or not self.concentration_effect_id.strip():
            raise ValueError("Summoned creature requires spell and effect ids.")


def legal_summon_positions(
    board: BoardState,
    state: CombatState,
    caster: Actor,
    *,
    range_feet: int,
) -> tuple[Coordinate, ...]:
    occupied = {
        actor.position
        for actor in state.actors
        if not actor.is_defeated()
    }
    positions: list[Coordinate] = []
    for row in range(board.dimensions.rows):
        for col in range(board.dimensions.cols):
            position = Coordinate(col, row)
            if (
                position in occupied
                or board.terrain_at(position).blocks_movement
                or grid_distance_feet(caster.position, position) > range_feet
                or not line_of_sight_clear(board, caster.position, position)
            ):
                continue
            positions.append(position)
    return tuple(sorted(positions))


def summon_actor(
    definition: SummonDefinition,
    *,
    actor_id: ActorId,
    owner: Actor,
    position: Coordinate,
) -> Actor:
    return Actor(
        id=actor_id,
        name=definition.name,
        ac=definition.ac,
        hp=definition.hp,
        max_hp=definition.hp,
        temp_hp=0,
        speed_feet=definition.speed_feet,
        position=position,
        faction=owner.faction,
        ability_scores=definition.ability_scores,
        size=definition.size,
        uses_death_saves=False,
    )


def summon_attack_source(
    definition: SummonDefinition,
    owner: Actor | None = None,
) -> AttackSource:
    owner_spell_attack = (
        definition.id == "spiritual_weapon"
        and owner is not None
    )
    attack_bonus = (
        owner.spell_save_dc - 8
        if owner_spell_attack
        else definition.attack_bonus
    )
    damage_modifier = (
        max(
            0,
            owner.spell_save_dc - 8 - owner.proficiency_bonus,
        )
        if owner_spell_attack
        else 0
    )
    from dnd_board_game.actors.resources import uses_shared_mana
    from dnd_board_game.rules import DiceExpression
    from .damage import DamageComponentSpec
    shared_weapon = owner_spell_attack and uses_shared_mana(owner)
    return AttackSource(
        name=definition.attack_name,
        source_type=AttackSourceType.CUSTOM,
        range_feet=definition.attack_range_feet,
        attack_roll_request=D20RollRequest(
            modifiers=(
                RollModifier(
                    (
                        "Premia ataku czarami właściciela"
                        if owner_spell_attack
                        else "Premia ataku przywołanej istoty"
                    ),
                    attack_bonus,
                    RollModifierType.CUSTOM,
                ),
            )
        ),
        damage_components=(DamageComponentSpec("spiritual_weapon", definition.attack_damage_type, dice=DiceExpression(2, 8), modifier=damage_modifier, label="Duchowy oręż"),) if shared_weapon else (),
        damage_hint=(
            f"{2 if shared_weapon else 1}d8 + {damage_modifier}"
            if owner_spell_attack
            else ""
        ),
        damage_fixed=(
            None
            if owner_spell_attack
            else definition.attack_damage_fixed
        ),
        damage_die_sides=8 if owner_spell_attack else None,
        damage_modifier=damage_modifier,
        damage_type=definition.attack_damage_type.value,
        id=definition.attack_id,
        attack_kind=(
            AttackKind.MELEE
            if definition.attack_range_feet <= 5
            else AttackKind.RANGED
        ),
        reach_feet=5 if definition.attack_range_feet <= 5 else None,
    )


def add_summoned_creature(
    state: CombatState,
    summon: SummonedCreatureState,
    actor: Actor,
) -> CombatState:
    if any(candidate.id == actor.id for candidate in state.actors):
        raise ValueError(f"Summoned actor id already exists: {actor.id}.")
    owner_index = next(
        (
            index
            for index, entry in enumerate(state.initiative_order.entries)
            if entry.actor.id == summon.owner_actor_id
        ),
        None,
    )
    if owner_index is None:
        raise ValueError("Summon owner is absent from initiative.")
    from dnd_board_game.actors.resources import uses_physical_mana
    owner = next(a for a in state.actors if a.id == summon.owner_actor_id)
    if uses_physical_mana(owner) and summon.spell_id == "spiritual_weapon":
        return replace(state, actors=(*state.actors, actor), summoned_creatures=(*state.summoned_creatures, summon))
    owner_entry = state.initiative_order.entries[owner_index]
    entry = InitiativeEntry(
        actor=actor,
        roll=owner_entry.roll,
        dexterity_modifier=owner_entry.dexterity_modifier,
        stable_order=max(
            (item.stable_order for item in state.initiative_order.entries),
            default=0,
        )
        + 1,
    )
    entries = list(state.initiative_order.entries)
    insert_index = owner_index + 1
    entries.insert(insert_index, entry)
    current_index = state.initiative_order.current_index
    if insert_index <= current_index:
        current_index += 1
    return replace(
        state,
        actors=(*state.actors, actor),
        initiative_order=InitiativeOrder(
            tuple(entries),
            current_index,
            state.round_number,
        ),
        summoned_creatures=(*state.summoned_creatures, summon),
    )


def remove_summons(
    state: CombatState,
    *,
    owner_actor_id: ActorId | str | None = None,
    spell_id: str | None = None,
) -> tuple[CombatState, tuple[SummonedCreatureState, ...]]:
    owner_key = str(owner_actor_id) if owner_actor_id is not None else None
    removed = tuple(
        summon
        for summon in state.summoned_creatures
        if (owner_key is None or str(summon.owner_actor_id) == owner_key)
        and (spell_id is None or summon.spell_id == spell_id)
    )
    if not removed:
        return state, ()
    removed_ids = {summon.actor_id for summon in removed}
    actors = tuple(actor for actor in state.actors if actor.id not in removed_ids)
    order = _initiative_without_actor_ids(
        state.initiative_order,
        removed_ids,
    )
    updated = replace(
        state,
        actors=actors,
        initiative_order=order,
        summoned_creatures=tuple(
            summon
            for summon in state.summoned_creatures
            if summon.actor_id not in removed_ids
        ),
        spent_reaction_actor_ids=frozenset(
            actor_id
            for actor_id in state.spent_reaction_actor_ids
            if actor_id not in removed_ids
        ),
        condition_states=tuple(
            condition
            for condition in state.condition_states
            if condition.actor_id not in {str(actor_id) for actor_id in removed_ids}
        ),
        hidden_states=tuple(
            hidden
            for hidden in state.hidden_states
            if hidden.actor_id not in {str(actor_id) for actor_id in removed_ids}
        ),
    )
    from .session import refresh_combat_status

    return refresh_combat_status(updated), removed


def summoned_state_for_actor(
    summons: tuple[SummonedCreatureState, ...],
    actor_id: ActorId | str,
) -> SummonedCreatureState | None:
    actor_key = str(actor_id)
    return next(
        (summon for summon in summons if str(summon.actor_id) == actor_key),
        None,
    )


def _initiative_without_actor_ids(
    order: InitiativeOrder,
    removed_ids: set[ActorId],
) -> InitiativeOrder:
    entries = tuple(
        entry for entry in order.entries if entry.actor.id not in removed_ids
    )
    if not entries:
        raise ValueError("Cannot remove every actor from initiative.")
    current_id = order.current_actor.id
    if current_id not in removed_ids:
        current_index = next(
            index
            for index, entry in enumerate(entries)
            if entry.actor.id == current_id
        )
        return InitiativeOrder(entries, current_index, order.round_number)
    original_ids = tuple(entry.actor.id for entry in order.entries)
    next_id: ActorId | None = None
    for offset in range(1, len(original_ids) + 1):
        candidate = original_ids[(order.current_index + offset) % len(original_ids)]
        if candidate not in removed_ids:
            next_id = candidate
            break
    assert next_id is not None
    current_index = next(
        index for index, entry in enumerate(entries) if entry.actor.id == next_id
    )
    return InitiativeOrder(entries, current_index, order.round_number)
