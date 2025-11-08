import json
import sys
from pathlib import Path
from enum import Enum, auto
import logging
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from board import Connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class State:
    """Klasa bazowa dla stanów."""
    def on_enter(self):
        return None

    def on_exit(self):
        return None

class Start(State):
    def on_enter(self):
        print("Start gry")
    
    def connect_to_board(self):
        conn = Connection()
        if conn is not None:
            logger.info("Connected to board.")
            return conn
        else:
            logger.error("Failed to connect to board.")
            raise ConnectionError("Could not connect to board.")

class Game:
    def __init__(self):
        self.conn: Connection | None = None
        self.state: State = Start()
    
    def run_state_action(self, action_name: str, *args, **kwargs):
        """Wywołaj akcję stanu i obsłuż ewentualną zmianę stanu."""
        action: Any = getattr(self.state, action_name, None)
        if not callable(action):
            raise AttributeError(
                f"Stan {self.state.__class__.__name__} nie posiada akcji '{action_name}'"
            )

        result: Any = action(*args, **kwargs)

        if isinstance(result, State) and result is not self.state:
            self.state.on_exit()
            self.state = result
            self.state.on_enter()

        return result
