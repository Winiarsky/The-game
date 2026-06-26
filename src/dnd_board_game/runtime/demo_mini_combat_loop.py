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
    active_actor_led_feedback,
    apply_damage,
    attack_declaration_from_state,
    attack_result_led_feedback,
    attack_targets_led_feedback,
    confirm_turn_intent,
    current_actor,
    finish_turn,
    legal_melee_targets,
    movement_remaining,
    preview_turn_intent,
    replace_actor,
    resolve_attack,
    resolve_damage,
    resolve_enemy_auto_turn,
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
    _select_target,
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
    observer.record(
        "scenario_loaded",
        {"scenario_id": encounter.scenario_id, "scenario_name": encounter.scenario_name, "path": args.scenario},
    )
    state = start_combat(encounter.actors, _fixed_demo_initiative(encounter.actors))
    rng = random.Random(args.enemy_seed)
    messages: list[str] = [scenario_message]
    feedback_events = 0

    while state.status == CombatStatus.ACTIVE:
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
            state, turn_messages, sent = _run_hero_turn(args, encounter.board, state, actor, source, adapter, observer)
        else:
            enemy_source = encounter.attack_sources_by_actor[actor.id]
            state, turn_messages, sent = _run_enemy_turn(encounter.board, state, actor, enemy_source, rng, adapter, observer, args)
        messages.extend(turn_messages)
        feedback_events += sent

        if state.status == CombatStatus.FINISHED:
            break

        observer.record("turn_finished", {"actor_id": str(actor.id), "round_number": state.round_number})
        state = finish_turn(state)

    if state.status == CombatStatus.FINISHED:
        message = _combat_finished_message(state)
        print(message)
        messages.append(message)
        observer.record("combat_finished", {"winner": state.winner.value if state.winner else None})

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


def _run_hero_turn(
    args: argparse.Namespace,
    board,
    state: CombatState,
    actor: Actor,
    source: AttackSource,
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
) -> tuple[CombatState, tuple[str, ...], int]:
    messages: list[str] = []
    feedback_events = 0
    actor_id = str(actor.id)
    attack_roll_overrides = _parse_actor_value_overrides(args.ally_attack_roll, int)
    damage_overrides = _parse_actor_value_overrides(args.ally_damage, int)
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
        if _turn_has_no_options(board, state, actor, source):
            message = f"{actor.name} nie ma już dostępnej akcji ani ruchu w tej turze."
            print(message)
            messages.append(message)
            break

        if adapter is not None:
            adapter.show_feedback(_turn_options_led_feedback(board, state, actor, source))
            feedback_events += 1
            observer.record("led_feedback_sent", {"phase": "turn_options", "actor_id": actor_id})

        if pending_click is not None:
            clicked = pending_click
            pending_click = None
        else:
            clicked = _next_turn_click(args, board, state, actor, source, adapter, observer, script)
        if clicked is None:
            message = f"{actor.name} kończy turę."
            print(message)
            messages.append(message)
            if adapter is not None:
                adapter.clear()
            break

        preview = preview_turn_intent(board, state, actor, source, clicked)
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
        if adapter is not None:
            adapter.clear()
            adapter.show_feedback(_preview_led_feedback(preview))
            feedback_events += 1
            observer.record("led_feedback_sent", {"phase": preview.mode.value, "actor_id": actor_id})

        confirmation_click = _confirm_preview_click(args, board, state, actor, source, preview, adapter, observer, script)
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

    return state, tuple(messages), feedback_events


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
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
    script: list[str],
) -> Coordinate | None:
    if script:
        command = script.pop(0)
        return _coordinate_from_turn_command(command, state, actor)
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
    acceptable = [position.as_tuple() for position in _acceptable_turn_positions(board, state, actor, source)]
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
    acceptable = [position.as_tuple() for position in _acceptable_turn_positions(board, state, actor, source)]
    selected = scan_board(acceptable, timeout_s=args.scan_timeout)
    if selected is None:
        observer.record("turn_intent_confirmation_cancelled", {"expected_position": list(expected)})
        return None
    confirmed = tuple(selected) == expected
    observer.record("turn_intent_confirmation_scan", {"position": list(selected), "confirmed": confirmed})
    return Coordinate(int(selected[0]), int(selected[1]))


def _coordinate_from_turn_command(command: str, state: CombatState, actor: Actor) -> Coordinate | None:
    command = command.strip()
    if command == "end":
        return None
    if command.startswith("move:"):
        return _parse_coordinate(command.removeprefix("move:"))
    if command.startswith("attack:"):
        target_id = command.removeprefix("attack:")
        return _actor_by_string_id(state, target_id).position
    raise ValueError(f"Unknown turn script command for {actor.id}: {command!r}.")


def _acceptable_turn_positions(board, state: CombatState, actor: Actor, source: AttackSource) -> tuple[Coordinate, ...]:
    positions: set[Coordinate] = set()
    if movement_remaining(state, actor) > 0:
        movement_actor = replace(actor, speed_feet=movement_remaining(state, actor))
        positions.update(movement_range(board, movement_actor, state.actors).reachable_tiles)
    if state.turn_action.action_use == ActionUse.ACTION_AVAILABLE:
        positions.update(target.position for target in legal_melee_targets(board, actor, state.actors))
    positions.discard(actor.position)
    return tuple(sorted(positions))


def _turn_options_led_feedback(board, state: CombatState, actor: Actor, source: AttackSource) -> LedFeedback:
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
    return LedFeedback(tuple(frames))


def _preview_led_feedback(preview) -> LedFeedback:
    if preview.movement_range is not None:
        return movement_led_feedback(preview.movement_range, preview.movement_path)
    if preview.attack_target is not None:
        return selected_attack_target_led_feedback(preview.attack_target)
    return LedFeedback((LedFrame((preview.clicked_position,), (255, 0, 0), LedRole.DESTINATION),))


def _turn_has_no_options(board, state: CombatState, actor: Actor, source: AttackSource) -> bool:
    has_move = movement_remaining(state, actor) > 0 and bool(_acceptable_turn_positions(board, state, actor, source))
    has_attack = state.turn_action.action_use == ActionUse.ACTION_AVAILABLE and bool(legal_melee_targets(board, actor, state.actors))
    return not has_move and not has_attack


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
