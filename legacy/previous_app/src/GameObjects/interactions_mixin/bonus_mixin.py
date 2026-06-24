from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

from bonuses import BonusEffect, BonusType, aggregate_best_by_type, compute_total_modifier


@dataclass
class BonusMixin:
    """Przechowuje i agreguje bonusy/kary dla akcji (hero/enemy)."""

    bonuses: list[BonusEffect] = field(default_factory=list)

    # --- modyfikacja listy ---
    def add_bonus(self, effect: BonusEffect) -> None:
        """Dodaj efekt bez deduplikacji (różne źródła mogą współistnieć)."""
        self.bonuses.append(effect)

    def remove_bonuses_by_source(self, source: str) -> int:
        """Usuń bonusy z podanego źródła, zwróć liczbę usuniętych."""
        removed = 0
        new_list: list[BonusEffect] = []
        for eff in self.bonuses:
            if eff.source == source:
                removed += 1
                continue
            new_list.append(eff)
        self.bonuses = new_list
        return removed

    def remove_bonuses_with_prefix(self, prefix: str) -> int:
        """Pomocnicze do czyszczenia efektów przejściowych (np. flankowanie)."""
        removed = 0
        new_list: list[BonusEffect] = []
        for eff in self.bonuses:
            if eff.source and eff.source.startswith(prefix):
                removed += 1
                continue
            new_list.append(eff)
        self.bonuses = new_list
        return removed

    # --- odczyt/obliczenia ---
    def effects_for(self, tag: str, target: Optional[object] = None) -> list[BonusEffect]:
        target_id = getattr(target, "object_id", None)
        return [eff for eff in self.bonuses if eff.matches(tag, target_id)]

    def best_by_type(self, tag: str, target: Optional[object] = None):
        target_id = getattr(target, "object_id", None)
        return aggregate_best_by_type(self.bonuses, tag, target_id)

    def compute_modifier(self, tag: str, target: Optional[object] = None) -> int:
        target_id = getattr(target, "object_id", None)
        return compute_total_modifier(self.bonuses, tag, target_id)

    def tick_bonuses_turn(self) -> None:
        """Zdekrementuj liczniki duration_turns i usuń wygasłe efekty."""
        if not self.bonuses:
            return
        remaining: list[BonusEffect] = []
        for eff in self.bonuses:
            if eff.duration_turns is None:
                remaining.append(eff)
                continue
            turns = eff.duration_turns - 1
            if turns > 0:
                remaining.append(
                    BonusEffect(
                        type=eff.type,
                        value=eff.value,
                        tag=eff.tag,
                        source=eff.source,
                        target_id=eff.target_id,
                        label=eff.label,
                        is_penalty=eff.is_penalty,
                        duration_turns=turns,
                    )
                )
        self.bonuses = remaining

    def format_prompt(self, tag: str, target: Optional[object] = None) -> str:
        """Opis bonusów/kar do wyświetlenia w promptcie (z wyróżnieniem najwyższych)."""
        target_id = getattr(target, "object_id", None)
        aggregated = aggregate_best_by_type(self.bonuses, tag, target_id)
        if not aggregated:
            return ""

        lines: list[str] = []
        for btype, data in aggregated.items():
            bonus = data["bonus"]
            penalty = data["penalty"]
            bonuses: Iterable[BonusEffect] = data["bonuses"]  # type: ignore[assignment]
            penalties: Iterable[BonusEffect] = data["penalties"]  # type: ignore[assignment]

            def _fmt(eff: BonusEffect, is_best: bool) -> str:
                sign = "-" if eff.is_penalty or eff.value < 0 else "+"
                val = eff.value
                label = eff.label or eff.source or ""
                mark = "*" if is_best else " "
                return f"{mark}{sign}{val} {label}".strip()

            best_bonus_line = None
            if bonus:
                for eff in bonuses:
                    if eff.value == bonus:
                        best_bonus_line = _fmt(eff, True)
                        break
            other_bonus_lines = [_fmt(eff, False) for eff in bonuses if bonus and eff.value != bonus]

            best_penalty_line = None
            if penalty:
                for eff in penalties:
                    if abs(eff.value) == penalty:
                        best_penalty_line = _fmt(eff, True)
                        break
            other_penalty_lines = [_fmt(eff, False) for eff in penalties if penalty and abs(eff.value) != penalty]

            header = f"{btype.value.capitalize()}:"
            lines.append(header)
            if best_bonus_line:
                lines.append(f"  {best_bonus_line} (najwyższy bonus)")
            for line in other_bonus_lines:
                lines.append(f"  {line}")
            if best_penalty_line:
                lines.append(f"  {best_penalty_line} (największa kara)")
            for line in other_penalty_lines:
                lines.append(f"  {line}")

        lines.append("(*) – użyj najwyższego bonusu i największej kary z każdej kategorii.")
        return "\n".join(lines)
