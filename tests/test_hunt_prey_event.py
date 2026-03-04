from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import GameObjects.events.all_events  # noqa: F401
from GameObjects.events.base import EventContext
from GameObjects.events.registry import dispatch_event
from GameObjects.interactions_mixin.bonus_mixin import BonusMixin
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from GameObjects.items.weapon import create_weapon
from states.combat import Combat
from skills import Skill
from statuses.base import Status


class FakeConn:
    def __init__(self, choice=None):
        self.choice = choice

    def set_leds(self, *_args, **_kwargs):
        return None

    def scan_board(self, _acceptable_responses=None):
        return self.choice

    def leds_off(self):
        return None


class FakeGame:
    def __init__(self):
        self.heroes = []
        self.enemies = []
        self.conn = FakeConn()
        self.state = None
        self.ui_log = lambda *_a, **_k: None


@dataclass
class DummyHero(StatusMixin, BonusMixin):
    object_id: str = "hero-1"
    name: str = "Hero"
    position: tuple[int, int] | None = (0, 0)
    messages: list[str] = field(default_factory=list)
    inventory: list[object] = field(default_factory=list)
    equipped_weapon_item_ids: list[str] = field(default_factory=list)

    def ui_log(self, message: str) -> None:
        self.messages.append(str(message))


@dataclass
class DummyEnemy:
    object_id: str = "enemy-1"
    name: str = "Enemy"
    position: tuple[int, int] | None = (1, 0)
    hp: int = 20
    ac: int = 15


def test_hunt_prey_sets_target_and_grants_outwit_and_monster_hunter(monkeypatch):
    actor = DummyHero(object_id="hero-ranger", name="Ranger")
    ally = DummyHero(object_id="hero-ally", name="Ally")
    enemy = DummyEnemy(object_id="enemy-goblin", name="Goblin", position=(1, 0))

    crossbow = create_weapon("longbow")
    assert crossbow is not None
    crossbow.item_id = "crossbow"
    crossbow.name = "Crossbow"
    crossbow.traits = ("crossbow",)
    actor.inventory = [crossbow]
    actor.equipped_weapon_item_ids = [crossbow.instance_id]

    actor.add_status(
        Status(
            id="ranger",
            data={
                "ranger_setup": {
                    "hunter_edge": "outwit",
                    "monster_hunter_used_target_ids": [],
                }
            },
        )
    )
    actor.add_status(Status(id="hunt_prey"))
    actor.add_status(Status(id="monster_hunter"))
    actor.add_status(Status(id="crossbow_ace"))

    game = FakeGame()
    game.heroes = [actor, ally]
    game.enemies = [enemy]
    game.conn.choice = enemy.position
    game.state = Combat(game)

    monkeypatch.setattr(
        "GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll",
        lambda *_a, **_k: {"roll": 20, "natural_shift": 1},
    )

    result = dispatch_event("hunt_prey", EventContext(game=game, actor=actor))

    assert result.success is True
    setup = actor.get_status_data("ranger", "ranger_setup", {})
    assert setup.get("hunted_prey_target_id") == enemy.object_id

    outwit_effects = [b for b in actor.bonuses if str(getattr(b, "source", "")) == "ranger:outwit:ac"]
    assert outwit_effects
    assert outwit_effects[0].target_id == enemy.object_id

    ally_attack_bonuses = [
        b
        for b in ally.bonuses
        if str(getattr(b, "source", "")) == "ranger:monster_hunter:attack" and b.target_id == enemy.object_id
    ]
    assert ally_attack_bonuses

    used_targets = set((actor.get_status_data("ranger", "ranger_setup", {}) or {}).get("monster_hunter_used_target_ids") or [])
    assert enemy.object_id in used_targets

    assert actor.has_status("crossbow_ace_ready")


def test_hunt_prey_unavailable_outside_combat():
    actor = DummyHero(object_id="hero-ranger", name="Ranger")
    enemy = DummyEnemy(object_id="enemy-goblin", name="Goblin", position=(1, 0))
    actor.add_status(Status(id="hunt_prey"))
    actor.add_status(Status(id="ranger", data={"ranger_setup": {"hunter_edge": "outwit"}}))

    game = FakeGame()
    game.heroes = [actor]
    game.enemies = [enemy]
    game.conn.choice = enemy.position
    game.state = None

    result = dispatch_event("hunt_prey", EventContext(game=game, actor=actor))

    assert result.success is False
    assert result.consumed_action is False


def test_monster_hunter_uses_dynamic_recall_skill_for_undead(monkeypatch):
    actor = DummyHero(object_id="hero-ranger", name="Ranger")
    enemy = DummyEnemy(object_id="enemy-undead", name="Skeleton", position=(1, 0), ac=16)
    enemy.tags = ["undead"]
    actor.add_status(Status(id="ranger", data={"ranger_setup": {"hunter_edge": "outwit"}}))
    actor.add_status(Status(id="hunt_prey"))
    actor.add_status(Status(id="monster_hunter"))

    game = FakeGame()
    game.heroes = [actor]
    game.enemies = [enemy]
    game.conn.choice = enemy.position
    game.state = Combat(game)

    captured = {}

    class _Resolution:
        outcome = "critical_success"

    def _fake_resolver(**kwargs):
        captured["skill_id"] = kwargs.get("skill_id")
        captured["dc"] = kwargs.get("dc")
        return _Resolution()

    monkeypatch.setattr("GameObjects.events.ranger_feat_events.resolve_skill_check_with_sources", _fake_resolver)

    result = dispatch_event("hunt_prey", EventContext(game=game, actor=actor))

    assert result.success is True
    assert captured["skill_id"] == Skill.RELIGION.value
    assert int(captured["dc"]) >= 10
