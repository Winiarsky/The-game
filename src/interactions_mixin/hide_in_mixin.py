from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from statuses import HIDE_STATUS, HideStatus, Status


@dataclass(init=False)
class HideInMixin:
    """Mixin dający możliwość ukrycia pasażera w obiekcie."""

    hide_status: str | Status = HIDE_STATUS
    hide_stealth_bonus: int = 2

    def __init__(
        self,
        *,
        hide_status: str | Status = HIDE_STATUS,
        hide_stealth_bonus: int = 2,
        **_kwargs,
    ) -> None:
        # pozwól podać string lub Status; w razie potrzeby utwórz nowy obiekt HideStatus
        self.hide_status = hide_status if hide_status is not None else HideStatus()
        self.hide_stealth_bonus = hide_stealth_bonus
        # obiekty mogą mieć atrybut someone_inside; jeśli brak, ustawiany przy pierwszym użyciu

    def _hide_in_precheck(self, actor, game) -> Optional[str]:
        """Opcjonalne pre-checki; zwróć komunikat błędu by zablokować."""
        return None

    def hide_in(self, actor, game) -> str:
        """Umieść aktora w obiekcie, nadaj status hide i premię do stealth."""
        failure = self._hide_in_precheck(actor, game)
        if failure:
            return failure
        position = getattr(self, "position", None)
        if position is None:
            return "Obiekt nie jest na planszy."
        board = game.board
        occupant = board.occupant_at(position)
        passenger = getattr(self, "someone_inside", None)
        if passenger is not None and passenger is not actor:
            return "Obiekt jest już zajęty."
        if occupant is not None and occupant is not actor:
            return "Ktoś już zajmuje to pole."

        if actor.position is not None:
            board.remove(actor.position)
        board.place(actor, position)
        setattr(self, "someone_inside", actor)

        if hasattr(actor, "add_status"):
            try:
                actor.add_status(self.hide_status)  # type: ignore[attr-defined]
            except Exception:
                pass
        else:
            statuses = getattr(actor, "statuses", None)
            if isinstance(statuses, list) and self.hide_status not in statuses:
                statuses.append(self.hide_status)
        setattr(actor, "hide_stealth_bonus", getattr(actor, "hide_stealth_bonus", 0) + self.hide_stealth_bonus)
        return "Ukrywasz się w środku i zyskujesz osłonę."
