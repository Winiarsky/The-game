from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Sequence

from dnd_board_game.actors import (
    Actor,
    ExhaustionRollKind,
    apply_exhaustion_to_roll_request,
)
from dnd_board_game.inventory import effective_speed_feet
from dnd_board_game.rules import (
    ActiveEffect,
    D20RollInput,
    D20RollKind,
    D20RollRequest,
    EffectDuration,
    EffectEvent,
    EffectEventType,
    RollMode,
    RollModifier,
    RollModifierType,
    SavingThrowRequest,
    SavingThrowEffectTag,
    SavingThrowResult,
    apply_actor_d20_traits,
    resolve_d20_roll,
    resolve_saving_throw_request,
)
from dnd_board_game.world import MovementRangeResult, PathResult

from .attack_flow import AttackSource


class CombatCondition(StrEnum):
    BLINDED = "blinded"
    CHARMED = "charmed"
    DEAFENED = "deafened"
    FRIGHTENED = "frightened"
    PRONE = "prone"
    GRAPPLED = "grappled"
    INCAPACITATED = "incapacitated"
    INVISIBLE = "invisible"
    PARALYZED = "paralyzed"
    PETRIFIED = "petrified"
    POISONED = "poisoned"
    RESTRAINED = "restrained"
    STUNNED = "stunned"
    UNCONSCIOUS = "unconscious"
    RAY_OF_FROST_SLOW = "ray_of_frost_slow"
    NO_REACTIONS = "no_reactions"
    NO_HEALING = "no_healing"
    TURNED = "turned"
    ENFEEBLED = "enfeebled"
    HANDS_BOUND = "hands_bound"
    GAGGED = "gagged"
    HAMSTRUNG = "hamstrung"
    BLEEDING = "bleeding"
    STASIS = "stasis"


class ConditionSaveTiming(StrEnum):
    TURN_START = "turn_start"
    TURN_END = "turn_end"
    ACTION = "action"


@dataclass(frozen=True, slots=True)
class ConditionDefinition:
    condition: CombatCondition
    label: str
    description: str
    speed_zero: bool = False
    attack_disadvantage: bool = False
    attacks_against_advantage: bool = False
    attack_advantage: bool = False
    attacks_against_disadvantage: bool = False
    ability_check_disadvantage: bool = False
    dexterity_save_disadvantage: bool = False
    speed_penalty_feet: int = 0
    speed_halved: bool = False
    reactions_blocked: bool = False
    healing_blocked: bool = False
    actions_blocked: bool = False
    auto_fail_strength_dexterity_saves: bool = False
    critical_within_five_feet: bool = False
    somatic_components_blocked: bool = False
    verbal_components_blocked: bool = False


