"""Real page, rune dispatch and the physical-dice wizard."""
import shutil
import subprocess
from threading import Event, Thread
from pathlib import Path
import pytest
from werkzeug.serving import make_server
from flask import request
from tests.unit.test_mission_zero import session, stage, start_battle, send
from dnd_board_game.ui import mission_zero as m
from dataclasses import replace
from dnd_board_game.ui.exploration_app import create_app
from dnd_board_game.ui import confrontation as c

@pytest.mark.parametrize('width',[390,1100])
def test_mission_runes_confrontation_pause_and_fatigue_dice(tmp_path,width):
    chrome=shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:pytest.skip('Chrome required')
    s=session(tmp_path);s.configured_board_backend='none'
    app=create_app(s);finished=Event();reported={}
    @app.post('/__test/result')
    def result():
        reported.update(request.get_json());finished.set();return {'ok':True}
    @app.post('/__test/fatigue')
    def fatigue():
        store=c.read_store(s);store['active']=False;c.write(s,store)
        stage(s,'fatigue_roll');return s.state_payload()
    @app.post('/__test/potion')
    def potion():
        from tests.unit.test_pooled_mana_runtime import prepare
        from dnd_board_game.combat.session import current_actor
        data=m.read(s);m.grant(s,data,'potion');m.write(s,data)
        start_battle(s);prepare(s,'B','C')
        actor=current_actor(s.combat_state)
        s.combat_state=replace(s.combat_state,actors=tuple(replace(a,hp=a.hp-15) if a.id==actor.id else a for a in s.combat_state.actors))
        send(s,'potion');send(s,'potion_target',target=str(actor.id))
        return s.state_payload()
    @app.post('/__test/potion-result')
    def potion_result():
        return dict(ok=m.read(s)['stage']=='battle' and not m.available_potions(s))
    harness=r'''<script>
(async()=>{
const wait=async f=>{for(let i=0;i<160;i++){if(f())return;await new Promise(r=>setTimeout(r,30));}throw Error('timeout '+state?.mission?.stage);};
const check=(v,m)=>{if(!v)throw Error(m);};
const press=async(action,exploration=false)=>{await wait(()=>!busy);const options=exploration?state.exploration_mana.board_choices:state.mission.choices;const c=options.find(c=>c.action===action);check(c,'choice '+action);await api('/api/board/select',{col:19,row:29-c.slot},'');await wait(()=>!busy);};
const die=async values=>{const phase=state.exploration_mana?.phase,missionStage=state.mission?.stage;values=Array.isArray(values)?values:[values];
 for(let i=0;i<values.length;i++){
  const value=values[i];await wait(()=>keyboardRollWizard?.index===i&&!keyboardRollWizard.review&&!busy&&!boardPanelSyncPromise);
  let input=document.getElementById('keyboard-roll-wizard-input');input.value=String(value-1);input.dispatchEvent(new Event('input',{bubbles:true}));
  await wait(()=>!boardPanelSyncPromise&&state.board_selection.panel_context===desiredBoardPanel()?.context);
  await api('/api/board/select',{col:19,row:2},'');await wait(()=>!busy&&!boardPanelSyncPromise&&Number(document.getElementById('keyboard-roll-wizard-input')?.value)===value);
  await api('/api/board/select',{col:19,row:1},'');
 }
 await wait(()=>keyboardRollWizard?.review&&!busy&&!boardPanelSyncPromise);
 if(values.length===2)check(document.getElementById('keyboard-roll-wizard').textContent.includes('11 PW'),'potion bonus once in summary');
 await api('/api/board/select',{col:19,row:1},'');
 await wait(()=>!busy&&(state.exploration_mana?.phase!==phase||state.mission?.stage!==missionStage));
};
try{
 await wait(()=>state?.mission&&!busy);
 check(document.getElementById('mission-panel').textContent.includes('Dzwon'),'mission visible');
 for(let i=0;i<12&&state.mission.stage!=='brief';i++)await press('next');
 check(state.mission.stage==='brief','intro progression');
 await press('negotiate');await press('acknowledge',true);await press('acknowledge',true);
 for(let i=0;i<3&&state.exploration_mana.mana.phase==='reveal';i++)await press('color',true);
 await press('take',true);await press('test',true);
 await die(20);check(state.exploration_mana.phase==='impact','natural attack die');
 await die(state.exploration_mana.attempt.die);
 await press('leave',true);check(!state.exploration_mana?.active,'pause');
 await press('negotiate');check(state.exploration_mana.phase!=='introduction','resume retained encounter');
 await api('/__test/fatigue',{},'');await die(4);
 check(state.mission.stage==='fatigue_result'&&state.mission.fatigue===4,'fatigue result');
 check(document.getElementById('mission-panel').textContent.includes('4 pełnych rund'),'fatigue narration');
 check(document.documentElement.scrollWidth<=innerWidth,'horizontal overflow');
 await api('/__test/potion',{},'');await die([3,4]);
 check((await (await fetch('/__test/potion-result',{method:'POST'})).json()).ok,'potion consumed');
 await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:'PASS'})});
}catch(e){await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:e.stack,stage:state?.mission?.stage,body:document.body.innerText.slice(-1500)})});}
})();</script>'''
    @app.after_request
    def inject(response):
        if request.path=='/play' and response.status_code==200:response.set_data(response.get_data(as_text=True).replace('</body>',harness+'</body>'))
        return response
    server=make_server('127.0.0.1',0,app,threaded=True);thread=Thread(target=server.serve_forever,daemon=True);thread.start();process=None
    try:
        process=subprocess.Popen([chrome,'--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--disable-background-networking','--no-proxy-server',f'--user-data-dir={tmp_path/"chrome"}',f'--window-size={width},1000',f'http://127.0.0.1:{server.server_port}/play'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
        assert finished.wait(42),'Browser did not report'
        assert reported.get('result')=='PASS',reported
    finally:
        if process:
            process.terminate()
            try:process.communicate(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.communicate(timeout=5)
        server.shutdown();thread.join(timeout=3)
