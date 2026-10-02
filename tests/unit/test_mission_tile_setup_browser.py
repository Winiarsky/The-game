"""Tile artwork, grouped setup and accept through the real browser/board routes."""
from pathlib import Path
from threading import Event, Thread
import shutil
import subprocess

from flask import request
import pytest
from werkzeug.serving import make_server
from dnd_board_game.ui.exploration_app import create_app
from tests.unit.test_mission_zero import session, stage, send


@pytest.mark.parametrize('width',[390,1100])
def test_tile_setup_preview_and_accept(tmp_path: Path,width: int) -> None:
    chrome=shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome required')
    s=session(tmp_path)
    s.configured_board_backend='none'
    stage(s,'guild_setup',index=0)
    app=create_app(s)
    done=Event()
    report={}

    @app.post('/__test/battle')
    def battle():
        stage(s,'arrival')
        return send(s,'battle')

    @app.post('/__test/result')
    def result():
        report.update(request.get_json())
        done.set()
        return {'ok':True}

    harness=r'''<script>
(async()=>{
 const check=(v,m)=>{if(!v)throw Error(m)};
 const wait=async f=>{for(let i=0;i<160;i++){if(f())return;await new Promise(r=>setTimeout(r,25))}throw Error('timeout')};
 const accept=async()=>{await wait(()=>!busy&&!boardPanelSyncPromise);await api('/api/board/select',{col:19,row:1},'');await wait(()=>!busy)};
 const pictures=()=>[...document.querySelectorAll('[data-setup-cutout]')].filter(el=>el.getBoundingClientRect().height>0);
 try{
  await wait(()=>state?.mission?.setup&&!busy);
  check(!document.querySelector('#mission-panel .mission-map'),'no full map');
  check(pictures().map(el=>el.dataset.setupCutout).join(',')==='G01','large office first');
  const illustration=pictures()[0].querySelector('svg image');
  check(illustration&&(await fetch(illustration.getAttribute('href'))).ok,'cutout illustration available');
  if(innerWidth>=760)check(pictures()[0].getBoundingClientRect().right<document.querySelector('.mission-tile-instruction').getBoundingClientRect().left,'art left, instructions right');
  check(document.documentElement.scrollWidth<=innerWidth,'guild overflow');
  check(state.board_selection.legal_positions.length===4,'accept, scrolling and menu are selectable');
  await accept();check(pictures()[0].dataset.setupCutout==='G02','second large tile');
  const backChoice=document.querySelector('[data-mission-slot="29"]');
  check(backChoice?.textContent.includes('Poprzedni element'),'guild back visible');
  backChoice.click();await wait(()=>!busy&&pictures()[0]?.dataset.setupCutout==='G01');
  await accept();check(pictures()[0].dataset.setupCutout==='G02','guild tile can be confirmed again');
  const rev=state.mission.revision;
  document.querySelector('[data-mission-slot="28"]').click();await wait(()=>!busy&&state.mission.revision!==rev);
  check(pictures()[0].dataset.setupCutout==='G03','small exit after large tiles');
  await accept();check(!pictures().length&&document.querySelector('.mission-figurine-preview'),'single party figure');
  await accept();check(state.mission.stage==='guild_hub','setup ends in guild');
  check(!document.querySelector('[data-mission-slot]'),'guild has no destination buttons');
  check(state.board_selection.legal_positions.length===5,'two map fields, scroll controls and menu');
  const select=async(col,row)=>{await wait(()=>!busy&&!boardPanelSyncPromise);await api('/api/board/select',{col,row},'');await wait(()=>!busy)};
  await select(14,8);check(state.mission.stage==='arena_unavailable','arena information');
  await select(19,0);check(state.mission.stage==='guild_hub','back to guild');
  await select(5,7);check(state.mission.stage==='brief','Nessa selected on board');
  check(getComputedStyle(document.querySelector('.mission-art')).objectFit==='contain','full Nessa artwork');
  const prose=document.querySelector('.mission-narrative-text');
  if(innerWidth>=760)check(document.querySelector('.mission-art').getBoundingClientRect().right<=prose.getBoundingClientRect().left,'briefing art left');
  const choices=[...document.querySelectorAll('[data-mission-slot]')];
  check(choices.length===4,'four dialog choices');
  check(choices.every(el=>el.getBoundingClientRect().bottom<=innerHeight),'all dialog choices within viewport');
  prose.insertAdjacentHTML('beforeend','<p>Próba długiego opisu.</p>'.repeat(40));
  const revision=state.mission.revision;
  await select(19,3);await wait(()=>missionScrollArea().scrollTop>0);
  check(state.mission.revision===revision,'scroll preserves dialogue');
  check(choices.every(el=>el.getBoundingClientRect().bottom<=innerHeight),'choices stay visible while scrolling');
  await api('/__test/battle',{},'');await wait(()=>!busy);
  const groups=[['P05'],['P06'],['P07'],['P01','P02'],['P03','P04'],['P08','P09','P10'],['P11','P12'],['P13','P14']];
  for(let i=0;i<groups.length;i++){
   check(JSON.stringify(pictures().map(el=>el.dataset.setupCutout))===JSON.stringify(groups[i]),'battle batch '+i);
   check(document.getElementById('mission-panel').hidden,'no duplicate mission map');
   check(document.documentElement.scrollWidth<=innerWidth,'battle overflow');
   const before=state.encounter_setup.current_index;
   if(i===2){
    check(document.querySelector('[data-setup-back]'),'battle back visible');
    await select(19,0);
    check(state.encounter_setup.current_index===before-1,'back reopens previous batch');
    check(JSON.stringify(pictures().map(el=>el.dataset.setupCutout))===JSON.stringify(groups[i-1]),'previous artwork');
    await accept();check(state.encounter_setup.current_index===before,'accept corrected batch');
   }
   if(i===1){document.querySelector('[data-setup-accept]').click();await wait(()=>!busy&&state.encounter_setup.current_index!==before)}
   else await accept();
   check(state.encounter_setup.current_index===before+1,'one accept advances one batch');
  }
  check(state.encounter_setup.current_step.requires_board_assignment,'figures after terrain');
  check(!document.querySelector('.battle-map-preview'),'no full map during figure setup');
  while(state.encounter_setup.current_step?.requires_board_assignment){
   const step=state.encounter_setup.current_step;
   const actor=state.actors.find(a=>a.id===step.assignment_actor_id);
   await wait(()=>document.querySelector('.setup-assignment-hero img')?.complete&&document.querySelector('.setup-assignment-hero img').naturalWidth);
   const portrait=document.querySelector('.setup-assignment-hero img');
   check(portrait.getAttribute('src')===actor.portrait_url,'portrait follows called hero');
   check(portrait.alt===step.assignment_actor_name,'portrait names called hero');
   check(Math.abs(portrait.getBoundingClientRect().height-100)<1,`portrait size: ${portrait.getBoundingClientRect().height}, CSS ${getComputedStyle(portrait).height}`);
   if(innerWidth>=760)check(document.querySelector('.setup-current-command').getBoundingClientRect().bottom<=innerHeight,'placement clipped');
   const position=step.available_positions[0];
   await select(position[0],position[1]);
   check(state.encounter_setup.current_step.assignment_actor_id===actor.id,'selection changed called hero before confirmation');
   await accept();
  }
  while(state.encounter_setup.status==='active')await accept();
  await accept();
  for(let hero=0;hero<3;hero++){
   await wait(()=>keyboardRollWizard?.initiative&&!busy);
   const prompt=state.encounter_initiative.current_prompt;
   const actor=state.actors.find(a=>a.id===prompt.actor_id);
   const portrait=()=>document.querySelector('#keyboard-roll-wizard .initiative-roll-portrait');
   await wait(()=>portrait()?.complete&&portrait().naturalWidth);
   check(portrait().getAttribute('src')===actor.portrait_url,'initiative portrait follows hero');
   check(portrait().alt===prompt.actor_name,'initiative portrait identity');
   check(portrait().getBoundingClientRect().width>=80,'initiative portrait large enough');
   check(document.querySelector('#keyboard-roll-wizard .keyboard-roll-wizard-kicker').textContent.includes(prompt.actor_name),'name beside portrait');
   check(document.documentElement.scrollWidth<=innerWidth,'initiative horizontal overflow');
   await select(19,3);check(state.encounter_initiative.panel.values[0]===11,'initiative plus');
   check(portrait().alt===prompt.actor_name,'portrait survives result adjustment');
   await accept();check(state.encounter_initiative.panel.review,'initiative summary');
   check(portrait().alt===prompt.actor_name,'portrait stays on summary');
   if(hero<2)await accept();
  }
  await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:'PASS'})});
 }catch(e){await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:e.stack,body:document.body.innerText.slice(-1800)})})}
})();</script>'''

    @app.after_request
    def inject(response):
        if request.path=='/play' and response.status_code==200:
            response.set_data(response.get_data(as_text=True).replace('</body>',harness+'</body>'))
        return response

    server=make_server('127.0.0.1',0,app,threaded=True)
    worker=Thread(target=server.serve_forever,daemon=True)
    worker.start()
    process=None
    try:
        process=subprocess.Popen([chrome,'--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',
            '--no-first-run','--disable-background-networking','--no-proxy-server',f'--user-data-dir={tmp_path/"chrome"}',
            f'--window-size={width},720',f'http://127.0.0.1:{server.server_port}/play'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
        assert done.wait(45),'Browser did not report'
        assert report.get('result')=='PASS',report
    finally:
        if process:
            process.terminate()
            try:process.communicate(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.communicate(timeout=5)
        server.shutdown()
        worker.join(timeout=2)