CONDITION_DEFINITIONS: dict[CombatCondition, ConditionDefinition] = {
    CombatCondition.BLINDED: ConditionDefinition(
        CombatCondition.BLINDED,
        "Oślepiony",
        "Nie widzi; jego ataki mają utrudnienie, a ataki przeciw niemu przewagę.",
        attack_disadvantage=True,
        attacks_against_advantage=True,
    ),
    CombatCondition.CHARMED: ConditionDefinition(
        CombatCondition.CHARMED,
        "Zauroczenie",
        "Nie może atakować źródła zauroczenia; źródło ma przewagę w interakcjach społecznych.",
    ),
    CombatCondition.DEAFENED: ConditionDefinition(
        CombatCondition.DEAFENED,
        "Ogłuchły",
        "Nie słyszy i automatycznie przegrywa testy wymagające słuchu.",
    ),
    CombatCondition.FRIGHTENED: ConditionDefinition(
        CombatCondition.FRIGHTENED,
        "Przerażony",
        "Ma utrudnienie ataków i testów, gdy widzi źródło strachu, i nie może dobrowolnie się do niego zbliżyć.",
        attack_disadvantage=True,
        ability_check_disadvantage=True,
    ),
    CombatCondition.TURNED: ConditionDefinition(
        CombatCondition.TURNED,
        "Odpędzony",
        (
            "Musi oddalać się od źródła, nie może dobrowolnie zbliżyć się na "
            "mniej niż 30 stóp ani używać reakcji; używa akcji Dash albo Dodge, "
            "jeśli nie może się ruszyć. Efekt kończy się po otrzymaniu obrażeń."
        ),
        attack_disadvantage=True,
        reactions_blocked=True,
    ),
    CombatCondition.PRONE: ConditionDefinition(
        CombatCondition.PRONE,
        "Powalony",
        "Ataki aktora mają utrudnienie; wstawanie kosztuje połowę szybkości.",
    ),
    CombatCondition.GRAPPLED: ConditionDefinition(
        CombatCondition.GRAPPLED,
        "Chwytany",
        "Szybkość wynosi 0 do czasu zakończenia chwytu.",
        speed_zero=True,
    ),
    CombatCondition.STASIS: ConditionDefinition(
        CombatCondition.STASIS,
        "Staza",
        "Nie może poruszać się ani używać akcji, akcji dodatkowych i reakcji.",
        speed_zero=True, reactions_blocked=True, actions_blocked=True,
    ),
    CombatCondition.INCAPACITATED: ConditionDefinition(
        CombatCondition.INCAPACITATED,
        "Obezwładniony",
        "Nie może wykonywać akcji ani reakcji.",
        reactions_blocked=True,
        actions_blocked=True,
    ),
    CombatCondition.INVISIBLE: ConditionDefinition(
        CombatCondition.INVISIBLE,
        "Niewidzialny",
        "Ataki aktora mają przewagę, a ataki przeciw niemu utrudnienie, o ile przeciwnik nie ignoruje niewidzialności.",
        attack_advantage=True,
        attacks_against_disadvantage=True,
    ),
    CombatCondition.PARALYZED: ConditionDefinition(
        CombatCondition.PARALYZED,
        "Sparaliżowany",
        "Jest obezwładniony, nie porusza się, automatycznie przegrywa save Siły i Zręczności; trafienia z 5 ft są krytyczne.",
        speed_zero=True,
        attacks_against_advantage=True,
        reactions_blocked=True,
        actions_blocked=True,
        auto_fail_strength_dexterity_saves=True,
        critical_within_five_feet=True,
    ),
    CombatCondition.PETRIFIED: ConditionDefinition(
        CombatCondition.PETRIFIED,
        "Skamieniały",
        "Jest obezwładniony, nie porusza się i automatycznie przegrywa save Siły i Zręczności.",
        speed_zero=True,
        attacks_against_advantage=True,
        reactions_blocked=True,
        actions_blocked=True,
        auto_fail_strength_dexterity_saves=True,
    ),
    CombatCondition.POISONED: ConditionDefinition(
        CombatCondition.POISONED,
        "Zatruty",
        "Ataki i testy cech aktora mają utrudnienie.",
        attack_disadvantage=True,
        ability_check_disadvantage=True,
    ),
    CombatCondition.RESTRAINED: ConditionDefinition(
        CombatCondition.RESTRAINED,
        "Unieruchomiony",
        "Szybkość wynosi 0; ataki aktora i Dexterity saves mają utrudnienie, a ataki przeciw niemu przewagę.",
        speed_zero=True,
        attack_disadvantage=True,
        attacks_against_advantage=True,
        dexterity_save_disadvantage=True,
    ),
    CombatCondition.STUNNED: ConditionDefinition(
        CombatCondition.STUNNED,
        "Ogłuszony",
        "Jest obezwładniony, nie porusza się, automatycznie przegrywa save Siły i Zręczności, a ataki przeciw niemu mają przewagę.",
        speed_zero=True,
        attacks_against_advantage=True,
        reactions_blocked=True,
        actions_blocked=True,
        auto_fail_strength_dexterity_saves=True,
    ),
    CombatCondition.UNCONSCIOUS: ConditionDefinition(
        CombatCondition.UNCONSCIOUS,
        "Nieprzytomny",
        "Jest obezwładniony i powalony; automatycznie przegrywa save Siły i Zręczności, a trafienia z 5 ft są krytyczne.",
        speed_zero=True,
        attacks_against_advantage=True,
        reactions_blocked=True,
        actions_blocked=True,
        auto_fail_strength_dexterity_saves=True,
        critical_within_five_feet=True,
    ),
    CombatCondition.RAY_OF_FROST_SLOW: ConditionDefinition(
        CombatCondition.RAY_OF_FROST_SLOW,
        "Spowolniony przez Promień Mrozu",
        "Szybkość jest zmniejszona o 10 ft do początku następnej tury rzucającego.",
        speed_penalty_feet=10,
    ),
    CombatCondition.NO_REACTIONS: ConditionDefinition(
        CombatCondition.NO_REACTIONS,
        "Bez reakcji",
        "Istota nie może wykonywać reakcji do początku swojej następnej tury.",
        reactions_blocked=True,
    ),
    CombatCondition.NO_HEALING: ConditionDefinition(
        CombatCondition.NO_HEALING,
        "Zablokowane leczenie",
        "Istota nie może odzyskiwać punktów wytrzymałości.",
        healing_blocked=True,
    ),
    CombatCondition.ENFEEBLED: ConditionDefinition(
        CombatCondition.ENFEEBLED,
        "Osłabiony",
        "Ataki bronią oparte na Sile zadają połowę obrażeń; Constitution save na końcu tury kończy efekt.",
    ),
    CombatCondition.HANDS_BOUND: ConditionDefinition(
        CombatCondition.HANDS_BOUND,
        "Związane ręce",
        "Nie może wykonywać komponentów somatycznych czarów.",
        somatic_components_blocked=True,
    ),
    CombatCondition.GAGGED: ConditionDefinition(
        CombatCondition.GAGGED,
        "Zakneblowany",
        "Nie może wykonywać komponentów werbalnych czarów.",
        verbal_components_blocked=True,
    ),
    CombatCondition.HAMSTRUNG: ConditionDefinition(
        CombatCondition.HAMSTRUNG,
        "Przecięte ścięgno",
        "Szybkość jest zmniejszona o połowę do otrzymania leczenia albo oczyszczenia statusu.",
        speed_halved=True,
    ),
    CombatCondition.BLEEDING: ConditionDefinition(
        CombatCondition.BLEEDING,
        "Krwawienie",
        "Na początku swojej tury otrzymuje 1k4 obrażeń do otrzymania leczenia albo oczyszczenia statusu.",
    ),
}


