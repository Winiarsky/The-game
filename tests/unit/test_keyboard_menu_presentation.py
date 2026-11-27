"""Keyboard menus stay on screen while the board displays only spatial cues."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from threading import Event, Thread
from typing import Any

from flask import request
import pytest
from werkzeug.serving import make_server

from dnd_board_game.hardware.led_palette import LedColor
from dnd_board_game.ui.routes import create_app
from scripts.keyboard_playtest import prepare_session
from tests.integration.test_combat_board_feedback import combat, send
from tests.unit.test_initiative_panel import Board
from tests.unit.test_launcher_board import arm
from tests.unit.test_mission_zero import stage


def lit_fields(board: Board) -> set[tuple[int, int]]:
    return {position for position, color in board.leds.items() if any(color)}


def test_keyboard_intro_and_launcher_leave_the_function_strip_dark(tmp_path: Path) -> None:
    game = prepare_session(tmp_path, ('garran', 'brakka', 'nimra'))
    board = Board()
    game.attach_board_connection(board, backend='simulator')
    game._sync_board_leds()

    assert not any(col == 19 for col, _ in lit_fields(board))
    client = create_app(game, character_dir=tmp_path / 'characters').test_client()
    client.get('/')
    selection = arm(game, client)

    assert len(selection['legal_positions']) == 4
    assert not selection['auto_arm']
    assert not lit_fields(board)
    assert board.scans == 0


def test_keyboard_brief_removes_existing_rune_lights_and_board_mode_restores_them(tmp_path: Path) -> None:
    game = prepare_session(tmp_path, ('garran', 'brakka', 'nimra'))
    stage(game, 'brief')
    board = Board()
    game.attach_board_connection(board, backend='simulator')
    game.configure_input_mode('board')
    game._sync_board_leds()
    physical_controls = {position for position in lit_fields(board) if position[0] == 19}
    assert physical_controls

    game.configure_input_mode('keyboard')
    game._sync_board_leds()
    assert not any(col == 19 for col, _ in lit_fields(board))
    assert not game.state_payload()['board_selection']['auto_arm']

    game.configure_input_mode('board')
    game._sync_board_leds()
    assert physical_controls <= lit_fields(board)
    assert board.scans == 0


def test_keyboard_setup_keeps_map_feedback_without_function_lights(tmp_path: Path) -> None:
    game = prepare_session(tmp_path, ('garran', 'brakka', 'nimra'), arena=True)
    board = Board()
    game.attach_board_connection(board, backend='simulator')
    game._sync_board_leds()

    assert lit_fields(board), 'Terrain or setup locations must remain visible'
    assert all(col != 19 for col, _ in lit_fields(board))
    assert not game.state_payload()['board_selection']['auto_arm']
    assert board.scans == 0


def test_keyboard_motion_preserves_range_path_and_destination_colors(tmp_path: Path) -> None:
    game, board, _, _ = combat(tmp_path)
    game.configure_input_mode('keyboard')
    send(game, 'choose', id='move')
    client = create_app(game, character_dir=tmp_path / 'characters').test_client()
    controls = game.state_payload()['input']
    response = client.post('/api/input/command', json={
        'command': 'cursor', 'position': [3, 5],
        'context': controls['context'], 'revision': controls['revision'],
    })

    assert response.status_code == 200, response.json
    assert board.leds[(3, 5)] == LedColor.MOVEMENT_DESTINATION
    assert board.leds[(3, 4)] == LedColor.PLAYER_MOVEMENT_PATH
    assert any(color == LedColor.MOVEMENT_RANGE for color in board.leds.values())
    assert all(col != 19 for col, _ in lit_fields(board))
    assert board.scans == 0


def test_keyboard_nessa_menu_is_textual_focused_and_operated_by_arrows(tmp_path: Path) -> None:
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome required for menu presentation check')
    game = prepare_session(tmp_path, ('garran', 'brakka', 'nimra'))
    stage(game, 'brief')
    board = Board()
    game.attach_board_connection(board, backend='simulator')
    game._sync_board_leds()
    app = create_app(game, character_dir=tmp_path / 'characters')
    done = Event()
    report: dict[str, Any] = {}

    @app.post('/__test/result')
    def result() -> dict[str, bool]:
        report.update(request.get_json())
        done.set()
        return {'ok': True}

    harness = r'''<script>
    (async()=>{
      const pause=()=>new Promise(resolve=>setTimeout(resolve,20));
      const check=(value,message)=>{if(!value)throw Error(message)};
      const wait=async(predicate,message)=>{
        for(let i=0;i<300;i++){if(predicate())return;await pause();}
        throw Error('timeout '+message);
      };
      const key=value=>{
        const code=/^[0-9]$/.test(value)?'Numpad'+value:value==='Enter'?'NumpadEnter':value;
        (document.activeElement||document.body).dispatchEvent(new KeyboardEvent('keydown',{
          key:value,code,location:code.startsWith('Numpad')?3:0,bubbles:true,cancelable:true,
        }));
        document.dispatchEvent(new KeyboardEvent('keyup',{key:value,code,bubbles:true}));
      };
      const options=()=>[...document.querySelectorAll('.keyboard-mission-menu .keyboard-mission-option')];
      const focused=()=>document.querySelector('.keyboard-mission-option.keyboard-choice-focused[aria-current="true"]');
      const idle=()=>wait(()=>!busy&&!boardPanelSyncPromise,'input idle');
      try{
        await wait(()=>state?.mission?.stage==='brief'&&!busy&&focused(),'initial menu highlight');
        const entries=options();
        check(entries.length===state.mission.choices.length,'text menu lost available actions');
        check(focused()===entries[0],'first choice is not selected on entry');
        check(document.activeElement===entries[0],'first choice lacks keyboard focus');
        check(entries.every(element=>!element.querySelector('svg')),'physical rune icons remain in choices');
        check(!document.querySelector('#mission-panel .mission-scroll-controls'),'old panel scroll controls remain');
        const reading=document.querySelector('#mission-panel .keyboard-reading-hint');
        check(reading&&reading.textContent.includes('− / +'),'missing numpad reading guidance');
        check(entries[0].getBoundingClientRect().top<entries[1].getBoundingClientRect().top,
          'choices are not a vertical menu');
        const revision=state.mission.revision;
        key('2');await pause();
        check(focused()===options()[1],'ArrowDown did not choose next option');
        key('8');await pause();
        check(focused()===options()[0],'ArrowUp did not choose previous option');
        key('2');await pause();
        check(state.mission.stage==='brief'&&state.mission.revision===revision,'arrows performed an action');
        const selectedKey=focused().dataset.keyboardChoice;
        render();await idle();
        await wait(()=>focused()?.dataset.keyboardChoice===selectedKey,'focus after refresh');
        check(document.activeElement===focused(),'refresh lost native focus');
        const choice=state.mission.choices[1];
        check(choice.action==='road_info','fixture second choice changed');
        key('Enter');await wait(()=>state.mission.stage==='road_info'&&!busy,'chosen road information');
        await wait(()=>focused(),'first choice in next context');
        check(focused()===options()[0],'new screen did not select its first choice');
        key('Enter');await wait(()=>state.mission.stage==='brief'&&!busy,'return to brief');
        await wait(()=>focused()===options()[0],'fresh context first choice');
        check(!state.board_selection.auto_arm&&!boardScanInFlight,'text menu started physical input');
        check(document.documentElement.scrollWidth<=innerWidth,'horizontal overflow');
        await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({result:'PASS'})});
      }catch(error){
        await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({result:String(error.stack),stage:state?.mission?.stage,
            body:document.body.innerText.slice(-1200)})});
      }
    })();</script>'''

    @app.after_request
    def inject(response: Any) -> Any:
        if request.path == '/play' and response.status_code == 200:
            response.set_data(response.get_data(as_text=True).replace('</body>', harness + '</body>'))
        return response

    server = make_server('127.0.0.1', 0, app, threaded=True)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    process = None
    try:
        process = subprocess.Popen([
            chrome, '--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
            '--no-first-run', '--disable-background-networking', '--no-proxy-server',
            f'--user-data-dir={tmp_path / "chrome"}', '--window-size=1268,800',
            f'http://127.0.0.1:{server.server_port}/play',
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        assert done.wait(35), 'Menu presentation browser did not report'
        assert report.get('result') == 'PASS', report
        assert not any(col == 19 for col, _ in lit_fields(board))
        assert board.scans == 0
    finally:
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
