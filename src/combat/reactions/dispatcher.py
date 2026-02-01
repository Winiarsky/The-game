from __future__ import annotations

import logging
from typing import Iterable

logger = logging.getLogger(__name__)


def _in_reach(board, reactor, target_pos) -> bool:
    reach = getattr(reactor, "reach", 1) or 1
    pos = getattr(reactor, "position", None)
    if pos is None or target_pos is None:
        return False
    cx, cy = pos
    tx, ty = target_pos
    dx, dy = abs(cx - tx), abs(cy - ty)
    return max(dx, dy) <= reach


def iter_reactors(game) -> Iterable[object]:
    """Zwróć wszystkich aktorów zdolnych do reakcji (heroes + enemies) z reactions_left>0."""
    for actor in list(getattr(game, "heroes", [])) + list(getattr(game, "enemies", [])):
        if getattr(actor, "reactions_left", 0) <= 0:
            continue
        reactions = getattr(actor, "reactions", [])
        if reactions:
            yield actor


def dispatch_reactions(game, event: dict[str, object]) -> None:
    """Obsługa reakcji dla zdarzenia. Wrogowie reagują automatycznie, bohaterowie przez prompt."""
    state = getattr(game, "state", None)
    if getattr(getattr(state, "__class__", None), "__name__", "") != "Combat":
        return

    actor = event.get("actor")
    target_pos = getattr(actor, "position", None)
    board = getattr(game, "board", None)
    if board is None:
        return

    heroes = list(getattr(game, "heroes", []))
    enemies = list(getattr(game, "enemies", []))
    actor_side = "hero" if actor in heroes else "enemy" if actor in enemies else None

    for reactor in iter_reactors(game):
        if reactor is actor:
            continue
        # tylko przeciwna strona
        if actor_side == "hero" and reactor in heroes:
            continue
        if actor_side == "enemy" and reactor in enemies:
            continue
        if not _in_reach(board, reactor, target_pos):
            continue
        for reaction in list(getattr(reactor, "reactions", [])):
            try:
                if not reaction.triggers(reactor, event):
                    continue
            except Exception as exc:
                logger.error("Błąd w triggers %s: %s", reaction.id, exc)
                continue

            # bohaterowie: zapytaj; wrogowie: auto
            if reactor in getattr(game, "heroes", []):
                prompt_fn = getattr(game, "ui", None)
                reason = reaction.reason(reactor, event)
                consent = False
                if prompt_fn and getattr(prompt_fn, "enabled", False):
                    try:
                        choice = game.ui.prompt_choice(
                            f"Czy chcesz wykonać reakcję {reaction.label}? ({reason})",
                            choices=["tak", "nie"],
                            source="reaction",
                        )
                        consent = str(choice or "").strip().lower().startswith("t")
                    except Exception as exc:
                        logger.error("Prompt reakcji nie powiódł się: %s", exc)
                else:
                    try:
                        resp = input(f"Reakcja {reaction.label} ({reason}). Wykonać? [t/N]: ")
                        consent = resp.strip().lower() in ("t", "tak", "y", "yes")
                    except Exception:
                        consent = False
                if not consent:
                    continue

            try:
                executed = reaction.execute(reactor, event, ctx=type("Ctx", (), {"game": game, "event": event})())
                if executed and hasattr(reactor, "consume_reaction"):
                    reactor.consume_reaction()
            except Exception as exc:
                logger.error("Błąd wykonania reakcji %s: %s", reaction.id, exc)
