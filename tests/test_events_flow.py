import sys
import types
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import GameObjects.events.all_events  # noqa: F401
from GameObjects.events.registry import dispatch_event
from GameObjects.events.base import EventContext


class FakeEvents:
    def __init__(self):
        self.last_event = None

    def safe_emit_action(self, **payload):
        self.last_event = payload
        return True


class FakeConn:
    def __init__(self, scan_return=None):
        self.scan_return = scan_return

    def set_leds(self, *a, **k):
        return None

    def scan_board(self, *a, **k):
        return self.scan_return

    def leds_off(self):
        return None

    def read_card(self, *a, **k):
        return "end"


class FakeBoard:
    def __init__(self, hero_pos):
        self.hero_pos = hero_pos

    def rooms_at(self, *_):
        return set()

    def in_bounds(self, *_):
        return True

    def cell_at(self, *_):
        return types.SimpleNamespace(field=types.SimpleNamespace(stealth_impact=0))

    def get_neighbors(self, *_args, **_kwargs):
        return []

    def is_blocked(self, *_):
        return False

    def interactables_at(self, *_):
        return []

    def get_interactables_in_range(self, *_args, **_kwargs):
        return []

    def can_traverse(self, *_args, **_kwargs):
        return True

    def can_enter(self, *_args, **_kwargs):
        return True

    def positions_in_rooms(self, *_):
        return set()

    def room_seek_failures(self, *_):
        return 0

    def is_room_seek_locked(self, *_):
        return False

    def lock_room_seek(self, *_):
        return None

    def increment_room_seek_fail(self, *_):
        return None


class FakeGame:
    def __init__(self, conn=None, board=None):
        self.events = FakeEvents()
        self.conn = conn or FakeConn()
        self.ui_log = lambda *a, **k: None
        self.ui_event = lambda *a, **k: None
        self.heroes = []
        self.enemies = []
        self.board = board
        self.state = None


def test_move_event_emits_action_and_uses_tags(monkeypatch):
    hero = types.SimpleNamespace(name="Hero", position=(0, 0))
    conn = FakeConn(scan_return=hero.position)  # natychmiast kończy ruch
    board = FakeBoard(hero.position)
    game = FakeGame(conn=conn, board=board)
    game.heroes = [hero]

    # skracamy logikę: od razu zwracamy obecne pole
    import GameObjects.events.move_event as move_event_module

    monkeypatch.setattr(move_event_module.MoveEvent, "_wait_for_destination", lambda self, ctx, b: hero.position)

    ctx = EventContext(game=game, actor=hero, tags=["custom"])
    result = dispatch_event("move", ctx)

    assert result.success  # powinno się wykonać bez wyjątku
    event = game.events.last_event
    # ruch mógł zostać anulowany, ale tagi powinny być ustawione kiedy emitowane
    if event:
        assert set(event.get("action_tags", [])) >= {"move", "custom"}


def test_stealth_event_respects_hide_status(monkeypatch):
    class Hero:
        def __init__(self):
            self.position = (1, 1)
            self.stealth_fail_counts = {}
            self.blocked_stealth_rooms = set()
            self.stealth_bonus = 0
            self.stealth_detection_dc = None

        def has_status(self, name):
            return name == "hide"

        def add_status(self, *_):
            return None

        def remove_status(self, *_):
            return None

    hero = Hero()
    conn = FakeConn(scan_return=hero.position)
    board = FakeBoard(hero.position)
    game = FakeGame(conn=conn, board=board)
    game.heroes = [hero]

    # zablokuj prompt_for_roll w resolverze skill_check
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_, **__: 20)
    ctx = EventContext(game=game, actor=hero)
    result = dispatch_event("stealth", ctx)

    assert result.success


