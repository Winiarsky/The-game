"""Starting a game keeps its device transport; the play page connects once."""

from pathlib import Path
import shutil
import subprocess

import pytest

from dnd_board_game.ui.exploration_app import ExplorationUiSession
from dnd_board_game.ui.training_arena import start_training_trial
from tests.unit.test_initiative_panel import Board


class ConnectedBoard(Board):
    def __init__(self) -> None:
        super().__init__()
        self.resets = 0
        self.closed = False

    def reset_connection(self) -> None:
        self.resets += 1

    def close(self) -> None:
        self.closed = True


@pytest.mark.parametrize('scenario', ['recruitment_arena', 'abandoned_watchtower'])
def test_reset_preserves_connected_board_and_custom_settings(tmp_path: Path, scenario: str) -> None:
    session = ExplorationUiSession(f'content/scenarios/{scenario}.json',
        observation_dir=tmp_path / 'observations', save_dir=tmp_path / 'saves')
    board = ConnectedBoard()
    session.attach_board_connection(board, backend='hardware')
    adapter = session.board_adapter
    session.board_serial_port = '/dev/custom-board'
    session.wled_url = 'http://test-leds'
    session.scan_timeout_s = 42
    session.reset()
    assert session.board_adapter is adapter
    assert session._board_payload()['connected']
    assert session.board_backend == 'hardware'
    assert session.board_serial_port == '/dev/custom-board'
    assert session.wled_url == 'http://test-leds'
    assert session.scan_timeout_s == 42
    assert session.ui_flow_stage.value == 'ready_to_start'
    assert board.resets == 1 and not board.closed
    if scenario == 'recruitment_arena':
        start_training_trial(session, 'garran', 'basic', 'humanoid')
        assert session.board_adapter is adapter
        assert session._board_selection_payload()['auto_arm']
    assert session.shutdown_board()
    assert board.closed
    session.reset()
    assert not session._board_payload()['connected']


def test_browser_connects_at_start_and_only_shows_real_failures(tmp_path: Path) -> None:
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if chrome is None:
        pytest.skip('Chrome/Chromium is required for startup browser regressions')
    source = Path('src/dnd_board_game/ui/static/exploration.js').read_text()
    startup = source[source.index('async function loadState()'):source.index('function render()')]
    connection = source[source.index('function renderBoardConnectionIndicator()'):
                        source.index('function toggleBoardFallback(')]
    harness = r"""
let state, busy = false, boardFallbackEnabled = false, boardConnectionNotice = '';
let boardConnectionInFlight = false, activeInteractionId, lastBoardSelectionRevision, chatInstanceOpen;
let pendingConnect, requests = [], scanSchedules = 0, connected = false, backend = 'hardware';
const synchronizeBoardSelection = () => {};
const refreshSessionLog = () => {};
const focusCombatDecision = () => {};
const setBusy = text => { busy = Boolean(text); };
const stopBoardScanLoop = async () => {};
const scheduleAutomaticBoardScan = () => { if (state.board.connected && !busy) scanSchedules++; };
const render = () => { renderBoardConnectionIndicator(); renderBoardFallback(); };
function payload() { return {board: {connected, backend: connected ? backend : 'none',
  configured_backend: backend, board_serial_port: '/dev/test', wled_url: 'http://test-leds'}}; }
window.fetch = async (path, options) => {
  requests.push(path);
  if (path === '/api/state') return {json: async () => payload()};
  check(JSON.parse(options.body).backend === backend, 'wrong backend');
  return new Promise(resolve => { pendingConnect = ok => {
    connected = ok; resolve({ok, json: async () => ok ? payload() : {error: 'offline', state: payload()}});
  }; });
};
function check(ok, message) { if (!ok) throw new Error(message); }
async function flush() { for (let i = 0; i < 8; i++) await Promise.resolve(); }
async function run() {
  for (const kind of ['hardware', 'simulator']) {
    backend = kind; connected = false; requests = []; scanSchedules = 0;
    const loading = loadState(); await flush();
    check(requests.join(',') === '/api/state,/api/board/configure', 'startup did not connect exactly once');
    check(busy && boardConnectionInFlight, 'connection not marked pending');
    check(document.getElementById('board-disconnected-banner').hidden, 'false failure during startup');
    check(document.querySelector('#board-connection-indicator span:last-child').textContent.includes('Łączę'), 'missing connecting status');
    await retryBoardConnection();
    check(requests.length === 2, 'duplicate retry opened another connection');
    pendingConnect(true); await loading;
    check(state.board.connected && !busy && !boardConnectionInFlight, 'connection did not finish');
    check(scanSchedules > 0, 'setup scan not scheduled after connection');
    requests = []; await loadState();
    check(requests.join(',') === '/api/state', 'reopened an existing connection');
  }
  connected = false; requests = [];
  const failed = loadState(); await flush(); pendingConnect(false); await failed;
  check(!document.getElementById('board-disconnected-banner').hidden, 'real failure hidden');
  check(boardConnectionNotice.includes('Nie udało'), 'failure lacks explanation');
  const retry = retryBoardConnection(); await flush(); pendingConnect(true); await retry;
  check(state.board.connected && !boardConnectionNotice, 'manual recovery failed');
  connected = false; boardFallbackEnabled = true; requests = []; await loadState();
  check(requests.join(',') === '/api/state', 'ignored explicit fallback choice');
  boardFallbackEnabled = false; backend = 'none'; requests = []; await loadState();
  check(requests.join(',') === '/api/state', 'ignored disabled backend');
  document.getElementById('result').textContent = 'PASS';
}
run().catch(error => { document.getElementById('result').textContent = 'FAIL: ' + error.stack; });
"""
    page = tmp_path / 'startup.html'
    page.write_text('<pre id="result">PENDING</pre><div id="board-connection-indicator"><span></span><span></span></div>'
        '<div id="board-disconnected-banner" hidden></div><div id="board-disconnected-copy"></div>'
        '<script>' + startup + connection + harness + '</script>')
    result = subprocess.run([chrome, '--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
        '--no-first-run', '--disable-background-networking', '--no-proxy-server',
        f'--user-data-dir={tmp_path / "chrome"}', '--dump-dom', page.as_uri()],
        capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr[-1500:]
    assert '<pre id="result">PASS</pre>' in result.stdout, result.stdout[:2200]
