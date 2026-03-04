from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from combat.reactions.nimble_dodge_reaction import NimbleDodgeReaction
from GameObjects.events.attack.attack_base import AttackEventBase
from statuses import Status


class DummyAttack(AttackEventBase):
    name = "dummy_attack"


class DummyActor:
    def __init__(self, object_id: str, *, ac: int = 15):
        self.object_id = object_id
        self.name = object_id
        self.ac = ac
        self.statuses = [Status(id="nimble_dodge")]
        self.bonuses = []

    def has_status(self, status_id: str) -> bool:
        return any(getattr(item, "id", item) == status_id for item in self.statuses)

    def add_bonus(self, effect):
        self.bonuses.append(effect)


def test_nimble_dodge_reaction_applies_and_consumes_bonus_for_triggering_attack():
    defender = DummyActor("hero")
    attacker = DummyActor("enemy")
    reaction = NimbleDodgeReaction()
    event = {
        "event_uid": "ev:test",
        "actor": attacker,
        "target": defender,
        "action_id": "attack_sword_pre",
        "action_tags": ["attack_melee"],
    }
    ctx = SimpleNamespace(game=SimpleNamespace(ui_log=lambda *_a, **_k: None))

    assert reaction.triggers(defender, event) is True
    assert reaction.execute(defender, event, ctx) is True

    attack = DummyAttack()
    ac_before, _base_ac, modifier = attack._ac_with_bonuses(defender, attacker=attacker)
    assert modifier == 2
    assert ac_before == 17

    attack._consume_nimble_dodge_bonus(defender, attacker)
    ac_after, _base_ac2, modifier_after = attack._ac_with_bonuses(defender, attacker=attacker)
    assert modifier_after == 0
    assert ac_after == 15

