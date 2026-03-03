from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from bonuses import BonusEffect, BonusType
from combat.reactions.reactive_shield_reaction import ReactiveShieldReaction
from GameObjects.interactions_mixin import BonusMixin, StatusMixin
from GameObjects.items.shield import StandardShield
from statuses import Status


class DummyActor(StatusMixin, BonusMixin):
    def __init__(self, name: str = "Hero"):
        super().__init__()
        self.name = name
        self.bonuses = []
        self.statuses = [Status(id="reactive_shield")]
        self.equipped_shield = StandardShield()


def _event_for(actor, *, action_id: str = "attack_sword_pre", action_tags: list[str] | None = None) -> dict[str, object]:
    return {
        "target": actor,
        "action_id": action_id,
        "action_tags": list(action_tags or ["attack_melee"]),
    }


def test_reactive_shield_triggers_on_melee_pre():
    actor = DummyActor()
    reaction = ReactiveShieldReaction()

    assert reaction.triggers(actor, _event_for(actor)) is True
    assert reaction.triggers(actor, _event_for(actor, action_id="attack_sword")) is False
    assert reaction.triggers(actor, _event_for(actor, action_tags=["attack_ranged"])) is False


def test_reactive_shield_execute_applies_raise_shield_bonus_for_triggering_attack():
    actor = DummyActor()
    actor.add_bonus(
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=1,
            tag="ac",
            source="raise_shield:round0",
            label="old shield bonus",
            duration_turns=1,
        )
    )
    reaction = ReactiveShieldReaction()
    logs: list[str] = []
    game = SimpleNamespace(state=SimpleNamespace(round_index=3), ui_log=lambda msg: logs.append(str(msg)))
    ctx = SimpleNamespace(game=game)

    executed = reaction.execute(actor, _event_for(actor), ctx)

    assert executed is True
    ac_bonuses = [item for item in actor.bonuses if getattr(item, "tag", None) == "ac"]
    assert len(ac_bonuses) == 1
    assert int(getattr(ac_bonuses[0], "value", 0) or 0) == 2
    assert str(getattr(ac_bonuses[0], "source", "")).startswith("raise_shield:")
    assert any("Reactive Shield" in line for line in logs)
