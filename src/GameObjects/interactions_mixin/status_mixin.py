from __future__ import annotations

from dataclasses import dataclass, field, replace
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from statuses import Status

logger = logging.getLogger(__name__)


@dataclass
class StatusMixin:
    """
    Mixin do zarządzania statusami (unikalna lista Status, kompatybilna ze stringami).

    Kontrakt:
    - add_status przyjmuje wyłącznie instancje Status (stringi są odrzucane).
    - do odczytu danych statusów używaj helperów get_status / get_status_data,
      zamiast przechowywać duplikaty pól na aktorze.
    """

    statuses: list["Status"] = field(default_factory=list)

    def _ui_log(self, message: str) -> None:
        ui_log = getattr(self, "ui_log", None)
        if callable(ui_log):
            ui_log(message)
            return
        game = getattr(self, "game", None)
        if game is not None:
            game_ui_log = getattr(game, "ui_log", None)
            if callable(game_ui_log):
                game_ui_log(message)

    def _status_immunity_blocks(self, incoming: "Status") -> bool:
        incoming_id = incoming.id
        incoming_tags = set(getattr(incoming, "data", {}).get("effect_tags", []) or [])
        for s in self.statuses:
            data = getattr(s, "data", None) or {}
            immune_ids = set(data.get("immune_status_ids", []) or [])
            if incoming_id in immune_ids:
                return True
            immune_tags = set(data.get("immune_status_tags", []) or [])
            if incoming_tags and immune_tags.intersection(incoming_tags):
                return True
        return False

    def _ensure_status_objects(self) -> None:
        if not self.statuses:
            return
        from statuses import Status  # lokalny import by unikać cykli
        # Zachowawczo konwertuj ewentualne stare stringi na Status, aby utrzymać spójność.
        if not all(isinstance(s, Status) for s in self.statuses):
            self.statuses = [s if isinstance(s, Status) else Status(id=str(s)) for s in self.statuses]

    def has_status(self, status: str | "Status") -> bool:
        self._ensure_status_objects()
        from statuses import Status  # lokalny import by unikać cykli
        status_id = status.id if isinstance(status, Status) else str(status)
        return any(s.id == status_id for s in self.statuses)

    def add_status(self, status: str | "Status") -> bool:
        """Dodaj status – wymagany obiekt Status (nie string)."""
        from statuses import Status  # lokalny import by unikać cykli
        if not isinstance(status, Status):
            raise TypeError("add_status oczekuje instancji Status.")
        self._ensure_status_objects()
        if self._status_immunity_blocks(status):
            msg = f"Status '{getattr(status, 'label', status.id)}' zablokowany przez immunitet."
            logger.info(msg)
            self._ui_log(msg)
            return False
        if not getattr(status, "stacks", False):
            if any(s.id == status.id for s in self.statuses):
                return False
        self.statuses.append(status)
        self._apply_granted_statuses(status)
        self._ui_log(f"Otrzymujesz status: {status.display_label}.")
        return True

    def _apply_granted_statuses(self, status: "Status") -> None:
        data = getattr(status, "data", None) or {}
        grants = data.get("grants_statuses") or data.get("grants_status") or []
        if not grants:
            return
        from statuses import Status  # lokalny import by unikać cykli
        for granted in grants:
            if isinstance(granted, Status):
                if granted.id == status.id:
                    continue
                self.add_status(granted)
            elif isinstance(granted, str):
                if granted == status.id:
                    continue
                try:
                    self.add_status(Status(id=granted))
                except Exception:
                    continue

    def remove_status(self, status: str | "Status") -> bool:
        self._ensure_status_objects()
        from statuses import Status  # lokalny import by unikać cykli
        target_id = status.id if isinstance(status, Status) else str(status)
        for idx, item in enumerate(self.statuses):
            if getattr(item, "id", None) == target_id:
                del self.statuses[idx]
                return True
        return False

    def get_status(self, status_id: str) -> Status | None:
        """Zwróć pierwszą instancję Status o podanym id albo None."""
        self._ensure_status_objects()
        for status in self.statuses:
            if getattr(status, "id", None) == status_id:
                return status
        return None

    def get_status_data(self, status_id: str, key: str, default=None):
        """Shortcut do pobrania danych z statusu."""
        status = self.get_status(status_id)
        if status is None:
            return default
        data = getattr(status, "data", None) or {}
        return data.get(key, default)

    def clear_statuses(self, *statuses: str | "Status") -> int:
        """Usuń podane statusy, zwróć liczbę usuniętych wpisów."""
        self._ensure_status_objects()
        from statuses import Status  # lokalny import by unikać cykli
        to_remove = {s.id if isinstance(s, Status) else str(s) for s in statuses} if statuses else {s.id for s in self.statuses}
        new_statuses: list[Status] = []
        removed = 0
        for status in self.statuses:
            if status.id in to_remove:
                removed += 1
                continue
            new_statuses.append(status)
        self.statuses = new_statuses
        return removed

    def status_labels(self) -> list[str]:
        """Zwraca listę etykiet (label -> id) do logów/UI."""
        self._ensure_status_objects()
        return [s.display_label for s in self.statuses]

    def tick_statuses_turn(self) -> int:
        """Zdekrementuj duration statusów; usuń wygasłe."""
        self._ensure_status_objects()
        if not self.statuses:
            return 0
        remaining: list[Status] = []
        removed = 0
        for status in self.statuses:
            duration = getattr(status, "duration", None)
            if duration is None:
                remaining.append(status)
                continue
            try:
                turns = int(duration) - 1
            except Exception:
                remaining.append(status)
                continue
            if turns <= 0:
                removed += 1
                continue
            remaining.append(replace(status, duration=turns))
        self.statuses = remaining
        return removed
