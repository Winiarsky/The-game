from __future__ import annotations

import argparse
import os
import queue
import select
import sys
import threading
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path

from dnd_board_game.actors import Actor, ability_check_roll_modifiers
from dnd_board_game.combat import SceneFlags, SetupVisibility, objective_status_after_flags, scene_flag, set_scene_flag
from dnd_board_game.exploration import (
    CheckAggregation,
    CheckParticipants,
    ConsequenceTarget,
    ExplorationChallenge,
    ExplorationCheckPlan,
    ExplorationChallengeOption,
    ExplorationPoint,
    ExplorationResource,
    ExplorationState,
    ExplorationZone,
    PartyCheckInput,
    apply_goal_resolution_profile,
    available_challenge_options,
    available_exploration_zones,
    challenge_for_zone,
    challenge_state_for,
    exploration_setup_feedback,
    exploration_zone_feedback,
    grant_resource,
    matching_resources,
    party_position_feedback,
    reveal_exploration_points,
    resolve_challenge_option,
    resolve_exploration_check,
    resolve_party_check,
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


@dataclass(frozen=True, slots=True)
class DeclarationThreadEntry:
    role: str
    content: str
    outcome: str = ""


@dataclass(frozen=True, slots=True)
class RuntimePreparationEffect:
    effect: object
    source_option_id: str


class GmInterpretationDecision(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"
    RECLASSIFY = "reclassify"


def _print_section(title: str, body: str | None = None) -> None:
    print(f"\n\n=== {title} ===")
    if body:
        print(body)


def _print_block(message: str) -> None:
    print(f"\n{message}")


def _print_result(message: str) -> None:
    print(f"\n-> {message}")


def run_demo(
    args: argparse.Namespace,
    *,
    connection_factory: ConnectionFactory | None = None,
    gm_client: object | None = None,
) -> DemoExplorationResult:
    _resolve_gm_classifier_defaults(args)
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
        merchants=exploration.merchants,
    )
    messages: list[str] = [f"Scenariusz eksploracji: {exploration.scenario_name}."]
    _print_section(messages[-1])
    if args.debug_point:
        state, debug_messages, feedback_events = _run_debug_point_interaction(
            args,
            exploration,
            state,
            adapter,
            observer,
            gm_client,
        )
        messages.extend(debug_messages)
        observer.record("session_finished", {"observation_path": str(observer.path)})
        return DemoExplorationResult(tuple(messages), state, observer.path, feedback_events)
    setup_messages, feedback_events = _run_exploration_setup(args, exploration, state, adapter, observer)
    messages.extend(setup_messages)
    for objective in objectives:
        objective_message = f"Cel eksploracji: {objective.name}. {objective.description}".strip()
        _print_section("Cel sceny", objective_message)
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
    freeform_action = args.freeform_action.strip() if args.freeform_action else ""
    freeform_consumed = False
    last_map_prompt_key = _map_prompt_key(state)
    steps = 0
    while steps < args.max_steps:
        steps += 1
        if freeform_action and not freeform_consumed:
            freeform_consumed = True
            state, freeform_messages, _freeform_resolved = _handle_freeform_actions(args, exploration, state, adapter, observer, gm_client)
            objectives = _record_objectives_after_flags(objectives, state.flags, observer)
            messages.extend(freeform_messages)
            if _objectives_completed(objectives):
                _finish_exploration_objectives(observer, messages)
                break
            if args.gm_dry_run:
                observer.record("exploration_finished", {"reason": "gm_dry_run"})
                break
            continue
        if adapter is not None:
            adapter.clear()
            adapter.show_feedback(exploration_zone_feedback(state))
            feedback_events += 1
            observer.record("led_feedback_sent", {"phase": "exploration_map"})
        prompt_key = _map_prompt_key(state)
        if prompt_key != last_map_prompt_key:
            map_prompt = _map_prompt_message(state)
            _print_section("Dostępne lokacje", map_prompt)
            messages.append(map_prompt)
            observer.record(
                "exploration_available_locations_shown",
                {
                    "zone_ids": [zone.id for zone in available_exploration_zones(state)],
                    "point_ids": [point.id for point in visible_exploration_points(state.points)],
                },
            )
            last_map_prompt_key = prompt_key
        clicked = _next_exploration_click(args, state, adapter, observer, scripts)
        if clicked is None:
            message = "Eksploracja zakończona."
            _print_result(message)
            messages.append(message)
            observer.record("exploration_finished", {"reason": "ended_by_user"})
            break
        point = _visible_point_for_position(state, clicked)
        if point is not None:
            state, point_messages, sent = _handle_exploration_point(args, exploration, state, point, adapter, observer, gm_client)
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
            _print_result(message)
            messages.append(message)
            continue
        if zone.id != state.party_position.zone_id:
            state, travel_messages, sent = _handle_zone_travel(args, state, zone, adapter, observer, scripts)
            messages.extend(travel_messages)
            feedback_events += sent
            continue
        if clicked != zone.marker_position:
            message = f"To fragment strefy: {zone.name}. Główne opcje tej lokacji są w podświetlonym punkcie centralnym."
            _print_result(message)
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
        state, option_messages, sent = _handle_zone_options(args, exploration, state, zone, adapter, observer, scripts, gm_client)
        objectives = _record_objectives_after_flags(objectives, state.flags, observer)
        messages.extend(option_messages)
        feedback_events += sent
        if _objectives_completed(objectives):
            _finish_exploration_objectives(observer, messages)
            break
    else:
        message = f"Eksploracja zatrzymana po limicie kroków: {args.max_steps}."
        _print_result(message)
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
    parser.add_argument("--leader-id", default="hero")
    parser.add_argument("--lead-actor", default=None)
    parser.add_argument("--helper-actor", default=None)
    parser.add_argument("--selected-actor", action="append", default=[])
    parser.add_argument("--gm-classifier", choices=("auto", "none", "groq", "gemini"), default="auto")
    parser.add_argument("--freeform-action", default="")
    parser.add_argument("--groq-model", default=None)
    parser.add_argument("--gemini-model", default=None)
    parser.add_argument("--gm-dry-run", action="store_true", default=False)
    parser.add_argument("--gm-accept", choices=("ask", "yes", "no"), default="ask")
    parser.add_argument("--freeform-retries", type=int, default=1)
    parser.add_argument("--interactive-freeform", action="store_true", default=False)
    parser.add_argument("--debug-point", default="", help="Debug: reveal and interact with this exploration point immediately.")
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


def _run_debug_point_interaction(
    args: argparse.Namespace,
    exploration: LoadedExploration,
    state: ExplorationState,
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
    gm_client: object | None,
) -> tuple[ExplorationState, tuple[str, ...], int]:
    point_id = args.debug_point.strip()
    known_point_ids = {point.id for point in state.points}
    if point_id not in known_point_ids:
        raise ValueError(f"Unknown debug exploration point: {point_id}.")
    state, _revealed = reveal_exploration_points(state, (point_id,))
    point = next(point for point in state.points if point.id == point_id)
    zone = next((zone for zone in state.zones if zone.id == point.zone_id), None)
    if zone is None:
        raise ValueError(f"Debug point {point_id} references unknown zone: {point.zone_id}.")
    state = set_party_zone(state, zone)
    message = (
        f"Debug: pomijam setup mapy i przechodzę od razu do punktu `{point.id}` "
        f"w lokacji: {zone.name}."
    )
    _print_section("Debug punktu eksploracji", message)
    observer.record(
        "debug_point_interaction_started",
        {
            "point_id": point.id,
            "point_name": point.name,
            "zone_id": zone.id,
            "zone_name": zone.name,
        },
    )
    state, point_messages, feedback_events = _handle_exploration_point(
        args,
        exploration,
        state,
        point,
        adapter,
        observer,
        gm_client,
    )
    observer.record("debug_point_interaction_finished", {"point_id": point.id})
    return state, (message, *point_messages), feedback_events


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
    _print_section("Setup sceny", message)
    messages.append(message)
    observer.record("exploration_setup_started", {"scenario_id": exploration.scenario_id})

    available_zones = available_exploration_zones(state)
    if available_zones:
        zone_lines = ["Dostępne lokacje:"]
        for zone in available_zones:
            zone_lines.append(f"- {zone.name}: kolor {led_color_name_pl(zone.color)}")
        if _should_auto_select_single_freeform_zone(args, state):
            zone_lines.append("Jest jedna dostępna lokacja, więc przechodzę do niej automatycznie. Zaraz wpiszesz deklarację drużyny.")
        else:
            zone_lines.append("Kliknij odpowiednią lokację, aby wejść w interakcję.")
        zones_message = "\n".join(zone_lines)
        _print_block(zones_message)
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
        _print_block(step_message)
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


def _map_prompt_key(state: ExplorationState) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return (
        tuple(zone.id for zone in available_exploration_zones(state)),
        tuple(point.id for point in visible_exploration_points(state.points)),
    )


def _map_prompt_message(state: ExplorationState) -> str:
    lines: list[str] = []
    zones = available_exploration_zones(state)
    if zones:
        lines.append("Lokacje dostępne teraz:")
        for zone in zones:
            current_marker = " (aktualna)" if zone.id == state.party_position.zone_id else ""
            lines.append(f"- {zone.name}{current_marker}: kolor {led_color_name_pl(zone.color)}")
    points = visible_exploration_points(state.points)
    if points:
        lines.append("Ujawnione punkty:")
        for point in points:
            lines.append(f"- {point.name}: kolor {led_color_name_pl(point.color)}")
    lines.append("Kliknij jedną z dostępnych lokacji albo ujawniony punkt na planszy.")
    return "\n".join(lines)


def _next_exploration_click(args: argparse.Namespace, state: ExplorationState, adapter: BoardLedAdapter | None, observer: SessionObserver, scripts: list[str]) -> Coordinate | None:
    if scripts:
        return _coordinate_from_script(scripts.pop(0), state)
    if _should_auto_select_single_freeform_zone(args, state):
        zone = available_exploration_zones(state)[0]
        observer.record(
            "exploration_zone_auto_selected",
            {"zone_id": zone.id, "position": list(zone.marker_position.as_tuple()), "reason": "single_freeform_zone"},
        )
        return zone.marker_position
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


def _should_auto_select_single_freeform_zone(args: argparse.Namespace, state: ExplorationState) -> bool:
    if args.gm_classifier == "none" or not args.interactive_freeform:
        return False
    zones = available_exploration_zones(state)
    return len(zones) == 1 and zones[0].id == state.party_position.zone_id


def _resolve_gm_classifier_defaults(args: argparse.Namespace) -> None:
    if args.gm_classifier != "auto":
        return
    if args.freeform_action.strip() or args.interactive_freeform:
        provider = os.environ.get("GM_LLM_PROVIDER", "gemini").strip().lower()
    else:
        provider = "none"
    if provider not in {"none", "groq", "gemini"}:
        raise RuntimeError(f"Unsupported GM_LLM_PROVIDER: {provider}. Dozwolone: none, groq, gemini.")
    args.gm_classifier = provider


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
        _print_result(message)
        observer.record("zone_travel_rejected", {"from_zone_id": current.id, "to_zone_id": destination.id, "reason": "not_adjacent"})
        return state, (message,), 0
    message = _zone_travel_preview_message(current, destination)
    _print_section("Przejście między lokacjami", message)
    observer.record("zone_travel_previewed", {"from_zone_id": current.id, "to_zone_id": destination.id})
    feedback_events = 0
    if adapter is not None:
        adapter.show_feedback(
            LedFeedback(
                (
                    LedFrame((current.marker_position,), LedColor.ACTIVE_ACTOR, LedRole.ACTIVE_ACTOR),
                    LedFrame((destination.marker_position,), destination.color, LedRole.DESTINATION),
                )
            )
        )
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
    _print_result(confirm_message)
    if adapter is not None:
        adapter.clear()
        adapter.show_feedback(party_position_feedback(new_state))
        feedback_events += 1
        observer.record("led_feedback_sent", {"phase": "party_position", "zone_id": destination.id})
    return new_state, (message, confirm_message), feedback_events


def _zone_travel_preview_message(current: ExplorationZone, destination: ExplorationZone) -> str:
    lines = [
        f"Wybrana lokacja: {destination.name}.",
    ]
    if destination.description:
        lines.append(destination.description)
    lines.extend(
        [
            "",
            f"Czy chcecie opuścić {current.name} i przejść do: {destination.name}?",
            "Kliknij główny punkt tej lokacji ponownie, aby potwierdzić.",
            "Kliknięcie innej lokacji pokaże jej opis i pytanie o przejście.",
        ]
    )
    return "\n".join(lines)


def _handle_zone_options(
    args: argparse.Namespace,
    exploration: LoadedExploration,
    state: ExplorationState,
    zone: ExplorationZone,
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
    scripts: list[str],
    gm_client: object | None,
) -> tuple[ExplorationState, tuple[str, ...], int]:
    challenge = challenge_for_zone(state, zone.id)
    if challenge is not None and available_challenge_options(state, challenge):
        new_state, challenge_messages, resolved = _handle_challenge_freeform_prompt(
            args,
            exploration,
            state,
            zone,
            challenge,
            adapter,
            observer,
            gm_client,
        )
        if resolved:
            return new_state, challenge_messages, 0
        return state, challenge_messages, 0
    message = f"{zone.name}: nie ma teraz aktywnego wyzwania LLM ani punktu interakcji do obsłużenia."
    _print_result(message)
    observer.record("exploration_zone_has_no_freeform_interaction", {"zone_id": zone.id})
    return state, (message,), 0


def _handle_challenge_freeform_prompt(
    args: argparse.Namespace,
    exploration: LoadedExploration,
    state: ExplorationState,
    zone: ExplorationZone,
    challenge: ExplorationChallenge,
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
    gm_client: object | None,
) -> tuple[ExplorationState, tuple[str, ...], bool]:
    message = _challenge_prompt_message(state, zone, challenge)
    _print_section(f"Wyzwanie: {challenge.name}", message)
    observer.record(
        "challenge_freeform_prompted",
        {
            "zone_id": zone.id,
            "challenge_id": challenge.id,
            "progress": challenge_state_for(state, challenge.id).current_progress,
            "progress_required": challenge.progress_required,
        },
    )
    if args.gm_classifier != "none":
        new_state, freeform_messages, resolved = _handle_freeform_actions(args, exploration, state, adapter, observer, gm_client)
        return new_state, (message, *freeform_messages), resolved
    if args.board_backend != "none" and sys.stdin.isatty():
        _print_block("Wpisz deklarację przez `--gm-classifier gemini --interactive-freeform` albo `--gm-classifier groq --interactive-freeform`.")
    else:
        _print_block("Brak aktywnego klasyfikatora LLM. Uruchom runtime z `--gm-classifier gemini --interactive-freeform` albo podaj `--freeform-action`.")
    return state, (message,), False


def _challenge_prompt_message(
    state: ExplorationState,
    zone: ExplorationZone,
    challenge: ExplorationChallenge,
) -> str:
    challenge_state = challenge_state_for(state, challenge.id)
    lines = [
        f"{zone.name}: {challenge.name}.",
        zone.description or "Przed drużyną jest przeszkoda eksploracyjna.",
    ]
    if challenge.llm_context.summary:
        lines.append(challenge.llm_context.summary)
    if challenge.completion_all_flags or challenge.completion_any_flags:
        lines.append(
            "Przejście zależy od konkretnych zmian stanu przeszkody, nie od punktów postępu."
        )
    else:
        lines.append(
            f"Aby przejść dalej, musicie osiągnąć postęp {challenge.progress_required}. "
            f"Aktualny postęp: {challenge_state.current_progress}/{challenge.progress_required}."
        )
    if challenge_state.noise:
        lines.append(f"Dotychczasowy hałas: {challenge_state.noise}.")
    if challenge_state.complications:
        lines.append(f"Komplikacje: {', '.join(challenge_state.complications)}.")
    if challenge.llm_context.reasonable_approaches:
        lines.append("Sensowne podejścia: " + ", ".join(challenge.llm_context.reasonable_approaches) + ".")
    if challenge.llm_context.risk_notes:
        lines.append("Ryzyka: " + ", ".join(challenge.llm_context.risk_notes) + ".")
    lines.append("Co robi drużyna?")
    return "\n".join(lines)


def _handle_freeform_actions(
    args: argparse.Namespace,
    exploration: LoadedExploration,
    state: ExplorationState,
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
    gm_client: object | None,
) -> tuple[ExplorationState, tuple[str, ...], bool]:
    messages: list[str] = []
    current_action = args.freeform_action.strip()
    max_attempts = max(1, int(args.freeform_retries))
    declaration_thread: list[DeclarationThreadEntry] = []
    active_preparation_effects: list[RuntimePreparationEffect] = []
    for attempt in range(1, max_attempts + 1):
        if not current_action:
            current_action = _read_next_freeform_action(args, attempt)
            if current_action and _last_thread_entry_was_rejected_interpretation(declaration_thread):
                observer.record(
                    "gm_interpretation_corrected",
                    {
                        "attempt": attempt,
                        "correction": current_action,
                        "previous_outcome": _thread_entry_text(declaration_thread[-1]) if declaration_thread else "",
                    },
                )
        if not current_action:
            message = "Nie podano kolejnej deklaracji freeform."
            _print_result(message)
            messages.append(message)
            observer.record("gm_classifier_retry_cancelled", {"attempt": attempt})
            return state, tuple(messages), False
        new_state, attempt_messages, resolved = _handle_freeform_action_once(
            args,
            exploration,
            state,
            adapter,
            observer,
            gm_client,
            current_action,
            attempt,
            tuple(declaration_thread),
            active_preparation_effects,
        )
        messages.extend(attempt_messages)
        state = new_state
        if resolved:
            return new_state, tuple(messages), True
        declaration_thread.append(DeclarationThreadEntry("player", current_action, _thread_outcome_from_messages(attempt_messages)))
        if attempt_messages:
            declaration_thread.append(DeclarationThreadEntry("system", attempt_messages[-1]))
        observer.record(
            "gm_declaration_thread_updated",
            {
                "attempt": attempt,
                "entries": [_declaration_thread_entry_payload(entry) for entry in declaration_thread],
            },
        )
        current_action = ""
        if not args.interactive_freeform:
            return state, tuple(messages), False
    return state, tuple(messages), False


def _handle_freeform_action_once(
    args: argparse.Namespace,
    exploration: LoadedExploration,
    state: ExplorationState,
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
    gm_client: object | None,
    freeform_action: str,
    attempt: int,
    declaration_thread: tuple[DeclarationThreadEntry, ...] = (),
    active_preparation_effects: list[RuntimePreparationEffect] | None = None,
    reclassification_count: int = 0,
) -> tuple[ExplorationState, tuple[str, ...], bool]:
    active_preparation_effects = active_preparation_effects if active_preparation_effects is not None else []
    if args.gm_classifier == "none":
        message = "Freeform action wymaga `--gm-classifier groq` albo `--gm-classifier gemini`."
        _print_result(message)
        observer.record("gm_classifier_proposal_rejected", {"reason": "classifier_disabled"})
        return state, (message,), False
    try:
        (
            build_gm_classifier_request,
            challenge_option_from_validated_proposal,
            declaration_analysis_type,
            validate_gm_declaration_analysis,
            validate_gm_classifier_proposal,
            gm_action_flow,
        ) = _load_gm_classifier_tools()
        request = build_gm_classifier_request(
            scenario_id=exploration.scenario_id,
            scenario_name=exploration.scenario_name,
            scenario_context=exploration.llm_context,
            state=state,
            player_action=freeform_action,
            declaration_thread=_llm_declaration_thread(declaration_thread),
            active_preparation_effects=_llm_preparation_effects(active_preparation_effects),
        )
        observer.record(
            "gm_classifier_requested",
            {
                "provider": args.gm_classifier,
                "model": _gm_model_name(args),
                "player_action": freeform_action,
                "attempt": attempt,
                "payload": request.to_prompt_payload(),
            },
        )
        client = gm_client or _create_gm_classifier_client(args)
        analysis = _analyze_freeform_declaration(client, request)
        analysis = validate_gm_declaration_analysis(analysis, request)
        observer.record(
            "gm_declaration_analyzed",
            {
                "analysis_type": analysis.analysis_type.value,
                "action_flow": analysis.action_flow.value if analysis.action_flow else None,
                "player_message": analysis.player_message,
                "normalized_intent": analysis.normalized_intent,
                "reason": analysis.reason,
                "confidence": analysis.confidence,
                "declared_resources": list(analysis.declared_resources),
                "referenced_existing_resource_ids": list(analysis.referenced_existing_resource_ids),
                "assumed_new_facts": list(analysis.assumed_new_facts),
                "missing_requirements": list(analysis.missing_requirements),
                "attempt": attempt,
            },
        )
        if analysis.analysis_type == declaration_analysis_type.PLAYER_QUESTION:
            message = analysis.player_message or "To jest pytanie o sytuację. Nie wykonuję rzutu ani nie zmieniam stanu sceny."
            _print_section("Odpowiedź MG", message)
            observer.record("player_question_answered", {"message": message, "attempt": attempt})
            return state, (message,), False
        if analysis.analysis_type == declaration_analysis_type.NEEDS_CLARIFICATION:
            message = analysis.player_message or "Doprecyzujcie, co dokładnie próbujecie zrobić."
            _print_section("Doprecyzowanie", message)
            observer.record(
                "gm_declaration_needs_clarification",
                {
                    "message": message,
                    "normalized_intent": analysis.normalized_intent,
                    "attempt": attempt,
                },
            )
            if not analysis.normalized_intent or not _confirm_clarified_intent(args, analysis.normalized_intent, observer, attempt):
                return state, (message,), False
            request = replace(request, player_action=analysis.normalized_intent)
        if analysis.analysis_type == declaration_analysis_type.UNSUPPORTED:
            message = analysis.player_message or "Ta deklaracja nie pasuje do aktualnej sceny."
            _print_section("Deklaracja odrzucona", message)
            observer.record("gm_declaration_unsupported", {"message": message, "attempt": attempt})
            return state, (message,), False
        proposal = client.classify(request)
        observer.record(
            "gm_classifier_response_received",
            {
                "model": getattr(client, "model", _gm_model_name(args)),
                "proposal": proposal.model_dump(mode="json"),
            },
        )
        validated = validate_gm_classifier_proposal(proposal, request)
        if proposal.action_flow == gm_action_flow.PREPARATION:
            updated_state, messages = _record_preparation_effect(
                args,
                state,
                proposal,
                validated.challenge.id,
                active_preparation_effects,
                observer,
            )
            return updated_state, messages, False
        option = apply_goal_resolution_profile(
            challenge_option_from_validated_proposal(validated),
            challenge=validated.challenge,
            selected_goal_id=None,
            player_action=freeform_action,
            state=state,
        )
        resource = validated.resources[0] if validated.resources else None
        observer.record(
            "gm_classifier_proposal_validated",
            {
                "challenge_id": validated.challenge.id,
                "option_id": option.id,
                "label": option.label,
                "ability": option.ability_check.ability,
                "skill": option.ability_check.skill,
                "tool": option.ability_check.tool,
                "dc": option.ability_check.dc,
                "difficulty_tier": proposal.difficulty_tier,
                "difficulty_reason": proposal.difficulty_reason,
                "progress_on_success": option.progress_on_success,
                "progress_on_failure": option.progress_on_failure,
                "approach_tags": list(option.tags),
                "resource_ids": [resource.id for resource in validated.resources],
            },
        )
    except (RuntimeError, KeyError, ValueError) as exc:
        message = f"Nie udało się użyć deklaracji freeform: {exc}"
        _print_section("Deklaracja nie przeszła walidacji", message)
        observer.record(
            "declaration_fact_rejected",
            {
                "reason": str(exc),
                "attempt": attempt,
                "player_action": freeform_action,
            },
        )
        observer.record("gm_classifier_proposal_rejected", {"reason": str(exc), "attempt": attempt})
        retry_message = "Możecie spróbować opisać inne podejście." if args.interactive_freeform else ""
        if retry_message:
            _print_block(retry_message)
            return state, (message, retry_message), False
        return state, (message,), False

    messages: list[str] = []
    if proposal.player_narration:
        _print_section("Narracja MG", proposal.player_narration)
        messages.append(proposal.player_narration)
    applicable_preview_effects = _applicable_preparation_effects(active_preparation_effects, option)
    if proposal.action_flow == gm_action_flow.COMBINED and proposal.preparation_effect is not None:
        pending_effect = RuntimePreparationEffect(proposal.preparation_effect, option.id)
        if set(option.tags).intersection(set(proposal.preparation_effect.target_tags)):
            applicable_preview_effects = (*applicable_preview_effects, pending_effect)
    preview = _challenge_consequence_preview(
        validated.challenge,
        option,
        proposal,
        resource,
        applicable_preview_effects,
    )
    resolution_summary = (
        "rozstrzygnięcie stanowe bez punktów postępu."
        if validated.challenge.completion_all_flags or validated.challenge.completion_any_flags
        else (
            f"postęp przy sukcesie: +{option.progress_on_success}, "
            f"postęp przy porażce: +{option.progress_on_failure}."
        )
    )
    summary = (
        f"Propozycja MG: {option.label}. Test: {option.ability_check.ability}"
        f"{'/' + option.ability_check.skill if option.ability_check.skill else ''}, "
        f"{'narzędzie ' + option.ability_check.tool + ', ' if option.ability_check.tool else ''}"
        f"ST {option.ability_check.dc}, {resolution_summary}"
    )
    if proposal.difficulty_tier:
        summary = f"{summary} Trudność: {proposal.difficulty_tier}."
    if proposal.difficulty_reason:
        summary = f"{summary} Powód ST: {proposal.difficulty_reason}"
    if resource is not None:
        summary = f"{summary} Zasób: {resource.label}."
    _print_section("Propozycja mechaniczna", summary)
    _print_section("Konsekwencje przed rzutem", preview)
    messages.append(summary)
    messages.append(preview)
    observer.record(
        "gm_interpretation_proposed",
        {
            "challenge_id": validated.challenge.id,
            "option_id": option.id,
            "summary": summary,
            "player_narration": proposal.player_narration,
            "gm_notes": proposal.gm_notes,
            "consequence_preview": preview,
            "action_flow": proposal.action_flow.value,
            "difficulty_tier": proposal.difficulty_tier,
            "difficulty_reason": proposal.difficulty_reason,
        },
    )
    decision = _decide_gm_interpretation(
        args,
        observer,
        validated.challenge.id,
        option.id,
        summary,
        _join_explanation(preview, proposal.gm_notes),
    )
    if decision == GmInterpretationDecision.RECLASSIFY:
        if reclassification_count >= 2:
            message = "Osiągnięto limit reinterpretacji tej samej deklaracji. Wpiszcie korektę podejścia."
            _print_result(message)
            messages.append(message)
            return state, tuple(messages), False
        observer.record(
            "gm_interpretation_reclassified",
            {
                "challenge_id": validated.challenge.id,
                "option_id": option.id,
                "reclassification_count": reclassification_count + 1,
            },
        )
        return _handle_freeform_action_once(
            args,
            exploration,
            state,
            adapter,
            observer,
            gm_client,
            freeform_action,
            attempt,
            (
                *declaration_thread,
                DeclarationThreadEntry(
                    "system",
                    _reclassification_context(summary, proposal.player_narration, proposal.gm_notes),
                    "Gracz poprosił o reinterpretację tej samej deklaracji bez zmiany tekstu.",
                ),
            ),
            active_preparation_effects,
            reclassification_count + 1,
        )
    if decision == GmInterpretationDecision.REJECT:
        message = "Odrzucono interpretację MG. Wpiszcie korektę albo doprecyzowanie podejścia."
        _print_result(message)
        messages.append(message)
        return state, tuple(messages), False
    if args.gm_dry_run:
        observer.record("gm_classifier_dry_run_finished", {"challenge_id": validated.challenge.id, "option_id": option.id})
        return state, tuple(messages), True
    combined_effect_messages: tuple[str, ...] = ()
    if proposal.action_flow == gm_action_flow.COMBINED and proposal.preparation_effect is not None:
        combined_effect_messages = _store_preparation_effect(
            proposal.preparation_effect,
            option.id,
            active_preparation_effects,
            observer,
        )
        messages.extend(combined_effect_messages)
    if resource is not None:
        _activate_resource(args, validated.challenge, option, resource, observer)
    temporary_challenge = replace(validated.challenge, options=(option, *validated.challenge.options))
    applicable_effects = _applicable_preparation_effects(active_preparation_effects, option)
    new_state, result_messages = _resolve_challenge_option(
        args,
        exploration.actors,
        state,
        temporary_challenge,
        option,
        resource,
        observer,
        adapter=adapter,
        preparation_effects=applicable_effects,
    )
    new_state = _apply_post_challenge_preparation_effects(
        new_state,
        result_messages,
        applicable_effects,
        observer,
        validated.challenge.id,
        option.id,
        success=_last_challenge_success(new_state, validated.challenge.id),
    )
    _expire_preparation_effects(active_preparation_effects, applicable_effects, observer, validated.challenge.id, option.id)
    observer.record(
        "gm_classifier_option_resolved",
        {
            "challenge_id": validated.challenge.id,
            "option_id": option.id,
            "resource_id": resource.id if resource else None,
        },
    )
    return new_state, (*messages, *result_messages), True


def _read_next_freeform_action(args: argparse.Namespace, attempt: int) -> str:
    if not args.interactive_freeform or not sys.stdin.isatty():
        return ""
    return input(f"Opisz kolejne podejście drużyny ({attempt}/{args.freeform_retries}): ").strip()


def _llm_declaration_thread(entries: tuple[DeclarationThreadEntry, ...]):
    from dnd_board_game.llm import GmDeclarationThreadEntry

    return tuple(GmDeclarationThreadEntry(entry.role, entry.content, entry.outcome) for entry in entries[-8:])


def _llm_preparation_effects(entries: list[RuntimePreparationEffect]):
    return tuple(entry.effect for entry in entries)


def _declaration_thread_entry_payload(entry: DeclarationThreadEntry) -> dict[str, str]:
    return {
        "role": entry.role,
        "content": entry.content,
        "outcome": entry.outcome,
    }


def _thread_entry_text(entry: DeclarationThreadEntry) -> str:
    return entry.outcome or entry.content


def _thread_outcome_from_messages(messages: tuple[str, ...]) -> str:
    if not messages:
        return "Brak wyniku deklaracji."
    for message in messages:
        if message.startswith("Nie udało się użyć deklaracji freeform:"):
            return message
        if "Odrzucono interpretację MG" in message:
            return message
    return messages[-1]


def _last_thread_entry_was_rejected_interpretation(entries: list[DeclarationThreadEntry]) -> bool:
    return bool(entries) and any(
        "Odrzucono interpretację MG" in entry.content or "Odrzucono interpretację MG" in entry.outcome
        for entry in entries[-2:]
    )


def _analyze_freeform_declaration(client: object, request: object):
    analyze = getattr(client, "analyze", None)
    if callable(analyze):
        return analyze(request)
    from dnd_board_game.llm import GmDeclarationAnalysis, GmDeclarationAnalysisType

    return GmDeclarationAnalysis(
        analysis_type=GmDeclarationAnalysisType.PLAUSIBLE,
        player_message="",
        normalized_intent=request.player_action,
        reason="Fake client without analyze(); defaulting to plausible for tests.",
        confidence=1.0,
    )


def _decide_gm_interpretation(
    args: argparse.Namespace,
    observer: SessionObserver,
    challenge_id: str,
    option_id: str,
    summary: str,
    gm_notes: str,
) -> GmInterpretationDecision:
    if args.gm_accept == "yes":
        decision = GmInterpretationDecision.ACCEPT
    elif args.gm_accept == "no":
        decision = GmInterpretationDecision.REJECT
    elif not sys.stdin.isatty():
        decision = GmInterpretationDecision.ACCEPT
    else:
        _print_section("Decyzja terminalowa", "`+` akceptuje, `-` odrzuca, `?` wyjaśnia, `r` prosi o reinterpretację.")
        while True:
            answer = input("Komenda: ").strip().lower()
            if answer in {"+", "akceptuj", "a", "tak", "t"}:
                decision = GmInterpretationDecision.ACCEPT
                break
            if answer in {"-", "odrzuc", "o", "nie", "n"}:
                decision = GmInterpretationDecision.REJECT
                break
            if answer in {"?", "help", "h", "wyjasnij", "wyjaśnij"}:
                _explain_gm_interpretation(observer, challenge_id, option_id, summary, gm_notes)
                continue
            if answer in {"r", "reinterpretuj", "ponow", "ponów"}:
                decision = GmInterpretationDecision.RECLASSIFY
                break
            _print_result("Nieznana komenda. Dostępne: +, -, ?, r.")
    observer.record(
        _gm_decision_event_type(decision),
        {"challenge_id": challenge_id, "option_id": option_id},
    )
    return decision


def _gm_decision_event_type(decision: GmInterpretationDecision) -> str:
    if decision == GmInterpretationDecision.ACCEPT:
        return "gm_interpretation_accepted"
    if decision == GmInterpretationDecision.RECLASSIFY:
        return "gm_interpretation_reclassify_requested"
    return "gm_interpretation_rejected"


def _explain_gm_interpretation(
    observer: SessionObserver,
    challenge_id: str,
    option_id: str,
    summary: str,
    gm_notes: str,
) -> None:
    explanation = gm_notes.strip() if gm_notes.strip() else summary
    _print_section("Wyjaśnienie mechaniczne", explanation)
    observer.record(
        "gm_interpretation_explained",
        {
            "challenge_id": challenge_id,
            "option_id": option_id,
            "summary": summary,
            "gm_notes": gm_notes,
        },
    )


def _reclassification_context(summary: str, player_narration: str, gm_notes: str) -> str:
    parts = [
        "Poprzednia interpretacja została odrzucona albo wymaga ponownej klasyfikacji.",
        f"Poprzednie podsumowanie mechaniczne: {summary}",
    ]
    if player_narration:
        parts.append(f"Poprzednia narracja: {player_narration}")
    if gm_notes:
        parts.append(f"Poprzednie notatki MG: {gm_notes}")
    parts.append("Nie powtarzaj tej samej interpretacji bez zmiany uzasadnienia albo pól mechanicznych.")
    return "\n".join(parts)


def _confirm_clarified_intent(
    args: argparse.Namespace,
    normalized_intent: str,
    observer: SessionObserver,
    attempt: int,
) -> bool:
    if args.gm_accept == "yes":
        accepted = True
    elif args.gm_accept == "no":
        accepted = False
    elif not sys.stdin.isatty():
        accepted = False
    else:
        _print_section(
            "Interpretacja do potwierdzenia",
            f"{normalized_intent}\n\nDecyzja terminalowa: wpisz `+`, żeby użyć tej interpretacji, albo `-`, żeby wrócić do deklaracji.",
        )
        accepted = _read_terminal_decision("Komenda: ", accept_commands={"+", "tak", "t", "akceptuj", "a"}, reject_commands={"-", "nie", "n", "odrzuc", "o"})
    observer.record(
        "gm_declaration_clarification_accepted" if accepted else "gm_declaration_clarification_rejected",
        {"normalized_intent": normalized_intent, "attempt": attempt},
    )
    return accepted


def _read_terminal_decision(
    prompt: str,
    *,
    accept_commands: set[str],
    reject_commands: set[str],
) -> bool:
    while True:
        answer = input(prompt).strip().lower()
        if answer in accept_commands:
            return True
        if answer in reject_commands:
            return False
        _print_result(
            "Nieznana komenda. Dostępne: "
            f"{', '.join(sorted(accept_commands | reject_commands))}."
        )


def _create_gm_classifier_client(args: argparse.Namespace) -> object:
    if args.gm_classifier == "groq":
        try:
            from dnd_board_game.llm import GroqGmClassifierClient
        except ModuleNotFoundError as exc:
            raise RuntimeError("LLM classifier wymaga zależności `pydantic`. Uruchom `pip install -r requirements.txt`.") from exc
        return GroqGmClassifierClient(model=args.groq_model)
    if args.gm_classifier == "gemini":
        try:
            from dnd_board_game.llm import GeminiGmClassifierClient
        except ModuleNotFoundError as exc:
            raise RuntimeError("LLM classifier wymaga zależności `pydantic`. Uruchom `pip install -r requirements.txt`.") from exc
        return GeminiGmClassifierClient(model=args.gemini_model)
    raise RuntimeError(f"Unknown GM classifier: {args.gm_classifier}.")


def _create_npc_interaction_client(args: argparse.Namespace) -> object:
    if args.gm_classifier == "groq":
        try:
            from dnd_board_game.llm import GroqNpcInteractionClient
        except ModuleNotFoundError as exc:
            raise RuntimeError("NPC LLM wymaga zależności `pydantic`. Uruchom `pip install -r requirements.txt`.") from exc
        return GroqNpcInteractionClient(model=args.groq_model)
    if args.gm_classifier == "gemini":
        try:
            from dnd_board_game.llm import GeminiNpcInteractionClient
        except ModuleNotFoundError as exc:
            raise RuntimeError("NPC LLM wymaga zależności `pydantic`. Uruchom `pip install -r requirements.txt`.") from exc
        return GeminiNpcInteractionClient(model=args.gemini_model)
    raise RuntimeError(f"Unknown NPC LLM provider: {args.gm_classifier}.")


def _gm_model_name(args: argparse.Namespace) -> str:
    if args.gm_classifier == "gemini":
        return args.gemini_model or os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
    if args.gm_classifier == "groq":
        return args.groq_model or os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
    return "none"


def _load_gm_classifier_tools():
    try:
        from dnd_board_game.llm import (
            GmActionFlow,
            GmDeclarationAnalysisType,
            build_gm_classifier_request,
            challenge_option_from_validated_proposal,
            validate_gm_declaration_analysis,
            validate_gm_classifier_proposal,
        )
    except ModuleNotFoundError as exc:
        raise RuntimeError("LLM classifier wymaga zależności `pydantic`. Uruchom `pip install -r requirements.txt`.") from exc
    return (
        build_gm_classifier_request,
        challenge_option_from_validated_proposal,
        GmDeclarationAnalysisType,
        validate_gm_declaration_analysis,
        validate_gm_classifier_proposal,
        GmActionFlow,
    )


def _load_npc_interaction_tools():
    try:
        from dnd_board_game.llm import build_npc_interaction_request, validate_npc_interaction_proposal
    except ModuleNotFoundError as exc:
        raise RuntimeError("NPC LLM wymaga zależności `pydantic`. Uruchom `pip install -r requirements.txt`.") from exc
    return build_npc_interaction_request, validate_npc_interaction_proposal


def _npc_interaction_summary(proposal) -> str:
    if proposal.requires_roll:
        skill_text = f"/{proposal.skill}" if proposal.skill else ""
        base = f"Akcja: {proposal.action_type}. Test: {proposal.ability}{skill_text}, ST {proposal.dc}."
    else:
        base = f"Akcja: {proposal.action_type}. Bez rzutu."
    success_flags = ", ".join(change.key for change in proposal.flag_changes_on_success)
    failure_flags = ", ".join(change.key for change in proposal.flag_changes_on_failure)
    info = ", ".join(proposal.revealed_information_ids)
    details = []
    if success_flags:
        details.append(f"flagi przy sukcesie: {success_flags}")
    if failure_flags:
        details.append(f"flagi przy porażce: {failure_flags}")
    if info:
        details.append(f"możliwe informacje: {info}")
    return f"{base} {'; '.join(details)}".strip()


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
    _print_section("Koniec sceny", message)
    messages.append(message)
    observer.record("exploration_finished", {"reason": "objectives_completed"})


def _resolve_challenge_option(
    args: argparse.Namespace,
    actors: tuple[Actor, ...],
    state: ExplorationState,
    challenge: ExplorationChallenge,
    option: ExplorationChallengeOption,
    resource: ExplorationResource | None,
    observer: SessionObserver,
    adapter: BoardLedAdapter | None = None,
    preparation_effects: tuple[RuntimePreparationEffect, ...] = (),
) -> tuple[ExplorationState, tuple[str, ...]]:
    plan = _default_challenge_check_plan(args, option)
    modifiers = (
        *option.ability_check.modifiers,
        *_resource_roll_modifiers(resource),
        *_preparation_roll_modifiers(preparation_effects),
        *_support_roll_modifiers(state, option),
    )
    mode = _roll_mode_for_challenge(resource, preparation_effects)
    request = D20RollRequest(mode=mode, modifiers=modifiers)
    instruction = roll_instruction(request)
    if preparation_effects:
        _print_block("Aktywne przygotowania: " + ", ".join(_preparation_summary(effect) for effect in preparation_effects) + ".")
    _print_section("Test podejścia", f"{option.label}. ST {option.ability_check.dc}. {_check_plan_instruction(actors, plan)} {instruction.message}")
    observer.record("check_plan_created", {"phase": "challenge", "challenge_id": challenge.id, "option_id": option.id, "plan": plan.as_payload()})
    check_inputs = _check_inputs_for_plan(args, actors, request, plan, option_id=option.id)
    check_result = resolve_exploration_check(plan, check_inputs)
    roll = check_result.selected_roll
    actor = check_result.selected_actor
    observer.record("check_resolved", {"phase": "challenge", "challenge_id": challenge.id, "option_id": option.id, **check_result.as_payload()})
    result = resolve_challenge_option(
        state,
        challenge,
        option,
        roll,
        resource,
        negative_effect_reduction=_preparation_negative_effect_reduction(preparation_effects),
        progress_boost_on_success=_preparation_progress_boost(preparation_effects),
    )
    _print_section("Wynik podejścia", result.message)
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
            "check_plan": plan.as_payload(),
            "consequence_actor_ids": [str(actor.id) for actor in check_result.consequence_actors],
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
    final_state, reveal_messages = _reveal_points_for_completed_challenge(args, result.state, challenge, adapter, observer)
    return final_state, (result.message, *reveal_messages)


def _reveal_points_for_completed_challenge(
    args: argparse.Namespace,
    state: ExplorationState,
    challenge: ExplorationChallenge,
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
) -> tuple[ExplorationState, tuple[str, ...]]:
    if not challenge.reveals_on_complete or not challenge_state_for(state, challenge.id).completed:
        return state, ()
    new_state, revealed = reveal_exploration_points(state, challenge.reveals_on_complete)
    messages: list[str] = []
    for point in revealed:
        message = f"Odkrywacie nowy punkt w lokacji: {point.name}."
        _print_section("Nowy punkt odkryty", message)
        messages.append(message)
    if revealed:
        observer.record(
            "exploration_point_revealed",
            {
                "challenge_id": challenge.id,
                "point_ids": [point.id for point in revealed],
                "point_names": [point.name for point in revealed],
            },
        )
        if adapter is not None:
            positions = tuple(position for point in revealed for position in point.positions)
            adapter.clear()
            adapter.show_feedback(exploration_setup_feedback(positions, LedColor.INTERACTION_SUCCESS))
            observer.record("led_feedback_sent", {"phase": "challenge_revealed_points", "challenge_id": challenge.id})
            if args.wait_for_enter:
                _pause_for_led_step(args, messages[-1])
    return new_state, tuple(messages)


def _confirm_zone_click(args: argparse.Namespace, state: ExplorationState, destination: ExplorationZone, adapter: BoardLedAdapter | None, observer: SessionObserver, scripts: list[str]) -> bool:
    if scripts:
        clicked = _coordinate_from_script(scripts.pop(0), state)
        return clicked == destination.marker_position if clicked else False
    if args.board_backend == "none" or adapter is None:
        return True
    scan_board = getattr(adapter.connection, "scan_board", None)
    if not callable(scan_board):
        return True
    selected = scan_board([destination.marker_position.as_tuple()], timeout_s=args.scan_timeout)
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
    resource_lines = ["Możesz użyć jednego zasobu albo nacisnąć Enter bez zasobu:"]
    for resource in resources:
        resource_lines.append(f"- {resource.id}: {_resource_summary(resource)}")
    _print_section("Zasoby pasujące do podejścia", "\n".join(resource_lines))
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
    _print_section(
        "Aktywowano zasób",
        f"{resource.label}\nEfekt zasobu dla podejścia `{option.label}`: {_resource_summary(resource)}.\nZa chwilę wykonacie test z uwzględnieniem tego bonusu.",
    )
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


def _record_preparation_effect(
    args: argparse.Namespace,
    state: ExplorationState,
    proposal,
    challenge_id: str,
    active_preparation_effects: list[RuntimePreparationEffect],
    observer: SessionObserver,
) -> tuple[ExplorationState, tuple[str, ...]]:
    messages: list[str] = []
    if proposal.player_narration:
        _print_section("Narracja MG", proposal.player_narration)
        messages.append(proposal.player_narration)
    summary = _preparation_proposal_summary(proposal)
    _print_section("Propozycja przygotowania", summary)
    messages.append(summary)
    observer.record(
        "gm_interpretation_proposed",
        {
            "challenge_id": challenge_id,
            "option_id": "preparation",
            "summary": summary,
            "player_narration": proposal.player_narration,
            "gm_notes": proposal.gm_notes,
            "action_flow": proposal.action_flow.value,
        },
    )
    decision = _decide_gm_interpretation(args, observer, challenge_id, "preparation", summary, proposal.gm_notes)
    if decision != GmInterpretationDecision.ACCEPT:
        message = "Odrzucono interpretację MG. Wpiszcie korektę albo doprecyzowanie podejścia."
        _print_result(message)
        messages.append(message)
        return state, tuple(messages)
    updated_state, stored_messages = _apply_or_store_preparation_effect(
        state,
        proposal.preparation_effect,
        "preparation",
        active_preparation_effects,
        observer,
        challenge_id,
    )
    messages.extend(stored_messages)
    return updated_state, tuple(messages)


def _apply_or_store_preparation_effect(
    state: ExplorationState,
    effect,
    source_option_id: str,
    active_preparation_effects: list[RuntimePreparationEffect],
    observer: SessionObserver,
    challenge_id: str,
) -> tuple[ExplorationState, tuple[str, ...]]:
    if effect is not None and effect.type.value in {"grant_resource", "unlock_option"}:
        return _apply_immediate_preparation_effect(state, effect, source_option_id, observer, challenge_id)
    return state, _store_preparation_effect(effect, source_option_id, active_preparation_effects, observer)


def _apply_immediate_preparation_effect(
    state: ExplorationState,
    effect,
    source_option_id: str,
    observer: SessionObserver,
    challenge_id: str,
) -> tuple[ExplorationState, tuple[str, ...]]:
    if effect is None:
        return state, ()
    if effect.type.value == "grant_resource" and getattr(effect, "resource_id", None):
        updated = grant_resource(state, effect.resource_id)
        message = f"Zasób dodany do ekwipunku: {effect.resource_id}."
        _print_result(message)
        observer.record(
            "resource_granted",
            {
                "challenge_id": challenge_id,
                "option_id": source_option_id,
                "resource_id": effect.resource_id,
                "source": effect.source,
            },
        )
        observer.record(
            "preparation_effect_created",
            {
                "source_option_id": source_option_id,
                "type": effect.type.value,
                "label": effect.label,
                "target_tags": list(effect.target_tags),
                "value": effect.value,
                "duration": effect.duration.value,
                "source": effect.source,
                "resource_id": effect.resource_id,
                "option_id": getattr(effect, "option_id", None),
                "applied_immediately": True,
            },
        )
        return updated, (message,)
    if effect.type.value == "unlock_option" and getattr(effect, "option_id", None):
        flag = _llm_unlocked_option_flag(effect.option_id)
        updated = replace(state, flags=set_scene_flag(state.flags, flag, True))
        message = f"Odblokowano podejście: {effect.option_id}."
        _print_result(message)
        observer.record(
            "option_unlocked",
            {
                "challenge_id": challenge_id,
                "option_id": source_option_id,
                "unlocked_option_id": effect.option_id,
                "flag": flag,
                "source": effect.source,
            },
        )
        observer.record(
            "preparation_effect_created",
            {
                "source_option_id": source_option_id,
                "type": effect.type.value,
                "label": effect.label,
                "target_tags": list(effect.target_tags),
                "value": effect.value,
                "duration": effect.duration.value,
                "source": effect.source,
                "resource_id": getattr(effect, "resource_id", None),
                "option_id": effect.option_id,
                "applied_immediately": True,
            },
        )
        return updated, (message,)
    return state, _store_preparation_effect(effect, source_option_id, [], observer)


def _store_preparation_effect(
    effect,
    source_option_id: str,
    active_preparation_effects: list[RuntimePreparationEffect],
    observer: SessionObserver,
) -> tuple[str, ...]:
    entry = RuntimePreparationEffect(effect, source_option_id)
    active_preparation_effects.append(entry)
    message = f"Przygotowanie zapisane: {effect.label}. Zadziała przy następnej pasującej próbie."
    _print_result(message)
    observer.record(
        "preparation_effect_created",
        {
            "source_option_id": source_option_id,
            "type": effect.type.value,
            "label": effect.label,
            "target_tags": list(effect.target_tags),
            "value": effect.value,
            "duration": effect.duration.value,
            "source": effect.source,
            "resource_id": getattr(effect, "resource_id", None),
            "option_id": getattr(effect, "option_id", None),
        },
    )
    return (message,)


def _preparation_proposal_summary(proposal) -> str:
    effect = proposal.preparation_effect
    if effect is None:
        return "Propozycja MG: przygotowanie bez opisanego efektu."
    effect_kind = _preparation_effect_kind_pl(effect)
    target = f", tagi: {', '.join(effect.target_tags)}" if effect.target_tags else ""
    extra = ""
    if getattr(effect, "resource_id", None):
        extra = f", zasób: {effect.resource_id}"
    if getattr(effect, "option_id", None):
        extra = f", opcja: {effect.option_id}"
    return (
        f"Propozycja MG: przygotowanie `{effect.label}`. "
        f"Efekt: {effect_kind} {effect.value}{target}{extra}."
    )


def _applicable_preparation_effects(
    active_preparation_effects: list[RuntimePreparationEffect],
    option: ExplorationChallengeOption,
) -> tuple[RuntimePreparationEffect, ...]:
    option_tags = set(option.tags)
    return tuple(
        entry
        for entry in active_preparation_effects
        if option_tags.intersection(set(entry.effect.target_tags))
    )


def _expire_preparation_effects(
    active_preparation_effects: list[RuntimePreparationEffect],
    applied_effects: tuple[RuntimePreparationEffect, ...],
    observer: SessionObserver,
    challenge_id: str,
    option_id: str,
) -> None:
    for effect in applied_effects:
        observer.record(
            "preparation_effect_applied",
            {
                "challenge_id": challenge_id,
                "option_id": option_id,
                "label": effect.effect.label,
                "type": effect.effect.type.value,
                "target_tags": list(effect.effect.target_tags),
                "value": effect.effect.value,
                "resource_id": getattr(effect.effect, "resource_id", None),
                "option_id": getattr(effect.effect, "option_id", None),
            },
        )
        if effect in active_preparation_effects:
            active_preparation_effects.remove(effect)
        observer.record(
            "preparation_effect_expired",
            {
                "challenge_id": challenge_id,
                "option_id": option_id,
                "label": effect.effect.label,
                "duration": effect.effect.duration.value,
            },
        )


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


def _preparation_roll_modifiers(effects: tuple[RuntimePreparationEffect, ...]) -> tuple[RollModifier, ...]:
    modifiers: list[RollModifier] = []
    for entry in effects:
        effect = entry.effect
        if effect.type.value != "modifier" or effect.value == 0:
            continue
        modifiers.append(
            RollModifier(
                f"Przygotowanie: {effect.label}",
                effect.value,
                RollModifierType.SITUATIONAL,
                stacking_key=f"preparation:{effect.label}:{','.join(effect.target_tags)}",
            )
        )
    return tuple(modifiers)


def _preparation_negative_effect_reduction(effects: tuple[RuntimePreparationEffect, ...]) -> int:
    return sum(effect.effect.value for effect in effects if effect.effect.type.value == "reduce_negative_effect")


def _preparation_progress_boost(effects: tuple[RuntimePreparationEffect, ...]) -> int:
    return sum(effect.effect.value for effect in effects if effect.effect.type.value == "effect_boost")


def _roll_mode_for_challenge(
    resource: ExplorationResource | None,
    effects: tuple[RuntimePreparationEffect, ...],
) -> RollMode:
    has_advantage = resource is not None and resource.advantage
    has_disadvantage = False
    for entry in effects:
        if entry.effect.type.value == "advantage":
            has_advantage = True
        if entry.effect.type.value == "disadvantage":
            has_disadvantage = True
    if has_advantage and not has_disadvantage:
        return RollMode.ADVANTAGE
    if has_disadvantage and not has_advantage:
        return RollMode.DISADVANTAGE
    return RollMode.NORMAL


def _preparation_summary(entry: RuntimePreparationEffect) -> str:
    effect = entry.effect
    if effect.type.value == "modifier":
        return f"{effect.label} +{effect.value}"
    if effect.type.value == "reduce_negative_effect":
        return f"{effect.label} -{effect.value} negatywnego efektu"
    if effect.type.value == "advantage":
        return f"{effect.label} przewaga"
    if effect.type.value == "disadvantage":
        return f"{effect.label} utrudnienie"
    if effect.type.value == "effect_boost":
        return f"{effect.label} +{effect.value} postępu przy sukcesie"
    if effect.type.value == "grant_resource":
        return f"{effect.label} może dać zasób {getattr(effect, 'resource_id', '')}"
    if effect.type.value == "unlock_option":
        return f"{effect.label} może odblokować opcję {getattr(effect, 'option_id', '')}"
    return effect.label


def _preparation_effect_kind_pl(effect) -> str:
    names = {
        "modifier": "modyfikator",
        "reduce_negative_effect": "redukcja negatywnego efektu",
        "advantage": "przewaga",
        "disadvantage": "utrudnienie",
        "effect_boost": "wzmocnienie efektu",
        "grant_resource": "przyznanie zasobu",
        "unlock_option": "odblokowanie opcji",
    }
    return names.get(effect.type.value, effect.type.value)


def _apply_post_challenge_preparation_effects(
    state: ExplorationState,
    result_messages: tuple[str, ...],
    effects: tuple[RuntimePreparationEffect, ...],
    observer: SessionObserver,
    challenge_id: str,
    option_id: str,
    *,
    success: bool,
) -> ExplorationState:
    del result_messages
    if not success:
        return state
    updated = state
    for entry in effects:
        effect = entry.effect
        if effect.type.value == "grant_resource" and getattr(effect, "resource_id", None):
            before = set(updated.inventory_resource_ids)
            updated = grant_resource(updated, effect.resource_id)
            if effect.resource_id not in before:
                _print_result(f"Zasób dodany do ekwipunku: {effect.resource_id}.")
                observer.record(
                    "resource_granted",
                    {
                        "challenge_id": challenge_id,
                        "option_id": option_id,
                        "resource_id": effect.resource_id,
                        "source": effect.source,
                    },
                )
        if effect.type.value == "unlock_option" and getattr(effect, "option_id", None):
            flag = _llm_unlocked_option_flag(effect.option_id)
            updated = replace(updated, flags=set_scene_flag(updated.flags, flag, True))
            _print_result(f"Odblokowano podejście: {effect.option_id}.")
            observer.record(
                "option_unlocked",
                {
                    "challenge_id": challenge_id,
                    "option_id": option_id,
                    "unlocked_option_id": effect.option_id,
                    "flag": flag,
                    "source": effect.source,
                },
            )
    return updated


def _last_challenge_success(state: ExplorationState, challenge_id: str) -> bool:
    current = challenge_state_for(state, challenge_id)
    if not current.attempts:
        return False
    return current.attempts[-1].success


def _llm_unlocked_option_flag(option_id: str) -> str:
    return f"llm_unlocked_option:{option_id}"


def _challenge_consequence_preview(
    challenge: ExplorationChallenge,
    option: ExplorationChallengeOption,
    proposal,
    resource: ExplorationResource | None,
    preparation_effects: tuple[RuntimePreparationEffect, ...],
) -> str:
    boost = _preparation_progress_boost(preparation_effects)
    reduction = _preparation_negative_effect_reduction(preparation_effects)
    success_progress = option.progress_on_success + boost
    failure_noise = max(0, option.failure_noise - reduction)
    critical_noise = max(0, option.critical_failure_noise - reduction)
    uses_flag_completion = bool(challenge.completion_all_flags or challenge.completion_any_flags)
    progress_success = "" if uses_flag_completion else f"; postęp +{success_progress}"
    progress_failure = "" if uses_flag_completion else f"; postęp +{option.progress_on_failure}"
    lines = [
        "Preview konsekwencji:",
        f"- Krytyczny sukces: {option.critical_success_message or option.success_message or 'pełny sukces'}{progress_success}.",
        f"- Sukces: {option.success_message or 'sukces'}{progress_success}.",
        f"- Porażka: {option.failure_message or 'fail-forward'}{progress_failure}; hałas +{failure_noise}.",
        f"- Krytyczna porażka: {option.critical_failure_message or option.failure_message or 'poważniejsza komplikacja'}"
        f"{progress_failure}; hałas +{critical_noise}.",
    ]
    if proposal.difficulty_tier:
        lines.insert(1, f"- Trudność: {proposal.difficulty_tier}, ST {option.ability_check.dc}.")
    if resource is not None:
        lines.append(f"- Zasób przy teście: {_resource_summary(resource)}.")
    if preparation_effects:
        lines.append("- Aktywne przygotowania: " + ", ".join(_preparation_summary(effect) for effect in preparation_effects) + ".")
    complications = tuple(
        item
        for item in (
            option.success_complication,
            option.failure_complication,
            option.critical_failure_complication,
        )
        if item
    )
    if complications:
        lines.append("- Możliwe komplikacje: " + ", ".join(dict.fromkeys(complications)) + ".")
    return "\n".join(lines)


def _join_explanation(preview: str, gm_notes: str) -> str:
    if gm_notes.strip():
        return f"{preview}\nNotatki MG: {gm_notes.strip()}"
    return preview



def _support_roll_modifiers(state: ExplorationState, option: ExplorationChallengeOption) -> tuple[RollModifier, ...]:
    flag = f"challenge_support:{option.id}"
    legacy_flag = f"gate_support:{option.id}"
    if not bool(next((value for key, value in state.flags.values if key in {flag, legacy_flag}), False)):
        return ()
    return (
        RollModifier(
            "Przygotowanie do wyzwania",
            2,
            RollModifierType.SITUATIONAL,
            stacking_key=flag,
        ),
    )


def _challenge_roll_for_option(args: argparse.Namespace, option_id: str) -> int | None:
    overrides = _parse_actor_value_overrides(args.challenge_roll, int)
    return overrides.get(option_id, overrides.get("gm_generated"))


def _visible_point_for_position(state: ExplorationState, position: Coordinate) -> ExplorationPoint | None:
    for point in visible_exploration_points(state.points):
        if position in point.positions:
            return point
    return None


def _handle_exploration_point(
    args: argparse.Namespace,
    exploration: LoadedExploration,
    state: ExplorationState,
    point: ExplorationPoint,
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
    gm_client: object | None = None,
) -> tuple[ExplorationState, tuple[str, ...], int]:
    message = point.description or f"Odnaleziono punkt: {point.name}."
    _print_section(f"Punkt eksploracji: {point.name}", message)
    observer.record("exploration_point_clicked", {"point_id": point.id, "zone_id": point.zone_id})
    new_state = state
    if point.id == "old_camp_tools":
        new_state = grant_resource(state, "saw")
        found_message = "Drużyna zabiera starą piłę. Odblokowuje to nowe podejście przy bramie."
        _print_result(found_message)
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
    if point.npc_interaction is not None:
        new_state, npc_messages = _handle_npc_interaction(args, exploration, new_state, point, observer, gm_client)
        messages = (*messages, *npc_messages)
    return new_state, messages, feedback_events


def _handle_npc_interaction(
    args: argparse.Namespace,
    exploration: LoadedExploration,
    state: ExplorationState,
    point: ExplorationPoint,
    observer: SessionObserver,
    gm_client: object | None,
) -> tuple[ExplorationState, tuple[str, ...]]:
    npc = point.npc_interaction
    if npc is None:
        return state, ()
    intro = npc.dialogue_intro or npc.public_description
    _print_section(f"NPC: {npc.name}", intro)
    observer.record(
        "npc_interaction_started",
        {
            "point_id": point.id,
            "zone_id": point.zone_id,
            "npc_name": npc.name,
            "capabilities": list(npc.capabilities),
        },
    )
    if args.gm_classifier == "none":
        message = "Interakcje NPC przez LLM wymagają `--gm-classifier gemini` albo `--gm-classifier groq`."
        _print_result(message)
        return state, (intro, message)
    if args.freeform_action.strip():
        player_action = args.freeform_action.strip()
    elif args.interactive_freeform and sys.stdin.isatty():
        player_action = input("Co robicie wobec NPC?: ").strip()
    else:
        message = "Brak deklaracji wobec NPC. Użyj `--interactive-freeform` albo `--freeform-action`."
        _print_result(message)
        return state, (intro, message)
    if not player_action:
        message = "Nie podano deklaracji wobec NPC."
        _print_result(message)
        return state, (intro, message)
    try:
        (
            build_npc_interaction_request,
            validate_npc_interaction_proposal,
        ) = _load_npc_interaction_tools()
        zone = next(zone for zone in exploration.zones if zone.id == point.zone_id)
        request = build_npc_interaction_request(
            scenario_id=exploration.scenario_id,
            scenario_name=exploration.scenario_name,
            zone=zone,
            point=point,
            state=state,
            player_action=player_action,
        )
        observer.record(
            "npc_interaction_requested",
            {
                "provider": args.gm_classifier,
                "model": _gm_model_name(args),
                "point_id": point.id,
                "player_action": player_action,
                "payload": request.to_prompt_payload(),
            },
        )
        client = gm_client or _create_npc_interaction_client(args)
        if not hasattr(client, "interact_npc"):
            client = _create_npc_interaction_client(args)
        proposal = client.interact_npc(request)
        observer.record("npc_interaction_response_received", {"proposal": proposal.model_dump(mode="json")})
        validated = validate_npc_interaction_proposal(proposal, request)
    except (RuntimeError, KeyError, ValueError) as exc:
        message = f"Nie udało się użyć interakcji NPC: {exc}"
        _print_section("Interakcja NPC odrzucona", message)
        observer.record("npc_interaction_rejected", {"point_id": point.id, "reason": str(exc)})
        return state, (intro, message)

    proposal = validated.proposal
    messages: list[str] = [intro]
    if proposal.player_narration:
        _print_section("Narracja MG", proposal.player_narration)
        messages.append(proposal.player_narration)
    if proposal.npc_response:
        _print_section("Odpowiedź NPC", proposal.npc_response)
        messages.append(proposal.npc_response)
    summary = _npc_interaction_summary(proposal)
    _print_section("Propozycja interakcji", summary)
    messages.append(summary)
    decision = _decide_gm_interpretation(
        args,
        observer,
        point.id,
        proposal.action_type,
        summary,
        proposal.gm_notes,
    )
    if decision != GmInterpretationDecision.ACCEPT:
        message = "Odrzucono interpretację NPC. Kliknij punkt lub wpisz deklarację ponownie."
        _print_result(message)
        messages.append(message)
        observer.record("npc_interaction_interpretation_rejected", {"point_id": point.id, "action_type": proposal.action_type})
        return state, tuple(messages)

    new_state = state
    success = True
    roll_payload = None
    if proposal.requires_roll:
        assert proposal.ability is not None and proposal.dc is not None
        plan = _default_npc_check_plan(args, proposal)
        instruction = _check_plan_instruction(exploration.actors, plan)
        _print_section(
            "Test przy NPC",
            f"{proposal.action_type}. ST {proposal.dc}. {instruction}",
        )
        observer.record("check_plan_created", {"phase": "npc", "point_id": point.id, "action_type": proposal.action_type, "plan": plan.as_payload()})
        rolls = _check_inputs_for_plan(args, exploration.actors, D20RollRequest(), plan)
        result = resolve_exploration_check(plan, rolls)
        success = result.success
        roll_payload = {
            "dc": result.plan.dc,
            "success": result.success,
            "winner_id": str(result.selected_actor.id),
            "winning_total": result.selected_roll.total,
            "selected_actor_id": str(result.selected_actor.id),
            "selected_total": result.selected_roll.total,
            "successful_actor_ids": [str(actor.id) for actor in result.successful_actors],
            "failed_actor_ids": [str(actor.id) for actor in result.failed_actors],
            "consequence_actor_ids": [str(actor.id) for actor in result.consequence_actors],
            "check_plan": result.plan.as_payload(),
            "rolls": [
                {"actor_id": str(actor.id), "natural_roll": roll.natural_roll, "total": roll.total}
                for actor, roll in result.rolls
            ],
        }
        result_message = proposal.success_message if success else proposal.failure_message
        if not result_message:
            result_message = "Test przy NPC zakończony sukcesem." if success else "Test przy NPC nie wychodzi czysto."
        _print_section("Wynik interakcji NPC", result_message)
        messages.append(result_message)
        observer.record("npc_check_resolved", {"point_id": point.id, **roll_payload})
        observer.record("check_resolved", {"phase": "npc", "point_id": point.id, **result.as_payload()})
    changes = proposal.flag_changes_on_success if success else proposal.flag_changes_on_failure
    for change in changes:
        new_state = replace(new_state, flags=set_scene_flag(new_state.flags, change.key, change.value))
        observer.record("npc_flag_set", {"point_id": point.id, "key": change.key, "value": change.value, "success": success})
    revealed_messages: list[str] = []
    for info_id in proposal.revealed_information_ids:
        info = next(item for item in npc.locked_information if item.id == info_id)
        if all(scene_flag(new_state.flags, flag, False) for flag in info.reveal_if_flags):
            for flag in info.sets_flags:
                new_state = replace(new_state, flags=set_scene_flag(new_state.flags, flag, True))
                observer.record("npc_flag_set", {"point_id": point.id, "key": flag, "value": True, "source": info_id})
            _print_section(f"Informacja: {info.label}", info.text)
            revealed_messages.append(info.text)
            observer.record("npc_information_revealed", {"point_id": point.id, "information_id": info.id})
    messages.extend(revealed_messages)
    observer.record(
        "npc_interaction_finished",
        {"point_id": point.id, "action_type": proposal.action_type, "success": success, "roll": roll_payload},
    )
    return new_state, tuple(messages)


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


def _lead_actor_id(args: argparse.Namespace) -> str:
    return str(args.lead_actor or args.leader_id)


def _actor_by_id(actors: tuple[Actor, ...], actor_id: str | None) -> Actor | None:
    if not actor_id:
        return None
    return next((actor for actor in actors if str(actor.id) == str(actor_id)), None)


def _check_actors_for_plan(
    actors: tuple[Actor, ...],
    plan: ExplorationCheckPlan,
) -> tuple[Actor, ...]:
    if plan.participants == CheckParticipants.WHOLE_PARTY:
        return actors
    if plan.participants == CheckParticipants.SELECTED_ACTORS:
        selected = tuple(actor for actor in actors if str(actor.id) in set(plan.selected_actor_ids))
        return selected or actors
    lead = _actor_by_id(actors, plan.lead_actor_id) or actors[0]
    if plan.participants == CheckParticipants.LEAD_WITH_HELP:
        helper = _actor_by_id(actors, plan.helper_actor_id)
        if helper is not None and helper != lead:
            return (lead, helper)
    return (lead,)


def _check_inputs_for_plan(
    args: argparse.Namespace,
    actors: tuple[Actor, ...],
    request: D20RollRequest,
    plan: ExplorationCheckPlan,
    *,
    option_id: str | None = None,
) -> tuple[PartyCheckInput, ...]:
    overrides = _parse_actor_value_overrides(args.party_check_roll, int)
    challenge_roll = _challenge_roll_for_option(args, option_id) if option_id else None
    result: list[PartyCheckInput] = []
    plan_actors = _check_actors_for_plan(actors, plan)
    for index, actor in enumerate(plan_actors):
        default_roll = int(overrides.get(str(actor.id), challenge_roll if challenge_roll is not None and index == 0 else 10))
        natural_roll = _read_int_or_default(args, f"Wpisz naturalny wynik testu dla {actor.name} albo Enter dla {default_roll}: ", default_roll)
        actor_request = D20RollRequest(
            mode=request.mode,
            modifiers=(*_ability_roll_modifiers(actor, plan.ability, plan.skill, plan.tool), *request.modifiers),
        )
        result.append(PartyCheckInput(actor, natural_roll, actor_request))
    return tuple(result)


def _default_challenge_check_plan(
    args: argparse.Namespace,
    option: ExplorationChallengeOption,
) -> ExplorationCheckPlan:
    return ExplorationCheckPlan(
        participants=option.check_participants or CheckParticipants.SINGLE_ACTOR,
        aggregation=option.check_aggregation or CheckAggregation.LEAD_RESULT,
        consequence_targets=option.consequence_targets or (ConsequenceTarget.LEAD_ACTOR, ConsequenceTarget.SCENE),
        lead_actor_id=_lead_actor_id(args),
        helper_actor_id=args.helper_actor,
        selected_actor_ids=tuple(args.selected_actor),
        ability=option.ability_check.ability,
        skill=option.ability_check.skill,
        tool=option.ability_check.tool,
        dc=option.ability_check.dc,
        reason_for_players=option.description,
    )


def _default_npc_check_plan(
    args: argparse.Namespace,
    proposal,
) -> ExplorationCheckPlan:
    participants = proposal.check_participants
    aggregation = proposal.check_aggregation
    consequence_targets = proposal.consequence_targets
    if participants is None:
        if proposal.action_type in {"medical"}:
            participants = CheckParticipants.LEAD_WITH_HELP
        elif proposal.action_type in {"search"}:
            participants = CheckParticipants.WHOLE_PARTY
        else:
            participants = CheckParticipants.SINGLE_ACTOR
    if aggregation is None:
        aggregation = CheckAggregation.HIGHEST if participants == CheckParticipants.WHOLE_PARTY else CheckAggregation.LEAD_RESULT
    if not consequence_targets:
        if proposal.action_type in {"medical", "social", "information"}:
            consequence_targets = (ConsequenceTarget.NPC,)
        elif proposal.action_type in {"theft", "harm", "intimidation"}:
            consequence_targets = (ConsequenceTarget.LEAD_ACTOR, ConsequenceTarget.NPC)
        else:
            consequence_targets = (ConsequenceTarget.SCENE,)
    return ExplorationCheckPlan(
        participants=participants,
        aggregation=aggregation,
        consequence_targets=tuple(consequence_targets),
        lead_actor_id=_lead_actor_id(args),
        helper_actor_id=args.helper_actor,
        selected_actor_ids=tuple(args.selected_actor),
        ability=proposal.ability or "wisdom",
        skill=proposal.skill,
        dc=proposal.dc or 10,
        reason_for_players=proposal.player_narration,
    )


def _check_plan_instruction(actors: tuple[Actor, ...], plan: ExplorationCheckPlan) -> str:
    actor_names = ", ".join(actor.name for actor in _check_actors_for_plan(actors, plan))
    participants_text = {
        CheckParticipants.SINGLE_ACTOR: f"test wykonuje jedna postać: {actor_names}",
        CheckParticipants.LEAD_WITH_HELP: f"test wykonuje prowadzący z pomocą: {actor_names}",
        CheckParticipants.WHOLE_PARTY: "rzuca cała drużyna",
        CheckParticipants.SELECTED_ACTORS: f"rzucają wybrane postacie: {actor_names}",
    }[plan.participants]
    aggregation_text = {
        CheckAggregation.LEAD_RESULT: "liczy się wynik prowadzącego",
        CheckAggregation.HIGHEST: "liczy się najwyższy wynik",
        CheckAggregation.LOWEST: "liczy się najniższy wynik",
        CheckAggregation.MAJORITY: "sukces wymaga co najmniej połowy zdanych testów",
        CheckAggregation.ALL_MUST_SUCCEED: "wszyscy muszą zdać",
        CheckAggregation.ANY_SUCCESS: "wystarczy jeden sukces",
        CheckAggregation.SUM_PROGRESS: "każdy sukces dokłada postęp",
    }[plan.aggregation]
    consequence_text = ", ".join(target.value for target in plan.consequence_targets) or "brak"
    modifier_text = ", ".join(
        f"{actor.name} {_format_modifier(roll_instruction(D20RollRequest(modifiers=_ability_roll_modifiers(actor, plan.ability, plan.skill, plan.tool))).breakdown.modifier_total)}"
        for actor in _check_actors_for_plan(actors, plan)
    )
    return (
        f"{participants_text}; {aggregation_text}. "
        f"Konsekwencje porażki: {consequence_text}. Modyfikatory: {modifier_text}."
    )


def _ability_roll_modifiers(
    actor: Actor,
    ability: str,
    skill: str | None = None,
    tool: str | None = None,
) -> tuple[RollModifier, ...]:
    return ability_check_roll_modifiers(actor, ability, skill=skill, tool=tool)


def _party_check_instruction(actors: tuple[Actor, ...], ability: str, skill: str | None = None) -> str:
    modifier_text = ", ".join(
        f"{actor.name} {_format_modifier(roll_instruction(D20RollRequest(modifiers=_ability_roll_modifiers(actor, ability, skill))).breakdown.modifier_total)}"
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
