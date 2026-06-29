from __future__ import annotations

import argparse
import queue
import random
import select
import sys
import threading
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from dnd_board_game.actors import Actor
from dnd_board_game.combat import SceneFlags, SetupVisibility, objective_status_after_flags, set_scene_flag
from dnd_board_game.exploration import (
    ExplorationChallenge,
    ExplorationChallengeOption,
    ExplorationMenu,
    ExplorationMenuOption,
    ExplorationMenuOptionKind,
    ExplorationOption,
    ExplorationOptionKind,
    ExplorationPoint,
    ExplorationResource,
    ExplorationState,
    ExplorationZone,
    PartyCheckInput,
    SearchResult,
    available_challenge_options,
    available_exploration_zones,
    build_exploration_menu,
    challenge_for_zone,
    challenge_state_for,
    exploration_setup_feedback,
    exploration_menu_feedback,
    exploration_zone_feedback,
    grant_resource,
    look_around_feedback,
    matching_resources,
    menu_option_for_position,
    party_position_feedback,
    resolve_challenge_option,
    resolve_party_check,
    resolve_zone_search,
    set_party_zone,
    visible_exploration_points,
    visible_exploration_zones,
    zone_for_position,
    zone_is_available,
)
from dnd_board_game.hardware import BoardLedAdapter, LedColor, LedFeedback, LedFrame, LedRole, led_color_name_pl
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    RollMode,
    RollModifier,
    RollModifierType,
    ability_modifier,
    resolve_d20_roll,
    roll_instruction,
)
from dnd_board_game.scenarios import LoadedExploration, build_exploration_from_scenario, load_scenario
from dnd_board_game.world import Coordinate

from .demo_mini_combat import ConnectionFactory, _create_adapter, _read_int_or_default
from .demo_mini_combat_loop import _batched, _pause_for_led_step
from .session_observer import SessionObserver


@dataclass(frozen=True, slots=True)
class DemoExplorationResult:
    messages: tuple[str, ...]
    final_state: ExplorationState
    observation_path: Path
    feedback_events: int


