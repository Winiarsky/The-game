"""Deterministic casting boundary for exploration and narrative spells."""

from __future__ import annotations

from dataclasses import dataclass, replace

from dnd_board_game.actors import Actor
from dnd_board_game.combat import (
    AppliedHealingResult,
    HealingSource,
    HealingSourceType,
    SpellCastingKind,
    actor_spell_cast_validation,
    apply_healing_result,
    consume_spell_resource,
    grid_distance_feet,
    set_scene_flag,
)
from dnd_board_game.exploration import (
    ExplorationState,
    TimedMagicEffect,
    advance_exploration_time,
    apply_timed_magic_effect,
)
from dnd_board_game.rules import (
    ability_modifier,
    spell_duration_minutes,
    spellcasting_ability_for_spell,
)


@dataclass(frozen=True, slots=True)
class ExplorationSpellCastResult:
    actors: tuple[Actor, ...]
    state: ExplorationState
    actor_before: Actor
    actor_after: Actor
    spell_id: str
    spell_name: str
    cast_level: int
    cast_flag: str
    target_id: str
    timed_effect: TimedMagicEffect | None
    healing_results: tuple[AppliedHealingResult, ...] = ()
    elapsed_minutes: int = 0
    expired_effects: tuple[TimedMagicEffect, ...] = ()
    triggered_clock_events: tuple[object, ...] = ()


class ExplorationSpellCastingFlowService:
    def cast(
        self,
        *,
        actors: tuple[Actor, ...],
        state: ExplorationState,
        actor_id: str,
        spell_id: str,
        cast_level: int | None = None,
        target_id: str = "",
        target_ids: tuple[str, ...] = (),
        healing_roll: int | None = None,
    ) -> ExplorationSpellCastResult:
        actor = next(
            (candidate for candidate in actors if str(candidate.id) == actor_id),
            None,
        )
        if actor is None:
            raise ValueError(f"Nieznany aktor czaru: {actor_id}.")
        spell = next(
            (candidate for candidate in actor.spells if candidate.id == spell_id),
            None,
        )
        if spell is None:
            raise ValueError(f"Aktor {actor.name} nie zna czaru {spell_id}.")
        validation = actor_spell_cast_validation(actor, spell_id)
        if validation is None or not validation.valid:
            errors = validation.errors if validation is not None else ()
            raise ValueError(" ".join(errors) or f"Nie można rzucić {spell.name}.")
        selected_level = int(cast_level or spell.level)
        if selected_level not in validation.available_cast_levels:
            raise ValueError(
                f"{spell.name} nie może zostać rzucony ze slotu {selected_level}."
            )
        resource = consume_spell_resource(
            actor,
            spell.level,
            spell_id=spell.id,
            cast_level=selected_level,
        )
        actor_after = resource.actor_after
        updated_actors = tuple(
            actor_after if candidate.id == actor.id else candidate
            for candidate in actors
        )
        cast_flag = f"cast_{spell.id}"
        flag_value: bool | str = target_id or True
        updated_state = replace(
            state,
            flags=set_scene_flag(state.flags, cast_flag, flag_value),
        )
        healing_results: tuple[AppliedHealingResult, ...] = ()
        elapsed_minutes = 0
        expired_effects: tuple[TimedMagicEffect, ...] = ()
        triggered_clock_events: tuple[object, ...] = ()
        if spell.id == "prayer_of_healing":
            (
                updated_actors,
                healing_results,
            ) = _resolve_prayer_of_healing(
                updated_actors,
                caster_id=str(actor.id),
                cast_level=selected_level,
                requested_target_ids=target_ids,
                healing_roll=healing_roll,
            )
            time_advance = advance_exploration_time(updated_state, 10)
            updated_state = time_advance.state
            elapsed_minutes = time_advance.elapsed_minutes
            expired_effects = time_advance.expired_effects
            triggered_clock_events = time_advance.triggered_clock_events
        duration_minutes = spell_duration_minutes(spell.duration)
        timed_effect = None
        if duration_minutes != 0:
            timed_effect = TimedMagicEffect(
                id=f"spell:{actor.id}:{spell.id}:{target_id or 'scene'}",
                actor_id=str(actor.id),
                spell_id=spell.id,
                label=spell.name,
                flag_key=cast_flag,
                flag_value=flag_value,
                started_at_minute=state.elapsed_minutes,
                expires_at_minute=(
                    None
                    if duration_minutes is None
                    else state.elapsed_minutes + duration_minutes
                ),
            )
            updated_state = apply_timed_magic_effect(
                updated_state,
                timed_effect,
            )
        return ExplorationSpellCastResult(
            actors=updated_actors,
            state=updated_state,
            actor_before=actor,
            actor_after=next(
                candidate
                for candidate in updated_actors
                if candidate.id == actor.id
            ),
            spell_id=spell.id,
            spell_name=spell.name,
            cast_level=selected_level,
            cast_flag=cast_flag,
            target_id=target_id,
            timed_effect=timed_effect,
            healing_results=healing_results,
            elapsed_minutes=elapsed_minutes,
            expired_effects=expired_effects,
            triggered_clock_events=triggered_clock_events,
        )


