from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.items.weapon import create_weapon


def test_crossbow_weapon_profile():
    weapon = create_weapon("crossbow")
    assert weapon is not None
    assert weapon.item_id == "crossbow"
    assert weapon.event_name == "crossbow"
    assert weapon.damage_prompt == "1k8"
    assert weapon.damage_type == "piercing"
    assert weapon.ranged is True
    assert int(getattr(weapon, "range_increment_ft", 0) or 0) == 120
    assert int(getattr(weapon, "reload", 0) or 0) == 1
