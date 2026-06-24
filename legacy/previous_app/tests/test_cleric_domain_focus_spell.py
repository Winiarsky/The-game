from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import GameObjects.events.all_events  # noqa: F401

MOVE_UTILS_PATH = SRC_ROOT / "actions" / "move_utils.py"
move_utils_spec = importlib.util.spec_from_file_location("domain_test_move_utils", MOVE_UTILS_PATH)
move_utils = importlib.util.module_from_spec(move_utils_spec)
assert move_utils_spec and move_utils_spec.loader
move_utils_spec.loader.exec_module(move_utils)  # type: ignore[arg-type]

from board_grid import BoardGrid
from GameObjects.Terrains.rumble_terrain import RumbleTerrain
from GameObjects.events.base import EventContext
from GameObjects.events.magic.focus_spells.cleric import domain_spell_events as domain_events
from GameObjects.events.magic.focus_spells.cleric.domain_spell_events import ClericDomainSpellEvent
from GameObjects.events.registry import dispatch_event, list_events
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from statuses.base import Status
from statuses.classes.cleric.cleric import CLERIC_DOMAIN_INITIAL_SPELLS


@dataclass
class DummyHero(StatusMixin):
    name: str = "Hero"
    position: tuple[int, int] | None = None
    hp: int = 20

    def __post_init__(self):
        self.bonuses = []

    def apply_damage(self, amount: int, _damage_type: str = ""):
        self.hp -= int(amount)
        return self.hp, self.hp <= 0

    def heal(self, amount: int):
        self.hp += int(amount)


class DummyConn:
    def set_leds(self, *_args, **_kwargs):
        return None

    def scan_board(self, *_args, **_kwargs):
        return None

    def leds_off(self):
        return None


def _cleric_with_domain(*, domain: str, spell: str, position=(0, 0), focus: int = 1) -> DummyHero:
    actor = DummyHero(name="Cleric", position=position, hp=20)
    actor.class_name = "cleric"
    actor.focus_point = int(focus)
    actor.add_status(Status(id="cleric", data={"cleric_setup": {"doctrine": "cloistered_cleric"}}))
    actor.add_status(
        Status(
            id="domain_initiate",
            stacks=True,
            data={
                "selected_domain": domain,
                "domain_spell": spell,
            },
        )
    )
    return actor


def _game(*, actor, enemies=None, heroes=None):
    return SimpleNamespace(
        state=object(),
        heroes=list(heroes or [actor]),
        enemies=list(enemies or []),
        conn=DummyConn(),
        ui=None,
        board=None,
        ui_log=lambda *_a, **_k: None,
    )


def test_all_cleric_initial_domain_spells_are_registered():
    events = list_events()
    missing = [spell for spell in CLERIC_DOMAIN_INITIAL_SPELLS.values() if spell not in events]
    assert missing == []
    for spell in CLERIC_DOMAIN_INITIAL_SPELLS.values():
        assert issubclass(events[spell], ClericDomainSpellEvent)


def test_specific_domain_spell_fire_ray_deals_damage_and_spends_focus(monkeypatch):
    actor = _cleric_with_domain(domain="fire", spell="fire_ray")
    target = DummyHero(name="Enemy", position=(1, 0), hp=15)

    monkeypatch.setattr(domain_events, "_pick_target", lambda *_a, **_k: target)
    monkeypatch.setattr(domain_events, "prompt_for_roll", lambda *_a, **_k: 6)

    game = _game(actor=actor, enemies=[target])
    result = dispatch_event("fire_ray", EventContext(game=game, actor=actor))

    assert result.success is True
    assert actor.focus_point == 0
    assert target.hp == 9
    assert any(getattr(status, "id", None) == "persistent_damage" for status in target.statuses)


def test_fire_ray_burn_it_applies_damage_and_persistent_bonus(monkeypatch):
    actor = _cleric_with_domain(domain="fire", spell="fire_ray")
    actor.level = 1
    actor.add_status(Status(id="burn_it"))
    target = DummyHero(name="Enemy", position=(1, 0), hp=15)

    monkeypatch.setattr(domain_events, "_pick_target", lambda *_a, **_k: target)
    monkeypatch.setattr(domain_events, "prompt_for_roll", lambda *_a, **_k: 6)

    game = _game(actor=actor, enemies=[target])
    result = dispatch_event("fire_ray", EventContext(game=game, actor=actor))

    assert result.success is True
    assert actor.focus_point == 0
    assert target.hp == 8  # 6 +1 Burn It (rank 1 => +1)
    persistent = next((s for s in target.statuses if getattr(s, "id", None) == "persistent_damage"), None)
    assert persistent is not None
    assert int((persistent.data or {}).get("amount", 0) or 0) == 2  # base 1 + Burn It persistent +1


