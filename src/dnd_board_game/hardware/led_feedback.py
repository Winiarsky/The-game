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
    INTERACTIVE_OBJECT = "interactive_object"
    MARKER = "marker"
    ALLY = "ally"
    ENEMY = "enemy"
    PROJECTILE = "projectile"
    ENEMY_FLEE_PATH = "enemy_flee_path"
    ENEMY_ESCAPE_DESTINATION = "enemy_escape_destination"
    ENEMY_REGROUP_PATH = "enemy_regroup_path"
    ENEMY_GUARD_DESTINATION = "enemy_guard_destination"
    ACTOR_DEFEATED = "actor_defeated"
    AREA_CENTER_RANGE = "area_center_range"
    AREA_EFFECT = "area_effect"
    AREA_ANCHOR = "area_anchor"


@dataclass(frozen=True, slots=True)
class LedFrame:
    positions: tuple[Coordinate, ...]
    color: tuple[int, int, int]
    role: LedRole


@dataclass(frozen=True, slots=True)
class LedFeedback:
    frames: tuple[LedFrame, ...] = field(default_factory=tuple)


class BoardConnectionLike(Protocol):
    def set_leds(
        self,
        positions,
        rgb_color,
        *,
        brightness: int | None = None,
        replace: bool = False,
        transition_ms: int | None = None,
    ) -> None: ...

    def leds_off(self) -> None: ...


DEFAULT_COLORS: dict[LedRole, tuple[int, int, int]] = {
    LedRole.ACTIVE_ACTOR: LedColor.ACTIVE_ACTOR,
    LedRole.MOVEMENT_RANGE: LedColor.MOVEMENT_RANGE,
    LedRole.SELECTED_PATH: LedColor.PLAYER_MOVEMENT_PATH,
    LedRole.DESTINATION: LedColor.MOVEMENT_DESTINATION,
    LedRole.DIFFICULT_TERRAIN: LedColor.DIFFICULT_TERRAIN,
    LedRole.BLOCKING_TERRAIN: LedColor.BLOCKING_TERRAIN,
    LedRole.INTERACTIVE_OBJECT: LedColor.INTERACTIVE_OBJECT,
    LedRole.MARKER: LedColor.MARKER,
    LedRole.ALLY: LedColor.ALLY,
    LedRole.ENEMY: LedColor.ENEMY,
    LedRole.PROJECTILE: LedColor.RANGED_PROJECTILE,
    LedRole.ENEMY_FLEE_PATH: LedColor.ENEMY_FLEE_PATH,
    LedRole.ENEMY_ESCAPE_DESTINATION: LedColor.ENEMY_ESCAPE_DESTINATION,
    LedRole.ENEMY_REGROUP_PATH: LedColor.ENEMY_REGROUP_PATH,
    LedRole.ENEMY_GUARD_DESTINATION: LedColor.ENEMY_GUARD_DESTINATION,
    LedRole.ACTOR_DEFEATED: LedColor.ACTOR_DEFEATED,
    LedRole.AREA_CENTER_RANGE: LedColor.AREA_CENTER_RANGE,
    LedRole.AREA_EFFECT: LedColor.AREA_EFFECT,
    LedRole.AREA_ANCHOR: LedColor.AREA_ANCHOR,
}


LED_ROLE_PRIORITY: dict[LedRole, int] = {
    LedRole.MOVEMENT_RANGE: 10,
    LedRole.DIFFICULT_TERRAIN: 20,
    LedRole.ACTIVE_ACTOR: 25,
    LedRole.INTERACTIVE_OBJECT: 30,
    LedRole.MARKER: 35,
    LedRole.SELECTED_PATH: 40,
    LedRole.DESTINATION: 50,
    LedRole.ALLY: 60,
    LedRole.ENEMY: 60,
    LedRole.BLOCKING_TERRAIN: 70,
    LedRole.PROJECTILE: 100,
    LedRole.ENEMY_FLEE_PATH: 42,
    LedRole.ENEMY_REGROUP_PATH: 42,
    LedRole.ENEMY_ESCAPE_DESTINATION: 52,
    LedRole.ENEMY_GUARD_DESTINATION: 52,
    LedRole.ACTOR_DEFEATED: 110,
    LedRole.AREA_CENTER_RANGE: 10,
    LedRole.AREA_EFFECT: 40,
    LedRole.AREA_ANCHOR: 50,
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
        self._last_render: tuple[
            tuple[tuple[int, int], tuple[int, int, int]], ...
        ] | None = None
        self._last_brightness: int | None = None

    def show_feedback(
        self,
        feedback: LedFeedback,
        *,
        brightness: int | None = None,
        replace: bool = False,
        transition_ms: int | None = None,
    ) -> None:
        updates: dict[tuple[int, int], tuple[int, int, int]] = {}
        for frame in sorted(feedback.frames, key=lambda item: LED_ROLE_PRIORITY[item.role]):
            for position in frame.positions:
                updates[position.as_tuple()] = frame.color
        if not updates:
            return
        rendered = tuple(sorted(updates.items()))
        if rendered == self._last_render and brightness == self._last_brightness:
            return
        positions = list(updates.keys())
        colors = [list(color) for color in updates.values()]
        color_payload = colors[0] if len({tuple(color) for color in colors}) == 1 else colors
        try:
            self.connection.set_leds(
                positions,
                color_payload,
                brightness=brightness,
                replace=replace,
                transition_ms=transition_ms,
            )
        except TypeError:
            if brightness is None:
                self.connection.set_leds(positions, color_payload)
            else:
                try:
                    self.connection.set_leds(
                        positions,
                        color_payload,
                        brightness=brightness,
                    )
                except TypeError:
                    self.connection.set_leds(positions, color_payload)
        self._last_render = rendered
        self._last_brightness = brightness

    def show_movement(self, feedback: LedFeedback) -> None:
        self.show_feedback(feedback)

    def clear(self) -> None:
        if self._last_render == ():
            return
        self.connection.leds_off()
        self._last_render = ()
        self._last_brightness = None
