from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class Hero:
    position: Optional[Tuple[int, int]] = None
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    neighbors: List[Tuple[int, int]] = field(default_factory=list)

    def __post_init__(self):
        if self.position is not None:
            self.position_x, self.position_y = self.position

    def __repr__(self):
        return f"position: {self.position}"

    def __eq__(self, other):
        return self.position == other.position

    def set_position(self, position: Tuple[int, int]):
        self.position = position
        self.position_x, self.position_y = position

    def make_move(self, action: str, connection):
        pass

    def _get_neighbors(self):
        pass

    def _light_tiles(self, connection):
        pass
