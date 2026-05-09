from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scenario_flow import load_scenario_flow
from scenario_session import ScenarioSession
from game import Game
from GameObjects.Interactables.hidden_cache import HiddenCache
from GameObjects.Interactables.skill_challenge import SkillChallenge
from GameObjects.events.base import EventContext
from GameObjects.events.magic.consumables.events import BrindlefordHealingHerbEvent
from GameObjects.items.equipment import create_equipment
from GameObjects.items.inventory import add_item, ensure_actor_inventory


class DummyConnection:
    def set_leds(self, *_args, **_kwargs):
        return None

    def leds_off(self, *_args, **_kwargs):
        return None

    def scan_board(self, *_args, **_kwargs):
        return (0, 0)

    def read_card(self, *_args, **_kwargs):
        return "DECLINE"


class SilentPrompt:
    def info(self, *_args, **_kwargs):
        return object()


def _iter_board_interactables(game: Game):
    for row in range(game.board.rows):
        for col in range(game.board.cols):
            pos = (col, row)
            for obj in game.board.interactables_at(pos):
                yield pos, obj


def _runtime_game_for_map(payload: dict[str, Any], map_id: str) -> Game:
    map_ref = next(item for item in payload["maps"] if item["map_id"] == map_id)
    return Game(
        conn=DummyConnection(),
        scenario=map_ref["source"],
        scenario_label=map_id,
    )


def test_ashen_oath_flow_loads_and_links_maps():
    payload = load_scenario_flow("ashen_oath")

    assert payload["scenario_id"] == "ashen_oath"
    assert payload["entry_map_id"] == "brindleford_square"
    assert len(payload["maps"]) == 5
    assert "to_burned_chapel" in payload["map_logic_index"]["brindleford_square"]["exits"]
    assert "from_ruins" in payload["map_logic_index"]["oath_crypt"]["anchors"]


def test_ashen_oath_story_events_declare_voiceover_audio():
    payload = load_scenario_flow("ashen_oath")
    story_actions = [
        action
        for event in payload["events"]
        for action in event["actions"]
        if action["type"] in {"show_prompt", "show_log"}
    ]

    assert story_actions
    assert all(str(action.get("audio") or "").startswith("audio/voiceover/") for action in story_actions)


def test_ashen_oath_runtime_dialogues_are_exported_for_voiceover_generation():
    prompts = (PROJECT_ROOT / "assets/ui_v2/ashen_oath/AUDIO_PROMPTS.md").read_text(encoding="utf-8")

    assert "Generated runtime dialogue prompts" in prompts
    assert "audio/voiceover/runtime_dialogue/brindleford_square_mara_fen" in prompts
    assert "audio/voiceover/runtime_dialogue/brindleford_square_nila_ashwick" in prompts
    assert "audio/voiceover/runtime_dialogue/old_mill_tovin_barrow" in prompts
    assert "Mara uznaje, ze naprawde probujecie pomoc wiosce" in prompts
    assert "audio/voiceover/runtime_dialogue/brindleford_square_vale_guards_shaken_intro_001.mp3" in prompts
    assert "audio/voiceover/runtime_dialogue/brindleford_square_public_square_address_intro_001.mp3" in prompts


def test_ashen_oath_has_main_and_optional_objectives():
    payload = load_scenario_flow("ashen_oath")
    objective_ids = {str(item.get("id") or "") for item in payload["objectives"]}

    assert "uncover_ashen_oath" in objective_ids
    assert {"free_the_acolyte", "recover_warden_medallion", "clear_miras_name"} <= objective_ids


def test_ashen_oath_all_npcs_have_image_and_voiceover_prompts():
    image_prompts = (PROJECT_ROOT / "assets/ui_v2/ashen_oath/IMAGE_PROMPTS.md").read_text(encoding="utf-8")
    audio_prompts = (PROJECT_ROOT / "assets/ui_v2/ashen_oath/AUDIO_PROMPTS.md").read_text(encoding="utf-8")
    manifest = json.loads((PROJECT_ROOT / "assets/ui_v2/ashen_oath/manifest.json").read_text(encoding="utf-8"))
    manifest_character_ids = set(manifest["characters"])
    missing: list[str] = []

    for scenario_path in sorted((PROJECT_ROOT / "scenarios").glob("ashen_oath_*.json")):
        map_id = scenario_path.stem.replace("ashen_oath_", "")
        scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
        for entry in scenario["objects"]:
            for instance in entry.get("instances", []):
                config = instance.get("config") or {}
                npc_id = str(config.get("npc_id") or "").strip()
                if not npc_id:
                    continue
                if npc_id not in manifest_character_ids:
                    missing.append(f"{map_id}:{npc_id}:manifest")
                if f"images/characters/{npc_id}.png" not in image_prompts:
                    missing.append(f"{map_id}:{npc_id}:image_prompt")
                if f"runtime_dialogue/{map_id}_{npc_id}_" not in audio_prompts:
                    missing.append(f"{map_id}:{npc_id}:voiceover_prompt")

    assert missing == []


