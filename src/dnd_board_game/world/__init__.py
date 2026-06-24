"""Board topology, terrain, movement, pathfinding, and visibility."""

from .board_state import BoardState, Door, Edge, edge_between
from .coordinates import BoardDimensions, Coordinate
from .movement import (
    DIFFICULT_MOVE_COST_FEET,
    NORMAL_MOVE_COST_FEET,
    MovementRangeResult,
    PathResult,
    can_traverse,
    find_path,
    movement_cost,
    movement_range,
    neighbors,
)
from .terrain import BLOCKING_TERRAIN, DIFFICULT_TERRAIN, NORMAL_TERRAIN, Terrain, TerrainType

__all__ = [
    "BLOCKING_TERRAIN",
    "DIFFICULT_MOVE_COST_FEET",
    "DIFFICULT_TERRAIN",
    "BoardDimensions",
    "BoardState",
    "Coordinate",
    "Door",
    "Edge",
    "MovementRangeResult",
    "NORMAL_MOVE_COST_FEET",
    "NORMAL_TERRAIN",
    "PathResult",
    "Terrain",
    "TerrainType",
    "can_traverse",
    "edge_between",
    "find_path",
    "movement_cost",
    "movement_range",
    "neighbors",
]
