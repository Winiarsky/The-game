from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.NPC.base_npc import BaseNPC  # noqa: E402
from GameObjects.interactions_mixin import TradeItem  # noqa: E402
from economy import actor_total_cp, set_actor_total_cp  # noqa: E402
from hero import Hero  # noqa: E402
from services import create_service, list_service_ids  # noqa: E402
from spell_management import can_cast_managed_spell, consume_managed_spell_resources  # noqa: E402


class _FakeChoiceUI:
    enabled = True
    allow_cli_fallback = False

    def __init__(self, answers: list[str]):
        self._answers = list(answers)
        self.infos: list[tuple[str, str]] = []

    def prompt_choice(self, *_args, **_kwargs):
        if not self._answers:
            return None
        return self._answers.pop(0)

    def prompt_info(self, title, *, prompt_long=None, **_kwargs):
        self.infos.append((str(title), str(prompt_long or "")))
        return "ok"


@dataclass
class _Game:
    ui: object


def test_service_catalog_contains_crb_examples_and_service_category():
    required = {
        "mug_of_ale",
        "lodging_bed_day",
        "hireling_skilled_day",
        "transport_carriage_5_miles",
        "spellcasting_service_rank_1",
        "cost_of_living_subsistence_week",
    }
    available = set(list_service_ids())
    missing = sorted(required.difference(available))
    assert not missing, f"Brakuje uslug: {missing}"

    service = create_service("mug_of_ale")
    assert service is not None
    assert str(getattr(service, "category", "")).lower() == "service"
    assert int(getattr(service, "price_cp", 0) or 0) == 1
    assert "Usluga natychmiastowa" in str(getattr(service, "description", ""))


def test_service_purchase_spends_money_and_does_not_add_inventory_item():
    ui = _FakeChoiceUI(["1", "__exit_trade__"])
    game = _Game(ui=ui)
    hero = Hero()
    set_actor_total_cp(hero, 100)
    npc = BaseNPC(
        name="Karczmarz testowy",
        inventory=[
            TradeItem(
                item_id="mug_of_ale",
                name="Kufel piwa",
                price=1,
                kind="service",
                stock=-1,
            )
        ],
        enable_talk=False,
        enable_diplomacy=False,
        enable_pickpocket=False,
    )

    message = npc.action_trade(hero, game)

    assert "kupiono" in str(message or "").lower()
    assert actor_total_cp(hero) == 99
    assert list(getattr(hero, "inventory", []) or []) == []
    history = list(getattr(hero, "service_history", []) or [])
    assert len(history) == 1
    assert str(history[0].get("service_id", "")) == "mug_of_ale"


def test_priest_heal_service_applies_mechanical_effect():
    ui = _FakeChoiceUI(["1", "__exit_trade__"])
    game = _Game(ui=ui)
    hero = Hero()
    hero.max_hp = 20
    hero.wounds = 10
    set_actor_total_cp(hero, 500)
    npc = BaseNPC(
        name="Kaplan testowy",
        inventory=[
            TradeItem(
                item_id="priest_service_heal_minor",
                name="Usluga: Leczenie mniejsze",
                price=300,
                kind="service",
                stock=-1,
            )
        ],
        enable_talk=False,
        enable_diplomacy=False,
        enable_pickpocket=False,
    )

    message = npc.action_trade(hero, game)

    assert "kupiono" in str(message or "").lower()
    assert actor_total_cp(hero) == 200
    assert int(getattr(hero, "wounds", 0) or 0) < 10
    assert any(
        str(entry.get("service_id", "")) == "priest_service_heal_minor"
        for entry in (getattr(hero, "service_history", []) or [])
    )


def test_mage_armor_service_adds_ac_item_bonus():
    ui = _FakeChoiceUI(["1", "__exit_trade__"])
    game = _Game(ui=ui)
    hero = Hero()
    set_actor_total_cp(hero, 500)
    npc = BaseNPC(
        name="Mag testowy",
        inventory=[
            TradeItem(
                item_id="mage_service_mage_armor",
                name="Usluga: Mage Armor",
                price=300,
                kind="service",
                stock=-1,
            )
        ],
        enable_talk=False,
        enable_diplomacy=False,
        enable_pickpocket=False,
    )

    _ = npc.action_trade(hero, game)

    bonuses = list(getattr(hero, "bonuses", []) or [])
    assert any(
        str(getattr(effect, "tag", "")) == "ac"
        and int(getattr(effect, "value", 0) or 0) == 1
        and str(getattr(effect, "source", "")).startswith("mage_armor:")
        for effect in bonuses
    )


