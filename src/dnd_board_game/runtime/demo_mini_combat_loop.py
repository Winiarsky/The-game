from __future__ import annotations

import argparse
import random
import sys
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from dnd_board_game.actors import Actor, Faction
from dnd_board_game.combat import (
    ActionUse,
    AttackSource,
    CombatState,
    CombatStatus,
    DamageComponentInput,
    DamageType,
    InitiativeEntry,
    InitiativeOrder,
    SceneFlags,
    active_actor_led_feedback,
    apply_damage,
    attack_declaration_from_state,
    attack_result_led_feedback,
    attack_targets_led_feedback,
    available_scene_interactions,
    complete_interaction_objective,
    confirm_turn_intent,
    current_actor,
    finish_turn,
    legal_melee_targets,
    movement_remaining,
    objective_status_after_combat,
    objective_status_after_flags,
    preview_turn_intent,
    replace_actor,
    resolve_attack,
    resolve_damage,
    resolve_enemy_auto_turn,
    resolve_scene_interaction,
    scene_is_finished,
    scene_result,
    set_scene_flag,
    select_attack_target,
    selected_attack_target_led_feedback,
    start_attack_action,
    start_combat,
    stop_combat,
    use_turn_action,
)
from dnd_board_game.hardware import BoardLedAdapter, LedFeedback, LedFrame, LedRole, movement_led_feedback
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll, roll_instruction
from dnd_board_game.scenarios import LoadedEncounter, build_encounter_from_scenario, load_scenario
from dnd_board_game.world import Coordinate, find_path, movement_range

from .demo_mini_combat import (
    ConnectionFactory,
    _attack_result_message,
    _create_adapter,
    _parse_coordinate,
    _pause_for_led_step,
    _read_int_or_default,
)
from .session_observer import SessionObserver


@dataclass(frozen=True, slots=True)
class DemoMiniCombatLoopResult:
    messages: tuple[str, ...]
    final_state: CombatState
    observation_path: Path
    feedback_events: int


