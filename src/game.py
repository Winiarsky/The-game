import json
import sys
from pathlib import Path
import logging
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = Path(__file__).resolve().parent
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from board import Connection
from states import Start, State
from hero import Hero
from board_grid import BoardGrid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Game:
    def __init__(self, conn: Connection | None = None):
        with open('board/led_positions.json', 'r') as led_file:
            self.led_positions = json.load(led_file)
        with open('scenarios/scenario_1.json', 'r') as scenario_file:
            self.scenario = json.load(scenario_file)
        with open('board/config.json', 'r') as config_file:
            self.config = json.load(config_file)
        self.conn: Connection = self._init_connection() if conn is None else conn
        self.heroes: list[Hero] = []
        self.board = self._init_board()
        self.state: State = Start(self)
        

    def _init_board(self) -> BoardGrid:
        rows = self.config['n_rows']
        cols = self.config['n_cols']
        return BoardGrid(rows, cols)

    def _init_connection(self) -> Connection:
        conn = Connection()
        if conn is not None:
            logger.info("Connected to board.")
            return conn
        logger.error("Failed to connect to board.")
        raise ConnectionError("Could not connect to board.")

    def run_action(self, action_name: str, *args, **kwargs):
        """Wywołaj akcję stanu i obsłuż ewentualną zmianę stanu."""
        action: Any = getattr(self.state, action_name, None)
        if not callable(action):
            raise AttributeError(
                f"Stan {self.state.__class__.__name__} nie posiada akcji '{action_name}'"
            )

        result: Any = action(*args, **kwargs)

        if isinstance(result, State) and result is not self.state:
            self.state.on_exit()
            self.state = result.set_context(self)
            self.state.on_enter()

        return result
