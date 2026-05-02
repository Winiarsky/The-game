from __future__ import annotations

import copy
import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from hero import Hero
from scenario_flow import load_scenario_flow, validate_scenario_flow
from scenario_session import ScenarioSession
from statuses.base import Status
import ui_client


class DummyConnection:
    def set_leds(self, *_args, **_kwargs):
        return None

    def leds_off(self, *_args, **_kwargs):
        return None

    def scan_board(self, acceptable_responses=None, *_args, **_kwargs):
        if acceptable_responses:
            return tuple(acceptable_responses[0])
        return (0, 0)

    def read_card(self, *_args, **_kwargs):
        return "DECLINE"


class RecordingUI:
    def __init__(self):
        self.enabled = True
        self.events: list[tuple[str, dict[str, object]]] = []

    def send_event(self, event_type: str, payload: dict[str, object]) -> bool:
        self.events.append((str(event_type), dict(payload)))
        return True

    def prompt_info(self, *_args, **_kwargs):
        self.events.append(("prompt_info", {"title": _args[0] if _args else ""}))
        return "ok"


def _find_exit(game, exit_id: str):
    board = game.board
    for row in range(board.rows):
        for col in range(board.cols):
            pos = (col, row)
            for obj in list(board.interactables_at(pos) or []):
                if str(getattr(obj, "exit_id", "")).strip() == exit_id:
                    return obj
    raise AssertionError(f"Brak exit_id={exit_id}")


def _find_cache(game, cache_id: str):
    board = game.board
    for row in range(board.rows):
        for col in range(board.cols):
            pos = (col, row)
            for obj in list(board.interactables_at(pos) or []):
                if str(getattr(obj, "cache_id", "")).strip() == cache_id:
                    return obj
    raise AssertionError(f"Brak cache_id={cache_id}")


def test_bandit_cave_flow_loads_and_validates_logic_refs():
    payload = load_scenario_flow("bandit_cave")

    assert payload["scenario_id"] == "bandit_cave"
    assert payload["entry_map_id"] == "cave_entrance"
    assert "secret_treasure" in payload["map_logic_index"]["cave_entrance"]["exits"]
    assert "from_cave_docks" in payload["map_logic_index"]["smuggler_docks"]["anchors"]


def test_bandit_cave_flow_declares_voiceover_assets_on_story_events():
    payload = load_scenario_flow("bandit_cave")
    story_actions = [
        action
        for event in payload["events"]
        for action in event["actions"]
        if action["type"] in {"show_prompt", "show_log"}
    ]

    assert story_actions
    assert all(str(action.get("audio") or "").startswith("audio/voiceover/") for action in story_actions)


def test_flow_validator_rejects_missing_transition_exit():
    payload = load_scenario_flow("bandit_cave")
    broken = copy.deepcopy(payload)
    broken["transitions"][0]["exit_id"] = "does_not_exist"

    try:
        validate_scenario_flow(broken)
    except ValueError as exc:
        assert "does_not_exist" in str(exc)
    else:
        raise AssertionError("Walidacja powinna odrzucić nieistniejący exit_id.")


def test_scenario_session_restores_map_snapshot_after_round_trip(monkeypatch):
    session = ScenarioSession(conn=DummyConnection(), scenario="bandit_cave")
    monkeypatch.setattr(session, "_confirm_pending_transition", lambda _transition: True)
    session._load_map("cave_entrance", entry_anchor_id=None, initial_load=True)  # noqa: SLF001
    assert session.current_game is not None

    hero = Hero()
    hero.name = "Tester"
    hero.character_id = "tester"
    session.heroes = [hero]
    session.current_game.heroes = [hero]
    session._place_party_on_map(session.current_game, anchor_id="front_gate")  # noqa: SLF001

    secret_exit = _find_exit(session.current_game, "secret_treasure")
    secret_exit.revealed = True
    session.global_flags["secret_passage_found"] = True
    session.current_game.enemies[0].hp = 0

    ok, _message = session.request_transition(
        exit_id="secret_treasure",
        trigger_type="exit_interact",
        source_map_id="cave_entrance",
        actor=hero,
        source_object=secret_exit,
    )
    assert ok is True
    session._apply_pending_transition()  # noqa: SLF001
    assert session.current_map_id == "treasure_room"

    treasure_exit = _find_exit(session.current_game, "return_to_cave")
    ok, _message = session.request_transition(
        exit_id="return_to_cave",
        trigger_type="exit_enter",
        source_map_id="treasure_room",
        actor=hero,
        source_object=treasure_exit,
    )
    assert ok is True
    session._apply_pending_transition()  # noqa: SLF001

    assert session.current_map_id == "cave_entrance"
    restored_secret_exit = _find_exit(session.current_game, "secret_treasure")
    assert restored_secret_exit.revealed is True
    assert any(int(getattr(enemy, "hp", 0) or 0) <= 0 for enemy in session.current_game.enemies)


