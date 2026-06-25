from __future__ import annotations

import argparse
import sys
import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Protocol

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.combat import (
    ActionUse,
    AttackActionState,
    AttackSource,
    AttackSourceType,
    DamageComponentInput,
    DamageType,
    apply_damage,
    attack_declaration_from_state,
    attack_result_led_feedback,
    attack_targets_led_feedback,
    resolve_attack,
    resolve_damage,
    select_attack_target,
    selected_attack_target_led_feedback,
    start_attack_action,
)
from dnd_board_game.hardware import BoardLedAdapter
from dnd_board_game.rules import D20RollInput, D20RollRequest, RollModifier, RollModifierType, resolve_d20_roll, roll_instruction
from dnd_board_game.world import BoardState, Coordinate

from .session_observer import SessionObserver


class ConnectionLike(Protocol):
    def set_leds(self, positions, rgb_color) -> None: ...

    def leds_off(self) -> None: ...

    def scan_board(self, acceptable_responses=None, *, timeout_s=None): ...


ConnectionFactory = Callable[[argparse.Namespace], ConnectionLike]


@dataclass(frozen=True, slots=True)
class DemoMiniCombatResult:
    messages: tuple[str, ...]
    attack_hit: bool
    target_hp: int
    target_temp_hp: int
    observation_path: Path
    feedback_events: int


def build_demo_combatants() -> tuple[BoardState, Actor, Actor, AttackSource]:
    hero = Actor(
        id=ActorId("hero"),
        name="Bohater",
        ac=14,
        hp=20,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=Faction.ALLY,
        ability_scores=AbilityScores(strength=16, dexterity=14),
    )
    goblin = Actor(
        id=ActorId("goblin"),
        name="Goblin",
        ac=13,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(1, 0),
        faction=Faction.ENEMY,
        ability_scores=AbilityScores(dexterity=14),
    )
    source = AttackSource(
        name="Miecz",
        source_type=AttackSourceType.WEAPON,
        range_feet=5,
        attack_roll_request=D20RollRequest(
            modifiers=(
                RollModifier("Modyfikator z Siły", 3, RollModifierType.ABILITY, stacking_key="attack_strength"),
                RollModifier("Premia z biegłości", 2, RollModifierType.PROFICIENCY, stacking_key="proficiency"),
            )
        ),
        damage_hint="1d6 slashing",
    )
    return BoardState(), hero, goblin, source


