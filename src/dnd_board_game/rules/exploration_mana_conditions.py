"""Optional social conditions. No content, transport or side effects."""
from dataclasses import dataclass

from .exploration_mana_catalog import COLORS


@dataclass(frozen=True, slots=True)
class ManaCondition:
    kind: str = 'none'
    color: str = ''
    count: int = 2
    minimum: int = 15
    maximum: int = 17

    def __post_init__(self) -> None:
        if self.kind not in {'none', 'compromise', 'sensitive_topic', 'color_goal', 'favor'}:
            raise ValueError('Nieznany warunek rozmowy.')
        if self.kind in {'sensitive_topic', 'color_goal'} and self.color not in COLORS:
            raise ValueError('Warunek wymaga prawidłowego koloru.')
        if type(self.count) is not int or not 1 <= self.count <= 5:
            raise ValueError('Cel wymaga od jednej do pięciu kart.')
        if not (type(self.minimum) is type(self.maximum) is int and 1 <= self.minimum <= self.maximum < 21):
            raise ValueError('Nieprawidłowy zakres porozumienia.')
