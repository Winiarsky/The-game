from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional, Tuple


class BonusType(str, Enum):
    """Typy bonusów/kar (na razie dwie kategorie, łatwo rozszerzyć)."""

    CIRCUMSTANCE = "circumstance"
    STATUS = "status"


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
