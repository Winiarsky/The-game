from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.events.base import EventContext
from GameObjects.events.lay_on_hands_event import LayOnHandsEvent
from GameObjects.events.raise_shield_event import RaiseShieldEvent
from GameObjects.interactions_mixin import BonusMixin, ReactiveMixin, StatusMixin
from combat.reactions.dispatcher import dispatch_reactions
from states.combat import Combat
from statuses.classes.champion.champion import CHAMPION_STATUS
from statuses import GrabbedStatus, RestrainedStatus
from statuses.enfeebled import enfeebled_value
from GameObjects.items.shield import StandardShield


class DummyUI:
    def __init__(self, answers: list[str]):
        self.answers = list(answers)
        self.enabled = True
        self.allow_cli_fallback = False

    def prompt_choice(self, _prompt: str, choices=None, **_kwargs):
        if self.answers:
            return self.answers.pop(0)
        if choices:
            return choices[0]
        return None

    def prompt_info(self, *_args, **_kwargs):
        return None


class DummyConn:
    def set_leds(self, *_args, **_kwargs):
        return None

    def scan_board(self, positions):
        return positions[0] if positions else None

    def leds_off(self):
        return None

    def read_card(self, *_args, **_kwargs):
        return "end"


class DummyHero(StatusMixin, BonusMixin, ReactiveMixin):
    def __init__(
        self,
        *,
        name: str,
        object_id: str,
        position: tuple[int, int],
        wounds: int = 0,
        level: int = 1,
        ac: int = 16,
        attack_bonus: int = 6,
    ):
        super().__init__()
        self.name = name
        self.object_id = object_id
        self.position = position
        self.wounds = wounds
        self.level = level
        self.ac = ac
        self.attack_bonus = attack_bonus
        self.logs: list[str] = []
        self.bonuses = []
        self.reactions = []
        self.reactions_max = 1
        self.reactions_left = 1

    def __hash__(self):
        return id(self)

    def ui_log(self, message: str) -> None:
        self.logs.append(str(message))

    def heal(self, amount: int) -> int:
        self.wounds = max(0, int(self.wounds) - max(0, int(amount)))
        return self.wounds


class DummyEnemy(ReactiveMixin):
    def __init__(
        self,
        *,
        name: str,
        object_id: str,
        position: tuple[int, int],
        hp: int = 20,
        ac: int = 15,
    ):
        super().__init__()
        self.name = name
        self.object_id = object_id
        self.position = position
        self.hp = hp
        self.ac = ac
        self.statuses: list = []

    def __hash__(self):
        return id(self)

    def add_status(self, status):
        self.statuses.append(status)
        return True

    def apply_damage(self, amount: int, _damage_type: str):
        self.hp -= max(0, int(amount))
        return self.hp, self.hp <= 0


def _add_champion_with_setup(
    hero: DummyHero,
    monkeypatch,
    *,
    cause: str = "Paladin",
    deific_weapon: str = "Sword",
):
    answers = ["standard", "Strength", cause, "Custom", "Religion"]
    if str(cause).strip().lower() == "paladin":
        answers.append(deific_weapon)
    ui = DummyUI(answers)
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)
    hero.add_status(CHAMPION_STATUS)
    return ui


def _add_champion_with_no_shield(
    hero: DummyHero,
    monkeypatch,
    *,
    cause: str = "Paladin",
    deific_weapon: str = "Sword",
):
    answers = ["brak", "Strength", cause, "Custom", "Religion"]
    if str(cause).strip().lower() == "paladin":
        answers.append(deific_weapon)
    ui = DummyUI(answers)
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)
    hero.add_status(CHAMPION_STATUS)
    return ui


