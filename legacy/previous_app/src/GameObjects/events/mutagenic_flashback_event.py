from __future__ import annotations

import logging
from dataclasses import replace

from .base import EventContext, EventResult, GameEvent
from .registry import register_event, get_event_cls
from .elixirs.base_elixir_event import _minutes

logger = logging.getLogger(__name__)


@register_event
class MutagenicFlashbackEvent(GameEvent):
    """Mutagenic Flashback (free action)."""

    name = "mutagenic_flashback"
    consumes_action = False
    available_in_combat = True
    available_in_exploration = True
    default_tags = ["alchemical", "mutagen", "free_action"]

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do użycia Mutagenic Flashback.")

        status = self._get_status(actor, "alchemist_research_field")
        if status is None:
            return EventResult.cancelled(message="Brak Research Field (Mutagenist).")
        data = getattr(status, "data", None) or {}
        if data.get("research_field") != "mutagenist":
            return EventResult.cancelled(message="Research Field nie jest Mutagenist.")
        if data.get("mutagenic_flashback_used"):
            return EventResult.cancelled(message="Mutagenic Flashback zużyty dziś.")

        consumed = list(data.get("mutagen_consumed", []) or [])
        if not consumed:
            return EventResult.cancelled(message="Brak wypitych mutagenów do wyboru.")

        label_map: dict[str, dict] = {}
        for entry in consumed:
            name = str(entry.get("name", "") or "")
            tier = str(entry.get("tier", "") or "")
            label = f"{name.replace('_', ' ').title()} ({tier})"
            label_map[label] = entry

        choice = self._prompt_choice(list(label_map.keys()))
        if not choice:
            return EventResult.cancelled(message="Nie wybrano mutagenu.")

        entry = label_map.get(choice)
        if not entry:
            return EventResult.cancelled(message="Nie wybrano poprawnego mutagenu.")

        mutagen_name = str(entry.get("name", "") or "")
        tier = str(entry.get("tier", "") or "")
        try:
            event_cls = get_event_cls(mutagen_name)
        except Exception as exc:
            logger.warning("Nie znaleziono mutagenu '%s': %s", mutagen_name, exc)
            return EventResult.cancelled(message="Nie znaleziono mutagenu.")

        event = event_cls()
        tier_data = dict(getattr(event, "tiers", {}).get(tier, {}) or {})
        if not tier_data:
            return EventResult.cancelled(message="Brak danych dla wybranego poziomu mutagenu.")
        tier_data["duration"] = _minutes(1)

        try:
            event._apply_elixir(ctx, actor, tier, tier_data)  # type: ignore[attr-defined]
        except Exception as exc:
            logger.warning("Nie udało się nałożyć mutagenu: %s", exc)
            return EventResult.cancelled(message="Nie udało się nałożyć mutagenu.")

        new_data = dict(data)
        new_data["mutagenic_flashback_used"] = True
        self._replace_status_data(actor, "alchemist_research_field", new_data)
        return EventResult(success=True, consumed_action=False, message="Mutagenic Flashback aktywne.")

    def _prompt_choice(self, choices: list[str]) -> str | None:
        try:
            from ui_client import get_ui_client

            ui = get_ui_client()
            if ui.enabled:
                return ui.prompt_choice(
                    "Mutagenic Flashback: wybierz mutagen",
                    choices=choices,
                    source="mutagenic_flashback",
                )
        except Exception:
            pass
        return None

    @staticmethod
    def _get_status(target, status_id: str):
        getter = getattr(target, "get_status", None)
        if callable(getter):
            try:
                return getter(status_id)
            except Exception:
                return None
        for status in getattr(target, "statuses", []) or []:
            if getattr(status, "id", None) == status_id:
                return status
        return None

    @staticmethod
    def _replace_status_data(target, status_id: str, new_data: dict) -> bool:
        statuses = getattr(target, "statuses", None)
        if not isinstance(statuses, list):
            return False
        for idx, status in enumerate(statuses):
            if getattr(status, "id", None) == status_id:
                try:
                    statuses[idx] = replace(status, data=new_data)
                    return True
                except Exception:
                    return False
        return False
