import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.events.base import EventContext  # noqa: E402
from GameObjects.events.raise_shield_event import RaiseShieldEvent  # noqa: E402
from character_creation.pipeline import hero_from_snapshot  # noqa: E402
from combat import ac_with_bonuses, effective_ac  # noqa: E402
from ui_payloads import build_hero_snapshot  # noqa: E402


class CombatCtx(EventContext):
    @property
    def in_combat(self):  # type: ignore[override]
        return True

    @property
    def in_exploration(self):  # type: ignore[override]
        return False


class DummyGame:
    def __init__(self, round_idx=1):
        self.state = type("S", (), {"round_index": round_idx})()
        self.logs = []

    def ui_log(self, message):
        self.logs.append(str(message))


def _load_christopher_snapshot():
    path = PROJECT_ROOT / "data" / "heroes" / "christopher.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_christopher_runtime_ac_includes_equipped_scale_mail():
    hero = hero_from_snapshot(_load_christopher_snapshot())

    assert hero.ac == 18
    total_ac, base_ac, modifier = ac_with_bonuses(hero)
    assert base_ac == 18
    assert modifier == 0
    assert total_ac == 18
    assert effective_ac(hero) == 18


def test_christopher_raise_shield_updates_runtime_and_ui_snapshot_ac():
    hero = hero_from_snapshot(_load_christopher_snapshot())
    ctx = CombatCtx(game=DummyGame(round_idx=2), actor=hero)

    result = RaiseShieldEvent().execute(ctx)

    assert result.success
    total_ac, base_ac, modifier = ac_with_bonuses(hero)
    assert base_ac == 18
    assert modifier == 2
    assert total_ac == 20
    assert effective_ac(hero) == 20

    payload = build_hero_snapshot(hero)
    assert payload["ac"] == 20
    assert payload["ac_base"] == 18
    assert payload["ac_modifier"] == 2
