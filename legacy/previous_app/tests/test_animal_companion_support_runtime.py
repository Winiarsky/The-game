from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from action_events import ActionEventBus
from GameObjects.companions import build_animal_companion
from GameObjects.events.magic import base_attack_magic_event
from GameObjects.events.magic.base_attack_magic_event import BaseMagicAttackEvent
from GameObjects.companions.support_runtime import (
    animal_companion_support_damage_bonus,
    animal_companion_support_forces_off_guard,
    apply_on_hit_animal_companion_support,
)
from GameObjects.events.base import EventContext, EventResult
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from board_grid import BoardGrid
from statuses import action_block_reason, speed_penalty_value
from statuses.base import Status


class DummyConn:
    def set_leds(self, *_args, **_kwargs):
        return None

    def leds_off(self):
        return None

    def scan_board(self, acceptable_responses=None):
        if acceptable_responses:
            return acceptable_responses[0]
        return None

    def read_card(self, *_args, **_kwargs):
        return "end"


class DummyUI:
    enabled = False
    allow_cli_fallback = False


class Combat:
    def __init__(self):
        self.animal_companions: dict[str, object] = {}
        self.round_index = 1
        self._reaction_resolution_keys: set[tuple[object, ...]] = set()

    def get_animal_companion(self, owner):
        return self.animal_companions.get(str(getattr(owner, "object_id", "") or ""))

    def can_pay_reaction_action_cost(self, _actor, *, cost: int = 1) -> bool:
        return cost >= 1

    def consume_reaction_action_cost(self, _actor, *, cost: int = 1, reason: str | None = None) -> bool:
        _ = reason
        return cost >= 1

    def _effective_initiative(self, actor) -> int:
        return int(getattr(actor, "initiative", 0) or 0)


@dataclass
class DummyActor(StatusMixin):
    name: str = "Actor"
    object_id: str = "actor-1"
    position: tuple[int, int] | None = None
    hp: int = 20
    ac: int = 14
    level: int = 1
    initiative: int = 10
    class_name: str = "druid"
    reactions: list[object] = field(default_factory=list)
    reactions_left: int = 1
    reactions_max: int = 1
    ui_messages: list[str] = field(default_factory=list)

    def __hash__(self):
        return hash(self.object_id)

    def set_position(self, position):
        self.position = position

    def apply_damage(self, amount: int, _damage_type: str = "normal"):
        self.hp -= int(amount)
        return self.hp, self.hp <= 0

    def ui_log(self, message: str):
        self.ui_messages.append(str(message))

    def consume_reaction(self):
        if self.reactions_left <= 0:
            return False
        self.reactions_left -= 1
        return True

    def reset_reactions(self):
        self.reactions_left = self.reactions_max


class DummyReaction:
    id = "dummy_reaction"
    label = "Dummy Reaction"
    requires_reach = True
    priority = 1

    def __init__(self):
        self.executed = 0

    def triggers(self, _actor, event):
        return "manipulate" in {str(tag or "").strip().lower() for tag in (event.get("action_tags") or [])}

    def reason(self, _actor, _event):
        return "dummy"

    def execute(self, _actor, _event, ctx):
        _ = ctx
        self.executed += 1
        return True


class DummyGame:
    def __init__(self, board: BoardGrid):
        self.board = board
        self.conn = DummyConn()
        self.ui = DummyUI()
        self.heroes: list[object] = []
        self.enemies: list[object] = []
        self.state = Combat()
        self.events = ActionEventBus(self)
        self.logs: list[str] = []

    def ui_log(self, message: str, **_kwargs):
        self.logs.append(str(message))

    def ui_event(self, *_args, **_kwargs):
        return None


class DummySpellAttack(BaseMagicAttackEvent):
    name = "dummy_spell_attack"
    default_tags = ["magic", "spell", "attack_ranged"]
    range_feet = 30

    def _resolve_on_target(self, target, pos, ctx, *, critical=False):
        _ = pos, ctx, critical
        return EventResult(success=True, consumed_action=self.consumes_action, message=f"Spell attack hit {getattr(target, 'name', 'target')}.")


def _grant_support(owner: DummyActor, companion_type: str) -> None:
    owner.add_status(
        Status(
            id="animal_companion_support",
            label=f"Animal Companion Support ({companion_type})",
            data={
                "companion_type": companion_type,
                "source_id": owner.object_id,
                "source_turns_left": 1,
                "owner_move_feet_this_turn": 0,
            },
        )
    )


def _setup_support(companion_type: str, *, owner_pos=(1, 1), enemy_pos=(2, 1), companion_pos=(1, 2)):
    board = BoardGrid(6, 6)
    game = DummyGame(board)
    owner = DummyActor(name="Druid", object_id="hero-1", position=owner_pos)
    enemy = DummyActor(name="Enemy", object_id="enemy-1", position=enemy_pos, class_name="enemy")
    game.heroes = [owner]
    game.enemies = [enemy]
    board.place(owner, owner.position)
    board.place(enemy, enemy.position)
    companion = build_animal_companion(owner, companion_type)
    board.place(companion, companion_pos)
    game.state.animal_companions[owner.object_id] = companion
    _grant_support(owner, companion_type)
    return game, owner, enemy, companion


