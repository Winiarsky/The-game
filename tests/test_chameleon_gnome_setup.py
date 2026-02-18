from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.game import Game
from src.hero import Hero
from src.GameObjects.events.base import EventContext
from src.GameObjects.events.stealth_event import StealthEvent
from src.statuses.race.gnome.heritages.chameleon_gnome import CHAMELEON_GNOME_STATUS


class DummyConnection:
    def set_leds(self, *_args, **_kwargs):
        return None

    def leds_off(self, *_args, **_kwargs):
        return None

    def scan_board(self, *_args, **_kwargs):
        return (0, 0)

    def read_card(self, *_args, **_kwargs):
        return "DECLINE"


class DummyUI:
    def __init__(self, answer: str):
        self.answer = answer
        self.last_choices = None
        self.enabled = True

    def prompt_choice(self, _prompt: str, choices=None, **_kwargs):
        self.last_choices = list(choices or [])
        return self.answer


def test_chameleon_gnome_setup_choices_and_stealth_bonus():
    game = Game(conn=DummyConnection(), scenario="test_chameleon_gnome")
    ui = DummyUI("bushes")
    game.ui = ui

    hero = Hero()
    hero.add_status(CHAMELEON_GNOME_STATUS)
    game.board.place(hero, (3, 0))

    start_state = game.state
    start_state._maybe_prompt_chameleon_gnome(hero)

    assert ui.last_choices is not None
    assert "bushes" in ui.last_choices
    assert "basic" not in ui.last_choices
    assert "dim_light" not in ui.last_choices
    assert "darkness" not in ui.last_choices
    assert hero.get_status_data("chameleon_gnome", "chameleon_terrain") == "bushes"

    ctx = EventContext(game=game, actor=hero)
    total, details = StealthEvent()._compute_modifier(ctx, hero.position)
    assert total == 2
    assert "chameleon gnome +2" in details
