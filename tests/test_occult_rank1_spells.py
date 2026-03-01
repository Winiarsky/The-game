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
from GameObjects.events.magic.level_1st import events as occ1
from GameObjects.events.magic.spell_types import SpellTradition


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


def test_rank1_arcane_tradition_added_for_shared_spells():
    events = [
        occ1.AlarmEvent(),
        occ1.CharmEvent(),
        occ1.ColorSprayEvent(),
        occ1.CommandEvent(),
        occ1.FearEvent(),
        occ1.FloatingDiskEvent(),
        occ1.GrimTendrilsEvent(),
        occ1.IllusoryDisguiseEvent(),
        occ1.IllusoryObjectEvent(),
        occ1.ItemFacadeEvent(),
        occ1.LockSpellEvent(),
        occ1.MageArmorEvent(),
        occ1.MagicAuraEvent(),
        occ1.MagicWeaponEvent(),
        occ1.MendingEvent(),
        occ1.RayOfEnfeeblementEvent(),
        occ1.SleepEvent(),
        occ1.TrueStrikeEvent(),
        occ1.UnseenServantEvent(),
        occ1.VentriloquismEvent(),
    ]
    for event in events:
        assert SpellTradition.ARCANA in tuple(getattr(event, "magic_traditions", ()) or ())


def test_magic_missile_spends_actions_by_missiles(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    enemy = DummyActor("enemy", (1, 0), hp=20)
    game = _game(actor=caster, enemies=[enemy])

    monkeypatch.setattr(occ1, "_prompt_choice", lambda *_a, **_k: "2")
    monkeypatch.setattr(occ1, "pick_target_in_range", lambda *_a, **_k: (enemy, enemy.position))
    damage_rolls = iter([3, 4])
    monkeypatch.setattr(occ1, "prompt_for_roll", lambda *_a, **_k: next(damage_rolls))

    result = occ1.MagicMissileEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert result.actions_spent == 2
    assert enemy.hp == 13


def test_burning_hands_hits_targets_in_cone(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    e1 = DummyActor("e1", (1, 0), hp=20)
    e2 = DummyActor("e2", (2, 0), hp=20)
    game = _game(actor=caster, enemies=[e1, e2])

    monkeypatch.setattr(occ1, "_prompt_choice", lambda *_a, **_k: "E")
    rolls = iter([15, 6])  # DC, damage
    monkeypatch.setattr(occ1, "prompt_for_roll", lambda *_a, **_k: next(rolls))
    monkeypatch.setattr(occ1.random, "randint", lambda _a, _b: 5)  # failure

    result = occ1.BurningHandsEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert e1.hp == 8
    assert e2.hp == 8


def test_hydraulic_push_deals_damage_and_pushes(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    enemy = DummyActor("enemy", (1, 0), hp=20)
    game = _game(actor=caster, enemies=[enemy])

    monkeypatch.setattr("GameObjects.events.magic.base_attack_magic_event.pick_target_in_range", lambda *_a, **_k: (enemy, enemy.position))
    monkeypatch.setattr("GameObjects.events.magic.base_attack_magic_event.prompt_for_roll", lambda *_a, **_k: 20)
    monkeypatch.setattr(occ1, "prompt_for_roll", lambda *_a, **_k: 5)

    result = occ1.HydraulicPushEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert enemy.hp == 10
    assert "Odepchniecie" in (result.message or "")


def test_grease_surface_prones_enemy_and_creates_zone(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    enemy = DummyActor("enemy", (1, 0), hp=20)
    game = _game(actor=caster, enemies=[enemy])

    choices = iter(["surface"])
    monkeypatch.setattr(occ1, "_prompt_choice", lambda *_a, **_k: next(choices))
    monkeypatch.setattr(occ1, "pick_position_in_range", lambda *_a, **_k: (1, 0))
    monkeypatch.setattr(occ1, "prompt_for_roll", lambda *_a, **_k: 15)
    monkeypatch.setattr(occ1.random, "randint", lambda _a, _b: 5)

    result = occ1.GreaseEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert enemy.has_status("prone")
    assert game._arcane_runtime["grease_zones"]


def test_longstrider_adds_speed_bonus(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    ally = DummyActor("ally", (1, 0))
    game = _game(actor=caster, heroes=[caster, ally])

    monkeypatch.setattr(occ1, "pick_target_in_range", lambda *_a, **_k: (ally, ally.position))
    result = occ1.LongstriderEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert any(getattr(s, "id", "") == "speed_bonus" for s in ally.statuses)


def test_air_bubble_reaction_style(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    ally = DummyActor("ally", (1, 0))
    game = _game(actor=caster, heroes=[caster, ally])

    monkeypatch.setattr(occ1, "pick_target_in_range", lambda *_a, **_k: (ally, ally.position))
    result = occ1.AirBubbleEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert result.consumed_action is False
    assert ally.has_status("air_bubble")


def test_shocking_grasp_critical_damage(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    enemy = DummyActor("enemy", (1, 0), hp=20)
    game = _game(actor=caster, enemies=[enemy])

    monkeypatch.setattr("GameObjects.events.magic.base_attack_magic_event.pick_target_in_range", lambda *_a, **_k: (enemy, enemy.position))
    monkeypatch.setattr("GameObjects.events.magic.base_attack_magic_event.prompt_for_roll", lambda *_a, **_k: 30)
    choices = iter(["nie"])
    monkeypatch.setattr(occ1, "_prompt_choice", lambda *_a, **_k: next(choices))
    monkeypatch.setattr(occ1, "prompt_for_roll", lambda *_a, **_k: 4)

    result = occ1.ShockingGraspEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert enemy.hp == 12


def test_goblin_pox_applies_poisoned_on_failure(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    enemy = DummyActor("enemy", (1, 0), hp=20)
    game = _game(actor=caster, enemies=[enemy])

    monkeypatch.setattr(occ1, "pick_target_in_range", lambda *_a, **_k: (enemy, enemy.position))
    rolls = iter([15, 6])  # dc, dmg
    monkeypatch.setattr(occ1, "prompt_for_roll", lambda *_a, **_k: next(rolls))
    monkeypatch.setattr(occ1.random, "randint", lambda _a, _b: 5)  # failure

    result = occ1.GoblinPoxEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert enemy.hp == 8
    assert enemy.has_status("poisoned")


def test_summon_animal_and_construct_add_status():
    caster = DummyActor("caster", (0, 0))
    game = _game(actor=caster, heroes=[caster], enemies=[])

    res_animal = occ1.SummonAnimalEvent().execute(EventContext(game=game, actor=caster))
    res_construct = occ1.SummonConstructEvent().execute(EventContext(game=game, actor=caster))

    assert res_animal.success is True
    assert res_construct.success is True
    assert caster.has_status("summon_animal")
    assert caster.has_status("summon_construct")


def test_pest_form_sets_form_status(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    game = _game(actor=caster, heroes=[caster], enemies=[])

    monkeypatch.setattr(occ1, "_prompt_choice", lambda *_a, **_k: "rat")
    result = occ1.PestFormEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    status = [s for s in caster.statuses if getattr(s, "id", "") == "pest_form"]
    assert status and status[0].data.get("form") == "rat"
