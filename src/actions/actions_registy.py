from __future__ import annotations

from typing import Dict, Type

from .base import BaseAction

_ACTIONS: Dict[str, Type[BaseAction]] = {}


def register(action_cls: Type[BaseAction]) -> Type[BaseAction]:
    """Dekorator rejestrujący klasę akcji pod unikalną nazwą."""
    name = getattr(action_cls, "name", None)
    if not name:
        raise ValueError("Akcja musi posiadać atrybut 'name'.")
    if name in _ACTIONS:
        raise ValueError(f"Akcja '{name}' jest już zarejestrowana.")

    _ACTIONS[name] = action_cls
    return action_cls


def get_action(name: str) -> BaseAction:
    """Zwróć instancję zarejestrowanej akcji."""
    try:
        action_cls = _ACTIONS[name]
    except KeyError as exc:
        available = ", ".join(sorted(_ACTIONS))
        raise KeyError(f"Nieznana akcja '{name}'. Dostępne: {available}") from exc
    return action_cls()


def list_actions() -> Dict[str, Type[BaseAction]]:
    """Zwróć kopię rejestru (np. do wyświetlania nazw akcji)."""
    return dict(_ACTIONS)
