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
from GameObjects.events.base import EventResult
from GameObjects.items.shield import StandardShield
from states.combat import Combat


class DummyConn:
    def __init__(self, answer: str = "test_action"):
        self.answer = answer
        self.read_calls = 0

    def set_leds(self, *_args, **_kwargs):
        return None

    def scan_board(self, positions):
        return positions[0] if positions else None

    def leds_off(self):
        return None

    def read_card(self, *_args, **_kwargs):
        self.read_calls += 1
        return self.answer


class DummyUI:
    def __init__(self, *, answer: str = "tak"):
        self.enabled = True
        self.answer = answer
        self.prompt_calls = 0
        self.allow_cli_fallback = False

    def prompt_choice(self, *_args, **_kwargs):
        self.prompt_calls += 1
        return self.answer


class DummyActor:
    def __init__(self, name: str, pos: tuple[int, int]):
        self.name = name
        self.object_id = name
        self.position = pos
        self.initiative = 10
        self.hp = 10
        self.statuses = []
        self.reactions = []
        self.reactions_left = 1
        self.reactions_max = 1

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

    def __init__(self):
        self.executed = 0

    def triggers(self, _actor, _event):
        return True

    def reason(self, _actor, _event):
        return "test"

    def execute(self, _actor, _event, ctx):
        self.executed += 1
        _ = ctx
        return True


def _build_game():
    ui = DummyUI()
    conn = DummyConn()
    logs: list[str] = []
    game = SimpleNamespace(
        heroes=[],
        enemies=[],
        conn=conn,
        ui=ui,
        board=SimpleNamespace(),
        ui_log=lambda msg: logs.append(str(msg)),
        ui_event=lambda *_a, **_k: None,
        ui_hero=lambda *_a, **_k: None,
        ui_active_actor=lambda *_a, **_k: None,
        _logs=logs,
    )
    return game, ui, conn


def test_reaction_before_turn_reduces_starting_actions():
    game, _ui, _conn = _build_game()
    champion = DummyActor("champion", (0, 0))
    ally = DummyActor("ally", (5, 5))
    enemy = DummyActor("enemy", (0, 1))
    reaction = DummyReaction()
    champion.reactions = [reaction]

    game.heroes = [ally, champion]
    game.enemies = [enemy]
    combat = Combat(game)
    game.state = combat
    combat.base_order = [ally, champion, enemy]
    combat.round_queue = [ally, champion, enemy]
    combat.base_initiative[ally] = 15
    combat.base_initiative[champion] = 12
    combat.base_initiative[enemy] = 10

    dispatch_reactions(game, {"actor": enemy, "action_id": "enemy_attack", "action_tags": ["move"]})

    assert reaction.executed == 1
    assert champion.reactions_left == 0
    assert combat.out_of_turn_actions_used.get(champion, 0) == 1

    combat.round_queue = [champion]
    combat.base_order = [champion]
    actor = combat._current_actor()

    assert actor is champion
    assert combat.actions_used.get(champion, 0) == 1
    assert combat.actions_remaining(champion) == 2


def test_reaction_is_blocked_without_available_actions():
    game, ui, _conn = _build_game()
    champion = DummyActor("champion", (0, 0))
    enemy = DummyActor("enemy", (0, 1))
    reaction = DummyReaction()
    champion.reactions = [reaction]

    game.heroes = [champion]
    game.enemies = [enemy]
    combat = Combat(game)
    game.state = combat
    combat.out_of_turn_actions_used[champion] = 3

    dispatch_reactions(game, {"actor": enemy, "action_id": "enemy_attack", "action_tags": ["move"]})

    assert reaction.executed == 0
    assert champion.reactions_left == 1
    assert ui.prompt_calls == 0


