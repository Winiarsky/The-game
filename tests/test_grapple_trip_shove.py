from types import SimpleNamespace

from GameObjects.events.base import EventContext
from GameObjects.events.grapple_event import GrappleEvent
from GameObjects.events.trip_event import TripEvent
from GameObjects.events.shove_event import ShoveEvent
from GameObjects.events.disarm_event import DisarmEvent
from GameObjects.events.parry_event import ParryEvent
from GameObjects.interactions_mixin import BonusMixin, StatusMixin
from statuses import GRABBED_STATUS, PRONE_STATUS
from states.combat import Combat


class DummyConn:
    def set_leds(self, *_a, **_k):
        return None

    def leds_off(self):
        return None

    def scan_board(self, positions):
        return positions[0] if positions else None


class DummyEvents:
    def __init__(self):
        self.emitted = []

    def safe_emit_action(self, **payload):
        return_event = bool(payload.pop("return_event", False))
        self.emitted.append(payload)
        if return_event:
            return dict(payload)
        return True


class DisruptingEvents(DummyEvents):
    def safe_emit_action(self, **payload):
        return_event = bool(payload.pop("return_event", False))
        self.emitted.append(payload)
        if return_event:
            return {"disrupted": True, "disruption_reason": "opportunity_attack_critical_manipulate"}
        return True


class DummyBoard:
    def __init__(self, occupants):
        self._occ = dict(occupants)

    def get_neighbors(self, pos, include_position=False, diagonal=True):
        x, y = pos
        res = [
            (x - 1, y),
            (x + 1, y),
            (x, y - 1),
            (x, y + 1),
        ]
        if diagonal:
            res += [(x - 1, y - 1), (x - 1, y + 1), (x + 1, y - 1), (x + 1, y + 1)]
        return res

    def occupant_at(self, pos):
        return self._occ.get(pos)

    def can_enter(self, pos, allow_occupied=False):
        return pos not in self._occ

    def is_blocked(self, *_a, **_k):
        return False

    def move(self, src, dst):
        obj = self._occ.pop(src, None)
        if obj is not None:
            self._occ[dst] = obj


class DummyActor(StatusMixin, BonusMixin):
    def __init__(self, object_id, position):
        super().__init__()
        self.object_id = object_id
        self.position = position
        self.bonuses = []
        self.inventory = []
        self.equipped_weapon_item_ids = []
        self.equipped_shield = None

    def apply_damage(self, amount, *_a, **_k):
        self.last_damage = amount
        return 0, False


def _equip_trait_weapon(actor, *, item_id: str, traits: tuple[str, ...]):
    weapon = SimpleNamespace(
        item_id=item_id,
        instance_id=f"{item_id}-1",
        category="weapon",
        traits=tuple(traits),
        hands_required=1,
        ranged=False,
    )
    actor.inventory = [weapon]
    actor.equipped_weapon_item_ids = [weapon.instance_id]
    return weapon


def _game(hero, enemy, board):
    game = SimpleNamespace(
        heroes=[hero],
        enemies=[enemy],
        board=board,
        conn=DummyConn(),
        events=DummyEvents(),
        ui_log=lambda *_a, **_k: None,
        ui_event=lambda *_a, **_k: None,
    )
    game.state = Combat(game)
    return game


def _ctx(game, actor):
    return EventContext(game=game, actor=actor)


def test_grapple_success_applies_grabbed(monkeypatch):
    hero = DummyActor("h1", (0, 0))
    enemy = DummyActor("e1", (1, 0))
    board = DummyBoard({hero.position: hero, enemy.position: enemy})
    game = _game(hero, enemy, board)

    monkeypatch.setattr(
        "GameObjects.events.grapple_event.resolve_skill_check_with_sources",
        lambda **_k: SimpleNamespace(outcome="success"),
    )
    monkeypatch.setattr(
        "GameObjects.events.grapple_event.compute_skill_modifier_with_sources",
        lambda **_k: (0, [], []),
    )

    res = GrappleEvent().execute(_ctx(game, hero))
    assert res.success is True
    assert enemy.has_status(GRABBED_STATUS)


def test_grapple_critical_failure_grabs_actor(monkeypatch):
    hero = DummyActor("h1", (0, 0))
    enemy = DummyActor("e1", (1, 0))
    board = DummyBoard({hero.position: hero, enemy.position: enemy})
    game = _game(hero, enemy, board)

    monkeypatch.setattr(
        "GameObjects.events.grapple_event.resolve_skill_check_with_sources",
        lambda **_k: SimpleNamespace(outcome="critical_failure"),
    )
    monkeypatch.setattr(
        "GameObjects.events.grapple_event.compute_skill_modifier_with_sources",
        lambda **_k: (0, [], []),
    )

    res = GrappleEvent().execute(_ctx(game, hero))
    assert res.success is True
    assert hero.has_status(GRABBED_STATUS)


def test_trip_critical_success_deals_bludgeoning(monkeypatch):
    hero = DummyActor("h1", (0, 0))
    enemy = DummyActor("e1", (1, 0))
    board = DummyBoard({hero.position: hero, enemy.position: enemy})
    game = _game(hero, enemy, board)

    monkeypatch.setattr(
        "GameObjects.events.trip_event.resolve_skill_check_with_sources",
        lambda **_k: SimpleNamespace(outcome="critical_success"),
    )
    monkeypatch.setattr(
        "GameObjects.events.trip_event.compute_skill_modifier_with_sources",
        lambda **_k: (0, [], []),
    )
    monkeypatch.setattr("GameObjects.events.trip_event.prompt_for_roll", lambda *_, **__: 4)

    res = TripEvent().execute(_ctx(game, hero))
    assert res.success is True
    assert enemy.has_status(PRONE_STATUS)
    assert getattr(enemy, "last_damage", None) == 4


