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
    assert len(result['legal_positions']) == 4
    assert not any(any(color) for color in board.leds.values())
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


@pytest.mark.parametrize('page_path', ['/', '/new-game', '/load-game'])
@pytest.mark.parametrize('key_profile', ['arrows', 'numpad', 'numpad-unlocked', 'portable'])
def test_launcher_keyboard_events_select_real_controls(tmp_path: Path, page_path: str, key_profile: str) -> None:
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
let contract=null, scans=0, generation=0, navigation=null, submission=null;
const scrolls=[];
window.scrollBy=options=>scrolls.push(options.top);
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
function press(action,repeat=false){
 const profiles={
  arrows:{up:['ArrowUp','ArrowUp'],right:['ArrowRight','ArrowRight'],down:['ArrowDown','ArrowDown'],left:['ArrowLeft','ArrowLeft'],accept:['Enter','Enter'],back:['Escape','Escape']},
  numpad:{up:['8','Numpad8'],right:['6','Numpad6'],down:['2','Numpad2'],left:['4','Numpad4'],accept:['Enter','NumpadEnter'],back:['Backspace','Backspace']},
  'numpad-unlocked':{up:['ArrowUp','Numpad8'],right:['ArrowRight','Numpad6'],down:['ArrowDown','Numpad2'],left:['ArrowLeft','Numpad4'],accept:['Enter','NumpadEnter'],back:['Backspace','Backspace']},
  portable:{up:['8','Digit8'],right:['6','Digit6'],down:['2','Digit2'],left:['4','Digit4'],accept:['Enter','Enter'],back:['Backspace','Backspace']},
 };
 const [key,code]=profiles[PROFILE][action]||({scrollDown:['+','NumpadAdd'],scrollUp:['-','NumpadSubtract']})[action];
 document.dispatchEvent(new KeyboardEvent('keydown',{key,code,repeat,bubbles:true,cancelable:true}));
}
document.addEventListener('submit',event=>{
 event.preventDefault();submission={path:new URL(event.target.action).pathname,values:[...new FormData(event.target)]};
},true);
document.addEventListener('click',event=>{
 const link=event.target.closest('a.menu-action,a[data-board-back]');
 if(link){event.preventDefault();navigation=new URL(link.href).pathname;}
},true);
window.addEventListener('load',async()=>{
 try{
  await until(()=>contract);
  await pause();
  check(document.querySelector('[data-board-status]').textContent.includes('Klawiatura'),'missing keyboard hint');
  check(document.querySelector('[data-board-status]').textContent.includes('8/2/4/6'),'missing numpad hint');
  check(scans===0,'keyboard started scan');
  press('scrollDown');press('scrollUp');
  check(scrolls.length===2&&scrolls[0]>0&&scrolls[1]<0,'numpad +/- did not scroll descriptions');
  if(PAGE==='/'){
   for(const [direction,slot] of [['right',6],['left',5],['down',6],['up',5],['down',6]]){
    press(direction);await pause();check(contract.focused===slot,'wrong direction '+direction);
   }
   press('accept');await pause();
   check(navigation==='/load-game','Enter did not follow selected menu link');
  }else if(PAGE==='/new-game'){
   press('accept');await pause();
   check(document.querySelectorAll('input[name="character_ids"]:checked').length===1,'Enter did not select hero');
   press('accept',true);await pause();
   check(document.querySelectorAll('input[name="character_ids"]:checked').length===1,'repeat toggled hero');
   const field=document.createElement('input');field.type='text';document.body.append(field);field.focus();
   field.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));
   check(document.querySelectorAll('input[name="character_ids"]:checked').length===1,'typing triggered menu');
   field.remove();
   const continueParty=async()=>{
    for(let i=0;i<10&&contract.focused!==24;i++){press('down');await pause();}
    check(contract.focused===24,'numpad could not reach party confirmation');
    press('accept');await until(()=>!document.getElementById('scenario-selection-step').hidden);await pause();
   };
   await continueParty();
   press('back');await until(()=>!document.getElementById('party-selection-step').hidden);await pause();
   check(document.querySelectorAll('input[name="character_ids"]:checked').length===1,'Backspace lost selected party');
   await continueParty();press('accept');await until(()=>submission);
   check(submission.path==='/new-game/start','numpad did not start selected scenario');
   check(submission.values.some(([key])=>key==='character_ids'),'selected hero missing from submission');
  }else{
   press('back');await pause();
   check(navigation==='/','Backspace did not return from saved games');
  }
  check(scans===0,'physical scan requested');
  const out=document.createElement('pre');out.id='keyboard-result';out.textContent=JSON.stringify({ok:true});document.body.append(out);
 }catch(error){const out=document.createElement('pre');out.id='keyboard-result';out.textContent=JSON.stringify({ok:false,error:String(error)});document.body.append(out);}
});
'''
    html = html.replace('</head>', '<script>const PAGE=' + json.dumps(page_path) + ', PROFILE=' + json.dumps(key_profile) + ';' + harness + '</script></head>')
    path = tmp_path / 'keyboard-launcher.html'
    path.write_text(html)
    result = subprocess.run([chrome, '--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
                             '--virtual-time-budget=5000', '--dump-dom', path.as_uri()],
                            capture_output=True, text=True, timeout=20)
    match = re.search(r'<pre id="keyboard-result">(.*?)</pre>', result.stdout)
    assert match, result.stderr[-1500:]
    payload = json.loads(match.group(1).replace('&quot;', '"').replace('&amp;', '&'))
    assert payload['ok'], payload
