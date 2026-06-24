from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import GameObjects.events.all_events  # noqa: F401
from GameObjects.events.attack import basic_melee_attack_event  # noqa: E402
from GameObjects.events.base import EventContext  # noqa: E402
from GameObjects.events.registry import dispatch_event  # noqa: E402
from GameObjects.items.armor import create_armor  # noqa: E402
from GameObjects.items.armor import basic_armors as armor_mod  # noqa: E402
from GameObjects.items.equipment import create_equipment, list_equipment_ids  # noqa: E402
from GameObjects.items.shield import create_shield  # noqa: E402
from GameObjects.items.shield import basic_shields as shield_mod  # noqa: E402
from GameObjects.items.weapon import create_weapon  # noqa: E402
from GameObjects.items.weapon import basic_weapons as weapon_mod  # noqa: E402
from GameObjects.items.weapon.base_weapon import BaseWeapon  # noqa: E402
from GameObjects.items.inventory import item_use_description  # noqa: E402
from economy import parse_bulk_units  # noqa: E402


def _assert_item_core_fields(item):
    assert item is not None
    assert hasattr(item, "price_cp")
    assert int(getattr(item, "price_cp", 0) or 0) >= 0
    assert hasattr(item, "bulk")
    assert parse_bulk_units(getattr(item, "bulk", None)) >= 0
    assert isinstance(getattr(item, "traits", ()), tuple)
    text = str(item.ui_description() or "")
    assert "Cena:" in text
    assert "Bulk:" in text


def test_all_defined_weapons_have_price_bulk_traits_and_ui():
    for weapon_id in sorted(weapon_mod._WEAPON_FACTORIES.keys()):  # noqa: SLF001 - test audit
        weapon = create_weapon(weapon_id)
        _assert_item_core_fields(weapon)


def test_all_defined_armors_have_price_bulk_traits_and_ui():
    for armor_id in sorted(armor_mod._ARMOR_FACTORIES.keys()):  # noqa: SLF001 - test audit
        armor = create_armor(armor_id)
        _assert_item_core_fields(armor)


def test_all_defined_shields_have_price_bulk_traits_and_ui():
    for shield_id in sorted(shield_mod._SHIELD_FACTORIES.keys()):  # noqa: SLF001 - test audit
        shield = create_shield(shield_id)
        _assert_item_core_fields(shield)


def test_all_defined_equipment_have_price_bulk_traits_and_ui():
    for equipment_id in list_equipment_ids():
        item = create_equipment(equipment_id)
        _assert_item_core_fields(item)


def test_equipment_use_descriptions_include_tool_hints():
    healer_tools = create_equipment("healer_tools")
    thieves_tools = create_equipment("thieves_tools")
    assert healer_tools is not None and thieves_tools is not None
    assert "Battle Medicine" in item_use_description(healer_tools)
    assert "Disable Device" in item_use_description(thieves_tools)


class _FakeEvents:
    def safe_emit_action(self, **_payload):
        return None


class _FakeConn:
    def set_leds(self, *_args, **_kwargs):
        return None

    def scan_board(self, acceptable_responses=None):
        if acceptable_responses:
            return acceptable_responses[0]
        return None

    def leds_off(self):
        return None

    def read_card(self, *_args, **_kwargs):
        return ""


class _FakeBoard:
    def __init__(self):
        self.occupants = {}

    def occupant_at(self, pos):
        return self.occupants.get(pos)

    def get_neighbors(self, pos, include_position=False, diagonal=True):
        del diagonal
        out = [
            (pos[0] + 1, pos[1]),
            (pos[0] - 1, pos[1]),
            (pos[0], pos[1] + 1),
            (pos[0], pos[1] - 1),
        ]
        if include_position:
            out.append(pos)
        return out

    def in_bounds(self, _pos):
        return True

    def interactables_at(self, _pos):
        return []

    def is_blocked(self, _a, _b):
        return False

    def get_wall(self, _a, _b):
        return None

    def edge_interactables_between(self, _a, _b):
        return []

    def remove(self, _pos):
        return None


class _Hero:
    def __init__(self, pos, weapon):
        self.position = pos
        self.statuses = []
        self.inventory = [weapon]
        self.equipped_weapon_item_ids = [str(getattr(weapon, "instance_id", ""))]
        self.bonuses = []

    def remove_status(self, status):
        sid = getattr(status, "id", status)
        self.statuses = [item for item in self.statuses if getattr(item, "id", item) != sid]

    def add_status(self, status):
        self.statuses.append(status)

    def has_status(self, status_id):
        return any(getattr(item, "id", item) == status_id for item in self.statuses)


class _Enemy:
    def __init__(self, pos, hp=10, ac=10):
        self.position = pos
        self.hp = hp
        self.ac = ac

    def apply_damage(self, amount, _dmg_type=""):
        self.hp -= int(amount or 0)
        return self.hp, self.hp <= 0


class _Game:
    def __init__(self, hero, enemy):
        self.events = _FakeEvents()
        self.conn = _FakeConn()
        self.board = _FakeBoard()
        self.heroes = [hero]
        self.enemies = [enemy]
        self.board.occupants = {hero.position: hero, enemy.position: enemy}
        self.ui_log = lambda *_a, **_k: None


def test_attack_event_fallback_for_weapon_without_registered_event(monkeypatch):
    weapon = BaseWeapon(
        item_id="audit_blade",
        name="Audit Blade",
        event_name="audit_blade",
        damage_prompt="1k6 + STR",
        damage_type="slashing",
        price_cp=100,
        bulk=1,
    )
    hero = _Hero((0, 0), weapon)
    enemy = _Enemy((1, 0), hp=10, ac=10)
    game = _Game(hero, enemy)
    rolls = iter([18, 4])  # trafienie + obrażenia
    monkeypatch.setattr(basic_melee_attack_event, "prompt_for_roll", lambda *_, **__: next(rolls))
    monkeypatch.setattr(basic_melee_attack_event, "refresh_flanking_statuses", lambda *_a, **_k: None)

    result = dispatch_event("attack", EventContext(game=game, actor=hero))

    assert result.success
    assert enemy.hp == 6
