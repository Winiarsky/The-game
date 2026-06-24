from __future__ import annotations

from statuses import SpeedBonusStatus

from .base_elixir_event import BaseElixirEvent, _minutes, _hours
from ..registry import register_event


@register_event
class CheetahsElixirEvent(BaseElixirEvent):
    name = "cheetahs_elixir"
    prompt_description = "Status bonus do Speed na określony czas."
    tiers = {
        "lesser": {"speed_bonus": 5, "duration": _minutes(1)},
        "moderate": {"speed_bonus": 10, "duration": _minutes(10)},
        "greater": {"speed_bonus": 10, "duration": _hours(1)},
    }
    tier_choices = ("lesser", "moderate", "greater")

    def _apply_elixir(self, ctx, target, tier: str, tier_data: dict[str, object]) -> None:
        bonus = int(tier_data.get("speed_bonus", 0) or 0)
        duration = tier_data.get("duration")
        try:
            duration = int(duration) if duration is not None else None
        except Exception:
            duration = None
        if bonus <= 0:
            return
        remover = getattr(target, "remove_status", None)
        if callable(remover):
            remover("speed_bonus")
        adder = getattr(target, "add_status", None)
        if callable(adder):
            adder(
                SpeedBonusStatus(
                    bonus_feet=bonus,
                    duration=duration,
                    source=self.name,
                    label=f"speed +{bonus}ft",
                )
            )
