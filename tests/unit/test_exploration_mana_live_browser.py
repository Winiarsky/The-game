"""Actual Flask page, assets, HTTP commands and browser input for a complete object lesson."""
from pathlib import Path
import shutil
import subprocess
from threading import Event, Thread

import pytest
from werkzeug.serving import make_server

from dnd_board_game.ui.routes import create_app
from tests.unit.test_recruitment_arena import arena


@pytest.mark.parametrize('lesson', ['object', 'npc', 'abort'])
def test_live_party_runes_focus_rolls_and_return(tmp_path: Path, lesson: str):
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
  await waitFor(()=>document.querySelectorAll('.training-roster button').length===7 && !busy);
  for(const action of ['hero:erynd','subject:exploration','cases','case:LESSON']) {
    const option=state.training_arena.menu.options.find(o=>o.action===action);
    if(!option)throw Error('Missing menu rune '+action);
    await api('/api/board/select',{col:19,row:29-option.slot},'Menu samouczka…');
    await waitFor(()=>!busy);
  }
  await waitFor(()=>state.exploration_mana?.active && !busy);
  if(state.exploration_mana.hero!=='erynd')throw Error('Wrong hero');
  await press('acknowledge');
  await waitFor(()=>state.exploration_mana.phase==='setup' && !busy);
  while(state.exploration_mana.phase==='setup')await press('acknowledge');
  const sync=()=>waitFor(()=>keyboardRollWizard && !busy && !boardPanelSyncPromise && desiredBoardPanel()?.context===state.board_selection.panel_context);
  const diePress=async slot=>{
    await sync();await api('/api/board/select',{col:19,row:29-slot},'Kość…');
    await new Promise(r=>setTimeout(r,30));
  };
  let checkedDice=false,checkedImpact=false,aborted=false;
  for(let i=0;i<160;i++) {
    const p=state.exploration_mana;
    if(p.phase==='result')break;
    if(p.mana.phase==='reveal'||p.mana.phase==='burn')await press('color',p.board_choices.find(c=>c.action==='color').extra);
    else if(p.mana.phase==='choose')await press('take',{index:0});
    else if(p.phase==='turn')await press('test',{bonus:0});
    else if(p.attempt?.phase==='roll') {
      await sync();
      if(boardSelectionPausedForScreenInput())throw Error('Dice paused board');
      if(ABORT_CASE) {
        document.querySelectorAll('#training-tools button')[1].click();
        await waitFor(()=>!state.exploration_mana.active&&!busy);
        if(keyboardRollWizard||document.getElementById('exploration-mana-roll'))throw Error('Stale dice after exit');
        aborted=true;break;
      }
      const die=p.attempt.die;
      if(keyboardRollWizard.steps.length!==1)throw Error('Wrong dice count');
      await waitFor(()=>document.activeElement?.id==='keyboard-roll-wizard-input');
      const input=document.getElementById('keyboard-roll-wizard-input');
      input.value=String(die-1);input.dispatchEvent(new Event('input',{bubbles:true}));
      await diePress(27);await sync();
      if(Number(document.getElementById('keyboard-roll-wizard-input').value)!==die)throw Error('Plus missed focus');
      await diePress(26);await sync();
      if(Number(document.getElementById('keyboard-roll-wizard-input').value)!==die-1)throw Error('Minus missed focus');
      await diePress(28);await sync();
      if(!keyboardRollWizard.review)throw Error('Missing summary');
      if(!document.getElementById('keyboard-roll-wizard').innerText.includes('Premia doliczona raz'))throw Error('Modifier summary missing');
      await diePress(29);await sync();
      await diePress(27);await sync();
      await diePress(28);await sync();
      if(!document.querySelector('.keyboard-roll-combined-summary').innerText.includes(`${die} +${p.attempt.modifier_total} = ${die+p.attempt.modifier_total}`))throw Error('Incorrect single modifier');
      checkedDice ||= p.phase==='check';checkedImpact ||= p.phase==='impact';
      await api('/api/board/select',{col:19,row:1},'Potwierdź…');
      await waitFor(()=>state.exploration_mana.revision!==p.revision&&!busy);
    }
    else if(p.phase==='reaction')await press('react');
    else await press('advance');
  }
  if(!aborted) {
    if(state.exploration_mana.phase!=='result'||!state.exploration_mana.completed)throw Error('Confrontation unfinished');
    if(!checkedDice||!checkedImpact)throw Error('Missing check or influence');
    if(document.documentElement.scrollWidth>innerWidth)throw Error('Horizontal overflow');
    await press('next');await waitFor(()=>!state.exploration_mana.active&&!busy);
  }
  if(state.training_arena.menu.view!=='cases'||state.training_arena.menu.subject!=='exploration')throw Error('Wrong return menu');
  report.textContent='PASS';
 }catch(error){report.textContent='FAIL: '+error.stack;}
 await fetch('/__test/exploration-result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:report.textContent})});
})();
</script>
'''
    harness=harness.replace('LESSON','object' if lesson == 'abort' else lesson).replace('ABORT_CASE', 'true' if lesson == 'abort' else 'false')
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
        assert finished.wait(45), 'Browser did not report the lesson result'
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
