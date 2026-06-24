from __future__ import annotations

from damage_types import DamageType
from statuses import SpeedPenaltyStatus

from .base_alchemical_bomb_event import BaseAlchemicalBombEvent
from ..registry import register_event


@register_event
class FrostVialEvent(BaseAlchemicalBombEvent):
    name = "frost_vial"
    damage_type = DamageType.COLD.value
    splash_damage_type = DamageType.COLD.value
    prompt_description = (
        "Type lesser; Level 1; Price 3 gp\n"
        "The bomb deals 1d6 cold damage and 1 cold splash damage, and the target takes a –5-foot penalty.\n"
        "Type moderate; Level 3; Price 10 gp\n"
        "You gain a +1 item bonus to attack rolls, the bomb deals 2d6 cold damage and 2 cold splash damage, "
        "and the target takes a –10-foot penalty.\n"
        "Type greater; Level 11; Price 250 gp\n"
        "You gain a +2 item bonus to attack rolls, the bomb deals 3d6 cold damage and 3 cold splash damage, "
        "and the target takes a –10-foot penalty.\n"
        "Type major; Level 17; Price 2,500 gp\n"
        "You gain a +3 item bonus to attack rolls, the bomb deals 4d6 cold damage and 4 cold splash damage, "
        "and the target takes a –15-foot penalty."
    )

    tiers = {
        "lesser": {"item_bonus": 0, "damage_dice": "1d6", "splash": 1, "speed_penalty": 5},
        "moderate": {"item_bonus": 1, "damage_dice": "2d6", "splash": 2, "speed_penalty": 10},
        "greater": {"item_bonus": 2, "damage_dice": "3d6", "splash": 3, "speed_penalty": 10},
        "major": {"item_bonus": 3, "damage_dice": "4d6", "splash": 4, "speed_penalty": 15},
    }

    def _apply_on_hit(self, ctx, target, target_pos, tier, tier_data, *, critical: bool = False) -> None:
        super()._apply_on_hit(ctx, target, target_pos, tier, tier_data, critical=critical)
        penalty = int(tier_data.get("speed_penalty", 0) or 0)
        if penalty <= 0:
            return
        if target in getattr(ctx.game, "heroes", []):
            try:
                from ui_client import get_ui_client

                get_ui_client().prompt_info(
                    "Frost Vial",
                    prompt_long=f"Otrzymujesz karę do szybkości -{penalty} stóp (zapisz ręcznie).",
                    source="frost_vial",
                )
            except Exception:
                pass
            return
        source_id = getattr(ctx.actor, "object_id", None)
        try:
            target.add_status(
                SpeedPenaltyStatus(
                    penalty_feet=penalty,
                    source="frost_vial",
                    source_id=source_id,
                    source_turns_left=1,
                    label=f"frost vial -{penalty}ft",
                )
            )
        except Exception:
            pass
