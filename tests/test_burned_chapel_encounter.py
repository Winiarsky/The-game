from pathlib import Path
import sys
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from burned_chapel_encounter import add_seal_progress, ensure_state, present_chapel_overview, trigger_altar
from combat.damage_utils import cleanup_defeated_enemies
from scenario_flow import load_scenario_flow
from src.game import Game


class DummyConnection:
    def __init__(self):
        self.led_calls = []

    def set_leds(self, *args, **kwargs):
        self.led_calls.append((args, kwargs))

    def leds_off(self, *_args, **_kwargs):
        return None

    def scan_board(self, *_args, **_kwargs):
        return (0, 0)

    def read_card(self, *_args, **_kwargs):
        return "DECLINE"


def _interactable_ids(game):
    ids = set()
    for row in range(game.board.rows):
        for col in range(game.board.cols):
            for obj in game.board.cell_at((col, row)).interactables:
                ids.add(str(getattr(obj, "scenario_object_id", "") or getattr(obj, "cache_id", "") or ""))
                ids.add(obj.__class__.__name__)
    return ids


def test_burned_chapel_loads_board_interactions_before_boss_spawn():
    game = Game(conn=DummyConnection(), scenario="ashen_oath_burned_chapel")

    assert game.enemies == []
    ids = _interactable_ids(game)
    assert "charred_altar" in ids
    assert "chapel_confessional" in ids
    assert "chapel_statue_watcher" in ids
    assert "chapel_statue_bellbearer" in ids
    assert "chapel_statue_flamekeeper" in ids
    assert "chapel_statue_ash_saint" in ids
    assert "chapel_bell_rope" in ids
    assert "fallen_beam" in ids
    assert "chapel_overview" in ids
    assert "broken_oath_seal" in ids
    assert "TrapTile" in ids


def test_burned_chapel_direct_playtest_has_static_physical_setup_plan():
    game = Game(conn=DummyConnection(), scenario="ashen_oath_burned_chapel")

    plan = list(game.scenario.get("setup_plan") or [])

    assert game.requires_setup_phase() is True
    assert any("spalony ołtarz" in str(step.get("prompt", "")).lower() for step in plan)
    assert any("popielne wyziewy" in str(step.get("prompt", "")).lower() for step in plan)


def test_chapel_overview_marks_map_as_seen_and_highlights_key_leds():
    conn = DummyConnection()
    game = Game(conn=conn, scenario="ashen_oath_burned_chapel")

    msg = present_chapel_overview(game)

    assert "konfesjonał" in msg
    assert "posągi" in msg
    assert "belkę" in msg
    assert ensure_state(game)["overview_seen"] is True
    assert conn.led_calls


def test_altar_trigger_spawns_deacon_and_starts_combat():
    game = Game(conn=DummyConnection(), scenario="ashen_oath_burned_chapel")

    msg = trigger_altar(game)

    assert "Diakona" in msg
    assert {enemy.__class__.__name__ for enemy in game.enemies} == {"CharredDeacon"}
    assert game.enemies[0].position == (6, 6)
    assert ensure_state(game)["altar_triggered"] is True


def test_statue_before_altar_does_not_spawn_deacon_or_start_combat():
    game = Game(conn=DummyConnection(), scenario="ashen_oath_burned_chapel")
    statue = next(obj for obj in game.board.interactables_at((3, 6)) if obj.__class__.__name__ == "ChapelStatue")

    msg = statue.action_activate(None, game)

    assert "dopiero wtedy" in msg
    assert "ołtarz się przebudzi" in msg
    assert game.enemies == []
    assert ensure_state(game)["altar_triggered"] is False


def test_holy_water_can_only_be_used_once():
    game = Game(conn=DummyConnection(), scenario="ashen_oath_burned_chapel")
    altar = next(obj for obj in game.board.interactables_at((6, 5)) if obj.__class__.__name__ == "CharredAltar")
    actor = SimpleNamespace(inventory=[SimpleNamespace(item_id="holy_water", name="Woda swiecona")])

    first = altar.action_use_holy_water(actor, game)
    ensure_state(game)["last_seal_round"] = 999
    second = altar.action_use_holy_water(actor, game)

    assert "Zużywacie" in first
    assert "została już zużyta" in second
    assert ensure_state(game)["seal_progress"] == 1
    assert actor.inventory == []


