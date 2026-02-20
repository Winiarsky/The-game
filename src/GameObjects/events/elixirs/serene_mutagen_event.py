from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill

from .base_elixir_event import BaseElixirEvent, _minutes, _hours, make_bonus_status, skill_bonus_effect, skill_check_effect
from ..registry import register_event


@register_event
class SereneMutagenEvent(BaseElixirEvent):
    name = "serene_mutagen"
    default_tags = ["elixir", "alchemical", "mutagen", "polymorph"]
    prompt_description = "Bonus do Will/Perception/Med/Nature/Religion/Survival, kary do ataków (opisowo: mental)."
    tiers = {
        "lesser": {"bonus": 1, "duration": _minutes(1)},
        "moderate": {"bonus": 2, "duration": _minutes(10)},
        "greater": {"bonus": 3, "duration": _hours(1), "will_crit": True},
        "major": {"bonus": 4, "duration": _hours(1), "will_crit": True},
    }

    def _apply_elixir(self, ctx, target, tier: str, tier_data: dict[str, object]) -> None:
        bonus = int(tier_data.get("bonus", 0) or 0)
        duration = int(tier_data.get("duration", 0) or 0)
        skills = [
            Skill.WILL.value,
            Skill.PERCEPTION.value,
            Skill.MEDICINE.value,
            Skill.NATURE.value,
            Skill.RELIGION.value,
            Skill.SURVIVAL.value,
        ]
        effects = []
        if bonus:
            for skill_id in skills:
                effects.append(
                    skill_check_effect(
                        applies_to="source",
                        skills=[skill_id],
                        tags_required=[skill_id],
                        bonus_effects=[
                            skill_bonus_effect(
                                skill_id=skill_id,
                                bonus=bonus,
                                bonus_type=BonusType.ITEM,
                                source=f"{self.name}:{tier}",
                                label=f"{self.name} {tier}",
                            )
                        ],
                    )
                )
        remover_status = getattr(target, "remove_status", None)
        if callable(remover_status):
            remover_status("serene_mutagen")

        status = make_bonus_status(
            status_id="serene_mutagen",
            label="Serene Mutagen",
            duration=duration,
            data={"effect_tags": ["mutagen", "polymorph"]},
            effects=effects,
        )
        adder = getattr(target, "add_status", None)
        if callable(adder):
            adder(status)

        # attack penalty
        remover = getattr(target, "remove_bonuses_with_prefix", None)
        if callable(remover):
            try:
                remover(f"{self.name}:")
            except Exception:
                pass
        adder_bonus = getattr(target, "add_bonus", None)
        if callable(adder_bonus):
            for tag in ("attack_melee", "attack_ranged"):
                adder_bonus(
                    BonusEffect(
                        type=BonusType.ITEM,
                        value=1,
                        tag=tag,
                        source=f"{self.name}:{tier}:attack",
                        label=f"{self.name} {tier} (penalty)",
                        is_penalty=True,
                        duration_turns=duration,
                    )
                )

        if tier_data.get("will_crit"):
            try:
                ctx.game.ui_log("Serene Mutagen: sukces vs mental -> krytyczny sukces (opisowo).")
            except Exception:
                pass
        try:
            ctx.game.ui_log("Serene Mutagen: -1 per damage die i kary do spell DC (opisowo).")
        except Exception:
            pass
