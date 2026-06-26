import json

from dnd_board_game.actors import Faction
from dnd_board_game.combat import CombatStatus
from dnd_board_game.runtime.demo_mini_combat_loop import build_parser, run_demo


class FakeConnection:
    def __init__(self, scanned=None):
        self.events = []
        self.scanned = scanned

    def set_leds(self, positions, rgb_color):
        self.events.append(("set_leds", list(positions), list(rgb_color)))

    def leds_off(self):
        self.events.append(("leds_off",))

    def scan_board(self, acceptable_responses=None, *, timeout_s=None):
        self.events.append(("scan_board", list(acceptable_responses or [])))
        if isinstance(self.scanned, list):
            if not self.scanned:
                return None
            return self.scanned.pop(0)
        return self.scanned


def _args(tmp_path, *extra):
    parser = build_parser()
    return parser.parse_args(
        [
            "--board-backend",
            "none",
            "--session-id",
            "mini_combat_loop",
            "--observation-dir",
            str(tmp_path),
            "--step-delay",
            "0",
            "--max-rounds",
            "2",
            *extra,
        ]
    )


def _events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_demo_mini_combat_loop_none_backend_runs_hero_and_enemy_turns(tmp_path):
    result = run_demo(_args(tmp_path, "--hero-attack-roll", "14", "--hero-damage", "1", "--enemy-seed", "7"))

    assert any("Tura: Bohater" in message for message in result.messages)
    assert any("Tura: Goblin" in message for message in result.messages)
    assert any("Scenariusz: Zasadzka goblina." in message for message in result.messages)
    event_types = [event["event_type"] for event in _events(result.observation_path)]
    assert "scenario_loaded" in event_types
    assert "turn_started" in event_types
    assert "action_used" in event_types
    assert "enemy_action_selected" in event_types
    assert "turn_finished" in event_types


def test_demo_mini_combat_loop_finishes_when_goblin_is_defeated(tmp_path):
    result = run_demo(_args(tmp_path, "--hero-attack-roll", "14", "--hero-damage", "10", "--enemy-seed", "7"))

    assert result.final_state.status == CombatStatus.FINISHED
    assert result.final_state.winner == Faction.ALLY
    event_types = [event["event_type"] for event in _events(result.observation_path)]
    assert "combat_finished" in event_types


def test_demo_mini_combat_loop_stops_at_max_rounds(tmp_path):
    result = run_demo(_args(tmp_path, "--hero-attack-roll", "2", "--max-rounds", "1", "--enemy-seed", "7"))

    assert result.final_state.status == CombatStatus.STOPPED
    event_types = [event["event_type"] for event in _events(result.observation_path)]
    assert "combat_stopped" in event_types


def test_demo_mini_combat_loop_fake_led_sequence_and_scan_selection(tmp_path):
    connection = FakeConnection(scanned=(1, 0))
    args = _args(
        tmp_path,
        "--board-backend",
        "simulator",
        "--show-leds",
        "--hero-attack-roll",
        "14",
        "--hero-damage",
        "10",
    )

    result = run_demo(args, connection_factory=lambda args: connection)

    assert result.feedback_events >= 4
    assert connection.events[0][0] == "set_leds"
    scan_events = [event for event in connection.events if event[0] == "scan_board"]
    assert any((1, 0) in event[1] for event in scan_events)
    assert ("leds_off",) in connection.events
    event_types = [event["event_type"] for event in _events(result.observation_path)]
    assert "led_feedback_sent" in event_types
    assert "combat_finished" in event_types