def test_ashen_oath_player_cards_cover_six_person_party():
    cards_root = PROJECT_ROOT / "assets/ui_v2/ashen_oath/player_cards"
    expected = {"cedric", "freya", "kord", "christopher", "lorielen", "jimi"}

    assert {path.stem for path in (cards_root / "md").glob("*.md")} == expected
    assert {path.stem for path in (cards_root / "html").glob("*.html")} == expected
    assert (cards_root / "images/ashen_oath_party_header_6p.png").exists()


def test_hidden_cache_reveal_dispatches_scenario_object_revealed():
    dispatched: list[tuple[str, str | None, str | None]] = []

    class FakeSession:
        current_map_id = "hill_ruins"

        def dispatch_trigger(self, trigger, *, map_id=None, target_id=None, **_kwargs):
            dispatched.append((trigger, map_id, target_id))

    class FakeGame:
        scenario_session = FakeSession()

    cache = HiddenCache(cache_id="ash_memory_circle", hidden=True, description_on_reveal="memory")

    outcome, _message = cache.try_reveal(30)
    extra = cache.on_reveal(FakeGame())

    assert outcome in {"success", "critical_success"}
    assert extra == "memory"
    assert dispatched == [("object_revealed", "hill_ruins", "ash_memory_circle")]


def test_ashen_oath_golden_path_cache_reveal_sets_truth_and_unlocks_crypt():
    session = ScenarioSession(conn=DummyConnection(), scenario="ashen_oath")
    session.current_map_id = "hill_ruins"
    session._load_map("hill_ruins", entry_anchor_id=None, initial_load=False, place_party=False)
    assert session.current_game is not None
    session.current_game.player_prompt = SilentPrompt()

    caches = [
        obj
        for _pos, obj in _iter_board_interactables(session.current_game)
        if str(getattr(obj, "cache_id", "") or "") == "ash_memory_circle"
        and obj.__class__.__name__ == "HiddenCache"
    ]
    assert len(caches) == 1

    caches[0].try_reveal(30)
    caches[0].on_reveal(session.current_game)

    transition = session._find_transition(exit_id="to_oath_crypt", from_map_id="hill_ruins")
    assert session.global_flags["mira_truth_learned"] is True
    assert session.global_flags["mira_allied"] is True
    assert "clear_miras_name" in session.completed_objectives
    assert transition is not None
    assert session._conditions_pass(transition["conditions"], map_id="hill_ruins", target_id="to_oath_crypt")


def test_ashen_oath_campaign_npcs_load_as_interactables():
    payload = load_scenario_flow("ashen_oath")
    expected_by_map = {
        "brindleford_square": {
            "odran_vale",
            "elna_barrow",
            "tomas_reed",
            "mara_fen",
            "old_brann",
            "nila_ashwick",
            "bren_cale",
        },
        "old_mill": {"tovin_barrow"},
        "hill_ruins": {"mira_ashwane"},
        "oath_crypt": {"warden_serai", "odran_vale"},
    }

    for map_id, expected_ids in expected_by_map.items():
        game = _runtime_game_for_map(payload, map_id)
        npc_ids = {
            str(getattr(obj, "npc_id", "") or "").strip()
            for _pos, obj in _iter_board_interactables(game)
        }
        assert expected_ids <= npc_ids


def test_brindleford_social_scene_has_contextual_patrol_and_villagers():
    payload = load_scenario_flow("ashen_oath")
    game = _runtime_game_for_map(payload, "brindleford_square")
    npcs = {
        str(getattr(obj, "npc_id", "") or ""): obj
        for _pos, obj in _iter_board_interactables(game)
        if str(getattr(obj, "npc_id", "") or "")
    }
    challenges = [
        obj
        for _pos, obj in _iter_board_interactables(game)
        if obj.__class__.__name__ == "SkillChallenge"
    ]

    assert {"tomas_reed", "mara_fen", "old_brann", "nila_ashwick", "bren_cale"} <= set(npcs)
    patrol = next(challenge for challenge in challenges if getattr(challenge, "challenge_id", "") == "vale_guards_shaken")
    assert patrol.challenge_label == "Odciagnij uwage patrolu"
    assert patrol.name == "Odciagnij uwage patrolu"
    assert patrol.interaction_label == "Odciagnij uwage patrolu"
    assert "Celem nie jest upokorzenie" in patrol.intro
    mara_dialog = npcs["mara_fen"].dialog["start"]["options"][0]["skill_check"]["outcomes"]
    assert mara_dialog["critical_success"]["effects"][0]["item_id"] == "brindleford_healing_herb"
    child_dialog = npcs["nila_ashwick"].dialog["start"]["options"][0]
    assert "vale_guards_shaken" in child_dialog["conditions"]["any_flags"]
    sick_dialog = npcs["bren_cale"].dialog["start"]["options"][0]["skill_check"]
    assert sick_dialog["skill_id"] == "medicine"


