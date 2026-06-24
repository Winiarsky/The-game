from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional, Tuple


class BonusType(str, Enum):
    """Typy bonusów/kar (na razie dwie kategorie, łatwo rozszerzyć)."""

    CIRCUMSTANCE = "circumstance"
    STATUS = "status"
    ITEM = "item"


@dataclass(frozen=True)
class BonusEffect:
    """Pojedynczy bonus lub kara odnosząca się do danego tagu akcji."""

    type: BonusType
    value: int
    tag: str  # np. "attack_melee", "attack_range", "stealth", "ac"
    source: Optional[str] = None  # identyfikacja źródła (status, wydarzenie, efekt)
    target_id: Optional[str] = None  # opcjonalne zawężenie do konkretnego celu
    label: Optional[str] = None  # czytelna nazwa do promptu/UI
    is_penalty: bool = False  # kara (True) lub bonus (False)
    duration_turns: Optional[int] = None  # ile własnych tur pozostaje (None = bez limitu)

    @property
    def signed_value(self) -> int:
        return -self.value if self.is_penalty else self.value

    def matches(self, tag: str, target_id: Optional[str]) -> bool:
        if self.tag != tag:
            return False
        if self.target_id is None:
            return True
        return self.target_id == target_id


def _best_bonus_penalty(effects: Iterable[BonusEffect]) -> Tuple[int, int, list[BonusEffect], list[BonusEffect]]:
    """Zwraca (naj_bonus, naj_kara, bonusy, kary) z listy efektów."""
    bonuses: list[BonusEffect] = []
    penalties: list[BonusEffect] = []
    for eff in effects:
        if eff.is_penalty or eff.value < 0:
            penalties.append(eff)
        else:
            bonuses.append(eff)
    best_bonus = max((e.value for e in bonuses), default=0)
    best_penalty = max((abs(e.value) for e in penalties), default=0)
    return best_bonus, best_penalty, bonuses, penalties


def aggregate_best_by_type(
    effects: Iterable[BonusEffect], tag: str, target_id: Optional[str] = None
) -> dict[BonusType, dict[str, object]]:
    """
    Grupuje efekty po typie i wybiera najlepszy bonus i karę na dany tag/target.
    Zwraca mapę BonusType -> {"bonus": int, "penalty": int, "bonuses": [...], "penalties": [...]}.
    """
    grouped: dict[BonusType, list[BonusEffect]] = {}
    for eff in effects:
        if not eff.matches(tag, target_id):
            continue
        grouped.setdefault(eff.type, []).append(eff)

    result: dict[BonusType, dict[str, object]] = {}
    for btype, items in grouped.items():
        best_bonus, best_penalty, bonuses, penalties = _best_bonus_penalty(items)
        result[btype] = {
            "bonus": best_bonus,
            "penalty": best_penalty,
            "bonuses": bonuses,
            "penalties": penalties,
        }
    return result


def compute_total_modifier(effects: Iterable[BonusEffect], tag: str, target_id: Optional[str] = None) -> int:
    """Suma najlepszych bonusów minus suma najlepszych kar z każdej kategorii."""
    aggregated = aggregate_best_by_type(effects, tag, target_id)
    total_bonus = sum(data["bonus"] for data in aggregated.values())
    total_penalty = sum(data["penalty"] for data in aggregated.values())
    return int(total_bonus - total_penalty)


def _effect_is_penalty(effect: BonusEffect) -> bool:
    return bool(effect.is_penalty or effect.value < 0)


def _effect_label(effect: BonusEffect) -> str:
    return effect.label or effect.source or effect.tag or "mod"


def select_best_effects(
    effects: Iterable[BonusEffect], tag: str, target_id: Optional[str] = None
) -> list[BonusEffect]:
    """Wybierz po 1 najwyższym bonusie i karze na typ dla danego tagu/targetu."""
    filtered = [eff for eff in effects if eff.matches(tag, target_id)]
    if not filtered:
        return []
    result: list[BonusEffect] = []
    grouped: dict[BonusType, list[BonusEffect]] = {}
    for eff in filtered:
        grouped.setdefault(eff.type, []).append(eff)
    for btype, items in grouped.items():
        bonuses = [e for e in items if not _effect_is_penalty(e)]
        penalties = [e for e in items if _effect_is_penalty(e)]
        if bonuses:
            best_bonus = max(bonuses, key=lambda e: e.value)
            result.append(best_bonus)
        if penalties:
            best_penalty = max(penalties, key=lambda e: abs(e.value))
            result.append(best_penalty)
    return result


def format_effects_log(
    effects: Iterable[BonusEffect], tag: str, target_id: Optional[str] = None
) -> list[str]:
    """Zwróć listę unikalnych linii do logu (grupowanie po typie/znaku/wartości)."""
    filtered = [eff for eff in effects if eff.matches(tag, target_id)]
    if not filtered:
        return []
    groups: dict[tuple[BonusType, bool, int], set[str]] = {}
    for eff in filtered:
        is_penalty = _effect_is_penalty(eff)
        value = abs(int(getattr(eff, "value", 0) or 0))
        if value == 0:
            continue
        key = (eff.type, is_penalty, value)
        groups.setdefault(key, set()).add(_effect_label(eff))
    ordered_types = list(BonusType)
    lines: list[str] = []
    for btype in ordered_types:
        for is_penalty in (False, True):
            for (t, pen, value), labels in groups.items():
                if t != btype or pen != is_penalty:
                    continue
                sign = "-" if is_penalty else "+"
                label_txt = ", ".join(sorted(labels))
                lines.append(f"{sign}{value} {btype.value} ({label_txt})")
    return lines


def build_modifiers_grid(effects: Iterable[BonusEffect]) -> dict:
    """Przygotuj dane do sekcji premii/kar w UI (najlepsze per typ)."""
    buckets = {
        "penCirc": [],
        "bonCirc": [],
        "penStat": [],
        "bonStat": [],
        "penItem": [],
        "bonItem": [],
    }
    for eff in effects:
        value = getattr(eff, "value", 0) or 0
        if not value:
            continue
        label = _effect_label(eff)
        btype = getattr(eff, "type", None)
        is_penalty = _effect_is_penalty(eff)
        if btype == BonusType.CIRCUMSTANCE:
            key = "penCirc" if is_penalty else "bonCirc"
        elif btype == BonusType.STATUS:
            key = "penStat" if is_penalty else "bonStat"
        elif btype == BonusType.ITEM:
            key = "penItem" if is_penalty else "bonItem"
        else:
            key = "penCirc" if is_penalty else "bonCirc"
        buckets[key].append({"label": label, "value": value})
    for key, arr in buckets.items():
        arr.sort(key=lambda x: abs(x.get("value", 0)), reverse=True)
    return buckets
