from dataclasses import dataclass, field
from typing import List, Optional

# to do make hero scrpt, 
@dataclass
class Hero:
    position: Optional[tuple[int, int]] = None
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    neighbors: List[tuple[int, int]] = field(default_factory=list)
    statuses: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.position is not None:
            self.position_x, self.position_y = self.position

    def __repr__(self):
        return f"position: {self.position}"

    def __hash__(self):
        return hash(self.position)
    
    def __eq__(self, other):
        if not isinstance(other, Hero):
            return False
        return self.position == other.position

    def set_position(self, position: Optional[tuple[int, int]]):
        self.position = position
        if position is None:
            self.position_x = None
            self.position_y = None
        else:
            self.position_x, self.position_y = position

    def make_move(self, action: str, connection):
        pass

    def _get_neighbors(self):
        pass

    def _light_tiles(self, connection):
        pass
