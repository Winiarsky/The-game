from __future__ import annotations

import logging

from GameObjects.items.inventory import add_alchemical_item, item_label
from localization import localize_term_pl, localized_hint_pl

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

        ui = getattr(ctx.game, "ui", None)
        choice_meta = []
        for idx, event_name in enumerate(allowed, start=1):
            label = localize_term_pl(event_name)
            hint = localized_hint_pl(event_name) or "Przedmiot alchemiczny gotowy do użycia po stworzeniu."
            choice_meta.append(
                {
                    "raw": event_name,
                    "label": label,
                    "desc": f"Quick Alchemy: {hint}",
                    "key": str(idx),
                }
            )
        choice_meta.append(
            {
                "raw": "end",
                "label": "Zakończ",
                "desc": "Anuluj Quick Alchemy bez wyboru eventu.",
                "key": "0",
            }
        )

        while True:
            raw = None
            if ui is not None and hasattr(ui, "prompt_choice"):
                raw = ui.prompt_choice(
                    "Quick Alchemy",
                    choices=[entry["label"] for entry in choice_meta],
                    source=self.name,
                    layout="menu_numpad",
                    title="Quick Alchemy",
                    subtitle="Wybierz event alchemiczny lub zakończ.",
                    choice_meta=choice_meta,
                )
            if raw is None:
                return EventResult.cancelled(message="Quick Alchemy anulowane.")
            choice = str(raw or "").strip().lower()
            if not choice:
                try:
                    ctx.game.ui_log("Quick Alchemy: brak wyboru eventu, spróbuj ponownie.")
                except Exception:
                    pass
                continue
            for entry in choice_meta:
                raw_id = str(entry.get("raw") or "").strip().lower()
                label = str(entry.get("label") or "").strip().lower()
                if choice in {raw_id, label, str(entry.get("key") or "").strip().lower()}:
                    choice = raw_id
                    break
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
            raw_label = str(choice).strip().lower().replace("_", " ")
            return EventResult(
                success=True,
                consumed_action=self.consumes_action,
                actions_spent=self.actions_cost,
                message=(
                    f"Quick Alchemy: stworzono {raw_label} ({label}). "
                    "Przedmiot będzie gotowy od następnej tury."
                ),
                data={"created_event": choice},
            )
