from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game import Game


class State:
    """Bazowa klasa stanów pozwalająca na dostęp do kontekstu gry."""

    def __init__(self, game: "Game"):
        self.game = game

    def set_context(self, game: "Game") -> "State":
        """Podmieniamy kontekst gdy stan jest ponownie używany."""
        self.game = game
        return self

    def on_enter(self):
        return None

    def on_exit(self):
        return None
