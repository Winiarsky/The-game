"""Shield Bash uses the same per-die controls and aggregation as normal damage."""
from pathlib import Path
import shutil
import subprocess

import pytest


@pytest.mark.parametrize('count', [1, 2, 3])
def test_shield_bash_dice_icons_steps_and_raw_damage_sum(tmp_path: Path, count: int) -> None:
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome is needed for the roll wizard regression')
    static = Path('src/dnd_board_game/ui/static')
    source = (static / 'exploration.js').read_text()
    wizard = source[source.index('function isKeyboardRollInput('):
                    source.index('function handleKeyboardRollWizardKeydown(')]
    harness = r'''
let busy = false, keyboardRollWizard = null, submitted = null;
const state = {combat: {shield_bash: {stage:'damage', damage_dice:COUNT,
  attacker_name:'Garran', target_name:'Kukła', attacker_roll:15, attacker_modifier:4,
  defender_roll:5, defender_modifier:0}}};
const esc = text => String(text ?? '');
const signedNumber = n => n >= 0 ? '+' + n : String(n);
const scheduleAutomaticBoardScan = () => {};
const handleKeyboardRollWizardKeydown = () => {};
const api = (path, body) => {submitted = {path, body};};
function check(ok, message) {if (!ok) throw new Error(message);}
try {
 document.getElementById('encounter').innerHTML = shieldBashHtml(state.combat.shield_bash);
 check(initializeKeyboardRollWizard(), 'wizard did not open');
 check(keyboardRollWizard.steps.length === COUNT, 'expected one step per physical die');
 for (let i=0; i<COUNT; i++) {
  const overlay = document.getElementById('keyboard-roll-wizard');
  check(overlay.querySelector('.dice-icon-k6'), 'missing k6 icon');
  check(overlay.innerText.includes(`Rzut ${i+1} z ${COUNT}`), 'wrong progress');
  const entry = document.getElementById('keyboard-roll-wizard-input');
  check(entry.min === '1' && entry.max === '6', 'die has sum bounds');
  entry.value = '7';
  check(!confirmKeyboardRollStep(), 'accepted impossible k6');
  document.getElementById('keyboard-roll-wizard-input').value = '3';
  changeRollPanelValue(1);
  check(confirmKeyboardRollStep(), 'valid die rejected');
 }
 check(keyboardRollWizard.review, 'missing review');
 check(document.getElementById('keyboard-roll-wizard').innerText.includes(`= ${COUNT*4+4}`), 'Strength not applied once');
 previousKeyboardRollStep();
 document.getElementById('keyboard-roll-wizard-input').value = '5';
 confirmKeyboardRollStep();
 check(document.getElementById('shield-bash-damage-roll').value === String(COUNT*4+1), 'correction did not replace previous die');
 submitKeyboardRollWizard();
 check(submitted.body.damage_roll === COUNT*4+1, 'backend must receive dice sum without Strength');
 check(submitted.path === '/api/combat/shield-bash/rolls', 'wrong action');
 document.getElementById('result').textContent = 'PASS';
} catch (error) { document.getElementById('result').textContent = 'FAIL: ' + error.stack; }
'''
    page = tmp_path / 'dice.html'
    page.write_text('<meta charset="utf-8"><div id="encounter"></div><pre id="result">PENDING</pre><script>'
                    + (static / 'dice_icons.js').read_text() + wizard
                    + (static / 'board_panel.js').read_text() + (static / 'shield_bash.js').read_text()
                    + harness.replace('COUNT', str(count)) + '</script>')
    result = subprocess.run([chrome, '--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
                             '--no-first-run', '--disable-background-networking', '--no-proxy-server',
                             f'--user-data-dir={tmp_path / "chrome"}', '--dump-dom', page.as_uri()],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr[-1500:]
    assert '<pre id="result">PASS</pre>' in result.stdout, result.stdout[:3000]
