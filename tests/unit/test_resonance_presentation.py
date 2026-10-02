"""One authoritative projection drives the v03 screen and physical panel."""
from copy import deepcopy
import json
from pathlib import Path

from dnd_board_game.combat.charge_encounter import ChargeEncounter
from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.hardware.led_palette import LedColor, RGBColor
from dnd_board_game.hardware.resonance_feedback import ResonanceBoardView, resonance_feedback
from dnd_board_game.ui.board_panel_symbols import rune_slot
from dnd_board_game.ui.resonance import controls, presentation
from tests.unit.test_resonance_combat import game
from dnd_board_game.world import Coordinate


def relations_game(hero: str = "garran", companions: tuple[str, ...] = ()) -> ChargeEncounter:
    engine = game(hero, companions)
    engine.s.version = 2
    engine.s.profile = "rune_relations_v03"
    catalog = Path(__file__).resolve().parents[2] / "content/print/rune_relations_v03/catalog.json"
    engine.catalog = json.loads(catalog.read_text(encoding="utf-8"))
    return engine


def led_colors(board_view: ResonanceBoardView) -> dict[Coordinate, RGBColor]:
    return {pos: frame.color for frame in resonance_feedback(board_view).frames for pos in frame.positions}


def test_single_cost_preview_and_memory_use_the_previous_runes() -> None:
    engine = relations_game()
    engine.add_rune("garran", "Wieża")
    engine.add_rune("garran", "Schody")
    assert engine.choose("breaking_strike")
    before = deepcopy(engine.s.as_payload())
    view, board = presentation(engine)
    assert engine.s.as_payload() == before
    assert view["profile"] == "rune_relations_v03" and view["relations"]
    assert view["decision"]["cost"] == 5
    assert "base_cost" not in view["decision"] and "mode" not in view["decision"]
    assert all("base_cost" not in power and "enhanced_cost" not in power for power in view["powers"])
    assert not {26, 27} & controls(engine).keys()
    preview = view["decision"]["resonance"]
    assert preview["transition"] == "continue"
    assert len(preview["active_bonuses"]) == 2
    assert [entry["rune"] for entry in preview["memory_after"]] == ["Wieża", "Schody", "Grot"]
    assert view["chain"]["bonuses"] == []
    assert view["chain"]["next_runes"] == ["Grot", "Oko", "Błysk", "Fala"]
    assert board.selected_slot == rune_slot("Grot")


def test_mismatch_warning_and_leds_share_the_same_preview() -> None:
    engine = relations_game()
    engine.add_rune("garran", "Wieża")
    engine.add_rune("garran", "Oko")
    view, board = presentation(engine)
    power = next(power for power in view["powers"] if power["id"] == "second_wind")
    assert power["resonance"]["transition"] == "reset"
    assert (power["slot"], "reset") in board.action_cues
    assert led_colors(board)[panel_position(power["slot"])] == tuple(round(value * .65) for value in LedColor.PANEL_RESONANCE_RESET)
    assert engine.choose("second_wind")
    view, board = presentation(engine)
    assert view["decision"]["resonance"]["active_bonuses"] == []
    assert led_colors(board)[panel_position(power["slot"])] == LedColor.MENU_WHITE


def test_finisher_requires_both_memory_and_a_legal_entry() -> None:
    engine = relations_game("brakka")
    engine.add_rune("brakka", "Wieża")
    engine.add_rune("brakka", "Błysk")
    view, board = presentation(engine)
    power = next(power for power in view["powers"] if power["id"] == "powerful_strike")
    assert power["disabled"]
    assert rune_slot("Grot") not in controls(engine)
    assert panel_position(rune_slot("Grot")) not in led_colors(board)
    assert power["resonance"]["missing_required_runes"] == []
    assert not power["resonance"]["continuity_allowed"]
    engine.add_rune("brakka", "Schody")
    view, board = presentation(engine)
    power = next(power for power in view["powers"] if power["id"] == "powerful_strike")
    assert not power["disabled"] and (power["slot"], "finisher") in board.action_cues


def test_reserved_runes_are_never_physical_commands_and_fala_is_nimras() -> None:
    for hero in ("garran", "brakka", "mira", "dagna", "lorian", "nimra", "erynd"):
        view, board = presentation(relations_game(hero))
        assert len(view["reserved_runes"]) == 9
        for rune in view["reserved_runes"]:
            assert rune_slot(rune) not in board.action_slots
            assert rune_slot(rune) not in {control["slot"] for control in view["controls"]}
            assert view["rune_icons"][rune]
        wave = [power for power in view["powers"] if power["rune"] == "Fala"]
        assert bool(wave) == (hero == "nimra")


def test_followup_ally_selection_projects_target_and_confirmation() -> None:
    engine = relations_game("garran", ("mira",))
    engine.s.phase = "task"
    engine.s.task = dict(type="bonus_target", source="garran", targets=["mira"],
                         dice=[dict(count=1, sides=6)], label="Żar odnowy", target=None)
    view, board = presentation(engine)
    assert board.legal_kind == "target"
    assert board.legal == (engine.actor("mira").position,)
    assert 28 not in controls(engine) and controls(engine)[29]["command"] == "back"
    assert view["decision"]["actor"] == "garran"
    assert engine.select(engine.actor("mira").position)
    view, board = presentation(engine)
    assert view["decision"]["targets"] == [engine.actor("mira").name]
    assert board.selected == (engine.actor("mira").position,)
    assert controls(engine)[28]["command"] == "accept"


def test_information_preserves_pending_roll_and_hides_action_controls() -> None:
    engine = relations_game()
    assert engine.choose("second_wind") and engine.commit()
    engine.s.inspected = "garran"
    before = deepcopy(engine.s.as_payload())
    view, board = presentation(engine)
    assert view["decision"]["inspected"] == "garran"
    assert controls(engine)[26]["command"] == "page"
    assert controls(engine)[27]["command"] == "page"
    assert 28 not in controls(engine) and not board.action_cues
    assert engine.s.as_payload() == before


def test_card_pools_and_wards_show_their_deadline_after_chain_ends() -> None:
    engine = relations_game("garran", ("mira",))
    engine.grant_ac("mira", 1, "garran", "breaking_strike")
    engine.grant_pool("mira", "temporary", 4, "garran")
    engine.grant_pool("mira", "prevention", 3, "garran")
    engine.add_rune("garran", "Wieża")
    engine.end_chain("wyładowanie")
    view, _ = presentation(engine)
    ally = next(actor for actor in view["actors"] if actor["id"] == "mira")
    assert view["chain"] is None
    for prefix in ("Ochrona · +1 KP", "Tymczasowe PW: 4", "Osłona obrażeń: 3"):
        matching = [status for status in ally["statuses"] if status.startswith(prefix)]
        assert len(matching) == 1
        assert "do początku tury: Garran" in matching[0]


def test_focus_and_normal_movement_keep_the_selected_physical_button_visible() -> None:
    engine = relations_game()
    engine.fighter().charges = 10
    assert engine.choose("focus")
    _, board = presentation(engine)
    assert board.selected_slot == rune_slot("Spirala")
    assert led_colors(board)[panel_position(board.selected_slot)] == LedColor.ACTIVE_ACTOR
    assert engine.cancel() and engine.choose("move")
    _, board = presentation(engine)
    assert board.selected_slot == 0 and board.legal_kind == "movement"
    assert all(led_colors(board)[position] == LedColor.MOVEMENT_RANGE for position in board.legal)
