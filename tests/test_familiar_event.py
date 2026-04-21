import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.events.base import EventContext
from GameObjects.events.command_familiar_event import CommandFamiliarEvent
from GameObjects.events.enemy.basic_enemy_melee_attack_event import BasicEnemyMeleeAttackEvent
from GameObjects.events.magic.base_attack_magic_event import BaseMagicAttackEvent
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources_from_roll
from GameObjects.Enemies.basic_enemy import BasicEnemy
from hero import Hero
from skills import Skill
from statuses.base import Status


class DummyUI:
    def __init__(self, answers):
        self.answers = list(answers)
        self.last_choices = None
        self.enabled = True

    def prompt_choice(self, _prompt: str, choices=None, **_kwargs):
        self.last_choices = list(choices or [])
        if self.answers:
            return self.answers.pop(0)
        return None


class DummyConn:
    def __init__(self, scan_return=None, read_return="ACCEPT"):
        self.scan_return = scan_return
        self.read_return = read_return
        self.last_prompt = None

    def set_leds(self, *_args, **_kwargs):
        return None

    def leds_off(self, *_args, **_kwargs):
        return None

    def scan_board(self, *_args, **_kwargs):
        return self.scan_return

    def read_card(self, prompt, *_args, **_kwargs):
        self.last_prompt = prompt
        return self.read_return


class DummyGame:
    def __init__(self):
        self.conn = DummyConn()
        self.ui = None
        self.events = type("E", (), {"safe_emit_action": lambda *_a, **_k: None})()
        self.heroes = []
        self.enemies = []
        self.board = None
        self.logs = []

    def ui_log(self, msg: str):
        self.logs.append(msg)


class DummyBoard:
    def __init__(self, hero_pos, enemy_pos=None, enemy=None, interactables=None):
        self.hero_pos = hero_pos
        self.enemy_pos = enemy_pos
        self.enemy = enemy
        self._interactables = interactables or {}

    def get_neighbors(self, pos, include_position=False, diagonal=True):
        return [self.hero_pos] if self.hero_pos else []

    def occupant_at(self, pos):
        if pos == self.hero_pos:
            return self.hero
        if pos == self.enemy_pos:
            return self.enemy
        return None

    def in_bounds(self, _pos):
        return True

    def interactables_at(self, pos):
        return list(self._interactables.get(pos, []))


class HiddenObj:
    def __init__(self, hidden=True, revealed=False, seekable=True):
        self.hidden = hidden
        self.revealed = revealed
        self.seekable = seekable


def _make_familiar_owner_status():
    return Status(
        id="FamiliarOwner",
        label="Familiar Owner",
        data={
            "ui_description": "Posiadasz familiara.",
            "familiar_mode": None,
            "familiar_guidance_skill": None,
        },
    )


def test_familiar_setup_scout_choice():
    from game import Game

    game = Game(conn=DummyConn(), scenario="test_chameleon_gnome")
    ui = DummyUI(["Scout (Perception)"])
    game.ui = ui

    hero = Hero()
    hero.add_status(_make_familiar_owner_status())

    start_state = game.state
    start_state._maybe_prompt_familiar_owner(hero)

    assert ui.last_choices is not None
    assert "Scout (Perception)" in ui.last_choices
    assert hero.get_status_data("FamiliarOwner", "familiar_mode") == "scout"


def test_familiar_setup_guidance_choice_and_skill():
    from game import Game

    game = Game(conn=DummyConn(), scenario="test_chameleon_gnome")
    ui = DummyUI(["Guidance (Skill)", Skill.STEALTH.value])
    game.ui = ui

    hero = Hero()
    hero.add_status(_make_familiar_owner_status())

    start_state = game.state
    start_state._maybe_prompt_familiar_owner(hero)

    assert hero.get_status_data("FamiliarOwner", "familiar_mode") == "guidance"
    assert hero.get_status_data("FamiliarOwner", "familiar_guidance_skill") == Skill.STEALTH.value


def test_command_familiar_scout_adds_and_consumes():
    game = DummyGame()
    hero = Hero()
    hero.set_position((0, 0))
    hero.add_status(_make_familiar_owner_status())
    hero.get_status("FamiliarOwner").data["familiar_mode"] = "scout"
    game.heroes = [hero]
    board = DummyBoard(hero.position)
    board.hero = hero
    game.board = board

    ctx = EventContext(game=game, actor=hero)
    result = CommandFamiliarEvent().execute(ctx)
    assert result.success
    assert hero.has_status("familiar_scout")

    resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.PERCEPTION.value,
        dc=10,
        actor=hero,
        tags=[Skill.PERCEPTION.value],
        roll=10,
        apply_modifiers=True,
    )
    assert not hero.has_status("familiar_scout")


