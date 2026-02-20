from __future__ import annotations

import logging

from damage_types import DamageType
from statuses import make_persistent_damage
from combat.damage_utils import apply_splash_damage

from .base_alchemical_bomb_event import BaseAlchemicalBombEvent
from ..registry import register_event

logger = logging.getLogger(__name__)


@register_event
class AcidFlaskEvent(BaseAlchemicalBombEvent):
    name = "acidflask"
    actions_cost = 1
    range_feet = 20
    splash_damage_type = DamageType.ACID.value
    prompt_description = (
        "Type lesser; Level 1; Price 3 gp\n"
        "It deals 1d6 persistent acid damage and 1 acid splash damage.\n"
        "Type moderate; Level 3; Price 10 gp\n"
        "You gain a +1 item bonus to attack rolls. The bomb deals 2d6\n"
        "persistent acid damage and 2 acid splash damage.\n"
        "Type greater; Level 11; Price 250 gp\n"
        "You gain a +2 item bonus to attack rolls. The bomb deals\n"
        "3d6 persistent acid damage and 3 acid splash damage.\n"
        "Type major; Level 17; Price 2,500 gp\n"
        "You gain a +3 item bonus to attack rolls. The bomb deals\n"
        "4d6 persistent acid damage and 4 acid splash damage."
    )

    tiers = {
        "lesser": {"item_bonus": 0, "persistent": "1d6", "splash": 1},
        "moderate": {"item_bonus": 1, "persistent": "2d6", "splash": 2},
        "greater": {"item_bonus": 2, "persistent": "3d6", "splash": 3},
        "major": {"item_bonus": 3, "persistent": "4d6", "splash": 4},
    }

    def _apply_on_hit(self, ctx, target, target_pos, tier, tier_data, *, critical: bool = False) -> None:
        persistent_value = self._prompt_persistent(tier, str(tier_data.get("persistent", "")))
        if persistent_value and persistent_value > 0:
            try:
                target.add_status(make_persistent_damage(persistent_value, DamageType.ACID.value, source=self.name))
            except Exception as exc:
                logger.debug("Nie udało się dodać persistent acid: %s", exc)

        splash = int(tier_data.get("splash", 0) or 0)
        if splash > 0:
            apply_splash_damage(
                ctx.game,
                target_pos,
                splash,
                DamageType.ACID.value,
                exclude=target,
                info_title="Acid Splash",
                source="acid_flask",
            )

    def _prompt_persistent(self, tier: str, dice: str) -> int:
        from ui_client import get_ui_client

        ui = get_ui_client()
        val = ui.prompt_roll(
            f"Acid Flask ({tier}) – podaj obrażenia persistent acid ({dice}):",
            source="acid_flask",
            layout="damage",
            answer_placeholder="Persistent acid",
        )
        return int(val or 0)