@dataclass(frozen=True, slots=True)
class ConditionState:
    actor_id: str
    condition: CombatCondition
    source_actor_id: str | None = None
    source_label: str = ""
    duration: EffectDuration = EffectDuration.PERMANENT
    expiration_actor_id: str | None = None
    save_ability: str | None = None
    save_dc: int | None = None
    save_timing: ConditionSaveTiming | None = None
    source_spell_id: str | None = None
    source_spell_level: int | None = None
    expiration_event_count: int = 1

    def __post_init__(self) -> None:
        if not self.actor_id:
            raise ValueError("Condition actor id cannot be empty.")
        if self.condition == CombatCondition.GRAPPLED and not self.source_actor_id:
            raise ValueError("Grappled condition requires a source actor id.")
        if self.source_actor_id == self.actor_id:
            raise ValueError("An actor cannot be the source of its own condition.")
        if self.expiration_actor_id is None:
            object.__setattr__(self, "expiration_actor_id", self.actor_id)
        save_fields = (self.save_ability, self.save_dc, self.save_timing)
        if any(value is not None for value in save_fields) and not all(
            value is not None for value in save_fields
        ):
            raise ValueError("Condition save requires ability, DC and timing.")
        if self.save_dc is not None and self.save_dc < 0:
            raise ValueError("Condition save DC cannot be negative.")
        spell_fields = (self.source_spell_id, self.source_spell_level)
        if any(value is not None for value in spell_fields) and not all(
            value is not None for value in spell_fields
        ):
            raise ValueError("Magical condition source requires spell id and level.")
        if self.source_spell_id is not None and not self.source_spell_id.strip():
            raise ValueError("Condition source spell id cannot be empty.")
        if self.source_spell_level is not None and self.source_spell_level < 0:
            raise ValueError("Condition source spell level cannot be negative.")
        if self.expiration_event_count < 1:
            raise ValueError("Condition expiration event count must be positive.")


@dataclass(frozen=True, slots=True)
class ConditionApplicationResult:
    condition_states: tuple[ConditionState, ...]
    applied: bool
    state: ConditionState | None
    message: str


@dataclass(frozen=True, slots=True)
class ConditionSaveResolution:
    condition_states: tuple[ConditionState, ...]
    condition_state: ConditionState
    saving_throw: SavingThrowResult
    removed: bool


def has_condition(
    states: Sequence[ConditionState],
    actor_id: str,
    condition: CombatCondition,
) -> bool:
    return any(state.actor_id == actor_id and state.condition == condition for state in states)


def add_condition(
    states: Sequence[ConditionState],
    actor_id: str,
    condition: CombatCondition,
    *,
    source_actor_id: str | None = None,
    source_label: str = "",
    duration: EffectDuration = EffectDuration.PERMANENT,
    expiration_actor_id: str | None = None,
    save_ability: str | None = None,
    save_dc: int | None = None,
    save_timing: ConditionSaveTiming | None = None,
    source_spell_id: str | None = None,
    source_spell_level: int | None = None,
    expiration_event_count: int = 1,
) -> tuple[ConditionState, ...]:
    candidate = ConditionState(
        actor_id=actor_id,
        condition=condition,
        source_actor_id=source_actor_id,
        source_label=source_label,
        duration=duration,
        expiration_actor_id=expiration_actor_id,
        save_ability=save_ability,
        save_dc=save_dc,
        save_timing=save_timing,
        source_spell_id=source_spell_id,
        source_spell_level=source_spell_level,
        expiration_event_count=expiration_event_count,
    )
    if candidate in states:
        return tuple(states)
    remaining = tuple(
        state
        for state in states
        if not (state.actor_id == actor_id and state.condition == condition)
    )
    return (*remaining, candidate)


