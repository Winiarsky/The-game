from types import SimpleNamespace
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from GameObjects.events.base import EventContext, EventResult
from GameObjects.events.bombs.bottled_lightning_event import BottledLightningEvent
from GameObjects.events.bombs.frost_vial_event import FrostVialEvent
from GameObjects.events.bombs.tanglefoot_bag_event import TanglefootBagEvent
from GameObjects.events.bombs.thunderstone_event import ThunderstoneEvent
from GameObjects.events.bombs.alchemists_fire_event import AlchemistsFireEvent
from GameObjects.items.inventory import add_alchemical_item
from states.combat import Combat
from statuses import PERSISTENT_DAMAGE_STATUS, Status


class FakeConn:
    def __init__(self, responses):
        self.responses = list(responses)

    def set_leds(self, positions, colors):
        pass

    def scan_board(self, _positions):
        return self.responses.pop(0)

    def leds_off(self):
        pass


class BoardStub:
    def __init__(self, width=5, height=5):
        self.width = width
        self.height = height

    def in_bounds(self, pos):
        x, y = pos
        return 0 <= x < self.width and 0 <= y < self.height

    def get_neighbors(self, pos, include_position=False, diagonal=True):
        if not self.in_bounds(pos):
            return []
        x, y = pos
        neighbors = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                if not diagonal and abs(dx) + abs(dy) != 1:
                    continue
                candidate = (x + dx, y + dy)
                if self.in_bounds(candidate):
                    neighbors.append(candidate)
        if include_position:
            neighbors.append(pos)
        return neighbors

    def remove(self, _pos):
        pass


class DummyEnemy:
    def __init__(self, pos, hp=20, ac=10, object_id="enemy"):
        self.position = pos
        self.hp = hp
        self.ac = ac
        self.object_id = object_id
        self.statuses = []

    def apply_damage(self, amount, damage_type):
        self.hp -= amount
        return self.hp, self.hp <= 0

    def add_status(self, status):
        self.statuses.append(status)
        return True


class DummyHero:
    def __init__(self, pos, hp=20, name="Hero", object_id="hero"):
        self.position = pos
        self.hp = hp
        self.name = name
        self.object_id = object_id
        self.level = 1
        self.dex_mod = 3
        self.str_mod = 0
        self.ability_modifiers = {
            "strength": 0,
            "dexterity": 3,
        }
        self.weapon_proficiency_ranks = {
            "simple": "trained",
            "martial": "untrained",
            "advanced": "untrained",
            "unarmed": "trained",
        }
        self.bonuses = []
        self.statuses = []

    def add_status(self, status):
        self.statuses.append(status)
        return True

    def apply_damage(self, amount, damage_type):
        self.hp -= amount
        return self.hp, self.hp <= 0


def _dummy_ui(monkeypatch):
    class DummyUI:
        def __init__(self):
            self.messages = []

        def prompt_info(self, title, *, prompt_long=None, **_kwargs):
            self.messages.append((title, prompt_long))
            return "ok"

    ui = DummyUI()
    monkeypatch.setattr("combat.damage_utils.get_ui_client", lambda: ui)
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)
    return ui


def _give_alchemical_item(
    actor,
    event_name: str,
    *,
    preparation_counter: int = 0,
    alchemical_tier: str | None = None,
):
    return add_alchemical_item(
        actor,
        event_name=event_name,
        alchemical_tier=alchemical_tier,
        preparation_counter=preparation_counter,
    )


def test_bottled_lightning_applies_flat_footed(monkeypatch):
    event = BottledLightningEvent()
    monkeypatch.setattr(event, "_prompt_level", lambda: "lesser")
    monkeypatch.setattr(event, "_prompt_damage", lambda *_args, **_kwargs: 5)
    monkeypatch.setattr("GameObjects.events.bombs.base_alchemical_bomb_event.prompt_for_roll", lambda *_, **__: 15)
    _dummy_ui(monkeypatch)

    hero = DummyHero((0, 0), object_id="hero-1")
    _give_alchemical_item(hero, event.name)
    target = DummyEnemy((1, 0), object_id="enemy-1")
    game = SimpleNamespace(
        conn=FakeConn(responses=[(1, 0)]),
        board=BoardStub(),
        heroes=[hero],
        enemies=[target],
        ui_log=lambda _msg=None: None,
    )
    ctx = EventContext(game=game, actor=hero)

    res = event.execute(ctx)
    assert res.success
    assert any(s.id == "flat_footed" for s in target.statuses)


