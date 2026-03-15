from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Iterable

from combat.hp_engine import current_hp as hp_current_hp

logger = logging.getLogger(__name__)


def _normalize(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


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


def _reaction_policy_state(actor) -> dict[str, set[str]]:
    raw = getattr(actor, "reaction_policy_state", None)
    if isinstance(raw, dict):
        auto_accept = set(str(item) for item in list(raw.get("auto_accept", set()) or set()))
        skip_until_turn_end = set(str(item) for item in list(raw.get("skip_until_turn_end", set()) or set()))
        state = {
            "auto_accept": auto_accept,
            "skip_until_turn_end": skip_until_turn_end,
        }
    else:
        state = {
            "auto_accept": set(),
            "skip_until_turn_end": set(),
        }
    try:
        setattr(actor, "reaction_policy_state", state)
    except Exception:
        pass
    return state


def clear_turn_reaction_policies(actor) -> None:
    state = _reaction_policy_state(actor)
    state["skip_until_turn_end"] = set()
    try:
        setattr(actor, "reaction_policy_state", state)
    except Exception:
        pass


def _reaction_trigger_key(reaction, reactor, event_payload: dict[str, object]) -> str:
    trigger_key_fn = getattr(reaction, "trigger_key", None)
    if callable(trigger_key_fn):
        try:
            value = _normalize(trigger_key_fn(reactor, event_payload))
            if value:
                return value
        except Exception:
            pass
    reaction_id = _normalize(getattr(reaction, "id", "reaction"))
    tags = [_normalize(item) for item in list(event_payload.get("action_tags") or []) if _normalize(item)]
    if tags:
        return f"{reaction_id}:{tags[0]}"
    action_id = _normalize(event_payload.get("action_id"))
    if action_id:
        return f"{reaction_id}:{action_id}"
    return reaction_id or "reaction"


def _reaction_decision(choice: str | None) -> str:
    normalized = _normalize(choice)
    if normalized in {"tak", "t", "y", "yes", "1", "react_now", "react"}:
        return "react_now"
    if normalized in {"skip_now", "nie", "n", "no", "2"}:
        return "skip_now"
    if normalized in {"auto_for_trigger", "auto", "3"}:
        return "auto_for_trigger"
    if normalized in {"pass_trigger_until_turn_end", "pass_until_turn_end", "pass", "4"}:
        return "pass_trigger_until_turn_end"
    return "skip_now"


@dataclass
class _Candidate:
    reactor: object
    reaction: object
    priority: int
    initiative: int
    tie_key: str
    dedupe_key: tuple[object, ...]
    local_key: tuple[str, str]
    trigger_key: str


def dispatch_reactions(game, event: dict[str, object]) -> None:
    """Obsługa reakcji dla zdarzenia. Wrogowie reagują automatycznie, bohaterowie przez prompt."""
    state = getattr(game, "state", None)
    if getattr(getattr(state, "__class__", None), "__name__", "") != "Combat":
        return
    event_payload = event
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
            trigger_key = _reaction_trigger_key(reaction, reactor, event_payload)
            candidates.append(
                _Candidate(
                    reactor=reactor,
                    reaction=reaction,
                    priority=priority,
                    initiative=_initiative_score(state, reactor),
                    tie_key=reactor_key,
                    dedupe_key=dedupe_key,
                    local_key=(reactor_key, reaction_id),
                    trigger_key=trigger_key,
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
            policy = _reaction_policy_state(reactor)
            trigger_key = str(candidate.trigger_key or "")
            if trigger_key and trigger_key in policy.get("skip_until_turn_end", set()):
                continue
            if trigger_key and trigger_key in policy.get("auto_accept", set()):
                consent = True
            else:
                prompt_fn = getattr(game, "ui", None)
                reason = reaction.reason(reactor, event_payload)
                consent = False
                prompt_text_fn = getattr(reaction, "prompt_text", None)
                if callable(prompt_text_fn):
                    try:
                        prompt_text = str(prompt_text_fn(reactor, event_payload) or "").strip()
                    except Exception:
                        prompt_text = ""
                else:
                    prompt_text = ""
                if not prompt_text:
                    prompt_text = f"Czy chcesz wykonać reakcję {reaction.label}? ({reason})"
                if prompt_fn and getattr(prompt_fn, "enabled", False):
                    try:
                        choice = game.ui.prompt_choice(
                            prompt_text,
                            choices=[
                                "react_now",
                                "skip_now",
                                "auto_for_trigger",
                                "pass_trigger_until_turn_end",
                            ],
                            source="reaction",
                        )
                        decision = _reaction_decision(str(choice or ""))
                        if decision == "auto_for_trigger" and trigger_key:
                            policy.setdefault("auto_accept", set()).add(trigger_key)
                            consent = True
                        elif decision == "pass_trigger_until_turn_end" and trigger_key:
                            policy.setdefault("skip_until_turn_end", set()).add(trigger_key)
                            consent = False
                        else:
                            consent = decision == "react_now"
                    except Exception as exc:
                        logger.error("Prompt reakcji nie powiódł się: %s", exc)
                else:
                    if getattr(getattr(game, "ui", None), "allow_cli_fallback", False) is False:
                        continue
                    try:
                        resp = input(
                            f"{prompt_text} [t=react, n=skip, a=auto trigger, p=pass do końca tury]: "
                        )
                        decision = _reaction_decision(resp)
                        if decision == "auto_for_trigger" and trigger_key:
                            policy.setdefault("auto_accept", set()).add(trigger_key)
                            consent = True
                        elif decision == "pass_trigger_until_turn_end" and trigger_key:
                            policy.setdefault("skip_until_turn_end", set()).add(trigger_key)
                            consent = False
                        else:
                            consent = decision == "react_now"
                    except Exception:
                        consent = False
                try:
                    setattr(reactor, "reaction_policy_state", policy)
                except Exception:
                    pass
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
