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
from GameObjects.events.magic import occult_cantrips_event as occ
from GameObjects.events.magic.lighting_effects import is_position_in_light_aura
from GameObjects.interactions_mixin.skill_check_resolver import compute_skill_modifier_with_sources
from GameObjects.NPC.base_npc import BaseNPC
from skills import Skill
from states.combat import Combat
from statuses import InDarkStatus, Status, StunnedStatus, apply_shield_cantrip_absorb


class DummyConn:
    def __init__(self, scans=None):
        self.scans = list(scans or [])
        self.last_led_positions = None

    def set_leds(self, positions, _colors):
        self.last_led_positions = list(positions)

    def scan_board(self, _positions):
        if self.scans:
            return self.scans.pop(0)
        return None

    def leds_off(self):
        return None


class DummyBoard:
    def __init__(self, rows=8, cols=8, terrain_map=None, interactables=None):
        self.rows = rows
        self.cols = cols
        self._terrain_map = dict(terrain_map or {})
        self._interactables = dict(interactables or {})

    def in_bounds(self, pos):
        x, y = pos
        return 0 <= x < self.cols and 0 <= y < self.rows

    def cell_at(self, pos):
        name = self._terrain_map.get(pos, "basic")
        return SimpleNamespace(field=SimpleNamespace(name=name))

    def interactables_at(self, pos):
        return list(self._interactables.get(pos, []))


class DummyActor:
    def __init__(self, name="actor", position=(0, 0), hp=30, object_id=None):
        self.name = name
        self.object_id = object_id or name
        self.position = position
        self.hp = hp
        self.statuses = []
        self.bonuses = []

    def __hash__(self):
        return hash(self.object_id)

    def has_status(self, status):
        sid = getattr(status, "id", status)
        return any(getattr(s, "id", s) == sid for s in self.statuses)

    def add_status(self, status):
        self.statuses.append(status)
        return True

    def remove_status(self, status):
        sid = getattr(status, "id", status)
        for idx, item in enumerate(list(self.statuses)):
            if getattr(item, "id", item) == sid:
                del self.statuses[idx]
                return True
        return False

    def add_bonus(self, effect):
        self.bonuses.append(effect)

    def remove_bonuses_with_prefix(self, prefix):
        kept = [b for b in self.bonuses if not (getattr(b, "source", "") or "").startswith(prefix)]
        removed = len(self.bonuses) - len(kept)
        self.bonuses = kept
        return removed

    def apply_damage(self, amount, _damage_type="normal"):
        effective, _absorbed, _broken = apply_shield_cantrip_absorb(self, int(amount))
        self.hp -= int(effective)
        return self.hp, self.hp <= 0


def _game(*, actor, enemies=None, heroes=None, board=None, conn=None):
    logs = []
    game = SimpleNamespace(
        board=board or DummyBoard(),
        conn=conn or DummyConn(),
        heroes=list(heroes if heroes is not None else [actor]),
        enemies=list(enemies or []),
        ui_log=lambda msg: logs.append(str(msg)),
        ui_event=lambda *_a, **_k: None,
        ui=SimpleNamespace(prompt_choice=lambda *a, **k: None, enabled=False),
        state=SimpleNamespace(__class__=type("Exploration", (), {})),
        _logs=logs,
    )
    actor.game = game
    for h in game.heroes:
        h.game = game
    for e in game.enemies:
        e.game = game
    return game


def test_chill_touch_failure_applies_enfeebled(monkeypatch):
    hero = DummyActor("hero", (0, 0))
    enemy = DummyActor("enemy", (1, 0), hp=20)
    game = _game(actor=hero, enemies=[enemy])

    monkeypatch.setattr(occ, "pick_target_in_range", lambda *_a, **_k: (enemy, enemy.position))
    rolls = iter([15, 4])  # spell DC, damage
    monkeypatch.setattr(occ, "prompt_for_roll", lambda *_a, **_k: next(rolls))
    monkeypatch.setattr(occ.random, "randint", lambda _a, _b: 8)  # failure vs DC 15

    res = occ.ChillTouchEvent().execute(EventContext(game=game, actor=hero))

    assert res.success is True
    assert enemy.hp == 16
    enfeebled = [s for s in enemy.statuses if getattr(s, "id", "") == "enfeebled"]
    assert enfeebled
    assert enfeebled[0].data.get("enfeebled_value") == 1


def test_daze_critical_failure_applies_stunned(monkeypatch):
    hero = DummyActor("hero", (0, 0))
    enemy = DummyActor("enemy", (1, 0), hp=20)
    game = _game(actor=hero, enemies=[enemy])

    monkeypatch.setattr(occ, "pick_target_in_range", lambda *_a, **_k: (enemy, enemy.position))
    rolls = iter([15, 6])
    monkeypatch.setattr(occ, "prompt_for_roll", lambda *_a, **_k: next(rolls))
    monkeypatch.setattr(occ.random, "randint", lambda _a, _b: 1)  # critical failure

    res = occ.DazeEvent().execute(EventContext(game=game, actor=hero))

    assert res.success is True
    assert enemy.hp == 14
    assert any(getattr(s, "id", "") == "stunned" for s in enemy.statuses)


