from __future__ import annotations

from damage_types import DamageType
from statuses import make_persistent_damage
from combat.damage_utils import burn_it_bonus, burn_it_prompt_note

from .base_alchemical_bomb_event import BaseAlchemicalBombEvent
from ..registry import register_event


@register_event
class AlchemistsFireEvent(BaseAlchemicalBombEvent):
    name = "alchemists_fire"
    damage_type = DamageType.FIRE.value
    splash_damage_type = DamageType.FIRE.value
    prompt_description = (
        "Type lesser; Level 1; Price 3 gp\n"
        "The bomb deals 1d8 fire damage, 1 persistent fire damage, and 1 fire splash damage.\n"
        "Type moderate; Level 3; Price 10 gp\n"
        "You gain a +1 item bonus to attack rolls. The bomb deals 2d8 fire damage, 2 persistent fire damage, and 2 fire splash damage.\n"
        "Type greater; Level 11; Price 250 gp\n"
        "You gain a +2 item bonus to attack rolls. The bomb deals 3d8 fire damage, 3 persistent fire damage, and 3 fire splash damage.\n"
        "Type major; Level 17; Price 2,500 gp\n"
        "You gain a +3 item bonus to attack rolls. The bomb deals 4d8 fire damage, 4 persistent fire damage, and 4 fire splash damage."
    )

    tiers = {
        "lesser": {"item_level": 1, "item_bonus": 0, "damage_dice": "1d8", "splash": 1, "persistent": 1},
        "moderate": {"item_level": 3, "item_bonus": 1, "damage_dice": "2d8", "splash": 2, "persistent": 2},
        "greater": {"item_level": 11, "item_bonus": 2, "damage_dice": "3d8", "splash": 3, "persistent": 3},
        "major": {"item_level": 17, "item_bonus": 3, "damage_dice": "4d8", "splash": 4, "persistent": 4},
    }

    def _prompt_damage(self, tier: str, dice: str) -> int:
        from ui_client import get_ui_client

        ui = get_ui_client()
        item_level = int(self.tiers.get(str(tier).strip().lower(), {}).get("item_level", 1) or 1)
        note = (
            burn_it_prompt_note(
                self._actor_for_prompt,
                self.damage_type,
                source_kind="alchemical",
                item_level=item_level,
            )
            if hasattr(self, "_actor_for_prompt")
            else None
        )
        val = ui.prompt_roll(
            f"{self._event_label()} ({tier}) – podaj obrażenia ({dice}):",
            source=self.name,
            layout="damage",
            answer_placeholder="Obrażenia",
            prompt_long=note,
        )
        bonus = (
            burn_it_bonus(
                self._actor_for_prompt,
                self.damage_type,
                source_kind="alchemical",
                item_level=item_level,
            )
            if hasattr(self, "_actor_for_prompt")
            else 0
        )
        return int(val or 0) + int(bonus)

    def _apply_on_hit(self, ctx, target, target_pos, tier, tier_data, *, critical: bool = False) -> None:
        # zapisz aktora do promptu burn_it
        self._actor_for_prompt = ctx.actor
        try:
            super()._apply_on_hit(ctx, target, target_pos, tier, tier_data, critical=critical)
        finally:
            self._actor_for_prompt = None

        item_level = int(tier_data.get("item_level", 1) or 1)
        persistent = int(tier_data.get("persistent", 0) or 0)
        persistent += int(
            burn_it_bonus(
                ctx.actor,
                DamageType.FIRE.value,
                persistent=True,
                source_kind="alchemical",
                item_level=item_level,
            )
            or 0
        )
        if persistent > 0:
            try:
                target.add_status(make_persistent_damage(persistent, DamageType.FIRE.value, source=self.name))
            except Exception:
                pass