def test_delay_reorders_initiative(monkeypatch):
    from states.combat import Combat
    import states.combat as combat_module

    # stały wynik rzutu obniżający inicjatywę o 3
    monkeypatch.setattr(combat_module, "prompt_for_roll", lambda *_, **__: 3)

    class Hero:
        def __init__(self):
            self.name = "Hero"
            self.position = (0, 0)
            self.initiative = 15

        def reset_reactions(self):
            return None

        def __hash__(self):
            return id(self)

    hero = Hero()
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = []
    combat = Combat(game)
    game.state = combat

    combat.base_initiative[hero] = 15
    combat.round_queue = [hero]
    combat.base_order = [hero]
    combat.actions_used[hero] = 0

    ctx = EventContext(game=game, actor=hero)
    result = dispatch_event("delay", ctx)

    assert result.success
    assert hero in combat.delayed
    assert combat.temp_initiative[hero] == 12  # 15 - 3
    assert combat.round_queue[0] is hero
    assert combat.actions_used[hero] == 0


def test_actions_reset_when_actor_turn_comes_again():
    from states.combat import Combat

    class Hero:
        def __init__(self):
            self.name = "Hero"
            self.object_id = "hero-1"
            self.position = (0, 0)
            self.initiative = 15

        def __hash__(self):
            return id(self)

    class Enemy:
        def __init__(self):
            self.name = "Enemy"
            self.object_id = "enemy-1"
            self.position = (1, 0)
            self.initiative = 10
            self.hp = 10

        def __hash__(self):
            return id(self)

    hero = Hero()
    enemy = Enemy()
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.ui = None
    combat = Combat(game)
    game.state = combat

    combat.base_order = [hero, enemy]
    combat.round_queue = [hero, enemy]
    combat.initiative_order = [hero, enemy]
    combat.base_initiative[hero] = 15
    combat.base_initiative[enemy] = 10
    combat.actions_used[hero] = 2

    # Koniec tury bohatera -> tura wroga.
    combat._advance_turn()
    assert combat._current_actor() is enemy

    # Koniec tury wroga -> nowa runda, znowu bohater.
    combat._advance_turn()
    assert combat._current_actor() is hero
    assert combat.actions_used.get(hero, 0) == 0


def test_end_blocked_for_non_active_actor():
    from states.combat import Combat
    from GameObjects.events.base import EventContext
    from GameObjects.events.registry import dispatch_event

    class Hero:
        def __init__(self, name, object_id, pos):
            self.name = name
            self.object_id = object_id
            self.position = pos
            self.initiative = 10

        def __hash__(self):
            return id(self)

    hero_a = Hero("Hero A", "hero-a", (0, 0))
    hero_b = Hero("Hero B", "hero-b", (1, 0))
    game = FakeGame()
    game.heroes = [hero_a, hero_b]
    game.enemies = []
    game.ui = None
    combat = Combat(game)
    game.state = combat
    combat.base_order = [hero_a, hero_b]
    combat.round_queue = [hero_a, hero_b]
    combat.base_initiative[hero_a] = 12
    combat.base_initiative[hero_b] = 10

    ctx = EventContext(game=game, actor=hero_b)  # nieaktywny aktor próbuje END
    result = dispatch_event("end", ctx)

    assert result.success is False
    assert "nie jest tura" in (result.message or "").lower()
    assert combat.round_queue[0] is hero_a