def test_demo_mini_combat_loop_multi_actor_scenario_runs_more_than_two_actors(tmp_path):
    result = run_demo(
        _args(
            tmp_path,
            "--scenario",
            "content/scenarios/multi_actor_skirmish.json",
            "--ally-attack-roll",
            "hero=14",
            "--ally-attack-roll",
            "rogue=13",
            "--ally-damage",
            "hero=10",
            "--ally-damage",
            "rogue=10",
            "--enemy-seed",
            "7",
            "--max-rounds",
            "5",
        )
    )

    assert any("Scenariusz: Potyczka przy rozbitych skrzyniach." in message for message in result.messages)
    assert any("Tura: Bohater" in message for message in result.messages)
    assert any("Tura: Łotrzyca" in message for message in result.messages)
    assert any("Tura: Goblin C" in message for message in result.messages)
    event_types = [event["event_type"] for event in _events(result.observation_path)]
    assert "target_selected" in event_types
    assert "damage_applied" in event_types


def test_demo_mini_combat_loop_per_actor_roll_override_is_used(tmp_path):
    result = run_demo(
        _args(
            tmp_path,
            "--scenario",
            "content/scenarios/multi_actor_skirmish.json",
            "--ally-attack-roll",
            "hero=2",
            "--ally-attack-roll",
            "rogue=13",
            "--ally-damage",
            "rogue=10",
            "--max-rounds",
            "1",
        )
    )

    attack_events = [event for event in _events(result.observation_path) if event["event_type"] == "attack_resolved"]
    hero_attack = next(event for event in attack_events if event["payload"]["attacker_id"] == "hero")
    rogue_attack = next(event for event in attack_events if event["payload"]["attacker_id"] == "rogue")
    assert hero_attack["payload"]["natural_roll"] == 2
    assert rogue_attack["payload"]["natural_roll"] == 13


def test_demo_mini_combat_loop_turn_script_moves_attacks_moves_and_ends(tmp_path):
    result = run_demo(
        _args(
            tmp_path,
            "--scenario",
            "content/scenarios/movement_skirmish.json",
            "--ally-turn-script",
            "hero=move:1,0,attack:goblin_a,move:0,1,end",
            "--hero-attack-roll",
            "14",
            "--hero-damage",
            "1",
            "--enemy-seed",
            "7",
            "--max-rounds",
            "1",
        )
    )

    hero = next(actor for actor in result.final_state.actors if actor.id == "hero")
    assert hero.position.as_tuple() == (0, 1)
    event_types = [event["event_type"] for event in _events(result.observation_path)]
    assert "turn_intent_previewed" in event_types
    assert "turn_intent_confirmed" in event_types
    assert "movement_committed" in event_types
    assert "attack_previewed" in event_types


def test_demo_mini_combat_loop_turn_script_self_click_ends_turn(tmp_path):
    result = run_demo(
        _args(
            tmp_path,
            "--scenario",
            "content/scenarios/movement_skirmish.json",
            "--ally-turn-script",
            "hero=self",
            "--enemy-seed",
            "7",
            "--max-rounds",
            "1",
        )
    )

    event_types = [event["event_type"] for event in _events(result.observation_path)]
    assert any("Opcje aktora: Bohater" in message for message in result.messages)
    assert "turn_end_requested" in event_types


def test_demo_mini_combat_loop_second_click_on_different_tile_changes_preview(tmp_path):
    connection = FakeConnection(scanned=[(1, 0), (3, 1), (1, 0), (1, 1), (1, 1)])
    args = _args(
        tmp_path,
        "--scenario",
        "content/scenarios/multi_actor_skirmish.json",
        "--board-backend",
        "simulator",
        "--show-leds",
        "--hero-attack-roll",
        "14",
        "--hero-damage",
        "10",
        "--max-rounds",
        "1",
    )

    result = run_demo(args, connection_factory=lambda args: connection)

    target_events = [event for event in _events(result.observation_path) if event["event_type"] == "target_selected"]
    assert target_events[0]["payload"]["target_id"] == "goblin_b"


