"""Rejestr eventów-akcji (karty) i dispatcher nazw -> instancja."""

from __future__ import annotations

from typing import Callable, Dict, Iterable, Type
import logging

from .base import EventContext, EventResult, GameEvent

logger = logging.getLogger(__name__)

_registry: Dict[str, Type[GameEvent]] = {}


def _normalize(name: str) -> str:
    return name.strip().lower()


def register_event(cls: Type[GameEvent]) -> Type[GameEvent]:
    """Dekorator do rejestracji klasy eventu."""
    name = getattr(cls, "name", None)
    if not name:
        raise ValueError(f"Event class {cls.__name__} missing 'name'")
    key = _normalize(name)
    if key in _registry:
        logger.warning("Nadpisuję event '%s' klasą %s", key, cls.__name__)
    _registry[key] = cls
    return cls


def get_event_cls(name: str) -> Type[GameEvent]:
    key = _normalize(name)
    if key not in _registry:
        raise KeyError(f"Nieznany event '{name}'")
    return _registry[key]


def list_events() -> Dict[str, Type[GameEvent]]:
    return dict(_registry)


def dispatch_event(name: str, ctx: EventContext) -> EventResult:
    """Znajdź event po nazwie i uruchom jego lifecycle."""
    event_cls = get_event_cls(name)
    event = event_cls()

    # Magiczne eventy wymagają dodatkowej walidacji (koszt akcji, tryb tury)
    try:
        from .magic.magic_event import MagicEvent, MagicEventResolver
    except Exception:  # pragma: no cover - brak zależności magicznych
        MagicEvent = None  # type: ignore
        MagicEventResolver = None  # type: ignore

    # dostępność fazowa
    if ctx.in_combat and not event.available_in_combat:
        msg = f"Event '{name}' niedostępny w walce."
        logger.info(msg)
        return EventResult(success=False, consumed_action=False, message=msg)
    if ctx.in_exploration and not event.available_in_exploration:
        msg = f"Event '{name}' niedostępny poza walką."
        logger.info(msg)
        return EventResult(success=False, consumed_action=False, message=msg)

    if MagicEvent and isinstance(event, MagicEvent):
        result = MagicEventResolver.resolve(event, ctx)  # type: ignore[arg-type]
    else:
        result = event.run(ctx)
    if result is None:  # type: ignore[unreachable]
        result = EventResult()
    # Jeśli wynik nie określił consumed_action, przyjmij flagę z klasy.
    if result.consumed_action is None:  # pragma: no cover - defensywnie
        result.consumed_action = event.consumes_action
    if result.actions_spent is None and result.consumed_action:
        try:
            result.actions_spent = getattr(event, "actions_cost", 1)
        except Exception:
            result.actions_spent = 1
    return result


def iter_event_names() -> Iterable[str]:
    for name in _registry:
        yield name
