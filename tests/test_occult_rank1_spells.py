from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from GameObjects.events.base import EventContext
from GameObjects.events.magic import occult_rank1_event as occ1


class DummyConn:
    def set_leds(self, _positions, _colors):
        return None

    def scan_board(self, _positions):
        return None

    def leds_off(self):
        return None


class DummyBoard:
    def __init__(self, rows=8, cols=8, interactables=None):
        self.rows = rows
        self.cols = cols
        self._interactables = dict(interactables or {})

    def interactables_at(self, pos):
        return list(self._interactables.get(pos, []))

    def in_bounds(self, pos):
        x, y = pos
        return 0 <= x < self.cols and 0 <= y < self.rows

    def get_neighbors(self, pos, include_position=False, diagonal=True):
        x, y = pos
        out = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                if not diagonal and abs(dx) + abs(dy) != 1:
                    continue
                cand = (x + dx, y + dy)
                if self.in_bounds(cand):
                    out.append(cand)
        if include_position:
            out.append(pos)
        return out

    def can_traverse(self, src, dst, allow_occupied=False):
        return self.in_bounds(src) and self.in_bounds(dst)

    def can_enter(self, pos, allow_occupied=False):
        return self.in_bounds(pos)

    def move(self, source, target):
        return None


class DummyActor:
    def __init__(self, name="actor", position=(0, 0), hp=20, object_id=None):
        self.name = name
        self.object_id = object_id or name
        self.position = position
        self.hp = hp
        self.wounds = 0
        self.statuses = []
        self.bonuses = []

    def __hash__(self):
        return hash(self.object_id)

    def add_status(self, status):
        self.statuses.append(status)
        return True

    def remove_status(self, status):
        sid = getattr(status, "id", status)
        for i, item in enumerate(list(self.statuses)):
            if getattr(item, "id", item) == sid:
                del self.statuses[i]
                return True
        return False

    def has_status(self, status):
        sid = getattr(status, "id", status)
        return any(getattr(s, "id", s) == sid for s in self.statuses)

    def add_bonus(self, effect):
        self.bonuses.append(effect)

    def remove_bonuses_with_prefix(self, prefix):
        self.bonuses = [b for b in self.bonuses if not (getattr(b, "source", "") or "").startswith(prefix)]

    def apply_damage(self, amount, _damage_type="normal"):
        self.hp -= int(amount)
        self.wounds += int(amount)
        return self.hp, self.hp <= 0

    def heal(self, amount):
        self.hp += int(amount)
        self.wounds = max(0, self.wounds - int(amount))
        return self.hp


class DummyInteractable:
    def __init__(self):
        self.locked = False
        self.is_open = True
        self.jammed = True
        self.thievery_dc = 15


def _game(*, actor, enemies=None, heroes=None, board=None):
    logs = []
    game = SimpleNamespace(
        board=board or DummyBoard(),
        conn=DummyConn(),
        heroes=list(heroes if heroes is not None else [actor]),
        enemies=list(enemies or []),
        ui=SimpleNamespace(prompt_choice=lambda *a, **k: None, enabled=False, allow_cli_fallback=False),
        ui_log=lambda msg: logs.append(str(msg)),
        _logs=logs,
    )
    actor.game = game
    for h in game.heroes:
        h.game = game
    for e in game.enemies:
        e.game = game
    return game


def test_bless_and_bane_apply_expected_bonuses():
    caster = DummyActor("caster", (0, 0))
    ally = DummyActor("ally", (1, 0))
    enemy = DummyActor("enemy", (1, 1))
    game = _game(actor=caster, heroes=[caster, ally], enemies=[enemy])

    bless = occ1.BlessEvent().execute(EventContext(game=game, actor=caster))
    bane = occ1.BaneEvent().execute(EventContext(game=game, actor=caster))

    assert bless.success is True
    assert bane.success is True
    assert any((getattr(b, "source", "") or "").startswith("bless:") for b in ally.bonuses)
    assert any((getattr(b, "source", "") or "").startswith("bane:") for b in enemy.bonuses)


def test_lock_spell_locks_target(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    chest = DummyInteractable()
    board = DummyBoard(interactables={(1, 0): [chest]})
    game = _game(actor=caster, board=board)

    monkeypatch.setattr(occ1, "pick_target_in_range", lambda *_a, **_k: (chest, (1, 0)))

    result = occ1.LockSpellEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert chest.locked is True
    assert chest.is_open is False
    assert chest.jammed is False
    assert chest.thievery_dc == 17


def test_sleep_targets_low_hp_enemies(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    low = DummyActor("low", (1, 0), hp=3)
    high = DummyActor("high", (1, 1), hp=8)
    game = _game(actor=caster, enemies=[low, high])

    monkeypatch.setattr(occ1, "pick_position_in_range", lambda *_a, **_k: (1, 0))
    monkeypatch.setattr(occ1, "prompt_for_roll", lambda *_a, **_k: 5)

    result = occ1.SleepEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert low.has_status("sleep")
    assert low.has_status("prone")
    assert not high.has_status("sleep")


def test_command_prone_applies_prone(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    enemy = DummyActor("enemy", (1, 0), hp=15)
    game = _game(actor=caster, enemies=[enemy])

    monkeypatch.setattr(occ1, "pick_target_in_range", lambda *_a, **_k: (enemy, enemy.position))
    monkeypatch.setattr(occ1, "prompt_for_roll", lambda *_a, **_k: 15)
    monkeypatch.setattr(occ1.random, "randint", lambda _a, _b: 1)
    monkeypatch.setattr(occ1, "_prompt_choice", lambda *_a, **_k: "prone")

    result = occ1.CommandEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert enemy.has_status("prone")


def test_alarm_triggers_on_enemy_enter(monkeypatch):
    caster = DummyActor("caster", (0, 0), object_id="caster-id")
    enemy = DummyActor("enemy", (5, 5), object_id="enemy-id")
    game = _game(actor=caster, enemies=[enemy])

    monkeypatch.setattr(occ1, "pick_position_in_range", lambda *_a, **_k: (2, 2))

    placed = occ1.AlarmEvent().execute(EventContext(game=game, actor=caster))
    assert placed.success is True

    from GameObjects.events.magic.runtime_effects import process_alarm_wards_for_move

    messages = process_alarm_wards_for_move(game, enemy, (2, 2))

    assert messages
    assert "Alarm" in messages[0]
