from statuses import Status, CONCEALED_STATUS
from skills import Skill
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources_from_roll

from statuses.race.halfling.keen_eyes import KeenEyesStatus
import importlib.util
import sys
import types
from pathlib import Path


class Dummy:
    def __init__(self):
        self.statuses = []

    def add_status(self, status):
        self.statuses.append(status)

    def has_status(self, status_id):
        return any(getattr(s, "id", s) == status_id for s in self.statuses)


def test_keen_eyes_seek_bonus():
    actor = Dummy()
    actor.add_status(KeenEyesStatus())
    res = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.PERCEPTION.value,
        dc=15,
        actor=actor,
        tags=["seek", Skill.PERCEPTION.value],
        roll=13,
        apply_modifiers=True,
    )
    assert res.modifier == 2
    assert res.total == 15
    assert res.outcome == "success"


def test_keen_eyes_reduces_concealed_dc(monkeypatch):
    attacker = Dummy()
    attacker.add_status(KeenEyesStatus())
    target = Dummy()
    target.add_status(CONCEALED_STATUS)

    class Ctx:
        def __init__(self, actor):
            self.actor = actor
            self.game = type("G", (), {"ui": None, "ui_log": lambda *_a, **_k: None})()

    attack_base = _load_attack_base()
    monkeypatch.setattr(attack_base, "prompt_for_roll", lambda *a, **k: 3)
    assert attack_base.check_concealed(Ctx(attacker), target) is True


def test_concealed_default_dc(monkeypatch):
    attacker = Dummy()
    target = Dummy()
    target.add_status(CONCEALED_STATUS)

    class Ctx:
        def __init__(self, actor):
            self.actor = actor
            self.game = type("G", (), {"ui": None, "ui_log": lambda *_a, **_k: None})()

    attack_base = _load_attack_base()
    monkeypatch.setattr(attack_base, "prompt_for_roll", lambda *a, **k: 3)
    assert attack_base.check_concealed(Ctx(attacker), target) is False


def _load_attack_base():
    root = Path(__file__).resolve().parents[1]
    base_path = root / "src" / "GameObjects" / "events" / "base.py"
    attack_path = root / "src" / "GameObjects" / "events" / "attack" / "attack_base.py"

    sys.modules.setdefault("GameObjects", types.ModuleType("GameObjects"))
    events_pkg = sys.modules.setdefault("GameObjects.events", types.ModuleType("GameObjects.events"))
    setattr(events_pkg, "__path__", [str(root / "src" / "GameObjects" / "events")])
    attack_pkg = sys.modules.setdefault("GameObjects.events.attack", types.ModuleType("GameObjects.events.attack"))
    setattr(attack_pkg, "__path__", [str(root / "src" / "GameObjects" / "events" / "attack")])

    if "GameObjects.events.base" not in sys.modules:
        base_spec = importlib.util.spec_from_file_location("GameObjects.events.base", base_path)
        base_mod = importlib.util.module_from_spec(base_spec)
        assert base_spec and base_spec.loader
        sys.modules["GameObjects.events.base"] = base_mod
        base_spec.loader.exec_module(base_mod)

    attack_spec = importlib.util.spec_from_file_location("GameObjects.events.attack.attack_base", attack_path)
    attack_mod = importlib.util.module_from_spec(attack_spec)
    assert attack_spec and attack_spec.loader
    attack_spec.loader.exec_module(attack_mod)
    return attack_mod