def test_demo_mini_combat_loop_first_playable_scene_setup_and_interaction(tmp_path):
    result = run_demo(
        _args(
            tmp_path,
            "--scenario",
            "content/scenarios/first_playable_scene.json",
            "--ally-turn-script",
            "hero=move:1,0,interact:ancient_crate,end",
            "--ally-check-roll",
            "hero=13",
            "--max-rounds",
            "8",
            "--enemy-seed",
            "7",
        )
    )

    assert any("Setup sceny" in message for message in result.messages)
    assert any("Cel sceny: Zabezpiecz starą skrzynię" in message for message in result.messages)
    event_types = [event["event_type"] for event in _events(result.observation_path)]
    assert "scene_started" in event_types
    assert "scene_setup_started" in event_types
    assert "scene_setup_confirmed" in event_types
    assert "interaction_options_shown" in event_types
    assert "interaction_previewed" in event_types
    assert "interaction_confirmed" in event_types
    assert "ability_check_requested" in event_types
    assert "ability_check_resolved" in event_types
    assert "scene_flag_set" in event_types
    assert "objective_completed" in event_types
    assert "scene_finished" in event_types


def test_demo_mini_combat_loop_failed_interaction_check_does_not_complete_flag_objective(tmp_path):
    result = run_demo(
        _args(
            tmp_path,
            "--scenario",
            "content/scenarios/first_playable_scene.json",
            "--ally-turn-script",
            "hero=move:1,0,interact:ancient_crate,end",
            "--ally-check-roll",
            "hero=1",
            "--max-rounds",
            "1",
            "--enemy-seed",
            "7",
        )
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert "ability_check_resolved" in event_types
    resolved = next(event for event in events if event["event_type"] == "ability_check_resolved")
    assert resolved["payload"]["success"] is False
    flag_event = next(event for event in events if event["event_type"] == "scene_flag_set")
    assert flag_event["payload"]["key"] == "crate_trap_missed"
    assert "objective_completed" not in event_types


def test_demo_mini_combat_loop_scene_setup_uses_board_clicks_for_hero_positions(tmp_path):
    connection = FakeConnection(scanned=[(1, 0), (0, 1), (5, 0), (3, 1), (2, 2), (2, 0), None])
    args = _args(
        tmp_path,
        "--scenario",
        "content/scenarios/first_playable_scene.json",
        "--board-backend",
        "simulator",
        "--show-leds",
        "--max-rounds",
        "1",
    )

    result = run_demo(args, connection_factory=lambda args: connection)

    hero = next(actor for actor in result.final_state.actors if actor.id == "hero")
    rogue = next(actor for actor in result.final_state.actors if actor.id == "rogue")
    assert hero.position.as_tuple() == (1, 0)
    assert rogue.position.as_tuple() == (0, 1)
    assert any("Bohater: ustaw figurkę" in message for message in result.messages)
    assert any("Łotrzyca: ustaw figurkę" in message for message in result.messages)
    setup_events = [event for event in _events(result.observation_path) if event["event_type"] == "scene_setup_step_confirmed"]
    assert any(event["payload"]["actor_id"] == "hero" and event["payload"]["selected_position"] == [1, 0] for event in setup_events)
    assert any(event["payload"]["phase"] == "scene_setup_enemies" for event in setup_events)


def test_demo_mini_combat_loop_invalid_interaction_does_not_request_confirmation_or_led_preview(tmp_path):
    connection = FakeConnection(scanned=[(0, 0), (0, 1), (5, 0), (3, 1), (2, 2), (2, 0), (2, 0), None])
    args = _args(
        tmp_path,
        "--scenario",
        "content/scenarios/first_playable_scene.json",
        "--board-backend",
        "simulator",
        "--show-leds",
        "--max-rounds",
        "1",
    )

    result = run_demo(args, connection_factory=lambda args: connection)

    assert any("Stara skrzynia jest poza zasięgiem interakcji" in message for message in result.messages)
    events = _events(result.observation_path)
    assert not any(event["event_type"] == "turn_intent_confirmation_scan" for event in events)
    assert not any(
        event["event_type"] == "led_feedback_sent" and event["payload"].get("phase") == "invalid"
        for event in events
    )
