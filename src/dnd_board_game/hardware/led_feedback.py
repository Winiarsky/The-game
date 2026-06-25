from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from dnd_board_game.world import Coordinate, MovementRangeResult, PathResult


class LedRole(StrEnum):
    ACTIVE_ACTOR = "active_actor"
    MOVEMENT_RANGE = "movement_range"
    SELECTED_PATH = "selected_path"
    DESTINATION = "destination"
    DIFFICULT_TERRAIN = "difficult_terrain"
    BLOCKING_TERRAIN = "blocking_terrain"
    ALLY = "ally"
    ENEMY = "enemy"


@dataclass(frozen=True, slots=True)
class LedFrame:
    positions: tuple[Coordinate, ...]
    color: tuple[int, int, int]
    role: LedRole


@dataclass(frozen=True, slots=True)
class LedFeedback:
    frames: tuple[LedFrame, ...] = field(default_factory=tuple)


class BoardConnectionLike(Protocol):
    def set_leds(self, positions, rgb_color) -> None: ...

    def leds_off(self) -> None: ...


DEFAULT_COLORS: dict[LedRole, tuple[int, int, int]] = {
    LedRole.ACTIVE_ACTOR: (255, 255, 255),
    LedRole.MOVEMENT_RANGE: (0, 80, 220),
    LedRole.SELECTED_PATH: (255, 210, 0),
    LedRole.DESTINATION: (0, 255, 120),
    LedRole.DIFFICULT_TERRAIN: (255, 120, 0),
    LedRole.BLOCKING_TERRAIN: (180, 0, 0),
    LedRole.ALLY: (0, 220, 255),
    LedRole.ENEMY: (255, 0, 80),
}


def movement_led_feedback(
    result: MovementRangeResult,
    selected_path: PathResult | None = None,
    *,
    colors: dict[LedRole, tuple[int, int, int]] | None = None,
) -> LedFeedback:
    palette = dict(DEFAULT_COLORS)
    if colors:
        palette.update(colors)

    frames: list[LedFrame] = [
        LedFrame((result.origin,), palette[LedRole.ACTIVE_ACTOR], LedRole.ACTIVE_ACTOR),
    ]
    range_tiles = tuple(sorted(tile for tile in result.reachable_tiles if tile != result.origin))
    if range_tiles:
        frames.append(LedFrame(range_tiles, palette[LedRole.MOVEMENT_RANGE], LedRole.MOVEMENT_RANGE))

    if selected_path is not None and selected_path.valid and selected_path.path:
        path_without_origin = tuple(tile for tile in selected_path.path if tile != result.origin)
        if path_without_origin:
            frames.append(LedFrame(path_without_origin, palette[LedRole.SELECTED_PATH], LedRole.SELECTED_PATH))
        frames.append(LedFrame((selected_path.destination,), palette[LedRole.DESTINATION], LedRole.DESTINATION))

    return LedFeedback(tuple(frames))


class BoardLedAdapter:
    def __init__(self, connection: BoardConnectionLike) -> None:
        self.connection = connection

    def show_movement(self, feedback: LedFeedback) -> None:
        for frame in feedback.frames:
            self.connection.set_leds([position.as_tuple() for position in frame.positions], list(frame.color))

    def clear(self) -> None:
        self.connection.leds_off()
