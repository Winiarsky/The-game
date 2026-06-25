from __future__ import annotations

import argparse
import sys
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.hardware import BoardLedAdapter, LedFeedback, LedFrame, LedRole
from dnd_board_game.world import (
    BLOCKING_TERRAIN,
    DIFFICULT_TERRAIN,
    BoardState,
    Coordinate,
    MovementRangeResult,
    PathResult,
    TerrainType,
    find_path,
    movement_range,
)

from .session_observer import SessionObserver


class ConnectionLike(Protocol):
    def set_leds(self, positions, rgb_color) -> None: ...

    def leds_off(self) -> None: ...


ConnectionFactory = Callable[[argparse.Namespace], ConnectionLike]


@dataclass(frozen=True, slots=True)
class DemoScenario:
    board: BoardState
    actor: Actor
    actors: tuple[Actor, ...]


@dataclass(frozen=True, slots=True)
class DemoMovementResult:
    scenario: DemoScenario
    movement: MovementRangeResult
    path: PathResult
    feedback_sent: bool
    observation_path: Path


def parse_coordinate(value: str) -> Coordinate:
    try:
        col_text, row_text = value.split(",", maxsplit=1)
        return Coordinate(int(col_text), int(row_text))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Coordinate must use COL,ROW format, for example 3,3.") from exc


def build_demo_scenario() -> DemoScenario:
    board = BoardState()
    board.set_terrain(Coordinate(1, 0), BLOCKING_TERRAIN)
    board.set_terrain(Coordinate(2, 1), DIFFICULT_TERRAIN)
    board.set_terrain(Coordinate(3, 2), DIFFICULT_TERRAIN)
    board.add_wall(Coordinate(0, 1), Coordinate(1, 1))

    actor = Actor(
        id=ActorId("hero"),
        name="Debug Hero",
        ac=14,
        hp=20,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=Faction.ALLY,
    )
    ally = Actor(
        id=ActorId("ally"),
        name="Debug Ally",
        ac=12,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 2),
        faction=Faction.ALLY,
    )
    enemy = Actor(
        id=ActorId("enemy"),
        name="Debug Enemy",
        ac=13,
        hp=8,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(2, 0),
        faction=Faction.ENEMY,
    )
    return DemoScenario(board=board, actor=actor, actors=(actor, ally, enemy))


