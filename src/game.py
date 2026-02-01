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
from states.combat import Combat
from hero import Hero
from GameObjects.Enemies.simple_enemy import Enemy
from GameObjects.Obstacles.basic_obstacle import Obstacle
from GameObjects.Terrains.basic_terrain import BasicTerrain
from GameObjects.Walls.basic_wall import Wall, Mur
from board_grid import BoardGrid
from object_registry import get_object
from ui_client import get_ui_client

try:
    from game_objects_loader import scan_game_objects
except Exception:  # pragma: no cover - gdy pakiet nie istnieje
    scan_game_objects = None  # type: ignore

logging.basicConfig(level=logging.DEBUG)
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
        self.ui = get_ui_client()
        from action_events import ActionEventBus
        self.events = ActionEventBus(self)
        self.heroes: list[Hero] = []
        self.enemies: list[Enemy] = []
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

        self._apply_rooms(board, scenario)
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

        def build_instance(cls, cfg: dict[str, Any] | None, default_cfg: dict[str, Any] | None = None):
            if not isinstance(cls, type):
                logger.error("logic_cls %s nie jest klasą", cls)
                return None
            # użyj default_config obiektu, jeśli brak/empty config
            effective_cfg = cfg if cfg not in (None, {}) else (default_cfg or {})
            try:
                return cls(**effective_cfg)
            except TypeError as exc:
                logger.error("Nie udało się utworzyć %s z configiem %s: %s", cls.__name__, effective_cfg, exc)
                try:
                    return cls()
                except Exception:
                    return None

        from GameObjects.Enemies.simple_enemy import Enemy

        def _place_enemy(obj, pos):
            board.place(obj, pos)
            self.enemies.append(obj)

        from GameObjects.interactions_mixin.base_interaction import InteractableMixin

        handlers: list[tuple[type, callable]] = [
            (BasicTerrain, lambda obj, pos: board.set_field(pos, obj)),
            (Obstacle, lambda obj, pos: board.place(obj, pos)),
            (InteractableMixin, lambda obj, pos: board.add_interactable(obj, pos)),
            (Enemy, _place_enemy),
        ]

        def place_logic(
            logic_cls,
            definition,
            pos: tuple[int, int],
            cfg: dict[str, Any] | None,
        ):
            default_cfg = getattr(definition.meta, "default_config", None) if definition else None
            instance = build_instance(logic_cls, cfg, default_cfg)
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
                        config = edge.get("config") or {}
                        default_cfg = definition.meta.default_config if definition else None
                        if isinstance(logic_cls, type) and issubclass(
                            logic_cls, InteractableMixin  # type: ignore[arg-type]
                        ):
                            instance = build_instance(logic_cls, config, default_cfg)
                            if instance is None:
                                continue
                            board.add_edge_interactable(instance, a, b)
                        else:
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
                        place_logic(logic_cls, definition, (col, row), inst.get("config") or {})
                    except ValueError as exc:
                        logger.error("Pole %s jest zajęte, nie można ustawić %s: %s", raw_pos, object_id, exc)
                    except Exception as exc:
                        logger.error("Nie można ustawić obiektu %s na %s: %s", object_id, raw_pos, exc)

                # Legacy lista pozycji bez konfiguracji.
                for pos in obj.get("positions", []):
                    try:
                        col, row = pos
                        place_logic(logic_cls, definition, (col, row), {})
                    except ValueError as exc:
                        logger.error("Pole %s jest zajęte, nie można ustawić %s: %s", pos, object_id, exc)
                    except Exception as exc:
                        logger.error("Nie można ustawić obiektu %s na %s: %s", object_id, pos, exc)

    def _apply_rooms(self, board: BoardGrid, scenario: dict[str, Any]) -> None:
        """Zastosuj definicje pokoi z scenariusza (wspiera wiele pokoi na polu)."""
        rooms = scenario.get("rooms")
        if isinstance(rooms, list):
            board.apply_rooms(rooms)

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

        current_state = self.state
        result: Any = action(*args, **kwargs)

        # Jeśli stan został zmieniony w trakcie akcji (np. trigger combat), nie nadpisuj go wynikiem.
        if self.state is not current_state:
            logger.debug("Stan zmienił się w trakcie akcji (%s -> %s); pomijam wynik %s.",
                         current_state.__class__.__name__, self.state.__class__.__name__, result)
            return result

        if isinstance(result, State) and result is not self.state:
            self.state.on_exit()
            self.state = result.set_context(self)
            self.state.on_enter()

        return result

    def find_object(self, object_id: str):
        """Szybkie wyszukiwanie obiektu po jego globalnym id."""
        return get_object(object_id)

    def start_combat(self, trigger: object | None = None) -> None:
        """Wejście w stan walki (ignorowane, jeśli już walczymy)."""
        if isinstance(self.state, Combat):
            logger.info("Walka już trwa – ignoruję wywołanie.")
            return
        if not isinstance(self.state, State):
            logger.error("Brak aktywnego stanu – nie mogę rozpocząć walki.")
            return
        self.state.on_exit()
        self.state = Combat(self)
        self.state.on_enter()

    # --- UI helpery ---
    def ui_event(self, event_type: str, payload: dict[str, Any]) -> bool:
        """Bezpieczne wysyłanie eventów do UI (ignoruje brak UI)."""
        try:
            if not getattr(self, "ui", None) or not self.ui.enabled:
                return False
            return bool(self.ui.send_event(event_type, payload))
        except Exception:
            return False

    def ui_log(
        self,
        message: str,
        *,
        level: str | None = None,
        tag: str | None = None,
        image: str | None = None,
    ) -> None:
        """Wyślij komunikat do logów UI (opcjonalnie z levelem, tagiem lub obrazkiem)."""
        payload: dict[str, Any] = {"message": message}
        if level:
            payload["level"] = level
        if tag:
            payload["tag"] = tag
        if image:
            payload["image"] = image
        self.ui_event("log", payload)

    def ui_hero(self, hero: Hero, note: str | None = None) -> None:
        statuses = getattr(hero, "statuses", [])
        if hasattr(hero, "status_labels"):
            try:
                statuses = hero.status_labels()  # type: ignore[attr-defined]
            except Exception:
                statuses = getattr(hero, "statuses", [])
        payload = {
            "name": getattr(hero, "name", None) or getattr(hero, "object_id", "Bohater"),
            "statuses": statuses,
            "note": note,
            "pos": getattr(hero, "position", None),
            "wounds": getattr(hero, "wounds", None),
            "initiative": getattr(hero, "initiative", None),
        }
        self.ui_event("hero", payload)
