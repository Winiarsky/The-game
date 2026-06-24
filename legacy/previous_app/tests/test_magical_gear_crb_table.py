from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import GameObjects.events.all_events  # noqa: F401
from GameObjects.events.base import EventContext  # noqa: E402
from GameObjects.events.magic.consumables.events import (  # noqa: E402
    HolyWaterEvent,
    MinorHealingPotionEvent,
    PotencyCrystalEvent,
    ScrollCommonRank1Event,
    UnholyWaterEvent,
    choose_common_rank1_scroll_spell,
    configure_common_rank1_scroll,
)
from GameObjects.events.registry import list_events  # noqa: E402
from GameObjects.items.equipment import create_equipment  # noqa: E402
from GameObjects.items.inventory import add_item  # noqa: E402
from GameObjects.items.weapon import create_weapon  # noqa: E402
from economy import item_cost_cp, parse_bulk_units  # noqa: E402
from hero import Hero  # noqa: E402
from states.intent_menu import filter_events_for_actor  # noqa: E402


@dataclass
class _Enemy:
    position: tuple[int, int] = (1, 0)
    ac: int = 10
    hp: int = 20
    tags: tuple[str, ...] = ()
    statuses: list[object] = None

    def __post_init__(self):
        if self.statuses is None:
            self.statuses = []

    def apply_damage(self, amount, _damage_type=""):
        self.hp -= int(amount or 0)
        return self.hp, self.hp <= 0


class _Conn:
    def __init__(self, choice=None):
        self.choice = choice

    def set_leds(self, *_args, **_kwargs):
        return None

    def scan_board(self, _acceptable_responses=None):
        return self.choice

    def leds_off(self):
        return None


class _UI:
    enabled = True
    allow_cli_fallback = False

    def __init__(self, answers: list[str]):
        self._answers = list(answers)

    def prompt_choice(self, *_args, **_kwargs):
        if not self._answers:
            return None
        return self._answers.pop(0)

    def prompt_info(self, *_args, **_kwargs):
        return "ok"


class _MetaUI(_UI):
    def __init__(self, answers: list[str]):
        super().__init__(answers)
        self.last_choice_meta = None

    def prompt_choice(self, *args, **kwargs):
        self.last_choice_meta = list(kwargs.get("choice_meta") or [])
        return super().prompt_choice(*args, **kwargs)


def _make_game(*, hero: Hero, enemies: list[object] | None = None, ui=None, conn_choice=None):
    if enemies is None:
        enemies = []
    return SimpleNamespace(
        heroes=[hero],
        enemies=list(enemies),
        conn=_Conn(choice=conn_choice),
        ui=ui,
        ui_log=lambda *_a, **_k: None,
        state=None,
    )


def test_crb_magical_gear_events_registered_and_items_have_cost_bulk():
    registered = set(list_events().keys())
    expected_events = {
        "holy_water",
        "unholy_water",
        "minor_healing_potion",
        "scroll_common_rank1",
        "potency_crystal",
    }
    missing = sorted(expected_events.difference(registered))
    assert not missing, f"Brakuje eventow magicznego ekwipunku: {missing}"

    expected_prices = {
        "holy_water": 300,
        "unholy_water": 300,
        "minor_healing_potion": 400,
        "scroll_common_rank1": 400,
        "potency_crystal": 400,
    }
    for item_id, price_cp in expected_prices.items():
        item = create_equipment(item_id)
        assert item is not None
        assert int(getattr(item, "price_cp", 0) or 0) == price_cp
        assert item_cost_cp(item_id) == price_cp
        assert parse_bulk_units(getattr(item, "bulk", None)) >= 0
        assert str(getattr(item, "event_name", "") or "").strip().lower() == item_id


def test_holy_water_hits_undead_and_is_consumed(monkeypatch):
    hero = Hero(position=(0, 0))
    target = _Enemy(position=(1, 0), tags=("undead",), hp=20)
    holy = create_equipment("holy_water")
    assert holy is not None
    add_item(hero, holy)
    game = _make_game(hero=hero, enemies=[target], conn_choice=target.position)

    event = HolyWaterEvent()
    monkeypatch.setattr(event, "_prompt_for_roll", lambda *_a, **_k: 18)
    monkeypatch.setattr(event, "_prompt_damage", lambda *_a, **_k: 6)
    result = event.execute(EventContext(game=game, actor=hero))

    assert result.success is True
    assert target.hp == 14
    inventory_ids = {str(getattr(item, "item_id", "")).strip().lower() for item in list(getattr(hero, "inventory", []) or [])}
    assert "holy_water" not in inventory_ids


def test_unholy_water_no_effect_on_non_celestial_but_is_consumed(monkeypatch):
    hero = Hero(position=(0, 0))
    target = _Enemy(position=(1, 0), tags=("humanoid",), hp=20)
    item = create_equipment("unholy_water")
    assert item is not None
    add_item(hero, item)
    game = _make_game(hero=hero, enemies=[target], conn_choice=target.position)

    event = UnholyWaterEvent()
    monkeypatch.setattr(event, "_prompt_for_roll", lambda *_a, **_k: 18)
    monkeypatch.setattr(event, "_prompt_damage", lambda *_a, **_k: 6)
    result = event.execute(EventContext(game=game, actor=hero))

    assert result.success is True
    assert target.hp == 20
    inventory_ids = {str(getattr(item, "item_id", "")).strip().lower() for item in list(getattr(hero, "inventory", []) or [])}
    assert "unholy_water" not in inventory_ids


