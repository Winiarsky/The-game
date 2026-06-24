import sys
from pathlib import Path
import types

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import GameObjects.events.all_events  # noqa: F401  # rejestracja eventów
from GameObjects.events.registry import dispatch_event
from GameObjects.events.base import EventContext
from GameObjects.events.attack import base_attack_range_event
from GameObjects.events.attack import attack_range_long_bow
from GameObjects.Obstacles.simple_obstacle import SimpleObstacle
from bonuses import BonusEffect, BonusType
from GameObjects.items.shield import create_shield
from board import consts


class FakeEvents:
    def __init__(self):
        self.emitted = []

    def safe_emit_action(self, **payload):
        self.emitted.append(payload)


class FakeConn:
    def __init__(self, choice=None):
        self.choice = choice
        self.led_calls = []
        self.leds_off_calls = 0

    def set_leds(self, *args, **kwargs):
        self.led_calls.append((args, kwargs))
        return None

    def scan_board(self, acceptable_responses=None):
        if isinstance(self.choice, list):
            if not self.choice:
                return None
            return self.choice.pop(0)
        return self.choice

    def leds_off(self):
        self.leds_off_calls += 1
        return None


class FakeUI:
    enabled = True
    allow_cli_fallback = False

    def __init__(self):
        self.info_calls = []
        self.choice_calls = []
        self.choice_answers = []

    def prompt_info(self, title, *, prompt_long=None, **_kwargs):
        self.info_calls.append({"title": title, "prompt_long": prompt_long})
        return "ok"

    def prompt_choice(self, title, *, choices=None, prompt_long=None, **_kwargs):
        self.choice_calls.append({"title": title, "choices": list(choices or []), "prompt_long": prompt_long})
        if self.choice_answers:
            return self.choice_answers.pop(0)
        if choices:
            return choices[0]
        return None


class FakeBoard:
    def __init__(self):
        self.occupants = {}
        self.blocked_edges = set()
        self.edge_objs = {}

    def occupant_at(self, pos):
        return self.occupants.get(pos)

    def interactables_at(self, pos):
        return []

    def is_blocked(self, a, b):
        return frozenset((a, b)) in self.blocked_edges

    def get_wall(self, a, b):
        return None

    def edge_interactables_between(self, a, b):
        return self.edge_objs.get(frozenset((a, b)), [])

    def remove(self, pos):
        self.occupants.pop(pos, None)


class FakeGame:
    def __init__(self):
        self.events = FakeEvents()
        self.heroes = []
        self.enemies = []
        self.board = FakeBoard()
        self.conn = FakeConn()
        self.ui = None
        self.ui_log = lambda *_a, **_k: None


class Hero:
    def __init__(self, pos):
        self.position = pos
        self.statuses = []
        self.bonuses = []
        self.equipped_shield = None

    def add_status(self, status):
        self.statuses.append(status)

    def remove_status(self, status):
        self.statuses = [s for s in self.statuses if getattr(s, "id", s) != getattr(status, "id", status)]

    def has_status(self, status_id):
        return any(getattr(s, "id", s) == status_id for s in self.statuses)


class Enemy:
    def __init__(self, pos, hp=12, ac=12):
        self.position = pos
        self.hp = hp
        self.ac = ac
        self.statuses = []
        self.bonuses = []

    def apply_damage(self, amount, dmg_type="piercing"):
        self.hp -= amount
        return self.hp, self.hp <= 0


def _ctx(game, hero):
    return EventContext(game=game, actor=hero)


def test_longbow_hits_without_cover(monkeypatch):
    hero = Hero((0, 0))
    enemy = Enemy((2, 0), hp=8, ac=10)
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position

    rolls = iter([15, 5])  # hit, dmg
    monkeypatch.setattr(base_attack_range_event, "prompt_for_roll", lambda *_, **__: next(rolls))

    result = dispatch_event("longbow", _ctx(game, hero))
    assert result.success
    assert enemy.hp == 3
    # status range_attacker nadany
    assert any(getattr(s, "id", s) == "range_attacker" for s in hero.statuses)