def test_initiative_event_payload_excludes_removed_dead_enemy():
    from states.combat import Combat

    class Hero:
        def __init__(self):
            self.name = "Hero"
            self.object_id = "hero-1"
            self.position = (0, 0)
            self.initiative = 15
            self.wounds = 3
            self.max_hp = 20
            self.statuses = []
            self.image = "/static/portraits/custom/hero-test.jpg"

        def reset_reactions(self):
            return None

        def __hash__(self):
            return id(self)

    class Enemy:
        def __init__(self, *, alive=True):
            self.name = "Enemy"
            self.object_id = "enemy-alive" if alive else "enemy-dead"
            self.position = (1, 0) if alive else (2, 0)
            self.initiative = 10
            self.hp = 10 if alive else 0
            self.max_hp = 12
            self.statuses = []
            self.image = "/assets/ui_v2/bandit_cave/images/enemies/bandit.svg"

        def __hash__(self):
            return id(self)

    captured = []

    hero = Hero()
    alive_enemy = Enemy(alive=True)
    dead_enemy = Enemy(alive=False)
    overkilled_enemy = Enemy(alive=True)
    overkilled_enemy.object_id = "enemy-overkilled"
    overkilled_enemy.hp = -4
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [alive_enemy, dead_enemy, overkilled_enemy]
    game.ui = object()
    game.ui_event = lambda event_type, payload: captured.append((event_type, payload))
    game.ui_active_actor = lambda *_a, **_k: None

    combat = Combat(game)
    game.state = combat
    combat.base_order = [hero, dead_enemy, alive_enemy, overkilled_enemy]
    combat.round_queue = [hero, dead_enemy, alive_enemy, overkilled_enemy]
    combat.base_initiative[hero] = 15
    combat.base_initiative[dead_enemy] = 11
    combat.base_initiative[alive_enemy] = 10
    combat.base_initiative[overkilled_enemy] = 9
    combat.actions_used[hero] = 1

    combat._send_initiative_event()

    evt_type, payload = captured[-1]
    assert evt_type == "initiative"
    ids = [entry["id"] for entry in payload["order"]]
    assert "enemy-dead" not in ids
    assert "enemy-overkilled" not in ids
    assert payload["active_id"] == "hero-1"
    hero_entry = next(entry for entry in payload["order"] if entry["id"] == "hero-1")
    alive_enemy_entry = next(entry for entry in payload["order"] if entry["id"] == "enemy-alive")
    assert hero_entry["wounds"] == 3
    assert hero_entry["max_hp"] == 20
    assert hero_entry["statuses"] == []
    assert hero_entry["image"] == "/static/portraits/custom/hero-test.jpg"
    assert hero_entry["asset_id"] == "hero-1"
    assert hero_entry["actions_used"] == 1
    assert hero_entry["actions_total"] == 3
    assert hero_entry["actions_remaining"] == 2
    assert alive_enemy_entry["wounds"] == 2
    assert alive_enemy_entry["max_hp"] == 12
    assert alive_enemy_entry["image"].endswith("bandit.svg")
    assert alive_enemy_entry["asset_id"] == "enemy-alive"


def test_combat_end_clears_companion_initiative_from_ui():
    from states.combat import Combat
    from states.heroes_turns import HeroesTurn

    class Hero:
        def __init__(self):
            self.name = "Hero"
            self.object_id = "hero-1"
            self.position = (0, 0)
            self.initiative = 15
            self.statuses = []

        def __hash__(self):
            return id(self)

    class Companion:
        def __init__(self):
            self.name = "Wolf"
            self.object_id = "companion-1"
            self.position = (1, 0)
            self.initiative = 14
            self.hp = 10
            self.max_hp = 10
            self.statuses = []

        def __hash__(self):
            return id(self)

    captured = []
    active_changes = []
    hero = Hero()
    companion = Companion()
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = []
    game.ui = object()
    game.ui_event = lambda event_type, payload: captured.append((event_type, payload))
    game.ui_active_actor = lambda actor: active_changes.append(actor)

    combat = Combat(game)
    game.state = combat
    combat.base_order = [hero, companion]
    combat.round_queue = [companion]
    combat.initiative_order = [companion, hero]
    combat.base_initiative[hero] = 15
    combat.base_initiative[companion] = 14
    combat.animal_companions[hero.object_id] = companion

    next_state = combat._end_combat_if_no_enemies()

    assert isinstance(next_state, HeroesTurn)
    assert combat.animal_companions == {}
    assert combat.base_order == []
    assert combat.round_queue == []
    assert captured[-1] == ("initiative", {"round": None, "order": [], "active_id": None})
    assert active_changes[-1] is None
