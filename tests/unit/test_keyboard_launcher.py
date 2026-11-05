"""Keyboard launchers keep LEDs but never wait for physical panel input."""
from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest

from dnd_board_game.runtime import exploration_ui, mission_combat_ui
from dnd_board_game.ui.routes import create_app
from scripts.keyboard_playtest import prepare_session
from tests.unit.test_launcher_board import arm, menu
from tests.unit.test_launcher_ui import _session


def test_keyboard_launcher_has_led_choices_without_automatic_scan(tmp_path: Path) -> None:
    session, board, client = menu(tmp_path)
    session.input_mode = 'keyboard'
    result = arm(session, client)

    assert result['control_mode'] == 'keyboard'
    assert result['connected']
    assert not result['auto_arm']
    assert not result['allow_retry']
    assert 'Enter' in result['prompt']
    assert len(board.leds) == 4
    assert board.scans == 0


def test_launcher_respects_output_only_capability(tmp_path: Path) -> None:
    session, board, client = menu(tmp_path)
    board.can_scan = False

    result = arm(session, client)

    assert result['connected']
    assert not result['auto_arm']
    assert board.scans == 0


def test_keyboard_launcher_does_not_probe_remembered_hardware(tmp_path: Path, monkeypatch) -> None:
    session = _session(tmp_path)
    session.input_mode = 'keyboard'
    session.board_backend = 'none'
    session.configured_board_backend = 'hardware'
    configured: list[str] = []
    monkeypatch.setattr(session, 'configure_board', lambda **kwargs: configured.append(kwargs['backend']))
    client = create_app(session, character_dir=tmp_path / 'characters').test_client()
    client.get('/')

    result = arm(session, client)

    assert configured == []
    assert result['control_mode'] == 'keyboard'
    assert not result['auto_arm']
    assert session.board_adapter is None


def test_keyboard_full_mission_preparation_is_isolated(tmp_path: Path) -> None:
    from dnd_board_game.ui import mission_zero

    session = prepare_session(tmp_path, ('garran', 'brakka', 'nimra'))

    assert session.input_mode == 'keyboard'
    assert session.configured_board_backend == 'none'
    assert session.board_adapter is None
    assert session.save_dir == tmp_path / 'saves'
    assert mission_zero.read(session)['stage'] == 'world'
    assert {str(actor.id) for actor in session.exploration.actors} == {'garran', 'brakka', 'nimra'}


def test_keyboard_arena_preparation_can_skip_simulator_setup(tmp_path: Path) -> None:
    session = prepare_session(tmp_path, ('garran', 'brakka', 'nimra'), arena=True, skip_setup=True)

    assert session.input_mode == 'keyboard'
    assert session.combat_state is not None
    assert session.combat_state.resonance is not None
    assert session.combat_state.resonance.profile == 'rune_relations_v03'


def test_runtime_accepts_keyboard_and_wled_profiles() -> None:
    assert exploration_ui.build_parser().parse_args(['--input-mode', 'keyboard']).input_mode == 'keyboard'
    assert exploration_ui.build_parser().parse_args(['--board-backend', 'wled']).board_backend == 'wled'
    assert mission_combat_ui.build_parser().parse_args(['--input-mode', 'keyboard']).input_mode == 'keyboard'
    assert mission_combat_ui.build_parser().parse_args(['--board-backend', 'wled']).board_backend == 'wled'


@pytest.mark.parametrize('page_path', ['/', '/new-game'])
def test_launcher_keyboard_events_select_real_controls(tmp_path: Path, page_path: str) -> None:
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome is needed for keyboard browser checks')
    session = _session(tmp_path)
    session.input_mode = 'keyboard'
    html = create_app(session).test_client().get(page_path).get_data(as_text=True)
    static = Path('src/dnd_board_game/ui/static')
    html = re.sub(r'<link rel="stylesheet"[^>]+>',
                  lambda _: '<style>' + (static / 'launcher.css').read_text() + '</style>', html)
    for filename in ('launcher_board.js', 'session_copy.js'):
        html = re.sub(r'<script src="[^"]*' + filename.replace('.', r'\.') + r'[^\"]*"[^>]*></script>',
                      lambda _, name=filename: '<script>' + (static / name).read_text() + '</script>', html)
    harness = r'''
let contract=null, scans=0, generation=0, navigation=null;
window.fetch=(path,options)=>{
 const body=JSON.parse(options.body);
 if(path==='/api/board/navigation') {
  contract=body;
  return Promise.resolve({ok:true,json:()=>Promise.resolve({input:{mode:'keyboard'},
   board_selection:{revision:String(++generation),control_mode:'keyboard',connected:true,auto_arm:false}})});
 }
 if(path.endsWith('/release'))return Promise.resolve({ok:true,json:()=>Promise.resolve({ok:true})});
 scans++;throw new Error('Unexpected physical scan '+path);
};
const check=(ok,message)=>{if(!ok)throw new Error(message);};
const pause=()=>new Promise(resolve=>setTimeout(resolve,20));
async function until(predicate){for(let i=0;i<100;i++){if(predicate())return;await pause();}throw new Error('Timed out');}
function press(key,repeat=false){document.dispatchEvent(new KeyboardEvent('keydown',{key,repeat,bubbles:true,cancelable:true}));}
document.addEventListener('click',event=>{
 const link=event.target.closest('a.menu-action');
 if(link){event.preventDefault();navigation=new URL(link.href).pathname;}
},true);
window.addEventListener('load',async()=>{
 try{
  await until(()=>contract);
  await pause();
  check(document.querySelector('[data-board-status]').textContent.includes('Klawiatura'),'missing keyboard hint');
  check(scans===0,'keyboard started scan');
  if(PAGE==='/'){
   press('ArrowDown');await pause();press('Enter');await pause();
   check(navigation==='/load-game','Enter did not follow selected menu link');
  }else{
   press('Enter');await pause();
   check(document.querySelectorAll('input[name="character_ids"]:checked').length===1,'Enter did not select hero');
   press('Enter',true);await pause();
   check(document.querySelectorAll('input[name="character_ids"]:checked').length===1,'repeat toggled hero');
   const field=document.createElement('input');field.type='text';document.body.append(field);field.focus();
   field.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));
   check(document.querySelectorAll('input[name="character_ids"]:checked').length===1,'typing triggered menu');
  }
  check(scans===0,'physical scan requested');
  const out=document.createElement('pre');out.id='keyboard-result';out.textContent=JSON.stringify({ok:true});document.body.append(out);
 }catch(error){const out=document.createElement('pre');out.id='keyboard-result';out.textContent=JSON.stringify({ok:false,error:String(error)});document.body.append(out);}
});
'''
    html = html.replace('</head>', '<script>const PAGE=' + json.dumps(page_path) + ';' + harness + '</script></head>')
    path = tmp_path / 'keyboard-launcher.html'
    path.write_text(html)
    result = subprocess.run([chrome, '--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
                             '--virtual-time-budget=5000', '--dump-dom', path.as_uri()],
                            capture_output=True, text=True, timeout=20)
    match = re.search(r'<pre id="keyboard-result">(.*?)</pre>', result.stdout)
    assert match, result.stderr[-1500:]
    payload = json.loads(match.group(1).replace('&quot;', '"').replace('&amp;', '&'))
    assert payload['ok'], payload
