from __future__ import annotations

from typing import Any

from dnd_board_game.world import Coordinate

from .led_feedback import BoardLedAdapter, LedFeedback


class BoardSessionAdapter:
    """Application-facing board port for scanning and LED feedback."""

    def __init__(self, connection: object) -> None:
        self.connection = connection
        self.leds = BoardLedAdapter(connection)  # type: ignore[arg-type]

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
        self.leds.clear()
        if feedback.frames:
            self.leds.show_feedback(feedback)

