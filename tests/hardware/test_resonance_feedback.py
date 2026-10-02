"""Semantic v0.3 LED cues using an in-memory connection, without a device."""
from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.hardware.board_session import BoardSessionAdapter
from dnd_board_game.hardware.led_palette import LedColor
from dnd_board_game.hardware.resonance_feedback import ResonanceBoardView, resonance_feedback
from dnd_board_game.world import Coordinate


class FakeBoard:
    def __init__(self) -> None:
        self.leds: dict[tuple[int, int], tuple[int, int, int]] = {}
        self.clears = 0

    def set_leds(self, positions: list[tuple[int, int]], rgb_color: list[int] | list[list[int]]) -> None:
        colors = rgb_color if rgb_color and isinstance(rgb_color[0], list) else [rgb_color] * len(positions)
        self.leds.update({tuple(position): tuple(color) for position, color in zip(positions, colors, strict=True)})

    def leds_off(self) -> None:
        self.leds.clear()
        self.clears += 1


def test_legal_rune_cues_and_locked_finishers_are_translated_without_rules() -> None:
    board = FakeBoard()
    adapter = BoardSessionAdapter(board)
    view = ResonanceBoardView(active=Coordinate(2, 2), action_slots=(5, 6, 7, 8, 9, 25),
        action_cues=((5, "start"), (6, "continue"), (7, "reset"), (8, "finisher"), (9, "locked")))
    adapter.show_feedback(resonance_feedback(view))
    gold = tuple(round(value * .65) for value in LedColor.PANEL_RUNE)
    for slot in (5, 6, 8):
        assert board.leds[panel_position(slot).as_tuple()] == gold
    assert board.leds[panel_position(7).as_tuple()] == tuple(round(value * .65) for value in LedColor.PANEL_RESONANCE_RESET)
    assert panel_position(9).as_tuple() not in board.leds
    assert board.leds[panel_position(25).as_tuple()] == tuple(round(value * .65) for value in LedColor.PANEL_INFO)
    # A new authoritative frame may lock a formerly available finisher after
    # memory changes. The board receives a replacement and clears its old LED.
    adapter.show_feedback(resonance_feedback(ResonanceBoardView(active=view.active, action_slots=(25,),
        action_cues=((5, "locked"), (6, "locked"), (7, "locked"), (8, "locked"), (9, "locked")))))
    assert all(panel_position(slot).as_tuple() not in board.leds for slot in (5, 6, 7, 8, 9))


def test_selected_rune_and_figure_white_targets_gold_and_distinct_player_path() -> None:
    board = FakeBoard()
    adapter = BoardSessionAdapter(board)
    target, selected, path, destination = (Coordinate(x, 3) for x in range(3, 7))
    view = ResonanceBoardView(active=Coordinate(2, 3), legal=(target, selected, destination),
        selected=(selected,), path=(path, destination), destination=destination,
        action_slots=(25,), selected_slot=6)
    adapter.show_feedback(resonance_feedback(view))
    assert board.leds[target.as_tuple()] == LedColor.PANEL_RUNE
    assert board.leds[selected.as_tuple()] == LedColor.ACTIVE_ACTOR
    assert board.leds[path.as_tuple()] == LedColor.PLAYER_MOVEMENT_PATH
    assert board.leds[destination.as_tuple()] == LedColor.MOVEMENT_DESTINATION
    assert board.leds[panel_position(6).as_tuple()] == LedColor.ACTIVE_ACTOR


def test_movement_range_survives_destination_changes_and_illegal_targets_are_red() -> None:
    board = FakeBoard()
    adapter = BoardSessionAdapter(board)
    fields = tuple(Coordinate(x, 4) for x in range(3, 8))
    for destination, path in ((fields[2], fields[:3]), (fields[4], fields[3:])):
        adapter.show_feedback(resonance_feedback(ResonanceBoardView(
            active=Coordinate(2, 4), legal=fields, path=path, destination=destination, legal_kind="movement")))
        assert all(board.leds[p.as_tuple()] == (LedColor.MOVEMENT_DESTINATION if p == destination
                   else LedColor.PLAYER_MOVEMENT_PATH if p in path else LedColor.MOVEMENT_RANGE) for p in fields)
    adapter.show_feedback(resonance_feedback(ResonanceBoardView(
        active=Coordinate(2, 4), legal=(fields[0],), illegal=(fields[1],))))
    assert board.leds[fields[0].as_tuple()] == LedColor.PANEL_RUNE
    assert board.leds[fields[1].as_tuple()] == LedColor.ATTACK_MISS


def test_enemy_reaction_red_and_new_feedback_clears_previous_rune_selection() -> None:
    board = FakeBoard()
    adapter = BoardSessionAdapter(board)
    selected, reacting = Coordinate(3, 3), Coordinate(4, 3)
    adapter.show_feedback(resonance_feedback(ResonanceBoardView(active=selected, selected_slot=6)))
    adapter.show_feedback(resonance_feedback(ResonanceBoardView(active=selected, focus=reacting, enemy=True,
        legal=(Coordinate(5, 3),), legal_kind="movement", path=(Coordinate(6, 3),))))
    assert panel_position(6).as_tuple() not in board.leds
    assert board.leds[reacting.as_tuple()] == LedColor.ENEMY
    assert board.leds[(5, 3)] == LedColor.MOVEMENT_RANGE
    assert board.leds[(6, 3)] == LedColor.ENEMY_MOVEMENT_PATH
    adapter.close()
    assert not board.leds