def test_longbow_miss_shows_blocking_result_prompt(monkeypatch):
    hero = Hero((0, 0))
    hero.name = "Cedric"
    enemy = Enemy((2, 0), hp=8, ac=20)
    enemy.name = "Bandit Bruiser"
    game = FakeGame()
    game.ui = FakeUI()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position

    monkeypatch.setattr(base_attack_range_event, "prompt_for_roll", lambda *_, **__: 2)

    result = dispatch_event("longbow", _ctx(game, hero))

    assert result.success
    assert result.data["hit"] is False
    assert enemy.hp == 8
    assert game.ui.info_calls
    prompt = game.ui.info_calls[-1]
    assert prompt["title"] == "Wynik ataku: Cedric"
    assert "Cedric nie trafia celu Bandit Bruiser" in prompt["prompt_long"]
    assert "Wynik ataku" in prompt["prompt_long"]


def test_longbow_blocked_by_wall(monkeypatch):
    hero = Hero((0, 0))
    enemy = Enemy((2, 0))
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.board.blocked_edges.add(frozenset(((0, 0), (1, 0))))

    result = dispatch_event("longbow", _ctx(game, hero))
    assert not result.success
    assert "zasięgu" in (result.message or "") or "linia" in (result.message or "")
    assert enemy.hp == 12


def test_cover_and_range_penalty_emitted(monkeypatch):
    class ShortBow(base_attack_range_event.BaseRangeAttackEvent):
        name = "attack_short_test"
        range_increment_ft = 5
        max_range_increments = 6
        action_id_base = "attack_short_test"

    hero = Hero((0, 0))
    enemy = Enemy((6, 0), ac=12)
    obstacle = SimpleObstacle()
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy, (1, 0): obstacle}
    game.conn.choice = enemy.position

    rolls = iter([30, 4])  # attack (>= target AC) after auto penalties, dmg
    monkeypatch.setattr(base_attack_range_event, "prompt_for_roll", lambda *_, **__: next(rolls))

    event = ShortBow()
    result = event.run(_ctx(game, hero))
    assert result.success
    emitted = next(payload for payload in game.events.emitted if payload.get("action_id") == "attack_short_test")
    assert emitted.get("cover") == "greater"
    assert emitted.get("range_penalty") == 10  # 6 increment -> (6-1)*2
    assert enemy.hp == 8


def test_roll_only_forced_target_skips_analysis_prompt(monkeypatch):
    hero = Hero((0, 0))
    enemy = Enemy((2, 0), hp=8, ac=10)
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.ui = FakeUI()

    rolls = iter([15, 5])
    monkeypatch.setattr(base_attack_range_event, "prompt_for_roll", lambda *_, **__: next(rolls))

    result = dispatch_event(
        "longbow",
        EventContext(
            game=game,
            actor=hero,
            metadata={
                "forced_target": enemy,
                "forced_target_pos": enemy.position,
                "roll_only": True,
            },
        ),
    )

    assert result.success is True
    assert not any(call["title"] == "Atak dystansowy: analiza strzału" for call in game.ui.info_calls)


def test_ranged_attack_triggers_projectile_led_animation(monkeypatch):
    hero = Hero((0, 0))
    enemy = Enemy((2, 0), hp=8, ac=10)
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position

    rolls = iter([15, 5])
    monkeypatch.setattr(base_attack_range_event, "prompt_for_roll", lambda *_, **__: next(rolls))
    calls = []
    monkeypatch.setattr(
        base_attack_range_event,
        "animate_projectile_line",
        lambda conn, start, end, **_kwargs: calls.append((start, end)) or True,
    )

    result = dispatch_event("longbow", _ctx(game, hero))

    assert result.success
    assert calls == [((0, 0), (2, 0))]


def test_analyze_shot_uses_pf2e_grid_distance_for_diagonal_range():
    shooter = Hero((0, 0))
    target = Enemy((6, 6), ac=12)
    game = FakeGame()
    game.heroes = [shooter]
    game.enemies = [target]
    game.board.occupants = {
        shooter.position: shooter,
        target.position: target,
    }

    event = attack_range_long_bow.LongBowAttackEvent()
    analyzed = event._analyze_shot(game, shooter.position, target.position, target=target)

    assert analyzed.get("distance_ft") == 45
    assert analyzed.get("increments") == 1
    assert analyzed.get("range_penalty") == 0