def test_spellcasting_service_grants_one_shot_spell_for_noncaster():
    ui = _FakeChoiceUI(["1", "magic_missile", "__exit_trade__"])
    game = _Game(ui=ui)
    hero = Hero()
    hero.class_name = "fighter"
    hero.ability_modifiers = {"intelligence": 2}
    hero.int_mod = 2
    set_actor_total_cp(hero, 500)
    npc = BaseNPC(
        name="Mag testowy",
        inventory=[
            TradeItem(
                item_id="spellcasting_service_rank_1",
                name="Usluga czaru 1. rangi",
                price=300,
                kind="service",
                stock=-1,
            )
        ],
        spell_service_traditions=["arcana", "primal"],
        spell_service_max_rank=1,
        spell_service_allow_cantrips=True,
        enable_talk=False,
        enable_diplomacy=False,
        enable_pickpocket=False,
    )

    message = npc.action_trade(hero, game)
    assert "kupiono" in str(message or "").lower()
    assert actor_total_cp(hero) == 200

    spell_state = dict(getattr(hero, "spell_state", {}) or {})
    charges = dict((spell_state.get("merchant_one_shot", {}) or {}).get("rank_1", {}) or {})
    assert int(charges.get("magic_missile", 0) or 0) == 1

    can_cast_before, _ = can_cast_managed_spell(hero, spell_id="magic_missile", tier="rank_1")
    assert can_cast_before is True
    consume_managed_spell_resources(hero, spell_id="magic_missile", tier="rank_1")
    can_cast_after, reason = can_cast_managed_spell(hero, spell_id="magic_missile", tier="rank_1")
    assert can_cast_after is False
    assert "ladunku" in str(reason or "").lower()


def test_spellcasting_service_respects_intelligence_capacity_minimum_one():
    ui = _FakeChoiceUI(["1", "magic_missile", "1", "fear", "__exit_trade__"])
    game = _Game(ui=ui)
    hero = Hero()
    hero.class_name = "fighter"
    hero.ability_modifiers = {"intelligence": -1}
    hero.int_mod = -1
    set_actor_total_cp(hero, 1000)
    npc = BaseNPC(
        name="Kaplan testowy",
        inventory=[
            TradeItem(
                item_id="spellcasting_service_rank_1",
                name="Usluga czaru 1. rangi",
                price=300,
                kind="service",
                stock=-1,
            )
        ],
        spell_service_traditions=["divine", "occult"],
        spell_service_max_rank=1,
        spell_service_allow_cantrips=True,
        enable_talk=False,
        enable_diplomacy=False,
        enable_pickpocket=False,
    )

    _ = npc.action_trade(hero, game)
    # INT -1 => limit 1; drugi zakup czaru uslugowego powinien zostac odrzucony.
    spell_state = dict(getattr(hero, "spell_state", {}) or {})
    rank1 = dict((spell_state.get("merchant_one_shot", {}) or {}).get("rank_1", {}) or {})
    assert sum(int(value or 0) for value in rank1.values()) == 1


def test_trade_offer_respects_item_min_tier():
    npc = BaseNPC(
        name="Kupiec tier test",
        trade_tier="novice",
        inventory=[
            TradeItem(item_id="dagger", name="Sztylet", price=20, kind="weapon", stock=-1, min_tier="novice"),
            TradeItem(item_id="rapier", name="Rapier", price=200, kind="weapon", stock=-1, min_tier="adept"),
        ],
        enable_talk=False,
        enable_diplomacy=False,
        enable_pickpocket=False,
    )

    offer = npc._trade_offer_text()
    assert "Sztylet" in offer
    assert "Rapier" not in offer

    npc.trade_tier = "master"
    offer_master = npc._trade_offer_text()
    assert "Sztylet" in offer_master
    assert "Rapier" in offer_master
