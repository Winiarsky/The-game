from pathlib import Path
import sys
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.Interactables.loot_pile import LootPile
from combat.damage_utils import cleanup_defeated_enemies, remove_defeated_enemy
from states.combat import Combat


class BoardStub:
    def __init__(self):
        self.rows = 6
        self.cols = 6
        self.occupants = {}
        self.interactables = {}
        self.removed = []

    def occupant_at(self, pos):
        return self.occupants.get(pos)

    def remove(self, pos):
        self.removed.append(pos)
        self.occupants.pop(pos, None)

    def add_interactable(self, interactable, position):
        self.interactables.setdefault(position, []).append(interactable)
        setter = getattr(interactable, "set_position", None)
        if callable(setter):
            setter(position)

    def interactables_at(self, position):
        return list(self.interactables.get(position, []))

    def remove_interactable(self, interactable, position):
        if interactable in self.interactables.get(position, []):
            self.interactables[position].remove(interactable)
            interactable.set_position(None)


class EnemyStub:
    def __init__(self, *, pos=(1, 1), hp=0, loot_items=None, loot_cp=0):
        self.position = pos
        self.hp = hp
        self.loot_items = list(loot_items or [])
        self.loot_cp = int(loot_cp)
        self.inventory = []
        self.coin_pouch = {}
        self.statuses = []

    def has_status(self, status_id):
        return False


class PromptRecorder:
    def __init__(self, answers=None):
        self.card_calls = []
        self.choice_calls = []
        self.answers = list(answers or [])

    def card(self, **kwargs):
        self.card_calls.append(kwargs)
        return True

    def choice(self, title, **kwargs):
        self.choice_calls.append({"title": title, **kwargs})
        if self.answers:
            return self.answers.pop(0)
        return "stash_all"


def test_remove_defeated_enemy_drops_loot_pile_and_removes_enemy():
    board = BoardStub()
    item = SimpleNamespace(name="Sztylet", item_id="dagger", category="weapon")
    enemy = EnemyStub(loot_items=[item], loot_cp=35)
    board.occupants[enemy.position] = enemy
    logs = []
    game = SimpleNamespace(board=board, enemies=[enemy], heroes=[], ui_log=lambda message, **kwargs: logs.append((message, kwargs)))

    result = remove_defeated_enemy(game, enemy, source="test")

    assert result["removed_from_list"] is True
    assert result["removed_from_board"] is True
    assert result["loot_dropped"] == 2
    assert enemy not in game.enemies
    assert enemy.position is None
    assert (1, 1) in board.removed
    piles = [obj for obj in board.interactables_at((1, 1)) if isinstance(obj, LootPile)]
    assert len(piles) == 1
    loot_ids = {getattr(item, "item_id", None) for item in piles[0].loot_items}
    assert "dagger" in loot_ids
    currency_entries = [
        entry
        for entry in piles[0].loot_items
        if isinstance(entry, dict) and str(entry.get("kind", "")).lower() == "currency_cp"
    ]
    assert currency_entries and int(currency_entries[0].get("amount_cp", 0) or 0) == 35
    assert logs
    message, kwargs = logs[-1]
    assert "zostaje loot" in message.lower()
    communication = kwargs.get("communication") or {}
    assert "Jak zebrać loot" in str(communication.get("details_markdown") or "")


def test_remove_defeated_enemy_refreshes_combat_initiative_before_prompt():
    board = BoardStub()
    enemy = EnemyStub(hp=-4)
    enemy.name = "Bandit Lookout"
    enemy.max_hp = 6
    enemy.object_id = "enemy-lookout"
    board.occupants[enemy.position] = enemy

    captured = []
    prompt_calls = []
    game = SimpleNamespace(
        board=board,
        enemies=[enemy],
        heroes=[],
        ui=SimpleNamespace(enabled=True),
        ui_event=lambda event_type, payload: captured.append((event_type, payload)),
        ui_log=lambda *_args, **_kwargs: None,
        player_prompt=SimpleNamespace(info=lambda title, **kwargs: prompt_calls.append((title, kwargs)) or "ok"),
    )
    combat = Combat(game)
    game.state = combat
    combat.base_order = [enemy]
    combat.round_queue = [enemy]
    combat.base_initiative[enemy] = 7

    result = remove_defeated_enemy(game, enemy, source="test")

    assert result["removed_from_list"] is True
    assert enemy not in game.enemies
    initiative_events = [payload for event_type, payload in captured if event_type == "initiative"]
    assert initiative_events
    assert initiative_events[-1]["order"] == []
    assert combat.base_order == []
    assert combat.round_queue == []
    assert prompt_calls
    assert "Zdejmij figurkę" in prompt_calls[0][1]["body_markdown"]


