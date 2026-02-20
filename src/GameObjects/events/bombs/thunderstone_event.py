from __future__ import annotations

from damage_types import DamageType
from skills import Skill
from statuses import DeafenedStatus
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources
from GameObjects.events.magic.magic_utils import grid_distance_feet

from .base_alchemical_bomb_event import BaseAlchemicalBombEvent
from ..registry import register_event


@register_event
class ThunderstoneEvent(BaseAlchemicalBombEvent):
    name = "thunderstone"
    damage_type = DamageType.SONIC.value
    splash_damage_type = DamageType.SONIC.value
    prompt_description = (
        "Type lesser; Level 1; Price 3 gp\n"
        "The bomb deals 1d4 sonic damage and 1 sonic splash damage, and the DC is 17.\n"
        "Type moderate; Level 3; Price 10 gp\n"
        "You gain a +1 item bonus to attack rolls. The bomb deals 2d4 sonic damage and 2 sonic splash damage, and the DC is 20.\n"
        "Type greater; Level 11; Price 250 gp\n"
        "You gain a +2 item bonus to attack rolls. The bomb deals 3d4 sonic damage and 3 sonic splash damage, and the DC is 28.\n"
        "Type major; Level 17; Price 2,500 gp\n"
        "You gain a +3 item bonus to attack rolls. The bomb deals 4d4 sonic damage and 4 sonic splash damage, and the DC is 36."
    )

    tiers = {
        "lesser": {"item_bonus": 0, "damage_dice": "1d4", "splash": 1, "dc": 17},
        "moderate": {"item_bonus": 1, "damage_dice": "2d4", "splash": 2, "dc": 20},
        "greater": {"item_bonus": 2, "damage_dice": "3d4", "splash": 3, "dc": 28},
        "major": {"item_bonus": 3, "damage_dice": "4d4", "splash": 4, "dc": 36},
    }

    def _apply_on_hit(self, ctx, target, target_pos, tier, tier_data, *, critical: bool = False) -> None:
        super()._apply_on_hit(ctx, target, target_pos, tier, tier_data, critical=critical)
        dc = int(tier_data.get("dc", 0) or 0)
        if dc <= 0 or target_pos is None:
            return
        self._apply_deafened(ctx, target_pos, dc)

    def _apply_deafened(self, ctx, center_pos, dc: int) -> None:
        actors = list(getattr(ctx.game, "heroes", [])) + list(getattr(ctx.game, "enemies", []))
        for actor in actors:
            pos = getattr(actor, "position", None)
            if pos is None:
                continue
            if grid_distance_feet(center_pos, pos) > 10:
                continue
            res = resolve_skill_check_with_sources(
                skill_id=Skill.FORTITUDE.value,
                dc=dc,
                actor=actor,
                target=None,
                tags=["fortitude", "save", "sonic"],
                apply_modifiers=True,
            )
            if res.outcome in ("failure", "critical_failure"):
                source_id = getattr(ctx.actor, "object_id", None)
                try:
                    actor.add_status(
                        DeafenedStatus(
                            source="thunderstone",
                            source_id=source_id,
                            source_turns_left=1,
                        )
                    )
                    state = getattr(ctx.game, "state", None)
                    if state is not None and hasattr(state, "apply_initiative_penalty"):
                        state.apply_initiative_penalty(actor, 2)
                except Exception:
                    pass
