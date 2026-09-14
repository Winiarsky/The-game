import json
from pathlib import Path
import shutil
import subprocess

import pytest

from dnd_board_game.ui.shared_mana import payload
from tests.unit.test_shared_mana_board_targets import shield_bonus, send


@pytest.mark.parametrize("width", [390, 1100])
def test_target_dialog_uses_board_instructions_and_does_not_override_native_scan(tmp_path: Path, width: int) -> None:
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome:
        pytest.skip("Chrome is needed to check the target dialog")
    session, _ = shield_bonus(tmp_path)
    empty = payload(session)
    send(session, "target", target_id="mira")
    send(session, "target", target_id="brakka")
    selected = payload(session)
    static = Path("src/dnd_board_game/ui/static")
    scripts = "\n".join((static / name).read_text() for name in
        ("physical_mana.js", "shared_mana.js", "board_panel.js"))
    css = "\n".join((static / name).read_text() for name in ("exploration.css", "physical_mana.css"))
    harness = '''
const busy = false, keyboardRollWizard = null;
let call = null;
function esc(value) {return String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');}
function api(path, body) {call = {path, body};}
function check(value, message) {if (!value) throw new Error(message);}
try {
 document.getElementById('app').innerHTML = sharedManaHtml(state.combat);
 check(!document.querySelector('.shared-mana-decision select'), 'Dropdown still controls targets');
 check(document.querySelector('.shared-mana-decision > .panel-accept').disabled, 'Empty selection can confirm');
 check(document.querySelector('.mana-target-instruction').innerText.includes('na planszy'), 'Missing board instruction');
 sharedManaPrimary();
 check(call === null, 'Empty selection submitted');
 check(sharedManaPanel() === null && desiredBoardPanel() === null, 'Browser overrides native target mask');
 state.combat.shared_mana = selectedMana;
 document.getElementById('app').innerHTML = sharedManaHtml(state.combat);
 check(document.querySelectorAll('.mana-target-option[aria-pressed="true"]').length === 2, 'Missing selected targets');
 check(document.querySelector('.mana-target-selection [role="status"]').innerText.includes('2/2'), 'Missing selection count');
 check(!document.querySelector('.shared-mana-decision > .panel-accept').disabled, 'Valid selection cannot confirm');
 check(!document.querySelector('.shared-mana-decision').innerText.includes('Rzuć kością'), 'Shield ward asks for a die');
 document.querySelector('.mana-target-selection details').open = true;
 document.querySelector('.mana-target-option').click();
 check(call.body.command === 'target' && call.body.target_id === 'mira', 'Fallback uses different target command');
 sharedManaPrimary();
 check(call.body.command === 'bonus' && call.body.revision === selectedMana.revision, 'Wrong confirmation or revision');
 check(document.documentElement.scrollWidth <= innerWidth, 'Horizontal overflow');
 document.getElementById('result').textContent = 'PASS';
} catch(error) {document.getElementById('result').textContent = 'FAIL: ' + error.stack;}
'''
    page = tmp_path / "targets.html"
    data = {"combat": {"shared_mana": empty}, "board_selection": {"panel_enabled": True}}
    page.write_text('<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        + '<style>' + css + '</style><div id="app"></div><pre id="result">PENDING</pre><script>'
        + 'const state = ' + json.dumps(data) + '; const selectedMana = ' + json.dumps(selected) + ';'
        + scripts + harness + '</script>')
    result = subprocess.run([chrome, '--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
        '--no-first-run', '--disable-background-networking', '--no-proxy-server',
        f'--user-data-dir={tmp_path / "chrome"}', f'--window-size={width},1000', '--dump-dom', page.as_uri()],
        capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr[-1500:]
    assert '<pre id="result">PASS</pre>' in result.stdout, result.stdout[-2500:]
