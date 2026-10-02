"""Preview feedback remains editable and invalid targets never spend a turn."""
from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.combat.scene import SceneObject
from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.hardware.led_palette import LedColor
from dnd_board_game.ui import resonance
from dnd_board_game.ui.exploration_app import ExplorationUiSession
from dnd_board_game.ui.routes import create_app
from dnd_board_game.ui.training_arena import training_hero
from dnd_board_game.world import BoardState, Coordinate
from dnd_board_game.world.terrain import BLOCKING_TERRAIN
from tests.unit.test_initiative_panel import Board
from tests.unit.test_mission_zero import session, start_battle


def combat(tmp_path: Path) -> tuple[ExplorationUiSession, Board, str, str]:
    game = session(tmp_path, legacy_combat=False)
    game.configure_custom_party(tuple(training_hero(key) for key in ('erynd', 'nimra', 'brakka')))
    start_battle(game)
    encounter = game._active_encounter()
    board = BoardState()
    board.set_terrain(Coordinate(5, 3), BLOCKING_TERRAIN)
    chest = SceneObject('test_crate', 'Skrzynia P03', (Coordinate(5, 3),), 'Obejrzyj')
    game._replace_active_encounter(replace(encounter, board=board, scene_objects=(chest,)))
    engine = resonance.engine(game)
    for index, actor in enumerate(engine.actors.values()):
        engine.update_actor(replace(actor, position=Coordinate(12 + index % 4, 12 + index // 4)))
    engine.update_actor(replace(engine.actor('erynd'), position=Coordinate(3, 3)))
    blocked, legal = (str(actor.id) for actor in engine.enemies()[:2])
    engine.update_actor(replace(engine.actor(blocked), position=Coordinate(7, 3)))
    engine.update_actor(replace(engine.actor(legal), position=Coordinate(3, 6)))
    engine.s.index = engine.s.order.index('erynd')
    engine.begin_turn()
    game.combat_state = engine.combat_state()
    connection = Board()
    game.attach_board_connection(connection, backend='simulator')
    return game, connection, blocked, legal


def send(game: ExplorationUiSession, command: str, **data: object) -> dict:
    return resonance.command(game, dict(command=command, revision=game.combat_state.resonance.revision, **data))


def test_range_and_route_stay_visible_until_accept(tmp_path: Path) -> None:
    game, board, _, _ = combat(tmp_path)
    send(game, 'choose', id='move')
    initial = resonance.scan_target(game)
    fields = {tuple(p) for p in resonance.payload(game)['legal_positions']}
    origin = next(a.position for a in game.combat_state.actors if a.id == 'erynd')
    before_budget = game.combat_state.resonance.fighters['erynd'].base_spent
    for destination in (Coordinate(3, 5), Coordinate(1, 3)):
        send(game, 'select', position=list(destination))
        engine = resonance.engine(game)
        _, cues = resonance.presentation(engine)
        assert set(tuple(p) for p in cues.legal) == fields
        assert board.leds[destination.as_tuple()] == LedColor.MOVEMENT_DESTINATION
        assert all(board.leds[p.as_tuple()] == LedColor.PLAYER_MOVEMENT_PATH for p in cues.path if p != destination)
        assert all(board.leds[p.as_tuple()] == LedColor.MOVEMENT_RANGE for p in cues.legal if p not in cues.path)
        assert engine.active.position == origin
        assert engine.fighter().base_spent == before_budget
        assert set(initial.positions) <= set(resonance.scan_target(game).positions)
    send(game, 'accept')
    assert next(a.position for a in game.combat_state.actors if a.id == 'erynd') == Coordinate(1, 3)
    assert game.combat_state.resonance.fighters['erynd'].base_spent == before_budget + 2


@pytest.mark.parametrize('action', ('attack', 'hunters_mark'))
def test_illegal_target_is_red_scannable_explained_and_does_not_spend_action(tmp_path: Path, action: str) -> None:
    game, board, blocked, legal = combat(tmp_path)
    send(game, 'choose', id=action)
    engine = resonance.engine(game)
    blocked_position = engine.actor(blocked).position
    legal_position = engine.actor(legal).position
    target = resonance.scan_target(game)
    assert blocked_position in target.positions and legal_position in target.positions
    assert board.leds[blocked_position.as_tuple()] == LedColor.ATTACK_MISS
    assert board.leds[legal_position.as_tuple()] == LedColor.PANEL_RUNE
    budget = replace(engine.fighter())
    send(game, 'select', position=list(legal_position))
    board.selected = blocked_position.as_tuple()
    client = create_app(game).test_client()
    response = client.post('/api/board/scan', json=dict(revision=game._board_selection_payload()['revision'], automatic=True))
    assert response.status_code == 200, response.json
    view = response.json['combat']['resonance']
    assert 'Cel nielegalny' in view['decision']['warning']
    assert 'Skrzynia P03' in view['decision']['warning']
    assert view['decision']['target_ids'] == [blocked]
    assert 28 not in {control['slot'] for control in view['controls']}
    assert game.combat_state.resonance.fighters['erynd'] == budget
    with pytest.raises(ValueError, match='Cel nielegalny'):
        send(game, 'accept')
    # The fixture uses an empty test board; production reload reconstructs the authored map.
    fixture_encounter = game._active_encounter()
    game.save_snapshot()
    game.load_snapshot()
    assert 'Cel nielegalny' in resonance.payload(game)['decision']['warning']
    game._replace_active_encounter(fixture_encounter)
    send(game, 'select', position=list(legal_position))
    view = resonance.payload(game)
    assert not view['decision'].get('warning')
    assert view['decision']['target_ids'] == [legal]
    assert panel_position(28) in resonance.scan_target(game).positions


def test_target_sheet_includes_mark_source_and_effect_duration(tmp_path: Path) -> None:
    game, _, _, legal = combat(tmp_path)
    engine = resonance.engine(game)
    engine.fighter('erynd').mark = legal
    engine.add_status(legal, 'broken', until_end='erynd')
    game.combat_state = engine.combat_state()
    send(game, 'choose', id='attack')
    send(game, 'select', position=list(engine.actor(legal).position))
    view = game.state_payload()['combat']['resonance']
    actor = next(actor for actor in view['actors'] if actor['id'] == legal)
    assert actor['name'] and actor['id'] == legal  # Browser resolves authored enemy atlas portraits.
    assert any('Piętno łowcy' in status and 'Erynd' in status for status in actor['statuses'])
    assert any('Przełamana obrona' in status and 'do końca tury: Erynd' in status for status in actor['statuses'])
    assert len(actor['ability_scores']) == 6
    send(game, 'accept')
    assert resonance.payload(game)['decision']['target_ids'] == [legal]


def test_garran_second_wind_board_flow_only_lights_self_and_heals_self(tmp_path: Path) -> None:
    game = session(tmp_path, legacy_combat=False)
    game.configure_custom_party(tuple(training_hero(key) for key in ('erynd', 'garran', 'nimra')))
    start_battle(game)
    e = resonance.engine(game)
    e.s.index = e.s.order.index('garran')
    e.begin_turn()
    e.update_actor(replace(e.active, hp=5, position=Coordinate(8, 14)))
    # Positions from the final board scans of the reported session.
    for enemy, position in zip(e.enemies(), ((8, 13), (7, 15), (9, 13), (7, 13))):
        e.update_actor(replace(enemy, position=Coordinate(*position)))
    game.combat_state = e.combat_state()
    board = Board()
    game.attach_board_connection(board, backend='simulator')
    client = create_app(game).test_client()

    def press(position: Coordinate) -> dict:
        board.selected = position.as_tuple()
        response = client.post('/api/board/scan', json=dict(
            revision=game._board_selection_payload()['revision'], automatic=True))
        assert response.status_code == 200, response.json
        return response.json['combat']['resonance']

    view = press(Coordinate(19, 17))  # Żar odnowy rune.
    assert view['legal_positions'] == [[8, 14]]
    assert view['illegal_positions'] == []
    assert view['decision']['target_ids'] == ['garran']
    assert 'Garran' in view['decision']['prompt']
    targets = resonance.scan_target(game).positions
    assert not any(enemy.position in targets for enemy in resonance.engine(game).enemies())
    enemy_hp = {str(enemy.id): enemy.hp for enemy in resonance.engine(game).enemies()}
    view = press(panel_position(28))
    assert view['decision']['die']['sides'] == 10
    assert view['decision']['die']['value'] == 5
    press(panel_position(28))
    e = resonance.engine(game)
    assert e.actor('garran').hp == 5 + 5 + e.actor('garran').level
    assert {str(enemy.id): enemy.hp for enemy in e.enemies()} == enemy_hp
