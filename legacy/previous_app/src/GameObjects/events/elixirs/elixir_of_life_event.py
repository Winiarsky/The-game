from __future__ import annotations

from bonuses import BonusType
from skills import Skill

from .base_elixir_event import BaseElixirEvent, _minutes, make_bonus_status, skill_bonus_effect, skill_check_effect
from ..registry import register_event


@register_event
class ElixirOfLifeEvent(BaseElixirEvent):
    name = "elixir_of_life"
    prompt_description = "Eliksir leczy oraz daje bonus do saves vs disease/poison na 10 minut."
    tier_choices = ("minor", "lesser", "moderate", "greater", "major", "true")
    tiers = {
        "minor": {"heal_dice": "1d6", "save_bonus": 1},
        "lesser": {"heal_dice": "3d6+6", "save_bonus": 1},
        "moderate": {"heal_dice": "5d6+12", "save_bonus": 2},
        "greater": {"heal_dice": "7d6+18", "save_bonus": 2},
        "major": {"heal_dice": "8d6+21", "save_bonus": 3},
        "true": {"heal_dice": "10d6+27", "save_bonus": 4},
    }

    def _apply_elixir(self, ctx, target, tier: str, tier_data: dict[str, object]) -> None:
        dice = str(tier_data.get("heal_dice", "") or "")
        if dice:
            amount = self._heal_amount(ctx, target, dice)
            self._apply_heal_or_harm(target, amount)

        bonus = int(tier_data.get("save_bonus", 0) or 0)
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
            status_id="elixir_of_life",
            label="Elixir of Life",
            duration=_minutes(10),
            data={"effect_tags": ["poison", "disease", "elixir"]},
            effects=[
                skill_check_effect(
                    applies_to="source",
                    skills=[Skill.FORTITUDE.value],
                    tags_required=["poison"],
                    bonus_effects=[effect],
                ),
                skill_check_effect(
                    applies_to="source",
                    skills=[Skill.FORTITUDE.value],
                    tags_required=["disease"],
                    bonus_effects=[effect],
                ),
            ],
        )
        remover = getattr(target, "remove_status", None)
        if callable(remover):
            remover("elixir_of_life")
        adder = getattr(target, "add_status", None)
        if callable(adder):
            adder(status)
