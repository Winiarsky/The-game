from __future__ import annotations

from dataclasses import dataclass, field

from GameObjects.interactions_mixin.base_interaction import InteractableMixin, Interaction
from GameObjects.items.inventory import add_item, item_label


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
        for item in taken:
            add_item(actor, item)
        labels = ", ".join(item_label(item) for item in taken[:4])
        if len(taken) > 4:
            labels = f"{labels}, +{len(taken) - 4} więcej"
        if self.position is not None:
            try:
                game.board.remove_interactable(self, self.position)
            except Exception:
                pass
        return f"Podniesiono loot: {labels}."


__all__ = [
    "LootPile",
]
