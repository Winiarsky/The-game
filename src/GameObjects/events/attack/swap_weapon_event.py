from __future__ import annotations

from GameObjects.items.inventory import ensure_actor_inventory, get_equipped_weapons, item_category, item_label, set_equipped_weapons
from GameObjects.items.weapon import normalize_weapon_id
from ..base import EventContext, EventResult, GameEvent
from ..registry import register_event


@register_event
class SwapWeaponEvent(GameEvent):
    name = "swap_weapon"
    default_tags = ["weapon", "manipulate"]
    consumes_action = True

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak aktora do zmiany broni.")

        inventory = ensure_actor_inventory(actor)
        weapons = [item for item in inventory if item_category(item) == "weapon"]
        available = [normalize_weapon_id(getattr(item, "item_id", None)) for item in weapons]
        available = [wid for wid in available if wid]
        if not available:
            return EventResult.cancelled(message="Brak dostępnych broni.")

        current_equipped = get_equipped_weapons(actor)
        current = normalize_weapon_id(getattr(current_equipped[0], "item_id", None)) if current_equipped else None

        choice_raw = (ctx.metadata or {}).get("weapon_id") or (ctx.metadata or {}).get("weapon")
        if choice_raw is None:
            choice_raw = ctx.game.conn.read_card(
                f"Wybierz broń ({', '.join(available)})",
                list(available),
            )

        normalized = normalize_weapon_id(choice_raw)
        if not normalized:
            return EventResult.cancelled(message="Nie rozpoznano broni.")
        if normalized not in available:
            return EventResult.cancelled(
                message=f"Ta broń nie jest w loadoucie bohatera ({', '.join(available)})."
            )
        if current == normalized:
            for item in weapons:
                if normalize_weapon_id(getattr(item, "item_id", None)) == normalized:
                    return EventResult.noop(message=f"Masz już aktywną broń: {item_label(item)}.")
            return EventResult.noop(message=f"Masz już aktywną broń: {normalized}.")

        selected = None
        for item in weapons:
            if normalize_weapon_id(getattr(item, "item_id", None)) == normalized:
                selected = item
                break
        if selected is None:
            return EventResult.cancelled(message="Nie udało się zmienić aktywnej broni.")
        set_equipped_weapons(actor, [selected])

        return EventResult(
            success=True,
            consumed_action=True,
            message=f"Aktywna broń: {item_label(selected)}.",
        )
