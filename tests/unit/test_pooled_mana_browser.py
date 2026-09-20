import json
import re
from pathlib import Path
import shutil
import subprocess

import pytest

from tests.unit.test_hero_rules_consistency import heroes
from tests.unit.test_physical_mana import session_for
from tests.unit.test_pooled_mana_runtime import send
from dnd_board_game.ui.shared_mana import payload


@pytest.mark.parametrize("width", [390, 1100])
def test_pool_dialog_runes_and_native_board_ownership(heroes, tmp_path, width):
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome:
        pytest.skip("Chrome required")
    session = session_for(heroes["brakka"], tmp_path, pooled=True)
    setup = payload(session)
    send(session, "pool_shuffle")
    send(session, "pool_color", color="C")
    send(session, "pool_color", color="B")
    choice = payload(session)
    send(session, "pool_take", index=0)
    ready = payload(session)
    payer = session_for(heroes["garran"], tmp_path / "payer", pooled=True)
    from tests.unit.test_pooled_mana_runtime import prepare
    prepare(payer, "B", "C")
    payer.use_combat_class_feature("second_wind")
    payment = payload(payer)
    assert dict(payment["declaration"]["sections"])["Akcja"] == "Akcja główna"
    send(payer, "pay")
    paid = payload(payer)
    static = Path("src/dnd_board_game/ui/static")
    scripts = "\n".join((static / name).read_text() for name in ("physical_mana.js", "shared_mana.js", "board_panel.js", "shield_bash.js"))
    source = (static / "exploration.js").read_text()
    scripts += source[source.index('function combatTurnActorStatsHtml('):source.index('function rememberCombatScreenFallback(')]
    css = "\n".join((static / name).read_text() for name in ("exploration.css", "physical_mana.css"))
    harness = """
const busy = false, keyboardRollWizard = null, combatActorDetailsActorId = '';
function combatActorChips() { return []; }
function statusChipsHtml() { return ''; }
let call = null;
function esc(v) { return String(v).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'); }
function api(path, body) { call = {path, body}; }
function check(v,m) { if (!v) throw new Error(m); }
try {
 document.getElementById('app').innerHTML = sharedManaHtml(state.combat);
 check(document.querySelector('[role="dialog"]').textContent.includes('Przetasuj'), 'Missing shuffle instruction');
 sharedManaPrimary();
 check(call.body.command === 'pool_shuffle', 'Wrong shuffle command');
 state.combat.shared_mana = choice;
 document.getElementById('app').innerHTML = sharedManaHtml(state.combat);
 check(sharedManaPanel() === null && desiredBoardPanel() === null, 'Browser steals native runes');
 const buttons = [...document.querySelectorAll('[role="dialog"] button')];
 check(buttons.length === 2, 'Not two choices');
 check(buttons[0].textContent.includes('Klucz'), 'Missing printed rune');
 check(buttons[0].textContent.includes('Atut → 2/6 ładunku · +1 do testów'), 'Missing card point preview');
 check(document.querySelector('[role="dialog"] .mana-points-total').textContent.includes('0/6 kart'), 'Missing current points inside choice');
 buttons[0].click();
 check(call.body.command === 'pool_take' && call.body.index === 0, 'Wrong choice command');
 check(document.documentElement.scrollWidth <= innerWidth, 'Horizontal overflow');
 state.combat = {shared_mana: ready, current_actor: {id: 'brakka', name: 'Brakka'}};
 document.getElementById('app').innerHTML = pooledManaPointsHtml(state.combat, null, true) + combatTurnActorStatsHtml(state.combat);
 check(document.querySelector('.mana-points-total').textContent.includes('1/6 kart'), 'Missing visible turn total');
 check(document.querySelector('.mana-points-summary').textContent.includes('Testy +1 · Ładunek 2/6'), 'Compact panel must distinguish bonus and ability charge');
 state.combat = {shared_mana: payment, current_actor: {id: 'enemy'}};
 document.getElementById('app').innerHTML = sharedManaHtml(state.combat);
 check(document.querySelector('[role="dialog"] .mana-points-total').textContent.includes('Garran'), 'Wrong paying actor');
 check(document.querySelector('[role="dialog"] .mana-points-total').textContent.includes('1/6 kart'), 'Missing points during payment');
 check(document.querySelector('[role="dialog"] .mana-valued-card').textContent.includes('Atut · 2 ładunku'), 'Missing individual card value');
 check(document.documentElement.scrollWidth <= innerWidth, 'Payment point display overflows');
 check(document.querySelector('[role="dialog"]').textContent.includes('Zachowaj'), 'Missing retained charge reminder');
 check(document.querySelector('.mana-charge-statuses').textContent.includes('KP'), 'Missing passive status');
 check(document.querySelector('.mana-charge-statuses [data-stackable="false"]'), 'Missing nonstacking icon frame');
 check(!document.querySelector('.mana-charge-statuses').textContent.includes('×'), 'Unlock incorrectly shown as stacking');
 check(document.getElementById('app').textContent.includes('Naładowanie: +1 do testów'), 'Missing charge bonus');
 state.combat = {shared_mana: paid, current_actor: {id: 'garran'}};
 document.getElementById('app').innerHTML = pooledManaPointsHtml(state.combat);
 check(document.querySelector('.mana-points-total').textContent.includes('1/6 kart'), 'Charge disappeared after ability');
 document.getElementById('result').textContent = 'PASS';
} catch(e) { document.getElementById('result').textContent = 'FAIL: ' + e.stack; }
"""
    path = tmp_path / "pool.html"
    path.write_text('<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><style>' + css
        + '</style><div id="app"></div><pre id="result">PENDING</pre><script>let state = '
        + json.dumps(dict(combat=dict(shared_mana=setup), board_selection=dict(panel_enabled=True)))
        + '; const choice = ' + json.dumps(choice) + '; const ready = ' + json.dumps(ready) + '; const payment = ' + json.dumps(payment) + '; const paid = ' + json.dumps(paid) + '; new Function(' + json.dumps(source) + ');' + scripts + harness + '</script>')
    result = subprocess.run([chrome, '--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
        '--no-first-run', '--enable-logging=stderr', '--disable-background-networking', '--no-proxy-server', f'--user-data-dir={tmp_path / "chrome"}',
        f'--window-size={width},1000', '--dump-dom', path.as_uri()], capture_output=True, text=True, timeout=25)
    assert result.returncode == 0, result.stderr[-1200:]
    assert '<pre id="result">PASS</pre>' in result.stdout, (re.findall(r'<pre id="result">(.*?)</pre>', result.stdout, re.S), result.stderr[-1800:])