def test_domain_focus_spell_dispatches_selected_domain_spell(monkeypatch):
    actor = _cleric_with_domain(domain="fire", spell="fire_ray")
    target = DummyHero(name="Enemy", position=(1, 0), hp=14)

    monkeypatch.setattr(domain_events, "_pick_target", lambda *_a, **_k: target)
    monkeypatch.setattr(domain_events, "prompt_for_roll", lambda *_a, **_k: 5)

    game = _game(actor=actor, enemies=[target])
    result = dispatch_event("domain_focus_spell", EventContext(game=game, actor=actor))

    assert result.success is True
    assert actor.focus_point == 0
    assert target.hp == 9
    assert "placeholder" not in str(result.message or "").lower()


def test_dazzling_flash_applies_blinded(monkeypatch):
    actor = _cleric_with_domain(domain="sun", spell="dazzling_flash")
    target = DummyHero(name="Enemy", position=(1, 0), hp=12)

    monkeypatch.setattr(domain_events, "_pick_target", lambda *_a, **_k: target)

    game = _game(actor=actor, enemies=[target])
    result = dispatch_event("dazzling_flash", EventContext(game=game, actor=actor))

    assert result.success is True
    assert actor.focus_point == 0
    assert any(getattr(status, "id", None) == "blinded" for status in target.statuses)


def test_agile_feet_adds_speed_bonus_status():
    actor = _cleric_with_domain(domain="travel", spell="agile_feet")
    game = _game(actor=actor)

    result = dispatch_event("agile_feet", EventContext(game=game, actor=actor))

    assert result.success is True
    assert actor.focus_point == 0
    assert any(
        getattr(status, "id", None) == "speed_bonus" and int((getattr(status, "data", None) or {}).get("speed_bonus_feet", 0)) >= 10
        for status in actor.statuses
    )


def test_agile_feet_ignores_difficult_terrain_cost():
    actor = _cleric_with_domain(domain="travel", spell="agile_feet")
    board = BoardGrid(rows=1, cols=3)
    board.set_field((1, 0), RumbleTerrain())
    game = _game(actor=actor)
    game.board = board

    result = dispatch_event("agile_feet", EventContext(game=game, actor=actor))

    assert result.success is True
    path = [(0, 0), (1, 0), (2, 0)]
    assert move_utils.path_cost_feet(path, board, mover=actor) == 10


def test_healers_blessing_buffs_next_heal_and_is_consumed(monkeypatch):
    actor = _cleric_with_domain(domain="healing", spell="healers_blessing")
    ally = DummyHero(name="Ally", position=(1, 0), hp=10)
    game = _game(actor=actor, heroes=[actor, ally])

    monkeypatch.setattr(domain_events, "_pick_target", lambda *_a, **_k: ally)
    blessing = dispatch_event("healers_blessing", EventContext(game=game, actor=actor))

    assert blessing.success is True
    assert ally.has_status("healers_blessing")

    monkeypatch.setattr(
        "GameObjects.events.magic.level_1st.events._prompt_choice",
        lambda *_a, **_k: "1",
    )
    monkeypatch.setattr(
        "GameObjects.events.magic.level_1st.events.pick_target_in_range",
        lambda *_a, **_k: (ally, ally.position),
    )
    monkeypatch.setattr(
        "GameObjects.events.magic.level_1st.events.prompt_for_roll",
        lambda *_a, **_k: 6,
    )

    heal_result = dispatch_event("heal", EventContext(game=game, actor=actor))

    assert heal_result.success is True
    assert ally.hp == 18
    assert not ally.has_status("healers_blessing")


def test_registered_domain_spell_action_cost_matches_spec():
    events = list_events()
    fire_ray_cls = events["fire_ray"]
    assert int(getattr(fire_ray_cls, "actions_cost", 0) or 0) == int(domain_events.DOMAIN_SPELL_SPECS["fire_ray"].actions_cost)


def test_enemy_status_domain_spell_can_have_no_effect_on_save_success(monkeypatch):
    actor = _cleric_with_domain(domain="sun", spell="dazzling_flash")
    target = DummyHero(name="Enemy", position=(1, 0), hp=12)

    monkeypatch.setattr(domain_events, "_pick_target", lambda *_a, **_k: target)
    monkeypatch.setattr(domain_events, "_prompt_choice", lambda *_a, **_k: "success")

    game = _game(actor=actor, enemies=[target])
    result = dispatch_event("dazzling_flash", EventContext(game=game, actor=actor))

    assert result.success is True
    assert actor.focus_point == 0
    assert not any(getattr(status, "id", None) == "blinded" for status in target.statuses)
