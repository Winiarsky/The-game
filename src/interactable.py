from dataclasses import dataclass, field
from typing import Optional, Tuple, Protocol, List


class InventoryCarrier(Protocol):
    inventory: List[str]


@dataclass
class Interactable:
    """Obiekt, z którym można wchodzić w interakcję."""

    position: Optional[Tuple[int, int]] = None
    blocks_movement: bool = False  # jeśli True: traktujemy jak przeszkodę, nie da się wejść na pole
    allow_same_cell_interact: bool = True  # jeśli False: wymagaj stania obok

    def set_position(self, position: Optional[Tuple[int, int]]) -> None:
        self.position = position

    def can_interact(self, actor: InventoryCarrier, game) -> bool:
        return True

    def interact(self, actor: InventoryCarrier, game) -> str:
        """Zwraca krótką wiadomość o wyniku interakcji."""
        raise NotImplementedError
