from pathlib import Path
import sys
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.Interactables.hidden_cache import HiddenCache
from GameObjects.NPC.bound_smuggler_npc import BoundSmugglerNPC


class _SessionStub:
    def __init__(self):
        self.global_flags = {}
        self.reveals = []

    def reveal_object(self, map_id, target_id, *, state_updates=None, message=None):
        self.reveals.append((map_id, target_id, dict(state_updates or {}), message))
        return True


def test_bound_smuggler_diplomacy_reveals_upper_cache_and_disarms_trap(monkeypatch):
    session = _SessionStub()
    game = SimpleNamespace(scenario_session=session)
    actor = SimpleNamespace(name="Hero")
    npc = BoundSmugglerNPC()

    monkeypatch.setattr(
        "GameObjects.NPC.bound_smuggler_npc.resolve_skill_check_with_sources",
        lambda **_kwargs: SimpleNamespace(outcome="success", total=19),
    )

    message = npc.action_diplomacy_cache(actor, game)

    assert "skrytkę" in message
    assert session.global_flags["upper_cache_revealed"] is True
    assert session.global_flags["upper_cache_revealed_by_marek"] is True
    assert session.reveals
    map_id, target_id, updates, _log = session.reveals[-1]
    assert map_id == "treasure_room"
    assert target_id == "upper_smuggler_cache"
    assert updates["hidden"] is False
    assert updates["revealed"] is True
    assert updates["trap_armed"] is False


def test_hidden_cache_revealed_by_seek_keeps_opening_trap_armed():
    cache = HiddenCache(
        cache_id="upper_smuggler_cache",
        hidden=True,
        allow_hidden_interaction=False,
        reveal_dc=17,
        trap_armed=True,
        trap_name="Igłowa pułapka skrytki",
        trap_effect="Igła odpala alarm.",
        loot=["ledger"],
    )

    outcome, _message = cache.try_reveal(25)
    open_message = cache.action_open(SimpleNamespace(name="Hero"), SimpleNamespace())

    assert outcome in {"success", "critical_success"}
    assert cache.revealed is True
    assert cache.hidden is True
    assert cache.revealed_by_seek is True
    assert cache.trap_triggered is True
    assert cache.trap_armed is False
    assert "Igłowa pułapka skrytki" in open_message
