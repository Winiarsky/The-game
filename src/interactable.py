from dataclasses import dataclass
from typing import Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from board_grid import Occupant


@dataclass
class Interactable:
    """Obiekt, z którym można wchodzić w interakcję."""

    position: Optional[Tuple[int, int]] = None
    blocks_movement: bool = False  # jeśli True: traktujemy jak przeszkodę, nie da się wejść na pole
    allow_same_cell_interact: bool = True  # jeśli False: wymagaj stania obok
    dc: int = 15  # trudność interakcji
    critical_failure_dc: int = dc - 10   # próg krytycznej porażki
    critical_success_dc: int = dc + 10  # próg krytycznego sukcesu
    

    def set_position(self, position: Optional[Tuple[int, int]]) -> None:
        self.position = position

    def can_interact(self, actor: "Occupant", game) -> bool:
        return True

    def interact(self, actor: "Occupant", game):
        """Zwraca krótką wiadomość o wyniku interakcji."""
        raise NotImplementedError
