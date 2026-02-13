import sys
import types
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import GameObjects.events.all_events  # noqa: F401
from GameObjects.events.base import EventContext
from GameObjects.events.registry import dispatch_event
from GameObjects.NPC.guard_npc import GuardNPC


class FakeUI:
    def __init__(self):
        self.enabled = True
        self.rolls = []
        self._answers = ["1", "leave"]

    def prompt_choice(self, *_, **__):
        # wybierz Diplomacy, potem zakończ rozmowę
        return self._answers.pop(0) if self._answers else "leave"

    def prompt_roll(self, *_, **__):
        # stały wynik, żeby zaliczyć test
        self.rolls.append(18)
        return 18


class FakeConn:
    def __init__(self, target_pos):
        self.target_pos = target_pos
        self.calls = []

    def set_leds(self, *a, **k):
        return None

    def scan_board(self, *_a, **_k):
        return self.target_pos

    def leds_off(self, *a, **k):
        return None

    def read_card(self, *a, **k):
        return "interaction"


class FakeBoard:
    def __init__(self, interactable, hero_pos, target_pos):
        self.interactable = interactable
        self.hero_pos = hero_pos
        self.target_pos = target_pos

    def get_interactables_in_range(self, *_a, **_k):
        return [(self.target_pos, [self.interactable])]

    def interactables_at(self, *_a, **_k):
        return [self.interactable]

    def get_neighbors(self, *_a, **_k):
        return []

    def rooms_at(self, *_a, **_k):
        return set()

    def positions_in_rooms(self, *_a, **_k):
        return set()

    def can_traverse(self, *_a, **_k):
        return True

    def can_enter(self, *_a, **_k):
        return True


class FakeEvents:
    def safe_emit_action(self, **_payload):
        return True


class FakeGame:
    def __init__(self, hero, guard, target_pos):
        self.heroes = [hero]
        self.enemies = []
        self.conn = FakeConn(target_pos)
        self.board = FakeBoard(guard, hero.position, target_pos)
        self.events = FakeEvents()
        self.ui = FakeUI()

    def ui_log(self, *_, **__):
        return None

    def ui_event(self, *_, **__):
        return None


def test_interaction_triggers_skill_check(monkeypatch):
    hero = types.SimpleNamespace(name="Hero", position=(1, 1), statuses=[], has_status=lambda *_: False)
    guard = GuardNPC(enable_talk=False, enable_trade=False, enable_pickpocket=False, enable_diplomacy=True)
    game = FakeGame(hero, guard, target_pos=(2, 1))

    # skieruj skill_check na fake UI (bez oczekiwania na prawdziwy UI)
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.get_ui_client", lambda: game.ui)

    ctx = EventContext(game=game, actor=hero, tags=["interaction"])
    result = dispatch_event("interaction", ctx)

    assert result.success, "Interaction event powinien zakończyć się sukcesem"
    assert game.ui.rolls, "Powinien zostać wywołany prompt roll dla skill_check"
