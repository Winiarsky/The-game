"""The guided arena is usable with symbols, board confirmation and narrow screens."""
import json
import re
from pathlib import Path
import shutil
import subprocess

import pytest

from dnd_board_game.application.training_walkthrough import steps
from dnd_board_game.ui import training_walkthrough as guided
from tests.unit.test_training_walkthrough import prepared, prepare_pool


@pytest.mark.parametrize('width', [390, 1100])
def test_guided_briefing_and_roster_in_browser(tmp_path: Path, width: int) -> None:
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome is needed for presentation checks')
    index = next(i for i, step in enumerate(steps('garran')) if step.id == 'shield_bash:damage')
    s = prepared(tmp_path, 'garran', index)
    state = s.state_payload()
    stance_index = next(i for i, step in enumerate(steps('garran')) if step.id == 'defensive_stance')
    stance = prepared(tmp_path / 'stance', index=stance_index)
    guided.acknowledge(stance, guided.notice_id(stance))
    prepare_pool(stance)
    option = next(o for o in stance._combat_turn_action_options() if o.action_id == 'defensive_stance')
    preview_state = stance.confirm_combat_turn_action(option.id)
    payment_state = stance.confirm_combat_turn_action()
    from tests.unit.test_recruitment_arena import arena
    from dnd_board_game.ui.training_menu import command, payload
    roster_session = arena(tmp_path / 'menu')
    roster_state = roster_session.state_payload()
    subjects_state = command(roster_session, dict(action='hero:garran', revision=payload(roster_session)['revision']))
    modes_state = command(roster_session, dict(action='subject:combat', revision=payload(roster_session)['revision']))
    cases_state = command(roster_session, dict(action='cases', revision=payload(roster_session)['revision']))
    next_state = command(roster_session, dict(action='next', revision=payload(roster_session)['revision']))
    static = Path('src/dnd_board_game/ui/static')
    scripts = '\n'.join((static / name).read_text() for name in ('physical_mana.js', 'board_panel.js', 'training_arena.js', 'exploration_mana.js'))
    source = (static / 'exploration.js').read_text()
    initialize = source[source.index('function initializeKeyboardRollWizard()'):source.index('function keyboardRollStepPrompt(')]
    css = '\n'.join((static / name).read_text() for name in ('exploration.css', 'physical_mana.css', 'training_arena.css'))
    harness = r'''
let busy=false, keyboardRollWizard=null, call=null;
function esc(text) {return String(text ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');}
function api(path,body) {call={path,body};}
function check(ok,message) {if(!ok) throw new Error(message);}
try {
 renderTrainingArena();
 const notice=document.getElementById('training-notice');
 check(notice?.getAttribute('role')==='dialog', 'missing briefing dialog');
 check(notice.innerText.includes('TWOJE ZADANIE'), 'wrong briefing stage');
 check(state.training_arena.tutorial.current.explanation.includes('12 pkt'), 'new point requirement missing');
 check(state.training_arena.tutorial.current.narration.includes('osobistą pulę'), 'physical preparation missing');
 check(!notice.innerText.includes('ĆWICZENIE ZALICZONE'), 'briefing gives premature completion');
 check(!initializeKeyboardRollWizard(), 'dice overlay stole briefing');
 check(desiredBoardPanel()===null, 'browser overwrites board briefing mask');
 check(!document.getElementById('training-mode'), 'old free-form tutorial selector remains');
 const token=state.training_arena.tutorial.notice.id;
 notice.querySelector('button').click();
 check(call.path==='/api/training/acknowledge' && call.body.ability_id===token, 'wrong briefing acknowledgement');
 check(document.documentElement.scrollWidth<=innerWidth, 'horizontal overflow in briefing');
 const card=notice.querySelector('.training-notice-card').getBoundingClientRect();
 check(card.left>=0 && card.right<=innerWidth, 'briefing outside viewport');
 state=previewState;
 renderTrainingArena();
 check(!document.querySelector('.training-lesson-help').open, 'lesson help should start collapsed');
 document.querySelector('.training-lesson-help').open=true;
 check(document.querySelector('.training-next').innerText.includes('Naciśnij niebieskie ✓'), 'preview still asks to select rune');
 check(!document.getElementById('training-notice'), 'briefing still blocks preview');
 state=paymentState;
 renderTrainingArena();
 check(document.getElementById('training-arena-panel').hidden, 'course competes with payment dialog');
 check(!document.querySelector('.training-next'), 'old action instruction remains during payment');
 state=rosterState;
 renderTrainingArena();
 check(!document.getElementById('training-notice'), 'stale briefing');
 check(document.querySelectorAll('.training-roster button').length===7, 'incomplete roster');
 check(document.querySelectorAll('.training-roster svg[data-panel-slot]').length===7, 'missing hero runes');
 check(document.querySelector('.training-menu-controls').innerText.includes('Menu główne'), 'missing roster back');
 document.querySelector('.training-roster button').click();
 check(call.path==='/api/training/menu' && call.body.action==='hero:garran', 'roster did not open modes');
 check(call.body.revision===state.training_arena.menu.revision, 'missing stale-input protection');
 state=subjectsState;
 renderTrainingArena();
 check(document.querySelector('.training-roster').innerText.includes('Eksploracja'), 'missing exploration branch');
 check(!document.querySelector('.mana-hero-entry'), 'old duplicate exploration roster remains');
 state=modesState;
 renderTrainingArena();
 check(document.querySelector('.training-roster').innerText.includes('Po kolei'), 'missing sequential mode');
 document.querySelectorAll('.training-roster button')[1].click();
 check(call.body.action==='cases', 'missing independent case selection');
 state=casesState;
 renderTrainingArena();
 check(document.querySelectorAll('.training-roster button').length===8, 'case pagination missing');
 check(document.querySelector('.training-menu-controls').innerText.includes('Następna strona'), 'missing next page');
 state=nextState;
 renderTrainingArena();
 check(document.querySelector('.training-roster').innerText.includes('Uderzenie'), 'missing ability variants');
 document.querySelector('.training-roster button').click();
 check(call.body.action.startsWith('case:'), 'case did not start independently');
 check(!document.getElementById('training-tools'), 'stale retry toolbar in menu');
 state=paymentState;
 renderTrainingArena();
 document.querySelector('#training-tools button').click();
 check(call.path==='/api/training/leave' && call.body.retry===true, 'cannot restart during payment');
 const toolbar=document.getElementById('training-tools').getBoundingClientRect();
 check(toolbar.left>=0 && toolbar.right<=innerWidth, 'retry toolbar outside viewport');
 document.querySelectorAll('#training-tools button')[1].click();
 check(call.path==='/api/training/leave' && !call.body.retry, 'cannot return during payment');
 check(document.documentElement.scrollWidth<=innerWidth, 'horizontal overflow in roster');
 document.getElementById('result').textContent='PASS';
} catch(error) {document.getElementById('result').textContent='FAIL: '+error.stack;}
'''
    page = tmp_path / 'walkthrough.html'
    page.write_text('<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                   + '<style>' + css + '</style><div id="training-arena-panel"></div><pre id="result">PENDING</pre>'
                   + '<script>let state=' + json.dumps(state).replace('</', '<\\/') + ';'
                   + 'const previewState=' + json.dumps(preview_state).replace('</', '<\\/') + ';'
                   + 'const paymentState=' + json.dumps(payment_state).replace('</', '<\\/') + ';'
                   + 'new Function(' + json.dumps(source).replace('</', '<\\/') + ');'
                   + ''.join('const ' + key + '=' + json.dumps(value).replace('</', '<\\/') + ';' for key, value in dict(rosterState=roster_state, subjectsState=subjects_state, modesState=modes_state, casesState=cases_state, nextState=next_state).items())
                   + scripts + initialize + harness + '</script>')
    result = subprocess.run([chrome, '--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
        '--no-first-run', '--disable-background-networking', '--no-proxy-server',
        f'--user-data-dir={tmp_path / "chrome"}', f'--window-size={width},1000', '--dump-dom', page.as_uri()],
        capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr[-1000:]
    status = re.search(r'<pre id="result">(.*?)</pre>', result.stdout, re.S)
    assert status and status.group(1) == 'PASS', status.group(1) if status else result.stdout[-1000:]
