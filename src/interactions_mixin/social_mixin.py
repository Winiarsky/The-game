from __future__ import annotations

from dataclasses import dataclass

AttitudeLabel = str


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def attitude_label(attitude: int) -> AttitudeLabel:
    """Mapuje liczbę na etykietę postawy."""
    if attitude <= -2:
        return "wrogi"
    if attitude == -1:
        return "podejrzliwy"
    if attitude == 0:
        return "neutralny"
    if attitude == 1:
        return "życzliwy"
    return "przyjacielski"


@dataclass
class SocialMixin:
    attitude: int = 0  # -2 wrogi, -1 podejrzliwy, 0 neutralny, 1 życzliwy, 2+ przyjacielski
    min_attitude: int = -2
    max_attitude: int = 2

    def adjust_attitude(self, delta: int) -> tuple[int, AttitudeLabel]:
        self.attitude = clamp(self.attitude + delta, self.min_attitude, self.max_attitude)
        return self.attitude, attitude_label(self.attitude)