def test_holy_water_requires_real_item():
    game = Game(conn=DummyConnection(), scenario="ashen_oath_burned_chapel")
    altar = next(obj for obj in game.board.interactables_at((6, 5)) if obj.__class__.__name__ == "CharredAltar")
    actor = SimpleNamespace(inventory=[])

    msg = altar.action_use_holy_water(actor, game)

    assert "Nie macie wody święconej" in msg
    assert ensure_state(game)["seal_progress"] == 0
    assert ensure_state(game)["holy_water_used"] is False


def test_holy_water_stack_decrements_when_quantity_is_present():
    game = Game(conn=DummyConnection(), scenario="ashen_oath_burned_chapel")
    altar = next(obj for obj in game.board.interactables_at((6, 5)) if obj.__class__.__name__ == "CharredAltar")
    item = SimpleNamespace(item_id="holy_water", name="Woda swiecona", quantity=2)
    actor = SimpleNamespace(inventory=[item])

    msg = altar.action_use_holy_water(actor, game)

    assert "Zużywacie" in msg
    assert item.quantity == 1
    assert actor.inventory == [item]


def test_deacon_revives_while_altar_is_unsealed():
    game = Game(conn=DummyConnection(), scenario="ashen_oath_burned_chapel")
    trigger_altar(game)
    deacon = game.enemies[0]
    deacon.hp = 0

    removed = cleanup_defeated_enemies(game, source="test")

    assert removed == 1
    assert deacon in game.enemies
    assert deacon.hp > 0
    assert ensure_state(game)["deacon_sustained_message_shown"] is True


def test_deacon_can_be_removed_after_altar_is_sealed():
    game = Game(conn=DummyConnection(), scenario="ashen_oath_burned_chapel")
    trigger_altar(game)
    deacon = game.enemies[0]
    state = ensure_state(game)
    state["seal_progress"] = 3
    state["altar_sealed"] = True
    deacon.hp = 0

    removed = cleanup_defeated_enemies(game, source="test")

    assert removed == 1
    assert deacon not in game.enemies
    assert ensure_state(game)["boss_defeated"] is True


def test_seal_progress_only_once_per_round():
    game = Game(conn=DummyConnection(), scenario="ashen_oath_burned_chapel")
    state = ensure_state(game)
    state["altar_triggered"] = True

    ok1, _msg1 = add_seal_progress(game, method="test")
    ok2, msg2 = add_seal_progress(game, method="test")

    assert ok1 is True
    assert ok2 is False
    assert state["seal_progress"] == 1
    assert "odrzuca kolejny rytuał" in msg2


def test_altar_hides_seal_actions_after_round_progress():
    game = Game(conn=DummyConnection(), scenario="ashen_oath_burned_chapel")
    altar = next(obj for obj in game.board.interactables_at((6, 5)) if obj.__class__.__name__ == "CharredAltar")
    state = ensure_state(game)
    state["altar_triggered"] = True

    add_seal_progress(game, method="test")

    action_ids = {action.id for action in altar.available_actions(None, game)}
    assert "seal_religion" not in action_ids
    assert "seal_occultism" not in action_ids
    assert "use_holy_water" not in action_ids
    assert "damage_altar" not in action_ids
    assert "leave" in action_ids


def test_ashen_oath_flow_has_burned_chapel_checkpoints():
    flow = load_scenario_flow("ashen_oath")
    events = {event["id"]: event for event in flow["events"]}

    chapel_intro_actions = events["chapel_intro"]["actions"]
    deacon_actions = events["charred_deacon_defeated"]["actions"]

    assert {"type": "checkpoint", "reason": "burned_chapel_entered"} in chapel_intro_actions
    assert {"type": "checkpoint", "reason": "charred_deacon_defeated"} in deacon_actions