def test_frost_vial_applies_speed_penalty_to_enemy(monkeypatch):
    event = FrostVialEvent()
    monkeypatch.setattr(event, "_prompt_level", lambda: "moderate")
    monkeypatch.setattr(event, "_prompt_damage", lambda *_args, **_kwargs: 6)
    monkeypatch.setattr("GameObjects.events.bombs.base_alchemical_bomb_event.prompt_for_roll", lambda *_, **__: 15)
    _dummy_ui(monkeypatch)

    hero = DummyHero((0, 0), object_id="hero-1")
    _give_alchemical_item(hero, event.name)
    target = DummyEnemy((1, 0), object_id="enemy-1")
    game = SimpleNamespace(
        conn=FakeConn(responses=[(1, 0)]),
        board=BoardStub(),
        heroes=[hero],
        enemies=[target],
        ui_log=lambda _msg=None: None,
    )
    ctx = EventContext(game=game, actor=hero)

    res = event.execute(ctx)
    assert res.success
    assert any(s.id == "speed_penalty" for s in target.statuses)


def test_tanglefoot_bag_critical_immobilizes(monkeypatch):
    event = TanglefootBagEvent()
    monkeypatch.setattr(event, "_prompt_level", lambda: "lesser")
    monkeypatch.setattr("GameObjects.events.bombs.base_alchemical_bomb_event.prompt_for_roll", lambda *_, **__: 30)
    _dummy_ui(monkeypatch)

    hero = DummyHero((0, 0), object_id="hero-1")
    _give_alchemical_item(hero, event.name)
    target = DummyEnemy((1, 0), object_id="enemy-1")
    game = SimpleNamespace(
        conn=FakeConn(responses=[(1, 0)]),
        board=BoardStub(),
        heroes=[hero],
        enemies=[target],
        ui_log=lambda _msg=None: None,
    )
    ctx = EventContext(game=game, actor=hero)

    res = event.execute(ctx)
    assert res.success
    assert any(s.id == "speed_penalty" for s in target.statuses)
    assert any(s.id == "immobilized" for s in target.statuses)


def test_thunderstone_applies_deafened_on_failed_save(monkeypatch):
    event = ThunderstoneEvent()
    monkeypatch.setattr(event, "_prompt_level", lambda: "lesser")
    monkeypatch.setattr(event, "_prompt_damage", lambda *_args, **_kwargs: 4)
    monkeypatch.setattr("GameObjects.events.bombs.base_alchemical_bomb_event.prompt_for_roll", lambda *_, **__: 15)

    def _fail_save(**_kwargs):
        return SimpleNamespace(outcome="failure", total=0, modifier=0)

    monkeypatch.setattr("GameObjects.events.bombs.thunderstone_event.resolve_skill_check_with_sources", _fail_save)
    _dummy_ui(monkeypatch)

    hero = DummyHero((0, 0), object_id="hero-1")
    _give_alchemical_item(hero, event.name)
    enemy = DummyEnemy((1, 0), object_id="enemy-1")
    game = SimpleNamespace(
        conn=FakeConn(responses=[(1, 0)]),
        board=BoardStub(),
        heroes=[hero],
        enemies=[enemy],
        ui_log=lambda _msg=None: None,
    )
    ctx = EventContext(game=game, actor=hero)

    res = event.execute(ctx)
    assert res.success
    assert any(s.id == "deafened" for s in enemy.statuses)


def test_alchemists_fire_adds_persistent_damage(monkeypatch):
    event = AlchemistsFireEvent()
    monkeypatch.setattr(event, "_prompt_level", lambda: "lesser")
    monkeypatch.setattr(event, "_prompt_damage", lambda *_args, **_kwargs: 6)
    monkeypatch.setattr("GameObjects.events.bombs.base_alchemical_bomb_event.prompt_for_roll", lambda *_, **__: 15)
    _dummy_ui(monkeypatch)

    hero = DummyHero((0, 0), object_id="hero-1")
    _give_alchemical_item(hero, event.name)
    target = DummyEnemy((1, 0), object_id="enemy-1")
    game = SimpleNamespace(
        conn=FakeConn(responses=[(1, 0)]),
        board=BoardStub(),
        heroes=[hero],
        enemies=[target],
        ui_log=lambda _msg=None: None,
    )
    ctx = EventContext(game=game, actor=hero)

    res = event.execute(ctx)
    assert res.success
    assert any(s.id == PERSISTENT_DAMAGE_STATUS.id for s in target.statuses)