def test_escape_ship_requires_cleared_docks_and_then_finishes_scenario():
    session = ScenarioSession(conn=DummyConnection(), scenario="bandit_cave")
    session.current_map_id = "smuggler_docks"
    session._load_map("smuggler_docks", entry_anchor_id="from_cave_docks", initial_load=False)  # noqa: SLF001
    assert session.current_game is not None

    hero = Hero()
    hero.name = "Captain"
    hero.character_id = "captain"
    session.heroes = [hero]
    session.current_game.heroes = [hero]
    session._place_party_on_map(session.current_game, anchor_id="from_cave_docks")  # noqa: SLF001

    ship_exit = _find_exit(session.current_game, "escape_ship")
    ok, message = session.request_transition(
        exit_id="escape_ship",
        trigger_type="exit_interact",
        source_map_id="smuggler_docks",
        actor=hero,
        source_object=ship_exit,
    )
    assert ok is False
    assert "jeszcze dostępne" in message
    assert session.finished is False

    for enemy in session.current_game.enemies:
        enemy.hp = 0
    session.dispatch_trigger("combat_end", map_id="smuggler_docks")
    assert session.global_flags["docks_cleared"] is True

    ok, _message = session.request_transition(
        exit_id="escape_ship",
        trigger_type="exit_interact",
        source_map_id="smuggler_docks",
        actor=hero,
        source_object=ship_exit,
    )
    assert ok is True
    assert session.finished is True
    assert session.global_flags["ship_escaped"] is True


def test_docks_first_descent_success_keeps_party_in_exploration(monkeypatch):
    session = ScenarioSession(conn=DummyConnection(), scenario="bandit_cave")
    monkeypatch.setattr(session, "_confirm_pending_transition", lambda _transition: True)
    session._load_map("cave_entrance", entry_anchor_id=None, initial_load=True)  # noqa: SLF001
    assert session.current_game is not None

    hero = Hero()
    hero.name = "Sneak"
    hero.character_id = "sneak"
    session.heroes = [hero]
    session.current_game.heroes = [hero]
    session._place_party_on_map(session.current_game, anchor_id="front_gate")  # noqa: SLF001

    monkeypatch.setattr(
        "scenario_session.resolve_skill_check_with_sources",
        lambda **_kwargs: SimpleNamespace(outcome="success", total=17, dc=15),
    )

    docks_exit = _find_exit(session.current_game, "to_docks")
    ok, _message = session.request_transition(
        exit_id="to_docks",
        trigger_type="exit_enter",
        source_map_id="cave_entrance",
        actor=hero,
        source_object=docks_exit,
    )
    assert ok is True
    session._apply_pending_transition()  # noqa: SLF001

    assert session.current_map_id == "smuggler_docks"
    assert session.global_flags["docks_stealth_all_success"] is True
    assert session.current_game.state.__class__.__name__ == "HeroesTurn"


