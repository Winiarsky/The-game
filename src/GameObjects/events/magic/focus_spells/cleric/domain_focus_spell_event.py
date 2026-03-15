from __future__ import annotations

from ....base import EventContext, EventResult
from ....registry import dispatch_event, register_event
from ...magic_event import MagicEvent
from ...spell_types import SpellTradition


def _is_domain_focus_user(actor) -> bool:
    if actor is None:
        return False
    has_status = getattr(actor, "has_status", None)
    if callable(has_status):
        try:
            if bool(has_status("cleric")):
                return True
        except Exception:
            pass
        try:
            if bool(has_status("deitys_domain")):
                return True
        except Exception:
            pass
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", None) in {"cleric", "deitys_domain"}:
            return True
    class_name = str(getattr(actor, "class_name", "") or "").strip().lower()
    return class_name in {"cleric", "champion"}


def _focus_points(actor) -> int:
    raw = getattr(actor, "focus_point", None)
    try:
        return max(0, int(raw or 0))
    except Exception:
        return 0


def _known_domain_spells(actor) -> list[tuple[str, str]]:
    known: list[tuple[str, str]] = []
    for status in getattr(actor, "statuses", []) or []:
        status_id = str(getattr(status, "id", "") or "").strip().lower()
        if status_id not in {"domain_initiate", "deitys_domain"}:
            continue
        data = getattr(status, "data", None) or {}
        domain = str(data.get("selected_domain", "") or "").strip().lower()
        spell = str(data.get("domain_spell", "") or "").strip().lower()
        if not domain or not spell:
            continue
        pair = (domain, spell)
        if pair not in known:
            known.append(pair)
    return known


def _pick_spell(ctx: EventContext, known: list[tuple[str, str]]) -> tuple[str, str] | None:
    if not known:
        return None
    if len(known) == 1:
        return known[0]

    labels = [f"{domain} -> {spell}" for domain, spell in known]
    ui = getattr(ctx.game, "ui", None)
    chooser = getattr(ui, "prompt_choice", None)
    if not callable(chooser):
        return known[0]
    try:
        answer = chooser("Domain Focus Spell: choose known domain spell", choices=labels, source="domain_focus_spell")
    except Exception:
        answer = None
    if answer is None:
        return known[0]
    raw = str(answer).strip()
    for idx, label in enumerate(labels):
        if raw == label:
            return known[idx]
    return known[0]


@register_event
class DomainFocusSpellEvent(MagicEvent):
    name = "domain_focus_spell"
    consumes_action = False
    actions_cost = 1
    default_tags = ["magic", "spell", "focus", "cleric", "champion", "domain"]
    spell_tags = ["focus", "divine", "cleric", "champion", "domain"]
    magic_traditions = (SpellTradition.DIVINE,)
    magic_types = ["focus"]
    prompt = "Choose one of your known domain focus spells and cast it."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Domain Focus Spell: missing actor.")
        if not _is_domain_focus_user(actor):
            return EventResult.cancelled(
                message="Domain Focus Spell: only Cleric or Champion with Deity's Domain can use this action."
            )

        known = _known_domain_spells(actor)
        if not known:
            return EventResult.cancelled(message="Domain Focus Spell: no known domain spells (Domain Initiate).")

        current_focus = _focus_points(actor)
        if current_focus <= 0:
            return EventResult.cancelled(message="Domain Focus Spell: no Focus Point.")

        selection = _pick_spell(ctx, known)
        if selection is None:
            return EventResult.cancelled(message="Domain Focus Spell: spell not selected.")
        _domain, spell = selection

        # Delegate full logic (including Focus Point spend) to the selected domain spell event.
        return dispatch_event(spell, ctx)