def run_demo(
    args: argparse.Namespace,
    *,
    connection_factory: ConnectionFactory | None = None,
) -> DemoMiniCombatLoopResult:
    observer = SessionObserver(args.session_id, Path(args.observation_dir))
    observer.record("session_started", {"runtime": "demo_mini_combat_loop"})
    observer.record(
        "board_backend_selected",
        {"backend": args.board_backend, "board_url": args.board_url, "show_leds": args.show_leds},
    )
    adapter = _create_adapter(args, connection_factory) if args.show_leds and args.board_backend != "none" else None
    encounter = _load_encounter(args.scenario)
    scenario_message = f"Scenariusz: {encounter.scenario_name}."
    print(scenario_message)
    observer.record("scene_started", {"scenario_id": encounter.scenario_id, "scenario_name": encounter.scenario_name})
    observer.record(
        "scenario_loaded",
        {"scenario_id": encounter.scenario_id, "scenario_name": encounter.scenario_name, "path": args.scenario},
    )
    objectives = encounter.objectives
    scene_flags = SceneFlags()
    setup_actors, setup_messages, setup_feedback = _run_scene_setup(args, encounter, adapter, observer)
    state = start_combat(setup_actors, _fixed_demo_initiative(setup_actors))
    rng = random.Random(args.enemy_seed)
    messages: list[str] = [scenario_message, *setup_messages]
    feedback_events = setup_feedback
    for objective in objectives:
        message = f"Cel sceny: {objective.name}. {objective.description}".strip()
        print(message)
        messages.append(message)
        observer.record(
            "objective_started",
            {
                "objective_id": objective.id,
                "name": objective.name,
                "condition": objective.condition.value,
                "target_id": objective.target_id,
                "flag_key": objective.flag_key,
                "flag_value": objective.flag_value,
            },
        )

    while state.status == CombatStatus.ACTIVE:
        if scene_is_finished(state, objectives):
            break
        if state.round_number > args.max_rounds:
            state = stop_combat(state)
            message = f"Demo zatrzymane po limicie rund: {args.max_rounds}."
            print(message)
            messages.append(message)
            observer.record("combat_stopped", {"reason": "max_rounds", "max_rounds": args.max_rounds})
            break

        actor = current_actor(state)
        turn_message = f"Runda {state.round_number}. Tura: {actor.name}."
        print(turn_message)
        messages.append(turn_message)
        observer.record("turn_started", {"actor_id": str(actor.id), "round_number": state.round_number})
        if adapter is not None:
            adapter.show_feedback(active_actor_led_feedback(state.initiative_order))
            feedback_events += 1
            observer.record("led_feedback_sent", {"phase": "active_actor", "actor_id": str(actor.id)})
            _pause_for_led_step(
                args,
                "To tylko wskazanie aktywnego aktora. Nie klikaj planszy; naciśnij Enter w terminalu.",
            )
            adapter.clear()

        if actor.faction == Faction.ALLY:
            source = encounter.attack_sources_by_actor[actor.id]
            state, objectives, scene_flags, turn_messages, sent = _run_hero_turn(
                args,
                encounter.board,
                state,
                objectives,
                scene_flags,
                actor,
                source,
                encounter.scene_objects,
                adapter,
                observer,
            )
        else:
            enemy_source = encounter.attack_sources_by_actor[actor.id]
            state, turn_messages, sent = _run_enemy_turn(encounter.board, state, actor, enemy_source, rng, adapter, observer, args)
        objectives = objective_status_after_combat(state, objectives)
        objectives = objective_status_after_flags(objectives, scene_flags)
        messages.extend(turn_messages)
        feedback_events += sent

        if state.status == CombatStatus.FINISHED or scene_is_finished(state, objectives):
            break

        observer.record("turn_finished", {"actor_id": str(actor.id), "round_number": state.round_number})
        state = finish_turn(state)

    result = scene_result(state, objectives)
    if result.finished:
        message = result.message if encounter.objectives else _combat_finished_message(state)
        print(message)
        messages.append(message)
        observer.record("combat_finished", {"winner": state.winner.value if state.winner else None})
        observer.record(
            "scene_finished",
            {
                "winner": result.winner.value if result.winner else None,
                "completed_objectives": list(result.completed_objectives),
                "message": result.message,
            },
        )

    observer.record("session_finished", {"observation_path": str(observer.path)})
    return DemoMiniCombatLoopResult(tuple(messages), state, observer.path, feedback_events)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run debug mini combat loop.")
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
    parser.add_argument("--target-id", default="auto")
    parser.add_argument("--target-id-by-actor", action="append", default=[])
    parser.add_argument("--target-position", default=None)
    parser.add_argument("--scan-timeout", type=float, default=30.0)
    parser.add_argument("--hero-attack-roll", type=int, default=14)
    parser.add_argument("--hero-damage", type=int, default=6)
    parser.add_argument("--ally-attack-roll", action="append", default=[])
    parser.add_argument("--ally-damage", action="append", default=[])
    parser.add_argument("--ally-check-roll", action="append", default=[])
    parser.add_argument("--ally-turn-script", action="append", default=[])
    parser.add_argument("--hero-damage-type", choices=[item.value for item in DamageType], default=None)
    parser.add_argument("--enemy-seed", type=int, default=7)
    parser.add_argument("--max-rounds", type=int, default=3)
    parser.add_argument("--scenario", default="content/scenarios/goblin_ambush.json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.session_id is None:
        args.session_id = f"demo_mini_combat_loop_{uuid.uuid4().hex[:8]}"
    try:
        run_demo(args)
    except Exception as exc:
        print(f"demo_mini_combat_loop failed: {exc}", file=sys.stderr)
        return 1
    return 0


def _run_scene_setup(
    args: argparse.Namespace,
    encounter: LoadedEncounter,
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
) -> tuple[tuple[Actor, ...], tuple[str, ...], int]:
    messages: list[str] = []
    feedback_events = 0
    actors = tuple(encounter.actors)
    start_positions = _flatten_start_zones(encounter.player_start_zones)
    if not start_positions and not encounter.environment and not any(actor.faction == Faction.ENEMY for actor in actors):
        return actors, (), 0

    message = "Setup sceny: ustawcie wskazane figurki i elementy na podświetlonych polach."
    print(message)
    messages.append(message)
    observer.record(
        "scene_setup_started",
        {
            "scenario_id": encounter.scenario_id,
            "player_start_zones": [
                [list(position.as_tuple()) for position in zone] for zone in encounter.player_start_zones
            ],
        },
    )

    used_start_positions: set[Coordinate] = set()
    for actor in actors:
        if actor.faction != Faction.ALLY:
            continue
        available = tuple(position for position in start_positions if position not in used_start_positions)
        if not available:
            break
        step_message = (
            f"{actor.name}: ustaw figurkę na jednym z podświetlonych pól startowych. "
            "Kliknięcie pola potwierdza ustawienie."
        )
        print(step_message)
        messages.append(step_message)
        selected, sent = _confirm_setup_positions(
            args,
            adapter,
            observer,
            positions=available,
            color=(0, 220, 255),
            phase="scene_setup_hero",
            prompt=step_message,
            actor_id=str(actor.id),
        )
        feedback_events += sent
        selected_position = selected or actor.position
        used_start_positions.add(selected_position)
        actors = tuple(replace(candidate, position=selected_position) if candidate.id == actor.id else candidate for candidate in actors)

    enemy_positions = tuple(actor.position for actor in actors if actor.faction == Faction.ENEMY and not actor.is_defeated())
    if enemy_positions:
        for batch_index, batch in enumerate(_batched(enemy_positions, 5), start=1):
            step_message = f"Ustaw przeciwników {batch_index}: kliknij jedno z podświetlonych pól po ustawieniu tej grupy."
            print(step_message)
            messages.append(step_message)
            _, sent = _confirm_setup_positions(
                args,
                adapter,
                observer,
                positions=batch,
                color=(255, 0, 80),
                phase="scene_setup_enemies",
                prompt=step_message,
            )
            feedback_events += sent

    visible_environment = tuple(entry for entry in encounter.environment if entry.visibility.value == "visible" and entry.positions)
    for setup_type in sorted({entry.setup_type for entry in visible_environment}, key=lambda item: item.value):
        entries = tuple(entry for entry in visible_environment if entry.setup_type == setup_type)
        positions = tuple(position for entry in entries for position in entry.positions)
        names = ", ".join(entry.name for entry in entries)
        for batch_index, batch in enumerate(_batched(positions, 5), start=1):
            step_message = (
                f"Ustaw { _setup_type_label(setup_type) } {batch_index}: {names}. "
                "Kliknij jedno z podświetlonych pól po ustawieniu tej grupy."
            )
            print(step_message)
            messages.append(step_message)
            _, sent = _confirm_setup_positions(
                args,
                adapter,
                observer,
                positions=batch,
                color=_setup_type_color(setup_type),
                phase=f"scene_setup_{setup_type.value}",
                prompt=step_message,
            )
            feedback_events += sent

    observer.record("scene_setup_confirmed", {"scenario_id": encounter.scenario_id})
    return actors, tuple(messages), feedback_events


def _confirm_setup_positions(
    args: argparse.Namespace,
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
    *,
    positions: tuple[Coordinate, ...],
    color: tuple[int, int, int],
    phase: str,
    prompt: str,
    actor_id: str | None = None,
) -> tuple[Coordinate | None, int]:
    observer.record(
        "scene_setup_step_started",
        {
            "phase": phase,
            "actor_id": actor_id,
            "positions": [list(position.as_tuple()) for position in positions],
            "prompt": prompt,
        },
    )
    if adapter is None:
        selected = positions[0] if positions else None
        observer.record(
            "scene_setup_step_confirmed",
            {"phase": phase, "actor_id": actor_id, "selected_position": list(selected.as_tuple()) if selected else None},
        )
        return selected, 0

    feedback = LedFeedback((LedFrame(positions, color, LedRole.DESTINATION),)) if positions else LedFeedback()
    adapter.show_feedback(feedback)
    observer.record("led_feedback_sent", {"phase": phase, "actor_id": actor_id})
    selected: Coordinate | None = None
    scan_board = getattr(adapter.connection, "scan_board", None)
    if callable(scan_board) and positions:
        acceptable = [position.as_tuple() for position in positions]
        observer.record("board_scan_requested", {"phase": phase, "acceptable_positions": [list(pos) for pos in acceptable]})
        clicked = scan_board(acceptable, timeout_s=args.scan_timeout)
        if clicked is not None:
            selected = Coordinate(int(clicked[0]), int(clicked[1]))
            observer.record("board_scan_received", {"phase": phase, "position": list(selected.as_tuple())})
    else:
        _pause_for_led_step(args, prompt)
    adapter.clear()
    observer.record(
        "scene_setup_step_confirmed",
        {"phase": phase, "actor_id": actor_id, "selected_position": list(selected.as_tuple()) if selected else None},
    )
    return selected, 1


def _flatten_start_zones(start_zones: tuple[tuple[Coordinate, ...], ...]) -> tuple[Coordinate, ...]:
    return tuple(sorted({position for zone in start_zones for position in zone}))


def _batched(items: tuple[Coordinate, ...], batch_size: int) -> tuple[tuple[Coordinate, ...], ...]:
    size = max(1, batch_size)
    return tuple(tuple(items[index : index + size]) for index in range(0, len(items), size))


def _setup_type_label(setup_type) -> str:
    labels = {
        "blocking_terrain": "blokady",
        "obstacle": "przeszkody",
        "difficult_terrain": "trudny teren",
        "interactable": "obiekty interaktywne",
        "container": "skrzynie i pojemniki",
        "npc": "NPC",
        "cover": "osłony",
        "marker": "markery",
        "custom": "elementy otoczenia",
    }
    return labels.get(setup_type.value, "elementy otoczenia")


def _setup_type_color(setup_type) -> tuple[int, int, int]:
    if setup_type.value in {"blocking_terrain", "obstacle", "cover"}:
        return (180, 0, 0)
    if setup_type.value == "difficult_terrain":
        return (255, 120, 0)
    if setup_type.value in {"interactable", "container", "npc"}:
        return (0, 255, 120)
    return (255, 210, 0)


def _run_hero_turn(
    args: argparse.Namespace,
    board,
    state: CombatState,
    objectives,
    scene_flags: SceneFlags,
    actor: Actor,
    source: AttackSource,
    scene_objects,
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
) -> tuple[CombatState, tuple, SceneFlags, tuple[str, ...], int]:
    messages: list[str] = []
    feedback_events = 0
    actor_id = str(actor.id)
    attack_roll_overrides = _parse_actor_value_overrides(args.ally_attack_roll, int)
    damage_overrides = _parse_actor_value_overrides(args.ally_damage, int)
    check_roll_overrides = _parse_actor_value_overrides(args.ally_check_roll, int)
    scripts = _parse_turn_scripts(args.ally_turn_script)
    script = list(scripts.get(actor_id, ()))
    prompt_message = f"Tura: {actor.name}. Kliknij pole ruchu, cel ataku albo zakończ turę w terminalu."
    print(prompt_message)
    messages.append(prompt_message)
    observer.record(
        "turn_prompt_started",
        {"actor_id": actor_id, "round_number": state.round_number, "movement_remaining": movement_remaining(state, actor)},
    )

    pending_click: Coordinate | None = None
    while state.status == CombatStatus.ACTIVE:
        actor = _actor_by_string_id(state, actor_id)
        if actor.is_defeated():
            break
        if _turn_has_no_options(board, state, actor, source, scene_objects):
            message = f"{actor.name} nie ma już dostępnej akcji ani ruchu w tej turze."
            print(message)
            messages.append(message)
            break

        if adapter is not None:
            adapter.show_feedback(_turn_options_led_feedback(board, state, actor, source, scene_objects))
            feedback_events += 1
            observer.record("led_feedback_sent", {"phase": "turn_options", "actor_id": actor_id})

        if pending_click is not None:
            clicked = pending_click
            pending_click = None
        else:
            clicked = _next_turn_click(args, board, state, actor, source, scene_objects, adapter, observer, script)
        if clicked is None:
            message = f"{actor.name} kończy turę."
            print(message)
            messages.append(message)
            if adapter is not None:
                adapter.clear()
            break

        preview = preview_turn_intent(board, state, actor, source, clicked, scene_objects)
        print(preview.message)
        messages.append(preview.message)
        observer.record(
            "turn_intent_previewed",
            {
                "actor_id": actor_id,
                "round_number": state.round_number,
                "mode": preview.mode.value,
                "clicked_position": list(clicked.as_tuple()),
                "movement_remaining": preview.movement_remaining_feet,
                "action_available": preview.action_available,
            },
        )
        if preview.mode.value == "movement_preview" and preview.movement_path is not None:
            observer.record(
                "movement_path_selected",
                {
                    "actor_id": actor_id,
                    "destination": list(preview.movement_path.destination.as_tuple()),
                    "cost_feet": preview.movement_path.cost_feet,
                    "remaining_before": preview.movement_remaining_feet,
                },
            )
        if preview.mode.value == "attack_preview" and preview.attack_target is not None:
            observer.record("attack_previewed", {"actor_id": actor_id, "target_id": preview.attack_target.id})
        if preview.mode.value == "interaction_preview" and preview.interaction_object is not None:
            interaction = _selected_interaction(preview.interaction_object)
            options_message = _interaction_options_message(preview.interaction_object)
            print(options_message)
            messages.append(options_message)
            observer.record(
                "interaction_options_shown",
                {
                    "actor_id": actor_id,
                    "object_id": preview.interaction_object.id,
                    "interactions": [
                        {
                            "id": available.id,
                            "label": available.label,
                            "has_ability_check": available.ability_check is not None,
                        }
                        for available in available_scene_interactions(preview.interaction_object)
                    ],
                },
            )
            observer.record(
                "interaction_previewed",
                {"actor_id": actor_id, "object_id": preview.interaction_object.id, "interaction_id": interaction.id},
            )
        if preview.mode.value == "invalid":
            continue
        if adapter is not None:
            adapter.clear()
            adapter.show_feedback(_preview_led_feedback(preview))
            feedback_events += 1
            observer.record("led_feedback_sent", {"phase": preview.mode.value, "actor_id": actor_id})

        confirmation_click = _confirm_preview_click(args, board, state, actor, source, scene_objects, preview, adapter, observer, script)
        if confirmation_click is None:
            continue
        if confirmation_click != preview.clicked_position:
            pending_click = confirmation_click
            if adapter is not None:
                adapter.clear()
            continue

        confirmation = confirm_turn_intent(state, preview)
        observer.record(
            "turn_intent_confirmed",
            {
                "actor_id": actor_id,
                "round_number": state.round_number,
                "mode": preview.mode.value,
                "accepted": confirmation.accepted,
                "clicked_position": list(clicked.as_tuple()),
            },
        )
        if not confirmation.accepted:
            print(confirmation.message)
            messages.append(confirmation.message)
            observer.record("movement_rejected", {"actor_id": actor_id, "reason": confirmation.message})
            continue
        print(confirmation.message)
        messages.append(confirmation.message)

        if confirmation.end_turn_requested:
            observer.record(
                "turn_end_requested",
                {
                    "actor_id": actor_id,
                    "round_number": state.round_number,
                    "movement_remaining": preview.movement_remaining_feet,
                    "action_available": preview.action_available,
                },
            )
            if adapter is not None:
                adapter.clear()
            break

        if confirmation.movement_result is not None:
            state = confirmation.state
            observer.record(
                "movement_committed",
                {
                    "actor_id": actor_id,
                    "destination": list(clicked.as_tuple()),
                    "cost_feet": preview.movement_path.cost_feet if preview.movement_path else 0,
                    "movement_remaining": confirmation.movement_result.movement_remaining_feet,
                },
            )
            if adapter is not None:
                adapter.clear()
                adapter.show_feedback(LedFeedback((LedFrame((clicked,), (0, 255, 120), LedRole.DESTINATION),)))
                feedback_events += 1
                observer.record("led_feedback_sent", {"phase": "movement_committed", "actor_id": actor_id})
                _pause_for_led_step(args, "Naciśnij Enter po potwierdzeniu ruchu.")
                adapter.clear()
            continue

        if confirmation.interaction_object is not None:
            state = confirmation.state
            completed_before = _completed_objective_ids(objectives)
            objectives = complete_interaction_objective(objectives, confirmation.interaction_object)
            state, objectives, scene_flags, interaction_messages, sent = _resolve_confirmed_interaction(
                args,
                state,
                objectives,
                scene_flags,
                actor,
                confirmation.interaction_object,
                check_roll_overrides,
                adapter,
                observer,
            )
            messages.extend(interaction_messages)
            feedback_events += sent
            _record_new_objective_completions(observer, completed_before, objectives)
            if adapter is not None:
                _pause_for_led_step(args, "Naciśnij Enter po potwierdzeniu interakcji.")
                adapter.clear()
            if scene_is_finished(state, objectives):
                break
            continue

        if confirmation.attack_target is not None and confirmation.attack_source is not None:
            state, attack_messages, sent = _resolve_confirmed_hero_attack(
                args,
                board,
                state,
                actor,
                confirmation.attack_target,
                confirmation.attack_source,
                attack_roll_overrides,
                damage_overrides,
                adapter,
                observer,
            )
            messages.extend(attack_messages)
            feedback_events += sent
            continue

    return state, objectives, scene_flags, tuple(messages), feedback_events


def _resolve_confirmed_interaction(
    args: argparse.Namespace,
    state: CombatState,
    objectives,
    scene_flags: SceneFlags,
    actor: Actor,
    scene_object,
    check_roll_overrides: dict[str, object],
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
) -> tuple[CombatState, tuple, SceneFlags, tuple[str, ...], int]:
    messages: list[str] = []
    feedback_events = 0
    actor_id = str(actor.id)
    interaction = _selected_interaction(scene_object)
    observer.record(
        "interaction_confirmed",
        {"actor_id": actor_id, "object_id": scene_object.id, "interaction_id": interaction.id},
    )

    natural_roll: int | None = None
    if interaction.ability_check is not None:
        request = D20RollRequest(modifiers=interaction.ability_check.modifiers)
        instruction = roll_instruction(request)
        check_message = (
            f"Test {_ability_check_label(interaction.ability_check.ability, interaction.ability_check.skill)}, "
            f"ST {interaction.ability_check.dc}. {instruction.message}"
        )
        print(check_message)
        messages.append(check_message)
        observer.record(
            "ability_check_requested",
            {
                "actor_id": actor_id,
                "object_id": scene_object.id,
                "interaction_id": interaction.id,
                "ability": interaction.ability_check.ability,
                "skill": interaction.ability_check.skill,
                "dc": interaction.ability_check.dc,
                "instruction": instruction.message,
            },
        )
        default_roll = int(check_roll_overrides.get(actor_id, 10))
        natural_roll = _read_int_or_default(
            args,
            f"Wpisz naturalny wynik testu d20 albo naciśnij Enter dla wartości z CLI ({default_roll}): ",
            default_roll,
        )

    result = resolve_scene_interaction(interaction, natural_roll=natural_roll)
    print(result.message)
    messages.append(result.message)
    if result.roll is not None:
        observer.record(
            "ability_check_resolved",
            {
                "actor_id": actor_id,
                "object_id": scene_object.id,
                "interaction_id": interaction.id,
                "natural_roll": result.roll.natural_roll,
                "modifier_total": result.roll.breakdown.modifier_total,
                "total": result.roll.total,
                "dc": result.dc,
                "success": result.success,
            },
        )

    if result.flag_key is not None:
        scene_flags = set_scene_flag(scene_flags, result.flag_key, result.flag_value)
        observer.record(
            "scene_flag_set",
            {"key": result.flag_key, "value": result.flag_value, "actor_id": actor_id, "interaction_id": interaction.id},
        )
        observer.record(
            "scene_flag_checked",
            {"key": result.flag_key, "value": result.flag_value, "actor_id": actor_id, "interaction_id": interaction.id},
        )
    objectives = objective_status_after_flags(objectives, scene_flags)

    if adapter is not None:
        adapter.clear()
        color = (0, 255, 120) if result.success else (255, 0, 0)
        adapter.show_feedback(LedFeedback((LedFrame(scene_object.positions, color, LedRole.DESTINATION),)))
        feedback_events += 1
        observer.record(
            "led_feedback_sent",
            {"phase": "interaction_success" if result.success else "interaction_failure", "actor_id": actor_id},
        )
    return state, objectives, scene_flags, tuple(messages), feedback_events


def _resolve_confirmed_hero_attack(
    args: argparse.Namespace,
    board,
    state: CombatState,
    actor: Actor,
    target,
    source: AttackSource,
    attack_roll_overrides: dict[str, object],
    damage_overrides: dict[str, object],
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
) -> tuple[CombatState, tuple[str, ...], int]:
    messages: list[str] = []
    feedback_events = 0
    actor = _actor_by_string_id(state, str(actor.id))
    attack_state = select_attack_target(start_attack_action(board, actor, state.actors, source), target_id=target.id)
    declaration = attack_declaration_from_state(attack_state)
    observer.record(
        "target_selected",
        {"actor_id": str(actor.id), "target_id": declaration.target.id, "target_position": list(declaration.target.position.as_tuple())},
    )
    observer.record(
        "attack_declared",
        {"attacker_id": str(actor.id), "target_id": declaration.target.id, "source": declaration.source.name},
    )
    instruction = roll_instruction(source.attack_roll_request)
    roll_message = f"Atakujesz {declaration.target.name} za pomocą {source.name}. {instruction.message}"
    print(roll_message)
    messages.append(roll_message)
    if adapter is not None:
        adapter.clear()
        adapter.show_feedback(selected_attack_target_led_feedback(declaration.target))
        feedback_events += 1
        observer.record("led_feedback_sent", {"phase": "selected_attack_target", "target_id": declaration.target.id})
    default_roll = int(attack_roll_overrides.get(str(actor.id), args.hero_attack_roll))
    natural_attack_roll = _read_int_or_default(
        args,
        f"Wpisz naturalny wynik ataku d20 albo naciśnij Enter dla wartości z CLI ({default_roll}): ",
        default_roll,
    )
    if adapter is not None:
        adapter.clear()
    attack_roll = resolve_d20_roll(D20RollInput(source.attack_roll_request, natural_attack_roll))
    resolution = resolve_attack(declaration, attack_roll, ActionUse.ACTION_AVAILABLE)
    action_result = use_turn_action(state)
    state = action_result.state
    observer.record("action_used", {"actor_id": str(actor.id), "action": "attack", "accepted": action_result.accepted})
    result_message = _attack_result_message(resolution.outcome.value, declaration.target.name, attack_roll.total)
    print(result_message)
    messages.append(result_message)
    observer.record(
        "attack_resolved",
        {
            "attacker_id": str(actor.id),
            "target_id": declaration.target.id,
            "natural_roll": attack_roll.natural_roll,
            "modifier_total": attack_roll.breakdown.modifier_total,
            "total": attack_roll.total,
            "outcome": resolution.outcome.value,
            "hit": resolution.hit,
        },
    )
    if adapter is not None:
        adapter.show_feedback(attack_result_led_feedback(declaration.target, resolution.outcome))
        feedback_events += 1
        observer.record("led_feedback_sent", {"phase": "attack_result", "outcome": resolution.outcome.value})
        _pause_for_led_step(args, "Naciśnij Enter po wyniku ataku.")
        adapter.clear()
    if resolution.hit:
        damage_amount = int(damage_overrides.get(str(actor.id), args.hero_damage))
        damage_type = args.hero_damage_type or source.damage_type
        damage = resolve_damage((DamageComponentInput(damage_amount, DamageType(damage_type), source.name),))
        target_actor = _actor_by_string_id(state, declaration.target.id)
        updated_target = apply_damage(target_actor, damage)
        state = replace_actor(state, updated_target)
        damage_message = (
            f"Obrażenia: {damage.total_applied} {damage_type}. "
            f"{target_actor.name}: HP {target_actor.hp} -> {updated_target.hp}."
        )
        print(damage_message)
        messages.append(damage_message)
        _record_damage(observer, target_actor, updated_target, damage)
    return state, tuple(messages), feedback_events


def _next_turn_click(
    args: argparse.Namespace,
    board,
    state: CombatState,
    actor: Actor,
    source: AttackSource,
    scene_objects,
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
    script: list[str],
) -> Coordinate | None:
    if script:
        command = script.pop(0)
        return _coordinate_from_turn_command(command, state, actor, scene_objects)
    if args.board_backend == "none":
        if state.turn_action.action_use == ActionUse.ACTION_AVAILABLE:
            targets = legal_melee_targets(board, actor, state.actors)
            if targets:
                return targets[0].position
        return None
    if adapter is None:
        return None
    scan_board = getattr(adapter.connection, "scan_board", None)
    if not callable(scan_board):
        return None
    acceptable = [position.as_tuple() for position in _acceptable_turn_positions(board, state, actor, source, scene_objects)]
    observer.record("board_scan_requested", {"acceptable_positions": [list(position) for position in acceptable]})
    print("Kliknij pole ruchu albo cel ataku. Kliknięcie tego samego pola drugi raz potwierdzi wybór.")
    selected = scan_board(acceptable, timeout_s=args.scan_timeout)
    if selected is None:
        observer.record("board_scan_cancelled", {})
        return None
    observer.record("board_scan_received", {"position": list(selected)})
    return Coordinate(int(selected[0]), int(selected[1]))


def _confirm_preview_click(
    args: argparse.Namespace,
    board,
    state: CombatState,
    actor: Actor,
    source: AttackSource,
    scene_objects,
    preview,
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
    script: list[str],
) -> Coordinate | None:
    if script or args.board_backend == "none":
        return preview.clicked_position
    if adapter is None:
        return preview.clicked_position
    scan_board = getattr(adapter.connection, "scan_board", None)
    if not callable(scan_board):
        return preview.clicked_position
    expected = preview.clicked_position.as_tuple()
    print("Kliknij to samo pole ponownie, aby potwierdzić. Kliknięcie innego pola zmieni podgląd.")
    acceptable = [position.as_tuple() for position in _acceptable_turn_positions(board, state, actor, source, scene_objects)]
    selected = scan_board(acceptable, timeout_s=args.scan_timeout)
    if selected is None:
        observer.record("turn_intent_confirmation_cancelled", {"expected_position": list(expected)})
        return None
    confirmed = tuple(selected) == expected
    observer.record("turn_intent_confirmation_scan", {"position": list(selected), "confirmed": confirmed})
    return Coordinate(int(selected[0]), int(selected[1]))


def _coordinate_from_turn_command(command: str, state: CombatState, actor: Actor, scene_objects) -> Coordinate | None:
    command = command.strip()
    if command == "end":
        return None
    if command in {"self", "options"}:
        return actor.position
    if command.startswith("move:"):
        return _parse_coordinate(command.removeprefix("move:"))
    if command.startswith("attack:"):
        target_id = command.removeprefix("attack:")
        return _actor_by_string_id(state, target_id).position
    if command.startswith("interact:"):
        object_id = command.removeprefix("interact:")
        for scene_object in scene_objects:
            if scene_object.id == object_id:
                return scene_object.primary_position
        raise ValueError(f"Unknown interaction object: {object_id}.")
    raise ValueError(f"Unknown turn script command for {actor.id}: {command!r}.")


def _acceptable_turn_positions(board, state: CombatState, actor: Actor, source: AttackSource, scene_objects=()) -> tuple[Coordinate, ...]:
    positions: set[Coordinate] = {actor.position}
    if movement_remaining(state, actor) > 0:
        movement_actor = replace(actor, speed_feet=movement_remaining(state, actor))
        positions.update(movement_range(board, movement_actor, state.actors).reachable_tiles)
    if state.turn_action.action_use == ActionUse.ACTION_AVAILABLE:
        positions.update(target.position for target in legal_melee_targets(board, actor, state.actors))
        positions.update(
            position
            for scene_object in scene_objects
            for position in scene_object.positions
            if scene_object.visibility.value == "visible"
        )
    return tuple(sorted(positions))


def _turn_options_led_feedback(board, state: CombatState, actor: Actor, source: AttackSource, scene_objects=()) -> LedFeedback:
    frames: list[LedFrame] = [LedFrame((actor.position,), (255, 255, 255), LedRole.ACTIVE_ACTOR)]
    if movement_remaining(state, actor) > 0:
        movement_actor = replace(actor, speed_feet=movement_remaining(state, actor))
        reachable = tuple(
            tile
            for tile in sorted(movement_range(board, movement_actor, state.actors).reachable_tiles)
            if tile != actor.position
        )
        if reachable:
            frames.append(LedFrame(reachable, (0, 110, 160), LedRole.MOVEMENT_RANGE))
    if state.turn_action.action_use == ActionUse.ACTION_AVAILABLE:
        targets = tuple(sorted(target.position for target in legal_melee_targets(board, actor, state.actors)))
        if targets:
            frames.append(LedFrame(targets, (0, 80, 220), LedRole.DESTINATION))
        object_positions = tuple(
            sorted(
                position
                for scene_object in scene_objects
                if scene_object.visibility.value == "visible"
                for position in scene_object.positions
            )
        )
        if object_positions:
            frames.append(LedFrame(object_positions, (0, 255, 120), LedRole.DESTINATION))
    legal_target_positions = {target.position for target in legal_melee_targets(board, actor, state.actors)}
    visible_enemy_positions = tuple(
        sorted(
            other.position
            for other in state.actors
            if other.id != actor.id
            and other.faction != actor.faction
            and not other.is_defeated()
            and other.position not in legal_target_positions
        )
    )
    if visible_enemy_positions:
        frames.append(LedFrame(visible_enemy_positions, (120, 0, 45), LedRole.ENEMY))
    visible_ally_positions = tuple(
        sorted(
            other.position
            for other in state.actors
            if other.id != actor.id
            and other.faction == actor.faction
            and not other.is_defeated()
        )
    )
    if visible_ally_positions:
        frames.append(LedFrame(visible_ally_positions, (80, 180, 200), LedRole.ALLY))
    return LedFeedback(tuple(frames))


def _preview_led_feedback(preview) -> LedFeedback:
    if preview.mode.value == "actor_options_preview":
        return LedFeedback((LedFrame((preview.clicked_position,), (255, 255, 255), LedRole.ACTIVE_ACTOR),))
    if preview.movement_range is not None:
        return movement_led_feedback(preview.movement_range, preview.movement_path)
    if preview.attack_target is not None:
        return selected_attack_target_led_feedback(preview.attack_target)
    if preview.interaction_object is not None:
        return LedFeedback((LedFrame(preview.interaction_object.positions, (0, 255, 120), LedRole.DESTINATION),))
    return LedFeedback((LedFrame((preview.clicked_position,), (255, 0, 0), LedRole.DESTINATION),))


def _selected_interaction(scene_object):
    return available_scene_interactions(scene_object)[0]


def _interaction_options_message(scene_object) -> str:
    interactions = available_scene_interactions(scene_object)
    if len(interactions) == 1:
        interaction = interactions[0]
        description = f" {interaction.description}" if interaction.description else ""
        return f"Opcja interakcji: {interaction.label}.{description}"
    labels = ", ".join(interaction.label for interaction in interactions)
    return f"Dostępne interakcje dla {scene_object.name}: {labels}. W MVP wybrana zostanie pierwsza opcja."


def _ability_check_label(ability: str, skill: str | None) -> str:
    ability_label = {
        "strength": "Siły",
        "dexterity": "Zręczności",
        "constitution": "Kondycji",
        "intelligence": "Inteligencji",
        "wisdom": "Mądrości",
        "charisma": "Charyzmy",
    }.get(ability, ability)
    if skill is None:
        return ability_label
    skill_label = {
        "perception": "Percepcja",
        "investigation": "Śledztwo",
        "athletics": "Atletyka",
        "acrobatics": "Akrobatyka",
        "stealth": "Skradanie",
        "persuasion": "Perswazja",
        "deception": "Oszustwo",
        "insight": "Intuicja",
        "arcana": "Wiedza tajemna",
        "history": "Historia",
        "nature": "Natura",
        "religion": "Religia",
    }.get(skill, skill)
    return f"{ability_label} ({skill_label})"


def _completed_objective_ids(objectives) -> set[str]:
    return {objective.id for objective in objectives if objective.status.value == "completed"}


def _record_new_objective_completions(observer: SessionObserver, completed_before: set[str], objectives) -> None:
    for objective in objectives:
        if objective.status.value == "completed" and objective.id not in completed_before:
            observer.record("objective_completed", {"objective_id": objective.id, "name": objective.name})


def _turn_has_no_options(board, state: CombatState, actor: Actor, source: AttackSource, scene_objects=()) -> bool:
    has_move = movement_remaining(state, actor) > 0 and any(
        position != actor.position for position in _acceptable_turn_positions(board, state, actor, source, ())
    )
    has_attack = state.turn_action.action_use == ActionUse.ACTION_AVAILABLE and bool(legal_melee_targets(board, actor, state.actors))
    has_interaction = state.turn_action.action_use == ActionUse.ACTION_AVAILABLE and bool(scene_objects)
    return not has_move and not has_attack and not has_interaction


def _run_enemy_turn(
    board,
    state: CombatState,
    actor: Actor,
    source: AttackSource,
    rng: random.Random,
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
    args: argparse.Namespace,
) -> tuple[CombatState, tuple[str, ...], int]:
    result = resolve_enemy_auto_turn(board, state, actor, source, rng)
    observer.record("enemy_action_selected", {"actor_id": str(actor.id), "action": "attack_or_move", "target_id": result.target.id if result.target else None})
    observer.record("action_used", {"actor_id": str(actor.id), "action": "attack", "accepted": result.action_used})
    messages: list[str] = []
    feedback_events = 0

    if result.movement_path is not None and result.movement_path.valid:
        observer.record(
            "movement_committed",
            {
                "actor_id": str(actor.id),
                "destination": list(result.movement_path.destination.as_tuple()),
                "cost_feet": result.movement_path.cost_feet,
                "movement_remaining": 0,
            },
        )
        if adapter is not None:
            adapter.show_feedback(movement_led_feedback(movement_range(board, actor, state.actors), result.movement_path))
            feedback_events += 1
            observer.record("led_feedback_sent", {"phase": "enemy_movement", "actor_id": str(actor.id)})
            _pause_for_led_step(args, "Naciśnij Enter po ruchu przeciwnika.")
            adapter.clear()

    if result.target is not None:
        observer.record(
            "target_selected",
            {"actor_id": str(actor.id), "target_id": result.target.id, "target_position": list(result.target.position.as_tuple())},
        )
        target_message = f"{actor.name} wybiera cel: {result.target.name}."
        print(target_message)
        messages.append(target_message)
        if adapter is not None:
            adapter.show_feedback(selected_attack_target_led_feedback(result.target))
            feedback_events += 1
            observer.record("led_feedback_sent", {"phase": "enemy_selected_attack_target", "target_id": result.target.id})
            _pause_for_led_step(args, "Naciśnij Enter po celu przeciwnika.")
            adapter.clear()

    print(result.message)
    messages.append(result.message)

    if result.attack_roll is not None and result.attack_resolution is not None:
        observer.record(
            "attack_resolved",
            {
                "attacker_id": str(actor.id),
                "target_id": result.target.id if result.target else None,
                "natural_roll": result.attack_roll.natural_roll,
                "modifier_total": result.attack_roll.breakdown.modifier_total,
                "total": result.attack_roll.total,
                "outcome": result.attack_resolution.outcome.value,
                "hit": result.attack_resolution.hit,
            },
        )
        if adapter is not None and result.target is not None:
            adapter.show_feedback(attack_result_led_feedback(result.target, result.attack_resolution.outcome))
            feedback_events += 1
            observer.record("led_feedback_sent", {"phase": "enemy_attack_result", "outcome": result.attack_resolution.outcome.value})
            _pause_for_led_step(args, "Naciśnij Enter po wyniku ataku przeciwnika.")
            adapter.clear()

    if result.damage is not None and result.updated_target is not None:
        previous_target = _actor_by_string_id(state, result.target.id)
        _record_damage(observer, previous_target, result.updated_target, result.damage)

    return result.state, tuple(messages), feedback_events


def _load_encounter(path: str) -> LoadedEncounter:
    return build_encounter_from_scenario(load_scenario(path))


def _fixed_demo_initiative(actors: tuple[Actor, ...]) -> InitiativeOrder:
    empty_request = D20RollRequest()
    entries: list[InitiativeEntry] = []
    for index, actor in enumerate(actors):
        natural_roll = max(1, 20 - (index * 10))
        entries.append(
            InitiativeEntry(
                actor,
                resolve_d20_roll(D20RollInput(empty_request, natural_roll)),
                actor.ability_scores.dexterity,
                index,
            )
        )
    return InitiativeOrder(tuple(entries))


def _actor_by_string_id(state: CombatState, actor_id: str) -> Actor:
    for actor in state.actors:
        if str(actor.id) == actor_id:
            return actor
    raise ValueError(f"Unknown actor: {actor_id}.")


def _target_id_for_actor(actor_id: str, default_target_id: str, overrides: dict[str, object], legal_targets) -> str:
    target_id = str(overrides.get(actor_id, default_target_id))
    if target_id == "auto":
        return legal_targets[0].id
    return target_id


def _parse_actor_value_overrides(values: Sequence[str], parser) -> dict[str, object]:
    result: dict[str, object] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Expected actor=value override, got: {value!r}.")
        actor_id, raw = value.split("=", maxsplit=1)
        actor_id = actor_id.strip()
        if not actor_id:
            raise ValueError(f"Missing actor id in override: {value!r}.")
        result[actor_id] = parser(raw.strip())
    return result


def _parse_turn_scripts(values: Sequence[str]) -> dict[str, tuple[str, ...]]:
    result: dict[str, tuple[str, ...]] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Expected actor=command,command override, got: {value!r}.")
        actor_id, raw = value.split("=", maxsplit=1)
        commands = tuple(command.strip() for command in raw.split(",") if command.strip())
        expanded: list[str] = []
        index = 0
        while index < len(commands):
            command = commands[index]
            if command.startswith("move:") and index + 1 < len(commands):
                expanded.append(f"{command},{commands[index + 1]}")
                index += 2
                continue
            expanded.append(command)
            index += 1
        result[actor_id.strip()] = tuple(expanded)
    return result


def _record_damage(observer: SessionObserver, before: Actor, after: Actor, damage) -> None:
    observer.record(
        "damage_applied",
        {
            "target_id": str(before.id),
            "components": [
                {"amount": component.amount, "damage_type": component.damage_type.value, "label": component.label}
                for component in damage.components
            ],
            "total_applied": damage.total_applied,
            "hp_before": before.hp,
            "hp_after": after.hp,
            "temp_hp_before": before.temp_hp,
            "temp_hp_after": after.temp_hp,
        },
    )


def _combat_finished_message(state: CombatState) -> str:
    if state.winner == Faction.ALLY:
        return "Walka zakończona. Zwyciężają bohaterowie."
    if state.winner == Faction.ENEMY:
        return "Walka zakończona. Zwyciężają przeciwnicy."
    return "Walka zakończona."


if __name__ == "__main__":
    raise SystemExit(main())
