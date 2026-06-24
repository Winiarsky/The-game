from __future__ import annotations


_VALID_CATEGORIES = {"light", "medium", "heavy"}
_VALID_GROUPS = {"cloth", "leather", "chain", "composite", "plate"}

_GROUP_LABELS_PL: dict[str, str] = {
    "cloth": "materialowy",
    "leather": "skorzany",
    "chain": "lancuchowy",
    "composite": "kompozytowy",
    "plate": "plytowy",
}

_SPECIALIZATION_RULES: dict[str, dict[str, tuple[str, int]]] = {
    "chain": {
        "medium": ("critical_physical", 4),
        "heavy": ("critical_physical", 6),
    },
    "composite": {
        "medium": ("piercing_resistance", 1),
        "heavy": ("piercing_resistance", 2),
    },
    "leather": {
        "medium": ("bludgeoning_resistance", 1),
        "heavy": ("bludgeoning_resistance", 2),
    },
    "plate": {
        "medium": ("slashing_resistance", 1),
        "heavy": ("slashing_resistance", 2),
    },
}


def normalize_armor_category(value: object) -> str:
    raw = str(value or "").strip().lower()
    return raw if raw in _VALID_CATEGORIES else "light"


def normalize_armor_group(value: object) -> str:
    raw = str(value or "").strip().lower()
    return raw if raw in _VALID_GROUPS else "cloth"


def armor_group_label_pl(value: object) -> str:
    group = normalize_armor_group(value)
    return _GROUP_LABELS_PL.get(group, group)


def armor_potency_rune_value(armor) -> int:
    if armor is None:
        return 0

    candidates: list[object] = [
        getattr(armor, "potency_rune", None),
        getattr(armor, "potency_rune_value", None),
        getattr(armor, "armor_potency_rune", None),
        getattr(armor, "potency", None),
    ]
    runes = getattr(armor, "runes", None)
    if isinstance(runes, dict):
        candidates.append(runes.get("potency"))
    if isinstance(runes, (list, tuple)):
        for item in runes:
            if isinstance(item, dict):
                candidates.append(item.get("potency"))
            else:
                text = str(item or "").strip().lower()
                if text.startswith("potency"):
                    pieces = text.split(":")
                    if len(pieces) > 1:
                        candidates.append(pieces[-1])
    for raw in candidates:
        try:
            value = int(raw or 0)
        except Exception:
            continue
        if value > 0:
            return value
    return 0


def armor_specialization_rule(*, armor_group: object, armor_category: object, potency: int = 0) -> dict[str, object]:
    group = normalize_armor_group(armor_group)
    category = normalize_armor_category(armor_category)
    value = max(0, int(potency or 0))
    rule = _SPECIALIZATION_RULES.get(group, {}).get(category)
    if not rule:
        return {
            "enabled": False,
            "group": group,
            "category": category,
            "kind": "",
            "amount": 0,
        }
    kind, base_amount = rule
    return {
        "enabled": True,
        "group": group,
        "category": category,
        "kind": kind,
        "amount": int(base_amount + value),
    }


def armor_specialization_description_pl(*, armor_group: object, armor_category: object) -> str:
    group = normalize_armor_group(armor_group)
    category = normalize_armor_category(armor_category)
    rule = armor_specialization_rule(armor_group=group, armor_category=category, potency=0)
    if not bool(rule.get("enabled")):
        return "Brak efektu specjalizacji dla tej kategorii pancerza."

    kind = str(rule.get("kind", "") or "")
    amount = int(rule.get("amount", 0) or 0)
    if kind == "critical_physical":
        return (
            f"Na trafieniu krytycznym redukuje obrazenia fizyczne o {amount} "
            "(+ wartosc runy potencji)."
        )
    if kind == "piercing_resistance":
        return f"Zapewnia odpornosc na obrazenia klute {amount} (+ wartosc runy potencji)."
    if kind == "bludgeoning_resistance":
        return f"Zapewnia odpornosc na obrazenia obuchowe {amount} (+ wartosc runy potencji)."
    if kind == "slashing_resistance":
        return f"Zapewnia odpornosc na obrazenia sieczne {amount} (+ wartosc runy potencji)."
    return "Efekt specjalizacji pancerza."


__all__ = [
    "armor_group_label_pl",
    "armor_potency_rune_value",
    "armor_specialization_description_pl",
    "armor_specialization_rule",
    "normalize_armor_category",
    "normalize_armor_group",
]
