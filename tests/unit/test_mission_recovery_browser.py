"""Real rune/field input, object confrontation and identification dice UI."""
from pathlib import Path
from threading import Event, Thread
import shutil
import subprocess

from flask import request
import pytest
from werkzeug.serving import make_server
from tests.unit.test_mission_recovery import party, finish
from tests.unit.test_mission_zero import stage
from dnd_board_game.ui.exploration_app import create_app
from dnd_board_game.ui import mission_zero as m, confrontation as c


@pytest.mark.parametrize('width,natural',[(1100,20),(390,1)])
def test_recovery_runes_room_ring_and_return(tmp_path: Path,width: int,natural: int):
    chrome=shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:pytest.skip('Chrome required')
    s=party(tmp_path);s.configured_board_backend='none';stage(s,'brief')
    app=create_app(s);done=Event();report={}
    @app.post('/__test/result')
    def report_result():
        report.update(request.get_json());done.set();return {'ok':True}
    @app.post('/__test/explore')
    def explore():
        finish(s,'success');stage(s,'explore',outcome='accepted');return s.state_payload()
    @app.post('/__test/search-success')
    def search_success():
        finish(s,'success');return s.state_payload()
    harness=r'''<script>
(async()=>{
const check=(v,m)=>{if(!v)throw Error(m)};
const wait=async f=>{for(let i=0;i<180;i++){if(f())return;await new Promise(r=>setTimeout(r,25))}throw Error('timeout '+state?.mission?.stage)};
const field=async(col,row)=>{await wait(()=>!busy&&!boardPanelSyncPromise);await api('/api/board/select',{col,row},'');await wait(()=>!busy)};
const press=async(action,extra=null,explore=false)=>{await wait(()=>!busy);const choices=explore?state.exploration_mana.board_choices:state.mission.choices;const c=choices.find(c=>c.action===action&&(!extra||Object.entries(extra).every(([k,v])=>c.extra[k]===v)));check(c,'missing '+action);await field(19,29-c.slot)};
try{
 await wait(()=>state?.mission&&!busy);
 await press('compliments');check(state.mission.choices.length===5,'five one-shot compliments');
 check([...document.querySelectorAll('[data-mission-slot]')].every(el=>el.getBoundingClientRect().bottom<=innerHeight),'all compliments accessible');
 await press('compliment',{option:'wounded'});await press('brief_back');
 check(!state.mission.choices.some(c=>c.action==='compliments'),'one chance');
 await press('negotiate');check(state.exploration_mana.first_test_bonus===2,'Nessa favour visible');
 await api('/__test/explore',{},'');await wait(()=>!busy);
 await field(14,7);await press('search',{room:'quarters'});
 check(state.exploration_mana.scene.kind==='object','room uses object confrontation');
 await press('acknowledge',null,true);while(state.exploration_mana.phase==='approach') await press('approach',null,true);await press('acknowledge',null,true);
 await press('color',{color:'C'},true);await press('color',{color:'B'},true);await press('take',{index:0},true);
 check(state.exploration_mana.party.some(p=>p.cards.length===1),'physical card actually taken');
 await api('/__test/search-success',{},'');await wait(()=>!busy);
 check(state.mission.text.body.includes('niezidentyfikowany'),'ring not revealed early');
 await press('identify_nimra');
 await wait(()=>keyboardRollWizard&&!busy&&!boardPanelSyncPromise);
 const input=document.getElementById('keyboard-roll-wizard-input');input.value=String(NATURAL===1?2:NATURAL-1);input.dispatchEvent(new Event('input',{bubbles:true}));
 await wait(()=>!boardPanelSyncPromise&&state.board_selection.panel_context===desiredBoardPanel()?.context);await field(19,NATURAL===1?3:2);
 await wait(()=>Number(document.getElementById('keyboard-roll-wizard-input')?.value)===NATURAL);
 await field(19,1);await wait(()=>keyboardRollWizard?.review&&!boardPanelSyncPromise);
 check(document.getElementById('keyboard-roll-wizard').textContent.includes('ST 15'),'identification review includes DC');
 await field(19,1);await wait(()=>!keyboardRollWizard&&state.mission.stage!=='identify_roll');
 if(NATURAL===1){
  check(state.mission.stage==='identify_failure','failed Nimra attempt');await press('ring_view');
  check(!state.mission.choices.some(c=>c.action==='identify_nimra'),'no retry');
 }else check(state.mission.stage==='ring_identified','identified on site');
 await press('ring_back');await press('back');
 await field(5,7);await press('collect',{room:'armory'});await press('back');
 await field(4,15);await press('back');
 await field(9,12);await press('debt_garran');await press('back');
 await press('dilemma');await press('bell_fence');await press('next');await press('loaded');await press('next');
 check(state.mission.stage==='guild_return','returned to guild');
 await press('ring');
 if(NATURAL===1)await press('identify_guild');
 await press('equipment_open');
 while(state.mission.equipment.item?.id!=='mission_ring')await press('equipment_next');
 if(innerWidth>650)check([...document.querySelectorAll('[data-mission-slot]')].every(el=>el.getBoundingClientRect().bottom<=innerHeight),'equipment controls fit viewport');
 await press('equipment_slots');await press('equipment_attach',{gear_slot:'ring'});
 const g=state.actors.find(a=>a.id==='garran');check(g.ability_scores.strength===19,'score +1 displayed');
 for(let i=0;i<4;i++)await press('equipment_accept');await press('summary');
 check(state.mission.text.title==='Misja zakończona','summary');
 check(document.querySelector('.mission-cargo').textContent.includes('Kompletny'),'cargo accounted');
 check(state.mission.recovery.open_threads.length===2,'debt and pending fence payout');
 check(!state.mission.ledger.some(x=>x.id==='bell_fence_payment'),'no early fence payment');
 check(document.documentElement.scrollWidth<=innerWidth,'no horizontal overflow');
 await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:'PASS'})});
}catch(e){await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:e.stack,body:document.body.innerText.slice(-2400)})})}
})();</script>'''.replace('NATURAL',str(natural))
    error_hook="""<script>window.alert=message=>{throw Error(message)};window.addEventListener('error',e=>fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:String(e.message)+' '+e.filename+':'+e.lineno})}));</script>"""
    @app.after_request
    def inject(response):
        if request.path=='/play' and response.status_code==200:
            response.set_data(response.get_data(as_text=True).replace('<head>','<head>'+error_hook).replace('</body>',harness+'</body>'))
        return response
    server=make_server('127.0.0.1',0,app,threaded=True);worker=Thread(target=server.serve_forever,daemon=True);worker.start();process=None
    try:
        process=subprocess.Popen([chrome,'--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run',
            '--disable-background-networking','--no-proxy-server',f'--user-data-dir={tmp_path/"chrome"}',f'--window-size={width},800',
            f'http://127.0.0.1:{server.server_port}/play'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
        assert done.wait(70),'Browser did not report'
        assert report.get('result')=='PASS',report
    finally:
        if process:
            process.terminate()
            try:process.communicate(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.communicate(timeout=5)
        server.shutdown();worker.join(timeout=2)
