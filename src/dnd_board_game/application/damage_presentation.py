from __future__ import annotations

from dnd_board_game.combat import AppliedDamageResult, DamageAdjustment, DamageResult


_ADJUSTMENT_LABELS_PL: dict[DamageAdjustment, str] = {
    DamageAdjustment.NORMAL: "bez modyfikacji",
    DamageAdjustment.RESISTANCE: "odporność",
    DamageAdjustment.IMMUNITY: "niewrażliwość",
    DamageAdjustment.VULNERABILITY: "podatność",
    DamageAdjustment.RESISTANCE_AND_VULNERABILITY: "odporność i podatność",
}


def damage_result_text(result: DamageResult) -> str:
    parts: list[str] = []
    for component in result.resolved_components:
        label = component.damage_type.value
        if component.adjustment == DamageAdjustment.NORMAL:
            parts.append(f"{component.amount_applied} {label}")
        else:
            parts.append(
                f"{component.amount_before} {label} -> {component.amount_applied} "
                f"({_ADJUSTMENT_LABELS_PL[component.adjustment]})"
            )
    return ", ".join(parts) if parts else "0"


def applied_damage_message(result: AppliedDamageResult) -> str:
    if result.instant_death:
        defeated_text = " Obrażenia powodują natychmiastową śmierć."
    elif result.death_save_failures_added:
        defeated_text = f" Porażki death saves: +{result.death_save_failures_added}."
    elif result.defeated_by_damage and result.actor_after.needs_death_save():
        defeated_text = " Cel traci przytomność i zaczyna wykonywać death saves."
    else:
        defeated_text = " Cel zostaje pokonany." if result.defeated_by_damage else ""
    temp_text = ""
    if result.temp_hp_before > 0 or result.absorbed_by_temp_hp > 0:
        temp_text = (
            f" Temp HP {result.temp_hp_before} -> {result.temp_hp_after}, "
            f"pochłonięto {result.absorbed_by_temp_hp}."
        )
    breakdown = damage_result_text(result.damage)
    return (
        f"Obrażenia: {breakdown}; razem {result.damage.total_applied}. "
        f"{result.actor_before.name}: HP {result.hp_before} -> {result.hp_after} / "
        f"{result.actor_after.max_hp}.{temp_text}{defeated_text}"
    )


def applied_damage_payload(result: AppliedDamageResult | None) -> dict[str, object] | None:
    if result is None:
        return None
    return {
        "damage": result.damage.total_applied,
        "damage_before_affinities": result.damage.total_before_reduction,
        "damage_breakdown": result.damage.as_payload(),
        "hp_before": result.hp_before,
        "hp_after": result.hp_after,
        "temp_hp_before": result.temp_hp_before,
        "temp_hp_after": result.temp_hp_after,
        "absorbed_by_temp_hp": result.absorbed_by_temp_hp,
        "applied_to_hp": result.applied_to_hp,
        "defeated": result.defeated,
        "defeated_by_damage": result.defeated_by_damage,
        "death_save_failures_added": result.death_save_failures_added,
        "instant_death": result.instant_death,
    }


__all__ = ["applied_damage_message", "applied_damage_payload", "damage_result_text"]