def test_command_familiar_guidance_adds_and_consumes():
    game = DummyGame()
    hero = Hero()
    hero.set_position((0, 0))
    hero.add_status(_make_familiar_owner_status())
    status = hero.get_status("FamiliarOwner")
    status.data["familiar_mode"] = "guidance"
    status.data["familiar_guidance_skill"] = Skill.STEALTH.value
    game.heroes = [hero]
    board = DummyBoard(hero.position)
    board.hero = hero
    game.board = board

    ctx = EventContext(game=game, actor=hero)
    result = CommandFamiliarEvent().execute(ctx)
    assert result.success
    assert hero.has_status(f"familiar_guidance_{Skill.STEALTH.value}")

    resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.STEALTH.value,
        dc=10,
        actor=hero,
        tags=[Skill.STEALTH.value],
        roll=10,
        apply_modifiers=True,
    )
    assert not hero.has_status(f"familiar_guidance_{Skill.STEALTH.value}")


def test_command_familiar_distract_applies_penalty_and_consumes(monkeypatch):
    game = DummyGame()
    hero = Hero()
    hero.set_position((0, 0))
    enemy = BasicEnemy()
    enemy.position = (0, 1)
    game.heroes = [hero]
    game.enemies = [enemy]

    conn = DummyConn(scan_return=hero.position, read_return="ACCEPT")
    game.conn = conn

    board = DummyBoard(hero.position, enemy.position, enemy=enemy)
    board.hero = hero
    game.board = board

    hero.add_status(_make_familiar_owner_status())
    hero.get_status("FamiliarOwner").data["familiar_mode"] = "distract"

    ctx = EventContext(game=game, actor=hero)
    result = CommandFamiliarEvent().execute(ctx)
    assert result.success
    assert enemy.has_status("familiar_distract")

    monkeypatch.setattr("GameObjects.events.enemy.basic_enemy_melee_attack_event.random.randint", lambda *_a, **_k: 10)
    BasicEnemyMeleeAttackEvent().execute(EventContext(game=game, actor=enemy))
    assert conn.last_prompt is not None
    assert "wynik końcowy" in conn.last_prompt.lower()
    assert "9" in conn.last_prompt
    assert not enemy.has_status("familiar_distract")


def test_command_familiar_touch_delivery_extends_range_and_consumes(monkeypatch):
    class DummyTouchSpell(BaseMagicAttackEvent):
        name = "dummy_touch"
        range_feet = 5

        def _resolve_on_target(self, target, pos, ctx, *, critical=False):
            return EventResult(success=True, consumed_action=self.consumes_action)

    from GameObjects.events.base import EventResult
    import GameObjects.events.magic.base_attack_magic_event as base_magic

    game = DummyGame()
    hero = Hero()
    hero.set_position((0, 0))
    enemy = BasicEnemy()
    enemy.position = (0, 2)  # 10 ft
    game.heroes = [hero]
    game.enemies = [enemy]
    game.conn = DummyConn(scan_return=enemy.position)

    class MagicBoard:
        def occupant_at(self, pos):
            if pos == enemy.position:
                return enemy
            if pos == hero.position:
                return hero
            return None

    game.board = MagicBoard()

    hero.add_status(_make_familiar_owner_status())
    hero.get_status("FamiliarOwner").data["familiar_mode"] = "deliver_touch"

    ctx = EventContext(game=game, actor=hero)
    CommandFamiliarEvent().execute(ctx)
    assert hero.has_status("familiar_touch_delivery")

    monkeypatch.setattr(base_magic, "prompt_for_roll", lambda *_a, **_k: 20)
    res = DummyTouchSpell().execute(ctx)
    assert res.success
    assert not hero.has_status("familiar_touch_delivery")


def test_command_familiar_scent_seek_hint():
    game = DummyGame()
    hero = Hero()
    hero.set_position((0, 0))
    game.heroes = [hero]

    hidden = HiddenObj(hidden=True, revealed=False, seekable=True)
    board = DummyBoard(hero.position, interactables={(1, 1): [hidden]})
    board.hero = hero
    game.board = board

    hero.add_status(_make_familiar_owner_status())
    hero.get_status("FamiliarOwner").data["familiar_mode"] = "scent_seek"

    ctx = EventContext(game=game, actor=hero)
    result = CommandFamiliarEvent().execute(ctx)
    assert result.success
    assert result.message and "wyczuwa" in result.message


def test_command_familiar_prompts_mode_on_first_use_and_persists_choice():
    game = DummyGame()
    ui = DummyUI(["Distract (Enemy)"])
    game.ui = ui

    hero = Hero()
    hero.set_position((0, 0))
    enemy = BasicEnemy()
    enemy.position = (0, 1)

    game.heroes = [hero]
    game.enemies = [enemy]
    board = DummyBoard(hero.position, enemy.position, enemy=enemy)
    board.hero = hero
    game.board = board

    hero.add_status(_make_familiar_owner_status())
    assert hero.get_status_data("FamiliarOwner", "familiar_mode") is None

    ctx = EventContext(game=game, actor=hero)
    result = CommandFamiliarEvent().execute(ctx)

    assert result.success
    assert hero.get_status_data("FamiliarOwner", "familiar_mode") == "distract"
    assert enemy.has_status("familiar_distract")
    assert ui.last_choices is not None
    assert "Distract (Enemy)" in ui.last_choices
