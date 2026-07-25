from __future__ import annotations

import inspect
from typing import Any

from dnd_board_game.world import Coordinate

from .led_feedback import BoardLedAdapter, LedFeedback


class BoardSessionAdapter:
    """Application-facing board port for scanning and LED feedback."""

    def __init__(self, connection: object) -> None:
        self.connection = connection
        self.leds = BoardLedAdapter(connection)  # type: ignore[arg-type]
        self.atomic_led_frames = _supports_atomic_led_frames(connection)
        self.transition_ms = max(
            0,
            int(getattr(connection, "led_transition_ms", 180)),
        )
        self.scan_transition_ms = max(
            0,
            int(getattr(connection, "scan_led_transition_ms", 80)),
        )
        self.scan_brightness = max(
            1,
            min(255, int(getattr(connection, "scan_brightness", 255))),
        )

    @classmethod
    def connect(
        cls,
        *,
        backend: str,
        board_url: str = "",
        serial_port: str = "",
        wled_url: str = "",
    ) -> BoardSessionAdapter:
        from board.connection import Connection

        if backend == "simulator":
            connection = Connection(backend="simulator", simulator_url=board_url)
        elif backend == "hardware":
            connection = Connection(
                backend="hardware",
                serial_port=serial_port or None,
                wled_url=wled_url or None,
            )
        else:
            raise ValueError(f"Unsupported connected board backend: {backend}.")
        return cls(connection)

    def scan(self, positions: tuple[Coordinate, ...], *, timeout_s: float) -> Any:
        scan_board = getattr(self.connection, "scan_board", None)
        if not callable(scan_board):
            raise ValueError("Aktualny backend planszy nie obsługuje scan_board.")
        return scan_board([position.as_tuple() for position in positions], timeout_s=timeout_s)

    def reset_scan(self) -> str:
        resetter = getattr(self.connection, "reset_connection", None)
        rearmer = getattr(self.connection, "rearm_scan", None)
        canceller = getattr(self.connection, "cancel_scan", None)
        if callable(resetter):
            resetter()
            return "reset_connection"
        if callable(rearmer):
            rearmer()
            return "rearm_scan"
        if callable(canceller):
            canceller()
            return "cancel_scan"
        raise ValueError("Aktualny backend planszy nie obsługuje resetu skanu.")

    def show_feedback(self, feedback: LedFeedback) -> None:
        self._replace_feedback(feedback, transition_ms=self.transition_ms)

    def show_scan_feedback(self, feedback: LedFeedback) -> None:
        self._replace_feedback(
            feedback,
            brightness=self.scan_brightness,
            transition_ms=self.scan_transition_ms,
        )

    def restore_feedback(self, feedback: LedFeedback) -> None:
        self._replace_feedback(feedback, transition_ms=self.transition_ms)

    def _replace_feedback(
        self,
        feedback: LedFeedback,
        *,
        brightness: int | None = None,
        transition_ms: int,
    ) -> None:
        if not feedback.frames:
            self.leds.clear()
            return
        if not self.atomic_led_frames:
            self.leds.clear()
        self.leds.show_feedback(
            feedback,
            brightness=brightness,
            replace=self.atomic_led_frames,
            transition_ms=transition_ms if self.atomic_led_frames else None,
        )


def _supports_atomic_led_frames(connection: object) -> bool:
    setter = getattr(connection, "set_leds", None)
    if not callable(setter):
        return False
    try:
        parameters = inspect.signature(setter).parameters.values()
    except (TypeError, ValueError):
        return False
    return any(
        parameter.name == "replace"
        or parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in parameters
    )