def test_ranged_attack_prompts_targeting_legend_and_shot_analysis(monkeypatch):
    class ShortBow(base_attack_range_event.BaseRangeAttackEvent):
        name = "attack_short_prompt_test"
        range_increment_ft = 5
        max_range_increments = 6
        action_id_base = "attack_short_prompt_test"

    hero = Hero((0, 0))
    enemy = Enemy((6, 0), ac=12)
    obstacle = SimpleObstacle()
    game = FakeGame()
    game.ui = FakeUI()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy, (1, 0): obstacle}
    game.conn.choice = enemy.position

    rolls = iter([30, 4])
    monkeypatch.setattr(base_attack_range_event, "prompt_for_roll", lambda *_, **__: next(rolls))

    result = ShortBow().run(_ctx(game, hero))

    assert result.success
    titles = [call["title"] for call in game.ui.info_calls]
    assert "Atak dystansowy: wybór celu" in titles
    legend_prompt = next(call["prompt_long"] for call in game.ui.info_calls if call["title"] == "Atak dystansowy: wybór celu")
    assert "legalne cele" in str(legend_prompt or "").lower()
    assert "minor cover" in str(legend_prompt or "").lower()
    assert "turkusowe pola" in str(legend_prompt or "").lower()
    assert "standard cover" in str(legend_prompt or "").lower()
    choice_titles = [call["title"] for call in game.ui.choice_calls]
    assert "Atak dystansowy: analiza strzału" in choice_titles
    analysis_prompt = next(call["prompt_long"] for call in game.ui.choice_calls if call["title"] == "Atak dystansowy: analiza strzału")
    assert "kara za zasięg" in str(analysis_prompt or "").lower()
    assert "typ osłony" in str(analysis_prompt or "").lower()


def test_ranged_attack_targeting_hint_is_non_blocking_during_board_scan(monkeypatch):
    class ShortBow(base_attack_range_event.BaseRangeAttackEvent):
        name = "attack_short_idle_hint_test"
        range_increment_ft = 5
        max_range_increments = 6
        action_id_base = "attack_short_idle_hint_test"

    hero = Hero((0, 0))
    enemy = Enemy((6, 0), ac=12)
    game = FakeGame()
    game.ui = FakeUI()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position
    idle_calls = []
    game.ui_idle_hint = lambda title, text=None: idle_calls.append({"title": title, "text": text})

    rolls = iter([30, 4])
    monkeypatch.setattr(base_attack_range_event, "prompt_for_roll", lambda *_, **__: next(rolls))

    result = ShortBow().run(_ctx(game, hero))

    assert result.success
    assert idle_calls and idle_calls[0]["title"] == "Atak dystansowy: wybór celu"
    assert "kliknij pole celu" in str(idle_calls[0]["text"] or "").lower()
    assert "Atak dystansowy: wybór celu" not in [call["title"] for call in game.ui.info_calls]


def test_ranged_attack_focuses_leds_on_selected_target_before_confirmation(monkeypatch):
    hero = Hero((0, 0))
    enemy_a = Enemy((2, 0), hp=8, ac=10)
    enemy_b = Enemy((3, 0), hp=8, ac=10)
    game = FakeGame()
    game.ui = FakeUI()
    game.heroes = [hero]
    game.enemies = [enemy_a, enemy_b]
    game.board.occupants = {
        hero.position: hero,
        enemy_a.position: enemy_a,
        enemy_b.position: enemy_b,
    }
    game.conn.choice = enemy_b.position

    rolls = iter([15, 5])
    monkeypatch.setattr(base_attack_range_event, "prompt_for_roll", lambda *_, **__: next(rolls))

    result = dispatch_event("longbow", _ctx(game, hero))

    assert result.success is True
    assert len(game.conn.led_calls) >= 2
    focused_led_calls = []
    for call in game.conn.led_calls:
        positions = list(call[0][0])
        colors = list(call[0][1])
        target_color_count = sum(1 for color in colors if color == base_attack_range_event.BaseRangeAttackEvent.TARGET_LED)
        if enemy_b.position in positions and target_color_count == 1:
            focused_led_calls.append((positions, colors))
    assert focused_led_calls
    assert game.conn.leds_off_calls >= 2