def test_shove_success_moves_target(monkeypatch):
    hero = DummyActor("h1", (0, 0))
    enemy = DummyActor("e1", (1, 0))
    board = DummyBoard({hero.position: hero, enemy.position: enemy})
    game = _game(hero, enemy, board)

    monkeypatch.setattr(
        "GameObjects.events.shove_event.resolve_skill_check_with_sources",
        lambda **_k: SimpleNamespace(outcome="success"),
    )
    monkeypatch.setattr(
        "GameObjects.events.shove_event.compute_skill_modifier_with_sources",
        lambda **_k: (0, [], []),
    )

    res = ShoveEvent().execute(_ctx(game, hero))
    assert res.success is True
    assert enemy.position == (2, 0)


def test_grapple_is_disrupted_before_resolution(monkeypatch):
    hero = DummyActor("h1", (0, 0))
    enemy = DummyActor("e1", (1, 0))
    board = DummyBoard({hero.position: hero, enemy.position: enemy})
    game = _game(hero, enemy, board)
    game.events = DisruptingEvents()

    monkeypatch.setattr(
        "GameObjects.events.grapple_event.compute_skill_modifier_with_sources",
        lambda **_k: (0, [], []),
    )

    res = GrappleEvent().execute(_ctx(game, hero))

    assert res.success is False
    assert res.consumed_action is True
    assert "przerwane" in str(res.message or "").lower()
    assert not enemy.has_status(GRABBED_STATUS)


def test_trip_with_trait_reach_targets_enemy_two_cells_away(monkeypatch):
    hero = DummyActor("h1", (0, 0))
    enemy = DummyActor("e1", (2, 0))
    _equip_trait_weapon(hero, item_id="trip_spear", traits=("trip", "reach:10"))
    board = DummyBoard({hero.position: hero, enemy.position: enemy})
    game = _game(hero, enemy, board)

    monkeypatch.setattr(
        "GameObjects.events.trip_event.resolve_skill_check_with_sources",
        lambda **_k: SimpleNamespace(outcome="success"),
    )
    monkeypatch.setattr(
        "GameObjects.events.trip_event.compute_skill_modifier_with_sources",
        lambda **_k: (0, [], []),
    )

    res = TripEvent().execute(_ctx(game, hero))

    assert res.success is True
    assert enemy.has_status(PRONE_STATUS)


def test_grapple_with_trait_reach_targets_enemy_two_cells_away(monkeypatch):
    hero = DummyActor("h1", (0, 0))
    enemy = DummyActor("e1", (2, 0))
    _equip_trait_weapon(hero, item_id="grapple_staff", traits=("grapple", "reach:10"))
    board = DummyBoard({hero.position: hero, enemy.position: enemy})
    game = _game(hero, enemy, board)

    monkeypatch.setattr(
        "GameObjects.events.grapple_event.resolve_skill_check_with_sources",
        lambda **_k: SimpleNamespace(outcome="success"),
    )
    monkeypatch.setattr(
        "GameObjects.events.grapple_event.compute_skill_modifier_with_sources",
        lambda **_k: (0, [], []),
    )

    res = GrappleEvent().execute(_ctx(game, hero))

    assert res.success is True
    assert enemy.has_status(GRABBED_STATUS)


def test_shove_with_trait_reach_targets_enemy_two_cells_away(monkeypatch):
    hero = DummyActor("h1", (0, 0))
    enemy = DummyActor("e1", (2, 0))
    _equip_trait_weapon(hero, item_id="shove_spear", traits=("shove", "reach:10"))
    board = DummyBoard({hero.position: hero, enemy.position: enemy})
    game = _game(hero, enemy, board)

    monkeypatch.setattr(
        "GameObjects.events.shove_event.resolve_skill_check_with_sources",
        lambda **_k: SimpleNamespace(outcome="success"),
    )
    monkeypatch.setattr(
        "GameObjects.events.shove_event.compute_skill_modifier_with_sources",
        lambda **_k: (0, [], []),
    )

    res = ShoveEvent().execute(_ctx(game, hero))

    assert res.success is True
    assert enemy.position == (3, 0)


def test_disarm_success_applies_attack_penalty(monkeypatch):
    hero = DummyActor("h1", (0, 0))
    enemy = DummyActor("e1", (1, 0))
    _equip_trait_weapon(hero, item_id="disarm_whip", traits=("disarm",))
    board = DummyBoard({hero.position: hero, enemy.position: enemy})
    game = _game(hero, enemy, board)

    monkeypatch.setattr(
        "GameObjects.events.disarm_event.resolve_skill_check_with_sources",
        lambda **_k: SimpleNamespace(outcome="success"),
    )
    monkeypatch.setattr(
        "GameObjects.events.disarm_event.compute_skill_modifier_with_sources",
        lambda **_k: (0, [], []),
    )

    res = DisarmEvent().execute(_ctx(game, hero))

    assert res.success is True
    assert enemy.compute_modifier("attack_melee") == -2
    assert enemy.compute_modifier("attack_ranged") == -2


def test_parry_requires_trait_and_grants_ac_bonus():
    hero = DummyActor("h1", (0, 0))
    enemy = DummyActor("e1", (1, 0))
    board = DummyBoard({hero.position: hero, enemy.position: enemy})
    game = _game(hero, enemy, board)

    fail = ParryEvent().execute(_ctx(game, hero))
    assert fail.success is False

    _equip_trait_weapon(hero, item_id="parry_rapier", traits=("parry",))
    ok = ParryEvent().execute(_ctx(game, hero))
    assert ok.success is True
    assert hero.compute_modifier("ac") == 1
