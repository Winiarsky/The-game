from GameObjects.base import GameObjectMeta
from interactable import Interactable


class LockedChest(Interactable):
    """Prosta skrzynia: otwórz, aby zebrać skarb."""

    def __init__(self, loot: list[str] | None = None, locked: bool = True):
        super().__init__(position=None)
        self.locked = locked
        self.opened = False
        self.loot = loot or ["gold_coin", "gem"]

    def can_interact(self, actor, game) -> bool:
        return not self.opened

    def interact(self, actor, game) -> str:
        if self.opened:
            return "Skrzynia jest pusta."
        if self.locked:
            # Na razie brak kluczy – otwieramy przy pierwszej interakcji.
            self.locked = False
        self.opened = True
        if hasattr(actor, "inventory"):
            actor.inventory.extend(self.loot)
        return f"Otwierasz skrzynię i znajdujesz: {', '.join(self.loot)}." # dodac check na rezultat testu
    


META = GameObjectMeta(
    object_id="locked_chest",
    label="Zamknięta skrzynia",
    color="#c58f22",
    category="Interactables",
    placement="cell",
    description="Skrzynia ze skarbem, interakcja: otwórz i zabierz łup.",
    logic_cls=LockedChest,
)