@pytest.mark.parametrize(
    ("companion_type", "assertion"),
    [
        (
            "badger",
            lambda enemy: "Badger Support" in str(
                action_block_reason(enemy, action_tags=["step"], action_name="step") or ""
            ),
        ),
        (
            "cat",
            lambda enemy: any(
                getattr(status, "id", None) == "off_guard" and str(getattr(status, "source", "") or "") == "animal_companion_support:cat"
                for status in getattr(enemy, "statuses", []) or []
            ),
        ),
        (
            "wolf",
            lambda enemy: int(speed_penalty_value(enemy) or 0) == 5,
        ),
    ],
)
def test_on_hit_support_applies_runtime_status_effects(companion_type, assertion):
    game, owner, enemy, _companion = _setup_support(companion_type)

    result = apply_on_hit_animal_companion_support(
        EventContext(game=game, actor=owner),
        owner,
        enemy,
        tags=["attack_ranged"],
    )

    assert result["applied"] is True
    assert assertion(enemy)


def test_bird_support_applies_persistent_bleed(monkeypatch):
    game, owner, enemy, _companion = _setup_support("bird")
    monkeypatch.setattr(
        "GameObjects.companions.support_runtime.prompt_for_roll",
        lambda *_a, **_k: 3,
    )

    result = apply_on_hit_animal_companion_support(
        EventContext(game=game, actor=owner),
        owner,
        enemy,
        tags=["attack_ranged"],
    )

    assert result["applied"] is True
    assert any(
        getattr(status, "id", None) == "persistent_damage" and int((getattr(status, "data", None) or {}).get("amount", 0) or 0) == 3
        for status in getattr(enemy, "statuses", []) or []
    )


def test_bear_support_adds_damage_and_can_finish_target(monkeypatch):
    game, owner, enemy, _companion = _setup_support("bear")
    enemy.hp = 4
    monkeypatch.setattr(
        "GameObjects.companions.support_runtime.prompt_for_roll",
        lambda *_a, **_k: 5,
    )

    result = apply_on_hit_animal_companion_support(
        EventContext(game=game, actor=owner),
        owner,
        enemy,
        tags=["attack_melee"],
    )

    assert result["applied"] is True
    assert result["defeated"] is True
    assert enemy.hp == -1
    assert result["damage_components"] == [("slashing", 5)]


def test_dromaeosaur_support_forces_off_guard_for_melee():
    game, owner, enemy, _companion = _setup_support(
        "dromaeosaur",
        owner_pos=(1, 1),
        enemy_pos=(2, 1),
        companion_pos=(3, 1),
    )

    assert animal_companion_support_forces_off_guard(game, owner, enemy, is_melee=True) is True
    assert animal_companion_support_forces_off_guard(game, owner, enemy, is_melee=False) is False


def test_horse_support_tracks_move_and_adds_damage_bonus():
    game, owner, enemy, _companion = _setup_support(
        "horse",
        owner_pos=(1, 1),
        enemy_pos=(2, 1),
        companion_pos=(2, 2),
    )

    game.events.emit_action(
        actor=owner,
        action_id="move",
        action_tags=["move"],
        from_pos=(1, 1),
        to_pos=(2, 1),
    )
    game.events.emit_action(
        actor=owner,
        action_id="move",
        action_tags=["move"],
        from_pos=(2, 1),
        to_pos=(3, 1),
    )

    bonus, notes = animal_companion_support_damage_bonus(
        game,
        owner,
        enemy,
        tags=["attack_melee"],
    )

    assert bonus == 2
    assert any("+2 circumstance" in str(note) for note in notes)


def test_snake_support_blocks_reactions_for_enemies_in_companion_reach():
    game, owner, enemy, _companion = _setup_support("snake")
    reaction = DummyReaction()
    enemy.reactions = [reaction]
    enemy.reactions_left = 1

    game.events.emit_action(
        actor=owner,
        action_id="interact_pre",
        action_tags=["manipulate"],
    )

    assert reaction.executed == 0


def test_wolf_support_applies_on_owner_spell_attack_but_not_ally_spell_attack(monkeypatch):
    game, owner, enemy, _companion = _setup_support("wolf")
    ally = DummyActor(name="Wizard", object_id="hero-ally", position=(0, 1), class_name="wizard")
    game.heroes.append(ally)
    game.board.place(ally, ally.position)

    monkeypatch.setattr(base_attack_magic_event, "pick_target_in_range", lambda *_a, **_k: (enemy, enemy.position))
    monkeypatch.setattr(base_attack_magic_event, "check_concealed", lambda *_a, **_k: True)
    monkeypatch.setattr(base_attack_magic_event, "prompt_for_roll", lambda *_a, **_k: {"roll": 18, "raw_roll": 18})

    owner_result = DummySpellAttack().execute(EventContext(game=game, actor=owner))
    assert owner_result.success is True
    assert int(speed_penalty_value(enemy) or 0) == 5

    enemy.statuses = []

    ally_result = DummySpellAttack().execute(EventContext(game=game, actor=ally))
    assert ally_result.success is True
    assert int(speed_penalty_value(enemy) or 0) == 0


def test_wolf_support_marks_speed_penalty_as_round_based_and_combat_only():
    game, owner, enemy, _companion = _setup_support("wolf")

    result = apply_on_hit_animal_companion_support(
        EventContext(game=game, actor=owner),
        owner,
        enemy,
        tags=["attack_ranged"],
    )

    assert result["applied"] is True
    penalty = enemy.get_status("speed_penalty")
    assert penalty is not None
    data = penalty.data or {}
    assert int(data.get("combat_rounds_left", 0) or 0) == 10
    assert bool(data.get("expire_on_combat_end", False)) is True
