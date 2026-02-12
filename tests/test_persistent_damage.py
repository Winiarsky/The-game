from types import SimpleNamespace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from statuses import make_persistent_damage, process_persistent_damage


class DummyActor:
    def __init__(self, name="actor"):
        self.name = name
        self.statuses = []
        self.damage_taken = 0

    def apply_damage(self, amount, damage_type):
        self.damage_taken += amount
        return self.damage_taken, False

    def remove_status(self, status):
        target_id = status.id if hasattr(status, "id") else str(status)
        self.statuses = [s for s in self.statuses if getattr(s, "id", None) != target_id]
        return True


def test_persistent_damage_hero_removed_on_success(monkeypatch):
    actor = DummyActor("hero")
    actor.statuses.append(make_persistent_damage(3, "fire"))
    logs = []
    game = SimpleNamespace(heroes=[actor], enemies=[], ui_log=lambda msg: logs.append(msg))
    monkeypatch.setattr("statuses.persistent_damage.prompt_for_roll", lambda prompt: 16)

    process_persistent_damage(actor, game)

    assert actor.damage_taken == 3
    assert not actor.statuses  # removed
    assert any("Persistent damage ustaje" in msg for msg in logs)


def test_persistent_damage_enemy_persists_on_fail(monkeypatch):
    enemy = DummyActor("enemy")
    enemy.statuses.append(make_persistent_damage(5, "acid"))
    logs = []
    game = SimpleNamespace(heroes=[], enemies=[enemy], ui_log=lambda msg: logs.append(msg))
    monkeypatch.setattr("statuses.persistent_damage.random.randint", lambda a, b: 10)

    process_persistent_damage(enemy, game)

    assert enemy.damage_taken == 5
    assert enemy.statuses  # still present
    assert any("utrzymuje się" in msg for msg in logs)


def test_persistent_damage_stacks_same_type(monkeypatch):
    actor = DummyActor("hero")
    actor.statuses.append(make_persistent_damage(2, "fire"))
    actor.statuses.append(make_persistent_damage(3, "fire"))
    logs = []
    game = SimpleNamespace(heroes=[actor], enemies=[], ui_log=lambda msg: logs.append(msg))
    monkeypatch.setattr("statuses.persistent_damage.prompt_for_roll", lambda prompt: 10)

    process_persistent_damage(actor, game)

    assert actor.damage_taken == 5  # summed
    assert actor.statuses  # not removed on failed flat check
    assert any("5 obrażeń" in msg for msg in logs)


def test_persistent_damage_enemy_removed_on_high_roll(monkeypatch):
    enemy = DummyActor("enemy")
    enemy.statuses.append(make_persistent_damage(4, "poison"))
    logs = []
    game = SimpleNamespace(heroes=[], enemies=[enemy], ui_log=lambda msg: logs.append(msg))
    monkeypatch.setattr("statuses.persistent_damage.random.randint", lambda a, b: 19)

    process_persistent_damage(enemy, game)

    assert enemy.damage_taken == 4
    assert not enemy.statuses  # removed on good roll
    assert any("ustaje" in msg for msg in logs)
