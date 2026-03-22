import json
import copy
import sys
from pathlib import Path
import logging
import os
import time
from collections import deque
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
from GameObjects.Enemies.basic_enemy import BasicEnemy
from GameObjects.Enemies.simple_enemy import Enemy
from GameObjects.Obstacles.basic_obstacle import Obstacle
from GameObjects.Terrains.basic_terrain import BasicTerrain
from GameObjects.Walls.basic_wall import Wall, Mur
from board_grid import BoardGrid
from object_registry import OBJECT_REGISTRY, get_object
from ui_client import UndoRequested, get_ui_client
from debug_trace import DebugTrace
from ui_payloads import build_active_actor_payload, build_hero_snapshot

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
        self.debug_trace: DebugTrace | None = None
        self._init_debug_trace(scenario)
        from action_events import ActionEventBus
        self.events = ActionEventBus(self)
        self._attach_debug_event_listener()
        self.heroes: list[Hero] = []
        self.enemies: list[BasicEnemy] = []
        self.board = self._init_board()
        self.state: State = Start(self)
        self._init_debug_undo()
        self._install_ui_prompt_trace_hooks()
        

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
            # Scal default_config z configiem instancji:
            # - defaulty zapewniają pełną konfigurację obiektu (np. inventory handlarza),
            # - wpisy instancji nadpisują tylko to, co scenariusz chce zmienić.
            effective_cfg: dict[str, Any] = dict(default_cfg or {})
            if isinstance(cfg, dict):
                effective_cfg.update(cfg)
            try:
                return cls(**effective_cfg)
            except TypeError as exc:
                logger.error("Nie udało się utworzyć %s z configiem %s: %s", cls.__name__, effective_cfg, exc)
                try:
                    return cls()
                except Exception:
                    return None

        def _place_enemy(obj, pos):
            board.place(obj, pos)
            self.enemies.append(obj)

        from GameObjects.interactions_mixin.base_interaction import InteractableMixin

        handlers: list[tuple[type, callable]] = [
            (BasicTerrain, lambda obj, pos: board.set_field(pos, obj)),
            (Obstacle, lambda obj, pos: board.place(obj, pos)),
            (InteractableMixin, lambda obj, pos: board.add_interactable(obj, pos)),
            (BasicEnemy, _place_enemy),
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
        t0 = time.perf_counter()
        self._capture_undo_snapshot(action_name)
        if self.debug_trace is not None:
            self.debug_trace.write(
                "run_action_start",
                action_name=action_name,
                state_before=current_state.__class__.__name__,
                args=args,
                kwargs=kwargs,
            )
        try:
            result: Any = action(*args, **kwargs)
        except UndoRequested as undo_exc:
            restored = self.undo_last_action(reason=f"prompt:{undo_exc.command}")
            if self.debug_trace is not None:
                self.debug_trace.write(
                    "run_action_undo",
                    action_name=action_name,
                    command=undo_exc.command,
                    restored=bool(restored),
                    duration_ms=round((time.perf_counter() - t0) * 1000, 3),
                    snapshot=self.debug_trace.snapshot_game(self),
                )
            if not restored:
                self.ui_log("Debug: brak snapshotu do cofnięcia.", level="warning", tag="Debug")
            return None
        except Exception as exc:
            if self.debug_trace is not None:
                self.debug_trace.write_exception(
                    "run_action",
                    exc,
                    action_name=action_name,
                    state_before=current_state.__class__.__name__,
                    duration_ms=round((time.perf_counter() - t0) * 1000, 3),
                    snapshot=self.debug_trace.snapshot_game(self),
                )
            raise
        self._cleanup_defeated_enemies_after_action(source=f"action:{action_name}")

        # Jeśli stan został zmieniony w trakcie akcji (np. trigger combat), nie nadpisuj go wynikiem.
        if self.state is not current_state:
            logger.debug("Stan zmienił się w trakcie akcji (%s -> %s); pomijam wynik %s.",
                         current_state.__class__.__name__, self.state.__class__.__name__, result)
            if self.debug_trace is not None:
                self.debug_trace.write(
                    "run_action_end",
                    action_name=action_name,
                    duration_ms=round((time.perf_counter() - t0) * 1000, 3),
                    state_before=current_state.__class__.__name__,
                    state_after=self.state.__class__.__name__,
                    state_changed=True,
                    result=result,
                    snapshot=self.debug_trace.snapshot_game(self),
                )
            return result

        if isinstance(result, State) and result is not self.state:
            self.state.on_exit()
            self.state = result.set_context(self)
            self.state.on_enter()

        if self.debug_trace is not None:
            self.debug_trace.write(
                "run_action_end",
                action_name=action_name,
                duration_ms=round((time.perf_counter() - t0) * 1000, 3),
                state_before=current_state.__class__.__name__,
                state_after=self.state.__class__.__name__,
                state_changed=self.state is not current_state,
                result=result,
                snapshot=self.debug_trace.snapshot_game(self),
            )
        return result

    def find_object(self, object_id: str):
        """Szybkie wyszukiwanie obiektu po jego globalnym id."""
        return get_object(object_id)

    def _cleanup_defeated_enemies_after_action(self, *, source: str) -> None:
        try:
            from combat.damage_utils import cleanup_defeated_enemies

            cleanup_defeated_enemies(self, source=source)
        except Exception:
            return

    def start_combat(self, trigger: object | None = None) -> None:
        """Wejście w stan walki (ignorowane, jeśli już walczymy)."""
        if isinstance(self.state, Combat):
            logger.info("Walka już trwa – ignoruję wywołanie.")
            return
        if not self._has_combat_ready_enemies():
            logger.info("Brak żywych przeciwników na planszy – pomijam wejście w walkę.")
            return
        if not isinstance(self.state, State):
            logger.error("Brak aktywnego stanu – nie mogę rozpocząć walki.")
            return
        self.state.on_exit()
        self.state = Combat(self)
        self.state.on_enter()

    @staticmethod
    def _is_enemy_combat_ready(enemy: object) -> bool:
        """Zwraca True dla przeciwnika, który realnie może rozpocząć walkę."""
        if enemy is None:
            return False
        if getattr(enemy, "position", None) is None:
            return False
        try:
            if int(getattr(enemy, "hp", 1) or 0) <= 0:
                return False
        except Exception:
            pass
        has_status = getattr(enemy, "has_status", None)
        if callable(has_status):
            try:
                if bool(has_status("dead")):
                    return False
            except Exception:
                pass
        return True

    def _has_combat_ready_enemies(self) -> bool:
        return any(self._is_enemy_combat_ready(enemy) for enemy in getattr(self, "enemies", []) or [])

    # --- UI helpery ---
    def ui_event(self, event_type: str, payload: dict[str, Any]) -> bool:
        """Bezpieczne wysyłanie eventów do UI (ignoruje brak UI)."""
        if self.debug_trace is not None:
            self.debug_trace.write("ui_event", ui_event_type=event_type, payload=payload)
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
        if self.debug_trace is not None:
            self.debug_trace.write(
                "ui_log",
                message=message,
                level=level,
                tag=tag,
                image=image,
            )
        payload: dict[str, Any] = {"message": message}
        if level:
            payload["level"] = level
        if tag:
            payload["tag"] = tag
        if image:
            payload["image"] = image
        self.ui_event("log", payload)

    def ui_hero(self, hero: Hero, note: str | None = None) -> None:
        self.ui_event("hero_snapshot", build_hero_snapshot(hero, note=note))

    def ui_active_actor(self, actor: Any | None) -> None:
        self.ui_event(
            "active_actor_changed",
            build_active_actor_payload(
                actor,
                heroes=getattr(self, "heroes", []),
                enemies=getattr(self, "enemies", []),
            ),
        )

    def ui_idle_hint(self, title: str, text: str | None = None) -> None:
        """Wyślij wskazówkę do UI dla stanu bez aktywnego promptu."""
        payload: dict[str, Any] = {"title": title}
        if text:
            payload["text"] = text
        self.ui_event("idle_hint", payload)

    # --- Debug undo ---
    def _init_debug_undo(self) -> None:
        enabled = str(os.environ.get("GAME_DEBUG_UNDO", "1")).strip().lower() not in {"0", "false", "no"}
        limit_raw = str(os.environ.get("GAME_DEBUG_UNDO_LIMIT", "60")).strip()
        try:
            limit = max(1, int(limit_raw))
        except Exception:
            limit = 60
        self._debug_undo_enabled = bool(enabled)
        self._debug_undo_limit = int(limit)
        self._debug_undo_stack: deque[dict[str, Any]] = deque(maxlen=self._debug_undo_limit)

    def _capture_undo_snapshot(self, action_name: str) -> None:
        if not bool(getattr(self, "_debug_undo_enabled", False)):
            return
        try:
            state_payload = {
                "state_class": self.state.__class__,
                "state_data": {
                    key: value
                    for key, value in dict(getattr(self.state, "__dict__", {}) or {}).items()
                    if key != "game"
                },
                "heroes": list(self.heroes),
                "enemies": list(self.enemies),
                "board": self.board,
            }
            cloned = copy.deepcopy(state_payload)
            self._debug_undo_stack.append(
                {
                    "action_name": str(action_name),
                    "created_at": time.time(),
                    "state": cloned,
                }
            )
            if self.debug_trace is not None:
                self.debug_trace.write(
                    "undo_snapshot_saved",
                    action_name=action_name,
                    stack_size=len(self._debug_undo_stack),
                )
        except Exception as exc:
            logger.debug("Nie udało się zapisać snapshotu undo: %s", exc, exc_info=True)

    def undo_last_action(self, *, reason: str | None = None) -> bool:
        if not bool(getattr(self, "_debug_undo_enabled", False)):
            return False
        stack = getattr(self, "_debug_undo_stack", None)
        if not stack:
            return False
        try:
            entry = stack.pop()
        except Exception:
            return False
        state_blob = entry.get("state") if isinstance(entry, dict) else None
        if not isinstance(state_blob, dict):
            return False
        try:
            state_class = state_blob.get("state_class")
            state_data = dict(state_blob.get("state_data") or {})
            heroes = list(state_blob.get("heroes") or [])
            enemies = list(state_blob.get("enemies") or [])
            board = state_blob.get("board")
            if state_class is None or board is None:
                return False

            self.heroes = heroes
            self.enemies = enemies
            self.board = board

            restored_state = state_class(self).set_context(self)
            restored_state.__dict__.update(state_data)
            restored_state.set_context(self)
            self.state = restored_state
            self._rebuild_object_registry_after_undo()

            self._refresh_ui_after_undo(entry)
            if self.debug_trace is not None:
                self.debug_trace.write(
                    "undo_applied",
                    action_name=entry.get("action_name"),
                    reason=reason,
                    stack_size=len(self._debug_undo_stack),
                    snapshot=self.debug_trace.snapshot_game(self),
                )
            return True
        except Exception as exc:
            logger.debug("Undo restore failed: %s", exc, exc_info=True)
            return False

    def _refresh_ui_after_undo(self, entry: dict[str, Any]) -> None:
        action_name = str(entry.get("action_name") or "?")
        self.ui_log(f"Debug: cofnięto stan o 1 akcję (przed: {action_name}).", tag="Debug")
        for hero in list(getattr(self, "heroes", []) or []):
            try:
                self.ui_hero(hero, note="Debug rollback")
            except Exception:
                continue
        active_actor = None
        current_actor_fn = getattr(self.state, "_current_actor", None)
        if callable(current_actor_fn):
            try:
                active_actor = current_actor_fn()
            except Exception:
                active_actor = None
        if active_actor is None:
            active_actor = getattr(self.state, "active_hero", None) or getattr(self.state, "active_actor", None)
        self.ui_active_actor(active_actor)
        initiative_fn = getattr(self.state, "_send_initiative_event", None)
        if callable(initiative_fn):
            try:
                initiative_fn()
            except Exception:
                pass
        state_name = self.state.__class__.__name__
        self.ui_idle_hint("Debug rollback", f"Stan przywrócony. Aktualny stan: {state_name}.")

    def _rebuild_object_registry_after_undo(self) -> None:
        try:
            OBJECT_REGISTRY.clear()
        except Exception:
            return

        def _register(obj: Any) -> None:
            oid = str(getattr(obj, "object_id", "") or "").strip()
            if not oid:
                return
            try:
                OBJECT_REGISTRY.register(obj, oid)
            except Exception:
                pass

        for actor in list(getattr(self, "heroes", []) or []) + list(getattr(self, "enemies", []) or []):
            _register(actor)

        board = getattr(self, "board", None)
        if board is None:
            return
        rows = int(getattr(board, "rows", 0) or 0)
        cols = int(getattr(board, "cols", 0) or 0)
        for row in range(rows):
            for col in range(cols):
                pos = (col, row)
                try:
                    cell = board.cell_at(pos)
                except Exception:
                    continue
                _register(getattr(cell, "field", None))
                _register(getattr(cell, "occupant", None))
                for interactable in list(getattr(cell, "interactables", []) or []):
                    _register(interactable)
        for objects in list(getattr(board, "edge_interactables", {}).values() or []):
            for obj in list(objects or []):
                _register(obj)
        for wall in list(getattr(board, "walls", {}).values() or []):
            _register(wall)

    # --- Debug trace ---
    def _init_debug_trace(self, scenario: str) -> None:
        enabled = str(os.environ.get("GAME_DEBUG_TRACE", "1")).strip().lower() not in {"0", "false", "no"}
        if not enabled:
            self.debug_trace = None
            return
        try:
            trace_dir_raw = str(os.environ.get("GAME_DEBUG_TRACE_DIR", "")).strip()
            trace_dir = Path(trace_dir_raw) if trace_dir_raw else (PROJECT_ROOT / "data" / "debug_sessions")
            self.debug_trace = DebugTrace(trace_dir)
            self.debug_trace.write(
                "session_start",
                scenario=scenario,
                cwd=str(PROJECT_ROOT),
            )
            self.ui_event(
                "info",
                {
                    "message": f"Sesja debug: {self.debug_trace.session_id}",
                    "source": "debug",
                },
            )
            self.ui_log(f"Sesja debug: {self.debug_trace.session_id}", tag="Debug")
        except Exception as exc:
            logger.debug("Nie udało się zainicjalizować DebugTrace: %s", exc, exc_info=True)
            self.debug_trace = None

    @staticmethod
    def _trace_actor_ref(obj: Any) -> dict[str, Any] | None:
        if obj is None:
            return None
        return {
            "id": getattr(obj, "object_id", None) or getattr(obj, "name", None) or str(obj),
            "name": getattr(obj, "name", None),
            "pos": getattr(obj, "position", None),
            "kind": getattr(obj, "__class__", type("", (), {})).__name__,
        }

    def _attach_debug_event_listener(self) -> None:
        if self.debug_trace is None:
            return

        def _listener(event: dict[str, Any]) -> None:
            try:
                safe_event = dict(event)
                for key in ("actor", "target"):
                    if key in safe_event:
                        safe_event[key] = self._trace_actor_ref(safe_event[key])
                self.debug_trace.write("action_bus_event", event=safe_event)
            except Exception:
                logger.debug("DebugTrace: błąd listenera eventów.", exc_info=True)

        try:
            self.events.add_listener(_listener)
        except Exception:
            logger.debug("Nie udało się podpiąć listenera DebugTrace.", exc_info=True)

    def _install_ui_prompt_trace_hooks(self) -> None:
        if self.debug_trace is None:
            return
        ui = getattr(self, "ui", None)
        if ui is None:
            return
        if bool(getattr(ui, "_debug_trace_wrapped", False)):
            return

        methods = (
            "prompt_roll",
            "prompt_choice",
            "prompt_info",
            "prompt_file_image",
            "prompt_action_select",
        )

        for method_name in methods:
            original = getattr(ui, method_name, None)
            if not callable(original):
                continue

            def _make_wrapper(orig_fn, meth: str):
                def _wrapped(*args, **kwargs):
                    started = time.perf_counter()
                    prompt = args[0] if args else kwargs.get("prompt") or kwargs.get("title")
                    if self.debug_trace is not None:
                        self.debug_trace.write(
                            "prompt_start",
                            method=meth,
                            prompt=prompt,
                            kwargs=kwargs,
                        )
                    try:
                        answer = orig_fn(*args, **kwargs)
                    except Exception as exc:
                        if self.debug_trace is not None:
                            self.debug_trace.write_exception(
                                f"ui.{meth}",
                                exc,
                                prompt=prompt,
                                duration_ms=round((time.perf_counter() - started) * 1000, 3),
                            )
                        raise
                    if self.debug_trace is not None:
                        self.debug_trace.write(
                            "prompt_answer",
                            method=meth,
                            prompt=prompt,
                            answer=answer,
                            duration_ms=round((time.perf_counter() - started) * 1000, 3),
                        )
                    return answer

                return _wrapped

            try:
                setattr(ui, method_name, _make_wrapper(original, method_name))
            except Exception:
                logger.debug("DebugTrace: nie udało się owinąć %s.", method_name, exc_info=True)

        try:
            setattr(ui, "_debug_trace_wrapped", True)
        except Exception:
            pass
