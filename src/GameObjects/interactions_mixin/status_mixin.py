from __future__ import annotations

from dataclasses import dataclass, field

from statuses import Status


@dataclass
class StatusMixin:
    """Mixin do zarządzania statusami (unikalna lista Status, kompatybilna ze stringami)."""

    statuses: list[Status] = field(default_factory=list)

    def _normalize(self, status: str | Status) -> Status:
        return status if isinstance(status, Status) else Status(id=status)

    def _ensure_status_objects(self) -> None:
        if not self.statuses:
            return
        if all(isinstance(s, Status) for s in self.statuses):
            return
        self.statuses = [self._normalize(s) for s in self.statuses]

    def has_status(self, status: str | Status) -> bool:
        self._ensure_status_objects()
        return any(s == status for s in self.statuses)

    def add_status(self, status: str | Status) -> bool:
        self._ensure_status_objects()
        normalized = self._normalize(status)
        if any(s == normalized for s in self.statuses):
            return False
        self.statuses.append(normalized)
        return True

    def remove_status(self, status: str | Status) -> bool:
        self._ensure_status_objects()
        for idx, item in enumerate(self.statuses):
            if item == status:
                del self.statuses[idx]
                return True
        return False

    def clear_statuses(self, *statuses: str | Status) -> int:
        """Usuń podane statusy, zwróć liczbę usuniętych wpisów."""
        self._ensure_status_objects()
        to_remove = {self._normalize(s).id for s in statuses} if statuses else {s.id for s in self.statuses}
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
