from __future__ import annotations

import argparse
import queue
import select
import sys
import threading
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from dnd_board_game.actors import Actor
from dnd_board_game.combat import SceneFlags, SetupVisibility, set_scene_flag
from dnd_board_game.exploration import (
    ExplorationOption,
    ExplorationOptionKind,
    ExplorationState,
    ExplorationZone,
    PartyCheckInput,
    SearchResult,
    available_exploration_zones,
    exploration_setup_feedback,
    exploration_zone_feedback,
    option_feedback,
    party_position_feedback,
    resolve_party_check,
    resolve_zone_search,
    set_party_zone,
    visible_exploration_points,
    visible_exploration_zones,
    zone_for_position,
    zone_is_available,
)
from dnd_board_game.hardware import BoardLedAdapter, LedColor, LedFeedback, LedFrame, LedRole
from dnd_board_game.rules import D20RollRequest, RollMode, RollModifier, RollModifierType, ability_modifier, roll_instruction
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
    state = ExplorationState(exploration.zones, exploration.points, exploration.party_position, SceneFlags())
    messages: list[str] = [f"Scenariusz eksploracji: {exploration.scenario_name}."]
    print(messages[-1])
    setup_messages, feedback_events = _run_exploration_setup(args, exploration, state, adapter, observer)
    messages.extend(setup_messages)

    scripts = list(args.exploration_script)
    option_indices: dict[str, int] = {}
    steps = 0
    while steps < args.max_steps:
        steps += 1
        if adapter is not None:
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
        state, option_messages, sent = _handle_zone_options(args, exploration.actors, state, zone, option_indices, adapter, observer, scripts)
        messages.extend(option_messages)
        feedback_events += sent
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

    for zone in available_exploration_zones(state):
        step_message = f"Setup strefy: {zone.name}. Podświetlony obszar oznacza tę lokację. Kliknij dowolne podświetlone pole po ułożeniu mapy."
        print(step_message)
        messages.append(step_message)
        feedback_events += _confirm_setup_step(
            args,
            adapter,
            observer,
            zone.positions,
            zone.color,
            f"exploration_setup_zone:{zone.id}",
            step_message,
            anchor_position=zone.marker_position,
        )

    point_positions = tuple(position for point in visible_exploration_points(state.points) for position in point.positions)
    for batch_index, batch in enumerate(_batched(point_positions, 5), start=1):
        step_message = f"Setup jawnych elementów {batch_index}: kliknij jedno z podświetlonych pól po ustawieniu elementów."
        print(step_message)
        messages.append(step_message)
        feedback_events += _confirm_setup_step(args, adapter, observer, batch, LedColor.INTERACTIVE_OBJECT, "exploration_setup_points", step_message)

    party_message = "Kliknij podświetlony punkt centralny, aby wejść w interakcję z lokacją startową."
    print(party_message)
    messages.append(party_message)
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
    acceptable = [position.as_tuple() for zone in available_exploration_zones(state) for position in zone.positions]
    observer.record("board_scan_requested", {"phase": "exploration_click", "acceptable_positions": [list(position) for position in acceptable]})
    print("Kliknij strefę eksploracji albo puste pole planszy.")
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
    option_indices: dict[str, int],
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
    scripts: list[str],
) -> tuple[ExplorationState, tuple[str, ...], int]:
    if not zone.options:
        message = f"{zone.name}: nie ma teraz dostępnych akcji."
        print(message)
        return state, (message,), 0
    index = option_indices.get(zone.id, 0) % len(zone.options)
    option = zone.options[index]
    message = f"{zone.name}. Wybrano opcję: {option.label}. Kliknij strefę ponownie, aby przełączyć opcję. Naciśnij Enter, aby potwierdzić."
    print(message)
    observer.record("zone_option_previewed", {"zone_id": zone.id, "option_id": option.id, "index": index})
    feedback_events = 0
    if adapter is not None:
        adapter.show_feedback(option_feedback(zone, option))
        feedback_events += 1
        observer.record("led_feedback_sent", {"phase": "zone_option_preview", "zone_id": zone.id, "option_id": option.id})
    action = _confirm_or_cycle_option(args, state, zone, adapter, observer, scripts)
    if action == "cycle":
        option_indices[zone.id] = index + 1
        observer.record("zone_option_cycled", {"zone_id": zone.id, "next_index": option_indices[zone.id] % len(zone.options)})
        return state, (message,), feedback_events
    if action != "confirm":
        return state, (message,), feedback_events
    observer.record("zone_option_confirmed", {"zone_id": zone.id, "option_id": option.id})
    if option.kind == ExplorationOptionKind.SEARCH:
        new_state, search_messages = _resolve_search_option(args, actors, state, zone, adapter, observer)
        return new_state, (message, *search_messages), feedback_events
    if option.kind == ExplorationOptionKind.CHECK and option.ability_check is not None:
        new_state, check_messages = _resolve_check_option(args, actors, state, option, observer)
        return new_state, (message, *check_messages), feedback_events
    option_message = option.message or option.description or f"Wykonano opcję: {option.label}."
    print(option_message)
    return state, (message, option_message), feedback_events


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


def _confirm_or_cycle_option(args: argparse.Namespace, state: ExplorationState, zone: ExplorationZone, adapter: BoardLedAdapter | None, observer: SessionObserver, scripts: list[str]) -> str:
    if scripts:
        command = scripts.pop(0).strip()
        if command == "cycle":
            return "cycle"
        if command == "confirm":
            return "confirm"
        scripts.insert(0, command)
        return "cancel"
    if args.board_backend == "none" or adapter is None:
        return "confirm"
    if not callable(getattr(adapter.connection, "scan_board", None)):
        return "confirm"
    print("Naciśnij Enter, aby potwierdzić opcję, albo kliknij tę strefę ponownie, aby przełączyć opcję.")
    event, selected = _wait_for_scan_or_enter(adapter, [position.as_tuple() for position in zone.positions], args.scan_timeout)
    if event == "click" and selected is not None:
        observer.record("zone_option_cycled", {"zone_id": zone.id, "reason": "scan", "position": list(selected.as_tuple())})
        return "cycle"
    if event == "enter":
        observer.record("zone_option_enter_confirmed", {"zone_id": zone.id})
        return "confirm"
    observer.record("zone_option_confirmation_timeout", {"zone_id": zone.id})
    return "cancel"


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
        if adapter is not None and result.revealed_points:
            positions = tuple(position for point in result.revealed_points for position in point.positions)
            adapter.show_feedback(exploration_setup_feedback(positions, LedColor.INTERACTION_SUCCESS))
    else:
        observer.record("zone_search_exhausted", {"zone_id": zone.id})
    return result.state, (result.message,)


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
    return ExplorationState(state.zones, state.points, state.party_position, flags, state.exhausted_search_zones), (message,)


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
