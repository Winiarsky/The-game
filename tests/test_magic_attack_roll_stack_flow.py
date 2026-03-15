import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from bonuses import BonusEffect, BonusType
from GameObjects.events.base import EventContext, EventResult
from GameObjects.events.magic import base_attack_magic_event
from GameObjects.events.magic.base_attack_magic_event import BaseMagicAttackEvent


class _DummySpellAttack(BaseMagicAttackEvent):
    name = "test_spell_attack_flow"
    default_tags = ["spell_attack"]
    range_feet = 30

    def _resolve_on_target(self, target, pos, ctx, *, critical=False):
        return EventResult(success=True, consumed_action=self.consumes_action, message="trafienie")


class _DummyTarget:
    def __init__(self):
        self.position = (1, 0)
        self.ac = 10
        self.bonuses = []


class _DummyGame:
    def __init__(self, actor, target):
        self.heroes = [actor]
        self.enemies = [target]
        self.events = SimpleNamespace(safe_emit_action=lambda **_k: None)
        self.ui_log = lambda *_a, **_k: None


def test_magic_attack_roll_stack_contains_auto_modifier(monkeypatch):
    target = _DummyTarget()
    actor = SimpleNamespace(
        position=(0, 0),
        bonuses=[BonusEffect(BonusType.STATUS, 14, "spell_attack", source="spell_prof", label="spell attack")],
        statuses=[],
    )
    game = _DummyGame(actor, target)
    ctx = EventContext(game=game, actor=actor)
    captured = {}

    monkeypatch.setattr(base_attack_magic_event, "pick_target_in_range", lambda *_a, **_k: (target, target.position))
    monkeypatch.setattr(base_attack_magic_event, "check_concealed", lambda *_a, **_k: True)

    def _prompt(_prompt, **kwargs):
        captured.update(kwargs)
        return {"roll": 10, "raw_roll": 10}

    monkeypatch.setattr(base_attack_magic_event, "prompt_for_roll", _prompt)

    result = _DummySpellAttack().execute(ctx)
    assert result.success

    stack = captured.get("roll_stack", {})
    components = list(stack.get("components", []) or [])
    assert len(components) == 1
    assert str(components[0].get("id")) == "spell_attack"
    assert int(components[0].get("value", 0) or 0) == 14
    assert int(stack.get("auto_total_modifier", 0) or 0) == 14
