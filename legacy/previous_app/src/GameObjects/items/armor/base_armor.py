from __future__ import annotations

from dataclasses import dataclass

from GameObjects.items.base_item import BaseItem
from localization import localize_term_pl, localized_hint_pl
from .specialization import (
    armor_group_label_pl,
    armor_specialization_description_pl,
)


_ARMOR_TRAIT_HINTS_PL: dict[str, str] = {
    "comfort": "Wygodny pancerz, bez dodatkowych utrudnien noszenia.",
    "flexible": "Nie stosujesz kary pancerza do testow Acrobatics i Athletics.",
    "noisy": "Kara pancerza do Stealth zawsze obowiazuje (nawet przy spelnionym STR).",
    "bulwark": "W testach Reflex vs efekty obszarowe/obrazenia daje minimum +3 z DEX.",
}


def _trait_key_and_value(trait: object) -> tuple[str, str]:
    text = str(trait or "").strip().lower()
    if ":" in text:
        key, value = text.split(":", 1)
        return key.strip(), value.strip()
    return text, ""


def _labelize_term(value: object) -> str:
    key = str(value or "").strip().lower()
    if not key:
        return ""
    localized = localize_term_pl(key)
    if localized:
        return str(localized)
    return key.replace("_", " ").strip()


def _armor_trait_effect_line(trait: object) -> str:
    key, _value = _trait_key_and_value(trait)
    if not key:
        return "Cecha specjalna pancerza."
    hint = _ARMOR_TRAIT_HINTS_PL.get(key) or localized_hint_pl(key)
    trait_label = _labelize_term(key)
    if hint:
        return f"{trait_label}: {hint}"
    return f"{trait_label}: cecha specjalna pancerza."


@dataclass
class BaseArmor(BaseItem):
    category: str = "armor"
    armor_category: str = "light"
    armor_group: str = "cloth"
    ac_bonus: int = 0
    dex_cap: int = 5
    strength_requirement: int = 10
    check_penalty: int = 0
    speed_penalty_feet: int = 0
    bulwark_reflex_floor: int | None = None

    def ui_description(self) -> str:
        trait_tokens = [str(item).strip() for item in list(self.traits or ()) if str(item).strip()]
        trait_labels = ", ".join(_labelize_term(_trait_key_and_value(item)[0]) for item in trait_tokens) if trait_tokens else "brak"
        trait_effects = [_armor_trait_effect_line(item) for item in trait_tokens]
        speed_penalty = max(0, int(self.speed_penalty_feet or 0))
        check_penalty = max(0, int(self.check_penalty or 0))
        armor_group = str(getattr(self, "armor_group", "cloth") or "cloth")
        specialization_effect = armor_specialization_description_pl(
            armor_group=armor_group,
            armor_category=getattr(self, "armor_category", "light"),
        )
        lines: list[str] = [
            f"{self.name}",
            f"- Kategoria pancerza: {_labelize_term(self.armor_category)}",
            f"- Grupa pancerza: {armor_group_label_pl(armor_group)}",
            f"- Bonus AC: +{int(self.ac_bonus)}",
            f"- Max DEX: +{int(self.dex_cap)}",
            f"- Wymaganie STR: {int(self.strength_requirement)}",
            f"- Kara do testow (STR/DEX, m.in. Stealth): -{check_penalty}",
            f"- Kara do predkosci: -{speed_penalty} ft",
            f"- Specjalizacja pancerza: {specialization_effect}",
        ]
        if self.bulwark_reflex_floor is not None:
            lines.append(f"- Bulwark (minimum Refleks): +{int(self.bulwark_reflex_floor)}")
        lines.extend(
            [
                f"- Cena: {self._price_label(int(getattr(self, 'price_cp', 0) or 0))}",
                f"- Bulk: {self._bulk_label(getattr(self, 'bulk', '-'))}",
                f"- Cechy: {trait_labels}",
            ]
        )
        if trait_effects:
            lines.extend(f"- Dzialanie cechy: {effect}" for effect in trait_effects)
        else:
            lines.append("- Dzialanie cech: Brak dodatkowych efektow cech.")
        return "\n".join(lines)


__all__ = [
    "BaseArmor",
]
