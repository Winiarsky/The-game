import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from GameObjects.NPC.base_npc import BaseNPC  # noqa: E402
from interactable import Interaction  # noqa: E402
from GameObjects.interactions_mixin import TradeItem  # noqa: E402


def test_flags_disable_actions():
    npc = BaseNPC(enable_trade=False, enable_pickpocket=False)
    actions = npc.actions
    assert "trade" not in actions
    assert "pickpocket" not in actions
    assert "talk" in actions
    assert "leave" in actions


def test_string_dialog_normalized():
    npc = BaseNPC(dialog="Cześć", enable_trade=False, enable_pickpocket=False)
    assert npc.dialog["start"]["text"] == "Cześć"


def test_on_trade_callback_adds_line(monkeypatch):
    called = {}

    def on_trade(self, actor):
        called["actor"] = actor
        return "Extra info"

    npc = BaseNPC(
        inventory=[TradeItem(item_id="id", name="item", price=2)],
        on_trade=on_trade,
    )
    msg = npc.action_trade("HERO", None)
    assert "Extra info" in msg
    assert called["actor"] == "HERO"


def test_on_pickpocket_fail_callback(monkeypatch):
    # force fail: roll=1, dc=16
    monkeypatch.setattr("GameObjects.NPC.base_npc.prompt_for_roll", lambda *_: 1)
    actor = type("A", (), {"statuses": ["stealth"], "stealth_bonus": 0})()
    called = {}

    def on_fail(self, act):
        called["actor"] = act
        return "Alarm!"

    npc = BaseNPC(enable_trade=False, on_pickpocket_fail=on_fail)
    msg = npc.action_pickpocket(actor, None)
    assert "Alarm!" in msg
    assert called["actor"] is actor


def test_extra_actions_hook():
    class CustomNPC(BaseNPC):
        def extra_actions(self):
            return [Interaction(id="wave", label="Pomachaj", handler=lambda *_: "Machasz.")]

    npc = CustomNPC(enable_trade=False, enable_pickpocket=False)
    assert "wave" in npc.actions
