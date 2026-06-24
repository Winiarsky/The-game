from __future__ import annotations

from typing import Protocol, Tuple


class LeapBlockerMixin:
    """Mixin oznaczający obiekty blokujące lądowanie akcji leap na danym polu."""

    def blocks_leap(self, _from: Tuple[int, int] | None, to: Tuple[int, int]) -> bool:
        """Zwróć True gdy obiekt ma zablokować skok kończący się na polu `to`."""
        return True