def test_docks_transition_waits_for_confirmation_before_stealth(monkeypatch):
    session = ScenarioSession(conn=DummyConnection(), scenario="bandit_cave")
    session._load_map("cave_entrance", entry_anchor_id=None, initial_load=True)  # noqa: SLF001
    assert session.current_game is not None

    hero = Hero()
    hero.name = "Sneak"
    hero.character_id = "sneak"
    session.heroes = [hero]
    session.current_game.heroes = [hero]
    session._place_party_on_map(session.current_game, anchor_id="front_gate")  # noqa: SLF001

    calls: list[str] = []

    def _choice(*_args, **_kwargs):
        calls.append("confirm")
        return "confirm"

    def _skill_check(**_kwargs):
        calls.append("stealth")
        return SimpleNamespace(outcome="success", total=17, dc=15)

    session.current_game.player_prompt.choice = _choice  # type: ignore[method-assign]
    monkeypatch.setattr("scenario_session.resolve_skill_check_with_sources", _skill_check)
    monkeypatch.setattr(session, "_run_map_setup", lambda *_args, **_kwargs: None)

    docks_exit = _find_exit(session.current_game, "to_docks")
    docks_exit.requires_confirmation = True
    ok, _message = session.request_transition(
        exit_id="to_docks",
        trigger_type="exit_enter",
        source_map_id="cave_entrance",
        actor=hero,
        source_object=docks_exit,
    )

    assert ok is True
    assert calls == []

    session._apply_pending_transition()  # noqa: SLF001

    assert calls[:2] == ["confirm", "stealth"]
    assert session.current_map_id == "smuggler_docks"


def test_docks_transition_does_not_prompt_for_confirmation_by_default(monkeypatch):
    session = ScenarioSession(conn=DummyConnection(), scenario="bandit_cave")
    session._load_map("cave_entrance", entry_anchor_id=None, initial_load=True)  # noqa: SLF001
    assert session.current_game is not None

    hero = Hero()
    hero.name = "Sneak"
    hero.character_id = "sneak"
    session.heroes = [hero]
    session.current_game.heroes = [hero]
    session._place_party_on_map(session.current_game, anchor_id="front_gate")  # noqa: SLF001

    calls: list[str] = []
    session.current_game.player_prompt.choice = lambda *_args, **_kwargs: calls.append("confirm") or "confirm"  # type: ignore[method-assign]
    monkeypatch.setattr(
        "scenario_session.resolve_skill_check_with_sources",
        lambda **_kwargs: SimpleNamespace(outcome="success", total=17, dc=15),
    )
    monkeypatch.setattr(session, "_run_map_setup", lambda *_args, **_kwargs: None)

    docks_exit = _find_exit(session.current_game, "to_docks")
    ok, _message = session.request_transition(
        exit_id="to_docks",
        trigger_type="exit_enter",
        source_map_id="cave_entrance",
        actor=hero,
        source_object=docks_exit,
    )

    assert ok is True
    session._apply_pending_transition()  # noqa: SLF001

    assert calls == []
    assert session.current_map_id == "smuggler_docks"


def test_cancelled_docks_transition_rolls_hero_back_without_stealth(monkeypatch):
    session = ScenarioSession(conn=DummyConnection(), scenario="bandit_cave")
    session._load_map("cave_entrance", entry_anchor_id=None, initial_load=True)  # noqa: SLF001
    assert session.current_game is not None

    hero = Hero()
    hero.name = "Cautious"
    hero.character_id = "cautious"
    session.heroes = [hero]
    session.current_game.heroes = [hero]
    rollback_pos = (17, 10)
    exit_pos = (18, 9)
    session.current_game.board.place(hero, rollback_pos)
    session.current_game.board.move(rollback_pos, exit_pos)
    hero._movement_previous_position = rollback_pos

    session.current_game.player_prompt.choice = lambda *_args, **_kwargs: "cancel"  # type: ignore[method-assign]
    monkeypatch.setattr(
        "scenario_session.resolve_skill_check_with_sources",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("stealth should not run")),
    )

    docks_exit = _find_exit(session.current_game, "to_docks")
    docks_exit.requires_confirmation = True
    ok, _message = session.request_transition(
        exit_id="to_docks",
        trigger_type="exit_enter",
        source_map_id="cave_entrance",
        actor=hero,
        source_object=docks_exit,
    )
    assert ok is True

    session._apply_pending_transition()  # noqa: SLF001

    assert session.current_map_id == "cave_entrance"
    assert getattr(hero, "position", None) == rollback_pos
    assert session.global_flags.get("docks_stealth_challenge_resolved") is not True