def apply_condition(
    states: Sequence[ConditionState],
    actor: Actor,
    condition: CombatCondition,
    *,
    source_actor_id: str | None = None,
    source_label: str = "",
    duration: EffectDuration = EffectDuration.PERMANENT,
    expiration_actor_id: str | None = None,
    save_ability: str | None = None,
    save_dc: int | None = None,
    save_timing: ConditionSaveTiming | None = None,
    source_spell_id: str | None = None,
    source_spell_level: int | None = None,
    expiration_event_count: int = 1,
) -> ConditionApplicationResult:
    definition = condition_definition(condition)
    if condition.value in actor.condition_immunities:
        return ConditionApplicationResult(
            tuple(states),
            False,
            None,
            f"{actor.name} ma odporność na stan {definition.label}.",
        )
    updated = add_condition(
        states,
        str(actor.id),
        condition,
        source_actor_id=source_actor_id,
        source_label=source_label,
        duration=duration,
        expiration_actor_id=expiration_actor_id,
        save_ability=save_ability,
        save_dc=save_dc,
        save_timing=save_timing,
        source_spell_id=source_spell_id,
        source_spell_level=source_spell_level,
        expiration_event_count=expiration_event_count,
    )
    applied_state = next(
        state
        for state in updated
        if state.actor_id == str(actor.id) and state.condition == condition
    )
    return ConditionApplicationResult(
        updated,
        updated != tuple(states),
        applied_state,
        f"Nałożono stan {definition.label} na {actor.name}.",
    )


def condition_definition(condition: CombatCondition) -> ConditionDefinition:
    return CONDITION_DEFINITIONS[condition]


def condition_label(condition: CombatCondition) -> str:
    return condition_definition(condition).label


def expire_condition_states(
    states: Sequence[ConditionState],
    event: EffectEvent,
) -> tuple[tuple[ConditionState, ...], tuple[ConditionState, ...]]:
    kept: list[ConditionState] = []
    expired: list[ConditionState] = []
    for state in states:
        if not _condition_matches_expiration_event(state, event):
            kept.append(state)
        elif (
            event.event_type
            in {
                EffectEventType.SCENARIO_ENDED,
                EffectEventType.LONG_REST_COMPLETED,
                EffectEventType.ENCOUNTER_ENDED,
            }
            or state.expiration_event_count <= 1
        ):
            expired.append(state)
        else:
            kept.append(
                replace(
                    state,
                    expiration_event_count=state.expiration_event_count - 1,
                )
            )
    return tuple(kept), tuple(expired)


def pending_condition_saves(
    states: Sequence[ConditionState],
    actor_id: str,
    timing: ConditionSaveTiming,
) -> tuple[ConditionState, ...]:
    return tuple(
        state
        for state in states
        if state.actor_id == actor_id and state.save_timing == timing
    )