def run_demo(
    args: argparse.Namespace,
    *,
    connection_factory: ConnectionFactory | None = None,
) -> DemoMiniCombatResult:
    observer = SessionObserver(args.session_id, Path(args.observation_dir))
    observer.record("session_started", {"runtime": "demo_mini_combat"})
    observer.record(
        "board_backend_selected",
        {"backend": args.board_backend, "board_url": args.board_url, "show_leds": args.show_leds},
    )
    adapter = _create_adapter(args, connection_factory) if args.show_leds and args.board_backend != "none" else None
    board, hero, goblin, source = build_demo_combatants()
    actors = (hero, goblin)
    messages: list[str] = []
    feedback_events = 0

    action_message = f"Runda 1. Tura: {hero.name}. Wybrana akcja: Atak."
    print(action_message)
    messages.append(action_message)
    state = start_attack_action(board, hero, actors, source)
    if not state.legal_targets:
        message = "Brak legalnych celów ataku."
        print(message)
        messages.append(message)
        observer.record("attack_rejected", {"reason": "no_legal_targets", "attacker_id": str(hero.id)})
        observer.record("session_finished", {"observation_path": str(observer.path)})
        return DemoMiniCombatResult(tuple(messages), False, goblin.hp, goblin.temp_hp, observer.path, feedback_events)

    target_message = "Wybierz cel ataku. Legalne cele: " + ", ".join(target.name for target in state.legal_targets) + "."
    print(target_message)
    messages.append(target_message)
    if adapter is not None:
        adapter.show_feedback(attack_targets_led_feedback(state.legal_targets))
        feedback_events += 1
        observer.record("led_feedback_sent", {"phase": "legal_attack_targets"})

    state = _select_target(args, state, adapter, observer)
    if adapter is not None:
        adapter.clear()
    declaration = attack_declaration_from_state(state)
    observer.record(
        "attack_declared",
        {
            "attacker_id": str(declaration.attacker.id),
            "target_id": declaration.target.id,
            "source": declaration.source.name,
        },
    )

    instruction = roll_instruction(source.attack_roll_request)
    roll_message = f"Atakujesz {declaration.target.name} za pomocą {source.name}. {instruction.message}"
    print(roll_message)
    messages.append(roll_message)
    if adapter is not None:
        adapter.show_feedback(selected_attack_target_led_feedback(declaration.target))
        feedback_events += 1
        observer.record("led_feedback_sent", {"phase": "selected_attack_target", "target_id": declaration.target.id})
    natural_attack_roll = _read_int_or_default(
        args,
        f"Wpisz naturalny wynik ataku d20 albo naciśnij Enter dla wartości z CLI ({args.hero_attack_roll}): ",
        args.hero_attack_roll,
    )
    if adapter is not None:
        adapter.clear()

    attack_roll = resolve_d20_roll(D20RollInput(source.attack_roll_request, natural_attack_roll))
    resolution = resolve_attack(declaration, attack_roll, ActionUse.ACTION_AVAILABLE)
    result_message = _attack_result_message(resolution.outcome.value, declaration.target.name, attack_roll.total)
    print(result_message)
    messages.append(result_message)
    observer.record(
        "attack_resolved",
        {
            "attacker_id": str(hero.id),
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

    updated_goblin = goblin
    if resolution.hit:
        damage = resolve_damage((DamageComponentInput(args.hero_damage, DamageType(args.hero_damage_type), source.name),))
        updated_goblin = apply_damage(goblin, damage)
        damage_message = (
            f"Obrażenia: {damage.total_applied} {args.hero_damage_type}. "
            f"{goblin.name}: HP {goblin.hp} -> {updated_goblin.hp}."
        )
        print(damage_message)
        messages.append(damage_message)
        observer.record(
            "damage_applied",
            {
                "target_id": str(goblin.id),
                "components": [
                    {"amount": component.amount, "damage_type": component.damage_type.value, "label": component.label}
                    for component in damage.components
                ],
                "total_applied": damage.total_applied,
                "hp_before": goblin.hp,
                "hp_after": updated_goblin.hp,
                "temp_hp_before": goblin.temp_hp,
                "temp_hp_after": updated_goblin.temp_hp,
            },
        )

    observer.record("session_finished", {"observation_path": str(observer.path)})
    return DemoMiniCombatResult(
        messages=tuple(messages),
        attack_hit=resolution.hit,
        target_hp=updated_goblin.hp,
        target_temp_hp=updated_goblin.temp_hp,
        observation_path=observer.path,
        feedback_events=feedback_events,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run debug mini combat.")
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
    parser.add_argument("--target-id", default="goblin")
    parser.add_argument("--target-position", default=None)
    parser.add_argument("--scan-timeout", type=float, default=30.0)
    parser.add_argument("--hero-attack-roll", type=int, default=14)
    parser.add_argument("--hero-damage", type=int, default=6)
    parser.add_argument("--hero-damage-type", choices=[item.value for item in DamageType], default=DamageType.SLASHING.value)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.session_id is None:
        args.session_id = f"demo_mini_combat_{uuid.uuid4().hex[:8]}"
    try:
        run_demo(args)
    except Exception as exc:
        print(f"demo_mini_combat failed: {exc}", file=sys.stderr)
        return 1
    return 0


def _select_target(
    args: argparse.Namespace,
    state: AttackActionState,
    adapter: BoardLedAdapter | None,
    observer: SessionObserver,
) -> AttackActionState:
    if args.target_id == "none":
        raise ValueError("Attack target selection was cancelled.")
    if args.board_backend in {"simulator", "hardware"} and adapter is not None and args.target_position is None:
        connection = adapter.connection
        scan_board = getattr(connection, "scan_board", None)
        if callable(scan_board):
            acceptable = [target.position.as_tuple() for target in state.legal_targets]
            print("Kliknij pole celu w symulatorze albo na planszy. Jeśli skan nie zwróci pola, użyję fallbacku --target-id.")
            observer.record("board_scan_requested", {"acceptable_positions": [list(position) for position in acceptable]})
            try:
                selected = scan_board(acceptable, timeout_s=args.scan_timeout)
            except Exception as exc:
                observer.record("board_scan_error", {"error": str(exc), "fallback_target_id": args.target_id})
                print(f"Skan celu nie powiódł się, używam fallbacku: {args.target_id}.")
            else:
                if selected is not None:
                    observer.record("board_scan_received", {"position": list(selected)})
                    try:
                        return select_attack_target(state, position=Coordinate(int(selected[0]), int(selected[1])))
                    except ValueError:
                        observer.record(
                            "attack_target_rejected",
                            {"position": list(selected), "fallback_target_id": args.target_id},
                        )
                        print(f"Wybrane pole {tuple(selected)} nie jest legalnym celem, używam fallbacku: {args.target_id}.")
                else:
                    observer.record("board_scan_cancelled", {"fallback_target_id": args.target_id})
                    print(f"Nie wybrano celu na planszy, używam fallbacku: {args.target_id}.")
    if args.target_position is not None:
        return select_attack_target(state, position=_parse_coordinate(args.target_position))
    return select_attack_target(state, target_id=args.target_id)


def _create_adapter(args: argparse.Namespace, connection_factory: ConnectionFactory | None) -> BoardLedAdapter:
    if connection_factory is not None:
        return BoardLedAdapter(connection_factory(args))
    from board.connection import Connection

    if args.board_backend == "simulator":
        return BoardLedAdapter(Connection(backend="simulator", simulator_url=args.board_url))
    if args.board_backend == "hardware":
        return BoardLedAdapter(Connection(backend="hardware", serial_port=args.board_serial_port, wled_url=args.wled_url))
    raise ValueError("Backend 'none' does not create a board connection.")


def _parse_coordinate(value: str) -> Coordinate:
    col_text, row_text = value.split(",", maxsplit=1)
    return Coordinate(int(col_text), int(row_text))


def _pause_for_led_step(args: argparse.Namespace, prompt: str) -> None:
    if args.wait_for_enter:
        try:
            input(f"{prompt} ")
        except EOFError:
            return
        return
    if args.step_delay > 0:
        time.sleep(args.step_delay)


def _read_int_or_default(args: argparse.Namespace, prompt: str, default: int) -> int:
    if not args.wait_for_enter:
        if args.step_delay > 0:
            time.sleep(args.step_delay)
        return default
    try:
        value = input(prompt).strip()
    except EOFError:
        return default
    if not value:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Expected an integer value, got: {value!r}.") from exc


def _attack_result_message(outcome: str, target_name: str, total: int) -> str:
    labels = {
        "critical_hit": "Trafienie krytyczne",
        "hit": "Trafienie",
        "miss": "Pudło",
        "critical_miss": "Krytyczne pudło",
    }
    return f"{labels[outcome]} przeciwko {target_name}. Wynik ataku: {total}."


if __name__ == "__main__":
    raise SystemExit(main())
