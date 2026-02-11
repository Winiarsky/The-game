import sys
from pathlib import Path
import types

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from skills import Skill  # noqa: E402
from damage_types import DamageType  # noqa: E402
from combat.damage_utils import apply_damage_resistance  # noqa: E402
from GameObjects.interactions_mixin.skill_check_resolver import (  # noqa: E402
    resolve_skill_check_with_sources,
)
from GameObjects.events.take_cover_event import TakeCoverEvent  # noqa: E402
from GameObjects.Terrains.forest_terrain import ForestTerrain  # noqa: E402
from board_grid import BoardGrid  # noqa: E402
from statuses.race.elf import (  # noqa: E402
    ARCTIC_ELF_STATUS,
    CAVERN_ELF_STATUS,
    SEER_ELF_STATUS,
    WHISPERER_ELF_STATUS,
    WOODLAND_ELF_STATUS,
)
from statuses import IN_DARK_STATUS  # noqa: E402
from bonuses import BonusEffect, BonusType  # noqa: E402
from GameObjects.interactions_mixin import RangeAttackAffectMixin  # noqa: E402


class DummyActor:
    def __init__(self, statuses=None, bonuses=None):
        self.statuses = statuses or []
        self.bonuses = bonuses or []

    def has_status(self, status_id):
        return any(
            status_id == s or getattr(s, "id", None) == status_id for s in self.statuses
        )


def test_arctic_elf_reduces_cold_damage():
    target = DummyActor(statuses=[ARCTIC_ELF_STATUS])
    effective, reduced = apply_damage_resistance(target, 3, DamageType.COLD.value)
    assert reduced == 1
    assert effective == 2


def test_cavern_elf_stores_dark_ignore_flag():
    status = CAVERN_ELF_STATUS
    assert "dark" in status.data.get("ignore_effect_tags", [])
    assert any("dark" in note for note in status.data.get("prompt_notes", []))


def test_seer_elf_bonus_identify_magic(monkeypatch):
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_: 10)
    actor = DummyActor(statuses=[SEER_ELF_STATUS])
    res = resolve_skill_check_with_sources(
        skill_id=Skill.ARCANA.value,
        dc=10,
        actor=actor,
        target=None,
        tags=["identify_magic"],
        apply_modifiers=False,
    )
    assert res.modifier == 1


def test_seer_elf_bonus_decipher_writing_society(monkeypatch):
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_: 10)
    actor = DummyActor(statuses=[SEER_ELF_STATUS])
    res = resolve_skill_check_with_sources(
        skill_id=Skill.SOCIETY.value,
        dc=10,
        actor=actor,
        target=None,
        tags=["decipher_writing"],
        apply_modifiers=False,
    )
    assert res.modifier == 1


def test_whisperer_elf_seek_bonus(monkeypatch):
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_: 12)
    actor = DummyActor(statuses=[WHISPERER_ELF_STATUS])
    res = resolve_skill_check_with_sources(
        skill_id=Skill.PERCEPTION.value,
        dc=12,
        actor=actor,
        target=None,
        tags=["seek", Skill.PERCEPTION.value],
        apply_modifiers=False,
    )
    assert res.modifier == 2


class DummyGame:
    def __init__(self, board):
        self.board = board
        self.conn = types.SimpleNamespace(
            set_leds=lambda *args, **kwargs: None,
            scan_board=lambda positions: positions[0] if positions else None,
            leds_off=lambda: None,
        )

    def ui_log(self, msg):
        # dla testu przechowujemy logi w liście
        self.logged = getattr(self, "logged", [])
        self.logged.append(msg)


class DummyHero(RangeAttackAffectMixin):
    def __init__(self, pos, statuses=None):
        self.position = pos
        self.statuses = statuses or []
        self.bonuses = []

    def add_bonus(self, eff: BonusEffect):
        self.bonuses.append(eff)

    def remove_bonuses_with_prefix(self, prefix: str):
        self.bonuses = [b for b in self.bonuses if not (b.source or "").startswith(prefix)]

    def add_status(self, status):
        if status not in self.statuses:
            self.statuses.append(status)

    def has_status(self, status_id):
        return any(status_id == s or getattr(s, "id", None) == status_id for s in self.statuses)


class DummyCtx:
    def __init__(self, game, actor, in_combat=True):
        self.game = game
        self.actor = actor
        self.in_combat = in_combat


def _ac_bonus(hero):
    return next((b.value for b in hero.bonuses if b.tag == "ac"), None)


def test_woodland_elf_can_take_cover_on_forest():
    board = BoardGrid(rows=3, cols=3)
    hero_pos = (1, 1)
    board.set_field(hero_pos, ForestTerrain())
    hero = DummyHero(hero_pos, statuses=[WOODLAND_ELF_STATUS])
    game = DummyGame(board)
    ctx = DummyCtx(game, hero, in_combat=True)

    result = TakeCoverEvent().execute(ctx)

    assert result.success is True
    # start z "standard" -> upgrade do "greater" => +4 AC
    assert _ac_bonus(hero) == 4
    assert any("forest" in (msg or "").lower() or "Woodland" in (msg or "") for msg in getattr(game, "logged", []))


def test_non_woodland_elf_cannot_take_cover_on_forest():
    board = BoardGrid(rows=3, cols=3)
    hero_pos = (1, 1)
    board.set_field(hero_pos, ForestTerrain())
    hero = DummyHero(hero_pos, statuses=[])
    game = DummyGame(board)
    ctx = DummyCtx(game, hero, in_combat=True)

    result = TakeCoverEvent().execute(ctx)

    assert result.success is False
    assert "osłony" in (result.message or "").lower()


def test_cavern_elf_blocks_in_dark_status():
    actor = DummyActor(statuses=[CAVERN_ELF_STATUS])
    added = actor.__dict__.setdefault("add_status", lambda s: False)
    # korzystamy bezpośrednio z mixinu-like API
    from GameObjects.interactions_mixin.status_mixin import StatusMixin

    sm = StatusMixin(statuses=list(actor.statuses))
    sm.statuses = list(actor.statuses)
    # próba dodania in_dark
    result = sm.add_status(IN_DARK_STATUS)
    assert result is False
    assert not any(s == IN_DARK_STATUS for s in sm.statuses)