def resolve_condition_save(
    states: Sequence[ConditionState],
    actor: Actor,
    condition_state: ConditionState,
    *,
    natural_roll: int,
    natural_roll_2: int | None = None,
    natural_rerolls: tuple[int, ...] = (),
    combat_actors: Sequence[Actor] = (),
    additional_modifiers: tuple[RollModifier, ...] = (),
    active_effects: Sequence[object] = (),
) -> ConditionSaveResolution:
    from dnd_board_game.actors import saving_throw_roll_modifiers
    from .auras import saving_throw_aura_modifiers
    from .mana_charge import saving_modifiers
    from .poison_protection import poison_protection_roll_mode

    if condition_state.actor_id != str(actor.id):
        raise ValueError("Condition save does not belong to this actor.")
    if condition_state.save_ability is None or condition_state.save_dc is None:
        raise ValueError("Condition does not define a saving throw.")
    request = condition_roll_request(
        D20RollRequest(
            ability=condition_state.save_ability,
            mode=poison_protection_roll_mode(
                actor,
                active_effects,
                (
                    "poison"
                    if condition_state.condition == CombatCondition.POISONED
                    else condition_state.condition.value,
                ),
            ),
            modifiers=(
                *saving_throw_roll_modifiers(actor, condition_state.save_ability),
                *saving_modifiers(actor, condition_state.save_ability, active_effects),
                *saving_throw_aura_modifiers(combat_actors, actor),
                *additional_modifiers,
            )
        ),
        states,
        actor,
        saving_throw_ability=condition_state.save_ability,
    )
    request = apply_exhaustion_to_roll_request(
        actor,
        request,
        ExhaustionRollKind.SAVING_THROW,
    )
    request = apply_actor_d20_traits(
        actor,
        request,
        D20RollKind.SAVING_THROW,
        effect_tags=(
            (
                SavingThrowEffectTag.POISON.value
                if condition_state.condition == CombatCondition.POISONED
                else condition_state.condition.value
            ),
        ),
        active_effects=active_effects,
        condition_states=states,
    )
    if request.mode != RollMode.NORMAL and natural_roll_2 is None:
        raise ValueError("Condition save with advantage or disadvantage requires two d20 rolls.")
    roll = resolve_d20_roll(
        D20RollInput(
            request,
            int(natural_roll),
            natural_roll_2,
            tuple(int(value) for value in natural_rerolls),
        )
    )
    saving_throw = resolve_saving_throw_request(
        SavingThrowRequest(
            ability=condition_state.save_ability,
            dc=condition_state.save_dc,
            source_label=condition_state.source_label or condition_label(condition_state.condition),
            failure_effect_label=f"stan {condition_label(condition_state.condition)} pozostaje",
            success_effect_label=f"stan {condition_label(condition_state.condition)} usunięty",
        ),
        actor_id=str(actor.id),
        actor_name=actor.name,
        roll=roll,
    )
    if condition_auto_fails_saving_throw(
        states,
        str(actor.id),
        condition_state.save_ability,
    ):
        saving_throw = replace(
            saving_throw,
            success=False,
            damage_multiplier=1.0,
        )
    updated = (
        remove_condition(states, str(actor.id), condition_state.condition)
        if saving_throw.success
        else tuple(states)
    )
    return ConditionSaveResolution(updated, condition_state, saving_throw, saving_throw.success)


def remove_condition(
    states: Sequence[ConditionState],
    actor_id: str,
    condition: CombatCondition,
) -> tuple[ConditionState, ...]:
    return tuple(
        state
        for state in states
        if not (state.actor_id == actor_id and state.condition == condition)
    )


def grappled_by(
    states: Sequence[ConditionState],
    actor_id: str,
) -> str | None:
    state = next(
        (
            state
            for state in states
            if state.actor_id == actor_id
            and state.condition == CombatCondition.GRAPPLED
        ),
        None,
    )
    return state.source_actor_id if state is not None else None


def grappled_actor_ids(
    states: Sequence[ConditionState],
    source_actor_id: str,
) -> tuple[str, ...]:
    return tuple(
        state.actor_id
        for state in states
        if state.condition == CombatCondition.GRAPPLED
        and state.source_actor_id == source_actor_id
    )


def remove_grapple(
    states: Sequence[ConditionState],
    actor_id: str,
    *,
    source_actor_id: str | None = None,
) -> tuple[ConditionState, ...]:
    return tuple(
        state
        for state in states
        if not (
            state.actor_id == actor_id
            and state.condition == CombatCondition.GRAPPLED
            and (source_actor_id is None or state.source_actor_id == source_actor_id)
        )
    )


def normalize_grapple_conditions(
    states: Sequence[ConditionState],
    actors: Sequence[Actor],
) -> tuple[ConditionState, ...]:
    """Remove grapples whose source/target cannot maintain a 5 ft hold."""

    actors_by_id = {str(actor.id): actor for actor in actors}
    normalized: list[ConditionState] = []
    for state in states:
        if state.condition != CombatCondition.GRAPPLED:
            normalized.append(state)
            continue
        target = actors_by_id.get(state.actor_id)
        source = actors_by_id.get(state.source_actor_id or "")
        if target is None or source is None or target.is_defeated() or source.is_defeated():
            continue
        distance = max(
            abs(source.position.col - target.position.col),
            abs(source.position.row - target.position.row),
        )
        if distance <= 1:
            normalized.append(state)
    return tuple(normalized)


def standing_movement_cost(actor: Actor) -> int:
    return effective_speed_feet(actor) // 2


def path_with_condition_cost(
    path: PathResult,
    states: Sequence[ConditionState],
    actor_id: str,
    *,
    movement_budget_feet: int | None = None,
) -> PathResult:
    cost = path.cost_feet
    if (
        path.valid
        and path.destination != path.origin
        and any(
            condition_definition(state.condition).speed_zero
            for state in states
            if state.actor_id == actor_id
        )
    ):
        return replace(path, valid=False)
    if path.valid and has_condition(states, actor_id, CombatCondition.PRONE):
        cost += _base_path_distance(path.path)
    valid = path.valid and (
        movement_budget_feet is None or cost <= movement_budget_feet
    )
    return replace(path, cost_feet=cost, valid=valid)


