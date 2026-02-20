from __future__ import annotations

from bonuses import BonusType
from skills import Skill
from .base_elixir_event import BaseElixirEvent, _hours, make_bonus_status, skill_bonus_effect, skill_check_effect
from ..registry import register_event


@register_event
class AntidoteEvent(BaseElixirEvent):
    name = "antidote"
    prompt_description = (
        "Antidote: bonus do Fortitude vs poison na 6 godzin.\n"
        "Major: dodatkowo natychmiastowy save vs poison (opisowo)."
    )
    tiers = {
        "lesser": {"item_bonus": 2},
        "moderate": {"item_bonus": 3},
        "greater": {"item_bonus": 4},
        "major": {"item_bonus": 4, "extra_save": True},
    }

    def _apply_elixir(self, ctx, target, tier: str, tier_data: dict[str, object]) -> None:
        bonus = int(tier_data.get("item_bonus", 0) or 0)
        if bonus <= 0:
            return
        effect = skill_bonus_effect(
            skill_id=Skill.FORTITUDE.value,
            bonus=bonus,
            bonus_type=BonusType.ITEM,
            source=f"{self.name}:{tier}",
            label=f"{self.name} {tier}",
        )
        status = make_bonus_status(
            status_id="antidote",
            label="Antidote",
            duration=_hours(6),
            data={"effect_tags": ["poison", "elixir"]},
            effects=[
                skill_check_effect(
                    applies_to="source",
                    skills=[Skill.FORTITUDE.value],
                    tags_required=["poison"],
                    bonus_effects=[effect],
                    prompt_notes=[f"Antidote: +{bonus} item vs poison."],
                )
            ],
        )
        remover = getattr(target, "remove_status", None)
        if callable(remover):
            remover("antidote")
        adder = getattr(target, "add_status", None)
        if callable(adder):
            adder(status)

        if tier_data.get("extra_save"):
            try:
                ctx.game.ui_log("Antidote (major): natychmiastowy save vs poison (opisowo).")
            except Exception:
                pass
