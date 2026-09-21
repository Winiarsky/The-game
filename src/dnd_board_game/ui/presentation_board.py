"""Read-only browser panels temporarily own function keys, never game rules."""
from __future__ import annotations

from typing import TYPE_CHECKING

from dnd_board_game.hardware.board_panel import panel_feedback, panel_position

if TYPE_CHECKING:
    from .exploration_app import BoardScanTarget, ExplorationUiSession
    from dnd_board_game.world import Coordinate

PREFIXES = ("confrontation-detail:", "session-menu:", "session-journal:", "session-help:")


def owns_context(context: str) -> bool:
    return context.startswith(PREFIXES)


def active(session: ExplorationUiSession) -> bool:
    context = session.board_panel_context
    return bool(context and context[2] and owns_context(context[0]))


def validate(session: ExplorationUiSession, context: str, exclusive: bool) -> None:
    if not exclusive:
        raise ValueError("Podgląd musi przejąć przyciski do chwili zamknięcia.")
    if context.startswith("confrontation-detail:"):
        from .confrontation import payload
        current = payload(session)
        if not current or not current.get("active"):
            raise ValueError("Ten podgląd rozmowy nie jest już dostępny.")
        detail = context.rsplit(":", 1)[-1]
        expected = f"confrontation-detail:{current['revision']}:{detail}"
        if (not current.get("active") or context != expected
                or not any(choice["action"] == "inspect" and choice["extra"].get("detail") == detail
                           for choice in current.get("board_choices", ()))):
            raise ValueError("Ten podgląd rozmowy nie jest już dostępny.")


def target(session: ExplorationUiSession) -> BoardScanTarget:
    from .exploration_app import BoardScanTarget
    context = session.board_panel_context
    assert context is not None
    return BoardScanTarget(
        positions=tuple(panel_position(slot) for slot in context[1]),
        feedback=panel_feedback(control_slots=context[1]),
        empty_message="−/+ przegląda. ✓ wybiera, ↩ wraca do gry.",
    )


def select(session: ExplorationUiSession, position: Coordinate) -> dict[str, object]:
    if position not in target(session).positions:
        raise ValueError("Najpierw zamknij bieżący podgląd przyciskiem ↩.")
    assert session.board_panel_context is not None
    session.board_selection_revision += 1
    return {"panel_event": {"slot": 29 - position.row, "context": session.board_panel_context[0]},
            "board_selection": session._board_selection_payload()}
