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

    def on_exit(self):
        logger.info("Koniec tury bohaterow.")

    def choose_action(self) -> State:
        available = list_actions()
        if not available:
            logger.warning("Brak zarejestrowanych akcji.")
            return self

        logger.info("Dostępne akcje: %s", ", ".join(sorted(available)))
        choice = input("Wpisz nazwę akcji: ").strip()
        try:
            action = get_action(choice)
        except KeyError:
            logger.error("Nieznana akcja '%s'", choice)
            return self

        ctx = ActionContext(game=self.game, heroes_turn=self)
        action.execute(ctx)
        return self