def test_brindleford_has_extra_social_side_beats():
    payload = load_scenario_flow("ashen_oath")
    game = _runtime_game_for_map(payload, "brindleford_square")
    challenges = {
        str(getattr(obj, "challenge_id", "") or ""): obj
        for _pos, obj in _iter_board_interactables(game)
        if obj.__class__.__name__ == "SkillChallenge"
    }

    assert {"well_echo_read", "public_square_address"} <= set(challenges)
    well = challenges["well_echo_read"]
    assert well.skill_id == "occultism"
    assert "well_mark_hint" in well.outcome_flags["success"]
    speech = challenges["public_square_address"]
    assert speech.skill_id == "performance"
    assert "villagers_willing_to_talk" in speech.outcome_flags["success"]
    assert "crowd_intimidated" in speech.outcome_flags["critical_failure"]


def test_skill_challenge_outcome_flags_and_prompt(monkeypatch):
    class FakeUI:
        enabled = True
        info_calls = []

        def prompt_info(self, *args, **kwargs):
            self.info_calls.append({"args": args, **kwargs})
            return "ok"

    class FakeGame:
        ui = FakeUI()
        scenario_session = type("Session", (), {"global_flags": {}})()

    monkeypatch.setattr(
        "GameObjects.Interactables.skill_challenge.resolve_skill_check_with_sources",
        lambda **_kwargs: type("Resolution", (), {"outcome": "critical_success", "total": 25})(),
    )
    challenge = SkillChallenge(
        challenge_id="patrol",
        label="Odciagnij uwage patrolu",
        intro="Kontekst.",
        outcome_messages={"critical_success": "Patrol ustepuje."},
        outcome_flags={"critical_success": ["patrol_shifted"]},
    )

    message = challenge.action_attempt(actor=object(), game=FakeGame())

    assert "Patrol ustepuje" in message
    assert FakeGame.scenario_session.global_flags["patrol_shifted"] is True
    assert len(FakeGame.ui.info_calls) == 2


def test_brindleford_healing_herb_heals_one_and_is_consumed():
    class Actor:
        def __init__(self):
            self.inventory = []
            self.wounds = 3

        def heal(self, amount):
            self.wounds = max(0, self.wounds - int(amount))

    actor = Actor()
    item = create_equipment("brindleford_healing_herb")
    assert item is not None
    add_item(actor, item)

    result = BrindlefordHealingHerbEvent().execute(EventContext(game=object(), actor=actor))

    assert result.success is True
    assert result.consumed_action is True
    assert result.data["healed"] == 1
    assert actor.wounds == 2
    assert "brindleford_healing_herb" not in {
        str(getattr(item, "item_id", "")) for item in ensure_actor_inventory(actor)
    }


def test_ashen_oath_maps_have_six_valid_room_start_positions():
    payload = load_scenario_flow("ashen_oath")

    for map_ref in payload["maps"]:
        game = _runtime_game_for_map(payload, map_ref["map_id"])
        starts = [tuple(pos) for pos in game.scenario["starting_positions"]]
        assert len(starts) == 6
        assert len(set(starts)) == 6
        for start in starts:
            assert game.board.in_bounds(start)
            assert game.board.rooms_at(start), f"{map_ref['map_id']} start {start} is outside rooms"
            occupant = game.board.occupant_at(start)
            assert occupant is None, f"{map_ref['map_id']} start {start} is occupied"


def test_ashen_oath_maps_use_corner_marker_setup_not_full_board_highlight():
    payload = load_scenario_flow("ashen_oath")

    for map_ref in payload["maps"]:
        scenario_path = PROJECT_ROOT / "scenarios" / f"{map_ref['source']}.json"
        data = __import__("json").loads(scenario_path.read_text(encoding="utf-8"))
        assert data.get("setup_corner_markers") is True
        assert "setup_full_board" not in data


def test_ashen_oath_maps_include_role_skill_moments():
    payload = load_scenario_flow("ashen_oath")
    expected_challenges = {
        "brindleford_square": {
            "vale_guards_shaken": "diplomacy",
            "well_echo_read": "occultism",
            "public_square_address": "performance",
        },
        "burned_chapel": {"chapel_tracks_read": "survival"},
        "old_mill": {"mill_beam_moved": "athletics"},
        "hill_ruins": {"ash_ritual_interpreted": "occultism"},
        "oath_crypt": {"serai_liturgy_recited": "religion"},
    }

    for map_id, expected in expected_challenges.items():
        game = _runtime_game_for_map(payload, map_id)
        challenges = {
            str(getattr(obj, "challenge_id", "") or ""): str(getattr(obj, "skill_id", "") or "")
            for _pos, obj in _iter_board_interactables(game)
            if obj.__class__.__name__ == "SkillChallenge"
        }
        assert expected.items() <= challenges.items()

    mill = _runtime_game_for_map(payload, "old_mill")
    traps = [
        obj
        for _pos, obj in _iter_board_interactables(mill)
        if obj.__class__.__name__ == "TrapTile"
    ]
    assert any(int(getattr(trap, "trap_disable_dc", 0) or 0) >= 15 for trap in traps)