def run_demo(
    args: argparse.Namespace,
    *,
    connection_factory: ConnectionFactory | None = None,
) -> DemoExplorationResult:
    observer = SessionObserver(args.session_id, Path(args.observation_dir))
    observer.record("session_started", {"runtime": "demo_exploration_scene"})
    observer.record(
        "board_backend_selected",
        {"backend": args.board_backend, "board_url": args.board_url, "show_leds": args.show_leds},
    )
    adapter = _create_adapter(args, connection_factory) if args.show_leds and args.board_backend != "none" else None
    exploration = _load_exploration(args.scenario)
    observer.record(
        "scenario_loaded",
        {"scenario_id": exploration.scenario_id, "scenario_name": exploration.scenario_name, "path": args.scenario},
    )
    observer.record(
        "exploration_started",
        {"scenario_id": exploration.scenario_id, "scenario_name": exploration.scenario_name},
    )
    objectives = exploration.objectives
    state = ExplorationState(
        exploration.zones,
        exploration.points,
        exploration.party_position,
        SceneFlags(),
        challenges=exploration.challenges,
        resources=exploration.resources,
        inventory_resource_ids=exploration.initial_resource_ids,
    )
    messages: list[str] = [f"Scenariusz eksploracji: {exploration.scenario_name}."]
    print(messages[-1])
    setup_messages, feedback_events = _run_exploration_setup(args, exploration, state, adapter, observer)
    messages.extend(setup_messages)
    for objective in objectives:
        objective_message = f"Cel eksploracji: {objective.name}. {objective.description}".strip()
        print(objective_message)
        messages.append(objective_message)
        observer.record(
            "objective_started",
            {
                "objective_id": objective.id,
                "name": objective.name,
                "condition": objective.condition.value,
                "flag_key": objective.flag_key,
                "flag_value": objective.flag_value,
            },
        )

    scripts = list(args.exploration_script)
    steps = 0
    while steps < args.max_steps:
        steps += 1
        if adapter is not None:
            adapter.clear()
            adapter.show_feedback(exploration_zone_feedback(state))
            feedback_events += 1
            observer.record("led_feedback_sent", {"phase": "exploration_map"})
        clicked = _next_exploration_click(args, state, adapter, observer, scripts)
        if clicked is None:
            message = "Eksploracja zakończona."
            print(message)
            messages.append(message)
            observer.record("exploration_finished", {"reason": "ended_by_user"})
            break
        point = _visible_point_for_position(state, clicked)
        if point is not None:
            state, point_messages, sent = _handle_exploration_point(args, state, point, adapter, observer)
            objectives = _record_objectives_after_flags(objectives, state.flags, observer)
            messages.extend(point_messages)
            feedback_events += sent
            if _objectives_completed(objectives):
                _finish_exploration_objectives(observer, messages)
                break
            continue
        zone = zone_for_position(state.zones, clicked)
        if zone is not None and not zone_is_available(state, zone):
            zone = None
        observer.record("exploration_zone_clicked", {"position": list(clicked.as_tuple()), "zone_id": zone.id if zone else None})
        if zone is None:
            message = "Nie ma tu dostępnej lokacji."
            print(message)
            messages.append(message)
            continue
        if zone.id != state.party_position.zone_id:
            state, travel_messages, sent = _handle_zone_travel(args, state, zone, adapter, observer, scripts)
            messages.extend(travel_messages)
            feedback_events += sent
            continue
        if clicked != zone.marker_position:
            message = f"To fragment strefy: {zone.name}. Główne opcje tej lokacji są w podświetlonym punkcie centralnym."
            print(message)
            observer.record(
                "zone_tile_inspected",
                {
                    "zone_id": zone.id,
                    "position": list(clicked.as_tuple()),
                    "anchor_position": list(zone.marker_position.as_tuple()),
                },
            )
            messages.append(message)
            continue
        state, option_messages, sent = _handle_zone_options(args, exploration.actors, state, zone, adapter, observer, scripts)
        objectives = _record_objectives_after_flags(objectives, state.flags, observer)
        messages.extend(option_messages)
        feedback_events += sent
        if _objectives_completed(objectives):
            _finish_exploration_objectives(observer, messages)
            break
    else:
        message = f"Eksploracja zatrzymana po limicie kroków: {args.max_steps}."
        print(message)
        messages.append(message)
        observer.record("exploration_finished", {"reason": "max_steps", "max_steps": args.max_steps})

    observer.record("session_finished", {"observation_path": str(observer.path)})
    return DemoExplorationResult(tuple(messages), state, observer.path, feedback_events)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run exploration scene demo.")
    parser.add_argument("--scenario", default="content/scenarios/abandoned_watchtower.json")
    parser.add_argument("--board-backend", choices=("none", "simulator", "hardware"), default="none")
    parser.add_argument("--board-url", default="http://127.0.0.1:5000")
    parser.add_argument("--board-serial-port", default=None)
    parser.add_argument("--wled-url", default=None)
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--observation-dir", default="data/session_observations")
    parser.add_argument("--show-leds", dest="show_leds", action="store_true", default=False)
    parser.add_argument("--no-show-leds", dest="show_leds", action="store_false")
    parser.add_argument("--wait-for-enter", action="store_true", default=False)
    parser.add_argument("--step-delay", type=float, default=1.5)
    parser.add_argument("--scan-timeout", type=float, default=30.0)
    parser.add_argument("--max-steps", type=int, default=12)
    parser.add_argument("--exploration-script", action="append", default=[])
    parser.add_argument("--party-check-roll", action="append", default=[])
    parser.add_argument("--challenge-roll", action="append", default=[])
    parser.add_argument("--resource-choice", action="append", default=[])
    parser.add_argument("--exploration-seed", type=int, default=7)
    parser.add_argument("--look-around-clicks", type=int, default=3)
    parser.add_argument("--leader-id", default="hero")
    parser.add_argument("--helper-id", default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.session_id is None:
        args.session_id = f"demo_exploration_{uuid.uuid4().hex[:8]}"
    try:
        run_demo(args)
    except Exception as exc:
        print(f"demo_exploration_scene failed: {exc}", file=sys.stderr)
        return 1
    return 0


def _run_exploration_setup(
    args: argparse.Namespace,
    exploration: LoadedExploration,
    state: ExplorationState,
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
) -> tuple[tuple[str, ...], int]:
    messages: list[str] = []
    feedback_events = 0
    message = "Połóż mapę eksploracji na planszy i ustaw jawne elementy sceny."
    print(message)
    messages.append(message)
    observer.record("exploration_setup_started", {"scenario_id": exploration.scenario_id})

    available_zones = available_exploration_zones(state)
    if available_zones:
        zone_lines = ["Dostępne lokacje:"]
        for zone in available_zones:
            zone_lines.append(f"- {zone.name}: kolor {led_color_name_pl(zone.color)}")
        zone_lines.append("Kliknij odpowiednią lokację, aby wejść w interakcję.")
        zones_message = "\n".join(zone_lines)
        print(zones_message)
        messages.append(zones_message)
        observer.record(
            "exploration_setup_step_started",
            {
                "phase": "exploration_available_zones",
                "zone_ids": [zone.id for zone in available_zones],
            },
        )
        if adapter is not None:
            adapter.clear()
            adapter.show_feedback(exploration_zone_feedback(state))
            feedback_events += 1
            observer.record("led_feedback_sent", {"phase": "exploration_available_zones"})
        observer.record(
            "exploration_setup_step_confirmed",
            {
                "phase": "exploration_available_zones",
                "selected_position": None,
            },
        )

    setup_points = tuple(point for point in visible_exploration_points(state.points) if point.requires_setup)
    setup_positions = tuple(position for point in setup_points for position in point.positions)
    setup_names = ", ".join(point.name for point in setup_points)
    for batch_index, batch in enumerate(_batched(setup_positions, 5), start=1):
        label = f": {setup_names}" if setup_names else ""
        step_message = f"Setup jawnych elementów {batch_index}{label}. Kliknij jedno z podświetlonych pól po ustawieniu elementów."
        print(step_message)
        messages.append(step_message)
        feedback_events += _confirm_setup_step(args, adapter, observer, batch, LedColor.INTERACTIVE_OBJECT, "exploration_setup_points", step_message)

    observer.record("party_position_set", {"zone_id": state.party_position.zone_id})
    observer.record("exploration_setup_confirmed", {"scenario_id": exploration.scenario_id})
    return tuple(messages), feedback_events


def _confirm_setup_step(
    args: argparse.Namespace,
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
    positions: tuple[Coordinate, ...],
    color: tuple[int, int, int],
    phase: str,
    prompt: str,
    anchor_position: Coordinate | None = None,
) -> int:
    observer.record("exploration_setup_step_started", {"phase": phase, "positions": [list(position.as_tuple()) for position in positions]})
    if adapter is None:
        observer.record("exploration_setup_step_confirmed", {"phase": phase, "selected_position": list(positions[0].as_tuple()) if positions else None})
        return 0
    adapter.show_feedback(exploration_setup_feedback(positions, color, anchor_position))
    observer.record("led_feedback_sent", {"phase": phase})
    scan_board = getattr(adapter.connection, "scan_board", None)
    selected = None
    if callable(scan_board) and positions:
        selected = scan_board([position.as_tuple() for position in positions], timeout_s=args.scan_timeout)
    else:
        _pause_for_led_step(args, prompt)
    adapter.clear()
    observer.record("exploration_setup_step_confirmed", {"phase": phase, "selected_position": list(selected) if selected else None})
    return 1


def _next_exploration_click(args: argparse.Namespace, state: ExplorationState, adapter: BoardLedAdapter | None, observer: SessionObserver, scripts: list[str]) -> Coordinate | None:
    if scripts:
        return _coordinate_from_script(scripts.pop(0), state)
    if args.board_backend == "none" or adapter is None:
        return None
    scan_board = getattr(adapter.connection, "scan_board", None)
    if not callable(scan_board):
        return None
    acceptable = [zone.marker_position.as_tuple() for zone in available_exploration_zones(state)]
    acceptable.extend(position.as_tuple() for point in visible_exploration_points(state.points) for position in point.positions)
    observer.record("board_scan_requested", {"phase": "exploration_click", "acceptable_positions": [list(position) for position in acceptable]})
    selected = scan_board(None, timeout_s=args.scan_timeout)
    if selected is None:
        observer.record("board_scan_cancelled", {"phase": "exploration_click"})
        return None
    observer.record("board_scan_received", {"phase": "exploration_click", "position": list(selected)})
    return Coordinate(int(selected[0]), int(selected[1]))


def _handle_zone_travel(
    args: argparse.Namespace,
    state: ExplorationState,
    destination: ExplorationZone,
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
    scripts: list[str],
) -> tuple[ExplorationState, tuple[str, ...], int]:
    current = _current_zone(state)
    if destination.id not in current.adjacent_zone_ids:
        message = f"Nie można przejść bezpośrednio z {current.name} do {destination.name}."
        print(message)
        observer.record("zone_travel_rejected", {"from_zone_id": current.id, "to_zone_id": destination.id, "reason": "not_adjacent"})
        return state, (message,), 0
    message = f"Czy opuścić {current.name} i przejść do {destination.name}? Kliknij tę strefę ponownie, aby potwierdzić."
    print(message)
    observer.record("zone_travel_previewed", {"from_zone_id": current.id, "to_zone_id": destination.id})
    feedback_events = 0
    if adapter is not None:
        adapter.show_feedback(LedFeedback((LedFrame(current.positions, LedColor.ACTIVE_ACTOR, LedRole.ACTIVE_ACTOR), LedFrame(destination.positions, destination.color, LedRole.DESTINATION))))
        feedback_events += 1
        observer.record("led_feedback_sent", {"phase": "zone_travel_preview", "to_zone_id": destination.id})
    confirmed = _confirm_zone_click(args, state, destination, adapter, observer, scripts)
    if not confirmed:
        if adapter is not None:
            adapter.clear()
        return state, (message, "Przejście anulowane."), feedback_events
    new_state = set_party_zone(state, destination)
    observer.record("zone_travel_confirmed", {"from_zone_id": current.id, "to_zone_id": destination.id})
    observer.record("party_zone_changed", {"from_zone_id": current.id, "to_zone_id": destination.id})
    confirm_message = f"Drużyna przechodzi do strefy: {destination.name}."
    print(confirm_message)
    if adapter is not None:
        adapter.clear()
        adapter.show_feedback(party_position_feedback(new_state))
        feedback_events += 1
        observer.record("led_feedback_sent", {"phase": "party_position", "zone_id": destination.id})
    return new_state, (message, confirm_message), feedback_events


def _handle_zone_options(
    args: argparse.Namespace,
    actors: tuple[Actor, ...],
    state: ExplorationState,
    zone: ExplorationZone,
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
    scripts: list[str],
) -> tuple[ExplorationState, tuple[str, ...], int]:
    menu = build_exploration_menu(state, zone)
    if not menu.options:
        message = f"{zone.name}: nie ma teraz dostępnych opcji."
        print(message)
        return state, (message,), 0
    message = _menu_message(zone, menu)
    print(message)
    observer.record(
        "exploration_menu_opened",
        {
            "zone_id": zone.id,
            "options": [
                {"id": option.id, "label": option.label, "kind": option.kind.value, "position": list(option.slot_position.as_tuple())}
                for option in menu.options
            ],
        },
    )
    feedback_events = 0
    if adapter is not None:
        adapter.clear()
        adapter.show_feedback(exploration_menu_feedback(menu))
        feedback_events += 1
        observer.record("led_feedback_sent", {"phase": "exploration_menu", "zone_id": zone.id})
    selected = _select_menu_option(args, menu, adapter, observer, scripts)
    if selected is None:
        return state, (message,), feedback_events
    if selected.kind == ExplorationMenuOptionKind.CANCEL:
        cancel_message = "Wycofano wybór opcji."
        print(cancel_message)
        observer.record("exploration_menu_cancelled", {"zone_id": zone.id})
        return state, (message, cancel_message), feedback_events
    if selected.kind == ExplorationMenuOptionKind.LOOK_AROUND:
        new_state, look_messages, sent = _handle_look_around(args, state, zone, adapter, observer, scripts)
        return new_state, (message, *look_messages), feedback_events + sent
    if selected.kind == ExplorationMenuOptionKind.CHALLENGE:
        challenge = challenge_for_zone(state, zone.id)
        if challenge is None:
            error_message = f"{zone.name}: ta opcja wyzwania nie jest już dostępna."
            print(error_message)
            return state, (message, error_message), feedback_events
        option = next(option for option in available_challenge_options(state, challenge) if option.id == selected.source_id)
        resources = matching_resources(state, option)
        observer.record("challenge_option_confirmed", {"challenge_id": challenge.id, "option_id": option.id})
        resource = _select_resource(args, option, resources)
        if resource is not None:
            _activate_resource(args, challenge, option, resource, observer)
        new_state, result_messages = _resolve_challenge_option(args, actors, state, challenge, option, resource, observer)
        return new_state, (message, *result_messages), feedback_events
    if selected.kind == ExplorationMenuOptionKind.ZONE_OPTION:
        option = next(option for option in zone.options if option.id == selected.source_id)
        observer.record("zone_option_confirmed", {"zone_id": zone.id, "option_id": option.id})
        if option.kind == ExplorationOptionKind.SEARCH:
            new_state, search_messages = _resolve_search_option(args, actors, state, zone, adapter, observer)
            return new_state, (message, *search_messages), feedback_events
        if option.kind == ExplorationOptionKind.CHECK and option.ability_check is not None:
            new_state, check_messages = _resolve_check_option(args, actors, state, option, observer)
            return new_state, (message, *check_messages), feedback_events
        new_state = _apply_message_option_flags(state, option, observer)
        option_message = option.message or option.description or f"Wykonano opcję: {option.label}."
        print(option_message)
        return new_state, (message, option_message), feedback_events
    return state, (message,), feedback_events


def _apply_message_option_flags(
    state: ExplorationState,
    option: ExplorationOption,
    observer: SessionObserver,
) -> ExplorationState:
    flags = state.flags
    changed: list[str] = []
    if option.success_flag and not _scene_flag_bool(flags, option.success_flag):
        flags = set_scene_flag(flags, option.success_flag, True)
        changed.append(option.success_flag)
    if option.failure_flag and not _scene_flag_bool(flags, option.failure_flag):
        flags = set_scene_flag(flags, option.failure_flag, True)
        changed.append(option.failure_flag)
    for flag_key in changed:
        observer.record("scene_flag_set", {"option_id": option.id, "flag_key": flag_key, "value": True})
    if not changed:
        return state
    return replace(state, flags=flags)


def _scene_flag_bool(flags: SceneFlags, key: str) -> bool:
    return bool(next((value for flag_key, value in flags.values if flag_key == key), False))


def _record_objectives_after_flags(objectives, flags: SceneFlags, observer: SessionObserver):
    completed_before = {objective.id for objective in objectives if objective.status.value == "completed"}
    updated = objective_status_after_flags(objectives, flags)
    for objective in updated:
        if objective.status.value == "completed" and objective.id not in completed_before:
            observer.record("objective_completed", {"objective_id": objective.id, "name": objective.name})
    return updated


def _objectives_completed(objectives) -> bool:
    return bool(objectives) and all(objective.status.value == "completed" for objective in objectives)


def _finish_exploration_objectives(observer: SessionObserver, messages: list[str]) -> None:
    message = "Cel eksploracji został osiągnięty. Scena zakończona."
    print(message)
    messages.append(message)
    observer.record("exploration_finished", {"reason": "objectives_completed"})


def _menu_message(zone: ExplorationZone, menu: ExplorationMenu) -> str:
    lines = [f"{zone.name}. Dostępne opcje:"]
    for option in menu.options:
        lines.append(f"- {option.label}: kolor {led_color_name_pl(option.color)}, pole {option.slot_position.as_tuple()}")
    lines.append("Kliknij podświetlone pole opcji, aby ją wybrać.")
    return "\n".join(lines)


def _select_menu_option(
    args: argparse.Namespace,
    menu: ExplorationMenu,
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
    scripts: list[str],
) -> ExplorationMenuOption | None:
    if scripts:
        command = scripts.pop(0).strip()
        if command.startswith("option:"):
            option_id = command.removeprefix("option:")
            selected = next((option for option in menu.options if option.id == option_id), None)
            if selected is None:
                raise ValueError(f"Unknown exploration menu option: {option_id}.")
            observer.record("exploration_menu_option_selected", {"zone_id": menu.zone.id, "option_id": selected.id, "source": "script"})
            return selected
        if command == "confirm":
            selected = next(option for option in menu.options if option.kind != ExplorationMenuOptionKind.CANCEL)
            observer.record("exploration_menu_option_selected", {"zone_id": menu.zone.id, "option_id": selected.id, "source": "script_compat"})
            return selected
        if command == "cancel":
            selected = next(option for option in menu.options if option.kind == ExplorationMenuOptionKind.CANCEL)
            observer.record("exploration_menu_option_selected", {"zone_id": menu.zone.id, "option_id": selected.id, "source": "script"})
            return selected
        scripts.insert(0, command)
        return None
    if args.board_backend == "none" or adapter is None:
        selected = next(option for option in menu.options if option.kind != ExplorationMenuOptionKind.CANCEL)
        observer.record("exploration_menu_option_selected", {"zone_id": menu.zone.id, "option_id": selected.id, "source": "default"})
        return selected
    scan_board = getattr(adapter.connection, "scan_board", None)
    if not callable(scan_board):
        return None
    acceptable = [option.slot_position.as_tuple() for option in menu.options]
    observer.record("board_scan_requested", {"phase": "exploration_menu", "acceptable_positions": [list(position) for position in acceptable]})
    print("Kliknij jedno z podświetlonych pól opcji.")
    selected_position = scan_board(acceptable, timeout_s=args.scan_timeout)
    if selected_position is None:
        observer.record("board_scan_cancelled", {"phase": "exploration_menu"})
        return None
    coordinate = Coordinate(int(selected_position[0]), int(selected_position[1]))
    selected = menu_option_for_position(menu, coordinate)
    observer.record(
        "exploration_menu_option_selected",
        {
            "zone_id": menu.zone.id,
            "option_id": selected.id if selected else None,
            "position": list(coordinate.as_tuple()),
            "source": "board",
        },
    )
    return selected


def _handle_look_around(
    args: argparse.Namespace,
    state: ExplorationState,
    zone: ExplorationZone,
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
    scripts: list[str],
) -> tuple[ExplorationState, tuple[str, ...], int]:
    message = (
        f"Rozglądacie się po okolicy: {zone.name}. "
        f"Możecie kliknąć do {args.look_around_clicks} pól tej strefy."
    )
    print(message)
    observer.record("look_around_started", {"zone_id": zone.id, "limit": args.look_around_clicks})
    feedback_events = 0
    if adapter is not None:
        adapter.clear()
        adapter.show_feedback(look_around_feedback(zone))
        feedback_events += 1
        observer.record("led_feedback_sent", {"phase": "look_around", "zone_id": zone.id})
    messages = [message]
    current_state = state
    for index in range(args.look_around_clicks):
        clicked = _next_look_around_click(args, current_state, zone, adapter, observer, scripts)
        if clicked is None:
            break
        point = _visible_point_for_position(current_state, clicked)
        if point is not None:
            current_state, point_messages, sent = _handle_exploration_point(args, current_state, point, adapter, observer)
            messages.extend(point_messages)
            feedback_events += sent
            continue
        if clicked in zone.positions:
            tile_message = f"Sprawdzacie fragment lokacji {zone.name} na polu {clicked.as_tuple()}. Nie ma tu nic oczywistego."
            print(tile_message)
            messages.append(tile_message)
            observer.record(
                "look_around_tile_checked",
                {"zone_id": zone.id, "position": list(clicked.as_tuple()), "index": index},
            )
            continue
        outside_message = "To pole nie należy do aktualnie oglądanej lokacji."
        print(outside_message)
        messages.append(outside_message)
    observer.record("look_around_finished", {"zone_id": zone.id})
    return current_state, tuple(messages), feedback_events


def _next_look_around_click(
    args: argparse.Namespace,
    state: ExplorationState,
    zone: ExplorationZone,
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
    scripts: list[str],
) -> Coordinate | None:
    if scripts:
        command = scripts.pop(0).strip()
        if command in {"look_done", "cancel", "end"}:
            return None
        return _coordinate_from_script(command, state)
    if args.board_backend == "none" or adapter is None:
        return None
    scan_board = getattr(adapter.connection, "scan_board", None)
    if not callable(scan_board):
        return None
    acceptable = [position.as_tuple() for position in zone.positions]
    acceptable.extend(position.as_tuple() for point in visible_exploration_points(state.points) for position in point.positions)
    print("Kliknij pole w oglądanej strefie albo poczekaj, aby zakończyć rozejrzenie.")
    selected = scan_board(acceptable, timeout_s=args.scan_timeout)
    if selected is None:
        observer.record("board_scan_cancelled", {"phase": "look_around"})
        return None
    observer.record("board_scan_received", {"phase": "look_around", "position": list(selected)})
    return Coordinate(int(selected[0]), int(selected[1]))


def _resolve_challenge_option(
    args: argparse.Namespace,
    actors: tuple[Actor, ...],
    state: ExplorationState,
    challenge: ExplorationChallenge,
    option: ExplorationChallengeOption,
    resource: ExplorationResource | None,
    observer: SessionObserver,
) -> tuple[ExplorationState, tuple[str, ...]]:
    actor = next((candidate for candidate in actors if str(candidate.id) == args.leader_id), actors[0])
    modifiers = (
        *_ability_roll_modifiers(actor, option.ability_check.ability, option.ability_check.skill),
        *option.ability_check.modifiers,
        *_resource_roll_modifiers(resource),
        *_support_roll_modifiers(state, option),
    )
    mode = RollMode.ADVANTAGE if resource is not None and resource.advantage else RollMode.NORMAL
    request = D20RollRequest(mode=mode, modifiers=modifiers)
    instruction = roll_instruction(request)
    print(f"Test podejścia: {option.label}. ST {option.ability_check.dc}. {instruction.message}")
    natural_roll = _challenge_roll_for_option(args, option.id)
    if natural_roll is None:
        natural_roll = _read_int_or_default(args, f"Wpisz naturalny wynik testu dla {actor.name}: ", 10)
    else:
        print(f"Używam wyniku testowego dla {option.label}: {natural_roll}.")
    roll = resolve_d20_roll(D20RollInput(request, natural_roll))
    result = resolve_challenge_option(state, challenge, option, roll, resource)
    print(result.message)
    observer.record(
        "challenge_option_resolved",
        {
            "challenge_id": challenge.id,
            "option_id": option.id,
            "actor_id": str(actor.id),
            "natural_roll": roll.natural_roll,
            "total": roll.total,
            "success": result.success,
            "critical_failure": result.critical_failure,
            "resource_id": resource.id if resource else None,
        },
    )
    observer.record(
        "challenge_progress_updated",
        {
            "challenge_id": challenge.id,
            "progress_added": result.progress_added,
            "current_progress": challenge_state_for(result.state, challenge.id).current_progress,
            "progress_required": challenge.progress_required,
            "noise_added": result.noise_added,
            "complications_added": list(result.complications_added),
        },
    )
    if result.completed:
        observer.record("challenge_completed", {"challenge_id": challenge.id, "completed_flag": challenge.completed_flag})
    return result.state, (result.message,)


def _confirm_zone_click(args: argparse.Namespace, state: ExplorationState, destination: ExplorationZone, adapter: BoardLedAdapter | None, observer: SessionObserver, scripts: list[str]) -> bool:
    if scripts:
        clicked = _coordinate_from_script(scripts.pop(0), state)
        return clicked in destination.positions if clicked else False
    if args.board_backend == "none" or adapter is None:
        return True
    scan_board = getattr(adapter.connection, "scan_board", None)
    if not callable(scan_board):
        return True
    selected = scan_board([position.as_tuple() for position in destination.positions], timeout_s=args.scan_timeout)
    observer.record("board_scan_received", {"phase": "zone_travel_confirmation", "position": list(selected) if selected else None})
    return selected is not None


def _wait_for_scan_or_enter(
    adapter: BoardLedAdapter,
    acceptable: list[tuple[int, int]],
    timeout_s: float | None,
) -> tuple[str, Coordinate | None]:
    result_queue: queue.Queue[tuple[str, Coordinate | None]] = queue.Queue(maxsize=1)

    def scan() -> None:
        try:
            scan_board = getattr(adapter.connection, "scan_board")
            selected = scan_board(acceptable, timeout_s=timeout_s)
            if selected is None:
                result_queue.put(("timeout", None))
                return
            result_queue.put(("click", Coordinate(int(selected[0]), int(selected[1]))))
        except Exception:
            result_queue.put(("timeout", None))

    thread = threading.Thread(target=scan, daemon=True)
    thread.start()
    while thread.is_alive():
        readable, _, _ = select.select([sys.stdin], [], [], 0.1)
        if readable:
            sys.stdin.readline()
            cancel_scan = getattr(adapter.connection, "cancel_scan", None)
            if callable(cancel_scan):
                cancel_scan()
            return "enter", None
        try:
            return result_queue.get_nowait()
        except queue.Empty:
            continue
    try:
        event, selected = result_queue.get_nowait()
    except queue.Empty:
        event, selected = "timeout", None
    if event == "timeout":
        cancel_scan = getattr(adapter.connection, "cancel_scan", None)
        if callable(cancel_scan):
            cancel_scan()
    return event, selected


def _resource_preview_text(resources: tuple[ExplorationResource, ...]) -> str:
    if not resources:
        return "Brak pasujących zasobów."
    items = ", ".join(_resource_summary(resource) for resource in resources)
    return f"Pasujące zasoby: {items}."


def _resource_summary(resource: ExplorationResource) -> str:
    parts = [resource.label]
    if resource.modifier:
        parts.append(_format_modifier(resource.modifier))
    if resource.advantage:
        parts.append("advantage")
    if resource.mitigates_noise:
        parts.append(f"-{resource.mitigates_noise} hałasu")
    if resource.mitigates_complications:
        parts.append(f"łagodzi: {', '.join(resource.mitigates_complications)}")
    return " ".join(parts)


def _select_resource(
    args: argparse.Namespace,
    option: ExplorationChallengeOption,
    resources: tuple[ExplorationResource, ...],
) -> ExplorationResource | None:
    if not resources:
        return None
    overrides = _parse_actor_value_overrides(args.resource_choice, str)
    selected_id = overrides.get(option.id)
    if selected_id:
        return next((resource for resource in resources if resource.id == selected_id), None)
    if args.board_backend == "none":
        return None
    print("Możesz użyć jednego zasobu albo nacisnąć Enter bez zasobu:")
    for resource in resources:
        print(f"- {resource.id}: {_resource_summary(resource)}")
    raw = input("Zasób: ").strip()
    if not raw:
        return None
    return next((resource for resource in resources if resource.id == raw), None)


def _activate_resource(
    args: argparse.Namespace,
    challenge: ExplorationChallenge,
    option: ExplorationChallengeOption,
    resource: ExplorationResource,
    observer: SessionObserver,
) -> None:
    print(f"Aktywowano zasób: {resource.label}.")
    print(f"Efekt zasobu dla podejścia `{option.label}`: {_resource_summary(resource)}.")
    print("Za chwilę wykonacie test z uwzględnieniem tego bonusu.")
    observer.record("resource_used", {"challenge_id": challenge.id, "option_id": option.id, "resource_id": resource.id})
    observer.record(
        "resource_activated",
        {
            "challenge_id": challenge.id,
            "option_id": option.id,
            "resource_id": resource.id,
            "modifier": resource.modifier,
            "advantage": resource.advantage,
            "mitigates_noise": resource.mitigates_noise,
            "mitigates_complications": list(resource.mitigates_complications),
        },
    )
    if args.board_backend != "none" and sys.stdin.isatty():
        input("Naciśnij Enter, aby przejść do testu. ")


def _resource_roll_modifiers(resource: ExplorationResource | None) -> tuple[RollModifier, ...]:
    if resource is None or resource.modifier == 0:
        return ()
    return (
        RollModifier(
            f"Zasób: {resource.label}",
            resource.modifier,
            RollModifierType.ITEM,
            stacking_key=f"resource:{resource.id}",
        ),
    )


def _support_roll_modifiers(state: ExplorationState, option: ExplorationChallengeOption) -> tuple[RollModifier, ...]:
    flag = f"gate_support:{option.id}"
    if not bool(next((value for key, value in state.flags.values if key == flag), False)):
        return ()
    return (
        RollModifier(
            "Przygotowanie przy bramie",
            2,
            RollModifierType.SITUATIONAL,
            stacking_key=flag,
        ),
    )


def _challenge_roll_for_option(args: argparse.Namespace, option_id: str) -> int | None:
    overrides = _parse_actor_value_overrides(args.challenge_roll, int)
    return overrides.get(option_id)


def _visible_point_for_position(state: ExplorationState, position: Coordinate) -> ExplorationPoint | None:
    for point in visible_exploration_points(state.points):
        if position in point.positions:
            return point
    return None


def _handle_exploration_point(
    args: argparse.Namespace,
    state: ExplorationState,
    point,
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
) -> tuple[ExplorationState, tuple[str, ...], int]:
    message = point.description or f"Odnaleziono punkt: {point.name}."
    print(message)
    observer.record("exploration_point_clicked", {"point_id": point.id, "zone_id": point.zone_id})
    new_state = state
    if point.id == "old_camp_tools":
        new_state = grant_resource(state, "saw")
        found_message = "Drużyna zabiera starą piłę. Odblokowuje to nowe podejście przy bramie."
        print(found_message)
        observer.record("resource_found", {"point_id": point.id, "resource_id": "saw"})
        messages = (message, found_message)
    else:
        messages = (message,)
    feedback_events = 0
    if adapter is not None:
        adapter.clear()
        adapter.show_feedback(exploration_setup_feedback(point.positions, point.color))
        feedback_events += 1
        observer.record("led_feedback_sent", {"phase": "exploration_point", "point_id": point.id})
        if args.wait_for_enter:
            _pause_for_led_step(args, message)
    return new_state, messages, feedback_events


def _resolve_search_option(
    args: argparse.Namespace,
    actors: tuple[Actor, ...],
    state: ExplorationState,
    zone: ExplorationZone,
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
) -> tuple[ExplorationState, tuple[str, ...]]:
    if zone.id in state.exhausted_search_zones:
        message = f"Ta strefa była już badana: {zone.name}."
        print(message)
        observer.record("zone_search_exhausted", {"zone_id": zone.id})
        return state, (message,)
    request = D20RollRequest()
    instruction = _party_check_instruction(actors, zone.search_ability, zone.search_skill)
    print(f"Test drużynowy Spostrzegawczości w strefie {zone.name}. {instruction}")
    observer.record("party_check_requested", {"zone_id": zone.id, "dc": zone.search_dc, "actors": [str(actor.id) for actor in actors]})
    rolls = _party_check_inputs(args, actors, request, ability=zone.search_ability, skill=zone.search_skill)
    result = resolve_zone_search(state, zone, rolls)
    print(result.message)
    observer.record(
        "party_check_resolved",
        {
            "zone_id": zone.id,
            "dc": result.party_check.dc,
            "success": result.party_check.success,
            "winner_id": str(result.party_check.winner.id),
            "winning_total": result.party_check.winning_roll.total,
            "rolls": [
                {"actor_id": str(actor.id), "natural_roll": roll.natural_roll, "total": roll.total}
                for actor, roll in result.party_check.rolls
            ],
        },
    )
    if result.party_check.success:
        observer.record("zone_search_revealed", {"zone_id": zone.id, "point_ids": [point.id for point in result.revealed_points]})
        result_state = _apply_search_preparation_bonus(args, result.state, zone, observer)
        if result_state is not result.state:
            result = SearchResult(result_state, result.party_check, result.revealed_points, result.message)
        if adapter is not None and result.revealed_points:
            positions = tuple(position for point in result.revealed_points for position in point.positions)
            adapter.clear()
            adapter.show_feedback(exploration_setup_feedback(positions, LedColor.INTERACTION_SUCCESS))
    else:
        observer.record("zone_search_exhausted", {"zone_id": zone.id})
    return result.state, (result.message,)


def _apply_search_preparation_bonus(
    args: argparse.Namespace,
    state: ExplorationState,
    zone: ExplorationZone,
    observer: SessionObserver,
) -> ExplorationState:
    challenge = challenge_for_zone(state, zone.id)
    if challenge is None or challenge_state_for(state, challenge.id).completed:
        return state
    options = available_challenge_options(state, challenge)
    if not options:
        return state
    selected = random.Random(args.exploration_seed).choice(options)
    flag_key = f"gate_support:{selected.id}"
    new_state = replace(state, flags=set_scene_flag(state.flags, flag_key, True))
    message = f"Przygotowanie pomaga przy podejściu: {selected.label} (+2)."
    print(message)
    observer.record("challenge_support_discovered", {"challenge_id": challenge.id, "option_id": selected.id, "flag_key": flag_key})
    return new_state


def _resolve_check_option(args: argparse.Namespace, actors: tuple[Actor, ...], state: ExplorationState, option: ExplorationOption, observer: SessionObserver) -> tuple[ExplorationState, tuple[str, ...]]:
    actor = next((candidate for candidate in actors if str(candidate.id) == args.leader_id), actors[0])
    ability = option.ability_check.ability if option.ability_check else "wisdom"
    modifiers = option.ability_check.modifiers if option.ability_check else ()
    ability_modifiers = _ability_roll_modifiers(actor, ability)
    modifiers = (*ability_modifiers, *modifiers)
    request = D20RollRequest(modifiers=modifiers)
    if option.allow_help and args.helper_id:
        request = D20RollRequest(mode=RollMode.ADVANTAGE, modifiers=modifiers)
    instruction = roll_instruction(request)
    print(f"Test: {option.label}. {instruction.message}")
    natural_roll = _read_int_or_default(args, f"Wpisz naturalny wynik testu dla {actor.name}: ", 10)
    result = resolve_party_check((PartyCheckInput(actor, natural_roll, request),), option.ability_check.dc)
    flags = state.flags
    if result.success and option.success_flag:
        flags = set_scene_flag(flags, option.success_flag, True)
    if not result.success and option.failure_flag:
        flags = set_scene_flag(flags, option.failure_flag, True)
    if result.success:
        message = option.success_message or option.message or "Test zakończony sukcesem."
    else:
        message = option.failure_message or "Test zakończony porażką."
    print(message)
    observer.record("party_check_resolved", {"option_id": option.id, "success": result.success, "winner_id": str(actor.id), "winning_total": result.winning_roll.total})
    return replace(state, flags=flags), (message,)


def _party_check_inputs(
    args: argparse.Namespace,
    actors: tuple[Actor, ...],
    request: D20RollRequest,
    *,
    ability: str = "wisdom",
    skill: str | None = None,
) -> tuple[PartyCheckInput, ...]:
    overrides = _parse_actor_value_overrides(args.party_check_roll, int)
    result: list[PartyCheckInput] = []
    for actor in actors:
        default_roll = int(overrides.get(str(actor.id), 10))
        natural_roll = _read_int_or_default(args, f"Wpisz naturalny wynik testu dla {actor.name} albo Enter dla {default_roll}: ", default_roll)
        actor_request = D20RollRequest(
            mode=request.mode,
            modifiers=(*_ability_roll_modifiers(actor, ability, skill), *request.modifiers),
        )
        result.append(PartyCheckInput(actor, natural_roll, actor_request))
    return tuple(result)


def _ability_roll_modifiers(actor: Actor, ability: str, skill: str | None = None) -> tuple[RollModifier, ...]:
    score = getattr(actor.ability_scores, ability)
    ability_label = _ABILITY_LABELS.get(ability, ability)
    skill_label = _SKILL_LABELS.get(skill or "", skill)
    label = f"Modyfikator z cechy {ability_label}"
    if skill:
        label = f"Modyfikator {ability_label}/{skill_label}"
    return (RollModifier(label, ability_modifier(score), RollModifierType.ABILITY, stacking_key=f"ability:{ability}"),)


def _party_check_instruction(actors: tuple[Actor, ...], ability: str, skill: str | None = None) -> str:
    modifier_text = ", ".join(
        f"{actor.name} {_format_modifier(_ability_roll_modifiers(actor, ability, skill)[0].value)}"
        for actor in actors
    )
    return f"Każdy bohater rzuca 1d20. Liczy się najwyższy wynik po modyfikatorach. Modyfikatory: {modifier_text}."


def _format_modifier(value: int) -> str:
    return f"+{value}" if value >= 0 else str(value)


_ABILITY_LABELS = {
    "strength": "Siła",
    "dexterity": "Zręczność",
    "constitution": "Kondycja",
    "intelligence": "Inteligencja",
    "wisdom": "Mądrość",
    "charisma": "Charyzma",
}

_SKILL_LABELS = {
    "athletics": "Atletyka",
    "perception": "Spostrzegawczość",
    "survival": "Sztuka przetrwania",
}


def _coordinate_from_script(command: str, state: ExplorationState) -> Coordinate | None:
    command = command.strip()
    if command == "end":
        return None
    if command.startswith("zone:"):
        zone_id = command.removeprefix("zone:")
        zone = next(zone for zone in state.zones if zone.id == zone_id)
        return zone.marker_position
    if command.startswith("tile:"):
        zone_id = command.removeprefix("tile:")
        zone = next(zone for zone in state.zones if zone.id == zone_id)
        return zone.positions[0]
    if command.startswith("point:"):
        point_id = command.removeprefix("point:")
        point = next(point for point in state.points if point.id == point_id)
        return point.positions[0]
    if command.startswith("pos:"):
        col, row = command.removeprefix("pos:").split(",", 1)
        return Coordinate(int(col), int(row))
    raise ValueError(f"Unknown exploration script command: {command!r}.")


def _current_zone(state: ExplorationState) -> ExplorationZone:
    return next(zone for zone in state.zones if zone.id == state.party_position.zone_id)


def _parse_actor_value_overrides(values: Sequence[str], cast):
    result = {}
    for value in values:
        key, raw = value.split("=", 1)
        result[key] = cast(raw)
    return result


def _load_exploration(path: str) -> LoadedExploration:
    return build_exploration_from_scenario(load_scenario(path))


if __name__ == "__main__":
    raise SystemExit(main())
