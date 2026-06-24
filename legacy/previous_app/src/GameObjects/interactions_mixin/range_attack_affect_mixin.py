from __future__ import annotations

from typing import Literal, Optional


CoverType = Literal["minor", "standard", "greater", "block"]


class RangeAttackAffectMixin:
    """Mixin oznaczający obiekty wpływające na strzały dystansowe."""

    # domyślny typ osłony, nadpisuj w klasach potomnych
    cover_type: CoverType = "standard"
    cover_label: Optional[str] = None

    def range_cover_type(self) -> CoverType:
        return getattr(self, "cover_type", "standard")  # type: ignore[return-value]

    def cover_bonus(self) -> int:
        """Zwróć premię do AC wynikającą z osłony (block -> -1 jako sygnał blokady)."""
        ctype = self.range_cover_type()
        if ctype == "minor":
            return 1
        if ctype == "standard":
            return 2
        if ctype == "greater":
            return 4
        return -1  # blokada
