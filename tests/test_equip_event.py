import sys
from pathlib import Path
import types


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import GameObjects.events.all_events  # noqa: F401
from GameObjects.events.base import EventContext
from GameObjects.events.registry import dispatch_event
from GameObjects.events.attack import basic_melee_attack_event
from GameObjects.items.goodberry_item import GoodberryItem
from GameObjects.items.inventory import ensure_actor_inventory, get_equipped_weapons
from GameObjects.items.shield import StandardShield
from board_grid import BoardGrid


class CombatCtx(EventContext):
    @property
    def in_combat(self):  # type: ignore[override]
        return True

    @property
    def in_exploration(self):  # type: ignore[override]
        return False


class ExplorationCtx(EventContext):
    @property
    def in_combat(self):  # type: ignore[override]
        return False

    @property
    def in_exploration(self):  # type: ignore[override]
        return True


class FakeConn:
    def __init__(self, card_choices=None, scan_choices=None):
        self.card_choices = list(card_choices or [])
        self.scan_choices = list(scan_choices or [])
        self.scan_calls = []

    def read_card(self, *_args, **_kwargs):
        if self.card_choices:
            return self.card_choices.pop(0)
        return "0"

    def set_leds(self, *_args, **_kwargs):
        return None

    def leds_off(self):
        return None

    def scan_board(self, acceptable_responses=None):
        self.scan_calls.append(list(acceptable_responses) if acceptable_responses is not None else None)
        if self.scan_choices:
            return self.scan_choices.pop(0)
        if acceptable_responses:
            return acceptable_responses[0]
        return None


class FakeUI:
    def __init__(self, *, enabled=False, answer="exit"):
        self.enabled = enabled
        self.answer = answer
        self.allow_cli_fallback = False
        self.calls = []
        self.info_calls = []

    def prompt_choice(self, prompt, **kwargs):
        self.calls.append({"prompt": prompt, **kwargs})
        return self.answer

    def prompt_info(self, title, **kwargs):
        self.info_calls.append({"title": title, **kwargs})
        return "ok"


class FakeEvents:
    def __init__(self):
        self.emitted = []

    def safe_emit_action(self, **payload):
        self.emitted.append(payload)


class Hero:
    def __init__(self, name, pos):
        self.name = name
        self.position = pos
        self.statuses = []
        self.weapon_loadout = ["sword", "dagger", "longbow", "unarmed"]
        self.active_weapon = "sword"
        self.equipped_shield = StandardShield()
        self.hp = 20

    def set_position(self, pos):
        self.position = pos

    def has_status(self, _status):
        return False

    def remove_status(self, status):
        sid = getattr(status, "id", status)
        self.statuses = [s for s in self.statuses if getattr(s, "id", s) != sid]

    def add_status(self, status):
        self.statuses.append(status)

    def heal(self, amount):
        self.hp += int(amount)


class Enemy:
    def __init__(self, pos, hp=12, ac=10):
        self.position = pos
        self.hp = hp
        self.ac = ac

    def set_position(self, pos):
        self.position = pos

    def apply_damage(self, amount, dmg_type=""):
        del dmg_type
        self.hp -= int(amount)
        return self.hp, self.hp <= 0


class FakeGame:
    def __init__(self, conn, ui=None):
        self.conn = conn
        self.ui = ui or FakeUI(enabled=False)
        self.events = FakeEvents()
        self.ui_log = lambda *_a, **_k: None
        self.ui_event = lambda *_a, **_k: None
        self.board = BoardGrid(6, 6)
        self.heroes = []
        self.enemies = []
        self.state = types.SimpleNamespace(ACTION_LIMIT=3, actions_used={})


def test_equip_combat_costs_one_action_and_handles_navigation():
    hero = Hero("A", (0, 0))
    hero.equipped_shield = None
    game = FakeGame(conn=FakeConn(card_choices=["2", "5"]))
    game.heroes = [hero]
    game.board.place(hero, hero.position)
    game.state.actions_used = {hero: 0}

    result = dispatch_event("equip", CombatCtx(game=game, actor=hero))

    assert result.success
    assert result.consumed_action
    assert result.actions_spent == 1
    equipped_labels = [getattr(item, "item_id", None) for item in get_equipped_weapons(hero)]
    assert "dagger" in equipped_labels


