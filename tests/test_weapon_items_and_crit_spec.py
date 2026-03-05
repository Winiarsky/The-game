import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import GameObjects.events.all_events  # noqa: F401
from GameObjects.events.base import EventContext
from GameObjects.events.registry import dispatch_event
from GameObjects.events.attack import basic_melee_attack_event, base_attack_range_event
from GameObjects.items.weapon import create_weapon, normalize_weapon_id
from damage_types import DamageType
from statuses import Status


class FakeEvents:
    def __init__(self):
        self.emitted = []

    def safe_emit_action(self, **payload):
        self.emitted.append(payload)


class FakeConn:
    def __init__(self, choices=None):
        self._choices = list(choices or [])

    def set_leds(self, *args, **kwargs):
        return None

    def scan_board(self, acceptable_responses=None):
        if self._choices:
            return self._choices.pop(0)
        if acceptable_responses:
            return acceptable_responses[0]
        return None

    def leds_off(self):
        return None

    def read_card(self, *_args, **_kwargs):
        return ""


class FakeBoard:
    def __init__(self):
        self.occupants = {}
        self.blocked_edges = set()

    def occupant_at(self, pos):
        return self.occupants.get(pos)

    def interactables_at(self, _pos):
        return []

    def is_blocked(self, a, b):
        return frozenset((a, b)) in self.blocked_edges

    def get_wall(self, _a, _b):
        return None

    def edge_interactables_between(self, _a, _b):
        return []

    def remove(self, pos):
        self.occupants.pop(pos, None)

    def move(self, src, dst):
        actor = self.occupants.pop(src, None)
        if actor is not None:
            self.occupants[dst] = actor

    def can_enter(self, pos, allow_occupied=False):
        if allow_occupied:
            return True
        return self.occupants.get(pos) is None

    def get_neighbors(self, pos, *, include_position=False, diagonal=True):
        x, y = pos
        deltas = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        if diagonal:
            deltas += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        neighbors = [(x + dx, y + dy) for dx, dy in deltas]
        if include_position:
            neighbors.insert(0, pos)
        return neighbors

    def in_bounds(self, _pos):
        return True


class FakeGame:
    def __init__(self, conn=None, board=None):
        self.events = FakeEvents()
        self.heroes = []
        self.enemies = []
        self.board = board or FakeBoard()
        self.conn = conn or FakeConn()
        self.ui_log = lambda *a, **k: None


class Hero:
    def __init__(self, pos=(0, 0)):
        self.position = pos
        self.statuses = []
        self.bonuses = []
        self.object_id = "hero-1"

    def add_status(self, status):
        self.statuses.append(status)
        return True

    def remove_status(self, status):
        sid = getattr(status, "id", status)
        self.statuses = [item for item in self.statuses if getattr(item, "id", item) != sid]
        return True

    def has_status(self, status_id):
        return any(getattr(item, "id", item) == status_id for item in self.statuses)


class Enemy:
    def __init__(self, pos=(1, 0), hp=40, ac=10):
        self.position = pos
        self.hp = hp
        self.ac = ac
        self.statuses = []
        self.last_damage_type = None

    def add_status(self, status):
        self.statuses.append(status)
        return True

    def remove_status(self, status):
        sid = getattr(status, "id", status)
        self.statuses = [item for item in self.statuses if getattr(item, "id", item) != sid]
        return True

    def has_status(self, status_id):
        return any(getattr(item, "id", item) == status_id for item in self.statuses)

    def apply_damage(self, amount, dmg_type="slashing", nonlethal=False):
        del nonlethal
        self.last_damage_type = dmg_type
        self.hp -= int(amount)
        return self.hp, self.hp <= 0


def _ctx(game, hero):
    return EventContext(game=game, actor=hero)


def _setup_game(enemy_pos):
    hero = Hero((0, 0))
    enemy = Enemy(enemy_pos)
    board = FakeBoard()
    board.occupants = {hero.position: hero, enemy.position: enemy}
    game = FakeGame(conn=FakeConn([enemy.position]), board=board)
    game.heroes = [hero]
    game.enemies = [enemy]
    return game, hero, enemy


