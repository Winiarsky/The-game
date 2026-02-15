import sys
from pathlib import Path
import types

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# --- Stuby brakujących modułów actions.* potrzebne przy imporcie eventów ---
_actions = types.ModuleType("actions")
_actions.__path__ = []
_move_utils = types.ModuleType("actions.move_utils")
_move_utils.find_path = lambda *a, **k: []
_move_utils.path_cost_feet = lambda *a, **k: 0
_move_utils.trim_path_to_feet = lambda *a, **k: []
_move_utils.perform_movement = lambda *a, **k: None
_move_utils.follow_path = lambda *a, **k: None
_move_utils.default_on_enter = lambda *a, **k: None
_move_utils._maybe_dispatch_move_reactions = lambda *a, **k: None
_specials = types.ModuleType("actions.specials")
_specials.__path__ = []
_magic = types.ModuleType("actions.specials.magic_missile")
_magic.magic_missile_ability = lambda *a, **k: None
sys.modules.setdefault("actions", _actions)
sys.modules.setdefault("actions.move_utils", _move_utils)
sys.modules.setdefault("actions.specials", _specials)
sys.modules.setdefault("actions.specials.magic_missile", _magic)

from bonuses import BonusEffect, BonusType  # noqa: E402
from GameObjects.interactions_mixin.skill_check_resolver import (  # noqa: E402
    resolve_skill_check_with_sources,
)
from GameObjects.events.checks import skill_check_event  # noqa: F401  # rejestruje eventy
from statuses import NOBLE_PERSON_STATUS, SILVER_TONGUE_STATUS, STUBBORN_STATUS  # noqa: E402
from GameObjects.NPC.guard_npc import GuardNPC  # noqa: E402


class DummyGame:
    def __init__(self):
        self.logged = []

    def ui_log(self, msg):
        self.logged.append(msg)


class Hero:
    def __init__(self, statuses=None, bonuses=None):
        self.statuses = statuses or []
        self.bonuses = bonuses or []


def test_source_bonus_and_target_penalty(monkeypatch):
    # gracz podaje wynik końcowy już z premią +2 (13+2=15)
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_: 15)

    actor = Hero(statuses=[NOBLE_PERSON_STATUS])
    target = Hero(statuses=[STUBBORN_STATUS])
    res = resolve_skill_check_with_sources(skill_id="diplomacy", dc=15, actor=actor, target=target, tags=["diplomacy", "noble"])
    assert res.modifier == 2  # bonus z noble_person (pokazywany w promptcie)
    # wejściowy success 15 -> demote o 1 (stubborn) => failure
    assert res.outcome == "failure"
    assert any("szlacheckie" in note or "oporny" in note for note in res.notes) or res.notes


def test_promotion_from_silver_tongue(monkeypatch):
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_: 12)
    actor = Hero(statuses=[SILVER_TONGUE_STATUS])
    res = resolve_skill_check_with_sources(skill_id="diplomacy", dc=15, actor=actor, target=None, tags=["diplomacy"])
    # 12 vs 15 -> failure, promote +1 => success
    assert res.outcome == "success"
    assert "Rzuć 2k20" in " ".join(res.notes)


def test_conditional_promote_on_success(monkeypatch):
    from statuses.base import Status
    from statuses.check_effects import CheckEffect

    # promote tylko gdy bazowo success
    dwarven = Status(
        id="dwarven_resilience",
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=["fortitude"],
                tags_required=["necromancy"],
                promote=1,
                promote_on=["success"],
                prompt_notes=["Krasnoludzka odporność: success -> critical success vs nekromancja."],
            )
        ],
    )

    # bazowy success (roll 13 vs DC 13)
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_: 13)
    actor = Hero(statuses=[dwarven])
    res = resolve_skill_check_with_sources(skill_id="fortitude", dc=13, actor=actor, target=None, tags=["necromancy"])
    assert res.outcome == "critical_success"

    # bazowy failure (roll 10 vs DC 13) nie spełnia promote_on -> zostaje failure
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_: 10)
    res2 = resolve_skill_check_with_sources(skill_id="fortitude", dc=13, actor=actor, target=None, tags=["necromancy"])
    assert res2.outcome == "failure"


def test_guard_diplomacy_action(monkeypatch):
    # roll 17 ensures sukces (DC zależy od nastawienia=0 => 16)
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_: 17)
    game = DummyGame()
    guard = GuardNPC(enable_trade=False, enable_pickpocket=False, enable_talk=False, enable_diplomacy=True, attitude=0)
    hero = Hero(statuses=[NOBLE_PERSON_STATUS, SILVER_TONGUE_STATUS])

    msg = guard.action_diplomacy_guard(hero, game)
    assert "pismo" in msg.lower()
    assert guard.diplomacy_letter_given
    assert guard.attitude >= 0

    # krytyczna porażka blokuje (osobna instancja bez promujących statusów)
    guard2 = GuardNPC(enable_trade=False, enable_pickpocket=False, enable_talk=False, enable_diplomacy=True, attitude=0)
    hero_plain = Hero()
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_: 1)
    msg2 = guard2.action_diplomacy_guard(hero_plain, game)
    assert "Nie będzie dalszych" in msg2 or guard2.diplomacy_blocked
