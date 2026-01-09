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
from board_grid import BoardGrid, BasicTerrain
from obstacle import Obstacle
from wall import Wall, Mur
from interactable import Interactable

try:
    from game_objects_loader import scan_game_objects
except Exception:  # pragma: no cover - gdy pakiet nie istnieje
    scan_game_objects = None  # type: ignore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Game:
    def __init__(self, conn: Connection | None = None, scenario: str = "scenario_1"):
        with open('board/led_positions.json', 'r') as led_file:
            self.led_positions = json.load(led_file)
        
        with open(f'scenarios/{scenario}.json', 'r') as scenario_file:
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
        board = BoardGrid(rows, cols)
        scenario = self.scenario

        # Wczytaj obiekty z nowego formatu (objects), a w razie braku z legacy pól.
        if scan_game_objects is not None:
            self._apply_objects(board, scenario)
        else:
            logger.warning("Brak scan_game_objects - używam legacy pól.")
            self._apply_legacy(board, scenario)

        return board

    def _apply_legacy(self, board: BoardGrid, scenario: dict[str, Any]) -> None:
        """Obsługa starego formatu scenariusza."""
        for pos in scenario.get("blocked_fields", []):
            col, row = pos
            board.set_field((col, row), BasicTerrain(name="blocked", walkable=False))

        for pos in scenario.get("obstacles", []):
            try:
                col, row = pos
                board.place(Obstacle(), (col, row))
            except ValueError as exc:
                logger.error("Nie można ustawić przeszkody na %s: %s", pos, exc)

        for wall_data in scenario.get("walls", []):
            try:
                a_raw = tuple(wall_data["a"])
                b_raw = tuple(wall_data["b"])
                a = (a_raw[0], a_raw[1])
                b = (b_raw[0], b_raw[1])
                wall_type = wall_data.get("type", "wall").lower()
                hardness = wall_data.get("hardness")
                features = wall_data.get("features") or {}

                wall_cls = Mur if wall_type == "mur" else Wall
                board.add_wall(a, b, hardness=hardness, features=features, wall_cls=wall_cls)
            except Exception as exc:  # szeroki wyjątek, bo format scenariusza może być błędny
                logger.error("Nie można dodać ściany %s: %s", wall_data, exc)

    def _apply_objects(self, board: BoardGrid, scenario: dict[str, Any]) -> None:
        """Nowy format scenariusza oparty o GameObjects."""
        definitions = scan_game_objects(Path(__file__).resolve().parent / "GameObjects")
        registry = {
            (definition.meta.category, definition.meta.object_id): definition for definition in definitions
        }

        def build_instance(cls, cfg: dict[str, Any] | None):
            if not isinstance(cls, type):
                logger.error("logic_cls %s nie jest klasą", cls)
                return None
            try:
                return cls(**(cfg or {}))
            except TypeError as exc:
                logger.error("Nie udało się utworzyć %s z configiem %s: %s", cls.__name__, cfg, exc)
                try:
                    return cls()
                except Exception:
                    return None

        handlers: list[tuple[type, callable]] = [
            (BasicTerrain, lambda obj, pos: board.set_field(pos, obj)),
            (Obstacle, lambda obj, pos: board.place(obj, pos)),
            (Interactable, lambda obj, pos: board.add_interactable(obj, pos)),
        ]

        def place_logic(logic_cls, pos: tuple[int, int], cfg: dict[str, Any] | None):
            instance = build_instance(logic_cls, cfg)
            if instance is None:
                return
            for base, action in handlers:
                if isinstance(instance, base):
                    action(instance, pos)
                    return
            # fallback gdy nie pasuje do znanych typów – traktuj jako przeszkodę
            try:
                board.place(Obstacle(), pos)
            except Exception as exc:
                logger.error("Fallback obstacle na %s nie powiódł się: %s", pos, exc)

        if not isinstance(scenario.get("objects"), list):
            logger.info("Brak pola objects w scenariuszu - używam legacy pól.")
            self._apply_legacy(board, scenario)
            return

        for obj in scenario.get("objects", []):
            category = obj.get("category")
            object_id = obj.get("object_id")
            definition = registry.get((category, object_id))
            logic_cls = definition.logic_cls if definition else None
            placement = obj.get("placement", "cell")

            if placement == "edge":
                for edge in obj.get("edges", []):
                    try:
                        a_raw = tuple(edge["a"])
                        b_raw = tuple(edge["b"])
                        a = (a_raw[0], a_raw[1])
                        b = (b_raw[0], b_raw[1])
                        wall_cls = logic_cls if isinstance(logic_cls, type) and issubclass(logic_cls, Wall) else Wall
                        board.add_wall(a, b, wall_cls=wall_cls)
                    except Exception as exc:
                        logger.error("Nie można dodać krawędzi %s: %s", edge, exc)
                continue

            if placement == "cell":
                # Nowy format per instancja: {"position":[col,row],"config":{...}}
                for inst in obj.get("instances") or []:
                    raw_pos = inst.get("position") or inst.get("pos")
                    if not raw_pos:
                        continue
                    try:
                        col, row = raw_pos
                        place_logic(logic_cls, (col, row), inst.get("config") or {})
                    except ValueError as exc:
                        logger.error("Pole %s jest zajęte, nie można ustawić %s: %s", raw_pos, object_id, exc)
                    except Exception as exc:
                        logger.error("Nie można ustawić obiektu %s na %s: %s", object_id, raw_pos, exc)

                # Legacy lista pozycji bez konfiguracji.
                for pos in obj.get("positions", []):
                    try:
                        col, row = pos
                        place_logic(logic_cls, (col, row), {})
                    except ValueError as exc:
                        logger.error("Pole %s jest zajęte, nie można ustawić %s: %s", pos, object_id, exc)
                    except Exception as exc:
                        logger.error("Nie można ustawić obiektu %s na %s: %s", object_id, pos, exc)

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
