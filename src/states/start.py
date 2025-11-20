from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from board import Connection, consts
from hero import Hero

from .base import State
from .heroes_turns import HeroesTurn


logger = logging.getLogger(__name__)


class Start(State):
    
    def welcome_message(self):
        logger.info("Witamy w grze planszowej!")
        
    def connect_to_board(self):
        conn = Connection()
        if conn is not None:
            logger.info("Connected to board.")
            self.game.conn = conn
            return conn
        logger.error("Failed to connect to board.")
        raise ConnectionError("Could not connect to board.")

    def set_heroes_starting_positions(
        self,
        conn: Connection,
        starting_positions: list[tuple[int, int]],
    ):
        heroes: list[Hero] = self.game.heroes
        while True:

            response = conn.read_card(
                "Skanuj karte ACCEPT by ustawic figurke na polu startowym, lub DECLINE by zakonczyc setup",
                ["ACCEPT", "DECLINE"],
            )
            if response.upper() == "DECLINE":
                logger.info("Setup graczy zakonczony.")
                break
            if response.upper() == "ACCEPT":
                logger.info("Ustaw figurke swojego bohatera na wolnym polu startowym.")
            conn.set_leds(starting_positions, consts.MOVE_FIELD_RGB) # usunac pozycje zajete
            logger.info("Odczytuje polozenie figurki...")
            pos = conn.scan_board(starting_positions) # dodac check na zajetosc pola
            conn.leds_off()
            hero = Hero()
            hero.set_position(pos)
            heroes.append(hero)
            logger.info(
                f"Bohater ustawiony na pozycji {pos}."
            )
        self.game.heroes = heroes
        return HeroesTurn(self.game)
