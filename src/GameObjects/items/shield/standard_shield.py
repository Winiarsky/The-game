from __future__ import annotations

from dataclasses import dataclass

from .base_shield import BaseShield


@dataclass
class StandardShield(BaseShield):
    item_id: str = "standard_shield"
    name: str = "Standard Shield"
    hardness: int = 5
    max_hp: int = 20
    broken_threshold: int = 10
