"""Actor feature hooks for attack rolls, ability checks, and saving throws."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from .dice import (
    D20RollKind,
    D20RollContextTag,
    D20RollRequest,
    RollMode,
    RollModifier,
    RollModifierType,
)
from .saving_throws import SavingThrowEffectTag


def apply_actor_d20_traits(
    actor: object,
    request: D20RollRequest,
    roll_kind: D20RollKind,
    *,
    effect_tags: Iterable[str] = (),
    active_effects: Iterable[object] = (),
    condition_states: Iterable[object] = (),
) -> D20RollRequest:
    """Apply executable species rerolls and save advantages to one request."""
    tags = frozenset(str(tag) for tag in effect_tags)
    effects = tuple(active_effects)
    conditions = frozenset(
        str(getattr(getattr(state, "condition", ""), "value", getattr(state, "condition", "")))
        for state in condition_states
        if getattr(state, "actor_id", "") == str(getattr(actor, "id", ""))
    )
    feature_ids = frozenset(
        getattr(grant, "feature_id", "")
        for grant in getattr(actor, "features", ())
    )
    wearing_heavy_armor = any(
        getattr(item, "equipped", False)
        and getattr(getattr(item, "armor_category", None), "value", "") == "heavy"
        for item in getattr(actor, "inventory", ())
    )
    raging = (
        not wearing_heavy_armor
        and any(
            getattr(effect, "actor_id", "") == str(getattr(actor, "id", ""))
            and getattr(effect, "kind", "") == "rage"
            for effect in effects
        )
    )
    modifiers = list(request.modifiers)
    advantage_labels: list[tuple[str, str]] = []
    if (
        raging
        and request.ability == "strength"
        and roll_kind in {D20RollKind.ABILITY_CHECK, D20RollKind.SAVING_THROW}
    ):
        advantage_labels.append(("Szał", "rage"))
    if roll_kind == D20RollKind.SAVING_THROW:
        if (
            SavingThrowEffectTag.POISON.value in tags
            and "dwarven_resilience" in feature_ids
        ):
            advantage_labels.append(("Dwarven Resilience", "dwarven_resilience"))
        if SavingThrowEffectTag.FEAR.value in tags and "brave" in feature_ids:
            advantage_labels.append(("Brave", "brave"))
        if (
            SavingThrowEffectTag.CHARM.value in tags
            and "fey_ancestry" in feature_ids
        ):
            advantage_labels.append(("Fey Ancestry", "fey_ancestry"))
        if (
            SavingThrowEffectTag.MAGIC.value in tags
            and "gnome_cunning" in feature_ids
            and request.ability in {"intelligence", "wisdom", "charisma"}
        ):
            advantage_labels.append(("Gnome Cunning", "gnome_cunning"))
        if (
            SavingThrowEffectTag.VISIBLE_DANGER.value in tags
            and "danger_sense" in feature_ids
            and request.ability == "dexterity"
            and not {"blinded", "deafened", "incapacitated"}.intersection(conditions)
        ):
            advantage_labels.append(("Danger Sense", "danger_sense"))
    if (
        roll_kind == D20RollKind.ABILITY_CHECK
        and D20RollContextTag.STONEWORK.value in tags
        and "stonecunning" in feature_ids
    ):
        proficiency_bonus = int(getattr(actor, "proficiency_bonus", 0))
        modifiers.append(
            RollModifier(
                "Stonecunning: podwójna biegłość",
                proficiency_bonus * 2,
                RollModifierType.FEATURE,
                stacking_key="proficiency",
            )
        )
    if (
        roll_kind == D20RollKind.ABILITY_CHECK
        and "jack_of_all_trades" in feature_ids
        and not any(modifier.stacking_key == "proficiency" for modifier in modifiers)
    ):
        modifiers.append(
            RollModifier(
                "Jack of All Trades: połowa biegłości",
                int(getattr(actor, "proficiency_bonus", 0)) // 2,
                RollModifierType.FEATURE,
                stacking_key="proficiency",
            )
        )
    if (
        roll_kind == D20RollKind.ABILITY_CHECK
        and D20RollContextTag.ARTIFICERS_LORE.value in tags
        and "artificers_lore" in feature_ids
    ):
        proficiency_bonus = int(getattr(actor, "proficiency_bonus", 0))
        modifiers.append(
            RollModifier(
                "Artificer's Lore: podwójna biegłość",
                proficiency_bonus * 2,
                RollModifierType.FEATURE,
                stacking_key="proficiency",
            )
        )
    mode = request.mode
    if advantage_labels:
        mode = (
            RollMode.NORMAL
            if request.mode == RollMode.DISADVANTAGE
            else RollMode.ADVANTAGE
        )
        modifiers.extend(
            RollModifier(
                f"{label}: przewaga",
                0,
                RollModifierType.FEATURE,
                stacking_key=f"feature:{feature_id}:advantage",
            )
            for label, feature_id in advantage_labels
        )
    lucky = "lucky" in feature_ids
    return replace(
        request,
        mode=mode,
        modifiers=tuple(modifiers),
        reroll_natural_ones=request.reroll_natural_ones or lucky,
        reroll_label=request.reroll_label or ("Lucky" if lucky else ""),
    )


def actor_is_immune_to_effect(actor: object, effect_tag: str) -> bool:
    """Return feature-derived immunity for effects that are not conditions."""
    feature_ids = {
        getattr(grant, "feature_id", "")
        for grant in getattr(actor, "features", ())
    }
    return (
        (
            effect_tag == SavingThrowEffectTag.MAGICAL_SLEEP.value
            and "fey_ancestry" in feature_ids
        )
        or (
            effect_tag == SavingThrowEffectTag.DISEASE.value
            and "divine_health" in feature_ids
        )
    )


__all__ = [
    "actor_is_immune_to_effect",
    "apply_actor_d20_traits",
]
