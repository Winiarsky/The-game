from __future__ import annotations

from statuses import SpeedPenaltyStatus, ImmobilizedStatus

from .base_alchemical_bomb_event import BaseAlchemicalBombEvent
from ..registry import register_event


@register_event
class TanglefootBagEvent(BaseAlchemicalBombEvent):
    name = "tanglefoot_bag"
    prompt_description = (
        "Type lesser; Level 1; Price 3 gp\n"
        "The target takes a –10-foot penalty, and the Escape DC is 17.\n"
        "Type moderate; Level 3; Price 10 gp\n"
        "You gain a +1 item bonus to attack rolls, the target takes a –15-foot penalty, and the Escape DC is 19.\n"
        "Type greater; Level 11; Price 250 gp\n"
        "You gain a +2 item bonus to attack rolls, the target takes a –15-foot penalty, and the Escape DC is 28.\n"
        "Type major; Level 17; Price 2,500 gp\n"
        "You gain a +3 item bonus to attack rolls, the target takes a –20-foot penalty, and the Escape DC is 37."
    )

    tiers = {
        "lesser": {"item_bonus": 0, "speed_penalty": 10, "escape_dc": 17},
        "moderate": {"item_bonus": 1, "speed_penalty": 15, "escape_dc": 19},
        "greater": {"item_bonus": 2, "speed_penalty": 15, "escape_dc": 28},
        "major": {"item_bonus": 3, "speed_penalty": 20, "escape_dc": 37},
    }

    def _apply_on_hit(self, ctx, target, target_pos, tier, tier_data, *, critical: bool = False) -> None:
        penalty = int(tier_data.get("speed_penalty", 0) or 0)
        escape_dc = int(tier_data.get("escape_dc", 0) or 0)
        if penalty > 0:
            if target in getattr(ctx.game, "heroes", []):
                try:
                    from ui_client import get_ui_client

                    get_ui_client().prompt_info(
                        "Tanglefoot Bag",
                        prompt_long=(
                            f"Otrzymujesz karę do szybkości -{penalty} stóp na 1 minutę "
                            f"(Escape DC {escape_dc}). Zapisz ręcznie."
                        ),
                        source="tanglefoot_bag",
                    )
                except Exception:
                    pass
            else:
                source_id = getattr(ctx.actor, "object_id", None)
                try:
                    target.add_status(
                        SpeedPenaltyStatus(
                            penalty_feet=penalty,
                            source="tanglefoot_bag",
                            source_id=source_id,
                            source_turns_left=10,
                            label=f"tanglefoot -{penalty}ft",
                            escape_dc=escape_dc,
                        )
                    )
                except Exception:
                    pass

        if critical:
            source_id = getattr(ctx.actor, "object_id", None)
            try:
                target.add_status(
                    ImmobilizedStatus(
                        source="tanglefoot_bag",
                        source_id=source_id,
                        source_turns_left=1,
                    )
                )
            except Exception:
                pass