def test_weapon_items_profiles_and_aliases():
    rapier = create_weapon("rapier")
    dagger = create_weapon("dagger")
    halberd = create_weapon("halberd")
    shortbow = create_weapon("shortbow")
    longbow = create_weapon("longbow")
    light_crossbow = create_weapon("light_crossbow")
    javelin = create_weapon("javelin")

    assert rapier is not None and rapier.weapon_group == "sword"
    assert "deadly:d8" in rapier.traits
    assert dagger is not None and dagger.damage_type == DamageType.PIERCING.value
    assert "versatile:s" in dagger.traits
    assert halberd is not None and int(halberd.hands_required) == 2
    assert "reach:10" in halberd.traits
    assert shortbow is not None and shortbow.range_increment_ft == 60
    assert "deadly:d10" in shortbow.traits
    assert longbow is not None and "deadly:d10" in longbow.traits
    assert light_crossbow is not None and int(light_crossbow.reload) == 1
    assert javelin is not None and javelin.ranged is True
    assert normalize_weapon_id("lekka kusza") == "light_crossbow"


def test_halberd_reach_is_compatible_with_existing_reach_mechanics(monkeypatch):
    game, hero, enemy = _setup_game((2, 0))
    rolls = iter([20, 5])
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.prompt_for_roll",
        lambda *_, **__: next(rolls),
    )
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.refresh_flanking_statuses",
        lambda *_: None,
    )

    result = dispatch_event("halberd", _ctx(game, hero))
    assert result.success
    assert enemy.hp < 40


def test_critical_specialization_sword_requires_status(monkeypatch):
    game, hero, enemy = _setup_game((1, 0))
    rolls = iter([20, 5, 20, 5])
    monkeypatch.setattr(
        basic_melee_attack_event,
        "prompt_for_roll",
        lambda *_, **__: next(rolls),
    )
    monkeypatch.setattr(basic_melee_attack_event, "refresh_flanking_statuses", lambda *_: None)

    # Bez statusu efekt krytyczny grupy nie odpala.
    result_no_status = dispatch_event("longsword", _ctx(game, hero))
    assert result_no_status.success
    assert not enemy.has_status("off_guard")

    # Ze statusem grupy sword efekt odpala.
    hero.add_status(Status(id="critical_specialization", data={"weapon_groups": ["sword"]}))
    result_with_status = dispatch_event("longsword", _ctx(game, hero))
    assert result_with_status.success
    assert enemy.has_status("off_guard")


def test_critical_specialization_knife_adds_persistent_bleed(monkeypatch):
    game, hero, enemy = _setup_game((1, 0))
    hero.add_status(Status(id="critical_specialization", data={"weapon_groups": ["knife"]}))
    rolls = iter([20, 4, 6])  # attack, dmg, bleed
    monkeypatch.setattr(
        basic_melee_attack_event,
        "prompt_for_roll",
        lambda *_, **__: next(rolls),
    )
    monkeypatch.setattr(basic_melee_attack_event, "refresh_flanking_statuses", lambda *_: None)

    result = dispatch_event("dagger", _ctx(game, hero))
    assert result.success
    persistent = [s for s in enemy.statuses if getattr(s, "id", None) == "persistent_damage"]
    assert persistent
    assert int((persistent[0].data or {}).get("amount", 0)) == 6
    assert (persistent[0].data or {}).get("damage_type") == DamageType.BLEED.value


def test_critical_specialization_hammer_knocks_target_prone(monkeypatch):
    game, hero, enemy = _setup_game((1, 0))
    hero.add_status(Status(id="critical_specialization", data={"weapon_groups": ["hammer"]}))
    rolls = iter([20, 4])
    monkeypatch.setattr(
        basic_melee_attack_event,
        "prompt_for_roll",
        lambda *_, **__: next(rolls),
    )
    monkeypatch.setattr(basic_melee_attack_event, "refresh_flanking_statuses", lambda *_: None)

    result = dispatch_event("warhammer", _ctx(game, hero))
    assert result.success
    assert enemy.has_status("prone")


def test_critical_specialization_crossbow_applies_slowed_or_pinned(monkeypatch):
    game, hero, enemy = _setup_game((3, 0))
    hero.add_status(Status(id="critical_specialization", data={"weapon_groups": ["crossbow"]}))
    rolls = iter([20, 4])
    monkeypatch.setattr(
        base_attack_range_event,
        "prompt_for_roll",
        lambda *_, **__: next(rolls),
    )

    result = dispatch_event("light_crossbow", _ctx(game, hero))
    assert result.success
    assert enemy.has_status("speed_penalty") or enemy.has_status("immobilized")
