from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from actions.base import ActionContext
from actions.actions_registy import get_action, list_actions
from .base import State


logger = logging.getLogger(__name__)


class HeroesTurn(State):


    def on_enter(self):
        logger.info("Tura bohaterow!")
        self.game.ui_log("Tura bohaterów!")
        self.game.ui_event("initiative", {"round": None, "order": [], "active_id": None})
        self.game.ui_log("Press Enter aby kontynuować turę bohaterów.")

    def on_exit(self):
        logger.info("Koniec tury bohaterow.")
        self.game.ui_log("Koniec tury bohaterów.")

    def choose_action(self) -> State:
        available = list_actions()
        if not available:
            logger.warning("Brak zarejestrowanych akcji.")
            self.game.ui_log("Brak zarejestrowanych akcji.")
            return self

        logger.info("Dostępne akcje: %s", ", ".join(sorted(available)))
        self.game.ui_log(f"Dostępne akcje: {', '.join(sorted(available))}")
        choice = self.game.conn.read_card("Wpisz nazwę akcji: ", list(available.keys())).strip()
        try:
            action = get_action(choice)
        except KeyError:
            logger.error("Nieznana akcja '%s'", choice)
            self.game.ui_log(f"Nieznana akcja '{choice}'")
            return self

        ctx = ActionContext(game=self.game, heroes_turn=self)
        action.execute(ctx)
        return self
    