def _resolve_prayer_of_healing(
    actors: tuple[Actor, ...],
    *,
    caster_id: str,
    cast_level: int,
    requested_target_ids: tuple[str, ...],
    healing_roll: int | None,
) -> tuple[tuple[Actor, ...], tuple[AppliedHealingResult, ...]]:
    caster = next(actor for actor in actors if str(actor.id) == caster_id)
    dice_count = 2 + max(0, cast_level - 2)
    if healing_roll is None:
        raise ValueError(f"Rzuć {dice_count}k8 leczenia i wpisz sumę kości.")
    if not dice_count <= healing_roll <= dice_count * 8:
        raise ValueError(
            f"Wynik {dice_count}k8 musi mieścić się od {dice_count} do {dice_count * 8}."
        )
    eligible = tuple(
        actor
        for actor in actors
        if actor.faction == caster.faction
        and actor.creature_type not in {"construct", "undead"}
        and grid_distance_feet(caster.position, actor.position) <= 30
    )
    if requested_target_ids:
        if len(requested_target_ids) > 6:
            raise ValueError("Modlitwa leczenia może objąć najwyżej 6 istot.")
        if len(requested_target_ids) != len(set(requested_target_ids)):
            raise ValueError("Cele Modlitwy leczenia nie mogą się powtarzać.")
        eligible_by_id = {str(actor.id): actor for actor in eligible}
        unknown = tuple(
            target_id
            for target_id in requested_target_ids
            if target_id not in eligible_by_id
        )
        if unknown:
            raise ValueError(
                "Nielegalne cele Modlitwy leczenia: " + ", ".join(unknown) + "."
            )
        targets = tuple(eligible_by_id[target_id] for target_id in requested_target_ids)
    else:
        targets = eligible[:6]
    casting_ability = spellcasting_ability_for_spell(caster, "prayer_of_healing")
    modifier = (
        ability_modifier(getattr(caster.ability_scores, casting_ability))
        if casting_ability is not None
        else 0
    )
    source = HealingSource(
        id="prayer_of_healing",
        name="Modlitwa leczenia",
        source_type=HealingSourceType.SPELL,
        range_feet=30,
        healing_hint=f"{dice_count}k8 {modifier:+d}",
        healing_die_sides=8,
        healing_dice_count=dice_count,
        healing_modifier=modifier,
        spell_level=2,
        casting_kind=SpellCastingKind.LEVELED,
        cast_level=cast_level,
        upcast_healing_dice_per_level=1,
        excluded_creature_types=("construct", "undead"),
    )
    amount = healing_roll + modifier
    updated = actors
    results: list[AppliedHealingResult] = []
    for selected in targets:
        current = next(actor for actor in updated if actor.id == selected.id)
        result = apply_healing_result(current, source, amount)
        updated = tuple(
            result.actor_after if actor.id == current.id else actor
            for actor in updated
        )
        results.append(result)
    return updated, tuple(results)


__all__ = [
    "ExplorationSpellCastResult",
    "ExplorationSpellCastingFlowService",
]
