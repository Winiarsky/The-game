"""Lekki autobus zdarzeń akcji.

Każde wykonanie akcji (bohatera lub wroga) powinno emitować event, który mogą
obsłużyć różne słuchacze (reakcje w walce, UI, logi itp.). Ten moduł dostarcza
prosty "event bus" z domyślnymi słuchaczami.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, List, MutableMapping

from narration import narrate_action_event

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
    event_seq: int = 0

    def __post_init__(self) -> None:
        self._register_default_listeners()

    # --- Helper ---
    def safe_emit_action(self, *, return_event: bool = False, **kwargs: Any) -> bool | ActionEvent | None:
        """Emituj akcję, łapiąc wyjątki.

        - domyślnie zwraca ``True``/``False`` (kompatybilność wsteczna),
        - przy ``return_event=True`` zwraca payload eventu (lub ``None`` przy błędzie).
        """
        try:
            event = self.emit_action(**kwargs)
            if return_event:
                return event
            return True
        except Exception:
            logger.debug("safe_emit_action failure", exc_info=True)
            if return_event:
                return None
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
    ) -> ActionEvent:
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
        self.event_seq = int(self.event_seq) + 1
        event.setdefault("event_uid", f"ev:{self.event_seq}")
        event.update(payload)

        for listener in list(self.listeners):
            try:
                listener(event)
            except Exception as exc:  # pragma: no cover - tylko logujemy
                logger.error("ActionEvent listener failed: %s", exc)
        return event

    # --- Domyślne słuchacze ---
    def _register_default_listeners(self) -> None:
        self._register_animal_companion_support_listener()
        self._register_reactions_listener()
        self._register_ui_listener()

    def _register_animal_companion_support_listener(self) -> None:
        try:
            from GameObjects.companions.support_runtime import animal_companion_support_action_listener
        except Exception as exc:  # pragma: no cover - defensywny fallback
            logger.warning("Nie mogę załadować listenera Animal Companion support: %s", exc)
            return

        def _listener(event: ActionEvent) -> None:
            animal_companion_support_action_listener(self.game, event)

        self.add_listener(_listener)

    def _register_reactions_listener(self) -> None:
        try:
            from combat.reactions import dispatch_reactions
        except Exception as exc:  # pragma: no cover - fallback gdy import zawiedzie
            logger.warning("Nie mogę załadować dispatch_reactions: %s", exc)
            return

        def _listener(event: ActionEvent) -> None:
            # dispatcher sam sprawdza stan walki, więc emitujemy zawsze
            dispatch_reactions(self.game, event)

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
            if callable(ui_event):
                try:
                    safe_event = dict(event)
                    for key in ("actor", "target"):
                        if key in safe_event:
                            safe_event[key] = _serialize(safe_event[key])
                    ui_event("action", safe_event)
                except Exception:  # pragma: no cover - logowanie poniżej
                    logger.debug("Nie udało się wysłać eventu akcji do UI", exc_info=True)
            ui_narration = getattr(self.game, "ui_narration", None)
            if callable(ui_narration):
                try:
                    ui_narration(
                        narrate_action_event(dict(event)),
                        summary="Co się dzieje",
                        source=f"action:{event.get('action_id')}",
                        priority="info",
                        semantic_type="status_update",
                        dedupe_key=f"action-start:{event.get('event_uid')}",
                        next_hint="Po zakończeniu tej akcji pojawi się jej efekt.",
                    )
                except Exception:
                    logger.debug("Nie udało się wysłać narracji akcji do UI", exc_info=True)
            refresh_ui = getattr(self.game, "refresh_ui_after_action", None)
            if callable(refresh_ui):
                try:
                    refresh_ui(event)
                except Exception:
                    logger.debug("Nie udało się odświeżyć UI po akcji", exc_info=True)

        self.add_listener(_listener)
