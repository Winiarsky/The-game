from __future__ import annotations

import argparse
import random
import sys
import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.combat import (
    ActorSetupEntry,
    EncounterSetup,
    EnvironmentSetupEntry,
    EnvironmentSetupType,
    InitiativeEntry,
    SetupStep,
    active_actor_led_feedback,
    build_enemy_initiative_prompt,
    build_initiative_order,
    build_player_initiative_prompts,
    build_setup_steps,
    initiative_prompt_led_feedback,
    setup_led_feedback,
)
from dnd_board_game.hardware import BoardLedAdapter
from dnd_board_game.rules import D20RollInput, resolve_d20_roll
from dnd_board_game.world import Coordinate

from .session_observer import SessionObserver


class ConnectionLike(Protocol):
    def set_leds(self, positions, rgb_color) -> None: ...

    def leds_off(self) -> None: ...


ConnectionFactory = Callable[[argparse.Namespace], ConnectionLike]


@dataclass(frozen=True, slots=True)
class DemoInitiativeSetupResult:
    messages: tuple[str, ...]
    initiative_order: tuple[str, ...]
    active_actor_id: str
    observation_path: Path
    feedback_events: int


def build_demo_encounter() -> EncounterSetup:
    hero = _actor("hero", "Bohater", Faction.ALLY, Coordinate(0, 0), dexterity=16)
    rogue = _actor("rogue", "Łotrzyca", Faction.ALLY, Coordinate(1, 0), dexterity=18)
    goblin = _actor("goblin", "Goblin", Faction.ENEMY, Coordinate(4, 2), dexterity=14)
    return EncounterSetup(
        name="Zasadzka goblinów",
        actors=(
            ActorSetupEntry(hero, "bohater", hero.position),
            ActorSetupEntry(rogue, "bohater", rogue.position),
            ActorSetupEntry(goblin, "przeciwnik", goblin.position),
        ),
        environment=(
            EnvironmentSetupEntry("rubble", "Rumowisko", EnvironmentSetupType.DIFFICULT_TERRAIN, (Coordinate(2, 1),)),
            EnvironmentSetupEntry("crates", "Skrzynie", EnvironmentSetupType.CONTAINER, (Coordinate(3, 1),)),
            EnvironmentSetupEntry("pillar", "Kamienny filar", EnvironmentSetupType.OBSTACLE, (Coordinate(2, 2),)),
        ),
    )


