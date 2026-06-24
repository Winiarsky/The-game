from __future__ import annotations

from bonuses import BonusType
from skills import Skill

from .base_elixir_event import BaseElixirEvent, _hours, make_bonus_status, skill_bonus_effect, skill_check_effect
from ..registry import register_event


@register_event
class EagleEyeElixirEvent(BaseElixirEvent):
    name = "eagle_eye_elixir"
    prompt_description = "Bonus do Perception, większy przy szukaniu secret doors/traps."
    tiers = {
        "lesser": {"base_bonus": 1, "secret_bonus": 2},
        "moderate": {"base_bonus": 2, "secret_bonus": 3},
        "greater": {"base_bonus": 3, "secret_bonus": 4},
        "major": {"base_bonus": 3, "secret_bonus": 4, "auto_check": True},
    }

    def _apply_elixir(self, ctx, target, tier: str, tier_data: dict[str, object]) -> None:
        base_bonus = int(tier_data.get("base_bonus", 0) or 0)
        secret_bonus = int(tier_data.get("secret_bonus", 0) or 0)
        effects = []
        if base_bonus:
            effects.append(
                skill_check_effect(
                    applies_to="source",
                    skills=[Skill.PERCEPTION.value],
                    tags_required=[Skill.PERCEPTION.value],
                    bonus_effects=[
                        skill_bonus_effect(
                            skill_id=Skill.PERCEPTION.value,
                            bonus=base_bonus,
                            bonus_type=BonusType.ITEM,
                            source=f"{self.name}:{tier}",
                            label=f"{self.name} {tier}",
                        )
                    ],
                )
            )
        if secret_bonus:
            for tag in ("secret", "trap"):
                effects.append(
                    skill_check_effect(
                        applies_to="source",
                        skills=[Skill.PERCEPTION.value],
                        tags_required=[Skill.PERCEPTION.value, tag],
                        bonus_effects=[
                            skill_bonus_effect(
                                skill_id=Skill.PERCEPTION.value,
                                bonus=secret_bonus,
                                bonus_type=BonusType.ITEM,
                                source=f"{self.name}:{tier}:{tag}",
                                label=f"{self.name} {tier} ({tag})",
                            )
                        ],
                    )
                )
        status = make_bonus_status(
            status_id="eagle_eye",
            label="Eagle-Eye",
            duration=_hours(1),
            data={"effect_tags": ["perception", "elixir"]},
            effects=effects,
        )
        remover = getattr(target, "remove_status", None)
        if callable(remover):
            remover("eagle_eye")
        adder = getattr(target, "add_status", None)
        if callable(adder):
            adder(status)

        if tier_data.get("auto_check"):
            try:
                ctx.game.ui_log("Eagle-Eye (major): auto-check w 10 ft od secret/trap (opisowo).")
            except Exception:
                pass
