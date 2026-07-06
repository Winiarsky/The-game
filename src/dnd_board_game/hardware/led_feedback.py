from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from dnd_board_game.hardware.led_palette import LedColor
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
    LedRole.ACTIVE_ACTOR: LedColor.ACTIVE_ACTOR,
    LedRole.MOVEMENT_RANGE: LedColor.MOVEMENT_RANGE,
    LedRole.SELECTED_PATH: LedColor.PLAYER_MOVEMENT_PATH,
    LedRole.DESTINATION: LedColor.MOVEMENT_DESTINATION,
    LedRole.DIFFICULT_TERRAIN: LedColor.DIFFICULT_TERRAIN,
    LedRole.BLOCKING_TERRAIN: LedColor.BLOCKING_TERRAIN,
    LedRole.ALLY: LedColor.ALLY,
    LedRole.ENEMY: LedColor.ENEMY,
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

    def show_feedback(self, feedback: LedFeedback) -> None:
        updates: dict[tuple[int, int], tuple[int, int, int]] = {}
        for frame in feedback.frames:
            for position in frame.positions:
                updates[position.as_tuple()] = frame.color
        if not updates:
            return
        positions = list(updates.keys())
        colors = [list(color) for color in updates.values()]
        if len({tuple(color) for color in colors}) == 1:
            self.connection.set_leds(positions, colors[0])
        else:
            self.connection.set_leds(positions, colors)

    def show_movement(self, feedback: LedFeedback) -> None:
        self.show_feedback(feedback)

    def clear(self) -> None:
        self.connection.leds_off()