def run_demo(
    args: argparse.Namespace,
    *,
    connection_factory: ConnectionFactory | None = None,
) -> DemoInitiativeSetupResult:
    observer = SessionObserver(args.session_id, Path(args.observation_dir))
    observer.record(
        "session_started",
        {"runtime": "demo_initiative_setup", "encounter": "Zasadzka goblinów"},
    )
    observer.record(
        "board_backend_selected",
        {"backend": args.board_backend, "board_url": args.board_url, "show_leds": args.show_leds},
    )

    adapter = _create_adapter(args, connection_factory) if args.show_leds and args.board_backend != "none" else None
    messages: list[str] = []
    feedback_events = 0
    setup = build_demo_encounter()

    for index, step in enumerate(build_setup_steps(setup), start=1):
        message = f"Krok {index}: {step.message}"
        messages.append(message)
        observer.record("setup_step_started", _setup_step_payload(step, index))
        print(message)
        if adapter is not None:
            adapter.show_feedback(setup_led_feedback(step))
            feedback_events += 1 if step.positions else 0
            observer.record("led_feedback_sent", {"phase": "setup", "step": index, "positions": _positions_payload(step.positions)})
            _pause_for_led_step(args, "Naciśnij Enter, aby przejść do następnego kroku setupu.")
            adapter.clear()
        observer.record("setup_step_finished", {"step": index})

    actors = tuple(entry.actor for entry in setup.actors)
    entries: list[InitiativeEntry] = []
    stable_order = 0
    roll_by_actor = {"hero": args.hero_roll, "rogue": args.rogue_roll}

    for prompt in build_player_initiative_prompts(actors):
        messages.append(prompt.message)
        observer.record(
            "roll_requested",
            {"roll_type": "initiative", "actor_id": str(prompt.actor.id), "message": prompt.message},
        )
        print(prompt.message)
        if adapter is not None:
            adapter.show_feedback(initiative_prompt_led_feedback(prompt))
            feedback_events += 1
            observer.record("led_feedback_sent", {"phase": "initiative", "actor_id": str(prompt.actor.id)})
            _pause_for_led_step(args, "Naciśnij Enter po wpisaniu wyniku inicjatywy.")
        natural_roll = roll_by_actor.get(str(prompt.actor.id), args.default_player_roll)
        roll = resolve_d20_roll(D20RollInput(prompt.request, natural_roll))
        entries.append(InitiativeEntry(prompt.actor, roll, prompt.dexterity_modifier, stable_order))
        stable_order += 1
        observer.record(
            "roll_resolved",
            {
                "roll_type": "initiative",
                "actor_id": str(prompt.actor.id),
                "natural_roll": roll.natural_roll,
                "modifier_total": roll.breakdown.modifier_total,
                "total": roll.total,
            },
        )
        if adapter is not None:
            adapter.clear()

    rng = random.Random(args.enemy_seed)
    for actor in actors:
        if actor.faction == Faction.ALLY or actor.is_defeated():
            continue
        prompt = build_enemy_initiative_prompt(actor)
        if adapter is not None:
            adapter.show_feedback(initiative_prompt_led_feedback(prompt))
            feedback_events += 1
            observer.record("led_feedback_sent", {"phase": "enemy_initiative", "actor_id": str(actor.id)})
            _pause_for_led_step(args, "Naciśnij Enter, aby przejść dalej po auto-rzucie przeciwnika.")
        natural_roll = rng.randint(1, 20)
        roll = resolve_d20_roll(D20RollInput(prompt.request, natural_roll))
        message = f"Inicjatywa przeciwnika {actor.name} została rzucona automatycznie: {roll.total}."
        messages.append(message)
        print(message)
        entries.append(InitiativeEntry(actor, roll, prompt.dexterity_modifier, stable_order))
        stable_order += 1
        observer.record(
            "enemy_initiative_rolled",
            {
                "actor_id": str(actor.id),
                "natural_roll": roll.natural_roll,
                "modifier_total": roll.breakdown.modifier_total,
                "total": roll.total,
            },
        )
        if adapter is not None:
            adapter.clear()

    order = build_initiative_order(entries)
    order_message = "Kolejność inicjatywy została ustalona: " + ", ".join(entry.actor.name for entry in order.entries) + "."
    turn_message = f"Runda {order.round_number}. Tura: {order.current_actor.name}."
    messages.extend([order_message, turn_message])
    print(order_message)
    print(turn_message)
    observer.record(
        "initiative_set",
        {
            "order": [
                {
                    "actor_id": str(entry.actor.id),
                    "name": entry.actor.name,
                    "total": entry.roll.total,
                    "natural_roll": entry.roll.natural_roll,
                }
                for entry in order.entries
            ],
            "active_id": str(order.current_actor.id),
        },
    )
    observer.record("turn_started", {"round": order.round_number, "actor_id": str(order.current_actor.id)})
    if adapter is not None:
        adapter.show_feedback(active_actor_led_feedback(order))
        feedback_events += 1
        observer.record("led_feedback_sent", {"phase": "turn_started", "actor_id": str(order.current_actor.id)})
        _pause_for_led_step(args, "Naciśnij Enter, aby zakończyć demo.")
        adapter.clear()

    observer.record("session_finished", {"observation_path": str(observer.path)})
    return DemoInitiativeSetupResult(
        messages=tuple(messages),
        initiative_order=tuple(str(entry.actor.id) for entry in order.entries),
        active_actor_id=str(order.current_actor.id),
        observation_path=observer.path,
        feedback_events=feedback_events,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run debug encounter setup and initiative.")
    parser.add_argument("--board-backend", choices=("none", "simulator", "hardware"), default="none")
    parser.add_argument("--board-url", default="http://127.0.0.1:5000")
    parser.add_argument("--board-serial-port", default=None)
    parser.add_argument("--wled-url", default=None)
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--observation-dir", default="data/session_observations")
    parser.add_argument("--show-leds", dest="show_leds", action="store_true", default=False)
    parser.add_argument("--no-show-leds", dest="show_leds", action="store_false")
    parser.add_argument("--hero-roll", type=int, default=12)
    parser.add_argument("--rogue-roll", type=int, default=8)
    parser.add_argument("--default-player-roll", type=int, default=10)
    parser.add_argument("--enemy-seed", type=int, default=7)
    parser.add_argument("--step-delay", type=float, default=1.5)
    parser.add_argument("--wait-for-enter", action="store_true", default=False)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.session_id is None:
        args.session_id = f"demo_initiative_setup_{uuid.uuid4().hex[:8]}"
    try:
        run_demo(args)
    except Exception as exc:
        print(f"demo_initiative_setup failed: {exc}", file=sys.stderr)
        return 1
    return 0


def _create_adapter(args: argparse.Namespace, connection_factory: ConnectionFactory | None) -> BoardLedAdapter:
    if connection_factory is not None:
        return BoardLedAdapter(connection_factory(args))
    from board.connection import Connection

    if args.board_backend == "simulator":
        return BoardLedAdapter(Connection(backend="simulator", simulator_url=args.board_url))
    if args.board_backend == "hardware":
        return BoardLedAdapter(Connection(backend="hardware", serial_port=args.board_serial_port, wled_url=args.wled_url))
    raise ValueError("Backend 'none' does not create a board connection.")


def _pause_for_led_step(args: argparse.Namespace, prompt: str) -> None:
    if args.wait_for_enter:
        try:
            input(f"{prompt} ")
        except EOFError:
            return
        return
    if args.step_delay > 0:
        time.sleep(args.step_delay)


def _actor(actor_id: str, name: str, faction: Faction, position: Coordinate, *, dexterity: int) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=name,
        ac=12,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
        ability_scores=AbilityScores(dexterity=dexterity),
    )


def _setup_step_payload(step: SetupStep, index: int) -> dict[str, object]:
    return {
        "step": index,
        "kind": step.kind.value,
        "label": step.label,
        "message": step.message,
        "positions": _positions_payload(step.positions),
    }


def _positions_payload(positions: tuple[Coordinate, ...]) -> list[dict[str, int]]:
    return [{"col": position.col, "row": position.row} for position in positions]


if __name__ == "__main__":
    raise SystemExit(main())
