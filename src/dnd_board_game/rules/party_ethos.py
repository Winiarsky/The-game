"""Persistent party choices; excluded mana is outside the encounter economy."""
from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True)
class PartyEthos:
    # Three steps on either side of the centre; no signed player-facing score.
    position: int = 3
    events: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.position) is not int or not 0 <= self.position <= 6:
            raise ValueError('Postawa drużyny wymaga jednego z siedmiu pól.')
        if len(set(self.events)) != len(self.events) or any(not isinstance(e, str) or not e for e in self.events):
            raise ValueError('Nieprawidłowa historia postawy drużyny.')

    @property
    def excluded(self) -> tuple[str, ...]:
        colors = ('C', 'F') if self.position < 3 else ('B', 'N')
        return tuple(c for c in colors for _ in range(abs(self.position - 3)))

    @property
    def label(self) -> str:
        return 'Solidarność' if self.position < 3 else 'Bezwzględność' if self.position > 3 else 'Równowaga'


def shift(state: PartyEthos, event_id: str, direction: str) -> PartyEthos:
    """An authored choice moves one field once, even when already at an endpoint."""
    if direction not in {'solidarity', 'ruthlessness'} or not event_id:
        raise ValueError('Nieprawidłowe zdarzenie postawy drużyny.')
    if event_id in state.events:
        return state
    position = min(6, max(0, state.position + (-1 if direction == 'solidarity' else 1)))
    return replace(state, position=position, events=(*state.events, event_id))
