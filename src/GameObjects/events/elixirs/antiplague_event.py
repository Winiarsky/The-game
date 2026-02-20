from __future__ import annotations

from bonuses import BonusType
from skills import Skill

from .base_elixir_event import BaseElixirEvent, _hours, make_bonus_status, skill_bonus_effect, skill_check_effect
from ..registry import register_event


@register_event
class AntiplagueEvent(BaseElixirEvent):
    name = "antiplague"
    prompt_description = (
        "Antiplague: bonus do Fortitude vs disease na 24 godziny.\n"
        "Major: dodatkowo natychmiastowy save vs disease (opisowo)."
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
            status_id="antiplague",
            label="Antiplague",
            duration=_hours(24),
            data={"effect_tags": ["disease", "elixir"]},
            effects=[
                skill_check_effect(
                    applies_to="source",
                    skills=[Skill.FORTITUDE.value],
                    tags_required=["disease"],
                    bonus_effects=[effect],
                    prompt_notes=[f"Antiplague: +{bonus} item vs disease."],
                )
            ],
        )
        remover = getattr(target, "remove_status", None)
        if callable(remover):
            remover("antiplague")
        adder = getattr(target, "add_status", None)
        if callable(adder):
            adder(status)

        if tier_data.get("extra_save"):
            try:
                ctx.game.ui_log("Antiplague (major): natychmiastowy save vs disease (opisowo).")
            except Exception:
                pass
