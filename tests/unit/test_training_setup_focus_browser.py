"""Introduction and placement are separate, visible decisions at both screen sizes."""
import json
import re
from pathlib import Path
import shutil
import subprocess

import pytest

from dnd_board_game.combat import SetupStepKind
from dnd_board_game.ui import training_walkthrough as guided
from tests.unit.test_recruitment_arena import arena


@pytest.mark.parametrize('width', [390, 1100])
def test_introduction_then_current_placement_without_scrolling(tmp_path: Path, width: int) -> None:
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome is needed for presentation checks')
    session = arena(tmp_path)
    guided.start(session, 'garran')
    introduction = session.state_payload()
    guided.acknowledge(session, guided.notice_id(session))
    terrain = session.state_payload()
    while session.encounter_setup_flow.current_step.kind != SetupStepKind.ACTORS:
        session.confirm_encounter_setup_step()
    actor = session.state_payload()
    static = Path('src/dnd_board_game/ui/static')
    source = (static / 'exploration.js').read_text()
    scripts = '\n'.join((static / name).read_text() for name in ('physical_mana.js', 'training_arena.js', 'exploration_mana.js'))
    scripts += source[source.index('function encounterHtml()'):source.index('function encounterStealthHtml(')]
    scripts += source[source.index('function focusCombatDecision()'):source.index('function combatInitiativeRibbonHtml(')]
    css = '\n'.join((static / name).read_text() for name in ('exploration.css', 'physical_mana.css', 'training_arena.css'))
    harness = r'''
let busy=false, keyboardRollWizard=null;
// Headless dump-dom does not reliably advance compositor frames in virtual time.
window.requestAnimationFrame=callback=>setTimeout(()=>callback(performance.now()),0);
function esc(text) {return String(text ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');}
function boardSelectionStatusHtml() {return '<span>Plansza nasłuchuje</span>';}
function check(ok,message) {if(!ok) throw new Error(message);}
const frame=()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
function render() {
 renderTrainingArena();
 document.getElementById('encounter').innerHTML=encounterHtml();
 focusCombatDecision();
}
(async()=>{try {
 render();
 await frame();
 const notice=document.getElementById('training-notice');
 check(notice?.innerText.includes('PRZED ĆWICZENIEM'), 'introduction is missing');
 check(notice.querySelector('.training-notice-card').scrollTop===0, 'focus scrolled past introduction');
 check(getComputedStyle(document.getElementById('encounter-panel')).display==='none', 'setup competes with introduction');
 check(document.getElementById('training-arena-panel').hidden, 'course competes with introduction');
 for (const next of [terrainState, actorState]) {
   state=next;
   render();
   await frame();
   check(!document.getElementById('training-notice'), 'stale introduction blocks setup');
   check(document.getElementById('training-arena-panel').hidden, 'course hides current placement below fold');
   check(getComputedStyle(document.getElementById('encounter-panel')).display!=='none', 'setup remains hidden');
   check(!document.querySelector('.encounter-transition-head, .encounter-progress'), 'generic combat stages compete with setup');
   check(!document.querySelector('.battle-map-preview[open]'), 'map expands before placement');
   const command=document.querySelector('.setup-current-command');
   check(command.innerText.includes(state.encounter_setup.current_step.label), 'wrong placement instruction');
   check(command.innerText.includes('✓ Potwierdź'), 'physical confirmation missing');
   check(document.activeElement===command, 'current placement did not get focus');
   const rect=command.getBoundingClientRect();
   const header=document.querySelector('.app-shell-header').getBoundingClientRect();
   check(rect.top>=header.bottom && rect.bottom<=innerHeight, 'current placement needs scrolling: '+JSON.stringify(rect.toJSON()));
   check(document.documentElement.scrollWidth<=innerWidth, 'horizontal overflow in setup');
 }
 document.getElementById('result').textContent='PASS';
} catch(error) {document.getElementById('result').textContent='FAIL: '+error.stack;}})();
'''
    data = lambda value: json.dumps(value).replace('</', '<\\/')
    page = tmp_path / 'setup.html'
    page.write_text('<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                   + '<style>' + css + '.app-shell-header{position:fixed;top:0;height:80px;width:100%;}'
                   + 'main{padding-top:100px;}footer{height:100vh;}</style>'
                   + '<header class="app-shell-header"></header><main><div id="training-arena-panel"></div>'
                   + '<section id="encounter-panel"><div id="encounter"></div></section></main><footer></footer>'
                   + '<pre id="result">PENDING</pre><script>let state=' + data(introduction) + ';'
                   + 'const terrainState=' + data(terrain) + ',actorState=' + data(actor) + ';'
                   + scripts + harness + '</script>')
    result = subprocess.run([chrome, '--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
        '--no-first-run', '--disable-background-networking', '--no-proxy-server', '--run-all-compositor-stages-before-draw',
        '--virtual-time-budget=3000', f'--user-data-dir={tmp_path / "chrome"}',
        f'--window-size={width},844', '--dump-dom', page.as_uri()], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr[-1000:]
    status = re.search(r'<pre id="result">(.*?)</pre>', result.stdout, re.S)
    assert status and status.group(1) == 'PASS', status.group(1) if status else result.stdout[-1000:]