def test_loot_pile_pickup_names_loot_in_action_and_result_prompt():
    item = SimpleNamespace(name="Dogslicer", item_id="dogslicer", category="weapon")
    pile = LootPile(
        loot_items=[
            item,
            {"kind": "currency_cp", "amount_cp": 35},
        ]
    )
    pile.set_position((2, 3))
    prompt = PromptRecorder()
    hero = SimpleNamespace(name="Valeros", inventory=[], weapon_loadout=[], coin_pouch={})
    game = SimpleNamespace(board=BoardStub(), player_prompt=prompt)

    actions = pile.available_actions()

    assert len(actions) == 1
    assert "Dogslicer" in actions[0].description
    assert "3 sp, 5 cp" in actions[0].description

    message = pile._pickup_handler(pile, hero, game, {})

    assert "Dogslicer" in message
    assert "3 sp, 5 cp" in message
    assert len(prompt.card_calls) == 1
    card = prompt.card_calls[0]
    assert card["title"] == "Loot podniesiony"
    assert card["ack_required"] is True
    assert card["pause_policy"] == "ack"
    assert "Dogslicer" in str(card["body_markdown"])
    assert "3 sp, 5 cp" in str(card["body_markdown"])
    assert getattr(game, "party_stash", []) == [item]
    assert getattr(game, "party_coin_pouch", {}).get("sp") == 3
    assert getattr(game, "party_coin_pouch", {}).get("cp") == 5


def test_loot_pile_pickup_can_assign_selected_item_to_actor_before_stashing_rest():
    dogslicer = SimpleNamespace(name="Dogslicer", item_id="dogslicer", category="weapon")
    shortbow = SimpleNamespace(name="Shortbow", item_id="shortbow", category="weapon")
    pile = LootPile(loot_items=[dogslicer, shortbow])
    pile.set_position((2, 3))
    prompt = PromptRecorder(answers=["take:0", "stash_all"])
    hero = SimpleNamespace(name="Valeros", inventory=[], weapon_loadout=[], coin_pouch={})
    game = SimpleNamespace(board=BoardStub(), player_prompt=prompt)

    message = pile._pickup_handler(pile, hero, game, {})

    assert "Dogslicer" in message
    assert dogslicer in hero.inventory
    assert getattr(game, "party_stash", []) == [shortbow]
    assert len(prompt.choice_calls) == 2


def test_cleanup_defeated_enemies_removes_only_dead_targets():
    board = BoardStub()
    dead_enemy = EnemyStub(pos=(1, 1), hp=0, loot_cp=10)
    live_enemy = EnemyStub(pos=(2, 2), hp=6)
    board.occupants[(1, 1)] = dead_enemy
    board.occupants[(2, 2)] = live_enemy
    game = SimpleNamespace(board=board, enemies=[dead_enemy, live_enemy], heroes=[])

    removed = cleanup_defeated_enemies(game, source="cleanup:test")

    assert removed == 1
    assert dead_enemy not in game.enemies
    assert live_enemy in game.enemies
    piles = [obj for obj in board.interactables_at((1, 1)) if isinstance(obj, LootPile)]
    assert len(piles) == 1


def test_combat_end_loot_all_collects_remaining_piles_to_party_stash():
    board = BoardStub()
    dogslicer = SimpleNamespace(name="Dogslicer", item_id="dogslicer", category="weapon")
    pile = LootPile(loot_items=[dogslicer, {"kind": "currency_cp", "amount_cp": 12}])
    board.add_interactable(pile, (1, 1))
    hero = SimpleNamespace(name="Valeros", position=(0, 0), inventory=[], weapon_loadout=[])
    prompt = PromptRecorder(answers=["stash_all"])
    game = SimpleNamespace(
        board=board,
        heroes=[hero],
        enemies=[],
        player_prompt=prompt,
        ui_log=lambda *_args, **_kwargs: None,
    )
    combat = Combat(game)

    combat._offer_collect_remaining_loot()

    assert board.interactables_at((1, 1)) == []
    assert getattr(game, "party_stash", []) == [dogslicer]
    assert getattr(game, "party_coin_pouch", {}).get("sp") == 1
    assert getattr(game, "party_coin_pouch", {}).get("cp") == 2
