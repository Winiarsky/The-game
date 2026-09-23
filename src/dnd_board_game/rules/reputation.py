"""Shared, finite campaign reputation with idempotent authored events."""
from __future__ import annotations

from dataclasses import dataclass, replace

STARTING_REPUTATION = 20
BOOSTS = (("plus_one", 1, 1), ("plus_five", 3, 5), ("extra_die", 5, 0))


@dataclass(frozen=True, slots=True)
class Reputation:
    points: int = STARTING_REPUTATION
    events: tuple[tuple[str, int], ...] = ()

    def __post_init__(self) -> None:
        if type(self.points) is not int or self.points < 0:
            raise ValueError("Reputacja nie może być ujemna.")
        if (len({key for key, _ in self.events}) != len(self.events)
                or any(not key or type(amount) is not int for key, amount in self.events)):
            raise ValueError("Nieprawidłowa historia reputacji.")


def change(state: Reputation, event_id: str, amount: int, *, minimum: int = 0) -> Reputation:
    """A repeated saved event never pays or awards its amount a second time."""
    if not event_id or type(amount) is not int or type(minimum) is not int or minimum < 0:
        raise ValueError("Nieprawidłowa zmiana reputacji.")
    previous = dict(state.events)
    if event_id in previous:
        if previous[event_id] != amount:
            raise ValueError("Zdarzenie reputacji ma już inną wartość.")
        return state
    if state.points < minimum or state.points + amount < 0:
        raise ValueError("Drużyna ma za mało reputacji.")
    return replace(state, points=state.points + amount, events=(*state.events, (event_id, amount)))
