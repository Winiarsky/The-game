from dataclasses import dataclass, field
from typing import Callable, Optional, Tuple, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from board_grid import Occupant


# luźny typ handlera, by dopuścić metody podklas
InteractionHandler = Callable[[Any, "Occupant", Any, Optional[dict]], str]


@dataclass
class Interaction:
    """Opis pojedynczej akcji dostępnej dla obiektu."""

    id: str
    label: str
    description: str = ""
    handler: InteractionHandler = lambda *_args, **_kwargs: "Brak akcji."
    enabled: bool = True

    def execute(self, interactable: "Interactable", actor: "Occupant", game, payload: Optional[dict] = None) -> str:
        if not self.enabled:
            return f"Akcja '{self.label}' jest niedostępna."
        return self.handler(interactable, actor, game, payload or {})


@dataclass
class Interactable:
    """Obiekt, z którym można wchodzić w interakcję."""

    position: Optional[Tuple[int, int]] = None
    blocks_movement: bool = False  # jeśli True: traktujemy jak przeszkodę, nie da się wejść na pole
    allow_same_cell_interact: bool = True  # jeśli False: wymagaj stania obok
    dc: int = 15  # trudność interakcji
    critical_failure_dc: int = dc - 10   # próg krytycznej porażki
    critical_success_dc: int = dc + 10  # próg krytycznego sukcesu
    actions: dict[str, Interaction] = field(default_factory=dict, init=False, repr=False)
    

    def set_position(self, position: Optional[Tuple[int, int]]) -> None:
        self.position = position

    def can_interact(self, actor: "Occupant", game) -> bool:
        return True

    def register_action(self, interaction: Interaction) -> None:
        """Zarejestruj nową akcję możliwą do wyboru."""
        self.actions[interaction.id] = interaction

    def disable_action(self, action_id: str) -> None:
        if action_id in self.actions:
            self.actions[action_id].enabled = False

    def available_actions(self) -> list[Interaction]:
        return [i for i in self.actions.values() if i.enabled]

    def _prompt_action_choice(self) -> Optional[str]:
        """Prosta konsolowa selekcja akcji."""
        actions = self.available_actions()
        if not actions:
            return None
        print("Dostępne akcje:")
        for idx, action in enumerate(actions, start=1):
            suffix = f" — {action.description}" if action.description else ""
            print(f"{idx}. {action.label}{suffix}")
        choice = input("Wybierz numer akcji (lub Enter aby anulować): ").strip()
        if not choice:
            return None
        if not choice.isdigit():
            return None
        index = int(choice) - 1
        if index < 0 or index >= len(actions):
            return None
        return actions[index].id

    def interact(self, actor: "Occupant", game, action_id: Optional[str] = None, payload: Optional[dict] = None):
        """Zwraca krótką wiadomość o wyniku interakcji."""
        if action_id is None:
            action_id = self._prompt_action_choice()
        if action_id is None:
            return "Przerywasz interakcję."
        interaction = self.actions.get(action_id)
        if interaction is None:
            return f"Akcja '{action_id}' jest niedostępna."
        return interaction.execute(self, actor, game, payload)
