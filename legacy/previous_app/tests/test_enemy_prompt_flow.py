from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from board_grid import BoardGrid
from GameObjects.companions import build_animal_companion
from GameObjects.events.enemy.enemy_attack_melee_event import EnemyMeleeAttackEvent
from GameObjects.Enemies.goblin_warrior import GoblinWarrior
from GameObjects.events.base import EventContext
from GameObjects.events.enemy.enemy_move_event import EnemyMoveEvent
from GameObjects.events.enemy.enemy_strike_event import EnemyStrikeEvent
from combat.reactions.opportunity_attack import OpportunityAttack
from states.combat import Combat


class PromptUI:
    enabled = True
    allow_cli_fallback = False

    def __init__(self):
        self.info_calls = []

    def prompt_info(self, title, *, prompt_long=None, **_kwargs):
        self.info_calls.append({"title": title, "prompt_long": prompt_long})
        return "ok"


class DummyConn:
    def set_leds(self, *_args, **_kwargs):
        return None

    def scan_board(self, acceptable_responses=None):
        if acceptable_responses:
            return acceptable_responses[0]
        return None

    def leds_off(self):
        return None

    def read_card(self, *_args, **_kwargs):
        return "ACCEPT"


@dataclass
class DummyHero:
    name: str = "Cedric"
    object_id: str = "hero-1"
    ac: int = 15
    hp: int = 20
    max_hp: int = 20
    position: tuple[int, int] | None = (2, 1)
    statuses: list = field(default_factory=list)
    bonuses: list = field(default_factory=list)
    initiative: int = 10

    def __hash__(self):
        return hash(self.object_id)

    def set_position(self, pos):
        self.position = pos

    def apply_damage(self, amount, _damage_type="normal"):
        self.hp = max(0, int(self.hp) - int(amount))
        return self.hp, self.hp <= 0

    def has_status(self, status_id: str) -> bool:
        return any(str(getattr(item, "id", item) or "").strip().lower() == status_id for item in self.statuses)

    def reset_reactions(self):
        return None


@dataclass
class DummyOwner:
    name: str = "Ranger"
    object_id: str = "owner-1"
    level: int = 1


def _build_game(board: BoardGrid, heroes: list[DummyHero], enemies: list[object], ui: PromptUI):
    logs = []
    events = []
    hero_updates = []
    game = SimpleNamespace(
        board=board,
        heroes=heroes,
        enemies=enemies,
        ui=ui,
        conn=DummyConn(),
        ui_log=lambda message, **_kwargs: logs.append(str(message)),
        ui_event=lambda event_type, payload=None, **_k: events.append({"type": event_type, "payload": payload or {}}),
        ui_hero=lambda hero, **_kwargs: hero_updates.append({"hero": hero, **_kwargs}),
        ui_active_actor=lambda *_a, **_k: None,
        ui_idle_hint=lambda *_a, **_k: None,
    )
    game.logs = logs
    game.ui_events = events
    game.hero_updates = hero_updates
    game.events = SimpleNamespace(safe_emit_action=lambda **_kwargs: True)
    return game


def _place(board: BoardGrid, actors: list[object]) -> None:
    for actor in actors:
        pos = getattr(actor, "position", None)
        if pos is not None:
            board.place(actor, pos)


def test_combat_enemy_turn_blocks_on_start_and_skips_thinking_noise(monkeypatch):
    board = BoardGrid(rows=5, cols=5)
    ui = PromptUI()
    hero = DummyHero(position=(3, 3))
    enemy = GoblinWarrior(position=(1, 1))
    enemy.name = "Bandit Bruiser"
    enemy.initiative = 15
    game = _build_game(board, [hero], [enemy], ui)
    _place(board, [hero, enemy])

    combat = Combat(game)
    game.state = combat
    combat.base_order = [enemy]
    combat.round_queue = [enemy]
    combat.initiative_order = [enemy]
    combat._initiatives_ready = True

    monkeypatch.setattr("states.combat.get_behavior", lambda _behavior_id: (lambda *_a, **_k: 1))

    combat.choose_action()

    titles = [call["title"] for call in ui.info_calls]
    assert "Tura przeciwnika - Bandit Bruiser" in titles
    assert "Bandit Bruiser myśli..." not in titles
    assert not any("Bandit Bruiser myśli..." in msg for msg in game.logs)
    cancel_events = [event for event in game.ui_events if event["type"] == "prompt_scope_cancel"]
    assert {event["payload"]["scope_key"] for event in cancel_events} >= {
        "hero_turn:intent",
        "hero_turn:targeting",
        "hero_turn:resolution",
    }