def test_equip_cancel_does_not_consume_action():
    hero = Hero("A", (0, 0))
    game = FakeGame(conn=FakeConn(card_choices=["0"]))
    game.heroes = [hero]
    game.board.place(hero, hero.position)
    game.state.actions_used = {hero: 0}

    result = dispatch_event("equip", CombatCtx(game=game, actor=hero))

    assert not result.success
    assert not result.consumed_action


def test_equip_transfer_in_exploration_ignores_distance():
    hero_a = Hero("A", (0, 0))
    hero_b = Hero("B", (5, 5))
    game = FakeGame(conn=FakeConn(card_choices=["6"]))
    game.heroes = [hero_a, hero_b]
    game.board.place(hero_a, hero_a.position)
    game.board.place(hero_b, hero_b.position)
    ensure_actor_inventory(hero_a)
    ensure_actor_inventory(hero_b)
    before_b = len(hero_b.inventory)

    result = dispatch_event("equip", ExplorationCtx(game=game, actor=hero_a))

    assert result.success
    assert result.consumed_action
    assert len(hero_b.inventory) == before_b + 1


def test_equip_transfer_selects_target_via_board_scan_expected_fields():
    hero_a = Hero("A", (0, 0))
    hero_b = Hero("B", (5, 5))
    hero_c = Hero("C", (4, 4))
    conn = FakeConn(card_choices=["6"], scan_choices=[hero_c.position])
    game = FakeGame(conn=conn)
    game.heroes = [hero_a, hero_b, hero_c]
    game.board.place(hero_a, hero_a.position)
    game.board.place(hero_b, hero_b.position)
    game.board.place(hero_c, hero_c.position)
    ensure_actor_inventory(hero_a)
    ensure_actor_inventory(hero_b)
    ensure_actor_inventory(hero_c)
    before_b = len(hero_b.inventory)
    before_c = len(hero_c.inventory)

    result = dispatch_event("equip", ExplorationCtx(game=game, actor=hero_a))

    assert result.success
    assert len(hero_b.inventory) == before_b
    assert len(hero_c.inventory) == before_c + 1
    assert conn.scan_calls
    expected = set(conn.scan_calls[-1] or [])
    assert expected == {hero_b.position, hero_c.position}


def test_equip_transfer_in_combat_requires_adjacent_target():
    hero_a = Hero("A", (0, 0))
    hero_b = Hero("B", (5, 5))
    game = FakeGame(conn=FakeConn(card_choices=["6"]))
    game.heroes = [hero_a, hero_b]
    game.board.place(hero_a, hero_a.position)
    game.board.place(hero_b, hero_b.position)
    game.state.actions_used = {hero_a: 0}

    result = dispatch_event("equip", CombatCtx(game=game, actor=hero_a))

    assert not result.success
    assert not result.consumed_action
    assert "sąsiedniego" in (result.message or "")


def test_equip_drop_creates_loot_and_interaction_picks_it_up():
    hero = Hero("A", (0, 0))
    game = FakeGame(conn=FakeConn(card_choices=["2", "4"], scan_choices=[hero.position]), ui=FakeUI(enabled=False))
    game.heroes = [hero]
    game.board.place(hero, hero.position)
    game.state.actions_used = {hero: 0}
    ensure_actor_inventory(hero)
    before = len(hero.inventory)

    drop_result = dispatch_event("equip", CombatCtx(game=game, actor=hero))
    assert drop_result.success
    assert len(game.board.interactables_at(hero.position)) >= 1

    game.ui = FakeUI(enabled=True, answer="pickup_loot")
    pick_result = dispatch_event("interaction", ExplorationCtx(game=game, actor=hero))
    assert pick_result.success
    assert len(hero.inventory) == before


