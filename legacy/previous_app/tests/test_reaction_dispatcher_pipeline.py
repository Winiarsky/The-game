from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from combat.reactions.dispatcher import dispatch_reactions
from states.combat import Combat


class DummyUI:
    enabled = False
    allow_cli_fallback = False


class DummyActor:
    def __init__(self, name: str, pos: tuple[int, int], *, initiative: int = 10, hp: int = 10, reactions_max: int = 1):
        self.name = name
        self.object_id = name
        self.position = pos
        self.initiative = initiative
        self.hp = hp
        self.statuses = []
        self.reactions = []
        self.reactions_max = reactions_max
        self.reactions_left = reactions_max

    def __hash__(self):
        return id(self)

    def consume_reaction(self):
        if self.reactions_left <= 0:
            return False
        self.reactions_left -= 1
        return True

    def reset_reactions(self):
        self.reactions_left = self.reactions_max


class RecordReaction:
    requires_reach = False
    blocks_range_attacker = False
    action_cost = 1

    def __init__(self, rid: str, label: str, *, priority: int, sink: list[str]):
        self.id = rid
        self.label = label
        self.priority = priority
        self.sink = sink
        self.executed = 0

    def triggers(self, _actor, _event):
        return True

    def reason(self, _actor, _event):
        return self.label

    def execute(self, actor, _event, ctx):
        self.executed += 1
        _ = ctx
        self.sink.append(actor.name)
        return True


def _build_game():
    logs: list[str] = []
    game = SimpleNamespace(
        heroes=[],
        enemies=[],
        ui=DummyUI(),
        conn=SimpleNamespace(),
        board=SimpleNamespace(),
        ui_log=lambda msg: logs.append(str(msg)),
        ui_event=lambda *_a, **_k: None,
        ui_hero=lambda *_a, **_k: None,
        ui_active_actor=lambda *_a, **_k: None,
        _logs=logs,
    )
    combat = Combat(game)
    game.state = combat
    return game, combat


def test_dispatcher_orders_by_priority_then_initiative():
    game, combat = _build_game()
    hero = DummyActor("hero", (0, 0), initiative=20)
    enemy_fast = DummyActor("enemy_fast", (0, 1), initiative=18)
    enemy_slow = DummyActor("enemy_slow", (1, 1), initiative=10)
    order: list[str] = []
    enemy_fast.reactions = [RecordReaction("fast_low", "fast-low", priority=5, sink=order)]
    enemy_slow.reactions = [RecordReaction("slow_high", "slow-high", priority=20, sink=order)]

    game.heroes = [hero]
    game.enemies = [enemy_fast, enemy_slow]
    combat.base_order = [hero, enemy_fast, enemy_slow]
    combat.round_queue = [hero, enemy_fast, enemy_slow]
    combat.base_initiative[hero] = 20
    combat.base_initiative[enemy_fast] = 18
    combat.base_initiative[enemy_slow] = 10

    dispatch_reactions(game, {"actor": hero, "action_id": "hero_move", "action_tags": ["move"], "event_uid": "evt-1"})

    assert order == ["enemy_slow", "enemy_fast"]


def test_dispatcher_deduplicates_same_event_uid():
    game, combat = _build_game()
    hero = DummyActor("hero", (0, 0), initiative=20)
    enemy = DummyActor("enemy", (0, 1), initiative=15, reactions_max=2)
    order: list[str] = []
    reaction = RecordReaction("dupe", "dupe", priority=1, sink=order)
    enemy.reactions = [reaction]

    game.heroes = [hero]
    game.enemies = [enemy]
    combat.base_order = [hero, enemy]
    combat.round_queue = [hero, enemy]
    combat.base_initiative[hero] = 20
    combat.base_initiative[enemy] = 15

    event = {"actor": hero, "action_id": "hero_move", "action_tags": ["move"], "event_uid": "evt-same"}
    dispatch_reactions(game, event)
    dispatch_reactions(game, dict(event))

    assert reaction.executed == 1
    assert enemy.reactions_left == 1


def test_dispatcher_skips_when_target_is_dead():
    game, combat = _build_game()
    target_dead = DummyActor("target_dead", (2, 2), initiative=12, hp=0)
    attacker = DummyActor("attacker", (0, 0), initiative=20)
    reactor = DummyActor("reactor", (0, 1), initiative=15)
    order: list[str] = []
    reaction = RecordReaction("dead_target_guard", "guard", priority=1, sink=order)
    reactor.reactions = [reaction]

    game.heroes = [reactor, target_dead]
    game.enemies = [attacker]
    combat.base_order = [attacker, reactor, target_dead]
    combat.round_queue = [attacker, reactor, target_dead]
    combat.base_initiative[attacker] = 20
    combat.base_initiative[reactor] = 15
    combat.base_initiative[target_dead] = 12

    dispatch_reactions(
        game,
        {
            "actor": attacker,
            "target": target_dead,
            "action_id": "enemy_attack",
            "action_tags": ["attack_melee"],
            "event_uid": "dead-target",
        },
    )

    assert reaction.executed == 0
    assert order == []
