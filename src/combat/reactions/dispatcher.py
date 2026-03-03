from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Iterable

from combat.hp_engine import current_hp as hp_current_hp

logger = logging.getLogger(__name__)


def _actor_id(actor) -> str:
    if actor is None:
        return ""
    return getattr(actor, "object_id", None) or getattr(actor, "name", None) or str(id(actor))


def _in_reach(reactor, target_pos) -> bool:
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


def _is_alive(actor, game) -> bool:
    if actor is None:
        return False
    if getattr(actor, "position", None) is None:
        return False
    if hasattr(actor, "is_dead"):
        try:
            if bool(actor.is_dead()):
                return False
        except Exception:
            pass
    hp = hp_current_hp(actor)
    if hp is not None and int(hp) <= 0:
        return False
    return True


def _initiative_score(state, actor) -> int:
    calc = getattr(state, "_effective_initiative", None)
    if callable(calc):
        try:
            return int(calc(actor))
        except Exception:
            pass
    mapping = getattr(state, "temp_initiative", None)
    if isinstance(mapping, dict) and actor in mapping:
        try:
            return int(mapping[actor])
        except Exception:
            pass
    mapping = getattr(state, "base_initiative", None)
    if isinstance(mapping, dict) and actor in mapping:
        try:
            return int(mapping[actor])
        except Exception:
            pass
    try:
        return int(getattr(actor, "initiative", 0) or 0)
    except Exception:
        return 0


def _event_uid(event: dict[str, object]) -> str | None:
    raw = event.get("event_uid") or event.get("reaction_event_uid")
    if raw is None:
        return None
    return str(raw)


@dataclass
class _Candidate:
    reactor: object
    reaction: object
    priority: int
    initiative: int
    tie_key: str
    dedupe_key: tuple[object, ...]
    local_key: tuple[str, str]


def dispatch_reactions(game, event: dict[str, object]) -> None:
    """Obsługa reakcji dla zdarzenia. Wrogowie reagują automatycznie, bohaterowie przez prompt."""
    state = getattr(game, "state", None)
    if getattr(getattr(state, "__class__", None), "__name__", "") != "Combat":
        return
    event_payload = dict(event)
    event_payload.setdefault("game", game)
    can_pay_action = getattr(state, "can_pay_reaction_action_cost", None)
    consume_action = getattr(state, "consume_reaction_action_cost", None)

    actor = event_payload.get("actor")
    if not _is_alive(actor, game):
        return
    target = event_payload.get("target")
    if target is not None and not _is_alive(target, game):
        return

    heroes = list(getattr(game, "heroes", []))
    enemies = list(getattr(game, "enemies", []))
    actor_side = "hero" if actor in heroes else "enemy" if actor in enemies else None
    event_uid = _event_uid(event_payload)
    global_history = getattr(state, "_reaction_resolution_keys", None)
    if global_history is None:
        global_history = set()
        try:
            setattr(state, "_reaction_resolution_keys", global_history)
        except Exception:
            pass

    def _has_status(actor, status_id: str) -> bool:
        statuses = getattr(actor, "statuses", None)
        if hasattr(actor, "has_status"):
            try:
                return bool(actor.has_status(status_id))  # type: ignore[arg-type]
            except Exception:
                pass
        if isinstance(statuses, list):
            return any(getattr(s, "id", s) == status_id for s in statuses)
        return False

    candidates: list[_Candidate] = []
    for reactor in iter_reactors(game):
        if reactor is actor:
            continue
        if not _is_alive(reactor, game):
            continue
        # tylko przeciwna strona
        if actor_side == "hero" and reactor in heroes:
            continue
        if actor_side == "enemy" and reactor in enemies:
            continue
        for reaction in list(getattr(reactor, "reactions", [])):
            blocks_range_attacker = bool(getattr(reaction, "blocks_range_attacker", True))
            if blocks_range_attacker and _has_status(reactor, "range_attacker"):
                continue
            needs_reach = bool(getattr(reaction, "requires_reach", True))
            target_pos = getattr(actor, "position", None)
            if needs_reach and not _in_reach(reactor, target_pos):
                continue
            try:
                if not reaction.triggers(reactor, event_payload):
                    continue
            except Exception as exc:
                logger.error("Błąd w triggers %s: %s", reaction.id, exc)
                continue
            cost = getattr(reaction, "action_cost", 1)
            try:
                cost = max(1, int(cost))
            except Exception:
                cost = 1
            if callable(can_pay_action):
                try:
                    if not bool(can_pay_action(reactor, cost=cost)):
                        continue
                except Exception:
                    continue
            reaction_id = str(getattr(reaction, "id", "reaction"))
            reactor_key = _actor_id(reactor)
            if event_uid is not None:
                event_key: object = event_uid
            else:
                # Brak stabilnego UID = deduplikacja tylko dla pojedynczego wywołania dispatch.
                event_key = ("dispatch", id(event_payload))
            dedupe_key = (event_key, reactor_key, reaction_id)
            if dedupe_key in global_history:
                continue
            try:
                priority = int(getattr(reaction, "priority", 0) or 0)
            except Exception:
                priority = 0
            candidates.append(
                _Candidate(
                    reactor=reactor,
                    reaction=reaction,
                    priority=priority,
                    initiative=_initiative_score(state, reactor),
                    tie_key=reactor_key,
                    dedupe_key=dedupe_key,
                    local_key=(reactor_key, reaction_id),
                )
            )

    candidates.sort(key=lambda item: (-item.priority, -item.initiative, item.tie_key, item.local_key[1]))
    seen_in_dispatch: set[tuple[str, str]] = set()

    for candidate in candidates:
        reactor = candidate.reactor
        reaction = candidate.reaction
        if candidate.local_key in seen_in_dispatch:
            continue
        if candidate.dedupe_key in global_history:
            continue
        if not _is_alive(reactor, game) or getattr(reactor, "reactions_left", 0) <= 0:
            continue
        cost = getattr(reaction, "action_cost", 1)
        try:
            cost = max(1, int(cost))
        except Exception:
            cost = 1
        if callable(can_pay_action):
            try:
                if not bool(can_pay_action(reactor, cost=cost)):
                    continue
            except Exception:
                continue

        # bohaterowie: zapytaj; wrogowie: auto
        if reactor in heroes:
            prompt_fn = getattr(game, "ui", None)
            reason = reaction.reason(reactor, event_payload)
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
                if getattr(getattr(game, "ui", None), "allow_cli_fallback", False) is False:
                    continue
                try:
                    resp = input(f"Reakcja {reaction.label} ({reason}). Wykonać? [t/N]: ")
                    consent = resp.strip().lower() in ("t", "tak", "y", "yes")
                except Exception:
                    consent = False
            if not consent:
                continue

        try:
            executed = reaction.execute(
                reactor,
                event_payload,
                ctx=type("Ctx", (), {"game": game, "event": event_payload})(),
            )
            if not executed:
                continue
            seen_in_dispatch.add(candidate.local_key)
            global_history.add(candidate.dedupe_key)
            if hasattr(reactor, "consume_reaction"):
                reactor.consume_reaction()
            if callable(consume_action):
                consume_action(reactor, cost=cost, reason=getattr(reaction, "label", "Reakcja"))
        except Exception as exc:
            logger.error("Błąd wykonania reakcji %s: %s", getattr(reaction, "id", "reaction"), exc)
