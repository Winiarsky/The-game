import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from GameObjects.NPC.base_npc import BaseNPC  # noqa: E402
from GameObjects.events.base import EventResult  # noqa: E402
from GameObjects.interactions_mixin.base_interaction import Interaction  # noqa: E402
from GameObjects.interactions_mixin import TradeItem  # noqa: E402
from GameObjects.items.inventory import ensure_actor_inventory  # noqa: E402
from economy import set_actor_total_cp  # noqa: E402


def test_flags_disable_actions():
    npc = BaseNPC(enable_trade=False, enable_pickpocket=False)
    actions = npc.actions
    assert "trade" not in actions
    assert "pickpocket" not in actions
    assert "talk" in actions
    assert "dialog" in actions["talk"].tags
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
    monkeypatch.setattr("GameObjects.NPC.base_npc.prompt_for_roll", lambda *_, **__:1)
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
            return [Interaction(id="wave", label="Pomachaj", handler=lambda *_, **__:"Machasz.")]

    npc = CustomNPC(enable_trade=False, enable_pickpocket=False)
    assert "wave" in npc.actions


class FakeDialogUI:
    enabled = True
    allow_cli_fallback = False

    def __init__(self, choices=None):
        self.choices = list(choices or [])
        self.info_calls = []
        self.choice_calls = []

    def prompt_choice(self, *args, **kwargs):
        self.choice_calls.append({"args": args, **kwargs})
        if self.choices:
            return self.choices.pop(0)
        return None

    def prompt_info(self, *args, **kwargs):
        self.info_calls.append({"args": args, **kwargs})
        return "ok"


def test_dialog_tree_uses_blocking_prompts_and_sets_flags(monkeypatch):
    def fake_dispatch(_name, ctx):
        return EventResult(success=True, data={"outcome": "critical_success", "total": 25})

    monkeypatch.setattr("GameObjects.NPC.base_npc.dispatch_event", fake_dispatch)

    actor = type("Actor", (), {"statuses": [], "inventory": [], "coin_pouch": {"cp": 0, "sp": 0, "gp": 0, "pp": 0}})()
    session = type("Session", (), {"global_flags": {}})()
    ui = FakeDialogUI(choices=["Ask"])
    game = type("Game", (), {"ui": ui, "scenario_session": session})()
    npc = BaseNPC(
        name="Witness",
        npc_id="witness",
        enable_trade=False,
        enable_pickpocket=False,
        enable_diplomacy=False,
        dialog={
            "start": {
                "text": "Opening",
                "options": [
                    {
                        "id": "ask",
                        "label": "Ask",
                        "skill_check": {
                            "skill_id": "diplomacy",
                            "dc": 15,
                            "outcomes": {
                                "critical_success": {
                                    "text": "Truth.",
                                    "effects": [{"type": "set_flag", "flag": "truth_known"}],
                                }
                            },
                        },
                    }
                ],
            }
        },
    )

    message = npc.action_talk(actor, game)

    assert "Truth" in message
    assert session.global_flags["truth_known"] is True
    assert len(ui.choice_calls) == 1
    assert len(ui.info_calls) == 1
    assert ui.info_calls[0]["scope_key"] == "dialog:witness"
    assert ui.info_calls[0]["prompt_id"] == "dialog.witness.ask"
    assert ui.info_calls[0]["image"].endswith("/default_actor.png")


def test_dialog_plain_option_result_uses_blocking_prompt():
    actor = type("Actor", (), {"statuses": [], "inventory": [], "coin_pouch": {"cp": 0, "sp": 0, "gp": 0, "pp": 0}})()
    session = type("Session", (), {"global_flags": {}})()
    ui = FakeDialogUI(choices=["Ask"])
    game = type("Game", (), {"ui": ui, "scenario_session": session})()
    npc = BaseNPC(
        name="Nila",
        npc_id="nila",
        enable_trade=False,
        enable_pickpocket=False,
        enable_diplomacy=False,
        dialog={
            "start": {
                "text": "Nila patrzy na patrol.",
                "options": [{"id": "ask", "label": "Ask", "text": "Nila szepcze wskazówkę."}],
            }
        },
    )

    message = npc.action_talk(actor, game)

    assert message == "Nila szepcze wskazówkę."
    assert len(ui.choice_calls) == 1
    assert len(ui.info_calls) == 1
    assert ui.info_calls[0]["args"][0] == "Nila"
    assert ui.info_calls[0]["prompt_long"] == "Nila szepcze wskazówkę."
    assert ui.choice_calls[0]["image"].endswith("/default_actor.png")


def test_dialog_offer_purchase_adds_selected_items():
    actor = type("Actor", (), {"statuses": [], "inventory": [], "coin_pouch": {"cp": 0, "sp": 0, "gp": 0, "pp": 0}})()
    set_actor_total_cp(actor, 500)
    ui = FakeDialogUI(choices=["Kup 2"])
    game = type("Game", (), {"ui": ui, "scenario_session": type("Session", (), {"global_flags": {}})()})()
    npc = BaseNPC(name="Herbalist", enable_trade=False, enable_pickpocket=False, enable_diplomacy=False)

    message = npc._dialog_offer_purchase(
        actor,
        game,
        {"item_id": "brindleford_healing_herb", "quantity": 5, "price_cp": 100},
    )

    inventory_ids = [str(getattr(item, "item_id", "")) for item in ensure_actor_inventory(actor)]
    assert message.startswith("Kupiono: 2")
    assert inventory_ids.count("brindleford_healing_herb") == 2
