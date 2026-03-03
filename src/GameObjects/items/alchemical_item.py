from __future__ import annotations

from dataclasses import dataclass

from .base_item import BaseItem


@dataclass
class AlchemicalItem(BaseItem):
    category: str = "potion"
    event_name: str = ""
    preparation_counter: int = 0
    prepared_by_quick_alchemy: bool = False
    prepared_by_advanced_alchemy: bool = False

    def ui_description(self) -> str:
        ready_note = "Gotowe do użycia."
        if int(self.preparation_counter or 0) > 0:
            ready_note = f"Przygotowanie: {int(self.preparation_counter)} tury do gotowości."
        source_note = "Źródło: standard."
        if bool(self.prepared_by_quick_alchemy):
            source_note = "Źródło: quick_alchemy."
        elif bool(self.prepared_by_advanced_alchemy):
            source_note = "Źródło: advanced_alchemy."
        return f"{self.name}\nEvent: {self.event_name}\n{ready_note}\n{source_note}"


def alchemical_item_name_from_event(event_name: str) -> str:
    return str(event_name or "alchemical_item").replace("_", " ").title()


__all__ = [
    "AlchemicalItem",
    "alchemical_item_name_from_event",
]
