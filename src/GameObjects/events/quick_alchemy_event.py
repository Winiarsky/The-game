from __future__ import annotations

import logging

from GameObjects.items.inventory import add_alchemical_item, item_label

from .base import ActionCostEvent, EventContext, EventResult
from .registry import list_events, register_event

logger = logging.getLogger(__name__)



def _has_status(actor, status_id: str) -> bool:
    if actor is None:
        return False
    checker = getattr(actor, "has_status", None)
    if callable(checker):
        try:
            return bool(checker(status_id))
        except Exception:
            return False
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", status) == status_id:
            return True
    return False


@register_event
class QuickAlchemyEvent(ActionCostEvent):
    name = "quick_alchemy"
    actions_cost = 1
    consumes_action = True
    available_in_combat = True
    available_in_exploration = False
    default_tags = ["alchemical", "manipulate"]

    def pre(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Quick Alchemy: brak aktywnego bohatera.")
        if not _has_status(actor, "quick_alchemy_allow"):
            return EventResult.cancelled(message="Quick Alchemy: wymaga feata quick_alchemy_allow.")
        return super().pre(ctx)

    def _craftable_alchemical_events(self) -> list[str]:
        try:
            from .bombs.base_alchemical_bomb_event import BaseAlchemicalBombEvent
            from .elixirs.base_elixir_event import BaseElixirEvent
            from .poisons.base_poison_event import BasePoisonEvent
        except Exception:
            return []

        base_types = (BaseAlchemicalBombEvent, BaseElixirEvent, BasePoisonEvent)
        result: list[str] = []
        for name, cls in list_events().items():
            try:
                if not issubclass(cls, base_types):
                    continue
            except Exception:
                continue
            if not getattr(cls, "available_in_combat", True):
                continue
            result.append(str(name).strip().lower())
        return sorted(set(result))

    def _show_prompt(self, choices: list[str]) -> None:
        choices_preview = ", ".join(choices[:10])
        if len(choices) > 10:
            choices_preview += ", ..."
        prompt_long = (
            "Wybierz event alchemiczny do stworzenia przez Quick Alchemy.\n"
            "Koszt: 1 składnik alchemiczny (informacja UI, bez walidacji zasobów).\n"
            "Stworzony przedmiot trafia do ekwipunku z przygotowaniem = 1 i będzie gotowy od następnej tury.\n"
            "Wpisz 'end', aby anulować bez kosztu akcji.\n"
            f"Przykładowe eventy: {choices_preview}"
        )
        try:
            from ui_client import get_ui_client

            ui = get_ui_client()
            if ui.enabled:
                ui.prompt_info("Quick Alchemy", prompt_long=prompt_long, source=self.name)
                return
        except Exception:
            pass
        try:
            logger.info(prompt_long)
        except Exception:
            pass

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Quick Alchemy: brak aktywnego bohatera.")

        allowed = self._craftable_alchemical_events()
        if not allowed:
            return EventResult.cancelled(message="Quick Alchemy: brak dostępnych eventów alchemicznych.")

        self._show_prompt(allowed)

        while True:
            raw = ctx.game.conn.read_card(
                "Quick Alchemy: zeskanuj event alchemiczny (end = anuluj)",
                [],
            )
            choice = str(raw or "").strip().lower()
            if not choice:
                try:
                    ctx.game.ui_log("Quick Alchemy: brak wyboru eventu, spróbuj ponownie.")
                except Exception:
                    pass
                continue
            if choice == "end":
                return EventResult.cancelled(message="Quick Alchemy anulowane.")
            if choice not in allowed:
                try:
                    ctx.game.ui_log(f"Quick Alchemy: '{choice}' nie jest poprawnym eventem alchemicznym.")
                except Exception:
                    pass
                continue

            item = add_alchemical_item(
                actor,
                event_name=choice,
                preparation_counter=1,
                prepared_by_quick_alchemy=True,
            )
            label = item_label(item)
            return EventResult(
                success=True,
                consumed_action=self.consumes_action,
                actions_spent=self.actions_cost,
                message=(
                    f"Quick Alchemy: stworzono {label}. "
                    "Przedmiot będzie gotowy od następnej tury."
                ),
                data={"created_event": choice},
            )