def effective_movement_speed(
    actor: Actor,
    states: Sequence[ConditionState],
    active_effects: Sequence[ActiveEffect] = (),
) -> int:
    base_speed = effective_speed_feet(actor) + sum(
        effect.value
        for effect in active_effects
        if effect.actor_id == str(actor.id)
        and effect.kind == "speed_bonus"
    )
    if any(e.kind == "mana_wave_2" for e in active_effects) and not any(
        e.actor_id == str(actor.id) and e.kind == "mana_blue_movement" for e in active_effects
    ):
        base_speed = max(5, base_speed - 10)
    if any(
        condition_definition(state.condition).speed_zero
        for state in states
        if state.actor_id == str(actor.id)
    ):
        return 0
    if any(
        effect.actor_id == str(actor.id) and effect.kind == "roar_no_movement"
        for effect in active_effects
    ):
        return 0
    if any(
        effect.actor_id == str(actor.id)
        and effect.kind == "garran_command_no_movement"
        for effect in active_effects
    ):
        return 0
    if any(
        effect.actor_id == str(actor.id)
        and effect.kind in {
            "erynd_anchored",
            "erynd_anchor_pending",
            "lorian_entangled_no_movement",
        }
        for effect in active_effects
    ):
        return 0
    if levitation_altitude_feet(str(actor.id), active_effects) > 0:
        # Levitate does not grant horizontal movement. Pulling along a fixed
        # object is handled as an explicit scene interaction, never as normal
        # board movement.
        return 0
    if grappled_actor_ids(states, str(actor.id)):
        return base_speed // 2
    penalty = max(
        (
            condition_definition(state.condition).speed_penalty_feet
            for state in states
            if state.actor_id == str(actor.id)
        ),
        default=0,
    )
    speed = max(0, base_speed - penalty)
    caps = tuple(
        effect.value
        for effect in active_effects
        if effect.actor_id == str(actor.id)
        and effect.kind == "movement_speed_cap"
        and effect.value >= 0
    )
    if caps:
        speed = min(speed, min(caps))
    if any(
        condition_definition(state.condition).speed_halved
        for state in states
        if state.actor_id == str(actor.id)
    ):
        speed //= 2
    if any(
        effect.actor_id == str(actor.id)
        and effect.kind == "garran_command_half_movement"
        for effect in active_effects
    ):
        speed //= 2
    if any(
        effect.actor_id == str(actor.id)
        and effect.kind in {
            "erynd_anchor_half_movement",
            "lorian_entangled_half_movement",
        }
        for effect in active_effects
    ):
        speed //= 2
    return speed


def remove_wound_conditions_after_healing(
    states: Sequence[ConditionState],
    actor_id: str,
    effective_healing: int,
) -> tuple[ConditionState, ...]:
    """Actual HP recovery closes Mira's persistent wound riders."""

    if effective_healing <= 0:
        return tuple(states)
    removable = {CombatCondition.HAMSTRUNG, CombatCondition.BLEEDING}
    return tuple(
        state
        for state in states
        if not (state.actor_id == actor_id and state.condition in removable)
    )


def bleeding_damage_at_turn_start(
    states: Sequence[ConditionState],
    actor_id: str,
    d4_roll: int,
) -> int:
    """Return deterministic bleeding damage for a physical/automatic d4 roll."""

    if not 1 <= int(d4_roll) <= 4:
        raise ValueError("Krwawienie wymaga wyniku k4 od 1 do 4.")
    return int(d4_roll) if has_condition(states, actor_id, CombatCondition.BLEEDING) else 0


def levitation_altitude_feet(
    actor_id: str,
    active_effects: Sequence[ActiveEffect],
) -> int:
    """Return the represented altitude of an actor affected by Levitate."""

    return max(
        (
            effect.value
            for effect in active_effects
            if effect.actor_id == actor_id and effect.kind == "levitate"
        ),
        default=0,
    )


def condition_blocks_reactions(
    states: Sequence[ConditionState],
    actor_id: str,
) -> bool:
    return any(
        state.actor_id == actor_id
        and condition_definition(state.condition).reactions_blocked
        for state in states
    )


def condition_blocks_actions(
    states: Sequence[ConditionState],
    actor_id: str,
) -> bool:
    return any(
        state.actor_id == actor_id
        and condition_definition(state.condition).actions_blocked
        for state in states
    )


def condition_blocks_somatic_components(
    states: Sequence[ConditionState],
    actor_id: str,
) -> bool:
    return any(
        state.actor_id == actor_id
        and condition_definition(state.condition).somatic_components_blocked
        for state in states
    )


