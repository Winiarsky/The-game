from dataclasses import dataclass, field
from typing import Optional, Tuple, Protocol, List


class InventoryCarrier(Protocol):
    inventory: List[str]


@dataclass
class Interactable:
    """Obiekt, z którym można wchodzić w interakcję (nie blokuje ruchu)."""

    position: Optional[Tuple[int, int]] = None

    def set_position(self, position: Optional[Tuple[int, int]]) -> None:
        self.position = position

    def can_interact(self, actor: InventoryCarrier, game) -> bool:
        return True

    def interact(self, actor: InventoryCarrier, game) -> str:
        """Zwraca krótką wiadomość o wyniku interakcji."""
        raise NotImplementedError
