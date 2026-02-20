from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill

from .base_elixir_event import BaseElixirEvent, _minutes, _hours, make_bonus_status, skill_bonus_effect, skill_check_effect
from ..registry import register_event


@register_event
class CognitiveMutagenEvent(BaseElixirEvent):
    name = "cognitive_mutagen"
    default_tags = ["elixir", "alchemical", "mutagen", "polymorph"]
    prompt_description = "Bonus do INT skilli + Recall Knowledge, kara do ataków/ATH/ACRO (opisowo: bulk)."
    tiers = {
        "lesser": {"bonus": 1, "duration": _minutes(1)},
        "moderate": {"bonus": 2, "duration": _minutes(10)},
        "greater": {"bonus": 3, "duration": _hours(1), "trained_skill": True},
        "major": {"bonus": 4, "duration": _hours(1), "trained_skill": True},
    }

    def _apply_elixir(self, ctx, target, tier: str, tier_data: dict[str, object]) -> None:
        bonus = int(tier_data.get("bonus", 0) or 0)
        duration = int(tier_data.get("duration", 0) or 0)
        skills = [
            Skill.ARCANA.value,
            Skill.CRAFTING.value,
            Skill.LORE.value,
            Skill.OCCULTISM.value,
            Skill.SOCIETY.value,
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
                        promote=1,
                        promote_on=["critical_failure"],
                    )
                )
        remover_status = getattr(target, "remove_status", None)
        if callable(remover_status):
            remover_status("cognitive_mutagen")
            remover_status("cognitive_mutagen_penalty")

        status = make_bonus_status(
            status_id="cognitive_mutagen",
            label="Cognitive Mutagen",
            duration=duration,
            data={"effect_tags": ["mutagen", "polymorph"]},
            effects=effects,
        )
        adder = getattr(target, "add_status", None)
        if callable(adder):
            adder(status)

        # penalties: attacks, athletics, acrobatics
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
                        value=2,
                        tag=tag,
                        source=f"{self.name}:{tier}:attack",
                        label=f"{self.name} {tier} (penalty)",
                        is_penalty=True,
                        duration_turns=duration,
                    )
                )

        if bonus:
            penalty_effects = []
            for skill_id in (Skill.ATHLETICS.value, Skill.ACROBATICS.value):
                penalty_effects.append(
                    skill_check_effect(
                        applies_to="source",
                        skills=[skill_id],
                        tags_required=[skill_id],
                        bonus_effects=[
                            skill_bonus_effect(
                                skill_id=skill_id,
                                bonus=2,
                                bonus_type=BonusType.ITEM,
                                source=f"{self.name}:{tier}:penalty",
                                label=f"{self.name} {tier} (penalty)",
                                is_penalty=True,
                            )
                        ],
                    )
                )
            penalty_status = make_bonus_status(
                status_id="cognitive_mutagen_penalty",
                label="Cognitive Mutagen (penalty)",
                duration=duration,
                data={"effect_tags": ["mutagen", "polymorph"]},
                effects=penalty_effects,
            )
            if callable(adder):
                adder(penalty_status)

        if tier_data.get("trained_skill"):
            try:
                ctx.game.ui_log("Cognitive Mutagen: trained skill (opisowo).")
            except Exception:
                pass
