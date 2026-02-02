"""Podstawowe klasy dla nowego sterowania opartego o eventy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class EventContext:
    """Kontekst przekazywany do eventów."""

    game: Any
    actor: Any | None = None
    tags: list[str] | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def in_combat(self) -> bool:
        from states.combat import Combat  # lokalny import by uniknąć cykli

        return isinstance(getattr(self.game, "state", None), Combat)

    @property
    def in_exploration(self) -> bool:
        return not self.in_combat


@dataclass
class EventResult:
    """Standardowy wynik wykonania eventu."""

    success: bool = True
    consumed_action: bool = True
    message: str | None = None
    data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def cancelled(cls, *, message: str | None = None) -> "EventResult":
        return cls(success=False, consumed_action=False, message=message)

    @classmethod
    def noop(cls, *, message: str | None = None) -> "EventResult":
        return cls(success=True, consumed_action=False, message=message)


class GameEvent:
    """Bazowa klasa wszystkich eventów-akcji."""

    # unikalna nazwa karty/eventu
    name: str = "event"
    # domyślne tagi (mogą być rozszerzane przez ctx.tags)
    default_tags: list[str] | None = None
    # dostępność w fazach
    available_in_combat: bool = True
    available_in_exploration: bool = True
    # czy zużywa slot akcji bohatera
    consumes_action: bool = True

    def pre(self, ctx: EventContext) -> EventResult:
        """Hook przed głównym wykonaniem. Zwróć EventResult.cancelled by przerwać."""
        return EventResult()

    def execute(self, ctx: EventContext) -> EventResult:
        """Główna logika eventu."""
        raise NotImplementedError

    def post(self, ctx: EventContext, result: EventResult) -> None:
        """Hook po wykonaniu (nie powinien zmieniać consumed_action)."""
        return None

    # --- helpers ---
    def _effective_tags(self, ctx: EventContext) -> list[str]:
        tags: list[str] = []
        if self.default_tags:
            tags.extend(self.default_tags)
        if ctx.tags:
            tags.extend([t for t in ctx.tags if t not in tags])
        return tags

    def run(self, ctx: EventContext) -> EventResult:
        """Wykonaj pełny lifecycle: pre -> execute -> post."""
        pre_res = self.pre(ctx)
        if not pre_res.success:
            return pre_res
        try:
            result = self.execute(ctx)
        except Exception as exc:  # pragma: no cover - log dla stabilności
            logger.error("Event %s failed: %s", self.name, exc, exc_info=True)
            return EventResult(success=False, consumed_action=False, message=str(exc))
        try:
            self.post(ctx, result)
        except Exception:  # pragma: no cover - nie blokuj dalszych akcji
            logger.debug("Post hook failed for %s", self.name, exc_info=True)
        return result