def test_ranged_attack_analysis_can_retarget_before_roll(monkeypatch):
    hero = Hero((0, 0))
    enemy_a = Enemy((2, 0), hp=8, ac=10)
    enemy_b = Enemy((3, 0), hp=8, ac=10)
    game = FakeGame()
    game.ui = FakeUI()
    game.ui.choice_answers = ["Wybierz inny cel", "Potwierdź strzał"]
    game.heroes = [hero]
    game.enemies = [enemy_a, enemy_b]
    game.board.occupants = {
        hero.position: hero,
        enemy_a.position: enemy_a,
        enemy_b.position: enemy_b,
    }
    game.conn.choice = [enemy_a.position, enemy_b.position]

    rolls = iter([15, 5])
    monkeypatch.setattr(base_attack_range_event, "prompt_for_roll", lambda *_, **__: next(rolls))

    result = dispatch_event("longbow", _ctx(game, hero))

    assert result.success is True
    assert (result.data or {}).get("target") is enemy_b
    assert enemy_a.hp == 8
    assert enemy_b.hp < 8
    assert [call["title"] for call in game.ui.choice_calls].count("Atak dystansowy: analiza strzału") == 2


def test_ranged_attack_minor_cover_led_differs_from_move_green(monkeypatch):
    assert base_attack_range_event.BaseRangeAttackEvent.COVER_LED["minor"] == [0, 150, 150]
    assert base_attack_range_event.BaseRangeAttackEvent.COVER_LED["minor"] != consts.MOVE_FIELD_RGB


def test_ranged_attack_in_exploration_adds_ambush_off_guard_note(monkeypatch):
    hero = Hero((0, 0))
    enemy = Enemy((2, 0), hp=8, ac=10)
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position

    prompts: list[str] = []
    rolls = iter([15, 5])

    def _prompt(*args, **kwargs):
        prompts.append("\n".join(filter(None, [str(args[0]) if args else "", str(kwargs.get("prompt_long") or "")])))
        return next(rolls)

    monkeypatch.setattr(base_attack_range_event, "prompt_for_roll", _prompt)

    result = dispatch_event("longbow", _ctx(game, hero))

    assert result.success
    assert any("Atak z zaskoczenia" in prompt for prompt in prompts)


def test_longbow_wrong_square_against_undetected_target_still_counts_as_attack():
    hero = Hero((0, 0))
    enemy = Enemy((2, 0), hp=8, ac=10)
    enemy.statuses.append(types.SimpleNamespace(id="undetected"))
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = (1, 1)

    result = dispatch_event("longbow", _ctx(game, hero))

    assert result.success is True
    assert bool((result.data or {}).get("hit", True)) is False
    assert (result.data or {}).get("target") is None
    assert (result.data or {}).get("guessed_target_square") == (1, 1)
    assert enemy.hp == 8
    assert getattr(hero, "_attack_trait_state", {}).get("attacks_this_turn") == 1
    assert any(getattr(s, "id", s) == "range_attacker" for s in hero.statuses)


def test_analyze_shot_raised_tower_shield_in_line_grants_standard_cover():
    shooter = Hero((0, 0))
    blocker = Hero((1, 0))
    target = Enemy((2, 0), ac=12)
    tower = create_shield("tower_shield")
    assert tower is not None
    blocker.equipped_shield = tower
    blocker.bonuses.append(
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=2,
            tag="ac",
            source="raise_shield:round1",
            label="tarcza w gorze",
        )
    )
    game = FakeGame()
    game.heroes = [shooter, blocker]
    game.enemies = [target]
    game.board.occupants = {
        shooter.position: shooter,
        blocker.position: blocker,
        target.position: target,
    }

    event = attack_range_long_bow.LongBowAttackEvent()
    analyzed = event._analyze_shot(game, shooter.position, target.position, target=target)

    assert analyzed.get("cover_type") == "standard"
    assert analyzed.get("blocked") is False


def test_analyze_shot_tower_shield_without_raise_does_not_grant_cover():
    shooter = Hero((0, 0))
    blocker = Hero((1, 0))
    target = Enemy((2, 0), ac=12)
    tower = create_shield("tower_shield")
    assert tower is not None
    blocker.equipped_shield = tower
    game = FakeGame()
    game.heroes = [shooter, blocker]
    game.enemies = [target]
    game.board.occupants = {
        shooter.position: shooter,
        blocker.position: blocker,
        target.position: target,
    }

    event = attack_range_long_bow.LongBowAttackEvent()
    analyzed = event._analyze_shot(game, shooter.position, target.position, target=target)

    assert analyzed.get("cover_type") == "none"
