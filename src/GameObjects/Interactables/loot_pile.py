from __future__ import annotations

from dataclasses import dataclass, field

from GameObjects.interactions_mixin.base_interaction import InteractableMixin, Interaction
from GameObjects.items.inventory import add_item, item_label
from economy import add_actor_cp, format_cp_value


@dataclass
class LootPile(InteractableMixin):
    name: str = "Loot"
    loot_items: list[object] = field(default_factory=list)
    allow_same_cell_interact: bool = True
    require_same_cell_interact: bool = False
    allow_hidden_interaction: bool = False
    blocks_movement: bool = False

    def __post_init__(self) -> None:
        super().__post_init__()
        self.register_action(
            Interaction(
                id="pickup_loot",
                label="Podnieś loot",
                description="Podnosi wszystkie przedmioty z tego pola.",
                handler=self._pickup_handler,
                tags=["interaction", "manipulate", "loot"],
                end_interaction=True,
            )
        )

    def can_interact(self, actor, game) -> bool:
        return bool(self.loot_items)

    def _pickup_handler(self, _interactable, actor, game, _payload) -> str:
        if not self.loot_items:
            return "Brak przedmiotów do podniesienia."
        taken = list(self.loot_items)
        self.loot_items.clear()
        item_loot: list[object] = []
        coin_cp = 0
        for item in taken:
            if isinstance(item, dict) and str(item.get("kind", "")).strip().lower() == "currency_cp":
                try:
                    coin_cp += max(0, int(item.get("amount_cp", 0) or 0))
                except Exception:
                    continue
                continue
            item_loot.append(item)
        for item in item_loot:
            add_item(actor, item)
        if coin_cp > 0:
            add_actor_cp(actor, coin_cp)

        labels_parts: list[str] = []
        if item_loot:
            labels_parts.append(", ".join(item_label(item) for item in item_loot[:4]))
            if len(item_loot) > 4:
                labels_parts.append(f"+{len(item_loot) - 4} więcej")
        if coin_cp > 0:
            labels_parts.append(f"monety: {format_cp_value(coin_cp)}")
        labels = ", ".join(part for part in labels_parts if str(part).strip())
        if not labels:
            labels = "nic użytecznego"
        if self.position is not None:
            try:
                game.board.remove_interactable(self, self.position)
            except Exception:
                pass
        return f"Podniesiono loot: {labels}."


__all__ = [
    "LootPile",
]