def test_attack_fallbacks_to_unarmed_when_no_weapon_equipped(monkeypatch):
    hero = Hero("A", (0, 0))
    enemy = Enemy((1, 0), hp=9, ac=10)
    game = FakeGame(conn=FakeConn(scan_choices=[enemy.position]))
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.place(hero, hero.position)
    game.board.place(enemy, enemy.position)
    ensure_actor_inventory(hero)
    hero.equipped_weapon_item_ids = []

    rolls = iter([18, 4])  # attack, damage
    monkeypatch.setattr(basic_melee_attack_event, "prompt_for_roll", lambda *_, **__: next(rolls))
    monkeypatch.setattr(basic_melee_attack_event, "refresh_flanking_statuses", lambda *_a, **_k: None)

    result = dispatch_event("attack", ExplorationCtx(game=game, actor=hero))

    assert result.success
    assert enemy.hp == 5


def test_equip_ui_prompt_contains_details_and_legend():
    hero = Hero("A", (0, 0))
    ui = FakeUI(enabled=True, answer="exit")
    game = FakeGame(conn=FakeConn(), ui=ui)
    game.heroes = [hero]
    game.board.place(hero, hero.position)

    result = dispatch_event("equip", ExplorationCtx(game=game, actor=hero))

    assert not result.success
    call = ui.calls[-1]
    prompt_long = str(call.get("prompt_long") or "")
    assert "Nawigacja:" in prompt_long
    assert "Szczegóły:" in prompt_long
    assert "Attack:" in prompt_long


def test_equip_toggle_consumes_goodberry_and_heals(monkeypatch):
    hero = Hero("A", (0, 0))
    hero.equipped_shield = None
    hero.inventory = [GoodberryItem(cast_rank=1)]
    ui = FakeUI(enabled=False)
    game = FakeGame(conn=FakeConn(card_choices=["2", "5"]), ui=ui)
    game.heroes = [hero]
    game.board.place(hero, hero.position)
    game.state.actions_used = {hero: 0}

    monkeypatch.setattr("GameObjects.events.equip_event.random.randint", lambda *_a, **_k: 6)

    result = dispatch_event("equip", CombatCtx(game=game, actor=hero))

    assert result.success
    assert result.consumed_action
    assert hero.hp == 30
    assert all(str(getattr(item, "item_id", "")).lower() != "goodberry" for item in ensure_actor_inventory(hero))
    assert len(ui.info_calls) == 1
    assert "Leczenie: 6 + 4 = 10 HP." in str(ui.info_calls[0].get("prompt_long") or "")


def test_attack_with_two_active_weapons_asks_and_uses_selected(monkeypatch):
    hero = Hero("A", (0, 0))
    enemy = Enemy((1, 0), hp=10, ac=10)
    ui = FakeUI(enabled=True, answer="2")
    game = FakeGame(conn=FakeConn(scan_choices=[enemy.position]), ui=ui)
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.place(hero, hero.position)
    game.board.place(enemy, enemy.position)
    ensure_actor_inventory(hero)
    # Dwie aktywne bronie 1H: sword + dagger.
    dagger = next(item for item in hero.inventory if getattr(item, "item_id", None) == "dagger")
    sword = next(item for item in hero.inventory if getattr(item, "item_id", None) == "sword")
    hero.equipped_weapon_item_ids = [getattr(sword, "instance_id"), getattr(dagger, "instance_id")]

    rolls = iter([17, 3])  # attack, damage
    monkeypatch.setattr(basic_melee_attack_event, "prompt_for_roll", lambda *_, **__: next(rolls))
    monkeypatch.setattr(basic_melee_attack_event, "refresh_flanking_statuses", lambda *_a, **_k: None)

    result = dispatch_event("attack", ExplorationCtx(game=game, actor=hero))

    assert result.success
    assert any(str(ev.get("action_id", "")).startswith("attack_dagger") for ev in game.events.emitted)
