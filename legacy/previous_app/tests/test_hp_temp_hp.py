from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from combat.hp_engine import apply_damage, grant_temp_hp
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from statuses import Status


@dataclass
class DummyActor(StatusMixin):
    max_hp: int = 40
    wounds: int = 0
    temp_hp: int = 0


def test_temp_hp_absorbs_damage_before_normal_hp():
    actor = DummyActor(max_hp=40, wounds=0, temp_hp=10)

    info = apply_damage(actor, 12, "normal", source="test")

    assert int(info["incoming"]) == 12
    assert int(info["temp_absorbed"]) == 10
    assert int(info["hp_damage"]) == 2
    assert actor.temp_hp == 0
    assert actor.wounds == 2
    assert int(info["current_hp"]) == 38


def test_temp_hp_clears_when_source_status_removed():
    actor = DummyActor(max_hp=40, wounds=0, temp_hp=0)
    actor.add_status(Status(id="rage", data={"temp_hp_source": "rage"}))
    grant_temp_hp(actor, 8, source="rage")

    removed = actor.remove_status("rage")

    assert removed is True
    assert actor.temp_hp == 0
