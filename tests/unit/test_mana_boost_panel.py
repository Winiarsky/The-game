from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.ui.shared_mana import gate_payment, payload, command
from dnd_board_game.ui.routes import create_app
from tests.unit.test_recruitment_arena import arena, begin
from tests.unit.test_initiative_panel import Board


def payment(tmp_path: Path, hero: str = 'garran', ability: str = 'shield_bash'):
    session = arena(tmp_path)
    begin(session, hero)
    gate_payment(session, ability, 'state_payload')
    board = Board()
    session.attach_board_connection(board, backend='simulator')
    session._sync_board_leds()
    return session, board


def choose(session, slot: int):
    return command(session, dict(command='boost_option', slot=slot,
                                revision=session.combat_state.shared_mana.revision))


def test_payment_runes_show_red_cost_and_explicit_amounts(tmp_path: Path) -> None:
    session, board = payment(tmp_path)
    choices = payload(session)['declaration']['boost_options']
    assert [(o['slot'], o['cost'], o['amount']) for o in choices] == [(6, ['C'], 1), (7, ['C', 'C'], 2)]
    assert all('data-panel-slot' in o['icon'] for o in choices)
    target = session._current_board_scan_target()
    assert set(target.positions) == {panel_position(s) for s in (6, 7, 28, 29)}
    assert board.leds[panel_position(6).as_tuple()][0] > board.leds[panel_position(6).as_tuple()][1]
    board.selected = panel_position(6).as_tuple()
    session.scan_board_selection(automatic=True)
    assert session.shared_mana_declaration.boosts == {'damage': 1}
    assert payload(session)['declaration']['cost'].count('C') == 2
    # Same physical rune toggles off, while the second selects two boosts.
    session.scan_board_selection(automatic=True)
    assert session.shared_mana_declaration.boosts == {'damage': 0}
    choose(session, 7)
    assert session.shared_mana_declaration.boosts == {'damage': 2}


def test_different_mana_colors_combine_and_limits_disable_only_invalid_variants(tmp_path: Path) -> None:
    session, _ = payment(tmp_path, 'brakka', 'shoulder_check')
    choose(session, 6)  # one blue push
    choose(session, 8)  # one red damage
    assert session.shared_mana_declaration.boosts == {'push': 1, 'damage': 1}
    choices = {o['slot']: o for o in payload(session)['declaration']['boost_options']}
    assert choices[6]['selected'] and choices[8]['selected']
    assert not choices[7]['enabled'] and not choices[9]['enabled']
    assert panel_position(7) not in session._current_board_scan_target().positions
    with pytest.raises(ValueError, match='limit'):
        choose(session, 7)
    choose(session, 6)
    assert session.shared_mana_declaration.boosts == {'push': 0, 'damage': 1}
    assert next(o for o in payload(session)['declaration']['boost_options'] if o['slot'] == 9)['enabled']


def test_stale_rune_request_cannot_toggle_new_payment_state(tmp_path: Path) -> None:
    session, _ = payment(tmp_path)
    old = session._board_selection_payload()['revision']
    revision = session.combat_state.shared_mana.revision
    choose(session, 6)
    assert old != session._board_selection_payload()['revision']
    with pytest.raises(ValueError, match='Nieaktualny'):
        command(session, dict(command='boost_option', revision=revision, slot=6))
    assert session.shared_mana_declaration.boosts['damage'] == 1


def test_card_shortage_leaves_back_and_selected_rune_available(tmp_path: Path) -> None:
    session, _ = payment(tmp_path)
    choose(session, 7)
    session.combat_state = replace(session.combat_state, shared_mana=replace(
        session.combat_state.shared_mana, market=2, discard=3))
    target = session._current_board_scan_target()
    assert panel_position(28) not in target.positions
    assert {panel_position(29), panel_position(7)} <= set(target.positions)
    choose(session, 7)
    assert panel_position(28) in session._current_board_scan_target().positions


def test_screen_and_board_choose_same_variant_and_back_keeps_cards(tmp_path: Path) -> None:
    session, board = payment(tmp_path)
    client = create_app(session).test_client()
    response = client.post('/api/combat/shared-mana', json=dict(command='boost_option', slot=7,
        revision=session.combat_state.shared_mana.revision))
    assert response.status_code == 200
    assert session.shared_mana_declaration.boosts['damage'] == 2
    board.selected = panel_position(29).as_tuple()
    session.scan_board_selection(automatic=True)
    assert session.shared_mana_declaration is None
    assert session.combat_state.shared_mana.market == 5