def condition_blocks_verbal_components(
    states: Sequence[ConditionState],
    actor_id: str,
) -> bool:
    return any(
        state.actor_id == actor_id
        and condition_definition(state.condition).verbal_components_blocked
        for state in states
    )


def condition_auto_fails_saving_throw(
    states: Sequence[ConditionState],
    actor_id: str,
    ability: str,
) -> bool:
    return ability in {"strength", "dexterity"} and any(
        state.actor_id == actor_id
        and condition_definition(
            state.condition
        ).auto_fail_strength_dexterity_saves
        for state in states
    )


def condition_hit_is_automatic_critical(
    states: Sequence[ConditionState],
    target_id: str,
    *,
    within_five_feet: bool,
) -> bool:
    return within_five_feet and any(
        state.actor_id == target_id
        and condition_definition(state.condition).critical_within_five_feet
        for state in states
    )


def condition_blocks_healing(
    states: Sequence[ConditionState],
    actor_id: str,
) -> bool:
    return any(
        state.actor_id == actor_id
        and condition_definition(state.condition).healing_blocked
        for state in states
    )


def movement_range_with_condition_cost(
    movement: MovementRangeResult,
    states: Sequence[ConditionState],
    actor_id: str,
    *,
    movement_budget_feet: int,
) -> MovementRangeResult:
    costs: dict = {}
    paths: dict = {}
    for tile, path_positions in movement.paths_by_tile.items():
        path = PathResult(
            movement.origin,
            tile,
            path_positions,
            movement.costs_by_tile[tile],
            tile in movement.reachable_tiles,
        )
        adjusted = path_with_condition_cost(
            path,
            states,
            actor_id,
            movement_budget_feet=movement_budget_feet,
        )
        if adjusted.valid:
            costs[tile] = adjusted.cost_feet
            paths[tile] = adjusted.path
    return MovementRangeResult(
        origin=movement.origin,
        reachable_tiles=frozenset(costs),
        costs_by_tile=costs,
        paths_by_tile=paths,
    )


def attack_source_with_prone(
    source: AttackSource,
    states: Sequence[ConditionState],
    attacker: Actor,
    target: Actor,
) -> AttackSource:
    if source.save_ability is not None or source.area is not None:
        return source
    attacker_prone = has_condition(states, str(attacker.id), CombatCondition.PRONE)
    target_prone = has_condition(states, str(target.id), CombatCondition.PRONE)
    target_within_five_feet = max(
        abs(attacker.position.col - target.position.col),
        abs(attacker.position.row - target.position.row),
    ) <= 1
    attacker_conditions = tuple(
        condition_definition(state.condition)
        for state in states
        if state.actor_id == str(attacker.id)
    )
    target_conditions = tuple(
        condition_definition(state.condition)
        for state in states
        if state.actor_id == str(target.id)
    )
    condition_advantage = (
        any(item.attacks_against_advantage for item in target_conditions)
        or any(item.attack_advantage for item in attacker_conditions)
    )
    condition_disadvantage = (
        any(item.attack_disadvantage for item in attacker_conditions)
        or any(item.attacks_against_disadvantage for item in target_conditions)
    )
    chill_touch_undead_disadvantage = (
        attacker.creature_type == "undead"
        and any(
            state.actor_id == str(attacker.id)
            and state.condition == CombatCondition.NO_HEALING
            and state.source_actor_id == str(target.id)
            for state in states
        )
    )
    advantage = (target_prone and target_within_five_feet) or condition_advantage
    disadvantage = (
        attacker_prone
        or (target_prone and not target_within_five_feet)
        or condition_disadvantage
        or chill_touch_undead_disadvantage
    )
    if not advantage and not disadvantage:
        return source

    request = source.attack_roll_request
    mode = _mode_with_factors(request.mode, advantage=advantage, disadvantage=disadvantage)
    modifiers = list(request.modifiers)
    if attacker_prone:
        modifiers.append(_factor("Atak w pozycji powalonej", "prone_attacker"))
    if target_prone:
        modifiers.append(
            _factor(
                "Powalony cel w zasięgu 5 ft" if target_within_five_feet else "Powalony cel dalej niż 5 ft",
                "prone_target_close" if target_within_five_feet else "prone_target_far",
            )
        )
    for definition in attacker_conditions:
        if definition.attack_disadvantage:
            modifiers.append(
                _factor(f"{definition.label}: utrudnienie ataku", f"condition:{definition.condition}:attack")
            )
        if definition.attack_advantage:
            modifiers.append(
                _factor(
                    f"{definition.label}: przewaga ataku",
                    f"condition:{definition.condition}:attack_advantage",
                )
            )
    for definition in target_conditions:
        if definition.attacks_against_advantage:
            modifiers.append(
                _factor(f"{definition.label}: przewaga przeciw celowi", f"condition:{definition.condition}:target")
            )
        if definition.attacks_against_disadvantage:
            modifiers.append(
                _factor(
                    f"{definition.label}: utrudnienie przeciw celowi",
                    f"condition:{definition.condition}:target_disadvantage",
                )
            )
    if chill_touch_undead_disadvantage:
        modifiers.append(
            _factor(
                "Dotyk chłodu: nieumarły atakuje rzucającego z utrudnieniem",
                "chill_touch_undead",
            )
        )
    return replace(
        source,
        attack_roll_request=replace(
            request,
            mode=mode,
            modifiers=tuple(modifiers),
        ),
    )


