from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from combat.reactions.dispatcher import clear_turn_reaction_policies, dispatch_reactions
from states.combat import Combat


class DummyUI:
    def __init__(self, answers: list[str]):
        self.enabled = True
        self.allow_cli_fallback = False
        self.answers = list(answers)
        self.prompt_calls = 0

    def prompt_choice(self, _prompt, choices=None, **_kwargs):
        self.prompt_calls += 1
        if self.answers:
            return self.answers.pop(0)
        if choices:
            return choices[0]
        return None


class DummyActor:
    def __init__(self, name: str, pos: tuple[int, int], *, reactions_max: int = 2):
        self.name = name
        self.object_id = name
        self.position = pos
        self.initiative = 10
        self.hp = 10
        self.statuses = []
        self.reactions = []
        self.reactions_max = reactions_max
        self.reactions_left = reactions_max

    def __hash__(self):
        return id(self)

    def reset_reactions(self):
        self.reactions_left = self.reactions_max

    def consume_reaction(self):
        if self.reactions_left <= 0:
            return False
        self.reactions_left -= 1
        return True


class DummyReaction:
    id = "test_reaction"
    label = "Test Reaction"
    requires_reach = False
    blocks_range_attacker = False
    action_cost = 1
    priority = 1

    def __init__(self):
        self.executed = 0

    def triggers(self, _actor, _event):
        return True

    def reason(self, _actor, _event):
        return "test reason"

    def execute(self, _actor, _event, ctx):
        _ = ctx
        self.executed += 1
        return True


def _build_game(ui_answers: list[str]):
    ui = DummyUI(ui_answers)
    game = SimpleNamespace(
        heroes=[],
        enemies=[],
        ui=ui,
        conn=SimpleNamespace(),
        board=SimpleNamespace(),
        ui_log=lambda *_a, **_k: None,
        ui_event=lambda *_a, **_k: None,
        ui_hero=lambda *_a, **_k: None,
        ui_active_actor=lambda *_a, **_k: None,
    )
    combat = Combat(game)
    game.state = combat
    return game, combat, ui


def test_auto_for_trigger_executes_without_second_prompt():
    game, combat, ui = _build_game(["auto_for_trigger"])
    reactor = DummyActor("hero", (0, 0), reactions_max=2)
    enemy = DummyActor("enemy", (1, 0), reactions_max=0)
    reaction = DummyReaction()
    reactor.reactions = [reaction]

    game.heroes = [reactor]
    game.enemies = [enemy]
    combat.base_order = [reactor, enemy]
    combat.round_queue = [reactor, enemy]
    combat.base_initiative[reactor] = 12
    combat.base_initiative[enemy] = 10

    dispatch_reactions(game, {"actor": enemy, "action_id": "enemy_move_1", "action_tags": ["move"], "event_uid": "e1"})
    dispatch_reactions(game, {"actor": enemy, "action_id": "enemy_move_2", "action_tags": ["move"], "event_uid": "e2"})

    assert reaction.executed == 2
    assert ui.prompt_calls == 1


def test_pass_trigger_until_turn_end_skips_until_policy_is_cleared():
    game, combat, ui = _build_game(["pass_trigger_until_turn_end", "react_now"])
    reactor = DummyActor("hero", (0, 0), reactions_max=1)
    enemy = DummyActor("enemy", (1, 0), reactions_max=0)
    reaction = DummyReaction()
    reactor.reactions = [reaction]

    game.heroes = [reactor]
    game.enemies = [enemy]
    combat.base_order = [reactor, enemy]
    combat.round_queue = [reactor, enemy]
    combat.base_initiative[reactor] = 12
    combat.base_initiative[enemy] = 10

    dispatch_reactions(game, {"actor": enemy, "action_id": "enemy_move_1", "action_tags": ["move"], "event_uid": "e1"})
    dispatch_reactions(game, {"actor": enemy, "action_id": "enemy_move_2", "action_tags": ["move"], "event_uid": "e2"})

    assert reaction.executed == 0
    assert ui.prompt_calls == 1

    clear_turn_reaction_policies(reactor)
    dispatch_reactions(game, {"actor": enemy, "action_id": "enemy_move_3", "action_tags": ["move"], "event_uid": "e3"})

    assert reaction.executed == 1
    assert ui.prompt_calls == 2
