from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.hardware.initiative_panel import initiative_panel_feedback
from dnd_board_game.rules.dice import RollMode
from dnd_board_game.ui.initiative_panel import InitiativePanel
from dnd_board_game.ui.exploration_app import ExplorationUiSession
from dnd_board_game.ui.training_arena import start_training_trial, training_hero
from dnd_board_game.ui.routes import create_app
from dnd_board_game.world import Coordinate


class Board:
    def __init__(self) -> None:
        self.selected = (19, 2)
        self.scans = 0
        self.leds: dict[tuple[int, int], tuple[int, int, int]] = {}

    def set_leds(self, positions, rgb_color) -> None:
        colors = rgb_color if rgb_color and isinstance(rgb_color[0], list) else [rgb_color] * len(positions)
        for p, color in zip(positions, colors, strict=True):
            self.leds[tuple(p)] = tuple(color)

    def leds_off(self) -> None:
        self.leds.clear()

    def cancel_scan(self) -> None:
        pass

    def scan_board(self, positions, *, timeout_s):
        assert self.selected in positions
        self.scans += 1
        return self.selected


def session_at_initiative(tmp_path: Path) -> ExplorationUiSession:
    session = ExplorationUiSession(
        "content/scenarios/recruitment_arena.json",
        observation_dir=tmp_path / "observations",
        save_dir=tmp_path / "saves",
    )
    session.configure_custom_party((training_hero("garran"),))
    start_training_trial(session, "garran", "basic", "humanoid")
    while not session.encounter_setup_flow.completed:
        session.confirm_encounter_setup_step()
    session.start_encounter_initiative()
    return session


def test_bounds_and_two_separate_dice_with_review_and_correction() -> None:
    panel = InitiativePanel((10, 10))
    panel = panel.change("minus", 1)
    assert panel.values == (1, 10) and 26 in panel.enabled_slots
    panel = panel.change("accept", 20)
    assert panel.values == (20, 10) and panel.index == 1
    panel = panel.change("accept", 7)
    assert panel.review and panel.enabled_slots == (28, 29)
    panel = panel.change("back").change("minus").change("accept")
    assert panel.review and panel.values == (20, 6)
    with pytest.raises(ValueError):
        panel.change("plus")


@pytest.mark.parametrize("value", [0, 21, 2.5, True, "12"])
def test_invalid_natural_result_is_rejected(value: object) -> None:
    with pytest.raises(ValueError):
        InitiativePanel().change("accept", value)


def test_board_scan_changes_one_value_and_requires_second_accept(
    tmp_path: Path,
) -> None:
    session = session_at_initiative(tmp_path)
    board = Board()
    board.selected = (19, 3)  # Printed + is slot 26.
    session.attach_board_connection(board, backend="simulator")
    session._sync_board_leds()
    payload = session.state_payload()
    selection = payload["board_selection"]
    assert selection["auto_arm"] and selection["mode"] == "initiative_roll"
    assert board.leds == {
        (19, 3): (0, 255, 0),
        (19, 2): (255, 0, 0),
        (19, 1): (0, 80, 255),
    }
    session.scan_board_selection(
        expected_revision=selection["revision"], automatic=True
    )
    assert board.scans == 1
    assert session.encounter_initiative_flow.roll_panel.values == (11,)
    # An old retry must neither scan again nor increase the result.
    session.scan_board_selection(
        expected_revision=selection["revision"], automatic=True
    )
    assert board.scans == 1
    assert session.encounter_initiative_flow.roll_panel.values == (11,)
    board.selected = (19, 1)
    session.scan_board_selection(automatic=True)
    assert session.combat_state is None
    assert set(board.leds) == {(19, 1), (19, 0)}
    session.scan_board_selection(automatic=True)
    assert session.combat_state is not None
    flow = session.encounter_initiative_flow
    assert flow.completed and flow.roll_panel is None
    entry = next(e for e in flow.entries if str(e.actor.id) == "garran")
    assert entry.roll.natural_roll == 11
    assert session.state_payload()["board_selection"]["mode"] != "initiative_roll"


def test_advantage_uses_two_values_and_only_commits_after_review(
    tmp_path: Path,
) -> None:
    session = session_at_initiative(tmp_path)
    flow = session.encounter_initiative_flow
    prompt = flow.current_prompt
    flow.prompts = (
        replace(prompt, request=replace(prompt.request, mode=RollMode.ADVANTAGE)),
    )
    flow.panel = None
    session.update_initiative_panel("accept", value=4)
    assert flow.roll_panel.index == 1 and flow.roll_panel.values == (4, 10)
    session.update_initiative_panel("accept", value=17)
    assert session.combat_state is None
    session.select_board_position(Coordinate(19, 0))
    session.update_initiative_panel("accept", value=16)
    session.select_board_position(Coordinate(19, 1))
    entry = next(e for e in flow.entries if str(e.actor.id) == "garran")
    assert entry.roll.natural_rolls == (4, 16)


def test_http_panel_and_stale_confirmation(tmp_path: Path) -> None:
    session = session_at_initiative(tmp_path)
    client = create_app(session, character_dir=tmp_path / "characters").test_client()
    revision = session.state_payload()["board_selection"]["revision"]
    result = client.post(
        "/api/encounter/initiative/panel",
        json={"command": "accept", "value": 13, "revision": revision},
    )
    assert result.status_code == 200
    assert result.json["encounter_initiative"]["panel"]["review"]
    client.post(
        "/api/encounter/initiative/panel",
        json={"command": "accept", "revision": revision},
    )
    assert session.combat_state is None
    revision = session.state_payload()["board_selection"]["revision"]
    result = client.post(
        "/api/encounter/initiative/panel",
        json={"command": "accept", "revision": revision},
    )
    assert result.status_code == 200 and session.combat_state is not None


def test_feedback_contains_only_enabled_panel_fields() -> None:
    frames = initiative_panel_feedback((28, 29)).frames
    assert [f.positions for f in frames] == [(Coordinate(19, 1),), (Coordinate(19, 0),)]