def test_forbidding_ward_sets_target_id(monkeypatch):
    caster = DummyActor("caster", (0, 0), object_id="caster-id")
    ally = DummyActor("ally", (1, 0), object_id="ally-id")
    enemy = DummyActor("enemy", (2, 0), object_id="enemy-id")
    game = _game(actor=caster, heroes=[caster, ally], enemies=[enemy])

    picks = [(ally, ally.position), (enemy, enemy.position)]
    monkeypatch.setattr(occ, "pick_target_in_range", lambda *_a, **_k: picks.pop(0))

    res = occ.ForbiddingWardEvent().execute(EventContext(game=game, actor=caster))

    assert res.success is True
    ac_bonuses = [b for b in ally.bonuses if b.tag == "ac"]
    save_bonuses = [b for b in ally.bonuses if b.tag in ("fortitude", "reflex", "will")]
    enemy_penalties = [b for b in enemy.bonuses if b.is_penalty]
    assert ac_bonuses and ac_bonuses[0].target_id == "enemy-id"
    assert save_bonuses and all(b.target_id == "enemy-id" for b in save_bonuses)
    assert enemy_penalties and all(b.target_id == "ally-id" for b in enemy_penalties)


def test_shield_cantrip_absorbs_damage_and_breaks():
    caster = DummyActor("caster", (0, 0), hp=20)
    game = _game(actor=caster)

    res = occ.ShieldCantripEvent().execute(EventContext(game=game, actor=caster))
    assert res.success is True

    caster.apply_damage(3, "slashing")
    assert caster.hp == 20  # absorbed fully

    caster.apply_damage(4, "slashing")
    assert caster.hp == 18  # remaining absorb was 2
    assert not any(getattr(s, "id", "") == "shield_cantrip" for s in caster.statuses)


def test_dancing_lights_select_and_confirm():
    hero = DummyActor("hero", (0, 0))
    enemy = DummyActor("enemy", (1, 1))
    enemy.add_status(InDarkStatus())
    terrain = {
        (1, 1): "darkness",
        (2, 1): "dim_light",
        (3, 1): "dim_light",
    }
    conn = DummyConn(scans=[(1, 1), hero.position])
    board = DummyBoard(terrain_map=terrain)
    game = _game(actor=hero, heroes=[hero], enemies=[enemy], board=board, conn=conn)

    res = occ.DancingLightsEvent().execute(EventContext(game=game, actor=hero))

    assert res.success is True
    assert game._magic_lighting["dancing_positions"] == {(1, 1)}
    assert not enemy.has_status("in_dark")


def test_light_sets_aura_and_applies_stealth_penalty():
    caster = DummyActor("caster", (0, 0))
    sneaker = DummyActor("sneaker", (1, 0))
    game = _game(actor=caster, heroes=[caster, sneaker])

    res = occ.LightEvent().execute(EventContext(game=game, actor=caster))
    assert res.success is True
    assert is_position_in_light_aura(game, sneaker.position)

    sneaker.game = game
    mod, _breakdown, _notes = compute_skill_modifier_with_sources(
        skill_id=Skill.STEALTH.value,
        actor=sneaker,
        tags=[Skill.STEALTH.value, "try_stealth"],
    )
    assert mod <= -10


def test_mage_hand_interacts_non_npc(monkeypatch):
    hero = DummyActor("hero", (0, 0))

    class DummyInteractable:
        def __init__(self):
            self.actions = {"interact": object()}
            self.called = False

        def interact(self, actor, game, action_id=None):
            self.called = True
            return f"ok:{action_id}:{actor.name}"

    obj = DummyInteractable()
    board = DummyBoard(interactables={(1, 0): [obj]})
    game = _game(actor=hero, board=board)

    monkeypatch.setattr(occ, "pick_target_in_range", lambda *_a, **_k: (obj, (1, 0)))
    res = occ.MageHandEvent().execute(EventContext(game=game, actor=hero))

    assert res.success is True
    assert obj.called is True


def test_message_targets_npc(monkeypatch):
    hero = DummyActor("hero", (0, 0))
    npc = BaseNPC(name="Guide")
    npc.position = (1, 0)

    called = {"talk": False}

    def _talk(actor, game, action_id=None):
        called["talk"] = True
        return "hello"

    npc.interact = _talk

    board = DummyBoard(interactables={(1, 0): [npc]})
    game = _game(actor=hero, board=board)
    monkeypatch.setattr(occ, "pick_target_in_range", lambda *_a, **_k: (npc, npc.position))

    res = occ.MessageEvent().execute(EventContext(game=game, actor=hero))

    assert res.success is True
    assert called["talk"] is True


def test_read_aura_logs_enemy_statuses(monkeypatch):
    hero = DummyActor("hero", (0, 0))
    enemy = DummyActor("enemy", (1, 0))
    enemy.add_status(Status(id="poisoned", label="Poisoned"))
    game = _game(actor=hero, enemies=[enemy])

    monkeypatch.setattr(occ, "pick_target_in_range", lambda *_a, **_k: (enemy, enemy.position))
    res = occ.ReadAuraEvent().execute(EventContext(game=game, actor=hero))

    assert res.success is True
    assert any("poisoned" in msg.lower() for msg in game._logs)


def test_stunned_consumed_on_turn_start():
    actor = DummyActor("hero", (0, 0), object_id="hero-1")
    actor.add_status(StunnedStatus(value=2))
    game = SimpleNamespace(heroes=[actor], enemies=[], ui_log=lambda *_a, **_k: None, ui_event=lambda *_a, **_k: None)
    combat = Combat(game)
    game.state = combat
    combat.round_queue = [actor]
    combat.base_order = [actor]
    combat.base_initiative[actor] = 15

    current = combat._current_actor()

    assert current is actor
    assert combat.actions_used[actor] == 2
    assert not actor.has_status("stunned")