def test_champion_status_setup_adds_focus_and_reaction(monkeypatch):
    hero = DummyHero(name="Champion", object_id="hero-champion", position=(0, 0))
    _add_champion_with_setup(hero, monkeypatch, cause="Paladin", deific_weapon="Longbow")

    assert getattr(hero, "class_name", None) == "champion"
    assert getattr(hero, "focus_point", None) == 1
    assert hero.champion_cause == "paladin"
    setup = hero.get_status_data("champion", "champion_setup", {})
    assert setup.get("key_ability") == "strength"
    assert setup.get("deity") == "custom"
    assert setup.get("deity_skill") == "religion"
    assert hero.has_status("raise_shield_allow")
    assert hero.has_status("shield_block")
    assert hero.has_status("deific_weapon")
    assert hero.get_status_data("deific_weapon", "deific_weapon_type") == "longbow"
    assert isinstance(getattr(hero, "equipped_shield", None), StandardShield)
    assert any(getattr(reaction, "id", None) == "champion_reaction" for reaction in hero.reactions)
    assert any(getattr(reaction, "id", None) == "shield_block" for reaction in hero.reactions)


def test_champion_non_paladin_does_not_get_deific_weapon(monkeypatch):
    hero = DummyHero(name="Champion", object_id="hero-champion", position=(0, 0))
    _add_champion_with_setup(hero, monkeypatch, cause="Redeemer")

    assert not hero.has_status("deific_weapon")


def test_lay_on_hands_heals_and_grants_ac_bonus(monkeypatch):
    champion = DummyHero(name="Champion", object_id="hero-champion", position=(0, 0))
    ally = DummyHero(name="Ally", object_id="hero-ally", position=(1, 0), wounds=5)
    _add_champion_with_setup(champion, monkeypatch, cause="Paladin")

    ui = DummyUI(["Ally"])
    game = type("Game", (), {})()
    game.ui = ui
    game.conn = DummyConn()
    game.heroes = [champion, ally]
    game.enemies = []
    game.ui_log = lambda *_a, **_k: None
    game.ui_event = lambda *_a, **_k: None
    game.ui_hero = lambda *_a, **_k: None
    game.ui_active_actor = lambda *_a, **_k: None

    combat = Combat(game)
    game.state = combat
    combat._initiatives_ready = True
    combat.base_order = [champion]
    combat.round_queue = [champion]
    combat.base_initiative[champion] = 12
    combat.turn_initialized.add(champion)
    combat.actions_used[champion] = 0

    result = LayOnHandsEvent().run(EventContext(game=game, actor=champion))

    assert result.success is True
    assert result.consumed_action is True
    assert result.actions_spent == 1
    assert champion.focus_point == 0
    assert ally.wounds == 0
    assert any((bonus.source or "").startswith("lay_on_hands:") for bonus in ally.bonuses)


def test_champion_can_raise_shield_with_granted_feat(monkeypatch):
    champion = DummyHero(name="Champion", object_id="hero-champion", position=(0, 0))
    _add_champion_with_setup(champion, monkeypatch, cause="Paladin")

    game = type("Game", (), {})()
    game.ui = DummyUI([])
    game.conn = DummyConn()
    game.heroes = [champion]
    game.enemies = []
    game.ui_log = lambda *_a, **_k: None
    game.ui_event = lambda *_a, **_k: None
    game.ui_hero = lambda *_a, **_k: None
    game.ui_active_actor = lambda *_a, **_k: None

    combat = Combat(game)
    game.state = combat
    combat._initiatives_ready = True
    combat.base_order = [champion]
    combat.round_queue = [champion]
    combat.base_initiative[champion] = 12

    result = RaiseShieldEvent().run(EventContext(game=game, actor=champion))

    assert result.success is True
    assert result.consumed_action is True
    assert any((bonus.source or "").startswith("raise_shield:") for bonus in champion.bonuses)


def test_champion_without_equipped_shield_cannot_raise_shield(monkeypatch):
    champion = DummyHero(name="Champion", object_id="hero-champion", position=(0, 0))
    _add_champion_with_no_shield(champion, monkeypatch, cause="Paladin")

    game = type("Game", (), {})()
    game.ui = DummyUI([])
    game.conn = DummyConn()
    game.heroes = [champion]
    game.enemies = []
    game.ui_log = lambda *_a, **_k: None
    game.ui_event = lambda *_a, **_k: None
    game.ui_hero = lambda *_a, **_k: None
    game.ui_active_actor = lambda *_a, **_k: None

    combat = Combat(game)
    game.state = combat
    combat._initiatives_ready = True
    combat.base_order = [champion]
    combat.round_queue = [champion]
    combat.base_initiative[champion] = 12

    result = RaiseShieldEvent().run(EventContext(game=game, actor=champion))

    assert result.success is False
    assert "brak wyposazonej tarczy" in str(result.message or "").lower()


