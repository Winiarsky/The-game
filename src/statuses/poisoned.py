from __future__ import annotations

from typing import Optional

from damage_types import DamageType
from skills import Skill
from statuses.base import Status
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources


def PoisonedStatus(*, duration: int, damage: int, dc: int, source: str | None = None) -> Status:
    """Status: Poisoned (czasowy, z testem Fortitude co turę)."""
    return Status(
        id="poisoned",
        label="Poisoned",
        duration=int(duration),
        source=source,
        data={
            "dc": int(dc),
            "damage": int(damage),
            "damage_type": DamageType.POISON.value,
        },
    )


def _poison_damage_for_outcome(base_damage: int, outcome: str) -> int:
    if outcome == "critical_success":
        return 0
    if outcome == "success":
        return max(0, int(base_damage) // 2)
    if outcome == "critical_failure":
        return max(0, int(base_damage) * 2)
    return max(0, int(base_damage))


def process_poisoned(actor, game) -> None:
    """Obsłuż start tury: rzut obronny vs poison i obrażenia."""
    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list) or not statuses:
        return
    for status in list(statuses):
        if getattr(status, "id", None) != "poisoned":
            continue
        data = getattr(status, "data", None) or {}
        try:
            dc = int(data.get("dc"))
            damage = int(data.get("damage"))
        except Exception:
            continue
        damage_type = data.get("damage_type", DamageType.POISON.value)

        result = resolve_skill_check_with_sources(
            skill_id=Skill.FORTITUDE.value,
            dc=dc,
            actor=actor,
            target=None,
            tags=["poison", Skill.FORTITUDE.value],
            game=game,
            apply_modifiers=True,
        )

        dealt = _poison_damage_for_outcome(damage, result.outcome)
        if dealt:
            apply = getattr(actor, "apply_damage", None)
            if callable(apply):
                apply(dealt, damage_type)
        try:
            if hasattr(game, "ui_log"):
                game.ui_log(
                    f"Poisoned: {result.outcome} – obrażenia {dealt} ({damage_type})."
                )
            if hasattr(game, "ui_event"):
                game.ui_event(
                    "info",
                    {"text": f"Poisoned: otrzymujesz {dealt} obrażeń ({damage_type})."},
                )
        except Exception:
            pass


__all__ = ["PoisonedStatus", "process_poisoned"]
