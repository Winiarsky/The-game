"""Lekki autobus zdarzeń akcji.

Każde wykonanie akcji (bohatera lub wroga) powinno emitować event, który mogą
obsłużyć różne słuchacze (reakcje w walce, UI, logi itp.). Ten moduł dostarcza
prosty "event bus" z domyślnymi słuchaczami.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, List, MutableMapping

logger = logging.getLogger(__name__)

ActionEvent = MutableMapping[str, Any]
ActionListener = Callable[[ActionEvent], None]


def _safe_tags(tags: Iterable[str] | None) -> list[str]:
    if tags is None:
        return []
    return [t for t in tags if t]


@dataclass
class ActionEventBus:
    game: Any
    listeners: List[ActionListener] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._register_default_listeners()

    # --- Helper ---
    def safe_emit_action(self, **kwargs: Any) -> bool:
        """Emituj akcję, łapiąc wyjątki; zwraca True przy sukcesie."""
        try:
            self.emit_action(**kwargs)
            return True
        except Exception:
            logger.debug("safe_emit_action failure", exc_info=True)
            return False

    # --- Public API ---
    def add_listener(self, listener: ActionListener) -> None:
        if listener not in self.listeners:
            self.listeners.append(listener)

    def emit_action(
        self,
        *,
        actor: Any,
        action_id: str,
        action_tags: Iterable[str] | None = None,
        **payload: Any,
    ) -> None:
        """Emituje event akcji do wszystkich słuchaczy.

        Event ma minimalnie: actor, action_id, action_tags, state_name.
        """

        event: ActionEvent = {
            "type": "action",
            "actor": actor,
            "action_id": action_id,
            "action_tags": _safe_tags(action_tags),
            "state": getattr(getattr(self.game, "state", None), "__class__", type("", (), {})).__name__,
        }
        event.update(payload)

        for listener in list(self.listeners):
            try:
                listener(event)
            except Exception as exc:  # pragma: no cover - tylko logujemy
                logger.error("ActionEvent listener failed: %s", exc)

    # --- Domyślne słuchacze ---
    def _register_default_listeners(self) -> None:
        self._register_reactions_listener()
        self._register_ui_listener()

    def _register_reactions_listener(self) -> None:
        try:
            from combat.reactions import dispatch_reactions
        except Exception as exc:  # pragma: no cover - fallback gdy import zawiedzie
            logger.warning("Nie mogę załadować dispatch_reactions: %s", exc)
            return

        def _listener(event: ActionEvent) -> None:
            # dispatcher sam sprawdza stan walki, więc emitujemy zawsze
            dispatch_reactions(self.game, dict(event))

        self.add_listener(_listener)

    def _register_ui_listener(self) -> None:
        def _serialize(obj: Any) -> Any:
            """Zwraca prostą strukturę JSON-safe dla aktora/celu."""
            if obj is None:
                return None
            return {
                "id": getattr(obj, "object_id", None) or getattr(obj, "name", None) or str(obj),
                "name": getattr(obj, "name", None),
                "pos": getattr(obj, "position", None),
                "kind": "hero" if obj in getattr(self.game, "heroes", []) else ("enemy" if obj in getattr(self.game, "enemies", []) else None),
            }

        def _listener(event: ActionEvent) -> None:
            ui_event = getattr(self.game, "ui_event", None)
            ui_log = getattr(self.game, "ui_log", None)
            if callable(ui_event):
                try:
                    safe_event = dict(event)
                    for key in ("actor", "target"):
                        if key in safe_event:
                            safe_event[key] = _serialize(safe_event[key])
                    ui_event("action", safe_event)
                except Exception:  # pragma: no cover - logowanie poniżej
                    logger.debug("Nie udało się wysłać eventu akcji do UI", exc_info=True)
            # prosty wpis do logów UI, by użytkownik widział zdarzenie
            if callable(ui_log):
                try:
                    actor = event.get("actor")
                    actor_name = getattr(actor, "name", None) or getattr(actor, "object_id", None) or "actor"
                    ui_log(
                        f"[akcja] {actor_name}: {event.get('action_id')} {event.get('action_tags')}",
                        tag="action_event",
                    )
                except Exception:
                    logger.debug("Nie udało się zalogować eventu akcji w UI", exc_info=True)

        self.add_listener(_listener)