def test_champion_reaction_reduces_damage_and_spends_out_of_turn_action(monkeypatch):
    champion = DummyHero(name="Champion", object_id="hero-champion", position=(0, 0))
    ally = DummyHero(name="Ally", object_id="hero-ally", position=(1, 0), wounds=5)
    enemy = DummyEnemy(name="Enemy", object_id="enemy-1", position=(0, 1))
    _add_champion_with_setup(champion, monkeypatch, cause="Redeemer")

    game = type("Game", (), {})()
    game.ui = DummyUI(["tak"])
    game.conn = DummyConn()
    game.heroes = [champion, ally]
    game.enemies = [enemy]
    game.board = type("Board", (), {})()
    game.ui_log = lambda *_a, **_k: None
    game.ui_event = lambda *_a, **_k: None
    game.ui_hero = lambda *_a, **_k: None
    game.ui_active_actor = lambda *_a, **_k: None

    combat = Combat(game)
    game.state = combat
    combat.base_order = [ally, champion, enemy]
    combat.round_queue = [ally, champion, enemy]
    combat.base_initiative[ally] = 15
    combat.base_initiative[champion] = 12
    combat.base_initiative[enemy] = 10

    dispatch_reactions(
        game,
        {
            "actor": enemy,
            "target": ally,
            "action_id": "enemy_attack_melee",
            "action_tags": ["attack_melee"],
            "damage": 5,
        },
    )

    assert ally.wounds == 2
    assert combat.out_of_turn_actions_used.get(champion, 0) == 1
    assert champion.reactions_left == 0
    assert enfeebled_value(enemy) == 2


def test_champion_paladin_reaction_counterattacks(monkeypatch):
    champion = DummyHero(name="Champion", object_id="hero-champion", position=(0, 0))
    ally = DummyHero(name="Ally", object_id="hero-ally", position=(1, 0), wounds=5)
    enemy = DummyEnemy(name="Enemy", object_id="enemy-1", position=(0, 1), hp=20, ac=15)
    _add_champion_with_setup(champion, monkeypatch, cause="Paladin")

    rolls = iter([20, 4])
    monkeypatch.setattr("combat.reactions.champion_reaction.prompt_for_roll", lambda *_a, **_k: next(rolls))

    game = type("Game", (), {})()
    game.ui = DummyUI(["tak"])
    game.conn = DummyConn()
    game.heroes = [champion, ally]
    game.enemies = [enemy]
    game.board = type("Board", (), {"remove": lambda *_a, **_k: None})()
    game.ui_log = lambda *_a, **_k: None
    game.ui_event = lambda *_a, **_k: None
    game.ui_hero = lambda *_a, **_k: None
    game.ui_active_actor = lambda *_a, **_k: None

    combat = Combat(game)
    game.state = combat
    combat.base_order = [ally, champion, enemy]
    combat.round_queue = [ally, champion, enemy]
    combat.base_initiative[ally] = 15
    combat.base_initiative[champion] = 12
    combat.base_initiative[enemy] = 10

    dispatch_reactions(
        game,
        {
            "actor": enemy,
            "target": ally,
            "action_id": "enemy_attack_melee",
            "action_tags": ["attack_melee"],
            "damage": 5,
        },
    )

    assert ally.wounds == 2
    assert enemy.hp == 16


