"""Run the actual browser scheduler with controlled promises and timers."""

from pathlib import Path
import shutil
import subprocess

import pytest


def test_scan_timers_respect_pending_commands_and_newer_requests(tmp_path: Path) -> None:
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if chrome is None:
        pytest.skip("Chrome/Chromium is required for browser scheduling regressions")
    source = Path("src/dnd_board_game/ui/static/exploration.js").read_text()
    scheduler = source[source.index("function scheduleAutomaticBoardScan()"):
                       source.index("async function scanBoard()")]
    receiver = source[source.index("async function performBoardScan("):
                      source.index("function stopBoardScanLoop(")]
    harness = r"""
let timers = new Map(), timerId = 0;
window.setTimeout = fn => { timers.set(++timerId, fn); return timerId; };
window.clearTimeout = id => timers.delete(id);
let selection = {revision: 'menu'}, busy = false, syncing = false;
let boardAutoArmTimer = null, boardPanelSyncPromise = null, boardScanStopPromise = null;
let boardScanInFlight = false, boardScanPromise = null, boardScanToken = 1;
let boardListeningRevision = '', lastAttemptedBoardRevision = '', boardInputPhase = '';
let state = {}, boardScanError = '', scans = 0, scheduled = 0, initialized = 0;
const currentBoardSelection = () => selection;
const boardSelectionCanAutoArm = () => !busy;
const syncBrowserBoardPanel = () => syncing;
const updateBoardInputPresentation = () => {};
const stopBoardScanLoop = () => {};
const scanBoardOnce = () => { scans++; };
const initializeKeyboardRollWizard = () => { initialized++; };
const focusCombatDecision = () => {};
const handleBoardPanelEvent = () => { busy = true; };
function check(ok, message) { if (!ok) throw new Error(message); }
function tick() {
  const batch = [...timers.values()]; timers.clear(); batch.forEach(fn => fn());
}
async function run() {
  scheduleAutomaticBoardScan(); busy = true; tick();
  check(scans === 0, 'timer started a scan while confirming an action');
  busy = false; scheduleAutomaticBoardScan(); selection = {revision: 'next'}; tick();
  check(scans === 0, 'timer started a scan for an obsolete menu');
  scheduleAutomaticBoardScan(); syncing = true; scheduleAutomaticBoardScan();
  check(timers.size === 0, 'old timer survived browser panel registration');
  syncing = false; scheduleAutomaticBoardScan(); tick();
  check(scans === 1, 'current menu did not rearm');

  // A corner press is dispatched on the next event-loop turn. Its old menu
  // must not be rearmed by the completed request's finally block.
  window.fetch = async () => ({ok: true, json: async () => ({panel_event: {slot: 28}})});
  boardScanInFlight = true;
  await performBoardScan({revision: 'next', automatic: true, token: 1});
  check(timers.size === 1 && initialized === 0, 'scan rearmed before corner dispatch');
  tick(); tick();
  check(busy && scans === 1, 'corner confirmation raced another scan');

  // An obsolete response must not clear the newer request's lock/promise.
  let resolveFetch;
  window.fetch = () => new Promise(resolve => { resolveFetch = resolve; });
  const old = performBoardScan({revision: 'old', automatic: true, token: 1});
  boardScanToken = 2; boardScanInFlight = true;
  const newer = Promise.resolve(); boardScanPromise = newer;
  resolveFetch({ok: true, json: async () => ({})}); await old;
  check(boardScanInFlight && boardScanPromise === newer, 'old request cleared newer scan');
  document.getElementById('result').textContent = 'PASS';
}
run().catch(error => { document.getElementById('result').textContent = 'FAIL: ' + error.stack; });
"""
    page = tmp_path / "scheduler.html"
    page.write_text('<pre id="result">PENDING</pre><script>' + scheduler + receiver + harness + '</script>')
    result = subprocess.run(
        [chrome, "--headless", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
         "--no-first-run", "--disable-background-networking", "--no-proxy-server",
         f"--user-data-dir={tmp_path / 'chrome'}", "--dump-dom", page.as_uri()],
        capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stderr[-1500:]
    assert '<pre id="result">PASS</pre>' in result.stdout, result.stdout[:2000]


def test_dice_panel_keeps_context_across_values_and_changes_it_on_review(tmp_path: Path) -> None:
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if chrome is None:
        pytest.skip('Chrome/Chromium is required for browser regressions')
    source = Path('src/dnd_board_game/ui/static/board_panel.js').read_text()
    harness = r"""
let state = {board_selection: {panel_enabled: true}}, busy = false;
let keyboardRollWizard = {steps: [{raw: 10, min: 1, max: 20}], index: 0, review: false};
let schedules = 0;
const sharedManaPanel = () => null;
const scheduleAutomaticBoardScan = () => { schedules++; };
const renderKeyboardRollWizard = () => {
  document.getElementById('keyboard-roll-wizard-input').value = keyboardRollWizard.steps[0].raw;
};
const triggerPrimaryAction = () => { keyboardRollWizard.review = true; };
function check(value, message) { if (!value) throw new Error(message); }
try {
  const initial = desiredBoardPanel();
  state.board_selection.panel_context = initial.context;
  for (let i = 0; i < 20; i++) changeRollPanelValue(1);
  check(keyboardRollWizard.steps[0].raw === 20, 'maximum was exceeded');
  check(desiredBoardPanel().context === initial.context, 'value changed context');
  check(desiredBoardPanel().slots.join(',') === '26,27,28', 'mask changed at bound');
  check(syncBrowserBoardPanel() === false, 'same die required a new registration');
  handleBoardPanelEvent({panel_event: {slot: 28, context: initial.context}, board_selection: state.board_selection});
  check(desiredBoardPanel().context !== initial.context, 'review kept dice context');
  check(desiredBoardPanel().slots.join(',') === '28,29', 'review controls are wrong');
  document.getElementById('result').textContent = 'PASS';
} catch (error) { document.getElementById('result').textContent = 'FAIL: ' + error.stack; }
"""
    page = tmp_path / 'dice-context.html'
    page.write_text('<input id="keyboard-roll-wizard-input" value="10"><pre id="result">PENDING</pre><script>'
                    + source + harness + '</script>')
    result = subprocess.run([chrome, '--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
                             '--no-first-run', '--disable-background-networking', '--no-proxy-server',
                             f'--user-data-dir={tmp_path / "chrome"}', '--dump-dom', page.as_uri()],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr[-1500:]
    assert '<pre id="result">PASS</pre>' in result.stdout, result.stdout[:2200]


def test_cancel_reload_and_retry_release_the_previous_scan(tmp_path: Path) -> None:
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if chrome is None:
        pytest.skip('Chrome is required for browser scan recovery')
    source = Path('src/dnd_board_game/ui/static/exploration.js').read_text()
    stopper = source[source.index('function stopBoardScanLoop('):source.index('function selectBoardPosition(')]
    receiver = source[source.index('async function performBoardScan('):source.index('function stopBoardScanLoop(')]
    manual = source[source.index('async function scanBoard()'):source.index('function scanBoardOnce(')]
    loader = source[source.index('async function loadState()'):source.index('function render()')]
    harness = r'''
let state = {board:{connected:true}, board_selection:{revision:'actions'}};
let boardAutoArmTimer=null, boardScanStopPromise=null, boardScanInFlight=false, boardScanPromise=null;
let boardScanToken=0, boardListeningRevision='', lastAttemptedBoardRevision='', boardScanError='', boardInputPhase='';
let activeInteractionId=null, lastBoardSelectionRevision=0, chatInstanceOpen=false;
let resets=0, scans=0, rendered=false, delayedResponse=null;
const currentBoardSelection = () => state.board_selection;
const updateBoardInputPresentation = () => {};
const scheduleAutomaticBoardScan = () => {};
const initializeKeyboardRollWizard = () => {};
const focusCombatDecision = () => {};
const refreshSessionLog = () => {};
const synchronizeBoardSelection = () => {};
const render = () => {rendered=true;};
const scanBoardOnce = () => {scans++;};
function check(ok, message) {if (!ok) throw new Error(message);}
window.fetch = async path => {
 if(path === '/api/board/scan') return new Promise(resolve => {delayedResponse=resolve;});
 if(path === '/api/board/reset-scan') {
  resets++;
  if(delayedResponse) {delayedResponse({ok:true,json:async()=>({})}); delayedResponse=null;}
  return {ok:true};
 }
 if(path === '/api/state') return {ok:true,json:async()=>state};
 throw new Error('unexpected fetch ' + path);
};
function startWaiting() {
 boardScanInFlight=true;
 lastAttemptedBoardRevision='actions';
 boardScanPromise=performBoardScan({revision:'actions', automatic:true, token:++boardScanToken});
}
async function run() {
 startWaiting();
 const stopping=stopBoardScanLoop();
 check(stopBoardScanLoop() === stopping, 'cancellation was not coalesced');
 await stopping;
 check(resets===1 && !boardScanInFlight && boardScanPromise===null, 'cancelled scan left a browser lock');
 check(lastAttemptedBoardRevision==='', 'cancel suppressed same-menu rearm');
 startWaiting();
 await scanBoard();
 check(resets===2 && scans===1, 'manual retry did not cancel and restart a waiting scan');
 // Reload has no promise for the old page; reset must still precede rendering.
 await loadState();
 check(resets===3 && rendered, 'reload did not clear orphan server scan');
 // An unrelated newer request remains authoritative, even during cancellation.
 startWaiting();
 const oldStop=stopBoardScanLoop();
 boardScanToken++;
 const newer=Promise.resolve(); boardScanPromise=newer; boardScanInFlight=true;
 await oldStop;
 check(boardScanInFlight && boardScanPromise===newer, 'cancellation cleared newer scan');
 // A rejected reset must show its error without waiting for an orphan forever.
 window.fetch = async () => ({ok:false,json:async()=>({error:'Reset nie powiódł się'})});
 boardScanPromise = new Promise(() => {});
 await scanBoard();
 check(boardInputPhase==='error' && boardScanError==='Reset nie powiódł się', 'reset failure was hidden');
 check(scans===1, 'started another scan after rejected reset');
 document.getElementById('result').textContent='PASS';
}
run().catch(error => {document.getElementById('result').textContent='FAIL: ' + error.stack;});
'''
    page = tmp_path / 'scan-recovery.html'
    page.write_text('<pre id="result">PENDING</pre><script>' + stopper + receiver + manual + loader + harness + '</script>')
    result = subprocess.run([chrome, '--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
                             '--no-first-run', '--disable-background-networking', '--no-proxy-server',
                             f'--user-data-dir={tmp_path / "chrome"}', '--dump-dom', page.as_uri()],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr[-1500:]
    assert '<pre id="result">PASS</pre>' in result.stdout, result.stdout[:2500]
