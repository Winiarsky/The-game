from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill

from .base_elixir_event import BaseElixirEvent, _minutes, _hours, make_bonus_status, skill_bonus_effect, skill_check_effect
from ..registry import register_event


@register_event
class JuggernautMutagenEvent(BaseElixirEvent):
    name = "juggernaut_mutagen"
    default_tags = ["elixir", "alchemical", "mutagen", "polymorph"]
    prompt_description = "Bonus do Fortitude + temp HP (opisowo), kara do Will/Perception/initiative."
    tiers = {
        "lesser": {"bonus": 1, "temp_hp": 5, "duration": _minutes(1)},
        "moderate": {"bonus": 2, "temp_hp": 10, "duration": _minutes(10)},
        "greater": {"bonus": 3, "temp_hp": 30, "duration": _hours(1), "fort_crit": True},
        "major": {"bonus": 4, "temp_hp": 45, "duration": _hours(1), "fort_crit": True},
    }

    def _apply_elixir(self, ctx, target, tier: str, tier_data: dict[str, object]) -> None:
        bonus = int(tier_data.get("bonus", 0) or 0)
        duration = int(tier_data.get("duration", 0) or 0)
        effects = []
        if bonus:
            effects.append(
                skill_check_effect(
                    applies_to="source",
                    skills=[Skill.FORTITUDE.value],
                    tags_required=[Skill.FORTITUDE.value],
                    bonus_effects=[
                        skill_bonus_effect(
                            skill_id=Skill.FORTITUDE.value,
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
            remover_status("juggernaut_mutagen")
            remover_status("juggernaut_mutagen_penalty")

        status = make_bonus_status(
            status_id="juggernaut_mutagen",
            label="Juggernaut Mutagen",
            duration=duration,
            data={"effect_tags": ["mutagen", "polymorph"]},
            effects=effects,
        )
        adder = getattr(target, "add_status", None)
        if callable(adder):
            adder(status)

        # penalties: Will, Perception, initiative
        penalty_effects = []
        for skill_id in (Skill.WILL.value, Skill.PERCEPTION.value):
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
        penalty_effects.append(
            skill_check_effect(
                applies_to="source",
                skills=[Skill.PERCEPTION.value],
                tags_required=["initiative"],
                bonus_effects=[
                    skill_bonus_effect(
                        skill_id=Skill.PERCEPTION.value,
                        bonus=2,
                        bonus_type=BonusType.ITEM,
                        source=f"{self.name}:{tier}:initiative",
                        label=f"{self.name} {tier} (penalty)",
                        is_penalty=True,
                    )
                ],
            )
        )
        penalty_status = make_bonus_status(
            status_id="juggernaut_mutagen_penalty",
            label="Juggernaut Mutagen (penalty)",
            duration=duration,
            data={
                "effect_tags": ["mutagen", "polymorph"],
                "initiative_penalty": 2,
            },
            effects=penalty_effects,
        )
        if callable(adder):
            adder(penalty_status)
            state = getattr(ctx.game, "state", None)
            if state is not None and hasattr(state, "sync_status_initiative_penalty"):
                try:
                    state.sync_status_initiative_penalty(target, reorder_round_queue=True)
                except Exception:
                    pass

        temp_hp = int(tier_data.get("temp_hp", 0) or 0)
        if temp_hp:
            try:
                ctx.game.ui_log(f"Juggernaut Mutagen: tymczasowe HP {temp_hp} (opisowo).")
            except Exception:
                pass
        if tier_data.get("fort_crit"):
            try:
                ctx.game.ui_log("Juggernaut Mutagen: sukces na Fortitude -> krytyczny sukces (opisowo).")
            except Exception:
                pass
