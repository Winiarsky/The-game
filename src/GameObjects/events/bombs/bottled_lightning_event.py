from __future__ import annotations

from damage_types import DamageType
from statuses import Status

from .base_alchemical_bomb_event import BaseAlchemicalBombEvent
from ..registry import register_event


@register_event
class BottledLightningEvent(BaseAlchemicalBombEvent):
    name = "bottled_lightning"
    damage_type = DamageType.ELECTRIC.value
    splash_damage_type = DamageType.ELECTRIC.value
    prompt_description = (
        "Type lesser; Level 1; Price 3 gp\n"
        "It deals 1d6 electricity damage and 1 electricity splash damage.\n"
        "Type moderate; Level 3; Price 10 gp\n"
        "You gain a +1 item bonus to attack rolls. The bomb deals 2d6\n"
        "electricity damage and 2 electricity splash damage.\n"
        "Type greater; Level 11; Price 250 gp\n"
        "You gain a +2 item bonus to attack rolls. The bomb deals 3d6\n"
        "electricity damage and 3 electricity splash damage.\n"
        "Type major; Level 17; Price 2,500 gp\n"
        "You gain a +3 item bonus to attack rolls. The bomb deals 4d6\n"
        "electricity damage and 4 electricity splash damage."
    )

    tiers = {
        "lesser": {"item_bonus": 0, "damage_dice": "1d6", "splash": 1},
        "moderate": {"item_bonus": 1, "damage_dice": "2d6", "splash": 2},
        "greater": {"item_bonus": 2, "damage_dice": "3d6", "splash": 3},
        "major": {"item_bonus": 3, "damage_dice": "4d6", "splash": 4},
    }

    def _apply_on_hit(self, ctx, target, target_pos, tier, tier_data, *, critical: bool = False) -> None:
        super()._apply_on_hit(ctx, target, target_pos, tier, tier_data, critical=critical)
        source_id = getattr(ctx.actor, "object_id", None)
        status = Status(
            id="flat_footed",
            label="flat-footed",
            data={
                "ac_penalty": 2,
                "flat_footed_source": "bottled_lightning",
                "source_id": source_id,
                "source_turns_left": 1,
            },
        )
        try:
            target.add_status(status)
        except Exception:
            pass
