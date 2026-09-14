"""Actual Flask page, assets, HTTP commands and browser input for a complete object lesson."""
from pathlib import Path
import shutil
import subprocess
from threading import Event, Thread

import pytest
from werkzeug.serving import make_server

from dnd_board_game.ui.routes import create_app
from tests.unit.test_recruitment_arena import arena


@pytest.mark.parametrize('lesson', ['object', 'bust'])
def test_live_page_opens_and_resolves_erynd_object_lesson(tmp_path: Path, lesson: str):
    chrome=shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome required')
    s=arena(tmp_path)
    app=create_app(s)
    finished=Event()
    reported={}
    @app.post('/__test/exploration-result')
    def report_result():
        from flask import request
        reported.update(request.get_json())
        finished.set()
        return {'ok': True}
    harness=r'''
<script>
(async()=>{
 const report=document.createElement('pre');report.id='live-mana-result';document.body.appendChild(report);
 const waitFor=async predicate=>{for(let i=0;i<160;i++){if(predicate())return;await new Promise(r=>setTimeout(r,50));}throw Error('Timed out waiting for lesson');};
 const press=async(action,extra={})=>{
  const c=state.exploration_mana.board_choices.find(c=>c.action===action && Object.entries(extra).every(([k,v])=>c.extra[k]===v));
  if(!c)throw Error('Missing board choice: '+action);
  await api('/api/board/select',{col:19,row:29-c.slot},'Runa…');
 };
 try {
  await waitFor(()=>document.querySelectorAll('.mana-hero-entry').length===7 && !busy);
  await api('/api/exploration-mana',{action:'open',hero:'erynd',lesson:'LESSON',revision:state.exploration_mana.revision},'Lekcja…');
  await waitFor(()=>state.exploration_mana?.active && !busy);
  if(state.exploration_mana.hero!=='erynd')throw Error('Wrong hero');
  await press('acknowledge');
  await waitFor(()=>state.exploration_mana.phase==='setup' && !busy);
  while(state.exploration_mana.phase==='setup')await press('acknowledge');
  await press('start');
  await waitFor(()=>state.exploration_mana.attempt?.phase==='offer' && !busy);
  for(const color of ('LESSON'==='bust'?'CCNF':'C')) {
    if(state.exploration_mana.attempt.phase==='decision')await press('draw');
    await press('choose',{color});
  }
  if(state.exploration_mana.attempt.phase==='decision')await press('stand');
  await waitFor(()=>document.getElementById('exploration-mana-roll') && !busy);
  const sync=()=>waitFor(()=>keyboardRollWizard && !busy && !boardPanelSyncPromise && desiredBoardPanel()?.context===state.board_selection.panel_context);
  const diePress=async slot=>{
    await sync();
    await api('/api/board/select',{col:19,row:29-slot},'Kość…');
    await new Promise(r=>setTimeout(r,30));
    await sync();
  };
  await sync();
  await waitFor(()=>document.activeElement?.id==='keyboard-roll-wizard-input');
  if(keyboardRollWizard.steps.length!==('LESSON'==='bust'?2:1))throw Error('Wrong dice count');
  if(boardSelectionPausedForScreenInput())throw Error('Dice paused the board');
  await diePress(27);
  if(document.getElementById('keyboard-roll-wizard-input').value!=='11')throw Error('Plus missed focus');
  await diePress(26);
  if(document.getElementById('keyboard-roll-wizard-input').value!=='10')throw Error('Minus missed focus');
  await diePress(28);
  if('LESSON'==='bust') {
    if(keyboardRollWizard.index!==1 || keyboardRollWizard.review)throw Error('Second die skipped');
    await diePress(26); // second die 9
    await diePress(28);
  }
  if(!keyboardRollWizard.review || state.exploration_mana.attempt.phase!=='roll')throw Error('No review before resolution');
  if(!document.getElementById('keyboard-roll-wizard').innerText.includes('Premia doliczona raz'))throw Error('Modifier summary missing');
  await diePress(29);
  const original='LESSON'==='bust'?9:10;
  if(Number(document.getElementById('keyboard-roll-wizard-input').value)!==original)throw Error('Correction lost die');
  await diePress('LESSON'==='bust'?26:27);
  await diePress(28);
  const raw='LESSON'==='bust'?8:11;
  if(!document.querySelector('.keyboard-roll-combined-summary').innerText.includes(`${raw} +${state.exploration_mana.attempt.modifier_total} = ${raw+state.exploration_mana.attempt.modifier_total}`))throw Error('Summary adds modifier more than once or wrong die');
  await sync();
  await api('/api/board/select',{col:19,row:1},'Zatwierdź rzut…');
  await waitFor(()=>state.exploration_mana.attempt?.phase==='result' && !busy);
  if(state.exploration_mana.attempt.rolls.join(',')!==('LESSON'==='bust'?'10,8':'11'))throw Error('Wrong natural dice sent');
  if(!document.querySelector('#training-arena-panel').innerText.includes('Praktyka terenowa'))throw Error('Passive missing');
  if(document.documentElement.scrollWidth>innerWidth)throw Error('Horizontal overflow');
  report.textContent='PASS';
 }catch(error){report.textContent='FAIL: '+error.stack;}
 await fetch('/__test/exploration-result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:report.textContent})});
})();
</script>
'''
    harness=harness.replace('LESSON',lesson)
    @app.after_request
    def inject(response):
        from flask import request
        if request.path=='/play' and response.status_code==200:
            response.set_data(response.get_data(as_text=True).replace('</body>',harness+'</body>'))
        return response
    server=make_server('127.0.0.1',0,app,threaded=True)
    thread=Thread(target=server.serve_forever,daemon=True)
    thread.start()
    process=None
    try:
        process=subprocess.Popen([chrome,'--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',
            '--no-first-run','--disable-background-networking','--no-proxy-server',
            f'--user-data-dir={tmp_path/"chrome"}','--window-size=390,1000',
            f'http://127.0.0.1:{server.server_port}/play'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
        assert finished.wait(25), 'Browser did not report the lesson result'
        assert reported.get('result')=='PASS', reported
    finally:
        if process:
            process.terminate()
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=5)
        server.shutdown()
        thread.join(timeout=3)