def condition_roll_request(
    request: D20RollRequest,
    states: Sequence[ConditionState],
    actor: Actor,
    *,
    ability_check: bool = False,
    saving_throw_ability: str | None = None,
) -> D20RollRequest:
    """Apply condition-driven advantage/disadvantage to a non-attack d20 roll."""
    definitions = tuple(
        condition_definition(state.condition)
        for state in states
        if state.actor_id == str(actor.id)
    )
    disadvantage_definitions = tuple(
        definition
        for definition in definitions
        if (ability_check and definition.ability_check_disadvantage)
        or (
            saving_throw_ability == "dexterity"
            and definition.dexterity_save_disadvantage
        )
    )
    if not disadvantage_definitions:
        return request
    mode = _mode_with_factors(request.mode, advantage=False, disadvantage=True)
    modifiers = (
        *request.modifiers,
        *(
            _factor(
                f"{definition.label}: utrudnienie",
                f"condition:{definition.condition}:roll",
            )
            for definition in disadvantage_definitions
        ),
    )
    return replace(request, mode=mode, modifiers=modifiers)


def _condition_matches_expiration_event(
    state: ConditionState,
    event: EffectEvent,
) -> bool:
    if (
        event.event_type == EffectEventType.DAMAGE_TAKEN
        and event.actor_id == state.actor_id
        and state.source_spell_id == "sleep"
    ):
        return True
    if event.event_type == EffectEventType.SCENARIO_ENDED:
        return state.duration != EffectDuration.PERMANENT
    if event.event_type == EffectEventType.LONG_REST_COMPLETED:
        return state.duration != EffectDuration.PERMANENT
    if event.event_type == EffectEventType.ENCOUNTER_ENDED:
        return state.duration in {
            EffectDuration.UNTIL_TURN_START,
            EffectDuration.UNTIL_TURN_END,
            EffectDuration.UNTIL_ROUND_END,
            EffectDuration.UNTIL_NEXT_ATTACK,
            EffectDuration.WHILE_AT_POSITION,
            EffectDuration.CONCENTRATION,
            EffectDuration.UNTIL_ENCOUNTER_END,
        }
    if state.duration == EffectDuration.UNTIL_SHORT_REST:
        return event.event_type == EffectEventType.SHORT_REST_COMPLETED
    if state.save_timing is not None:
        return False
    if state.duration == EffectDuration.UNTIL_TURN_START:
        return (
            event.event_type == EffectEventType.TURN_START
            and event.actor_id == state.expiration_actor_id
        )
    if state.duration == EffectDuration.UNTIL_TURN_END:
        return (
            event.event_type == EffectEventType.TURN_END
            and event.actor_id == state.expiration_actor_id
        )
    return False


def _base_path_distance(path: Sequence) -> int:
    distance = 0
    diagonal_parity = 0
    for origin, destination in zip(path, path[1:]):
        diagonal = origin.col != destination.col and origin.row != destination.row
        if diagonal:
            distance += 10 if diagonal_parity else 5
            diagonal_parity = 1 - diagonal_parity
        else:
            distance += 5
    return distance


def _mode_with_factors(
    current: RollMode,
    *,
    advantage: bool,
    disadvantage: bool,
) -> RollMode:
    if advantage and disadvantage:
        return RollMode.NORMAL
    if advantage:
        return RollMode.NORMAL if current == RollMode.DISADVANTAGE else RollMode.ADVANTAGE
    if disadvantage:
        return RollMode.NORMAL if current == RollMode.ADVANTAGE else RollMode.DISADVANTAGE
    return current


def _factor(label: str, stacking_key: str) -> RollModifier:
    return RollModifier(
        label,
        0,
        RollModifierType.SITUATIONAL,
        stacking_key=stacking_key,
    )
