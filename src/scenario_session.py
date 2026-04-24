from __future__ import annotations

import copy
import logging
from collections import deque
from dataclasses import dataclass
from typing import Any

from board import consts
from GameObjects.Enemies.basic_enemy import BasicEnemy
from GameObjects.Interactables.entry_anchor import EntryAnchor
from hero import Hero
from states.combat import Combat
from states.encounter_setup import run_setup_batches
from states.heroes_turns import HeroesTurn

from game import Game
from runtime_setup import build_runtime_setup_plan
from narration import NARRATOR_TITLE
from scenario_flow import load_scenario_flow, resolve_map_payload


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MapSnapshot:
    map_id: str
    board: Any
    local_flags: dict[str, Any]


class ScenarioSession:
    """Warstwa orkiestracji dla wielomapowego scenariusza."""

    def __init__(
        self,
        *,
        conn,
        scenario: str,
        flow_payload: dict[str, Any] | None = None,
        preselected_character_ids: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        self.conn = conn
        self.flow = load_scenario_flow(scenario) if flow_payload is None else dict(flow_payload)
        self.scenario_id = str(self.flow.get("scenario_id") or scenario or "scenario_flow")
        self.label = str(self.flow.get("label") or self.scenario_id)
        self.description = str(self.flow.get("description") or "")
        self.maps = {
            str(item["map_id"]): dict(item)
            for item in list(self.flow.get("maps") or [])
        }
        self.transitions = [dict(item) for item in list(self.flow.get("transitions") or [])]
        self.global_flags: dict[str, Any] = dict(self.flow.get("global_flags") or {})
        self.objectives: list[dict[str, Any]] = [dict(item) for item in list(self.flow.get("objectives") or [])]
        self.checkpoint_policy = dict(self.flow.get("checkpoint_policy") or {})
        self.current_map_id = str(self.flow.get("entry_map_id") or "")
        self.current_game: Game | None = None
        self.finished = False
        self.pending_transition: dict[str, Any] | None = None
        self.heroes: list[Hero] = []
        self.map_snapshots: dict[str, MapSnapshot] = {}
        self.map_local_flags: dict[str, dict[str, Any]] = {}
        self.visited_maps: set[str] = set()
        self.completed_objectives: set[str] = set()
        self.triggered_once_events: set[str] = set()
        self.loot_journal: list[dict[str, Any]] = []
        self.checkpoints: list[dict[str, Any]] = []
        self.preselected_character_ids = deque(
            str(item or "").strip().lower()
            for item in (preselected_character_ids or [])
            if str(item or "").strip()
        )
        self._session_announced = False

    @property
    def ui(self):
        return getattr(self.current_game, "ui", None)

    def run_loop(self) -> None:
        self._load_map(self.current_map_id, entry_anchor_id=None, initial_load=True)
        if self.current_game is None:
            raise RuntimeError("Nie udało się uruchomić pierwszej mapy scenariusza.")
        self._run_map_setup(initial_load=True)

        initial_action = getattr(self.current_game.state, "initial_action_name", None) or "set_heroes_starting_positions"
        self.current_game.run_action(initial_action)
        self.heroes = list(getattr(self.current_game, "heroes", []) or [])
        self._prepare_opening_exploration_state()
        self._announce_session_start()
        self._announce_map_entry()
        self.dispatch_trigger("map_start", map_id=self.current_map_id)

        while not self.finished and self.current_game is not None:
            before_state = self.current_game.state.__class__.__name__
            self.current_game.run_action("choose_action")
            self.heroes = list(getattr(self.current_game, "heroes", []) or self.heroes)
            after_state = self.current_game.state.__class__.__name__
            if before_state == "Combat" and after_state != "Combat":
                self.dispatch_trigger("combat_end", map_id=self.current_map_id)
            if self.pending_transition is not None:
                self._apply_pending_transition()
            if getattr(self.current_game, "finished", False) and self.pending_transition is None:
                self.finished = True

    def request_transition(
        self,
        *,
        exit_id: str,
        trigger_type: str,
        source_map_id: str | None,
        actor=None,
        source_object=None,
    ) -> tuple[bool, str]:
        map_id = str(source_map_id or self.current_map_id or "").strip()
        if map_id != self.current_map_id:
            return False, "To przejście nie należy do aktywnej mapy."
        if self.current_game is not None and isinstance(self.current_game.state, Combat):
            return False, "Nie możesz zmienić mapy w trakcie walki."

        has_bound_event = self._has_trigger_binding(trigger_type, map_id=map_id, target_id=exit_id)
        self.dispatch_trigger(
            trigger_type,
            map_id=map_id,
            target_id=exit_id,
            actor=actor,
            source_object=source_object,
        )
        if self.pending_transition is not None or self.finished:
            return True, "Uruchomiono event przejścia."

        transition = self._find_transition(exit_id=exit_id, from_map_id=map_id)
        if transition is None:
            if has_bound_event:
                return False, "To przejście nie jest jeszcze dostępne."
            return False, f"Brak zdefiniowanego przejścia dla exit_id '{exit_id}'."
        if not self._conditions_pass(transition.get("conditions"), map_id=map_id, target_id=exit_id):
            return False, "Przejście jest obecnie zablokowane."
        if self.pending_transition is None:
            self.pending_transition = {
                "transition_id": transition["id"],
                "from_map_id": map_id,
                "to_map_id": transition["to_map_id"],
                "entry_anchor_id": transition["target_entry_anchor_id"],
                "reason": trigger_type,
            }
        return True, f"Przejście do mapy '{self.pending_transition['to_map_id']}' zostało aktywowane."

    def dispatch_trigger(
        self,
        trigger: str,
        *,
        map_id: str | None = None,
        target_id: str | None = None,
        actor=None,
        source_object=None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        normalized_trigger = str(trigger or "").strip().lower()
        current_payload = dict(payload or {})
        for event in list(self.flow.get("events") or []):
            event_id = str(event.get("id") or "").strip()
            if not event_id:
                continue
            if bool(event.get("once")) and event_id in self.triggered_once_events:
                continue
            if str(event.get("trigger") or "").strip().lower() != normalized_trigger:
                continue
            event_map_id = str(event.get("map_id") or "").strip() or None
            event_target_id = str(event.get("target_id") or "").strip() or None
            if event_map_id and event_map_id != str(map_id or self.current_map_id or ""):
                continue
            if event_target_id and event_target_id != str(target_id or ""):
                continue
            if not self._conditions_pass(event.get("conditions"), map_id=map_id, target_id=target_id):
                continue
            self._execute_actions(
                list(event.get("actions") or []),
                trigger=normalized_trigger,
                map_id=map_id,
                target_id=target_id,
                actor=actor,
                source_object=source_object,
                payload=current_payload,
            )
            if bool(event.get("once")):
                self.triggered_once_events.add(event_id)

    def _execute_actions(
        self,
        actions: list[dict[str, Any]],
        *,
        trigger: str,
        map_id: str | None,
        target_id: str | None,
        actor=None,
        source_object=None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        for action in actions:
            kind = str(action.get("type") or "").strip().lower()
            if kind == "set_flag":
                flag = str(action.get("flag") or "").strip()
                value = action.get("value", True)
                self.global_flags[flag] = value
                self.dispatch_trigger(
                    "flag_set",
                    map_id=map_id,
                    target_id=flag,
                    actor=actor,
                    source_object=source_object,
                    payload={"flag": flag, "value": value},
                )
                continue
            if kind == "clear_flag":
                flag = str(action.get("flag") or "").strip()
                self.global_flags[flag] = False
                continue
            if kind in {"show_log", "show_prompt"}:
                message = str(action.get("message") or action.get("text") or "").strip()
                if not message:
                    continue
                if self.current_game is not None:
                    if kind == "show_prompt":
                        prompt_sent = False
                        try:
                            prompt_sent = self.current_game.player_prompt.info(
                                NARRATOR_TITLE,
                                body_markdown=message,
                                summary="Co się dzieje",
                                source="scenario_flow",
                                scope_key="scenario_transition",
                                dedupe_key=f"scenario_prompt:{_safe_id(trigger)}:{_safe_id(map_id)}:{_safe_id(target_id)}:{_safe_id(message)}",
                                semantic_type="required_action",
                            ) is not None
                        except Exception:
                            prompt_sent = False
                        if not prompt_sent:
                            self.current_game.ui_narration(message, summary="Co się dzieje", source="scenario_flow")
                    else:
                        self.current_game.ui_narration(message, summary="Co się dzieje", source="scenario_flow")
                continue
            if kind == "go_to_map":
                target_map_id = str(action.get("map_id") or "").strip()
                entry_anchor_id = str(
                    action.get("entry_anchor_id") or action.get("target_entry_anchor_id") or ""
                ).strip()
                if target_map_id:
                    self.pending_transition = {
                        "transition_id": None,
                        "from_map_id": str(map_id or self.current_map_id or ""),
                        "to_map_id": target_map_id,
                        "entry_anchor_id": entry_anchor_id or None,
                        "reason": trigger,
                    }
                continue
            if kind == "activate_transition":
                transition_id = str(action.get("transition_id") or "").strip()
                transition = self._find_transition(transition_id=transition_id)
                if transition is not None:
                    self.pending_transition = {
                        "transition_id": transition["id"],
                        "from_map_id": transition["from_map_id"],
                        "to_map_id": transition["to_map_id"],
                        "entry_anchor_id": transition["target_entry_anchor_id"],
                        "reason": trigger,
                    }
                continue
            if kind == "complete_objective":
                objective_id = str(action.get("objective_id") or action.get("id") or "").strip()
                if objective_id:
                    self.completed_objectives.add(objective_id)
                continue
            if kind == "checkpoint":
                self.save_checkpoint(reason=str(action.get("reason") or trigger or "event"))
                continue
            if kind == "start_combat":
                if self.current_game is not None:
                    self.current_game.start_combat(trigger=source_object)
                continue
            if kind == "spawn_group":
                self._spawn_group(action)
                continue
            if kind == "grant_loot":
                entry = {
                    "map_id": str(map_id or self.current_map_id or ""),
                    "target_id": str(target_id or ""),
                    "items": list(action.get("items") or []),
                    "message": str(action.get("message") or "").strip(),
                }
                self.loot_journal.append(entry)
                if self.current_game is not None and entry["message"]:
                    self.current_game.ui_log(entry["message"])
                continue
            if kind == "finish_scenario":
                self.finished = True
                if self.current_game is not None:
                    self.current_game.ui_log("Scenariusz zakończony.")
                continue

    def save_checkpoint(self, *, reason: str) -> None:
        checkpoint = {
            "reason": str(reason),
            "current_map_id": self.current_map_id,
            "global_flags": copy.deepcopy(self.global_flags),
            "completed_objectives": sorted(self.completed_objectives),
            "visited_maps": sorted(self.visited_maps | {self.current_map_id}),
        }
        self.checkpoints.append(checkpoint)

    def _apply_pending_transition(self) -> None:
        if self.pending_transition is None:
            return
        transition = dict(self.pending_transition)
        self.pending_transition = None
        self._snapshot_current_map()
        from_map_id = str(self.current_map_id or "")
        self.visited_maps.add(from_map_id)
        target_map_id = str(transition.get("to_map_id") or "").strip()
        anchor_id = str(transition.get("entry_anchor_id") or "").strip() or None
        if str(self.checkpoint_policy.get("transition") or "auto").strip().lower() != "off":
            self.save_checkpoint(reason=f"transition:{from_map_id}->{target_map_id}")
        self.current_map_id = target_map_id
        self._load_map(target_map_id, entry_anchor_id=anchor_id, initial_load=False, place_party=False)
        self._run_map_setup(initial_load=False)
        if self.current_game is not None and self.heroes:
            self._place_party_on_map(self.current_game, anchor_id=anchor_id, prompt_physical_setup=True)
            self.current_game.state = HeroesTurn(self.current_game)
            self.current_game._rebuild_object_registry_after_undo()
        self._announce_map_entry()
        self.dispatch_trigger(
            "map_start",
            map_id=target_map_id,
            target_id=anchor_id,
            payload={"from_map_id": from_map_id},
        )

    def _load_map(
        self,
        map_id: str,
        *,
        entry_anchor_id: str | None,
        initial_load: bool,
        place_party: bool = True,
    ) -> None:
        map_ref = self.maps.get(str(map_id or "").strip())
        if map_ref is None:
            raise ValueError(f"Nieznana mapa scenariusza '{map_id}'.")
        runtime_payload = resolve_map_payload(map_ref)
        runtime_payload.setdefault("metadata", {})
        runtime_payload["metadata"] = {
            **dict(runtime_payload.get("metadata") or {}),
            "scenario_flow_id": self.scenario_id,
            "scenario_map_id": map_id,
        }
        game = Game(
            conn=self.conn,
            scenario=map_id,
            scenario_payload=runtime_payload,
            scenario_label=f"{self.scenario_id}:{map_id}",
            preselected_character_ids=list(self.preselected_character_ids) if initial_load and not self.heroes else None,
        )
        game.scenario_session = self
        game.scenario_session_map_id = map_id
        self.current_game = game

        snapshot = self.map_snapshots.get(map_id)
        if snapshot is not None:
            game.board = copy.deepcopy(snapshot.board)
            game.enemies = self._collect_enemies_from_board(game.board)
            game.state = HeroesTurn(game)
            game._rebuild_object_registry_after_undo()

        if self.heroes and place_party:
            game.heroes = list(self.heroes)
            self._place_party_on_map(game, anchor_id=entry_anchor_id)
            game.state = HeroesTurn(game)
            game._rebuild_object_registry_after_undo()

    def _announce_session_start(self) -> None:
        if self._session_announced or self.current_game is None:
            return
        try:
            self.current_game.ui_narration(
                f"Rozpoczyna się scenariusz: {self.label}.",
                summary="Co się dzieje",
                source="scenario_flow",
            )
        except Exception:
            pass
        self._session_announced = True

    def _announce_map_entry(self) -> None:
        if self.current_game is None:
            return
        map_ref = self.maps.get(str(self.current_map_id or "").strip()) or {}
        self.current_game.ui_narration(
            f"Wchodzicie na mapę: {map_ref.get('label') or self.current_map_id}.",
            summary="Co się dzieje",
            source="scenario_flow",
        )

    def _prepare_opening_exploration_state(self) -> None:
        if self.current_game is None:
            return
        for hero in list(self.heroes or []):
            remover = getattr(hero, "remove_status", None)
            if callable(remover):
                try:
                    remover("observable")
                except Exception:
                    pass
            try:
                self.current_game.ui_hero(hero, note="Początek scenariusza: poza obserwacją")
            except Exception:
                pass

    def _snapshot_current_map(self) -> None:
        game = self.current_game
        if game is None:
            return
        board_copy = copy.deepcopy(game.board)
        self._remove_heroes_from_board(board_copy)
        self.map_snapshots[self.current_map_id] = MapSnapshot(
            map_id=self.current_map_id,
            board=board_copy,
            local_flags=copy.deepcopy(self.map_local_flags.get(self.current_map_id, {})),
        )

    @staticmethod
    def _remove_heroes_from_board(board) -> None:
        rows = int(getattr(board, "rows", 0) or 0)
        cols = int(getattr(board, "cols", 0) or 0)
        for row in range(rows):
            for col in range(cols):
                cell = board.cell_at((col, row))
                occupant = getattr(cell, "occupant", None)
                if isinstance(occupant, Hero):
                    cell.occupant = None
                    occupant.set_position(None)

    @staticmethod
    def _collect_enemies_from_board(board) -> list[BasicEnemy]:
        enemies: list[BasicEnemy] = []
        rows = int(getattr(board, "rows", 0) or 0)
        cols = int(getattr(board, "cols", 0) or 0)
        for row in range(rows):
            for col in range(cols):
                occupant = getattr(board.cell_at((col, row)), "occupant", None)
                if isinstance(occupant, BasicEnemy):
                    enemies.append(occupant)
        return enemies

    def _run_map_setup(self, *, initial_load: bool) -> None:
        if self.current_game is None:
            return
        map_ref = self.maps.get(str(self.current_map_id or "").strip()) or {}
        plan = build_runtime_setup_plan(
            self.current_game,
            include_clear_prompt=not initial_load,
            clear_prompt=(
                f"Przygotuj fizycznie mapę: {map_ref.get('label') or self.current_map_id}. "
                "Usuń poprzedni układ i rozstaw nowy zgodnie z podświetleniem."
            ),
        )
        if plan:
            run_setup_batches(self.current_game, plan)

    def _place_party_on_map(self, game: Game, *, anchor_id: str | None, prompt_physical_setup: bool = False) -> None:
        positions = self._resolve_entry_positions(game, anchor_id=anchor_id)
        available_positions = list(positions)
        for hero in self.heroes:
            target_position = available_positions[0]
            if prompt_physical_setup:
                hero_name = str(getattr(hero, "name", "Bohater") or "Bohater")
                prompt = (
                    f"Wybierz pole wejścia dla bohatera {hero_name}, klikając jedno z podświetlonych pól."
                )
                game.ui_log(prompt)
                game.ui_idle_hint("Zmiana mapy", prompt)
                try:
                    game.conn.set_leds(available_positions, consts.MOVE_FIELD_RGB)
                except Exception:
                    pass
                try:
                    selected = game.conn.scan_board(available_positions)
                except Exception:
                    selected = None
                try:
                    game.conn.leds_off()
                except Exception:
                    pass
                if selected in available_positions:
                    target_position = selected
                confirm_prompt = (
                    f"Wybrane pole wejścia dla bohatera {hero_name}: {target_position}.\n"
                    "Przenieś figurkę na to pole i potwierdź Enterem."
                )
                confirm_sent = False
                try:
                    confirm_sent = game.player_prompt.info(
                        "Przenieś bohatera",
                        body_markdown=confirm_prompt,
                        summary="Zmiana mapy",
                        source="scenario_transition_place",
                        scope_key="scenario_transition",
                        dedupe_key=f"scenario_transition_place:{self.current_map_id}:{hero_name}",
                    ) is not None
                except Exception:
                    confirm_sent = False
                if not confirm_sent:
                    game.ui_log(confirm_prompt)
            try:
                game.board.place(hero, target_position)
            except ValueError:
                continue
            available_positions = [pos for pos in available_positions if pos != target_position]
            game.ui_hero(hero, note=f"Wejście na mapę {self.current_map_id}")

    def _resolve_entry_positions(self, game: Game, *, anchor_id: str | None) -> list[tuple[int, int]]:
        anchor_positions = self._anchor_positions(game.board, anchor_id) if anchor_id else []
        if not anchor_positions:
            anchor_positions = [tuple(pos) for pos in list(game.scenario.get("starting_positions") or [])]
        resolved: list[tuple[int, int]] = []
        reserved: set[tuple[int, int]] = set()
        queue = deque(anchor_positions)
        seen = set(anchor_positions)
        while queue and len(resolved) < len(self.heroes):
            pos = tuple(queue.popleft())
            if pos in reserved:
                continue
            try:
                if game.board.can_enter(pos, allow_occupied=False):
                    resolved.append(pos)
                    reserved.add(pos)
            except Exception:
                pass
            try:
                for neighbor in game.board.get_neighbors(pos, include_position=False, diagonal=True):
                    if neighbor in seen:
                        continue
                    seen.add(neighbor)
                    queue.append(neighbor)
            except Exception:
                continue
        if len(resolved) < len(self.heroes):
            raise ValueError(f"Brak wystarczającej liczby pól wejścia dla mapy '{self.current_map_id}'.")
        return resolved

    @staticmethod
    def _anchor_positions(board, anchor_id: str | None) -> list[tuple[int, int]]:
        target_id = str(anchor_id or "").strip()
        positions: list[tuple[int, int]] = []
        rows = int(getattr(board, "rows", 0) or 0)
        cols = int(getattr(board, "cols", 0) or 0)
        for row in range(rows):
            for col in range(cols):
                pos = (col, row)
                for obj in list(board.interactables_at(pos) or []):
                    if isinstance(obj, EntryAnchor) and str(getattr(obj, "entry_anchor_id", "")).strip() == target_id:
                        positions.append(pos)
                        break
        return sorted(positions, key=lambda item: (item[1], item[0]))

    def _find_transition(
        self,
        *,
        transition_id: str | None = None,
        exit_id: str | None = None,
        from_map_id: str | None = None,
    ) -> dict[str, Any] | None:
        for transition in self.transitions:
            if transition_id and str(transition.get("id") or "").strip() == str(transition_id):
                return transition
            if exit_id and from_map_id:
                if (
                    str(transition.get("exit_id") or "").strip() == str(exit_id)
                    and str(transition.get("from_map_id") or "").strip() == str(from_map_id)
                ):
                    return transition
        return None

    def _has_trigger_binding(self, trigger: str, *, map_id: str | None, target_id: str | None) -> bool:
        normalized_trigger = str(trigger or "").strip().lower()
        lookup_map_id = str(map_id or "").strip() or None
        lookup_target_id = str(target_id or "").strip() or None
        for event in list(self.flow.get("events") or []):
            if str(event.get("trigger") or "").strip().lower() != normalized_trigger:
                continue
            event_map_id = str(event.get("map_id") or "").strip() or None
            event_target_id = str(event.get("target_id") or "").strip() or None
            if event_map_id and event_map_id != lookup_map_id:
                continue
            if event_target_id and event_target_id != lookup_target_id:
                continue
            return True
        return False

    def _conditions_pass(self, conditions: Any, *, map_id: str | None, target_id: str | None) -> bool:
        for condition in list(conditions or []):
            kind = str(condition.get("type") or "").strip().lower()
            if kind == "flag":
                flag = str(condition.get("flag") or "").strip()
                expected = condition.get("value", True)
                if self.global_flags.get(flag) != expected:
                    return False
                continue
            if kind == "visited_map":
                required_map_id = str(condition.get("map_id") or "").strip()
                expected = bool(condition.get("value", True))
                is_visited = required_map_id in self.visited_maps
                if is_visited != expected:
                    return False
                continue
            if kind == "map_enemies_cleared":
                target_map = str(condition.get("map_id") or map_id or self.current_map_id or "").strip()
                expected = bool(condition.get("value", True))
                cleared = self._map_enemies_cleared(target_map)
                if cleared != expected:
                    return False
                continue
            if kind == "objective_completed":
                objective_id = str(condition.get("objective_id") or condition.get("id") or "").strip()
                expected = bool(condition.get("value", True))
                done = objective_id in self.completed_objectives
                if done != expected:
                    return False
                continue
            if kind == "object_state":
                state_name = str(condition.get("state") or "").strip()
                expected = condition.get("value", True)
                lookup_map_id = str(condition.get("map_id") or map_id or self.current_map_id or "").strip()
                lookup_target = str(condition.get("target_id") or target_id or "").strip()
                current_value = self._object_state_value(lookup_map_id, lookup_target, state_name)
                if current_value != expected:
                    return False
                continue
        return True

    def _map_enemies_cleared(self, map_id: str) -> bool:
        if map_id == self.current_map_id and self.current_game is not None:
            return not self.current_game._has_combat_ready_enemies()
        snapshot = self.map_snapshots.get(map_id)
        if snapshot is None:
            return False
        return not any(self.current_game._is_enemy_combat_ready(enemy) for enemy in self._collect_enemies_from_board(snapshot.board))  # type: ignore[union-attr]

    def _object_state_value(self, map_id: str, target_id: str, state_name: str) -> Any:
        if not map_id or not target_id or not state_name:
            return None
        objects = self._iter_logic_objects(map_id)
        for obj in objects:
            if str(getattr(obj, "exit_id", "")).strip() == target_id or str(getattr(obj, "entry_anchor_id", "")).strip() == target_id:
                return getattr(obj, state_name, None)
        return None

    def _iter_logic_objects(self, map_id: str) -> list[object]:
        board = None
        if map_id == self.current_map_id and self.current_game is not None:
            board = self.current_game.board
        else:
            snapshot = self.map_snapshots.get(map_id)
            board = snapshot.board if snapshot is not None else None
        if board is None:
            return []
        result: list[object] = []
        rows = int(getattr(board, "rows", 0) or 0)
        cols = int(getattr(board, "cols", 0) or 0)
        for row in range(rows):
            for col in range(cols):
                pos = (col, row)
                result.extend(list(board.interactables_at(pos) or []))
        return result

    def _spawn_group(self, action: dict[str, Any]) -> None:
        if self.current_game is None:
            return
        map_id = str(action.get("map_id") or self.current_map_id or "").strip()
        if map_id != self.current_map_id:
            return
        spawns = list(action.get("spawns") or [])
        for spawn in spawns:
            if not isinstance(spawn, dict):
                continue
            category = str(spawn.get("category") or "Enemies").strip()
            object_id = str(spawn.get("object_id") or "").strip()
            position = spawn.get("position") or spawn.get("pos")
            if not object_id or not isinstance(position, (list, tuple)) or len(position) < 2:
                continue
            obj = self.current_game._encounter_build_object_instance(category, object_id, dict(spawn.get("config") or {}))
            if obj is None:
                continue
            pos_tuple = (int(position[0]), int(position[1]))
            try:
                if category == "Enemies":
                    self.current_game.board.place(obj, pos_tuple)
                    self.current_game.enemies.append(obj)
                else:
                    self.current_game.board.add_interactable(obj, pos_tuple)
            except Exception:
                logger.debug("Nie udało się zespawnować obiektu %s na %s.", object_id, pos_tuple, exc_info=True)


def _safe_id(value: object) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return "none"
    normalized = "".join(ch if ch.isalnum() else "_" for ch in text)
    return normalized[:64] or "none"