def test_auto_end_turn_when_action_spends_last_slot(monkeypatch):
    import states.combat as combat_module

    game, _ui, conn = _build_game()
    hero = DummyActor("hero", (0, 0))
    enemy = DummyActor("enemy", (1, 0))
    game.heroes = [hero]
    game.enemies = [enemy]

    combat = Combat(game)
    game.state = combat
    combat._initiatives_ready = True
    combat.base_order = [hero, enemy]
    combat.round_queue = [hero, enemy]
    combat.base_initiative[hero] = 12
    combat.base_initiative[enemy] = 10
    combat.actions_used[hero] = 2

    monkeypatch.setattr(combat_module, "list_events", lambda: {"test_action": object()})
    monkeypatch.setattr(
        combat_module,
        "dispatch_event",
        lambda _name, _ctx: EventResult(success=True, consumed_action=True, actions_spent=1, message="ok"),
    )

    combat.choose_action()

    assert combat.round_queue[0] is enemy
    assert conn.read_calls == 1


def test_auto_end_turn_when_no_actions_left_at_start():
    game, _ui, conn = _build_game()
    hero = DummyActor("hero", (0, 0))
    enemy = DummyActor("enemy", (1, 0))
    game.heroes = [hero]
    game.enemies = [enemy]

    combat = Combat(game)
    game.state = combat
    combat._initiatives_ready = True
    combat.base_order = [hero, enemy]
    combat.round_queue = [hero, enemy]
    combat.base_initiative[hero] = 12
    combat.base_initiative[enemy] = 10
    combat.out_of_turn_actions_used[hero] = 3

    combat.choose_action()

    assert combat.round_queue[0] is enemy
    assert conn.read_calls == 0


def test_full_round_reaction_then_two_actions_auto_end(monkeypatch):
    import states.combat as combat_module

    game, _ui, conn = _build_game()
    hero = DummyActor("hero", (0, 0))
    ally = DummyActor("ally", (2, 2))
    enemy = DummyActor("enemy", (0, 1))
    reaction = DummyReaction()
    hero.reactions = [reaction]

    game.heroes = [ally, hero]
    game.enemies = [enemy]
    combat = Combat(game)
    game.state = combat
    combat._initiatives_ready = True
    combat.base_order = [ally, hero, enemy]
    combat.round_queue = [ally, hero, enemy]
    combat.base_initiative[ally] = 15
    combat.base_initiative[hero] = 12
    combat.base_initiative[enemy] = 10

    # Reakcja poza turą bohatera -> start swojej tury z 2 akcjami.
    dispatch_reactions(game, {"actor": enemy, "action_id": "enemy_attack", "action_tags": ["move"]})
    assert combat.out_of_turn_actions_used.get(hero, 0) == 1

    # Przejście do tury bohatera.
    combat.round_queue = [hero, enemy]
    combat.base_order = [hero, enemy]

    monkeypatch.setattr(combat_module, "list_events", lambda: {"test_action": object()})
    monkeypatch.setattr(
        combat_module,
        "dispatch_event",
        lambda _name, _ctx: EventResult(success=True, consumed_action=True, actions_spent=1, message="ok"),
    )

    combat.choose_action()
    assert combat.round_queue[0] is hero
    combat.choose_action()
    assert combat.round_queue[0] is enemy
    assert conn.read_calls == 2


def test_hero_ui_note_contains_shield_status():
    game, _ui, _conn = _build_game()
    hero = DummyActor("hero", (0, 0))
    enemy = DummyActor("enemy", (1, 0))
    hero.equipped_shield = StandardShield(current_hp=8)
    notes: list[str] = []
    game.ui_hero = lambda _hero, note=None, **_kwargs: notes.append(str(note or ""))
    game.heroes = [hero]
    game.enemies = [enemy]

    combat = Combat(game)
    game.state = combat
    combat._initiatives_ready = True
    combat.base_order = [hero, enemy]
    combat.round_queue = [hero, enemy]
    combat.base_initiative[hero] = 12
    combat.base_initiative[enemy] = 10
    combat.actions_used[hero] = 3

    combat.choose_action()

    assert notes
    assert "Shield:" in notes[-1]
    assert "BROKEN" in notes[-1]
