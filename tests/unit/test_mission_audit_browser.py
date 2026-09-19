"""Confrontation layout and board input in the real Mission 0 page."""
from pathlib import Path
from threading import Event, Thread
import shutil
import subprocess

from flask import request
import pytest
from werkzeug.serving import make_server
from dnd_board_game.ui.exploration_app import create_app
from tests.unit.test_confrontation_presentation import start


@pytest.mark.parametrize('case', ['six_heroes', 'initiative'])
def test_audit_ui_regressions(tmp_path: Path, case: str):
    width,height=1131,720
    chrome=shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome: pytest.skip('Chrome required')
    if case == 'six_heroes':
        s=start(tmp_path,6)
    else:
        from tests.unit.test_mission_zero import session, stage, send
        s=session(tmp_path)
        stage(s,'arrival');send(s,'battle')
        while not s.encounter_setup_flow.completed:
            if s.encounter_setup_flow.is_player_start_step:
                s.assign_encounter_player_start_position(s.encounter_setup_flow.remaining_player_start_positions()[0])
            else:
                s.confirm_encounter_setup_step()
        s.start_encounter_initiative()
    s.configured_board_backend='none'
    app=create_app(s);done=Event();report={}
    @app.post('/__test/result')
    def report_result():
        report.update(request.get_json());(tmp_path/'browser-result.json').write_text(__import__('json').dumps(report,ensure_ascii=False,indent=2));done.set();return {'ok':True}
    harness=r'''<script>
(async()=>{
const CASE='__CASE__';
const check=(v,m)=>{if(!v)throw Error(m)};
const wait=async f=>{for(let i=0;i<180;i++){if(f())return;await new Promise(r=>setTimeout(r,25))}throw Error('timeout')};
const field=async(slot)=>{await wait(()=>!busy&&!boardPanelSyncPromise);await api('/api/board/select',{col:19,row:29-slot},'');await wait(()=>!busy)};
const press=async(action,extra=null)=>{const c=state.exploration_mana.board_choices.find(c=>c.action===action&&(!extra||Object.entries(extra).every(([k,v])=>c.extra[k]===v)));check(c,'missing '+action);await field(c.slot)};
try{
 await wait(()=>state&&!busy);
 if (CASE === 'six_heroes') {
  await wait(()=>state.exploration_mana?.active);
  await press('acknowledge');while(state.exploration_mana.phase==='approach') await press('approach',{approach:state.exploration_mana.approaches.find(a=>a.available).id});await press('acknowledge');
  for(let turn=0;turn<5;turn++) {
   while(state.exploration_mana.mana.phase==='reveal') await press('color');
   await press('take',{index:0});await press('support');
   while(state.exploration_mana.mana.phase==='burn') await press('color');
   await press('advance');
  }
  const p=state.exploration_mana;
  check(p.actor===p.party[5].id,'sixth hero not active');
  await new Promise(r=>requestAnimationFrame(r));
  let area=document.querySelector('.confrontation-scroll'), card=area.querySelector('.current');
  check(area.scrollTop>0,'active sixth hero not scrolled into view');
  const a=area.getBoundingClientRect(),c=card.getBoundingClientRect();
  check(c.top>=a.top-1&&c.top<a.bottom-30,'active hero heading offscreen');
  const previous=area.scrollTop;
  await press('color');
  area=document.querySelector('.confrontation-scroll');
  check(Math.abs(area.scrollTop-previous)<2,'card report lost reading position');
  await press('take',{index:0});
  check(document.documentElement.scrollWidth<=innerWidth,'horizontal overflow');
  const detail=pooledManaPointsHtml({shared_mana:{pool_view:{phase:'ready',hands:[{hero:'garran',name:'Garran',total:7,cards:['B'],values:{B:7},color_passives:{B:{stackable:false,label:'Żelazna linia: pełny opis działania.',status:'Aktywne'}}}]}}},'garran');
  const node=document.createElement('div');node.innerHTML=detail;
  check(node.querySelector('summary').textContent.includes('Żelazna linia'),'passive name absent');
  check(!node.querySelector('summary').textContent.includes('pełny opis'),'passive not compact');
  check(node.querySelector('details p').textContent.includes('pełny opis'),'passive details lost');
  check(visibleActorEffects({effects:[{kind:'shared_offensive_used'},{kind:'mana_series_source'},{kind:'charge_feature'}]}).length===1,'internal counters visible');
  check(effectDisplayValue({kind:'charge_feature',value_label:'+1'})==='','feature displayed as +1');
 } else {
  await wait(()=>keyboardRollWizard?.initiative);
  for(let hero=0;hero<3;hero++) {
   await field(27);
   check(state.encounter_initiative.panel.values[0]===11,'+ did not change initiative');
   await field(26);
   check(state.encounter_initiative.panel.values[0]===10,'- did not change initiative');
   await field(28);
   await wait(()=>keyboardRollWizard?.initiative&&keyboardRollWizard.review);
   await field(28);
   if(hero<2) await wait(()=>keyboardRollWizard?.initiative&&!keyboardRollWizard.review);
  }
  await wait(()=>state.combat&&!keyboardRollWizard);
  check(state.combat.shared_mana,'combat mana not initialized');
 }
 await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:'PASS'})});
}catch(e){await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:e.stack,body:document.body.innerText.slice(-5000),wizard:keyboardRollWizard,initiative:state?.encounter_initiative,mission:state?.mission?.stage,dialogs:[...document.querySelectorAll('dialog[open]')].map(e=>e.id)})})}
})();</script>'''
    harness=harness.replace('__CASE__',case)
    error_hook="""<script>window.alert=message=>{throw Error(message)};window.addEventListener('error',e=>fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:String(e.message)+' '+e.filename+':'+e.lineno})}));</script>"""
    @app.after_request
    def inject(response):
        if request.path=='/play' and response.status_code==200:
            response.set_data(response.get_data(as_text=True).replace('<head>','<head>'+error_hook).replace('</body>',harness+'</body>'))
        return response
    server=make_server('127.0.0.1',0,app,threaded=True);worker=Thread(target=server.serve_forever,daemon=True);worker.start();process=None
    try:
        process=subprocess.Popen([chrome,'--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run',
            '--disable-background-networking','--no-proxy-server',f'--user-data-dir={tmp_path/"chrome"}',f'--window-size={width},{height + 143}',
            f'http://127.0.0.1:{server.server_port}/play'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
        assert done.wait(60),'Browser did not report'
        assert report.get('result')=='PASS',report
    finally:
        if process:
            process.terminate()
            try:process.communicate(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.communicate(timeout=5)
        server.shutdown();worker.join(timeout=2)