def test_champion_liberator_reaction_clears_grabbed_and_restrained(monkeypatch):
    champion = DummyHero(name="Champion", object_id="hero-champion", position=(0, 0))
    ally = DummyHero(name="Ally", object_id="hero-ally", position=(1, 0), wounds=4)
    enemy = DummyEnemy(name="Enemy", object_id="enemy-1", position=(0, 1))
    _add_champion_with_setup(champion, monkeypatch, cause="Liberator")
    ally.add_status(GrabbedStatus(source_id="enemy-1", maintain_turns_left=1))
    ally.add_status(RestrainedStatus(source_id="enemy-1", maintain_turns_left=1))

    game = type("Game", (), {})()
    game.ui = DummyUI(["tak"])
    game.conn = DummyConn()
    game.heroes = [champion, ally]
    game.enemies = [enemy]
    class Board:
        def __init__(self):
            self.moved = None

        def in_bounds(self, _pos):
            return True

        def get_neighbors(self, pos, include_position=False, diagonal=True):
            _ = include_position
            _ = diagonal
            x, y = pos
            return [
                (x - 1, y),
                (x + 1, y),
                (x, y - 1),
                (x, y + 1),
                (x - 1, y - 1),
                (x + 1, y - 1),
                (x - 1, y + 1),
                (x + 1, y + 1),
            ]

        def can_enter(self, *_args, **_kwargs):
            return True

        def is_blocked(self, *_args, **_kwargs):
            return False

        def edge_interactables_between(self, *_args, **_kwargs):
            return []

        def move(self, src, dst):
            self.moved = (src, dst)

    board = Board()
    game.board = board
    game.ui_log = lambda *_a, **_k: None
    game.ui_event = lambda *_a, **_k: None
    game.ui_hero = lambda *_a, **_k: None
    game.ui_active_actor = lambda *_a, **_k: None

    combat = Combat(game)
    game.state = combat
    combat.base_order = [ally, champion, enemy]
    combat.round_queue = [ally, champion, enemy]
    combat.base_initiative[ally] = 15
    combat.base_initiative[champion] = 12
    combat.base_initiative[enemy] = 10

    dispatch_reactions(
        game,
        {
            "actor": enemy,
            "target": ally,
            "action_id": "enemy_attack_melee",
            "action_tags": ["attack_melee"],
            "damage": 4,
        },
    )

    assert ally.has_status("grabbed") is False
    assert ally.has_status("restrained") is False
    assert board.moved is not None
    assert ally.position != (1, 0)


def test_champion_redeemer_attacker_can_forgo_damage(monkeypatch):
    class EnemyAlly(DummyEnemy):
        def __init__(self, *, name: str, object_id: str, position: tuple[int, int], wounds: int):
            super().__init__(name=name, object_id=object_id, position=position, hp=20, ac=15)
            self.wounds = wounds

        def heal(self, amount: int) -> int:
            self.wounds = max(0, int(self.wounds) - max(0, int(amount)))
            return self.wounds

    champion_enemy = DummyEnemy(name="Redeemer Enemy", object_id="redeemer-enemy", position=(0, 0), hp=20)
    champion_enemy.class_name = "champion"
    champion_enemy.reactions = []
    champion_enemy.reactions_left = 1
    champion_enemy.reactions_max = 1
    champion_enemy.get_status_data = lambda sid, key, default=None: (
        {"cause": "redeemer"} if sid == "champion" and key == "champion_setup" else default
    )
    from combat.reactions.champion_reaction import ChampionReaction

    champion_enemy.reactions = [ChampionReaction()]

    attacker_hero = DummyHero(name="Attacker Hero", object_id="attacker-hero", position=(0, 1), wounds=0)
    target_enemy = EnemyAlly(name="Enemy Ally", object_id="enemy-ally", position=(1, 0), wounds=5)

    game = type("Game", (), {})()
    game.ui = DummyUI(["powstrzymaj atak"])
    game.conn = DummyConn()
    game.heroes = [attacker_hero]
    game.enemies = [champion_enemy, target_enemy]
    game.board = type(
        "Board",
        (),
        {
            "is_blocked": staticmethod(lambda *_a, **_k: False),
            "edge_interactables_between": staticmethod(lambda *_a, **_k: []),
        },
    )()
    game.ui_log = lambda *_a, **_k: None
    game.ui_event = lambda *_a, **_k: None
    game.ui_hero = lambda *_a, **_k: None
    game.ui_active_actor = lambda *_a, **_k: None

    combat = Combat(game)
    game.state = combat
    combat.base_order = [attacker_hero, champion_enemy, target_enemy]
    combat.round_queue = [attacker_hero, champion_enemy, target_enemy]
    combat.base_initiative[attacker_hero] = 15
    combat.base_initiative[champion_enemy] = 12
    combat.base_initiative[target_enemy] = 10

    dispatch_reactions(
        game,
        {
            "actor": attacker_hero,
            "target": target_enemy,
            "action_id": "hero_attack_melee",
            "action_tags": ["attack_melee"],
            "damage": 5,
        },
    )

    assert target_enemy.wounds == 0
    assert enfeebled_value(attacker_hero) == 0


