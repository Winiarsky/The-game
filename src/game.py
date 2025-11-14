import json
import sys
from pathlib import Path
import logging
from typing import Any
from player import Player

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from board import Connection
from states import Start, State

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Game:
    def __init__(self):
        with open('src/arduino/led_positions.json', 'r') as led_file:
            self.led_positions = json.load(led_file)
        with open('src/scenarios/scenario_1.json', 'r') as scenario_file:
            self.scenario = json.load(scenario_file)
        self.conn: Connection | None = None
        self.players: list[Player] = []
        self.state: State = Start(self)
    
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