def test_bomb_triggers_projectile_and_blast_led_fx(monkeypatch):
    event = AlchemistsFireEvent()
    monkeypatch.setattr(event, "_prompt_level", lambda: "lesser")
    monkeypatch.setattr(event, "_prompt_damage", lambda *_args, **_kwargs: 6)
    monkeypatch.setattr("GameObjects.events.bombs.base_alchemical_bomb_event.prompt_for_roll", lambda *_, **__: 15)
    _dummy_ui(monkeypatch)

    projectile_calls = []
    burst_calls = []
    monkeypatch.setattr(
        "GameObjects.events.bombs.base_alchemical_bomb_event.animate_projectile_line",
        lambda conn, start, end, **_kwargs: projectile_calls.append((start, end)) or True,
    )
    monkeypatch.setattr(
        "GameObjects.events.bombs.base_alchemical_bomb_event.animate_area_wave",
        lambda conn, origin, area_positions, **_kwargs: burst_calls.append((origin, list(area_positions))) or True,
    )

    hero = DummyHero((0, 0), object_id="hero-1")
    _give_alchemical_item(hero, event.name)
    target = DummyEnemy((1, 0), object_id="enemy-1")
    game = SimpleNamespace(
        conn=FakeConn(responses=[(1, 0)]),
        board=BoardStub(),
        heroes=[hero],
        enemies=[target],
        ui_log=lambda _msg=None: None,
    )
    ctx = EventContext(game=game, actor=hero)

    res = event.execute(ctx)

    assert res.success
    assert projectile_calls == [((0, 0), (1, 0))]
    assert burst_calls
    assert burst_calls[0][0] == (1, 0)
    assert (1, 0) in set(burst_calls[0][1])