def test_champion_redeemer_enfeebled_expires_after_attackers_next_turn(monkeypatch):
    champion = DummyHero(name="Champion", object_id="hero-champion", position=(0, 0))
    ally = DummyHero(name="Ally", object_id="hero-ally", position=(1, 0), wounds=5)
    enemy = DummyEnemy(name="Enemy", object_id="enemy-1", position=(0, 1))
    _add_champion_with_setup(champion, monkeypatch, cause="Redeemer")

    game = type("Game", (), {})()
    game.ui = DummyUI(["tak"])
    game.conn = DummyConn()
    game.heroes = [champion, ally]
    game.enemies = [enemy]
    game.board = type("Board", (), {})()
    game.ui_log = lambda *_a, **_k: None
    game.ui_event = lambda *_a, **_k: None
    game.ui_hero = lambda *_a, **_k: None
    game.ui_active_actor = lambda *_a, **_k: None

    combat = Combat(game)
    game.state = combat
    combat.base_order = [ally, champion, enemy]
    combat.round_queue = [ally, champion, enemy]
    combat.base_initiative[ally] = 15
    combat.base_initiative[champion] = 12
    combat.base_initiative[enemy] = 10

    dispatch_reactions(
        game,
        {
            "actor": enemy,
            "target": ally,
            "action_id": "enemy_attack_melee",
            "action_tags": ["attack_melee"],
            "damage": 5,
        },
    )

    assert enfeebled_value(enemy) == 2
    combat._expire_sourced_statuses(enemy)
    assert enfeebled_value(enemy) == 2
    combat._expire_sourced_statuses(enemy)
    assert enfeebled_value(enemy) == 0


def test_champion_liberator_step_is_optional(monkeypatch):
    champion = DummyHero(name="Champion", object_id="hero-champion", position=(0, 0))
    ally = DummyHero(name="Ally", object_id="hero-ally", position=(1, 0), wounds=4)
    enemy = DummyEnemy(name="Enemy", object_id="enemy-1", position=(0, 1))
    _add_champion_with_setup(champion, monkeypatch, cause="Liberator")
    ally.add_status(GrabbedStatus(source_id="enemy-1", maintain_turns_left=1))

    game = type("Game", (), {})()
    # 1) zgoda na reakcje, 2) odmowa Liberating Step
    game.ui = DummyUI(["tak", "nie"])
    game.conn = DummyConn()
    game.heroes = [champion, ally]
    game.enemies = [enemy]

    class Board:
        def __init__(self):
            self.moved = None

        def in_bounds(self, _pos):
            return True

        def get_neighbors(self, pos, include_position=False, diagonal=True):
            _ = include_position
            _ = diagonal
            x, y = pos
            return [(x + 1, y), (x, y + 1)]

        def can_enter(self, *_args, **_kwargs):
            return True

        def is_blocked(self, *_args, **_kwargs):
            return False

        def edge_interactables_between(self, *_args, **_kwargs):
            return []

        def move(self, src, dst):
            self.moved = (src, dst)

    board = Board()
    game.board = board
    game.ui_log = lambda *_a, **_k: None
    game.ui_event = lambda *_a, **_k: None
    game.ui_hero = lambda *_a, **_k: None
    game.ui_active_actor = lambda *_a, **_k: None

    combat = Combat(game)
    game.state = combat
    combat.base_order = [ally, champion, enemy]
    combat.round_queue = [ally, champion, enemy]
    combat.base_initiative[ally] = 15
    combat.base_initiative[champion] = 12
    combat.base_initiative[enemy] = 10

    dispatch_reactions(
        game,
        {
            "actor": enemy,
            "target": ally,
            "action_id": "enemy_attack_melee",
            "action_tags": ["attack_melee"],
            "damage": 4,
        },
    )

    assert ally.has_status("grabbed") is False
    assert board.moved is None
    assert ally.position == (1, 0)
