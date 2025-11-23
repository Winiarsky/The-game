from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from board import consts
from hero import Hero

from .base import State
from .heroes_turns import HeroesTurn


logger = logging.getLogger(__name__)


class Start(State):
    
    def welcome_message(self):
        logger.info("Witamy w grze planszowej!")
        
    def set_heroes_starting_positions(self) -> State:
        heroes: list[Hero] = self.game.heroes
        starting_positions = self.game.scenario['starting_positions']
        logger.info("Ustawianie pozycji startowych bohaterow.")
        while True:
            response = self.game.conn.read_card(
                "Skanuj karte ACCEPT by ustawic figurke na polu startowym, lub DECLINE by zakonczyc setup",
                ["ACCEPT", "DECLINE"],
            )
            if response.upper() == "DECLINE":
                logger.info("Setup graczy zakonczony.")
                break
            if response.upper() == "ACCEPT":
                logger.info("Ustaw figurke swojego bohatera na wolnym polu startowym.")
            self.game.conn.set_leds(starting_positions, consts.MOVE_FIELD_RGB) # usunac pozycje zajete
            logger.info("Odczytuje polozenie figurki...")
            pos = self.game.conn.scan_board(starting_positions)
            self.game.conn.leds_off()
            hero = Hero()
            try:
                self.game.board.place(hero, pos)
            except ValueError as exc:
                logger.error("Nie można ustawić bohatera: %s", exc)
                continue
            heroes.append(hero)
            logger.info(
                f"Bohater ustawiony na pozycji {pos}."
            )
        self.game.heroes = heroes
        return HeroesTurn(self.game)