def test_alchemists_fire_burn_it_increases_persistent(monkeypatch):
    event = AlchemistsFireEvent()
    monkeypatch.setattr(event, "_prompt_level", lambda: "lesser")
    monkeypatch.setattr(event, "_prompt_damage", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr("GameObjects.events.bombs.base_alchemical_bomb_event.prompt_for_roll", lambda *_, **__: 15)
    _dummy_ui(monkeypatch)

    hero = DummyHero((0, 0), object_id="hero-1")
    hero.add_status(Status(id="burn_it"))
    _give_alchemical_item(hero, event.name)
    target = DummyEnemy((1, 0), object_id="enemy-1")
    game = SimpleNamespace(
        conn=FakeConn(responses=[(1, 0)]),
        board=BoardStub(),
        heroes=[hero],
        enemies=[target],
        ui_log=lambda _msg=None: None,
    )
    ctx = EventContext(game=game, actor=hero)

    res = event.execute(ctx)
    assert res.success
    persistent = next((s for s in target.statuses if s.id == PERSISTENT_DAMAGE_STATUS.id), None)
    assert persistent is not None
    assert int((persistent.data or {}).get("amount", 0) or 0) == 2


def test_far_lobber_extends_bomb_range(monkeypatch):
    event = BottledLightningEvent()
    monkeypatch.setattr(event, "_prompt_level", lambda: "lesser")
    monkeypatch.setattr(event, "_prompt_damage", lambda *_args, **_kwargs: 4)
    monkeypatch.setattr("GameObjects.events.bombs.base_alchemical_bomb_event.prompt_for_roll", lambda *_, **__: 15)
    _dummy_ui(monkeypatch)

    hero = DummyHero((0, 0), object_id="hero-1")
    _give_alchemical_item(hero, event.name)
    target = DummyEnemy((5, 0), object_id="enemy-1")
    game = SimpleNamespace(
        conn=FakeConn(responses=[(5, 0)]),
        board=BoardStub(width=10, height=5),
        heroes=[hero],
        enemies=[target],
        ui_log=lambda _msg=None: None,
    )
    ctx = EventContext(game=game, actor=hero)

    res = event.execute(ctx)
    assert not res.success
    assert res.message == "Brak celu w zasięgu."

    hero.add_status(Status(id="far_lobber", data={"bomb_range_bonus": 10}))
    game.conn = FakeConn(responses=[(5, 0)])
    res = event.execute(ctx)
    assert res.success


def test_quick_bomber_reduces_bomb_action_cost(monkeypatch):
    event = BottledLightningEvent()
    monkeypatch.setattr(event, "execute", lambda _ctx: EventResult(success=True, consumed_action=True))

    hero = DummyHero((0, 0), object_id="hero-1")
    hero.add_status(Status(id="quick_bomber", data={"bomb_action_cost_reduction": 1}))
    _give_alchemical_item(hero, event.name)

    game = SimpleNamespace()
    state = Combat(game)
    game.state = state
    state.actions_used[hero] = 2

    ctx = EventContext(game=game, actor=hero)
    res = event.run(ctx)
    assert res.success


def test_alchemists_fire_attack_prompt_uses_split_roll_stack(monkeypatch):
    event = AlchemistsFireEvent()
    monkeypatch.setattr(event, "_prompt_level", lambda: "lesser")
    monkeypatch.setattr(event, "_prompt_damage", lambda *_args, **_kwargs: 4)
    _dummy_ui(monkeypatch)

    captured = {}

    def _capture_prompt(*_args, **kwargs):
        captured.update(kwargs)
        return 15

    monkeypatch.setattr("GameObjects.events.bombs.base_alchemical_bomb_event.prompt_for_roll", _capture_prompt)

    hero = DummyHero((0, 0), object_id="hero-1")
    _give_alchemical_item(hero, event.name)
    target = DummyEnemy((1, 0), ac=14, object_id="enemy-1")
    game = SimpleNamespace(
        conn=FakeConn(responses=[(1, 0)]),
        board=BoardStub(),
        heroes=[hero],
        enemies=[target],
        ui_log=lambda _msg=None: None,
    )
    ctx = EventContext(game=game, actor=hero)

    res = event.execute(ctx)
    assert res.success
    stack = captured.get("roll_stack", {})
    components = list(stack.get("components", []) or [])
    ids = [str(component.get("id")) for component in components]
    assert "proficiency" in ids
    assert "ability" in ids
    assert int(stack.get("auto_total_modifier", 0) or 0) == int(captured.get("auto_total_modifier", 0) or 0)


def test_alchemists_fire_failure_applies_splash_to_target_and_adjacent(monkeypatch):
    event = AlchemistsFireEvent()
    monkeypatch.setattr(event, "_prompt_level", lambda: "lesser")
    monkeypatch.setattr(event, "_prompt_damage", lambda *_args, **_kwargs: 4)
    monkeypatch.setattr("GameObjects.events.bombs.base_alchemical_bomb_event.prompt_for_roll", lambda *_, **__: 2)
    _dummy_ui(monkeypatch)

    hero = DummyHero((0, 0), object_id="hero-1")
    _give_alchemical_item(hero, event.name)
    target = DummyEnemy((1, 0), hp=20, ac=14, object_id="enemy-1")
    enemy_adj = DummyEnemy((1, 1), hp=20, ac=14, object_id="enemy-2")
    game = SimpleNamespace(
        conn=FakeConn(responses=[(1, 0)]),
        board=BoardStub(),
        heroes=[hero],
        enemies=[target, enemy_adj],
        ui_log=lambda _msg=None: None,
    )
    ctx = EventContext(game=game, actor=hero)

    res = event.execute(ctx)
    assert res.success
    assert "rozprysk" in (res.message or "").lower()
    assert target.hp == 19
    assert enemy_adj.hp == 19


def test_alchemists_fire_success_splash_hits_target_and_adjacent_allies(monkeypatch):
    event = AlchemistsFireEvent()
    monkeypatch.setattr(event, "_prompt_level", lambda: "lesser")
    monkeypatch.setattr(event, "_prompt_damage", lambda *_args, **_kwargs: 6)
    monkeypatch.setattr("GameObjects.events.bombs.base_alchemical_bomb_event.prompt_for_roll", lambda *_, **__: 15)
    _dummy_ui(monkeypatch)

    hero = DummyHero((0, 0), hp=20, object_id="hero-1")
    ally = DummyHero((0, 1), hp=20, object_id="hero-2")
    _give_alchemical_item(hero, event.name)
    target = DummyEnemy((1, 0), hp=20, ac=14, object_id="enemy-1")
    enemy_adj = DummyEnemy((1, 1), hp=20, ac=14, object_id="enemy-2")
    game = SimpleNamespace(
        conn=FakeConn(responses=[(1, 0)]),
        board=BoardStub(),
        heroes=[hero, ally],
        enemies=[target, enemy_adj],
        ui_log=lambda _msg=None: None,
    )
    ctx = EventContext(game=game, actor=hero)

    res = event.execute(ctx)
    assert res.success
    # Success: cel dostaje damage + splash; sąsiedzi tylko splash.
    assert target.hp == 13
    assert enemy_adj.hp == 19
    assert hero.hp == 19
    assert ally.hp == 19
    assert any(s.id == PERSISTENT_DAMAGE_STATUS.id for s in target.statuses)


def test_alchemists_fire_failure_applies_only_splash_and_no_persistent(monkeypatch):
    event = AlchemistsFireEvent()
    monkeypatch.setattr(event, "_prompt_level", lambda: "lesser")
    monkeypatch.setattr("GameObjects.events.bombs.base_alchemical_bomb_event.prompt_for_roll", lambda *_, **__: 2)
    _dummy_ui(monkeypatch)

    hero = DummyHero((0, 0), hp=20, object_id="hero-1")
    ally = DummyHero((0, 1), hp=20, object_id="hero-2")
    _give_alchemical_item(hero, event.name)
    target = DummyEnemy((1, 0), hp=20, ac=16, object_id="enemy-1")
    enemy_adj = DummyEnemy((1, 1), hp=20, ac=16, object_id="enemy-2")
    game = SimpleNamespace(
        conn=FakeConn(responses=[(1, 0)]),
        board=BoardStub(),
        heroes=[hero, ally],
        enemies=[target, enemy_adj],
        ui_log=lambda _msg=None: None,
    )
    ctx = EventContext(game=game, actor=hero)

    res = event.execute(ctx)
    assert res.success
    # Failure: tylko splash na celu i wokół, bez direct i bez persistent.
    assert target.hp == 19
    assert enemy_adj.hp == 19
    assert hero.hp == 19
    assert ally.hp == 19
    assert not any(s.id == PERSISTENT_DAMAGE_STATUS.id for s in target.statuses)


def test_alchemists_fire_critical_success_doubles_direct_not_splash(monkeypatch):
    event = AlchemistsFireEvent()
    monkeypatch.setattr(event, "_prompt_level", lambda: "lesser")
    monkeypatch.setattr(event, "_prompt_damage", lambda *_args, **_kwargs: 6)
    monkeypatch.setattr("GameObjects.events.bombs.base_alchemical_bomb_event.prompt_for_roll", lambda *_, **__: 24)
    _dummy_ui(monkeypatch)

    hero = DummyHero((0, 0), hp=20, object_id="hero-1")
    ally = DummyHero((0, 1), hp=20, object_id="hero-2")
    _give_alchemical_item(hero, event.name)
    target = DummyEnemy((1, 0), hp=20, ac=14, object_id="enemy-1")
    enemy_adj = DummyEnemy((1, 1), hp=20, ac=14, object_id="enemy-2")
    game = SimpleNamespace(
        conn=FakeConn(responses=[(1, 0)]),
        board=BoardStub(),
        heroes=[hero, ally],
        enemies=[target, enemy_adj],
        ui_log=lambda _msg=None: None,
    )
    ctx = EventContext(game=game, actor=hero)

    res = event.execute(ctx)
    assert res.success
    # Critical success: 2x direct + 1x splash (splash nie jest podwajany).
    assert target.hp == 7
    assert enemy_adj.hp == 19
    assert hero.hp == 19
    assert ally.hp == 19


def test_alchemists_fire_critical_failure_has_no_splash(monkeypatch):
    event = AlchemistsFireEvent()
    monkeypatch.setattr(event, "_prompt_level", lambda: "lesser")
    monkeypatch.setattr("GameObjects.events.bombs.base_alchemical_bomb_event.prompt_for_roll", lambda *_, **__: 1)
    _dummy_ui(monkeypatch)

    hero = DummyHero((0, 0), hp=20, object_id="hero-1")
    ally = DummyHero((0, 1), hp=20, object_id="hero-2")
    _give_alchemical_item(hero, event.name)
    target = DummyEnemy((1, 0), hp=20, ac=20, object_id="enemy-1")
    enemy_adj = DummyEnemy((1, 1), hp=20, ac=20, object_id="enemy-2")
    game = SimpleNamespace(
        conn=FakeConn(responses=[(1, 0)]),
        board=BoardStub(),
        heroes=[hero, ally],
        enemies=[target, enemy_adj],
        ui_log=lambda _msg=None: None,
    )
    ctx = EventContext(game=game, actor=hero)

    res = event.execute(ctx)
    assert res.success
    assert "rozprysk" not in (res.message or "").lower()
    assert hero.hp == 20
    assert target.hp == 20
    assert enemy_adj.hp == 20
    assert ally.hp == 20


def test_bomb_uses_single_item_tier_without_prompt(monkeypatch):
    event = AlchemistsFireEvent()
    monkeypatch.setattr(event, "_prompt_damage", lambda *_args, **_kwargs: 4)
    monkeypatch.setattr("GameObjects.events.bombs.base_alchemical_bomb_event.prompt_for_roll", lambda *_, **__: 15)
    monkeypatch.setattr(event, "_prompt_level", lambda: (_ for _ in ()).throw(AssertionError("prompt tier should not be called")))
    _dummy_ui(monkeypatch)

    hero = DummyHero((0, 0), object_id="hero-1")
    _give_alchemical_item(hero, event.name, alchemical_tier="lesser")
    target = DummyEnemy((1, 0), hp=20, ac=14, object_id="enemy-1")
    game = SimpleNamespace(
        conn=FakeConn(responses=[(1, 0)]),
        board=BoardStub(),
        heroes=[hero],
        enemies=[target],
        ui_log=lambda _msg=None: None,
    )
    ctx = EventContext(game=game, actor=hero)

    res = event.execute(ctx)
    assert res.success
    assert target.hp == 15  # 4 direct + 1 splash


def test_bomb_prompts_tier_when_multiple_variants_in_inventory(monkeypatch):
    event = AlchemistsFireEvent()
    monkeypatch.setattr(event, "_prompt_damage", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr("GameObjects.events.bombs.base_alchemical_bomb_event.prompt_for_roll", lambda *_, **__: 15)

    class DummyUI:
        enabled = True

        def prompt_info(self, *_args, **_kwargs):
            return "ok"

        def prompt_choice(self, *_args, **_kwargs):
            return "moderate"

    ui = DummyUI()
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)
    monkeypatch.setattr("combat.damage_utils.get_ui_client", lambda: ui)

    hero = DummyHero((0, 0), object_id="hero-1")
    _give_alchemical_item(hero, event.name, alchemical_tier="lesser")
    _give_alchemical_item(hero, event.name, alchemical_tier="moderate")
    target = DummyEnemy((1, 0), hp=20, ac=14, object_id="enemy-1")
    game = SimpleNamespace(
        conn=FakeConn(responses=[(1, 0)]),
        board=BoardStub(),
        heroes=[hero],
        enemies=[target],
        ui_log=lambda _msg=None: None,
    )
    ctx = EventContext(game=game, actor=hero)

    res = event.execute(ctx)
    assert res.success
    assert target.hp == 18  # moderate splash = 2
    remaining = [
        item
        for item in (getattr(hero, "inventory", []) or [])
        if str(getattr(item, "event_name", "")).strip().lower() == event.name
    ]
    assert len(remaining) == 1
    assert str(getattr(remaining[0], "alchemical_tier", "")).strip().lower() == "lesser"


def test_log_splash_mode_sends_idle_hint_to_action_panel():
    event = AlchemistsFireEvent()
    logs: list[str] = []
    hints: list[tuple[str, str | None]] = []

    game = SimpleNamespace(
        ui_log=lambda msg: logs.append(str(msg)),
        ui_idle_hint=lambda title, text=None: hints.append((str(title), None if text is None else str(text))),
    )
    ctx = EventContext(game=game, actor=None)

    event._log_splash_mode(ctx, True)
    assert logs and "Bomber: splash ON" in logs[-1]
    assert hints
    title, text = hints[-1]
    assert "Bomber: splash ON" in title
    assert "Kliknij cel" in str(text or "")
