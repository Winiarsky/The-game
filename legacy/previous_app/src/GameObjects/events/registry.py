"""Rejestr eventów-akcji (karty) i dispatcher nazw -> instancja."""

from __future__ import annotations

from typing import Callable, Dict, Iterable, Type
import logging

from .base import EventContext, EventResult, GameEvent, mapping_setdefault_actor
from .exploration_combat_trigger import maybe_trigger_exploration_combat

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
        # spróbuj doładować skill_check (bez pełnego all_events)
        if key == "skill_check":
            try:
                from importlib import import_module

                import_module(".checks.skill_check_event", package=__package__)
            except Exception as exc:
                logger.warning("Nie udało się doładować skill_check: %s", exc)
        # spróbuj doładować wszystkie eventy
        try:
            from importlib import import_module

            import_module(".all_events", package=__package__)
        except Exception:
            pass
        if key not in _registry:
            raise KeyError(f"Nieznany event '{name}'")
    return _registry[key]


def list_events() -> Dict[str, Type[GameEvent]]:
    # Lazy-load skill_check on first access to list_events to avoid circular imports.
    if "skill_check" not in _registry:
        try:
            from importlib import import_module

            import_module(".checks.skill_check_event", package=__package__)
        except Exception as exc:
            logger.warning("Nie udało się zarejestrować skill_check: %s", exc)
    return dict(_registry)


def dispatch_event(name: str, ctx: EventContext) -> EventResult:
    """Znajdź event po nazwie i uruchom jego lifecycle."""
    # Upewnij się, że wszystkie eventy są zarejestrowane (ważne dla skill_check).
    try:
        import importlib

        importlib.import_module("GameObjects.events.all_events")
    except Exception:
        pass
    # awaryjna rejestracja skill_check bezpośrednio
    key = _normalize(name)
    if key == "skill_check" and key not in _registry:
        try:
            from .checks.skill_check_event import GenericSkillCheckEvent

            _registry[key] = GenericSkillCheckEvent
        except Exception as exc:
            logger.warning("Nie udało się wymusić rejestracji skill_check: %s", exc)

    event_cls = get_event_cls(name)
    event = event_cls()
    started_in_exploration = bool(ctx.in_exploration)
    game = getattr(ctx, "game", None)
    dispatch_depth = 0
    if game is not None:
        try:
            dispatch_depth = int(getattr(game, "_event_dispatch_depth", 0) or 0)
        except Exception:
            dispatch_depth = 0
        setattr(game, "_event_dispatch_depth", dispatch_depth + 1)
        if dispatch_depth == 0:
            setattr(game, "_exploration_combat_triggered_in_dispatch", False)

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

    try:
        if MagicEvent and isinstance(event, MagicEvent):
            result = MagicEventResolver.resolve(event, ctx)  # type: ignore[arg-type]
        else:
            result = event.run(ctx)
        if result is None:  # type: ignore[unreachable]
            result = EventResult()

        # Globalny tracking traitów akcji (PF2): attack/open/flourish.
        if ctx.in_combat and result.success and result.consumed_action and ctx.actor is not None:
            try:
                combat_state = getattr(ctx.game, "state", None)
                attack_state = getattr(combat_state, "attack_state", None)
                if isinstance(attack_state, dict):
                    payload = mapping_setdefault_actor(attack_state, ctx.actor, dict)
                    if not isinstance(payload, dict):
                        payload = {}
                    tags = set(event._effective_tags(ctx))
                    used_attack = (
                        "attack" in tags
                        or any(str(tag).startswith("attack_") for tag in tags)
                        or "ranged_attack" in tags
                    )
                    if used_attack:
                        payload["used_attack_action"] = True
                    if "flourish" in tags:
                        payload["used_flourish_action"] = True
            except Exception:
                logger.debug("Nie udało się zaktualizować trait usage dla akcji '%s'.", name, exc_info=True)

        # Jeśli wynik nie określił consumed_action, przyjmij flagę z klasy.
        if result.consumed_action is None:  # pragma: no cover - defensywnie
            result.consumed_action = event.consumes_action
        if result.actions_spent is None and result.consumed_action:
            try:
                result.actions_spent = getattr(event, "actions_cost", 1)
            except Exception:
                result.actions_spent = 1

        if started_in_exploration:
            try:
                maybe_trigger_exploration_combat(
                    event_name=name,
                    event=event,
                    ctx=ctx,
                    result=result,
                )
            except Exception:
                logger.debug(
                    "Nie udało się rozstrzygnąć triggera walki po akcji eksploracyjnej '%s'.",
                    name,
                    exc_info=True,
                )
        return result
    finally:
        if game is not None:
            try:
                next_depth = int(getattr(game, "_event_dispatch_depth", 1) or 1) - 1
            except Exception:
                next_depth = 0
            if next_depth > 0:
                setattr(game, "_event_dispatch_depth", next_depth)
            else:
                try:
                    delattr(game, "_event_dispatch_depth")
                except Exception:
                    pass
                try:
                    delattr(game, "_exploration_combat_triggered_in_dispatch")
                except Exception:
                    pass


def iter_event_names() -> Iterable[str]:
    for name in _registry:
        yield name
