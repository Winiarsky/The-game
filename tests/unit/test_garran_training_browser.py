"""The physical command explains which figure acts next at both screen sizes."""
import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest

from dnd_board_game.ui import training_walkthrough as guided
from tests.unit.test_garran_training_regressions import lesson
from tests.unit.test_shared_mana_runtime import send
from dnd_board_game.ui.shared_command import select
from dnd_board_game.hardware.board_panel import panel_position


@pytest.mark.parametrize('width', [390, 1100])
def test_guard_and_two_command_steps_are_explicit(tmp_path: Path, width: int) -> None:
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome is needed for presentation checks')
    guard, _ = lesson(tmp_path / 'guard', 'garran_guard_companion')
    guided.acknowledge(guard, guided.notice_id(guard))
    guard_view = guard.state_payload()['combat']
    session, _ = lesson(tmp_path / 'command', 'counterattack_command')
    guided.acknowledge(session, guided.notice_id(session))
    session.use_combat_class_feature('counterattack_command', target_id='recruitment_helper')
    send(session, 'pay')
    first = session.state_payload()['combat']
    select(session, panel_position(28))
    preview = session.state_payload()['combat']
    enemy = next(a for a in session.combat_state.actors if str(a.id) == 'recruitment_dummy')
    session.select_player_attack_target_at_position(enemy.position)
    session.confirm_player_attack_target()
    session.submit_player_attack_roll(natural_roll=1)
    second = session.state_payload()['combat']
    static = Path('src/dnd_board_game/ui/static')
    scripts = '\n'.join((static / name).read_text() for name in ('physical_mana.js', 'shared_mana.js'))
    source = (static / 'exploration.js').read_text()
    scripts += source[source.index('function combatCurrentStepHtml('):source.index('function combatCardReminderHtml(')]
    css = '\n'.join((static / name).read_text() for name in ('exploration.css', 'physical_mana.css'))
    harness = r'''
let state={combat:guard}, resultAck=null;
function esc(text) {return String(text ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');}
function check(ok,message) {if(!ok) throw new Error(message);}
function combatPresentationPhase() {return 'choice';}
function combatPhaseStepsHtml() {return '';}
let busy=false, calls=[];
function api(path, data) {calls.push({path, data});}
function combatCardReminderHtml() {return '';}
function combatPrimaryActionHtml() {return '<button>Wybierz akcję na planszy</button>';}
try {
 document.getElementById('app').innerHTML=sharedManaHtml(guard);
 const dialog=document.querySelector('.shared-mana-decision');
 check(dialog.innerText.includes('atakuje Pomocnik'), 'missing original target');
 check(dialog.innerText.includes('PW traci Garran'), 'missing damage recipient');
 let slot=null;
 for (const [index,combat] of [first,second].entries()) {
   state.combat=combat;
   document.getElementById('app').innerHTML= combatCurrentStepHtml(combat,false,true,false);
   const step=document.querySelector('.shared-command-step');
   check(step, 'command instruction absent from current decision');
   check(step.innerText.includes((index+1)+'/2'), 'missing part count');
   check(step.innerText.includes(combat.current_actor.name), 'wrong active participant');
   check(step.innerText.includes('Koszt jest już opłacony'), 'unclear second payment');
   check(step.innerText.includes('✓ bez wyboru pola pomija ruch'), 'unclear zero movement confirmation');
   check(step.querySelector('.shared-command-movement').innerText.includes('opcjonalnie'), 'movement appears mandatory');
   check(step.querySelector('.shared-command-movement svg').dataset.panelSlot === '0', 'wrong movement symbol');
   check(!step.querySelector('.shared-command-attack'), 'attack instruction competes with movement');
   const next=step.querySelector('.shared-command-movement svg').dataset.panelSlot;
   check(slot===null || slot===next, 'helper uses a different rune');
   slot=next;
   check(step.getBoundingClientRect().bottom<innerHeight, 'instruction below fold');
   check(document.documentElement.scrollWidth<=innerWidth, 'horizontal overflow');
 }
 document.getElementById('app').innerHTML=sharedCommandStepHtml(preview);
 check(document.querySelector('.shared-command-step').innerText.includes('Garran'), 'lost participant during targeting');
 check(document.querySelector('.shared-command-attack').innerText.includes('Atak wyposażoną bronią jest już gotowy'), 'attack does not explain automatic weapon selection');
 check(!document.querySelector('.shared-command-movement'), 'movement prompt competes with target selection');
 state={combat:first, board_selection:{revision:'movement'}};
 sharedManaPrimary();
 check(calls.length===1 && calls[0].path==='/api/combat/command', 'physical confirm did not finish movement');
 state.combat=preview; sharedManaPrimary();
 check(calls.length===1, 'confirm sent before selecting enemy');
 document.getElementById('result').textContent='PASS';
} catch(error) {document.getElementById('result').textContent='FAIL: '+error.stack;}
'''
    page = tmp_path / 'garran.html'
    encode = lambda data: json.dumps(data).replace('</', '<\\/')
    page.write_text('<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        + '<style>' + css + '</style><div id="app"></div><pre id="result">PENDING</pre><script>'
        + 'const guard=' + encode(guard_view) + ',first=' + encode(first) + ',second=' + encode(second) + ',preview=' + encode(preview) + ';'
        + scripts + harness + '</script>')
    result = subprocess.run([chrome, '--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
        '--no-first-run', '--disable-background-networking', '--no-proxy-server',
        f'--user-data-dir={tmp_path / "chrome"}', f'--window-size={width},844', '--dump-dom', page.as_uri()],
        capture_output=True, text=True, timeout=20)
    status = re.search(r'<pre id="result">(.*?)</pre>', result.stdout, re.S)
    assert result.returncode == 0, result.stderr[-1000:]
    assert status and status.group(1) == 'PASS', status.group(1) if status else result.stdout[-1000:]
