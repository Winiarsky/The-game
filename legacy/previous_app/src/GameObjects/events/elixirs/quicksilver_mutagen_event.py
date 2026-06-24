from __future__ import annotations

from bonuses import BonusEffect, BonusType
from damage_types import DamageType
from skills import Skill

from .base_elixir_event import BaseElixirEvent, _minutes, _hours, make_bonus_status, skill_bonus_effect, skill_check_effect
from ..registry import register_event
from statuses import SpeedBonusStatus


@register_event
class QuicksilverMutagenEvent(BaseElixirEvent):
    name = "quicksilver_mutagen"
    default_tags = ["elixir", "alchemical", "mutagen", "polymorph"]
    prompt_description = "Bonus do DEX skilli/Reflex/ataków + Speed, kara do Fortitude i self-damage."
    tiers = {
        "lesser": {"bonus": 1, "speed_bonus": 5, "duration": _minutes(1)},
        "moderate": {"bonus": 2, "speed_bonus": 10, "duration": _minutes(10)},
        "greater": {"bonus": 3, "speed_bonus": 15, "duration": _hours(1)},
        "major": {"bonus": 4, "speed_bonus": 15, "duration": _hours(1)},
    }

    def _apply_elixir(self, ctx, target, tier: str, tier_data: dict[str, object]) -> None:
        bonus = int(tier_data.get("bonus", 0) or 0)
        duration = int(tier_data.get("duration", 0) or 0)
        effects = []
        if bonus:
            for skill_id in (Skill.ACROBATICS.value, Skill.STEALTH.value, Skill.THIEVERY.value, Skill.REFLEX.value):
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
            remover_status("quicksilver_mutagen")
            remover_status("quicksilver_mutagen_penalty")

        status = make_bonus_status(
            status_id="quicksilver_mutagen",
            label="Quicksilver Mutagen",
            duration=duration,
            data={"effect_tags": ["mutagen", "polymorph"]},
            effects=effects,
        )
        adder = getattr(target, "add_status", None)
        if callable(adder):
            adder(status)

        # attack bonus (uproszczenie: wszystkie ataki)
        remover = getattr(target, "remove_bonuses_with_prefix", None)
        if callable(remover):
            try:
                remover(f"{self.name}:")
            except Exception:
                pass
        adder_bonus = getattr(target, "add_bonus", None)
        if callable(adder_bonus) and bonus:
            for tag in ("attack_melee", "attack_ranged"):
                adder_bonus(
                    BonusEffect(
                        type=BonusType.ITEM,
                        value=bonus,
                        tag=tag,
                        source=f"{self.name}:{tier}:attack",
                        label=f"{self.name} {tier}",
                        duration_turns=duration,
                    )
                )

        # speed bonus
        speed_bonus = int(tier_data.get("speed_bonus", 0) or 0)
        if speed_bonus and callable(adder):
            if callable(remover_status):
                remover_status("speed_bonus")
            adder(
                SpeedBonusStatus(
                    bonus_feet=speed_bonus,
                    duration=duration,
                    source=self.name,
                    label=f"speed +{speed_bonus}ft",
                )
            )

        # Fortitude penalty
        penalty_status = make_bonus_status(
            status_id="quicksilver_mutagen_penalty",
            label="Quicksilver Mutagen (penalty)",
            duration=duration,
            data={"effect_tags": ["mutagen", "polymorph"]},
            effects=[
                skill_check_effect(
                    applies_to="source",
                    skills=[Skill.FORTITUDE.value],
                    tags_required=[Skill.FORTITUDE.value],
                    bonus_effects=[
                        skill_bonus_effect(
                            skill_id=Skill.FORTITUDE.value,
                            bonus=2,
                            bonus_type=BonusType.ITEM,
                            source=f"{self.name}:{tier}:penalty",
                            label=f"{self.name} {tier} (penalty)",
                            is_penalty=True,
                        )
                    ],
                )
            ],
        )
        if callable(adder):
            adder(penalty_status)

        # self-damage: 2 * level
        try:
            level = int(getattr(target, "level", 1) or 1)
        except Exception:
            level = 1
        damage = max(0, 2 * level)
        if damage > 0:
            if target in getattr(ctx.game, "heroes", []):
                amount = self._prompt_value("Quicksilver Mutagen", dice=str(damage), source=self.name)
                apply = getattr(target, "apply_damage", None)
                if callable(apply):
                    apply(amount, DamageType.NORMAL.value)
            else:
                apply = getattr(target, "apply_damage", None)
                if callable(apply):
                    apply(damage, DamageType.NORMAL.value)
            try:
                ctx.game.ui_log("Quicksilver Mutagen: HP utracone nie mogą być odzyskane (opisowo).")
            except Exception:
                pass