@pytest.mark.parametrize('format_id', ['minimal', 'bw_test', 'color', 'cards'])
def test_all_hero_prints_fit_cards_and_pages(tmp_path, format_id):
    from dnd_board_game.application.recruitment_arena import HERO_ORDER
    from dnd_board_game.physical_cards.mana_print import build_print_hero
    from dnd_board_game.physical_cards.mana_print_html import render_hero_html, CSS
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome required')
    pages = []
    for hero in HERO_ORDER:
        markup = render_hero_html(build_print_hero(hero), format_id)
        pages.extend(re.findall(r'<section class="page.*?</section>', markup, re.S))
    harness = '''
const problems = [];
for (const [i, card] of [...document.querySelectorAll('.ability')].entries()) {
 if(card.scrollHeight > card.clientHeight + 2) problems.push('card:' + i + ':' + card.scrollHeight + '/' + card.clientHeight);
}
for (const [i, page] of [...document.querySelectorAll('.page')].entries()) {
 if(page.scrollHeight > page.clientHeight + 2) problems.push('page:' + i);
 const footer = page.querySelector('footer');
 if(footer) for (const child of page.children) {
  if(child !== footer && child.getBoundingClientRect().bottom > footer.getBoundingClientRect().top + 1) problems.push('footer:' + i);
 }
}
document.getElementById('result').textContent = problems.length ? problems.join(', ') : 'PASS';
'''
    path = tmp_path / 'prints.html'
    path.write_text('<meta charset="utf-8"><style>' + CSS + '</style><body class="bw">' + ''.join(pages)
                    + '<pre id="result"></pre><script>' + harness + '</script>')
    result = subprocess.run([chrome, '--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
        '--no-first-run', '--disable-background-networking', f'--user-data-dir={tmp_path / "chrome"}',
        '--dump-dom', path.as_uri()], capture_output=True, text=True, timeout=25)
    assert result.returncode == 0, result.stderr[-1200:]
    assert '<pre id="result">PASS</pre>' in result.stdout, re.findall(r'<pre id="result">(.*?)</pre>', result.stdout, re.S)
