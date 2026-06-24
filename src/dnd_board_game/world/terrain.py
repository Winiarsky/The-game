from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TerrainType(StrEnum):
    NORMAL = "normal"
    DIFFICULT = "difficult"
    BLOCKING = "blocking"


@dataclass(frozen=True, slots=True)
class Terrain:
    terrain_type: TerrainType = TerrainType.NORMAL

    @property
    def blocks_movement(self) -> bool:
        return self.terrain_type == TerrainType.BLOCKING

    @property
    def is_difficult(self) -> bool:
        return self.terrain_type == TerrainType.DIFFICULT


NORMAL_TERRAIN = Terrain(TerrainType.NORMAL)
DIFFICULT_TERRAIN = Terrain(TerrainType.DIFFICULT)
BLOCKING_TERRAIN = Terrain(TerrainType.BLOCKING)
