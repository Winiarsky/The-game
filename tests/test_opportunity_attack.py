import types
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from combat.reactions import OpportunityAttack, dispatch_reactions
from GameObjects.interactions_mixin.reactive_mixin import ReactiveMixin
from statuses import OPPORTUNITY_ATTACK_STATUS


class FakeBoard:
    def __init__(self):
        self.removed = []

    def remove(self, pos):
        self.removed.append(pos)

    def in_bounds(self, pos):
        return True


class DummyUI:
    enabled = True

    def __init__(self, choice="tak"):
        self.choice = choice
        self.logs = []

    def prompt_choice(self, _msg, choices, source=None):
        return self.choice

    def log(self, msg):
        self.logs.append(msg)

    def __getattr__(self, name):
        if name == "ui_log":
            return self.log
        raise AttributeError


class DummyGame:
    def __init__(self):
        self.heroes = []
        self.enemies = []
        self.board = FakeBoard()
        self.ui = DummyUI()

    def ui_log(self, msg):
        self.ui.log(msg)


class DummyHero(ReactiveMixin):
    def __init__(self, pos, ac=10, attack_bonus=5):
        super().__init__()
        self.position = pos
        self.ac = ac
        self.attack_bonus = attack_bonus
        self.wounds = 0
        self.reactions = [OpportunityAttack()]
        self.statuses = [OPPORTUNITY_ATTACK_STATUS]

    def consume_reaction(self):
        super().consume_reaction()

    def reset_reactions(self):
        super().reset_reactions()
        self.reactions_left = self.reactions_max


class DummyEnemy(ReactiveMixin):
    def __init__(self, pos, ac=10, hp=10, strength=2):
        super().__init__()
        self.position = pos
        self.ac = ac
        self.hp = hp
        self.strength = strength
        self.reactions = [OpportunityAttack()]
        self.wounds = 0
        self.statuses = [OPPORTUNITY_ATTACK_STATUS]

    def apply_damage(self, amt, _type):
        self.hp -= amt
        return self.hp, self.hp <= 0

    def consume_reaction(self):
        super().consume_reaction()

    def reset_reactions(self):
        super().reset_reactions()
        self.reactions_left = self.reactions_max


def test_enemy_opportunity_attack_triggers_on_leaving_reach(monkeypatch):
    game = DummyGame()
    game.state = type("Combat", (), {})()
    hero = DummyHero(pos=(0, 0))
    enemy = DummyEnemy(pos=(0, 1))
    game.heroes = [hero]
    game.enemies = [enemy]

    # gwarantowany hit: d20=18, dmg=5
    monkeypatch.setattr("random.randint", lambda *args, **kwargs: 18)

    event = {"actor": hero, "action_tags": {"move"}, "from_pos": (0, 0), "to_pos": (0, 1), "leaving_reach": True}
    dispatch_reactions(game, event)

    assert hero.wounds > 0
    assert enemy.reactions_left == 0


def test_hero_opportunity_attack_prompts_and_deals_damage(monkeypatch):
    game = DummyGame()
    game.state = type("Combat", (), {})()
    hero = DummyHero(pos=(0, 0))
    enemy = DummyEnemy(pos=(0, 1), hp=6)
    game.heroes = [hero]
    game.enemies = [enemy]

    # auto-hit: d20=15; dmg roll mocked
    monkeypatch.setattr("random.randint", lambda *args, **kwargs: 15)
    monkeypatch.setattr("combat.reactions.opportunity_attack.prompt_for_roll", lambda *_, **__: 4)
    # typ obrażeń
    monkeypatch.setattr("actions.attack._choose_damage_type", lambda _game: "sieczne")
    game.ui.enabled = True
    game.ui.choice = "tak"

    event = {"actor": enemy, "action_tags": {"move"}, "from_pos": (0, 1), "to_pos": (1, 1), "leaving_reach": True}
    dispatch_reactions(game, event)

    assert enemy.hp < 6  # otrzymał obrażenia
    assert hero.reactions_left == 0


def test_step_does_not_trigger_opportunity_attack():
    """Akcja step nie powinna uruchamiać OA mimo że wykonuje ruch obok wroga."""
    game = DummyGame()
    game.state = type("Combat", (), {})()

    hero = DummyHero(pos=(0, 0))
    enemy = DummyEnemy(pos=(0, 1))
    game.heroes = [hero]
    game.enemies = [enemy]

    # Step – brak tagu 'move' i leaving_reach=False
    event = {
        "actor": hero,
        "action_tags": {"step"},
        "from_pos": (0, 0),
        "to_pos": (1, 0),  # wciąż w zasięgu wroga
        "leaving_reach": False,
    }
    dispatch_reactions(game, event)

    assert hero.wounds == 0
    assert enemy.reactions_left == enemy.reactions_max