@pytest.mark.parametrize('width', [390, 1100])
def test_browser_boost_cards_use_symbols_and_send_exact_rune(tmp_path: Path, width: int) -> None:
    import json
    import shutil
    import subprocess

    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome is needed for the rendered payment panel')
    session, _ = payment(tmp_path)
    mana = payload(session)
    static = Path('src/dnd_board_game/ui/static')
    scripts = (static / 'physical_mana.js').read_text() + (static / 'shared_mana.js').read_text()
    css = (static / 'exploration.css').read_text() + (static / 'physical_mana.css').read_text()
    harness = '''
const busy = false;
let call = null;
function esc(value) {return String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');}
function api(path, body) {call = {path, body};}
function check(value, message) {if (!value) throw new Error(message);}
try {
 document.getElementById('app').innerHTML = sharedManaHtml(state.combat);
 const buttons = [...document.querySelectorAll('.mana-boost-option')];
 check(buttons.length === 2, 'Missing explicit one/two boost choices');
 check(!document.querySelector('.mana-boosts select'), 'Boost dropdown is still present');
 check(!document.querySelector('.mana-boosts .panel-plus'), 'Ambiguous plus control is still present');
 check(buttons[0].querySelectorAll('.mana-C').length === 1, 'Single boost needs red symbol');
 check(buttons[1].querySelectorAll('.mana-C').length === 2, 'Double boost needs two red symbols');
 check(buttons[1].innerText.includes('+2k6 obrażeń przy wygranym teście'), 'Damage amount and condition must be explicit');
 check(buttons[0].querySelector('[data-panel-slot="6"]'), 'Missing printed rune');
 buttons[1].click();
 check(call.body.command === 'boost_option' && call.body.slot === 7, 'Wrong rune command');
 check(call.body.revision === state.combat.shared_mana.revision, 'Missing revision guard');
 check(sharedManaPanel() === null && sharedManaDelta(1) === false, 'Browser may not override payment runes');
 check(!document.querySelector('[role="dialog"]').innerText.includes('Enter'), 'Keyboard-first instruction');
 check(document.documentElement.scrollWidth <= innerWidth, 'Horizontal overflow');
 document.getElementById('result').textContent = 'PASS';
} catch(error) {document.getElementById('result').textContent = 'FAIL: ' + error.stack;}
'''
    page = tmp_path / f'mana-boosts-{width}.html'
    syntax_check = 'new Function(' + json.dumps((static / 'exploration.js').read_text()).replace('</', '<\\/') + ');'
    page.write_text('<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
                    + '<style>' + css + '</style><div id="app"></div><pre id="result">PENDING</pre><script>'
                    + 'const state = ' + json.dumps({'combat': {'shared_mana': mana}}, ensure_ascii=False) + ';'
                    + syntax_check + scripts + harness + '</script>')
    result = subprocess.run([chrome, '--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
                             '--no-first-run', '--disable-background-networking', '--no-proxy-server',
                             f'--user-data-dir={tmp_path / "chrome"}', f'--window-size={width},1000',
                             '--dump-dom', page.as_uri()], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr[-1500:]
    assert '<pre id="result">PASS</pre>' in result.stdout, result.stdout[-2500:]


def test_shield_bash_physical_rune_and_accept_pay_for_extra_damage(tmp_path: Path) -> None:
    from tests.unit.test_shield_bash_ui_flow import ready
    session = ready(tmp_path, pay=False)
    board = Board()
    session.attach_board_connection(board, backend='simulator')
    board.selected = panel_position(6).as_tuple()
    session.scan_board_selection(automatic=True)
    assert session.combat_state.shared_mana.market == 5
    board.selected = panel_position(28).as_tuple()
    result = session.scan_board_selection(automatic=True)
    assert session.shared_mana_declaration is None
    assert session.combat_state.shared_mana.market == 2
    assert result['combat']['shield_bash']['stage'] == 'contest'
    assert result['combat']['shield_bash']['damage_dice'] == 2