def test_minor_healing_potion_heals_and_is_consumed(monkeypatch):
    hero = Hero(position=(0, 0))
    hero.wounds = 10
    item = create_equipment("minor_healing_potion")
    assert item is not None
    add_item(hero, item)
    game = _make_game(hero=hero)
    event = MinorHealingPotionEvent()

    monkeypatch.setattr("GameObjects.events.magic.consumables.events.prompt_for_roll", lambda *_a, **_k: 8)
    result = event.execute(EventContext(game=game, actor=hero))

    assert result.success is True
    assert int(getattr(hero, "wounds", 0) or 0) == 2
    inventory_ids = {str(getattr(it, "item_id", "")).strip().lower() for it in list(getattr(hero, "inventory", []) or [])}
    assert "minor_healing_potion" not in inventory_ids


def test_potency_crystal_adds_attack_bonus_and_is_consumed():
    hero = Hero(position=(0, 0))
    weapon = create_weapon("longsword")
    crystal = create_equipment("potency_crystal")
    assert weapon is not None and crystal is not None
    hero.inventory = [weapon, crystal]
    hero.equipped_weapon_item_ids = [str(getattr(weapon, "instance_id", ""))]
    game = _make_game(hero=hero)

    event = PotencyCrystalEvent()
    result = event.execute(EventContext(game=game, actor=hero))

    assert result.success is True
    sources = {str(getattr(effect, "source", "") or "") for effect in list(getattr(hero, "bonuses", []) or [])}
    assert "potency_crystal:attack" in sources
    inventory_ids = {str(getattr(it, "item_id", "")).strip().lower() for it in list(getattr(hero, "inventory", []) or [])}
    assert "potency_crystal" not in inventory_ids


def test_scroll_common_rank1_casts_selected_spell_and_is_consumed():
    hero = Hero(position=(0, 0))
    hero.spell_state = {
        "enabled": True,
        "enforce": True,
        "class_name": "wizard",
        "known": {"rank_1": ["heal"], "cantrip": [], "focus": [], "innate": []},
    }
    scroll = create_equipment("scroll_common_rank1")
    assert scroll is not None
    configure_common_rank1_scroll(scroll, "true_strike")
    add_item(hero, scroll)
    game = _make_game(hero=hero)

    event = ScrollCommonRank1Event()
    result = event.execute(EventContext(game=game, actor=hero))

    assert result.success is True
    assert hero.has_status("true_strike") is True
    inventory_ids = {str(getattr(it, "item_id", "")).strip().lower() for it in list(getattr(hero, "inventory", []) or [])}
    assert "scroll_common_rank1" not in inventory_ids


def test_scroll_common_rank1_selects_specific_scroll_item_when_multiple_ready():
    hero = Hero(position=(0, 0))
    hero.spell_state = {
        "enabled": True,
        "enforce": True,
        "class_name": "wizard",
        "known": {"rank_1": ["heal"], "cantrip": [], "focus": [], "innate": []},
    }
    first = create_equipment("scroll_common_rank1")
    second = create_equipment("scroll_common_rank1")
    assert first is not None and second is not None
    configure_common_rank1_scroll(first, "mage_armor")
    configure_common_rank1_scroll(second, "true_strike")
    add_item(hero, first)
    add_item(hero, second)
    ui = _UI(["2"])
    game = _make_game(hero=hero, ui=ui)

    event = ScrollCommonRank1Event()
    result = event.execute(EventContext(game=game, actor=hero))

    assert result.success is True
    assert hero.has_status("true_strike") is True
    remaining_scrolls = [item for item in list(getattr(hero, "inventory", []) or []) if str(getattr(item, "item_id", "")).strip().lower() == "scroll_common_rank1"]
    assert len(remaining_scrolls) == 1
    assert str(getattr(remaining_scrolls[0], "scroll_spell_id", "") or "").strip().lower() == "mage_armor"


def test_scroll_purchase_spell_choices_show_full_structured_spell_description():
    ui = _MetaUI(["mage_armor"])
    game = SimpleNamespace(ui=ui)

    chosen = choose_common_rank1_scroll_spell(game, source="scroll_common_rank1", choices=["mage_armor"])

    assert chosen == "mage_armor"
    meta = list(ui.last_choice_meta or [])
    assert len(meta) == 1
    desc = str(meta[0].get("desc") or "")
    assert "Fluff:" in desc
    assert "Mechanika:" in desc
    assert "Pancerz maga" in desc
    assert "+1 item do AC na 10 tur" in desc
    assert "Koszt: 2 akcje" in desc
    assert "Tradycja:" in desc


def test_configured_scroll_description_uses_spell_mechanics_summary():
    scroll = create_equipment("scroll_common_rank1")
    assert scroll is not None

    configure_common_rank1_scroll(scroll, "mage_armor")

    description = str(getattr(scroll, "description", "") or "")
    assert "Jednorazowo rzuca czar: Pancerz maga." in description
    assert "+1 item do AC na 10 tur" in description
    assert "Koszt: 2 akcje." in description


def test_required_inventory_event_filters_action_visibility():
    hero = Hero(position=(0, 0))
    events = list_events()
    available = {"holy_water": events["holy_water"], "minor_healing_potion": events["minor_healing_potion"]}

    filtered_without_items = filter_events_for_actor(available, actor=hero, in_combat=False, game=None)
    assert filtered_without_items == {}

    holy = create_equipment("holy_water")
    assert holy is not None
    add_item(hero, holy)
    filtered_with_item = filter_events_for_actor(available, actor=hero, in_combat=False, game=None)
    assert "holy_water" in filtered_with_item
    assert "minor_healing_potion" not in filtered_with_item
