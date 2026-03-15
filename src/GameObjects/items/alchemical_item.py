from __future__ import annotations

from dataclasses import dataclass

from .base_item import BaseItem


_ALCHEMICAL_EVENT_ALIASES: dict[str, str] = {
    "acid_flask": "acidflask",
    "lesser_acid_flask": "acidflask",
    "lesser_alchemists_fire": "alchemists_fire",
    "lesser_bottled_lightning": "bottled_lightning",
    "lesser_frost_vial": "frost_vial",
    "lesser_tanglefoot_bag": "tanglefoot_bag",
    "lesser_thunderstone": "thunderstone",
    "lesser_antidote": "antidote",
    "lesser_antiplague": "antiplague",
    "minor_elixir_of_life": "elixir_of_life",
    "lesser_smokestick": "smokestick",
}

_ALCHEMICAL_ITEM_NAMES: dict[str, str] = {
    "acidflask": "Lesser Acid Flask",
    "alchemists_fire": "Lesser Alchemist's Fire",
    "bottled_lightning": "Lesser Bottled Lightning",
    "frost_vial": "Lesser Frost Vial",
    "tanglefoot_bag": "Lesser Tanglefoot Bag",
    "thunderstone": "Lesser Thunderstone",
    "antidote": "Lesser Antidote",
    "antiplague": "Lesser Antiplague",
    "elixir_of_life": "Minor Elixir of Life",
    "smokestick": "Lesser Smokestick",
}

_ALCHEMICAL_ITEM_DEFAULTS: dict[str, dict[str, object]] = {
    key: {"price_cp": 300, "bulk": "L"}
    for key in _ALCHEMICAL_ITEM_NAMES.keys()
}


def normalize_alchemical_event_id(event_name: str | None) -> str:
    raw = str(event_name or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not raw:
        return ""
    return _ALCHEMICAL_EVENT_ALIASES.get(raw, raw)


def alchemical_item_defaults(event_name: str | None) -> dict[str, object]:
    key = normalize_alchemical_event_id(event_name)
    payload = dict(_ALCHEMICAL_ITEM_DEFAULTS.get(key) or {})
    if "bulk" not in payload:
        payload["bulk"] = "L"
    if "price_cp" not in payload:
        payload["price_cp"] = 0
    return payload


@dataclass
class AlchemicalItem(BaseItem):
    category: str = "potion"
    event_name: str = ""
    alchemical_tier: str | None = None
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
        tier_note = ""
        tier = str(getattr(self, "alchemical_tier", "") or "").strip().lower()
        if tier:
            tier_note = f"\nTier: {tier}"
        return f"{self.name}\nEvent: {self.event_name}{tier_note}\n{ready_note}\n{source_note}"


def alchemical_item_name_from_event(event_name: str) -> str:
    key = normalize_alchemical_event_id(event_name)
    if key in _ALCHEMICAL_ITEM_NAMES:
        return str(_ALCHEMICAL_ITEM_NAMES[key])
    return str(key or "alchemical_item").replace("_", " ").title()


def list_alchemical_item_ids() -> list[str]:
    return sorted(_ALCHEMICAL_ITEM_NAMES.keys())


__all__ = [
    "AlchemicalItem",
    "alchemical_item_defaults",
    "alchemical_item_name_from_event",
    "list_alchemical_item_ids",
    "normalize_alchemical_event_id",
]
