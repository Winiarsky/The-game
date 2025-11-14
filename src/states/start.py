from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from board import Connection, consts
from hero import Hero
from player import Player

from .base import State
from .players_turn import PlayersTurn


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

    def set_players(
        self,
        conn: Connection,
        starting_positions: list[tuple[int, int]],
    ):
        players: list[Player] = self.game.players
        while True:
            logger.info("Aktywuj gracza...")
            player_id = conn.read_card(
                "Zeskanuj karte gracza lub ACCEPT by skonczyc setup",
                ["ACCEPT", "player1", "player2", "player3", "player4"],
            )
            if player_id.upper() == "ACCEPT":
                logger.info("Setup graczy zakonczony.")
                break
            active_player = Player(player_id)
            if active_player in players:
                logger.warning(f"Ustawic ponownie figurke gracza {player_id}?")
                decision = conn.read_card(
                    "Skanuj karte ACCEPT by ustawic ponownie, lub DECLINE by pominac",
                    ["ACCEPT", "DECLINE"],
                )
                if decision.upper() == "DECLINE":
                    logger.info(
                        f"Pominieto ustawienie figurki gracza {player_id}."
                    )
                    continue
                if decision.upper() == "ACCEPT":
                    logger.info(f"Ponowny setup gracza {player_id}.")
                    players = [p for p in players if p != active_player]
                    
            logger.info(f"Gracz {player_id} aktywowany.")
            logger.info("Ustaw figurke bohatera na podswietlonym polu startowym")
            conn.set_leds(starting_positions, consts.MOVE_FIELD_RGB)
            logger.info("Odczytuje polozenie figurki...")
            pos = conn.scan_board(starting_positions)
            hero = Hero()
            hero.set_position(pos)
            active_player.assign_hero(hero)
            players.append(active_player)
            logger.info(
                f"Bohater gracza {player_id} ustawiony na pozycji {pos}."
            )
        self.game.players = players
        return PlayersTurn(self.game)
