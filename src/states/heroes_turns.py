from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from .base import State

from GameObjects.events import EventContext
from GameObjects.events.registry import dispatch_event, list_events
import GameObjects.events.all_events  # noqa: F401  # rejestruj eventy
from board import consts

logger = logging.getLogger(__name__)


class HeroesTurn(State):
    def __init__(self, game):
        super().__init__(game)
        self.active_hero = None

    def on_enter(self):
        logger.info("Tura bohaterow!")
        self.game.ui_log("Tura bohaterów!")
        self.game.ui_event("initiative", {"round": None, "order": [], "active_id": None})
        ui_active_actor = getattr(self.game, "ui_active_actor", None)
        if callable(ui_active_actor):
            ui_active_actor(None)
        ui_idle_hint = getattr(self.game, "ui_idle_hint", None)
        if callable(ui_idle_hint):
            ui_idle_hint("Tura bohaterów", "Wybierz bohatera i akcję.")

    def on_exit(self):
        logger.info("Koniec tury bohaterow.")
        self.game.ui_log("Koniec tury bohaterów.")

    def _choose_active_hero(self):
        heroes_positions = [hero.position for hero in self.game.heroes if hero.position is not None]
        if not heroes_positions:
            logger.warning("Brak bohaterów na planszy.")
            self.game.ui_log("Brak bohaterów na planszy.")
            return None
        self.game.conn.set_leds(heroes_positions, consts.HERO_HIGHLIGHT_RGB)
        pos = self.game.conn.scan_board(heroes_positions)
        self.game.conn.leds_off()
        hero = self.game.board.occupant_at(pos)
        return hero

    def choose_action(self) -> State:
        all_events = list_events()
        available_events = {
            name: cls for name, cls in all_events.items() if getattr(cls, "available_in_exploration", True)
        }
        if not available_events:
            logger.warning("Brak zarejestrowanych eventów dla eksploracji.")
            self.game.ui_log("Brak akcji do wykonania.")
            return self

        # wybierz aktywnego bohatera tylko jeśli jeszcze nie ma
        if self.active_hero is None or getattr(self.active_hero, "position", None) is None:
            hero = self._choose_active_hero()
            if hero is None:
                return self
            self.active_hero = hero
        hero = self.active_hero
        ui_active_actor = getattr(self.game, "ui_active_actor", None)
        if callable(ui_active_actor):
            ui_active_actor(hero)

        # podświetl aktywnego bohatera podczas wyboru akcji
        highlighted = False
        try:
            pos = getattr(hero, "position", None)
            if pos is not None:
                self.game.conn.set_leds([pos], consts.HERO_HIGHLIGHT_RGB)
                highlighted = True
        except Exception:
            pass

        # Nie logujemy listy akcji – nazwy są na fizycznych kartach.
        choice = self.game.conn.read_card("Nazwa akcji (wpisz): ", []).strip().lower()

        if highlighted:
            try:
                self.game.conn.leds_off()
            except Exception:
                pass

        if choice not in available_events:
            logger.error("Nieznana akcja '%s'", choice)
            self.game.ui_log(f"Nieznana akcja '{choice}'")
            return self

        ctx = EventContext(game=self.game, actor=hero)
        result = dispatch_event(choice, ctx)
        if result.message:
            self.game.ui_log(result.message)
        else:
            status = "powiodła się" if result.success else "nie powiodła się"
            self.game.ui_log(f"Akcja '{choice}' {status}.")
        if choice == "end" and result.success:
            self.active_hero = None  # wymuś wybór kolejnego bohatera
        return self
    
