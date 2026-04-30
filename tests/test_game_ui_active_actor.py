from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from game import Game
from hero import Hero


class _UiCarrier:
    def __init__(self):
        self.heroes = []
        self.enemies = []
        self.events: list[tuple[str, dict]] = []

    def ui_event(self, event_type: str, payload: dict) -> bool:
        self.events.append((event_type, payload))
        return True


def test_ui_active_actor_marks_creation_hero_as_hero_kind():
    carrier = _UiCarrier()
    actor = Hero()
    actor.character_creation_in_progress = True
    actor.image = "/static/portraits/custom/test.jpg"

    Game.ui_active_actor(carrier, actor)

    assert carrier.events
    event_type, payload = carrier.events[-1]
    assert event_type == "active_actor_changed"
    assert payload.get("kind") == "hero"
    assert payload.get("image") == "/static/portraits/custom/test.jpg"
    assert payload.get("asset_id")