def test_docks_first_descent_critical_failure_starts_combat_with_enemy_bonus(monkeypatch):
    session = ScenarioSession(conn=DummyConnection(), scenario="bandit_cave")
    monkeypatch.setattr(session, "_confirm_pending_transition", lambda _transition: True)
    session._load_map("cave_entrance", entry_anchor_id=None, initial_load=True)  # noqa: SLF001
    assert session.current_game is not None

    hero = Hero()
    hero.name = "Loud"
    hero.character_id = "loud"
    session.heroes = [hero]
    session.current_game.heroes = [hero]
    session._place_party_on_map(session.current_game, anchor_id="front_gate")  # noqa: SLF001

    monkeypatch.setattr(
        "scenario_session.resolve_skill_check_with_sources",
        lambda **_kwargs: SimpleNamespace(outcome="critical_failure", total=5, dc=15),
    )
    monkeypatch.setattr(Hero, "roll_for_initiative", lambda self: setattr(self, "initiative", 10) or 10)

    docks_exit = _find_exit(session.current_game, "to_docks")
    ok, _message = session.request_transition(
        exit_id="to_docks",
        trigger_type="exit_enter",
        source_map_id="cave_entrance",
        actor=hero,
        source_object=docks_exit,
    )
    assert ok is True
    session._apply_pending_transition()  # noqa: SLF001

    assert session.current_map_id == "smuggler_docks"
    assert session.global_flags["docks_stealth_critical_failure"] is True
    assert session.current_game.state.__class__.__name__ == "Combat"
    enemy = session.current_game.enemies[0]
    assert enemy.compute_modifier("initiative") == 2
    assert enemy.compute_modifier("attack_melee") == 2


def test_revealed_upper_cache_override_applies_when_treasure_room_loads():
    session = ScenarioSession(conn=DummyConnection(), scenario="bandit_cave")
    session.current_map_id = "smuggler_docks"
    session._load_map("smuggler_docks", entry_anchor_id="from_cave_docks", initial_load=False)  # noqa: SLF001

    session.reveal_object(
        "treasure_room",
        "upper_smuggler_cache",
        state_updates={"hidden": False, "revealed": True, "trap_armed": False},
    )
    session.current_map_id = "treasure_room"
    session._load_map("treasure_room", entry_anchor_id="from_cave_secret", initial_load=False)  # noqa: SLF001

    cache = _find_cache(session.current_game, "upper_smuggler_cache")
    assert cache.hidden is False
    assert cache.revealed is True
    assert cache.trap_armed is False


def test_initial_scenario_intro_waits_until_after_hero_setup(monkeypatch):
    original_ui = ui_client.get_ui_client()
    recording_ui = RecordingUI()
    ui_client.set_default_ui_client(recording_ui)

    from game import Game

    original_run_action = Game.run_action

    def _run_action(self, action_name: str, *args, **kwargs):
        if action_name == "choose_action":
            self.finished = True
            return None
        return original_run_action(self, action_name, *args, **kwargs)

    monkeypatch.setattr(Game, "run_action", _run_action)

    try:
        session = ScenarioSession(
            conn=DummyConnection(),
            scenario="bandit_cave",
            preselected_character_ids=["cedric"],
        )
        session.run_loop()
    finally:
        ui_client.set_default_ui_client(original_ui)

    meaningful = [
        (event_type, payload.get("message") or payload.get("prompt") or payload.get("title") or "")
        for event_type, payload in recording_ui.events
        if event_type in {"log", "info", "prompt_info", "narration"}
        and "Sesja debug:" not in str(payload.get("message") or payload.get("prompt") or payload.get("title") or "")
    ]
    assert meaningful

    setup_idx = next(
        idx for idx, (_event, message) in enumerate(meaningful) if "Ustawianie pozycji startowych bohaterów." in str(message)
    )
    start_idx = next(
        idx for idx, (_event, message) in enumerate(meaningful) if "Rozpoczyna się scenariusz:" in str(message)
    )
    map_entry_idx = next(
        idx for idx, (_event, message) in enumerate(meaningful) if "Wchodzicie na mapę:" in str(message)
    )

    assert setup_idx < start_idx
    assert setup_idx < map_entry_idx


def test_opening_exploration_state_clears_observable_from_starting_heroes():
    session = ScenarioSession(conn=DummyConnection(), scenario="bandit_cave")
    session.current_game = type("DummyGame", (), {"ui_hero": staticmethod(lambda *_a, **_k: None)})()

    hero = Hero()
    hero.add_status(Status(id="observable", label="Observable"))
    assert hero.has_status("observable") is True

    session.heroes = [hero]
    session._prepare_opening_exploration_state()  # noqa: SLF001

    assert hero.has_status("observable") is False