def test_enemy_move_emits_prompt_before_and_after_move(monkeypatch):
    board = BoardGrid(rows=7, cols=7)
    ui = PromptUI()
    hero = DummyHero(position=(4, 1))
    enemy = GoblinWarrior(position=(1, 1))
    enemy.name = "Bandit Lookout"
    game = _build_game(board, [hero], [enemy], ui)
    _place(board, [hero, enemy])

    monkeypatch.setattr(
        "GameObjects.events.enemy.enemy_move_event.find_path",
        lambda *_a, **_k: [(1, 1), (2, 1), (3, 1)],
    )
    monkeypatch.setattr(
        "GameObjects.events.enemy.enemy_move_event.path_cost_feet",
        lambda path, *_a, **_k: max(0, (len(path) - 1) * 5),
    )
    monkeypatch.setattr(
        "GameObjects.events.enemy.enemy_move_event.trim_path_to_feet",
        lambda path, *_a, **_k: list(path),
    )

    result = EnemyMoveEvent().run(EventContext(game=game, actor=enemy))

    assert result.success is True
    titles = [call["title"] for call in ui.info_calls]
    assert "Ruch przeciwnika: Bandit Lookout" in titles
    assert "Ruch wykonany: Bandit Lookout" not in titles
    prompt_text = next(call["prompt_long"] for call in ui.info_calls if call["title"] == "Ruch przeciwnika: Bandit Lookout")
    assert "pole docelowe" in str(prompt_text or "").lower()
    assert any("Ruch wykonany: Bandit Lookout" in msg for msg in game.logs)


def test_enemy_strike_emits_roll_breakdown_and_result_prompts(monkeypatch):
    board = BoardGrid(rows=5, cols=5)
    ui = PromptUI()
    hero = DummyHero(position=(2, 1), ac=15, hp=20)
    enemy = GoblinWarrior(position=(1, 1))
    enemy.name = "Bandit Bruiser"
    game = _build_game(board, [hero], [enemy], ui)
    _place(board, [hero, enemy])

    rolls = iter([15, 4])
    monkeypatch.setattr("random.randint", lambda *_a, **_k: next(rolls))

    result = EnemyStrikeEvent().run(EventContext(game=game, actor=enemy, metadata={"forced_target": hero}))

    assert result.success is True
    titles = [call["title"] for call in ui.info_calls]
    assert "Atak przeciwnika: Bandit Bruiser" in titles
    assert "Wynik ataku: Bandit Bruiser" in titles
    assert "Rzut ataku: Bandit Bruiser" not in titles
    prepare_text = next(call["prompt_long"] for call in ui.info_calls if call["title"] == "Atak przeciwnika: Bandit Bruiser")
    assert "Enter rozstrzyga rzut ataku" in str(prepare_text or "")
    assert any("Bandit Bruiser atakuje Cedric" in msg for msg in game.logs)
    dice_events = [event for event in game.ui_events if event["type"] == "dice_roll"]
    assert [event["payload"]["roll_type"] for event in dice_events] == ["attack", "damage"]
    assert game.hero_updates
    assert game.hero_updates[-1]["hero"] is hero


def test_enemy_opportunity_attack_uses_blocking_prompts(monkeypatch):
    board = BoardGrid(rows=5, cols=5)
    ui = PromptUI()
    hero = DummyHero(position=(2, 1), ac=15, hp=20)
    enemy = GoblinWarrior(position=(1, 1))
    enemy.name = "Bandit Bruiser"
    game = _build_game(board, [hero], [enemy], ui)
    _place(board, [hero, enemy])

    rolls = iter([15, 4])
    monkeypatch.setattr("random.randint", lambda *_a, **_k: next(rolls))

    executed = OpportunityAttack().execute(enemy, {"actor": hero, "action_tags": ["move"]}, SimpleNamespace(game=game))

    assert executed is True
    titles = [call["title"] for call in ui.info_calls]
    assert "Wynik reakcji: Bandit Bruiser" in titles
    assert "Reakcja przeciwnika: Bandit Bruiser" not in titles
    assert any("Bandit Bruiser wykonuje atak okazyjny" in msg for msg in game.logs)


def test_enemy_strike_can_auto_target_animal_companion(monkeypatch):
    board = BoardGrid(rows=6, cols=6)
    ui = PromptUI()
    hero = DummyHero(position=(5, 5), ac=15, hp=20)
    enemy = GoblinWarrior(position=(1, 1))
    enemy.name = "Bandit Bruiser"
    owner = DummyOwner(object_id="hero-owner")
    companion = build_animal_companion(owner, "wolf")
    companion.set_position((2, 1))
    game = _build_game(board, [hero], [enemy], ui)
    game.state = SimpleNamespace(animal_companions={owner.object_id: companion})
    _place(board, [hero, enemy, companion])

    rolls = iter([16, 4])
    monkeypatch.setattr("random.randint", lambda *_a, **_k: next(rolls))

    result = EnemyStrikeEvent().run(EventContext(game=game, actor=enemy))

    assert result.success is True
    assert (result.data or {}).get("target") is companion
    assert int(companion.hp) < int(companion.max_hp)


def test_enemy_melee_attack_can_target_adjacent_animal_companion(monkeypatch):
    board = BoardGrid(rows=6, cols=6)
    ui = PromptUI()
    hero = DummyHero(position=(5, 5), ac=15, hp=20)
    enemy = GoblinWarrior(position=(1, 1))
    enemy.name = "Bandit Bruiser"
    owner = DummyOwner(object_id="hero-owner")
    companion = build_animal_companion(owner, "wolf")
    companion.set_position((2, 1))
    game = _build_game(board, [hero], [enemy], ui)
    game.state = SimpleNamespace(animal_companions={owner.object_id: companion})
    _place(board, [hero, enemy, companion])

    rolls = iter([18, 5])
    monkeypatch.setattr("random.randint", lambda *_a, **_k: next(rolls))

    result = EnemyMeleeAttackEvent().run(EventContext(game=game, actor=enemy))

    assert result.success is True
    assert int(companion.hp) < int(companion.max_hp)
