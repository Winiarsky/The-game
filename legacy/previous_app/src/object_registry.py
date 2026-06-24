"""Prosty rejestr obiektów gry z unikalnymi identyfikatorami."""

from __future__ import annotations

import itertools
import threading
from typing import Any, Optional


class ObjectRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counter = itertools.count(1)
        self._objects: dict[str, Any] = {}

    def _next_id(self) -> str:
        return f"obj-{next(self._counter)}"

    def register(self, obj: Any, object_id: Optional[str] = None) -> str:
        """Zarejestruj obiekt i zwróć jego id."""
        with self._lock:
            oid = object_id or self._next_id()
            existing = self._objects.get(oid)
            if existing is not None and existing is not obj:
                raise ValueError(f"Id '{oid}' jest już zajęte.")
            self._objects[oid] = obj
            return oid

    def unregister(self, object_id: str) -> None:
        with self._lock:
            self._objects.pop(object_id, None)

    def get(self, object_id: str) -> Any | None:
        return self._objects.get(object_id)

    def clear(self) -> None:
        """Czyści rejestr (użyteczne w testach)."""
        with self._lock:
            self._objects.clear()


OBJECT_REGISTRY = ObjectRegistry()


def assign_id(obj: Any, object_id: Optional[str] = None) -> str:
    """Przypisz obiektowi id i go zarejestruj."""
    current = getattr(obj, "object_id", None)
    if current:
        return OBJECT_REGISTRY.register(obj, current)
    return OBJECT_REGISTRY.register(obj, object_id)


def get_object(object_id: str) -> Any | None:
    """Szybki odczyt obiektu po id."""
    return OBJECT_REGISTRY.get(object_id)
