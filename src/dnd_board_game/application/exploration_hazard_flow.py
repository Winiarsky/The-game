from __future__ import annotations

from dataclasses import dataclass
from random import Random

from dnd_board_game.actors import Actor
from dnd_board_game.combat import (
    AppliedDamageResult,
    DamageComponentInput,
    DamageType,
    apply_damage_result,
    apply_save_damage_amount,
    resolve_actor_saving_throw,
    resolve_damage,
    CombatCondition,
)
from dnd_board_game.exploration import (
    ExplorationEffectResult,
    ExplorationHazard,
    ExplorationState,
    add_exploration_condition,
    apply_exploration_effect,
)
from dnd_board_game.rules import EffectDuration, SavingThrowResult

from .damage_presentation import applied_damage_message


@dataclass(frozen=True, slots=True)
class ExplorationHazardResolution:
    actor_before: Actor
    actor_after: Actor
    hazard: ExplorationHazard
    saving_throw: SavingThrowResult
    base_damage: int
    applied_damage: AppliedDamageResult
    outcome_effects: tuple[dict[str, object], ...]
    message: str


def resolve_exploration_hazard(
    actor: Actor,
    hazard: ExplorationHazard,
    *,
    natural_roll: int,
    natural_roll_2: int | None = None,
    natural_rerolls: tuple[int, ...] = (),
    rng: Random,
) -> ExplorationHazardResolution:
    saving_throw = resolve_actor_saving_throw(
        actor,
        hazard.saving_throw,
        natural_roll=natural_roll,
        natural_roll_2=natural_roll_2,
        natural_rerolls=natural_rerolls,
    )
    base_damage = _roll_hazard_damage(hazard, rng)
    adjusted_damage = apply_save_damage_amount(base_damage, saving_throw)
    damage = resolve_damage(
        (
            DamageComponentInput(
                adjusted_damage,
                DamageType(hazard.damage.damage_type),
                hazard.label,
            ),
        )
    )
    applied = apply_damage_result(actor, damage)
    outcome_message = hazard.success_message if saving_throw.success else hazard.failure_message
    outcome = "sukces" if saving_throw.success else "porażka"
    message = (
        f"{actor.name}: {hazard.saving_throw.ability} save d20 "
        f"{saving_throw.natural_roll}, modyfikator {saving_throw.modifier:+d}, "
        f"razem {saving_throw.total} przeciw ST {saving_throw.dc}: {outcome}. "
        f"{outcome_message} {applied_damage_message(applied)}"
    ).strip()
    return ExplorationHazardResolution(
        actor_before=actor,
        actor_after=applied.actor_after,
        hazard=hazard,
        saving_throw=saving_throw,
        base_damage=base_damage,
        applied_damage=applied,
        outcome_effects=(hazard.success_effects if saving_throw.success else hazard.failure_effects),
        message=message,
    )


def apply_exploration_hazard_outcome(
    state: ExplorationState,
    effects: tuple[dict[str, object], ...],
    *,
    actor_id: str,
    challenge_id: str,
) -> tuple[ExplorationState, tuple[ExplorationEffectResult, ...]]:
    """Apply authored hazard consequences after the physical saving throw."""

    current = state
    results: list[ExplorationEffectResult] = []
    for raw_effect in effects:
        effect_type = str(raw_effect.get("type", "")).strip().lower()
        raw_parameters = raw_effect.get("parameters", {})
        if not isinstance(raw_parameters, dict):
            raise ValueError(f"{effect_type}.parameters must be an object.")
        parameters = dict(raw_parameters)
        if effect_type == "apply_condition":
            condition = CombatCondition(str(parameters.get("condition", "")))
            updated = add_exploration_condition(
                current,
                actor_id,
                condition,
                source_label=str(
                    parameters.get("source_label", f"Zagrożenie: {challenge_id}")
                ),
                duration=EffectDuration(
                    str(parameters.get("duration", EffectDuration.PERMANENT.value))
                ),
            )
            changed = updated != current
            current = updated
            results.append(
                ExplorationEffectResult(
                    current,
                    effect_type,
                    changed,
                    f"{_condition_label(condition)}: stan nałożony na aktora {actor_id}.",
                )
            )
            continue
        if effect_type in {"add_noise", "add_complication"}:
            parameters.setdefault("challenge_id", challenge_id)
        normalized = {"type": effect_type, "parameters": parameters}
        result = apply_exploration_effect(current, normalized)
        current = result.state
        results.append(result)
    return current, tuple(results)


def _condition_label(condition: CombatCondition) -> str:
    return {
        CombatCondition.PRONE: "Powalony",
        CombatCondition.GRAPPLED: "Pochwycony",
        CombatCondition.POISONED: "Zatruty",
        CombatCondition.RESTRAINED: "Unieruchomiony",
    }[condition]


def _roll_hazard_damage(hazard: ExplorationHazard, rng: Random) -> int:
    damage = hazard.damage
    amount = damage.fixed if damage.fixed is not None else rng.randint(1, damage.die_sides or 6)
    return max(0, amount + damage.modifier)


__all__ = [
    "ExplorationHazardResolution",
    "apply_exploration_hazard_outcome",
    "resolve_exploration_hazard",
]