def run_demo(
    args: argparse.Namespace,
    *,
    connection_factory: ConnectionFactory | None = None,
) -> DemoMovementResult:
    observer = SessionObserver(args.session_id, Path(args.observation_dir))
    observer.record(
        "session_started",
        {
            "runtime": "demo_movement",
            "destination": _coordinate_payload(args.destination),
        },
    )

    scenario = build_demo_scenario()
    observer.record(
        "board_backend_selected",
        {
            "backend": args.board_backend,
            "board_url": args.board_url,
            "show_leds": args.show_leds,
        },
    )
    observer.record(
        "movement_range_requested",
        {
            "actor_id": str(scenario.actor.id),
            "origin": _coordinate_payload(scenario.actor.position),
            "speed_feet": scenario.actor.speed_feet,
        },
    )

    result = movement_range(scenario.board, scenario.actor, scenario.actors)
    observer.record(
        "movement_range_calculated",
        {
            "actor_id": str(scenario.actor.id),
            "reachable_count": len(result.reachable_tiles),
            "reachable_tiles": _coordinates_payload(result.reachable_tiles),
        },
    )

    path = find_path(scenario.board, scenario.actor, scenario.actors, args.destination)
    if path.valid:
        observer.record(
            "movement_path_selected",
            {
                "actor_id": str(scenario.actor.id),
                "destination": _coordinate_payload(path.destination),
                "cost_feet": path.cost_feet,
                "path": _coordinates_payload(path.path),
            },
        )
    else:
        observer.record(
            "movement_rejected",
            {
                "actor_id": str(scenario.actor.id),
                "destination": _coordinate_payload(path.destination),
                "known_cost_feet": path.cost_feet,
                "partial_path": _coordinates_payload(path.path),
            },
        )

    feedback_sent = False
    if args.show_leds and args.board_backend != "none":
        observer.record("led_feedback_requested", {"backend": args.board_backend})
        connection = _create_connection(args, connection_factory)
        adapter = BoardLedAdapter(connection)
        feedback = demo_movement_led_feedback(scenario, result, path if path.valid else None)
        adapter.clear()
        adapter.show_movement(feedback)
        feedback_sent = True
        observer.record(
            "led_feedback_sent",
            {
                "backend": args.board_backend,
                "frame_roles": [frame.role.value for frame in feedback.frames],
            },
        )

    observer.record(
        "session_finished",
        {
            "path_valid": path.valid,
            "feedback_sent": feedback_sent,
            "observation_path": str(observer.path),
        },
    )

    return DemoMovementResult(
        scenario=scenario,
        movement=result,
        path=path,
        feedback_sent=feedback_sent,
        observation_path=observer.path,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the first debug movement scenario.")
    parser.add_argument("--board-backend", choices=("none", "simulator", "hardware"), default="none")
    parser.add_argument("--board-url", default="http://127.0.0.1:5000")
    parser.add_argument("--board-serial-port", default=None)
    parser.add_argument("--wled-url", default=None)
    parser.add_argument("--destination", type=parse_coordinate, default=Coordinate(3, 3))
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--observation-dir", default="data/session_observations")
    parser.add_argument("--show-leds", dest="show_leds", action="store_true", default=False)
    parser.add_argument("--no-show-leds", dest="show_leds", action="store_false")
    return parser


def demo_movement_led_feedback(
    scenario: DemoScenario,
    movement: MovementRangeResult,
    selected_path: PathResult | None = None,
) -> LedFeedback:
    difficult_tiles = tuple(
        sorted(
            coordinate
            for coordinate, terrain in scenario.board.terrain_by_tile.items()
            if terrain.terrain_type == TerrainType.DIFFICULT
        )
    )
    blocking_tiles = tuple(
        sorted(
            coordinate
            for coordinate, terrain in scenario.board.terrain_by_tile.items()
            if terrain.terrain_type == TerrainType.BLOCKING
        )
    )
    allies = tuple(
        sorted(
            actor.position
            for actor in scenario.actors
            if actor.id != scenario.actor.id and actor.faction == scenario.actor.faction and not actor.is_defeated()
        )
    )
    enemies = tuple(
        sorted(
            actor.position
            for actor in scenario.actors
            if actor.id != scenario.actor.id and actor.faction != scenario.actor.faction and not actor.is_defeated()
        )
    )

    frames: list[LedFrame] = []
    range_tiles = tuple(sorted(tile for tile in movement.reachable_tiles if tile != movement.origin))
    if range_tiles:
        frames.append(LedFrame(range_tiles, (0, 80, 220), LedRole.MOVEMENT_RANGE))
    if difficult_tiles:
        frames.append(LedFrame(difficult_tiles, (255, 120, 0), LedRole.DIFFICULT_TERRAIN))
    if blocking_tiles:
        frames.append(LedFrame(blocking_tiles, (180, 0, 0), LedRole.BLOCKING_TERRAIN))
    if allies:
        frames.append(LedFrame(allies, (0, 220, 255), LedRole.ALLY))
    if enemies:
        frames.append(LedFrame(enemies, (255, 0, 80), LedRole.ENEMY))

    if selected_path is not None and selected_path.valid and selected_path.path:
        path_without_origin = tuple(tile for tile in selected_path.path if tile != movement.origin)
        if path_without_origin:
            frames.append(LedFrame(path_without_origin, (255, 210, 0), LedRole.SELECTED_PATH))
        frames.append(LedFrame((selected_path.destination,), (0, 255, 120), LedRole.DESTINATION))

    frames.append(LedFrame((movement.origin,), (255, 255, 255), LedRole.ACTIVE_ACTOR))
    return LedFeedback(tuple(frames))


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.session_id is None:
        args.session_id = f"demo_movement_{uuid.uuid4().hex[:8]}"

    try:
        result = run_demo(args)
    except Exception as exc:
        print(f"demo_movement failed: {exc}", file=sys.stderr)
        return 1

    print(_format_summary(result))
    return 0


def _create_connection(args: argparse.Namespace, connection_factory: ConnectionFactory | None) -> ConnectionLike:
    if connection_factory is not None:
        return connection_factory(args)
    from board.connection import Connection

    if args.board_backend == "simulator":
        return Connection(backend="simulator", simulator_url=args.board_url)
    if args.board_backend == "hardware":
        return Connection(backend="hardware", serial_port=args.board_serial_port, wled_url=args.wled_url)
    raise ValueError("Backend 'none' does not create a board connection.")


def _format_summary(result: DemoMovementResult) -> str:
    path_text = " -> ".join(_coordinate_text(tile) for tile in result.path.path) or "none"
    return "\n".join(
        [
            "Demo movement result:",
            f"- origin: {_coordinate_text(result.scenario.actor.position)}",
            f"- destination: {_coordinate_text(result.path.destination)}",
            f"- reachable_count: {len(result.movement.reachable_tiles)}",
            f"- path_valid: {result.path.valid}",
            f"- cost_feet: {result.path.cost_feet}",
            f"- path: {path_text}",
            f"- feedback_sent: {result.feedback_sent}",
            f"- observation_path: {result.observation_path}",
        ]
    )


def _coordinate_text(coordinate: Coordinate) -> str:
    return f"({coordinate.col},{coordinate.row})"


def _coordinate_payload(coordinate: Coordinate) -> dict[str, int]:
    return {"col": coordinate.col, "row": coordinate.row}


def _coordinates_payload(coordinates: Sequence[Coordinate] | frozenset[Coordinate]) -> list[dict[str, int]]:
    return [_coordinate_payload(coordinate) for coordinate in sorted(coordinates)]


if __name__ == "__main__":
    raise SystemExit(main())
