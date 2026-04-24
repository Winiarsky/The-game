from pathlib import Path
import sys
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from action_events import ActionEventBus
from combat.damage_utils import remove_defeated_enemy


class _PlayerPromptStub:
    def __init__(self):
        self.calls = []

    def info(self, title, **kwargs):
        self.calls.append((title, kwargs))
        return "ok"


class _BoardStub:
    def __init__(self):
        self.occupants = {}
        self.interactables = {}

    def occupant_at(self, pos):
        return self.occupants.get(pos)

    def remove(self, pos):
        self.occupants.pop(pos, None)

    def add_interactable(self, interactable, position):
        self.interactables.setdefault(position, []).append(interactable)
        setter = getattr(interactable, "set_position", None)
        if callable(setter):
            setter(position)

    def interactables_at(self, position):
        return list(self.interactables.get(position, []))


class _EnemyStub:
    def __init__(self, *, name="Bandit Bruiser", pos=(12, 10), hp=0, loot_items=None, loot_cp=0):
        self.name = name
        self.position = pos
        self.hp = hp
        self.loot_items = list(loot_items or [])
        self.loot_cp = int(loot_cp)
        self.inventory = []
        self.coin_pouch = {}
        self.statuses = []

    def has_status(self, _status_id):
        return False


def test_damage_applied_event_shows_summary_prompt_for_hero_side_action():
    hero = SimpleNamespace(name="Cedric", object_id="hero-1", owner_id=None)
    enemy = SimpleNamespace(name="Bandit Bruiser", object_id="enemy-1", statuses=[])
    prompts = _PlayerPromptStub()
    narrations = []
    game = SimpleNamespace(
        heroes=[hero],
        enemies=[enemy],
        player_prompt=prompts,
        ui_event=lambda *_args, **_kwargs: True,
        ui_narration=lambda *args, **kwargs: narrations.append((args, kwargs)),
        refresh_ui_after_action=lambda *_args, **_kwargs: None,
    )

    bus = ActionEventBus(game)
    bus.emit_action(
        actor=hero,
        action_id="damage_applied",
        action_tags=["damage", "attack", "bow"],
        target=enemy,
        source_action="attack_long_bow",
        source_label="Longbow",
        damage=4,
        damage_components=[("piercing", 2), ("piercing", 2)],
        applied_statuses=["Prone"],
    )

    assert len(prompts.calls) == 1
    title, kwargs = prompts.calls[0]
    assert title == "Efekt akcji"
    assert kwargs["prompt_id"] == "combat.damage_applied_summary"
    assert "Cedric" in kwargs["summary"]
    assert "Bandit Bruiser" in kwargs["body_markdown"]
    assert "Długi łuk" in kwargs["body_markdown"]
    assert "Prone" in kwargs["body_markdown"]
    assert not narrations


def test_remove_defeated_enemy_uses_prompt_for_defeat_and_loot_when_available():
    board = _BoardStub()
    prompts = _PlayerPromptStub()
    item = SimpleNamespace(name="Sztylet", item_id="dagger", category="weapon")
    enemy = _EnemyStub(loot_items=[item], loot_cp=35)
    board.occupants[enemy.position] = enemy
    game = SimpleNamespace(
        board=board,
        enemies=[enemy],
        heroes=[],
        player_prompt=prompts,
        ui_log=lambda *_args, **_kwargs: None,
    )

    remove_defeated_enemy(game, enemy, source="attack_long_bow")

    assert len(prompts.calls) == 1
    title, kwargs = prompts.calls[0]
    assert title == "Przeciwnik pokonany"
    assert kwargs["prompt_id"] == "interaction.enemy_defeated_loot"
    assert "Bandit Bruiser" in kwargs["body_markdown"]
    assert "loot" in kwargs["body_markdown"].lower()
    assert "Jak zebrać loot" in kwargs["details_markdown"]
